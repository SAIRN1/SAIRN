# cody — handoff, 2026-10-07c (batch 25 / b2)

**Claim:** `cody / Tooling`, batch 25, taken at HEAD `b3ce8f23`.
**Written per item and committed per item**, as item 2 of batch 24 set the habit.
Every premise below was re-derived **at pickup** from `sairn_claim.py` (the
registry) and from `origin/main` — never from a claim-file read alone.

`sairn-guardian-v2` was **not loaded**: no item in this batch edits an app file.

---

## item 1 — BLOCKED. The holder is **cc**. 6 eligible, 0 discharged.

```
command : python tools/sairn_claim.py check Tooling "tier a review discharge docs/tier-a-reviews.json most overdue"
commit  : b3ce8f23        date: 2026-10-08
result  : EXIT 1 -- BLOCKED
```

```
session  : cc
claimed  : 2026-10-07T23:20:05Z  (0.7h ago)
declares : docs/tier-a-reviews.json  -- IN ITS FILES SEGMENT, not merely in prose
its own item 1 : "Tier A: my own most-overdue eligible first, freshness-checked
                  before each verdict" -- the identical discharge
```

**hank's claim was also checked, as the item asks.** `platform`, last activity
**8.0h ago** — past the 4h expiry, so **not live**; its Tier A text says its own
18 eligible were listed and not discharged. So hank is **not** the blocker; cc is.

**My 6 eligible, re-derived at `aa2f014d` on 2026-10-08** (22 open in the ledger;
authored by another session **and** `reviewer_owner == cody`):

| age | author | opened | resources |
|---|---|---|---|
| 57.1h | fourth | 2026-10-05T15:02:28Z | `quotes` |
| 50.7h | fourth | 2026-10-05T21:25:19Z | `alf_activities, alf_billing, alf_claim_routes, …` |
| 41.9h | hank | 2026-10-06T06:14:34Z | `alf_clients, alf_family_contacts, alf_mar` |
| 41.9h | cc | 2026-10-06T06:18:11Z | `quotes, sb_ap` |
| 40.7h | hank | 2026-10-06T07:29:58Z | `sdn_projects` |
| 40.2h | hank | 2026-10-06T07:56:17Z | `sen_settings` |

A further **9** are open, owned elsewhere and past the 48h takeover line. None
taken, for the same reason.

**No freshness check was run against any of the six**, because a freshness check
is the first step of a discharge and the discharge is blocked. Running the checks
and then not writing a verdict would produce six measurements with nothing to
attach them to.

**NEXT STEP:** when cc releases, `sairn_claim.py check` first, then declare the
ledger and discharge **fourth `2026-10-05T15:02:28Z` `quotes`** — freshness check
before the verdict — and work down the table.

## item 2 — SKIPPED, and this says so. cc's `superseded_by` support has NOT landed.

```
command : git show origin/main:tools/defect_register.py | grep -n "superseded_by\|superseded"
commit  : b3ce8f23        date: 2026-10-08
result  : ZERO hits
command : git ls-tree -r --name-only origin/main | grep -i superseded
result  : no such path -- cc's probe does not exist on origin/main either
working tree : grep -c superseded_by tools/defect_register.py -> 0
```

cc's live claim confirms why: its **item 3** is building that support now —
*"defect_register.py Option A: superseded_by honoured only when the named survivor
EXISTS and is an ANCESTOR of origin/main; `--reseat` never re-seats or reports
success on a superseded record; fixtures for live-survivor-passes,
survivor-missing, survivor-not-an-ancestor and self-reference"*. It is in
progress, not landed.

**So the four records are NOT touched** —
`88d7543b2698 -> f2ee7be0d6da`, `8ae20da10239 -> 6a2690bec035`,
`e90d8775c7b2 -> d051c89faa16`, `f13f4f4982d3 -> 7ed27c5e78fa` — and **no
`34 -> 31` / `194 -> 193` / `25 -> 22` figure is reported**, because writing a
`superseded_by` key no reader honours would produce exactly the silent-no-op this
platform keeps paying for: the field present, the counts unchanged, and a
standing document claiming otherwise.

`tools/defect_register.py` is **declared in FILES by cc** in any case, so the
support is not mine to add.

**NEXT STEP:** when cc's support is on `origin/main`, apply the four
`superseded_by` values through the tool and report the three count deltas
measured, not predicted. The division of labour cc's own report sets — cc builds
the support, cody applies the field — is unchanged.

