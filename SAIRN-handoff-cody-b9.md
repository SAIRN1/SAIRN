# Handoff — cody, batch b9, 2026-10-14

**ALL SIX ITEMS DONE. ON `origin/main` at `0b7a7a0d`, 0 ahead / 0 behind, tree
clean.** Nothing below is half-finished. Every open thing is open because it
belongs to somebody else, because a tool refused and the refusal is recorded, or
because it is named here as the next batch's work.

**Nothing was overridden. `SAIRN_SEED_GATE` was NEVER used, no hook was restored
or re-added, `.claude/settings.json` was never committed, NO `api/` FILE AND NO
`sql/` FILE WAS EDITED, and no auditor clone was entered.**

---

## 1. Committed and pushed

| | |
|---|---|
| HEAD / `origin/main` | **`0b7a7a0d`** — identical, `0 ahead / 0 behind`, `git status` clean |
| my b9 commits, each tested as an ancestor of `origin/main` | `b2be3d27` items 1–5 · `cd65d82d` the two regenerated derived docs + item 5 applied to the two new suites · `856b9847` the gate's own scrutiny rows · `6204314f` the live-clone re-drive that **corrected two of my own verdicts** — **4 of 4 ANCESTOR** by `git merge-base --is-ancestor` |
| push | **LANDED without `--force`.** One gate refusal repaired at cause, plus four ref-lock/fast-forward races with five sessions pushing |
| claim | `tests` — **released after this handoff, the report and the digest** |
| scope kept | **writes under `tests/` only**, plus `docs/known-red-suites.json` (the register rows items 1–4 owe) and my own root b9 artifacts. The two **generated** docs are the one declared exception — §7 |

---

## 2. Per item

| # | item | state |
|---|---|---|
| 1 | re-drive `tests/run_selftest_sweep_probe.py` alone, bigger cap, `python -u` | **DONE — exit 1 in 246s, and the zero-byte mystery is fully explained** — §3 |
| 2 | drive suites 13–36, one exit-code line each, route every red | **DONE — 1 green, 22 exit 1, 1 exit 2, no timeouts** — §4 |
| 3 | failing-first suite for a SAIRNcare `office_manager` role in four places | **DONE — exit 1, all four places red. CODE ROUTED TO hank** — §5 |
| 4 | failing-first suite for `clock_flags` assigned instead of merged | **DONE — exit 1, and it REPRODUCES the defect live. FIX ROUTED TO hank** — §6 |
| 5 | turn the two WEAKENING lines into assertions; classify the 20 could-not-run arms | **DONE — and NONE of the 20 needs an endpoint, a database or a credential** — §8 |
| 6 | push without force and confirm landed | **LANDED** — §1, §7 |

---

## 3. Item 1 — slow AND block-buffered, which is two causes for one symptom

`python -u tests/run_selftest_sweep_probe.py`, alone, 900s cap: **EXIT 1 in 246
SECONDS**, log **6,235 bytes / 114 lines**, output from the first second.

**THE PREVIOUS 180s TIMEOUT WITH A ZERO-BYTE LOG HAD TWO CAUSES AND EITHER ALONE
WOULD HAVE BEEN MISREAD.** It needs ~246s, so a 180s cap kills it mid-run; and
without `-u`, stdout to a file buffers in 8KB blocks, so a run killed at ~6KB of
output **flushes nothing**. Slow-but-flushing would have left a partial log;
buffered-but-fast would have finished. **It is not a silent suite.**

It found **44 self-tests, 5 arms failed, 0 could-not-tell**, and its
tree-integrity arm passed.

**THE HEADLINE IS A DEFECT IN THE SWEEP'S OWN DISCOVERY, NOT IN ITS SUBJECTS.**
Three of the five failures are tools that have **no `--selftest` flag at all** —
its `SELFTEST_RX` matches the string `'--selftest'` as *text*, and
`tools/first_article_inspection.py:391`,
`tools/subprocess_decode_check.py:96` and
`tools/checker_selftest_check.py:150` each contain that exact string inside a
regex literal or a comment. **The sweep's own comment claims this class was
fixed by comparing against argv rather than searching the file. It was not, and
it is still 3 of 44.** Its tolerance is also spelled for the wrong wording:
`TOLERATE_MISSING` matches `not recognized` while argparse prints
`unrecognized arguments`, so a could-not-run lands in `fails`.

The two real defects it did find are both stale expectations in the **subjects**:
`ooda_phases.py` asserts `<10 records have an injection date` and 249 now do;
`subprocess_decode_check.py` reports 69 text-mode subprocess calls with no
explicit `encoding=`.

