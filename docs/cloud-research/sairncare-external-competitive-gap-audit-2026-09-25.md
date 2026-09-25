# Worldwide external competitive-gap audit — SAIRNcare

**Sourcing caveat, read this before anything else below:** this session's
outbound network could not reach any vendor, trade-press, or patent-office
domain. Every vendor-attributed fact in this document is a `WebSearch`
index snippet of that vendor's own domain, not an opened page — one grade
below this series' normal standard. Full disclosure and the direct test
evidence are in §0.

**Research pass, 2026-09-25. No code written, no app file touched.**
Written by a standalone cloud session under `docs/cloud-research/` per
instruction (new files only, new branch, no PR). **No internal
competitive-gap re-derivation document existed for SAIRNcare on `main`
before this pass** — unlike SAIRNvet, SAIRNlaw, and SAIRNmechanical, which
each already had one. §1 below is therefore this document's own internal
grounding, done directly against `sairncare.html`, `api/_resources/sairncare.js`,
`api/sd-data.js`, and `docs/CRITICALITY-TIERS.md` — marker counts, then a
hand-read of every non-zero hit, this series' own standing method — not a
restatement of a prior document.

**Method and standard**: the reference for this series is
`docs/superpowers/specs/2026-09-02-stonedesk-worldwide-competitive-gap-audit.md`
— every competitor claim read from the vendor's own site, not a comparison
article; aggregator pages used only to find vendors; a failed fetch
recorded as a failure, never filled in; pricing only from a vendor's own
pricing page, and where no vendor publishes one, that absence is reported
as a market fact, not filled in from an aggregator's guess.

---

## 0. A material limitation, stated before anything else

**This session's outbound network cannot reach any vendor, trade-press, or
patent-office domain**, confirmed directly by a blocked `WebFetch` to
`pointclickcare.com` against a healthy proxy status (`enabled: true`,
`bundleCoversEveryHost: true`, zero recent relay failures, a fresh proxy
instance on port 37503 — distinct from the ports seen in this series'
prior sessions, confirming this is not a one-off fluke but a persistent
destination-level policy). Per the proxy documentation's own instruction
on a blocked host — *"Do not retry or route around it — report the
blocked host"* — that instruction is followed here rather than worked
around.

**Evidence grade**: every vendor-fact cell below is a `WebSearch` result
restricted to the named vendor's own domain via `allowed_domains` — the
search engine's indexed excerpt of that page, not the page itself. This is
one grade below this series' own standard and is marked as such
throughout. **Nothing here should be quoted externally — to a facility
operator, in a pitch, in a proposal — without a follow-up pass from a
network that can reach these domains.** Pricing figures sourced only from
aggregators (Capterra, SoftwareFinder, ITQlick, GetApp) rather than a
vendor's own page are marked as aggregator estimates, not vendor-confirmed
prices, per this series' standing rule that pricing is only ever taken
from a vendor's own pricing page. Two figures surfaced during this pass
could not be pinned to a clean source URL at all (an AI-adoption
statistic and an investment-size claim) and are excluded from anything
stated as fact — see §4.

Retrieval date for every row below: 2026-09-25.

---

## 1. What SAIRNcare is, established directly against the code (no prior
internal document exists to anchor against)

- **Assisted living (ALF), deliberately not skilled nursing.** The v1
  scope document (`docs/superpowers/specs/2026-08-20-sairncare-v1-scope.md`)
  states MDS, PDPM, election statements, and other SNF/hospice-specific
  requirements are out of scope by design, not by omission — the same
  kind of stated scope boundary this series has found and respected in
  other apps (SAIRNmechanical's HVAC-only scope, StoneDesk's residential
  focus).
- **Thirteen registered resources, twelve Tier A**, `docs/CRITICALITY-TIERS.md:54` —
  the highest Tier-A-to-total ratio this series has seen in a
  re-derivation. Several resources carry real PHI (Protected Health
  Information) and were re-tiered upward as recently as 2026-09-22 and
  2026-09-25 specifically because a resident-linked row (activity
  attendance) was read individually and found to answer "where was an
  identifiable resident and what did they do in a care facility" —
  `docs/CRITICALITY-TIERS.md:168-172`.
- **MAR (Medication Administration Record) is real and regulation-aware.**
  A genuine status vocabulary — given / refused / held / not available
  (`sairncare.html:469`) — with PRN tracking (18 hits) and a documented,
  in-app-stated distinction between refusing a single dose (logged as a
  Refused administration entry) and refusing the underlying care
  assessment itself, citing **Minnesota Stat. 144G.71** by section number
  (`sairncare.html:512`). **No controlled-substance running-balance or
  witness/co-sign register exists** — only a yes/no flag on a medication
  order (`sairncare.html:453`, `Controlled Substance? Yes/No`). No
  diversion-count workflow of any kind.
