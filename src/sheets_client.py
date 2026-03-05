"""
sheets_client.py – Reads configuration and OKR data from Google Sheets.

Config sheet layout (Sheet2, columns B:C, starting row 2):
  B: Key name  (e.g. WORK_START, WORK_END, USER_EMAIL, OKR_SHEET_ID, OKR_TAB_NAME)
  C: Value

OKR sheet layout (header row assumed):
  Column B (index 1): Key Result name
  Column E (index 4): Effort in minutes
  Column F (index 5): Running Count
  Column G (index 6): Target

Calendar IDs sheet layout ('Google CalendarIds', column B, starting row 2):
  B: Calendar ID string
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build


SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


@dataclass
class OKRTask:
    """Represents a single OKR task."""

    name: str
    effort_minutes: int
    running_count: int
    target: int

    @property
    def remaining_units(self) -> int:
        """How many more units need to be completed to hit the target."""
        return max(0, self.target - self.running_count)

    @property
    def is_complete(self) -> bool:
        # A task with no target set (target=0) is never complete
        return self.target > 0 and self.running_count >= self.target

    @property
    def adjusted_effort(self) -> int:
        """
        Scales effort proportionally by how much is left.
        If a task is 40% done (2/5), the remaining effort is 60% of base effort.
        """
        if self.target <= 0:
            return self.effort_minutes
        fraction_remaining = self.remaining_units / self.target
        return round(self.effort_minutes * fraction_remaining)


def _build_sheets_service(service_account_info: dict, delegated_user: str) -> Any:
    """Build and return an authenticated Google Sheets API client."""
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SHEETS_SCOPES
    )
    delegated_credentials = credentials.with_subject(delegated_user)
    return build("sheets", "v4", credentials=delegated_credentials)


def get_sheet_config(
    service_account_info: dict,
    delegated_user: str,
    config_sheet_id: str,
    tab_name: str = "Sheet2",
) -> dict[str, str]:
    """
    Read key→value config pairs from the Sheet2 tab (columns B:C, rows 2-10).

    Returns a dict such as:
        {"WORK_START": "09:00", "WORK_END": "17:00", "USER_EMAIL": "you@example.com", ...}
    """
    service = _build_sheets_service(service_account_info, delegated_user)
    range_name = f"{tab_name}!B2:C10"
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=config_sheet_id, range=range_name)
        .execute()
    )
    rows = result.get("values", [])
    config: dict[str, str] = {}
    for row in rows:
        if len(row) >= 2 and row[0]:
            config[str(row[0]).strip()] = str(row[1]).strip() if row[1] else ""
    return config


def get_calendar_ids(
    service_account_info: dict,
    delegated_user: str,
    config_sheet_id: str,
) -> list[str]:
    """
    Read calendar IDs from the 'Google CalendarIds' tab (column B, starting row 2).
    """
    service = _build_sheets_service(service_account_info, delegated_user)
    range_name = "Google CalendarIds!B2:B"
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=config_sheet_id, range=range_name)
        .execute()
    )
    rows = result.get("values", [])
    return [row[0] for row in rows if row and row[0]]


def get_active_okrs(
    service_account_info: dict,
    delegated_user: str,
    okr_sheet_id: str,
    okr_tab_name: str,
) -> list[OKRTask]:
    """
    Read OKR tasks from the specified sheet and tab.

    Only tasks that have a name, positive effort, and are not yet complete
    (Running Count < Target) are returned.  Tasks are sorted so that those
    furthest from their target come first.
    """
    service = _build_sheets_service(service_account_info, delegated_user)
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=okr_sheet_id, range=okr_tab_name)
        .execute()
    )
    rows = result.get("values", [])
    if not rows:
        return []

    tasks: list[OKRTask] = []
    for row in rows[1:]:  # skip header row
        # Pad row so index access is safe
        row = list(row) + [""] * 7

        name = str(row[1]).strip()
        effort_raw = row[4]
        running_raw = row[5]
        target_raw = row[6]

        if not name:
            continue

        try:
            effort = int(float(effort_raw)) if effort_raw else 0
        except (ValueError, TypeError):
            effort = 0

        try:
            running_count = int(float(running_raw)) if running_raw else 0
        except (ValueError, TypeError):
            running_count = 0

        try:
            target = int(float(target_raw)) if target_raw else 0
        except (ValueError, TypeError):
            target = 0

        if effort <= 0:
            continue

        task = OKRTask(
            name=name,
            effort_minutes=effort,
            running_count=running_count,
            target=target,
        )

        # Only include tasks that are not yet fully complete
        if not task.is_complete:
            tasks.append(task)

    # Sort: tasks furthest from target first (most remaining_units)
    tasks.sort(key=lambda t: t.remaining_units, reverse=True)
    return tasks
