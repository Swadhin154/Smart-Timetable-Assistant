from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from free_time_logic import find_free_slots, _to_time


INDIA_TZ = ZoneInfo("Asia/Kolkata")


def calculate_recommended_hours(difficulty, preparedness):
    """
    Estimate preparation hours.

    difficulty: 1 (easy) to 5 (very difficult)
    preparedness: 1 (not prepared) to 5 (well prepared)
    """

    if difficulty not in range(1, 6):
        raise ValueError("Difficulty must be between 1 and 5.")

    if preparedness not in range(1, 6):
        raise ValueError("Preparedness must be between 1 and 5.")

    hours = 4 + (difficulty * 2) + ((6 - preparedness) * 2)

    return hours


def generate_exam_study_plan(
    classes,
    exam_date,
    exam_id,
    course_id,
    target_hours=None,
    difficulty=3,
    preparedness=3,
    max_session_minutes=120,
    max_daily_minutes=180,
    min_session_minutes=30,
    planning_date=None,
):
    """
    Generate study sessions before an exam using available timetable slots.

    If target_hours is provided, manual allocation is used.
    Otherwise, recommended hours are calculated automatically.

    Returns a dictionary containing sessions and allocation summary.
    """

    if planning_date is None:
        planning_date = datetime.now(INDIA_TZ).date()

    if isinstance(exam_date, datetime):
        exam_date = exam_date.date()

    if exam_date <= planning_date:
        raise ValueError("The exam date must be after today.")

    if target_hours is None:
        target_hours = calculate_recommended_hours(
            difficulty,
            preparedness
        )

    if target_hours <= 0:
        raise ValueError("Target preparation hours must be positive.")

    if max_session_minutes < min_session_minutes:
        raise ValueError(
            "Maximum session duration must be at least the minimum duration."
        )

    if min_session_minutes <= 0 or max_session_minutes <= 0:
        raise ValueError("Session durations must be positive.")

    if max_daily_minutes < min_session_minutes:
        raise ValueError(
            "Daily study limit must be at least the minimum session duration."
        )

    target_minutes = int(round(target_hours * 60))
    remaining_minutes = target_minutes

    current_time = datetime.now(INDIA_TZ).time()
    study_plan = []

    current_date = planning_date

    while current_date < exam_date and remaining_minutes > 0:

        weekday = current_date.strftime("%A")
        search_start = "06:00"

        # Avoid suggesting past slots when planning for today.
        if current_date == planning_date:
            earliest_time = (
                datetime.combine(current_date, current_time)
                + timedelta(minutes=15)
            ).time()

            search_start = max(
                time(6, 0),
                earliest_time
            ).strftime("%H:%M")

        if search_start < "19:00":

            free_slots = find_free_slots(
                classes=classes,
                day=weekday,
                start_time=search_start,
                end_time="19:00",
                min_duration_minutes=min_session_minutes,
            )

            daily_allocated = 0

            for slot in free_slots:

                if remaining_minutes <= 0:
                    break

                if daily_allocated >= max_daily_minutes:
                    break

                slot_start = _to_time(slot["Start Time"])
                slot_end = _to_time(slot["End Time"])

                start_dt = datetime.combine(current_date, slot_start)
                end_dt = datetime.combine(current_date, slot_end)

                available_minutes = int(
                    (end_dt - start_dt).total_seconds() // 60
                )

                daily_capacity = (
                    max_daily_minutes - daily_allocated
                )

                allocation = min(
                    available_minutes,
                    max_session_minutes,
                    daily_capacity,
                    remaining_minutes,
                )

                if allocation < min_session_minutes:
                    continue

                session_end = start_dt + timedelta(
                    minutes=allocation
                )

                study_plan.append({
                    "exam_id": exam_id,
                    "course_id": course_id,
                    "session_date": current_date,
                    "start_time": start_dt.time(),
                    "end_time": session_end.time(),
                    "duration_minutes": allocation,
                    "status": "Planned",
                })

                remaining_minutes -= allocation
                daily_allocated += allocation

        current_date += timedelta(days=1)

    return {
        "sessions": study_plan,
        "target_minutes": target_minutes,
        "allocated_minutes": target_minutes - remaining_minutes,
        "unallocated_minutes": remaining_minutes,
    }