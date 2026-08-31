"""Tests for the theme system and themed/combined PDF generation."""

from __future__ import annotations

import random
import re
from pathlib import Path

import pytest
from ics_parser import parse_schedule
from pdf_builder import build_pdf
from themes import DEFAULT_THEME_KEY, get_theme, list_themes
from themes.base import CLASSIC, Theme

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

ALL_KEYS = ["classic", "sports", "video_games", "music", "slang"]


@pytest.fixture
def real_schedule() -> dict:
    ics_text = (FIXTURES_DIR / "real_anonymized.ics").read_text()
    return parse_schedule(ics_text)


def _count_pdf_pages(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf))


class TestRegistry:
    def test_all_themes_registered(self) -> None:
        keys = {t["key"] for t in list_themes()}
        assert keys == set(ALL_KEYS)

    def test_list_themes_has_metadata(self) -> None:
        for t in list_themes():
            assert t["key"]
            assert t["name"]
            assert t["description"]

    def test_get_theme_by_key(self) -> None:
        assert get_theme("sports").key == "sports"
        assert get_theme("VIDEO_GAMES").key == "video_games"  # case-insensitive
        assert get_theme("  music  ").key == "music"  # trimmed

    def test_unknown_theme_falls_back_to_classic(self) -> None:
        assert get_theme("nonsense").key == DEFAULT_THEME_KEY
        assert get_theme("").key == DEFAULT_THEME_KEY
        assert get_theme(None).key == DEFAULT_THEME_KEY


class TestThemeContent:
    """Content-validity guards — catch things that would break rendering."""

    # Matches emoji / symbol / pictographic codepoints that reportlab's base
    # Helvetica cannot render (spec §5.4 forbids these).
    _EMOJI_RE = re.compile(
        "[\U0001f000-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff\U00002190-\U000021ff\U00002b00-\U00002bff]"
    )

    @pytest.mark.parametrize("key", ALL_KEYS)
    def test_no_emoji_glyphs_anywhere(self, key: str) -> None:
        """No theme string may contain emoji/pictographs (won't render)."""
        theme = get_theme(key)
        strings: list[str] = [
            theme.display_name,
            theme.description,
            theme.title_template,
            theme.title_template_no_name,
            theme.tests_header,
            theme.projects_header,
            theme.goals_header,
            theme.howto_header,
            theme.priorities_header,
            theme.homework_header,
            theme.checklist_header,
        ]
        for pool in theme.ef_tips.values():
            strings.extend(pool)
        strings.extend(theme.easter_eggs)

        for s in strings:
            match = self._EMOJI_RE.search(s)
            assert match is None, f"{key}: emoji/glyph {match!r} in: {s!r}"

    @pytest.mark.parametrize("key", ALL_KEYS)
    def test_every_weekday_has_tips(self, key: str) -> None:
        theme = get_theme(key)
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            assert theme.ef_tips.get(day), f"{key} missing tips for {day}"

    @pytest.mark.parametrize("key", ALL_KEYS)
    def test_title_renders_with_and_without_name(self, key: str) -> None:
        theme = get_theme(key)
        assert "Alex" in theme.title("Alex")
        # No-name title must not contain a stray unformatted placeholder
        assert "{name}" not in theme.title("")

    def test_slang_uses_only_verified_terms(self) -> None:
        """Guard: the slang theme must not introduce unvetted slang.

        We assert the risky/ambiguous terms we deliberately excluded never
        appear (case-insensitive, word-boundary where sensible).
        """
        slang = get_theme("slang")
        blob = " ".join(
            [slang.title_template, slang.description]
            + [t for pool in slang.ef_tips.values() for t in pool]
            + slang.easter_eggs
            + [
                slang.tests_header,
                slang.projects_header,
                slang.goals_header,
                slang.howto_header,
                slang.priorities_header,
                slang.checklist_header,
            ]
        ).lower()
        forbidden = ["gyat", "sus", "skibidi", "ohio", "6-7", "6 7", "rizzler"]
        for term in forbidden:
            assert term not in blob, f"excluded slang term leaked in: {term}"


