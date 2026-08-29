# SAIRNsenior — CMS EVV guidance located, and state research round 2

2026-08-29, later the same day. **Research plus one comment-only code change**,
described in §4. Third document in the series; read after
`2026-08-29-sairnsenior-state-variation.md` and
`2026-08-29-sairnsenior-domestic-worker-overtime.md`, same two-tier rule.

---

## 1. CMS EVV guidance — FOUND, and both prior explanations were half right

**The page is at**
`medicaid.gov/medicaid/home-community-based-services/home-community-based-services-guidance-additional-resources/electronic-visit-verification`

Reached by pointing a real browser at the old
`.../guidance/electronic-visit-verification-evv` path and letting the redirect
run. That closes item 4 of `2026-08-28-narrow-verification-pass-results.md` §7 as
a *search*; the documents themselves are still unread.

### Why neither earlier note could have found it

| Recorded | When | Verdict today |
|---|---|---|
| "medicaid.gov and cms.gov return 403 to automated fetch" | before 2026-08-28 | **Right about medicaid.gov, wrong about cms.gov** |
| "Both return 200; the EVV page 404s — it moved" | 2026-08-28 | **Right that it moved, wrong that medicaid.gov is reachable** |

Measured today, four ways: **every** medicaid.gov URL tried — the guidance path,
the PDFs, and the **site root** — returns **403** to both WebFetch and `curl`
with a full Chrome user-agent. `cms.gov` returns **200**. Chrome loads all of
them normally.

So the honest description is: **the host blocks automated clients, AND the page
had moved.** Each note captured one half and each half implied a remedy that
would fail on its own — "blocked" says wait and retry, "moved" says find the new
URL, and the thing that actually worked was **a different client**. The general
form is worth keeping: *a reachability claim is about a host, a client, and a
date. Drop any of the three and the note goes wrong quietly.*

### What the page says (quoted from the live page)

> "States must require Electronic Visit Verification (EVV) use for all
> Medicaid-funded PCS by January 1, 2020 and HHCS by January 1, 2023. Otherwise,
> the state is subject to incremental FMAP reductions up to 1% unless the state
> has both made a 'good faith effort' to comply and has encountered 'unavoidable
> delays.'"

Scope is stated as PCS under §§ 1905(a)(24), 1915(c), 1915(i), 1915(j), 1915(k)
and § 1115, and HHCS under § 1905(a)(7) or a waiver.

### The ten documents it indexes — the actual reading list

1. Documenting EVV in Applications for 1915(c) Waivers and Other Programs — May 2022
2. **CIB: Additional EVV Guidance — August 2019**
3. **Requests from States for Good Faith Effort Exemptions — December 2022**
4. EVV Update — August 2018
5. EVV Requirements in the 21st Century Cures Act: NASUAD Pre-Conference Intensive — August 2018
6. EVV Requirements in the 21st Century Cures Act: NASUAD Conference Workshop — August 2018
7. **CIB: Cures Act for Electronic Visit Verification — May 16, 2018**
8. **FAQs: Cures Act for Electronic Visit Verification — May 16, 2018**
9. CURES Act EVV Systems Session 2: Promising Practices for States Using EVV — January 2018
10. CURES Act EVV Systems Session 1: Requirements, Implementation, Considerations, and State Survey Results — December 2017

Plus sub-pages: EVV Outcomes-Based Certification, per-state EVV compliance status
for PCS and for HHCS, and Good Faith Effort Exemption Requests.

**None has been read.** The bolded four are the load-bearing ones. They are PDFs
on medicaid.gov, so they need the browser, and Chrome's PDF viewer is
canvas-backed — the same wall that stopped 105 CMR 155 below. **That is the next
concrete obstacle, and it is a PDF-extraction problem, not a discovery problem.**

---

## 2. Tier 1 — new states, verified from primary source 2026-08-29

### The finding that should shape the schema

**Most states do not set a training-hour number at all.** Of eleven states now
read on aide training, only four state hours:

| State | Requirement | Source |
|---|---|---|
| Washington | **75 hours** in 120 days, 5 before care | RCW 74.39A.074(1)(b) |
| Texas | **75 hours** min, ≥16 classroom before clinical, ≥16 clinical | 26 TAC § 558.701 *(agency restatement)* |
| Georgia | **40 hours** — but only as **one of four** alternative pathways | Ga. Comp. R. & Regs. 111-8-65-.09 |
| California | **5 hours** entry (2 orientation + 3 safety) + **5 annual** | HSC § 1796.44 |

The other seven — **PA, VA, MN, NC, NY, FL (homemaker/companion), NJ** — impose
**competency, not hours.** A data model with a required `training_hours` integer
per state would be **empty or wrong for most of the map**, and would invite
someone to fill it with a number from a vendor blog. The correct shape is a
**qualification-pathway** model: a worker satisfies a state by matching **one of
N enumerated routes**, only some of which are hour-denominated.

