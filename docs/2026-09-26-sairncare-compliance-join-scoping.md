# SAIRNcare: why compliance rules do not join against staff credential records

**2026-09-26 (cc).** The question raised: dental and roofing both compute a
per-person credential board with `evaluateBoard(records, rules, today)`.
SAIRNcare has the rules (`alf_compliance_rules`), has the records
(`alf_staff_credentials`), and **no function in `api/_lib/compliance-rules.js`
takes a `records` argument at all** — every one is `(rules, opts)`. Build the
join, or document why it is deliberately absent.

**It is not deliberately absent. It is blocked, and the attempt to build it
found a live fabricated compliance pass instead.** Both halves are below.

---

## 1. The join is HALF-built already, and the half that exists was wrong

`evaluateTraining(rules, opts)` has always accepted an optional `opts.staff`
array and returned per-person findings. **Nothing calls it.**
`sairncare.html`'s `cqShowTraining()` sends `{state, facility_class,
requirement_type}` and nothing else, so the branch is dormant.

That dormancy is the only reason what follows has not reached a screen.

### 1a. A different vocabulary read as an empty one → a false PASS

Driven against the real seeded rules, West Virginia, staff member with **zero**
recorded hours:

```
{ required_annual_hours: 0, recorded_annual_hours: 0, shortfall_hours: 0,
  meets: TRUE, applicable_requirements: [null, null] }
