# HANDOFF — fourth / ted, batch b23, 2026-10-15

**Written BEFORE the report**, at a point where nothing is half-finished: all
six items are committed and pushed, `HEAD == origin/main`, 0/0, clean, no rebase
and no stash in progress, and the b23 claim is still held on purpose.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**FOUR THINGS WORTH READING FIRST:**

1. **PAYROLL IGNORES AN APPROVED CLOCK CORRECTION — 60 minutes and $20.00
   unpaid on one visit, DRIVEN.** hank asked whether an *unapproved* time could
   reach payroll; it cannot. **The mirror image is the defect and it is money on
   a federally mandated EVV record.** §4.
2. **MICHAEL'S leg_aftercare CONDITION IS NOW MET.** Both claims are released
   and hank's key fix is on `origin/main`. **It is unblocked and still mine. I
   did not start it** — the batch was six items and this is the handoff point.
   §3.
3. **MY OWN b22 SEVERITY ON THE 151 WAS OVERSTATED, and two of my own
   predicates failed inside this batch.** §6 and §9.
4. **THE 373 IS AN ACTUAL 371**, and the two it was high by are named. §8.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\578e6f48-a2d0-4543-b65b-e5b79ea4e6c8.jsonl`

**Working files (this session's scratchpad):**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\578e6f48-a2d0-4543-b65b-e5b79ea4e6c8\scratchpad\`
New this batch: `verdict_b23_cc.txt`, `verdict_b23_hank.txt`,
`discharge_cc_b23.log`, `discharge_hank_b23.log`, `cc_tool_live_b23.log`,
`cc_selftest_b23.log`, `cc_ablation_b23.log`, `cc_a7b_mutants_b23.py` + `.log`,
`payroll_clock_repro_b23.js` + `.log`, `branch_census_b23.py` + `.log`,
`body_read_b23.py` + `.log`, `branch_drive_b23.js` + `.log`,
`cody_mutants_b23.py` + `.log`, `m1_detail_b23.py`,
`sf_anchor_ablation_b23.py` + `.log`, `bare_citations_b23.py` + `.log`,
`claims_b23.log`, `rebase_resolve_b23.log`, `pre_push_tip_b23.txt`,
`pull_b23.log`, `pull_b23b.log`, `push_b23.log`.
**Same session as b22**, so b22's logs are in the same directory; b18–b21's are
under `b0f8683c…` and are not.

---

## 0. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `5f5fcbad` | `git rev-parse --short HEAD` |
| `origin/main` | `5f5fcbad` | `git rev-parse --short origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| working tree | **clean at this line**; the deliverables commit after it | `git status --porcelain` |
| push forced? | **NO — PROVED BY ANCESTRY, not by grepping git's wording** | pre-push tip in `pre_push_tip_b23.txt`; `git merge-base --is-ancestor <tip> HEAD` → **ANCESTOR** |
| pushes denied first | **2, and neither was about my commits** | `register_feed_gate` got no ref lines because the clone was behind — a non-fast-forward git was about to refuse itself |
| **ledger conflict** | **1, on `docs/tier-a-reviews.json`** | resolved with `tools/sairn_rebase_resolve.py` as the gate's own hint says: 259 ancestor + 2 upstream-only, merged and **validated** |
| the merge **verified, not trusted** | **both discharges survived** | it reported `0 local-only` because a discharge *mutates* a record rather than adding one, so I read `origin/main:docs/tier-a-reviews.json` back (§1) |
| `SAIRN_SEED_GATE` / `GATE_EXEMPT` / `SAIRN_SKIP` | **none used, any form** | — |
| `.claude/settings.json` | **not edited, not committed** | not in any commit's file list |
| hooks | **untouched and never re-added** | by instruction |
| files written outside `docs/` | **0**, plus my own root deliverables | by instruction |
| `api/`, `sql/`, `tests/`, `tools/` files written | **0** | all read-only here by claim |
| files under `.claude/skills/sairn-hover-auditor/` | **0 — neither auditor clone entered** | by claim |
| b23 manifest | **6 of 6 `done`** | `batch_manifest.py --check --agent fourth --batch b23` |
| **context now** | **61% of 1000k** | `tools/sairn_status_line.py` fed this session's transcript |

**`5f5fcbad` IS THE STATE BEFORE THIS HANDOFF** — this file, the report, the
digest, `SAIRN-latest-fourth.md`, the b23 close and the claim release all land
after it.

---

## 1. EVERY b23 ITEM