- **Billing correctly separates private-pay from Medicaid HCBS waiver
  claims, and never conflates them.** Room & board is always private-pay;
  the care-level rate is billed privately unless the facility both accepts
  Medicaid HCBS waiver AND the specific resident's payer is set to it
  (`sairncare.html:999-1022`) — the same discipline this series flagged as
  a strength in SAIRNmechanical's refusal to conflate its two federal
  refrigerant rules. A real, append-only payer-routing audit trail exists
  (`alf_claim_routes`, `api/sd-data.js:10101`) with honest
  not-provisioned-vs-empty messaging when the underlying table hasn't been
  set up (`sairncare.html:3317-3318`).
- **Compliance has a real Jurisdiction Requirements rules engine — seeded
  for four states.** Ohio, Indiana, Michigan, and Pennsylvania, each with
  real cited staffing ratios, dementia-training-hour requirements, and
  licensure rules, and a state-specific staffing checker
  (`sairncare.html:776-806`). **Any state outside those four fails closed
  with an explicit "not seeded" result rather than guessing** — the app's
  own code comment states the reasoning directly: *"No two of those four
  share a licensure model, a staffing METHOD, or a training-hour
  structure, so there is deliberately no 'default' shown for an unseeded
  state — it fails closed and says so"* (`sairncare.html:775`).
- **Incident reporting has real, cited per-state deadline awareness.** A
  per-facility configurable state-reporting-deadline field, with the
  app's own note citing real confirmed examples — Virginia 24 hours,
  Massachusetts 24 hours, California 7 days, Florida 15 days, Washington
  initial report plus 5 business days follow-up — and an explicit
  admission the survey "was not exhaustively surveyed," instructing the
  user to set the real deadline rather than assume one of the examples
  applies (`sairncare.html:806`). Incident categories include fall (with
  injury), medication error, and elopement/wandering — but these are
  **reactive** entries logged after an event, not a proactive
  risk-assessment tool.
- **Staff certification tracking is real**: cert expiry, background-check
  field, and status, surfaced on the Compliance panel's own table.
- **Zero markers for a family/resident-facing portal.** `family_portal`
  and every variant searched returned nothing — this is a staff-only
  application with no resident- or family-facing surface at all.

---

## 2. What the market does, against each open item

### 2.1 Named vendor landscape

