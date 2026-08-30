# Questions for a CPA or attorney — SAIRN Technologies LLC

**Prepared 2026-08-30 (CC).** Extracted from the research documents so they can
be handed over as-is the moment a professional is engaged, rather than someone
having to mine them out of long research files.

**Each item states the question, why it matters commercially, what has already
been established from primary sources, and what turns on the answer.** The
research behind each is cited so the professional can start from a position
rather than from zero — this is not a request to research from scratch, it is a
request to decide questions we have deliberately not decided ourselves.

**Standing caveat on everything below:** all underlying research is a
primary-source read by a non-professional. Verbatim statutory quotes are
reproduced accurately, but the *characterisation* and *application* are exactly
what is being asked.

---

# A. TAX — for a CPA or state-tax professional

Source: `2026-08-30-sairntech-digital-goods-sales-tax.md`

## A1. What IS the hosted app, for Ohio sales-tax purposes?

**The question.** SAIRN sells access to web applications that run in a browser
against SAIRN's servers. Nothing is downloaded or installed. Is that:

- an **electronic information service** under ORC 5739.01(Y)(1)(c) — taxable
  only *"for use in business"*; or
- a **prewritten software licence**, i.e. tangible personal property under
  5739.01(WW) with 5739.01(B)(1) taxing *"a license to use or consume"* it —
  **taxable to everyone, with no business-use gate**; or
- a **specified digital product** under 5739.01(B)(12)?

**Why it matters, commercially.** This single determination decides **whether
individual (non-business) customers must be charged sales tax at all**. It also
governs how the product is described on the website, on invoices, and in the
terms of sale — the wording and the tax treatment are coupled.

**What is already established.** ORC 5739.01(B)(3)(e) taxes ADP/computer/
electronic information services *"for use in business when the **true object** of
the transaction is the receipt by the consumer of"* those services.
**OAC 5703-9-46(A)(7) defines "business" to include nonprofits**, so a nonprofit
customer does not escape through that gate.

**The Ohio Supreme Court applied the true-object test in *Cincinnati Fed. S. &
L. Co. v. McClain*, 168 Ohio St.3d 123, 2022-Ohio-725** (March 15, 2022):

> "A transaction for computer-related services is taxable only when the
> consumer's true object is to obtain the work performed by computer systems
> rather than to obtain personal and professional services that are coupled with
> the work that is performed by computer systems."

**The facts there were SaaS-shaped, and the Court remanded rather than decide** —
which is precisely why this is on this list and not settled internally.

**What we did not obtain:** Ohio's **SST Taxability Matrix** entry for
*"prewritten computer software accessed remotely."* It is JavaScript-rendered and
could not be retrieved. **That is likely the single fastest document to settle
this**, and a professional with access should look there first.

**What turns on the answer.** Whether to charge individual consumers; how to word
the product name and invoices; and whether the current plan to describe it as
"hosted access" rather than a "licence" is the right call.

## A2. Are our fraternal-lodge and veterans-post customers actually exempt?

**The question.** SAIRNfreedom's customers are VFW and American Legion posts,
Elks, Moose and Eagles lodges — typically **501(c)(8), (c)(10), (c)(19) or
(c)(4)**. Are their purchases of software and ebooks exempt from Ohio sales tax?

**Why it matters, commercially.** Pricing and the checkout flow were about to
assume a nonprofit exemption. **Our reading is that the exemption mostly does not
apply**, and building a nonprofit discount around it would be a pricing error
discovered by an auditor rather than by us.

**What is already established.** ORC 5739.02(B)(12) exempts sales to churches,
**501(c)(3)** organisations, and nonprofits *"operated exclusively for charitable
purposes"* — with charitable purposes then defined narrowly and exhaustively
(relief of poverty, improvement of health, homes for the aged, educational
broadcasting, animal adoption, institutions of learning, PTAs, community arts
centres, performances, scientific research). Fraternal and veterans organisations
do not appear.

**The only veterans provision is ORC 5739.02(B)(33)**, and it reaches:

> "the **state headquarters** of any veterans' organization … **for use by the
> headquarters**"

**State headquarters only — a local post appears not to qualify.**
Corroborating: the Streamlined exemption certificate Ohio accepts offers
"Charitable organization", "Religious or educational organization" and
"Educational Organization" — **no fraternal or veterans category exists on the
form.**

**The wrinkle worth asking about specifically.** Many lodges operate a **separate
501(c)(3) charitable foundation**. Presumably the exemption attaches to *that
entity as the buyer*, not to the lodge — but if a lodge directs a purchase
through its foundation, does that work, and what documentation is required?

