import json

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

with open("weekA.json") as f:
    weekA = json.load(f)
with open("weekB.json") as f:
    weekB = json.load(f)

NAVY = colors.HexColor("#1a3c6e")
LIGHT_BLUE = colors.HexColor("#eef2f8")
GRAY = colors.HexColor("#666666")
LIGHT_GRAY = colors.HexColor("#cccccc")
ACCENT = colors.HexColor("#e8871e")

# Subject color coding -- consistent across every page so Kaden builds visual
# pattern-recognition ("blue is always math") which reduces cognitive load.
SUBJECT_COLORS = {
    "Ancient Civilizations": colors.HexColor("#fdebd3"),
    "Pre-Algebra Honors": colors.HexColor("#dbeafe"),
    "English": colors.HexColor("#e6f4ea"),
    "Intro to Leadership": colors.HexColor("#f3e8fd"),
    "Life Science": colors.HexColor("#d9f2f0"),
    "Spanish A": colors.HexColor("#fdeaea"),
    "Rock Band": colors.HexColor("#fff6d1"),
    "Exploratory Engineering": colors.HexColor("#e0e7ff"),
    "PCNN": colors.HexColor("#f0f0f0"),
    "Physical Education": colors.HexColor("#e6f7d9"),
    "Study Hall": colors.HexColor("#f5f5f5"),
}

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "title",
    parent=styles["Title"],
    fontSize=22,
    alignment=TA_CENTER,
    textColor=NAVY,
    spaceAfter=2,
)
subtitle_style = ParagraphStyle(
    "subtitle",
    parent=styles["Normal"],
    fontSize=10.5,
    alignment=TA_CENTER,
    textColor=GRAY,
    spaceAfter=6,
)
day_title_style = ParagraphStyle(
    "daytitle",
    parent=styles["Title"],
    fontSize=20,
    alignment=TA_LEFT,
    textColor=NAVY,
    spaceAfter=0,
)
day_sub_style = ParagraphStyle(
    "daysub", parent=styles["Normal"], fontSize=9.5, alignment=TA_LEFT, textColor=GRAY
)
section_head = ParagraphStyle(
    "sechead",
    parent=styles["Heading2"],
    fontSize=11.5,
    textColor=colors.white,
    spaceAfter=0,
    spaceBefore=0,
)
label_style = ParagraphStyle(
    "label", parent=styles["Normal"], fontSize=8.5, textColor=GRAY, fontName="Helvetica"
)
table_header_style = ParagraphStyle(
    "tblhead",
    parent=styles["Normal"],
    fontSize=8.5,
    textColor=colors.white,
    fontName="Helvetica-Bold",
)
class_style = ParagraphStyle(
    "class",
    parent=styles["Normal"],
    fontSize=9.5,
    fontName="Helvetica-Bold",
    leading=11,
)
period_style = ParagraphStyle(
    "period", parent=styles["Normal"], fontSize=8, textColor=GRAY, alignment=TA_CENTER
)
time_style = ParagraphStyle(
    "time", parent=styles["Normal"], fontSize=7.5, textColor=GRAY
)
tip_style = ParagraphStyle(
    "tip",
    parent=styles["Normal"],
    fontSize=8.5,
    textColor=NAVY,
    fontName="Helvetica-Oblique",
    leading=11,
)
check_text_style = ParagraphStyle(
    "checktext", parent=styles["Normal"], fontSize=9, leading=12
)

# ---------------------------------------------------------------- helpers


def section_bar(text, width=7.5 * inch, height=0.24 * inch, color=NAVY):
    t = Table([[Paragraph(text, section_head)]], colWidths=[width], rowHeights=[height])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def checkbox_cell():
    t = Table([[""]], colWidths=[0.16 * inch], rowHeights=[0.16 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1.1, colors.HexColor("#888888")),
            ]
        )
    )
    return t


def checklist(items):
    rows = []
    for item in items:
        rows.append([checkbox_cell(), Paragraph(item, check_text_style)])
    t = Table(rows, colWidths=[0.28 * inch, 7.2 * inch])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
            ]
        )
    )
    return t


def blank_rule_table(nrows, headers, col_widths, row_h=0.42 * inch):
    data = [[Paragraph(h, label_style) for h in headers]]
    for _ in range(nrows):
        data.append(["" for _ in headers])
    t = Table(data, colWidths=col_widths, rowHeights=[0.22 * inch] + [row_h] * nrows)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.6, LIGHT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]
    t.setStyle(TableStyle(style))
    return t