---

## 4. Item 2 — the premise was stale, so both readings are recorded

**THE BRIEF SAID 13–36 OF 36. THE LIVE REGISTER SAYS 20 UNDRIVEN, AND
`tests/run_subprocess_decode_probe.py` — the brief's starting point — ALREADY
CARRIED A DIAGNOSIS.** `docs/2026-10-13-fourth-b10-undriven-suites.md` was
regenerated at `c23b4a81`: its 36 was a frozen number read out of a dead
session's temp directory. **I drove the full named range anyway**, so every one
of the 24 has a real exit code, and §4 of the report reconciles both readings.

**Driven one at a time in an isolated worktree, `python -u` / `node`, 180s cap,
exit code from `echo "EXIT=$?"` on its own line. No timeouts.**

| | |
|---|---|
| **exit 0 — GREEN** | **1** — `tests/run_truthy_sum_probe.py`, moved OUT of `entries` into `recovered` |
| **exit 1** | **22** |
| **exit 2 — COULD NOT RUN** | **1** — `tests/sairnfreedom_server_backup_probe.py`, **left exactly as it was** |

**Every one of the 24 carries its `file:line` for the line that produces its
exit code, re-read in the file rather than taken from the runner.** Seven blank
`why` fields filled; the other seventeen carry a dated b9 note.

**ALL 24 ARE REGISTERED TO cody, SO THERE IS NOBODY TO ROUTE THEM TO — the
routing that matters is by CAUSE, and five causes explain most of the 22:**

| cause | suites | owner |
|---|---|---|
| **sairnfreedom gained a 36th resource** and `tests/sairnfreedom_server_backup.js` still hardcodes 35 | #23, and #21 and #24 chain off it; #27 corroborates at 36 in the schema | **tests owner (me)** — one count change clears three rows |
| **sairncare and sairnmechanical gained blind write sites** | #17 (24→25, `REGRESSION sairncare.html 0→1`) and #36 (10/10 and 3/3 vs 9 and 2), two methods agreeing | **tests owner**, then whoever added the sites |
| **19 could-not-tell seams in the seam gate** | #32 and #33 — both are `(code == 0 and …)` and the gate exits 2 | **cc** (`tools/`), the 19 seams are the work |
| **a `credentialStillActive` pre-gate landed after the fixture was written** and now eats the fixture's first reply | #26, and #25 chains off it | **tests owner** — `api/` is correct as written |
| **the same pre-gate's stub is missing its third argument** | #19, all 14 failures, one root cause | **tests owner** — `api/sd-data.js:1936-1938` is correct |
| **text-mode subprocess calls with no `encoding=`** | #13 (6 sites) and the 69 under item 1 | **cc** (`tools/`) |
| `license_keys` missing from the SQL preflight column catalogue | #34 | **cc** (`tools/`) |
| a **false claim live in the sairnfreedom panel** (`sf_trustee_audits` says device-only and is synced) | #22 | **hank** (the panel) + tests owner (the arm) |

**AND I GOT TWO VERDICTS WRONG IN THE WORKTREE AND CORRECTED THEM — §9.**

---

## 5. Item 3 — the office_manager role, red in all four places

`tests/sairncare_office_manager_role.test.js` — **FAILING-FIRST, registered,
wired into NO gate.** `node`: **exit 1, 5 passed, 5 failed, 0 unproven.**

**Michael's open question from b8 is answered: ADD THE ROLE.**
`owner`-as-office-manager was considered and rejected, so the suite asserts the
role itself exists.

| place | state |
|---|---|
| `ROLES_BY_APP.sairncare`, `api/_lib/auth.js` | **A1 RED** — still the six values, read by *requiring the module* rather than regexing its source |
| `api/alf-auth.js` | **B1 RED** (it derives from place 1, and the derivation is FINE — the arm says so) and **B2 RED** — it names the role in **no code line**, and `PROVISIONING_ROLES` is `['owner']` with `MANAGEMENT_ROLES = { owner, billing }`, so **the role would exist with no authority at all** |
| the role `CHECK`, `sql/sairncare_employee_auth_schema.sql` | **C1 RED** |
| the role `CHECK` again, `sql/sairncare_all_remaining_migrations.sql` | **C2 RED** |

**IT DELIBERATELY DOES NOT DUPLICATE THE AGREEMENT PROPERTY.**
`api/role-vocabulary-agreement.test.js` (hank) already pins set-equality between
`ROLES_BY_APP` and every `sql/` role `CHECK`, in both directions, across both of
SAIRNcare's two declarations. **So if the role is added to the server and not to
both CHECKs, hank's own suite goes red before mine.** Arm D1 asserts that net is
still in place, so its deletion would be visible.

