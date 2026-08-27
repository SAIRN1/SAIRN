# Connecticut — deadline-seed source-availability gate

**Run 2026-08-26. Verdict: SOURCES PASS — NOT seedable in the shape this engine
models. Connecticut's primary pleading rule is a self-perpetuating CHAIN, not a
deadline from a trigger, and its rollover has no holiday basis at all.**

> ## UPDATE 2026-08-27 — PARTIALLY SEEDED, DELIBERATELY UNPROVISIONED
>
> The chain row is now seeded as
> `sql/sairnlaw_deadline_seed_connecticut.json` (one row, Sec. 10-8, trigger
> `filing_of_preceding_pleading`) with standard `ct_pb_63_2` in the engine.
> **No `ct` holiday calendar was created, so every Connecticut computation
> refuses `NOT_PROVISIONED` — on every date, not only on weekends, because
> `rollOff()` consults the calendar before it looks at the weekday.** That
> refusal is the hold on the rollover basis, enforced mechanically rather than
> by convention, and it is locked by `api/_lib/deadline-connecticut.test.js`
> (26 assertions) which **breaks if anyone loads a `ct` calendar**.
>
> Re-verifying this document against the PDF turned up **three things it did
> not record**, one of which cuts the other way from everything else here:
>
> 1. **§3 needs a caveat: the counting rule is in the APPELLATE chapter, and
>    that is a LATE-direction risk.** See §3a below. This is the only known
>    Connecticut exposure that fails in the unsafe direction.
> 2. **§5 is stronger than reported — it is now affirmative, not an absence.**
>    Sec. 10-13 states *"Service by mail is complete upon mailing."* See §5a.
> 3. **§4 missed a second early-direction limb** in Sec. 7-17: an e-filing
>    **system-outage** tolling provision. See §4a.
>
> §7's open items are unchanged and still block the calendar.

Connecticut (~3.6M). Rules of court are the **Practice Book**, adopted by the
judges of the Superior Court.

---

## 1. Sources — PASS, and the file is excellent

The Judicial Branch publishes the **OFFICIAL 2026 Connecticut Practice Book** as
a single free PDF on **plain `curl`**:

```
jud.ct.gov/Publications/PracticeBook/PB.pdf     200, 3.6 MB, 699 pages
```

It is a **real text PDF**, not a scan — fully extractable. Its first page reads
`OFFICIAL / 2026 / CONNECTICUT PRACTICE BOOK / (Revision of 1998)`, so the text
is current for this year. Every section carries its own amendment history
(e.g. Sec. 10-8: *"(Amended June 14, 2013, to take effect Jan. 1, 2014.)"*), so
`effective_from` is real per row.

`cga.ct.gov` publishes the General Statutes free on plain `curl` as well.

**This is among the cleanest source positions of any state gated.** Nothing here
is the blocker.

## 2. THE BLOCKER — Sec. 10-8 is a CHAIN, not a deadline

**Practice Book Sec. 10-8, "Time To Plead"**, verbatim in full:

> Commencing on the **return day** of the writ, summons and complaint in civil
> actions, pleadings, including motions and requests addressed to the pleadings,
> **shall advance within thirty days from the return day**, and any subsequent
> pleadings, motions and requests **shall advance at least one step within each
> successive period of thirty days from the preceding pleading or the filing of
> the decision of the judicial authority thereon** if one is required, except that
> in **summary process actions the time period shall be three days** and in
> **actions to foreclose a mortgage on real estate the time period shall be
> fifteen days**. The filing of interrogatories or requests for discovery shall
> not suspend the time requirements of this section unless upon motion of either
> party the judicial authority shall find that there is good cause to suspend such
> time requirements.

**This is not a deadline computed from a trigger. It is a rolling cadence.**

- The first step runs 30 days from the **return day**.
- Every subsequent step runs 30 days **from the preceding pleading** — or from
  the filing of the court's decision on it, where one was required.
- So the *n*th deadline depends on the *(n−1)*th **actual filing date**, which
  depends on the one before it, indefinitely.

**Every seeded jurisdiction computes ONE date from ONE caller-supplied trigger.**
Maryland's chained discovery floor was logged as the highest-stakes shape found
in any gate because *one limb* depended on another rule's output. **Connecticut's
entire pleading cadence is that shape, as the primary mechanism**, and it chains
without limit.

