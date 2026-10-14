# Handoff — cody, batch b8, 2026-10-14

**ALL SIX ITEMS DONE. ON `origin/main` at `18bf06eb`, 0 ahead / 0 behind, tree
clean.** Nothing below is half-finished. Every open thing is open because it
belongs to somebody else, because a decision is not mine, or because a tool
refused and the refusal is recorded.

**Nothing was overridden. `SAIRN_SEED_GATE` was NEVER used, no hook was restored
or re-added, `.claude/settings.json` was never committed, NO `api/` FILE WAS
EDITED, and no auditor clone was entered.**

---

## 1. Committed and pushed

| | |
|---|---|
| HEAD / `origin/main` | **`18bf06eb`** — identical, `0 ahead / 0 behind`, `git status` clean |
| my b8 commits, each tested as an ancestor of `origin/main` | `a47cdf2d` items 1–5 · `2c9399c5` the two regenerated derived docs + the gate's own scrutiny row · `8a4bdfc8` the Tier A obligation this push owed · `18bf06eb` the merge — **4 of 4 ANCESTOR** by `git merge-base --is-ancestor` |
| push | **LANDED on the fourth attempt, without `--force`.** Three refusals, each repaired at its cause — §7 |
| claim | `tests` — **released after this handoff, the report and the digest** |
| status registry | `working` row written at session start |

**A prior b8 session committed a claim (`e9d6d40c`) and nothing else.** It left
`tests/mar_billing_grant.test.js` uncommitted and untracked. **That draft was
good and it is the file that shipped** — I verified it, ran it, made one edit
(§3) and committed it. Nothing was rebuilt from scratch.

---

## 2. Per item

| # | item | state |
|---|---|---|
| 1 | billing/MAR role-vocabulary note + failing-first tests | **DONE** — §3 |
| 2 | reconcile the two b7 runs; commit or discard the `2026-10-13c` edit | **DONE. THERE WAS NOTHING TO COMMIT OR DISCARD** — §4 |
| 3 | drive the first 12 of fourth b10's 36 undriven suites | **DONE — 11 exit 1, 1 TIMEOUT, ZERO exit 0** — §5 |
| 4 | build `unproven_arm_check` with a failing-first test | **IT ALREADY EXISTED from b7, so it was VERIFIED not rebuilt** — §6 |
| 5 | review the three hank-authored `api/` Tier A records | **TWO REVIEWED WITH FINDINGS, ONE UNSIGNABLE** — §8 |
| 6 | push without force and confirm it landed | **LANDED** — §1, §7 |

---

## 3. Item 1 — the decision encoded, and the suite is red on purpose

`docs/2026-10-13-cody-b8-billing-mar-role-vocabulary.md`, **routed to the `api/`
owner (hank)**, plus `tests/mar_billing_grant.test.js` — **FAILING-FIRST,
deliberately red, registered, wired into NO gate.**

**MEASURED, `node tests/mar_billing_grant.test.js`: exit 1, 5 passed, 16 failed,
4 unproven.** The 4 unproven are COUNTED, not printed — `process.exit` reads the
counter, so it can never exit 0 with one outstanding.

**THE OPEN HOLE, still open at HEAD:** `ALF_FAMILY_READ_ROLES = { owner, billing,
nursing }` (`api/sd-data.js:12551`) is inherited by action `family_mar`
(`:12654`), and because `billing` is in the BROAD half the assignment scope is
skipped entirely (`:12656`) — **so a billing clerk 403'd from `alf_mar` receives
EVERY resident's MAR on the licence through the sibling resource**, not one.

**MY ONE EDIT TO THE DRAFT:** arm C4's label now says its own pass is **vacuous
while A1 is red** — at HEAD billing gets 200 with or without a grant row, so C4
is only load-bearing once A1 refuses. Disclosed in the arm, not only in the
document.

**REGISTERED:** `docs/known-red-suites.json` grew from 84 to 85 entries, with the
measurement, the owner basis, and **"when it goes green, REMOVE this row"** — an
entry whose suite has gone green swallows the next real failure of that file.

