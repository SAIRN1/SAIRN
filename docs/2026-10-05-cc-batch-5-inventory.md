# CC batch 5, 2026-10-05 — the cell emitter, a false claim in four places, and a standing check that would have caught two

**Every figure measured, driven or run at HEAD. Exit codes read with output
redirected into a file and `$?` on its own line — never off a pipeline, which is
the lesson this batch exists partly to repair.**

Methodology: **every screen reports its blind-spot count on its last line.**

---

## 1. What landed, with shas

| sha | What |
|---|---|
| `39595804` | The `tooling_inventory` cell emitter — 11 malformed rows → 0, plus a pre-write refusal |
| `9e72413b` | The withdrawn `md_table_check` claim: it lived in **four** artifacts, only one was corrected |
| `b8688e80` | The bypass log's own record of my blanket override, **which did not work** |
| `c6d66c11` | `law-auth-custody` — the move-proofing was **half done** |
| `f7d8a78c` | SAIRNcare's audit was **branch-only and PR #18 did not contain it** |
| `7c89e0a7` | `doc_checker_coverage.py` — the standing check, proven against the real event |

---

## 2. The cell emitter — 11 → 0, and **three survived a fix I had already called complete**

**`39595804`. PROVEN: `docs/TOOLING-INVENTORY.md` is 401/401 rows, 0 malformed,
bare exit 0.**

**The escape everyone reaches for cannot work**, which is why this is a function
and not a `.replace()`: inside a code span both a backslash and an HTML entity
render literally. `table_safe()` is context-dependent — `&#124;` outside a span,
U+2502 inside one. **The substitution is a fidelity cost and is declared in the
generated document's own header**: where a cell shows the box-drawing character
twice, the source says the two-character OR operator.

### The part that corrected a claim I made four hours earlier

I sanitised `purpose()` and asserted **"ONE EDIT AND NOT FIVE."** **Eight of
eleven rows cleared and three survived.** `purpose()` is the single accessor for
*purpose text* and is **not** the single accessor for *cell text*: the
promoted-registry table takes `catches` straight out of
`report_only_checks.REGISTRY`, and the not-promoted table takes its reason out
of `NOT_PROMOTED`.

**So the durable fix is not a third sanitised source — it is making a broken
table unemittable.** `malformed_rows()` parses the assembled document before the
write and **refuses at exit 2**, naming every bad row with its cell count and
its header's. A fourth text source added next month inherits that; a fourth
`table_safe()` call site would have had to be remembered.

**Driven both ways:** sanitised → 401/401, exit 0. With an unsanitised cell
planted the way a fourth source would arrive → **exit 2, "REFUSING TO WRITE …
73 row(s) would be malformed"**, and the document is **not touched** — verified
by diff *and* by confirming the planted string appears nowhere in the file.

**And the omission recorded that morning is closed rather than re-argued.**
`TOOLING-INVENTORY.md` was deliberately out of `md_table_check`'s
`DEFAULT_FILES` because it was generated *and* broken. The generator is fixed, so
it is now **in** the list — coverage **2,188 rows over six files** — and
`KNOWN_UNADDED` is empty, kept as the place the next deliberate omission gets
recorded. Probe: **38 cases, 0 failed**, membership asserted by name.

**BLIND SPOTS: 4.** (1) `table_safe()`'s span detection is backtick **parity**, so
a stray backtick picks the other substitution — harmless for structure, both
leave zero literal pipes. (2) `malformed_rows()` takes the **first** row of each
block as its header, so a malformed *header* would set a wrong expectation and
pass the rest — the one shape it cannot see. (3) The 11 figure moves, because the
file is regenerated; what is locked is the invariant. (4) Nothing runs the
generator on a cadence, so a new pipe-carrying `PURPOSES` entry is refused only
when somebody regenerates.

---

## 3. The withdrawn claim lived in **FOUR** artifacts, and only one carried the correction

**`9e72413b`.** Asked to check both artifacts, not one. **Checked — and there
were four.**

| # | Artifact | State before |
|---|---|---|
| 1 | `docs/SAIRN-OPEN-WORK-INDEX.md` row 73 | **corrected** (`7ca1c7b9`) |
| 2 | commit `51548ec9`'s own message | **not, and cannot be** — pushed, asserts it **twice** |
| 3 | `docs/2026-10-05-cc-batch-inventory.md:228` | **not** — corrected here |
| 4 | `docs/2026-10-05-cc-batch-2-inventory.md:365` | **not** — corrected here |

**I had corrected the one I remembered editing, which is the same shape as the
defect.**

