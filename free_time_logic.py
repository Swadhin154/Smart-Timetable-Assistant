from datetime import datetime, time


def _to_time(value):
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


def find_free_slots(classes, day, start_time="06:00", end_time="19:00",
                    min_duration_minutes=30):
    """
    Find available time slots on a selected day.

    Each class should contain Day, Start Time and End Time.
    Returns free slots as dictionaries containing Start Time,
    End Time and Duration (minutes).
    """
    day_key = str(day).strip().casefold()
    day_start = _to_time(start_time)
    day_end = _to_time(end_time)

    if day_start >= day_end:
        raise ValueError("The search end time must be after the start time.")

    if min_duration_minutes < 0:
        raise ValueError("Minimum duration cannot be negative.")

    busy_periods = []

    for item in classes:
        if str(item.get("Day", "")).strip().casefold() != day_key:
            continue

        try:
            start = _to_time(item["Start Time"])
            end = _to_time(item["End Time"])
        except (KeyError, TypeError, ValueError):
            continue

        if start >= end:
            continue

        # Restrict each class to the requested search window.
        start = max(start, day_start)
        end = min(end, day_end)

        if start < end:
            busy_periods.append((start, end))

    busy_periods.sort(key=lambda period: period[0])

    # Merge overlapping or back-to-back classes into busy periods.
    merged = []

    for start, end in busy_periods:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    free_slots = []
    cursor = day_start

    for start, end in merged:
        duration = int(
            (
                datetime.combine(datetime.min.date(), start)
                - datetime.combine(datetime.min.date(), cursor)
            ).total_seconds() // 60
        )

        if duration >= min_duration_minutes:
            free_slots.append({
                "Start Time": cursor.strftime("%I:%M %p"),
                "End Time": start.strftime("%I:%M %p"),
                "Duration (minutes)": duration,
            })

        cursor = max(cursor, end)

    duration = int(
        (
            datetime.combine(datetime.min.date(), day_end)
            - datetime.combine(datetime.min.date(), cursor)
        ).total_seconds() // 60
    )

    if duration >= min_duration_minutes:
        free_slots.append({
            "Start Time": cursor.strftime("%I:%M %p"),
            "End Time": day_end.strftime("%I:%M %p"),
            "Duration (minutes)": duration,
        })

    return free_slots