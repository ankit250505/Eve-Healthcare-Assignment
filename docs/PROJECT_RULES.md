# EVE Healthcare: agreed implementation baseline

Status: steps 1 through 8 are implemented and verified locally, including Docker packaging files. These are implementation decisions, not additional requirements from the assignment.

## Scope and architecture

A Django REST Framework monolith backed by PostgreSQL. Modules: accounts, catalogue, bookings, payments. Views handle HTTP, serializers validate input, services own business rules and transaction boundaries, models enforce persistent constraints. No real payment gateway. No Redis, Celery, or separate provider service in the initial implementation.

## Accounts and access

- Implement a custom email-based user before the first database migration. Signup normalizes email and uses Django password hashing and validators. Public signup never grants staff permissions.
- Signup, login, token refresh, catalogue reads, and liveness are public. Other user APIs require JWT. Provider webhooks require a separate secret, not a user's JWT.
- Staff manage catalogue records. Users can list, inspect, cancel, or pay only their own bookings. Owner-scoped lookup returns 404 for another user's resource.
- Access tokens expire after 15 minutes; refresh tokens after one day. Logout and refresh revocation are outside initial scope.

## Catalogue and bookings

- CentreTest links a centre to a test with a unique centre/test pair and a non-negative decimal price. Deactivate referenced catalogue entries rather than deleting them.
- Booking identifies its owner from authentication. Client provides an offering ID and a future timezone-aware appointment time. Centre, test, price, owner, and initial status are derived by the server.
- Currency is INR, with two decimal places. A booking stores an immutable amount snapshot; later price changes do not affect it.
- Users book for themselves. Separate patient records, slot capacity, clinical data, scheduling conflicts, rescheduling, and refunds are outside initial scope.
- PENDING -> CONFIRMED on successful payment; PENDING -> FAILED on failed payment. PENDING or FAILED -> CANCELLED on owner cancellation. Repeated cancellation is harmless. CONFIRMED cannot be cancelled in this version.

## Payments and webhooks

- One payment attempt per booking, enforced by database uniqueness. After failure, create a new booking to try again. Payment retries are a documented future improvement.
- POST /api/payments/ accepts booking_id and simulated_outcome (SUCCESS or FAILED). This outcome control is exclusively for the mock demonstration.
- Require an Idempotency-Key scoped to the authenticated user. Same key and normalized input returns the original response; changed input returns 409. Different keys cannot create a second attempt for the booking.
- The mock endpoint generates a provider event and calls the same processing service used by POST /api/payments/webhook/.
- Payment PENDING -> SUCCESS or FAILED. Terminal payment results are immutable. Booking and payment update atomically.
- Provider event IDs are unique. Same ID and payload returns 200 without side effects; same ID with changed content returns 409. Different IDs with the same terminal result are recorded and acknowledged without repeating the state change.
- Conflicting terminal results are recorded as ignored conflicts and acknowledged with 200. Unknown payment reference returns 404. Invalid payload returns 400; invalid provider secret returns 403.
- Verify provider authentication before storing an event. Never log secrets. Store minimal event fields rather than arbitrary sensitive payloads.
- Record events and apply updates in one transaction. Use database constraints for concurrent duplicates. Lock booking before payment consistently, including cancellation, to prevent payment/cancellation races. Recover uniqueness conflicts outside a failed transaction or inside an explicit savepoint.
- An event referring to an existing pending payment may only advance an eligible pending booking. Cancelled bookings remain cancelled; late events are recorded as ignored.

## API conventions

Prefix /api/; trailing slashes. Invalid input: 400; missing/invalid JWT: 401; insufficient role: 403; missing or inaccessible resource: 404; invalid state or idempotency conflict: 409. Money is serialized as a decimal string and times as ISO 8601 with offsets. Lists will be paginated. No endpoint may accept client-selected ownership or status.

## Verification and delivery

Test authentication, role and ownership checks, catalogue validation, price snapshots, future appointments, state transitions, payment request replay, webhook duplicates/conflicts, concurrent processing, cancellation races, and transaction rollback. Run database integrity/concurrency tests against PostgreSQL. README must document reproducible setup, API examples, schema, assumptions, and improvements. Never commit .env or credentials.

## Build sequence

1. Rules and project scaffold.
2. PostgreSQL-backed custom user and domain models before migrations.
3. Authentication and permissions.
4. Catalogue APIs and sample data.
5. Booking APIs and cancellation.
6. Shared payment service, mock endpoint, webhook.
7. Complete integration/concurrency tests and documentation.
8. Patient-facing UI using docs/FRONTEND_PLAN.md, Docker packaging, and clean-install instructions.
