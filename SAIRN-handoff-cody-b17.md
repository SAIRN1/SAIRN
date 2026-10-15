# Handoff — cody, batch b17, 2026-10-15

**Written BEFORE the report.** Every item below is either landed, or open with
the reason it is open and the exact next step. **Nothing is half-edited.**

**THE EXPECTED HEAD WAS WRONG AND THAT IS NOT A PROBLEM.** The prompt said HEAD
should be `763c9560`. It was **`96d35e12`** at session start. `763c9560` is the
**b16 handoff commit** and was **9 commits behind `origin/main`** when this
session opened — `git merge-base --is-ancestor 763c9560 origin/main` → yes. The
other clones had pushed since. Fast-forwarded to `origin/main` before any work.

---

## 1. What landed

| | |
|---|---|
| commits | **`34902339`** `test(b17): eight of the thirty closed at cause…` and **`29129fda`** `test(b17): the ablation record's three UNPROVEN arms were three defects IN THE RECORD…` |
| claim | `tests` (**`cody-1792072154`**, taken **2026-10-15T13:49:14Z**, committed `084f9df8`) — taken **BEFORE any work**, released with the four artefacts |
| committer | `fx <fx@example.invalid>`, this clone's LOCAL config, unchanged |
| overrides | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`, in any form |
| boundaries | **NO `api/`, `sql/` or `tools/` file edited.** No hook restored. `.claude/settings.json` never committed. No auditor clone entered |

**Files in the two commits — 16, all under `tests/` and `docs/`:**

```
tests/sairnbuild_backup_pending.js            FIXED  exit 0, 29/0
tests/sd_data_family_mar_gate.js              FIXED  exit 0, 10/0
tests/run_sv_session_gate_sabotage_probe.py   FIXED  exit 0, 7 arms CAUGHT (+ __main__ guard)
tests/run_leg_session_gate_sabotage_probe.py  FIXED  exit 0
tests/run_sairnbuild_server_wins_sabotage_probe.py FIXED exit 0
tests/sairnbuild_server_wins.js               FIXED  a SILENT assertion, 25/0
tests/run_python_escape_hygiene_probe.py      FIXED  exit 0, 9/9
tests/run_capa_fields_probe.py                FIXED  no longer dirties the tree
tests/run_exec_msgs_gate_sabotage_probe.py    3 named exit-3 preconditions
tests/claims/run_push_verify_probe.py         the 4 raw-status reads, decided
tests/run_criticality_tier_probe.py           consumes tests/lib/rm_ro.py
tests/claims/run_freshness_probe.py           consumes tests/lib/rm_ro.py
tests/lib/rm_ro.py                            NEW -- one definition, self-checking
tests/run_b13_b14_ablation_record.py          4 b17 arms + 3 record defects fixed
docs/2026-10-15-cody-b17-triage.md            NEW -- the triage
docs/2026-10-15-cody-b17-compaction-diagnosis.md NEW -- item 1
```

---

## 2. THE RESULT IS THE SAME METHOD FINDING, HARDER

**b16 proved that reading the subject separates a discovered defect from an
injected one. b17 is the test of that claim at scale, and it held:**

> **NOT ONE of the 30 was a live `api/` defect that b15's last-line triage had
> named correctly.** Eight are closed at cause. The largest single cause is a
> probe anchor that stopped matching — **six files**. The second is an
> **operator decision Michael took on 2026-10-11** that four probes report as a
> defect in the thing they guard.

| what the failure line said | what it was |
|---|---|
| `TypeError at :241`, reading `payload` of undefined | **every push count was 0 from the first arm** — an undeclared identifier turned the whole backup off and `st()`'s bare `catch(e){}` swallowed it |
| `active-credential re-check DID NOT RUN`, ×5 | **all five arms say `ok`.** It is diagnostic stderr. The one real failure was an arm asserting an identifier a **security tightening** had removed |
| `THE SESSION GATE MOVES AFTER THE WITNESS LOCK` | **ANCHOR-0.** The mutation was never applied; the gate block grew from 6 lines to ~68 on 2026-10-14 |
| `the gate WIDENS to sf_officers and sf_tickets` | a **mutation label** — but the arm's failure is real and is a **missing set-equality assertion** in hank's suite |
| `7a the real repo has zero bad anchors` | **one** stale anchor in 530, and fixing it closed **two** of the 30 |

**And one thing that was never red and was never testing anything:**
`tests/sairnbuild_server_wins.js:420` asserted the literal `key==='bld_bids'`
appears in `bldRetryPending`. It does not — the retry passes
`!!BLD_SESSION_REQUIRED[key]` — but the string occurs **twice in
`sairnbuild.html` and both are COMMENTS**, one at `:2534` *inside that very
function*, explaining that the old form "used to read `key==='bld_bids'`".
**The assertion was satisfied by the comment documenting the removal of the
thing it asserted**, and the sabotage arm guarding it was ANCHOR-0. Two layers,
neither guarding.

---

## 3. Item 1 — the compaction diagnosis, and it answers none of the three

`docs/2026-10-15-cody-b17-compaction-diagnosis.md`. Read-only; nothing changed.

**232 transcripts across all six SAIRN clones contain ZERO structural
compaction events, and every clone's sessions reach 957,000–999,683 context
tokens.**

* **Winning source:** `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE = "97"` in
  `C:\Users\marsh\.claude\settings.json`. It is the **only** autocompact knob
  set anywhere — no `autoCompactWindow` at any of the four scopes, **no
  `modelSettings` block at all**, neither managed-settings file on disk, and
  `CLAUDE_CODE_AUTO_COMPACT_WINDOW` / `CLAUDE_CODE_MAX_CONTEXT_TOKENS` /
  `ANTHROPIC_BETAS` / `DISABLE_AUTO_COMPACT` all unset. Confirmed live:
  `printenv` → `97`.
* **Launch command:** all **six** live `claude.exe` processes have **zero
  arguments**. `--autocompact` is passed by none of them. CLI **2.1.222**.
* **Verdict: none of threshold / window / flooding.** The threshold is as high
  as it goes; the window is the full ~1M and the peak ever recorded is
  **999,683**; the largest single tool result across five sessions is 24,190
  chars (~6k tokens) and a whole session's tool results sum to ~122k (12%).
  **No cap was imposed because the diagnosis found no flooding.**
* **Fixed baseline: 59,434 tokens**, measured from this session's first request
  (24,842 cache-read + 34,590 cache-creation), stable within 1,400 across five
  sessions.
* `/context`'s category split is **deliberately omitted** — it is a client-side
  command and cannot be invoked from a tool call, so any split would be my
  arithmetic wearing the command's name.

**UNVERIFIED, and it is the one thing this cannot settle:** three sessions
exceeded the ~970,000 trigger point (998,916 · 999,683 · 987,724) and still
produced no `compact_boundary` entry. Either CLI 2.1.222 does not write a
structural marker, or compaction never fired. **Read the 0 as "no record of
any compaction", not as proof none occurred.**

**A trap worth keeping:** a first pass searched for the *word* `compact` and
reported this fresh 133-line session as having three compactions. Every hit was
**my own search command and its echoed result**, written into the transcript by
the act of searching. A substring search for a marker inside the log that
records the search **finds itself**.

**And the link to item 2 nobody asked for:** `.claude/settings.json`'s
committed `_hooks_note` says the 23 hooks were cleared on **2026-10-11**
*"because they were causing agent compaction."* **That cannot be credited from
these transcripts** — the zero is uniform across the whole period, including
before 2026-10-11, so the record cannot show whether the clearing changed
anything. The residual cost of it is §5's four red probes.

---

## 4. Items done, per item

**ITEM 1** — above. **ITEM 2** — eight of 30 closed at cause, 22 routed;
`docs/2026-10-15-cody-b17-triage.md` has an owner and a next step for every
one. **ITEM 3** — the `run_capa_fields_probe.py` cleanup (done first, as
instructed), the four raw-status reads, the exit-3 reason lines. The register
rows are **NOT done** — §6.1. **ITEM 4** — both halves; `tests/lib/rm_ro.py`
and four ablation arms. **ITEM 5** — the floor is **NOT raised**, and the
comparison in the prompt turns out to be two different metrics — §6.2.
**ITEM 6** — this file, then the three artefacts.

### Verification at the landed sha — exit codes read from `echo "EXIT=$?"` on
### its own line, never from a pipeline

```
EXIT=0  node tests/sairnbuild_backup_pending.js                 29 passed, 0 failed
EXIT=0  python tests/sairnbuild_fault_probe.py                  0 failure(s)
EXIT=0  node tests/sd_data_family_mar_gate.js                   10 passed, 0 failed
EXIT=0  python tests/run_sv_session_gate_sabotage_probe.py       7 arms CAUGHT
EXIT=0  python tests/run_leg_session_gate_sabotage_probe.py
EXIT=0  python tests/run_sairnbuild_server_wins_sabotage_probe.py arm 6 CAUGHT
EXIT=0  node tests/sairnbuild_server_wins.js                     25 passed, 0 failed
EXIT=0  python tests/run_python_escape_hygiene_probe.py           ALL 9 ARMS PASS
EXIT=0  python tests/run_mutation_anchor_probe.py                 0 arm(s) failed
EXIT=0  python tools/mutation_anchor_check.py      530 anchors, 0 not matching once
EXIT=0  python tests/lib/rm_ro.py                                0 failure(s)
EXIT=0  python tests/run_criticality_tier_probe.py                0 failed
EXIT=0  python tests/claims/run_freshness_probe.py               63 passed, 0 failed
EXIT=0  python tools/copy_exactly_check.py
EXIT=0  python tests/run_floor_layers_probe.py      all three floor layers armed
EXIT=1  python tests/run_capa_fields_probe.py      no longer TIMES OUT, tree CLEAN,
                                                   7 real register CONTENT failures
