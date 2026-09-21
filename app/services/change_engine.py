from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Union

AmountInput = Union[Decimal, int, str]


class ChangeType(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"
    NO_CHANGE = "no_change"
    NEW = "new"
    RESUMED = "resumed"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class ChangeResult:
    previous_amount: Decimal | None
    current_amount: Decimal
    change_amount: Decimal | None
    change_percentage: Decimal | None
    change_type: ChangeType


def _to_decimal(amount: AmountInput) -> Decimal:
    if isinstance(amount, Decimal):
        return amount
    return Decimal(str(amount))


def _percentage_change(previous: Decimal, current: Decimal) -> Decimal:
    raw = ((current - previous) / previous) * Decimal("100")
    return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_change(
    previous_amount: AmountInput,
    current_amount: AmountInput,
    *,
    historical_spend_exists: bool = False,
    comparison_available: bool = True,
) -> ChangeResult:
    previous = _to_decimal(previous_amount)
    current = _to_decimal(current_amount)

    if previous < 0 or current < 0:
        raise ValueError("Spending amounts must not be negative")

    if not comparison_available:
        return ChangeResult(
            previous_amount=previous,
            current_amount=current,
            change_amount=None,
            change_percentage=None,
            change_type=ChangeType.NOT_APPLICABLE,
        )

    if previous == current:
        return ChangeResult(
            previous_amount=previous,
            current_amount=current,
            change_amount=Decimal("0"),
            change_percentage=Decimal("0"),
            change_type=ChangeType.NO_CHANGE,
        )

    if previous > 0 and current > previous:
        return ChangeResult(
            previous_amount=previous,
            current_amount=current,
            change_amount=current - previous,
            change_percentage=_percentage_change(previous, current),
            change_type=ChangeType.INCREASE,
        )

    if previous > 0 and current < previous:
        return ChangeResult(
            previous_amount=previous,
            current_amount=current,
            change_amount=current - previous,
            change_percentage=_percentage_change(previous, current),
            change_type=ChangeType.DECREASE,
        )

    if previous == 0 and current > 0:
        change_type = (
            ChangeType.RESUMED if historical_spend_exists else ChangeType.NEW
        )
        return ChangeResult(
            previous_amount=previous,
            current_amount=current,
            change_amount=current,
            change_percentage=None,
            change_type=change_type,
        )

    raise ValueError("Unhandled change calculation state")
