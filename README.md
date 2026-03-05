# AI-Powered Daily Career Coach

An automated daily career coaching system that bridges your Google Calendar and OKR Google Sheet to deliver a personalized, AI-curated action plan every morning via email.

## Overview

This project ensures your high-leverage goals actually get scheduled into your available "white space" each day. Every morning at 07:30 UTC, a GitHub Action:

1. Reads your work-hours configuration from a Google Sheet
2. Queries Google Calendar to calculate free time ("white space")
3. Reads active OKRs (filtering by Running Count vs. Target)
4. Calls OpenAI GPT to prioritize the best 2–4 tasks for the day
5. Sends a clean HTML email with the daily action plan

## Architecture

```
GitHub Actions (cron 07:30 UTC)
         │
         ▼
   src/main.py  ◄──────────────────────────────────────────────────────┐
         │                                                              │
    ┌────┴─────────────────────────────────────────────────┐           │
    │                                                      │           │
    ▼                                                      ▼           │
src/calendar_client.py                           src/sheets_client.py  │
  Google Calendar API                              Google Sheets API   │
  (Free/Busy query)                                (OKR data + config) │
    │                                                      │           │
    └──────────────────────┬───────────────────────────────┘           │
                           │                                           │
                           ▼                                           │
                    src/ai_coach.py                                    │
                     OpenAI GPT-4o                                     │
                  (Task Prioritization)                                 │
                           │                                           │
                           ▼                                           │
                  src/email_sender.py ─────────────────────────────────┘
                   Gmail API (HTML email)
```

**Bridge between Google Calendar & Sheets OKRs**: the system treats your Google Calendar as the source of truth for available time, and your OKR Sheet as the source of truth for what matters most.

## Project Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| **v1.0-MVP** | Original Google Apps Script implementation | ✅ Complete |
| **v2.0-Python-Cloud** | Python-based cloud architecture (this repo) | 🚧 In Progress |
| **v3.0-Vibe-Coding-Integration** | Continuous AI-led updates integration | 🔜 Planned |

## Repository Structure

```
career-coach/
├── src/
│   ├── main.py            # Master orchestration entry point
│   ├── config.py          # Environment variable & config management
│   ├── calendar_client.py # Google Calendar free/busy queries
│   ├── sheets_client.py   # Google Sheets OKR & config parsing
│   ├── ai_coach.py        # OpenAI GPT task prioritization
│   └── email_sender.py    # HTML email formatting & Gmail API sender
├── tests/
│   ├── test_calendar_client.py
│   ├── test_sheets_client.py
│   ├── test_ai_coach.py
│   └── test_email_sender.py
├── .github/
│   └── workflows/
│       └── daily_coach.yml  # Scheduled GitHub Action (07:30 UTC daily)
├── requirements.txt
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- A Google Cloud project with the following APIs enabled:
  - Google Calendar API
  - Google Sheets API
  - Gmail API
- A Google Service Account with domain-wide delegation (for Calendar + Sheets access)
- An OpenAI API key

### Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable **Google Calendar API**, **Google Sheets API**, and **Gmail API**.
3. Create a **Service Account** and download the JSON key.
4. Enable **Domain-Wide Delegation** on the service account.
5. In your Google Workspace Admin console, grant the service account the following OAuth scopes:
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/spreadsheets.readonly`
   - `https://www.googleapis.com/auth/gmail.send`

### Google Sheet Layout

#### Config Sheet (`Sheet2`)

| Column B (Key)  | Column C (Value)           |
|-----------------|---------------------------|
| WORK_START      | 09:00                     |
| WORK_END        | 17:00                     |
| USER_EMAIL      | you@example.com           |
| OKR_SHEET_ID    | `<spreadsheet-id>`        |
| OKR_TAB_NAME    | March OKRs                |

#### OKR Sheet

| A | B (Key Result) | C | D | E (Effort mins) | F (Running Count) | G (Target) |
|---|----------------|---|---|-----------------|-------------------|------------|
|   | Write blog post |   |   | 60              | 2                 | 5          |
|   | Record video    |   |   | 90              | 0                 | 3          |

#### Calendar IDs Sheet (`Google CalendarIds`)

| Column B            |
|---------------------|
| primary             |
| team@example.com    |

### Local Development

```bash
# Clone and install dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
export GOOGLE_DELEGATED_USER='you@example.com'
export OPENAI_API_KEY='sk-...'
export CONFIG_SHEET_ID='<your-config-spreadsheet-id>'

# Run the coach
python src/main.py
```

### GitHub Actions Setup (Recommended)

Add the following **repository secrets** in Settings → Secrets and Variables → Actions:

| Secret Name                  | Description                                      |
|------------------------------|--------------------------------------------------|
| `GOOGLE_SERVICE_ACCOUNT_JSON`| Full JSON content of the service account key     |
| `GOOGLE_DELEGATED_USER`      | Email of the user to impersonate (your email)    |
| `OPENAI_API_KEY`             | Your OpenAI API key                              |
| `CONFIG_SHEET_ID`            | The Google Spreadsheet ID containing Sheet2      |

The workflow runs automatically at **07:30 UTC every day**. You can also trigger it manually from the Actions tab.

### Running Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Known Issues / Backlog

- **[BUG/High Priority] Scheduler Failure**: The original GAS daily trigger was inconsistent. This has been resolved by migrating to a GitHub Actions cron schedule.
- **[Feature] Personalization Logic**: OKR parsing now incorporates the "Running Count" and "Target" columns to dynamically adjust task priority and effort.
- **[Feature] Human-Readable Formatting**: Email is now rendered as clean HTML/CSS for better readability.

## Environment Variables Reference

| Variable                      | Required | Description                                         |
|-------------------------------|----------|-----------------------------------------------------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | ✅       | Service account credentials JSON (as a string)      |
| `GOOGLE_DELEGATED_USER`       | ✅       | Google Workspace user email to impersonate          |
| `OPENAI_API_KEY`              | ✅       | OpenAI API key                                      |
| `CONFIG_SHEET_ID`             | ✅       | Spreadsheet ID for the config/calendar-IDs sheets   |