## item 3 — ROUTED, not applied. The premise is wrong in two ways and the tool cannot reach the record.

**(a) THE RECORD IS NOT IN THE DEFECT REGISTER.** Searching both ledgers for
`2026-10-06T22:18:54Z`:

```
docs/defect-density-register.json : 0 records
docs/tier-a-reviews.json          : 1 record
    author_session  'cody'
    opened_at       '2026-10-06T22:18:54Z'
    opened_at_sha   '4aa33b4565ddceeaac1081997f1d379d05b9de47'
    status          'reviewed'
    reviewer_owner  'cc'
    resources       ['quotes']
    files           ['tools/ledger_append.py']
```

It is a **Tier A review record**, and `opened_at_sha` is that ledger's field.

**(b) `4aa33b4565dd` DOES RESOLVE.** The item says it does not:

```
git cat-file -t 4aa33b4565dd                        -> rc 0   OBJECT PRESENT
git merge-base --is-ancestor 4aa33b4565dd origin/main -> rc 1
git merge-base --is-ancestor 4aa33b4565dd HEAD        -> rc 1
git branch -a --contains 4aa33b4565dd                -> 0 branches
```

The accurate statement is **resolves but is ORPHANED** — unreachable from any
ref, gc-eligible. That distinction is not pedantic: the gate's own output
separates *"the recorded sha is not in this clone's object store"* from a
reachability failure, and only the second applies here. Its subject is identical
to the survivor's, so it is the pre-rebase twin.

**(c) cc's RECOVERY IS CORRECT, and I verified it myself as instructed:**

```
git log --diff-filter=A --format='%H %ad %s' --date=short -- tools/ledger_append.py
  -> 27de70bee07a208ab6aa1c7e424ca65643d30719  2026-10-06
     feat(tools)+fix(bounds): five tools land with their inventory entries ...
git cat-file -t 27de70bee07a                           -> rc 0
git merge-base --is-ancestor 27de70bee07a origin/main   -> rc 0  ON-REF
```

**(d) AND THE TOOL CANNOT RE-SEAT IT — this is the real finding.** The item says
"re-seat through the tool only". The only reseat path is
`tier_a_review_gate.py --reseat-shas`, and its first line of work is:

```python
rows = [r for r in (data.get('records') or []) if r.get('status') == 'open']
```

My record's status is **`reviewed`**. Its dry run confirms the consequence —
**0 mentions** of `2026-10-06T22:18:54Z` in the whole report, while it names 22
open records, 10 already reachable, 1 reseatable, 3 weak and 8 refused with
reasons. So **a reviewed record whose sha is orphaned is permanently unfixable by
the tool**, and nothing says so.

**(e) AND THE FILE IS CC'S.** `docs/tier-a-reviews.json` is declared in cc's
FILES segment under the live 0.7h claim. Even with a working tool path this write
is not mine.

**ROUTED TO CC** with everything above: the record identity, the measured
orphan-not-missing distinction, the independently verified survivor
`27de70bee07a`, and the `status == 'open'` filter that excludes it.
**NEXT STEP, two parts:** cc re-seats the record, and the reseat path grows a
mode that can reach `reviewed` records — or refuses out loud that it cannot,
rather than omitting them silently.

## item 4 — DONE. Duplicate LEDGER arms removed; the unit arms stay. FIRST RUN EXIT 0.

```
command : python tests/run_tier_a_review_gate_probe.py
commit  : c2fcada9 + this change        date: 2026-10-08
FIRST RUN EXIT CODE : 0      (and a second run, also 0)
result  : ALL ARMS PASS, 230 ok
file    : 2,566 -> 2,412 lines
```

**REMOVED** — the ledger half, because `tests/run_tier_a_open_basis_probe.py` is
cc's and is the surviving probe for it: `BASIS_VOCAB`, `_basis_cutoff()`,
`_basis_violations()`, the cutoff arm, the every-record-since-the-fix arm, the
coverage NOTE, the exemption-counted-twice arm, the ledger-arm-bites arm, the
5-shape planted negative and the pre-cutoff arm. The now-unused `import calendar`
went with them.

**KEPT** — the six unit arms that belong beside this tool, three on `subject_sha()`
and three on what `_open_record()` writes:

```
ok  THE NEXT --open BY ANYBODY writes opened_at_sha_basis -- driven as a session that is not me
ok  ...and that record really was attributed to the other session
ok  ...and its fixture tree was removed, read-only objects and all
ok  NEGATIVE HALF: a record naming NO files gets basis 'head', so the field is derived
ok  ...and the two fixtures really did differ, so one code path is not satisfying both arms
ok  ...and that fixture tree was removed too
```

