# Arms that assert on a message, not on behaviour — swept, mutated both ways, and one converted

**2026-09-29 (Hank), queue25 item 11.** Three criteria of mine were wrong in one
session, each aimed at TEXT rather than at behaviour, each caught before it was
reported and none caught by review. Ted's was the same class. So: sweep every arm
in `tests/`, mutate the guarded behaviour out and confirm the arm fails, then
change only the wording and confirm it still passes.

---

## 1. The sweep — `tools/message_assertion_audit.py` (NEW, report-only)

One question of every assertion: **does it assert on anything other than a string?**

| | |
|---|---|
| test files read | **589** (358 python, 231 javascript) |
| UNPARSEABLE | **0** — counted, never folded into clean |
| assertions classified | **10,718** |
| … on a STRING only | **1,464** |
| … on a VALUE | **2,755** |
| … COULD NOT CLASSIFY | **6,499** — a third state, over half the corpus |
| python: assertions / string-only | 5,914 / **211** (parsed with `ast`) |
| javascript: assertions / string-only | 4,804 / **1,253** (regex — **an estimate**) |
| **files where string checks are at least half the classified assertions** | **43 of 230 scoreable** |

**The javascript half is not folded in.** Python goes through `ast`, so "the first
argument is a containment comparison" is a fact about the tree. JavaScript is
regex. Two different kinds of evidence, reported separately.

**6,499 UNKNOWN is the honest weak point of this tool**, and it is excluded from
the ratio's denominator on purpose — folding it either way would decide the answer
by how much the tool failed to parse.

### The criterion, and BOTH of its first two versions were wrong

**v1 called any equality against a string literal a message assertion.** One
corpus run showed the cost: **nine mutation controls** came back as "every
assertion is a string check", when what each of them asserts is
`assert.strictEqual(fs.readFileSync(clean, 'utf8'), ORIGINAL)` — **a whole-file
byte comparison against a saved baseline, the strongest behavioural check in this
repository.** And `strictEqual(handle(null), 'REFUSED')` is an assertion about a
return value that happens to be spelled with letters.

> **The defect class is a check that some WORDS APPEAR IN captured output or in a
> source file. CONTAINMENT, REGEX and COUNT are TEXT. EQUALITY is VALUE.**

**v2 fixed that and then its FINDING UNIT was wrong.** It asked for a file whose
*every* assertion is text. Over 589 real files that returns **zero** — every file
has at least one value or unclassified assertion. A tool sitting on 1,464 string
assertions reported no findings. **A criterion that cannot fire on its own corpus
has not been validated, it has been flattered.** The unit is now the file's ratio
over its classified assertions, and `tests/run_message_assertion_probe.py` carries
the arm that would have caught it: *the finding count must be neither 0 nor the
whole denominator*.

### Stated limits

* It mutates nothing. Whether an arm SURVIVES having its behaviour removed is a
  question only a mutation answers; this names the population.
* A file with 40 value assertions and one fragile message check is invisible, by
  design — guessing arm boundaries across four label conventions
  (`ok(cond,label)`, `arm(label,cond)`, `t(label,fn)`, `test(label,fn)`) would
  mis-attribute findings, and a mis-attributed finding is worse than a coarse one.
* `assert out == 'the exact expected report'` is a message assertion and this rule
  calls it VALUE. Rare here; the alternative mis-sorts more than it fixes.

---

## 2. The both-ways mutation — three subjects, on a scratch copy

Each subject was mutated twice in a throwaway copy of the repo: **A** rewrote
user-facing phrases and changed no behaviour; **B** removed the guard the probe
exists for and left every message intact.

### `tools/hedge_carry_check.py` — 12 arms

| | |
|---|---|
| **A. reword only** | **0 arms failed.** No arm depends on the wording changed. |
| **B. behaviour out** (every `DROPPED` verdict forced to `CARRIED`) | **1 caught, 5 still passed, 1 could not run.** |

**The baseline itself had 5 failing arms in the scratch copy**, and that is the
finding: the probe's known-bad arms need **a real commit from this repository**,
and the scratch copy is a fresh `git init` with one commit. So in an isolated tree
the probe cannot exercise the DROPPED path at all, and what caught the mutation
was the tool's own `--selftest`. **The five survivors are the fail-closed arms**
(exit 2 on a missing `--range`, `--item`, unreadable range, absent `--item-file`) —
correctly unaffected by a verdict change.

### `tools/citation_no_source_report.py` — 29 arms

| | |
|---|---|
| **A. reword only** | **2 arms are TEXT-DEPENDENT.** |
| **B. behaviour out** (`CITE` forced to match everything, so no row cites nothing) | **18 caught, 11 still passed, 0 could not run.** |

**Both text-dependent arms are correct as message assertions, and that judgement
is the point of the exercise rather than a get-out:**

* *"it says the number is coverage rather than bugs"* — the requirement **is** that
  sentence. `209 findings` reads as 209 defects; the report must say otherwise.
* *"it says which rule it is NOT"* — the requirement is that a reader does not take
  this report for the write-site rule that was measured and declined.

