# Cross-domain disciplines — standing conventions for any checker built here

**COUNT THE `## <n>.` HEADINGS BELOW. DO NOT TRUST A NUMBER IN THIS TITLE OR
ANYWHERE ELSE.** This heading read *"eleven standing conventions"* until
2026-10-07, while the file held **nineteen** — it was last correct on
2026-09-25 and nothing announced the day it stopped being. The number is
removed from the title rather than corrected to 19, because a count in a title
is a fact that goes stale on the next addition and this file's own item 8 is
about exactly that. `CLAUDE.md` already says to count rather than trust, and
so does `docs/METHODOLOGY.md`.

**Read this before building any checker, probe, gate or tool.**  These are not
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

## 10. Segmented verification — no long run whose first check is at the end

**The convention: break one long unverifiable run into short segments, each
independently checkable at its boundary, instead of betting everything on one
continuous leap of faith checked only at the finish.** (Methodology item 95,
adopted 2026-09-24 -- NUMBERED TENTH after landing: another session adopted
a different ninth the same day, and this document's own closing note records
what a numbering collision costs, so the later-to-land renumbers.)

Borrowed from survey engineering's hardest recent case: the Gotthard Base
Tunnel did not bore 57 km from each portal and hope to meet — intermediate
access shafts (Sedrun, Faido, Amsteg) let several machines drill SHORTER,
independently-surveyable segments, so an alignment error was caught at the
next boundary instead of compounding for a decade. The tubes met within
centimetres because nothing was allowed to run unverified for long enough to
drift by metres.

**Why it is a convention and not advice — it was paid for HERE, twice, and the
second time was the day it was adopted:**

- **The stale-plan dispatch (2026-09-24).** A queue item said methodology
  item 34 had "no owner." It had been BUILT ten days earlier and extended by
  another session that very morning. The dispatch trusted one long
  unverified read — a plan snapshot, never re-checked against the repo
  between its writing and its execution — and the truth surfaced only
  because the rebuild accidentally collided with the original at the
  inventory gate. Segments existed (the claim record, `git log`, the
  inventory) and the run consulted none of them until the end.
- **The headline sentence of `docs/CRITICALITY-TIERS.md` drifted five
  recorded times**, twice while two sessions re-derived it concurrently from
  different trees. The fix that held was not care — it was a SHAFT:
  `criticality_tier_check.py` re-derives the count on every run, so a drift
  is caught at the next boundary instead of at the next audit weeks later.

**What already implements it, named so the pattern is copied rather than
reinvented:** item 35's checkpoint endpoint plus item 54's heartbeat (a long
agent run becomes independently-checkable segments); every sabotage probe's
per-arm verdicts with byte-verified restore between arms (a probe is never
one long mutation whose first check is at the end); the push loop's
per-attempt rebase-verify-push cycle; and the tier checker's per-run
re-derivation above.

**The test to apply when building or reviewing anything long-running:** find
the longest interval in which the work could be silently wrong. If the answer
is "from start to finish," the run needs a shaft — a boundary at which the
work so far is checked against an independent source — and the shaft must be
CHEAPER than the segment it protects, or nobody will sink it. A checkpoint
that merely records progress is not a shaft; a shaft VERIFIES, against
something the run did not itself produce (item 5's isolation rule, applied to
time).

**Where it does not transfer, said plainly:** an operation that is atomic by
design (one upsert, one signed commit) has no interior to segment, and
slicing it would add failure modes, not remove them. The convention is about
runs whose LENGTH is the risk, not about making everything incremental.

---

## 11. Human-gated auto-remediation — a fixer may not approve its own fix

> **HEADING REPAIRED 2026-10-06 (Fourth), ON CC'S ROUTED FINDING.** This
> heading had NO BODY, and the body below sat forty lines further down under
> a heading reading *"The failure mode seven of the first eight share"* — a
> section title from when this file had eight numbered items. So item 11 read
> as an empty promise and its content read as a summary of something else.
> **Nothing in the text changed; only where it sits and what it is called.**
> cc found it while working on an unrelated file, routed it rather than
> editing another session's document, and named it precisely enough that no
> re-derivation was needed: *"its item 11 heading has NO BODY"*.


**The convention: a tool that DETECTS drift may PROPOSE the repair, and may
never apply it. The proposal lands through a review a human performs.**
(Methodology item 103, adopted 2026-09-25 on Michael's decision about item
102 phase 2.)

Borrowed from GitOps, which formalised exactly this as the **plan/apply
split**: drift between declared and actual state is continuously detected
and *proposed*, and it reaches the cluster only through a reviewed merge —
enforced PR review even for mechanical infrastructure fixes, precisely
because "mechanical" is a judgement somebody has to make about each case.
The live software-engineering precedent is a coding-agent drift tool that
opens two draft PRs per finding — revert, or adopt — and leaves the choice
to a reviewer rather than picking one.

**Why it is a convention and not advice.** It is the same failure as item 8's
`--check` comparing a document to its own output, moved one step later: there,
a generator judged what it had produced; here, a detector would bless what it
had repaired. In both the comparison is real and the *independence* is gone,
and the output reads exactly like a check that passed. This platform has the
receipt: `tools/tooling_inventory.py` refuses to generate rather than emit a
blank cell, and the push gate treats that refusal as a finding — a generator
that had quietly filled the cell in would have looked identical to a clean
run.

**It binds harder here than in infrastructure, and that is the local
addition.** A GitOps drift is usually a fact — a replica count, an image tag.
A register cell is usually a **judgement**: a tier, a confidentiality class,
a compliance argument. The one genuinely mechanical part of such a cell is a
line number, and even that is only proposed:
`tools/register_freshness_propose.py` repoints a citation **only** when the
named identifier has exactly one definition-like line today, refuses with a
reason when there are several (choosing is the judgement) or none (the cell
needs re-reading, not repointing), and withdraws any batch that does not
clear its own findings and nobody else's.

**How to implement it.**
- The detector has **no write path to its subject**, asserted on the source
  rather than promised in prose. `tools/register_freshness_check.py` carries
  that as a fixture.
- The proposer works on a **throwaway branch**, refuses a dirty tree, and
  restores HEAD **verified by sha**.
- The proposal **verifies itself before it is offered** — re-run the
  detector, require the claimed findings gone and no others.
- When the PR-opening tool is absent, **say so and stop**. Falling back to a
  direct write is the one behaviour the convention forbids, and it is the
  convenient one.

**Where it does not transfer, said plainly.** Fully reversible,
self-verifying machine state with no judgement in it — a regenerated derived
document whose generator is itself gated, a formatter — is not what this is
about; `master_plan.py` regenerating `docs/MASTER-PLAN.md` is a generator
doing its job, and the check on it is a separate `--check`. The line is
whether the artefact encodes a DECISION somebody could be wrong about. If it
does, the fixer proposes.

---

## 12. Ablation over chaos — measure ONE layer's contribution, not the system's luck

**Borrowed from SpaceX's heatshield practice, and the distinction from item 70's
chaos engineering is the whole value.** Chaos asks *does the platform survive a
random failure*. Ablation asks *what does THIS layer catch that nothing else
would* — one named protective layer removed deliberately, instrumented on that
exact spot, on code already believed clean.

