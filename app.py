import csv
import io
from datetime import date, datetime, time

import streamlit as st
from scheduling_logic import find_timetable_conflicts
from free_time_logic import find_free_slots
from study_recommendations import recommend_study_slots
from natural_language import understand_request
from deadline_logic import validate_deadline, get_deadline_status
from deadline_planner import prioritize_deadlines
from app_auth import sign_up, sign_in, sign_out, get_current_user
from academic_event_storage import (
    get_user_academic_events,
    add_user_academic_event,
    update_user_academic_event,
    delete_user_academic_event,
)
from course_storage import (
    get_user_courses,
    add_user_course,
    update_user_course,
    delete_user_course,
)
from exam_storage import (
    get_user_exams,
    add_user_exam,
    update_user_exam,
    delete_user_exam,
)
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
from google_calendar_web import (
    create_calendar_event,
    get_calendar_events,
    handle_google_oauth_callback,
    is_google_calendar_connected,
    start_google_oauth,
)
from academic_calendar import (
    get_indian_national_holidays,
    get_upcoming_holidays,
)
def format_time_display(value):
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


def format_study_time(value):
    """Maintain compatibility with existing study planner code."""
    return format_time_display(value)

DAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
]

st.set_page_config(
    page_title="Smart Timetable Assistant",
    page_icon="📅",
    layout="wide",
)

st.title("Smart Timetable Assistant")

# Handle Google's redirect BEFORE showing the login screen.
# The callback attempts to restore the app session securely.
handle_google_oauth_callback()
current_user = get_current_user()

# ---------- SIGN IN / SIGN UP ----------
if not current_user:
    st.subheader("Sign in or create an account")

    login_tab, signup_tab = st.tabs(["Sign In", "Sign Up"])

    with login_tab:
        with st.form("login_form"):
            login_email = st.text_input(
                "Email address",
                key="login_email",
            )
            login_password = st.text_input(
                "Password",
                type="password",
                key="login_password",
            )
            login_submitted = st.form_submit_button("Sign In")

        if login_submitted:
            try:
                response = sign_in(
                    login_email.strip(),
                    login_password,
                )

                if response.user:
                    st.success("Signed in successfully!")
                    st.rerun()
                else:
                    st.error(
                        "Sign-in failed. Please check your credentials."
                    )

            except Exception as e:
                st.error(f"sign-in error: {e}")

    with signup_tab:
        with st.form("signup_form"):
            signup_email = st.text_input(
                "Email address",
                key="signup_email",
            )
            signup_password = st.text_input(
                "Create password",
                type="password",
                key="signup_password",
            )
            signup_submitted = st.form_submit_button("Create Account")

        if signup_submitted:
            try:
                response = sign_up(
                    signup_email.strip(),
                    signup_password,
                )

                if response.user and response.session:
                    st.success("Account created and signed in!")
                    st.rerun()

                elif response.user:
                    st.success(
                        "Account created. Check your email to confirm "
                        "your account, then sign in."
                    )

            except Exception as e:
                st.error(f"Account creation error: {e}")

    st.stop()

# ---------- SIGNED-IN USER ----------
with st.sidebar:
    st.write(f"Signed in as *{current_user.email}*")

    if st.button("Sign Out"):
        sign_out()
        st.rerun()

if "classes" not in st.session_state:
    st.session_state.classes = []

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

if "delete_mode" not in st.session_state:
    st.session_state.delete_mode = False

st.write(
    "Organize your classes, assignments, exams, and study times "
    "in one place."
)
# ---------- COURSE MANAGEMENT ----------
st.header("Courses")

user_id = current_user.id

try:
    courses = get_user_courses(user_id)

    with st.expander("Add a New Course", expanded=False):
        with st.form("add_course_form"):
            course_name = st.text_input("Course Name")
            course_code = st.text_input("Course Code")

            course_semester = st.selectbox(
                "Semester",
                [f"Semester {i}" for i in range(1, 9)],
                key="course_semester",
            )

            course_credits = st.number_input(
                "Credits",
                min_value=0.0,
                max_value=30.0,
                value=0.0,
                step=0.5,
            )

            course_teacher = st.text_input("Teacher")

            add_course_submitted = st.form_submit_button(
                "Add Course"
            )

        if add_course_submitted:
            if not course_name.strip() or not course_code.strip():
                st.error(
                    "Please enter both course name and course code."
                )
            else:
                add_user_course(
                    user_id,
                    course_name,
                    course_code,
                    course_semester,
                    course_credits,
                    course_teacher,
                )

                st.success("Course added successfully!")
                st.rerun()

    st.subheader("My Courses")

    if courses:
        st.dataframe(
            courses,
            use_container_width=True,
            hide_index=True,
        )

        course_options = {
            (
                f"{course['course_code']} - "
                f"{course['course_name']} "
                f"({course['semester']})"
            ): course
            for course in courses
        }

        selected_course_label = st.selectbox(
            "Select a course to manage",
            list(course_options.keys()),
            key="manage_course_selection",
        )

        selected_course = course_options[selected_course_label]
        course_id = selected_course["id"]

        with st.expander("Edit Selected Course"):
            with st.form("edit_course_form"):
                edit_course_name = st.text_input(
                    "Course Name",
                    value=selected_course["course_name"],
                )

                edit_course_code = st.text_input(
                    "Course Code",
                    value=selected_course["course_code"],
                )

                semester_options = [
                    f"Semester {i}" for i in range(1, 9)
                ]

                current_semester = selected_course["semester"]

                semester_index = (
                    semester_options.index(current_semester)
                    if current_semester in semester_options
                    else 0
                )

                edit_course_semester = st.selectbox(
                    "Semester",
                    semester_options,
                    index=semester_index,
                    key="edit_course_semester",
                )

                edit_course_credits = st.number_input(
                    "Credits",
                    min_value=0.0,
                    max_value=30.0,
                    value=float(selected_course.get("credits") or 0),
                    step=0.5,
                    key="edit_course_credits",
                )

                edit_course_teacher = st.text_input(
                    "Teacher",
                    value=selected_course.get("teacher") or "",
                )

                update_course_submitted = st.form_submit_button(
                    "Update Course"
                )

            if update_course_submitted:
                if (
                    not edit_course_name.strip()
                    or not edit_course_code.strip()
                ):
                    st.error(
                        "Course name and course code are required."
                    )
                else:
                    update_user_course(
                        user_id,
                        course_id,
                        edit_course_name,
                        edit_course_code,
                        edit_course_semester,
                        edit_course_credits,
                        edit_course_teacher,
                    )

                    st.success("Course updated successfully!")
                    st.rerun()

        if st.button(
            "Delete Selected Course",
            key="delete_course_button",
        ):
            delete_user_course(user_id, course_id)
            st.success("Course deleted successfully!")
            st.rerun()

    else:
        st.info(
            "No courses added yet. Add your first course above."
        )

