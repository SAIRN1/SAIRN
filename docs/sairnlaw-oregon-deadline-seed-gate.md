# Oregon — deadline-seed source-availability gate

**Run 2026-08-26. Verdict: PASS. The Council-on-Court-Procedures wrinkle is
REAL, but it is a CURRENCY problem with a known answer, not a source problem.
And Oregon's Rule 10 expressly answers the Maryland ambiguity this project
logged as an open decision two days ago.**

Oregon (~4.3M). Checked the Council question first, as flagged in advance.

---

## 1. The Council on Court Procedures — the wrinkle is real

Oregon's civil rules are **not promulgated by the Supreme Court**. The **Council
on Court Procedures**, a statutory public body, drafts and promulgates the ORCP;
its promulgations are then **submitted to the Legislative Assembly, which may
amend or repeal them**, and they take effect as law on the following 1 January.

That two-stage lifecycle is visible in the rules' own citation lines. ORCP 10's:

> `[CCP 12/2/78; §C amended by CCP 12/13/80; §A amended by CCP 12/10/88 and
> 1/6/89; §A amended by 2002 s.s.1 c.10 §9; §A amended by CCP 12/6/14 and 2015
> c.212 §8; §B amended by CCP 12/6/14 and repealed by 2015 c.212 §4; §C amended
> by CCP 12/6/14 and amended and redesignated §B by 2015 c.212 §6]`

**Two amending authorities in one history** — "CCP" (Council) and session laws
("2015 c.212"). No other seeded jurisdiction has this.

**And the Council's own site says its copy is not authoritative**, verbatim from
`counciloncourtprocedures.org/the-orcp/`:

> Please note that **the first link is static and may not include the most recent
> Council amendments nor amendments by the Legislature.** Links to Council
> amendments and information about legislative updates are provided on this page,
> and should be consulted to learn the current language of any affected rules.

Its static copy is labelled **"ORCP – Effective January 1, 2020"**, its
"Amendments Made By Oregon Legislature" section is **empty and pending**, and its
own news page records **2024 promulgations** (Rules 1, 14, 39, 55 and a new Rule
35) that the ORCP page does not reflect.

**So: do NOT use the Council's static copy as the rule text.** The Council page
itself points to the authoritative one —
`oregonlegislature.gov/bills_laws/SiteAssets/ORCP.html`, a single ~1.1 MB HTML
file of the whole ORCP, **HTTP 200 on plain `curl`**. That is what was read here.

**Standing consequence for any Oregon seed:** the Legislature's file is the
text, and the Council's promulgation record is the *forward* channel — it shows
what will become law next 1 January before the Legislature's copy reflects it.
Both must be checked, in that order. Same two-channel shape as Maryland's Rules
Orders, arrived at for a completely different structural reason.

## 2. Sources — PASS

| What | URL | Method |
|---|---|---|
| **ORCP, entire, current** | `oregonlegislature.gov/bills_laws/SiteAssets/ORCP.html` | **curl 200** (~1.1 MB) |
| ORS 187.010 / 187.020 | `oregonlegislature.gov/bills_laws/ors/ors187.html` | **curl 200** |
| Council promulgation record | `counciloncourtprocedures.org/the-orcp/` | curl/browser 200 |

Free, official, no gate. Per-rule citation lines give real `effective_from`.

## 3. ORCP 10 A — verbatim, and it is unusually well-drafted

> **A Computation.** In computing any period of time prescribed or allowed by
> these rules, by the local rules of any court, or by order of court the day of
> the act, event, or default from which the designated period of time begins to
> run shall not be included. The last day of the period so computed shall be
> included, **unless it is a Saturday or a legal holiday, including Sunday**, in
> which event the period runs until the end of the next day that is not a
> Saturday or a legal holiday. **If the period so computed relates to serving a
> public officer or filing a document at a public office, and if the last day
> falls on a day when that particular office is closed before the end of or for
> all of the normal work day**, the last day shall be excluded … in which event
> the period runs until the close of office hours on the next day the office is
> open for business. When the period of time prescribed or allowed **(without
> regard to section B of this rule)** is **less than 7 days**, intermediate
> Saturdays and legal holidays, including Sundays, shall be excluded in the
> computation. As used in this rule, "legal holiday" means legal holiday **as
> defined in ORS 187.010 and 187.020**. This section does not apply to any time
> limitation governed by **ORS 174.120**.

