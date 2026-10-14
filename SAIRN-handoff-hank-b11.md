# Hank handoff — 2026-10-14, batch b11

Written **before** the report, at a point where nothing is half-finished: all
six items are committed and pushed, `HEAD == origin/main` with no divergence,
every suite this batch owns is green at the published HEAD, and the post-push
live probe ran against production with **`fail=0 couldnot=0`**.

---

## Push state — verified, not asserted

    git fetch -q origin main
    git rev-list --left-right --count HEAD...origin/main   ->  0 0
    git rev-parse HEAD                                     ->  9f488101

**CORRECTED 2026-10-14 (b12 item 1). THIS LINE READ `21dd38d9c778` AND IT NAMED
A COMMIT THAT CANNOT CONTAIN THIS DOCUMENT.** `21dd38d9` was HEAD at the
*instant this file was being typed*, which was true and useless: this handoff
was then committed as `ffb2463a`, so anybody who checked out `21dd38d9` to see
"the state this handoff describes" would get a tree with no handoff in it. A
standing document may not quote a HEAD that predates its own existence.

The three b11 deliverables disagreed and the disagreement was real, not a
typo — all three shas are on `origin/main` and each was accurate at its own
moment of writing:

| file | said | was it true when written | why it is still wrong or right |
|---|---|---|---|
| this handoff | `21dd38d9` | yes, before its own commit | **WRONG, and corrected above** — it predates the file |
| `SAIRN-report-hank-b11.txt` | `ffb2463a` | yes | **RIGHT, and left alone** — it labels that sha as the handoff commit on its own line and says a report cannot carry the sha of the commit that adds it |
| `SAIRN-digest-hank-b11.txt` | `ffb2463a` | yes | **RIGHT, same reason, left alone** |

`9f488101` is b11's last commit — the push gate's own ledger row for the
report/digest commit. The full b11 range is `4c258b04..9f488101`, and
`797c37f2` (the claim release) sits inside it. **Verify, do not trust this
line:** `git merge-base --is-ancestor 9f488101 origin/main`.

No `--force` at any point. **No override of either form was used** — not
`SAIRN_SEED_GATE=off` and not the scoped `SAIRN_GATE_EXEMPT=seed`. Every gate
refusal was satisfied, not overridden; there were five of them and each is
accounted for below. **Re-verify with `git log --oneline origin/main`**: five
sessions push to this branch and these shas are current only as of this
sentence.

| sha | item |
|---|---|
| `e3858f19` | **item 1** — the MAR access grant, and billing out of `family_mar` by default |
| `9841e14a` | **item 2** — the SAIRNvet role matrix, 42 resources |
| `44abebb3` | **item 3** — AI provenance at six client save sites |
| `d6e58c61` | **item 4** — three transports that could reject, and the third state |
| `fe8e6cb7` | four register records |
| `d1997189` | the two regenerated documents, the ledger rows, and arm D1b |
| `c3c38431` | the Tier A obligation, 33 resources, assigned to `fourth` |
| `45ab59d5` | the SQL preflight fix — block 2 creates the audit table before widening it |
| `3c143e1b` | the gate's own ledger row for `d1997189` |
| `a53650cd` | the live probe and every captured red beside its green |

Plus **five merge commits** from `pull --no-rebase` — see *The push* below.

---

## Item by item

### 1. The MAR access grant — DONE, 28/28, and ONE HALF NEEDS SQL

`tests/mar_billing_grant.test.js` is the spec and the brief named its 16 failing
arms as such. **8 passed / 16 failed / 4 unproven → 28 passed / 0 failed /
0 unproven.** Red captured in `docs/hank-evidence/b11/b11-item1-red.log`.

**THE SECURITY HALF IS LIVE WITH THE DEPLOY AND NEEDS NO SQL.** `family_mar`
stops inheriting `ALF_FAMILY_READ_ROLES` and gets its own
`ALF_FAMILY_MAR_ROLES = { owner, nursing }`. That closes **the third door the
same role had found to the same data** — H1 #877 on 2026-10-05 (no caller gate
at all, fixed by inheriting `read`'s set, which is how billing arrived),
`derive_charges` on 2026-10-07 (`7ed27c5e`), and `family_mar` itself.

