# Pine Crest Middle School Planner Generator — Build Spec

Status: ready to build. Two real 6th-grade ICS feeds have been fetched and
compared to validate the assumptions below. 7th/8th grade feeds are not yet
verified (see Open Questions).

## 1. Purpose

A small web tool for a known circle of Pine Crest middle-school parents
(6th–8th grade). A parent pastes their kid's Blackbaud/Podium ICS calendar
feed URL, clicks Generate, and downloads a printable, executive-functioning
focused weekly planner PDF for that specific kid's real schedule.

No accounts, no install, no terminal. One field, one button, one download.

## 2. Non-Goals

- No auth, accounts, saved profiles, or repeat visits assumed.
- No persistence of any parent/student data server-side — no database.
- No support for other schools or calendar systems.
- No attempt to scale beyond a handful of families.

## 3. Validated Data Findings

Two real 6th-grade feeds were fetched and diffed directly (not assumed):
Kaden's, and a classmate's. Findings below are confirmed from actual data,
not guesses — flagged separately where something is still just an
assumption.

### 3.1 Bell schedule is shared and fixed (confirmed)

Both students have **identical period start/end times**, because the bell
schedule is school-wide, not per-student:

| Period   | Start    | End                        |
| -------- | -------- | -------------------------- |
| Advisory | 8:00 AM  | 8:10 AM (8:00–8:20 on Wed) |
| P1       | 8:14 AM  | 8:54 AM                    |
| P2       | 8:58 AM  | 9:38 AM                    |
| P3       | 9:42 AM  | 10:22 AM                   |
| P4       | 10:26 AM | 11:06 AM                   |
| P5       | 11:10 AM | 11:50 AM                   |
| P6       | 11:54 AM | 12:29 PM                   |
| P7       | 12:32 PM | 1:07 PM                    |
| P8       | 1:11 PM  | 1:51 PM                    |
| P9       | 1:55 PM  | 2:35 PM                    |
| P10      | 2:40 PM  | 3:25 PM                    |

Wednesday and Thursday have longer block periods (some periods merge/extend,
e.g. 8:24–9:43, 9:47–11:06, 11:10–14:30 spans) and **do not run all 10
periods** — only a subset appears, varying by A/B rotation.

**Implication:** the parser should never hardcode "period N happens at
time X" per subject — it should read whatever period/time/subject triple is
actually in each VEVENT. The subject-to-period mapping is per-student and
must be discovered from the feed, not assumed.

### 3.2 Which subject sits in which period varies per student (confirmed)

Kaden has Ancient Civilizations in P1; his classmate has Spanish A in P1
instead. Same time grid, different subject assignments. This is expected —
the tool must not assume any fixed subject→period relationship.

### 3.3 Monday/Tuesday/Friday fixed, Wed/Thu A/B rotation (confirmed, twice)

Both feeds contain **all-day marker VEVENTs** on every school day that
identify the day type directly:

```
Monday (BRMS)
Tuesday (BRMS)
Wednesday A (BRMS)
Wednesday B (BRMS)
Thursday A (BRMS)
Thursday B (BRMS)
Friday (BRMS)
```

("BRMS" = the middle school division code — this may differ if 7th/8th
grade use a different division tag; check for this rather than hardcoding
"BRMS".)

These markers are the authoritative source for which rotation day it is —
**do not infer A/B from date parity or a hardcoded calendar**; read the
marker event for that date directly. Monday, Tuesday, and Friday have no
A/B split and repeat identically every week. Only Wednesday and Thursday
have two variants.

### 3.4 Course-name cleanup needs to be a general rule, not a lookup table (important correction)

The first version of this tool (built for Kaden alone) used a hardcoded
dictionary mapping specific raw strings to clean names. **That does not
generalize** — it would silently fail to clean any course name it hadn't
seen before (e.g. the classmate's "Advanced Mathematics - 8 Goldberg (8)"
or "Applied AI and Computing-6 - 4 (4)").

Tested and confirmed pattern instead — **use a general regex-based
cleaner**:

```python
import re

def clean_course_name(raw: str) -> str:
    """
    Raw Blackbaud/Podium summary strings look like:
      "Ancient Civilizations - 1 (1)"
      "Study Hall-6 - P5-T1 (5)"
      "Physical Education - PE 6-T (6)"
      "Exploratory Engineering-6 - 6 (W) (6)"
      "Advanced Mathematics - 8 Goldberg (8)"
      "Applied AI and Computing-6 - 4 (4)"
      "Band - MWF (5)"
      "Rock Band 678 - MF 7 (7)"
    The trailing "(N)" is the period number (matches the VEVENT's actual
    period). Everything after " - " is section/teacher/day-code detail.
    A trailing "-N" directly on the course name (no space) is often a
    grade-level or cohort suffix on things like "Study Hall-6",
    "Exploratory Engineering-6", "Applied AI and Computing-6".
    """
    s = re.sub(r'\s*\(\w+\)\s*$', '', raw)      # strip trailing "(N)" or "(W)" tag
    s = re.split(r' - ', s)[0]                   # keep only text before first " - "
    s = re.sub(r'-\d+$', '', s)                  # strip trailing "-N" grade/cohort suffix
    return s.strip()
```

Verified output against every raw string seen in both feeds (22 samples,
0 misclassifications requiring a lookup table). Two known minor rough
edges to polish during implementation, not blockers:
- `"Advisory Grade 6 - Baena (Advisory)"` → `"Advisory Grade 6"` (a
  trailing `\d+$` strip after removing "Grade" would tidy this to
  "Advisory" if desired — decide during build whether "Advisory Grade 6"
  is actually fine to display as-is).
- `"Rock Band 678 - MF 7 (7)"` → `"Rock Band 678"` (same shape — trailing
  digits are a cohort code "678" meaning grades 6/7/8 combined, not a
  grade to strip; leave as-is or special-case "Rock Band" as a known
  subject name).

Do not build a second hardcoded per-string table for these — extend the
regex or add a very short list of **known multi-grade elective names**
("Rock Band", "PCNN") that skip the trailing-digit strip.

### 3.5 One numeric quirk already resolved

A raw string like `"Advanced Mathematics - 8 Goldberg (8)"` looks at first
glance like it could mean "8th grade," but it doesn't — it was verified
against the actual VEVENT start/end time (13:11–13:51) which matches
period 8 exactly. **The number before the teacher name is the period
number**, consistently, matching the trailing "(N)" tag. No grade-level
inference should ever be drawn from numbers embedded in the raw summary —
only from the "Advisory Grade 6" style strings that say "Grade" explicitly,
and even those should be treated as informational, not load-bearing.

## 4. ICS Feed Parsing Logic

1. Fetch the ICS URL server-side (required — see §7, CORS is blocked).
2. Parse with a standard ICS library (`icalendar` in Python was used for
   prototyping; any equivalent works).
3. Separate events into two kinds:
   - **All-day marker events** (`DTSTART` is a `date`, not `datetime`) —
     these are the day-type labels (`"Monday (BRMS)"`,
     `"Wednesday A (BRMS)"`, etc.). Use these to build a date→day-type map.
   - **Timed period events** (`DTSTART`/`DTEND` are `datetime`) — these are
     actual class periods. Extract period number from the trailing `(N)`
     tag in the summary (fall back to ordinal position by start time if a
     tag is ever missing), clean the name per §3.4, and record start/end
     times.
4. Group timed events by **day-type** (Monday / Tuesday / Wednesday-A /
   Wednesday-B / Thursday-A / Thursday-B / Friday), not by specific
   calendar date — Monday's week-1 schedule and Monday's week-3 schedule
   should be identical; use the first clean occurrence of each day-type as
   the canonical template, matching what was done for Kaden's original
   `weekA.json` / `weekB.json`.
5. Produce a structured intermediate representation, e.g.:

```json
{
  "Monday": [
    {"period": "Advisory", "name": "Advisory", "start": "8:00 AM", "end": "8:10 AM"},
    {"period": "1", "name": "Ancient Civilizations", "start": "8:14 AM", "end": "8:54 AM"}
  ],
  "Tuesday": [ "..." ],
  "Wednesday-A": [ "..." ],
  "Wednesday-B": [ "..." ],
  "Thursday-A": [ "..." ],
  "Thursday-B": [ "..." ],
  "Friday": [ "..." ]
}
```

6. Validate the result before generating a PDF: confirm at least Monday,
   Tuesday, and Friday were found and non-empty, and that some Wednesday
   and Thursday data exists. If validation fails, return a `422` (see §8)
   rather than generating a broken/empty PDF.

## 5. PDF Output Specification

This reproduces the planner already built and approved for Kaden
(`build_ef_planner.py`, using `reportlab`), generalized to take the
per-student parsed schedule (§4) plus the student's first name as inputs
instead of hardcoded `weekA.json`/`weekB.json`.

### 5.1 Structure — 8 pages, portrait letter

- **Page 1 — Weekly Overview**
  - Title: `"{StudentFirstName}'s Weekly Planner"`, subtitle
    `"Pine Crest {Grade}th Grade — Overview & Planning Page"`
  - "Week of: ____" field, plus an A-day/B-day checkbox chooser for both
    Wednesday and Thursday (parent/student marks which rotation applies
    that week, then uses the matching daily page).
  - "Tests & Quizzes This Week" — blank ruled table: Subject / Topic /
    Test Date / Study Days Planned.
  - "Projects & Long-Term Assignments" — blank ruled table: Subject /
    Assignment / Due Date / Steps-Checkpoints.
  - "My Goals for This Week" — 3 blank ruled lines.
  - "How to Use This Planner" — instructional box (four numbered rules,
    see script for exact copy).
- **Pages 2–8 — one page per distinct school day**, in order: Monday,
  Tuesday, Wednesday–A-day, Wednesday–B-day, Thursday–A-day,
  Thursday–B-day, Friday. These are reusable/reprintable every week since
  Mon/Tue/Fri never change and Wed/Thu only have two variants each.

Each daily page contains:
  - Header: day name + rotation label, "Date: ____" field.
  - "Today's Top 3 Priorities" — 3-item checklist with blank lines.
  - "Class-by-Class Homework Log" — table with columns Class / Homework /
    Due Date / Materials Needed / ✓ checkbox. One row per period **for
    that day**, **excluding Advisory and Lunch**. Row background is
    color-coded per subject (§5.2) so the same subject always has the
    same color across every page the student sees — this is a deliberate
    executive-functioning aid (visual pattern recognition), not just
    styling, so it must carry over into the generalized version.
  - A rotating "EF tip" box, one per weekday (§5.3), shown at the bottom
    of that day's page regardless of A/B variant.
  - "End-of-Day Checklist" — fixed 5-item checklist ending in a
    parent-initial line.

### 5.2 Visual design tokens

```python
NAVY = "#1a3c6e"        # headers, section bars, titles
LIGHT_BLUE = "#eef2f8"  # table header fill, EF tip box background
GRAY = "#666666"        # secondary text
LIGHT_GRAY = "#cccccc"  # table gridlines
ACCENT = "#e8871e"      # "How to Use" box, "End-of-Day Checklist" bar
```

Per-subject row colors (**generalize this**: the original was a hardcoded
map of Kaden's 11 subjects — the shared tool needs to assign a color from
a fixed palette to each subject **dynamically**, the first time it's seen
per student, and hold that mapping consistent across that student's own 8
pages. Do not try to standardize colors across different students/PDFs —
only within one student's own document does the color need to stay
consistent.)

Suggested approach: maintain an ordered palette of ~12 pre-chosen pastel
hex values (reuse the 11 from the original script as a starting set, add
1–2 more for headroom), and assign colors to subjects in the order they're
first encountered when building that student's pages. Fall back to white
if a student somehow has more distinct subjects than palette entries.

### 5.3 EF tips (fixed copy, reuse verbatim)