**FIRST RUN, 2026-09-25, and it paid for itself immediately**
(`docs/2026-09-25-ablation-sabotage-harness.md`). Subject: `tests/sabotage_harness.py`'s
per-mutation verdict, which was `rc != 0` — so a mutant that failed to PARSE was
indistinguishable from one the suite refused, for all 27 probes that share the
harness. Measured contribution: **6 arms across 6 probes had been reporting
CAUGHT on mutants that never compiled**, and nothing else on this platform could
see them (`mutation_anchor_check.py` proves an anchor is unique, never that the
result parses).

**THREE THINGS THAT MAKE IT WORK, each learned in that one run:**

* **Pick a layer whose SIGNAL IS AMBIGUOUS.** The value came from CAUGHT and
  CRASHED printing the same word. A layer with an unambiguous verdict has more
  to learn from a sabotage control than from ablation.
* **A NEW layer needs no sandbox** — the ablated condition is a git ref. That is
  the cheapest form this experiment takes, and the reason to run it at the
  moment a layer lands rather than later.
* **MEASURE PER ARM, NOT PER EXIT CODE.** 6 of the 15 findings were invisible at
  the exit-code level: the probes exited non-zero in BOTH conditions, for
  different reasons, so an exit-code comparison would have reported no change.

**AND THE SECOND-ORDER FINDING OUTRANKED THE FIRST, which is the pattern to
expect rather than a one-off:** the experiment was designed to price one layer
and established instead that **nothing runs the probe corpus at all** — 15 arms
across 12 of 27 probes were unreliable (6 malformed mutants, 7 stale anchors,
2 expired premises, 2 stale fixtures) and no gate, hook or sweep would have
said so. Ablation puts a layer under a bright light; what it mostly finds is
what else that light falls on.

**WHERE IT DOES NOT TRANSFER, said plainly:** ablating a layer on LIVE data or a
shared clone is not this practice, it is an outage. The subject must be code
already believed clean and a condition you can restore byte-for-byte — and the
restoration must be VERIFIED, not assumed, which is what the harness's own
byte-identical arms are for.

**AND THE CLASS IT STILL CANNOT SEE:** a mutant that parses and is caught for
the WRONG reason. The layer proves the mutant compiles; nothing proves the suite
went red about the property the arm's name claims. All six rewrites were
hand-read for that, and hand-reading is not a check.

---

## 13. An edit is verified by READING THE FILE, never by the editor's diff counts

**Adopted 2026-10-06 (Fourth), after the same mistake twice in one morning, in
two different files, both times while deliberately correcting a stale fact.**

The edit tool reports what it changed -- *"1 addition, 1 removal"* -- and that
report is about the PATCH, not about the file. A patch can apply cleanly and
leave the old text standing: a near-duplicate line, a second copy in another
section, a sentence that says the same thing in different words. The counts are
correct and the file is wrong, and nothing in the tool's output can tell you so.

**THE TWO CASES, both in the batch that produced this convention:**

* `docs/2026-09-17-sairnroofing-competitive-gap-rederived.md` -- the A5 headline
  row was rewritten from STILL OPEN to CLOSED. The edit's output showed the A5
  row **twice**, which was the only visible sign that the old row might still be
  there. A read of the file was needed to establish that it was not.
* `api/_lib/exec-context.js` -- an accounting statement was replaced. The
  previous statement sat in the SAME array, a few lines up. Two accounting
  statements contradicting each other inside one system prompt is strictly worse
  than the original single wrong one, because the model now has to pick.

**THE CHECK IS NOT "re-read the diff".** A diff shows what the patch did; the
question is what the FILE now says. For a replaced fact the read has to be a
search for the OLD text across the whole file, not a look at the new text:

    the fact is corrected  <=>  the old wording occurs ZERO times in the output
                                a reader will actually see

For `exec-context.js` that meant joining the prompt the way the app joins it and
searching the joined string -- not reading the source, where the old wording
legitimately survives inside a comment that records the correction. **Source and
rendered output are different documents, and the assertion is about the rendered
one.**

**Why it is a convention and not advice.** It is item 8 one step earlier. Item 8
is about a check that stopped testing anything; this is about an EDIT that
stopped changing anything, and both produce an artefact that looks maintained.
And it generalises past text: the same shape is a migration that adds a column
beside the one it was meant to replace, and a config line appended under an
earlier line that still wins.

**Where it does not transfer, said plainly.** A generated document regenerated by
its generator does not need this -- the generator owns the whole file and a
`--check` compares it to its sources, which is a stronger test than a read. The
convention is about HAND edits to standing prose, data and prompts.

---

## 14. A convention inferred from a sample states n of N before it is used as evidence

**Adopted 2026-10-06 (Fourth). Paid for three times: once by somebody else's void
A/B comparison, and twice by me in the hour after I wrote the tool that was
supposed to catch it.**

**THE ORIGINAL CASE.** On 2026-10-05 a session needed to know whether a change to
`sairnlegacy.html` had broken `tests/sairnlegacy_write_failure_voice.js`. It ran
the suite twice, once with `LEG_HTML=<pre-change copy>` and once without, got the
same failure both times, and read that as *"pre-existing, not mine."* **That suite
does not read `LEG_HTML`.** Both runs tested the identical file, so the comparison
established nothing -- while looking like a careful A/B. The conclusion happened
to be right, which is the worst outcome: a void method that returns the right
answer gets reused.

The caller did not invent the convention out of nothing. **Two sibling suites DO
accept `LEG_HTML`.** Measured on 2026-10-06 across the whole family: **2 of 7**.
And across the tree, no app-file override reaches a majority of its family
anywhere -- `SD_HTML` 6 of 70, `SB_HTML` 7 of 20, `DNT_HTML` 5 of 18, `SEN_HTML`
3 of 15. There is no convention; there are scattered instances, and one instance
looks exactly like a convention from inside one file.

**MY OWN TWO, the same day, which is why this is numbered rather than noted:**

* Re-counting the app files behind an exec-context claim, I classified a sub-page
  as *"a root `.html` with a hyphen in its name"* and got **17 + 5** where the
  line said **18 + 4**. That rule was mine and is nowhere in the repo. The repo's
  rule is an explicit four-item list in `api/sd-data-exec-context.test.js`, which
  deliberately counts `stonedesk-catalog` as an APP and says the boundary is
  fuzzy. I would have "corrected" a correct line.
* Counting `KNOWN_APP_IDS` in `api/claude.js`, I reported a duplicate
  `'sairnsenior'`. There is none -- my count matched app_id strings inside the
  file's COMMENTS, which is the mistake that file's own suite warns about in a
  comment saying a first pass did exactly this and was *"one edit away from fixing
  a non-bug."*

Both were caught by a suite going red, not by re-reading.

**THE RULE, in the form that is checkable:**

> Before a pattern observed in a sample is used as a premise, state **how many of
> how many** carry it, and state **the rule by which you classified them**. A
> premise with no denominator and no stated rule is an impression.

**Two numbers, not one, and they do different work.** `n/N` says how much of the
family agrees. The classification rule says whether `N` is the right family at
all -- and in both of my cases `n/N` would have looked fine while the rule was
wrong. This is item 3's named-uncertainty-table discipline applied to the
population rather than to the measurement.

**How to implement it.** `tools/suite_override_consistency.py` prints the ratio
with every finding for exactly this reason, and keeps its superseded
`--rule majority` selectable so the difference between two classification rules is
measurable rather than argued. When the rule comes from somewhere else -- a
suite's own list, a schema, a registry -- **cite that source instead of
re-deriving it**, because a second derivation is a second rule.