**THE CONTACT LIST KEEPS BILLING, DELIBERATELY.** Dropping `billing` from
`ALF_FAMILY_READ_ROLES` was the smaller diff and the wrong change: that set also
guards name, phone, email and the consent trail, and a business office that may
not see medication status still has to be able to ring a resident's daughter
about an invoice. The decision was about the MAR.

**THE CAPABILITY HALF NEEDS MICHAEL'S SQL** —
`sql/2026-10-14-hank-b11-mar-grant.sql`, two blocks, each with its verify and
the answer it must give. Until they run, `mar_access_grant` answers **503
NOT_PROVISIONED naming that file** and the three new audit event types are
rejected by the audit table's CHECK. Fail-closed in both directions: the read
path treats an absent grants table as "no grant" and refuses.

A **second grantee bound** was added beyond the spec and it is narrower, not
wider: `ALF_MAR_GRANT_GRANTEE_ROLES = { billing }`, so a grant row written for a
caregiver admits nobody and the hot read path issues no grants query for the
roles that could never hold one.

**Ablated four ways, each layer alone** (`b11-item1-ablation.log`): the role
narrowing → 6 FAIL, the read-time expiry → 1 FAIL (C5), the grantor gate →
3 FAIL, the grantee scoping → 1 FAIL (C6).

`office_manager` added to `sairncare.html` at all three sites in the same
change, with a comment at `:1018` saying out loud that the server mints the role
and **the database may still refuse it 23514** until run-order block 5 is run.

### 2. The SAIRNvet role matrix — DONE, 31/31, NO SQL AT ALL

Per `docs/2026-10-14-fourth-b15-sairnvet-role-matrix.md`. `api/_lib/sv-roles.js`:
one table, 42 rows, one `decide()`, consulted **ONCE** before the read/write
dispatch, same shape as `api/_lib/leg-roles.js`.

**MEASURED before it was built:** `grep -nE "SV_[A-Z_]*ROLES" api/sd-data.js`
returned nothing. A `frontdesk` token read and wrote `sv_soapnotes`,
`sv_labresults`, `sv_surgery`, `sv_imaging` and `sv_invoicing` exactly as the
owner did. Bands verified 23 REGULATED / 4 MONEY / 13 OPERATIONS / 2 REFERENCE
against the spec, and the 42 names reconciled **both ways** against the
handler's own `SV_RESOURCES` dict read out of the source.

**`sv_controlled` IS UNTOUCHED AND ITS ROW IS DERIVED, NOT RE-LISTED** — built
from `api/sv-auth.js`'s `PRESCRIBER_ROLES`, with arm A5 comparing the two role
by role and arm C4 asserting the new pre-dispatch block does not reference
`api/sv-witness.js` at all.

**NO DEPRECATED ROLE EXISTS IN THIS APP**, said rather than assumed: unlike
SAIRNlegacy's `staff`, all six names in `ROLES_BY_APP.sairnvet` are current
roster values, so there is no migration tier and no row carries one.

19 passed / 11 failed → 31 / 0 / 0. **Arm D1 drives all 492
(resource, role, action) combinations** against the table in both directions;
D2 is the control that the table holds both verdicts (374 ALLOW / 130 DENY).
**Arm A6 failed on first run against my own work** — `sv_scheduling`'s `why` was
four words restating the name — which is what keeps that field from being
dormant. Ablated three ways: the role decision → 8 FAIL, the append-only lock →
3 FAIL, the `sv_controlled` message → 1 FAIL.

**Entirely live on deploy.** The vocabulary and the Postgres CHECK already
agree (`api/role-vocabulary-agreement.test.js`).

### 3. AI provenance at the client — DONE, 18/18, NO SQL

The server half landed in b9 and stated its own limit out loud: `ai_source` is a
**claim by the writer**, so "a client that does not stamp it gets no gate". No
production client stamped it on a high-risk resource — a gate **reachable and
never reached**, which no server test can find.

