from datetime import date, datetime, time

import streamlit as st

from app_auth import get_current_user

from course_storage import get_user_courses

from exam_storage import get_user_exams

from study_session_storage import (
    get_user_study_sessions,
    add_user_study_session,
    update_study_session_status,
    delete_user_study_session,
    delete_exam_study_sessions,
)

from exam_study_planner import (
    generate_exam_study_plan,
    calculate_recommended_hours,
)


# ---------- PAGE CONFIGURATION ----------

st.set_page_config(
    page_title="Study Plan | Smart Timetable Assistant",
    page_icon="📖",
    layout="wide",
)


# ---------- HELPER FUNCTION ----------

def format_study_time(value):
    """Convert supported time values into 12-hour AM/PM format."""

    if value is None or value == "":
        return "-"

    if isinstance(value, datetime):
        value = value.time()

    if isinstance(value, time):
        return value.strftime("%I:%M %p")

    value = str(value).strip()

    for fmt in (
        "%H:%M:%S",
        "%H:%M",
        "%I:%M:%S %p",
        "%I:%M %p",
    ):
        try:
            parsed_time = datetime.strptime(value, fmt)
            return parsed_time.strftime("%I:%M %p")
        except ValueError:
            continue

    return value


# ---------- USER AUTHENTICATION ----------

current_user = get_current_user()

if not current_user:
    st.warning("Please sign in from the main application.")
    st.stop()

user_id = current_user.id


# ---------- EXAM STUDY PLANNER ----------

st.title("Exam Study Planner")

