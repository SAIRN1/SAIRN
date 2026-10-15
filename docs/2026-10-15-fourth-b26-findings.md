# fourth b26 — a paid period can be silently unfrozen, an adjustment can be negative, and the census stopped drifting

**2026-10-15.** Every figure names the command that produced it. **Measured at
`ceea750d`**; re-derive anything you mean to quote, including out of this file.

**THE TWO THAT MATTER, both driven end to end through the real handler:**

1. **A PAID PERIOD CAN BE SILENTLY UNFROZEN BY ANY MANAGEMENT ROLE**, through
   the generic `sen_settings` key path, with the prior list overwritten and no
   record that it ever existed. The next pay run then reports $100.00 for a
   period already paid at $80.00. §1.3
2. **AN ADJUSTMENT CAN BE NEGATIVE** — a downward approved correction deducts
   from a later period's wages with no notice. §1.2

Both are the rules Michael asked me to decide, and both are violated as shipped.

---

## 1. ITEM 1 — THE TIER A REVIEW OF `a1c22397`, DISCHARGED

Seven Tier A resources, three changes. Full verdict on the record in
`docs/tier-a-reviews.json`. Driver `<scratchpad>/b26_freeze_drive.js` → `.log`,
five sections against a **COPY** of `api/` in a tempdir; the live tree was never
written. Ablation `<scratchpad>/b26_lock_ablation.py` → `.log`.

### 1.1 Change (3) first, as instructed, because it is settleable mechanically

**The `law_trusttx` arm is STRICTLY STRONGER and I checked the assertion, not the
description.** The old arm asserted all three roles could read the IOLTA trust
ledger — a **stale expectation**, not a defect: `api/_lib/law-roles.js:87` gives
`paralegal: ''` and `:52-55` hard-locks it. All citations verified by reading.
Arms 3a/3b/3c cover **four** independent failure modes where the old arm covered
one and covered it wrongly — a 401 fails on the status assertion (asserted
first), a 403 from another cause fails on the code, a refusal leaking an empty
`data` array fails the third assertion, and the degenerate "paralegal always
refused" cannot pass because 3b and 3c's second half both go red. **Not an
exemption.** `node api/sd-data-law-trusttx-session.test.js` → **EXIT=0, 13/13**.

**403 and not 404 is right, and there is NO independent spec** — the only
document is hank's own handoff, i.e. the same author as the handler. On the
merits the refusal is a policy refusal about an object the caller's own
navigation shows them; 404 would be a lie they can disprove by clicking.

**FINDING H1 — THE TRUST HARD-LOCK IS UNTESTED. 2×2 ABLATION, not an argument.**
`decide()` applies the table FIRST and re-asserts the lock only after the table
agrees, so on the shipped table the lock can never be reached for a paralegal:

| arm | lock | table | result |
|---|---|---|---|
| BASELINE | intact | denies | exit 0, 3a ok |
| ARM B | intact | `paralegal: 'r'` | **exit 0, 3a ok** — the lock alone DOES save a permissive row |
| ARM C | emptied | `paralegal: 'r'` | exit 1, 3a FAIL |
| **ARM A** | **emptied** | denies (shipped) | **exit 0, 3a ok** |

**Delete `LAW_TRUST_LOCKED` entirely and the whole suite stays green.** The one
defence built for the case where the table is wrong has no arm. And
**`law_bankstatements` has no arm at all** in that suite — the other member of
the same lock, rated A on integrity at `docs/CRITICALITY-TIERS.md:425` by the
module's own citation.

**NEXT STEP (hank)**, and `LAW_TRUST_LOCKED` is already exported, so it is two
assertions plus one behavioural arm for `paralegal → law_bankstatements → 403`.
**Then re-run the 2×2: ARM A must go RED**, or the arm still is not testing the
lock.

**Checked and correct, so it is not re-found later:** `decide()` fails CLOSED on
an unknown `law_` resource and returns `NOT_LAW` rather than a decision for a
non-law one. The suite's `NO_ACTIVE_CHECK` console line naming app
`"sairndental"` is the **documented cross-app arm**, not a mapping bug — the
pre-gate runs the active check only when the expected app matches the token's,
because its first version refused employees who were simply in the wrong app,
and the branch's own gate then refuses the mismatch. Arm 4 proves the real path:
403 `CREDENTIAL_INACTIVE`.

