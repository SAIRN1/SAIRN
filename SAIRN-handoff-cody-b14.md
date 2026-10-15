# Handoff — cody, batch b14, 2026-10-14

**ALL SIX ITEMS ARE DONE AND LANDED. Nothing is half-finished.** The two
suites that end at exit 1 are **RED ON PURPOSE AND WRITTEN RED** — that is the
deliverable of items 3 and 4, not an unfinished edge — and each carries an
`expected_red_scope` field in `docs/known-red-suites.json` naming exactly which
arms are the expected red, so any *other* failure in either is new rather than
absorbed.

**ON `origin/main` at `a91b530a`, 0 ahead / 0 behind, tree clean apart from the
gate's own ledger file.**

**Nothing was overridden. No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no
`SAIRN_SEED_GATE`, in any form. No hook added or restored,
`.claude/settings.json` never committed, NO `api/`, `sql/` OR `tools/` FILE
EDITED, no `CLAUDE.md` edit, no auditor clone entered, no `--force`.** Two
gates refused this push and both were true; both were fixed at cause — §6.

---

## 1. Committed and pushed

| | |
|---|---|
| HEAD / `origin/main` | **`a91b530a`** — identical, `0 ahead / 0 behind` |
| my b14 commit | **`a91b530a`** `test(b14): two-axis red arm fixed at cause, the OWNER line, and six arms with every failure path driven` — **tested as an ancestor of `origin/main`** |
| push | **LANDED without `--force`** (`grep -ci force` over the push log: 0). It took **two rebases and four attempts**, all non-fast-forward races with other sessions plus the two gate refusals in §6 |
| claim | `tests` — **HELD, released after this handoff, the report, the digest and `SAIRN-latest-cody.md`** |
| committer identity | `fx <fx@example.invalid>`, this clone's LOCAL config — unchanged |

Files in the landed commit — **11, and `api/`, `sql/` and `tools/` appear
nowhere in it**:

```
docs/2026-10-14-cody-b14-blob-conversion-routed-to-hank.md  | 134 +
docs/MASTER-PLAN.md                                         |  16 +-   (regenerated)
docs/known-red-suites.json                                  | 118 +-
docs/scrutiny-flags.json                                    | 150 +    (the gate's own ledger)
docs/tier-a-reviews.json                                    |  21 +    (the obligation, §6)
docs/traceability-matrix.md                                 |   8 +-   (regenerated)
tests/run_b14_leg_aftercare_probe.py                        | 325 +    (NEW)
tests/run_scope_gate_unfetched_base_probe.py                |  11 +-
tests/run_two_axis_tier_parser_probe.py                     |  60 +-
tests/sairncare_compliance_window_boundary.test.js          | 307 +    (NEW)
tests/sairnlegacy_reservation_lock.js                       |  77 +-
```

**One expected residue:** `docs/scrutiny-flags.json`, the gate's ledger row for
the *successful* push, written after the commit was built. `git worktree list`
shows **only the live clone**.

**`docs/tool-owner-map.json` was REVERTED rather than committed, deliberately.**
Running `python tools/tool_owner_map.py` regenerated it — it is a declared
`OWNER-INTENDED BARE-RUN WRITER` and producing the map *is* the run — and its
diff was **352 lines of other sessions' claim-history churn** (`claim_commits_read`
2539 → 2673), which is not this batch's to land. The OWNER change in §3 was
verified through the generator's `owner_lines()` function instead, which does
not write.

---

## 2. Per item — six of six

| item | state |
|---|---|
| 1. `run_two_axis_tier_parser_probe.py`'s red arm vs its register row | **DONE. FIXED AT CAUSE.** exit 1 → **exit 0, 17/17** — §3 |
| 2. the OWNER line, green + wired, and the ten blob conversions routed | **DONE.** `cody`, **13/13**, wired; the ten **ROUTED to hank in `docs/`** — §3 |
| 3. three arms: aftercare collision, anchor, `leg_clergybookings` | **DONE.** Collision arm RED on purpose; anchor arm green; **35/36 → 36/36** — §4 |
| 4. three compliance arms N4 names | **DONE. All three GREEN**, plus two found by measuring, RED on purpose — §5 |
| 5. a counterfactual per arm, plus the register rows | **DONE. 17 counterfactual runs; 4 register rows** — §4, §5, §7 |
| 6. push without force, confirm landed | **DONE** — §1 |

