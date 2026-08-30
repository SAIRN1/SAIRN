# SAIRNsenior — state round 10: Arkansas trains the unlicensed segment, Michigan doesn't license it

2026-08-30. **Research only.** Twelfth document in the series.

Two findings at opposite ends of the same question — *what happens to non-medical
in-home care when nobody licenses it?* **Arkansas answers with a training
mandate. Michigan appears to answer with nothing.**

Also: the Louisiana worker × client × task finding promoted to its own warning at
the top of the pathways model, per instruction.

---

## 1. Arkansas — the unlicensed segment, regulated by training alone

Route: `healthy.arkansas.gov/resources/rules/final-rules/` → **`codeofarrules.arkansas.gov`**,
which is *"the official version of the Code of Arkansas Rules"* under Ark. Code
§ 25-15-218, effective 2025-01-01 and updated weekly. **Title 20, Chapter I,
Subchapter B, Part 45 — "Rules for Home Caregiver Training in Arkansas"**, adopted
by the State Board of Health 2024-01-25 under **Act 1410 of 2013**
(Ark. Code § 20-77-2301 et seq.), **effective 2024-09-05**.

### The scope trigger is the client's AGE — the only one in the survey

**20 CAR § 45-101(1):** *"'Caregiver services' means the services provided to an
individual … to assist the recipient of the services in the activities of daily
living, and **the recipient of services is fifty (50) years of age or older** at
the time the services are provided."*

Every other state scopes by service type, setting, or licence category.
**Arkansas scopes by how old the client is** — and at the time the services are
provided, so a client can cross into scope mid-engagement. For a product aimed
squarely at senior care this is the one scope test that will almost always be
satisfied, but it still has to be *evaluated*, not assumed.

### And the regime attaches to the UNLICENSED agency by definition

**§ 45-101(3):** an *"in-home services agency"* provides caregiver services for
pay in a client's residence **and "is not otherwise licensed by the Department of
Health as a: (i) Home health agency; (ii) Private care agency; or (iii) Hospice
agency."*

**The rule is written to apply only where the licensing rules do not.** Compare
the other three answers to the same gap:

| State | Unlicensed non-medical in-home care is… |
|---|---|
| **Louisiana** | left alone entirely — unless bundled with home health services |
| **Florida** | registered ($50/biennium), no training requirement |
| **Arizona** | unregulated, but must **disclose** its own standards annually per client |
| **Arkansas** | **trained** — 40 hours, by rule, with no licence at all |

### Axis A — 40 hours, of which 16 are demonstrated physical skills

**§ 45-102(b)** — a person qualifies as a *"trained in-home assistant"* if they:

1. are **eighteen (18) or older**;
2. have **not been convicted of a felony that would prevent working in a
   long-term care facility** under Ark. Code § 20-38-101 et seq., *"unless the
   conviction has been expunged or pardoned"* — **axis B by cross-reference to
   the nursing-home standard**, with the same expungement/pardon escape Ohio
   has; and
3. have completed a Department-approved course covering ten core competencies,
   **"not less than forty (40) hours"**: body functions; body mechanics and
   safety precautions; communication skills; **at least four (4) hours on
   Alzheimer's disease and other dementia** (communication skills, problem
   solving with challenging behaviours, assistance with daily living, and an
   explanation of the disease); dementia and Alzheimer's; emergency situations
   including recognition and proper procedures; household safety and fire
   prevention; infection control and prevention; **ethical considerations and
   state law regarding delegation of nursing tasks to unlicensed personnel**; and
   nutrition.

**§ 45-102(b)(3)(B): at least sixteen (16) of the forty hours must cover
"physical skills and competent demonstration of such skills"** for ambulation;
basic housekeeping including laundry; bathing, shampooing and shaving; dressing
and undressing; meal preparation and clean-up; oral hygiene; range of motion;
toileting; transfer techniques; **recordkeeping and documentation of
activities**; **role of caregiver in a healthcare team**; and nail and skin care.

> **A nested hour structure: 40 total ⊃ 16 demonstrated ⊃ 4 dementia.** No other
> state read so far subdivides its hour figure. A single `training_hours: 40`
> loses both inner constraints, and the 16 are not merely instruction — they
> require *competent demonstration*.

### § 45-103 — the employer may certify the training itself

> "The training required under this part **may be certified by an employer** if
> that employer maintains records regarding: (1) The identification of the
> employee who received training; (2) The topic for which the training was
> conducted; and (3) **The amount of time spent on training.**"

**A self-certification route conditioned on record-keeping** — and the records it
names (person, topic, time) are exactly what a training module in a product would
already produce. This is the clearest case yet where the compliance artefact and
the product's own data are the same thing.

### § 45-104 — exemptions, and one of them is an experience substitution

Exempt from the training specification: a person with **at least one (1) year of
experience working in an institutional setting** — home health agency, hospital,
hospice, or long-term care facility — *"verified by the person's employer during
the experience"*, i.e. **verified by the prior employer, not the current one**.

May provide caregiver services without the training at all: a **CNA, LPN, RN,
physician, or licensed social worker**; a **parent, grandparent, child,
grandchild, or sibling** of the recipient; a **service provider who does not
receive compensation**; a **court-appointed legal guardian** of the recipient; or
**a direct-care worker serving a participant in any programme licensed,
administered or certified by the Department of Human Services.**

