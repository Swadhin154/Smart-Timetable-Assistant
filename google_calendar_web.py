import json
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import streamlit as st
from cryptography.fernet import Fernet
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app_auth import get_current_user, get_supabase_client


SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def _fernet():
    return Fernet(st.secrets["TOKEN_ENCRYPTION_KEY"].encode())


def _redirect_uri():
    return (
        "https://smart-timetable-assistant-fwamrxbvul7qmvsg9s9mpd."
        "streamlit.app/"
    )


def _new_flow(state=None):
    client_config = {
        "web": {
            "client_id": st.secrets["GOOGLE_WEB_CLIENT_ID"],
            "client_secret": st.secrets["GOOGLE_WEB_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [_redirect_uri()],
        }
    }

    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state,
        redirect_uri=_redirect_uri(),
    )


def start_google_oauth():
    """Start the Google authorization process."""
    user = get_current_user()
    if not user:
        st.error("Please sign in to your app first.")
        return

    flow = _new_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )

    st.session_state["google_oauth_state"] = state
    st.link_button("Continue to Google", authorization_url)


def handle_google_oauth_callback():
    """Process Google's redirect after authorization."""
    code = st.query_params.get("code")
    returned_state = st.query_params.get("state")

    if not code:
        return False

    user = get_current_user()
    expected_state = st.session_state.get("google_oauth_state")

    if not user:
        st.error("Please sign in again, then connect Google Calendar.")
        st.query_params.clear()
        return True

    if not expected_state or returned_state != expected_state:
        st.error("Authorization verification failed. Please try again.")
        st.session_state.pop("google_oauth_state", None)
        st.query_params.clear()
        return True

    try:
        flow = _new_flow(state=expected_state)
        flow.fetch_token(code=code)
        credentials = flow.credentials

        encrypted_token = _fernet().encrypt(
            credentials.to_json().encode()
        ).decode()

        client = get_supabase_client()
        client.table("google_calendar_tokens").upsert({
            "user_id": str(user.id),
            "encrypted_token": encrypted_token,
            "updated_at": datetime.now().astimezone().isoformat(),
        }).execute()

        st.session_state.pop("google_oauth_state", None)
        st.query_params.clear()
        st.success("Google Calendar connected successfully!")
        return True

    except Exception:
        st.error(
            "Google Calendar connection failed. Check the OAuth settings "
            "and try again."
        )
        st.query_params.clear()
        return True


def get_calendar_service():
    """Load this signed-in user's encrypted Google token."""
    user = get_current_user()
    if not user:
        raise RuntimeError("Please sign in first.")

    client = get_supabase_client()
    result = (
        client.table("google_calendar_tokens")
        .select("encrypted_token")
        .eq("user_id", str(user.id))
        .maybe_single()
        .execute()
    )

    if not result.data:
        raise RuntimeError("Connect your Google Calendar first.")

    token_json = _fernet().decrypt(
        result.data["encrypted_token"].encode()
    ).decode()

    credentials = Credentials.from_authorized_user_info(
        json.loads(token_json), SCOPES
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

        encrypted_token = _fernet().encrypt(
            credentials.to_json().encode()
        ).decode()

        client.table("google_calendar_tokens").upsert({
            "user_id": str(user.id),
            "encrypted_token": encrypted_token,
            "updated_at": datetime.now().astimezone().isoformat(),
        }).execute()

    if not credentials.valid:
        raise RuntimeError("Reconnect your Google Calendar.")

    return build("calendar", "v3", credentials=credentials)


def get_calendar_events():
    service = get_calendar_service()
    now = datetime.now().astimezone()
    end_date = now + timedelta(days=90)

    result = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=end_date.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    classes = []

    for event in result.get("items", []):
        start = event.get("start", {})
        end = event.get("end", {})

        if "dateTime" not in start or "dateTime" not in end:
            continue

        start_dt = datetime.fromisoformat(
            start["dateTime"].replace("Z", "+00:00")
        )
        end_dt = datetime.fromisoformat(
            end["dateTime"].replace("Z", "+00:00")
        )

        classes.append({
            "subject": event.get("summary", "Untitled"),
            "Day": start_dt.strftime("%A"),
            "Start Time": start_dt.time(),
            "End Time": end_dt.time(),
            "Teacher": "",
            "Room": "",
        })

    return classes


def create_calendar_event(subject, event_date, start_time, end_time):
    service = get_calendar_service()
    start_dt = datetime.combine(event_date, start_time).astimezone()
    end_dt = datetime.combine(event_date, end_time).astimezone()

    event_body = {
        "summary": subject,
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
    }

    return service.events().insert(
        calendarId="primary", body=event_body
    ).execute()