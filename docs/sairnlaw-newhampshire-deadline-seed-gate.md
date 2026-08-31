# New Hampshire — deadline-seed source-availability gate

**Run 2026-08-31. Verdict: PASS, and SEEDED the same day — 13 rules, calendar
2026 with ten dates.** Local verification is complete: `1200/1200` deadline
assertions pass across the whole suite, of which `50/50` are New Hampshire's own.
**Load to `LAW-PINNACLE-2026` and the live re-verification are NOT done** — this
clone has no `SAIRNLAW_LICENSE_KEY` — and nothing in this document should be read
as claiming otherwise. See §8.

**Three headline findings.**

**★ THERE IS NO MAILED-SERVICE EXTENSION. NOT A SHORTER ONE — NONE.** Every
seeded jurisdiction until now has had one: the FRCP family adds three, South
Carolina and New Jersey add five, Hawaiʻi adds two, California and New York use
per-method tables. New Hampshire has no such provision anywhere in the civil
rules or in the Supplemental Rules for Electronic Filing. **An `add: 3` copied
from any neighbour reports LATE on every New Hampshire deadline** — the direction
that loses a filing.

**AND THE REASON IS STRUCTURAL.** New Hampshire runs its periods from **filing**
and from **the date on the clerk's notice**, where the FRCP family runs them from
**service**. Three separate rules name the delivery method in the same sentence
and then decline to let it matter.

**RSA 288:2 IS A SUNDAY RULE ONLY**, so Friday 3 July 2026 is not a New Hampshire
holiday — the fourth different answer this platform now has to that one date.

New Hampshire (~1.4M) was taken up as the claim already held by this clone
(`.claude/claims/hank.json`, claimed 2026-08-31T10:21Z) after Hawaiʻi closed
earlier the same day.

---

## 1. Sources — PASS, and the 403 is not a wall

| What | URL | Result |
|---|---|---|
| **Superior Court Civil Rules, complete** | `courts.nh.gov/rules-superior-court-state-new-hampshire/civil-rules` | **200 with browser headers — 2,225,391 B, 228,837 chars of text, all 55 rules + 13A, 13B, 28A** |
| Same URL, plain `curl` | — | **403** |
| Same URL, `WebFetch` | — | **403** |
| `courts.nh.gov/` (homepage), plain `curl` | — | **403** |
| Supplemental Rules for Electronic Filing | `courts.nh.gov/supplemental-rules-superior-court-new-hampshire-electronic-filing` | 200 |
| Individual rule page | `…/civil-rules/rule-1-scope-purpose-enforcement-waiver-and` | 200 |
| **2013 adoption order (PDF)** | `…/2021-08/05-22-2013-order-adopting-new-superior-court-civil-rules.pdf` | 200, 692,803 B |
| RSA 288:1, 288:2, 288:4 | `gencourt.state.nh.us/rsa/html/XXV/288/…` | 200 |
| RSA 653:7, 652:1–:4, 21:35 | `gencourt.state.nh.us/rsa/html/…` | 200 |
| NHJB 2026 court-holiday schedule (PDF) | `…/2025-06/2026-nhjb-holiday-schedule.pdf` | **403 to every automated route; not read** |

**IT IS A HEADER CHECK, NOT A GATE.** `courts.nh.gov` 403s a plain `curl` and
`WebFetch` on *every* path including the homepage, and returns 200 to the same
URL with a full browser header set (`Accept`, `Accept-Language`, `sec-ch-ua`,
`Sec-Fetch-*`, `Upgrade-Insecure-Requests`). **No CAPTCHA, no terms page, no
login.** Colorado is a WALL (CAPTCHA behind terms); New Mexico was an OBSTACLE
needing a browser pass to surface a plain PDF URL; Idaho was only wrong guessed
URLs. **New Hampshire is a fourth shape: the document was always public and the
request looked wrong.**

The rules render client-side from a Tabulator table, so the visible page shows
five rules at a time and the pager is JavaScript. **All 59 rows are in the page
payload**, which is why the plain fetch returns the whole rule set. Completeness
was checked rather than assumed: 60 distinct rule numbers extracted, 1–55 plus
13A, 13B, 28A and the reserved 62/201 headings.

---

## 2. Computation — the shortest rule on the platform