**That last one matters commercially:** Medicaid-waiver work under DHS is carved
out of the training rule entirely, so an Arkansas agency's obligations differ
**per client**, by payer, within one workforce.

### Dementia is now a four-state overlay, four ways

| State | Mechanism |
|---|---|
| California | one topic added to the 5 annual hours, **from 2027-01-01** |
| Kentucky | **6 hours initial + 3 annual**, before serving a symptomatic patient |
| Missouri | enumerated topics, **no hours**, reaching independent contractors |
| Arkansas | **4 hours inside the 40**, with four named subtopics |

Four states, four mechanisms, one subject. It is a dimension of the model, not a
per-state quirk.

---

## 2. Michigan — the licensing list does not contain home care

`michigan.gov/lara/bureau-list/bchs`, the **Bureau of Community and Health
Systems**, states its own remit:

> "The bureau oversees state licensing of **adult foster care facilities, adult
> camps, freestanding surgical outpatient facilities, homes for the aged, hospice
> agencies and residences, hospitals, nursing homes, substance use disorder
> programs** as well as state and federally **certified nurse aides**, state
> **certified medication aides**…"

**No home health agency. No home care agency. No in-home services agency.**

> **Stated with the limit on it, because this is a negative finding from one
> page.** What is verified is that **BCHS's own description of its licensing
> remit does not include home health or in-home care agencies**. That is
> consistent with the widely-reported position that Michigan does not license
> home health agencies (relying on Medicare certification) and does not license
> non-medical home care — **but "consistent with" is not "confirmed", and I have
> not read the Public Health Code.** Michigan sits in Tier 2 until Act 368 of
> 1978 is checked. If it holds, Michigan is a **second null case** alongside
> Louisiana's conditional one — and the largest state in the survey with no
> licensure axis at all.

---

## 3. Alabama and Mississippi — routes not found, and one that lies

**Alabama.** `admincode.legislature.state.al.us` is a JavaScript SPA (902 bytes
of shell). `alabamapublichealth.gov` is worse: **it returns HTTP 200 with a
"404page" body** for every guessed path — 6,109 bytes of styled not-found. Three
different paths returned byte-identical 200s.

> **A soft-404 is the most dangerous routing failure in this survey.** Every
> earlier probe loop treated 200 as reachable. Alabama would have been logged as
> "fetched, three routes available" on status codes alone — the same mistake as
> the `/dev/null` probe in round 3, arriving by a different door. **Check the
> body, not the code.**

**Mississippi.** `sos.ms.gov/regulation-enforcement/administrative-code` returns
200 but the body is site navigation only; `sos.ms.gov/adminsearch/` loads a
search UI; two guessed document paths 404. The MAC is published by the Secretary
of State but the document endpoint was not found.

**Both recorded as open with the routes tried.**

---

## 4. Tier 2 — reported, not independently checked

| Item | Status | Provenance |
|---|---|---|
| Michigan Public Health Code (Act 368 of 1978), Art. 17 | **NOW READ — negative CONFIRMED, and Michigan is NOT a null case** | MCL 333.20106(1) enumerates “health facility or agency” in eleven items and **home health agencies are not among them** — so no licensure. But MCL 333.20173a makes a home health agency a **covered facility** under a statutory employment bar. See `2026-08-30-sairnsenior-state-round-11-michigan-confirmed.md`. |
| Alabama Admin. Code ch. 420-5-6 (home health) | **NO ROUTE** | SPA + soft-404s. |
| Mississippi Administrative Code Title 15 | **NO ROUTE** | Index loads, document endpoint not found. |
| AR § 45-102(b)(3)(A)(iv) vs (v) | **NOTED, NOT RESOLVED** | The competency list names dementia twice — "at least four hours covering Alzheimer's… " at (iv) and "Dementia and Alzheimer's diseases" at (v). Quoted as printed; whether (v) is a drafting artefact was not established. |
| AR Ark. Code §§ 20-77-2301–2305, 20-38-101 | **NOT READ** | Cross-referenced for authority, the felony bar and employer certification. |
| LA ch. 92 Subchapters A–C; KY cross-referenced KRS | **NOT READ** | Carried from round 9. |
| OAC 310:661; AZ AAC R9-10 | **NO ROUTE** | Carried. |
| Indiana | **ON HOLD** | Per instruction. |
| The remaining ~20 states | **NOT ATTEMPTED** | Thirty-one states touched on at least one axis is not coverage. |

## 5. Method notes

- **HTTP 200 can be a 404.** Alabama serves a styled not-found page with a 200
  status on every wrong path. Status-code-only probing would have recorded three
  working routes. Check the body length and content before counting a probe as
  a success.
- **A regulator's own description of its remit is usable evidence for a
  negative** — but only for what it says, and it should be labelled as such
  until the enabling statute is read. Michigan is written up that way
  deliberately.
- **Follow the safelink.** Arkansas's rule links were wrapped in
  `gcc02.safelinks.protection.outlook.com` redirects; the real
  `codeofarrules.arkansas.gov` URL is in the `url=` query parameter. A link
  extractor that does not unwrap them finds nothing useful.
- **Walk the hierarchy.** `codeofarrules.arkansas.gov` renders part and subpart
  pages as metadata only; the text lives at `levelType=section` with a
  `sectionID`, reachable by following the NEXT links down. The part page looks
  empty and is not.
