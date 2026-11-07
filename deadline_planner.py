from datetime import date, datetime


def prioritize_deadlines(deadlines, today=None):
    """
    Rank assignments using:
    1. Deadline urgency: 40%
    2. User-selected priority: 35%
    3. Preparation workload: 25%
    """

    if today is None:
        today = date.today()

    priority_scores = {
        "high": 100,
        "medium": 60,
        "low": 30,
    }

    ranked = []

    for deadline in deadlines:
        try:
            title = str(deadline["title"]).strip()
            due_date_value = deadline["due_date"]

            if isinstance(due_date_value, datetime):
                due_date = due_date_value.date()
            elif isinstance(due_date_value, date):
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

            if not title or estimated_hours <= 0:
                continue

        except (KeyError, TypeError, ValueError):
            continue

        # Calculate deadline urgency score.
        days_remaining = (due_date - today).days

        if days_remaining <= 0:
            urgency_score = 100
        else:
            urgency_score = max(
                0,
                100 - (days_remaining * 5)
            )

        # Calculate selected priority score.
        priority_score = priority_scores.get(
            priority.lower(), 60
        )

        # Calculate workload score.
        workload_score = min(
            estimated_hours * 10,
            100
        )

        # Calculate the weighted overall score.
        final_score = (
            urgency_score * 0.40
            + priority_score * 0.35
            + workload_score * 0.25
        )

        # Determine deadline status.
        if days_remaining < 0:
            status = "Overdue"
        elif days_remaining == 0:
            status = "Due today"
        elif days_remaining <= 3:
            status = "Due soon"
        else:
            status = f"{days_remaining} day(s) remaining"

        # Assign recommendation level.
        if final_score >= 75:
            recommendation = "High"
        elif final_score >= 45:
            recommendation = "Medium"
        else:
            recommendation = "Low"

        ranked.append({
            "title": title,
            "due_date": due_date.isoformat(),
            "days_remaining": days_remaining,
            "status": status,
            "estimated_hours": estimated_hours,
            "priority": priority,
            "urgency_score": round(urgency_score, 2),
            "priority_score": round(priority_score, 2),
            "workload_score": round(workload_score, 2),
            "priority_score_total": round(final_score, 2),
            "recommendation": recommendation,
        })

    # Highest overall score appears first.
    ranked.sort(
        key=lambda item: (
            -item["priority_score_total"],
            item["days_remaining"],
        )
    )

    return ranked