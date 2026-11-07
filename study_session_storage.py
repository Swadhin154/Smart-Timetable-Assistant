from app_auth import get_user_supabase_client


def get_user_study_sessions(user_id):
    client = get_user_supabase_client()

    response = (
        client.table("study_sessions")
        .select("*")
        .eq("user_id", user_id)
        .order("session_date")
        .order("start_time")
        .execute()
    )

    return response.data or []


def add_user_study_session(
    user_id,
    exam_id,
    course_id,
    session_date,
    start_time,
    end_time,
    duration_minutes
):
    client = get_user_supabase_client()

    response = (
        client.table("study_sessions")
        .insert({
            "user_id": user_id,
            "exam_id": exam_id,
            "course_id": course_id,
            "session_date": session_date.isoformat(),
            "start_time": start_time.strftime("%H:%M:%S"),
            "end_time": end_time.strftime("%H:%M:%S"),
            "duration_minutes": duration_minutes,
            "status": "Planned",
        })
        .execute()
    )

    return response.data or []


def update_study_session_status(user_id, session_id, status):
    client = get_user_supabase_client()

    response = (
        client.table("study_sessions")
        .update({"status": status})
        .eq("id", session_id)
        .eq("user_id", user_id)
        .execute()
    )

    return response.data or []


def delete_user_study_session(user_id, session_id):
    client = get_user_supabase_client()

    response = (
        client.table("study_sessions")
        .delete()
        .eq("id", session_id)
        .eq("user_id", user_id)
        .execute()
    )

    return response.data or []

def delete_exam_study_sessions(user_id, exam_id):
    """Delete existing study sessions for one user's exam."""
    client = get_user_supabase_client()

    response = (
        client.table("study_sessions")
        .delete()
        .eq("user_id", user_id)
        .eq("exam_id", exam_id)
        .execute()
    )

    return response.data or []    