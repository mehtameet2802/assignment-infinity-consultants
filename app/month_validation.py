import re


def validate_month_string(value: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}", value):
        raise ValueError("Invalid month format. Expected YYYY-MM")
    year = int(value[:4])
    month_number = int(value[5:7])
    if year < 1 or month_number < 1 or month_number > 12:
        raise ValueError("Invalid month format. Expected YYYY-MM")
    return value
