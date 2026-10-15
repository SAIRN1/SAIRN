# HANDOFF — fourth / ted, batch b26, 2026-10-15

**READ THIS FILE ONLY.** It is the whole state.

**ALL SIX b26 ITEMS ARE DONE** and the batch manifest closes 6/6 — it was opened
as the FIRST action of the batch, which is the thing b25 could not honestly do.
Nothing is parked, nothing is half-checked, nothing is recorded as verified that
was not. **Context at this line: 54.6% of 1000k.**

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**FOUR THINGS TO READ FIRST:**

1. **A PAID PERIOD CAN BE SILENTLY UNFROZEN BY ANY MANAGEMENT ROLE** — `billing`
   included, and `billing` is also the role that runs payroll. Driven end to
   end: one settings POST, HTTP 200, and the next pay run reports **$100.00 for
   a period already paid at $80.00**, with no record the frozen list ever
   existed. §3.3
2. **AN ADJUSTMENT CAN BE NEGATIVE.** A downward approved correction deducts
   from a later period's wages with no notice. §3.2
3. **TWO OF MY OWN PUBLISHED FIGURES ARE WITHDRAWN.** b23's CALLER count was
   **low by 19**, and b23's *"0 of the 151 interpolates a caller value"* is
   wrong — **16 do**. §5
4. **ONE FRESH TIER A OBLIGATION ARRIVED MID-BATCH and is UNTOUCHED.** §8

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\990beb38-3b90-4380-8bf3-2fb64608e44e.jsonl`

**Working files (this session's scratchpad):**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\990beb38-3b90-4380-8bf3-2fb64608e44e\scratchpad\`
New this batch: `b26_freeze_drive.js` + `.log`, `b26_lock_ablation.py` + `.log`,
`b26_late_replay_drive.js` + `.log`, `branch_census_b26.py`, `b26_census.log`,
`b26_census_selftest.log`, `b26_census_ablate.log`,
`b26_trusttx_baseline.log`, `verdict_b26_hank_a1c22397.txt`,
`b26_pre_push_tip.txt`, `b26_push.log`, `b26_rebase_*.log`.
**SAME SESSION AS b25**, so b25's files are in the same directory; b22–b24's are
under `578e6f48…` and are not.

---

## 1. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `f54bbb19` | `git rev-parse --short HEAD` |
| `origin/main` | `f54bbb19` | `git rev-parse --short origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| working tree | **clean at this line**; this handoff and the deliverables commit after it | `git status --porcelain` |
| push forced? | **NO — PROVED BY ANCESTRY**, not by grepping git's wording | `b26_pre_push_tip.txt` → `git merge-base --is-ancestor <tip> HEAD` → **ANCESTOR**. `grep -c force b26_push.log` → **0** |
| landed, verified **on origin** | `git show origin/main:docs/2026-10-15-fourth-b26-findings.md` returns its first line | — |
| push gate | **ran live and allowed** — `.githooks/pre-push` is wired | — |
| `SAIRN_SEED_GATE` / `GATE_EXEMPT` / `SAIRN_SKIP` | **none used, any form** | — |
| `.claude/settings.json` | **not edited, not committed** | — |
| hooks | **untouched and never re-added** | — |
| `api/` `sql/` `tests/` `tools/` files written | **0.** Every suite RUN, every drive against a COPY | `git diff --name-only` → no `.js/.html/.sql/.py` |
| auditor clones | **not entered**; 0 files under `.claude/skills/sairn-hover-auditor/` | — |
| `git stash` | **0** | `git stash list` |
| b26 batch manifest | **opened FIRST, 6/6 done** | `batch_manifest.py --check --agent fourth --batch b26` |
| Tier A assigned to fourth | **1 — arrived MID-BATCH at 15:12:47Z, untouched (§8)** | `tier_a_review_gate.py --list` |
| **context now** | **54.6% of 1000k** (545,603 tokens) | max `usage` sum over this session's transcript |

**`f54bbb19` IS THE STATE BEFORE THIS HANDOFF** — this file, the report, the
digest and `SAIRN-latest-fourth-b26.md` all land after it.

---

