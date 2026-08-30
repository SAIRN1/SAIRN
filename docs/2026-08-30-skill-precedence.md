# Skill precedence — the four overlapping groups

**Written 2026-08-30 (CC), after a ground-truth audit of what is actually on
disk:** 52 skills in `~/.claude/skills/`, 23 of them SAIRN-prefixed and mirrored
in this repo, 29 general-purpose and user-level only.

**Scope of this note.** It sets precedence **for SAIRN work in this repo.** The
29 general skills live in the user-level store shared with every other project
on this machine, so nothing here claims what they should do elsewhere — and
nothing here is deleted. Precedence, not pruning.

**Each entry was read**, not inferred from its name. Where the audit expected a
duplicate and found a distinct tool instead, that is recorded as the finding,
because "these three look alike" was the assumption this note exists to test.

---

## 1. Design — four skills, and only two of them actually compete

| Skill | Where | Size | What it actually is |
|---|---|---|---|
| `sairn-client-facing-design` | repo + user | 7.0 KB | Audit and fix an **existing SAIRN app** so it reads as software a business would pay for. Tuned to SAIRN's one-brand-colour-per-app system |
| `frontend-design` | user only | 8.3 KB | Aesthetic direction for **new UI or a reshape** — typography, avoiding templated defaults |
| `design-taste-frontend` | user only | **87 KB** | Anti-slop skill for **landing pages, portfolios, redesigns**. Audit-first on redesigns, strict pre-flight check |
| `ui-ux-pro-max` | user only | 13.8 KB | A **searchable reference database** — 84 styles, 192 palettes, 74 font pairings, 98 UX guidelines, 22 stacks |

**Precedence for SAIRN work:**

1. **`sairn-client-facing-design` wins on any existing SAIRN app.** It is the
   only one that knows the brand system. Its own description already declares
   the split — *"Companion to the general frontend-design skill — that one
   covers building distinctive new designs from scratch; this one covers
   auditing and fixing an EXISTING app"* — so the boundary was authored
   deliberately and should be respected, not re-litigated.
2. **`frontend-design` for genuinely new UI** where no SAIRN convention exists
   yet.
3. **`design-taste-frontend` rarely applies here.** It is by far the largest of
   the four and it is scoped to landing pages, portfolios and marketing-site
   redesigns. SAIRN builds single-file B2B operational apps. Reach for it if a
   marketing site is ever built; do not reach for it to style a panel.
4. **`ui-ux-pro-max` does not compete with any of them.** It is a lookup asset,
   not a process. Usable *alongside* whichever of the above is driving.

**Real overlap is one pair only:** `frontend-design` vs `design-taste-frontend`.
Both exist to stop output looking templated. They differ by target, and for this
platform the smaller one is the right default.

---

## 2. Performance — the audit expected duplicates and found three layers

**No redundancy in this group. This entry corrects the audit's own initial
grouping.**

| Skill | Layer | Scope |
|---|---|---|
| `perf-profiler` | **Backend / runtime** | Slow endpoints, slow tasks, **slow queries**, memory and network bottlenecks. Reproducible baseline, graded evidence, explicit authorisation required before touching production |
| `performance` | **Frontend, broad** | Performance budget, critical rendering path, image and font optimisation, caching strategy, runtime |
| `core-web-vitals` | **Frontend, metric-specific** | LCP, INP and CLS individually, with measurement tools and framework-specific fixes |

`perf-profiler` was flagged as a possible duplicate on size alone (3.8 KB) and
is nothing of the kind — it is the only skill in the entire store covering
**server-side** profiling, which is where most SAIRN performance questions
actually live (`api/sd-data.js`, Supabase queries). It is also the only one that
insists on a reproducible baseline and refuses to invent timing numbers, which
matches this platform's fabrication discipline exactly.

`performance` and `core-web-vitals` are the same author (`web-quality-skills`),
same version, same licence — **shipped as a designed pair**, broad-then-deep,
not two attempts at one job.