| app | function | resource | tag |
|---|---|---|---|
| sairnmechanical | `saveDoc` | `mech_docs` | `claude:doc-scan` |
| sairnroofing | `saveMeasurementReading` | `rf_photos` | `claude:measurement-photo` |
| sairngrounds | `grdUploadProgressPhoto` | `grd_progress_photos` | `claude:grd-progress-photo` |
| sairnscape | `scpUploadProgressPhoto` | `scp_progress_photos` | `claude:scp-progress-photo` |
| stonedesk | `revSend` + the preview label | `sd_rev_log` (local) | `claude:review-request` |
| sairngrounds | `msbHandleScanResult` | `msb_bottle_scans` | `claude:bottle-scan` |

**`rf_photos` IS THE ONE THAT CHANGES BEHAVIOUR**, not just labelling: it is in
`HIGH_RISK_AI` and carries no `status`, and an absent status is FINAL, so the
server approval gate now fires in production for the first time and sets
`ai_approved_by` ITSELF from the verified session. **Proven live** — probe arm 5.

**THE AUTO-SAVE SITES HAVE NO APPROVER AND DO NOT CLAIM ONE.** All of them save
the moment the model answers, so `aiFooter()` reads *"AI-assisted — not
reviewed"*, which is the true sentence. Arm B1 measures that **no client file
assigns `ai_approved_by` anywhere** across six files.

**`msb_bottle_scans`, THE EXCLUSION-vs-FLAGGED DISCREPANCY, RESOLVED BY READING
BOTH SIDES AT file:line.** `api/_lib/ai-scan-redaction.js:100` excludes it from
REDACTION, reason *"no model prose is stored"* — **true**, and verified at
`sairngrounds.html:4779`: two scalars out of `msbParseScanResult()` (`:4754`)
plus a `note` this app computes at `:4771-4777` from local cost data. Meanwhile
`brand_read` **is** what a model read off a label and the row syncs to the
server at `:4781` with no provenance. **Both sides were right about different
safeguards**; an exclusion from redaction was being read as an exemption from
disclosure. It now carries `ai_source` and **stays out of BOTH risk maps** —
an entry in either would fail `api/ai-safeguards.test.js`'s phantom arm, because
those maps partition `AI_SCANNED_TEXT` and this resource is deliberately
outside it.

**SAIRNfreedom WAS ALREADY DONE IN b9** and is **re-measured rather than redone
or silently skipped**: four `callClaude` sites, four `sfAiLabel` renders,
`ai_source` on `sf_bottle_fills`. Arm D1 is what will notice a fifth surface
added without a label.

Ablated four ways: the stonedesk label → C1, the `rf_photos` stamp → A2 + A5
unproven, the bottle-scan stamp → E3, two identical tags → A5.

### 4. Cody-routed — DONE, 81/81, and HALF THE FINDING IS REFUTED

**REFUTED, with file:line.** *"stonedesk `sdData()` has no 15s abort"* is wrong.
It has carried `signal: sdFetchTimeoutSignal()` since 2026-09-11 —
`stonedesk.html:30084`, with `SD_FETCH_TIMEOUT_MS = 15000` at `:30065`. The
sweep reported "fetch was called with no signal" because
`_sdWriteOk[resource] = false` on `sdData`'s **first line, outside its own
try**, threw before fetch was ever reached. **That arm was a symptom, not a
second finding.**

**CONFIRMED, and the rejections were printed rather than inferred.** Driving the
three real transports against a fetch that never answers:

    sairncare   ReferenceError: alfNote is not defined      (in the catch)
    sairnscape  ReferenceError: scpLastErr is not defined   (in the catch)
    stonedesk   ReferenceError: _sdWriteOk is not defined   (first line)

**The fix is the rule this codebase had already written down and not applied to
itself.** `sdData`'s own catch says it: *"a rejecting transport is the defect
relocated, not fixed: every `await` caller would throw out of its own handler
and skip the toast it exists to show. A failure path that can itself fail is the
shape this session has spent two days on, so it is not left to the reporter
being present."* It guarded its REPORTER for that reason and left its
bookkeeping line outside the guard. All three failure paths can no longer
throw, and in **every case the `return null` is OUTSIDE the guard**, so the
vocabulary each caller is written for is delivered whatever the reporter does.

Calibrated against the 12 apps that already passed: their equivalents are either
pre-stubbed globals or already-guarded reporters. 77 passed / 4 FAILED →
**ALL 81 ARMS PASS (15 apps)**. Ablated: sairncare → 3 FAIL, sairnscape →
1 FAIL, stonedesk → 2 FAIL.

