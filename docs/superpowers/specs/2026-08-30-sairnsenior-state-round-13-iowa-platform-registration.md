# SAIRNsenior — state round 13: Iowa registers the *software platform* itself

2026-08-30. **Research only.** Fifteenth document in the series.

**This is the most directly product-relevant finding in the entire survey.**
Every previous rule constrained SAIRNsenior's *customers*. Iowa has a category
that would constrain **SAIRNsenior**.

---

## ⛔⛔⛔ BUILD/BUSINESS CONSTRAINT — Iowa regulates "health care technology platforms"

**Iowa Code ch. 135Q / 481 IAC ch. 55, "Health Care Employment Agencies and
Health Care Technology Platforms."** Adopted ARC 6711C (effective 2023-01-04),
amended ARC 9022C (effective 2025-04-23).

> **481—55.2(135Q) Registration.** "A health care employment agency **or health
> care technology platform** operating in the state **shall register annually
> with the department and pay an annual registration fee**…"

The chapter runs two parallel tracks:

| Entity | Its workers are called |
|---|---|
| health care **employment agency** | **"agency worker"** |
| health care **technology platform** | **"independent nursing services professional"** |

**The platform track is aimed squarely at software that connects independent
professionals to health care entities** — and "health care entity" is defined to
include *"any **home health agency**, hospice, end-stage renal disease center,
rural health clinic, or federally qualified health care center"* certified by
CMS, plus entities under Iowa Code chs. 135B (hospitals), 135C (health care
facilities), 135G, 135H, 135J (hospice), **231C (assisted living programs)**,
**231D (adult day services)** and 135R.

### What registration actually obliges the platform to do

**§ 55.3(1) — the platform inherits the entity's screening duties.** It must
complete, for each independent nursing services professional, everything *"that
would otherwise be the responsibility of the health care entity if the health
care entity … contracted with the independent nursing services professional
directly"*:

- (a) **criminal, dependent adult abuse, and child abuse record checks**;
- (b) **physical examination and screening and testing for tuberculosis**;
- (c) confirmation that the professional **has completed all education, training
  and continuing education requirements** for their occupation **and is in good
  standing** with any minimum licensing or certification standards.

> **Axes B, D and A — moved onto the platform.** In every other state in this
> survey these are the agency's obligations. Iowa makes them the software
> vendor's obligations when the vendor is the placement channel.

**§ 55.3(2) — immediate abuse-allegation notification.** On receiving an
allegation of dependent adult abuse against an independent nursing services
professional, the platform **shall immediately notify the facility in which the
alleged abuse occurred** so the facility can separate the person. **An
inbound-report handling path with an immediate outbound obligation** — not a
ticket queue.

**§ 55.5(1) — documentation on demand** to the department or a health care entity
for a contracted worker.

**§ 55.5(2)(a) — registry reporting.** For agency workers who are certified nurse
aides, **report completed work assignments to the direct care worker registry**
sufficient to maintain active status, per 441 IAC 81.16(5) and
**42 CFR 483.35(d)(6) and 483.156(c)(2)**. *(Written in the rules against the
employment-agency track; whether it binds the platform track equally was not
established — see Tier 2.)*

> **Completed shifts are a regulatory filing.** A worker's registry status
> depends on assignments being reported. That is a scheduling system's own data,
> with a compliance consequence for the *worker* if it is not filed.

**§ 55.5(3) — quarterly reporting, including prices.** Each quarter a health care
employment agency must give the department:

1. a **detailed list of every health care entity participating in Medicare or
   Medicaid** it contracted with over the prior quarter; and
2. a **detailed list of the average amount charged** to those entities, **broken
   down by provider type** (hospital, nursing facility) **and by worker category**
   (certified nurse aide, registered nurse, …).

**§ 55.6 — complaints.** Anyone may complain; the complainant's name is
confidential; the department makes a preliminary probable-cause assessment and,
if met, **opens an investigation within 45 working days**; the standard is
**preponderance of the evidence**; both the platform and the complainant are
notified of the final report.

### Why this matters more than any earlier finding

Every rule up to now — Colorado forbidding scheduling, Louisiana's per-client
certification, Nevada's paid training — told SAIRNsenior what its **customers**
must do, and therefore what the product must support or withhold. **Iowa
describes a regulated entity that a placement-capable product could itself
be.**

