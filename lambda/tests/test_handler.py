"""Integration tests for the Lambda handler.

Mocks the ICS fetch so we don't hit the network, but exercises the full
request → parse → PDF generation → response flow.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from handler import handler
from ics_fetch import FetchError

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def synthetic_ics_text() -> str:
    return (FIXTURES_DIR / "synthetic_6th_grade.ics").read_text()


def _make_event(body: dict) -> dict:
    return {
        "body": json.dumps(body),
        "isBase64Encoded": False,
    }


class TestHandlerSuccess:
    """Happy path: valid request produces a PDF response."""

    def test_generates_pdf(self, synthetic_ics_text: str) -> None:
        event = _make_event(
            {
                "ics_url": "https://school.myschoolapp.com/podium/feed/iCal.aspx?z=abc123",
                "student_name": "TestKid",
                "grade": 6,
            }
        )

        with patch("handler.fetch_ics", return_value=synthetic_ics_text):
            response = handler(event, None)

        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/pdf"
        assert "TestKid_planner.pdf" in response["headers"]["Content-Disposition"]
        assert response["isBase64Encoded"] is True

        # Verify it's valid base64 that decodes to a PDF
        pdf_bytes = base64.b64decode(response["body"])
        assert pdf_bytes[:4] == b"%PDF"
        assert len(pdf_bytes) > 1000  # A real PDF should be more than trivial

    def test_generates_pdf_without_optional_fields(self, synthetic_ics_text: str) -> None:
        event = _make_event(
            {
                "ics_url": "https://school.myschoolapp.com/podium/feed/iCal.aspx?z=abc123",
            }
        )

        with patch("handler.fetch_ics", return_value=synthetic_ics_text):
            response = handler(event, None)

        assert response["statusCode"] == 200
        assert "planner.pdf" in response["headers"]["Content-Disposition"]

    def test_handles_base64_encoded_body(self, synthetic_ics_text: str) -> None:
        body_str = json.dumps(
            {
                "ics_url": "https://school.myschoolapp.com/podium/feed/iCal.aspx?z=abc123",
                "student_name": "Base64Kid",
            }
        )
        event = {
            "body": base64.b64encode(body_str.encode()).decode(),
            "isBase64Encoded": True,
        }

        with patch("handler.fetch_ics", return_value=synthetic_ics_text):
            response = handler(event, None)

        assert response["statusCode"] == 200


class TestHandlerThemeAndBlocks:
    """theme + combine_blocks request parameters."""

    def test_theme_and_combine_blocks(self, synthetic_ics_text: str) -> None:
        event = _make_event(
            {
                "ics_url": "https://school.myschoolapp.com/podium/feed/iCal.aspx?z=abc",
                "theme": "video_games",
                "combine_blocks": True,
            }
        )
        with patch("handler.fetch_ics", return_value=synthetic_ics_text):
            response = handler(event, None)
        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/pdf"

    def test_unknown_theme_still_succeeds(self, synthetic_ics_text: str) -> None:
        """Unknown theme falls back to classic — not an error."""
        event = _make_event(
            {
                "ics_url": "https://school.myschoolapp.com/podium/feed/iCal.aspx?z=abc",
                "theme": "does-not-exist",
            }
        )
        with patch("handler.fetch_ics", return_value=synthetic_ics_text):
            response = handler(event, None)
        assert response["statusCode"] == 200

    def test_combine_blocks_as_string(self, synthetic_ics_text: str) -> None:
        """combine_blocks accepts string 'true' (form-style)."""
        event = _make_event(
            {
                "ics_url": "https://school.myschoolapp.com/podium/feed/iCal.aspx?z=abc",
                "combine_blocks": "true",
            }
        )
        with patch("handler.fetch_ics", return_value=synthetic_ics_text):
            response = handler(event, None)
        assert response["statusCode"] == 200


class TestHandlerValidation:
    """Request validation — bad inputs return 400."""

    def test_missing_url(self) -> None:
        event = _make_event({})
        response = handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "URL" in body["error"]

    def test_empty_url(self) -> None:
        event = _make_event({"ics_url": "   "})
        response = handler(event, None)
        assert response["statusCode"] == 400

    def test_non_https_url(self) -> None:
        event = _make_event({"ics_url": "http://school.myschoolapp.com/feed/iCal.aspx?z=x"})
        response = handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "HTTPS" in body["error"]

    def test_non_ics_url(self) -> None:
        event = _make_event({"ics_url": "https://google.com/search?q=hello"})
        response = handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Blackbaud" in body["error"] or "calendar feed" in body["error"]

    def test_invalid_json_body(self) -> None:
        event = {"body": "not json at all", "isBase64Encoded": False}
        response = handler(event, None)
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "JSON" in body["error"]

    def test_invalid_grade_ignored(self, synthetic_ics_text: str) -> None:
        """Non-numeric or out-of-range grade is silently ignored, not an error."""
        event = _make_event(
            {
                "ics_url": "https://school.myschoolapp.com/podium/feed/iCal.aspx?z=abc",
                "grade": "banana",
            }
        )
        with patch("handler.fetch_ics", return_value=synthetic_ics_text):
            response = handler(event, None)
        assert response["statusCode"] == 200


class TestHandlerFetchErrors:
    """Fetch failures return 502."""

    def test_timeout_returns_502(self) -> None:
        event = _make_event(
            {
                "ics_url": "https://school.myschoolapp.com/podium/feed/iCal.aspx?z=abc",
            }
        )

        with patch("handler.fetch_ics", side_effect=FetchError("Timeout", status_code=502)):
            response = handler(event, None)

        assert response["statusCode"] == 502
        body = json.loads(response["body"])
        assert "Timeout" in body["error"]


class TestHandlerParseErrors:
    """Unparseable ICS content returns 422."""

    def test_empty_calendar_returns_422(self) -> None:
        empty_ics = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Test//EN\nEND:VCALENDAR"
        event = _make_event(
            {
                "ics_url": "https://school.myschoolapp.com/podium/feed/iCal.aspx?z=abc",
            }
        )

        with patch("handler.fetch_ics", return_value=empty_ics):
            response = handler(event, None)

        assert response["statusCode"] == 422
        body = json.loads(response["body"])
        assert "missing" in body["error"].lower()
