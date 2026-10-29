# Licensing product plan: agent control platform, verification report, skills package

**Written 2026-10-29 (cc). A planning document, not a decision.** Nothing in it is
built because of this document, nothing is priced, and nothing is offered to anyone.
Every price below is a **proposal**. Every repo count was produced by a command run
on 2026-10-29, and the command is given next to it.

**What existed before today and what is new.** Read this first, because the three
product names in the title are not equally real:

| Name | Existed in the repo before 2026-10-29? | What existed |
|---|---|---|
| **Skills marketplace package** | **Yes**, under the names "skill pack" and "skills marketplace" | A research doc, a decision-gate doc that **no-bid the paid path** (2026-08-26), a vet report, a claim-verification pass, and a **published free marketplace** with one skill in `dist/skills-public/sairn-skills/` |
| **Verification certificate** | **No.** `grep -rli "verification.certificate"` over `docs/` and the root `*.md` files returned nothing | The underlying tooling exists (gates, Tier A review, hover audit, defect register). The *product* is proposed here for the first time |
| **Agent control platform** | **No.** `grep -rli "agent.control.platform\|agent-control-platform"` returned nothing; `"agent control\|agent governance\|governance platform\|control plane"` matched only Anthropic's own vendored `claude-api` docs under `docs/skill-backups/` | The tools exist and run every day inside SAIRN. Treating them as a licensable product is proposed here for the first time |

So: one of the three has a recorded history, including a recorded **no** on selling
it. The other two are new framing over tooling that does exist. This plan does not
overturn the 2026-08-26 no-bid; §7 asks Michael whether to.

---

## 1. Summary

**What would be licensed.** The process-control layer SAIRN built to run four
AI build agents and one AI auditor on one codebase: push gates, claim locking, an
independent-review obligation on high-criticality code, a structurally separated
auditor role, a scoped and logged exemption mechanism, and the defect register those
produce. Packaged three ways:

1. **Agent control platform** (parent): the tooling, adapted to a customer's repo.
2. **Verification report** (module; called "verification certificate" in the brief,
   see §6 for why the word "certificate" should go): a dated, commit-pinned record
   of which checks ran against a customer's repo, what they found, and what they
   could not test.
3. **Skills package** (module): SKILL.md files for Claude Code, distributed through
   a plugin marketplace.

**To whom.** Small engineering teams (roughly 2 to 20 developers) that already let
Claude Code or similar coding agents commit to a real repo and have found, as SAIRN
did, that the agents' own reports of "done" and "passing" are not reliable. This is
a hypothesis about the buyer. **No buyer has been identified**; the 2026-08-26 gate
recorded "no buyer exists, no inbound demand recorded anywhere" and this pass found
nothing that changes that (`docs/DECISION-2026-08-26-skills-marketplace-gate.md`
line 16).

**Why now.** Two external changes since the August decision, both found in today's
research (§3), not in the repo:

- Agent governance became a priced product category from large vendors. Microsoft
  Agent 365 lists at **$15.00 user/month, paid yearly** on its own product page.