Georgia proves the point inside a single state: 40 hours is the *fallback*
route, sitting alongside three competency routes.

### The states

**New York — 10 NYCRR 700.2.** A home health aide *"shall have successfully
completed a basic training program in home health aide services or an equivalent
exam approved by the department"* (¶ 9). A personal care aide (¶ 14) qualifies by
**one of four** routes: the HHA program or equivalent exam; **one full year of
experience** through a home care services agency within the preceding three
years; a personal care training program per **18 NYCRR 505.14(a) and (e)**; and,
where health-related tasks are involved, that training **completed in full before
assignment to any patient**.

> **Correction to a widely-repeated figure.** The familiar "NY = 40-hour PCA /
> 75-hour HHA" numbers **are not in 700.2**. The regulation points to
> *department-approved programs* and to 18 NYCRR 505.14. Those hour figures were
> listed as unverified in the first document and **remain unverified** — the
> section everyone would cite for them does not contain them.

**Pennsylvania — 28 Pa. Code ch. 611** (Home Care Agencies and Home Care
Registries). § 611.55 competency: before assignment a direct care worker must
hold a nurse's licence, **pass a competency exam, or complete an approved
training program** covering at minimum confidentiality, consumer control,
infection control, emergency handling and abuse recognition. **No hours.**
§ 611.52 requires a criminal history report obtained at application or **within
1 year immediately preceding** it; § 611.53 adds child-abuse clearance; § 611.54
provides for provisional hiring.

**Georgia — Ga. Comp. R. & Regs. 111-8-65-.09.** A Personal Care Assistant hired
after the rule's effective date must have **one of**: a nurse-aide training and
competency evaluation program under 42 CFR pt. 483 subpt. D; a department-
recognised nurse-aide competency examination; a department-approved health care
or personal care credentialing program; or **"successful completion or progress
in the completion of a 40 hour training program provided by a private home care
provider"** covering enumerated areas (ambulation and transfer, bathing,
toileting, grooming, and more). **"or progress in the completion of"** is
load-bearing — Georgia lets a PCA start mid-course. Background: **fingerprint
records check** under Chapter 111-8-12 before serving as a direct access
employee, plus **TB screening per CDC guidance before starting work**, annual
performance evaluation, and **bonding** where the employee has unlimited access
to client funds.

**Virginia — 12VAC5-381.** § 290: home attendants must speak, read and write
English **and** meet **one of six** qualifications — RN/LPN education program
completed; Board-of-Nursing-approved nurse aide education program; Board
certification as a nurse aide; enrolled in a nursing program having completed at
least one clinical course; passed a competency evaluation meeting **42 CFR
484.36(b)** (personal-care attendants need only the tasks relevant to personal
care); or the DMAS **"Personal Care Aide Training Curriculum," 2003 edition**
(personal care only). § 110: criminal record report from the **Virginia
Department of State Police** obtained **within 30 days of employment**, **not
dated more than 90 days before** employment, original only, against the barrier
crimes in Va. Code § 32.1-162.9:1 — with a defined letter substitute for
temp-agency staff.

**Minnesota — Minn. Stat. § 144A.4795.** Subd. 1: all staff must *"be trained and
competent … consistent with current practice standards appropriate to the
client's needs"* and be informed of the home care bill of rights (§ 144A.44).
Subd. 3: unlicensed personnel providing **basic** home care must complete a
training and competency evaluation **or** demonstrate competency by written/oral
test, **plus a practical skills test** on specified topics; basic-provider staff
**may not perform delegated nursing or therapy tasks**. Unlicensed personnel
doing delegated nursing for a **comprehensive** provider face the higher bar, one
route being the Medicare home-health-aide requirements at 42 CFR 483/484.36.
Subd. 7 enumerates the training content (documentation, reporting changes,
infection control, safe environment, hygiene and grooming, **falls prevention**,
standby assistance, medication/exercise/treatment reminders, nutrition and meal
safety). **Two tiers, no hours.**

**North Carolina — 10A NCAC 13J.** In-home aide services are defined at .0901(13)
as hands-on home management, personal care or supervision tasks. For **in-home
aides not listed on the nurse aide registry**, personnel records must contain
**verification of core competencies by a registered nurse** — mobility/ambulation
/transfers/bed mobility, bath/shower, toileting and the rest — **for aides hired
after April 1, 2009**. Supervision and competency sit at .1110. **Competency,
verified by an RN, no hours.**

**Florida — the registration/licensure split matters commercially.** § 400.509
lets a **homemaker or companion services organization register** rather than be
licensed: **$50 per biennium**, a duty to obtain and **verify employment or
contract history** for staff with client contact, and **no training or in-service
hour requirement in the section at all**. A registrant **may not provide a home
health service**. (Persons contracted with the Agency for Persons with
Disabilities providing companion services solely to individuals with
developmental disabilities are exempt from registration outright.) Contrast
§ 408.809's **level 2 screening with 5-year rescreening**, verified this morning,
which attaches to **licensed** providers. **Two Florida businesses that look
identical to a customer sit under materially different obligations, and which one
applies turns on whether any service crosses into home health.**

