"""
Tests for src/ai_coach.py

Tests the prompt-building and OKR summary formatting logic without
making live calls to the OpenAI API.
"""

import pytest

from src.ai_coach import _format_okr_summary, _build_prompt
from src.calendar_client import Availability
from src.sheets_client import OKRTask


class TestFormatOKRSummary:
    def test_task_with_target_shows_progress(self):
        tasks = [OKRTask(name="Blog post", effort_minutes=60, running_count=2, target=5)]
        summary = _format_okr_summary(tasks)
        assert "Blog post" in summary
        assert "2/5 done" in summary
        assert "Adjusted effort" in summary

    def test_task_without_target_shows_base_effort(self):
        tasks = [OKRTask(name="Open task", effort_minutes=45, running_count=0, target=0)]
        summary = _format_okr_summary(tasks)
        assert "Open task" in summary
        assert "Effort: 45 mins" in summary

    def test_multiple_tasks_all_listed(self):
        tasks = [
            OKRTask(name="Task A", effort_minutes=30, running_count=0, target=3),
            OKRTask(name="Task B", effort_minutes=60, running_count=1, target=4),
        ]
        summary = _format_okr_summary(tasks)
        assert "Task A" in summary
        assert "Task B" in summary

    def test_empty_tasks_returns_empty_string(self):
        assert _format_okr_summary([]) == ""


class TestBuildPrompt:
    def test_prompt_contains_total_minutes(self):
        avail = Availability(total_minutes=240, largest_block=120)
        prompt = _build_prompt(avail, "- Task A (Effort: 30 mins)")
        assert "240 minutes" in prompt

    def test_prompt_contains_largest_block(self):
        avail = Availability(total_minutes=240, largest_block=120)
        prompt = _build_prompt(avail, "- Task A (Effort: 30 mins)")
        assert "120 minutes" in prompt

    def test_prompt_contains_80_percent_capacity(self):
        avail = Availability(total_minutes=200, largest_block=100)
        prompt = _build_prompt(avail, "- Task A")
        # 80% of 200 = 160
        assert "160" in prompt

    def test_prompt_contains_okr_summary(self):
        avail = Availability(total_minutes=300, largest_block=150)
        summary = "- Write blog post (Effort: 60 mins)"
        prompt = _build_prompt(avail, summary)
        assert "Write blog post" in prompt
