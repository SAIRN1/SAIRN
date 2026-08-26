# Colorado — deadline-seed source-availability gate

**Run 2026-08-26. Verdict: SPLIT — statutes PASS outright, RULES BLOCKED pending
one decision. Colorado is NOT seedable today, and the decision it needs is a
materially easier one than Tennessee's.**

Colorado (~5.9M) is the next unseeded state after Wisconsin.

**Stated plainly up front: I did NOT read C.R.C.P. Rule 6 verbatim.** Its
consolidated current text sits behind an "I Agree" dialog I will not click, and
nothing in this document should be read as reporting what that rule says.

---

## 1. Statutes — PASS, with two independent free channels

`leg.colorado.gov` publishes the **full Colorado Revised Statutes as free
official PDFs** through the Office of Legislative Legal Services, served on a
plain `curl` with no gate:

```
leg.colorado.gov/sites/default/files/images/olls/crs2024-title-13.pdf   200 (5.6 MB)
leg.colorado.gov/sites/default/files/images/olls/crs2024-title-24.pdf   200 ( 25 MB)
```

**C.R.S. § 24-11-101 was read verbatim from that PDF** (page 252 of 3,111 in the
Title 24 file) — no Lexis, no browser, no gate. That is the channel Tennessee
lacked entirely.

**Currency caveat, disclosed:** every page footer reads *"Colorado Revised
Statutes 2024 **Uncertified Printout**"*. So it is the **2024** edition and is
expressly **not** the certified text — § 2-5-118 makes only the printed version
official. Contrast Wisconsin, whose pages carry a statutory certification with
an as-of date. Colorado's free channel is complete and official-in-origin but
does not certify itself, so a seed would need the currency disclosed or checked
against session laws.

## 2. Rules — BLOCKED, and it is the Tennessee shape with a real difference

The **Colorado Judicial Branch publishes only rule-change PDFs**, not a
consolidated current text. `coloradojudicial.gov` carries dozens of
`Rule_Change_YYYY-NN.pdf` files; the old `courts.state.co.us/.../Full_set_of_CRCP_and_Water_Rules.doc`
now redirects to a site-search page, and `/rules`, `/court-rules`,
`/self-help/rules` and `/supreme-court/rulemaking` are all **404**. The one
promising `Full Table of Contents.pdf` turns out to be the **Pattern Civil Jury
Instructions** TOC, not the Rules.

Reconstructing the current C.R.C.P. from a base plus rule-change PDFs is exactly
the **Arizona** method, failed there because a reconstruction cannot prove its
own completeness. And Colorado has a specific reason that would bite: **Rule
Change 2011(18) was a wholesale "TIME CALCULATION CHANGES" overhaul.** Any
pre-2012 text of Rule 6 carries an *"less than eleven days"* intermediate-day
exclusion that the overhaul may well have removed — so a stale snapshot would be
wrong on the single most load-bearing property in the rule.

The consolidated maintained text lives on the **Colorado Legal Resources public
access site**, reached from the General Assembly's own "click here" link:

```
lexisnexis.com/hottopics/colorado/... -> advance.lexis.com/container?...
```

Unlike Tennessee's, **this site loads** — the CRS table of contents (Titles
1–43) renders, and it carries a **"Colorado - Local, State and Federal Court
Rules"** link, so the C.R.C.P. is there. But reaching content requires
dismissing a modal, and the modal is a terms acceptance.

### The dialog, verbatim — and the carve-out that changes the analysis

> **Colorado Statutes Annotated - Free Public Access**
>
> This website is maintained by LexisNexis®, the publisher of the Colorado
> Revised Statutes, to provide free public access to the law. …
>
> **Terms & Conditions**
>
> Your use of this service is subject to the attached Terms and Conditions
> associated with LexisNexis's proprietary interests. LexisNexis® reserves the
> right to claim and defend its copyright on copyrightable portions of the site.
> **The Terms and Conditions do not apply to the text and numbering of the
> statutes, constitutional provisions, or court rules in the content of the
> site.** Pursuant to section 2-5-118, Colorado Revised Statutes, persons,
> agencies, or political subdivisions **may publish, reprint, or otherwise
> distribute the statutes** in print, electronic, or other digital format;
> however, only the printed version … may be considered to be the official
> statutes of the state of Colorado. Please indicate your agreement to these
> Terms and Conditions by clicking **"I agree"** below.

**Four differences from Tennessee, all favourable:**

| | Tennessee | **Colorado** |
|---|---|---|
| Does the site load? | **No** — 403 to curl *and* browser | **Yes**, TOC renders |
| Do the terms cover the text we need? | Not addressed | **Expressly NOT** — "do not apply to the text and numbering of the statutes … or court rules" |
| Does state law permit redistribution? | Not found | **Yes** — C.R.S. § 2-5-118 |
| Who does the state's own site vouch for? | AOC expressly **disclaims** control | Maintained under contract with the **Committee on Legal Services of the General Assembly** |

