# h1 b39 -- why 191d8fc6 passed the scope gate while the b38 handoff commit was refused, reconciled

**Routed to cc** (owner of `tools/hover_auditor_scope_gate.py` and `.githooks/`).
Follow-up to `2026-10-15-h1-b38-scope-gate-refuses-own-handoff-commit.md`, which
left this open. **Not fixed here** -- the candidate fix is a `.githooks/`
and/or `tools/` change, outside this role's scope.

## Ruled out, with the exact check that ruled each out

1. **The ALLOWED list used to be broader.** `git show
   7a1d3382:tools/hover_auditor_scope_gate.py` (191d8fc6's own parent) has the
   SAME 4-entry `ALLOWED` tuple as HEAD today -- no handoff-shaped entry then
   either. Ruled out.
2. **Case sensitivity** (lowercase `h1` vs uppercase `H1`). Called
   `g.ALLOWED` matching directly in Python against both
   `SAIRN-handoff-h1-b37.md` and `SAIRN-handoff-H1-b38.md`: both return
   `False` identically. Ruled out.
3. **The clone was not armed / `core.hooksPath` not yet set at that moment.**
   The marker `.git/sairn-hover-auditor-clone` is dated 2026-09-15; `.git/config`
   (which carries `core.hooksPath=.githooks`) has an mtime of 2026-09-16 --
   both predate 191d8fc6 (2026-10-14 20:40:53) by nearly a month. Ruled out
   as the explanation, though see the caveat below.
4. **Git identity.** 191d8fc6 and every one of this role's own SUCCESSFUL
   commits that same evening (`2f4a895e`, `cff2e7a8`, `db1aa9d0`) are ALL
   authored and committed as `Michael Dibert <mikied68@gmail.com>` -- the
   global identity, no local override in this clone. Identical in every case.
   Ruled out.
5. **A `SAIRN_SEED_GATE`/`SAIRN_GATE_EXEMPT`/`SAIRN_SKIP` override.**
   `docs/BYPASS-LOG.jsonl` has no row anywhere near 2026-10-14T20:4x-21:xx.
   Ruled out for those three named mechanisms specifically (does not rule out
   a bare `git commit --no-verify`, which this log cannot see by design).

## What actually happened, found in the reflog

`git reflog show HEAD`, around that commit:

```
40262f40  HEAD@{34}: commit: docs(hover): h1 b37 handoff -- clean stopping point before the report/digest
7a1d3382  HEAD@{33}: pull --rebase origin main (start): checkout 7a1d3382...
191d8fc6  HEAD@{32}: pull --rebase origin main (pick): docs(hover): h1 b37 handoff -- clean stopping point before the report/digest
191d8fc6  HEAD@{31}: pull --rebase origin main (finish): returning to refs/heads/main
3883b7fa  HEAD@{30}: commit: chore(claims): hover releases hover
```

**`191d8fc6` is not the commit that was originally authored.** The handoff was
first committed locally as `40262f40` (still a resolvable object: `git
cat-file -e 40262f40` succeeds, same message, orphaned since the rebase
replaced it). A `git pull --rebase origin main` then ran, and its internal
replay (`pick`) produced a NEW commit, `191d8fc6`, with the same tree and
message but a different sha and parent -- the one that ended up on
`origin/main`.

**The b38 handoff attempt, by contrast, was a plain `git add` +
`git commit`** with no pull/rebase in between -- and it was refused, exactly
as `tools/hover_auditor_scope_gate.py`'s `ALLOWED` list says it should be.

## What this role could NOT pin down, and why it is routed rather than guessed at

Both `.githooks/pre-commit` (the path 40262f40 would have gone through) and
`.githooks/pre-push`'s own call to the SAME gate (`--pre-push`, via
`changed_outgoing()`, which diffs `remote-sha..local-sha` with `git log
--name-only` -- a range that would include `SAIRN-handoff-h1-b37.md` either
way) both read as though they SHOULD have caught this on the original commit
or on the push that landed it. **Two possibilities this role cannot
distinguish from inside a worktree check, and did not want to guess between:**

1. **`40262f40`'s original `git commit` used `--no-verify`** (invisible to
   `BYPASS-LOG.jsonl`, which only logs the three named env-var overrides, not
   a bare flag) -- in which case the gate worked exactly as designed and
   simply was not consulted.
2. **Git's internal rebase-replay (`pick`) does not invoke `pre-commit`/
   `commit-msg` the same way an interactive `git commit` does**, in whatever
   git version/config this machine runs -- in which case ANY session that
   commits a platform-scope violation locally, then runs `git pull --rebase`
   before noticing, could have it silently replayed past the gate on the next
   rebase, with `--pre-push`'s own range-diff either not running for the same
   reason or not being reached because the push itself used a fast path this
   role did not identify.

**Either way, the operational fact for every other session matters more than
which one it is:** `git pull --rebase` is the standard move used throughout
this platform's own push protocol (see every build agent's own handoff,
"pulled via git pull --rebase, clean fast-forwards and rebases throughout")
-- so if explanation 2 is correct, this is not a one-off, it is a standing gap
in the auditor's own enforcement that reproduces every time a locally-refused
(or never-checked) commit gets rebased rather than committed fresh.

## Suggested next step, for cc to decide

Test directly (cc's own clone, cc's own call on whether it's worth the
cost): commit a disposable out-of-scope file in this clone WITHOUT
`--no-verify` first to confirm the baseline refusal still holds (this role
did not re-run that live test this batch, to avoid leaving test commits in
the real history under a denied-permission constraint), then reproduce
`40262f40`'s exact shape -- commit it, then `git pull --rebase` over it --
and watch whether `.githooks/pre-commit` fires on the replay. If it does not,
the fix is likely in `.githooks/pre-commit`'s own docstring section titled
"TWO GUARDS LOOKED THE SAME AND ARE NOT" -- a THIRD guard, for rebase-replay,
may belong there.

Logged to the hover chain alongside this note.
