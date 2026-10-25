import streamlit as st
from supabase import create_client


def get_supabase_client():
    
    """Create a server-side Supabase client."""
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SECRET_KEY"],
    )
def get_user_supabase_client():
    """Create a Supabase client using the signed-in user's token."""
    access_token = st.session_state.get("supabase_access_token")

    if not access_token:
        raise ValueError("Please sign in before accessing deadlines.")

    client = get_supabase_client()
    client.postgrest.auth(access_token)

    return client

def sign_up(email, password):
    """Register a new user with the correct confirmation redirect."""
    client = get_supabase_client()
    return client.auth.sign_up({
        "email": email,
        "password": password,
        "options": {
            "email_redirect_to": (
                "https://smart-timetable-assistant-fwamrxbvul7qmvsg9s9mpd.streamlit.app/"
            )
        },
    })


def sign_in(email, password):
    """Sign in and keep the session in Streamlit's server-side state."""
    client = get_supabase_client()
    response = client.auth.sign_in_with_password({
        "email": email,
        "password": password,
    })

    if response.session and response.user:
        st.session_state["supabase_access_token"] = (
            response.session.access_token
        )
        st.session_state["supabase_refresh_token"] = (
            response.session.refresh_token
        )
        st.session_state["supabase_user_id"] = response.user.id
        st.session_state["supabase_user_email"] = response.user.email

    return response


def get_current_user():
    """Verify the stored access token with Supabase."""
    access_token = st.session_state.get("supabase_access_token")

    if not access_token:
        return None

    try:
        client = get_supabase_client()
        response = client.auth.get_user(access_token)
        return response.user
    except Exception:
        return None


def sign_out():
    """Sign out and clear the local session."""
    try:
        access_token = st.session_state.get("supabase_access_token")
        refresh_token = st.session_state.get("supabase_refresh_token")

        if access_token and refresh_token:
            client = get_supabase_client()
            client.auth.set_session(access_token, refresh_token)
            client.auth.sign_out()
    finally:
        for key in (
            "supabase_access_token",
            "supabase_refresh_token",
            "supabase_user_id",
            "supabase_user_email",
        ):
            st.session_state.pop(key, None)