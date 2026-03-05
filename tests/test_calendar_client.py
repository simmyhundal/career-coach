"""
Tests for src/calendar_client.py

These tests cover the pure calculation logic (_calculate_free_time)
without requiring live Google API credentials.
"""

import datetime
import pytest

from src.calendar_client import Availability, _calculate_free_time, _parse_time, _parse_iso


class TestParseTime:
    def test_basic_hhmm(self):
        h, m = _parse_time("09:00")
        assert h == 9
        assert m == 0

    def test_with_minutes(self):
        h, m = _parse_time("17:30")
        assert h == 17
        assert m == 30

    def test_padded_zeros(self):
        h, m = _parse_time("08:05")
        assert h == 8
        assert m == 5


class TestParseIso:
    def test_iso_with_z(self):
        dt = _parse_iso("2024-03-01T09:00:00Z")
        assert dt == datetime.datetime(2024, 3, 1, 9, 0, 0)

    def test_iso_without_z(self):
        dt = _parse_iso("2024-03-01T09:00:00")
        assert dt == datetime.datetime(2024, 3, 1, 9, 0, 0)


class TestCalculateFreeTime:
    """Tests for the white-space calculation logic."""

    _DATE = datetime.date(2024, 3, 1)

    def _dt(self, h: int, m: int = 0) -> datetime.datetime:
        return datetime.datetime(self._DATE.year, self._DATE.month, self._DATE.day, h, m)

    def test_no_meetings_full_day_free(self):
        result = _calculate_free_time(
            busy_slots=[],
            work_start=self._dt(9),
            work_end=self._dt(17),
        )
        assert result.total_minutes == 480  # 8 hours = 480 minutes
        assert result.largest_block == 480

    def test_single_meeting_in_the_middle(self):
        busy = [{"start": "2024-03-01T11:00:00Z", "end": "2024-03-01T12:00:00Z"}]
        result = _calculate_free_time(
            busy_slots=busy,
            work_start=self._dt(9),
            work_end=self._dt(17),
        )
        # 2 hours before + 5 hours after = 420 minutes
        assert result.total_minutes == 420
        # Largest block is 5 hours after = 300 minutes
        assert result.largest_block == 300

    def test_meeting_at_start_of_day(self):
        busy = [{"start": "2024-03-01T09:00:00Z", "end": "2024-03-01T10:00:00Z"}]
        result = _calculate_free_time(
            busy_slots=busy,
            work_start=self._dt(9),
            work_end=self._dt(17),
        )
        # 7 hours after = 420 minutes
        assert result.total_minutes == 420
        assert result.largest_block == 420

    def test_back_to_back_meetings(self):
        busy = [
            {"start": "2024-03-01T09:00:00Z", "end": "2024-03-01T10:00:00Z"},
            {"start": "2024-03-01T10:00:00Z", "end": "2024-03-01T11:00:00Z"},
        ]
        result = _calculate_free_time(
            busy_slots=busy,
            work_start=self._dt(9),
            work_end=self._dt(17),
        )
        # 6 hours after = 360 minutes
        assert result.total_minutes == 360
        assert result.largest_block == 360

    def test_overlapping_meetings(self):
        # Two overlapping meetings: 10-12 and 11-13 → effectively 10-13
        busy = [
            {"start": "2024-03-01T10:00:00Z", "end": "2024-03-01T12:00:00Z"},
            {"start": "2024-03-01T11:00:00Z", "end": "2024-03-01T13:00:00Z"},
        ]
        result = _calculate_free_time(
            busy_slots=busy,
            work_start=self._dt(9),
            work_end=self._dt(17),
        )
        # 1 hour before (60 min) + 4 hours after (240 min) = 300 min
        assert result.total_minutes == 300

    def test_fully_booked_day(self):
        busy = [{"start": "2024-03-01T09:00:00Z", "end": "2024-03-01T17:00:00Z"}]
        result = _calculate_free_time(
            busy_slots=busy,
            work_start=self._dt(9),
            work_end=self._dt(17),
        )
        assert result.total_minutes == 0
        assert result.largest_block == 0

    def test_returns_availability_dataclass(self):
        result = _calculate_free_time([], self._dt(9), self._dt(17))
        assert isinstance(result, Availability)