**New Jersey — Domestic Workers' Bill of Rights, effective 2024-07-01.** NJDOL,
the administering agency: overtime **1.5× over 40 hours**; a live-in worker
**"must be paid for at least 8 hours for each day you are on duty"**; **written
agreement** required for workers exceeding five hours a month covering duties,
wages, schedule and breaks; **10-minute paid breaks every four hours**; privacy
protections barring retention of personal documents, monitoring of
bathroom/bedroom/dressing areas, and interference with private communications.
Excluded: family members, government employees, kinship caregivers, home-based
business workers, house-sitters, pet-sitters, repair workers, and casual or
irregular workers. The statutory route is that domestic workers are brought
inside the "employee" definition feeding **C.34:11-56a4**, rather than given
their own overtime clause.

**Texas — Personal Assistance Services, partially.** PAS-only agencies must
designate an **administrator and an alternate**, both of whom must complete the
**Presurvey CBT**, which satisfies the Presurvey Conference licensure
requirement. First-time administrators designated after **2006-12-01** need
**8 clock hours** of administration training on the topics at **26 TAC
§ 558.259** in the 12 months **before** designation, plus **16 additional clock
hours** within the first 12 months **after**. Where RN delegation is used, the
agency must employ or contract the delegating RN, who follows **22 TAC § 225**.
**All of this is administrator-side.** The requirement for the **unlicensed
personal assistant** — the worker SAIRNsenior actually schedules — is **still
unretrieved**.

---

## 3. Tier 2 — reported, not independently checked

**Do not encode anything in this section.**

| Item | Status | Provenance |
|---|---|---|
| MA 105 CMR 155.010 and .016 (registry duties, registry contents) | **UNREADABLE by every method tried** | mass.gov 403s WebFetch and curl; Chrome renders the PDF but the viewer is canvas-backed, and it does not respond to scroll, Page_Down, scrollbar drag or `#page=` — five attempts across two sessions, always page 1. Scope and section list are known from the search index and the PDF's own contents page; **the substantive text is not.** |
| NY 40-hour PCA / 75-hour HHA figures | **STILL UNVERIFIED, and now known not to be where they are usually cited** | Not in 10 NYCRR 700.2. Would need 18 NYCRR 505.14 and the department's approved-program standards. |
| TX unlicensed personal assistant requirements | **UNRETRIEVED** | Only administrator-side requirements were found. The codified 26 TAC text remains unreachable via the Appian portal. |
| MA c. 151 § 1A hospital/nursing-home exemption wording | **SUMMARISED, NOT QUOTED** | Carried unchanged from the overtime document. |
| The remaining ~35 states | **NOT ATTEMPTED** | Sixteen states now have at least one verified axis. That is not coverage. |

---

## 4. The one code change

`api/_lib/sen-evv-readiness.js` — **comment and string only.** The header note and
the `residual_gaps[0]` string now carry the located URL, the ten-document list in
summary, and the correction that both earlier reachability claims were half
right. The gap itself is **not** closed and is not described as closed: it is
restated as *a reading task rather than a search*.

Verified before pushing, and stated rather than implied:

- `node --check` passes.
- The module loads and its exports are unchanged:
  `FEDERAL_ELEMENTS, FEDERAL_SOURCE, CHECKABLE_STATUSES, checkVisit, summarize`.
- A diff filter for changed lines that are **not** comments and **not** string
  literals returns **empty** — 23 insertions, 10 deletions, all prose.

**Disclosed, not glossed:** the full 30-check Guardian pass
(`## The 30 Checks`, count re-read from the skill heading today rather than
trusted from CLAUDE.md) was **not** run, on the grounds that no executable line
changed. That is a judgment call, and it is written here so it is reviewable
rather than invisible.

## 5. Method notes worth carrying

- **`curl` beat WebFetch on four state hosts today** — `regs.health.ny.gov`
  403s WebFetch and 200s curl; `reports.oah.state.nc.us` is HTTP-only and
  WebFetch upgrades to HTTPS, which fails outright. For statute and regulation
  sites, **probe with curl first, then extract locally**; it is cheaper and it
  does not truncate.
- **Probe a batch of hosts for status codes before fetching any of them.** Eight
  candidate publishers were checked in one pass; seven were live and one
  (casetext) returned **410 Gone**. That is thirty seconds against several
  wasted fetches.
- **Canvas-backed PDF viewers defeat browser automation completely** — no text
  extraction, and in this case no scrolling either. Two separate targets (MA
  105 CMR 155, the CMS EVV PDFs) are blocked on the same mechanism. Solving it
  once unblocks both, and it is now the single highest-leverage tooling gap in
  this research line.
- **Check whether a famous number is actually in the section everyone cites.**
  NY's 40/75 is not in 10 NYCRR 700.2. A figure repeated confidently across
  secondary sources is exactly the kind that never gets checked.
