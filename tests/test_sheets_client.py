"""
Tests for src/sheets_client.py

Covers OKRTask dataclass logic and the OKR parsing/filtering logic
without requiring live Google API credentials.
"""

import pytest

from src.sheets_client import OKRTask, get_active_okrs


class TestOKRTask:
    """Unit tests for the OKRTask dataclass logic."""

    def test_remaining_units(self):
        task = OKRTask(name="Blog post", effort_minutes=60, running_count=2, target=5)
        assert task.remaining_units == 3

    def test_remaining_units_at_target(self):
        task = OKRTask(name="Done task", effort_minutes=60, running_count=5, target=5)
        assert task.remaining_units == 0

    def test_remaining_units_no_target(self):
        task = OKRTask(name="No target", effort_minutes=60, running_count=0, target=0)
        assert task.remaining_units == 0

    def test_is_complete_when_at_target(self):
        task = OKRTask(name="Done", effort_minutes=60, running_count=5, target=5)
        assert task.is_complete is True

    def test_is_not_complete_when_below_target(self):
        task = OKRTask(name="In progress", effort_minutes=60, running_count=2, target=5)
        assert task.is_complete is False

    def test_adjusted_effort_proportional(self):
        # 2 out of 5 done → 3/5 remaining → 60 * (3/5) = 36
        task = OKRTask(name="Blog post", effort_minutes=60, running_count=2, target=5)
        assert task.adjusted_effort == 36

    def test_adjusted_effort_zero_progress(self):
        # Nothing done → full effort
        task = OKRTask(name="New task", effort_minutes=90, running_count=0, target=3)
        assert task.adjusted_effort == 90

    def test_adjusted_effort_no_target(self):
        # No target set → return base effort unchanged
        task = OKRTask(name="Open ended", effort_minutes=45, running_count=0, target=0)
        assert task.adjusted_effort == 45

    def test_adjusted_effort_one_unit_left(self):
        # 4 out of 5 done → 1/5 remaining → 60 * (1/5) = 12
        task = OKRTask(name="Almost done", effort_minutes=60, running_count=4, target=5)
        assert task.adjusted_effort == 12


class TestGetActiveOKRs:
    """
    Tests for the OKR parsing/filtering logic using a mock Sheets service.
    """

    def _make_mock_service(self, rows):
        """Create a mock that mimics the Google Sheets API response structure."""

        class MockValues:
            def get(self, **kwargs):
                return self

            def execute(self_inner):
                return {"values": rows}

        class MockSpreadsheets:
            def values(self):
                return MockValues()

        class MockService:
            def spreadsheets(self):
                return MockSpreadsheets()

        return MockService()

    def test_filters_complete_tasks(self, monkeypatch):
        rows = [
            ["", "Key Result", "", "", "Effort", "Running", "Target"],
            ["", "Complete task", "", "", "60", "5", "5"],   # complete → skip
            ["", "Active task", "", "", "30", "1", "5"],     # active → include
        ]
        service = self._make_mock_service(rows)
        monkeypatch.setattr(
            "src.sheets_client._build_sheets_service", lambda *a: service
        )
        tasks = get_active_okrs({}, "user@example.com", "sheet_id", "Tab")
        assert len(tasks) == 1
        assert tasks[0].name == "Active task"

    def test_filters_zero_effort_tasks(self, monkeypatch):
        rows = [
            ["", "Key Result", "", "", "Effort", "Running", "Target"],
            ["", "No effort task", "", "", "0", "0", "5"],
            ["", "With effort", "", "", "60", "0", "5"],
        ]
        service = self._make_mock_service(rows)
        monkeypatch.setattr(
            "src.sheets_client._build_sheets_service", lambda *a: service
        )
        tasks = get_active_okrs({}, "user@example.com", "sheet_id", "Tab")
        assert len(tasks) == 1
        assert tasks[0].name == "With effort"

    def test_sorts_by_remaining_units_descending(self, monkeypatch):
        rows = [
            ["", "Key Result", "", "", "Effort", "Running", "Target"],
            ["", "Almost done", "", "", "60", "4", "5"],    # 1 remaining
            ["", "Just started", "", "", "60", "0", "5"],   # 5 remaining
            ["", "Halfway", "", "", "60", "2", "5"],         # 3 remaining
        ]
        service = self._make_mock_service(rows)
        monkeypatch.setattr(
            "src.sheets_client._build_sheets_service", lambda *a: service
        )
        tasks = get_active_okrs({}, "user@example.com", "sheet_id", "Tab")
        assert tasks[0].name == "Just started"
        assert tasks[1].name == "Halfway"
        assert tasks[2].name == "Almost done"

    def test_empty_sheet_returns_empty_list(self, monkeypatch):
        service = self._make_mock_service([])
        monkeypatch.setattr(
            "src.sheets_client._build_sheets_service", lambda *a: service
        )
        tasks = get_active_okrs({}, "user@example.com", "sheet_id", "Tab")
        assert tasks == []

    def test_handles_missing_running_count_and_target(self, monkeypatch):
        rows = [
            ["", "Key Result", "", "", "Effort", "Running", "Target"],
            ["", "Legacy task", "", "", "45", "", ""],  # no running/target
        ]
        service = self._make_mock_service(rows)
        monkeypatch.setattr(
            "src.sheets_client._build_sheets_service", lambda *a: service
        )
        tasks = get_active_okrs({}, "user@example.com", "sheet_id", "Tab")
        # target=0 and running_count=0 → is_complete is False → should be included
        assert len(tasks) == 1
        assert tasks[0].running_count == 0
        assert tasks[0].target == 0
