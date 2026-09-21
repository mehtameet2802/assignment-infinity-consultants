from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Expense


def _add(
    db_session: Session,
    *,
    amount: str,
    category: str = "Other",
    payment_method: str = "Cash",
    note: str | None = None,
    expense_date: date,
) -> Expense:
    expense = Expense(
        amount=Decimal(amount),
        category=category,
        payment_method=payment_method,
        note=note,
        date=expense_date,
    )
    db_session.add(expense)
    db_session.commit()
    db_session.refresh(expense)
    return expense


def test_dashboard_valid_request(client, db_session: Session):
    _add(db_session, amount="100.00", expense_date=date(2026, 9, 10))
    response = client.get("/dashboard", query_string={"month": "2026-09"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["month"] == "2026-09"
    assert Decimal(str(data["total_spend"])) == Decimal("100.00")
    assert data["transaction_count"] == 1


def test_dashboard_missing_month_rejected(client):
    response = client.get("/dashboard")
    assert response.status_code == 422
    body = response.get_json()
    assert body["error"] == "validation_error"
    assert body["details"][0]["field"] == "month"


def test_dashboard_invalid_month_format_rejected(client):
    response = client.get("/dashboard", query_string={"month": "abc"})
    assert response.status_code == 422
    assert response.get_json()["error"] == "validation_error"


def test_dashboard_invalid_month_number_rejected(client):
    response = client.get("/dashboard", query_string={"month": "2026-13"})
    assert response.status_code == 422
    assert response.get_json()["error"] == "validation_error"


def test_dashboard_rejects_year_zero_month(client):
    response = client.get("/dashboard", query_string={"month": "0000-01"})
    assert response.status_code == 422
    assert response.get_json()["error"] == "validation_error"


def test_dashboard_total_spend_correct(client, db_session: Session):
    _add(db_session, amount="100.50", expense_date=date(2026, 9, 1))
    _add(db_session, amount="49.50", expense_date=date(2026, 9, 30))
    data = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()
    assert Decimal(str(data["total_spend"])) == Decimal("150.00")


def test_dashboard_transaction_count_correct(client, db_session: Session):
    for day in (1, 2, 3):
        _add(db_session, amount="10.00", expense_date=date(2026, 9, day))
    data = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()
    assert data["transaction_count"] == 3


def test_dashboard_previous_month_comparison(client, db_session: Session):
    _add(db_session, amount="200.00", expense_date=date(2026, 8, 15))
    _add(db_session, amount="300.00", expense_date=date(2026, 9, 15))
    change = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "month_change"
    ]
    assert change["previous_month"] == "2026-08"
    assert Decimal(str(change["previous_amount"])) == Decimal("200.00")
    assert Decimal(str(change["current_amount"])) == Decimal("300.00")


def test_dashboard_january_compares_to_december(client, db_session: Session):
    _add(db_session, amount="100.00", expense_date=date(2025, 12, 20))
    _add(db_session, amount="250.00", expense_date=date(2026, 1, 10))
    change = client.get("/dashboard", query_string={"month": "2026-01"}).get_json()[
        "month_change"
    ]
    assert change["previous_month"] == "2025-12"


def test_dashboard_increase_state(client, db_session: Session):
    _add(db_session, amount="5000.00", expense_date=date(2026, 8, 1))
    _add(db_session, amount="7000.00", expense_date=date(2026, 9, 1))
    change = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "month_change"
    ]
    assert change["change_type"] == "increase"
    assert Decimal(str(change["change_amount"])) == Decimal("2000.00")
    assert Decimal(str(change["change_percentage"])) == Decimal("40.00")


def test_dashboard_decrease_state(client, db_session: Session):
    _add(db_session, amount="5000.00", expense_date=date(2026, 8, 1))
    _add(db_session, amount="3000.00", expense_date=date(2026, 9, 1))
    change = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "month_change"
    ]
    assert change["change_type"] == "decrease"
    assert Decimal(str(change["change_amount"])) == Decimal("-2000.00")