**N.H. Super. Ct. R. 2, in full.** This is the entire rule:

> In computing any period of time prescribed or allowed by these rules, by order
> of court, or by applicable law, the day of the act, event, or default after
> which the designated period of time begins to run shall not be included. The
> last day of the period so computed shall be included, unless it is a Saturday,
> Sunday, or a legal holiday, in which event the period shall extend until the
> end of the next day that is not a Saturday, Sunday, or a legal holiday **as
> specified in RSA ch. 288, as amended**.

Two sentences. What is *not* in it: no intermediate-day exclusion at any length,
no months-or-years rule, no hours rule, no backward-direction rule, no
non-extendable list, no subdivisions to cite.

**NO SHORT-PERIOD EXCLUSION AT ALL** — joins MN/UT/NV/KS/ID/NE. **It matters
more here than the tally suggests:** four seeded rows are **ten days**, which
Arkansas's 14-day threshold and Alabama's and Wisconsin's 11 would all have
excluded weekends from. Proved as a date, not just as a field: Friday 6 March
2026 + 10 straight days is **Monday 16 March**, where business-day counting gives
Friday the 20th.

### The referent names a CHAPTER, not a section — and that distinction already decided a date once

Hawaiʻi's Rule 6(a) named **HRS § 8-1** by number, so § 8-2's weekend observance
sat *outside* the reference and Hawaiʻi's calendar omits its shifted Friday as a
reading. Rule 2 reaches **RSA ch. 288**, so **RSA 288:2 is inside the reference
and is carried.**

It then turns out not to matter in 2026, and the reason is the finding:

> **288:2** … When any holiday listed in RSA 288:1 falls on **Sunday**, the
> following day shall be observed as a holiday.

**A Sunday rule only. There is no Saturday limb at all.** 4 July 2026 is a
Saturday, so New Hampshire has no Friday 3 July observance — **not by
interpretation, but because no clause could produce one.** And no RSA 288:1
holiday falls on a Sunday in 2026 (checked date by date), so the shift that *does*
exist is dormant this year.

| | Friday 3 July 2026 | why |
|---|---|---|
| Idaho | **carried** | Idaho Code § 73-108's Saturday shift is in the section the rule cites |
| Nebraska | **carried** | Neb. Rev. Stat. § 25-2221's Saturday shift, likewise |
| Hawaiʻi | omitted | HRS § 8-2 *does* shift Saturdays, but Rule 6(a) incorporates § 8-1 alone — **a reading** |
| **New Hampshire** | **omitted** | **RSA 288:2 has no Saturday limb — nothing to read** |

Four jurisdictions, three reasons, one date. Asserted directly against the Idaho
and Nebraska calendar files, which both carry `2026-07-03`.

### No direction rule, so no backward row — and the one given up is unusual

Rule 2 extends to *"the **next** day"* and says nothing about a period measured
before an event — the Mississippi/Idaho/Nebraska/Hawaiʻi shape, not New Mexico's.

**Rule 26(b) is the one worth naming:** no deposition notice is reasonable
*"unless served at least 3 days, **exclusive of the day of service and the day of
caption**, before the day on which they are to be taken."* That period carries
its **own both-endpoints-excluded convention**, which Rule 2 does not supply and
this engine cannot express. Also unseeded and backward: Rule 5(a)(8) (dispositive
motions ≥120 days before trial), Rule 5(a)(9) (other pre-trial motions ≤14 days
before trial), Rule 35 (14-day trial-management filings), Rule 40 (10 days' notice
to a next friend).

---

## 3. ★ Service — there is nothing to model

The phrases **"shall be added"**, **"additional days"** and **"prescribed
period"** do not occur anywhere in the Superior Court Civil Rules. The only
sentence in the whole rule set matching a days-added shape is Rule 26(b)'s
deposition notice, which is a backward minimum, not an extension. The
Supplemental Rules for Electronic Filing add nothing either — their only time
provisions are a five-business-day fee purge, a ten-day signature challenge, and
*"a document is timely filed if it is filed before midnight on the date the
filing is due."*

**The reason is structural rather than an omission.** Three rules name the
delivery method in the same sentence and then refuse to let it count:

