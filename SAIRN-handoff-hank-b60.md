# SAIRN handoff — hank b60 — 2026-10-28

**Subject:**
- S2: demo licences are exempt from SAIRNcode's trial gate, and the server decides.
- L1: a push-time SQL placeholder gate.
- H1 #1274: the readiness caregiver projection.

The batch was resumed after a memory-kill push stop. This handoff was written before the report. Nothing is half-finished.

**Methodology concepts:**
1. *Ship the file that passed:* each item was marked shipped only after its committed blob on origin was re-read
   (item 4 below).
2. *(Michael, this batch)* An exit 1 with no printed reason on this 16GB machine is ambiguous between a gate refusal
   and a low-memory kill. Re-run once, cleanly and in the foreground, before treating it as a gate failure. b60 proved
   it: the reaped run's last line was "push exit 1" with no reason. The clean re-run printed a real, different refusal
   (TOOLING-INVENTORY stale). Memory: `memory-kill-vs-gate-refusal`.

## 1. PUSHED STATE — NOT FORCED, LANDED on origin/main
| commit | what |
|---|---|
| `414d26351` | feat(sairncode): S2 trial exemption |
| `cdf71e894` | fix(sairnsenior): H1 #1274 |
| `995e53c9a` | feat(tools): L1 placeholder gate |
| `bce658193` | bookkeeping: register record, Tier A obligation, path-manifest overrides, OWNER line, regenerated derived docs |

- All of them are authored `mikied68@gmail.com`.
- The tools claim commit landed with them. The release commits follow.
- **The push took four attempts:**
  - a memory kill (no reason printed);
  - TOOLING-INVENTORY stale, so it was regenerated (Michael approved);
  - a rebase conflict on the two shared ledgers: the bookkeeping commit was dropped and re-applied as pure appends;
  - one non-fast-forward race: rebased, re-seated, pushed.
- **No retry loop was used.** Every sha was re-derived after the final rebase. The register cites `cdf71e894bf3` and
  Tier A `cdf71e894`, both checked on origin.

## 2. CLAIMS HELD
None. sairncode, sairnsenior and tools were released after the push: `79640a636`, `47fceba5b`, `b8a717c49`, all on origin.

## 3. THE ITEMS
1. **S2: demo licences skip checkTrialGate. Server-decided, and fail-closed.**
   - `api/sc-auth.js` login and bootstrap return `trial_exempt: true` only for the licence plan exactly `'demo'`.
   - In SAIRNcode today that covers SC-PINNACLE-2026 and SC-AUDIT-2026, with their `sairn-demo-owner`, `owner` and
     `zz-audit-admin` admin accounts. Measured live: there is no `audit-owner` on SAIRNcode; that account is the ALF one.
   - The `trial` and `b2b_starter` plans, a null plan and `'Demo'` all return false.
   - `sairncode.html` `checkTrialGate(trialExempt)` skips only on an explicit `true`. The call sites pass
     `result.trial_exempt === true`.
   - Test `api/b60-sc-trial-exempt.test.js` 18/0: the real handler, the gate function extracted from the shipped html,
     and 2 mutants red.
   - **Stated limit, a DECISION for Michael given real customer deployment:** the trial gate itself is CLIENT-SIDE
     (localStorage). A customer with DevTools can reset it. A real paywall needs a server-side check.
     `license_keys` has no `trial_ends_at` column, and one licence already carries plan `trial`. Not built: out of
     S2's one-function scope.
2. **L1: `tools/sql_placeholder_check.py` plus push-gate CHECK 4d.**
   - It reads each changed `sql/*.sql` blob at the pushed tip.
   - It lexes comments away, then refuses `__DUNDER__`, `{{mustache}}`, `REPLACE_ME`-style markers and operator
     `'<...hash/key/id...>'` literals.
   - Exit 2 (could not run) denies too, and so does a missing tool.
   - Reasoned `operator-input` declarations are reported NOT RUN-READY. `sql/backup_reader_role.sql`, a role password,
     was declared (comment only).
   - Evidence:
     - 20/20 fixtures;
     - probe 5/5 (the b58 blob a93a74cb7 refused, the b59 blob clean);
     - `--all` over 307 files: 0 could-not-run;
     - through the REAL hook: a synthetic placeholder commit was refused by 4d, and a clean control passed (exit 0).
3. **H1 #1274 (from the H1 log, seq 1274; still unfixed at seq 1288).**
   - The `sen_visits/readiness` engine now receives only `{id, name, state_caregiver_id}` per caregiver.
   - For coordinator and scheduler, the state ID VALUE is replaced by a presence marker. The verdict is unchanged, and
     the fetch is unchanged, as `sd-data-sen-caregiver-read-paths` section C requires.
   - Test `api/b60-readiness-caregiver-projection.test.js` 18/0: the engine input is captured per role, and 2 mutants
     go red. read-paths 19/0.
   - Residual, by design: coordinators and schedulers still learn whether a state ID is on file, because an EVV
     readiness report must say so. Suppressing it would be a product decision.
   - Tier A obligation opened, assigned to cc.
4. **Item 4: the literal committed blobs on origin (`bce658193`).**
   - All 9 shipped files are byte-identical to the files that were tested.
   - All three suites were run FROM the extracted origin archive: 18/0, 18/0 and 19/0.
   - `--all` at origin: OK, with backup_reader_role reported NOT RUN-READY.
5. **Item 5: the fx identity fix holds after the push.**
   - No local `user.*`; `core.bare=false`; `GIT_DIR` unset; author `Michael Dibert <mikied68@gmail.com>`.
   - All four b60 commits on origin are authored by mikied68.
   - `idleCompaction` is still false.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | owner | next step |
|---|---|---|---|
| T1 | Tier A review of cdf71e894 (#1274) | cc | discharge with `tools/tier_a_review_gate.py --discharge hank <opened_at> "<verdict>"` |
| P1 | the SAIRNcode trial gate is client-side only | Michael decides | if a real paywall is wanted: add `license_keys.trial_ends_at` (or a trial table) and a server check in `api/sc-auth.js` login |
| R1 | the readiness presence signal for coordinator/scheduler | Michael, only if wanted | keep it (current), or suppress the state-ID element for non-HR roles |
| A1 | run sql/alf-audit-owner-recovery.sql (b59) | Michael | unchanged |
| G1 | the fx identity in the cody and fourth clones (b59) | cody, fourth | unchanged |
| U1 | untracked files in the clone root that are not mine | owner | unchanged |

## 5. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
