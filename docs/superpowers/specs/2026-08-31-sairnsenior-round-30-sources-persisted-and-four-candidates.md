# SAIRNsenior — round 30: sources are now kept, and four of the twelve candidates opened

2026-08-31. **Research only.** Forty-fourth document in the series.

Two things this round. **The sources are now persisted** — the gap that made
round 29's analysis weaker than it needed to be is closed going forward. And
**four of the twelve candidate states from round 29's absence list were read**,
applying the four-axis lens rather than assuming one worker class per state.

**All four had something the corpus had missed. One of them — Minnesota —
abolishes the worker class entirely.**

---

## 1. `docs/sources/sairnsenior/` — what is kept, and what deliberately is not

`tools/sairn_source_fetch.py` fetches a legal source and stores its **extracted
text** at `docs/sources/sairnsenior/<STATE>/<slug>.txt`, with a `MANIFEST.json`
recording URL, fetch date, HTTP status, content type, **original byte size and
sha256 of the original bytes**, page count and a note.

**Originals are not stored.** They run 7–20 MB; every question this corpus has
actually been asked is a text question. **Reproducibility lives in the sha256,
not in the bytes** — any quotation can be re-fetched and checked against the
exact document it came from, and a changed hash later is itself a signal.

**Twelve sources stored, 5.2 MB.** Three design points came from real friction
this round rather than from planning:

- **`curl` fallback.** Arizona's and Mississippi's hosts return **403 to urllib
  and 200 to curl** for the identical URL and User-Agent. The difference is below
  the header layer, so no header-setting fixes it. The tool tries urllib, then
  shells out to curl.
- **`--from-file`.** Mississippi's host served the 7 MB Title 15 Pt 16 PDF once
  this morning and **returned 403 to the same URL about an hour later**. A source
  can stop being available *after* you read it — which is the argument for this
  directory, arriving as a live example while the directory was being built.
- **Publisher requests are honoured.** Maryland's COMAR publisher prints *"Please
  do not scrape. Instead, bulk download."* on every page. That host is not swept;
  individual pages read in the course of research are what any human reader does.
  The constraint is recorded in the manifest's `publisher_note` so the next
  session inherits it instead of rediscovering it.

**Two manifest entries were corrected before this was committed**, because a
manifest that lies is worse than no manifest:

- `ND/NDCC-23-17.4-home-health` → **`NDCC-23-17.4-hospice-programs`**. The
  chapter is Hospice. It is kept, with the mis-hit named in the note.
- `SC/R.61-77-in-home-care-providers` → **`Reg-60-77-home-health-agencies`**.
  See §5.

**This begins at round 30.** Rounds 1–26 are not reconstructed and their claims
still rest only on the write-ups.

---

## 2. Minnesota — the state that deletes the worker class

Minnesota was in round 29's **group A**: no worker class named anywhere in the
corpus. The reason turns out to be that **Minnesota does not use worker classes.**

There is no home health aide, no personal care aide, no companion, no state
registry for any of them. There is **"unlicensed personnel"**, and the
requirements scale by **which licence the employer holds** and **which tasks are
delegated**.

**Two licence tiers (Minn. Stat. § 144A.471, subds. 5–7):**

- **Basic home care licence** — six assistive tasks **"provided by licensed or
  unlicensed personnel"**: dressing, self-feeding, oral hygiene, hair care,
  grooming, toileting, bathing; standby assistance; **verbal or visual reminders
  to take regularly scheduled medication**, including bringing previously set-up
  medication or medication in original containers; reminders for treatments and
  exercises; preparing modified diets ordered by a licensed health professional;
  and — **only if the provider is also providing at least one of the other five**
  — laundry, housekeeping, meal preparation, shopping and household chores.
- **Comprehensive** — everything basic, plus professional services and **tasks
  delegated to unlicensed personnel by a registered nurse**.

> **Clause (6) is a dependency rule, not a task.** Housekeeping and shopping are
> permitted *only as an adjunct* to hands-on assistance. A pure
> chores-and-errands service falls outside the basic licence altogether. **No
> other state read so far conditions one task on the presence of another.**

**Requirements for unlicensed personnel (§ 144A.4795, subd. 3):**

| | Basic-licence provider | Comprehensive-licence provider (delegated nursing) |
|---|---|---|
| Route | training + competency evaluation on the 15 statutory topics, **or** a written/oral test **plus a practical skills test** on topics (5), (7) and (8) | written/oral test on the fuller topic list **plus a practical skills test on named topics and on every delegated task the person will perform** |
| Alternatives | — | **satisfy current Medicare training/competency requirements for home health aides or nursing assistants (42 C.F.R. 483 / 484.36)**, **or** have completed a commissioner-approved nursing-assistant course **before 19 April 1993** |
| Hard limit | **may not perform delegated nursing or therapy tasks** | — |