**`api/alf-append-only-read-order.test.js` NOW HAS THREE OUTCOMES.** Its
file-level guards already exited 2 COULD NOT RUN; its per-arm guards did not, so
an arm that could no longer FIND its read printed `FAIL` and exited 1 — the same
answer as "this read has no `order=` clause", sending a reader to the wrong file.
Proven both directions by ablation:

| ablation | before | after |
|---|---|---|
| a pure refactor of the `alf_op_audits` read literal | **FAIL, exit 1** (a false accusation against correct code) | **COULD NOT RUN, exit 2** |
| the `order=` clause genuinely deleted from that read | FAIL, exit 1 | **FAIL, exit 1** |

More than one match is the same third state from the other side. The summary
line carries all three counts because the exit code can only carry the worst.

### 5. Methodology — what was done, and both halves named

* **Every fix is failing-first and the red is captured**, not described:
  `docs/hank-evidence/b11/` keeps the red beside the green for all four items,
  because a green suite proves nothing about what it would have caught.
* **Every fix is ablated against the pre-fix handler**, one named layer at a
  time, measured per ARM rather than per exit code — 15 ablations across the
  four items, each with the arms it alone catches.
* **Over-refusal controls everywhere**: item 1 arms A6/A7 and C4, item 2 arms
  V7–V12 (V12 drives all 42 resources on an owner token), item 3 arms F3/F4,
  item 4 the 12-app calibration, and live probe arms 2, 3, 6 and 7.
* **The live probe prints what it did NOT drive**, so an absence cannot read as
  a pass. See *Live verification* below.
* **The probe writes nothing and that is measured, not hoped**:
  `class=VERIFICATION-READONLY guard=n/a residue=none`. Every arm is a read or
  a request refused before its insert; the three `rf_photos` arms carry no `id`,
  so even the two that pass the AI gate stop at the handler's own validation.
  The one arm that would have needed a write — the `sv_audit_log` append-only
  lock, whose two halves cannot both be proven by a refusal — is unreachable
  because the SAIRNvet demo credential is **DEAD**
  (`docs/2026-09-03-demo-credentials.md:59` and `:250`). So there is no residue
  and no removal SQL to enumerate.

**WHICH HALF OF EVERY CHANGE IS LIVE, AND WHICH NEEDS MICHAEL'S SQL:**

| item | live on deploy | needs Michael |
|---|---|---|
| 1 — billing refused on `family_mar` | **YES**, the whole security half | — |
| 1 — the `mar_access_grant` action | the action, the gate and the refusals, all live and proven | **blocks 1 and 2** of `sql/2026-10-14-hank-b11-mar-grant.sql` before any grant can be written, found or audited |
| 1 — `office_manager` in the SAIRNcare UI | **YES**, the option is offered | **block 5 of the b10 run order** or the INSERT is refused 23514 |
| 2 — the SAIRNvet matrix | **YES, entirely.** No SQL | — |
| 3 — all six provenance sites | **YES, entirely.** No SQL | — |
| 4 — the three transport guards and the third state | **YES, entirely.** No SQL | — |

### 6. Push — DONE, after five refusals and five merges

1. **register feed gate** — four records written (below).
2. **generated-document gate** — `docs/MASTER-PLAN.md` and
   `docs/traceability-matrix.md` regenerated with their own generators (PR §2.5).
3. **Tier A review gate** — 33 resources. Obligation opened and **assigned to
   `fourth`**, naming what to review hardest on each of the three surfaces
   rather than listing the diff.
4. **`tools/sairn_sql_preflight.py`** — `MISSING_TABLE sairncare_audit_log`, and
   **it was right**: that schema file's header has said NOT RUN since
   2026-10-11, so block 2's `alter table` would have failed outright on a clean
   database, **after block 1, half way through a migration**. Block 2 now
   creates the table first and then widens the constraint, correct in both
   worlds.
5. **A `no-defect-record:` sentence** was required twice and given twice with a
   real reason, not a bare refusal.
6. **Five ref-lock / fetch-first rejections.** The gate takes minutes and four
   other sessions push during it. Every retry was **`pull --no-rebase`**, which
   preserves the register records' shas — b10 learned the other way round and
   had to re-seat twice. Two ledger conflicts resolved with
   `python tools/sairn_rebase_resolve.py`, which 3-way merges by the identity
   each ledger declares and stages nothing unless the validator passes.

