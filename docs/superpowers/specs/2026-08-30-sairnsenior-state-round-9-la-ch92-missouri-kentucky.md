# SAIRNsenior — state round 9: Louisiana's registry chapter, a Missouri correction, and Kentucky

2026-08-30. **Research only.** Eleventh document in the series.

The most consequential finding is Louisiana's: **competency is certified for a
named individual receiving care, and the certification may not be delegated.**
That makes caregiver substitution a regulated act, not a scheduling convenience.

---

## 0. Correction — Missouri 19 CSR 30-26 was the right chapter and I said it was not

Round 3 recorded: *"Missouri 19 CSR 30-26 — **WRONG CHAPTER, ABANDONED**. Fetched
cleanly (189 KB) but contains no aide-qualification or hour provisions — the
citation was a guess and it was wrong."* Round 4 and round 5 both carried that
forward.

**The citation was right.** The Secretary of State's own Title 19 index lists
`19c30-26.pdf` as *"Chapter 26 — Home Health Agencies"*. What was wrong was my
scan: I searched only for **hour patterns**, found none, and generalised that to
"nothing relevant". The chapter is short because of what it does, not because it
is the wrong chapter — and it contains a training requirement I missed.

> **The lesson is narrower and more useful than "check the citation":** I
> concluded *no hours* and reported *nothing relevant*. Those are different
> claims, and the second was not tested. A negative from a single pattern is a
> negative about that pattern.

### What Missouri actually says

**19 CSR 30-26.010, Home Health Licensure Rule.** Missouri **incorporates the
federal rule wholesale**:

> "(1)(A) This rule incorporates by reference **42 CFR 484, Medicare Conditions
> of Participation: Home Health Agencies**, for Missouri licensed home health
> agencies. Missouri licensed home health agencies shall **strictly meet the
> currently applicable Medicare Conditions of Participation** and surveys
> performed for state licensure will be conducted **per Medicare standards**."

**This is the purest instance of the federal-coupling shape in the survey.**
Tennessee's aide hours point at the federal competency rule; Connecticut and
Oregon define overtime coverage by reference to FLSA regulations; **Missouri
adopts an entire federal chapter as its state licensure standard, including the
survey methodology.** "Currently applicable" means it moves without any Missouri
rulemaking.

**And then one thing Missouri adds on top:**

> "(1)(B) Licensed home health agencies shall provide **dementia-specific
> training about Alzheimer's disease and related dementias** to their employees
> **and those persons working as independent contractors** who provide direct
> care to or **may have daily contact with** residents, patients, clients, or
> consumers with Alzheimer's disease or related dementias."

Minimum content for direct-care staff: an overview of Alzheimer's and related
dementias; communicating with persons with dementia; behaviour management;
promoting independence in ADLs; and understanding and dealing with family issues.
**No hour figure.** Note the scope: it reaches **independent contractors** and
anyone who *may have daily contact*, not only assigned caregivers.

---

## 1. Kentucky — a full five-axis state, and dementia training with hours

**902 KAR 20:081, "Operations and services; home health agencies."** Its own
necessity clause is worth quoting because it names the driver:

> "KRS 216.9375(11)(a) requires the cabinet to promulgate administrative
> regulations to implement, monitor, and enforce compliance with
> **dementia-specific training requirements for home health aides**."

### Axis A — a general programme, plus a patient-condition trigger

The agency must ensure each home health aide successfully completes an aide
training and competency evaluation programme. **On top of that:**

> "…a home health aide who provides care to a patient that **exhibits symptoms of
> Alzheimer's disease or other dementia** shall complete at least **six (6) hours
> of initial training and three (3) hours of annual training in dementia care**
> pursuant to KRS 216.9375(3)… a home health aide shall **successfully complete
> the initial training in dementia care prior to providing services** to such a
> patient."

**This is a new trigger for axis A: the patient's condition.** Not the worker's
role, not the task, not the licence category — **who they are about to be sent
to**. Kentucky and Missouri both single out dementia; Kentucky attaches hours
(6 + 3 annual) and a pre-service gate, Missouri attaches topics and no hours.
California adds a dementia topic to its annual five hours from 2027-01-01
(round 1). **Three states, three different mechanisms, same subject** — a
dementia overlay is now a distinct thing to model, not a per-state curiosity.

### Axis E — two supervisory cadences, and which one applies depends on the service mix

