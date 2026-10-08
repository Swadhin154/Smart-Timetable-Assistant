import os
from datetime import datetime, timedelta

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def get_calendar_service():
    credentials = None

    # Load previously saved Google authorization
    if os.path.exists("token.json"):
        credentials = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    # Refresh the token if it has expired
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    # If there is no valid authorization, ask Google for permission
    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json",
            SCOPES
        )

        credentials = flow.run_local_server(port=0)

        # Save authorization for future runs
        with open("token.json", "w") as token:
            token.write(credentials.to_json())

    # Create connection to Google Calendar API
    service = build(
        "calendar",
        "v3",
        credentials=credentials
    )

    return service


def get_calendar_events():
    service = get_calendar_service()

    now = datetime.now().astimezone()
    end_date = now + timedelta(days=90)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=end_date.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])

    timetable_classes = []

    for event in events:
        start = event.get("start", {})
        end = event.get("end", {})

        # Ignore all-day events because our timetable needs start/end times
        if "dateTime" not in start or "dateTime" not in end:
            continue

        start_datetime = datetime.fromisoformat(
            start["dateTime"].replace("Z", "+00:00")
        )

        end_datetime = datetime.fromisoformat(
            end["dateTime"].replace("Z", "+00:00")
        )

        timetable_classes.append({
            "subject": event.get("summary", "Untitled"),
            "Day": start_datetime.strftime("%A"),
            "Start Time": start_datetime.time(),
            "End Time": end_datetime.time(),
            "Teacher": "",
            "Room": ""
        })

    return timetable_classes