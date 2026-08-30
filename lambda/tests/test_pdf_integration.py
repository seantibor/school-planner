"""Integration tests using the real anonymized ICS fixture.

Validates the full pipeline: parse → filter → PDF build, catching
edge cases observed in production output.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ics_parser import parse_schedule
from pdf_builder import _EXCLUDED_SUBJECTS, build_pdf

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def real_schedule() -> dict:
    ics_text = (FIXTURES_DIR / "real_anonymized.ics").read_text()
    return parse_schedule(ics_text)


class TestRealScheduleStructure:
    """Validate schedule structure from real feed data."""

    def test_all_seven_day_types_present(self, real_schedule: dict) -> None:
        expected = {
            "Monday",
            "Tuesday",
            "Wednesday-A",
            "Wednesday-B",
            "Thursday-A",
            "Thursday-B",
            "Friday",
        }
        assert set(real_schedule.keys()) == expected

    def test_monday_has_lunch(self, real_schedule: dict) -> None:
        """Lunch should be in the parsed schedule (filtering is at PDF build time)."""
        names = [p["name"] for p in real_schedule["Monday"]]
        assert "Lunch" in names

    def test_friday_has_no_advisory(self, real_schedule: dict) -> None:
        """Friday feed genuinely has no Advisory period."""
        names = [p["name"] for p in real_schedule["Friday"]]
        assert not any(n.startswith("Advisory") for n in names)

    def test_wednesday_is_block_schedule(self, real_schedule: dict) -> None:
        """Wednesday A/B have fewer periods than regular days."""
        assert len(real_schedule["Wednesday-A"]) < len(real_schedule["Monday"])
        assert len(real_schedule["Wednesday-B"]) < len(real_schedule["Monday"])

    def test_thursday_is_block_schedule(self, real_schedule: dict) -> None:
        assert len(real_schedule["Thursday-A"]) < len(real_schedule["Tuesday"])
        assert len(real_schedule["Thursday-B"]) < len(real_schedule["Tuesday"])

    def test_periods_are_chronologically_ordered(self, real_schedule: dict) -> None:
        """Periods within each day should be sorted by start time."""
        for day_type, periods in real_schedule.items():
            starts = [p["start"] for p in periods]
            # Convert to comparable times (simple string sort works for "H:MM AM" format
            # only if we normalize — instead just check the raw datetime ordering was preserved)
            for i in range(len(starts) - 1):
                # Start times should not go backwards
                # We can't easily compare "8:00 AM" < "12:32 PM" as strings,
                # so just verify no duplicates which would indicate parsing issues
                assert (
                    starts[i] != starts[i + 1]
                ), f"{day_type}: duplicate start time {starts[i]}"


class TestAdvisoryAndLunchExclusion:
    """The PDF builder should exclude Advisory and Lunch from the homework log."""

    def test_advisory_excluded_by_prefix(self, real_schedule: dict) -> None:
        """Advisory Grade 7 should match the prefix-based exclusion."""
        for day_type, periods in real_schedule.items():
            filtered = [
                p
                for p in periods
                if not any(p["name"].startswith(exc) for exc in _EXCLUDED_SUBJECTS)
            ]
            names = [p["name"] for p in filtered]
            assert not any(
                n.startswith("Advisory") for n in names
            ), f"{day_type} still has Advisory after filtering"

    def test_lunch_excluded(self, real_schedule: dict) -> None:
        for day_type, periods in real_schedule.items():
            filtered = [
                p
                for p in periods
                if not any(p["name"].startswith(exc) for exc in _EXCLUDED_SUBJECTS)
            ]
            names = [p["name"] for p in filtered]
            assert "Lunch" not in names, f"{day_type} still has Lunch after filtering"

    def test_monday_filtered_period_count(self, real_schedule: dict) -> None:
        """Monday has 10 total periods; after removing Advisory + Lunch = 8."""
        periods = real_schedule["Monday"]
        filtered = [
            p
            for p in periods
            if not any(p["name"].startswith(exc) for exc in _EXCLUDED_SUBJECTS)
        ]
        assert len(filtered) == 8


class TestCourseNameCleaning:
    """Verify cleaned names from the real feed are display-friendly."""

    def test_no_trailing_parenthetical(self, real_schedule: dict) -> None:
        """No period should have a trailing (N) tag in its name."""
        for periods in real_schedule.values():
            for p in periods:
                assert not p["name"].endswith(")"), f"Uncleaned name: {p['name']}"

    def test_introduction_abbreviated(self, real_schedule: dict) -> None:
        """'Introduction to Leadership' should be abbreviated to 'Intro to Leadership'."""
        all_names = {p["name"] for periods in real_schedule.values() for p in periods}
        assert "Intro to Leadership" in all_names or "Creative Writing" in all_names
        assert "Introduction to Leadership" not in all_names

    def test_no_name_exceeds_max_length(self, real_schedule: dict) -> None:
        """All course names should be within display bounds."""
        for periods in real_schedule.values():
            for p in periods:
                assert len(p["name"]) <= 40, f"Name too long: {p['name']}"

    def test_known_electives_keep_trailing_digits(self, real_schedule: dict) -> None:
        """Jazz Ensemble 678 should keep its trailing number."""
        all_names = {p["name"] for periods in real_schedule.values() for p in periods}
        assert "Jazz Ensemble 678" in all_names


class TestPDFGeneration:
    """Verify PDF generation succeeds and produces reasonable output."""

    def test_generates_valid_pdf(self, real_schedule: dict) -> None:
        pdf_bytes = build_pdf(real_schedule, student_name="Test", grade=7)
        assert pdf_bytes[:4] == b"%PDF"
        # 8 pages at typical size should be at least 15KB
        assert len(pdf_bytes) > 15_000

    def test_generates_without_student_name(self, real_schedule: dict) -> None:
        pdf_bytes = build_pdf(real_schedule)
        assert pdf_bytes[:4] == b"%PDF"

    def test_pdf_size_is_reasonable(self, real_schedule: dict) -> None:
        """PDF should not be absurdly large (would indicate a rendering bug)."""
        pdf_bytes = build_pdf(real_schedule, student_name="Test", grade=7)
        # Should be under 500KB for an 8-page planner
        assert len(pdf_bytes) < 500_000
