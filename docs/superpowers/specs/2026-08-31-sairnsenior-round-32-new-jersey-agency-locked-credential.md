# SAIRNsenior — round 32: New Jersey, where the worker's credential is void outside an agency

2026-08-31. **Research only.** Forty-sixth document in the series.

Round 31 left New Jersey unresolved and said *"assume the route exists and has
not been found yet."* **It did.** The statutes are behind a Folio NXT search
application at `lis.njleg.state.nj.us`, which `curl` cannot drive and the
browser can — the same pattern as Utah, Kansas, Alabama, Mississippi,
Connecticut and Idaho before it.

**Twelve of twelve candidates now read. Twelve of twelve had something the
corpus had missed.**

New Jersey turns out to hold the single most decisive provision found in
thirty-two rounds for the question SAIRNsenior actually has to answer.

---

## 1. The credential is agency-locked, in both directions

New Jersey certifies the worker through the **Board of Nursing** — not the health
department, not the employing agency. **N.J.S.A. 45:11-24.1 – 24.7** is the
scheme. Two of its sections decide the business model.

**Scope — the certificate carries a legend limiting when it is valid at all:**

> **N.J.S.A. 45:11-24.7, "Required language on certificate":** "The Division of
> Consumer Affairs shall require that a New Jersey Board of Nursing certificate
> issued to a homemaker-home health aide contain the following statement:
> **'Valid only if certified homemaker-home health aide is employed by a home
> health agency or health care service firm and is performing delegated nursing
> regimen or nursing tasks delegated through the authority of a duly licensed
> registered professional nurse.'"**
> *(L.1997, c.100, s.11; amended 1997, c.284, s.10.)*

**Renewal — the agency has to attest, or the credential lapses:**

> **N.J.S.A. 45:11-24.6, "Conditions for issuance of biennial recertification":**
> "The Division of Consumer Affairs shall require that the New Jersey Board of
> Nursing issue **biennial recertifications** to homemaker-home health aides
> **only upon receiving documented proof from a home health agency or health care
> service firm that the homemaker-home health aide is currently employed and
> regularly supervised by a registered professional nurse.**"
> *(L.1997, c.100, s.10; amended 1997, c.284, s.9.)*

> **This is a state-issued personal credential that cannot be exercised outside an
> employment relationship with a licensed agency, and cannot be renewed without
> one vouching for you.** Every other state read so far regulates the *agency* and
> lets the credential travel with the worker. New Jersey does the reverse:
> **the worker's credential is a function of who employs and supervises them.**
>
> A directly-hired New Jersey aide, or one engaged as an independent contractor
> by a platform, is not operating on a valid certificate on the face of § 24.7 —
> and after two years, has no certificate at all.

## 2. New Jersey also answers a question Kansas answered the opposite way

> **N.J.S.A. 45:11-24.2, "Oral competency test":** "The board shall provide that
> a person may satisfy the examination requirement for certification as a
> homemaker-home health aide **by passing an oral competency evaluation in English
> or Spanish.**" *(L.1990, c.125, s.1.)*

Against Kansas, **K.A.R. 28-51-116(e)(2)** (round 27):

> "**No test shall be given orally or by a sign language interpreter** since
> reading and writing instructions or directions **is an essential job task of a
> home health aide**."

**Two states, the same accommodation question, opposite answers — and each gives
its reason in the text.** Kansas declares literacy an essential job function;
New Jersey provides a Spanish-language oral route to the same certificate.
*A product that models "passed the competency test" as one boolean erases the
difference; a product that surfaces the route taken can be right in both states.*

## 3. Two more New Jersey pathways worth recording

**A paid family-member route, Medicaid-scoped and age-limited.**
**N.J.S.A. 30:4D-7qq** directs the Division of Medical Assistance and Health
Services to establish a programme under which **a family member of a Medicaid or
NJ FamilyCare enrollee may seek Board of Nursing certification as a
homemaker-home health aide** and then, **under the direction of a registered
nurse, provide services to that enrollee through a home care services agency** —
**provided the enrollee is under 21** and otherwise qualifies. "Family member" is
defined for the section (child, parent, parent-in-law, …).

