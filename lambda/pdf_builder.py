"""PDF planner generation for middle school students.

Generalized from the approved build_ef_planner.py prototype. Takes a parsed
schedule dict (from ics_parser.parse_schedule) plus student name/grade and
produces an 8-page portrait-letter PDF as bytes.

Spec references: §5 (PDF Output Specification)
"""

from __future__ import annotations

import html
import io
import random
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from themes import Theme, get_theme
from themes.base import CLASSIC

# ---------------------------------------------------------------------------
# Design tokens (§5.2)
# ---------------------------------------------------------------------------

NAVY = colors.HexColor("#1a3c6e")
LIGHT_BLUE = colors.HexColor("#eef2f8")
GRAY = colors.HexColor("#666666")
LIGHT_GRAY = colors.HexColor("#cccccc")
ACCENT = colors.HexColor("#e8871e")

# Dynamic subject color palette — assigned in encounter order per student.
# 12 distinct pastels; falls back to white if exhausted.
_COLOR_PALETTE = [
    colors.HexColor("#fdebd3"),  # warm peach
    colors.HexColor("#dbeafe"),  # soft blue
    colors.HexColor("#e6f4ea"),  # mint green
    colors.HexColor("#f3e8fd"),  # lavender
    colors.HexColor("#d9f2f0"),  # teal
    colors.HexColor("#fdeaea"),  # blush pink
    colors.HexColor("#fff6d1"),  # pale yellow
    colors.HexColor("#e0e7ff"),  # periwinkle
    colors.HexColor("#f0f0f0"),  # light gray
    colors.HexColor("#e6f7d9"),  # lime
    colors.HexColor("#f5f5f5"),  # near-white
    colors.HexColor("#fce4ec"),  # rose
]

# EF tips now live in the theme system (themes/). Each theme provides a pool
# of tips per weekday, sampled at random per page for the "surprise" element.

# Subjects to exclude from the homework log (not real class periods)
_EXCLUDED_SUBJECTS = {"Advisory", "Lunch"}

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

_base_styles = getSampleStyleSheet()

_title_style = ParagraphStyle(
    "planner_title",
    parent=_base_styles["Title"],
    fontSize=22,
    alignment=TA_CENTER,
    textColor=NAVY,
    spaceAfter=2,
)
_subtitle_style = ParagraphStyle(
    "planner_subtitle",
    parent=_base_styles["Normal"],
    fontSize=10.5,
    alignment=TA_CENTER,
    textColor=GRAY,
    spaceAfter=6,
)
_day_title_style = ParagraphStyle(
    "planner_daytitle",
    parent=_base_styles["Title"],
    fontSize=20,
    alignment=TA_LEFT,
    textColor=NAVY,
    spaceAfter=0,
)
_day_sub_style = ParagraphStyle(
    "planner_daysub",
    parent=_base_styles["Normal"],
    fontSize=9.5,
    alignment=TA_LEFT,
    textColor=GRAY,
)
_section_head_style = ParagraphStyle(
    "planner_sechead",
    parent=_base_styles["Heading2"],
    fontSize=11.5,
    textColor=colors.white,
    spaceAfter=0,
    spaceBefore=0,
)
_label_style = ParagraphStyle(
    "planner_label",
    parent=_base_styles["Normal"],
    fontSize=8.5,
    textColor=GRAY,
    fontName="Helvetica",
)
_table_header_style = ParagraphStyle(
    "planner_tblhead",
    parent=_base_styles["Normal"],
    fontSize=8.5,
    textColor=colors.white,
    fontName="Helvetica-Bold",
)
_class_style = ParagraphStyle(
    "planner_class",
    parent=_base_styles["Normal"],
    fontSize=9.5,
    fontName="Helvetica-Bold",
    leading=11,
)
_tip_style = ParagraphStyle(
    "planner_tip",
    parent=_base_styles["Normal"],
    fontSize=8.5,
    textColor=NAVY,
    fontName="Helvetica-Oblique",
    leading=11,
)
_check_text_style = ParagraphStyle(
    "planner_checktext",
    parent=_base_styles["Normal"],
    fontSize=9,
    leading=12,
)
_egg_style = ParagraphStyle(
    "planner_egg",
    parent=_base_styles["Normal"],
    fontSize=8,
    textColor=GRAY,
    fontName="Helvetica-Oblique",
    leading=10,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _section_bar(
    text: str,
    width: float = 7.5 * inch,
    height: float = 0.24 * inch,
    color: Any = NAVY,
) -> Table:
    t = Table(
        [[Paragraph(text, _section_head_style)]],
        colWidths=[width],
        rowHeights=[height],
    )
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


def _checkbox_cell() -> Table:
    t = Table([[""]], colWidths=[0.16 * inch], rowHeights=[0.16 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1.1, colors.HexColor("#888888")),
            ]
        )
    )
    return t


