from datetime import date


def get_indian_national_holidays(year=2026):
    """
    Return the All India Holidays reference list.

    Dates are based on the India Post 2026 holiday list.
    Update this dataset when the official annual list changes.
    """

    holidays_2026 = [
        ("Republic Day", "2026-01-26"),
        ("Id-ul-Fitr", "2026-03-21"),
        ("Mahavir Jayanti", "2026-03-31"),
        ("Good Friday", "2026-04-03"),
        ("Buddha Purnima", "2026-05-01"),
        ("Id-ul-Zuha", "2026-05-27"),
        ("Muharram", "2026-06-26"),
        ("Independence Day", "2026-08-15"),
        ("Prophet Mohammad's Birthday (Id-e-Milad)", "2026-08-26"),
        ("Mahatma Gandhi's Birthday", "2026-10-02"),
        ("Dussehra (Vijay Dashmi)", "2026-10-20"),
        ("Diwali (Deepavali)", "2026-11-08"),
        ("Guru Nanak's Birthday", "2026-11-24"),
        ("Christmas Day", "2026-12-25"),
    ]

    if year != 2026:
        return []

    events = []

    for name, date_text in holidays_2026:
        holiday_date = date.fromisoformat(date_text)

        events.append({
            "Event": name,
            "Date": holiday_date,
            "Day": holiday_date.strftime("%A"),
            "Category": "All India Holiday",
            "Source": "India Post 2026 Holiday List",
        })

    return events


def get_upcoming_holidays(year=2026, today=None):
    """Return holidays occurring today or later."""

    if today is None:
        today = date.today()

    holidays = get_indian_national_holidays(year)

    return [
        holiday
        for holiday in holidays
        if holiday["Date"] >= today
    ]