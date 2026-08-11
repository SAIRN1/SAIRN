# SAIRNdental — Fee-Schedule Engine + Real-Time Checkout Balance Design

**Status:** Design drafted 2026-08-11, pending review. Not yet implemented.

Concrete technical design for the top-level spec's §3 (real per-CDT-code
fee-schedule/coverage-percentage engine — confirmed in scope, not the
manual-entry fallback, per the original design brainstorm). Two real
design questions resolved directly, not assumed, before writing this:
whether the insurance estimate is a locked-in snapshot or always
recomputed live, and whether completing a visit auto-generates its
charge.

## 0. Two real design questions, resolved

**Estimate timing — locked in at charge-entry time, not recomputed
live.** `dnt_charges` gains a new field, `estimated_insurance_portion`,
computed once from `dnt_coverage_rules`' current `coverage_percent`
for that patient's payer + the charge's procedure type, and stored on
the charge record permanently. A later edit to a coverage rule never
retroactively changes a past charge's estimate — matches how a real
insurance estimate given at time of service actually works (a
snapshot), and avoids a coverage-rule edit silently changing a
months-old balance with no real event behind it.

**Charge creation — auto-generated on visit completion, not always
manual.** `dnt_appointments` gains a real `Completed` status (alongside
the existing `Pending`/`Confirmed`/`Cancelled`). A new "Complete
Visit" action on a `Confirmed` appointment creates its linked
`dnt_charges` row automatically from the procedure type's
`default_fee` — pre-filled, never silently auto-committed (staff
reviews/edits the amount before saving, same "AI/automation suggests,
human confirms" discipline as every prior automated-suggestion
feature on this platform, even though nothing here is AI-driven).
Connects scheduling and billing as one real system instead of two
disconnected halves, and removes the real "staff forgot to log the
charge" failure mode `dnt_charges.appointment_id` was already built
to support but nothing used yet.

## 1. Balance model — patient-level, not per-visit-isolated

Confirmed by the existing data model, not newly decided here:
`dnt_charges`/`dnt_payments` are patient-scoped (`patient_id`), not
appointment-scoped-and-isolated — a patient's checkout balance is
their **real cumulative ledger**: every unpaid charge's
patient-responsibility portion, across every visit, minus every
payment on file. This matches how real dental practice-management
software actually works (an old unpaid balance from a prior visit
surfaces at today's checkout too, not hidden), not a narrower
"today's visit only" number.

```
patient_responsibility(charge) = charge.amount - charge.estimated_insurance_portion
balance_due(patient) = sum(patient_responsibility(c) for c in patient's charges)
                        - sum(p.amount for p in patient's payments)
```

Real arithmetic, computed client-side from the real synced ledger —
no AI involvement in the number itself, same discipline as every
financial computation on this platform this session.

## 2. Coverage-rule lookup — real, with an honest, safe gap fallback

- Lookup key: `(patient.insurance_payer, charge.procedure_type_id)`
  against `dnt_coverage_rules`, **case-insensitive exact match** on
  payer (`"Delta Dental"` matches `"delta dental"`, not
  `"Delta Dental PPO"` — no fuzzy matching, which would risk a wrong
  guess on a genuinely different plan).
- **No rule found → honest disclosure, safe default.** Estimated
  insurance portion is `$0` (patient shown as responsible for the
  full charge) with a visible "No coverage rule on file for
  `[payer]` / `[procedure]` — showing full amount due. Add a coverage
  rule for a real estimate." message at charge-entry time — never a
  silently guessed percentage. Financially safe default: better to
  show the full amount than under-collect and have to chase the
  difference later.

## 3. Non-goals (explicit scope cuts, this pass)

- No void/refund flow for charges or payments — append-only ledger
  only, matching every other financial-log resource on this platform
  (SAIRNcode's `sc_revenue`/`sc_denial` never supported edits/deletes
  either).
- No patient-facing balance view — checkout balance is a
  **staff-only, internal** feature. Adding a second public,
  unauthenticated surface (beyond the booking page) is real scope
  creep not requested here — a real design question in its own right
  if ever wanted, not folded in silently.
- No live cross-device push sync — "real-time" here means the same
  thing it means everywhere else on this platform: instantly
  recomputed client-side as data is entered, persisted via the
  standard write-then-honest-toast pattern (`sd-data.js`, license-key
  auth). SAIRNcash's Firebase push-sync is specific to its different
  (Stripe-subscriber, not license-key) auth model — not reused here.

## 4. Why no new atomic-write mechanism is needed here (confirmed, not assumed)

Unlike the availability engine's real double-booking risk (two
requests racing to claim the *same* mutable resource), `dnt_charges`
and `dnt_payments` are **append-only ledger entries** — every write
creates a new, uniquely-IDed row; balance is a `sum()` computed at
display time over every entry. Two staff entering a payment
simultaneously each create their own row; both land, both count,
neither can be lost to a last-write-wins race the way a shared
"current balance" field could be. No `EXCLUDE` constraint, no
reservation-lock-style fix needed — checked and stated explicitly
here rather than silently assumed safe.

## 5. Data model additions

- `dnt_charges` — extend existing shape:
  `{id, patient_id, appointment_id, procedure_type_id, amount,
  estimated_insurance_portion, date}`. `estimated_insurance_portion`
  is new (§0).
- `dnt_appointments` — `status` gains a real `'Completed'` value
  alongside `Pending`/`Confirmed`/`Cancelled`. No schema change (the
  column is already `text`, not an enum) — client-side status options
  and the `EXCLUDE` constraints' `where (status in ('Pending',
  'Confirmed'))` clause are both already correct as-is (a `Completed`
  appointment correctly stops blocking new bookings for that slot,
  same as `Cancelled` already does).

## 6. Internal-app additions (staff side)

- **Billing panel** — patient selector, real computed balance
  breakdown (total charges, total estimated insurance, total
  payments, balance due), itemized charge list (amount, locked
  estimated portion, resulting patient responsibility, date), itemized
  payment list, Add Charge form (procedure type auto-fills
  `default_fee`, editable; computes and displays the real coverage
  lookup — including the honest no-rule-found message — before save),
  Add Payment form (amount, method).
- **Appointments panel** (new — distinct from the existing Pending
  Requests panel, which stays focused on new-request triage) — lists
  `Confirmed` appointments with a real "Complete Visit" action that
  opens the pre-filled charge form (§0) rather than silently creating
  it.

## 7. Testing

- Balance math: hand-computed examples across multiple
  charges/payments/coverage combinations, including the no-rule-found
  fallback path.
- Locked-estimate regression test (the actual test for §0's first
  decision): create a charge, then change the underlying coverage
  rule's percentage, confirm the existing charge's stored
  `estimated_insurance_portion` did NOT change, and confirm a *new*
  charge created after the rule change uses the new percentage.
- Complete Visit regression test (the actual test for §0's second
  decision): confirm completing a `Confirmed` appointment pre-fills a
  real charge form from the real procedure default fee, confirm the
  charge is NOT created until the form is explicitly saved (never
  silently auto-committed), and confirm the appointment's status
  becomes `Completed` only after that save.
- Ledger-safety test (§4's claim, verified not assumed): two
  concurrent payment/charge writes for the same patient both land,
  neither is lost.
- Standard structural checks + Push Protocol on every file touched.
