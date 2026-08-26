# Wisconsin — deadline-seed source-availability gate

**Run 2026-08-26. Verdict: PASS — the strongest source position of any state
gated, and it needs NO new engine mechanism. One structural finding must be
settled before seeding, and it is the dangerous kind.**

Wisconsin (~5.9M) is the next unseeded state after Maryland. Its civil
procedure is **statutory** (chs. 801–847), like North Carolina, which puts the
whole of it on the Legislature's own free site.

---

## 1. Sources — PASS, and this is the best case seen

Everything needed returns **HTTP 200 to plain `curl`**. No browser required, no
challenge, no paywall, no terms gate, no publisher redirect:

| What | URL | Method |
|---|---|---|
| Wis. Stat. § 801.15 (time) | `docs.legis.wisconsin.gov/statutes/statutes/801/15` | curl 200 |
| § 801.14 (service) | same chapter page | curl 200 |
| § 802.06 (answer) | `.../statutes/802/06` | curl 200 |
| §§ 804.08 / 804.09 / 804.11 (discovery) | `.../statutes/804/08` etc. | curl 200 |
| § 995.20 (legal holidays) | `.../statutes/995/20` | curl 200 |
| § 230.35(4)(a) (state office holidays) | `docs.legis.wisconsin.gov/document/statutes/230.35(4)` | browser (chapter page is paginated) |

Only one quirk: **§ 230.35 is long enough that the chapter page paginates and
subsection (4) is not on the first page.** The `/document/statutes/230.35(4)`
node returns it. Everything else was plain `curl`.

### Currency is CERTIFIED, with a date, in the page footer

Verbatim from the statutes pages:

> 2023-24 Wisconsin Statutes updated through **2025 Wis. Act 247** and through
> all Supreme Court Orders and Controlled Substances Board Orders filed before
> and in effect on **August 5, 2026**. **Published and certified under s.
> 35.18.** (Published 8-5-26)

That is a **statutory certification of currency with an as-of date on every
page** — stronger evidence than any other state gated. Missouri's revisor site
gives per-section version history; Maryland gives per-rule credits plus a
separate Rules-Order channel; Wisconsin certifies the whole corpus by statute.
Nothing here has to be cross-checked against a second source to establish
currency.

Per-section history is also printed (e.g. § 801.15's runs from Sup. Ct. Order,
67 Wis. 2d 585 (1975) through 2019 a. 30), so `effective_from` is real per row.

## 2. § 801.15 — the computation statute, verbatim

> **801.15(1)(a)** In this subsection, "holiday" means any day that is a holiday
> provided in s. 230.35 (4) (a) or a statewide legal holiday provided in s.
> 995.20 or both, and a full day on Good Friday.
>
> **801.15(1)(b)** Notwithstanding ss. 985.09 and 990.001 (4), in computing any
> period of time prescribed or allowed by chs. 801 to 847, by any other statute
> governing actions and special proceedings, or by order of court, the day of
> the act, event or default from which the designated period of time begins to
> run shall not be included. **The last day of the period so computed shall be
> included, unless it is a day the clerk of courts office is closed.** When the
> period of time prescribed or allowed is **less than 11 days**, Saturdays,
> Sundays and holidays shall be excluded in the computation.

### THE STRUCTURAL FINDING — two different tests in one subsection

**This is new, and nothing seeded does it.** § 801.15(1)(b) uses **two
different standards for two different jobs**:

| Job | Test |
|---|---|
| Does the **last day** roll? | **"a day the clerk of courts office is closed"** |
| Are **intermediate days** excluded (period < 11 days)? | Saturdays, Sundays, and "holiday" as defined in (1)(a) |

So the carefully-composed holiday definition in (1)(a) **does not govern the
rollover at all.** The rollover is a **courthouse-closure** test — the North
Carolina shape — while the exclusion is a **statutory-list** test. Every
jurisdiction seeded so far uses one basis for both.

