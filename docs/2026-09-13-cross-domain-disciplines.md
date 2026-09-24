# Cross-domain disciplines — nine standing conventions for any checker built here

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

**CORRECTED 2026-09-13, and the correction is the useful part.** This section
first said margin requires an INEQUALITY, so only one of four engines could have
one. That was right about the mathematics and **wrong about the code**. `stated
== sum of lines` is an equality on paper; in the implementation it is
`|stated − computed| < 0.005`, and a 0.005 tolerance band has real unused
headroom. **Ask what the CHECK does, not what the identity says.**

All four engines now report a margin, and the shapes differ in a way worth
seeing:

- `wip-accounting.jobWip` — a true inequality (`released <= accrued`). Alarm at
  **1% of accrued**. It fires: **29 of 2000 runs came inside the band without
  violating anything.**
- `roofing-billing.computeTotals` and `care-charges.reconcileAgainstInvoice` —
  equalities with a **0.005 tolerance**. Margin is the unused band; alarm at
  0.001, a fifth of it.
- `ledger.validateEntry` — a bare `===` on **floats**, measured (0.1 + 0.2
  returns `debit_total 0.3`, not integer cents). **Zero-width band**, so there is
  no headroom to report and its margin is non-positive by construction. That is
  itself the finding: on a check with no band there is no drift to detect before
  failure, only failure. Moving the engine to integer cents is a design decision
  and not a tool's to make.

**A display bug found in the same pass, worth keeping:** the margin was printed
to two decimals, which rendered a 0.005 band as `0.01` — **wider than the
tolerance it was measuring**. A number that cannot be smaller than the thing it
describes is worse than no number.

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

## 7. Byte-identical is not safe-in-context

**The convention: propagating a proven pattern to a new resource requires an
explicit re-qualification against the TARGET's actual operating conditions —
scale, input range, criticality tier — not merely a diff proving the code
matches. "Copy exactly" governs the bytes. It says nothing about the
assumptions the bytes were proven under.**

Borrowed from Ariane 5 Flight 501. The inertial reference software was reused
from Ariane 4 — correct code, correct in its original context, propagated
without unexplained variation. Ariane 5's flight profile produced a horizontal
velocity outside the range Ariane 4 could ever reach, an unprotected conversion
overflowed, both redundant units failed identically because they were running
the same correct software, and the vehicle was destroyed. **The copy was
faithful. The context was not.**

**Why this is a seventh discipline and not a footnote on the other six.** The
first six all defend against *a check that cannot fire*. This defends against
something structurally different: *a correct thing moved into a context where
its assumptions no longer hold*. Nothing in items 1–6 would catch it — the
criteria would be locked, the accuracy and stability would both be perfect, the
uncertainty table would be complete, the alarm would be correctly placed, the
validation would be isolated, and the redundancy would be there. **Dissimilar
redundancy is the one that fails hardest here, and that is the sharpest part of
the lesson: two identical copies of correct software fail identically, which
means a second copy is not a second opinion.**

**What re-qualification has to establish, and it is three questions, not one:**

- **SCALE** — does the target carry the same order of magnitude the pattern was
  proven at? A guard sized for one practice's supply list is not thereby sized
  for a platform-wide sweep.
- **INPUT RANGE** — can the target receive values the source could not? This is
  the Ariane case exactly, and it is the one that reads as paranoid right up
  until it is not.
- **CRITICALITY TIER** — is the target the same tier as the source? A pattern
  proven on a Tier C preference store, propagated unchanged to a Tier A money
  path, has been re-qualified for nothing. `docs/CRITICALITY-TIERS.md` is the
  register that answers this, per resource.

**This has to be designed in, not added afterwards.** Any mechanism built to
propagate a must-copy-exactly pattern automatically must carry the
re-qualification check **by construction** — a propagation tool that verifies
byte-identity and nothing else is faster at making this exact mistake, on more
resources, than a human doing it by hand. The check belongs in the mechanism
before the mechanism exists, because bolting it on afterwards means every
propagation done in between was unchecked and nobody recorded which.

**And the honest limit, stated rather than implied:** none of the three
questions can be answered mechanically today. Scale and input range need
somebody who knows the target; only the tier is already written down. So the
realistic first version is a **refusal to propagate without a recorded answer to
each**, not an automatic verdict — the same standard as a quarantine needing a
named owner rather than a tool deciding on its own.

## 8. Instrument drift — nothing announces the day a check stops testing anything

**The convention: any check whose validity rests on something OUTSIDE itself — a
string anchor into a source file, a generator's inputs, a captured snapshot — is
re-referenced against that outside source on a stated cadence, and the cadence is
derived from a MEASURED drift rate rather than chosen. Re-running the check
against its own output is not a re-reference, and a check that cannot say how old
its evidence is has not been re-referenced at all.**