| # | item | state |
|---|---|---|
| 1 | `--list`, discharge every obligation assigned to me, oldest past-deadline first | **DONE, 2 of 3 — and the item's premise did not hold** (§2) |
| 2 | hank b13 Tier A for `alf_staff`, `leg_cases`, `sen_visits` | **DONE. 4 findings, F1 driven** (§4) |
| 3 | measure the 69 and 151, classify defect vs not, route to hank with `file:line` | **DONE. 22 + 13 real, 151 → 0 caller-reachable** (§6) |
| 4 | reproduce cody's other four mutants; ablate my anchor check | **DONE. 5 of 5 caught; every layer load-bearing** (§7) |
| 5 | re-derive the 373 bare citations to an actual count | **DONE. 371** (§8) |
| 6 | push without force, confirm landed, then check the leg_aftercare claims | **DONE. 0/0, and the condition is MET** (§3) |
| — | this handoff, before the report | **DONE** |

**Verified on `origin/main`, not locally:** `cc 01:13:35Z` → `reviewed`, verdict
**9,134** chars; `hank 01:21:13Z` → `reviewed`, verdict **13,429**;
`cody 01:18:14Z` → **still `open`, no verdict** — which is the deferral and not
a loss.

---

## 2. ITEM 1 — THE PREMISE DID NOT HOLD, AND ONE OBLIGATION WAS DELIBERATELY NOT CLOSED

**The item said "oldest past-deadline first (14 are past the 24h deadline
queue-wide)". 15 were past it queue-wide — and NONE of them was mine.** All
three assigned to me were **11h old**. So the ordering rule did not apply and
the order was `opened_at`. **Said rather than silently reinterpreted.**

**cody `2026-10-15T01:18:14Z` (`leg_aftercare`,
`tests/run_b14_leg_aftercare_probe.py`) IS NOT DISCHARGED.** Michael's standing
decision keeps `leg_aftercare` mine but holds it until the claims release.
**Discharging it would have recorded a review nobody did**, which is worse than
an open row. It is open, it is mine, and §3 says it is now unblocked.

**AND hank's record NAMES `leg_aftercare` AMONG FOUR RESOURCES.** I discharged
it with the carve-out **written into the verdict body**: `leg_aftercare` and
`leg_cases` are explicitly listed as NOT reviewed, with Michael's reason quoted,
so the closed record cannot be read as covering them. `leg_cases` is in that
list only because the aftercare key derives from `case_id`; no other path in the
diff touches it.

---

## 3. ITEM 6 SECOND HALF — THE leg_aftercare CONDITION IS MET

`python tools/sairn_claim.py list` → log `claims_b23.log`.

| fact | measured |
|---|---|
| active claims, total | **2** — mine and cody's **b16** |
| hank active claims | **0** |
| does cody's b16 name `leg_aftercare`? | **NO** — and it says *"NO api/ FILE (hank)"* |
| only active claim mentioning `leg_aftercare` | **my own b23 deferral clause** |
| hank's key fix on `origin/main`? | **YES** — `git cat-file -e origin/main:api/leg-aftercare-key-unambiguous.test.js` |

**SO BOTH CONDITIONS MICHAEL SET ARE SATISFIED: the fix has landed and both
claims are released. The leg_aftercare Tier A review is UNBLOCKED and is STILL
MINE. I did not hand it to anyone and I did not start it.**

**EXACT NEXT STEP, b24 item 1:** discharge `cody 2026-10-15T01:18:14Z` and the
`leg_aftercare` half of hank's b13 that I carved out. **Two questions, both
written by their authors and both still unanswered:**

* **hank's:** prove **no row any shipped build could have written changes key**
  — a changed key *orphans* the row rather than updating it. hank's evidence is
  the preservation arm `F4d`, which tests the shapes hank *believes* exist, so
  the review is of the shape list and not of the arm. **And `legAdoptServerId`
  MERGES onto an existing canonical row, which DROPS a local row — check the
  dropped row can never carry data the kept one lacks.**
* **cody's:** that the probe asserts the **property** and not the agreement
  between the two key derivations — arm `E4` of
  `api/sd-data-leg-role-matrix.test.js` **passes on the colliding pair because
  both copies agree on the wrong answer**; that neither expression is retyped;
  and that `docs/known-red-suites.json` names **ARM 1 ONLY** as expected red.
  **Reviewer must not be cody.**

---

## 4. ITEM 2 — `sen_visits`: THE QUESTION ANSWERED NO, AND THE MIRROR IMAGE IS MONEY

