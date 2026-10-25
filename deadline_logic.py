from datetime import date, datetime


def validate_deadline(title, due_date, estimated_hours, priority):
    """Validate the details of an assignment or exam."""

    if not isinstance(title, str) or not title.strip():
        return False, "Please enter a task title."

    if not isinstance(due_date, date):
        return False, "Please provide a valid due date."

    if isinstance(due_date, datetime):
        due_date = due_date.date()

    if estimated_hours <= 0:
        return False, "Estimated preparation time must be greater than zero."

    if priority not in ("Low", "Medium", "High"):
        return False, "Priority must be Low, Medium, or High."

    return True, "Deadline details are valid."


def get_deadline_status(due_date, today=None):
    """Return the number of days remaining and deadline status."""

    if isinstance(due_date, datetime):
        due_date = due_date.date()

    if today is None:
        today = date.today()

    days_remaining = (due_date - today).days

    if days_remaining < 0:
        status = "Overdue"
    elif days_remaining == 0:
        status = "Due today"
    elif days_remaining <= 3:
        status = "Due soon"
    else:
        status = "Upcoming"

    return {
        "days_remaining": days_remaining,
        "status": status,
    }