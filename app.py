import csv
import io
from datetime import date, datetime

import streamlit as st

from app_auth import sign_up, sign_in, sign_out, get_current_user
from google_calendar_web import (
    create_calendar_event,
    get_calendar_events,
    handle_google_oauth_callback,
    is_google_calendar_connected,
    start_google_oauth,
)

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

st.header("Add Your Timetable")

option = st.selectbox(
    "How would you like to add your timetable?",
    [
        "Enter manually",
        "Upload a Timetable file",
        "Import from Google Calendar",
    ],
)

# ---------- ADD CLASSES MANUALLY ----------
if option == "Enter manually":
    st.subheader("Add a class")

    with st.form("class_form"):
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
            st.session_state.classes.append(
                {
                    "subject": subject.strip(),
                    "Day": day,
                    "Start Time": start_time,
                    "End Time": end_time,
                    "Teacher": teacher.strip(),
                    "Room": room.strip(),
                    "Source": "Manual",
                    "Date": None,
                }
            )

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

                        if (
                            csv_day not in DAYS
                            or csv_start >= csv_end
                            or not row["Subject"].strip()
                        ):
                            raise ValueError("Invalid timetable row")

                        uploaded_classes.append(
                            {
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

                if uploaded_classes:
                    st.write("Preview")
                    st.dataframe(
                        uploaded_classes,
                        use_container_width=True,
                    )

                    if st.button(
                        "Add CSV classes to timetable",
                        key="confirm_csv_import",
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
    st.subheader("My Timetable")

    st.dataframe(
        st.session_state.classes,
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
        for item in st.session_state.classes
        if item.get("Day") == selected_day
    ]

    if day_classes:
        st.dataframe(
            day_classes,
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
            f"{i + 1}. {item.get('subject', 'Untitled')} — "
            f"{item.get('Day', '?')} "
            f"({item.get('Start Time', '')}–{item.get('End Time', '')})"
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