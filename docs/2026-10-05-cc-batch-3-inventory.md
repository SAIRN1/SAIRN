# CC batch 3, 2026-10-05 — five planted defects all caught, and three documents corrected my own claims

**Every figure measured, driven or run at HEAD today. Where something is quoted
from an earlier document it says so and says it was not re-derived.**

Methodology: **every screen reports its blind-spot count on its last line.**

---

## 0. TWO PREMISES IN THE DISPATCH WERE STALE, AND SAYING SO IS THE FIRST RESULT

The queue asked me to fix `test-alf-mar.js`, `alf_incidents` and
`retainage_race`, describing them as *"now correctly reddened, not fixed"* and
*"retainage_race (1/2) — still open."*

**Measured at HEAD before touching anything:**

| Suite | Dispatch said | At HEAD |
|---|---|---|
| `tests/sairncare/test-alf-mar.js` | reddened, not fixed | **21 passed, 0 failed** |
| `tests/sairncare/test-alf-incidents.js` | reddened, not fixed | **14 passed, 0 failed** |
| `tests/sairnbuild_retainage_race.js` | **1/2, still open** | **3 passed, 0 failed** |

All three landed earlier today in `ac9c21df` and `395f7f2a`. **The dispatch
describes the state before those two commits.** I did not re-fix them.

**BUT THE QUEUE ASKED FOR TWO THINGS I HAD NOT DONE, and those are the real work
below:** re-deriving whether 403 or 200 is *actually* correct for the
`alf_incidents` self-scope rather than aligning to whatever passes (§1), and
**planting the defect each arm exists to catch** (§2). Both are discharged.

**BLIND SPOTS: 1.** This table is three suite runs at one moment; another clone
could land a change that reddens any of them and nothing here would notice.

---

## 1. Is 403 or 200 correct for the `alf_incidents` self-scope? RE-DERIVED: **200.**

Asked not to align the arms "to whatever makes them pass". **Four independent
sources, none of them the arms and none of them the gate's own comment alone:**

1. **`6977854d`**, the commit that made the change, reasons it in its own
   message: filing is mandatory-reporting-by-whoever-witnessed-it, write access
   correctly ends the moment the report is saved, and *"ending write access is
   accountability; ending read access is just opacity."*
2. **The scope filters a real column set from the verified session**, and that
   same commit explicitly **refuses** the forgeable `data.reported_by`
   alternative — it *"would let any employee read any incident by claiming to
   have filed it, which is worse than the flat 403 it replaces."*
3. **It carries a Tier A review, status `reviewed`** (fourth, opened
   2026-09-28T01:24:38Z), which read it as a security fix.
4. **`api/sd-data-alf-caregiver-scope.test.js`** — a *different* suite whose
   stated job is pinning exactly these product questions — records the flat 403
   as *"now DECIDED"* and moved its arms. **The decision exists somewhere other
   than beside the code.**

**And `recorded_by` itself is protected**, which is what makes the scope worth
anything: register record **`ad97da6bce25`** (critical) closed a follow-on spoof
where `recorded_by` was missing from the write path's strip list. A scope on a
forgeable column would have been theatre.

**The 503 `MIGRATION_REQUIRED` state is deliberately NOT armed in
`test-alf-incidents.js`** and the file now says so: until
`sql/sairncare_incidents_recorded_by.sql` runs, that read answers 503 naming the
file, and `api/sd-data-alf-caregiver-scope.test.js` already drives it, asserting
the code *and* that the message names the file. A second copy would be a second
thing to drift.

The whole chain is now written into `test-alf-incidents.js` so the next reader
does not repeat it — `3b4551c5`.

**BLIND SPOTS: 2.** (1) Source 4 is a sibling test file, which is weaker than a
product decision recorded by Michael; the only *person*-level decision in the
chain is for the legacy-rows half, not the widening itself. (2) Whether the
migration has actually been run in production is **unverified** — I did not drive
the live endpoint for it, so which of 200 and 503 a real caregiver gets today is
unmeasured.

---

## 2. The five planted defects — **ALL CAUGHT.** `3b4551c5`

Landed as `tests/run_alf_scope_mutation_probe.py` rather than run once, because
the thing being asserted decays. Per **arm**, not per exit code; every mutant
`node --check`ed first.