**B2 accepts either resolution** — `PROVISIONING_ROLES`, or a new named grantor
constant. Asserting one would dictate the implementation.

---

## 6. Item 4 — the clock_flags defect, reproduced rather than asserted

`tests/sd_data_clock_flags_merge.test.js` — **FAILING-FIRST, registered, no
gate.** `node`: **exit 1, 6 passed, 2 failed, 0 unproven.**

**MEASURED AGAINST THE REAL HANDLER: `clock_flags` after write 1 =
`['clock_in_at']`, after write 2 = `['clock_out_at']`.** The array is
**replaced**. A caregiver who clocks in late and out late loses the clock-in's
`LATE_REPLAY`, and nothing says it ever existed.

**The three passing arms are what make the finding precise rather than a
complaint about merges:**

* **A2** — write 1 really *did* store a `clock_in_at` flag, so A1 is a **loss**,
  not an absence.
* **A3** — the per-field **skew stamps for both halves coexist** on the same row.
  **So per-field keying already works here**, and the defect is in the *unkeyed
  array* specifically.
* **A4** — with a **clean** clock-out the clock-in's flag **survives**, because
  `flags` is empty and the `if` never fires. **That is why nothing has noticed:
  the common case hides it and the audit case does not.**

**A FIXED-ROW HARNESS CANNOT SEE THIS BUG.**
`api/sd-data-sen-evv-clock.test.js` returns one immutable row and this defect
exists only *across* two writes, so my mock store is mutable and the POST of
write 1 becomes the GET of write 2. That is probably why it survived.

**The citation is re-derived every run, not carried.** b8 cited `:6985-6987`;
arm B1 measured **`api/sd-data.js:7062`** at this HEAD. B1 accepts either fix:
merge on `field`, or key per field as the stamps already are.

---

## 7. Item 6 — one gate refusal, repaired at cause, nothing overridden

**The refusal:** `docs/MASTER-PLAN.md` and `docs/traceability-matrix.md` stopped
matching their sources, because this push adds two test files and three register
rows that both documents count. Regenerated with the two commands the gate
itself printed — `python tools/master_plan.py` and
`python tools/traceability_matrix.py`, both exit 0, both *"every leg closed"*.

**THAT IS THE ONE DECLARED EXCEPTION TO b9's `tests/`-ONLY SCOPE, and it is a
generator the gate demanded rather than an authored `docs/` edit.** Said out
loud here rather than left for someone to find in a diff.

**Then four ref races** with five sessions pushing — one
`cannot lock ref 'refs/heads/main'`, three `fetch first`. Resolved by
fetch-merge-retry. **No conflicts and no `--force`.**

**THE LEDGER FLAGGED ALL THREE OF MY SUITES `WEAKENING`, ON THE SAME PROSE
SHAPE, AND IT WAS RIGHT ABOUT THE SHAPE.** Every flagged detail is a closing
line or a section header claiming the suite is registered and that no gate reads
it. **All three are now backed by arms E1/E2 (§8). I MAY NOT SIGN ANY OF THEM
OFF** — I wrote the commits they accuse, which is the self-review the Tier A
gate refuses at write time. **The rows are left standing and routed to any
session except cody.**

---

## 8. Item 5 — the prose became assertions, and the 20 need none of what was expected

### The two flagged lines

**`:458` was an arm LABEL and `:649` was a `console.log`.** The answer was not
to argue the flag down but to make the lines carry assertions, because **a
requirement stated only in an arm's name is a requirement nothing checks.**

**C1 was SPLIT**, because two propositions were tangled in one arm:

* **C1** now asserts **at source** that the handler *requires* an expiry — the
  action, `expires_at` and `ALF_MAR_GRANT_MAX_HOURS` all named. Answerable now.
  **It FAILS.**
* **C1b** keeps the behavioural question — whether a missing expiry is
  *refused* — and stays **UNPROVEN**, which is still correct: a 400 from an
  action that does not exist is the dispatcher talking, not the handler.

**E1 and E2 replace the closing line's two claims** and both PASS: E1 asserts
the suite *is* in `docs/known-red-suites.json`; E2 **measures** that no file
under `tools/` names it. **A suite that tells you it is harmless is not evidence
that it is.** The same two arms were then added to both new suites (§7).

`tests/mar_billing_grant.test.js`: **7 passed, 17 failed, 4 unproven** (was
5/16/4). **The b8 value is kept in `tail_b8`** so a hand-moved count cannot be
mistaken for a changed app.