**DECISION STILL NEEDED, AND IT IS ARM B2:** there is **no `office_manager` role
in SAIRNcare** (`api/_lib/auth.js:238`), so the grantor the decision names cannot
hold a session. Either add it across `ROLES_BY_APP`, `api/alf-auth.js:52` and the
`role` CHECK in **both** schema files together, or declare `owner` to BE the
office manager. **Both are legitimate; the note states both and picks neither.**

---

## 4. Item 2 — the two b7 runs, and the thing that is bigger than a filename clash

`docs/2026-10-13-cody-b8-b7-reconciliation.md`.

**AUTHORITATIVE: the ROOT trio.** `SAIRN-handoff-cody-b7.md` (11,417),
`SAIRN-report-cody-b7.txt` (29,901), `SAIRN-digest-cody-b7.txt` (1,002) — and
the Drive folder holds **one of each at exactly those byte counts**, so
**Michael's copy is already the authoritative one and nothing needed
re-uploading.**

**The report's SHA256 line RECOMPUTES to the stated value**
(`4d32d6c5…2e8ebe46`), by the report's own stated rule.

**THE TWO RUNS HAD DIFFERENT BRIEFS.** Items 1, 2, 3 and 5 were identical;
**item 4 was a different task in each** (run A: `verify_citator_feedback.py`,
stopped on two missing env vars. run B: `git worktree` / `.git/config`
isolation). So *"b7 item 4"* is ambiguous and a reader must say which run. The
authoritative digest already handles this in its own words.

**`docs/SAIRN-handoff-cody-b7.md` is RETAINED, NOT authoritative.** It is run A's,
and it is the **only** record of run A's item 4. Retained ≠ authoritative, and
deleting it would lose a tool that never ran.

**The root report is a HYBRID: 486 lines by run A (`0d5c241a`), 43 edited by run
B (`6de71700`).** It reads as one document because run B edited rather than
replaced. Disclosed rather than smoothed.

**`docs/handoff-cody-2026-10-13c.md`: NOTHING TO COMMIT OR DISCARD.** It was
committed at **`72ca3ad1`** before either b7 run began — re-measured three ways
(`git status`, `git diff HEAD`, `git log -1`), and `72ca3ad1` is an ancestor of
`origin/main`. **Run A had already reached this answer; mine is an independent
re-measurement that agrees.** The task carried into b8 only because it was
answered in the handoff that is NOT the authoritative one — **that is the
collision's one concrete cost.**

---

## 5. Item 3 — 12 suites driven, and not one has gone green

`docs/2026-10-13-cody-b8-undriven-suite-results.md`. **Isolated worktree, one at
a time, exit code from `echo "EXIT=$?"` on its own line, a log per suite.**

| real exit | suites |
|---|---|
| **1** | **11** |
| **TIMEOUT at 180s, zero output** | **1** (`tests/run_selftest_sweep_probe.py`) |
| **0** | **ZERO — so no register entry is removed** |

**Every one of the twelve carries its `file:line` for the line that produces its
exit code, and I re-read all twelve of those lines in the live clone rather than
trusting the runner's report.**

**THREE blank `why` fields filled** — suites 7, 8 and 10 — per fourth's own
exit-1 rule. **ONE stored `tail` CONTRADICTS the measurement:**
`run_report_only_checks_probe.py` is registered as *"TIMED OUT after 300s"* and
**it did not time out** — exit 1 in ~130s with four named arms. **Appended to
`why`, NOT overwritten**, because a register edited in place cannot tell a
changed reason from a new one.

**THE PATTERN, which is worth more than any single result: 20 of the 42 failing
arms are the subject tool exiting 2 COULD NOT RUN, scored as a FAILED ARM.** None
of those probes has a third bucket. **That is the b6 unproven defect running
backwards** — b6's case was an unproven arm hidden inside exit 0; this is an
unproven arm reported as a failure. Both collapse a third state.