**ONE MISTAKE MADE AND CAUGHT IN THE SAME ITEM:** the first cut re-inserted the
`(B)` branch that was already inside the kept region, so the probe ran with those
three arms **twice** — 233 ok with visible duplicates at two line ranges. Caught
by reading the arm list rather than the total, which would have looked like more
coverage. Removed; 230 ok, no duplicates.

**A NOTE LEFT IN THE FILE WHERE THE ARMS WERE**, so the next reader finds the
reason rather than a gap: it names cc's probe as the survivor, says two copies of
one check is itself a finding on this platform, and records the one difference
that was routed rather than dropped — cc **pins** the cutoff by sha and guards the
pin; the removed version **derived** it with `git log --reverse -S 'def
subject_sha('`, which cannot go stale.

**This closes my half of the `--open` HEAD-stamping finding.** The fix landed at
`18078d38`, the unit arms live beside the tool, and the ledger rule lives in cc's
probe where it is exercised by real records.

## item 6 — DONE. A `RUNNING` status for a dead pid now reads **DEAD**. Fixture-locked.

```
command : python tools/capture_exit.py --fixtures
commit  : 15b611c1 + this change        date: 2026-10-08
FIRST RUN EXIT 0, and a second run 0.  0 FAIL.
criteria lock: 33 arms, 12 of them negative, 6 through the CLI
               (criteria 2026-10-07.3 -> 2026-10-08.1, bumped because the
                criteria really changed)
```

**PROVED AGAINST THE REAL CASE, not only a fixture.** Batch 24's killed run left
this on disk and `--read` reported it as RUNNING for hours:

```
RUNNING 74488 2026-10-07T19:27:29Z python tools/run_all_tests.py --pinned --out ...
```

Now:

```
python tools/capture_exit.py --read <SCRATCH>/b24/i3/suite.status   -> EXIT 2
DEAD  74488 2026-10-07T19:27:29Z python tools/run_all_tests.py --pinned --out ...
  the writer is GONE: this run ENDED WITHOUT RECORDING AN OUTCOME, so there is
  no verdict and there never will be.
  Do not wait on it. Re-run, and treat the partial output as a partial.
```

And the **live** batch-25 run, read in the same minute, still prints
`RUNNING  87256 …` — so the change distinguishes the two rather than relabelling
everything.

**THREE STATES, NOT TWO.** `pid_alive()` returns True / False / **None**, and
`read_status()` maps them to `RUNNING` / `DEAD` / `COULD-NOT-TELL-PID`. None of
the three is `EXIT` and none exits 0. A `RUNNING` line whose pid will not parse is
`UNREADABLE`, not RUNNING.

**`os.kill(pid, 0)` IS NOT USED ON WINDOWS AND THE COMMENT SAYS WHY.** There,
`os.kill` calls `TerminateProcess` — a liveness check that kills what it asks
about; `run_all_tests.py` already records that trap for its own lock staleness.
This uses `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` plus
`GetExitCodeProcess`, which can only read, and falls back to the correct POSIX
`os.kill(pid, 0)` off Windows.

**THE ARM THAT WAS THERE BEFORE WAS PASSING FOR THE WRONG REASON, and it was
replaced rather than kept.** It planted **pid 999** and asserted `RUNNING` — 999
is almost certainly not a live process, so that arm was asserting that a status
for a *dead* writer reads as RUNNING. The two statements cannot both be true.

**THE PLANTED DEAD PID IS DEAD BY CONSTRUCTION**, not by being an unlikely
number: the fixture spawns `python -c pass`, waits for it, and reuses its pid — a
number that provably existed and provably does not now, which is the real shape
of a killed run. Beside it, a pid that is alive by construction (the interpreter's
own), so the DEAD arm cannot be satisfied by a checker that answers False to
everything.

**AND THE CLI, SEPARATELY**, because this file's own comment says a strong lock
over one half of a tool says nothing about the other half — the previous `--read`
bug was exactly that. Two more arms: `--read` on a DEAD status exits 2 and prints
`DEAD`, and the word `RUNNING` appears **nowhere** in that output.

**STATED LIMIT, in the code as well as here:** a **recycled** pid reads as alive.
Windows reuses pid numbers, so a status whose writer died and whose number was
handed to something else still reports RUNNING. Closing that needs the process
start time compared against the status timestamp, which this does not do. So
**DEAD is sound and RUNNING means "alive or recycled"** — the asymmetry is
deliberate, because a false DEAD would be worse than a late RUNNING.

