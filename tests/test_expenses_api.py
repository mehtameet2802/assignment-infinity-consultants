from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models import Expense


def _expense_payload(**overrides):
    payload = {
        "amount": 850.50,
        "category": "Food & Dining",
        "payment_method": "UPI",
        "note": "Dinner",
        "date": "2026-09-20",
    }
    payload.update(overrides)
    return payload


def _assert_validation_error(response, *, field: str | None = None):
    assert response.status_code == 422
    body = response.get_json()
    assert body["error"] == "validation_error"
    assert isinstance(body["details"], list)
    assert body["details"]
    for detail in body["details"]:
        assert set(detail.keys()) == {"field", "message"}
    if field is not None:
        assert any(detail["field"] == field for detail in body["details"])


def test_create_expense_success(client):
    response = client.post("/expenses", json=_expense_payload())
    assert response.status_code == 201
    data = response.get_json()
    assert data["id"] is not None
    assert Decimal(str(data["amount"])) == Decimal("850.50")
    assert data["category"] == "Food & Dining"
    assert data["payment_method"] == "UPI"
    assert data["note"] == "Dinner"
    assert data["date"] == "2026-09-20"
    assert data["created_at"] is not None


def test_create_expense_rejects_invalid_json_body(client):
    response = client.post(
        "/expenses",
        data="not-json",
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.get_json() == {
        "error": "invalid_json",
        "details": [
            {"field": None, "message": "Request body must be valid JSON"},
        ],
    }


def test_create_expense_rejects_zero_amount(client):
    response = client.post("/expenses", json=_expense_payload(amount=0))
    _assert_validation_error(response, field="amount")


def test_create_expense_rejects_negative_amount(client):
    response = client.post("/expenses", json=_expense_payload(amount=-10))
    _assert_validation_error(response, field="amount")


def test_create_expense_rejects_invalid_category(client):
    response = client.post("/expenses", json=_expense_payload(category="Paytm"))
    _assert_validation_error(response, field="category")


def test_create_expense_rejects_invalid_payment_method(client):
    response = client.post(
        "/expenses", json=_expense_payload(payment_method="PhonePe")
    )
    _assert_validation_error(response, field="payment_method")


def test_create_expense_rejects_future_date(client):
    future = (date.today() + timedelta(days=1)).isoformat()
    response = client.post("/expenses", json=_expense_payload(date=future))
    _assert_validation_error(response, field="date")


def test_list_expenses_empty(client):
    response = client.get("/expenses")
    assert response.status_code == 200
    data = response.get_json()
    assert data == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_list_expenses_returns_created_records(client):
    client.post("/expenses", json=_expense_payload())
    response = client.get("/expenses")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


def test_list_expenses_filter_by_category(client):
    client.post(
        "/expenses",
        json=_expense_payload(category="Shopping", payment_method="Credit Card"),
    )
    client.post("/expenses", json=_expense_payload(category="Groceries"))

    response = client.get("/expenses", query_string={"category": "Shopping"})
    data = response.get_json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "Shopping"


def test_list_expenses_filter_by_payment_method(client):
    client.post(
        "/expenses",
        json=_expense_payload(payment_method="Cash", note="Snacks"),
    )
    client.post("/expenses", json=_expense_payload(payment_method="UPI"))

    response = client.get("/expenses", query_string={"payment_method": "Cash"})
    data = response.get_json()
    assert data["total"] == 1
    assert data["items"][0]["payment_method"] == "Cash"


def test_list_expenses_filter_by_date_range(client):
    client.post("/expenses", json=_expense_payload(date="2026-09-01"))
    client.post("/expenses", json=_expense_payload(date="2026-09-15"))
    client.post("/expenses", json=_expense_payload(date="2026-10-01"))

    response = client.get(
        "/expenses",
        query_string={"start_date": "2026-09-01", "end_date": "2026-09-30"},
    )
    data = response.get_json()
    assert data["total"] == 2


def test_list_expenses_combined_filters(client):
    client.post(
        "/expenses",
        json=_expense_payload(
            category="Shopping",
            payment_method="Credit Card",
            date="2026-09-10",
        ),
    )
    client.post(
        "/expenses",
        json=_expense_payload(
            category="Shopping",
            payment_method="UPI",
            date="2026-09-10",
        ),
    )
    client.post(
        "/expenses",
        json=_expense_payload(
            category="Groceries",
            payment_method="Credit Card",
            date="2026-09-10",
        ),
    )

    response = client.get(
        "/expenses",
        query_string={
            "category": "Shopping",
            "payment_method": "Credit Card",
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
        },
    )
    data = response.get_json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "Shopping"
    assert data["items"][0]["payment_method"] == "Credit Card"


def test_list_expenses_invalid_date_range(client):
    response = client.get(
        "/expenses",
        query_string={"start_date": "2026-09-30", "end_date": "2026-09-01"},
    )
    assert response.status_code == 400
    assert response.get_json() == {
        "error": "invalid_date_range",
        "details": [
            {
                "field": "start_date",
                "message": "start_date must not be after end_date",
            }
        ],
    }


def test_list_expenses_pagination(client, db_session: Session):
    for day in range(1, 6):
        db_session.add(
            Expense(
                amount=Decimal("100.00"),
                category="Other",
                payment_method="Cash",
                note=None,
                date=date(2026, 9, day),
            )
        )
    db_session.commit()

    page1 = client.get("/expenses", query_string={"limit": 2, "offset": 0})
    page2 = client.get("/expenses", query_string={"limit": 2, "offset": 2})

    assert page1.status_code == 200
    assert page2.status_code == 200
    assert page1.get_json()["total"] == 5
    assert len(page1.get_json()["items"]) == 2
    assert len(page2.get_json()["items"]) == 2
    assert page1.get_json()["items"][0]["date"] == "2026-09-05"
    assert page1.get_json()["items"][1]["date"] == "2026-09-04"


def test_list_expenses_limit_cannot_exceed_max(client):
    response = client.get("/expenses", query_string={"limit": 101})
    _assert_validation_error(response, field="limit")


def test_list_expenses_sorts_by_date_then_id_desc(client, db_session: Session):
    db_session.add_all(
        [
            Expense(
                amount=Decimal("10"),
                category="Other",
                payment_method="Cash",
                date=date(2026, 9, 10),
            ),
            Expense(
                amount=Decimal("20"),
                category="Other",
                payment_method="Cash",
                date=date(2026, 9, 10),
            ),
            Expense(
                amount=Decimal("30"),
                category="Other",
                payment_method="Cash",
                date=date(2026, 9, 11),
            ),
        ]
    )
    db_session.commit()

    response = client.get("/expenses")
    items = response.get_json()["items"]
    assert [item["date"] for item in items] == ["2026-09-11", "2026-09-10", "2026-09-10"]
    assert Decimal(items[1]["amount"]) > Decimal(items[2]["amount"])
