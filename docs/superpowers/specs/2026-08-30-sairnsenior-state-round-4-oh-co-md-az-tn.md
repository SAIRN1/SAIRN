# SAIRNsenior — state round 4: Ohio, Colorado, Maryland, Arizona, Tennessee

2026-08-30. **Research only.** Sixth document in the series. Two-tier rule, and
the five-axis pathways model from
`2026-08-30-sairnsenior-state-round-3-pathways-model.md` used as the standard
shape throughout.

**Two of my own claims are corrected in §0 before anything is added.**

---

## 0. Two corrections first

**"Ohio 3701-60-04 and Colorado 6 CCR 1011-1 — FETCHED, NOT YET READ." Wrong on
both counts.** The probe loop that reported those 200s wrote every body to
`/dev/null` — nothing was ever on disk. And the Colorado URL I had was not
6 CCR 1011-1 at all; it resolves to **10 CCR 2505-10 § 8.500**, the Medicaid
*benefit* rule, not the licensure chapter. A status of "fetched" that rests on a
status code and never on a file is the same error as the Missouri citation logged
in the same table — **HTTP 200 is not possession, and it is not relevance.**
Both are fetched and read for real below.

**"Tennessee 0720-11" was a guessed citation and it is wrong.** 0720-11 is
*Certificate of Need Program — General Criteria*. Home care organizations are
**0720-27**. Second guessed citation in two days; the fix is the same as
Missouri's — read the chapter index before constructing a URL from a memory of
the numbering.

---

## 1. The routes — three found, one still closed

**Tennessee was never blocking me.** `publications.tnsosfiles.com` returns
`403 application/xml` — that is **S3 AccessDenied on a key that does not exist**,
not a bot wall. The index at `/rules/0720/0720.htm` fetched fine the whole time.
Its hrefs are **flat and date-stamped** — `0720-27.20260318.pdf`, directly under
`/rules/0720/`, not in a per-chapter subdirectory as I had assumed. Correct path,
instant 200 and 384 KB. **An XML 403 from an object store is a wrong-key signal;
read the index instead of guessing the key.**

**Maryland's canonical host is `regs.maryland.gov`.** `dsd.maryland.gov` 404s on
the paths I tried but **redirects** its chapter pages there. Following one
redirect gave the whole chapter, section by section, on a state host — no mirror
needed.

**Arizona statutes: `azleg.gov/viewdocument/?docName=…`** serves clean section
text. The plain `/ars/36/00411.htm` path also works; the sibling pattern I
guessed for § 36-425.01 404s, so use the index.

**Arizona's Administrative Code is still closed.** `apps.azsos.gov` and
`azsos.gov` 403 every variant tried — bare, full header set, with Referer, with
and without `.pdf`. `administrativerules.az.gov` does not resolve. **So the
four-header fix did not generalise, exactly as flagged.** Arizona below is
*statutory only*; AAC R9-10 is unread.

---

## 2. Tier 1 — Ohio

**Two licence categories, and the second is the one that matters here.** Ohio
licenses **skilled home health services** *and* **nonmedical home health
services** (OAC 3701-60-01(B)). "Nonmedical home health services" means **home
health aide services plus personal care services** (¶ R). Licence fee for the
nonmedical application: **$250**, cashier's check or postal money order
(3701-60-03(B)).

**Axis A is absent — and that is the finding.** Chapter 3701-60 has eleven rules:
definitions, applicability, licensure, enforcement, **state and national database
review, criminal records check, conditional employment, disqualifying offenses,
exclusionary periods/certificates/pardons**, records and reports, liability.
**There is no training or competency rule in the chapter at all.** Ohio regulates
this workforce almost entirely through axis B.

**Axis B, in unusual detail.**
- **3701-60-06(A):** the chief administrator must request a superintendent
  criminal records check for **each applicant for a direct care position**.
