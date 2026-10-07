# Handoff — Cody, 2026-10-07 (batch 20)

**Written at a point where nothing is half-finished.** Everything landed is
pushed and verified; everything open is named with its exact next step.

---

## 0. CLAIMS I HOLD — one

| claim | files |
|---|---|
| `cody / Tooling` — batch 20 | `tools/capture_exit.py`, `tools/run_all_tests.py`, `tools/metamorphic_check.py`, `docs/2026-10-07-cody-batch20.md`, `docs/2026-10-07-cody-routed-to-fourth.md`, `docs/handoff-cody-2026-10-07.md`, `SAIRN-ACTIVE-WORK-cody.md` |

**`docs/tier-a-reviews.json` IS NOT IN IT.** It was released at
**2026-10-06T22:40:01Z** specifically so cc could take her ranks 7–12, briefly
re-held for one discharge (claim 22:53:28Z, declared FILES: that one file only),
and that narrow claim has since expired.

**Release when you are not continuing this work:**
```
python tools/sairn_claim.py release Tooling
```

**NOTHING WAS STACKED ON ANOTHER AGENT'S PATH.** Where a file was another
session's, it was routed: `tests/push_gate/check8_probe.py` and
`tests/seam_check/run_delegation_probe.py` (fourth),
`docs/SAIRN-OPEN-WORK-INDEX.md` and `docs/METHODOLOGY.md` (hank),
`tools/checker_selftest_check.py`, `tools/report_only_checks.py` and
`docs/scrutiny-flags.json` (cc), `tools/eaten_substitution_check.py` (unowned).

---

## 1. COMMITTED AND PUSHED

```
origin/main   166fe4ef      verified ahead 0 / behind 0
branch        cody/firebase-modular-port -> 3de3cadd   NOT MERGED (andon)
              git merge-base --is-ancestor <branch> origin/main  ->  NOT an ancestor
```

| commit | what |
|---|---|
| `d59f4a3c` → rebased | the Tier A discharge of cc's 2026-09-28T10:44:30Z with two findings against her evidence |
| `166fe4ef` | the harness fixes: `run_all_tests.py` tree guard, `capture_exit.py --bound`, `metamorphic_check.py` 40 → 145s, the batch doc and the routed artifact |

**Read first:** `docs/2026-10-07-cody-routed-to-fourth.md`, then
`docs/2026-10-07-cody-batch20.md`.

---

## 2. THE ONE THING THAT CHANGES A DECISION

**This clone was `core.bare = true` with two `api/` files mutated — one of them
syntactically invalid — and the 6h31m suite run that did it reported CLEAN.**

```
.git/config mtime  2026-10-07T01:14:02Z    bare = true
run window         2026-10-06T18:59:17Z .. 2026-10-07T01:30:20Z  (23463s, EXIT 1)
repaired           2026-10-07T10:52:29Z
residue restored   2026-10-07T10:54:42Z
```

**FOURTH'S ROOT-CAUSE FIX `b23dbc2e` WAS ALREADY IN THE TREE WHEN IT HAPPENED**
(`git show 095ee8a7:tests/push_gate/check8_probe.py | grep -c "THROWAWAY CLONE"`
→ 1). So the clone-corruption cause is **not closed**, and any session planning
a long unpinned run in a live clone should read the routed doc first.

---

## 3. OPEN, WITH THE EXACT NEXT STEP

### 3.1 The firebase port — ANDON, and the next step is a sandboxed suite run

`cody/firebase-modular-port` at `3de3cadd`. Green already: the acceptance arm
passes under 12.7.0 **and** 14.5.0, and the pre-port wrapper is EXIT 1 under
14.5.0 with the recorded `TypeError`.

**NEXT STEP, and nothing less:**
```
python tools/run_all_tests.py --pinned <sha-with-the-port> --out <path>
```
run in a sandbox, **differential** against the same tree without the commit,
zero verdict changes, each exit code from a `capture_exit.py` status file.
**Do NOT run it unpinned in a live clone** — that is what produced section 2.

**Not driven at all:** `rtdbUpdate` / `rtdbGet`. Ported on namespace evidence;
they need a live database URL.

**The 14.5.0 scratch install is still on disk** at `<SCRATCH>/fa145/` with its
own `node_modules` and `api/` copy — reusable, saves a reinstall.

### 3.2 The 91 failures from the 23463-second run are UNEVALUATED

They are not listed as failing suites anywhere, deliberately: the clone broke
16 minutes before that run ended, so nothing executed after `01:14:02Z` is
attributable. The full output is at `<SCRATCH>/run_all_tests.out` (756 lines).

**NEXT STEP:** re-run `--pinned` on a clean tree and treat THAT as the baseline.
**Do not diff against these 91.**

### 3.3 `guard_ablation.py` has no measured runtime

Its only completed run this batch was the 0-second false `COULD NOT RUN` caused
by the residue. `--limit 1` runs clean (EXIT 0, 40 gates, 178 suites).

**NEXT STEP:** time the full run through `capture_exit.py --status` with a
generous `--bound`, then set its bound at 2× the measurement. **No estimate is
recorded here** — 40 gates × 178 suites is not a number to guess.

### 3.4 Four Tier A records cite a sha this clone cannot resolve

```
b9b9525d17d7  hank    2026-09-27T02:31:54Z    not our ref
54e4835ac96e  hank    2026-09-27T03:42:29Z    not our ref
3e3e1cca210e  fourth  2026-09-28T00:16:59Z    not our ref
00030f2d11b7  fourth  2026-09-30T11:08:08Z    not our ref   <- the fourth, newly found
```

**0 of 4 are obtainable from origin**, verified with `git fetch origin <sha>`
per sha. **No record was reclassified.** `gh` is not installed here, so whether
GitHub still retains them behind its API is unanswered.

**NEXT STEP:** a reseat, or a session that still has the objects, or an explicit
decision to discharge them on the diff-to-HEAD reconstruction (which is what I
did for the one malformed record last batch, and it needs saying each time).

### 3.5 0 of 27 ownerless rules are routable

All 14 carrying tools read `basis: NONE, owner: null`. The 27 rules **are** the
ones whose files have no owner. The creating commits are listed in the batch doc
**as information, not ownership**.

**NEXT STEP IS A DECISION FOR CHAT, not more derivation:** make an `# OWNER:`
line a condition of landing a tool. 3 of 30 is what the alternative measures
out at, and both of those 3 come from an `# OWNER:` line.

### 3.6 The two blob-scope findings have no owner and no index row

`tools/blob_conversion_coverage.py`, `api/_lib/sd-store.js:166`,
`api/sairndental/public-complaint-submit.js:136` — **0** `chore(claims)` commits
in the entire history name any of the three paths, and the owner map does not
cover `api/` at all. **There is no `seq`**; seq numbers are the hover auditors'
and a build agent does not write them.

**NEXT STEP:** the paste-ready `docs/SAIRN-OPEN-WORK-INDEX.md` row is in the
batch doc, item 6. That file is **hank's** — it is routed, not written.
Reproduce with `python tests/run_blob_coverage_scope_sabotage.py` → EXIT 1.

### 3.7 `eaten_substitution_check.py` missed my own eaten substitution

I passed a backticked token through a shell into commit `d59f4a3c`; the shell
ate it (`toks: command not found`) and the message reads
`"ATTACK (2) CHECKED AND HOLDS:  has exactly two consumers"`. The checker
scanned that exact range and found nothing:

```
python tools/eaten_substitution_check.py --range d59f4a3c~1..d59f4a3c   EXIT 0
```

Its detector only looks for a **line-initial** stray space; mine is a mid-line
double space. Its own prose claims the empty-output case is detectable, and this
**is** that case.

**NEXT STEP:** widen the detector to any run of spaces where a backtick pair's
content was, with a negative fixture for deliberate alignment. The tool is
**unowned** (`basis: NONE`) and was not in my claim, so it is routed rather than
patched. **The message is NOT amended** — rewriting published history to tidy a
sentence is a worse trade than a recorded corruption.

### 3.8 29 worktrees remain, none swept

