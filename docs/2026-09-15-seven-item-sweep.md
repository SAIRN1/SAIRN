# Seven items, four already built — and the three that were not each found something live

**2026-09-15 (CC).** Items 45, 47, 50, 53, 55, 58, 61, taken as one batch.

**The headline is the split.** Three needed building. Three were already done and
needed *verifying* rather than rebuilding. One does not exist as a registry item
at all and the work behind the number is real anyway.

Every "already built" verdict below was checked against the code, not against a
summary. That distinction is the point of the sweep: `docs/SAIRN-OPEN-WORK-INDEX.md`
opens by saying every row is a claim and not a fact, and four of these seven rows
were.

---

## The split

| # | subject | verdict | evidence |
|---|---|---|---|
| **45** | trend-aware threshold alarming (PID) | **BUILT** | `tools/trend_alarm.py`, `tests/run_trend_alarm_probe.py` |
| **47** | First Article Inspection | **METHOD EXISTED, NOW MECHANISED** | `tools/first_article_inspection.py` |
| **50** | condition-number awareness | **ALREADY ANSWERED 2026-09-13** | 50b and 50c landed and guarded; 50a deliberately unbuilt |
| **53** | weakness combination | **BUILT** | `tools/weakness_combination.py` |
| **55** | pre-planned threshold response | **ALREADY BUILT AND GUARDED** | `api/_lib/cron-response.js`, guarded bidirectionally |
| **58** | three-way match | **ALREADY ANSWERED 2026-09-14** | the audit asks this exact question, verbatim |
| **61** | rotation and blast radius | **BUILT** | `tools/rotation_blast_radius.py` |

---

## Item 45 — and there is no item 45

`docs/SAIRN-OPEN-WORK-INDEX.md` states, in bold, **"THERE IS NO ITEM 45"** —
recorded 2026-09-14 after a session spent time hunting for it. That is still
true of the registry and it is recorded here rather than quietly worked around.

**The work described under the number is real regardless**, and it was specified
concretely enough to build: the platform's margin checks compare a current value
to a static line, which is the proportional term of a controller and nothing
else.

### What was found, on the first run, in this repo's own headline metric

`traceability-ratio` and `traceability-untraced` are the **same generated
document** and the **same 221 readings**, recovered from the git history of
`docs/traceability-matrix.md`. They point in opposite directions:

| view | 2026-09-10 | 2026-09-15 | slope per reading | verdict |
|---|---|---|---|---|
| traced ratio (the headline) | 29.4 % | 52.5 % | **+0.047** | improving |
| untraced count | 185 | 212 | **+0.120** | **worsening** |

A threshold on the headline reads better every single day for five days while
the backlog it is a ratio of grows. **That is not an illustration of the
integral blind spot. It is the live one.**

### Why nothing is armed, and why that is the design

A PID is only as good as its gains, and gains are tuned against history where
you know what *should* have fired. This platform has **221 readings and zero
labelled episodes**. With no episode, only the FALSE-POSITIVE half is
measurable — and an alarm wired to `return` scores perfectly on that half too.

So the three terms are printed on every run (a slope and an accumulated
exceedance need no gain at all) and the word ALARM is gated, with the missing
half named. The gate has a door: `--record-episode` then `--set-gains`, in that
order, and gains before an episode are refused.

Same shape as item 80's admissibility gate, deliberately.

---

## Item 47 — the answer to the question asked

**The question was: has anything shipped tonight actually gone through
exhaustive first-verification, or only spot-checking?**

`tools/first_article_inspection.py` answers the half that is mechanically
answerable. **27 artefacts were added on 2026-09-15. Seven have no suite at
all**, carrying **83 stated claims** between them:

| artefact | claims in its own header |
|---|---|
| `tools/guard_ablation.py` | 18 |
| `tools/accepted_risk_expiry_audit.py` | 16 |
| `tools/line_endings.py` | 13 |
| `tools/sabotage.py` | 11 |
| `tools/ai_action_approval_audit.py` | 9 |
| `tools/nhi_register.py` | 9 |
| `tools/sc_tier_a_write_gate_live_probe.py` | 7 |

Two of those seven are themselves test artefacts. **They are flagged, not
excluded** — this platform's recorded defect class is precisely that the tools
written to enforce a rule kept committing the defect they were built to catch,
so "it is a probe" is a judgement for a human and not an exemption.

### The tool committed both of the failures it exists to catch, on its first run

