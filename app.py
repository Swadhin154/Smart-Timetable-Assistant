
import streamlit as st
st.title("Smart Timetable Assistant")
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
st.write("You selected:", option)
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
            st.success("Class added successfully!")
            st.write("subject:", subject)
            st.write("Day:", day)
            st.write("Time:", start_time, "-", end_time)
            st.write('Teacher:', teacher)
            st.write("Room:", room)
elif option == "Upload a Timetable file":
    st.info("File upload will be added next.")
elif option == 'Imort from Google Calendar':
    st.info("Google Calendar integration will be added next.")
