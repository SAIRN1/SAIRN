# The 76 REAL suite failures, routed by owning app and agent — 2026-10-11 (cody, batch 27 b4)

**ROUTING TABLE ONLY. Nothing here is fixed, and nothing here is diagnosed.**
Batch 27 item 1 says commit the table and do not fix yet; this document holds
to that exactly. The "suite reason" column is the line the suite printed,
quoted, not interpreted.

## Where the 76 come from

`docs/2026-10-08-cody-suite-86-triage.tsv` — the `--pinned` suite run at
`aa2f014dd21b088711944b5675104471c43b0502`, 759 files, 671 ok, **86 FAIL**,
each one of the 86 then re-run **alone in a `git clone --local` at the same
commit** at a 420 s bound, with the verdict rule fixed before the run:

| verdict | count |
|---|---:|
| **REAL** (fails alone on a clean tree) | **76** |
| COULD-NOT-RUN (exit 2, or the bound) | 7 |
| ARTIFACT (passes alone) | 3 |

**The 76 are the REAL rows and only those.** The 7 COULD-NOT-RUN are not
routed here: a third state is not a failure, and routing one as if it were
would hand an owner a verdict that was never reached. They stay in the triage
document with their exit codes.

## The method is H1's, and the App column is derived

Taken from `.claude/skills/sairn-hover-auditor/routing/2026-10-08-routed-field-findings.md`
(H1 batch X item 4), which solved the same problem for 15 field findings and
reached this conclusion first: **this platform has no durable per-agent app
assignment**, so naming a build agent without evidence is a fabricated claim,
not a proposal. What *is* derivable is the app, and the app is the unit the
claim system already routes on.

Four rules, carried over whole:

1. **The app is DERIVED from the resource registry, never guessed from a name
   prefix.** H1 read it through `hover_cold_scan_pool.resource_app_map()`. This
   document reads `api/_resources/*.js` **directly**, through that package's own
   `index.js` in node — **398 resources across 18 declared app names, 17 of
   which own at least one resource.** A structurally different method reaching
   the same kind of answer is the independence rule (cross-domain discipline
   §6), and it keeps a build agent out of the auditor's clone entirely.
2. **An agent owner is named only on a declaration.** Two sources, both
   recorded per row:
   * `map` — a non-null `owner` in `docs/tool-owner-map.json`, **with its own
     `basis` printed**, because that file's `_basis_vocabulary` says plainly
     that `CLAIM_SUBJECT_ONLY` is *"derived and WEAKER than `LAST_CLAIM`: a
     subject is prose, not a declaration of scope."* Four of this table's
     owners rest on exactly that weaker basis and say so.
   * `claimFILES` — a session declared the path in a claim's `FILES:` list,
     read out of all 7 `.claude/claims/*.json` records **claim by claim**, not
     by one regex over the file: each session's record holds ~300 historical
     claims, and a blob regex finds one `FILES:` list and silently drops the
     rest. **746 distinct paths** carry a declaration. Active and historical
     are labelled separately — an expired claim is who last declared it, not
     who holds it.
3. **With no declaration, no agent is named.** The route is *"next claim on
   `<app>`"*, which is the only routing claim with evidence behind it.
4. **Where the derivation cannot resolve one app, it says so.** `PLATFORM` =
   the path names no app and the file references no app-prefixed resource.
   `MULTI` = it references several apps' resources, or its path names several.
   Neither is a guess dressed as an answer.

**Added here, not in H1's version: a confidence column on the app.** Reported
as its own number rather than folded into the label, so a single-mention
inference cannot read like a path-token certainty. `HIGH` = the path names the
app, or three-plus of that app's prefixed resources appear. `MODERATE` = two.
`LOW` = one. **5 of the 18 app-resolved rows are LOW and are marked LOW**;
anyone acting on those five should re-read the file before accepting the app.

### What the generic-name trap cost, stated rather than hidden

13 of the 398 registered resource names carry no app prefix and are ordinary
English words — `customers`, `employees`, `invoices`, `jobs`, `locations`,
`memory`, `profile`, `properties`, `quotes`, `remnants`, `schedule`, `slabs`,
`subcontractors`. The first pass of this derivation matched them on a word
boundary and **routed two platform probes to apps on the strength of a word in
their prose**: `tests/hover_separation_ci_probe.py` to sairngrounds because
"quotes" appears, `tests/run_dependency_graph_probe.py` to sairnscape because
"schedule" does. A second pass required a quoted string literal instead; that
left exactly one row, `tests/run_cron_liveness_probe.py`, which was then read
directly — its `'jobs'` (:63) and `'schedule'` (:201-212) are GitHub Actions
YAML keys. **Generic names are now not evidence at all, and the split between
prefixed and generic is taken from the registry (`"_" in name`), not from a
hand-written exclusion list.**

