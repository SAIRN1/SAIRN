# SAIRNdental patient portal — scoping

**2026-09-25 (Cody). Scoping only: no panel built, no endpoint written, no
schema applied.** Raised by external research (PR #17) as a real,
high-confidence gap — zero markers in the app, confirmed table stakes across
seven named competitors.

**The zero-marker finding is confirmed and it is misleading on its own.**
Measured against `sairndental.html`: `portal` 0, `patient portal` 0, `online
booking` 0, `magic-link` 0, `patient_login` 0. But `self-scheduled` /
`self-scheduling` appears 6 times, and the reason is the finding this document
turns on.

---

## 1. The gap is NOT the public surface — that is already built

SAIRNdental already ships a genuinely public, unauthenticated surface, with
real controls, that most of a portal would otherwise have to invent:

| already on disk | what it does |
|---|---|
| `api/sairndental/public-availability.js` | public slot availability by practice slug |
| `api/sairndental/public-book.js` | public booking. **Atomic double-booking prevention is a Postgres EXCLUDE constraint** (`sql/sairndental_availability_booking_schema.sql`) firing on the insert — a `23P01` maps to a clean `409 SLOT_TAKEN`, deliberately not an application-level pre-check that could itself race. Bookings land `Pending`, never auto-confirmed |
| `api/sairndental/public-complaint-submit.js` + `public-complaint-thread.js` | an anonymous **two-way thread**: `{token}` loads it, `{token, reply}` appends |
| `api/sairndental/send-reminder.js` | outbound reminders |
| `api/_lib/dental-public.js` | slug resolution, IP hashing, rate limiting, shared by all of the above |
| `api/_lib/dental-guardian.js` | the minor/guardian rule, shared with the authenticated `dnt_patients` write — one implementation, two paths |

So the platform is much further along than "zero portal markers" implies.

**WHAT IS ACTUALLY MISSING IS IDENTITY, AND IT IS EXACTLY ONE THING.**
Everything public today is *anonymous and one-shot*. A patient books and
receives nothing they can come back with; a complainant is the sole exception
and the mechanism is already there — `dnt_complaints.access_token`, looked up
server-side at `public-complaint-thread.js:23`.

**A patient portal is that same surface plus a patient who can return and see
their own record.** That reframing is the whole scope: it is an identity
problem with a small amount of read surface attached, not a new application.

---

## 2. Panel shape

Two surfaces, and keeping them apart matters more than what is on them.

**(a) The patient-facing view — NOT a panel in `sairndental.html`.** Every
existing panel sits behind the practice's employee session. A patient is not an
employee and must never reach the staff app. It is a separate document served
at the practice slug, the way the existing public booking flow already is.

Minimum content, each mapping to a resource that already exists:

| section | source | notes |
|---|---|---|
| My appointments | `dnt_appointments` | upcoming + past, with the `Pending`/confirmed distinction the booking flow already produces |
| Request an appointment | existing `public-book.js` | already built; the portal only pre-fills the patient |
| My treatment plan | `dnt_txplans` | **read-only.** Already patient-scoped server-side |
| My estimates | `dnt_gfe` | Good Faith Estimate — already patient-scoped |
| Balance & statements | `dnt_charges`, `dnt_payments`, `dnt_ar` | **read-only, and see §4 — this is the risky one** |
| Forms / intake | new | the one genuinely new write surface |
| Messages | `dnt_complaints` pattern | the token thread generalised, or deliberately excluded — see §5 |

**(b) The staff-facing panel — one, small.** `panel-portal-access`: who has
portal access, invite/revoke, last-seen. Owner-gated. It is an access-control
table, so it follows the precedent `dnt_providers` already set when
`linked_employee_id` made the roster an access-control table and its write went
owner-only.

---

## 3. Data model

**The identity record is the only new table.**

```
dnt_portal_access
  portal_id        (the resource key, per DNT_RESOURCES convention)
  patient_id       -> dnt_patients.id     ONE-TO-ONE, enforced server-side
  status           invited | active | revoked
  invited_by       employee_id from the verified session
  invited_at, last_seen_at
  -- NO credential material in the data blob; see below
```

**ONE-TO-ONE ENFORCED SERVER-SIDE, 409 ON A SECOND ROW.** This is not a style
choice — `dnt_providers.linked_employee_id` is enforced exactly this way and
its own comment gives the reason: *"two rows carrying the same link would make
scoping depend on row order."* A portal row is the same shape and inherits the
same failure.

**Authentication: magic-link, not a password.** Reasons, in order:

1. The platform already has the mechanism — `dnt_complaints.access_token` is a
   server-side-resolved opaque token, and `api/_lib/auth.js` already signs and
   verifies short-TTL tokens with a deliberately distinct `typ` claim
   (`signPreAuthToken`/`verifyPreAuthToken`, 5-minute TTL). A portal token is a
   third `typ`, not a new crypto system.
2. A password means storing a credential for a **patient**, which widens the
   BAA surface and adds a reset flow, a lockout policy and a rotation story.
3. `typ` MUST be distinct and MUST be verified. `verifySessionToken` already
   refuses any token whose `typ` is not `session`; a portal token must be
   refused by every staff path by the same mechanism, and that arm is the first
   one to write.

**No new patient table.** The portal reads `dnt_patients` and friends. Creating
a second patient record for portal users is how the two drift.

---

## 4. Integration points — and the one that decides the size of this

**THE SERVER-SIDE SCOPING ALREADY EXISTS AND IS THE REASON THIS IS TRACTABLE.**
`api/sd-data.js:11970` defines:

```
DNT_PATIENT_SCOPED_RESOURCES = { dnt_patients: 'id', dnt_referrals: 'patient_id',
  dnt_gfe: 'patient_id', dnt_recall_outreach: 'patient_id',
  dnt_txplans: 'patient_id', dnt_denial: 'patient_id' }
```

built for the provider tier on 2026-08-27. A portal caller is the same shape of
problem — one identity, one patient's rows — so the portal read path should
**reuse that map with a different subject**, not add a parallel one. Two
scoping maps that can disagree is the defect; one map with two callers is not.

**THE FINANCIAL TIER IS WHERE THIS GETS DECIDED, AND IT IS NOT A DETAIL.**
`DNT_FINANCIAL_ROLES = roleSet({owner, frontdesk})` (`:11834`) gates
`dnt_charges`, `dnt_payments`, `dnt_denial`, `dnt_ar`, `dnt_revenue`,
`dnt_coverage_rules` on read AND write. A patient seeing "my balance" needs a
row from a resource **currently refused to a provider**. That is not a bug to
route around — it is the minimum-necessary tier working. Three honest options,
and this document does not pick one:

1. **Ship the portal without balances.** Smallest, safest, and six of the seven
   competitor products lead with scheduling rather than billing anyway.
2. **A derived, patient-scoped balance endpoint** that returns a single figure
   and never the rows — a new surface with its own tier, not a widening of
   `DNT_FINANCIAL_RESOURCES`.
3. **Widen the financial tier to a portal subject.** Cheapest to write and the
   one that should not be chosen quietly: it puts a patient identity inside a
   map built to keep *staff* out of financial rows.

**The write surface must stay almost empty.** Today a patient can create a
`Pending` appointment and nothing else. The portal should add at most intake
forms. Any portal write to `dnt_patients` reopens the minor/guardian rule, and
`api/_lib/dental-guardian.js` exists precisely because that rule was once
enforced on one server path and not the other.

---

## 5. What this scoping does NOT settle

- **Whether to build it at all.** That is a `sairn-decision-gate` question. PR
  #17's "table stakes across seven competitors" is a market claim, and it
  arrives one grade below a direct vendor read (see the cloud-research audits'
  own §0 on evidence grade).
- **Messaging.** Generalising the complaint thread into patient↔practice
  messaging creates a PHI channel with retention, breach-notification and
  minimum-necessary consequences that scheduling does not have. It should be a
  separate decision, not a portal sub-feature.
- **The BAA.** `docs/SAIRN-OPEN-WORK-INDEX.md` carries an OPEN row: no BAA
  exists, and it blocks signing rather than shipping. **A portal materially
  widens the surface that row is about** — it puts PHI in front of the patient
  over a new channel with a new credential. It does not change the answer
  (counsel, before real patient data), but it changes the size of the question
  and counsel should see this scope.
- **Any estimate.** No hours are given here. The §4 financial decision changes
  the size by more than the panel work does, and estimating before that call is
  made would be a number invented to look like a plan.

---

## 6. What was verified for this document

Read out of the repo at `bfbe53e7`, not taken from the brief: the marker counts
in §1; the seven files under `api/sairndental/`; `public-book.js`'s header
describing the EXCLUDE-constraint race prevention and the `Pending` rule;
`public-complaint-thread.js:23`'s `access_token` lookup;
`DNT_PATIENT_SCOPED_RESOURCES` at `api/sd-data.js:11970` and
`DNT_FINANCIAL_ROLES` at `:11834` with their enforcement sites; and
`api/dnt-auth.js`'s role header recording that `dnt_providers` write went
owner-only once the roster became an access-control table.

**Not verified: the competitor claim.** Seven products are said to ship this;
none was opened from here.
