
import streamlit as st
import csv
import io
from datetime import datetime
from google_calendar import get_calendar_events, create_calendar_event
st.title("Smart Timetable Assistant")
if "classes" not in st.session_state:
    st.session_state.classes = []
st.write("Organize your classes, assignments, exams, and study times in one place.")
st.header("Add Your Timetables")
option = st.selectbox(
    "How would you like to add your Timetable?",
    [
    "Enter manually",
    "Upload a Timetable file",
    "Import from Google Calendar"
    ]
)
if option == "Enter manually":
    st.subheader("Add a class")
    with st.form("class_form"):
        subject = st.text_input("subject")
        day = st.selectbox("Day",
        [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday"
        ]
        )
        start_time = st.time_input("Start time", format="12h")
        end_time = st.time_input("End time", format="12h")
        teacher = st.text_input("Teacher")
        room = st.text_input("Room")
        submitted = st.form_submit_button("Add Class")
        if submitted:
            if not subject.strip():
                st.error("Please enter a subject")
            elif start_time >= end_time:
                st.error("End time must be after start time.")
            else:
                new_class = {
                    "subject": subject,
                    "Day": day,
                    "Start Time": start_time,
                    "End Time": end_time,
                    "Teacher": teacher,
                    "Room": room
                }
                st.session_state.classes.append(new_class)
                st.success("Class added successfully!")
         # Display all saved classes
if st.session_state.classes:
    st.subheader("My Timetable")
    st.dataframe(
        st.session_state.classes,
        use_container_width=True
    )
    # Day-wise timetable view
if st.session_state.classes:

    st.subheader("Daily Timetable")

    selected_day = st.selectbox(
        "Select a day",
        [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday"
        ]
    )

    day_classes = [
        class_item
        for class_item in st.session_state.classes
        if class_item["Day"] == selected_day
    ]

    if day_classes:
        st.dataframe(
            day_classes,
            use_container_width=True
        )
    else:
        st.info(f"No classes scheduled for {selected_day}.")
    # Initialize edit and delete modes
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

if "delete_mode" not in st.session_state:
    st.session_state.delete_mode = False


# Edit and Delete options 
if st.session_state.classes:

    # EDIT CLASSES 

    if st.button("Edit Classes"):
        st.session_state.edit_mode = not st.session_state.edit_mode
        st.session_state.delete_mode = False

    if st.session_state.edit_mode and st.session_state.classes:

        st.subheader("Edit")

        class_options = ["Select a class"] + [
            f"Class {i + 1}: {class_item['subject']} - {class_item['Day']}"
            for i, class_item in enumerate(st.session_state.classes)
        ]

        selected_class = st.selectbox(
            "Select a class to edit",
            class_options,
            key="edit_class_selection"
        )

        if selected_class != "Select a class":

            selected_index = class_options.index(selected_class) - 1
            class_item = st.session_state.classes[selected_index]

            with st.form(key=f"edit_form_{selected_index}"):

                edited_subject = st.text_input(
                    "Subject",
                    value=class_item["subject"]
                )

                days = [
                    "Monday", "Tuesday", "Wednesday", "Thursday",
                    "Friday", "Saturday", "Sunday"
                ]

                edited_day = st.selectbox(
                    "Day",
                    days,
                    index=days.index(class_item["Day"])
                )

                edited_start_time = st.time_input(
                    "Start time",
                    value=class_item["Start Time"]
                )

                edited_end_time = st.time_input(
                    "End time",
                    value=class_item["End Time"]
                )

                edited_teacher = st.text_input(
                    "Teacher",
                    value=class_item["Teacher"]
                )

                edited_room = st.text_input(
                    "Room",
                    value=class_item["Room"]
                )

                update_button = st.form_submit_button("Update Class")

                if update_button:
                    if not edited_subject.strip():
                        st.error("Please enter a subject.")

                    elif edited_start_time >= edited_end_time:
                        st.error("End time must be after start time.")

                    else:
                        st.session_state.classes[selected_index] = {
                            "subject": edited_subject.strip(),
                            "Day": edited_day,
                            "Start Time": edited_start_time,
                            "End Time": edited_end_time,
                            "Teacher": edited_teacher,
                            "Room": edited_room
                        }

                        st.success("Class updated successfully!")
                        st.rerun()


    #  DELETE CLASSES 

    if st.button("Delete Classes"):
        st.session_state.delete_mode = not st.session_state.delete_mode
        st.session_state.edit_mode = False

    if st.session_state.delete_mode and st.session_state.classes:

        st.subheader("Delete")

        delete_action = st.radio(
            "Choose a delete option",
            ["Delete one class", "Delete all classes"],
            key="delete_action"
        )

        if delete_action == "Delete one class":

            delete_options = ["Select a class"] + [
                f"Class {i + 1}: {class_item['subject']} - {class_item['Day']}"
                for i, class_item in enumerate(st.session_state.classes)
            ]

            selected_delete = st.selectbox(
                "Select the class to delete",
                delete_options,
                key="delete_class_selection"
            )

            if selected_delete != "Select a class":

                delete_index = delete_options.index(selected_delete) - 1

                if st.button("Delete Selected Class", key="confirm_delete"):
                    st.session_state.classes.pop(delete_index)

                    if not st.session_state.classes:
                        st.session_state.edit_mode = False
                        st.session_state.delete_mode = False

                    st.success("Class deleted successfully!")
                    st.rerun()

        elif delete_action == "Delete all classes":

            st.warning(
                f"This will remove all {len(st.session_state.classes)} "
                "classes from your app's timetable."
            )

            confirm_delete_all = st.checkbox(
                "I confirm that I want to delete all classes.",
                key="confirm_delete_all_checkbox"
            )

            if st.button("Delete All Classes", key="delete_all_classes"):
                if confirm_delete_all:
                    st.session_state.classes = []
                    st.session_state.edit_mode = False
                    st.session_state.delete_mode = False

                    st.success("All classes deleted successfully!")
                    st.rerun()
                else:
                    st.error("Please confirm before deleting all classes.")
