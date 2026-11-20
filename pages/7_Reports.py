import streamlit as st

from app_auth import get_current_user

from course_storage import get_user_courses
from exam_storage import get_user_exams

from study_session_storage import get_user_study_sessions

from deadline_storage import get_user_deadlines

from academic_event_storage import get_user_academic_events

from academic_report_generator import (
    generate_academic_excel,
    generate_academic_pdf,
)


# ---------- PAGE CONFIGURATION ----------

st.set_page_config(
    page_title="Reports | Smart Timetable Assistant",
    page_icon="📊",
    layout="wide",
)


# ---------- USER AUTHENTICATION ----------

current_user = get_current_user()

if not current_user:
    st.warning("Please sign in from the main application.")
    st.stop()

user_id = current_user.id


# ---------- CONSOLIDATED ACADEMIC REPORT ----------

st.title("Consolidated Academic Report")

try:

    report_data = {
        "timetable": st.session_state.get("classes", []),
        "courses": get_user_courses(user_id),
        "exams": get_user_exams(user_id),
        "study_sessions": get_user_study_sessions(user_id),
        "deadlines": get_user_deadlines(user_id),
        "academic_events": get_user_academic_events(user_id),
    }

    st.write(
        "Download all your academic information in one organised report."
    )

    col1, col2 = st.columns(2)

    with col1:

        excel_file = generate_academic_excel(report_data)

        st.download_button(
            label="📊 Download Excel Report",
            data=excel_file,
            file_name="academic_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_consolidated_excel",
            use_container_width=True,
        )

    with col2:

        pdf_file = generate_academic_pdf(report_data)

        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_file,
            file_name="academic_report.pdf",
            mime="application/pdf",
            key="download_consolidated_pdf",
            use_container_width=True,
        )

except Exception as e:

    st.error(f"Could not generate academic report: {e}")