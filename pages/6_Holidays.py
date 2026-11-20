import csv
import io
from datetime import date

import streamlit as st

from app_auth import get_current_user

from academic_calendar import (
    get_indian_national_holidays,
    get_upcoming_holidays,
)

from academic_event_storage import (
    get_user_academic_events,
    add_user_academic_event,
    update_user_academic_event,
    delete_user_academic_event,
)
current_user = get_current_user()

if not current_user:
    st.warning("Please sign in from the main application.")
    st.stop()

academic_calendar_user_id = current_user.id

# ---------- INDIAN NATIONAL HOLIDAY CALENDAR ----------

st.title("Academic Calendar and Holidays")

st.divider()

calendar_view = st.radio(
    "Choose calendar view",
    ["Upcoming Holidays", "All Holidays"],
    horizontal=True,
    key="national_holiday_view",
)

all_holidays = get_indian_national_holidays(2026)

if calendar_view == "Upcoming Holidays":
    holiday_events = get_upcoming_holidays(
        2026,
        today=date.today(),
    )
else:
    holiday_events = all_holidays

if holiday_events:
    display_holidays = []

    for holiday in holiday_events:
        display_holidays.append({
            "Holiday": holiday["Event"],
            "Date": holiday["Date"].strftime("%d %B %Y"),
            "Day": holiday["Day"],
            "Category": holiday["Category"],
        })

    st.dataframe(
        display_holidays,
        width="stretch",
        hide_index=True,
    )
else:
    st.info("No upcoming holidays remaining in the 2026 calendar.")


# ---------- PERSONAL ACADEMIC EVENTS ----------

st.divider()
st.subheader("Your Academic Events")

with st.expander("➕ Add Academic Event", expanded=False):

    with st.form("add_academic_event_form"):

        event_title = st.text_input(
            "Event Title",
            placeholder="e.g. Physics Internal Examination",
        )

        event_date = st.date_input(
            "Event Date",
            value=date.today(),
        )

        event_type = st.selectbox(
            "Event Type",
            [
                "Semester Start",
                "Semester End",
                "Internal Examination",
                "Practical Examination",
                "Assignment",
                "Project",
                "College Event",
                "Semester Break",
                "Other",
            ],
        )

        event_description = st.text_area(
            "Description",
            placeholder="Add any additional details...",
        )

        add_event_button = st.form_submit_button(
            "Save Academic Event",
            use_container_width=True,
        )

        if add_event_button:

            if not event_title.strip():
                st.error("Please enter an event title.")

            else:
                try:
                    add_user_academic_event(
                        academic_calendar_user_id,
                        event_title,
                        event_date,
                        event_type,
                        event_description,
                    )

                    st.success("Academic event added successfully!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Could not add event: {e}")


# ---------- DISPLAY SAVED ACADEMIC EVENTS ----------

try:
    academic_events = get_user_academic_events(
        academic_calendar_user_id
    )

    if academic_events:

        st.markdown("Your Academic Events")

        display_academic_events = []

        for event in academic_events:
            display_academic_events.append({
                "Event": event["event_title"],
                "Date": date.fromisoformat(
                    str(event["event_date"])[:10]
                ).strftime("%d %B %Y"),
                "Type": event["event_type"],
                "Description": event.get("description", ""),
            })

        st.dataframe(
            display_academic_events,
            width="stretch",
            hide_index=True,
        )

        # Export academic events to CSV
        csv_output = io.StringIO()

        csv_writer = csv.DictWriter(
            csv_output,
            fieldnames=[
                "Event",
                "Date",
                "Type",
                "Description",
            ],
        )

        csv_writer.writeheader()
        csv_writer.writerows(display_academic_events)

        st.download_button(
            label="Download Academic Events CSV",
            data=csv_output.getvalue().encode("utf-8-sig"),
            file_name="academic_events.csv",
            mime="text/csv",
            key="download_academic_events_csv",
        )

        # Select an event to edit or delete
        event_options = {
            (
                f"{event['id']} | {event['event_title']} | "
                f"{str(event['event_date'])[:10]}"
            ): event
            for event in academic_events
        }

        selected_event_label = st.selectbox(
            "Select an event to manage",
            list(event_options.keys()),
            key="manage_academic_event",
        )

        selected_event = event_options[selected_event_label]

        st.markdown("Edit Selected Event")

        with st.form("edit_academic_event_form"):

            edit_title = st.text_input(
                "Event Title",
                value=selected_event["event_title"],
            )

            edit_date = st.date_input(
                "Event Date",
                value=date.fromisoformat(
                    str(selected_event["event_date"])[:10]
                ),
            )

            event_type_options = [
                "Semester Start",
                "Semester End",
                "Internal Examination",
                "Practical Examination",
                "Assignment",
                "Project",
                "College Event",
                "Semester Break",
                "Other",
            ]

            current_event_type = selected_event["event_type"]

            if current_event_type not in event_type_options:
                event_type_options.append(current_event_type)

            edit_type = st.selectbox(
                "Event Type",
                event_type_options,
                index=event_type_options.index(current_event_type),
            )

            edit_description = st.text_area(
                "Description",
                value=selected_event.get("description", ""),
            )

            update_event_button = st.form_submit_button(
                "Update Event",
                use_container_width=True,
            )

            if update_event_button:

                if not edit_title.strip():
                    st.error("Event title cannot be empty.")

                else:
                    try:
                        update_user_academic_event(
                            academic_calendar_user_id,
                            selected_event["id"],
                            edit_title,
                            edit_date,
                            edit_type,
                            edit_description,
                        )

                        st.success("Academic event updated successfully!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Could not update event: {e}")

        # Delete selected event
        if st.button(
            "🗑️ Delete Selected Event",
            key="delete_academic_event_button",
            type="secondary",
        ):

            try:
                delete_user_academic_event(
                    academic_calendar_user_id,
                    selected_event["id"],
                )

                st.success("Academic event deleted successfully!")
                st.rerun()

            except Exception as e:
                st.error(f"Could not delete event: {e}")

    else:
        st.info("No personal academic events added yet.")

except Exception as e:
    st.error(f"Could not load academic events: {e}")