Full verdict in the discharged record and in `scratchpad/verdict_b23_hank.txt`.
Driven: `node scratchpad/payroll_clock_repro_b23.js` → `…_b23.log`, requiring
the **real** `api/_lib/sen-payroll.js` and `api/_lib/sen-evv-clock.js`.

One visit, clock-in 13:00Z, clock-out 17:00Z, a correction to 12:00Z, $20/hour,
week start Monday:

| | effectiveClock | payroll |
|---|---|---|
| **PENDING** correction | `13:00Z`, `corrected=false`, `pending=true` | **240 min** — same as no correction. **SAFE** |
| **APPROVED** correction | `12:00Z`, `corrected=true` | **240 min / 8000¢ as shipped** vs **300 min / 10000¢** with `effectiveClock` applied |

**→ 60 MINUTES AND $20.00 UNPAID, on one visit with one approved correction.**

**F1 — HIGH.** `api/_lib/sen-payroll.js:200-201` reads `row.clock_in_at` raw
(`grep -c effectiveClock` → **0**; the module does not require
`sen-evv-clock.js` at all), and `api/sd-data.js:7678-7679` spreads `x.data` with
no substitution. **And `api/_lib/sen-evv-clock.js:342-344` asserts the
opposite** in its own words: *"'A scheduler approves it before payroll uses it'
is implemented HERE, in the function payroll reads."* **The function payroll
reads is `instant(row.clock_in_at)`.** Silent, and the two screens disagree: the
read path at `api/sd-data.js:6993-7003` *does* apply `effectiveClock` and
attaches `effective_clock` beside the raw field, deliberately.
**NEXT STEP: apply `effectiveClock` in ONE place — the payroll action's map — so
`sen-payroll.js` stays pure. Do NOT change `SEN_CLOCK_IMMUTABLE`.**

**F2** — `api/_lib/sen-evv-readiness.js:302-303, :310` also read raw, reached
from `api/sd-data.js:7632` via the same spread at `:7603-7604`. **There is a
real argument for raw on an EVV record** — that file says *"EVV verifies what
happened, not what was planned"* — **but nothing says the divergence is
deliberate**, and an undeclared divergence is indistinguishable from F1.
**A DECISION, not a fix.**

**F3** — `grep -c effective_clock sairnsenior.html` → **0**, against ~20 raw
`clock_in_at` reads including the duration calc at `:2540-2541` and the
"Clocked in" row at `:2980`. **The corrected value is reachable by nobody.**

**(b)** the status-less-entry default is **sound by construction** — both
writers stamp a status (`:288`, `:324`), so a status-less entry can only be
pre-T16. **It fails OPEN**, though: a future writer that forgets gets APPROVED.
**NEXT STEP, small: refuse a status-less entry at WRITE time, keep the
permissive read.** **(c)** the marked self-approval is **acceptable with the
marking** and my view is recorded rather than an approval. **(d)** no stranded
`LATE_REPLAY` — the superseded set excludes submitted fields
(`api/sd-data.js:7349-7358`). **(d) IS READ, NOT DRIVEN** and is the
weakest-evidenced item in the verdict.

---

## 5. ITEM 2 — `alf_staff`: RIGHT DIRECTION, ONE BRANCH SHORT

**The direction is confirmed and I would not change it**, and **no consumer
coerces `null` to `false`** — all three test explicitly
(`api/sd-data.js:14010`, `compliance-rules.js:1057`, `:1081`).

**F4 — MODERATE.** `s.applies_to` is a strict `applies === true` **whitelist**
(`api/sd-data.js:14009-14010`), and `compliance-rules.js:899-901` drops an
**undecided** requirement into the same bucket as a decided `false`, so its
hours vanish from `required_annual_hours`. **`anyUnmapped` (`:1056-1058`) does
detect the null — but it is consulted only at `:1156`, inside the
`emptyApplicable` branch**, and `excluded_by_position` collects `false` only.
**So: nothing matched + one undecided → correct message. SOME matched + one
undecided → a confident lower figure to a surveyor, with no caveat.** That is
T18's own case. **NEXT STEP: collect the nulls the way the falses are collected,
and require a TWO-SIDED arm** — one `true` + one `null` must not report a
settled figure; one `true` + one `false` must still report one.

---

## 6. ITEM 3 — THE TRUE COUNTS, AND MY b22 SEVERITY WAS WRONG

