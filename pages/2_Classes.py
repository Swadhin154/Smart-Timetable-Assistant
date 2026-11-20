import csv
import io
from datetime import date, datetime, time

import streamlit as st

from app_auth import get_current_user
from scheduling_logic import find_timetable_conflicts
from free_time_logic import find_free_slots
from study_recommendations import recommend_study_slots
from natural_language import understand_request
from google_calendar_web import (
    create_calendar_event,
    get_calendar_events,
    is_google_calendar_connected,
    start_google_oauth,
)


# ---------- PAGE CONFIGURATION ----------
st.set_page_config(
    page_title="Classes | Smart Timetable Assistant",
    page_icon="📚",
    layout="wide",
)

current_user = get_current_user()

if not current_user:
    st.warning("Please sign in from the main application.")
    st.stop()


# ---------- TIME FORMATTING ----------
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


DAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]


# ---------- SESSION STATE ----------
if "classes" not in st.session_state:
    st.session_state.classes = []

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

if "delete_mode" not in st.session_state:
    st.session_state.delete_mode = False


# ---------- PAGE HEADER ----------
st.title("Classes")
st.caption("Manage your timetable, find free time and connect Google Calendar.")


# ---------- ADD TIMETABLE ----------
st.header("Add Your Timetable")

option = st.selectbox(
    "How would you like to add your timetable?",
    [
        "Enter manually",
        "Upload a Timetable file",
        "Import from Google Calendar",
    ],
    key="classes_input_method",
)


# ---------- ADD CLASSES MANUALLY ----------
if option == "Enter manually":
    st.subheader("Add a class")

    with st.form("class_form"):
        semester = st.selectbox(
            "Semester",
            [f"Semester {i}" for i in range(1, 9)],
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
                and existing.get("subject", "").strip().casefold()
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
                    "No changes were made."
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

                        uploaded_classes.append({
                            "semester": csv_semester,
                            "subject": row["Subject"].strip(),
                            "Day": csv_day,
                            "Start Time": csv_start,
                            "End Time": csv_end,
                            "Teacher": row["Teacher"].strip(),
                            "Room": row["Room"].strip(),
                            "Source": "CSV",
                            "Date": None,
                        })

                    except (ValueError, AttributeError, KeyError):
                        invalid_rows.append(row_number)

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


st.divider()


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

    if selected_semester != "Select Semester" and semester_classes:

        csv_buffer = io.StringIO()

        csv_writer = csv.DictWriter(
            csv_buffer,
            fieldnames=[
                "subject",
                "Day",
                "Start Time",
                "End Time",
                "Teacher",
                "Room",
                "semester",
            ],
            extrasaction="ignore",
        )

        csv_writer.writeheader()

        for class_item in semester_classes:
            export_item = class_item.copy()

            export_item["Start Time"] = format_time_display(
                class_item.get("Start Time")
            )

            export_item["End Time"] = format_time_display(
                class_item.get("End Time")
            )

            csv_writer.writerow(export_item)

        st.download_button(
            label="📥 Export Timetable as CSV",
            data=csv_buffer.getvalue(),
            file_name=f"{selected_semester.replace(' ', '_')}_timetable.csv",
            mime="text/csv",
            key="export_semester_timetable",
        )

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
                    st.error("End time must be after start time.")

                else:
                    item.update({
                        "subject": edit_subject.strip(),
                        "Day": edit_day,
                        "Start Time": edit_start,
                        "End Time": edit_end,
                        "Teacher": edit_teacher.strip(),
                        "Room": edit_room.strip(),
                    })

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


# ---------- FIND FREE TIME ----------
with st.expander("🕒 Find Free Time", expanded=False):
    st.caption(
        "Find available periods between 6:00 AM and 7:00 PM."
    )

    selected_day_for_free_time = st.selectbox(
        "Choose a day",
        options=DAYS,
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


# ---------- STUDY TIME RECOMMENDATIONS ----------
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


# ---------- GOOGLE CALENDAR ----------
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