**Where it does not transfer, said plainly.** A closed set you can enumerate in
full is not a sample: `n` of `n` needs no ratio. The convention bites when the
population is large enough that you looked at part of it, which is most of the
time on a platform this size and almost always when the evidence is a grep.

---

## 15. A green claim must cite an exit code captured by whatever WAITED on the tool

**Promoted 2026-10-06 (Fourth) from cody's routed write-up
(`docs/2026-10-06-cody-queue16-inventory.md` §8), which asked for exactly this
and said why it must not stay in a dated file: "a lesson in a dated file is the
eighth convention waiting to happen."** Cody found it, measured it and could
not promote it -- this document was under a subject-level claim block that hour.
The derivation below is theirs; the only thing added here is the promotion.

**The rule, in one sentence:** *a standing document may not call a tool green
without an exit code captured from the run itself, and a backgrounded run's
"completed (exit code 0)" is the status of whatever ran LAST, not of the tool.*

**The repo's own advice is correct and is not enough.**
`tools/exit_status_attributable.py` recommends the right shape:

    python tools/some_check.py > /tmp/out 2>&1
    echo "EXIT=$?"

In the FOREGROUND that is completely correct. Backgrounded, the caller receives
the status of the COMPOUND command, whose last element is the `echo` -- so it
reports **0** whatever the tool did. Measured:

| run | harness notification | real code |
|---|---|---|
| `metamorphic_check.py` | completed (exit code 0) | **1** |
| `dead_rule_sweep.py` | completed (exit code 0) | **2** |

**Two not-green tools were one step from entering a standing document as green.**
Nothing was hidden -- both real numbers sat in the captured stdout. What was
wrong was the number that looked authoritative.

**Why a habit cannot fix this and a file can.** The backgrounding decision is
made AFTER the command text is written, by something other than whoever wrote
it. The same text is safe in one context and misleading in the other, so no care
at writing time can tell which it will be. A checker that reasons about command
TEXT -- the right place for such a checker -- cannot see the layer that makes
that text wrong. `tools/capture_exit.py` records the status in a NAMED FILE,
written by the process that actually reaped the child:

    python tools/capture_exit.py --status run.status -- python tools/some_check.py
    python tools/capture_exit.py --read run.status     # exits WITH that code

**And the third state is the hard part, one level down.** A status file that
does not exist yet and one reading `EXIT 0` are the same bytes to a careless
reader: nothing, then zero. That is PR §1.11 again, so the file is written
twice -- `RUNNING <pid>` before the child starts, `EXIT <code>` after it is
reaped, `COULD_NOT_RUN` when it never started -- and `--read` exits **2, never
0**, on ABSENT / RUNNING / UNREADABLE.

**THE COROLLARY, which cody's own batch paid for three times: reporting a run
WITHOUT its exit code is the same defect arriving quietly.** Three dated
documents printed a sweep's figures with no status anywhere in the file. That
sweep exits 2 whenever rules stay uncleared, so none of those runs was ever
green and nothing said so. All three now carry a dated correction, and **the
exit code of a past run is not recoverable and was not invented** -- each says
so and records a re-run instead.

**Where it does not transfer, said plainly.** A tool whose only contract is its
stdout, with no exit-code meaning at all, has nothing to capture -- but that is
a tool whose greenness cannot be claimed either, which is the same conclusion
by a different road.

---

## 16. A probe that never reached the code proves nothing about the code -- so prove it arrived

**Adopted 2026-10-06 (Fourth), after reading SIX clean results as evidence
when all six were non-runs.**

**THE CASE.** `tests/push_gate/check8_probe.py` leaves this clone's
`.git/config` carrying `core.bare = true` and a fixture identity, after which
every git command in the clone fails outright. To find the writer I isolated
six candidates and every one came back **CONFIG UNCHANGED**:

* `tools/copy_exactly_gate.py --fixtures`, and `--range` from a worktree
  (its `_fx_repo()` is the *only* place in the repo that writes
  `fx@example.invalid`);
* each of the four `.githooks/pre-push` gates, driven separately with a
  crafted refs line on stdin;
* `tools/sairn_push_gate_hook.py` in PreToolUse mode;
* a real `git push --dry-run` from a worktree;
* `git worktree add` on its own.

I was one step from writing "mechanism unknown, six candidates excluded".

**EVERY ONE OF THOSE SIX EXITED EARLY ON THE SAME LINE:** *"the outgoing range
`<a>..<b>` could not be read"*. `origin/main` moves hourly here, so the gate
chain refused before reaching the path that writes. **Six negative results
from six runs that never executed the code under suspicion.** The probe's own
instrumentation then pinned it in one run — a per-step reassertion that names
the step the drift appears after reported `dry_push(probe_env=False)`, the
first dry-run push whose range *does* resolve, every time.

**THE RULE.**

> A negative result is evidence only if the run REACHED the code it is about.
> Before recording "X did not do it", show that X ran — a line of its output,
> a counter, a side effect, anything that could only exist if the suspect code
> executed. **An isolation with no arrival evidence is a COULD-NOT-TELL
> wearing a verdict.**

**This is PR §1.11 moved from checks to EXPERIMENTS,** and it is harder to see
there. A check that could not run usually says so; an isolation that could not
run looks *exactly* like an isolation that ran and found nothing. Both print
nothing.

**THE SIBLING CASE, from the batch before, because the two share a root.** A
whole-tree run was driven WITHOUT `--pinned` on a branch five clones push to
hourly. Its log reports `tests/sairnbiz_vendor_ytd_derivation.js` as passing;
the same suite driven by hand exits 1, because a rename arrived mid-run. There
the run DID reach the code — and reached a *different version of it* than the
one being reported on. **Arrival has two halves: did it execute, and did it
execute the thing you are naming.** `--pinned` exists for the second half and
not using it cost a day's census.

**HOW TO IMPLEMENT IT.**
- **Make the suspect announce itself.** The per-step label that pinned the
  config writer cost four lines and replaced six wasted isolations.
- **Pin the subject before measuring it** — a commit, a sha, a frozen copy —
  whenever anything else can move it while you look.
- **Record WHY each negative is a negative.** "Ran and found nothing" and
  "refused before reaching it" are different sentences; a list of the first
  that is secretly the second is worse than no list.

**WHERE IT DOES NOT TRANSFER, said plainly.** A total, unconditional absence —
grep over a corpus for a string that is simply not there — has no "arrival" to
demonstrate; the search itself is the arrival. The rule bites when the suspect
is CODE THAT HAS PRECONDITIONS, because the preconditions are what fail
quietly.

---

## 17. A third state for ABSENCE is not a third state for AMBIGUITY

**Adopted 2026-10-06 (Fourth), from my own tool reporting FIFTEEN findings
that were all true of the wrong file.**

**THE CONVENTION: when a check has to pick which thing it is judging, "I
could not find a subject" and "I found several and chose one" are DIFFERENT
third states. A tool that handles only the first silently guesses its way
through the second, and the guess is reported in the same shape as a
measurement.**

**THE CASE.** My gap-document verifier was written to remove an inference it
had been caught making: it had guessed each document's subject app from the
document's *filename*. The replacement rule was explicitly evidence-based —
judge each claim against **the file the document itself names nearest above
it** — and it carried a proper third state, `COULD NOT CHECK (no file
named)`, counted separately and never folded into "holds". That was the right
correction and it was not enough.