It is not unmodellable — a caller who supplies "the date of the preceding
pleading" gets a correct 30-day answer, and that is a legitimate row. But it must
be seeded as **"30 days from the preceding pleading"**, with a trigger named so
nobody mistakes it for "30 days from the return day", and with the readme saying
plainly that Connecticut has no single answer deadline to compute.

**Two domain-scoped variants** ride on the same sentence: **summary process = 3
days**, **mortgage foreclosure = 15 days**. Three days is short enough that any
intermediate-day rule would matter — except Connecticut has none (§3).

### The "return day" is a Connecticut-specific concept and was NOT read

The cadence starts from the **return day**, which in Connecticut is a date stated
in the writ rather than the date of service, and is fixed by statute (Gen. Stat.
§ 52-48, not read here). **It is not derivable from a service date**, so it must
be a caller-supplied input, and a seed must not silently equate the two.

## 3. Counting — calendar days, no exclusion at all

**Practice Book Sec. 63-2**, verbatim on the operative part:

> In determining the last day for filing any documents, **the last day shall, and
> the first day shall not, be counted. Time shall be counted by calendar, not
> working, days.** When the last day of any limitation of time for filing any
> document under these rules or an order of the court **falls on a day when the
> office of the clerk of the trial court or of the appellate clerk is closed, the
> document may be filed on the next day when such office is open.**

- **No intermediate-day exclusion exists**, and unlike Minnesota — where the
  absence had to be inferred from a days-are-days rule — **Connecticut states it
  affirmatively**: *"counted by calendar, not working, days."* So
  `short_period_exclusion_days` must be **absent**, and that is on the record
  rather than by inference.
- The first-day/last-day rule is the standard one, stated in reverse order.

## 3a. ADDED 2026-08-27 — that counting rule is in the APPELLATE chapter

**Sec. 63-2 sits under `RULES OF APPELLATE PROCEDURE`** (confirmed from the
running page header). §3 above quoted it as though it were the Practice Book's
general counting rule. It is the **only** counting rule in the book, which is a
different thing.

Measured on the extracted text, **de-hyphenated and whitespace-flattened** so
that `calen-\ndar` cannot hide a hit:

| Search | Hits in 699 pages |
|---|---|
| `first day shall` | **1** — Sec. 63-2, and nowhere else |
| `computation of time` | 0 |
| `computing any period` | 0 |
| `period of time prescribed` | 0 |
| `intermediate Saturdays` | **0** — confirms §3's no-exclusion finding |

**There is no trial-court day-counting provision in the Connecticut Practice
Book.** Two textual points argue Sec. 63-2 reaches a Superior Court filing
anyway: it governs *"any documents … under these rules or an order of the
court"*, and its own rollover sentence expressly names *"the office of the clerk
of the **trial court** or of the appellate clerk"*. **Neither is conclusive.**

**Why this matters more than the other open items:** if Sec. 63-2 does not
reach trial-court pleadings, the first-day/last-day convention applied to a
Sec. 10-8 deadline is **assumed rather than sourced**, and a wrong assumption
there computes **LATE** — the direction that loses a filing. Every other
disclosed Connecticut gap fails EARLY.

It is tolerable today **only because nothing computes**. It must be resolved
before a `ct` calendar is loaded, and it belongs alongside the closure schedule
as a calendar blocker rather than below it.

## 4. THE ROLLOVER HAS NO HOLIDAY BASIS — it is pure clerk's-office closure

Applying the standing weekend-coverage check from the Oklahoma gate — *if the
rule doesn't name Saturday and Sunday, does a holiday statute cover both,
everywhere?* — **Connecticut fails the premise of the question: there is no
holiday list in play at all.**

**The word "holiday" appears FIVE times in the entire 699-page Practice Book**,
and **none of the five is a definition or a computation rule**. Two are in the
Rules of Professional Conduct commentary about gifts; one is a juvenile-detention
provision; the other two are the clerk's-office provisions below.

**Sec. 7-17, "Clerks' Offices"**, verbatim on the operative part:

> …each clerk's office shall be open at least five days a week **except during
> weeks which include a legal holiday**. … **If the last day for filing any matter
> in the clerk's office falls on a day on which such office is not open as thus
> provided or is closed pursuant to authorization by the administrative judge …
> due to the existence of special circumstances, then the last day for filing
> shall be the next business day upon which such office is open.**

So the rollover test, in both the trial and appellate rules, is **"the clerk's
office is closed."** Not a holiday list. Not Saturday and Sunday by name.

**Consequences, and one of them is the Wisconsin problem:**