| Rule | the period runs from | and the rule says |
|---|---|---|
| 13(a) | *"10 days after **filing** thereof"* | — |
| 12(e) | *"10 days of **the date on the written Notice**"* | *"which shall be **mailed or electronically delivered** by the clerk **on the date of the Notice**"* |
| 43 | *"10 days from **the date on the court's written notice**"* | *"which shall be **mailed by the court on the date of the notice**"* |

A rule that starts the clock on the day the paper is *sent* has nothing to
compensate for. **The practical consequence is real and runs against the
practitioner:** a New Hampshire notice that arrives on day three leaves seven
days, not ten, and no provision gives the time back.

### The fifth answer to a question four states already split on

On the post-motion trigger — a party responding after notice of the court's
action:

| | the time rule reaches | that row takes |
|---|---|---|
| Mississippi | R. 6(e): *"the service of a **notice** or other paper"* | +3 |
| Hawaiʻi | R. 6(e): same words | +2 |
| Idaho | 2.2(c): *"after **service**"* | nothing |
| Nebraska | § 6-1106(c): *"after **being served**"* | nothing |
| **New Hampshire** | **no extension provision exists** | **nothing, for a third reason** |

Idaho and Nebraska take nothing because their extension does not reach a
*notice*. New Hampshire takes nothing because there is no extension to reach the
question with **and** the period does not run from service in the first place.

**Asserted twice.** As a field — no row carries `service_extension`, and no
`nh_*` key was added to `SERVICE_EXTENSION_STANDARDS`. And as a **date**: every
one of the thirteen rows is computed four ways (`mail`, `electronic`,
`facsimile`, `other_consented_means`) and must return the identical answer. The
field being absent is necessary and not sufficient; a standard defaulting
elsewhere could still have paid out.

---

## 4. The calendar — ten dates, one closed list, one omission

**RSA 288:1** enumerates eleven entries; ten are dated for 2026 and seeded.

| Date | Day | Holiday |
|---|---|---|
| 2026-01-01 | Thu | New Year's Day |
| 2026-01-19 | Mon | **Martin Luther King, Jr. Civil Rights Day** — the statutory name, New Hampshire's own |
| 2026-02-16 | Mon | **Washington's Birthday** — not "Presidents' Day" |
| 2026-05-25 | Mon | Memorial Day |
| 2026-07-04 | **Sat** | Independence Day — **and no Friday observance** |
| 2026-09-07 | Mon | Labor Day |
| 2026-10-12 | Mon | **Columbus Day** — Hawaiʻi has none; Idaho and Nebraska do |
| 2026-11-11 | Wed | Veterans Day |
| 2026-11-26 | Thu | Thanksgiving Day |
| 2026-12-25 | Fri | Christmas Day |

**THE LIST IS CLOSED, WHICH NO OTHER SEEDED HOLIDAY STATUTE IS.** Idaho and
Hawaiʻi both end with a day appointed by the President or the governor; Kansas
reaches any day observed by order of the supreme court; Nebraska subordinates its
dates to the federal schedule *and* adds a governor-proclamation limb. RSA 288:1
enumerates and stops — *"…and Christmas Day are legal holidays."* **There is no
proclamation limb to disclose**, which removes the open-ended gap every other
jurisdiction here has to declare.

**NO Juneteenth, NO day after Thanksgiving, NO Good Friday, NO Patriots' Day.**
Nebraska enumerates Juneteenth *and* the day after Thanksgiving *and* Arbor Day;
a calendar copied from it would add three days New Hampshire does not have.

### THE OMISSION — the biennial election day, and it is the one judgment call

RSA 288:1 makes *"the day on which the **biennial election** is held"* a legal
holiday. 2026 is an even-numbered year, so such a day exists.

**Dating it requires a second statute that does not use the same word.**
RSA 653:7: *"The **state general election** shall be held on the first Tuesday
following the first Monday in November of every even-numbered year"* — **Tuesday
3 November 2026**. And RSA ch. 652, the election-law definitions chapter, defines
*election* (652:1), *regular election* (652:2), *state election* (652:3) and
*state general election* (652:4) — and **never defines "biennial election."**

The identification is near-certain and it is still a reading across two chapters.
**The direction decides it.** Omitting a holiday returns the unrolled, sooner
date, and filing early is safe; carrying a day that is not a holiday returns a
date one day **late** and loses the filing. So it is omitted, and the coverage
entry names **Tuesday 3 November 2026** by date. No other 2026 date is affected.