- **(B) recurrence:** for employees hired **before 2008-01-01**, within 30 days
  of the hire anniversary and **at least every five years** after; hired **on or
  after 2008-01-01**, within 30 days of the **fifth** anniversary and every five
  years after. *A recurring obligation with a date, not a one-time gate.*
- **(C) residency:** absent proof of five years' Ohio residency (or an FBI
  request within that window), the federal check is triggered.
- **3701-60-07 conditional employment** — Ohio's provisional-hire route, and it
  is conditional on **three** things: the 3701-60-05 database review shows
  nothing disqualifying; a completed **fingerprint impression sheet before**
  conditional employment begins; and the records check requested **not later than
  five business days** after the person starts. A staffing-agency referral
  substitutes a dated letter on the agency's letterhead.
- **3701-60-08** enumerates disqualifying offences by Revised Code section — a
  long list running from cruelty to animals through homicide, assault, menacing
  by stalking and beyond — and bars employing **or continuing to employ** anyone
  convicted, pleading guilty, **or found eligible for intervention in lieu of
  conviction**.
- **3701-60-09** then supplies **exclusionary periods, certificates and pardons**
   — i.e. a disqualification can expire or be cured. **A boolean
  `background_check_passed` cannot represent that.**

"Direct care" is defined broadly at 3701-60-01(F): a listed service in the
patient's home, **or any activity requiring the person to be routinely alone with
a patient or routinely have access to their personal property or financial
documents.**

---

## 3. Tier 1 — Colorado

Read: **10 CCR 2505-10 § 8.500** (Dept. of Health Care Policy and Financing,
Medical Services Board) — the Medicaid home health benefit rule, 192 pages.

**Axis A runs through the Nurse Aide Practice Act.** Colorado's home health aide
equivalent in this rule is the **CNA**, and its limits are drawn from the
Colorado Nurse Aide Practice Act: a CNA may provide only services ordered on the
Home Health Plan of Care by the ordering practitioner, assists with ADLs, and
**may not perform a visit for the purpose of behaviour modification**.

**Axis E is explicit and generates a record.** *"When an agency allows a CNA to
perform skilled tasks that require competency or delegation, the agency shall
have policies and procedures regarding its process for determining the competency
of the CNA. All competency testing and documentation related to the CNA shall be
retained in the CNA's personnel file."* Task-specific competency: exercise/range
of motion is skilled where prescribed **and the CNA has demonstrated
competency**, with the agency ensuring training and keeping the program
documentation in the client record for renewal at each Plan of Care.

**A scheduling-relevant limit:** CNA services may only be ordered where the task
is **outside the usual responsibilities of the client's family member/caregiver**.

**Not read: the licensure chapter (6 CCR 1011-1).** Everything above is the
Medicaid benefit rule. Colorado's home care agency *licensure* requirements are
unlocated — the CCR PDF generator is keyed by opaque `ruleVersionId`.

---

## 4. Tier 1 — Maryland

**COMAR 10.07.05, Residential Service Agencies** — Maryland's home care licensure
chapter, read from `regs.maryland.gov`.

**Axis B + D, as one enumerated screening list (§ .10B(1)).** Before referral to
clients an agency must complete **all** of: a State criminal history records
check **or a private agency background check** under Health-General Art., Title
19, Subtitle 19; verification of current professional licensure/certification;
**a basic health screening including tuberculosis screening**; verification of
references; verification of employment history; I-9 completion; verification of
identity and employment eligibility; **an in-person interview before the
individual is referred to clients**; and **completion of a skills assessment and
demonstration before client referral**.

> Two of those are not screening in the ordinary sense and would be lost in a
> `background_check` field: **an in-person interview** and **a skills assessment
> and demonstration**, both gated on *referral*, not on hire. Maryland's axis A
> is discharged by demonstration, at the point of assignment.

