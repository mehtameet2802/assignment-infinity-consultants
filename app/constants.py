from enum import Enum


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
