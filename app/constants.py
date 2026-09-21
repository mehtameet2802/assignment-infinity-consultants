from decimal import Decimal
from enum import Enum

# Matches Expense.amount NUMERIC(12, 2): 10 integer digits + 2 fraction digits.
MAX_EXPENSE_AMOUNT = Decimal("9999999999.99")


class Category(str, Enum):
    FOOD_DINING = "Food & Dining"
    GROCERIES = "Groceries"
    TRANSPORT = "Transport"
    SHOPPING = "Shopping"
    BILLS_UTILITIES = "Bills & Utilities"
    ENTERTAINMENT = "Entertainment"
    HEALTH = "Health"
    TRAVEL = "Travel"
    EDUCATION = "Education"
    OTHER = "Other"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "Credit Card"
    DEBIT_CARD = "Debit Card"
    UPI = "UPI"
    CASH = "Cash"