**UNDER-COUNTING, SILENTLY.** Arm helpers were hardcoded as `check/ck/test/it`.
`api/_lib/safe-number.test.js` declares `function t(name, fn)` and every arm is
`t('...')`, so a real suite reported **zero arms**. Separately, a
`#!/usr/bin/env python` shebang put the module docstring out of reach of a
top-anchored regex, so three tools reported **zero claims**. In both cases the
tool was reporting a finding about somebody else's work that was a fact about
its own regex.

**OVER-COUNTING, LOOSELY.** A substring search for the artefact's stem matched
`tools/sabotage.py` to **34** test files.

The arm dialect is now *discovered* per file rather than named, and an
unrecognised dialect reports **COULD NOT TELL, not zero**.

### What it will not do

It does not pair a claim to an arm. `docs/2026-09-14-first-article-inspection.md`
says the two lists must not be matched automatically — word-overlap scoring
returned **38 % with five false positives out of five** on this platform. The
probe asserts, by name, that no scoring function exists.

**And a short claim list is not good news.** This measures an artefact against
the drawing it supplied.

---

## Item 50 — already answered, and the remaining piece is deliberately unbuilt

**The question was: does the platform know which financial formulas are
inherently ill-conditioned, independent of whether the code is correct?**

**Yes, since 2026-09-13.** `docs/2026-09-13-condition-number-scoping.md` drove
the real exported functions and found three things: `wip-accounting`'s
`over_under` is structurally ill-conditioned; the bonding chain is **not**
ill-conditioned in general but degrades to κ ≈ 656 near the aggregate limit,
which is exactly where the answer is acted on; and every other money formula is
well-posed because its inputs are **recorded amounts, not estimates**.

**Verified on disk today, not taken from the document:**

- **50b — LANDED AND GUARDED.** `api/_lib/roofing-prequal.js:242-278` computes
  κ exactly and reports `remaining_regime`. Four assertions in
  `roofing-prequal.test.js` pin `well_conditioned` / `sensitive` /
  `ill_conditioned` / `at_the_limit` with their κ values.
- **50c — LANDED AND GUARDED.** The `cost_to_cost` branch keeps
  `pct_complete_exact` for the arithmetic and rounds only what is displayed.
  `wip-accounting.test.js:349-375` holds it, including the control that the
  exact field appears **only** on that path.
- **50a — DELIBERATELY UNBUILT**, and the code says so where the decision
  bites: *"nothing in this repo has an honest source for [the input's
  uncertainty] — which is exactly why item 50a is deliberately unbuilt."* The
  scoping document and the code agree.

The scoping document also says, in bold, **do not build a condition-number
scanner** — it would rediscover the one site already named. That instruction was
followed.

---

## Item 53 — and the tool found its own defect before it found the platform's

Citicorp Center: perpendicular-wind design was fine, substituting bolted joints
for welded was fine and approved, and nobody ran the quartering wind because
each half had already been signed off **alone**.

### The regression it caught in itself

The first version fired on **six real pairs out of six**, because "bound is not
a control" is a property of **one** entry that propagates into every pair that
entry appears in. A signal that fires on everything is noise with a table. It is
now reported per entry; three of six pairs trip; and section 4 of the probe is
the arm that catches the regression coming back.

### The finding: the register's own rule, turned on the register

> *"A trigger nobody watches is not a trigger."* — `docs/ACCEPTED-RISKS.md`

**AR-1 carries the only MECHANICAL trigger on the register.** It is
`api/_lib/stripe-config.js` returning a `warnings` entry, and the signal is that
warning **disappearing**. Nothing in `report_only_checks`, the push gate,
`run_all_tests`, the hooks or any workflow mentions that module. The signal is
**produced and never consumed** — and detecting an *absence* needs a watcher
more than detecting an event does.

By the register's own standard, all four entries are unwatched. It believes one
of them is not.

### The residual, printed on every run

This can only pair risks **somebody wrote down**. The Citicorp combination was
two decisions both on the record. A pair where one half was never recorded is
invisible to any analysis over a register, and four entries is the whole
register.

---

## Item 55 — already built, and guarded in both directions

`api/_lib/cron-response.js` (Fourth, 2026-09-14, extended by Hank 2026-09-15) is
a pre-decided response table, one row per status, with the argument written
where it belongs: *"A detector that stops at detecting hands the decision to
whoever happens to read the output, at the moment they read it, under whatever
pressure they are under."*

