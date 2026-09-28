# Entry-point scope divergence — the enumeration, the control, and the two false positives it cost

**2026-09-28 (Cody).** Methodology item: a tool with more than one entry point
over one population can answer two different questions and be individually
correct at every door. The instance cost a real session a real push. This is the
sweep, the mechanism, and the honest denominator.

**Re-run everything here rather than quoting it:**

    python tools/entry_point_scope_check.py
    python tools/entry_point_scope_check.py --all        # every tool considered
    python tests/run_entry_point_scope_probe.py          # 21 arms

---

## 1. The defect, stated once

`tools/tier_a_review_gate.py` had two doors onto one question:

| Door | What it read |
|---|---|
| a bare run (what a human types before pushing) | the **working tree** |
| the push hook | **`merge-base origin/main HEAD..HEAD`** |

A session committed a new Tier A engine, ran the tool to check first, and was
told *"No file in this change names a Tier A resource … Nothing to record"*. The
same tool then **denied the push, naming seven resources.**

**Both answers were true about what they read.** Neither was about the question
asked. Recorded as a rule-1.6 defect — *the copy a human invokes is not the copy
that enforces* — and worse than a wrong answer, because the door a human uses to
check **before** pushing was the one blind to committed-not-pushed work, which is
the only state a pre-push check exists for.

---

## 2. What counts as a second door, and what does not

**`--fixtures` and `--selftest` are NOT doors.** They read no real state — that is
their entire purpose, and it is discipline 5: the deep check runs with its subject
not trusted. Counting them produced **70 candidates of which most are correct by
construction**, and a checker reporting 70 rows where 60 are right is one nobody
runs twice.

The vocabulary is therefore the flags that read **real** state: `--explain`,
`--check`, `--list`, `--report`, `--pre-push`, `--dry-run`, `--fix`, `--propose`,
`--apply`, `--verify`, `--audit`, `--json`, `--planned`, `--all`.

**And the bare run is a door.** It has no flag to key on, which is exactly why the
original defect was invisible to any flag-based search. `--all` prints every tool
considered so the hand-kept vocabulary is auditable rather than an omission
somebody has to notice.

---

## 3. THE CRITERION IS NOT "two doors differ"

That was the first criterion and it reported correct code twice. The two
corrections are what make the tool usable, and both are now fixtures **and** arms:

### 3.1 Shared setup belongs to every door

`tools/probe_selector.py` calls `corpus_probes()` **before** its `--all` branch.
The first version attributed that enumeration to the bare run alone, so two doors
going through the same setup read as two different populations. **A checker that
flags shared setup is a checker whose findings get ignored.**

Calls outside every flag branch are now **shared**, and each door's population is
`shared | its own`. The bare run is exactly `shared`.

### 3.2 Two doors may answer two questions

`tier_a_review_gate --list` reads the review ledger and **no scope accessor at
all**. It is not disagreeing about scope; it is answering a different question,
which a tool is allowed to do. Reporting it would have been reporting the tool
**after** its fix.

So a finding requires **two doors reading different members of one family**:

| Family | Members |
|---|---|
| scope-of-change | `working_diff` `push_range` `default_scope_diff` `outgoing_files` `changed_files` |
| file-tree | `walk` `listdir` `glob` `iglob` `tracked` `git_ls_files` `all_tests` `test_files` `suites` |
| register | `load_register` `load_reviews` `load_identities` `read_register` `promoted` `registered_resources` `_mention_corpus` |

`working_diff()` and `push_range()` are **both** "what changed" — that is what
made their disagreement a contradiction rather than two facts. A door that reads
no member of a family is not disagreeing about that family.

---

## 4. THE FIRST VERSION WAS BLIND TO THE SHAPE IT WAS BUILT FOR

Worth recording on its own, because it is this repo's favourite defect one level
up.

Version 1 read only the calls **lexically inside** a branch. It reported **9
candidate tools and CLEAN for all nine**, every one with the reason *"no
entry-point branch enumerates a population directly"* — because this repo
dispatches:

    if '--check' in argv:
        return cmd_check()          # the enumeration is in here

**A checker that cannot see the shape it exists for reports clean for ever.** It
would have sat in the registry, green, indefinitely.

Calls are now resolved through module-level functions to `RESOLVE_DEPTH` (3).
Depth is bounded rather than full because a cycle would hang and a real call graph
is a different tool — and the depth is a named constant so a reader knows how far
it looked. With resolution the candidate population went **9 → 64**.

---

