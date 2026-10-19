# Worldwide competitive-gap audit — SAIRNLAW

**fourth / b37, 2026-10-19.** Not a new vertical — **an audit of an app that
already exists**, under a worldwide lens rather than a US one.

**THE INSTRUCTION WAS EXPLICIT ABOUT THE THING THE PREVIOUS AUDIT GOT WRONG:
*"Pull primary regulation sources this time, not vendor pages."*** b36's
sairndental audit disclosed its own weakness — *"no primary regulatory citation
was pulled, and several sources sell into this exact gap."* **So this audit
cites regulators and legislatures only. Every regulatory claim below comes
from a regulator's own site, a legislature's own site, or the standard-setter
— and the domain was restricted at search time, not filtered afterwards.
Zero vendor pages, zero analyst reports, zero law-firm marketing posts.**

**THIS IS NOT A BUILD RECOMMENDATION.** §5 is the company decision and §7 is
what would have to be true.

**Two prior SAIRNlaw audits already exist** —
`SAIRNlaw-external-competitive-gap-audit-2026-09-25.md` and
`sairnlaw-external-competitive-gap-audit-2026-09-26.md`. **Both are
competitor-facing and US-framed. This one is neither, and it is not a
refresh of them.**

---

## 0. THE HEADLINE, BECAUSE IT IS ONE SENTENCE AND IT IS MEASURED

**SAIRNlaw has a genuinely good three-way IOLTA reconciliation and cannot
satisfy the record-keeping half of a single one of the four trust-accounting
regimes audited — including the two US ones — because the reconciliation is
never stored and never signed.**

    grep -n "law_trust_reconcile" api/sd-data.js
    # -> :18747  if (resource === 'law_trust_reconcile' && action === 'read')
    # ONE action. There is no write branch and no table in sql/.

That is not a market gap. **It is a compliance gap in shipped code**, found by
reading regulators rather than competitors, and it is worth more than the
market finding underneath it.

---

## 1. THE REGULATORY SURFACE — PRIMARY SOURCES, SIX JURISDICTIONS AND THE STANDARD-SETTER

### 1.1 The worldwide floor is FATF, and lawyers are inside it

**FATF Recommendations 22 and 23** put *"lawyers, notaries, other independent
legal professionals and accountants"* inside the DNFBP perimeter: customer due
diligence and record-keeping under **R.22** when they prepare for or carry out
transactions concerning the buying and selling of real estate or the managing
of client money, securities or other assets; **suspicious-transaction reporting
under R.23** for the same activities. R.23 carries the professional-secrecy /
legal-professional-privilege carve-out for information obtained in privileged
circumstances.

**This is the reason a "worldwide" legal-practice product is not just 50 states
with the labels changed.** FATF is the common floor; every regime below is a
local implementation of it with its own numbers, and **the numbers are what a
product has to encode.**

### 1.2 The four trust-accounting regimes, side by side, from the regulators

| | jurisdiction | cadence | the third leg | sign-off | retention |
|---|---|---|---|---|---|
| **R1** | **England & Wales** — SRA Accounts Rules 2019, **r.8.3** | **every five weeks** | bank statement **vs** cash book **vs** client ledger total — explicitly three-way | **the COFA or a manager of the firm**, by name | statements obtained at least every five weeks (r.8.2) |
| **R2** | **Ontario** — Law Society of Ontario **By-Law 9** | **monthly, by the 25th** of the following month | a detailed per-client listing **plus** a detailed reconciliation of each trust bank account | **the licensee who prepared or approved it** | **10 years plus the current year** |
| **R3** | **NSW / Victoria et al** — Legal Profession Uniform General Rules 2015 (NSW SI 2015-246), under the Uniform Law | trust receipts cash book kept **per receipt** | per-client/per-matter identification on every receipt | — | **annual external examination**, report filed with the regulator **within 60 days** of period end (s.155 UL) |
| **R4** | **New York** — 22 NYCRR 1200, **Rule 1.15** | entries **at or near the time** of the act (contemporaneous) | date, source and description per deposit; date, payee and purpose per withdrawal | — | **seven years** after the events recorded |
| **R5** | **California** — State Bar Rules, **Title 2 Div. 1.5 (CTAPP)** | **annual** | — | **a per-licensee certification and declaration** | annual registration of *every* trust account: routing number, bank name, account number |

**R1 and R2 are the demanding pair and they demand the same two things SAIRNlaw
does not do: a STORED reconciliation record, and a NAMED HUMAN'S SIGN-OFF on
it.** R4 adds a seven-year clock to the same artefact in the largest US legal
market. R5 is a different shape — a per-lawyer annual attestation, not a
per-reconciliation record — and nothing in SAIRNlaw addresses it at all.

