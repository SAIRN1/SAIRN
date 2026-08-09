---
name: sairn-precommit-gate
description: 'Not a new analysis skill — a routing checklist confirming the RIGHT existing skills actually ran before any commit, given what kind of change it is. Trigger before every commit. Guardian, adversarial-reviewer, decision-gate, and visual-review already exist and are good; this exists because a real gap surfaced tonight — visual-review did not run until very late, well after several panels were already committed, simply because nothing forced the question of whether it applied.'
---

# SAIRN Pre-Commit Gate

Before any commit, answer these — not new judgment, just confirming the right existing tools were actually pointed at this change:

| Question | If yes | Skill |
|---|---|---|
| Does this touch JS logic, data, or claimed capabilities? | Always yes for a code change | `sairn-guardian-v2` — mandatory, no exceptions |
| Is this a real feature/bug-fix merge, not a tiny one-liner? | Usually yes | `sairn-adversarial-reviewer` — all 4 personas |
| Does this touch anything rendered/visible (a panel, a button, layout, color)? | If yes | `sairn-visual-review` — at minimum the affected panel, both viewports |
| Does this claim "complete," "production," or make a customer-facing promise? | If yes | `sairn-decision-gate`'s Premortem |
| Does this create a new storage key or wire a function to a DOM target? | If yes | The two preventive checks in `sairn-software-architect` (grep before creating, grep before wiring) |
| Is this the first touch on this app this session, or a new app entirely? | If yes | `sairn-portfolio-triage`'s 4 scanners — real baseline before assuming anything about current state |
| Does this touch money, sync, or infrastructure config? | If yes | `sairn-silent-failure-sweep` — "no crash" is not "correct" |
| Does the change resemble a previously-shipped bug class (fire-and-forget write, IIFE scope leak, AI chat placeholder race, etc.)? | If yes | `sairn-code-scrubber`'s checklist |

**Added 2026-08-09:** the original version of this table only routed to
Guardian/adversarial-reviewer/visual-review/decision-gate/software-architect
— it never mentioned portfolio-triage, silent-failure-sweep, or
code-scrubber at all, despite all three existing and being exactly the
right tool for "first touch on an app" or "money/sync/infra" changes. Same
gap class this skill exists to prevent, found in its own routing table.

**The rule:** don't commit until every "yes" row's skill has actually run for this specific change — not run at some point this session, run *for this change*. A Guardian pass from three commits ago doesn't cover a new commit's new risk.

## Why this exists instead of a bigger review skill

Tonight had genuinely excellent tools sitting unused for too long — `sairn-visual-review` existed but nothing forced the question "does this apply to what I'm about to commit" until asked directly, late, after real UI bugs had already shipped. This isn't a new judgment layer on top of already-good judgment; it's the checklist that makes sure the judgment that exists actually gets pointed at the right target, every time, not just when someone happens to remember.
