"""
ai_coach.py – Calls the OpenAI Chat Completions API to prioritize OKR tasks
based on the user's available calendar white space.
"""

from __future__ import annotations

from openai import OpenAI

from .sheets_client import OKRTask
from .calendar_client import Availability


def prioritize_tasks_with_ai(
    openai_api_key: str,
    availability: Availability,
    tasks: list[OKRTask],
) -> str:
    """
    Ask GPT-4o to pick the best 2–4 tasks for the day given the user's
    available time and OKR progress.

    Args:
        openai_api_key: OpenAI secret key.
        availability: Today's free-time summary.
        tasks: Active OKR tasks (already filtered & sorted by sheets_client).

    Returns:
        A formatted string with the AI's "Daily Action Plan" recommendation.
    """
    okr_summary = _format_okr_summary(tasks)
    prompt = _build_prompt(availability, okr_summary)
    return _call_openai(openai_api_key, prompt)


def _format_okr_summary(tasks: list[OKRTask]) -> str:
    """
    Format OKR tasks for the AI prompt, including personalization data
    (running count, target, and adjusted effort based on remaining units).
    """
    lines = []
    for task in tasks:
        if task.target > 0:
            progress = f"{task.running_count}/{task.target} done"
            effort_note = (
                f"Adjusted effort: {task.adjusted_effort} mins "
                f"(base: {task.effort_minutes} mins, {progress})"
            )
        else:
            effort_note = f"Effort: {task.effort_minutes} mins"
        lines.append(f"- {task.name} ({effort_note})")
    return "\n".join(lines)


def _build_prompt(availability: Availability, okr_summary: str) -> str:
    capacity_cap = round(availability.total_minutes * 0.8)
    return (
        f"Today I have {availability.total_minutes} minutes of total free time.\n"
        f"My largest contiguous focus block is {availability.largest_block} minutes.\n\n"
        f"Based on my OKRs, please pick the best 2-4 tasks to tackle today:\n"
        f"{okr_summary}\n\n"
        f"Instructions:\n"
        f"1. Do not exceed a total of {capacity_cap} minutes (80% capacity rule).\n"
        f"2. Prioritize tasks that fit into my largest focus block first.\n"
        f"3. Prefer tasks with the most remaining units relative to their target "
        f"(they appear first in the list).\n"
        f"4. Format the response as a bulleted 'Daily Action Plan'.\n"
        f"5. Keep the response concise, encouraging, and under 150 words."
    )


def _call_openai(api_key: str, prompt: str) -> str:
    """Send the prompt to OpenAI and return the assistant's response text."""
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a daily career coach. Your goal is to select the most "
                    "high-leverage tasks from a list of OKRs that fit within the user's "
                    "specific calendar availability. Keep recommendations concise, "
                    "encouraging, and under 150 words."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content
