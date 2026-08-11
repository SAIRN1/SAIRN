# SAIRNdental — New App Design Spec

**Status:** Design drafted 2026-08-10, pending review. Not yet implemented.

New SAIRN B2B practice-management app for dental practices. Confirmed
scope, resolved through direct design questions rather than assumed
(timeline explicitly extended mid-brainstorm — "no rush... take the
time each genuinely needs" — this is a real, properly-scoped build,
not a rushed 5-day MVP with the ambitious options quietly downgraded):

1. Real-time checkout balance tracking, backed by a real per-CDT-code
   fee-schedule/coverage-percentage engine.
2. Self-scheduling via a real public booking page, backed by a real
   recurring-availability engine (provider working hours,
   appointment-length by procedure type, real conflict/double-booking
   prevention) — multi-provider/multi-operatory from day one.
3. Real automated no-show reminders via email (not SMS) — genuinely
   new infrastructure for this platform (see §3).
4. Denial tracking + A/R aging + revenue reporting, bridged directly
   from SAIRNcode's `sc_denial`/`sc_ar`/`sc_revenue` (data model + KPI
   math reused as-is — confirmed CARC/RARC codes are the universal
   ANSI X12 835 remittance standard, not medical-specific).

**Explicitly out of scope:** claims submission / clearinghouse
integration (confirmed). AI chat / general assistant panel — not
requested, would be scope creep on top of an already-substantial build.

## 0. Brand identity

**Color: `#0EA5E9`** (sky blue). Checked against Guardian v2's App File
Map (`~/.claude/skills/sairn-guardian-v2/SKILL.md` §App File Map) —
genuinely non-colliding: the map currently has six green/teal/lime
variants already in use (`#16C762`, `#14B8A6`, `#22C55E`, `#15803D`,
`#0D9488` ×2, `#84CC16`) plus red (`#F87171`), amber (`#F59E0B`),
indigo (`#6366F1`), purple (`#7C3AED`), gray (`#6B7280`), and royal
blue (`#2563EB`) — `#0EA5E9` is a distinct hue from every one of them,
including the two existing blues.

**Found while checking, not asked to fix:** `#0D9488` is currently
assigned to *two* apps in the map — SAIRNcare and SAIRNacc — an
undetected collision of the exact class this skill's own changelog has
corrected before (SAIRNhr/SAIRNvet, 2026-07-30). Not touched here —
orthogonal to this task — but flagged so it isn't silently missed
again.