`docs/2026-10-15-fourth-b23-notprovisioned-branch-census.md`. **332 guards** at
18,770 lines. Classified by the **HTTP method** of the guarded fetch and by what
its URL **interpolates**, because a fold is harmless exactly when the request
cannot return 400 for any reason other than the table being absent.

| | count | verdict |
|---|---:|---|
| **B, WRITE-guarded** | **22** | **REAL, HIGH** — a `23514` from the 64 KB cap answers *"run the migration"* |
| **B, GET + CALLER value** | **13** | **REAL, MODERATE** — a `22P02` on a malformed caller id answers 503 |
| B, GET server-only | 33 | not caller-reachable; **untested** |
| B, unclassified | **2** | `:13503`, `:17127` — **could-not-tell, read by hand** |
| **C (the 151)** | **0 caller-reachable** | 0 write-guarded, 0 caller-interpolated; 1 session-interpolated (`:3604`) |

**THE 22, for hank:** `2644, 3206, 3567, 4123, 4182, 4431, 4513, 4588, 8231,
9029, 9224, 10553, 10700, 10899, 11018, 11188, 11265, 11516, 11595, 13660,
13791, 14348`. **`:3206` and `:11018` already read the body first**, so they
want the existing 4-argument preread form; the other 20 want the 3-argument call.

**MY b22 CLAIM THAT THE 151 WERE "the largest un-owned population" AND
"strictly worse" IS WITHDRAWN AS TO REACHABILITY.** The shape claim stands; **a
caller cannot provoke a non-missing-table 400 on any of them.** What is still
real is **deploy-reachable**: a dropped or renamed column answers `42703` as 400
and renders `{ok:true,data:[],provisioned:false}` on **150** read paths — a
partial migration, which is the state this platform is in most often. **One
helper change, not 151.**

**Driven:** `notProvisionedDecide` extracted by text from the shipped file and
run in a `vm` — `23514` → **400 ROW_REFUSED**, `PGRST100` → **400
UPSTREAM_REJECTED**, `42703` → **503 NOT_PROVISIONED**, `404` → **503
NOT_PROVISIONED**. The third line confirms my b22 F2 concretely.

---

## 7. ITEM 4 — 5 OF 5 MUTANTS CAUGHT; EVERY ABLATED LAYER LOAD-BEARING

`docs/2026-10-15-fourth-b23-mutants-ablation-and-citations.md` §1–2.

**Baseline first** (419 passed / 0 failed), then: **M2** gate suite absent,
**M3** a member name removed, **M4** the 401 refusal stripped, **M5** the
invented control name present — **all CAUGHT, exit 1**, each naming its own MISS
line. **M1 re-driven is CAUGHT at exit 2 COULD NOT RUN**, printing *"405 passed,
14 failed"* — **b22's figure from a second route**, and the refusal is correct: a
sabotage control on a red baseline cannot separate its own mutation from the 14.
**The four that b22 left uncorroborated are now corroborated**, by copying the
tree and running the **copied** probe so its `ROOT` is the copy.

**Ablation of `tools/sf_events_anchor_check.py`, both forms.** Part A: the fix
removed → **1 finding, ARM FAILS**; restored → **0, ARM PASSES**. Part B: L1
breaks 2 arms, L2 breaks 1, L3 breaks 2 **and raises**, L4 breaks 2 **and
raises** — **every layer load-bearing**. **L5 IS A FINDING ABOUT MY OWN TOOL:
the fail-closed guard lives in `main()` and not `check()`, so NO fixture arm can
see it** — the lock would pass with the guard deleted. Driven directly instead:
app absent → **exit 2**, register absent → **exit 2**, both present → **exit 0**.
**NEXT STEP: an arm for L5.**

---

## 8. ITEM 5 — **371**, AND THE 48 ARE THE INTERESTING ONES

Every `:(\d{1,5})` occurrence classified rather than one regex narrowed —
**571** in total: **198 qualified**, **323 bare single lines**, **48 bare
RANGES**, **1** OAC chapter number, **1** ISO timestamp.

**b22's 373 was high by EXACTLY TWO and both are named.** **cc's 323 is not a
predicate error — it is the single-line form only; the 48 ranges are the
difference**, and they are real citations cc's regex cannot see. **A range
cannot be checked by ANY single-line lookup, so no tool in this repo can assess
them** — unassessable by **form**, 13% of the bare population. **Routed to cc.**

---

## 9. CLAIMS, LOCKS, STASHES — and two predicates of mine that failed

