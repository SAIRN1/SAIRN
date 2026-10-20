# Worldwide competitive-gap audit — SAIRNCODE

**fourth / b38, 2026-10-20.** An audit of an app that already exists, under a
worldwide lens. Second in the primary-sources-only pair after sairnlaw (b37).

**THE SOURCING RULE WAS TIGHTENED FOR THIS ONE AND IT CHANGED THE RESULT.** b37
pulled primary regulation but read most of it through domain-restricted *search
snippets*. This audit's instruction was **fetch the consolidated or full text,
and report any source you could not read in full** — so §1 lists what was read
whole and §6 lists what was not, with the failure mode of each.

**FIVE SOURCES READ IN FULL. TWO COULD NOT BE READ AND ARE NOT PARAPHRASED FROM
MEMORY.** Where a rule number is cited below, its text was fetched.

**THIS IS NOT A BUILD RECOMMENDATION.** §7 is what would have to be true.

---

## 0. THE RESULT, AND IT IS THE OPPOSITE SHAPE TO EVERY PRIOR AUDIT IN THE SERIES

Every previous audit found **a market need SAIRN had no capability to fill.**
This one finds the inverse:

> **SAIRNcode already implements the hardest substantive requirement of the US
> AI-transparency regime for health IT — and names none of the five regulations
> that govern it, in a file of 38 panels.**

Measured, not impressions (`grep -ci` over `sairncode.html`):

| named in the app? | term | hits |
|---|---|---|
| **no** | `RADV` | **0** — with an HCC panel *and* a RAC panel |
| **no** | `False Claims` / `upcod` | **0** |
| **no** | `Section 1557` / `1557` | **0** |
| **no** | `170.315` / `decision support intervention` / `source attribute` | **0** |
| **no** | `first Friday` (the risk-adjustment deadline) | **0** |
| **no** | `ICD-11` | **0** |
| yes | `ICD-10` 44 · `CPT` 127 · `HCPCS` 63 | US code sets only |

**The gap is the ARTEFACT, not the capability** — and an artefact is what a
certification body, a payer's procurement, or a hospital compliance officer
actually asks to see. §3.

---

## 1. THE FIVE PRIMARY SOURCES, READ IN FULL

### 1.1 45 CFR 170.315(b)(11) — Decision Support Interventions

**ONC/ASTP certification criterion. Read in full via the eCFR API.** This is
the one that matters most, because it is the only US rule that enumerates what
an algorithmic recommendation must carry:

* **(b)(11)(iv)(A) — evidence-based DSIs: THIRTEEN source attributes**,
  including the **bibliographic citation** of the intervention, its
  **developer**, **funding source**, **release and revision dates**, and
  documented use of race, ethnicity, language, sexual orientation, gender
  identity, sex, date of birth and social-determinants data.
* **(b)(11)(iv)(B) — PREDICTIVE DSIs: a longer list**, covering the
  intervention's details and output, its **purpose**, its **cautioned
  out-of-scope uses**, development details, **fairness process**, **external
  validation process**, **quantitative performance measures**, **ongoing
  maintenance**, and an **update/validation schedule**.
* **(b)(11)(v)(A)** — the module must let identified users reach *"complete and
  up-to-date plain language descriptions of source attribute information."*
* **(b)(11)(v)(B)** — users must be able to **record, change and access** those
  attributes.

### 1.2 42 CFR 422.310 — Risk adjustment data

**Read in full via the eCFR API, (a) through (g).** Two paragraphs are directly
decisive for an HCC product:

* **(e)** — *"MA organizations and their providers and practitioners are
  required to submit a sample of medical records for the validation of risk
  adjustment data, as required by CMS."* Penalties apply for false data, and
  **RADV audits may produce EXTRAPOLATED findings with payment remitted.**
* **(g)** — submission deadlines are the **first Friday in September** and the
  **first Friday in March**, and **after the final deadline an organisation may
  only correct OVERPAYMENTS — it may not submit new diagnoses.**

**(g) is an ASYMMETRY and it is the single most product-shaped sentence in this
audit.** Past the deadline, a found-but-unsubmitted HCC is worth nothing and a
wrongly-submitted one is still a liability. A coding tool that treats "we found
a gap" and "we found an error" as the same kind of finding is wrong about the
only direction that still matters.

