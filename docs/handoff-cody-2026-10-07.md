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