---

## 3. Items 1 and 2

### Item 1 — the diagnosis in the row was right, and is the fix that was applied

`row_problems()` was over-collecting **HEADLINE**, a **DOCUMENT-scope** label,
into arm 2 whose own criterion says **row-level**.
`tools/criticality_tier_check.py:1003-1008` re-reads the whole register looking
for the `N resources, A A, B B, C C` sentence and says in its own comment that
it is *"a check on the DOCUMENT's prose, not on the table parse() builds"*.
Every fixture in that probe is a two-row table with **no summary sentence by
construction**, so the could-not-tell fired on every run and said nothing about
the parser — the same run printed `RESOURCE_ROWS:2` and
`ROWS_MIGRATED_TWO_AXIS:2 of 2`, and arms 3-14 passed on that identical fixture
the whole time.

**RED CAPTURED FIRST:** exit 1, `row problems: ['HEADLINE']`. **No `tools/`
file edited and no arm edited to turn it green** — arm 2's assertion is
unchanged, only the *scope* of the helper feeding it.

**The other repair the row offered was rejected with a reason**, written into
the file: giving the fixtures a headline means either a typed sentence that is a
second copy of `NEW_ROWS` (stale the first time a fixture row changes) or a
derived one that makes the headline check agree with itself on every arm — a
check that can no longer fail. Scoping one helper changes one judgement;
rewriting the fixtures changes fourteen.

**Two controls, both failure paths driven** on scratch copies with `REPO`
pinned:

| run | result |
|---|---|
| unmodified copy | **EXIT 0** — so a red cannot be the harness |
| a bogus label added to the exclusion set | **EXIT 3 COULD NOT RUN**, naming it |
| the fixture given a matching headline | **EXIT 1**, arm 2 still ok and **the control FAILS** |

### Item 2 — the OWNER line, and why the ten are routed and not converted

`# OWNER: cc` → **`cody`**, on Michael's decision. `tools/tool_owner_map.py`
treats that line as **AUTHORITATIVE**, so until now every finding in a file
sitting in `tests/` routed to cc. **cc's authorship is kept on the line above
rather than erased.** Verified green *after* the edit — **EXIT 0, 13/13** —
and verified **WIRED by measurement**: `tools/run_all_tests.py`'s own
`discover()` returns it in the 425-file `.py` list.