**Highest-value single finding:** `tests/run_rebase_resolve_probe.py` — its
subject prints `No conflicted files. Nothing to do.` and exits **0** where the
probe created a real rebase conflict. **A tool that answers "nothing to do" on a
real conflict is the silent-failure shape.** NOTE, and it narrows the finding:
`tools/sairn_rebase_resolve.py` **correctly saw all three real conflicts** during
my own push (§7), so the blindness is to the probe's fixture, not general.

---

## 6. Item 4 — verified against its own spec rather than rebuilt

`docs/2026-10-13-cody-b8-unproven-arm-verification.md`.

**`tools/unproven_arm_check.py` AND `tests/run_unproven_arm_probe.py` ALREADY
EXIST — b7 built them and they landed.** Building a second would have been the
orthogonal-change failure. All six clauses of
`docs/2026-10-13-cody-b6-methodology-unproven.md` §4 check out: A1, A2, A3,
report-only (registered with its measured count), the control pair, and the named
false-positive shape as an actual arm.

**Failing-first is satisfied by arms that FIRE: 15 arms, exit 0 — five FIRES
arms and five STAYS-SILENT arms**, plus the ablation (`0 of 2` before, `2 of 2`
after) and arm 5, which is the fail-closed one: an empty `tests/` tree gives
**exit 2 COULD NOT RUN**, not 0.

**Real tree RE-MEASURED: 404 files / 151 with a summary construct / 3 in scope /
0 findings.** b7 measured 399 / 146 / 1. **The new MAR suite is one of the three
in scope and it is clean** — the tool was pointed at the tree without being told
the file existed, found it, scoped it and passed it.

**NAME DIFFERENCE, DECLARED:** my claim string said
`tests/run_unproven_arm_check_probe.py`. The real file is
`tests/run_unproven_arm_probe.py`. **The claim is wrong, not the repo.** No file
was created under the claimed name.

---

## 7. Item 6 — three refusals, all repaired at cause, nothing overridden

**Attempt 1 — `docs/MASTER-PLAN.md` and `docs/traceability-matrix.md` no longer
matched their sources.** Correct: this push adds a test file and a register entry
that both documents count. Regenerated with the two commands the gate itself
printed, both exit 0, both *"every leg closed"*.

**Attempt 2 — the Tier A review gate: *"this push changes code serving a Tier A
resource and no independent-review obligation is recorded for it."*** `alf_mar`
was already covered; **`alf_clients` and `alf_family_contacts` were not**, because
the new suite drives the real handler. **RECORDED, not overridden** —
`python tools/tier_a_review_gate.py --open …`, and the tool **assigned it to hank
itself** rather than leaving it first-come. The obligation names what a reviewer
should attack, including that **C4 passes vacuously** and that **arm B2 is a
question I may not answer.**

**Attempt 3 — three merge conflicts**, resolved by `tools/sairn_rebase_resolve.py`
(not by hand): `docs/MASTER-PLAN.md` and `docs/traceability-matrix.md`
regenerated, `docs/tier-a-reviews.json` **union-merged by identity — 248 ancestor
+ 1 upstream-only + 1 local-only = 250**, validator passed, **no ancestor record
dropped.**

**THE GATE ALSO FLAGGED MY OWN NEW TEST FILE `WEAKENING`, AND I MAY NOT SIGN
THAT OFF.** Both shapes are **false positives**, measured: the *"bound or
threshold ADDED"* detail is an arm **label** at
`tests/mar_billing_grant.test.js:458` inside `ok('C1. …')`, and the *"skip /
exemption / allowlist entry ADDED"* detail is the closing `console.log` at
`:649`. Neither is an assertion. **I wrote `a47cdf2d`, so resolving my own flag
is the self-review the Tier A gate refuses at write time. THE FLAG ROW IS LEFT
STANDING and the resolution is ROUTED TO ANY SESSION EXCEPT cody** — same shape
and same routing as b7's `check4_probe` flag.

---

## 8. Item 5 — the three Tier A records

