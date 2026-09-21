from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.constants import MAX_EXPENSE_AMOUNT, Category, PaymentMethod
from app.schemas import ExpenseCreate


def test_expense_create_accepts_valid_payload():
    payload = ExpenseCreate(
        amount=Decimal("100.00"),
        category=Category.FOOD_DINING,
        payment_method=PaymentMethod.UPI,
        note="Lunch",
        date=date.today(),
    )
    assert payload.amount == Decimal("100.00")
    assert payload.category == Category.FOOD_DINING


def test_expense_create_rejects_non_positive_amount():
    with pytest.raises(ValidationError):
        ExpenseCreate(
            amount=Decimal("0"),
            category=Category.OTHER,
            payment_method=PaymentMethod.CASH,
            date=date.today(),
        )


def test_expense_create_rejects_negative_amount():
    with pytest.raises(ValidationError):
        ExpenseCreate(
            amount=Decimal("-1"),
            category=Category.OTHER,
            payment_method=PaymentMethod.CASH,
            date=date.today(),
        )


def test_expense_create_rejects_invalid_category():
    with pytest.raises(ValidationError):
        ExpenseCreate(
            amount=Decimal("10"),
            category="Invalid",
            payment_method=PaymentMethod.CASH,
            date=date.today(),
        )


def test_expense_create_rejects_invalid_payment_method():
    with pytest.raises(ValidationError):
        ExpenseCreate(
            amount=Decimal("10"),
            category=Category.OTHER,
            payment_method="Paytm",
            date=date.today(),
        )


def test_expense_create_accepts_max_amount():
    payload = ExpenseCreate(
        amount=MAX_EXPENSE_AMOUNT,
        category=Category.OTHER,
        payment_method=PaymentMethod.CASH,
        date=date.today(),
    )
    assert payload.amount == MAX_EXPENSE_AMOUNT


def test_expense_create_rejects_amount_above_max_precision():
    with pytest.raises(ValidationError):
        ExpenseCreate(
            amount=MAX_EXPENSE_AMOUNT + Decimal("0.01"),
            category=Category.OTHER,
            payment_method=PaymentMethod.CASH,
            date=date.today(),
        )


def test_expense_create_rejects_future_date():
    with pytest.raises(ValidationError):
        ExpenseCreate(
            amount=Decimal("10"),
            category=Category.OTHER,
            payment_method=PaymentMethod.CASH,
            date=date.today() + timedelta(days=1),
        )


def test_category_and_payment_method_enums_cover_v1_values():
    assert len(Category) == 10
    assert len(PaymentMethod) == 4
    assert Category.SHOPPING.value == "Shopping"
    assert PaymentMethod.CREDIT_CARD.value == "Credit Card"
