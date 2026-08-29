# SAIRNsenior — state-by-state variation

2026-08-29. **Research only. No app behaviour changed by this document.**

Opens item 1 of the five left open by `2026-08-28-narrow-verification-pass-results.md`
§7 — licensure, training hours, background checks, wage/sick-leave. It does not
close it. What it does is establish a **small core that is actually verified** and
put an honest boundary around everything else.

## How to read this document

Two tiers, and nothing moves between them without a fresh primary fetch.

- **Tier 1 — personally verified.** Every claim below was fetched from the
  issuing government's own site during this pass and is quoted or paraphrased
  from the retrieved text. Safe to encode.
- **Tier 2 — not independently checked.** Named gaps, conflicts, and dead
  sources. **Not safe to encode.** Each carries why it is here.

---

## Tier 1 — verified from primary source, 2026-08-29

### Washington

**Training — RCW 74.39A.074(1)(b).** A long-term care worker must complete
**75 hours of entry-level training** approved by the department within
**120 calendar days after the date of being hired**, and **5 of those 75 hours
before being eligible to provide care.**

**Certification timing — WAC 246-980-030.** A worker may provide care before
certification only if they complete the RCW 74.39A.074(1)(d)(i)(A)–(B) training
first and **submit the certification application within 14 calendar days of
hire**. Eligibility to work uncertified ends if the 120-day training deadline is
missed, or if certification is not obtained within **365 calendar days from date
of hire** — **425 days** with a provisional certificate under RCW 18.88B.035.

> **The 365/425-day rule is dated, and this is the part worth carrying.** The
> regulation says in terms: *"These timelines go into effect August 25, 2025,
> through December 31, 2027. These timelines apply to a pending applicant or a
> new applicant who has submitted an original application for certification as a
> home care aide by December 31, 2027."* Retrieved version filed under
> **WSR 26-12-065, effective 2026-07-03**. A product that hard-codes 365 will be
> wrong for anyone applying after 2027-12-31. **Encode it as a dated rule with
> an expiry, not as a constant.**

**Training exemptions — RCW 18.88B.041** (most recent amendment 2025 c 18 s 1).
Exempt from the certified home care aide training requirement: registered
nurses, LPNs and certified nursing assistants; persons hired before
**2012-01-07** who met the then-current requirements; all long-term care workers
employed by community residential service businesses; workers providing in-home
care **only to family members** (child, parent, sibling, spouse, domestic
partner, extended relatives); a worker providing **20 hours or less of
non-respite care for one person in any calendar month**; and a respite-only
worker working **fewer than 300 hours in any calendar year**.

**Paid sick leave — RCW 49.46.210.** Accrual **1 hour per 40 hours worked**;
unused leave carries over but the employer need not allow carryover **in excess
of 40 hours**.

**Negative finding — L&I Administrative Policy ES.C.2 is "Hours Worked."**
Fetched the policy PDF directly. It covers travel time, internships,
preparatory/concluding activities and on-call time as general Minimum Wage Act
principles. **It contains no home-care, domestic-worker or individual-provider
rule.** Any home-care-specific claim cited to ES.C.2 is miscited. This confirms
the prior pass's fabrication finding against the source document itself.

### New York

**Home care minimum wage — Public Health Law § 3614-f**, "Home care minimum wage
increase," applying to home care aides as defined in § 3614-c. Retrieved
schedule: a **$2.00** add-on to the otherwise-applicable minimum wage from
2022-10-01; then stated hourly floors — 2024 **$18.55** downstate / **$17.55**
rest-of-state; 2025 **$19.10 / $18.10**; **2026 $19.65 / $18.65**. From
**2027-01-01** the rate moves to an annual CPI-based *"home care worker wage
adjustment,"* capped at the Commissioner of Labor's wage plus **$3.00** in
either region.