### 1.3 There is a dated cliff, and it is the only one in the series so far that is still ahead

**Regulation (EU) 2024/1624 (AMLR) applies from 10 July 2027**, with
**10 July 2029** for the obliged entities in Article 3(3)(n) and (o). Notaries,
lawyers and other independent legal professionals involved in financial or real
estate transactions — and lawyers whose main profession is tax advice — are
obliged entities. **The privilege carve-out is in the Regulation itself:** it
does not apply to the extent that those persons *ascertain the legal position of
their client, or perform the task of defending or representing that client in,
or concerning, judicial proceedings, including advice on instituting or avoiding
such proceedings*. AMLA guidelines to obliged entities are themselves due **by
10 July 2027**.

**The UK is already there and has been since 2017.** The Money Laundering,
Terrorist Financing and Transfer of Funds (Information on the Payer) Regulations
2017 (SI 2017/692) make an *"independent legal professional"* a relevant person
on essentially the FATF R.22 activity list, and **regulation 40 fixes the
retention period at five years** from completion of the transaction or the end
of the business relationship, including *sufficient supporting records … to
enable the transaction to be reconstructed.*

**So the worldwide AML obligation on law firms is: in force in the UK now,
in force under local 4th/5th-directive transpositions across the EU now, and
re-based onto a directly-applicable EU Regulation on 10 July 2027.** That is a
real date, 20 months out, and unlike b30's trucking cliff it is a *start* date
rather than a lapse.

### 1.4 And one live structural risk, from the regulator itself

**The SRA consulted in 2025 on whether solicitors should hold client money at
all** (consultation closed 21 February 2025). **In December 2025 it decided
not to decide**: it will progress three areas to strengthen the current
regime in the immediate term and return to the wider question — including
whether it is right that solicitors hold client money, and the treatment of
interest — as longer-term reforms. A majority of legal-sector respondents
disagreed with preventing firms from retaining interest; around 40% agreed
that a manager who can make unilateral client-money decisions should not hold
a COLP or COFA role.

**Why this matters to a build decision rather than being trivia:** the single
most valuable asset SAIRNlaw has in E&W is a trust-accounting engine, and the
E&W regulator has an open, un-withdrawn question about whether the firms will
hold the money at all. **That is a roadmap risk a vendor page would never have
disclosed, and it is the clearest single argument in this audit for pulling
primary sources.**

---

## 2. WHAT SAIRNLAW ACTUALLY IS, MEASURED AT HEAD

Universe re-derived, as in b28–b31:

    git ls-files '*.html' | grep -E '^(sairn[a-z]+|stonedesk)\.html$' | wc -l   -> 17

| | measured | command |
|---|---|---|
| registered resources | **20** | bracket-matched parse of `api/_resources/sairnlaw.js`, comments stripped |
| of those, money/trust | **7** — `law_trusttx`, `law_trust_reconcile`, `law_opaccounts`, `law_optx`, `law_bankstatements`, `law_invoices`, `law_timeentries` | same |
| **US state deadline calendars** | **33** | `ls sql/sairnlaw_deadline_calendars_*.json \| grep -v 2027_2031 \| wc -l` |
| **non-US deadline calendars** | **0** | same list: alabama … wisconsin, all US |
| international case-law footprint | **US + UK England & Wales ONLY** | the scope decision is stated as data in `api/_lib/intl-caselaw.js` |
| **AML / CDD / beneficial-owner content in `sairnlaw.html`** | **0** | `grep -nic "money launder\|anti-money\|AML\|know your client\|customer due diligence\|beneficial owner" sairnlaw.html` → `0` |
| retention-policy content | **0** | `grep -nic "retention\|retain for\|purge\|archive after" sairnlaw.html` → `0`. **The three `retain` hits are "retainer"**, which is a different word and is exactly the kind of near-match that makes a grep-based absence claim worth stating with its pattern |

**THE RECONCILIATION ENGINE IS THE GOOD NEWS AND IT IS GENUINELY GOOD.**
`api/_lib/law-trust-reconcile.js` is server-side, pure and integer-cents; it
labels each of its own three legs by the KIND of independence it has rather
than calling them all independent, and it fixes the as-of bug — the bank leg
compares the ledger **as of the statement date** and reports post-statement
movement separately.