### 1.3 31 U.S.C. 3729 — the False Claims Act

**Read in full via govinfo (GPO).**

* **(a)(1)(A)** — liability for knowingly presenting *"a false or fraudulent
  claim for payment or approval"*; **(a)(1)(B)** — for knowingly using *"a false
  record or statement material to a false or fraudulent claim."*
* **(a)(1)** — a civil penalty of **not less than $5,000 and not more than
  $10,000**, *"as adjusted by the Federal Civil Penalties Inflation Adjustment
  Act of 1990"*, **plus three times** the Government's damages.
* **(b)(1)** — *"knowing"* and *"knowingly"* cover actual knowledge,
  **deliberate ignorance**, and **reckless disregard** — and **"require no
  proof of specific intent to defraud."**

**THAT LAST CLAUSE IS WHY THIS AUDIT IS ABOUT ARTEFACTS.** A product that
systematically nudges toward a higher-paying code exposes its *user* with **no
intent element** — reckless disregard suffices. The defence is a record showing
each suggestion was grounded and reviewed. **SAIRNcode builds that record and
never says what it is for.** §3.1.

### 1.4 45 CFR 92.210 — Nondiscrimination in patient care decision support tools

**Read in full via the eCFR API. It has three paragraphs, (a)–(c), not four.**

* **(a)** a covered entity must not discriminate on *"race, color, national
  origin, sex, age, or disability"* through the use of patient care decision
  support tools;
* **(b)** an **ongoing duty to make reasonable efforts to IDENTIFY** uses of
  such tools that employ variables measuring those characteristics;
* **(c)** for each tool identified, **reasonable efforts to MITIGATE** the
  discrimination risk.

**(b) is a duty to go looking, not a duty to respond to complaints** — a
standing inventory obligation, which is an artefact again.

### 1.5 WHO — ICD-11

**Read in full on who.int.** Adopted by the **72nd World Health Assembly in
2019** (**WHA72.15**) and **in effect since 1 January 2022**. As of **May
2024**, WHO reports **132 Member States and areas** at various phases: **72**
having commenced implementation, **50** piloting, **14** collecting or
reporting data in ICD-11. On the predecessor: *"All Member States are committed
to using the most recent version of ICD"*, and **the latest ICD-10 version WHO
publishes online is from 2019.**

---

## 2. WHAT SAIRNCODE IS, MEASURED AT HEAD

| | measured | command |
|---|---|---|
| resources | **28** | bracket-matched parse of `api/_resources/sairncode.js` |
| panels | **38** | `grep -o 'id="panel-[a-z0-9-]*"'` |
| | `hcc`, `drg`, `rac`, `prebill`, `encoder`, `query`, `anesthesia`, `pctc`, `modrouting`, `fraud`, `ar`, `revenue`, `compliance`, `auth`, `eligibility`, plus 13 specialty panels | |
| code sets | **ICD-10-CM, CPT, HCPCS — US only** | hit counts in §0 |
| ICD-11 | **0** | `grep -ci "ICD-11\|ICD11"` |

**This is a full revenue-cycle and coding-compliance product, not a thin
wrapper.** It is the largest-surface app in this series so far.

---

## 3. THE GAP — THREE FINDINGS

### 3.1 **IT ALREADY DOES THE HARD HALF OF (b)(11) AND SAYS SO IN ITS OWN WORDS, NOT THE RULE'S**

From `sairncode.html:842`, shipped user-facing copy:

> *"Every suggested code must cite the exact phrase in the note that supports it
> — this page independently checks that the quoted phrase is actually present in
> what you pasted, and flags any suggestion whose citation can't be verified
> rather than trusting it silently."*

**That is grounding WITH AN INDEPENDENT VERIFIER, which is stronger than
(b)(11)(iv)(A)'s "bibliographic citation" attribute asks for** — the rule wants
the citation supplied; this checks it. Alongside it: a **Coded Items** panel
holding *"stored citation and reasoning per coded item, plus the human-review
queue"* (`:749`), and a confidence figure that is **DERIVED** — the file records
that it *"already had fabricated 82%/71% confidence scores"* and that this was
fixed (`:862`, `:4206`).

