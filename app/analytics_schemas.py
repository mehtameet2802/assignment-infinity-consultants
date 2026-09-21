from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.month_validation import validate_month_string


class SummaryQuery(BaseModel):
    start_month: str
    end_month: str

    @field_validator("start_month", "end_month")
    @classmethod
    def validate_month(cls, value: str) -> str:
        return validate_month_string(value)


class MonthlyAmountPoint(BaseModel):
    month: str
    amount: Decimal
    change_amount: Optional[Decimal] = None
    change_percentage: Optional[Decimal] = None
    change_type: str


class CategoryMonthlySeries(BaseModel):
    category: str
    months: list[MonthlyAmountPoint]


class PaymentMethodMonthlySeries(BaseModel):
    payment_method: str
    months: list[MonthlyAmountPoint]


class CategoryPaymentMonthlySeries(BaseModel):
    category: str
    payment_method: str
    months: list[MonthlyAmountPoint]


class Insight(BaseModel):
    type: str
    month: str
    message: str


class SummaryResponse(BaseModel):
    start_month: str
    end_month: str
    monthly_totals: list[MonthlyAmountPoint]
    category_monthly: list[CategoryMonthlySeries]
    payment_method_monthly: list[PaymentMethodMonthlySeries]
    category_payment_monthly: list[CategoryPaymentMonthlySeries]
    insights: list[Insight] = Field(default_factory=list)
