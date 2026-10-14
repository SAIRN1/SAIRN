# Tier A review — DISCHARGE of cody's queue16 obligation (`dnt_ar`, `dnt_revenue`)

**Obligation:** author `cody`, opened `2026-09-28T03:34:57Z`, resources
`dnt_ar`, `dnt_revenue`, file `tests/reachability/resource_demand_probe.py`.
**Assigned to `fourth` from the moment it was opened; held 397 hours — 16.5
days — at discharge.** Second-oldest obligation on the platform and the oldest
one owned by me after b18's discharge.
**Reviewer:** fourth, 2026-10-14, batch b19.

---

## 0. WHAT I OPENED, AND WHAT I LOOKED FOR

**Stated first and concretely, because the obligation's own instruction is that
a verdict naming neither is not a review.**

| # | what I opened | what I looked for |
|---|---|---|
| 1 | `tests/push_gate/refspec_and_override_probe.py` arm A3, **plus the pre-change blob** `git show bb840eec^:tests/push_gate/refspec_and_override_probe.py` | whether the OLD arm ran backwards, and separately whether it read the working tree where it should have read the commit — **two halves, checked apart**, because if the direction was already right the author inverted a correct arm |
| 2 | `tests/reachability/resource_demand_probe.py` arms 3a, 3b, 3c0, 3c and the two functions they call in `tools/sairn_reachability_check.py` | whether 3c is the logical complement of 3b, and whether the *stated justification* ("3b survives a registry shrunk to two rows and 3c does not") is true — **the reasoning, not just the outcome** |
| 3 | `tests/run_rotation_blast_radius_probe.py` version-parsing arm, and `tools/rotation_blast_radius.py`'s `CRITERIA_VERSION` | the off-by-one in "trailing `.N` implies N−1 transitions", and every degenerate version string that could make the check vacuous |
| 4 | `tools/entry_point_scope_check.py` `FAMILIES` + the divergence criterion, its 21 fixtures, and `tests/run_entry_point_scope_probe.py` | whether the family grouping is too permissive — and I also asked the opposite question, because a criterion can be both |
| 5 | `docs/CRITICALITY-TIERS.md`'s `sf_events` row, and `sairnfreedom.html`'s event/session paths plus `sql/sairnfreedom_data_schema.sql` | whether `sessionId` really is the ONLY link between a hall event and its minted session — **five candidate second paths, each disproved or found** |

**HOW, and this is the part that bounds the verdict:** each of the five was
re-derived from source by a reader that was **not given cody's conclusions**,
then the load-bearing claims were re-checked by hand against the same lines.
Two of the five were additionally driven **in process** — the reachability
functions were evaluated to produce real numbers, and the fixture lock of the
scope checker was run (`--fixtures --quiet`, exit 0, `21/21`). **Nothing was
written to the repo**; `tools/` and `tests/` are not mine.

### What I could NOT read

```
CMD git cat-file -e f88105a88287d89b80d93cf2936066b198b90069   ->  DANGLING
CMD tier_a_review_gate.py --reseat-shas --include-reviewed
    cody 2026-09-28T03:34:57Z  ->  bb840eeccb3c   [FILE-SET SUBSET]  (WEAK basis)
```

**THIS IS A STATE REVIEW, NOT A DIFF REVIEW, AND THE VERDICT SAYS SO.** The
recorded sha does not resolve in this clone even after `git fetch origin`. So I
reviewed the code **as it stands at HEAD**, not the diff as recorded.

**But unlike b18's dangling record, this one has a candidate:** the re-seat tool
offers `bb840eeccb3c` on a **WEAK** basis (file-set subset within a 6h window).
I did not `--write` it — that is a register-wide write on a containment claim,
and the tool splits strong and weak across two flags deliberately. **I did,
however, read `bb840eec` to get arm A3's pre-change text**, and it is the commit
that changed both arm A3 and arm 3c in one edit, which is consistent with the
obligation's own description of the batch. **That makes the weak basis
plausible, and "plausible" is not "recorded" — it stays weak.**

---

