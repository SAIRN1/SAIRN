# Handoff — cody, batch b13, 2026-10-14

**STOPPED EARLY ON INSTRUCTION AT 71% CONTEXT. ITEM 1 IS DONE AND LANDED; ITEMS
2, 3, 4 AND 5 WERE NOT REACHED AND ARE NOT STARTED.** Nothing is half-finished —
the one item in flight was taken to a clean point, committed and pushed, and no
file belonging to an unstarted item was touched.

**ON `origin/main` at `0c7d4ac8`, 0 ahead / 0 behind, tree clean apart from the
gate's own ledger file.**

**Nothing was overridden. No `SAIRN_SEED_GATE` and no `SAIRN_GATE_EXEMPT`, in
any form. No hook added or restored, `.claude/settings.json` never committed, NO
`api/`, `sql/`, `tools/` OR `CLAUDE.md` FILE EDITED, no auditor clone entered, no
`--force`.**

---

## 1. Committed and pushed

| | |
|---|---|
| HEAD / `origin/main` | **`0c7d4ac8`** — identical, `0 ahead / 0 behind` |
| my b13 commit | **`0c7d4ac8`** `test(b13): the retired replay's REPLACEMENT …` — **tested as an ancestor of `origin/main`** |
| push | **LANDED without `--force`**, first attempt, no gate refusal |
| claim | `tests` — **HELD, released after this handoff, the report, the digest and `SAIRN-latest-cody.md`** |
| files changed | `tests/app_session_isolation_probe.py` only |
| committer identity | `fx <fx@example.invalid>`, from this clone's LOCAL config — unchanged |

One expected residue: `docs/scrutiny-flags.json`, the gate's own ledger row for
this push, committed with these artefacts. A leftover `sairn-sab-qtbp6o8m`
worktree from the probe run was removed and pruned; `git worktree list` shows
only the live clone.

---

## 2. Per item — one done, four not reached

| item | state |
|---|---|
| 1. the replacement for the retired counterfactual | **DONE AND LANDED.** Exit 0, ablation **4 of 4** — §3 |
| 2. `run_two_axis_tier_parser_probe.py`'s red arm vs its register row | **NOT REACHED. NOT STARTED.** No file touched — §4 |
| 3. `run_scope_gate_unfetched_base_probe.py` OWNER line → cody | **NOT REACHED. NOT STARTED.** No file touched — §4 |
| 4. the `leg_aftercare` collision arm, the anchor arm, the `leg_clergybookings` arm | **NOT REACHED. NOT STARTED.** No file touched — §4 |
| 5. the next ten blob conversions and the ratchet | **NOT REACHED. NOT STARTED.** Pin still 58 — §4 |
| 6. push without force and confirm landed | **DONE** — §1 |

**Nothing was half-applied for items 2–5.** No arm was added and left failing, no
register row was edited in anticipation, and
`docs/blob-conversion-coverage.json` is untouched at `unconverted: 58`.

---

## 3. Item 1 — the replacement, and the ablation found two defects in itself

`python tests/app_session_isolation_probe.py` → **exit 0, ALL 13 ARMS PASS (8
mutations)**, and the new section reports **2 same-reason mutations INVISIBLE to
the pre-repair predicate and REFUSED by the current one.**
`--ablate` → **4 of 4.**

**FAILING-FIRST, AND THE RED IS THE STATE THIS REPLACED.** b12 retired the
pre-fix replay with the measurement that ruled out re-basing, and wrote the cost
at the top of the file: *"what is no longer shown is that the OLD predicate was
blind to it."* `run_probe` proves the CURRENT suite refuses mutations 6, 7 and 9;
nothing proved the pre-repair form was blind to them. The suite exited 0 with the
gap recorded. That is the red.

**`old_predicate_is_blind()` REPLAYS NOTHING, which is the whole design.** The
property under test is ONE EXPRESSION, not a suite: `out.code !== 401` versus
`out.code === 403 && … FORBIDDEN`. Both predicates are applied **directly** to
the refusal shape each mutation produces. No worktree, no historical suite, no
world-state — so nothing a later gate landing elsewhere can invalidate.

**EVERY INPUT IS DERIVED**, because a retyped predicate or status code is the
second-copy defect this file has already paid for twice:

| input | source | measured |
|---|---|---|
| NEW predicates | the two `ok(` expressions in `tests/app_session_isolation.js` | gate demands **403 FORBIDDEN**, oracle demands **400** |
| OLD predicate | HISTORY, the same DERIVED commit the retired control located (`798543873912^`) — **one expression read, never the file to run** | `code !== 401` |
| each mutant status code | the MUTATION TABLE's own replacement text | 403→500, 400→404 |

Anything underivable is **exit 3 UNPROVEN** with the reason named, never a pass.

**MUTATION 6 IS DECLARED OUT OF SCOPE RATHER THAN COUNTED.** It changes an app
NAME, not a status code, and the arm it trips did not exist before the repair —
precisely the trap the first version of the retired control fell into:
hand-reverting a predicate does not remove an arm. Reported as `CANNOT`.

**TWO CONTROLS, BOTH DIRECTIONS.** The new predicate must ACCEPT the healthy
shape, or *"it refuses everything"* satisfies every REFUSED line. The old
predicate must REFUSE 401, or *"it accepts everything"* satisfies every BLIND
line — which is also why 401 was never a legitimate mutation in this table.

**AND THE ABLATION FOUND TWO DEFECTS IN ITS OWN CONTROLS, which is why it was
worth driving rather than asserting:**

* **CONTROL A could not fail.** The healthy SHAPE and the predicate's EXPECTED
  error code were one name, so overriding it moved both together and they still
  agreed. Split into `GATE_SHAPE_ERR` and `GATE_OK_ERR`.
