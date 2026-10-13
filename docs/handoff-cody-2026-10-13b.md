# Handoff — cody, batch 27 (b6), 2026-10-13

**NOT PUSHED. Three commits sit locally at `672f61ca`, 3 ahead / 0 behind.**
The push was refused by two gate checks, both true, and the batch's standing
instruction is to record the exact text and stop rather than unblock. Full
verbatim refusal: §3. **Nothing is half-finished** — every item is either
committed or explicitly routed, and the branch loses nothing by sitting.

---

## 1. Committed state

| | |
|---|---|
| HEAD | `672f61ca` (a merge of `origin/main` @ `618cbd9f`) |
| ahead / behind | **3 ahead, 0 behind** — committed, **NOT pushed** |
| commits | `c465743b` tests fix · `5f7bc94f` two routing docs · `672f61ca` merge |
| files changed | 3 under `tests/`, 2 new under `docs/` (both mine, both new) |
| claim | **HELD.** `cody` — released only after this handoff, the report and the digest |

**Scope held exactly:** every code change is under `tests/`. Nothing in `api/`,
`tools/` or any pre-existing `docs/` file was edited. `.claude/settings.json`
was never touched and hooks were never restored. `SAIRN_SEED_GATE=off` was never
used.

---

## 2. Per item

| # | item | state |
|---|---|---|
| 1 | fix the arm-11 thread race | **DONE** — §4 |
| 2 | write the b5 item-8 fix | **DONE in tests/, product half ROUTED** — §4 |
| 3 | check4 arm1 + check7 arms1-2 as real pass or named failure | **DONE — all three are real passes in both remote modes** — §5 |
| 4 | print `sql/sairnlaw_citator_schema.sql` in full + the verification command | **DONE** — last section of the report |
| 5 | METHODOLOGY note on UNPROVEN, propose the rule, route the spec, build nothing | **DONE** — `docs/2026-10-13-cody-b6-methodology-unproven.md` |
| 6 | push and confirm 0 ahead / 0 behind | **BLOCKED — refused, recorded, stopped** — §3 |

Michael's decisions were applied and not revisited: **paralegals stay denied on
`law_portalmessages`** and **trust reconciliation stays owner-only**. Both are
the stated defaults; no code, no test and no document was changed for either,
and no further work was done on them.

---

## 3. Item 6 — the push is refused, and why it was not unblocked

Two checks refused, both true. The verbatim text is in
`<scratch>/b6/REFUSAL-VERBATIM.txt` and reproduced in the report.

**Refusal 1 — EXTERNAL FILE INDEX.** One unindexed file:
`g:\my drive\sairn-status\handoff-fourth-2026-10-16.md`. Fourth's handoff on the
shared Drive. **Nothing to do with b6** — it is the sixteenth row of the
standing loop that b4 and b5 each declared rows for.

**Refusal 2 — `docs/TOOLING-INVENTORY.md` no longer matches its sources.**
*"It was clean at the base commit and is not at this tip, so this push is what
changed the answer."*

**That attribution is correct, and I tested it rather than accepting it**,
because my commits touch only `tests/` and add no `tools/` file:

- `origin/main` @ `618cbd9f` alone, in a throwaway clone without my commits:
  `tooling_inventory.py --check` → **exit 0, "OK: matches the repo"**.
- Each of my commits walked in a throwaway clone: **`c465743b` already FAILS** —
  the first one, three `tests/` files.
- **Why:** the generator's own declared legs include *"tools invoked by
  tests/ — 232 — tests/\*\*/\*.py, \*.js"*. Item 3 made `check4_probe.py` invoke
  `tools/sairn_seam_check.py` and `check7_probe.py` import
  `tools/preauth_oracle_check.py` directly, so the wiring classification of
  those two tools genuinely changed. **The gate is right.**

**Why it was not fixed:** both remedies are `docs/` edits. b6's scope is *edit
only `tests/`; route anything in `api/`, `tools/` or `docs/` to its owner*, and
the batch says *if a push is refused, record the exact text and stop*. Both
instructions point the same way, so the refusal was recorded and the push
stopped. Nothing was overridden.

### The exact next step, one command each

```
python tools/tooling_inventory.py          # regenerate; caused by b6's own tests/ change
# then declare fourth's handoff-fourth-2026-10-16.md in docs/external-files-index.json
git push origin main
```

**Whoever lands these three commits should run the regeneration in the same
push**, because the drift is b6's and will follow the commits wherever they go.

