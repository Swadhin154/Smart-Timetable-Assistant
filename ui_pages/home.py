from datetime import date, datetime, timedelta, time

import streamlit as st

from exam_storage import get_user_exams
from study_session_storage import get_user_study_sessions
from deadline_storage import get_user_deadlines


DAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
]


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def parse_date(value):
    try:
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        return date.fromisoformat(str(value)[:10])

    except (ValueError, TypeError):
        return None


def format_time(value):
    if value is None or value == "":
        return "—"

    if isinstance(value, datetime):
        value = value.time()

    if isinstance(value, time):
        return value.strftime("%I:%M %p")

    value = str(value).strip()

    for fmt in (
        "%H:%M:%S",
        "%H:%M",
        "%I:%M:%S %p",
        "%I:%M %p",
    ):
        try:
            return datetime.strptime(value, fmt).strftime("%I:%M %p")
        except ValueError:
            continue

    return value


def time_sort_key(value):
    if isinstance(value, (datetime, time)):
        return value.strftime("%H:%M")

    value = str(value or "").strip()

    for fmt in (
        "%H:%M:%S",
        "%H:%M",
        "%I:%M:%S %p",
        "%I:%M %p",
    ):
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            continue

    return value


def get_exam_name(exam_id, exam_names):
    return exam_names.get(str(exam_id), "Study session")


def get_day_items(day_classes, day_sessions, exam_names):
    items = []

    for item in day_classes:
        items.append({
            "start": item.get("Start Time", ""),
            "end": item.get("End Time", ""),
            "name": item.get("subject", "Class"),
            "type": "Class",
        })

    for item in day_sessions:
        items.append({
            "start": item.get("start_time", ""),
            "end": item.get("end_time", ""),
            "name": get_exam_name(
                item.get("exam_id", ""),
                exam_names,
            ),
            "type": "Study",
        })

    items.sort(key=lambda item: time_sort_key(item["start"]))
    return items


# ==========================================================
# HOME DASHBOARD
# ==========================================================

