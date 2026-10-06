# SAIRNdental competitive-gap status, re-derived 2026-09-17 — B2 was built, tiered, reviewed twice, and never wired to a caller. ~~IT STILL IS NOT~~ **IT WAS WIRED THE NEXT MORNING. Headline corrected at HEAD 2026-10-06 (Fourth).**

> **THE HEADLINE OF THIS DOCUMENT WAS FALSE FOR ELEVEN DAYS AND THE
> CORRECTION WAS ALREADY WRITTEN DOWN SOMEWHERE ELSE.**
> `b179d967` *"feat(sairndental): the roll-up gets a reader…"* wired
> `dnt_rollup` on the morning of **2026-09-18**, and
> `docs/2026-09-25-gap-status-docs-reverified.md` recorded that closure on
> 2026-09-25 — in a table whose own row reads *"dental, 19:29 … next morning
> 08:29 … `b179d967` the roll-up gets a reader"*. **Nobody came back here.**
> So the document that exists to answer *"is this still open"* answered it
> correctly, was used, and then went on asserting the old answer in the one
> place a reader hits first.
>
> That is exactly the finding the 2026-09-25 pass generalised — *"the build
> that closes a row edits the row"* — and this file is now the fourth instance
> of it rather than a counter-example. §0's body is corrected below with
> counts taken today; the ANALYSIS in §0.1 and §0.2 is left standing, because
> it was right about why the gap mattered and that reasoning does not expire
> with the status.

**Derived 2026-09-17 (CC) against the code at HEAD.** A **status** document, per
the convention `docs/2026-09-02-competitive-gap-status-rederived.md` set, using
the method of `docs/2026-09-17-sairnroofing-competitive-gap-rederived.md` and
`docs/2026-09-17-caller-level-gap-check-senior-stonedesk.md`: marker counts,
then a hand-read of every non-zero hit, then a **caller-level check** — does the
capability have a panel, a nav target and something that actually sends it.

**This is the pass the two 2026-09-17 documents said they could not do.** Both
stopped at the same place and said so:

> *"SAIRNdental was requested in the same pass and was NOT started. Fourth
> claimed overlapping work 0.1h before this began… Flagged rather than reworded
> past the matcher. SAIRNdental still needs this pass."*
> — `2026-09-17-senior-mechanical-competitive-gap-rederived.md`

> *"SAIRNdental was not touched — fourth's claim on that app is still active."*
> — `2026-09-17-caller-level-gap-check-senior-stonedesk.md` §4

