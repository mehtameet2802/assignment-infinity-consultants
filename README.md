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
- API-key authentication (SQLite-backed keys, browser unlock flow, rotation with grace period)

Public deployment is optional and not included by default.

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

Create the local environment file:

```bash
cp .env.example .env
```

On Windows Command Prompt, use `copy .env.example .env`. The `.env` file is ignored
by Git and must not be committed because it contains authentication secrets. Complete
the authentication setup below before starting the application with authentication
enabled.

### Quick evaluator setup (core assignment)

API-key authentication is an optional bonus feature and is not required to review
the core expense and summary functionality. For the shortest first-time setup, set
the following value in `.env`:

```dotenv
AUTH_ENABLED=false
```

Then start the application without creating an administrator password or initial
API key:

```bash
flask --app 'app:create_app()' run
```

The expense, dashboard, analytics, and UI features will be available immediately at
[http://127.0.0.1:5000/](http://127.0.0.1:5000/). Enable authentication later by
following the optional authentication setup below.

## Run

```bash
source .venv/bin/activate
FLASK_APP='app:create_app()' flask run
```

Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/) for the UI.

Health check: `GET /health` → `{"status":"ok"}`

The SQLite database file is created automatically on first run.

## Authentication

Single-user API-key protection for expense, dashboard, and analytics JSON endpoints. Keys are stored in SQLite as **HMAC-SHA256** hashes using `API_KEY_PEPPER`; raw keys are never written to the database or logs. The application **never rewrites `.env`** at runtime.

### Environment variables

| Variable | Purpose |
|----------|---------|
| `AUTH_ENABLED` | `true` to require API keys on protected routes |
| `API_KEY_PEPPER` | High-entropy secret for HMAC hashing before storage |
| `ADMIN_PASSWORD_HASH` | Werkzeug hash used to authorize key rotation |

### Configure `.env` and create the first key

Run these commands from the repository root with the virtual environment activated.

1. Generate a high-entropy API-key pepper:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the entire output. Open `.env` in a text editor and replace the
`API_KEY_PEPPER` placeholder. At this stage, `.env` should look like this:

```dotenv
DATABASE_URL=sqlite:///./spend_tracker.db
AUTH_ENABLED=true
API_KEY_PEPPER=PASTE_THE_GENERATED_PEPPER_HERE
ADMIN_PASSWORD_HASH=replace-with-werkzeug-password-hash
```

`API_KEY_PEPPER` is a server secret, not the API key entered in the browser. Keep it
stable and private. Changing it later makes every API key already stored in the
database unusable.

2. Generate the administrator password hash:

```bash
flask --app 'app:create_app()' auth hash-password
```

Enter the administrator password twice when prompted. Copy the complete generated
hash and replace the `ADMIN_PASSWORD_HASH` placeholder in `.env`. Store only the
generated hash in `.env`, never the plain-text administrator password.

The completed file has this shape (the values below are examples, not usable
credentials):

```dotenv
DATABASE_URL=sqlite:///./spend_tracker.db
AUTH_ENABLED=true
API_KEY_PEPPER=your-generated-random-pepper
ADMIN_PASSWORD_HASH=scrypt:example-generated-hash
```

3. Create the initial API key:

```bash
flask --app 'app:create_app()' auth create-initial-key
```

The command creates `spend_tracker.db` if necessary and prints a raw key beginning
with `st_`. Copy and store that key immediately; it is displayed only once and
cannot be recovered from the database. If the command reports that a usable key
already exists, use that existing raw key or follow the recovery guidance below
instead of resetting the database.

4. Start the application:

```bash
flask --app 'app:create_app()' run
```

Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/) and enter the generated
`st_...` key on the unlock screen. To confirm the key from a terminal:

```bash
curl \
  -H "X-API-Key: YOUR_ST_KEY" \
  "http://127.0.0.1:5000/dashboard?month=2026-09"
```

For local development without authentication, set `AUTH_ENABLED=false`; the pepper,
administrator password hash, and initial-key step are then unnecessary.

### Browser unlock

1. Open the app; enter the API key on the unlock screen.
2. The key is stored in `sessionStorage` as `spend_tracker_api_key` for the tab session.
3. All protected API calls send `X-API-Key`.
4. Use **Security** (`/settings/security`) to view prefix/metadata, rotate the key, or **Lock** (clears session only; does not revoke the server key).

### Rotation and grace period

`POST /auth/api-key/rotate` requires the current API key and administrator password. The response includes the **new raw key once**. The previous key remains valid for **five minutes** (`previous_key_valid_until`), then expires automatically. If the response is interrupted, retry rotation with the old key during the grace window.

### Example request

Use HTTPS outside local development.

```bash
curl \
  -H "X-API-Key: YOUR_KEY" \
  "http://127.0.0.1:5000/dashboard?month=2026-09"
```

### Recovery

If a key is lost after the grace window, generate a new initial key only when no usable key exists (`flask auth create-initial-key`), or insert a new key through a controlled admin process on the server. There is no API to recover a lost raw key.

Set `AUTH_ENABLED=false` for local development without keys (default in tests).

## Tests

```bash
npm ci    # once per clone, if not already run during setup
pytest
```

Python tests cover the API, analytics, dashboard, and authentication. jsdom suites (`tests/js/frontend_regression.test.mjs`, `tests/js/auth_regression.test.mjs`) run via pytest when Node.js is installed. Use `npm ci` so installs match `package-lock.json`; if `node_modules/` is missing, pytest may attempt `npm install` instead (network required).

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

The endpoint requires an explicit bounded month range even though the original task
does not prescribe summary query parameters. This keeps aggregation work predictable,
makes month-over-month comparisons unambiguous, includes zero-spend months correctly,
and lets the same endpoint support both short comparisons and longer trend analysis.

### Authentication (when `AUTH_ENABLED=true`)

Send `X-API-Key` on protected routes. Public: `GET /health`, SPA HTML routes (`/`, `/expenses` with `Accept: text/html`, `/analytics`, `/settings/security`), and `/static/*`.

- `GET /auth/verify` — validate key; returns prefix metadata
- `GET /auth/api-key` — key metadata (no hash, no full key)
- `POST /auth/api-key/rotate` — body `{"password":"..."}`; returns new raw key once

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
11. **Bounded summary ranges** — Required inclusive `start_month` and `end_month` values make query cost and comparison semantics explicit instead of relying on an arbitrary server default.

## Assumptions

- Single-user MVP with one active API-key set at a time
- INR display in the UI
- Fixed categories and payment methods in v1
- No edit/delete expense endpoints in v1
- Calendar-month boundaries for dashboard and analytics

## What I Would Improve With More Time

- Multi-user accounts and per-user data isolation
- PostgreSQL and Alembic migrations
- Edit/delete expenses
- Configurable categories and payment methods
- Docker image and CI pipeline
- Structured logging and observability
- Public deployment (e.g. container + managed DB)
- API rate limiting where appropriate

## AI Usage

I used ChatGPT and Cursor to help plan the API structure, generate implementation scaffolding, and review edge cases and tests. I reviewed and adapted the generated code, including validation, pagination, database queries, month-over-month logic, and frontend integration, and verified the final behavior with automated tests and manual browser testing.