## item 7 — DONE. `--pinned` now KEEPS the clone when the post-run tree read fails. Fixture-locked.

```
command : python tools/run_all_tests.py --selftest
commit  : 77366afe + this change        date: 2026-10-08
FIRST RUN EXIT 0 after the arm below was fixed; two further runs 0. 0 FAIL.
criteria lock: 18 arms, 5 of them negative (2026-10-07.1 -> 2026-10-08.1)
```

**THE COST THIS PAYS BACK, measured 2026-10-07.** A run ended
`EXIT 2 -- COULD NOT RUN: the clone was broken during this run`, on
`git status exited 3221225794` = `0xC0000142` — a process that failed to
*initialise*, i.e. git could not be **launched**. Whether the clone was really
broken or git merely could not start was answerable **in that directory and
nowhere else**, and the cleanup had already deleted it. Item 4 of batch 24 had to
report the cause as **UNKNOWN** for want of evidence this tool destroyed on its
way out.

**HOW IT SIGNALS: a marker file, not a phrase in stdout.** The inner run writes
`.sairn-tree-unreadable` when `unreadable_tree` is true; the wrapper's cleanup
reads it. The two halves are one tool but **separate processes**, and a text
contract between them is one rewording away from silently keeping nothing.

**KEPT FOR THAT ONE CAUSE ONLY.** A clean run, a red run and every other
COULD-NOT-RUN still clean up. Keeping 215 MB per run would get the behaviour
switched off, and 29 abandoned directories is the failure in the other direction.

**THE WRITE IS GUARDED BY `SAIRN_PINNED_RUN`**, because on an ordinary run `REPO`
*is* the developer's clone and dropping an untracked file into it would be
residue of exactly the kind the guard exists to report.

**`_drop_pinned_clone()` RETURNS `'KEPT'` OR `'REMOVED'`** so the fixture can
assert *which branch ran* rather than inferring it from whether a directory
exists — an existing directory is also what a failed delete looks like.

**EIGHT ARMS, and one of them failed twice before it was right:**

```
ok  THE PINNED CLONE IS **KEPT** WHEN THE TREE READ FAILED
ok  ...and it PRINTS THE PATH, so the evidence is findable rather than merely undeleted
ok  NEGATIVE: with NO marker the clone is still REMOVED
ok  ...and the two branches really differ, so one is not satisfying both arms
ok  the keep-marker is a named constant, not a literal spelled twice
ok  the marker is only WRITTEN under SAIRN_PINNED_RUN -- bounded 400-char window
ok  ...and the window has a DIRECTION: not in the 400 chars BEFORE the guard
ok  AND THE LIVE CLONE CARRIES NO MARKER RIGHT NOW -- the behavioural half
```

**THE TWO FAILURES ARE THE USEFUL PART.** The guard-position arm first compared
`_src.index(guard)` with `_src.index(write)` — and **the fixture a few lines
above writes the marker too**, so `index` found the fixture's write and the
comparison was between two unrelated positions. Rewritten as a bounded window, it
failed *again*: the arm spelled the guard out as a literal, so **that line became
a second occurrence of its own subject** and `find` landed on the arm instead of
the guard, 100 lines early. The needle is now assembled at run time from
`chr(39)`, the guard is asserted to occur **exactly once**, and the window is
asserted to have a **direction**. A source-reading arm that contains its own
subject measures the wrong file position — which is a defect shape already in my
own notes, committed again anyway.

## item 5 — DONE as a launch; the run **COMPLETED**. EXIT 1, 86 failures. NOT a clean pass.

**The detached launch worked.** Three batches tried to get a `--pinned` run to
finish; this is the first that did. Nothing killed it.

```
command : powershell Start-Process python tools/capture_exit.py --status <D>/suite.status
          -- python tools/run_all_tests.py --pinned --out <D>/suite.out
commit  : aa2f014dd21b088711944b5675104471c43b0502   (meta.txt, stamped at launch)
START   : 2026-10-08T00:08:09Z     EXIT at 2026-10-08T03:21:50Z     3h 13m 41s
RUNS AT THIS SHA : 1.   FIRST RUN RETURNED: **EXIT 1**.
```

```
RAN: 351 JS + 408 PY = 759 files (1 skipped)
671 ok        86 FAIL        86 FAILING TEST FILE(S)
EXIT 1 -- FAILURES ABOVE
```

