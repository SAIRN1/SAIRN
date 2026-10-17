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
- ~~**Ohio conformity to §224.**~~ **ANSWERED 2026-09-23 — see §10.** The
  question was mis-framed: §224 never touches the number Ohio starts from, so
  there is nothing for Ohio to conform to.
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
- ~~**Whether a members-only canteen meets the "customary" tipping test** of
  §45B(b)(2).~~ **RESEARCHED 2026-09-23 — see §10.** Still not settled, and
  §10 says why: the statute supplies no test, and a SECOND hurdle in the same
  sentence — "customers or clients" — cuts against this document's own
  exempt-function position.
- ~~**Ohio conformity.**~~ **ANSWERED 2026-09-23 — see §10.**

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

---

## 10. The last two register items — answered 2026-09-23 (Cody)

**Both were in §7's unverified list. One is answered outright; the other is
researched to the point where the remaining question changes shape — and the
larger finding is that §7's list was carrying TWO DIFFERENT TESTS under one
word.**

### 10.0 Sources — primary, retrieved this session

| Source | Retrieved from | What it settles |
|---|---|---|
| **26 U.S.C. §45B(b)(2)** | `law.cornell.edu/uscode/text/26/45B` | the credit's own "customary" wording, quoted below |
| **26 U.S.C. §224(d)(1)** | `law.cornell.edu/uscode/text/26/224` | "qualified tips", and the occupation-list mandate |
| **26 U.S.C. §63(b)(5)** | `law.cornell.edu/uscode/text/26/63` | where §224's deduction sits relative to AGI |
| **ORC 5747.01(A)** | `codes.ohio.gov/ohio-revised-code/section-5747.01` | what Ohio's tax starts from |
| **Final regulations, occupations that customarily and regularly received tips** | Federal Register `2026-07104`, issued **10 Apr 2026**; IRB **2026-18**, 27 Apr 2026 | the §224 test is occupation-keyed, and the list |

**NOT HASHED, AND §8 IS WHY.** §0 sets a bar of "retrieved AND hashed, with
byte counts". Five of these are statute and regulation text with no PDF to
hash; hashing the publisher's HTML rendering would pin *their page on the day I
fetched it*, which is a weaker claim than the citation and reads as a stronger
one. That is the shape §8 already proposed and did not apply. Stated here rather
than quietly skipped.

### 10.1 THE FINDING: "customary" is two different tests, and the register had them as one

§7's list read *"whether a members-only canteen meets the 'customary' tipping
test of §45B(b)(2)"*, and §5's read *"Ohio conformity to §224"*. They sit under
one word and they are not the same question:

| | **§45B(b)(2)** — the FICA tip credit | **§224(d)(1)** — the qualified-tips deduction |
|---|---|---|
| The words | *"if the tipping of employees delivering or serving food or beverages by customers **is customary**"* | *"cash tips received by an individual in an **occupation which customarily and regularly received tips** on or before December 31, 2024"* |
| What is tested | the **service**, at this establishment, as a fact | the **worker's occupation**, nationally |
| Who decides | undefined in the statute — facts and a professional | **Treasury, by published list** |
| Settled? | **no** | **yes, and it is checkable** |

**Conflating them would produce the wrong answer in both directions**: a post
that decided its canteen fails "customary" could wrongly conclude its
bartender's tips are not §224 qualified tips, and a post that read the Treasury
list as settling §45B would claim a credit on a test nobody applied.

### 10.2 §224 — the occupation test is settled, and "bartender" is on the list

§224(d)(1) directed Treasury to publish the list. It has: **final regulations,
Federal Register 2026-07104, issued 10 April 2026**, listing **more than
seventy** occupations, each with a three-digit **Treasury Tipped Occupation Code
(TTOC)**, an occupation title, a description, illustrative examples and related
SOC codes. **Bartender is among them.**

**THE TEST KEYS TO THE WORKER'S OCCUPATION, NOT THE ESTABLISHMENT'S TYPE** —
*"To be a qualified tip, the tip must be received by a worker in an occupation
on the List of Occupations that Receive Tips."* Nothing in that formulation asks
whether the bar is members-only.

**WHAT THIS DOES NOT DO, and it is the important half:** §224 is a deduction on
the **individual's** return. It changes nothing about §1 of this document. A tip
is still compensation, it still destroys the volunteer-labour exclusion for the
person who received it, and the post's obligation to record and report it is
unchanged. §224 is about what the bartender may deduct, not about what the post
may treat as volunteer labour.

### 10.3 Ohio — the question was mis-framed, and the answer is structural

**§224's deduction never reaches Ohio's tax base, so there is nothing to conform
to.** Two steps, both from primary text:

1. **§63(b)(5)** lists *"the deduction provided in section 224"* among the
   deductions subtracted **from adjusted gross income** for an individual who
   does not itemise. It is therefore **below the line: it does not reduce
   federal AGI.**
2. **ORC 5747.01(A):** *"'Adjusted gross income' or 'Ohio adjusted gross income'
   means **federal adjusted gross income**, as defined and used in the Internal
   Revenue Code, adjusted as provided in this section."*

