# Coverage ledger — what is EXHAUSTED at this depth, and what that does not mean

**fourth (Ted), 2026-10-07.** Two sweeps are recorded here as **exhausted at
the depth they operate at**. That phrase is doing work: it means every item in
a re-derived population was measured by a named command at a named commit, and
it means nothing at all about the depths those commands do not reach. The
limits are stated in each row rather than left for a reader to discover.

---

## 1. GAP-DOCUMENT VERIFICATION — 36 of 36, EXHAUSTED at the arithmetic depth

| | |
|---|---|
| **population** | **36** documents, re-enumerated at HEAD. The dispatch premise said *"5 of 35"*; that was the batch-9 figure, batch 10 checked all 35 at headline level, and the population re-enumerates to **36** |
| **command** | `python <scratchpad>/gapverify2.py $(cat gapdocs.txt)` |
| **commit** | `762b084b` |
| **date** | 2026-10-06 |
| **exit** | **`PROGRAM_EXIT=0`**, read from the program's own invocation |
| **runs** | **three** against that SHA. The first returned the same file-citation and count-claim totals as the last; only the citation column moved, because the two states added between runs move citations |
| **result** | documents NAMED 36 / READ 36 / ABSENT 0 · file citations 321, 4 missing · count claims 47 hold, 17 broke, 173 could-not-check, 4 ambiguous · line citations 6 hold, 5 broke, 21 could-not-check, 1 ambiguous, **15 misattributed by the tool** |

### What EXHAUSTED means here, and what it does not

**Exhausted:** every checkable **count claim** and **line citation** in all 36
documents has been re-derived against the file the document itself names.

**NOT exhausted, and these are not caveats, they are the larger part:**

* **No verdict in any of the 36 documents has been re-derived.** This pass
  checks arithmetic, never argument. A document whose every figure holds can
  still reach a wrong conclusion.
* **173 count claims and 21 line citations name no file at all** and are
  unreachable by any version of this tool. That is roughly **60% of the count
  claims in the corpus** and it is a ceiling, not a tuning problem.
* **The 17 broken count claims are measured, not triaged.** `applicant`
  46 → 0 in `stonedesk.html` and `public catalog` 17 → 0 in `sairnsenior.html`
  are capabilities going the *wrong* way and are the two to read first.
* **The tool cannot see a correction written as strikethrough.** Three
  already-corrected SAIRNdental figures were reported stale by an earlier pass
  for exactly this reason.
* **15 of the 21 citations the tool first called broken were ITS OWN wrong
  denominator** — roofing `rf_*` judged against `sairndental.html` and dental
  `dnt_*`/`cdt_*` against `sairnroofing.html`, in one document covering three
  verticals. That became convention **17**. A future reader should assume the
  same class exists in whatever the tool cannot attribute.

---

## 2. SPAN SWEEP — 34 of 34, EXHAUSTED at the does-it-parse depth

| | |
|---|---|
| **population** | **34** span-taking sites, re-derived. The dispatch premise said *"14 remaining of 38"*; **143** sites match a function-start locator, **110** take no span at all, 143 − 110 = 33, plus one `FIXED_WINDOW` site = **34**. The 38 was an earlier raw candidate count including sites later shown not to take a span. There is no "14 remaining" |
| **command** | `node <scratchpad>/spanparse.js` |
| **commit** | `762b084b` |
| **date** | 2026-10-06 |
| **exit** | **`PROGRAM_EXIT=0`** |
| **judge** | **V8.** Each span is written to a temp file and fed to `node --check`. A span that does not parse as a function expression is not a function body, whatever any brace counter says |
| **result** | `SITES: 34   WALKER SPANS THAT PARSE: 34   SITE SPANS THAT PARSE: 31   COULD NOT EVALUATE: 0` |

### The three real findings

| site | app / source |
|---|---|
| `tests/sairnbiz_vendor_ytd_derivation.js:268` | `sairnbiz.html`, `function rVends()`, bound `marker0` on `$('vntbody').innerHTML=html;` |
| `api/sd-data-leg-session-gate.test.js:211` | `sairnlegacy.html`, `function sdnData(...)`, bound `marker` on `return fetch(DATA_API` |
| `api/_lib/stonedesk-remnant-publishing.test.js:201` | `stonedesk.html`, `window.pcToggleRemnant=async function`, bound `func` on `function pcRenderRequests` |