**AND THE CLIENT NOW CALLS IT, WHICH IS BETTER THAN THIS AUDIT FIRST WROTE
DOWN.** The old client-side `reconcileTrust()` — the tautology the module
header dissects — **no longer exists.** It was replaced by `trustFigures()`
(`sairnlaw.html:3315`), which displays the three figures and is explicitly
forbidden from deciding whether they agree, plus a real call to the server
endpoint that returns **AGREES / DISAGREES / PARTIAL / CANNOT_RECONCILE**, with
a fifth client-side **UNAVAILABLE**, and *"deliberately refuses a single
boolean"*. A 403 for a non-owner role renders as *"not available to your
role"* — never as agreement. **That is the right shape and it is already
shipped.**

**That engine satisfies the ARITHMETIC half of R1's and R2's three-way
requirement and arguably exceeds it.** The gap is entirely in the artefact.

### 2.1 TWO STALENESS DEFECTS FOUND WHILE MEASURING THIS, BOTH REPORTED NOT FIXED

Neither is in scope for this audit and both are the discipline-#8 class —
*nothing announces the day a reference stops matching.*

1. **`api/_lib/law-trust-reconcile.js`'s header describes a function that no
   longer exists, in the present tense.** Its *"WHAT THE CLIENT ALREADY DOES"*
   section says *"`sairnlaw.html:3134` `reconcileTrust()` already compares three
   figures"*. `grep -n "reconcileTrust" sairnlaw.html` returns **one hit and it
   is a comment saying the function is gone** (`:3288`). The dissection is still
   valuable history; the tense makes a next reader believe a fixed defect is
   live.
2. **The branch is cited at three different line numbers in three places and
   two of the three are wrong.** Re-derived:

   | cited in | says | what is actually there |
   |---|---|---|
   | `api/sd-data.js:1352` (a comment) | `:11690` | a SAIRNcare roster `.map()` — **WRONG** |
   | `sairnlaw.html:3339` (a comment) | `:12439` | an `alf_compliance_rules` comment — **WRONG** |
   | — | — | **real location: `api/sd-data.js:18747`** |

   `grep -n "law_trust_reconcile" api/sd-data.js` is the one-line check, and it
   is the same shape as CLAUDE.md's *"do not write the number down"* rule
   applied to a line number instead of a count.

---

## 3. THE GAP — THREE FINDINGS, EACH TIED TO A PRIMARY CITATION

### 3.1 The reconciliation is computed and thrown away — R1, R2, R4

`law_trust_reconcile` registers **one** action, `read` (`api/sd-data.js:18747`).
There is no write branch, and `grep -n "trust_reconcile" sql/*.sql` returns
**nothing** — no table.

* **R1 (SRA r.8.3)** requires a reconciliation *"a record of which must be
  signed off by the COFA or a manager of the firm"* — a record, signed.
* **R2 (LSO By-Law 9)** requires the monthly comparison be **created within 25
  days** of month end, **signed by the licensee who prepared or approved it**,
  and **retained 10 years plus the current year**.
* **R4 (NY r.1.15)** puts a **seven-year** clock on the records of the same
  account.

**A read-only computation is none of those things.** A firm can run SAIRNlaw's
reconciliation correctly every single month — and it *is* the correct
reconciliation, performed server-side, with a four-outcome verdict — **and have
nothing to produce on inspection.** Crucially, **nothing in the app would tell
them that**, which makes it the platform's own silent-failure class rather than
a missing feature.

### 3.2 There is no cadence and no due date — R1, R2, R3, R5

`grep -ni "signed\|sign_off\|period\|cadence\|monthly" api/_lib/law-trust-reconcile.js`
returns **seven hits and all seven are the arithmetic word "signed"** (deposits
positive, cheques negative). **There is no five-week clock, no 25th-of-the-month
clock, no 60-day external-examination filing clock and no annual CTAPP clock
anywhere in the trust layer.**

**And the app already knows how to do this for a different artefact**, which is
what makes it a gap rather than a research question: there are **33 state
deadline calendars** driving `law_deadlines`. **The machinery for "this is due
on this date in this jurisdiction" exists and has never been pointed at the
firm's own compliance obligations** — only at its matters' court deadlines.

### 3.3 Zero AML capability, against a dated obligation — §1.3

**Zero** matches for money laundering, CDD, KYC or beneficial ownership in
`sairnlaw.html`. Measured, not inferred.

The app has `law_clients` and a client intake, which is **exactly where CDD
attaches** under FATF R.22, UK MLR 2017 reg. 28, and EU AMLR from 10 July 2027.
**This is the one place in this audit where SAIRNlaw is structurally close**:
risk rating, identity evidence with a five-year retention clock, a
beneficial-owner record for entity clients, and a privilege-aware
suspicious-activity path all hang off a client record that already exists and
is already Tier A for confidentiality.

