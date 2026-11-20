import csv
import io
from datetime import date, datetime, time

import streamlit as st

from app_auth import get_current_user

from course_storage import get_user_courses

from exam_storage import (
    get_user_exams,
    add_user_exam,
    update_user_exam,
    delete_user_exam,
)


# ---------- PAGE CONFIGURATION ----------

st.set_page_config(
    page_title="Exams | Smart Timetable Assistant",
    page_icon="📝",
    layout="wide",
)


# ---------- HELPER FUNCTION ----------

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


# ---------- USER AUTHENTICATION ----------

current_user = get_current_user()

if not current_user:
    st.warning("Please sign in from the main application.")
    st.stop()

user_id = current_user.id


# ---------- EXAM MANAGEMENT ----------

st.title("Manage Exams")

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
                        "Start Time": format_time_display(
                            exam.get("start_time")
                        ),
                        "End Time": format_time_display(
                            exam.get("end_time")
                        ),
                        "Location": exam.get("location") or "—",
                    }
                )

            st.dataframe(
                display_exams,
                use_container_width=True,
                hide_index=True,
            )

            # ---------- EXPORT EXAM SCHEDULE ----------

            exam_csv_buffer = io.StringIO()

            exam_csv_writer = csv.DictWriter(
                exam_csv_buffer,
                fieldnames=[
                    "Exam",
                    "Course",
                    "Semester",
                    "Date",
                    "Type",
                    "Start Time",
                    "End Time",
                    "Location",
                ],
            )

            exam_csv_writer.writeheader()

            for exam_row in display_exams:

                export_exam = exam_row.copy()

                export_exam["Start Time"] = format_time_display(
                    exam_row.get("Start Time")
                )

                export_exam["End Time"] = format_time_display(
                    exam_row.get("End Time")
                )

                exam_csv_writer.writerow(export_exam)

            st.download_button(
                label="📥 Export Exam Schedule as CSV",
                data=exam_csv_buffer.getvalue(),
                file_name="exam_schedule.csv",
                mime="text/csv",
                key="export_exam_schedule",
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