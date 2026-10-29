# SAIRN handoff — cody b60 (2026-10-29)

b60 lands the b59 work, minus the hover_separation (M1) fix that Michael directed to be dropped. It also reports three findings that are new and not fixed.

## Committed / pushed state
- **LANDED, tip `335dd33df`.** The full gate passed on try 1, with no REFUSED line. `merge-base --is-ancestor` is true.
- **What the push carried** (items 1, 2, 4 and 5 of b59):
  - `199e3563f`: the dead_function_sweep guard;
  - `14f6a1b1f`: the WRITE_RE verb sweep;
  - `cb49b0dd6`: the JS extractor, re-picked from `5b71ca7e0`;
  - `4de79b471`: the red-triage doc, re-picked from `a510f5940`;
  - `6b88faaca`: the register record for the guard fix.
- **The M1 commit was dropped, not pushed.** It is `dcc4af020` (`tools/hover_separation_audit.py` + its probe); the manifest gives `tools/` to cc.
  - Michael ran `git reset --hard 14f6a1b1f`, the commit's parent. Auto mode had denied the reset to me.
  - Afterwards, `merge-base --is-ancestor dcc4af020 HEAD` is false, and no hover file is in the outgoing diff.
  - The reset also took 5b71ca7e0, a510f5940 and the two-record register commit off HEAD. The first two were cherry-picked back, and the guard's register record was re-added on its own.
- **The dropped work still exists locally.** The local branches `cody-b59-hover-hold` (tip 034ad2917) and `cody-b59-full` (tip a510f5940) hold the M1 fix, with probe arms J1–J5 at 159/0. **Neither is pushed.** Route to cc (the path owner) or re-declare it before using them; delete them once routed.
- **Claim:** item 2 was done before the push. `sairn_claim.py own` showed the PLATFORM claim HELD by the pid lock but 11.5 h old, so `claim` re-took it at 2026-10-29T10:05Z for this push. It is released at close.

## b59 results that landed (detail in the b59 commits and the triage doc)
1. **33 reds triaged** in `docs/2026-10-28-cody-b59-red-triage.md`:
   - **33 are REAL at HEAD and 0 files are clone artefacts.** One arm was a clone artefact: the install_git_hooks CONTROL arm, which reads `core.hooksPath`.
   - The split is 24 TEST-STALE, 5 PRODUCT/DATA and 4 TEST-BUG. Each has its last-green and first-bad sha.
   - The 543/903 floor stands as measured.
2. **dead_function_sweep guard: the trip was a false positive.**
   - sairnbiz, sairncash and sairnsenior are 25–31% real comments. An independent count, which does not use the stripper, agrees within 0.5 points.
   - The fixed 25% is replaced by `comment_estimate() + 5` points.
   - All 22 apps are now swept, exit 0, TOTAL_DEAD 100. The three apps add 587 functions and 0 dead.
   - The probe's runaway fixture is now a real runaway. Its comment-heavy arm is red on the old tool.
4. **WRITE_RE verbs.** It now covers write, write_batch, soft_delete, delete and approve_clock_correction. Each was checked against its sd-data branch.
   - The compute verbs (evaluate, route, reconcile and others) contain no write.
   - It changes 0 findings today.
   - There are 4 fixtures; the 3 verb arms are red with the old list.
5. **JS extractor.**
   - It now judges `assert.ok(<plain value>, LABEL)`, and the registered limit falls 35 → 27.
   - Its precision on the tree was **0 true of 4**, so its verdicts are capped at ADVISORY. CONFIRMED stays at 33.
   - Fixtures 71/71, probe 43/0.

## NEW FINDINGS, reported and NOT fixed (b60 items 4–5)
| # | finding | evidence | owner |
|---|---|---|---|
| F1 | **sairnfreedom says "held on this device only" for a record that is already syncing to the server.** sf_trustee_audits reached the server in e3446a48b, but the flagbox at sairnfreedom.html:1668 still says the record is held on this device only. The user is told something false about where their data is. | tests/sairnfreedom_segregation_of_duties.js arm D4: last green e12ed2623, first bad e3446a48b | sairnfreedom's owner (e3446a48b's author, likely fourth) |
| F2 | **`install_git_hooks.py --check` has not been able to confirm that git fires the hook since 2026-09-28.** Since 2e1ad2775, `.githooks/prepare-commit-msg` refuses when `tools/staged_*_check.py` is missing. The check's fire test commits in a scratch repo with no tools/, so the commit is refused and `--check` exits 2. The verification that hooks are live is blind. | tests/install_git_hooks_check_probe.py: last green 67d7322c3, first bad 2e1ad2775 | the hook / gate owner (cc) |
| F3 | **7 register records carry `recurrence_open: "yes"`, which states nothing.** The field exists to name the residual. "yes" names none, and `defect_register --check` does not refuse it. | tests/run_capa_fields_probe.py: last green d6e58c617, first bad fe8e6cb7c (+3 more in 065d11350) | the record authors; defect_register owner for the missing refusal |

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | F1, F2, F3 above | route as listed; none is fixed |
| O2 | b55 M1 (hover_separation) fix exists only on the local branches | cc decides: take it, or declare the path to cody; then push or delete the branches |
| O3 | 24 TEST-STALE + 4 TEST-BUG reds (triage doc) | each test's owner; the doc names first-bad commits |
| O4 | local_only_shape arm 6: 3 truly local-only collections (sd_aiq_timings, sb_id_series, sairnlegacy_cs_pending) | product decision per app |
| O5 | the hover probe's G10–G14/G21 arms pick "the tool's latest commit" and go red when that commit is auditor-scope only | whoever next owns the probe: pin to an always-out-of-scope path and check it in G10 |
| O6 | assertion_label_shape Python path: `assert all(...)`, set `<=` and `min() >=` fall into the bare branch | cody: fix in `_ops_in()` with fixtures |
| O7 | Tier A reviews (b57, b58) | cc |
