"""AWS Lambda handler for the planner PDF generator.

Entry point: POST /generate
Accepts JSON body with ics_url, optional student_name and grade.
Returns PDF binary or a JSON error.

PRIVACY HARD REQUIREMENTS:
- The ICS URL is NEVER logged, stored, or persisted anywhere.
- Schedule data exists only in memory for the duration of the request.
- No print() or logging calls that could leak request content to CloudWatch.
- API Gateway is configured (via Terraform) to suppress request/response logging.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any

from ics_fetch import FetchError, fetch_ics
from ics_parser import parse_schedule
from pdf_builder import build_pdf

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


def _validate_request(body: dict[str, Any]) -> tuple[str, str, int | None]:
    """Validate and extract request parameters.

    Returns:
        Tuple of (ics_url, student_name, grade).

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

    return ics_url, student_name, grade


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entry point. Processes a single PDF generation request."""
    # Parse request body
    body_raw = event.get("body", "")
    if event.get("isBase64Encoded"):
        body_raw = base64.b64decode(body_raw).decode("utf-8")

    try:
        body = json.loads(body_raw) if body_raw else {}
    except json.JSONDecodeError:
        return _error_response(400, "Invalid JSON in request body.")

    # Validate
    try:
        ics_url, student_name, grade = _validate_request(body)
    except ValueError as e:
        return _error_response(400, str(e))

    # Fetch ICS (URL used here and nowhere else — never logged)
    try:
        ics_text = fetch_ics(ics_url)
    except FetchError as e:
        return _error_response(e.status_code, str(e))

    # Parse schedule
    try:
        schedule = parse_schedule(ics_text)
    except ValueError as e:
        return _error_response(422, str(e))

    # Generate PDF
    try:
        pdf_bytes = build_pdf(schedule, student_name=student_name, grade=grade)
    except Exception:
        return _error_response(500, "An unexpected error occurred generating the PDF.")

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
