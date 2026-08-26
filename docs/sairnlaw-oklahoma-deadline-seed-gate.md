# Oklahoma — deadline-seed source-availability gate

**Run 2026-08-26. Verdict: PASS on sources. It has Louisiana's rollover SHAPE
but not Louisiana's problem, and the reason is one clause in the holiday
statute. Two things must be settled before seeding, and the calendar is NOT
fully derivable.**

Oklahoma (~4.1M). Civil procedure is statutory — the Oklahoma Pleading Code,
Title 12.

---

## 1. Sources — PASS

**OSCN, the Oklahoma State Courts Network**, publishes Title 12 *and* Title 25
free on **plain `curl`**, with per-section Historical Data giving real
`effective_from`.

| What | CiteID |
|---|---|
| 12 O.S. § 2006 (Time) | `DeliverDocument.asp?CiteID=94867` |
| 12 O.S. § 2012 (answer) | `CiteID=94873` |
| 25 O.S. § 82.1 (Holidays) | `CiteID=73358` |
| 25 O.S. § 82.4 (Juneteenth) | `CiteID=73361` |

Title indexes at `Index.asp?ftdb=STOKST12&level=1` (and `STOKST25`) list every
section with its CiteID, so navigation is mechanical rather than guesswork.

## 2. The rollover has LOUISIANA'S SHAPE — and one clause saves it

**12 O.S. § 2006(A)(1)**, verbatim:

> The last day of the period so computed shall be included, **unless it is a
> legal holiday as defined by Section 82.1 of Title 25** of the Oklahoma
> Statutes **or any other day when the office of the court clerk does not remain
> open for public business until the regularly scheduled closing time**, in which
> event the period runs until the end of the next day which is not a legal
> holiday or a day when the office of the court clerk does not remain open …

**Saturday and Sunday are not named.** That is exactly the structure that blocked
Louisiana one gate earlier, where art. 5059 rolls only on "a legal holiday" and
R.S. 1:55 makes Saturday a holiday in some parishes only.

**Oklahoma resolves it in the first eight words of its holiday statute.**
25 O.S. § 82.1(A):

> The designation and dates of holidays in Oklahoma shall be as follows: **Each
> Saturday, Sunday**, New Year's Day on the 1st day of January, …

**Both weekend days are statutory holidays, statewide, with no parish or county
qualification.** So § 2006's rollover reaches them, and **the engine's
`isWeekend()` is correct for Oklahoma** — by a different textual route than any
common-law state, but correct.

**This is worth recording as a pattern, not a one-off.** Three states in a row
have now had the weekend inside the holiday list rather than beside it —
Louisiana (Sunday only, parish-scoped Saturday → **blocked**), Oregon (Sunday in
the list but Saturday *also named separately in the rule* → **safe**), Oklahoma
(both days in the list, statewide → **safe**). The question to ask on every
future gate is no longer "does the rule name Saturday and Sunday" but **"if it
doesn't, does the holiday statute cover both, everywhere?"**

## 3. The short-period exclusion — eleven days, and SIX SECTIONS CARVED OUT

> **Except for the times provided in Sections 765, 990.3, 1148.4, 1148.5,
> 1148.5A, and 1756 of this title**, when the period of time prescribed or
> allowed is **less than eleven (11) days**, intermediate legal holidays and any
> other day when the office of the court clerk does not remain open for public
> business until the regularly scheduled closing time, shall be excluded from the
> computation.

Two findings:

- **Threshold is 11**, joining Tennessee, Arizona, Wisconsin and Alabama, and
  not the 7 of six other states or Minnesota's absence.
- **Six named sections are expressly excluded from the exclusion.** Any row
  seeded under **§§ 765, 990.3, 1148.4, 1148.5, 1148.5A or 1756** must count
  every intermediate day regardless of period length. This is an *enumerated*
  opt-out — narrower and more tractable than Louisiana's open-ended "expressly
  excluded" and Minnesota's open-ended opt-in, but it is still something a
  standard-level flag cannot express. **None of those six is in a first civil
  batch, so the constraint is recordable rather than blocking** — but seeding one
  later without noticing would silently apply an exclusion the statute removes,
  computing **LATE**.

**The clerk-closure limb appears in BOTH the rollover and the exclusion**, and it
is a *partial-closure* test — "does not remain open … **until the regularly
scheduled closing time**". Broader than a simple closed/open test, same breadth
as Oregon's. Unknowable in advance; **additional to** the holiday list rather
than a replacement, so omitting it reports **EARLY**. Disclosable.

## 4. THE CALENDAR IS NOT FULLY DERIVABLE — two independent reasons

### (a) The Christmas rule is the most complex encountered anywhere

§ 82.1(A), verbatim on Christmas:

> Christmas on the 25th day of December, **the day before or after Christmas if
> Christmas is not on a Saturday or Sunday**, **the Thursday and Friday before
> Christmas if Christmas is on a Saturday**, **the Monday and Tuesday after
> Christmas, if Christmas is on a Sunday**; and if any of such holidays **other
> than Christmas** fall on Saturday, the preceding Friday shall be a holiday …
> and if any of such holidays **other than Christmas** fall on Sunday, the
> succeeding Monday shall be a holiday …

So Christmas produces **two or three holidays** depending on the weekday, and the
general both-ways shift **expressly does not apply to Christmas** (it has its own
bespoke rules instead). Critically, **"the day before **or** after Christmas"** —
on a weekday Christmas — **does not say which**. That choice is not in the
statute.

### (b) An annual Executive Order supplies the actual dates

§ 82.1(B):

