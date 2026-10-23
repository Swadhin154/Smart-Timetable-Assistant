import json
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import streamlit as st
from cryptography.fernet import Fernet
from itsdangerous import (
    URLSafeTimedSerializer,
    BadSignature,
    SignatureExpired,
)
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app_auth import get_current_user, get_supabase_client


SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

REDIRECT_URI = (
    "https://smart-timetable-assistant-phystar.streamlit.app/"
)

LOCAL_TIMEZONE = ZoneInfo("Asia/Kolkata")


def _fernet():
    """Return the encryption helper for stored credentials."""
    return Fernet(
        st.secrets["TOKEN_ENCRYPTION_KEY"].encode()
    )


def _state_serializer():
    """Create a signed serializer for OAuth state verification."""
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
    """
    Start Google OAuth.

    A short-lived, encrypted app session and the PKCE verifier are saved
    server-side. They are not placed directly in the browser URL.
    """
    user = get_current_user()

    if not user:
        st.info(
            "Sign in to Smart Timetable Assistant before "
            "connecting Google Calendar."
        )
        return

    access_token = st.session_state.get(
        "supabase_access_token"
    )
    refresh_token = st.session_state.get(
        "supabase_refresh_token"
    )

    if not access_token or not refresh_token:
        st.error(
            "Your app login session is incomplete. "
            "Please sign out and sign in again."
        )
        return

    try:
        flow = _new_flow()

        verifier = secrets.token_urlsafe(64)
        nonce = secrets.token_urlsafe(32)

        # State is signed and contains no raw login tokens.
        state = _state_serializer().dumps(
            {
                "user_id": str(user.id),
                "nonce": nonce,
            }
        )

        flow.code_verifier = verifier

        client = get_supabase_client()

        pending_row = {
            "nonce": nonce,
            "user_id": str(user.id),
            "encrypted_access_token": _fernet().encrypt(
                access_token.encode("utf-8")
            ).decode("utf-8"),
            "encrypted_refresh_token": _fernet().encrypt(
                refresh_token.encode("utf-8")
            ).decode("utf-8"),
            "encrypted_verifier": _fernet().encrypt(
                verifier.encode("utf-8")
            ).decode("utf-8"),
            "expires_at": (
                datetime.now(timezone.utc)
                + timedelta(minutes=10)
            ).isoformat(),
        }

        # The table must be accessible only through server-side credentials.
        client.table("google_oauth_pending").upsert(
            pending_row
        ).execute()

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
            type="primary",
            use_container_width=True,
        )

        st.caption(
            "Google will ask you to approve calendar access. "
            "Return here after approval."
        )

    except Exception as exc:
        st.error(
            "Unable to start Google Calendar connection. "
            f"Error type: {type(exc)._name_}."
        )


