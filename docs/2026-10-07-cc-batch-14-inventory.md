# Batch 14 inventory — ownership and location

**Items 6 and 8, 2026-10-07 (cc). READ-ONLY apart from the eighteen `# OWNER:`
lines item 6 asked for.** Every figure below is program output captured at
`a9e9147b`, not retyped.

---

## Item 6 — ownership recorded through the existing mechanism

`docs/tool-owner-map.json` is **generated** (`python tools/tool_owner_map.py`),
and its own vocabulary says which bases are guesses:

| basis | meaning |
|---|---|
| `OWNER_LINE` | the file carries `# OWNER: x`. **AUTHORITATIVE — nothing else is** |
| `LAST_CLAIM` | derived. The most recent session to name it in a FILES list |
| `CONTESTED` | derived, and more than one session has claimed it |
| `NONE` | no OWNER line and no claim ever named it. **UNKNOWN, NOT UNOWNED** |

So "record myself as owner through the existing mechanism" means an `# OWNER:`
line, not a claim — a claim only ever yields `LAST_CLAIM`, which the map itself
labels a guess.

**Eighteen `# OWNER: cc` lines added** — the 17 tools whose read-only `--check`
mode I added on 2026-10-07, plus `role_gate_mc_config.py`:

    audit_checkpoint_status.py   cron_liveness_check.py
    gen_ma_calendar.py           gen_ma_seed.py
    gen_mn_calendar.py           gen_mn_seed.py
    gen_mo_calendar.py           gen_mo_seed.py
    gen_nj_calendar.py           gen_nv_calendar.py
    gen_ok_calendar.py           gen_or_calendar.py
    gen_sc_calendar.py           gen_ut_calendar.py
    gen_va_calendar.py           gen_va_seed.py
    sairn_build_load_gates.py    role_gate_mc_config.py

Each line sits immediately after the shebang, or as line 1 where there is none,
which is where `tool_owner_map.py` and `doc_sha_reseat.py` already carry theirs.
All eighteen `py_compile` clean.

**Measured before and after, `python tools/tool_owner_map.py`:**

| basis | before | after |
|---|---|---|
| `OWNER_LINE` | 28 | **46** |
| `LAST_CLAIM` | 243 | 225 |
| `CONTESTED` | 29 | 29 |
| `NONE` | 680 | 680 |
| total tracked | 980 | 980 |

`OWNER_LINE` +18 and `LAST_CLAIM` −18: the eighteen moved from a derived guess
to an authoritative line, and nothing else moved. `cc` now holds 23 of the 46
authoritative rows.

The tool exits **1**, and that is its REPORT-ONLY design, not a failure — 680
rows are `NONE` and it says so on every run rather than reporting clean.

### The ownerless tools — PRINTED FOR CHAT TO ASSIGN, NOT ASSIGNED

**680 of 980 tracked files under `tools/`, `tests/` and `scripts/` have no owner
at all:** `tests` 502, `tools` 175, `scripts` 3. Of the 175 under `tools/`,
**164 are `tools/*.py`** and those are the ones a finding gets routed to. They
are listed below with what they write.

**How "what it writes" was derived, and what it cannot see.** By `ast` parse —
**nothing was executed**. It reports an `open(...)` whose mode contains `w`, `a`
or `x`, plus calls named `remove`, `unlink`, `rmtree`, `rename`, `replace`,
`mkdir`, `makedirs`, and `json.dump`. **`<computed path>`** means the write
target is built at run time and a static read cannot name it.

**"no write site detected" IS NOT "READ-ONLY".** It means this scan found no
write-shaped call. A tool that writes through a helper, through `subprocess`, or
through a module it imports looks identical to a pure reader here. 85 of the 164
fall in that bucket and none of them has been proved read-only.

| tool (under `tools/`) | what it writes (AST-detected, never executed) |
|---|---|
| `accepted_risk_scan.py` | `os/shutil.replace` |
| `accepted_risk_trigger_check.py` | no write site detected |
| `adversarial_prompt_corpus.py` | `<computed path>` |
| `ai_action_approval_audit.py` | no write site detected |
| `ai_output_resource_scan.py` | no write site detected |
| `ai_prompt_refusal_check.py` | `os/shutil.replace` |
| `allan_deviation_check.py` | no write site detected |
| `assurance_case.py` | no write site detected |
| `audit_licence.py` | no write site detected |
| `bare_run_write_check.py` | no write site detected |

