"""Server-side ICS feed fetching.

Required because Blackbaud's feed endpoints do not include CORS headers,
so browser-side fetch is blocked. This module fetches the ICS content
server-side and returns it as a string.

PRIVACY: The ICS URL is used for exactly one outbound fetch and is never
written to disk, logs, or any persistent location.
"""

from __future__ import annotations

import requests

# Conservative timeout — Blackbaud can be slow but shouldn't take forever
_FETCH_TIMEOUT_SECONDS = 15


class FetchError(Exception):
    """Raised when the ICS URL cannot be fetched."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def fetch_ics(url: str) -> str:
    """Fetch ICS content from the given URL.

    Args:
        url: The Blackbaud/Podium ICS feed URL.

    Returns:
        The raw ICS file content as a string.

    Raises:
        FetchError: If the fetch fails (timeout, bad status, unreachable host).
    """
    try:
        response = requests.get(
            url,
            timeout=_FETCH_TIMEOUT_SECONDS,
            headers={"User-Agent": "PineCrestPlannerBot/1.0"},
        )
    except requests.exceptions.Timeout:
        raise FetchError(
            "The calendar feed took too long to respond. Please try again in a moment.",
            status_code=502,
        ) from None
    except requests.exceptions.ConnectionError:
        raise FetchError(
            "Could not connect to the calendar feed. Please check the URL and try again.",
            status_code=502,
        ) from None
    except requests.exceptions.RequestException as e:
        raise FetchError(
            f"Failed to fetch the calendar feed: {type(e).__name__}",
            status_code=502,
        ) from None

    if response.status_code != 200:
        raise FetchError(
            f"The calendar feed returned an error (HTTP {response.status_code}). "
            "Please verify the URL is correct.",
            status_code=502,
        )

    content_type = response.headers.get("content-type", "")
    # Blackbaud feeds serve as text/calendar; reject obviously wrong content
    if "html" in content_type.lower() and "calendar" not in content_type.lower():
        raise FetchError(
            "The URL returned an HTML page instead of a calendar feed. "
            "Please make sure you're using the ICS/iCal feed URL, not a web page link.",
            status_code=400,
        )

    return response.text