def test_dashboard_decrease_to_zero_minus_one_hundred_percent(
    client, db_session: Session
):
    _add(db_session, amount="5000.00", expense_date=date(2026, 8, 1))
    data = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()
    change = data["month_change"]
    assert change["change_type"] == "decrease"
    assert Decimal(str(change["change_amount"])) == Decimal("-5000.00")
    assert Decimal(str(change["change_percentage"])) == Decimal("-100.00")


def test_dashboard_new_state(client, db_session: Session):
    _add(db_session, amount="5000.00", expense_date=date(2026, 9, 1))
    change = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "month_change"
    ]
    assert change["change_type"] == "new"
    assert change["change_percentage"] is None


def test_dashboard_resumed_state(client, db_session: Session):
    _add(db_session, amount="4000.00", expense_date=date(2026, 6, 10))
    _add(db_session, amount="5000.00", expense_date=date(2026, 8, 10))
    change = client.get("/dashboard", query_string={"month": "2026-08"}).get_json()[
        "month_change"
    ]
    assert change["change_type"] == "resumed"
    assert change["change_percentage"] is None


def test_dashboard_no_change_state(client, db_session: Session):
    _add(db_session, amount="5000.00", expense_date=date(2026, 8, 1))
    _add(db_session, amount="5000.00", expense_date=date(2026, 9, 1))
    change = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "month_change"
    ]
    assert change["change_type"] == "no_change"
    assert Decimal(str(change["change_amount"])) == Decimal("0")
    assert Decimal(str(change["change_percentage"])) == Decimal("0")


def test_dashboard_category_breakdown_correct(client, db_session: Session):
    _add(
        db_session,
        amount="100.00",
        category="Groceries",
        expense_date=date(2026, 9, 5),
    )
    _add(
        db_session,
        amount="50.00",
        category="Transport",
        expense_date=date(2026, 9, 6),
    )
    breakdown = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "category_breakdown"
    ]
    by_name = {item["category"]: item for item in breakdown}
    assert Decimal(str(by_name["Groceries"]["amount"])) == Decimal("100.00")
    assert by_name["Groceries"]["transaction_count"] == 1
    assert Decimal(str(by_name["Transport"]["amount"])) == Decimal("50.00")


def test_dashboard_zero_spend_categories_included(client, db_session: Session):
    _add(db_session, amount="10.00", expense_date=date(2026, 9, 1))
    breakdown = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "category_breakdown"
    ]
    assert len(breakdown) == 10
    travel = next(item for item in breakdown if item["category"] == "Travel")
    assert Decimal(str(travel["amount"])) == Decimal("0")
    assert travel["transaction_count"] == 0


def test_dashboard_payment_method_breakdown_correct(client, db_session: Session):
    _add(
        db_session,
        amount="75.00",
        payment_method="UPI",
        expense_date=date(2026, 9, 3),
    )
    breakdown = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "payment_method_breakdown"
    ]
    by_name = {item["payment_method"]: item for item in breakdown}
    assert Decimal(str(by_name["UPI"]["amount"])) == Decimal("75.00")


def test_dashboard_zero_spend_payment_methods_included(client, db_session: Session):
    _add(
        db_session,
        amount="20.00",
        payment_method="Cash",
        expense_date=date(2026, 9, 1),
    )
    breakdown = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "payment_method_breakdown"
    ]
    assert len(breakdown) == 4
    credit = next(item for item in breakdown if item["payment_method"] == "Credit Card")
    assert Decimal(str(credit["amount"])) == Decimal("0")


def test_dashboard_top_category_correct(client, db_session: Session):
    _add(
        db_session,
        amount="500.00",
        category="Shopping",
        expense_date=date(2026, 9, 1),
    )
    _add(
        db_session,
        amount="100.00",
        category="Groceries",
        expense_date=date(2026, 9, 2),
    )
    tops = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "top_categories"
    ]
    assert len(tops) == 1
    assert tops[0]["category"] == "Shopping"