- The practitioner responsible for delivery or supervision within their scope
  makes a supervisory visit to the patient's residence **at least every two (2)
  weeks**, with the aide either **present** (to observe and assist) or **absent**
  (to assess relationships and determine whether goals are being met).
- **But** if aide services are provided to a patient **not receiving skilled
  nursing or another skilled service**, the RN visits **at least every sixty (60)
  days**, and that visit **shall occur while the aide is providing patient
  care**.

**Two cadences — 14 days or 60 days — selected by whether a skilled service is
in the plan**, and the 60-day one has a co-presence condition the 14-day one does
not. Compare Tennessee's flat monthly visit with preferred alternation. **A
single `supervisory_visit_interval_days` field cannot hold this.**

### Axes B and C — both, and both pre-employment

Personnel policies must include, among other things, provision for orientation
and on-the-job training, **annual evaluation of employee performance**, job
descriptions specific to what each category may carry out, and:

- **"Pre-employment abuse registry checks conducted pursuant to KRS 216.937 and
  KRS 209.032"**; and
- **"Pre-employment criminal background checks"**, where the agency **shall not**
  employ anyone in a direct-services position convicted of a **felony** relating
  to theft; abuse, possession or sale of illegal drugs; abuse, neglect or
  exploitation of a child or an adult; or a sexual crime — **or a misdemeanour**
  relating to abuse, neglect or exploitation of an adult.

An enumerated bar (like Ohio, Texas, Virginia, Florida, South Carolina) **plus**
a separate registry check (like Massachusetts, Arizona, Colorado, Louisiana).
Kentucky runs both axes at full strength.

---

## 2. Louisiana — Chapter 92, and the finding that constrains scheduling

**LAC 48:I Chapter 92, Direct Service Worker Registry**, Subchapter D
(medication administration and noncomplex tasks in home and community-based
settings).

### § 9245(A) — competency is certified per *person receiving care*

> "**Person-Specific Training.** Direct service workers shall receive
> person-specific training from a RN **who has assessed the health status of the
> person** and who has determined that the direct service worker can competently
> perform the tasks **in a safe, appropriate manner for this person**.
> 1. The RN's determination of competency shall be **certified by the RN in
> writing**, and the written certification shall be maintained in the direct
> service worker's personnel file. **The RN's determination of competency shall
> not be delegated.**
> 2. This training **shall be repeated** if the RN does not certify… sufficient
> competency…
> 3. …the RN shall provide **additional person-specific training when the person
> receiving care has a change in health status or physician orders**…"

The RN may judge that this additional training can be delivered by telephone or
other electronic means rather than face-to-face, based on their assessment of
the worker's competency — examples given are changed orders for health care
tasks, changed routine medications, or new short-term medication for a minor
acute condition.

> **Why this is the most product-relevant rule found so far.** Competency here is
> a **triple** — worker × client × task set — not a property of the worker. A
> caregiver authorised for Client A is **not** authorised for Client B. So:
>
> - **Substitution is a regulated act.** Filling a shift from a pool requires an
>   existing person-specific certification for that client, or the visit cannot
>   lawfully proceed.
> - **A client's change in condition or orders invalidates the basis of the
>   certification** and triggers fresh training — so the record has a
>   dependency on clinical events, not just a date.
> - **The certifying RN cannot be delegated**, so the record must name that RN.
>
> Colorado's adaptive-equipment clause and Oklahoma's task-competency clause are
> the same family; **Louisiana is the strictest and the most explicit.**

### § 9245(B) — 16 hours, and what they cover

*"Direct Service Staff shall receive **16 hours of medication administration
training** which has been coordinated and approved by an RN"*, on a core
curriculum including the legal aspects of administering medication and roles and
responsibilities. **A sixth state with an hour figure** — and it is task-scoped
(medication administration), not role-scoped.

### § 9247 — annual competency evaluation, by an RN

*"The direct service worker shall undergo an **annual competency evaluation
performed by a RN**"* for the authorised person-specific medication
administration and noncomplex tasks, the RN using professional judgment.
(Promulgated under R.S. 37:1031-1034; LR 38:3178, December 2012.)

### § 9249 — what may actually be done, and a labelling rule

