# SAIRNsenior — round 22: sweep v2, West Virginia's licensure answer, and a corrected state list

2026-08-30. **Research only.** Thirty-second document in the series.

Three things: **the sweep is now bidirectional and its first version of the new
patterns was too loose** (recorded, because the fix matters more than the run);
**West Virginia's article 2C is settled — it is not licensure**; and **the
remaining-states list I was given contains three states already completed**,
which is corrected here rather than re-done.

---

## 1. Sweep v2 — bidirectional, and my new patterns were sloppy

**The flaw v2 was built to fix:** v1's ten patterns only matched statutes that
**deem** workers employees. Delaware — which expressly **permits** independent
contractors — was invisible to it and was found by reading.

**v2 adds a PERMIT group and reports polarity per hit.** Tally across every
corpus on disk: **DEEM 7, ROLE 9, PERMIT 42.**

> **And the PERMIT count is misleading, which is my error, not the corpus's.**
> Two of the new patterns — `employ or contract with` and
> `…or (through) contract arrangements` — match **neutral** phrasing that
> contemplates contractors without taking any position on their status. They fired
> in Colorado, Louisiana, South Carolina, Iowa, Michigan, Nevada, Oregon and
> others, none of which is a Delaware-style permission.
>
> **The signal that actually works is the literal phrase "independent
> contractor", read in context.** Re-run on that alone, the picture is clean and
> the polarity table survives — but **a broad pattern that produces 42 hits and
> one real finding is not a sweep, it is noise with a true answer inside it.**
> Recorded so v3 narrows rather than widens.

### What the narrow re-run actually shows — a fourth polarity

| Polarity | State | Text |
|---|---|---|
| **Forbids** | **Rhode Island** | *"shall be considered employees and **not** independent contractors"* — in both the staffing and home-care parts |
| **Permits** | **Delaware** | *"through contract arrangements, **including those contracts with individuals considered to be independent contractors**"* |
| **Premises a category on it** | **Iowa** | *"'Independent nursing services professional' means a person engaged **as an independent contractor** through a health care technology platform"* |
| **Extends duties to them** | **Nevada**, **Michigan**, **South Carolina** | the obligation follows the person **regardless of status** |

**The fourth is the most common and the least noticed.** Examples:

- **Nevada** NRS 449.0113 — *"Duties of administrator or licensee if Central
  Repository unable to complete investigation of **employee or independent
  contractor**…"* The background-check machinery names contractors explicitly.
- **Michigan** — "employee or independent contractor" appears in the nursing home
  definition, and § 20173a's employment bar already reaches *"employ,
  independently contract with, or grant clinical privileges to."*
- **South Carolina** — the TB-screening rule defines *"employee"* to include a
  person *"whether a direct employee or an independent contractor, and whether
  full-time, part-time, temporary or in any other capacity."*

> **A state can be entirely silent on employment *status* while making every duty
> *status-blind*.** For a product this is arguably the more important pattern:
> it means **the compliance record must exist for contractors too**, even where
> the state never says who the employer is.

**Two hits worth discarding explicitly**, so nobody re-reads them as findings:
**Louisiana** § 105 is a conflict-of-interest rule (no immediate family as
employee, consultant or independent contractor); **Colorado** § 26 permits
training to be *produced by* an independent contractor — a training vendor, not a
caregiver.

---

## 2. West Virginia — article 2C is NOT licensure, and there is no home health licensure article

Round 21 flagged this as unresolved. **Settled: W. Va. Code art. 16-2C has five
sections and none of them licenses anyone.**

> § 16-2C-1 Definitions · § 16-2C-2 **Department to provide services**; charges
> for services; authority to employ personnel · § 16-2C-3 **Local boards'
> authority** respecting home health services · § 16-2C-4 **Funds received** for
> home health services · § 16-2C-5 **Collection of fees** for home health
> services.

**Article 2C authorises the State and local boards of health to *provide* home
health services and to charge for them.** It is a public-provision article.

