"""Video games theme — the planner as a quest log / RPG progression.

All tips are original executive-functioning advice framed in gaming language.
No emoji/unicode glyphs (they don't render in reportlab base fonts, per spec).
"""

from __future__ import annotations

from themes.base import Theme

VIDEO_GAMES = Theme(
    key="video_games",
    display_name="Video Games",
    description="Your week as a quest log — main quests, side quests, and XP.",
    title_template="{name}\u2019s Quest Log",
    title_template_no_name="Weekly Quest Log",
    tests_header="BOSS BATTLES: TESTS & QUIZZES",
    projects_header="MAIN QUESTS: PROJECTS & LONG-TERM ASSIGNMENTS",
    goals_header="MY QUEST OBJECTIVES THIS WEEK",
    howto_header="HOW TO PLAY",
    priorities_header="TODAY'S MAIN QUESTS  (your 3 top objectives)",
    homework_header="CLASS-BY-CLASS QUEST LOG",
    checklist_header="END-OF-LEVEL SAVE POINT",
    ef_tips={
        "Monday": [
            "Player tip: Open your map before the run \u2014 do a 2-minute brain dump of "
            "everything due this week so you know every objective.",
            "Player tip: Check your full quest list before diving in. You can't beat "
            "the level you can't see.",
        ],
        "Tuesday": [
            "Player tip: Fight the hardest boss (your toughest subject) while your HP "
            "is full \u2014 first thing, before you're worn down.",
            "Player tip: Take on the biggest challenge first. Easy quests are great "
            "cooldowns for later.",
        ],
        "Wednesday": [
            "Player tip: A big project is a main quest with multiple stages. Break it "
            "into 3\u20134 checkpoints, each with its own due-date.",
            "Player tip: Don't rush the final boss. Split a big assignment into "
            "smaller quests you can clear one at a time.",
        ],
        "Thursday": [
            "Player tip: Use Study Hall to grind ahead on tomorrow's work \u2014 "
            "banked XP makes the next level easy.",
            "Player tip: Smart players farm early. Use Study Hall to get ahead so "
            "future-you cruises.",
        ],
        "Friday": [
            "Player tip: Before you log off, check next week's boss battles "
            "(tests & projects) so nothing ambushes you.",
            "Player tip: Save your progress \u2014 scan next week's tests/projects box "
            "before you close your backpack.",
        ],
    },
    easter_eggs=[
        "Achievement unlocked: Showed up and did the work. +100 XP.",
        "Pro gamer move: Save often. Write homework down the second it's assigned.",
        "Loading tip: Every expert player started on tutorial level. Keep going.",
    ],
)