**`EXIT 1` IS A COMPLETED RED RUN, NOT A VOID ONE** — and that distinction is the
point of the last two batches. `EXIT 2` would be COULD-NOT-RUN; the status file
says `EXIT 1`, the `RAN:` summary printed, and the clone was cleaned up normally
because the post-run tree read **succeeded**. So these 86 are a real verdict.

**NO CLEAN PASS, SO NOTHING IS CLEARED.** The firebase andon needs a clean
completed pass. 86 failures is not that. **ANDON HELD** — on a measurement this
time rather than on a void run.

**ONE RESIDUE PATH, AND IT BOUNDS HOW MUCH OF THE 86 IS BELIEVABLE:**

```
THE SUITE DIRTIED THE TREE (1 path(s)) -- a probe did not clean up:
     M docs/report-only-reachability.json
```

The runner's own warning applies: a modified tracked file fails every clean-tree
probe after it, so some of the 86 may be **cascade** rather than real. **2 of the
86 carry `FAILED TWICE`** — the runner re-ran them alone and they failed again,
which is the only subset proven real without further work.

**NEXT STEP:** restore `docs/report-only-reachability.json`, then re-run the 86
individually and split real from cascade. Do not quote 86 as a defect count.

### AND THE WATCHER BESIDE IT WAS **BLIND FOR 3h13m AND LOOKED LIKE IT WAS WORKING**

```
command : scratchpad/b25/analyse_times.py over child_times.txt.live
samples parsed        : 14,976
samples with EMPTY cmd: 14,976  (100%)
distinct subjects     : 6   -- pids 0, 4, 236, 276, 1000, 4416
distinct REAL test files observed : 0
```

Its summary file reported *"6 distinct children, longest 11635s TIMEOUT"*, which
**reads like a finding** and is an artefact of watching the kernel.

**ROOT CAUSE, found and fixed.** It invoked
`powershell -NoProfile -Command <script> -root <pid>`, and with `-Command` the
trailing arguments are **not bound to a `param()` block**. `$root` was `$null`,
the filter became `ParentProcessId=` and matched the few processes whose parent
is 0. The pid never reached the script.

**FIXED AND PROVED, not asserted:** the pid is now interpolated into the script
text, and the watcher **refuses** (`SystemExit`) if the placeholder is still
present rather than watching pid 0. Driven against a parent with a known named
child:

```
samples naming the child  : 1 of 3
2026-10-08T07:40:03Z  pid 33452  C:\Python314\python.exe tests/run_tier_a_review_gate_probe.py
VERDICT: the watcher now sees the real child
```

**THE b24 APPEND-AS-YOU-GO FIX IS WHY THIS WAS DIAGNOSABLE AT ALL.** The summary
was written at the end and was misleading; the 382 KB live log was written per
sample and is what proved the watcher saw nothing. A fix made for crash-safety
turned out to be what made the instrument auditable.

**So the 35-minute-file question is STILL open**, and for a new reason: the run
completed, but the instrument measuring it was pointed at the wrong process tree.
The 900 s / 14,400 s bound stays **UNSET**.

## item 8 — DONE. 6 of 6 mine, and **36 of 36** not-mine. 0 refused, 0 held.

```
command : scratchpad/b25/apply_onerror.py, then apply_onerror_36.py
commit  : fd41b8cc (the six) and this change (the 36)        date: 2026-10-08
```

### The six genuine sites of mine

```
tests/claims/run_freshness_probe.py:536            rmtree(tmp,     onerror=_rm_ro)
tests/push_gate/redaction_base_probe.py:200        rmtree(tmp,     onerror=_rm_ro)
tests/push_gate/refspec_and_override_probe.py:219  rmtree(_sand,   onerror=_rm_ro)
tests/push_gate/refspec_and_override_probe.py:453  rmtree(sandbox, onerror=_rm_ro)
tests/run_bare_run_write_probe.py:267              rmtree(d,       onerror=_rm_ro)
tools/clone_health_check.py:399                    rmtree(base,    onerror=_rm_ro)
```

**Each verified after patching, every code from its own `.status` file or
measured alone:** `run_freshness_probe` **0**, `redaction_base_probe` **0**,
`refspec_and_override_probe` **0**, `run_bare_run_write_probe` **0**,
`clone_health_check --fixtures` **0** with 11 arms and 0 FAIL.

