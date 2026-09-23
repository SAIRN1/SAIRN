# SAIRNfreedom §9a.2 — tips received, tax treatment: answered

**2026-09-17 (Fourth).** Closes the last unresearched item in
`docs/superpowers/specs/2026-08-30-sairnfreedom-phased-build-spec.md` §9a.2,
which read: *"Tips received — tax treatment. Already flagged. Reporting
obligations, tip credit, allocation between employees and volunteers. **Do not
build fields until researched.**"*

**The answer is not "here is how to tax a tip." It is that a tip jar in a post
canteen is a TAX-EXEMPTION event, not a payroll detail** — and the deferral
was right for the wrong reason. The spec deferred this as a payroll question.
The sharpest finding is upstream of payroll and lands on UBIT.

**AND THE LAW MOVED WHILE THIS SAT DEFERRED.** §9a.2 was written 2026-08-30.
Final regulations **TD 10044** published **13 April 2026** and the 2026 Form W-2
gained **two new fields that did not exist when the spec was drafted**. Anything
built to the pre-2026 shape would be built wrong. That is the whole argument for
re-reading a deferred research item against source rather than resuming from the
note.

---

## 0. Sources — primary, retrieved and hashed

| Source | Retrieved | Evidence |
|---|---|---|
| IRS **Pub. 3386**, *Tax Guide for Veterans' Organizations* | `irs.gov/pub/irs-pdf/p3386.pdf` | 551,647 bytes, `sha256 3f40efa3ab826bb8…`, 46 pages |
| IRS **2026 General Instructions for Forms W-2 and W-3** | `irs.gov/pub/irs-pdf/iw2w3.pdf` | 527,838 bytes, `sha256 d16b9f506f039f5a…`, 36 pages, Catalog 25979S, dated **Jan 29, 2026** |
| IRS, *Volunteer Labor Exclusion from Unrelated Trade or Business* | `irs.gov/charities-non-profits/volunteer-labor-exclusion-from-unrelated-trade-or-business` | quoted below |

Both PDFs were **downloaded and text-extracted locally**, not read through a
summariser and not taken from a tax-firm alert. Four secondary write-ups (RSM,
BDO, The Tax Adviser, an ERISA practice blog) agreed on the W-2 changes and
**none of them is cited as authority** — the W-2 instructions say it directly,
which is the same discipline the Ohio gate used against rules aggregators.

---

## 1. THE FINDING THAT OUTRANKS EVERYTHING ELSE: a tip is compensation, and compensation destroys the volunteer-labor exclusion

IRC §513(a)(1) excludes from unrelated business income any trade or business in
which **substantially all the work is performed by volunteers without
compensation**. For a post, that exclusion is what keeps a canteen, a dance or a
hall event from being taxable.

**Pub. 3386, verbatim:**

> "**Volunteer Labor:** Any business in which substantially all the work is
> performed by volunteers without compensation. **Compensation may include tips
> and non-cash benefits.** For example, if your members volunteer to sell tickets
> to the general public for your sponsored dances, and substantially all the work
> in organizing and conducting the event is done by volunteers without
> compensation, the activity is not an unrelated trade or business."

**The IRS's volunteer-labor page, verbatim:**

> "'Compensation' is interpreted broadly. It may include payments to bartenders,
> waitresses, snack bar staff, maintenance workers, security, and other workers,
> **as well as the tips that any workers receive.**"

> "**Tips received by workers in lieu of salary were compensation** for purposes
> of Section 513(a)(1)." *(Executive Network Club)*

> "There must be a **'but-for' connection** between payment and services in order
> for the payment to be considered 'compensation.'"

**So a canteen staffed by tipped volunteers is not staffed by uncompensated
volunteers, and the exclusion that made its income non-taxable is in question.**
The workers named in the IRS's own sentence — bartenders, snack bar staff — are
exactly the roles a post canteen runs on.

**"Substantially all" has NO percentage test.** The IRS page says so directly:
*"The term 'substantially all' is not defined in section 513 or regulations for
purposes of this exception"* and *"the existing court cases do not apply a set
percentage test."* **The app must therefore never compute or display a
pass/fail percentage** — an 85%-style figure would be a fabricated threshold
presented as a rule, which is the fabricated-KPI shape Guardian check 0b exists
for.

---

## 2. Pub. 3386 makes tip records MANDATORY — which reverses "do not build fields"

