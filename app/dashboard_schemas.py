from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.month_validation import validate_month_string


class DashboardQuery(BaseModel):
    month: str

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str) -> str:
        return validate_month_string(value)


class MonthChangeBlock(BaseModel):
    previous_month: str
    previous_amount: Decimal
    current_amount: Decimal
    change_amount: Optional[Decimal]
    change_percentage: Optional[Decimal]
    change_type: str


class CategoryMetric(BaseModel):
    category: str
    amount: Decimal
    percentage_of_total: Decimal
    transaction_count: int


class PaymentMethodMetric(BaseModel):
    payment_method: str
    amount: Decimal
    percentage_of_total: Decimal
    transaction_count: int


class DashboardRecentExpense(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    category: str
    payment_method: str
    note: Optional[str]
    amount: Decimal
    created_at: datetime


class DashboardResponse(BaseModel):
    month: str
    total_spend: Decimal
    transaction_count: int
    month_change: MonthChangeBlock
    top_categories: list[CategoryMetric]
    top_payment_methods: list[PaymentMethodMetric]
    category_breakdown: list[CategoryMetric]
    payment_method_breakdown: list[PaymentMethodMetric]
    recent_expenses: list[DashboardRecentExpense]
