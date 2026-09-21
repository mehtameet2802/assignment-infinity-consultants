import calendar
from collections.abc import Callable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics_schemas import (
    CategoryMonthlySeries,
    CategoryPaymentMonthlySeries,
    Insight,
    MonthlyAmountPoint,
    PaymentMethodMonthlySeries,
    SummaryResponse,
)
from app.constants import Category, PaymentMethod
from app.models import Expense
from app.services.change_engine import ChangeType, calculate_change
from app.services.month_periods import iter_months_inclusive, month_start_end

_MONTH_KEY = func.strftime("%Y-%m", Expense.date)


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _to_decimal(value) -> Decimal:
    return _quantize_money(Decimal(str(value or 0)))


def _month_point_from_change(month: str, amount: Decimal, change) -> MonthlyAmountPoint:
    return MonthlyAmountPoint(
        month=month,
        amount=amount,
        change_amount=change.change_amount,
        change_percentage=change.change_percentage,
        change_type=change.change_type.value,
    )


def _not_applicable_point(month: str, amount: Decimal) -> MonthlyAmountPoint:
    return MonthlyAmountPoint(
        month=month,
        amount=amount,
        change_amount=None,
        change_percentage=None,
        change_type=ChangeType.NOT_APPLICABLE.value,
    )


def _build_month_series(
    months: list[str],
    amount_by_month: dict[str, Decimal],
    historical_exists_before: Callable[[date], bool],
) -> list[MonthlyAmountPoint]:
    points: list[MonthlyAmountPoint] = []
    for index, month in enumerate(months):
        amount = amount_by_month.get(month, Decimal("0"))
        if index == 0:
            points.append(_not_applicable_point(month, amount))
            continue

        previous_month = months[index - 1]
        previous_amount = amount_by_month.get(previous_month, Decimal("0"))
        previous_start, _ = month_start_end(previous_month)
        change = calculate_change(
            previous_amount,
            amount,
            historical_spend_exists=historical_exists_before(previous_start),
            comparison_available=True,
        )
        points.append(_month_point_from_change(month, amount, change))
    return points


def _format_inr(amount: Decimal) -> str:
    quantized = _quantize_money(amount)
    sign = "-" if quantized < 0 else ""
    absolute = abs(quantized)
    formatted = f"{absolute:,.2f}"
    return f"{sign}₹{formatted}"


def _month_label(month: str) -> str:
    month_number = int(month[5:7])
    year = int(month[:4])
    return f"{calendar.month_name[month_number]} {year}"


def _overall_amounts(db: Session, range_start: date, range_end: date) -> dict[str, Decimal]:
    rows = db.execute(
        select(_MONTH_KEY, func.coalesce(func.sum(Expense.amount), 0))
        .where(Expense.date >= range_start, Expense.date <= range_end)
        .group_by(_MONTH_KEY)
    ).all()
    return {month: _to_decimal(amount) for month, amount in rows if month}


def _category_amounts(db: Session, range_start: date, range_end: date) -> dict[str, dict[str, Decimal]]:
    rows = db.execute(
        select(
            Expense.category,
            _MONTH_KEY,
            func.coalesce(func.sum(Expense.amount), 0),
        )
        .where(Expense.date >= range_start, Expense.date <= range_end)
        .group_by(Expense.category, _MONTH_KEY)
    ).all()
    result: dict[str, dict[str, Decimal]] = {}
    for category, month, amount in rows:
        if not month:
            continue
        result.setdefault(category, {})[month] = _to_decimal(amount)
    return result


def _payment_method_amounts(
    db: Session, range_start: date, range_end: date
) -> dict[str, dict[str, Decimal]]:
    rows = db.execute(
        select(
            Expense.payment_method,
            _MONTH_KEY,
            func.coalesce(func.sum(Expense.amount), 0),
        )
        .where(Expense.date >= range_start, Expense.date <= range_end)
        .group_by(Expense.payment_method, _MONTH_KEY)
    ).all()
    result: dict[str, dict[str, Decimal]] = {}
    for payment_method, month, amount in rows:
        if not month:
            continue
        result.setdefault(payment_method, {})[month] = _to_decimal(amount)
    return result


def _combo_amounts(
    db: Session, range_start: date, range_end: date
) -> dict[tuple[str, str], dict[str, Decimal]]:
    rows = db.execute(
        select(
            Expense.category,
            Expense.payment_method,
            _MONTH_KEY,
            func.coalesce(func.sum(Expense.amount), 0),
        )
        .where(Expense.date >= range_start, Expense.date <= range_end)
        .group_by(Expense.category, Expense.payment_method, _MONTH_KEY)
    ).all()
    result: dict[tuple[str, str], dict[str, Decimal]] = {}
    for category, payment_method, month, amount in rows:
        if not month:
            continue
        result.setdefault((category, payment_method), {})[month] = _to_decimal(amount)
    return result


