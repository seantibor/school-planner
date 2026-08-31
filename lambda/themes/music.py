"""Music theme — the planner as a setlist / studio session.

All tips are original executive-functioning advice framed in music language.
No attributed quotes to real musicians (avoids fabrication risk).
No emoji/unicode glyphs (they don't render in reportlab base fonts, per spec).
"""

from __future__ import annotations

from themes.base import Theme

MUSIC = Theme(
    key="music",
    display_name="Music",
    description="Your week as a setlist — rehearsals, tracks, and the big show.",
    title_template="{name}\u2019s Setlist",
    title_template_no_name="Weekly Setlist",
    tests_header="SOUND CHECK: TESTS & QUIZZES",
    projects_header="ALBUM TRACKS: PROJECTS & LONG-TERM ASSIGNMENTS",
    goals_header="MY HEADLINER GOALS THIS WEEK",
    howto_header="HOW TO READ THIS SETLIST",
    priorities_header="TODAY'S TOP 3 TRACKS  (your most important songs to play)",
    homework_header="CLASS-BY-CLASS SETLIST",
    checklist_header="END-OF-SHOW SOUND CHECK",
    ef_tips={
        "Monday": [
            "Studio tip: Warm up before the session \u2014 do a 2-minute brain dump of "
            "everything due this week so you know the whole setlist.",
            "Studio tip: Every great show starts with a run-through. Scan your week "
            "before you play the first note.",
        ],
        "Tuesday": [
            "Studio tip: Rehearse the hardest song first, while your focus is sharp "
            "\u2014 the easy tracks can come later.",
            "Studio tip: Nail the tricky solo (your hardest subject) first, while you're fresh.",
        ],
        "Wednesday": [
            "Studio tip: A big project is a whole album, not a single. Break it into "
            "3\u20134 tracks, each with its own deadline.",
            "Studio tip: You record an album one track at a time. Split big "
            "assignments into small, scheduled sessions.",
        ],
        "Thursday": [
            "Studio tip: Use Study Hall as extra rehearsal \u2014 get ahead on "
            "tomorrow's work so show day feels effortless.",
            "Studio tip: The tightest bands rehearse when no one's listening. Use "
            "Study Hall to work ahead.",
        ],
        "Friday": [
            "Studio tip: Before the encore, check next week's sound check "
            "(tests & projects) so nothing throws off your rhythm.",
            "Studio tip: Great performers review the setlist. Check next week's "
            "tests/projects box before you pack up.",
        ],
    },
    easter_eggs=[
        "Backstage note: Practice doesn't make perfect \u2014 it makes permanent. "
        "Practice the good habits.",
        "Backstage note: Even your favorite artist started with clumsy first takes.",
        "Backstage note: Small daily practice beats one giant cram session.",
    ],
)