```python
EF_TIPS = {
    "Monday": "EF tip: Do a 2-minute \u201cbrain dump\u201d of everything due this week before you start homework \u2014 it frees up mental energy for the actual work.",
    "Tuesday": "EF tip: Start with your hardest or least-favorite subject first, while your brain is freshest.",
    "Wednesday": "EF tip: Big projects feel less overwhelming when you break them into 3\u20134 small steps with their own mini due-dates.",
    "Thursday": "EF tip: Use Study Hall to work ahead on tomorrow's homework \u2014 future-you will be grateful.",
    "Friday": "EF tip: Before you close your backpack, check next week's tests/projects box on the overview page so nothing sneaks up on you.",
}
```

### 5.4 Fonts / rendering notes

- Base14 Helvetica only — no external font files needed.
- **Do not use emoji or unicode glyphs** (checkmark stars, target icons,
  etc.) — these did not render in reportlab's base font during
  prototyping. Checkboxes are drawn as small bordered table cells
  (`checkbox_cell()` helper), not glyph characters.
- Table header text must be white-on-navy for contrast (a gray-on-navy
  first pass had a contrast bug — already fixed, keep it white).

### 5.5 Reference implementation

The full working `reportlab` implementation for a single hardcoded
student (Kaden) exists and was visually approved page-by-page. Use it as
the direct basis for generalization — the main changes needed are:
(a) accept parsed schedule + student name + grade as parameters instead of
loading `weekA.json`/`weekB.json` from disk, (b) replace the hardcoded
`SUBJECT_COLORS` dict with the dynamic-assignment approach in §5.2,
(c) replace the hardcoded course-name dict (never actually productionized)
with the regex cleaner in §3.4.

## 6. System Architecture

```
GitHub Pages site (static HTML/JS)
  - paste ICS URL box, "Generate" button, download link
        |
        |  HTTPS POST { ics_url, student_name, grade }
        v
API Gateway --> Lambda function
  - fetch ICS server-side
  - parse (Section 4)
  - build PDF (Section 5)
  - return PDF binary, log nothing sensitive
        |
        v
  PDF returned directly in the HTTP response
```

- **Frontend:** static site on GitHub Pages. Minimal — one input field
  (ICS URL), one optional field (student first name / grade, if not
  derivable from the feed), one "Generate" button, one status/error
  message area, one download link once the PDF comes back. Plain
  HTML/CSS/JS is sufficient; no framework required.
- **Backend:** single Lambda function behind an API Gateway HTTP API.
  Performs the ICS fetch server-side — this is required, not optional,
  because direct browser fetch of the ICS URL was tested and **confirmed
  blocked by CORS** (no `Access-Control-*` headers present on the feed
  response at all; verified via `curl -I` with and without a spoofed
  `Origin` header). Parses (§4), builds the PDF (§5), returns it as the
  HTTP response body.
- **No datastore of any kind.** No S3 output bucket, no DB, no queue.
  Fetch → parse → generate → return → discard, within one Lambda
  invocation. This is a hard requirement, not a nice-to-have (see §7).

## 7. Privacy & Security Requirements

The ICS URL functions as a bearer token — anyone holding it can read that
family's calendar, no login required. Given that, and given the project
will live in a **public GitHub repo** specifically so any parent can verify
these claims by reading the actual deployed code:

1. The ICS URL is used for exactly one outbound fetch per request and is
   **never written to disk, logs, a datastore, or any persistent
   location**, by the Lambda or by API Gateway.
2. Configure API Gateway/Lambda logging to **exclude request bodies and
   query strings** (or explicitly scrub them) so the ICS URL can't end up
   in CloudWatch logs by default configuration accident. Verify this by
   inspecting actual logs after a test request, not just by reading the
   config.
3. No secrets are required for the core fetch (the Blackbaud feed itself
   needs no auth) — so there is nothing sensitive in the Lambda's own
   config to leak. If anything is added later that does need a secret, it
   goes in Lambda environment variables / AWS Secrets Manager, and is
   never committed to the repo.
