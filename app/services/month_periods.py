import calendar
from datetime import date


def month_start_end(month: str) -> tuple[date, date]:
    year = int(month[:4])
    month_number = int(month[5:7])
    start = date(year, month_number, 1)
    last_day = calendar.monthrange(year, month_number)[1]
    end = date(year, month_number, last_day)
    return start, end


def iter_months_inclusive(start_month: str, end_month: str) -> list[str]:
    year = int(start_month[:4])
    month_number = int(start_month[5:7])
    end_year = int(end_month[:4])
    end_month_number = int(end_month[5:7])

    months: list[str] = []
    while (year, month_number) <= (end_year, end_month_number):
        months.append(f"{year}-{month_number:02d}")
        if month_number == 12:
            year += 1
            month_number = 1
        else:
            month_number += 1
    return months