All 34 **walker** spans (`tests/lib/fn_span.js`) parse, so the shared helper is
clean and the three defects are in what those three suites take for themselves.

### What EXHAUSTED means here, and what it does not

**Exhausted:** every site in the re-derived population has been measured by a
real JavaScript parser, in both the walker and the site-span direction.

**NOT exhausted:**

* **"Parses as a function" is not "is the RIGHT function."** A span can parse
  cleanly and still start or end in the wrong place. Nothing here checks that
  the span is the body the suite intended.
* **The three defects are NOT repointed.** A repoint needs a **planted control
  per site** proving the new span is the right one — per-site work, and the
  next step.
* **The 110 "take no span" sites were classified, not verified.** They were
  excluded by a scanner, and a site wrongly excluded is invisible to this
  measurement entirely.
* **One SHA, one machine.** Measured at `762b084b` only, and a span bound to a
  marker string in a 2MB app file is exactly the kind of thing that moves.

---

## 3. WHY A COVERAGE LEDGER AT ALL, and the figure that is NOT in it

A sweep reported as "36 of 36" or "34 of 34" reads as *done*. Both are, at one
depth, and neither is at the depth a reader cares about: whether the gap
documents are **right**, and whether the spans are **correct**. Writing the
depth beside the ratio is the only thing that keeps the ratio honest, and it is
item **3** of the cross-domain disciplines — publish the denominator and what it
is a denominator *of*.

**The figure deliberately absent from this ledger:** any statement that the
suite as a whole is green or that the tree is clean. The last whole-tree run,
`PROGRAM_EXIT=1` at `762b084b`, reported 83 failing files — and two probes in
it gave **opposite verdicts** depending only on whether they ran in the live
clone or in a linked worktree. Until `tools/run_all_tests.py` carries cody's
isolation fix, **no whole-tree or `--pinned` figure belongs in a coverage
ledger**, which is why neither is here and why every suite this batch was run
individually.

---

## 4. THE SHA EXTRACTOR — the old sweep was wrong in BOTH directions, not just one

**Corrected 2026-10-07.** The dispatch premise was that my 8-hex sweeps
**over-report ABSENT**. They did. They also **under-reported ORPHANED**, which
is the half nobody had noticed and the half that matters.

| | old extractor | fixed extractor |
|---|---|---|
| pattern | `\b[0-9a-f]{8}\b` — exactly 8, counted as a sha | hex RUN, length 8–40 measured against the whole run, with four rejection rules |
| distinct tokens | 87 | **111** |
| ON-REF | 66 | **73** |
| **ORPHANED** | 6 | **17** |
| ABSENT | 15 | 21 |
| rejected as not-a-sha | 0 | **10**, by reason |

**Why ABSENT rose rather than fell, and it is not a regression.** Ten
false positives were rejected — but the old `{8}` pattern also *missed* every
12- and 40-character form, so the fixed run sees many more real shas in all
three states. Netted out: **10 non-shas removed from ABSENT, and 11 genuine
orphans found that the old pattern was structurally blind to.** The old sweep
was not merely noisy; it was quiet about the state that needs action.

**The ten rejected, by reason, printed by the tool itself:**

    all digits -- a number, not a hex id   8   000000000000 1234567890123 40318627
                                               4111111111111111 50000000000001 55889165
    date shape YYYYMMDD                    2   20260318 20260825

**The rules, each with its own selftest arm:** minimum length 8; all-digit
strings rejected; `YYYYMMDD` date shapes rejected by name even though rule 2
subsumes them, so the arm can say *why*; full 8-4-4-4-12 UUIDs masked out of the
text **before** matching, so a scratchpad session id contributes nothing rather
than contributing its first block; and length measured against the whole hex
**run**, because `\b` does not separate `4111111111111111`.

**12 selftest arms: 8 false-positive shapes, 4 paired positives, 1 anti-vacuity
arm.** The paired positives (an 8-char prefix, a 40-char sha, a 12-char prefix,
an uppercase prefix) exist because *reject everything* is the easy wrong fix
here, and the anti-vacuity arm proves a **bare** 8-char hex token is still kept
— so the UUID arms are not passing because the length rule rejected them.

**Three identical runs:** `PROGRAM_EXIT=0` each, and all three outputs
**byte-identical**. First run clean.

