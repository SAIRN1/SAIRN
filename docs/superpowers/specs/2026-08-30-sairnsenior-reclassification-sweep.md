# SAIRNsenior — sweep: which states assign employment status by statute?

2026-08-30. **Targeted sweep**, run because Rhode Island's reclassification clause
turned up by accident and a second confirmed instance of a hidden business-model
trap warrants the same treatment the platform-registration category got.

**Result: three states, three different shapes — and Rhode Island's clause is
broader than round 18 recorded.**

---

## Method, and its limits

A ten-pattern regex over **every state corpus gathered tonight** — 60+ files,
including the 19.7 MB Iowa PDF, the 2.9 MB Wyoming PDF, both Louisiana `.docx`
volumes and the 787-page South Carolina chapter. Patterns: *not independent
contractors*, *shall be considered/deemed an employer*, *deemed/considered
employees*, *is the employer of*, *joint employer*, *employer of record*,
*co-employer*, *shall not be considered an independent contractor*.

**17 hits, of which 14 are real and 3 are false positives.** Discarded: Iowa's
agricultural-labour joint-employer test (29 CFR 516.33, in an unrelated chapter)
and Wyoming's county joint-community-board provision.

> **What this sweep does NOT establish.** It covers **the text already on disk**,
> which is the chapters read tonight — not the states' full codes, and not the
> ~12 states never touched. **A state with no hit here may still have such a
> clause in a chapter that was never fetched.** The same caution that proved
> warranted when Iowa's platform category turned out to have three siblings.

---

## 1. Rhode Island — and the clause is in BOTH parts, not just the staffing one

Round 18 and the RI determination recorded the clause at **R.I. Gen. Laws
§ 23-17.7.1-2(d)**, for *nursing service agencies*. **The sweep found it again in
216-RICR-40-10-17 — the home care regulation itself:**

> "A **home nursing care provider or home care provider** shall be considered
> **for all purposes an employer** and those persons that it supplies on a
> temporary basis shall be considered **employees and not independent
> contractors** and home nursing care providers or home care providers shall be
> subject to all state and federal laws which govern employer/employee
> relationships."

**This widens the finding materially.** It is not confined to temporary-staffing
businesses: **Rhode Island applies the same rule to ordinary licensed home care
providers** when they supply people on a temporary basis. An RI home care agency
cannot treat supplied caregivers as contractors either.

**Correction to my own framing:** the determination document presented this as a
*nursing service agency* rule that happened to foreclose the Iowa model.
**It is a Rhode Island policy applied across its home-care licensing scheme.**

## 2. Nevada — employer of record, by regulation

> "An **intermediary service organization shall serve as the employer of record**
> for and shall maintain a personnel file for each personal assistant employed by
> the intermediary service organization."

Nevada's self-directed branch (NAC 449.395xx) — the one where **the client is the
managing employer and trainer** (§ 449.39519) — nonetheless designates the
**intermediary service organization as employer of record**, with personnel-file
duties attached, and requires the personal assistant to carry **motor vehicle
liability insurance if transporting** the person.

> **Client directs, organisation is employer of record.** A split that a single
> `employer` field cannot hold.

## 3. Oregon — common law employer plus a statutory co-employer

**ORS 443.360(1)(g)**, the *agency with choice* definition:

> "'**Self-directed service delivery model**' means a model in which an individual
> is supported by an agency that **functions as the common law employer of direct
> support workers recruited by the individual** and provides financial management
> services and tasks in place of the individual. **The individual directs the
> direct support workers and is considered a co-employer with the agency.**"

**"Direct support worker"** is defined as a person providing attendant or personal
care services identified in the individual's plan **as an employee of the
agency** — and expressly **excludes** home care workers and personal support
workers as defined in ORS 410.600.

The agency must assist individuals with **recruiting and selecting** direct
support workers, among other tasks; DHS licenses agencies serving older adults
and people with physical disabilities, and OHA licenses those serving people with
behavioural health needs under 42 U.S.C. § 1396n(i) and (k).

> **A three-party employment structure written into statute:** the worker is the
> **agency's** employee, **recruited by the client**, whom the statute makes a
> **co-employer**. Neither party alone is "the employer".

---

## 4. What this changes

**Employment status is a regulated attribute in at least three of the states read,
and it is assigned three different ways:**

| State | Who is the employer | Mechanism |
|---|---|---|
| **Rhode Island** | the supplier — **and the workers are not contractors, for all purposes** | statute + regulation, in **both** the staffing and home-care parts |
| **Nevada** | the intermediary service organization, as **employer of record** — while the **client directs and trains** | regulation |
| **Oregon** | the agency as **common law employer**, with the **client as statutory co-employer** | statute |

**Three consequences for the model:**

1. **`employment_type` is not a free field.** In these states the answer is
   supplied by law and can contradict the contract. A product that stores
   "W-2 / 1099" as a customer preference is storing something the state may
   override.
2. **"Employer" can be split from "who directs the work".** Nevada and Oregon both
   separate them explicitly. A single employer reference cannot represent either.
3. **This belongs with the marketplace decision, not beside it.** Added to
   `2026-08-30-sairnsenior-DECISION-GATE-INPUT-marketplace-model.md`.

## 5. States swept with no reclassification hit

Corpora searched and clean: **Washington, California, New York, Texas, Florida,
Pennsylvania, Virginia, Georgia, Minnesota, North Carolina, Massachusetts,
Ohio, Colorado, Michigan, Missouri, Kentucky, Louisiana, Tennessee, South
Carolina, Oklahoma, Arkansas, Arizona, Wisconsin, Maryland, Maine, Vermont,
Wyoming, Montana, New Jersey, Connecticut, Illinois, Nevada (aside from the
employer-of-record clause above), Iowa (aside from the discarded agricultural
provision).**

**Read that list as "no hit in the text fetched", not as "this state does not do
it."** For most of these, what was fetched is one chapter.

## 6. Method note

**The sweep found in one pass what a year of reading might not.** Rhode Island's
Part 17 clause sat in a file already on disk, in a part already read for a
different purpose, and was missed because I was reading for *scope* and not for
*employment status*. **Once a pattern has two confirmed instances, sweep the
corpus you already have before fetching anything new** — it is nearly free and it
found two states the reading had walked past.
