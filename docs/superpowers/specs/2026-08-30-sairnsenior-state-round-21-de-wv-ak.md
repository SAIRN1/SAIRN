# SAIRNsenior — round 21: Delaware expressly permits what Rhode Island forbids

2026-08-30. **Research only.** Thirtieth document in the series.

**Delaware § 122(3)(o) affirms independent contractors in the same breath that
Rhode Island denies them** — the cleanest contrast the survey has produced, and
it turns the reclassification dimension from a binary into a three-way.

Also: **West Virginia and Delaware opened**, Alaska's route is confirmed working,
and **the "Delaware has no home-care chapter" hypothesis was wrong** — which is
why it was not written up as a finding last round.

---

## 1. Delaware — regulated inside a department-powers section, not a chapter

Round 20 recorded that Delaware's 143 title-16 chapters contain **no** home health
or home care chapter, and flagged it as *possibly* a real finding. **It was not.**

Delaware regulates home health inside **16 Del. C. § 122(3)(o)** — the section
enumerating the Department of Health and Social Services' powers:

> "…**Establish standards for public health quality assurance in the operation of
> home health agency programs and regulate the public health practice of such
> programs.**"

> **No chapter ≠ no regulation.** Had round 20 published "Delaware does not
> regulate home care", it would have been wrong on the strength of a chapter list.
> **A missing chapter is a hypothesis, not a finding** — the same discipline that
> kept Michigan's negative in Tier 2 until the statute was read.

### The definition, and the aide-only business is inside it

> "A **home health agency** is any business entity or subdivision thereof, whether
> public or private, proprietary or not-for-profit, **which provides home
> health-care services.**
> **A.** Home health-care services include but are not limited to: licensed
> nursing; physical therapy; speech therapy; audiology; occupational therapy;
> nutrition; social services; **or home health aides.**
> **B.** Home health agencies shall provide: **I.** two or more home health-care
> services, **one of which must be either licensed nursing services or home
> health aide services**; **or II. home health aide services exclusively**, which
> shall include but not be limited to: **(A) Feeding; (B) Bathing; (C) Dressing;
> (D) Grooming; and (E) Incidental household services.**"

**Delaware's "home health agency" reaches a purely non-medical, aide-only
business** — feeding, bathing, dressing, grooming and incidental household
services, with no nursing at all. That is a **seventh answer to the
unlicensed-segment question**: Delaware does not create a separate non-medical
category; **it puts the non-medical business inside the home health definition.**

### The clause that matters — § 122(3)(o)(2)(A)

> "Home health agency services are provided **directly through employees of the
> agency or through contract arrangements, including those contracts with
> individuals considered to be independent contractors.**"

> **This is the exact inverse of Rhode Island.** R.I. Gen. Laws § 23-17.7.1-2(d)
> and 216-RICR-40-10-17 say supplied workers *"shall be considered employees and
> **not** independent contractors"*, for all purposes. **Delaware writes
> independent contractors into the statutory definition of how the service is
> delivered.**
>
> **The reclassification dimension is therefore three-way, not binary:**
>
> | Polarity | States | Effect |
> |---|---|---|
> | **Deems employees** | **Rhode Island** | contractors are unavailable for supplied workers, for all purposes |
> | **Assigns employer roles without forbidding contractors** | **Nevada** (intermediary is *employer of record*), **Oregon** (agency is *common law employer*, client is *co-employer*) | who the employer is, is fixed by law |
> | **Expressly permits contractors** | **Delaware** | the statute names independent contractors as a lawful delivery route |
> | **Silent** | Nebraska ("employ or contract with"), North Dakota, West Virginia and every other state read | no statutory position |
>
> **A product cannot infer a state's position from silence in either direction.**
> Delaware and Rhode Island both address the question explicitly and answer it
> oppositely.

---

## 2. West Virginia — opened, and the path was the problem twice over

Round 19 diagnosed *my path*. Correct — but the first correction was also wrong.

**W. Va. Code art. 16-5D is *repealed*.** `§16-5D-1. Purpose. [Repealed.]`, in an
article whose breadcrumb reads "…RESIDENCES". **A sixth repealed chapter/article
in this survey.**

**The right article came from the chapter index:** **ARTICLE 2C — HOME HEALTH
SERVICES.** (Chapter 16 also carries art. 5I *Hospice Licensure Act*, art. 5N
*Residential Care Communities*, art. 5R *Alzheimer's Special Care Standards Act*,
art. 5X *Caregiver Advise, Record and Enable Act* and art. 5AA *Medication
Administration by Unlicensed Personnel in Nursing Homes* — several worth a later
look.)