class TestClassicUnchanged:
    """Classic theme must preserve the original approved wording."""

    def test_classic_headers(self) -> None:
        assert CLASSIC.tests_header == "TESTS & QUIZZES THIS WEEK"
        assert CLASSIC.checklist_header == "END-OF-DAY CHECKLIST"
        assert CLASSIC.homework_header == "CLASS-BY-CLASS HOMEWORK LOG"

    def test_classic_has_no_easter_eggs(self) -> None:
        assert CLASSIC.easter_eggs == []

    def test_classic_title(self) -> None:
        assert CLASSIC.title("Kaden") == "Kaden\u2019s Weekly Planner"
        assert CLASSIC.title("") == "Weekly Planner"


class TestRandomization:
    def test_seed_makes_tip_selection_reproducible(self) -> None:
        theme = get_theme("sports")
        r1 = random.Random(123)
        r2 = random.Random(123)
        assert theme.tip_for("Monday", r1) == theme.tip_for("Monday", r2)

    def test_different_seeds_can_differ(self) -> None:
        """Over many draws, a multi-item pool should yield >1 distinct value."""
        theme = get_theme("sports")  # Monday pool has 2 tips
        seen = {theme.tip_for("Monday", random.Random(s)) for s in range(20)}
        assert len(seen) > 1

    def test_classic_single_tip_pool_is_stable(self) -> None:
        seen = {CLASSIC.tip_for("Monday", random.Random(s)) for s in range(10)}
        assert len(seen) == 1  # classic has one tip per day

    def test_seed_makes_full_pdf_reproducible(self, real_schedule: dict) -> None:
        a = build_pdf(real_schedule, theme="video_games", seed=42)
        b = build_pdf(real_schedule, theme="video_games", seed=42)
        # Same seed -> same tip/egg choices. PDFs contain a timestamp/ID that
        # differs, so compare page count + that both are valid instead.
        assert a[:4] == b"%PDF"
        assert _count_pdf_pages(a) == _count_pdf_pages(b)


class TestThemedPDFGeneration:
    @pytest.mark.parametrize("key", ALL_KEYS)
    def test_each_theme_generates_valid_pdf(self, key: str, real_schedule: dict) -> None:
        pdf = build_pdf(real_schedule, student_name="Alex", grade=7, theme=key, seed=1)
        assert pdf[:4] == b"%PDF"
        assert _count_pdf_pages(pdf) == 8

    def test_theme_instance_accepted(self, real_schedule: dict) -> None:
        """build_pdf accepts a Theme object, not just a key string."""
        theme_obj = get_theme("music")
        pdf = build_pdf(real_schedule, theme=theme_obj, seed=1)
        assert pdf[:4] == b"%PDF"

    def test_none_theme_defaults_classic(self, real_schedule: dict) -> None:
        pdf = build_pdf(real_schedule, theme=None, seed=1)
        assert pdf[:4] == b"%PDF"


class TestCombinedBlocks:
    def test_combined_is_six_pages(self, real_schedule: dict) -> None:
        pdf = build_pdf(real_schedule, combine_blocks=True, seed=1)
        assert _count_pdf_pages(pdf) == 6

    def test_standard_is_eight_pages(self, real_schedule: dict) -> None:
        pdf = build_pdf(real_schedule, combine_blocks=False, seed=1)
        assert _count_pdf_pages(pdf) == 8

    @pytest.mark.parametrize("key", ALL_KEYS)
    def test_combined_no_overflow_any_theme(self, key: str, real_schedule: dict) -> None:
        """Every theme's combined page must fit in 6 pages across seeds."""
        for seed in range(6):
            pdf = build_pdf(
                real_schedule,
                student_name="Alexandra",
                grade=7,
                theme=key,
                combine_blocks=True,
                seed=seed,
            )
            assert _count_pdf_pages(pdf) == 6, f"{key} seed={seed} overflowed"


class TestThemeIsDataclass:
    def test_theme_is_frozen(self) -> None:
        """Themes are immutable — accidental mutation should raise."""
        with pytest.raises(Exception):  # noqa: B017 - FrozenInstanceError
            CLASSIC.tests_header = "changed"  # type: ignore[misc]

    def test_default_theme_is_classic_instance(self) -> None:
        assert isinstance(CLASSIC, Theme)
        assert CLASSIC.key == "classic"