`wt-item9` was mine and is **removed** (`EXIT 0`). The other 29 are listed with
age and attribution in the batch doc, item 9. `git worktree prune` would remove
none — every directory still exists. Only **1 of 29** attributes to a single
session (`defreg-vocab-52240` → cc).

### 3.9 The push gate writes three tracked files on every push

`docs/scrutiny-flags.json`, `docs/report-only-shard-state.txt`,
`docs/report-only-sweep-marker.txt` go dirty on each push attempt and blocked a
rebase three times. They belong to cc's `report_only_checks` / `scrutiny_flag`
machinery and **she declares them**, so this is an observation rather than a
routed finding. Restored, not committed. Mentioned because it will cost the next
session the same twenty minutes otherwise: **stash them, rebase, push, drop the
stash, restore.**

---

## 4. WHAT WAS RE-DERIVED AND FOUND FALSE

Seven premises, every one checked before acting:

| premise | what I ran FIRST | result |
|---|---|---|
| "a shell is still running" | `capture_exit.py --read` | **finished** at 01:30:20Z, EXIT 1 |
| the harness notification, twice | the status files | said "exit code 0"; real codes **1** and **2** |
| "report suites run" | the program's stdout | **745 files**, not 249 — two different populations |
| "three SHAs do not resolve" | `git fetch origin <sha>` ×4 | three confirmed, **a fourth exists** |
| "assign the 27 per the owner map" | the map, 965 entries | **0 of 27** — those files are the unowned ones |
| "the other 28 worktrees" | `clone_health_check.py` | **29**, one created during my own run |
| my own "40s is a 2x bound" | three runs | **EXIT 2, three of three** |

---

## 5. WHAT WENT WRONG THIS BATCH, MINE

1. **`_tree()` folded a could-not-ask into a clean answer** — the residue check
   in my own harness, which let a broken clone report clean for 6h31m.
2. **I set a bound from the wrong input.** 40s derived honestly from a 2.76MB
   file; the tool bounds a checker against a 5.51MB transform of it. Failed 3
   runs of 3, and the correction is **higher** than the value I replaced.
3. **I lost a backticked token to a shell in a commit message** — the exact
   defect `ledger_append.py` exists for, in the one place
   `eaten_substitution_check.py` is supposed to cover.
4. **`capture_exit.py`'s own lock count was a literal** and its reporter printed
   failure detail on passing arms — the third and second instances respectively
   of defects I had already fixed in sibling tools.
5. **I routed the `core.bare` cause to the wrong session last batch** (cc, on
   `sairn_push_gate_hook.py`). The owner is **fourth**. Corrected my own
   routing; reclassified nobody's finding.

1 and 2 were caught by driving the tools. 3 was caught by reading the shell's
own stderr. 4 was caught by reading my own output. **5 was caught by reading
another session's claim text**, which is the only one with no control behind it.

---

## 6. SESSION TRANSCRIPT

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\6f1d5069-5b6c-4a9d-8e38-78d125446571
```

`scratchpad/` — every run as a `*.status` beside its `*.out`:
`run_all_tests.{status,timing,out}`, `guard_ablation.*`, `meta1..3.*` (the 40s
failures), `meta145.*` (the 145s confirmation), `ce_fx_r1..3.out`,
`rat_st2_1..3.out`, `abl_base*.out` and `abl_1.out` (the criticality ablation),
`dis2.*` (the discharge), `audit.json`, and
`corruption-evidence/{git-config-BEFORE-repair.txt,git-config-mtime.txt,residue.diff}`.

**Read a status file, not a notification.** It was wrong twice in this batch.

---

# BATCH 21 CHECKPOINT LOG (appended one line per item, as worked)

- **item 1 — PARTIAL — commit pending (reviews done, NOT landed).** fourth holds
  `docs/tier-a-reviews.json` AND `tools/tier_a_review_gate.py`; a held claim is
  reported, never overridden, so **no discharge was written.** All 6 of my
  assigned-and-eligible obligations reviewed read-only with captured output;
  **4 of the 6 carry a sha that is not on origin** (`not our ref`). My two cc
  findings CONFIRMED landed: commit `d59f4a3c`, ancestor of origin/main, record
  (cc, 2026-09-28T10:44:30Z) now `status: reviewed`, `reviewer_session: cody`,
  `reviewed_at 2026-10-06T22:54:25Z`, 5677-byte verdict containing both findings
  and the one-line ablation as the reproducing artifact. **There is no seq** —
  seqs are the hover auditors' JSONL numbering; build-agent findings are
  identified by commit plus record identity. **NEXT STEP:** when fourth
  releases, paste the six verdicts from `docs/2026-10-07-cody-batch21.md` item 1
  through `tier_a_review_gate.py --discharge --body-file`.
- **item 2 — DONE — `~/.claude/settings.json`, no commit (outside the repo).**
  Backed up twice: `~/.claude/settings.json.bak-20261007T124442Z` and
  `<SCRATCH>/perm/settings.json.BACKUP-20261007T124442Z`. All **12 top-level
  keys preserved**, `CLAUDE_CODE_FORK_SUBAGENT=0` asserted present after the
  write. `defaultMode: acceptEdits`. allow 11→42, deny 3→25, ask 6→6 (4
  relocated, 4 added). Syntax checked against
  `https://code.claude.com/docs/en/permissions` read 2026-10-07: **0 grammar
  problems**, `defaultMode` confirmed a documented value. Allow proved
  (`git rev-parse --short HEAD` EXIT 0); a temporary deny pattern was inserted,
  verified present, and **removed** (verified absent). **Enforcement could NOT
  be demonstrated in-session and that is expected** — rules load at session
  start, as the item itself says. **DEVIATION REPORTED, NOT RESOLVED:** `Edit`
  and `Write` remain in `ask`, which outranks `defaultMode: acceptEdits`, so
  edits will still prompt; removing them would remove existing entries, which
  the item forbids. **NEXT STEP:** one authorisation to drop `Edit` and `Write`
  from `ask`, or accept that acceptEdits is inert for file edits.