* **CONTROL B was TAUTOLOGICAL.** It asked whether the predicate refuses
  `OLD_BLIND_TO` — true by construction for every value. It now asks whether it
  refuses `DERIVED_OLD`, the code HISTORY records, which is the actual property.

Both were invisible until the failure path was driven. **An arm whose failure
path has never been run is an assertion, not a check.** `force` is the one
injection point, never set on an ordinary run, and the ablation needs no file
copy, no scratch script and no edit to the suite.

---

## 4. Open, with the exact next step — including everything not reached

1. **ITEM 2 → CODY. `tests/run_two_axis_tier_parser_probe.py` is RED on one
   arm** — *"2. the NEW six-cell shape parses, raises no row-level problem, and
   counts as migrated"*. **Measured in b12 and confirmed PRE-EXISTING** by
   stashing and re-running, so it is not b12's or b13's doing. **NEXT STEP:**
   read its `docs/known-red-suites.json` row first, then either fix the arm AT
   CAUSE or correct the row — **no silent skip, and do not edit the arm to turn
   it green.** Not started in b13; nothing touched.
2. **ITEM 3 → CODY. `tests/run_scope_gate_unfetched_base_probe.py` still carries
   `# OWNER: cc`** on line 2 while living in `tests/`, which the register's own
   directory-owner rule makes cody's. **Michael has decided it is mine.**
   **NEXT STEP:** change the OWNER line to `cody`, then verify the suite is
   green (it was **13/13** in b12) and that it is WIRED — i.e. something runs it.
   Not started; the file is untouched.
3. **ITEM 4 → CODY, three arms, none written.**
   * the **`leg_aftercare` key-collision** arm, failing-first: `('CS-7','1 Week')`
     and `('CS-7-1','Week')` must not derive the same `AC-CS-7-1-WEEK` key.
     Source: `docs/2026-10-14-fourth-b20-leg-role-matrix-discharge.md`.
   * the **function-name anchor** arm, which must degrade to **UNPROVEN at exit
     3** rather than passing when its anchor moves.
   * the **`leg_clergybookings`** arm at `tests/sairnlegacy_reservation_lock.js:330`
     — **or** accept **35/36 explicitly in the register with the reason.** The
     choice is the deliverable; 35/36 with no recorded reason is the one outcome
     that is not acceptable.
4. **ITEM 5 → CODY. The next ten of the 58 unconverted blob sites.**
   `docs/blob-conversion-coverage.json` is **untouched at `unconverted: 58`,
   `converted: 34`**. **NEXT STEP:** convert ten, ratchet the pin down **with the
   tool** (`python tools/blob_conversion_coverage.py --repin`, never by hand),
   and for EACH conversion record the command that shows the old shape failed
   first. **ROUTING CONSTRAINT THAT WAS NOT RESOLVED:** the sites live in `api/`,
   which is hank's, and my b13 claim declared `api/` read-only. **Whoever takes
   this must either hold an `api/` claim or route the ten conversions to hank
   with the failing-first command per site.** That question is open and is the
   first thing to settle, before any conversion.
5. **FROM b12, STILL OPEN AND NOT MINE — T16, T17, T18 and N4 → HANK.** Each has
   a RED arm in `tests/run_b12_routed_findings_probe.py` that goes green on its
   own when fixed; `--ablate` shows which fix each one measures.
   `api/sd-data.js:7179` (a second EVV write replaces `clock_in_at` with no
   trail), `api/sen-auth.js:263` (`setup` can demote the last owner),
   `api/_lib/compliance-rules.js` (`applies_to_positions` contents unvalidated),
   and `api/sd-data-cross-tenant-dispatchers.test.js:577` (a coverage claim
   citing a path that does not exist — a one-line comment correction).
6. **FROM b12 → FOURTH.** The Tier A review obligation in
   `docs/tier-a-reviews.json` on `grd_boq_rates` / `grd_rounds`, assigned.
7. **FROM b12 → CC (`tools/`).** `MIN_TEST_FILES` 370 against 796 discovered;
   `tools/sairn_push_gate_hook.py:988-991` says *"THE BLANKET FORM STILL WORKS"*
   while `:1377-1392` refuses it. **→ `CLAUDE.md` owner:** it still says
   *"`SAIRN_SEED_GATE=off` still works"*; the code contradicts it.

---

## 5. Claims held

`tests` — **HELD at the time of writing**, claimed for all six b13 items.
Released after this handoff, the report, the digest and `SAIRN-latest-cody.md`.
**The claim string names files for items 2–5 that were never written**
(`tests/run_two_axis_tier_parser_probe.py`,
`tests/run_scope_gate_unfetched_base_probe.py`,
`tests/sairnlegacy_reservation_lock.js`, `tests/run_b13_leg_aftercare_probe.py`,
`docs/blob-conversion-coverage.json`) — **a claimed FILES list is an intention,
not a record of what changed**, and the only file this batch actually touched is
`tests/app_session_isolation_probe.py`. Said here so the next session does not
read the claim as a change log.

---

## 6. Cleanup

Scratch logs under
`C:\Users\marsh\AppData\Local\Temp\claude\…\scratchpad\` are removed.
`git worktree list` shows **only the live clone** — one `sairn-sab-qtbp6o8m`
worktree left by the probe run was removed and pruned. Evidence lives in the
commit message and in the suite's own `--ablate` output, never in a temp path.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\ec3355ad-083b-4402-a518-3d4e79072c4c.jsonl`

---

*Written before the report, at a point where everything above is committed and
pushed except this file and the three artefacts that follow it.*
