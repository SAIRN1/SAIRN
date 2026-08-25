# Kentucky deadline seed — what was established, and the two blockers

**2026-08-25, Hank.** Kentucky was the second half of Batch 3 (West Virginia
landed in `ad45643`). It is **not seeded**, and this file records why, plus every
primary text that was successfully read, so the next session does not repeat the
research.

Nothing in this file is a guess. Every quoted passage was read verbatim from the
source named next to it on 2026-08-25.

---

## Blocker 1 — there is no permitted primary source for the Rules of Civil Procedure

The Kentucky Court of Justice **does not publish the Rules of Civil Procedure**.
Its own rules page (`kycourts.gov/Courts/Pages/Rules-of-Practice.aspx`) carries
exactly one rules link, and it points off-site to **Thomson Reuters Westlaw**
(`govt.westlaw.com/kyrules`). That Westlaw site is publicly reachable and does
carry the full CR text.

**It was not scraped, and that was a deliberate call, not an oversight.** This
is a commercial publisher's platform whose terms of use were not read, and this
project has already been through exactly this decision once: during the SAIRNlaw
Wex/international-caselaw work, BAILII and AustLII were found to prohibit
automated access outright, the Bright Data connector was rejected as the wrong
tool for a *permission* problem rather than a *bot-detection* problem, and CanLII
was noted to have sued an AI legal-research platform over systematic scraping.
Routing around a publisher's terms with better tooling makes it deliberate rather
than incidental. Same reasoning applies here.

**Consequence:** `CR 6.01` (computation), `CR 6.05` (additional time after
service), `CR 5.02` (service methods), `CR 12.01` (answer), `CR 33.01`
(interrogatories), `CR 34.02` (production) and `CR 36.01` (admissions) were
**not read verbatim** and are therefore not encodable to this engine's standard.

Search engines will happily return summaries of these rules. Those are not
primary sources and every period length in this engine computes off the number,
so a summary is not good enough — the same line already drawn for
*Proctor v. Green* in the Texas seed, where a database rendering was accepted
**only** because nothing computed off it.

### Options for unblocking, in the order they should be tried

1. **Read Westlaw's terms of use for the free state-government sites.** If they
   permit on-demand retrieval of a handful of specific documents (as The National
   Archives' Open Justice Licence does for Find Case Law, which this platform
   already relies on), then fetching ~7 named rules is inside the permission and
   this blocker disappears. If they prohibit it, it stays.
2. **Buy the book.** *Kentucky Rules of Court* (Thomson West) is the printed
   official compilation. A purchased copy read by a human is not a licensing
   question at all.
3. **Reconstruct from Supreme Court orders.** Every CR amendment is a free order
   on `kycourts.gov`. This does not work on its own: establishing that a rule has
   *not* been amended since a given order requires the consolidated text, which is
   the thing that is missing. Usable only to confirm a text obtained another way.

---

## Blocker 2 — "legal holiday" is undefined for Kentucky courts, and the obvious candidate is wrong in the dangerous direction

This one is **independent of blocker 1** and would still block Kentucky even if
the full CR text were in hand. Without a defensible holiday calendar every
Kentucky row refuses `NOT_PROVISIONED`, so the rows would be worthless.

**RAP 6(A) uses the phrase twice and never defines it.** Verbatim (Order 2022-49):

> In computing any period of time prescribed or allowed by these rules, by order
> of court, or by any applicable statute, the day of the act, event, or default
> after which the designated period of time begins to run is not to be included.
> The last day of the period so computed is to be included, unless it is a
> Saturday, a Sunday or a legal holiday, in which event the period runs until the
> end of the next day that is not a Saturday, a Sunday, or a legal holiday. When
> the period of time prescribed or allowed is less than 7 days, intermediate
> Saturdays, Sundays, and legal holidays shall be excluded in the computation.

**KRS 446.030 uses it too and also never defines it** (verbatim, LRC):

> ...unless it is a Saturday, a Sunday, a legal holiday, or a day on which the
> public office in which a document is required to be filed is actually and
> legally closed, in which event the period runs until the end of the next day
> which is not one (1) of the days just mentioned. When the period of time
> prescribed or allowed is less than seven (7) days, intermediate Saturdays,
> Sundays and legal holidays shall be excluded in the computation.

**KRS 2.110 is the obvious candidate and it does not fit.** Verbatim (LRC):

