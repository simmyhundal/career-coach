"""
main.py – Entry point for the AI-Powered Daily Career Coach.

Run with:
    python src/main.py

Required environment variables (see README.md for full documentation):
    GOOGLE_SERVICE_ACCOUNT_JSON
    GOOGLE_DELEGATED_USER
    OPENAI_API_KEY
    CONFIG_SHEET_ID
"""

from __future__ import annotations

import sys

from .config import load_env_config
from .calendar_client import get_daily_availability
from .sheets_client import get_sheet_config, get_calendar_ids, get_active_okrs
from .ai_coach import prioritize_tasks_with_ai
from .email_sender import send_coach_email


def run_daily_coach() -> None:
    """
    Master orchestration function – mirrors the original GAS runDailyCoach().

    Steps:
      1. Load environment variables.
      2. Read runtime config from Sheet2 (WORK_START, WORK_END, USER_EMAIL, …).
      3. Fetch Calendar IDs.
      4. Calculate today's white space / availability.
      5. Fetch active OKRs (filtered & sorted by remaining progress).
      6. Ask the AI to prioritize tasks.
      7. Send the daily coaching email.
    """
    print("🚀 Daily Career Coach starting…")

    # 1. Load env config
    cfg = load_env_config()

    # 2. Read Sheet2 config
    print("  📋 Loading sheet config…")
    sheet_cfg = get_sheet_config(
        cfg.service_account_info,
        cfg.delegated_user,
        cfg.config_sheet_id,
    )

    work_start = sheet_cfg.get("WORK_START", "09:00")
    work_end = sheet_cfg.get("WORK_END", "17:00")
    user_email = sheet_cfg.get("USER_EMAIL", "")
    okr_sheet_id = sheet_cfg.get("OKR_SHEET_ID", "")
    okr_tab_name = sheet_cfg.get("OKR_TAB_NAME", "")

    if not user_email:
        raise ValueError("USER_EMAIL not found in Sheet2 config.")
    if not okr_sheet_id:
        raise ValueError("OKR_SHEET_ID not found in Sheet2 config.")
    if not okr_tab_name:
        raise ValueError("OKR_TAB_NAME not found in Sheet2 config.")

    print(f"  ✅ Config loaded (work hours: {work_start}–{work_end})")

    # 3. Fetch Calendar IDs
    print("  📅 Fetching calendar IDs…")
    calendar_ids = get_calendar_ids(
        cfg.service_account_info,
        cfg.delegated_user,
        cfg.config_sheet_id,
    )
    if not calendar_ids:
        print("  ⚠️  No calendar IDs found; defaulting to 'primary'.")
        calendar_ids = ["primary"]
    print(f"  ✅ Found {len(calendar_ids)} calendar(s).")

    # 4. Calculate availability
    print("  🕐 Calculating today's availability…")
    availability = get_daily_availability(
        cfg.service_account_info,
        cfg.delegated_user,
        calendar_ids,
        work_start,
        work_end,
    )
    print(
        f"  ✅ White space: {availability.total_minutes} min total, "
        f"{availability.largest_block} min largest block."
    )

    # 5. Fetch active OKRs
    print("  📊 Fetching active OKRs…")
    tasks = get_active_okrs(
        cfg.service_account_info,
        cfg.delegated_user,
        okr_sheet_id,
        okr_tab_name,
    )
    if not tasks:
        print("  ⚠️  No active OKR tasks found. Nothing to do today!")
        return
    print(f"  ✅ Found {len(tasks)} active OKR task(s).")

    # 6. AI prioritization
    print("  🤖 Asking AI to prioritize tasks…")
    ai_content = prioritize_tasks_with_ai(
        cfg.openai_api_key,
        availability,
        tasks,
    )
    print("  ✅ AI recommendation received.")

    # 7. Send email
    print(f"  📧 Sending coaching email to {user_email}…")
    send_coach_email(
        cfg.service_account_info,
        cfg.delegated_user,
        user_email,
        ai_content,
        availability,
    )
    print("  ✅ Email sent successfully!")
    print("🎯 Daily Career Coach complete.")


if __name__ == "__main__":
    try:
        run_daily_coach()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Error: {exc}", file=sys.stderr)
        sys.exit(1)