**Precedence:** pick by layer, not by preference. Server-side symptom →
`perf-profiler`. Page feels slow generally → `performance`. A specific Core Web
Vital is the complaint → `core-web-vitals`.

---

## 3. Security — one genuine redundancy, and it is also stale

| Skill | Size | Status |
|---|---|---|
| `owasp-security` | 15.0 KB | **Canonical.** OWASP Top 10:**2025**, ASVS 5.0, LLM Top 10 (2025), Agentic AI (2026), UNSAFE/SAFE code patterns, and a "Before Reporting a Finding" gate |
| `security-auditor` | 2.0 KB | **Superseded — flagged for removal, see below** |

**`security-auditor` is not merely smaller, it is out of date.** Its "OWASP Top
10" section lists **XXE** and **Insecure Deserialization** as top-ten
categories. Those are the **2017** list; both were folded into other categories
in the 2021 revision and are not in the 2025 list `owasp-security` carries. A
skill whose headline framework is two revisions behind will produce findings
organised against categories that no longer exist.

Everything else it contains — injection, broken auth, access control,
misconfiguration, XSS, dependency CVEs, config review, password hashing, JWT,
RBAC — `owasp-security` covers in more depth, with runnable UNSAFE/SAFE
examples it does not have.

**Its one unique asset**, and the only reason not to treat it as pure
duplication: a fixed six-field reporting template — *Severity / Category /
Description / Impact / Remediation / References*. `owasp-security` has better
severity *guidance* (*"report severity by exploitability, not by pattern"*) but
no fixed output shape.

**Recommendation: remove `security-auditor`, after lifting that template into
`owasp-security`.** Not removed here — deletion is not mine to authorise. See
*Removal candidate* at the end.

**Note for SAIRN work specifically:** neither of these is the first stop.
`sairn-guardian-v2` (checks 22, 25, 26, 28) and `sairn-code-scrubber` are the
platform's own security passes and run first; `owasp-security` is the
general-knowledge layer underneath them.

---

## 4. Skill management — three links in one chain, not three copies

**No redundancy. They compose.**

| Skill | Size | Job |
|---|---|---|
| `self-improving-agent` | 7.2 KB | **Harvest.** Curate `MEMORY.md` into durable knowledge — promote proven learnings to `CLAUDE.md` and `.claude/rules/`, extract recurring solutions into skills |
| `skill-creator` | 33.7 KB | **Author.** Create, edit and optimise skills; run evals; benchmark trigger accuracy |
| `skill-vetter` | 3.5 KB | **Admit.** A security gate on **third-party** skills — detects malicious code before installation. `user-invocable: true` |

The apparent overlap is only in the word "skill". The real relationship is a
pipeline: `self-improving-agent` notices a pattern worth keeping →
`skill-creator` writes it properly → `skill-vetter` is what you run instead when
the skill came from **outside**, which is a supply-chain question and not an
authoring one.

`skill-vetter` is small because a gate should be. Size is not evidence of
redundancy here — the audit's size-based shortlist flagged it, and reading it
cleared it.

---

## Removal candidate — ONE, and not removed

**`~/.claude/skills/security-auditor/` — 2,037 bytes, user-level only.**

- **Superseded in substance** by `owasp-security` on every topic it covers.
- **Actively stale**: its Top 10 is the 2017 list.
- **One thing worth salvaging first**: the six-field reporting template.

**Not deleted, and not deleted by me.** It is user-level, shared with every
other project on this machine, and deletion authority sits with Michael. The
order matters too: lift the template into `owasp-security` **first**, confirm it
landed, then remove — otherwise the one useful part goes with it.

Everything else audited stays. Three of the four groups turned out to be
correctly-separated tools that a name-and-size scan made look like duplicates.

---

## What this note does not cover

- **The 29 general skills' behaviour in other projects.** They are user-level.
  This note governs SAIRN work only.
- **`grill-me`**, which is on disk but carries `disable-model-invocation: true`
  and is therefore user-invocable only. Not a defect and not in any of these
  groups — recorded because a session's available-skills list is not a complete
  inventory of what is installed, which is worth knowing before any future audit
  trusts that list.
