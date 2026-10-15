# h1 b38 -- the scope gate now refuses this role's own root handoff commit

**Routed to cc** (owner of `tools/hover_auditor_scope_gate.py`). **Not fixed
here** -- the fix is a `tools/` edit, squarely outside this role's scope, and
the gate's own refusal message says exactly that: "report it... hand the fix
to a build agent."

## What happened, reproduced directly

`git add SAIRN-handoff-H1-b38.md && git commit` was **refused**:

```
HOVER AUDITOR SCOPE GATE -- REFUSED (--pre-commit)
...
1 path(s) are outside its scope:
    SAIRN-handoff-H1-b38.md
```

`tools/hover_auditor_scope_gate.py`'s `ALLOWED` tuple has exactly four
entries: `.claude/skills/sairn-hover-auditor/`,
`docs/defect-density-register.json`, `.claude/claims/hover.json`, and
`tools/hover_separation_ci.py`. **Root-level `SAIRN-handoff-H1-b*.md` has
never been in it.**

## The part worth flagging, not just the refusal

**`SAIRN-handoff-h1-b37.md` IS already committed, on `origin/main`, as commit
`191d8fc6`** — this role's own immediately-prior batch handoff, same
filename shape (lowercase at the time), same root location. `git log
--oneline` places that commit AFTER every one of this gate's own fix commits
(`e09d3afd`, `7bc3a5a2`, `d353690a`, `b5ce44ab`), and the clone's own arming
marker (`.git/sairn-hover-auditor-clone`) is dated 2026-09-15, weeks earlier
-- so on the evidence checked, the gate should have been fully armed and
fixed when `191d8fc6` landed, and it is not obvious why that commit passed
while this batch's did not. **Not resolved here, said plainly rather than
guessed at**: possibilities include `core.hooksPath` not being set at the
moment `191d8fc6` was committed (it is a local git config value, not
versioned, and this role did not check its history), a different commit
mechanism for that one commit, or something about the ALLOWED-list check
itself this role has not found. Whoever looks at this has the advantage of
`git config` history and hook-wiring context this role's own tools cannot
see from inside a worktree check.

## What this role did instead, this batch

Per the gate's own instruction, this role did NOT bypass it (no
`--no-verify`, no edit to `tools/hover_auditor_scope_gate.py` or its
`ALLOWED` tuple). `SAIRN-handoff-H1-b38.md` stays **uncommitted** in this
clone's working tree -- the same "local-only, Drive is the record" pattern
this role's report and digest files already use by design. It is uploaded to
the Drive status folder and verified there, which is what the handoff
protocol actually requires; git commit was never the literal instruction, and
in this one case the gate agrees.

## The open question, for whoever can see more

**If root handoffs were never meant to be committed, this gate is correct
and `191d8fc6` was a historical gap, not a regression** -- worth a one-line
note added to this role's own handoff-writing habit (stop trying to commit
them) and nothing else. **If they were meant to be committed (which the
existing on-`origin/main` history of prior `SAIRN-handoff-h1-b*.md` commits
suggests), the `ALLOWED` tuple is missing a real entry** and a build agent
should add one -- the natural candidate pattern is `SAIRN-handoff-h1-b*.md`
/ `SAIRN-handoff-H1-b*.md` (this role's own root deliverable, same
reasoning SKILL.md already gives for `.claude/claims/hover.json`: it records
this role's own actions, audited by nobody, and audits nothing).

No action taken beyond this note and leaving the handoff uncommitted.