- **Weekends are handled correctly by accident of fact** — clerk's offices are
  closed Saturdays and Sundays, so `isWeekend()` produces the right answer. But
  the *basis* is closure, not the weekend as such.
- **Encoding Conn. Gen. Stat. § 1-4's holiday list for the rollover would be
  wrong in the LATE direction** if a clerk's office is in fact open on a listed
  day — precisely the hazard that left Wisconsin gated. Sec. 7-17 says offices
  close "during weeks which include a legal holiday" but **never says which days
  those are**, and the Practice Book supplies no list.
- **The correct basis is the Judicial Branch's own published court-closure
  schedule**, which makes Connecticut **ingest-not-derive**, like North Carolina,
  New Jersey, Maryland and Oklahoma.
- Sec. 7-17 adds a further **discretionary** limb — closure "pursuant to
  authorization by the administrative judge … due to the existence of special
  circumstances" — unknowable in advance, **EARLY**, disclosable.

## 4a. ADDED 2026-08-27 — a SECOND early-direction limb in Sec. 7-17

§4 caught the discretionary-closure limb and missed this one. Sec. 7-17,
continuing past the passage quoted above, verbatim:

> If a party is unable to electronically file a document because the court's
> electronic filing system is **nonoperational for thirty consecutive minutes
> from 9 a.m. to 3 p.m. or for any period of time from 3 to 5 p.m.** of the day
> on which the electronic filing is attempted, and such day is the last day for
> filing the document, the document **shall be deemed to be timely filed if
> received by the clerk's office on the next business day** the electronic
> system is operational.

Unknowable in advance, like the discretionary closure. It can only ever make a
real deadline **later** than a computed one, so omitting it reports **EARLY** —
safe, disclosable, not modelled.

Sec. 7-17 was last **amended June 12, 2025, to take effect Jan. 1, 2026**, and
carries a `HISTORY—2026` note; the text above is current-year, not inherited.

## 5. NO SERVICE EXTENSION FOUND ANYWHERE IN THE PRACTICE BOOK

Searched the full extracted text for `"days shall be added"`, `"shall be added to
the prescribed"` and `"additional time after service"` — **zero hits each.**

Every one of the nineteen seeded jurisdictions has an added-days-for-service
provision. **Connecticut appears to have none.** Sec. 10-13 governs the *method*
of service (delivery or mail) and says nothing about extending time.

**This is reported as an absence I searched for, not as a conclusion.** The
General Statutes were not searched for an equivalent, and that must be done
before seeding — because "no extension" is exactly the kind of assumption that,
if wrong, computes **EARLY** on every mailed period. Safe direction, but wrong.

## 5a. ADDED 2026-08-27 — §5 upgraded from an absence to an affirmative rule

Two things changed here.

**First, the search was re-run on de-hyphenated, whitespace-flattened text.**
§5's original search ran on the raw extraction, where a line-broken
`add-\ned` could have produced a false negative. It did not: `days shall be
added`, `shall be added to the prescribed`, `additional time after service`,
`three days shall be added` and `additional (three|five) days` all return
**zero hits** on the flattened text as well. §5's finding survives.

**Second, and better — Sec. 10-13 states the positive rule.** §5 said Sec.
10-13 "says nothing about extending time," which is true but sells it short.
Sec. 10-13, under `SUPERIOR COURT—PROCEDURE IN CIVIL MATTERS`, says:

> **Service by mail is complete upon mailing.** Service by electronic delivery
> is complete upon sending the electronic notice **unless the party making
> service learns that the attempted service did not reach the electronic
> address** of the person to be served.

So Connecticut does not merely fail to extend for mail — it **completes on
mailing**, mechanically Missouri's `service_completion` shape rather than a
missing `service_extension`. That is affirmative evidence, and it materially
lowers the risk that §5's absence is wrong.

The electronic limb's **negative condition** ("unless the party … learns that
the attempted service did not reach") is not knowable to an engine, and would
push completion — and therefore the deadline — **later**. Another **EARLY**,
disclosable gap.

**Still not closed:** the General Statutes were still not searched. But the
seeded row runs from the **filing** of the preceding pleading, not from service
of anything, so no service mechanism applies to it either way.

## 6. An e-filing cutoff that moves the FILING, not the deadline

Sec. 7-17, continuing:

> a document that is electronically received by the clerk's office for filing
> **after 5 p.m.** on a day on which the clerk's office is open, **or** that is
> electronically received … **at any time on a day on which the clerk's office is
> closed, shall be deemed filed on the next business day** upon which such office
> is open.

