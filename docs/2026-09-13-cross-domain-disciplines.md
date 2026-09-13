# Cross-domain disciplines — six standing conventions for any checker built here

**Read this before building any checker, probe, gate or tool.** These are not
aspirations. Each one is a convention every new tool must satisfy, and each was
paid for — either by a defect on this platform or by a defect a tool committed
while being written to prevent that same defect.

They are borrowed from domains that solved these problems first — clinical
trial design, metrology, aviation and nuclear assurance, survey engineering —
and adapted to what a web platform can actually enforce. Where the borrowed
practice does not transfer, that is said plainly rather than adopted for the
sound of it.

---

## 1. Blind analysis — lock the criteria before you see whether they flatter

**The convention: a check's pass/fail criteria are decided against synthetic
fixtures BEFORE the check is run against real data, and the tool REFUSES to
judge anything real until those fixtures classify correctly.**

Borrowed from blind analysis in experimental physics and from pre-registration
in clinical trials: decide the analysis before seeing whether it gives the
answer you want. A criterion chosen by looking at what produced a number is not
a check — it is a description of the data wearing a check's clothes, and it
passes by construction.

**Why it is a convention and not advice.** It has already failed here twice, in
one night:

- The FMEA scorer matched on three shared content words and reported **38%
  accuracy**. All five hits were false positives, every one from a draft of a
  worklog file — a worklog accumulates the prose of every defect ever recorded,
  so a three-word bar matches anything. The rule had been chosen because it
  produced a number.
- The testability gate's own criteria **failed 5 of 17 fixtures on the first
  run**, before touching real data: the behaviour-verb list had no passive
  forms, and the length test ran before the vagueness test so a vague sentence
  came back as a length complaint.

**How to implement it.** Criteria and fixtures live together in their own file.
The tool loads them, runs them against hand-built objects **in isolation** —
never alongside real output, because a lock that rides beside live data can be
satisfied by the data — and exits 2 with *"nothing real was judged"* if any
fixture is wrong. `tools/testability_criteria.py` and
`tools/invariant_registry.js` are the two worked examples.

**The distinction that keeps it honest.** Fixtures do get corrected — a fixture
whose expected verdict was simply wrong should change. What must never happen
is a fixture changed to match what the tool output. **Say in the file which one
you did.** Both examples carry that declaration.

## 2. Accuracy and stability are two numbers, never one score

**The convention: any checker reporting a "score" reports two — did it measure
the right thing (ACCURACY), and how consistently did the thing hold
(STABILITY). They are never collapsed.**

From measurement science, where accuracy (closeness to truth) and precision
(repeatability) are different axes and a single figure hides which one failed.

**It earned its place immediately.** The financial invariant runner reported
`ledger.validateEntry` as **2000/2000 STABLE while MISCLASSIFIED** — the adapter
asked for `debits_cents`, the engine returns `debit_total`, and
`undefined === undefined` is true on every case. A vacuous perfect score. **A
single number would have said PASS.** The very next row failed the other way:
`roofing-billing.computeTotals` came back **TYPE CONFIRMED with 0/2000**,
because the function takes positional arguments and was being handed an options
object. One field was right and the other wrong, in both directions, and only
two numbers could tell them apart.

**Stability is a ratio, not a verdict.** 9,999/10,000 is a different finding
from 10,000/10,000, and reporting both as PASS throws away the only signal that
matters.

## 3. A named, itemized uncertainty table — never a combined number

**The convention: wherever a derived number feeds a real decision, publish one
row per contributor, naming it and the evidence it rests on.**

From metrology's uncertainty budget: a single ±figure tells you nothing about
what to fix. The same discipline this repo already applies in
`docs/SOUP-REGISTER.md` and `docs/CRITICALITY-TIERS.md` — every Tier A row cites
a commit, a schema file or an incident, so a reader checks the claim against the
source rather than against the table.

