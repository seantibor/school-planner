#!/usr/bin/env python3
"""Local end-to-end test: fetch a real ICS feed and generate a PDF.

Usage:
    uv run scripts/local_test.py "https://yourschool.myschoolapp.com/podium/feed/iCal.aspx?z=..."

The PDF is written to test_output.pdf in the current directory.
DO NOT commit this script's output or the URL you use.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add lambda/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lambda"))

from ics_fetch import fetch_ics  # noqa: E402
from ics_parser import parse_schedule  # noqa: E402
from pdf_builder import build_pdf  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run scripts/local_test.py <ICS_URL> [student_name] [grade]")
        print("  Example: uv run scripts/local_test.py 'https://...' Kaden 6")
        sys.exit(1)

    ics_url = sys.argv[1]
    student_name = sys.argv[2] if len(sys.argv) > 2 else ""
    grade = int(sys.argv[3]) if len(sys.argv) > 3 else None

    print("Fetching ICS feed...")
    ics_text = fetch_ics(ics_url)
    print(f"  Got {len(ics_text)} bytes of ICS data")

    print("Parsing schedule...")
    schedule = parse_schedule(ics_text)
    for day_type, periods in schedule.items():
        print(f"  {day_type}: {len(periods)} periods")

    print("Generating PDF...")
    pdf_bytes = build_pdf(schedule, student_name=student_name, grade=grade)

    output_path = Path("test_output.pdf")
    output_path.write_bytes(pdf_bytes)
    print(f"Written {len(pdf_bytes):,} bytes to {output_path}")
    print("Open test_output.pdf to verify the layout.")


if __name__ == "__main__":
    main()
