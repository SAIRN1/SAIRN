# Pending patches to audit tooling outside this skill's own directory (b85, 2026-10-22)

Michael ruled in b85 that #1705 and #1698 are audit tooling and are this role's to fix. They live outside the skill directory, so the scope gate (`tools/hover_auditor_scope_gate.py`, `ALLOWED`) refuses a commit of them from the hover clone, and `ALLOWED` is in a file this role may not edit for itself. The fixes are therefore built and tested here as patches against HEAD. **Nothing below has been applied to the real files.**

| patch | applies to | what | proof |
|---|---|---|---|
| `b85-1705-scope-gate-merge-base.patch` | `tools/hover_auditor_scope_gate.py` | `changed_outgoing()` diffs from the merge-base of the remote tip and the pushed tip, not the two trees; no merge-base is COULD-NOT-READ; 4 new in-file selftest arms on real clones of a real bare origin | on the unfixed gate the new arms fail 3 of 4 (12/15 pass; it blames the other session's `docs/BYPASS-LOG.jsonl` on the pusher exactly as in the live refusal); fixed 15/15 |
| `b85-1698-routing-gap-tool.patch` | `tools/hover_routing_gap_check.py` | a log with findings and no `routable` key anywhere is COULD-NOT-READ (exit 2); an undatable ts counts as past the age limb and is labelled AGE UNKNOWN; an unparseable `--now` is COULD-NOT-READ | see the probe patch |
| `b85-1698-routing-gap-probe.patch` | `tests/run_hover_routing_gap_probe.py` | PART 3b (the two vacuous states plus controls) and one end-to-end arm through `main()` | probe on the unfixed tool: 31 passed, 4 failed (the named defects); on the fixed tool 35/0; the unmodified probe passes 27/0 on both layouts |

## Order, and why

1. `SKILL.md` carries the quotable sentences (done, b85): the core-rule paragraph names the triad `tools/hover_auditor_scope_gate.py`, `tools/hover_separation_audit.py`, `tools/hover_separation_ci.py` as audit-side, and the "Where findings go" section now names `tools/hover_routing_gap_check.py` and `tests/run_hover_routing_gap_probe.py`.
2. **A build agent adds the `ALLOWED` entries** for exactly: `tools/hover_auditor_scope_gate.py`, `tools/hover_routing_gap_check.py`, `tests/run_hover_routing_gap_probe.py` (the SEPARATION_CI precedent of 2026-10-08, and cc b48 for #1640). The audit copy `tools/hover_separation_audit.py` mirrors the allowlist and must move in the same change, as cc b48 did. This role does not make that edit and does not bypass the gate.
3. This role then applies the patches (`git apply`), runs the proofs above, and commits.

## Check before applying

`git apply --check <patch>` passed against HEAD `d790e95d2` plus the b85 working tree. Re-run it first: both files are edited by others.