> **The Governor shall issue an Executive Order each year specifying the dates on
> which the holidays other than Saturdays and Sundays designated in subsection A
> of this section occur.** If the President of the United States declares any day
> other than those listed in subsection A as a national holiday, the Governor
> **may** issue an Executive Order declaring such day a state holiday.

**That is the New Jersey shape — an annual order — layered on top of a statute.**
It resolves the before-or-after-Christmas choice, and it is the only thing that
does. So an Oklahoma calendar is **ingest-per-year for at least one day**, and
the presidential limb is discretionary and ad hoc on top of that (**EARLY**,
disclosable).

### Other list items

- **The day after Thanksgiving is a statutory holiday** — as in South Carolina,
  and unlike Minnesota where it is a branch option.
- **No Columbus Day or Indigenous Peoples Day at all** — as in Oregon.
- **JUNETEENTH IS NOT A § 82.1 HOLIDAY, AND ITS DATE IS NOT 19 JUNE.**
  25 O.S. **§ 82.4** declares *"**The third Saturday in June** of each year …
  'Juneteenth National Freedom Day'"* — a separate section, and § 2006 defines
  legal holiday by reference to **§ 82.1 only**.
  **Practically this changes nothing**, because the third Saturday in June is
  already a holiday under § 82.1(A)'s "Each Saturday" — so it rolls anyway. But
  it must not be encoded as a 19 June holiday by analogy to the ten other seeded
  states that have one: doing so would add a non-holiday and compute **LATE**.
  **Oklahoma's Juneteenth is functionally invisible to deadline computation.**

## 5. Service extension — plus a branch with a different TRIGGER

**§ 2006(D)**, verbatim:

> Whenever a party has the right or is required to do some act … within a
> prescribed period after the service of a notice or other paper upon the party
> and the notice or paper is served upon the party by **mail, third-party
> commercial carrier or electronic means, three (3) days shall be added to the
> prescribed period**; **provided, however, when a summons and petition are
> served by mail, a defendant shall serve an answer within twenty (20) days or
> thirty-five (35) days if pursuant to subsection A of Section 2012 of this
> title, after the date of receipt or if refused, the date of refusal** of the
> summons and petition by the defendant.

- **+3 days for mail, third-party commercial carrier and electronic means** —
  period-lengthening ("added to the prescribed period"), like most, and **not**
  Alabama's federal after-expiry order. Ninth distinct answer on electronic
  service, and the only one naming **third-party commercial carrier** as its own
  category.
- **The proviso is a different TRIGGER, not a different amount.** Where a summons
  and petition are served by mail, the answer runs from **the date of receipt —
  or, if refused, the date of refusal** — not from service, and takes **no +3**.
  That must be its own row with a trigger named for receipt/refusal, or a caller
  supplying a service date would compute **EARLY**.

## 6. The answer period has a PLAINTIFF'S ELECTION the engine cannot see

**§ 2012(A)**: a defendant shall serve an answer **within 20 days** after service
of the summons and petition; cross-claim answer **20 days**; reply to a
counterclaim **20 days** after service of the answer or of the order; and on a
denied or postponed motion, **20 days after notice of the court's action**.

But:

> **4.** The party requesting a summons to be issued or filing a counter-claim or
> cross-claim **may elect to have the answer served within thirty-five (35) days
> in lieu of the twenty (20) days** set forth in this section.

**That is a plaintiff's election — a fact about what the requesting party chose,
which the engine has no input for.** Same shape as Louisiana's art. 1001 (21 vs
30 depending on whether the plaintiff served discovery with the petition). It
must be **two rows with unmissable trigger names**, never one row with a default:
guessing 35 where 20 applies computes **LATE**.

There is also a **reservation of time**: a defendant may file one, extending the
response by a further 20 days but **waiving** the defences in § 2012(B)(2)–(6)
and (9). A filing the engine cannot see; it only ever extends, so omitting it is
**EARLY**.

## 7. What was NOT determined

- **The discovery response periods** — §§ 3233 (interrogatories), 3234
  (production) and 3236 (admissions) in Title 12 were not read. Same source, same
  mechanical index; effort remaining, not a source problem.
- **Whether any of §§ 765, 990.3, 1148.4, 1148.5, 1148.5A or 1756 would ever
  belong in a civil batch** — they were not read, only their carve-out noted.
- **The current year's gubernatorial Executive Order** under § 82.1(B), which is
  what actually fixes the before-or-after-Christmas day.
- **25 O.S. § 82.2 ("Additional Holidays – Acts Performable – Optio…")** — the
  index shows it exists and its title suggests it bears on acts performable on
  holidays. § 2006 points only at § 82.1, but § 82.2 should be read before
  seeding to confirm it does not widen the definition.

## 8. Verdict

**PASS on sources**, and no blocker: OSCN is free, official and `curl`-reachable
with real per-section currency, and the weekend question — which blocked
Louisiana — resolves safely here because § 82.1(A) makes both weekend days
statewide holidays.

**Two things to settle before seeding, plus one calendar constraint:**

1. **The 20-vs-35 answer election** and the **mail-service receipt/refusal
   trigger** must each be their own row with unmissable names. Both are facts
   about what a party did, and both run **LATE** if defaulted wrongly.
2. **Record the six carved-out sections** so a later row under any of them does
   not silently inherit the 11-day exclusion.
3. **The calendar is ingest-per-year, not derivable** — the before-or-after-
   Christmas day comes only from the Governor's annual Executive Order. Oklahoma
   joins New Jersey, North Carolina and Maryland as ingest-not-derive, and it is
   the first to be so for a *single day* inside an otherwise derivable list.

And one thing not to do: **do not encode Juneteenth on 19 June.** Oklahoma's is
the third Saturday in June, lives in § 82.4 rather than § 82.1, and is already
covered by "Each Saturday".
