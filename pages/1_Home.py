import streamlit as st

from ui_pages.home import render_home
from app_auth import get_current_user


st.set_page_config(
    page_title="Home | Smart Timetable Assistant",
    page_icon="📚",
    layout="wide",
)

current_user = get_current_user()

if not current_user:
    st.warning("Please sign in from the main application.")
    st.stop()

render_home(current_user.id)