> **A paid-family-caregiver pathway that still routes through an agency and an
> RN.** Compare Vermont § 6321, where the *recipient* hires and directs the
> attendant outright (round 31), and Maine § 2147, which simply excludes
> "families, friends and neighbors" from licensure. **Three states, three
> different answers to "can a relative be paid to do this?"**

**A bridge between credentials.** **N.J.S.A. 26:2H-12.96** lets a long-term care
facility employ a certified homemaker-home health aide **to work as a certified
nurse aide, provided the aide is enrolled in a qualified CNA programme and is
working toward CNA certification.** *(L.2020, c.112, s.2.)* — a
work-while-training bridge of the same family as Kansas's 90-day trainee window,
but crossing between two credentials rather than leading to one.

## 4. A gap in the source-persistence system, recorded rather than fixed

**These citations could not be stored by `tools/sairn_source_fetch.py`.** The
Folio NXT application serves documents from a stateful session behind
`gateway.dll`, with no stable per-section URL to fetch or hash. The text above
was read in the browser and is quoted from screenshots of the official state
system.

**Consequence, stated plainly:** New Jersey's entries rest on the same footing as
every pre-round-30 state — a write-up, not a stored source. **The manifest has no
NJ entry and should not be read as if New Jersey were unread.**

**Not fixed now.** Adding browser-capture to the fetch tool is a real feature with
real design questions (what is hashed when there are no canonical bytes?), and
inventing it at the end of a long session is how tools acquire the complexity
this project keeps deleting. **Logged as an option, not built.**

---

## 5. This changes the held item, and makes it sharper

Round 31 § 8 held a marketplace-scope question for Michael on three provisions —
South Carolina's financial-interest referral clause, Wyoming's unqualified
"arranging", and Vermont's designated-area prohibition. **New Jersey adds a
fourth that is different in kind and stronger than any of them.**

The first three ask *"does the platform become the licensed entity?"* — a
question about the platform. **New Jersey asks something worse: whether the
workers themselves hold a valid credential at all when nobody employs them.**
A platform can restructure to avoid being a provider. It cannot restructure the
legend printed on somebody else's certificate.

**Still not decided here.** What is established is the text of §§ 45:11-24.6 and
24.7 as quoted from the official statute database. **What is not established:**
how New Jersey applies "health care service firm" — that term is defined
elsewhere in New Jersey law and **was not read this round**, and it is entirely
possible that a platform *is* a health care service firm, which would resolve the
problem rather than create it. **That single definition is the next thing anyone
should read about New Jersey**, and it is a one-section job.

> **Recommendation for Michael, to accept or reject, unchanged in shape from
> round 31:** route these four to the marketplace-model decision gate as *scope*
> questions before further state reading — and read New Jersey's definition of
> "health care service firm" first, because it may collapse the New Jersey
> problem in one step.

---

## 5a. ADDENDUM, same session — "health care service firm" was read, and it names the business model

§ 5 said the definition of *health care service firm* "is the next thing anyone
should read about New Jersey, and it is a one-section job." **It was read. It does
not collapse the problem, but it changes its shape, and it is the single most
directly relevant provision found in thirty-two rounds.**

It is not in the health title at all. It is in **Title 34, Labor and Workmen's
Compensation**, attached to the Private Employment Agency Act:

> **N.J.S.A. 34:8-45.1(1)(a):** "Notwithstanding any other law or regulation to
> the contrary, an employment agency required to be licensed pursuant to
> P.L.1989, c.331 (C.34:8-43 et al.), **or any other firm, company, business,
> agency, or other entity that is not a home health care agency** licensed
> pursuant to P.L.1971, c.136 (C.26:2H-1 et seq.) **or a hospice** licensed
> pursuant to P.L.1997, c.78, **which employs, places, arranges for the placement
> of, or in any way refers, an individual to provide companion services, health
> care services, or personal care services in the personal residence of a person
> with a disability or who is age 60 or older, regardless of the title by which
> the provider of the services is known, shall be registered as a Health Care
> Service Firm** and shall be subject to the rules and regulations governing
> Health Care Service Firms adopted by the Division of Consumer Affairs in the
> Department of Law and Public Safety. The Division of Consumer Affairs is
> authorized to enforce the health care service firm registration requirement …
> upon any person whose operations are subject to this section, **whether the
> operations include the direct employment of individuals, the use of an Internet
> website or application, or any other process or business model.**"

