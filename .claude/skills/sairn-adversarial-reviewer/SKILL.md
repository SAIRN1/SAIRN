---
name: sairn-adversarial-reviewer
description: 'Adversarial code review with four hostile personas, not three. Adapted from alirezarezvani/claude-skills (engineering-team/skills/adversarial-reviewer, MIT license, author ekreloff) with two additions found missing by our own vetting on 2026-07-26: no persona checked for fabricated/hardcoded data posing as computed values, and the existing personas only weakly caught cross-feature storage-key collisions. Trigger before merging any PR, after a long session, when Claude says "looks good," or when something feels off — same as the original.'
---

# SAIRN Adversarial Reviewer

Adapted from a real, well-designed upstream skill — the three-persona structure, severity classification, and output format below are the original design and it's genuinely good work. Two additions come from our own real bugs tonight that none of the three original personas reliably catch, confirmed by an honest third-party vetting pass before we adopted this: *"none of the surveyed skills read business logic for 'is this number actually computed or hardcoded' — that's specific to your own panel-auditor's Check 0b/0d."*

## The Four Personas

Each MUST produce at least one finding. If a persona finds nothing wrong, it hasn't looked hard enough.

### Persona 1: The Saboteur
**Mindset:** "I am trying to break this code in production."
Input never validated, state that can become inconsistent, concurrent access without synchronization, error paths that swallow exceptions, off-by-one errors, null/undefined dereferences, resource leaks.

**Strengthened 2026-07-26:** explicitly check whether two different code paths write to the same storage key with different assumed shapes — a schema collision. This is a distinct, named failure mode, not just a generic "state inconsistency": StoneDesk's invoices panel had exactly this (two features silently sharing `sd_invoices` with incompatible field shapes — one used `deposit`/`balance`, the other used `paid`) and it went undetected until specifically hunted for. Ask directly: "does anything else in this codebase read or write this same key, and does it assume the same shape?"

### Persona 2: The New Hire
**Mindset:** "I need to understand and modify this code in 6 months with zero context from the original author."
Unclear names, logic requiring 3+ files to understand, magic numbers, functions doing more than their name says, comments describing *what* instead of *why*.

### Persona 3: The Security Auditor
**Mindset:** "This code will be attacked. My job is to find the vulnerability first."
OWASP-informed: injection, broken auth, data exposure, insecure defaults, missing access control, dependency risk, secrets in code.

### Persona 4: The Auditor (new, added 2026-07-26)
**Mindset:** "Every number and status on this screen is a claim. Prove it or flag it."

This is the persona the original skill didn't have, and it's the single most common real defect class found across every SAIRN app audited so far — more common than the crash bugs the other three personas are built for.

**Review process:**
1. For every number, badge, or status indicator in the reviewed code: find the specific function that computes it. If none exists, or it's a hardcoded literal masquerading as live data, that's a CRITICAL finding — not a style note.
2. For every claimed integration or capability (SMS, GPS, cloud sync, user accounts, notifications): confirm real code actually implements it before letting a UI element imply it exists.
3. For every function with more than one plausible entry point (an add/create function and a separate render/display function): check that BOTH are actually wired to something real — a function that's dead code today can carry unreviewed fabrication into production the moment something later calls it.
4. Never suggest a replacement number without a real computation behind it. A null/zero/placeholder state is always safer to suggest than an invented one.

**You MUST find at least one issue or explicitly confirm every displayed value traces to a real function** — "looks fine" is not sufficient; state which specific functions you verified.

## Severity Classification

| Severity | Definition | Action Required |
|---|---|---|
| **CRITICAL** | Data loss, security breach, production outage, OR fabricated data presented as real. | Block merge. |
| **WARNING** | Likely to cause bugs in edge cases, degrade performance, or confuse maintainers. | Fix or explicitly accept risk with justification. |
| **NOTE** | Style issue, minor improvement, documentation gap. | Author's discretion. |

Promotion rule unchanged: a finding flagged by 2+ personas is promoted one severity level.

## Output Format

Structure your review as follows:

## Adversarial Review: [what was reviewed]

**Scope:** [files reviewed, lines changed, type of change]
**Coverage:** [full read of every changed file, or a sweep/sample —
  state which, and name anything excluded, same standard as our own
  Check 0b-coverage disclosure requirement — never imply full coverage
  that didn't happen]
**Verdict:** BLOCK / CONCERNS / CLEAN

### Critical Findings
[If any — these block the merge]

### Warnings
[Should-fix items]

### Notes
[Nice-to-fix items]

### Summary
[2-3 sentences: what's the overall risk profile? What's the single most important thing to fix?]

**Verdict definitions:**
- **BLOCK** — 1+ CRITICAL findings. Do not merge until resolved.
- **CONCERNS** — No criticals but 2+ warnings. Merge at your own risk.
- **CLEAN** — Only notes. Safe to merge.

## Anti-Patterns (unchanged from upstream — genuinely good as-is)

"LGTM, no issues found" is not an acceptable outcome — if nothing was found, look again. Don't hedge findings ("this might possibly be a concern") — state directly what's wrong. Don't review only changed lines — bugs live in the interaction between new and existing code.

## When to Use This

Before merging any PR, after a long session, when Claude says "looks good," or when something feels off — same as the original.
