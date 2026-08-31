"""Theme registry for the planner.

Add a new theme by creating a module in this package that defines a Theme
instance, then registering it in _THEMES below.
"""

from __future__ import annotations

from themes.base import CLASSIC, Theme
from themes.music import MUSIC
from themes.slang import SLANG
from themes.sports import SPORTS
from themes.video_games import VIDEO_GAMES

# Registry: key -> Theme. Order matters for the frontend dropdown.
_THEMES: dict[str, Theme] = {t.key: t for t in [CLASSIC, SPORTS, VIDEO_GAMES, MUSIC, SLANG]}

DEFAULT_THEME_KEY = "classic"


def get_theme(key: str | None) -> Theme:
    """Return the theme for the given key, falling back to classic."""
    if not key:
        return _THEMES[DEFAULT_THEME_KEY]
    return _THEMES.get(key.strip().lower(), _THEMES[DEFAULT_THEME_KEY])


def list_themes() -> list[dict[str, str]]:
    """Return theme metadata for the frontend dropdown."""
    return [
        {"key": t.key, "name": t.display_name, "description": t.description}
        for t in _THEMES.values()
    ]


__all__ = ["Theme", "get_theme", "list_themes", "DEFAULT_THEME_KEY"]
