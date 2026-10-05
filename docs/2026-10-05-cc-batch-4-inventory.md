# CC batch 4, 2026-10-05 — four instrument failures repaired, and the last uncovered app audited

**Every figure measured, driven or run at HEAD today.**

Methodology: **every screen reports its blind-spot count on its last line.** The
instrument failures below are **their own section with their own lesson
entries** (§3), deliberately not folded into the items they happened inside —
because the pattern across them is worth more than any one of them.

---

## 1. What landed, with shas

| sha | What |
|---|---|
| `7ca1c7b9` | The four instrument failures: `md_table_check` coverage, the withdrawn false row, the dead-expectation guard, the derived case count |
| `29d738a7` | **SAIRNscape competitive-gap audit — the LAST of the three uncovered apps** |
| *(this commit)* | Batch inventory; the competitive-gap inventory's three-apps section **closed** |

**BLIND SPOTS: 1.** Two earlier shas in this session were rewritten by
`push_retry`'s rebase; these three are re-resolved by subject at write time, not
carried from notes.

---

## 2. THE COMPETITIVE-GAP COVERAGE GAP IS CLOSED

`docs/2026-09-29-competitive-gap-doc-inventory.md` found **three apps with no
competitive-gap doc of any kind**. All three were written today:

| App | sha | Shape |
|---|---|---|
| `sairnlegacy` | `88ee8fe7` + `24ba5c08` | internal half, then the vendor half **which overturned it** |
| `sairndesign` | `5a4ea4fb` | both halves, one pass |
| `sairnscape` | `29d738a7` | both halves, one pass |

That section of the inventory doc is now struck through and closed in place,
with the three paths and the method change recorded.

### SAIRNscape, the new one: its irrigation module competes with the hardware

**22 `scp_*` collections, 9 register rows, 1 Tier A — the thinnest surface
audited.** And two things no other app has: **a four-collection irrigation
subsystem** (controllers, zones, schedules, water features) and **a published
price on its own page** ($99 / $199 / $299 per month).

**The controller record, read at HEAD, is an ASSET RECORD:** `{id, customer_id,
name, brand, model, zones_supported}` — a manual catalogue of what is installed.
Measured: `weather` **0**, `evapotranspiration` **0**, `et0` **0**, `soil`
**0**, `runtime` **0**.

Against that, from the vendors' own material: **Hydrawise** does Predictive
Watering from forecast temperature, rainfall probability, wind and humidity, is
**flow-meter compatible for real-time leak detection**, and keeps **365 days** of
history; **Rachio** maps yards by soil type, plant variety, sun exposure and
slope.

**SO THE COMPETITOR IS THE FREE APP THAT SHIPS WITH THE HARDWARE**, not a rival
landscaping platform — which is harder to beat and cheaper for the customer. The
defensible move is to **integrate** rather than compete, and whether that is
possible depends on APIs this audit did not investigate.

**AND THE PRICE IS NOT THE PROBLEM, which is worth saying after two audits where
it was.** $99–299 sits inside Service Autopilot's band ($49/$199/$499) and below
LMN's entry tier ($297 for 1 office + 5 crew). Per-tenant is **normal** here —
Aspire is described as one fee with no user cap, LMN bundles licences. **The one
app of the three where licence model, published price and category norm all
agree** — paired with the thinnest feature surface, which is the uncomfortable
part.

**BLIND SPOTS: 3.** (1) No feature-by-feature comparison against Jobber, LMN,
Service Autopilot or Aspire — only irrigation and pricing, so "thinnest surface"
is a stored-data count and **not** a scored competitive gap. (2) Whether
Hydrawise or Rachio expose an integrable API was **not investigated**, and the
strategic recommendation depends on it. (3) Competitor claims are marketing;
Aspire's $300–500/user is third-party report, not vendor-stated.

---

## 3. MY OWN INSTRUMENT FAILURES — four, not three, each as its own lesson

I reported three last batch. **Measuring them found a fourth, and it is the
worst of the set.** Each is a separate lesson entry below.

### LESSON A — I put a FALSE "could not run" accusation into a standing document

**CLAIMED:** *"`tools/md_table_check.py` exits 2 (COULD NOT RUN) while reporting
0 malformed rows."* **MEASURED: it exits 0.**

Run with output redirected into files and `echo $?` on its own line, it exits
**0** with `TOTAL_MALFORMED_ROWS:0`. And `main()` can only
`return 1 if (total or unseen) else 0` — **there is no path in it that returns 2
at all.**

**Where the 2 came from:** I read it off a **compound Bash command** (the tool
piped into `tail`, inside an `&&` chain), where the reported status belongs to
the last element of the pipeline, not to the tool. I then wrote the misreading
into the open-work index *and* a commit message.

**THE LESSON:** *on this platform, a false COULD-NOT-RUN accusation against a
working checker is worse than the defect it imagines.* `PR §1.11` exists because
silent could-not-run is the costliest failure here — which is exactly why
**claiming** it falsely is the costliest false finding: it is the claim most
likely to get a sound tool distrusted or rewritten. **An exit code read off a
pipeline is not that program's exit code**, and the fix is one line of shell
discipline: redirect, then check `$?` alone.

Row withdrawn in place with the measurement.

### LESSON B — the nine-day-old lesson did not fail; the instrument did not read the file

On 2026-09-27 a `|` inside a code span malformed index rows 355/356, and the
lesson was written up the same day. On 2026-10-05 **the same defect was committed
again by the session that wrote it**, in `docs/CRITICALITY-TIERS.md`.

**`md_table_check.py` did not see it, because `DEFAULT_FILES` held three files
and that was not one of them.**