- Agent certification became a real, audited thing. AIUC-1 ("the technical
  certification for agent security") is audited by Schellman, valid one year,
  with quarterly retests, and coding-agent vendors have pursued it.

Neither change creates a SAIRN buyer. Both mean a buyer who exists now has a
vocabulary and a budget line for this, which they did not in August.

---

## 2. Product architecture

### 2.1 The parent: agent control platform

**What it actually is today:** a set of Python tools in `tools/`, git hooks, and
Claude Code hooks that run inside SAIRN's five clones. **It is not a product.** It
has no installer, no configuration surface, no customer documentation, and it is
wired to SAIRN-specific facts (licence seed files, app names, the four-session
roster). Measured scale, 2026-10-29:

| Measure | Value | Command |
|---|---|---|
| Python files in `tools/` | 362 | `ls tools/*.py \| wc -l` |
| ...of which define `main` | 328 | `ls tools/*.py \| xargs grep -l "def main" \| wc -l` |
| Distinct `CHECK n:` labels in the push gate | 25 (1 to 17, plus 4c, 4d, 5b to 5f, 12b) | `grep -o "CHECK [0-9][0-9a-z]*:" tools/sairn_push_gate_hook.py \| sort -u` |
| Lines in the push gate | 5,408 | `ast` read of `tools/sairn_push_gate_hook.py` |
| Skippable gate ids / of which wired / not skippable | 13 / 9 / 3 | `python tools/gate_skip.py --gates` |
| Rows in the bypass log | 138 | `wc -l < docs/BYPASS-LOG.jsonl` |
| Defect register records (since 2026-09-09) | 786 | `json.load` of `docs/defect-density-register.json`, `len(records)` |

The components, each grounded in a file:

| Component | File(s) | What it does (from its own docstring) | Status as a product |
|---|---|---|---|
| **Push gate** | `tools/sairn_push_gate_hook.py` | Pre-push checks "that must not depend on memory". Two entry points: a Claude Code PreToolUse hook on `git push` command text, and a real git `pre-push` hook, because the first cannot see pushes driven from Python | Runs daily in SAIRN. Many checks are SAIRN-specific (seed files vs live licence, app contrast tokens). **Not built** as a configurable product |
| **Scoped exemptions** | `tools/gate_skip.py`, `docs/BYPASS-LOG.jsonl` | One named gate at a time, a required reason, 30-minute expiry, logged. Three gates (credentials, hook-integrity, syntax) cannot be skipped. **Four declared ids are not wired**, and the tool says so itself | Runs. Generic in concept |
| **Claim locking** | `tools/sairn_claim.py`, `.claude/claims/<session>.json` | "Claim a work gate before running it, so two sessions do not." Built after two sessions duplicated about four hours of research on 2026-08-30. Claims expire after 4 hours (CLAUDE.md) | Runs. Close to generic: any multi-agent repo has the same problem |
| **Status registry** | `tools/sairn_status.py` | Shared working/blocked/idle rows, outside every clone so they are current without a fetch; `blocked` refuses without saying what it waits on | Runs. Generic |
| **Tier A independent review** | `tools/tier_a_review_gate.py`, `tools/tier_a_reviews_store.py` | Turns "high-criticality code needs a second reviewer" into a recorded obligation that blocks the push range until another session discharges it | Runs. Depends on SAIRN's criticality register (`docs/CRITICALITY-TIERS.md`, which is over the size ceiling and was not opened here) |
| **Separated auditor role** | `tools/hover_auditor_scope_gate.py` (prevent), `tools/hover_separation_audit.py` (detect), `.git/sairn-hooks/builder_auditor_deny_hook.py`; account in `docs/2026-09-15-hover-auditor-separation-enforcement.md` | A fifth agent that audits the four builders and may not write platform code; builders may not reach into its files. **The deny hook refused one of this session's own grep commands today** because the command text named the auditor's path | Runs. The idea is generic; the enforcement is path-based and SAIRN-shaped |
| **Landing verification** | `tools/landing_verification.py` | "Did the work LAND": pushed vs live, each clone's skills, upgrades. Exit 0 clean / 1 finding / **2 COULD NOT TELL**, never folded into a pass | Runs |
| **Controls on the controls** | `tools/sabotage_control_check.py`, `tools/scrutiny_ledger_check.py` | Checks that a negative control actually broke its target (a `str.replace` whose anchor stopped matching silently tests an unmodified file); checks every scrutiny-ledger row against the commit it names | Runs |
| **Defect register** | `docs/defect-density-register.json` | 786 records by detection method: code-review 332, independent-review 155, static-checker 93, hover-audit 70, live-verification 41, probe-control 37, fault-injection 30, mutation-testing 18 (top eight; `collections.Counter` on `detection_method`) | Data exists. **No reporting surface for a customer is built** |

**What the parent product would be:** the generic half of the rows above
(claims, status, scoped exemptions, Tier A obligation, auditor separation,
three-state exit codes, controls-on-controls), extracted, configurable per repo,
and installable into a customer's Claude Code setup as hooks plus a plugin.
**Not built.** The extraction is the same shape of work the August research called
"a rewrite measured in days, not an export" for Guardian
(`docs/SAIRN-SKILLS-MARKETPLACE-RESEARCH-2026-08-26.md` lines 139-142), multiplied by
the number of tools.

### 2.2 Module: verification report (brief's "verification certificate")

**Proposed, new today.** A fixed-scope engagement that produces a dated document
saying, for one customer repo at one commit:

- which checks ran (by name and version), with exit status;
- what each found, with file and line;
- **what could not be tested and why**, as a separate third state (the
  `landing_verification.py` 0/1/2 convention, and PR §1.11 in CLAUDE.md: "could not
  run" is never folded into "passed");
- the reviewer of record, and whether that reviewer was independent of the author.

What it could draw on today: the push gate's generic checks, `sairn-guardian-v2`
Check 0 (syntax and fabricated-KPI detection), `sairn-code-scrubber`,
`sairn-silent-failure-sweep`, `sairn-grant-sweep` for Postgres/Supabase privileges.
**What is not built:** a runner that executes those against a repo SAIRN does not
own, a report template, a signing or integrity mechanism for the report, and any
re-verification flow. Hash-chained logs and SLSA build provenance were **scoped**,
not shipped, as far as their titles show (`docs/2026-09-14-hash-chained-audit-logs-scoping.md`,
`docs/2026-09-18-slsa-build-provenance-scoping.md`; not read in full here).

**What it must never be:** an accredited certification. SAIRN is not a
certification body, holds no SOC 2 report, and has "no audit engagement, and no
observation period" (`docs/2026-09-26-soc2-readiness.md` lines 5-7). See §6.

### 2.3 Module: skills package

**This one has history and an artifact.**

- **Shipped (free):** `dist/skills-public/sairn-skills/` is a Claude Code plugin
  marketplace owned by "SAIRN Tech LLC", MIT licensed, listing **one** plugin,
  `postgres-grant-sweep` v0.1.0 (read from its `marketplace.json`). Its README states
  the validation scope honestly: "three real sweeps against one production Postgres
  database on Supabase, run by one operator".
- **Internal skills:** 34 directories under `.claude/skills/` (`ls -d .claude/skills/*/
  | wc -l`), one of which is the auditor's own skill and is out of scope for any
  package.
- **Vetted subset:** nine "SAIRN-original" skills rebuilt from incidents
  (`docs/skill-rebuild-specs/README.md` lines 1-27). The claim-verification pass
  checked **88 claims, 86 correct, 2 real errors fixed**
  (`docs/2026-08-30-skill-pack-claim-verification.md` line 7), verdict "ADMIT WITH
  CHANGES" for shipping, with four mechanical items outstanding (lines 105-114).
- **Known blockers recorded in August:** an MIT-derivative skill with no LICENSE
  file, APMP copyrighted material in `sairn-decision-gate`, a DISC trademark
  question, and seven skills carrying private infrastructure references, one with a
  licence key (`docs/SAIRN-SKILLS-MARKETPLACE-RESEARCH-2026-08-26.md` lines 100-126).
  `sairn-contract-drafter` is "DO NOT PUBLISH, in any tier" (line 96).
- **Recorded decision:** paid path **no-bid at 18/80 (22.5%)**, free path go at
  59/80 (74%), conditionally and for one skill
  (`docs/DECISION-2026-08-26-skills-marketplace-gate.md` lines 24-26, 95-121).
- **Recorded positioning:** the sairntech.com scoping recommends the pack as a
  **free credibility asset** on an About/Engineering page, not a catalog product
  (`docs/2026-08-30-sairntech-corporate-site-scoping.md` lines 65-93;
  `docs/2026-08-30-sairntech-shell-and-inquiry-scoping.md` lines 157-169).

**In this plan:** the skills package sits under the parent as the distribution
channel. The plugin format is how hooks and skills get into a customer's Claude Code
install, so the parent product would ship *as* a plugin from a private marketplace.
Whether any skill is ever sold on its own is left as an open decision (§7), with the
August no-bid standing until Michael changes it.

---

## 3. Competitor and pricing research

**Researched 2026-10-29** with web search and direct fetches of vendor pages. A price
appears only where it was read on a page; "not published" means the vendor page was
fetched and showed none. Third-party roundups that quoted prices the vendor page did
not show are noted but not used.

### 3.1 Agent governance and control

| Vendor | What it does | Published pricing | Source |
|---|---|---|---|
| Microsoft Agent 365 | Central place for IT and security teams to monitor, protect and manage AI agents across an organisation | **$15.00 user/month, paid yearly** | https://www.microsoft.com/en-us/microsoft-agent-365 |
| Credo AI | AI governance: discover, risk-manage and govern AI systems, agents, models and vendors | Not published ("Request demo") | https://www.credo.ai/ |
| Zenity | Security and governance for AI agents across SaaS, custom agent platforms and endpoints | Not published ("Get a Demo") | https://zenity.io/ |
| Airia | Agent platform with runtime governance controls | Not found on the vendor site: the pricing URL redirects to a usage-limits doc with no prices. Third-party listings quote $50 and $250/month tiers and disagree on limits; **not used** | https://airia.ai/docs/building-and-deploying-agents/interface-options/usage_limits |
| Trustible, Holistic AI | AI governance platforms | Not published per review/aggregator sites (vendor pages not fetched) | https://www.g2.com/products/holistic-ai/pricing |
| Langfuse (adjacent: observability) | Open-source tracing, prompt management and evaluation for LLM apps and agents | Hobby free; Core $29/month; Pro $199/month; Enterprise $2,499/month | https://langfuse.com/pricing |
| CodeRabbit (adjacent: AI code review gate) | AI review on pull requests | Annual: Essentials $24, Team $48, Advanced $72 per developer/month; monthly: $30, $60; Enterprise contact | https://www.coderabbit.ai/pricing |

**Read across the table:** the named governance platforms sell to enterprises and do
not publish prices; the two published per-seat anchors near SAIRN's buyer are
$15/user/month (Microsoft, inside a Microsoft estate) and $24 to $72/developer/month
(CodeRabbit). None of the governance vendors fetched describes repo-level
push gates, claim locking between concurrent coding agents, or a separated auditor
agent. That is an observation from their landing pages, not a feature audit.

### 3.2 AI audit, assurance and certification

| Vendor / scheme | What it does | Published pricing | Source |
|---|---|---|---|
| AIUC-1 | "The technical certification for agent security"; six risk domains; accredited third-party auditor; certificate valid 1 year; quarterly retests | Not published ("Begin Certification") | https://www.aiuc-1.com/ |
| Schellman | First accredited AIUC-1 auditor (per the AIUC-1 site); also sells ISO 42001 | Not published (not found in search results) | https://www.aiuc-1.com/ |
| BSI | ISO/IEC 42001 certification; states it was the first certification body accredited by UKAS for 42001 | Not published (quote form) | https://www.bsigroup.com/en-US/products-and-services/standards/iso-42001-ai-management-system/ |
| Vanta | Compliance automation; lists ISO 42001 among frameworks | Not published ("Get personalized pricing") | https://www.vanta.com/pricing |
| ISMS.online (estimate, not a certifier) | Compliance platform vendor publishing cost ranges | **Its own estimates**: total £8,000-£50,000; Stage 1 £2,000-£6,000; Stage 2 £3,000-£15,000; annual surveillance £1,500-£5,000. Not a quote, and published by a party that sells the preparation | https://www.isms.online/iso-42001/certification/certification-cost/ |

The repo's own September research reached the same place independently:
A-LIGN, Schellman, BarrAdvisory and Barnes Dennig sell combined SOC 2 + ISO 42001
programmes, flagged there as "vendor-sourced, lower confidence"
(`docs/cloud-research/soc2-readiness-deep-research-2026-09-25.md` lines 854-861).

### 3.3 Claude / agent skill and prompt marketplaces

| Vendor | What it does | Published pricing | Source |
|---|---|---|---|
| Anthropic Claude Code plugin marketplaces | Any git repo with `.claude-plugin/marketplace.json`; can be private; an org admin can require it on every machine; public directory by submission | Free. The documented `marketplace.json` fields shown (`name`, `owner`, `plugins`, `source`, `description`) include nothing for price or entitlement | https://code.claude.com/docs/en/plugin-marketplaces |
| SkillHQ | Paid marketplace for SKILL.md packages and Custom GPT configs | Seller keeps 80% (Starter) or 85% (Pro); no listing fee; Stripe processing 1.5% + €0.25 (EU) / 3.25% + €0.25 (non-EU); minimum skill price €2.00 | https://skillhq.dev/become-seller |
| MCP Market | "Turn any agent skill into a paid listing", seller-set price per install | Commission not stated on the seller page | https://mcpmarket.com/sell |
| PromptBase | Prompt marketplace | Could not read: FAQ returned HTTP 403 | https://promptbase.com/faq |

**Unresolved and not used:** several SEO blogs claim Anthropic launched a paid Skills
Marketplace taking 15%; another guide says no such store exists. No Anthropic page
fetched today confirms it. The plugin-marketplace docs above describe free,
self-hosted distribution only.

---

## 4. Pricing proposal (all figures are proposals)

The anchors are the published numbers in §3. Where a number below is not derived
from an anchor, it says so.

| SKU | Proposed form | Proposed price | Rationale |
|---|---|---|---|
| **Agent control platform, design-partner pilot** | Setup engagement, billed as dev services, software at no charge for 90 days | Setup billed at SAIRN's services rate. **No rate is recorded in the repo** (sairntech scoping §9 item 5: pricing "entirely unscoped"), so no figure is proposed here | The product does not exist until a customer's repo forces the extraction. Charging a licence fee for an un-extracted tool would be selling the August "product is not real" gap (`DECISION-...` line 17) |
| **Agent control platform, licence (after Phase 3 exit)** | Per developer seat, annual | **Proposal: $40/developer/month, annual**; floor 5 seats | Above Microsoft Agent 365's $15 (which governs agents inside a Microsoft estate, not repo pushes) and inside CodeRabbit's $24-$72 band for a per-developer gate on code. Placed below CodeRabbit Team ($48) because SAIRN has no track record outside one codebase. The exact figure is a judgment, not a derivation |
| **Verification report, one repo, one commit** | Fixed-fee engagement | **Proposal: $3,000 per report; $1,000 per re-run within 90 days** | Deliberately well under ISMS.online's own £2,000-£6,000 *Stage 1* estimate for ISO 42001, because this is **not** a certification and must not be priced like one. It must still cover a real manual reading of findings, which is where SAIRN's own record shows the time goes (ten check-bugs per real finding, `skill-pack-claim-verification.md` lines 56-76) |
| **Skills package** | Free public marketplace (status quo) plus inclusion in the platform licence | **$0 standalone** (keeps the August decision); bundled in the seat price | SkillHQ's published floor is €2 with 15-20% commission, and the only documented Anthropic channel collects nothing. The August gate found the paid path's deciding gap was the absence of a buyer, not of a payment rail; nothing found today supplies a buyer |

**What is deliberately not proposed:** a per-agent price (no published anchor found
for one), any enterprise tier (no support capacity, §6), and any price for the
auditor role as a separate SKU (it is SAIRN-internal and its skill path is out of
bounds for build agents).

---

## 5. One-page pitch outline

**Problem.** Teams that let coding agents commit find the agents report "done",
"passing" and "verified" for work that is none of those. Silence and false success
look identical in a log.

**Solution.** A control layer between the agents and `main`: push gates that fail
closed when a tool they depend on is missing, claims so two agents do not duplicate
work, a recorded second-review obligation on the code that matters most, an auditor
agent that cannot write the code it audits, and exemptions that are scoped to one
gate, require a reason and expire.

**Proof points (each checkable in the repo; quote them with the command):**

1. The push gate has 25 distinct check labels and two entry points, because the
   Claude Code hook alone cannot see a push driven from Python
   (`tools/sairn_push_gate_hook.py` docstring).
2. 13 skippable gate ids, 3 that cannot be skipped, and the tool itself prints which
   4 are declared but not wired, rather than hiding it (`python tools/gate_skip.py
   --gates`).
3. 786 defect records since 2026-09-09, 70 of them found by the separated auditor
   and 155 by independent review (`docs/defect-density-register.json`).
4. The free skill marketplace exists and states its own validation limits
   (`dist/skills-public/sairn-skills/README.md`).
5. Claim-verification of the skill pack: 88 claims, 86 correct, 2 errors fixed
   in place and left visible.

**Do not use as proof points:** "battle-tested" without "one codebase, one operator,
one stack"; any count not re-run on the day of the pitch; any comparison to
AIUC-1 or ISO 42001 other than "this is not that".

**Who buys.** Hypothesis: the engineering lead of a 2-20 developer team already
running Claude Code agents against a production repo. Not validated.

**Pricing.** §4, presented as pilot terms first.

**Ask.** One design partner for a 90-day pilot on their repo, in exchange for the
right to describe the outcome (with their approval) and their feedback on whether
they would pay the §4 seat price.

---

## 6. Sequencing against dev services, and risks

### 6.1 What the repo says about dev services

`grep -rli "dev services\|dev-services\|services revenue"` over `docs/` and root
`*.md` matched **one** file, a competitor's revenue figures in
`docs/cloud-research/sairnbiz-external-competitive-gap-audit-2026-09-26.md` line 351.
There is no SAIRN dev-services plan under that name. The nearest thing is the
**"custom work"** funnel in the sairntech.com scoping (2026-08-30): "a custom
app/website-building service with its own structured inquiry flow", sequenced
**first**, because it "needs nothing else to exist"
(`docs/2026-08-30-sairntech-corporate-site-scoping.md` lines 5-7, 230-235).
`git log --grep=sairntech` shows only docs commits; no site, page or inquiry
endpoint was found in the repo root or `api/`. This pass found no record of
services customers or revenue; it did not look outside the repo.

### 6.2 Phases

The licensing line rides on dev services, not ahead of it: the first customer for
the control platform should be a services customer whose repo SAIRN is already
working in.

| Phase | What happens | Entry criteria | Exit criteria |
|---|---|---|---|
| **0. Hold** (now) | Nothing sold. Two cheap preparations: counsel question list extended to cover §6.3 items 1-3; the four mechanical items from the claim-verification pass closed for the nine-skill pack | Michael approves this plan's direction | Counsel answer on the Anthropic usage clause and on the word "certificate"; vet items closed and re-run |
| **1. Credibility** | Publish more of the vetted skills free, one at a time, per the August condition 5 ("one published skill, then stop and look") | Phase 0 exit; sairntech.com About/Engineering page exists (it does not yet) | Measured evidence of external use or inbound interest that names the skills. If none after a set review date, stop at Phase 1 |
| **2. Pilot inside dev services** | Install the generic control tooling on one services customer's repo, as part of a paid build engagement; produce one verification report for that repo | A signed dev-services customer; the generic tools extracted enough to run outside SAIRN's clones | The tools ran on a second codebase; a report was delivered; the customer said in writing whether they would pay for it separately |
| **3. Standalone licence** | Offer the §4 seat licence and per-report SKU | Phase 2 exit with a yes; a support owner named; a private marketplace with access control | First paid licence; an incident and rollback path exists for a bad release (the August RMF "Manage" gap) |

### 6.3 Risks

1. **Representing a verification report as a certification.** The repo already
   records why this is the near-term legal risk: FTC actions against misrepresented
   certification and seal programmes (SecurTest, ControlScan, TRUSTe, the Safe
   Harbor settlements), and the rule that "the actionable conduct is the claim"
   (`docs/2026-09-26-soc2-readiness.md` lines 237-264). Mitigation: rename the SKU
   away from "certificate"; put "not a certification, not an audit, not accredited"
   in the first paragraph of every report, as the SOC 2 readiness doc does for
   itself; never reference ISO 42001, AIUC-1 or SOC 2 except to say the report is
   not one of them; run `sairn-decision-gate` before any external wording.
2. **Validation scope.** Every tool and skill has run against one codebase, one
   operator, one stack (`DECISION-...` lines 80-85). Selling it as proven elsewhere
   would be the fabricated-authority pattern Guardian Check 0b exists to catch.
3. **Independence is weaker than the names suggest.** "Independent review" and the
   "hover auditor" are other agent sessions, not human third parties, and all roles
   commit through one git identity (`tools/hover_separation_audit.py` docstring:
   "There is no author field to group by"). A report must say who reviewed, and that
   the reviewer is an AI session under the same operator.
4. **Anthropic terms.** The usage-policy clause on reselling Claude usage was judged
   not to reach a markdown file on its face, but was never read by counsel
   (`SAIRN-SKILLS-MARKETPLACE-RESEARCH-...` lines 14-28). A platform that runs agents
   on the customer's behalf is closer to that clause than a skill file is.
5. **Platform churn.** Plugin format, hook semantics or skill invocation can change
   under a paying customer (August premortem item 2). Today's docs fetch shows
   features gated on specific Claude Code versions, so this is live, not theoretical.
6. **Third-party content.** MIT attribution, APMP and DISC items from August remain
   open until shown closed.
7. **Attention.** The August gate's premortem item 1: effort on licensing taken from
   work with a real customer attached. Phase 2's entry criterion exists to prevent
   that.
8. **SAIRN-specific gates leaking into a customer product.** The seed gate, contrast
   gate and path-scope gate encode SAIRN facts; shipping them unmodified would fail
   or mislead in another repo.

---

## 7. Open decisions for Michael

1. **Revisit the 2026-08-26 paid-path no-bid?** It said to revisit "only if inbound
   demand appears unprompted". This plan found no such demand. Recommendation: keep
   the no-bid for standalone skills, and treat the platform licence as a separate
   question gated on Phase 2.
2. **Name of the verification SKU.** Recommendation: "verification report" or
   "evidence report", not "certificate". Counsel to confirm.
3. **Is the control platform a product at all, or only a capability inside dev
   services?** Phase 2 is designed to answer this with evidence; the decision is
   whether to start down that road.
4. **Services rate and Phase 2 pilot terms.** No rate exists in the repo.
5. **Which skills to publish next in Phase 1**, and the review date the August
   condition 5 requires.
6. **Support owner.** A licence implies support; there is no named owner today.
7. **Counsel scope.** One combined question: Anthropic usage clause applied to a
   control platform; "certificate" wording; MIT/APMP/DISC items.
8. **Whether `sairn-decision-gate` should be run formally on this plan** before any
   external conversation. Recommendation: yes, on the Phase 2 pilot offer.

---

## 8. Sources

### 8.1 Sources in this repo

| File | Lines used | For |
|---|---|---|
| `docs/SAIRN-SKILLS-MARKETPLACE-RESEARCH-2026-08-26.md` | 5-35, 60-126, 128-157 | No first-party payment rail; usage-clause reading; skill tiers; blockers |
| `docs/DECISION-2026-08-26-skills-marketplace-gate.md` | 14-32, 40-63, 80-91, 95-143 | Paid no-bid 22.5% vs free go 74%; premortem; RMF findings; conditions |
| `docs/2026-08-30-skill-pack-claim-verification.md` | 7, 56-76, 96-118 | 88/86/2 claim check; remaining shipping items |
| `docs/skill-rebuild-specs/README.md` | 1-45, 97-105 | Nine-skill pack and its narrow claim |
| `docs/2026-08-30-sairntech-corporate-site-scoping.md` | 1-35, 65-93, 230-255 | Custom-work funnel; skill pack as credibility asset; sequencing |
| `docs/2026-08-30-sairntech-shell-and-inquiry-scoping.md` | 20-34, 157-169 | About/Engineering page carries the skill pack |
| `docs/2026-09-26-soc2-readiness.md` | 1-30, 237-283 | Not-a-claim framing; FTC misrepresentation line; ISO 42001 applicability |
| `docs/cloud-research/soc2-readiness-deep-research-2026-09-25.md` | 829-861 | ISO 42001 structure; combined SOC 2 + 42001 vendors |
| `docs/2026-09-15-hover-auditor-separation-enforcement.md` | 1-30 | Why the auditor's separation is mechanical |
| `dist/skills-public/sairn-skills/` (`marketplace.json`, `README.md`, `LICENSE`) | whole (small) | The shipped free marketplace |
| `tools/sairn_push_gate_hook.py`, `tools/gate_skip.py`, `tools/sairn_claim.py`, `tools/tier_a_review_gate.py`, `tools/landing_verification.py`, `tools/sabotage_control_check.py`, `tools/scrutiny_ledger_check.py`, `tools/hover_separation_audit.py`, `tools/claim_provenance.py` | module docstrings | Component descriptions in §2.1 |
| `docs/defect-density-register.json`, `docs/BYPASS-LOG.jsonl` | measured, not read | Counts in §2.1 and §5 |
| `CLAUDE.md` | push protocol, claims, PR §1.11 | Claim expiry, fail-closed rule |

Titles cited but **not read** in this pass: `docs/2026-09-14-hash-chained-audit-logs-scoping.md`,
`docs/2026-09-18-slsa-build-provenance-scoping.md`, `docs/2026-09-13-claim-provenance-chain-design.md`,
`docs/CRITICALITY-TIERS.md` (over the size ceiling).

### 8.2 External sources (all accessed 2026-10-29)

- Microsoft Agent 365: https://www.microsoft.com/en-us/microsoft-agent-365
- Credo AI: https://www.credo.ai/
- Zenity: https://zenity.io/
- Airia usage limits (pricing URL redirect target): https://airia.ai/docs/building-and-deploying-agents/interface-options/usage_limits
- Holistic AI on G2: https://www.g2.com/products/holistic-ai/pricing
- Langfuse pricing: https://langfuse.com/pricing
- CodeRabbit pricing: https://www.coderabbit.ai/pricing
- AIUC-1: https://www.aiuc-1.com/
- BSI ISO/IEC 42001: https://www.bsigroup.com/en-US/products-and-services/standards/iso-42001-ai-management-system/
- Vanta pricing: https://www.vanta.com/pricing
- ISMS.online ISO 42001 cost: https://www.isms.online/iso-42001/certification/certification-cost/
- Claude Code plugin marketplaces: https://code.claude.com/docs/en/plugin-marketplaces
- SkillHQ seller terms: https://skillhq.dev/become-seller
- MCP Market seller page: https://mcpmarket.com/sell
- PromptBase FAQ (HTTP 403, not read): https://promptbase.com/faq
