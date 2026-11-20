import csv
import io
from datetime import date, datetime, time

import streamlit as st

from scheduling_logic import find_timetable_conflicts
from free_time_logic import find_free_slots
from study_recommendations import recommend_study_slots
from natural_language import understand_request
from deadline_logic import validate_deadline, get_deadline_status
from deadline_planner import prioritize_deadlines

from app_auth import (
    sign_up,
    sign_in,
    sign_out,
    get_current_user,
)

from academic_event_storage import (
    get_user_academic_events,
    add_user_academic_event,
    update_user_academic_event,
    delete_user_academic_event,
)

from course_storage import (
    get_user_courses,
    add_user_course,
    update_user_course,
    delete_user_course,
)

from exam_storage import (
    get_user_exams,
    add_user_exam,
    update_user_exam,
    delete_user_exam,
)

from study_session_storage import (
    get_user_study_sessions,
    add_user_study_session,
    update_study_session_status,
    delete_user_study_session,
    delete_exam_study_sessions,
)

from exam_study_planner import (
    generate_exam_study_plan,
    calculate_recommended_hours,
)

from google_calendar_web import (
    create_calendar_event,
    get_calendar_events,
    handle_google_oauth_callback,
    is_google_calendar_connected,
    start_google_oauth,
)

from academic_calendar import (
    get_indian_national_holidays,
    get_upcoming_holidays,
)

from academic_report_generator import (
    generate_academic_excel,
    generate_academic_pdf,
)

from ui_pages.home import render_home


# ---------- HELPER FUNCTIONS ----------

def format_time_display(value):
    """Convert supported time values into 12-hour AM/PM format."""

    if value is None or value == "":
        return "-"

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
            parsed_time = datetime.strptime(value, fmt)
            return parsed_time.strftime("%I:%M %p")
        except ValueError:
            continue

    return value


def format_study_time(value):
    """Maintain compatibility with existing study planner code."""
    return format_time_display(value)


DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


# ---------- PAGE CONFIGURATION ----------

st.set_page_config(
    page_title="Smart Timetable Assistant",
    page_icon="📅",
    layout="wide",
)


# ---------- AUTHENTICATION ----------

# Handle Google's redirect before showing the login screen.
handle_google_oauth_callback()

current_user = get_current_user()


# ---------- HIDE SIDEBAR ON LOGIN PAGE ----------

