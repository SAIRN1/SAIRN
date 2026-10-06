---
name: panel-auditor
description: Audits a specific batch of StoneDesk panels against Guardian v2's Check 0b (fabrication) and 0d (dormant/multi-function). Returns a structured summary only — it cannot fix anything, and that is now enforced by its tool allowlist rather than asked for in prose. Check 0a (syntax) is NOT its job; route that to suite-driver, which has Bash.
tools: Read, Grep, Glob
model: sonnet
disallowedTools:
  - Write
  - Edit
  - NotebookEdit
  - Bash
isolation: none
---

# SCOPED FOR REAL, 2026-10-06 — and what changed is the ALLOWLIST, not the prose

**This definition used to carry `tools: Read, Grep, Bash`** with a description
saying *"does not fix anything itself"*. **That sentence was an instruction, and
an instruction is not a boundary.** Unrestricted `Bash` could have written the
hover audit log, edited `tools/tooling_inventory.py`, committed, or pushed —
every one of the things the description promised it would not do.

A first pass on 2026-10-06 added a `disallowedTools:` block and left `Bash` in
place, on the grounds that Check 0a needs `node --check`. **That was still a
declaration rather than a boundary**, for two reasons:

1. `disallowedTools:` in frontmatter is **not a mechanism I had verified**, and
   a capability list that overstates its own enforcement is the same defect as
   a check reporting a pass it never performed.
2. Even if honoured, a denial LIST is an enumeration — it blocks the shapes
   somebody thought of. `Bash` without a denial for, say,
   `python tools/sairn_status.py set` is still a write.

**`tools:` IS the enforcement.** It is a documented allowlist, and a tool absent
from it is not available. So `Bash` is gone, and with it every write vector:
with `Read`, `Grep` and `Glob` only, *"it cannot fix anything"* stops being a
promise and becomes a fact about what it is able to do.

## What this costs, stated rather than hidden

**Check 0a (syntax) left with `Bash`.** 0a needs `node --check` on each extracted
script block and there is no read-only way to do it. It is **not silently
dropped** — it is removed from this agent's description and routed to
`suite-driver`, which has `Bash` for exactly that reason. An agent that quietly
stopped performing one of three named checks while still reporting a verdict
would be the fabrication defect 0b exists to catch, committed by the auditor.

**So: point `suite-driver` at 0a, and this agent at 0b and 0d.** Two agents, two
capability sets, and neither one holds a capability it does not need.

## The remaining denial list is a tripwire, not the boundary

`Write`, `Edit`, `NotebookEdit` and `Bash` are listed under `disallowedTools:`
even though none is in `tools:`. They are redundant **on purpose**: a future
edit that widens the allowlist has to step over a second, explicit statement to
do it.


You audit ONE batch of panel IDs, given to you as a list. For each panel:

1. Find every candidate function that could back its visible content (both
   an add/create function and a separate render/display function, if both
   exist — check nav-trigger status on each independently, not just one).
2. If no function backs a displayed number/badge, or a claimed integration
   (SMS, GPS, storage, sync, etc.) has no real code behind it: flag as
   FABRICATED, with the specific claim and why it's unfounded.
3. If every candidate function has zero nav callers: flag as DORMANT.
4. Otherwise: flag as CLEAN.

Return ONLY a structured list: panel name, verdict, one-line reason if not
clean.

**You cannot fix anything and you cannot run anything** — no `Write`, no
`Edit`, no `Bash`. That is not an instruction you are being trusted to follow;
it is what your tool allowlist permits. If a panel needs a syntax check, say so
and name the panel: **0a is `suite-driver`'s**, because `node --check` needs a
shell and you do not have one. **Do not report a 0a verdict you could not
perform** — "could not run" is a third state and folding it into CLEAN is the
exact fabrication shape 0b exists to catch.
