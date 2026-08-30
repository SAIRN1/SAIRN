# SAIRNsenior — state round 5: Tennessee in full, Colorado's licensure chapter, and Arizona still closed

2026-08-30. **Research only.** Seventh document in the series. Five-axis
pathways model throughout.

Three things this round establishes that no earlier round could:

1. **Tennessee's home health chapter contains no background-check rule at all** —
   the mirror image of Ohio, which contains nothing but one.
2. **Colorado's licensure chapter is the richest state read so far**, and its
   personal care worker requirement is **stacked on top of** the homemaker one —
   a shape no flat per-role record can hold.
3. **Arizona's Administrative Code resisted the browser too.** Recorded as
   closed, with what was tried, rather than left as an open intention.

---

## 1. Tennessee — 0720-27 read in full

`publications.tnsosfiles.com/rules/0720/0720-27.20260318.pdf`, 107 KB of text,
version **2026-03-18**. Fifteen rules: definitions, licensing, discipline,
administration, admissions/discharge/transfers, basic agency functions,
infectious waste, records, patient rights, health-care decision-making, disaster
preparedness.

### Axis A — the aide standard, and it defers to the federal rule

§ 0720-27-.06(7)(a): aides are selected on *"a sympathetic attitude toward the
care of the sick; the ability to read, write and carry out directions; and the
maturity and ability to deal effectively with the demands of the job"*, and must
be *"formally and carefully trained"* in an enumerated list — self-reliance in
nutrition and meal preparation, the aging process and emotional problems of
illness, maintaining a clean and healthy environment, **changes in condition that
should be reported**, the work of the agency and the health team, ethics,
confidentiality, respect for human dignity and individual differences, and record
keeping.

Then the line that changes how the 75 hours should be stored:

> "Any home health aide training programs **must comply with the federal home
> health aide training and competency regulations.**"

**Tennessee's 75/16 is not an independent state number — it tracks the federal
standard.** Same coupling shape as Connecticut's and Oregon's overtime
definitions, on a different axis. A state whose figure is a pointer to a federal
rule moves when that rule moves, and should not be stored as a state constant.

### Axis E — a monthly supervisory visit, in the home

§ .06(7)(b): the aide is **assigned to a particular patient by a registered
nurse**, with written instructions prepared by an RN or therapist.

§ .06(7)(c): the RN *"shall make a supervisory visit to the patient's residence
**at least monthly**, either when the aide is present to observe and assist or
when the aide is absent (**preferably alternating visits**), to assess the aide's
competence in providing care and determine whether goals are being met."*

§ .06(7)(d): *"There shall be continuing in-service programs on a regularly
scheduled basis with on-the-job training during supervisor visits."*

**That is a recurring, schedulable, per-patient obligation** — monthly, located
at the patient's residence, alternating between aide-present and aide-absent. It
belongs in a scheduling product, not a compliance sidebar, and no other state
read so far specifies the alternation.

### Axis D and general personnel

§ .06 requires an ongoing educational programme, **orientation to the
organisation, its policies, the position and the duties**, with records of subject
and attendance; personnel records kept current with job descriptions,
**verification of references and credentials** and performance evaluations. An
**annual influenza vaccination programme** must at least offer vaccination to all
staff and independent practitioners; **continuing education on infection
control** is required for all patient care providers, *"as evidenced by the
ability to verbalize/or demonstrate an understanding of basic techniques."*

### Axis B — absent, and the absence is the finding

**A full-text sweep of 0720-27 returns no criminal-background-check requirement.**
Every hit on "criminal" is liability language in the health-care-decisions rule.
Compare Ohio, whose entire chapter is axis B and which has no axis A at all.
**The two states are exact complements, and either one alone would suggest the
wrong universal shape for the model.**