**The `sd_hr_*` id-shadow change is CORRECT and it CLOSES a finding of mine.**
`api/sd-data.js:4160` is now `Object.assign({}, x.data, { id: x[cfg.idCol] })` —
the column spread LAST. My b25 LOW asked for `storedBlob(payload, ['id'])`;
hank's answer is better, because stripping `id` from the blob would have been a
correct-looking fix that emptied the identifier off the three sites whose row has
no id column at all — cody's arm Z's exact scenario. **My LOW is CLOSED.**
And **hank's own question is answered**: I widened the consumer universe rather
than accepting his sample. Outside `archive/`, `sd_hr_employees` appears in
`api/sd-data.js`, `api/_resources/stonedesk.js` (a resource REGISTRY, not an id
consumer), `stonedesk.html`, `stonedesk-hr.html` and three test files; the SD_HR
dispatcher map is `app: 'stonedesk'` only, so there is no cross-app id consumer;
and a strict-equality search for a numeric comparison against the HR id in
`stonedesk-hr.html` returns **nothing**. **The two files he measured are the
whole live universe.**

### 1.2 MY DECISION — THE STRAIGHT-TIME FLOOR, AND FINDING H2

**THE RULE: an adjustment line is straight time at the rate in force on the
service date, which is acceptable — BUT AN ADJUSTMENT MUST NEVER BE NEGATIVE.**

Driven, section C, against the real `api/_lib/sen-payroll.js`:

    UPWARD   (clock_in moved 1h earlier) -> adjustment_cents= 2000  delta=[ 60]  total_payable_cents= 2000
    DOWNWARD (clock_in moved 1h later)   -> adjustment_cents=-2000  delta=[-60]  total_payable_cents=-2000

`b.adjustment_cents += dCents` has no sign guard and
`total_payable_cents = gross + b.adjustment_cents`. **So a scheduler approving a
downward correction silently deducts $20 from a later period's wages.**

**THE RATIONALE, because the decision was asked for and not just the rule.** An
adjustment line exists to **pay** for work already performed and underpaid. A
negative adjustment is not an adjustment; it is a **wage deduction to recover an
overpayment**, which is a separate regulated act with its own conditions — an
employer may recoup an overpayment under the FLSA but not where the deduction
takes a workweek below the minimum wage, and many states additionally require
the employee's written authorisation. **A payroll run must not perform one as a
side effect of an approval, in a period the employee has not been told about.**
It is also the mirror of the harm F1 closed: F1 was sixty minutes unpaid by
omission; this is sixty minutes removed by commission, which is worse because
somebody chose it. And it violates Michael's rule literally — the later period's
own work is paid at gross **minus** 2000 cents, which is below straight time for
that period.

**NEXT STEP (hank):** floor `adjustment_cents` at 0 per visit; surface the
negative deltas as their own `overpayments[]` list carrying employee, visit,
service date, minutes and cents, requiring a human act and **never netted into a
payable total**. The invariant worth an arm is then
`total_payable_cents >= gross_cents`.

**THE FLSA PREMIUM GAP STAYS A DISCLOSED FLOOR, WITH ONE CONDITION.**
`not_computed[5]` names the class correctly; it does not name the caregiver.
Flagging does **not** require reopening the frozen week — the as-paid weekly
minutes are already in hand on the frozen run — so each adjustment should carry
`premium_may_be_owed` when the as-paid week was at or over the threshold or the
delta crosses it. **A disclosure that names a class is a note; a flag that names
a person is payable.**

### 1.3 MY DECISION — THE REOPEN RULE, AND FINDING H3

**THE RULE: a paid period is reopened only by an APPENDED correction record.
Never a silent replace.**

