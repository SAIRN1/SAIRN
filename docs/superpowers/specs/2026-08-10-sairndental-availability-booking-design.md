# SAIRNdental — Availability Engine + Self-Scheduling Design

**Status:** Code implemented and pushed 2026-08-10
(`docs/superpowers/plans/2026-08-10-sairndental-availability-booking.md`).
**Not fully live-verified — blocked on the SQL migration, honestly
reported, not glossed over.**

**Confirmed live, real tests, not assumed:**
- `sairndental` and `sairndental-book` both return 200.
- The license key genuinely never appears anywhere in
  `sairndental-book.html`'s served source (grepped the real response —
  zero matches for the key or `dntLicenseKey`) — structural isolation
  confirmed, not just claimed by file separation.
- An unknown/unmigrated slug returns a clean `404 UNKNOWN_SLUG`, not a
  crash or a misleading response.
- Internal-app Booking Settings panel: real slug/timezone/procedure-
  type selection, correct public-link preview, honest "server sync not
  yet enabled" toast (accurate — the migration hasn't run).
- Pending Requests panel: correct empty state.
- **A real production deploy failure was found and fixed during this
  verification pass**, not shipped broken: `vercel.json`'s
  `buildCommand` exceeded Vercel's 256-character schema limit after
  adding the two new app files, the deployment failed
  (`readyState:'ERROR'`), and `sairn.vercel.app` silently kept serving
  the previous successful build in the meantime — caught by checking
  Vercel's own deployment API directly (build logs were empty; the
  real error was in `get_deployment`'s `errorMessage` field), not
  assumed from the monitor's timeout alone. Fixed by replacing the
  ever-growing explicit app-list with a wildcard `cp *.html dist/`
  (confirmed via `git ls-tree` that only real, intended app files are
  tracked at the repo root before making that change) — the root
  cause (a hard character ceiling on a growing string) cannot recur.

**Not yet verifiable — `sql/sairndental_availability_booking_schema.sql`
has not been run** (confirmed live: `dnt_settings` read returns
`"provisioned":false`): the real conflict/double-booking test (the
actual regression test for the `EXCLUDE` constraints), real rate-limit
persistence, a real end-to-end booking creating a genuine `Pending`
appointment, and the Confirm/Reject flow against real synced data all
require this migration first. Re-run
`docs/superpowers/plans/2026-08-10-sairndental-availability-booking.md`
Task 6 Steps 4-9 once it has.

Concrete technical design for the top-level spec's §4 (real recurring
availability, multi-provider conflict prevention, public booking page),
resolved through direct design questions rather than assumed — two real
architectural forks found and settled below that the top-level spec
hadn't specified at the implementation level.

## 0. Two real architectural gaps found during this design pass

**Gap 1 — the public page has no way to identify which practice it's
booking for, without a real security problem.** This platform's whole
auth model treats the license key as a Bearer secret sufficient for
full staff-app access (`api/sd-data.js`'s own header: "holding it
grants access to that shop's data"). A public, unauthenticated booking
page can't carry that key in its URL — anyone who got the link (shared
text, browser history, a scraped page) would get full staff access,
not just booking access. **Resolved: a dedicated, non-secret public
booking slug per practice**, entirely separate from the license key,
mapped server-side to `license_hash`. The license key never appears
anywhere on the public page or in its URL.

**Gap 2 — rate limiting the public write endpoint has no existing
pattern to reuse, confirmed by checking, not assumed.** Every "rate
limit" mention anywhere in this codebase is a documented gap, not an
implementation: `api/sd-data.js`'s own header says "add rate-limiting
... before wide multi-tenant exposure" (not done yet), and
`api/claude.js`'s `demo_limit` counter is explicitly flagged
in-code as "best-effort... does NOT reliably cap usage... across real
traffic" because Vercel serverless functions are stateless across
invocations. **Resolved: a real, persistent, Supabase-backed rate
limiter** (§4) — genuinely new infrastructure, the first real one on
this platform, not a reuse of an existing pattern.

## 1. Data model additions

- `dnt_settings` — one row per practice: `{id:'default',
  booking_slug, timezone, publicly_bookable_procedure_type_ids:
  [...]}`. New resource, same generic jsonb pattern as every other
  `dnt_` resource — but `booking_slug` also needs a **promoted, real,
  indexed column** (not buried in `data` jsonb) so the public
  endpoints can look up `license_hash` by slug efficiently and
  without scanning every practice's blob on every request.
- `dnt_appointments` — **deliberately deviates from this platform's
  usual generic-jsonb-blob pattern.** `provider_id`, `operatory_id`,
  `start_time`, `end_time`, and `status` are promoted to real columns
  (not buried in `data`), specifically because this resource needs a
  real Postgres `EXCLUDE` constraint (§3) to prevent double-booking
  at the database level — the first resource on this platform that
  needs genuine interval-overlap prevention, not just an exact-match
  unique constraint like every prior atomic-write fix
  (`leg_merch_units`'s reservation lock, `sdn_invoices`'s uniqueness
  index) has needed. This is a deliberate, reasoned exception, not
  drift from convention.
- `dnt_booking_rate_limits` — new, real: `{ip_hash, window_start,
  count}`. `ip_hash = sha256(ip + a server-side salt)`, matching this
  platform's existing `license_hash = sha256(license_key)` pattern —
  never store a raw IP address any longer than the rate-limit window
  needs it.

## 2. Public endpoints (new — genuinely unauthenticated, first on this platform)

