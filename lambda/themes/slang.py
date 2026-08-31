"""Gen-Alpha slang theme — the planner in playful, current internet slang.

Slang meanings verified against reputable sources (Merriam-Webster, wikiHow,
Pearson's teacher guide, People, Reader's Digest):
  - "lock in"      = focus all your attention on one task
  - "W"            = a win
  - "glow-up"      = a big positive transformation
  - "no cap"       = no lie / for real
  - "rizz"         = charisma / charm (Oxford Word of the Year 2023)
  - "bussin"       = really good

Deliberately AVOIDS ambiguous or potentially-exclusionary terms (e.g. "6-7",
"Ohio", "sus" as an insult) that guides for parents/teachers flag as sometimes
hiding insult or exclusion. Kept light, kind, and school-appropriate.

All tips are original executive-functioning advice; no attributed quotes.
No emoji/unicode glyphs (they don't render in reportlab base fonts, per spec).
"""

from __future__ import annotations

from themes.base import Theme

SLANG = Theme(
    key="slang",
    display_name="Gen-Alpha Slang",
    description="Same planner, playful internet slang. Lock in and get the W.",
    title_template="{name}\u2019s Weekly Lock-In",
    title_template_no_name="Weekly Lock-In",
    tests_header="TESTS & QUIZZES (time to lock in)",
    projects_header="BIG PROJECTS (the long game)",
    goals_header="MY GOALS THIS WEEK (let's get the W)",
    howto_header="HOW TO USE THIS (no cap)",
    priorities_header="TODAY'S TOP 3  (the real priorities, no cap)",
    homework_header="CLASS-BY-CLASS HOMEWORK LOG",
    checklist_header="END-OF-DAY CHECK (secure the W)",
    ef_tips={
        "Monday": [
            "Tip: Before you start, do a 2-minute brain dump of everything due this "
            "week. Know the mission, then lock in.",
            "Tip: Scan the whole week first \u2014 you can't lock in on what you can't see.",
        ],
        "Tuesday": [
            "Tip: Do your hardest subject first while your brain is fresh. That's how "
            "you get the W.",
            "Tip: Start with the toughest thing. Getting it done early is a whole "
            "glow-up for your afternoon.",
        ],
        "Wednesday": [
            "Tip: A big project is less scary in pieces. Break it into 3\u20134 small "
            "steps with their own due-dates \u2014 no cap.",
            "Tip: Don't cram the whole project at once. Small daily steps hit different.",
        ],
        "Thursday": [
            "Tip: Use Study Hall to work ahead on tomorrow's homework. Future-you "
            "will say thanks, no cap.",
            "Tip: Bank some work now in Study Hall so tomorrow is easy mode.",
        ],
        "Friday": [
            "Tip: Before you pack up, check next week's tests and projects so nothing "
            "sneaks up on you.",
            "Tip: Quick check of next week's box now = zero surprises later. That's the W.",
        ],
    },
    easter_eggs=[
        "Real talk: Writing homework down the second it's assigned is low-key elite.",
        "Real talk: Showing up and doing the work every day is the actual glow-up.",
        "Real talk: Small habits > big cram sessions. That consistency is bussin.",
    ],
)
