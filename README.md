# EVE Healthcare

Diagnostic test booking and simulated payment service built with Django REST Framework and PostgreSQL.

## Current progress

Steps 1 through 8 are implemented and verified locally:

- Project scaffold, dependency pinning, environment-based settings, and GET /api/health/.
- Custom email-based user model with signup, JWT login, refresh, and /api/auth/me/.
- Staff-controlled catalogue models and APIs for centres, tests, and centre-specific offerings.
- Demo catalogue seed command.
- Authenticated booking create/list/detail flow with immutable price snapshots and idempotent cancellation behavior.
- Simulated payment endpoint, provider webhook endpoint, idempotency records, and payment-driven booking state transitions.
- Automated tests for auth, bookings, payment idempotency, webhook replay/conflict handling, and invalid edge cases.
- Patient-facing frontend at `/` with signup/login, catalogue search, booking, mock checkout, and booking history.
- Docker and Docker Compose packaging for evaluator setup.

## Local setup (PowerShell)

Requires Python 3.14 (the validated interpreter) and PostgreSQL.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set DJANGO_SECRET_KEY in .env to a random value. Generate one with:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Configure database credentials and keep .env private.

```powershell
.\scripts\start_local_postgres.ps1
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_catalogue
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Open http://127.0.0.1:8000/api/health/ for {"status":"ok","service":"eve-healthcare"}.
Open http://127.0.0.1:8000/ for the patient-facing UI.

This workspace uses an ignored local PostgreSQL data directory at .postgres-data/ on port 55432. The helper script creates and starts that database without touching any PostgreSQL service already installed on port 5432.

## Docker setup

If Docker is available, the project can run with one command:

```powershell
docker compose up --build
```

The compose stack runs PostgreSQL 18, applies migrations, seeds the catalogue, and starts Django on http://127.0.0.1:8000/. The database is exposed on local port 55433 to avoid colliding with an existing PostgreSQL service.

## API endpoints now available

| Method | Endpoint | Auth | Purpose |
| --- | --- | --- | --- |
| GET | /api/health/ | Public | Application liveness check |
| GET | / | Public | Patient-facing frontend |
| POST | /api/auth/signup/ | Public | Create a normal user account |
| POST | /api/auth/login/ | Public | Get JWT access and refresh tokens |
| POST | /api/auth/refresh/ | Public | Refresh an access token |
| GET | /api/auth/me/ | JWT | Inspect current user |
| GET | /api/centres/ | Public | List active diagnostic centres |
| POST/PATCH/DELETE | /api/centres/ | Staff JWT | Manage centres |
| GET | /api/centres/{id}/tests/ | Public | List active tests and prices at a centre |
| GET | /api/tests/ | Public | List active diagnostic tests |
| POST/PATCH/DELETE | /api/tests/ | Staff JWT | Manage test definitions |
| GET | /api/offerings/ | Public | List centre-test price offerings |
| POST/PATCH/DELETE | /api/offerings/ | Staff JWT | Manage centre-test pricing |
| GET | /api/bookings/ | JWT | List the signed-in user's bookings |
| POST | /api/bookings/ | JWT | Create a booking from offering_id and appointment_at |
| GET | /api/bookings/{id}/ | JWT | Retrieve own booking |
| POST | /api/bookings/{id}/cancel/ | JWT | Cancel own pending or failed booking |
| POST | /api/payments/ | JWT + Idempotency-Key | Simulate payment success or failure for own pending booking |
| GET | /api/payments/{id}/ | JWT | Retrieve own payment attempt |
| POST | /api/payments/webhook/ | X-Webhook-Secret | Process provider payment event idempotently |

## Example requests

Signup:

```json
{
  "email": "patient@example.com",
  "first_name": "Asha",
  "last_name": "Mehta",
  "password": "StrongPass123!"
}
```

Create booking:

```json
{
  "offering_id": 1,
  "appointment_at": "2026-10-05T10:30:00+05:30"
}
```

Booking responses include the centre/test names and amount snapshot captured at booking time, so later catalogue price edits do not change existing bookings.

Simulate payment:

```json
{
  "booking_id": 1,
  "simulated_outcome": "SUCCESS"
}
```

Send the payment request with an `Idempotency-Key` header. Reusing the same key with the same body returns the original payment response; reusing it with a changed body returns `409`.

Webhook payload:

```json
{
  "event_id": "evt_001",
  "provider_reference": "9b4c40ad-36f4-4d83-961a-7c45975b0110",
  "outcome": "SUCCESS",
  "amount": "499.00",
  "currency": "INR"
}
```

Send webhook calls with `X-Webhook-Secret` matching `PAYMENT_WEBHOOK_SECRET`.

## Tests

Run the local PostgreSQL helper first, then run Django tests:

```powershell
.\scripts\start_local_postgres.ps1
.\.venv\Scripts\python.exe manage.py test --noinput
```

Current suite: 16 tests covering signup/login/current user, booking validation, owner-only booking access, booking cancellation rules, payment success/failure transitions, payment idempotency key replay/conflict handling, webhook replay, changed-event conflicts, conflicting terminal events, invalid webhook secret, unknown payment references, amount mismatch rollback, and homepage rendering for the patient UI.

## Schema summary

| Model | Purpose | Key constraints |
| --- | --- | --- |
| User | Email-based app user | Unique email, Django password hashing |
| DiagnosticCentre | Diagnostic centre | Unique name/city/address, soft deactivation |
| DiagnosticTest | Test definition | Unique test code, soft deactivation |
| CentreTest | Centre-specific test price | Unique centre/test pair, non-negative price |
| Booking | User booking with immutable price snapshot | Owner-scoped access, status lifecycle, protected catalogue references |
| PaymentAttempt | One simulated payment per booking | One-to-one booking, unique provider reference, user-scoped idempotency key |
| WebhookEvent | Provider event audit/idempotency record | Unique provider event id and payload hash validation |

## Assumptions

- Users book tests for themselves; separate patient records are outside this version.
- Slot capacity, rescheduling, refunds, real payment gateway integration, and notifications are outside scope.
- Catalogue records are deactivated instead of hard-deleted once referenced.
- The mock payment endpoint intentionally accepts `SUCCESS` or `FAILED` to demonstrate assignment scenarios.
- Failed bookings require creating a new booking for another payment attempt.
- The frontend stores tokens only in page memory for this demo; production refresh tokens should move to HttpOnly Secure cookies.

## Future improvements

- Add production-grade refresh token cookies, CSRF/origin checks, logout, and refresh revocation.
- Add OpenAPI/Swagger documentation.
- Add rate limiting and structured request logging.
- Add slot availability, rescheduling, refunds, notifications, and patient profiles.
- Add PostgreSQL concurrency stress tests beyond the current API/service suite.
- Replace Django development server with a production ASGI/WSGI server for deployment.

## Architecture and decisions

- config/: settings, routing, WSGI/ASGI, health endpoint.
- accounts/: email-based custom user, signup, JWT routes, current-user route, shared permissions.
- catalogue/: centres, tests, centre-specific offerings, staff management, public reads, seed data.
- bookings/: owner-scoped booking APIs, amount snapshots, cancellation state transition.
- payments/: payment attempts, idempotency, mock provider flow, webhook state transitions.
- templates/frontend/ and static/frontend/: patient-facing UI.
- docs/PROJECT_RULES.md: precise business rules, state transitions, and build sequence.
- docs/FRONTEND_PLAN.md: patient UI scope, appearance, and acceptance criteria.

Dependencies are pinned in requirements.txt. Django system checks pass. The local workspace PostgreSQL database was initialized on port 55432, migrations were applied, catalogue seed data was inserted, and the full Django test suite passes. Docker packaging is included for environments with Docker installed.
