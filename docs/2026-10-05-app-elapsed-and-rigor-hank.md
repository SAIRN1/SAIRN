# Build span vs verification rigor, per app — derived, 2026-10-05

**Item 10.** First commit to last commit, real calendar days, with the
verification state of each app beside it. Every figure comes from `git` or from
a repo record named in the column header. **Nothing is estimated.**

This exists to feed a speed-vs-human-firm comparison, so the scope basis is
stated before the numbers, not after.

---

## What "complete" means here, and what it does not

**22 `.html` targets are routed in `vercel.json`** — all of them are shipped in
the sense that a URL serves them.

**Five are not apps.** `docs/MASTER-PLAN.md` reports them with 0 resources, 0
suites and 0 fault probes, flagged `no dedicated suite · no fault probe`:
`sairndental-book`, `sairndental-complaint`, `stonedesk-catalog`,
`stonedesk-hr`, `stonedesk-intake`. They are sub-pages of their parent app
(2–4 commits each). Excluded, and named rather than silently dropped.

**That leaves 18 apps.** All 18 are routed, all 18 are `tiered ✅`, all 18 carry
suites and fault probes, and the plan's `Gaps` column is empty for every one.

**THE BOUNDARY THAT MATTERS FOR ANY COMPARISON:** "complete" above means
*routed + tiered + has suites + no gap flagged by this repo's own tooling*. It
does **not** mean feature-complete against a customer specification, because
**no such specification exists in this repo for any app.** A firm's delivery
date is measured against a signed scope; these dates are measured against
"nobody has filed a gap". Those are different claims and only one of them is in
evidence here. **Any speed comparison built on this table has to carry that
sentence with it**, or it is comparing a clock to a contract.

---

## The table

`days` = first commit to last commit of that file, inclusive, calendar.
`cmts` = commits touching the file. `rows` / `TierA` = criticality-register
rows owned by the app's resource prefix, and how many are Tier A.
`dfct` = records in `docs/defect-density-register.json` attributed to the app.
`rvw` = entries in `docs/tier-a-reviews.json` naming the file (independent
review obligations). `tests` = test files whose name carries the app's stem.

| app | first | last | days | cmts | rows | TierA | dfct | rvw | tests |
|---|---|---|---|---|---|---|---|---|---|
| `stonedesk` | 2026-06-22 | 2026-09-29 | **100** | 566 | 31 | 16 | 25 | 7 | 23 |
| `sairnbiz` | 2026-06-29 | 2026-09-30 | **94** | 90 | 13 | 11 | 14 | 5 | 19 |
| `sairnvet` | 2026-07-06 | 2026-09-30 | **87** | 116 | 42 | 30 | 33 | 4 | 12 |
| `sairncode` | 2026-07-06 | 2026-09-26 | **83** | 95 | 28 | 24 | 12 | 10 | 8 |
| `sairnbuild` | 2026-07-30 | 2026-09-29 | **62** | 79 | 32 | 20 | 4 | 2 | 11 |
| `sairndesign` | 2026-08-07 | 2026-09-29 | **54** | 37 | 18 | 10 | 4 | 4 | 2 |
| `sairnscape` | 2026-07-30 | 2026-09-21 | **54** | 45 | 9 | 1 | 6 | 2 | 8 |
| `sairngrounds` | 2026-08-05 | 2026-09-25 | **52** | 43 | 26 | 16 | 4 | 1 | 2 |
| `sairncash` | 2026-08-10 | 2026-09-27 | **49** | 25 | 0 | 0 | 5 | 0 | 5 |
| `sairnlaw` | 2026-08-07 | 2026-09-23 | **48** | 82 | 20 | 20 | 29 | 5 | 30 |
| `sairnlegacy` | 2026-08-07 | 2026-09-21 | **46** | 33 | 36 | 20 | 2 | 0 | 6 |
| `sairncare` | 2026-08-20 | 2026-09-30 | **42** | 38 | 14 | 14 | 29 | 6 | 8 |
| `sairndental` | 2026-08-10 | 2026-09-18 | **40** | 75 | 25 | 20 | 20 | 1 | 14 |
| `sairnsenior` | 2026-08-20 | 2026-09-27 | **39** | 37 | 15 | 13 | 4 | 4 | 7 |
| `sairnmechanical` | 2026-08-27 | 2026-09-29 | **34** | 27 | 7 | 5 | 10 | 4 | 3 |
| `sairnfreedom` | 2026-08-31 | 2026-09-28 | **29** | 25 | 36 | 27 | 7 | 2 | 6 |
| `sairnroofing` | 2026-08-24 | 2026-09-17 | **25** | 42 | 25 | 22 | 4 | 1 | 7 |

*(17 rows — `sairngrounds.html` also owns the `msb_` prefix, whose 9 rows are
included in its 26.)*

**Platform totals from `MASTER-PLAN.md`:** 391 resources owned by an app, 287
test files attributed to one, 244 traced, 63 fault probes.

---

## What the numbers actually support

**The span is calendar, not effort.** 100 days for `stonedesk` is 100 days of
wall clock during which 17 other apps were also being built, by several
sessions, against one branch. **No app in this table had a dedicated team for
its span**, so dividing days by anything gives a number with no referent. The
honest unit is *elapsed*, which is what the column says.

**The last commit is not a delivery date.** It is the last time anybody touched
the file. `sairnroofing`'s 25 days is the shortest span and it has 22 Tier A
rows and 7 suites — it is not less finished than `sairnscape` at 54 days with
1 Tier A row. **Span and rigor do not correlate in this data** and anyone
quoting the fast end should notice that.

**Three apps are visibly thinner than their span suggests, and this is the
column a comparison would otherwise hide:**

* `sairncash` — **0 register rows.** 49 days, 25 commits, 5 test files, and
  `MASTER-PLAN` confirms `res: 0`. Nothing of its stored data is tiered, so the
  defect and review columns have no denominator. **Not comparable to the
  others on rigor**, whatever its clock says.
* `sairnscape` — 9 rows, **1 Tier A**, and the expanded citation sweep found
  **0 extractable citations** for its `scp_` prefix (exit 2, COULD NOT RUN).
* `sairndesign` / `sairngrounds` — **2 test files each**, against 18 and 26
  register rows. `sairnlaw` has 30 tests for 20 rows; that is a 15× difference
  in test-per-row between apps in the same table.

**Where the independent-review column is zero, nothing outside the building
session has checked the app**: `sairncash` (0) and `sairnlegacy` (0), and
`sairngrounds`, `sairndental` and `sairnroofing` have 1 each.

**The defect counts are a FINDING RATE, not a quality ranking.** `sairnvet` 33
and `sairnlaw` 29 are the most-reviewed apps by `rvw`×`tests`; `sairnlegacy` 2
has 0 reviews and 6 tests. A low number here means less looking, not less
wrong, and the register's own documentation makes that point about itself.

---

## What this table cannot be used for

* **It is not effort.** No per-app hours exist anywhere in this repo.
* **It is not a delivery date against a scope.** No app has a specification in
  this repo to be complete *against*.
* **It is not a quality measure.** `dfct` counts what was found by whoever
  looked, and the `rvw` column shows how unevenly that was.
* **It does not establish a human-firm baseline.** That number is not in this
  repo and I did not import one. **A comparison needs a scope-matched external
  figure, which is a research task, not a derivation** — and it needs to be
  matched on the rigor columns above, not just the clock, which is the whole
  reason those columns are here.
