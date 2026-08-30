# SAIRNsenior — state round 3, and the qualification-pathways model written down

2026-08-30. **Research only.** Fifth document in the series. Same two-tier rule.

Closes the **Texas Personal Assistance Services** gap that has been open since
2026-08-29, adds **Wisconsin**, and — because Michael asked for it to become the
standard shape rather than a finding about four states — states the
**qualification-pathways model** explicitly, with the axes the eighteen states
read so far actually require.

---

# ▲ CONSOLIDATED FINDINGS — read this instead of sixteen round documents

*Added 2026-08-30, after 38 states were touched. This is the index to the whole
survey; the boxed warnings below it are the items that change what gets built.
Every claim names its state and citation so it can be checked without re-reading
a round document.*

## The model in one paragraph

A worker may work for a given employer in a given state when they satisfy **each
applicable axis** — and **which axes apply is decided one level up, by the
employer's registration category**. Separately, a handful of rules are not
requirements at all: they say what the **software** must or must not do. And in
three states the **matching business itself** is a regulated entity.

## Layer 0 — registration category decides which axes apply

The same state imposes different requirements on two different customers. Found
in **Florida** (register vs licence), **Ohio** (skilled vs nonmedical), **Texas**
(seven HCSSA categories), **Colorado** (Part 6 skilled, Part 7 non-medical, Part 3
placement), **Nevada** (personal care agency vs employment agency vs referral
agency), **Arizona** (licensed vs § 36-144 disclosure-only).

**Five distinct answers to "what happens to non-medical in-home care":**

| Answer | State |
|---|---|
| Nothing — unless bundled with home health | **Louisiana** |
| Register, no training | **Florida** § 400.509 |
| No licence, but **disclose your own standards annually, per client** | **Arizona** A.R.S. § 36-144 |
| No licence, but **40 hours of training** | **Arkansas** 20 CAR pt. 45 |
| **Licensed as its own category** | **Nevada** NAC 449.396+, **Ohio**, **Colorado** pt. 7 |

## Layer 1 — the five axes

| Axis | What it holds |
|---|---|
| **A. Qualification route** | one of N alternatives — licence, approved programme, competency evaluation, documented experience, or hours |
| **B. Criminal record** | authority, timing window, staleness limit, barred offences, and whether disqualification can expire |
| **C. Registry** | a dated query or listing event — and it has three polarities |
| **D. Health screening** | TB, physical, immunisation — with intervals and lookbacks |
| **E. Supervision / delegation** | who evaluates competency, for which tasks, on what cadence |

**Axis A has eight written forms:** hours with a pre-service floor (**WA** 75, of
which 5 before any care); hours with a grace period (**TN** 75/16 by month 3,
**TX** L&CHHS 75, **OK** registry within 4 months); hours as one route among
several (**GA** 40); small recurring hours (**CA** 5 + 5 annual); **nested** hours
(**AR** 40 ⊃ 16 demonstrated ⊃ 4 dementia); competency demonstrated before
assignment (**MD**, **CO**, **MN**, **NC**, **PA**, **VA**); recurring training
counted in **topics** (**CO**, 4 topics per 12 months); registry presence as the
qualification (**WI**); and **none at all** (**OH**, **MI**).

**Only 6 of 38 states name an hour figure.** A `training_hours` field is null or
wrong for most of the map.

**Axis B has three shapes:** enumerated barred offences (**OH**, **TX**, **VA**,
**FL**, **KY**, **MI**); **agency-determined risk with a required policy**
(**CO**); and enumerated-plus-open-ended (**SC** — *"or any similar criminal
offense"*). Disqualification **expires or is curable** in **OH** (exclusionary
periods, certificates, pardons), **AR** (expunged or pardoned) and **MI**
(15 years from completion of sentence, parole *and* probation).

**Axis C has three polarities:** adverse-findings queried pre-hire with hiring
barred on a hit (**MA** § 155.010(E)(3), **AZ** § 36-411(C), **TN**, **LA**,
**KY**, **CO** CAPS); **presence required to work** (**WI**, **OK**); and
nurse-aide registry as a qualification route (**GA**, **VA**, **NC**). Status is
**dated and contestable** — removal petitions in **MA** (after 1 year) and **TN**
(UAPA), appeal in **MI** § 20173b. **AZ** additionally required a **one-off
retroactive sweep of the existing workforce** by 2025-03-31.