except Exception as e:
    st.error(f"Could not load or manage courses: {e}")
# ---------- EXAM MANAGEMENT ----------
st.header("Manage Exams")

try:
    courses = get_user_courses(user_id)
    exams = get_user_exams(user_id)

    if not courses:
        st.info(
            "Please add at least one course before scheduling an exam."
        )

    else:
        course_options = {
            (
                f"{course['course_code']} - "
                f"{course['course_name']} "
                f"({course['semester']})"
            ): course
            for course in courses
        }

        # ---------- ADD EXAM ----------
        with st.expander("Add a New Exam", expanded=False):
            with st.form("add_exam_form"):
                exam_title = st.text_input("Exam Title")

                selected_course_label = st.selectbox(
                    "Select Course",
                    list(course_options.keys()),
                    key="add_exam_course",
                )

                exam_date = st.date_input(
                    "Exam Date",
                    value=date.today(),
                    min_value=date.today(),
                    key="add_exam_date",
                )

                exam_type = st.selectbox(
                    "Exam Type",
                    [
                        "Mid-Semester",
                        "End-Semester",
                        "Internal",
                        "Practical",
                        "Other",
                    ],
                    key="add_exam_type",
                )

                include_exam_time = st.checkbox(
                    "Add exam timing",
                    key="include_exam_time",
                )

                exam_start_time = None
                exam_end_time = None

                if include_exam_time:
                    exam_start_time = st.time_input(
                        "Start Time",
                        value=time(9, 0),
                        key="add_exam_start",
                    )

                    exam_end_time = st.time_input(
                        "End Time",
                        value=time(12, 0),
                        key="add_exam_end",
                    )

                exam_location = st.text_input("Exam Location")
                exam_notes = st.text_area("Additional Notes")

                add_exam_submitted = st.form_submit_button(
                    "Add Exam"
                )

            if add_exam_submitted:
                selected_course = course_options[
                    selected_course_label
                ]

                if not exam_title.strip():
                    st.error("Please enter an exam title.")

                elif (
                    include_exam_time
                    and exam_start_time >= exam_end_time
                ):
                    st.error(
                        "End time must be after start time."
                    )

                else:
                    add_user_exam(
                        user_id=user_id,
                        course_id=selected_course["id"],
                        exam_title=exam_title,
                        exam_date=exam_date,
                        start_time=exam_start_time,
                        end_time=exam_end_time,
                        exam_type=exam_type,
                        location=exam_location,
                        notes=exam_notes,
                    )

                    st.success("Exam added successfully!")
                    st.rerun()

        # ---------- VIEW EXAMS ----------
        st.subheader("Upcoming and Scheduled Exams")

        if exams:
            course_lookup = {
                course["id"]: course
                for course in courses
            }

            display_exams = []

            for exam in exams:
                linked_course = course_lookup.get(
                    exam.get("course_id")
                )

                display_exams.append(
                    {
                        "Exam": exam["exam_title"],
                        "Course": (
                            linked_course["course_name"]
                            if linked_course
                            else "Course unavailable"
                        ),
                        "Semester": (
                            linked_course["semester"]
                            if linked_course
                            else "—"
                        ),
                        "Date": exam["exam_date"],
                        "Type": exam.get("exam_type") or "Final",
                        "Start Time": format_time_display(exam.get("start_time")),
                        "End Time": format_time_display(exam.get("end_time")),
                        "Location": exam.get("location") or "—",
                    }
                )

            st.dataframe(
                display_exams,
                use_container_width=True,
                hide_index=True,
            )

            # ---------- SELECT EXAM ----------
            exam_options = {
                (
                    f"{exam['exam_title']} - "
                    f"{exam['exam_date']}"
                ): exam
                for exam in exams
            }

            selected_exam_label = st.selectbox(
                "Select an exam to manage",
                list(exam_options.keys()),
                key="manage_exam_selection",
            )

            selected_exam = exam_options[selected_exam_label]

            # ---------- EDIT EXAM ----------
            with st.expander("Edit Selected Exam"):
                with st.form("edit_exam_form"):
                    edit_exam_title = st.text_input(
                        "Exam Title",
                        value=selected_exam["exam_title"],
                    )

                    current_course_label = next(
                        (
                            label
                            for label, course in course_options.items()
                            if course["id"] == selected_exam.get(
                                "course_id"
                            )
                        ),
                        list(course_options.keys())[0],
                    )

                    course_labels = list(course_options.keys())

                    edit_course_label = st.selectbox(
                        "Course",
                        course_labels,
                        index=course_labels.index(
                            current_course_label
                        ),
                        key="edit_exam_course",
                    )

                    edit_exam_date = st.date_input(
                        "Exam Date",
                        value=date.fromisoformat(
                            selected_exam["exam_date"]
                        ),
                        key="edit_exam_date",
                    )

                    exam_types = [
                        "Mid-Semester",
                        "End-Semester",
                        "Internal",
                        "Practical",
                        "Other",
                    ]

                    current_type = (
                        selected_exam.get("exam_type") or "Final"
                    )

                    if current_type not in exam_types:
                        exam_types.append(current_type)

                    edit_exam_type = st.selectbox(
                        "Exam Type",
                        exam_types,
                        index=exam_types.index(current_type),
                        key="edit_exam_type",
                    )

                    edit_exam_location = st.text_input(
                        "Exam Location",
                        value=selected_exam.get("location") or "",
                    )

                    edit_exam_notes = st.text_area(
                        "Additional Notes",
                        value=selected_exam.get("notes") or "",
                    )

                    update_exam_submitted = st.form_submit_button(
                        "Update Exam"
                    )

                if update_exam_submitted:
                    updated_course = course_options[
                        edit_course_label
                    ]

                    update_user_exam(
                        user_id=user_id,
                        exam_id=selected_exam["id"],
                        course_id=updated_course["id"],
                        exam_title=edit_exam_title,
                        exam_date=edit_exam_date,
                        start_time=(
                            time.fromisoformat(
                                selected_exam["start_time"]
                            )
                            if selected_exam.get("start_time")
                            else None
                        ),
                        end_time=(
                            time.fromisoformat(
                                selected_exam["end_time"]
                            )
                            if selected_exam.get("end_time")
                            else None
                        ),
                        exam_type=edit_exam_type,
                        location=edit_exam_location,
                        notes=edit_exam_notes,
                    )

                    st.success("Exam updated successfully!")
                    st.rerun()

            # ---------- DELETE EXAM ----------
            if st.button(
                "Delete Selected Exam",
                key="delete_exam_button",
            ):
                delete_user_exam(
                    user_id,
                    selected_exam["id"],
                )

                st.success("Exam deleted successfully!")
                st.rerun()

        else:
            st.info(
                "No exams scheduled yet. Add your first exam above."
            )

