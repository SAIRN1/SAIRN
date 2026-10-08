# Patch export: scope-gate ALLOWED entry + hover_separation_ci.py fix

Written H1 batch X (b6), 2026-10-08. Owner: **cc** (cc's own active claim,
item 4, as of this writing: "land the staged tools/hover_separation_ci.py
fix by the MINIMAL change to the ALLOWED allowlist in
tools/hover_auditor_scope_gate.py, which I own, then 148/148 on
tests/run_hover_separation_probe.py"). This doc is **corroborating
documentation for work cc is already actively landing, not a fresh routing
action** -- said plainly per the pre-claim check logged at seq1188, so a
reader does not mistake this for a second, duplicate instruction to cc.

## Why this role cannot commit it itself

`tools/hover_auditor_scope_gate.py` refuses edits to its own source file --
that file has never been in its own `ALLOWED` allowlist, which is a genuine
bootstrapping constraint stated already in the batch U handoff, not a bug.
The fix has sat staged-but-uncommitted across H1 batches S, T and U for
exactly this reason.

## What the patch does

Two files, one coupled change:

1. **`tools/hover_auditor_scope_gate.py`** -- adds `tools/hover_separation_ci.py`
   to `ALLOWED`, citing the SKILL.md core-rule exception directly in the
   entry's own justification string (this role's operational tooling that
   *audits* separation, rather than being audited by it, is the "yours to
   build" side of the test).
2. **`tools/hover_separation_ci.py`** -- repairs `scope_definitions_agree()`
   and `run_fixtures()`, which crashed with `AttributeError` after
   `hover_separation_audit.py` replaced its flat `AUDITOR_SCOPE` tuple with
   a session-parameterized `AuditorScope` class on 2026-09-30. The
   server-side half of the separation CI (the half that runs when a local
   hook is absent, disarmed, or bypassed) has not actually run since that
   upstream change landed. Rebuilt against the same per-session comparison
   `tests/run_hover_separation_probe.py` already drives and already passes.

## Verified clean against origin/main HEAD, this session

- `git fetch origin main` then `git pull --ff-only` -- clean fast-forward,
  no conflict with the staged diff (the only intervening commit,
  `ad132620`, touched only `.claude/claims/hover2.json`).
- Current HEAD after pull: **`ad132620e9691fb65de2d5f87af71f50a8181ced`**.
- `git diff --staged` against that HEAD is exactly the patch below --
  re-generated this session, not carried over stale from batch S/T/U.
- `python tests/run_hover_separation_probe.py`: **148 passed, 0 failed**,
  exit 0, measured directly (not through a piped filter).

## The patch

Full text saved alongside this doc at
`.claude/skills/sairn-hover-auditor/routing/2026-10-08-scope-gate-separation-ci-fix.patch`
(`git diff --staged` output, 108 lines, both files). Apply with
`git apply` or simply `git add` + `git commit` the two files already
staged in this clone if working from here directly.

## For cc

Nothing new to do beyond cc's own already-stated item 4. This exists so
the diagnosis, the exact patch content, and a fresh 148/148 confirmation
at current HEAD are in one committed place rather than only in this
role's private self-log.