> "If applicable, it also must maintain records to determine **if there is tip
> income, employment tax owed** and income subject to wagering and other excise
> taxes. Records should be maintained to show income from veteran members and
> from nonmembers by activity or income source."

> "**If records are not maintained to indicate income from members and
> nonmembers, or if records are inadequate, all income may be subject to UBIT,
> and tax exemption may be jeopardized.**"

The spec's instruction was *"do not build fields until researched."* It is now
researched, and the answer is that **the fields are required** — a post that
takes tips and cannot produce per-worker tip records is in the failure Pub. 3386
describes, where inadequate records put *all* income into UBIT.

---

## 3. What changed in 2026, and why a pre-2026 build would be wrong

From the **2026 Instructions for Forms W-2 and W-3**, verbatim:

> "New box 12, code TP, will be used to report the total amount of cash tips
> reported to the employer."

> "Box 14 has been split into box 14a and box 14b. Information that was reported
> in box 14—Other will now be reported in box 14a—Other. **Box 14b was created to
> report the Treasury Tipped Occupation Code(s).**"

> "Employers must file Forms W-2 with the SSA and furnish statements to tip
> recipients showing cash tips received **and the Treasury Tipped Occupation
> Code(s)** of the tip recipient."

> "**Deduction for qualified tips.** For tax years beginning after 2024 and
> ending before 2029, P.L. 119-21 allows certain employees and self-employed
> individuals to deduct up to **$25,000** of qualified tips received in
> occupations that are listed by the IRS as having customarily and regularly
> received tips on or before December 31, 2024… **Mandatory service charges added
> to the bill are not qualified tips.** Tips are generally subject to federal
> income tax withholding and both the employer share and employee share of social
> security tax and Medicare tax **if the tips received are $20 or more per
> month**."

TD 10044 (13 April 2026) finalises the occupation list: **70+ occupations in
eight Treasury Tipped Occupation Code categories, 100 through 800.** Bartender
and server are on it. *(This sentence is the one thing here resting on secondary
sources agreeing — the box numbers and the $25,000/$20 figures above are from
the IRS instructions themselves.)*

---

## 4. The build rules

**R1 — "VOLUNTEER" AND "RECEIVES TIPS" ARE NOT INDEPENDENT CHECKBOXES.**
Setting both is a state with a tax consequence, and the app must say so where it
is entered, not in a help page. This is the same shape as the liquor/bingo
coupling in §9a.3: two modules that look separate and are not.

**R2 — TIP INCOME IS RECORDED PER WORKER PER MONTH, not per year.** The FICA and
withholding trigger is *"$20 or more per month"*, so an annual total cannot
answer the question the law asks. A month bucket is the minimum shape.

**R3 — A VOLUNTARY TIP AND A MANDATORY SERVICE CHARGE ARE DIFFERENT FIELDS.**
A mandatory gratuity on a hall-rental invoice is a **service charge**: it is
wages, not a tip, and it is expressly **not** a qualified tip. Hall rental is an
existing module (§2.5), so this has a concrete home and a concrete way to go
wrong — one "gratuity" column holding both is a wrong answer on every row.

**R4 — STORE THE TREASURY TIPPED OCCUPATION CODE AS A FIELD, never derive it
from a job-title string.** A free-text role of "bar help" is not a TTOC. This is
the same rule the deadline engine follows for jurisdictions and the same reason:
a derived code is a guess wearing an identifier.

**R5 — THE APP REPORTS; IT DOES NOT ADVISE.** Do not compute the §224 deduction.
It is claimed on the worker's own return, the cap is $25,000, there are income
phase-outs the post cannot see, and the window closes for tax years beginning
after 2028. Show what was received and reported; say where it goes. Same
discipline as SAIRNlaw's citation rule — and this app already has the
counterexample on file, where one surface routed everything through a source and
the adjacent one displayed raw model prose about money.

**R6 — THE UBIT WARNING MUST NOT CARRY A PERCENTAGE.** See §1: there is no
percentage test. State the risk and name Pub. 3386; do not invent a bar.

**R7 — THE GAMING COUPLING, which the app is already half-aware of.** Pub. 3386:
*"The definition of bingo does not include the sale of pull-tabs, instant bingo
or similar raffles."* So instant bingo has **neither** the bingo exclusion
**nor**, if its workers are tipped, the volunteer-labor exclusion. The app
already routes instant-bingo money to the 2915.101 percentages rather than
demanding a division (V) purpose tag (CORRECTION 4 from the Ohio research). This
is the **federal** side of that same coupling and belongs beside it.