except Exception as e:
    st.error(f"Could not load or manage exams: {e}")

 # ---------- EXAM STUDY PLANNER ----------

st.divider()
st.header("Exam Study Planner")

try:
    planner_exams = get_user_exams(user_id)
    planner_sessions = get_user_study_sessions(user_id)

    if not planner_exams:
        st.info("Add an exam in Manage Exams before creating a study plan.")

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

        # Update session status.
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

        # Delete selected session.
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

# ---------- END EXAM STUDY PLANNER ----------       
    
st.header("Add Your Timetable")

option = st.selectbox(
    "How would you like to add your timetable?",
    [
        "Enter manually",
        "Upload a Timetable file",
        "Import from Google Calendar",
    ],
)

# ---------------- INDIAN NATIONAL HOLIDAY CALENDAR ----------------

st.divider()
st.header("Academic Calendar and Holidays")


calendar_view = st.radio(
    "Choose calendar view",
    ["Upcoming Holidays", "All Holidays"],
    horizontal=True,
    key="national_holiday_view",
)

all_holidays = get_indian_national_holidays(2026)

if calendar_view == "Upcoming Holidays":
    holiday_events = get_upcoming_holidays(
        2026,
        today=date.today(),
    )
else:
    holiday_events = all_holidays

if holiday_events:
    display_holidays = []

    for holiday in holiday_events:
        display_holidays.append({
            "Holiday": holiday["Event"],
            "Date": holiday["Date"].strftime("%d %B %Y"),
            "Day": holiday["Day"],
            "Category": holiday["Category"],
        })

    st.dataframe(
        display_holidays,
        width="stretch",
        hide_index=True,
    )

    
else:
    st.info("No upcoming holidays remaining in the 2026 calendar.")

academic_calendar_user_id = st.session_state.get("supabase_user_id")