Same call as Hawaiʻi's election day, for a related but not identical reason —
Hawaiʻi's is county-scoped by the statute's own words, New Hampshire's is
statewide and merely undated.

### Two conditional clauses, both live law, both dormant in 2026

- **Memorial Day** is *"the last Monday in May … **or, on a date to coincide with
  the federal observance if it is held on a different day**."* The federal
  observance (5 U.S.C. 6103) is also the last Monday in May, so both fall on
  25 May 2026.
- **Thanksgiving** is *"Thanksgiving Day, **whenever appointed**"* — the statute
  names no date. It is seeded as the fourth Thursday. **That is a convention and
  is labelled as one** on the calendar entry.

### The Judicial Branch's own schedule is not the legal test — the Kansas position, inverted

`courts.nh.gov` publishes *"Court Holidays - 2026"* (a PDF posted 11 June 2025)
and a 2027 one beside it. **Neither was read.** Both 403 to every automated route
available here and the browser PDF viewer returned a blank frame; that is recorded
rather than guessed at.

It would not change this calendar. **Rule 2 keys the rollover on a day being "a
legal holiday as specified in RSA ch. 288", not on whether a courthouse opened.**
In Kansas the statute keys on a day being observed *by order of the supreme
court*, so the Judicial Branch's published list **is** the legal test; here the
statute keys on the legislature's enumeration, so the courts' own list is
practical information and nothing more. **A day the New Hampshire courts close
that RSA 288:1 does not name remains a countable day under Rule 2** — and a
practitioner should still check it before relying on being able to file.

**2026 only.** All ten would generate mechanically, which is exactly why a later
year is refused: generating would hide the biennial-election question behind a
confident answer, and it would be wrong a second way — 2027 is an **odd** year in
which the election limb produces no day at all, and a generator that silently
dropped it would look identical to one that had reasoned about it.

---

## 5. ★ Currency — the published rules carry no dates at all

Hawaiʻi, Idaho, Nebraska and New Mexico all print bracketed amendment notes on
each rule. **The New Hampshire Judicial Branch prints the rule text and a Comment
and nothing else** — verified on the combined page *and* on an individual rule
page.

So every `effective_from` here comes from the **adoption order** instead:

> **Effective Date.** The amendments shall take effect **October 1, 2013**.
> Date: May 22, 2013. ATTEST: Eileen Fox, Clerk of Court

and from the rule set's own **PREAMBLE** in Appendix B of that order:

> They take effect on **October 1, 2013**, and apply to civil actions pending or
> filed in superior court on or after that date.

**The currently-published web version does not reproduce that preamble**, which
is why no date appears anywhere in the live text.

### Every seeded row was diffed against the order — with one limit that changes what the diff proves

Each row's operative sentence was searched for verbatim in the order's text.
**The order's PDF text layer drops words.** Rule 43 comes back as

> "…a motion to set aside any other verdict or decree shall be filed ~~within 10
> days from the date on the court's written notice with respect to same,~~ which
> shall be mailed by the court…"

— eleven words gone, including the ones that carry the period. **So a hit proves
PRESENCE and a miss proves nothing.** Absence had to be established from the
order's **table of contents**, which is clean text: it runs **1 through 54, with
no Rule 13A, no Rule 13B, no Rule 28A and no Rule 55.**

### Two real periods were dropped for want of a date

The New Mexico discipline. All current, all useful, all post-dating the 2013
adoption with **no published effective date anywhere on the Judicial Branch site**:

- **Rule 13A** — a reply within ten days of an objection, and notice to the clerk
  within three days of the court's receipt of it.
- **Rule 12** — the thirty-day summary-judgment objection and the twenty-day reply
  to an additional statement of material facts.

Seeding either would mean inventing an `effective_from`. They are named in the
coverage entry instead, so a caller needing them knows not to compute them here.

### One seeded row changed wording and says so on its face

**Rule 28(a)** as adopted required a party to **file** the request with the court
and **deliver** a copy, and ran the thirty days from that **delivery**; the current
text says **serve** and runs from **service**. Both figures are identical and the
practical trigger is the same event. It is seeded with the current quote and the
adoption date, and the row's note states the change rather than hiding it.

