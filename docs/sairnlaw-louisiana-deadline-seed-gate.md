# Louisiana — deadline-seed source-availability gate

**Run 2026-08-26. Verdict: SOURCES PASS — but NOT SEEDABLE, and the blocker is
in the ENGINE CORE, not in a calendar. Louisiana is the first jurisdiction where
`isWeekend()` itself is wrong, and wrong in the LATE direction.**

Louisiana (~4.6M) is a **civil-law** jurisdiction with a Code of Civil Procedure
rather than rules of court. It was read fresh on the working assumption that
none of the accumulated pattern transfers — and that assumption paid off
immediately.

---

## 1. Sources — PASS

`legis.la.gov` publishes the **Code of Civil Procedure and the Revised Statutes**
free, officially, on plain `curl` (`Law.aspx?d=<id>`). Article and section text
carries its own Acts history, so `effective_from` is real per article.

Read verbatim: **C.C.P. arts. 5059, 1001, 1313, 1458, 1462, 1467** and **La.
R.S. 1:55**.

Navigation is a small ASP.NET search form (law body + article number) rather
than guessable URLs, so a browser is needed to *find* an article; once found, the
`Law.aspx?d=` URL is stable and `curl`-able.

**CURRENCY CAVEAT, disclosed rather than glossed.** The search page states:

> Laws have been updated through the **2025 First Extraordinary Session**. For a
> list of laws updated through the **2026 Regular Legislative Session**, click
> here.

So the served text **lags the 2026 Regular Session**, with a separate list of
2026 changes maintained elsewhere. Any seed must cross-check that list — the same
shape as Maryland's Rules Orders channel. Art. 5059 itself already shows
`Acts 2025, No. 250, §3`, so this area is actively amended.

## 2. THE BLOCKER — Saturdays are legal holidays in SOME PARISHES ONLY

**La. R.S. 1:55(A)(1)**, verbatim on the decisive passage:

> The following shall be days of public rest and legal holidays: **Sundays**;
> January 1, New Year's Day; **January 8, Battle of New Orleans**; the third
> Monday in January … the third Monday in February … **the day of Mardi Gras;
> Good Friday**; the last Monday in May … July 4 … **August 30, Huey P. Long
> Day**; the first Monday in September … the second Monday in October,
> Christopher Columbus Day; **November 1, All Saints' Day**; November 11 …; the
> fourth Thursday in November …; December 25 …; **Inauguration Day in the city of
> Baton Rouge**; **provided, however, that in the parish of Orleans, the city of
> Baton Rouge, in each of the parishes comprising the second and sixth
> congressional districts, except the parish of Ascension, and in each of the
> parishes comprising the fourteenth and thirty-first judicial districts of the
> state, the whole of every Saturday shall be a legal holiday** …

And **C.C.P. art. 5059(A)**:

> The last day of the period is included, **unless it is a legal holiday**, in
> which event the period runs until the end of the next day that is not a legal
> holiday.

**Put those together and the consequence is structural:**

- Art. 5059 rolls the last day **only if it is "a legal holiday."** It does
  **not** separately name Saturday or Sunday, as every common-law rule seeded
  does ("a Saturday, a Sunday, or a legal holiday").
- **Sunday IS a statewide legal holiday** under R.S. 1:55, so Sunday rolls
  everywhere.
- **Saturday is a legal holiday ONLY in the enumerated parishes** — Orleans, the
  city of Baton Rouge, the parishes of the 2nd and 6th congressional districts
  except Ascension, and the parishes of the 14th and 31st judicial districts.
  **Everywhere else in Louisiana, a Saturday is an ordinary day and a deadline
  landing on it does NOT roll.**

**This engine's `isWeekend()` returns true for both Saturday and Sunday, and
`rollOff()` rolls off both, unconditionally, for every jurisdiction.** For
Louisiana that would roll Saturday deadlines in the majority of parishes where
the law does not roll them — producing a date **LATER than the true deadline**.

That is the direction that misses a filing, and it is **not fixable in a calendar
file**: weekend handling lives in the engine core and is shared by all nineteen
seeded jurisdictions. This is the first jurisdiction where a core assumption of
the engine is affirmatively wrong.

**It is also geographic, like Massachusetts' Suffolk County and Alabama's Mardi
Gras — but those were both safe.** Omitting a county-only *extra* holiday runs
EARLY. Louisiana inverts it: the engine would be applying a holiday that does not
exist in most of the state, which runs LATE. **A coverage disclosure cannot fix a
LATE-direction error**, which is the standing rule this project has applied since
Kentucky.

### Three ways out, none chosen here

1. **Seed only the parishes where Saturday IS a legal holiday**, as a distinct
   jurisdiction code (e.g. `la-orleans`), and refuse the rest. Honest and
   buildable, but covers a minority of the state.
2. **Add a per-jurisdiction weekend flag to the engine** — something like
   `weekend_days` on the computation standard, defaulting to `[Sat, Sun]` and set
   to `[Sun]` for a statewide `la`. Correct, touches core code shared by every
   jurisdiction, and needs its own regression pass.
3. **Refuse Louisiana** and record why.

## 3. Art. 5059 — INCLUSION IS THE DEFAULT, which inverts every seeded state

> **C.** A half-holiday is considered a legal holiday. **A legal holiday is
> INCLUDED in the computation** of a period of time allowed or prescribed,
> **except when**: (1) It is expressly excluded. (2) It would otherwise be the
> last day of the period. **(3) The period is less than seven days.**