def _checklist(items: list[str]) -> Table:
    rows = [[_checkbox_cell(), Paragraph(item, _check_text_style)] for item in items]
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


def _blank_rule_table(
    nrows: int,
    headers: list[str],
    col_widths: list[float],
    row_h: float = 0.42 * inch,
) -> Table:
    data: list[list[Any]] = [[Paragraph(h, _label_style) for h in headers]]
    for _ in range(nrows):
        data.append(["" for _ in headers])
    t = Table(data, colWidths=col_widths, rowHeights=[0.22 * inch] + [row_h] * nrows)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
                ("GRID", (0, 0), (-1, -1), 0.6, LIGHT_GRAY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


# ---------------------------------------------------------------------------
# Subject color assignment
# ---------------------------------------------------------------------------


class _SubjectColorMap:
    """Assigns colors to subjects dynamically in encounter order."""

    def __init__(self) -> None:
        self._map: dict[str, Any] = {}
        self._next_index = 0

    def get(self, subject: str) -> Any:
        if subject not in self._map:
            if self._next_index < len(_COLOR_PALETTE):
                self._map[subject] = _COLOR_PALETTE[self._next_index]
                self._next_index += 1
            else:
                self._map[subject] = colors.white
        return self._map[subject]


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------


def _esc(text: str) -> str:
    """Escape a plain string for safe use inside a reportlab Paragraph."""
    return html.escape(text, quote=False)


def _overview_page(student_name: str, grade: int | None, theme: Theme) -> list[Any]:
    story: list[Any] = []

    story.append(Paragraph(_esc(theme.title(student_name)), _title_style))

    grade_label = f"{grade}th Grade" if grade else "Middle School"
    story.append(
        Paragraph(
            f"{grade_label} &nbsp;\u2014&nbsp; Overview &amp; Planning Page",
            _subtitle_style,
        )
    )

    # Week-of / A-B chooser
    def ab_choice_cell(label: str) -> Table:
        inner = Table(
            [
                [
                    Paragraph(f"<b>{label}</b>", _check_text_style),
                    _checkbox_cell(),
                    Paragraph("A-day", _check_text_style),
                    _checkbox_cell(),
                    Paragraph("B-day", _check_text_style),
                ]
            ],
            colWidths=[1.15 * inch, 0.2 * inch, 0.5 * inch, 0.2 * inch, 0.5 * inch],
        )
        inner.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        return inner

    header_tbl = Table(
        [
            [
                Paragraph("<b>Week of:</b> _______________________", _check_text_style),
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
            "Check the school calendar/Blackbaud for the A/B rotation, "
            "circle it here, then use the matching Wed/Thu page this week.",
            _label_style,
        )
    )
    story.append(Spacer(1, 10))

    # Tests & quizzes
    story.append(_section_bar(_esc(theme.tests_header)))
    story.append(
        _blank_rule_table(
            4,
            [
                "Subject",
                "Topic",
                "Test Date",
                "Study Days Planned (write which nights)",
            ],
            [1.4 * inch, 2.0 * inch, 1.1 * inch, 3.0 * inch],
        )
    )
    story.append(Spacer(1, 10))

    # Projects
    story.append(_section_bar(_esc(theme.projects_header)))
    story.append(
        _blank_rule_table(
            4,
            [
                "Subject",
                "Assignment",
                "Due Date",
                "Steps / Checkpoints (3-4 mini-deadlines)",
            ],
            [1.4 * inch, 2.0 * inch, 1.1 * inch, 3.0 * inch],
        )
    )
    story.append(Spacer(1, 10))

    # Goals
    story.append(_section_bar(_esc(theme.goals_header)))
    goals_tbl = Table(
        [[""], [""], [""]],
        colWidths=[7.5 * inch],
        rowHeights=[0.32 * inch] * 3,
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

    # How to use
    story.append(_section_bar(_esc(theme.howto_header), color=ACCENT))
    howto = (
        "1) Every class, write down the homework the second it's assigned "
        "\u2014 don't trust your memory. "
        "2) If nothing's assigned, write \u201cnone\u201d so you know you checked. "
        "3) Tests and projects go on THIS page as soon as you hear about them, "
        "even if they're weeks away. "
        "4) Do the End-of-Day Checklist on each daily page before you leave school "
        "or close your backpack at home."
    )
    howto_tbl = Table([[Paragraph(howto, _check_text_style)]], colWidths=[7.5 * inch])
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


def _homework_table(
    periods: list[dict[str, str]],
    color_map: _SubjectColorMap,
    row_height: float = 0.5 * inch,
) -> Table:
    """Build the class-by-class homework log table for a list of periods.

    Shared by daily pages and combined block pages (DRY).
    """
    header = [
        Paragraph(_esc(h), _table_header_style)
        for h in [
            "Class",
            "Homework / Assignment",
            "Due Date",
            "Materials Needed",
            "Done",
        ]
    ]
    data: list[list[Any]] = [header]
    row_colors = []
    for p in periods:
        name_p = Paragraph(
            f"<b>{_esc(p['name'])}</b><br/>"
            f"<font size=7 color='#777777'>{_esc(p['start'])}\u2013{_esc(p['end'])}</font>",
            _class_style,
        )
        data.append([name_p, "", "", "", ""])
        row_colors.append(color_map.get(p["name"]))

    col_widths = [1.5 * inch, 2.95 * inch, 0.85 * inch, 1.5 * inch, 0.5 * inch]
    row_heights = [0.24 * inch] + [row_height] * len(periods)
    t = Table(data, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)
    style_cmds: list[Any] = [
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
        style_cmds.append(("BACKGROUND", (0, i), (0, i), c))
    t.setStyle(TableStyle(style_cmds))
    return t


def _priorities_block(theme: Theme) -> list[Any]:
    """Build the 'Top 3 Priorities' section (header + rows). Shared/DRY."""
    block: list[Any] = [_section_bar(_esc(theme.priorities_header))]
    pri_rows = [
        [
            _checkbox_cell(),
            Paragraph(
                f"{i}.  ___________________________________________________",
                _check_text_style,
            ),
        ]
        for i in range(1, 4)
    ]
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
    block.append(pri_tbl)
    return block


def _ef_tip_block(base_day: str, theme: Theme, rng: random.Random) -> list[Any]:
    """Build the EF-tip box + optional easter egg. Shared/DRY."""
    block: list[Any] = []
    tip_text = theme.tip_for(base_day, rng)
    tip_tbl = Table([[Paragraph(_esc(tip_text), _tip_style)]], colWidths=[7.5 * inch])
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
    block.append(tip_tbl)

    egg = theme.easter_egg(rng)
    if egg:
        block.append(Spacer(1, 4))
        egg_tbl = Table([[Paragraph(_esc(egg), _egg_style)]], colWidths=[7.5 * inch])
        egg_tbl.setStyle(
            TableStyle(
                [
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        block.append(egg_tbl)
    return block


def _end_of_day_checklist(theme: Theme) -> list[Any]:
    """Build the end-of-day checklist section. Shared/DRY."""
    return [
        _section_bar(_esc(theme.checklist_header), color=ACCENT),
        _checklist(
            [
                "I wrote down homework for every class (or wrote \u201cnone\u201d).",
                "I checked today\u2019s box against what\u2019s actually in my backpack.",
                "I packed the books/materials I need for tomorrow.",
                "I looked at the Tests & Projects box on the overview page.",
                "Parent check: ______________________ (initial)",
            ]
        ),
    ]


def _day_header(title_text: str) -> Table:
    """Build the day-page header row (title + date line)."""
    head = Table(
        [
            [
                Paragraph(title_text, _day_title_style),
                Paragraph("Date: _______________", _day_sub_style),
            ]
        ],
        colWidths=[5.5 * inch, 2.0 * inch],
    )
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    return head


def _daily_page(
    day_name: str,
    label_suffix: str,
    periods: list[dict[str, str]],
    color_map: _SubjectColorMap,
    theme: Theme,
    rng: random.Random,
) -> list[Any]:
    """Build a single daily page. periods should already exclude Advisory/Lunch."""
    base_day = day_name.split("-")[0] if "-" in day_name else day_name

    story: list[Any] = [_day_header(f"{day_name.upper()}{label_suffix}"), Spacer(1, 6)]
    story.extend(_priorities_block(theme))
    story.append(Spacer(1, 8))
    story.append(_section_bar(_esc(theme.homework_header)))
    story.append(_homework_table(periods, color_map))
    story.append(Spacer(1, 8))
    story.extend(_ef_tip_block(base_day, theme, rng))
    story.append(Spacer(1, 8))
    story.extend(_end_of_day_checklist(theme))
    return story


def _combined_block_page(
    day_name: str,
    a_periods: list[dict[str, str]],
    b_periods: list[dict[str, str]],
    color_map: _SubjectColorMap,
    theme: Theme,
    rng: random.Random,
) -> list[Any]:
    """Build a combined block page with A-day and B-day stacked.

    Saves a sheet of paper vs. two separate pages. Shares one priorities
    section, one EF tip, and one checklist; each rotation gets its own
    clearly-labeled homework table. Uses tighter row heights so both fit.
    """
    story: list[Any] = [
        _day_header(f"{day_name.upper()} \u2014 A & B DAYS"),
        Spacer(1, 3),
    ]
    story.append(
        Paragraph(
            "Two rotations on one page \u2014 use the table that matches today\u2019s "
            "A/B day (check the overview page).",
            _label_style,
        )
    )
    story.append(Spacer(1, 5))

    story.extend(_priorities_block(theme))
    story.append(Spacer(1, 6))

    # A-day table (tight rows so both rotations + footer fit on one page)
    story.append(_section_bar(f"{_esc(theme.homework_header)} \u2014 A-DAY"))
    story.append(_homework_table(a_periods, color_map, row_height=0.34 * inch))
    story.append(Spacer(1, 5))

    # B-day table
    story.append(_section_bar(f"{_esc(theme.homework_header)} \u2014 B-DAY"))
    story.append(_homework_table(b_periods, color_map, row_height=0.34 * inch))
    story.append(Spacer(1, 6))

    story.extend(_ef_tip_block(day_name, theme, rng))
    story.append(Spacer(1, 6))
    story.extend(_end_of_day_checklist(theme))
    return story


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _filter_periods(periods: list[dict[str, str]]) -> list[dict[str, str]]:
    """Drop Advisory and Lunch from a period list (prefix match)."""
    return [p for p in periods if not any(p["name"].startswith(exc) for exc in _EXCLUDED_SUBJECTS)]


def build_pdf(
    schedule: dict[str, list[dict[str, str]]],
    student_name: str = "",
    grade: int | None = None,
    theme: Theme | str | None = None,
    combine_blocks: bool = False,
    seed: int | None = None,
) -> bytes:
    """Generate a planner PDF from a parsed schedule.

    Args:
        schedule: Dict from ics_parser.parse_schedule() mapping day-type keys
                  to lists of period dicts with "period", "name", "start", "end".
        student_name: Student's first name (used in title). Falls back to generic.
        grade: Grade number (6, 7, 8). Falls back to "Middle School".
        theme: A Theme instance, a theme key string, or None (classic).
        combine_blocks: If True, Wed A/B and Thu A/B are each stacked onto one
                        page (6 pages total instead of 8).
        seed: Optional RNG seed for reproducible tip/easter-egg selection.
              If None, selection is fresh each call (the "surprise" element).

    Returns:
        PDF file content as bytes.
    """
    if theme is None:
        theme = CLASSIC
    elif isinstance(theme, str):
        theme = get_theme(theme)

    # Non-crypto: only used to pick which fun tip/easter-egg to show.
    rng = random.Random(seed)  # noqa: S311

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=0.45 * inch,
        bottomMargin=0.4 * inch,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
    )

    color_map = _SubjectColorMap()
    story: list[Any] = []

    # Page 1: Overview
    story.extend(_overview_page(student_name, grade, theme))
    story.append(PageBreak())

    # Build the daily-page sequence. Each entry is a callable returning a story.
    pages: list[list[Any]] = []

    pages.append(
        _daily_page(
            "Monday",
            "",
            _filter_periods(schedule.get("Monday", [])),
            color_map,
            theme,
            rng,
        )
    )
    pages.append(
        _daily_page(
            "Tuesday",
            "",
            _filter_periods(schedule.get("Tuesday", [])),
            color_map,
            theme,
            rng,
        )
    )

    if combine_blocks:
        # Stack Wed-A + Wed-B on one page, Thu-A + Thu-B on one page (6 total).
        pages.append(
            _combined_block_page(
                "Wednesday",
                _filter_periods(schedule.get("Wednesday-A", [])),
                _filter_periods(schedule.get("Wednesday-B", [])),
                color_map,
                theme,
                rng,
            )
        )
        pages.append(
            _combined_block_page(
                "Thursday",
                _filter_periods(schedule.get("Thursday-A", [])),
                _filter_periods(schedule.get("Thursday-B", [])),
                color_map,
                theme,
                rng,
            )
        )
    else:
        pages.append(
            _daily_page(
                "Wednesday",
                " \u2014 A-day",
                _filter_periods(schedule.get("Wednesday-A", [])),
                color_map,
                theme,
                rng,
            )
        )
        pages.append(
            _daily_page(
                "Wednesday",
                " \u2014 B-day",
                _filter_periods(schedule.get("Wednesday-B", [])),
                color_map,
                theme,
                rng,
            )
        )
        pages.append(
            _daily_page(
                "Thursday",
                " \u2014 A-day",
                _filter_periods(schedule.get("Thursday-A", [])),
                color_map,
                theme,
                rng,
            )
        )
        pages.append(
            _daily_page(
                "Thursday",
                " \u2014 B-day",
                _filter_periods(schedule.get("Thursday-B", [])),
                color_map,
                theme,
                rng,
            )
        )

    pages.append(
        _daily_page(
            "Friday",
            "",
            _filter_periods(schedule.get("Friday", [])),
            color_map,
            theme,
            rng,
        )
    )

    for i, page_story in enumerate(pages):
        story.extend(page_story)
        if i < len(pages) - 1:
            story.append(PageBreak())

    doc.build(story)
    return buf.getvalue()