**Why this matters, and which way it fails.** Wisconsin's clerks of circuit
court are **county** officers. If a clerk's office is open on a day that is on
the statutory list, then encoding the list for rollover rolls the deadline when
the statute would not — **LATE**, the direction that misses a filing. If a
clerk's office is closed on a day *not* on the list (weather, local closure),
omitting it reports **EARLY**, which is safe.

So there is a **dangerous-direction exposure here that must be resolved before
seeding**, unlike Missouri's and Massachusetts' gaps which were safe in every
reading. Three candidate resolutions, none chosen in this gate:

1. **Treat the union list as a proxy for closure and disclose the mismatch.**
   Defensible only if clerks in fact close on every listed day — which needs
   checking, not assuming. Note the 1985 Law Revision Committee Note says the
   Good Friday / Dec 24 / Dec 31 amendment "will **permit** clerks to close
   their offices at these times" — *permit*, not require, which is exactly the
   wrong word for this purpose and is the reason this cannot be waved through.
2. **Seed only rows whose periods are ≥ 11 days**, where the exclusion never
   fires, and disclose that the rollover basis is closure rather than the list.
   Reduces but does not remove the exposure — rollover still applies.
3. **Refuse Wisconsin rollover entirely** and compute unrolled dates with a
   disclosure. Safe but of little use.

**This is the one open question in an otherwise clean gate**, and it is a
lawyer's question about what "the clerk of courts office is closed" means when
a statewide list and a county office diverge.

### Short-period exclusion is ELEVEN days, with its own provenance

"less than 11 days" — so `short_period_exclusion_days: 11` (the field is
compared with a strict less-than, and 11 is the literal number). Matches
**Tennessee** and **Arizona**; **not** the 7 of NJ, NC, WA, MA, MO and WV
appellate. And Wisconsin explains itself, verbatim:

> **Judicial Council Note, 1986:** Sub. (1) is amended by extending from 7 to 11
> days the periods from which Saturdays, Sundays and legal holidays are
> excluded. The change conforms to that made in Rule 6 (a), F.R.C.P. in 1985.

That note is worth keeping: it shows the 7-vs-11 split across states is a
**vintage artefact** — states that tracked the 1985 federal amendment have 11,
states that kept the older text or later followed the 2009 restyling have 7.
Useful when gating the remaining states.

### Backward counting

§ 801.15(1)(b) speaks only of a period that "begins to run" from an act, event
or default. **No backward provision.** Backward stays blank, like NJ, NC, WA,
MA and MO.

## 3. Service — a FIFTH answer, but it reuses machinery the engine already has

Applying the standing habit (read the service rule before trusting the time
rule) — and here the habit pays off **in reverse**.

**§ 801.14(2)**, the service rule, verbatim on timing:

> Service by mail is complete upon mailing. Service by facsimile is complete
> upon transmission. Service by electronic mail is complete upon transmission,
> except if the sender receives notification or indication that the message was
> not delivered.

**No deeming provision, and no cutoff hour.** That is the opposite of Missouri,
where the cutoff lives in the *service* rule. Wisconsin puts it in the *time*
rule instead:

**§ 801.15(5)**, verbatim in full:

> Whenever a party has the right or is required to do some act or take some
> proceedings within a prescribed period after the service of a notice or other
> paper upon the party:
> **(a)** If the notice or paper is served by mail, **3 days** shall be added to
> the prescribed period.
> **(b)** If the notice or paper is served by facsimile transmission, by
> electronic mail, or by the electronic filing system under s. 801.18 and such
> transmission is **completed between 5 p.m. and midnight, one day** shall be
> added to the prescribed period.

**This is VIRGINIA's mechanism, not Missouri's.** The 5 p.m. clock decides **how
many days are added** (0 or 1), not when service was complete. So it maps
directly onto the existing `amount(method, ctx)` shape with `service_time`, and
**no new engine mechanism is required** — the completion standard built for
Missouri is not needed here.