Every common-law rule seeded states an *exclusion* with conditions. Louisiana
states **inclusion** with three exceptions. Exception (3) reaches the same
arithmetic as a "less than seven days" exclusion, so the engine's existing
`short_period_exclusion_days: 7` would produce correct dates — **but the framing
matters for (1)**: "expressly excluded" is a **per-article opt-out** that
individual Code articles can invoke, which a standard-level flag cannot express.
Same shape as Minnesota's opt-*in*, mirrored.

**"A half-holiday is considered a legal holiday"** — and note this is the **exact
opposite of South Carolina**, whose Rule 6(a) says "A half holiday shall be
considered as other days and not as a holiday." Two states, one concept,
opposite answers, gated one day apart. It is not academic: R.S. 1:55 creates real
half-holidays in **Sabine and Vernon parishes** (Wednesday and Saturday, noon to
midnight).

**Art. 5059(D)** carves out a *different computation entirely* for administrative
appeals: legal holidays are **excluded outright** — not merely on short periods —
when seeking rehearing, reconsideration, judicial review or appeal of an
executive-branch agency decision, with named exceptions for the Departments of
**Revenue, Environmental Quality, and Insurance**. That is a second computation
standard living inside one article, and it must never be applied to ordinary
civil litigation.

## 4. Holiday list — statewide items no other jurisdiction has

Statewide, from R.S. 1:55(A)(1): **Battle of New Orleans (8 January)**, **Mardi
Gras** (movable, tied to Easter), **Good Friday**, **Huey P. Long Day (30
August)**, **All Saints' Day (1 November)**, and **Christopher Columbus Day**.

Two contrasts worth keeping:
- **Mardi Gras is STATEWIDE here**, where in **Alabama** it is a holiday in
  Baldwin and Mobile Counties only. Same festival, two states, different scope.
- **Good Friday is a full statewide legal holiday**, where **Wisconsin** had to
  add it by a bespoke clause in its time rule and **South Carolina** does not
  list it at all.

**No weekend-shift provision appears in R.S. 1:55** for holidays falling on a
Saturday or Sunday. Given that Sunday is itself a legal holiday and art. 5059(B)
cascades to "the subsequent calendar day that is not a legal holiday", the
cascade appears to do the work — but **no observed-date shift was found**, and
that is stated as an absence I looked for rather than a conclusion.

## 5. Periods — and two conditional ones the engine cannot see

- **Art. 1001 (Delay for answering)**, `Acts 2021, No. 174, eff. Jan. 1, 2022`:
  **21 days** after service of citation — **but 30 days if the plaintiff files
  and serves a discovery request with the petition.** That condition turns on
  *what the plaintiff did*, which the engine has no input for. Guessing 21 where
  30 applies computes **EARLY** (safe); guessing 30 where 21 applies computes
  **LATE**. So the two must be **separate rows with unmissable trigger names**,
  never one row with a default.
  Also **15 days** after an exception is overruled or referred to the merits, and
  **15 days** after service of an amended petition.
- **Art. 1458 (Interrogatories)**: **30 days** — **but 15 days in FAMILY LAW
  cases** (divorce, custody, support, community property and incidental
  matters), *unless* served with the original petition, in which case 30. A
  **domain-scoped period**, which no seeded jurisdiction has; it belongs in a
  separate domain, not in `civil-litigation`.
- **Art. 1462 (Production)**: **30 days**, with an exception in subparagraph
  (B)(2) that was **not read**.
- **Art. 1313 (Service by mail, delivery, or electronic means)**: service by mail
  is "complete upon mailing"; electronic service "complete upon transmission but
  is not effective and shall not be certified if the serving party learns that
  the transmission did not reach the party to be served." **No added-days
  provision appears in the text read.** If Louisiana genuinely has no
  service-extension analogue, that is itself a finding — but **it was not
  confirmed**, and it must be before any row is seeded.

**No 30/45 defendant floor appears** in the discovery articles read. The
common-law floor pattern seen in every other seeded state does **not** obviously
exist here — consistent with reading this jurisdiction fresh rather than by
analogy.

## 6. What was NOT determined

- **Art. 1467's response deadline for requests for admission** — the article text
  retrieved covers the form of answers and objections; the day count was not
  captured. Louisiana's admissions deadline must be read before seeding.
- **Art. 1462(B)(2)**'s exception to the 30-day production period.
- **Whether any Code article adds days for service by mail or electronic means.**
  Nothing in art. 1313 does. This is the single most important remaining read,
  because assuming "no extension" without confirming would be exactly the kind of
  inherited assumption this gate was run fresh to avoid.
- **Which parishes comprise the 2nd and 6th congressional districts and the 14th
  and 31st judicial districts** — needed for any parish-scoped approach, and note
  congressional districts are **redistricted**, so that membership is not stable
  over time.
- Whether the 2026 Regular Session list changes any of the above.

## 7. Verdict

**Sources PASS. Louisiana is NOT seedable today, and not for a source reason.**

The blocker is that **`isWeekend()` is wrong for most of Louisiana** — Saturday
is a legal holiday only in enumerated parishes, art. 5059 rolls only on "legal
holiday", and the engine rolls both weekend days everywhere. That produces
**LATE** dates in the majority of the state, and a LATE-direction error cannot be
shipped behind a disclosure.

**Next action:** decide between the three options in §2 — parish-scoped seeding,
a per-jurisdiction weekend flag in the engine core, or refusal. Option 2 is the
correct one and is the largest, because weekend handling is shared by all
nineteen seeded jurisdictions and would need a full regression pass.

**Before any of that**, finish the three unread items in §6 — particularly
whether any service extension exists at all.