## 2. EVERY b26 ITEM

| # | item | state |
|---|---|---|
| — | open the batch manifest FIRST | **DONE.** `--new fourth b26 --items 6`, `id_lock=906816e5cf0d24f9`, before any item was worked |
| 1 | Tier A for `a1c22397`, change (3) first; decide the floor and the reopen rule | **DONE.** Discharged. 3 findings, 2 of them HIGH, both driven (§3) |
| 2 | re-derive the 22 at HEAD; review the ten blob conversions as a change | **DONE.** Still 22; conversions CORRECT (§4) |
| 3 | drive (d) `LATE_REPLAY` live | **DONE.** 4 writes in sequence, all four properties hold (§6) |
| 4 | reclassify the 33 server-only GETs; extend the census to follow variables | **DONE**, and two of my own figures withdrawn (§5) |
| 5 | methodology: span recount mechanical, failing-first with ablation | **DONE.** 10/10 fixtures, per-arm ablation, routed to cc with full source (§7) |
| 6 | push without force, confirm it landed | **DONE.** 0/0, ancestry-proved, verified on origin (§1) |
| — | this handoff, before the report | **DONE** |

---

## 3. ITEM 1 — THE TIER A REVIEW, AND MY TWO DECISIONS

Discharged: `hank 2026-10-15T15:04:38Z` / `a1c22397`, seven Tier A resources.
Full verdict on the record in `docs/tier-a-reviews.json`; the body is also at
`<scratchpad>/verdict_b26_hank_a1c22397.txt`. Narrative in
`docs/2026-10-15-fourth-b26-findings.md` §1.

### 3.1 Change (3), taken first as instructed

**STRICTLY STRONGER AND NOT AN EXEMPTION**, verified on the assertion rather
than the description: four independent failure modes against the old arm's one.
**403 is right on the merits**, and there is **no independent spec** — the only
document is hank's own handoff. `node api/sd-data-law-trusttx-session.test.js` →
EXIT=0, 13/13.

**FINDING H1 — THE TRUST HARD-LOCK IS UNTESTED**, by 2×2 ablation:

    BASELINE  lock intact,  table denies            exit 0  3a ok
    ARM B     lock intact,  table paralegal 'r'     exit 0  3a ok   <- the lock DOES work
    ARM C     lock emptied, table paralegal 'r'     exit 1  3a FAIL
    ARM A     lock emptied, table denies (shipped)  exit 0  3a ok   <- THE FINDING

**Delete `LAW_TRUST_LOCKED` entirely and the suite stays green**, because
`decide()` applies the table first and re-asserts the lock only after it agrees.
**`law_bankstatements` has no arm at all.** **NEXT STEP (hank):** two assertions
on the exported `LAW_TRUST_LOCKED` plus a behavioural arm for
`paralegal → law_bankstatements → 403`, **then re-run the 2×2 — ARM A must go
RED.**

### 3.2 MY DECISION: the straight-time floor. **FINDING H2 (HIGH)**

**THE RULE: straight time is an acceptable floor, but AN ADJUSTMENT MUST NEVER
BE NEGATIVE.** Driven:

    UPWARD   -> adjustment_cents= 2000  delta=[ 60]  total_payable_cents= 2000
    DOWNWARD -> adjustment_cents=-2000  delta=[-60]  total_payable_cents=-2000

**RATIONALE:** an adjustment exists to PAY for work already performed and
underpaid. A negative one is **recovery of an overpayment** — a separate
regulated act (unlawful under the FLSA where it takes a workweek below minimum
wage; written authorisation required in many states). A pay run must not perform
one as a side effect of an approval, in a period the employee has not been told
about. It is also F1's mirror: F1 was sixty minutes unpaid by omission, this is
sixty minutes removed by commission.
**NEXT STEP (hank):** floor at 0 per visit; surface negatives as
`overpayments[]` requiring a human act, never netted; assert
`total_payable_cents >= gross_cents`. And **each adjustment carries
`premium_may_be_owed`** when the as-paid week was at or over the threshold —
flagging needs no reopening, the weekly minutes are already in hand. **A
disclosure that names a class is a note; a flag that names a person is payable.**

