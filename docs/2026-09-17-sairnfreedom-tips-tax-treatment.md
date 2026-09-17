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
- **FICA tip credit (§45B).** §9a.2 named "tip credit" and it is **not answered
  here**. §45B is a credit against employer social security tax on tips, and
  whether a §501(c)(19) post with little or no income tax liability can use it is
  a different question from whether tips are taxable. Named so it is not read as
  covered.
- **Form 8027.** Whether a post canteen is ever a "large food or beverage
  establishment" (the >10-employee test) was not determined.

---

## 6. What this changes in the spec

§9a.2 moves from *"do not build fields until researched"* to **"fields are
required, and here are seven rules for them."** The blocking half is discharged.
The five items in §5 are narrower questions that block specific features, not the
tip record itself.