`docs/2026-10-13-cody-b8-tier-a-review.md`. **`docs/tier-a-reviews.json` carries
no verdict from this document** — record 3 is cc's and record 1 is unsignable
from here.

| record | sha | verdict |
|---|---|---|
| `2026-09-27T03:42:29Z` | `54e4835ac96e` — **NO_OBJECT even after `git fetch origin`** | **CANNOT SIGN.** Reviewed against HEAD instead, declared as the weaker basis |
| `2026-10-06T06:14:34Z` | `8246d8bab707` ANCESTOR | already `reviewed` (cody, b7). Re-attacked; not re-signed |
| `2026-10-12T01:51:33Z` | `b7f6fb54116e` ANCESTOR | **cc's to sign.** Findings routed |

**ONE NEW FINDING, mine, not in any record — `api/sd-data.js:6985-6987`:**

    if (clockCheck.flags && clockCheck.flags.length) {
      visitData.clock_flags = clockCheck.flags;
    }

**That is an ASSIGNMENT, and `checkClockEvent` only reports on the clock fields
present in THIS payload.** A caregiver clocks in late (`LATE_REPLAY` stored),
then clocks out late — the second write **replaces** the array and **the
clock-in's flag is gone with nothing saying it existed.** A `FUTURE` flag — the
forged-time case — is lost the same way. The stamps do not have this defect
because they are **keyed per field**. And the same author got it right one screen
away: the sibling self-correction marker is deliberately sticky
(`api/sd-data.js:6870-6872`). **Routed to hank.**

**What I CONFIRMED CLEAN, each by a method that does not share a source with the
assertion it checks:** the EVV stamp keys cannot collide with a clock field (read
the key construction, not arm H2); a caller cannot forge the server's own
observation (`SEN_VISIT_EVV_FIELDS` at `api/sd-data.js:6770` excludes
`*_received_at` / `*_skew_ms`); the legacy dual-key widening is bounded (a `v2`
ciphertext gets exactly one key, `api/_lib/auth.js:849-851`); and arm C0's
uniqueness guard is **load-bearing** — it `process.exit(1)`s and refuses to run
C1-C3 (`tests/sd_data_family_mar_gate.js:211-219`, re-run: exit 0, 10 passed).

**A RULING THE RECORD ASKED FOR AND GOT: the residual existence oracle on
`family_mar` is ACCEPTED.** What leaks is *"a contact row with this id exists on
this licence"*, the alternative collapses 403 into 404, and the caller who learns
anything is already legitimately assigned residents.

**AND A FINDING ABOUT THE REGISTER RATHER THAN THE CODE: four of the named attack
points are no longer true at HEAD, and in one case HEAD gives the OPPOSITE answer
to the diff** — record 1's self-correction lockout was fixed **two days after the
record was opened**. A record stamps `opened_at_sha` so the diff can be found but
**does not record which basis the reviewer used.** Proposed, not built: a
`reviewed_against` field of `diff` / `HEAD` / `both`. Owner: whoever owns
`tools/tier_a_review_gate.py`.

---

## 9. MY OWN ERROR, DECLARED: a global `taskkill` mid-sweep

I ran `taskkill //F //IM python.exe` to stop
`tools/red_suite_register_check.py`, which runs every registered suite with
`cwd=repo` and **no isolation** (`tools/red_suite_register_check.py:96`) — which
should not run in the live clone. **Stopping it was right; stopping it that way
was not.** `//IM` is process-wide, so it also killed the sweep suite in flight.

**What was done rather than hoped:** the runner was told, **every already-run
suite was re-run from the start, and all ten re-runs came back byte-identical
with the same exit code**, so no number in §5 is kill-contaminated. The tree was
checked clean afterwards, and the two orphaned gate worktrees the killed process
left (`gate12-29652-2`, `sairn-gate-base-433860be9668`) were removed and pruned —
a stale entry makes the next `git worktree add` refuse.

**Kill by PID, not by image name.**

---

## 10. Open, with the exact next step