## Layer 2 — behaviour constraints: rules about the software itself

**Not fields. Checked at assignment time, not at onboarding.**

| Polarity | State | Rule |
|---|---|---|
| **Forbids** | **Colorado** | A **pure-referral** placement agency (§ 2.12 — *"only referrals"*) must give a consumer-signed notice that it *"does not direct, control, **schedule**, or train"*. Those features must be **absent** for that account. |
| **Forbids** | **Nevada** | NAC 449.3978 — an enumerated **task deny-list**: catheter insertion/irrigation, body-cavity irrigation, injections, medication administration, physical assessments, digital rectal exam, **trimming toenails**, massage, medical case management. |
| **Compels** | **Louisiana** | A **clinical note for each patient visit**, written into the aide's own definition. |
| **Compels** | **Louisiana** | § 9245(A) — competency certified by an RN **for a named individual**, non-delegably, refreshed when that person's condition or orders change. |
| **Compels** | **Oregon** | ORS 443.190(3) — a **statutory intake field list**; ORS 443.195 names **a mobile application** and requires policies permitting charting **outside** the home. |
| **Compels** | **Oklahoma** | Assign an aide **only to tasks** they have been determined competent for. |
| **Compels** | **Kentucky** | Dementia training **before** serving a symptomatic patient; supervisory visits every **14 or 60 days** depending on service mix. |
| **Permits, with notice** | **Vermont** | § 6309 — may **refuse to dispatch** to a home where a previously-discharged individual is believed present; **notice stating reasons** required. |

**"Is this caregiver qualified?" is the wrong question in LA, OK, CO and KY** —
qualification is a **worker × client × task** triple. Detail in the boxed section
below.

## Layer 3 — the intermediary category: the vendor may be the regulated entity

**Three states regulate caregiver matching**, under three names sharing **no
keyword**:

| State | Category | Trigger | Instrument |
|---|---|---|---|
| **Iowa** | health care technology platform | independent contractors **bid on open shifts** posted by a health care entity | registration, $500/yr |
| **Colorado** | home care placement agency | **a fee, for referrals only** | registration |
| **Oregon** | caregiver registry | roster of **private contractor** caregivers **provided to the client for hiring** | **licence** + site inspection every 3 years |

Adjacent: **Nevada** *employment agency to provide nonmedical services* — hinges
on **contracting with the caregivers**. **Rhode Island** *nursing service agency*
(216-RICR-40-10-10) hinges on **supplying personnel on a temporary basis** —
and R.I. Gen. Laws § 23-17.7.1-2(d) **deems those workers employees and NOT
independent contractors, for all purposes**. **That extinguishes the premise of
an Iowa-style contractor marketplace in Rhode Island as a matter of statute, not
licensing.** Both Rhode Island and Oregon also bar **holding yourself out** as
the regulated thing, so marketing copy carries a statutory edge in each. **Not** analogues: Nevada *referral
agency* and Oregon *long term care referral* — both are **facility placement**.

**SAIRNsenior as built on 2026-08-30 is OUTSIDE all four.** See
`2026-08-30-sairnsenior-iowa-135Q-scope-determination.md` and
`2026-08-30-sairnsenior-intermediary-scope-or-co-nv.md`. **The four triggers
differ, so an open-shift marketplace must be re-tested against each separately —
they would not all flip together.** Oregon adds a limb the others lack:
**representing to the public that you are a caregiver registry** is itself
unlawful without a licence, so marketing copy carries a statutory edge there.

## Layer 4 — cross-cutting patterns

- **Federal coupling — store the pointer, not the value.** **MO** adopts 42 CFR
  484 wholesale *including survey methodology*; **TN**'s aide hours point at the
  federal competency rule; **MI** defines a home health agency as
  *Medicare-certified*; **CT** § 31-58(e) and **OR** ORS 653.547 define overtime
  coverage by FLSA reference; **OR** ORS 443.195 benchmarks training to
  **NIOSH/OSHA**.
- **Dated rules hiding inside apparent constants.** **WA**'s 365-day window
  expires 2027-12-31; **NY**'s printed wage schedule ends 2026-12-31; **CA** adds
  a dementia topic 2027-01-01; **OH** splits recheck anniversaries on 2008-01-01;
  **LA** splits administrator qualifications on 2018-01-13.