### 3.3 MY DECISION: the reopen rule. **FINDING H3 (HIGH)**

**THE RULE: a paid period is reopened only by an APPENDED correction record.
Never a silent replace.** Driven through the real handler:

    stored before : {"periods":[{"period_start":"2026-09-01",...,"paid_at":"2026-09-20T00:00:00.000Z"}]}
    as billing    -> HTTP 200
    as owner      -> HTTP 200
    stored after  : {"periods":[]}
    rows carrying the key: 1      (an APPEND would leave 2+; a REPLACE leaves 1)

    closed_periods = the real one -> HTTP 200  period_closed={...}  minutes=240  gross=8000
    closed_periods = EMPTIED      -> HTTP 200  period_closed=null   minutes=300  gross=10000

`sen_settings`'s generic write (`api/sd-data.js:8282`) requires only
`MANAGEMENT_ROLES` = `{owner, billing}`, validates only `evv_config` and
`agency_profile`, **says in its own words that unknown keys are stored as-is**,
and upserts `merge-duplicates` — a full REPLACE. **It defeats the mechanism's own
safety argument in its own words:** the 503 on an unreadable list exists because
treating it as empty *"would silently UNFREEZE every paid period and restate
history"*.
**NEXT STEP (hank), a schema decision not a patch:** a **named** refusal of that
key at the generic path; an **append-only** closings resource, one row per
closing, never updated or deleted — the `leg_custodylog` shape `leg-roles.js`
already models — with the read unioning them; a reopen as a new appended row
referencing what it reverses. **Until then the gap is OPEN and the freeze must
not be described to an agency as a guarantee.**

### 3.4 hank's five questions

* **Q1 undatable approval — his reasoning holds**, and the proof is
  **structural, not his counterfactual**: both writers stamp the fields and
  `clock_corrections` is in neither payload allowlist, so an undatable approved
  entry can only be legacy. Driven: no double count.
* **Q4 the straddling run — CONFIRMED.** A partly-frozen 480-minute total is
  labelled `period_closed: null` and **none of the 7 `not_computed` entries
  mentions it**. The per-visit freeze is the safe half and worked. **NEXT STEP:**
  a `partially_closed` third state.
* **Q5 the 503 direction — CORRECT**, and I am not splitting it.
* **Q(b)2 — MICHAEL'S SAME-CLOCK DECISION IS NOT FULLY IMPLEMENTED.**
  `api/_lib/sen-evv-readiness.js:339-340` uses the **no-as-of** form, so a closed
  period has pay reading as at `paid_at` while EVV reads **now**.
  `effectiveClockAsOf` already exists. **Reported, not decided by me.**
* **Q(c) the purity HEADERS are the defect**, not the `require()`. hank's own
  line that not editing them may itself be the defect is correct.
* **The `sd_hr` id-shadow change is CORRECT and CLOSES my own b25 LOW**, in the
  opposite direction to what I routed. I widened the consumer universe: his two
  files are the whole of it.

---

## 4. ITEM 2 — THE 22, AND THE TEN CONVERSIONS

**STILL 22**, at `ceea750d`, 18,867 lines. The file grew about 100 lines since
b25's 18,769 and **the count did not drift** — which is the methodology working
rather than luck. Citations moved (+24 early, +98 late):

    :2668  :3230  :3591  :4176  :4240  :4489  :4571  :4646  :8328  :9126
    :9321  :10650 :10797 :10996 :11115 :11285 :11362 :11613 :11692 :13757
    :13888 :14445

**A 23rd WRITE-GUARDED GUARD EXISTS IN A SHAPE NOBODY COUNTED — `:15150` — AND
IT IS NOT A DEFECT.** Its own comment names 23505 / 23502 / 23503 and says the
table exists and refused the row. Named because a 22 beside a bucket of 23
invites the 25-vs-22 mistake again.

**THE TEN BLOB CONVERSIONS (`8627f4e4`) ARE CORRECT AND LOSE NOTHING.**
`storedBlob(payload, [])` narrows by **exactly the three scope keys**, so the
nine empty column lists are right rather than an omission — stripping a mapped
column would have been cody's arm-Z defect. The one `['shop_id']` loses nothing:
read and write echo both re-attach it from the column (`:2339`, `:2343`,
`:2355`). `storedBlob` mutates a copy.