```

**Confirmed landed for hank** (item 5's "confirm landed"): of b15's three
failing `api/` suites, **two are now green** —
`api/sd-data-leg-session-gate.test.js` **EXIT=0** and
`api/sd-data-memory-app-scope.test.js` **EXIT=0**.
`api/sd-data-law-trusttx-session.test.js` is **still EXIT=1**. The leg suite
going green is also why `tests/run_leg_session_gate_sabotage_probe.py` moved
from exit 2 (baseline red) to exit 1 (its own ANCHOR-0) — the chain is
confirmed, not inferred.

---

## 5. Claims held

**NONE after this handoff.** `tests` (`cody-1792072154`) is **released** with
the report, digest and `SAIRN-latest-cody.md`, because b17 is not continuing
and a claim left standing blocks the next session for four hours.

The standing decision was honoured: **the claim was taken before any work.**

---

## 6. Open — every item, why it is open, and the exact next step

### 6.1 → CODY. The 16 CHANGED and 9 RECOVERED register rows. NOT DONE, and the
### reason is a measurement, not a shortage of time

**`docs/known-red-suites.json` was measured 2026-10-12 against 411 files, and
NONE of b17's eight newly-green files has a row in it — checked, 0 of 66
entries match.** `tools/known_red_check.py --from-run <log>` needs a full-tree
log; this batch ran **36 files**, deliberately, because reading each subject is
what the batch was for.

**Writing rows from a 36-file run would record a subset as if it were the
tree**, which is the defect the register exists to prevent. So nothing was
written. **NEXT STEP:** a full-tree `python tools/run_all_tests.py`
(~2h), then `python tools/known_red_check.py --from-run <log>`, then drive each
CHANGED file **alone on a clean tree** and re-word or split its row. Take the
16 CHANGED before the 9 RECOVERED, as instructed — a row registered red that
now fails on a *different arm* absorbs a failure it does not describe.

**AND A BLOCKER TO READ FIRST:** `tests/run_known_red_probe.py` is red with
seven `COULD NOT RUN: the log says 66 FAILING TEST FILE(S) and 64 FAIL lines
were parsed`. **The tool is refusing correctly** — the PROBE's fixture log has
a header count two higher than its own FAIL lines. Fix the fixture, not
`known_red_check.py`.

**→ CC, seen in passing:** `C:\Python314\python.exe tools/run_all_tests.py` has
been running in `Documents\SAIRN-cc` since **08:12:23** (pid 79316) and
`docs/sweep-2026-10-15.log` was **0 bytes after 1h41m** — the tool's stdout is
block-buffered, so a full-tree sweep gives no sign of progress until it exits.
Not mine, not touched. A 0-byte log is indistinguishable from a dead run.

### 6.2 → WHOEVER CAN COMMIT IT. The floor is NOT raised, and "808 vs 970"
### compares two different populations

**Measured.** `docs/test-file-floor.json` says **808**. The floor's own
population — `tools/run_all_tests.py discover()`, which walks `tests/**` plus
**top-level `api/*.test.js` only** — is **819** (266 js + 429 py + 124
api/*.test.js). The **970** in the prompt comes from
`tools/traceability_matrix.py:456`, whose leg is labelled
`'tests/**, api/** (both walked)'` — **all five `api/` subdirectories**. They
are not the same metric and the real gap is **11, not 162**.

**NOT RAISED**, per the instruction: only from a run whose failures are
triaged, and this run covered 36 files. `run_all_tests.py` raises it itself on
a full-tree run anyway. **The ratchet is ARMED and was verified today:**
`python tests/run_floor_layers_probe.py` → **EXIT=0, all three floor layers
armed**. Arm S remains **structural, not behavioural**, and says so in its own
output. **NEXT STEP:** raise it from the same full-tree run as §6.1, and expect
819+ rather than 970.

### 6.3 → CODY. The hooks cluster, 3 files, and the fix is NOT to restore
### anything

`tests/hook_command_anchoring_probe.py`,
`tests/run_conflict_preflight_hook_probe.py`,
`tests/run_tooling_inventory_probe.py`. All three assert that hooks are
registered in `.claude/settings.json`. **Both settings files carry
`hooks: {}`** and the committed `_hooks_note` says Michael cleared the 23 hooks
on 2026-10-11 on purpose.

The failures are correct as observations and **wrong as verdicts: these are
COULD NOT RUN, not FAIL.** **NEXT STEP:** give each an explicit precondition
that exits **3** naming `hooks: {}` as the reason, quoting the `_hooks_note`.
**Do not restore a hook. Do not commit `settings.json`.** In the same change,
`hook_command_anchoring_probe.py`'s passing arm *"no hook command resolves a
repo script relative to the cwd (0 bare)"* is a **vacuous pass over a
population of zero** and must become exit 3 too.

### 6.4 → CC. `tools/tooling_inventory.py --hooked` fails OPEN on an empty
### hook set, and this is independent of the hooks decision

`tests/run_closing_error_probe.py` asserts it **refuses with exit 2** when
there are no hook entries, **and it got 0**. A tool that reports success on an
empty population is a fail-open whatever Michael decides about hooks.
**NEXT STEP:** make `--hooked` exit 2 and say which source was empty; the
probe's other two failing arms (`writes NO document rather than a thinner one`,
`says which source was empty`) are the same defect's other halves.

### 6.5 → CC FIRST, THEN CODY. The two claims probes, and the order matters

`tests/claims/run_own_claim_overlap_probe.py` (3 arms) and
`tests/claims/run_claim_audit_probe.py` (2 arms) assert `rc == 3` on a
**retyped task string**. `tools/sairn_claim.py` was deliberately changed:
`9b0bfd51 fix(claim matcher): the declared FILES set is the PRIMARY mode`.
Confirmed live this session — claiming `tests` against fourth's active claim
answered **`CLEAR ON WORDS -- AND THE FILE OVERLAP COULD NOT BE PROVEN EITHER
WAY`**.

Two readings, and the probes cannot separate them: the policy change is right
and the probes are superseded, **or** the change re-opened the two incidents
they exist to hold shut. **NEXT STEP (CC):** run the two real incidents' actual
task strings **and their FILES lists** through the current matcher. If they
still refuse, the probes are superseded. If not, `9b0bfd51` needs narrowing and
the probes are what noticed. **THEN (CODY):** re-derive both fixtures against
whichever policy stands.

### 6.6 → HANK. Three things, all verified before routing

1. **`api/sd-data-sf-session-gate.test.js` has no set-equality assertion.**
   `tests/run_sf_session_gate_sabotage_probe.py` arm 6 reports **`SILENT — the
   suite passed with this defect planted`**: adding `sf_officers` and
   `sf_tickets` to `SD_SESSION_GATED` passes every assertion, because the suite
   checks that each approved resource **is** gated and never that an unapproved
   one is **not**. **NEXT STEP:** one arm asserting set equality between the
   gated set and the approved set; then `python tests/run_sf_session_gate_sabotage_probe.py`
   arm 6 must flip to `ok`.
2. **`api/sd-data-law-trusttx-session.test.js`, still EXIT=1, 9/10.**
   `active-credential re-check DID NOT RUN for app "sairndental"
   (NO_ACTIVE_CHECK) on law_trusttx/read`. **The app is `sairndental`, not
   `sairncare`** — b15's "one fix, two files" is **refuted on the `tests/`
   half** (§2) and this half is its own defect. `tests/law_trusttx_session_probe.py`
   (exit 2, baseline red) recovers by itself the moment this is fixed.
3. **`tests/sd_data_write_attribution_three_apps.js`: `rf_schedule` fails three
   ways** — does not stamp the session employee in its blob, does not discard a
   caller-supplied actor (**14 of 15 cases do**), and `set_status` does not
   merge onto the stored blob. One resource, three symptoms, and C1's "14 of
   15" is what a real single-branch defect looks like. **Verify against the
   handler before accepting it**, since §2 is a list of cases where this shape
   was the probe.
4. **Already routed and NOT re-raised:** the `memApp` read at
   `api/sd-data.js:1930` (b16) and `tests/run_exec_msgs_gate_sabotage_probe.py`
   — **nothing new on either**, as instructed.

### 6.7 → WHOEVER OWNS `sairnbuild.html`. A READ, and it is the sharpest
### finding in the batch

`st()` at `sairnbuild.html:2109` wraps the whole server-backup call in
**`try{bldSyncCollection(k,v,prev);}catch(e){}`** — a bare swallow. b17 proved
what that costs by accident: **one undefined identifier turned the entire
feature off and the only symptom was "nothing to back up."** The identifier is
declared in the live app, so there is no bug today. But any future throw inside
`bldSyncCollection` produces the same silence, **in the feature that exists
because silently-failing backups cost real records**. **NEXT STEP:** decide
whether that `catch` should re-raise, `console.error`, or mark the collection
pending.

### 6.8 → WHOEVER WROTE THE ROWS. Six named register records

`tests/run_capa_fields_probe.py` now completes and reports **7 real failures**,
six of them named: `31406a87e010`, `44abebb30bf5`, `4f69facd93b3`,
`9841e14a5eaa`, `d6e58c61766a`, `e3858f19aad8` — each *"`recurrence_open`
states a residual rather than dismissing one"*. **This is register CONTENT, not
the probe.** **NEXT STEP:** `git log -S<hash> -- docs/defect-density-register.json`
names each row's author; the field must say what is still latent.

### 6.9 → CODY. 18 of the 30, routed but NOT read to cause

`docs/2026-10-15-cody-b17-triage.md` §11 has the measured failure line, owner
and next step for each. **They are hypotheses with evidence attached, not
verdicts** — the nine files b16 and b17 have now read to cause produced **six**
cases where the failure line meant something other than it said.
**NEXT STEP, in this order:** `tests/server_wins_hydration.js` first (1 of 179,
and it is also the blocked baseline of
`tests/run_server_wins_hydration_sabotage_probe.py`, so one fix closes two);
then the three files whose failing arm is a **CONTROL or a precondition**
(`run_fail_open_probe.py`, `run_register_feed_gate_probe.py`,
`run_audit_event_type_probe.py` H0) because nothing below a failed control has
measured anything; then `run_tier_a_open_basis_probe.py` (**9/30**, the largest
gap, and the arm count GREW while the pass count FELL since b15's 10/27).

### 6.10 → CODY. `tests/run_capa_fields_probe.py` is still slow, and the cause
### is measured

It was **never hung**: it finishes between 200s and 420s. The cost is
structural — `with_register()` deep-copies and **re-writes the whole 2.46MB
register, then runs `cmd_check()` over all of it, once per arm**, ~15 times.
**NEXT STEP:** build the mutant from a small fixture register carrying only the
records the arms touch, with **one** arm pinned against the real register so
the fixture cannot drift into testing nothing.

### 6.11 → CODY. The b16 ablation arms, and one that cannot be expressed

Four b17 arms were added to `tests/run_b13_b14_ablation_record.py`. **b16's four
are NOT there**, and that is a decision: their fix hunks are long re-aims, and
one of them — the `registry_claim` `blocked_lines` revert — only goes red when
**another session's live claim prose** happens to contain the word `BLOCKED`,
which is not a deterministic arm and must not be written as one.
**NEXT STEP:** `git show 7af3737e -U0 -- <file>` for the hunks; add the three
that are deterministic. **And b17's `sairnbuild_server_wins.js` fix cannot be
expressed in that harness at all** — its state change lands in a *different*
file from the one mutated (reverting the suite's assertion flips arm 6 of the
sabotage probe from CAUGHT to SILENT), and the harness applies its fix to the
suite it then runs. Observed both ways in-session; recorded in the report.

### 6.12 → FOURTH. The Tier A obligation, unchanged from b16

`quotes`, `sd_hr_certs`, `sd_hr_employees`, `sdn_projects`.
**NEXT STEP:** `python tools/tier_a_review_gate.py` to read it. cody cannot
close its own; `--takeover` after 48h.

---

## 7. The gate, and the scratch files

**The push gate's own output is in the report.** Nothing overridden.

**Scratch:** this session's own files are in
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\bdbf0e62-dbf8-4c25-945f-9606bba2bf34\scratchpad\`
— logs, plus **`wt17/`, a `git worktree`** used to run the 36 files in
isolation. `git worktree remove` it, or `git worktree prune` after deleting.

**The 109 files / 247 MB that `rm` has refused four times across b14–b16 are
still at the b16 path** and are listed in `SAIRN-handoff-cody-b16.md` §6.
`cfapi/` (a 455-file copy of `api/`) and `clone46/` (a full local clone) are
nearly all of the 247 MB and are the two worth deleting by hand. **Nothing in
the repo or on the Drive depends on any of them.**

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\bdbf0e62-dbf8-4c25-945f-9606bba2bf34.jsonl`

---

*Written before the report, at a point where everything above is committed
except this file and the three artefacts that follow it.*
