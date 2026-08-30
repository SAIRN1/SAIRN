# SAIRNsenior — state round 3, and the qualification-pathways model written down

2026-08-30. **Research only.** Fifth document in the series. Same two-tier rule.

Closes the **Texas Personal Assistance Services** gap that has been open since
2026-08-29, adds **Wisconsin**, and — because Michael asked for it to become the
standard shape rather than a finding about four states — states the
**qualification-pathways model** explicitly, with the axes the eighteen states
read so far actually require.

---

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
| Missouri 19 CSR 30-26 | **WRONG CHAPTER, ABANDONED** | Fetched cleanly (189 KB) but contains no aide-qualification or hour provisions — the citation was a guess and it was wrong. Recorded so nobody re-fetches the same PDF. |
| Arizona (`apps.azsos.gov` 403), Tennessee (`publications.tnsosfiles.com` 403), Maryland (`dsd.maryland.gov` 404), Seattle DWO (404) | **THREE RESOLVED 2026-08-30, ARIZONA STILL BLOCKED** — see `2026-08-30-sairnsenior-state-round-4-oh-co-md-az-tn.md` | Tennessee was never blocked: an XML 403 from that object store is a **bad key**, and the real hrefs are flat and date-stamped. Maryland's canonical host is `regs.maryland.gov`, which `dsd.maryland.gov` redirects to. Arizona statutes are on `azleg.gov`; the **Administrative Code has no working route**. |
| Ohio 3701-60-04, Colorado 6 CCR 1011-1 | **THIS ROW WAS WRONG — corrected 2026-08-30** | Neither was on disk: the probe loop wrote every body to `/dev/null`, so "fetched" rested on a status code and nothing else. The Colorado URL was also **not** 6 CCR 1011-1 — it resolves to 10 CCR 2505-10 § 8.500, the Medicaid benefit rule. Both now fetched and read for real; CO's licensure chapter remains unlocated. |
| Municipal domestic-worker ordinances | **NOT ATTEMPTED** | Seattle's canonical URL 404s; needs the current one. |
| The remaining ~33 states | **NOT ATTEMPTED** | Eighteen states on at least one axis is not coverage. |

## 6. Method notes

- **The header-set fetch is not universal.** It unblocked mass.gov, medicaid.gov
  and hhs.texas.gov; Arizona, Tennessee and Maryland still refuse. Reporting it
  as *the* fix would have been the same over-generalisation as calling the
  original block a "request fingerprint".
- **A guessed citation that fetches cleanly is still a wrong citation.** Missouri
  returned a real 189 KB PDF containing nothing relevant. **HTTP 200 is not
  relevance** — check the content answers the question before counting it.
- **An agency FAQ can be more current than the code.** Texas's is dated July 2026
  and carries `<Added 07/02/26>` markers. It is still one step from the rule, and
  the label stays on.
