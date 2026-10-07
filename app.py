
import streamlit as st
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
    "Import from Google Calender"
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
    st.info("Timetable file uploade will be done later")
elif option == 'Imort from Google Calendar':
    st.info("Google Calendar integration will be added next.")