- `api/sairndental/public-availability.js` — `{slug, provider_id,
  procedure_type_id, date_range}` in, real computed open slots out.
  **Never returns the raw appointments array or any other patient's
  data** — the response is exactly `[{start_time, end_time,
  provider_id}]`, computed entirely server-side. This is the one
  piece of this whole platform's usual "fetch the full array, filter
  client-side" convention that cannot be reused here — sending the
  real appointments array to an anonymous browser, even just to
  filter it into slots client-side, would leak other patients' visit
  times and (via `patient_id`) enough to correlate identity. Server-
  side-only computation is not a hardening step added later; it's the
  only safe design.
- `api/sairndental/public-book.js` — `{slug, patient info (name, dob,
  phone, email), provider_id, procedure_type_id, start_time}` in.
  Rate-limited (§4) before anything else runs. Creates a real
  `dnt_appointments` row with `status:'Pending'`,
  `source:'self-scheduled'` — the `EXCLUDE` constraint (§3) is what
  actually prevents two patients racing for the same slot; this
  endpoint's own pre-check is a fast-fail UX nicety, not the real
  guarantee.

Both new files, not additions to the existing `DNT_RESOURCES` block in
`api/sd-data.js` — that block requires a Bearer license key on every
request (`validateLicenseKey` runs before any resource dispatch); these
two endpoints must not, so they need their own request handling, slug-
to-`license_hash` resolution, and (for `public-book.js`) their own
insert logic against the real-column `dnt_appointments` shape.

## 3. Real conflict/double-booking prevention

```sql
alter table public.dnt_appointments
  add column provider_id text,
  add column operatory_id text,
  add column start_time timestamptz,
  add column end_time timestamptz,
  add column status text;

create extension if not exists btree_gist;

alter table public.dnt_appointments
  add constraint dntap_no_provider_overlap
    exclude using gist (
      license_hash with =, provider_id with =,
      tsrange(start_time, end_time) with &&
    ) where (status in ('Pending','Confirmed')),
  add constraint dntap_no_operatory_overlap
    exclude using gist (
      license_hash with =, operatory_id with =,
      tsrange(start_time, end_time) with &&
    ) where (status in ('Pending','Confirmed'));
```

Two real, atomic, database-level constraints — a provider can't be
double-booked, an operatory can't be double-booked, checked by
Postgres itself on every insert, not by application code that could
race. This is the textbook-correct tool for interval-overlap
prevention (the same reasoning the reservation-lock and invoice-
uniqueness fixes already established for exact-match cases, applied
to the genuinely different shape this problem has — overlapping time
ranges, not a single duplicate key).

`api/sairndental/public-book.js`'s insert against this table will
raise a real Postgres `23P01` (exclusion_violation) on a genuine race
— mapped to a clean `409 SLOT_TAKEN` response, same "map the real DB
conflict to an honest rejection" pattern as `sdn_invoices`'s
`DUPLICATE_INVOICE` fix.

## 4. Real rate limiting

`dnt_booking_rate_limits`, checked and incremented atomically per
request in `api/sairndental/public-book.js` (and `public-availability`
at a looser threshold — read abuse is lower-stakes than write abuse
but not zero-risk): a fixed window (e.g. 5 booking attempts per IP per
hour), real 429 response when exceeded. Genuinely new infrastructure —
stated plainly in the SQL migration's own header, not presented as
reusing an existing pattern that doesn't actually exist.

## 5. Internal-app additions (staff side)

- **Booking Settings panel** — practice sets/views their public
  `booking_slug`, timezone, and which `dnt_procedure_types` are
  checked as publicly bookable (not every procedure type should
  necessarily be self-schedulable — e.g. a first surgical consult
  might be staff-only).
- **Pending Requests panel** — every `status:'Pending'` appointment
  (self-scheduled or otherwise), with Confirm/Reject actions. **No
  outbound notification email in this plan** — deferred to the
  automated-reminders follow-up plan (spec §5) so email
  infrastructure is built once, coherently, not piecemeal across two
  plans. Staff checks this panel in-app for now; a real "new pending
  request" notification becomes possible once that infrastructure
  exists.
- **Provider Hours** (already built in the foundation) is the real
  input `public-availability.js` walks forward from — no new UI
  needed there, just a new consumer of existing data.

## 6. Timezone handling

`dnt_settings.timezone` (practice's real local timezone, e.g.
`America/New_York`) is the single source of truth for every displayed
and stored appointment time — never the visitor's browser timezone.
Slot times are computed and returned in the practice's timezone;
the public page displays them as-is, labeled with the timezone
explicitly (a patient in a different timezone must not be confused
about which "9am" is meant).

## 7. Testing

- Real conflict test: two near-simultaneous `public-book.js` requests
  for the same provider+time (or same operatory+time) — confirm
  exactly one succeeds and the other gets a real `409 SLOT_TAKEN` from
  the actual `EXCLUDE` constraint firing, not from an application-
  level pre-check that could itself race.
- Real rate-limit test: exceed the threshold from one IP, confirm a
  real `429`, confirm a different IP is unaffected.
- Confirm `public-availability.js`'s response never contains another
  patient's `patient_id`, name, or any field beyond
  `{start_time, end_time, provider_id}` — the actual regression test
  for §2's "never leak" requirement, not assumed from code review.
- Slug resolution: confirm a booking request with an invalid/unknown
  slug is rejected cleanly, and confirm the real license key is never
  present anywhere in the public page's HTML, JS, or network requests
  (a real check, not an assumption — grep the served page and inspect
  actual request payloads).
- Standard structural checks + Push Protocol on every file touched.