From instrument flying. A directional gyro precesses at a known rate — a few
degrees a quarter hour — and it reads perfectly smoothly the entire time it is
wrong. There is no flicker at the moment it stops being right. The remedy is not
a better gyro; it is a scheduled re-reference against the magnetic compass,
performed in the one condition where the compass is itself valid. And the reason
the reference has to be a DIFFERENT instrument is the vacuum-failure case: an
attitude indicator on a dying pump eases over rather than falling off its peg,
and every instrument on that pump fails together and agrees with the others all
the way down. **Agreement is not corroboration when both ends come off the same
bus.**

**Why this is an eighth and not a footnote on 5 and 6.** Items 1–7 judge a check
at ONE INSTANT: is the criterion locked, is the validation isolated, is the
replication structurally independent, is the copy safe in its new context. All
seven can be satisfied at once. This asks the question none of them asks — **the
check WAS valid; what tells you the day it stopped?** Item 5 says do not feed a
validation from its own subject. Item 8 says a validation that was correctly
isolated in July is running against a file that moved in September, and nothing
on either side of it will say so.

**The commonest gyro here is a string anchor, and it has been measured.** A
negative control patches a real source file, runs the checker and asserts it goes
red — almost always `src.replace(anchor, …)`. When the target is refactored the
anchor stops matching, **`str.replace` silently does nothing**, and the control
then runs the checker against an unmodified file.
`python tools/sabotage_control_check.py`, run 2026-09-13: **39 probes sabotage a
real source file, 16 verify the sabotage applied, 23 do not.** The asymmetry is
why it needed a tool rather than care — an arm expecting RED fails loudly against
a checker that works, which is how this was noticed at all; an arm written as
*"expect no findings"* keeps passing on a file nobody touched and reports green
for ever.

**And the number moved the wrong way inside one afternoon.** `51fe25e8` measured
**37 and 21** when the tool was written; six hours later it is **39 and 23** —
both probes added since the tool existed were written unguarded. A drift rate is
not always slow, and it is not always in the direction of the fix.

**Re-run it rather than quoting it from here.** 23 is an open burn-down under an
active claim (`cody`, 2026-09-13), so this figure is expected to move and this
document is not its source of truth — which is the eighth convention applied to
the paragraph stating the eighth convention.

**The second gyro is a generator's own `--check`.** Both ends of that comparison
come from the same instrument, so it proves the document has not been hand-edited
and cannot prove the generator still reads what it used to read.
`tooling_inventory.py` stayed **byte-clean through two separate wrong readers in
one session** — a probe column naming the wrong test file for 27 tools, then a
pre-filter that saw no probe at all for five promoted checkers. Both were caught
by reading the regenerated diff; neither was caught by `--check`. The fix is item
2 of `docs/2026-09-13-stackup-traverse-drift-scoping.md`: every derivation SOURCE
must yield a non-zero count, and a source yielding zero is a refusal rather than
a quiet zero.

**The cadence comes from a measurement, not from a preference.**
`python tools/tooling_inventory.py --drift` reports margin against its own
history: over **16 regenerations the worst staleness ever reached is 5 source
commits and the median is 2**, so it warns at **3** — a line taken from that
distribution rather than picked, which is convention 4 applied to time. The
answer it produced was worth having on its own: for that document a schedule adds
little, because `--check` already runs on every push. **Measure before you
schedule — the drift may not be the problem.**

**A REGISTERED CHECK IS NOT A RE-REFERENCE, observed 2026-09-14 and sharpening
the sentence above.** All three derived documents were checked by hand that day.
`MASTER-PLAN.md` had no check on any push at all — `master_plan.py` was built the
day before and never registered, so the one document compounding four gates into
a FINISHED verdict was the only derived document nothing watched. Worse for the
claim above: **`traceability-matrix.md` WAS registered, its `--check` HAD been
running on every push, and it was stale anyway** — report-only never blocks, so
the check fires, prints, and the push proceeds. And `tooling_inventory.py` had
been answering **exit 2, refusing to generate**, for hours over a tool added
without an inventory entry, which meant the refusal was also **blocking its own
repair**: every other document's accumulated drift sat behind it.

So the re-reference is not the check running. **It is somebody CLEARING it**, and
a report-only check with nobody assigned to clear it degrades into a log line.
Convention 4's alarm still has to reach a person.

**State the age of the evidence, and say which instrument loses a
disagreement.** `python tools/schema_snapshot_freshness.py` is the worked
example. It prints *"VERDICTS ARE AS OF THE CAPTURE, 4.1 HOURS AGO — NOT AS OF
NOW"*, names the live probes that re-reference it, and says outright that a live
`provisioned:true` against a never-run verdict **means RE-CAPTURE, not that the
rule is broken.** That last sentence is the whole discipline in one line: when
the gyro and the compass disagree, the gyro is the one that is wrong.

