# Worldwide competitive-gap audit — SAIRNBIZ

**fourth / b41, 2026-10-20.** Fourth in the primary-sources-only set, after
sairnlaw (b37), sairncode (b38) and sairndesign (b39). **The first in the
series that cites EU law from source from the start**, through the CELEX route
b40 fixed. `sairnbiz-external-competitive-gap-audit-2026-09-26.md` already
exists and is **competitor- and US-payroll-facing**; this is the
EU-employment-and-invoicing lens and does not refresh it.

**SIX INSTRUMENTS AND ONE JUDGMENT READ FROM SOURCE.** Where an article number
appears below, its text was fetched from
`http://publications.europa.eu/resource/celex/<CELEX>` and the article was
read in full. Nothing below is quoted from a summary.

**AUDIT ONLY: `sairnbiz.html` is in 0 of this batch's commits.** Every finding
below that touches the app is a source read of a write site, named with its
line.

---

## 0. THE RESULT

> **SAIRNbiz holds the three records EU employment and VAT law ask about —
> pay, hours and invoices — and each is shaped so the question cannot be
> answered from it.**

| record | write site | fields | the question it cannot answer |
|---|---|---|---|
| employee | `saveEmp()` `sairnbiz.html:2433` | `id fn ln role dept type rate pay_freq start phone email status ec notes` (+`ben`) | **average pay by sex for the same work or work of equal value** — Pay Transparency Directive Art. 7, *every* employer, two months |
| timesheet | `saveTimesheet()` `:3427` | `id emp week hours` — **six daily totals, Monday to Saturday** | **how long each worker worked each day, and whether 11 consecutive hours of rest followed** — WTD Arts 3, 5, 6 as read in CJEU C-55/18 |
| invoice | `saveInv()` `:2634` | `id cust date due amt paid status cat` | **the 15 mandatory particulars** — VAT Directive Art. 226: sequential number, both VAT IDs, addresses, VAT rate and amount |

`grep -ci` over the whole file, **each hit read**:

| term | hits |
|---|---|
| `gender` / `sex` | **0 / 0** |
| `pay transparen` / `pay gap` / `equal pay` | **0 / 0 / 0** |
| `VAT` (case-sensitive, word) | **0** — the 14 case-insensitive hits are inside words like *private* |
| `UBL` / `peppol` / `e-invoic` / `16931` | **0 / 0 / 0 / 0** — the 13 case-insensitive `UBL` hits are inside *public* and *double* |
| `EUR` (word) / `country` | **0 / 0** |
| `rest period` | **0** |

**Stated because an alternation count is worthless without reading the
hits** — the same rule b39 applied to `ADA` inside *UNREADABLE*.

---

## 1. THE INSTRUMENTS

| instrument | CELEX | fetched | in force / applies |
|---|---|---|---|
| **Pay Transparency Directive** (EU) 2023/970 | `32023L0970` | 200, 192,706 B | **transposition deadline 7 June 2026** (Art. 34(1)) — **passed four months ago** |
| **Working Time Directive** 2003/88/EC | `32003L0088` | 200, **PDF** 118,061 B (no XHTML manifestation) | in force since 2004 |
| **CJEU C-55/18 *CCOO v Deutsche Bank SAE*** (Grand Chamber) | `62018CJ0055` | 200, 114,294 B | judgment of 14 May 2019 |
| **Transparent and Predictable Working Conditions Directive** (EU) 2019/1152 | `32019L1152` | 200, 135,967 B | **transposition 1 August 2022** (Art. 21(1)) |
| **VAT Directive** 2006/112/EC | `32006L0112` | 200, 1,724,486 B | **original OJ text — see §5** |
| **GDPR** (EU) 2016/679 | `32016R0679` | 200, 804,894 B | applies from **25 May 2018** (Art. 99(2)) |

**Five of the six are DIRECTIVES.** They bind Member States, and an employer's
duty is the national transposition, which this audit did **not** read. Every
finding below is stated against the Directive's text and says so. **GDPR is a
Regulation and applies directly.**

---

## 2. THE GAPS

### 2.1 **PAY: THE RIGHT TO INFORMATION HAS NO SIZE THRESHOLD, AND THE ROSTER HAS NO SEX FIELD**

**Pay Transparency Directive Art. 7(1):** *"Workers shall have the right to
request and receive in writing … information on their individual pay level
and the average pay levels, broken down by sex, for categories of workers
performing the same work as them or work of equal value to theirs."* **Art.
7(4):** within **two months**. **Art. 7(3):** employers must tell all workers
**annually** that the right exists.

**Art. 7 carries no headcount threshold.** The thresholds in this Directive
are on **Art. 9** gender-pay-gap *reporting* — **250+ by 7 June 2027 and
annually; 150–249 by 7 June 2027 and every three years; 100–149 by 7 June
2031** (Art. 9(2)–(4)). **SAIRNbiz's customer — a small trade business — is
outside Art. 9 and squarely inside Art. 7.**

**What the record lacks, by the Directive's own terms:**

