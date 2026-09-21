from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants import Category, PaymentMethod


class ExpenseBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    category: Category
    payment_method: PaymentMethod
    note: Optional[str] = Field(default=None, max_length=500)
    date: date

    @field_validator("date")
    @classmethod
    def date_not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Expense date cannot be in the future")
        return value


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseResponse(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