Run over 36 gap documents at HEAD `762b084b`, it reported **21 broken line
citations**. Fifteen of them looked like this:

    CITE  `rf_warranty_tiers` at sairndental.html:4737 -- found at NOWHERE
    CITE  `dnt_gfe`           at sairnroofing.html:1802 -- found at NOWHERE

Roofing's `rf_*` tables judged against the dental app; dental's `dnt_*` and
`cdt_*` tables judged against the roofing app. The document is
`docs/superpowers/specs/2026-08-26-competitive-gap-audit-roofing-dental-senior.md`
— **three verticals interleaved in one file.** Inside a 1200-character
lookback window it names more than one app, and `hits[-1]` picked whichever
was nearest. Each "NOWHERE" was *true*: the identifier really is absent from
the file the tool chose. The denominator was mine.

**WHY IT IS A CONVENTION AND NOT A BUG REPORT.** The tool had already been
fixed once for exactly this class and the fix did not generalise. It had a
named third state for the case where the evidence was MISSING, and no state at
all for the case where the evidence was AMBIGUOUS — so zero candidates
refused, and two candidates resolved silently. That asymmetry is invisible in
the output: `found at NOWHERE` reads identically whether the subject was
established or guessed. This is item 8's decay and item 16's non-arrival
wearing a third skin: the check ran, it reached code, and it reached the
wrong code.

**AND WIDENING THE WINDOW IS NOT THE FIX.** A longer lookback moves the error
to a different set of claims; a shorter one converts real checks into
no-subject refusals. Any proximity heuristic has this failure at its
boundary. Tuning the boundary cannot remove it, which is what makes a state
the answer rather than a parameter.

**HOW TO IMPLEMENT IT.**
- **Enumerate the candidates before choosing.** If the resolver returns one,
  proceed. If it returns none, refuse with the existing absence state. If it
  returns more than one, refuse with a **separate, separately counted**
  ambiguity state. `len(set(candidates)) > 1` is the whole test.
- **Report your own wrong answers under your own name.** Where the chosen
  subject lacks the identifier but exactly one other candidate the document
  names *has* it, that is not a document defect — it is a misattribution by
  the tool, and it belongs in a line that says so:
  `MISATTRIBUTED ... MY denominator, not the document`. Fifteen of twenty-one
  findings moved out of "broken" into that line, and the remaining five are
  the real ones.
- **Fail closed on an empty subject list.** The same run, invoked with no
  arguments, printed `TOTALS over 0 document(s)` with every counter at zero
  and **exited 0** — a run that verified nothing, in the same shape and with
  the same exit code as a run that verified all 36. It now exits 2 and says
  `COULD NOT RUN`. Counts must state what was NAMED, what was READ and what
  was ABSENT, because one number cannot carry all three.
- **A tool is allowed to say the finding was its own fault.** Nothing else in
  the output can discover that for you.

**WHERE IT DOES NOT TRANSFER.** A check whose subject is handed to it
explicitly — a path argument, a declared resource, a row key — has no
resolution step and therefore no ambiguity state to add. The rule bites
wherever a subject is *derived*, and proximity is the most common derivation
because it usually works.

---

## 18. One assertion per arm — and a LIVE-TREE assertion never gates the rest

**Adopted in chat 2026-10-07. Derived by fourth from eight red suites
diagnosed one at a time, six of which turned out to be the same root cause
running in two opposite directions.**

**THE CONVENTION: an arm asserts exactly one thing, and an arm whose subject
is the state of the REPOSITORY is reported, never a precondition. If a live
state genuinely invalidates the arms below it, NARROW THE CRITERION AND SAY SO
— do not stop.**

**THE CASE, measured at `eb430f25`, each suite run alone with its own exit
code.** A probe arm that asserts something about the live tree is a drift
tripwire, not a test of the detector, and it goes red on ordinary feature work:

| suite | what the live-tree arm asserts |
|---|---|
| `run_truthy_sum_probe` | the tree has no unbaselined `\|\| 0` addition — 16 appeared in `stonedesk.html:25471–28942` |
| `run_primitive_obsession_probe` | the detector is clean on the tree — 18 new occurrences across five apps |
| `run_subprocess_decode_probe` | no text-mode subprocess call lacks `encoding=` — 40 files do |
| `run_write_path_scan_probe` | the shipped baseline still passes — and a baselined count **fell** |
| `run_removal_path_probe` | every resource has a removal path — one does not |
| `run_export_coverage_probe` | the export registries resolve — three `rf_` resources are missing |
| `preauth_exemption_anchor_probe` | the tree carries zero oracles — it carries at least one |

**And one runs the other way.** `run_completeness_probe` asserts the tool
**still finds** `api/sen-portal.js MANAGEMENT_ROLES`; the tool exits 0 because
that was fixed. A probe pinned to a current defect rots the moment the defect
is fixed — which `tools/run_all_tests.py`'s own header already documents for
two other probes. **Both directions are one defect: the live tree used as the
fixture.**

**ARM ORDERING DECIDES THE BLAST RADIUS FROM AN IDENTICAL ASSERTION, and that
is the half worth paying attention to.** `run_truthy_sum_probe` places the
assertion **last** and still reports 13 passing arms, so the detector is
verified and one line says the tree drifted. `run_primitive_obsession_probe`
placed the identical assertion at **arm 0 as a gate** — `if run_tool() != 0:
print FAIL; return 1` — so it printed one line and ran **none** of its five
mutation arms. **The detector was unverified in either direction, which is
worse than a red arm**, because a red arm is a fact and an unrun arm is a
silence.

**THE GATE WAS NOT GRATUITOUS, AND THE FIX IS THEREFORE NOT A DELETION.** That
probe's per-mutation criterion was `rc != 0`; on a dirty tree the *unmutated*
tool already exits 1, so `rc != 0` is satisfied whether or not the mutation was
caught. Removing the gate alone would have replaced a loud stop with five arms
passing vacuously — strictly worse.

**So the criterion narrows instead of the probe stopping.** Exit **2** is the
fixture lock refusing, and it is unambiguous on a dirty tree because real
findings produce 1 and never 2. When the baseline is dirty every mutation must
produce exactly 2; when it is clean the original `rc != 0` stands; **and the
criterion in force is printed.** The probe went from exit 1 having verified
**nothing** to exit 0 having verified **all five**, while saying out loud that
the claim is smaller.

**ABLATION, because a narrowed criterion that cannot fail is the same defect
again.** A NO-OP mutation — one comment word in the tool, no detector touched —
was planted. Under the old `rc != 0` it **passes vacuously**. Under the
narrowed `exit == 2` it is correctly reported `NOT REFUSED BY THE LOCK -- the
tool exited 1`, probe exit 1. File restored byte-identical, probe back to
exit 0.

**HOW TO IMPLEMENT IT.**
- **One subject per arm.** `run_two_axis_tier_parser_probe` arm 2 says *"raises
  no ROW-LEVEL problem"* and its helper collects HEADLINE-scope problems too,
  so it fails on a fixture that parses perfectly. Two scopes, one arm.
- **An arm must not assert a conditional section unconditionally.**
  `run_financial_invariant_probe` arm 7f requires the literal
  `JUDGED BUT NO LONGER UNGUARDED`, which its subject prints under `if stale:`
  only — so the arm is red **precisely because the register is in order.**
- **If the live state must be asserted, assert it LAST, on its own line, and
  let the rest report.**
- **If it genuinely invalidates what follows, narrow and announce.** Never
  stop silently and never stop loudly-but-totally.