**WHAT IT STILL CANNOT DO, stated rather than discovered later.** It cannot tell
an 8-char mixed-hex token that is *not* a sha — an md5 prefix, a colour code
without `#` — from one that is. Two such tokens remain in the ABSENT column:
`4975e2e9` and `c430231c`, which are **scratchpad session UUIDs quoted as bare
8-char tokens** in the batch-12 caveat paragraph that named them as false
positives. The UUID mask catches them in a path; it cannot catch them in prose.
**The report naming three states is the fix, not a cleverer regex.**

**Where the durable version belongs:** this is my scratchpad sweep, which is the
tool that produced the wrong figures and therefore the tool the dispatch asked
me to fix. The platform's durable sha reader is `tools/doc_sha_reseat.py`, which
is **cc's**, so the rules above are routed rather than copied in.

---

## 5. THE 83 — a CENSUS, and it is 31 of 83

**Measured 2026-10-07 at `a7b6b58c`.** The 83 is re-extracted from the pinned
run log itself rather than quoted — `^  FAIL\s+(?:py|node)\s+(\S+)` over
`pinned2_stdout.txt` returns **83 rows**, which is the number that log's own
summary line states.

**A row counts as individually verified when its register `environment` stamp
carries a real SHA** — meaning somebody ran it alone and recorded which commit.
That is a stricter test than "I ran it": it requires the commit to be written
down.

| | |
|---|---|
| the 83, re-extracted | **83** |
| register rows with a SHA-stamped individual run | **32** |
| **of those, inside the 83** | **31** |
| still unverified of the 83 | **52** |

### The one verified row that is NOT in the 83, and it confirms a diagnosis

`tests/push_gate/check9_probe.py` is SHA-stamped and individually run — and it
is **not** one of the 83. The pinned run reported it **SKIPPED**, not FAIL. That
is exactly consistent with this batch's diagnosis of it: check 9 declines to
judge a docs-only outgoing range, so it emits nothing. **The row is red when
driven directly and skipped in a suite run**, which is the environment
dependence the stamp exists to record.

### What 31 of 83 does NOT mean

* **It is not 31 confirmed failures.** Of the 31, **four exit 2** — a
  could-not-run, not a failure — and **one now exits 0**
  (`run_primitive_obsession_probe`, fixed under convention 18 and RECOVERED).
* **The 52 are not presumed red.** They are *unmeasured individually*. The
  pinned run is not a census for the reason this platform already recorded: two
  probes in that very run gave opposite verdicts depending only on whether they
  ran in the clone or in a linked worktree.
* **Eight of the 31 carried no `exit_code` field until this batch**, only an
  environment stamp. Backfilled from the runs recorded in their own `why`
  text — which is why the field exists rather than being inferable from prose.

---

## 10. CONVENTION 18 — 2 of 8 fixed, and the second fix corrected my own diagnosis

**`tests/run_write_path_scan_probe.py` fixed 2026-10-07, verified alone,
ablated.** That makes **2 of the 8** suites in the convention-18 family fixed —
`run_primitive_obsession_probe` in batch 12 and this one — with **6 open and
carrying artifacts**.

### The violation, and why it was not visible before

    _loosened = dict(_shipped['counts'])
    _loosened[_worst] += 5          # ONLY the worst app

That arm's stated subject is *"a count that FELL is not a regression"* — a
property of the **ratchet**. Loosening one app silently made its outcome depend
on **every other app matching its baseline** — a property of the
**repository**. Two assertions, one arm, and it was failing for the second one.

Every app is loosened now, so the arm asserts only its own subject.

### And it corrected a diagnosis I wrote in batch 12

I had recorded *"a baselined count FELL"*. **Measured at `a7b6b58c`: the shipped
baseline records 25 sites and the tree measures 25 — the TOTAL AGREES — and the
shipped-baseline arm fails anyway.** One app **rose** while another **fell**.

A fall alone could not fail a ratchet that tolerates falls, which is the half I
had backwards. **The redistribution is invisible to a total**, and catching it
is the whole reason the ratchet is per-app — so this row is evidence *for* the
tool's design rather than against it.

### Verification

| | |
|---|---|
| failing arms | **2 → 1** |
| runs | **two**, both `PROGRAM_EXIT=1`, both naming the same single arm |
| ablation | the ratchet made intolerant of a fall → **the fixed arm FAILS**; subject restored **byte-identical** |

