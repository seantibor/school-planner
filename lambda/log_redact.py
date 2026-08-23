"""Redacting logger for the school planner Lambda.

All log output passes through a filter on the root logger's handler that
scrubs sensitive patterns before anything reaches CloudWatch:
- URLs (including ICS feed URLs which act as bearer tokens)
- Email addresses
- Patterns that look like names (capitalized word pairs)

This catches output from our code AND from third-party libraries (e.g.,
requests/urllib3 at debug level), since everything flows through root.

Approach follows Python stdlib best practices: logging.Filter subclass
attached to the handler (not the logger), modifying the LogRecord before
emission. See: https://docs.python.org/3/library/logging.html#filter-objects
"""

from __future__ import annotations

import logging
import re

# Patterns to redact
_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# Capitalized word pairs that look like names (e.g. "Kaden Smith", "Jane Doe")
# Deliberately conservative — won't catch single names or uncapitalized ones
_NAME_RE = re.compile(r"\b[A-Z][a-z]{1,15}\s+[A-Z][a-z]{1,20}\b")


def _redact(text: str) -> str:
    """Apply all redaction patterns to a string."""
    text = _URL_RE.sub("[REDACTED_URL]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _NAME_RE.sub("[REDACTED_NAME]", text)
    return text


class RedactingFilter(logging.Filter):
    """Logging filter that redacts sensitive patterns from all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: _redact(str(v)) if isinstance(v, str) else v for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    _redact(str(a)) if isinstance(a, str) else a for a in record.args
                )
        return True


def install_redacting_filter() -> None:
    """Install the redacting filter on the root logger's handler(s).

    Call this once at module load time (e.g., top of handler.py).
    Safe to call multiple times — won't double-install.

    In AWS Lambda, the root logger comes pre-configured with a handler
    that writes to CloudWatch. We attach our filter to that handler so
    ALL log output (ours + third-party libs) gets scrubbed.
    """
    root = logging.getLogger()

    # Lambda pre-configures a handler; if somehow there isn't one, add a default
    if not root.handlers:
        root.addHandler(logging.StreamHandler())

    for handler in root.handlers:
        # Don't double-install
        if not any(isinstance(f, RedactingFilter) for f in handler.filters):
            handler.addFilter(RedactingFilter())

    # Ensure root level allows INFO through
    if root.level == logging.NOTSET or root.level > logging.INFO:
        root.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a module-level logger. Standard stdlib pattern.

    Usage:
        from log_redact import get_logger
        logger = get_logger(__name__)
        logger.info("Processing request for %s", some_url)
        # CloudWatch sees: "Processing request for [REDACTED_URL]"
    """
    return logging.getLogger(name)
