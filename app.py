
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
elif option == "Upload a Timetable file":
    st.info("File upload will be added next.")
elif option == 'Imort from Google Calendar':
    st.info("Google Calendar integration will be added next.")
