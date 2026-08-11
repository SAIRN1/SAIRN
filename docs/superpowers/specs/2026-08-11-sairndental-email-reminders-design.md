# SAIRNdental — Automated Email Reminders Design

**Status:** Design approved 2026-08-11. Implementation plan at
`docs/superpowers/plans/2026-08-11-sairndental-email-reminders.md`.
Tasks 1-5 built, tested, and pushed to `main`
(`5f0f6a8`, `7bfd71b`, `c5eb83b`, `d079e74`, `e92a08f`) — Practice Info
settings fields, "no email on file" badge, the email-copy module (7
tests), the window-selection module (14 boundary/idempotency tests),
`send-reminder.js` (4 auth-gate tests), and the hourly Vercel Cron
entry. Live-verified: `sairndental.html`'s two UI changes are live
byte-identical to the pushed file; `send-reminder.js` is deployed and
reachable, and correctly fails closed (500) rather than accepting an
unauthenticated request, since `CRON_SECRET` is not yet set in Vercel.
**Not yet done:** `CRON_SECRET` and `RESEND_FROM_ADDRESS` env vars,
and every live-data step in Task 6 (real Resend send,
delivery-confirmed window-boundary check, idempotency-of-a-real-send,
live missing-email/failed-send checks against production data) —
blocked on Resend's sending-domain DNS verification, currently
propagating after a Namecheap Custom DNS → BasicDNS switch (per
Namecheap's own documentation, up to 24-48h; confirmed a genuine
external wait, not a bug).

Concrete technical design for the top-level spec's §5 (real automated
no-show reminders via email, not SMS — genuinely new platform
infrastructure, confirmed via a full-platform search: no email/SMS
send capability, no cron config, no provider keys existed anywhere on
SAIRN before this feature). Seven real design questions resolved
directly with Michael before writing this, not assumed — recorded
below with the reasoning, not just the outcome.

## 0. Design questions, resolved

**Email provider — Resend.** Chosen over SendGrid (heavier API/config
surface, not needed here) and Postmark (no free tier). Requires a
manual step outside what I can do myself: Michael creates the account,
verifies a sending domain, and sets `RESEND_API_KEY` in Vercel's
project environment variables.

**Reminder count/timing — two reminders per appointment: 48h before
and 2h before.** Chosen over a single 24h reminder (simpler, but
weaker no-show reduction) and a per-practice-configurable offset
(most flexible, but a real settings UI + validation surface not
scoped for this pass). Means `reminder_sent_at` can't be a single
timestamp — needs two independent idempotency keys (§2).

**Cron frequency — hourly.** The 2h-before window is too tight for a
daily cron (an appointment could cross from >2h out to already-past
between two daily runs, never getting a 2h reminder at all). Confirmed
feasible: the SAIRN Vercel project (`sairn`, team `sairn1s-projects`)
is on a **Pro** plan — Hobby's once-per-day cron cap would have forced
a redesign of the 2h reminder; Pro removes that constraint.

**Sender identity — one shared SAIRN-domain address for every
practice** (e.g. `reminders@sairndental.app`), not a per-practice
custom domain. This app is multi-tenant; per-practice domain
verification (DNS records, a real setup flow per practice) is a
significant scope increase for a v1 and isn't needed — the practice's
own name appears in the subject/body, not the From address.

**Email content — informational only, no cancel/reschedule link.**
States date/time/provider/procedure and the practice's phone number to
call for changes. A one-click cancel link was considered and rejected
for this pass: it would require a new unauthenticated write endpoint
with the same security posture as the public booking page (rate
limiting, no data leakage) — a second public attack surface, real
added scope not requested.

**Practice info source — new Settings section, not hardcoded.**
`dnt_settings` currently has no practice identity fields at all
(`booking_slug`, `timezone`, `publicly_bookable_procedure_type_ids`
only). Hardcoding one practice's name/phone/address directly in the
email template was considered and rejected: it breaks the moment a
second practice licenses the app, and this platform is already
multi-tenant by design (license-key auth). `practice_address` doubles
as the physical-address line CAN-SPAM requires in the footer of any
commercial email, satisfying that requirement as a side effect of
data already being collected for the email body.

**Missing patient email — skip silently in the cron, surface visibly
in the UI.** Not every patient has an email on file (optional field).
A cron with nothing to send to just skips that appointment — but per
this platform's no-silent-failure standard, the Appointments panel
shows a visible "no email on file" flag on that appointment so staff
notice and can call the patient directly, rather than a no-show
looking identical regardless of cause.

## 1. Architecture

- **`api/sairndental/send-reminder.js`** — new endpoint, invoked only
  by Vercel Cron via a shared-secret header check (`CRON_SECRET` env
  var compared against an `Authorization` header Vercel Cron sends) —
  not a publicly callable route. Per run: queries `dnt_appointments`
  for `Confirmed` appointments needing either reminder (§2), calls
  Resend's API once per due appointment, stamps the corresponding
  `reminder_*_sent_at` field only on confirmed success, logs any
  failure with the appointment ID and error detail (never silently
  dropped, per `sairn-silent-failure-sweep`).
