# Skills marketplace — research findings

**2026-08-26. Research only. No packaging work started.**

## 1. The headline: there is no first-party way to sell a skill

**Established, not inferred.** Anthropic operates two marketplaces —
`claude-plugins-official` (curated) and `claude-plugins-community` (third-party,
after review and safety screening). Both are **free**. The `marketplace.json`
schema has **no payment, pricing, or entitlement fields**, and there is no
Anthropic-provided billing rail for plugins or skills. There is no storefront.
Every documented example of third-party distribution is free and open-source.

**Where I will not go further than the evidence.** The research surfaced this
line from Anthropic's legal-and-compliance docs:

> "Customers may not pay for, resell, or intermediate Claude usage on their end
> users' behalf. Each end user must authenticate with their own Anthropic API
> key, Claude subscription plan credentials, or 3P inference provider
> credential."

That clause is about **reselling Claude usage** — inference billed to you and
resold to someone else. A SKILL.md is a text file of instructions that the
buyer runs against **their own** Claude subscription; no Claude usage is being
intermediated. So the clause does **not**, on its face, prohibit selling a
skill. It is not a green light either — this is a licensed-attorney question,
not a session's call, and the same standing caveat applies as everywhere else
in this repo.

**The commercially useful conclusion is narrower and firmer than "you can't
sell them":** there is **no channel that will collect money for you**. Any
commercial model has to carry its own payment, licensing, and delivery — a
private git marketplace behind paid access, a consulting or retainer wrapper, or
a product that happens to include the skills. The distribution mechanism is
free by construction; monetization would sit entirely outside it.

## 2. What distribution actually requires

Mechanics, all documented:

- A **plugin** is a directory with `.claude-plugin/plugin.json` (`name` required,
  kebab-case; `version` optional but controls updates) and skills auto-discovered
  from `skills/<name>/SKILL.md`. Installed skills become `/plugin-name:skill-name`.
- A **marketplace** is a `.claude-plugin/marketplace.json` at a git repo root
  listing plugins. **Anyone can host one** — GitHub, GitLab, self-hosted, or a
  private repo with credential auth. Users add it with
  `/plugin marketplace add owner/repo`.
- Source types include relative paths, git URLs, npm packages, and **zip archives
  with optional SHA256 verification** — the last is the closest thing to a
  controlled artefact.
- **SKILL.md frontmatter:** `name` (≤64 chars, lowercase+hyphens) and
  `description` (≤1024 chars) are required. Optional and relevant here: `license`,
  `metadata`, `allowed-tools`, `compatibility`, `version` via the plugin.
- The **Skills API** (`/v1/skills`) is **workspace-scoped**, not a distribution
  channel — it shares skills within an org, not publicly.

**Practical read:** a private marketplace repo, access-gated, is technically
straightforward. The hard parts are legal and editorial, not mechanical.

## 3. Inventory — 22 skills, measured rather than asserted

Evidence proxies computed across the canonical store
(`C:/SAIRN/skills/sairn/`): dated corrections, cited commit SHAs, and
SAIRN-specificity (app names and table prefixes per 100 words of body text).

**Tier A — general-purpose, could stand alone.** Low SAIRN-specificity means
these already read as methodology, not internal documentation.

| skill | lines | SAIRN-specificity | what it solves |
|---|---|---|---|
| `sairn-grant-sweep` | 224 | **0.1%** | Auditing and narrowing excess Postgres/Supabase privileges — list-free discovery, revoke-then-grant, full-outer-join verification. Nothing in it is SAIRN-shaped. |
| `sairn-visual-review` | 79 | **0.1%** | Screenshot-and-review every panel with Playwright, because code review never sees the rendered app. |
| `sairn-silent-failure-sweep` | 42 | 0.6% | The one pattern behind most catastrophic bugs: something fails while showing success. Thin file, strong idea. |
| `sairn-session-handoff` | 159 | 0.6% | Cross-session handoff discipline. The naming-collision failure it documents is universal to any multi-agent setup. |
| `sairn-decision-gate` | 93 | 0.3% | Pursue-or-walk-away judgment (NIST AI RMF, Shipley, Klein premortem). **See §4 — third-party framework dependency.** |
| `sairn-adversarial-reviewer` | 82 | 0.4% | Four hostile review personas. **See §4 — MIT derivative.** |