Five states, five answers, none inheritable:

| State | Electronic service |
|---|---|
| Massachusetts | +3 days, in the time rule |
| Tennessee | service rule **deems** it mail → +3 |
| Missouri | +0 days, **trigger date moves** on a 5 p.m./weekend cutoff |
| Maryland | +0 days, no cutoff at all |
| **Wisconsin** | **+1 day if completed 5 p.m.–midnight, else +0** |

### A boundary ambiguity to disclose, not guess

Virginia's text is *"no later than 5:00 p.m."* / *"after 5:00 p.m."*, which puts
17:00 unambiguously in the zero bucket. Wisconsin says **"completed between 5
p.m. and midnight"**, and *between* does not settle whether 17:00 itself is
inside. Two consequences:

- **At exactly 17:00** the answer is genuinely unclear. Direction: reading it as
  inside adds a day (**later**); reading it as outside adds none (**earlier**).
- **A transmission after midnight but before 5 p.m.** — say 02:00 — is **not**
  "between 5 p.m. and midnight", so it adds nothing. Worth stating explicitly
  because a naive "after 5 p.m." implementation would add a day.

Also note Wisconsin adds **nothing** for a fax or e-mail sent at noon on a
Saturday, where Missouri would shift the trigger. The two states share a clock
and nothing else.

## 4. The holiday definition is a UNION of two statutes plus a bespoke day

§ 801.15(1)(a) composes its list from **three** sources. Both were read verbatim.

**§ 230.35(4)(a)** — state office closure days, nine plus a shift rule:

> the office of the agencies of state government shall be kept open on all days
> of the year except Saturdays, Sundays and the following holidays:
> 1. January 1. · 1m. The 3rd Monday in January … · 3. The last Monday in May …
> · 4. July 4. · 5. The first Monday in September. · 6. The 4th Thursday in
> November. · **7. December 24.** · 8. December 25. · **9. December 31.**
> · 10. The day following if January 1, July 4 or December 25 falls on Sunday.

**§ 995.20** — statewide legal holidays:

> January 1, the 3rd Monday in January …, the 3rd Monday in February …, the last
> Monday in May …, **June 19, which shall be the day of observation for
> Juneteenth Day**, July 4, the 1st Monday in September …, **the 2nd Monday in
> October**, **November 11**, the 4th Thursday in November …, December 25, **the
> day of holding the partisan primary election, and the day of holding the
> general election in November** are legal holidays. … **Whenever any legal
> holiday falls on Sunday, the succeeding Monday shall be the legal holiday.**

Neither list is a superset of the other — **the union is required**:

- Only in **230.35(4)(a)**: **December 24** and **December 31**.
- Only in **995.20**: 3rd Monday in February, **Juneteenth**, **Columbus Day**,
  **Veterans Day**, and **two election days**.
- Added by **801.15(1)(a)** itself: **a full day on Good Friday** — note that
  995.20 makes Good Friday only *"the period from 11 a.m. to 3 p.m. … for the
  purpose of worship"*, so the full-day treatment exists **only** for time
  computation. Encoding 995.20 alone would miss it.

**Shift is SUNDAY-ONLY in both.** 995.20: "Whenever any legal holiday falls on
Sunday, the succeeding Monday shall be the legal holiday." 230.35(4)(a)(10) is
narrower still — the day following only if **January 1, July 4 or December 25**
falls on Sunday. **No Saturday shift in either.** Third state running
(Massachusetts, Missouri, now Wisconsin) where carrying Virginia's or West
Virginia's both-ways shift across would invent a Friday holiday and roll LATE.

### Two derivation problems and a county-scoped one

1. **Election days are in the list.** The November general is derivable (Tuesday
   after the first Monday, even years) but the **partisan primary** date is set
   by statute and must be confirmed per cycle rather than guessed.
