"""
calendar_client.py – Queries the Google Calendar API for free/busy information
and calculates how many minutes of "white space" the user has today.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build


CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


@dataclass
class Availability:
    """Summary of a user's daily free time."""

    total_minutes: int
    largest_block: int


def _build_calendar_service(service_account_info: dict, delegated_user: str) -> Any:
    """Build and return an authenticated Google Calendar API client."""
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=CALENDAR_SCOPES
    )
    delegated_credentials = credentials.with_subject(delegated_user)
    return build("calendar", "v3", credentials=delegated_credentials)


def get_daily_availability(
    service_account_info: dict,
    delegated_user: str,
    calendar_ids: list[str],
    work_start: str,
    work_end: str,
) -> Availability:
    """
    Calculate the total free minutes and largest contiguous free block for today.

    Args:
        service_account_info: Parsed service-account JSON dict.
        delegated_user: Email of the user whose calendar to inspect.
        calendar_ids: List of Google Calendar IDs to include in the query.
        work_start: Work-day start time as "HH:MM".
        work_end: Work-day end time as "HH:MM".

    Returns:
        An Availability dataclass with total_minutes and largest_block.
    """
    today = datetime.date.today()
    start_h, start_m = _parse_time(work_start)
    end_h, end_m = _parse_time(work_end)

    today_start = datetime.datetime(today.year, today.month, today.day, start_h, start_m)
    today_end = datetime.datetime(today.year, today.month, today.day, end_h, end_m)

    service = _build_calendar_service(service_account_info, delegated_user)

    body = {
        "timeMin": today_start.isoformat() + "Z",
        "timeMax": today_end.isoformat() + "Z",
        "items": [{"id": cal_id} for cal_id in calendar_ids],
    }
    response = service.freebusy().query(body=body).execute()

    busy_slots: list[dict] = []
    for cal_data in response.get("calendars", {}).values():
        busy_slots.extend(cal_data.get("busy", []))

    busy_slots.sort(key=lambda s: s["start"])

    return _calculate_free_time(busy_slots, today_start, today_end)


def _parse_time(time_str: str) -> tuple[int, int]:
    """Parse an "HH:MM" string into (hours, minutes)."""
    parts = str(time_str).strip().split(":")
    return int(parts[0]), int(parts[1])


def _calculate_free_time(
    busy_slots: list[dict],
    work_start: datetime.datetime,
    work_end: datetime.datetime,
) -> Availability:
    """
    Given a sorted list of busy slots, calculate total free minutes and
    the largest contiguous free block within the work window.
    """
    free_minutes = 0.0
    largest_block = 0.0
    last_end = work_start

    for slot in busy_slots:
        slot_start = _parse_iso(slot["start"])
        slot_end = _parse_iso(slot["end"])

        if slot_start > last_end:
            gap = (slot_start - last_end).total_seconds() / 60
            free_minutes += gap
            if gap > largest_block:
                largest_block = gap

        if slot_end > last_end:
            last_end = slot_end

    # Final gap between last meeting and end of workday
    if work_end > last_end:
        final_gap = (work_end - last_end).total_seconds() / 60
        free_minutes += final_gap
        if final_gap > largest_block:
            largest_block = final_gap

    return Availability(
        total_minutes=round(free_minutes),
        largest_block=round(largest_block),
    )


def _parse_iso(iso_str: str) -> datetime.datetime:
    """Parse an ISO 8601 datetime string, stripping the trailing 'Z' if present."""
    return datetime.datetime.fromisoformat(iso_str.rstrip("Z"))