---

## Live verification — PR §3.2, `fail=0 couldnot=0`

`docs/hank-evidence/b11_live_gate_probe.py`, output in `.out`.

| | result |
|---|---|
| `mar_access_grant`, OWNER session | **403 FORBIDDEN** |
| `family_mar`, OWNER, unknown contact | **404 NO_SUCH_CONTACT** (over-refusal control) |
| `alf_mar` read, OWNER | **200, 2 rows** (regression pin) |
| `family_mar`, NO session | **401 NO_SESSION** (unchanged control) |
| `rf_photos` write, `ai_source`, no session | **403 AI_APPROVAL_REQUIRED** |
| `rf_photos` write, `ai_source` + `status: draft` | **401 NO_SESSION** — the AI gate let it past |
| `rf_photos` write, NO `ai_source` | **401 NO_SESSION** — an ordinary write is untouched |

**Arm 1 is a discrimination, not merely a refusal.** A 400 *"action must be
..."* would mean the dispatcher has never heard of `mar_access_grant` and
nothing of item 1 is deployed. **403 FORBIDDEN** means the action exists, is
registered in `api/_resources/sairncare.js`, is reached, **and** that the
grantor set is `office_manager` and not `owner`. One request, two different
answers.

**Arm 5 is the first time the high-risk AI approval gate has fired in
production.** b9 landed it reachable and never reached.

**What the probe did NOT drive, printed by the probe itself:** the entire
SAIRNvet matrix and the `sv_audit_log` lock (the demo credential is dead); the
billing refusal on `family_mar` and the grant-then-read flow (need `billing`
and `office_manager` credentials that do not exist on `ALF-TEST-2026`, and a
probe does not mint credentials); the three client-side transport guards (no
HTTP request can reach them); the COULD NOT RUN third state (a property of a
checker); and both SQL blocks.

---

## Open, with the exact next step

1. **`sql/2026-10-14-hank-b11-mar-grant.sql` HAS NOT BEEN RUN — neither block.**
   Until it does, `mar_access_grant` answers 503 NOT_PROVISIONED naming the
   file, and the three audit event types are rejected by the table's CHECK so
   `writeAuditLog` returns false and logs nothing. **Next step: Michael runs
   block 1, reads BOTH its verifies against the expected answers printed beside
   them, then block 2 and its THREE verifies.** Block 2 must be pasted whole —
   between its DROP and its ADD the audit table accepts any `event_type`. A
   clean Supabase run is not evidence; the verify's answer is.

2. **`sql/2026-10-14-michael-run-order.sql` BLOCK 5 IS STILL UNRUN** and
   `sairncare.html:1018` now offers `office_manager` in the owner's
   provisioning picker, so the failing path is reachable from the UI today: the
   server mints the role, the database refuses the INSERT 23514, and the save
   fails rather than validating. **Next step: Michael runs block 5.** This is
   b10's open item 1 unchanged, now with a UI that can reach it.

3. **`tests/sd_data_family_mar_gate.js` IS 9 PASSED / 1 FAILED AND THE FAILING
   ARM CANNOT BE SATISFIED ALONGSIDE THE b11 SPEC.** Arm C1 is a source pin
   requiring `ALF_FAMILY_READ_ROLES` to appear inside the `family_mar` gate;
   arm A9 of `tests/mar_billing_grant.test.js` requires the opposite. The only
   resolution that satisfies both is dropping `billing` from
   `ALF_FAMILY_READ_ROLES` itself, which would also take away the business
   office's facility-wide contact-list read — a wider change than the decision
   covers. **All nine behaviour arms are green.** `tests/` is cody's. **Next
   step: cody re-aims C1 at `ALF_FAMILY_MAR_ROLES` and updates the
   `docs/known-red-suites.json` row.**

4. **NOTHING INVOKES THE TWO NEW SUITES.**
   `api/sd-data-sv-role-matrix.test.js` and
   `api/ai-provenance-client-sites.test.js` are referenced by no file under
   `tools/`. **`tools/` is cc's, so this is routed, not done** — and cc's b11
   claim already covers wiring hank's four b10 suites into the gate driver, so
   this is two more for the same change. **Next step: cc adds both.**

