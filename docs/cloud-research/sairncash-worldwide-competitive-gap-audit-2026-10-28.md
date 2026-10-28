# Worldwide competitive-gap audit: SAIRNcash

**fourth / b64, 2026-10-28.** This continues the queued order: mechanical, build, then SAIRNcash.

**What the app is.** In its own words, an *"AI Financial Co-Pilot for Freelancers"* (`sairncash.html:18`). It does three things:
- quarterly federal estimated-tax set-asides;
- deduction categorisation;
- SEP IRA / Solo 401(k) room.

It is **US federal, self-employment income only**, and it files nothing.

## Where this comes from

**It is built only from research already on file.** Nothing was fetched for this pass:

| source | its evidence grade, as it states it |
|---|---|
| `docs/superpowers/specs/2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md` §1, §2, §7, §9, §10 | supplied testimony, no URLs, no non-English section. A4 was flagged for a patent screen |
| `docs/cloud-research/sairncash-external-competitive-gap-audit-2026-09-26.md`, in full | **[SNIPPET] throughout**. It read the code at `3238bf61` / `c0ae9a0a` |
| `docs/2026-09-15-…-mechanical-and-five-apps.md`, the SAIRNcash rows | 0 of 33 rows had moved by then |

**Audit only:** `sairncash.html` is in 0 of this batch's commits. Each status below comes from reading the code at `d92ead730`. The file was last changed in `e137c3bc1`.

---

## 0. The result

> **The September tax-calculation findings were fixed within a day of being written:** the safe-harbour basis, the MFS 110% trigger, tax-year splitting and QBI. The research document still reads as if they were open. **What remains are defects in the profile and entry records that feed the calculation.** Two of them make the answer look safer than it is.

Outside the US, the research on file contains nothing, and neither does the code. There is no currency, no tax id and no country.

---

## 1. Defects in records the app already writes

**Read from the code, not run.** Each needs a claim on `sairncash.html` and its own record.

1. **A hidden checkbox is saved as a real answer, and it removes a warning.**
   - `profAgiOver150k` is `display:none` (`sairncash.html:367`). `saveProfile()` `sairncash.html:1579` still saves it as a boolean, which is `false` for a new user.
   - `priorYearAgiForCalc()` `sairncash.html:1573` then returns `{legacyOver150k:false}`.
   - The result: a single, MFJ or HoH filer who enters last year's tax but leaves AGI blank gets the 100% figure **without** the "AGI not recorded, 110% may apply" warning. An unsaved profile does get that warning.
   - The code's own comment near `sairncash.html:1567` names this "flattering reading".
2. **A typed $0 is dropped.** `Number(…) || null` in `saveProfile()` turns an entered prior-year tax of 0 into "not provided".
3. **Solo 401(k) room can exceed what the user earned.** `calcRetirementEstimate()` `sairncash.html:1505` computes, at line 1512, `min(deferral + base, 72000)` with no cap at net earnings. At $5,000 of profit it shows about $25,000 of room.
4. **The retirement figure uses year-to-date profit, while the tax figure beside it is projected for the full year.** The label implies an annual figure.
5. **An entry's date is the moment it was typed.** `addIncomeEntry()` `sairncash.html:1606` and `addDeductionEntry()` `sairncash.html:1611` stamp `new Date()`, and the forms have no date field. December income typed in on 2 January lands in the wrong tax year. This was open in September and is still open.
6. **No entry can be corrected or removed.** There is no update or delete path for an income or deduction entry, so a mistyped amount stays in the totals for good.
7. **A failed save is silent.** The awaited Firebase `push` and `set` have no catch, so no error is shown.

**Items 1 and 3 are the ones that matter most.** In both, the app shows a more comfortable number than the inputs support.

---

## 2. The September findings, status now