Authorised tasks apply only to a person **in stable condition**, only where the
tasks *"may be performed according to exact directions, there is no need to alter
the standard procedure, and the results are predictable"*: administration of oral
and topical medication, ointments, suppositories, or a manufacturer's pre-measured
oral inhalant aerosol dose as ordered; **routine hydration, nutrition or
medication via an established gastro-tube**; and other noncomplex tasks per
Department guidelines. Medication must be in a container marked with clear
instructions, prescriber's name, prescription number, medication name, dosage,
route, frequency and time to be administered.

### § 9103 — administrator, with a dated qualification split

The administrator answers directly to the governing body, is designated in
writing, and must be available in person or by telecommunication **at all
times**. Three years of management experience in delivering health care service,
**plus one of**: licensed physician; RN; **employed as administrator on or after
2018-01-13 and a college graduate with a bachelor's degree**; **employed before
2018-01-13 with three additional years** of documented health care delivery
experience; or experience in health service administration with at least one year
of supervisory or administrative experience related to home health care.

**A qualification that depends on when the person was hired** — the same dated-
rule shape as Washington's 365-day window and Ohio's pre/post-2008 recheck
anniversaries. And: an administrator serving **more than one agency** must
designate an alternate who is a **full-time, on-site employee of each agency**
and separately meets the administrator qualifications.

---

## 3. What this round adds to the model

- **Competency can be scoped to the client** (LA § 9245). Promoted into the
  pathways-model document as part of the new **behaviour-constraints** table,
  because it is checked at assignment time and cannot live on a worker record.
- **Patient condition is a trigger for training** (KY dementia; MO dementia; CA
  dementia topic from 2027). A dementia overlay is its own dimension.
- **Supervisory cadence can be conditional on the service mix** (KY: 14 days vs
  60 days), and the conditional branch can carry its own co-presence rule.
- **Wholesale federal incorporation is a real state posture** (MO adopts 42 CFR
  484 including survey methodology). Store the pointer; there is nothing else to
  store.
- **Hour figures can be task-scoped** (LA: 16 hours for medication
  administration) rather than role-scoped.

The pathways-model document now carries a **behaviour-constraints** table listing
all five such rules found (Colorado forbidding, Louisiana × 2, Oklahoma and
Kentucky compelling), with the note that **three of the five are triggered by the
client or the task rather than the worker**.

---

## 4. Tier 2 — reported, not independently checked

| Item | Status | Provenance |
|---|---|---|
| MO 19 CSR 30-25 ("Special Notice — Home Health Agencies") | **NOT READ** | Sits beside Chapter 26 in the index. |
| KY KRS 216.9375, 216.937, 209.032, 216.935 | **NOT READ** | Cross-referenced by 902 KAR 20:081 for the dementia mandate, the abuse registry and the aide definition. |
| KY 902 KAR 20:081 in full | **PARTIALLY READ** | 60 KB of text; definitions, training, supervision and personnel policies mined. |
| LA Chapter 92 Subchapters A–C (§ 9201 definitions, § 9231 provider responsibilities) | **NOT READ** | Only Subchapter D and § 9103 were read. |
| LA § 9245(B) full 16-hour curriculum | **PARTIALLY READ** | Two items of the core curriculum quoted; the rest not extracted. |
| Michigan, Alabama, Mississippi, Arkansas | **NOT ATTEMPTED THIS ROUND** | Index probes: `michigan.gov/lara` 200, `alabamapublichealth.gov/providerstandards` 200 (nursing-home oriented), `sos.ms.gov` 404, `sos.arkansas.gov/rules-and-regulations` 404, `alabamaadministrativecode.state.al.us` does not resolve. Two working indexes to start from. |
| OAC 310:661 | **STILL NO ROUTE** | Carried. |
| Indiana | **ON HOLD** | Per instruction. |
| The remaining ~22 states | **NOT ATTEMPTED** | Twenty-nine states on at least one axis is not coverage. |

## 5. Method notes

- **"No hits for pattern X" is not "nothing here".** Missouri cost three rounds
  of a false negative because I searched for hours, found none, and wrote off the
  chapter. State the pattern that was searched, not the conclusion it seemed to
  support.
- **A regulation's necessity clause names its driver.** Kentucky's opens by
  citing the dementia-training statute, which is how the overlay was found
  before reading the body.
- **Two states adding the same overlay is a dimension, not a coincidence.**
  Dementia-specific training appeared in Kentucky and Missouri in one round and
  in California in round 1, with three different mechanisms.