### It does NOT have Louisiana's problem — and the drafting is why

Oregon names **"a Saturday or a legal holiday, including Sunday."** Saturday is
named **separately**, and Sunday is expressly folded **into** the holiday
definition. So even though ORS 187.010(1)(a) makes "Each Sunday" a legal holiday
— the same statutory quirk Louisiana has — **Oregon's rule rolls off Saturday in
its own right**, statewide.

**This engine's `isWeekend()` is therefore correct for Oregon.** Worth stating
explicitly, because Louisiana was gated one step earlier on exactly this and the
statutes look superficially alike. The difference is entirely in how the
*procedural rule* is drafted, not in the holiday statute.

### ORCP 10 A EXPRESSLY ANSWERS THE MARYLAND OPEN DECISION

Two days ago the Maryland gate logged an unresolved ambiguity — whether adding 3
mail days to a ≤7-day period converts it into a >7-day period and so kills the
intermediate-day exclusion. No committee note or authority was found, and it was
logged as **"ship DISCLOSED, do not guess."**

**Oregon settles the identical question in its own text:** the threshold applies
to the period *"**(without regard to section B of this rule)**"* — section B
being the service extension. **The 7-day test is measured on the underlying
period, BEFORE the 3 days are added.**

That does not decide Maryland — different state, different rule — but it is a
real data point that the question is a known one, that at least one drafter saw
it coming, and **which way that drafter resolved it**. It belongs in the Maryland
decision row as persuasive material for whoever answers it.

### Other fields

- **Short-period exclusion at seven** — `short_period_exclusion_days: 7`.
- **Holiday basis is an express cross-reference to BOTH ORS 187.010 and
  187.020** — the enumerated list *and* the appointed-days section. Most states
  name one; Oregon names both.
- **A public-office-closure limb**, and it is **broader than any seen**: it fires
  when the office is closed *"before the end of **or for all of** the normal work
  day"* — so a **partial-day** closure counts. Unknowable in advance, and it is
  **additional to** the Saturday/holiday rollover rather than a replacement, so
  omitting it reports **EARLY**. Disclosable.
- **A carve-out to check: "This section does not apply to any time limitation
  governed by ORS 174.120."** Not read; must be before seeding.
- **No backward provision.** Backward stays blank.

## 4. ORCP 10 B — the broadest service enumeration yet, and the scope stated outright

> **B Additional time after service by mail, e-mail, facsimile communication, or
> electronic service. Except for service of summons**, whenever a party has the
> right to or is required to do some act within a prescribed period after the
> service of a notice or other document upon that party and the notice or
> document is served by **mail, e-mail, facsimile communication, or electronic
> service, 3 days shall be added to the prescribed period**.

- **All four methods get +3** — mail, e-mail, fax and electronic service. That is
  the Massachusetts pattern (the time rule granting it directly) with the widest
  enumeration encountered. Eighth distinct answer on electronic service.
- **"Added to the prescribed period"** → period-lengthening, like NJ, NC, WA, NY,
  VA, MA, MO, MN and SC, and **not** Alabama's federal after-expiry order.
- **"Except for service of summons" is stated in the rule itself.** Every other
  seeded state required inferring the Rule 4 / Rule 5 scope split from which rule
  authorises the service. Oregon says it outright, which removes the single most
  repeated inference in this whole engine.

## 5. ORS 187.010 — and one drafting detail worth copying

Eleven days: **Each Sunday**; January 1; third Monday in January (MLK); third
Monday in February (Presidents Day); last Monday in May (Memorial); **June 19
(Juneteenth)**; July 4; first Monday in September (Labor); November 11
(Veterans); fourth Thursday in November (Thanksgiving); December 25.

