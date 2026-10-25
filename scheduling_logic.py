from datetime import datetime, time


def _parse_time(value):
    """Convert supported time values into datetime.time."""
    if isinstance(value, datetime):
        return value.time()

    if isinstance(value, time):
        return value

    if isinstance(value, str):
        for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p"):
            try:
                return datetime.strptime(value.strip(), fmt).time()
            except ValueError:
                continue

    raise ValueError(f"Invalid time value: {value!r}")


def find_timetable_conflicts(classes):
    """
    Find overlapping classes on the same day.

    Each class should contain:
    Day, Start Time, End Time, and subject (or Subject).

    Returns a list of dictionaries describing each conflict.
    """
    conflicts = []

    for i, first in enumerate(classes):
        for second in classes[i + 1:]:
            first_day = str(first.get("Day", "")).strip().casefold()
            second_day = str(second.get("Day", "")).strip().casefold()

            if not first_day or first_day != second_day:
                continue

            try:
                first_start = _parse_time(first["Start Time"])
                first_end = _parse_time(first["End Time"])
                second_start = _parse_time(second["Start Time"])
                second_end = _parse_time(second["End Time"])
            except (KeyError, ValueError, TypeError):
                continue

            # Ignore invalid or zero-duration classes.
            if first_start >= first_end or second_start >= second_end:
                continue

            # Adjacent classes are not conflicts.
            if first_start < second_end and second_start < first_end:
                conflicts.append({
                    "Day": first.get("Day", ""),
                    "Class 1": first.get(
                        "subject", first.get("Subject", "Untitled")
                    ),
                    "Class 1 Time": (
                        f"{first_start:%H:%M}–{first_end:%H:%M}"
                    ),
                    "Class 2": second.get(
                        "subject", second.get("Subject", "Untitled")
                    ),
                    "Class 2 Time": (
                        f"{second_start:%H:%M}–{second_end:%H:%M}"
                    ),
                })

    return conflicts