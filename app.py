
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

