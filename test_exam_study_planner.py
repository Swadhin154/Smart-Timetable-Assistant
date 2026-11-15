from datetime import date, timedelta

from exam_study_planner import generate_exam_study_plan


classes = [
    {
        "Day": "Monday",
        "Start Time": "09:00",
        "End Time": "10:00",
    },
    {
        "Day": "Monday",
        "Start Time": "11:00",
        "End Time": "12:00",
    },
    {
        "Day": "Tuesday",
        "Start Time": "10:00",
        "End Time": "11:00",
    },
    {
        "Day": "Wednesday",
        "Start Time": "09:00",
        "End Time": "10:00",
    },
]

result = generate_exam_study_plan(
    classes=classes,
    exam_date=date.today() + timedelta(days=7),
    exam_id=1,
    course_id=1,
    target_hours=8,
)

print("\nGENERATED STUDY PLAN")

for session in result["sessions"]:
    print(
        session["session_date"],
        session["start_time"].strftime("%I:%M %p"),
        "-",
        session["end_time"].strftime("%I:%M %p"),
        "|",
        session["duration_minutes"],
        "minutes"
    )

print("\nSUMMARY")
print("Target minutes:", result["target_minutes"])
print("Allocated minutes:", result["allocated_minutes"])
print("Unallocated minutes:", result["unallocated_minutes"])

assert result["allocated_minutes"] <= result["target_minutes"]
assert result["allocated_minutes"] + result["unallocated_minutes"] == result["target_minutes"]

print("\nTEST PASSED")