**Applied to invariant selection:** `tools/invariant_registry.js` carries one
row per engine, naming which invariant applies and **the export it was read
from**. That matters because the alternative was tried: a keyword pass over
`debit|credit` classified `api/_lib/dental-ledger.js` as a double-entry engine
on the strength of **five comment lines** (*"as though the patient were in
credit"*), and a filename assumption reported it untested when
`api/sd-data-dental-ledger-validation.js` covers it 282/282. Both claims had to
be walked back. A row that cites the export it was read from cannot fail that
way silently.

**Corollary: publish the denominator.** A rate over the subset you looked at is
not a rate. The FMEA prediction check prints NO-DRAFT **first** and carries
`DO NOT QUOTE THIS ALONE` beside the drafted-only figure.

## 4. Control-limit margin — alarm tighter than the failure point

**The convention: any numeric pass/fail threshold sets its internal alarm
TIGHTER than the actual violation point, and reports margin-to-violation where
margin means anything.**

From statistical process control: a process that only alarms once it is out of
spec has already shipped the bad unit. The useful signal is the drift toward
the limit.

**Where margin means nothing, say so rather than padding the column.** Margin
requires an INEQUALITY. Double-entry (`debits == credits`) is exact, and reading
the engines showed ROLLUP (`stated == sum of lines`) is exact too — the distance
to violating an equality is zero, or it is already violated. So the invariant
runner reports margin on exactly one of four rows, `wip-accounting.jobWip`
(`released <= accrued`), with the alarm at **1% of accrued** rather than at
zero. It fires in practice: **29 of 2000 generated runs came inside the band
without violating anything.**

## 5. Isolated validation — the deep check runs with the subject NOT trusted

**The convention: a periodic deep re-check runs with the thing it is checking
temporarily not trusted, rather than riding alongside its live output.**

From instrument calibration: you do not calibrate a scale by weighing things
with it. If the validation consumes the subject's own output, the subject's
error is inside the validation.

**Implemented as: the fixture lock runs on hand-built objects, first, in a
separate pass.** `node tools/invariant_runner.js --fixtures` calls no engine at
all. `python tools/testability_gate.py --fixtures` reads no requirement. And the
probes go further, driving each tool from a **copy of the tree with a criterion
deliberately broken**, asserting it refuses rather than reports clean.

**Related instance, worth knowing:** `list` and `check` in `sairn_claim.py` once
ran `git checkout origin/main -- .claude/claims` to read claims — a
read-only-sounding command that writes and stages. A validation that mutates its
subject is the same failure with the arrow reversed.

## 6. Independent replication means a structurally different method

**The convention: for Tier A independence, "different method" means a
structurally different tool, code path or evidence source — not two passes
through the same tool by different people.**

Two agents running the same checker share its blind spot exactly. The
replication only buys something when the second method could fail differently
from the first.

**The worked example is real.** StoneDesk's storefront tables were confirmed
absent by **two sources sharing no mechanism**: absent from a live schema
capture, and answering 503 `UNAVAILABLE` / `NOT_PROVISIONED` to live probes. An
absence alone is consistent with a stale snapshot; a 503 alone is consistent
with an outage. **Neither explanation survives the other.** That is what
independence is for.

**Open, carried deliberately:** methodology piece 2 (tiered independence) has
not yet resolved whether its Tier A bar currently means the structural version
or the two-passes version. It is an open question there, referenced here, and it
should be resolved in piece 2 rather than assumed in either direction.

---

## The failure mode all six share

Every one of these conventions defends against the same thing: **a check that
reads as coverage and structurally cannot fire.** A criterion tuned to the data.
A score that averages away the half that broke. A rate over a denominator
nobody stated. An alarm set at the cliff edge. A validation fed by its own
subject. A replication that shares a blind spot.

The recurring evidence for taking that seriously is that **the tools written to
enforce these conventions kept committing the defects they were built to catch**
— a risk scorer that fabricated, a testability gate that read the wrong column,
an idempotency checker narrowed three times after false positives, and a regex
that shipped with a **literal backspace** in it and could never match. None of
those were caught by review. Each was caught by a control that had been built to
make the tool fail on purpose.

**Which is the seventh thing, and it underwrites the other six: build the
control that makes it fail before you trust the run that says it passed.**