This is criteria tuned on real data rather than locked against a fixture
first, which the cross-domain disciplines warn about. It is recorded because
the tuning ran in the conservative direction — it *removes* app claims and
leaves the rows `PLATFORM` — and because the single row it finally rested on
was opened and read rather than counted.

## Agreement with Hank's independent derivation of the same question

`docs/2026-10-08-hank-suite-failure-owners.md` routed a **different** run
(batch 18's clean-worktree run: 101 failures, 89 REAL) by the same two
declaration-grade sources, three days earlier. **72 of these 76 suites also
appear in that table. 67 agree, 5 differ — 93%.** Reported as two numbers, and
the five are named rather than reconciled:

| suite | here | hank | why they differ |
|---|---|---|---|
| `tests/claims/run_push_verify_probe.py` | cody+cc (CONTESTED) | cc | The map's basis for this path is literally `CONTESTED`, `owner: cody`, `also_claimed_by: [cc]`. Both readings are half of one record; neither is wrong |
| `tests/sairnfreedom_server_backup.js` | cody | UNOWNED | `CLAIM_SUBJECT_ONLY` — the weaker basis |
| `tests/run_nhi_register_write_flag_probe.py` | cody | UNOWNED | `CLAIM_SUBJECT_ONLY` |
| `tests/run_rewrite_convergence_probe.py` | fourth | UNOWNED | `CLAIM_SUBJECT_ONLY` |
| `tests/schema_provisioning_probe.py` | cody | UNOWNED | `CLAIM_SUBJECT_ONLY` |

**All four non-contested differences are the same cause**: the owner map at
`criteria 2026-10-07.1` now carries a claim-subject-derived owner where Hank's
read found nothing, and that basis is the weak one. They are included **with the
basis printed on the row** rather than dropped, so a reader can discount them;
they are not presented as equal to a `FILES:` declaration.

### The owner map was 12 tracked files stale when this table was derived

Stated with its cause rather than quietly refreshed. The table was first derived
against the **committed** `docs/tool-owner-map.json` — `_meta.tools: 989`,
`owner_line: 55`. Adding this document's own tool forced a regeneration, and the
regenerated map is **`tools: 1001`, `owner_line: 67`** — 12 newly tracked files
and 12 more `# OWNER:` lines, of which **exactly one (`tools/route_suite_failures.py`)
is this batch's**. The other 11 landed from other sessions' commits without the
map being regenerated.

**The derivation was then re-run against the regenerated map and the TSV is
byte-identical** (`diff`, 0 lines), so none of the 12 is among the 76 and no
number in this document moved. That is the only reason the staleness is a note
here and not a correction: it was checked, not assumed.

The 4 suites in this table that are **not** in Hank's: `tests/sd_tax_money_coercion.js`,
`tests/run_defect_register_probe.py`, `tests/push_gate/check4_probe.py`,
`tests/push_gate/check7_probe.py`. Two runs of a moving suite are not the same
population, and the overlap is stated rather than assumed.

**A parser defect found and fixed inside this cross-check, worth the line:**
the first version read `### <owner> — N REAL` headings and never reset on the
level-2 heading that ends that region, so the last owner section stayed in
scope across Hank's CASCADE and TIMEOUT tables and reported
`tests/run_defect_register_probe.py` — a TIMEOUT row owned by cc — as
`cc+fourth+hank`. A parser reading past the close of its own structure, which
is the defect class CLAUDE.md names for `sed` ranges, in a different file
format.

## The split

| app (derived) | REAL failures | owner declared | UNOWNED |
|---|---:|---:|---:|
| **sairnfreedom** | 6 | 3 | 3 |
| **sairncare** | 4 | 0 | 4 |
| **stonedesk** | 3 | 2 | 1 |
| **sairnlegacy** | 2 | 0 | 2 |
| **sairnbiz** | 1 | 0 | 1 |
| **sairndental** | 1 | 0 | 1 |
| **sairnsenior** | 1 | 0 | 1 |
| **PLATFORM** (no app) | 47 | 16 | 31 |
| **MULTI** (several apps) | 11 | 6 | 5 |
| **total** | **76** | **27** | **49** |

| declared owner | count |
|---|---:|
| UNOWNED | 49 |
| **cody** | 14 |
| **fourth** | 6 |
| **cc** | 4 |
| **cc+fourth+hank** | 1 |
| **hank** | 1 |
| **cody+cc** (CONTESTED) | 1 |

**The headline is not the agent split, it is that 47 of 76 are not an app's
problem at all** — they are platform tooling: probes, gates, controls and
sweeps over the repo's own machinery. Routing them "by app" cannot work, and
that is a fact about the population rather than a shortfall of the method.
**49 of 76 have no declared owner.** `UNOWNED` is a gap in the record, not a
verdict that nobody wrote the file.

**The `mentioned in active-work` column is a weaker, separate signal and is
never promoted to an owner.** H1 used that grep as a *negative* check — zero
matches across all four `SAIRN-ACTIVE-WORK-*.md` meant nobody had picked a
finding up. Of the 49 UNOWNED rows here, **17 are mentioned somewhere in some
agent's active-work file and 32 are mentioned nowhere.** A path appearing
inside a 1 MB standing document is not a declaration of scope, so it sits in
its own column.

## How to re-derive this

`tools/route_suite_failures.py` (committed with this document), against
`docs/2026-10-08-cody-suite-86-triage.tsv`, `docs/tool-owner-map.json`,
`api/_resources/*.js` and `.claude/claims/*.json`. It is **read-only** against
the repo and writes only to the output paths it is given. The numbers in this
document came out of it; none were typed from memory.

---

## The table

Grouped by derived app, app-resolved groups first, then `MULTI`, then
`PLATFORM`. `rc` is the exit code from the isolated run.

### sairnbiz -- 1 of 76

| suite | kind | rc | app basis / confidence | owner (declared) | owner basis | mentioned in active-work | route to |
|---|---|---:|---|---|---|---|---|
| `tests/local_only_self_evidence_probe.py` | py | 1 | prefixed-resource-ref / HIGH | UNOWNED | no map entry and no claim FILES declaration | cc | next claim on sairnbiz |

### sairncare -- 4 of 76

| suite | kind | rc | app basis / confidence | owner (declared) | owner basis | mentioned in active-work | route to |
|---|---|---:|---|---|---|---|---|
| `api/sd-data-family-contacts.test.js` | node | 1 | prefixed-resource-ref / MODERATE | UNOWNED | no map entry and no claim FILES declaration | none | next claim on sairncare |
| `tests/run_alf_read_order_sabotage_probe.py` | py | 1 | prefixed-resource-ref / HIGH | UNOWNED | no map entry and no claim FILES declaration | hank | next claim on sairncare |
| `tests/sairncare/test-compliance-rules.js` | node | 1 | path-token / HIGH | UNOWNED | no map entry and no claim FILES declaration | none | next claim on sairncare |
| `tests/sairncare/test-op-audit.js` | node | 1 | path-token / HIGH | UNOWNED | no map entry and no claim FILES declaration | none | next claim on sairncare |

### sairndental -- 1 of 76

| suite | kind | rc | app basis / confidence | owner (declared) | owner basis | mentioned in active-work | route to |
|---|---|---:|---|---|---|---|---|
| `tests/sql_preflight/run_probe.py` | py | 1 | prefixed-resource-ref / LOW -- one resource mention only | UNOWNED | no map entry and no claim FILES declaration | cc+cody | next claim on sairndental |

### sairnfreedom -- 6 of 76

| suite | kind | rc | app basis / confidence | owner (declared) | owner basis | mentioned in active-work | route to |
|---|---|---:|---|---|---|---|---|
| `api/sf-auth.test.js` | node | 1 | prefixed-resource-ref / HIGH | UNOWNED | no map entry and no claim FILES declaration | none | next claim on sairnfreedom |
| `tests/sairnfreedom_auth_review_probe.js` | node | 1 | path-token / HIGH | UNOWNED | no map entry and no claim FILES declaration | none | next claim on sairnfreedom |
| `tests/sairnfreedom_fault_probe.py` | py | 1 | path-token / HIGH | **cody** | map(LAST_CLAIM); claimFILES(historical cody) | fourth | cody |
| `tests/sairnfreedom_segregation_of_duties.js` | node | 1 | path-token / HIGH | UNOWNED | no map entry and no claim FILES declaration | none | next claim on sairnfreedom |
| `tests/sairnfreedom_server_backup.js` | node | 1 | path-token / HIGH | **cody** | map(CLAIM_SUBJECT_ONLY) | fourth | cody |
| `tests/schema_provisioning_probe.py` | py | 1 | prefixed-resource-ref / LOW -- one resource mention only | **cody** | map(CLAIM_SUBJECT_ONLY) | cc | cody |

### sairnlegacy -- 2 of 76

| suite | kind | rc | app basis / confidence | owner (declared) | owner basis | mentioned in active-work | route to |
|---|---|---:|---|---|---|---|---|
| `tests/sairnlegacy_fault_probe.py` | py | 1 | path-token / HIGH | UNOWNED | no map entry and no claim FILES declaration | cody | next claim on sairnlegacy |
| `tests/sairnlegacy_reservation_lock.js` | node | 1 | path-token / HIGH | UNOWNED | no map entry and no claim FILES declaration | none | next claim on sairnlegacy |

### sairnsenior -- 1 of 76

| suite | kind | rc | app basis / confidence | owner (declared) | owner basis | mentioned in active-work | route to |
|---|---|---:|---|---|---|---|---|
| `tests/suite_control_backfill_probe.py` | py | 1 | prefixed-resource-ref / MODERATE | UNOWNED | no map entry and no claim FILES declaration | cc | next claim on sairnsenior |

### stonedesk -- 3 of 76

| suite | kind | rc | app basis / confidence | owner (declared) | owner basis | mentioned in active-work | route to |
|---|---|---:|---|---|---|---|---|
| `api/sd-data-customer-soft-delete.test.js` | node | 1 | prefixed-resource-ref / LOW -- one resource mention only | UNOWNED | no map entry and no claim FILES declaration | none | next claim on stonedesk |
| `tests/run_citation_anchor_hop_sabotage.py` | py | 1 | prefixed-resource-ref / LOW -- one resource mention only | **cody** | map(OWNER_LINE) | none | cody |
| `tests/sd_tax_money_coercion.js` | node | 1 | prefixed-resource-ref / LOW -- one resource mention only | **cody** | map(LAST_CLAIM); claimFILES(historical cody) | none | cody |

### MULTI -- 11 of 76

| suite | kind | rc | app basis / confidence | owner (declared) | owner basis | mentioned in active-work | route to |
|---|---|---:|---|---|---|---|---|
| `api/sd-data-cross-tenant-dispatchers.test.js` | node | 1 | prefixed-resource-ref / n/a | **cc+fourth+hank** | claimFILES(historical cc+fourth+hank) | none | cc+fourth+hank |
| `api/sd-data-scp-licence-only.test.js` | node | 1 | prefixed-resource-ref / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim naming this path |
| `tests/app_session_isolation.js` | node | 1 | prefixed-resource-ref / n/a | **cody** | map(LAST_CLAIM); claimFILES(historical cody) | cc+cody+fourth+hank | cody |
| `tests/faults/sd_write_faults.js` | node | 1 | prefixed-resource-ref / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim naming this path |
| `tests/local_only_shape_probe.py` | py | 1 | prefixed-resource-ref / n/a | UNOWNED | no map entry and no claim FILES declaration | cc | next claim naming this path |
| `tests/run_export_coverage_probe.py` | py | 1 | prefixed-resource-ref / n/a | **cc** | map(LAST_CLAIM); claimFILES(historical cc) | cc | cc |
| `tests/run_removal_path_probe.py` | py | 1 | prefixed-resource-ref / n/a | **fourth** | map(LAST_CLAIM); claimFILES(historical fourth) | hank | fourth |
| `tests/run_two_axis_tier_parser_probe.py` | py | 1 | prefixed-resource-ref / n/a | **cody** | map(LAST_CLAIM); claimFILES(historical cody) | none | cody |
| `tests/run_write_path_scan_probe.py` | py | 1 | prefixed-resource-ref / n/a | **fourth** | map(LAST_CLAIM); claimFILES(historical fourth) | cody | fourth |
| `tests/scp_quotes_review_probe.js` | node | 1 | prefixed-resource-ref / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim naming this path |
| `tests/write_readback_shape_probe.py` | py | 1 | prefixed-resource-ref / n/a | UNOWNED | no map entry and no claim FILES declaration | cc+fourth | next claim naming this path |

### PLATFORM -- 47 of 76

| suite | kind | rc | app basis / confidence | owner (declared) | owner basis | mentioned in active-work | route to |
|---|---|---:|---|---|---|---|---|
| `tests/claims/run_push_verify_probe.py` | py | 1 | no-app-evidence / n/a | **cody+cc (CONTESTED)** | map(CONTESTED, also cc); claimFILES(historical cc+cody) | fourth | cody+cc (CONTESTED) |
| `tests/claims/run_registry_claim_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/defect_register_capa_control.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | cody | next claim on platform tooling |
| `tests/faults/transport_timeout_sweep.js` | node | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | cody+fourth | next claim on platform tooling |
| `tests/hover_quotable_session_vocab_check.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/hover_separation_ci_probe.py` | py | 1 | no-app-evidence / n/a | **cody** | map(LAST_CLAIM); claimFILES(historical cody) | cc | cody |
| `tests/install_git_hooks_check_probe.py` | py | 1 | no-app-evidence / n/a | **cc** | map(LAST_CLAIM); claimFILES(historical cc) | none | cc |
| `tests/law_reconcile_role_vocab_control.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/push_gate/check4_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | cc+fourth+hank | next claim on platform tooling |
| `tests/push_gate/check7_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | fourth | next claim on platform tooling |
| `tests/push_gate/preauth_exemption_anchor_probe.py` | py | 1 | no-app-evidence / n/a | **fourth** | map(LAST_CLAIM); claimFILES(historical fourth) | hank | fourth |
| `tests/rebase_resolve_merge_control.py` | py | 1 | no-app-evidence / n/a | **cody** | map(LAST_CLAIM); claimFILES(historical cody) | none | cody |
| `tests/run_adversarial_prompt_corpus_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_all_tests_floor_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | fourth | next claim on platform tooling |
| `tests/run_all_tests_pinned_probe.py` | py | 1 | no-app-evidence / n/a | **cody** | map(LAST_CLAIM); claimFILES(historical cody) | none | cody |
| `tests/run_baseline_readiness_probe.py` | py | 1 | no-app-evidence / n/a | **cc** | map(LAST_CLAIM); claimFILES(historical cc) | none | cc |
| `tests/run_blob_coverage_scope_sabotage.py` | py | 1 | no-app-evidence / n/a | **cody** | map(OWNER_LINE); claimFILES(historical cody) | cody | cody |
| `tests/run_checker_control_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | fourth | next claim on platform tooling |
| `tests/run_completeness_probe.py` | py | 1 | no-app-evidence / n/a | **fourth** | map(LAST_CLAIM); claimFILES(historical fourth) | none | fourth |
| `tests/run_concurrency_retry_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_condition_coverage_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_copy_exactly_gate_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_cron_liveness_probe.py` | py | 1 | generic-only / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_defect_dispersion_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_defect_register_probe.py` | py | 1 | no-app-evidence / n/a | **cc** | map(LAST_CLAIM); claimFILES(historical cc) | fourth | cc |
| `tests/run_dependency_graph_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_dispatch_state_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_eaten_substitution_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_financial_invariant_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_first_article_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_ghost_field_read_probe.py` | py | 1 | no-app-evidence / n/a | **hank** | map(LAST_CLAIM); claimFILES(historical hank) | none | hank |
| `tests/run_githook_install_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_graduated_exemption_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_harness_stage_diagnosis_probe.py` | py | 1 | no-app-evidence / n/a | **cody** | map(LAST_CLAIM); claimFILES(historical cody) | none | cody |
| `tests/run_index_duplicate_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_nhi_clone_enumeration_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_nhi_register_write_flag_probe.py` | py | 1 | no-app-evidence / n/a | **cody** | map(CLAIM_SUBJECT_ONLY) | none | cody |
| `tests/run_rebase_resolve_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | fourth | next claim on platform tooling |
| `tests/run_rewrite_convergence_probe.py` | py | 1 | no-app-evidence / n/a | **fourth** | map(CLAIM_SUBJECT_ONLY) | none | fourth |
| `tests/run_role_gate_negative_coverage_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_secrets_inventory_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/run_selftest_sweep_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | cc | next claim on platform tooling |
| `tests/run_stored_data_criticality_probe.py` | py | 1 | no-app-evidence / n/a | **cody** | map(LAST_CLAIM); claimFILES(historical cody) | none | cody |
| `tests/run_subprocess_decode_probe.py` | py | 1 | no-app-evidence / n/a | **fourth** | map(LAST_CLAIM); claimFILES(historical fourth) | none | fourth |
| `tests/run_tool_selftest_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | none | next claim on platform tooling |
| `tests/seam_check/run_or_default_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | hank | next claim on platform tooling |
| `tests/seam_check/run_ref_probe.py` | py | 1 | no-app-evidence / n/a | UNOWNED | no map entry and no claim FILES declaration | cc | next claim on platform tooling |