| hold | count | detail |
|---|---:|---|
| repo claims held | **1** | b23; **release LAST**, after all four uploads verify |
| **Tier A obligations assigned to me** | **1, deliberately open** | cody `01:18:14Z`, `leg_aftercare` — **unblocked, see §3** |
| discharged this batch | **2** | both as the assigned owner, neither by `--takeover` |
| `git stash` | **0** | `git stash list` |
| session lock | **mine and live** | not reaped or removed this batch |
| status registry row | `working` | **`idle` at release** |

**TWO OF MY OWN PREDICATES FAILED INSIDE THIS BATCH AND BOTH ARE IN THE
DOCUMENTS.** The caller-influence test first flagged **68 of 151** because a
`select=` clause matched the trailing paren of every URL — caught by
spot-reading `:5120` and `:3604`. The body-read detector first reported *"reads
the body first: YES"* for all eight samples because it matched
`code: 'NOT_PROVISIONED'` **inside the answer**; re-measured positionally it is
**7 of 332**, not hank's nine, and four of the seven are already preread sites.
**b22's method note was "when a predicate names an identifier, say which
identifier". This batch adds: SAY WHERE THE PREDICATE LOOKS. Both failures were
positional, not lexical.**

---

## 10. WHAT IS OPEN, AND WHY

### hank — `api/`

1. **F1 first: apply `effectiveClock` in the payroll action's map.** Money, on a
   federally mandated record.
2. **The 22 write branches** (§6), then the **13** caller-interpolated GETs.
3. **Read `:13503` and `:17127` by hand** — unclassified, could-not-tell.
4. **Decide the read-case fifth answer** before touching the 151.
5. **F2** (declare the EVV divergence or substitute), **F3** (the client reads
   `effective_clock`), **F4** (`alf_staff`'s undecided disclosure), and the
   status-less-entry write guard.
6. **Still open and NOT re-verified this batch:** b18's N1; the MAR grant bypass
   via `alf_clients` with no audit row; the `rf_photos` rebuild dropping
   `ai_source`; `license_hash` never re-verified in memory; no revoke action for
   a live grant; the two `sd_photos` caller findings from b22.

### cc — `tools/`

1. **Wire ONE anchor-rot tool into a gate.** Both `citation_anchor_rot_check.py`
   and my `sf_events_anchor_check.py` are **UNWIRED**, and cc's A7b cannot fail
   on a real rot by design (M7/M8 pass). **So the chain has no live link** —
   rule 1.1 one level out. **Then delete mine**, per its own header.
2. **A7b's floor is per-TARGET, not per-ROW** — latent, not reachable today
   (1 declaration, 8 anchors, all on line 358), measured so it is not guessed.
3. **R3 should count the 48 RANGES** so the second class is 371, not 323.
4. **`subject_sha()`** touched-file disclosure and the **re-seat author-time
   guard**, both from b22, still open. b19's census asks 1 and 4.
   `batch_manifest.py:386`, still worked around with `PYTHONIOENCODING=utf-8`.

### cody — `tests/`

1. **A failing-first arm driving a `23514` through one of the 22**, and a
   `42703` through one of the 151. **Nothing in the repo drives either today.**
2. The REPLACEMENT COVERAGE generalisation arm and the per-resource refusal arm
   (b22), plus b22's F3/F4 arms and b19's four.

### Michael

**Nothing blocking.** Two decisions when convenient: **F2**, whether the state
aggregator should receive the device clock or the approved correction; and
**(c)**, whether a marked `self_approved` is acceptable on an EVV record — I
recorded a view (yes, with the marking) rather than an approval.

### hover2 / hover

Unchanged: four `# OWNER: hover2` lines; which tree is canonical for the four
basenames in both.

---

## 11. FINAL STEPS STILL AHEAD OF THIS HANDOFF

1. Commit this handoff and push — **without force, confirmed by ancestry and
   `0/0`**.
2. **Upload it to Drive folder `14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09` and verify**,
   then a **Drive-side API read** — the mount proves the bytes are in the sync
   set, not that Google acknowledged them. **Expect the API read to lag; b19–b22
   all saw an empty first read.**
3. The report, digest and `SAIRN-latest-fourth.md`, then upload-and-verify all
   four and read each back.
4. `batch_manifest.py --close --agent fourth --batch b23` — **after** the uploads
   verify.
5. **Release the b23 claim LAST**, then set the status row to `idle`.

**Nothing is partial.** Every open item above is another session's, or Michael's
with its decision named, or mine and named as mine with its b24 slot. **The one
obligation still assigned to me is open on purpose and §3 gives its exact next
step.**
