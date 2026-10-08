# External tooling index

Written H1 batch T item 3. Full inventory of this role's external working directory (C:/Users/marsh/.claude/projects/C--Users-marsh-Documents-SAIRN-hover/hover-audit-log/), the one place batch R's own search never checked before wrongly concluding a tool was missing (seq1125, corrected seq1132). Categories below: tools newly committed this batch, tools already mirrored into this repo before this batch, handoffs and reference docs committed this batch, and the operational data this role deliberately does not commit, with the reason for each.

## Tools newly committed this batch (19) -- were external-only

| File | Path | Purpose (from its own docstring) |
|---|---|---|
| `hover_audit_trail_reviewer.py` | `.claude/skills/sairn-hover-auditor/tools/hover_audit_trail_reviewer.py` | Reads docs/BYPASS-LOG.jsonl and reports, per LIVE bypass entry, two mechanically-checkable facts -- never a judgement on whether bypassing was wise at decision  |
| `hover_code_normalize.py` | `.claude/skills/sairn-hover-auditor/tools/hover_code_normalize.py` | Strip comments/docstrings and normalize identifiers -- so a correctness verdict on code isn't swayed by a misleading comment or a misleading name |
| `hover_cross_resource_gate_check.py` | `.claude/skills/sairn-hover-auditor/tools/hover_cross_resource_gate_check.py` | Independent cross-resource gate-parity screen: for resource === 'x' && action === 'y' dispatch files, group branches by the TABLE each one reads and flag a tabl |
| `hover_hardfail_cap.py` | `.claude/skills/sairn-hover-auditor/tools/hover_hardfail_cap.py` | hover_hardfail_cap.py -- a general-purpose hard-fail severity cap for any scored item list (SOC 2-style control results, a batch's own findings, a review checkl |
| `hover_hardfail_severity_scorer.py` | `.claude/skills/sairn-hover-auditor/tools/hover_hardfail_severity_scorer.py` | Star-flagged (security / data-integrity / irreversible-operation) items cap a batch's result regardless of how many other items passed |
| `hover_hash_citation_guard.py` | `.claude/skills/sairn-hover-auditor/tools/hover_hash_citation_guard.py` | hover_hash_citation_guard.py -- the system-level fix from the batch-O item 7 blameless postmortem (seq1082's self-caught fabricated chain-hash) |
| `hover_identity_attribution_check.py` | `.claude/skills/sairn-hover-auditor/tools/hover_identity_attribution_check.py` | Does every WRITE action in a handler file record WHO performed it |
| `hover_independence_grader.py` | `.claude/skills/sairn-hover-auditor/tools/hover_independence_grader.py` | For each finding in a batch (a seq range of this role's own log), grades three independence dimensions -- EVIDENCE TYPE, MUTABILITY, METHOD SEPARATION -- each S |
| `hover_money_on_row_sweep.py` | `.claude/skills/sairn-hover-auditor/tools/hover_money_on_row_sweep.py` | hover_money_on_row_sweep.py -- the dnt_supplies/#446 shape, automated |
| `hover_own_exit_capture.py` | `.claude/skills/sairn-hover-auditor/tools/hover_own_exit_capture.py` | Runs a command and reports ITS real exit code, captured directly by this role's own subprocess call -- never a harness completion-status message, never a status |
| `hover_own_http.py` | `.claude/skills/sairn-hover-auditor/tools/hover_own_http.py` | Minimal real-HTTP helper, stdlib only, no dependency on tools/sairn_http.py |
| `hover_py_guard_checker.py` | `.claude/skills/sairn-hover-auditor/tools/hover_py_guard_checker.py` | hover_py_guard_checker.py -- a static, syntax-tree-only Python checker for four honesty-shaped defect classes this platform keeps re-discovering by hand |
| `hover_reexecution_check.py` | `.claude/skills/sairn-hover-auditor/tools/hover_reexecution_check.py` | Given a CLAIM (command, claimed exit code, optional claimed output substrings), re-run the command for real in this clone and compare |
| `hover_review_triage.py` | `.claude/skills/sairn-hover-auditor/tools/hover_review_triage.py` | hover_review_triage.py -- before spending a 'git show --stat' plus a full read on every candidate in hover_coverage_ledger.py's UNCOVERED list, decide which one |
| `hover_sha_citation_check.py` | `.claude/skills/sairn-hover-auditor/tools/hover_sha_citation_check.py` | Given a tracking doc, checks every CITED commit sha -- a backtick- delimited hex run, 7-40 chars -- against the real git history |
| `hover_timestamp.py` | `.claude/skills/sairn-hover-auditor/tools/hover_timestamp.py` | hover_timestamp.py -- RFC 3161 trusted timestamp for this role's own chain tip, requested from a real, external, independent authority (freetsa.org) rather than |
| `regenerate_repoint_list.py` | `.claude/skills/sairn-hover-auditor/tools/regenerate_repoint_list.py` | regenerate_repoint_list.py -- the MOVED-SINCE repoint list generator, promoted from three rounds of inline one-off scripts to a real tool with its own self-chec |
| `register_citation_check.py` | `.claude/skills/sairn-hover-auditor/tools/register_citation_check.py` | register_citation_check.py -- every explicit path:line citation in docs/CRITICALITY-TIERS.md, verified to anchor at HEAD (2026-09-30, directed item 7) |
| `run_citation_class_mutation_test.py` | `.claude/skills/sairn-hover-auditor/tools/run_citation_class_mutation_test.py` | Mutation test for citation_class_check.py (2026-09-30, item 3 of the directed queue): copy the real log, inject 20 KNOWN-WRONG citations spread across all five  |

## Tools already present in both locations before this batch (37)

| File | Path | Purpose |
|---|---|---|
| `citation_class_check.py` | `.claude/skills/sairn-hover-auditor/tools/citation_class_check.py` | citation_class_check.py -- three honest classes for every cited claim in this append-only log, because "correct when written, moved later" and "wrong when writt |
| `claim_collision_scan.py` | `.claude/skills/sairn-hover-auditor/tools/claim_collision_scan.py` | claim_collision_scan.py -- retrospective detection of the 2026-09-15 session- lock collision SHAPE, run against .claims history |
| `code_quality_baseline.py` | `.claude/skills/sairn-hover-auditor/tools/code_quality_baseline.py` | code_quality_baseline.py -- a real, first cyclomatic-complexity baseline for this platform, never computed before tonight (2026-09-18), per direct instruction,  |
| `defect_density_weighting.py` | `.claude/skills/sairn-hover-auditor/tools/defect_density_weighting.py` | defect_density_weighting.py -- a real, driven rotation input: which files and modules have this role's own self-log ACTUALLY produced findings against, not whic |
| `dependency_health_check.py` | `.claude/skills/sairn-hover-auditor/tools/dependency_health_check.py` | dependency_health_check.py -- bus-factor / maintainer-health scanner for SAIRN's own third-party dependency tree |
| `flagged_then_argued_down_scan.py` | `.claude/skills/sairn-hover-auditor/tools/flagged_then_argued_down_scan.py` | flagged_then_argued_down_scan.py -- the Mythos 5 shape named in SKILL.md (2026-09-17, round 2 item b): a build agent's own reasoning trail correctly names a con |
| `freshness_stamp.py` | `.claude/skills/sairn-hover-auditor/tools/freshness_stamp.py` | freshness_stamp.py -- one line every report-style hover tool prints so a reader can SEE the vintage of a list instead of assuming it is current |
| `git_history_secrets_scan.py` | `.claude/skills/sairn-hover-auditor/tools/git_history_secrets_scan.py` | git_history_secrets_scan.py -- full git-HISTORY secrets scan, never picked up before tonight (2026-09-17), built on real, live motivation: a real GitGuardian al |
| `hover_backup_mirror.py` | `.claude/skills/sairn-hover-auditor/tools/hover_backup_mirror.py` | hover_backup_mirror.py -- off-machine mirror for this role's hash-chained LOG, ANCHORS and tip BEACON -- AND NOTHING ELSE -- plus the restore drill that proves  |
| `hover_claim_precheck.py` | `.claude/skills/sairn-hover-auditor/tools/hover_claim_precheck.py` | hover_claim_precheck.py -- item 4 of the 2026-09-21 setup queue: "a cheap deterministic pre-check on command shape before it runs, catching malformed invocation |
| `hover_cold_scan_pool.py` | `.claude/skills/sairn-hover-auditor/tools/hover_cold_scan_pool.py` | hover_cold_scan_pool.py -- Tier B/C resources this role has never once mentioned in its own self-log, to pick a genuinely cold target from during an undirected  |
| `hover_completeness_probe.py` | `.claude/skills/sairn-hover-auditor/tools/hover_completeness_probe.py` | hover_completeness_probe.py -- an OUTSIDE-IN completeness check: does docs/CRITICALITY-TIERS.md (the registry a Verification Certificate's own "X of Y resources |
| `hover_coverage_ledger.py` | `.claude/skills/sairn-hover-auditor/tools/hover_coverage_ledger.py` | hover_coverage_ledger.py -- which of the platform's own discharged Tier A review obligations this role has actually independently re-verified, and which are gen |
| `hover_duplicate_finding_check.py` | `.claude/skills/sairn-hover-auditor/tools/hover_duplicate_finding_check.py` | hover_duplicate_finding_check.py -- before logging a new finding, check whether the SAME underlying defect is already tracked under a different citation or comm |
| `hover_editor_review.py` | `.claude/skills/sairn-hover-auditor/tools/hover_editor_review.py` | hover_editor_review.py -- the EDITOR pass: a mechanical re-derivation of a report's own checkable claims against CURRENT source, run before the report is pasted |
| `hover_editor_review_criteria.py` | `.claude/skills/sairn-hover-auditor/tools/hover_editor_review_criteria.py` | hover_editor_review_criteria.py -- criteria and fixture lock for hover_editor_review.py, kept in their own file per the blind-analysis convention (docs/2026-09- |
| `hover_live_refusal_check.py` | `.claude/skills/sairn-hover-auditor/tools/hover_live_refusal_check.py` | hover_live_refusal_check.py -- TIER 1 of the live-execution capability queued 2026-09-21 item 3, built on Michael's explicit authorization 2026-09-22: "real API |
| `hover_log.py` | `.claude/skills/sairn-hover-auditor/tools/hover_log.py` | hover_log.py -- the hover auditor's own black-box self-log |
| `hover_log_rotation_control.py` | `.claude/skills/sairn-hover-auditor/tools/hover_log_rotation_control.py` | Sabotage control for hover_log.py's rotation interlock |
| `hover_pure_js_exec.py` | `.claude/skills/sairn-hover-auditor/tools/hover_pure_js_exec.py` | hover_pure_js_exec.py -- TIER 0 of the live-execution capability queued 2026-09-21 item 3: run a real, verbatim JS function extracted from a platform app's own  |
| `hover_second_opinion.py` | `.claude/skills/sairn-hover-auditor/tools/hover_second_opinion.py` | hover_second_opinion.py -- a genuinely different model checks a CRITICAL finding before it stands unchallenged |
| `hover_self_health.py` | `.claude/skills/sairn-hover-auditor/tools/hover_self_health.py` | hover_self_health.py -- the hover-auditor's own system-of-quality-control check, distinct from any check of a single finding |
| `hover_self_health_hook.py` | `.claude/skills/sairn-hover-auditor/tools/hover_self_health_hook.py` | SessionStart hook: make hover_self_health.py actually FIRE |
| `hover_tip_beacon.py` | `.claude/skills/sairn-hover-auditor/tools/hover_tip_beacon.py` | hover_tip_beacon.py -- a passive, second signal for the self-log's integrity, distinct from the hash chain |
| `hover_tool_index.py` | `.claude/skills/sairn-hover-auditor/tools/hover_tool_index.py` | hover_tool_index.py -- the reuse-loop closer this role's own tools were missing |
| `hover_watchlist.py` | `.claude/skills/sairn-hover-auditor/tools/hover_watchlist.py` | hover_watchlist.py -- a durable list of "not a mismatch TODAY, but check again on the next real read" items |
| `peer_authority_trace_scan.py` | `.claude/skills/sairn-hover-auditor/tools/peer_authority_trace_scan.py` | peer_authority_trace_scan.py -- the platform-side analog of the "GO" moment named in SKILL.md's Hugging Face swarm section (2026-09-17): does a build agent's ow |
| `run_editor_review_v3_known_bad_control.py` | `.claude/skills/sairn-hover-auditor/tools/run_editor_review_v3_known_bad_control.py` | KNOWN-BAD CONTROL for hover_editor_review_criteria.py's CRITERIA_VERSION 3 (IMPLIED_LINE, bare ':NNNN' implied-file citations) -- built 2026-09-29 |
| `run_editor_review_v3_last30.py` | `.claude/skills/sairn-hover-auditor/tools/run_editor_review_v3_last30.py` | Runs the CRITERIA_VERSION 3 editor pass (bare ':NNNN' implied-file citations) over this log's last 30 entries, per direct instruction |
| `run_memory_vs_derived_sweep.py` | `.claude/skills/sairn-hover-auditor/tools/run_memory_vs_derived_sweep.py` | run_memory_vs_derived_sweep.py -- entries #600+ re-derived at HEAD |
| `run_selftest_hygiene_sweep.py` | `.claude/skills/sairn-hover-auditor/tools/run_selftest_hygiene_sweep.py` | run_selftest_hygiene_sweep.py -- does any selftest WRITE outside a temp directory? Built 2026-09-29 after hover_backup_mirror.py's selftest, run from the platfo |
| `sabotage_claim_verify.py` | `.claude/skills/sairn-hover-auditor/tools/sabotage_claim_verify.py` | sabotage_claim_verify.py -- which commits claim a sabotage/mutation count with no matching runnable artifact committed alongside the claim, AND how much that cl |
| `sabotage_closed_system_check.py` | `.claude/skills/sairn-hover-auditor/tools/sabotage_closed_system_check.py` | sabotage_closed_system_check.py -- verify, don't assume, that a sabotage test ran in a closed system: this session, alone, for the whole window |
| `scope_narrowing_check.py` | `.claude/skills/sairn-hover-auditor/tools/scope_narrowing_check.py` | scope_narrowing_check.py -- has what this role actually reviews quietly narrowed over time, without any explicit decision anywhere logging it |
| `tool_provenance_check.py` | `.claude/skills/sairn-hover-auditor/tools/tool_provenance_check.py` | tool_provenance_check.py -- before any hover tool's findings count as confirmed, a DIFFERENT hover instance has to run it against a real historical holdout set  |
| `undirected_sweep_freshness.py` | `.claude/skills/sairn-hover-auditor/tools/undirected_sweep_freshness.py` | undirected_sweep_freshness.py -- makes the deliberately-undirected sweep (SKILL.md, round 3, the Von Arx/wiki-discovery item) a real, running check rather than  |
| `verbalized_audit_awareness_scan.py` | `.claude/skills/sairn-hover-auditor/tools/verbalized_audit_awareness_scan.py` | verbalized_audit_awareness_scan.py -- the earlier, weaker signal named in SKILL.md's Astra section (2026-09-17): a build agent's own reasoning showing AWARENESS |

## This role's own tools built in-repo this engagement (6), never external-only

| File | Path |
|---|---|
| `hover_completeness_probe.py` | `.claude/skills/sairn-hover-auditor/tools/hover_completeness_probe.py` |
| `hover_threshold_cluster.py` | `.claude/skills/sairn-hover-auditor/tools/hover_threshold_cluster.py` |
| `hover_hidden_state.py` | `.claude/skills/sairn-hover-auditor/tools/hover_hidden_state.py` |
| `hover_session_gate_parity_check.py` | `.claude/skills/sairn-hover-auditor/tools/hover_session_gate_parity_check.py` |
| `hover_citation_guard.py` | `.claude/skills/sairn-hover-auditor/tools/hover_citation_guard.py` |
| `hover_ai_redaction_field_check.py` | `.claude/skills/sairn-hover-auditor/tools/hover_ai_redaction_field_check.py` |

## Handoffs committed this batch (17) -- corrects the "14" figure named in this batch's own task text; the real count, counted directly, is 17

Original filenames preserved -- an earlier naming convention (`handoff-h1-<date>[-<letter>].md`) than this role's current one (`<date>-h1-batch-<letter>-handoff.md`), not renamed on commit so no existing cross-reference breaks.

| File | Path |
|---|---|
| `handoff-h1-2026-10-06.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-06.md` |
| `handoff-h1-2026-10-06-b.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-06-b.md` |
| `handoff-h1-2026-10-06-c.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-06-c.md` |
| `handoff-h1-2026-10-06-d.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-06-d.md` |
| `handoff-h1-2026-10-06-e.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-06-e.md` |
| `handoff-h1-2026-10-06-f.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-06-f.md` |
| `handoff-h1-2026-10-06-g.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-06-g.md` |
| `handoff-h1-2026-10-06-h.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-06-h.md` |
| `handoff-h1-2026-10-06-i.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-06-i.md` |
| `handoff-h1-2026-10-06-j.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-06-j.md` |
| `handoff-h1-2026-10-07-k.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-07-k.md` |
| `handoff-h1-2026-10-07-l.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-07-l.md` |
| `handoff-h1-2026-10-07-m.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-07-m.md` |
| `handoff-h1-2026-10-07-n.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-07-n.md` |
| `handoff-h1-2026-10-07-o.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-07-o.md` |
| `handoff-h1-2026-10-07-p.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-07-p.md` |
| `handoff-h1-2026-10-07-q.md` | `.claude/skills/sairn-hover-auditor/handoffs/handoff-h1-2026-10-07-q.md` |

## Handoffs already in-repo (current naming convention, 3)

- `.claude/skills/sairn-hover-auditor/handoffs/2026-10-07-h1-batch-q-handoff.md`
- `.claude/skills/sairn-hover-auditor/handoffs/2026-10-07-h1-batch-r-handoff.md`
- `.claude/skills/sairn-hover-auditor/handoffs/2026-10-08-h1-batch-s-handoff.md`

## Reference docs committed this batch (5)

| File | Path |
|---|---|
| `hover_coverage_ledger_own.md` | `.claude/skills/sairn-hover-auditor/references/hover_coverage_ledger_own.md` |
| `hover_parity_specs.md` | `.claude/skills/sairn-hover-auditor/references/hover_parity_specs.md` |
| `hover_sweep_method_skill.md` | `.claude/skills/sairn-hover-auditor/references/hover_sweep_method_skill.md` |
| `seed_corpus.md` | `.claude/skills/sairn-hover-auditor/references/seed_corpus.md` |
| `tier_population_completeness_spec.md` | `.claude/skills/sairn-hover-auditor/references/tier_population_completeness_spec.md` |

## Operational data deliberately NOT committed, with the reason for each

| File(s) | Why not committed |
|---|---|
| `hover-audit-log.jsonl` | THE chain log itself -- append-only, hash-chained, this role's own record. Not committed by design: hover_log.py's own header states logging its own actions inside the repo it audits would blur the audit/build boundary. |
| `TIP-BEACON.md` | Regenerated on every token refresh (this batch, item 2) -- a point-in-time checkpoint claim, not a stable artifact worth versioning in git. |
| `chain-tip-seq*.msg / .tsr / .tsq` | RFC 3161 timestamp artifacts for one specific past chain tip each -- mirrored to G:/My Drive/SAIRN-status/hover-chain-h1/ instead (batch Q item 1, batch S/T item 2), not git, because they are point-in-time evidence, not code. |
| `freetsa-cacert.pem / freetsa-tsa.crt` | Public CA/TSA certificates from freetsa.org, needed to verify the tokens above locally. Public and reproducible from the CA's own site -- not committed, no reason found this batch that it would need to be. |
| `.mirror-token` | A CREDENTIAL. Never committed, never will be -- this is exactly the secret class CLAUDE.md and every push gate on this platform exist to keep out of git. |
| `.mirror-config.json / .mirror-askpass.py / .mirror-askpass.bat` | The mirror mechanism's own operational config/helper scripts -- infrastructure for moving files between this directory and the repo, not an audit tool, and plausibly sensitive (the askpass scripts exist to supply the credential above without it appearing in a process list). Not committed. |
| `class_detail.json, none27_fresh.json, nosha_sample.json, rederive15.json, rederive15b.json, moved_since_repoint_list.txt, mirror-anchors.jsonl, hover_self_health_fires.jsonl, tool_provenance_validations.jsonl, hover-watchlist.json` | RUN-TIME DATA/OUTPUT from the tools above -- scan results, fixtures, tracking ledgers -- not code. Same category as hover-audit-log.jsonl: this role's own operational state, regenerated by running the owning tool, not meant to be versioned as source. |
| `.gitignore` | This directory's own gitignore -- meaningless to commit into a different repo. |

## sabotage_benchmark/ subdirectory

`fixtures.py` and `run_benchmark.py` already exist at `.claude/skills/sairn-hover-auditor/tools/sabotage_benchmark/` in both locations -- checked this batch, nothing new to commit there.
