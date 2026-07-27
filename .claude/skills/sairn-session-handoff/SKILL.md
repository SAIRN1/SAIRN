---
name: sairn-session-handoff
description: 'How to write a SAIRN-SESSION-N-HANDOFF.md, codified from what actually worked across three real handoffs tonight (65, 66, 67) rather than adopted wholesale from any single external source. Trigger before capacity runs low, before a known stopping point, or any time a session needs to hand off to a fresh one — same as before, now with a real, tested template instead of writing one from scratch each time.'
---

# SAIRN Session Handoff

Considered adopting alirezarezvani/claude-skills' "Handoff" skill (derived from Matt Pocock's original, MIT licensed) wholesale — decided against it, for a specific, real reason: its core discipline is referencing existing artifacts by path/URL instead of duplicating them. That's a reasonable design choice in general, but it's the wrong one for us specifically — our actual failure mode tonight (the SAIRNbuild claims that turned out to be entirely false) happened because something sat unverified in memory; a reference-by-path handoff doesn't force the re-verification that caught it. Our own three handoffs tonight (Sessions 65, 66, 67), fully self-contained and independently re-verified each time, already worked in exactly our environment. Codifying that instead of switching philosophies.

Two genuinely good mechanical ideas borrowed from the upstream skill, kept:

1. **Automated triggering** — a SessionStart hook that reminds a fresh session to read the latest handoff before touching anything, and a SessionEnd hook that prompts writing one if capacity is running low. (Add to `.claude/settings.json` if not already present — mechanical trigger, not just a remembered habit.)
2. **A redaction check before saving** — given tonight involved a real GitHub PAT and could easily have involved Stripe keys in a handoff doc, scan for anything credential-shaped before writing the file, same category of check as Guardian's "no API keys in HTML."

## Naming convention — resolved 2026-07-26

Two conventions exist in the repo right now: a general `SAIRN-SESSION-N` series (used for StoneDesk work, N=63 through 67 so far) and a separate `SAIRNVET-SESSION-N` series (N=56 through 62). Both exist; neither was ever formally decided as *the* standard, which becomes a real problem the moment this skill is genuinely used for every app, not just StoneDesk.

**Resolved: per-app prefix, always.** `SAIRN-SESSION-N` was really StoneDesk work all along — it should be understood as `STONEDESK-SESSION-N` in spirit, and future StoneDesk handoffs should use that explicit prefix rather than the generic one, matching SAIRNvet's existing pattern. When work spans multiple apps in one session (as tonight's skill-building did), use `SAIRN-PLATFORM-SESSION-N` for that specific cross-cutting work, keeping per-app numbering independent and never colliding with any single app's own series. Do not renumber the existing 63-67 files retroactively — apply this convention going forward only, and note the historical inconsistency in the next handoff so nobody re-derives the wrong pattern from old filenames.

## The Template (proven across Sessions 65-67 tonight)

# SAIRN — Session N Handoff

Written [mid-session before capacity ran out / at natural stopping point].
Claims below are independently verified against the actual repo/live site,
not assumed from memory — same standard as prior sessions in this series.

## 1. Verified current state
- origin/main HEAD: [SHA] — confirmed via `git rev-parse origin/main`
- [Any other directly-checkable facts: panel counts, script-block counts,
  live proxy status via a real curl, not assumed]

## 2. Commits this session, in order
[SHA + one-line summary each, pulled from real `git log`, not paraphrased
from memory of what was intended]

## 3. What was CORRECTED, not just added
[This section matters as much as new work — if anything reported earlier
as true turned out not to hold up on verification, say so explicitly here.
Sessions 66 and 67 both had real examples: a platform-context handoff that
didn't exist in the repo, a "duplicate ID" finding that didn't reproduce,
an output-style key that was never actually added despite being assumed
done. Naming the correction is not a failure — treating an unverified claim
as fact going forward would be.]

## 4. Open items, prioritized
[Real, current, re-verified — not carried forward from an older handoff
without re-checking it's still accurate]

## 5. Standard verification reminder for whoever reads this next
Verify main HEAD, verify branch, re-run relevant checks before trusting any
claim in this document — including this one.

## When to write one

- Proactively, before capacity runs low — never wait for a hard cutoff.
- At any natural stopping point where a session might not resume immediately.
- Before switching between local and cloud sessions, or before opening a fresh session for any reason.

## The one rule that matters most

Section 3 (corrections) is not optional and not a sign of a bad session — a handoff that never has anything to correct across a long project is more likely hiding an unverified claim than actually being perfect three times running. Look for what to correct before assuming there's nothing.