**App ID:** `sairndental`. **File:** `sairndental.html` (this
platform's standard single-file-per-app convention). **Server routes:**
`api/sairndental/*.js` (own namespace, matching SAIRNcash's
precedent) plus new entries in the shared `api/sd-data.js` resource
allowlist for the license-key-synced resources (§5) — **not** the
Stripe/Firebase pattern SAIRNcash uses. SAIRNdental is a standard SAIRN
B2B practice app (license-key auth, like SAIRNvet/SAIRNcode/every
other non-consumer-subscription app on this platform), not a
direct-consumer subscription product — the license-key + `sd-data.js`
resource-route pattern is the correct, consistent choice here, not a
question that needed asking.

## 1. Mandatory scaffold requirement (per `sairn-app-scaffold`)

**Every new SAIRN app's v1 must include the Photo Capture → Claude
Analysis → Structured Output pattern** — a standing platform
requirement, not optional, found by checking that skill before scoping
this app (would have been missed otherwise). StoneDesk's shape:
photo → Claude reads it → structured output relevant to the app's
actual user.

**Chosen adaptation for SAIRNdental: insurance-card capture.**
Front-desk staff photograph a new patient's insurance card; Claude
extracts payer name, member ID, group number, and plan type from the
image and pre-fills the patient's insurance record. This is a
deliberate, non-generic fit — not "photo → quote" copy-pasted from
StoneDesk — chosen because it directly feeds §3's fee-schedule/
coverage engine (accurate payer identification is exactly what that
engine needs as input), unlike a clinical-diagnosis photo feature
(out of scope — no clinical documentation was requested, and this
app's users are front-desk/billing staff, not clinicians).

Same proxy discipline as every other app: `sairn.vercel.app/api/claude`
only, `app_id:'sairndental'`, image as a multimodal content block,
free-text response with targeted extraction (not a fragile JSON
contract) — the proven baseline per the scaffold skill's own honest
note about StoneDesk's real implementation.

## 2. Data model (new resources, `sd_` — actually `dnt_`-prefixed per
   this platform's per-app-prefix convention)

- `dnt_patients` — `{id, name, dob, phone, email, insurance_payer,
  insurance_member_id, insurance_group_number, insurance_plan_type,
  created_at}` — `insurance_*` fields populated by §1's capture flow
  or manual entry.
- `dnt_providers` — `{id, name, role (dentist/hygienist), operatory_id}`.
- `dnt_operatories` — `{id, name}` — the physical chairs/rooms being
  scheduled against.
- `dnt_provider_hours` — `{id, provider_id, day_of_week, start_time,
  end_time}` — real recurring weekly availability, the input to §4's
  slot-computation engine.
- `dnt_procedure_types` — `{id, cdt_code, description,
  default_length_minutes, default_fee}` — practice-entered, **not** a
  bundled ADA CDT code library (see §3's licensing note — this is a
  real legal constraint, not a style choice).
- `dnt_coverage_rules` — `{id, payer, procedure_type_id,
  coverage_percent}` — practice-entered estimate basis for §3.
- `dnt_appointments` — `{id, patient_id, provider_id, operatory_id,
  procedure_type_id, start_time, end_time, status
  (Pending/Confirmed/Completed/No-Show/Cancelled), reminder_sent_at,
  created_at, source (staff/self-scheduled)}`.
- `dnt_charges` — `{id, patient_id, appointment_id, procedure_type_id,
  amount, date}`.
- `dnt_payments` — `{id, patient_id, amount, date, method}`.
- `sc_denial` / `sc_ar` / `sc_revenue` — **reused resource names and
  shapes directly from SAIRNcode** (§6), not renamed to a `dnt_`
  prefix, since the whole point is reusing SAIRNcode's proven data
  model and KPI math verbatim. New `api/sd-data.js` resource-name
  entries needed (`dnt_denial`/`dnt_ar`/`dnt_revenue` to avoid an
  actual key collision with SAIRNcode's own resources on the shared
  backend — the *shape* is reused, the *storage key* still needs its
  own namespace, same collision-avoidance discipline this platform's
  `api/sd-data.js` header already documents for every prior app).

## 3. Real-time checkout balance + fee-schedule engine

**Balance = charges for today's visit − (coverage_percent × charge,
per procedure, from `dnt_coverage_rules`) − payments already made.**
Real arithmetic, computed live as charges/payments are entered — no
AI involvement in the number itself, same discipline as every
financial computation on this platform this session.

**CDT code licensing — real constraint, not a preference.** CDT
(Current Dental Terminology) codes are copyrighted by the American
Dental Association, the same licensing class as AMA-copyrighted CPT
codes. SAIRN has no ADA license. **`dnt_procedure_types` is entirely
practice-entered** — the practice types in their own procedure list
(code, description, length, fee) — matching how every other
coding-adjacent feature on this platform already works (SAIRNcode's
`sc_prebill` free-text error field, `sc_denial`'s free-text cause) —
never a bundled/hardcoded copy of the real CDT code set. This is not
a scope cut; it's the only legally clean option available, and it's
consistent with existing platform convention regardless.

**Coverage percentages are payer + procedure-type level estimates,
not per-individual-plan.** Real dental coverage varies by specific
plan even within one payer — a payer-level default is a genuine
estimate, not a guaranteed figure, and must be disclosed as such in
the UI (same "this is an estimate, not a filing/claim-ready number"
discipline as SAIRNcash's tax estimator). No public, canonical source
exists to verify these against (unlike SAIRNcash's IRS constants) —
this is inherently practice-configured data, stated plainly in the
spec rather than implied to be more authoritative than it is.

## 4. Self-scheduling + real availability engine

**Public booking page — new, unauthenticated surface, first on this
platform.** Real security requirements, not optional hardening added
later:
- Shows only open slot times (date/time/provider name/procedure-type
  options) — never another patient's name, appointment details, or
  any identifying information.
- Rate-limited (server-side, same discipline as every other public
  endpoint on this platform that accepts unauthenticated writes).
- A submission never reads or modifies any existing appointment or
  patient record it doesn't own — write-only creation of a new
  request, no lookup capability exposed to an anonymous caller.
- **New bookings land as `status:'Pending'`, never auto-confirmed.**
  An anonymous, unauthenticated submitter should never be able to
  permanently lock a real slot without staff review — this is a
  firm decision, not a question, given the alternative (auto-confirm)
  creates a real bad-faith-booking / slot-squatting risk with zero
  verification. Staff confirms (or rejects) in the internal app.

**Real recurring availability, computed from `dnt_provider_hours`:**
for a selected provider + procedure type, the engine walks the
provider's weekly hours forward, subtracts existing `Confirmed`/
`Pending` appointments for that provider AND that provider's assigned
operatory (double-booking prevention checks both dimensions — a
provider can't be in two places, and an operatory can't hold two
patients), and returns real open slots sized to the procedure type's
`default_length_minutes`. This is genuinely more complex than a flat
slot list (confirmed timeline supports it) — real conflict detection,
not a placeholder.

## 5. Automated no-show reminders (real email, confirmed)

**Genuinely new platform infrastructure — no email/SMS send capability
exists anywhere on SAIRN today** (confirmed via a full-platform search
before this design pass, not assumed). Requires:
- A real transactional email provider account (e.g. Resend) — **a
  manual step for Michael**, same category as every Stripe/Supabase
  credential this session's other builds have needed provisioned
  outside what I can do myself.
- `api/sairndental/send-reminder.js` — calls the provider's API to
  send one real email per due appointment.
- A real scheduled trigger — Vercel Cron (`vercel.json`'s `crons`
  config, new to this repo) running e.g. daily, querying
  `dnt_appointments` for `Confirmed` appointments in the next 24-48
  hours with no `reminder_sent_at` yet, sending one email each, and
  recording the timestamp so a reminder is never sent twice for the
  same appointment.
- Honest failure handling: a failed send is logged, not silently
  swallowed — matches this platform's `sairn-silent-failure-sweep`
  discipline for anything touching an external system.

## 6. Denial / A/R / Revenue bridge from SAIRNcode

Per the prior real assessment of `sairncode.html`'s
`sc_denial`/`sc_ar`/`sc_revenue`: the data model and KPI math (denial
appeal-success-rate + predictive insights, A/R aging buckets,
payer-mix + cash-conversion) port **directly, unchanged** — confirmed
CARC/RARC codes are the real, universal ANSI X12 835 denial-code
standard used by dental claims too, not a medical-specific system that
needed reworking. Only the seed/example content and UI copy are
relabeled to dental context (e.g. denial-cause examples, payer-mix
category framing). No new business logic invented for this bridge —
reuse, not reinvention, per the confirmed assessment this design
builds on.

## 7. Testing

- Fee-schedule math: hand-computed balance examples across multiple
  procedures/payers, confirming the arithmetic (not an estimate of an
  estimate — the coverage-percent lookup and multiplication must be
  exactly right even though the coverage percent itself is a
  practice-entered estimate).
- Availability engine: real conflict-detection test cases — same
  provider double-booked, same operatory double-booked, a slot
  correctly excluded when either resource is taken, correctly
  included when neither is.
- Public booking page: confirm an anonymous request can never read or
  modify data beyond open-slot times and its own new (Pending)
  submission; confirm rate limiting actually triggers under repeated
  requests.
- Reminder cron: confirm a reminder fires once and only once per
  appointment (idempotency via `reminder_sent_at`), confirm a failed
  send is logged honestly, not silently dropped.
- Denial/AR/Revenue bridge: confirm the ported KPI math produces
  identical results to SAIRNcode's own logic given the same input
  shape — the actual regression test for "reused directly," not
  assumed from code review alone.
- Standard structural checks (`checkblocks.py`, `div_balance_check.py`,
  `duplicate_global_check.py`, `key_collision_check.py` — this last one
  specifically for the `sc_denial`/`sc_ar`/`sc_revenue`-shaped
  resources given the explicit reuse) after every change; full Push
  Protocol before/after push.

## 8. Open items for the next pass (not resolved by this spec)

- Real competitive pricing research for dental practice-management
  software — not done as part of this design pass, required before
  any pricing/trial-gate numbers are finalized (standing
  market-readiness gate).
- Whether `dnt_patients` needs any HIPAA-specific handling beyond
  this platform's existing data-minimization patterns — flagged, not
  assessed here; dental practices are covered entities, worth a real
  compliance pass before this goes to a real practice, separate from
  this design spec's scope.