EF_TIPS = {
    "Monday": "EF tip: Do a 2-minute \u201cbrain dump\u201d of everything due this week before you start homework \u2014 it frees up mental energy for the actual work.",
    "Tuesday": "EF tip: Start with your hardest or least-favorite subject first, while your brain is freshest.",
    "Wednesday": "EF tip: Big projects feel less overwhelming when you break them into 3\u20134 small steps with their own mini due-dates.",
    "Thursday": "EF tip: Use Study Hall to work ahead on tomorrow's homework \u2014 future-you will be grateful.",
    "Friday": "EF tip: Before you close your backpack, check next week's tests/projects box on the overview page so nothing sneaks up on you.",
}

# ---------------------------------------------------------------- overview page


def overview_page():
    story = []
    story.append(Paragraph("Kaden's Weekly Planner", title_style))
    story.append(
        Paragraph(
            "Pine Crest 6th Grade &nbsp;\u2014&nbsp; Overview &amp; Planning Page",
            subtitle_style,
        )
    )

    # Week of / A-B chooser
    def ab_choice_cell(label):
        inner = Table(
            [
                [
                    Paragraph(f"<b>{label}</b>", check_text_style),
                    checkbox_cell(),
                    Paragraph("A-day", check_text_style),
                    checkbox_cell(),
                    Paragraph("B-day", check_text_style),
                ]
            ],
            colWidths=[1.15 * inch, 0.2 * inch, 0.5 * inch, 0.2 * inch, 0.5 * inch],
        )
        inner.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        return inner

    header_tbl = Table(
        [
            [
                Paragraph("<b>Week of:</b> _______________________", check_text_style),
                ab_choice_cell("Wed is:"),
                ab_choice_cell("Thu is:"),
            ]
        ],
        colWidths=[2.7 * inch, 2.6 * inch, 2.6 * inch],
    )
    header_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(header_tbl)
    story.append(
        Paragraph(
            "Check the school calendar/Blackbaud for the A/B rotation, circle it here, then use the matching Wed/Thu page this week.",
            label_style,
        )
    )
    story.append(Spacer(1, 10))

    story.append(section_bar("TESTS &amp; QUIZZES THIS WEEK"))
    story.append(
        blank_rule_table(
            4,
            [
                "Subject",
                "Topic",
                "Test Date",
                "Study Days Planned (write which nights you'll review)",
            ],
            [1.4 * inch, 2.0 * inch, 1.1 * inch, 3.0 * inch],
        )
    )
    story.append(Spacer(1, 10))

    story.append(section_bar("PROJECTS &amp; LONG-TERM ASSIGNMENTS"))
    story.append(
        blank_rule_table(
            4,
            [
                "Subject",
                "Assignment",
                "Due Date",
                "Steps / Checkpoints (break it into 3-4 mini-deadlines)",
            ],
            [1.4 * inch, 2.0 * inch, 1.1 * inch, 3.0 * inch],
        )
    )
    story.append(Spacer(1, 10))

    story.append(section_bar("MY GOALS FOR THIS WEEK"))
    goals_tbl = Table(
        [[""], [""], [""]], colWidths=[7.5 * inch], rowHeights=[0.32 * inch] * 3
    )
    goals_tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, LIGHT_GRAY),
                ("BOX", (0, 0), (-1, -1), 0.6, LIGHT_GRAY),
            ]
        )
    )
    story.append(goals_tbl)
    story.append(Spacer(1, 10))

    story.append(section_bar("HOW TO USE THIS PLANNER", color=ACCENT))
    howto = (
        "1) Every class, write down the homework the second it's assigned \u2014 don't trust your memory. "
        "2) If nothing's assigned, write \u201cnone\u201d so you know you checked. "
        "3) Tests and projects go on THIS page as soon as you hear about them, even if they're weeks away. "
        "4) Do the End-of-Day Checklist on each daily page before you leave school or close your backpack at home."
    )
    howto_tbl = Table([[Paragraph(howto, check_text_style)]], colWidths=[7.5 * inch])
    howto_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.8, ACCENT),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff8ef")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(howto_tbl)
    return story


# ---------------------------------------------------------------- daily page