## 1. THE VERDICT IN ONE TABLE

| # | cody's claim | verdict |
|---|---|---|
| **1** | arm A3's old subset ran BACKWARDS **and** against the WRONG POPULATION | **BOTH HALVES TRUE. The new arm is correct and not inverted** — and the old arm was weaker than cody realised: it was *implied by its neighbour*. One residual: the fix to half two cannot be demonstrated on a clean tree (**F1**) |
| **2** | 3c is the COMPLEMENT of 3b and survives a shrunk registry where 3b would not | **THE REASONING IS WRONG IN BOTH HALVES. 3c is a strict logical WEAKENING of 3b, not its complement, and BOTH survive the two-row shrink** — measured, not argued (**F2**). Keeping 3c is defensible for a different reason than the one given |
| **3** | the `.N` → N−1 arithmetic is right and a scheme change cannot make it vacuous | **ARITHMETIC RIGHT. THE ANTI-VACUITY CLAIM IS PARTLY WRONG** — the arm has no guard of its own, and one two-character edit defeats it while both arms stay green (**F3**) |
| **4** | the FAMILIES grouping is not too permissive | **IT IS BOTH TOO PERMISSIVE AND TOO STRICT, in different places — and the tool prints a live false positive at HEAD** whose shape no fixture decides (**F4**, **F5**) |
| **5** | `sessionId` is the ONLY link between a hall event and its minted session | **TRUE. Five candidate second paths, all disproved.** The B→A promotion rests on a correct code fact. Two adjacent defects found on the deletion path (**F6**), and the row's own citations have rotted (**F7**) |

**DISCHARGE VERDICT: claims 1 and 5 hold. Claim 3's arithmetic holds and its
safety claim does not. Claims 2 and 4 do not hold as stated — and in both cases
the CODE is defensible while the REASONING for it is false, which is the
distinction this review exists to draw.** Seven findings, all routed; none fixed
here.

**Why that distinction is the point and not pedantry:** a correct arm kept for a
false reason is a correct arm nobody can maintain. The next session reads the
comment, not the measurement — and when the comment says "3b would still pass
and this would not", a future edit that breaks the *real* protection (3a and
3c0) looks safe.

---

## 2. F1 — claim 1 holds, and the old arm was weaker still

**HALF ONE — ran backwards: TRUE.**

| | the assertion |
|---|---|
| OLD, `bb840eec^` blob lines 228-229 | `set(exported) <= set(on_disk)` — *"the export adds nothing beyond the reference set"* |
| NEW, `tests/push_gate/refspec_and_override_probe.py:271-272` | `sorted(set(committed) - set(exported))` must be `[]` — *"the reference set adds nothing beyond the export"* |

**Both carry the same label — "every committed seed json is present in the
export" — and that label is `reference ⊆ exported`. The old code asserted the
opposite containment.** The consequence is load-bearing in exactly the direction
that matters: **if `export_sql_at()` silently dropped a seed, `exported` shrinks
and `exported ⊆ on_disk` becomes *more* true.** The old arm passed on the defect
it was named after. The new `MISSING` arm goes red.

**AND IT WAS WEAKER THAN cody CLAIMED, which is worth recording because it
strengthens the case for the rewrite rather than weakening it.** `note == ''`
(`:276`) is only true when every committed seed name exists on disk — see the
`else: differs.append(... ' (absent from the working tree)')` branch in
`tools/sairn_push_gate_hook.py`. So once the neighbouring arm passed,
`exported ⊆ on_disk` was **automatically** true. The old arm's entire residual
content was `len(exported) > 0`.

**HALF TWO — wrong population: TRUE.**

* OLD: `os.listdir(os.path.join(REPO, 'sql'))` — **the working tree, no
  subprocess at all.**
* NEW `:263`: `subprocess.run(['git', '-C', REPO, 'ls-tree', '--name-only', 'HEAD', 'sql/'], ...)` — **git's tree at the commit.**
* The function under test reads the commit too (`git ls-tree -r --name-only <tip> sql/` in `tools/sairn_push_gate_hook.py`).