**THE LESSON:** *a discipline written in prose cannot prevent what nothing
measures.* The question to ask of any repeated defect is not "why did I forget"
but **"what would have caught it, and does that thing look at my file?"**

Fixed by coverage, measured before adding: `CRITICALITY-TIERS.md` (434 rows) and
`traceability-matrix.md` (516 rows), both clean, so neither arrives red.
**Coverage: 837 rows over 3 files → 1,787 over 5.** **Driven:** re-breaking that
exact cell now reports *"409 12 cells, header says 8"* and exit **1**, where
before it reported nothing. Locked by 11 probe arms asserting membership by name;
removing one turns the probe red on a named arm.

### LESSON C — narrow coverage does not just miss defects, it manufactures a worse instrument

The ad-hoc checker that false-flagged three **header** rows was not an unrelated
mistake. **I hand-rolled it because the real tool was blind to my file.** It then
got the answer wrong, because it only updated its expected column width on
separator lines.

**THE LESSON:** *the second-order cost of a narrow instrument is larger than the
first.* A session that finds the real tool does not cover its file **builds a
worse one and then trusts it** — and the worse one fails toward a confident wrong
answer, not a refusal. Fixing B removes the reason C exists.

### LESSON D — case-insensitivity fixed the instance; the class needed a different fix

The mutation matcher reported **SURVIVED** for a mutation that was **caught**,
because the arm says `CLIENT-SUPPLIED` and the expectation said
`client-supplied`.

**Making it case-insensitive closed one case and left the category open.** An arm
can be reworded, split or deleted as easily as mis-cased, and each leaves a
matcher that **cannot match** — indistinguishable from a missing guard, and
failing toward the **louder** verdict, the direction that gets a real control
deleted to make a probe green.

`dead_expectations()` now checks every expectation against the arm names that
**actually exist**, before any mutation runs; an unmatchable one is **exit 2
REFUSING** rather than a verdict. *Same question `once()` asks of a sabotage
anchor, asked of the matcher instead of the subject.*

**Driven both ways:** a mis-cased expectation still matches and all five
mutations stay CAUGHT; an expectation naming an arm that does not exist refuses
at exit 2, naming the mutation, the suite and the dead text.

**THE LESSON:** *when a matcher is wrong, ask what else could make it fail to
match — fixing the observed instance leaves the class.*

### LESSON E — the assertion that stopped the fifth instance

**While writing the withdrawal row, I put a pipe inside two code spans — one of
them in the clause explaining that pipes inside code spans break rows.** The row
came out at 9 cells against 7.

**An assertion in the writing script caught it before the file was touched.**
That is the only reason it is an anecdote rather than a fourth malformed row.

**THE LESSON:** *assert the invariant in the script that writes the artefact, not
in a check that runs afterwards.* A post-hoc checker tells you what you broke; a
pre-write assertion means you never broke it. Both existed here and only one
prevented anything.

### And one real defect the wider coverage found

**`docs/TOOLING-INVENTORY.md`: 400 rows, ELEVEN genuinely malformed** — lines 84,
91, 93, 101, 257, 318, 342, 406, 420, 422, 431 — every one a pipe character
inside a code span in a tool's `PURPOSES` text. **It is GENERATED**, so the rows
cannot be repaired in place; the fix belongs in `tools/tooling_inventory.py`'s
cell emitter.

Deliberately **not** added to `DEFAULT_FILES` — adding a file that cannot be
cleaned from the document would put a report-only tool permanently in a state
nobody can clear, which is how it becomes noise. Named in a `KNOWN_UNADDED`
constant so the omission reads as a decision, and locked by a probe arm.

**So the pipe-in-code-span defect is platform-wide and sits in a generated
document — not a typo I made twice.**

### A fifth, small, same class

The probe's summary line read **"25 cases"** while **35 arms ran**, because the
count was `len(CASES) + 18`. A hardcoded check count that does not move when a
check does is the defect `CLAUDE.md`'s push protocol names in those words. Now
derived from what actually ran.

**BLIND SPOTS: 3.** (1) `dead_expectations` proves an expectation **can** match
some arm — not that it matches the **right** one, so an accidental substring
match still scores wrongly. (2) The `TOOLING-INVENTORY` count of 11 is as of
today and the file is regenerated, so it moves. (3) **Four of the five were
found by measuring my own claims and the fifth by an assertion. None was found
by a cadenced check** — so the next of this class also waits for somebody to
look.

---

## 4. Left alone, as directed

* **Rows 82 / 845** — hank has not delivered the paste-ready text.
* **`report_only_checks` arm E2 and the seam-watch wiring** — both blocked on
  hank's refuse-at-import fix, which has not landed. Not reworked around.
* **Cody's claimed registry tools**, **hank's `rebase_state_guard.py`**, **seq
  468** — untouched.

Verified against the live claim record at the start of the batch: hank held
`citation_line_drift_check.py` / `push_retry.py`, cody held `gap_ledger.py`,
fourth held `sairnsenior.html` and others. None of my files overlapped.

**BLIND SPOTS: 1.** The claim record is only as fresh as the last push to it; a
session working without claiming is invisible to this check.

---

## 5. What this batch did NOT do

* **No fix to `tools/tooling_inventory.py`'s cell emitter** — the 11 malformed
  generated rows are logged, not repaired.
* **No feature-by-feature comparison** for SAIRNscape beyond irrigation and
  pricing.
* **No investigation of Hydrawise/Rachio APIs**, which the SAIRNscape
  recommendation depends on.
* **No SAIRNbiz click-through**; finding 13 still open and unfixed.
* **No live drive of the `alf_incidents` migration state.**

**BLIND SPOTS: 1.** This is what I know I did not do; it cannot cover what I did
not think to check — which is what §3's five entries exist to narrow and do not
eliminate.