if not current_user:
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }

            [data-testid="collapsedControl"] {
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------- SIGN IN / SIGN UP ----------

if not current_user:

    st.subheader("Sign in or create an account")

    login_tab, signup_tab = st.tabs(
        ["Sign In", "Sign Up"]
    )

    # ---------- SIGN IN ----------

    with login_tab:

        with st.form("login_form"):

            login_email = st.text_input(
                "Email address",
                key="login_email",
            )

            login_password = st.text_input(
                "Password",
                type="password",
                key="login_password",
            )

            login_submitted = st.form_submit_button(
                "Sign In"
            )

        if login_submitted:

            try:
                response = sign_in(
                    login_email.strip(),
                    login_password,
                )

                if response.user:
                    st.success("Signed in successfully!")
                    st.rerun()

                else:
                    st.error(
                        "Sign-in failed. Please check your credentials."
                    )

            except Exception as e:
                st.error(f"sign-in error: {e}")

    # ---------- SIGN UP ----------

    with signup_tab:

        with st.form("signup_form"):

            signup_email = st.text_input(
                "Email address",
                key="signup_email",
            )

            signup_password = st.text_input(
                "Create password",
                type="password",
                key="signup_password",
            )

            signup_submitted = st.form_submit_button(
                "Create Account"
            )

        if signup_submitted:

            try:
                response = sign_up(
                    signup_email.strip(),
                    signup_password,
                )

                if response.user and response.session:

                    st.success(
                        "Account created and signed in!"
                    )
                    st.rerun()

                elif response.user:

                    st.success(
                        "Account created. Check your email to confirm "
                        "your account, then sign in."
                    )

            except Exception as e:
                st.error(f"Account creation error: {e}")

    st.stop()


# ---------- SIGNED-IN USER ----------

user_id = current_user.id


# ---------- INITIALISE SHARED SESSION STATE ----------

if "classes" not in st.session_state:
    st.session_state.classes = []

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

if "delete_mode" not in st.session_state:
    st.session_state.delete_mode = False


# ---------- ACCOUNT INFORMATION AND SIGN OUT ----------

with st.sidebar:

    st.write(
        f"Signed in as {current_user.email}"
    )

    if st.button("Sign Out"):

        sign_out()
        st.rerun()

# ---------- LANDING PAGE ----------

st.html("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');


/* MAIN CONTAINER */

.landing-container {
    height: calc(100vh - 85px);
    min-height: 540px;
    max-height: 760px;
    width: 100%;
    box-sizing: border-box;

    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;

    text-align: center;
    padding: 10px 18px;
    position: relative;
    overflow: hidden;
    background: transparent;
}


/* CALENDAR ILLUSTRATION */

.landing-calendar-area {
    width: 125px;
    height: 100px;
    position: relative;

    display: flex;
    justify-content: center;
    align-items: center;

    margin-bottom: 5px;
}

.landing-orbit {
    position: absolute;
    width: 150px;
    height: 58px;
    border: 2px solid rgba(112, 79, 180, 0.22);
    border-radius: 50%;
    transform: rotate(-18deg);
    animation: orbitFloat 5s ease-in-out infinite;
}

.landing-calendar {
    position: relative;
    width: 72px;
    height: 78px;
    border-radius: 14px;

    background: linear-gradient(145deg, #9A7BE0, #51358E);
    box-shadow: 0 7px 17px rgba(65, 43, 112, 0.20);

    transform: rotate(-5deg);
    z-index: 2;
    padding: 7px;
    box-sizing: border-box;

    animation: calendarFloat 4s ease-in-out infinite;
}

.landing-calendar-top {
    height: 17px;
    display: flex;
    justify-content: center;
    gap: 18px;
}

.landing-calendar-ring {
    width: 7px;
    height: 16px;
    border-radius: 8px;
    background: #392078;
    margin-top: -12px;
}

.landing-calendar-grid {
    background: #F5F0FF;
    height: 49px;
    border-radius: 7px;
    padding: 6px;

    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
}

.landing-calendar-grid span {
    border-radius: 3px;
    background: #C8B5F5;
}

.landing-calendar-grid span:nth-child(2),
.landing-calendar-grid span:nth-child(5) {
    background: #7651D1;
}


/* CLOCK */

.landing-clock {
    position: absolute;
    width: 45px;
    height: 45px;
    border-radius: 50%;

    background: #FFFFFF;
    border: 4px solid #6545AD;

    box-shadow: 0 5px 13px rgba(75, 40, 150, 0.18);

    right: 5px;
    bottom: 0;
    z-index: 3;
}

.landing-clock::before {
    content: "";
    position: absolute;
    width: 3px;
    height: 13px;
    border-radius: 5px;
    background: #392078;
    left: 18px;
    top: 6px;
}

.landing-clock::after {
    content: "";
    position: absolute;
    width: 11px;
    height: 3px;
    border-radius: 5px;
    background: #392078;
    left: 18px;
    top: 18px;
    transform: rotate(-35deg);
    transform-origin: left center;
}


/* MAIN TITLE */

.landing-title {
    position: relative;

    font-family: 'Outfit', sans-serif;
    font-size: clamp(40px, 5.2vw, 65px);
    font-weight: 800;
    line-height: 1.04;
    letter-spacing: -2px;

    margin: 0;
    padding: 0 43px;

    animation: titleFloat 4s ease-in-out infinite;
}


/* SMART TIMETABLE - DARK NAVY */

.landing-title .title-first {
    display: block;

    background: linear-gradient(
        100deg,
        #101827,
        #263D62,
        #111C30,
        #354D75
    );

    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}


/* ASSISTANT - PURPLE AND BLUE MIX */

.landing-title .title-second {
    display: block;

    background: linear-gradient(
        100deg,
        #5141A5 0%,
        #6655C5 25%,
        #526ED0 55%,
        #7656C8 78%,
        #5141A5 100%
    );

    background-size: 200% auto;

    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;

    animation: assistantShimmer 5s ease-in-out infinite;
}


/* CURVED SEMICIRCULAR FLASHING STROKES */

.landing-title::before,
.landing-title::after {
    content: "";
    position: absolute;

    width: 27px;
    height: 17px;

    border: 3px solid transparent;
    border-top-color: #7959C5;
    border-radius: 50% 50% 0 0;

    filter: drop-shadow(0 0 4px rgba(112, 79, 190, 0.55));

    animation: arcFlash 1.8s ease-in-out infinite;
}

.landing-title::before {
    left: 3px;
    top: 19px;
    transform: rotate(-35deg);
}

.landing-title::after {
    right: 3px;
    bottom: 19px;
    transform: rotate(145deg);
    animation-delay: 0.9s;
}


/* ACADEMIC COMPANION BOX */

.landing-badge {
    display: inline-block;

    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 2.5px;

    color: #62449E;

    padding: 9px 23px;
    margin-top: 17px;

    border: 1px solid rgba(112, 79, 180, 0.35);
    border-radius: 30px;

    background: rgba(246, 242, 253, 0.65);
    box-shadow: 0 3px 12px rgba(75, 50, 120, 0.06);
}


/* TAGLINE */

.landing-subtitle {
    font-family: 'Outfit', sans-serif;
    font-size: clamp(16px, 2vw, 22px);
    font-weight: 600;
    color: #514078;

    margin-top: 15px;
}


/* READY TO GET STARTED CARD */

.landing-welcome {
    width: min(520px, 92%);
    box-sizing: border-box;

    display: flex;
    align-items: center;
    justify-content: center;
    gap: 13px;

    /* Compact vertical size */
    padding: 0px 22px;
    margin-top: 25px;
    min-height: 48px;

    text-align: left;

    background: rgba(246, 242, 252, 0.55);
    border: 1px solid rgba(130, 101, 180, 0.24);
    border-radius: 16px;

    box-shadow: 0 5px 18px rgba(70, 45, 115, 0.07);
}

.landing-rocket {
    font-size: 24px;
    line-height: 1;
    min-width: 34px;
    text-align: center;

    animation: rocketFloat 3s ease-in-out infinite;
}

.landing-welcome-text {
    flex: 1;
}

.landing-ready {
    font-family: 'Outfit', sans-serif;
    font-size: 16px;
    font-weight: 700;
    line-height: 1.2;
    color: #432879;
    margin-bottom: 1px;
}

.landing-guidance {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 10px;
    line-height: 1.3;
    font-weight: 500;
    color: #746887;
}


/* SMALL ACADEMIC DECORATIONS */

.landing-decoration {
    position: absolute;
    font-size: 32px;
    opacity: 0.17;
    pointer-events: none;
}

.landing-books {
    left: 20px;
    bottom: 18px;
}

.landing-cap {
    right: 20px;
    bottom: 18px;
}


/* ANIMATIONS */

@keyframes titleFloat {
    0%, 100% {
        transform: translateY(0);
    }

    50% {
        transform: translateY(-3px);
    }
}

@keyframes assistantShimmer {
    0%, 100% {
        background-position: 0% center;
    }

    50% {
        background-position: 100% center;
    }
}

@keyframes arcFlash {
    0%, 100% {
        opacity: 0.25;
        filter: drop-shadow(0 0 2px rgba(112, 79, 190, 0.25));
    }

    50% {
        opacity: 1;
        filter: drop-shadow(0 0 9px rgba(112, 79, 190, 0.8));
    }
}

@keyframes calendarFloat {
    0%, 100% {
        transform: rotate(-5deg) translateY(0);
    }

    50% {
        transform: rotate(-2deg) translateY(-5px);
    }
}

@keyframes orbitFloat {
    0%, 100% {
        transform: rotate(-18deg) scale(1);
    }

    50% {
        transform: rotate(-12deg) scale(1.04);
    }
}

@keyframes rocketFloat {
    0%, 100% {
        transform: translateY(0) rotate(-5deg);
    }

    50% {
        transform: translateY(-4px) rotate(5deg);
    }
}


/* MOBILE RESPONSIVENESS */

@media (max-width: 700px) {

    .landing-container {
        height: calc(100vh - 75px);
        min-height: 520px;
        padding: 8px;
    }

    .landing-calendar-area {
        transform: scale(0.82);
        margin-bottom: 0;
    }

    .landing-title {
        font-size: clamp(34px, 8vw, 48px);
        letter-spacing: -1.5px;
        padding: 0 30px;
    }

    .landing-title::before,
    .landing-title::after {
        width: 19px;
        height: 12px;
        border-width: 2px;
    }

    .landing-title::before {
        top: 15px;
    }

    .landing-title::after {
        bottom: 15px;
    }

    .landing-badge {
        font-size: 9px;
        letter-spacing: 1.8px;
        padding: 8px 17px;
    }

    .landing-subtitle {
        font-size: 16px;
    }

    .landing-welcome {
        width: 95%;
        padding: 0px 13px;
        gap: 10px;
        margin-top: 22px;
        min-height: 43px;
    }

    .landing-rocket {
        font-size: 22px;
        min-width: 30px;
    }

    .landing-ready {
        font-size: 15px;
    }

    .landing-guidance {
        font-size: 9px;
    }

    .landing-decoration {
        font-size: 25px;
        opacity: 0.13;
    }
}


/* REDUCED MOTION */

@media (prefers-reduced-motion: reduce) {
    .landing-container *,
    .landing-container *::before,
    .landing-container *::after {
        animation: none !important;
    }
}

</style>


<div class="landing-container">


    <!-- CALENDAR AND CLOCK -->

    <div class="landing-calendar-area">

        <div class="landing-orbit"></div>

        <div class="landing-calendar">

            <div class="landing-calendar-top">
                <div class="landing-calendar-ring"></div>
                <div class="landing-calendar-ring"></div>
            </div>

            <div class="landing-calendar-grid">
                <span></span>
                <span></span>
                <span></span>
                <span></span>
                <span></span>
                <span></span>
            </div>

        </div>

        <div class="landing-clock"></div>

    </div>


    <!-- MAIN TITLE -->

    <h1 class="landing-title">

        <span class="title-first">
            Smart Timetable
        </span>

        <span class="title-second">
            Assistant
        </span>

    </h1>


    <!-- ACADEMIC COMPANION BOX -->

    <div class="landing-badge">
        YOUR ACADEMIC COMPANION
    </div>


    <!-- TAGLINE -->

    <div class="landing-subtitle">
        Plan smarter. Learn better. Achieve more.
    </div>


    <!-- READY TO GET STARTED -->

    <div class="landing-welcome">

        <div class="landing-rocket">
            🚀
        </div>

        <div class="landing-welcome-text">

            <div class="landing-ready">
                Ready to get started?
            </div>

            <div class="landing-guidance">
                Choose a section from the navigation sidebar
                and start organising your academic journey.
            </div>

        </div>

    </div>


    <!-- SMALL DECORATIONS -->

    <div class="landing-decoration landing-books">
        📚
    </div>

    <div class="landing-decoration landing-cap">
        🎓
    </div>


</div>

""")