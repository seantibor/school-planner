"""ICS feed parsing for Blackbaud/Podium school calendars.

Implements the logic from spec §3.4 and §4:
- Separates all-day marker events (day-type labels) from timed period events
- Discovers per-student subject-to-period mapping from the feed itself
- Cleans raw Blackbaud course names via regex (no hardcoded lookup tables)
- Groups periods by day-type (Mon/Tue/Wed-A/Wed-B/Thu-A/Thu-B/Fri)
- Returns a structured schedule dict ready for PDF generation
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from icalendar import Calendar

# Pattern for extracting the trailing period tag, e.g. "(5)" or "(W)"
_TRAILING_TAG_RE = re.compile(r"\s*\(\w+\)\s*$")
# Pattern for trailing grade/cohort suffix like "-6" on "Study Hall-6"
_TRAILING_GRADE_SUFFIX_RE = re.compile(r"-\d+$")

# Input length limits — prevents layout breakage and bounds memory usage
_MAX_COURSE_NAME_LEN = 40
_MAX_SUMMARY_LEN = 200  # raw ICS summary field before cleaning

# Day-type detection from all-day marker event summaries.
# Matches patterns like "Monday (BRMS)", "Wednesday A (BRMS)", etc.
# The division code in parens is ignored (not hardcoded to "BRMS").
_DAY_TYPE_RE = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday)" r"(?:\s+(A|B))?" r"\s*\(.*\)\s*$",
    re.IGNORECASE,
)

# Canonical day-type keys in display order
DAY_TYPE_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday-A",
    "Wednesday-B",
    "Thursday-A",
    "Thursday-B",
    "Friday",
]

# Known multi-grade elective names where trailing digits are part of the name,
# not a grade suffix to strip (e.g. "Rock Band 678", "PCNN")
_KNOWN_ELECTIVE_NAMES = {"Rock Band", "PCNN", "Jazz Ensemble"}


def clean_course_name(raw: str) -> str:
    """Clean a raw Blackbaud/Podium summary string into a human-friendly course name.

    Examples:
        "Ancient Civilizations - 1 (1)" -> "Ancient Civilizations"
        "Study Hall-6 - P5-T1 (5)" -> "Study Hall"
        "Physical Education - PE 6-T (6)" -> "Physical Education"
        "Exploratory Engineering-6 - 6 (W) (6)" -> "Exploratory Engineering"
        "Advanced Mathematics - 8 Goldberg (8)" -> "Advanced Mathematics"
        "Applied AI and Computing-6 - 4 (4)" -> "Applied AI and Computing"
        "Rock Band 678 - MF 7 (7)" -> "Rock Band 678"
        "Advisory Grade 6 - Baena (Advisory)" -> "Advisory Grade 6"
    """
    # Strip trailing "(N)" or "(W)" tag
    s = _TRAILING_TAG_RE.sub("", raw[:_MAX_SUMMARY_LEN])
    # Keep only text before first " - " (section/teacher/day-code detail)
    s = s.split(" - ")[0]
    # Strip trailing "-N" grade/cohort suffix, unless it's a known elective
    # where the trailing digits are part of the actual name
    if not any(s.startswith(name) for name in _KNOWN_ELECTIVE_NAMES):
        s = _TRAILING_GRADE_SUFFIX_RE.sub("", s)
    s = s.strip()
    # Abbreviate common long prefixes that break table layout
    s = re.sub(r"^Introduction to ", "Intro to ", s)
    # Truncate to max display length
    if len(s) > _MAX_COURSE_NAME_LEN:
        s = s[: _MAX_COURSE_NAME_LEN - 1] + "\u2026"
    return s


def _extract_period_number(summary: str) -> str | None:
    """Extract the period number from the trailing (N) tag in a summary string.

    Returns the period identifier as a string, or None if not found.
    """
    match = re.search(r"\((\w+)\)\s*$", summary)
    if match:
        tag = match.group(1)
        # Only return numeric period numbers, not letter codes like "(W)"
        if tag.isdigit():
            return tag
    return None


def _classify_day_type(summary: str) -> str | None:
    """Classify an all-day marker event summary into a canonical day-type key.

    Returns e.g. "Monday", "Wednesday-A", "Thursday-B", or None if not a day marker.
    """
    match = _DAY_TYPE_RE.match(summary.strip())
    if not match:
        return None
    day = match.group(1).capitalize()
    rotation = match.group(2)
    if rotation:
        return f"{day}-{rotation.upper()}"
    return day


def _event_is_all_day(component: Any) -> bool:
    """Check if a VEVENT is an all-day event (DTSTART is a date, not datetime)."""
    dtstart = component.get("dtstart")
    if dtstart is None:
        return False
    dt = dtstart.dt
    return isinstance(dt, date) and not isinstance(dt, datetime)


def _format_time(dt: datetime) -> str:
    """Format a datetime into a display time string like '8:14 AM'."""
    return dt.strftime("%-I:%M %p")


def parse_schedule(ics_text: str) -> dict[str, list[dict[str, str]]]:
    """Parse an ICS calendar feed into a structured schedule.

    Args:
        ics_text: Raw ICS file content as a string.

    Returns:
        Dict mapping day-type keys (from DAY_TYPE_ORDER) to lists of period dicts.
        Each period dict has keys: "period", "name", "start", "end".
        Advisory and Lunch periods are included (filtering is done at PDF build time).

    Raises:
        ValueError: If the feed doesn't contain enough data to build a schedule.
    """
    cal = Calendar.from_ical(ics_text)

    # Step 1: Build date -> day-type map from all-day marker events
    date_to_day_type: dict[date, str] = {}

    # Step 2: Collect timed period events grouped by date
    events_by_date: dict[date, list[dict[str, str]]] = {}

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        summary = str(component.get("summary", ""))
        if not summary:
            continue

        if _event_is_all_day(component):
            # This is a day-type marker
            day_type = _classify_day_type(summary)
            if day_type:
                event_date = component.get("dtstart").dt
                if isinstance(event_date, datetime):
                    event_date = event_date.date()
                date_to_day_type[event_date] = day_type
        else:
            # This is a timed period event
            dtstart = component.get("dtstart")
            dtend = component.get("dtend")
            if dtstart is None or dtend is None:
                continue

            start_dt = dtstart.dt
            end_dt = dtend.dt
            if not isinstance(start_dt, datetime) or not isinstance(end_dt, datetime):
                continue

            event_date = start_dt.date()
            period_num = _extract_period_number(summary)
            name = clean_course_name(summary)

            period_info = {
                "period": period_num or "?",
                "name": name,
                "start": _format_time(start_dt),
                "end": _format_time(end_dt),
                "_start_dt": start_dt,  # kept for sorting, stripped before return
            }

            if event_date not in events_by_date:
                events_by_date[event_date] = []
            events_by_date[event_date].append(period_info)

    # Step 3: Group events by day-type, taking the first clean occurrence as canonical
    schedule: dict[str, list[dict[str, str]]] = {}

    for event_date, periods in sorted(events_by_date.items()):
        day_type = date_to_day_type.get(event_date)
        if day_type is None:
            continue
        # Use first occurrence of each day-type as the canonical template
        if day_type in schedule:
            continue

        # Sort periods by start time
        sorted_periods = sorted(periods, key=lambda p: p["_start_dt"])

        # Assign ordinal period numbers for any missing ones
        for i, p in enumerate(sorted_periods):
            if p["period"] == "?":
                p["period"] = str(i + 1)

        # Strip internal sorting key
        clean_periods = [
            {
                "period": p["period"],
                "name": p["name"],
                "start": p["start"],
                "end": p["end"],
            }
            for p in sorted_periods
        ]
        schedule[day_type] = clean_periods

    # Step 4: Validate
    _validate_schedule(schedule)

    return schedule


def _validate_schedule(schedule: dict[str, list[dict[str, str]]]) -> None:
    """Validate that the parsed schedule has enough data to generate a useful PDF.

    Raises:
        ValueError: With a descriptive message if validation fails.
    """
    required_days = ["Monday", "Tuesday", "Friday"]
    missing = [d for d in required_days if d not in schedule or not schedule[d]]
    if missing:
        raise ValueError(
            f"Schedule is missing data for: {', '.join(missing)}. "
            "Please verify the ICS URL is correct and contains upcoming events."
        )

    has_wednesday = any(k.startswith("Wednesday") for k in schedule)
    has_thursday = any(k.startswith("Thursday") for k in schedule)
    if not has_wednesday or not has_thursday:
        missing_rot = []
        if not has_wednesday:
            missing_rot.append("Wednesday")
        if not has_thursday:
            missing_rot.append("Thursday")
        raise ValueError(
            f"Schedule is missing rotation data for: {', '.join(missing_rot)}. "
            "The feed may not contain enough future dates to capture both A/B rotations."
        )
