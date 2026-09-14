# Claim-provenance chain — design, not a build

**2026-09-13 (Hank).** Item 23, scoped to a real design and stopped there
deliberately. Three questions were open; this answers all three with evidence
and names what it would cost.

Skill used: **`sairn-decision-gate`** — premortem on each answer, and the
Bid/No-Bid question applied to the build itself.

---

## What the thing is

Every standing document on this platform states claims: *"the live licence has
two active owners"*, *"this column exists"*, *"53 Tier A resources have no
removal path"*. Today a claim carries, at best, a date and an author. **A
provenance chain would make each claim carry HOW it was established, and let a
reader mechanically distinguish a fact somebody measured from a fact somebody
repeated.**

The two proof cases are both from tonight and they fail in opposite directions,
which is why one mechanism has to cover both.

**Proof case 1 — a true claim that blocked a push, and nobody could tell whose
it was.** The push gate refused with *"MISSING_CONSTRAINT
rf_draws.rfdraw_released_not_negative — declared in sql/ and NOT present on the
live table."* It is a **correct** finding: the constraint really is in
`sql/sairnroofing_draws_schema.sql:104` and really is absent from the live
database. But it arrived attached to **my** push, which touched no roofing SQL,
and establishing that it was not mine took a `git log -S` and a read of somebody
else's commit. **The claim had no owner attached, so every session that trips it
pays the same cost again.**

**Proof case 2 — a claim whose strongest link is a human, not a tool.** The
schema snapshot cannot be derived by anything in this repo. It is produced by a
person running `sql/schema_snapshot_query.sql` in the Supabase editor and saving
the result. **Every schema claim on this platform rests on that one
human-attested link**, and a chain that cannot represent it cannot represent the
foundation the others stand on.

---

## Q1 — What freshness threshold counts as "live"?

**Answer: there is no single threshold, and picking one would be the wrong
shape. A claim is LIVE when the interval since its measurement is shorter than
the interval in which its subject can change — which is a property of the
SUBJECT, not of the clock.**

Evidence for rejecting a fixed number: the platform already has both extremes in
production.

| Subject | Changes when | A useful "live" window |
|---|---|---|
| live database schema | a human runs a migration, unannounced | **hours** — measured: a snapshot 43.3 hours old was already wrong about five tables |
| deployed code | on every push, several times an hour | **minutes** |
| criticality tier of a resource | a deliberate judgement, rarely | **weeks** |
| a standing lesson | when it is disproved | **no expiry; it is a rule, not a measurement** |

A single number that satisfied the schema case would declare tier claims stale
every day for no reason, and one that satisfied tiers would call a two-day-old
snapshot live — which is exactly the error that produced a wrong 89-table
never-run verdict.

**So the chain stores an interval per claim TYPE, and the default for an
unclassified type is "not live".** Failing closed matters here: a claim whose
subject nobody has classified is a claim nobody has thought about, and calling
it live by default is the same fail-open shape `CLAUDE.md` §PR 1.11 names.

**And the second half, which the schema incident proved is the one that
bites:** freshness is measured from **when the measurement was TAKEN**, never
from when it was written down or committed. `gate_column_check.py` read the git
commit date and reported a capture as 25 hours old when it was 43.3 — an
18.7-hour understatement, in the direction that makes stale data look current.
The chain must record the **observation instant**, separately from the recording
instant, and show both.

## Q2 — Does the chain need a human-attested link?

**Answer: yes, unavoidably, and the design is worse than useless without it.**

The schema snapshot is the proof. No tool in this repo can derive it — it
requires Supabase editor access no clone holds. Every downstream schema claim
(`sairn_sql_preflight`, `gate_column_check`, `schema_snapshot_freshness`, push
gate check 3) rests on a link only a person can make. A chain that only
represents tool-derived links would have to either **omit its own foundation**
or **silently present a human attestation as machine-derived**, and the second
is a fabrication.

**What an attested link must carry, and the standard is already set by the
quarantine ledger and the criticality tiers:** WHO, WHEN THE OBSERVATION WAS
MADE (not when it was typed), WHAT WAS OBSERVED in words a reader can check, and
— the part that makes it honest — **HOW SOMEBODY ELSE COULD REDO IT**. An
attestation with no reproduction path is an assertion with a name attached.

**The premortem on this, because it is the most abusable part of the design:**
*"a year from now, an attested link turned out to be wrong and nobody caught
it — why?"* Because attestation became the cheap path. If a tool-derived link is
harder to produce than typing a sentence, the chain fills with sentences.

**Two guards, both cheap.** An attested link **expires** on the same per-type
interval as a measured one — it is a measurement, not a rule, and it decays the
same way. And an attested link that a tool **could** have produced is reported
as a downgrade: if `schema_snapshot_freshness` can answer the question, an
attestation saying the same thing is weaker evidence, not equal evidence.

## Q3 — Universal scope, or Tier A only?

**Answer: Tier A only, and the number is why.**

Measured: **382 registered resources, ~~78 Tier A~~ → 80 Tier A.** Universal scope means
provenance on 382 subjects, most of which are Tier B operational data and Tier C
preference stores where the consequence of a stale claim is somebody refreshing
a screen.

**The argument against universal is not cost, it is dilution.** A chain covering
everything gets skimmed. The platform already has the worked example: the
testability gate flagged **70% of the requirements corpus** on its first run and
the honest reading was miscalibration, not 123 junk requirements — a signal that
covers everything carries no information. Tier A is ~~78~~ 80 subjects, each already
carrying evidence in `docs/CRITICALITY-TIERS.md`, and a reader can hold that.