**The privilege carve-out is the hard part and it is a legal design question,
not a schema question.** R.23 and AMLR both exempt what is obtained while
ascertaining a legal position or defending/representing in proceedings — so a
product that prompts a lawyer to report is prompting them to make a privilege
determination. **Getting that boundary wrong in software is worse than not
building it**, which is a decision-gate question and is flagged as one.

---

## 4. WHAT WOULD HAVE TO BE BUILT THAT HAS NEVER BEEN BUILT

| | thing | size | precedent on this platform |
|---|---|---|---|
| **B1** | **Persist and sign the reconciliation.** A `law_trust_reconcile` write branch, a table, the computed legs frozen at run time, the preparer's `employee_id` and role stamped, immutable thereafter | **small — and it is the highest value per line in this audit** | the acting-employee stamp pattern is already shipped in `rf_claims/write`; countersign exists in `sql/sairnlaw_countersign_schema.sql` |
| **B2** | **A compliance-obligation clock**, per jurisdiction, for the FIRM rather than the matter: five weeks (E&W), 25th of the month (ON), 60 days post-period (AU), annual (CA) | **medium** | `law_deadlines` + 33 state calendars is the same shape, aimed elsewhere |
| **B3** | **Retention clocks that differ per regime** — 5 years (UK MLR reg. 40), 7 years (NY r.1.15), 10 years + current (LSO) | **medium**, and it is a DELETION policy, which this platform has never shipped for anything | **none. Zero retention content in any SAIRN app's legal layer** |
| **B4** | **A CDD / AML module** with risk rating, identity evidence, beneficial ownership, and a privilege-aware reporting path | **large, and B4 is where the company decision sits** | none |
| **B5** | **Non-US jurisdiction data at all** — 0 of 33 calendars are non-US; the case-law footprint is a deliberate US + E&W scope decision | **large and it is the 50-state-matrix problem again, in a new coat** | this is the blocker that killed b28 and b30 |

**B1 is buildable now, by one session, and it closes a real compliance gap in
two US jurisdictions and two Commonwealth ones at once.** Everything from B2
down runs into the same wall the series keeps hitting.

---

## 5. THE BLOCKER — AND IT IS THE SAME ONE, FOR THE FIFTH TIME

**B5 is *nobody owns a per-jurisdiction regulatory matrix*, which killed the
childcare audit (b28) and the trucking audit (b30).** SAIRNlaw's 33 US state
deadline calendars are the counter-example and also the warning: **they took
real, repeated, per-state work** — the claim record shows hank seeding
Mississippi, New Mexico, Idaho, Nebraska, Florida and Hawaii one at a time —
**and that is 33 of 50 US states after months. A worldwide version is a
different order of magnitude, not a bigger version of the same thing.**

**B4 adds a second blocker that is new to this series: AML advice is a
regulated activity in its own right in several of these jurisdictions.**
Shipping software that tells a lawyer whether to file a suspicious-activity
report, over a privilege boundary the Regulation itself draws, is not a feature
decision. **It is the same class as b36's dental clearinghouse contract and
b30's administered service: a company decision, not an engineering one.**

**Five of six series blockers are now company decisions.** That is the pattern
and it is worth naming rather than discovering a sixth time.

---

## 6. WHAT THIS AUDIT DID NOT DO — READ THIS BEFORE QUOTING ANY OF IT

* **No competitor product was driven, and no market size is quoted anywhere in
  this file.** That is deliberate: the instruction was primary regulation, and
  a market number sourced from a vendor would have been the exact defect b36
  disclosed. **The consequence is real — this audit does not tell you whether
  anyone else already does B1–B5**, and that is a genuine hole, not a style
  choice. The two 2026-09 SAIRNlaw audits are the competitor-facing half.
* **Nobody was interviewed.** No practising solicitor, no COFA, no Ontario
  licensee, no compliance officer.
* **Every regulatory figure is from a REGULATOR'S OR LEGISLATURE'S OWN SITE,
  REACHED THROUGH A DOMAIN-RESTRICTED SEARCH — AND MOST WERE READ VIA SEARCH
  SNIPPETS RATHER THAN THE FULL INSTRUMENT.** `WebFetch` on the EUR-Lex summary
  returned an empty body and **the fetch failure is reported rather than
  silently replaced with a secondary source**. Treat the rule *numbers* here as
  load-bearing and the *paraphrases* as needing the full text before anything
  is built on them. The URLs are in §8.