**AND ONE OF MY OWN INVOCATIONS WAS WRONG, recorded rather than quietly
corrected:** I first ran `clone_health_check.py --selftest` and got **EXIT 2**.
That file takes `--fixtures`. The pre-patch version from `git show` returns the
identical **EXIT 2**, so it is an argument error of mine and not a regression —
and it is the unknown-flag-exits-2 behaviour working as designed.

**DELIBERATELY NOT TOUCHED:** `tools/clone_health_check.py:328` removes a
**linked worktree** directory, measured to carry 0 read-only files, and the very
next line is an arm asserting it is gone. Not in the class, guarded either way,
and changing it would be an edit to working code to satisfy a pattern.

### The 36 not mine — all 25 files were FREE

```
command : python tools/sairn_claim.py list (the registry, not a claim-file read)
          plus the FILES segment of every live claim
date    : 2026-10-08T07:5xZ
FREE : 25 of 25     HELD : 0 of 25
```

**X OF 36: patched 36, refused 0, held 0, routed 0.** 25 of 25 compile clean.

**ANCHORED BY LINE NUMBER, NOT BY A STRING, and that mattered:**
`tests/run_fail_open_probe.py` holds **12** of the 36 and several share the
identical call text, so a string anchor there is not unique and a replace-all
would have hit sites the ordered predicate deliberately excluded. Each site was
addressed as `(file, line)` from the b24 sweep, the line **re-read** and required
to contain both `rmtree(` and `ignore_errors=True`, and sites patched
**bottom-up** per file so the helper insertion could not shift them. A site that
no longer matched would have been **REFUSED and printed**; none was.

The 1–2 remaining `ignore_errors=True` per file are the **out-of-class** sites —
pre-create deletes and worktree removals — and they stay, which is the point of
the ordered predicate.

**SAMPLE RUN, 6 of the 25, stated as a sample:**

| probe | exit |
|---|---|
| `run_fail_open_probe.py` (the 12-site file) | **0** |
| `conflict_marker_preflight_probe.py` | **0** |
| `run_semgrep_encoding_probe.py` | **0** |
| `run_worktree_root_home_repo_probe.py` | **0** |
| `sairnvet_fault_probe.py` | **0** |
| `run_harness_stage_diagnosis_probe.py` | **1** |

**THAT EXIT 1 IS PRE-EXISTING AND PROVED SO, NOT ASSUMED.** It appears in the
completed suite run at `suite.out:757` — `FAIL py
tests/run_harness_stage_diagnosis_probe.py  1 failure(s)` — and that run was at
`aa2f014d`, which **predates this patch**. It is one of the 86.

**WHY A BLANKET APPLICATION IS DEFENSIBLE HERE, and it was argued in the claim
before it was done:** `ignore_errors=True` and `onerror=<swallowing retry>` have
**identical observable behaviour** except that the retry clears the read-only bit
first. No input exists on which the patch makes a correct call worse, so it needs
no per-site behaviour judgement — only the ordered predicate to decide where it
is worth applying.

## item 9 — DONE. Four stale artifacts gone, `.git/config` byte-identical.

```
command : scratchpad/b25/clean_artifacts.py
commit  : this change        date: 2026-10-08
```

**Liveness checked first**, excluding my own query shells:
`non-shell processes referencing a pinned dir: 0`.

```
sairn-suite-pinned-6j2r6zlt        0 files -> gone, 0 left
sairn-suite-pinned-ez_wtgtg        0 files -> gone, 0 left
sairn-suite-pinned-vnw7na2m    3,275 files -> gone, 0 left   (109 MB)
newchk-27740   worktree unlock rc 0, worktree remove --force rc 0, prune rc 0
```

**FORCE TWICE, as the item says, and the two steps do different things:**
`unlock` clears the `initializing` lock the interrupted `worktree add` left
behind; `remove --force` then drops the registration and the directory. Either
alone would have failed.

**THE PROOF THAT MATTERS:**

```
BEFORE  .git/config sha256 93070fe59db24a5bdcf7aca3bc619fd5bd14247986522ad8f624aeceb108ad98   core.bare false
AFTER   .git/config sha256 93070fe59db24a5bdcf7aca3bc619fd5bd14247986522ad8f624aeceb108ad98   core.bare false
CONFIG UNCHANGED  True
worktree registrations now: just this clone
```

That file is the one a worktree operation can reach, and a `core.bare` flip in it
is what broke this clone on 2026-10-07 — which is why the hash is the evidence
rather than the absence of a complaint.
