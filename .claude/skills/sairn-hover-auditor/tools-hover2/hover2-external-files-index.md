# hover2's external-file index

Committed so a future session (or `hover2_external_file_check.py`, batch Q
item 4) can tell "known, deliberately external" apart from "unindexed" without
re-deriving the whole inventory by hand. **Format:** one row per file or
glob, the declared directory it lives under, and why it is not (or not yet)
git-tracked. Built from a real, fresh listing taken 2026-10-08 (batch Q item
3), not from memory of an earlier sweep.

## Declared external directories

1. `~/.claude/projects/C--Users-marsh-Documents-SAIRN-hover2/hover-audit-log/`
   — this role's own operational tooling and self-log. Outside every git
   clone **by design** (see `hover_log.py`'s own docstring and this role's
   memory note `hover-self-log-location`).
2. `~/.claude/projects/C--Users-marsh-Documents-SAIRN-hover2/memory/` —
   Claude's own auto-memory system. Separate purpose, separate owner
   (the harness, not this role), not re-indexed here beyond naming the
   directory as known-and-exempt.
3. The session scratchpad (`AppData/Local/Temp/claude/.../scratchpad/`) —
   per-session temp staging, blanket-exempt (see below), never individually
   indexed — it does not outlive the session it was created in.

## Directory 1 — `hover-audit-log/` (full listing, 2026-10-08)

**Tools (committed-and-mirrored here, also git-tracked under
`tools-hover2/` — EXTERNAL-ONLY IS NOT THE CLAIM for these; they are
INTENTIONALLY DUPLICATED, the clone copy is the one that matters for
cross-session visibility, this copy is this role's own working copy):**
`claim_collision_scan.py`, `defect_density_weighting.py`,
`dependency_health_check.py`, `hover2_claim_reexecute.py`,
`hover2_code_normalize.py` (**committed THIS item, batch Q #3 — see below**),
`hover2_hardfail_score.py`, `hover2_log_mirror.py`, `hover2_timestamp.py`,
`hover_citation_linter.py`, `hover_cold_scan_pool.py`,
`hover_coverage_ledger.py`, `hover_duplicate_finding_check.py`,
`hover_editor_review.py`, `hover_log.py`, `hover_log_rotation_control.py`,
`hover_nongit_integrity_check.py`, `hover_predictive_drift_check.py`,
`hover_register_key_sweep.py`, `hover_self_health.py`,
`hover_self_health_hook.py`, `hover_tier0_exec.py`, `hover_tier1_live.py`,
`hover_tip_beacon.py`, `hover_tool_index.py`,
`hover_validation_freshness_check.py`, `presync_tier_a_dryrun.py`,
`routing_field_shape_audit.py`, `sabotage_claim_verify.py`,
`sabotage_closed_system_check.py`, `scope_narrowing_check.py`,
`stale_basis_check.py`, `tool_provenance_status.py`,
`undirected_sweep_freshness.py`.

**Standing docs — correctly EXTERNAL-ONLY, no git copy exists or should:**
`handoff-h2-*.md` (every dated handoff — handoffs live in the log repo per
established convention, never the platform clone), `methodology-h2.md`,
`hover2_coverage_ledger_own.md`, `hover2_unverified_ledger.md`,
`h1-h2-disagreement-protocol.md`, `TIP-BEACON.md`.

**Data/state files — correctly EXTERNAL-ONLY, generated or appended by the
tools above, not source:** `hover-audit-log.jsonl` (the chain itself),
`h1-h2-disagreements.jsonl`, `hover_self_health_fires.jsonl`,
`nongit_integrity_baseline.json`, `predictive-drift-state.json`,
`tool_provenance_validations.jsonl`, `chain-tip-timestamp.tsr`,
`chain-tip-timestamp.message.txt`.

**Credential/mirror-plumbing — MUST NEVER BE COMMITTED, contains or
references actual push credentials:** `.mirror-token`,
`.mirror2-token-meta.json`, `.mirror2-anchor-outbox.jsonl`,
`.mirror2-askpass-empty.py`, `.mirror2-askpass-empty.bat`,
`.mirror2-askpass-real.py`, `.mirror2-askpass-real.bat`, `.gitignore` (the
log repo's own, correctly keeping the above out of ITS git history too).

## Directory 2 — `memory/`

`MEMORY.md` (index) + 5 memory files, Claude's own system, not re-indexed
item-by-item here — see directory note above.

## Directory 3 — scratchpad (blanket entry, not itemized)

Per-session `--summary-file` staging content for `hover_log.py --append`
calls, and report-body drafts before copying to the final destination.
**Never meant to be anything but scratch** — it is cleared with the
session and re-created fresh next time. One exception noted and resolved
this item: `tool_parity_check.py` (batch P item 8's one-off extraction
script) was a real, reusable piece of logic left in scratchpad — its
functionality was already properly rebuilt into the COMMITTED
`citation_resolve_check.py` (`--recheck` mode) the very next item (batch P
item 9), so the scratchpad original is superseded and correctly left
uncommitted, not a gap.

## This item's own action: `hover2_code_normalize.py` committed

Built at seq626 and cited there as "built... in this role's own tooling
directory" — ambiguous between this directory and the git clone's
`tools-hover2/`, and it only ever existed here. **Committed this item**
(batch Q #3) to `.claude/skills/sairn-hover-auditor/tools-hover2/` after a
fresh selftest (9/9 pass) and syntax check, both clean. The seq626 citation
itself is NOT edited (append-only log) — a correcting entry is filed
separately, citing seq626 and this commit, per the same convention used
for every other citation correction in this log.
