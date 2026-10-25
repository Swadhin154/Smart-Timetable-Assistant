import re
from datetime import datetime, timedelta


DAYS = [
    "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday", "Sunday"
]


def contains(text, phrases):
    """Match complete words and phrases."""
    return any(
        re.search(r"\b" + re.escape(phrase) + r"\b", text)
        for phrase in phrases
    )


def understand_request(text):
    """Interpret common English timetable questions."""

    if not isinstance(text, str) or not text.strip():
        return {
            "action": None,
            "day": None,
            "error": "Please enter a request."
        }

    request = re.sub(
        r"\s+", " ", text.casefold()
    ).strip()

    # 1. Identify the day.
    day = None

    if contains(request, ["day after tomorrow"]):
        day = (
            datetime.now() + timedelta(days=2)
        ).strftime("%A")

    elif contains(request, ["tomorrow"]):
        day = (
            datetime.now() + timedelta(days=1)
        ).strftime("%A")

    elif contains(request, ["today"]):
        day = datetime.now().strftime("%A")

    else:
        for candidate in DAYS:
            if contains(request, [candidate.casefold()]):
                day = candidate
                break

    # 2. Recognize timetable conflicts.
    conflict_phrases = [
        "clash", "clashes", "clashing",
        "conflict", "conflicts",
        "overlap", "overlaps", "overlapping",
        "double booked", "double booking",
        "same time", "schedule collision",
        "timing conflict"
    ]

    # 3. Recognize study recommendations.
    study_phrases = [
        "study", "studying", "revision",
        "revise", "prepare for exam",
        "preparation", "best time to learn",
        "study session", "study period",
        "study recommendation"
    ]

    # 4. Recognize free-time questions.
    free_phrases = [
        "free", "free time", "free slot",
        "available", "availability",
        "vacant", "empty", "gap", "gaps",
        "break", "breaks", "spare time",
        "no classes", "not busy",
        "time off", "open slot"
    ]

    # 5. Choose the intended action.
    if contains(request, conflict_phrases):
        action = "check_conflicts"

    elif contains(request, study_phrases):
        action = "study_recommendations"

    elif contains(request, free_phrases):
        action = "find_free_time"

    else:
        return {
            "action": None,
            "day": day,
            "error": (
                "I couldn't understand that request. "
                "Try asking about free time, study periods, "
                "or timetable clashes."
            )
        }

    # 6. Ask for a day if none was provided.
    if day is None:
        return {
            "action": action,
            "day": None,
            "error": (
                "Please mention a day, such as Monday, "
                "today, or tomorrow."
            )
        }

    return {
        "action": action,
        "day": day,
        "error": None
    }