| Vendor | Facility scope | Pricing model | Top-line claim |
|---|---|---|---|
| PointClickCare | SNF + senior living broadly, not ALF-exclusive | No published rate card; aggregator estimates only (~$300+/user/month, or $500–$15,000+/month tiered by facility size — not vendor-confirmed) | Senior Living EHR platform; relies on an 8+-vendor marketplace for family/resident engagement rather than a built-in portal |
| MatrixCare | LTPAC + senior living + life-plan communities | Custom quote; "4,700+" facilities claimed | Being sold by ResMed to Frazier Healthcare Partners for $490M, announced ~July 2026 (see §4) |
| American HealthTech / Netsmart (myUnity) | Post-acute/senior living, cross-setting (independent/assisted/memory care, CCRC, home health, hospice) | Custom quote | Acquired by PointClickCare from CPSI, January 2024 |
| Yardi Senior Living / eMAR | ALF, memory care, SNF, CCRC | Custom quote | eMAR is **DEA EPCS-certified** (electronic prescribing of controlled substances) — a real, vendor-confirmed controlled-substance capability, on the prescribing side, not diversion-count reconciliation |
| Eldermark | Senior housing / ALF | Aggregator estimate only, ~$100–500/user/month (not vendor-confirmed) | EHR + eMAR + CRM + billing bundle |
| ECP | ALF, memory care, IDD/group homes, independent living — explicitly ALF-focused, not SNF | Custom quote; no published rate card | Claims compliance support "in all 50 U.S. states," 8,500+ communities, dedicated per-state landing pages |
| Aline (Aline Engage / Family App) | ALF, SNF, referral management | Not published | Ships a named family-engagement module; **its relationship to ECP could not be confirmed from search** — both `ecp123.com` and `alineops.com` are live, separate-looking sites today, and this pass does not assert a merger history it cannot verify |
| ALIS (Medtelligent) | ALF, memory care, independent living | Only vendor with anything resembling a real figure, and even that is aggregator-sourced, not from ALIS's own pricing page: $8–15/resident/month, $300/month single-community minimum ($190/month multi-community), $650–3,500 one-time onboarding | Modular: CRM, Clinical & eMAR, RevOps, HQ analytics, and a named family-engagement module ("ALIS Connect") |
| CareVoyant | Home care / private-duty nursing / HCBS — **adjacent market, not core ALF facility management** | Not published | Markets a dedicated narcotics-count-tracking feature (start/end-of-shift entry, running count, diversion prevention) — the clearest positive evidence found anywhere in this pass for §2.2, but from outside SAIRNcare's actual peer set |
| Sandata | State-mandated EVV aggregator for Medicaid HCBS waivers (e.g. Ohio's Assisted Living Waiver) | N/A — state infrastructure | Relevant only as backend infrastructure some states require alongside HCBS billing, not a facility-management competitor |

Most of the well-known names span SNF plus ALF plus more, rather than
being ALF-exclusive; ECP and ALIS read as the two most purpose-built ALF
platforms in this set.

### 2.2 Controlled-substance / diversion register — a real compliance
requirement, moderate-confidence gap

ECP's own compliance page states state surveyors specifically check
**"controlled substance logs"** as one of four core audited areas —
confirming this is a real, named requirement in the ALF regulatory
environment, not a hypothetical. No vendor-domain search (PointClickCare,
MatrixCare, Eldermark, ALIS, ECP, Yardi, Netsmart) surfaced a **named,
dedicated running-balance-plus-witness-signature register** as a marketed
product feature. The clearest positive evidence for this shape of feature
comes from CareVoyant, in the adjacent home-care/private-duty-nursing
market, not core ALF. Independent best-practice sources confirm
double-signature narcotic counts are standard *operational* practice in
ALF settings, and paper count-sheet templates remain in active
circulation — suggesting this is often still handled off-platform even
where a full EHR is in use. **This is reported as a real, evidenced, but
not conclusively proven gap**: a vendor's marketing page staying silent
about a feature is weaker evidence than a positive confirmation either
way, and SAIRNcare's own posture (a yes/no flag, no register) may be
closer to the market's actual norm than to an outlier.

### 2.3 Multi-state compliance breadth — this one cuts against
SAIRNcare, reported honestly rather than softened

ECP explicitly markets **"compliant in all 50 U.S. states"** as a named
differentiator, with dedicated per-state landing pages. Measured purely
on breadth, SAIRNcare's four-state Jurisdiction Requirements engine (Ohio,
Indiana, Michigan, Pennsylvania) is genuinely thin next to a real
competitor's claimed coverage — this is not a case, like SAIRNmechanical's
CARB finding, of a gap the market hasn't solved either. **What could not
be verified**: whether ECP's fifty state pages carry real cited statute
sections, staffing ratios, and training-hour requirements the way
SAIRNcare's four seeded states do, or whether they read as state-specific
SEO/marketing content layered on a thinner or absent rules engine —
ECP's own site was not opened, only search-indexed. **SAIRNcare's only
defensible counter-claim is depth and honesty (real citations, and an
explicit fail-closed result for anything unseeded) rather than breadth,
and that counter-claim could not be confirmed against ECP from search
alone.** This should not be asserted as an established fact in any
customer-facing material — the breadth gap is real and sourced; the
depth counter-claim is a hypothesis this pass could not test.

### 2.4 Proactive fall-risk assessment — a real gap, but the market is
leapfrogging the shape SAIRNcare might build

No evidence surfaced that PointClickCare, MatrixCare, Eldermark, ALIS, or
ECP embed a validated fall-risk instrument (Morse Fall Scale, JH-FRAT, or
similar) as a named product feature. SAIRNcare's own "fall" handling is
entirely reactive — an incident category logged after an event, not a
predictive assessment. The better-funded market answer to "proactive fall
risk" is not a MAR-embedded scored questionnaire, though: **Sage**, a
senior-care AI/sensor startup, raised a $65M Series C led by Goldman Sachs
Alternatives (~March 2026, ~$124M total raised) explicitly positioned
around shifting senior care "from reactive to predictive," using
hardware sensors including fall detection. **Adding a classic scored
questionnaire would close a real, present-day gap against mainstream
ALF-EHR platforms, but the capital in this specific sub-category is
already moving toward continuous sensor-based prediction instead** — a
fact worth carrying into any build decision, not a reason to skip the
gap.

### 2.5 Family/resident engagement portal — the strongest, best-evidenced
gap in this document