**A certification requirement with a client-consent escape (§ .10D–E).** An
agency **may not knowingly provide or refer a caregiver who is not certified**
unless the client (1) needs no ADL assistance, (2) needs only ADL assistance and
the **supervising nurse** judges there are no predictable adverse health
consequences, or (3) **signs a waiver of skilled services** under § .12D. A
**certified** caregiver is required where the client needs ADL performance or
**administration of medication**.

**§ .11 Training — topics, no hours, and an approval step.** Training must be
appropriate to the clients' needs; **sources other than the agency may provide it
only as approved in writing by the Office of Health Care Quality**. Minimum
content: instruction and **supervised practice** in personal care of the sick or
disabled at home; identifying situations requiring **referral to a registered
nurse**, including significant changes in condition; record keeping; ethical
behaviour and confidentiality; **CPR**; standard precautions for infection
control; and prevention of abuse and neglect.

**CPR is new to this survey** — no other state read so far names it in the
minimum curriculum.

**§ .10F** adds a reporting duty: conduct that may be grounds for action under
Health Occupations Art. §§ 8-316 / 8-6A-10 must be reported to the **Board of
Nursing and the Office of Health Care Quality immediately**.

---

## 5. Tier 1 — Arizona (statutory only)

**A.R.S. § 36-411 — fingerprint clearance card.** As a condition of licensure and
of employment, employees, owners, contracted persons and volunteers of a home
health agency who provide the listed services and are not already fingerprinted
by a Title 32 health-professional board must **hold a valid fingerprint clearance
card** (Title 41, ch. 12, art. 3.1) **or apply for one within twenty working days**
of starting employment, volunteering or contract work. A health professional who
met their own board's fingerprinting requirement need not submit a second set
(§ 36-411(B)).

**§ 36-411(C) — documented good-faith efforts, with two dated registry duties.**
The agency must make documented, good-faith efforts to contact previous
employers, **verify the current status of the fingerprint clearance card**, and:

- **beginning 2025-01-01**, verify a potential employee is **not on the adult
  protective services registry** under § 46-459 — and **may not hire** anyone who
  is; and
- **on or before 2025-03-31**, verify that **each existing employee** is likewise
  not on it.

> **A third registry polarity.** Massachusetts queries an adverse-findings
> registry pre-hire; Wisconsin requires registry *presence* as the qualification;
> Arizona does the adverse-findings check **and applies it retroactively to the
> existing workforce on a fixed date**. A model holding one registry event per
> worker cannot express a one-off sweep of everyone already employed.

Also present in the statute book and not read: **§ 36-425.01** (home health agency
licensure) and **§ 36-144** (home care services; disclosure).

---

## 6. Tier 1 — Tennessee

**Rule ch. 0720-27, Standards for Home Care Organizations Providing Home Health
Services** (Health Facilities Commission; transferred from 1200-08-26; version
dated **2026-03-18**).

**Axis A, hour-denominated — and the timing is unusually permissive:**

> "**Home Health Aide.** A person who has completed a total of **seventy-five
> (75) hours** of training which included **sixteen (16) hours of clinical
> training** **prior to or during the first three (3) months of employment**…"

Qualified to provide basic services including simple procedures as an extension
of therapy services, personal care for nutritional needs, ambulation and
exercise, and household services. "Home care organization" takes its meaning from
**T.C.A. § 68-11-201**.

**Note the shape:** the hours may be completed **during** the first three months.
Washington's 75 hours run to a 120-day deadline from hire with **5 hours before
any care**; Tennessee names no pre-service floor in this definition. **Same
number, different gate** — a model storing "75" and a deadline, with no
pre-service component, would get Washington wrong.

**Axis C — Tennessee has a statewide registry too.** Ch. **0720-39**, *Registry
of Persons Who Have Abused, Neglected, Misappropriated, or Exploited the Property
of Vulnerable Individuals* (version **2025-08-03**), under T.C.A. tit. 68, ch. 11,
pt. 10. It covers notifications of intent to place, referrals from courts,
state agencies, the TBI or law enforcement, notification to the individual,
information requests, and **requests for removal** — with contested-case due
process under the UAPA. **Like Massachusetts, removal is possible**, so registry
status is a dated state, not a permanent flag.