> **Same shape as the WA rule and the same instruction:** the printed schedule
> runs out at the end of 2026. From 2027 the number is *computed*, not listed.
> Do not ship 2026's figure as the current rate past 2026-12-31.

### California

**Training — Health and Safety Code § 1796.44.** Affiliated home care aides
require **a minimum of 5 hours of entry-level training prior to presence with a
client** — **2 hours orientation** plus **3 hours safety training** covering
basic safety precautions, emergency procedures and infection control — and **a
minimum of 5 hours of annual training** covering core competencies (clients'
rights, assistance with daily living, abuse prevention, personal hygiene, safe
transportation). Training may be completed online.

> **Dated element, third one in this document:** an additional annual topic —
> *"special care needs of clients with dementia"* — applies **as of
> 2027-01-01**. The section was **repealed and re-added by Stats. 2025,
> Ch. 414**, so any pre-2025 secondary summary of § 1796.44 should be treated as
> superseded rather than merged.

**Background check — HSC § 1796.19** requires *"a review of the … applicant's
criminal offender record information pursuant to Section 1522 or 1522.7,"* as
part of determining reputable and responsible character. The statute as
retrieved does **not** name a registry in this section and does **not** state
automatic disqualification — only that the record be reviewed. (Which department
administers it is a Tier 2 conflict; see below.)

**Paid sick leave — Labor Code § 246** (as amended Stats. 2023, Ch. 309,
operative 2024-01-01). Eligibility at **30 or more days** worked for the same
employer within a year. Accrual **not less than 1 hour per 30 hours worked**.
Employer may cap use at **40 hours or 5 days** per year; no obligation to allow
total accrual to exceed **80 hours or 10 days**. Availability floors: at least
**24 hours or 3 days by the 120th calendar day**, **40 hours or 5 days by the
200th calendar day**.

### Florida

**Background screening — Fla. Stat. § 408.809**, "Background screening;
prohibited offenses." **Level 2 screening under chapter 435** conducted through
the agency, required of the licensee (if an individual), the administrator, the
financial officer, controlling-interest persons, and employees or contractors
providing personal care or having access to client funds or living areas.
**Rescreening every 5 years** following licensure, employment or entry into a
contract, as a condition of retaining the licence or continuing employment.

### Cross-state pattern worth encoding once

Three of the four states above put a **date-bounded** rule inside what looks like
a fixed number: WA's 365-day window expires 2027-12-31, NY's printed wage
schedule ends 2026-12-31, CA adds a dementia topic 2027-01-01. This is the same
lesson the federal pass reached about the FLSA companionship rule
(`2026-08-28-narrow-verification-pass-results.md` §3) — **encode as dated,
configurable rules with a re-check date, never as constants.** It is the single
most transferable finding here.

---

## Tier 2 — reported, not independently checked

**Do not encode anything in this section.**

### First, a provenance problem that has to be stated

The prior pass's research payloads for this item **are not on disk in this
clone** — no state-variation file exists in `docs/`, `docs/superpowers/specs/`
or scratch, and nothing in git history carries them. So this document **cannot**
reproduce a large "reported" tier with each payload's own provenance label,
because those payloads are unrecoverable here. Rather than restate them from
memory — which is exactly the failure mode the two-tier split exists to prevent —
Tier 2 below carries **only what this pass actually touched and could not
confirm**, plus named gaps. If the payloads exist in another clone, they should
be committed there before anyone tries to merge them into this file.

### Conflicts and dead sources found this pass