1. **`billing` reading a MAR — THE CODE.** → **hank** (`api/`). Michael's
   decision is made and encoded; the hole is still open at HEAD. Answer arm B2
   (§3) first, then land A–D plus the grant table **and the three audit
   `event_type` values in `sql/sairncare_audit_log_schema.sql` IN ONE CHANGE** —
   an `event_type` outside the CHECK makes `writeAuditLog` `return false`
   (`api/_lib/audit.js:133`) so the grant succeeds and the audit silently does
   not exist. Then re-run the suite; **exit 3 means arms are still unproven and
   is NOT a pass.** On exit 0, remove the row from
   `docs/known-red-suites.json`.
2. **The `clock_flags` finding** (§8) → **hank**. `api/sd-data.js:6985-6987`.
   Merge by field or key per field, the way the stamps already are.
3. **The Tier A obligation this push opened** (`alf_clients`,
   `alf_family_contacts`, `alf_mar`) → **hank**, assigned by the tool. Anybody
   after 48h with `--takeover`.
4. **Record `2026-09-27T03:42:29Z`** → **hank**, in hank's clone:
   `python tools/tier_a_review_gate.py --reseat-shas`, or fetch the object in.
   **An unreachable record is unreviewable, not passing.** Then fourth reviews
   the diff; §8's three paragraphs are evidence that reviewer can use.
5. **Record `2026-10-12T01:51:33Z`** → **cc**. Two of its three attack points are
   moot at HEAD (§8); the third — *not proven live with a bare-key call* — is
   **STILL UNVERIFIED and I could not close it**: `SUPABASE_URL`,
   `SERVICE_ROLE_KEY` and `SUPABASE_SERVICE_ROLE_KEY` are all absent from this
   session's environment. No live call was attempted.
6. **The `tests/mar_billing_grant.test.js` WEAKENING flag** → **any session
   except cody.** Re-derive: the two flagged details are at `:458` and `:649`
   and neither is an assertion (§7).
7. **`tests/run_selftest_sweep_probe.py`** → **cody, next batch.** Re-drive ALONE
   with a much larger cap and `python -u`. 180s was my cap, not a property of the
   suite, and zero output in three minutes is itself the finding.
8. **24 of fourth's 36 suites remain undriven** → **cody**, numbers 13–36,
   starting at `tests/run_subprocess_decode_probe.py`. Same method. **Read §5 of
   the results document before scoring any of them** — just under half the
   failing arms will be could-not-run rather than defects.
9. **A fourth signal for `unproven_arm_check`** — *a probe that records a
   subject's exit 2 and has no third bucket for it* — would have flagged four of
   the twelve suites. **Observation with a measured denominator (20 of 42 arms);
   NOT a claim that it is worth building.** Owner: `tools/` (cc).
10. **`tools/red_suite_register_check.py` runs every registered suite in the live
    clone with no isolation** (`:96`). Pre-existing, not mine, not touched →
    whoever owns it. It should call `require_isolation()` the way b7's three tools
    now do.

---

## 11. Cleanup

**Removed:** my own scratch logs under
`C:\Users\marsh\AppData\Local\Temp\claude\…\scratchpad\` (`claim.log`, `mar.log`,
`mar2.log`, `unproven_probe.log`, `unproven_tool.log`, `famgate.log`,
`rsrc_before.log`, `mp.log`, `tm.log`, `rr.log`, `rr2.log`, `push2.log`,
`tiera.log`), the two orphaned gate worktrees named in §9, and the sweep
worktree (removed by the runner, `git worktree list` confirmed back to the live
clone alone). **No other agent's files, no live rows, nothing in the repo.**

**EVIDENCE IS IN THE REPO, NOT IN SCRATCH** — the five b8 documents, each naming
the command that produced every figure in it. That is deliberate: a digest
pointing at a temp directory is a citation that expires.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\6f734872-ad7d-48a6-9ee8-4fe9b8c31a22.jsonl`

---

*Written before the report, at a point where everything above is committed and
pushed except this file and the report and digest that follow it.*
