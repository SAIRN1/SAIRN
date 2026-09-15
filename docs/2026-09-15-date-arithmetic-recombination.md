# The date-arithmetic trap, recombined — and the class is closed

**2026-09-15 (Fourth).** A standing recombination pass over the date-arithmetic
defect class: three distinct shapes, each a different failure, each with a real
precedent in this repo.

**Result: the class is CLOSED in live code, with exactly one known-open
instance that was already recorded by somebody else.** Published because the
narrowing is the useful part — 356 raw hits down to 1 — and because a class
somebody will re-open a sweep on next month deserves the measurement written
down rather than re-derived.

---

## The three shapes, and why they are three and not one

| | Shape | What actually goes wrong |
|---|---|---|
| **1** | `new Date(...).toISOString().slice(0, 10)` | `toISOString()` is **always UTC**. Slicing the first ten characters gives the UTC calendar day, which for a contractor in Ohio is *yesterday* for five hours of every day |
| **2** | `+ n * 86400000` on a calendar unit | A civil day is not always 86,400,000 ms. Across a DST boundary the arithmetic and the calendar disagree by an hour, which rounds to a day |
| **3** | `a.date < b.date` on strings | Correct for ISO-8601, silently wrong for anything else, and **nothing in the comparison says which it got** |

They share a symptom — an off-by-one day — and nothing else. A single "date bug"
sweep that looked for one of them would have reported the platform clean.

---

## Shape 3 was closed first, by item 94, and that is why it is 3 hits

`api/_lib/calendar-date.js` already owns "what is a calendar date, and how do two
of them compare". Its own header records the measurement that justified it:
`isDate` was defined **fourteen times across `api/`, all byte-identical, and all
wrong in the same way** — validating the *shape* of a date rather than the date,
so `2026-02-31` passed and JavaScript silently repaired it into `2026-03-03`,
three days later.

Shape 3 now measures **3 hits, all in one file** (`sairnbuild.html`). The concept
has an owner, and eight `api/_lib/*` modules import it.

---

## Shape 2: 57 hits, narrowed to 5, and all five are correct

Raw ms-per-day arithmetic is **not** the defect — it is exact whenever both
operands are UTC instants, which is what a date-only string parses to. The
defect needs ms arithmetic **combined with a LOCAL calendar read**.

Narrowing to ms-arithmetic within three lines of `getDate()`/`getMonth()`/
`getFullYear()`/`toLocaleDateString`: **57 → 5.** Every one was then read by
hand, because a hit is a triage signal and not proof:

| Site | Verdict |
|---|---|
| `sairnfreedom.html:2593` — `Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())/86400000` | **Correct, and it is the canonical safe idiom** — take the local calendar fields, rebuild a UTC midnight, then divide |
| `stonedesk.html:35269-70` — AR aging buckets | **Correct.** `today` is `sdLocalToday()`, a local `YYYY-MM-DD`; `x.due` is the same shape; `new Date('YYYY-MM-DD')` parses as **UTC midnight**, so both sides are UTC and the subtraction is an exact multiple of a day. This is the money path and it is right |
| `sairncash.html:1125` — days until a tax due date | A duration between two *instants*. Can be off by one across a DST boundary; display-only countdown, not money and not a deadline |
| `stonedesk.html:39447` — `sdAgo(ts)` | Same shape, same conclusion: "x days ago" on a display |

`api/_lib/calendar-date.js`'s own `addDays` uses `t + n * DAY_MS` and is
**correct**, because `toMs` parses to UTC midnight and `format` reads back in
UTC. Nothing leaves UTC, so DST never applies. The idiom is not the bug; leaving
UTC is.

---

## Shape 1: 356 hits, narrowed to 1, and that one is already on record

| Filter | Hits |
|---|---|
| Whole repo | 356 |
| Excluding `archive/` and `docs/skill-backups/` | **13** |
| Excluding comments, tests and fixtures | **5** |
| Excluding sites where the source is already a UTC date-only value | **1** |

`archive/` accounts for **343 of 356**, which is why the raw number is useless.
It is excluded by the tier gate and by semgrep for the same reason, and any
future sweep of this class should exclude it before reporting a figure.

Of the 13: five are **comments describing the pattern**, and three of those say
*"replaces the bare `new Date().toISOString().slice(0,10)` call sites"* — they
are documentation of a fix that already happened. One is a test asserting the
Feb-31 repair. `roofing-safety.js:73` and `roofing-warranties.js:73` stay in UTC
end to end. `api/claude.js:190` is a per-day usage key, where a UTC window is
the right choice for a server-side limit. `api/legal-deadlines.js:887,915` are
`retrieved_at` provenance stamps.

**The one that is live and wrong is `api/sd-sub-data.js:61`** —
`const today = todayISO || new Date().toISOString().slice(0, 10)` in the
subcontractor compliance check, deciding whether a COI or licence has expired.

**It was already found, by somebody else, before this pass.** The
`SAIRN-BACKLOG.md` correction of 2026-09-02 states it and calls it correctly:

> *"They disagree on the clock. `sd-sub-data.js` defaults to the server clock
> (`nowISO().slice(0,10)`, UTC). The shared engine refuses to run without a
> caller-supplied `today`. **This one is not a tie** — the UTC default is the
> defect class fixed across nine SAIRNvet panels on 2026-09-01, and a
> contractor in Ohio gets a different answer than the server does for six hours
> of every day."*

So the pass found nothing new. **That is the result, and it is worth having:**
two independent routes — a whole-platform shape sweep, and a reviewer reading one
file — converged on the same single instance. That is the independence property
`docs/2026-09-13-cross-domain-disciplines.md` asks for, arrived at by accident
rather than design, for the second time today.

---

## No checker was built, and that is a decision rather than an omission

The obvious next move is a report-only checker for shape 1. It was not built:

- **It would report one row**, and that row is already recorded in two places.
- `packages/testint/`'s README states the consequence of a number nobody can
  act on: *"the moment a number exists somebody drives it to zero by the
  cheapest available route, which for a checker is switching it off."*
- The concept already has an owner. **The durable fix for this class is not a
  detector, it is `api/_lib/calendar-date.js` having eight importers instead of
  fourteen copies** — which is what closed shape 3 and what will close shape 1
  as `sd-sub-data.js` adopts the shared engine.

What this document is instead: the measurement, the narrowings that produced it,
and the exclusion (`archive/`) that a future sweep must apply before quoting any
figure from this class.

---

## What this does NOT claim

- **Not a proof of absence.** Three shapes were searched. A fourth — a timezone
  offset applied twice, a date stored in local time and read in UTC — is not
  covered, and a shape nobody looked for is not a shape that is absent.
- **The hand-reads are hand-reads.** Five shape-2 sites and five shape-1 sites
  were read in context. No test was written for any of them, and none was
  exercised against a real DST boundary.
- **`archive/` was excluded, not audited.** 343 hits sit there. They are not
  live code and they are not claimed to be clean.