**What turns on the answer.** Whether to build a nonprofit price tier at all; and
whether the exemption-certificate feature is a rare edge case or a common path.

## A3. Have we already crossed a nexus threshold anywhere without registering?

**The question.** Straightforward, and the reason it is here is that the remedy
is not self-help.

**Why it matters.** Discovering a crossing months late generally means a
**Voluntary Disclosure Agreement**, because you cannot retroactively collect from
customers who have already paid — the liability comes out of margin.

**What is already established.** SAIRN has **certain physical nexus in Ohio**
today, so Ohio registration is required regardless of revenue and is not
threshold-dependent. *(Currently on hold pending formation of the new LLC and its
FEIN — see the tax doc.)* Economic nexus elsewhere is the open question.

**A finding the professional should know before relying on any published table:**
**five official government sources currently publish superseded thresholds** —
the SST board's Kentucky and Maine pages, Kentucky DOR (two pages still citing
2018 HB 487), **Maine Revenue Services citing a repealed statute**, and
Louisiana's Remote Sellers Commission still stating a transaction prong repealed
three years ago. Kentucky removed its transaction prong effective **2026-08-01**.
**Illinois DOR is actively de-registering sellers who registered under the old
rule.** All of these err toward over-registration.

**What turns on the answer.** Whether a VDA conversation is needed now, and
whether to delegate threshold monitoring to a service rather than tracking it
in-house.

---

# B. LEGAL — for an attorney

These are not from the tax research but sit at the same decision point and are
grouped here so one handover covers both.

## B1. May a D-4 club serve accompanied non-member guests?

Source: `2026-08-30-sairnfreedom-ohio-liquor-permits.md`

**Completely unresolved in either direction.** ORC 4303.17(A)(1) authorises sales
*"to its members only."* There is **no statute, no Ohio Administrative Code rule,
and no definition of "guest"** anywhere in Chapter 4301:1-1 — the full chapter
index and the definitions rule were read. **Nothing found permitting guests and
nothing prohibiting them by name.**

**Why it matters.** Every lodge in Ohio serves accompanied guests as ordinary
practice. The software must either permit it or block it at the point of sale.
Getting it wrong in the permissive direction is a violation of an applicable
restriction of Chapter 4303, which reaches the **lodge's permit** under ORC
4301.25(A) — the customer's exposure, not ours.

## B2. Does a change in elected officers require a fresh D-4 certification?

Same source.

ORC 4303.17(A)(1) conditions the permit being *"granted or **retained**"* on all
elected officers having filed a certifying statement — and is **silent on
refiling, frequency, and officer turnover**. *"The current officers must have
filed"* and *"the officers who filed were the officers at the time"* are different
rules, and the text does not choose.

**Why it matters.** The difference between the software **flagging** an
uncertified officer and **blocking** on one is a legal question, not a product
decision. Our current design flags and explicitly declines to assert that
refiling is required.

## B3. Ebook publishing — general-information framing and disclaimer

Source: `2026-08-30-sairntech-corporate-site-scoping.md` §5

**Why it matters.** The planned ebook line reuses genuine primary-source
regulatory research — Ohio charitable-gaming law, VA accreditation boundaries,
liquor permit conditions. Every research document says *"I am not a lawyer and
this is not legal advice"* and carries an explicit UNVERIFIED section. **That
framing is load-bearing and must survive the transition into a published,
purchased book.**

Three specifics for review: (a) the disclaimer and general-information framing,
reviewed **once** before the first regulatory title rather than per book; (b)
whether an Ohio-specific title needs an express jurisdictional limitation, given
that an out-of-state buyer is foreseeable; (c) a stated **edition date and
revision policy** — IRS Publication 1771 is three years stale and still prints
2023 figures, which is what any regulatory title becomes without one.

---

## What we are NOT asking

To avoid paying for work already done: the statutory texts above were read from
primary sources and quoted verbatim. **The ask is the characterisation and
application calls, not a re-read of the code.** Where a document could not be
obtained — Ohio's SST Taxability Matrix entry, 38 CFR 14.629 — that is flagged
in the source research rather than papered over.

## Source documents

- `docs/2026-08-30-sairntech-digital-goods-sales-tax.md`
- `docs/2026-08-30-sairnfreedom-ohio-liquor-permits.md`
- `docs/2026-08-30-sairnfreedom-va-claims-accreditation-boundary.md`
- `docs/2026-08-30-sairnfreedom-four-research-items.md`
- `docs/2026-08-30-sairntech-corporate-site-scoping.md`
