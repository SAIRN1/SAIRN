# SAIRNsenior — round 23: Hawaii licenses home care and exempts individuals; Alaska and South Dakota are JS-gated below the index

2026-08-30. **Research only.** Thirty-fourth document in the series.

**Hawaii opened and is a distinct model.** Alaska and South Dakota are now
**diagnosed rather than merely blocked** — both serve a top-level index and
require JavaScript to go one level deeper, reached by different routes.

---

## 1. Hawaii — HRS § 321-14.8, "Home care agencies; licensing"

Found by the **TOC-first** method again: the chapter 321 table of contents lists
§ 321-14.8 by name. **Seventh state in a row where the index was the whole
answer.**

> "(a) **Beginning July 1, 2010, each home care agency shall be licensed by the
> department of health** to ensure the health, safety, and welfare of clients.
> (b) The department … shall adopt rules … to (1) protect the health, safety, and
> civil rights of clients … and (2) provide for the licensure of home care
> agencies."

### The definition carries an individual-provider carve-out

> "'**Home care agency**' means a public or proprietary agency, a private,
> nonprofit organization, or a subdivision of an agency or organization, engaged
> in providing home care services to clients in the client's residence. **'Home
> care agency' does not apply to an individual, including an individual who is
> incorporated as a business, or is an unpaid or stipended volunteer.**"

> **A solo caregiver is outside Hawaii's licence — even if incorporated.** No
> other state read has drawn the line at *the individual* and then closed the
> obvious workaround in the same sentence. **For a product this matters
> commercially, not just legally:** in Hawaii the single-operator caregiver is a
> lawful, unlicensed market segment, and an agency of two is not.

**"Home care services"** are defined as: **personal care** (assistance with
dressing, feeding and personal hygiene to facilitate self-care); **homemaker
assistance** (housekeeping, shopping, meal planning and preparation); and
**respite care and assistance and support provided to the family.**

**An eighth answer to the unlicensed-segment question:** Hawaii **licenses the
non-medical home care agency directly** — no nursing predicate at all — while
exempting individuals entirely.

### Two limits written into the licensing section itself

**§ 321-14.8(c) — payer-based exemptions.** A service provider agency is exempt
when services are provided **under contract with the City and County of Honolulu,
Elderly Affairs Division**, or **exclusively to participants in the Medicaid
1915(c) home and community based services waiver** through an agency approved by
DHS Med-QUEST.

> **Third payer-based carve-out in the survey**, after Arkansas's DHS exemption
> and Nebraska's § 71-6504. **The obligation depends on who pays**, so a Hawaii
> agency serving both waiver and private-pay clients is exempt for one and
> licensed for the other — and the exemption requires the waiver work to be
> **exclusive**, which a mixed book of business would forfeit.

**§ 321-14.8(d) — a scope-of-practice boundary inside the licence.** A home care
agency **"shall only provide home care services or related tasks, functions, and
activities in accordance with its license, and shall not provide services
authorized by chapter 457 unless those services are provided by a registered
nurse, a licensed practical nurse, or an advanced practice registered nurse."**

**Contractor/reclassification check: zero hits.** Hawaii is **silent** on
employment status. *(Recorded per the standing practice; and per round 22,
silence is not a position.)*

Amendment history is active: **L Sp 2009 c 21; am 2014 c 125; 2018 c 148; 2019
c 91 and c 158** — five touches in a decade, so the operative rules (adopted
under HRS chs. 91 and 201M) are worth checking for currency when they are read.

---

## 2. Alaska and South Dakota — the same failure, reached two different ways

Both states **serve a working top-level index and then require JavaScript.**

**Alaska.** `akleg.gov/basis/aac.asp` and `/basis/statutes.asp` **render the
title lists server-side** — Administrative Code titles 1 through 6+ and the
Statutes title list are readable in the fetched HTML. **But `?title=7` and
`?title=47` are ignored**: both return the same list, 999 and 2,005 characters
respectively. **The index is real; the drill-down is client-side.**

*(Both pages also carry the stale banner "This page is no longer used please use
www.akleg.gov" while being served from www.akleg.gov — recorded in round 21 and
still true.)*

Other Alaska routes excluded this round: `touchngo.com` (third-party mirror,
**DNS failure**), `akleg.gov/basis/folioproxy.asp` (**HTTP 500**).
`health.alaska.gov` loads and has a Background Check Program section, but is
programme information rather than code.

**South Dakota.** Now **eleven endpoint forms excluded**, all returning the same
2,256-byte Vue shell:
`/Statutes/34-12` · `/Statutes/34-12/PDF` · `/api/Statutes/34-12` ·
`/api/Statutes/34-12?all=true` · `/api/Statutes/Chapter/34-12` ·
`/api/Statutes/Chapter?Code=34-12` · `/api/Statutes/Chapters?title=34` ·
`/api/Statutes/Codified/34-12` · `/api/Statutes/Codified?Code=34-12` ·
`/api/Statutes/ContentsByChapter/34-12` · `/api/Statutes/Title/34` — including
with `Accept: application/json`. The companion host `mylrc.sdlegislature.gov`
returns **404** on both `/api/Statutes/Chapter/34-12` and
`/api/Documents/Statute/34-12.pdf` — **a different answer from the shell, which
still suggests the right host and the wrong path.**

> **Diagnosis for both: "index server-side, content client-side."** That is a
> *fifth* distinct blocking shape, alongside header-blocking (mass.gov,
> medicaid.gov), soft-200 error bodies (Alabama, Connecticut, Rhode Island's
> statute host), bot walls (Oregon OARD, Arizona) and JS-gated commercial
> publishers (Alabama, Mississippi via LexisNexis).
>
> **Both are browser-solvable in principle** — Chrome renders them — but the
> Arizona experience (Chrome loads the PDF, canvas viewer, `fetch` times out) is
> why that is not automatically the answer, and **neither state is worth that
> cost while the substantive findings are already this dense.** Recorded as a
> known-shape, known-cost decision rather than an open task.

---

## 3. Tier 2

| Item | Status |
|---|---|
| Hawaii Administrative Rules under HRS § 321-14.8 (HAR title 11) | **NOT READ** — the operative standards. § 321-14.8 is enabling; the training, screening and supervision content lives in the rules. |
| HI §§ 321-13.5 (certified nurse aides; abuse and neglect investigations), 321-1.9 (inspections of licensed care facilities) | **NOT READ** — both relevant to axes C and E. |
| HI ch. 457 (nursing) boundary | **NOT READ** — cross-referenced by § 321-14.8(d). |
| Alaska 7 AAC 12; AS 47.32 | **JS-GATED below the index** |
| South Dakota codified laws | **JS-GATED; 11 endpoint forms excluded** |
| AL, MS, UT, CT, KS | **NO ROUTE** — carried. |
| ID | **CLOSED** — state outage. |
| IN | **ON HOLD** — API key. |

## 4. Method notes

- **TOC-first, seventh consecutive state.** Hawaii's § 321-14.8 was named in the
  chapter table of contents. No keyword sweep produced it; no guessed citation
  would have.
- **A carve-out can close its own loophole.** Hawaii exempts "an individual,
  **including an individual who is incorporated as a business**". Reading only
  the first clause would have produced the wrong commercial conclusion.
- **"Index server-side, content client-side" is a distinct diagnosis** and worth
  naming, because it looks like success at the first fetch. Both Alaska and South
  Dakota return a real, useful index and nothing beneath it.
- **Excluding eleven endpoints is a result.** South Dakota is not "blocked" in
  the sense Alabama is; it is a known shape with a known cost, deliberately not
  paid.