**AND THE ARTEFACTS THE RULE ENUMERATES ARE ABSENT.** `grep -ci`: `source
attribute` **0**, `effective date` **0**, `authority` **1**. Nothing in the file
expresses an **external validation process**, **quantitative performance
measures**, a **fairness process**, an **update/validation schedule**, or
**cautioned out-of-scope uses** — the five attributes (b)(11)(iv)(B) requires
for a *predictive* DSI and the five a buyer's compliance officer will ask for
first.

**So the finding is not "build the capability". It is "write down the one you
have, in the vocabulary the regulation uses."** That is the cheapest item in
any audit in this series.

### 3.2 **NO CODE SET IS DATE-QUALIFIED, AND A SIBLING APP ALREADY SOLVES THIS**

SAIRNcode is **impressively date-aware about MONEY** and not at all about
**CODES**. On money it is better than this audit expected: it carries the
**CY2026 dual conversion factors**, cites the statute (**SSA 1848(d)(20)**),
names both real rates, and **refuses to state a payment amount when QP status
is unknown** rather than picking one (`:2968`, `:3698`).

**On codes there is no vintage at all.** `effective date` → **0**. ICD-10-CM
changes every **1 October** and CPT every **1 January**; a code valid for a
2026 date of service may not have existed for a 2025 one. A claim coded with a
code not in effect on the DOS is a denial at best and, under §1.3's **reckless
disregard** standard, exposure at worst.

**SAIRNdental already does exactly this**, in the same repo:
`cdtStatusFor(proc, serviceDate)` resolves a CDT code's status **as of the
service date** and renders a status badge per line. **The pattern exists, is
shipped, and has not been carried across** — and per discipline 7 it should be
re-qualified for scale and criticality rather than copied, which is a real but
bounded piece of work.

### 3.3 **THE RISK-ADJUSTMENT DEADLINE ASYMMETRY IS NOWHERE, ON A PRODUCT WITH AN HCC PANEL AND A RAC PANEL**

`RADV` → **0**. `first Friday` → **0**. 42 CFR 422.310(e) and (g) are the two
paragraphs an HCC product lives inside, and neither is named.

**The consequence is directional, which is what makes it more than a missing
label.** Before the deadline, a found gap and a found error are both actionable.
**After it, (g) permits only the overpayment correction** — so a tool that
surfaces both as "findings" is pointing the user at work that is now worthless
in one direction and mandatory in the other. And **(e)'s extrapolation** means a
small sampled error rate is not a small liability.

---

## 4. WHAT WOULD HAVE TO BE BUILT

| | thing | size | precedent |
|---|---|---|---|
| **B1** | **A DSI source-attribute record** per suggestion type, carrying the (b)(11)(iv)(B) list, surfaced in plain language and editable | **small-to-medium, and the highest value per line here** — the grounding already exists; this is its description |
| **B2** | **Code-set vintage**: an effective/termination date per code, resolved against the date of service | **medium** | `cdtStatusFor()` in `sairndental.html` |
| **B3** | **A RADV-aware HCC mode**: the two 422.310(g) deadlines, and after the final one surface **only** overpayment corrections | **small**, once the dates are data | the app's QP refusal is the same shape — refuse rather than guess |
| **B4** | **A 92.210(b) tool inventory**: a standing list of which panels use a decision-support tool and which variables it reads | **small, and it is a document** | none |
| **B5** | **ICD-11 and any non-US code set** | **large, and it is the matrix problem again** | none — 0 hits |

**B1 and B4 are documents. B3 is two dates. None of the three needs new
capability**, which is why this audit's recommendation is narrow and the
previous four were not.

---

## 5. THE BLOCKER — AND FOR ONCE IT IS NOT THE SAME ONE

**B5 is the per-jurisdiction matrix problem that killed b28 and b30**, and WHO's
own numbers say why it is real: **132 Member States** at various ICD-11 phases
but only **14** actually collecting or reporting in it. A product that moves to
ICD-11 early serves 14 countries; one that waits serves the US indefinitely.
**That is a timing judgment, not a capability gap, and it is the first blocker
in this series that is neither a company decision nor a missing dataset.**

**B1–B4 have NO blocker**, which has not been true of any audit in this series.
They need a session and a decision about vocabulary.

---