elif option == "Upload a Timetable file":
    st.subheader("Upload Your Timetable")
    uploaded_file = st.file_uploader(
        "choose a CSV file",
        type=["csv"]
    )
    if uploaded_file is not None:
        file_content = uploaded_file.getvalue().decode("utf-8")
        reader = csv.DictReader(io.StringIO(file_content))
        required_columns = [
            "Subject",
            "Day",
            "Start Time",
            "End Time",
            "Teacher",
            "Room",
        ]
        if not all(column in reader.fieldnames for column in required_columns):
            st.error(
                "Invalid CSV file. Please make sure it contains: "
                "Subject, Day, Start Time, End Time, Teacher, Room"
            )
        else:
            uploaded_classes = []
            for row in reader:
                try:
                    start_time = datetime.strptime(
                        row["Start Time"].strip(),
                        "%H:%M"    
                    ).time()
                    end_time = datetime.strptime(
                        row["End Time"].strip(),
                        "%H:%M"
                    ).time()
                    uploaded_classes.append({
                        "subject": row["Subject"].strip(),
                        "Day": row["Day"].strip(),
                        "Start Time":start_time,
                        "End Time": end_time,
                        "Teacher": row["Teacher"].strip(),
                        "Room": row["Room"].strip()
                    })
                except ValueError:
                    st.error(
                        "Invalid time format. Please use HH:MM, "
                        "for example 10:00 or 15:30."
                    )
                    uploaded_classes = []
                    break
                if uploaded_classes:
                    st.write("Preview")
                    st.dataframe(
                        uploaded_classes,
                        use_container_width=True
                    )
                    st.session_state.classes.extend(uploaded_classes)
                    st.success(
                        f"{len(uploaded_classes)} classes(es) imported successfully!"
                    )
                    st.rerun()
elif option == "Import from Google Calendar":
    st.subheader("Import from Google Calendar")

    if st.button("Connect Google Calendar"):
        try:
            imported_classes = get_calendar_events()

            if imported_classes:
                st.session_state.classes.extend(imported_classes)
                st.success(
                    f"{len(imported_classes)} event(s) imported successfully!"
                )
                st.rerun()
            else:
                st.info("No timed events found in your Google Calendar.")

        except Exception as e:
            st.error(f"Could not connect to Google Calendar: {e}")

st.divider()
st.subheader("Create Google Calendar Event")

with st.form("create_google_event_form"):
    event_subject = st.text_input("Event title")
    event_date = st.date_input("Event date")
    event_start = st.time_input(
        "Start time",
        format="12h",
        key="google_event_start"
    )
    event_end = st.time_input(
        "End time",
        format="12h",
        key="google_event_end"
    )

    create_submitted = st.form_submit_button("Create Event")

if create_submitted:
    if not event_subject.strip():
        st.error("Please enter an event title.")
    elif event_start >= event_end:
        st.error("End time must be after start time.")
    else:
        try:
            created_event = create_calendar_event(
                event_subject.strip(),
                event_date,
                event_start,
                event_end
            )
            st.success(
                f"Event created successfully: "
                f"{created_event.get('summary', event_subject)}"
            )
        except Exception as e:
            st.error(f"Could not create the event: {e}")

    if st.button("Connect Google Calendar"):
        try:
            imported_classes = get_calendar_events()

            if imported_classes:
                st.session_state.classes.extend(imported_classes)
                st.success(
                    f"{len(imported_classes)} event(s) imported successfully!"
                )
                st.rerun()
            else:
                st.info("No timed events found in your Google Calendar.")

        except Exception as e:
            st.error(f"Could not connect to Google Calendar: {e}")
