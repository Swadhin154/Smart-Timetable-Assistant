from app_auth import get_user_supabase_client


def get_user_deadlines(user_id):
    """Retrieve deadlines belonging to one user."""
    client = get_user_supabase_client()

    response = (
        client.table("deadlines")
        .select("*")
        .eq("user_id", user_id)
        .order("due_date")
        .execute()
    )

    return response.data or []


def add_user_deadline(
    user_id,
    title,
    due_date,
    estimated_hours,
    priority,
):
    """Save a deadline for one user."""
    client = get_user_supabase_client()

    response = (
        client.table("deadlines")
        .insert({
            "user_id": user_id,
            "title": title,
            "due_date": due_date.isoformat(),
            "estimated_hours": float(estimated_hours),
            "priority": priority,
        })
        .execute()
    )

    return response.data or []


def delete_user_deadline(user_id, deadline_id):
    """Delete a deadline belonging to one user."""
    client = get_user_supabase_client()

    response = (
        client.table("deadlines")
        .delete()
        .eq("id", deadline_id)
        .eq("user_id", user_id)
        .execute()
    )

    return response.data or []