## 5. CHECKED / UNIVERSE

    read 240 tool(s); 64 have TWO OR MORE real-data entry points
    CHECKED / UNIVERSE: 64 of 240 tools in tools/ (27%)

**The other 176 are not a coverage gap.** They have one door or none, and a single
door cannot disagree with itself — the population is genuinely smaller than the
directory, which is a different statement from "we only looked at 27%".

**Result on 2026-09-28: 0 findings across all 64.** The one known instance was
fixed the day before this tool existed.

---

## 6. WHY A ZERO FROM THIS TOOL IS WORTH ANYTHING

Because it is **ablated, not asserted**. `tests/run_entry_point_scope_probe.py`
(21 arms):

- **B1–B1c** reconstruct the **real pre-fix shape** of `tier_a_review_gate.py` as
  a source string and demand the tool report it, name the family, and name **both
  accessors**. Nothing on disk is mutated, so there is no restore to get wrong.
- **B2** is the silent half: the same tool **after** its fix must not report. A
  checker flagging the fix too would be reporting the shape, not the defect.
- **A2** sabotages the criteria in process — every family collapsed to empty — and
  **asserts the sabotage applied before** asserting anything about behaviour,
  because a patch that silently failed leaves every arm green for ever. A3
  asserts the restore.
- **C1–C3** pin the two false positives above plus the `--fixtures` exclusion.
- **D2** reads the two coverage figures **back** and asserts checked > 0 and
  universe > checked, because "it prints a coverage line" is satisfied by a line
  printing 0 of 0.
- **E1–E4** are anchors: the function names this control calls, the criteria
  version appearing in real output, the `CONTROLLED_BY` declaration, and
  `RESOLVE_DEPTH` being ≥ 2 — that last one exists because version 1 resolved
  nothing.

---

## 7. What this cannot see — stated, not discovered later

1. **A shared accessor that itself branches on the flag.** Both doors reach the
   same function name and this reports CLEAN while the divergence lives one level
   down. Note the awkward corollary: `tier_a_review_gate`'s **fix** is of this
   shape — `default_scope_diff()` reads both ranges deliberately — so a tool doing
   this on purpose and a tool doing it by accident are indistinguishable here.
2. **Dict/table dispatch** rather than an `if` on the flag.
3. **Anything a subprocess does.** A door that shells out is a call this cannot
   follow.
4. **It does not run the tools.** Running both doors of 64 tools and diffing the
   output would be a better check and a much slower one, and several doors
   **write** (`--fix`, `--propose`, `--fix-rollup-list`). A static answer honest
   about being static beats a dynamic one nobody waits for.

**The obvious next step, not taken here:** a dynamic pair-run for the subset whose
doors are all read-only. That is a real improvement and a different tool.

---

## 8. Registration

- `tools/entry_point_scope_check.py` — the checker, criteria `2026-09-28.1`,
  11 fixtures.
- `tests/run_entry_point_scope_probe.py` — the control, 21 arms, `CONTROLS_FOR`
  declared.
- `docs/TOOLING-INVENTORY.md` — entry added and regenerated.
- **NOT in the report-only registry**, and that is blocked rather than skipped:
  `tools/report_only_checks.py` is held under a live `cc` claim. Same blocker as
  `assertion_label_shape_check.py`, and the same consequence —
  `checker_control_check.promoted()` reads that registry and nothing else, so
  until the entry lands **the pair exists and nothing counts it**.

---

## 9. 2026-09-29 — THE SECOND BLIND SPOT, AND IT WAS WRITTEN DOWN IN SECTION 7

Section 7 item 2 said the tool could not see **dict/table dispatch**. That is the
right way to ship a gap and the wrong place to leave it, because a limitation
recorded in a header is not a limitation anybody re-reads. Two real tools sat
behind it, and one of them was being described by this tool in terms that were
simply false:

| tool | shape | version 1 reported | truth |
|---|---|---|---|
| `tools/claim_provenance.py` | `cmds = {'scope': cmd_scope, …}` then `cmds[argv[0]](argv[1:])` | **only one real-data entry point** | it has **four**, and none of them is a flag |
| `tools/checker_denominator.py` | `TOOLS = [{'universe': _apps, …}, …]` then `spec['universe']()` | `--json` enumerates nothing | its doors reach `walk` and `glob` |

`claim_provenance.py` has **no flag anywhere**. A door vocabulary made only of
flags cannot count the doors of a tool that does not use flags, so it reported a
one-door tool — and a single door cannot disagree with itself, which is the
cleanest possible way to be permanently green about something never examined.

### What was added

