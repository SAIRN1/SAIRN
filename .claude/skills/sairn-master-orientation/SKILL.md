---
name: sairn-master-orientation
description: 'Read this FIRST, every session, before anything else. One consolidated index of every real lesson learned across a very long SAIRN build session — not a replacement for the other skills, a map to them plus the handful of cross-cutting rules that apply to literally every task regardless of which app or feature is being touched.'
---

# SAIRN Master Orientation

## The 10 cross-cutting rules — apply to every task, no exceptions

1. **Verify, never trust.** A "deployed"/"pushed"/"complete" claim — including your own — is unverified until checked against the real source (GitHub, the live site, the actual schema). Compaction and long sessions produce confident-sounding false claims. This cost real time twice tonight (a fabricated "SAIRNbuild deployed" claim, a stale "SAIRNbuild doesn't exist" finding that went stale after real work happened).

2. **Self-review is not independent review.** The session that wrote code checking its own work shares its own blind spot. Anything claimed "complete" needs a genuinely separate review pass. (`sairn-precommit-gate`)

3. **Byte-verification isn't scope-verification.** Confirming final bytes match doesn't confirm the diff was scoped correctly — a whole-file rewrite (encoding change, unintended re-save) can hide inside a byte-verified push. Check diff size against intended scope. (`sairn-guardian-v2`)

4. **Grep before creating.** Before a new storage key or a function targeting a new DOM container: check if it already exists. This single habit would have prevented the majority of real bugs found across every app tonight. (`sairn-software-architect`)

5. **Real function ≠ correct math ≠ honest visual signal.** Three distinct bug classes, all real, all found this session: fabricated data (no function at all), wrong math (a real function, wrong formula), and static/misleading visuals (a real correct number, wrong color). Check all three, not just the first. (`sairn-adversarial-reviewer`, `sairn-visual-review`)

6. **Never type a secret anywhere but its real destination.** A credential typed into chat, a terminal command, or a wrong file is compromised the moment it's typed — revoke and replace, don't just stop using it. Only ever enter a real secret directly into its actual destination file via a text editor.

7. **Canonical checkout only.** Verify working directory matches the one real, current checkout before trusting anything — multiple stale local copies caused real confusion tonight.

8. **"100%" means every known item resolved, not correctly prioritized.** Prioritization order (risk first) governs sequence; it doesn't excuse a known minor bug riding along under a "done" claim. (`sairn-decision-gate`)

9. **Scanners built for one app need portability verification before trusting on another.** An identical alarming result across two different apps is often the tool not recognizing either app's real pattern, not two real matching bugs. (`sairn-portfolio-triage`)

10. **Silence is enforced by convention, not a hard gate — with one real nuance found 2026-08-07.** Two distinct sources of unwanted output exist: model-generated narration (governed by output-style/CLAUDE.md, compliance-based, needs restating when it slips), and a separate Claude Code infrastructure feature — "a periodic progress heartbeat for long-running tool calls that previously went silent" — which is harness-level, not model-generated, and NOT touched by outputStyle at all. No specific disable-toggle for the heartbeat was found in a real search; don't assume one exists without checking again. Separately, a real, relevant bug fix was found in Claude Code's own changelog: "Auto mode boundaries — Fixed auto mode not respecting explicit user boundaries ('don't push', 'wait for X before Y') even when the action would otherwise be allowed." If a session is running a version older than this fix, `claude update` may genuinely help with both narration and general boundary-compliance — check the installed version against the changelog before assuming it's purely a repetition problem.

11. **A tracking-table cell is a claim, not evidence — including this skill's own App File Map and any Portfolio Audit Status table.** "Done" written down by an earlier session doesn't make it true; it makes it a claim from that session, exactly as fallible as anything else in rule #1. Found real, concrete on 2026-08-09: `sairn-guardian-v2`'s App File Map had a completely absent row for a real, live, fully-treated app (`sairnlegacy.html`, shipped under a different name than its own planned placeholder) that nothing ever cross-checked against `git ls-tree`; separately, `sairn-parallel-app-scaling`'s Portfolio Audit Status table claimed "Adversarial Review: done" for two apps with zero corroborating commit anywhere in history — re-running the check for real caught a live CRITICAL bug. Before trusting any table cell, grep `git log` for the specific commit that should back it; don't let a table's own prior entry stand in as its own evidence on a later read. (`sairn-guardian-v2`, `sairn-parallel-app-scaling`, `sairn-portfolio-triage`)

## Tool index — what to reach for, by task type

| Task | Tools/Skills |
|---|---|
| Any code edit | `sairn-guardian-v2` (mandatory), `node --check`, div-balance/nav-panel checks |
| Merging a real feature/fix | `sairn-adversarial-reviewer` (4 personas), `ponytail-review` |
| Anything visible/rendered | `sairn-visual-review` (browser must be focused — see its Environment Requirement) |
| New app/feature architecture | `sairn-software-architect`, `sairn-mobile-sync` (if field/phone-facing) |
| Should we build this / is this claim true | `sairn-decision-gate` (Bid/No-Bid, Premortem, NIST AI RMF) |
| Checking another app's real state | `sairn-portfolio-triage` (4 scanners: duplicate_global, missing_dom_target, panel_nesting, key_collision — note: key_collision's biggest false-positive class is comparing variable NAMES, not what they reference; trace before trusting a raw hit) |
| Catastrophic-shaped risk (money, sync, infra config) before calling anything done | `sairn-silent-failure-sweep` — "no crash" is not "correct"; the single most common real defect class found across the whole portfolio |
| More than one app needs real work in the same stretch of time | `sairn-parallel-app-scaling` — worktree-per-app, per-app handoff naming, and the Portfolio Audit Status table (verify every "done" cell against a real commit, don't trust the table itself) |
| End of session / low capacity | `sairn-session-handoff` — write it proactively, before a hard cutoff |
| Before any commit | `sairn-precommit-gate` — routes to the right skill above for that specific change |
| Recurring bug pattern already shipped once before | `sairn-code-scrubber` — 15 named, real, previously-shipped bug classes across all 10 apps; check before writing similar code again |
| Hard, repeated, unclear bug | `systematic-debugging` — after 3+ failed fixes, question the architecture, not the next patch |
| Greenfield build | `brainstorming` → `writing-plans` → `executing-plans`, spec approved before any code |
| Simplification pass | `ponytail-review` — finds what to delete, not just what to fix |

## What this skill is NOT

Not a replacement for reading the specific skill relevant to the task at hand — this is the map, not the territory. When a task clearly needs `sairn-visual-review`'s full checklist or `sairn-decision-gate`'s three frameworks, go read that skill directly. This exists so a fresh session (or one recovering from a compaction/context gap) gets oriented in one read, not so the other 10 skills stop mattering.
