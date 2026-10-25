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


def _format_duration(total_minutes):
    """Format minutes as hours and minutes."""
    hours, minutes = divmod(total_minutes, 60)

    if hours and minutes:
        return f"{hours} hr {minutes} min"
    if hours:
        return f"{hours} hr"
    return f"{minutes} min"


def _duration_in_minutes(duration):
    """Convert a formatted duration to minutes."""
    parts = duration.split()
    total = 0

    for index, part in enumerate(parts):
        if part == "hr":
            total += int(parts[index - 1]) * 60
        elif part == "min":
            total += int(parts[index - 1])

    return total


def recommend_study_slots(
    classes,
    day,
    min_duration_minutes=30,
    max_recommendations=3,
    start_time="06:00",
    end_time="19:00",
):
    """
    Recommend the longest uninterrupted study periods
    on a selected day.
    """
    if min_duration_minutes <= 0 or max_recommendations <= 0:
        return []

    try:
        window_start = _parse_time(start_time)
        window_end = _parse_time(end_time)
    except (TypeError, ValueError):
        return []

    if window_start >= window_end:
        return []

    target_day = str(day).strip().casefold()
    busy_periods = []

    for item in classes:
        if str(item.get("Day", "")).strip().casefold() != target_day:
            continue

        try:
            start = _parse_time(item["Start Time"])
            end = _parse_time(item["End Time"])
        except (KeyError, TypeError, ValueError):
            continue

        if start >= end:
            continue

        start = max(start, window_start)
        end = min(end, window_end)

        if start < end:
            busy_periods.append((start, end))

    busy_periods.sort(key=lambda period: period[0])

    # Merge overlapping and adjacent classes.
    merged_periods = []

    for start, end in busy_periods:
        if merged_periods and start <= merged_periods[-1][1]:
            previous_start, previous_end = merged_periods[-1]
            merged_periods[-1] = (
                previous_start,
                max(previous_end, end),
            )
        else:
            merged_periods.append((start, end))

    today = datetime.today().date()
    cursor = datetime.combine(today, window_start)
    window_finish = datetime.combine(today, window_end)

    recommendations = []

    for busy_start_time, busy_end_time in merged_periods:
        busy_start = datetime.combine(today, busy_start_time)
        busy_end = datetime.combine(today, busy_end_time)

        gap_minutes = int(
            (busy_start - cursor).total_seconds() // 60
        )

        if gap_minutes >= min_duration_minutes:
            recommendations.append({
                "Day": day,
                "Start Time": cursor.strftime("%I:%M %p"),
                "End Time": busy_start.strftime("%I:%M %p"),
                "Available Duration": _format_duration(gap_minutes),
            })

        cursor = max(cursor, busy_end)

    remaining_minutes = int(
        (window_finish - cursor).total_seconds() // 60
    )

    if remaining_minutes >= min_duration_minutes:
        recommendations.append({
            "Day": day,
            "Start Time": cursor.strftime("%I:%M %p"),
            "End Time": window_finish.strftime("%I:%M %p"),
            "Available Duration": _format_duration(remaining_minutes),
        })

    # Prioritize the longest study periods; break ties by start time.
    recommendations.sort(
        key=lambda slot: (
            -_duration_in_minutes(slot["Available Duration"]),
            datetime.strptime(slot["Start Time"], "%I:%M %p").time(),
        )
    )

    return recommendations[:max_recommendations]