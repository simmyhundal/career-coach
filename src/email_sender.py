"""
email_sender.py – Formats and sends the daily coaching email via the Gmail API.
"""

from __future__ import annotations

import base64
import datetime
import email.mime.multipart
import email.mime.text

from google.oauth2 import service_account
from googleapiclient.discovery import build

from .calendar_client import Availability


GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def send_coach_email(
    service_account_info: dict,
    delegated_user: str,
    recipient: str,
    ai_content: str,
    availability: Availability,
) -> None:
    """
    Send the daily career-coach email as a clean HTML message.

    Args:
        service_account_info: Parsed service-account JSON dict.
        delegated_user: The Google Workspace user to impersonate (sender).
        recipient: Destination email address.
        ai_content: The AI-generated action plan text.
        availability: Today's free-time summary for the email header.
    """
    today_raw = datetime.date.today()
    today = today_raw.strftime("%A, %B {day}, %Y").replace(
        "{day}", str(today_raw.day)
    )
    subject = f"🚀 Your Daily Career Coach: {today}"
    html_body = _build_html_body(ai_content, availability, today)
    plain_body = _build_plain_body(ai_content, availability)

    message = _build_mime_message(
        sender=delegated_user,
        recipient=recipient,
        subject=subject,
        html_body=html_body,
        plain_body=plain_body,
    )
    _send_via_gmail_api(service_account_info, delegated_user, message)


def _build_html_body(
    ai_content: str, availability: Availability, today: str
) -> str:
    """Render the email as clean, readable HTML."""
    # Convert plain-text bullet lines to HTML list items
    lines = ai_content.strip().split("\n")
    list_items = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Remove leading bullet characters for clean HTML list
        clean = stripped.lstrip("-•* ").strip()
        if clean:
            list_items += f"        <li>{clean}</li>\n"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      background: #f4f6f8;
      margin: 0;
      padding: 24px;
    }}
    .card {{
      background: #ffffff;
      border-radius: 12px;
      padding: 32px 40px;
      max-width: 640px;
      margin: 0 auto;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    h1 {{
      font-size: 22px;
      margin-top: 0;
      color: #1a1a2e;
    }}
    .badge {{
      display: inline-block;
      background: #e8f4fd;
      color: #1565c0;
      border-radius: 20px;
      padding: 6px 16px;
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 24px;
    }}
    h2 {{
      font-size: 16px;
      color: #333;
      border-bottom: 2px solid #e0e0e0;
      padding-bottom: 8px;
    }}
    ul {{
      padding-left: 20px;
      line-height: 1.8;
      color: #444;
    }}
    .footer {{
      margin-top: 28px;
      font-size: 13px;
      color: #888;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>🚀 Your Daily Career Coach</h1>
    <div class="badge">📅 {today}</div>
    <p>
      Good morning! Today you have
      <strong>{availability.total_minutes} minutes</strong> of "White Space"
      across your calendars (largest focus block:
      <strong>{availability.largest_block} minutes</strong>).
    </p>
    <h2>🎯 Daily Action Plan</h2>
    <ul>
{list_items}    </ul>
    <p>Go get 'em! 💪</p>
    <div class="footer">
      Powered by AI-Powered Daily Career Coach &bull; Delivered via GitHub Actions
    </div>
  </div>
</body>
</html>"""


def _build_plain_body(ai_content: str, availability: Availability) -> str:
    """Build a plain-text fallback version of the email."""
    return (
        f"Good morning!\n\n"
        f"Today you have {availability.total_minutes} minutes of White Space "
        f"(largest block: {availability.largest_block} minutes).\n\n"
        f"Daily Action Plan\n"
        f"-----------------\n"
        f"{ai_content}\n\n"
        f"Go get 'em!"
    )


def _build_mime_message(
    sender: str,
    recipient: str,
    subject: str,
    html_body: str,
    plain_body: str,
) -> str:
    """
    Assemble a multipart/alternative MIME message and return it as a
    base64url-encoded string suitable for the Gmail API.
    """
    msg = email.mime.multipart.MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(email.mime.text.MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(email.mime.text.MIMEText(html_body, "html", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return raw


def _send_via_gmail_api(
    service_account_info: dict, delegated_user: str, raw_message: str
) -> None:
    """Send a pre-encoded MIME message via the Gmail API."""
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=GMAIL_SCOPES
    )
    delegated_credentials = credentials.with_subject(delegated_user)
    service = build("gmail", "v1", credentials=delegated_credentials)
    service.users().messages().send(
        userId="me", body={"raw": raw_message}
    ).execute()
