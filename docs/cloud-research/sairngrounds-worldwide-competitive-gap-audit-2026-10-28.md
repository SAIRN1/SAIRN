# Worldwide competitive-gap audit: SAIRNgrounds

**fourth / b64, 2026-10-28.** This is the last of the queued order: mechanical, build, cash, then grounds. SAIRNgrounds is landscaping and grounds maintenance, with golf-course operations. That includes a bar (alcohol sales) and a bottle scanner.

## Where this comes from

**It is built only from research already on file.** Nothing was fetched for this pass:

| source | its evidence grade, as it states it |
|---|---|
| `docs/superpowers/specs/2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md` §0–2, §6, §8–10 | supplied testimony, no URLs; no non-English section; no patent screen |
| `docs/cloud-research/sairngrounds-external-competitive-gap-audit-2026-09-27.md`, in full | **[SNIPPET] throughout**, because every fetch was blocked by egress. Its regulatory lens is **Ohio and US federal only** |
| `docs/2026-09-15-…-mechanical-and-five-apps.md` §1 | 0 grounds rows had moved by then |

**No research on file covers any non-US instrument for grounds work.** It does not cover FIFRA by name either, or H-2B.

**Audit only:** `sairngrounds.html` is in 0 of this batch's commits. Each status below comes from reading the code at `d92ead730`. The file was last changed in `e137c3bc1`.

---

## 0. The result

> **The regulated record a lawn and grounds business is most often asked for, the pesticide application record, does not exist.** Neither does an applicator-licence register. The September findings about the bar (sale hours, permits, server age) are all unchanged. Reading the write sites found four defects in records the app already keeps. **One of them makes a cleared Sunday open all day.**

---

## 1. Defects in records the app already writes

**Read from the code.** Each needs a claim on `sairngrounds.html` and its own record.

1. **Clearing a day's sale hours opens it all day.** `saveMsbHours()` `sairngrounds.html:5092` turns an empty start into `'00:00'` and an empty end into `'23:59'`. So "no sales on Sunday" saves as **sales all Sunday**. The only way to close a day is an inverted window. **This is an alcohol-sale control, so it is the one to fix first.**
2. **Quote lines lose their text.** `saveQuote()` `sairngrounds.html:2414` takes the last comma part of each line as the amount:
   - a line with no comma ("Mulch") saves as `{d:'', a:0}`;
   - "Mulch, 3 yards" saves as `d:"Mulch", a:0`.
3. **A job can be marked Complete with no photo.** The 09-03 audit says completion is photo-gated, but the gate covers only scheduled visits, and only on the client:
   - `saveJob()` `sairngrounds.html:2385` writes "Complete" with no check;
   - the server's `grd_schedule` write accepts `status:'complete'` ungated.
4. **DreamClose:** the visit it creates has no `status` field, and its status line always says "0 until priced".

---

## 2. The regulated records

| finding (09-27, all [SNIPPET]) | instrument (as the research names it) | status | nearest record |
|---|---|---|---|
| G-1 pesticide application record | ORC 921 / OAC 901:5-11-10 | **absent** (`pesticide`, `applicator`, `SDS`, `restricted use` ×0) | `saveInvasive()` `sairngrounds.html:4282`, with free-text `method` and `treated` fields |
| applicator licence register (category, Sept 30 expiry, recertification credits) | ORC 921 | **absent**: training completions store only name, course, status and date | n/a |
| weather on the application record | OAC 901:5-11-10 | **partial**: temperature and wind reach the dashboard only, with no wind direction and nothing attached to a record | `sairnLoadWeather()` `sairngrounds.html:5272` |
| 24-hour lawn posting | OAC 901:5-11-09 | **absent** | n/a |
| copper Notice of Intent for ponds | Ohio EPA OHG870003 | **absent** (no permit field on water features) | n/a |
| fertiliser go/no-go (western basin) | ORC 905.326 (applicability unknown) | **absent**: the go/no-go checks temperature, wind and weather code only | n/a |
| water-withdrawal log | ORC 1521.16 | **absent** | n/a |
| G-2 bar sale hours, Sunday, permits, server age | OAC 4301:1-1-49, ORC 4303.182, 4301.22 | **unchanged**: every day is seeded 10:00–23:59; a window cannot cross midnight; the permit list is Texas types only; no age check reaches the server | `msbEnsureSaleHoursSeeded()` `sairngrounds.html:4656`, `msbIsAlcoholSaleAllowedNow()` `sairngrounds.html:4661` |
| G-3 bottle scanner shipped with no freedom-to-operate check | US 9,576,267, US 11,639,868, US 2019/0197466 | **unchanged** | n/a |
| minor-labour guardrails | ORC 4109, 29 CFR 570.33 | **absent** | n/a |
| SDS register (HazCom 2024, by 2026-11-20) | OSHA | **absent** | n/a |
| mower rollover and slope pre-operation checks | OSHA | **absent** | n/a |

**Also unchanged from 09-27:**
- G-4: demo data seeds on every licence (`seed()` `sairngrounds.html:2078`), and the merge keeps demo rows beside server rows;
- G-5: pace of play is timed by hand.

**From 09-03, all absent:** flat-price positioning, satellite measurement, review requests and win-back, a tee sheet, multi-course operation, and multi-division/snow. Purchase orders are partial: vendors exist.

## 3. Outside the US: the research never looked

The research on file names **no** non-US instrument for pesticides, labour, alcohol or invoicing. The code has no tax, VAT or GST field, `fmt()` hard-codes `$` with `en-US`, and weather is °F/mph.

**This is a coverage hole, not a clean result.** The record such a regime would most likely land on is the one §2 says does not exist: the pesticide application record. So the US-only answer and the worldwide answer are the same first step.

## 4. Write sites

| record | write site | fields |
|---|---|---|
| property | `saveProp()` `sairngrounds.html:2356` | id, name, type, acreage (typed), contact, phone, email, address, status, notes |
| job | `saveJob()` `sairngrounds.html:2385` | id, property_id, scope, date, status, notes |
| quote | `saveQuote()` `sairngrounds.html:2414` | id, property_id, lines[{d,a}], status, valid |
| schedule / visit | `saveSched()` `sairngrounds.html:3514` | id, property_id, freq, next, crew (free text), quote_id, status |
| invoice | `saveInv()` `sairngrounds.html:3783` | id, property_id, quote_id, amount, status, issued, due, notes |
| invasive treatment | `saveInvasive()` `sairngrounds.html:4282` | free-text method and treated |

There is **no crew roster record**: crews are derived from the schedule's free-text `crew` strings. **There is no chemical or pesticide log.**

## 5. Corrections to the record on file

1. **The 09-03 photo gate for job completion covers only scheduled visits, and only on the client** (§1 item 3).
2. **09-27 counts `pesticide` ×4.** It is now **0**; the hits were `herbicide` strings.
3. **The 09-03 citation `sairngrounds.html:591` for the completion gate** is now near `:636`.

## 6. Unverified: read before quoting anything externally

- **Every 09-27 statute, permit and patent number** is [SNIPPET]. The ORC 905.326 applicability is marked unknown there.
- **Every 09-03 market claim** is supplied testimony.
- **No regulator was read for this document.**

## 7. What this does not do

It changes no code. §1 item 1 (sale hours) is a control on alcohol sales and should be fixed first. The pesticide application record (§2, G-1) is the largest gap. It is a product decision, because it brings in licence categories, posting and weather capture together.