> **New Jersey wrote the platform into the statute.** Where South Carolina reaches
> referral businesses only where the referrer has a financial interest, and
> Wyoming folds "arranging" into its home health definition without saying why,
> **New Jersey names "the use of an Internet website or application" and "any
> other process or business model" as things that do not avoid registration.**
> This is an anti-avoidance clause aimed squarely at the model.

**Three definitions come with it, and they draw the medical/non-medical line
somewhere no other state has put it:**

- **"Companion services"** — "non-medical, basic supervision and socialization
  services **which do not include assistance with activities of daily living**,
  and which are provided in the individual's home. Companion services **may
  include the performance of household chores.**"
- **"Health care services"** — services for maintaining or restoring physical or
  mental health, or any health-related services, **"and for which a license or
  certification is required as a pre-condition to the rendering of such
  services."**
- **"Personal care services"** — "services performed **by licensed or certified
  personnel**" assisting with ADLs that may involve physical contact: bathing,
  toileting, transferring, dressing, grooming, ambulation, exercise, personal
  hygiene.

> **In New Jersey, ADL assistance is by definition credentialed work.** Companion
> services stop where ADLs begin, and personal care services are defined as being
> performed by licensed or certified personnel. **Compare Maine, which excludes
> chore services from licensure entirely, and Minnesota, which lets unlicensed
> personnel do ADLs under a basic licence.** The same three activities —
> socialising, chores, ADLs — are cut into different categories by all three
> states.

**What this does to the held question.** It resolves one half and sharpens the
other:

- **Resolved:** a platform *can* be a health care service firm — in fact it
  **must register as one** if it employs, places, arranges or refers anyone into
  the home of a person 60+ or a person with a disability. Registration is with
  **Consumer Affairs**, not the Department of Health. So the certificate legend's
  phrase "*home health agency or health care service firm*" is reachable.
- **Still open, and now the whole question:** §§ 45:11-24.6 and 24.7 both say
  **"employed by"** — 24.7 for validity, 24.6 for renewal, the latter requiring
  documented proof the aide is "**currently employed and regularly supervised by a
  registered professional nurse**." **A registered health care service firm that
  places independent contractors is not obviously "employing" them.** Whether New
  Jersey treats placement by a registered HCSF as employment for these two
  sections is **not established here** — it turns on the Consumer Affairs rules
  (N.J.A.C. 13:45B), which were **not read**, and quite possibly on litigation
  history, which was **not searched**.

**That is now the one New Jersey question**, and it is narrow enough to put to
counsel in a sentence: *does placement by a registered Health Care Service Firm
satisfy "employed by" in N.J.S.A. 45:11-24.6 and 24.7?*

## 6. Where things stand

| | |
|---|---|
| Round 29 candidate list | **12 of 12 read** |
| Candidates that had something the corpus missed | **12 of 12** |
| States with a confirmed internal split | Kansas, North Carolina, Maryland, Connecticut, Minnesota, South Carolina, Vermont, New Hampshire, Maine, New Jersey |
| Discriminators confirmed | worker class · task · hands-on/not · direct access · client condition · client diagnosis · agency type · licence tier · territorial designation · **employment relationship** |

**Maryland remains the one partly-read state**: COMAR 10.07.05 `.12` (the waiver
of skilled services form) and 10.27.11 (delegation of nursing functions) are
still unread, and the publisher asks not to be swept, so those are two individual
page reads whenever someone picks it up.

## 7. Method notes

- **"Unresolved, not blocked" held for the eighth time.** Round 31 recorded New
  Jersey that way on the strength of this session's record; the route was found in
  four browser calls.
- **A search application is not a wall.** `curl` sees a 38 KB shell and JSON 404s;
  the browser sees 22 results. Same lesson as rounds 27–28, now with the
  additional wrinkle that **the win came with no persistable artefact** — worth
  knowing before assuming the new sources directory captures everything.
- **The most decisive provision in the survey was in the last state read**, in a
  seven-section run of the statute nobody had cited. There is no reason to think
  the remaining unread material is less load-bearing than what has been read.