| | Planted defect | Verdict | Red arms |
|---|---|---|---|
| **M1** | the witness refusal is computed and not acted on | **CAUGHT** | 1 |
| **M2** | the lock refuses EVERY count, even a confirmed one | **CAUGHT** | 2 |
| **M3** | the self-scope eq-clause dropped entirely | **CAUGHT** | 4 |
| **M4** | the self-scope **moved to the forgeable field** | **CAUGHT** | 4 |
| **M5** | the scope applied to broad roles too | **CAUGHT** | 2 |

`api/sd-data.js` restored byte-for-byte after each; final `git diff` clean,
checked rather than assumed.

**M4 IS THE ONE THAT JUSTIFIES THE FILE.** A suite that catches the clause being
*deleted* can still be blind to it being *moved* to `data->>reported_by`, which
looks correct in a diff and is the exact substitution `6977854d` refused by
name. It is caught.

**M5 points the other way on purpose.** A self-scope that also catches
management is not a leak — it is management losing a mandated-reporting log. The
management **control** inside the negative arm is what makes that arm mean
"scoped" rather than "unreachable", and M5 proves the control is load-bearing.

**A DEFECT IN MY OWN HARNESS, RECORDED RATHER THAN QUIETLY FIXED.** The first run
scored **M1 SURVIVED**. The arm had gone red; the arm says `CLIENT-SUPPLIED` and
my expectation said `client-supplied`, so a case-sensitive match **reported the
opposite of what happened**. A probe whose matcher is narrower than its subject
is the defect class this repo keeps paying for, and I committed it inside the
tool built to prove the arms work.

**BLIND SPOTS: 4.** (1) It proves the arms are **load-bearing**, not that the
gates are **correct** — different claims, only the first is mechanical. (2) M4 is
caught because the fixture carries `recorded_by` and no `data.reported_by`; a
fixture carrying *both* would be the harder test and does not exist. (3) The
witness happy path runs on a **mocked** token store. (4) **Nothing runs this
probe on a cadence** — it is in no registry, for the same reason the seam watch
is not.

---

## 3. `api/sd-data.js` claimed. `07eb0ce6`

Held by nobody at the start of the batch; claimed with the file set declared.
Hank held `tools/report_only_checks.py` (0.8h) and cody held seven registry
tools — **both left alone** as directed.

---

## 4. Hank's `match.cost` text applied — and re-deriving it found the opposite of what he expected. `4dfc4753`

His file was **already on `main`** and **byte-identical** to his clone's copy, so
nothing of his was unpushed and no cross-clone read was needed.

**All seven of his citations hold at HEAD this time** — `:1103`, `:4552`,
`:4771`, `:4773`, `:4774`, `:4779`, `:4784`, `:4961` — which matters because his
*previous* prepared text had two drifted citations and one already-landed fix.
His own flagged typo (`bottle_oze`) corrected on paste as he asked.

**AND ONE CLAIM CAME BACK STRONGER THAN HE WROTE IT.** He named
`msb_food_waste` as *"where I would look next"*, said explicitly he had not read
it and was **not** claiming it had the defect. I read it:

```js
if(cost<=0){toast('Cost must be greater than zero');return;}
```

**`saveMsbWaste()` refuses at the point of entry.** The same module, one panel
over, treats an absent cost as a reason to refuse the write. **That inverts the
shape of the finding** — it is not an input nobody thought about, it is the one
place a rule already applied elsewhere was not applied, which makes it cheaper
to justify and harder to defend.

**I BROKE THE ROW ON THE FIRST ATTEMPT.** The cell went to **12 cells against a
6-cell header**, because the pipes inside `match.cost||0` sit **inside code
spans**, where neither a backslash nor `&#124;` works — the identical defect that
malformed index rows 355 and 356. I wrote that lesson down nine days ago and
still walked into it; `md_table_check.py` caught it in one run.

**"Register" here is the CRITICALITY register**, not `defect-density-register.json`
— hank's own text offers the note *"for the `msb_bottle_scans` cell"*, and the
code defect is **unfixed**, so it belongs in the index. Rows 82 and 845 left
alone.