**THE LESSON: a claim does not live where you wrote it, it lives wherever it was
copied.** The question to ask of a retraction is not *"did I fix the row"* but
*"how many copies did I make, and what is the search that finds all of them"*.

**Artifact 2 is the one that cannot be repaired**, and the honest handling is
recorded rather than glossed:

* `git log --grep` now returns the corrections — **verified**.
* `git log -S` (diff content) still returns **`51548ec9` alone** — so a reader
  who searches for *where this text came from* gets the false claim without the
  correction. **Not fixed, and it cannot be**: `-S` matches text a commit ADDS
  or REMOVES, and no later commit adds that exact uppercase phrase, so no
  correction can ever appear in that result set.
  > **IF YOU ARRIVED HERE FROM `git log -S`, THAT SEARCH CANNOT SHOW YOU A
  > CORRECTION — USE `git log --grep` INSTEAD.** `-S` will keep surfacing the
  > stale claim in `51548ec9` forever, with nothing beside it. The corrections
  > are in commit MESSAGES, which only `--grep` reads:
  >
  > ```
  > git log --grep="md_table_check" --all
  > git log --grep="EXITS 2" --all
  > ```
  >
  > The rule that generalises: **`-S` answers "which commit introduced this
  > text", never "is this text still true".** A claim withdrawn in prose is
  > invisible to it by construction, so a `-S` hit on an assertion is a lead to
  > check, not a fact to quote.
* A **git note** was attached to `51548ec9` and **does not propagate**: the
  push gate refuses `refs/notes/commits` because it cannot resolve the ref's
  base against `main`, and `SAIRN_SEED_GATE=off` does not cover that check. **The
  gate is right** — failing closed on could-not-tell is the behaviour `PR §1.11`
  demands — so the note is local to this clone only. Logged in `b8688e80` with
  the bypass log's own record of the attempt, because *a bypass log containing
  only the overrides that worked is not a record of anything.*

**BLIND SPOTS: 3.** (1) The four were found by grepping phrases I remember using;
a copy worded differently would not have surfaced, and two true uses of "exit 2"
about other tools were excluded by hand rather than by a rule. (2) Nothing stops
the next false claim being copied the same way — there is no check that a
withdrawn claim's other copies get annotated. (3) The note's content is
unverified by anyone else: it is my correction of my own false claim, the weakest
review available.

---

## 4. The move-proofing was **half done**, and the premise that failed was written down

**`c6d66c11`.** All three arms the 2026-09-29 row named as latent were **already
applied on 2026-09-30**, and all three suites are green — so the dispatch's
premise was stale. **But nobody had planted the refactor they were made proof
against**, and one of the two arms does not survive it.

Planted into `api/law-auth.js`, licence scope entirely intact, only the
concatenation split:

```js
let lmQ = 'law_matters?license_hash=eq.' + enc(licHash);
lmQ += '&matter_id=eq.' + enc(matter_id) + '&select=matter_id&limit=1';
const mr = await fetch(rest(lmQ), { headers });
```

The first arm survived. The **canary** fired, as designed. **And the substantive
arm — "a matter belonging to another firm must not confirm" — went red.**

**The cause is a stated premise that is false.** That arm windowed to the **first
semicolon**, on the written ground that *"a variable build … keeps it inside ONE
statement, so a `;` is the honest boundary."* A `+=` build puts the first
semicolon at the end of line one, so the window held `license_hash=eq.` and
**not** `matter_id=eq.`

**And the `+=` shape is not hypothetical: `api/sd-data.js:10782-10785` builds the
`alf_incidents` query exactly that way** — the same read I worked on this
morning. The premise was tested against the wrong example, which is why reading
the diff could not have found it.

**The boundary is now the consumer, not a punctuation mark.** Three directions
driven, and the third is the one that matters:

| | Planted | Result |
|---|---|---|
| A | inline form at HEAD | **19/19 pass** |
| B | `+=` build, scope intact | **only the canary fires** — exactly what its own text says should happen |
| C | **actually unscoped** lookup | **three arms red**, including the licence-scoping arm — the widening did **not** hollow it out |

**One mistake of mine, kept rather than hidden:** my first planted refactor
renamed `matter_id` to `matterId`, which is undefined in that scope. **It parsed
and it was not faithful**, so it broke the handler at runtime and reddened a
behavioural arm for an unrelated reason — I briefly read that as "the
move-proofing is broken" before re-reading my own mutant. *`node --check` cannot
tell you a mutant is semantically equivalent.*

