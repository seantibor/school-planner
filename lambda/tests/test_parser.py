"""Tests for ics_parser — validates spec §3 findings against synthetic fixture."""

from __future__ import annotations

import pytest
from ics_parser import DAY_TYPE_ORDER, clean_course_name, parse_schedule


class TestCleanCourseName:
    """Spec §3.4: regex-based name cleaner, no hardcoded lookup table."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Ancient Civilizations - 1 (1)", "Ancient Civilizations"),
            ("Pre-Algebra Honors - 2 Smith (2)", "Pre-Algebra Honors"),
            ("English - 3 (3)", "English"),
            ("Intro to Leadership - 4 (4)", "Intro to Leadership"),
            ("Introduction to Leadership - 4 (4)", "Intro to Leadership"),
            ("Life Science - 5 (5)", "Life Science"),
            ("Spanish A - 6 (6)", "Spanish A"),
            ("Study Hall-6 - P5-T1 (5)", "Study Hall"),
            ("Physical Education - PE 6-T (6)", "Physical Education"),
            ("Exploratory Engineering-6 - 6 (W) (6)", "Exploratory Engineering"),
            ("Advanced Mathematics - 8 Goldberg (8)", "Advanced Mathematics"),
            ("Applied AI and Computing-6 - 4 (4)", "Applied AI and Computing"),
            ("Band - MWF (5)", "Band"),
            # Known multi-grade electives — trailing digits are part of the name
            ("Rock Band 678 - MF 7 (7)", "Rock Band 678"),
            ("PCNN - 5 (5)", "PCNN"),
            # Advisory keeps "Grade 6" (spec says this is acceptable)
            ("Advisory Grade 6 - Baena (Advisory)", "Advisory Grade 6"),
        ],
    )
    def test_clean_course_name(self, raw: str, expected: str) -> None:
        assert clean_course_name(raw) == expected


class TestParseSchedule:
    """Spec §4: full schedule parsing from ICS feed."""

    def test_all_day_types_found(self, synthetic_ics: str) -> None:
        """Confirm all 7 day-types are discovered from the fixture."""
        schedule = parse_schedule(synthetic_ics)
        for day_type in DAY_TYPE_ORDER:
            assert day_type in schedule, f"Missing day-type: {day_type}"

    def test_monday_has_correct_periods(self, synthetic_ics: str) -> None:
        """Monday should have Advisory + 10 periods."""
        schedule = parse_schedule(synthetic_ics)
        monday = schedule["Monday"]
        # Fixture has Advisory + 10 class periods on Monday
        assert len(monday) == 11
        # First entry is Advisory
        assert monday[0]["name"] == "Advisory Grade 6"
        # Second is Ancient Civilizations in period 1
        assert monday[1]["name"] == "Ancient Civilizations"
        assert monday[1]["period"] == "1"

    def test_wednesday_a_is_block_schedule(self, synthetic_ics: str) -> None:
        """Wednesday A should have fewer periods (block schedule)."""
        schedule = parse_schedule(synthetic_ics)
        wed_a = schedule["Wednesday-A"]
        # Block schedule: Advisory + 4 blocks
        assert len(wed_a) == 5
        names = [p["name"] for p in wed_a]
        assert "Ancient Civilizations" in names
        assert "Applied AI and Computing" in names

    def test_thursday_b_is_block_schedule(self, synthetic_ics: str) -> None:
        """Thursday B should have block periods."""
        schedule = parse_schedule(synthetic_ics)
        thu_b = schedule["Thursday-B"]
        assert len(thu_b) >= 4

    def test_subject_period_mapping_varies(self, synthetic_ics: str) -> None:
        """Spec §3.2: same subject can appear in different period slots on different days."""
        schedule = parse_schedule(synthetic_ics)
        # Life Science is period 5 on Monday, period 4 on Tuesday
        mon_life_sci = next(
            (p for p in schedule["Monday"] if p["name"] == "Life Science"), None
        )
        tue_life_sci = next(
            (p for p in schedule["Tuesday"] if p["name"] == "Life Science"), None
        )
        assert mon_life_sci is not None
        assert tue_life_sci is not None
        assert mon_life_sci["period"] == "5"
        assert tue_life_sci["period"] == "4"

    def test_bell_schedule_times_consistent(self, synthetic_ics: str) -> None:
        """Spec §3.1: period 1 starts at 8:14 AM on regular days."""
        schedule = parse_schedule(synthetic_ics)
        # Monday and Tuesday period 1 should both start at 8:14 AM
        mon_p1 = schedule["Monday"][1]  # index 0 is Advisory
        tue_p1 = schedule["Tuesday"][1]
        assert mon_p1["start"] == "8:14 AM"
        assert tue_p1["start"] == "8:14 AM"


class TestParseScheduleValidation:
    """Spec §4 step 6: validation catches broken/incomplete feeds."""

    def test_empty_feed_raises(self) -> None:
        empty_ics = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Test//EN\nEND:VCALENDAR"
        with pytest.raises(ValueError, match="missing data"):
            parse_schedule(empty_ics)

    def test_missing_wednesday_raises(self) -> None:
        """A feed with only Mon/Tue/Fri but no Wed/Thu markers should fail."""
        partial_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260901
DTEND;VALUE=DATE:20260902
SUMMARY:Monday (BRMS)
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260902
DTEND;VALUE=DATE:20260903
SUMMARY:Tuesday (BRMS)
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260905
DTEND;VALUE=DATE:20260906
SUMMARY:Friday (BRMS)
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=America/New_York:20260901T081400
DTEND;TZID=America/New_York:20260901T085400
SUMMARY:English - 3 (3)
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=America/New_York:20260902T081400
DTEND;TZID=America/New_York:20260902T085400
SUMMARY:English - 3 (3)
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=America/New_York:20260905T081400
DTEND;TZID=America/New_York:20260905T085400
SUMMARY:English - 3 (3)
END:VEVENT
END:VCALENDAR"""
        with pytest.raises(ValueError, match="Wednesday"):
            parse_schedule(partial_ics)