# Add a new academic event
with st.expander("➕ Add Academic Event", expanded=False):

    with st.form("add_academic_event_form"):

        event_title = st.text_input(
            "Event Title",
            placeholder="e.g. Physics Internal Examination",
        )

        event_date = st.date_input(
            "Event Date",
            value=date.today(),
        )

        event_type = st.selectbox(
            "Event Type",
            [
                "Semester Start",
                "Semester End",
                "Internal Examination",
                "Practical Examination",
                "Assignment",
                "Project",
                "College Event",
                "Semester Break",
                "Other",
            ],
        )

        event_description = st.text_area(
            "Description",
            placeholder="Add any additional details...",
        )

        add_event_button = st.form_submit_button(
            "Save Academic Event",
            use_container_width=True,
        )

        if add_event_button:

            if not event_title.strip():
                st.error("Please enter an event title.")

            else:
                try:
                    add_user_academic_event(
                        academic_calendar_user_id,
                        event_title,
                        event_date,
                        event_type,
                        event_description,
                    )

                    st.success("Academic event added successfully!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Could not add event: {e}")


# Display saved academic events
try:
    academic_events = get_user_academic_events(
        academic_calendar_user_id
    )

    if academic_events:

        st.markdown("*Your Academic Events*")

        display_academic_events = []

        for event in academic_events:
            display_academic_events.append({
                "Event": event["event_title"],
                "Date": date.fromisoformat(
                    str(event["event_date"])[:10]
                ).strftime("%d %B %Y"),
                "Type": event["event_type"],
                "Description": event.get("description", ""),
            })

        st.dataframe(
            display_academic_events,
            width="stretch",
            hide_index=True,
        )

        # Select an event to edit or delete
        event_options = {
            (
                f"{event['id']} | {event['event_title']} | "
                f"{str(event['event_date'])[:10]}"
            ): event
            for event in academic_events
        }

        selected_event_label = st.selectbox(
            "Select an event to manage",
            list(event_options.keys()),
            key="manage_academic_event",
        )

        selected_event = event_options[selected_event_label]

        st.markdown("*Edit Selected Event*")

        with st.form("edit_academic_event_form"):

            edit_title = st.text_input(
                "Event Title",
                value=selected_event["event_title"],
            )

            edit_date = st.date_input(
                "Event Date",
                value=date.fromisoformat(
                    str(selected_event["event_date"])[:10]
                ),
            )

            event_type_options = [
                "Semester Start",
                "Semester End",
                "Internal Examination",
                "Practical Examination",
                "Assignment",
                "Project",
                "College Event",
                "Semester Break",
                "Other",
            ]

            current_event_type = selected_event["event_type"]

            if current_event_type not in event_type_options:
                event_type_options.append(current_event_type)

            edit_type = st.selectbox(
                "Event Type",
                event_type_options,
                index=event_type_options.index(current_event_type),
            )

            edit_description = st.text_area(
                "Description",
                value=selected_event.get("description", ""),
            )

            update_event_button = st.form_submit_button(
                "Update Event",
                use_container_width=True,
            )

            if update_event_button:

                if not edit_title.strip():
                    st.error("Event title cannot be empty.")

                else:
                    try:
                        update_user_academic_event(
                            academic_calendar_user_id,
                            selected_event["id"],
                            edit_title,
                            edit_date,
                            edit_type,
                            edit_description,
                        )

                        st.success("Academic event updated successfully!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Could not update event: {e}")

        # Delete selected event
        if st.button(
            "🗑️ Delete Selected Event",
            key="delete_academic_event_button",
            type="secondary",
        ):

            try:
                delete_user_academic_event(
                    academic_calendar_user_id,
                    selected_event["id"],
                )

                st.success("Academic event deleted successfully!")
                st.rerun()

            except Exception as e:
                st.error(f"Could not delete event: {e}")

    else:
        st.info("No personal academic events added yet.")

except Exception as e:
    st.error(f"Could not load academic events: {e}")    

# ---------- ADD CLASSES MANUALLY ----------
if option == "Enter manually":
    st.subheader("Add a class")

    with st.form("class_form"):
        semester = st.selectbox(
        "Semester",
        [f"Semester {i}" for i in range(1, 9)]
    )
        subject = st.text_input("Subject")
        day = st.selectbox("Day", DAYS)

        start_time = st.time_input(
            "Start time",
            format="12h",
            key="manual_start_time",
        )
        end_time = st.time_input(
            "End time",
            format="12h",
            key="manual_end_time",
        )

        teacher = st.text_input("Teacher")
        room = st.text_input("Room")

        submitted = st.form_submit_button("Add Class")

    if submitted:
        if not subject.strip():
            st.error("Please enter a subject.")

        elif start_time >= end_time:
            st.error("End time must be after start time.")

        else:
            new_class = {
                "semester": semester,
                "subject": subject.strip(),
                "Day": day,
                "Start Time": start_time,
                "End Time": end_time,
                "Teacher": teacher.strip(),
                "Room": room.strip(),
                "Source": "Manual",
                "Date": None,
            }

            duplicate_exists = any(
                existing.get("semester") == new_class["semester"]
                and
                existing.get("subject", "").strip().casefold()
                == new_class["subject"].casefold()
                and existing.get("Day") == new_class["Day"]
                and existing.get("Start Time") == new_class["Start Time"]
                and existing.get("End Time") == new_class["End Time"]
                and existing.get("Teacher", "").strip().casefold()
                == new_class["Teacher"].casefold()
                and existing.get("Room", "").strip().casefold()
                == new_class["Room"].casefold()
                for existing in st.session_state.classes
            )

            if duplicate_exists:
                st.warning(
                    "This class is already in your timetable. "
                    "No Changes were made."
                )
            else:
                st.session_state.classes.append(new_class)
                st.success("Class added successfully!")