**BLIND SPOTS: 4.** (1) The other two move-proofed files were **not** driven
against a planted refactor — unmeasured, not claimed. (2) The consumer boundary
assumes a `fetch(rest(` consumer; a query passed to a helper falls to a
900-character budget. (3) The canary now fires on any variable build, so a
legitimate refactor leaves one red arm until somebody updates it — as its author
intended. (4) Nothing drives this on a cadence.

---

## 5. SAIRNcare's audit was branch-only — **my "every app now has an audit" was false**

**`f7d8a78c`.** Asked for "the next of the 2 remaining fully-missing docs."
**Derived rather than assumed, there are zero of those — and one real gap of a
different shape, which is mine.**

I reported yesterday that closing three apps meant *"every app on the platform
now has an audit."* The 2026-09-29 inventory tracked **17** apps and I trusted
its denominator. `git ls-files '*.html'` at the repo root returns **22**.
Cross-referencing every name against `docs/` filenames surfaced **`sairncare`
with no audit on `main`.**

**Its audit existed all along, on `claude/cloud-research-sairncare`, and PR #18
did not contain it.** That PR merged twelve audits and closed the
"nine-of-fourteen are branch-only" finding. **So the finding the merge was meant
to close survived its own closure**, in one branch nobody checked against the app
list, for a further eight days.

Landed the PR #18 way: **all nine internal citations re-derived at HEAD, all nine
resolve.** 411 lines, tables clean. **Branch tip `74e029a5f373` recorded first
and the branch is not deleted** — landing content and deleting a ref are separate
decisions.

**The other four of the 22 are not products** and are named so the gap reads as a
decision: `sairndental-book`, `sairndental-complaint`, `stonedesk-catalog`,
`stonedesk-intake` are public-facing forms with no licence gate.
`stonedesk-hr` (99KB, licence-gated) is a StoneDesk module.

**The correction goes into the inventory itself**, because that is the file the
next session will trust: **an inventory is a claim about a denominator, and that
one never published how it chose its 17.** A coverage document that does not
derive its own universe cannot be used to say *every* — which is what I used it
for.

**BLIND SPOTS: 3.** (1) The 22 is root-level `*.html` and excludes `archive/` — a
better denominator, not a proven one. (2) *"`stonedesk-hr` is covered by
StoneDesk's audit"* is an assertion about scope I did **not** verify by reading
that audit. (3) Three of the nine citations land on closing-`div` lines, which
suggests my regex took the END of a line range — they resolve, but two are weaker
evidence than the count implies.

---

## 6. The standing check — it catches **two** of the five, by one mechanism

**`7c89e0a7`. `tools/doc_checker_coverage.py`:** which markdown files a change
touches are read by **no** structural checker.

**The two it catches share a single cause:** the `CRITICALITY-TIERS.md` row was
malformed because `md_table_check` did not read that file (**B**), and the
hand-rolled checker that then false-flagged three header rows existed **because**
the real tool was blind to it (**C**). One question at commit time answers both:
*is the markdown file I am editing read by anything?*

**Proven against the real event, not a fixture.** With `DEFAULT_FILES` shrunk to
its 2026-10-05-morning state and run on the exact commit range that malformed the
row:

```
1 markdown file(s) in this change are read by NO declared checker:
  UNCOVERED  docs/CRITICALITY-TIERS.md
```

…and exit 1 under `--strict`. **The three-file state is not assumed either** —
read out of git at `5ab3bcb5~1` with `ast`: `DEFAULT_FILES` was **3** files,
`CRITICALITY-TIERS.md` **False**. Today: **6** and **True**.

**It needs no new convention** — 290 `tools/*.py` parse, 12 doc paths across 6
tools, read with `ast` and **never by importing**, because an import runs
module-level code and a coverage report must not be able to change what it
measures.

**Deliberately report-only and a list to read.** Most markdown here is prose and
wants no structural check. **A gate would be cleared by deleting a table**, which
is worse than the gap.

**What it does NOT catch, so the claim is two and not five:** nothing about the
false exit-2 claim (**A**), the matcher fixed at instance rather than class
(**D**), or the fifth pipe caught by an assertion (**E**). A and D are claims
about *behaviour*, not coverage; E happened in a file that **was** covered, and
the lesson there was to assert in the writer rather than check afterwards.

**BLIND SPOTS: 4.** (1) It reads **today's** `tools/*.py`, so it cannot reproduce
a historical verdict without a worktree — the proof needed `DEFAULT_FILES` shrunk
by hand, and `--at <sha>` does not exist. (2) A file set built from a glob, a
config, or assembled inside a function is **invisible** to it, so "uncovered"
over-reports gaps; unquantified. (3) `.md` only. (4) **Nothing runs it on a
cadence** — see §7. So the honest status is: *the answer to "none was found by a
cadenced check" is now "a check exists that would have found two, and it is not
cadenced either."*