The 15-topic floor for everyone includes items no other state names: **fall
prevention for providers working with the elderly or people at risk**,
**understanding appropriate boundaries between staff and clients and the
client's family**, and **awareness of commonly used health technology equipment
and assistive devices**.

**Two provisions are directly product-shaped:**

- **§ 144A.4795, subds. 5–6 close the contractor and temp-agency routes
  explicitly.** An individual contractor excluded from licensure, and staff from
  a temporary staffing agency excluded from licensure, **must meet the same
  requirements** and temp staff **"shall be treated as if they are staff of the
  home care provider."**
- **§ 144A.4795, subd. 4 statutorily requires a live competency system.** The
  comprehensive provider "must establish and implement a system to communicate
  **up-to-date information to the registered nurse** … regarding the current
  available staff and **their competency** so the registered nurse … has
  sufficient information to determine the appropriateness of delegating tasks."
  **Minnesota requires by statute the thing a product would build.**

> **Minnesota is a fifth discriminator: the licence tier, defined by task list,
> with worker class deliberately irrelevant.** It is the exact inverse of Kansas,
> which names two worker classes and gives each its own regime. A schema with a
> `worker_class` column has nothing to put in it for Minnesota, and a schema
> without one cannot represent Kansas.

---

## 3. New Mexico — the whole chapter was repealed on 1 July 2024

**7.28.2 NMAC, "Requirements for Home Health Agencies", was repealed effective
1 July 2024**, and **NMAC Title 7 Chapter 28 — Home Health Services — is marked
[Repealed] in its entirety.**

It is not an isolated repeal. Chapter 1 (Health General Provisions) shows the
same date-stamped clearing-out, including parts that are exactly the
qualification-axis material this survey looks for:

> **Health Facility Licensure Fees and Procedures [Repealed]** · Health Facility
> Sanctions and Civil Monetary Penalties [Repealed] · **Caregivers Criminal
> History Screening Requirements [Repealed]** · **Employee Abuse Registry
> [Repealed]** · Incident Reporting, Intake, Processing and Training Requirements
> [Repealed] · **Abuse, Neglect, Exploitation, and Death Reporting, Training and
> Related Requirements for Community Providers [Repealed]** · Long-Term Care
> Facility Dementia Training [Repealed]

**Successor not located in this pass.** Title 7 Chapter 1 and Title 8 were both
checked and neither carries a replacement home health part.

> **A hypothesis, labelled as such and not verified:** New Mexico stood up its
> **Health Care Authority on 1 July 2024** — the same date — and this looks like
> a machinery-of-government transfer rather than deregulation. **It is a date
> coincidence and nothing more until someone reads the transferring instrument.**
>
> **What is established regardless: any pre-July-2024 New Mexico material in this
> corpus is stale**, and NM currently has a home health chapter with no operative
> part.

---

## 4. North Dakota — the corpus had the wrong chapter

Round 26 worked from **NDCC 23-17.5**, found "repealed cooperative agreements",
and recorded that. **The home health chapter is 23-17.3, "Home Health Agency
Licensure"**, and it is live. *(23-17.4 is Hospice Programs — also fetched this
round, by the same mis-hit, and kept as a labelled example.)*

**This is the third wrong-citation incident in the survey** after North Dakota
itself (round 20) and South Dakota's eleven endpoint forms tested against the
wrong chapter (round 25).

On the axis: **one worker class in statute.** "Home health aide" is defined as
"an individual who renders **personal related service under the supervision of a
registered professional nurse**" — no training standard, no hours, no registry;
**§ 23-17.3-08 delegates all of it to rules.** "Supportive services" is defined
to include **homemaker or companion services**, but as a *service category inside
the licensed agency*, not as a separate worker class with its own regime.

**Certificate of need was repealed in 1995** (§ 23-17.3-03), which is worth
noting against Alabama, where CON is the *entire* entry gate.

**Not established:** NDAC (the administrative rules) were not read, and that is
where any competency requirement would sit. **Route open, unread.**

---

## 5. South Carolina — a separate Act for the non-medical tier, and it may never have commenced

South Carolina was in round 29's **group B** — only "home health aide" named.
It has a **whole separate licensure statute** for the non-medical tier:
**S.C. Code ch. 44-70, the "Licensure of In-Home Care Providers Act" (2011)**.

