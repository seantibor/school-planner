"""Theme system for the planner PDF.

A Theme customizes the *text* of the planner — titles, section headers,
EF tips, checklist wording, and easter-egg one-liners — while keeping the
exact same layout, structure, and executive-functioning value.

Design notes:
- Every field has a sensible classic default (see CLASSIC below), so a theme
  only needs to override what it wants to change. This keeps themes DRY and
  short — a theme file is mostly just the fun bits.
- EF tips and easter eggs are POOLS (lists), sampled at build time so that
  reprints of the same page differ — the "element of surprise".
- EF tips are original executive-functioning advice written in a themed
  voice. They are NOT attributed quotes. Any attributed quote in a theme
  must be verified against a reputable source before inclusion.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Theme:
    """A planner theme. All fields default to the classic wording.

    Themes override only the fields they want to change.
    """

    # Registry key + human-facing metadata (shown in the frontend dropdown)
    key: str = "classic"
    display_name: str = "Classic"
    description: str = "The original clean planner. No frills, just focus."

    # Title flourish. "{name}" is replaced with the student's first name (or
    # dropped gracefully if no name is given).
    title_template: str = "{name}\u2019s Weekly Planner"
    title_template_no_name: str = "Weekly Planner"

    # Section headers (uppercased at render time by the caller as needed).
    tests_header: str = "TESTS & QUIZZES THIS WEEK"
    projects_header: str = "PROJECTS & LONG-TERM ASSIGNMENTS"
    goals_header: str = "MY GOALS FOR THIS WEEK"
    howto_header: str = "HOW TO USE THIS PLANNER"
    priorities_header: str = (
        "TODAY'S TOP 3 PRIORITIES  (pick the most important things to get done)"
    )
    homework_header: str = "CLASS-BY-CLASS HOMEWORK LOG"
    checklist_header: str = "END-OF-DAY CHECKLIST"

    # EF tip pools, keyed by weekday. Each list is sampled at random per page.
    # The classic theme keeps the single approved tip per day (as one-item pools).
    ef_tips: dict[str, list[str]] = field(
        default_factory=lambda: {
            "Monday": [
                "EF tip: Do a 2-minute \u201cbrain dump\u201d of everything due this week "
                "before you start homework \u2014 it frees up mental energy for the actual work."
            ],
            "Tuesday": [
                "EF tip: Start with your hardest or least-favorite subject first, "
                "while your brain is freshest."
            ],
            "Wednesday": [
                "EF tip: Big projects feel less overwhelming when you break them into "
                "3\u20134 small steps with their own mini due-dates."
            ],
            "Thursday": [
                "EF tip: Use Study Hall to work ahead on tomorrow\u2019s homework "
                "\u2014 future-you will be grateful."
            ],
            "Friday": [
                "EF tip: Before you close your backpack, check next week\u2019s "
                "tests/projects box on the overview page so nothing sneaks up on you."
            ],
        }
    )

    # Optional easter-egg one-liners dropped in a small footer on daily pages.
    # Empty for classic (no easter eggs). Sampled at random when non-empty.
    easter_eggs: list[str] = field(default_factory=list)

    def tip_for(self, weekday: str, rng: random.Random) -> str:
        """Pick a tip for the given weekday, falling back to Monday's pool."""
        pool = self.ef_tips.get(weekday) or self.ef_tips.get("Monday", [""])
        return rng.choice(pool)

    def easter_egg(self, rng: random.Random) -> str | None:
        """Pick an easter egg, or None if this theme has none."""
        if not self.easter_eggs:
            return None
        return rng.choice(self.easter_eggs)

    def title(self, student_name: str) -> str:
        """Render the planner title for the given (possibly empty) name."""
        if student_name:
            return self.title_template.format(name=student_name)
        return self.title_template_no_name


# The classic theme is just the defaults.
CLASSIC = Theme()