**But it is still an "I Agree" click, and I did not make it.** That is the same
bright line drawn for BAILII/AustLII and with CanLII v. Caseway AI in mind, and
it is not mine to cross unilaterally — even where the terms themselves say they
do not reach the material in question. The difference is that here the decision
is nearly self-answering on the document's own words, which was not true of
Tennessee.

## 3. What WAS read verbatim — C.R.S. § 24-11-101

From the free OLLS PDF, in full:

> **24-11-101. Legal holidays - effect. (1)** The following days, viz: The first
> day of January, commonly called New Year's day; the third Monday in January,
> which shall be observed as the birthday of Dr. Martin Luther King, Jr.; the
> third Monday in February, commonly called **Washington-Lincoln day**; the last
> Monday in May, commonly called Memorial day; the nineteenth day of June,
> commonly called Juneteenth; the fourth day of July, commonly called
> Independence day; the first Monday in September, commonly called Labor day;
> **the first Monday in October, commonly called Frances Xavier Cabrini day**;
> the eleventh day of November, commonly called Veterans' day; the fourth
> Thursday in November, commonly called Thanksgiving day; the twenty-fifth day
> of December, commonly called Christmas day; **and any day appointed or
> recommended by the governor of this state or the president of the United
> States as a day of fasting or prayer or thanksgiving**, are hereby declared to
> be legal holidays and shall, for all purposes whatsoever, as regards the
> presenting for payment or acceptance and the protesting and giving notice of
> the dishonor of bills of exchange, drafts, bank checks, promissory notes, or
> other negotiable instruments **and also for the holding of courts**, be
> treated and considered as is the first day of the week commonly called Sunday.

Four findings worth banking regardless of whether Colorado is ever seeded:

- **FRANCES XAVIER CABRINI DAY, the first Monday in October.** Colorado replaced
  Columbus Day with it in 2020. **No other jurisdiction in this engine has it**,
  which makes it the natural "prove the calendar is actually being read" day —
  the role Patriots' Day played for Massachusetts and Truman Day for Missouri.
  It also means **Columbus Day must NOT be carried across** from New Jersey,
  Virginia, Massachusetts or Missouri, all of which count it.
- **The statute links itself to courts in its own words** — "and also **for the
  holding of courts**". So Colorado does not join the bundled
  which-list-applies question on the statute side; § 24-11-101 says it reaches
  court business. (Whether C.R.C.P. 6 points here instead is unread.)
- **THERE IS NO WEEKEND-SHIFT PROVISION AT ALL.** § 24-11-101 says nothing about
  a holiday falling on a Saturday or a Sunday. Every state seeded so far has one
  somewhere — Sunday-only (MA, MO, WI) or both-ways (VA, WV, MD). Colorado's
  silence is a genuine gap, and **the temptation to import a shift by analogy is
  exactly the mistake caught three times already**. Whatever C.R.C.P. 6 says
  about rolling the last day would have to carry that weight instead.
- **The governor/president "fasting or prayer or thanksgiving" limb** is ad hoc
  and not knowable in advance — the same shape as Va. § 1-210(F) and Mass. R.
  6(a)'s President/Congress limb. EARLY direction, disclosable.

## 4. What was NOT determined

- **C.R.C.P. Rule 6 itself** — not read. Unknown: whether an intermediate-day
  exclusion survives Rule Change 2011(18) and at what threshold; what the
  rollover test is; whether it points at § 24-11-101 or elsewhere; whether
  backward counting is addressed; and the service-extension shape (which, on the
  five patterns found so far, cannot be guessed).
- The answer period and the discovery periods — not read, for the same reason.
- Whether any Colorado district publishes local holiday closures.
- Whether the OLLS PDF set is refreshed annually and how far behind "2024" now
  is relative to the current session.

## 5. Verdict

**Statutes PASS; rules BLOCKED pending one decision; Colorado NOT seedable
today.**

This is the Tennessee question again, but on much better facts: the site loads,
the state's own General Assembly contracts for it, C.R.S. § 2-5-118 permits
redistribution, and **the terms text itself says it does not apply to the text
and numbering of statutes, constitutional provisions or court rules.** On its
own words the material this engine needs is outside the agreement being asked
for.

**Next action — Michael's, and narrower than Tennessee's:** decide whether
clicking "I Agree" on a public-access site whose terms expressly exclude
statutes and court rules is acceptable for this use. If yes, Colorado is
immediately readable and the remaining work is ordinary. If no, Colorado is
refused on the same basis as Tennessee — but the two should be recorded as
different facts, because Tennessee's site does not load at all and its terms
carve out nothing.

A second, cheaper option exists and should be weighed first: **ask the Office of
Legislative Legal Services directly.** The public-access page states OLLS "can
provide electronic copies of specified portions of the Colorado Revised Statutes
without charge." Whether that extends to the court rules is worth one email, and
would sidestep the question entirely.