1. **Sex.** `0` hits. An average *"broken down by sex"* cannot be computed.
2. **A category of work of equal value.** **Art. 4(4)**: pay structures must
   let the employer assess comparability *"on the basis of objective,
   gender-neutral criteria … They shall include skills, effort,
   responsibility and working conditions."* `role` is free text and `dept` a
   department; **neither is a job-evaluation category**, and two people with
   different `role` strings doing work of equal value would never be grouped.
3. **What already works, said so it is not lost:** `rate` + `pay_freq` per
   employee is the *individual pay level* half, and the app already
   normalises pay frequency (`sbPayFreq()`).

**Pre-employment, Art. 5:** *"the initial pay or its range, based on
objective, gender-neutral criteria"* (5(1)(a)); **no pay-history question**
(5(2)); gender-neutral job titles (5(3)). The hiring record (`saveHire()`)
has a **free-text** *"Pay Rate Range"* (`#hrate`, `:446`, placeholder
`$18-22/hr`) — **the right shape, not tied to any criteria** — and **asks no
pay history** (the one `desired` hit in the file, `:4934`, is a code comment).

### 2.2 **HOURS: A DAILY TOTAL CANNOT SHOW A REST PERIOD, AND THERE IS NO DAY SEVEN**

**WTD Art. 3:** *"a minimum daily rest period of 11 consecutive hours per
24-hour period."* **Art. 5:** *"per each seven-day period … a minimum
uninterrupted rest period of 24 hours plus the 11 hours' daily rest."* **Art.
6(b):** average working time *"for each seven-day period, including overtime,
does not exceed 48 hours"*, over a reference period of up to **four months**
(Art. 16(b)).

**CJEU C-55/18, operative ruling:** Arts 3, 5 and 6, read with Charter Art.
31(2) and Directive 89/391/EEC, *"must be interpreted as precluding a law of a
Member State that … does not require employers to set up **a system enabling
the duration of time worked each day by each worker to be measured**."*

