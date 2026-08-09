---
name: sairn-parallel-app-scaling
description: 'How to run multiple SAIRN apps'' work in parallel safely, without the cross-session confusion this project hit repeatedly on just 1-2 apps at a time (lost context, cloud/local session mixups, duplicate work across sessions). Trigger whenever more than one app needs real work in the same stretch of time — not a review skill, a logistics/safety playbook for scale.'
---

# SAIRN Parallel App Scaling

Everything else built tonight (Guardian, adversarial-reviewer, silent-failure-sweep, etc.) answers "is this app correct." This answers a different question: "how do we work on many apps at once without the sessions stepping on each other or losing track of what happened where" — a real, repeated problem tonight even at small scale (1-2 apps), worth solving properly before scale makes it worse.

## The one mechanical fix: worktree per app, always

claude --worktree sairnhr
claude --worktree sairnacc
claude --worktree sairnlaw

Each gets its own directory and branch, shares one git history, zero risk of one session's edit colliding with another's uncommitted work. This was researched and confirmed real earlier tonight — use it as the default the moment more than one app is in flight, not just when a collision has already happened.

**Real ceiling, from actual current usage data:** 4-8 concurrent worktrees per person before you're bottlenecked on *review*, not on running them. Don't scale past what can actually be reviewed.

## Mandatory first 3 steps, every new app, before any other work

1. **`sairn-portfolio-triage`** — the 4 scanners, real baseline, before assuming an app's state.
2. **`sairn-silent-failure-sweep`** — check the catastrophic-shaped risks (money claims, sync claims, infrastructure config) before assuming "no crash" means "correct."
3. **Confirm the app is in `sairn-guardian-v2`'s App File Map** with a real, non-colliding color — two collisions (SAIRNhr/SAIRNvet, SAIRNcare/SAIRNacc) were found and never resolved tonight; don't let a new app launch into a third collision.

Only after these three: start real feature work.

## Naming discipline at scale

Per-app handoff prefix always (`SAIRNHR-SESSION-N`, `SAIRNACC-SESSION-N`), never a shared generic series — this was already the resolved convention from `sairn-session-handoff`, restated here because it matters more, not less, once several apps' handoffs could otherwise collide or get confused for each other.

## What actually caused confusion tonight, applied forward

- **Lost context mid-session** (the SAIRNgrounds/SAIRNscape work Hank had no record of) — mitigated by proactive handoffs, not eliminated. At scale, write a handoff at the end of EVERY app-session, not just when capacity runs low — a 2-line "confirmed clean, nothing pending" handoff costs nothing and prevents the next session from re-deriving state.
- **Cloud vs. local session confusion** — at scale, with more sessions open, this risk multiplies. Before typing into any Claude Code window, confirm which one it is (local terminal vs. claude.ai's Code tab) — don't assume.
- **Two sessions given the same instruction, doing redundant work** — before pasting an instruction, know which specific worktree/session it's going to. "Fold into the next response" instructions apply to ONE specific session, not whichever one answers first.

## Portfolio Audit Status (as of 2026-08-09)

Track which apps have had the full mechanical + judgment treatment
(`sairn-portfolio-triage`'s 4 scanners, `sairn-silent-failure-sweep`,
`sairn-adversarial-reviewer`'s 4 personas) vs. only a narrower pass —
update this table whenever an app crosses that line, so a fresh
session doesn't have to re-derive which apps are actually clean.

| App | 4-Scanner Triage | Silent-Failure Sweep | Adversarial Review (4 personas) | Status |
|---|---|---|---|---|
| stonedesk.html | done | done | done | Fully treated |
| sairnbiz.html | done | done | done | Fully treated |
| sairngrounds.html | done | done | done | Fully treated |
| sairnscape.html | done | done | done | Fully treated |
| sairncode.html | done | done | done | Fully treated |
| sairnvet.html | done | done | done | Fully treated |
| sairnbuild.html | **not run** | **not run** | **not run** | **Gap — only the AI Budget Early Warning feature was reviewed, scoped to that one feature. The rest of the app has never had any of the three passes.** |

**sairnbuild.html is the one real gap left in the portfolio.** Don't
assume it's clean because nothing bad has surfaced — nothing has
looked yet, outside the one feature that was reviewed. Run the full
three-pass treatment on it before calling it anything other than
unaudited.

## When this doesn't apply

Single-app, single-session work (most of tonight) doesn't need any of this — worktrees, multi-app naming, and the "which session is this" discipline are specifically for when real parallel app work is actually happening, not a default overhead to carry for a single StoneDesk session.