> **Both counts corrected 2026-09-14 (fourth), and the drift is the design
> working rather than the design decaying.** `78` was true as written on
> 2026-09-13. The commit *"feat(sairnbiz): the three-way match's own two
> documents reach a server"* tiered two more resources A, and because scope is
> derived from the register rather than from a second list, those two entered
> the chain with nothing to keep in step — which is exactly what the escape
> hatch below promises. Read 2026-09-14: `python tools/claim_provenance.py
> scope` reports 80, and an independent `awk -F'|'` count of column 3 in
> `docs/CRITICALITY-TIERS.md` agrees at 80. Two structurally different readers,
> not one read twice. **The figure has a tense and will drift again — re-read
> it, do not cite this line.**

**Confirmed rather than assumed, which is what was asked.** Two things make Tier
A the right boundary beyond its size: the tier register **already exists and is
already maintained per resource**, so the scope needs no new taxonomy; and Tier
A is defined as money, regulated data, or a documented incident — which is
exactly the set where "somebody repeated this and nobody re-measured it" is
expensive.

**The disclosed cost of choosing it:** a wrong claim about a Tier B resource
will go unchecked by this mechanism, and that is accepted rather than hidden.
The escape hatch is that the tier register is the scope definition, so promoting
a resource to Tier A automatically brings it into the chain — no second list to
keep in step.

---

## What it would cost to build, honestly

**Not small, and the largest part is not the code.** The mechanism is perhaps a
session: a claim record (subject, type, observation instant, method, author,
reproduction path), a per-type freshness table, and a checker that reports claims
whose interval has lapsed. **The expensive part is that ~~78~~ 80 Tier A subjects need
their current claims located and classified**, and most of them live in prose
inside `docs/SAIRN-OPEN-WORK-INDEX.md` rather than in any structured field.

**And the same blocker that stopped items 2 and 4 applies here, which is the
strongest argument for designing before building.** Both of those tools are
finished and both report an honest zero, because the data they need was never
captured: the defect register has 1 of 52 records with
`detection_method = independent-review`, and 0 of 52 with a rules citation.
**A provenance chain built before claims carry provenance would be the third
tool waiting on an input nobody is producing.**

**The recommendation: build the RECORDING side first and the checking side
second.** Make it possible — and then required — for a Tier A claim to carry its
provenance when it is written, and let the chain accumulate for a fortnight
before anything measures it. That is the same order the flaky-checker ledger
needed and did not get: it shipped able to judge and had nothing to judge, and
three measurement passes in a row produced TOO-FEW-RUNS.

---

## What this design does NOT settle

- **Whether a chain link can be revoked**, and what happens to everything
  derived from it. The Ariane case in disciplines item 7 is the shape: a link
  that was valid under one set of conditions and is not under another.
- **How to represent a claim derived from two sources sharing no mechanism** —
  the strongest evidence this platform produces (a schema absence AND a live
  503) and the one the chain most needs to be able to say.
- **Whether the chain itself needs a provenance chain.** It does, and the
  regress has to stop somewhere; naming where is a decision, not a derivation.

---

## BUILT — 2026-09-14 (fourth), the recording side only

`tools/claim_provenance.py`, commit subject *"feat(provenance): item 23
recording side -- and a second subject kind that only running it exposed"*. The
recommendation above was followed exactly: **it records and deliberately does
not judge.** The ledger is `docs/claim-provenance.json`, 3 records as of
2026-09-14T17:44Z. The checking side is not built.

### What USING it found that reading the design would not have

**The first real claim anybody tried to record had no valid subject.** It was
*"this migration was run and verified"* — and Q3's answer derives scope from the
**resource** register, so there was no legal way to name it. The type
`migration-run` already sat in the tool's own freshness table describing the
human-attested foundation the whole chain rests on (Q2), **with nothing it could
legally be about.** That is an inconsistency between Q2 and Q3 that survived
being designed, reviewed and written down, and it took about a minute of actual
use to surface.

**The fix, and what it deliberately is not.** A second subject kind,
`migration:<file>.sql`, whose filename must name a real file in `sql/`. It is
**not** widened to free text: Q3's dilution argument is right and a chain
covering everything gets skimmed. The filename is still derived from the repo,
so there is still no second list to keep in step — the same discipline as the
tier register, applied to a different source.

### Q3 is amended, not overturned

Scope is still Tier A only for resources. But **"Tier A only" was stated as if
the tier register enumerated every namable thing, and it does not** — it
enumerates resources. A claim can be about an *event* (a migration ran) as well
as about a *resource*, and the design had no vocabulary for the first even
though Q2 made one the foundation. Read the two answers together before adding
a third subject kind.

### What was verified, by use rather than by reading

- Refusal path: `migration:` naming a file absent from `sql/` → exit 1, nothing
  written.
- Two `measured` records (`mech_credentials`, `sen_payer_contracts`) from
  `tools/schema_snapshot_freshness.py`.
- One `derived` migration record, **scoped to the two `CREATE TABLE`s it can
  actually evidence** — table presence does not evidence columns, grants or
  indexes, and it says so in the record rather than overclaiming.
- The attestation downgrade branch — named above as the most abusable part —
  exercised against a throwaway ledger, so the most abusable path is not also
  the untested one.

**The observed/recorded gap is already earning its place.** All three records
carry `observed_at 2026-09-13T18:39:55Z` against `recorded_at 2026-09-14T17:44Z`
— a 23-hour gap. Stamping "now" as the observation instant would have erased it,
in the same direction as the 18.7-hour understatement this design cites.

### Still not settled, and this build did not touch it

All three items above remain open. **A fourth is added by having built it:** the
checker cannot be written against 3 records. The recommendation says let the
chain accumulate for a fortnight, so the earliest honest date for the checking
side is **2026-09-28**, and building it sooner reproduces the exact failure
(items 2/24 and 4) this order exists to avoid.