**The discriminator is written into the definition.** "In-home care" is care
*"primarily intended to assist an individual with an activity of daily living or
in meeting a **personal rather than a medical need**, but not including skilled
care"*, and *"personal in nature but **not mandating continuing attention or
supervision from trained and licensed medical personnel**."*

**The exclusions are the product-relevant part** (§ 44-70-20(3)):

- **(d) "an individual hired directly by the person receiving care or hired by
  his family"** — the direct-hire carve-out, stated plainly;
- (a) an already-licensed home health agency or hospice;
- (b) an entity providing **only** house cleaning;
- (c) direct care entities/caregivers under § 44-7-2910 and services under
  § 44-21-60;
- (e) a church or 501(c)(3) providing in-home care **without compensation or for
  a nominal fee covering incidental expenses**.

**And the definition of "in-home care provider" reaches referral businesses:**
one that "makes provision for in-home care services … **through referral of other
persons** … **when the individual making the referral has a financial interest in
the delivery of those services**." *That is a marketplace trigger and belongs in
front of the SAIRNsenior marketplace-model decision gate.*

**§ 44-70-40** tells the department to promulgate regulations covering, among
other things, **"criteria that a licensee's employee, agent, independent
contractor, or referral must satisfy before providing in-home care service …
including … completion of a minimum education requirement, completion of minimum
training and continuing education requirements, and screening for communicable
diseases."** § 44-70-60 adds a **criminal record check and a drug test** for both
the provider and each in-home caregiver.

> **But the licensure requirement is dormant until those rules exist.** The 2011
> Act's own effective-date clause:
>
> *"This act takes effect upon approval by the Governor, **except the licensure
> requirements of Section 44-70-30 … become effective upon the effective date of
> regulations promulgated** by the Department … pursuant to Section 44-70-40."*
>
> **Whether those regulations were ever promulgated is NOT ESTABLISHED in this
> pass.** This is the exact inverse of Idaho (round 28), which has a live mandate
> whose standards are missing from the code; **South Carolina may have a mandate
> that has never commenced because the standards were never written.** Both shapes
> produce the same practical result — no published worker standard — from opposite
> causes, and only one of them is a gap in the law.

**A citation warning for the whole corpus.** The file at
`dph.sc.gov/…/R.61-77.pdf` contains **"Regulation 60-77, Standards for Licensing
Home Health Agencies"** — filename and content disagree. **South Carolina
renumbered its health regulations from Chapter 61 to Chapter 60**; the current
Chapter 61 is *Department of Environmental Services*, and the health department
itself split into DPH in 2024 (the old `scdhec.gov` host now fails TLS
validation). **Any earlier SAIRNsenior citation of the form "S.C. Reg. 61-⟨n⟩"
for a health rule should be re-checked against Chapter 60.**

---

## 6. Where the twelve candidates stand

| State | Group | Status after this round |
|---|---|---|
| **Minnesota** | A | **READ** — licence-tier model, worker class abolished |
| **New Mexico** | A | **READ** — chapter repealed 2024-07-01; successor not located |
| **North Dakota** | A | **STATUTE READ; citation corrected to 23-17.3**; NDAC unread |
| **South Carolina** | B | **STATUTE READ** — separate Act, possibly never commenced; reg not located |
| Maryland | A | **PARTLY READ** (round 29) — .12 waiver form and delegation rules still unread |
| Montana, New Hampshire, New Jersey, Vermont, Wyoming | A | **NOT READ** — routes probed and open (NH's He-P 800 is a single 22 MB HTML) |
| Kentucky, Maine | B | **NOT READ** — 902 KAR 20:081 and Maine's ch. 118 routes not yet resolved |

## 7. Method notes

- **The absence list is now three for three.** North Carolina and Maryland
  (round 29), then Minnesota, New Mexico, North Dakota and South Carolina — every
  candidate pulled from it had something the write-ups did not record. **Round 29
  called it a candidate generator; it has behaved like a finding.**
- **Fix the manifest before committing it.** Two of twelve entries were
  mislabelled within an hour of the directory existing — a hospice chapter filed
  as home health, and a home health regulation filed under the in-home-care name
  its *filename* claimed. **An index that lies is the failure mode this whole
  session has been documenting; building one and not checking it would have been
  the joke.**
- **A repeal date and a reorganisation date that match are a hypothesis, not a
  finding.** New Mexico's is written as one.
- **"Effective upon promulgation of regulations" is a distinct legal state** and
  needs its own value. A statute can be on the books, mandatory in wording, and
  not in force. Neither "licensed" nor "unlicensed" describes South Carolina's
  in-home care tier until someone finds the regulation or confirms its absence.
