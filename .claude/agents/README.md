# Scoped subagent definitions — hank's delegation points

Written 2026-10-06. **Every delegation point a session doing this work actually
reaches is listed here, and each one says what is enforced versus what is only
declared.** A capability list that overstates its own enforcement is the same
defect as a check that reports a pass it never performed.

---

## MEASURED 2026-10-06 — and the answer is narrower than the first version of this file claimed

**I drove a live subagent to find out, instead of reasoning about it.** A
`suite-driver` instance was asked to attempt four things and report the verbatim
refusal for each: one command NOT on its denial list (the control), two that
were, and one `Write`.

**All four were refused identically:**

    Error: No such tool available: Bash. Bash is disabled for this
    session, in subagents as well as here.

**The CONTROL was blocked too**, which is what makes the result honest and
inconclusive in the direction that matters:

- **`disallowedTools:` in frontmatter is NOT CONFIRMED to be enforced.** The
  observed behaviour is equally consistent with `Bash` and `Write` being
  disabled session-wide, one layer above the agent file. Nothing in the refusal
  text mentions a pattern, a command, or the agent definition. **Treat it as
  declared, not enforced.**
- **`tools:` CANNOT GRANT, only narrow.** `suite-driver` lists `Bash` in its
  allowlist and did not get it. So the session's own tool policy is an upper
  bound and a definition can only subtract from it. The first version of this
  file called `tools:` "the enforcement" — **that was half right and the wrong
  half was load-bearing**: it is enforcement against WIDENING, and it is not a
  grant.
- **`isolation:` in frontmatter is likewise unverified**, and `isolation` is
  documented as a parameter of the `Agent` **call**. Pass it there when it
  matters.

**The practical consequence, which is the only thing to act on: in this
session, subagents are read-only because the SESSION says so, not because these
files say so.** That is a stronger guarantee than the one I wrote down and a
*different* one — it can change without any of these files changing. So
`suite-driver` and `sweep-runner` **cannot currently do their jobs**: both need
`Bash` and neither can have it. They are kept because the definitions are
correct about what those roles need; they are **not usable in this session** and
that is recorded here rather than discovered by somebody whose sweep returns
nothing.

---

## HOW TO READ THE TABLE BELOW

**SUPERSEDED, 2026-10-06, AND LEFT NAMED RATHER THAN DELETED.** This section
used to open *"`tools:` IS THE ENFORCEMENT"* and describe it as an allowlist
that makes the read-only agents safe. **The measurement above shows that was
half right, and the wrong half was the load-bearing one:** `tools:` constrains
only DOWNWARD. It cannot hand an agent a tool the session withholds, and in
this session it withheld `Bash` and `Write` from every subagent regardless of
what any definition asked for.

So read the `tools:` column as **the most this agent could ever have**, not as
what it has. The read-only agents really are read-only here — but by the
session's policy, which can change without any of these files changing.

---

## The delegation points

| Agent | What it is for | `tools:` (the CEILING, not a grant) | Writes possible in THIS session? |
|---|---|---|---|
| `citation-verifier` | re-derive a `file:line` at HEAD; MOVED / UNMOVED / NOT FOUND / CANNOT TELL | `Read, Grep, Glob` | **No** — no Write, Edit or Bash |
| `register-cell-reader` | read a resource's real write site, field list, consumers, named trigger | `Read, Grep, Glob` | **No** |
| `hover-finding-reader` | read named seq numbers out of the auditors' logs | `Read, Grep, Glob` | **No** — and this one is structural, see below |
| `suite-driver` | run named suites, report real exit codes and failing arm names | `Read, Grep, Glob, Bash` | **No — and it cannot run either.** `Bash` is withheld session-wide, so this agent is currently UNUSABLE |
| `sweep-runner` | run write-when-run sweeps in a worktree, report exit codes | `Read, Grep, Glob, Bash` | **No — and it cannot run either.** Same session-wide withholding; pass `isolation: "worktree"` on the Agent CALL if Bash ever returns |
| `panel-auditor` | pre-existing; Guardian Check **0b and 0d** over a batch of StoneDesk panels | `Read, Grep, Glob` | **No** — `Bash` REMOVED 2026-10-06; Check 0a routed to `suite-driver` |

**`panel-auditor` was the only pre-existing definition and it was NOT scoped.**
It carried `tools: Read, Grep, Bash` with no denials and a description saying
*"does not fix anything itself"*. That sentence was an instruction, and an
instruction is not a boundary: unrestricted `Bash` could have written the hover
audit log, edited `tools/tooling_inventory.py`, committed or pushed.

**A first pass added a `disallowedTools:` block and KEPT `Bash`, on the grounds
that Check 0a needs `node --check`. That was still a declaration** — and the
measurement above shows why it was not good enough: a denial LIST enumerates
the shapes somebody thought of, and `disallowedTools:` is not confirmed to be
read at all.

**`Bash` is now REMOVED from the allowlist (2026-10-06).** *"It cannot fix
anything"* stops being a promise and becomes a fact about what it can reach.
**Check 0a is not silently dropped** — it is taken out of the agent's
description and routed to `suite-driver`, because an agent that quietly stopped
performing one of three named checks while still returning a verdict would be
the fabrication defect 0b exists to catch, committed by the auditor.

---

## The two things the denials exist for

**1. The hover audit log.** `hover-finding-reader` has **no Bash at all**, and
that is deliberate rather than tidy. The auditors' logs are hash-chained
precisely so a build agent cannot alter what was said about the build agent's
work; anything a build agent spawns inherits that boundary. A tool that *can*
write cannot be trusted to have not. `tools/hover_auditor_scope_gate.py`
(prevent) and `tools/hover_separation_audit.py` (detect) enforce the same thing
at repo level, independently — two layers on purpose.

**2. `tools/tooling_inventory.py`.** Named in every `disallowedTools` block
because its `PURPOSES` dict is hand-written and **a duplicate key is a silent
overwrite** — the generator refuses loudly when an entry is MISSING and says
nothing when one is written twice. On 2026-10-06 I inserted a second
`gate_parity_check.py` key without noticing another session had already added
one; Python kept the later and mine was dead text.

**NOT put in the shared `.claude/settings.json` deny list, deliberately.** A
path deny there would block **cody and fourth**, who legitimately own and edit
that file. Scoping it to the subagents I spawn gets the protection without the
collateral damage — which is the difference between a boundary and an
obstruction.

---

## The standing rule these all share

Every one of them reports and **none of them decides**. The tier is derived and
cross-checked; the replacement wording belongs to somebody who can see the whole
cell; the fix belongs to a session with a claim. A narrow read that produces
paste-ready text is how `sfBottleFill()` — a function that has never existed —
reached a register cell, a routed fix and two correction passes.