---

## 5. ITEM 4 — THE 33 RECLASSIFIED, AND TWO FIGURES OF MINE WITHDRAWN

Class B's 46 GET-guarded branches: **CALLER 32**, SESSION 1, **UNRESOLVED 4**,
**SERVER-ONLY 9** — against b23's **13** and **33**. **CALLER was low by 19 and
SERVER-ONLY high by 24.**

**AND b23's CLAIM ABOUT THE 151 IS WITHDRAWN.** b23 said *"0 of them
interpolates a caller value, so a caller cannot provoke a non-missing-table 400
on any of them."* The census finds **16 CALLER**, 2 SESSION, **19 UNRESOLVED**,
114 SERVER-ONLY. The reachability withdrawal I made in b23 was itself too
generous.

**Spot-checked in BOTH directions**, because an over-reporting predicate is as
bad as an under-reporting one: `:5120` CALLER correct (`enc(String(payload.id))`
literally in the URL); `:15150` write-guarded correct and a true non-defect;
`:10556` **UNRESOLVED correct, and it is the third state earning its keep** —
`jobId` is a function parameter of `rfJobGate`, whose call sites at `:10612` and
`:10746` pass `payload.job_id`, **so it is CALLER once you go
inter-procedural.**

**THE LOWER BOUND IS NOT GONE — IT IS NAMED.** 26 enumerated `UNRESOLVED` lines
(4 + 19 + 3) instead of a hidden `else` branch, one resolved by hand.
**EXACT NEXT STEP:** resolve a parameter by finding the enclosing function and
unioning the origins of the matching argument at every call site — **with a
fixture in both directions, or the extension is the same prose problem again.**

---

## 6. ITEM 3 — (d) `LATE_REPLAY`, DRIVEN LIVE

b23 read it; **b24 and b25 both left it as read-only evidence** and b23's own
verdict called it its weakest-evidenced item. Four writes in sequence against one
persistent row through the real handler. **All four properties hold:** the flag
is STORED not only returned; a later write on the other clock field does not
erase it (**and the both-flagged case is the discriminating one**, which is the
one driven, because the pre-fix bug only showed when both halves were flagged);
**the T16 refinement holds** — a re-sent immutable field lands as a pending
correction, the row keeps the original, and the original's flag is KEPT; and a
write mentioning no clock field keeps every flag untouched.

**ONE FIXTURE CORRECTION DISCLOSED:** the first draft moved `clock_in` to NOW,
inverting the visit, and was refused `400 CLOCK_OUT_BEFORE_IN` — correct
behaviour, and it meant the arm never reached its subject. Corrected to +30
minutes and re-driven.

---

## 7. ITEM 5 — THE SPAN RULE IS NOW A FIXTURE, AND IT IS ROUTED

`CRITERIA_VERSION 2026-10-15.b26.1`. **Ten fixtures, 10/10**, locked before the
real file is read, and the program **exits 2 COULD NOT RUN rather than reporting
a census** if they fail. Three rules, each with fixtures in both directions.
**Ablation per ARM, not per exit code:**

    WITHOUT R1 span-bounded-at-next-fetch          1 change -> GET becomes POST   (the 25-vs-22 error)
    WITHOUT R2 guard-binds-to-own-variable         1 change -> UNCLASSIFIED -> GET
    WITHOUT R3 follow-caller-through-assignments   3 change -> all collapse to SERVER-ONLY (the lower-bound error)

**Every rule is load-bearing.** **ONE FIXTURE WAS WRONG AND IS DISCLOSED:** the
first R1 fixture used a layout the file does not contain and failed for that
reason, not because the rule was wrong.

**`tools/` is cc's, so it is ROUTED WITH ITS FULL SOURCE INLINE** in
`docs/2026-10-15-fourth-b26-branch-census-routed-to-cc.md` — because the three
previous censuses each lived in a scratchpad and **each rebuild re-introduced a
bug the previous one had fixed.** Convention **35** gains one operational clause
rather than a 36th number; the heading count and denominator are unchanged
(35 headings, 1–35, no gap, no duplicate, *"ELEVEN of the thirty-five"*).