try:
    planner_exams = get_user_exams(user_id)
    planner_sessions = get_user_study_sessions(user_id)

    if not planner_exams:
        st.info(
            "Add an exam in Manage Exams before creating a study plan."
        )

    else:
        exam_options = {
            f"{exam['exam_title']} - {exam['exam_date']}": exam
            for exam in planner_exams
        }

        selected_exam_label = st.selectbox(
            "Select an exam",
            list(exam_options.keys()),
            key="study_planner_exam",
        )

        selected_planner_exam = exam_options[selected_exam_label]

        st.caption(
            f"Exam date: {selected_planner_exam['exam_date']}"
        )

        allocation_method = st.radio(
            "How would you like to calculate preparation hours?",
            [
                "Set preparation hours manually",
                "Calculate automatically",
            ],
            key="study_allocation_method",
        )

        target_hours = None
        difficulty = 3
        preparedness = 3

        if allocation_method == "Set preparation hours manually":

            target_hours = st.number_input(
                "Total preparation hours",
                min_value=1.0,
                max_value=200.0,
                value=8.0,
                step=1.0,
                key="manual_preparation_hours",
            )

        else:

            difficulty = st.slider(
                "Exam difficulty",
                min_value=1,
                max_value=5,
                value=3,
                help="1 = Easy, 5 = Very difficult",
                key="exam_difficulty",
            )

            preparedness = st.slider(
                "Current preparation level",
                min_value=1,
                max_value=5,
                value=3,
                help="1 = Not prepared, 5 = Well prepared",
                key="exam_preparedness",
            )

            recommended_hours = calculate_recommended_hours(
                difficulty,
                preparedness,
            )

            st.info(
                f"Recommended preparation time: "
                f"{recommended_hours} hours"
            )

        # ---------- GENERATE STUDY PLAN ----------

        if st.button(
            "Generate Study Plan",
            key="generate_exam_study_plan",
        ):

            timetable_classes = st.session_state.get("classes", [])

            if not timetable_classes:

                st.warning(
                    "Please add or import your timetable first."
                )

            else:

                exam_date_value = selected_planner_exam["exam_date"]

                if isinstance(exam_date_value, str):
                    exam_date_value = date.fromisoformat(
                        exam_date_value
                    )

                result = generate_exam_study_plan(
                    classes=timetable_classes,
                    exam_date=exam_date_value,
                    exam_id=selected_planner_exam["id"],
                    course_id=selected_planner_exam.get("course_id"),
                    target_hours=target_hours,
                    difficulty=difficulty,
                    preparedness=preparedness,
                )

                if not result["sessions"]:

                    st.warning(
                        "No suitable study slots were found before "
                        "this exam. Check your timetable and exam date."
                    )

                else:

                    # Replace the previous plan for this exam.
                    delete_exam_study_sessions(
                        user_id,
                        selected_planner_exam["id"],
                    )

                    for session in result["sessions"]:

                        add_user_study_session(
                            user_id=user_id,
                            exam_id=session["exam_id"],
                            course_id=session["course_id"],
                            session_date=session["session_date"],
                            start_time=session["start_time"],
                            end_time=session["end_time"],
                            duration_minutes=session["duration_minutes"],
                        )

                    st.success("Study plan generated and saved!")

                    if result["unallocated_minutes"] > 0:

                        st.warning(
                            f"{result['unallocated_minutes'] // 60} "
                            f"hours and "
                            f"{result['unallocated_minutes'] % 60} "
                            f"minutes could not be allocated."
                        )

                    st.rerun()

    # ---------- VIEW SAVED STUDY SESSIONS ----------

    st.divider()
    st.subheader("Your Study Sessions")

    planner_sessions = get_user_study_sessions(user_id)

    if planner_sessions:

        course_lookup = {
            course["id"]: course["course_name"]
            for course in get_user_courses(user_id)
        }

        exam_lookup = {
            exam["id"]: exam["exam_title"]
            for exam in get_user_exams(user_id)
        }

        # Prepare readable session information.
        display_sessions = []

        for session in planner_sessions:

            display_sessions.append({
                "Exam": exam_lookup.get(
                    session["exam_id"],
                    "Exam unavailable"
                ),
                "Course": course_lookup.get(
                    session.get("course_id"),
                    "Course unavailable"
                ),
                "Date": session["session_date"],
                "Start Time": format_study_time(
                    session["start_time"]
                ),
                "End Time": format_study_time(
                    session["end_time"]
                ),
                "Duration": (
                    f"{session['duration_minutes']} minutes"
                ),
                "Status": session.get("status", "Planned"),
            })

        # Display the study schedule.
        st.dataframe(
            display_sessions,
            use_container_width=True,
            hide_index=True,
        )

        # Prepare session selection options.
        session_options = {
            (
                f"{session['session_date']} | "
                f"{format_study_time(session['start_time'])} - "
                f"{format_study_time(session['end_time'])} | "
                f"{exam_lookup.get(session['exam_id'], 'Exam')}"
            ): session
            for session in planner_sessions
        }

        selected_session_label = st.selectbox(
            "Select a study session to manage",
            list(session_options.keys()),
            key="manage_study_session",
        )

        selected_session = session_options[
            selected_session_label
        ]

        # ---------- UPDATE SESSION STATUS ----------

        status_options = [
            "Planned",
            "Completed",
            "Skipped",
        ]

        current_status = selected_session.get(
            "status",
            "Planned"
        )

        if current_status not in status_options:
            status_options.append(current_status)

        new_status = st.selectbox(
            "Update session status",
            status_options,
            index=status_options.index(current_status),
            key="study_session_status",
        )

        if st.button(
            "Update Session Status",
            key="update_study_session_status",
        ):

            update_study_session_status(
                user_id,
                selected_session["id"],
                new_status,
            )

            st.success("Study session status updated.")
            st.rerun()

        # ---------- DELETE SELECTED SESSION ----------

        if st.button(
            "Delete Selected Session",
            key="delete_study_session",
        ):

            delete_user_study_session(
                user_id,
                selected_session["id"],
            )

            st.success("Study session deleted.")
            st.rerun()

    else:

        st.info("No study sessions generated yet.")

except Exception as e:

    st.error(f"Could not load the Exam Study Planner: {e}")