`payroll_closed_periods` lives as **one `sen_settings` row**
(`api/sd-data.js:7755-7757`, read-only there and never from the payload — that
part is right). But `sen_settings` has a generic WRITE path at
`api/sd-data.js:8282` which requires only
`senAuth.MANAGEMENT_ROLES[session.role]` — `{owner, billing}`, and **`billing`
is also the role that runs payroll** (`api/sd-data.js:7710`) — validates **only**
`evv_config` and `agency_profile`, says so in its own words (*"Unknown keys are
stored as-is — this is a settings store, not a schema registry"*), and upserts
`on_conflict=license_hash,setting_key` with `resolution=merge-duplicates`, i.e.
**a full REPLACE of that key's `data`**.

Driven, section A, through the real handler with a real signed session:

    stored before : {"periods":[{"period_start":"2026-09-01","period_end":"2026-09-15","paid_at":"2026-09-20T00:00:00.000Z"}]}
    as billing    -> HTTP 200
    as owner      -> HTTP 200
    stored after  : {"periods":[]}
    rows carrying the key: 1   (an APPEND would leave 2+; a REPLACE leaves 1)

And section B is the consequence, the same payroll run twice:

    closed_periods = the real one -> HTTP 200  period_closed={...paid_at...}  minutes=240  gross=8000
    closed_periods = EMPTIED      -> HTTP 200  period_closed=null             minutes=300  gross=10000

**THE WHOLE CHAIN: a billing session POSTs one settings row, gets a 200, and the
next pay run reports $100.00 for a period already paid at $80.00, with
`period_closed: null` stating that nothing is frozen — and no record anywhere
that the list ever contained anything.** `updated_by`/`updated_at` sit on the
single row the next write overwrites.

**THE RATIONALE.** The freeze exists so a paid figure is REPRODUCIBLE. A control
erasable by the same role that runs payroll, through an endpoint whose own
comment disclaims validating it, with the prior value overwritten, is not a
control — it is a convention. **And it defeats the mechanism's own safety
argument in its own words:** the 503 on an unreadable list exists because
treating it as empty *"would silently UNFREEZE every paid period and restate
history"*. The code refuses to do that by accident and permits it on purpose.
Direction is not the point either — the same write can move `paid_at` later so an
owed adjustment vanishes, or shorten a period so part of it unfreezes.

**NEXT STEP (hank), a schema decision rather than a patch:** refuse the
`payroll_closed_periods` key explicitly at the generic path (a **named** refusal,
not an allowlist the next payroll control also misses); give it its own
**append-only** resource, one row per closing, never updated and never deleted —
the shape `leg_custodylog` already has and `api/_lib/leg-roles.js` already models
— with the read unioning them; and make a REOPEN a new appended row referencing
the closing it reverses, with a reason. **Until that exists this gap is open and
the freeze must not be described to an agency as a guarantee.**

### 1.4 hank's remaining questions, answered from measurement

**Q1 the undatable approval — his reasoning holds, and I checked the PREMISE
rather than the conclusion.** Driven, section E:

    the CLOSED period itself -> minutes=300 gross=10000 adjustment_cents=0 undatable_corrections=1 adjustments=0
    a LATER open period      -> minutes=0   gross=0     adjustment_cents=0 undatable_corrections=1 adjustments=0

**No double count** — it applies once, in the closed run, and posts no adjustment
anywhere. And the reason is **structural, not a counterfactual about history**:
`proposeCorrection` writes `approved_at_server: null` **with** a status
(`api/_lib/sen-evv-clock.js:290`) so a pending entry is not approved;
`approveCorrection` stamps a real instant (`:349`); and `clock_corrections` is in
**neither** `sen_visits` payload allowlist, which I established in b25. **So an
undatable approved entry can only be a legacy row**, provable from the writers
rather than from the past.

**Q4 the straddling run — the hazard is REAL and nothing discloses it.** Driven,
section D, one visit inside the closed period and one after it, run
2026-09-10→2026-09-25 across the closed end 2026-09-15:

    period_closed = null
    minutes=480  gross=16000  adjustment_cents=0
    not_computed entries: 7, and NONE of them mentions a straddle

The **per-visit freeze is the safe half and it worked** — the corrected visit
contributed its as-paid 240, not its corrected 300, so 480 and not 540. **The
LABEL is the unsafe half**: `period_closed: null` says nothing in this total is
frozen while half of it is. **NEXT STEP:** a third state — `null` only when no
visit in the run was frozen, and a `partially_closed` naming the overlapping
closings otherwise.

**Q5 the 503 direction — CORRECT, and I am not splitting it.** Treating a failed
read as "nothing is closed" unfreezes every paid period and restates history,
which is unrecoverable; refusing a pay run on a settings blip is recoverable. The
asymmetry is the whole argument.

**Q(b)2 — MICHAEL'S SAME-CLOCK DECISION IS NOT FULLY IMPLEMENTED.**
`api/_lib/sen-evv-readiness.js:339-340` calls `effectiveClock(v, field)` — the
**no-as-of form**. So for an OPEN period EVV and pay agree, and **for a CLOSED
period pay reads as at `paid_at` while EVV reads NOW**. `effectiveClockAsOf`
already exists, so the gap is threading the as-of through, not building anything.
**Reported, not decided by me** — this is the shape of Michael's decision.

**Q(b)1 a corrected clock-out with no GPS now surfaces as a GPS exception.**
hank is right that it is correct and right that it changes what a surveyor sees.
I agree with the direction. **Not a finding.**

**Q(c) the purity question — THE HEADERS ARE NOW MISLEADING, AND THAT IS THE
DEFECT, not the `require()`.** One copy of the approval rule beats three and
`sen-evv-clock.js` is itself pure. What is not defensible is two headers still
claiming purity when the claim was doing two jobs — no I/O, and no dependencies —
and only one is still true. hank's own line that not editing them "may itself be
the defect" is correct; it is. **NEXT STEP:** say what they now mean.

**The throw question:** his F17 arm over 15 hostile shapes is good and the reason
it exists — no per-visit `try/catch`, so a throw fails the run for every
caregiver — is right. **His caveat stands and I am not upgrading it:** 15 shapes
are not a property.

---

## 2. ITEM 2 — THE 22 RE-DERIVED, AND THE TEN BLOB CONVERSIONS AS A CHANGE

**THE 22 IS STILL 22**, at `ceea750d`, 18,867 lines — the file grew by about 100
lines since b25's 18,769 and **the count did not drift**. The citations moved
(+24 on the early ones, +98 on the later):

    :2668  :3230  :3591  :4176  :4240  :4489  :4571  :4646  :8328  :9126
    :9321  :10650 :10797 :10996 :11115 :11285 :11362 :11613 :11692 :13757
    :13888 :14445

**AND A 23rd WRITE-GUARDED GUARD IN A SHAPE NOBODY COUNTED — `:15150` — WHICH IS
NOT A DEFECT.** It is neither the helper nor a bare inline 503 nor a 200-empty,
so it lands in the census's `other` bucket; its own comment names 23505 / 23502 /
23503, says *"the table EXISTS and refused this row"*, and is **deliberately
scoped to that branch**. So it is the one write-guarded branch that already
distinguishes the integrity class. Reported because a count of 22 beside a bucket
of 23 invites exactly the 25-vs-22 mistake again.

**HANK'S TEN BLOB CONVERSIONS (`8627f4e4`) — CORRECT, AND NO DATA LOSS.**
`storedBlob(payload, columnKeys)` copies `payload`, deletes `columnKeys`, then
deletes `NEVER_STORED` (`api/_lib/blob.js`). So `storedBlob(payload, [])`
narrows by **exactly the three scope keys and nothing else** — every other key is
stored as before. **The nine empty column lists are RIGHT rather than an
omission**, and stripping a mapped column would have been cody's arm-Z defect.
The one non-empty list, `['shop_id']`, is right too **and loses nothing**: the
read selects `data,shop_id` and returns `flat(row.data, { shop_id: row.shop_id })`
(`:2339`, `:2343`), and the write echo does the same (`:2355`). `storedBlob`
mutates a **copy**, so `payload.id` is still readable by the same object literal
that calls it.

---

## 3. ITEM 3 — (d) `LATE_REPLAY`, DRIVEN LIVE AT LAST

b23 read it; **b24 and b25 both left it as read-only evidence** and b23's own
verdict named it its weakest-evidenced item. Four writes in sequence against one
persistent row through the real handler
(`<scratchpad>/b26_late_replay_drive.js` → `.log`). All four properties hold:

1. an 8-day-old clock-in raises `LATE_REPLAY` and it is **STORED**, not only
   returned;
2. a later write on the **other** clock field does not erase it — and the
   **both-flagged** case is the discriminating one, which is the one driven,
   because the code's own comment says the pre-2026-10-14 bug *only showed when
   both halves were flagged* and a clean clock-out let the flag survive by luck;
3. **the T16 refinement holds**: a re-sent immutable clock field lands as a
   **pending correction**, the row keeps the original, and the original's
   `LATE_REPLAY` is **KEPT**;
4. a write mentioning no clock field keeps every flag untouched.

**ONE FIXTURE CORRECTION DISCLOSED:** the first draft moved `clock_in` to NOW,
which inverts the visit, and the handler refused it `400 CLOCK_OUT_BEFORE_IN` —
correct behaviour, and it meant arm 3 never ran. Corrected to +30 minutes and
re-driven. **An arm that was refused before it reached its subject proves nothing
about the subject** and would have been reported as a pass by its exit code.

---

## 4. ITEM 4 — THE 33 RECLASSIFIED, AND TWO OF MY OWN FIGURES WITHDRAWN

`<scratchpad>/branch_census_b26.py` → `b26_census.log`. 332 guards at 18,867
lines. Shapes: `A-helper` 88, `B-inline-503` 70, `C-200-empty` 151, `other` 23.

**Class B's 46 GET-guarded branches:**

| influence | b23 | b26 |
|---|---:|---:|
| CALLER | 13 | **32** |
| SESSION | — | 1 |
| UNRESOLVED | *(not a state)* | **4** |
| SERVER-ONLY | 33 | **9** |

**CALLER was LOW BY 19 and SERVER-ONLY was HIGH BY 24.**

**AND MY OWN b23 STATEMENT ON THE 151 IS WITHDRAWN.** b23 said *"0 of them
interpolates a caller value, so a caller cannot provoke a non-missing-table 400
on any of them."* The census finds **16 CALLER**, 2 SESSION, **19 UNRESOLVED**
and 114 SERVER-ONLY. So a caller **can** provoke one on at least 16 of the 151,
and the reachability withdrawal I made in b23 was itself too generous.

**SPOT-CHECKED IN BOTH DIRECTIONS rather than trusted** — the b23 lesson is that
an over-reporting predicate is as bad as an under-reporting one:

* `:5120` **CALLER, correct** — `enc(String(payload.id))` is literally in the URL.
* `:15150` **write-guarded, correct, and a true non-defect** (§2).
* `:10556` **UNRESOLVED, correct, and it is the third state earning its keep** —
  `jobId` is a **function parameter** of `rfJobGate`, and its call sites at
  `:10612` and `:10746` pass `payload.job_id`, **so it is CALLER once you go
  inter-procedural.**

**THE LOWER BOUND IS NOT GONE — IT IS NAMED.** 26 enumerated `UNRESOLVED` lines
(4 + 19 + 3) instead of a hidden `else` branch, with one resolved by hand as a
worked example. Closing it fully needs inter-procedural resolution for the
handful of helper arrows; that is routed with the tool.

---

## 5. ITEM 5 — THE METHODOLOGY: THE SPAN RULE IS NOW A FIXTURE

`CRITERIA_VERSION 2026-10-15.b26.1`, **ten fixtures, 10/10**, locked **before**
the real file is read — and the program **exits 2 COULD NOT RUN rather than
reporting a census** if they fail.

Three rules, each with fixtures in both directions: **R1** the span ends at the
next `await fetch(` and never at a line count; **R2** a guard binds to the fetch
that assigned **its own** variable; **R3** a caller value is followed
transitively through assignments **and an unresolvable identifier is its own
third state**, never folded into SERVER-ONLY.

**ABLATION PER ARM, not per exit code:**

    WITHOUT R1 span-bounded-at-next-fetch          1 fixture(s) change  -> GET becomes POST
    WITHOUT R2 guard-binds-to-own-variable         1 fixture(s) change  -> UNCLASSIFIED becomes GET
    WITHOUT R3 follow-caller-through-assignments   3 fixture(s) change  -> all three collapse to SERVER-ONLY

**Every rule is load-bearing**, and removing R1 reproduces the exact 25-vs-22
error while removing R3 reproduces the exact lower-bound error. If a future edit
makes a rule buy nothing, `--ablate` says so **and calls it a finding about the
fixtures rather than a pass**.

**ONE FIXTURE WAS WRONG AND IS DISCLOSED:** the first R1 fixture put the guard
AFTER the upsert, a layout `api/sd-data.js` does not contain, and failed for that
reason rather than because the rule was wrong. It is now the shipped
`:5061-5072` layout with the reason in its own comment.

`tools/` is cc's, so the tool is **routed with its full source inline** in
`docs/2026-10-15-fourth-b26-branch-census-routed-to-cc.md` — because the three
previous censuses each lived in a scratchpad and each rebuild re-introduced one of
the bugs the previous one had fixed. Convention **35** gains one operational
clause rather than a 36th number: **the span rule itself has to be a fixture, not
a sentence.**

---

## 6. WHAT b26 DID NOT DO

* **No live verification.** Nothing ran against a real Supabase, and no agency
  has a `payroll_closed_periods` row — **so the freeze has never run on real
  data by anyone**, which hank says too.
* **No production row read. No table touched. No file written under `api/`,
  `sql/`, `tests/` or `tools/`.**
* **The inter-procedural half of the census.** 26 `UNRESOLVED` lines stand.
* **`law_optx`** is covered only as the control in arm 3b.
* **`sairnsenior.html`** was grepped and read in commit messages, never
  re-extracted block by block and never rendered.
* **The FLSA premium itself is not computed by me.** I accept the floor and
  require the flag; I do not assert what any premium is worth.
* **The one-person-agency self-approval exception** is not reviewed and is not a
  gap — unbuilt by Michael's standing decision, recorded for question H8.