**BLIND SPOTS: 3.** (1) **The code is not fixed** — the dispatch said route it,
not fix it. (2) Nobody has checked whether any product on any live licence
actually carries a zero or absent cost: the path is reachable, whether it has
been *reached* is unmeasured, and that is the difference between a defect and an
incident. (3) Hank's proposed fix is carried into the row **as his**, with his
own argument against it, rather than resolved by me.

---

## 5. SAIRNlegacy Part 2 — the vendor-claim axis **killed Part 1's main claim.** `24ba5c08`

| Part 1 said | Part 2 found |
|---|---|
| Breadth across four businesses is the competitive thesis | **WRONG.** Cemetery+crematory+funeral is a named category — PlotBox, byondpro, Cemetery Workstation, Halcyon all sell it. Breadth is **parity**; cemetery **mapping** may put us behind |
| F1 could disqualify us in one question | **CONFIRMED AND WORSE.** The CPL has a **presentation trigger** — it must be shown *before the items or pictures are shown* — attached to the merchandise screen the app already has |
| F3: is preneed trust administration table stakes? | **ANSWERED, and mis-framed.** Case management is table stakes; trust administration is specialist; **revocable/irrevocable is a contract field, not a trust feature** |
| Pricing: not touched | **$49–$200/month, per FIRM** |
| Custody may be where we are ahead | **STILL UNKNOWN.** No vendor advertises it, which is not evidence either way |

**THIS IS WHY PART 1 REFUSED TO WRITE A COMPETITOR COLUMN IT HAD NOT
RESEARCHED.** Had it guessed, it would have guessed **in favour of the
platform**, and the breadth claim would have gone into a deck.

**BLIND SPOTS: 2.** (1) Every competitor claim is marketing or a review-site
tag — evidence of what is *sold*. (2) Two findings there rest on **feature-list
absence**, the weakest evidence in that document, and both are labelled.

---

## 6. SAIRNdesign audit — second of three, **both halves in one pass.** `5a4ea4fb`

**Method change, paid for in §5:** the competitor column goes in the same pass or
the document is not written.

**THE FINDING: `tax` occurs ZERO times in the whole file** — any case, any
context — and so do `sales tax`, `tax_rate`, `taxable`, `resale certificate`.
**The zero is CONTROLLED:** `sairnbiz.html` has **6** sales-tax occurrences,
`stonedesk.html` has **8**. Not a platform convention.

**It is the defining mechanic of the trade.** A designer **buys at trade cost and
resells**. The studio is a reseller: tax is charged to the client on resold
goods, and a **resale certificate** goes to the vendor so it is not taxed twice.
**And the PO record confirms it rather than the count inferring it** (`:2935`):
eight fields, `total_cost` a sum of item costs and nothing else — no freight, no
tax, no ship-to, no sidemark, no receiving date.

**The gap is the MIDDLE of the procurement chain.** `freight` 0, `procurement` 0,
`expedit` 0, against a category whose advertised spine is *vendor records, POs,
expediting, receiving, freight tracking*. And **`sidemark` is 0** — the trade's
universal shipment-routing field, a one-word disqualifier.

**AND A COMMERCIAL FINDING ABOUT THE PLATFORM.** Interior design prices **per
user** (Studio Designer ~$65/user/mo; Houzz Pro $99/mo for one seat, +$60/mo per
seat) — the **opposite** of death care's per-firm norm. **The same
licence-key-per-tenant model that fits SAIRNlegacy under-monetises SAIRNdesign by
construction:** a five-person studio pays one tenant licence here and ~$325/month
at Studio Designer's Basic rate. Nothing in this repo had stated this.

**Severity and competitive exposure AGREE here**, which the last two inventories
did not — every item is something a prospect meets in week one.

**BLIND SPOTS: 2.** (1) Feature-list absence is **not** used as evidence anywhere
in that document, which is the one method improvement over §5. (2) The invoicing
panel's line-item structure was **not** read, so the tax finding is about the
absence of the concept, not a specific wrong total.

---

## 7. `github-advanced-security` — checked, retried once, **closed as unanswerable**

