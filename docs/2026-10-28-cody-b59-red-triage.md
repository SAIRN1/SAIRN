# cody b59 — triage of the 33 reds from the b58 partial run

## Method and summary
- **Source.** These are the 33 files that came back FAIL in the b58 paced continuation of `run_all_tests`, run in a throwaway `git clone --local`.
- **Method.** Each file was re-run at HEAD `90e324fd1` in a fresh detached worktree of the live repo, with `node_modules` junctioned in and the session identity copied. Each red was then walked back to its **last green** commit by running it at candidate commits (bisect where needed). The first-bad commit was run to confirm it fails with the same arm as HEAD.
- **No fixes were made.** This is a routing document.

**Result: 33 of 33 are REAL reds at HEAD. 0 files are clone artefacts.**
- One ARM is a clone artefact. In `install_git_hooks_check_probe`, the CONTROL arm "clone still points at .githooks" fails only because a `git clone --local` has no `core.hooksPath`. The file is red at HEAD for a separate, real reason.
- **24** are TEST-STALE: the product changed on purpose and the test asserts the old shape.
- **5** are PRODUCT-REGRESSION, and so is one of them on the data side.
- **4** are TEST-BUG.

Session names come from the commit subject where it carries one. Otherwise they come from the commit body or a handoff that cites the sha, so treat those as likely rather than certain. `fx`-authored commits are not attributed.

## PRODUCT-REGRESSION (5): act on the product or the data, not just the test
| test | first bad | what is actually wrong |
|---|---|---|
| tests/sairnfreedom_segregation_of_duties.js | e3446a48b (sf_trustee_audits reached the server) | sairnfreedom.html:1668 still tells the user the record is "held on this device only". The copy is now false. Arm D4 also needs rewriting. |
| tests/hover_quotable_session_vocab_check.py | 2510590da (claim(cloud): sairncash audit) | a `cloud` session exists and QUOTABLE in tools/hover_separation_audit.py does not name it. This is a registry change. |
| tests/install_git_hooks_check_probe.py | 2e1ad2775 (staged-blob credential refusal) | `.githooks/prepare-commit-msg` refuses when `tools/staged_*_check.py` is missing. So `install_git_hooks.py --check`'s fire test, run in a scratch repo, cannot commit and exits 2. **`--check` has not been able to verify that git fires the hook since 2026-09-28.** |
| tests/rebase_resolve_merge_control.py | c680a4c1d (REPO from `__file__`) | `sairn_rebase_resolve.py` can no longer resolve a rebase in any repo but the clone it lives in. Real use inside a clone is unaffected; arguable. |
| tests/run_capa_fields_probe.py | fe8e6cb7c, 065d11350 (register records) | 7 register records carry `recurrence_open: "yes"`, which states no residual. `defect_register --check` does not refuse that. |

## TEST-BUG (4)
| test | why |
|---|---|
| tests/sairncare_compliance_window_boundary.test.js | Red since its own commit, 9f04ad39a. The X1 parser reads only compliant/non-compliant, so the corrected comment "a determinate PASS" captures "a". |
| tests/rt_routes_live_probe.py | Needs SD_LICENSE, SD_OWNER_PIN and the live deployment. Without them it exits 2, where the suite's skip code is 3, so it counts as FAIL. It was not run with credentials. |
| tests/run_batch_cleanup_probe.py | Its section 2 runs the real `push_landed()` sweep, which deletes the section-3 fixture whenever HEAD is already on origin/main. Green only with unpushed commits. Red since birth. |
| tests/run_checker_control_probe.py | `tests/criticality_rollup_list_review_probe.py` (bff244d36) declares `CONTROLS_FOR = []`, and the meta-arm flags any file declaring nothing. Needs an exemption or a declaration. |