---

## 4. Items 1 and 2 — arm 11 was announcing a race it had not run

`_saver` called `save_reviews()` with **no try/except**. On Windows one of the
two concurrent `os.replace` calls raises `PermissionError` — `os.replace` is
`MoveFileEx(MOVEFILE_REPLACE_EXISTING)`, which fails `ERROR_ACCESS_DENIED` while
the destination is held open, including by another `MoveFileEx` on the same
target. POSIX `rename(2)` has no such failure mode.

**The exception went nowhere**: raised in a thread, printed by `threading`, exit
code untouched — and **both assertions still passed**, because the surviving
writer left a file that parses with no leftovers.

| measurement | result |
|---|---|
| b5, the race driven in isolation, 400 iterations | **305 raised `PermissionError`** |
| b5, this suite, consecutive runs | **12 of 12 carried the traceback; all 12 exited 0** |
| b6, the new arm's condition on the OLD saver, 40 iterations | **RED in 31 of 40** |
| b6, same condition with the retry | **GREEN 40 of 40** |
| b6, this suite after the fix, 6 runs | **0 tracebacks; 0 or 1 retries per run; exit 0** |

On the same red iteration the old arm's conditions were `parses=True`,
`leftovers=[]` — **which is exactly why it was invisible.**

**Safety and liveness are kept apart, and that distinction is the finding.** No
file was ever corrupt; the property the arm exists to prove held throughout.
What fails is that one of two writers *errors instead of completing*.

**What landed in `tests/`:** each writer retries its own save on
`PermissionError` **by name** (a bare `except Exception` would swallow the next
real defect exactly as the missing one swallowed this); a new arm, **first**,
asserts both writers completed; a second asserts no writer failed for an
unrecognised reason; the retry cap is 20, chosen against the measured ~76%
per-attempt rate so exhaustion sits near 1e-11 and is a signal rather than
noise; and the **retry count is printed and deliberately not asserted**, because
zero is correct on POSIX and nonzero on Windows.

**Arm 12 had the same hole with a worse failure mode** and is fixed the same
way: its expected answer is `len(names) == 1`, **which a dead writer also
satisfies**, so it could have reported the read-modify-write race it documents
when one writer never wrote at all.

**ROUTED, NOT FIXED — the product half.** `save_reviews` still has no retry of
its own, and `--open`, `--discharge` and `--reseat-shas` all end there, so two
sessions landing together means one record is not written. Paste-ready patch and
the measurement it owes: `docs/2026-10-13-cody-b6-routed-to-cc.md` §1.

---

## 5. Item 3 — all three arms are real passes now

b5 reported them UNPROVEN whenever a foreign check refused the clean push.
**UNPROVEN is an absence of information and the information was available.**

**check 4's arm 1** runs `tools/sairn_seam_check.py` directly — the gate shells
out to exactly that script — so the answer is check 4's own verdict, first-hand.
**And the criterion is the NOT-FORWARDED count, not the exit code**, which was
found by running it: the seam checker exits **2 on any tree in this repo**
because 19 endpoint/engine pairs are genuinely unparseable (`roleSet()`
destructures its input). The gate treats exit 2 as ALLOW with a disclosed note
and denies only on exit 1, so keying the arm on the exit code would have made it
red for ever over a repo-wide backlog. **Measured: 96 clean, 0 not-forwarded,
19 could-not-tell** — and the could-not-tell number is disclosed in the arm's own
output rather than dropped.

**check 7's arms 1 and 2** call `preauth_oracle_check.scan()` — the same function
the gate imports. **Arm 2 is the sharper one and is why `boundary` is checked
and not only the finding list**: an empty list is produced both by a clean file
and by one whose auth boundary could not be located, because `scan` returns
early in that case. Reading an empty list as a pass would be a checker that is
silent because it never looked.

| mode | check4 | check7 |
|---|---|---|
| local bare remote | **exit 0**, CHECK 4 VERIFIED True | **exit 0**, 13 checks 0 failed |
| default (real remote) | **exit 0**, CHECK 4 VERIFIED True | **exit 0**, 13 checks 0 failed |

**Nothing is UNPROVEN in either probe in either mode.**

A second could-not-read-the-push marker was also added, because without it the
PLANTED arms reported FAILED on a run where the check was never reached:
`register_feed_gate` denies with *"stdin is not a terminal and carried NO ref
lines"*, and its own text says a nested `git push` inside a script cannot
reproduce the ref list git hands a hook — *"ISSUE THE PUSH DIRECTLY … there is
nothing wrong with the change."* A probe drives every push from Python, so it is
permanently in that case.

