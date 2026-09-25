# Item 65, the acceptance half — does this look like real, lived-in data?

**Written 2026-09-25 (Hank).** This is the piece `docs/2026-09-14-backup-restorability-scoping.md`
sized as 65a/65b/65c/65d and did not size: **what a human decides when the
restore job exits 0.**

It is a CHECKLIST, deliberately, and not a tool — **that decision is argued in
the next section against the repo's current state, not inherited from the
scoping document.**

What both agree on, and what makes an exit code useless here, is one measured
fact — stated in the scoping document and independently in
`tools/restore_coherence_check.js`'s own header:

> `sairn_agents(id)` is **the only foreign key** across **459** declared tables.
> "Postgres will accept a partial restore without complaint. A restore that
> silently dropped half of `rf_draws` produces a database that starts, answers
> queries, and is wrong."

A restore that loses half its rows exits 0. A restore that loads a dump of the
demo licence exits 0. A restore that writes every table as an empty array exits
0. **The exit code is not a weak signal here — it is measuring a different
thing**, and no amount of tightening it will make it measure this one.

---

## Why this is not a tool, stated so nobody builds one by mistake

**Re-checked against the repo, not read off the 2026-09-14 scoping document —
which is a snapshot from before the tools it sizes were built the same day.**
The mechanical layer already exists and it is not small:

- **65a/65d are BUILT.** `tools/restore_coherence_check.js`, held by
  `tests/run_restore_coherence_probe.js` (26 arms). Point it at a database with
  two env vars; no scratch environment, no baseline capture.
- **The restore pipeline is BUILT and has NEVER RUN.**
  `.github/workflows/nightly-backup.yml` takes a dump, restores it into a
  throwaway Postgres, and runs 65a against the restored copy. It is blocked on
  Michael: `sql/backup_reader_role.sql` run as `postgres`, plus 10 GitHub
  secrets.
- **65b is NOT built, and it is the gap that matters here.**
  `restore_coherence_check.js` already accepts `--baseline
  db/row_count_baseline.json` — **and nothing on this platform writes that
  file.** The reader half exists; the writer half does not. Checked: the path
  does not exist and the only mention of it in the repo is the tool's own usage
  line.

So a second tool is not what is missing. What is missing is **the part no tool
does**: deciding whether what came back looks like a business. Writing a fresh
checker now would be the shape this platform has shipped five times and named —
**a tool able to judge with nothing to judge**, which passes clean on its first
run and is believed.

**If any of this rubric is ever automated, automate section 1 by building 65b**,
not by adding a seventh checker.

---

## The verdict has three states, and the middle one is the common one

| | |
|---|---|
| **ACCEPT** | every section below answered, and answered YES |
| **REJECT** | any section answered NO |
| **COULD NOT TELL** | any section could not be answered *(this is NOT an ACCEPT, and on this platform today it is the expected verdict — see §1)* |

A restore signed off as ACCEPT on five of six sections is a **COULD NOT TELL**.
Write which section, and why.

---

## 1. Volume plausibility — is there about as much as there should be?

**Ask:** for each restored table, is the row count within the range a person who
knows this business would expect?

**And the honest answer today is COULD NOT TELL, for every table.**
65b — "a recorded row-count baseline per table, taken on a cadence from
production" — **does not exist**, and the absence is sharper than it sounds:
`tools/restore_coherence_check.js` already takes `--baseline
db/row_count_baseline.json` and **nothing writes that file**. Without it there
is nothing to compare against, and comparing a restore only against itself is
the check that cannot fail. Do not substitute a guess. Record COULD NOT TELL
and name 65b — it is sized **S** with nothing blocking it.

**The two exceptions, which are genuinely answerable now:**

- **The audit chain**, which `restore_coherence_check.js` runs as its headline
  check. `sairn_audit_checkpoint` carries a daily digest over a closed window,
  chained to the previous one. Every window whose digest still matches restored
  byte-faithfully; the first disagreement names *when* the restore diverged, and
  its row count separates **LOST**, **GAINED**, and **the same count with
  different content** — three findings kept apart because they point at three
  different causes. This needs no baseline. It covers the audit tables and
  **nothing else** — do not let a green chain stand in for the other ~380.
- **Zero.** A table restored with zero rows that had rows yesterday is a NO
  without any baseline at all. An **append-only** table at zero is always a NO.

**What a NO looks like:** `rf_draws` at 4 rows when the business draws weekly
and the app has been live for months.
**What a sneaky NO looks like:** every table at a round number — 10, 50, 100.
That is a page limit, not a business.

---

## 2. Field variety — does the data vary the way a business varies?

**Ask, per table, on the columns that should differ between rows:**

- Does the **primary business column** (amount, status, name, date) take more
  than one distinct value?
- Is a **status column** spread across its real vocabulary, or is every row
  `Open`? A table where every invoice is `Paid` is either a very unusual month
  or a restore that dropped a column and defaulted it.
- Is a **money column** distributed across orders of magnitude, or is every
  amount the same, or a multiple of 100? (`tools/benford_check.py` already
  encodes the shape pre-check for this and **refuses** on corpora too small or
  too rounded to judge — read its refusal rather than its statistic.)
- Do **free-text** columns contain different lengths and different words?
- Is a column that should be **NULL sometimes** never NULL, or always NULL?

**The column list is available offline:** `db/schema_snapshot.json` carries
column names for **384** tables. It carries no types, no counts and no data — so
it tells you *which* columns to look at, never whether they are right.

**What a NO looks like:** `sv_controlled` restored with 600 rows in which
`drug` takes one value. A controlled-substance register with one drug in it did
not come from a practice.

---