5. **THE SAIRNvet SPEC'S TWO STRUCTURAL `[CONFIRM]`s ARE IMPLEMENTED AS THE
   SPEC'S OWN PROPOSED ANSWERS AND NEITHER IS SETTLED.** (a) does `manager`
   read clinical records — spec'd read-yes/write-no, which the spec itself calls
   *"the one most likely to be wrong"*; (b) may a `tech` record a
   controlled-substance administration — spec'd NO, and **changing it is a
   legal reading, not a preference**, because in many states a technician
   administers under direct supervision and the record is the technician's.
   **Next step: Michael or a practitioner confirms, before any real practice is
   provisioned.**

6. **FOUR TIER-A SAIRNvet RESOURCES ARE BANDED OPERATIONS AND THE SPEC FLAGS
   EACH.** `sv_boarding`, `sv_multisite`, `sv_portal`, `sv_reminders`. A client
   portal and an automated reminder both touch client-visible data, and if
   either SENDS on the practice's behalf it may belong in a narrower band —
   OPERATIONS currently gives every role read **and write**. **Next step: the
   same practitioner question as item 5.**

7. **AN OBSERVATION FOR A HUMAN, NOT A CODE FAULT.** `sv_staff` is banded
   OPERATIONS, so a `frontdesk` token writes the staff roster as app data
   (shifts, contact details). The CREDENTIAL roster is a different surface —
   `api/sv-auth.js`'s `roster` action behind `MANAGEMENT_ROLES` — and is
   unaffected. Correct if the whiteboard-style roster is genuinely shared; a
   hole if the app's staff panel carries anything personnel-grade. **Next step:
   read `sairnvet.html`'s staff panel against that row before a real practice
   uses it.**

8. **THE SWEEP'S HAND-WRITTEN SCAFFOLDING LIST HAS ROTTED AND IT IS NOT MINE TO
   FIX.** `tests/faults/transport_timeout_sweep.js` pre-stubs `_sdReadFailed`
   and `_sdLastStatus` but not `_sdWriteOk`, and knows nothing of `alfNote` or
   `scpLastErr` — globals these three transports gained after the list was
   written. Its reactive `__stub` loop cannot help, because `within()` RESOLVES
   with `{rejected:true}` instead of rejecting, so the *"X is not defined"*
   retry never sees it. **Twelve apps pass partly by that list's grace.**
   `tests/` is cody's. **Next step: cody either stubs reactively on a resolved
   rejection or derives the scaffolding from the transport body it already
   extracts.**

9. **THE SAIRNvet DEMO CREDENTIAL IS DEAD AND THAT IS WHY A 42-RESOURCE MATRIX
   IS SUITE-VERIFIED ONLY.** `SV-PINNACLE-2026` / `38471260` answers 401
   INVALID_CREDENTIALS (`docs/2026-09-03-demo-credentials.md:59`, `:250`). Not a
   gap in the probe — there is no session to be had, and minting one is a
   credential-row write. **Next step: whoever owns demo credentials re-seeds
   SAIRNvet, after which the role matrix's refusal half and the `sv_audit_log`
   append-only lock become drivable live.**

10. **TWO WEAKENING LEDGER ROWS, ANSWERED DIFFERENTLY ON PURPOSE.**
    `api/sd-data-sv-role-matrix.test.js` — the flag was RIGHT that D1's label
    made a claim about an exemption and nothing checked it; **answered with new
    arm D1b**, which drives the WRITE half of both excluded resources for all
    six roles and asserts the role table still governs them. The exclusion is
    from the SWEEP, whose comparison a second control would spoil, and never
    from the policy. `api/ai-provenance-client-sites.test.js` — **REBUTTED, not
    changed**: the quoted detail is a comment sentence, nothing in that file
    skips or allowlists anything, and arms E1/E2/E3 assert both sides of
    `msb_bottle_scans` at file:line. **Next step: whoever signs the ledger off
    reads this paragraph and the two arms.**

