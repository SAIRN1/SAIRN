# Scoped subagent definitions — hank's delegation points

Written 2026-10-06. **Every delegation point a session doing this work actually
reaches is listed here, and each one says what is enforced versus what is only
declared.** A capability list that overstates its own enforcement is the same
defect as a check that reports a pass it never performed.

---

## WHAT IS ACTUALLY ENFORCED, AND WHAT IS NOT — read this before trusting the table

**`tools:` IS THE ENFORCEMENT.** It is a documented frontmatter key and it is an
**allowlist**: a tool absent from it is not available to the agent. For the four
read-only agents this is the whole boundary and it is a strong one — with no
`Write`, no `Edit` and no `Bash`, they cannot modify any file or run any command,
so *"must not write the audit log"* is not a rule they could break.

**`disallowedTools:` and `isolation:` in frontmatter are DECLARED, NOT VERIFIED
BY ME.** `isolation: "worktree"` is documented as a parameter of the `Agent`
**tool call**, and `disallowedTools` is documented for settings rather than for
agent frontmatter. I have not driven either through a live spawn to confirm the
harness reads them from these files. **So treat them as intent plus a tripwire
for a future editor, and pass `isolation: "worktree"` on the Agent call itself
when it matters** — `sweep-runner` is the one where it matters, because that
agent runs tools that write.

That distinction is the honest state. **Do not read the `disallowedTools` block
as a proven boundary on an agent that also has `Bash`.** For `panel-auditor`,
`sweep-runner` and `suite-driver`, `Bash` is unrestricted at the harness level
unless the harness honours those entries, and I have not proved it does.

---

## The delegation points

| Agent | What it is for | `tools:` (enforced) | Writes possible? |
|---|---|---|---|
| `citation-verifier` | re-derive a `file:line` at HEAD; MOVED / UNMOVED / NOT FOUND / CANNOT TELL | `Read, Grep, Glob` | **No** — no Write, Edit or Bash |
| `register-cell-reader` | read a resource's real write site, field list, consumers, named trigger | `Read, Grep, Glob` | **No** |
| `hover-finding-reader` | read named seq numbers out of the auditors' logs | `Read, Grep, Glob` | **No** — and this one is structural, see below |
| `suite-driver` | run named suites, report real exit codes and failing arm names | `Read, Grep, Glob, Bash` | Bash present; denials declared |
| `sweep-runner` | run write-when-run sweeps in a worktree, report exit codes | `Read, Grep, Glob, Bash` | Bash present; **`isolation: worktree`** is the real boundary |
| `panel-auditor` | pre-existing; Guardian Check 0 over a batch of StoneDesk panels | `Read, Grep, Bash` | Bash present; **was previously unscoped** |

**`panel-auditor` was the only pre-existing definition and it was NOT scoped.**
It carried `tools: Read, Grep, Bash` with no denials and a description saying
*"does not fix anything itself"*. That sentence was an instruction, and an
instruction is not a boundary: unrestricted `Bash` could have written the hover
audit log, edited `tools/tooling_inventory.py`, committed or pushed. Scoped in
this same change.

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