def _min_positive_dates_by_category(db: Session) -> dict[str, date]:
    rows = db.execute(
        select(Expense.category, func.min(Expense.date))
        .where(Expense.amount > 0)
        .group_by(Expense.category)
    ).all()
    return {category: min_date for category, min_date in rows if min_date}


def _min_positive_dates_by_payment_method(db: Session) -> dict[str, date]:
    rows = db.execute(
        select(Expense.payment_method, func.min(Expense.date))
        .where(Expense.amount > 0)
        .group_by(Expense.payment_method)
    ).all()
    return {payment_method: min_date for payment_method, min_date in rows if min_date}


def _min_positive_dates_by_combo(db: Session) -> dict[tuple[str, str], date]:
    rows = db.execute(
        select(Expense.category, Expense.payment_method, func.min(Expense.date))
        .where(Expense.amount > 0)
        .group_by(Expense.category, Expense.payment_method)
    ).all()
    return {
        (category, payment_method): min_date
        for category, payment_method, min_date in rows
        if min_date
    }


def _historical_from_min(min_date: date | None, before: date) -> bool:
    return min_date is not None and min_date < before


def _active_combo_keys(
    combo_amounts: dict[tuple[str, str], dict[str, Decimal]], months: list[str]
) -> list[tuple[str, str]]:
    active: list[tuple[str, str]] = []
    for key, month_map in combo_amounts.items():
        if any(month_map.get(month, Decimal("0")) > 0 for month in months):
            active.append(key)
    active.sort(key=lambda item: (item[0], item[1]))
    return active


def _generate_insights(
    months: list[str],
    monthly_totals: list[MonthlyAmountPoint],
    category_monthly: list[CategoryMonthlySeries],
    payment_method_monthly: list[PaymentMethodMonthlySeries],
    category_payment_monthly: list[CategoryPaymentMonthlySeries],
) -> list[Insight]:
    if len(months) < 2:
        return []

    final_month = months[-1]
    final_overall = monthly_totals[-1]
    insights: list[Insight] = []

    if final_overall.change_type == ChangeType.INCREASE.value:
        pct = final_overall.change_percentage
        pct_text = f" ({pct:+.2f}%)" if pct is not None else ""
        insights.append(
            Insight(
                type="overall_change",
                month=final_month,
                message=(
                    f"Overall spending increased by {_format_inr(final_overall.change_amount)}"
                    f"{pct_text} in {_month_label(final_month)}."
                ),
            )
        )
    elif final_overall.change_type == ChangeType.DECREASE.value:
        pct = final_overall.change_percentage
        pct_text = f" ({pct:+.2f}%)" if pct is not None else ""
        insights.append(
            Insight(
                type="overall_change",
                month=final_month,
                message=(
                    f"Overall spending decreased by {_format_inr(abs(final_overall.change_amount))}"
                    f"{pct_text} in {_month_label(final_month)}."
                ),
            )
        )
    elif final_overall.change_type == ChangeType.NEW.value:
        insights.append(
            Insight(
                type="overall_change",
                month=final_month,
                message=(
                    f"Overall spending appeared for the first time in {_month_label(final_month)} "
                    f"at {_format_inr(final_overall.amount)}."
                ),
            )
        )
    elif final_overall.change_type == ChangeType.RESUMED.value:
        insights.append(
            Insight(
                type="overall_change",
                month=final_month,
                message=(
                    f"Overall spending resumed in {_month_label(final_month)} "
                    f"at {_format_inr(final_overall.amount)}."
                ),
            )
        )

    category_final_points = {
        series.category: series.months[-1] for series in category_monthly
    }
    increases = [
        (category, point)
        for category, point in category_final_points.items()
        if point.change_amount is not None and point.change_amount > 0
    ]
    if increases:
        category, point = max(increases, key=lambda item: item[1].change_amount)
        insights.append(
            Insight(
                type="largest_category_increase",
                month=final_month,
                message=(
                    f"{category} recorded the largest category increase: "
                    f"+{_format_inr(point.change_amount)}."
                ),
            )
        )

    decreases = [
        (category, point)
        for category, point in category_final_points.items()
        if point.change_amount is not None and point.change_amount < 0
    ]
    if decreases:
        category, point = min(decreases, key=lambda item: item[1].change_amount)
        insights.append(
            Insight(
                type="largest_category_decrease",
                month=final_month,
                message=(
                    f"{category} recorded the largest category decrease: "
                    f"{_format_inr(point.change_amount)}."
                ),
            )
        )

    payment_final_points = {
        series.payment_method: series.months[-1]
        for series in payment_method_monthly
    }
    payment_increases = [
        (payment_method, point)
        for payment_method, point in payment_final_points.items()
        if point.change_amount is not None and point.change_amount > 0
    ]
    if payment_increases:
        payment_method, point = max(
            payment_increases, key=lambda item: item[1].change_amount
        )
        insights.append(
            Insight(
                type="largest_payment_method_increase",
                month=final_month,
                message=(
                    f"{payment_method} spending increased the most: "
                    f"+{_format_inr(point.change_amount)}."
                ),
            )
        )

    payment_decreases = [
        (payment_method, point)
        for payment_method, point in payment_final_points.items()
        if point.change_amount is not None and point.change_amount < 0
    ]
    if payment_decreases:
        payment_method, point = min(
            payment_decreases, key=lambda item: item[1].change_amount
        )
        insights.append(
            Insight(
                type="largest_payment_method_decrease",
                month=final_month,
                message=(
                    f"{payment_method} spending decreased the most: "
                    f"{_format_inr(point.change_amount)}."
                ),
            )
        )

    combo_increases = [
        (series.category, series.payment_method, series.months[-1])
        for series in category_payment_monthly
        if series.months[-1].change_amount is not None
        and series.months[-1].change_amount > 0
    ]
    if combo_increases:
        category, payment_method, point = max(
            combo_increases, key=lambda item: item[2].change_amount
        )
        insights.append(
            Insight(
                type="largest_category_payment_increase",
                month=final_month,
                message=(
                    f"{category} paid using {payment_method} increased by "
                    f"{_format_inr(point.change_amount)}."
                ),
            )
        )

    for series in category_monthly:
        point = series.months[-1]
        if point.change_type == ChangeType.NEW.value:
            insights.append(
                Insight(
                    type="category_new",
                    month=final_month,
                    message=(
                        f"{series.category} spending appeared for the first time in "
                        f"{_month_label(final_month)} at {_format_inr(point.amount)}."
                    ),
                )
            )
        elif point.change_type == ChangeType.RESUMED.value:
            insights.append(
                Insight(
                    type="category_resumed",
                    month=final_month,
                    message=(
                        f"{series.category} spending resumed in {_month_label(final_month)} "
                        f"at {_format_inr(point.amount)}."
                    ),
                )
            )

    return insights