**What `saveTimesheet()` stores is `hours` — six numbers per week, one per day,
Monday to Saturday** (`:3427`, the modal at `:576` says *"Six day cells and
nothing else"*). Measured against the text:

1. **Art. 3 cannot be evaluated.** Eleven *consecutive* hours of rest needs a
   start and an end per day. A total of 9 hours is consistent with 08:00–17:00
   and with 20:00–05:00 followed by 08:00 the next day.
2. **Art. 5 and Art. 6 cannot be evaluated across a seven-day period, because
   the record has six days.** **There is no Sunday cell.** Hours worked on a
   Sunday have **nowhere to be entered** — which is not a reporting gap but a
   *recording* gap, and under C-55/18 the recording is the obligation.
3. **The 48-hour average needs a rolling reference period** (Art. 16(b));
   the app computes weekly overtime above a single threshold (`:5393`–`:5402`)
   and has no multi-week average.

**THE DAY-SEVEN GAP IS ALSO A US QUESTION** — overtime is computed over the
workweek, and a week with no Sunday cell cannot include Sunday hours in it.
**I did not read the US workweek rule this batch** (29 CFR Part 778 is not
cited here); the EU finding stands on the text above, and the US one is named
for the next read rather than asserted.

### 2.3 **THE WRITTEN STATEMENT: SEVEN DAYS, AND THE ROSTER HOLDS HALF OF IT**

**TPWC Art. 4(2)** lists the essential aspects an employer must give in
writing; **Art. 5(1)**: points (a)–(e), (g), (k), (l) and (m) **"no later than
the seventh calendar day"**, the rest within one month.

| Art. 4(2) | on the employee record? |
|---|---|
| (a) parties | name — yes |
| (b) place of work | **no** |
| (c) title/category or description | `role` — yes, free text |
| (d) start date | `start` — yes |
| (e) fixed-term end date | **no** (`type` holds *Full Time* etc., not an end date) |
| (g) probation | **no** |
| (k) remuneration, components separately, frequency and method | `rate`, `pay_freq` — **partly**; method of payment **no** |
| (l) standard day/week, overtime arrangements | **no** per-employee schedule |
| (m) unpredictable pattern: guaranteed hours, reference hours, notice | **no** |

**There is no "statement issued on" date anywhere**, so even where the data
exists the app cannot show the seven-day duty was met.

### 2.4 **INVOICES: AN ID THAT IS NEITHER SEQUENTIAL NOR UNIQUE**

**VAT Directive Art. 226(2):** an invoice must carry *"a sequential number,
based on one or more series, which uniquely identifies the invoice."*

`saveInv()` (`:2634`) sets `id:'INV-'+String(Date.now()).slice(-4)` — **the
last four digits of the millisecond clock.** That is:

* **not sequential** — consecutive invoices get unrelated numbers;
* **not unique** — the four digits repeat every 10,000 ms, so two invoices
  created 10 s, 20 s, … apart (±1 ms) collide, and `invs.push(r)` does not
  check. Per pair of invoices that is **1 in 10,000**, and a business issuing
  thousands of invoices accumulates pairs quadratically.

**The same pattern names employees** — `'E'+String(Date.now()).slice(-4)` in
`saveEmp()` (`:2433`). **This is a defect independent of any EU rule**: the
invoice `id` is also the GL `source_id` (`sbGlPost(... source_id:r.id ...)`),
so a collision joins two invoices' ledger entries to one identifier. **Recorded
here, not fixed — `sairnbiz.html` is audit-only this batch.**

**The other particulars, Art. 226(3)–(10):** supplier VAT ID, customer VAT ID
where liable, full names and addresses, nature and quantity, supply date,
taxable amount per rate, unit price, **VAT rate, VAT amount** — **none is on
the record**, and `VAT` is 0 hits. **SAIRNbiz is a US-shaped invoicing tool**;
an EU sale would need this whole field group, not a tweak.

### 2.5 **HEALTH DATA: THE OSHA LOG IS ART. 9 DATA IN THE EU**

The injury and illness log (`sb_incidents`, built at `:4824`) stores
`date emp job where desc classification type days_away days_restricted
privacy` — **data concerning health, linked to a named employee.** **GDPR Art.
9(1)** prohibits processing it unless an exception applies; the relevant one is
**9(2)(b)** — *"necessary for the purposes of carrying out the obligations …
in the field of employment and social security and social protection law in so
far as it is authorised by Union or Member State law"*. **Art. 88** lets Member
States set more specific employment rules, health and safety at work named
among the purposes.

**So the lawful basis is national, not universal**, and an EU deployment of
this panel needs the Member State's authorising law named per install. The
app's existing **`privacy` flag** (the OSHA privacy-concern case) is the right
instinct and is **not** a GDPR mechanism — it hides a name on a printed log; it
does not restrict who can read the record or for how long it is kept
(`retention`: **1** hit file-wide).

---

## 3. WHAT IS ALREADY RIGHT

* **`rate` + `pay_freq` is the individual half of Art. 7**, and pay frequency
  is already normalised in one function.
* **No pay-history question** in hiring (Art. 5(2)), and a pay **range**
  field exists (Art. 5(1)(a)'s shape).
* **The timesheet refuses non-numeric and out-of-range hours** and refuses a
  new week for a departed employee *on the write path*, not only the button
  (`:3427`–`:3446`) — the recording discipline C-55/18 asks for, applied to the
  wrong unit (a total rather than a time).
* **The incident log already has a privacy-case flag**, which is the seed of a
  GDPR access restriction.

---

## 4. WHAT WOULD HAVE TO BE BUILT

| | thing | size | blocker |
|---|---|---|---|
| **Z1** | **Invoice and employee ids that are sequential and unique** — a per-series counter for invoices (Art. 226(2)), a collision-checked id for employees. **A defect fix before it is a compliance feature.** | **small** | none — **do first** |
| **Z2** | **A seventh day on the timesheet**, then **start/end times per day** so Art. 3's 11 hours and Art. 5's 24+11 can be evaluated | small, then medium | none |
| **Z3** | **Pay Transparency: a sex field (with a "not recorded" state, never a default) and a job-evaluation category** on the employee record, and an Art. 7 answer: individual pay + average by sex for the worker's category, with the **denominator** shown and a refusal below a minimum cell size | medium | **the minimum cell size is a privacy call, and the national transposition sets it** |
| **Z4** | **A written-statement record**: the Art. 4(2) fields the roster lacks, and an *issued on* date checked against the seven-day duty | medium | national templates (Art. 5(2)) |
| **Z5** | **An EU invoice field group** (Art. 226(3)–(10)) | large | which Member States, and whether e-invoicing is in scope (not read) |
| **Z6** | **GDPR Art. 9 controls on the incident log**: role-restricted read, a retention period, the authorising national law named per install | medium | national law per Member State |

**Z1 and the first half of Z2 have no blocker and are small.** Z1 is a defect
in shipped behaviour regardless of jurisdiction.

---

## 5. WHAT WAS NOT READ — REPORTED, NOT PARAPHRASED

1. **No national transposition** of any of the five Directives. Every
   Directive finding is against the Directive's text; the employer's duty is
   the Member State's law.
2. **The VAT Directive is the 2006 Official Journal text, NOT consolidated.**
   Art. 226 has been amended since (invoicing rules were revised in 2010, and
   the 2025 *VAT in the Digital Age* package changes e-invoicing). **Art.
   226(2)'s sequential-number requirement is quoted from the original and was
   not re-checked against the consolidated version.** The e-invoicing rules
   were **not read at all**.
3. **No US source was read this batch.** The day-seven point (§2.2) is named
   for 29 CFR Part 778, not cited from it.
4. **Targeted extraction, not whole reads**: each article quoted was read in
   full; the rest of each instrument was not.
5. **No competitor was driven and no market figure is quoted** — the same
   deliberate hole as b37–b39. The 2026-09-26 audit is the competitor lens.
6. **Nothing was driven in the app.** Every app finding is a source read of
   the write site named. The invoice-id collision rate is arithmetic on the
   expression, not an observed collision.
7. **No legal review.**