**WHERE IT DOES NOT TRANSFER.** A precondition on the **fixture** — "the
scratch repo was created", "the anchor was found" — is a legitimate gate and
should stop everything, because the arms below really are meaningless and the
fixture is the probe's own responsibility. The line is **whose state it is**:
the probe owns its fixture and does not own the repository.

---

## 19. Object existence is never evidence of reachability

**Adopted in chat 2026-10-07. Derived by fourth from fourth's own wrong
verification, caught one batch later.**

**THE CONVENTION: a claim that a commit is REACHABLE must be tested with
`git merge-base --is-ancestor <sha> <ref>`. `git cat-file -e <sha>^{commit}`
and `git rev-parse --verify <sha>^{commit}` answer a DIFFERENT question —
does the object exist — and they answer OK for a commit no ref reaches.**

**THREE STATES, and an existence test sees two:**

| state | `cat-file -e` | `merge-base --is-ancestor` |
|---|---|---|
| **ON-REF** — reachable | OK | yes |
| **ORPHANED** — in the object store, reached by nothing, gc-eligible here, **absent from every other clone** | **OK** | **no** |
| **ABSENT** — not in this clone at all | fails | no |

**THE FIRST CASE, and it is mine.** On 2026-10-06 a rebase orphaned six of my
own commits twenty minutes after I wrote documents citing them. I re-seated the
citations and wrote that the old SHAs were *UNREACHABLE*, **verified with
`git cat-file -e <sha>^{commit}`** — which returned **OK for all three**. The
evidence I cited contradicted the claim I made and I read the exit code as
confirming it. The conclusion happened to be right; the verification was not,
and **a verification that cannot fail would have let the next re-seat pass
itself as verified.**

**THE SECOND CASE, and it was live in a gate.** `tools/tier_a_review_gate.py`
resolved each review record's subject commit with `rev-parse --verify`, then
diffed against it and printed an ordinary FRESH or STALE verdict. At
`eb430f25` `docs/tier-a-reviews.json` cited **seven orphaned 40-character
SHAs**, and `** STALE ** moved since 00030f2d11b7` was printed on an **open**
obligation — a diff against a commit no other clone has, reported as a plain
verdict. **The gate already contained the right test**: its own
`_is_reachable()` uses `merge-base --is-ancestor`, about 1,500 lines below.
The file carried both methods and the path that mattered used the weaker one.

**WHY IT IS A CONVENTION AND NOT A GIT TIP.** The two commands are
indistinguishable at the call site: same shape, same exit convention, neither
name says which question it answered. And the failure is **silent and
one-directional** — it never reports a reachable commit as missing, only a
missing one as fine, so it always errs toward "this is OK to use".

**HOW TO IMPLEMENT IT.**
- **Reachability uses `merge-base --is-ancestor`.** Existence tests are for
  "can I read this object", never for "is this still on a branch".
- **Accept more than one base when local work is legitimate.** The gate accepts
  `origin/main` **or** `HEAD`, because a record opened at an unpushed commit is
  ordinary work and not an orphan.
- **Name ORPHANED separately from ABSENT.** They need different actions: an
  orphan can be re-seated to its rewritten equivalent; an absent commit cannot
  be re-seated to anything and the record has to be retired.
- **Put an arm on the METHOD, not only on the verdict.** A verdict computed
  against an orphaned commit looks exactly like a correct one, so no
  verdict-level arm can catch this.
- **AND BOUND THE WINDOW OF A SOURCE-READING ARM.** The first version of that
  arm sliced ~1,500 lines and swallowed the definition of `_is_reachable`
  itself, so the substring matched whether or not the freshness path called it
  — **with the guard removed the probe stayed green.** An ablation caught it.
  A source-reading arm needs a bounded window, an assertion that the bound
  held, and the extraction exercised in both directions against a synthetic
  source.

**WHERE IT DOES NOT TRANSFER.** When the question really is *"can I read this
blob"* — a cache lookup, a `git show` that is allowed to work on a dangling
object — existence is the right test and reachability is the wrong one. The
rule bites wherever the word in the sentence is **still**, **current**,
**landed**, or **on main**.

---

## 20. An arm counts only after an ablation shows it can fail

**Adopted in chat 2026-10-07. Derived by fourth from fourth's own arm, which
passed while testing nothing.**

**THE CONVENTION: a new arm is not evidence until the thing it guards has been
removed and the arm has been seen to FAIL. Until then it is an assertion about
nothing, and it reports in exactly the same shape as one that works.**

**THE CASE, and it is the second-order version of item 19.** On 2026-10-07 I
wrote an arm to enforce convention 19 — *the freshness path must ask
reachability, not existence* — by reading the subject's own source and looking
for `_is_reachable(`. It passed. I was about to ship a convention, a fix, and a
guard, and report all three verified.

The arm sliced the source from the resolve message to `def _file_set_index` —
**roughly 1,500 lines** — which **swallowed the definition of `_is_reachable`
itself.** The substring was present whether or not the freshness path called it.

**With the guard removed, the probe stayed GREEN.** The ablation is the only
reason I know.

    guard removed  -> probe exit 0   <- WRONG, and indistinguishable from correct
    guard restored -> probe exit 0

After bounding the window to 3,000 bytes and truncating it at
`def _is_reachable`:

    guard removed  -> probe exit 1, naming both arms
    guard restored -> probe exit 0
    subject restored byte-identical

**AND IT CAUGHT A SECOND ONE THE SAME DAY.** Fixing
`tests/run_write_path_scan_probe.py` under item 18, the repaired arm was ablated
by making the ratchet intolerant of a fall — the arm **failed**, as it must. Had
it not, the fix would have been a second arm that could not fire, landed under a
commit message claiming it was verified.

**WHY IT IS A CONVENTION AND NOT ADVICE.** The platform already has *"build the
control that makes it fail before you trust the run that says it passed"* as the
unnumbered rule under the whole document. **This is the narrow, checkable case
of it**, and it needs numbering because the unnumbered form has not stopped it:
a vacuous arm is written *while fixing something else*, in the same commit as
the fix, and the green it produces is read as confirming the fix. Attention is
on the subject, not on the guard.

**It is also the one failure mode an arm cannot report.** A wrong arm fails
loudly and gets fixed. A **vacuous** arm passes, and passing is what it was
written to do.

**HOW TO IMPLEMENT IT.**
- **Remove the guard and run the arm.** Not a mutation of the arm — a removal of
  the thing it guards. If the arm still passes, it is not an arm.
- **Restore and verify byte-identically.** An ablation that leaves the subject
  changed has replaced one unverified state with another.
- **Bound every window a source-reading arm opens**, and assert the bound in its
  own arm. An unbounded window is the commonest way an arm becomes vacuous,
  because it eventually contains the thing being searched for.
- **Exercise the extraction in BOTH directions against a synthetic subject** —
  one that has the property and one that does not. *Reject everything* and
  *accept everything* both pass a one-sided test.
- **Say in the commit that the ablation ran, and what it returned.** "Verified"
  without an ablation means the arms were run, not that they can fail.

**WHERE IT DOES NOT TRANSFER.** An arm whose subject is a pure function of its
own fixture — a parser fed a literal, an arithmetic check — has nothing to
ablate; the fixture *is* the ablation, and a wrong fixture fails immediately.
The rule bites wherever an arm reads **live state**: source text, a repository,
a registry, a running tool's output.