11. **SEVEN FILES IN THIS BATCH HAVE NO FMEA DRAFT** and the loop named them:
    `api/_lib/sv-roles.js`, `api/_resources/sairncare.js`,
    `api/sd-data-sv-role-matrix.test.js`,
    `api/ai-provenance-client-sites.test.js`,
    `api/alf-append-only-read-order.test.js`, `sairnroofing.html` and the three
    new `sql/` files. `tools/fmea_draft.py` is cc's. **Next step:
    `python tools/fmea_draft.py <file> --save` for each, by whoever owns
    `tools/`** — and cc's b11 claim already covers exactly this for six hank
    files.

12. **THE SEAM CHECK SAID COULD NOT TELL on at least one endpoint/engine pair**
    and the push was allowed on that basis. Not a regression and not progress.
    **Next step: `python tools/sairn_seam_check.py` by whoever owns it.**

---

## Register

Four records, each with four contributing factors and an explicit
recurrence-open:

| sha | app | severity | method | rule |
|---|---|---|---|---|
| `e3858f19` | sairncare | **critical** | independent-review | 1.7 |
| `9841e14a` | sairnvet | **critical** | independent-review | 1.7 |
| `44abebb3` | sairnroofing | high | independent-review | 1.11 |
| `d6e58c61` | stonedesk | high | fault-injection | 1.11 |

`python tools/defect_register.py --check`: **OK, 574 records**, every commit
resolves and every field is in vocabulary.

**The FMEA loop is recorded in BOTH directions rather than only the flattering
half.** PREDICTED on `api/sd-data.js` for both role records (rule 1.7, from
`docs/fmea/api_sd-data.js.json`). **MISSED** on `sairncare.html`,
`sairngrounds.html`, `sairnmechanical.html`, `sairnscape.html` and
`stonedesk.html` — drafts predate those records and none cites 1.11.

---

## Claims held

**`sairn-api-sql`, claimed as the first action of this batch, still held as this
is written.** Released as the last action, after the final push.

**Conflicts declared and NOT overridden:**

* **`tests/` is cody's** — every file there was **read, never edited**,
  including `tests/mar_billing_grant.test.js` (the spec I was sent to satisfy),
  `tests/sd_data_family_mar_gate.js` (the one arm this batch leaves red, routed
  in open item 3) and `tests/faults/transport_timeout_sweep.js` (whose rotted
  scaffolding is routed in open item 8).
* **`tools/` is cc's** — no file under it was edited. Two routed items.
* **`docs/` specs are fourth's** —
  `docs/2026-10-14-fourth-b15-sairnvet-role-matrix.md` and
  `docs/2026-10-14-ai-safeguards-spec.md` were read and not edited.
* **No auditor clone was entered.**

**Deviations from the claim's FILES list, stated rather than hidden.** The claim
declared `api/`, `sql/` and eight app HTML files plus my own root artifacts.
Beyond those I wrote four `docs/` files that the **push gate itself requires**:
`docs/defect-density-register.json` (the feed gate),
`docs/MASTER-PLAN.md` and `docs/traceability-matrix.md` (regenerated by their
own generators), `docs/tier-a-reviews.json` (the Tier A gate),
`docs/scrutiny-flags.json` (written by the gate when it grades a commit), and
`docs/hank-evidence/b11/` (my own evidence directory). `sairnvet.html` was
declared and **not** edited — the matrix needed no client change.

---

## Hooks and settings

**No hook was restored or added, and `.claude/settings.json` was never
committed by this session.** `stash@{0}` (`b10-settings-park`) was **left
untouched and not popped**, as instructed — confirmed by never running
`git stash` at all in this batch. `.claude/settings.json.bak` and
`.claude/settings.json.hooks.bak` are untracked and were left alone.

**Neither override form was used.** `SAIRN_SEED_GATE=off` was never typed; the
scoped `SAIRN_GATE_EXEMPT=seed` was never typed either.

---

## Transcript

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\6412a39c-c2ab-47d2-8e18-c725548a950f\

Scratch artefacts there, not committed: `reg_b11.py` (the register-feed script,
which is how the four records were written and is the thing worth keeping if one
needs re-adding), `probe4.js` and `driveCtx.js` (the read-only reproduction that
PRINTED the three transport rejections instead of inferring them — this is the
one that turned a routed claim into a diagnosed cause), and the per-item red,
green and ablation logs, all of which are **also committed** under
`docs/hank-evidence/b11/`.