- **Delegation is a shape applied to different axes.** **CO** delegates axis B
  (agency-determined risk) and specifies axis A in detail; **SC** § 501(B) does
  the exact reverse.
- **Self-direction inverts who trains and who schedules.** **NV** § 449.39519
  (client is managing employer **and trainer**), **VT** § 6321 (recipient hires,
  trains, **sets work schedules**, oversees payment and recordkeeping), **OR**
  § 443.360 (agency with choice — two contracted providers only).
- **Caregiver safety is an emerging statutory dimension.** **VT** 2024 § 6309 and
  **OR** 2025 §§ 443.190/443.195 — both land on the **assignment**, both concern
  **household individuals**, not only the client.
- **Dementia is a four-state overlay by four mechanisms.** **KY** 6 + 3 annual
  hours, pre-service; **AR** 4 hours inside the 40; **MO** topics, no hours,
  reaching independent contractors; **CA** one topic added to the annual five
  from 2027.
- **Wage rules live inside licensure rules.** **NV** NAC 449.39735 makes training
  time **and travel time** compensable at the employee's own rate.
- **Market structure.** **VT** designates **exclusive geographic franchises**
  with a four-year obligation to serve — the only closed market found. **OK**
  § 1-1962(B) regulates **the referral**, barring licensed facilities and
  clinicians from referring to an unlicensed agency.
- **Scope triggers that are not service type.** **AR** scopes by the **client's
  age** (50 or older, at the time services are provided). **CMS** excludes
  **congregate residential settings with 24-hour availability** and **PACE** from
  the EVV requirement.

## Coverage, stated honestly

**38 states touched on at least one axis. That is not coverage.** No state has
been read exhaustively; every round document carries its own Tier 2 list of what
was not read.

**No route found:** Alabama and Mississippi (both route their own codes to LexisNexis, which is JS-gated), Utah, Connecticut, Kansas, and Montana's *rules* (its statutes work). **Rhode Island, New Mexico and Wyoming were opened 2026-08-30** — RI via the RICR scheme at `rules.sos.ri.gov/regulations/part/216-40-10-17`, NM via `srca.nm.gov/nmac-home/nmac-titles/title-7-health/` (route works; the home health chapter is **[RESERVED]** and empty, so its operative rules are elsewhere and unlocated), WY via its Title 35 statute PDF from `wyoleg.gov`. See `2026-08-30-sairnsenior-state-round-18-wy-nm-ri.md`. **Idaho** is a self-declared
site outage, retried once. **Indiana** is on hold pending an API key.
**Arizona's** Administrative Code and **Oregon's** OARs are bot-walled.

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
> ### ⛔⛔ Oregon specifies the CLIENT INTAKE FORM in primary legislation
>
> **ORS 443.190(3) (2025 c.535 § 12) is a field list, not compliance boilerplate.**
> A home health agency or home hospice program must, at client intake, use a
> questionnaire that **at a minimum** asks about:
>
> 1. **Pets** at the setting — and **whether they can be secured away from the
>    area in which care is given, if the caregiver requests it** (so the answer is
>    two fields: presence, and securability-on-request);
> 2. **Suspected pest infestations**;
> 3. **The client's willingness to securely store any weapons present, prior to
>    any visit** (a client commitment, captured before the first visit).
>
> **And it is directional.** § 443.190(2)(b) requires the information be
> **provided to each staff member who will be responsible for the services** —
> so it attaches to the **assignment**, not just the client record. § 443.190(2)(c)
> adds that for hospital-discharge referrals, any **client history of violence**
> learned through continuity of care must be passed to each assigned caregiver.
> The definitions also cover **"household individual"** — anyone other than the
> client *"present or reasonably anticipated to be present"* — so risk is not
> scoped to the client alone.
>
> **§ 443.195 then names the delivery mechanism:** the entity must provide
> *"mechanisms by which home health care staff can perform safety checks,
> **including but not limited to the use of a mobile application** to access the
> relevant safety-related information collected … under ORS 443.190"*, plus
> **quarterly safety assessments** with assigned staff, **client identity
> verification before an initial visit**, NIOSH/OSHA-consistent hazard training,
> and policies permitting **data entry and chart updates outside the client's
> home** — which cuts against a point-of-care-only documentation design.
>
> **Build implication:** intake needs these fields, the assignment needs to carry
> them to the caregiver's device, and charting must work away from the home. See
> `2026-08-30-sairnsenior-state-round-14-oregon.md`.
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
