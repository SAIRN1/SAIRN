# SAIRNsenior — state round 3, and the qualification-pathways model written down

2026-08-30. **Research only.** Fifth document in the series. Same two-tier rule.

Closes the **Texas Personal Assistance Services** gap that has been open since
2026-08-29, adds **Wisconsin**, and — because Michael asked for it to become the
standard shape rather than a finding about four states — states the
**qualification-pathways model** explicitly, with the axes the eighteen states
read so far actually require.

---

> ## ⛔ Read first: the model has a dimension ABOVE the five axes, and one entry in it is a build constraint
>
> **Registration category decides which axes apply at all** — Florida's
> registration vs licensure, Ohio's skilled vs nonmedical, Texas's seven HCSSA
> categories, Colorado's Part 6 vs Part 7. Added 2026-08-30; see
> `2026-08-30-sairnsenior-state-round-6-az-co-placement-sc.md`.
>
> **And one category forbids a feature outright.** A **Colorado-registered home
> care placement agency** must give the consumer a signed notice, before services
> start, stating it *"does not direct, control, **schedule**, or train"* the
> providers it refers (6 CCR 1011-1 ch. 26 § 3.3(B)). **Scheduling,
> training-delivery and assignment-direction must be absent from that customer's
> product, not merely unused** — an account-level capability gate keyed on
> registration category, decided before any UI is exposed. Full text and
> consequences in round 6.
>
> ### ⛔⛔ "Is this caregiver qualified?" is the WRONG QUESTION in at least four states
>
> **Qualification is not always a property of the worker.** In Louisiana it is a
> property of a **worker × client × task** triple, and the other three are the
> same family:
>
> **Louisiana, LAC 48:I § 9245(A)** — a direct service worker's competency for
> medication administration and noncomplex tasks is certified **by an RN who has
> personally assessed the health status of the individual receiving care**, who
> determines the worker can perform the tasks *"in a safe, appropriate manner
> **for this person**"*. The certification is written, filed, **and "shall not be
> delegated"**. It must be **repeated** if the RN does not certify competency,
> and **refreshed when that person's health status or physician orders change**.
>
> **What that means for scheduling logic, concretely:**
>
> - A caregiver cleared for Client A **is not cleared for Client B.** There is no
>   worker-level "qualified" state to check.
> - **Filling a shift from a pool is a regulated act**, not a convenience. Open-
>   shift claiming, auto-assignment, agency-pool substitution and last-minute
>   cover all need a per-client authorisation lookup **before** the assignment is
>   allowed to stand.
> - **The authorisation expires on a clinical event, not a date.** A change in the
>   client's condition or orders invalidates its basis, so the client record and
>   the caregiver's authorisation are coupled.
> - **The certifying RN must be named** on the record, because the determination
>   is non-delegable.
>
> Same family, elsewhere: **Oklahoma** — assign an aide *"only to tasks for which
> the aide has been determined to be competent"* (63 O.S. § 1-1962(C)(2));
> **Colorado** — demonstrated ability with the **specific adaptive equipment**
> that worker will encounter (6 CCR 1011-1 ch. 26 § 7.4(C)(1)(e)); **Kentucky** —
> dementia training completed **before** serving a patient exhibiting symptoms
> (902 KAR 20:081).
>
> **Design consequence:** the qualification check belongs at **assignment time**,
> keyed on (worker, client, task) — not at onboarding, keyed on worker. A schema
> that stores qualifications only on the caregiver record cannot answer the
> question these four states actually ask.
>
> ### ⛔⛔⛔ And in Iowa the REGULATED ENTITY may be SAIRNsenior itself
>
> Iowa Code ch. 135Q / 481 IAC ch. 55 registers and regulates **"health care
> technology platforms"** — annual registration and fee, plus the criminal /
> dependent-adult-abuse / child-abuse checks, TB screening and
> training-and-good-standing verification that would otherwise fall on the health
> care entity, immediate abuse-allegation notification, documentation on demand,
> and **quarterly reporting of every Medicare/Medicaid entity contracted with and
> the average amount charged**, broken down by provider type and worker category.
>
> **Every other rule in this model constrains a customer. This one constrains the
> vendor.** **SCOPE SETTLED 2026-08-30 against Iowa Code § 135Q.1:
> SAIRNsenior as currently built is OUTSIDE it.** The definition requires an
> internet- or application-based **marketplace** through which an **independent
> contractor bids on open shifts** posted by a health care entity; SAIRNsenior is
> an agency-facing roster-and-assignment scheduler with none of the three.
> **The trigger that would flip it: shipping an open-shift marketplace where
> non-employee caregivers bid.** And note "nursing services" expressly includes
> personal care by non-certified staff, so "we are not nursing" would NOT be a
> defence. See `2026-08-30-sairnsenior-iowa-135Q-scope-determination.md`.
>
> ### A sixth category of rule: BEHAVIOUR CONSTRAINTS
>
> Some rules are not requirements a worker meets or data a record holds. **They
> say what the software must, or must not, do.** They come in both polarities and
> both are binding:
>
> | | State | Rule | Product consequence |
> |---|---|---|---|
> | **Forbids** | Colorado | A registered placement agency *"does not direct, control, **schedule**, or train"* providers it refers — disclosed and consumer-signed before services start (ch. 26 § 3.3(B)) | The feature must be **absent** for that account |
> | **Compels** | Louisiana | A home health aide's own definition requires *"a **clinical note for each patient visit**"* (LAC 48:I ch. 91) | Every scheduled visit must **produce a record** |
> | **Compels** | Oklahoma | An agency *"shall only assign the home health aide to tasks for which the aide has been determined to be competent"* (63 O.S. § 1-1962(C)(2)) | **Assignment-time** check, per task |
> | **Compels** | Louisiana | Direct-service-worker competency is certified by an RN **for a named individual receiving care**, and that certification *"shall not be delegated"* (LAC 48:I § 9245(A)) | Caregiver substitution is **not free** — authorisation is per client |
> | **Compels** | Kentucky | Dementia training must be completed **before** serving a patient exhibiting symptoms; supervisory visits every 2 weeks, or every 60 days where no skilled service is involved (902 KAR 20:081) | Eligibility depends on **the patient**, and visits are **scheduled obligations** |
>
> **None of these is expressible as a field on a worker record.** Three of the
> five are triggered by *the client or the task*, not by the worker — so a model
> that asks only "is this caregiver qualified?" answers the wrong question.
> Track them separately from the five axes and check them at **assignment
> time**, not at onboarding.