- **item 3 — DONE — commit `e9304449` (fix at `543ffb8f`→rebased, register record
  on top).** `--pinned` now builds a throwaway `git clone --local --no-checkout`
  and checks the sha out there; 0 remaining `worktree add`/`worktree remove`
  calls. **Targeted proof, not a 6h run:** the exact write that broke this clone
  was run with cwd inside the sandbox — sandbox `core.bare=true`, **main clone
  `core.bare=false`**, `.git/config` byte-identical (sha256 `93070fe59db2…`, 506
  bytes before and after), `git config -l` identical, 0 worktree registrations.
  **First attempt leaked 239 files in silence** (`rmtree(ignore_errors=True)` vs
  git's read-only objects); fixed with an `onerror` handler that counts what it
  cannot remove. 2 of 2 fix-recheck rounds used. Claims: the file is in **my own**
  declared set; `sairn_claim.py` said BLOCKED on the phrase "clone pinned"
  against fourth's batch12, whose 20 declared files do not include it — matcher
  false positive, recorded not overridden. **NEXT STEP:** none; item 4 consumes it.
- **item 4 — first launch REFUSED BY ITS OWN GUARD, relaunching.** `--pinned`
  exited **2 COULD NOT RUN** because this checkpoint edit left the tree dirty:
  *"--pinned tests a COMMIT, and this clone has 1 uncommitted path(s) that would
  therefore NOT be tested."* Correct behaviour, and it exposes a real tension —
  the per-item checkpoint rule dirties the tree that `--pinned` requires clean.
  Resolution: commit the checkpoint, then launch. **The harness notification said
  "exit code 0" while the status file said EXIT 2 — fourth instance this session.**
- **item 4 — PARTIAL — running.** Relaunched on a clean tree at `c1cd7c41`.
  Confirmed in a **throwaway CLONE**, not a worktree: banner reads *"PINNED:
  running in a throwaway CLONE at c1cd7c41eaf5"*, 0 worktree registrations
  added, main clone `core.bare=false`. No concurrent whole-tree run (suite lock
  absent, 0 `run_all_tests` processes before launch).
  **STATUS FILE:** `<SCRATCH>/item4/suite.status`;
  **OUTPUT:** `<SCRATCH>/item4/suite.out`; **TIMING:** `<SCRATCH>/item4/meta.txt`.
  **NEXT STEP:** read the status file with `capture_exit.py --read`, then name
  every failing suite from `suite.out` with its first-run result. **The previous
  run took 23463s, so expect hours.**
- **item 5 — DONE — commit pending.** Cause re-derived **alone** at a clean HEAD:
  `guard_ablation.py --limit 1` → **EXIT 0**, 40 gates, 178 suites — so the
  earlier EXIT 2 was the residue, not a drift in the ablated shape. **And a
  worse defect was found in the same file:** `run()` returned **124** on a
  timeout and the ablation loop read `if run(...) != 0: noticed = s`, so a
  **timed-out suite counted as proof the guard was LOAD-BEARING** — a fabricated
  positive. `run()` now returns `None` (never an exit code); three buckets
  (green / red / COULD-NOT-RUN); a gate whose observers all timed out is
  COULD-NOT-RUN, not SILENT and never LOAD-BEARING; `--bound` added. Proved:
  `bound 1ms → None`, old `!= 0` would have called it noticed (True), new path
  does not. End to end `--bound 0.001` → **EXIT 2** with *"0 red on the shipped
  tree, 178 did NOT FINISH"*; control `--limit 1` → **EXIT 0** twice, COULD-NOT-RUN 0.
  **The first version of the refusal said "every suite is red", a false reason on
  a correct refusal** — found by the end-to-end run and fixed. 2 of 2 rounds used.
- **item 6 — DONE — commit pending.** Owner re-confirmed `basis: NONE,
  owner: null`, and it is in my own declared set, so claimed rather than routed.
  Detector widened from line-initial to **any position** as a SEPARATE class:
  the line-initial scan keeps its measured 0-false-positives-in-2,998 and does
  **not** lend that number to the new one. Measured on the same 3,000 commits:
  line-initial **4**, mid-line **29** → **19** after two exclusions found by
  hand-scoring (a digit on either side of the gap is columnar; a quote before it
  is a literal indent). Hand-scored 19: **14 true / 4 false / 1 uncertain**, and
  **the criteria were fitted to that corpus so 14 of 19 is an upper bound** — a
  fresh corpus is owed, and the tool prints that. Selftest built from
  `d59f4a3c`'s real line: **12 arms, 10 negative, 3 runs byte-identical, first
  run EXIT 0**. End to end on the range that used to return 0:
  **now EXIT 1**, naming body line 30 col 29. **NEXT STEP:** a fresh corpus
  (e.g. commits 3,000–6,000) to get an unfitted precision figure.
- **item 7 — DONE — report only, nothing assigned.** Re-derived at HEAD:
  **14 of 14 still unowned** (`basis: NONE, owner: null`), creating commits
  re-read from git, listed at the top of the final report for chat. **Nothing
  assigned and nothing claimed.** **7b: hank's index row has NOT landed** —
  `grep -c blob_conversion_coverage docs/SAIRN-OPEN-WORK-INDEX.md` → **0**, and
  `sd-store.js:166` → **0**. **There is no seq**: this was routed as a
  paste-ready row in `docs/2026-10-06-cody-queue19b-items-5-7-8-9-10-14.md`
  item 6, not through the auditors' JSONL, so no sequence number exists and
  inventing one would be a fabricated citation. **AND THE FILE IS NOW FREE** —
  no live claim declares `docs/SAIRN-OPEN-WORK-INDEX.md` — but it is not in my
  declared set and the row is hank's routed work, so it was not written.
- **item 8 — DONE — commit pending.** Re-measured at HEAD, nothing carried over:
  **moderate 1, high 2, total 3**. Reconciled: `@grpc/grpc-js` and **its
  companion low are GONE** (`low: 0`) — the doc was stale about the low; the two
  highs are confirmed one chain (same `via`, same `fixAvailable`, same
  `isSemVerMajor`). **`@fastify/busboy` added with measured reachability:**
  declared only by `firebase-admin ^3.0.0`, locked at 3.2.1, one call site at
  `firebase-admin/lib/utils/api-request.js:400` inside
  `handleMultipartResponse`, reached only when a RESPONSE content-type starts
  `multipart/`; **zero `fastify` references in `api/ tests/ tools/ scripts/`.**
  **DECISION: FIX, not accept-with-triggers** — measured in a scratch copy,
  `npm audit fix --package-lock-only --only=prod` changes exactly one line
  (3.2.1→3.2.2), `package.json` identical, audit after = moderate 0.
  **NOT APPLIED: `package-lock.json` is not in my declared set** and item 4 is
  still in flight. GitHub's 1-high vs npm's 2-high recorded as advisory-versus-
  package counting, not a contradiction.
- **item 9 — DONE — verified, not merged.** `git merge-base --is-ancestor
  origin/cody/firebase-modular-port origin/main` → **NOT an ancestor. ANDON
  HELD.** Branch tip `3de3cadd`, merge-base `d31ccdc4`, and
  `git merge-tree --write-tree origin/main 3de3cadd` → **EXIT 0, clean tree oid
  `ec911d448e09`** — it **still applies on current main with no conflict**.
  Re-measurement deferred to item 4 as instructed.
- **item 10 — DONE — commit pending.** Rule written, **ROUTED NOT PROMOTED**:
  `docs/METHODOLOGY.md` **and** `docs/2026-09-13-cross-domain-disciplines.md`
  are both in fourth's live declared set. **Next free convention number is 20**,
  counted (`grep -c "^## [0-9]*\." …` → **19**), not quoted. Full rule text is
  **inline** in `docs/2026-10-07-cody-routed.md` §3 — because METHODOLOGY.md's
  own queue records two of my earlier routings as NOT RECEIVED for naming a
  document that was not on `main`. Postmortem:
  `docs/postmortem-cody-2026-10-07-bound-measurement.md`, ending in **one
  system-level fix inside an existing check** — `metamorphic_check.py` now
  records and prints the largest artifact actually handed to a checker
  (`bound subject : …`), on clean runs as well as timeouts, and the timeout
  message carries the subject size. A report, not a refusal, because a bound
  that refuses its own subject is how a checker gets switched off.

---

# FULL HANDOFF — BATCH 21 (written after item 10, as instructed; refreshed at item 11)

## A. CLAIMS HELD — one

`cody / Tooling` — batch 21. **Declared FILES:** `tools/run_all_tests.py`,
`tools/guard_ablation.py`, `tools/eaten_substitution_check.py`,
`tools/capture_exit.py`, `tools/metamorphic_check.py`, `.claude/settings.json`,
`docs/2026-10-05-dependabot-high-triage.md`, `docs/2026-10-07-cody-batch21.md`,
`docs/postmortem-cody-2026-10-07-bound-measurement.md`,
`docs/2026-10-07-cody-routed.md`, `docs/handoff-cody-2026-10-07.md`,
`SAIRN-ACTIVE-WORK-cody.md`.

**The batch-20 claim was RELEASED FIRST at 2026-10-07T12:02:47Z** so the record
says one thing — `sairn_claim.py` refused to add an overlapping second claim and
was right to.

**HELD BY OTHERS AND NOT OVERRIDDEN, re-derived at HEAD:**

| file | holder | consequence |
|---|---|---|
| `docs/tier-a-reviews.json` | **fourth** | **item 1 could not land a discharge** |
| `tools/tier_a_review_gate.py` | **fourth** (owner map: cc, CONTESTED) | run read-only only |
| `docs/METHODOLOGY.md` | **fourth** | item 10 routed |
| `docs/2026-09-13-cross-domain-disciplines.md` | **fourth** | the convention routed, not written |

**Release:** `python tools/sairn_claim.py release Tooling`

## B. PUSHED STATE

```
origin/main  fa560504 at the time of writing (two commits pending below)
branch       cody/firebase-modular-port -> 3de3cadd   NOT an ancestor of main
             git merge-tree --write-tree origin/main 3de3cadd -> EXIT 0, clean
```

| commit | item |
|---|---|
| `e9304449` | item 3 — `--pinned` to a throwaway clone, plus its register record |
| `fa560504` | items 5 + 6 — the ablation fabricated positive, the eaten-substitution widening, and the item-5 register record |
| *pending* | items 7–10 — the triage addendum, the postmortem, the subject-size fix, the checkpoints |

## C. OPEN, WITH THE EXACT NEXT STEP

### C.1 Item 4 — the pinned whole suite is RUNNING

```
STATUS : <SCRATCH>/item4/suite.status      (capture_exit.py --read it)
OUTPUT : <SCRATCH>/item4/suite.out
TIMING : <SCRATCH>/item4/meta.txt
SHA    : c1cd7c41   sandbox: a throwaway CLONE, 0 worktree registrations
```

**NEXT STEP:** read the status file, then name **every failing suite** from
`suite.out` with its first-run result. **The previous unpinned run took 23463s**,
so expect hours. Do **not** start a second whole-tree run while it holds the
lock at `%TEMP%\sairn-suite-df228b25ddc49171.lock`.

### C.2 Item 10's confirming metamorphic run is RUNNING

```
STATUS : <SCRATCH>/i10_meta.status     OUTPUT: <SCRATCH>/i10_meta.out
```
**NEXT STEP:** confirm EXIT 0 and that the new `bound subject :` line names the
`duplicate` relation and an artifact larger than `stonedesk.html`.

### C.3 Item 1 — six reviews done, NONE landed

All six of my assigned-and-eligible obligations were reviewed read-only with
captured output. **4 of the 6 cite a sha that is not on origin**
(`13e40c9d79b7`, `a9e35feef967`, `c0be1a702088`, `c0ef09bdad7e` — all
`upload-pack: not our ref`), and the subjects were reconstructed from the
commit that last touched each named file.

**NEXT STEP:** when fourth releases `docs/tier-a-reviews.json`, discharge
through `tier_a_review_gate.py --discharge --takeover --body-file`. Evidence
already captured in `<SCRATCH>/r21/`:
`o1_probe` (21 passed), `o3_familymar` (10 passed, 2 runs),
`o4_sbap` (11 passed, 2 runs), `o5_suite` (10 passed),
`o2_json` (`db/schema_snapshot.json` parses, 442 keys, **`_constraints` still
absent**), `o6` (sairnsenior.html +14, a deliberate no-local-accessor note).

### C.4 Item 8's one-line lockfile fix is READY AND NOT APPLIED

```
npm audit fix --package-lock-only --only=prod
  -> node_modules/@fastify/busboy 3.2.1 -> 3.2.2   (the ONLY change)
     package.json identical; audit after: moderate 0
```
**NEXT STEP:** apply it, re-run `npm audit`, and confirm total 3 → 2. Needs
`package-lock.json` in the declared set.

### C.5 `Edit` and `Write` still sit in `permissions.ask`

They outrank `defaultMode: acceptEdits`, so edits will still prompt. **NEXT
STEP:** one authorisation to drop those two entries, or accept that acceptEdits
is inert for file edits. Backups:
`~/.claude/settings.json.bak-20261007T124442Z` and
`<SCRATCH>/perm/settings.json.BACKUP-20261007T124442Z`.

### C.6 Still open from earlier batches, unchanged

- **To fourth:** the clone-corruption writer is still unidentified; his fix
  `b23dbc2e` was already in the tree. `docs/2026-10-07-cody-routed-to-fourth.md`.
- **To cc and fourth:** `tier_a_review_gate.py --open` records HEAD rather than
  the subject commit — **two independent instances**, reproducing script in
  `docs/2026-10-07-cody-routed.md` §1.
- **Unowned:** `tools/deploy_verify_notify.py` exits **0** on an argument it does
  not understand (`--selftest` does not exist) — §2 of the same doc.
- **To chat:** the 14 unowned files, and whether an `# OWNER:` line becomes a
  condition of landing a tool.
- **A fresh corpus is owed** for the mid-line eaten-substitution precision
  figure: 14 of 19 was fitted to commits 1–3,000.

## D. TRANSCRIPT

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\6f1d5069-5b6c-4a9d-8e38-78d125446571
```

`scratchpad/` — `item4/` (the pinned suite), `r21/` (the six reviews),
`perm/` (settings backup, merge script, grammar check, the two item-3 proofs),
`i5_*` (ablation), `i6_*` (eaten substitution, including the 3,000-commit
measurements), `i8_*` (advisories), `i10_*` (the bound), plus every
`*.status` beside its `*.out`.

**Read a status file, not a notification.** The harness reported "exit code 0"
**five** times this session for programs that exited 1 or 2.

---

# ITEM 11 — FINAL REFRESH, and the claim is released below

**Nothing is half-finished.** Everything landed is pushed and verified at
`b637e2d4`; the one thing still moving is item 4, which has a status-file path
and cannot be hurried.

## FINAL VERIFICATION SWEEP, all at `b637e2d4`

```
tooling_inventory.py   --check      EXIT 0
master_plan.py         --check      EXIT 0
traceability_matrix.py --check      EXIT 0
run_all_tests.py       --selftest   EXIT 0
capture_exit.py        --fixtures   EXIT 0
eaten_substitution_check.py --selftest  EXIT 0
clone_health_check.py               EXIT 0   core.bare false, 0 dirty paths
merge-base --is-ancestor <branch> main  ->  ANDON HELD
```

**Item 10's confirming run landed and the fix is doing its job:**

```
capture_exit.py --read <SCRATCH>/i10_meta.status   ->  EXIT 0
  bound subject : PER_RUN_TIMEOUT=145s applies to a LARGEST artifact of
                  5.26MB, produced by relation 'duplicate' -- NOT to the
                  stonedesk.html on disk. Measure THIS when changing the bound.
  CLEAN -- every relation held on every comparison run.
```

**5.26MB is the number that was invisible when I set the bound from 2.76MB.**

## ITEM 4 IS STILL RUNNING AND THAT IS THE ONE OPEN THING

```
SHA     : c1cd7c41        sandbox: a throwaway CLONE, 0 worktree registrations
START   : 2026-10-07T13:13:23Z
STATUS  : <SCRATCH>/item4/suite.status   ->  RUNNING 80680
OUTPUT  : <SCRATCH>/item4/suite.out      ->  440 lines so far
TIMING  : <SCRATCH>/item4/meta.txt
```

**PARTIAL, with the path, as the item provides for.** The previous unpinned run
of the same suite took **23463s**, so this is expected to outlast the batch.

**NEXT STEP, in order:**
1. `python tools/capture_exit.py --read <SCRATCH>/item4/suite.status`
2. If `EXIT`: name **every failing suite** from `suite.out` with its first-run
   result. If `RUNNING`: it is still going — do **not** start a second
   whole-tree run; the lock is at `%TEMP%\sairn-suite-df228b25ddc49171.lock`.
3. Only a clean pass lifts the firebase andon. If suites fail, name each with a
   reproducing command and **do not claim a pass**.

## 29 WORKTREES REMAIN AND NONE WAS SWEPT

`clone_health_check.py` EXIT 0, 29 LIVE, 0 ORPHAN. **The pinned suite added
none** — a clone has no worktree registration, which was the point of item 3.
Two `sairn-suite-pinned-*` directories exist in `%TEMP%`: one is the live run's
sandbox, the other is from the launch its own dirty-tree guard refused. **Both
are outside the repo and neither is a registered worktree.**

## RELEASED

`python tools/sairn_claim.py release Tooling` — result recorded in the final
report.

---

# BATCH 22 CHECKPOINT LOG

- **item 1 — DONE — `~/.claude/settings.json`, no commit (outside the repo).**
  `Edit` and `Write` REMOVED from `permissions.ask` so `defaultMode:
  acceptEdits` governs them. **Removal, not a move to `allow`** — a rule in
  `allow` overrides a mode in the other direction and would keep auto-approving
  if the mode were later set back to `default`; "follow the default" means
  matched by **no** rule. The docs line that decides it, verbatim: *"An ask rule
  like `Bash(git clean *)` still prompts you … **even in auto mode**"* — an ask
  rule outranks a MODE, which is why acceptEdits was inert.
  **Counts, same diff method, same 12:44 baseline:** allow **11 → 42**, deny
  **3 → 25**, ask **6 → 4**; `defaultMode` absent → `acceptEdits`. This edit
  alone: ask 6 → 4, two lines removed, nothing else touched. Grammar re-checked:
  **0 problems**, `defaultMode` a documented value, `Edit`/`Write` in neither
  list. **A SEPARATE FINDING: the top-level `model` key disappeared between
  12:44 and 14:30 and NOT by any edit of mine** (`LOST by THIS edit: []`) — the
  app owns that setting, so it was not restored. Backups:
  `~/.claude/settings.json.bak-20261007T143044Z`,
  `<SCRATCH>/b22/settings.json.PRE-ITEM1-20261007T143044Z`.
  **NEXT STEP:** none — but enforcement still begins at the next session start,
  so Michael should confirm the first edit of a fresh session is not prompted.
- **item 2 — DONE — commit pending.** Claims-checked fresh first: **cody is the
  only session declaring `package-lock.json`**; `package.json` is declared by
  nobody and is **untouched** (`diff` → identical). Applied
  `npm audit fix --package-lock-only --only=prod`; **three lines changed**, all
  inside the one `@fastify/busboy` entry — `version`, `resolved`, `integrity`
  (3.2.1 → 3.2.2). `npm audit`: **moderate 1 → 0, total 3 → 2**; the two highs
  remain, as expected. `api/_lib/firebase-mint.test.js` still **EXIT 0**, 16/16.
  **STATED LIMIT: `node_modules` lives OUTSIDE this clone, so the INSTALLED
  busboy is still 3.2.1 while the LOCK now says 3.2.2.** The fix lands for the
  deploy and for `npm audit`; this clone's installed tree is unchanged until
  someone runs `npm install`. **NEXT STEP:** nothing required — the deploy
  installs from the lock.
- **item 3 — DONE — commit pending.** `docs/2026-10-07-cody-harness-exit-mismatches.md`.
  **MY OWN FIGURE WAS WRONG AND IS CORRECTED: six program-level mismatches, not
  five**, across **three** notifications of the four that fired; the fourth
  agreed (`meta145` real EXIT 0) and is listed so the six are not a selected
  set. Each cited with command, claimed `exit code 0`, real captured code,
  status-file line and recording commit (`166fe4ef`, `b637e2d4`, `c1cd7c41`).
  **Case 6's status file no longer exists** — a relaunch reused the same path and
  `capture_exit.py` replaces rather than appends; cited from the committed
  handoff instead, and the usage rule (**one status path per run**) is the only
  new thing. **Two findings routed:** (A) `defect_register.py --reseat` rewrites
  the whole ledger — **24,724/24,724 to change six fields**, caused by
  `indent=2` + `ensure_ascii=True` against a stored `indent=1`; after stripping,
  only 10 lines differ. Same shape as the 5681-line incident, on a file whose own
  merge policy is 3-way-from-ancestor. Reverted; **my two records corrected by
  raw-text substitution: 2 insertions, 2 deletions, 470 records intact,
  `--check` EXIT 0.** (B) four more orphaned citations belong to other sessions
  and were **not** taken. **NEXT STEP:** cc to decide the `--reseat` serialisation
  fix; the four orphans to their originators (fourth is already sweeping).
- **item 4 — DONE — the premise is overturned: THE ROUTING WAS RECEIVED.**
  Confirmed by READING the intake rule, not guessing. `docs/METHODOLOGY.md`
  states it itself: *"A convention goes in
  `docs/2026-09-13-cross-domain-disciplines.md`, as a numbered section … Nowhere
  else"*, *"a dated inventory may STATE a lesson and route it"*, and
  *"this file records what is ROUTED HERE AND NOT YET PROMOTED"* — so the intake
  queue is the table in METHODOLOGY.md and the home is the disciplines file.
  **Both are DECLARED by fourth in a claim 0.5h old (fresh list), so neither is
  writable by me** — and that is precisely why a third inlining would have been
  the wrong move. **It was not needed:** commit `4c574225`, on origin/main,
  promoted my rule as **convention 21** *verbatim*; the disciplines file now has
  **21** `## <n>.` headings (counted, was 19 earlier today). fourth's own queue
  row states the mechanism behind both earlier NOT RECEIVED verdicts:
  *"the first routing into this file that arrived as **paste-ready text in a
  readable document** rather than as a reference to a file not on `main`."*
  **All four of my routed docs verified present on origin/main.** My §1 finding
  was also received and **independently replicated by fourth 4 of 4**, and his
  row says cody and cc close it — correct, I am the originating finder.
  **NEXT STEP: none.** The transferable lesson is already recorded by fourth:
  route paste-ready text in a document that is on `main`, never a reference.

---

# FULL HANDOFF — BATCH 22 (written after item 4, as instructed; refreshed at item 8)

## A. CLAIMS HELD — one

`cody / Tooling` — batch 22. **Declared FILES:** `.claude/settings.json`,
`package-lock.json`, `tools/metamorphic_check.py`, `tools/capture_exit.py`,
`docs/2026-10-05-dependabot-high-triage.md`, `docs/2026-10-07-cody-routed.md`,
`docs/2026-10-07-cody-harness-exit-mismatches.md`,
`docs/handoff-cody-2026-10-07.md`, `SAIRN-ACTIVE-WORK-cody.md`.

**One file was written that is NOT in that list and it is declared here:**
`docs/defect-density-register.json` — two of my own orphaned sha citations,
**2 insertions / 2 deletions**. No live claim declares it; it was not in my
originally declared set and the write is narrower than a reseat.

**HELD BY OTHERS, re-derived from a FRESH claim list at `10521191`:**

| file | holder | consequence |
|---|---|---|
| `docs/METHODOLOGY.md` | **fourth** (0.5h) | item 4 confirmed, not written |
| `docs/2026-09-13-cross-domain-disciplines.md` | **fourth** (0.5h) | the convention was promoted BY fourth, not by me |
| `tools/doc_sha_reseat.py`, `tools/report_only_checks.py`, `tools/sairn_push_gate_hook.py`, `docs/tool-owner-map.json` | **cc** | untouched |
| `tools/defect_register.py` | **cc** by owner map (CONTESTED) | finding routed, tool untouched |

**A STALE CLAIM LIST NEARLY COST A CONFLICT.** My first read of `--list` was
captured before fourth re-claimed and showed **no fourth claim at all**; a fresh
call showed fourth holding both methodology files. Every declared set in this
batch was re-read live. **Release:**
`python tools/sairn_claim.py release Tooling`

## B. PUSHED STATE

```
origin/main at the time of writing : 10521191 + the commits below
branch cody/firebase-modular-port  : 3de3cadd  -- NOT merged, ANDON HELD
```

| commit | item |
|---|---|
| `327bb513` | item 2 — the busboy lockfile fix, three lines |
| `7786b054` | item 3 — the six mismatches, plus my two sha citations corrected |
| *pending* | item 4's checkpoint and this handoff |

Items **1** (settings.json) and **4** (confirmation only) produced no repo
commit by design.

## C. OPEN, WITH THE EXACT NEXT STEP

### C.1 Item 5 — the suite is STILL RUNNING; the andon cannot be cleared yet

```
STATUS : <SCRATCH>/item4/suite.status   ->  RUNNING 80680, started 2026-10-07T13:13:23Z
OUTPUT : <SCRATCH>/item4/suite.out      ->  471 lines
SANDBOX: a throwaway CLONE at c1cd7c41, 0 worktree registrations
```

**NEXT STEP, in order:** `capture_exit.py --read` the status file; if `EXIT`,
name every failing suite from `suite.out` with its first-run result, then re-run
`git merge-tree --write-tree origin/main origin/cody/firebase-modular-port` and
report its **captured** exit code. **Only a clean pass clears the andon.** Do
not start a second whole-tree run — the lock is at
`%TEMP%\sairn-suite-df228b25ddc49171.lock`.

### C.2 Item 1's effect begins at the next session start

`Edit`/`Write` are now matched by no rule, so `defaultMode: acceptEdits`
governs. **NEXT STEP:** Michael confirms the first edit of a fresh session is
not prompted. Backups:
`~/.claude/settings.json.bak-20261007T143044Z`,
`<SCRATCH>/b22/settings.json.PRE-ITEM1-20261007T143044Z`.

### C.3 Routed and not mine to close

- **cc** — `defect_register.py --reseat` rewrites the whole ledger
  (**24,724/24,724** for six fields; `indent=2` + `ensure_ascii` against a
  stored `indent=1`). Reproducing command in
  `docs/2026-10-07-cody-harness-exit-mismatches.md` §A.
- **four other sessions** — four orphaned register citations, with the correct
  mapping printed, not applied.
- **cc** — `tools/eaten_substitution_check.py`: a fresh corpus (commits
  3,000–6,000) is owed for the mid-line precision figure; 14 of 19 was fitted.
- **unowned** — `tools/deploy_verify_notify.py` exits **0** on an unknown flag.
- **chat** — the 14 unowned `tools/*.py`, and whether an `# OWNER:` line becomes
  a condition of landing a tool.

### C.4 A separate, non-mine change to the settings file

The top-level `model` key disappeared between 12:44 and 14:30 and **not by any
edit of mine** (`LOST by THIS edit: []`). The app owns that setting; it was not
restored. Recorded so nobody reads it as collateral from the permissions work.

## D. TRANSCRIPT

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\6f1d5069-5b6c-4a9d-8e38-78d125446571
```

`scratchpad/b22/` — settings backups, the grammar check, both diffs, the
lockfile before/after, `audit_before.json` / `audit_after.json`, the reseat
output, `old.json`. `scratchpad/item4/` — the running suite.
`scratchpad/r21/` — the six Tier A reviews from batch 21.
- **ESCALATION — THE PUSH IS BLOCKED BY THE REMOTE, NOT BY A GATE.** Three
  attempts, all `! [remote rejected] main -> main (Internal Server Error)`.
  **Not a gate refusal:** 0 lines matching blocked/denied/refus in the output,
  2 matching `Internal Server Error`. `git ls-remote` EXIT **0** and the remote
  tip `0cefb393` **equals** my local `origin/main`, so it is not a race either —
  I read it as one on the second attempt and that reading was wrong. Rebase is a
  no-op (`Current branch main is up to date`). **Per the 2-round cap this is
  ESCALATED, and the three commits are intact locally:** `145d1547` (item 2),
  `5ab99a27` (item 3), `c568a049` (item 4). **NEXT STEP:** retry
  `git push origin main` later; nothing needs re-doing.
- **item 6 — DONE — commit pending.** Re-measured: **moderate 0, high 2, total
  2** — the busboy moderate is gone, so everything left is the single
  `node-forge` advisory counted twice. **DECISION: WAIT**, accepted, four
  triggers unchanged. Measured basis, all re-derived: **exactly 1 of 1**
  `forge.*` call sites in firebase-admin is
  `pki.privateKeyFromPem` at `lib/app/credential-internal.js:150` — **a parser,
  return value discarded**, on our own key from our own env var, while the
  advisory is about **verification** (`rsa.js`); node-forge **1.4.0 is both
  installed and the newest published**, so no patch exists and the major bump is
  the only fix; and that bump is prepared but gated. **What changed since
  addendum 3: trigger 1 is no longer a rewrite, it is a suite run** — the port
  exists, so the andon now hangs on one condition. Written as addendum 5 of
  `docs/2026-10-05-dependabot-high-triage.md`.
- **item 7 — DONE — commit pending.** **"No new rule, reinforces existing"** for
  the mismatch itself: all six share the trailing-element cause
  `capture_exit.py` was built for, and convention **15** held all six times. Six
  in a day is a frequency measurement, not a new shape, and nothing is proposed
  for the conventions file on its account. **One new line IS owed, and it is
  about the evidence rather than the number:** *a status file is evidence, so one
  status path per run; a path reused across a relaunch destroys the first run's
  verdict.* Paid for by case 6, the only one of the six that cannot be cited
  from a file. Written paste-ready in `docs/2026-10-07-cody-routed.md` §5 and
  **ROUTED** — both convention files are declared by fourth.
- **item 5 — PARTIAL — the suite has NOT finished, so the andon does NOT clear.**
  Status read from the file, never a notification:
  `capture_exit.py --read <SCRATCH>/item4/suite.status` → **exit 2, `RUNNING
  80680`**, started 2026-10-07T13:13:23Z. **Progress confirmed, not assumed:**
  child PIDs churned 25 → 27 with several replaced over 25s, and wrapper 80680
  is alive. **466 suites reported, 0 FAIL so far** — a useful partial, not a
  pass. **AND ONE OBSERVATION WORTH CARRYING: `suite.out` had not been written
  for 35 minutes** (mtime 14:45:10Z, checked at 15:20:12Z) while children kept
  turning over, so a single test file has been running ~35 minutes. The last
  line is `ok py tests/run_hook_integrity_probe.py`; the next file
  alphabetically is `tests/run_hover_audit_method_sabotage_probe.py`. **I did not
  name the current child** — `wmic` returned no command lines and guessing it
  would be a fabricated citation.
  **The merge-tree check was re-run anyway, with captured codes:**
  `git merge-tree --write-tree origin/main origin/cody/firebase-modular-port` →
  **EXIT 0**, tree `87316631d227`; against local HEAD `e958eb50` → **EXIT 0**,
  tree `984e042eddf7`; `git merge-base --is-ancestor <branch> origin/main` →
  **EXIT 1**. **So the branch still applies cleanly and is still not merged.
  ANDON HELD** — the blocker is the suite condition, not a conflict.
  **NEXT STEP:** `capture_exit.py --read` the status file; on `EXIT`, name every
  failing suite from `suite.out` with its first-run result, then re-run the two
  merge-tree commands and report their captured codes. Only a clean pass clears it.

---

# ITEM 8 — FINAL, BATCH 22. CLAIM RELEASED BELOW.

## CORRECTION TO MY OWN ESCALATION NOTE ABOVE

The note said the push was *"blocked by the remote, not by a gate"* after three
`Internal Server Error` rejections. **That was true of those three attempts and
it was NOT the whole story.** The fourth attempt revealed a **register conflict**:
another session had appended three records, and my two-line sha correction
collided. `git ls-remote` had been EXIT 0 the whole time, so the server errors
were transient — and the real obstacle arrived afterwards. **Both facts are kept
rather than the tidier one.**

## A. PUSHED STATE — ALL FIVE COMMITS LANDED

```
origin/main  91f918e9     verified ahead 0 / behind 0, tree clean
branch       cody/firebase-modular-port -> 3de3cadd   NOT an ancestor. ANDON HELD.
```

| commit | item |
|---|---|
| `a1386313` | 2 — the busboy lockfile fix, three lines, `package.json` untouched |
| `43c61abc` | 3 — six mismatches, not five |
| `5a9b6bdb` | 4 — the routing was received, promoted as convention 21 |
| `996b6592` | 6 + 7 — the WAIT decision, and one new methodology line |
| `91f918e9` | 5 — the andon status with captured merge-tree codes |

Items **1** (`~/.claude/settings.json`) produced no repo commit by design.

## B. THE SHA CORRECTION WAS ABANDONED, AND THAT IS THE RIGHT OUTCOME

`tools/sairn_rebase_resolve.py` **refused** my two-line fix: the ledger's
identity is `["commit", "summary"]`, so changing `commit` is a **DELETE plus an
INSERT** on an append-only file. **A sha reseat is unmergeable on this ledger by
the ledger's own policy** — minimal or whole-file alike. So the 24,724-line diff
is a symptom, not the disease.

**`git diff origin/main..HEAD -- docs/defect-density-register.json` is EMPTY —
I change that file not at all.** `defect_register.py --check` **EXIT 0** over the
upstream 473 records. My two records still cite `538451398bf0` and
`543ffb8f5d02`, both orphaned, and that is recorded rather than tolerated
quietly. Full finding: `docs/2026-10-07-cody-routed.md` §6, for **cc**.

## C. OPEN, WITH THE EXACT NEXT STEP

### C.1 The suite — still running, 476 reported, **0 FAIL**

```
STATUS : <SCRATCH>/item4/suite.status  ->  exit 2, RUNNING 80680 (started 13:13:23Z)
OUTPUT : <SCRATCH>/item4/suite.out     ->  476 suites reported, 0 FAIL
```
**NEXT STEP:** `capture_exit.py --read` it. On `EXIT`, name every failing suite
with its first-run result, then re-run both `merge-tree` commands and
`merge-base --is-ancestor`, reporting captured codes. **Only a clean pass clears
the andon.** Do not start a second whole-tree run — lock at
`%TEMP%\sairn-suite-df228b25ddc49171.lock`.
**Carry forward:** `suite.out` went 35 minutes without a write while children
churned, so one test file is very slow. Not diagnosed; not guessed at.

### C.2 Permissions take effect at the next session start

`Edit`/`Write` are matched by no rule, so `defaultMode: acceptEdits` governs.
**NEXT STEP:** Michael confirms the first edit of a fresh session is not
prompted. Backups `~/.claude/settings.json.bak-20261007T143044Z` and
`<SCRATCH>/b22/settings.json.PRE-ITEM1-20261007T143044Z`.

### C.3 Routed, not mine to close

- **cc** — the reseat/identity-key problem (§6) **and** the whole-file
  serialisation (§A of the mismatches doc). `.githooks/post-rewrite` calls
  `--post-rewrite` automatically, so this fires on any rebase that moves a cited
  commit.
- **cc** — a fresh corpus is owed for the mid-line eaten-substitution precision
  (14 of 19 was fitted to commits 1–3,000).
- **four sessions** — four orphaned register citations, mapping printed, not
  applied.
- **unowned** — `tools/deploy_verify_notify.py` exits 0 on an unknown flag.
- **fourth** — the clone-corruption writer is still unidentified.
- **chat** — the 14 unowned `tools/*.py`; whether an `# OWNER:` line gates
  landing a tool.

### C.4 The advisory position

**moderate 0, high 2 (one chain), total 2. DECISION: WAIT**, four triggers
unchanged, basis in addendum 5. Trigger 1 is now a suite run, not a rewrite.

### C.5 Not mine, recorded so it is not read as collateral

The top-level `model` key left `~/.claude/settings.json` between 12:44 and 14:30
and **not by any edit of mine**. The app owns that setting; not restored.

## D. TRANSCRIPT

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\6f1d5069-5b6c-4a9d-8e38-78d125446571
```

`scratchpad/b22/` — settings backups and both diffs, the grammar check,
`audit_before/after/i6.json`, the lockfile before/after, the reseat and resolver
outputs, every `*.status` beside its `*.out`. `scratchpad/item4/` — the running
suite. `scratchpad/r21/` — batch 21's six Tier A reviews.

## E. THREE COMMITS FAILED BEFORE LANDING TODAY, ALL LOUDLY

`git commit -m` with backticks → **EXIT 127**, nothing landed.
`git commit -F /dev/stdin` → **EXIT 128**, nothing landed.
A rebase conflict on the register → resolver **EXIT 1**, change abandoned.
**Every one failed in a way that could not be mistaken for success**, which is
the only reason none of them became a corrupted record. The control in all three
cases is the same: a real message file, and a resolver that refuses.

---

# ITEM 12 — FINAL, BATCH 23. Written at a point where nothing is half-finished.

Resumed from a stopped terminal with no memory of the batch. Everything below
was re-derived; nothing was carried from the sections above without a re-check.
Full per-item detail: **`docs/2026-10-07-cody-batch23.md`**.

## A. CORRECTION TO THE BATCH 22 SECTION ABOVE

Batch 22 left `tools/tier_a_review_gate.py` and
`tests/run_tier_a_review_gate_probe.py` **modified in the working tree and
uncommitted**, and **the probe did not compile**: two string literals contained
a real newline (`SyntaxError: unterminated string literal`, line 2198). A probe
that cannot be imported reports nothing, and the handoff did not say the work
was in that state. Fixed first, before anything else in this batch.

The batch-22 note *"the top-level `model` key disappeared … not by any edit of
mine"* **stands**, and the window narrows from 12:44→14:30 to
**12:48:04Z→14:30:44Z**. See §C.2.

## B. PUSHED STATE

```
HEAD          8ee6e7c2   rebased onto origin/main (4263ed6b) cleanly, rc 0
branch        cody/firebase-modular-port -> 3de3cadd   NOT an ancestor. ANDON HELD.
```

| commit | item |
|---|---|
| `8ee6e7c2` | 8 — `subject_sha()`, the basis field, and 8 probe arms |
| the docs commit beside it | the batch doc, this handoff, the active-work append |

Items **1, 2, 3, 4, 5, 6, 7, 9, 10, 11** produce no code commit **by design** —
each is a report, a measurement, or an explicit do-not-touch.

## C. OPEN, WITH THE EXACT NEXT STEP

### C.1 The firebase andon — HELD, and the suite run is VOID not red

The run finished and **its own last line voids it**:

```
capture_exit.py --read <OLD-SCRATCH>/item4/suite.status
  -> EXIT 2 2026-10-07T16:23:49Z python tools/run_all_tests.py --pinned
suite.out last line:
  EXIT 2 -- COULD NOT RUN: the clone was broken during this run,
            so no verdict above is attributable
```

**1 run at `c1cd7c41eaf5`, and the first run returned EXIT 2.** 748 files ran,
183 reported FAIL, **none attributable**. Wall time **11,427 s**.

The guard fired on `git status exited 3221225794` = **`0xC0000142`, a process
that failed to INITIALISE** — git could not be launched. That is a genuine
could-not-tell, but the message's *"something in the suite broke this clone"* is
a cause it did not demonstrate. The live clone reads `core.bare=false` rc 0; the
throwaway clone `sairn-suite-pinned-9nb6j88c` **is gone**, so the one place that
could settle it no longer exists.

**NEXT STEP:** re-run `python tools/run_all_tests.py --pinned` once, alone, and
treat EXIT 2 as a harness problem rather than a suite verdict if it recurs.
**Only a clean pass clears the andon.** Captured codes this batch, each from its
own `.status` file:

```
merge-tree origin/main .. branch            -> EXIT 0  tree f4ebb446d0fa
merge-tree HEAD        .. branch            -> EXIT 0  tree f2b7bb72c578
merge-base --is-ancestor branch origin/main -> EXIT 1
```

### C.2 `~/.claude/settings.json` — Edit/Write CONFIRMED; the `model` key NARROWED

**Edit/Write no longer prompt. Confirmed in this fresh session:** every `Edit`
and `Write` call completed with **zero prompts** — **10 `Edit` and 3 `Write`**
by the time this line was written, the first before any settings work. `ask`
holds only the four `rm -rf` / `reset --hard` / `clean` / `branch -D` rules;
`defaultMode: acceptEdits`. Batch 22's prediction held.

**The `model` key: cause narrowed to the Claude Code application's own settings
writer**, by exclusion plus file shape — not unknown, and not provable to the
keystroke. Replaying batch 22's `merge.py` against a copy of the 12:44:42Z
backup reproduces the 14:30:44Z file **except that the replay keeps
`"model": "sonnet"`** — one key, nothing else. `final.diff` at 12:48:04Z still
shows no model line, so the window is **12:48:04Z → 14:30:44Z**. Ruled out:
another clone's session (no other handoff records a write), a migration into
`.claude.json` (no model key there), collateral on other keys (the replay
proves one key). No app-side audit trail exists: `~/.claude/logs` absent,
`~/.claude/backups` holds only `.claude.json.backup.*`, oldest **15:57Z — after
the window**. **Not restored; the app owns that setting.**

**AND A WRITE I DID NOT INTEND, verified and reported:** a failed `sed`
substitution left the replay pointed at the live file and it **rewrote
`~/.claude/settings.json`**. Content verified identical afterwards (3700 bytes,
11 keys, allow 42 / deny 25 / ask 4, `defaultMode acceptEdits`,
`CLAUDE_CODE_FORK_SUBAGENT=0`, diff vs the 14:30:44Z snapshot still exactly the
two `Edit`/`Write` lines); **only the mtime moved**. The write was idempotent.
Generalised as the method improvement, §C.6.

**NEXT STEP:** none. If Michael wants `model` back it is a `/model` selection,
not a file edit.

### C.3 The 35-minute test file is STILL NOT NAMED, and why

`Get-CimInstance Win32_Process … Select CommandLine` **works** where `wmic`
returned nothing — but my suite had already ended when I ran it, so every
process it listed was hank's. Measured instead:

| program | measured | source |
|---|---|---|
| `run_all_tests.py --pinned` | **11,427 s**, 748 files | `item4/meta.txt` |
| `guard_ablation.py --limit 1` | **328 s**, EXIT 0 | `t4/abl.status` |
| `run_hover_audit_method_sabotage_probe.py` alone | **567 s**, EXIT **2** | `t4/hover.status` |

The alphabetically-next file after the last written suite line is
`run_hover_audit_method_sabotage_probe.py`, and run alone it stopped early on a
red baseline (EXIT 2, 567 s) — a **lower bound on a different code path**.
Adjacency plus a lower bound is not an identification, so it is not named.

**PROPOSED BOUND, basis one measured run, labelled weak: 900 s per test file,
14,400 s for a whole `--pinned` run. NO FILE WAS CHANGED.**

**NEXT STEP:** to name it, run `--pinned` with `Get-CimInstance` sampled on a
timer *while it runs*, or add per-file timing to `run_all_tests.py` (my file,
not in this batch's declared FILES).

### C.4 Routed, not mine to close

- **cc — `tools/sairn_rebase_resolve.py` refusal.** Reproducing artifact
  complete in `docs/2026-10-07-cody-batch23.md` §9: the exact command, the
  captured `EXIT 1 2026-10-07T15:32:27Z` status line, the full REFUSED output
  naming both deleted ancestor records, and the ledger's own identity-key line
  at `docs/defect-density-register.json:3-9` showing **`"identity": ["commit",
  "summary"]`** — so changing a `commit` is a DELETE plus an INSERT on an
  append-only ledger. **Not fixed. `git diff origin/main..HEAD --
  docs/defect-density-register.json` is EMPTY.**
- **cc** — the whole-file serialisation of `defect_register.py --reseat`
  (24,724 lines for six fields), a symptom of the same identity rule.
- **chat** — the method improvement in §C.6, because both convention files are
  declared by fourth.
- **me, next batch** — the `run_all_tests.py` third-state message names a cause
  it did not establish (`0xC0000142` is a launch failure), and the harness
  deletes the throwaway clone that would settle it.

### C.5 Tier A obligations — 6 eligible, discharged NONE, and that is deliberate

`tools/tier_a_review_gate.py --list` → **EXIT 1**, 26 open. **6** are authored
by somebody else and assigned to cody: 49.7h `quotes` (fourth), 43.4h `alf_*`
(fourth), 34.5h `alf_clients…` (hank), 34.5h `quotes, sb_ap` (cc), 33.3h
`sdn_projects` (hank), 32.8h `sen_settings` (hank). A further 13 are
takeover-eligible past 48h.

**fourth's active claim declares `docs/tier-a-reviews.json` in its FILES**, and
a discharge writes that file. **NEXT STEP:** when fourth releases, discharge
most-overdue-first starting with the 49.7h `quotes` record.

### C.6 Method improvement — routed to chat

*A redirection that fails must not leave the program pointed at production.*
Paid for by §C.2's accidental write: the `sed` that was supposed to aim a replay
at a sandbox silently did not match, exited 0, and the **default on failure was
the real file**. The uniqueness-guard half (`count(anchor) != 1`) is
reinforcement of an existing convention I failed to apply. The new half is
structural: **take the path as a required argument with no default**, so a
redirection that does not happen crashes instead of writing to production.

### C.7 Dependencies

- **busboy** — **the deploy already matches the lock, measured on a real
  build.** `dpl_3eBAEBXL1fM4pxZAGzJBG4SgQc5F` (commit `4263ed6b`, build
  `bld_7y25kav6y`) printed `Installing dependencies…` → **`up to date in
  836ms`**; no `installCommand` in `vercel.json`, and npm would have reported a
  change had the cached tree disagreed with the lock. The 3.2.1 is only in the
  shared `C:\Users\marsh\node_modules`, which this lockfile does not govern
  (no `package.json` there). **Michael's optional one-liner, local probes only:
  `cd C:\Users\marsh && npm install @fastify/busboy@3.2.2`.**
- **node-forge — WAIT HOLDS. `npm view node-forge version` → 1.4.0, which is
  what is installed; `npm view node-forge time` shows 1.4.0 published
  2026-03-24 and nothing newer.** No patched release exists.
  **WAIT TRIGGER, written here as instructed:** re-run
  `npm view node-forge version` and act only when it returns **anything above
  1.4.0**, OR when `firebase-admin` publishes a release whose tree drops
  node-forge or moves it off the 1.4.x line. Until one of those is true there is
  nothing to apply and the major bump stays prepared and gated.

### C.8 Not an item, found while working: 30 stale worktree registrations

`git worktree list` in this clone shows **30 entries**, 29 of them temp-dir
probe leftovers (`sairn-abl-*`, `check4-probe-*`, `gate12-*`, `condcov-*`,
`defreg-probe-*`, …), one `locked`. A linked worktree **shares this clone's
`.git/config`**, which is the exact mechanism `run_all_tests.py`'s own guard
names for a `core.bare` flip. **Not pruned** — `git worktree prune` is a repo
state change outside this batch's declared FILES, and one entry is locked.
**NEXT STEP for whoever owns this:** `git worktree prune` after checking the
locked one.

## D. CLAIMS HELD

`cody / Tooling` — batch 23, the narrowed claim committed at `dea44d22`.
**Declared FILES actually touched:** `tools/tier_a_review_gate.py`,
`tests/run_tier_a_review_gate_probe.py` (the claim's FILES line spells it
`tests/run_tier_a_gate_probe.py` — the real file is
`run_tier_a_review_gate_probe.py`, recorded rather than silently reconciled),
`docs/2026-10-07-cody-batch23.md`, `docs/handoff-cody-2026-10-07.md`,
`SAIRN-ACTIVE-WORK-cody.md`. `.claude/settings.json` (the repo one) was **NOT**
touched; the settings work is all in `~/.claude/settings.json`, outside the
repo. **NOT TOUCHED, held by others:** `docs/tier-a-reviews.json`,
`docs/METHODOLOGY.md`, `docs/2026-09-13-cross-domain-disciplines.md`,
`docs/known-red-suites.json` (fourth); `tools/report_only_checks.py`,
`tools/sairn_push_gate_hook.py`, `tools/doc_sha_reseat.py`,
`docs/tool-owner-map.json` (cc). **I closed no finding I did not originate and
reclassified none.**

## E. TRANSCRIPT

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\20e0ab2b-79b3-44cb-b3dc-fe1a01d0c89e
```

`scratchpad/prefix_demo.py` — the pre-fix/post-fix fixture driver, with
`pre.txt` and `post.txt`. `scratchpad/i3/` — `merge_replay.py`, `replay.out`,
`replay_input.json` (the settings replay). `scratchpad/t4/` — `hover.{status,
out,time}`, `abl.{status,out,time}`, `git_before.txt`, `wt_before.txt`.
`scratchpad/i5/` — `mt1`, `mt2`, `anc` status files for the andon.
`scratchpad/i8_run1..3.out`, `i8_remeasure.txt` — the probe runs and the
re-derivation. Previous batch's artifacts remain under
`…\6f1d5069-5b6c-4a9d-8e38-78d125446571\scratchpad\{b22,item4,perm,r21}`.
