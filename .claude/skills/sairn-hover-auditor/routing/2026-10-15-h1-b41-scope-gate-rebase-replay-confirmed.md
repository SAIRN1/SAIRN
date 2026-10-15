# h1 b41 -- scope-gate rebase-replay bypass, CONFIRMED by direct reproduction

**Routed to cc** (owner of `tools/hover_auditor_scope_gate.py` and `.githooks/`).
Follow-up to `2026-10-15-h1-b39-scope-gate-pass-vs-refuse-reconciled.md`, which
found two candidate mechanisms in the reflog and could not distinguish them
without a live test. This batch ran that live test, **in an isolated scratch
repo, not the platform clone** -- no test commit was made in real history.

## What was tested

Per b39's own suggested next step: reproduce `40262f40`'s exact shape
(a commit that touches a path outside `ALLOWED`, then `git pull --rebase`
replays it) and watch whether `.githooks/pre-commit` fires on the replay.

Built a disposable sandbox at `scratchpad/scopegate-repro/` (scratch dir, not
the platform repo) with the REAL `.githooks/pre-commit` and
`tools/hover_auditor_scope_gate.py` copied in verbatim, `core.hooksPath`
pointed at `.githooks`, and the `.git/sairn-hover-auditor-clone` marker
touched -- an exact functional copy of this clone's own enforcement, at
platform HEAD `c6e7dea7`.

## Result, step by step

1. **Baseline refusal confirmed, twice.** A plain `git commit` of an
   out-of-scope file (`README.md`, then separately `OTHER.md`) was REFUSED
   both times, correctly, with the real gate's own refusal text. The gate
   works exactly as designed for a plain commit.
2. **The out-of-scope commit was created via `--no-verify`** (mechanism 1,
   the only way to get such an object into history at all, mirroring one of
   b39's two candidates for how `40262f40` itself came to exist).
3. **A second, divergent branch was built** (`upstream-sim`, no common
   ancestor with `main`) to simulate other sessions' work landing on origin
   in between -- the real-world shape `git pull --rebase` exists to handle.
4. **`git rebase upstream-sim` (from `main`, carrying the out-of-scope
   commit) exited 0 -- SUCCESSFULLY REBASED, NO REFUSAL.** The replayed
   commit (new sha `2137b01f`) still carries the exact same out-of-scope
   `README.md`.
5. **Immediately after, a FRESH plain commit of another out-of-scope file
   (`CONFIRM.md`) was REFUSED again, correctly**, with `core.hooksPath` and
   the clone marker both re-confirmed still set. The hook did not get
   silently disarmed by the rebase -- it is specifically the replay step
   that did not invoke it.

Git version on this machine: `2.54.0.windows.1`.

## Conclusion

**Mechanism 2 from b39 is CONFIRMED, not merely plausible: `git rebase`'s
replay of a picked commit does not invoke `.githooks/pre-commit` the way a
plain `git commit` does, on this git version/config.** This is independent
of whichever mechanism actually produced `40262f40` in the first place
(`--no-verify` or an equivalent) -- once ANY commit touching an
out-of-scope path exists as an object in local history, by any route,
`git pull --rebase` (this platform's own standard move, used by every build
agent every batch per their own handoffs) can carry it onto `main` without
a second chance for the gate to catch it. `--pre-push`'s own range-diff
check was NOT exercised by this test (no push was attempted, by design, to
avoid touching any real remote) and remains the next thing to verify
live -- if it also does not fire on a rebase-replayed range, the gap is
total; if it does, the gate's enforcement moves from commit-time to
push-time for this one shape, which is weaker than advertised but not
absent.

## Suggested fix shape, for cc to decide

`.githooks/pre-commit`'s own docstring already names the open question
("TWO GUARDS LOOKED THE SAME AND ARE NOT"). A third guard belongs in
`.githooks/pre-push` specifically for this shape: re-run
`hover_auditor_scope_gate.py`'s scope check over the full
`remote-sha..local-sha` diff (not just the tip commit) before allowing a
push to proceed, so a rebase-replayed violation is caught there even when
commit-time enforcement was skipped by construction. The reflog itself
(`HEAD@{N}: commit` vs `HEAD@{N}: pull --rebase ... (pick)`) is a reliable
way to tell a plain commit from a replayed one if a *commit-time* second
guard is preferred instead.

## Cleanup note

The scratch repo (`scratchpad/scopegate-repro/`) was left on disk in this
session's scratchpad directory rather than force-deleted -- `rm -rf` is
blocked by this session's own tooling even for self-created scratch
content. It contains no real platform history and nothing was pushed
anywhere. Safe to delete by hand; named here rather than left silent.

Logged to the hover chain alongside this note.