| Item | Status | Provenance |
|---|---|---|
| Which CA department administers the § 1796.19 criminal-record review | **CONFLICT, unresolved** | The § 1796.19 fetch summarised the administering body as the Department of Health *Care Services*; CDSS's own Community Care Licensing page shows home care under **CDSS**, with a Care Provider Management Branch and LiveScan process. The statute text itself says only "the department." Not resolved — do not cite either. |
| CA Home Care Aide Registry — its statutory basis, fees, renewal | **NOT FETCHED** | CDSS landing page served navigation only; the substantive program pages were not retrieved. |
| MA home care worker registry / 105 CMR | **RESOLVED — and my diagnosis in this row was wrong.** See `2026-08-29-sairnsenior-domestic-worker-overtime.md` | I wrote below that the obstacle was a bot wall "not an empty page". Both are true at once: mass.gov 403s automated fetch (curl with a browser UA too) **and** the regulation page is a landing shell whose only content is a PDF link, exactly as the prior pass said. My correction narrowed a correct note wrongly. The real unblock is that **`malegislature.gov` is a different host and is not blocked** — every MA statute now cited came from it. 105 CMR 155.000's scope and section list were read; §§ 155.010 and 155.016 text was not. |
| TX HCSSA licensure and personal-assistant training (26 TAC ch. 558) | **PARTLY RESOLVED.** See `2026-08-29-sairnsenior-domestic-worker-overtime.md` | The Appian portal navigates but **never reaches document-idle**, so text extraction, element search and screenshot all time out, and the `rule=` parameter is silently dropped. Recorded unusable after three attempts. Home health aide requirements (75 hrs, 16 classroom before clinical, 16 clinical, RN competency evaluation) obtained instead from **HHSC's own pre-survey training modules** — a primary *agency* source restating the rule, **not** the codified text of 26 TAC § 558.701. Personal Assistance Services requirements remain entirely unretrieved. |
| WA annual continuing-education hours for long-term care workers | **NOT IN THE SECTION READ** | RCW 74.39A.074 as retrieved states entry-level training only. The 12-hour figure commonly quoted was **not** confirmed and is not carried here; it lives in a different section that was not fetched. |
| NY PCA/HHA training hours (40 / 75) | **NOT FETCHED** | Widely reported; no primary fetch attempted this pass. |
| State domestic-worker overtime rules | **DONE for six states, and the premise was wrong.** See `2026-08-29-sairnsenior-domestic-worker-overtime.md` | The carried-forward wording — "these survive a federal FLSA rescission" — does **not** hold. Connecticut (C.G.S. § 31-58(e)) and Oregon (ORS 653.547(1)(b)(B)(ix)) each define coverage by reference to the federal FLSA regulations, so a DOL rescission propagates into their state law. Oregon additionally excludes employees of licensed in-home care agencies from its Domestic Workers' Protection Act entirely. |
| All 46 states not named in Tier 1 | **NOT ATTEMPTED** | Stated so the four-state core is not read as coverage. |

---

## What this changes about the open-work position

`2026-08-28-narrow-verification-pass-results.md` §7 item 1 stays **open**. It is
narrower by four states across four axes, and it now has a method that works
(direct statute/regulation fetch from `app.leg.wa.gov`, `nysenate.gov`,
`leginfo.legislature.ca.gov`, `flsenate.gov` — all four returned real statutory
text) and two publishers that defeat it (`mass.gov` 403, Texas SOS Appian
portal). Anyone continuing this should start with the four working publishers and
treat MA and TX as their own problem.

## Method notes worth carrying

- **`leginfo.legislature.ca.gov` `codes_displaySection.xhtml` returns a
  disambiguation page, not text**, for any section amended more than once in a
  session — § 1796.44 was repealed *and* re-added by the same 2025 chapter, so
  the section URL gave only a "multiple results exist" stub twice. The
  **`codes_displayText.xhtml` article URL** returned the full text. If a CA
  section looks empty, it probably was amended twice; switch URL form before
  concluding the text is unavailable.
- **A "multiple results exist" stub is itself a finding** — it means the section
  changed recently, which is precisely when a cached secondary summary is most
  likely to be stale.
- Where a fetch **summarised** rather than quoted (the CA § 1796.19 department
  attribution), that summary is an inference by the fetch layer, not the source
  speaking. Those go to Tier 2. This caught one wrong department name in this
  pass alone.