---

## 7. Still blocked — checked, not assumed

**Hank's refuse-at-import intake fix has NOT landed.** Measured at the true head:

| | Value |
|---|---|
| `report_only_checks.REGISTRY` size | **73** |
| Arm **E2** failures | **5** — `assertion_label_shape_check`, `entry_point_scope_check`, `parse_zero_third_state_check`, `fact_sheet_regenerates`, `verification_owed_report` |
| Seam watch wired | **no** |
| `doc_checker_coverage` wired | **no** |

Unchanged from yesterday, same five tools. **Left as-is, not reworked around**,
as directed. Two of my own instruments are now unwired for the same single
reason, which is worth stating as a cost rather than a note.

**Rows 82 / 845** — hank has not delivered the paste-ready text. Untouched.

**Claims re-checked fresh at batch start and again mid-batch**, per the
instruction: cody held `schema_provisioning_check` then `scpgate`
(`api/sd-data.js`), hank held `citation_line_drift_check` / `push_retry`. None of
my files overlapped; `api/sd-data.js` was mutated only inside restored ablations
and is byte-identical.

**BLIND SPOTS: 1.** The claim record is only as fresh as the last push to it.

---

## 8. One more reading error of mine, same family

After `7c89e0a7` pushed successfully, a **subsequent no-op push** printed
*"Blocked: this gate could not tell what is being pushed — no ref lines on
stdin"*, and I read it as a refusal **of my push**. It was the hook being invoked
with nothing to send: `git rev-list --left-right --count origin/main...HEAD`
answered `0 0` and the commit was already on `origin`.

**Same family as the exit-2 lesson**: a status read off the wrong subject. Twice
in two days, and both times the fix was to measure the specific thing rather than
read the nearest output.

---

## 9. What this batch did NOT do

* **No wiring** of the seam watch or `doc_checker_coverage` — blocked on hank's
  file.
* **No `--at <sha>`** for the coverage tool, so historical proofs stay manual.
* **No drive** of the other two move-proofed files against a planted refactor.
* **No SAIRNbiz click-through**; finding 13 still open and unfixed.
* **No fix** to `git log -S` reachability for `51548ec9` — only `--grep` connects.

**BLIND SPOTS: 1.** This is what I know I did not do; it cannot cover what I did
not think to check.

---

## 10. The new check's FIRST RUN found something, and I took its advice rather than ignoring it

`doc_checker_coverage.py` reported, on the very change that added it:

```
2 markdown file(s) in this change are read by NO declared checker:
  UNCOVERED  SAIRN-ACTIVE-WORK-cc.md
  UNCOVERED  docs/2026-10-05-cc-batch-5-inventory.md
```

The dated inventory is a one-off and covering each by name is unsustainable.
**`SAIRN-ACTIVE-WORK-cc.md` is different** — it is a standing file, it carries
tables, and I append to it every session. By the tool's own question it belongs
in `DEFAULT_FILES`.

### AND IT IS NOT ADDED, because measuring it first found an off-by-one

```
SAIRN-ACTIVE-WORK-cc.md: OK  (111/110 rows checked)
```

**0 malformed, 0 orphans — and `checked` (111) exceeds `looks-like-a-row`
(110).** The probe's arm for an added file asserts `checked == looks`, so adding
it would fail that arm.

**Cause, pinpointed rather than guessed — line 2008 is `| | |`.** It consists
only of pipes and spaces, so `SEPARATOR` matches it: `coverage()` counts it as a
checked body row while the `looks` tally excludes it as a separator. One
ambiguous empty row, double-counted.

**It is benign and the direction is still worth naming:** `checked > looks` means
the pair *over-states* coverage, which is the mildly unsafe direction for a
denominator, by one, on an empty row.

**I DID NOT RELAX THE ARM TO ADMIT THE FILE.** Loosening an assertion so a file
can join the covered set is the "make it green" failure in its purest form —
the same move as deleting a table to clear the gate this tool deliberately is
not. So: the file stays uncovered, the finding is recorded with its line number,
and the next session can decide whether `coverage()` should treat an all-pipes
row as a row or as a separator. **That is a decision about `md_table_check`'s own
accounting, not a thing to settle as a rider on an unrelated batch.**

**BLIND SPOTS: 2.** (1) I checked ONE file for this off-by-one — the three other
standing files in `DEFAULT_FILES` were not re-examined for an all-pipes row, so
whether the same double-count is already inflating their reported coverage is
unmeasured. (2) "Benign" is my judgement from 0 malformed and 0 orphans; I did
not construct a case where an all-pipes row hides a real defect.
