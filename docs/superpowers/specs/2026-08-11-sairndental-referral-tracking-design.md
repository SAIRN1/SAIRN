# SAIRNdental — Referral Tracking Design

**Status:** Design drafted 2026-08-11, pending review. Not yet implemented.

Tracks incoming/outgoing patient referrals between this practice and
external providers/specialists. **Not a previously-logged backlog
item** — checked `SAIRN-BACKLOG.md` and every prior spec before starting;
the only match was an unrelated "Referrals" resource name inside a
different app's (SAIRNbuild's) backlog entry. This is new scope,
requested directly, not an elevation of prior planned work — noted here
so the record is accurate.

## 0. Design questions, resolved

**Referring/receiving party — free text, not a link to `dnt_providers`.**
Dental referrals almost always go to/from external specialists
(endodontists, oral surgeons, orthodontists) who aren't SAIRNdental
users. Matches this app's existing convention for every other
external-entity reference (procedure types, coverage payers) — practice-
entered free text, never assumed to be another platform user.

**Patient link — free-text patient name required, `dnt_patients` link
optional.** The single most common real case (an incoming referral
arriving before the patient has ever booked here) would be blocked if a
real patient record were required up front. Staff can optionally set
`patient_id` later, once/if a real patient record exists — a manual,
staff-selected link, never an automatic name-based fuzzy match (which
risks attaching a referral to the wrong same-named patient).

**Status — a real field, not just a static log entry.** `'Pending'`,
`'Scheduled'`, `'Completed'`, `'Declined'`. Genuine added scope beyond
the original bare field list (who/what/when/why), confirmed directly
rather than assumed. Meaning differs slightly by direction (§2), stated
explicitly rather than left ambiguous.

**Provider scope — both an external party AND this practice's own
provider, two separate fields.** `external_party` (free text) captures
the outside specialist/practice. `internal_provider_id` (optional link
to `dnt_providers`) captures which of this practice's own
dentists/providers is actually responsible for the referral — a real
practice with more than one provider needs to know who's handling each
one, not just where it's going.

**No fee/commission field of any kind — a hard legal constraint, not a
style choice.** Referral fee-splitting or payment-for-referral is
illegal under the federal Anti-Kickback Statute for any federally-
reimbursed care, and prohibited by nearly every state dental board's
ethics rules regardless of payer. The enforcement mechanism is the
field whitelist in §1 itself — that list is the entire schema; nothing
resembling an amount, percentage, or "referral value" is ever added to
it, including as an optional or hidden field.

