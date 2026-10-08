
import streamlit as st
import csv
import io
from datetime import datetime
from google_calendar import get_calendar_events
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
    # Edit classes
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

if st.button("Edit Classes"):
    st.session_state.edit_mode = True
    st.session_state.delete_mode = False

if st.session_state.edit_mode and st.session_state.classes:

    st.subheader("Edit")

    class_options = ["Select a class"] + [
        f"Class {i + 1}: {class_item['subject']} - {class_item['Day']}"
        for i, class_item in enumerate(st.session_state.classes)
    ]

    selected_class = st.selectbox(
        "Edit",
        class_options
    )

    if selected_class != "Select a class":

        selected_index = class_options.index(selected_class) - 1
        class_item = st.session_state.classes[selected_index]

        with st.form(key=f"edit_form_{selected_index}"):

            st.write(
                f"Editing: {class_item['subject']} - {class_item['Day']}"
            )

            edited_subject = st.text_input(
                "Subject",
                value=class_item["subject"]
            )

            days = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday"
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
                        "subject": edited_subject,
                        "Day": edited_day,
                        "Start Time": edited_start_time,
                        "End Time": edited_end_time,
                        "Teacher": edited_teacher,
                        "Room": edited_room
                    }

                    st.success("Class updated successfully!")
                    st.rerun()


# Delete classes
if "delete_mode" not in st.session_state:
    st.session_state.delete_mode = False

if st.button("Delete Classes"):
    st.session_state.delete_mode = True
    st.session_state.edit_mode = False

if st.session_state.delete_mode and st.session_state.classes:

    st.subheader("Delete")

    delete_options = ["Select a class"] + [
        f"Class {i + 1}: {class_item['subject']} - {class_item['Day']}"
        for i, class_item in enumerate(st.session_state.classes)
    ]

    selected_delete = st.selectbox(
        "Delete",
        delete_options
    )

    if selected_delete != "Select a class":

        delete_index = delete_options.index(selected_delete) - 1

        if st.button("Delete Class", key="confirm_delete"):
            st.session_state.classes.pop(delete_index)
            st.success("Class deleted successfully!")
            st.rerun()
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