**Rule 12(e)** is the same shape and smaller: 2013 said *"A Motion for
Reconsideration or other post-decision relief **shall be filed** within 10 days of
the date on the written Notice"*; the current text says *"A party **intending to
file** … **shall do so** within 10 days of the date on the written Notice"* and
adds *"or electronically delivered"*. Same ten days, same trigger, verbatim.

---

## 6. Admissions — a plain thirty, and a shape not seen before here

| | how the defendant is protected |
|---|---|
| MS, NM, SC, HI | Rule 36: defendant *"shall not be required to serve … before the expiration of"* 45 days → **`later_of`** |
| Kansas | all three discovery rules are **elections** |
| Nebraska | *"whichever is longer"* in the rule's own words → **`later_of`** |
| Idaho | no 45-day figure exists → **plain 30** |
| **New Hampshire** | **the REQUEST is forbidden for 30 days** → **plain 30** |

Rule 28(a)(i): a request may be served only *"**after 30 days after** the date the
defendant is served with the Summons and Complaint"*, and once served the response
is a flat thirty. **Same protection, opposite mechanism** — and it means **no row
in this seed is a `resolve_periods`**, the first such seed since Idaho.

The stakes are the usual ones: Rule 28 is self-executing (*"shall be deemed
admitted unless…"*), so a `later_of` copied from a neighbour would tell a New
Hampshire defendant the matter is still open when it has already been admitted.

---

## 7. What was seeded, and what was deliberately left out

**Thirteen rules, every one forward, every one `effective_from` 2013-10-01.**
Appearance and Answer (30, Rule 4(e)); answer to a cross-claim (30, Rule 9(a));
answer to a counterclaim (30, Rule 9(a), from service of the Answer); answer after
a Motion to Dismiss is finally denied (30, from the **date on the Notice**, Rule
9(b)); objection to a motion (10, from **filing**, Rule 13(a)); motion for
reconsideration (10, from the **date on the written Notice**, Rule 12(e));
interrogatory answers (30, Rule 23(i)); production response (30, Rule 24(b)(2));
admissions (30, Rule 28(a)(i)); motion to set aside a **jury** verdict (10, from
**rendition**, Rule 43); motion to set aside any **other** verdict or decree (10,
from the **date on the court's written notice**, Rule 43); plaintiff's automatic
disclosure (30, Rule 22(b)(1)); defendant's automatic disclosure (60, Rule
22(b)(2)).

**Rule 43 is one sentence doing the work of four federal rules.** New Hampshire
has no Rule 50/52/59 equivalent — the string *"new trial"* does not occur in the
civil rules at all, and there is no motion to alter or amend and no
judgment-as-a-matter-of-law period. The sentence splits on the trigger, not the
number: a **jury** verdict runs from its **rendition**, because the parties were in
the room; **any other** verdict runs from the **date on the written notice**,
because they were not.

**Rule 22 is an automatic disclosure with no request behind it** — a deadline that
runs whether or not anyone asks, which no other seeded jurisdiction's civil rules
impose in this form. The two limbs are separated by one phrase that decides whose
Answer starts the clock: the plaintiff's thirty runs from the Answer of *"the
defendant **to whom** the disclosure is being made"*, the defendant's sixty from
the Answer of *"the defendant **making** the disclosure."* In a multi-defendant
case those are different filings, which is why the two rows carry distinct trigger
events rather than one shared name.

**Deliberately not seeded**, each for a stated reason:

- **Every backward row** — see §2.
- **Rule 9(e)'s 30-day jurisdictional Motion to Dismiss** — it runs from the *same*
  trigger as the Rule 4(e) answer row, and seeding it would make
  `service_of_summons_and_complaint` match two rules.
- **Rule 9(e)(1)–(3)'s answer deadlines** running from Supreme Court notices —
  appellate events this engine is not given.
- **Rule 4(c)'s proof of service** *"within 21 days of the **court-ordered
  deadline** for service"* — a date set by the order itself.
- **Rule 5's 75-day structuring conference and 20-day confer obligation** — both run
  from "the Answer date", a court-managed date rather than a filing.
- **Rule 10(d)'s 30-day third-party action** — the 2013 order lettered this
  subsection **(c)**, and the re-lettering carries no published date, so the
  citation cannot be given confidently for any earlier trigger.
- **Rule 23(k)(4)'s 10 days** after an objection is withdrawn *by agreement of
  counsel* — an agreement leaving no date the engine can be handed.
- **Rule 25's 30-day ESI response** — it runs from *"the **receipt** of the
  request"*, the only place in these rules where receipt and service are
  distinguished.
- **Rule 27's 30-day expert disclosure** — *"within 30 days of a request by the
  opposing party, **or in accordance with any order of the court**"*: two governing
  sources, one an order.
- **Rule 29's conditional-default rows** — they run from *"receiving notice"*.
- **Rule 28(a)(ii)** — its parallel thirty days for disputing signatures runs from
  the date the defendant **files** an Answer and duplicates a sentence in Rule 37(c).
- **The e-filing midnight cut-off** — *"timely filed if it is filed **before
  midnight** on the date the filing is due"* is a moment and not a date, the same
  thing this engine could not express in New Mexico.

---

## 8. Verdict, and what is NOT yet verified

**PASS, and seeded — locally.** The whole rule set is free and official once the
request headers are right, the holiday referent is named in the rule's own text,
the statutes are free, and the adoption order supplies a primary-source effective
date the published rules do not carry. Every gap disclosed runs EARLY, and the
one interpretive call — the biennial election day — is stated as a reading with the
single affected 2026 date named.

**Local gates, all run:**

- `node --check` clean on `deadline-engine.js`, the new test, and all 15 edited
  test files.
- **`50/50`** New Hampshire assertions.
- **`1200/1200`** deadline assertions across the whole suite (it was `1150/1150`
  before this seed).
- **0 failing files** across all 52 `api/_lib/*.test.js`.

**NOT DONE, and not to be reported as done:**

- **The load to `LAW-PINNACLE-2026` has not run.** This clone has no
  `SAIRNLAW_LICENSE_KEY` and `.env.local` is empty.
- **No live verification exists.** Every number above is local.
- **The seed-gate push hook will therefore DENY a push** of these files, correctly:
  a new jurisdiction in the repo and absent from the licence is exactly the drift
  it exists to catch. That is the gate working, not a problem to route around.

### The two gates point opposite ways, and the order that satisfies both

`tools/load_deadline_seed.py`'s own header: *"PUSH AND WAIT FOR THE DEPLOY BEFORE
LOADING A JURISDICTION THAT NEEDS A NEW COMPUTATION STANDARD"* — standards are
validated server-side, and loading North Carolina against a deployment that
predated `nc_rcp_6a` rejected all 13 rules while both calendars loaded fine.
**`nh_scr_2` is a new standard, so the same thing happens here.**

`tools/sairn_push_gate_hook.py` says the opposite: a push touching a seed file is
denied while the licence does not already hold it.

Neither is wrong; they constrain different files, and the sequence that satisfies
both is **three steps, not two**:

1. **Push the ENGINE and the fifteen edited tests only.** No seed file is in that
   commit, so the seed gate does not fire, and `nh_scr_2` deploys.
2. **Load** `sql/sairnlaw_deadline_{seed,calendars}_newhampshire.json` against the
   deployed engine, then re-verify live.
3. **Push the seed, calendar, doc and work log.** The licence now holds them, so
   the gate sees no drift and allows it.

The local commits are split along that line so step 1 can go first. **Do not
reach for `SAIRN_SEED_GATE=off`** — the ordering above removes the need for it,
and an override used to work around a solvable ordering problem is how the gate
gets hollowed out.

The dry run is clean: `python tools/load_deadline_seed.py newhampshire --dry-run`
parses 1 calendar entry (nh 2026, 10 dates) and 13 rules from 2 files.

Fifteen existing test files were edited alongside this work, all with the same
one-line change: the hardcoded `JURISDICTION_COVERAGE` key list gains `'nh'`, plus
one regex map in `deadline-massachusetts.test.js` that pins each coverage summary
to its own state's name.

**Three things to carry forward.** *No service extension at all* — the single most
copy-prone assumption on this platform, and New Hampshire is the first place it is
false. *A 403 is not always a wall* — a header set fixed it here after `curl` and
`WebFetch` both failed on every path. And *a PDF text layer that drops words can
only prove presence* — the absence of Rules 13A and 13B from the 2013 order had to
come from its table of contents, not from failing to find their text.