4. CORS on the API Gateway should be locked to the GitHub Pages origin
   only.
5. The frontend page and the README both state in plain language exactly
   what happens to a pasted URL (fetched once, used to generate a PDF,
   discarded, never logged) — and because the repo is public, that claim
   is independently checkable, not just asserted.
6. Basic API Gateway throttling is worth adding as cheap abuse insurance,
   even though the intended audience is small and known.

## 8. API Contract

**POST /generate**

Request:
```json
{
  "ics_url": "https://pinecrest.myschoolapp.com/podium/feed/iCal.aspx?z=...",
  "student_name": "Kaden",
  "grade": 6
}
```
(`student_name` and `grade` are used only for the PDF title/subtitle —
if omitted, fall back to generic labels like "Weekly Planner" / "Middle
School".)

Response (success): `200 OK`, `Content-Type: application/pdf`, binary PDF
body, `Content-Disposition: attachment; filename="{student_name}_planner.pdf"`.

Response (failure modes):
- Malformed/non-ICS-looking URL → `400`, plain-language error.
- Fetch timeout or unreachable host → `502`, plain-language error.
- Feed fetched but doesn't parse into a usable structure per §4 step 6 →
  `422`, plain-language error suggesting the parent double-check the URL.
  (Do not silently fall back to a broken PDF.)

## 9. Repo Structure

```
/                      README.md - what this is, how it works, privacy note
/frontend/             index.html, app.js, style.css - GitHub Pages site
/lambda/
  handler.py           entry point: request validation, orchestration
  ics_fetch.py         server-side ICS fetch
  ics_parser.py        Section 4 parsing logic incl. clean_course_name()
  pdf_builder.py        Section 5 PDF generation, generalized from
                       build_ef_planner.py
  requirements.txt
/lambda/tests/
  fixtures/            anonymized sample ICS files (both validated feeds,
                       with any real names/emails/tokens scrubbed before
                       committing - do not commit the real feed URLs or
                       raw files fetched during this validation session)
  test_parser.py       unit tests against fixtures, asserting Section 3
                       findings hold (bell schedule extraction, A/B
                       detection, name cleaning against the 22 known
                       sample strings)
/infra/                minimal IaC (SAM/CDK/Terraform - pick one) for the
                       API Gateway + Lambda + IAM role, no other resources
```

## 10. Open Questions / Not Yet Verified

- **7th and 8th grade feeds have not been examined.** Everything in §3 is
  confirmed only across two 6th-grade students. Before telling other
  parents "this works for your kid too," get at least one 7th-grade and
  one 8th-grade feed and re-run the same comparison (bell schedule, A/B
  markers, name patterns). Do not assume — the parsing logic in §4 is
  written to be grade-agnostic already (it discovers structure from the
  feed rather than hardcoding it), so it should work, but this needs an
  actual test, not an assumption.
- Whether the middle-school division tag is always `"BRMS"` on all-day
  marker events, or whether it varies — don't hardcode `"BRMS"` as a
  string to match on; match on the day-name prefix (`"Monday"`,
  `"Wednesday A"`, etc.) instead and treat the parenthetical suffix as
  informational only.
- Whether `student_name` / `grade` should be parsed out of the feed
  automatically (some ICS feeds embed a calendar name/owner) rather than
  requiring the parent to type it — worth a quick check against both
  fixture files during implementation.

## 11. Rollout Plan

1. Get a 7th and/or 8th grade feed, re-validate §3 against it.
2. Implement `/lambda` per §4/§5, with unit tests against the fixture
   files (§9) asserting the specific findings in §3 (not just "it runs").
3. Implement `/frontend`, deploy to GitHub Pages.
4. Deploy Lambda + API Gateway per §6, lock CORS to the Pages origin,
   verify §7's logging requirement against real CloudWatch output.
5. Smoke test end-to-end with Kaden's real URL and the classmate's real
   URL, confirm both PDFs render correctly and match the previously
   approved layout.
6. Share the repo link with the parent circle, pointing to the README's
   privacy explanation.