*(the full 164-row table is the generated block below — it is long on purpose,
because a truncated ownership list is indistinguishable from a complete one)*

<!-- OWNERLESS-TABLE-START -->

| tool | what it writes (AST-detected, never executed) |
|---|---|
| `accepted_risk_scan.py` | `os/shutil.replace` |
| `accepted_risk_trigger_check.py` | no write site detected |
| `adversarial_prompt_corpus.py` | `<computed path>` |
| `ai_action_approval_audit.py` | no write site detected |
| `ai_output_resource_scan.py` | no write site detected |
| `ai_prompt_refusal_check.py` | `os/shutil.replace` |
| `allan_deviation_check.py` | no write site detected |
| `assurance_case.py` | no write site detected |
| `audit_licence.py` | no write site detected |
| `bare_run_write_check.py` | no write site detected |
| `benford_check.py` | `os/shutil.replace` |
| `blind_review.py` | `<computed path>` |
| `blob_conversion_coverage.py` | `<computed path>`, `os/shutil.replace` |
| `blob_overrides_column_scan.py` | `<computed path>` |
| `bypass_log.py` | `<computed path>`, `os/shutil.remove` |
| `bypassed_constant_check.py` | no write site detected |
| `check_precedence.py` | no write site detected |
| `checker_confidence.py` | no write site detected |
| `checker_estimate_fusion.py` | `os/shutil.replace` |
| `checker_kit.py` | no write site detected |
| `citation_no_source_report.py` | no write site detected |
| `claim_search.py` | no write site detected |
| `cleanup_confirm_check.py` | `os/shutil.replace` |
| `cleanup_residue_check.py` | no write site detected |
| `closing_error.py` | no write site detected |
| `coding_rule_discovery.py` | no write site detected |
| `comment_quote_check.py` | `os/shutil.replace` |
| `comment_sensitivity_check.py` | `<computed path>`, `os/shutil.replace`, `os/shutil.rmtree` |
| `committer_identity_check.py` | `os/shutil.replace` |
| `completeness_check.py` | `os/shutil.replace` |
| `condition_coverage.py` | `<computed path>`, `json.dump -> a file object`, `os/shutil.makedirs`, `os/shutil.replace`, +1 more |
| `conflict_marker_check.py` | `os/shutil.replace` |
| `conflict_marker_preflight_hook.py` | no write site detected |
| `copy_exactly_check.py` | `os/shutil.replace` |
| `csv_formula_injection_check.py` | `os/shutil.replace` |
| `defect_budget.py` | `os/shutil.replace` |
| `defect_budget_gate.py` | no write site detected |
| `defect_budget_policy.py` | `<computed path>` |
| `defect_dispersion.py` | no write site detected |
| `deploy_verify_notify.py` | no write site detected |
| `discarded_verdict_check.py` | `os/shutil.replace` |
| `discarded_verdict_crossfile.py` | `os/shutil.replace` |
| `dora_metrics.py` | no write site detected |
| `duplicate_global_check.py` | no write site detected |
| `employee_auth_guard_check.py` | no write site detected |
| `entitlement_freshness_check.py` | `os/shutil.replace` |
| `entity_baseline_readiness.py` | no write site detected |
| `export_coverage_check.py` | no write site detected |
| `extract_panels.py` | no write site detected |
| `fail_open_check.py` | `os/shutil.replace` |
| `first_article_check.py` | `<computed path>` |
| `first_article_inspection.py` | `<computed path>`, `os/shutil.replace`, `os/shutil.rmtree` |
| `fmea_draft.py` | `<computed path>`, `os/shutil.makedirs`, `os/shutil.remove`, `os/shutil.replace` |
| `fmea_prediction_check.py` | no write site detected |
| `gate_column_check.py` | `os/shutil.replace` |
| `git_discovery_anchoring_check.py` | `<computed path>`, `os/shutil.replace` |
| `git_push_master_guard.py` | `os/shutil.replace` |
| `hedge_carry_check.py` | `os/shutil.replace` |
| `hover_auditor_scope_gate.py` | `<computed path>`, `os/shutil.remove`, `os/shutil.replace` |
| `hover_eqa_escalation.py` | no write site detected |
| `hover_process_pass_freshness.py` | no write site detected |
| `hover_self_health_shim.py` | `os/shutil.replace` |
| `hover_separation_ci.py` | `os/shutil.replace` |
| `html_script_check.py` | no write site detected |
| `idempotence_double_run.py` | `<computed path>`, `os/shutil.makedirs`, `os/shutil.replace`, `os/shutil.rmtree` |
| `idempotency_check.py` | `os/shutil.replace` |
| `independence_check.py` | no write site detected |
| `index_duplicate_check.py` | no write site detected |
| `invisible_in_pattern_check.py` | `os/shutil.replace` |
| `jscomments.py` | `os/shutil.replace` |
| `key_collision_check.py` | no write site detected |
| `landing_verification.py` | `os/shutil.replace` |
| `leg_session_gate_live_probe.py` | no write site detected |
| `licence_recoverability_check.py` | no write site detected |
| `line_endings.py` | `<computed path>`, `os/shutil.remove`, `os/shutil.replace` |
| `live_probe_declaration_check.py` | `os/shutil.replace` |
| `load_compliance_seed.py` | no write site detected |
| `load_schema_snapshot.py` | `<computed path>`, `os/shutil.replace` |
| `local_only_collection_check.py` | no write site detected |
| `log_cluster.py` | `os/shutil.replace` |
| `master_plan.py` | `<computed path>`, `os/shutil.replace` |
| `mech_gate_live_probe.py` | `<computed path>`, `os/shutil.makedirs`, `os/shutil.replace` |
| `mech_panels_live_check.py` | no write site detected |
| `message_assertion_audit.py` | `<computed path>`, `os/shutil.replace`, `os/shutil.rmtree` |
| `missing_dom_target_check.py` | no write site detected |
| `negated_status_assertion_scan.py` | `os/shutil.replace` |
| `new_checker.py` | `<computed path>` |
| `npm_audit_check.py` | no write site detected |
| `numeric_default_coalesce_scan.py` | `os/shutil.replace` |
| `ooda_phases.py` | no write site detected |
| `optimistic_success_scan.py` | no write site detected |
| `orphan_register_check.py` | no write site detected |
| `outline.py` | `os/shutil.remove` |
| `ownership_evidence_drift.py` | no write site detected |
| `panel_depth.py` | `os/shutil.replace` |
| `panel_nesting_check.py` | no write site detected |
| `pinned_list_drift_check.py` | `os/shutil.replace` |
| `pra_event_tree.py` | no write site detected |
| `preauth_oracle_check.py` | `os/shutil.replace` |
| `purge_evidence_gate.py` | `<computed path>`, `os/shutil.makedirs`, `os/shutil.replace` |
| `purpose_expired_measure.py` | no write site detected |
| `redaction_check.py` | no write site detected |
| `register_freshness_propose.py` | `<computed path>`, `os/shutil.replace`, `os/shutil.rmtree` |
| `reliability_growth.py` | no write site detected |
| `removal_path_check.py` | no write site detected |
| `resource_reachability_check.py` | no write site detected |
| `retry_backoff_check.py` | `os/shutil.replace` |
| `retry_policy_audit.py` | no write site detected |
| `review_ledger_reseat.py` | `<computed path>`, `json.dump -> a file object`, `os/shutil.replace` |
| `rewrite_convergence_map.py` | `os/shutil.replace` |
| `risk_event_tree.py` | no write site detected |
| `rotation_blast_radius.py` | no write site detected |
| `run_semgrep.py` | no write site detected |
| `sabotage.py` | `<computed path>`, `os/shutil.remove`, `os/shutil.replace` |
| `sairn_ai_fact_scan.py` | no write site detected |
| `sairn_app_map_check.py` | no write site detected |
| `sairn_claim_doc_freshness.py` | no write site detected |
| `sairn_claim_hook.py` | no write site detected |
| `sairn_dead_button_audit.py` | no write site detected |
| `sairn_http.py` | no write site detected |
| `sairn_load_state_check.py` | no write site detected |
| `sairn_self_state.py` | `<computed path>`, `json.dump -> a file object`, `os/shutil.makedirs`, `os/shutil.replace`, +1 more |
| `sairn_session_identity.py` | `<computed path>`, `os/shutil.makedirs`, `os/shutil.rmtree` |
| `sairn_source_fetch.py` | `<computed path>`, `json.dump -> a file object`, `os/shutil.makedirs` |
| `sairn_stale_snapshot_scan.py` | no write site detected |
| `sairn_strict_args_check.py` | no write site detected |
| `sairnlaw_citation_audit.py` | `os/shutil.replace` |
| `sc_tier_a_write_gate_live_probe.py` | no write site detected |
| `schema_snapshot_freshness.py` | `os/shutil.replace` |
| `scp_session_gate_live_probe.py` | no write site detected |
| `second_pass_coverage_scan.py` | `<computed path>`, `os/shutil.replace` |
| `secrets_inventory.py` | `<computed path>`, `os/shutil.replace` |
| `session_lock_check.py` | `<computed path>`, `json.dump -> a file object`, `os/shutil.makedirs`, `os/shutil.remove`, +1 more |
| `session_recheck_coverage.py` | `<computed path>`, `os/shutil.replace` |
| `shape_antipattern_check.py` | `os/shutil.replace` |
| `shape_search.py` | no write site detected |
| `soup_register_check.py` | no write site detected |
| `source_manifest.py` | `<computed path>` |
| `sql_column_exists_check.py` | no write site detected |
| `staged_conflict_marker_check.py` | no write site detected |
| `staged_parse_check.py` | no write site detected |
| `staging_discipline_scan.py` | no write site detected |
| `stale_row_sweep.py` | no write site detected |
| `stonedesk_storefront_live_check.py` | no write site detected |
| `stored_data_criticality_check.py` | no write site detected |
| `subprocess_decode_check.py` | `<computed path>`, `os/shutil.replace` |
| `suite_control_coverage.py` | `<computed path>` |
| `suite_control_triage.py` | no write site detected |
| `temporary_state_check.py` | `os/shutil.replace` |
| `testability_criteria.py` | no write site detected |
| `testability_gate.py` | no write site detected |
| `three_way_match_check.py` | no write site detected |
| `tier_a_bypass_check.py` | `os/shutil.replace` |
| `tier_a_replaceability_check.py` | `os/shutil.replace` |
| `tier_sentence_gate.py` | no write site detected |
| `trend_alarm.py` | `<computed path>` |
| `truthy_sum_check.py` | `os/shutil.replace` |
| `va_rule_currency.py` | no write site detected |
| `vercel_config_check.py` | no write site detected |
| `verification_plan_staleness_check.py` | no write site detected |
| `verify_review_gates.py` | no write site detected |
| `waf_rule_check.py` | no write site detected |
| `weakness_combination.py` | `<computed path>`, `os/shutil.replace`, `os/shutil.rmtree` |
| `write_path_fault_scan.py` | `<computed path>`, `json.dump -> a file object` |

