from datetime import date
from decimal import Decimal

from app.models import Expense


def test_expense_table_can_be_persisted(db_session):
    expense = Expense(
        amount=Decimal("850.50"),
        category="Food & Dining",
        payment_method="UPI",
        note="Dinner",
        date=date(2026, 9, 20),
    )
    db_session.add(expense)
    db_session.commit()
    db_session.refresh(expense)

    assert expense.id is not None
    assert expense.amount == Decimal("850.50")
    assert expense.category == "Food & Dining"
    assert expense.payment_method == "UPI"
    assert expense.note == "Dinner"
    assert expense.date == date(2026, 9, 20)
    assert expense.created_at is not None