**Tier B — general discipline, SAIRN-entangled implementation.** Extractable,
but that means a real rewrite, not a find-and-replace.

`sairn-guardian-v2` is the flagship and the hardest case: **1,000 lines, 43
dated corrections, and 117 SAIRN references.** Its *disciplines* are universal —
syntax-first Check 0, fabricated-KPI detection, the dormant-code rule, the
coverage-disclosure standard, and tonight's verify-after-cleanup rule. Its
*content* is an app map, a file map, and a numbered check list specific to 13
SAIRN apps. Also here: `sairn-software-architect`, `sairn-infra-debugger`
(general to the Supabase+Vercel stack), `sairn-forward-scan`,
`sairn-code-scrubber`.

**Tier C — SAIRN-specific, not standalone products.** `sairn-master-orientation`,
`sairn-portfolio-triage` (3.3%, highest), `sairn-parallel-app-scaling` (2.0%),
`sairn-app-scaffold`, `sairn-build-lifecycle`, `sairn-app-builder`,
`sairn-client-facing-design`, `sairn-mobile-sync`, `sairn-precommit-gate`
(routes to SAIRN skills by name), `sairn-training-needs-assessment`.

**`sairn-contract-drafter` — DO NOT PUBLISH, in any tier.** It quotes SAIRN's
real contract boilerplate verbatim and names the owner. It is internal-only by
construction.

## 4. Blockers found — all four are pre-publication, not pre-sale

**4.1 `sairn-adversarial-reviewer` is an MIT derivative.** Its own description
credits `alirezarezvani/claude-skills` (author ekreloff, MIT). MIT permits
commercial redistribution **but requires the copyright notice and licence text
to travel with the work**. Credit-by-name in a description is not that. There is
no `LICENSE` file in the directory. This is a compliance gap that has to close
before redistribution, paid or free.

**4.2 `sairn-decision-gate` builds on the APMP Body of Knowledge**, which is
copyrighted commercial material, alongside NIST AI RMF (US government, fine) and
Klein's premortem (a published method; the concept is not owned, the text is).
How much APMP substance is reproduced needs a read before this ships.

**4.3 `sairn-training-needs-assessment`** is cleaner than it looks — it
explicitly records that the Hennessy-Hicks 30 items could **not** be retrieved
and were not reproduced, so it carries methodology rather than the instrument.
But it markets a "DISC-style" module, and DISC is a trademark; "DISC-style" in a
commercial product is a trademark question.

**4.4 Seven skills carry content that must be scrubbed.** Mechanically scanned:
`sairn-app-builder`, `sairn-app-scaffold` (**plus a licence key**),
`sairn-guardian-v2`, `sairn-mobile-sync`, `sairn-session-handoff`,
`sairn-software-architect` all reference `github.com/SAIRN1` or
`sairn.vercel.app`; `sairn-contract-drafter` names the owner. None is a secret,
but all of it points at private infrastructure and none belongs in a shipped
artefact.

## 5. Proposed shortlist

**Lead with one, not six.** `sairn-grant-sweep` is the strongest candidate by
every measure taken: 224 lines, 0.1% SAIRN-specificity, built from three real
SQL files after a real incident, and it solves a problem every Supabase team has
and almost none has a method for. It needs the least work and carries no
third-party licensing entanglement.

**Second: `sairn-visual-review`** — same low specificity, and the gap it names
(code review never looks at the rendered app) is immediately legible to anyone.

**Third, and the real asset: a Guardian extraction.** Not Guardian as-is. The
verification disciplines it accumulated across 43 dated corrections — including
tonight's — are the genuinely valuable thing, and they are buried in a
SAIRN-specific check list. That is a rewrite measured in days, not an export.

**Deliberately not shortlisted:** anything in Tier C, `sairn-contract-drafter`
at all, and the two skills with unresolved third-party licensing (§4.1, §4.2)
until those are closed.

## 6. What to decide before any packaging starts

1. **Is there a business here at all**, given there is no channel that collects
   money? That is a `sairn-decision-gate` question and it should run before
   effort goes in, not after.
2. **Counsel on §1's policy clause** and on §4.1–4.3, as one question rather
   than four.
3. **Free-and-public vs private-and-gated.** These are different products. The
   free path is credibility and recruiting; the paid path needs its own rails.
