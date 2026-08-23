# Pine Crest Weekly Planner Generator

A small web tool for Pine Crest middle-school families. Paste your kid's
Blackbaud/Podium ICS calendar feed URL, click Generate, and download a
printable executive-functioning focused weekly planner PDF customized to
their actual schedule.

No accounts. No install. No data stored. One field, one button, one download.

## Privacy & Security

**This is a hard requirement, not a nice-to-have:**

- Your ICS URL is **never logged, stored, or retained** anywhere — not in
  application logs, not in cloud service logs, not in a database.
- Schedule data exists **only in memory** for the few seconds it takes to
  generate the PDF, then is discarded.
- The Lambda function has **no CloudWatch Logs permissions** — it physically
  cannot write logs that could contain your data.
- API Gateway access logging is **explicitly disabled** for request/response
  bodies.
- No analytics, tracking, cookies, or third-party scripts.

The repo is public so you can verify every one of these claims by reading
the actual code.

## Project Structure

```
frontend/           Static site (GitHub Pages) — HTML/CSS/JS
lambda/             AWS Lambda function — ICS parsing + PDF generation
  ics_parser.py     Parse Blackbaud ICS feeds into structured schedules
  pdf_builder.py    Generate the 8-page planner PDF (reportlab)
  ics_fetch.py      Server-side ICS URL fetch (CORS workaround)
  handler.py        Lambda entry point — validation, orchestration
  tests/            pytest test suite with synthetic fixtures
infra/              Terraform — API Gateway + Lambda + IAM
.github/workflows/  CI (lint/test) + CD (deploy infra + Pages)
```

## Tech Stack

- **Frontend:** Vanilla HTML/CSS/JS on GitHub Pages
- **Backend:** Python 3.14 on AWS Lambda
- **Infra:** Terraform, deployed via GitHub Actions
- **PDF:** reportlab (Helvetica base14, no external fonts)
- **ICS Parsing:** icalendar library
- **Toolchain:** uv, ruff, pytest, pre-commit, prettier

## Development Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- Node.js (for prettier, via pre-commit)

### Getting Started

```bash
# Clone and enter the project
git clone https://github.com/YOUR_ORG/school-planner.git
cd school-planner

# Install Python dependencies
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run pytest

# Run linter
uv run ruff check .
uv run ruff format --check .
```

### Local Testing

The Lambda handler can be tested locally by importing it directly:

```python
from lambda.handler import handler

event = {
    "body": '{"ics_url": "https://...", "student_name": "Test", "grade": 6}',
    "isBase64Encoded": False
}
response = handler(event, None)
# response["body"] is base64-encoded PDF bytes
```

## Deployment

Deployment is automated via GitHub Actions on push to `main`:

1. **CI** runs on all PRs: ruff lint/format, prettier, pytest, terraform validate
2. **Deploy** runs on merge to main: packages Lambda, applies Terraform, deploys frontend to Pages
3. **Releases** are created when you push a `v*` tag

### Required GitHub Secrets

| Secret                | Purpose                              |
| --------------------- | ------------------------------------ |
| `AWS_DEPLOY_ROLE_ARN` | IAM role ARN for OIDC-based AWS auth |
| `TF_STATE_BUCKET`     | S3 bucket for Terraform remote state |

### Manual Deploy

```bash
# Package Lambda
cd lambda
uv pip install --target package -r requirements.txt
cp *.py package/
cd package && zip -r ../package.zip . && cd ..

# Apply Terraform
cd ../infra
terraform init -backend-config="bucket=YOUR_BUCKET" \
               -backend-config="key=school-planner/terraform.tfstate" \
               -backend-config="region=us-east-1"
terraform plan
terraform apply
```

## Disclaimer

This is a community project built by Pine Crest parents for fun. It is **not
affiliated with, endorsed by, or supported by Pine Crest School** or Blackbaud.

**No warranty. No service level guarantee.** The tool is provided "as is"
without warranty of any kind. It may break, go offline, or produce incorrect
output at any time.

## License

MIT