A **5 p.m. cutoff that shifts the effective filing date** — mechanically the same
as Missouri's service-completion rule, but applied to **filing** rather than
service. It does not change the *deadline date* this engine reports; it means a
filer has until 5 p.m. on that date rather than midnight. Worth a row note, not a
mechanism.

## 7. What was NOT determined

- **Gen. Stat. § 52-48 (return day)** — how the return day is fixed, which the
  entire Sec. 10-8 cadence hangs on.
- **Gen. Stat. § 1-4** (legal holidays) and whether anything ties it to court
  deadlines. On the Practice Book text, nothing does.
- **Whether the General Statutes contain a service extension** — the single most
  important remaining read, per §5.
- **The discovery response periods** — Secs. 13-6 (interrogatories), 13-9
  (production) and 13-22/13-23 (admissions) were located but not read.
- **The Judicial Branch's published court-closure schedule**, which is the actual
  operative artifact for the rollover.

## 8. Verdict

**Sources PASS — cleanly.** Official current-year Practice Book, free, plain
`curl`, text-extractable, with real per-section currency, plus free statutes.

**NOT seedable in the ordinary shape**, for two structural reasons, neither of
which is a source problem:

1. **Sec. 10-8 is a chain.** The pleading cadence runs 30 days from *the
   preceding pleading*, indefinitely — the Maryland chained-floor shape, but as
   the primary mechanism rather than one limb of a floor. Seedable only as
   "30 days from the preceding pleading" with an unmissable trigger name and a
   readme that says Connecticut has no single answer deadline.
2. **The rollover has no holiday basis.** It keys on clerk's-office closure, the
   Practice Book contains no holiday list, and encoding the statutory list
   instead would risk rolling **LATE** — the Wisconsin hazard. The operative
   artifact is the Judicial Branch's closure schedule, making Connecticut
   ingest-not-derive.

**Before any seeding**, resolve §7's first three items — especially whether a
service extension exists anywhere in the General Statutes.

## 9. ADDED 2026-08-27 — what was seeded, and what each open item now blocks

§8's "before any seeding" line was written as one gate. It is really **three
gates with different scopes**, and separating them is what made the chain row
seedable today without touching any of them.

**Seeded** — `sql/sairnlaw_deadline_seed_connecticut.json`, one row:

| | |
|---|---|
| `rule_id` | `ct-pb-10-8-advance-from-preceding-pleading` |
| `trigger_event` | `filing_of_preceding_pleading` — named at length so it cannot be read as `return_day` |
| `count` | 30 calendar days, forward |
| `computation` | `ct_pb_63_2` (new; `impl: frcp_6a`, **no** `short_period_exclusion_days`) |
| `effective_from` | `2014-01-01` — Sec. 10-8's own amendment line, a real per-rule date |

**Not seeded, and why:** the **return-day first step** (needs Gen. Stat.
§ 52-48, and the return day is not derivable from a service date); the
**summary-process 3-day and foreclosure 15-day variants** (real and quoted, but
this engine's `DOMAIN_LABELS` knows only `civil-litigation` and `appellate` —
held on a domain decision, not on any doubt about the text); discovery rows;
appellate rows; any backward row.

**No `JURISDICTION_COVERAGE` entry.** That table's text rides on *successful*
computations. Connecticut has none, so an entry would be unreachable — a
Guardian 0d dormant-code violation. It goes in the same change as the calendar.

**Which open item blocks what:**

| Open item | Blocks |
|---|---|
| §3a — does Sec. 63-2's counting reach trial-court filings? **(LATE risk)** | the `ct` calendar |
| §4 — the Judicial Branch court-closure schedule as the calendar's basis | the `ct` calendar |
| §7 — Gen. Stat. § 52-48, how the return day is fixed | the return-day row only |
| §5/§5a — a service extension in the General Statutes | **nothing seeded** — this row runs from a filing |
| domain vocabulary for summary process / foreclosure | the two variant rows only |

**The hold is mechanical, not documentary.** With no `ct` calendar,
`rollOff()` returns `NOT_PROVISIONED` before it ever checks the weekday, so
Connecticut refuses on **every** date. `api/_lib/deadline-connecticut.test.js`
asserts that on a Tuesday landing as well as a weekend one, and **fails if a
`ct` calendar is loaded** — so the Wisconsin hazard in §4 cannot be walked into
quietly by a future session.
