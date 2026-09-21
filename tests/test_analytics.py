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
    expense_date: date,
) -> Expense:
    expense = Expense(
        amount=Decimal(amount),
        category=category,
        payment_method=payment_method,
        note=None,
        date=expense_date,
    )
    db_session.add(expense)
    db_session.commit()
    return expense


def _summary(client, start: str, end: str):
    return client.get(
        "/summary",
        query_string={"start_month": start, "end_month": end},
    )


def test_valid_multi_month_request(client, db_session: Session):
    _add(db_session, amount="100.00", expense_date=date(2026, 4, 10))
    _add(db_session, amount="200.00", expense_date=date(2026, 5, 10))
    response = _summary(client, "2026-04", "2026-06")
    assert response.status_code == 200
    data = response.get_json()
    assert data["start_month"] == "2026-04"
    assert len(data["monthly_totals"]) == 3


def test_missing_start_month(client):
    response = client.get("/summary", query_string={"end_month": "2026-04"})
    assert response.status_code == 422
    assert response.get_json()["error"] == "validation_error"


def test_missing_end_month(client):
    response = client.get("/summary", query_string={"start_month": "2026-04"})
    assert response.status_code == 422


def test_invalid_start_format(client):
    response = _summary(client, "abc", "2026-04")
    assert response.status_code == 422


def test_invalid_end_format(client):
    response = _summary(client, "2026-04", "bad")
    assert response.status_code == 422


def test_invalid_month_number(client):
    response = _summary(client, "2026-13", "2026-14")
    assert response.status_code == 422


def test_start_month_after_end_month(client):
    response = _summary(client, "2026-09", "2026-04")
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_month_range"


def test_both_endpoints_inclusive(client, db_session: Session):
    _add(db_session, amount="10.00", expense_date=date(2026, 4, 1))
    _add(db_session, amount="20.00", expense_date=date(2026, 6, 30))
    totals = _summary(client, "2026-04", "2026-06").get_json()["monthly_totals"]
    assert [item["month"] for item in totals] == ["2026-04", "2026-05", "2026-06"]
    assert Decimal(str(totals[0]["amount"])) == Decimal("10.00")
    assert Decimal(str(totals[2]["amount"])) == Decimal("20.00")


def test_zero_data_month_included(client):
    totals = _summary(client, "2026-04", "2026-05").get_json()["monthly_totals"]
    assert len(totals) == 2
    assert Decimal(str(totals[1]["amount"])) == Decimal("0")


def test_one_month_range(client):
    data = _summary(client, "2026-04", "2026-04").get_json()
    assert len(data["monthly_totals"]) == 1
    assert data["monthly_totals"][0]["change_type"] == "not_applicable"
    assert data["insights"] == []


def test_overall_totals_correct(client, db_session: Session):
    _add(db_session, amount="100.00", expense_date=date(2026, 4, 5))
    _add(db_session, amount="50.00", expense_date=date(2026, 4, 20))
    total = _summary(client, "2026-04", "2026-04").get_json()["monthly_totals"][0]
    assert Decimal(str(total["amount"])) == Decimal("150.00")


def test_first_month_not_applicable(client, db_session: Session):
    _add(db_session, amount="100.00", expense_date=date(2026, 4, 1))
    _add(db_session, amount="200.00", expense_date=date(2026, 5, 1))
    totals = _summary(client, "2026-04", "2026-05").get_json()["monthly_totals"]
    assert totals[0]["change_type"] == "not_applicable"
    assert totals[1]["change_type"] == "increase"


def test_second_month_increase(client, db_session: Session):
    _add(db_session, amount="5000.00", expense_date=date(2026, 4, 1))
    _add(db_session, amount="7000.00", expense_date=date(2026, 5, 1))
    point = _summary(client, "2026-04", "2026-05").get_json()["monthly_totals"][1]
    assert Decimal(str(point["change_amount"])) == Decimal("2000.00")


def test_decrease(client, db_session: Session):
    _add(db_session, amount="5000.00", expense_date=date(2026, 4, 1))
    _add(db_session, amount="3000.00", expense_date=date(2026, 5, 1))
    point = _summary(client, "2026-04", "2026-05").get_json()["monthly_totals"][1]
    assert point["change_type"] == "decrease"