That claim has since been released (finished 5.8h before this pass;
`sairn_claim.py check` returned CLEAR and the released-claim commits were read
before starting, per the tool's own warning about follow-on work). This closes
the gap those two documents left open, and the thing it found is the same shape
they were built to catch.

---

## 0. The finding, stated first: `dnt_rollup` is SAIRNmechanical's defect again, with the claim in the audit trail instead of the UI — **CLOSED 2026-09-18 by `b179d967`, confirmed at HEAD 2026-10-06**

`docs/2026-09-15-competitive-gap-status-rederived-mechanical-and-five-apps.md`
§3.1 called SAIRNdental **B2 — cross-location roll-up reporting** *"the one row
that is genuinely still open, in-house, and un-gated… the only buildable,
un-gated competitive-gap item this pass found across all four audits."*

It was built the same day. Everything except the caller exists:

| Layer | State at HEAD |
|---|---|
| Engine | `api/_lib/dnt-rollup.js` — pure, with four written rules (UNASSIGNED is its own bucket; an unregistered `location_id` is its own bucket; **an unreadable resource yields `null`, never `0`**; every figure carries its row count) |
| Endpoint | `api/sd-data.js:11274` — `dnt_rollup` / `read`, owner-gated via `DNT_MANAGEMENT_ROLES`, refuses the whole report with 503 when settings are unreadable, and lets no row-level data out |
| Registry | `api/_resources/sairndental.js` — `dnt_rollup`, with a comment explaining that an unregistered name is refused by the envelope before any handler runs |
| Tier | `docs/CRITICALITY-TIERS.md:222` — **A**, reasoning from *"a practice-group owner makes staffing and investment decisions from per-office production"* |
| Tests | `api/_lib/dnt-rollup.test.js` **27** arms, `api/_lib/dnt-rollup-endpoint.test.js` 12 arms — both run for this pass, 39 passing, 0 failing. (`SAIRN-OPEN-WORK-INDEX.md:176` says 19 for the first; it was 19 when written and the suite has grown. Counted, not quoted) |
| Independent review | **Twice, and both findings are now CLOSED.** Hank's review (`ce7764fa`, `tests/dnt_rollup_review_probe.js`) found 2 real findings; both were fixed and discharged in `91618cc6` — **which landed 40 minutes after this pass read the file, and is corrected here rather than left standing.** The suites are 27/27 and 12/12. None of it touches reachability |
| **Caller** | ~~**NONE.** `dnt_rollup` appears **0 times** in `sairndental.html` — and 0 times in every `.html` file in the repo~~ → **BUILT 2026-09-18 by `b179d967`. Re-counted at HEAD 2026-10-06: `dnt_rollup` appears 4 times, two of them real.** `sairndental.html:2492` is the read — `var b=await sdnData('read','dnt_rollup',{});` — behind an owner check at `:2485` (`rollup-owner-tools`), rendering into `rollup-tbody` / `rollup-note` / `rollup-disclosure-card`. `:2498` reads `dntLastErrText('dnt_rollup')` so a REFUSAL and an empty practice are told apart on screen rather than both rendering as nothing. `:1122` and `:1141` are comment text recording the gap and the role gate |

~~Beyond the resource name, the app has no vocabulary for the feature at all:
`rollup` × 0, `roll-up` × 0, `cross-location` × 0, `all locations` × 0,
`panel-rollup` × 0, `location_name` × 0.~~

**RE-COUNTED AT HEAD 2026-10-06, and the vocabulary arrived with the caller:**
`rollup` × **41**, `roll-up` × **9**, `panel-rollup` × **1**. Still zero:
`cross-location` × 0, `all locations` × 0, `location_name` × 0 — the panel uses
its own wording rather than the audit's.

~~**The sharpest form of this, and the one I would lead with: of the 25 resources
registered in `api/_resources/sairndental.js`, exactly ONE is never named
anywhere in `sairndental.html`, and it is `dnt_rollup`.**~~ **THAT SENTENCE IS
NO LONGER TRUE AND IT IS THE MOST QUOTABLE ONE IN THE FILE**, which is why it
is struck rather than quietly reworded. **Re-run at HEAD 2026-10-06 as a whole
set, not as a spot check:** `api/_resources/sairndental.js` now registers **28**
`dnt_*` names (not 25 — three were added since), and **0 of the 28 are
unnamed** in `sairndental.html`. The METHOD is left on the record because the
method is what
was worth keeping — a whole-set comparison rather than a search for a string
somebody expected to be missing, with the other 24 appearing, so it was proven
to find them when they are there. Every `dnt_` resource name in the app is a
**literal**; none is built by concatenation, so a name search cannot miss one
that is present. `tools/sairn_reachability_probe.py` is the standing form of
that method.

**The panel census cannot see this, and that is the whole reason the
caller-level check exists.** SAIRNdental was **22 panels / 22 nav targets / 22
sidebar ids, three identical sets** — no unreachable panel, no orphan nav
target, no sidebar id without a panel. The roll-up was missing from all three,
so a census that compares them to each other reported clean.

> **TENSE CORRECTED 2026-10-06 (Fourth) and the argument is UNAFFECTED.** The
> roll-up is now in all three (`panel-rollup`, `sairndental.html:2485`
> onward). The paragraph above is past tense now because the *claim about the
> census* is what was worth keeping: a census that compares three sets to each
> other cannot see a capability absent from all three, and that is still true
> of every app. Changing the verb rather than deleting the paragraph, because
> the method critique is the durable half.

### 0.1 Where this differs from SAIRNmechanical, and it matters

SAIRNmechanical's `eligibility` defect had a **claim on screen**: a panel
subtitle told a dispatcher *"the record dispatch eligibility is computed from"*
while nothing computed it. `sairndental.html` made no cross-location claim
anywhere — it could not, having no vocabulary for the feature. **As of
`b179d967` it has both the vocabulary and the screen, so this contrast is
historical; re-counted 2026-10-06, `rollup` × 41.**

**So the claim is not in the product. It is in the records the platform keeps
about itself**, which is a quieter place for it and a worse one, because those
records are what the next session reads instead of the code:

* `docs/SAIRN-OPEN-WORK-INDEX.md:176` — *"**BUILT 2026-09-15 (Fourth)**"*, listing
  the lib, both suites, the registration and the tier. No panel, no caller, and
  nothing saying there isn't one.
* `docs/CRITICALITY-TIERS.md:222` reasons about a practice-group owner reading
  per-office production. **No such reader exists**; there is no screen that
  produces that report.

A status row that says BUILT for something no user can reach is the same defect
as a subtitle that says computed for something nothing computes. It is the
`logDoseAudit` shape the mechanical document named, one layer out.

### 0.2 The half that IS reachable, stated so this is not read as worse than it is

**Per-office figures are not unobtainable to a customer** — they are obtainable
without the safeguards. `api/_lib/dental-bi.js` exports `location_id` as a
column on **six** of its datasets (`:176`, `:199`, `:216`, `:271`, `:311`,
`:327`), with `:213` noting the value is *"stamped server-side by
dnt-location.stampLocation on write"*. A practice group with Power BI, Tableau
or Looker can therefore group production by office today, through B5, which
shipped and is wired.

What they would not get is `dnt-rollup.js`'s four rules — the UNASSIGNED bucket
held out separately, the unregistered-office bucket, the refusal to print a
number when a table could not be read. Those exist precisely because the naive
aggregation is the dangerous one. **The careful path is the unreachable one.**

I checked the obvious alternative and it is not the answer: `dnt_rollup` is not
consumed by the BI feed either. It appears only in `api/sd-data.js`, its two
test suites, `tests/dnt_rollup_review_probe.js` and the resource registry.

### 0.3 What I am NOT claiming

**Not that the code is wrong.** It is careful, owner-gated, reviewed twice, and
its two review findings were about null-vs-zero precision, not about
reachability — and both were closed in `91618cc6` while this document was being
written. Nothing here re-opens them, and the correction is recorded rather than
silently applied, because "two open findings" is exactly the kind of tense a
status document gets wrong by being right at the moment it was read.

**Not that a panel was forgotten rather than deferred.** I looked for a written
deferral and found none — `rollup` and `roll-up` appear **0 times** in
`SAIRN-BACKLOG.md`, and the write-half's own NOT-IN-SCOPE list in
`api/_lib/dnt-location.js` names *"a client-side location selector"* as
buildable-later, which is the closest thing to a record and is about a selector
rather than this report. **Absence of a note is not proof of oversight**, which
is why this is filed as a finding to decide rather than a defect to fix: either
the panel is the missing half, or the deferral is real and unrecorded. Both need
a sentence; neither has one.

---

## 1. The 2026-08-26 audit rows, re-derived

Status column inherited from `docs/2026-09-02-competitive-gap-status-rederived.md`
and re-checked against HEAD, 15 days later.

### 1.1 Tier A

| # | 09-02 verdict | At HEAD, 2026-09-17 | Evidence |
|---|---|---|---|
| **A1** real-time insurance eligibility | OPEN | **holds** | `eligibilit` × 4, hand-read: 2 × `gfeEligibility` and 2 × the element id `gfe-eligibility` (`:760`, `:4610`). All four are No Surprises Act, none is payer eligibility. **The spelling of the hits changed since 09-02 and the verdict did not** — worth noting, because a count that moved from "4, all gfeEligibility" to "4, two of them bare `eligibility`" is exactly the shape that gets mistaken for a build |
| **A2** X12 837D / 835 ERA | OPEN — vendor-blocked | **holds** | `837` × 0, `x12` × 0, `clearinghouse` × 0 in the app. The 3 `835` and 1 `x12` hits across `api/dnt-*.js` and `api/_lib/d*-*.js` are substring noise — `sd-data.js:8352` line references and a test fixture DEA number `BX1234567`. **This is the 08-26 audit's own §6 trap reproducing exactly**, where a naive `ERA` grep returned 130 hits |
| **A3** clearinghouse connection | OPEN — vendor-blocked | **holds** | Same zero, same gate |
| **A4** CDT annual code maintenance | BUILT | **holds, and HARDENED since** | `cdt_version` × 12. `a8fe1485` (Fourth, today): *"the CDT catalogue was versioned and the charges were not — a posted charge re-read whatever the catalogue said today"* |
| **A5** imaging / CBCT / intraoral | OPEN — vendor-blocked | **holds** | `imaging` × 0, `radiograph` × 0, `cbct` × 0, `intraoral` × 0 |
| **A6** e-prescribing / EPCS / PDMP | OPEN — certification-blocked | **holds** | `prescrib` × 0, `EPCS` × 0, `PDMP` × 0. 21 CFR 1311 identity-proofing is the gate, not the code |
| **A7** good-faith estimates | BUILT | **holds** | `gfe` × 237, `panel-gfe`, `sql/sairndental_gfe_schema.sql` |
| **A8** recall / reactivation | BUILT | **holds** | `recall` × 92, `panel-recall`, `sql/sairndental_recall_schema.sql` |
| **A9** treatment planning | BUILT | **holds** | `txplan` × 42, `treatment plan` × 10, `panel-txplan`, `sql/sairndental_treatment_plans_schema.sql` |

### 1.2 Tier B

| # | 09-02 verdict | At HEAD, 2026-09-17 | Evidence |
|---|---|---|---|
| **B1** enterprise credentialing / payer enrolment | BUILT | **holds** | `payer_enrollment` × 5, `panel-credentials`, and `dnt_credentials: ['evaluate']` is registered **and sent** (`:2621`) |
| **B2** cross-location roll-up | PARTIAL — deliberately deferred | ~~**SERVER BUILT, NO CALLER — see §0**~~ → **BUILT AND REACHED. Closed 2026-09-18 by `b179d967`, re-counted at HEAD 2026-10-06** | The owner-gated panel the §0 recommendation asked for is the one that shipped: `sairndental.html:2485` gates on owner, `:2492` reads `dnt_rollup`, `:2498` distinguishes a REFUSAL from an empty practice via `dntLastErrText`. `rollup` × 41, `roll-up` × 9, `panel-rollup` × 1 — all three were 0 when this row was written |
| **B3** consolidated RCM / denials & appeals | BUILT | **holds** | `appeal` × 67, `panel-denials` |
| **B4** central call centre | OPEN — not recommended | **holds** | `call centre` × 0, `missed call` × 0. The 08-26 audit itself declined to recommend it |
| **B5** open BI / data-warehouse connectors | BUILT (⚠ SQL pending) | **holds; the SQL flag could not be checked — see §3** | `api/dnt-bi.js`, `api/_lib/dental-bi.js`, `panel-bi` × 3, `sql/sairndental_bi_tokens_schema.sql` present |

**Eleven of thirteen rows hold unchanged. One hardened. One moved, and it moved
into a state the status column has no word for.**

### 1.3 Caller-level check on the rest

Both registered extra actions are sent by the app: `dnt_credentials:
['evaluate']` at `sairndental.html:2621`, and `dnt_supplies: ['soft_delete']`.
`dnt_rollup` needs no extra action — it is a plain `read` — which is part of why
it slipped: a check that enumerates `extraActions` and asks "is each one sent"
never looks at it.

**That is a gap in the method I used next door, found by using it here.** The
SAIRNmechanical check keyed on `extraActions` because that is where the
mechanical defect lived. A read-only derived resource with no extra action is
invisible to it. The check that catches both is **"every registered resource,
does any client name it"** — recommended as the replacement, and it is what
found this.

---

> **CORRECTED 2026-09-26 (Cody): B2's remaining half is CLOSED.** See
> `docs/2026-09-26-gap-triage-four-verticals.md` §2.2. This document says B2
> *"needs a decision, not an estimate"* and that *"what must not persist is the
> current state"*. The decision was made and the panel was built:
> `panel-rollup` at `sairndental.html:1136`, with `rRollup()`, an owner-only
> path, and a comment recording that the server is the real gate --
> *"api/sd-data.js refuses dnt_rollup from any role outside
> DNT_MANAGEMENT_ROLES regardless of what this div does."*

## 2. What is genuinely open after this pass

| Item | Why it is open |
|---|---|
| ~~**B2 — the roll-up has no reader**~~ **CLOSED 2026-09-18 by `b179d967`** | The recommendation was *"either a panel (owner-gated, reusing `DNT_MANAGEMENT_ROLES`, ~one screen against an endpoint that already exists and is reviewed) or a written deferral."* **The panel is what shipped**, with the owner gate and the refusal-versus-empty distinction asked for. Confirmed at HEAD 2026-10-06. The row is struck rather than deleted so the prediction can be checked against what happened |
| A1 real-time eligibility | Needs a vendor or clearinghouse relationship |
| A2 / A3 837D, 835, clearinghouse | Vendor-gated. Same relationship |
| A5 imaging / CBCT / scanner | Vendor-gated. **The "only NexHealth" claim is CORRECTED 2026-09-25 (Cody, external research PR #17): DEXIS publishes public API documentation, so NexHealth is no longer the only open documented API here.** Not independently fetched from this clone, so it is recorded as "no longer safe to repeat" rather than as a verified new fact. SAIRNdental is still zero for imaging either way &mdash; the correction moves this from vendor-gated to buildable-in-principle, not to built |
| A6 e-prescribing / EPCS / PDMP | Certification-gated — 21 CFR 1311 identity-proofing and DEA registration |
| B4 central call centre | Not recommended by the audit that raised it |

**Nothing else here is buildable in-house and un-gated.** B2's remaining half is
the exception, and it is a decision rather than an engineering problem.

---

## 3. Limits

* **No live check.** Against the repository at HEAD, not the deployed app.
* **The `⚠ SQL pending a run` flags could not be resolved from the repo**, and
  are carried forward unchanged rather than quietly dropped. Whether
  `sairndental_bi_tokens_schema.sql` has been executed in Supabase is not a fact
  this clone holds; the file's presence is not the same claim.
* **Caller checks are textual, and here the ceiling was measured rather than
  assumed.** "No client names this resource" is a substring search across every
  `.html` file. A caller that built the name by concatenation would pass — so I
  checked: all 53 `dnt_`-prefixed strings in `sairndental.html` are literals,
  and 24 of the 25 registered resources are found by the same search that finds
  nothing for the 25th. A method that locates 24 out of 25 is not failing to
  see the one.
* **Marker counts are a floor.** The roofing pass's §2.2 stands: one hyphen
  produced a false negative there. Every non-zero count in §1 was hand-read;
  every zero is a floor, not a proof.
* **`location_id` × 0 in `sairndental.html` is NOT a finding and would have been
  a false one.** The column is stamped server-side — for this app by
  `api/_lib/dnt-location.js`'s `stampLocation()`, called at `api/sd-data.js:11079`
  and `:11506`; the platform also has `location-scope.js` and
  `roofing-locations.js` exporting a function of the same name, so name the file
  when citing it. The client never writes it. Fourth raised and withdrew exactly
  this today (`4a25a487`): *"A CLIENT-SIDE GREP CANNOT SEE A SERVER-SIDE
  STAMP."* Recorded here so the next pass does not re-raise it a third time —
  and it is the same class of error as the one this document's §0 is about,
  running the opposite way.
* **No code was written and no app file was touched by this pass.**

---

## Re-verified at HEAD, 2026-10-06 (Fourth) — all 14 rows, with every count re-taken

**One row had gone false: B2, which was this document's whole headline.** It
closed on 2026-09-18, the morning after this pass was written, by `b179d967`.
The other thirteen hold. Every count below was taken today against
`sairndental.html` at HEAD, not quoted from above.

| Row | 09-17 verdict | At HEAD 2026-10-06 | What was counted |
|---|---|---|---|
| A1 real-time eligibility | OPEN | **holds** | `eligibilit` × 4, all four `gfeEligibility` / the `gfe-eligibility` element — `:761`, `:4780`, `:4823`, `:4824` |
| A2 X12 837D / 835 ERA | OPEN — vendor-blocked | **holds** | `837` × 0, `835` × 0, `x12` × 0 in the app |
| A3 clearinghouse | OPEN — vendor-blocked | **holds** | `clearinghouse` × 0 |
| A4 CDT annual code maintenance | BUILT | **holds** | `cdt_version` × 12, first at `:3176` |
| A5 imaging / CBCT / intraoral | OPEN — vendor-blocked | **holds** | `imaging` × 0, `radiograph` × 0, `cbct` × 0, `intraoral` × 0 |
| A6 e-prescribing / EPCS / PDMP | OPEN — certification-blocked | **holds** | `prescrib` × 0, `EPCS` × 0, `PDMP` × 0 |
| A7 good-faith estimates | BUILT | **holds** | `gfe` × 237, `panel-gfe`:730, `dnt_gfe`:1802, `sql/sairndental_gfe_schema.sql` |
| A8 recall / reactivation | BUILT | **holds** | `recall` × 92, `panel-recall`:819, `dnt_recall_outreach`:1816, schema present |
| A9 treatment planning | BUILT | **holds** | `txplan` × 42, `treatment plan` × **11** (was 10), `panel-txplan`:881, `dnt_txplans`:1802, schema present |
| B1 credentialing / payer enrolment | BUILT | **holds** | `payer_enrollment` × 5 (`:494`), `panel-credentials`:476 |
| **B2** cross-location roll-up | **SERVER BUILT, NO CALLER** | **CLOSED — the one that moved** | `dnt_rollup` × 4, the read at `:2492`, the owner gate at `:2485`, the refusal-vs-empty branch at `:2498`; `rollup` × 41, `roll-up` × 9, `panel-rollup` × 1, all three previously 0 |
| B3 consolidated RCM / denials | BUILT | **holds** | `appeal` × 67, `panel-denials`:960 |
| B4 central call centre | OPEN — not recommended | **holds** | `call centre` × 0, `missed call` × 0 |
| B5 open BI / warehouse connectors | BUILT | **holds** | `panel-bi` × 3 (`:692`), `api/dnt-bi.js`, `api/_lib/dental-bi.js`, `sql/sairndental_bi_tokens_schema.sql` |

### The whole-set reachability claim, re-run rather than re-quoted

§0's sharpest sentence was *"of the 25 resources registered in
`api/_resources/sairndental.js`, exactly ONE is never named anywhere in
`sairndental.html`."* Re-run today as the same whole-set comparison:

* registered `dnt_*` names: **28** — three more than when that sentence was
  written;
* names absent from `sairndental.html`: **0**.

**Both halves of that sentence moved, and only one of them is the status.**
The denominator changed too, which is the part a re-quote would have missed:
reporting "0 of 25" today would have been right about the finding and wrong
about the set.

### What this leaves genuinely open for SAIRNdental

**Nothing in-house and un-gated.** A1, A2, A3, A5 are vendor-gated; A6 is
certification-gated (21 CFR 1311 identity-proofing and DEA registration); B4
was declined by the audit that raised it. Every BUILT row was confirmed by
locating its identifier at HEAD. That is the same conclusion §0 reached about
the rest of the app — with B2, the one exception it named, now closed.
