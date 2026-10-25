from datetime import date


def prioritize_deadlines(deadlines, today=None):
    """
    Rank upcoming deadlines by urgency, priority,
    and estimated preparation time.

    Expected fields:
    title, due_date, estimated_hours, priority
    """
    if today is None:
        today = date.today()

    priority_rank = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    ranked = []

    for deadline in deadlines:
        try:
            title = str(deadline["title"]).strip()
            due_date_value = deadline["due_date"]

            if isinstance(due_date_value, date):
                due_date = due_date_value
            else:
                due_date = date.fromisoformat(
                    str(due_date_value)[:10]
                )

            estimated_hours = float(
                deadline["estimated_hours"]
            )

            priority = str(
                deadline.get("priority", "Medium")
            ).strip()

            if not title or estimated_hours < 0:
                continue

        except (KeyError, TypeError, ValueError):
            continue

        days_remaining = (due_date - today).days

        if days_remaining < 0:
            status = "Overdue"
        elif days_remaining == 0:
            status = "Due today"
        else:
            status = f"{days_remaining} day(s) remaining"

        ranked.append({
            "title": title,
            "due_date": due_date.isoformat(),
            "days_remaining": days_remaining,
            "status": status,
            "estimated_hours": estimated_hours,
            "priority": priority,
        })

    ranked.sort(
        key=lambda item: (
            item["days_remaining"] > 0,
            item["days_remaining"],
            priority_rank.get(
                item["priority"].casefold(), 3
            ),
            -item["estimated_hours"],
        )
    )

    return ranked