def test_decrease_to_zero(client, db_session: Session):
    _add(db_session, amount="5000.00", expense_date=date(2026, 4, 1))
    point = _summary(client, "2026-04", "2026-05").get_json()["monthly_totals"][1]
    assert point["change_type"] == "decrease"
    assert Decimal(str(point["change_percentage"])) == Decimal("-100.00")


def test_no_change(client, db_session: Session):
    _add(db_session, amount="5000.00", expense_date=date(2026, 4, 1))
    _add(db_session, amount="5000.00", expense_date=date(2026, 5, 1))
    point = _summary(client, "2026-04", "2026-05").get_json()["monthly_totals"][1]
    assert point["change_type"] == "no_change"


def test_overall_new(client, db_session: Session):
    _add(db_session, amount="5000.00", expense_date=date(2026, 5, 1))
    point = _summary(client, "2026-04", "2026-05").get_json()["monthly_totals"][1]
    assert point["change_type"] == "new"


def test_overall_resumed(client, db_session: Session):
    _add(db_session, amount="4000.00", expense_date=date(2026, 3, 1))
    _add(db_session, amount="5000.00", expense_date=date(2026, 5, 1))
    point = _summary(client, "2026-04", "2026-05").get_json()["monthly_totals"][1]
    assert point["change_type"] == "resumed"


def test_all_ten_categories_returned(client):
    categories = _summary(client, "2026-04", "2026-05").get_json()["category_monthly"]
    assert len(categories) == 10


def test_all_months_present_for_each_category(client):
    for series in _summary(client, "2026-04", "2026-06").get_json()["category_monthly"]:
        assert [m["month"] for m in series["months"]] == [
            "2026-04",
            "2026-05",
            "2026-06",
        ]


def test_category_increase(client, db_session: Session):
    _add(
        db_session,
        amount="100.00",
        category="Shopping",
        expense_date=date(2026, 4, 1),
    )
    _add(
        db_session,
        amount="300.00",
        category="Shopping",
        expense_date=date(2026, 5, 1),
    )
    series = next(
        item
        for item in _summary(client, "2026-04", "2026-05").get_json()["category_monthly"]
        if item["category"] == "Shopping"
    )
    assert series["months"][1]["change_type"] == "increase"


def test_category_new(client, db_session: Session):
    _add(
        db_session,
        amount="4000.00",
        category="Travel",
        expense_date=date(2026, 5, 1),
    )
    series = next(
        item
        for item in _summary(client, "2026-04", "2026-05").get_json()["category_monthly"]
        if item["category"] == "Travel"
    )
    assert series["months"][1]["change_type"] == "new"


def test_category_resumed(client, db_session: Session):
    _add(
        db_session,
        amount="2000.00",
        category="Travel",
        expense_date=date(2026, 3, 1),
    )
    _add(
        db_session,
        amount="4000.00",
        category="Travel",
        expense_date=date(2026, 5, 1),
    )
    series = next(
        item
        for item in _summary(client, "2026-04", "2026-05").get_json()["category_monthly"]
        if item["category"] == "Travel"
    )
    assert series["months"][1]["change_type"] == "resumed"


def test_all_four_payment_methods_returned(client):
    assert len(_summary(client, "2026-04", "2026-05").get_json()["payment_method_monthly"]) == 4


def test_payment_method_change_logic(client, db_session: Session):
    _add(
        db_session,
        amount="100.00",
        payment_method="UPI",
        expense_date=date(2026, 4, 1),
    )
    _add(
        db_session,
        amount="250.00",
        payment_method="UPI",
        expense_date=date(2026, 5, 1),
    )
    series = next(
        item
        for item in _summary(client, "2026-04", "2026-05").get_json()[
            "payment_method_monthly"
        ]
        if item["payment_method"] == "UPI"
    )
    assert series["months"][1]["change_type"] == "increase"


def test_unused_combination_omitted(client, db_session: Session):
    _add(
        db_session,
        amount="100.00",
        category="Shopping",
        payment_method="Credit Card",
        expense_date=date(2026, 4, 1),
    )
    combos = _summary(client, "2026-04", "2026-05").get_json()["category_payment_monthly"]
    assert len(combos) == 1
    assert combos[0]["category"] == "Shopping"
    assert combos[0]["payment_method"] == "Credit Card"