| finding (09-26) | status | where |
|---|---|---|
| safe harbour compared against YTD tax, not full-year | **fixed** (`ec93b60c7`, `607f227f2`); with no data the result is null rather than 0 | `projectAnnualFromYtd()` `sairncash.html:1396`, `calcQuarterlySetAside()` `sairncash.html:1444` |
| MFS 110% trigger at $75k | **fixed** | `safeHarborAgiThreshold()` `sairncash.html:1215` |
| entries not split by tax year | **fixed**; entries it cannot place are disclosed | `entriesForTaxYear()` `sairncash.html:1632` |
| QBI (§199A) not applied | **built, partial**: flagged uncertain above a conservative ceiling | `calcQbiDeduction()` `sairncash.html:1319` |
| HoH/MFS brackets unverified | **re-verified in code**: the HoH 24% top corrected from 201,775 to 201,750 | comment near `sairncash.html:1164` |
| deadlines run out; no disaster postponement | **open**: returns null after the last 2026 deadline | `nextQuarterlyDeadline()` `sairncash.html:1687` |
| disclaimer does not say federal only | **partial**: "federal" appears only in one label | n/a |
| Form 2210 annualisation | **absent**, and disclosed as such | n/a |
| Solo 401(k) catch-up and the §401(a)(17) limit | **absent**, and deferred in a comment | n/a |
| assistant should refer out state, crypto and foreign topics | **absent** (`crypto`, `multi-state` ×0) | n/a |
| calculator test suite | **built**: `tests/sairncash_safe_harbor.js` | n/a |

**From 09-03:**
- A1, invoice follow-up: **absent**.
- A2, cash-flow prediction: **absent by design**; the insights panel looks backward only.
- A3, bank scanning: **absent** (`bank`, `plaid`, `CSV` ×0). The categoriser exists.
- A4, agentic action: **absent on purpose**. The page says it *"will never file anything on your behalf"*.

## 3. Outside the US

**Nothing on file, in the research or the code.** `VAT`, `GST`, `HMRC`, `CRA`, `EIN`, `SSN` and `TIN` all return 0. Money is a hard-coded `$` with `toFixed(2)`. The page is `lang="en"`, and the "2026" labels are fixed strings.

**This is the one app in the series where "absent" is plainly correct and plainly the whole story.** A US self-employment estimated-tax calculator has no non-US equivalent to be partly built. Taking it abroad would mean a separate calculator per country, not a gap in this one. **No research was done, so no market claim is made.**

## 4. Write sites

Financial records are written **client-side to Firebase RTDB** under `sairncash/customers/{customerId}/`. There is no server endpoint, and `api/sd-data.js` has no SAIRNcash branch.

| record | write site | fields |
|---|---|---|
| income | `addIncomeEntry()` `sairncash.html:1606` | amount, description, date (time of entry), created_at |
| deduction | `addDeductionEntry()` `sairncash.html:1611` | amount, category (default "Uncategorized"), description, date, created_at |
| profile | `saveProfile()` `sairncash.html:1579` | filing_status, prior_year_tax_liability, prior_year_agi, prior_year_agi_over_150k, retirement_vehicle. **A full overwrite** |

The only server writes are billing and lead records: waitlist, trial start and the Stripe webhook.

## 5. Corrections to the record on file

1. **09-26 §1.2, §1.3 items 1, 2a and 4, and the §3.1 HoH/MFS note are overtaken by code.** The research file was edited afterwards only for a citation fix (`1d46ab8dc`), so it still reads as open.
2. **09-26 says `1099` ×0.** The 1099-K guidance ($20,000 / 200, "still taxable") now exists in the assistant prompt.
3. **The 09-29 inventory says this audit lives only on a cloud branch.** It is on main.

## 6. Unverified: read before quoting anything externally

- **Every 09-26 statute and threshold** is [SNIPPET]: IRC §6654, Pub 505, OBBBA §§70432–70433, Rev. Proc. 2025-32, Notice 2025-67 and CFPB §1033.
- **§3.4 and §8 (GLBA, §7216)** are marked "needs counsel / not established".
- **The 09-03 pricing note** is unverified.
- **No regulator was read for this document.**

## 7. What this does not do

It changes no code. §1 items 1–3 are small, contained fixes to how the profile and the estimate are computed, but each changes a number a user acts on. **They should be fixed under a claim, with a test against the 1040-ES worksheet that `tests/sairncash_safe_harbor.js` already follows.**