# ---------- UPLOAD TIMETABLE CSV ----------
elif option == "Upload a Timetable file":
    st.subheader("Upload Your Timetable")

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        key="timetable_csv",
    )

    if uploaded_file is not None:
        try:
            text = uploaded_file.getvalue().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))

            required = [
                "Subject",
                "Day",
                "Start Time",
                "End Time",
                "Teacher",
                "Room",
            ]

            if (
                not reader.fieldnames
                or not all(column in reader.fieldnames for column in required)
            ):
                st.error(
                    "CSV must contain: Subject, Day, Start Time, "
                    "End Time, Teacher, Room."
                )

            else:
                uploaded_classes = []
                invalid_rows = []

                # Process every CSV row first.
                for row_number, row in enumerate(reader, start=2):
                    try:
                        csv_day = row["Day"].strip().capitalize()

                        csv_start = datetime.strptime(
                            row["Start Time"].strip(),
                            "%H:%M",
                        ).time()

                        csv_end = datetime.strptime(
                            row["End Time"].strip(),
                            "%H:%M",
                        ).time()

                        csv_semester = (
                            row.get("Semester", "Semester 1").strip()
                            or "Semester 1"
                        )

                        if (
                            csv_day not in DAYS
                            or csv_start >= csv_end
                            or not row["Subject"].strip()
                            or csv_semester not in [
                                f"Semester {i}" for i in range(1, 9)
                            ]
                        ):
                            raise ValueError("Invalid timetable row")

                        uploaded_classes.append(
                            {
                                "semester": csv_semester,
                                "subject": row["Subject"].strip(),
                                "Day": csv_day,
                                "Start Time": csv_start,
                                "End Time": csv_end,
                                "Teacher": row["Teacher"].strip(),
                                "Room": row["Room"].strip(),
                                "Source": "CSV",
                                "Date": None,
                            }
                        )

                    except (ValueError, AttributeError, KeyError):
                        invalid_rows.append(row_number)

                # Show the preview only once, after processing all rows.
                if uploaded_classes:
                    st.write("Preview")
                    st.dataframe(
                        uploaded_classes,
                        use_container_width=True,
                    )

                    if st.button(
                        "Add CSV classes to timetable",
                        key="csv_import_confirm_button_v3",
                    ):
                        st.session_state.classes.extend(uploaded_classes)

                        st.success(
                            f"Added {len(uploaded_classes)} class(es)."
                        )

                        if invalid_rows:
                            st.warning(
                                "Skipped invalid CSV row(s): "
                                + ", ".join(map(str, invalid_rows))
                            )

                        st.rerun()

                elif invalid_rows:
                    st.error(
                        "No valid rows found. Check CSV row(s): "
                        + ", ".join(map(str, invalid_rows))
                    )

        except UnicodeDecodeError:
            st.error(
                "Could not read the CSV. Save it as UTF-8 and upload again."
            )

# ---------- GOOGLE CALENDAR IMPORT OPTION ----------
else:
    st.subheader("Import from Google Calendar")
    st.caption(
        "Use the Import Google Calendar Events button below to bring "
        "upcoming timed events into your timetable."
    )