---

## 5. Unverified — do not build past these

- **Whether a small tip destroys the exclusion.** The IRS page says compensation
  is interpreted broadly and that de minimis amounts are not compensation. **No
  threshold is stated anywhere**, and "substantially all" has no percentage test.
  A post asking "how big a tip is safe" gets no answer from this research and
  must not get an invented one from the app.
- **Member vs nonmember interaction.** Pub. 3386 requires member/nonmember income
  records *and* treats tips as compensation. Whether a member tipping a
  member-volunteer creates a distinct question was not determined.
- **Ohio conformity to §224.** Whether Ohio's income tax follows the federal
  qualified-tips deduction was not researched. Federal-only here.
- ~~**FICA tip credit (§45B).**~~ **ANSWERED 2026-09-23 — see §7 below.** The
  answer is not a number, it is that the credit is only reachable in the state
  this document's headline is about avoiding.
- **Form 8027.** Whether a post canteen is ever a "large food or beverage
  establishment" (the >10-employee test) was not determined.

---

## 6. What this changes in the spec

§9a.2 moves from *"do not build fields until researched"* to **"fields are
required, and here are seven rules for them."** The blocking half is discharged.
The five items in §5 are narrower questions that block specific features, not the
tip record itself.

---

## 7. The FICA tip credit (§45B) — answered 2026-09-23 (Fourth)

**§9a.2 named "tip credit" and §5 left it open. This closes it.** The question
as posed was *"whether a §501(c)(19) post with little or no income tax liability
can use it."* It can, in exactly one circumstance — **and that circumstance is
the one §1 of this document says a post is trying to avoid.**

### 7.1 Sources — primary, retrieved 2026-09-23

Retrieved as TEXT, not as hashed PDFs, and that difference is stated rather than
glossed: §0's sources are hashed files, these are statutory text read from the
US Code. Anyone relying on this should read the section itself.

| Source | Retrieved from |
|---|---|
| **26 U.S.C. §45B** — credit for employer social security taxes paid on tips | `law.cornell.edu/uscode/text/26/45B` |
| **26 U.S.C. §38** — general business credit, components and limitation | `law.cornell.edu/uscode/text/26/38` |
| **26 U.S.C. §39** — carryback and carryforward of unused credit | `law.cornell.edu/uscode/text/26/39` |
| **26 U.S.C. §511** — tax on unrelated business income of exempt organisations | `law.cornell.edu/uscode/text/26/511` |
| **US DOL**, federal minimum wage history | `dol.gov/agencies/whd/minimum-wage/history/chart` |

### 7.2 The chain, and every link is from the statute

1. **§45B(a)** allows a credit equal to the *excess employer social security
   tax* paid on tips.
2. **§38(b)(11)** lists it verbatim — *"the employer social security credit
   determined under section 45B(a)"* — as a component of the **general business
   credit**. That is the decisive fact and it is what the original question was
   circling.
3. **§38(c)(1)** limits the general business credit to *"the excess (if any) of
   the taxpayer's net income tax over the greater of (A) the tentative minimum
   tax … or (B) 25 percent of so much of the taxpayer's net regular tax
   liability as exceeds $25,000."* **No income tax, no credit** — it is
   non-refundable by construction.
4. **§511(a)(1)** imposes tax on unrelated business taxable income *"computed as
   provided in section 11"*, and **§511(a)(2)(A)** applies it to any
   §501(a)-exempt organisation **other than one described in §501(c)(1)**. A
   §501(c)(19) post is squarely inside that.

**So a post's only chapter-1 income tax is UBIT, and §45B is only usable against
it.**

### 7.3 The finding, which is not the arithmetic

**§45B is reachable by a post ONLY to the extent the canteen produces unrelated
business taxable income — the exact thing §1 of this document says a tip jar
puts in question.** A post claiming the credit is, in substance, asserting it
has UBTI to credit against.

That makes the credit a **poor reason to introduce tipping** and a **bad first
question to ask about it**. The order of operations is: settle whether the
canteen's volunteer-labour exclusion survives, then ask about §45B — never the
reverse. Building a "tip credit" field that invites a post to chase the credit
would push the decision the wrong way round.

**The credit is not lost if unusable, merely deferred, and for most posts that
is indistinguishable from nothing.** **§39(a)(1)** carries an unused general
business credit **1 year back and 20 years forward**. A post with no UBTI
carries it for twenty years and then loses it.

### 7.4 Two things that surprised the intuition, both from the text

