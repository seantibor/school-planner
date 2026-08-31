"""AWS Lambda handler for the planner PDF generator.

Entry point: POST /generate
Accepts a JSON body:
  - ics_url        (required) Blackbaud/Podium ICS feed URL
  - student_name   (optional) first name for the title
  - grade          (optional) 6, 7, or 8
  - theme          (optional) theme key: classic|sports|video_games|music|slang
                   (unknown/missing falls back to classic)
  - combine_blocks (optional) if true, Wed/Thu A+B stack onto one page each
                   (6 pages instead of 8)
Returns PDF binary or a JSON error.

PRIVACY:
- Operational logs are sent to CloudWatch with a 7-day retention.
- All log output passes through a redacting filter (log_redact.py) that
  strips URLs, email addresses, and name patterns before writing.
- The raw ICS content and parsed schedule data are NEVER logged.
- API Gateway request/response body logging remains disabled.
"""

from __future__ import annotations

import base64
import json
import re
import time
from typing import Any

from ics_fetch import FetchError, fetch_ics
from ics_parser import parse_schedule
from log_redact import get_logger, install_redacting_filter
from pdf_builder import build_pdf

# Install redaction on the root logger's handlers at import time,
# before any log output can escape unfiltered.
install_redacting_filter()

logger = get_logger(__name__)

# Basic URL pattern for Blackbaud/Podium ICS feeds
_ICS_URL_PATTERN = re.compile(r"^https://.*\.(myschoolapp|blackbaud)\.com/.*iCal", re.IGNORECASE)

# More permissive fallback — any HTTPS URL ending in .ics or containing iCal
_ICS_URL_FALLBACK = re.compile(r"^https://.*(\\.ics|iCal)", re.IGNORECASE)


def _error_response(status_code: int, message: str) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps({"error": message}),
    }


def _validate_request(
    body: dict[str, Any],
) -> tuple[str, str, int | None, str, bool]:
    """Validate and extract request parameters.

    Returns:
        Tuple of (ics_url, student_name, grade, theme, combine_blocks).

    Raises:
        ValueError: With a user-friendly message if validation fails.
    """
    ics_url = body.get("ics_url", "").strip()
    if not ics_url:
        raise ValueError("Please provide your ICS calendar feed URL.")

    if not ics_url.startswith("https://"):
        raise ValueError("The URL must use HTTPS. Please check and try again.")

    if not (_ICS_URL_PATTERN.match(ics_url) or _ICS_URL_FALLBACK.match(ics_url)):
        raise ValueError(
            "This doesn't look like a Blackbaud/Podium calendar feed URL. "
            "Please follow the instructions to copy your ICS feed link."
        )

    student_name = body.get("student_name", "").strip()
    grade_raw = body.get("grade")
    grade = None
    if grade_raw is not None:
        try:
            grade = int(grade_raw)
            if grade not in (6, 7, 8):
                grade = None
        except ValueError, TypeError:
            grade = None

    # Theme is validated by the registry (unknown/None falls back to classic),
    # so no error is raised here — just normalize to a string key.
    theme = str(body.get("theme", "") or "").strip().lower()

    # combine_blocks: accept truthy JSON bool or common string forms.
    combine_raw = body.get("combine_blocks", False)
    if isinstance(combine_raw, str):
        combine_blocks = combine_raw.strip().lower() in ("true", "1", "yes", "on")
    else:
        combine_blocks = bool(combine_raw)

    return ics_url, student_name, grade, theme, combine_blocks


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entry point. Processes a single PDF generation request."""
    start = time.time()

    # Parse request body
    body_raw = event.get("body", "")
    if event.get("isBase64Encoded"):
        body_raw = base64.b64decode(body_raw).decode("utf-8")

    try:
        body = json.loads(body_raw) if body_raw else {}
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in request body")
        return _error_response(400, "Invalid JSON in request body.")

    # Validate
    try:
        ics_url, student_name, grade, theme, combine_blocks = _validate_request(body)
    except ValueError as e:
        logger.info("Validation failed: %s", str(e))
        return _error_response(400, str(e))

    # Fetch ICS (URL is redacted if it appears in logs)
    logger.info("Fetching ICS feed from %s", ics_url)
    try:
        ics_text = fetch_ics(ics_url)
    except FetchError as e:
        logger.warning("Fetch failed: %s", str(e))
        return _error_response(e.status_code, str(e))

    # Parse schedule
    try:
        schedule = parse_schedule(ics_text)
    except ValueError as e:
        logger.warning("Parse failed: %s", str(e))
        return _error_response(422, str(e))

    logger.info(
        "Schedule parsed: %d day-types found (theme=%s, combine=%s)",
        len(schedule),
        theme or "classic",
        combine_blocks,
    )

    # Generate PDF
    try:
        pdf_bytes = build_pdf(
            schedule,
            student_name=student_name,
            grade=grade,
            theme=theme,
            combine_blocks=combine_blocks,
        )
    except Exception:
        logger.exception("PDF generation failed")
        return _error_response(500, "An unexpected error occurred generating the PDF.")

    elapsed = time.time() - start
    logger.info("PDF generated: %d bytes in %.2fs", len(pdf_bytes), elapsed)

    # Return PDF
    filename = f"{student_name}_planner.pdf" if student_name else "planner.pdf"
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/pdf",
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
        "body": base64.b64encode(pdf_bytes).decode("utf-8"),
        "isBase64Encoded": True,
    }
