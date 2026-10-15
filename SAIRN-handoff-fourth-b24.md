# HANDOFF — fourth / ted, batch b24, 2026-10-15

**READ THIS FILE ONLY.** It is the whole state.

**STOPPED AT 71% CONTEXT BY INSTRUCTION.** Items 1 and 2 are complete and
pushed. **Items 3, 4 and 5 are PARKED, not abandoned and not partially done** —
item 3 at a named blocker with a one-line fix identified, items 4 and 5
not-started with nothing half-checked. **Nothing is recorded as verified that
was not.**

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**THREE THINGS TO READ FIRST:**

1. **The leg_aftercare preservation argument does not cover the rows that
   matter.** Both of hank's questions answer **NO**, driven. **F3 reintroduces
   the duplicate grief-support follow-up the deterministic key exists to
   prevent.** §3.
2. **Item 3's blocker is one line:** the driver needs
   `process.env.SD_AUTH_SECRET` stubbed before it signs a session token. The
   harness is written and the two target branches are named. §5.
3. **TWO FRESH OBLIGATIONS ARRIVED DURING THIS BATCH and are assigned to me.**
   Neither is in b24's dispatch; both are untouched. §7.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\578e6f48-a2d0-4543-b65b-e5b79ea4e6c8.jsonl`

**Working files (this session's scratchpad):**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\578e6f48-a2d0-4543-b65b-e5b79ea4e6c8\scratchpad\`
New this batch: `verdict_b24_cody.txt`, `discharge_cody_b24.log`,
`leg_aftercare_drive_b24.js` + `.log`, `cody_probe_b24.log`,
`suite_t16-clock-correction-record_b24.log`,
`suite_t18-positions-vocabulary_b24.log`,
`suite_leg-aftercare-key-unambiguous_b24.log`, `pick_branches_b24.py` + `.log`,
`drive_400_b24.js` + `.log`, `pre_push_tip_b24.txt`, `push_b24.log`.
**Same session as b22 and b23**, so their logs are in the same directory;
b18–b21's are under `b0f8683c…` and are not.

---

## 0. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `339f5c9d` | `git rev-parse --short HEAD` |
| `origin/main` | `339f5c9d` | `git rev-parse --short origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| working tree | **clean at this line**; the deliverables commit after it | `git status --porcelain` |
| push forced? | **NO — PROVED BY ANCESTRY**, not by grepping git's wording | pre-push tip in `pre_push_tip_b24.txt`; `git merge-base --is-ancestor <tip> HEAD` → **ANCESTOR** |
| `SAIRN_SEED_GATE` / `GATE_EXEMPT` / `SAIRN_SKIP` | **none used, any form** | — |
| `.claude/settings.json` | **not edited, not committed** | — |
| hooks | **untouched and never re-added** | by instruction |
| `api/` `sql/` `tests/` `tools/` files written | **0** — all read-only here by claim; every drive ran against a tempdir copy | — |
| files under `.claude/skills/sairn-hover-auditor/` | **0 — neither auditor clone entered** | by claim |
| b24 manifest | **2 `done`, 3 `blocked` with reasons, 1 open (item 6)** | `batch_manifest.py --check --agent fourth --batch b24` |
| discharge verified **on origin** | `cody 01:18:14Z` → `reviewed`, verdict **12,409** chars | `git show origin/main:docs/tier-a-reviews.json` |
| **context now** | **73% of 1000k** | `tools/sairn_status_line.py` on this session's transcript |

**`339f5c9d` IS THE STATE BEFORE THIS HANDOFF** — this file, the report, the
digest, `SAIRN-latest-fourth.md` and the claim release all land after it.

---

## 1. EVERY b24 ITEM — WHAT IS DONE AND WHAT IS OPEN

| # | item | state |
|---|---|---|
| 1 | leg_aftercare Tier A — cody's record + hank's carved-out half | **DONE.** 4 findings, hank's two questions both DRIVEN (§3) |
| 2 | run the three undriven suites | **DONE.** 3 of 3 green, and a fourth suite found at exit 3 (§4) |
| 3 | drive a 23514 through a write branch and a 42703 through a read path | **PARKED at a named blocker** (§5) |
| 4 | re-verify the six still-open findings; drive (d) LATE_REPLAY | **NOT STARTED** (§6) |
| 5 | the predicate-span rule; re-run the 33 server-only GETs with a variable trace | **NOT STARTED** (§6) |
| 6 | push without force, confirm landed | **DONE.** 0/0, ancestry-proved (§0) |
| — | this handoff, before the report | **DONE** |

---

## 2. CLAIMS HELD

| hold | count | detail |
|---|---:|---|
| repo claims held | **1** | the b24 claim. **Release LAST**, after all four uploads verify. **It is NOT being continued** — b24 stops here |
| **Tier A obligations assigned to me** | **2, both FRESH, both untouched** | §7 |
| discharged this batch | **1** | `cody 01:18:14Z`, as the assigned owner, not by `--takeover` |
| `git stash` | **0** | `git stash list` |
| session lock | mine and live; not reaped or removed this batch | |
| status registry row | `working` | **`idle` at release** |

---

## 3. ITEM 1 — WHAT b24 PROVED. Both of hank's questions answer NO.

`docs/2026-10-15-fourth-b24-leg-aftercare-discharge.md`, and the full verdict is
on the discharged record in `docs/tier-a-reviews.json`.
Driven: `node <scratchpad>/leg_aftercare_drive_b24.js` → `…_b24.log`. Both halves
**extracted by text** from the shipped files and run in a `vm` against a fake
`localStorage`. Live tree never written.

**THE DERIVATION HALF HOLDS, and I established it rather than accepting it:**
one creation path with three literal types (`sairnlegacy.html:4302`);
`newId('CS')` is always `^CS-[0-9]+-[0-9]+$` because the random segment is 1–3
digits and the regex accepts any width (`:1561`) — **checked, because a
fixed-width regex would have been the defect**; and both derivations agree on a
shipped pair.

* **F2 — HIGH. Rows written by shipped builds DO change id.** Rows predating the
  deterministic-id change carried `newId('AC')` and never had a derived id at
  all, and `api/sd-data.js:15872-15884` rewrites `payload.id` on **every**
  `leg_aftercare` write carrying both fields. Driven: `SAME ROW? false`.
  **hank's own comment at `sairnlegacy.html:4358-4360` says exactly this.**
* **F3 — HIGH, and it is the duplicate the key exists to prevent.**
  `legAdoptServerId` repairs the local store; **nothing repairs the server.**
  `legServerWinsMerge` (`sairnlegacy.html:5474-5500`) only **adds**. Driven: the
  completed check-in **reappears as a second Pending row** — a duplicate
  grief-support follow-up to a bereaved family, the harm `:4308-4310` names.
  **NEXT STEP (hank): the canonicalising write must DELETE the id it replaced,
  server-side, in the same request.** A client-side delete cannot be trusted:
  the device that would issue it is the one still on the old page.
* **F4 — MODERATE-TO-HIGH. `legAdoptServerId` is a whole-row replace.**
  `keep[at] = mine`, so the canonical row's `notes` and `completed_date` are
  lost on exactly the precondition its own comment names. **Both of its guards'
  controls hold**, so the loss is in the merge and nowhere else. **NEXT STEP
  (hank): the renamed row wins only on the fields THIS WRITE SET** — that list
  is the payload just sent and is not currently passed in. `Object.assign` is
  **not** the fix: `mine` carries `notes:''` as a real value.
* **F1 — cody's. The probe EXITS 3 COULD NOT RUN at HEAD** because hank's fix
  moved its extraction anchor. **It fails closed, which is right** — but ARM 1
  is now **UNRUN rather than RED**, and `docs/known-red-suites.json` still
  records `exit_code: 1` with *"ARM 1 ONLY. Any other failure is NEW"*, a
  sentence that **cannot classify an exit 3**. **NEXT STEP (cody): re-anchor on
  `const acEsc = (s) =>` plus the `acKey` ternary (`api/sd-data.js:15870-15878`),
  re-drive, re-diagnose the register row — and add an arm that FAILS when the
  extraction anchor stops matching**, which the probe's own ARM 2 does for a
  different anchor but not for its own.
* **cody's criticism of E4 is CONFIRMED, not accepted.**
  `api/sd-data-leg-role-matrix.test.js:456-478` — its `cases` list contains both
  `['CS-7','1 Week']` and `['CS-7-1','Week']`, and its only assertion is
  `disagree.length === 0`. **E4 drives the colliding pair and passes, because
  both halves agree on the wrong answer.**

**THE REGISTER CANNOT CARRY hank's CARVED-OUT HALF.**
`tier_a_review_gate.py` has **no `--amend` and no append**, so a record
discharged with a carve-out has nowhere for the carve-out's later completion to
land. It is recorded in the b24 doc and in cody's verdict body instead.
**ROUTED TO cc as a tool gap.**

---

## 4. ITEM 2 — THE SUITES, AND WHAT THEIR GREEN DOES NOT MEAN

Exit code read from `echo "EXIT=$?"` on its own line, never from a pipeline:

| suite | exit | counts |
|---|---:|---|
| `node api/t16-clock-correction-record.test.js` | **0** | 27 passed / 0 failed / 0 unproven |
| `node api/t18-positions-vocabulary.test.js` | **0** | 17 passed / 0 failed / 0 unproven |
| `node api/leg-aftercare-key-unambiguous.test.js` | **0** | 14 passed / 0 failed / 0 unproven |
| `python -u tests/run_b14_leg_aftercare_probe.py` | **3** | **COULD NOT RUN** — F1 |

**THE GREEN IS NOT EVIDENCE AGAINST THE FINDINGS, said rather than left to be
inferred.** The leg_aftercare suite tests the **derivation's** preservation
property, which holds; F2–F4 are about rows whose id was never derived and about
the local merge — **neither is in its scope**. And t16's 27 green arms **do not
cover the payroll consumer**, which is b23's F1 and was driven separately
against the real modules.

---

## 5. ITEM 3 — PARKED, AND THE BLOCKER IS ONE LINE

**The driver is written and it runs:** `<scratchpad>/drive_400_b24.js` copies
`api/` into a tempdir (**never the live tree**), loads the **copy's**
`sd-data.js` with a stubbed `_lib/license` and a PostgREST mock that answers 400
with a real body, and targets two **named** branches rather than line numbers
that move:

* **`alf_op_audits` write** — a **Tier A** resource — for the `23514` / 64 KB-cap
  observation;
* **`mech_site_assets` read** — for the `42703` observation;
* plus a **no-failure control** on both, and a **counterfactual** that rewrites
  the copy's `alf_op_audits` guard to the shipped 3-argument
  `notProvisioned()` call.

**All four sections returned `COULD NOT RUN: SD_AUTH_SECRET not set in
environment`** (`drive_400_b24.log`). **So NOTHING WAS OBSERVED and no verdict
is recorded** — a could-not-run is never folded into a pass.

**THE FIX IS IDENTIFIED:** `api/auth-license-app-scope.test.js:158-176` sets
`process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'stub-secret-for-tests'`
before signing and restores it after. **EXACT NEXT STEP: add that env stub at the
top of `drive_400_b24.js`, before `require`-ing `_lib/auth`, re-run, and record
the four observed answers plus the counterfactual.**

**AND ONE RE-MEASUREMENT THAT CHANGES THE ROUTING:** the class-B write-guarded
population is **25 at this HEAD (18,769 lines)**, not b23's **22 at 18,770**.
`<scratchpad>/pick_branches_b24.py` names resource and action for each.
**The three b23 did not list: `:5062` `grd_progress_photos` write, `:5935`
`scp_progress_photos` write, `:11241` `rf_schedule` write.** **So b23's "22" is
superseded by 25, and the b23 routing list is short by three.**

---

## 6. ITEMS 4 AND 5 — NOT STARTED, NOTHING HALF-CHECKED

**Item 4.** No re-verification was begun, so **none of the six is recorded as
either confirmed or cleared by b24.** All six stand exactly as b23 left them,
with their b23 `file:line` references still the best current pointers: **b18
N1**; **the MAR grant bypass via `alf_clients` with no audit row** (b21 F3);
**the `rf_photos` rebuild dropping `ai_source`** (b21 F4); **`license_hash`
never re-verified in memory**; **no revoke action for a live grant**; and **the
two `sd_photos` caller findings** (b22 F1 the failed-downscale branch storing
*and syncing* the original, F2 the octet-vs-UTF-16 margin). **The (d)
`LATE_REPLAY` item is UNDRIVEN** and is still read-only evidence, which the b23
verdict already names as its weakest-evidenced item.
**EXACT NEXT STEP: re-verify each against HEAD with a fresh `file:line`** —
every one of those citations was taken at an earlier HEAD and `api/sd-data.js`
has moved from 18,503 to 18,769 lines across b22–b24 — **and drive (d) as a
two-write sequence against a COPY of the handler** rather than reading the
superseded-set logic. The `drive_400_b24.js` harness is the right vehicle once
§5's blocker is cleared.

**Item 5.** **The predicate-span rule was NOT written into any standing
document.** It exists only in the b23 report and digest METHOD-NOTE sections.
**The 33 server-only GETs were NOT re-classified**, so **CALLER remains a lower
bound** and b23's UNVERIFIED line saying so is still current.
**One thing this batch did learn and it belongs with that item:** the class-B
count moved 22 → 25 between b23's HEAD and this one, **so a predicate has a SHA
as well as a span and a pattern** — the third clause, and the only one measured
rather than argued.
**EXACT NEXT STEP: write all three clauses into
`docs/2026-09-13-cross-domain-disciplines.md` as one numbered item — count the
`## <n>.` headings first, do not trust any written count — and extend
`<scratchpad>/branch_census_b23.py` to follow a variable back through its
assignments.** The current classifier reads only the fetch expression, which is
why it cannot see a caller value arriving through an earlier variable.

---

## 7. TWO FRESH OBLIGATIONS ARRIVED DURING THIS BATCH — UNTOUCHED

Neither is in b24's dispatch. **Both are mine and both are untouched.** Check
the clock before assuming runway: `tier_a_review_gate.py --list`.

| # | obligation | exact next step |
|---|---|---|
| **1** | `cody 2026-10-15T12:18:41Z` — `quotes`, `sd_hr_certs`, `sd_hr_employees`, `sdn_projects`; `tests/sd_data_blob_scope_ten_routed_sites.js` | A **new failing-first** suite over the ten unconverted stored-blob write sites, three serving Tier A resources. **`sd_hr_employees` and `sd_hr_certs` are PERSON DATA** — read the record's own `what` first, then check the suite asserts the scope property rather than agreement between two copies, which is the defect shape b24 F1 just found in its sibling |
| **2** | `hank 2026-10-15T12:24:35Z` — `leg_custodylog`, `sen_visits`; `api/b14-clock-approval-two-person.test.js`, `api/sd-data-leg-session-gate.test.js`, `sairnsenior.html` | **NO product code changed for `leg_custodylog`** — what changed is the ARM measuring its session gate, which asserted `write with a session -> 200` over a generic loop. **And `sen_visits` is in it, which is where b23's payroll F1 lives** — check the two-person approval arm does not assume `effectiveClock` is applied by payroll, because it is not |

---

## 8. WHAT IS OPEN, BY OWNER

### hank — `api/`

1. **b23 F1 FIRST, and Michael has decided it is a bug:** payroll ignores an
   **approved** clock correction — **60 minutes / 2000 cents unpaid on one
   visit**, driven. Apply `effectiveClock` in the payroll action's map
   (`api/sd-data.js:7678-7679`); do **not** change `SEN_CLOCK_IMMUTABLE`.
2. **b24 F3** — delete the replaced row id server-side in the canonicalising
   write. **b24 F4** — field-merge `legAdoptServerId` on the write's own payload.
   **b24 F2** is the framing both rest on.
3. **The 25 class-B write branches** (not 22 — §5), then b23's 13
   caller-interpolated GETs, then `:13503`/`:17127` by hand, then the read-case
   fifth answer before touching the 151.
4. **Still open and NOT re-verified this batch:** the six in §6, plus b23's F2
   (the EVV readiness raw clock), F3 (the client never reads `effective_clock`)
   and F4 (`alf_staff`'s undecided disclosure), and the status-less-entry write
   guard.

### cody — `tests/`

1. **b24 F1** — re-anchor the leg_aftercare probe, re-diagnose its register row,
   and arm the anchor itself.
2. **A failing-first arm driving a `23514` through one of the 25 and a `42703`
   through one of the 151.** Nothing in the repo drives either today, and b24's
   attempt to **observe** them is parked at §5.

### cc — `tools/`

1. **`tier_a_review_gate.py` has no `--amend`** — a carve-out's later completion
   has nowhere to land. **New this batch.**
2. **Wire ONE anchor-rot tool into a gate.** Both are UNWIRED and cc's A7b
   cannot fail on a real rot by design — the chain still has no live link. Then
   delete `tools/sf_events_anchor_check.py` per its own header.
3. **R3 should count the 48 citation RANGES** so the second class is 371, not
   323. Plus the b22 `subject_sha()` touched-file disclosure and the re-seat
   author-time guard; b19's census asks 1 and 4; `batch_manifest.py:386`.

### Michael

**Nothing blocking, and two things are HELD AT YOUR INSTRUCTION and were not
acted on:** the EVV-readiness raw-clock question and the one-person-agency
self-approval question. **Payroll F1 is decided and routed to hank.**

### hover2 / hover

Unchanged: four `# OWNER: hover2` lines; which tree is canonical for the four
basenames in both.

---

## 9. WHAT b24 PROVED vs LEFT UNPROVEN

**PROVED, driven:** that the leg_aftercare derivation is stable for every
shipped pair; that rows written by shipped builds nevertheless change id; that
the server-side orphan survives and reappears as a duplicate; that
`legAdoptServerId` loses data on its own named precondition, with its guards'
controls holding; that E4 passes on the colliding pair; and that three named
suites are green at this HEAD while a fourth cannot run.

**LEFT UNPROVEN, and none of it is recorded as checked:**

* **The two 400 observations were NOT made.** Item 3 is parked; the harness
  returned COULD NOT RUN on every section.
* **Whether any `leg_cases` row can carry a case_id that is not `newId('CS')`
  shape.** Not enumerated. **If one exists, F2 widens beyond pre-change rows.**
* **The real production rows.** No production read, so *"rows written before the
  change exist"* is an inference from the code's own comment, not an observation.
* **The full HTTP round trip for leg_aftercare.** The server derivation was
  extracted and run, not reached through a request.
* **The six re-verifications and the (d) drive.** Not begun.
* **The 33 server-only GETs.** Not re-classified; **CALLER is still a lower
  bound.**
* **No live deployment fetched and no table touched** — b24 is two `docs/` files
  plus my root deliverables.

---

## 10. FINAL STEPS STILL AHEAD OF THIS HANDOFF

1. Commit this handoff and push — **without force, confirmed by ancestry and
   `0/0`**.
2. The report, digest and `SAIRN-latest-fourth.md`; **upload all four to Drive
   folder `14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09` and read each back through the
   API** — the mount proves the bytes are in the sync set, not that Google
   acknowledged them.
3. **Do NOT close the b24 manifest.** Three items are `blocked` and one is open;
   closing it would say the batch finished what it was sent to do.
4. **Release the b24 claim LAST**, then set the status row to `idle`. **The claim
   is not being continued.**

**Nothing is partial.** Every open item above is another session's, or Michael's
with its decision named, or mine and named as mine with its exact next step.
