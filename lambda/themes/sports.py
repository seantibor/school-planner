"""Sports theme — the planner as a game plan / training schedule.

All tips are original executive-functioning advice framed in sports language.
No attributed quotes to real athletes (avoids fabrication risk).
"""

from __future__ import annotations

from themes.base import Theme

SPORTS = Theme(
    key="sports",
    display_name="Sports",
    description="Your week as a game plan — practices, plays, and game-day prep.",
    title_template="{name}\u2019s Game Plan",
    title_template_no_name="Weekly Game Plan",
    tests_header="SCOUTING REPORT: TESTS & QUIZZES",
    projects_header="SEASON GOALS: PROJECTS & LONG-TERM ASSIGNMENTS",
    goals_header="MY GAME-DAY GOALS THIS WEEK",
    howto_header="HOW TO RUN THIS PLAYBOOK",
    priorities_header="TODAY'S STARTING LINEUP  (your 3 most important plays)",
    homework_header="CLASS-BY-CLASS PLAY LOG",
    checklist_header="POST-GAME CHECKLIST",
    ef_tips={
        "Monday": [
            "Coach's tip: Do a 2-minute warm-up before homework \u2014 list everything "
            "due this week so you know the whole field before the first play.",
            "Coach's tip: Every champion reviews the game plan first. Scan your week "
            "before you start, then attack it one play at a time.",
        ],
        "Tuesday": [
            "Coach's tip: Run your hardest drill first, while your energy is highest "
            "\u2014 save the easy reps for when you're tired.",
            "Coach's tip: Toughest opponent (your hardest subject) goes first. "
            "Beat it while you're fresh.",
        ],
        "Wednesday": [
            "Coach's tip: A big project is a whole season, not one game. Break it into "
            "3\u20134 practices with their own mini due-dates.",
            "Coach's tip: You don't win the championship in a day. Split big "
            "assignments into small, scheduled reps.",
        ],
        "Thursday": [
            "Coach's tip: Use Study Hall like extra practice time \u2014 get ahead on "
            "tomorrow's work so game day is easy.",
            "Coach's tip: The best players put in reps when no one's watching. "
            "Use Study Hall to work ahead.",
        ],
        "Friday": [
            "Coach's tip: Before the final whistle, check next week's scouting report "
            "(tests & projects) so nothing catches you off guard.",
            "Coach's tip: Great teams review film. Check next week's tests/projects "
            "box before you pack up.",
        ],
    },
    easter_eggs=[
        "MVP move: Consistency beats intensity. Small daily reps win seasons.",
        "MVP move: Effort is the one stat that's 100% in your control.",
        "MVP move: Every pro was once a rookie who kept showing up.",
    ],
)