**Cause tag for the defect behind it:** `test-design/arm-vacuity/unbounded-window-swallowed-the-subject`.

---

## 21. A bound measured against the tool's INPUT is not a bound on its SUBJECT

**Adopted in chat 2026-10-07. DERIVED BY CODY, routed to fourth because fourth
holds this file, and written here VERBATIM from
`docs/2026-10-07-cody-routed.md` §3 rather than paraphrased.**

**THE CONVENTION: before setting any timeout at 2× a measurement, identify the
exact artifact the bounded call is handed — a transform of a file, a generated
fixture, a worst-case payload — and measure THAT. The thing you happen to have
on disk is a convenience sample.**

**THE CASE, in cody's own figures.** `metamorphic_check.py`'s unmeasured 120s
bound was replaced with **40s**, derived honestly as 2 × the 18.24s worst case
of six checkers against `stonedesk.html`. It then fired on **three runs out of
three, EXIT 2 each.**

A metamorphic check runs each checker against the file **and each TRANSFORM of
it**. `t_duplicate` returns `lf + '\n' + lf`, so the real subject is **5.51MB**,
and `duplicate_global_check.py` goes **0.82s → 71.54s** on that 2× input —
**87×**, superlinear in duplicate ids. **The correct bound is 145s, HIGHER than
the 120 it replaced. The tightening broke a working tool.**

**THE TEST TO APPLY: name the exact bytes the bounded call receives on its worst
invocation. If that is not the artifact you timed, you have not measured the
bound.**

**Why it sits beside item 4** (alarm tighter than the failure point) rather than
inside it: item 4 is about leaving margin below a *known* limit. This is about
the limit having been measured against the wrong object, so the margin is
computed from a number that was never the subject. A tighter alarm on a wrong
measurement is worse than a loose one on a right measurement, which is the part
that is not obvious.

**Full postmortem:** `docs/postmortem-cody-2026-10-07-bound-measurement.md`.

**Cause tag:** `measurement/denominator/bounded-call-receives-a-different-artifact`.

---

## 22. A WINDOW is a measurement, and an unbounded one measures the wrong thing

**Adopted in chat 2026-10-07. Derived by fourth from the same mistake three
times in three days, in three different roles.**

**THE CONVENTION, in one line: any window a check opens over text — a source
slice, a lookback, a grep context, an extraction range — is a MEASUREMENT with
its own bound, and the bound is asserted by its own arm, because an unbounded
window eventually contains the thing being searched for and then the check
passes on itself.**

**THREE INSTANCES, AND THE ROLE CHANGED EACH TIME, WHICH IS WHY IT IS A
CONVENTION AND NOT A BUG.**

1. **As a CHECK (convention 17).** The gap-document verifier's 1,200-character
   lookback picked the nearest named app on a document covering three verticals,
   and reported **15 citations as broken** that were all true of the wrong file.
2. **As a GUARD (convention 20).** The arm written to enforce convention 19
   sliced ~1,500 lines of source and **swallowed the definition of the function
   it was searching for**, so the substring matched whether or not the code
   called it. With the guard removed the probe stayed green.
3. **As a READ, with no tool involved at all.** Reviewing cc's obligation I ran
   `sed -n '459,500p'` over a tuple that runs past line 500, read four entries,
   and **reported a correct addition as missing.** By AST it has eight. The
   window was a shell argument and the subject was my own eye.

**The third is the one that makes the rule general.** A tuning parameter in a
tool can be argued about. The same mistake made by a person reading a file is
not a parameter — it is the shape, and the shape is *a bounded view presented
as the whole*.

**HOW TO IMPLEMENT IT.**
- **Name the bound and assert it.** Convention 19's arm now carries *"the window
  this arm reads was LOCATED and is bounded well short of `def _is_reachable`"*
  as an arm of its own, and it fails first.
- **Truncate at the thing you are searching for**, not at a byte count alone, so
  the window cannot contain its own answer.
- **Widening is not the fix.** A longer lookback relocates the boundary; a
  shorter one converts real checks into refusals. Any proximity heuristic fails
  at its edge, which is why convention 17's answer was a STATE and not a bigger
  number.
- **For a read, prefer a parser to a window.** `ast.literal_eval` on the tuple
  answered in one line what a `sed` range got wrong. The same holds for the
  AST comparison that replaced my grep when checking hank's *"docstring only"*.

**WHERE IT DOES NOT TRANSFER.** A window over a stream you are deliberately
sampling — the last N lines of a log, a head of a huge file — is a sample and
should say so. The rule bites when the window is presented as **the extent of
the subject** rather than as a sample of it.

**Cause tag:** `measurement/window/unbounded-view-presented-as-the-whole`.

## 23. A BRIEF IS A SNAPSHOT. Verify its premises before executing it, and record the result PER PREMISE

**Adopted 2026-10-07. DERIVED BY CC** -- routed in cc's batch-14 handoff and
landed here by fourth at cc's credit, not re-derived and re-badged.

**THE CONVENTION, in one line: every factual premise a brief carries about repo
state -- a count, an owner, a claim, a SHA, "X is outstanding" -- is a measurement
taken when the brief was written, and each one is re-derived and its result
WRITTEN DOWN BEFORE the work that depends on it starts, one line per premise, under one of FIVE verdicts.**

**WHY PER PREMISE AND NOT "I CHECKED".** A single "premises re-derived" line is
indistinguishable from not having checked. The record has to be per premise
because the premises fail *independently*: a brief with six facts in it is
usually right about four of them, and the two it is wrong about are the two that
change what you do.

**CC'S INSTANCE, which is the one that names the shape: A THREE-WAY CHOKEPOINT
STALE IN BOTH DIRECTIONS.** Three sessions -- cody, hank and fourth -- each
independently re-derived that cc held `tools/sairn_push_gate_hook.py`,
`tools/report_only_checks.py`, `tools/doc_sha_reseat.py` and
`docs/tool-owner-map.json`, and each narrowed its own batch around that. **cc had
released that claim at the close of batch 14 and `sairn_claim.py list` showed no
cc row at all.** Three sessions blocked themselves on four files nobody held. The
same read was stale in the other direction at the same time: a Tier A ledger that
two sessions stood down from was held by nobody either. **Nothing was wrong with
any of the three sessions' reasoning. The input was old.**

**FOURTH'S INSTANCE, from the batch that landed this section, measured rather
than recalled.** The batch-16 brief carried four state premises. Re-derived
before execution:

| premise as briefed | re-derived | verdict |
|---|---|---|
| ablation **7 of 8**, `truthy_sum` outstanding | a stopped session had recorded it DONE; its evidence file **does** exist -- in that session's scratchpad, not the resumed session's -- and its numbers are right for the lever it pulled, which was **not** the lever the brief named | **STALE, AND MY FIRST VERDICT ON IT WAS ITSELF WRONG.** I called the evidence absent after looking in the wrong one of two directories, and called the record wrong after not reading it. Corrected in the same document rather than edited out -- see the note under this table |
| census **40 of 83** | 40, and ten rows already edited uncommitted on a basis whose run output was gone | **STALE** -- right as a number, wrong as a state |
| orphans **84**, 28 mine, 56 others' | **93**, 18 mine, 75 others', under a written-down predicate | **DIFFERENT DEFINITION, not drift** |
| `__file__` sweep **424 of 1214** | **974 of 1227** under a stated predicate; the 424's predicate was never recorded | **NOT REPRODUCIBLE** |

