# SAIRN handoff — cody b62 (2026-10-29)

## Committed / pushed state
- **Item 1: the b61 work LANDED, tip `917d9bdba`. The full gate passed with 0 REFUSED lines.**
  - The manifest commit `7641c8c60` landed as `659888571`. A rebase rewrites the sha.
  - Before the gate passed, it blocked twice, and each was fixed at the cause:
    1. the register-feed gate: a record was added for the sairnfreedom fix (`01a24fad6`);
    2. Tier A: an obligation was opened for sf_trustee_audits and sf_officers, assigned to **cc**. The derived docs were regenerated.
- **The b62 work LANDED, tip `053e52285`.** It carries the Semgrep fix (`cf49bdc15`, as rebased), the manifest declaration and the register record.
  - The gate blocked it twice on derived docs. Both times the rebase onto a moving origin made freshly regenerated docs stale again.
  - **Push-script gap, routed to O7.** In gate mode the script does not regenerate derived docs after its own rebase; only the pure-base path does.
- **Claim:** sairnfreedom, cody b62. It is released at close.

## 2. api/b48-sd-agent-error-leak.test.js: FULL OUTPUT (for the auditor's open chain item)
Run at HEAD `917d9bdba`. The file was last changed in `c53c75c1b` (cody b48, 2026-10-22). Command: `node api/b48-sd-agent-error-leak.test.js`.
```
api/sd-agent.js -- the last catch never relays err.message (hover H1 #1684)
  ok - A. Anthropic refuses with a message -> its status, the fixed sentence, no upstream text
  ok - B. the fetch itself throws -> 502, the fixed sentence, no exception text
  ok - X. ABLATION: with the pre-b48 line restored, arm A's check FAILS

3/3 passed
rc=0
```

## 3. G1: the fx@example.invalid identity scan of this clone (hank's method)
- **Method.** I took the fx-identity commits on all refs and intersected them with the commits this clone's reflog shows it CREATED: commit, amend, merge, cherry-pick, or a rebase pick/continue. The reflog reaches back to 2026-09-21.
- **fx@example.invalid: DIRTY HISTORY, CLEAN NOW.**
  - 1,651 such commits exist on all refs.
  - **374 were created in SAIRN-cody**, from 2026-10-06 12:44 (`ae47c86ad`, "docs(items 10-13)") to 2026-10-22 10:15 (`85e774932`, "chore(claims): cody releases platform").
  - 357 of those are on origin/main; the rest are rebased-away originals.
  - The full list is in the b62 scratchpad as `fx_cody_commits.txt` (sha, date, ae/ce, subject).
- **fx@local** (this clone's later identity leak, fixed in b57): 47 were created here, 2026-10-22 10:24 to 2026-10-28 14:08 (`2c16eb91c`, the b56 deliverables).
- **Since then: 82 of 82 commits created here are authored and committed by mikied68.** The b57 fix holds. Today, `user.name` and `user.email` come only from the global `~/.gitconfig`, with no local override.
- History is NOT rewritten. That would be a force push on a shared branch, and it is Michael's decision, as with hank's 426.

## 4. Methodology: the two carried gaps, root-caused before patching
### 4a. The calibration-confidence gap: ROOT-CAUSED; it is H2's, NOT patched here
- **Root cause.** It is missing DATA, not a missing feature.
  - H2's `calibration_tracker.py` (outside the repo, in H2's tools-hover2) scores H2's own stated confidences.
  - **10 findings carry a confidence and have no resolution row:** seq 1078, 1079, 1080, 1082, 1083, 1084, 1085, 1091, 1109, and **1115**. b55's list stopped at 1109, so 1115 was missed.
  - `calibration_resolutions.jsonl` has 13 rows, the last on 2026-10-20T16:43Z.
  - The score exists, Brier 0.0375 over 10, but it **cannot discriminate**: resolution is 0.0000 at a base rate of 1.000.
  - Each confidence has to be resolved by an instrument other than the one that produced it (seq1106).
- **Owner.** H2. The tool, the log and the resolutions file all fall under the auditor deny scope (`sairn-hover*`), so a build agent must not write them. **Routed to H2:** resolve the 10, including 1115.
- **The build-side namesake is a different thing.** `tools/checker_confidence.py` fuses stability and evidence; it has no calibration concept. It is landed (b55 `98bb61e17`), has owner null, and has no gap of this kind.
### 4b. The Semgrep .html/.sql coverage gap: ROOT-CAUSED and FIXED on the build side
- **Root cause.** The SAIRN rules are `languages: [javascript, typescript]`, so Semgrep targets .js/.ts files only.
  - Every app is an .html whose code is inline `<script>`, and Semgrep removed extract mode in 1.65.0.
  - `tools/run_semgrep.py` treated a file as unscanned only if it appeared in Semgrep's `errors`. A file Semgrep never targets is in neither `results` nor `errors`, so **24 apps' JavaScript was silently never scanned.**
  - No rule targets SQL.