---

## 8. ONE FRESH TIER A OBLIGATION ARRIVED MID-BATCH — UNTOUCHED

**§1 says 1 assigned to fourth, and this is it.** It is **not** in b26's
dispatch and **nothing was done to it**: not begun, not partly checked, no
verdict recorded.

| | |
|---|---|
| record | **`cody 2026-10-15T15:12:47Z`**, sha `d47880d3`, **held 1h**, assigned to fourth |
| resource | **`bld_bids`** (Tier A) |
| files | `tests/sairnbuild_server_wins.js`, `tests/run_sairnbuild_server_wins_sabotage_probe.py` |
| state | **UNTOUCHED** |

**WHY IT MATTERS, in cody's own measurement:** the suite asserted the literal
`key==='bld_bids'` appears in `bldRetryPending`. That literal is **gone** from
the code — `sairnbuild.html:2369` now declares
`BLD_SESSION_REQUIRED = { bld_bids: true, bld_draws: true }` — but the string
still occurs twice in the file and **both occurrences are COMMENTS**, one of them
*inside* `bldRetryPending` explaining that the old form used to read that way.
**So the assertion was satisfied by the comment documenting the removal of the
thing it asserted, and the sabotage arm guarding it was ANCHOR-0 at the same
time. Two layers of guard on a Tier A resource, neither guarding.**

**EXACT NEXT STEP:** this one is **mechanically settleable** and should be
quick — check (1) that the new regex cannot be satisfied by a future comment or
string literal the way its predecessor was, which means reading what the suite
strips and confirming the four-argument call-site requirement a comment cannot
meet; then (2) and (3) from the record's own `what`; and **ablate the
re-anchored sabotage arm** so it is known to be able to fail, which is the
property its predecessor lacked. The 24h clock starts at **15:12:47Z** — read
the runway from `tier_a_review_gate.py --list`, not from this line.

---

## 9. WHAT IS OPEN, BY OWNER

### hank — `api/`

1. **H3 FIRST, and it is money on a federally mandated record:** the
   append-only closings resource and the named refusal of
   `payroll_closed_periods` at the generic `sen_settings` path. **Until it
   exists a paid period can be unfrozen by a billing session with one POST.**
2. **H2:** floor `adjustment_cents` at 0, surface `overpayments[]`, assert
   `total_payable_cents >= gross_cents`, and add `premium_may_be_owed` per
   adjustment.
3. **H1:** assert `LAW_TRUST_LOCKED` directly, add a `law_bankstatements` arm,
   **then re-run the 2×2 and confirm ARM A goes RED.**
4. **Q4:** a `partially_closed` third state on the period label.
5. **Q(b)2:** decide and implement the EVV basis for a closed period —
   `effectiveClockAsOf` exists. **Michael's same-clock decision is currently
   unimplemented for closed periods.**
6. **Q(c):** edit both "pure" headers to say what they now mean.
7. **b24 F3 / b24 F4** — still open, unchanged: delete the replaced id
   **server-side** in the canonicalising write; field-merge `legAdoptServerId` on
   the write's own payload (`Object.assign` is **not** the fix).
8. **The 22 branches** from §4's list — not b23's and not b24's 25 — then b23's
   13 caller-interpolated GETs, **now known to be 32**, then `:13503`/`:17127`.
9. **Still open and re-verified in b25 with fresh lines:** b21 F3, b21 F4,
   `license_hash` never re-verified, no revoke action, both `sd_photos`
   findings, b23 F4, the status-less-entry write guard. **b18 N1 and b23 F1/F2/F3
   are CLOSED.**

### cody — `tests/`

1. **Arm Z's `else` branch, then RE-RUN THE ABLATION** — the arm does not count
   until it comes back RED. (b25, HIGH, unchanged.)
2. The `known-red-suites.json` blob-scope row → **RECOVERED**; the control arm's
   hardcoded *"ten failures above"* → read off `failed.length`.