| Check | Result |
|---|---|
| GitHub platform status | *"All Systems Operational"*, **0 unresolved incidents** — not an outage |
| `rerun-failed-jobs` | **403** *"This workflow run cannot be retried"* |
| `rerun` (whole run) | **403**, same message |
| The run itself | created `2026-09-27T04:17:13Z`, updated `04:17:47Z` — **it ran for 34 seconds**, `run_attempt: 1` |
| Its `event` | **`dynamic`** |
| `github-advanced-security` runs in the last 100 workflow runs | **ZERO** — only `hover-separation` (33), `CodeQL Advanced` (33), `source-manifest` (33), `nightly-backup` (1) |

**IT IS NOT A REPO WORKFLOW.** No YAML in `.github/workflows/`, `event: dynamic`,
absent from the run history — a GitHub-side injected job. That explains the empty
output body, why it never runs on `main` pushes, and why it cannot be retried.
The positive evidence stands: **0 open code-scanning alerts** on
`refs/pull/18/head`, six checks success, combined status success,
`mergeable_state: clean`.

**Closed rather than left open.** A fresh verdict can only come from a **new**
pull request. If it fails there too with an empty body, that is when it becomes
a finding about the repository rather than about one expired run.

**BLIND SPOTS: 1.** I still never read the job's log — the API redirect to Azure
blob storage returns 401 — so "empty output" remains what the API reports about
it, not a positive explanation of the exit code.

---

## 8. Index rows — last batch's five, and this batch's four

### Last batch's five, status now

| Row | Status |
|---|---|
| Unscoped `verifySessionToken` calls uncounted | **OPEN.** Unchanged; the fix is a decision about 14 files |
| `report_only_checks.REGISTRY` accepts evidence-free entries | **BLOCKED, left as-is as directed** — hank is fixing the intake defect |
| Seam watch landed unwired | **BLOCKED on the same**, left as-is as directed |
| SAIRNlegacy GPL vs CPL/OBCPL | **SEVERITY RAISED by §5** — the CPL's presentation trigger attaches to a screen the app already has |
| A control landing on an already-red suite is invisible | **OPEN.** §0 is a third instance of the adjacent class: a *dispatch* describing pre-fix state |

### This batch's four new rows

1. **SAIRNgrounds** — `msb_bottle_scans` stores a dollar figure with no presence
   check on its only money input, **and the sibling panel refuses the same empty
   field** (`4dfc4753`).
2. **SAIRNdesign** — `tax` occurs zero times in a reseller platform, controlled
   (`5a4ea4fb`).
3. **Platform** — per-tenant licence vs two categories' per-user norm.
   **Michael's decision, no code.**
4. **Tooling** — the GHAS check, **closed as unanswerable** with every avenue
   recorded.

### Deliberately left

Rows 82 and 845 untouched (hank has not delivered their text). Cody's seven
claimed registry tools and hank's active files untouched. The low rows from
batch 2 logged and not chased.

**BLIND SPOTS: 2.** (1) "Status now" for the five is read from the index and from
the claim record, not re-measured against the code each row describes. (2) The
competitive judgements in rows 2 and 3 are mine, from list prices and marketing
read today, with no customer or quote behind them.

---

## 9. What this batch did NOT do

* **No code fix for `match.cost`** — routed, as directed.
* **No `sairnscape` audit** — the last of the three.
* **No work on `report_only_checks.py` or the seam-watch wiring** — left as-is as
  directed.
* **No live drive of the `alf_incidents` migration state**, so whether a real
  caregiver gets 200 or 503 today is unmeasured.
* **No SAIRNbiz click-through**; finding 13 is still open and unfixed.

**BLIND SPOTS: 1.** This is what I know I did not do; it cannot cover what I did
not think to check.

---

## Three instruments of mine were narrower than their subjects today

Recorded together because the pattern is the finding, not the three instances:

1. The **mutation matcher** was case-sensitive and reported `SURVIVED` for a
   mutation that was caught.
2. The **index row** I wrote put pipes inside code spans and malformed the table
   — a lesson I had documented nine days earlier.
3. An **ad-hoc table checker** flagged three rows in the SAIRNlegacy document as
   malformed; all three were **header** rows of new tables, and the script only
   updated its expected width on separator lines.

**All three were caught in one run each, two by `md_table_check.py` and one by
reading the output instead of the verdict.** The common shape: *the tool's
criteria were narrower than the thing it measured, and in every case it failed
toward a confident wrong answer rather than toward a refusal.*