**The trigger is unverified and that is the important caveat.** Ch. 55 says the
definitions "set forth in Iowa Code section 135Q.1 are incorporated herein by
reference", and **I have not read § 135Q.1**. So:

- **What is verified:** Iowa registers and regulates "health care technology
  platforms" annually, imposes screening, notification, documentation and
  quarterly price reporting on them, and defines "health care entity" to include
  home health agencies, assisted living programs and adult day services.
- **What is NOT verified:** the statutory definition of "health care technology
  platform" and of "independent nursing services professional" — i.e. **exactly
  which software is in scope.** A tool that only schedules an agency's own
  W-2 employees is plausibly outside it; a marketplace matching independent
  professionals to facilities is plausibly inside. **Neither reading is
  established, and the distinction is the whole question.**

**This belongs in a decision-gate pass, not just a research file** — it is a
question about what SAIRNsenior may sell in Iowa, and `sairn-decision-gate`
exists for exactly that class of question. Recorded here; not answered here.

---

## 2. Iowa's other relevant chapter

**481—50.9** applies background-check duties to a **"facility"**, defined for that
rule as, if state-regulated or receiving federal or state funding: a health care
facility under ch. 135C, **a home health agency**, or a hospice. Duties attach
**prior to employment**, and the facility must first inform the prospective
employee. Notably the rule also reaches **students** — a person applying for,
enrolled in, or returning to a **certified nurse aide training programme** — and
can prohibit a student's involvement in a clinical education component involving
children or dependent adults.

*"Crime"* for this rule **excludes Iowa Code ch. 321 simple misdemeanours**
(traffic) — a narrowing definition of the kind a barred-offence list must carry.

**Iowa chapter 53 (hospice)** defines *"home care provider"* as an agency that
contracts with the hospice to provide services in the patient's home, expressly
including **hospice aides, homemakers, nurses** and therapists — relevant to a
bundled model.

---

## 3. Nevada — the two sections flagged in round 12, now read

**§ 449.3978 — Attendants: prohibition on provision of certain types of
services.** The administrator must ensure each attendant works **within the
attendant's scope of service**. The enumerated prohibited services include:
insertion or irrigation of a **catheter**; irrigation of any body cavity
(including ear irrigation, enema, vaginal douche); application of a dressing
involving **prescription medication or aseptic technique**, including treatment
of moderate or severe skin conditions; **injections** into veins, muscles or skin
(except as authorised by § 449.39775); **administration of medication**, including
rectal suppositories, prescribed topical lotion and eye drops (same exception);
**performing physical assessments**; **specialized feeding techniques**; digital
rectal examination; **trimming or cutting toenails**; **massage**; specialized
range-of-motion services; and **medical case management**.

> **The first enumerated task deny-list in the survey.** Colorado forbids a
> *feature* to one registration category; **Nevada forbids named *tasks* to a
> role**, with a cross-referenced carve-out. A care-plan or task-catalogue
> builder needs a per-state, per-role deny-list — and "trimming or cutting
> toenails" is exactly the kind of ordinary-seeming task a product would
> otherwise offer without thinking.

**§ 449.3979 — written disclosure statement on acceptance.** The agency must
provide it, **require the client or their representative to sign it**, and
**incorporate a copy into the client's record**. Contents must include: a
statement, *"easily understandable to the client"*, that **it is not within the
scope of the agency's licence to manage medical and health conditions should they
become unstable or unpredictable**; **the qualifications and training
requirements for attendants**; charges; billing methods, payment systems, due
dates and the policy for notifying clients of **price increases**; the criteria
or conditions that may result in **termination of services** and the notification
policy; procedures for contacting the administrator **during all hours in which
services are provided**, and the **on-call policy**; and client rights and the
**grievance procedure**.

**Nevada's is at acceptance and signed; Arizona's (§ 36-144) is annual and
unsigned.** Same artefact family, different trigger and different proof.

**§ 449.3982 — supervisory home visits or telephone calls.** The administrator or
designee must conduct supervisory **home visits or telephone calls** to each
client's home, each **documented, dated and signed**, evaluating whether safe
techniques were used; whether the service plan was followed; whether the plan
still meets the client's needs; **whether the attendant has received sufficient
training relating to the services that attendant is providing to that client**;
and whether follow-up is needed.