**The one remaining failure is the genuine live-tree arm** (*"the shipped
baseline PASSES today"*), which is correct behaviour and stays.

**STILL NOT CLEARED:** which app rose and which fell is not named.
`tools/write_path_fault_scan.py` exposes `apps(argv)` and `scan(path)` rather
than a per-app counter, so the comparison needs the ratchet's own code path — and
re-implementing it is how a wrong denominator gets built.

---

## 6. THE FULL SHA SWEEP — and the width was already fixed; the CORPUS was not

**Run at HEAD `94bad71e`, 2026-10-07. `PROGRAM_EXIT=0`, three runs, all three
outputs byte-identical, `git status` unchanged before and after.**

### The dispatch premise is one batch stale, and that is the first finding

It says the matcher *"used a width of 8, which never matches a 12- or
40-character sha"*. **True of the first version only.** Batch 13 item 4 already
replaced it with a hex **run** (`[0-9a-fA-F]+`), length measured against the
whole run, `MIN_LEN 8` / `MAX_LEN 40`. Three arms now prove the width case
directly — a 40-char sha, a 12-char prefix, a 16-char prefix — each paired with
an **anti-vacuity arm proving the ORIGINAL `\b[0-9a-f]{8}\b` could not have
matched it.** Without those three, the width arms would pass whether or not the
fix was present, which is convention 20.

**What was still narrow was the corpus** — ten of my own documents. That is a
convenience sample, which is convention 21 applied to documents instead of
bytes. It is now **every tracked `*.md` and `*.json`** via `git ls-files`.

### Corrected counts, and they move in opposite directions

| | my 10 documents (batch 13) | the full corpus (now) |
|---|---|---|
| documents | 10 | **1,101** |
| distinct sha-shaped tokens | 115 | **16,319** |
| ON-REF | 82 | **2,433** |
| **ORPHANED** | 12 | **79** |
| ABSENT | 21 | **13,807** |
| rejected as not-a-sha | 10 | **1,624** (1,480 all-digit, 54 date-shape, 90 over-40) |

### AND THE WIDENING MADE ONE COLUMN USELESS, WHICH IS WORTH MORE THAN THE NUMBER

**13,807 ABSENT is not a finding list. It is noise.** At repo scale the column
is dominated by non-sha hex inside the JSON registers — content hashes, opaque
ids, base64-ish fragments — and **ABSENT is the state that attracts every false
positive**, because anything that is not a commit is trivially not in this
clone. The rejection rules removed 1,624 of them and cannot remove the rest: an
8-char mixed-hex token that is not a sha is indistinguishable from one that is.

**So the sweep's useful output is the ORPHANED column**, which is the state that
needs action, and **ABSENT only means something on a hand-picked corpus of prose
that cites commits.** Quote the 79; do not quote the 13,807.

### Where the 79 orphans live, and most of them are by design

    35  docs/2026-09-29-stale-branch-tips.md     <- a document ABOUT stale tips
    15  the purge-evidence documents
     7  docs/register-sha-pinning-proposal.md
     7  docs/2026-10-07-fourth-routed.md         <- the Tier A ledger SHAs, owed back
     7  docs/defect-density-register.json
     6  docs/tier-a-reviews.json
     5  docs/SAIRN-PLATFORM-2026-10-06-fourth-batch10-handoff.md
     3  docs/2026-10-06-fourth-andon-log.md
     3  .claude/claims/fourth.json

**A CORRECTION TO MY OWN BATCH-12 FIGURE.** I swept
`docs/defect-density-register.json` in batch 12 and reported **0 ORPHANED / 16
ABSENT**. It has **7 orphans**. That sweep used `[0-9a-f]{12,40}` and therefore
**could not see an 8-character prefix** — the mirror of the defect the dispatch
named, in a sweep I had already called clean. `docs/tier-a-reviews.json` reads 6
rather than the 7 I reported, consistent with one having been discharged or
re-seated since.

### My own five batch-12 commits, by name

    850a4849   ON-REF   docs/handoff-fourth-2026-10-07.md
    905b1736   ON-REF   docs/handoff-fourth-2026-10-07.md
    c74f5e6f   ON-REF   docs/handoff-fourth-2026-10-07.md
    f2ee7be0   ON-REF   docs/2026-10-07-fourth-routed.md + 1
    9e380383   ON-REF   4 documents

**All five are ON-REF**, which is the batch-13 re-seat holding at this HEAD. It
is the first batch in three in which none of my own cited commits is orphaned.

### Why it is indexed, and why the index is cross-checked

The naive form ran two git subprocesses per token and **did not finish in ten
minutes** on 1,101 documents. Two batched calls replace it: one
`git rev-list origin/main` (8,132 commits) for reachability, one
`git cat-file --batch-check` for everything else.

**An index is a shortcut, so it is checked against the real tests.** 29 tokens
spanning all three states were re-tested with `merge-base --is-ancestor` and
`cat-file -e`: **AGREES**, and the run refuses outright on any disagreement. A
faster answer that is not the same answer is worse than a slow one — and the
`--batch-check` path also refuses if it gets a different number of answers than
questions, because answers that cannot be paired with their questions are not
answers.

**Read-only by construction:** every git call is `rev-list`, `ls-files`,
`cat-file`, `merge-base` or `rev-parse`. `git status` was captured before and
after and is unchanged.

---

## 7. CONVENTION 18 — 4 of 8 fixed, and the two new ones are small arms with large reporting

**`tests/run_removal_path_probe.py` and
`tests/push_gate/preauth_exemption_anchor_probe.py`, 2026-10-07.** With
`run_primitive_obsession_probe` (batch 12) and `run_write_path_scan_probe`
(batch 13) that is **4 of 8**; **4 remain open with artifacts.**

### `run_removal_path_probe.py` — one arm, two counts

    check('and the counts are reported', 'A=1' in out and 'C=1' in out, True)

A tool that reported `A=1` and dropped `C=1` failed an arm whose name says only
*"the counts are reported"*, so **the output could not say which count went
missing** — and the Tier A count and the Tier C count are not interchangeable:
one of them is the number a reader acts on. Split in two, each carrying its own
name.

| | |
|---|---|
| failing arms | 1 → 1 (the live-tree baseline arm, unchanged) + the Tier A arm now **passing by name** |
| runs | **two**, both `PROGRAM_EXIT=1`, same single arm |
| **ablation** | C condition made unsatisfiable **in place** → **A arm `ok`, C arm `FAIL`, only the C arm failed**; file restored **byte-identical**; restored probe back to exit 1 |

### `preauth_exemption_anchor_probe.py` — a live-tree arm that did not say what it found

    check('...and zero oracles', 'PREAUTH_ORACLES:0' in out)

**No detail argument** — unlike its sibling two lines above, which carries
`re.sub(r'\s+', ' ', out)[-300:]`. So on the one tree state that matters the
failure printed *"...and zero oracles"* and **not the count it saw**. A
live-tree arm reported without its finding is a tripwire that tells you it fired
and not what tripped it.

**The fix produced the fact immediately, and it clears a NOT CLEARED from batch
12:**

    FAIL ...and zero oracles  PREAUTH_ORACLES:11 -- the tree carries 11 oracle(s)
      ... STALE_EXEMPTIONS:0 STALE_DECLARATIONS:0 HANDLERS_SCANNED:70
          PREAUTH_DISCLOSURES:0 PREAUTH_ORACLES:11
          HANDLERS_WITH_NO_AUTH_BOUNDARY:27 ...

**Eleven oracles, and 27 handlers with no auth boundary**, neither of which the
arm had ever printed. Two runs, both `PROGRAM_EXIT=1`. The ablation here is the
observed behaviour change itself: the arm fired before and after, and only after
does it name its subject.

### TWO ABLATION ATTEMPTS THAT COULD NOT RUN, AND WHY THAT MATTERS

**I tried to ablate the removal-path split twice before the method that worked,
and both attempts are recorded rather than dropped.**

1. **Removing the `C=` emission from the subject tool** — `COULD NOT RUN`: there
   is no `C=` string in `tools/removal_path_check.py`, so the count is composed
   somewhere the ablation could not reach.
2. **Running a modified COPY of the probe from `%TEMP%`** — ran, and printed
   **neither arm**. The probe resolves its own paths from `__file__`, so a copy
   outside the repo does not reach the fixture at all. **That is the
   home-repository path class again**, in an ablation harness rather than in a
   probe.

**In-place-modify-then-restore is the method that works here**, and it is the
one every ablation in batches 12–14 has used. A copy is not an isolation
technique for a tool that locates itself.

**Under convention 20, an attempt that could not run is not an ablation**, and
reporting those two as if the third had been the only attempt would have been
the easy version of this entry.

---

## 8. ITEM 3 — ABLATION 7 of 8, AND MY PREDICATE WAS THE DEFECT TWICE

**`7 of 8`.** Ablated in earlier batches: `run_primitive_obsession_probe`,
`run_write_path_scan_probe`, `run_removal_path_probe`,
`preauth_exemption_anchor_probe`. Ablated this batch:
`run_subprocess_decode_probe`, `run_completeness_probe`,
`run_export_coverage_probe`. **Outstanding: `run_truthy_sum_probe`, and the
reason is specific rather than vague.**

Every ablation modified the SUBJECT **in place** and restored it
byte-identically, with `git status` captured before and after the whole batch
and **unchanged**, and `node --check api/sd-data.js` clean afterwards.

### Attempt 1 — I ablated into an already-red state, and learned nothing

Weakened each subject's detector and asked whether the verdict moved. **1 of 4
moved.** The other three were **already red at baseline**, so an ablation that
leaves them red answers nothing: *an ablation asks "can this arm fail?", and an
arm that is already failing answers that trivially.*

### Attempt 2 — right lever, wrong field read

Forced each subject to exit 0 — which is the condition these arms actually
assert — and judged the result by **the arm's printed text**. Scored **0 of 3**.

**That score was wrong.** `run_completeness_probe` and
`run_export_coverage_probe` both went **probe exit 1 → 0**. A probe that PASSES
does not print a `FAIL` line, so my predicate looked for a line that cannot
exist on success and read the absence as no-response.

### Attempt 3 — judge by the probe's own exit code

    tests/run_completeness_probe.py      probe exit 1 -> 0   ABLATED
    tests/run_export_coverage_probe.py   probe exit 1 -> 0   ABLATED
    tests/run_truthy_sum_probe.py        probe exit 1 -> 1   outstanding

**`run_truthy_sum_probe` is outstanding for a reason worth knowing.** The lever
engaged — the subject's own run exits 0 under the override — and the probe still
exits 1, because **its other 13 arms also drive the same subject** and expect it
to exit 1 or 2 on planted breaks. A blunt exit-0 override breaks them too, so it
cannot isolate the live-tree arm. **The right lever there is to empty the
subject's BASELINE FILE, not to override its exit**, and that is the next step
rather than a fourth attempt — the fix-recheck cap is two rounds and this is
reported instead.

---

## 9. ITEM 4 — THE CENSUS: 40 of 83, unchanged this batch and stated as such

Re-extracted from `pinned2_stdout.txt` and cross-checked against the log's own
summary line, which the script refuses to proceed past on a disagreement:

    re-extracted: 83   log summary line: 83
    X of 83 VERIFIED: 40 of 83
      by exit code: {0: 1, 1: 35, 2: 4}
      STILL UNVERIFIED: 43

**No movement this batch, and that is the honest figure.** The suites run for
items 1 and 3 were either already counted or not members of the 83. The 43
remain **unmeasured individually**, not presumed red.

---

## 10. ITEM 9 — 424 of 1214 SCRIPTS CANNOT RUN FROM A COPY

`git ls-files` over `tests/`, `tools/`, `fmea/` and the `api/*.test.js` set:
**1,214 tracked scripts.**

| | |
|---|---|
| no `__file__` at all | 550 |
| **derives the repo from `__file__` with NO git anchor** | **424** |
| uses `__file__` but not to derive the repo | 186 |
| derives from `__file__` **and** has a git anchor — worth reading | 54 |

**424 of 1214**, split **236 under `tests/`** and **188 under `tools/`**.

**THIS IS NOT 424 DEFECTS, and saying so would be the easy version.** A script
that always runs from the repo is correct and cheap to write that way. What the
number means is narrower and more useful: **424 scripts cannot be ablated,
sandboxed or re-run from a copy**, because a copy in `%TEMP%` reaches no fixture
at all. I hit that twice — once trying to ablate
`run_removal_path_probe` from a copy (it printed neither arm), and once in
`run_copy_exactly_gate_probe`, whose first arm refuses because the gate resolved
the range against its own repo.

**So the platform-wide consequence is a METHOD constraint:
in-place-modify-then-restore is the only ablation technique that works here**,
and any future sandbox runner has to provide the repo rather than a copy of the
script. The 54 that carry both are the ones worth reading — they may already
have the right answer.

---

## 11. THE `__file__` BUCKETS -- THE PREDICATES, WRITTEN DOWN SO THE FIGURE IS CHECKABLE

**Added 2026-10-07 (batch 17), and it exists because §10's `424 of 1214` could be
neither confirmed nor denied.** That section recorded the four BUCKET NAMES and
never the rule that sorted a script into one, so re-deriving it a batch later gave
**974 of 1227** and there was no way to tell a definition difference from drift.
A figure whose predicate is unrecorded is **NOT-REPRODUCIBLE**, which is its own
verdict under convention 23 and is not the same as wrong.

### The population

`git ls-files` over `tests/`, `tools/`, `fmea/` and the `api/*.test.js` set,
keeping only paths ending `.py` or `.js`. **It moves with the repo** -- 1,214 when
§10 was written, 1,227 at `4fa9843a`, **1,232** after this batch's own files
landed -- so the denominator is stamped with a commit every time it is quoted.

### The marker

    .py  ->  the literal string  __file__
    .js  ->  the literal string  __dirname

Chosen per extension rather than searched for both, because `__file__` inside a JS
string is prose about python and `__dirname` in a python file is the same in
reverse.

### The two tests, applied in this order

**DERIVES** -- does the script compute a path from its own location? True when the
source matches any of:

    (dirname|abspath|realpath|resolve|join)\s*\([^)]*__file__
    __file__[^\n]*dirname
    path\.dirname\s*\(\s*__dirname
    __dirname

**ANCHORED** -- does it ask git where the repo is, rather than assuming? True when
the source matches any of:

    rev-parse        --show-toplevel        --git-dir
    --git-common-dir git_common_dir         GIT_DIR

### The four buckets, which are exhaustive and mutually exclusive by construction

| bucket | predicate | at `4fa9843a` | after batch 17 |
|---|---|---|---|
| **none** | the marker does not appear in the source at all | 172 | 172 |
| **derives_no_anchor** | marker present **AND** DERIVES **AND NOT** ANCHORED | **974** | **978** |
| **uses_not_derive** | marker present **AND NOT** DERIVES | 3 | 3 |
| **derives_with_anchor** | marker present **AND** DERIVES **AND** ANCHORED | 78 | 79 |
| | **sum, asserted every run** | **1227** | **1232** |

The sum is asserted rather than assumed: a script that fell into no bucket would be
invisible, which is the shape §10's own missing predicate had.

### What the predicate CANNOT tell, stated rather than discovered later

* It is **lexical, not semantic**. A script that matches ANCHORED inside a comment
  or a string is counted as anchored. That is the same PR 1.2 defect this batch
  routed 47 instances of in SEQ 17-A, and **this predicate has it too** -- named
  here rather than left for somebody else to find.
* **DERIVES is a floor, not an equality.** A script that reaches a fixture by some
  other route is not detected, so `none` over-counts and `derives_no_anchor`
  under-counts.
* **It predicts nothing on its own.** `derives_no_anchor` says *this script
  computes paths from its own location and never asks git* -- it does not say the
  script fails from a copy. That is the empirical half below, and it has already
  produced two counter-examples.

### The empirical half: 30 of 978 driven from a copy, and the claim is 93% right

Each script is copied **alone** into its own scratch directory and run there with
`cwd` set to it. Selection is a deterministic function of the sorted population, so
the exact scripts are reproducible: batch 16 drew 15 positions at **phase 0** of a
15-point even spacing; batch 17 drew 15 more at **phases 0.25, 0.5 and 0.75** of the
same spacing, excluding the first draw, so the two sets interleave instead of
clustering.

| | |
|---|---|
| driven from a copy, batch 16 | **15** -- 13 could not run, **2 could** |
| driven from a copy, batch 17 | **15** -- 15 could not run, 0 could |
| **cumulative** | **30 of 978**, **28 could not run, 2 could** |
| the claim's measured accuracy on this sample | **28/30 = 93%** |

**THE TWO COUNTER-EXAMPLES ARE THE POINT, and they are named:**
`tools/response_shape_check.py` and `tools/write_without_readback_check.py` both
**exit 0** from a scratch directory. So *"424 scripts cannot be ablated, sandboxed
or re-run from a copy"* is a **generalisation with a measured exception rate**, not
a rule, and the platform-wide method constraint that was derived from it inherits
that rate. **948 of the 978 remain empirically unmeasured** -- unmeasured, not
presumed.

**How to re-derive any figure here:** `<scratchpad>/filesweep.py` (batch 16, the
classification plus phase-0 draw) and `<scratchpad>/filesweep2.py` (batch 17,
phases 0.25/0.5/0.75, excluding the first draw). Both print the bucket counts, the
asserted sum, and one exit code per script.