## 1. The model, stated so every later state can be filled in against it

A worker is permitted to work for a given employer in a given state when they
satisfy **each applicable axis**. There is no single `training_hours` field, and
three of the five axes are not training at all.

| Axis | What it holds | States that force it |
|---|---|---|
| **A. Qualification route** | **one of N** enumerated alternatives — a licence, an approved program, a competency evaluation, documented experience, or an hour-denominated course | every state read |
| **B. Criminal-record check** | issuing authority, **timing window**, staleness limit, barred-offence list | WA, CA, FL, PA, VA, GA, TX, MA |
| **C. Registry** | a state-run list, queried or joined — **with a date and an outcome** | MA (adverse-findings, pre-hire query), WI (eligibility listing), GA/VA/NC (nurse-aide registry as a route) |
| **D. Health screening** | TB and similar, with an interval | CA, GA |
| **E. Supervision / delegation** | who may evaluate competency, and for which tasks | MN, NC, TX, WI, VA |

**Hours, where they exist at all, are one option inside axis A** — never the axis
itself. Of eighteen states now read, **four** name an hour figure, and in two of
those it is one route among several.

**The corollary that keeps being useful:** the same state can sit in different
places on the same axis depending on **which licence category the employer
holds**. Texas below is the cleanest example yet; Florida's registration-vs-
licensure split was the first.

---

## 2. Tier 1 — Texas Personal Assistance Services, CLOSED

Source: **HHSC's own HCSSA FAQ, dated July 2026** — current, and reachable with
the header-set fetch that solved the mass.gov/medicaid.gov block. The codified
26 TAC text is still behind the unusable Appian portal, so this remains an
**agency restating its own rule**, one step from the regulation. Labelled, not
smuggled.