def test_active_combination_includes_zero_months(client, db_session: Session):
    _add(
        db_session,
        amount="100.00",
        category="Shopping",
        payment_method="Credit Card",
        expense_date=date(2026, 4, 1),
    )
    _add(
        db_session,
        amount="200.00",
        category="Shopping",
        payment_method="Credit Card",
        expense_date=date(2026, 6, 1),
    )
    combo = _summary(client, "2026-04", "2026-06").get_json()["category_payment_monthly"][0]
    assert len(combo["months"]) == 3
    assert Decimal(str(combo["months"][1]["amount"])) == Decimal("0")


def test_combination_change_logic(client, db_session: Session):
    _add(
        db_session,
        amount="100.00",
        category="Shopping",
        payment_method="Credit Card",
        expense_date=date(2026, 4, 1),
    )
    _add(
        db_session,
        amount="400.00",
        category="Shopping",
        payment_method="Credit Card",
        expense_date=date(2026, 5, 1),
    )
    combo = _summary(client, "2026-04", "2026-05").get_json()["category_payment_monthly"][0]
    assert combo["months"][1]["change_type"] == "increase"


def test_category_history_does_not_use_other_category(client, db_session: Session):
    _add(
        db_session,
        amount="5000.00",
        category="Food & Dining",
        expense_date=date(2026, 3, 1),
    )
    _add(
        db_session,
        amount="3000.00",
        category="Travel",
        expense_date=date(2026, 5, 1),
    )
    travel = next(
        item
        for item in _summary(client, "2026-04", "2026-05").get_json()["category_monthly"]
        if item["category"] == "Travel"
    )
    assert travel["months"][1]["change_type"] == "new"


def test_payment_history_does_not_use_other_method(client, db_session: Session):
    _add(
        db_session,
        amount="5000.00",
        payment_method="UPI",
        expense_date=date(2026, 3, 1),
    )
    _add(
        db_session,
        amount="3000.00",
        payment_method="Cash",
        expense_date=date(2026, 5, 1),
    )
    cash = next(
        item
        for item in _summary(client, "2026-04", "2026-05").get_json()[
            "payment_method_monthly"
        ]
        if item["payment_method"] == "Cash"
    )
    assert cash["months"][1]["change_type"] == "new"


def test_combination_history_is_specific(client, db_session: Session):
    _add(
        db_session,
        amount="1000.00",
        category="Shopping",
        payment_method="UPI",
        expense_date=date(2026, 3, 1),
    )
    _add(
        db_session,
        amount="2000.00",
        category="Shopping",
        payment_method="Credit Card",
        expense_date=date(2026, 5, 1),
    )
    combo = _summary(client, "2026-04", "2026-05").get_json()["category_payment_monthly"][0]
    assert combo["months"][1]["change_type"] == "new"


def test_empty_entire_range_behavior(client):
    data = _summary(client, "2026-04", "2026-06").get_json()
    assert all(Decimal(str(item["amount"])) == 0 for item in data["monthly_totals"])
    assert len(data["category_monthly"]) == 10
    assert data["category_payment_monthly"] == []
    assert data["insights"] == []


def test_one_month_range_has_summary_and_leaders(client, db_session: Session):
    _add(db_session, amount="100.00", expense_date=date(2026, 4, 1))
    insights = _summary(client, "2026-04", "2026-04").get_json()["insights"]
    types = {item["type"] for item in insights}
    assert "range_summary" in types
    assert "range_top_category" in types
    assert "range_top_payment_method" in types
    assert "range_top_category_payment" in types
    assert "range_start_end_change" not in types


def test_insights_empty_for_all_zero_range(client):
    data = _summary(client, "2026-04", "2026-05").get_json()
    assert data["insights"] == []


def test_overall_insight_generated(client, db_session: Session):
    _add(db_session, amount="10000.00", expense_date=date(2026, 8, 1))
    _add(db_session, amount="12500.00", expense_date=date(2026, 9, 1))
    insights = _summary(client, "2026-08", "2026-09").get_json()["insights"]
    assert any(item["type"] == "overall_change" for item in insights)