### The 20 could-not-run arms, by exact prerequisite

**NOT ONE OF THE 20 NEEDS AN ENDPOINT, A DATABASE, OR A CREDENTIAL. All three of
those categories are ZERO.** The real prerequisites are four, each verified at
source:

| prerequisite | arms | suite | the refusal, and where it is decided |
|---|---:|---|---|
| **A clone-parent directory holding ≤32 repositories** (or an explicit `repo=`) | **8** — `A2 A3 A4 B1 B2 C1 C2 C3` | `run_nhi_register_write_flag_probe.py` | `tools/nhi_register.py:684`, `SIBLING_CANDIDATE_CAP = 32` at `:602`. The probe builds its sandbox under `%TEMP%`, which held 78 repositories, so the tool's own safety cap fires — **correctly** |
| **A UNIQUE `--post-rewrite` anchor in `.githooks/post-rewrite`** | **3** — `B1 B1b B4` | `run_rewrite_convergence_probe.py` | `tools/rewrite_convergence_map.py`; the anchor occurs **3 times** (`grep -c` = 3), so the uniqueness guard refuses. **A repo-state prerequisite, not a sandbox one** |
| **A pin file carrying an integer `uncovered` where the tool looks** | **4** | `run_role_gate_negative_coverage_probe.py` | `tools/role_gate_negative_coverage.py:761` and `:774` — *"COULD NOT TELL — the pin carries no integer `uncovered`"*. Its real-repo section passed entirely, so the classifier works and the fixture's pin is the gap |
| **A `SECRETS` entry for every env var read under `api/`** | **5** — `4c 5a 6a 6b 6c` | `run_secrets_inventory_probe.py` | `tools/secrets_inventory.py:259-262`, *"A new secret breaks this tool on purpose."* `SAIRNVET_TRANSCRIBE_URL` (`api/sairnvet-transcribe.js`) and `SAIRN_RESEND_TIMEOUT_MS` (`api/cron-watchdog.js`) are read and have no entry |

**THE SUITE THAT LOOKS MOST LIKE A CREDENTIALS PROBLEM IS NOT ONE.**
`run_secrets_inventory_probe.py` needs **two names classified**, not two secrets
supplied. **A taxonomy of endpoint / database / credentials would have put all
five in the wrong box** — which is the finding, not a quibble with the question.

---

## 9. I GOT TWO VERDICTS WRONG, AND THE CORRECTION IS THE MOST USEFUL THING HERE

**The isolated worktree is the right default and it is not free.** Three of the
24 could not reach a verdict there, and **reporting their exit codes as red
would have declared working code broken.** Re-driven in the live clone — only
after everything was committed and pushed, so a half-finished plant was
recoverable with `git`, with `git status --short` **empty before and after each
run** and the `.git` sentinel verified gone afterwards:

| suite | worktree | **live clone** |
|---|---|---|
| `tests/seam_check/run_delegation_probe.py` | crashed, exit 1 | **EXIT 0, all four arms True → `recovered`** |
| `tests/seam_check/run_delegation_residue_control.py` | crashed, exit 1 | **EXIT 0, 10 passed 0 failed → `recovered`** |
| `tests/run_tool_selftest_probe.py` | exit 1, 1 FAILING + 2 could-not-run | **exit 1, 0 FAILING + 1 could-not-run** |

**THE CAUSE IS STRUCTURAL AND WORTH KEEPING: their sentinel is
`os.path.join(REPO, '.git', 'seam-delegation-probe.planting')`, and IN A
WORKTREE `.git` IS A 64-BYTE FILE, NOT A DIRECTORY.** They cannot run in any
worktree, in either direction, and they move as a pair because the control
imports the probe's own `plant`.

**AND THE LIVE RUN MADE ONE DEFECT UNAMBIGUOUS WITH ZERO SANDBOX NOISE:**
`tests/run_tool_selftest_probe.py:330` is
`return 1 if (fails or cnr or shrunk or unparsed) else 0` — **so a
could-not-run alone produces exit 1.** The suite separates the third state
carefully in its output, citing PR §1.11 in its own header, and then collapses
it into failure in the exit code, which is the only thing a runner reads.
**That is the b6 unproven-arm finding running the other way, in a file that
quotes the rule it breaks.** `tests/`, so mine.

---

## 10. Open, with the exact next step