**Real sync from day one, not bolted on later.** `dnt_referrals` is
added to the `DNT_SYNC_RESOURCES` sweep
(`sairndental.html:1199-1209`, the mechanism built earlier this same
session specifically to fix the platform-critical "staff can't see
server data" bug) from the moment this feature ships. Skipping this
would silently recreate that exact bug for a brand-new resource.

**No remove/delete function — append-only, matching `dnt_charges`/
`dnt_payments`'s precedent, not `dnt_patients`'s.** A referral record is
fundamentally an audit trail entry (who referred whom, when, why), not
a mutable roster item — closer in kind to a charge or payment (the fee-
schedule spec's own explicit "no void/refund flow... append-only ledger
only" decision) than to a patient or procedure type record. `status`
can still change after creation (that's not immutability — see §2), but
the record itself is never deleted. Judgment call, stated with
reasoning here rather than silently picked either way.

## 1. Data model

New resource: `dnt_referrals`. Local storage key: `dnt_referrals_list`.
Server: new `api/sd-data.js` `DNT_RESOURCES` entry (`referral_id` as its
id column, the same generic read/write pair every other `dnt_*`
resource already uses — no dedicated handler needed, this resource has
no promoted-column/constraint requirements the generic block doesn't
already cover).

**Complete field whitelist — this is the entire schema, nothing else
gets added (§0's fee-field prohibition, enforced by this list being
exhaustive):**

- `id` — string, generated client-side (`newId('RF')`, matching this
  app's existing ID convention).
- `direction` — `'incoming'` | `'outgoing'`, required.
- `patient_name` — string, required (free text, always present even
  before a real patient record exists).
- `patient_id` — string | `''`, optional link to `dnt_patients`,
  staff-set, never auto-matched.
- `external_party` — string, required (free text — the outside
  practice/specialist name).
- `internal_provider_id` — string | `''`, optional link to
  `dnt_providers` — which of this practice's own providers is
  responsible.
- `date` — string (YYYY-MM-DD), required.
- `reason` — string, required (free text — e.g. "Root canal
  consult," "Wisdom teeth extraction," matching this app's existing
  free-text convention for anything procedure-adjacent, since CDT codes
  are practice-entered here for the same ADA-licensing reason as
  `dnt_procedure_types`).
- `status` — `'Pending'` | `'Scheduled'` | `'Completed'` | `'Declined'`,
  defaults to `'Pending'` at creation, the one field that can be updated
  after creation (§2).
- `created_at` — string (YYYY-MM-DD), set once at creation, matching
  every other resource's convention.

## 2. Internal-app additions (staff side)

- **New "Referrals" nav entry and panel**, matching every existing
  resource panel's shape: an Add form (direction toggle, patient name,
  optional patient dropdown populated from `patients()`, external party,
  optional internal-provider dropdown populated from `providers()`,
  date, reason) and an "On File" table.
- **Status-change control per row** — matching the existing Confirm/
  Reject button pattern on Pending Requests, not a new UI paradigm: a
  small set of action buttons or a dropdown that updates `status` and
  re-syncs (via the existing `sdnData('write','dnt_referrals',rec)`
  pattern every other resource already uses).
- **Status meaning differs by direction, stated explicitly:** for an
  **incoming** referral, status tracks this practice's own follow-up
  (`Pending` → `Scheduled` once an appointment is booked → `Completed`
  once the visit happens, or `Declined` if the patient never comes in).
  For an **outgoing** referral, status tracks this practice's follow-
  through on making the referral happen (`Scheduled` once the specialist
  appointment is arranged, `Completed` once confirmed) — with a real,
  honest limitation: this practice has limited-to-no visibility into
  the external specialist's own scheduling once the handoff happens, so
  `Completed` here means "confirmed on our end," not "verified by the
  specialist's own system." Not solved by this feature, stated plainly
  instead.

## 3. Legal compliance (real, not decorative)

The Anti-Kickback Statute (42 U.S.C. § 1320a-7b) prohibits payment in
exchange for referrals of federally-reimbursed care; state dental board
ethics rules (near-universal, not state-specific to any one state
checked) separately prohibit fee-splitting for referrals regardless of
payer. This feature's entire value is record-keeping (who/what/when/
why/status) — never a mechanism for tracking or facilitating payment
for referrals. The field whitelist in §1 is the concrete enforcement:
no amount, percentage, or value field exists anywhere in this resource,
now or as a future addition without a fresh legal review.

## 4. Sync integration

`dnt_referrals` added to `DNT_SYNC_RESOURCES`
(`sairndental.html:1199-1209`) as `['dnt_referrals','dnt_referrals_list']`,
using the existing `dntMergeById()` array-merge (no special single-
object handling needed — matches every resource except `dnt_settings`).
New `referrals()` accessor (`return ld('dnt_referrals_list',[]);`,
matching every other accessor's exact shape) and `rReferrals()` render
function, called from `nav()` and from `dntSyncFromServer()`'s existing
`if(changed){...}` re-render block alongside the other 9 resources.

## 5. Error handling

- **Add form validation** — matches this app's existing pattern
  (`addPatient()`/`addProcedureType()`'s style): required fields
  (`direction`, `patient_name`, `external_party`, `date`, `reason`)
  checked before submission, a `toast()` message if any is missing,
  optional fields (`patient_id`, `internal_provider_id`) genuinely
  optional.
- **Status-change write failure** — matches every other write's
  existing honest-toast convention: `sdnData()`'s real result determines
  whether the toast says the status was saved or "Saved on this device
  only -- server sync not yet enabled for this app," never a false
  success.
- **`patient_id`/`internal_provider_id` referencing a since-removed
  local-only record** — matches the existing `rPending()`/`rAppointments()`
  pattern for the same class of problem (an appointment referencing a
  removed patient): render `patient_name`/`external_party`'s own stored
  text regardless of whether the linked ID still resolves, so a stale
  link never breaks the display of the underlying record.

## 6. Non-goals (explicit scope cuts, this pass)

- No fee/commission/value field of any kind, ever, without a fresh
  legal review (§0, §3 — the hard constraint this whole feature is
  built around).
- No remove/delete function (§0) — append-only, matching `dnt_charges`/
  `dnt_payments`'s precedent.
- No automated matching between an incoming referral's `patient_name`
  and an existing `dnt_patients` record — staff-selected link only,
  explicitly to avoid a wrong-match risk (§0).
- No notification/reminder tied to a referral's status (e.g. "this
  incoming referral has been Pending for 2 weeks") — a real, separate
  feature if ever wanted, not folded in here.
- No visibility into the external specialist's own scheduling system
  for outgoing referrals (§2) — genuinely out of this practice's
  control, not something this feature attempts to solve.

## 7. Testing

- Add-form validation: confirm all 5 required fields are enforced,
  confirm both optional fields (`patient_id`, `internal_provider_id`)
  can be left blank without blocking submission.
- Status transitions: confirm each of the 4 status values can be set
  and persists through a sync round-trip (matches the real-sync
  feature's own established test method from earlier this session).
- Stale-link rendering: create a referral linked to a patient, remove
  that patient locally (`removePatient()`), confirm the referral row
  still renders the stored `patient_name` text correctly rather than
  breaking or showing "(unknown patient)" the way an appointment does —
  a deliberate difference, since `patient_name` is always independently
  stored here, unlike appointments which only store `patient_id`.
- Sync integration: confirm `dnt_referrals` is included in
  `dntSyncFromServer()`'s sweep and the manual Refresh button's full
  sweep, using the same live regression method as the real-sync
  feature (submit/create a referral, confirm it appears in a fresh
  browser session).
- Field-whitelist regression: confirm the complete `dnt_referrals`
  record shape (both client-side and the new `api/sd-data.js` entry)
  contains exactly the fields in §1, nothing else — the actual test for
  §0/§3's legal constraint, not just a code-review assertion.
- Standard structural checks (`checkblocks.py`, `div_balance_check.py`,
  `duplicate_global_check.py`) after every change; `node --check` on
  `api/sd-data.js`; Push Protocol before/after push.