def render_home(user_id):

    today = date.today()
    today_name = today.strftime("%A")

    classes = st.session_state.get("classes", [])

    # ------------------------------------------------------
    # LOAD DATA
    # ------------------------------------------------------

    try:
        exams = get_user_exams(user_id) or []
        sessions = get_user_study_sessions(user_id) or []
        deadlines = get_user_deadlines(user_id) or []

    except Exception as exc:
        st.error(f"Could not load dashboard information: {exc}")
        return

    # ------------------------------------------------------
    # EXAMS
    # ------------------------------------------------------

    upcoming_exams = []
    exam_names = {}

    for exam in exams:
        exam_id = str(exam.get("id", ""))
        exam_title = exam.get("exam_title", "Exam")

        if exam_id:
            exam_names[exam_id] = exam_title

        alternate_id = str(exam.get("exam_id", ""))

        if alternate_id:
            exam_names[alternate_id] = exam_title

        exam_date = parse_date(exam.get("exam_date"))

        if exam_date and exam_date >= today:
            upcoming_exams.append((exam_date, exam))

    upcoming_exams.sort(key=lambda item: item[0])

    # ------------------------------------------------------
    # DEADLINES
    # ------------------------------------------------------

    pending_deadlines = [
        item for item in deadlines
        if str(item.get("status", "")).lower()
        not in ("completed", "done")
    ]

    pending_deadlines.sort(
        key=lambda item: parse_date(item.get("due_date")) or date.max
    )

    # ------------------------------------------------------
    # TODAY'S ACTIVITIES
    # ------------------------------------------------------

    today_classes = [
        item for item in classes
        if item.get("Day") == today_name
    ]

    today_sessions = [
        item for item in sessions
        if parse_date(item.get("session_date")) == today
    ]

    today_items = get_day_items(
        today_classes,
        today_sessions,
        exam_names,
    )

    # ======================================================
    # DASHBOARD STYLING
    # ======================================================

    st.markdown(
        """
        <style>
        /* Keep the page compact without changing
           Streamlit's global column and container layout. */

        .block-container {
            padding-top: 2.8rem;
            padding-bottom: 0.6rem;
        }

        /* Welcome box */
        .welcome-card {
            width: 100%;
            min-height: 88px;
            height: auto;
            box-sizing: border-box;
            overflow: visible;
            background: linear-gradient(110deg, #eee5ff, #ffffff);
            border: 1px solid #e4d7ff;
            border-radius: 13px;
            padding: 12px 19px;
            margin: 0 0 10px 0;
        }

        .welcome-title {
            color: #39236b;
            font-size: 27px;
            line-height: 1.35;
            font-weight: 750;
            margin: 0;
            padding: 0;
            overflow: visible;
        }

        .welcome-subtitle {
            color: #71658a;
            font-size: 13px;
            line-height: 1.4;
            margin: 3px 0 0 0;
            padding: 0;
        }

        /* Schedule items */
        .schedule-item {
            padding: 5px 8px;
            border-radius: 7px;
            margin-bottom: 4px;
            overflow-wrap: anywhere;
            font-size: 12px;
            line-height: 1.35;
        }

        .class-item {
            background: #eee5ff;
            border-left: 3px solid #9b78dc;
        }

        .study-item {
            background: #e8f7ed;
            border-left: 3px solid #62ad7b;
        }

        .day-heading {
            font-size: 12px;
            font-weight: 650;
            text-align: center;
            margin-bottom: 1px;
        }

        .day-date {
            font-size: 10px;
            color: #81768f;
            text-align: center;
            margin-bottom: 3px;
        }

        .calendar-event {
            padding: 4px;
            border-radius: 5px;
            margin-bottom: 3px;
            font-size: 10px;
            line-height: 1.3;
            overflow-wrap: anywhere;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ======================================================
    # WELCOME HEADER
    # ======================================================

    st.markdown(
        f"""
        <div class="welcome-card">
            <div class="welcome-title">Hey there! 👋</div>
            <div class="welcome-subtitle">
                Your academic overview ·
                {today.strftime("%A, %d %B %Y")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ======================================================
    # SUMMARY CARDS
    # ======================================================

    metric1, metric2, metric3, metric4 = st.columns(
        4,
        gap="small",
    )

    with metric1:
        with st.container(border=True):
            st.metric("📚 Classes", len(today_classes))

    with metric2:
        with st.container(border=True):
            st.metric("🎯 Exams", len(upcoming_exams))

    with metric3:
        with st.container(border=True):
            st.metric("📝 Deadlines", len(pending_deadlines))

    with metric4:
        with st.container(border=True):
            st.metric("📖 Study Sessions", len(today_sessions))

    # ======================================================
    # MAIN DASHBOARD
    # ======================================================

    left, right = st.columns(
        [2.15, 1],
        gap="medium",
    )

    # ======================================================
    # LEFT COLUMN
    # ======================================================

    with left:

        # --------------------------------------------------
        # TODAY'S SCHEDULE
        # --------------------------------------------------

        with st.container(border=True):

            st.markdown("### 📖 Today's Schedule")

            if today_items:

                for item in today_items:

                    if item["type"] == "Class":
                        css_class = "class-item"
                        icon = "🟣"
                    else:
                        css_class = "study-item"
                        icon = "🟢"

                    st.markdown(
                        f"""
                        <div class="schedule-item {css_class}">
                            {icon} <b>{item["name"]}</b>
                            &nbsp; · &nbsp;
                            {format_time(item["start"])}
                            – {format_time(item["end"])}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            else:
                st.caption(
                    "No classes or study sessions scheduled today."
                )

        # --------------------------------------------------
        # YOUR TIMETABLE
        # --------------------------------------------------

        with st.container(border=True):

            st.markdown("### 📅 Your Timetable")

            view = st.radio(
                "Calendar view",
                ["Week", "Day", "Month"],
                horizontal=True,
                key="home_timetable_view",
                label_visibility="collapsed",
            )

            # ==============================================
            # WEEK VIEW
            # ==============================================

            if view == "Week":

                week_start = today - timedelta(
                    days=today.weekday()
                )

                day_columns = st.columns(7, gap="small")

                for index, day_name in enumerate(DAYS):

                    current_day = week_start + timedelta(days=index)

                    day_classes = [
                        item for item in classes
                        if item.get("Day") == day_name
                    ]

                    day_sessions = [
                        item for item in sessions
                        if parse_date(item.get("session_date"))
                        == current_day
                    ]

                    day_items = get_day_items(
                        day_classes,
                        day_sessions,
                        exam_names,
                    )

                    with day_columns[index]:

                        heading_color = (
                            "#8055c7"
                            if current_day == today
                            else "#51475e"
                        )

                        st.markdown(
                            f"""
                            <div class="day-heading"
                                 style="color:{heading_color}">
                                {day_name[:3]}
                            </div>
                            <div class="day-date">
                                {current_day.strftime("%d %b")}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        with st.container(border=True):

                            if day_items:

                                for item in day_items[:2]:

                                    if item["type"] == "Class":
                                        css_class = "class-item"
                                        icon = "🟣"
                                    else:
                                        css_class = "study-item"
                                        icon = "🟢"

                                    st.markdown(
                                        f"""
                                        <div class="calendar-event {css_class}">
                                            {icon}
                                            {format_time(item["start"])}
                                            <br>
                                            <b>{item["name"]}</b>
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                                if len(day_items) > 2:
                                    st.caption(
                                        f"+{len(day_items) - 2} more"
                                    )

                            else:
                                st.caption("Free")

            # ==============================================
            # DAY VIEW
            # ==============================================

            elif view == "Day":

                selected_day = st.date_input(
                    "Select date",
                    value=today,
                    key="home_selected_day",
                )

                selected_name = selected_day.strftime("%A")

                day_classes = [
                    item for item in classes
                    if item.get("Day") == selected_name
                ]

                day_sessions = [
                    item for item in sessions
                    if parse_date(item.get("session_date"))
                    == selected_day
                ]

                day_items = get_day_items(
                    day_classes,
                    day_sessions,
                    exam_names,
                )

                if day_items:

                    for item in day_items:

                        icon = (
                            "🟣"
                            if item["type"] == "Class"
                            else "🟢"
                        )

                        st.write(
                            f"{icon} **{format_time(item['start'])} – "
                            f"{format_time(item['end'])}** · "
                            f"{item['name']}"
                        )

                else:
                    st.caption("No activities scheduled for this date.")

            # ==============================================
            # MONTH VIEW
            # ==============================================

            else:

                st.caption(today.strftime("%B %Y"))

                month_items = []

                for item in classes:

                    if item.get("Day") in DAYS:
                        month_items.append({
                            "day": item.get("Day"),
                            "name": item.get("subject", "Class"),
                            "type": "Class",
                        })

                for item in sessions:

                    session_date = parse_date(
                        item.get("session_date")
                    )

                    if (
                        session_date
                        and session_date.year == today.year
                        and session_date.month == today.month
                    ):
                        month_items.append({
                            "day": session_date.strftime("%d %b"),
                            "name": get_exam_name(
                                item.get("exam_id", ""),
                                exam_names,
                            ),
                            "type": "Study",
                        })

                if month_items:

                    for item in month_items[:8]:

                        icon = (
                            "🟣"
                            if item["type"] == "Class"
                            else "🟢"
                        )

                        st.caption(
                            f"{icon} {item['day']} · {item['name']}"
                        )

                    if len(month_items) > 8:
                        st.caption(
                            f"+{len(month_items) - 8} more activities"
                        )

                else:
                    st.caption("No activities available.")

    # ======================================================
    # RIGHT COLUMN
    # ======================================================

    with right:

        # --------------------------------------------------
        # EXAM
        # --------------------------------------------------

        with st.container(border=True):

            st.markdown("### 🎯 Exam")

            if upcoming_exams:

                next_exam_date, next_exam = upcoming_exams[0]

                days_left = (next_exam_date - today).days

                st.markdown(
                    f"*{next_exam.get('exam_title', 'Exam')}*"
                )

                st.caption(
                    next_exam_date.strftime("%d %B %Y")
                )

                if days_left == 0:
                    st.warning("Your exam is today!")
                else:
                    st.metric("Days remaining", days_left)

            else:
                st.caption("No upcoming exams.")

        # --------------------------------------------------
        # TO-DO
        # --------------------------------------------------

        with st.container(border=True):

            st.markdown("### 📝 To-do")

            if pending_deadlines:

                for task in pending_deadlines[:3]:

                    priority = str(
                        task.get("priority", "Medium")
                    ).capitalize()

                    icon = (
                        "🔴" if priority == "High"
                        else "🟢" if priority == "Low"
                        else "🟡"
                    )

                    due_date = parse_date(task.get("due_date"))

                    due_text = (
                        due_date.strftime("%d %b")
                        if due_date
                        else "No due date"
                    )

                    st.markdown(
                        f"*{task.get('title', 'Untitled task')}*"
                    )

                    st.caption(
                        f"{icon} {priority} · Due {due_text}"
                    )

                if len(pending_deadlines) > 3:
                    st.caption(
                        f"+{len(pending_deadlines) - 3} more tasks"
                    )

            else:
                st.caption("You're all caught up!")

        # --------------------------------------------------
        # FREE-TIME TIP
        # --------------------------------------------------

        with st.container(border=True):

            st.markdown("### ✨ Free-time tip")

            if today_classes:

                st.caption(
                    "Use the gaps between classes for short "
                    "revision or focused study."
                )

            else:

                st.caption(
                    "Your schedule is clear today. Use some time "
                    "for revision or exam preparation."
                )