**The finding that closes the gap: there is no training-hour requirement for a
Texas unlicensed personal assistant.** The 75-hour figure verified on 2026-08-29
belongs to **home health aides** under the Licensed & Certified category — not to
PAS. A PAS attendant is qualified by **employability verification** plus, where
nursing tasks are delegated, **RN-determined competency**. A product that applied
75 hours to a Texas PAS agency would be imposing a requirement Texas does not
make.

**Licence categories — axis A varies by category, within one state.** Per
26 TAC § 558.13 a HCSSA licence may carry: **Personal Assistance Services (PAS)**,
Licensed Home Health Services, LHHS with home dialysis designation, **Licensed
and Certified Home Health Services (L&CHHS)**, L&CHHS with home dialysis, Hospice,
Hospice with an inpatient unit. Licensed-and-certified agencies must also meet
**42 CFR pt. 484** (home health) or **pt. 418** (hospice).

**What PAS is — 26 TAC § 558.2(87):** *"Routine ongoing care or services required
by an individual in a residence or independent living environment that enable the
individual to engage in the activities of daily living or to perform the physical
functions required for independent living, including respite services,"*
comprising personal care; health-related services performed in circumstances
defined as **not** the practice of professional nursing by the Texas Board of
Nursing; and health-related tasks by unlicensed personnel **under RN delegation**
or that an RN determines need no delegation.

**Personal care — § 558.2(88):** bathing, dressing, grooming, feeding,
exercising, toileting, positioning, assisting with self-administered medications,
routine hair and skin care, transfer or ambulation.

**Axis B, and it has a hard edge.** Per **26 TAC § 558.247** (*Verification of
Employability and Use of Unlicensed Persons*) a HCSSA **may not employ** a person
whose criminal history check shows conviction of an offence barring employment
under **Tex. Health & Safety Code § 250.006(a), (b), (d)**, or that the agency
itself judges a contraindication. **Deferred adjudication counts:** a person
currently serving a criminal sentence under deferred adjudication community
supervision for a barring offence is **not eligible**. Contracted unlicensed
persons fall under **§ 558.289(d)**.

**Axis E.** RN delegation is available under both PAS and LHHS. The agency must
**employ or contract** the delegating RN, who follows **22 TAC § 225**; the RN
must assess the client **before** delegating, and is responsible for
**supervision and evaluation of competency** of the unlicensed personnel.

**A scope limit worth carrying into scheduling:** a PAS agency **may not fill
weekly pill minders**. Where a client cannot self-administer, an RN or designee
under 22 TAC § 225.11 does it, with the delegation-oversight requirements
attached.

**Administrator, not attendant — the requirement that is easy to misfile.** For a
PAS-only agency the administrator and alternate **need not be licensed**, but
must meet **26 TAC § 558.244(a)(3)**: a high school diploma or GED **plus at least
one year of experience or training caring for individuals with functional
disabilities**; or **two years of full-time study** at an accredited college in a
health-related field; or the LHHS/L&CHHS/hospice route at (a)(1)(A)–(B). Exactly
one administrator and one alternate — multiple administrators are not allowed
(§ 558.243). The 8 + 16 clock-hour administration training recorded on 2026-08-29
sits here, on the **administrator**, and is not an attendant requirement.

**Operational, and it bites a franchise model:** a HCSSA licence authorises
service *from each place of business*; **a virtual office is not permitted**
(§ 558.1(a)(2)), and an administrative support site may **not** schedule client
visits or complete clinical documentation (§ 558.2(4)).

---

## 3. Tier 1 — Wisconsin, and a second shape for axis C

**Wis. Admin. Code § DHS 133.02(4)** defines a home health aide as *"an
individual **whose name is on the registry** and who is eligible for employment in
a home health agency, and who is employed by or under contract to a home health
agency to provide home health aide services **under supervision of a registered
nurse**."*

**That is axis C used as the qualification itself**, not as a disqualification
screen. Massachusetts queries a registry to find **adverse findings** and is
forbidden to hire on a hit; Wisconsin requires **presence on** a registry as the
precondition to employment. Same axis, opposite polarity — and a schema with a
single boolean `registry_checked` cannot tell them apart.

§ DHS 133.02(5) defines home health aide services as personal care services
facilitating self-care at home that do **not** require an RN or LPN. Aide
services are at § DHS 133.17, supervisory visits at § DHS 133.18. Caregiver takes
its meaning from **Wis. Stat. § 50.065(1)(ag)**, the caregiver-background-check
statute — axis B by cross-reference.