def handle_google_oauth_callback():
    """
    Process Google's redirect before the app login gate.

    Verify the signed state, restore the short-lived encrypted app session,
    exchange the authorization code, and save the encrypted Google token.
    """
    code = st.query_params.get("code")
    returned_state = st.query_params.get("state")
    oauth_error = st.query_params.get("error")

    if oauth_error:
        st.query_params.clear()
        st.error(
            "Google Calendar authorization was cancelled or denied. "
            "You can try connecting again."
        )
        return True

    if not code:
        return False

    if not returned_state:
        st.query_params.clear()
        st.error(
            "Google authorization state is missing. "
            "Please start a new connection."
        )
        return True

    try:
        # Never trust user ID or nonce until the signed state is verified.
        state_data = _state_serializer().loads(
            returned_state,
            max_age=600,
        )

        user_id = str(state_data.get("user_id", ""))
        nonce = str(state_data.get("nonce", ""))

        if not user_id or not nonce:
            raise ValueError(
                "Required OAuth state values are missing."
            )

        client = get_supabase_client()

        pending_response = (
            client.table("google_oauth_pending")
            .select("*")
            .eq("nonce", nonce)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        pending_rows = pending_response.data or []

        if not pending_rows:
            raise RuntimeError(
                "The temporary login session expired. "
                "Start the connection again."
            )

        pending = pending_rows[0]

        expires_at = datetime.fromisoformat(
            str(pending["expires_at"]).replace("Z", "+00:00")
        )

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc
            )

        if datetime.now(timezone.utc) >= expires_at:
            raise RuntimeError(
                "The temporary login session expired. "
                "Start the connection again."
            )

        # Restore the app login session from the encrypted server-side row.
        restored_access_token = _fernet().decrypt(
            pending["encrypted_access_token"].encode("utf-8")
        ).decode("utf-8")

        restored_refresh_token = _fernet().decrypt(
            pending["encrypted_refresh_token"].encode("utf-8")
        ).decode("utf-8")

        st.session_state["supabase_access_token"] = (
            restored_access_token
        )
        st.session_state["supabase_refresh_token"] = (
            restored_refresh_token
        )
        st.session_state["supabase_user_id"] = user_id

        user = get_current_user()

        if not user or str(user.id) != user_id:
            raise RuntimeError(
                "Your app session could not be restored. "
                "Please sign in and reconnect."
            )

        # Restore the PKCE verifier before exchanging the code.
        verifier = _fernet().decrypt(
            pending["encrypted_verifier"].encode("utf-8")
        ).decode("utf-8")

        flow = _new_flow(state=returned_state)
        flow.code_verifier = verifier
        flow.fetch_token(code=code)

        credentials = flow.credentials

        if not credentials.token:
            raise RuntimeError(
                "Google did not return an access token."
            )

        # Store Google credentials encrypted in Supabase.
        encrypted_token = _fernet().encrypt(
            credentials.to_json().encode("utf-8")
        ).decode("utf-8")

        client.table("google_calendar_tokens").upsert(
            {
                "user_id": user_id,
                "encrypted_token": encrypted_token,
                "updated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
        ).execute()

        # Remove the temporary OAuth record after successful connection.
        client.table("google_oauth_pending").delete().eq(
            "nonce", nonce
        ).execute()

        st.query_params.clear()
        st.session_state["google_calendar_just_connected"] = True
        return True

    except SignatureExpired:
        st.query_params.clear()
        st.error(
            "Google authorization expired. "
            "Please start a new connection."
        )
        return True

    except BadSignature:
        st.query_params.clear()
        st.error(
            "Authorization verification failed. "
            "Please start a new connection."
        )
        return True

    except Exception as exc:
        st.query_params.clear()

        st.error(
            "Google Calendar connection failed. "
            f"Error type: {type(exc)._name_}."
        )

        # Display safe explanatory messages, never tokens or secrets.
        if isinstance(exc, RuntimeError):
            st.info(str(exc))

        return True


def is_google_calendar_connected():
    """
    Check whether the signed-in app user has a saved Google token.

    This checks for a saved record; the actual Google operation checks
    whether the credentials are usable.
    """
    user = get_current_user()

    if not user:
        return False

    try:
        response = (
            get_supabase_client()
            .table("google_calendar_tokens")
            .select("user_id")
            .eq("user_id", str(user.id))
            .limit(1)
            .execute()
        )

        return bool(response.data)

    except Exception:
        return False


def get_calendar_service():
    """Load the current user's encrypted Google credentials and build API."""
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

    records = response.data if response else None

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
                "Google authorization has expired and no refresh "
                "token is available. Please reconnect Google Calendar."
            )

        credentials.refresh(Request())

        updated_encrypted_token = _fernet().encrypt(
            credentials.to_json().encode("utf-8")
        ).decode("utf-8")

        client.table("google_calendar_tokens").upsert(
            {
                "user_id": str(user.id),
                "encrypted_token": updated_encrypted_token,
                "updated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
        ).execute()

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
    """Fetch upcoming timed events and convert them to Indian Standard Time."""
    service = get_calendar_service()

    now = datetime.now(LOCAL_TIMEZONE)
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

        # Skip all-day events because this timetable uses times.
        if "dateTime" not in start or "dateTime" not in end:
            continue

        start_dt = datetime.fromisoformat(
            start["dateTime"].replace("Z", "+00:00")
        ).astimezone(LOCAL_TIMEZONE)

        end_dt = datetime.fromisoformat(
            end["dateTime"].replace("Z", "+00:00")
        ).astimezone(LOCAL_TIMEZONE)

        classes.append(
            {
                "subject": event.get("summary", "Untitled"),
                "Day": start_dt.strftime("%A"),
                "Start Time": start_dt.time().replace(tzinfo=None),
                "End Time": end_dt.time().replace(tzinfo=None),
                "Teacher": "",
                "Room": "",
                "Date": start_dt.date(),
                "Source": "Google Calendar",
                "Google Event ID": event.get("id", ""),
            }
        )

    return classes


def create_calendar_event(
    subject,
    event_date,
    start_time,
    end_time,
):
    """Create one event in the signed-in user's primary calendar."""
    if not subject or not subject.strip():
        raise ValueError("Please enter an event title.")

    if end_time <= start_time:
        raise ValueError("End time must be later than start time.")

    service = get_calendar_service()

    start_dt = datetime.combine(
        event_date,
        start_time,
        tzinfo=LOCAL_TIMEZONE,
    )

    end_dt = datetime.combine(
        event_date,
        end_time,
        tzinfo=LOCAL_TIMEZONE,
    )

    event_body = {
        "summary": subject.strip(),
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
    }

    return (
        service.events()
        .insert(
            calendarId="primary",
            body=event_body,
        )
        .execute()
    )