**§ 16-2C-1 Definitions:**

> "'**Home health services**' shall mean and include, but not be limited to, the
> following services furnished to an individual **who is under the care of a
> physician**, such services to be provided **on a visiting basis in a place of
> residence used as the individual's home**: (1) **part-time or intermittent
> nursing care** provided by or under the supervision of a registered
> professional nurse; (2) physical, occupational or speech therapy; (3) medical
> social services under the direction of a physician; (4) **part-time or
> intermittent services of a home health aide**."

**A physician-care predicate.** West Virginia's definition applies only to
services furnished to someone *under the care of a physician* — narrower than
Delaware's, which needs no physician at all.

> **Caution, stated because the article title is misleading:** § 16-2C-2 is
> *"Department to provide services; charges for services; authority to employ
> personnel…"* — **article 2C reads as a programme-authorisation article, not
> obviously a licensure one.** Whether West Virginia licenses home health
> agencies, and where, is **not established**. Art. 5D would have been the
> obvious candidate and is repealed.

**Reclassification check: clean** (WV, DE-for-*deeming*, ND all zero — Delaware's
affirmative contractor clause is a separate finding, not a reclassification).

---

## 3. Alaska, Hawaii, South Dakota

**Alaska — route confirmed working, banner notwithstanding.** The page carries
*"This page is no longer used please use www.akleg.gov"* **while itself being on
`www.akleg.gov` and rendering the Alaska Administrative Code title list** (Title 1
General Provisions through Title 6 Governor's Office and beyond). **The banner is
stale, not a redirect.** The relevant title (7, Health and Social Services) was
not yet walked.

**Hawaii — parser fixed, sections not identified.** The IIS listing uses uppercase
`<A HREF=` and yields per-section files at
`/hrscurrent/Vol06_Ch0321-0344/HRS0321/HRS_0321-NNNN.htm`. Route works.

**South Dakota — still closed, and now with five endpoint forms excluded.**
`/Statutes/34-12`, `/api/Statutes/34-12`, `/api/Statutes/Chapter/34-12`,
`/api/Statutes/Chapter?Code=34-12`, `/api/Statutes/Codified/34-12`,
`/api/Statutes/ContentsByChapter/34-12` and `/Statutes/34-12/PDF` all return the
**same 2,256-byte Vue shell**, including with `Accept: application/json`. The
shell's own `dns-prefetch` hints name **`mylrc.sdlegislature.gov`** as a
companion host — `mylrc.sdlegislature.gov/api/Statutes/Chapter/34-12` returns
**404**, which is at least a different answer and suggests the right host with
the wrong path.

---

## 4. Tier 2

| Item | Status |
|---|---|
| Whether West Virginia **licenses** home health agencies, and under what | **NOT ESTABLISHED** — art. 2C reads as programme authorisation; art. 5D is repealed. |
| WV arts. 5I, 5N, 5R, 5X, 5AA | **NOT READ** — hospice licensure, residential care communities, Alzheimer's standards, CARE Act, unlicensed medication administration. |
| DE § 122(3)(o) beyond the definition; DE administrative code (16 DE Admin. Code 4469?) | **NOT READ** — the operative standards are in regulation, not the statute. |
| Alaska Title 7 AAC; Hawaii HRS 321 sections | **ROUTE OPEN, NOT WALKED** |
| South Dakota | **CLOSED for now** — seven endpoint forms excluded; `mylrc` host identified but path unknown. |
| AL, MS, UT, CT, KS | **NO ROUTE** — carried. |
| ID | **CLOSED** — state outage. |
| IN | **ON HOLD** |

## 5. Method notes

- **A missing chapter is a hypothesis.** Delaware's home health rules are inside a
  department-powers section. Publishing "no chapter, therefore no regulation"
  would have been a confident wrong finding built on a correct chapter list.
- **Two wrong paths in a row can both be wrong differently.** West Virginia's
  first path was mine; the second was a *repealed article*. The chapter index
  resolved it — sixth state in a row.
- **A stale banner is not a redirect.** Alaska's page says it is no longer used
  and is serving current content at the URL it points to.
- **Excluding endpoints is progress.** South Dakota now has seven forms ruled out
  and a companion host identified, which is a better starting position than
  "SPA, blocked".
