from app_auth import get_user_supabase_client


def get_user_exams(user_id):
    """Retrieve exams belonging to one user."""
    client = get_user_supabase_client()

    response = (
        client.table("exams")
        .select("*")
        .eq("user_id", user_id)
        .order("exam_date")
        .execute()
    )

    return response.data or []


def add_user_exam(
    user_id,
    course_id,
    exam_title,
    exam_date,
    start_time=None,
    end_time=None,
    exam_type="Final",
    location="",
    notes="",
):
    """Save an exam for one user."""
    client = get_user_supabase_client()

    response = (
        client.table("exams")
        .insert({
            "user_id": user_id,
            "course_id": course_id,
            "exam_title": exam_title.strip(),
            "exam_date": exam_date.isoformat(),
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "exam_type": exam_type,
            "location": location.strip(),
            "notes": notes.strip(),
        })
        .execute()
    )

    return response.data or []


def update_user_exam(
    user_id,
    exam_id,
    course_id,
    exam_title,
    exam_date,
    start_time=None,
    end_time=None,
    exam_type="Final",
    location="",
    notes="",
):
    """Update an exam belonging to one user."""
    client = get_user_supabase_client()

    response = (
        client.table("exams")
        .update({
            "course_id": course_id,
            "exam_title": exam_title.strip(),
            "exam_date": exam_date.isoformat(),
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "exam_type": exam_type,
            "location": location.strip(),
            "notes": notes.strip(),
        })
        .eq("id", exam_id)
        .eq("user_id", user_id)
        .execute()
    )

    return response.data or []


def delete_user_exam(user_id, exam_id):
    """Delete an exam belonging to one user."""
    client = get_user_supabase_client()

    response = (
        client.table("exams")
        .delete()
        .eq("id", exam_id)
        .eq("user_id", user_id)
        .execute()
    )

    return response.data or []