**THE FOURTH-INSTANCE TABLE ABOVE CARRIES A CORRECTION TO ITSELF, and it is left
visible because a convention about verifying premises cannot cite a premise it got
wrong.** As first written, the ablation row read *"BOTH WRONG -- the brief and the
record"*. Both halves of that were mine and both were wrong:

* **"the evidence file does not exist".** It exists. A resumed session gets a NEW
  scratchpad directory; I checked the resumed one and reported absence from the
  original. **Looking in the right SHAPE of place and the wrong place is not a
  check** -- it is this convention's own failure mode applied to a file path.
* **"the direction it recorded is contradicted".** It is not. The record is
  accurate for the lever it pulled -- FILLING the baseline, 46 → 54 keys, tool
  1 → 0, probe 1 → 0. The brief named the opposite lever, EMPTYING, and that
  session had measured it too, in a second file, as *"COULD-NOT-RUN -- the lever
  never engaged"*. **The record was true and its LABEL was missing.**

The correction is the more useful result: emptying the baseline does nothing on a
dirty tree and everything on a clean fixture; filling it does everything on a
dirty tree. **The layer is only measurable from a clean baseline, in whichever
direction you reach it** — which is convention 12 arriving as a measurement.

**And it sharpens this convention rather than weakening it. THE FIFTH VERDICT IS
NOW PART OF IT: `WRONG-BY-MY-OWN-CHECK`, adopted in chat 2026-10-07, one batch
after the rest of the section** — where the premise stands and the RE-DERIVATION is
the faulty part. A premise check is itself a measurement and gets the same
treatment as any other: read the artefact, not the shape of where it should be.

**It was deliberately NOT self-added when it was found.** Adding a verdict to a
convention an hour after chat adopted the convention is a change to what was
adopted, so it sat in this note as a proposal until chat decided — which is
convention 11 applied to a convention rather than to a tool. The credit line at the
top of this section is unchanged: **the convention is still cc's**; the fifth
verdict is an amendment to it, from fourth's own mistake inside it.

Four premises, four different failure modes, and **one of them was a record this
same session had written an hour earlier**. Checking your own last line is not
paranoia; it is the cheapest check on the list. **And the fifth verdict exists
because that same row needed TWO passes:** the premise check was wrong, and only
re-checking the premise check found it.

**HOW TO IMPLEMENT IT.**
- **One row per premise, with the verdict in it.** The table above is the
  deliverable, not a preamble to it.
- **Distinguish the FIVE verdicts** and do not collapse them:
  **CONFIRMED**; **STALE** (was true, no longer); **WRONG** (never true);
  **NOT-REPRODUCIBLE** (the predicate is unrecorded, so it can be neither
  confirmed nor denied); and **WRONG-BY-MY-OWN-CHECK** (the premise stands and the
  RE-DERIVATION is what is faulty). NOT-REPRODUCIBLE is the one that gets written
  down as "confirmed" when nobody is strict. WRONG-BY-MY-OWN-CHECK is the one that
  never gets written down at all, because the only person positioned to notice it
  is the one who just finished being satisfied.
- **A released claim is not a held claim, and `list` is the authority** -- not the
  claim text of a sibling session, which is itself a snapshot.
- **Re-derive, then narrow.** Narrowing scope against a stale premise costs the
  work twice: once for the thing you did not do, once for the thing you did
  instead.

**WHERE IT DOES NOT TRANSFER.** A brief's *intent* is not a premise and is not
re-derivable -- if the dispatch says do X, re-deriving does not license doing Y.
This convention is about the facts a brief asserts, never about its instructions.

**Cause tag:** `process/brief/premise-taken-as-current-state`.

---

## 24. A LEG THAT RETURNS SUCCESS ON A FAILED LEG IS A SILENT SKIP, and must fail loud

**Adopted 2026-10-07. DERIVED BY CC** -- routed in cc's batch-14 handoff and
landed here at cc's credit.

**THE CONVENTION, in one line: when a composite operation reports the status of
the LAST thing that ran rather than the WORST thing that ran, its success means
"I reached the end", which is not the question anyone asked -- and that is a
SILENT SKIP, the third state of PR 1.11 wearing a green badge.**

This is the sibling of item 8 and of convention 19, one layer out. Those are
about a check that cannot fail. This is about a check that CAN fail, DOES fail,
and has its failure overwritten by a later leg's success.

**CC'S INSTANCE, as cc measured it and NOT re-run by fourth, stated so rather
than implied:** `tools/defect_register.py --reseat` returned **0** while leaving
the register **failing its own `--check`** -- it re-seated 12 records and took
`--check` from 0 to **FAIL, 4 duplicates**. The re-seat leg succeeded; the
validity leg was not consulted; the exit code reported the first.

**THE SAME SHAPE, VERIFIED IN THIS CLONE WHILE THIS SECTION WAS BEING WRITTEN, by
this platform's own hook.** `tools/exit_status_attributable.py` interrupted three
commands in one session with the same warning: a command of the form

    python tools/<checker>.py | head -40        # status comes from head
    <checker> && git commit                     # status of whichever ran LAST
    python tools/<checker>.py > out 2>&1; echo $?   # the correct form

**takes its exit status from `head`, from `grep`, from `tail` -- "a text filter,
which exits 0 for *I ran* and says NOTHING about the program before it".** The
hook's own note records the cost: that misreading **put a false "EXITS 2 (COULD
NOT RUN)" accusation against a working checker into a standing document on
2026-10-04.** The shape is not confined to tools; it is in the shell line you type
to measure one.

**HOW TO IMPLEMENT IT.**
- **Fail on the WORST leg, not the last.** A composite's exit code is the maximum
  severity across its legs, and COULD-NOT-RUN is its own code (2), never folded
  into either 0 or 1.
- **Name the leg in the message.** "FAILED" without which leg sends the next
  reader to the wrong half.
- **A leg that WRITES must re-run the leg that VALIDATES**, in the same
  invocation. A writer that leaves its subject invalid and exits 0 is this
  convention's exact centre.
- **Measure a tool alone.** `<tool> > out 2>&1` then read `$?` on its own line. No
  pipe, no `&&`, no `;` chain, when the status is the thing being claimed.
- **An arm that proves it:** make one leg fail and assert the composite's exit
  code moves. If it does not, the leg is decorative.

**WHERE IT DOES NOT TRANSFER.** A deliberately best-effort sweep that is
DOCUMENTED as best-effort and reports per-item status may exit 0 having had
failures -- but then its exit code is not a verdict, must not be read as one, and
it has to say so in its own output.

**Cause tag:** `verification/composite-exit/last-leg-overwrites-failed-leg`.

---

## 25. AT THREE FALSE-POSITIVE CLASSES FROM ONE CHECKER, STOP PATCHING AND REVIEW THE DESIGN

**Adopted 2026-10-07. DERIVED BY CC** -- routed in cc's batch-14 handoff and
landed here at cc's credit.

**THE CONVENTION, in one line: the third DISTINCT CLASS of false positive from a
single checker is a design signal, not a third bug, and the response is a review
of what the checker is matching on -- not a fourth narrowing.**

**CLASS, NOT COUNT, AND THE DIFFERENCE IS THE WHOLE RULE.** A hundred instances of
one class is one bug. Three instances of three classes is a predicate that does
not model its subject. The trigger counts CLASSES.

