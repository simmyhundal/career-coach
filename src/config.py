"""
config.py – Loads and validates all environment variables and
reads the run-time configuration from the Google Sheet (Sheet2).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass
class AppConfig:
    """Holds all runtime configuration values."""

    # Google credentials
    service_account_info: dict
    delegated_user: str

    # OpenAI
    openai_api_key: str

    # Sheet identifiers
    config_sheet_id: str

    # Values read from Sheet2 at runtime (populated by sheets_client)
    work_start: str = "09:00"
    work_end: str = "17:00"
    user_email: str = ""
    okr_sheet_id: str = ""
    okr_tab_name: str = ""


def load_env_config() -> AppConfig:
    """
    Load configuration from environment variables.

    Required environment variables:
      GOOGLE_SERVICE_ACCOUNT_JSON – full JSON string of the service-account key
      GOOGLE_DELEGATED_USER        – the Google Workspace email to impersonate
      OPENAI_API_KEY               – OpenAI secret key
      CONFIG_SHEET_ID              – Spreadsheet ID that contains Sheet2
                                     (and the 'Google CalendarIds' tab)
    """
    sa_json_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not sa_json_str:
        raise EnvironmentError("Missing required env var: GOOGLE_SERVICE_ACCOUNT_JSON")

    try:
        service_account_info = json.loads(sa_json_str)
    except json.JSONDecodeError as exc:
        raise EnvironmentError(
            "GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON"
        ) from exc

    delegated_user = os.environ.get("GOOGLE_DELEGATED_USER", "")
    if not delegated_user:
        raise EnvironmentError("Missing required env var: GOOGLE_DELEGATED_USER")

    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_api_key:
        raise EnvironmentError("Missing required env var: OPENAI_API_KEY")

    config_sheet_id = os.environ.get("CONFIG_SHEET_ID", "")
    if not config_sheet_id:
        raise EnvironmentError("Missing required env var: CONFIG_SHEET_ID")

    return AppConfig(
        service_account_info=service_account_info,
        delegated_user=delegated_user,
        openai_api_key=openai_api_key,
        config_sheet_id=config_sheet_id,
    )
