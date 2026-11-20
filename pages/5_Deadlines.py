import csv
import io

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import streamlit as st

from app_auth import get_current_user

from deadline_storage import (
    get_user_deadlines,
    add_user_deadline,
    delete_user_deadline,
)

from deadline_logic import (
    validate_deadline,
    get_deadline_status,
)

from deadline_planner import prioritize_deadlines


# ---------- PAGE CONFIGURATION ----------

st.set_page_config(
    page_title="Deadlines | Smart Timetable Assistant",
    page_icon="📅",
    layout="wide",
)


# ---------- USER AUTHENTICATION ----------

current_user = get_current_user()

if not current_user:
    st.warning("Please sign in from the main application.")
    st.stop()

user_id = current_user.id


# ---------- DEADLINE MANAGER ----------

st.title("Assignment & Exam Deadlines")

with st.form("add_deadline_form"):

    task_title = st.text_input(
        "Assignment or exam name",
        key="deadline_title",
    )

    due_date = st.date_input(
        "Due date",
        value=date.today(),
        key="deadline_due_date",
    )

    estimated_hours = st.number_input(
        "Estimated preparation hours",
        min_value=0.5,
        max_value=500.0,
        value=2.0,
        step=0.5,
        key="deadline_estimated_hours",
    )

    priority = st.selectbox(
        "Priority",
        ["Low", "Medium", "High"],
        index=1,
        key="deadline_priority",
    )

    reminder_enabled = st.checkbox(
        "Enable email reminder",
        value=False,
        key="deadline_reminder_enabled",
    )

    reminder_date = st.date_input(
        "Reminder date",
        value=date.today(),
        key="deadline_reminder_date",
    )

    reminder_time = st.time_input(
        "Reminder time",
        value=time(9, 0),
        format="12h",
        key="deadline_reminder_time",
    )

    submitted = st.form_submit_button("Add Deadline")


# ---------- SAVE DEADLINE ----------

if submitted:

    is_valid, message = validate_deadline(
        task_title,
        due_date,
        estimated_hours,
        priority,
    )

    if is_valid:

        try:

            reminder_at = None

            if reminder_enabled:

                reminder_at = datetime.combine(
                    reminder_date,
                    reminder_time,
                    tzinfo=ZoneInfo("Asia/Kolkata"),
                ).isoformat()

            add_user_deadline(
                user_id,
                task_title.strip(),
                due_date,
                estimated_hours,
                priority,
                reminder_at=reminder_at,
                reminder_enabled=reminder_enabled,
            )

            st.success("Deadline saved successfully.")
            st.rerun()

        except Exception as exc:

            st.error(f"Could not save deadline: {exc}")

    else:

        st.error(message)


# ---------- VIEW DEADLINES ----------

st.divider()
st.subheader("Your Deadlines")

try:

    deadlines = get_user_deadlines(user_id)

    if deadlines:

        # ---------- SMART ASSIGNMENT PRIORITIES ----------

        st.subheader("🎯 Smart Assignment Priorities")

        ranked_deadlines = prioritize_deadlines(
            deadlines,
            today=date.today(),
        )

        if ranked_deadlines:

            # ---------- EXPORT PRIORITIES AS CSV ----------

            csv_buffer = io.StringIO()

            csv_fields = [
                "title",
                "due_date",
                "days_remaining",
                "status",
                "priority",
                "estimated_hours",
                "recommendation",
                "priority_score_total",
            ]

            csv_writer = csv.DictWriter(
                csv_buffer,
                fieldnames=csv_fields,
            )

            csv_writer.writeheader()

            for task in ranked_deadlines:

                csv_writer.writerow({
                    field: task.get(field, "")
                    for field in csv_fields
                })

            st.download_button(
                label="📥 Download Assignment Priorities (CSV)",
                data=csv_buffer.getvalue(),
                file_name="assignment_priorities.csv",
                mime="text/csv",
                key="download_assignment_priorities",
            )

            # ---------- TOTAL PREPARATION HOURS ----------

            total_hours = sum(
                task["estimated_hours"]
                for task in ranked_deadlines
            )

            st.metric(
                "Total Pending Preparation Hours",
                f"{total_hours:.1f} hours",
            )

            # ---------- TOP RECOMMENDED TASK ----------

            top_task = ranked_deadlines[0]

            st.success(
                f"Recommended to work on first: "
                f"{top_task['title']} "
                f"(Score: {top_task['priority_score_total']}/100)"
            )

            # ---------- PRIORITY LIST ----------

            for index, task in enumerate(
                ranked_deadlines,
                start=1,
            ):

                with st.container(border=True):

                    st.write(f"*{index}. {task['title']}*")

                    st.write(
                        f"Recommendation: {task['recommendation']}"
                    )

                    st.write(
                        f"Deadline: {task['status']}"
                    )

                    st.write(
                        f"Selected priority: {task['priority']}"
                    )

                    st.write(
                        f"Preparation: "
                        f"{task['estimated_hours']} hours"
                    )

                    st.progress(
                        task["priority_score_total"] / 100
                    )

                    st.caption(
                        f"Priority score: "
                        f"{task['priority_score_total']}/100"
                    )

        # ---------- INDIVIDUAL DEADLINE DETAILS ----------

        today = date.today()

        for deadline in deadlines:

            deadline_id = deadline["id"]

            deadline_date = date.fromisoformat(
                deadline["due_date"]
            )

            status_info = get_deadline_status(
                deadline_date,
                today=today,
            )

            days_remaining = status_info["days_remaining"]

            if days_remaining < 0:

                timing = (
                    f"Overdue by {abs(days_remaining)} day(s)"
                )

            elif days_remaining == 0:

                timing = "Due today"

            else:

                timing = f"{days_remaining} day(s) remaining"

            with st.container(border=True):

                st.markdown(f"*{deadline['title']}*")

                st.write(f"Due date: {deadline_date}")

                st.write(f"Status: {timing}")

                st.write(
                    f"Preparation time: "
                    f"{deadline['estimated_hours']} hour(s)"
                )

                st.write(f"Priority: {deadline['priority']}")

                # ---------- DELETE DEADLINE ----------

                if st.button(
                    "Delete Deadline",
                    key=f"delete_deadline_{deadline_id}",
                ):

                    try:

                        delete_user_deadline(
                            user_id,
                            deadline_id,
                        )

                        st.success("Deadline deleted.")
                        st.rerun()

                    except Exception as exc:

                        st.error(
                            f"Could not delete deadline: {exc}"
                        )

    else:

        st.info("No deadlines added yet.")

except Exception as exc:

    st.error(f"Could not load deadlines: {exc}")