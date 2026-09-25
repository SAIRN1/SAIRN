# Worldwide external competitive-gap audit — SAIRNlaw

**Research pass, 2026-09-25. No code written, no app file touched.** Written
by a standalone cloud session under `docs/cloud-research/` per instruction
(new files only, new branch, no PR). This is the *external market* companion
to the internal re-derivation already on `main`
(`docs/SAIRNlaw-competitive-gap-audit-2026-09-24.md`, SAIRNlaw's first
competitive-gap audit, recreated 2026-09-24 by Fourth from a stranded cloud
session's findings and re-verified against HEAD). That document is the
anchor for what SAIRNlaw actually has; this document is the market it sells
into.

**Method and standard**: the reference for this series is
`docs/superpowers/specs/2026-09-02-stonedesk-worldwide-competitive-gap-audit.md`
— every competitor claim read from the vendor's own site, not a comparison
article; aggregator pages used only to find vendors; a failed fetch recorded
as a failure, never filled in; pricing only from a vendor's own pricing page.

---

## 0. A material limitation, stated before anything else

**This session's outbound network cannot reach any vendor, trade-press, or
patent-office domain.** Every direct fetch attempted against a vendor page in
this pass — for both this document and its SAIRNvet companion, including one
made directly by this session (not a subagent) to `www.shepherd.vet/pricing`
immediately after confirming the egress proxy itself reports healthy
(`enabled: true`, `bundleCoversEveryHost: true`, zero recent relay
failures) — returned `EGRESS_BLOCKED`. The proxy's own status shows no
certificate or routing fault; this is a destination-level policy decision,
and the proxy documentation's own instruction on a blocked host is explicit:
*"Do not retry or route around it — report the blocked host."* That is what
happens here rather than a workaround.

**What this means for evidence grade.** Every vendor-fact cell below came
from `WebSearch` restricted to the named vendor's own domain
(`allowed_domains`), returning the search engine's indexed *excerpt* of that
page, not the page itself — one grade below this series' own standard. Every
claim is a **vendor-domain snippet, not independently opened**, and marked
as such. **Nothing here should be quoted externally — to a firm, in a
pitch, in a proposal — without a follow-up pass from a network that can
reach these domains.** That follow-up is this document's single most
important recommendation, ahead of any finding below.

Patent-office and Google Patents domains were equally blocked; §5 records
patent numbers as they appear in third-party index snippets, explicitly
unverified, with no infringement conclusion drawn.

Retrieval date for every row below: 2026-09-25.

---

## 1. What SAIRNlaw has, measured against the internal audit

Read from `docs/SAIRNlaw-competitive-gap-audit-2026-09-24.md` (the
Fourth-verified HEAD document, SAIRNlaw's first) and confirmed as the anchor
for this pass:

**BUILT AND WIRED — the two features a firm would switch platforms for:**
- **IOLTA three-way reconciliation**, server-side, with its own suite: bank
  statement, ledger and per-client allocations reconciled as of the
  statement date, returning four outcomes (agree / disagree / partial /
  cannot reconcile) rather than a boolean, and failing closed on unreadable
  input. Dedicated race-condition suites exist for trust voids and
  transaction collisions.
- **Intake conflict-of-interest checking**, implemented as a real search
  across every existing matter's client and adverse parties, surfaced at
  intake, and blocking matter creation on a hit unless a reviewer ticks an
  explicit "reviewed and confirmed" override — a flag a human must clear,
  not a warning that scrolls away.

**REAL GAPS — six, all in billing operations, confirmed by the internal
audit's caller-level check:**
1. **LEDES export** — already the open-work index's own row: five of six
   in-app "LEDES" occurrences correctly cite the published standard, one was
   a claimed feature that was never built, and the false claim was removed
   2026-09-21. The export itself remains unbuilt.
2. **Ambient / passive time capture** — zero markers. Every billable entry
   is typed after the fact in one manual modal.
3. **Rate cards** — zero. One hourly figure typed per entry; no
   timekeeper entity, no per-client or per-matter rate structure.
4. **Origination credit** — zero, and distinct from what already exists.
   `saveInvoice()` has real invoice-level split-fee billing (attorney name
   plus percentage, validated to sum to 100, stored as `split_fees`) — that
   splits **one invoice**. Origination credit is an attribution system
   across a client's lifetime of matters feeding compensation, and the
   internal audit is explicit that naming the split-fee feature as partial
   credit here "would be the capability-inflation this audit series exists
   to catch."
5. **Outside-counsel guidelines** — zero. No per-client billing rules
   (task-code restrictions, staffing caps, no-charge activities), which is
   what makes a LEDES export useful to a corporate client once it exists.
6. **Role depth** — auth exists platform-side; legal practice roles do not.
   `paralegal` appears four times; `associate` zero times. No role-scoped
   rate defaults, no supervision chains, no role-limited trust actions
   beyond the platform's generic management gate.

---

## 2. The market, as far as this session could establish it

Roughly twenty vendors across small-firm (1–20 attorneys) and mid-market
(25–100+) tiers, every claim a vendor-domain **snippet, unopened** unless
marked third-party.

### 2.1 LEDES export (Gap 1)

| Vendor (tier) | What the vendor-domain snippet states |
|---|---|
| Clio (small) | Bills downloadable "as CSV, LEDES 1998B, LEDES 1998BI, LEDES XML 2.0, and LEDES XML 2.1" |
| MyCase (small) | "Download LEDES 1998B" per invoice; requires enabling LEDES and a per-user "Timekeeper Classification"; stated as an Advanced-tier feature |
| PracticePanther (small) | "LEDES billing feature is only available on… business subscription plan"; per-contact LEDES Client ID and Client Matter ID required |
| Smokeball (small) | "create LEDES 1998B invoices using the ABA task codes"; firm-wide default timekeeper-classification code, overridable per matter |
| CosmoLex (small) | States support for "LEDES1998B, LEDES 2000, LEDES 2.0 and Litigation Advisor eBilling formats" |
| TimeSolv (small) | States "LEDES 1998B, 1998BI, Chubb, Litigation Advisor, and UTBMS task codes", plus LEDES 2000 |
| Bill4Time (small) | "LEDES 1998b/i and XML format"; gated to its Legal Pro tier; requires firm Federal Taxpayer ID and per-client LEDES ID |
| LeanLaw (small/mid) | States LEDES export on its Pro plan, formats 98B and 2000 |
| Centerbase (mid) | A named partnership with Scan Logic (announced 2026-08-25): "compliant LEDES files are submitted directly through the client's e-Billing portals" — the only small/mid vendor snippet found stating direct portal submission rather than a file download |
| Aderant BillBlast (mid/large) | States "LEDES standards compliance" and "LEDES e-billing dispatch" |

**Pattern**: every small-firm vendor found ships LEDES 1998B at minimum, as a
**file download** the firm uploads itself; XML 2.x is stated by only three
vendors (Clio, CosmoLex, Bill4Time); direct-to-portal submission is a
mid-market, partner-dependent feature (Centerbase+Scan Logic, Aderant). The
enforced UTBMS code SAIRNlaw already has server-side is the hard
prerequisite every vendor's LEDES feature also depends on.

### 2.2 Time capture (Gap 2)

| Vendor | What the vendor-domain snippet states | Confirm-before-bill? |
|---|---|---|
| Clio (Manage AI) | "passively monitoring and capturing daily activities across Microsoft Outlook… document work saved in OneDrive, and outbound calls… automatically generates a draft time entry… Users then quickly review… and approve the entry for billing" | Yes, stated explicitly |
| Smokeball AutoTime | Nightly batch job converts the day's recorded in-app activity (documents, emails, calendar, calls) into "Pending" time entries added to billing | Reviewed before invoicing, not a hard per-entry confirm gate |
| MyCase Smart Time Finder | "works in the background, passively tracking all activities done in MyCase"; produces a list the lawyer uses to create entries | Yes — lawyer creates the entry from the suggestion |
| Actionstep Trace (announced Jan 2026, GA Aug 2026) | "passive activity tracking… across Outlook, Word, PDFs, and common websites… captures time down to the second… AI-generated narratives"; a premium add-on module | Not stated in snippet |
| Aderant iTimekeep (mid/large) | "Passive Time Assistant… tracks and captures time spent on… (meetings, emails, etc.) in the background"; an AI pre-selects client/matter on the entry form | Timekeeper submits the pre-filled form |
| Laurel (standalone, integrates with PM tools) | "content-level capture… Outlook emails with context, Zoom calls with attendees… document and web activity"; claims 4–11% more captured revenue | Not stated in snippet |
| Billables AI (standalone) | "automatically captures your work in the background… reconstructing your activities into draft time entries" | "Draft" entries implies a review step |

**Every vendor that describes passive, OS-level capture also states the
timekeeper reviews or approves before the entry bills** — none of the
snippets gathered describe fully autonomous billing with no human step. A
running timer with auto-pause and matter selection (PracticePanther,
TimeSolv) is the floor of the market at the $49–$99/month tier; passive,
cross-application capture is a 2026 premium layer at small-firm tier and
closer to standard at mid-market.

### 2.3 Rate cards (Gap 3)

| Vendor | What the vendor-domain snippet states |
|---|---|
| Clio | A documented precedence hierarchy: per-entry override > flat activity-category rate > matter-specific rate > client rate > custom hourly activity-category rate > user default |
| PracticePanther | Matter-level custom rate scoped "For everyone / Per User / Per Role", with a stated precedence order |
| Smokeball | "Rate Sets provide a table for setting and scheduling rate changes… associated with any matter"; effective-dated |
| CosmoLex | "up to eight different rate levels per timekeeper", plus matter-specific "localized" rates |
| Centerbase (mid) | Rate Tables at matter, client, system-default and timekeeper level; import requires an explicit `EffectiveDate` field; described as versioned |
| Tabs3 (small/mid) | A billing-rate table with multiple rates per timekeeper *level* ("e.g., partner, associate, paralegal") per client or case, with an effective date |

Rate cards in this market are a **timekeeper entity with a default rate**,
overridable at client or matter level (per person or per role), with a
defined precedence order; the more mature small-firm products and every
mid-market product add effective dates so a rate change applies forward
without rewriting history. SAIRNlaw's per-entry typed rate is the *top* of
this hierarchy everywhere else, not the only mechanism.

### 2.4 Origination and working-attorney credit (Gap 4)

| Vendor | What the vendor-domain snippet states |
|---|---|
| Clio | Matter fields "Originating Attorney" and "Responsible Attorney"; a firm-wide percentage allocation between the two feeds an Originating Attorney Revenue Report |
| CosmoLex | Roles named Originating / Responsible / Work Attorney / Other, with a matter-level fee-allocation percentage across them and a Collected Fee Allocation report |
| TimeSolv | A matter "Originators" tab supporting multiple originating attorneys, each with a commission percentage |
| Bill4Time | Originator and Split Percentage fields, stated as "calculated on payments to the invoice" (collected, not billed) |
| LeanLaw | Tracks originating, responsible and working attorney with separate originating-percent and working-percent columns per matter |
| Centerbase (mid) | "anyone listed as an originator receives a percentage of all fees received on the matter"; origination tables are effective-dated |

**Every vendor's model is (a) matter-level role fields for originating,
responsible and sometimes working attorney, (b) a percentage split across
them, and (c) a compensation report built from collected fees, not invoiced
amounts.** This is a structurally different object from SAIRNlaw's
invoice-level split-fee, which is the internal audit's own point: origination
tracks who brought in the matter across its lifetime, not who gets paid on
one bill.

### 2.5 Outside-counsel guidelines (Gap 5)

| Vendor | What the vendor-domain snippet states |
|---|---|
| Aderant OCG Live + iTimekeep (mid/large) | Validates and warns of a possible OCG violation as a timekeeper enters time; a named "Summary Acknowledgement" requires sign-off on the guidelines themselves before entries count |
| Intapp Time (mid/large, May 2026 release) | Admin-configured rules for "outside counsel guidelines, restricted terms, and block billing"; states it detects a multi-activity narrative and offers to split it into compliant entries |
| Centerbase + Scan Logic (mid, announced Aug 2026) | "time entries are validated against the applicable guidelines before an invoice goes out, and non-compliant entries are flagged for correction in real time" |
| Rocket Matter (small) | The **only small-firm vendor found** stating configurable rules: "set rules based on language or billing limits and specify when the rule is applied – at time entry or during prebill" |
| Clio (small) | A bill-approval workflow (draft → pending approval → approved) allowing a second firm member to review — human review, not a rules engine |

At the small-firm tier this is nearly absent: one vendor found states
configurable pre-bill rules; the rest offer a human approval step. At
mid-market it is a named product category — block-billing detection,
restricted-term checks, rate caps, minimum increments — validated both at
entry and again before submission. SAIRNlaw's existing server-side refusal
of an uncoded billable hour is structurally the seed of this pattern; it
already validates at the point of entry, which is the harder half most
small-firm competitors skip.

### 2.6 Role depth (Gap 6)

| Vendor | Role vocabulary / what it gates, per the vendor-domain snippet |
|---|---|
| Clio | Four functional permissions: Administrator, Billing (gates the Bills tab entirely), Accounts (trust/operating transactions), Reports — plus Groups and Job Titles |
| MyCase | User types Attorney / Paralegal / Staff crossed with Admin / Regular; per-feature access is Add&Edit / View Only / Hidden |
| CosmoLex | Predefined roles: Normal, Matter Owner, Timekeeper, Matter Owner/Timekeeper, Read Only, Time/Expense Entry Only — stated as "nearly 40 specific permissions" per role |
| Centerbase (mid) | Profiles plus Groups (example groups named "Associate Attorneys", "Billing and Accounting Department"), record-level permissions on rates and financials, and an "Ethical Wall" feature |
| Tabs3 | Access Profiles plus per-user timekeeper restriction; timekeeper *levels* (partner/associate/paralegal) drive rates, separate from auth |

**No small-firm vendor found exposes "partner" or "associate" as an
authorisation role.** Every vendor's actual gate is functional — billing
access, trust/accounts access, admin, report access, read-only — with
"partner/associate/paralegal" appearing only as a **rate-card level** or an
example permission-group name, never as the thing that decides what a user
can do. This directly reframes Gap 6: the realistic target is not adding job
titles, it is a billing permission that actually gates invoice creation and
viewing, a trust/accounts permission separate from billing, a rate-edit
restriction, and matter-level access lists.

### 2.7 Trust three-way reconciliation — a strength check, not a gap

| Vendor | How the vendor-domain snippet describes it |
|---|---|
| CosmoLex | "contains the adjusted bank balance, the book balance, and the client trust ledger balance and shows that all three balances match" |
| Tabs3 | Compares the total of all client trust ledger balances, the ending statement balance (adjusted for outstanding items) and the ending check-register balance |
| PracticePanther | A "guided Three-Way Reconciliation Wizard" stated to prevent commingling and block overdrafts before they occur |
| MyCase | "three-way reconciliation that aligns your client ledger balances, bank activity, and the related payments, invoices, and trust requests" |
| LeanLaw | States continuous, real-time reconciliation across bank statement, QuickBooks Online trust ledger and client sub-ledgers |

SAIRNlaw's as-of-statement-date, four-outcome, server-side reconciliation
matches this category's own description almost exactly (statement date,
three balances, a genuine match/mismatch answer) — **this is table stakes in
this market, not a differentiator**, and should be positioned to a firm as
"does what the category expects, correctly" rather than as a novel feature.
The adjacent claim worth checking against SAIRNlaw's own ledger writes is
PracticePanther's stated overdraft/commingling block, which is a step beyond
reconciliation into write-time prevention.

### 2.8 Pricing landscape (vendor-domain pricing-page snippets only)

| Vendor | Published figure |
|---|---|
| Clio | "from $49"; four named tiers, per-tier prices not exposed in the snippet gathered; a help-doc snippet used different tier names entirely, unresolved |
| MyCase | Basic $60 ($50 annual); Pro $99; Advanced $150 |
| PracticePanther | Solo $49 (annual); Essential $69; Business $89; Business Pro $114 |
| CosmoLex | Launch $49; Core $99; Pro $129 |
| Rocket Matter | Essentials $39; Pro $79; Premier $99 |
| TimeSolv | 1–4 users $39.95; 5–14 $34.95; 15+ $29.95 |
| Bill4Time | Solo $19.99; Pro $39.99 + $9.99/added user; Enterprise $99.99 + $9.99/user |
| LeanLaw | Core $55; Pro $75 |
| Centerbase, CARET Legal, Aderant, Intapp, Laurel, Billables AI | **Not published** on the vendor domain as retrievable in this pass |

---

## 3. What this means against SAIRNlaw's six gaps

**Gap 1 — LEDES.** A LEDES file is a fixed-width or XML invoice with
UTBMS-coded lines, a timekeeper classification, and a client-matter ID,
uploaded by the firm to the client's e-billing portal after invoice
finalisation. SAIRNlaw's server-side UTBMS enforcement is the hard
prerequisite every vendor's export also depends on; the remaining build is a
per-client LEDES ID field, a per-user timekeeper classification code, and a
serialiser. Direct portal submission is a mid-market, partner-dependent
feature and is not required for parity with the small-firm tier this
platform is actually selling into.

**Gap 2 — time capture.** Every vendor that describes passive, cross-app
capture also states a human reviews or approves before the entry bills —
none bills autonomously. The realistic build target is therefore not full
autonomy but the market's actual floor: a running timer with auto-pause and
matter selection, which is universal at the $49–$99 tier and which
SAIRNlaw's single manual modal is currently below.

**Gap 3 — rate cards.** Minimum parity is a timekeeper record carrying a
default rate, a matter-level override per timekeeper, and a defined
precedence order between them. Effective-dated rate sets are the next step
up and already exist in at least two small-firm products, so they are a
reasonable v2 rather than an enterprise-only feature.

**Gap 4 — origination credit.** This needs matter-level role fields
(originating, responsible, working attorney) distinct from the existing
invoice-level split, plus a compensation report derived from *collected*
fees rather than invoiced amounts — the dimension every vendor's own
reporting is built around and SAIRNlaw's current split-fee cannot answer.

**Gap 5 — outside-counsel guidelines.** SAIRNlaw's existing server refusal
of an uncoded billable hour already validates at the point of entry, which
most small-firm competitors do not do at all. Extending that same mechanism
to a per-client rule set (a task-code allowlist, a rate cap, a minimum
increment) evaluated before invoice generation would exceed the small-firm
norm rather than merely match it, and is the feature that makes Gap 1
actually useful to a corporate client once built.

**Gap 6 — role depth.** The market evidence reframes the ask: build
functional permissions (a billing gate, a trust/accounts gate separate from
it, a rate-edit restriction, matter-level access lists), not job titles.
Timekeeper level (partner/associate/paralegal) belongs on the rate card
(Gap 3), not in the authorisation model — that is how every vendor surveyed
actually implements it.

---

## 4. What SAIRNlaw has that this pass found no small-firm competitor stating

The intake conflict check's **blocking override with a stored reviewed-and-
confirmed flag on the matter record** is stronger than anything described in
the small-firm tier surveyed: every vendor-domain snippet gathered for
conflict checking in this pass either did not mention conflicts at all, or
(where mentioned in passing on a features page) did not state a hard block
on matter creation. This should be treated as a candidate differentiator,
not a confirmed one, pending the same follow-up pass this document asks for
in §0.

---

## 5. Patent screen — unverified, no conclusion drawn

Google Patents and USPTO domains were blocked identically to vendor domains.
Every entry below is a **third-party index snippet**, not an opened patent
page. No infringement conclusion is drawn; each needs a direct claims read
before it informs a build decision.

The one result most squarely on point for Gap 2 (ambient/passive time
capture): a US grant indexed to assignee **Centerbase, LLC**, titled around
"automated time entries utilizing automated time capture", with a snippet
describing autonomous entry generation on termination of a communication
session — identifying timekeeper, client, date and duration "without further
user input". Several older, more general "automated time tracking" grants
(one Microsoft Corporation, one Realtime Tracker Inc, several unassigned in
the snippets gathered) also surfaced without confirmed relevance. No
Chrometa-, Bellefield- or Laurel-assigned patent surfaced in this pass. A
grant indexed to "double entry-multivariable accounting for reconciliation
of bank trust accounts" surfaced incidentally while searching Smokeball's
domain and is recorded here rather than dropped, though its relevance to
SAIRNlaw's already-built reconciliation is unclear without a direct read.

**Read before design, not after**: if any passive-capture feature is
designed to fully autonomous entries without a confirmation step, the
Centerbase grant above is the first one to open — and §2.2 already shows
every competitor requires that confirmation step anyway, which is itself a
reason to build it that way regardless of the patent question.

---

## 6. Market signals, 2025–2026 (third-party unless the URL is the named
company's own site; none independently fetched in this pass)

- **Clio's roughly $1B acquisition of vLex** (2025) is described as the
  largest private legal-tech transaction to date, alongside a reported
  Harvey–LexisNexis partnership — both signal continuing consolidation of
  AI capability into the largest platforms.
- **Ownership consolidation among small-firm vendors**: ProfitSolv is
  reported to own CosmoLex, Rocket Matter, Tabs3, TimeSolv, Orion and
  LexCharge, with a private-equity co-investment (FTV Capital and Lightyear)
  reported June 2025 — several of the "small-firm" vendors compared above are
  therefore under common ownership, which is worth knowing when reading them
  as independent competitors.
- **8am (formerly AffiniPay), owner of MyCase and LawPay**, is reported to
  have had its LawPay integration discontinued by Clio in May 2026 — a
  payments-layer competitive move between two of the vendors surveyed.
  SAIRNlaw carries no payments integration at all currently; not previously
  flagged as a gap in the internal audit and not asserted as one here
  either, but adjacent to it.
- **Smokeball partnered with Thomson Reuters** to integrate CoCounsel legal
  AI into its practice-management platform, reported March 2026.
- **Clio's own 2025 Legal Trends report** (vendor-published) states AI use
  among legal professionals rose to 79% (from 19% in 2023), while adoption
  described as "wide" within a firm remains low at the solo/small tier
  (8%/4%); the same report states 75% of solos and 65% of small firms offer
  flat fees — relevant context for how much of this market SAIRNlaw's
  hourly-billing feature set actually reaches.
- **The ABA's own 2025 TechReport**, per third-party coverage, states 30.2%
  of attorneys' offices use AI tools while 67% remain on hourly billing —
  broadly consistent with Clio's figures above from an independent source.
- **Actionstep's Trace** (passive time capture, announced January 2026,
  general availability August 2026) and **Intapp Time's May 2026 release**
  (OCG and block-billing rules evaluated at time of entry) are both recent
  enough that a firm evaluating SAIRNlaw against either vendor today would
  be comparing against a feature that did not exist a year ago — the gap
  identified in §2.2 and §2.5 is not a stale one.