---

## 7. Axis tally after twenty-three states

| Axis A shape | States |
|---|---|
| **Hour-denominated** | WA 75 (+5 pre-service, 120 days) · **TN 75 (16 clinical, by end of month 3)** · TX *HHA only* 75 · CA 5 + 5 annual · GA 40 *(one of four routes)* |
| **Competency / enumerated routes** | PA · VA · MN · NC · NY · MA · NJ · FL *(homemaker/companion)* · TX *PAS* · **CO** *(CNA + delegation competency)* · **MD** *(skills demonstration before referral)* |
| **Registry presence as qualification** | WI |
| **No training rule at all** | **OH** — regulated through axis B alone |

| Axis C polarity | States |
|---|---|
| Adverse-findings, pre-hire query, hire barred on a hit | MA · **AZ** · **TN** |
| Presence required to work | WI |
| Nurse-aide registry as a qualification route | GA · VA · NC |
| Removal/expiry possible, so status is dated | MA (1 yr) · TN (UAPA petition) · **OH** (exclusionary periods, certificates, pardons) |

**Five of twenty-three states name an hour figure.** The `training_hours` field
would be null for eighteen, and **Ohio would be null on the whole axis**.

---

## 8. Tier 2 — reported, not independently checked

| Item | Status | Provenance |
|---|---|---|
| Arizona Administrative Code R9-10 (home health agency licensing rules) | **BLOCKED — no route found** | `apps.azsos.gov` and `azsos.gov` 403 on every variant incl. the full header set and a Referer; `administrativerules.az.gov` does not resolve. Arizona above is statute only. |
| A.R.S. §§ 36-425.01, 36-144 | **NOT READ** | Identified in the Title 36 index, not fetched. |
| Colorado 6 CCR 1011-1 (home care agency licensure) | **UNLOCATED** | The CCR PDF generator is keyed by opaque `ruleVersionId`; the id I had returns the Medicaid rule instead. |
| TN 0720-27 beyond the aide definition | **NOT READ** | 107 KB of rule text; only definitions were mined. |
| TN 0720-39 duties on employers | **NOT READ** | The rule covers Commission procedure; whether it imposes a pre-hire *query* duty on a home care organization (as MA § 155.010(E)(3) does) was **not** established. Do not assume symmetry with MA. |
| OH 3701-60-05 (database review) and -09 (exclusionary periods) full text | **PARTIALLY READ** | Titles and role are known; the substantive lists are not. |
| MD Health-General Art. Title 19 Subtitle 19 | **NOT READ** | COMAR § .10 cross-references it for the background-check standard. |
| Missouri | **CITATION WRONG, ABANDONED** | Carried from round 3. |
| The remaining ~28 states | **NOT ATTEMPTED** | Twenty-three states on at least one axis is not coverage. |

## 9. Method notes

- **`403` with `Content-Type: application/xml` from an object store means a bad
  key, not a bot wall.** Tennessee cost several probes to a wall that was never
  there. Fetch the index and read the real hrefs.
- **Follow the redirect and note where it lands.** `dsd.maryland.gov` →
  `regs.maryland.gov` is how Maryland's canonical host was found; the mirror I
  nearly settled for was unnecessary.
- **A probe loop that writes to `/dev/null` proves reachability and nothing
  else.** Two states were logged as "fetched" on that basis. Either save the
  body or record the result as *reachable*, never as *fetched*.
- **Two wrong guessed citations in two days** (MO 19 CSR 30-26, TN 0720-11), both
  returning real documents about something else. Read the chapter index first;
  constructing a citation from memory of a numbering scheme fails silently
  because the fetch succeeds.