> (1) The first day of January (New Year's Day), the third Monday of January
> (Birthday of Martin Luther King, Jr.), the nineteenth day of January (Robert E.
> Lee Day), the thirtieth day of January (Franklin D. Roosevelt Day), the twelfth
> day of February (Lincoln's Birthday), the third Monday in February
> (Washington's Birthday), the last Monday in May (Memorial Day), the third day
> of June (Confederate Memorial Day, and Jefferson Davis Day), the fourth day of
> July (Independence Day), the first Monday in September (Labor Day), the second
> Monday in October (Columbus Day), the eleventh day of November (Veterans Day),
> the twenty-fifth day of December (Christmas Day) of each year, and all days
> appointed by the President of the United States or by the Governor as days of
> thanksgiving, are holidays, on which all the public offices of this Commonwealth
> **may** be closed.

Four things are wrong with using it, and they do not cancel out:

1. **It is titled "Public holidays" and never says "legal holiday".** The link
   from the rules' phrase to this statute is an inference, not a cross-reference.
   Kentucky would be the **second** instance of exactly this defect already
   recorded for Texas, where Tex. R. Civ. P. 4 and Tex. R. App. P. 4.1 both say
   "legal holiday" without citing Tex. Gov't Code 662.021.
2. **It lists four days Kentucky courts do not close for** — Robert E. Lee Day
   (19 Jan), Franklin D. Roosevelt Day (30 Jan), Lincoln's Birthday (12 Feb) and
   Confederate Memorial Day / Jefferson Davis Day (3 Jun). Encoding them rolls
   deadlines **LATER** than any Kentucky court would, and late is how a filing is
   missed. **This is the inverse of the Pennsylvania case**, where the published
   closure schedule was *broader* than the statute and the fix was to encode the
   statute; here the statute is broader than reality, so the Pennsylvania rule
   ("encode the statute, disclose the divergence") produces the dangerous
   direction and cannot simply be applied.
3. **Thanksgiving Day is not in the list.** The fourth Thursday of November
   appears only through "all days appointed by the President ... as days of
   thanksgiving" — an annual proclamation, not a fixed date in the statute.
   Omitting it computes **EARLY** (safe); encoding it means encoding a
   proclamation the statute does not itself contain.
4. **There is no weekend-shift provision at all.** Unlike W. Va. Code 2-2-1(b),
   KRS 2.110 has no "if it falls on a Sunday" clause, so New Year's Day on a
   Saturday is simply a Saturday holiday and there are no observed dates to
   compute. Whether that is right or whether court practice shifts anyway is not
   answered by any text read here.

**This is a lawyer's question, not a research question** — the same shape as the
already-open Illinois holiday row (statute vs court-observed disagree both ways,
assigned to Michael). It should join that question set rather than being resolved
by picking a reading.

---

## What WAS established, verbatim, and is reusable

All of this came from free primary sources and is worth keeping.

### Kentucky replaced its appellate rules on 2023-01-01 — CR 73 is REPEALED

**Supreme Court of Kentucky Order 2022-49**, "Order Creating Rules of Appellate
Procedure and Amending Rules of Civil Procedure, Criminal Procedure, and Family
Court Rules of Practice and Procedure", verbatim: *"The following Rules of
Appellate Procedure and amendments to the Rules of Civil Procedure, Criminal
Procedure and Family Court Rules of Practice and Procedure shall be effective
January 1, 2023"*.

The same order states, verbatim:

- *"CR 72.01-72.13 shall be deleted in their entirety."*
- *"CR 73.01-73.08 shall be deleted in their entirety."*
- *"CR 74.01-74.02 shall be deleted in their entirety."*
- *"CR 75.01-75.15 shall be deleted in their entirety."*
- *"CR 76.01-76.46 shall be deleted in their entirety."*

**This is the trap the research avoided.** Every secondary summary of Kentucky
appellate deadlines still cites **CR 73.02** for the notice of appeal. That rule
no longer exists. Anyone seeding Kentucky from a summary would encode a repealed
rule.

Source: `https://www.kycourts.gov/Courts/Supreme-Court/Supreme%20Court%20Orders/202249.pdf`

### RAP 3(A) — notice of appeal, and a trigger unlike any already in the engine

Verbatim:

> (1) **30 days to appeal, unless another time applies.** Unless a statute or
> court rule provides a different time, the notice of appeal required by RAP 2
> shall be filed with the clerk of the court from which the appeal is taken no
> later than 30 days from the date of notation of service of the judgment or
> order appealed from.
> (2) **Date from which time to appeal begins to run.** The date of notation of
> service of the judgment or order under CR 77.04(2) or RCr 12.06 shall be the
> date for the purpose of fixing the running of the time for appeal under this
> rule.

And amended **CR 77.04(2)**, verbatim from the same order:

> The clerk shall make a note in the case docket of the service required in
> paragraph (1) of this rule and the notation shall show the date of service. The
> date of the notation on the docket of the service of notice of entry, or the
> date of filing a waiver if prior thereto, shall be the date of entry for the
> purpose of fixing the running of the time for appeal under RAP 3.

**Kentucky is a sixth way to start an appeal clock** — not entry, not signing,
not rendition, not service with notice of entry, but *the clerk's docket notation
of service of the notice of entry*, or an earlier-filed waiver. It feeds the
open trigger-derivation row directly, and the waiver limb is an `earlier_of`
between two supplied dates that would refuse on partial input for the ordinary
case where no waiver exists.

**RAP 3(E)(2) is a `retrigger`, and the rule contradicts itself on the date.**
(E)(2) verbatim: *"If a party timely files in the trial court any of the
following motions under the Kentucky Rules of Civil Procedure, the time to file
an appeal runs for all parties from **the entry of the order** disposing of the
last such remaining motion: CR 50.02; CR 52.02; or CR 59, except when a new trial
is granted under CR 59. No motions filed under any other civil rule will toll the
time to file a notice of appeal."* But (E)(4) measures the same thing *"from the
date of the RAP 3(A)(2) docket notation regarding service of the order disposing
of the last such remaining motion"*. Entry and docket-notation-of-service are
different dates. Resolve before encoding.

### RAP 6 — the appellate computation standard, ready to encode once a calendar exists

Quoted in full above. Short-period exclusion is **less than 7 days**, so the
engine property is `7`. Rollover is forward only. No months provision. RAP 6(C)
and (D) both say the court **may not** extend time under RAP 3, 4 or 17, which is
why no extension applies to the notice of appeal.

### Kentucky's service extension covers ELECTRONIC service — the opposite of the federal rule

**eFiling Rules Section 13(6)** (Supreme Court Order 2022-65, "Administrative
Rules of Practice and Procedure for the Kentucky Court of Justice Electronic
Filing", *"effective upon entry, and until further Order"*), verbatim:

> **Additional time after electronic service.** Service by electronic means under
> this rule is treated the same as service by mail under CR 6.05 for the purpose
> of adding three (3) days to the prescribed period.

Two things follow. First, Kentucky **adds** three days for e-service where FRCP
6(d) deliberately stopped doing so in 2016 and where W. Va. R. Civ. P. 6(e)'s
equivalent is contested — so it must not be encoded by analogy to either.
Second, *"adding three (3) days to the prescribed period"* is the
**period-lengthening** sequencing (`add_to_period_then_roll`), the New York /
Georgia / pre-2025 West Virginia shape, **not** the federal after-expiry order.
That still needs confirming against CR 6.05's own words, which are behind
blocker 1.

Source: `https://www.kycourts.gov/Courts/Supreme-Court/Supreme%20Court%20Orders/202265.pdf`

### KRS 446.030 — and a backward rule that rolls FORWARD

Quoted in full above. Subsection **(1)(b)** is a genuine backward-computation
provision, and its remedy runs the opposite way to every backward rule in this
engine so far: *"If the day thereby computed on which or by which the act is
required to be done falls on a Saturday, Sunday, legal holiday, or a day on which
the public office in which the act is required to be completed is actually and
legally closed, **the act may be done on the next day** which is none of the days
just mentioned."* W. Va. R. Civ. P. 6(a)(5) and Fla. 2.514(a)(5) both roll a
backward period **backward**; KRS 446.030(1)(b) rolls it **forward**, which
shortens the notice the period was meant to guarantee. `rollOff` cannot express
that today — it walks in the direction it is given. Encoding a Kentucky backward
period will need a new engine capability, not just data.

Sources: `https://apps.legislature.ky.gov/law/statutes/statute.aspx?id=19391`
(446.030), `https://apps.legislature.ky.gov/law/statutes/statute.aspx?id=46`
(2.110).

---

## Recommended next action

Put blocker 2 in front of a lawyer alongside the open Illinois holiday row and
the two Texas secondary-source rows — it is the same class of question and they
should be asked together. Resolve blocker 1 by reading Westlaw's terms or by
buying the printed compilation. **Do not seed Kentucky from a summary, and do not
encode CR 73.02.**