> **Not established, and explicitly not assumed:** whether a background-check
> duty sits elsewhere in Tennessee law (T.C.A. tit. 68 or the Health Facilities
> Commission's general chapters). Absence from *this chapter* is what was
> verified. Likewise for ch. 0720-39: it governs **Commission procedure** for
> placing people on and removing them from the vulnerable-persons registry, and
> **whether it obliges a home care organization to query the registry before
> hiring — as Massachusetts § 155.010(E)(3) does — was not established.** Do not
> infer symmetry.

---

## 2. Colorado — 6 CCR 1011-1 Chapter 26, Home Care Agencies

Adopted by the Board of Health **2025-04-16**, effective **2025-07-01**
(`ruleVersionId=12016`). Seven parts: statutory authority, definitions,
**placement agencies**, department oversight, general requirements for all
licence categories, **Part 6 Skilled Care**, **Part 7 Non-Medical / Personal
Care**.

**A two-category licence, like Ohio and Texas.** Third state in the survey where
the same regulator runs a skilled track and a non-medical track under one
chapter, and the requirements differ by track.

### Axis A — Part 7, and the roles stack

**§ 7.3 Homemaker.** Training **plus a competency evaluation that includes a
visual observation and evaluation of relevant skills, before providing care to a
consumer.** Initial training *"must be interactive in nature"* and may be
**in-person, online/virtual, or hybrid, with demonstration of learned concepts**.
Topics: duties and responsibilities including **incident and mandatory
reporting**; the rules for non-medical care; **the differences between homemaker
and personal care**; consumer rights including freedom from abuse or neglect and
confidentiality; basic health and safety (home safety, fall prevention, hand
washing, infection control); assignment and supervision of services;
communication skills; the physical, emotional and developmental needs of the
populations served; and **core competency evaluation of homemaking and
housekeeping skills before initial training is complete**.

If the agency **outsources** training it must *"validate that the training
program meets the requirements"* and retain evidence of completion in the
personnel record — an approval duty on the agency, where Maryland places it on
the state (written OHCQ approval).

**Ongoing:** orientation for all personnel on hire, and **at least four of the
§ 7.3(C)(1) topics every twelve months** after the start date. A recurring
obligation expressed as *a count of topics*, not a count of hours — a fifth
distinct way of writing axis A.

**§ 7.4 Personal Care Worker.** *"A personal care worker must meet **all**
requirements in Part 7.3, Homemaker, **in addition to** the specific requirements
for personal care workers"*, and must pass **a competency evaluation and skills
validation, including visual observation**, before providing care. Additional
topics: the differences between personal care, nurse aide care and health care in
the home **including the limiting factors at § 7.4(E)**; observation, reporting
and documentation of consumer status; non-medical ADL assistance enumerated
(bathing, skin, hair, nail, mouth care, shaving, dressing, feeding, ambulation,
exercises and transfers, positioning, bladder care, bowel care, protective
oversight); **medication reminders**; and demonstrated ability to assist with
**specific adaptive equipment** the worker will encounter.

> **The stacking is the modelling point.** A personal care worker is not a
> different row from a homemaker — they are a **superset**. Storing one
> `role → requirements` record per role duplicates the homemaker list into the
> PCW list, and the two silently drift apart the next time Colorado amends
> § 7.3. The model needs **role inheritance**, or at least a requirement that
> can be marked as inherited.
>
> Note too the **equipment-specific** clause: the requirement depends on the
> device *this worker* will be assisting with. That is per-assignment, not
> per-role.

### Axis B — Part 5, with an agency-judgment standard

§ 5 (General Requirements, all licence categories): the agency **shall require
any individual seeking employment to submit to a criminal history record check**
to ascertain conviction of *"a felony or misdemeanor, which felony or misdemeanor
involves conduct that **the agency determines** could pose a risk to the health,
safety, or welfare of home care consumers."* At minimum a **Colorado** criminal
history search, conducted **not more than ninety (90) days prior to employment**.
The agency must have policies for employing anyone with a conviction, to ensure
they do not pose a risk.

**This is a different axis-B shape from every other state read.** Ohio, Texas and
Virginia supply an enumerated barred-offence list; **Colorado delegates the
judgment to the agency** and requires a policy. A model with a
`barred_offences[]` field has nothing to put in it for Colorado — what Colorado
requires is *a documented decision*.

### Axis C — two mandatory pre-employment lookups

- **CAPS Check.** *"Before employing any individual to provide direct consumer
  care or services, the HCA must show compliance with the Colorado Adult
  Protective Services Data System (CAPS Check) requirements as set forth in
  Section 26-3.1-111, C.R.S., and 6 CCR 1011-1, Chapter 2, Part 2.3.6."*
- **DORA verification.** Before employing anyone for direct care the agency must
  contact DORA to verify whether **a licence, registration or certification
  exists and is in good standing**, and **a copy of the inquiry goes in the
  personnel file.**

Colorado therefore requires **three separate pre-employment lookups** — criminal
history, adult-protective-services registry, and professional-credential
verification — each with its own authority and its own record. Arizona's APS
registry duty (round 4) now has a companion; **two of twenty-four states run an
adult-protective-services registry check as a hard pre-hire gate.**

### The rest of Chapter 26, not mined

Part 3 governs **placement agencies** — Colorado regulates the registry/placement
model separately, which is directly relevant to any product serving that
business shape. Part 4 is department oversight, Part 6 skilled care, and § 5.12 a
Quality Management Program. **None of these was read.**

---

## 3. Arizona — the Administrative Code is closed, and here is exactly what was tried

`apps.azsos.gov/public_services/Title_09/9-10.pdf` is **AAC Title 9, Chapter 10,
Department of Health Services; Health Care Institutions** — confirmed, because
Chrome loads it and reports that title. Everything else failed:

| Attempt | Result |
|---|---|
| `curl`, bare | 403 |
| `curl`, User-Agent only | 403 |
| `curl`, full browser header set (the mass.gov/medicaid.gov fix) | 403 |
| `curl`, full headers **+ Referer** from the same host | 403 |
| `azsos.gov` and `www.azsos.gov` rule paths | 403 |
| `administrativerules.az.gov` | does not resolve |
| Chrome — **loads the PDF** | canvas viewer, no extractable text |
| `fetch()` from the PDF tab via javascript_tool | returned empty |
| `fetch()` from an HTML page on the same origin | **CDP `Runtime.evaluate` timed out after 45 s** |

**Stopped there rather than continuing** — eight distinct approaches across two
sessions is past the point where more of the same is justified, and the rabbit-
hole rule applies. **Arizona in this survey is statutory only** (A.R.S. § 36-411,
round 4). R9-10 personnel and training rules are unread, and § 36-425.01
(licensure) and § 36-144 (home care services; disclosure) are identified but not
fetched — **both on `azleg.gov`, which works**, so those two are cheap and remain
the sensible next Arizona step.

---

## 4. What rounds 4–5 add to the model

**Axis A now has six distinct written forms**, not two:

1. **Hours with a pre-service floor** — WA (75, of which 5 before any care)
2. **Hours with a grace period** — TN (75/16 by end of month 3), TX HHA (75)
3. **Hours as one route among several** — GA (40, or three competency routes)
4. **Hours, small and recurring** — CA (5 entry + 5 annual)
5. **Competency demonstrated before assignment** — MD (skills demonstration
   before referral), CO (visual observation before care), MN, NC, PA, VA
6. **Recurring training counted in topics** — CO (4 topics per 12 months)

…plus **registry presence as the qualification** (WI) and **no axis A at all**
(OH).

**And a state's own number may not be its own** — TN's 75 hours is a pointer to
the federal competency regulation, the same coupling that CT and OR have on
overtime. **Store the pointer, not the integer.**

**Axis B has two incompatible shapes:** an enumerated barred-offence list
(OH, TX, VA, FL) versus **an agency-determined risk judgment with a policy
requirement** (CO). A schema that assumes the first cannot express the second.

**Roles can nest** (CO: PCW ⊃ homemaker), and **some requirements are
per-assignment, not per-role** (CO adaptive equipment; TN's monthly supervisory
visit is per-patient).

---

## 5. Tier 2 — reported, not independently checked

| Item | Status | Provenance |
|---|---|---|
| Whether Tennessee imposes a background check or a registry query on home care employers | **NOT ESTABLISHED** | Absent from ch. 0720-27; ch. 0720-39 is Commission procedure. T.C.A. tit. 68 not read. **Symmetry with MA explicitly not assumed.** |
| Tennessee TB screening | **NOT FOUND, NOT A NEGATIVE FINDING** | The sweep printed no hits, but the output was truncated; treat as unchecked rather than absent. |
| Colorado Chapter 26 Parts 3, 4, 6 and § 5.12 | **NOT READ** | Part 3 (placement agencies) is the notable gap — it regulates the registry/placement business model directly. |
| Colorado Chapter 2 Part 2.3.6 (the CAPS Check standard itself) | **NOT READ** | Cross-referenced by § 5(D). |
| Arizona AAC R9-10 | **CLOSED — eight approaches, all listed above** | Not a pending task; a recorded dead end pending a new idea. |
| A.R.S. §§ 36-425.01, 36-144 | **NOT FETCHED** | Cheap — `azleg.gov` works. |
| The remaining ~27 states | **NOT ATTEMPTED** | Twenty-four states on at least one axis is not coverage. |

## 6. Method notes

- **The Colorado CCR PDF is reachable, but only via an id buried in an inline
  `onclick`.** The rule-info page exposes no `href` to the document at all —
  `OpenRuleWindow('12016', '6 CCR 1011-1 Chapter 26')`. An href-only link
  extractor finds nothing and reports the page as a dead end. **Grep the raw
  HTML for the JS call, not just for `href=`.**
- **Two complementary states are worth more than two similar ones.** Ohio (all
  axis B, no axis A) and Tennessee (axis A and E, no axis B) each look like a
  general rule in isolation and are refuted by the other. When a model is being
  derived from examples, deliberately seek the state that is shaped least like
  the ones already read.
- **An absence found by sweep is weaker than a presence found by quote.** Both
  Tennessee negatives above are labelled as scoped to the chapter actually read.