<!-- OWNERLESS-TABLE-END -->

---

## Item 8 — location inventory

**Eight directories under `~/Documents` hold a `.git`, DERIVED BY GLOBBING FOR
ONE rather than read from a list.** One of them is this clone, so there are
**seven siblings**, and the counts below are out of those seven.
`CLAUDE.md` once named four for weeks after a fifth existed and was pushing
commits; the correction it carries is in capitals — *count the directories*.

    C:\Users\marsh\Documents\SAIRN-cc        <- this clone
    C:\Users\marsh\Documents\SAIRN-cody
    C:\Users\marsh\Documents\SAIRN-fourth
    C:\Users\marsh\Documents\SAIRN-hank
    C:\Users\marsh\Documents\SAIRN-hover
    C:\Users\marsh\Documents\SAIRN-hover2
    C:\Users\marsh\Documents\SAIRN
    C:\Users\marsh\Documents\trading-bot     <- a .git, NOT a SAIRN clone

| what | where | owner | exists here | visible from a DIFFERENT clone folder |
|---|---|---|---|---|
| build-agent tools (`tools/`) | CLONE | mixed — 46 `OWNER_LINE`, 680 `NONE` | yes | **NO** — 6 of 7 siblings hold the same relative path as SEPARATE COPIES |
| tool tests / probes (`tests/`) | CLONE | mostly `NONE` (502) | yes | **NO** — 5 of 7, separate copies |
| git hooks (`.githooks/`) | CLONE | — | yes | **NO** — 5 of 7, separate copies |
| hook + permission wiring (`.claude/settings.json`) | CLONE | **cody** | yes | **NO** — 6 of 7, separate copies |
| skills, repo mirror (`.claude/skills/`) | CLONE | — | yes | **NO** — 6 of 7, separate copies |
| subagent definitions (`.claude/agents/`) | CLONE | — | yes | **NO** — 6 of 7, separate copies |
| claim records (`.claude/claims/`) | CLONE | one file per session | yes | **NO** — 5 of 7, separate copies |
| methodology (`docs/METHODOLOGY.md`) | CLONE | **fourth + hank** | yes | **NO** — 5 of 7, separate copies |
| cross-domain disciplines | CLONE | **fourth** | yes | **NO** — 5 of 7, separate copies |
| process rules (`docs/SAIRN-PROCESS-RULES.md`) | CLONE | — | yes | **NO** — 5 of 7, separate copies |
| project primer (`CLAUDE.md`) | CLONE | — | yes | **NO** — 6 of 7, separate copies |
| open-work index | CLONE | **hank** | yes | **NO** — 5 of 7, separate copies |
| tool owner map | CLONE | **cody** (`tool_owner_map.py`) | yes | **NO** — 5 of 7, separate copies |
| defect register | CLONE | shared, `union-by-identity` merge policy | yes | **NO** — 5 of 7, separate copies |
| bypass log | CLONE | written by the gate | yes | **NO** — 5 of 7, separate copies |
| skills, USER STORE (`~/.claude/skills/`) | **SHARED HOME** | — | yes | **YES** — one copy, every clone reads the same bytes |
| user-level settings (`~/.claude/settings.json`) | **SHARED HOME** | — | yes | **YES** — one copy |
| global primer (`~/.claude/CLAUDE.md`) | **SHARED HOME** | — | yes | **YES** — one copy |
| status registry (`~/SAIRN-SESSION-LOCKS/status`) | **SHARED HOME** | — | yes | **YES** — one copy |
| **gate exemption store** (`~/SAIRN-SESSION-LOCKS/gate-exemptions/`) | **SHARED HOME** | — | yes | **YES** — one copy |

Counts in this clone, read at `a9e9147b`:

    tools/*.py            305
    tests/**/*.py         403
    repo-mirrored skills   34
    USER-STORE skills      62

### The two rows that matter, and they are the shared-home ones

**`CLONE` means every clone has its OWN COPY.** A fix landing in one clone is
invisible to the others until it is pushed and pulled — which is PR §2.2 and is
exactly how this batch's claim was invisible to `sairn_claim.py list` while
being committed locally.

**`SHARED HOME` means there is one copy and no git between the writers.** The
`gate-exemptions` row is new in this table and is there because of this batch's
own finding (`f67cb7e5`): it holds **single-use tokens**, in a directory every
clone writes to, with nothing serialising the writers. That defect was two
*modes* of one process fighting over one token. Two *sessions* pushing at once
would be the same shape with a worse blast radius, and no arm covers it — the
probe drives both modes in one process and says so.

**28 of the 62 USER-STORE skills exist ONLY in the shared home folder** and are
not mirrored into the repo (34 mirrored, 62 in the store). That is a decision
for Michael, not a defect, and it is carried forward unchanged from
`docs/2026-10-07-cc-location-inventory.md`.
