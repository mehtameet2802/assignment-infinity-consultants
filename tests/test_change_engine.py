from decimal import Decimal

import pytest

from app.services.change_engine import ChangeType, calculate_change


def test_increase():
    result = calculate_change(Decimal("5000"), Decimal("7000"))
    assert result.change_type == ChangeType.INCREASE
    assert result.change_amount == Decimal("2000")
    assert result.change_percentage == Decimal("40.00")


def test_decrease():
    result = calculate_change(Decimal("5000"), Decimal("3000"))
    assert result.change_type == ChangeType.DECREASE
    assert result.change_amount == Decimal("-2000")
    assert result.change_percentage == Decimal("-40.00")


def test_decrease_to_zero_is_minus_one_hundred_percent():
    result = calculate_change(Decimal("5000"), Decimal("0"))
    assert result.change_type == ChangeType.DECREASE
    assert result.change_amount == Decimal("-5000")
    assert result.change_percentage == Decimal("-100.00")


def test_positive_no_change():
    result = calculate_change(Decimal("5000"), Decimal("5000"))
    assert result.change_type == ChangeType.NO_CHANGE
    assert result.change_amount == Decimal("0")
    assert result.change_percentage == Decimal("0")


def test_zero_to_zero_no_change():
    result = calculate_change(Decimal("0"), Decimal("0"))
    assert result.change_type == ChangeType.NO_CHANGE
    assert result.change_amount == Decimal("0")
    assert result.change_percentage == Decimal("0")


def test_new_when_no_historical_spend():
    result = calculate_change(
        Decimal("0"),
        Decimal("5000"),
        historical_spend_exists=False,
    )
    assert result.change_type == ChangeType.NEW
    assert result.change_amount == Decimal("5000")
    assert result.change_percentage is None


def test_resumed_when_historical_spend_exists():
    result = calculate_change(
        Decimal("0"),
        Decimal("5000"),
        historical_spend_exists=True,
    )
    assert result.change_type == ChangeType.RESUMED
    assert result.change_amount == Decimal("5000")
    assert result.change_percentage is None


def test_not_applicable():
    result = calculate_change(
        Decimal("4000"),
        Decimal("5000"),
        comparison_available=False,
    )
    assert result.change_type == ChangeType.NOT_APPLICABLE
    assert result.change_amount is None
    assert result.change_percentage is None
    assert result.current_amount == Decimal("5000")
    assert result.previous_amount == Decimal("4000")


def test_percentage_rounding_decrease_to_2500_from_3000():
    result = calculate_change(Decimal("3000"), Decimal("2500"))
    assert result.change_type == ChangeType.DECREASE
    assert result.change_percentage == Decimal("-16.67")


def test_percentage_rounding_non_integer_increase():
    result = calculate_change(Decimal("10000"), Decimal("12500"))
    assert result.change_type == ChangeType.INCREASE
    assert result.change_percentage == Decimal("25.00")


def test_negative_previous_amount_rejected():
    with pytest.raises(ValueError, match="must not be negative"):
        calculate_change(Decimal("-1"), Decimal("100"))


def test_negative_current_amount_rejected():
    with pytest.raises(ValueError, match="must not be negative"):
        calculate_change(Decimal("100"), Decimal("-1"))


def test_historical_flag_does_not_affect_increase():
    baseline = calculate_change(
        Decimal("5000"),
        Decimal("7000"),
        historical_spend_exists=False,
    )
    with_history = calculate_change(
        Decimal("5000"),
        Decimal("7000"),
        historical_spend_exists=True,
    )
    assert baseline == with_history


def test_historical_flag_does_not_affect_decrease():
    baseline = calculate_change(
        Decimal("5000"),
        Decimal("0"),
        historical_spend_exists=False,
    )
    with_history = calculate_change(
        Decimal("5000"),
        Decimal("0"),
        historical_spend_exists=True,
    )
    assert baseline == with_history


def test_decimal_outputs_without_float_artifacts():
    result = calculate_change("850.50", "1275.75")
    assert isinstance(result.change_amount, Decimal)
    assert isinstance(result.change_percentage, Decimal)
    assert result.change_amount == Decimal("425.25")
    assert result.change_percentage == Decimal("50.00")


def test_zero_to_positive_never_returns_percentage():
    for historical in (False, True):
        result = calculate_change(
            Decimal("0"),
            Decimal("120"),
            historical_spend_exists=historical,
        )
        assert result.change_percentage is None


def test_not_applicable_takes_precedence_over_increase_logic():
    result = calculate_change(
        Decimal("5000"),
        Decimal("7000"),
        comparison_available=False,
        historical_spend_exists=True,
    )
    assert result.change_type == ChangeType.NOT_APPLICABLE
    assert result.change_amount is None
    assert result.change_percentage is None