---

## 7. What this document does NOT establish

- **No vendor page was opened directly, at all, in this pass.** Every claim
  above is a search-engine snippet of a vendor's own domain. Stated once in
  §0 and repeated here because it governs how this document should be used:
  a map of what to verify, not verified fact to quote externally.
- **No patent claim was read.** §5 names one candidate for a real screen and
  performs none.
- **No competitor product was used, demoed, or tested.**
- **No pricing figure here should be quoted to a prospect** until re-read
  from the live page.
- This document does not decide whether SAIRNlaw should build any of the
  six gaps, in what order, or at what cost — same as the StoneDesk reference
  audit's own §7 declines to decide its gaps, and the same as the accepted
  precedent for this series (`docs/2026-08-29-single-provisioning-role-trapdoor-analysis.md`
  and `sairn-rbac`) that a new role is a new authorisation tier and should
  not be added lightly, cited here because Gap 6 is exactly that kind of
  decision.

---

## 8. Decay

Every fact in this document is a search-index snapshot from 2026-09-25 of
pages this session could not open. It will decay faster than a normal
competitive audit for that reason alone, independent of the market moving —
three of the market signals in §6 describe vendor releases from within the
last eight months. **Do not treat any cell here as current without
re-reading the source page.** The one action this document asks for, ahead
of any competitive finding: run this pass again from a network that can
reach vendor and patent-office domains, and only then decide what — if
anything — to build.