- **`vercel.json`** — new `crons` entry: `{"path":
  "/api/sairndental/send-reminder", "schedule": "0 * * * *"}` (hourly,
  top of every hour). First cron config in this repo — confirmed via
  `vercel_config_check.py` before push that this doesn't collide with
  the existing `buildCommand` length constraint.

## 2. Data model additions

- `dnt_appointments` — two new nullable timestamp fields:
  `reminder_48h_sent_at`, `reminder_2h_sent_at`. Independent
  idempotency keys — each reminder stage is stamped only once, only on
  a confirmed successful send, so a failed attempt is naturally
  retried on the next hourly run while still inside that reminder's
  window (§3 defines the window bounds).
- `dnt_settings` — three new fields: `practice_name`, `practice_phone`,
  `practice_address`. Populated via a new Settings form section,
  reused by every reminder email this practice's appointments trigger.

## 3. Reminder window logic

Per hourly cron run, for every appointment where `status ===
'Confirmed'`:

- **48h reminder:** if `now` falls within `[start_time - 48h,
  start_time - 47h)` and `reminder_48h_sent_at` is null → send, stamp
  with the current timestamp.
- **2h reminder:** if `now` falls within `[start_time - 2h, start_time
  - 1h)` and `reminder_2h_sent_at` is null → send, stamp with the
  current timestamp.

One-hour-wide windows matched to the hourly cron cadence — wide enough
that an hourly run can't skip an appointment between two runs, narrow
enough that neither reminder fires more than once per stage. An
appointment booked with less than 48h (or less than 2h) of lead time
simply never enters that reminder's window and gets fewer reminders —
stated explicitly as accepted behavior, not silently unhandled: a
same-day booking correctly gets zero reminders rather than an
error or a backdated one.

Only `Confirmed` appointments qualify — `Pending` appointments haven't
been reviewed by staff yet (per the existing booking-engine design's
"never auto-confirm" decision) and shouldn't generate patient-facing
communication before that review happens.

## 4. Failure handling

A failed Resend API call (network error, non-2xx response, invalid
recipient) is caught and logged with the appointment ID, reminder
stage, and error detail — `reminder_*_sent_at` stays null, so the next
hourly run retries it automatically as long as the appointment is
still inside that reminder's window. A send that never succeeds within
its window (e.g. Resend down for hours) is logged but not retried past
the window — matches the platform's existing "honest disclosure, no
silent success" discipline (`sairn-silent-failure-sweep`) rather than
inventing a queueing/backoff system not requested here.

## 5. Internal-app additions (staff side)

- **Settings panel** — new Practice Info section: `practice_name`,
  `practice_phone`, `practice_address` fields, saved via the existing
  `dnt_settings` write path.
- **Appointments panel** — existing panel gains a visible "no email on
  file" badge on any listed appointment whose patient has no `email`
  value, so a skipped reminder is never silently invisible to staff.

## 6. Non-goals (explicit scope cuts, this pass)

- No cancel/reschedule link in the email (§0).
- No per-practice custom sending domain (§0).
- No SMS — explicitly out of scope per the original request.
- No configurable reminder offsets — 48h/2h are fixed for this pass,
  not a per-practice setting.
- No reminder-effectiveness reporting (e.g. "did this reminder
  correlate with fewer no-shows") — this feature sends reminders; a
  no-show-rate analytics feature is a separate, unrequested addition.

## 7. Testing

- Window-boundary cases for both reminder stages: appointment just
  inside the window (sends), just outside on either edge (doesn't
  send), exactly at a boundary (defined behavior, not flaky).
- Idempotency: a second cron run within the same window does not
  re-send (the stamped `reminder_*_sent_at` blocks it).
- Missing-email path: appointment's patient has no `email` → cron
  skips with no send attempt, Appointments panel shows the "no email
  on file" badge.
- Failed-send logging: a simulated Resend failure is logged with
  appointment ID + stage + error, `reminder_*_sent_at` stays null, and
  a subsequent run within the window retries it.
- Real end-to-end send: once `RESEND_API_KEY` is live, a genuine test
  call through Resend's API confirming actual delivery (or a real,
  identifiable API error) — not assumed from a successful deploy.
- Standard structural checks + Push Protocol on every file touched.

## 8. Open items for the next pass (not resolved by this spec)

- Exact email subject line and body copy — will be drafted in the
  implementation plan; Michael can edit before it ships to a real
  practice.
- CAN-SPAM compliance beyond the physical-address footer (opt-out
  mechanism applicability to transactional-vs-commercial
  classification) — flagged, not fully researched here; worth a real
  pass before this reaches a real practice, same category as the
  fee-schedule spec's own flagged HIPAA open item.
