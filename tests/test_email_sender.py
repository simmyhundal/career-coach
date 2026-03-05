"""
Tests for src/email_sender.py

Tests the HTML/plain-text body generation and MIME message building
without making live Gmail API calls.
"""

import base64
import email
import pytest

from src.email_sender import (
    _build_html_body,
    _build_plain_body,
    _build_mime_message,
)
from src.calendar_client import Availability


def _decode_base64url(s: str) -> bytes:
    """Decode a base64url string, adding the correct amount of padding."""
    padding = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


@pytest.fixture
def availability():
    return Availability(total_minutes=300, largest_block=120)


class TestBuildPlainBody:
    def test_contains_total_minutes(self, availability):
        body = _build_plain_body("- Do the thing", availability)
        assert "300 minutes" in body

    def test_contains_largest_block(self, availability):
        body = _build_plain_body("- Do the thing", availability)
        assert "120 minutes" in body

    def test_contains_ai_content(self, availability):
        body = _build_plain_body("- Write a blog post", availability)
        assert "Write a blog post" in body

    def test_contains_greeting(self, availability):
        body = _build_plain_body("", availability)
        assert "Good morning" in body


class TestBuildHtmlBody:
    def test_contains_total_minutes(self, availability):
        html = _build_html_body("- Do the thing", availability, "Monday, March 1, 2024")
        assert "300" in html

    def test_contains_largest_block(self, availability):
        html = _build_html_body("- Do the thing", availability, "Monday, March 1, 2024")
        assert "120" in html

    def test_contains_date(self, availability):
        html = _build_html_body("- Do the thing", availability, "Monday, March 1, 2024")
        assert "Monday, March 1, 2024" in html

    def test_is_valid_html(self, availability):
        html = _build_html_body("- Task one\n- Task two", availability, "Test Day")
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_bullet_items_rendered_as_li(self, availability):
        html = _build_html_body("- Write blog post\n- Record video", availability, "Today")
        assert "<li>Write blog post</li>" in html
        assert "<li>Record video</li>" in html


class TestBuildMimeMessage:
    def test_returns_base64_encoded_string(self):
        raw = _build_mime_message(
            sender="sender@example.com",
            recipient="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Hello</p>",
            plain_body="Hello",
        )
        # Should be a valid base64url string
        decoded = _decode_base64url(raw)
        assert len(decoded) > 0

    def test_decoded_message_has_correct_headers(self):
        raw = _build_mime_message(
            sender="sender@example.com",
            recipient="recipient@example.com",
            subject="🚀 Test Subject",
            html_body="<p>Hello</p>",
            plain_body="Hello",
        )
        decoded_bytes = _decode_base64url(raw)
        msg = email.message_from_bytes(decoded_bytes)
        assert msg["From"] == "sender@example.com"
        assert msg["To"] == "recipient@example.com"

    def test_decoded_message_is_multipart_alternative(self):
        raw = _build_mime_message(
            sender="a@example.com",
            recipient="b@example.com",
            subject="Subject",
            html_body="<p>Hi</p>",
            plain_body="Hi",
        )
        decoded_bytes = _decode_base64url(raw)
        msg = email.message_from_bytes(decoded_bytes)
        assert msg.get_content_type() == "multipart/alternative"
        parts = msg.get_payload()
        assert len(parts) == 2
