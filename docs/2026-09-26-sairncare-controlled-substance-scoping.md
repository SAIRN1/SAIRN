# SAIRNcare controlled-substance register — scoping

**2026-09-26 (Cody). Scoping only: nothing built, no endpoint changed, no
schema applied.** Raised by external research (PR #15) as a moderate-confidence
gap versus competitors.

**THE PREMISE NEEDS CORRECTING BEFORE THE SCOPE MEANS ANYTHING.** This is not a
missing feature. SAIRNcare already ships a controlled-substance apparatus
inside the MAR panel, and it is more complete than "moderate-confidence gap"
suggests. What is missing is one specific property, it is precisely locatable,
and the platform already has a working implementation of it in another app.

---

## 1. What SAIRNcare already has — read out of the app, not assumed

| piece | where |
|---|---|
| `controlled_substance` flag and a DEA `schedule` field on the medication order | `sairncare.html:453`, `:2476` |
| A **Controlled-Substance Counts** card, listing count history | `:2437` |
| The count record: `{id, medication_id, date, count_value, counted_by, witness_id, discrepancy, discrepancy_notes}` | `saveCsCount()` at `:2856` |
| A facility-level **Controlled-Substance Count Policy** setting, with the active policy shown above the card | `:966`, `:2438` |
| Medication reconciliation and medication-management assessment refusal, both with their own entry types | `:2445`, `:2455` |

And the server side is not thin either. `alf_mar` (`api/sd-data.js:9571`)
requires a verified `sairncare` session, refuses outside
`ALF_MAR_ROLES = {owner, nursing, med_aide}`, whitelists `entry_type` against
`ALF_MAR_ENTRY_TYPES`, restricts the clinical-decision types to
`ALF_MAR_ORDER_ROLES = {owner, nursing}` so a `med_aide` may write only
`administration` and `count`, **looks the resident's assignment up live rather
than trusting a client-supplied `assigned_employee_id`**, and the table is
append-only.

**A reader who concluded "SAIRNcare has no controlled-substance handling" was
reading marker counts, not the app.** `controlled` appears 23 times, `dea` 39,
`witness` 23.

---

## 2. The actual gap, and it is one sentence

**THE SECOND SIGNATURE IS ENFORCED ONLY IN THE BROWSER.**

`saveCsCount()` at `sairncare.html:2860`:

```js
if(!witness){toast('A witness (second signature) is required for a
                    controlled-substance count');return;}
```

That is the whole enforcement. The server's `alf_mar` write validates
`payload.id`, `payload.resident_id` and `payload.entry_type`, checks the role,
and **never looks at `witness_id` at all**. So:

1. a `count` entry with **no witness** is accepted by the server;
2. a count where **`witness_id` equals `counted_by`** is accepted — nothing
   anywhere checks that the two signatures are two people;
3. `discrepancy` is a **client-supplied boolean**, not derived from anything.

**"The API is the boundary, not the panel"** is this platform's own phrase, and
this is a case where the panel is the boundary. On a DEA-relevant register.

**AND A FOURTH, WHICH IS A DESIGN GAP RATHER THAN A HOLE:** `count_value` is a
periodic count with no perpetual balance behind it. Nothing decrements a
running total when an `administration` entry is logged, so a discrepancy is
whatever the counter types rather than a computed difference between expected
and actual. A register that cannot compute the expected number cannot tell a
miscount from a diversion.

---

## 3. Where it fits — and the implementation already exists in this repo

**SAIRNvet solved exactly this, for exactly this class of record.**
`api/sd-data.js:11209` guards `sv_controlled`, and the comment says why in
terms that transfer without modification:

> *"`sv_controlled` is the DEA-relevant controlled-substance register and is
> Tier A WITH NO REMOVAL PATH: a wrong row cannot be taken back through the
> product, because a correction is a SECOND row and the wrong one stands
> forever. So the verification happens BEFORE the write, not as a report
> afterwards."*

and the shape of the guard is the part worth copying:

> *"IT IS A REFUSAL, NOT A FLAG. requireWitness returns a refusal object or
> null — deliberately not a boolean, because a boolean invites
> `if (!ok) { log(); }` and this has to be the thing that stops the write.
> Every could-not-tell answer inside it refuses too."*

The logic lives in **`api/sv-witness.js`**, deliberately extracted *"because a
second implementation of 'is this witnessed' is a second place for the answer
to drift."*

**THAT SENTENCE IS THE WARNING AGAINST THE OBVIOUS PLAN.** The cheap move is to
inline a witness check in the `alf_mar` branch. That creates the second
implementation the SAIRNvet comment exists to prevent, and the two will
disagree the first time either is amended. **The scope should be: generalise
`api/sv-witness.js` to take the resource and the id column, and call it from
both.** That is one shared gate with two callers, which is the shape the
platform already chose for `api/_lib/dental-guardian.js` after the minor/
guardian rule ended up enforced on one server path and not the other.

**AND `docs/2026-09-13-cross-domain-disciplines.md` §7 APPLIES DIRECTLY —
byte-identical is not safe-in-context.** SAIRNvet's witness rule was written
for a veterinary DEA register where the witness is a second clinician. An ALF's
`med_aide` is a different role with different authority, and whether a
`med_aide` may witness another `med_aide`'s count, or whether a witness must be
`nursing` or above, **is a product decision nobody has made** and is not
answerable by copying the vet rule. That decision is the precondition, not the
code.

---

## 4. Proposed scope, smallest first

1. **Server-side witness refusal on `alf_mar` `entry_type === 'count'`.** A
   count with no `witness_id` is refused. Requires the §3 role decision first.
2. **Self-witness refusal.** `witness_id !== counted_by`, and `counted_by` taken
   from the verified session rather than the payload — the same discipline the
   branch already applies to `assigned_employee_id`. This one needs no product
   decision and could land first.
3. **The shared gate**, rather than an inline copy: generalise
   `api/sv-witness.js` and call it from both apps.
4. **Perpetual balance** — expected = last count − administrations since, and
   `discrepancy` derived rather than typed. Materially larger than 1–3 and
   should be a separate decision.

**Not proposed: a new resource.** `alf_mar` is already append-only,
session-gated, role-gated and entry-type-whitelisted. A separate
`alf_controlled` table would split one medication trail across two records and
would be a second place for the answer to drift — the same mistake §3 warns
against, one layer up.

---

## 5. What this does NOT establish

- **The competitor claim.** PR #15's "moderate-confidence gap versus
  competitors" was not verified here; no competitor product was opened. On the
  evidence above the gap is narrower and more specific than that framing, which
  is a reason to re-read the claim rather than to act on it.
- **The tier.** `alf_mar` is not re-tiered here. Its cell should be re-read
  against §2 — a register whose second signature is browser-only is a different
  integrity argument from one whose signature is enforced — but that is a
  register read and this is a scoping pass.
- **Any estimate.** Item 1 is small, item 4 is not, and item 1 is blocked on a
  product decision rather than on engineering. Estimating before that decision
  would be a number invented to look like a plan.

---

## 6. Verified for this document

Read out of the repo at `885b25a7`: the marker counts; `saveCsCount()` and its
browser-only witness check; the `alf_mar` write branch at `api/sd-data.js:9571`
with `ALF_MAR_ROLES`, `ALF_MAR_ORDER_ROLES` and `ALF_MAR_ENTRY_TYPES`; the
live-lookup of the resident assignment; and `sv_controlled`'s witnessing lock
at `:11209` with its extraction into `api/sv-witness.js`.

**AND THE "NO OTHER ENFORCEMENT" CLAIM WAS CHECKED RATHER THAN ASSUMED**, because
it is the claim the whole document rests on: a sweep of `api/sd-data.js` for
`witness` within any `alf`/`mar` context returns nothing, and `api/_lib/*.js`
carries no ALF witness logic -- the single hit is the word "witnessed" inside a
test fixture's free-text note (`api/_lib/record-parity.test.js:44`). So the
browser check at `sairncare.html:2860` really is the only enforcement.

**The SQL layer was checked too and does not close it:** the SAIRNcare schema
files carry no witness constraint -- the only `witness` hit across `sql/*alf*`
and `sql/*care*` is a prose comment in `sairncare_incidents_schema.sql:19`
about mandatory reporting, a different subject. **Still not established:** a
constraint applied live but never written into a tracked schema file would
not show up in this check.
