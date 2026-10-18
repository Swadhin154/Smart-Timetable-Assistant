import json
import secrets
from datetime import datetime, timedelta

import streamlit as st
from cryptography.fernet import Fernet
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app_auth import get_current_user, get_supabase_client


SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

REDIRECT_URI = (
    "https://smart-timetable-assistant-phystar.streamlit.app/"
)


def _fernet():
    """Return the encryption helper for stored Google tokens."""
    return Fernet(st.secrets["TOKEN_ENCRYPTION_KEY"].encode())


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
    """Create a Google OAuth flow using the configured Web client."""
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
    """Start Google Calendar authorization with a PKCE verifier."""
    user = get_current_user()

    if not user:
        st.error("Please sign in to your app first.")
        return

    try:
        # Create the flow and generate a PKCE verifier.
        flow = _new_flow()
        verifier = secrets.token_urlsafe(64)

        # Encrypt the verifier before including it in signed state.
        encrypted_verifier = _fernet().encrypt(
            verifier.encode("utf-8")
        ).decode("utf-8")

        state = _state_serializer().dumps(
            {
                "user_id": str(user.id),
                "encrypted_verifier": encrypted_verifier,
            }
        )

        # Preserve the same verifier used to generate the challenge.
        flow.code_verifier = verifier

        authorization_url, _ = flow.authorization_url(
            state=state,
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
            code_challenge_method="S256",
        )

        st.link_button(
            "Continue to Google",
            authorization_url,
        )

    except Exception as exc:
        st.error(
            "Could not start Google Calendar authorization. "
            f"Error type: {type(exc)._name_}. "
            "Check the app configuration and deployment logs."
        )


def handle_google_oauth_callback():
    """Verify Google's callback, exchange the code, and save the token."""
    code = st.query_params.get("code")
    returned_state = st.query_params.get("state")
    oauth_error = st.query_params.get("error")

    if oauth_error:
        st.query_params.clear()
        st.error(
            "Google Calendar authorization was cancelled or denied. "
            "Please start a new connection if you want to continue."
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
            "Please start a new connection."
        )
        return True

    try:
        # Validate the signed state and its expiration.
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

        encrypted_verifier = state_data.get("encrypted_verifier")

        if not encrypted_verifier:
            raise RuntimeError(
                "PKCE verifier is missing from OAuth state."
            )

        # Restore the original PKCE verifier.
        verifier = _fernet().decrypt(
            encrypted_verifier.encode("utf-8")
        ).decode("utf-8")

        # Re-create the flow and restore the verifier before
        # exchanging the one-time authorization code.
        flow = _new_flow(state=returned_state)
        flow.code_verifier = verifier
        flow.fetch_token(code=code)

        credentials = flow.credentials

        if not credentials.token:
            raise RuntimeError(
                "Google did not return an access token."
            )

        # Encrypt the Google credentials before storing them.
        encrypted_token = _fernet().encrypt(
            credentials.to_json().encode("utf-8")
        ).decode("utf-8")

        client = get_supabase_client()

        response = (
            client.table("google_calendar_tokens")
            .upsert(
                {
                    "user_id": str(user.id),
                    "encrypted_token": encrypted_token,
                    "updated_at": datetime.now().astimezone().isoformat(),
                }
            )
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
            "Google authorization expired. Please start a new "
            "Google Calendar connection."
        )
        return True

    except BadSignature:
        st.query_params.clear()
        st.error(
            "Authorization verification failed. "
            "Please start a new Google Calendar connection."
        )
        return True

    except Exception as exc:
        error_type = type(exc).__name__
        error_code = getattr(exc, "error", None)
        error_description = getattr(exc, "description", None)

        # Remove the one-time authorization code from the URL.
        st.query_params.clear()

        # Never display authorization codes, tokens, secrets,
        # or complete OAuth request URLs.
        st.error(
            "Google Calendar connection failed. "
            f"Error type: {error_type}."
        )

        if isinstance(error_code, str):
            st.write("OAuth error code:", error_code[:100])

        if isinstance(error_description, str):
            st.write(
                "OAuth error description:",
                error_description[:200],
            )

        if error_type == "InvalidGrantError":
            st.info(
                "Google rejected the authorization-code exchange. "
                "Start a fresh connection and approve access once. "
                "If the error persists, check the Web client credentials, "
                "redirect URI, and PKCE configuration."
            )

        return True


def get_calendar_service():
    """Load and validate the signed-in user's Google credentials."""
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
            "Supabase returned no response while looking up the token."
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
        encrypted_token.encode("utf-8")
    ).decode("utf-8")

    credentials = Credentials.from_authorized_user_info(
        json.loads(token_json),
        SCOPES,
    )

    if credentials.expired:
        if not credentials.refresh_token:
            raise RuntimeError(
                "Google authorization has expired and no refresh token "
                "is available. Please reconnect Google Calendar."
            )

        credentials.refresh(Request())

        updated_encrypted_token = _fernet().encrypt(
            credentials.to_json().encode("utf-8")
        ).decode("utf-8")

        update_response = (
            client.table("google_calendar_tokens")
            .upsert(
                {
                    "user_id": str(user.id),
                    "encrypted_token": updated_encrypted_token,
                    "updated_at": datetime.now().astimezone().isoformat(),
                }
            )
            .execute()
        )

        if update_response is None:
            raise RuntimeError(
                "Credentials were refreshed, but Supabase returned "
                "no response while saving the updated token."
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
    """Fetch upcoming timed events from the primary Google Calendar."""
    service = get_calendar_service()

    now = datetime.now().astimezone()
    end_date = now + timedelta(days=90)

    response = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=end_date.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

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

        classes.append(
            {
                "subject": event.get("summary", "Untitled"),
                "Day": start_dt.strftime("%A"),
                "Start Time": start_dt.time(),
                "End Time": end_dt.time(),
                "Teacher": "",
                "Room": "",
            }
        )

    return classes


def create_calendar_event(
    subject,
    event_date,
    start_time,
    end_time,
):
    """Create an event in the signed-in user's primary calendar."""
    if not subject or not subject.strip():
        raise ValueError("Please enter an event title.")

    if end_time <= start_time:
        raise ValueError("End time must be later than start time.")

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
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
    }

    return (
        service.events()
        .insert(
            calendarId="primary",
            body=event_body,
        )
        .execute()
    )