Ohio starts from a number §224 does not move. So the answer is not "Ohio has not
conformed" — it is that **conformity is not the operative question**, and a
conformity update could not change the result on its own. Ohio would have to
enact its own tips deduction as a 5747.01 adjustment.

**WHAT I DID NOT DO, so the answer is not read wider than the work:** I did not
enumerate every division of ORC 5747.01's adjustments to confirm none of them
adds a tips deduction, and I did not read Am. Sub. S.B. 9 (signed 5 Mar 2026,
Ohio's conformity update for TY2025) line by line. The chain above shows the
federal deduction cannot arrive in Ohio's base **by conformity**; it does not
prove Ohio has not legislated one separately. That is a narrower check and it is
the one worth running before anyone relies on this.

### 10.4 §45B(b)(2) — still not settled, and there is a SECOND hurdle in the same sentence

The statute, verbatim:

> *"In applying paragraph (1) there shall be taken into account only tips
> received from **customers or clients** in connection with the following
> services: (A) The providing, delivering, or serving of food or beverages for
> consumption, if the tipping of employees delivering or serving food or
> beverages by customers is customary."*

**The register named one hurdle. There are two, and the unnamed one is sharper.**

- **"is customary"** — undefined in the statute, and no regulation supplies a
  test. It is a fact about the establishment. **Still not settled, and this
  document cannot settle it.**
- **"customers or clients"** — a member buying a drink in their own post's
  canteen. **This interacts badly with §7.3.** §7 concluded the credit is
  reachable only against UBIT, and the position that keeps a members-only
  canteen OUT of UBIT is that member sales are exempt-function rather than a
  trade or business serving customers. **Arguing members are "customers" for
  §45B argues against the ground the canteen stands on.** That is not a research
  gap; it is a reason the question may be self-defeating, and it belongs with
  §9's counsel question rather than in a research list.

**SO THE RECOMMENDATION IS UNCHANGED AND NOW BETTER SUPPORTED:** §7.3's order of
operations stands — settle the volunteer-labour exclusion first, then ask about
§45B, never the reverse. A post that has to argue its members are customers to
reach the credit has answered the first question the wrong way to win the
second.

**NOT TAX ADVICE.** Statutory structure, so a professional can be asked a narrow
question instead of an open one.

---

## 11. THE WORD "TIP" IS IN AN OHIO CRIMINAL STATUTE THIS APP ALREADY ENFORCES — and nothing above says so (2026-09-26, Cody)

**§45B was closed on 2026-09-23 (§7) and the register items on the same day
(§10). This section adds nothing to that and does not reopen it.** It records a
SECOND legal rule that the word "tip" triggers, which every section above
misses, and which the app has been enforcing in code for weeks.

**Sections 1-10 analyse a tip as compensation under ONE body of law** — federal
§513(a)(1), where compensation destroys the volunteer-labour exclusion and puts
canteen income into UBIT. That analysis is right and is not disturbed here.

**`sairnfreedom.html` enforces a DIFFERENT rule, on the same word.** ORC
**2915.09(D)(1)**, quoted verbatim at `:3623`:

> *"No commission, wage, salary, reward, **tip**, donation, gratuity or other
> form of compensation may be paid to a bingo game operator."*

`operatorEligibility()` refuses an operator who is compensated, and the app
already chases the interaction from both directions: it matches the **canteen
payroll roster by name** (`:3632` — the comment above it says *"(D)(1)
INTERACTS WITH CANTEEN STAFFING, and Phase 2 closed this loop"*), and since
2026-09-23 it also matches **gaming-account payees by name** as the direct
route.

### 11.1 Why this is not a duplicate of §1

Different statute, different population, different consequence, different
remedy:

| | §513(a)(1) / Pub. 3386 (§1 above) | ORC 2915.09(D)(1) (this section) |
|---|---|---|
| who | canteen workers | **bingo game operators** |
| what goes wrong | the volunteer-labour exclusion fails, canteen income becomes UBIT | the operator is **ineligible**; the payment is prohibited outright |
| severity | a tax bill | an Ohio **criminal** gaming provision and the post's gaming licence |
| can you pay the tax and move on | yes | **no** |

**A post can decide the UBIT risk is acceptable. It cannot decide that about
(D)(1).**

### 11.2 The concrete consequence, and it is a blind spot in a SHIPPED gate

Staff records are `{id, name, dob, paid}`, and `paid` comes from a **binary**
picker — *"Paid staff"* vs *"Volunteer, unpaid"* (`:1042`, written at `:3839`).
The (D)(1) canteen match fires only `if(s.paid && ...)`.

**So a canteen worker recorded as "Volunteer, unpaid" who receives TIPS is
invisible to that gate.** They are compensated under §1's own reading — the IRS
page it quotes says *"Compensation may include tips"* — and compensated under
(D)(1), which names tips in the statute. But `paid === false`, `payrollMatch`
stays null, and operator eligibility raises nothing.

**That is not a defect today, because nothing in this app records tips.** It is
a named PRECONDITION: **the day a tip is recorded anywhere in SAIRNfreedom, the
binary `paid` flag stops being sufficient for (D)(1)** and the gate must learn a
third state. Recording that here, where the tipping decision will be read, is
the point — a gate that silently stops covering its case is this platform's
most-recorded failure shape.

### 11.3 What this does NOT do

- **It does not propose building tip fields.** §7.3's warning stands: a field
  that invites a post to chase the credit pushes the decision the wrong way
  round, and §10.4 leaves §45B(b)(2) unsettled with a second hurdle against the
  exempt-function position.
- **It does not change any conclusion above**, or the §9 counsel question.
- **It is not legal advice**, and the (D)(1) reading is the app's own quoted
  statutory text, not a new source retrieval — no ORC text was fetched for this
  section.

---

## 12. §9's COUNSEL QUESTION IS ANSWERED BY AN IRS REVENUE RULING NOBODY HERE HAD FOUND — Rev. Rul. 2003-64 (2026-10-16, Cody)

**§9 escalated one question to outside counsel and filed a row in the index so
it would get asked. It did not need to leave the building.** There is a
published revenue ruling directly on the point, it has been on the IRS site
since 2003, and no section above cites it. **This section closes §9 to the
extent a ruling can close it, and says precisely where it stops.**

**THIS IS NOT A CRITICISM OF §7 OR §9.** Both reasoned correctly from the
statute and both said, in terms, that the statute alone could not settle the
confinement question. The gap is a SEARCH gap: §7.1 and §10.0 list statute,
regulation, DOL and Ohio sources, and **not one published IRS ruling.** A
source table with no ruling line cannot find a ruling.

### 12.1 Source — primary, retrieved 2026-10-16

| Source | Retrieved from | Bytes |
|---|---|---|
| **Rev. Rul. 2003-64**, *Part I, Section 512 — Unrelated Business Taxable Income* | `irs.gov/pub/irs-drop/rr-03-64.pdf` | 38,489 |

**NOT HASHED, AND §10.0's REASON APPLIES IN REVERSE.** This one IS a PDF and
could be hashed. It is not, because the quotations below are long enough to be
checked against any copy of the ruling, and a hash of my download proves only
that I downloaded something. The byte count is given because it is what a
re-retrieval can actually compare.

### 12.2 The ruling, quoted

**ISSUE** — and read it beside §9.1:

> In computing the unrelated business income tax it owes under § 511(a)(2)(A)
> of the Internal Revenue Code, is it proper for a social club described in
> § 501(c)(7) to claim the credit under § 45B for a portion of employer social
> security taxes paid with respect to employee tips received from both members
> and nonmembers?

**FACTS** — a country club with a clubhouse serving food and beverages to
members and their nonmember guests; insubstantial nonmember income treated as
gross income from an unrelated trade or business under §512(a)(3); employees
paid hourly who *"also customarily receive tips from both members and
nonmembers"*; tips reported, employment tax returns filed, social security tax
paid on the reported tips. The club *"calculates the credit based on all tips
received by its employees."*

**ANALYSIS**, the two sentences that matter:

> Section 45B does not prohibit social clubs described in § 501(c)(7) from
> claiming the credit, nor does it limit the credit to social security taxes
> paid in connection with a social club's unrelated trade or business.
> Therefore, A may calculate the § 45B credit on the basis of all tips received
> by its employees, not only the tips received by employees from nonmembers.

**HOLDING:**

> In computing the unrelated business income tax it owes under § 511(a)(2)(A),
> it is proper for a social club described in § 501(c)(7) to claim the credit
> under § 45B for the portion of employer social security taxes paid with
> respect to employee tips received from both members and nonmembers.

### 12.3 What it settles, and it is §9.3 exactly

**§9.3 said:** *"the chain above shows the credit is not structurally barred; it
does not show that a credit generated by an activity OUTSIDE the unrelated
trade or business may reduce the tax on the unrelated trade or business."*

**The ruling's second clause is that showing.** *"Nor does it limit the credit
to social security taxes paid in connection with a social club's unrelated
trade or business"* is a holding about where the credit may be GENERATED
relative to where it is USED — which is the confinement question — and it
resolves it in the taxpayer's favour, on the ground that **§45B contains no
such limitation.** The reasoning is about §45B's own text and nothing in it
turns on §501(c)(7).

**Two more things it settles that were open above:**

- **MEMBER TIPS COUNT.** §7 never asked this and §10 left §45B(b)(2)'s
  *"customers"* wording as a hurdle *"against this document's own
  exempt-function position"*. The ruling computes the credit on **all** tips,
  member and nonmember, and says the §45B(b)(2) test was met *"because the tips
  were received in connection with food and beverage service at A, and tipping
  of employees is customary at A."* **An exempt club's own members are treated
  as "customers" for §45B(b)(2).** §10's second hurdle is answered on these
  facts.
- **THE CREDIT IS CLAIMED ON FORM 990-T**, against the §511 tax, by an
  organisation with no other chapter-1 liability. §7.3's conclusion — *"§45B is
  reachable by a post ONLY to the extent the canteen produces unrelated
  business taxable income"* — is **confirmed by an IRS ruling** rather than
  inferred from §38(c), and the ruling is the reason it is now a statement and
  not a reading.

### 12.4 WHERE IT STOPS, and these are not quibbles

**THREE GAPS, each stated because a ruling read too widely is worse than no
ruling.**

1. **IT IS A §501(c)(7) RULING AND A POST IS USUALLY §501(c)(19).** The credit
   reasoning does not depend on which subsection, but the **UBTI computation
   does**: §512(a)(3) — the member-income / exempt-function-income machinery
   the ruling's facts run through — applies to §501(c)(7), (c)(9) and (c)(17),
   **not to (c)(19)**, which uses the general §512(a)(1) rules. So the ruling's
   FACTS are not a post's facts even when its HOLDING transfers.
   **AND Pub. 3386 SAYS THIS IS NOT ACADEMIC:** a veterans' organisation whose
   activities are social and recreational — *"such as operating a bar,
   restaurant, canteen or casino for members"* — **may be recognised as exempt
   under IRC 501(c)(7)**, and such clubs *"are often operated in conjunction
   with IRC 501(c)(4) veterans' organizations."* **So which subsection the
   canteen actually sits under is a FACT ABOUT THE POST, and it changes which
   authority is on all fours.** A build must not assume (c)(19).
2. **THE RULING'S FACTS HAVE ONE ACTIVITY, §9.1 HAS TWO.** In the ruling the
   UBI and the exempt-function tips come from the **same dining facility**
   serving two classes of customer. §9.1 posits a canteen producing **no** UBTI
   and UBTI from a **different** activity. The holding's rationale is
   activity-agnostic — it rests on an absence in §45B — but the ruling does not
   present that pattern. **§9 narrows from "unanswered" to "answered in
   principle, not on all fours", and that is the honest state.**
3. **PUB. 3386 DOES NOT ADDRESS §45B, AND THAT IS A MEASUREMENT WITH A STATED
   LIMIT.** A keyword pass over a text extraction of Pub. 3386 (Rev. 4-2018,
   Catalog 27489D) found **0** occurrences of `45B`, `8846` and
   `social security`, against 73 of `501(c)(19)`, 52 of `unrelated` and 5 of
   `canteen`. **THE ZEROS ARE NOT PROOF OF ABSENCE** — the extraction recovers
   the publication's prose but not its embedded font streams, and a truncated
   read is indistinguishable from a complete one. What the pass DOES establish
   positively is the prose it recovered, quoted next.

### 12.5 Pub. 3386, on the two things it does say about this

**TIP RECORDS ARE PART OF THE RECORDKEEPING DUTY**, which is §2's point with the
sentence it rests on:

> If applicable, it also must maintain records to determine if there is tip
> income, employment tax owed and income subject to wagering and other excise
> taxes. Records should be maintained to show income from veteran members and
> from…

**AND THE PUBLICATION'S REFERENCE LIST SENDS A POST TO PUB. 531, NOT TO §45B:**
*"Publication 531, Reporting Tip Income"* sits in its list between Pub. 526 and
Pub. 535. **The guide routes the tip question to the EMPLOYEE-side reporting
publication and never to the employer credit.** On its own that is weak
evidence; beside the three zeros above it is consistent, and it is why the
limit in 12.4 is stated rather than hidden.

### 12.6 THE IRS's OWN LIVE GUIDANCE PAGE CONTRADICTS §45B(b)(1), and §7.4 is the one that is right

**§7.4 says the floor is frozen at the minimum wage *"as in effect on January 1,
2007"*, $5.15/hour. That is the statute**, and Rev. Rul. 2003-64 quotes
§45B(b)(1)(B) in its **pre-freeze form** — *"at the minimum wage rate applicable
to such individual under § 6(a)(1) of the Fair Labor Standards Act of 1938"*,
with no date — which is itself useful: it dates the freeze to after 2003 rather
than leaving §7.4's quotation unplaceable. Confirmed independently this session,
including by the IRS's own 2007 news release **IR-2007-155**, which states that
employers use the **$5.15** rate even after the federal minimum rose.

**AND THE IRS PAGE A BUILDER OR A CPA WOULD ACTUALLY READ SAYS SOMETHING
DIFFERENT.** `irs.gov/businesses/small-businesses-self-employed/fica-tip-credit-for-employers`,
**Page Last Reviewed or Updated: 16-Aug-2026**, verbatim:

> You can't claim the credit for taxes on any tips used to meet a minimum wage
> of $7.25 per hour, the federal minimum wage rate in effect on July 24, 2009.

> The minimum wage basis for the FICA Tip Credit is $7.25 per hour.

**THE DIRECTION OF THE ERROR MATTERS: $7.25 makes the subtraction LARGER and the
credit SMALLER.** A post following that page would **understate** its credit. It
is not a trap that costs a penalty; it is one that costs money quietly, which is
the harder kind to notice.

### 12.6a DECIDED 2026-10-16 BY MICHAEL: THE FLOOR IS $5.15, AND THE IRS PAGE IS RECORDED AS THE ERROR

**§12.6 was written as a question. It is answered, and by the person whose call
it is.**

> **THE FIGURE THIS PLATFORM USES IS $5.15/hour**, the FLSA minimum wage as in
> effect on **January 1, 2007**, per **§45B(b)(1)(B)** and **IR-2007-155**.
> **The IRS FICA Tip Credit page's "$7.25 per hour / July 24, 2009" is
> recorded as THAT PAGE'S ERROR and is not followed.**

> **AND AS OF 2026-10-17 IT IS NOT A CONSTANT IN THE CODE EITHER.** §12.6b
> found a **second** §45B floor; §13 is the implementation. `SEC45B_LIMBS` in
> `sairnfreedom.html` carries **both** floors with the Form 8846 sentence each
> one comes from, and the canteen's limb is **named** (`food_bev`) rather than
> assumed — so the $5.15 decision is recorded as *"this limb's floor"* and not
> as *"the floor"*.

**WHAT CHANGED AND WHAT DID NOT.** §12.6 as first written declined to call the
page wrong, on the ground that *"a Treasury position in guidance is not
something this platform overrules from a statute reading."* **That caution was
right as a research posture and it is not the same thing as a decision.**
Michael has made the decision; the research is unchanged and still says what
it said. **The old paragraph is carried below rather than overwritten**, because
the reasoning for the caution is the reason the decision is safe to make — the
disagreement was documented with both sides quoted and dated before anybody
chose between them.

**THE RESIDUAL RISK, STATED PLAINLY RATHER THAN BURIED IN THE DECISION.**
$5.15 produces a **LARGER** credit than $7.25. Following the statute against a
live IRS web page is the position with more exposure if the page turns out to
reflect an amendment neither this document nor its searches found. **Three
things reduce that, and they are the whole basis:**

1. **§45B(b)(1)(B)'s date is in the statute**, not inferred — and Rev. Rul.
   2003-64 quotes the subsection in its **pre-freeze** form, with no date at
   all, which independently places the freeze after 2003 rather than leaving
   the quotation unplaceable.
2. **IR-2007-155 is the IRS's own release** and says employers use **$5.15**
   even after the federal minimum rose. So the conflict is not
   statute-versus-IRS; it is **IRS-page-versus-IRS-release**, and the release
   is the one that agrees with the statute.
3. **The page's figure is internally anomalous**: it names *"the federal
   minimum wage rate in effect on July 24, 2009"* — a real date for the $7.25
   rate, but **not the date §45B names**. That reads as a page describing the
   CURRENT federal minimum rather than the statute's frozen reference.

### 12.6b FORM 8846 SETTLES IT, AND THE IRS PAGE'S ERROR IS NOT THE ONE I NAMED

**§12.6a listed one cheap check still outstanding — read Form 8846's own wage
line — and said it would be decisive either way. IT WAS RUN, and the answer is
better than "the page is wrong": THE PAGE APPLIES A REAL NUMBER TO THE WRONG
LIMB.**

`irs.gov/pub/irs-pdf/f8846.pdf`, **Form 8846 (2025)**, 71,290 bytes, verbatim —
**two paragraphs, two different floors:**

> **Food or beverage employers.** These employers cannot claim the credit for
> taxes on any tips that are used to meet the federal minimum wage rate **in
> effect on January 1, 2007, of $5.15 an hour.**

> **Beauty service employers.** These employers cannot claim the credit for
> taxes on any tips that are used to meet the federal minimum wage rate
> **currently in effect, of $7.25 an hour.**

**SO §45B HAS TWO FLOORS, ONE PER LIMB OF §45B(b)(2), AND NOTHING ABOVE KNEW
THAT.** §7.4 recorded the freeze and §12.6 recorded the conflict; **neither
noticed that the 2025 expansion to barbering, nail care, esthetics and body and
spa treatments brought its own, UNFROZEN floor with it.** The food-and-beverage
limb is frozen at $5.15; the beauty limb tracks the current federal minimum,
$7.25 today.

**THE IRS PAGE'S $7.25 IS THEREFORE A REAL §45B FIGURE STATED WITHOUT ITS
LIMB.** Its sentence — *"the federal minimum wage rate in effect on July 24,
2009"* — even mislabels it: Form 8846 calls the $7.25 floor *"currently in
effect"*, not fixed to a 2009 date, and $7.25 is the beauty-service number
rather than a date-frozen one. **The page collapses two floors into one and
attaches the wrong one to a date.** That is a more specific and more useful
finding than "the page contradicts the statute", and it is also why the
collapse is easy to make.

**MICHAEL'S DECISION IS CONFIRMED BY AN EMPLOYER-FACING IRS FORM, not only by
the statute.** A post canteen is a **food or beverage** employer, so its floor
is **$5.15**, and Form 8846's own instruction text says so in the same words
§45B(b)(1)(B) uses. **The residual risk §12.6a described is gone**: this is no
longer the platform preferring a statute reading over live IRS guidance, it is
the platform following the form the credit is claimed on.

**AND THE ONE PLACE THIS COULD STILL BITE, named because it is the shape that
recurs:** if SAIRNfreedom ever computes a §45B figure, **the floor is a function
of WHICH LIMB the tipped service falls in, not a constant.** A single hardcoded
`5.15` is correct for a canteen and silently wrong for any beauty-service
employer — and this platform has fifteen other apps. **Nothing computes a §45B
figure today** and §7.3's warning against building toward the credit is
unchanged; this is a precondition recorded where the number will be read.

**CLOSED 2026-10-17 — IT IS NO LONGER ONLY A WARNING.** `SEC45B_LIMBS` in
`sairnfreedom.html` holds **both** limbs, each with its own `floor`, its own
`floorBasis` quoting the Form 8846 sentence it came from, and a `frozen`
boolean that distinguishes *"in effect on January 1, 2007"* from *"currently in
effect"*. `taxEntityFacts()` returns `limb: 'food_bev'` and `floor: 5.15`
**together**, so the figure cannot be read without the limb that licenses it.
See §13.

**WHAT IS STILL NOT CHECKED:** Form 8846's *instructions* document (as distinct
from the form's own instruction text quoted above) returned **HTTP 404** at
`irs.gov/instructions/i8846` this session, so it was not read. The form text is
the stronger source for this question and the 404 is recorded rather than
quietly skipped.

**STILL NOT TAX ADVICE, and the decision does not make it so.** It is an
operating convention for what this platform's own documents and any future
calculation will use, with the conflict disclosed. A post's return is its
CPA's.

---

*The paragraph §12.6 originally closed with, carried unchanged:*

> **WHAT THIS IS AND IS NOT.** It is a documented disagreement between a live
> IRS web page and the statute, with both quoted and both dated. **It is NOT a
> determination that the page is wrong** — a Treasury position in guidance is
> not something this platform overrules from a statute reading, and there may
> be an amendment I have not found. **It is a NARROW QUESTION FOR THE SAME
> PROFESSIONAL §9 was already going to:** *"§45B(b)(1)(B) says January 1, 2007
> and the IRS's FICA Tip Credit page says July 24, 2009 — which figure do we
> use?"* That is a one-line question with two citations attached, which is the
> shape §9 said it wanted.

### 12.7 TD 10044 does not touch any of this, said once more because the pairing keeps recurring

**The question arrived this session paired as "Pub. 3386 + TD 10044 → does §45B
apply".** §10 already establishes that **TD 10044 implements §224**, the
individual's deduction, and that its occupation list is **occupation-keyed and
establishment-agnostic**. It is re-stated here because the pairing is the
natural one to make and it is wrong in a specific way: **nothing on the Treasury
Tipped Occupation Code list makes an employer eligible for §45B, and nothing
off it makes an employer ineligible.** The two provisions share the word "tips"
and nothing else. §45B's own test is the service and the establishment; §224's
is the worker's occupation.

**One datum added to §10's account of the list**, since the final rule has
published since: the final regulations **add three occupations** that were not
on the proposed list — Visual Artists (509), Floral Designers (510) and Gas Pump
Attendant (810) — **and remove none.** Nothing in that changes §45B.

### 12.8 What this changes in the build — nothing, and that is the finding

**No build rule in §4 moves, and §7.3's warning stands unchanged:** a field that
invites a post to chase the credit pushes the decision the wrong way round,
because reaching §45B requires the post to first be in the UBIT state it is
trying to stay out of. **Rev. Rul. 2003-64 makes the credit MORE clearly
available and does not make it more desirable.**

**What does change:** the `docs/SAIRN-OPEN-WORK-INDEX.md` row filed by §9 should
be re-worded from *"needs outside counsel"* to **"answered in principle by Rev.
Rul. 2003-64."* **ROUTED AND NOT TAKEN WHEN THIS SECTION WAS WRITTEN**, because
re-wording somebody else's open-work row to carry my own answer is the edit
this platform has least tolerance for — **and then DONE 2026-10-16 on Michael's
instruction**, since the finding is mine. The old headline, status, owner and
next action are all **struck through and kept inside the row** rather than
deleted, which is that file's own convention for a resolved row.

**AND THE SECOND OF THE TWO RESIDUALS IS GONE.** §12.8 first said *"two narrow
questions go to the post's CPA"*. Michael decided the wage figure (§12.6a) and
Form 8846 then confirmed it (§12.6b), so **one** residual remains: whether the
canteen is held under (c)(19) or a companion (c)(7).

**ANSWER TO THE QUESTION AS ASKED, in one paragraph, because the sections above
are long.** **Yes — §45B applies to tip income reported by VFW/Legion canteen
staff, and member tips count**, on the authority of Rev. Rul. 2003-64 and the
face of §45B(b)(2): the tips are received in connection with serving food or
beverages, and an exempt club's members are "customers" for that test. **But
the credit is nonrefundable and the post must first owe tax it can offset** —
in practice §511 UBIT on Form 990-T — so a post with no UBTI gets nothing now
and only a §39 carryforward (1 back, 20 forward). **TD 10044 is irrelevant to
the employer credit; it governs the employee's §224 deduction.** **Pub. 3386
does not address §45B at all** and routes the tip question to Pub. 531. **The
floor for a canteen is $5.15** — the food-and-beverage limb's frozen
January 1, 2007 rate, decided by Michael and confirmed on the face of Form
8846, which carries **a second, UNFROZEN $7.25 floor for the beauty-service
limb** and is why the IRS web page's $7.25 is a real figure attached to the
wrong limb (§12.6a, §12.6b). **ONE narrow question goes to the post's CPA:**
whether the canteen is held under §501(c)(19) or a companion §501(c)(7).

**NOT TAX ADVICE.** Internal research on statutory structure and one published
ruling, written so a professional can be asked a narrow question instead of an
open one.

---

## 13. THE ENTITY STRUCTURE IS CONFIGURATION NOW, NOT AN ASSUMPTION — and `both` is a real shape this document could not represent (2026-10-17, Cody)

**§12.4 gap (a) said the (c)(19)-versus-(c)(7) question is "A FACT ABOUT THE
POST" and routed it to the CPA. It was still being ASSUMED everywhere else in
this document and in the app.** Every section above reasons as though a post is
a single §501(c)(19); the ruling that answers §9 is a §501(c)(7) ruling; and
Pub. 3386 says plainly that the canteen may sit in either, or in a companion
club beside the post. **A question routed to a professional still has to be
REPRESENTABLE in the system that will carry the answer back.** It was not.

### 13.1 The three shapes, and why `both` is the one that mattered

`TAX_ENTITIES` in `sairnfreedom.html`:

| id | structure | UBTI rule | Rev. Rul. 2003-64 |
|---|---|---|---|
| `c19` | the post itself holds the canteen under **§501(c)(19)** | **§512(a)(1)** | **answered in principle, NOT on all fours** — the holding transfers because §45B contains no entity limitation; the ruling's FACTS run through §512(a)(3), which does not apply to a (c)(19) |
| `c7` | a separate **§501(c)(7)** companion club holds it | **§512(a)(3)** | **ON ALL FOURS** |
| `both` | a §501(c)(19) post **AND** a §501(c)(7) companion club | **§512(a)(1) and §512(a)(3), one each** | on all fours for the club limb |

**`both` IS NOT A FORMALITY AND IT IS WHY A SINGLE FIELD WAS NOT ENOUGH.** It is
the shape in which *"whose employee received this tip"* **has two possible
answers**, and that answer decides **which return** the employer-side figures
land on. Pub. 3386's own sentence — such clubs *"are often operated in
conjunction with IRC 501(c)(4) veterans' organizations"* — describes exactly
this co-existence. **A design storing one entity cannot represent it at all**,
and would have silently collapsed two employers into one.

**THE DEFAULT IS `''`, NOT `'c19'`, and that is the load-bearing decision.** An
unset structure reads **UNKNOWN**. A defaulted (c)(19) would be a silent
assumption of precisely the thing this field exists to stop assuming — and the
ORC 2915.09(D)(1) compensation checks, the UBIT exposure and the canteen's
exempt-function basis all branch on it. `taxEntityFacts()` returns
`configured: false` with the reason stated, rather than a plausible answer.

### 13.2 What it reports, and what it refuses to compute

**`taxEntityFacts()` REPORTS; it does not calculate.** It answers which IRC
subsections apply, which UBTI rule governs, whether Rev. Rul. 2003-64 is on all
fours, which §45B limb the canteen falls in and that limb's floor — and it
carries an **`unknowns` list** whose entries are written to be asked verbatim.

**IT DOES NOT COMPUTE A §45B CREDIT, AND NOTHING IN THIS APP DOES.** §7.3 is
explicit that a field inviting a post to chase the credit pushes the decision
the wrong way round, because reaching §45B requires the post to first be in the
UBIT state it is trying to stay out of. **That warning is unchanged and this
change respects it:** what became configurable is the **entity structure** — a
fact the post already knows, that several unrelated questions already need —
not a credit calculator. **Read that as the boundary, not as caution:** the
request was for the calculation to be configurable rather than hardcoded, and
the honest form of that is to make the INPUTS it would need explicit and
limb-aware while declining to produce a number no professional has signed off.

**AND THE FLOOR IS NO LONGER A CONSTANT.** `SEC45B_LIMBS` carries **both** of
§45B(b)(2)'s limbs, each with its own `floor`, its own `floorBasis` quoting the
Form 8846 sentence it came from, and a `frozen` boolean separating *"in effect
on January 1, 2007"* from *"currently in effect"*. `taxEntityFacts()` returns
`limb` and `floor` **together**, so the number cannot be read without the limb
that licenses it. That closes §12.6b's precondition in code rather than leaving
it as a warning.

### 13.3 Driven, all four states, before it was committed

```
taxEntity=""      configured=false floor=5.15 limb=food_bev irc=null                           ubti=null                              onAllFours=undefined unknowns=1
taxEntity="c19"   configured=true  floor=5.15 limb=food_bev irc=["501(c)(19)"]                 ubti="512(a)(1)"                       onAllFours=false     unknowns=1
taxEntity="c7"    configured=true  floor=5.15 limb=food_bev irc=["501(c)(7)"]                  ubti="512(a)(3)"                       onAllFours=true      unknowns=1
taxEntity="both"  configured=true  floor=5.15 limb=food_bev irc=["501(c)(19)","501(c)(7)"]     ubti="512(a)(1) and 512(a)(3), one each" onAllFours=true    unknowns=2
```

Driven against the **real extracted script block** in a `vm` context, not
against a retyped copy. **`both` carries the extra unknown** and the unset case
carries `configured: false` — the two behaviours the shape exists for. Every
script block passed `node --check` before and after.

### 13.4 What is NOT built, said so it is not assumed

* **No §45B calculation.** §13.2.
* **The per-worker employer is NOT recorded.** In the `both` shape the app
  cannot say which entity employs a given tipped worker, and
  `taxEntityFacts().unknowns` says so rather than leaving it to be discovered.
  **That is the next real field if this is ever taken further**, and it is a
  roster change, not a tax change.
* **No §501(c)(4) option.** Pub. 3386 discusses (c)(4) posts and their canteens
  — where canteen income is UBIT-taxable *"whether the income is from members or
  nonmembers"* — but no SAIRNveterans post is recorded as (c)(4) and inventing
  the option would be speculative. **Named here so its absence is a decision.**
* **No change to any ORC check.** The §11 precondition — that the day a tip is
  recorded, the binary `paid` flag stops being sufficient for 2915.09(D)(1) —
  is unchanged and still open.

### 13.5 THE REPORTER WAS DORMANT CODE FOR THE LENGTH OF ONE BATCH, AND THE CHECK THAT CAUGHT IT WAS RUN AGAINST MY OWN CHANGE

**§13.3 above is true and was not sufficient.** `taxEntityFacts()` was driven in
all four states, every arm green — and **it had ZERO CALLERS.** Measured, not
noticed in passing: `grep -n "taxEntityFacts" sairnfreedom.html` returned the
definition, a mention inside its own comment, and nothing else. The select was
wired, the value persisted, and **nothing in the app displayed any consequence
of it.**

**THAT IS GUARDIAN CHECK 0d AGAINST MY OWN WORK, IN THE SAME BATCH THAT WROTE
IT**, and it is the reason the pre-push pass is run on the diff rather than on
somebody else's code. A configurable structure whose effects are invisible is
**the assumption this field exists to remove, one step later**: the post answers
the question, the answer changes nothing it can see, and the next session reads
a field nobody has any evidence is being used.

**RESOLVED BY WIRING, NOT BY QUARANTINE, and the choice was between two real
options.** Deleting `taxEntityFacts()` and `SEC45B_LIMBS` would have made
§12.6b's *"it is no longer only a warning"* false in the same commit that wrote
it. So `sfRenderTaxFacts()` renders it into the Post Profile panel, repainted
by `sfRenderPost()`, and **the unknowns are rendered as prominently as the
determinations** — with the unset state rendering the unknown as the *whole*
output rather than an empty box, because a blank box reads as *"no issue here"*.

**AND THE DRIVER IS NOW A LANDED SUITE:** `tests/sairnfreedom_tax_entity_facts.js`,
**26 arms, exit 0**. §13.3's driver was a scratchpad file, which is precisely the
defect `docs/2026-10-15-fourth-b25-findings.md` section 1 was criticised for and
that `tests/sd_data_not_provisioned_misclass.js` was written to correct: **a
probe outside the tree means nothing notices the subject being fixed OR getting
worse.** It fails CLOSED with **exit 2 COULD NOT RUN** if either extraction
anchor stops matching or stops being unique, and it names which anchor.

**THE ABLATION FOUND A DEFECT IN THE SUITE ITSELF AND IT IS RECORDED RATHER
THAN QUIETLY FIXED.** Five layers removed one at a time on a COPY of the app —
**5 of 5 now caught by a NAMED arm** — but the first run was **4 of 5**, and the
miss is the instructive one. Arm B6 asserted `TWO EMPLOYERS` appeared in the
rendered HTML. Deleting the two-employer **unknown** left B6 **GREEN**, because
`TAX_ENTITIES.both.note` independently contains the words *"TWO EMPLOYERS ARE
POSSIBLE"* and the renderer prints that note too.

**AN ARM SATISFIED BY A DIFFERENT STRING THAN THE ONE IT INTENDS TO CHECK IS
THE SAME DEFECT AS A PRECONDITION SATISFIED BY A COMMENT ABOUT THE CODE IT IS
CHECKING FOR** — which is arm P5 of the not-provisioned suite, found by ablation
in this same batch, one file over. **Twice in one batch, in two files, by the
same mechanism.** B6 now asserts against the `unknowns` list, requires the entry
to reach the rendered unknowns block, and **B6b requires the two single-entity
shapes NOT to carry it**, so a disclosure pushed unconditionally fails as well.

**WHAT THE ABLATION PROVES, PER ARM:** L1 the two-employer disclosure → B6;
L2 the UNSET branch's *not defaulted* sentence → A3; L3 the limb travelling
with the floor → C[c19], C[c7], C[both], D2; L4 the two limbs' floors made
equal → P2, P3; L5 the frozen/unfrozen distinction collapsed → P2, P3.
**Every layer this feature depends on has a named arm that fails when it is
removed**, which is what makes the green run evidence rather than a shape.