**And chapter 16 contains no home health agency licensure article at all.** Of
**156 articles**, the ones with "licensure/licensing" in the title are: 5H
*Chronic Pain Clinic Licensing Act*, **5I *Hospice Licensure Act***, 5O and 5AA
*Medication Administration by Unlicensed Personnel*, 5Y *Medication-Assisted
Treatment Program Licensing Act*, 34 *Radon*, 60 *EMS Personnel Licensure
Compact*, 68 *Alcohol and Drug Counselors*. **Hospice is licensed by statute;
home health is not.** Article 5D — the obvious candidate — is **repealed**.

> **Stated with its limit.** What is established is that **no home health agency
> licensure article exists in W. Va. Code ch. 16**. **Whether West Virginia
> licenses home health agencies by *legislative rule*** (W. Va. C.S.R. under the
> Secretary's general § 16-1-4 authority) **was not checked**, and West Virginia
> may also rely on Medicare certification as Michigan does. **Do not read this as
> "West Virginia does not license home health."** It is one level short of that.

---

## 3. The remaining-states list, corrected

I was asked to continue with *"Michigan, Alabama, Kentucky, Mississippi,
Arkansas."* **Three of those five are already complete**, and re-doing them would
have been silent duplicate work:

| State | Actual status |
|---|---|
| **Michigan** | **DONE — round 11.** Public Health Code Art. 17 read: MCL 333.20106(1) omits home health agencies from the licensed list, MCL 333.20173a makes a Medicare-certified home health agency a *covered facility* under a 15-year employment bar. |
| **Kentucky** | **DONE — round 9.** 902 KAR 20:081: 6 + 3 hours of dementia training pre-service, 14-day/60-day supervisory cadences, pre-employment abuse-registry and criminal checks. |
| **Arkansas** | **DONE — round 10.** 20 CAR pt. 45: 40 hours ⊃ 16 demonstrated ⊃ 4 dementia, employer self-certification, client-age (50+) scope trigger. |
| **Alabama** | **NO ROUTE** — round 11. `alison.legislature.state.al.us` and `admincode.legislature.state.al.us` are SPA shells; `alabamapublichealth.gov` serves **HTTP 200 with a "404page" body**; the state routes its code to **LexisNexis**, which is JS-gated. |
| **Mississippi** | **NO ROUTE** — round 11. Its own legislature site links the code to **LexisNexis**; `sos.ms.gov` admin-code page is navigation only. |

**Genuinely untouched, or open-but-unread:** **Hawaii** (route open, sections not
identified), **South Dakota** (SPA; seven endpoint forms excluded), **Alaska**
(route confirmed working, Title 7 not walked). **Blocked:** Alabama, Mississippi,
Utah, Connecticut, Kansas. **Closed:** Idaho (state-side outage). **On hold:**
Indiana (API key).

---

## 4. Tier 2

| Item | Status |
|---|---|
| W. Va. C.S.R. (legislative rules) for home health licensure | **NOT CHECKED** — the level below the code. |
| WV arts. 5I, 5N, 5R, 5X, 5AA | **NOT READ** |
| Sweep v3 pattern narrowing | **NOT DONE** — v2's PERMIT group needs replacing with the literal-phrase-plus-context approach described above. |
| HI sections, SD endpoint, AK Title 7 | **OPEN** |
| DE administrative code (the operative standards) | **NOT READ** |

## 5. Method notes

- **A sweep that widens its patterns can get worse.** v2's PERMIT group returned
  42 hits and one real finding. The narrow literal phrase returned the same
  finding plus a genuinely new category. **Precision beat recall here, and the
  first instinct was the wrong one.**
- **"Silent on status" and "status-blind duties" are different things**, and the
  second is more common. A state that never says who the employer is can still
  require every check to cover contractors.
- **Check the completed list before starting.** Three of five named states were
  already done. Saying so is cheaper than doing them twice.