> That fourth item is another **per-client training-sufficiency** test — the
> Louisiana family again, arriving through a supervision rule rather than a
> certification rule.

**And § 449.39519 is upgraded from inference to verified.** Round 12 labelled the
client-as-trainer finding as resting on a section heading. The body confirms it
and enumerates the content: general training; protocols including the rights and
responsibilities of client and personal assistant; grooming and dressing;
**bathing and hygiene including bed-bath and tub-bath techniques**; **bowel,
bladder and skin care** including catheter care, infection identification and
control, common bowel problems, early recognition of skin problems, prevention of
pressure sores and routine skin inspection; **assistive technology**; nutrition
and food preparation including balanced meals, dietary restrictions, hydration
and food handling; **maintaining health records**, with illustrations of how
information should be conveyed in written or dictated form to assure
confidentiality; and the training described in § 449.395185. Also nearby:
**§ 449.39521 visits and telephone interviews with clients** by the intermediary
service organization.

---

## 4. Routes

| Publisher | Result |
|---|---|
| `legis.iowa.gov/docs/iac/agency/481.pdf` | **works** — 19.7 MB, **2,463 pages**. Page-by-page keyword scan found the relevant chapters in ~4 minutes. |
| `leg.state.nv.us/NAC/` | works, as before |
| `oregonlegislature.gov/bills_laws/ors/ors443.html` | **works** — 141 KB, fetched, not yet read |
| `secure.sos.state.or.us/oard/` | **BOT-WALLED** — every page returns *"Please enable JavaScript to view the page content. Your support ID is: …"*. Oregon's **statutes** are reachable; its **administrative rules** are not. |
| `sos.ks.gov/publications/pubs_kar.aspx` | 200, but the page is site chrome — no KAR document links in it |

**Oregon is now a split state:** ORS via `oregonlegislature.gov`, OAR gated. Same
shape as Arizona (statutes yes, admin code no) and Oklahoma (statutes yes, rules
403).

---

## 5. Tier 2 — reported, not independently checked

| Item | Status | Provenance |
|---|---|---|
| **Iowa Code § 135Q.1 definitions** | **NOT READ — and this is the one that matters** | Defines "health care technology platform" and "independent nursing services professional". Determines whether SAIRNsenior itself is in scope in Iowa. |
| Whether § 55.5(2)(a) registry reporting binds the **platform** track or only the **employment agency** track | **NOT ESTABLISHED** | The rule text as read names the health care employment agency. |
| Iowa 481 ch. 55 registration fee amount, and §§ 55.4, 55.7+ | **NOT READ** | |
| Iowa 481 ch. 80 (home health) | **NOT LOCATED IN THE PDF** | The keyword scan surfaced chs. 50, 53 and 55; a chapter 80 was not among the hits. Whether Iowa still has one was not established. |
| NV NAC 441A.375, NRS 449.123, NRS 632.0166, NAC 449.39775, 449.395185 | **NOT READ** | Cross-references carrying axis B/D substance and the medication carve-out. |
| Oregon ORS 443 | **FETCHED, NOT READ** | |
| Kansas KAR | **NO DOCUMENT ROUTE FOUND** | Index page is chrome only. |
| Utah, Connecticut | **NO ROUTE** | Carried from round 12. |
| Alabama, Mississippi | **LEXISNEXIS-GATED** | Carried. |
| Indiana | **ON HOLD** | Per instruction. |
| The remaining ~18 states | **NOT ATTEMPTED** | Thirty-three states touched is not coverage. |

## 6. Method notes

- **A 2,463-page PDF is searchable page-by-page in minutes** and is a better
  route than a per-chapter viewer that returns a 10 KB wrapper. Iowa was recorded
  as "large" in round 12 as if that were a problem; it was not.
- **Scan for the category you did not expect.** The Iowa platform chapter turned
  up because the keyword sweep included `home care` generally, not because
  anything suggested a state regulates software vendors. A survey that only looks
  for "home health aide training" would never have found it.
- **When a finding is about the vendor rather than the customer, stop and route
  it.** This one is flagged for `sairn-decision-gate` rather than answered here.