**No Columbus Day or Indigenous Peoples Day** — unlike Alabama, South Carolina,
Louisiana, Minnesota, Missouri, New Jersey, Virginia and Massachusetts. Oregon
simply does not have that October holiday.

**The shift is both ways, with a careful carve-out:**

> (2) Each time a holiday, **other than Sunday**, listed in subsection (1) falls
> on Sunday, the succeeding Monday shall be a legal holiday. Each time a holiday
> listed in subsection (1) falls on Saturday, the preceding Friday shall be a
> legal holiday.

**"Other than Sunday" is load-bearing** — without it, every Sunday would make the
following Monday a holiday, because Sunday is itself item (1)(a). A generator
that applies a blanket Sunday-shift to this list would produce 52 spurious
Monday holidays a year. This is the kind of self-referential trap that only
appears where the weekend is *inside* the holiday list.

Being both-ways, it **will spill across the year boundary**, so the generator
must compute a wider span than it emits — the property Minnesota's own assertion
caught.

**ORS 187.020** adds: every day appointed by the Governor, and every day
appointed by the President **only when the Governor also appoints it**. Ad hoc
and unknowable → **EARLY**, disclosable. Note the conjunctive condition: a
presidential day alone is *not* an Oregon legal holiday.

## 6. Periods — and Oregon has NO INTERROGATORIES

- **ORCP 7 C(2)**: *"the defendant shall **appear and defend within 30 days** from
  the date of service."* If served by publication, 30 days from the date stated in
  the summons, which is the date of first publication. Note the phrasing is
  "appear and defend", not "file an answer".
- **ORCP 43 B (production)**: **30 days**, with a defendant floor — no production
  may be required *"before the expiration of **45 days** after service of
  summons, unless the court specifies a shorter time."*
- **ORCP 45 B (admissions)**: **30 days**, defendant floor **45 days**, and
  **silence ADMITS**. Rule 45 A additionally requires the request to carry a
  capital-letters warning: *"FAILURE TO SERVE A WRITTEN ANSWER OR OBJECTION
  WITHIN THE TIME ALLOWED BY ORCP 45 B WILL RESULT IN ADMISSION OF THE FOLLOWING
  REQUESTS."* — the same mandatory-warning device Missouri's R. 59.01(a)(1) has.
- **THERE ARE NO WRITTEN INTERROGATORIES IN OREGON CIVIL DISCOVERY.** Searching
  the entire ORCP for "interrogator" returns **four** hits, and **all four are
  jury interrogatories** under Rule 61 C (general verdict accompanied by answers
  to interrogatories). There is no discovery-interrogatory rule at all.

  **Every other seeded state has an interrogatory row. Oregon must have none, and
  that is the law rather than an omission** — it needs saying in the seed readme,
  because an absent row otherwise looks like unfinished work.

Both discovery floors run from **service of the summons** — a caller-supplied
date — so Oregon does **not** hit the Maryland chained-floor gap.

## 7. Verdict

**PASS, and nothing is blocked.** Sources free, official and `curl`-reachable;
real per-rule currency; the rollover names Saturday separately so the engine's
weekend handling is correct; the service extension is ordinary period-lengthening
that existing machinery covers; and every unmodelled item fails **EARLY**.

Four things to get right when seeding:

1. **Take the text from the Legislature's file, not the Council's static copy**,
   and check the Council's promulgation record for what becomes law next 1
   January. Two channels, in that order.
2. **Seed NO interrogatory row**, and say in the readme that Oregon has none.
3. **Apply the Sunday shift only to holidays "other than Sunday"** — a blanket
   rule generates 52 phantom Mondays.
4. **Read ORS 174.120** before seeding, since ORCP 10 A expressly disapplies
   itself to time limitations governed by it.

And one item to carry sideways: **ORCP 10 A's "without regard to section B"
belongs in the Maryland decision row** as persuasive material on the identical
question Maryland leaves open.
