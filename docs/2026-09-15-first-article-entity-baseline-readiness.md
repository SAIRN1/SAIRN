# Item 47 — First Article Inspection on `tools/entity_baseline_readiness.py`

**2026-09-15 (Fourth).** Report only, never gated, per the item's own terms.

**Subject:** `tools/entity_baseline_readiness.py` (item 51), built earlier the
same session. Chosen because it is the freshest and least-scrutinised artefact
on the platform: written, probed and pushed inside one round, with no
independent reader between it and `main`.

**Machine-readable record:** `docs/first-article-inspections.json`.
**Gate:** `python tools/first_article_check.py`.

---

## Why an FAI when the tool already shipped green

It shipped with 12 self-check arms, a 21-arm probe, and an 11-mutant sweep in
which 9 mutants died, 1 was equivalent, and the last one earned a new arm. That
is a good result and it answers a different question.

Mutation testing asks **"can my arms detect a change to the code I wrote."**
FAI asks **"is every requirement I STATED actually verified."** A tool can kill
every mutant in the code that exists and still carry a sentence in its own
header that no arm has ever exercised — because a mutant can only be written
against code, and an unverified claim's failure mode is that the code path was
never interesting enough for anyone to mutate it.

That is exactly what happened here.

## Result

| | claims in the header | arms before | **unverified at start** | unverified now |
|---|---|---|---|---|
| `tools/entity_baseline_readiness.py` | 13 | 33 | **5** | **0** |

Two claims are dispositioned `cannot-test` rather than verified, and that is a
distinction the arm-by-arm view cannot make — see the last section.

## The five claims nothing checked

Every one of them turned out to be **true**. The finding is not that the tool
was wrong; it is that nothing would have said so if it had been.

**1. "Exit 0 when at least one entity is ready."**
Every exit-code arm tested the *not-ready* side. The tool could have returned 1
unconditionally and passed the whole suite — and since it reports NOT READY on
today's register and will for months, nobody would have run the other path by
accident either. This is the sharpest of the five: the claim that could stay
false longest without anybody noticing.

**2. "Exit 2 when the question could not be answered."**
The `COULD NOT RUN` branch had no arm. An unreadable register would have been
indistinguishable from "nothing is ready" to anything watching the exit code —
a could-not-run folded into a finding, which is the **PR §1.11** shape precisely,
inside a tool whose own header cites that discipline.

**3. "REPORT ONLY — nothing gates on this."**
Stated in the header and enforced nowhere, despite being mechanically checkable
three different ways: not in the report-only runner `REGISTRY`, present in
`NOT_PROMOTED` as a deliberate decision, and absent from the push gate. All
three are now asserted.

**4. "…the exclusion is PRINTED, because a silent exclusion is a different tool
from a declared one."**
The exclusion *count* was asserted. That it reaches the printed page was not —
and `PRINTED` is the load-bearing word in that sentence. The claim's own
justification is about what a reader sees, so an arm on the data structure
verifies the half that does not matter.

**5. "One ready unit is not a comparison, and a baseline is one."**
The self-check asserted `MIN_READY_UNITS >= 2`. **A constant is not a
behaviour.** The comparison in `assess()` could have been written `>= 1` and
that arm would not have moved. Now there is a register with exactly one
qualifying app, and it is asserted NOT READY *and* asserted to give the VOLUME
reason, so the right verdict for the wrong reason would still fail.

All five arms were mutation-tested after being written. Four killed their
mutant immediately; the fifth (`ready_branch_off`) killed it once the mutant was
written correctly — the first attempt was `return 1 and finish(...)`, which is
`finish(...)`, an equivalent mutant rather than a surviving one.

## What FAI could NOT settle, and why that is the useful part

Two of the thirteen claims have no arm and never will, and separating them from
the five above is the judgement an arm-by-arm view cannot make.

- **"It does not compute a baseline."** A claim about SCOPE. There is no code
  path to assert the absence of, and an arm checking that some future field is
  missing passes forever on any tool that never grows one.
- **"Nothing here derives the bar."** A claim about PROVENANCE. No arm can show
  a number was not fitted to the data after the fact. It is held by the constant
  being a literal with its rationale beside it, and by the 2026-09-14 findings
  document the 20–30 range is quoted from.

Recording these as `cannot-test` rather than `verified` is the point. Both would
pass a word-overlap matcher against half the arms in the suite, which is one
more reason the mapping is not automated.

## What this inspection does NOT claim

- **An arm existing is not an arm being right.** FAI checks coverage, not
  correctness. The mutation sweep is what covers correctness here.
- **One artefact.** Nothing here says anything about the rest of the tool tree.
  `tools/first_article_check.py` prints the uninspected count on every run, and
  the number is deliberately not written here: a count in prose goes stale the
  first week and nothing makes it fail.
- **The claim-to-arm mapping was made by reading, not generated.** Word-overlap
  scoring of prose claims against prose arm labels returned 38% with five false
  positives out of five on this platform (2026-09-14), and the extractor in
  `--worksheet` is labelled a worksheet for that reason. It is never used to
  count anything.
- **The requirement is forward-only, from 2026-09-16.** 22 tools were first
  committed on 2026-09-15 by four sessions in parallel; none could have followed
  a rule that did not exist yet. This subject pre-dates the requirement as well
  and is inspected anyway, because it is the first article.
