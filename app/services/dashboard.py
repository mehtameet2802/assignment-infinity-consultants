import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import Category, PaymentMethod
from app.dashboard_schemas import (
    CategoryMetric,
    DashboardRecentExpense,
    DashboardResponse,
    MonthChangeBlock,
    PaymentMethodMetric,
)
from app.models import Expense
from app.services.change_engine import calculate_change


def _month_start_end(month: str) -> tuple[date, date]:
    year = int(month[:4])
    month_number = int(month[5:7])
    start = date(year, month_number, 1)
    last_day = calendar.monthrange(year, month_number)[1]
    end = date(year, month_number, last_day)
    return start, end


def _previous_month_label(month: str) -> str:
    year = int(month[:4])
    month_number = int(month[5:7])
    if month_number == 1:
        return f"{year - 1}-12"
    return f"{year}-{month_number - 1:02d}"


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _percentage_of_total(amount: Decimal, total: Decimal) -> Decimal:
    if total == 0:
        return Decimal("0")
    raw = (amount / total) * Decimal("100")
    return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _month_total(db: Session, start: date, end: date) -> Decimal:
    total = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.date >= start,
            Expense.date <= end,
        )
    )
    return _quantize_money(Decimal(str(total or 0)))


def _month_transaction_count(db: Session, start: date, end: date) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Expense)
            .where(Expense.date >= start, Expense.date <= end)
        )
        or 0
    )


def _historical_spend_exists(db: Session, before_date: date) -> bool:
    count = db.scalar(
        select(func.count())
        .select_from(Expense)
        .where(Expense.date < before_date, Expense.amount > 0)
    )
    return bool(count and count > 0)


def _category_aggregates(
    db: Session, start: date, end: date
) -> dict[str, tuple[Decimal, int]]:
    rows = db.execute(
        select(
            Expense.category,
            func.coalesce(func.sum(Expense.amount), 0),
            func.count(),
        )
        .where(Expense.date >= start, Expense.date <= end)
        .group_by(Expense.category)
    ).all()
    return {
        category: (_quantize_money(Decimal(str(amount))), int(count))
        for category, amount, count in rows
    }


def _payment_method_aggregates(
    db: Session, start: date, end: date
) -> dict[str, tuple[Decimal, int]]:
    rows = db.execute(
        select(
            Expense.payment_method,
            func.coalesce(func.sum(Expense.amount), 0),
            func.count(),
        )
        .where(Expense.date >= start, Expense.date <= end)
        .group_by(Expense.payment_method)
    ).all()
    return {
        payment_method: (_quantize_money(Decimal(str(amount))), int(count))
        for payment_method, amount, count in rows
    }


def _build_category_metrics(
    aggregates: dict[str, tuple[Decimal, int]], total_spend: Decimal
) -> list[CategoryMetric]:
    metrics: list[CategoryMetric] = []
    for category in Category:
        amount, count = aggregates.get(category.value, (Decimal("0"), 0))
        metrics.append(
            CategoryMetric(
                category=category.value,
                amount=amount,
                percentage_of_total=_percentage_of_total(amount, total_spend),
                transaction_count=count,
            )
        )
    return metrics


def _build_payment_method_metrics(
    aggregates: dict[str, tuple[Decimal, int]], total_spend: Decimal
) -> list[PaymentMethodMetric]:
    metrics: list[PaymentMethodMetric] = []
    for payment_method in PaymentMethod:
        amount, count = aggregates.get(payment_method.value, (Decimal("0"), 0))
        metrics.append(
            PaymentMethodMetric(
                payment_method=payment_method.value,
                amount=amount,
                percentage_of_total=_percentage_of_total(amount, total_spend),
                transaction_count=count,
            )
        )
    return metrics


def _top_categories(metrics: list[CategoryMetric]) -> list[CategoryMetric]:
    if not metrics:
        return []
    max_amount = max(item.amount for item in metrics)
    if max_amount <= 0:
        return []
    return [item for item in metrics if item.amount == max_amount]


def _top_payment_methods(
    metrics: list[PaymentMethodMetric],
) -> list[PaymentMethodMetric]:
    if not metrics:
        return []
    max_amount = max(item.amount for item in metrics)
    if max_amount <= 0:
        return []
    return [item for item in metrics if item.amount == max_amount]


def get_dashboard(db: Session, month: str) -> DashboardResponse:
    start, end = _month_start_end(month)
    previous_month = _previous_month_label(month)
    previous_start, previous_end = _month_start_end(previous_month)

    total_spend = _month_total(db, start, end)
    transaction_count = _month_transaction_count(db, start, end)
    previous_total = _month_total(db, previous_start, previous_end)

    historical_exists = _historical_spend_exists(db, previous_start)
    change = calculate_change(
        previous_total,
        total_spend,
        historical_spend_exists=historical_exists,
        comparison_available=True,
    )

    category_aggs = _category_aggregates(db, start, end)
    payment_aggs = _payment_method_aggregates(db, start, end)
    category_breakdown = _build_category_metrics(category_aggs, total_spend)
    payment_method_breakdown = _build_payment_method_metrics(
        payment_aggs, total_spend
    )

    recent_rows = db.scalars(
        select(Expense)
        .where(Expense.date >= start, Expense.date <= end)
        .order_by(Expense.date.desc(), Expense.id.desc())
        .limit(5)
    ).all()

    return DashboardResponse(
        month=month,
        total_spend=total_spend,
        transaction_count=transaction_count,
        month_change=MonthChangeBlock(
            previous_month=previous_month,
            previous_amount=change.previous_amount or Decimal("0"),
            current_amount=change.current_amount,
            change_amount=change.change_amount,
            change_percentage=change.change_percentage,
            change_type=change.change_type.value,
        ),
        top_categories=_top_categories(category_breakdown),
        top_payment_methods=_top_payment_methods(payment_method_breakdown),
        category_breakdown=category_breakdown,
        payment_method_breakdown=payment_method_breakdown,
        recent_expenses=[
            DashboardRecentExpense.model_validate(expense) for expense in recent_rows
        ],
    )