**The ten blob conversions are ROUTED, and that was the open question b13 left.**
All 58 unconverted sites live in `api/`, which is hank's.
`docs/2026-10-14-cody-b14-blob-conversion-routed-to-hank.md` names **the first
ten in `--list RAW` order** (the tool's own order — no cherry-picking), each
with its branch opener, its table, **the paired READ that decides the column
keys**, and **two failing-first commands of different shapes** per site.
**`docs/blob-conversion-coverage.json` is UNTOUCHED at `unconverted: 58`** —
re-pinning without a conversion is the one use the tool's own note forbids.
Two of the ten are **generic dispatchers** covering five resources between them
(`sd_blocks`/`sd_bundles`/`sd_slab_history`, and `sd_hr_employees`/`sd_hr_certs`
— **person data**), so a drop of more than ten in the count means something
other than these ten moved.

---

## 4. Item 3 — and the counterfactual found a defect in my own controls

### `tests/sairnlegacy_reservation_lock.js`: 35/36 → **36/36, 62 assertions, exit 0**

**THE HANDLER WAS RIGHT THE WHOLE TIME.** Measured, the odd one was
`leg_clergybookings (unprovisioned write -> 400)` —
`CLERGY_BOOKING_WINDOW_REQUIRED`, refused *before any upstream call*. The loop
hardcoded `resource === 'leg_bookings'` when building the
precondition-satisfying payload, so when the same overlap guard was extended to
`leg_clergybookings` on 2026-10-14 — a second `SPECS` entry in
`api/_lib/leg-overlap.js`, not a second copy of the block — this arm silently
stopped satisfying the precondition there and **counted a PRECONDITION refusal
as a PROPERTY failure**, the exact shape the b10 comment above it names.

The payload is **derived from `LEG_OVERLAP.SPECS[resource].groupField`** now, so
`leg_bookings` keys on `facility_id`, `leg_clergybookings` on `clergy_id`, and a
fourth overlap resource is covered the day it is added. **No `api/` file edited;
the map is read.**

**THE COUNTERFACTUAL FOUND A DEFECT IN THE CONTROLS I HAD JUST WRITTEN, which
is the whole reason for driving rather than asserting.** They sat *after* the
three count assertions, and `ok()` throws — so an emptied `SPECS` map reported
an unattributable **34/36** from the count arm and the control naming the cause
was **never reached**. They run **before** the counts now. *A diagnostic placed
downstream of the thing it diagnoses is not a control.*

**And a fourth control was written and REMOVED, with its reason recorded in the
file so nobody re-adds it:** *"every spec names a groupField"* can never be the
arm that fires, because a missing `groupField` causes the 400 that the
precondition control catches first. The two conditions are causally linked. It
was an assertion wearing a control's clothes.

| counterfactual | result |
|---|---|
| unmodified | **EXIT 0, 36/36** |
| the hardcoded name restored (**the pre-fix state**) | precondition control fires **BY NAME**, not as 35/36 |
| `start_time` dropped from the derived payload | precondition control fires |
| `SPECS` emptied | not-empty control fires, `specs: []` |
| a spec naming a non-SAIRNlegacy resource | wrong-app control fires |
| a spec stripped of `groupField` | precondition control fires — **why the 4th control went** |

### `tests/run_b14_leg_aftercare_probe.py` (NEW, exit 1, ARM 1 red on purpose)

**ARM 1** is fourth's b20 **F4** made checkable. Measured on **both**
derivations, each **extracted from source and run in node, never retyped**:
`('CS-7','1 Week')` and `('CS-7-1','Week')` both produce **`AC-CS-7-1-WEEK`**.
The upsert is `on_conflict=license_hash,aftercare_id` with
`resolution=merge-duplicates`, so **a collision silently overwrites a different
case's check-in and returns 200.** Arm E4 of
`api/sd-data-leg-role-matrix.test.js` cannot catch it because **both copies
agree on the wrong answer** — a cross-implementation test is necessary and not
sufficient. **Fix routed to hank**; this probe has no opinion on which of the
two shapes (encode the separator / hash the pair).

**ARM 2** (green) locks the degradation nothing tested: D4 in
`api/sd-data-leg-overlap.test.js` anchors on `function clergyBookingConflict(`
and routes to **UNPROVEN at exit 3** when that anchor moves. Driven on a
**fixture copy** of the HTML through `LEG_HTML`; **no `api/` file edited**.

| counterfactual | result |
|---|---|
| unmodified probe | EXIT 1, arm 1 red |
| a delimiter-safe key applied to **both** extracted derivations | **EXIT 0, ARM 1 GREEN** — so arm 1 measures the fix, not something else |
| the mutated overlap suite against the real HTML | EXIT 0 — the mutation did not break the suite |
| the exit-3 degradation **removed** from a scratch copy | **arm 2 goes RED** (that suite exits 0 where it should be 3) |

---

## 5. Item 4 — the three arms N4 named, and two more that measuring found

`tests/sairncare_compliance_window_boundary.test.js` (NEW): **13 passed, 2
failed.** Written in `tests/` against the module's **public exports** and the
**REAL seed** — `api/_lib/compliance-rules-staff-join.test.js` is where these
would naturally sit and `api/` is hank's.

**The three N4 named are all GREEN:**

1. **the exact anniversary** — evaluated 2026-11-02 the window is `2025-11-03`
   and the verdict is a determinate PASS; **on** 2026-11-03 the window **ROLLS
   to `2026-11-03`** rather than being decremented, so the same hours now fall
   outside it. That second fact is what makes day zero necessary.
2. **a `2024-02-29` hire in a COMMON year** — `window_from 2026-02-28`, with the
   **paired positive** that a **leap** year keeps `2028-02-29`, so the
   normalisation is **conditional on the target year** rather than applied to
   every 29 February hire; and the day before the normalised anniversary is
   still the previous window, `2025-02-28`.
3. **the day-zero shortfall** — `meets === null` **strictly**, not false,
   because `!meets` would read the two alike; the reason names the window
   opening today; the shortfall is still reported beside the withheld verdict;
   and the **paired positive** that meeting the requirement **on** day zero is
   still `true`, which is the module's own claim.

**All three failure paths driven** on scratch copies of
`api/_lib/compliance-rules.js`: the anniversary comparison made inclusive → arm
1 RED; the leap normalisation removed → arm 2 RED; the day-zero withholding
removed → arm 3 RED; the unmodified module → all three green.

**TWO ARMS RED ON PURPOSE, FOUND BY MEASURING, BOTH hank's:**

* **X1 — the hand-driven comment is now WRONG, not merely unproven.**
  `api/_lib/compliance-rules.js:929-931` says *"evaluated 2026-11-03 →
  NON-COMPLIANT"* and the module returns **`meets === null`**. The day-zero
  withholding landed **after** that sentence was hand-driven on 2026-09-29 and
  superseded it. It is the kind of claim a reader checks least, because it names
  its own evidence.
* **X2 — the withholding message cites a field the finding does not carry.**
  It tells the reader *"`hours_window_days_remaining` says how much of it is
  left"*. `window_days_elapsed` and `window_days_remaining` **are** computed
  (`:658`, `:663`) and stay on the internal window object, while the comment at
  `:943` claims the module hands *"every consumer"* both — and
  `evaluateTraining`'s staff finding exposes **neither**. Same shape as a
  citation to a file that does not exist. **X2 carries its own control**
  asserting the message really does cite the field, so it cannot be satisfied
  by the message changing instead.

---

## 6. Item 5's other half, and the two gates that refused

**Two gates refused this push and both were true. Neither was overridden.**

* **`tier-a`** — `leg_aftercare` is Tier A and the new probe touches code
  serving it. **RECORDED** with `python tools/tier_a_review_gate.py --open`,
  **assigned to fourth**; cody cannot discharge its own. The obligation text
  says what a reviewer should check. `docs/tier-a-reviews.json` committed with
  the change it covers.
* **`derived-docs`** — `docs/MASTER-PLAN.md` and `docs/traceability-matrix.md`
  stopped matching their sources because this push adds two test files.
  **REGENERATED with their own generators**, never hand-edited. The whole diff
  is this batch's: sairncare 33 → 34 suites, test files on disk 961 → 963.

**AND THE MATRIX'S OWN OUTPUT WAS ACTED ON RATHER THAN READ PAST.** The
regenerated document listed both new files under *"traced to no stated
requirement"* — this batch would have been adding to that debt while closing
other things. A real `REQUIREMENT:` header was added to each (not the subject
the filename already names), and the figure moves the right way: declared
citations **336 → 338**, traced **744 → 746 of 963**, **77.4% → 77.5%**.
Verified through the generator's own `declared_requirements()`, not by eye.

Two rebases were needed; **`python tools/sairn_rebase_resolve.py`** resolved
three conflicts (the two generated documents regenerated, `tier-a-reviews.json`
merged 256 + 1 + 1 = 258 and validated). **Every suite was re-run after every
rebase**, and again at the landed sha.

---

## 7. The register — four suites touched, four rows written, none left without one

`docs/known-red-suites.json`: **entries 64 → 65, recovered 37 → 39, not_red 4
unchanged.**

| file | row | why |
|---|---|---|
| `tests/run_two_axis_tier_parser_probe.py` | `entries` → **`recovered`**, exit 0 | fixed at cause; **the superseded `entries` row is kept VERBATIM** under `superseded_entries_row` rather than deleted, so the old diagnosis stays readable beside the repair |
| `tests/run_scope_gate_unfetched_base_probe.py` | **NEW in `recovered`**, exit 0 | **it had NO ROW AT ALL**, which by this file's own definition meant **UNMEASURED**, not green |
| `tests/run_b14_leg_aftercare_probe.py` | **NEW in `entries`**, exit 1 | red on purpose; `expected_red_scope`: **ARM 1 ONLY** |
| `tests/sairncare_compliance_window_boundary.test.js` | **NEW in `entries`**, exit 1 | red on purpose; `expected_red_scope`: **X1 and X2 ONLY** |
| `tests/sairnlegacy_reservation_lock.js` | `recovered` **updated in place** | still exit 0, **62 assertions not 59**, and the 35/36 it never mentioned is fixed at cause |

**Final re-run at `a91b530a`, after the last rebase:**

```
EXIT=0  python tests/run_two_axis_tier_parser_probe.py        17 arms
EXIT=0  python tests/run_scope_gate_unfetched_base_probe.py   13 arms
EXIT=0  node   tests/sairnlegacy_reservation_lock.js          62 assertions
EXIT=1  python tests/run_b14_leg_aftercare_probe.py           ARM 1 only
EXIT=1  node   tests/sairncare_compliance_window_boundary.js  X1 and X2 only
```

---

## 8. Open, with the exact next step

1. **→ HANK. The `leg_aftercare` key fix.** `tests/run_b14_leg_aftercare_probe.py`
   ARM 1 is RED and goes green on its own when the key stops being
   delimiter-ambiguous. **NEXT STEP:** encode the separator or hash the pair, in
   `api/sd-data.js:15610` **and** `sairnlegacy.html:4214-4216` — **both copies,
   or the probe's own agreement control fails.** The counterfactual already
   proves a delimiter-safe key turns ARM 1 green.
2. **→ HANK. The two compliance comments/fields (X1, X2).** **NEXT STEP for X1:**
   `api/_lib/compliance-rules.js:929-931` — say the anniversary verdict is
   WITHHELD (`meets: null`), or delete the date. **For X2:** surface
   `window_days_elapsed` / `window_days_remaining` on the staff finding as
   `hours_window_days_elapsed` / `hours_window_days_remaining`, **or** stop
   citing a field that is not there. Either direction turns the arm green.
3. **→ HANK. The ten blob conversions.** Everything needed is in
   `docs/2026-10-14-cody-b14-blob-conversion-routed-to-hank.md`. **NEXT STEP:**
   take site 1, capture the failing-first `grep -c "data: payload"` **before**
   the edit, convert, re-run `--list RAW` / `--list CONVERTED`, repeat; then
   `python tools/blob_conversion_coverage.py --repin` **once, at the end, never
   by hand**. `unconverted` must fall to **exactly 48**.
4. **→ FOURTH. The Tier A review obligation on `leg_aftercare`**, opened
   2026-10-14 by cody and **assigned to fourth**. **NEXT STEP:**
   `python tools/tier_a_review_gate.py` to read it, then discharge; the gate
   refuses any record whose reviewer is its own author, so cody cannot close it.
   Anybody may `--takeover` after 48h.
5. **→ WHOEVER OWNS `docs/tool-owner-map.json`.** It is **stale by 134 claim
   commits** (`claim_commits_read` 2539 on disk vs 2673 derivable) and does not
   yet reflect this batch's OWNER change. **NEXT STEP:** `python
   tools/tool_owner_map.py` in a clone with nothing else uncommitted, and commit
   the regeneration **alone** — it was deliberately not bundled here.
6. **FROM b13, STILL OPEN AND NOT MINE — T16, T17, T18 → HANK.** Each has a RED
   arm in `tests/run_b12_routed_findings_probe.py` that goes green on its own
   when fixed; `--ablate` shows which fix each measures. `api/sd-data.js:7179`,
   `api/sen-auth.js:263`, `api/_lib/compliance-rules.js` (`applies_to_positions`
   unvalidated). **N4 is now DISCHARGED by item 4** — the three arms exist.
7. **FROM b12 → CC (`tools/`). THE PUSH-GATE HALF IS CLOSED; THE FLOOR HALF IS
   NOT, AND IT HAS MOVED.** Both re-measured here rather than carried:
   * **CLOSED.** `grep "THE BLANKET FORM STILL WORKS" tools/sairn_push_gate_hook.py`
     now hits only **line 1254**, a comment that **names the correction**
     (*"THIS COMMENT SAID … UNTIL 2026-10-14"*). The refusal text this push
     actually printed derives the override hint from `gate_skip` and says the
     blanket form *"no longer works at all"*. Nothing open.
   * **STILL OPEN, and the b12 citation is stale.** The floor is
     `_MIN_TEST_FILES_FLOOR = 370` at **`tools/run_all_tests.py:284`**, not in
     the push gate, and it is now a **ratchet** read from
     `docs/test-file-floor.json` with the literal as a last resort. **NEXT
     STEP:** read `docs/test-file-floor.json` against `discover()`'s real
     count — 963 test files on disk, 425 of them `.py` — and decide whether the
     pinned floor is current. Do **not** lower it; the file's own comment says a
     detector that lowers its own floor is blessing its own fix.
8. **→ `CLAUDE.md` OWNER.** Its push-protocol section now **agrees** with the
   code on `SAIRN_SEED_GATE=off` (corrected 2026-10-14). No action found open.

---

## 9. Claims held

`tests` — **HELD at the time of writing** (`cody-1792024820`, claimed
2026-10-15T00:40:20Z), for all six b14 items. Released after this handoff, the
report, the digest and `SAIRN-latest-cody.md`.

**The claim's FILES list named `tests/run_b14_compliance_anniversary_probe.py`
and the item-4 arms landed as `tests/sairncare_compliance_window_boundary.test.js`
instead** — a `.js` suite beside a `.js` module, driving its public exports
directly, rather than a Python wrapper around `node`. **A claimed FILES list is
an intention, not a record of what changed.** Said here so the next session does
not read the claim as a change log; the authoritative list is §1.

`check` was **CLEAR ON WORDS**, and reported honestly that the file overlap
against hover and hover2 **could not be proven either way** because only one
side declared a FILES list. Read rather than waved past: both are audit roles
that write only to their own logs, and the two LIVE build claims (cc on
`tools/`, hank on `api/`) are **disjoint** from everything in §1.

---

## 10. Cleanup

`git worktree list` shows **only the live clone** — no probe left one behind.
Evidence lives in the commit message, in each suite's own output, and in the
`docs/known-red-suites.json` rows — **never in a temp path**, which is why what
follows costs nothing.

**NOT DONE, AND SAID RATHER THAN CLAIMED: the scratchpad was NOT cleared.**
`rm` inside
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\ee6c4b56-96e2-4664-a9e1-a787ca0141ff\scratchpad\`
was **refused by the permission layer**, twice, so **51 files remain there** —
the per-suite run logs, the four counterfactual drivers
(`cf_reslock.py`, `cf_aftercare.py`, `cf_compliance.py`, `find_odd.py`),
`measure_compliance.js`, `write_rows.py` and the commit message. **Nothing in
the repo and nothing on the Drive depends on any of them**, and no deliverable
cites a path under that directory. It is a session-scoped temp directory, so
leaving it is harmless — but this section said "removed" in the first draft and
that would have been a false statement about work not performed.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\ee6c4b56-96e2-4664-a9e1-a787ca0141ff.jsonl`

---

*Written before the report, at a point where everything above is committed and
pushed except this file and the three artefacts that follow it.*