**Verified for completeness rather than taken on trust.** The watchdog produces
six statuses — `DEAD`, `FAILING`, `LATE`, `NEVER_BEAT`, `PARTIAL`, `UNDECLARED`
— and `RESPONSE` has a row for each. **There is no status with no pre-planned
response.**

And the guard against that decaying is already there, in both directions:
`api/cron-watchdog.test.js:326` fails on a produced status with no `RESPONSE`
row, `:332` fails on a `RESPONSE` row for a status nothing produces, and
`cron-response.js:166` refuses at runtime rather than defaulting.

**Nothing to build.**

---

## Item 58 — the audit asks this exact question, verbatim

**The question was: does any SAIRNbiz/StoneDesk payment or invoice write commit
on a single internally-generated record, with no independent receiving or
delivery confirmation required first?**

`docs/2026-09-14-three-way-match-audit.md` line 13 asks that question in those
words and answers it: **"Yes. Both, and in two different ways."**

- **SAIRNbiz is a zero-way match.** `saveBill()` writes the payable and posts to
  the general ledger from what was typed into one modal; `sbPayBill(id)` settles
  **the same record** with no second document, no second person and no amount
  re-entry. `grep -ciE "purchase order|receiving|packing slip|bill of lading"`
  over `sairnbiz.html` returns **0**. Two of the three documents do not exist.
  **What bounds it:** the app moves no money — the exposure is a wrong set of
  books, not a wrong disbursement.
- **StoneDesk shipped all three legs and no join key.** The match was not
  unenforced, it was **unconstructible**. `po_num` fixed that and
  `tools/three_way_match_check.py` is the guard; its structural half runs clean
  today over `sd_receiving` and `sd_ap`.

**That checker reports COULD NOT RUN without a `--data` export**, correctly: the
records live in the browser, so only the structural half can run from the repo.
That is a third state and is not folded into a pass.

**Nothing to build.**

---

## Item 61 — two controls, two numbers, and the third list is not a third number

The documented failure is treating one as the other. A freshly-rotated
overprivileged credential is still dangerous; a tightly-scoped never-rotated one
is a different problem, not a smaller version of the same one.

Measured over the 22 identities in `tools/nhi_register.py`:

| control | measured |
|---|---|
| **ROTATION** | **20 of 22** have no attested date and no schedule |
| **SCOPE** | **7 of 22** hold broad standing access |
| **COMPROMISE TRIGGER** | **0 of 22** record what to do if that one leaks |

**Zero is the sharpest of those three.** Every identity has a *procedure* for
rotation — "Stripe dashboard", "Anthropic console" — which says HOW and never
WHEN. Not one says what happens if it is known to have leaked.

**Neither control is doing anything for five:** `supabase-service-role`,
`sairn_backup_reader`, `anthropic-api`, `session-signing`,
`sairncash-firebase-admin`. That is the **intersection**, not an average of the
two columns and not their union.

### The criteria were revised once, and the direction is why it was allowed

`.1 → .2`. The first run read `postgres` — *"Owns all 380-odd objects in
public"* — as BOUNDED, because the pattern list had no phrase for ownership.
The revision added one, with a fixture in both directions, and **moved a row
from BOUNDED to BROAD**.

**That direction is the test.** A criteria change that makes the number worse is
a correction. One that makes it better is the thing this platform has a standing
rule against, and would need the scrutiny that rule exists to apply.

One boundary case is left **deliberately unresolved and stated rather than
silently decided**: `stripe-account` is *"live charge and refund authority"* —
total authority within its domain, and the domain is real money. It is BOUNDED
here because widening BROAD to "holds authority over its own service" would make
every third-party key broad and the column would stop discriminating. Whether
money authority deserves its own tier is a judgement for a human, not a regex.

### And UNATTESTED is not "never rotated"

The register says so about itself and this inherits it: no clone holds any of
these credentials, so a missing date is the absence of a note rather than a fact
about the world. **What is a fact is that nothing on this platform would notice
either way.**

---

## What this sweep does NOT claim

- **No live credential was tested.** Every rotation and scope figure is read
  from a declaration.
- **No claim-to-arm mapping was performed.** Item 47's worksheet prints both
  lists and refuses to pair them; the 83 unverified claims are unverified
  because their artefacts have *no suite*, which needs no mapping to establish.
- **No accepted-risk pair is asserted to compound.** Item 53 reports shared
  properties; whether a pair actually compounds is a judgement.
- **The four "already built" verdicts are as of a read on 2026-09-15.** Same
  standard as any row in the open-work index: re-verify before acting on one.
