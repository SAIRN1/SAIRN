# SAIRN handoff — cc batch b14 — 2026-10-15

**Written by:** cc, in `Documents\SAIRN-cc`, on `main`.
**Written BEFORE the report**, at a point where nothing is half-finished:
every change is committed and on `origin/main`, the tree is clean, zero
stashes, the claim is released, and every selftest and ablation named below
was re-run after the final rebase.
**Companions:** `SAIRN-report-cc-b14.txt`, `SAIRN-digest-cc-b14.txt`,
`SAIRN-latest-cc.md`, `docs/2026-10-14-cc-b14-routed.md`,
`docs/2026-10-14-cc-b14-sweep.md`, `docs/ABLATION-RECORDS.md`.
**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\5521d10f-06f8-4089-8534-150e3e3c8d84.jsonl`
— shared with b12 and b13, so the CONTEXT figure covers all three batches.
Scratch: `…\5521d10f-06f8-4089-8534-150e3e3c8d84\scratchpad\`
(`exit3_survey.py`, `defects_b14.py`, the commit-message files).

**b14 was WRAPPED AT A CONTEXT LIMIT, not completed.** Items 1, 2, 3 and 5
landed in full. Item 4 ran and is reported with one half lost and two findings
parked. Nothing is mid-edit.

---

## Committed / pushed state

**HEAD `11697bad`, `git rev-list --left-right --count origin/main...HEAD` =
`0 0`, tree clean, zero stashes.** No `--force` in any spelling. **No override
of any form** — `docs/BYPASS-LOG.jsonl` holds 97 rows and **none is dated
2026-10-15**; the gate records an override *attempt* before deciding whether
to honour it, so an unused override is an absent row rather than a silence.
No hook added or restored; `.claude/settings.json` never committed.

| SHA | what |
|---|---|
| `3474df69` | fix(board) — chain_tip gets an independent source and mirror-freshness detection (item 1) |
| `c491f1bf` | fix(router) — the raw-`status` sweep, and the one real defect it found (item 2) |
| `efd2626e` | docs(PR 5.1), fix(gate) — exit 3 stays ONE code, decided with the numbers (item 3) |
| `2ab32b34` | test(ablation) — the b12–b13 ablation records, and two findings (item 5) |
| `eb917751` | docs(b14) — the sweep, the lost log, and the lock defect (item 4) |
| `0a0091d3`, `a490fc4b`, `20dd22a4`, `11697bad` | chore — two defect records, then the register's own `--reseat` after each rebase |
| `042454ee`, `1ad9d83f`, `761a69c4`, `f8563325` | chore — scrutiny-ledger rows the gate wrote while examining each push |

**SEVEN push attempts and the remote moved under five of them.** Four refusals
were gate checks satisfied rather than overridden (register-feed twice,
no-ref-lines, and one that could-not-tell what was being pushed); three were
`cannot lock ref` races with other sessions. All resolved by rebase.

**One rebase conflict was REFUSED by `tools/sairn_rebase_resolve.py`, and it
was right to refuse.** A register re-seat deletes old-sha records and adds
new-sha ones, which against an append-only ledger reads as two deleted
ancestor records:

> *REFUSED: 1 mergeable ledger(s) hold a difference that is not an append. A
> union would put every one of them back, which is a different wrong answer,
> not a safer one. These files CAN be merged automatically, and that is exactly
> why this case has to be refused out loud.*

The hand-written re-seat commit was **skipped** and the register's own
`--reseat` was run after the rebase settled. **Its output is a partial repair
and says so**: 2 re-seated, 4 SUPERSEDED skipped and excluded from that count,
1 LEFT ALONE on a destination collision.

**No live deployed-URL check, and that is not a skipped step:** this batch
changed no `api/`, `sql/` or app file — `tools/` and `docs/` only.

---

## What b14 PROVED

| claim | evidence |
|---|---|
| the board's chain-tip cell no longer reports a frozen mirror as current | live: `seq 893 (h2's own digest b36 — THE REPORTED TIP; …); beacon claims seq 778 … published 2026-10-08; MIRROR IS FROZEN: newest file 154h old, past the 48h line; THE MIRROR IS 115 ENTRIES BEHIND the digest` |
| the new detection is load-bearing | `--selftest` 22/22, `--ablation` **14 layers, every one load-bearing**. The three new layers break 2, 5 and 1 arms |
| the router no longer attributes ownership to a dead session | 27 ACTIVE-attributed paths → 25; `cloud` (gone 18 days) went from owning 2 to owning 0 |
| that arm is about the fix | driven against the pre-fix selector: **15/16, the raw-status arm FAILS**. Now permanent inside the criteria lock, 18/18 |
| exit 3 should stay one code | **51 producers** measured by `git ls-files tests api tools` + grep; **50 of 51 already print a recognised reason marker** |
| the anchor-rot tool's layers are load-bearing | `--ablation` added in b14 (it landed in b13 with 12 arms and none): **6 layers, all load-bearing** |
| the sf_events rot finding is CLOSED | fourth b22 re-anchored it: **8 anchors, 8 resolving exactly once, 0 not** |

## What b14 left UNPROVEN

| thing | why it is unproven, not just undone |
|---|---|
| **the full suite sweep's per-file results** | the run COMPLETED (lock released, pid gone) and **cc destroyed its stdout** by overwriting `/tmp/b14_sweep.log` while the process held an fd on it. The list does not exist. Not re-run: a second 17-minute sweep inside the wrap-up would have replaced the handoff |
| **the 3 test-file-floor layers from b12** | measured UNPROVEN against cody's probe — removing each leaves it green. Not cody's probe being wrong; it predates b12 and was never asked about the ratchet. **cc cannot add arms in `tests/`** |
| **the 20s-vs-540s report-only budget** | the sweep rewrote `docs/report-only-reachability.json` to `registry_size 78, reached 7, never_reached 71`. The figure in `report_only_checks.py`'s own comment — *"36 of 73 … 540s"* — is stale in both terms, and b12/b13 both justified a `_FRONT` placement with that arithmetic. The conclusion still holds; the stated reason does not |
| **`run_all_tests.py`'s lock** | `acquire_lock()` will delete a **live** run's lock after 15 minutes — measured: pid 25196 ALIVE at 16.1 min, `LOCK_MAX_AGE` 15.0 min. Found at the wrap-up point; a lock change needs a failing-first arm and an ablation, not a quick edit |
| **the 4 four `tests/` raw-`status` reads** | they may be CORRECT as written — a probe checking the record it just wrote *should* read the stored field. Routed with the judgement attached rather than asserted wrong |

---

## Claims held

**None. `cc` was claimed as the first action of b14 and is released** —
`python tools/sairn_claim.py release cc`, status row set to `idle`.

**Files written that were NOT in cc's declared b14 FILES**, said out loud:
`docs/ABLATION-RECORDS.md` and `docs/ablation/floor_layers.py` (new, item 5),
`docs/2026-10-14-cc-b14-sweep.md` (new, item 4),
`docs/SAIRN-PROCESS-RULES.md` (PR §5.1, item 3),
`docs/test-file-floor.json` (corrected by hand after the ablation poisoned it
— reason recorded inside the file),
`docs/report-only-reachability.json` (rewritten by the sweep itself),
`docs/defect-density-register.json` and `docs/scrutiny-flags.json` (each
demanded by a gate before it would accept a push).

**Conflicts declared and NOT overridden (PR §4.3):** `tests/` is cody's — when
item 5's ablation needed arms there, the arms were **routed**, not added, and
`docs/ablation/floor_layers.py` drives cody's probe from outside rather than
editing it. `api/` and `sql/` and app HTML are hank's and untouched. No auditor
clone entered or written: item 1's subject is H2's published mirror on the
Drive and the board was changed to stop depending on it rather than to refresh
it; item 2's fifth raw-`status` instance is inside
`.claude/skills/sairn-hover-auditor/` and is routed to H2.

---

## Open items — each with why it is open and the exact next step

| # | item | owner | why open | exact next step |
|---|---|---|---|---|
| 1 | **the suite sweep's per-file results** | **cc, next batch** | cc destroyed the log; re-running costs ~17 min, which the wrap-up did not have | `python tools/run_all_tests.py > docs/sweep-<date>.log 2>&1` — to a path **nothing else writes**, never a reused `/tmp` name. Supersedes §1 of the sweep doc |
| 2 | **`acquire_lock()` steals a live run's lock** | **cc, next batch** | found while waiting for the sweep, at the wrap-up point; needs a failing-first arm and an ablation | the fix is already decided in `docs/2026-10-14-cc-b14-sweep.md` §3: reclaim only when the recorded **pid is GONE**, fall back to age only when liveness is unknown, import `session_lock_check.owner_state()` rather than copying the recycled-pid defence, and **raise nothing**. Three arms named there: live pid + old mtime must NOT be reclaimed, dead pid must be, unparseable lock falls back to age |
| 3 | **arms for b12's 3 floor layers** | **cody** | `tests/` is cody's; cc measured them UNPROVEN but cannot arm them | `docs/ABLATION-RECORDS.md` Finding 2 names the fixture each needs. Then re-run `python docs/ablation/floor_layers.py` and watch three UNPROVEN lines become failures. **`tracked-intersection` is the urgent one** — unarmed in-run and *destructive across runs*: removing it made the ratchet count the probe's own untracked fixtures and write a floor of 812, then 813, against a real 808 |
| 4 | **the raw-`status` read in the auditor's own tool** | **H2** | `.claude/skills/sairn-hover-auditor/` is H2's scope and `hover_auditor_scope_gate.py` keeps cc out | `claim_collision_scan.py:339`. Import `is_active` from `tools/sairn_claim.py`, use it, and **fail closed** if the import fails — a fallback to the raw field is the defect wearing a fallback. Fifth instance of this class |
| 5 | **4 raw-`status` reads in `tests/claims/run_push_verify_probe.py`** | **cody** | they may be correct — a probe checking what it just wrote should read the stored field | `:523 :613 :649 :664`. For each, decide whether the arm is about **what was stored** (keep it and comment it, so the next sweep does not "fix" it) or **whether a session holds it** (use `is_active`) |
| 6 | **the 20s-vs-540s budget figure** | **cc, next batch** | correcting the comment needs establishing where the 20s comes from — this machine, or the missing hook entry in this clone | re-derive, then correct `report_only_checks.py`'s comment and re-state b12/b13's `_FRONT` arithmetic. Evidence: `docs/report-only-reachability.json`, 7 of 78 reached |
| 7 | **`tests/run_exec_msgs_gate_sabotage_probe.py` prints no exit-3 reason** | **cody** | the one non-compliant producer of 51; PR §5.1 now makes the reason mandatory | add a line starting `SKIPPED`, `UNPROVEN`, `COULD NOT RUN` or `NOT APPLICABLE` saying which meaning applies |
| 8 | **cc's 4 overdue Tier A obligations** | **cc**, and anybody may `--takeover` past 48h | b11's trade: four unbudgeted reviews at a wrap-up buys four rushed verdicts, and an unreviewed obligation is visible where a bad verdict is not | `python tools/obligation_surface.py --mine`. **One went STALE during b14** — cody's `2026-10-12` obligation covers `tools/route_suite_failures.py`, which item 2 changed, so read the file at HEAD not at the recorded sha |
| 9 | **hank's 410h obligation has an unresolvable sha** | **hank** | `3e3e1cca210e` does not resolve in this clone — rebased away without a reseat, or never fetched | the gate reports it as a **COULD-NOT-TELL** itself. Re-seat or re-record before reviewing |
| 10 | **`docs/NHI-REGISTER.md:69` omits step 4a** | **fourth** | carried from b11/b12/b13; `docs/` is fourth's | `python tools/runbook_constant_agreement.py` reports it. **Promote that check to blocking once the register copy lands** |
| 11 | **Tier A review of `citation_anchor_rot_check.py`** | **fourth** (auto-assigned) | recorded in b13; only fourth may discharge it | `python tools/tier_a_review_gate.py --list` — the obligation names the three things to review hardest |
| 12 | **the H2 chain mirror at 154h** | **H2** | a build agent does not write into an auditor's published chain directory | refresh `hover-chain-h2\` or retire it. The board no longer needs it fresh, but while it sits there it is a tamper-evidence artefact a reader takes as current. **Also check:** h1's mirror is currently AHEAD of its own digest (1444 vs 1440) — the board reports that and deliberately does not resolve it. If a digest can understate the tip, the board's "digest wins" default is wrong and cc should hear it |
| 13 | **FMEA drafts for cc's own 9 tools** | any session **except cc** | a detector drafting the FMEA for its own fix is detector-blesses-its-own-fix | list in `docs/2026-10-14-cc-b14-routed.md` §7 |

---

## Three things that will cost the next session time if nobody says them

1. **An ablation can be wrong in two directions, and both happened here.**
   `fail-closed-target` reported UNPROVEN twice before the ablation was right —
   the layer is **one thing implemented twice** (an `isfile` test *and*
   `read_text()` returning `None`), so removing either half left the other
   standing and the layer looked deletable. **A redundantly-guarded layer is a
   trap for a lazy ablation.** And the floor harness *restored the tool but
   left the floor file poisoned*, so the same layer read `load-bearing` in one
   run and `UNPROVEN` in the next. **An ablation that leaves its subject's
   state behind has contaminated every measurement after it** — snapshot and
   restore per layer, not once at the end.

2. **Two "ablations" from b13 were not ablations.** One asserted a property of
   a **string literal** and would have passed with the function deleted. The
   other was a one-off swap in a scratch script — gone when the terminal
   closed, leaving the next reader only the claim. **An ablation record has to
   be re-established on every run, and it has to restore the version it
   replaced, not some older one.** The `OVERRIDE_HINT` case is the proof: the
   b11 text was green on all eight arms that existed while being false in two
   ways.

3. **Running the thing finds what reading it cannot, and the log is part of the
   artefact.** Waiting ~17 minutes for a sweep is what surfaced a lock that
   declares a live run dead at 15 — nobody would have found that by reading
   `acquire_lock()`, because the code looks correct until you know how long a
   real run takes. **And the same batch lost that sweep's output by reusing a
   `/tmp` filename a live process held open.** Log a long run to a path nothing
   else writes, under `docs/` where it is committed, and treat the log as the
   deliverable rather than as console scroll.