def test_dashboard_tied_top_categories(client, db_session: Session):
    _add(
        db_session,
        amount="500.00",
        category="Food & Dining",
        expense_date=date(2026, 9, 1),
    )
    _add(
        db_session,
        amount="500.00",
        category="Shopping",
        expense_date=date(2026, 9, 2),
    )
    _add(
        db_session,
        amount="100.00",
        category="Travel",
        expense_date=date(2026, 9, 3),
    )
    tops = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "top_categories"
    ]
    assert len(tops) == 2
    assert {item["category"] for item in tops} == {"Food & Dining", "Shopping"}


def test_dashboard_top_payment_method_correct(client, db_session: Session):
    _add(
        db_session,
        amount="300.00",
        payment_method="UPI",
        expense_date=date(2026, 9, 1),
    )
    _add(
        db_session,
        amount="50.00",
        payment_method="Cash",
        expense_date=date(2026, 9, 2),
    )
    tops = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "top_payment_methods"
    ]
    assert len(tops) == 1
    assert tops[0]["payment_method"] == "UPI"


def test_dashboard_tied_top_payment_methods(client, db_session: Session):
    _add(
        db_session,
        amount="200.00",
        payment_method="UPI",
        expense_date=date(2026, 9, 1),
    )
    _add(
        db_session,
        amount="200.00",
        payment_method="Credit Card",
        expense_date=date(2026, 9, 2),
    )
    tops = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "top_payment_methods"
    ]
    assert len(tops) == 2


def test_dashboard_recent_expenses_limited_to_five(client, db_session: Session):
    for day in range(1, 8):
        _add(db_session, amount="10.00", expense_date=date(2026, 9, day))
    recent = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "recent_expenses"
    ]
    assert len(recent) == 5


def test_dashboard_recent_expenses_sorted(client, db_session: Session):
    first = _add(db_session, amount="10.00", expense_date=date(2026, 9, 10))
    second = _add(db_session, amount="20.00", expense_date=date(2026, 9, 10))
    _add(db_session, amount="30.00", expense_date=date(2026, 9, 5))
    recent = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "recent_expenses"
    ]
    assert recent[0]["id"] == second.id
    assert recent[1]["id"] == first.id


def test_dashboard_recent_expenses_restricted_to_selected_month(
    client, db_session: Session
):
    _add(db_session, amount="10.00", expense_date=date(2026, 8, 31))
    _add(db_session, amount="20.00", expense_date=date(2026, 9, 1))
    _add(db_session, amount="30.00", expense_date=date(2026, 10, 1))
    recent = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "recent_expenses"
    ]
    assert len(recent) == 1
    assert Decimal(str(recent[0]["amount"])) == Decimal("20.00")


def test_dashboard_empty_selected_month(client, db_session: Session):
    _add(db_session, amount="5000.00", expense_date=date(2026, 8, 1))
    data = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()
    assert data["total_spend"] in (0, "0", "0.00")
    assert data["transaction_count"] == 0
    assert data["top_categories"] == []
    assert data["top_payment_methods"] == []
    assert data["recent_expenses"] == []
    assert len(data["category_breakdown"]) == 10
    assert len(data["payment_method_breakdown"]) == 4


def test_dashboard_percentage_of_total_correct(client, db_session: Session):
    _add(
        db_session,
        amount="250.00",
        category="Shopping",
        expense_date=date(2026, 9, 1),
    )
    _add(
        db_session,
        amount="750.00",
        category="Groceries",
        expense_date=date(2026, 9, 2),
    )
    breakdown = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "category_breakdown"
    ]
    shopping = next(item for item in breakdown if item["category"] == "Shopping")
    assert Decimal(str(shopping["percentage_of_total"])) == Decimal("25.00")


def test_dashboard_percentage_zero_when_total_zero(client, db_session: Session):
    breakdown = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()[
        "category_breakdown"
    ]
    for item in breakdown:
        assert Decimal(str(item["percentage_of_total"])) == Decimal("0")


def test_dashboard_serializes_money_and_percentages_cleanly(
    client, db_session: Session
):
    _add(db_session, amount="100.00", expense_date=date(2026, 8, 1))
    _add(db_session, amount="125.00", expense_date=date(2026, 9, 1))
    data = client.get("/dashboard", query_string={"month": "2026-09"}).get_json()
    assert data["total_spend"] == "125.00"
    assert data["month_change"]["change_percentage"] == "25.00"
