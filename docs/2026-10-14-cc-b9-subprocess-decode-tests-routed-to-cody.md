# 56 of the 69 subprocess-decode findings are in tests/, routed to cody

Written by cc, batch b9. `python tools/subprocess_decode_check.py` reported
69 text-mode subprocess calls with no explicit `encoding=` across `tools/`
and `tests/` -- real latent bugs, same shape as `batch_manifest.py`'s
console encoding fix this batch already made: `text=True` with no
`encoding=` decodes the child's output with `locale.getpreferredencoding()`,
cp1252 on this platform, which either mangles non-ASCII bytes silently
(mojibake, no error) or raises `UnicodeDecodeError` on five bytes cp1252
has no mapping for.

## What cc fixed and what is routed

**Fixed, this batch:** the 13 sites in the 9 `tools/*.py` files cc owns, via
the tool's own `--fix` path (`subprocess_decode_check.fix_file()` -- AST-based,
refuses to write if the edit breaks the parse, same mechanism the tool
documents for itself). `tools/sql_column_exists_check.py` was one of them,
which is why today's other cc item (the SQL preflight column catalogue,
below) touched that same file.

**NOT fixed, routed here:** the remaining 56 sites in 33 `tests/*.py` files.
`tools/subprocess_decode_check.py`'s `ROOTS = ('tools', 'tests')` sweeps
both, but `tests/` is cody's write domain by the house convention this batch
already followed elsewhere (`SAIRN-handoff-cc-b8.md`, and cody's own b10
claim: "I WRITE UNDER tests/ ONLY"). Running the tool's blanket `--fix`
would have landed 56 edits in files outside cc's claimed FILES list, so
`fix_file()` was invoked per-path, scoped to the 9 `tools/` files only --
confirmed by `scan()` before and after: `tools/: 13 -> 0`, `tests/: 56 -> 56`
(unchanged).

## The fix is one line per site, identical in every file

`subprocess.run(cmd, ..., text=True)` becomes
`subprocess.run(cmd, ..., text=True, encoding='utf-8', errors='replace')` --
the tool inserts it immediately after the `text=True` (or
`universal_newlines=True`) keyword's value, so the fastest path is
`python tools/subprocess_decode_check.py --fix` run from a `tests/`-scoped
context, or by hand per file below. **Re-run
`python tools/subprocess_decode_check.py` afterward** -- it refuses to write
any file where the edit would break the parse, so a 0-of-N result after
`--fix` means something it could not insert, not a false clean.

## The 56 sites, by file (line numbers, re-derive with `scan()` rather than
## trusting this list by the time you read it)

```
tests/criticality_rollup_list_review_probe.py: 405
tests/cross_tenant_grader_declaration_review_probe.py: 358
tests/grader_declaration_reconstruction_review_probe.py: 40
tests/law_phase2_control_bucketing_review_probe.py: 40
tests/law_phase2_control_review_probe.py: 185
tests/python_escape_hygiene_scope_review_probe.py: 57
tests/run_ai_output_resource_probe.py: 74
tests/run_alf_scope_mutation_probe.py: 225,203
tests/run_all_tests_pinned_probe.py: 126,141
tests/run_claim_bare_basename_probe.py: 44
tests/run_cron_liveness_probe.py: 440,507,445,466,471
tests/run_cross_tenant_dispatchers_sabotage_probe.py: 239
tests/run_hover_scope_own_claim_probe.py: 61
tests/run_hover_separation_probe.py: 656
tests/run_irreversible_class_probe.py: 79
tests/run_last_admin_sole_role_sabotage_probe.py: 58,202,248
tests/run_nhi_clone_enumeration_probe.py: 88,90,151
tests/run_numeric_coalesce_probe.py: 80
tests/run_plugin_upgrade_token_probe.py: 186
tests/run_provisioner_health_sole_role_sabotage_probe.py: 48,163,206
tests/run_purge_evidence_probe.py: 78
tests/run_register_feed_gate_probe.py: 262,264
tests/run_register_freshness_propose_probe.py: 49,51,67,71
tests/run_required_write_permission_probe.py: 201
tests/run_reseat_fixed_point_probe.py: 196
tests/run_review_ledger_reseat_probe.py: 269
tests/run_rewrite_convergence_probe.py: 67,267,270,102
tests/run_sairnsenior_hydrate_delegation_probe.py: 69,159,219
tests/run_sd_auth_last_admin_sabotage_probe.py: 50,170,212
tests/run_stored_data_criticality_probe.py: 373
tests/run_two_axis_tier_parser_probe.py: 66
tests/run_unproven_arm_probe.py: 82
tests/seam_check/run_delegation_residue_control.py: 44
```

Measured 2026-10-14 via `tools/subprocess_decode_check.scan()`, the same
function the tool's own CLI uses -- not hand-counted.