- **Fix (`cf49bdc15`).**
  - Each tracked app's inline JS is written to a twin with the same line numbers, scanned with the same config, and mapped back to the .html.
  - Coverage is read from Semgrep's own `paths.scanned`. An unreadable app, or a twin that was not scanned, is COULD NOT SCAN, exit 2.
  - The report states coverage:
    - inline JS of 22 apps scanned;
    - **NOT COVERED: 313 of 313 tracked .sql files**, because no SQL rule exists. This is a disclosed scope limit, not a pass.
- **Real run.** Exit 1 with 1 finding: `api/sd-data.js:2301`. The active-credential pre-gate calls `verifySessionToken(preToken, licHash)` with no app. It is unchanged since `c8b5e5b12` and was already reported before this change. The 22 app twins add no finding.
- **Test.** `tests/run_semgrep_inline_probe.py` has 9 arms:
  - a live CONTROL: the rule run on the .html itself finds nothing;
  - the twin finds the violation at the page's own line 7.
  - The probe is red on the pre-fix tool. The encoding probe has 0 failures, and the rule tests pass 2/2.
- **H2's own Semgrep arm** (`tools-hover2/semgrep_risk_pack.py`, seq1091/1097/1099) has the same .html gap. It is H2's; the twin approach here is available to it.

## 5. The emailed-anchor chain-log contradiction (seq 813/871/1156/1704/1721): DETERMINED, NOT EDITED
- **Boundary.** Every entry involved is in the auditors' hash-chained logs, outside the repo and under the `sairn-hover*` deny scope.
  - H2: `~/.claude/projects/C--Users-marsh-Documents-SAIRN-hover2/hover-audit-log/hover-audit-log.jsonl`
  - H1: the same path under the `...SAIRN-hover` project directory.
  - The chain is append-only; editing an entry breaks every hash after it. **A build agent does not write there. These are routed, not fixed.** Read-only access was used.
- **Which entries are wrong:**
  1. **H2 seq813 (b19) is wrong.** It says the emailed-mirror-anchor requirement was "retired… the email step is gone". Its own change only WIDENED the restore gate, to accept a stamped-sent email OR an RFC3161 token. H1 seq1465 checked this against H2's b19 handoff, and WEAKENING-FLAGS.md:88-91 agrees.
  2. **H2 seq871 (b33) is the real removal**, recorded as Michael's decision: "the emailed-anchor path is dropped, not merely optional".
  3. **H2 seq1111, 1147 and 1156 contradict 871.** They list "the emailed-anchor leg" as an open decision of Michael's, but 871 recorded the decision.
     - What is really left is H2's own tooling: `cmd_push()` still prints email instructions, `cmd_anchor_sent()` and the outbox still exist, and the stale seq1004 `sent:false` anchor is still in the outbox.
     - WEAKENING-FLAGS.md:71-77 already flags this as an unbundled follow-on.
  4. **H1 seq1704, 1715 and 1721 are literally accurate but overstated.**
     - "DRILL PASSED: restored entry 691 matches the recorded anchor" compares against the seq-691 anchor mail. No fresh anchor mail exists, about 1,000 entries on.
     - By H1's own procedure (seq588: "all three must agree"), "PASSED" overstates the result.
     - **The b33 decision is recorded only for H2's `hover2_log_mirror.py`.** No entry shows that it covers H1's `hover_backup_mirror.py`.
- **Fixes, owned elsewhere:**
  - H2: append a correction to seq813 and remove the email machinery from `hover2_log_mirror.py`, as already flagged.
  - H1: append a correction qualifying "DRILL PASSED".
  - **Michael:** state whether the email-leg removal also covers H1's mirror.
- **Correcting my own b55 wording.** `SAIRN-handoff-cody-b55.md:37` said the WEAKENING-FLAGS sign-off was "still OPEN", and that "no H1 entry records the b19 retirement".
  - **Both are wrong at HEAD.** H1 signed Flag 1 on 2026-10-15 (WEAKENING-FLAGS.md:20). The "b19 retirement" premise is item 1 above, which is false.
  - This handoff is the correction; the b55 file is a dated record and is left as written.

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | Tier A reviews: sairnfreedom trustee panel (b61), plus b57 and b58 | cc |
| O2 | 10 unresolved H2 confidences (incl. seq1115) | H2: resolve each from an independent instrument |
| O3 | The emailed-anchor corrections | H2 (seq813, mirror tooling), H1 (DRILL PASSED wording), Michael (does it cover H1's mirror?) |
| O4 | `api/sd-data.js:2301` two-argument verifySessionToken in the active-credential pre-gate | the sd-data owner decides whether app-agnostic is intended; the rule flags it |
| O5 | No Semgrep rule targets SQL (313 files) | a SQL rule set, or keep it as a disclosed limit |
| O6 | History: 374 fx@example.invalid + 47 fx@local commits from this clone | Michael's decision (no rewrite without it) |
| O7 | Gate-mode retries do not regenerate derived docs after the rebase | cc, with push_retry.py: regenerate after every rebase, not only on a pure-base skip |
