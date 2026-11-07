from app_auth import get_user_supabase_client


def get_user_academic_events(user_id):
    """Retrieve academic events belonging to one user."""

    client = get_user_supabase_client()

    response = (
        client.table("academic_events")
        .select("*")
        .eq("user_id", user_id)
        .order("event_date")
        .execute()
    )

    return response.data or []


def add_user_academic_event(
    user_id,
    event_title,
    event_date,
    event_type,
    description="",
):
    """Add a personal academic event."""

    client = get_user_supabase_client()

    response = (
        client.table("academic_events")
        .insert({
            "user_id": user_id,
            "event_title": event_title.strip(),
            "event_date": event_date.isoformat(),
            "event_type": event_type,
            "description": description.strip(),
        })
        .execute()
    )

    return response.data or []


def update_user_academic_event(
    user_id,
    event_id,
    event_title,
    event_date,
    event_type,
    description="",
):
    """Update an existing personal academic event."""

    client = get_user_supabase_client()

    response = (
        client.table("academic_events")
        .update({
            "event_title": event_title.strip(),
            "event_date": event_date.isoformat(),
            "event_type": event_type,
            "description": description.strip(),
        })
        .eq("id", event_id)
        .eq("user_id", user_id)
        .execute()
    )

    return response.data or []


def delete_user_academic_event(user_id, event_id):
    """Delete one user's academic event."""

    client = get_user_supabase_client()

    response = (
        client.table("academic_events")
        .delete()
        .eq("id", event_id)
        .eq("user_id", user_id)
        .execute()
    )

    return response.data or []