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

## Portfolio Audit Status (as of 2026-08-09, corrected same day)

Track which apps have had the full mechanical + judgment treatment
(`sairn-portfolio-triage`'s 4 scanners, `sairn-silent-failure-sweep`,
`sairn-adversarial-reviewer`'s 4 personas) vs. only a narrower pass —
update this table whenever an app crosses that line, so a fresh
session doesn't have to re-derive which apps are actually clean.

**Correction, same day:** the original version of this table (written
mid-session) was already stale by the time anyone read it back. It
omitted sairnlaw.html/sairndesign.html/sairnlegacy.html entirely (all
three were built ground-up earlier the same session and got their own
full 3-pass treatment before this table was even written) and still
listed sairnbuild.html as "not run" after its gap had already been
closed later the same session. Separately, sairngrounds.html's and
sairnscape.html's "Adversarial Review: done" cells had **zero
corroborating commit evidence anywhere in the repo** — a follow-up
audit found the only commit mentioning both "adversarial" and either
app name was this table's own entry. A genuine adversarial-review pass
was run on both as part of that correction: sairnscape came back clean;
sairngrounds did not — a real CRITICAL (AI chat concurrent-request
misattribution, same bug class already fixed in sairnbiz/sairnscape,
found unfixed here) was caught and fixed (`8e70233`). Lesson: a table
entry is a claim, not evidence — don't trust "done" in this table
without a commit SHA or session handoff backing it, and re-verify
before extending trust forward from it, same standard as everything
else in the SAIRN skill set.

| App | 4-Scanner Triage | Silent-Failure Sweep | Adversarial Review (4 personas) | Status |
|---|---|---|---|---|
| stonedesk.html | done | done | done | Fully treated |
| sairnbiz.html | done | done | done | Fully treated |
| sairngrounds.html | done | done | done (real finding caught+fixed on re-verification, `8e70233`) | Fully treated |
| sairnscape.html | done | done | done (re-verified for real, genuinely clean) | Fully treated |
| sairncode.html | done | done | done | Fully treated |
| sairnvet.html | done | done | done | Fully treated |
| sairnbuild.html | done | done | done | Fully treated (was the one gap, closed `09b65a9`; its own 4 self-disclosed unfixed silent-failure instances were closed later, `66cf7b9`) |
| sairnlaw.html | done | done | done | Fully treated (built ground-up this portfolio; first full pass `c27a948`) |
| sairndesign.html | done | done | done | Fully treated (built ground-up this portfolio; first full pass `c27a948`) |
| sairnlegacy.html | done | done | done | Fully treated (built ground-up this portfolio; first full pass `c27a948`) |

**Standing rule: a cell in this table is only real if a corroborating
commit exists.** "Done" written in this table is not itself evidence —
it's a claim, exactly as fallible as any other unverified claim this
skill set warns about elsewhere. Before trusting any "done" here (your
own prior session's entry included), run `git log --oneline -i
--grep="<process name>" -- <app>.html` (or search commit bodies if the
file diff is empty, e.g. a review that found nothing to fix) and confirm
a real commit backs it. sairngrounds.html and sairnscape.html's
"Adversarial Review: done" cells passed this exact test with **zero
hits** — the only commit ever mentioning both "adversarial" and either
app name was this table's own entry, not a review. Re-running the check
for real caught a live CRITICAL in sairngrounds that had sat unfound
since the table first claimed it was clean. Never let this table's own
prior entry stand in as its own evidence on a later re-check.

**All 10 apps in the portfolio are now genuinely fully treated** — each
cell above traces to a specific commit, not just an assertion. That
doesn't mean zero future findings; it means the same standard baseline
StoneDesk got has now genuinely been applied everywhere, not just
claimed. Key-collision leads surfaced by the 4-scanner triage on 7 of
these apps were individually traced (same per-key process StoneDesk's
`SESSION78` handoff used) and all confirmed false positives — same
underlying storage-getter, different local variable name at each call
site, not a real divergent-shape bug.

## When this doesn't apply

Single-app, single-session work (most of tonight) doesn't need any of this — worktrees, multi-app naming, and the "which session is this" discipline are specifically for when real parallel app work is actually happening, not a default overhead to carry for a single StoneDesk session.