Confirmed as close to table stakes in this specific market segment,
independently across multiple vendors: ALIS ships a named "ALIS Connect"
family module; Aline ships "Aline Engage"/"Family App," described as
having grown from a social/communication tool to carrying "vital health
updates"; PointClickCare, while not shipping a built-in portal itself,
runs a marketplace of eight-plus third-party family/resident-engagement
integrations (LifeLoop, CareFeed, InTouchLink, Family CareSpace, Linked
Senior, Well iQ, Activated Insights, an IntelliChart family portal) —
meaning even the vendor without a built-in answer has built an entire
ecosystem around the need rather than ignoring it. **SAIRNcare has zero
markers for this capability at any level — built-in or integrated.**
Unlike §2.2's moderate-confidence read or §2.3's mixed result, this
finding has multiple independent positive confirmations and no
contradicting evidence, consistent with the plain fact that assisted
living sells to families making a placement decision on behalf of a
parent, not only to the facility operator — a sales dynamic the trades
vertical this series covered previously (plumbing/electrical/HVAC) simply
does not share.

### 2.6 Pricing landscape

Confirms this series' general expectation for enterprise senior-living
software: **"contact sales" is the norm.** PointClickCare, MatrixCare,
ECP, Yardi, and Netsmart/American HealthTech all publish no rate card;
every numeric figure found in this pass for those vendors came from a
third-party aggregator (Capterra, SoftwareFinder, ITQlick, GetApp)
estimating anywhere from $35 to $600+ per user per month depending on the
aggregator, which is itself evidence those figures should not be trusted
as real prices. **ALIS is the only vendor with anything resembling a
concrete number** ($8–15/resident/month, $300/month single-community
minimum), and even that is aggregator-sourced rather than pulled from
ALIS's own published pricing page, so it carries the same caveat as every
other figure in this section: do not quote it as a vendor-confirmed
price.

---

## 3. Patent screen — unverified, no conclusion drawn

Google Patents and USPTO domains were blocked identically to vendor
domains. Every entry below is a third-party index snippet, not an opened
patent page, and no infringement conclusion is drawn from any of them.

- **US 12,288,624 B2, "Compliance dataflow management"** — describes a
  jurisdiction database paired with an automated auditor determining
  compliance requirements and status per jurisdiction. Conceptually
  adjacent to SAIRNcare's Jurisdiction Requirements engine, but this is
  general compliance technology, not assisted-living-specific, and the
  snippet does not describe a fail-closed-for-unseeded-jurisdictions
  design the way SAIRNcare's own code does.
- Several general medication-administration/pharmacy-software patents
  surfaced (US 2006/0149416 A1, US 8,560,345 B2, US 7,706,915, US
  7,813,939 B2) — none specific to a controlled-substance count/witness
  register, none assisted-living-specific.
- Two older (2007/2008) general "method and system for assessing fall
  risk" patents (US 7,682,308, US 7,282,031) surfaced — general
  computational fall-risk assessment, not tied to any specific vendor's
  product or to assisted-living software specifically.
- **No patent surfaced for HCBS waiver claims-routing software
  specifically** — search returned only vendor product pages (WellSky,
  CareCade, MediSked), not patents.
- **No patent surfaced for an assisted-living-specific compliance rules
  engine** more targeted than the general compliance-dataflow grant
  above.

This screen is thin and inconclusive in both directions: no landmine was
found, and nothing confirms SAIRNcare's specific approach is
patent-differentiated either. It should not be leaned on as evidence for
or against any build decision.

---

## 4. Market signals, 2025–2026 (third-party unless the URL is a named
company's own site; none independently fetched in this pass)

- **MatrixCare is being sold.** ResMed is selling MatrixCare to Frazier
  Healthcare Partners for $490M all-cash, announced roughly July 2026,
  expected to close Q3 2026.
- **PointClickCare acquired American HealthTech** from CPSI, January
  2024, continuing a consolidation pattern in this market that predates
  this pass's window but bears directly on how many of the "named
  vendors" in §2.1 are converging under fewer owners.
- **Capital is moving toward AI/sensor-based predictive care, not
  MAR-embedded scoring tools**: Sage raised a $65M Series C (Goldman Sachs
  Alternatives, ~March 2026, ~$124M total) explicitly framed around
  shifting senior care from reactive to predictive; Inspiren raised $35M
  for AI-powered senior-living technology. Both are hardware-sensor plays,
  not EHR-embedded features — directly relevant to how §2.4's fall-risk
  gap should be prioritized.
- **No assisted-living-specific regulatory forcing function analogous to
  a new CMS mandate surfaced in this pass.** ALF compliance drivers remain
  state-by-state, which is consistent with §1's description of
  SAIRNcare's own Jurisdiction Requirements engine as the correct shape
  of solution for this vertical, even though its current coverage is
  narrow (§2.3).