def daily_page(day_name, label_suffix, periods):
    """periods: list of dicts with name/start/end, Advisory & Lunch already excluded"""
    story = []
    head = Table(
        [
            [
                Paragraph(f"{day_name.upper()}{label_suffix}", day_title_style),
                Paragraph("Date: _______________", day_sub_style),
            ]
        ],
        colWidths=[5.5 * inch, 2.0 * inch],
    )
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    story.append(head)
    story.append(Spacer(1, 6))

    # Today's top 3 priorities
    story.append(
        section_bar(
            "TODAY'S TOP 3 PRIORITIES  (pick the most important things to get done)"
        )
    )
    pri_rows = []
    for i in range(1, 4):
        pri_rows.append(
            [
                checkbox_cell(),
                Paragraph(
                    f"{i}.  ___________________________________________________",
                    check_text_style,
                ),
            ]
        )
    pri_tbl = Table(pri_rows, colWidths=[0.3 * inch, 7.2 * inch])
    pri_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(pri_tbl)
    story.append(Spacer(1, 8))

    # Class-by-class homework log
    story.append(section_bar("CLASS-BY-CLASS HOMEWORK LOG"))
    header = [
        Paragraph(h, table_header_style)
        for h in [
            "Class",
            "Homework / Assignment",
            "Due Date",
            "Materials Needed",
            "\u2713",
        ]
    ]
    data = [header]
    row_colors = []
    for p in periods:
        name_p = Paragraph(
            f"<b>{p['name']}</b><br/><font size=7 color='#777777'>{p['start']}\u2013{p['end']}</font>",
            class_style,
        )
        data.append([name_p, "", "", "", ""])
        row_colors.append(SUBJECT_COLORS.get(p["name"], colors.white))

    col_widths = [1.5 * inch, 3.0 * inch, 0.85 * inch, 1.55 * inch, 0.4 * inch]
    row_heights = [0.24 * inch] + [0.5 * inch] * len(periods)
    t = Table(data, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.6, LIGHT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (4, 1), (4, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]
    for i, c in enumerate(row_colors, start=1):
        style.append(("BACKGROUND", (0, i), (0, i), c))
    t.setStyle(TableStyle(style))
    story.append(t)
    story.append(Spacer(1, 8))

    # EF tip
    tip_key = day_name if day_name in EF_TIPS else "Monday"
    tip_tbl = Table(
        [[Paragraph("" + EF_TIPS[tip_key], tip_style)]], colWidths=[7.5 * inch]
    )
    tip_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(tip_tbl)
    story.append(Spacer(1, 8))

    # End of day checklist
    story.append(section_bar("END-OF-DAY CHECKLIST", color=ACCENT))
    story.append(
        checklist(
            [
                "I wrote down homework for every class (or wrote \u201cnone\u201d).",
                "I checked today's box against what's actually in my backpack.",
                "I packed the books/materials I need for tomorrow.",
                "I looked at the Tests &amp; Projects box on the overview page.",
                "Parent check: ______________________ (initial)",
            ]
        )
    )
    return story


# ---------------------------------------------------------------- build doc


def periods_excl(week, day):
    return [p for p in week[day] if p["name"] not in ("Advisory", "Lunch")]


doc = SimpleDocTemplate(
    "kaden_ef_planner.pdf",
    pagesize=letter,
    topMargin=0.45 * inch,
    bottomMargin=0.4 * inch,
    leftMargin=0.5 * inch,
    rightMargin=0.5 * inch,
)

story = []
story += overview_page()
story.append(PageBreak())

story += daily_page("Monday", "", periods_excl(weekA, "Monday"))
story.append(PageBreak())
story += daily_page("Tuesday", "", periods_excl(weekA, "Tuesday"))
story.append(PageBreak())
story += daily_page("Wednesday", " \u2014 A-day", periods_excl(weekA, "Wednesday"))
story.append(PageBreak())
story += daily_page("Wednesday", " \u2014 B-day", periods_excl(weekB, "Wednesday"))
story.append(PageBreak())
story += daily_page("Thursday", " \u2014 A-day", periods_excl(weekA, "Thursday"))
story.append(PageBreak())
story += daily_page("Thursday", " \u2014 B-day", periods_excl(weekB, "Thursday"))
story.append(PageBreak())
story += daily_page("Friday", "", periods_excl(weekA, "Friday"))

doc.build(story)
print("built", "pages: check with pdfinfo")
