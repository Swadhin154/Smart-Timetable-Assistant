import json
from datetime import datetime, timedelta

import streamlit as st
from cryptography.fernet import Fernet
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app_auth import get_current_user, get_supabase_client


SCOPES = [
    "https://www.googleapis.com/auth/calendar.events"
]

REDIRECT_URI = (
    "https://smart-timetable-assistant-phystar.streamlit.app/"
)


def _fernet():
    """Return the encryption helper for stored Google tokens."""
    return Fernet(
        st.secrets["TOKEN_ENCRYPTION_KEY"].encode()
    )


def _state_serializer():
    """Create a signed serializer for OAuth state."""
    return URLSafeTimedSerializer(
        st.secrets["TOKEN_ENCRYPTION_KEY"],
        salt="google-oauth-state",
    )


def _redirect_uri():
    """Return the registered Google OAuth redirect URI."""
    return REDIRECT_URI


def _new_flow(state=None):
    """Create the Google OAuth flow."""
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
    """Start Google Calendar authorization."""
    user = get_current_user()

    if not user:
        st.error("Please sign in to your app first.")
        return

    try:
        # The signed state is independently verifiable after
        # Google redirects back to the app.
        state = _state_serializer().dumps({
            "user_id": str(user.id),
        })

        flow = _new_flow(state=state)

        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )

        st.link_button(
            "Continue to Google",
            authorization_url,
        )

    except Exception:
        st.error(
            "Could not start Google Calendar authorization. "
            "Please check the app configuration."
        )


def handle_google_oauth_callback():
    """Process Google's redirect and verify the signed state."""
    code = st.query_params.get("code")
    returned_state = st.query_params.get("state")
    oauth_error = st.query_params.get("error")

    if oauth_error:
        st.query_params.clear()
        st.error(
            "Google Calendar authorization was cancelled or denied. "
            "Please try again if you want to connect your calendar."
        )
        return True

    if not code:
        return False

    user = get_current_user()

    if not user:
        st.query_params.clear()
        st.error(
            "Your app session has expired. Please sign in again "
            "and reconnect Google Calendar."
        )
        return True

    if not returned_state:
        st.query_params.clear()
        st.error(
            "Google authorization state is missing. "
            "Please try connecting again."
        )
        return True

    try:
        state_data = _state_serializer().loads(
            returned_state,
            max_age=600,
        )

        if state_data.get("user_id") != str(user.id):
            st.query_params.clear()
            st.error(
                "Authorization verification failed. "
                "Please sign in to the correct account and try again."
            )
            return True

        flow = _new_flow(state=returned_state)
        flow.fetch_token(code=code)
        credentials = flow.credentials

        if not credentials.token:
            raise RuntimeError(
                "Google did not return an access token."
            )

        encrypted_token = _fernet().encrypt(
            credentials.to_json().encode()
        ).decode()

        client = get_supabase_client()

        response = (
            client.table("google_calendar_tokens")
            .upsert({
                "user_id": str(user.id),
                "encrypted_token": encrypted_token,
                "updated_at": datetime.now().astimezone().isoformat(),
            })
            .execute()
        )

        if response is None:
            raise RuntimeError(
                "Supabase returned no response while saving the token."
            )

        st.query_params.clear()
        st.success("Google Calendar connected successfully!")
        return True

    except SignatureExpired:
        st.query_params.clear()
        st.error(
            "Google authorization took too long and expired. "
            "Please click Connect Google Calendar and try again."
        )
        return True

    except BadSignature:
        st.query_params.clear()
        st.error(
            "Authorization verification failed. "
            "Please start a new Google Calendar connection."
        )
        return True

    except Exception:
        # Do not display OAuth codes, tokens, or provider responses.
        st.query_params.clear()
        st.error(
            "Google Calendar connection failed. "
            "Check the app logs and OAuth settings, then try again."
        )
        return True


def get_calendar_service():
    """Load the current user's Google Calendar credentials."""
    user = get_current_user()

    if not user:
        raise RuntimeError("Please sign in first.")

    client = get_supabase_client()

    response = (
        client.table("google_calendar_tokens")
        .select("encrypted_token")
        .eq("user_id", str(user.id))
        .limit(1)
        .execute()
    )

    if response is None:
        raise RuntimeError(
            "Supabase returned no response when looking up "
            "the Google Calendar token."
        )

    records = response.data

    if not records:
        raise RuntimeError(
            "No Google Calendar token was found for this account. "
            "Connect Google Calendar and authorize access first."
        )

    encrypted_token = records[0].get("encrypted_token")

    if not encrypted_token:
        raise RuntimeError(
            "The saved Google Calendar token is empty. "
            "Please reconnect Google Calendar."
        )

    token_json = _fernet().decrypt(
        encrypted_token.encode()
    ).decode()

    credentials = Credentials.from_authorized_user_info(
        json.loads(token_json),
        SCOPES,
    )

    if credentials.expired:
        if not credentials.refresh_token:
            raise RuntimeError(
                "Google authorization has expired. "
                "Please reconnect Google Calendar."
            )

        credentials.refresh(Request())

        updated_encrypted_token = _fernet().encrypt(
            credentials.to_json().encode()
        ).decode()

        update_response = (
            client.table("google_calendar_tokens")
            .upsert({
                "user_id": str(user.id),
                "encrypted_token": updated_encrypted_token,
                "updated_at": datetime.now().astimezone().isoformat(),
            })
            .execute()
        )

        if update_response is None:
            raise RuntimeError(
                "Google credentials were refreshed, but Supabase "
                "returned no response while saving the updated token."
            )

    if not credentials.valid:
        raise RuntimeError(
            "Google credentials are invalid. "
            "Please reconnect Google Calendar."
        )

    return build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


def get_calendar_events():
    """Fetch upcoming timed events from Google Calendar."""
    service = get_calendar_service()

    now = datetime.now().astimezone()
    end_date = now + timedelta(days=90)

    response = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=end_date.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    classes = []

    for event in response.get("items", []):
        start = event.get("start", {})
        end = event.get("end", {})

        # Skip all-day events because the timetable uses times.
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


def create_calendar_event(
    subject,
    event_date,
    start_time,
    end_time,
):
    """Create an event in the current user's primary calendar."""
    if not subject or not subject.strip():
        raise ValueError("Please enter an event title.")

    if end_time <= start_time:
        raise ValueError(
            "End time must be later than start time."
        )

    service = get_calendar_service()

    start_dt = datetime.combine(
        event_date,
        start_time,
    ).astimezone()

    end_dt = datetime.combine(
        event_date,
        end_time,
    ).astimezone()

    event_body = {
        "summary": subject.strip(),
        "start": {
            "dateTime": start_dt.isoformat(),
        },
        "end": {
            "dateTime": end_dt.isoformat(),
        },
    }

    return service.events().insert(
        calendarId="primary",
        body=event_body,
    ).execute()