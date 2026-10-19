# b19 concepts — one line each, written BEFORE the code

**Dispatch item 1 is a method, not a deliverable:** state the concept before
writing logic. These are those statements, written first and left unedited
afterwards so a reader can tell what the design was *intended* to be from what
it became.

---

## Item 2 — the C1 bookkeeper IOLTA carve-out

> **CONCEPT.** The two trust-side reconciliation legs become reachable by a
> NEW NAMED VERB — `reconcile` — granted to the LEGAL-SIDE roles only
> (owner / attorney / paralegal) and never to `bookkeeper`; a plain `read` on
> those two resources stays refused for everyone outside
> `LAW_BAR_ADMITTED_ROLES`, so the hard lock still closes every other route.

Shape copied deliberately from C2's `prepare`: one spelled action name, one
frozen role set, one branch inside the lock. Not a widened table cell, not a
widened `LAW_BAR_ADMITTED_ROLES`.

### WHAT THE RESEARCH ACTUALLY SAYS, AND WHERE IT DISAGREES WITH THE DISPATCH

The dispatch's premise is *"two of the three legs are bar-admitted-only by
law."* **That is not what the rules say, and saying so is the point of doing
the research rather than citing it.** What the common-practice sources support,
in the same way `PRESCRIBER_ROLES` is supported by "a controlled-substance
entry is a legal act by a licensed person":

1. **The three legs are RECORDS, not acts.** A three-way reconciliation
   compares (a) the trust bank statement's adjusted balance, (b) the firm's own
   trust ledger / checkbook balance, and (c) the SUM of the individual client
   sub-ledger balances. All three must agree. None of those three is an act a
   licence is required to perform.
2. **ABA Model Rule 1.15** puts the DUTY to safeguard client property on the
   lawyer. That duty is non-delegable as a RESPONSIBILITY.
3. **ABA Model Rule 5.3** expressly permits non-lawyer assistants, with the
   lawyer answerable for their conduct — so the clerical and arithmetic work of
   a reconciliation IS delegable under supervision, and in ordinary practice it
   is delegated.
4. **THE BAR-ADMITTED-ONLY ACT IS THE SIGNATURE, NOT THE ARITHMETIC.** The
   clearest hard rule is New York's Rule 1.15(e): only an attorney admitted in
   the State may be an authorised signatory on an attorney special/trust
   account. Several states carry an equivalent. That is about AUTHORISING MONEY
   OUT, which is exactly the act C2's two-stage lock already models.
5. **The lawyer must REVIEW AND APPROVE the reconciliation.** State bar
   guidance that mandates periodic three-way reconciliation (North Carolina,
   Florida, New Jersey, Arizona and Texas among them) also puts the review on
   the lawyer and warns against a non-lawyer holding sole or unsupervised
   control of the trust account.

**SO THE INSTRUCTION IS IMPLEMENTED AND THE PREMISE IS CORRECTED.** Routing the
two trust legs to the legal side and keeping `bookkeeper` on the operating
account is well supported — a bookkeeper with trust-account access and no
lawyer between them and the money is the specific arrangement the guidance
warns about. What is NOT supported is the reason given: it is not that the legs
require a licence, it is that the ACTS ON THEM (signing, authorising, attesting)
do, and that the responsibility cannot be handed over with the task.

### THE RESIDUAL, RAISED AS ITS OWN DECISION-NEEDED RATHER THAN GUESSED

Point 5 is the half this item does **not** build. Granting `paralegal` the
`reconcile` verb implements "a non-lawyer may do the work"; it does **not**
implement "and a lawyer must review and approve the result", because there is
no attestation record anywhere in SAIRNlaw and building one is a mechanism, not
a role-map entry. **What b19 ships instead is a DISCLOSURE constant carrying
the rule and the gap**, not a silent half-measure — because a reconciliation
the app presents as complete, produced by a paralegal with no lawyer
attestation, is the "wrong model that looks like compliance" shape F3's own
answer exists to avoid.

**Two sub-questions are therefore open and both are named in the handoff:**
(a) should `paralegal` be on the reconcile list at all before an attestation
step exists; (b) should the attestation be the same countersignature mechanism
`api/_lib/countersign.js` already runs for C2.

---

## Item 3 — `leg_settings` storage

> **CONCEPT.** ONE row per home, keyed by `license_hash`, holding the two b18
> policy answers as NAMED COLUMNS rather than a free JSON blob — so an invalid
> value is refused by a database CHECK rather than normalised away at read
> time, and the narrow default is what an absent row means.

`api/_lib/leg-roles.js` already owns the normalisers (`liveryBilling`,
`apprenticePolicy`) and both already fail to the NARROW answer on anything they
cannot read. The schema's job is to make the stored value trustworthy at the
boundary as well: a CHECK on the livery-billing enum, and the apprentice
config as `jsonb` because it is genuinely a list-of-names shape the normaliser
must still filter.

**IT IS A SCHEMA AND A NORMALISER, NOT A HANDLER.** `api/sd-data.js` is cody's
this batch on Michael's explicit instruction, so the resource registration and
the `decide(..., home)` plumbing are ROUTED as a pasteable change rather than
written. Stated here so the gap is a decision and not a surprise.

---

## Item 4 — the countersignature panels

> **CONCEPT.** One read-only list per app driven by the `status` action that
> already exists, rendering ONE NAMED STAGE per row — never four nullable
> columns — because four columns is four chances for a panel to show "signed"
> for a spent-and-expired record.

The endpoint already computes the stage (`awaiting_signature` / `signed` /
`filed` / `expired`) for exactly this reason, and both SQL schemas carry an
`idx_*_countersign_open` index built to serve this query. The panel consumes
the computed stage and does no arithmetic of its own.

**ONLY `sairnlaw.html` IS BUILT.** `sairnlegacy.html` is fourth's for the b31
contrast pass; its panel is ROUTED as a pasteable change.

---

## Item 5 — the Grant App Login Access status

> **CONCEPT.** Not a build item: a measurement. Drive the shipped function and
> report what it does, because this is the bug whose own fix comment records
> that *reading* the code was the method and the method failed.

---

## What these concepts deliberately do NOT include

* **No widening of `LAW_BAR_ADMITTED_ROLES`.** The tier answers one question
  and `paralegal` is not bar-admitted. The reconcile grant is a separate named
  set for a separate named verb.
* **No attestation mechanism.** Named as DECISION-NEEDED above.
* **No change to `LAW_TRUST_TWO_STAGE` or to either `MODE_*`.** b18's F1/C2
  asymmetry is still open as attack point (a) of the Tier A obligation and is
  not re-decided here.