def test_range_insights_cover_full_selected_period(client, db_session: Session):
    _add(db_session, amount="100.00", category="Groceries", expense_date=date(2026, 4, 1))
    _add(db_session, amount="350.00", category="Travel", expense_date=date(2026, 5, 1))
    _add(db_session, amount="300.00", category="Groceries", expense_date=date(2026, 6, 1))
    insights = _summary(client, "2026-04", "2026-06").get_json()["insights"]
    by_type = {item["type"]: item for item in insights}

    assert "₹750.00" in by_type["range_summary"]["message"]
    assert "₹250.00" in by_type["range_summary"]["message"]
    assert "April 2026" in by_type["range_start_end_change"]["message"]
    assert "June 2026" in by_type["range_start_end_change"]["message"]
    assert by_type["range_peak_month"]["month"] == "2026-05"
    assert by_type["range_low_month"]["month"] == "2026-04"
    assert "Groceries" in by_type["range_top_category"]["message"]


def test_range_start_end_change_handles_zero_start_without_percentage(client, db_session: Session):
    _add(db_session, amount="250.00", expense_date=date(2026, 5, 1))
    insight = next(
        item
        for item in _summary(client, "2026-04", "2026-05").get_json()["insights"]
        if item["type"] == "range_start_end_change"
    )
    assert "rose from ₹0.00" in insight["message"]
    assert "%" not in insight["message"]


def test_range_start_end_change_handles_zero_at_both_ends(client, db_session: Session):
    _add(db_session, amount="250.00", expense_date=date(2026, 5, 1))
    insight = next(
        item
        for item in _summary(client, "2026-04", "2026-06").get_json()["insights"]
        if item["type"] == "range_start_end_change"
    )
    assert "₹0.00 in both April 2026 and June 2026" in insight["message"]
    assert "recorded between" in insight["message"]


def test_largest_category_increase_insight(client, db_session: Session):
    _add(db_session, amount="1000.00", category="Shopping", expense_date=date(2026, 8, 1))
    _add(db_session, amount="4000.00", category="Shopping", expense_date=date(2026, 9, 1))
    _add(db_session, amount="1000.00", category="Travel", expense_date=date(2026, 8, 1))
    _add(db_session, amount="1500.00", category="Travel", expense_date=date(2026, 9, 1))
    insights = _summary(client, "2026-08", "2026-09").get_json()["insights"]
    message = next(
        item["message"] for item in insights if item["type"] == "largest_category_increase"
    )
    assert "Shopping" in message


def test_largest_category_decrease_insight(client, db_session: Session):
    _add(db_session, amount="5000.00", category="Travel", expense_date=date(2026, 8, 1))
    _add(db_session, amount="3200.00", category="Travel", expense_date=date(2026, 9, 1))
    insights = _summary(client, "2026-08", "2026-09").get_json()["insights"]
    assert any(item["type"] == "largest_category_decrease" for item in insights)


def test_largest_payment_increase_insight(client, db_session: Session):
    _add(db_session, amount="1000.00", payment_method="UPI", expense_date=date(2026, 8, 1))
    _add(db_session, amount="5500.00", payment_method="UPI", expense_date=date(2026, 9, 1))
    insights = _summary(client, "2026-08", "2026-09").get_json()["insights"]
    assert any(item["type"] == "largest_payment_method_increase" for item in insights)


def test_largest_combination_increase_insight(client, db_session: Session):
    _add(
        db_session,
        amount="1000.00",
        category="Shopping",
        payment_method="Credit Card",
        expense_date=date(2026, 8, 1),
    )
    _add(
        db_session,
        amount="4500.00",
        category="Shopping",
        payment_method="Credit Card",
        expense_date=date(2026, 9, 1),
    )
    insights = _summary(client, "2026-08", "2026-09").get_json()["insights"]
    assert any(item["type"] == "largest_category_payment_increase" for item in insights)


def test_new_insight_wording_avoids_percentage(client, db_session: Session):
    _add(db_session, amount="4000.00", category="Travel", expense_date=date(2026, 9, 1))
    insights = _summary(client, "2026-08", "2026-09").get_json()["insights"]
    travel_insight = next(item for item in insights if item["type"] == "category_new")
    assert "%" not in travel_insight["message"]
    assert "first time" in travel_insight["message"]


def test_decimal_rounding_behavior(client, db_session: Session):
    _add(db_session, amount="3000.00", expense_date=date(2026, 4, 1))
    _add(db_session, amount="2500.00", expense_date=date(2026, 5, 1))
    point = _summary(client, "2026-04", "2026-05").get_json()["monthly_totals"][1]
    assert Decimal(str(point["change_percentage"])) == Decimal("-16.67")