**Fail-first for all three, 10 arms, driven against planted fixtures.** My first
DISCLOSURE fixture scored **ORACLE** and the arm correctly refused to call that
a fire — the tier needs two distinct quoted names or a `.join(`, and my message
held the verb list inside one string. A fixture that does not reach the tier it
claims to plant is a plant that plants nothing.

---

## 6. Open, with the exact next step

| # | what | owner | exact next step |
|---|---|---|---|
| 1 | **These three commits are unpushed** | next session | `python tools/tooling_inventory.py`, declare fourth's Drive handoff in `docs/external-files-index.json`, then `git push origin main`. Both are `docs/` edits b6 was not permitted to make. |
| 2 | **`save_reviews` has no retry** | **cc** (`tools/`) | Paste the patch from `docs/2026-10-13-cody-b6-routed-to-cc.md` §1.3. Verification is already instrumented: the probe PRINTS its retry count, and with the fix that count should fall to **0 on every run**. If it does not, the fix is not working. |
| 3 | **`tools/unproven_arm_check.py` is specced, not built** | **cc** | Spec in the routed doc §2: three signals, report-only first, with the control pair and current-count measurement this repo requires of a new gate. The false-positive shape is named in advance. |
| 4 | **Run `sql/sairnlaw_citator_schema.sql`** | **Michael**, then anyone | The full file and the one-step sequence are the last section of `SAIRN-report-cody-b6.txt`. Then `python tools/verify_citator_feedback.py --check-only`, then `--write`. Guardian Check 29 is not satisfied until `--write` passes. |
| 5 | **19 unparseable endpoint/engine seams** | unassigned | `python tools/sairn_seam_check.py` lists each with its reason. Each needs a hand-written test like `api/_lib/deadline-endpoint-inputs.test.js`. This is the backlog that makes check 4 exit 2 on every tree. |
| 6 | **The Drive-handoff loop, sixteen rows** | **cc** (the check) + the auditors (the habit) | Make `external_file_index_check.py` read `belongs_in_git` and keep exit 1 only for the session that owes the file; or auditors write handoffs into their own clone, which CLAUDE.md already says. |
| 7 | **Live-verify the sairnlaw role gate** | next session with network | Not attempted in b6. POST `law_trusttx/read` with a paralegal token → expect 403; `law_matterdocs/write` with the same token → expect not-403. |

---

## 7. Evidence and transcript

**Transcript:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\b9e5be49-2b5f-401f-99a3-d7fe4cd27336\`

**Scratchpad:** `…\scratchpad\b6\`

| what | file |
|---|---|
| **the verbatim push refusal, with the attribution test** | `REFUSAL-VERBATIM.txt` |
| arm-11 fail-first, 40 iterations both shapes | `failfirst_arm11.py` → `ff_arm11.log` |
| check4/check7 new arms, 10 arms both directions | `failfirst_check7_arms.py` → `ff_arms.log` |
| the inventory attribution at `origin/main` alone | `attribute_inv.py` → `attrib.log` |
| which commit flips the inventory check | `which_commit_drifted.py` → `which.log` |
| six consecutive gate-probe runs | `probe6/t.txt`, `probe6/p_*.log` |
| both probes, both remote modes | `c4_local.log`, `c7_local.log`, `c4_default.log`, `c7_default.log` |
| the b5 race driver (305/400) | `…\scratchpad\b5\race_repro.py` → `race.log` |

These are evidence for one batch, not checkers, which is why they are in the
scratchpad: `tools/` enrols a file in four governance populations and a one-off
driver belongs in none of them.

---

## 8. What is NOT verified

- **Not pushed.** Nothing in b6 is on `origin/main`. Every claim here is about a
  local branch at `672f61ca`.
- **No live request to any deployed endpoint**, and no database. The citator SQL
  was not run and `verify_citator_feedback.py` was not run against it.
- **The `save_reviews` retry is routed, not written**, so the product-side
  liveness defect is open and every real caller is still exposed.
- **`tools/unproven_arm_check.py` does not exist** and its current-count
  measurement has not been taken — building it was explicitly out of scope.
- **The 19 could-not-tell seams are disclosed, not resolved.** check 4's arm
  passes on the criterion the gate actually blocks on; it does not claim those
  19 pairs are fine.
