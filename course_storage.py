from app_auth import get_user_supabase_client


def get_user_courses(user_id):
    """Retrieve courses belonging to one user."""
    client = get_user_supabase_client()

    response = (
        client.table("courses")
        .select("*")
        .eq("user_id", user_id)
        .order("semester")
        .execute()
    )

    return response.data or []


def add_user_course(
    user_id,
    course_name,
    course_code,
    semester,
    credits,
    teacher,
):
    """Save a course for one user."""
    client = get_user_supabase_client()

    response = (
        client.table("courses")
        .insert({
            "user_id": user_id,
            "course_name": course_name.strip(),
            "course_code": course_code.strip(),
            "semester": semester,
            "credits": float(credits) if credits else None,
            "teacher": teacher.strip(),
        })
        .execute()
    )

    return response.data or []


def update_user_course(
    user_id,
    course_id,
    course_name,
    course_code,
    semester,
    credits,
    teacher,
):
    """Update a course belonging to one user."""
    client = get_user_supabase_client()

    response = (
        client.table("courses")
        .update({
            "course_name": course_name.strip(),
            "course_code": course_code.strip(),
            "semester": semester,
            "credits": float(credits) if credits else None,
            "teacher": teacher.strip(),
        })
        .eq("id", course_id)
        .eq("user_id", user_id)
        .execute()
    )

    return response.data or []


def delete_user_course(user_id, course_id):
    """Delete a course belonging to one user."""
    client = get_user_supabase_client()

    response = (
        client.table("courses")
        .delete()
        .eq("id", course_id)
        .eq("user_id", user_id)
        .execute()
    )

    return response.data or []