def get_summary(db: Session, start_month: str, end_month: str) -> SummaryResponse:
    months = iter_months_inclusive(start_month, end_month)
    range_start, _ = month_start_end(start_month)
    _, range_end = month_start_end(end_month)

    overall_amounts = _overall_amounts(db, range_start, range_end)
    category_amounts = _category_amounts(db, range_start, range_end)
    payment_amounts = _payment_method_amounts(db, range_start, range_end)
    combo_amounts = _combo_amounts(db, range_start, range_end)

    overall_min_date = db.scalar(
        select(func.min(Expense.date)).where(Expense.amount > 0)
    )
    category_min_dates = _min_positive_dates_by_category(db)
    payment_min_dates = _min_positive_dates_by_payment_method(db)
    combo_min_dates = _min_positive_dates_by_combo(db)

    monthly_totals = _build_month_series(
        months,
        overall_amounts,
        lambda before: _historical_from_min(overall_min_date, before),
    )

    category_monthly = [
        CategoryMonthlySeries(
            category=category.value,
            months=_build_month_series(
                months,
                category_amounts.get(category.value, {}),
                lambda before, cat=category.value: _historical_from_min(
                    category_min_dates.get(cat), before
                ),
            ),
        )
        for category in Category
    ]

    payment_method_monthly = [
        PaymentMethodMonthlySeries(
            payment_method=payment_method.value,
            months=_build_month_series(
                months,
                payment_amounts.get(payment_method.value, {}),
                lambda before, pm=payment_method.value: _historical_from_min(
                    payment_min_dates.get(pm), before
                ),
            ),
        )
        for payment_method in PaymentMethod
    ]

    active_combos = _active_combo_keys(combo_amounts, months)
    category_payment_monthly = [
        CategoryPaymentMonthlySeries(
            category=category,
            payment_method=payment_method,
            months=_build_month_series(
                months,
                combo_amounts.get((category, payment_method), {}),
                lambda before, key=(category, payment_method): _historical_from_min(
                    combo_min_dates.get(key), before
                ),
            ),
        )
        for category, payment_method in active_combos
    ]

    insights = _generate_insights(
        months,
        monthly_totals,
        category_monthly,
        payment_method_monthly,
        category_payment_monthly,
    )

    return SummaryResponse(
        start_month=start_month,
        end_month=end_month,
        monthly_totals=monthly_totals,
        category_monthly=category_monthly,
        payment_method_monthly=payment_method_monthly,
        category_payment_monthly=category_payment_monthly,
        insights=insights,
    )