# ---------- TIMETABLE DISPLAY ----------
if st.session_state.classes:
    conflicts = find_timetable_conflicts(st.session_state.classes)

    if conflicts:
        st.warning(
            f"⚠️ Found {len(conflicts)} timetable clash(es). "
            "Please review the conflicting classes below."
        )
        st.dataframe(
            conflicts,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No timetable clashes detected.")

    # ---------- MY TIMETABLE ----------
    st.subheader("My Timetable")

    selected_semester = st.selectbox(
        "Select Semester",
        ["Select Semester"] + [
            f"Semester {i}" for i in range(1, 9)
        ],
        key="semester_timetable_filter",
    )

    semester_classes = [
        item
        for item in st.session_state.classes
        if item.get("semester", "Semester 1") == selected_semester
    ]

    if selected_semester != "Select Semester":
        st.dataframe(
            semester_classes,
            use_container_width=True,
            hide_index=True,
        )

        selected_day = st.selectbox(
            "View timetable for a day",
            DAYS,
            key="daily_timetable_day",
        )

        day_classes = [
            item
            for item in semester_classes
            if item.get("Day") == selected_day
        ]

        if day_classes:
            display_day_classes = []

            for item in day_classes:
                formatted_item = item.copy()
                formatted_item["Start Time"] = format_time_display(
                    item.get("Start Time")
                )
                formatted_item["End Time"] = format_time_display(
                    item.get("End Time")
                )
                display_day_classes.append(formatted_item)

            st.dataframe(
                display_day_classes,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(f"No classes scheduled for {selected_day}.")
    
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Edit Classes"):
            st.session_state.edit_mode = not st.session_state.edit_mode
            st.session_state.delete_mode = False

    with col2:
        if st.button("Delete Classes"):
            st.session_state.delete_mode = not st.session_state.delete_mode
            st.session_state.edit_mode = False

    class_options = [
    (
        f"{i + 1}. {item.get('subject', 'Untitled')} - "
        f"{item.get('Day', '?')} "
        f"{format_time_display(item.get('Start Time'))} - "
        f"{format_time_display(item.get('End Time'))}"
    )
    for i, item in enumerate(st.session_state.classes)
]

    # ---------- EDIT CLASSES ----------
    if st.session_state.edit_mode:
        selected_edit = st.selectbox(
            "Select a class to edit",
            ["Select a class"] + class_options,
            key="edit_class_selection",
        )

        if selected_edit != "Select a class":
            idx = class_options.index(selected_edit)
            item = st.session_state.classes[idx]

            with st.form(f"edit_form_{idx}"):
                edit_subject = st.text_input(
                    "Subject",
                    value=item.get("subject", ""),
                )

                old_day = item.get("Day", "Monday")
                day_index = DAYS.index(old_day) if old_day in DAYS else 0

                edit_day = st.selectbox(
                    "Day",
                    DAYS,
                    index=day_index,
                )

                edit_start = st.time_input(
                    "Start time",
                    value=item["Start Time"],
                    key=f"edit_start_{idx}",
                )

                edit_end = st.time_input(
                    "End time",
                    value=item["End Time"],
                    key=f"edit_end_{idx}",
                )

                edit_teacher = st.text_input(
                    "Teacher",
                    value=item.get("Teacher", ""),
                )

                edit_room = st.text_input(
                    "Room",
                    value=item.get("Room", ""),
                )

                save_edit = st.form_submit_button("Update Class")

            if save_edit:
                if not edit_subject.strip():
                    st.error("Please enter a subject.")

                elif edit_start >= edit_end:
                    st.error(
                        "End time must be after start time."
                    )

                else:
                    # Preserve source and event metadata.
                    item.update(
                        {
                            "subject": edit_subject.strip(),
                            "Day": edit_day,
                            "Start Time": edit_start,
                            "End Time": edit_end,
                            "Teacher": edit_teacher.strip(),
                            "Room": edit_room.strip(),
                        }
                    )

                    st.success("Class updated successfully.")
                    st.rerun()

    # ---------- DELETE CLASSES ----------
    if st.session_state.delete_mode:
        delete_choice = st.radio(
            "Choose a delete option",
            ["Delete one class", "Delete all classes"],
            key="delete_action",
        )

        if delete_choice == "Delete one class":
            selected_delete = st.selectbox(
                "Select the class to delete",
                ["Select a class"] + class_options,
                key="delete_class_selection",
            )

            if (
                selected_delete != "Select a class"
                and st.button("Delete Selected Class", key="confirm_delete")
            ):
                delete_index = class_options.index(selected_delete)
                del st.session_state.classes[delete_index]

                st.success("Class deleted.")
                st.rerun()

        else:
            confirmed = st.checkbox(
                "I confirm that I want to delete all classes.",
                key="confirm_delete_all_checkbox",
            )

            if st.button("Delete All Classes", key="delete_all_classes"):
                if confirmed:
                    st.session_state.classes = []
                    st.session_state.edit_mode = False
                    st.session_state.delete_mode = False

                    st.success("All classes deleted.")
                    st.rerun()
                else:
                    st.warning(
                        "Please confirm before deleting all classes."
                    )

else:
    st.info(
        "Your timetable is empty. Add a class, upload a CSV, "
        "or import from Google Calendar."
    )

with st.expander("🕒 Find Free Time", expanded=False):
    st.caption(
        "Find available periods between 6:00 AM and 7:00 PM."
    )

    selected_day_for_free_time = st.selectbox(
        "Choose a day",
        options=[
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ],
        key="free_time_selected_day",
    )

    min_duration = st.selectbox(
        "Minimum available duration",
        options=[5, 10, 15, 30, 45, 60],
        index=3,
        format_func=lambda minutes: f"{minutes} minutes",
        key="free_time_min_duration",
    )

    free_slots = find_free_slots(
        st.session_state.classes,
        selected_day_for_free_time,
        start_time="06:00",
        end_time="19:00",
        min_duration_minutes=min_duration,
    )

    if free_slots:
        display_slots = []

        for slot in free_slots:
            total_minutes = slot["Duration (minutes)"]
            hours, minutes = divmod(total_minutes, 60)

            if hours and minutes:
                duration_text = f"{hours} hr {minutes} min"
            elif hours:
                duration_text = f"{hours} hr"
            else:
                duration_text = f"{minutes} min"

            display_slots.append({
                "Start Time": slot["Start Time"],
                "End Time": slot["End Time"],
                "Available Duration": duration_text,
            })

        st.dataframe(
            display_slots,
            width="stretch",
            hide_index=True,
        )

    else:
        st.info(
            f"No free periods of {min_duration} minutes or longer "
            f"found on {selected_day_for_free_time} "
            f"between 6:00 AM and 7:00 PM."
        )
with st.expander("📚 Study Time Recommendations", expanded=False):
    st.caption(
        "Identify the longest available study periods "
        "based on your timetable."
    )

    recommendation_day = st.selectbox(
        "Select a day",
        options=DAYS,
        key="study_recommendation_day",
    )

    recommendations = recommend_study_slots(
        st.session_state.classes,
        recommendation_day,
        min_duration_minutes=30,
        max_recommendations=3,
        start_time="06:00",
        end_time="19:00",
    )

    if recommendations:
        st.dataframe(
            recommendations,
            width="stretch",
            hide_index=True,
        )

        st.caption(
            "Recommendations are ranked by available duration, "
            "with the longest study periods shown first."
        )
    else:
        st.info(
            f"No study period of at least 30 minutes is available "
            f"on {recommendation_day} between 6:00 AM and 7:00 PM."
        )
# ---------- ASK YOUR TIMETABLE ----------
with st.expander("💬 Ask Your Timetable", expanded=False):
   

    user_request = st.text_input(
        "What would you like to know?",
        placeholder="e.g. Show study periods on Sunday",
        key="natural_language_request",
    )

    if st.button("Ask", key="ask_timetable_button"):
        result = understand_request(user_request)

        if result["error"]:
            st.warning(result["error"])

        else:
            requested_action = result["action"]
            requested_day = result["day"]
            timetable = st.session_state.classes

            if requested_action == "find_free_time":
                free_slots = find_free_slots(
                    timetable,
                    requested_day,
                    start_time="06:00",
                    end_time="19:00",
                    min_duration_minutes=30,
                )

                st.subheader(f"Free Time — {requested_day}")

                if free_slots:
                    display_slots = []

                    for slot in free_slots:
                        total_minutes = slot["Duration (minutes)"]
                        hours, minutes = divmod(total_minutes, 60)

                        if hours and minutes:
                            duration_text = f"{hours} hr {minutes} min"
                        elif hours:
                            duration_text = f"{hours} hr"
                        else:
                            duration_text = f"{minutes} min"

                        display_slots.append({
                            "Start Time": slot["Start Time"],
                            "End Time": slot["End Time"],
                            "Available Duration": duration_text,
                        })

                    st.dataframe(
                        display_slots,
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.info(
                        f"No free period of at least 30 minutes "
                        f"was found on {requested_day}."
                    )

            elif requested_action == "study_recommendations":
                recommendations = recommend_study_slots(
                    timetable,
                    requested_day,
                    min_duration_minutes=30,
                    max_recommendations=3,
                    start_time="06:00",
                    end_time="19:00",
                )

                st.subheader(
                    f"Study Time Recommendations — {requested_day}"
                )

                if recommendations:
                    st.dataframe(
                        recommendations,
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.info(
                        f"No study period of at least 30 minutes "
                        f"was found on {requested_day}."
                    )

            elif requested_action == "check_conflicts":
                all_conflicts = find_timetable_conflicts(timetable)

                day_conflicts = [
                    conflict
                    for conflict in all_conflicts
                    if str(conflict.get("Day", "")).casefold()
                    == requested_day.casefold()
                ]

                st.subheader(f"Timetable Clashes — {requested_day}")

                if day_conflicts:
                    st.dataframe(
                        day_conflicts,
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.success(
                        f"No timetable clashes were found "
                        f"on {requested_day}."
                    )
# ---------- GOOGLE CALENDAR CONNECTION STATUS ----------
st.divider()
st.subheader("Google Calendar")
connected = is_google_calendar_connected()

if st.session_state.pop("google_calendar_just_connected", False):
    st.toast("Google Calendar connected successfully!", icon="✅")

if connected:
    st.caption("🟢 Connected to Google Calendar")
else:
    st.info(
        "Connect your calendar to import events "
        "or create events from your timetable."
    )
    if st.button("Connect Google Calendar", key="connect_google_calendar"):
        start_google_oauth()


# ---------- GOOGLE CALENDAR EVENT SCHEDULING ----------
# Create an event directly in Google Calendar.
st.subheader("Schedule an Event in Google Calendar")

with st.form("create_google_event_form"):
    event_subject = st.text_input(
        "Event title",
        key="one_time_event_title",
    )

    event_date = st.date_input(
        "Event date",
        value=date.today(),
        key="one_time_event_date",
    )

    event_start = st.time_input(
        "Start time",
        format="12h",
        key="google_event_start",
    )

    event_end = st.time_input(
        "End time",
        format="12h",
        key="google_event_end",
    )

    create_submitted = st.form_submit_button("Create Event")

if create_submitted:
    if not connected:
        st.error("Connect Google Calendar first.")

    elif not event_subject.strip():
        st.error("Please enter an event title.")

    elif event_start >= event_end:
        st.error("End time must be after start time.")

    else:
        try:
            created = create_calendar_event(
                event_subject.strip(),
                event_date,
                event_start,
                event_end,
            )

            st.success(
                "Event created successfully: "
                f"{created.get('summary', event_subject)}"
            )

        except Exception as exc:
            st.error(
                "Could not create the event: "
                f"{type(exc)._name_}: {exc}"
            )

# ---------- IMPORT GOOGLE CALENDAR EVENTS ----------
if st.button(
    "Import Google Calendar Events",
    key="import_google_events",
):
    if not connected:
        st.error("Connect Google Calendar first.")

    else:
        try:
            imported = get_calendar_events()

            existing_ids = {
                item.get("Google Event ID")
                for item in st.session_state.classes
                if item.get("Google Event ID")
            }

            new_items = [
                item
                for item in imported
                if item.get("Google Event ID") not in existing_ids
            ]

            if new_items:
                st.session_state.classes.extend(new_items)

                st.success(
                    f"Imported {len(new_items)} new event(s)."
                )
                st.rerun()

            else:
                st.info(
                    "No new timed events found in Google Calendar."
                )

        except Exception as exc:
            st.error(
                "Could not import Google Calendar events: "
                f"{type(exc)._name_}: {exc}"
            )

           # ---------------- DEADLINE MANAGER ----------------

from deadline_storage import (
    get_user_deadlines,
    add_user_deadline,
    delete_user_deadline,
)

st.divider()
st.header("📅 Assignment & Exam Deadlines")

current_user_id = st.session_state.get("supabase_user_id")

if not current_user_id:
    st.warning("Please sign in to manage your deadlines.")
else:
    with st.form("add_deadline_form"):
        task_title = st.text_input(
            "Assignment or exam name",
            key="deadline_title",
        )

        due_date = st.date_input(
            "Due date",
            value=date.today(),
            key="deadline_due_date",
        )

        estimated_hours = st.number_input(
            "Estimated preparation hours",
            min_value=0.5,
            max_value=500.0,
            value=2.0,
            step=0.5,
            key="deadline_estimated_hours",
        )

        priority = st.selectbox(
            "Priority",
            ["Low", "Medium", "High"],
            index=1,
            key="deadline_priority",
        )
        reminder_enabled = st.checkbox(
            "Enable email reminder",
            value=False,
            key="deadline_reminder_enabled",
        )

        reminder_date = st.date_input(
            "Reminder date",
            value=date.today(),
            key="deadline_reminder_date",
        )

        reminder_time = st.time_input(
            "Reminder time",
            value=time(9, 0),
            format="12h",
            key="deadline_reminder_time",
        )

        submitted = st.form_submit_button("Add Deadline")

    if submitted:
        is_valid, message = validate_deadline(
            task_title,
            due_date,
            estimated_hours,
            priority,
        )

        if is_valid:
                try:
                    reminder_at = None

                    if reminder_enabled:
                        reminder_at = datetime.combine(
                            reminder_date,
                            reminder_time,
                            tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Kolkata"),
                        ).isoformat()

                    add_user_deadline(
                        current_user_id,
                        task_title.strip(),
                        due_date,
                        estimated_hours,
                        priority,
                        reminder_at=reminder_at,
                        reminder_enabled=reminder_enabled,
                    )

                    st.success("Deadline saved successfully.")
                    st.rerun()

                except Exception as exc:
                    st.error(f"Could not save deadline: {exc}")

        else:
                st.error(message)

    st.subheader("Your Deadlines")

    try:
        deadlines = get_user_deadlines(current_user_id)
        if deadlines:
            st.subheader("🎯 Smart Assignment Priorities")

            ranked_deadlines = prioritize_deadlines(
                deadlines,
                today=date.today(),
            )

            if ranked_deadlines:
                total_hours = sum(
                    task["estimated_hours"]
                    for task in ranked_deadlines
                )

                st.metric(
                    "Total Pending Preparation Hours",
                    f"{total_hours:.1f} hours",
                )

                top_task = ranked_deadlines[0]

                st.success(
                    f"Recommended to work on first: "
                    f"{top_task['title']} "
                    f"(Score: {top_task['priority_score_total']}/100)"
                )

                for index, task in enumerate(
                    ranked_deadlines,
                    start=1,
                ):
                    with st.container(border=True):
                        st.write(
                            f"*{index}. {task['title']}*"
                        )

                        st.write(
                            f"Recommendation: {task['recommendation']}"
                        )

                        st.write(
                            f"Deadline: {task['status']}"
                        )

                        st.write(
                            f"Selected priority: {task['priority']}"
                        )

                        st.write(
                            f"Preparation: "
                            f"{task['estimated_hours']} hours"
                        )

                        st.progress(
                            task["priority_score_total"] / 100
                        )

                        st.caption(
                            f"Priority score: "
                            f"{task['priority_score_total']}/100"
                        )

        if deadlines:
            today = date.today()

            for deadline in deadlines:
                deadline_id = deadline["id"]
                deadline_date = date.fromisoformat(
                    deadline["due_date"]
                )

                status_info = get_deadline_status(
                    deadline_date,
                    today=today,
                )

                days_remaining = status_info["days_remaining"]

                if days_remaining < 0:
                    timing = (
                        f"Overdue by {abs(days_remaining)} day(s)"
                    )
                elif days_remaining == 0:
                    timing = "Due today"
                else:
                    timing = f"{days_remaining} day(s) remaining"

                with st.container(border=True):
                    st.markdown(f"*{deadline['title']}*")
                    st.write(f"Due date: {deadline_date}")
                    st.write(f"Status: {timing}")
                    st.write(
                        f"Preparation time: "
                        f"{deadline['estimated_hours']} hour(s)"
                    )
                    st.write(f"Priority: {deadline['priority']}")

                    if st.button(
                        "Delete Deadline",
                        key=f"delete_deadline_{deadline_id}",
                    ):
                        try:
                            delete_user_deadline(
                                current_user_id,
                                deadline_id,
                            )
                            st.success("Deadline deleted.")
                            st.rerun()
                        except Exception as exc:
                            st.error(
                                f"Could not delete deadline: {exc}"
                            )
        else:
            st.info("No deadlines added yet.")

    except Exception as exc:
        st.error(f"Could not load deadlines: {exc}")