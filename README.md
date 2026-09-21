# Spend Tracker

A Flask-based personal spending tracker that lets you record expenses, filter transactions, and analyze month-over-month spending by total, category, and payment method.

## Features

- Add expenses with validation
- SQLite persistence
- Category and payment method validation
- Expense filtering and pagination
- Monthly dashboard (`GET /dashboard`)
- Month-over-month analytics (`GET /summary`)
- Category, payment-method, and category × payment-method analysis
- Deterministic backend insights
- Automated API tests (pytest)
- Responsive HTML/CSS/JavaScript UI with Chart.js

Authentication and public deployment are **not** part of this MVP.

## Tech Stack

- Python
- Flask
- SQLAlchemy
- SQLite
- Pydantic
- Pytest
- HTML
- Tailwind CSS (CDN)
- Vanilla JavaScript (ES modules)
- Chart.js

## Project Structure

```text
app/
  __init__.py          # Flask app factory, route registration, static serving
  main.py              # Development entrypoint
  config.py            # Settings (DATABASE_URL)
  database.py          # SQLAlchemy engine/session
  models.py            # Expense model
  schemas.py           # Expense request/response schemas
  constants.py         # Fixed categories and payment methods
  dashboard_schemas.py # Dashboard response models
  analytics_schemas.py # Analytics response models
  http.py              # Standard API error helpers
  routes/              # Flask blueprints (expenses, dashboard, analytics)
  services/            # Business logic (dashboard, analytics, change engine)
  static/              # Frontend SPA (index.html, JS, CSS)
tests/                 # Pytest suite
```

`stitch_spend_tracker_ui/` (if present locally) is optional design reference only and is not required at runtime.

## Setup

```bash
git clone https://github.com/mehtameet2802/assignment-infinity-consultants.git
cd assignment-infinity-consultants
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
npm ci   # locked jsdom deps for frontend regression tests (requires Node.js)
```

Optional: copy `.env.example` to `.env` to customize `DATABASE_URL` (defaults to `./spend_tracker.db`).

## Run

```bash
source .venv/bin/activate
FLASK_APP='app:create_app()' flask run
```

Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/) for the UI.

Health check: `GET /health` → `{"status":"ok"}`

The SQLite database file is created automatically on first run.

## Tests

```bash
npm ci    # once per clone, if not already run during setup
pytest
```

Python tests cover the API, analytics, and dashboard. A small jsdom suite (`tests/js/frontend_regression.test.mjs`) runs via pytest when Node.js is installed. Use `npm ci` so installs match `package-lock.json`; if `node_modules/` is missing, pytest may attempt `npm install` instead (network required).

## API Overview

### `POST /expenses`

Create an expense. Returns `201` with the created record.

### `GET /expenses`

List expenses with optional filters:

- `category`
- `payment_method`
- `start_date`, `end_date` (`YYYY-MM-DD`)
- `limit` (default `20`, max `100`)
- `offset` (default `0`)

Sorted by `date DESC`, then `id DESC`.

### `GET /dashboard?month=YYYY-MM`

Single-month dashboard: totals, month-over-month change, breakdowns, top category/method (including ties), and 5 recent expenses.

### `GET /summary?start_month=YYYY-MM&end_month=YYYY-MM`

Inclusive multi-month analytics: overall totals, category series, payment-method series, active category × payment-method combinations, and deterministic insights.

## Expense Fields

| Field | Description |
|-------|-------------|
| `amount` | Positive decimal |
| `category` | One of the fixed categories below |
| `payment_method` | One of the fixed methods below |
| `note` | Optional, max 500 characters |
| `date` | Expense date (`YYYY-MM-DD`), not in the future |

**Categories:** Food & Dining, Groceries, Transport, Shopping, Bills & Utilities, Entertainment, Health, Travel, Education, Other

**Payment methods:** Credit Card, Debit Card, UPI, Cash

## Validation Rules

- `amount` must be greater than zero
- Category and payment method must match the fixed lists exactly
- Future expense dates are rejected
- Invalid month formats and `start_month > end_month` (analytics) or `start_date > end_date` (expenses) return structured errors

## Pagination

- Default `limit`: 20
- Maximum `limit`: 100
- Default `offset`: 0
- Response includes `total`, `limit`, `offset`, and `items`

## Month-over-Month Logic

Centralized change states:

| `change_type` | Meaning |
|---------------|---------|
| `increase` | Previous > 0 and current > previous |
| `decrease` | Previous > 0 and current < previous (includes drop to zero, −100%) |
| `no_change` | Previous equals current |
| `new` | Previous is 0, current > 0, and no historical spend before the comparison period |
| `resumed` | Previous is 0, current > 0, and historical spend existed before the comparison period |
| `not_applicable` | No comparison (e.g. first month in an analytics range) |

**Zero denominator:** When previous amount is 0 and current is positive, `change_percentage` is `null` (undefined percentage). The UI shows labels such as **New** or **Resumed** instead of a percentage.

## Analytics Behavior

- `start_month` and `end_month` are inclusive; every month in the range appears (including zero-spend months)
- All 10 categories and all 4 payment methods are returned in their series
- Category × payment-method entries are returned only for **active** combinations (positive spend in at least one month in the range), with all months filled per combination
- The first month in the selected range does not compare against a month outside the range (`not_applicable`)

## Error Format

```json
{
  "error": "validation_error",
  "details": [
    {
      "field": "amount",
      "message": "Input should be greater than 0"
    }
  ]
}
```

Other codes include `invalid_json`, `invalid_date_range`, and `invalid_month_range`.

## Design Decisions

1. **Flask** — Simple, explicit control over routes and JSON responses for a take-home API.
2. **Pydantic with Flask** — Centralized request validation without adopting a heavier API framework.
3. **SQLite** — Lightweight local persistence; straightforward to swap for PostgreSQL later.
4. **Decimal / NUMERIC** — Avoids floating-point money errors.
5. **Application factory** — Clean configuration and isolated test databases.
6. **Blueprints** — Domain-separated routes (expenses, dashboard, analytics).
7. **Service layer** — Aggregations and analytics live outside route handlers.
8. **Central change engine** — One implementation of month-over-month rules.
9. **Deterministic insights** — Testable, rule-based insight text (no LLM).
10. **Active combinations only** — Keeps analytics payloads smaller than a full 40-combination matrix of mostly zeros.

## Assumptions

- Single-user MVP (no auth)
- INR display in the UI
- Fixed categories and payment methods in v1
- No edit/delete expense endpoints in v1
- Calendar-month boundaries for dashboard and analytics

## What I Would Improve With More Time

- Authentication and per-user data isolation
- PostgreSQL and Alembic migrations
- Edit/delete expenses
- Configurable categories and payment methods
- Docker image and CI pipeline
- Structured logging and observability
- Public deployment (e.g. container + managed DB)
- API rate limiting where appropriate

## AI Usage

I used ChatGPT and Cursor to help plan the API structure, generate implementation scaffolding, and review edge cases and tests. I reviewed and adapted the generated code, including validation, pagination, database queries, month-over-month logic, and frontend integration, and verified the final behavior with automated tests and manual browser testing.
