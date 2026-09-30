# Frontend scope and appearance

The assignment requires a backend. The user additionally requested a polished frontend. The patient UI is now implemented as a Django-served single-page interface at `/`.

## Approach

Use Django-rendered templates, reusable CSS components, and a small JavaScript module calling the same REST APIs. Serve frontend and API from one origin to simplify deployment. API business rules remain authoritative. Django admin is for catalogue administration, not the patient interface.

Authentication transport for this iteration: access and refresh tokens are held only in JavaScript memory for the open page session. Tokens are not persisted in localStorage. A later production hardening pass can move refresh tokens to HttpOnly Secure cookies with CSRF/origin checks.

## Screens

1. Welcome / diagnostic centres: searchable catalogue, centre locations, test names, transparent INR pricing.
2. Signup and login: labelled forms, helpful validation, clear pending and failure states.
3. Test selection and booking: offering summary, local appointment input, timezone label, amount, confirmation step.
4. Mock checkout: prominently labelled simulated payment; explicit success/failure controls for evaluation.
5. My bookings: appointment, centre, test, amount, status, permitted actions, booking details.

## Visual direction

Calm healthcare interface: warm off-white backgrounds, deep teal primary actions, restrained mint accents, dark readable text, generous spacing, consistent typography, subtle borders. Use status text and icons alongside colour. Avoid decorative clutter and unsupported medical claims. Final colours and assets remain adjustable when designing real screens.

## Acceptance criteria

- Responsive at 360px mobile, tablet, and desktop widths with no horizontal overflow.
- Semantic HTML, visible keyboard focus, labelled inputs, accessible error messages, sufficient contrast, and keyboard-operable controls.
- Consistent typography, spacing, buttons, forms, cards, and navigation across every screen.
- Loading, empty, success, failure, session-expired, and unauthorized states designed explicitly.
- Prevent accidental duplicate submissions while retaining backend idempotency protection.
- Show actual API data and server errors. Confirm price/status changes using returned server values.
- Run the page at http://127.0.0.1:8000/ and test signup -> browse -> book -> pay -> view journey.
