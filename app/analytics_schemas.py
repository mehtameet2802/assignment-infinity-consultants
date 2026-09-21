import re
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SummaryQuery(BaseModel):
    start_month: str
    end_month: str

    @field_validator("start_month", "end_month")
    @classmethod
    def validate_month(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}-\d{2}", value):
            raise ValueError("Invalid month format. Expected YYYY-MM")
        month_number = int(value[5:7])
        if month_number < 1 or month_number > 12:
            raise ValueError("Invalid month format. Expected YYYY-MM")
        return value


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