---

## 4. Where the eighteen states now sit on axis A

| Hour-denominated | Competency / route-based | Registry-based |
|---|---|---|
| WA 75 (+5 pre-care) · TX **HHA only** 75 · CA 5 + 5 annual · GA 40 *(one of four routes)* | PA · VA · MN · NC · NY · MA · NJ · FL (homemaker/companion) · **TX PAS** | WI · MA *(adverse-findings, inverse)* |

Also read on wage/overtime axes but not on training: CT, OR, IL, NV.

**Four of eighteen.** The `training_hours` field would be null for fourteen.

---

## 5. Tier 2 — reported, not independently checked

| Item | Status | Provenance |
|---|---|---|
| Codified 26 TAC § 558.2/.244/.247/.289 text | **NOT READ** | Everything in §2 is HHSC's July 2026 FAQ restating its own rules. Appian portal still unusable. |
| WI § DHS 133.17 (aide services) and § 133.18 (supervisory visits) | **NOT READ** | Only the chapter's definitions and section list were retrieved; the substantive rules are on sub-pages. |
| Missouri 19 CSR 30-26 | **THIS ROW WAS WRONG — corrected 2026-08-30** | The citation was RIGHT: the Secretary of State’s own Title 19 index lists `19c30-26.pdf` as “Chapter 26 — Home Health Agencies”. My scan searched only for **hour patterns**, found none, and I reported “nothing relevant” — a different claim, and untested. The chapter incorporates 42 CFR 484 wholesale and adds a dementia-training mandate. See `2026-08-30-sairnsenior-state-round-9-la-ch92-missouri-kentucky.md` §0. |
| Arizona (`apps.azsos.gov` 403), Tennessee (`publications.tnsosfiles.com` 403), Maryland (`dsd.maryland.gov` 404), Seattle DWO (404) | **THREE RESOLVED 2026-08-30, ARIZONA STILL BLOCKED** — see `2026-08-30-sairnsenior-state-round-4-oh-co-md-az-tn.md` | Tennessee was never blocked: an XML 403 from that object store is a **bad key**, and the real hrefs are flat and date-stamped. Maryland's canonical host is `regs.maryland.gov`, which `dsd.maryland.gov` redirects to. Arizona statutes are on `azleg.gov`; the **Administrative Code has no working route**. |
| Ohio 3701-60-04, Colorado 6 CCR 1011-1 | **THIS ROW WAS WRONG — corrected 2026-08-30** | Neither was on disk: the probe loop wrote every body to `/dev/null`, so "fetched" rested on a status code and nothing else. The Colorado URL was also **not** 6 CCR 1011-1 — it resolves to 10 CCR 2505-10 § 8.500, the Medicaid benefit rule. Both now fetched and read for real; CO's licensure chapter remains unlocated. |
| Municipal domestic-worker ordinances | **NOT ATTEMPTED** | Seattle's canonical URL 404s; needs the current one. |
| The remaining ~33 states | **NOT ATTEMPTED** | Eighteen states on at least one axis is not coverage. |

## 6. Method notes

- **The header-set fetch is not universal.** It unblocked mass.gov, medicaid.gov
  and hhs.texas.gov; Arizona, Tennessee and Maryland still refuse. Reporting it
  as *the* fix would have been the same over-generalisation as calling the
  original block a "request fingerprint".
- **CORRECTED 2026-08-30 — this bullet originally said "a guessed citation that
  fetches cleanly is still a wrong citation", using Missouri as the example.
  Missouri was not a wrong citation.** 19 CSR 30-26 really is *Home Health
  Agencies*; what failed was my scan, which searched only for hour patterns,
  found none, and reported "nothing relevant" — a claim I never tested. **The
  surviving lesson is the narrower one: a negative from a single pattern is a
  negative about that pattern**, and it must be reported that way. (The
  wrong-citation lesson is real, but its true example is Tennessee 0720-11 —
  see round 4.)
- **An agency FAQ can be more current than the code.** Texas's is dated July 2026
  and carries `<Added 07/02/26>` markers. It is still one step from the rule, and
  the label stays on.