So the old denominator was a different population from what the function
produces. **cody's description of their own defect is accurate on both halves,
and the arm was not inverted.**

**THE RESIDUAL — F1, and it is the one thing cody should hear.** The new arm
**cannot demonstrate half two's fix on a clean tree.** The two populations
*coincide* in any clean checkout, so if `export_sql_at()` were changed back to
`os.listdir(repo/sql)`, both `:272` and `:275` stay green. Its sensitivity to
half two is limited to states where the `sql/` **file set** diverges between
HEAD and disk — and `:276` already demands near-cleanliness, leaving only
"untracked extra `sql/*.json`" as a state the new arm catches and the old could
not (the `note` computation iterates only committed names, so it cannot see
untracked extras).

**What actually proves the section header is a DIFFERENT arm** — the one that
varies the commit (`export at an OLDER commit yields that commit's seed set,
not HEAD's`, with its own fixture-validity arm beside it). **And that arm is
skippable: it prints `SKIP ... arm not run` rather than failing.** A
commit-reading claim whose only real proof can decline to run is the gap here.

**Two latent fragilities, both dormant today and both cheap to close:** `:263`
uses `ls-tree` **without `-r`** while the implementation uses `-r` — today
`sql/` is flat so they agree, but one `sql/<subdir>/x.json` makes the `EXTRA`
arm false-alarm on correct code; and both sides `basename`-flatten, so two
same-named jsons in different subdirectories collide silently.

