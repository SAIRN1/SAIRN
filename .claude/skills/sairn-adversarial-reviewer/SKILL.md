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
5. **AI-guessing-instead-of-calling-real-code (added 2026-07-29):** when an AI-generation function (builds a prompt, calls Claude) needs a number a deterministic function elsewhere in the file already computes, check whether it actually CALLS that function or just re-describes the logic in a prompt string and asks the AI to guess ("apply an 8% contractor discount," "apply 15% waste"). Found in StoneDesk's AI Instant Quote: a real tier-pricing/waste-multiplier/linear-foot system already existed, fully computed, in the canonical Quote Builder — the AI feature quietly re-implemented a weaker version in prose instead of calling it. This looks dynamic and plausible, unlike a hardcoded literal, but it's silently less accurate. An AI feature should call existing real functions for the numbers and use Claude only for what it's suited for — extracting unstructured input, writing narrative around a real result — never re-deriving math the codebase already gets right.
6. **Real function, wrong math — distinct from fabrication (added 2026-07-29).** A number backed by a genuine computation can still be simply incorrect: SAIRNbiz's Payroll panel computed the correct company-wide benefits total inside a loop, then multiplied it AGAIN by employee count outside the loop — an 8x inflation on a real, non-fabricated calculation. Confirming "a function exists and runs" (item 1) is necessary but not sufficient; independently re-derive the expected value by hand for at least one realistic case and compare, the same way a real bug hides behind real-looking code.
7. **Two differently-labeled KPIs sharing one undifferentiated calculation (added 2026-07-29).** SAIRNbiz's "This Month" and "Total Recorded" expense figures were the identical variable under two labels — no actual month-filter existed, just masked by thin seed data all falling in one month. When two metrics claim to measure different things (a period vs. a total, current vs. historical), verify the underlying calculation actually differentiates them — don't assume distinct labels imply distinct logic.

**You MUST find at least one issue or explicitly confirm every displayed value traces to a real function** — "looks fine" is not sufficient; state which specific functions you verified.

## Severity Classification

| Severity | Definition | Action Required |
|---|---|---|
| **CRITICAL** | Data loss, security breach, production outage, OR fabricated data presented as real. | Block merge. |
| **WARNING** | Likely to cause bugs in edge cases, degrade performance, or confuse maintainers. | Fix or explicitly accept risk with justification. |
| **NOTE** | Style issue, minor improvement, documentation gap. | Author's discretion. |

Promotion rule unchanged: a finding flagged by 2+ personas is promoted one severity level.

## Output Format
Adversarial Review: [what was reviewed]

Scope: [files reviewed, lines changed, type of change]
Coverage: [full read of every changed file, or a sweep/sample —
state which, and name anything excluded, same standard as our own
Check 0b-coverage disclosure requirement — never imply full coverage
that didn't happen]
Verdict: BLOCK / CONCERNS / CLEAN

Critical Findings
Warnings
Notes
Summary

## Anti-Patterns (unchanged from upstream — genuinely good as-is)

"LGTM, no issues found" is not an acceptable outcome — if nothing was found, look again. Don't hedge findings ("this might possibly be a concern") — state directly what's wrong. Don't review only changed lines — bugs live in the interaction between new and existing code.

## When to Use This

Before merging any PR, after a long session, when Claude says "looks good," on anything touching payments/data storage/status displays, when something feels off. Given Persona 4, this is now also the right tool specifically before calling any panel or feature "complete."

## Cross-References

- `sairn-guardian-v2` — the platform-wide mechanical check (syntax, dormant-panel resolution, multi-codebase drift). This skill reviews diffs/changes; Guardian sweeps whole files. Use both, not one instead of the other.
- `sairn-decision-gate` — for whether a finding here is severe enough to justify walking away from a decision entirely, not just fixing the code.
- Original upstream: `alirezarezvani/claude-skills`, engineering-team/skills/adversarial-reviewer, MIT license, author ekreloff. This adaptation adds Persona 4 and the coverage-disclosure requirement; everything else is the original design, credited accordingly.