Where the message **is** the contract, an arm pinning it is doing its job and
failing on a reword is correct. What was missing is saying so, so nobody "fixes" it
by deleting it.

### `tools/tier_a_review_gate.py --reseat-shas` — 26 arms, and THIS one produced a real fix

| | before | after the fix |
|---|---|---|
| **A. reword only** | 1 TEXT-DEPENDENT | 1 TEXT-DEPENDENT |
| **B. behaviour out** (the ambiguity refusal removed) | **1 caught**, 22 passed, 3 could not run | **2 caught**, 25 passed, 0 could not run |

**THE ONE ARM THAT CAUGHT IT WAS A MESSAGE ASSERTION** — *"it says the match is
ambiguous"*. The behavioural arm beside it (*"AND THE SHA IS UNCHANGED"*) could
not: with the ambiguity branch gone, the record fell through to the **subset**
refusal, which refused it too, so the sha was unchanged and the behaviour arm
passed. **Defence in depth made the behaviour identical and only the REASON
differed — and the reason lived in prose.**

**The fix: `--reseat-shas --json` now emits a stable reason CODE per refusal**
(`AMBIGUOUS_EXACT_SET`, `SHA_WRONG_WHEN_WRITTEN`, `NO_OBJECT_IN_CLONE`,
`TWIN_SUBJECT_ABSENT`, `TWIN_SUBJECT_AMBIGUOUS`, `TWIN_CROSSCHECK_UNREADABLE`,
`NO_MATCH_ANYWHERE`, `NO_SHA_AT_ALL`, `NO_FILES_ON_RECORD`, with a
`+SUBSET_AMBIGUOUS` suffix where containment also failed). The probe now asserts
on the CODE. Measured after the change: it **catches the mutation** and **survives
the reword**, which is both directions on one arm.

**And it exposed a second defect while landing:** the JSON was emitted after the
`nothing to reseat` early return, so a ledger whose only dangling records are all
REFUSED printed nothing at all. A machine-readable report that disappears exactly
when every record is refused is useless for the case it exists to serve. Moved
above the return.

### THE HARNESS HAD A HOLE, AND IT PRODUCED THREE FALSE FINDINGS FIRST

The first run reported **three value-only arms in the reseat probe as
"text-dependent"** — including one that compares two shas and cannot depend on any
wording. They had not failed. **They had not run**, and the harness paired arms by
label without distinguishing ABSENT from FAILED.

The cause was in the probe, not the harness: **three arm labels interpolated the
fixture's shas, which are new on every run.** An arm nobody can pair across two
runs cannot be mutation-tested at all. The shas moved into the DETAIL — printed
only on failure, not part of the arm's identity — and `ABSENT` became its own
bucket in the harness. After both fixes: **0 could-not-run in either direction.**

---

## 3. Registered by owner — the 43-file population

**Owner cannot be derived from git here: every commit in this repository is
authored by `Michael Dibert`.** The honest proxy is the APP the file belongs to,
which is derivable from its name, and whoever holds that app's claim is the owner.
Recorded as one index row rather than 43, for the same reason the prose-fallback
backlog is one row: 43 rows naming a guessed owner would be 43 guesses.

**By app / area, 43 files:**

| area | files |
|---|---|
| StoneDesk (`sd_*`, `stonedesk_*`, `slab_*`, `viz_*`, `nesting_*`, `quote_*`, `approval_*`, `idless_*`, `ai_shortcuts_*`, `intake_*`, `st_reports_*`, `seam_check/`) | 15 |
| SAIRNdental (`dnt_*`, `sairndental_*`) | 5 |
| Platform tooling probes (`run_*_probe.py`, `tests/lib/`, `tests/faults/`) | 10 |
| SAIRNscape | 2 |
| SAIRNlegacy | 2 |
| SAIRNmechanical | 2 |
| SAIRNvet | 1 |
| SAIRNbiz | 2 |
| SAIRNcare, SAIRNsenior, SAIRNfreedom, SAIRNlaw | 4 |

The four with the highest string-check counts, for whoever starts:
`tests/sairnscape_memory.js` (33 text / 21 value),
`tests/sairnvet_formulary_source_honesty.js` (33 / 31),
`tests/sairndental_rollup_panel.js` (32 / 10),
`tests/run_master_plan_probe.py` (29 / 22).

**`tests/lib/strip_comments.test.js` is the sharpest of the 43: 28 text and ZERO
value assertions.** Every arm checks whether a string survived a comment stripper,
which is arguably what that library IS — but a stripper whose only evidence is
"the word `keep` is still there" cannot tell a correct strip from one that
returned its input unchanged.

---

## What this sweep did NOT do

* **It did not mutate the 43.** Three subjects were mutated both ways, all three
  mine. The other 43 files are a registered population, not a completed sweep.
* **It did not fix the two justified message assertions** in
  `citation_no_source_report`'s probe. They pin a sentence that IS the
  requirement; what they needed was the note saying so, which they now have.
* **The 6,499 UNKNOWN assertions are unexamined.** More than half the corpus. A
  future pass that shrinks that bucket will move every number above, which is why
  the ratio and not the raw count is the reported unit.