**ROUTED TO cody:** make the older-commit arm non-skippable (or fail when it
skips — a skip is not a pass, which is this platform's own rule); add `-r` to
match the implementation; and decide the basename collision deliberately.

---

## 3. F2 — claim 2's justification is false, and it is MEASURED false

**cody asked for exactly this: *"test that reasoning, it is the whole
justification for keeping both."*** It does not survive.

**THE LOGIC.** With `K = {(sairndental,dnt_ar), (sairndental,dnt_revenue)}`:

* **3b** asserts `unrequested == K` — **two** facts: nothing outside `K` is
  unnamed, **and** both members of `K` are unnamed.
* **3c** asserts `set(unrequested) - K == set()`, i.e. `unrequested ⊆ K` — the
  **first fact alone.**

**So `3b ⟹ 3c` unconditionally. 3c is not the complement of 3b; it is 3b minus a
conjunct.** There is no world where 3c fails and 3b passes. There is a world
where 3b fails and 3c passes — name `dnt_ar` somewhere and `unrequested` becomes
`[dnt_revenue]`: 3b red, 3c green. **As an assertion, 3c adds zero detection
power.**

**THE JUSTIFICATION, MEASURED.** The two functions were evaluated in process at
HEAD:

```
apps 16   total 392
unrequested  [('sairndental','dnt_ar'), ('sairndental','dnt_revenue')]
3b now: True      3c now: True

registry shrunk to those two rows:
SHRUNK unrequested  [('sairndental','dnt_ar'), ('sairndental','dnt_revenue')]
SHRUNK 3b:  True     <- cody says this, and it is right
SHRUNK 3c:  True     <- cody says FALSE; it is TRUE
SHRUNK 3a:  False
SHRUNK 3c0: universe = 2  ->  len(_universe) > 300 is False
```

Both rows are still absent from the corpus after the shrink, so
`unrequested == K`, so 3c computes `K - K == ∅` → **PASS**. **3c survives the
shrink exactly as 3b does.**

**WHAT ACTUALLY DIES ON A TWO-ROW REGISTRY IS 3a AND 3c0** — the two
floor-under-the-denominator arms, both added in the same edit. **cody attributed
3c0's protection to 3c.** That is the whole error, and it is the kind that only
a measurement finds: the arms are adjacent, they were written together, and the
protection is real — it just lives one arm over.

**WHAT cody DID FIX, AND IT IS REAL:** the previous `len(unrequested) < 5` floor
tolerated four unnamed resources under a label saying *"every"*. That is gone.
**One of the two defects named in the edit was genuinely closed; the second was
not, and the comment claims both.**

**ROUTED TO cody — three lines, in order of value:**

1. **Correct the comment**, or strengthen 3c to be a real complement
   (`set(_universe) - set(unrequested) == set(_universe) - K`, or simply assert
   `K ⊆ unrequested` so the pair is `==` split into two directions). **Either is
   fine. Leaving the comment is not** — it is the reason a future edit will
   delete 3a or 3c0 believing 3c covers them.
2. If 3c is kept as-is, **say what it is for in the comment**: it publishes the
   named/total denominator in its label and emits a named-offenders detail on
   failure, which 3b's bare list equality does not. **That is a reporting
   justification and a good one.** It is not the logical one claimed.
3. The **two acknowledged-unreachable dental resources are the Tier A trigger on
   this very obligation** (`dnt_ar`, `dnt_revenue`), named only inside the probe
   that measures their unreachability. **That is fine and I checked it:** the
   probe touches no dental code, exactly as the obligation says.

---

## 4. F3 — the version arithmetic is right; its safety claim is not

**THE ARITHMETIC IS RIGHT.** At `.3` the criteria have occupied three states, so
three states → **two** transitions, and `range(1, 3)` yields exactly
`['.1 -> .2', '.2 -> .3']`. No off-by-one. Both are genuinely explained in
`tools/rotation_blast_radius.py` — the `.1 -> .2` note and the `(.2 -> .3)`
note, each giving the direction the number moved. Live output confirms the
derivation: *"2 transition(s) implied by version 2026-09-15.3"*.

**THE UNSTATED ASSUMPTION:** the counter must be **1-based and
single-component**. Nothing enforces either.

**THE VACUITY TABLE, each row computed against the real parsing code:**

| `CRITERIA_VERSION` | N | transitions demanded | this arm | the neighbouring `int(rev) >= 2` arm | net |
|---|---:|---:|---|---|---|
| `2026-09-15.3` (today) | 3 | 2, both present | pass | pass | **has teeth** |
| no trailing numeric / `.0` / `.1` / `-3` / `.3-beta` | 0 | **0** | **passes vacuously** | fail | suite fails |
| `2026.09.15` | 15 | 14 | fail (12 unexplained) | pass | loud false failure |
| **`2026-10-14.2`** — new date, counter restarted | 2 | 1, already in the file | **pass** | **pass** | **VACUOUS, SILENTLY** |
| **`2026-09-15.4.2`** — three components | 2 | 1, already present | **pass** | **pass** | **VACUOUS, SILENTLY** |

**So the arm has no guard of its own.** Its own check rejects only an
*unparseable* version; it accepts `.0` and `.1`, for which `range(1, N)` is
empty and the unexplained list is trivially `[]`. What saves the suite in those
rows is **a different, pre-existing arm** (`rev.isdigit() and int(rev) >= 2`) —
so the protection cody is claiming for this arm is again one arm over, the same
shape as F2.

**TWO FURTHER OVERSTATEMENTS IN THE SAME CLAIM:**

1. **The explanation check is a substring test over the whole file.** It
   verifies that the literal `'.3 -> .4'` *appears somewhere*, not that a
   direction is given. The source's own promise — *"bumping the version now
   REQUIRES adding the explanation"* — is false; it requires adding **the
   string**.
2. **The denominator is self-declared, not observed.** `CRITERIA_VERSION` is a
   hand-typed literal in the same file the explanations are searched in, and
   this repo has files **born above `.1`** — `tools/rotation_blast_radius.py`
   itself was first committed at `'2026-09-15.2'`, and two other checkers were
   born at `.2` and `.3`. **N has never been an observable count of revisions.**
   There is also no repo-wide validator of the format, and at least one tool
   uses a scheme this regex cannot parse at all.

**THE SINGLE CHEAPEST DEFEATING INPUT, named because cody asked for it:**
`CRITERIA_VERSION = '2026-10-14.2'` — one token, stamping a 4th revision under
a restarted counter. Both arms pass, exactly one transition is demanded, and
`.1 -> .2` already appears in the file, so revisions 3 and 4 need no
explanation. *(Runner-up, equally cheap: bump to `.4` and add the bare comment
`# .3 -> .4`.)*

**ROUTED TO cody:** assert the floor **in this arm** rather than relying on its
neighbour; reject a multi-component trailing counter explicitly; and make the
explanation check require more than the transition string — the cheapest version
is "the transition string appears **on a line that also contains some other
word**", which is weak but is not satisfiable by the bare marker alone.

---

## 5. F4 and F5 — the FAMILIES criterion is both too permissive and too strict

cody asked only whether it is **too permissive**. It is — and it is also still
false-positiving, which is the question that was not asked.

### F4 — too permissive: the criterion compares accessor NAMES and never ARGUMENTS

`FAMILIES` is five hand-written tuples, but membership is tested against a
**module-blind tail name**: an attribute call is flattened to `f.attr`. Two
consequences, both measured:

* **`ast.walk` is read as a file-tree population.** 21 of 336 tools call
  `ast.walk(`, and in four of them (`tools/first_article_check.py`,
  `tools/probe_anchor_freshness.py`, `tools/checker_denominator.py`,
  `tools/assertion_label_shape_check.py`) `os.walk(` does not appear at all —
  **their entire "population" signal is an AST-node iterator.** This includes
  the checker's own self-verdict: run against itself it reports
  `walk` as both doors' population and declares no divergence, **while its real
  enumerator is a `git ls-files tools/*.py` subprocess that is in no family and
  no vocabulary at all.** The spurious `walk` also lifts those tools out of the
  honest "no population" verdict into the stronger-sounding "shared" one.
* **The `file-tree` family is three or four questions, not one.**
  `walk`/`listdir`/`glob`/`iglob` answer *"what is in this directory"*;
  `tracked`/`git_ls_files` answer *"what does git track"*;
  `all_tests`/`test_files`/`suites` answer *"what is the test corpus"*. By the
  file's own definition — *a family is ONE QUESTION with SEVERAL ACCESSORS* —
  that grouping is too permissive, and it is the family the live false positive
  fires on.

**THE GENUINE DIVERGENCE IT MISSES, AND THE MISS IS PINNED AS CORRECT.** A
fixture locks `tracked('*.py')` + `tracked('*.js')` behind one door against
`tracked('*.py')` behind another as **CLEAN** — *"the handlers agree with the
other door"*. **Two doors reading Python files and JavaScript files are declared
to agree.** Real code of exactly that shape exists:
`tools/assertion_label_shape_check.py` calls `tracked(...)` on `tests/*.py`
globs and then on `tests/*.js` globs; `tools/entitlement_freshness_check.py`
calls it on `['api/','tools/','scripts/']` and then on `['sql/']`. **Put either
pair behind two doors — the literal defect shape — and the verdict is CLEAN.**

Two smaller holes in the same vocabulary: **`ls_files` is in `POPULATION_CALLS`
but in no family**, so a door calling it counts as enumerating yet can never
diverge (latent — no caller today); and **two families are 1-tuples**, so the
all-equal test can never be false for them — they are exclusions dressed as
families. Also a plain mislabel: `load_ledger` is defined twice in `tools/`,
reading two different ledgers, so the family name is wrong for one of them.

### F5 — too strict: the tool prints a FALSE POSITIVE at HEAD, and its shape is unfixtured

```
CMD python tools/entry_point_scope_check.py          ->  EXIT 1
FINDINGS (1):
  ! tools/purge_evidence_gate.py  doors (no flag -- the bare run) --audit
    enumerate DIFFERENT populations: file-tree -> ...
```

In process the doors are `{'(no flag)': ['listdir'], '--audit': ['listdir','walk']}`.
Reading the subject: its `audit()` walks source directories for unguarded prune
call sites, while its two `listdir` calls list one pack directory and one
evidence-record directory. **Three different questions, correct code** — and the
file's own exemption rationale applies. Two compounding causes:

1. **A door that cannot exist.** `--record` / `--require-record` are not in the
   tool's real-data flag list, so their branches are not doors and their
   `listdir` reads are attributed to "shared", which manufactures a
   `(no flag -- the bare run)` door. **The subject's argparse puts its three
   flags in a `required=True` mutually exclusive group — a bare run is an
   argparse error.**
2. **Superset is treated as disagreement.** The two sets differ only by
   `{listdir} ⊂ {listdir, walk}`, and the all-equal test calls "reads more"
   "disagrees". **No fixture covers the superset shape — the only live finding
   the tool prints has a shape its 21 fixtures never decided.**

And the finding's own **printed detail is wrong**: it formats a `{door: calls}`
dict where it means the calls, so it prints door names where it promises
accessors. The probe arm that checks the accessors reads the in-process detail,
not the printed line, so the output defect is unpinned.

### Is the grouping itself pinned? No

The only arm over `FAMILIES` is a **sabotage counter** — it empties the map and
checks the total member count drops to zero, which proves `FAMILIES` is
load-bearing and nothing about whether any member is in the right family. **No
fixture and no arm mentions the two singleton families or the orphaned
vocabulary member.** And the split cody paid for is load-bearing: merging the
two singletons back into `register` turns a real tool into a FINDING.

**ROUTED TO cody — three arms, cheapest first:**

1. **One line:** every member of `POPULATION_CALLS` belongs to exactly one
   family, or the orphan is an accessor no divergence can ever use. **That one
   line would have caught `ls_files`.**
2. **One fixture pinning the superset shape** to whichever verdict is intended.
   Today it is a FINDING by accident and it is the tool's only live output.
3. **One fixture pinning the singleton split**, so the day somebody merges the
   families it is the fixture that changes rather than a correct tool going red.

**ROUTED TO cc (owner of `tools/`):** the `ast.walk` tail-name collision, the
missing-flag door that cannot exist, and the printed-detail formatting. **These
are `tools/` edits and not cody's** — the probe arms are cody's, the tool is
cc's, and this review does not merge the two.

---

## 6. F6 and F7 — claim 5 is TRUE, and two things sit beside it

**THE ASSERTION HOLDS. `sessionId`, stored on the event row, is the only
association between an `sf_events` row and the `sf_sessions` row its booking
minted.** All five candidate second paths were checked and none exists:

| candidate | finding |
|---|---|
| (i) reverse pointer on the session row | **does not exist as an identity.** The minted row carries `fromEvent: true` — a boolean naming no event, and a repo-wide grep finds **exactly one hit: that write.** Zero readers. Postgres agrees: both tables are opaque `data jsonb` with no FK and no event column |
| (ii) derived join on date+title / date+kind | **impossible for title** — the session row carries no title and no kind. Date *is* compared, but only inside a refusal check, and that check **explicitly `return`s for the gaming case**, which is exactly the rows in question |
| (iii) index / array position | **no.** Both stores are `push`-appended independently and every lookup is by `id`; the server-wins merge appends in arrival order, so positions are not even stable across a hydrate |
| (iv) shared generated id | **no.** Two separate `Date.now()` calls with different prefixes (`'ss'` / `'ev'`), and **nothing anywhere derives one id from the other** — a grep for prefix-stripping and numeric-suffix comparison finds only the three mint sites |
| (v) name / label convention | **no.** The only *"Bingo session"* string is a rendered literal for sessions with no event, and the `' + bingo session'` suffix is itself derived **from** `e.sessionId`. Neither is stored |

**AND THE HARM THE TIER ARGUMENT ASSERTS IS REAL.** The three-in-seven-days
statutory population is the whole sessions store minus one optional excluded id
— **no `fromEvent` filter, no `recorded` filter, and it never consults
`sf_events` at all.** So a stranded session **would** still be counted toward
the ORC 2915.09(C)(4) limit, and the only datum that could distinguish it lives
on the deleted event row. **The B→A promotion on INTEGRITY rests on a correct
code fact, and the row's named trigger stands.**

### F6 — the deletion path reports success it did not achieve

This is **new**, it is not what the row claims, and it is the finding of claim 5.
`sfDeleteEvent()` removes the linked session **by stored id only**, with no
existence check before the filter and no count comparison after it:

| state | what happens |
|---|---|
| stored id **missing** on a row that should have one | the guard is false, **no session is touched**, and the toast says *"Event removed"*. Silent no-op; the session survives and keeps counting |
| stored id points at a row **that no longer exists** | the filter matches nothing — **and the toast still says *"Event and its bingo session removed"***. **Affirmative false success**, which is worse than a silent no-op |
| stored id points at the **wrong** row | that row is deleted with no verification (`fromEvent` is never consulted) and success is reported |

**And the dangling-pointer state is one click away from the UI**, by a path the
row does not mention: `sfDeleteSession()` removes a session row and **never
clears any event's `sessionId`**, while the Sessions table renders a Remove
button for **every** session, event-minted ones included. After that the event
row still advertises *" + bingo session"*.

**One more exposure on the same id:** the sync pushes only changed-or-new rows
and never deletes a server row, the grant is `select, insert, update` with **no
delete**, and the server-wins merge re-adds any server row absent locally — so
**a deleted session can come back on a later hydrate, into the same store the
statutory count reads.**

**ROUTED TO hank (`sairnfreedom.html`, `api/`):** make the delete verify — count
before and after, and report what actually happened; refuse or warn when
`sfDeleteSession` is called on a row with `fromEvent: true` and a live event
pointing at it. **ROUTED TO cody:** an arm driving the three rows of that table.
**COULD NOT TELL:** whether any existing test pins this path — I did not sweep
the suites for it, and that is a gap in this review, not a clean bill.

### F7 — every line number in the `sf_events` cell has rotted

The cell cites six anchors and **all six are stale at HEAD**: `eventRefusals()`,
`sfSessionRefusals()`, `sfScheduleEvent()`, the delete, the Sessions-panel
decision and the two `alcohol` readers. **Every function named is real and does
what the cell says — only the numbers moved.** That is the eighth cross-domain
convention, and it is the second batch running in which I have found it live in
a document I or a peer wrote. **ROUTED: the register is a shared document; the
cheapest fix is the one already open as cc's `--read-the-line` ask on
`tools/citation_line_drift_check.py`.**

---

## 7. THE DISCHARGE, AND WHAT IT DOES NOT CLAIM

**DISCHARGED** via `tools/tier_a_review_gate.py --discharge cody
2026-09-28T03:34:57Z --body-file <verdict>`, as the **assigned owner**, not with
`--takeover`.

1. **It is not a diff review.** `f88105a88287` does not resolve. A weak re-seat
   candidate exists (`bb840eeccb3c`) and was **read** for arm A3's history but
   **not written** to the register.
2. **No suite was run end to end.** Two things were driven: the reachability
   functions in process (producing the numbers in §3) and the scope checker's
   own fixture lock (`21/21`, exit 0) plus one real run (exit 1, the false
   positive in §5). **No test file was executed as a suite, and no `tools/`,
   `tests/`, `api/` or `sql/` file was modified.**
3. **It fixes nothing.** Seven findings routed: four to cody, three to cc, one
   to hank, one shared-document fix.
4. **Claim 5 was verified by reading, not by driving the app.** I did not open
   SAIRNfreedom and delete an event. The five second-path denials are grep-and-
   read results over `sairnfreedom.html`, `api/` and
   `sql/sairnfreedom_data_schema.sql`; **F6's three rows are read from the code,
   not observed in a browser.**
5. **It does not re-tier anything.** `sf_events` stays A on INTEGRITY, and this
   review agrees with it.

**THE ONE THING WORTH KEEPING:** two of cody's five claims had **correct code
and false reasoning**, and in both cases the real protection lived in a
*neighbouring arm* the author credited to the arm under discussion. **That is
not sloppiness — it is what happens when several arms are written in one edit
and the comment is written last.** The cheap defence is the one cody already
asked for here: make the arm assert its own floor rather than inheriting its
neighbour's.