**And the honest limit, which is half the rule rather than a caveat on it: a
cadence does not repair a broken instrument.** Re-running a generator that has
stopped reading a source produces a fresher wrong document, sooner. The two
halves are complementary and neither substitutes — re-reference against the
SOURCE *and* on a measured cadence. The two documents this was scoped against
make the point by needing different fixes: `docs/TOOLING-INVENTORY.md`
regenerates from the repo at zero cost, so its staleness is a **scheduling**
problem; `db/schema_snapshot.json` needs a live capture pasted in by a human and
that relay has already failed twice, so its staleness is a **hand-off** problem,
and a cron that cannot perform the capture will report drift it cannot fix.

---

## 9. Verification rigor follows what the artifact IS, not what the team is like

**The convention: before deciding how much verification an item deserves, ask
whether the thing under test IS the expensive, irreplaceable artifact, or a
cheap stand-in for it. The real, costly thing earns exhaustive verification;
the genuinely cheap-to-rebuild thing legitimately earns faster, iterative
treatment — and the decision is recorded as a fact about the ARTIFACT, never
as a preference about process.** (Methodology item 97, added 2026-09-25.)

From the SpaceX-versus-NASA comparison, read past its usual telling. The two
organizations' testing philosophies are routinely explained as culture — move
fast versus measure twice — and that explanation predicts nothing. What
predicts everything is what was on the stand: a Starship prototype is cheap
relative to the program and REPLACEABLE, so letting it fail is a measurement
strategy; a crewed capsule or a one-shot space telescope IS the artifact, so
exhaustive ground verification is the only rational posture. Same physics,
same era, opposite rigor — because the COST OF THE TESTED THING differs, not
the engineering taste. NASA itself iterates fast on cheap simulators and
mockups; SpaceX tests crew-rated hardware exhaustively. Each organization
holds both postures at once, keyed to the artifact.

**Applied here, this is what the criticality tiers have been reaching for
without the basis stated.** Tier A deserves exhaustive verification — driven
suites, mutation controls, independent review, live checks — because a Tier A
resource IS the real, irreplaceable thing: a customer's money record, a
controlled-substance log, an executed signature. Losing or corrupting one is
not a rebuild, it is a loss event. A report-only checker that gates nothing,
an internal dev script, a probe fixture — these are cheap stand-ins:
rebuilding one costs an afternoon and corrupting one costs a wrong report
somebody re-runs. Iterating fast on those is not lowered standards, it is the
same standard correctly priced.

**The question to ask, verbatim, before assigning rigor to any future item:**
*is this the real costly thing, or a cheap stand-in for it?* Two honest
corollaries. First, the answer can CHANGE — a report-only checker that gets
promoted into a push gate stops being a cheap stand-in the day it can block a
release, and its verification debt comes due then, not never (this platform's
own promotion-is-earned convention already encodes half of this). Second, the
trap runs both ways: exhaustive verification of a cheap stand-in wastes the
attention Tier A needed (rigor theater), and iterative treatment of the real
artifact books the rebuild cost as if it were an afternoon (the direction
every incident in this file's registers points).

---

## The failure mode seven of the NINE share

Seven of these conventions defend against the same thing: **a check that reads as
coverage and structurally cannot fire.** (Items 7 and 9 are the exceptions and are worth
holding separately. Item 7 defends against a correct thing moved into a context
where its assumptions no longer hold, which none of the others would catch;
item 9 is upstream of every check — it prices how much rigor an item deserves
before any check exists, so it cannot share a failure mode with the checks it
sizes.) A criterion tuned to the data.
A score that averages away the half that broke. A rate over a denominator
nobody stated. An alarm set at the cliff edge. A validation fed by its own
subject. A replication that shares a blind spot. An anchor that quietly stopped
matching.

**Item 8 arrives at that same failure mode by a different route, which is why it
is separate rather than folded in.** Items 1–6 are about a check built wrong.
Item 8 is about a check built RIGHT that decayed, and the two need different
defences — nothing in a correctly-locked, correctly-isolated,
correctly-replicated check watches the calendar.

The recurring evidence for taking that seriously is that **the tools written to
enforce these conventions kept committing the defects they were built to catch**
— a risk scorer that fabricated, a testability gate that read the wrong column,
an idempotency checker narrowed three times after false positives, and a regex
that shipped with a **literal backspace** in it and could never match. None of
those were caught by review. Each was caught by a control that had been built to
make the tool fail on purpose.

**Which is the rule underneath all eight — deliberately NOT numbered among them,
because it is the precondition for trusting any of them: build the control that
makes it fail before you trust the run that says it passed.** And item 8's
addition to it: **re-check that the control can still fail, because the day it
stopped being able to is not a day anything reported.**

*(Numbering note, 2026-09-13: this closing rule used to be called "the seventh
thing", written when the document had six numbered sections. It is unnumbered now
so it cannot collide with a section again. The two references in
`docs/2026-09-13-stackup-traverse-drift-scoping.md` that were written against the
older numbering — "all six conventions" and "the seventh convention" — have been
corrected in that document, each carrying what it originally said so the
correction is visible rather than invisible.)*