**CC'S INSTANCE:** `tools/doc_sha_reseat.py` accumulated false-positive shapes
until `1234abcd` and other **test strings** were sitting in a standing register as
dead citations -- cc's own tool's error, recorded as such. The remedy cc reached
for was an arm **per false-positive shape**, which is right and is also the tell:
when the arms are enumerated by shape rather than by behaviour, the predicate is
being fenced rather than fixed.

**FOURTH'S INSTANCE, same family, found this batch:**
`tests/phi_cache_scoped_to_user.js` arm 5a matched `[ls][dt]\('(sen_[a-z_]+)'`
over a raw single-file app and counted **a comment that exists to say the key is
never written** as the key being written. `tests/lib/strip_comments.js` -- the
shared library this platform built after **three** private comment-stripping
versions were each wrong in a different direction -- exists precisely because that
threshold was crossed once already and the design review was the right answer.
That library's own header is the artefact of this convention being followed before
it was named.

**HOW TO IMPLEMENT IT.**
- **Keep a CLASSES LIST, not a count.** Name each false-positive class as it is
  found, in the tool's own header. Three named classes is the trigger.
- **At the trigger, ask what the predicate is standing in for.** "Text matching
  `st('key')`" was standing in for "a localStorage write", and the right fix was
  to parse code rather than to exempt prose case by case.
- **Prefer a stricter MODEL to a narrower PATTERN.** Narrowing clears the known
  instance and fails silently on the next phrasing; in a detector a false negative
  is invisible where a false positive is loud and gets read (scrubber item 24).
- **Reuse before you re-derive.** If a shared module already exists for the harder
  version of the problem, the fourth private copy is the finding.
- **A design review is not automatically a rewrite.** The output may be "the
  predicate is right and these three really are exceptions" -- but that is then a
  recorded decision with its reasons, not an accumulation of patches.

**WHERE IT DOES NOT TRANSFER.** A checker deliberately tuned to over-report on the
safe side -- `truthy_sum_check.py` reports a call on the left operand because
over-reporting is the safe side there -- is not accumulating false positives, it
is implementing a stated policy. The rule bites when each exemption was a surprise.

**Cause tag:** `detection/predicate/exemptions-accumulated-instead-of-reviewed`.

---

---

## The failure mode TEN of the twenty-five share

*(Denominator moved 2026-10-07 when cc's 23, 24 and 25 were landed, and the membership question was asked of all three rather than assumed. **24 IS A TENTH MEMBER.** A leg that returns success on a failed leg is a check that reads as coverage and structurally cannot fail in the direction that matters -- it never turns a passing subject red, only a failing one green, which is item 8's shape one layer out from the checker and into its composition. **23 IS NOT A MEMBER:** it is not a check at all, it is a discipline about the INPUT to work. **25 IS NOT A MEMBER:** its subject is a checker that fires loudly and too often, which is the opposite failure. So the NINE is now a TEN and the heading has been changed rather than left to drift -- and the nine-member list itself is otherwise unchanged.)*

*(Count corrected 2026-10-06: this heading read "eight of the eleven" when the document had eleven numbered sections, and was not updated when 12 was added on 2026-09-25 or when 13, 14 and 15 were added on 2026-10-06, or when 16 followed them. The EIGHT is unchanged and is the load-bearing number -- 12, 13, 14, 15 and 16 are NOT members of that group. Carrying what it said so the correction is visible rather than invisible, per the numbering note at the end of this file.)*

*(Denominator moved again 2026-10-07 when 22 was added. **22 IS NOT A MEMBER of the nine, and the question was asked.** Its instances all PRODUCED an answer -- 15 findings, a green probe, a wrong review note -- so the check fired every time; what was wrong was the EXTENT it measured. That is a measurement fault like 21, not a cannot-fire fault. The nine is unchanged.)*

*(Denominator moved 2026-10-07 when 20 and 21 were added. **NEITHER IS A MEMBER OF THE NINE, and the question was asked of both.** Item 20 is about an arm that CANNOT fire -- which sounds like the group -- but the group is about a CHECK that reads as coverage, and 20 is about the GUARD ON a check; folding them would lose the distinction between a check that cannot fire and a guard that cannot fire, and 20 exists because the second is written while fixing the first. Item 21 is a measurement error, not a check at all. The nine is unchanged.)*

*(Denominator moved 2026-10-07 when 18 and 19 were added, and the
membership question was asked of both rather than assumed. **19 IS A NINTH
MEMBER and is the first addition since 11 that belongs in the group:** an
existence test used as a reachability test is a check that reads as coverage
and structurally cannot fail in the direction that matters -- it never reports
a reachable commit as missing, only a missing one as fine. **18 is NOT a
member:** its arms fire, loudly; its defect is that one of them takes the
others down with it, which is a blast-radius property and not an inability to
fire. The EIGHT is therefore now a NINE, and the sentence below has been
changed from "eight" to "nine" rather than left to drift.)*

*(Denominator moved 2026-10-06 when 17 was added. 17 is NOT a ninth member and the question was asked rather than assumed: the shared failure mode is a check that reads as coverage and STRUCTURALLY CANNOT FIRE, and item 17's check fires -- it fires on the wrong subject and reports a guess in the shape of a measurement. That is adjacent to item 8's loss of independence, not identical to the eight. Left out of the group deliberately; putting it in would have been the easier edit and the wrong one.)*

Ten of these conventions defend against the same thing: **a check that reads as
coverage and structurally cannot fire.** (Items 7, 9 and 10 are the exceptions
and are worth holding separately. Item 7 defends against a correct thing moved
into a context where its assumptions no longer hold, which none of the others
would catch; item 9 is upstream of every check — it prices how much rigor an
item deserves before any check exists, so it cannot share a failure mode with
the checks it sizes; item 10 is about a check that fires correctly and fires
TOO LATE, which is a property of the schedule rather than of the check.)
A criterion tuned to the data.
A score that averages away the half that broke. A rate over a denominator
nobody stated. An alarm set at the cliff edge. A validation fed by its own
subject. A replication that shares a blind spot. An anchor that quietly stopped
matching.

**Item 24 is the TENTH member, added 2026-10-07 and derived by CC.** It is item 8
one layer out: not a check whose criterion cannot fail, but a check whose real
failure is *overwritten* by the success of a later leg -- a `| head` on the end of
the command, a `--reseat` that exits 0 having left its own `--check` red. It never
turns a passing subject red, only a failing one green, which is this group's
definition. See section 24 for both instances.

**Item 19 is the NINTH member, added 2026-10-07, and it is the cheapest of
the nine to commit by accident:** `git cat-file -e <sha>^{commit}` and
`git merge-base --is-ancestor <sha> origin/main` have the same shape, the same
exit convention, and neither name says which question it answered. An
existence test used as a reachability test **never reports a reachable commit
as missing, only a missing one as fine** -- it cannot fail in the direction
that matters, which is this group's definition. It was found twice in one
batch: once in fourth's own re-seat verification, where the evidence cited
contradicted the claim made, and once live in `tools/tier_a_review_gate.py`,
which printed `** STALE ** moved since 00030f2d11b7` against an ORPHANED
commit on an open obligation.

**Item 11 is the eighth member, and it arrives last among the original eight
because it is the newest spelling of the oldest failure here:** a fixer that applies its own repair
produces output indistinguishable from a check that passed, for the same
reason item 8's `--check` did when it compared a document to its own output.
The comparison is real; the independence is gone.

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