1. **The `office_manager` role** → **hank**. All four places, **in one change**:
   `ROLES_BY_APP` (`api/_lib/auth.js`), a capability decision in
   `api/alf-auth.js` (§5's B2 — either resolution), and the role `CHECK` in
   **both** `sql/` files. Miss a CHECK and credential creation fails at the
   database while the app believes the role exists. Then re-run the suite;
   **exit 3 would mean arms are unproven and is not a pass.** On exit 0, remove
   the row from `docs/known-red-suites.json`.
2. **The `clock_flags` fix** → **hank**. `api/sd-data.js:7062` at this HEAD —
   **re-derive it, do not trust that number.** Merge on `field`, or key per
   field as the stamps already are.
3. **The `billing`/MAR grant feature** (b8's item 1) → **hank**, still open at
   HEAD. `ALF_FAMILY_READ_ROLES` at `api/sd-data.js:12551` still reaches
   `family_mar`. The three audit `event_type` values must land in the same
   change as the code that emits them.
4. **The three WEAKENING flag rows** → **any session except cody.** All flagged
   details are prose and all are now backed by arms E1/E2; the rows are
   unsigned because I wrote the commits.
5. **`tests/sairnfreedom_server_backup.js`'s 35→36 count** → **tests owner
   (me), next batch.** **One change clears three register rows** (#21, #23, #24).
   Decide first whether the 36th resource is deliberate; if it is, change the
   number in the same commit as whatever added it.
6. **`tests/run_tool_selftest_probe.py:330`** → **tests owner (me).** Exit 3
   when the only outstanding state is could-not-run, and print the count beside
   the pass and fail counts.
7. **`tests/sairncare/test-op-audit.js`'s stub** → **tests owner (me).** Its
   `verifySessionToken` stub throws unless a third argument is `'sairncare'`, and
   `api/sd-data.js:1936-1938` deliberately calls the pre-gate with two. **The
   stub is the stale half; `api/` is correct.** 14 arms clear with one fix.
8. **`tests/sairnlegacy_reservation_lock.js`'s fixture** → **tests owner (me).**
   The `credentialStillActive` pre-gate consumes the fixture's first `replies`
   entry, so every downstream reply is shifted by one. Add the `active` lookup
   reply. Clears #25 too.
9. **13 suites are still undriven** (`diagnosed` blank) → **cody**, next batch.
   Re-derive the list from `docs/known-red-suites.json`; do not quote the 13.
   **Drive the two `.git`-sentinel-style suites in the live clone from the
   start** — §9 is the reason.
10. **Four `tools/` items routed to cc:** the sweep's `SELFTEST_RX` matching
    `'--selftest'` as text in 3 of 44 (and `TOLERATE_MISSING` spelled for the
    wrong argparse wording); `ooda_phases.py`'s `<10` expectation against 249
    records; `subprocess_decode_check.py`'s 69 unencoded subprocess calls plus
    the 6 from #13; and `license_keys` missing from the SQL preflight column
    catalogue.
11. **The `--post-rewrite` anchor occurs three times** in
    `.githooks/post-rewrite`, which is why three arms of
    `run_rewrite_convergence_probe.py` cannot run → whoever owns that hook.
12. **Two unclassified secrets** — `SAIRNVET_TRANSCRIBE_URL` and
    `SAIRN_RESEND_TIMEOUT_MS` → **cc**, `tools/secrets_inventory.py`'s `SECRETS`.
    Five arms clear with two entries.
13. **The 19 could-not-tell seams** → **cc**. #32 and #33 cannot pass until the
    seam gate can exit 0, and the 19 are a real repo condition corroborated by
    three independent suites.

---

## 11. Cleanup

**Removed:** my own scratch files under
`C:\Users\marsh\AppData\Local\Temp\claude\…\scratchpad\` — the b9 logs
(`b9claim`, `om`, `om2`, `cf`, `cf2`, `mar9`, `owners`, `mp`, `tm`,
`push1`–`push4`, `live14`, `live30`, `live31`) and the three one-shot register
scripts (`reg_b9.py`, `reg_b9_sweep.py`, `reg_b9_live.py`) and `msg1.txt`. The
sweep worktree was removed and pruned by the runner and
`git worktree list` shows **only the live clone**. **No other agent's files, no
live rows, nothing in the repo.**

**EVIDENCE IS IN THE REGISTER, NOT IN SCRATCH.** All 24 suites' results, the
seven filled `why` fields and the three `recovered` rows are in
`docs/known-red-suites.json`, each naming its exit code, its arm names and the
`file:line` that produced the exit. A digest pointing at a temp directory is a
citation that expires.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\6f734872-ad7d-48a6-9ee8-4fe9b8c31a22.jsonl`

---

*Written before the report, at a point where everything above is committed and
pushed except this file and the report and digest that follow it.*