## TEST-STALE (24): the product moved on purpose
| test | last green → first bad | the assertion that is now stale |
|---|---|---|
| tests/dnt_complaint_qr.js | 95e31d3b7 → 01aaa9988 | the fake QR box has no `querySelector`; the a11y pass sets the img alt |
| tests/intake_form_public_surface.js | f71526d4a → b2b02bbd0 | a tripwire: `sd_quote_request_photos` is now in the schema snapshot, and a live re-check is owed |
| tests/sairnlaw_clearance_refusal_review_probe.js | 8f2036615 → 7e43c9dab (cody b28) | the roster stub has no role, so the result is 403 COUNTERSIGN_ROLE_REVOKED |
| tests/sairnlegacy_reservation_lock.js | 9654772e7 → 54d6e95d9 | leg_cremations' countersign lock refuses before the id check, so 35/36 pass |
| tests/scp_quotes_review_probe.js | 616f6edba → b09674f65 | the harness does not extract the new `scpSetSendBtn` helper |
| tests/sd_data_write_attribution_three_apps.js | 501bcd150 → d7773533f | rf_schedule set_status moved from the blob to `status_changed_by*` columns |
| tests/sd_tax_money_coercion.js | 53168bb50 → 7e4551687 | 46 grandfathered entries are hard-coded; the baseline was re-done |
| tests/stonedesk_exec_msgs_gate.js | b27df033c → 1b8ac96fa (cc b38) | the stub returns no employee row, so the result is CREDENTIAL_INACTIVE |
| tests/sairncare/test-compliance-rules.js | 90c1a9c3e → 5a2eb3793, 0a4b2f765 | there are 5 states now, not 4; a stacked requirement returns `meets: null` |
| api/sd-data-family-contacts.test.js | 7ea69597e → 24690756d | care roles now get a scoped read (200); the test expects 403 |
| api/sd-data-law-trusttx-clearance.test.js | b9635216f → 7e43c9dab (cody b28) | the roster stub has no role |
| api/sd-data-leg-bookings-toctou.test.js | 69f828f1a → 3c574265f (b56) | `sdnData` gained a 5th parameter; the anchor is the 4-parameter signature |
| api/sd-data-leg-session-gate.test.js | 69f828f1a → 3c574265f (b56) | the same anchor |
| tests/active_credential_gate_probe.py | c57b50ab1 → 9a70365b5 (hank b16) | the NO_ACTIVE_CHECK log text was reworded, so arm 6's anchor finds 0 |
| tests/defect_register_capa_control.py | 9fe28f21c → 8f99bb38f | the mock `lambda sha:` must now be `derive(sha, ext)` |
| tests/law_reconcile_role_vocab_check.py | c0263b7c2 → dadfedf48 | ROLES_BY_APP is now `roleSet({...})` |
| tests/law_reconcile_role_vocab_control.py | c0263b7c2 → dadfedf48 | the set is frozen and moved to api/_lib/law-roles.js |
| tests/local_only_self_evidence_probe.py | d5e631143 → e3446a48b | the BASELINE is 35; sairnfreedom is now 36 covered (a real improvement) |
| tests/local_only_shape_probe.py | 74401bd44 → 68a9d4bc7 | per-app BASELINE drift. **Arm 6 also names 3 real local-only collections (sd_aiq_timings, sb_id_series, sairnlegacy_cs_pending), which need a product decision.** |
| tests/run_alf_read_order_sabotage_probe.py | 70192c7f6 → 76885c1bd | the suite now catches mutant 5; the probe still expects it to be blind |
| tests/run_b13_b14_ablation_record.py | f4d4345f2 → 9f30a3690, 144dfb715 (hank b17) | the needle changed; **the subject `run_criticality_tier_probe.py` is itself red since 144dfb715** |
| tests/run_baseline_readiness_probe.py | 0646a97cf → b431e6377 | it asserts today's register verdict, which has moved |
| tests/run_batch_manifest_probe.py | 171bf7ed4 → 9603441d8 (cc b7) | it pins 21/21 fixtures, and there are 39 now |
| tests/run_claim_doc_freshness_probe.py | ca22af822 → 7274e05f8, 0d33f6591 | CLAUDE.md lost the anchor line; the fixture claim has no timestamp |

## What this means for the floor
- The b58 floor of **543/903 passing** stands as measured.
- None of the 33 reds is an artefact of the throwaway clone, so the b58 method was sound. The high red rate is real drift in the not-yet-covered half of the suite.
- 24 of the 33 are tests that fell behind deliberate product changes. No run of the full suite had reached them since those changes landed.

Per-run outputs are in the b59 scratchpad (`t0-*`, `t1/`, `t2/`, `bis0.log`). They are not committed.