* **No consolidated-text check.** SI 2017/692 has been amended repeatedly since
  2017 and this audit read reg. 40 and the "independent legal professional"
  definition, not the amendment history. Same for the NSW rules, which
  `legislation.nsw.gov.au` itself serves in multiple in-force versions.
* **The SAIRNlaw measurements are source reads, not live drives.** No
  reconciliation was run against a deployed instance; the "never persisted"
  finding is from the absence of a write branch and the absence of a table,
  which is strong evidence and not a reproduction.
* **No Tier/criticality consequence was worked out.** If B1 ships, the stored
  reconciliation record is a new Tier A resource and needs a register row and a
  review obligation. Named here so it is not discovered afterwards.

---

## 7. WHAT WOULD HAVE TO BE TRUE

**For B1 — nothing. It is a scoped piece of work against an app SAIRN owns,
and the four regimes above are its specification.** Recommend it independently
of every other finding in this file.

**For B2/B3 — somebody has to own a per-jurisdiction obligation table and keep
it current.** The 33 state calendars prove SAIRN can do this and prove what it
costs. A worldwide table needs a named owner and a maintenance cadence, or it
becomes the stalest thing in the repo and asserts wrong deadlines, which is
worse than no table.

**For B4/B5 — a company decision on whether SAIRN sells into a regulated-advice
space at all.** That question has now been asked by five audits and has not
been answered. **This audit's recommendation is that it be answered before a
sixth is commissioned**, which is also what b30 recommended.

---

## 8. SOURCES — EVERY ONE A REGULATOR, A LEGISLATURE OR THE STANDARD-SETTER

* [FATF — International Standards on Combating Money Laundering and the Financing of Terrorism & Proliferation (the FATF Recommendations)](https://www.fatf-gafi.org/content/dam/fatf-gafi/recommendations/Feburary%202025%20FATF%20Recommendations.pdf) — R.22, R.23
* [FATF — Guidance for a Risk-Based Approach: Legal Professionals (June 2019)](https://www.fatf-gafi.org/content/dam/fatf-gafi/guidance/Risk-Based-Approach-Legal-Professionals.pdf.coredownload.inline.pdf)
* [Regulation (EU) 2024/1624 (AMLR) — EUR-Lex, ELI](https://eur-lex.europa.eu/eli/reg/2024/1624/oj/eng)
* [EUR-Lex summary — Preventing abuse of the financial system for money laundering and terrorism purposes (from 2027)](https://eur-lex.europa.eu/EN/legal-content/summary/preventing-abuse-of-the-financial-system-for-money-laundering-and-terrorism-purposes-from-2027.html) — **WebFetch returned an empty body; read via search snippet only**
* [The Money Laundering, Terrorist Financing and Transfer of Funds (Information on the Payer) Regulations 2017, reg. 40 — legislation.gov.uk](https://www.legislation.gov.uk/uksi/2017/692/regulation/40)
* [SRA Accounts Rules — Solicitors Regulation Authority](https://www.sra.org.uk/solicitors/standards-regulations/accounts-rules/)
* [SRA — Client money in legal services (consultation listing)](https://www.sra.org.uk/sra/consultations/consultation-listing/client-money-legal-services/)
* [SRA Update, issue 146, December 2025](https://www.sra.org.uk/news/sra-update/sra-update-issue-146-december-2025/)
* [Law Society of Ontario — By-Law 9](https://lso.ca/about-lso/legislation-and-rules/by-laws/by-law-9)
* [Law Society of Ontario — Summary of By-Law 9 record-keeping requirements](https://lso.ca/lawyers/practice-supports-and-resources/topics/managing-money/bookkeeping/summary-of-by-law-9-record-keeping-requirements)
* [Legal Profession Uniform General Rules 2015 (NSW SI 2015-246) — legislation.nsw.gov.au](https://legislation.nsw.gov.au/view/whole/html/inforce/current/sl-2015-0246)
* [Legal Profession Uniform Law (NSW) No 16a of 2014 — legislation.nsw.gov.au](https://legislation.nsw.gov.au/view/whole/html/inforce/current/act-2014-16a)
* [New York Rules of Professional Conduct, Part 1200, Rule 1.15 — nycourts.gov](https://www.nycourts.gov/LegacyPDFS/RULES/jointappellate/Joint%20Order%20-%20Part%201200%20-%20Rule%201.15.pdf)
* [State Bar of California — Rules, Title 2, Division 1.5 (Client Trust Account Protection Program)](https://www.calbar.ca.gov/sites/default/files/2025-10/Rules_Title2_Div.1.5-CTAPP.pdf)