A **dispatch table** — a dict literal whose string keys map to module-level
functions, at least `HANDLER_TABLE_MIN` (2) of them distinct, counting dicts
inside a list — is now read two ways:

1. **As a door vocabulary.** Each key becomes an entry point, when three things
   hold: something CALLS through the table; the call is not inside an
   `ISOLATED_FUNCTIONS` body; and the key expression mentions a
   `CALLER_KEY_NAMES` name, so the key came from the command line.
2. **As a resolution path.** A region that loads the table's name reaches the
   table's handlers, at the same bounded `RESOLVE_DEPTH` as every other hop.
   Resolution is **anchored on the table's name** rather than applied to every
   table in the module, because over-approximating makes two doors look alike and
   would **mask** a divergence — a worse failure than the one being fixed.

### Two things the first real run paid for, both now fixtures

- **Counting handlers by KEY collapsed the biggest table in the repo.**
  `checker_denominator`'s `TOOLS` is six dicts that each use the key `universe`,
  so a key-keyed threshold saw one handler, fell below the minimum, and did not
  recognise the table at all. Counted by **distinct function** instead.
- **A fixture runner is not a door vocabulary.** `completeness_check.py` calls
  `SHAPES[shape](…)` inside `run_fixtures()`, keyed by a loop variable over the
  fixture list. The looser rule invented `S1`/`S2`/`S3` as three entry points on
  a tool that has one. Both the exclusion **and the false negative it costs** —
  a real subcommand table reached through a helper that takes the key as a
  parameter is missed — are locked as fixtures, so loosening the rule has to
  change one of them.

### A vocabulary correction, made the honest way rather than the convenient one

Making `claim_provenance`'s doors visible exposed that `load_ledger` and
`load_tier_a` were missing from `POPULATION_CALLS`, so all four doors read as
enumerating nothing. Adding them to the existing **`register`** family reported
instantly: `scope` reads the tier doc, `list` reads the provenance ledger, `add`
reads both.

**That finding was wrong, and it was the section-7 item-2 exemption again.** A
family is ONE QUESTION with SEVERAL ACCESSORS — `working_diff` vs `push_range`,
both "what changed" — which is why their disagreement is a contradiction. Two
doors reading two **different registers** are answering two different questions
and are allowed to. Each is now its own family and neither can diverge from the
other.

`CLEAN_SHARED` was reworded in the same pass. It read *"every entry point reaches
the same population call"*, which was never what `classify()` decided and got
further from it with subcommand doors. It now says what it checks: **no two doors
enumerate different members of one population family.**

### Ablated, not asserted

Every real run reads each file **twice** — once with table resolution off — and
prints the delta under `TABLE-DISPATCH RESOLUTION, ABLATED`. That is discipline
12: remove the one named layer on already-clean code and measure what it alone
catches, rather than claiming a diff was worth something.

    TABLE-DISPATCH RESOLUTION, ABLATED (2026-09-29): 2 tool(s) read DIFFERENTLY
      + checker_denominator.py
          doors only this resolution sees: (no flag -- the bare run)
          populations only this resolution reaches: glob walk
          VERDICT MOVED: only one real-data entry point  ->  no two doors ...
      + claim_provenance.py
          doors only this resolution sees: add list scope types (subcommand)
          populations only this resolution reaches: load_ledger load_tier_a
          VERDICT MOVED: only one real-data entry point  ->  no two doors ...

**Do not quote those figures from here — run the tool.** Both verdicts moved off
*"only one real-data entry point"*, which was a false statement about both tools
for as long as version 1 existed.

### Numbers, as of 2026-09-29

- criteria `2026-09-29.1`, **21 fixtures** (was 11)
- control **33 arms** (was 21), including section **F**, where every claim about
  the extension is stated as a before/after against `doors(src, tables=False)`
- multi-door population **74 of 257** tools (was 71 of 257 the same day, 64 of
  240 on 2026-09-28)
- **0 findings.** The same caveat as section 6 applies and applies harder: a zero
  is worth something only because F1/F3 prove the tool fires on these shapes and
  F1b/F3b prove it is the extension doing the catching.

### Still not seen

1. A shared accessor that itself branches on the flag. *(unchanged)*
2. A subcommand table whose dispatch key is named outside `CALLER_KEY_NAMES`, or
   reached through a helper taking the key as a parameter. **A deliberate false
   negative**, locked in both directions.
3. A table built at runtime, by comprehension, or out of `globals()`. Only a dict
   **literal** assigned to a name is read.
4. Anything a subprocess does. *(unchanged)*
5. It still does not run the tools. *(unchanged)*