```

WV mandates 8 hours a year for an administrator and 2 hours a year of dementia
training for **all** staff (§ 64-14-4.3.3, § 64-14-4.5.3). Its requirement rows
are `{audience, hours_per_year, topic}`. The branch reads `r.who` and
`r.annual_hours`, so every requirement contributed `Number(undefined) || 0`.
The `[null, null]` is the tell.

**Once summed, an empty requirement set is indistinguishable from a satisfied
one.** That is the whole failure in one sentence.

### 1b. Stacking semantics summed → wrong in BOTH directions

This one survives a correct vocabulary, which makes it quieter.

| state | field on the real row | what summation does |
|---|---|---|
| **PA** (alr, pch) | `additive: true` — a secured-dementia-unit requirement **on top of** the general annual hours | **UNDER-requires.** 12 general + 6 dementia collapsed to one target of 18; a staff member with 18 hours of general training and no dementia training read as compliant. **False PASS.** |
| **OH** (rcf) | `counts_toward_general_annual: true` on two rows — 4 and 8 hours that count **toward** the general 8, not on top of it | **OVER-requires.** All four rows summed to 29 where the code requires less. **False FAIL** — the merciful direction, and still a wrong number on a compliance board, which is how a screen teaches people to ignore it. |

Both fields are machine-readable and present on the real seeded rows. Nothing
was reading either.

### What was changed

`evaluateTraining`'s per-staff branch now **refuses rather than guesses**, which
is this module's own standard in its own words — *"neither is ever silently
substituted … a substitution would produce a confident wrong answer rather than
an honest gap."*

1. **`REQUIREMENTS_NOT_JOINABLE`** when any requirement row carries neither
   `who` nor `annual_hours` — the vocabulary this code reads. It names the
   state, the rule and the unreadable rows' key sets.
2. **`meets: null`** with `meets_unknown_reason`, not `true` and not `false`,
   when any applicable requirement carries stacking semantics. The figures are
   still reported: a null verdict with no numbers would be less useful than the
   wrong answer it replaces.

Measured across all six seeded training rules afterwards:

| rule | verdict for an untrained staff member |
|---|---|
| OH / rcf | `meets: null` (stacking) |
| IN / rcf | `meets: false` ← the only one that can answer |
| MI | no staff branch — no state-mandated hours |
| PA / alr | `meets: null` (stacking) |
| PA / pch | `meets: null` (stacking) |
| WV | **refused**, `REQUIREMENTS_NOT_JOINABLE` |

`api/_lib/compliance-rules-staff-join.test.js`, 23 arms.

---

## 2. Why the records join is still not built

**One of six seeded states can currently be answered at all.** That is the
scoping answer, and it is about the RULE shape, not about effort.

Five blockers, each read out of the real data:

1. **`who` is prose, not a role.** *"staff serving residents with late-stage
   cognitive impairment, or cognitive impairment with increased emotional needs
   or presenting behaviors"*. `alf_staff` carries `position`. There is no
   machine mapping between them, and inventing one by substring matching is
   PR 1.2 — matching text that describes a thing instead of the thing.
2. **Recorded hours carry a `category`, requirements do not.** A
   `training_hours` record is `{hours, category: dementia|general|orientation,
   completed_on}`. A requirement is a `who` sentence with an hours figure. The
   dementia requirement and the dementia category cannot be matched to each
   other, so no amount of arithmetic apportions one against the other.
3. **Stacking is per-rule and there are at least three kinds** — `additive`,
   `counts_toward_general_annual`, and PA/pch's `counting_rules` prose
   (*"Staff orientation counts toward the 12 hours in the first year of
   employment"*), which is conditional on a staff member's tenure, a fact the
   engine is never given.
4. **`initial_hours` with a deadline is a different question entirely** —
   *"within 14 days of the first day of work"*, *"may not provide unsupervised
   assisted living services until completion"*. That is a gate on whether
   somebody may work at all, not an annual total, and it needs a hire date the
   rules engine never receives.
5. **The annual window is undefined.** `annual_hours` — rolling twelve months,
   calendar year, or the facility's own training year? Three different answers,
   all defensible, none stated anywhere. `completed_on` exists on the record, so
   the window is computable *once somebody decides which one*.

**None of these is solved by writing the join.** Writing it would produce a
number for every state within a week, and four of six would be wrong in a way
nobody could see — which is the failure this module's header was written about.

---

## 3. What would unblock it

In order, and the first is the only one that needs a human decision:

1. **Decide the annual window** and record it on the rule, not in code.
2. **Give each requirement a machine-readable `category`** matching the record
   vocabulary (`dementia` / `general` / `orientation`), and an `applies_to`
   role list alongside the `who` prose. Both are edits to
   `sql/sairncare_compliance_seed.json`, sourced from the same administrative
   code the rows already cite — a re-read, not a re-derivation.
3. **Normalise WV** onto `who` / `annual_hours`, or teach the branch the
   `audience` / `hours_per_year` vocabulary explicitly. Today it refuses, which
   is correct and is not coverage.
4. **Then** the join is mechanical: aggregate `training_hours` records per
   `staff_id` per category within the window, pass as `opts.staff`, and the
   existing branch answers.

**The server-side aggregation is the easy part and must still be server-side.**
Today `opts.staff` would be supplied by the caller, which means a client could
send any `annual_hours_recorded` it liked and the server would report compliance
against it — while holding the real append-only record itself. That is the same
shape as the `alf_staff_credentials` attribution defect fixed on 2026-09-26
(`f0c0cb7a`): a regulated verdict computed from client-supplied values while the
authoritative record sits unread on the server.

**Not started here**, and the reason is boundaries rather than effort: the
wiring belongs in `api/sd-data.js`'s `alf_compliance_rules` evaluate action, and
that file is under fourth's active claim.

---

## 4. What this does not claim

- **No staff member is asserted compliant or non-compliant by anything here.**
  The engine now refuses to answer what it cannot answer; that is the whole
  change.
- **The refusals are not coverage.** `REQUIREMENTS_NOT_JOINABLE` for WV means a
  WV facility gets no per-staff answer at all, which is worse for the user than
  a correct answer and better than a false pass. It is a disclosed gap.
- **Nothing was checked against a live deployment.** This is a read of the repo
  and a drive of the pure engine against the committed seed.
- **The five blockers are what a read of the six seeded rules found.** A
  seventh state could carry a sixth shape; the list is not asserted complete.