3. **b24 F1** — re-anchor the `leg_aftercare` probe, **with an arm that fails
   when the extraction anchor stops matching.**
4. A failing-first arm driving a `23514` through one of the 22 and a `42703`
   through one of the 151 — b25 **observed** both; nothing drives either.

### cc — `tools/`

1. **INSTALL THE CENSUS** from
   `docs/2026-10-15-fourth-b26-branch-census-routed-to-cc.md` — full source
   inline, fixtures included, `REPO` to become a repo-root derivation. **Three
   scratchpad censuses in three batches each re-introduced a predecessor's bug;
   this is the routing that stops the fourth rebuild.**
2. `tier_a_review_gate.py --amend`; wire **ONE** anchor-rot tool into a gate;
   R3's 48 citation ranges.
3. **The convention-numbering check** routed in
   `docs/2026-10-12-fourth-b5-routing.md:585-615` is **still not built** — b25
   and b26 both moved the prose denominator by hand.

### Michael

**Nothing blocking.** Two decisions carried into b26 and honoured: the adjustment
posts to the next period, and the EVV export reads the same effective clock as
pay — **the second is not fully implemented for closed periods (§3.4)**.

**STILL HELD AND NOT ACTED ON:** the one-person-agency self-approval question.

**AND THE STANDING QUESTION FROM b25 IS UNCHANGED:** an approved clock
correction now reaches pay, but **whether any real visit was underpaid before
today is not establishable from the repo** — no production row has ever been
read — so whether a back-payment is owed is yours. **Added by b26:** no agency
has a `payroll_closed_periods` row either, so **the freeze has never run on real
data by anyone.**

### hover2 / hover

Unchanged: four `# OWNER: hover2` lines; which tree is canonical for the four
basenames in both.

---

## 10. WHAT b26 PROVED vs LEFT UNPROVEN

**PROVED, driven:** that a billing session can unfreeze a paid period with one
settings POST and that the next pay run restates it; that a downward approved
correction produces a negative adjustment and a reduced payable total; that the
trust hard-lock can be deleted with the suite staying green, and that the lock
nevertheless works; that the `law_trusttx` arm is strictly stronger; that an
undatable approval cannot double-count, and why, from the writers; that a
straddling run presents a partly-frozen total as live; that all four
`LATE_REPLAY` properties hold including T16; that the 22 is still 22 while the
file grew; that the ten blob conversions lose nothing; that CALLER was low by 19
and that 16 of the 151 are caller-reachable; and that every one of the census's
three rules is load-bearing, by per-arm ablation.

**LEFT UNPROVEN, and none of it is recorded as checked:**

* **NO LIVE VERIFICATION.** Nothing ran against a real Supabase. **No
  production row read, no table touched, no deployment fetched.**
* **The inter-procedural half of the census.** 26 `UNRESOLVED` lines stand, one
  of them known to be CALLER.
* **The census is not a gate.** Nothing runs it on a push, so item 8 applies to
  it like everything else.
* **`cody 2026-10-15T15:12:47Z`** — fresh, untouched, §8.
* **`law_optx`** only as the control in arm 3b.
* **`sairnsenior.html` and `sairnbuild.html`** were grepped, never re-extracted
  block by block and never rendered.
* **The FLSA premium itself.** I accept the floor and require the flag; I do not
  assert what any premium is worth.
* **hank's F17 throw arm** stands with his own caveat: 15 shapes are not a
  property, and I did not write the fuzz either.

---

## 11. FINAL STEPS STILL AHEAD OF THIS HANDOFF

1. **Upload this handoff to the Drive status folder** `14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09`
   and read it back **through the API** — the mount proves the bytes are in the
   sync set, not that Google acknowledged them. **b25 measured the API lagging
   the mount by about five minutes**, so poll until it agrees.
2. Commit and push this handoff — **without force, confirmed by ancestry and
   `0/0`**.
3. The report, the digest and `SAIRN-latest-fourth-b26.md`; upload all, verify
   each.
4. **Release the b26 claim LAST**, then set the status row to `idle`.

**Nothing is partial.** Every open item above is another session's, or Michael's
with its decision named, or named as mine with its exact next step.
