# SAIRN handoff — cody b45 (2026-10-21)

Three items, all done. Nothing is half-finished.

## State
- Landed on origin/main, no force: `5cbb4bbf7` (CHECK 5e), `e06b3c729`
  (path-manifest override), with the gate's scrutiny rows in `41d54371d`.
- No app code, no SQL, no live writes. Nothing is deployed, so there is no live-verify.
- The first push was **refused by path-scope**: `tools/` is cc's. I declared
  the two files in `assigned_overrides.cody`, which replaces the b37 list, in the house
  pattern: a `_why_cody_b45_REPLACES_b37` key, no prefix. Then it landed on attempt 1.

## Item 1: blocking. CHECK 5e in tools/sairn_push_gate_hook.py
**Concept:** an anchor goes bad only when its probe or its subject changes. So
a finding is denied only for the push that touches one of those two files.
Questions answered before wiring (discipline 39):
- **Where can it run?** Everywhere. Both tools use ast and string counts, with no
  node and no network. They take about 10s together (7.2s + 2.7s, measured).
- **What debt does it land on?** Zero. Both tools exit 0 at HEAD.

Behaviour:
- Both tools run with `--json` on every non-empty push.
- A finding whose probe or subject is in the outgoing files is **denied**, with the
  probe, the subject, the count and the arm named.
- A finding on untouched files is **printed and not denied** ("already on the
  branch, still owed"). One session's debt never blocks another session's push.
- A missing tool, a crash, no parseable JSON, or a non-zero exit with no finding named
  is **denied as COULD NOT RUN** (PR 1.11).
- Skippable as `probe-anchors`, a new id in `tools/gate_skip.py` GATES.
  `--gates` reports it WIRED. The skip list is now 12.

## Item 2: no false blocks platform-wide
- Both tools exit 0 in all four build clones: cody `d97190a00`, hank `c0ab49205`,
  cc `a4d79034`, fourth `5af65a854`. So CHECK 5e has nothing to deny in any of them.
  The hover clones were not touched (boundary).
- `--preflight` on the real clone: exit 0. Hook `--selftest` 56/56;
  gate_skip `--fixtures` 14/14.
- **Ablation through the real `--pre-push` hook**, in an isolated worktree (now removed):
  - A, comment-only html change: no 5e line.
  - B, sdnData's anchor duplicated into sairnlaw.html: **denied** by both tools,
    `ANCHOR-2` and `AMBIGUOUS (count 2)`, naming the law probe.
  - C, the same duplicate already in the base plus an unrelated docs push: **note only**.
  - D, `probe_anchor_freshness.py` absent: **denied** "not in this clone".
  Every arm also showed `path-scope COULD NOT RUN`. That is the worktree's identity,
  not 5e, and the same in all four.

## Known limits (stated, not fixed)
- The tools read the WORKING TREE. A dirty tree is checked, not the pushed tip.
  CHECK 5b has the same limit.
- `mutation_anchor_check.py` also exits 1 for an in-place probe with no
  `__main__` guard, and its `--json` does not list that case. On its own it is
  denied as unattributable. Alongside a named finding it goes unnamed.
- Uniqueness cannot see an anchor that is unique but sits on the wrong code (PR 1.3).
- Every push now costs about 10s more.

## Open
- cc owns `tools/`. cc should review CHECK 5e. It is flagged in the gate's own
  scrutiny rows as a self-checking change.
- Carried: hank F2/F3 owner write path; cc Tier A b31–b37; fourth defects 7/8.