2. **County/city-scoped holidays**, same shape as Massachusetts' Suffolk County:
   995.20 makes the municipal election day a legal holiday **"in every 1st class
   city"** (Milwaukee), and lets **counties of 750,000 or more** (Milwaukee
   County) provide holidays by ordinance. A jurisdiction+year calendar cannot
   express either. Omitting them runs **EARLY** — safe — and gets the same
   `JURISDICTION_COVERAGE` treatment Massachusetts got.

## 5. Periods, read verbatim

**§ 802.06(1)(a)** — and it is the most branch-heavy answer rule seen so far:

- **20 days** after service of the complaint (default)
- **20 days** for a guardian ad litem, from appointment
- **20 days** to answer a cross-claim; **20 days** for a reply to a counterclaim
- **45 days** for **the state**, a state agency, or a state officer/employee/agent
- **45 days** where **a defendant is an insurance company**, or where **any cause
  of action is founded in tort** — verbatim: *"If a defendant in the action is
  an insurance company, or if any cause of action raised in the original
  pleading, cross claim, or counterclaim is founded in tort, the periods of time
  to serve a reply or answer shall be 45 days."*
- **10 days** after notice of the court's action if a § 802.06(2) motion is
  denied or postponed; **10 days** after service of a more definite statement

**The tort/insurer branch is the trap.** It turns on **what the claim is
about**, not on how or where service happened — a fact the engine has no input
for and cannot infer. Getting it wrong reports **20 days when the answer is
really due in 45**, i.e. **EARLY** — safe in direction, but badly wrong for a
user, and it would be the most commonly hit branch in practice since a large
share of civil filings sound in tort. It needs its own row with an unmissable
trigger name, exactly as Missouri's three § 55.25(a) branches got.

**Discovery — all three are 30 days with a 45-day defendant floor**, and unlike
Missouri there is no outlier:

- **§ 804.08(1)(b)**: *"within 30 days after the service of the interrogatories,
  except that a defendant may serve answers or objections within 45 days after
  service of the summons and complaint upon that defendant."*
- **§ 804.09(2)(b)1**: same construction, same 30/45.
- **§ 804.11(1)(b)**: same 30/45, and **silence ADMITS** — *"The matter is
  admitted unless, within 30 days after service of the request …"*

All three floors run from **service of the summons and complaint** — a
caller-supplied date, **not** a computed one. So Wisconsin does **not** hit the
Maryland chained-floor gap, and its `resolve_periods` rows are ordinary.

**§ 802.06(1)(b)** also imposes a **180-day stay** of all discovery on the
filing of certain motions. Not a deadline and not modelled, but it changes when
discovery periods can run at all and belongs in a row note.

## 6. Verdict

**PASS**, and the cheapest seed of any state gated: sources are free, official,
`curl`-reachable and **statutorily certified current with an as-of date**; the
service extension reuses Virginia's existing `amount(method, ctx)` machinery, so
**no new engine mechanism is needed**; and the discovery floors are ordinary.

**One thing must be settled before seeding**, and it is the only
dangerous-direction finding in the gate: § 801.15(1)(b) rolls the last day on
**"a day the clerk of courts office is closed"**, not on the holiday list, while
using the list only for the sub-11-day exclusion. Encoding the list for rollover
risks rolling **LATE** if any clerk's office is open on a listed day, and
Wisconsin's clerks are county officers. Three options are recorded above; none
is chosen here.

Secondary, both disclosable: the **"between 5 p.m. and midnight"** boundary at
exactly 17:00 is genuinely ambiguous, and the **Milwaukee city/county** holidays
cannot be expressed in a jurisdiction+year calendar (EARLY, safe).

**Not determined:** whether Wisconsin's clerks of circuit court publish closure
schedules, per county or centrally, which is what option 1 above turns on; and
the § 801.18 e-filing subchapter was not read beyond § 801.15(5)(b)'s reference
to it.