## 3. Realistic values, or obvious placeholders?

**Ask:** would a stranger reading twenty random rows believe a business
generated them?

Look for, and treat each as a NO until explained:

- `test`, `foo`, `bar`, `example`, `asdf`, `TBD`, `xxx`, `Lorem ipsum`
- `@example.com`, `@test.com`, `555-0100` through `555-0199`
- sequential names — `Customer 1`, `Customer 2`, `Vendor A`, `Vendor B`
- every row created within the same second, or on the same date
- amounts that are all round hundreds
- **the demo licence.** `SD-PINNACLE-2026` and the **11** other
  `*-PINNACLE-2026` keys in `docs/2026-09-03-demo-credentials.md` (counted from
  that file, not quoted from anywhere) are real keys carrying **openly
  invented** data. A restore consisting mostly of demo-licence rows is a
  successfully restored **demo**, and it exits 0.

**The inverse trap, which is the harder one:** seed data on this platform is
written to look plausible on purpose. `sairnvet`'s seeded referral reasons are
*"DCM workup"* and *"TPLO consult"* — correct veterinary shorthand. **Looking
real is not being real.** Section 3 can only ever reject; it can never accept
on its own, which is why section 4 exists.

---

## 4. Referential coherence — do the rows point at each other?

The database will not do this for you: **one foreign key in 459 tables.**

**Ask:**

- Does every `license_hash` on a child row resolve to a licence that exists?
- Does every `job_id`, `patient_id`, `vendor` name-join on a child row resolve
  to a parent that exists?
- Does every parent that should have children have some? An invoice with no
  lines, a patient with no visits, a job with no draws — a few are normal, **all
  of them is a dropped table**.
- Are the counts on the two sides of each relationship in a sane ratio?

**This section is ALREADY MECHANICAL — run `tools/restore_coherence_check.js`
rather than reading it by hand.** Its referential pass derives the relations
from `db/schema_snapshot.json` instead of carrying a hand list, and reports
**AMBIGUOUS as its own number, never folded into "skipped"** — a column owned by
more than one candidate parent is not checked at all, because guessing a parent
turns every child row into a false orphan. The pass is **report-only** by
design.

**So read its numbers, not its exit code.** Whatever its ambiguous count is on
the day you run it, that many relationships this section did NOT answer — write
them down as COULD NOT TELL. A clean run over the relations it could resolve is
not a clean run over the platform. **Do not copy the count into this document**;
it moves with the schema snapshot, and a number written here would be the stale
anchor this repo has been bitten by before.

**It fails closed, verified 2026-09-25:** run with no target it prints *"COULD
NOT RUN … Nothing was checked, and that is not the same as nothing being wrong"*
and exits **2**, not 0.

---

## 5. Temporal shape — does the history look lived-in?

**Ask:**

- Do `created_at` values spread across the period the business has been running,
  or cluster in one window?
- Is there a **recent tail**? Real data has rows from the last few days. A
  restore whose newest row is three months old is a restore of an old backup,
  and it exits 0.
- Are there **gaps that match reality** — weekends, holidays, a closure — rather
  than either perfect uniformity or one solid block?
- Does anything sit in the **future** that should not?

**What a NO looks like:** a `dnt_charges` history that is perfectly uniform
across 18 months, seven days a week. No dental practice bills on Sundays.

---

## 6. The adversarial arm — has this rubric ever rejected anything?

**Do not skip this. It is the control, and without it sections 1–5 are a
checklist nobody has seen fail.**

Before accepting a restore, take the restored copy and **break it on purpose**,
then run sections 1–5 again and require the break to be found:

| Sabotage | Which section must catch it |
|---|---|
| Truncate one table to 10% of its rows | 1 (and 4, via the ratio) |
| Set one status column to a single value everywhere | 2 |
| Replace one table's contents with the demo licence's rows | 3 |
| Delete every child row for one parent | 4 |
| Drop every row newer than 90 days | 5 |

**A sabotage that nothing catches is a finding about the rubric**, not about the
restore. Record it here rather than passing the restore.

---

## What this rubric cannot tell you, named

- **It cannot tell you the data is CORRECT.** It tells you the data is
  *shaped like* a business's data. A restore that faithfully preserves a wrong
  value passes every section.
- **It cannot distinguish good seed data from real data on section 3 alone.**
  That is what section 4 is for, and section 4 needs 65a.
- **It is relative to the reader's knowledge of the business.** Section 1 asks
  "what would a person who knows this business expect" — a reviewer who does not
  know it should record COULD NOT TELL rather than accept.
- **It has never been run.** There is no backup to run it against. Every claim
  about what it catches is derived from the failure shapes this platform has
  recorded, not from a restore it rejected.

---

## Where this sits

- `docs/2026-09-14-backup-restorability-scoping.md` — item 65 proper: why there
  is no recovery path, and the 65a–65d sizing. **Read it for the reasoning, not
  for the state** — it is a snapshot from before the tools it sizes were built,
  later the same day, and reading its "blocked on" column as current is exactly
  the mistake this rubric was nearly written on.
- `tools/restore_coherence_check.js` (65a/65d, BUILT) — makes section 4
  mechanical, and runs section 1's digest-chain exception.
- `.github/workflows/nightly-backup.yml` (65c, BUILT, **NEVER RUN**) — blocked
  on Michael: `sql/backup_reader_role.sql` as `postgres`, plus 10 GitHub
  secrets.
- **65b, the row-count baseline — NOT BUILT, and the one thing worth building.**
  It turns section 1 from COULD NOT TELL into an answer, it is sized **S** with
  nothing blocking it, and the checker already has the `--baseline` flag waiting
  for the file.