- **The minimum-wage floor is FROZEN.** §45B(b)(1) computes the excess against
  the minimum wage *"in the case of food or beverage establishments, as in
  effect on January 1, 2007."* **DOL confirms that rate was $5.15/hour** (in
  effect since 1 September 1997; next changed to $5.85 on 24 July 2007). So the
  credit is measured against a floor nearly two decades stale — for a canteen
  paying anything at or near a current wage, **essentially every tipped dollar
  is inside the credit**, which makes the credit larger than it sounds and
  changes nothing about §7.3.
- **The scope is wider than "restaurants".** §45B(b)(2) reaches tips for
  providing, delivering or serving food or beverages **and** certain personal
  services — barbering, nail care, esthetics, body and spa treatments — where
  tipping is customary. A post canteen is inside the food-and-beverage limb on
  its face; the customary-tipping test is factual and is **not** settled here.

### 7.5 Two coordination rules a build must not ignore

- **§45B(c), no double benefit:** *"No deduction shall be allowed under this
  chapter for any amount taken into account in determining the credit."* The
  employer FICA on those tips cannot be both deducted and credited.
- **§45B(d), election out:** the section *"shall not apply to a taxpayer for any
  taxable year if such taxpayer elects to have this section not apply."* The
  credit is elective, so "did the post elect out" is a real field on a real
  return, not a hypothetical.

### 7.6 What is STILL not answered, kept in the §5 register's spirit

- **→ PROMOTED TO §9. NEEDS OUTSIDE COUNSEL.** Whether FICA paid on
  EXEMPT-function tips can generate a credit usable against UBIT arising from a
  different activity. Moved out of this list because a question that must leave
  the building is not the same kind of thing as one nobody has got to yet, and
  burying it in prose is how it stays unasked.
- **Whether a members-only canteen meets the "customary" tipping test** of
  §45B(b)(2). Factual, not researched.
- **Ohio conformity.** Federal only, same as §5.

**NOT TAX ADVICE.** This is internal research on statutory structure, written so
a build decision can be made and so a professional can be asked a narrow
question instead of an open one.

---

## 8. A process question this document created, and it is not about tips

**§0 of this document sets an evidentiary bar — primary sources RETRIEVED AND
HASHED, with byte counts — and §7 could not meet it.** §7's sources are
statutory text read from the US Code; there is no PDF to hash. §7 says so in its
own source table rather than presenting text and hashes as the same currency,
which is the honest local fix. The general question is not local and is raised
here rather than settled.

**THE QUESTION:** is §0's standard meant to apply to every research document on
this platform, retroactively, or to this one and onwards?

**WHY IT IS NOT RHETORICAL.** The bar is a good one and it exists for a real
reason — this document's own headline is that *the law moved while this sat
deferred*, and a hash is what lets a later reader tell a re-read from a
re-assertion. But it is only applicable to sources that ARE files:

- **A PDF can be hashed.** Pub. 3386, the W-2 instructions, a court rules PDF.
  Most of the SAIRNlaw deadline gates already work this way and several
  re-fetched and re-matched their hashes days later, which is the standard
  working exactly as intended.
- **A STATUTE CANNOT, usefully.** US Code text is served as HTML by several
  publishers, none authoritative, all reformatting it. A hash would pin *the
  publisher's rendering on the day I fetched it*, which is a weaker claim than
  the citation itself and reads as a stronger one. Hashing it would be
  ceremony that looks like rigour.
- **A LIVE PAGE IS WORSE.** The IRS volunteer-labour page quoted in §0 has no
  stable byte identity either.

**SO THE STANDARD HAS A SHAPE IT FITS AND A SHAPE IT DOES NOT, and stating the
bar without stating the shape is how a future session either fabricates a hash
to satisfy it or quietly drops the citation.** Both are worse than saying which
kind of source this is.

### 8.1 ANSWERED 2026-09-23 (Fourth) — GOING FORWARD ONLY, with a shape clause

**THE STANDARD IS:** *hash what is a FILE; for anything else, name the
publisher, the retrieval date and the provision, and **say which of the two it
is.*** Adopted for this document, and proposed as the platform convention for
research documents from here on.

**RETROACTIVE APPLICATION IS REJECTED, AND THE REASON IS NOT COST.** The
obvious argument against a sweep is that there are dozens of prior documents.
That argument is true and it is the weaker one. The real one:

> **A HASH COMPUTED TODAY FOR A SOURCE READ THREE WEEKS AGO PINS TODAY'S BYTE
> IDENTITY TO A CLAIM MADE THEN.** It proves nothing about what was actually
> read, and it READS as though it does. Backfilling hashes into old documents
> would manufacture exactly the evidence a hash is supposed to be — and this
> document's own headline is that *the law moved while this sat deferred*, so
> a byte identity captured after the move would be evidence of the wrong day.

**A retroactive hash is worse than no hash.** No hash says "unverified"; a
backfilled one says "verified" and is wrong about when.

**SO WHAT DOES A PRIOR DOCUMENT GET?** Not a backfilled hash. If somebody
revisits one and the sources matter, it gets a **re-read with a fresh retrieval
date** — which is the same discipline §7 applied to §9a.2 and the reason this
document exists at all.

### 8.2 The deference in the paragraph below was reasonable and was WRONG, and that is worth more than the answer

The superseded text read: *"§0 is another session's standard on another
session's document, and rewriting somebody else's evidentiary rule because my
own section could not meet it is the wrong direction to resolve it from.
Michael's call, or the author's."*

**THE PREMISE WAS FALSE. §0 IS THIS CLONE'S OWN STANDARD ON THIS CLONE'S OWN
DOCUMENT** — the header says *2026-09-17 (**Fourth**)* and
`git log --diff-filter=A` on this file returns one commit, `9ffad7a9`. So the
deference was owed to nobody, and it deferred a question the deferring session
was entitled to answer.

**IT COST A WEEK OF THE QUESTION SITTING OPEN, AND THE CHECK WAS ONE COMMAND.**
Recorded here rather than silently corrected, because "another session wrote
this" is an assumption that feels like caution and is cheap to test. **The
retroactive half is still genuinely not mine** — that one reaches dozens of
other sessions' documents, and it is rejected above on its merits rather than
deferred.

---

## 9. NEEDS OUTSIDE COUNSEL — one question, stated so it can be asked

**This is not a research gap. It is a question this platform cannot answer from
primary sources, and it should go to the post's CPA or tax counsel as written.**

> **NOW FILED IN `docs/SAIRN-OPEN-WORK-INDEX.md` AS WELL, 2026-09-23, AND IT WAS
> NOT BEFORE.** §7.6 said moving this out of the research register mattered
> because *"burying it in prose is how it stays unasked"* — and then it was
> left in prose, in §9 of a dated document, with nothing in the index pointing
> at it. **The section that named the failure mode committed it.** A question
> that must leave the building needs a row in the place people look for work,
> not a heading in the place the research lives.

### 9.1 The question

> A §501(c)(19) veterans post operates a canteen. It pays employer FICA under
> §3111 on tips its employees receive. Assume for the question that the canteen
> activity is an EXEMPT function and produces no unrelated business taxable
> income, but that the post has UBTI from a **different** activity and therefore
> a §511 tax liability.
>
> **Can the §45B employer social security credit generated by the FICA paid on
> the exempt-function tips be applied against the §511 tax arising from the
> other activity?**

### 9.2 What is already established, so counsel is not asked to re-derive it

All from the statutory text, retrieved 2026-09-23 — see §7.1:

- §45B(a) allows the credit; **§38(b)(11)** makes it a **general business
  credit** component.
- **§38(c)(1)** limits the general business credit by reference to **net income
  tax**.
- **§511(a)(1)** imposes the UBIT *"computed as provided in section 11"* and
  **§511(a)(2)(A)** applies it to any §501(a)-exempt organisation other than a
  §501(c)(1). A §501(c)(19) post is inside that.
- So the §511 tax and the §38 credit are in the **same chapter**.

### 9.3 What is NOT established, and is exactly what is being asked

**Same chapter is not the same thing as available to offset.** The chain above
shows the credit is not structurally barred; it does **not** show that a credit
generated by an activity OUTSIDE the unrelated trade or business may reduce the
tax on the unrelated trade or business. §512's own computation is confined to
the unrelated activity, and whether that confinement reaches back through §38 is
the question.

### 9.4 Why it matters to the build, in one line

**§7.3's conclusion — that the credit is only reachable in the state the post is
trying to avoid — is CORRECT EITHER WAY**, because both readings require a §511
liability to exist. The answer changes **how much** credit is usable, not
**whether** the post must first have UBTI. **So no build decision is blocked on
this**, and it is filed as a question to ask rather than a blocker to wait on.

**NOT TAX ADVICE.** Written so a professional can be asked a narrow question
instead of an open one.
