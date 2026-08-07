---
name: sairn-forward-scan
description: 'Proactive risk-anticipation as a standing habit, not a per-decision gate. Distinct from sairn-decision-gate''s Premortem (which fires before a specific claim/proposal) — this runs continuously during ordinary work, asking "given what has already happened, what is the next likely problem, before it happens." Applies equally to Claude Code and this chat. Trigger: starting a new app/feature, before a long session, before typing anything sensitive, before trusting a new tool''s output.'
---

# SAIRN Forward Scan

Every real lesson tonight was found reactively — a bug shipped, then got caught. This skill exists to flip a subset of that: patterns that already happened once are now known, named risks. Watch for their next occurrence *before* it happens, not after.

## Real, named risks — check these proactively, not after the fact

**Starting work on any app not yet touched this session:** run `sairn-portfolio-triage`'s 4 scanners FIRST, before writing any code — don't wait to discover duplicate features the hard way, they're now a known, expected risk on any multi-session-built app.

**About to declare anything "done"/"complete"/"100%":** before saying it, ask "has this had a genuinely independent review, or only self-review?" If only self-review, get the independent pass BEFORE the claim, not after someone asks and it turns out incomplete.

**Session running long (many hours, many commits):** don't wait for compaction to start before writing a handoff. Proactively write one at a natural pause — the cost of an early handoff is small; the cost of a lost/rushed one mid-compaction is real (happened twice tonight).

**About to type anything credential-shaped:** before typing, ask "is this going into the real destination file, or into a chat/terminal command first?" Only the real destination is safe — this question prevents the exposure instead of reacting to it after (happened three times tonight before this became automatic).

**About to trust a scanner/tool's output on an app it wasn't built/tested against:** ask "has this specific tool been verified portable to this specific app," before trusting an alarming number — an identical result across two different apps is itself a signal to check the tool, not the apps.

**About to build a new feature with any threshold, ratio, or edge case:** before writing the happy-path logic, ask "what's the zero case, the negative case, the empty case" — SAIRNbuild's zero-budget-with-real-spend gap existed because that specific input wasn't asked about until a later review caught it. Ask during design, not after shipping.

**About to add a new visual indicator (color, badge, KPI):** before shipping, ask "does this collide with an existing color/signal meaning elsewhere in the app" — the --warn/--p amber collision and the SAIRNbiz static-green-on-negative bug both existed because this question wasn't asked until the color was already picked.

## What this is NOT

Not a replacement for `sairn-decision-gate`'s Premortem (that's for a specific claim or proposal about to go out the door) or `sairn-precommit-gate` (that's the routing checklist for which skill applies to a given commit). This is the standing habit of scanning for the *next* instance of an *already-known* pattern, applied continuously, not triggered by a specific decision point.

## Applies equally to both

This applies the same way whether the work is happening in Claude Code (Hank) or in this chat — a proactive question asked here about an instruction before sending it is the same discipline as one asked in code before writing it.