## 6. SOURCES I COULD NOT READ IN FULL — REPORTED, NOT PARAPHRASED

**The instruction required this list, and nothing below is quoted from memory to
fill a gap.**

1. **Regulation (EU) 2024/1689 (the AI Act) — NOT READ. THREE FETCH ATTEMPTS,
   THREE URL FORMS, ALL RETURNED AN EMPTY BODY**
   (`/eli/reg/2024/1689/oj/eng`, `/legal-content/EN/TXT/HTML/?uri=OJ:L_202401689`,
   `/legal-content/EN/TXT/?uri=CELEX:32024R1689`). **b37 hit the identical
   failure on the AMLR summary page, so this is now a CHARACTERISED, REPEATED
   EUR-Lex failure rather than a one-off**, and it means the EU limb of any
   audit in this series is currently unsourceable by this route. **No AI Act
   article, annex point or date is asserted anywhere in this document.** What
   that costs: whether an AI coding tool is Annex III high-risk, and on what
   date, is unanswered here.
2. **The eCFR WEB pages — WALLED, AND NOT ROUTED AROUND.**
   `https://www.ecfr.gov/current/title-45/section-92.210` and the title-42
   equivalent both **302 to `unblock.federalregister.gov`**, a bot-detection
   page. **I did not attempt to defeat it.** The **documented eCFR API**
   (`/api/renderer/v1/content/enhanced/...`) is the sanctioned machine
   interface, it answered, and it returned the same sections — so §1.1, §1.2
   and §1.4 are full-text reads through the intended route, not a bypass.
3. **The compliance date for 45 CFR 92.210 — NOT ESTABLISHED.** The section
   text carries none, and `45 CFR 92.10` turns out to be the *notice* section
   and carries none either. The date lives in the Section 1557 final rule's
   Federal Register preamble, **which I did not read. No date for 92.210 is
   stated in this document.**
4. **The CURRENT penalty amounts under 31 U.S.C. 3729 — NOT READ.** §1.3 gives
   the **statutory base** of $5,000–$10,000 and says *as adjusted*; the live
   adjusted figures sit in **28 CFR 85.5**, which was not fetched. **Do not
   quote a current dollar penalty from this document.**
5. **`uscode.house.gov` 404'd twice** on two URL forms for title 31 §3729;
   govinfo answered and is the source actually used.

---

## 7. WHAT WOULD HAVE TO BE TRUE

**B1 (the DSI source-attribute record) is recommended now, independently of
everything else.** It is a description of behaviour that already ships, it is
the artefact §1.3's reckless-disregard standard makes load-bearing, and
`170.315(b)(11)(iv)(B)` is a ready-made specification — the audit did not have
to invent the field list.

**B3 wants two dates in a data file and a mode switch.** Recommended with it.

**B2 wants a decision about where code-set vintage data comes from** — the
annual ICD-10-CM and CPT releases are licensed artefacts, and CPT in particular
is AMA-copyrighted. **That is a licensing question, not an engineering one, and
it is flagged as such rather than scoped here.**

**B5 wants a timing judgment on ICD-11** against WHO's 14-countries-reporting
figure. Not recommended now; recommended as a watch item with a named re-check.

---

## 8. WHAT THIS AUDIT DID NOT DO

* **Nothing was driven.** No note was pasted into the AI coder, no citation
  check was made to fail, no HCC was aged past a deadline. The §3.1 finding
  rests on shipped user-facing copy and code comments, which is strong evidence
  of intent and **not** proof the verifier works.
* **No market size is quoted and no competitor product was driven** — the same
  deliberate hole as b37, and the same cost: **this audit cannot tell you
  whether anyone else already ships B1–B5.**
* **The server half was not audited.** 28 `sc_*` resources dispatch through
  `api/sd-data.js`, which is cody's, and no claim is made about any of them.
* **Nobody was interviewed** — no coder, no compliance officer, no RADV auditor.
* **No legal review.** Five instruments were read; what they *mean* for a
  specific product is advice, and this is not it.
* **The 13 attributes of (b)(11)(iv)(A) were summarised by the fetch, not
  enumerated one by one.** Before B1 is built, read the criterion itself —
  a field list built from a summary of a field list is the staleness class
  this platform keeps paying for.