- **Two claims surfaced during this pass and are deliberately excluded
  from the findings above** because neither could be pinned to a clean,
  citable source: a statistic that AI adoption among senior-living
  operators rose from roughly 9% in 2024 to roughly 36% in 2025, and a
  claim that ECP raised "the largest growth investment in the history of
  assisted-living software" from Level Equity around December 2025.
  Neither is stated as fact anywhere in this document, in keeping with
  this series' standing refusal to fill in a fact it cannot verify — if
  either turns out to be real and useful, it needs its own sourced pass,
  not a citation to this document.

---

## 5. What this means for SAIRNcare, in priority order

Reading §2 against §1's own internal grounding — and, because no prior
internal audit existed to compare against, this ranking is this
document's own first pass, not a revision of an existing one:

1. **A family/resident engagement surface is the highest-confidence gap
   in this document** (§2.5) — multiple independent vendor confirmations,
   no contradicting evidence, and a market where this is closer to table
   stakes than a differentiator. It does not have to be a full built-in
   portal to start: PointClickCare's own answer is an integration
   marketplace, not a from-scratch build, which is a materially cheaper
   shape to consider first.
2. **The controlled-substance register is a real, plausible, but
   moderate-confidence gap** (§2.2) — a confirmed real compliance
   requirement (surveyors check controlled-substance logs), but not
   confirmed as a differentiator against SAIRNcare's actual peer set
   specifically, since the clearest positive evidence for this exact
   feature shape comes from an adjacent market (home care), not core ALF
   vendors. Worth building on the strength of the compliance requirement
   alone, not on the strength of a proven competitive gap.
3. **Proactive fall-risk scoring is a real gap against yesterday's market
   shape and should be scoped with that in mind** (§2.4) — closing it with
   a classic scored questionnaire is legitimate and cheap, but the
   best-funded answer in this exact sub-category is sensor-based
   continuous monitoring, which is a different, much larger investment.
   Do not treat a scored-questionnaire build as closing the gap the
   market is actually moving toward.
4. **The multi-state Jurisdiction Requirements coverage should be read
   as a real, sourced, unflattering finding, not softened** (§2.3) — at
   least one real competitor claims fifty-state breadth against
   SAIRNcare's four states. SAIRNcare's only available counter-argument
   (depth and honest fail-closed behavior over raw breadth) is plausible
   given the app's own code, but is not verified against ECP and should
   not be asserted to a customer or prospect as an established
   advantage without a follow-up pass that can actually open ECP's own
   pages.
5. **Everything else in this pass — pricing opacity (§2.6) and the
   patent screen (§3) — is context, not a gap finding**, and should not
   be read as either supporting or undermining any build decision on its
   own.

---

## 6. What this document does NOT establish

- **No vendor page was opened directly, at all, in this pass.** Every
  claim above is a search-engine snippet of a vendor's own domain.
- **No patent claim was read.** §3 names candidates for a real screen and
  performs none.
- **No competitor product was used, demoed, or tested.**
- **No pricing figure here should be quoted to a prospect** — most
  vendors publish none at all, and the few numbers found are aggregator
  estimates, not vendor-confirmed prices.
- **Two market-signal claims (§4) are explicitly excluded from this
  document's findings** because they could not be traced to a clean
  source in this pass — they are named so a future pass knows they exist
  and need their own verification, not so they can be cited from here.
- **The Aline/ECP relationship is stated as unresolved (§2.1), not
  guessed at** — both domains are live and distinct-looking today, and
  this pass does not assert a merger or corporate-family history it
  cannot verify.
- This document does not decide whether SAIRNcare should build any of
  the items in §5, in what order, or at what cost — that is a
  `sairn-software-architect` and `sairn-decision-gate` question, same as
  this series' own precedent declines to decide the gaps it finds.
- **§1's internal grounding is this pass's own first read, not a
  cross-checked prior document** — unlike the SAIRNvet, SAIRNlaw, and
  SAIRNmechanical companions in this series, there was no existing
  internal audit to verify §1 against. A second, independent read of
  `sairncare.html` before any customer-facing claim is drawn from §1
  would strengthen it the way the caller-level cross-check strengthened
  those other three documents.

---

## 7. Decay

Every fact in this document is a search-index snapshot from 2026-09-25 of
pages this session could not open, in a market this pass's own §4 shows
is actively consolidating (MatrixCare's sale) and shifting capital toward
a different technology shape entirely (Sage's and Inspiren's raises).
**Do not treat any cell here as current without re-reading the source
page.** The one action this document asks for, ahead of any competitive
finding: run this pass again from a network that can reach vendor and
patent-office domains — and, because this is the first pass for
SAIRNcare specifically, have a second reader independently re-derive §1
against the live code before either section is relied on for a real
decision.
