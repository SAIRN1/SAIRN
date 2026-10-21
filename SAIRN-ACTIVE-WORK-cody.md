# SAIRN Active Work — Cody

Per-session active-work log for the **Cody** session (`Documents\SAIRN-cody`).
Split out of the shared `SAIRN-ACTIVE-WORK.md` on 2026-08-24 because four
concurrent sessions appending to one file produced repeated merge conflicts
in a single night. Each session now appends only to its own file, so two
sessions can never collide on the same lines.

**Append your entries here, not to `SAIRN-ACTIVE-WORK.md`.**

The four sessions and their files — one row each, all equal, no special case:

| Session | Clone | File |
|---|---|---|
| Hank | `Documents\SAIRN-hank` | `SAIRN-ACTIVE-WORK-hank.md` |
| CC | `Documents\SAIRN-cc` | `SAIRN-ACTIVE-WORK-cc.md` |
| Cody | `Documents\SAIRN-cody` | `SAIRN-ACTIVE-WORK-cody.md` ← this file |
| Fourth | `Documents\SAIRN-fourth` | `SAIRN-ACTIVE-WORK-fourth.md` |

Still read the other three (`SAIRN-ACTIVE-WORK-hank.md`, `SAIRN-ACTIVE-WORK-cc.md`, `SAIRN-ACTIVE-WORK-fourth.md`) before starting anything —
the point of the shared file was to avoid two sessions touching the same app
file at once, and that reason has not gone away. Splitting the file removes
the write collision, not the need to check.

One line per task: app/file(s) touched, a one-line task description,
timestamp. Add a line before starting anything new.

Entries below were moved verbatim from the shared file (nothing reworded,
nothing summarized), in their original order. Cross-session context that
predates the split — including the `cc-work` worktree correction — stays in
`SAIRN-ACTIVE-WORK.md`.

---

> **SPLIT 2026-10-20 (cody b30 item 3).** This file was 795,238 bytes
> against a 400,000-byte ceiling, listed by
> `python tools/tooling_inventory.py --standing-doc-sizes` since b28.
>
> **The 88 oldest entries -- the ones in the original bullet format -- are
> now in `SAIRN-ACTIVE-WORK-cody-closed-1.md` and `-closed-2.md`.** They were moved whole and
> verified by an entry-multiset sha256 taken before the split and re-taken
> from disk afterwards; nothing was summarised and nothing was deleted.
>
> **This file keeps all 127 dated `## ` sections**, which is the recent work a
> fresh session needs. The archive parts are ARCHIVES: if an entry in one
> turns out to be live, MOVE it back rather than copying it.

## 2026-09-09 (Cody) -- the probe that kept stripping sairnvet.html's corrupt-store guard

RELEASED: reachability-probe-restore-failure. Root cause found, fixed, pushed
as `5b8570ce`.

**The trigger was CONCURRENCY, not a missing `finally`.** Probes under `tests/`
mutate a real tracked file and restore the bytes THEY read at their own start.
Nothing serialised the runs, and `tools/run_all_tests.py --hook` fires on every
`git push`, async. Observed alive in one tree on 2026-09-09: THREE concurrent
`--hook` runs (09:05:38, 09:06:06, 09:06:21) plus two copies of
`tests/seam_check/run_probe.py` started in the same second.

    run A snapshots the clean file, mutates it
    run B snapshots THE MUTATED FILE as its "original"
    run A restores clean
    run B restores the mutation -- and it stays on disk

Both runs restored exactly what they read. **The snapshot was the defect, not
the restore**, which is why "make it restore reliably" was the wrong shape of
fix and why Hank's 2026-09-08 observation (three files dirtied, five probes
red) was never reproducible with an instrumented SEQUENTIAL run.

**Caught in the act mid-session:** backfill control 1 ("a full disk goes back
to being silent") was found live on disk in `sairnvet.html` while this was
being written. Restored with a targeted `git checkout --`.

**Fix, two parts, because neither covers the other's case:**
- `tools/run_all_tests.py` takes a per-clone lock; a second run declines and
  says so. Lockfile lives in the temp dir -- an untracked one inside REPO
  would show as `??` and make every clean-tree probe skip. Stale by AGE, not
  pid: `os.kill(pid, 0)` on Windows does not test liveness, it calls
  TerminateProcess.
- `suite_control_backfill_probe.py` and `reachability/live_mode_probe.py`
  refuse to snapshot an ALREADY-DIRTY target (exit 3). This is the half the
  lock cannot see -- a process killed before its `finally`.

`tests/run_suite_lock_probe.py` is the control, 19 checks, both directions.

**Verified, not assumed:** 19/19 green; `live_mode_probe` still reports LIVE
MODE VERIFIED on a clean file; the backfill probe still GREEN with every
control BITING and all five app files restored byte-identical; `sairnvet.html`
and `tools/reachability_exemptions.json` confirmed clean on `origin/main`
after the push.

**NOT mine, claimed by `fourth`:** a probe COMMIT is residue no per-file
restore can undo. `check7_probe`'s fixture reached origin as `b909dbee`
(reverted in `86bf4b68`). The lock narrows that window; it does not close it.

**Standing lesson worth more than the fix:** a probe that snapshots the
working tree is only correct while it owns the working tree. Every
save-mutate-restore harness in this repo assumes exclusivity nobody granted
it, and the failure is silent in both directions -- the backfill probe printed
`restored byte-identical: True` the entire time the guard was missing, because
it was telling the truth about the wrong baseline.

### Follow-up the same day: the other five probes, and two more stranded mutations

`grep`ping the repo for the same defective shape found FIVE more probes that
snapshot the working tree with no baseline check -- `seam_check/run_probe.py`,
`seam_check/run_delegation_probe.py`, `seam_check/run_or_default_probe.py`,
`sairndental_write_failure_probe.py`, `sd_timesheet_pay_est_probe.py`. All five
now refuse a dirty target and exit 3. Two of them were bare `assert`s, exiting
1, which reads as "the seam check is broken" -- the same signal defect already
fixed in `check4_probe`.

`tests/run_suite_lock_probe.py` now drives **all seven** in a throwaway
`git worktree` (~2s), which is what makes it safe to dirty `stonedesk.html` and
`sairndental.html` at all. 40 checks, 0 failed.

**Two stranded `api/sd-data.js` mutations were found on disk during this**, both
`warn_days: gateWarn` deleted from the `canAssign` call site (delegation-probe
arm 1), both with the probe process already gone. The kill case is real and
frequent, not theoretical.

**Fourth's correction is right and I should record that I did not always meet
it:** DURING a run and AFTER an interrupted one look identical in `git status`.
I checked for a live process before restoring `api/sd-data.js`. I did NOT check
before restoring `sairnvet.html` earlier in the session -- that restore may have
clobbered a live probe mid-run. It did no harm (the probe rewrites its own
baseline), but the discipline is: check for a running python process first.

**Also noted, not fixed:** something is running probes against this clone that
does not go through `tools/run_all_tests.py` -- the lockfile was verifiably
absent while probes were mutating this tree, and the lock is proven to be taken
in hook mode. So the lock does not cover every path into these probes. The
per-probe dirty guard does, which is why both halves shipped.
## 2026-09-09 (Cody) -- the tooling inventory, and what runs nothing

CLAIMED and now released: `tooling-inventory`. Written up in
`docs/2026-09-09-tooling-inventory.md`. **Every count is derived** from
`.claude/settings.json`, `.githooks/pre-push`, `tools/sairn_push_gate_hook.py`
and `git ls-files` -- not read off any earlier document, and the doc carries a
*How to re-derive this* section so the next session redoes it rather than
trusting it.

**77 files in `tools/`:** 10 BLOCKING, 3 report-only, 2 advisory,
29 library/generator, **33 unwired -- 28 of them working checkers nobody runs.**

**The finding I would act on first:** nine of those 28 have a purpose-built
probe under `tests/` that `run_all_tests.py` executes on every push. The suite
proves the checker WORKS, on fixtures, while nothing ever runs it against the
real code. A green probe on an unwired checker reads as coverage and is
coverage of the tool, not of the codebase.

**Three unwired checkers are named as REQUIRED by Guardian v2 or CLAUDE.md**
and are not wired: `sairn_dead_button_audit.py` (Guardian check 27),
`nav_panel_check.py` (checks 16-18; the safe-editing rules say after EVERY
edit), `vercel_config_check.py` (whose own note says the failure it catches
takes production down while looking like nothing happened).
`div_balance_check.py` is in the same sentence as `nav_panel_check.py`.
Four rules that depend on remembering, in a repo whose recurring lesson is
that those are the failure mode.

**Deliberately NOT a recommendation to wire all 28.** Four are live network
probes needing a real licence and are correctly manual; several are one-off
audits. The decision each needs is blocking / report-only / deliberately
manual, recorded once instead of left unanswered by default. **That decision
is Michael's.**

**Skill-list audit re-derived the same day -- every claim still holds:** 60 on
disk, 32 SAIRN mirrored with **0 real content differences** and exactly 12
CRLF-only, 28 general-only, `security-auditor` absent from both stores,
`grill-me` present with `disable-model-invocation: true`, `sairn-code-guardian`
in neither store.

### Item 1 (probes running outside run_all_tests) -- ANSWERED BY HANK, not me

`4cbbcf23`. `.claude/settings.json` gated both Bash PostToolUse hooks with an
`"if"` key. **A hook entry has no `if` field** -- its only gate is `matcher`,
which matches the TOOL NAME -- so the unknown key was ignored in silence and
the full mutating suite ran after **every Bash tool call**. That is the volume
I could not explain and logged as an open observation. I pulled the fix rather
than duplicating the work; the churn stopped immediately.

**One thing that happened while I was working, worth recording as a class:** a
probe's `git reset --mixed <its own start>` REWOUND a completed rebase in this
clone, leaving Hank's just-pulled commits as uncommitted working-tree
modifications. Nothing was lost -- every byte was verified identical to
`origin/main` before recovering -- but a session that ran `git checkout -- .`
on that state, or committed it, would have made a real mess. **A probe that
resets HEAD is dangerous to more than its own files.**

### 2026-09-09 (Cody) -- StoneDesk timesheet AI panel: told what it cannot price

CLAIMED and released: `stonedesk-timesheet-ai-labour-cost-disclosure`. Picked as
the next real gap after the inventory: unassigned, sized S, and I had fresh
context on exactly this code from verifying `sd_timesheet_pay_est_probe.py`
earlier the same session.

`sdTSAI()` was the ONE consumer of `sd_timesheets` that did not go through
`tsRate`/`tsPay`. It posted the RAW rows and asked for "Estimated labor cost
efficiency", so an unrated row arrived as bare hours plus whatever was in
`rate`, and the answer carried no exclusion note. Same defect as the "$0 total
over all-`--` rows" one layer out -- **in prose rather than in a cell, which is
where it is hardest to see.**

Fixed with two NAMED, 2-space-indented helpers so the test can EXTRACT AND
DRIVE them, the same reason `tsCell()` is named. That mattered here: the fetch
needs a network, so a source assertion was otherwise the only possible cover,
and this suite has already caught one of those passing a mutation that had
removed the behaviour.

- `tsAIRows()` -- `rate:tsRate(x)`, `pay_est:tsPay(x)`, both null where the row
  cannot be priced. **Sending the raw `rate` handed a string `"28"` straight to
  the model, exactly the coercion `tsRate()` refuses.** `0` survives as `0`.
- `tsAIScope()` -- states the counts, says null means UNKNOWN NOT ZERO, tells
  the model not to estimate a rate for excluded rows. Three cases: a clean
  period must not carry an exclusion warning, an empty one must not be analysed.

**Verified:** checkblocks 130/0, duplicate-global clean, 27/27 suite assertions
(6 new), and ALL 12 mutation controls BITE (10-12 are new and guard precisely
the two source assertions) with `stonedesk.html` restored byte-identical.

**Two workflow notes from today, both worth keeping:**

1. **The probe now refuses a dirty tree**, so it cannot be run against
   uncommitted work. Order is **commit locally -> probe -> push**. That is a
   real cost of this morning's fix and it is the right trade: the alternative
   is a probe that snapshots your uncommitted work and hands it back as
   "restored byte-identical".
2. **`tools/md_table_check.py` caught me editing an index row by parts.** I
   replaced the leading cells and left the original tail, producing a 12-cell
   row against a 9-cell header -- the exact failure CLAUDE.md added that tool
   for, committed by the session that had just written a document about
   unwired checkers. **It is one of the 28 unwired checkers and I only ran it
   because I had just inventoried it.** Rebuilt the row whole. That is the
   strongest argument in the inventory, and I did not have to look for it.
## 2026-09-09 (Cody) -- the report-only promotion path, and three checkers wired

CLAIMED and released: `report-only-hook-mechanism`. **Scoped deliberately around
CC**, who holds `unwired-checkers-run-against-real-code` and is editing
`write_without_readback_check.py`, `sairn_app_map_check.py` and the guardian
skill. Michael's call was option (b): CC keeps those, I take the mechanism plus
the three I had already tested. No overlap.

`tools/report_only_checks.py` -- **one runner with a REGISTRY, not 28 hook
entries.** Promoting the next checker is a registry entry carrying when it was
promoted, what it catches, why it matters, and **the evidence from its real
run**. Twenty-eight hook entries would be twenty-eight places to keep in step
and twenty-eight chances to repeat the `"if": "Bash(git push*)"` mistake.

**Three promoted, each with its real run recorded:**

| Checker | Real run | Note |
|---|---|---|
| `vercel_config_check.py` | PASS, buildCommand 92/256 | clean first time |
| `sairn_dead_button_audit.py` | A=0 B=0 C2=0 over 22 apps; D1=1 | **it ALWAYS EXITS 0** -- it cannot be wired by exit code, which is a fair part of why it sat unwired while Guardian check 27 named it as required |
| `nav_panel_check.py` | 22 PASS / 0 FAIL **after a fix** | see below |

**`nav_panel_check.py` was broken and I did not promote it broken.** Its first
real run reported **all 26 sairnfreedom panels unreachable** -- it scanned
`<button>` and that app navigates with
`<div class="nitem" onclick="sfNav('x')">`. Blocking, it would have refused
every SAIRNfreedom push while the app was fine. That is the **fourth** instance
of that file's own recurring bug; it had already stopped hardcoding the class,
the id and the function name, and the element was the last assumption left.

**The widening is MEASURED, because trading a false alarm for a silent miss is
the easy mistake here.** My first widened pattern matched the JS comparison
`if(days<TRIAL_DAYS)return true;` as an opening tag, ran `[^>]*` across a dozen
lines, and swallowed a real nav call -- a phantom control on sairnvet and
sairnlegacy. Tightened (an HTML tag name cannot contain `_`), then **both**
patterns run over all 22 app files: the tight one loses exactly those two
phantoms and **not one real control**. The probe drives it in both directions
on synthetic fixtures -- a div-navigated app must pass, **a genuinely
unreachable panel must still FAIL**, and a JS `<` must not count as an element.

**A second finding came from wiring it, not from looking for it.** My first
`app_files()` was a bare `git ls-files '*.html'` and swept
`archive/branch-lucid-ptolemy-b73vu0/` -- the preserved ancestor branch
CLAUDE.md says explicitly must not be run. 13 findings, 12 of them in code
nobody deploys. That is precisely how a report-only checker earns the
reputation that gets it switched off before it is ever promoted. Top-level only
now (vercel.json routes every app from the repo root) and **the exclusion is
printed**, not silent.

**One real defect fixed:** `sairnmechanical.html` carried two `mechEsc`
declarations in one script block (`94034ed1`). The later hoisted over the
earlier, so the first had never run. Proven equivalent over ten inputs before
anything was touched -- it is an HTML escaper and Guardian 25 is not a place to
reason from "they look the same". Live-verified: 1 definition, 27 references,
200.

**Verified:** 29/29 probe checks, full sweep CLEAN across three checkers, and
Hank's `run_all_tests_hook_gate_probe.py` still ALL PASS -- which is what
proves my new hook entry carries no unrecognised key either.

**Deliberately no lock** on this runner: `run_all_tests.py` needs one because
its probes MUTATE, and every checker here is read-only. If a mutating tool ever
joins the registry that reasoning stops holding, and the file says so.

**25 checkers still unwired.** CC holds the ones they are editing.
## 2026-09-10 (Cody) -- a cleanup file that cannot answer "did it run?"

CLAIMED and released: `cleanup-sql-confirm-query-convention`.
`tools/cleanup_confirm_check.py` + `tests/run_cleanup_confirm_probe.py`
(`f1af957d`), promoted as the fourth checker in the report-only registry.

**The rule existed since 2026-08-26 and nothing enforced it.** Two files had no
confirm query of any kind -- `sairndesign_synctest_cleanup.sql` and
`sairnlegacy_synctest_cleanup.sql`, three live deletes each. Both now carry a
per-statement confirm with the expected answer **and a control**, because three
zeroes prove nothing if the rows were never reachable by that predicate.

**What it cannot do, and its header says so: it cannot tell you whether a file
was RUN.** Nothing in this repo can. What it tells you is whether the file could
ever answer that.

**The matcher is calibrated against hand-reading, not guessed.** My first
version called **17 of 26** files non-compliant. I read three; **two were false
positives** -- an expectation written mid-sentence, and a `select` with its
`count(*)` on the next line. Rebuilt: multi-line, counts a confirm inside a `--`
comment (that is how every compliant file here ships one), separates a COMMENTED
statement from a live one, and accepts verification through the live endpoint,
which CLAUDE.md **prefers** over a re-select. Two more false positives died and
became fixtures. **4 flags became 2, both hand-read, both real.**

### Two things that went wrong on my side, recorded rather than smoothed over

1. **I pushed a `PROBE seam violation` commit to origin/main.** A probe left it
   on HEAD between my `git log` and my `git push -q`, and the quiet push carried
   it. It deleted `service_methods: body.service_methods` from
   `api/legal-deadlines.js` -- **the exact field whose absence made SAIRNlaw
   compute Florida deadlines five days late.** Another session (`c7295822`) had
   already reverted it by the time I built a worktree to do it myself, so I
   stood down rather than duplicate. **The lesson is mine: never `push -q`. Read
   `git log --oneline -1` immediately before pushing, and treat a `PROBE`
   subject as a stop.**
2. **I created a git worktree inside the repo** because `$TMPDIR` was empty in
   that shell and the relative path resolved into the clone. A registered
   worktree is invisible to `git status`, so it left no trace to notice.
   Removed. **Use an absolute path outside the clone.**

**The worktree technique itself is the right answer to the churn** and is worth
keeping: with probes constantly dirtying this tree, `git rebase` refuses and a
push cannot land. Cherry-picking onto a detached worktree at `origin/main` and
pushing from there is race-proof and does not touch the working tree at all.

**Also corrected: a stale index row nearly cost a duplicate build.** I claimed
`sairnbiz sb_incidents` off the index, then found Hank had already closed the
display half in `37e409e2` with a 10/10 test. Released the claim immediately.
The row had been updated on origin between my read and my claim.
## 2026-09-10 (Cody) -- the human read on two C1s, and what it actually found

CLAIMED and released: `sairnmechanical toast-only buttons human read`.

**The read came back CLEAN, and that is the correct result.** `syncAll()` and
`mechNotLive()` are DELIBERATE honest refusals built on 2026-09-03 with the
reasoning in the file -- "Cross-app sync is not enabled for SAIRNmechanical yet
-- nothing was sent" and the eight silent controls that used to swallow a click
entirely. **"Wire this up" would have turned an honest refusal into a
fabricated feature**, which is the opposite of the fix. Recorded so the next
reader of a C1 count does not do that.

**The real finding was in the checker, not the app** -- and it is the SILENT
direction of `nav_panel_check.py`'s own recurring bug. That file has now stopped
hardcoding the class, the id, the nav-function name and the element, four
corrections, every one after it reported a WORKING app as broken. The fifth
failed the other way:

    sairnmechanical.html   17 containers id="page-x", showPage()  -> PASS
    stonedesk-hr.html      15 containers id="page-x", showPage()  -> PASS

**32 real containers invisible, reported as clean, by a checker I had promoted
to the registry that same morning.**

**Four defects, each one only findable after the one before it was fixed:**

1. `page-` containers unrecognised at all.
2. My first fix adopted only the `page-` ids something CALLS by name. **That is
   self-defeating** -- an unreachable container is by definition one nothing
   calls -- and it made sairnmechanical pass with 16 of 17 panels by dropping
   the unreachable one. The ≥2 test now decides whether the FILE navigates by
   `page-`; if it does, every `page-` container is in scope.
3. `nav_call_re` demanded the closing paren immediately after the quoted
   argument, so `showPage('dashboard', this)` was invisible and stonedesk-hr's
   fifteen working sidebar items counted as **zero**. **This was hidden BEHIND
   defect 1**: with no containers found, the file passed vacuously either way.
4. `resolve_panel` could not map a bare nav argument onto a camelCase id.

**"Could not tell" is no longer a pass.** No containers plus a nav function
called from ≥2 element handlers now exits **3 SKIPPED**, and the registry routes
exit 3 to "could not run". A genuinely single-purpose page has no nav system and
still passes, so the notice stays rare rather than firing every push.

**One true finding, already known and now suppressed WITH DISCLOSURE:**
`page-sairnbiz-connector`. Every suppression is printed on the run.

### Two corrections against myself

- **A probe arm I wrote asserted the OPPOSITE of the final design.** It said app
  SHELL containers must not be adopted -- written while the tool was wrongly
  reporting SAIRNcash's `homePage`/`appPage` as unreachable. Wrong diagnosis:
  those two ARE navigated, and the real defect was 4 above. Refusing to adopt
  would have been **a silent miss dressed up as a fix**. Rewritten in place with
  that reasoning rather than quietly deleted.
- **My earlier claim that the tightened tag pattern "loses not one real
  control" was true of the counts I compared and blind here.** stonedesk-hr's
  fifteen controls were already invisible for a different reason, so the
  comparison could not have shown a loss. A measurement is only as wide as what
  it could have seen.

### The push path, since the churn makes this recurring

`git rebase` refuses while probes dirty the tree, so pushes cannot land. Cherry-
picking onto a **detached worktree at `origin/main`** and pushing from there
touches no file in the clone and cannot be raced. `scratchpad/wtpush.sh` does
it; it reported failure after six attempts once while a manual retry succeeded
immediately, so it wants more attempts and a backoff.
## 2026-09-10 (Cody) -- second promotion batch: 4 -> 10 checkers

CLAIMED and released: `promote-second-batch`. Six more of the 25 unwired
checkers run against real code and promoted; **19 still unwired.**

**Clean first time, promoted as they stood:** `md_table_check.py`,
`div_balance_check.py`, `fail_open_check.py`, `discarded_verdict_check.py`.

**Two were broken, and both in the same way as yesterday's C1 read: an
INTENTIONAL pattern that a heuristic cannot tell from the defect it
resembles.** That is now three instances in two days, and it is the thing to
expect from any checker's first real run.

- `duplicate_global_check.py` flagged `rBids` on `sairnbuild.html`. It is a
  **deliberate wrapper** -- `var _origRBids = window.rBids;` then a
  redefinition that CALLS it -- with a comment at the site reading *"Do NOT
  'fix' this by deleting either half."* **Acting on the report would have
  deleted a live feature to satisfy a checker.** Now behavioural: is the
  original saved AND called? Every excused pair prints. Saving the reference
  without calling it is still reported, because excusing every second
  definition would switch the checker off.
- `panel_nesting_check.py` **failed on 7 of 22 app files, every one for having
  nothing to check.** Four defects:
  1. `NO_PANELS_FOUND` exited **1** -- a failure for an empty question.
  2. `page-` containers unmatched (the same miss as its sibling).
  3. the name part excluded hyphens, so `panel-check-register` was invisible
     **even under the convention it did support** -- nothing to do with
     `page-`, and there all along.
  4. SAIRNcash's `id="homePage"` has no separator, so the id test is now a
     MATCHER rather than a string prefix.

  `looks_navigated()` is **imported** from `nav_panel_check.py`, not copied.

**One self-inflicted break, recorded:** a heredoc turned the sentinel
`'\x00camel'` into a real NUL byte and broke the module; every app then
"failed". Restored from git and re-applied from a script file. **A patch script
containing escapes does not go in a heredoc** -- the same class as the earlier
backslash-eating that made two regexes unparseable.

**Note on the sairncash SKIP that briefly existed.** Adding the skip path made
the hook fire on every push for one file with genuinely nothing to nest. I did
not leave it and I did not silence it -- I taught the tool the camelCase
convention so it now gives a real answer. A standing notice is how a
report-only checker teaches people to ignore it, and hiding the notice is
worse; the third option is to make the tool able to answer.
## 2026-09-10 (Cody) -- third promotion batch: 10 -> 15, and the rest decided

CLAIMED and released: `promote-third-batch`.

**Clean on the first real run and promoted as they stood:**
`discarded_verdict_crossfile.py`, `literal_drift_check.py`,
`orphan_register_check.py`, `key_collision_check.py`.

**One was not, and it is the FOURTH instance in three days of a checker's first
real run flagging a deliberate pattern.** `sairn_strict_args_check.py` --
Guardian check 31, the class where six `window.fetch` patches shipped doing
nothing at all -- reported `stonedesk.html:3391`. **It is correct code.** The
`apply(this, arguments)` is an early return for a NON-PROXY url, before
anything is touched; the mutating path ends in an explicit
`saSecureClaudeCall(url, opts, _saInnerFetch)`. Mutually exclusive paths. And
Guardian 31 says in its own text not to "fix" a pass-through that has nothing
to forward -- it is correct that way and BETTER, since it preserves extra
arguments.

The checker asked *"does this body mutate anywhere and forward anywhere"*,
which is not the bug. **The bug is a forward that comes AFTER the mutation.**
Now ordered, with the limit stated rather than implied (textual order, not
control flow), and driven three ways: mutate-then-forward still fires, an early
pass-through does not, and the same shape in SLOPPY mode is still ignored
because there `arguments` IS linked and the mutation really does carry through.

**The four instances so far, so the next session expects it rather than
discovering it:**

| Checker | Flagged | Actually |
|---|---|---|
| `sairn_dead_button_audit` C1 | `syncAll`, `mechNotLive` | deliberate honest refusals |
| `duplicate_global_check` | `rBids` | a wrapper that CALLS the original |
| `panel_nesting_check` | 7 files | nothing to nest |
| `sairn_strict_args_check` | `stonedesk:3391` | correct forward on another path |

**Every one of them would have made the code WORSE if acted on.** Two would
have deleted a live feature; one would have turned an honest refusal into a
fabricated one.

**The NOT-PROMOTED decision is now recorded, not left as a default** -- which
is exactly what the inventory row asked for. `--list` prints nine entries with
reasons. Four are READ-LISTS rather than gates **and say so in their own
output**. `waf_rule_check.py` is clean and gate-shaped but makes a live API
call, so a transient network failure would read as a finding on a push; it goes
in once it can distinguish *drifted* from *could not ask* the way the SQL
preflight does.

**One thing to watch:** the sweep is now ~2m8s of CPU per push, async. Fine for
one clone; four clones pushing is real load. If it becomes a problem the answer
is scoping the `apps`-mode checkers to files the push actually touched, not
dropping checkers.
## 2026-09-10 (Cody) -- SAIRNvet live demo-seed: verified closed, three findings handed to Hank

**Did not claim and did not edit `sairnvet.html`.** Hank held
`sairnvet-demo-seed-reaching-live-server` before the dispatch reached me and had
already fixed and pushed it (`a858cab7`), with the file still open in their
clone. Michael's call: fold my three findings into Hank's claim.

**Item 1 CLOSED, and verified against the DEPLOYED file rather than the repo:**
`svSeedStore` live at `sairn.vercel.app/sairnvet` with **39 call sites**,
setting and clearing the flag in a `finally`; `svSyncCollection` returns
immediately when suppressed; and **derived from the deployed source, 46 getters
with ZERO seeding outside the wrapper.** Deriving it beat counting it -- the
count could have been right while one getter slipped past.

**Three findings handed over, all confirmed on the live file:**

1. **`sv_peerconsults` is in `SV_SYNCED` and every photo consult write is
   REJECTED.** `image: pcCapturedB64` is a full base64 JPEG against
   `check (octet_length(data::text) <= 65536)`. Only surfacing is a
   `console.warn`. **And the toast still says "no cross-device delivery yet"**
   on 2026-08-09 honest-language grounds that the collection is
   localStorage-only -- **stale now that it is synced**, so the feature asserts
   two contradictory things at once.
2. **Additive-only hydration**: a corrected dosing entry never reaches a second
   workstation, and nothing in the file says so.
3. **NEW: the hydration path has no `try/finally`** (deployed 2143-2145).
   `svSyncSuppressed=true; st(key,local); svSyncSuppressed=false;` -- `st()` is
   the function hardened for quota and corrupt-store failures, and the
   surrounding `.catch(function(){})` swallows the throw, so **one failed write
   silences the backup for the rest of the session.** That is precisely what
   `svSeedStore`'s `finally` exists to prevent, six lines above it.

**Worth keeping: a guard added with a `finally` next to one without it is the
shape to look for.** The fix and the defect were in the same function body,
written the same day, and the difference between them is three characters.
## 2026-09-10 (Cody) -- a PROBE commit reached origin THREE HOURS after the gate that stops it shipped

CLAIMED and released: `push-gate-check8-did-not-stop-a-probe-commit-that-reached-origin`.
Check 10 added, report-only (`eef3f4b6`).

**Check 8 was not broken, and my first measurement said it was.** Driven
directly with a PROBE commit in range it fires and exits 1. My first run
reported exit 0 -- I was reading `${PIPESTATUS[0]}` of
`printf | python | tail`, which is **printf's** exit code. I nearly filed "the
gate prints Blocked and then exits 0" as the defect. **A wrong instrument reads
exactly like a wrong gate**, and the only thing that separated them was
re-measuring without the pipeline.

**The real mechanism, and it is general.** The hook runs
`$(git rev-parse --show-toplevel)/tools/sairn_push_gate_hook.py` -- the
**working tree** copy. Check 8 landed at 10:08; `8fa974f9` reached origin at
13:24. A session running since before 10:08 that has not synced executes the
pre-check-8 gate, which contains no check 8 at all. All four clones have
`core.hooksPath` installed (checked, not assumed), so the hook fires -- it just
runs an older gate.

**This applies to every check in the file.** A gate shipped at 10:08 protects
nobody who last synced at 09:00, and nothing said so. Check 8 is the example,
not the finding.

Check 10 compares the running gate against `origin/main`'s copy. Report-only:
a stale gate is a could-not-tell about how much was checked, and denying would
block a legitimate push over somebody else's commit. **Does not fetch** --
latency and a new failure mode on every push -- so it under-reports right after
a gate change, which is the correct direction for a staleness check. Fails OPEN
and SILENT. **A CRLF-only difference does not fire**, because four false
"files differ" alarms in this repo came from line endings alone and a notice
that fires every push is worth less than none, on the one check whose whole job
is to be believed.

### Two setup errors in my own probe, both corrected in place

1. It first drove the worktree's gate **at origin/main** -- the OLD one -- so
   the check-10 arms passed on the **absence** of the thing they test. That is
   the same shape as an assertion checking existence where the requirement is
   use.
2. With the gate copied in, "in sync" could not be true while the fix was
   uncommitted, so two arms went red **for the setup, not the check**. The
   worktree now commits the copied gate and points its own `origin/main` at it,
   making the baseline true by construction rather than by whether I have
   pushed yet.

**Probe arm E drives check 8 in the same harness** -- a notice that the gate
may be old is worth nothing unless the checks it vouches for still bite.

The escaped commit itself I reverted in `2a0378f5`; it added
`api/_lib/zz_probe_clean.js` to the production tree.
## 2026-09-10 (Cody) -- independent review of eb640ae8 (SAIRNdental vendor collections)

CLAIMED BY HAND with a recorded override, and released. `sairn_claim.py check`
blocked on **`same app: sairndental`** against Fourth's
`sairndental-outbound-queue-probe / arm15-mutation-does-not-bite`. I read their
actual task and files first: theirs is `tests/sairndental_outbound_queue_probe.py`
arm 15 and their clone had nothing touched in the app. **I named the subject
accurately (`sairndental-vendor-schema-review`) rather than rewording to slip
past the matcher, and the claim carries a `matcher_override_note` saying so** --
same standard as saying `SAIRN_SEED_GATE=off` out loud. **Read-only review; I
did not edit `sairndental.html`**, which is the one file where we could have
collided.

**The commit holds up. `tests/dnt_vendor_backup_probe.py` ALL ARMS PASS.** The
three questions the row asked a reviewer to attack:

- **Soft delete on `dnt_supplies` alone -- CORRECT**, and I checked it by grep
  rather than by reading the rationale: no splice or delete against
  `dnt_vendor_contacts` or `dnt_vendor_pricing_rules` anywhere in the file, and
  `dnt_vendor_orders` is append-only. The reasoning and the code agree.
- **The nesting asymmetry -- JUSTIFIED.** Contacts are keyed by vendor name and
  would collide with `id`; the pricing object IS the record.
- **Wholesale-not-merged -- RIGHT, and it carries a cost the commit does not
  name.** That is the finding.

### The finding: a failed push looks like success and is then silently reverted

`vSetVendorDiscount()` / `vSetCategoryDiscount()` / `vSetProductOverride()` all
do:

    st('dnt_vendor_pricing_rules', rules);
    dntPushVendorPricing(rules);          // not awaited, result never checked
    toast('... discount set to ' + pct + '%');   // unconditional

`dntPushOne()` reports a failed write with a **`console.warn` and nothing
else**. And hydration is **server-wins with no guard** -- `dntSyncFromServer()`
`st()`s the server object straight over the local one. So a push that fails
shows a success toast, and the **next sync replaces the edit with the server's
stale copy.**

`dnt_settings` is cited as the precedent, and there this costs a preference.
**Here it is a negotiated vendor discount, so it changes what the practice
pays.**

**It is inert today and live the day the SQL runs.** With
`sql/sairndental_vendor_schema.sql` unrun, reads come back non-array,
`failureCount++` fires, and nothing is overwritten. The exposure starts the
moment the schema is provisioned -- which is precisely when nobody will be
looking for it. That timing is why this is worth writing down now rather than
after.

**Minimum bar:** check the push result before the success toast, and do not let
hydration overwrite an object whose last local write has not been confirmed.
## 2026-09-10 (Cody) -- SAIRNdental vendor writes: CLOSED, and it was live

CLAIMED and released: `sairndental-vendor-object-write-confirmation`.
`d22ce106`. The SQL had already been run, so the exposure I filed "before
provisioning" was in fact already open.

**Wholesale-replace was RIGHT and is not what changed.** It is what makes a
removal expressible, which a merge cannot do. The missing half was **confirming
the write before trusting it**.

1. **The toast is derived from the push result** at all four writers. A refusal
   names the consequence -- *"on THIS DEVICE only ... another workstation will
   not see it"* -- for 7s, rather than a status word for 3s.
2. **Hydration will not overwrite an unconfirmed write.** A refused push
   records the store key in `dnt_unconfirmed_writes`; a later success clears
   it; both wholesale branches consult it; and the refresh **reports what it
   held back** instead of saying "Refreshed from server", which would be the
   same false success one layer out.

**The flag is persisted deliberately:** a reload must not turn *"the server
never took this"* back into *"the server agrees"* -- exactly what a
`console.warn` left behind the moment the tab closed. It is **not synced and
must never be**, or one workstation could silence another's guard. It skips the
OVERWRITE, not the READ, so a genuine network failure is still counted.

**Verified live twice over.** Source checks against the deployed bytes (4
result-derived toasts, both hydration guards, no unconditional toast left, flag
absent from the sync registry) **and the deployed bytes DRIVEN**: a refused push
does not report success, says NOT SAVED, holds the key; the hold survives a
reload; a later success releases it.

### The probe earned its keep on its first run, against me

**Three of my own source assertions survived a mutation that removed the
behaviour.** They matched what came AFTER `dntIsUnconfirmed(...)` rather than
the guard's POSITION, so `if(false&&dntIsUnconfirmed(...))` left them green.
That is scrubber item 16 shape B -- asserting a mechanism EXISTS where the
requirement is that it is CONSULTED. Anchored on `if(` now.

A fourth control reported **ANCHOR-2**: two writers share a line verbatim, so
my anchor was not unique and that control silently probed nothing. Re-anchored
on the unique third writer.

**Both were found by the mutation controls, not by reading the assertions.**
That is the whole argument for writing the controls at the same time as the
suite rather than after.

**And a third heredoc casualty today:** a quote inside a heredoc broke the
patch that made the refresh toast honest. Rewritten as a script file. The rule
is now unambiguous for me -- **any patch containing quotes or escapes goes in a
file, never a heredoc.**
## 2026-09-10 (Cody) -- fourth batch: 15 -> 16, and one checker held back on purpose

CLAIMED and released: `promote-fourth-batch`. `5abfcdba`.

`write_without_readback_check.py` is clean on real code (0 findings, 0
could-not-tell) and goes in. **Its sibling does not, and that is the point.**

**`local_only_collection_check.py`'s exit code was wrong and is fixed.** It
returned **1** for a real finding AND for "I could not read this app". On
2026-09-10 it reported `local-only: 0` in **all eighteen apps** and still
exited 1 -- a checker announcing a failure while reporting that nothing is
wrong. Wired as it stood, the registry would have filed *"sairncash.html could
not be read"* as **a defect in SAIRNcash**. Now 3 for could-not-tell, 1 only
for a real finding, plus a canonical `SKIPPED:` line so the runner quotes the
reason rather than a bare "SKIPPED".

**Two of CC's probe arms asserted the literal 1 for a could-not-tell.** Their
NAMES said *"exits non-zero"* -- which is their purpose, and which 3 still
satisfies; the literal 1 was written when 1 was the only non-zero code the tool
had. They now pin **3** while the existing arm pins **1** for a real finding.
That is **strictly stronger** than before: the two states can no longer be
confused in either direction. I did not relax an assertion to get past a red.

### The part worth keeping: I tried the third option and reverted it

Those two apps report could-not-tell, so wiring the checker means a notice on
**every push**. Hand-checked: every `localStorage.setItem` in `sairncash.html`
and `sairnroofing.html` is device state -- device id, subscription, trial,
usage counter, licence fingerprint. **There is genuinely nothing to find, and
the tool cannot prove it.**

Earlier today, faced with the same choice on `panel_nesting_check`, the right
answer was to teach the tool the real convention. **Here it was not.**
Classifying those five keys as device state made both files resolve and the
notice vanish -- and **broke two arms of CC's `local_only_shape_probe.py`**.
Reverted.

**Changing a classifier to silence a notice is how a checker starts lying.**
The difference from the panel_nesting case is that there I taught the tool
something true about a convention it did not know; here I would have been
widening a device-state list to make an inconvenient output go away, in
somebody else's tool, against their fixtures. Same-looking action, opposite
character -- and the probe is what told me which one it was.

Held back with the precondition recorded in `NOT_PROMOTED`, printed by
`--list`: promote it when it can tell **absence** from **blindness**. Same
standing as `waf_rule_check.py`.
## 2026-09-10 (Cody) -- the verification programme: part 1 built, parts 2-4 scoped

CLAIMED and released: `requirements-to-test-traceability`. `10a0aa67`, plus
`docs/2026-09-10-verification-programme-plan.md`.

**Part 1 is DERIVED, not written**, and that is the whole design. A
hand-written matrix here would be wrong within hours -- measured, not assumed:
the Guardian app map has been corrected six times and CLAUDE.md carries a
standing instruction to re-count rather than trust its own numbers. Four
sources in descending authority (GUARD_TESTS, the numbered push-gate checks
parsed from source, the report-only REGISTRY, index rows citing a test), every
row naming the source it came from so an auditor checks THAT file, not this
document.

**Its first run is the baseline everything else gets measured against:**

| Measure | Value |
|---|---|
| Test files on disk | 261 |
| Traced to a stated requirement | 77 |
| **Untraced** | **184** |
| Citations pointing at a file that does not exist | **2** |

The two broken citations are a real finding: a row names a test as its proof
and the file is not there, so the requirement is UNPROVED however the row
reads. One is probably a prose placeholder; the tool cannot tell and says so
rather than picking.

**It states what it cannot tell you** -- that a traced test actually PROVES its
requirement (only the mutation probes answer that, and only some tests have
one), and anything at all about code nobody wrote a requirement for, which is
the largest unknown on the page.

**And it cannot go quietly stale.** CLAUDE.md is explicit that a generated
artefact needing regeneration after every edit reproduces the silent-failure
shape it exists to catch. `--check` regenerates in memory and compares, wired
as report-only checker 17. **It fired on its own first run, against me:** adding
its own registry entry changed a source and `--check` went red.

**Parts 2-4 scoped, with the order argued rather than assumed.** Part 3 (fault
injection) goes BEFORE part 2 (mock audit): it needs no second session, and it
has four concrete targets from tonight. **Every live finding today was a WORLD
failure, not a logic bug** -- a missing `finally`, a stuck suppression flag, a
refused push showing success, a seed leak on a fresh device. Mutating logic
could not have found any of them. Part 4 is last and says why: a register built
before there is anything to put in it becomes a file nobody updates, and its
emptiness reads as "no defects".

**Fourth heredoc casualty today** -- a quoted registry entry broke on insert.
Repaired from a script file. I have now hit this four times in one session and
it is filed platform-wide.

**One decision for Michael, in the plan:** whether the mock auditor may read
`docs/` at all. Fully blind is a stronger test and costs real time re-deriving
what the repo already knows; blind to the worklogs but allowed the index and
the matrix is cheaper and still adversarial. I would start with the second.
## 2026-09-10 (Cody) -- broken citations fixed, and Part 3: fault injection

CLAIMED and released: `fault-injection-harness`. `0d8cc523` (citations),
`15f3b86d` (fault injection).

### The two broken citations -- one was real

**`tests/X_probe.py` was a prose placeholder** inside a recommended sentence
template, harvested because it is shaped exactly like a path. Renamed to
`tests/<name>_probe.py` so it cannot parse as one.

**The other was real and the row was stale.**
`sairndental_settings_merge_base.js` was DELETED by `8b9201c7` -- the commit
that changed `dnt_settings` from a client-side merge to a server-side PATCH,
removing the stale-base problem at the root. The row still cited it and still
claimed **21 assertions**. **Verified before rewriting rather than assumed:**
the successor suite carries this row's substance more strongly (all three
writers asserted to build a patch of their OWN KEYS, plus the
ACKNOWLEDGED-collision arm) and has **15**, not 21. Attaching an old claim to a
new test without reading it is the failure the matrix exists to make visible.

**The correction reintroduced the finding on my first attempt** -- naming the
deleted file as a live path is itself a broken citation. The tool caught it
immediately; the filename is now written without its directory so the
provenance survives and the citation does not. **Zero broken citations remain.**

### Part 3 -- fault injection

**Break the WORLD, not the logic.** Mutation testing breaks the logic and asks
whether a test notices. Fault injection breaks the world and asks whether the
app stays HONEST. **The assertion is always: after the fault, does the app SAY
something true?** A silent survival IS the defect.

`tests/faults/faultkit.js` -- five transport faults, every one a shape this
platform has seen: `refused` (null), `throw` (REJECTS -- the shape a
`.then(ok => ...)` caller is blind to **by construction**), `hang`, `partial`,
and storage throwing on the Nth write. **It self-tests when run directly**,
because `run_all_tests.py` executes every `.js` under `tests/` and a library
that only defines would be counted as a passing test file.

**Three real gaps, reported rather than passed over:**

| Fault | What the app does |
|---|---|
| dropped socket | **no toast at all** -- user clicks Save on a dead connection, sees nothing |
| hung write | indistinguishable from not having clicked; no timeout on that path |
| partial response | **clears** the unconfirmed flag, so hydration may overwrite |

Each is asserted as CURRENT behaviour with the reason at the arm, so adding a
`.catch` or a timeout turns the arm RED and it gets updated deliberately rather
than the fix landing unnoticed. **That is the opposite of a skipped test.**

**Control 1 is the headline:** it reverts the hydration `finally` -- the exact
defect that shipped this morning, which every logic-level suite was green
through -- and the fault suite catches it. All 5 controls bite; both live app
files restored byte-identical.

**The structural arm is what makes it a guard rather than a regression test:**
every `svSyncSuppressed = true` must be followed by `try{` and cleared in a
`finally`, so a third suppression site added later is caught even though
nothing drives it.

**Standing note for every session, per Michael 2026-09-10:** criticality
tiering, requirements-to-test traceability and SOUP tracking are now the
permanent standard for ongoing vertical work, not a one-time initiative. The
matrix (`docs/traceability-matrix.md`) is regenerated by
`python tools/traceability_matrix.py` and verified by report-only checker 17 --
**adding a test without a stated requirement now shows up as an untraced file
rather than as nothing.**
## 2026-09-10 (Cody) -- the fault layer's first three findings, fixed and live-verified

CLAIMED and released: `dnt-push-dropped-socket-hang-and-partial`. `5b98fd27`.

**The layer built this afternoon found three live defects on its first run, and
this closes them.** All on SAIRNdental's vendor write path, whose schema is
provisioned, so all three were real.

| Fault | Was | Now |
|---|---|---|
| dropped socket | rejects -> `.then(ok => ...)` never runs -> **no toast at all**, and an unhandled rejection for two unkeyed callers | settles to `null`, the refusal shape every caller understands |
| hang | never settles, no timeout anywhere | races a 15s timeout into the same refusal |
| partial response | any non-null counted as success, **clearing** the unconfirmed flag | flag stays set, missing fields named |

`null` is the one shape every caller already understands, so a rejection and a
timeout are mapped onto it rather than inventing a second failure vocabulary.
Sentinels are **object identities, never strings** -- a sentinel a server could
plausibly return is one that will one day be mistaken for data.

**The partial case is deliberately NOT a user-facing refusal.** A short response
may still have been stored correctly, and "NOT SAVED" there would be a false
alarm on a path that may be fine. It does the one unambiguously right thing --
leaves the key unconfirmed so hydration cannot overwrite -- and names the
missing fields. **Conservative on the visible half, strict on the destructive
half.**

### Five arms went red, and that is the design working

Each of the three gaps was asserted as CURRENT behaviour with a note at the arm
saying the day a fix landed it would trip and be updated deliberately rather
than the fix landing unnoticed. **That day was the same day.** Every one is
inverted in place with its history kept, and three were ADDED in the other
direction -- an unkeyed caller no longer gets an unhandled rejection, the
shipped timeout is asserted to be a sane wait rather than a hidden zero, and a
COMPLETE response must still clear the flag. **Without that last one a
missing-key check that never passes would read as caution and behave as a
broken sync.**

### Two process notes worth keeping

**A crash is not a failure and reads like a pass.** When `dntPushOne` gained a
dependency its sibling harness did not supply, that suite CRASHED after
printing its last `ok` -- trivially mistaken for a green run. The harness now
supplies it, and its line-splitting regex is defined ONCE instead of at each
call site, because repeating it is how one of them ends up wrong.

**Fifth and sixth heredoc casualties today**, both mangling a regex literal in
the same patch. I restored from git and redid it from a script file. The rule
is not "prefer a file" -- it is **any patch containing a quote, a backslash or
a regex goes in a file, full stop.**
## 2026-09-10 (Cody) -- Part 4 (defect register) and the portfolio-wide hazard sweep

CLAIMED and released: `defect-density-register`, `write-path-fault-hazard-sweep`.
`1818e05f` and the sweep commit.

### Part 4 -- the register, and why the number is not the signal

**Deliberately not a commit log.** `git log --grep '^fix('` returns thirty
entries for 2026-09-10 alone and most are NOT product defects -- harness
corrections, checkers whose first run needed tightening, my own probe mistakes.
Auto-ingesting them would make the density large and meaningless, **and the
number would then be quoted.**

So a record carries the judgement nobody can derive -- layer, severity, and
above all **how it was found** -- while git supplies the mechanical half (date,
files, lines, whether the commit resolves). Seeded with **14 defects I can
personally attest to**, and not one line further back: a register padded with
guesses is worse than a short one, because its SIZE implies completeness.

**What the first report already shows is the whole point:**

| app | lines | defects | per 1k | methods |
|---|---:|---:|---:|---|
| sairndental | 6,047 | 4 | 0.66 | 4 |
| sairnmechanical | 2,420 | 1 | 0.41 | 1 |
| sairnvet | 8,866 | 3 | 0.34 | 1 |
| stonedesk | 40,246 | 1 | **0.02** | 1 |

**StoneDesk is not the cleanest app. It is the least swept.** The density ranks
ATTENTION, not quality, and reading it the other way is exactly the mistake the
register would otherwise cause -- so `--report` refuses to be quoted bare and
says so on every run.

24-check probe that ATTACKS it: a nonexistent commit, an invented method, an
invented layer and a duplicate are each refused; deleting a record's commit
makes `--check` go red; and **one commit CAN carry several distinct defects**,
because `5b98fd27` fixed three and collapsing them would undercount by two.

### The hazard sweep -- where the fault harness goes next

Fifteen apps write to a server. A dynamic suite for each is weeks, so
`tools/write_path_fault_scan.py` finds where the hazard IS first.

**36 write call sites across fifteen apps read their result on the success path
only or not at all, and ELEVEN OF FIFTEEN APPS HAVE NO TIMEOUT ANYWHERE.**

**Hand-verified before shipping**, because a first run that over-reports gets a
checker switched off. Both SAIRNvet flags are real and **both are open**:

- `sairnvet.html:2135` -- **the same defect I fixed in SAIRNdental this
  evening.** The server-backup push handles `saved===null` with a careful
  comment about not reporting a failed push as success, and has **no `.catch`**.
  A dropped socket skips that handler entirely.
- `sairnvet.html:8721` -- a `shared_knowledge` write inside a `try/catch` whose
  catch is synchronous and cannot catch a promise rejection.

**Task 3 was taken by CC while I worked.** They claimed
`tool-blind-spot-audit -- checkers that exit clean while silently not looking`,
which is the third-party tool audit verbatim. Not duplicated.

**And a process failure of my own, twice in one session:** I ran
`git reset --hard origin/main` after a push loop that had silently failed,
which DISCARDED the register commit. Recovered from the reflog both times.
**Verify the push landed BEFORE resetting** -- the loop returning is not the
same as the commit arriving. The second recovery also hit a cherry-pick
conflict in `docs/traceability-matrix.md`, and the right resolution there was
neither side: it is GENERATED, so I regenerated it in the worktree.
## 2026-09-10 (Cody) -- the two SAIRNvet write paths, and the mechanism I wrote
## down for both of them was wrong

Skill used: `sairn-silent-failure-sweep`, then `sairn-guardian-v2` before the
push. Claim held from the previous session: `sairnvet-write-path-rejection-
blindness`.

**BOTH FINDINGS WERE REAL SITES AND BOTH RECORDED REASONS WERE FALSE.** The
entry above this one says `sairnvet.html:2135` "has **no `.catch`** -- a dropped
socket skips that handler entirely", and that `:8721` is "a promise rejection a
synchronous try/catch cannot catch". `svData()` at `sairnvet.html:8698` ends in:

    .catch(function(e){ console.warn('svData network error:', e.message); return null; })

So a dropped socket, a DNS failure, a CORS rejection and a non-JSON body --
Vercel's bot-mitigation challenge page, which this platform really does get
served -- are **all** converted to a resolved `null` before any caller sees
them. The `.then(saved => ...)` handler ran. It warned. There was no unhandled
rejection on either line.

**THE HAND-VERIFICATION WAS DONE AND STILL PRODUCED A WRONG MECHANISM.** That is
the part worth keeping, because the previous entry's own defence was that it had
been hand-verified before shipping. Reading a call site cannot see that its
callee already catches. A flag is a lead; the proof is an injected fault.

**WHAT WAS GENUINELY SILENT: THE HANG.** `grep -c setTimeout sairnvet.html`
returned **1** for 8,866 lines, and that one is not on this path. A gateway that
accepts and never answers neither resolves nor rejects, so `svData()`'s own
catch never fires either: the `.then` never runs, the careful `saved===null`
warning never prints, and the clinic's record sits on one device with **nothing
saying so**. The exact defect class the backup feature exists to close, arriving
through the one door the feature's own reporting was blind to.

**REPRODUCED BEFORE FIXING, not after.** `tests/faults/sv_backup_write_faults.js`
against the pre-fix file: the hang arm failed with **0 warnings**, and the
rejection arm crashed the suite outright as an unhandled rejection at the
harness boundary. Then `svPushOne()` -- a 15s timer raced against the call,
with hang, rejection and refusal all mapped onto the single `null` every caller
here already understands and the reason named in each message. 12 arms pass.
**4 mutation controls all bite**, with `sairnvet.html` restored
byte-identical (sha256 compared, not assumed): dropping the race kills 2 arms,
a 0ms timeout kills 1, reverting the shared-knowledge write to bare `svData`
kills 2, and dropping the reason from the message kills 2.

**DELIBERATELY NARROWER THAN SAIRNdental's `dntPushOne()`, and an arm asserts
the reason.** No unconfirmed flag here: `dntHydrate` overwrites local rows, so
an unconfirmed copy can be clobbered, but `svHydrateAll()` is additive-only and
never overwrites a locally present id. There is no destructive path for such a
flag to protect, and porting it would be machinery with no failure behind it.
The arm fails if that hydration comment ever disappears -- so if hydration
starts overwriting, the narrowing stops being justified and says so.

**THE SCANNER FLAGGED ITS OWN FIX, and that is its own defect.**
`write_path_fault_scan.py` looked for a literal `.catch(`, so the two-argument
`.then(onOk, onErr)` form reported as `then-no-catch` -- in `svPushOne` and, since
the evening before, in `dntPushOne`. **A checker that flags the repair is one a
session switches off.** It now recognises the second argument by brace balance
(string-aware, stated limit on regex literals), held by
`tests/run_write_path_scan_probe.py`, 13 arms. The probe deliberately asserts
the opposite direction too -- a ONE-argument `.then` must still be a finding --
because a fix that stopped reporting the real defect would be worse than the
false positive it removed. Portfolio blind-site count **36 -> 33**.

**A PRE-EXISTING INCONSISTENCY IN `docs/traceability-matrix.md`, found by
regenerating it.** The committed file's own sentence said *"85 of 272 test files
are traced ... 187 are not"* while **its own list enumerated 188**. The file is
GENERATED and its header says a hand-edit "will look authoritative until it is";
a count line and a list that disagree is what a cherry-pick resolution taking one
side's sentence and the other side's body looks like. My regeneration corrects it
as a side effect; recording it because the artefact was internally inconsistent
and nothing would have surfaced that except running `--check`.

**Session-lock note.** The SessionStart hook warned another session claimed this
clone (PID 13668). `Get-Process -Id 13668` returned nothing -- the process was
gone, the lock was stale, and the `cody` claim on this subject was my own
previous session's. No duplication.
## 2026-09-10 (Cody) -- the platform wrapper test that three sessions found red,
## and the comment that was counting as a report

Skill used: `sairn-silent-failure-sweep`. Assigned directly by Michael after
Hank, CC and I each independently reported `tests/sairn_storage_wrapper_honesty.js`
broken the same night and each deferred it as someone else's lane. **That is the
finding underneath the finding: three correct deferrals leave a platform-wide
test red, and it was being cited as coverage the whole time.**

**THE CRASH.** `2a61b739` taught `saveCheck()` in `sairnmechanical.html` to mint
an id. The test extracts `saveCheck` into a `new Function` realm and did not
extract `mechCheckId()` or `mechEnsureCheckIds()`, and `saveCheck` also reads
`window.mechPushRecord` -- where `typeof` does **not** guard an undeclared
`window`, because typeof is only safe on a bare identifier and this touches a
property. `ReferenceError`, thrown inside the SAIRNmechanical block, which sits
**before** the blocks covering `stonedesk.html` and `sairnvet.html`. So the file
was not "failing one arm"; everything after that point had never run.

Helpers are now pulled from the real file, not stubbed. A stubbed `mechCheckId()`
would let the cheque-number collision fix it exists for rot while the arms stayed
green -- the fixture-supplies-the-thing-it-tests shape this repo has already been
bitten by once.

**THE SECOND DEFECT, AND MUTATION IS THE ONLY REASON IT WAS FOUND.** With the
crash fixed I probed whether the restored arms actually bite. Silencing every
real `console.error` in `sairnvet.html`'s `st()` left the file **GREEN**.

The reason is two lines of PROSE in that function's body:

    // Every non-success exit latches the key so the next success toast is
    // corrected rather than believed -- see showToast() above.

`speaks` was `/console\.|toast|Toast|alert\(/` run over **raw source**. So the
one assertion this block exists for -- `mute` is empty, therefore NO app has a
silent write wrapper -- **was satisfiable by a code comment**, in a repo whose
comments deliberately quote the calls they describe. An assertion a comment can
satisfy is close to unfalsifiable.

**MEASURED BEFORE LANDING THE FIX, because the honest question is whether it was
masking anything today:** across all 17 app files, **zero** wrappers speak only
via prose. Every one has a real console or toast call in code, so stripping
changes no verdict and `mute` stays empty either way. The defect was LATENT --
it would have masked the next regression, which is the single thing the block is
for. Fixed because a tripwire that cannot trip is worse than no tripwire, not
because it was lying today. That measurement is now a standing arm rather than a
sentence in a commit message, and it doubles as the sharper tripwire: a wrapper
whose only mention of a console or toast is prose gets named there even when the
`mute` list stays green.

Stripper is a state machine, not a regex, for the reason `tools/jscomments.py`
records at length -- three of seven regex strippers in `tools/` were destroying
90% of their input and reporting CLEAN on what survived. Controls assert it
leaves alone a `//` inside a URL string, a `/*` inside a string, a backtick
template, and an escaped quote, and that a real block comment IS removed.
The inline `probe()` helper in that file is a SECOND COPY of the detector logic,
so it was taught the same thing in the same commit -- otherwise the arms would
prove a function nothing runs.

**51 arms pass, from 41 that could not all run. Three mutation controls across
three different app files, all bite, all files restored byte-identical by
sha256:** breaking SAIRNmechanical's check-number restore reds the mech arm that
was previously dead; silencing SAIRNcare's `st()` catch reds both the `mute` list
and the named per-app arm, neither of which had been reached in the crashing
version; silencing SAIRNvet's reds the new prose arm.

**STILL OPEN, and stated rather than quietly tightened.** The one-hop delegation
rule lets `st()` borrow the voice of anything it calls. `sairnvet.html`'s `st()`
calls `svSyncCollection()`, which logs about a failed SERVER push -- nothing to
do with the localStorage write failing -- so with comments stripped the `mute`
list *still* passes on a silenced write-failure path. The new prose arm catches
that specific case, but narrowing delegation to callees invoked from inside a
`catch` is a behaviour change to a platform-wide gate and could turn working apps
red. Michael's call, not mine.

**FLAGGED FOR WHOEVER IS NEXT IN `sairndental.html`, with the diagnosis done so
it is not re-derived:** `tests/dnt_vendor_write_confirmation_probe.py` reports
two controls that do not bite, for two different reasons.

- **Control 4** anchors on `}else if(storeKey){` + `dntMarkUnconfirmed(storeKey,
  false)`. **That shape exists nowhere in the file** -- zero hits for
  `}else if(storeKey)`; `dntPushOne()` now ends in a flat
  `if(storeKey) dntMarkUnconfirmed(storeKey,false);` at line 5931. Reported
  honestly as `ANCHOR-0`, which is the probe working. The control tests nothing.
- **Control 3** anchors on the SIX-space-indented
  `if(storeKey) dntMarkUnconfirmed(storeKey,true);`. There are two such calls:
  line **5903** in `refused()` at four spaces, and line **5928** in the
  PARTIAL-RESPONSE branch at six. So the control mutates the partial-response
  branch while its label claims the refusal branch -- **and no control mutates
  the refusal path at all.** It returns `SILENT`, so no arm in
  `tests/dnt_vendor_write_faults.js` covers the branch it does hit either. A
  drifted anchor and a real coverage gap behind it, two separate facts.
- Worth a decision: the probe **exits 0** while printing `CONTROLS THAT DID NOT
  BITE`, so `run_all_tests.py` is the only thing surfacing it. A dead control
  arguably belongs in the exit code.
## 2026-09-10 (Cody) -- SAIRNgrounds had no timeout at all, and my own scan said
## it did, because of a weather message

Skill used: `sairn-silent-failure-sweep`, `sairn-guardian-v2` before the push.
Claim: `sairngrounds-write-path-blind-sites`. Picked because 8 fire-and-forget
writes was the largest blind cluster in the portfolio and nobody held it.

**THE FIRST THING I FOUND WAS THAT MY OWN TOOL WAS LYING IN THE OPTIMISTIC
DIRECTION**, which is the only direction a hazard scan must never fail in.
`write_path_fault_scan.py` printed `timeout? yes` for SAIRNgrounds. The file
contains no timer race, no `AbortController` and no `AbortSignal` in 324KB. The
`yes` came from `signal\s*:` matching two USER-FACING SENTENCES:

    'Weather Command Engine signal: '+src.textContent+...   (lines 3077, 3414)

Forty-three server writes, and the one thing that would make a hang survivable
was a string in a weather message. **Same defect class as the comment-counts-as-
a-log bug I had fixed in `sairn_storage_wrapper_honesty.js` an hour earlier --
a detector run over raw source instead of over code.** Twice in one session,
two different tools, found by two different routes.

**AND THE COLUMN WAS WRONG A SECOND WAY.** It was file-wide, so a READ-path
timeout counted as protecting writes. `sairnbiz.html`'s only race bounds
`sbFirstDeviceHydrate()`; `stonedesk.html`'s only `AbortSignal.timeout(8000)` is
on `/api/knowledge`. Neither protects a single write. So the portfolio line
**"eleven of fifteen apps have no timeout anywhere" was itself too kind -- it
was thirteen of fifteen**, and only SAIRNdental and SAIRNvet had a real one.
The column is now three-state; `read-only` is deliberately not spelled `yes`.

**THE FAULT IS WORSE HERE THAN A REFUSAL, BECAUSE THE REFUSAL PATH IS ALREADY
GOOD.** Forty of the 43 writes read `var syncResult = await grdData(...)` and
toast exactly what failed to sync. But `fetch` against a black-holed connection
neither resolves nor rejects, so the `await` never returns, `grdData()`'s catch
never runs, and **the toast never fires at all.** Click Save, screen says
nothing, indistinguishable from not having clicked. Careful reporting attached
to a promise that never settles reports nothing.

**ONE EDIT RATHER THAN A PUSH HELPER, and that was a deliberate call.** SAIRNvet
and SAIRNdental needed `svPushOne`/`dntPushOne` because their callers had no
shared failure vocabulary. This file already has one: `null` means "did not reach
the server", understood at all 43 sites. So `AbortSignal.timeout(15000)` went
INSIDE `grdData()`, where an AbortError lands in the catch that already returns
null. A hang arrives as the refusal every caller is written for -- no new shape,
no routing, and no chance of missing a site. Feature-detected, and **it bounds
reads too**, which is intended rather than incidental: a hung read leaves a panel
waiting forever and `null` is already the fall-back-to-localStorage signal.

**FIVE OF THE EIGHT FLAGGED SITES WERE SAFE**, which I only learned by reading
every one before touching any -- the rule the tool prints on every run.
`await Promise.all([grdData('write',...), ...])` then names each record that
failed to sync. **The most careful write-reporting on the platform was being
reported as the least**, because the classifier looked 40 characters behind the
call for an `await` and could not see one sitting before a `Promise.all([` and a
line break. Fixed, with an arm asserting a BARE `Promise.all` is still blind --
a fix that stopped reporting the real hazard would be worse than the
over-report.

**OF THE THREE REAL ONES, ONE IS A FIX AND TWO ARE CONFIRMED DECISIONS:**

- `cmSavePoints()` -- **fixed.** Its three callers toast *"Point captured (±4m)"*
  and *"N point(s) placed via AR"* unconditionally, so a course point that never
  reached the server was announced as captured. Now `async`/`await` matching the
  other forty sites verbatim, with the honest message raised in the saver: `toast()`
  is `textContent = m`, so a later message REPLACES an earlier one and the
  optimistic toast is superseded when the push resolves null.
- `gcdSaveRound()` -- **silence KEPT, and it was already accepted and recorded in
  the file**: it fires on every shot and hole arrival, so a per-call failure toast
  would run continuously while the server is down and drown the cart-order
  messages somebody is actually waiting on. **"Do not tell the user" was decided;
  "record nothing" was not**, and was only ever a side effect of reading no
  result. The transport now logs. An arm asserts both the silence AND that the
  reason is still stated at the site, so the next reader does not file it as a
  defect and "fix" it.
- `recordGrdSharedTopics()` -- best-effort AI telemetry, console only, same call
  and same reasoning as SAIRNvet's.

**THE SCAN ALSO COUNTED ITS OWN COMMENTS, AND I CAUGHT IT BY WRITING ONE.** The
`grdData` comment quotes the house pattern -- and the tool reported a
fire-and-forget write at a line holding nothing but prose. Write sites are now
found on comment-stripped source (length- and newline-preserving, so reported
line numbers stay true). **That cleared two OTHER sessions' phantoms as well:**
`sairndental.html:4839` and `sairndesign.html:2292` both read *"Was
sdnData('write',...)"* about code that no longer exists, and both had been in
the portfolio count since the scan shipped. 33 -> 25.

**18 fault arms pass. 7 mutation controls, all biting, file restored
byte-identical by sha256** -- removing the signal, widening the timeout past
platform, silencing the transport, silencing `cmSavePoints`, moving the local
write after the push, adding a per-shot toast to `gcdSaveRound`, and removing
both feature-detect guards.

**ONE MUTATION DELIBERATELY SURVIVED AND IS RECORDED RATHER THAN PATCHED
AROUND.** Deleting the `typeof AbortSignal !== 'undefined'` guard changes nothing,
because the inner try/catch catches both the TypeError and the ReferenceError.
The guard is kept for readability -- a normal expected condition should not be
signalled by an exception -- and the arms prove the BEHAVIOUR rather than the
line that delivers it. Said in the suite, because a surviving mutation nobody
explains reads as a hole.

**Pre-existing and untouched, verified by running both checkers against
`git show HEAD:sairngrounds.html`:** 4 key-collisions (distinct local variable
names writing one key, which the tool itself calls a pointer not a verdict) and
1 informational D2 dead-button finding. Identical before and after.
## 2026-09-11 (Cody) -- narrowing the delegation hop, and the measurement that
## said narrowing it was not enough

Skill used: `sairn-silent-failure-sweep`. Claim:
`wrapper-honesty-delegation-hop`. Michael's decision, with the explicit
condition: measure the real impact before committing.

**MEASURED, ACROSS ALL 17 WRAPPERS IN THE 17 APP FILES. ZERO VERDICTS FLIP.**
Every wrapper keeps the result it had. The case the loose rule was built for is
preserved exactly: `stonedesk.html`'s `st()` and `stRaw()` have **no console
call of their own** -- they survive purely through `sdStorageFailed()` and
`sdBackupHookFailed()`, and both of those are called **from inside a catch**, so
the stricter rule still reaches them. The only delegations it drops are the ones
that were never about a failed write: `svSyncCollection`, `sbSyncCollection`,
`sfSyncCollection`, and each wrapper matching its own name recursively.

**AND THE MEASUREMENT SAID SOMETHING I HAD NOT EXPECTED: NARROWING THE HOP DOES
NOT CLOSE THE CASE THAT MOTIVATED IT.** `sairnvet.html`'s `st()` has TWO catch
blocks -- one guarding the server-backup hook, one guarding the
`localStorage.setItem`. Both log. So silencing the write-failure one leaves the
backup-hook one talking, and `mute` stays green, because **`mute` asks whether
the wrapper speaks ANYWHERE, not whether the failure path does.** The narrowing
moves the hole one step; it does not fill it.

I checked the intermediate step too, rather than assuming: narrowing the DIRECT
test to catch bodies as well also measures 0 flips and **also does not close it**,
because both of sairnvet's logs are inside catches. The variant that closes it is
per-catch attribution -- does the catch that ENCLOSES the setItem speak -- and
that measures 0 mute across all 17 as well.

**SO BOTH LANDED, AND THE SECOND IS STATED AS MY ADDITION ON A CLEAN
MEASUREMENT.** The delegation narrowing is Michael's decision, implemented as
decided. The guarding-catch question is a SECOND, SEPARATE arm (`guardMute`),
not a change to what `mute` means -- because changing the meaning of the
platform-wide list is a further step and should be decided, not folded in. It
asserts `[]`, which is the measured truth for all 17 today, so it cannot fire
falsely; it fires the day a write-failure catch is silenced while some other
catch in the same function keeps talking.

**FOUR MUTATION CONTROLS, AND CONTROL 1 IS THE MOTIVATING CASE:**

- **M1** -- silence sairnvet's write-failure catch, leave the backup-hook catch
  logging. **The new arm goes RED.** This survived every previous version of this
  file, including the one I shipped an hour earlier.
- **M2** -- unmutated control: stonedesk, which relies *entirely* on the
  delegation hop, still passes 52/52. Without this arm the narrowing could have
  been silently too strict and looked like a success.
- **M3** -- silence the shared `sdStorageFailed()`: both arms red, both stonedesk
  wrappers named.
- **M4** -- silence SAIRNcare's catch: three arms red.

All three app files restored byte-identical by sha256. 52 arms pass.

**Noted for CC, whose `comment-quoting-probe-blindness` claim is active on
exactly this pattern:** this file already strips comments before every speaking
test as of `3f09a48e` -- on the direct test, on the delegation hop, and inside
its own duplicate `probe()` helper. It is the one checker in that sweep that
needs nothing, and the stripper there is a local state machine rather than
`tools/jscomments.py`, because this file is JS and that one is Python.

**The standing pattern, now three sessions deep and worth naming as one thing:**
a detector run over raw source counts its own explanatory prose. CC hit it twice
tonight on a different tool, I hit it in `sairn_storage_wrapper_honesty.js` and
again in `write_path_fault_scan.py` within the hour. It is not three incidents.
## 2026-09-11 (Cody) -- the portfolio transport sweep: twelve apps with no
## timeout anywhere, and two that would have swallowed one

Skill used: `sairn-silent-failure-sweep`, `sairn-guardian-v2` before the push.
Claim: `platform-write-transport-unbounded`.

**MEASURED FIRST, AND THE MEASUREMENT IS WHAT MADE A ONE-MECHANISM SWEEP
POSSIBLE: every app has exactly ONE write transport making exactly ONE `fetch`.**
Fifteen apps, fifteen functions, fifteen fetches. Twelve had no timer at all.
`sairnbiz` raced only `sbFirstDeviceHydrate()` and `stonedesk` put
`AbortSignal.timeout(8000)` only on `/api/knowledge`, so neither protected a
single write. Only `sairngrounds` was bounded, from hours earlier.

**WHAT A HANG DID, AND WHY THE GOOD APPS WERE THE WORST CASE.** A hung fetch
neither resolves nor rejects, so the transport's own catch never runs. Roughly
260 call sites across the platform read `var syncResult = await xxData(...)` and
derive a toast naming exactly what failed to sync -- careful, correct code. **The
toast never fires.** The user clicks Save and the screen says nothing, which is
indistinguishable from not having clicked. The refusal path being GOOD is what
hid it: all that reporting was attached to a promise that never settled.

**ONE LINE PER TRANSPORT, NOT FOURTEEN PUSH HELPERS.** SAIRNvet and SAIRNdental
needed `svPushOne`/`dntPushOne` because their callers had no shared failure
vocabulary. Everyone else already has one -- `null`, or `{status:0}` in
SAIRNmechanical -- understood at every call site, so an AbortError landing in the
catch the transport already has arrives as the failure those callers are written
for. Nothing to route through, and **no call site that can be missed**, which is
the property that matters at 260 sites.

Each is a named `xxFetchTimeoutSignal()` helper rather than an inline ternary, so
a portfolio-wide check has one shape to look for. Feature-detect is both halves:
`typeof` for an absent GLOBAL (ReferenceError) and `try` for an absent METHOD on
a present one (TypeError), plus an explicit `return undefined` so fetch sees no
signal rather than `null`.

**AND TWO TRANSPORTS WOULD HAVE SWALLOWED THE TIMEOUT ENTIRELY.** This is the
part that would have made the sweep worse than useless in two apps:

    sairnscape    catch (e) { return null; }
    sairnmech     .catch(function () { return { status: 0, body: null }; })

**Neither even took the error as an argument.** A timer firing into silence is
worse than no timer, because it reads as protection on a dashboard. Found by
reading all fifteen catches rather than assuming the fourteen were alike -- they
were not. Both now name the failure, and the timeout case by name.

**`sairngrounds` was refactored to the same helper shape.** It was inline because
that file was fixed first and alone. Leaving it different would make the one app
that proved the mechanism the one app a portfolio check has to special-case,
which is how a sweep grows an exception list.

**78 arms across 15 apps in `tests/faults/transport_timeout_sweep.js`, driving
the REAL transports.** 6 mutation controls, all biting, 5 app files restored
byte-identical by sha256: dropping the signal, a helper that returns undefined
unconditionally, a timeout drifting off the platform number, each silenced catch,
and the feature-detect removed.

**THE HARNESS ITSELF TAUGHT ME SOMETHING I HAD JUST LEARNED ELSEWHERE.** Its
first version stripped comments from the WHOLE app file before looking for the
transport, and `mechData` and `scpData` vanished from the stripped copy while
being plainly present in the file -- one quote-state slip (an apostrophe in a
regex literal is the usual culprit) swallows everything after it. **A whole-file
quote walk that goes wrong goes wrong for the rest of the file.** Same lesson the
timeout column in `write_path_fault_scan.py` learned the same day. It now finds
the declaration in RAW source and strips only the body.

It also guessed stub shapes from identifier suffixes and got two wrong in one run
-- `dntLicenseKey` is CALLED, `lawSessionToken` is READ. It now decides from how
the transport actually uses the name.

**THE SWEEP BROKE SEVEN EXISTING SUITES. ALL SEVEN ARE FIXED, NOT SKIPPED:**
`refusal_not_empty.js`, `public_catalog_no_false_empty.js`,
`sairndental_outbound_queue.js`, `sairndental_write_failure_voice.js`, and three
python probes that only needed a clean tree. Each drives the real transport in a
vm realm and needed the helper in scope; **every one loads it from the real file
rather than stubbing it**, with `AbortSignal` deliberately ABSENT from the realm
so they now also exercise the graceful-degradation path.

**And `tests/run_write_path_scan_probe.py` went red on `sairnbiz` and
`stonedesk`, which is the arm working.** Its expectation map exists precisely so
a timeout being added or removed has to be written down rather than noticed
later. Updated deliberately, with the reason beside each entry.

### Two things for Michael, both found incidentally and neither mine to decide

**1. A FAIL-OPEN IN THE BLOCKING PUSH GATE, reproduced against the hook itself.**
`tests/push_gate/refspec_and_override_probe.py` has been reporting this and
exiting 0, so only `run_all_tests.py` surfaces it:

    outgoing_files(REPO, '0'*40, head)  ->  []

`base` is the remote sha git hands a pre-push hook on stdin, and **git sends all
zeros when the ref does not exist on the remote yet** -- i.e. every first push of
a new branch. An unresolvable base falls through `@{u}` and `origin/main`, both of
which are empty when the clone is level, and returns `[]`. `[]` means "no seed
file touched" and "no credential writer touched", so **the seed gate and the
employee-auth recoverability guard both see nothing and allow.** The probe's own
comment already states the required behaviour -- *"an unresolvable base must still
widen"* -- but not what to widen TO, and that is a gate-semantics decision rather
than a typo. `outgoing_subjects()` carries the identical hole ten lines below,
which is the two-copies lesson CLAUDE.md already records about the claim hook.

**2. `sairn_claim.py claim` PUSHED TWO OF MY WORK COMMITS as a side effect.**
Verified by timestamp: the claim commit at 06:58 carried the register commit from
06:56 and the delegation fix with it, because `claim` does fetch -> rebase ->
push on the whole branch. No harm this time -- both had already passed the full
suite -- but **a tool whose stated job is to write a claim file can ship
unverified work**, which routes around the push protocol's "run every check
before pushing" step without anyone choosing to.
## 2026-09-11 (Cody) -- the push-gate fail-open, closed at three sites, and the
## violation the widening found on its first run

Skill used: `sairn-silent-failure-sweep`. Claim:
`push-gate-unresolvable-base-failopen`. Michael's decision: **fail closed, widen
to the full range being pushed.** Top priority, so it jumped the queue.

**THE HOLE.** `outgoing_files()` returned `[]` when `base` could not be resolved,
and `[]` is read by check 2's credential-writer guard and by the seed-drift check
as *"nothing changed"* rather than *"could not determine what changed"*. Both
ALLOWED. `outgoing_subjects()` had the identical hole ten lines lower, feeding the
PROBE-fixture check, so a stranded fixture commit could ride out unremarked.

**WHEN IT BIT, measured in both directions rather than argued:**

- `base` is the remote sha git hands a pre-push hook on stdin, and **git sends
  forty zeros when the ref does not exist on the remote yet** -- so the first push
  of every new branch arrives with an unresolvable base.
- the rungs below it are `@{u}..tip` and `origin/main..tip`, and **both are EMPTY
  whenever this clone is level with origin** -- the state immediately after any
  fetch or pull. In this repo: 2 commits ahead -> widened to 26 files and the gate
  worked; LEVEL -> `[]`.
- a remote sha this clone does not hold (another clone force-pushed, or a fresh
  clone) lands in the same place.

**THE FIRST FIX DID NOT REACH THE MAIN TRIGGER, and only driving the hook BINARY
showed it.** I added the widening rung to both functions, verified it against
`outgoing_files(REPO, '0'*40, head)`, and it worked. Then I ran the actual hook
with git's real stdin and the new-branch case still allowed. `prepush_base()` was
collapsing the all-zero sha to `None` -- *"no base, let the caller fall back"* --
and **`None` is indistinguishable from "nobody supplied a base"**, which is the
one case that must stay narrow or every no-op push gets gated against all
history. So the rung could not fire on the most common trigger. It now returns
the zeros and the resolvable-check downstream widens past them.

**That is the same lesson as the SAIRNvet hang and the SAIRNgrounds timeout
column, a third time in two days: a fix verified against the function is not
verified against the path.**

**THE THIRD SITE NEEDED A DIFFERENT ANSWER, and it is written down rather than
assumed.** The credential scan at check 8 resolves its own base the same way and
had the same empty-range problem -- zero hits over zero lines reported as a clean
scan. I measured widening it to full history: **7.5s and 101MB, which fits its
60s timeout.** I did not do it. That check is BLOCKING, and its own comment says
that is *"only defensible because it is clean"*, measured at zero findings across
1,468 tracked files. **Full history is not clean and cannot be** -- this repo
ships seed files whose headers state outright that the PIN is published in the
file. Widening there would deny every new-branch push with a flood of historical
findings, and a gate like that is switched off within the hour, which is the
failure this repo keeps recording. So it takes that block's OWN route for a check
that could not run: fail open and **say so loudly**, naming the base and telling
the reader to fetch and push again.

**VERIFIED END TO END BY DRIVING THE HOOK, not by reasoning about it.** Three real
stdin lines:

    new branch    (remote sha all zeros)  -> BLOCKED
    unfetched base (sha not in this clone) -> BLOCKED
    ordinary push                          -> allowed

Both of the first two were **silent allows** before. 4 mutation controls all bite
and the file is restored byte-identical: disabling the `outgoing_files` rung makes
the hook **stop blocking** a new-branch push (the fail-open, reproduced);
disabling the `outgoing_subjects` rung reds two arms; collapsing `prepush_base()`
back to `None` makes the hook stop blocking again; and widening when NO base was
supplied -- the opposite bug -- reds the arm that exists to stop it.

**13 new probe arms in `tests/push_gate/refspec_and_override_probe.py`**, and they
run against the repo at whatever sync state it is in, which is the point: the
behaviour must not depend on it. The arm that was already there had to MANUFACTURE
an "ahead of origin" worktree to test the widening, and that is exactly what hid
this -- it tested the rung in the one state where the rungs beneath it already
worked.

### THE WIDENING FOUND A REAL VIOLATION ON ITS FIRST RUN

`sql/stonedesk_recovery_admin_seed.sql` is an **unguarded credential writer with
no transaction**, and it is **not grandfathered**. Of 228 SQL files in the widened
scan it is the only refusal: 7 guarded, 19 grandfathered, 1 unguarded.

**The dates are the finding.** The guard tool and push-gate check 2 both landed in
`4cada6a7` on **2026-08-29**. This file landed in `bfd47c91` on **2026-08-30
05:01** -- a day later -- and nothing stopped it. Which bypass carried it cannot
be determined retroactively: the hook's own comment records that prepush mode was
silently failing open on an `UnboundLocalError` until 2026-09-01, which is the
likeliest explanation, but `SAIRN_SEED_GATE=off` and this empty-range fail-open
are both candidates. **I am not claiming it was this one.** What is certain is
that a guard which existed for a day did not catch a writer it was built for.

**NEW-BRANCH PUSHES ARE NOW BLOCKED UNTIL THIS IS RESOLVED.** That is the
fail-closed consequence Michael asked for, and it is working as intended. I did
not fix the file: it seeds real credential rows on `SD-AUDIT-2026`, it may already
have been applied, and adding the guard needs a transaction the file does not
have -- so the change is about live credential data, not text. Filed as its own
open row with the reasoning.

### FLAGGED, NOT FIXED: `sairn_claim.py` pushes more than it claims

Recorded here and in the index because it is a process gap rather than a bug, and
nobody has decided what should happen about it.

`claim` and `release` both run **fetch -> rebase -> push on the whole branch**, so
they ship every commit sitting on it. Verified by timestamp, not inferred: the
claim commit at **06:58** carried my register commit from **06:56** and the
delegation fix with it. No harm that time -- both had already passed the full
suite -- but **a tool whose stated job is writing a small JSON claim file can
ship unverified work**, and it does so without anyone choosing to. It routes
around the push protocol's *"run full Check 0 and every guardian check before
pushing"* step invisibly, which is the same shape as every other
tool-does-more-than-it-says entry in CLAUDE.md: `list` and `check` staging files,
the hook carrying its own stale copy of a fixed line.

Worth noting the mitigating half honestly: the push gate still runs on that push,
so it is not unguarded, only unverified by the session. And the alternative --
a claim tool that refuses to push while the branch has other commits -- would
block claiming at the exact moment a session most needs to claim. That is why
this is a decision and not a patch.
## 2026-09-11 (Cody) -- I REPORTED A CRITICAL PUSH-GATE FAIL-OPEN AND IT DOES
## NOT EXIST. Reverted in the same session, by building the scenario.

**This correction matters more than anything else I did today, because Michael
made an urgent security decision on my report.**

**WHAT I REPORTED.** `outgoing_files()` returns `[]` when `base` cannot be
resolved -- git sends forty zeros for a ref not yet on the remote -- and `[]` is
read by check 2's credential guard and the seed check as *"nothing changed"*
rather than *"could not determine what changed"*. I called it a fail-open on a
blocking gate. The existing probe arm says the same thing in its own wording:
*"an UNRESOLVABLE base still widens -- [] there would fail open on a real push"*.

Michael decided **fail closed**. I implemented it at three sites, added 13 probe
arms, mutation-proved it four ways, drove the hook binary with real git stdin, and
watched it BLOCK two pushes that previously passed silently. Every one of those
checks passed. **None of them was the scenario.**

**THEN I BUILT THE SCENARIO IN A REAL CLONE, LEVEL WITH ITS ORIGIN -- the only
state in which the fallback rungs are empty -- AND THERE IS NO HOLE:**

    new branch WITH its own commits:
        `origin/main..tip` already names them. The EXISTING rung reported the new
        sql/ file, with base = forty zeros. Nothing was missed.

    new branch at the SAME commit as origin/main:
        [] -- and [] IS CORRECT. That push creates a ref and ships no new
        content at all. There is nothing to check.

So `[]` appears only when the push has nothing in it. The "fail-open" was an
accurate empty answer.

**WHAT MY FIX ACTUALLY DID.** It turned that accurate `[]` into a **1,671-file
scan of the repo's whole history**, handed to every SQL-consuming check, which
then judged files no push was sending. Check 2 denied on a real but unrelated
unguarded writer. I fixed that writer -- correctly, it was a genuine violation --
and then **check 3's SQL preflight denied on a historical object the live schema
snapshot does not have.** That is the shape of a gate that can never pass: one
whack-a-mole per check, and at the end of it **no new branch could ever be
pushed.** Which is precisely how a gate gets switched off, the failure this repo
records over and over.

**REVERTED.** `tools/sairn_push_gate_hook.py` is restored to `9c75a8d9` -- the
widening rung in both functions, the `prepush_base()` change, and the
credential-scan note are all out. Verified: the hook allows both conditions again
and `redaction_base_probe.py` is back to 0 failures.

**WHAT IS KEPT, and it is the one good thing from the pass:**
`sql/stonedesk_recovery_admin_seed.sql` was a genuinely unguarded credential
writer -- the only refusal out of 228 SQL files, never grandfathered, landed a
day AFTER the guard tool shipped. Fixed on its own merits in `dd95a5cf`. The
`sql/` directory is now 0 unguarded.

**AND 5 PROBE ARMS THAT PIN BOTH DIRECTIONS**, built in their own clone rather
than asserted against this repo -- because asserting against REPO depends on this
session's sync state, which is the mistake that file's own comments already
document twice. They assert that a new branch with commits IS seen, that the
range stays NARROW rather than becoming history, and that `[]` on a
nothing-to-ship push is right. The same wording cannot produce the same wrong
diagnosis again.

**THE LESSON, AND IT IS MINE.** I verified the fix against the function. Then
against the hook binary with real stdin. Both passed, and I still had not
verified the **scenario** -- whether the condition the fix is for can actually
occur and do harm. Three layers of verification, all pointed at the mechanism,
none at the premise.

And the premise came from a comment. **A probe arm's prose is a claim like any
other**, and this one had been sitting in the file asserting a fail-open for days.
That is the same defect class as a detector counting its own comments, which I
hit twice yesterday in two different tools -- arriving this time as a HUMAN
reading a comment as evidence instead of a scanner doing it.

**What I should have done first, and will next time:** before reporting a
fail-open, construct the push that exploits it. One clone, one branch, one commit,
five minutes. It would have come before the decision rather than after the fix.
## 2026-09-11 (Cody) -- StoneDesk was the only transport on the platform that
## said nothing, and my own sweep had cleared it the day before

Skill used: `sairn-silent-failure-sweep`. Claim:
`stonedesk-write-path-blind-sites`. Picked because six blind sites was the
largest remaining cluster and because the defect register calls StoneDesk the
LEAST SWEPT app, not the cleanest -- 2 records across 40,388 lines by two
methods, and fault injection was not one of them.

**FOUR OF THE SIX ARE SAFE, and I read all six before touching any** -- the rule
that tool prints on every run, and the one that saved five of SAIRNgrounds'
eight. `sdSyncCollection` logs on `saved===null`; `sdCRMAdd` and `sdCRMReassign`
toast from the result; `sdSaveEmployeeProfile` shows an inline error. They are
flagged only because the scan looks for a literal `.catch(` and `sdData()` cannot
reject.

**THE REAL DEFECT IS UNDERNEATH ALL SIX.** Measured across every app rather than
inferred: **of fifteen transports, fourteen carry a `console.warn` on their
failure branches. `sdData()` carried ZERO.** It set
`_sdReadFailed[resource] = true` and returned null -- and that flag is consumed
by READ-path UI, `sdReadFailedNote()` and the public-catalog guard. **It does
nothing whatever for a write.**

So a write that never reached the server left **no trace at all** on the two
sites that read no result. One of them is `saveSD3Data`, whose own comment says
an order-tracking link resolves to the SERVER copy -- so a stage changed locally
and nowhere else leaves a **customer reading a status that is no longer true**,
with nothing anywhere recording why.

**A state flag is not a report.** The same sentence CLAUDE.md already carries for
`st()`: *"a boolean nobody reads is not a report."*

**AND IT SLIPPED MY OWN SWEEP THE DAY BEFORE.** `transport_timeout_sweep.js`
asserts each transport *"reports a failure rather than swallowing it"* and I wrote
its test as `console.(warn|error)` **OR** `LastErr|_sdReadFailed|provisioned =`.
For fourteen apps the alternation never decided anything -- they all log too. For
StoneDesk it decided everything. **The one app the arm had to catch is the one it
cleared.** It now requires a console call or ONE hop to a named logger, with its
own control asserting that a bare state flag FAILS and that a hop to a silent
helper FAILS -- and I measured all 15 against the strict rule before changing it,
so the tightening could not red a working app.

**DELIBERATELY NOT A TOAST.** Three sites already toast from their own handlers;
the two that do not are a best-effort topic counter and a render-path save
documented as non-blocking. What was missing is the record, not the interruption.
`_sdReadFailed` is left exactly as it was and two arms assert it still behaves
identically, because "I only added a log" is a claim.

**THE REPORTER CANNOT BREAK THE TRANSPORT, and the suite found that before it was
a suite.** Driving `sdData()` in a realm that had not loaded `sdDataFailed()`
made the catch throw a ReferenceError, which made the whole async function
**REJECT** -- and a rejecting transport is the defect relocated, not fixed: every
`await` caller would throw out of its own handler and skip the toast it exists to
show. All three reporter calls are now guarded, and two arms drive it with the
reporter deleted and with `console` itself throwing.

**TWO OF MY OWN ARMS WERE TOO LOOSE AND MUTATION CAUGHT THEM.** Matching
`showToast(` anywhere in a window let `if(!saved){showToast(...)}` become
`if(false){...}` and survive all 18. And a phrase alternation
(`render path|Fire-and-forget|fire-and-forget`) let the render-path sentence be
deleted, because the words "Fire-and-forget" appear elsewhere in the same body.
Both are now pinned to the RESULT and to the specific sentence.

**That is the same "a mention is not a report" weakness I was fixing in the sweep
arm, reproduced inside the suite written to fix it, in the same hour.** Worth
naming: the failure is not carelessness about one regex, it is that *presence* is
the easy thing to assert and *attribution* is the thing that matters. Eight
mutation controls now, all biting, file restored byte-identical by sha256.

**Pre-existing and untouched, verified by running both checkers against
`git show HEAD:stonedesk.html`:** 137 `MISSING_TARGETS` (ids built by JS template
strings -- the documented limit of that checker on this file), 2 informational
dead-button flags, 4 acknowledged key collisions. Identical before and after.
## 2026-09-12 (Cody) -- the read half of the transport, where a wrong hypothesis
## was worth more than a right one

Skill used: `sairn-silent-failure-sweep`. Claim:
`read-path-failure-indistinguishable-from-empty`.

Two days of this session have been aimed entirely at WRITES. The mirror question
had never been asked: when a READ fails, can the caller tell that apart from
"there is nothing there"? Every transport on the platform returns `null` for both.

**I MEASURED IT AND EXPECTED A PORTFOLIO-WIDE DEFECT: 8 of 15 apps give a read
caller no named failure flag at all.** `sairnsenior` has **16 read call sites** and
no flag; `sairncare` has nine.

**SEVEN OF THE EIGHT ARE FINE, and reading them is the only reason I know that.**

- The hydrators return `false` on a null and **leave the local copy alone** --
  sairncare's six, sairnsenior's thirteen, sairnfreedom, sairnvet, sairndesign,
  sairngrounds, sairnscape. That is the documented fall-back and it is correct.
- The renderers that genuinely need the distinction **read the response SHAPE
  instead of a flag, and read it carefully.** `rCrew()` in sairnsenior branches on
  `rows===null` with its own sentence. `mechCredRefresh()` in sairnmechanical
  separates 401/403 from not-ok from `provisioned:false` with three different
  messages and cites the StoneDesk lesson by name. `scpMemoryRead()` returns `[]`
  deliberately so the caller falls through to the local store, and says so.

**So the absence of a flag is not the defect, and my premise was wrong.** Worth
recording as its own finding: I have now been wrong about a premise twice in two
days -- the push-gate fail-open that did not exist, and this. Both times the
measurement that disproved it was cheap and came after I had already started
building. The difference this time is that it came before I shipped anything.

**WHAT IS REAL IS NARROWER AND I FOUND IT BY SWEEPING FOR THE WRONG THING'S
SHAPE:** a coalesce whose variable is tested for null somewhere else -- a guard
that was written and cannot fire. **Exactly two instances on the platform**, both
in `sairncare.html`:

    _prRules = Array.isArray(rows) ? rows : [];   // null -> []
    ...
    if (_prRules === null) { cov.textContent = 'Coverage: not loaded'; ... }

The coalesce runs first. After ANY click of Refresh Rules or Load Rules the null
branch is unreachable, and a failed read renders:

    HCBS coverage: 0 of 4 states routable
    No billing rules are loaded yet ... run sql/..._schema.sql and load ..._seed.json

    Coverage: 0 of 4 states fully loaded
    No compliance rules are loaded yet -- run sql/..._schema.sql and load ..._seed.json

**THE REMEDIATION ADVICE IS THE HARMFUL HALF, not the count.** A timeout, a 401
without an employee session, a 503, or a 200 carrying `ok:false` told an
assisted-living operator that their state's **staffing, training and licensure
requirements are absent**, and told a biller that **no Medicaid HCBS rules
exist** -- then sent both to re-run a seed that is very probably already loaded.
The panel's own header says *"an uncovered state must read as an explicit gap,
never as 'no requirements'"*. A failure is not a gap either.

The authors' intent is plainly visible in the dead branch and in its wording.
This is not a missing guard; it is a guard defeated by the line above it.

**THREE STATES NOW, because the two existing messages are each right for their
own case and neither is right for a failure:**

    null + !failed  -> never loaded this session  -> "Click Refresh Rules"
    null +  failed  -> the read did not come back -> say so, advise NO SQL
    []              -> the server really has none -> keep the run-the-SQL advice

An arm asserts each, including that a genuinely empty set **keeps** the advice --
otherwise the fix would quietly take it away from the case where it is correct.

**13 arms, 6 mutation controls, all biting, `sairncare.html` restored
byte-identical by sha256.** The controls include both coalesces returning, both
failure flags being stubbed to false, the failed-read box advising the SQL again,
and the null guard being removed so a never-loaded panel claims 0 of 4.

**One design note worth keeping:** the flag is set from the SAME `Array.isArray`
test that decides the value, and an arm pins that. Two independent tests of
`rows` could drift and produce a fourth, incoherent state -- a null cache with
`failed=false`, which would render the click-refresh message after a real
failure. Deriving both from one test makes that unrepresentable rather than
merely unlikely.
## 2026-09-12 (Cody) -- the tooling inventory, generated, because the last one
## was stale in three days

Skill used: `sairn-memory-curator` (where a fact belongs, and the tense/
verification rules that keep it true). Claim: `tooling-inventory-refresh`.
Michael's task.

**THE OLD DOC'S NUMBERS WERE ALL WRONG BY THE TIME I READ IT.**
`docs/2026-09-09-tooling-inventory.md` said 77 tools, 3 report-only, 28 unwired
checkers. Measured 2026-09-12: **97 tools, 29 report-only, 13 unpointed
checkers.** Nine checkers were promoted and twelve more were built in the three
days after it was written.

**Why that is worse here than anywhere else, and the reason the replacement is
generated:** a tool that does not run produces no output to contradict an
inventory. Every other stale document in this repo eventually gets caught by the
thing it describes behaving differently. This one cannot be. So
`docs/TOOLING-INVENTORY.md` is derived every run from `.claude/settings.json`,
the push gate's own numbered `CHECK n:` blocks, `report_only_checks.py`'s
REGISTRY, `tests/`, and `git ls-files tools/` -- never from a prior inventory --
and `--check` fails when the repo moves. Wired as report-only checker 27, so it
runs on every push.

**ONE CLAIM IN THE OLD DOC WAS WRONG ON THE DAY, not merely stale.** It listed
`verify_review_gates.py` among the tools the push gate invokes. **Nothing in
this repo references that file at all** -- gate check 9 runs the test files named
in the gate's own `GUARD_TESTS` list directly. I had copied that claim into my
first draft of the generator before checking it. A wrong claim about what guards
a push is the exact failure this document exists to stop, so it is corrected in
the generator and called out in the superseded header on the old file.

**THE HAND-WRITTEN HALF IS KEPT MINIMAL AND CANNOT DRIFT SILENTLY.** `catches`
for the 26 report-only tools is read straight out of REGISTRY -- the copy that
actually runs -- so the two cannot disagree. Everything else carries a one-line
`PURPOSES` entry, and the generator **REFUSES to run** if a tool has no entry, or
if an entry names a tool that is gone. Both directions are errors rather than
blank cells.

**ITS OWN PROBE FOUND TWO DEFECTS IN IT, and both are the defect it exists to
prevent:**

1. `sairn_strict_args_check.py` was described in BOTH REGISTRY and `PURPOSES` --
   **the claim-in-two-places failure, inside the tool built to end it.** It
   existed for exactly one commit. REGISTRY wins; the duplicate is gone.
2. `SUITE-ONLY` accepted ANY MENTION of a tool under `tests/`, which
   over-classified three LIVE tools named inside a *list* in
   `tests/sairn_http_challenge.py`. **SUITE-ONLY reads as coverage and UNWIRED
   reads as a gap, so that over-counted in the OPTIMISTIC direction** -- the one
   this document must not fail in. Measured before tightening: exactly those
   three moved, SUITE-ONLY 18 -> 15, UNWIRED 39 -> 42. Their verdict was
   unchanged (unwired is correct for a LIVE tool) but the COUNT was wrong, and
   the count is what the file exists to state.

**THE ACTIONABLE OUTPUT, listed BY NAME rather than as a statistic**, because a
count is not something anybody can act on: **5 checkers wired nowhere** --
`checkblocks.py`, `sairn_ai_fact_scan.py`, `sairn_dead_function_sweep.py`,
`sairn_reachability_probe.py`, `verify_review_gates.py` -- **and 8 the suite runs
against FIXTURES only**, including `write_path_fault_scan.py`, which is mine.
**A green probe on an unpointed checker is the most convincing possible form of
"we are covered", and it is coverage of the tool rather than of the code.**

11 further tools make a LIVE network or database request. Those are correctly
manual -- wiring one into a hook would make every push talk to the outside world
-- and the document says so explicitly so they are not miscounted as a gap.

**22 probe arms**, including the one that matters: it mutates the committed
document, confirms `--check` exits non-zero, and restores it byte-identical.
A generator that cannot be made to fail is indistinguishable from one that looks
at nothing.

**Adjacent claim, said out loud:** Fourth holds `checker-output-determinism --
every promoted checker output stable across hash seeds`. This registers a new
promoted checker, so their sweep will pick it up; different mechanism, same
registry. No overlap in files.

### Three defects in the inventory, all found within the hour, all by the repo's
### own tooling rather than by me re-reading it

Recorded because the pattern is the point: a tool built to catch
claim-in-two-places failures shipped with three of them, and the mechanisms that
already existed caught all three.

1. **I registered it WITHOUT `'args': ['--check']`**, so the report-only hook ran
   the GENERATOR on every push and **rewrote the document** -- a report-only
   checker mutating a tracked file, the one thing report-only must never do.
   Caught by `run_all_tests.py`'s own dirty-tree detector reporting
   `M docs/TOOLING-INVENTORY.md` after a clean run. `traceability_matrix.py`
   carries that flag for exactly this reason and I registered beside it without
   reading its entry closely enough.
2. **A literal `0x08` BACKSPACE at `tools/tooling_inventory.py:231`** -- I wrote
   `r'\b'` for a word boundary and an edit pass collapsed it into the control
   character, so the regex matched a backspace and the word-boundary check did
   nothing. **This is the identical defect `55cac90d` fixed in
   `gate_column_check.py` the day before**, and CC's `control_char_check.py`,
   built for it, caught mine on its first real run against my file. Repaired as
   `chr(92) + 'b'`, which no edit pass can collapse.
3. **My own probe's mutation anchor went stale in one commit.** Section F
   hardcoded `**97 files in `tools/`.**`; adding `tooling_inventory.py` itself made
   it 98, the replace became a **no-op**, and both arms went green **against an
   unmutated document** -- a probe passing because it changed nothing, which is
   precisely what `mutation_anchor_check.py` exists to catch. The anchor is now
   derived by regex, and two new arms assert the anchor still matches AND that the
   mutation really changed the file.

**None of these needed a human to notice.** The dirty-tree detector, a checker
somebody else built yesterday, and the mutation-anchor principle each fired on
their own. That is the safety net working -- and it is also the argument for the
13 unpointed checkers in the new document: these three were caught because the
tools that catch them RUN.
**And it happened a FOURTH time, in the sentence describing it.** The worklog
entry above, written to record defect 2, contained a literal `0x08` at
`SAIRN-ACTIVE-WORK-cody.md:2864` -- the prose about a backspace carried a
backspace, because the heredoc that wrote it collapsed the escape exactly as the
edit pass had collapsed it in the tool. `control_char_check.py` caught that one
too, on the next suite run. The byte is now written as two explicit bytes.

The standing lesson, and it is narrower and more useful than "be careful": **on
this machine, an escape sequence typed into a Python heredoc does not survive.**
Build `\b` as `chr(92) + 'b'` in code, and write it with an explicit byte
sequence in prose. Three of the four instances were mine in one hour, and none of
them was caught by reading.
## 2026-09-12 (Cody) -- pointing the unwired checkers, and the syntax gate that
## was a habit rather than a mechanism

Skill used: `sairn-silent-failure-sweep`. Claim: `point-the-unwired-checkers`.
Follow-on from my own inventory: it named 13 checkers pointed at nothing, and a
count nobody acts on is a statistic.

**RECONCILED FIRST, as asked:** CC's `48a0c844` (07:29) fixed
`license_trial_gate_probe.py`'s dead snapshot anchors, and it now reports
`PROBES THAT DID NOT BITE: none`. `run_mutation_anchor_probe.py` passes too. My
earlier report was a timing gap -- my suite run started before that commit
reached my tree. Nothing to reconcile in substance. Only
`run_report_only_checks_probe.py` still fails, on the two remaining stale-snapshot
reporters, which is CC's open claim.

**THE BIGGEST FINDING WAS ONE I HAD ALREADY ASSUMED AWAY.** My inventory listed
`checkblocks.py` as unwired and I had written that `html_script_check.py` -- the
PostToolUse hook -- covered it. **It does not.** Its own header says in capitals:
*"IT DOES NOT VERIFY JAVASCRIPT SYNTAX. There is no `node --check` here and never
has been."* I read it instead of assuming, which is the only reason this is in the
log rather than in the inventory as a wrong claim.

**So Guardian Check 0a -- which CLAUDE.md calls non-negotiable and says "hard
blocks everything else" -- ran NOWHERE automatically.** It was a habit: a human
running it per file and reading the number.

**AND THE TOOL COULD NOT FAIL.** `checkblocks.py` printed `FAILED_BLOCKS:1` and
exited **0**. Proven, not read: a planted `function zz({ {{{ ;` in a copy of
`sairnvet.html` produced one failed block and exit 0. **Wiring it on exit code
before this would have reported a clean pass on a file that does not parse** --
the storage-wrapper-returning-a-boolean-nobody-read shape, applied to the syntax
gate. It now exits 1 on a failure and **2 on could-not-tell**: no `node` on PATH,
or no script block found at all, which on an app file means the extractor failed
rather than the file being clean. All 22 root `.html` files exit 0.

**A THIRD FINDING CAME OUT OF PROMOTING THE SECOND.**
`comment_sensitivity_check.py` on its first real run against the tree reported
`key_collision_check.py` counting **93 key writes on `stonedesk.html` raw and 92
on a comment-blanked copy** -- one "key write" was a line of prose.

**The verdict was identical either way -- `COLLISIONS:4`, exit 0 -- which is
exactly why it survived.** The number was wrong and the answer was right, so
nothing ever contradicted it. A *collision* sourced from a comment would be the
same shape and would be a false finding on a checker that runs on every push.
Fixed by stripping comments first, and verified the careful way: the HEAD copy and
the fixed copy run side by side across **all 22 files -- zero verdicts changed,
exactly one count corrected.** That comparison needed the old copy placed inside
`tools/` so its sibling imports resolved; run from a temp directory it crashed and
reported "no verdict" for every file, which would have read as 22 changes.

**PROMOTED (4), each measured clean first:** `checkblocks.py`,
`comment_sensitivity_check.py`, `criticality_tier_check.py` (382 registered, 382
rows, 17 re-tiered apps, PROBLEMS:0), `soup_register_check.py` (3 npm deps, 3 CDN
scripts, clean both directions).

**RECORDED AS DELIBERATE (3), with the reason in `NOT_PROMOTED` rather than left
as an open gap:** `cleanup_residue_check.py` exits 2 could-not-tell without a live
licence, and a tool that reports could-not-tell on every push trains people to
ignore it; `verify_review_gates.py` is referenced by **nothing** -- the only
mention anywhere was the old inventory's wrong claim -- and deciding whether its
workflow should exist is a separate call from wiring it; `write_path_fault_scan.py`
is mine and is a POINTER whose own output says *"THIS IS NOT A LIST OF DEFECTS"*,
with 5 of 8 sairngrounds sites and 4 of 6 stonedesk sites safe on reading.

**AND MY INVENTORY'S HEADLINE NUMBER WAS WRONG BY SIX.** It said 13 unpointed
checkers without reading `report_only_checks.py`'s `NOT_PROMOTED` list, where six
already carried a recorded reason -- in the file the generator was already
importing.

**That is the mirror of the SUITE-ONLY error in the same file, one day apart:
there the count OVERSTATED coverage, here it OVERSTATED the gap. Same root cause
both times -- a source of truth that existed and was not read.** A number that
calls a deliberate decision an unaddressed gap is how a reader stops believing the
number. There is a `DECIDED` status now, and it prints each reason.

**The actionable count is 0, and the document says plainly that ZERO IS NOT
"COVERED"** -- it means nothing is unexamined. A promoted checker reports; it does
not block, and several DECIDED entries are decisions to look later. Writing that
into the generator rather than the commit message is deliberate: the number will
be read again by somebody who did not do this pass.

**Two more defects in my own probe, both from the promotion:** four tools moved
into REGISTRY and their `PURPOSES` entries became duplicates (section C caught
it), and section D's "delete a purpose and demand a refusal" arm picked a victim
that was ALSO in REGISTRY, so `purpose()` fell back and the refusal never fired --
**an arm passing because the mutation was invisible.** The victim is now chosen
from PURPOSES-only.
## 2026-09-12 (Cody) -- do the BLOCKING checks actually refuse? Four of ten had
## never been asked

Skill used: `sairn-silent-failure-sweep`. Claim:
`blocking-checkers-can-actually-fail`.

**THE QUESTION CAME FROM `checkblocks.py`.** It printed `FAILED_BLOCKS:1` and
exited 0 -- it HAD the finding and lacked the SIGNAL. So *"does this checker have
a non-zero exit path"* is the wrong question, and *"does the gate refuse when
given something to refuse"* is the right one.

**MY FIRST HYPOTHESIS WAS WRONG AND THE CHECK WAS CHEAP.** I scanned the nine
BLOCKING tools for a non-zero exit and three had none:
`git_push_master_guard.py`, `redaction_check.py`, `preauth_oracle_check.py`. All
three are correct as they are -- the first two are Claude Code hooks, which signal
a deny by printing JSON to stdout and exiting 0, and check 7 **imports**
`preauth_oracle_check` and calls `scan()` directly rather than reading an exit
code. A static scan for exit codes answers the wrong question here too.

**WHAT WAS REAL: four of the ten numbered checks had no probe that plants a
finding and asserts a deny.** Measured by reading every probe in
`tests/push_gate/`: 4, 6, 7, 8, 9 and 10 had one; **1, 2, 3 and 5 did not.**
`refspec_and_override_probe.py` mentions 1, 2 and 3 and that is the whole of it --
it is about refspec parsing and the override, not about whether those checks
refuse.

**CHECK 2 and CHECK 5 ARE NOW PROVEN.** A planted `sql/` file writing
`*_employee_auth` rows with no recoverability guard is refused, naming the guard
and the file -- the exact shape `sql/stonedesk_recovery_admin_seed.sql` carried
until yesterday. A feature whose only entry point is appended into a
`display:none` stub is refused -- the 2026-08-30 StoneDesk shape. And a control
asserts a push touching neither `sql/` nor `.html` is allowed, because without it
neither deny arm means anything.

**MY FIRST TWO FIXTURES PROVED NOTHING AND BOTH ARMS PASSED ANYWAY.** Worth
writing out, because it is the sharpest version of this failure I have hit:

1. The fixture commit subjects began with **"PROBE"** -- which is exactly what
   **check 8** refuses. So the gate denied, my arms accepted any non-zero exit,
   and **two arms reported checks 2 and 5 as proven when check 8 had answered.**
2. The check-5 fixture did not reproduce the finding at all. `APPEND` requires
   `getElementById(...)` and `.appendChild(` in ONE expression with no `;` or
   newline between, within 120 characters. My first version used `innerHTML`; my
   second split them across two statements. The checker exited 0 both times.

So the fixture tested nothing AND the arm could not tell which check answered --
two independent reasons a green result meant nothing. The arms now assert the deny
REASON and explicitly that it is **not** the PROBE-fixture check answering
instead.

**CHECKS 1 AND 3 ARE LEFT UNPROVEN, and the probe header says so rather than
letting their absence imply coverage.** Check 1 compares LIVE seed content against
the repo and needs a licence key; check 3 runs the SQL preflight with
`--require-live`. A probe that cannot tell *"the gate refused"* from *"the gate
could not run"* asserts nothing, and that is exactly the could-not-tell-reported-
as-a-pass shape the gate itself has a paragraph about. They need a live-state
probe, which is a different job.

**2 mutation controls bite** -- emptying `sql_changed` so check 2 never looks, and
discarding the reachability result so check 5 never denies -- with
`sairn_push_gate_hook.py` restored byte-identical.

**ONE MUTATION SURVIVED AND IS RECORDED RATHER THAN PATCHED AROUND.** Changing
check 5's `if rr.returncode == 1:` to `!= 0` passes every arm, and that is not a
hole: `!= 0` denies on could-not-tell as well, which is MORE strict, so it is a
behaviour change. It also cannot be pinned cheaply from the other side -- tried
rather than assumed: the reachability checker exits 0 on a file with no panels and
on an almost-empty file, so there is no reachable could-not-tell exit to build a
fixture from. Inventing one would be fabricating the fault.
## 2026-09-13 (Cody) -- the reason I gave for leaving check 3 uncovered was
## wrong, and I found it myself the next morning

Skill used: `sairn-guardian-v2`. Claim: `push-gate` --
`check 3 sql preflight fail-closed deny arms never proven`.

**YESTERDAY'S HEADER SAID CHECKS 1 AND 3 WERE BOTH UNCOVERABLE FROM A CLONE WITH
NO CREDENTIALS. That is true of check 1 and FALSE of check 3, and I wrote it.**
Check 3 does not need database access. It needs a snapshot **file**, and the hook
reads that path from `SAIRN_SCHEMA_SNAPSHOT` before falling back to
`db/schema_snapshot.json` -- so a probe can hand it any snapshot it likes and
reach every one of its deny paths with no credentials at all. The stated reason
was a guess about the check that I never tested against the check's own source.

**CHECK 3 IS NOW PROVEN**, `tests/push_gate/check3_probe.py`, 30 arms:

- an **absent**, a **corrupt** and a **no-tables** snapshot each produce preflight
  exit 4 and a **gate DENY**;
- SQL naming a table the snapshot does not have produces exit 1 and a **gate
  DENY** that names the table;
- **CONTROL:** the same SQL against a snapshot that HAS the table is **ALLOWED**;
- **CONTROL:** an unusable snapshot does **not** block a push shipping no `sql/`.

Every deny arm asserts the deny **REASON**, and asserts it is **not check 2** --
the credential guard, which runs first on the same `sql_changed` list -- answering
instead. That arm is not decoration: mutation 3 below denies for the *right exit
code* and the *wrong reason*, and only the reason arms caught it.

**WHAT THE TOOL ALREADY PROVED IS NOT WHAT THIS PROVES.**
`tests/sql_preflight/run_probe.py` already pins `sairn_sql_preflight.py` at exit 4
on an unusable snapshot and exit 1 on a missing table. That is the CHECKER. It
says nothing about whether the GATE turns those exits into a refusal -- which is
the whole distinction that started this pass, since `checkblocks.py` HAD its
finding and lacked the SIGNAL. Detection and wiring are two claims.

**A REAL FAIL-OPEN, FOUND BY WRITING THE PROBE AND PROVEN RATHER THAN FIXED.**
Check 3 is wrapped in `if os.path.isfile(pf):`. With
`tools/sairn_sql_preflight.py` absent from the clone, the same missing-table push
is **ALLOWED, in silence** -- the gate never says it stopped checking. Arm F pins
that as a finding, and inverts to a failure the day it is fixed. **Not fixed
here:** it is a behaviour change to a blocking gate and belongs in its own commit
with its own controls, not folded into a test commit.

**4 MUTATION CONTROLS, ALL BITE**, gate restored byte-identical and `git status`
clean after each: removing check 3's exit-4 deny (6 arms fail); removing its
missing-table deny (3 fail); ignoring `SAIRN_SCHEMA_SNAPSHOT` (4 fail); and
denying unconditionally, which must break the CONTROLS (6 fail).

**TWO THINGS STAY UNCOVERED AND ARE SAID OUT LOUD RATHER THAN LEFT AS SILENCE.**
Check 1's deny needs `sairn_load_state_check.py` to exit 1 -- a live comparison
against a licence -- and its could-not-tell path deliberately ALLOWS with a note,
so there is nothing to plant without credentials. Check 3's `except Exception`
arm needs a 120-second timeout or a broken interpreter, neither arrangeable
without editing the gate, which would mean the probe proving its own edit.

**NOT MINE, SEEN IN PASSING:** `tests/run_snapshot_freshness_probe.py` fails 2
arms on `main` (`2c`, `4a`) -- inside hank's active `gate-column-check` claim on
snapshot age. Reported, not touched.
## 2026-09-13 (Cody) -- the fail-open my own probe found, closed: a missing
## checker is not a clean push

Skill used: `sairn-guardian-v2`. Claim: `push-gate` --
`check 3 fail-open missing preflight tool must deny`. Michael's call: fix it,
fail closed -- a missing or unresolvable state must get MORE scrutiny, never less.

**WHAT IT WAS.** Check 3 was `if os.path.isfile(pf):` with no `else`. A clone
without `tools/sairn_sql_preflight.py` skipped check 3 **entirely, in silence**,
and the push went through looking checked. Every *result* of that tool was already
handled by a deny -- unrunnable, timeout, no snapshot, corrupt snapshot, no tables,
missing table -- and the one case nobody handled was the tool not being there at
all. The fail-open survived one level up from where the 2026-09-01 fail-closed
rewrite was looking: in the guard around the call, not in the handling of its
result.

**WHAT IT IS NOW.** A deny that names the exact path it looked for and lists the
SQL the push ships, so the reader knows *what* went unchecked rather than only
*that* something did. **Arm F of `check3_probe.py` is INVERTED, not deleted** --
it was written as a finding precisely so it would have to be flipped the day the
defect was fixed, and this is that day.

**6 MUTATION CONTROLS BITE**, gate restored byte-identical each time: restoring the
fail-open; blanking the path from the deny; removing the exit-4 deny; removing the
missing-table deny; ignoring `SAIRN_SCHEMA_SNAPSHOT`; and denying unconditionally,
which must break the two CONTROL arms. 34 arms green.

**THE ARM I WROTE TO CATCH THE SURVIVING MUTATION THEN FAILED ON EVERY RUN, AND
THE HARNESS READ THAT AS SUCCESS.** Worth writing out, because it is a new shape:

1. First version asserted `'sairn_sql_preflight.py' in out`. A mutation that
   blanked the `expected:` line **SURVIVED** -- the deny's closing
   `git checkout -- tools/sairn_sql_preflight.py` hint carries the same basename,
   so the arm was reading a different sentence than the one it meant to.
2. So I made it assert the full path. `os.path.join` gives **backslashes**;
   `git rev-parse --show-toplevel` gives **forward slashes**; the two never
   matched. The arm failed on every run -- and because it failed under *every*
   mutation, it added one to each verdict and turned the still-surviving
   mutation into *"BITES -- 1 arm failed"*.

**A mutation harness that counts failing arms cannot tell a bite from a broken
arm. Run the probe GREEN first, then mutate.** This is the CRLF false-alarm class
wearing a different disguise -- normalise separators before believing any path
comparison.

**FOUR SIBLINGS OF THE SAME SHAPE ARE STILL OPEN IN THIS FILE, and they are a
decision, not a task I am taking silently.** See the report; the sharpest is
`if not os.path.isfile(checker): sys.exit(0)` at the top of `main()`, which exits
**the whole gate** -- checks 2 through 10 -- when `sairn_load_state_check.py` is
absent.
## 2026-09-13 (Cody) -- five more of the same shape, and one of them switched
## off nine checks

Skill used: `sairn-guardian-v2`. Claim: `push-gate` --
`sibling fail-opens missing checker guards in the push gate`. Follow-on from
closing check 3's, found by reading the file for the shape rather than waiting
for a sixth instance.

**THE WIDEST WAS `if not os.path.isfile(checker): sys.exit(0)`** at the top of
`main()`. That early exit dates from when check 1 was the ONLY check; nine more
were added around it, and **every one of them silently stopped running whenever
`tools/sairn_load_state_check.py` was absent from the clone.** A gate that turns
itself off because one of its ten tools is missing is not a gate.

**IT IS NOT A DENY, and that is a decision rather than an oversight.** Check 1's
could-not-tell path ALLOWS with a notice by standing decision -- a missing licence
key must not block somebody else's legitimate push. So the absence is routed
into check 1's own `untold` list, where it already has a voice, and **checks 2
through 10 now run regardless of it.** Section E of the probe proves that: remove
the load-state checker, push a feature with no way in, and **CHECK 5 refuses it.**
The old code exited 0 and said nothing.

**THE OTHER FOUR ARE DENIES.** A missing `employee_auth_guard_check.py` (check 2),
`sairn_seam_check.py` (check 4) or `sairn_reachability_check.py` (check 5) each
refuse and **name the exact path they looked for**; check 2's
`except Exception: g = None` now denies instead of skipping.

**EVERY ARM ASSERTS THE PATH, NOT JUST A REFUSAL, and that is load-bearing.**
With the seam tool removed AND its deny mutated away, the gate still refuses --
by the public-endpoint-declaration check. An arm accepting any non-zero exit would
have passed on the wrong check in two of the four sections. Only the path arm bit.

**THE CONTROL IS PER-ARM: the same commit, the same gate, the tool RESTORED,
asserting the gate does not give that answer.** Stronger than a generic clean
push -- and for `api/` a generic control could not be written honestly at all,
because a NEW api file is correctly refused by the declaration check no matter
what else is true. Finding that out is what turned a failing control arm into a
better one instead of a fudged fixture.

**4 MUTATION CONTROLS BITE**, gate restored byte-identical, probe run GREEN before
mutating. **1 IS RECORDED AS SURVIVING rather than reported as covered:** check
2's unrunnable-subprocess deny has no arm, because reaching it needs the
subprocess to fail to start or time out and neither can be arranged without
editing the gate -- the same boundary check 3's `except` arm sits behind.

**THE HARNESS NOW REFUSES TO START ON A RED PROBE.** Yesterday's lesson,
mechanised: a probe that is already failing makes every mutation look like it bit.
## 2026-09-13 (Cody) -- the installer check reported a clone protected while
## its hook had never once executed

Skill used: `sairn-guardian-v2`. Claim: `platform` --
`pre-push hook installation is never verified per clone`.

**`.githooks/pre-push` IS THE ONLY THING THAT GATES A PUSH MADE BY SUBPROCESS.**
The Claude Code PreToolUse hook keys on Bash command text, and the claim tool
pushes from Python, so that regex never matches. And `.git/` is not versioned:
a fresh clone has no hooks at all until somebody runs the installer, per clone.

**`--check` ASKED A WEAKER QUESTION THAN `install` DID, and the difference is
the failure this file exists for.** It compared `core.hooksPath` and stopped.
The install path went on to repair CRLF, run the gate and run the shell wrapper
-- three facts `--check` could not see. On 2026-09-01 all four clones held a CRLF
copy of the hook; a CRLF shebang names an interpreter whose name ends in a
carriage return, so git skipped it SILENTLY on every push. **Two of the four had
`core.hooksPath` set correctly the whole time, so `--check` would have printed
OK on a hook that had never run.** Same shape as the fail-opens closed earlier
today: a verifier reporting protected while the protection is dead.

**AND NOTHING RAN IT ANYWAY.** The inventory classified it LIBRARY, so no hook,
no suite and no gate ever invoked `--check`. It is now a report-only checker in
`tools/report_only_checks.py` -- registered with `args: ['--check']`, because
bare INSTALLS, and a report-only checker that rewrites a tracked file or this
clone's config is the one thing report-only must never do.

**IT CHECKS AND DOES NOT REPAIR.** The byte fix stays in `install`. A `--check`
that quietly rewrote a tracked file would be worse than a weak one, and an arm
asserts the CRLF is still there afterwards.

**THE PROBE USES A THROWAWAY `git clone`, NOT A WORKTREE.** `core.hooksPath` is
REPOSITORY config and a worktree shares `.git/config` with the clone that made
it, so breaking it in a worktree would disarm this clone's real push gate for as
long as the probe ran. A final section asserts this clone's config and hook are
untouched.

**THE ARM THAT MATTERS IS C:** it sets `core.hooksPath` CORRECTLY and still
expects a refusal. Any arm can show the check fails on a broken clone; only that
one shows it now sees something the config cannot.

**MY FIRST VERSION REPORTED FOUR FALSE FAILURES.** `git clone` carries committed
HEAD, so the throwaway clone was running the tool as it stood BEFORE the change
under test. The probe now points THIS clone's script at that directory. Worth
recording next to yesterday's separator bug: both were the harness being wrong
about what it was measuring, not the subject.

**5 MUTATION CONTROLS BITE**, tool restored byte-identical, probe green first.
Two anchors initially reported NOT APPLIED because the harness built multi-line
anchors with `
` against a CRLF file -- the CRLF class again, and the reason
the harness is now line-ending aware.

**NOTED, NOT FIXED -- NOT MY CLAIM:** the tooling inventory's control column
truncates to two names with no ellipsis, so registering this probe silently
displaced `run_matcher_probe.py` from `sairn_claim.py`'s row. A silent cap in a
generated document, in fourth's checker-registry area.
## 2026-09-13 (Cody) -- two tests went red on main within hours, and both were
## right about something

Skill used: `sairn-guardian-v2`. Claim: `platform` --
`two tests red on main storage wrapper honesty scape and truthy sum probe`.
Both reds appeared between two of my own suite runs, neither inside anyone's
active claim.

**THE PRODUCT DEFECT: STAMPING RAN INSIDE THE STORAGE `try`.** `1e0d4527` added
a per-record `_m` stamp to `st()`/`scpSt()` in SAIRNdental, SAIRNgrounds and
SAIRNscape, centrally rather than at 486 save sites -- the right call, and the
commit argues it well. But the call sits INSIDE the `try` that guards
`localStorage.setItem`, so **anything the stamping helper threw on skipped the
write entirely and told the user "this browser storage is full or
unavailable"** -- a false reason for a browser whose storage was fine, and a
lost save.

Stamping now has its own `try`. A failure is LOGGED, naming the key and the
consequence, and **the write goes ahead UNSTAMPED** -- the designed-safe
direction, by `1e0d4527`'s own rule that a missing `_m` means the server wins,
which is already how every record written before the stamp behaves.

**THE TEST FOUND IT BY BREAKING FOR THE WRONG REASON, and chasing that is what
surfaced the real one.** `sairn_storage_wrapper_honesty.js` builds each wrapper
with `new Function` and injects only the globals it names, so the new helper was
an unbound identifier; the `ReferenceError` landed in the storage catch and every
good-path arm failed. In a browser the wrapper was fine. The easy fix was to
inject the helper and move on -- but the reason the harness could not tell the
two apart is exactly the reason a USER could not: **one catch answering for two
unrelated causes.** Arms now pin both halves, including that the console IS told,
because a silently swallowed stamping failure would be the same defect in a
smaller disguise.

**THE SECOND TEST PINNED AN EXACT COUNT.** `run_truthy_sum_probe.py` asserted
`occurrences : 135` to prove the scan was not empty, and went red the first time
an ordinary commit added a matching line (140). Replaced with a FLOOR, the same
rule `MIN_TEST_FILES` carries and for the same reason: a DROP means the scanner
stopped seeing files and is worth failing on; a rise is ordinary growth. An
equality answers a different and unstable question than the one the arm exists
to ask.

**THE TWO NEW OCCURRENCES ARE NOT DEFECTS, and are baselined with that
ASSESSMENT rather than with "not assessed".** Both are `'$'+(x||0)` currency
labels in `stonedesk.html`. The left operand is a STRING LITERAL, so
concatenation is the intended behaviour and the result is correct for a number,
a numeric string, `0` and `undefined` alike.

**5 MUTATION CONTROLS BITE**, all three app files restored byte-identical, test
green before mutating: stamping put back inside the storage try in each of the
three apps, and the stamping failure swallowed silently in two.

**NOTED FOR THE TOOL'S OWNER, NOT FIXED:** `truthy_sum_check.py` cannot tell a
numeric fold from a string-literal concatenation, so every future price-display
line will trip it and need a baseline entry.
## 2026-09-13 (Cody) -- the checker that was teaching people to write exemptions

Skill used: `sairn-code-scrubber`. Claim: `tooling` --
`truthy sum check string literal concatenation is not a numeric fold`.
My own flag from the previous pass, and my own close: baselining two currency
labels was the workaround, this is the fix.

**A STRING OPERAND MAKES `+` CONCATENATE.** `'$' + (x || 0)` matches the same
text as the hazard and sums nothing -- the result is correct for a number, a
numeric string, `0` and `undefined` alike. The checker could not tell the two
apart, so every price-display line anyone added tripped it and was answered with
a baseline entry. Measured after the split: **140 raw matches, 82 real
candidates across 8 files, 58 concatenations.** More than a third of what this
tool had been reporting was never a defect.

**ONLY AN IMMEDIATELY PRECEDING LITERAL COUNTS, and that is deliberate.**
`s + (x || 0)` where `s` happens to hold a string is the HAZARD and is not
derivable here; `label('$') + (x || 0)` ends in `)` and is still reported. Arms
pin both directions, because a classifier that guessed wrong would HIDE a real
fold -- over-reporting is the safe side for this tool and under-reporting is the
one that costs money. Template literals count as literals.

**THE EXCLUSION IS COUNTED AND PRINTED ON EVERY RUN**, the same way the
`archive/` exclusion already is. A silent exclusion reads as coverage.

**31 BASELINE KEYS PRUNED, AND THE FILE SAYS WHY.** The CHECKER was corrected,
not the code. Nothing was fixed by the prune and no hazard was retired; the
header says so, so nobody later reads a shrinking baseline as progress.

**A NEW REPORT: baseline keys nothing matches any more.** An entry with nothing
behind it is a claim nobody is checking, and it makes the file look like it is
holding back more than it is. Reported, never auto-pruned -- a key can vanish
because the code was deleted, because it was fixed, or because the matcher
changed, and only a reader can tell which.

**THE PROBE'S OWN FLOOR HAD TO MOVE, hours after I put it there.** I floored it
on the candidate count, which is post-classification, so this correctness
improvement took it 140 -> 82 and turned my own arm red. It floors on **raw
matches inspected** now -- the number that actually answers "did it look". A
floor is only as good as the quantity it is pinned to.

**7 MUTATION CONTROLS BITE**, tool restored byte-identical, probe green first:
the split removed, the split INVERTED (16 arms), the whitespace skip disabled,
string-literal ends never recorded, the concatenation count unprinted, the
stale-baseline report hardcoded to zero, and the raw-match line reporting the
wrong quantity.

**THREE DOCSTRING COUNTS CORRECTED** in the tool and in its report-only registry
entry rather than left to be quoted -- the tool's own docstring already says a
number in a docstring is a claim like any other.
## 2026-09-13 (Cody) -- a test pinned to the SHAPE of a cap went red on the
## commit that fixed the cap

Skill used: `sairn-code-scrubber`. Claim: `stonedesk` --
`drawing snapshot budget retention cap assertions stale`. The last red on
`main`, and it had been red since `ab0a43fe` landed.

**THE CODE WAS RIGHT AND THE TEST WAS STALE.** Two arms matched the INLINE trim,
`if(drawings.length>20)` and `drawings=drawings.slice(0,20)`. `ab0a43fe`
replaced that with the shared `sdCapLocal()` helper **because a raw slice told
the server every dropped drawing had been DELETED** -- a length cap is not a
deletion, and five collections were losing server history that way. The cap was
still 20 and still enforced.

**THE OBVIOUS REPAIR WOULD HAVE BEEN WORSE THAN THE FAILURE.** Re-pointing the
arms at `drawings.slice(0,20)` makes them go GREEN again the day somebody
reintroduces exactly the bug `ab0a43fe` fixed -- a test that would then be
holding the defect in place while reading as coverage. They assert the PROPERTY
instead, and more of it than before: the cap is 20, it is applied to
`sd_drawings`, and **no raw slice reaches the server sync**.

**ONE ARM WAS TIGHTENED TWICE.** My first rewrite of *"the old 50 is gone"*
stripped `//` comments and looked for any `50`, which would go red on an
unrelated number arriving in that function later and mangles a `//` inside a
string. It names the two real spellings now. A broad regex passing today is not
the same as a correct one.

**4 MUTATION CONTROLS BITE**, `stonedesk.html` restored byte-identical, test
green before mutating: the cap raised back to 50, the helper swapped back for
the raw slice, the cap removed entirely, and the cap applied to the wrong key.
The second of those is the one that matters -- it is the real bug, and it now
fails 3 arms.
## 2026-09-13 (Cody) -- 131 commits on main were authored by a test fixture

Skill used: `sairn-code-scrubber`. Claim: `platform` --
`committer identity leak probe identity in a clone config`. Michael's direction:
investigate as its own task, stop the leak, do NOT rewrite the history, and
answer separately whether check 8 is producing wrong results.

**FOUND WHILE DIAGNOSING SOMETHING ELSE.** `git log --format=%an` on the commit
that had just blocked every push returned `probe <probe@local>` -- the identity
push-gate probes give their throwaway fixture commits. Measured: **131 of 3,730
commits**, 2026-09-10 through 2026-09-13, including an app's entire per-employee
auth endpoint, claim commits and generated-doc regenerations.

**CAUSE, LOCATED RATHER THAN GUESSED.** `git config --local --get user.email`
across all four clones: `SAIRN-fourth` alone carried `probe@local`, written into
its `.git/config` on 2026-09-10 rather than passed per-invocation with `git -c`.
Unset, so it falls back to the global identity. All four clones now commit as
`Michael Dibert <mikied68@gmail.com>`. No current probe writes to a real clone's
config -- every `git config user.*` call in `tests/` is scoped to a temp repo or
a throwaway clone, checked one by one -- so this is residue rather than an
ongoing source.

**CHECK 8 IS NOT BROKEN, AND THAT IS A SEPARATE FACT FROM IT NOT CATCHING THIS.**
It keys on the commit SUBJECT matching `^PROBE\b` and has never read an
identity. Verified rather than assumed: grepping the gate for `%an`, `%ae`,
`%cn`, `%ce`, `user.name` and `user.email` returns nothing at all. So the leak
degraded no gate. It also tripped none -- because **nothing anywhere on this
platform reads the committing identity.** That absence is the defect class, and
it is why a clone published real work under a fixture's name for three days.

**THE GUARD IS DERIVED, NOT HARDCODED.** `tools/committer_identity_check.py`
reads the throwaway identities out of the probe sources themselves, so a new
probe's identity is covered with no edit to the checker -- the staleness failure
the app map and the tooling inventory were both rewritten for. An arm plants a
brand-new identity in a fixture file and requires it to be caught.

**HISTORY IS REPORTED AND NEVER FAILED ON.** Rewriting published history on a
repo four clones share is a larger risk than a wrong name on a commit, so the
count is printed on every run and an arm requires that a clone whose HISTORY
carries the identity still PASSES once its CONFIG is fixed.

**THE PROBE BREAKS A THROWAWAY CLONE, NOT A WORKTREE.** `user.*` is REPOSITORY
config and a worktree shares `.git/config` with the clone that made it, so doing
this in a worktree would mis-attribute this clone's own commits for as long as
the probe ran -- the defect, performed.

**ONE MUTATION SURVIVED THE FIRST PASS, for the reason that keeps recurring.**
Section C left `user.name=probe`, so the two derived-list arms were refusing on
the NAME and proving nothing about the email under test; deleting the
`-c user.email=x` branch from the scanner changed nothing. The arms reset the
name first and read the matched value out of the COMPROMISED block now. **7
mutation controls bite**, tool restored byte-identical, probe green first.

**FLAG FOR FOURTH, INFORMATIONAL:** the config in their clone is corrected and
no action is needed from them.

### Follow-on the same day: the probe poisoned the list it was testing

`tests/run_committer_identity_probe.py` went red on two CONTROL arms within a
minute of being committed, and both failures were correct.

**THE CHECKER DERIVES ITS LIST BY SCANNING `tests/`.** The moment this probe was
committed, a fresh clone carried it -- and the control arms' own clean identity,
written here as a literal `'user.email', 'a.person@example.com'` pair, became a
"throwaway identity" the checker refused. The two arms that assert an ordinary
identity PASSES are the ones that caught it.

**AND THE SAME SHAPE HAD ALREADY LET A MUTATION SURVIVE TWICE.** To make the
checker see a fixture value the probe must SET it with
`git config user.email <value>` -- and that line, in this file, is itself an
ARGUMENT-form pair the scanner reads. So the `-c user.email=x` arm was passing on
the checker finding the value in the PROBE rather than in the fixture, and
deleting the `-c` branch changed nothing. I chased it through two wrong
hypotheses before instrumenting the tool directly; reading the regexes was not
enough, running them was.

**THE FIX IS THAT EVERY IDENTITY THIS PROBE USES IS ASSEMBLED AT RUN TIME**, so
its only literal appearance is inside the generated fixture, in the spelling
under test. That keeps the control honest without weakening the checker: a real
probe writing a real throwaway identity still gets caught, because a real probe
writes it as a literal.

**THE PROBE ALSO COPIES ITSELF INTO THE CLONE NOW**, for the same reason it
already copied the tool: `git clone` carries committed HEAD, so without it the
arms were measured against the previous version of themselves and an edit could
not be verified until after it was committed. That is exactly how the literal
control identity went unnoticed -- correct in the working tree, wrong in the
clone.

**7 mutation controls bite**, all of them, tool restored byte-identical.

This is the third time today a probe has been wrong about what it was measuring
rather than the subject being wrong -- after the separator mismatch and the
`git clone` carrying committed HEAD. Same family: **the harness is part of the
system under test.**
## 2026-09-13 (Cody) -- control_char_check promoted to blocking, and a sixth
## instance found on the way

Skill used: `sairn-guardian-v2`. Claim: `tooling` --
`promote control char check to blocking`. Michael's call, on a real track
record: two fleet-wide sweeps, zero false positives, and a fifth instance caught
within hours of the file shipping.

**IT IS PUSH-GATE CHECK 11, SCOPED TO THE FILES THE PUSH SHIPS.** That scoping
is the whole reason blocking is survivable. The whole-tree scan is the right
question for a sweep and the wrong one for a gate: `api/sv-auth.test.js` carries
a standing finding inside fourth's active claim, so a tree-wide deny would
refuse EVERY push until somebody else's file was fixed -- the state check 5 has
been stuck in since 2026-09-01. An arm pins it: a push shipping a CLEAN file is
allowed **while that finding still exists in the tree**.

**THE REPORT-ONLY ENTRY IS KEPT, NOT MOVED.** The two runs answer different
questions and both are wanted: the gate blocks the push that carries the byte,
and the whole-tree run keeps a standing finding VISIBLE rather than letting it
sit unreported until somebody happens to touch that file. `checkblocks.py` is in
both lists for the same reason.

**NO EXEMPTION FILE, and that is a decision rather than an omission.** The fix
is a run-time no-op -- the escape produces the identical string -- so there is
never a defensible reason to keep the raw byte. Every other blocking check that
can be argued with has an exemption path; this one cannot be argued with.

**A SIXTH INSTANCE WAS FOUND AND FIXED ON THE WAY.** `51fe25e8` wrote a raw
backspace into `docs/SAIRN-OPEN-WORK-INDEX.md`, inside a row whose own prose is
about having shipped a literal backspace through a heredoc. Harmless in
markdown, but the index is touched by nearly every commit, so left unfixed it
would have denied every push the moment check 11 went in. The sentence now names
the byte instead of printing it.

**THE PROBE'S FIRST RUN MEASURED THE WRONG CODE, for the third time today.** A
`git worktree` is at committed HEAD and the gate runs the WORKTREE'S copy of
both itself and the checker, so the arms drove the previous versions -- and a
CONTROL arm failed because the old checker still scanned the whole tree and hit
fourth's standing finding. The probe copies its subject in now, and re-copies
after every `git reset --hard`, because a reset silently reverts it.

**5 MUTATION CONTROLS BITE**, gate and checker restored byte-identical, probe
green first: the deny removed, the missing-checker deny removed, an
unconditional deny (which must break the CONTROLS), the binary-extension filter
dropped, and the tool's file-argument scoping reverted.

**THE ONE REMAINING FINDING IS NOT MINE TO FIX.** `api/sv-auth.test.js:301` is
inside fourth's active `sairnvet` claim -- `sairn_claim.py check` BLOCKED, and I
verified the block rather than rewording past it. Check 11 will refuse the next
push that touches that file, which is the correct outcome and puts the fix in
front of its owner.
## 2026-09-13 (Cody) -- five sabotage controls closed, and the headline count is
## inflated by about half

Skill used: `sairn-guardian-v2`. Claim: `tests` --
`sabotage controls that never verify their own sabotage applied`.

**FIVE CLOSED**, 24 unguarded -> 19, each now asserting the sabotage CHANGED THE
TARGET rather than only that the checker answered as expected:
`gate_freshness_probe` (both the append and the CRLF rewrite assert the bytes
differ), and the four removal-style controls -- `check3_probe`, `check11_probe`,
`missing_checker_probe`, `run_githook_install_probe` -- which now assert the tool
was present before `os.remove` and is gone after.

**THE HEADLINE IS INFLATED AND THE CAUSE IS MECHANICAL.** The detector fires on
any file containing both a write and a `.replace(`. I classified all 19
remaining rows against their own evidence lines, and about NINE patch no file at
all:

  * `datetime.now(...).replace(tzinfo=None)` -- `run_gate_column_probe`,
    `run_snapshot_freshness_probe`
  * scrubbing a checker's OUTPUT STRING -- `run_control_char_probe`,
    `run_metamorphic_probe`, `claims/run_push_verify_probe`
  * path-separator normalisation -- `run_committer_identity_probe`,
    `run_defect_register_probe`, `run_suite_lock_probe`,
    `check2_and_check5_probe`

**NO ANCHOR TO ROT MEANS NOTHING TO GUARD, so I added no assertion to any of
them.** Flipping a flag by writing a check that proves nothing is the exact
defect this tool exists to find, performed on the tool.

**ITS OWN DOCSTRING RECORDS THE BLIND LOCK CATCHING THIS BIAS ONCE ALREADY, in
the opposite direction** -- the first pattern required `.replace(` to be followed
by a quote, so the GUARDED idiom was never judged at all. This is the mirror
image, and the fixtures cannot catch it because not one of the seven contains a
datetime or an output scrub. A blind lock is only as good as the shapes it
imagines.

**~10 GENUINELY UNGUARDED CONTROLS REMAIN**, most of them the sabotage tool's own
author's probes. Narrowing the detector to require the replace to FEED A FILE
WRITE is a change to somebody else's tool and is left as a decision rather than
taken.

**SUITE: 238 files, 8 failures, NONE MINE** -- all seven testable ones reproduce
on a stashed pristine main, and the eighth is
`tests/run_report_only_checks_probe.py` timing out at 600s because the
report-only sweep now takes longer than its own limit. That last one is worth
somebody's attention: a sweep that cannot finish inside its timeout reports as a
failure rather than as a result.
## 2026-09-13 (Cody) -- the report-only sweep had stopped completing, and the
## only symptom was its own probe calling a timeout a failure

Skill used: `sairn-guardian-v2`. Claim: `tooling` --
`sabotage detector replace must feed a file write and report-only sweep timeout`.

**MEASURED, NOT ESTIMATED.** The sweep is **364s**. The PostToolUse hook that
runs it was capped at **300s** in `.claude/settings.json`. Two checkers are half
the run: `comment_sensitivity_check` 104s, `sairn_dead_button_audit` 84s.

**A KILLED PROCESS REPORTS NOTHING** -- no partial result, no list of what it
never reached. So the sweep had been silently incomplete after every push, and
the only thing anyone could see was `run_report_only_checks_probe.py` reporting
a TimeoutExpired as a failure. CC capped `metamorphic_check` hours earlier
against the PROBE's 600s budget; the number that actually bound it was the
hook's 300, and nothing connected the two.

**BOTH HALVES, BECAUSE NEITHER ALONE IS HONEST.** The sweep now stops itself
just before the cap and NAMES the checkers it never reached, as *NOT RUN -- an
UNKNOWN, not a clean result*; and the cap is raised to 600s, so with 364s
measured nothing is skipped today. Splitting alone would have quietly dropped
per-push coverage of two checkers; extending alone would have left the next
overrun as silent as this one.

**IT ALSO REFUSED TO STOP SAYING CLEAN.** Over a `--budget 25` run where 33 of
35 checkers never executed it printed *"CLEAN -- 35 promoted checker(s), no
findings"*. That is the exact sentence this file exists to stop anybody writing,
printed by the file itself.

**PER-CHECKER TIMING IS PRINTED NOW**, because a sweep that grew and a checker
that hangs are different problems and one number cannot tell them apart. CC had
to measure by hand to cap metamorphic; the next person will not.

**TWO OF MY OWN MISTAKES, both caught by checking rather than assuming:**

1. The function I wrote to avoid keeping a SECOND COPY of the timeout called
   `io.open` in a module that does not import `io`. Every call raised
   NameError, a bare `except Exception: return None` caught it, and the 300
   fallback looked exactly like a correctly-read value -- while the settings
   file said 600. A silent except producing a plausible default, written into
   the function whose entire purpose was to stop a number drifting. It prints
   the reason now.
2. My first seven arms ran AFTER the probe's reporting loop. They were counted
   but never printed, so a failure would have shown only as a total that did
   not add up. Found by grepping the output for `J1` and getting nothing while
   the count had risen by exactly seven.

**5 MUTATION CONTROLS BITE**, tool restored byte-identical, probe green first.
**ONE SURVIVED THE FIRST PASS:** blanking the per-tool print in the SUMMARY
changed nothing, because the arm was reading the `COULD NOT RUN` list further
down. Two places say which checkers were skipped, so two places are checked now
-- otherwise one of them can go quiet unnoticed, which is the same shape as the
defect being fixed.
## 2026-09-14 (Cody) -- the trial-gate tripwire died for the third time, and
## both remaining reds on main were the same defect

Skill used: `sairn-guardian-v2`. Claim: `tests` --
`two probe anchors into the schema snapshot do not match exactly once`.

**ONE ROOT CAUSE BEHIND BOTH REDS.** `license_trial_gate_probe.py` reported
*PROBES THAT DID NOT BITE* for arms 1 and 2, and `mutation_anchor_check`
independently reported those same two as **ANCHOR-0 in
`db/schema_snapshot.json`**. Two failing test files, one cause.

**THE FILE ALREADY DOCUMENTED THIS HAPPENING TWICE.** The anchors assumed
one-line columns; `3d603dd0` re-captured the snapshot PRETTY-PRINTED and killed
them; they were rewritten for the pretty-printed shape; and it has now been
re-captured COMPACT -- `"license_keys": [ "id", ...` on one line -- killing them
again. The file's own comment generalises the lesson correctly: *re-capturing a
data file can change its formatting, and every text anchor into that file is a
consumer nobody thinks of as one.* It just kept taking the same bet.

**SO THE ARMS NO LONGER HAVE A TEXT ANCHOR.** Both mutate the PARSED DOCUMENT:
they say WHAT to change rather than what the bytes around it look like, and the
probe restores the original bytes in its `finally`, so the re-serialisation
never reaches a commit. Each transform RAISES if the thing it meant to change is
absent -- `trial_ends_at` already present, or `stripe_subscription_id` no longer
a `license_keys` column -- because a transform that silently no-ops is the same
failure the text anchors kept having, only harder to notice.

**THEN THE ANCHOR CHECKER REPORTED MY FIX AS A DEFECT.** It renders a bare Name
as `@name`, so it counted `@_snap_add_trial_column` as a literal, found it zero
times, and reported ANCHOR-0 against an arm that has no anchor by construction.
It now reports those as **NO TEXT ANCHOR** in their own printed line.

**SKIPPING THEM SILENTLY WOULD HAVE BEEN THE OTHER ERROR** -- a category nobody
sees is exactly where a real stale anchor would hide, which is the same argument
`report_only_checks.py` makes for printing its own exclusions. An arm pins that
the category is printed, and a mutation that suppresses the line fails it.

**4 MUTATION CONTROLS BITE**, both files restored byte-identical, both probes
green before mutating: the structural-arm branch removed, the structural line
suppressed, the add-column transform made a no-op, and the rename transform
pointed away from the sentinel the suite actually reads. The last two fail with
`PROBES THAT DID NOT BITE` naming the arm, which is the probe reporting its own
control as dead -- the behaviour the whole file exists for.

### Two of my own probes went red on other people's good work, same hour

**`check11_probe` arm E asserted that somebody else's file was STILL BROKEN.**
It proved check 11 is scoped by checking that the tree carried a control-byte
finding elsewhere -- `api/sv-auth.test.js`, inside fourth's claim. They fixed it,
the tree went clean, and my arm failed while the behaviour it tests was perfectly
correct. **A control whose precondition is another session's unfixed defect
expires the moment they do their job.** It plants its own elsewhere now: a dirty
file committed into the BASE, a clean file pushed on top, so the outgoing range
holds only the clean one while the worktree still carries a finding.

**`missing_checker_probe`'s html CONTROL was refused by a check that landed
today.** A new blocking check -- *this push makes a GENERATED document stop
matching what it is derived from* -- correctly refused it, because a new
ROOT-level `.html` changes MASTER-PLAN's derived counts. The fixture lives in a
subdirectory now: reachability scans every changed `.html` wherever it lives, so
the arm still exercises what it names, while the generated documents count root
files only.

Both were my probes being wrong about their environment rather than the gate
being wrong. Four other failures in the same run reproduce on a stashed pristine
main and are not mine.
## 2026-09-14 (Cody) -- four suite failures, three harness bugs, and one real
## finding I refused to bury

Skill used: `sairn-guardian-v2`. Claim: `tests` -- `four pre-existing suite
failures sv backup faults local only shape fmea loop tooling inventory`.

**`sv_backup_write_faults` -- SIX arms died on `SV_AUDIT_KEY is not defined`.**
`svSyncCollection()` grew two dependencies and the vm world only contains what
it is told about, so a fine subject read as a broken one. Same shape as the
storage-wrapper harness earlier. The KEY is lifted from the app rather than
retyped; the MARKER is a recording stub, which is what made four new arms
possible: **an audit entry becomes evictable only if the SERVER answered.** The
app states that rule in a comment and nothing checked it. 16/16 now.

**THREE HARNESS TRAPS, all mine, all caught by checking:**

1. A vm-realm Array is not `deepStrictEqual` to a host `[]`. Node says *"same
   structure but not reference-equal"*, which reads exactly like a real
   mismatch. Comparing a primitive crosses the realm boundary cleanly.
2. **My refusal arm used `transport: 'refuse'` and the mode is `'refused'`.**
   faultkit fell through to the HAPPY PATH, and the arm reported that a refused
   push marks a DEA-relevant audit entry evictable -- **a false defect in a
   controlled-substance trail, from a fixture that never reproduced a refusal.**
   faultkit now THROWS on an unknown transport; no existing suite depended on a
   typo. A harness that silently accepts a fault it does not implement is the
   could-not-tell-reported-as-a-result shape, one level below the code.
3. Both are candidates for their own bug class, recorded here rather than left
   in a commit message.

**`run_tooling_inventory_probe` -- `master_plan.py` was described TWICE**, in the
REGISTRY and in PURPOSES. Same removal `install_git_hooks.py` needed yesterday,
caught by the same assertion. **`run_fmea_loop_probe`** is green on current main
with no change from me.

**`local_only_shape_probe` -- IT CAUGHT TWO REAL NEW LOCAL-ONLY COLLECTIONS.**
`sv_audit_backed` is per-device bookkeeping, not a record -- another device's
confirmations say nothing about whether THIS device's copy is safe to evict --
so it is DECLARED not-synced and that half is closed. **`sb_po` and `sb_recv`
(`57236fe9`) are purchase orders and goods receipts with NO route to a server,
on one workstation.**

**ARM 6 STAYS RED AND THAT IS THE CORRECT STATE.** It asserts *no business
record anywhere reaches no server*, which is the claim the whole sweep exists to
make; a sweep that quietly lowers its own bar has stopped being one. Arm 5's
per-app baseline is restated to the MEASURED numbers with the reasons, so drift
detection keeps working, and the file now says why the two arms disagree on
purpose. **Michael routed `sb_po`/`sb_recv` to CC** -- their tables, their schema
context. Not mine to touch.
## 2026-09-14 (Cody) -- item 83: the two questions a fail-safe default is never
## asked

Skill used: `sairn-guardian-v2`. Claim: `platform` -- `fail safe verification
atomicity and recovery round trip for the witnessing lock`. Applied to item
19's witnessing lock first, as directed.

**EVERY FAIL-SAFE ON THIS PLATFORM IS TESTED THE SAME WAY:** drive it into the
unsafe condition and prove it refuses. Necessary, and it only ever asks whether
the transition FIRES.

**ATOMICITY.** `requireWitness()` is four round trips before an irreversible
write -- read the token, read the policy, compare-and-set the spend, proceed.
Kill the process or drop the socket between any two and the system settles
somewhere. The invariant is **returns null implies the token is SPENT**. The
unsafe inverse is a caller cleared to write on a REUSABLE signature, on a
DEA-relevant append-only record, and nothing asserted it could not happen. Every
interruption point is driven now, and the number of points is MEASURED at run
time rather than written down -- a count in a test is a claim that goes stale the
first time a round trip is added.

**THE SHAPE THAT ACTUALLY LOSES DATA** is its own section: a spend applied
server-side and THEN interrupted. The mutation landed and the caller will never
learn that it did, which is different in kind from a spend that never happened.

**RECOVERY.** A fail-safe that fired is a system in its safe state, not a working
one, and nothing anywhere walks the documented recovery. The lock's own words
are the documentation -- *"a lost token is re-requested, which costs one
confirmation"* -- so that is what the suite runs: one fresh confirmation restores
normal operation, costs exactly ONE spend, is available IMMEDIATELY (a burn is
not a lockout), and the replacement window is read from `TOKEN_TTL_MS` rather
than typed.

**NO RECOVERY SLA EXISTS, AND I DID NOT INVENT ONE.** Writing a number would be
fabricating the standard. The arms use what the lock actually commits to, said
out loud in the file.

**THE ARM WORTH HAVING:** recovery must not WIDEN what may be written. A
replacement confirmed for a DIFFERENT record is refused -- otherwise an
interruption becomes an opportunity on a register where the wrong row stands
forever.

**TWO MUTATIONS SURVIVED THE FIRST PASS.** Dropping the `spent_at=is.null`
compare-and-set, and treating its zero-row loser as a win, both left every arm
green -- because nothing RACED two requests at one signature, which is precisely
the defect the lock's own comment names as "exactly wide enough for a double
submit to write two controlled-substance rows on one signature". Three race arms
added, including one that asserts the CAS clause is present in the request the
lock actually sends; both mutations now bite.

**THE SIXTH SURVIVOR IS DEFENCE IN DEPTH, PROVEN RATHER THAN CLAIMED.** Removing
the already-spent guard alone still refuses, because the CAS catches it one step
later. An explanation is a claim, so I turned BOTH off together: 6 arms fail.
That is what makes the single-mutation survivor a redundancy rather than a hole.

**THE KIT IS THE REUSABLE HALF.** `tests/failsafe/failsafekit.js` keeps a real
(tiny) table and applies PATCHes to it, including the compare-and-set, because a
SCRIPTED stub cannot answer "did the write land" -- it replays the same answer
either way, and atomicity is entirely a question about what landed. The next
fail-safe in the family -- the cron watchdog, a circuit breaker, a
deny-by-default gate -- gets both questions asked with the same kit.

---
## 2026-09-14 (Cody) -- `check` printed CLEAR after its fetch had FAILED, and
## the control caught the same defect inside the fix

Skill used: `sairn-guardian-v2`. Claim: `platform`. Files:
`tools/sairn_claim.py`, `tests/claims/run_freshness_probe.py` (new, 63 arms).

**REPRODUCED FIRST, NOT INFERRED.** With the remote unreachable the `git fetch`
exited **128** with *"unable to access"*, and the next line printed was

    CLEAR -- no active overlapping claim from another session.

That verdict came off an `origin/main` ref eighteen minutes stale and nothing in
the output said so. The fetch failure was swallowed by `check=False`, and the one
existing warning -- *"falling back to this clone's copy, which may be stale"* --
**could not fire, because nothing had fallen back.** A stale remote-tracking ref
is perfectly readable, so `read_origin_claims()` SUCCEEDED and handed back old
claims. PR §1.11 inside the tool whose entire premise is that a fetch happened.

**WHY IT SURVIVED IS THE PART THAT TRANSFERS.** `tools/sairn_claim_hook.py`
already tracked this: `try_fetch()` returns a bool and `read_claims()` threads a
`fresh` flag so *"a fallback answer is never reported as a current one"*. The
freshness accounting existed in the copy that runs UNATTENDED and was missing
from the copy A HUMAN INVOKES before spending hours -- the same one-copy-fixed
asymmetry this pair recorded on 2026-09-04 over `git checkout origin/main --`,
with the arrow reversed. Neither copy is the canonical one, which is the lesson.

**THE FIX STAYS SILENT WHEN THE FETCH WORKED.** A banner on every run is one a
reader learns to skip, and that would cost exactly the line that matters. Exit
**4** is a distinct code because returning 0 for both a fresh CLEAR and a stale
one is what left nothing downstream able to tell them apart. A BLOCK still exits
1 and carries the note as well -- staleness cuts both ways, and a claim blocking
you may have been RELEASED since the last fetch.

**STALE DOES NOT ABORT A CLAIM, and that is a decision.** Refusing offline would
make the tool unusable the moment the network drops, and the file's own header
records the price: *"a gate that must be talked past routinely is a gate people
learn to talk past"* -- six false blocks, six overrides. The two halves also fail
differently. The COLLISION half genuinely degrades on stale data; the PUBLISH
half does not, because `push_verified()` proves the commit reached origin/main or
returns 3. So it warns, proceeds, and afterwards tells the session to re-run the
collision check now that the remote is demonstrably reachable.

**THE CONTROL CAUGHT A REAL DEFECT IN MY OWN FIX, which is the whole argument
for section I.** The age first came from `.git/FETCH_HEAD`'s mtime, on the
reasoning that git rewrites it on a successful fetch. **Measured rather than
reasoned about, both halves were wrong:** `git clone` never writes FETCH_HEAD at
all, and a **FAILED** fetch CREATES and touches it -- `git fetch` exiting 128
against a dead remote left the file **0.00 hours old**. The tool would have
reported a five-hour-stale view as ONE MINUTE old, immediately after the fetch
that failed to refresh it. That is the `gate_column_check` 18.7-hour
understatement recommitted by the code written to avoid it, in the one direction
that matters -- making stale data look current. Replaced by a stamp written under
`.git/` **only on exit 0**, read as a recorded instant rather than a file's
mtime, and control 7 exists so the mistake cannot come back.

**Seven controls, each asserting its own sabotage landed** before believing the
arm went red -- the 23-of-39 measurement is what that guard is for. Tool restored
byte-identical after all seven.

**NOT MINE, RESPECTED:** the cron-jitter collision (`send-reminder` and
`alf-alerts` both on `0 * * * *`) is CC's under an active claim. `vercel.json` is
untouched. Independently confirmed for CC's use: the collision is real, and
`cron-watchdog` (:15) and `audit-checkpoint` (3:30) are clear of it.

---
## 2026-09-14 (Cody) -- item 8's deterministic half, item 89's real defect, and
## 23 tools nothing was measuring

Skill used: `sairn-guardian-v2`. Claim: `ai-redteam-refusals`. Files:
`tools/ai_prompt_refusal_check.py` (new, via `tools/new_checker.py`),
`tests/run_ai_prompt_refusal_probe.py` (new), `tools/flaky_checker_quarantine.py`,
`tools/report_only_checks.py`, `tools/tooling_inventory.py`.

### Item 8, sub-item 7 -- the half that needs no model call

**THE LIMIT IS IN THE TOOL'S OWN OUTPUT, not just in this log:** it checks that
refusal WORDS ARE PRESENT in a system prompt. It cannot show the model obeys
them. That half needs a model call and stays deferred.

**THE FINDING WORTH HAVING IS THE ONE THAT LOOKS COVERED.** `sairnlaw` defines
`LAW_CITATION_RULE` -- *never output a case citation in citable-reference
format*. Two of its AI call sites do not reference it and instead write their
own `HARD RULES` block, one of which says *"if you cite a case, give its real
reporter citation"*. **Those are materially different rules on a legal product**,
and nothing keeps them in step. A third site is a trust-accounting explainer
emitting prose with no citation rule at all.

**THE RULE INFERS NOTHING, DELIBERATELY.** Topic matching would be a design
opinion on every prompt in the tree, which is what `shape_antipattern_check.py`
records getting switched off inside a day. It fires only where an app already
made the commitment itself; **an app with no constant is never told to write
one.** 6 files define a constant, 11 call sites sit in them, 7 carry one, 4 do
not -- and the denominator is printed, because quoting 4 against 465 files
scanned would flatter the platform by two orders of magnitude.

**FIVE FALSE POSITIVES, EVERY ONE HIT FOR REAL, ALL PINNED:** `dx-system` is a
BODY-SYSTEM `<select>` in SAIRNvet's diagnoses search -- "system" is overloaded
(anatomical, HVAC, "5-tab system"); `400 INVALID_COVERAGE_RULE` is an error code
in a SAIRNdental comment; a constant defined only inside a comment is not a
commitment.

### Three defects in my own tool, none caught by the blind lock

1. **`_value_expr` was not string-aware.** Every prompt here is English and
   English has commas, so the first comma inside the prose severed the
   expression. `sairnfreedom.html:4066` genuinely ends `+VA_CLAIM_REFUSAL`, and
   the walk stopped at the comma in *"on a page you read, and always name the
   page"* -- **reporting two COMPLIANT sites as missing their own refusal.**
   Nine findings became four. **The lock said 9/9 the whole time**, because not
   one fixture had a comma inside a string.
2. **The population counters were incremented by the FIXTURE run as well as the
   sweep.** First report: 18 sites, 10 compliant, 4 flagged -- **which does not
   add up, and the arithmetic is the only reason I looked.** An identity is
   asserted now.
3. **THE MUTATION CONTROLS WERE VACUOUS.** A mutant copied to a temp directory
   died on a missing-module error before reaching any sabotaged line, and that
   crash exits 1 -- indistinguishable from the sabotage working. Four of five
   controls "went RED" while measuring nothing. Every control now requires
   **proof the mutant RAN** before its verdict is believed.

**AND ONE CONTROL LEGITIMATELY REFUSED TO BITE, which is the point of having
them:** reverting the lock to raw text still gave 11/11, proving the
comment-stripping fix was UNPROVEN by the fixtures meant to hold it. A twelfth
fixture that discriminates by mode was added; the control bites now.

### Item 89 -- the look-elsewhere effect, and what was under it

**The premise is confirmed:** every threshold in item 22's ledger is
per-checker and none references how many checkers are measured.

**The arithmetic underneath is worse.** With n runs the smallest non-zero flip
rate expressible is 1/n. The WATCH band is `(0.0001, 0.05]`, so one
disagreement lands in WATCH only at n >= 20. **All 37 registered checkers sit at
n=6 or n=12**, where one disagreement is 0.167 and 0.083 -- both above the
quarantine bar. **The WATCH tier was unreachable fleet-wide**, so every first
chance flip went straight to a quarantine needing an owner, a deadline and ten
clean re-entry runs. That contradicts the file's own prose. **The lock read 5/5
throughout: no fixture covered n=4..19, the only regime any real checker has
been in.**

**NO PRE-REGISTERED THRESHOLD MOVED.** A post-hoc threshold change after seeing
the data is exactly what convention 1 forbids. What changed is that one
disagreement is WATCH at any run count -- the stated rule, implemented --
and `WATCH_EXPRESSIBLE_AT` is DERIVED from `QUARANTINE_AT` rather than typed.
The control proves it: removing the fix fails exactly the two new WATCH
fixtures, while the third (TWO disagreements at the same n is still QUARANTINE)
keeps passing, so it is not an amnesty for small samples. The one real
quarantine is untouched.

**THE MULTIPLICITY IS PUBLISHED, NOT SILENTLY CORRECTED.** Tightening the bar by
a Bonferroni factor is the same forbidden post-hoc change and would hide real
flakiness in a fleet that has already recorded a genuine case. The per-run
probability is printed as an ASSUMPTION and is **not calibrated from the ledger
it judges** -- that would be the validation eating its own subject. **The split
matters more than the figure:** multiplicity explains SINGLE disagreements and
not repeats, so quoting a chance figure beside a 4-in-12 checker would discount
a real defect. My own split read `r['rate']` where the key is `flip_rate` and
printed a plausible pair of zeros beside a live quarantine; it is cross-checked
against the verdict column now.

### 23 tools with no recorded decision

**Three REGISTERED checkers have no ledger evidence at all** --
`completeness_check.py`, `dependency_graph.py`, `secrets_inventory.py`, two of
them a day old. That half of the disclosure works and needs a `--measure` pass.

**The denominator was the half that did not.** "37 of 40 registered" is honest
about a registry and wrong for the question anyone asks: an unregistered tool is
not measured-zero-times, it is **absent from the arithmetic**. Measured: **64
check-shaped tools, 29 promoted, 12 recorded-not-promoted, 23 in neither** --
including `restore_coherence_check.js` and four other tools built in the last two
days. Third occurrence of the 11-unwired-checkers shape, so the disclosure is
widened rather than the finding re-found.

**And the register's own data shape is part of it:** two NOT_PROMOTED entries
pack several tool names into one string, so five names cannot be found by an
exact-name lookup. **My first count was 24 because of it** -- a source-regex read
found 59 decided names where importing finds 61. It imports now, keeps the regex
as a fallback, and prints which method it used, because a reader cannot tell a
parser's blind spot from a real gap.

`injection_commit` is **not a tool** -- it is a field on the defect register --
so there is nothing to register. Said because it was named in the ask.

My own new checker is in NOT_PROMOTED with a reason rather than promoted: its
four findings need a human triage that has not happened, and one looks
defensible as it stands.

**AND THE SAME THREE TOOLS TURNED A PRE-EXISTING RED TEST GREEN.**
`tests/run_tooling_inventory_probe.py` was failing on *"no REGISTRY tool is also
described in PURPOSES"*, and the three violators were exactly
`completeness_check.py`, `secrets_inventory.py` and `dependency_graph.py` -- the
same three that had no ledger evidence. A REGISTRY tool's `catches` must come
from REGISTRY; duplicating it into PURPOSES makes two sources that can disagree,
which is the claim-in-two-places failure that document exists to prevent. Their
registration was half-done: REGISTRY entry added, PURPOSES entry left behind,
never measured. Three duplicate entries removed, probe passes.

**It was one of the 12 failures I had already proven pre-existing by reverting
my own work, so it was never mine** -- it was fixable as a direct consequence of
asking whether the new tools were registered properly. One down, 11 to go, and
the remaining 11 belong to other sessions' work in flight.

**A FOURTH INSTANCE ARRIVED IN THE NEXT REBASE, FROM ANOTHER SESSION, WITHIN THE
HOUR** -- `eaten_substitution_check.py`, same half-done registration. A mistake
two sessions make independently is a MISSING GUARD, not carelessness, so the
generator now refuses on it: `tooling_inventory.py` already refused a tool with
no description and a description for no tool, and did not refuse a tool
described TWICE. That third direction is the claim-in-two-places failure the
document exists to prevent, inside the generator meant to prevent it -- and it
had been surfacing as a red test a long way from the line that caused it.

**AND MY OWN REMOVAL SCRIPT THEN ATE AN UNRELATED ENTRY.** It consumed lines
until one ended `'),`; the eaten_substitution entry ends `"),` with a double
quote, so the terminator never matched and it swallowed `claim_provenance.py`
as well. **The new refusal caught it on the very next run** -- "1 tool in tools/
with no PURPOSES entry: claim_provenance.py" -- and the entry was restored
byte-identical from `git show HEAD:`, not retyped. That is the never-bulk-replace
rule in CLAUDE.md earning its place, and the guard I had just written catching
the person who wrote it.

---
## 2026-09-14 (Cody) -- the citation premise did not survive checking, 14 real
## registration decisions, and item 8's attack half

Claim: `sairnlaw-citation-rule`. Files: `sairnlaw.html`,
`api/claude-guardrail-metamorphic.test.js` (new), `tools/report_only_checks.py`,
`tools/flaky_checker_quarantine.py`, `docs/defect-density-register.json`.

### The brief's premise was wrong, and checking it was the work

I was sent to log "2 of 11 call sites defining a contradictory rule" as a live
correctness bug permitting fabricated citations on a legal product. **The
critique step turned out to be the SAFEST AI surface in the app.** Its output
goes through `mtExtractCitations` -> `mtVerifyCitations` ->
`citatorFetch('verify')` against CourtListener; every citation is badged
Verified / *Not found -- do not rely on this* / Ambiguous / unavailable, the
footnote only says "every citation resolved" when they all did, and the whole
response is WITHHELD if a probability claim appears.

**So Michael's preferred option -- route the simulator's citations through the
existing citator -- was already wired.** Logging that site at the stated
severity would have been recording a defect that is not there, which is the one
thing this register must never contain.

**THREE GAPS THAT ARE REAL**, registered at honest severity against `e71bcba0`:
HIGH on the trust-accounting explainer (client money, no rule, no check, raw
prose to a bookkeeper); MODERATE on the decomposition renderer (unverified
citation displayed beside Anchored badges that cover `source_span` and NOT the
`claim` text); and MODERATE on **my own checker**, which cannot see a mechanical
control applied after the model call and therefore over-implies severity on
exactly the best-protected site.

### `--check` caught my own record before it became a second app

My new record spelled the app `platform`; 47 others say `PLATFORM`. "One entity
with two names is two entities to every per-app figure in this file."

### 14 registration decisions, and the count was wrong first

Reported as "23 of 64 tools with no recorded decision". Cross-referencing
`tooling_inventory.classify()` cut it to **14**: eight are wired MORE strongly
than report-only -- six BLOCKING, one report-only via PostToolUse, one advisory
via SessionStart. **"We decided not to promote this to report-only" is a
meaningless sentence about a tool that already blocks a push.** That is the
third time this file's own history records a count overstating the gap because
a source of truth existed and was not read, so the disclosure now consults the
wiring instead of assuming absence.

Ten individual rejections with real reasons (read-lists whose correct length is
not zero; burn-downs that report other people's unfinished work; three that
need the live network or database) and four with a NAMED blocker rather than a
guess -- a missing control pair, a missing FIXTURES block on a MONEY checker, a
network half that looks separable, and a .js checker the flaky ledger's python
runner cannot measure at all. **A uniform reason across fourteen tools would be
a bulk promotion wearing individual clothes.**

### Item 8's attack half, deterministically

`api/claude-guardrail-metamorphic.test.js`, 30 arms, **zero Anthropic calls by
construction**. Item 18's mechanism pointed at the guardrails: Hank's 27 arms
assert exact values, and **a guard can be right at every point an author thought
to write down and wrong on the variant nobody typed.** Five relations -- exact
allowlist under padding/casing/tab/newline/escaped-NUL/zero-width, equal numeric
representations agreeing (tested both at AND below the ceiling, since a
saturating clamp makes them agree for free), clamp idempotence, order and
multiplicity invariance, envelope-size invariance.

**The rephrasing families are over the ENVELOPE, not over natural language** --
the model-obedience version needs a model call and stays deferred.

**The controls caught two things in my own file:** a sabotage anchor that did not
match, which REFUSED instead of silently replacing nothing; and a **raw NUL byte**
I shipped in a fixture label, caught by `control_char_check.py`. Mutants are
written beside the original rather than in tmpdir, because a mutant that cannot
resolve `./_lib/` dies on require and that exits non-zero exactly like a
sabotage that worked -- which made four of five controls vacuous in a suite I
wrote earlier the same day.

### Item 83, re-confirmed rather than assumed

**An independent reviewer found a real hole in my work** (`53e5c88b`): nothing
ever drove an EXPIRED token. Both my suites built tokens with
`Date.now() + TOKEN_TTL_MS`, and the recovery suite MEASURED remaining TTL --
which reads like expiry coverage and is not. *"Measuring how long a token has
left never asks what happens after it runs out."* With the expiry check on the
spend path disabled, every arm in both suites stayed green; an expired signature
would spend successfully and write a controlled-substance row. Two arms added,
now 14 atomicity + 10 recovery, both green. That is my own
passing-assertion-checks-the-wrong-thing lesson landing on my own suite.

---
## 2026-09-14 (Cody) -- item 83 pass three, a rotted anchor, a money blind lock,
## and two self-inflicted defects caught by existing controls

Claim: `reliability-and-witness-expiry`. Files: `tests/failsafe/failsafekit.js`,
`tests/failsafe/witness_recovery.js`, `tests/run_reliability_growth_probe.py`,
`tools/three_way_match_check.py`, `tools/ai_prompt_refusal_check.py`,
`tests/run_ai_prompt_refusal_probe.py`, `sairnlaw.html`, `sairnfreedom.html`.

### Item 83, third pass -- and the first two failed DIFFERENTLY

Pass one MEASURED remaining TTL: a subtraction, not a behaviour. Pass two, by
an independent reviewer, drove a BACKDATED ROW and proved the comparison
exists. **Neither drove the transition that happens in production** -- a token
the lock itself issued as VALID becoming refused because time passed.

**The flaw common to both is that the test did the same arithmetic as the
code.** The lock mints `Date.now() + TOKEN_TTL_MS`; both old arms add or
subtract against `Date.now()`. So if TOKEN_TTL_MS were 0, negative, or in
seconds, every arm in both suites still passed. Agreement is not corroboration
when both ends come off the same bus.

So the new mechanism MOVES THE CLOCK THE LOCK READS and leaves the row
untouched. Four arms, three of which bite when the expiry guard is disabled;
the fourth is the valid-at-T0 control and is **the only thing in either suite
that would notice a misconfigured window** -- a backdated row cannot.

**MY OWN SEAM WAS BROKEN FIRST, AND ITS OWN ARMS CAUGHT IT.** A synchronous
`try/finally` around an async fn restores `Date.now` when fn returns its
PROMISE, before the lock has read the clock once. Three arms failed, and I was
one step from reporting a production fail-safe defect. Written as "expect no
findings" it would have gone green for ever while controlling nothing.

**Scope stated:** the lock has TWO expiry checks -- `requireWitness` and the
HTTP confirm path. These arms drive the first.

### Arm 5c was the same disease, one level out

It asserted a CONDITIONAL section unconditionally. That section prints only
when some interval has a denominator under `MIN_DENOMINATOR`=10, and nine
upstream commits pushed every denominator to **28-157**. Nothing is thin, the
section correctly stopped printing, and the arm **could never pass again until
the data got sparse enough to be wrong in the old way.**

The arm was wrong, not the tool. The expected state is re-derived from the
tool's own JSON each run, both branches assert something, and both were proven
live by raising the bar in-process.

### The money checker's blind lock

18 fixtures, both halves -- locking only the structural half would leave the
arithmetic tunable against real exports. A penny difference is still caught
while `0.1+0.2` float noise inside the 0.005 tolerance is not.

**One expected verdict was corrected and which kind is said out loud:** the
no-bill-yet case, which I first wrote as a finding and the tool's stated design
treats as an ordinary open order. Corrected to match the DESIGN, not the
output.

**And the first version of the lock reimplemented the rules inline instead of
calling `structure()`** -- validating a copy that could pass while the real
sweep was broken. That is the same lock-tests-a-different-path defect I found
in `new_checker.py`'s scaffold earlier the same day, **committed again by me
one task later.**

### Two self-inflicted defects, both caught by controls that already existed

1. The money checker's lock banner printed on stdout under `--json`, so
   `run_three_way_match_probe.py` died on "Expecting value: line 1 column 1".
   **That is exactly the push-gate check-10 defect I reported earlier today,
   reproduced in my own file within the hour.**
2. `run_ai_prompt_refusal_probe.py`'s G2 anchor rotted when I rewrote
   `run_fixtures`, and it REFUSED rather than patching nothing.

### The checker's blind spot: a third state, not a wider net

R3 fires when a named verification of the model's OUTPUT runs near the call. It
detects a CALL, not an intention, and deliberately is NOT a
verify/check/validate grep -- that matches `checkAiRateLimit` and every
unrelated helper. A purely STRUCTURAL output contract is a real control and is
deliberately not counted; conflating the two would make R3 mean "something
happens afterwards".

**Two fixtures that differ ONLY in kind forced the lock to check the kind** --
both are flagged, so a flag/no-flag lock discriminated nothing. Third
occurrence of that shape in this one file. New control G7 holds it.

### SAIRNlaw got the CHECK, not just the rule

A prompt is an instruction; a check on the output is a control. On the
trust-accounting panel a citation is FORBIDDEN, so finding one is not an
"unverified citation" -- it is the model having broken a hard rule on a
client-money surface, and it now says so, verified as well as flagged. The
decomposition path now runs the SAME verification as the critique rather than
handing the lawyer a task, with the disclaimer kept as the pre-result state and
the could-not-check fallback.

### SAIRNfreedom: a named exemption that does NOT silence the finding

`SF_PHOTO_JSON_ONLY_EXEMPTION` records why, verified in the code rather than
assumed: image in, two-key JSON out, `confident===true` and an integer 0-100
required, no model prose ever displayed. Image-borne injection can only produce
a WRONG INTEGER. It names what would END the exemption, and the checker still
reports the site.

---
## 2026-09-14 (Cody) -- the rubric is NOT ratified, and the STOP box failed its
## third reader because position was never the cause

Claim: `rubric-ratification`. Files:
`docs/2026-09-13-defect-severity-rubric-UNRATIFIED.md` (verdict recorded, NOT
renamed), `docs/2026-09-14-rubric-blind-grading-protocol.md` (new),
`tools/flaky_checker_quarantine.py`, `tools/report_only_checks.py`,
`tests/run_flaky_quarantine_probe.py`.

### I destroyed my own blind pass, and said so before grading anything

The STOP box says do not read past it. I opened the file in one action that
returned all 228 lines, so the box arrived in the same payload as the rubric it
guards. Fourth was caught identically, and the fix applied then was POSITION.

**Position is not the cause.** There is no position inside a file read
atomically that protects the rest of that file. A reader who scrolls is
protected by a box at the top; a reader whose smallest unit is "open the file"
is not -- and both kinds read this repo. So the guard is now a SEPARATE FILE,
the only arrangement where "read this first" is enforced by the reader's own
mechanics rather than their self-restraint.

### The measurement, and why the number is not the finding

Holdout is **21 records, not the 12 stated** -- 55 at the rubric's commit, 76
now. **ACCURACY 13/21 = 62%.** No `critical` in the holdout, so D3 is still
unexercised and the figure says nothing about it. **Stability is NOT reported
rather than estimated** -- unobtainable for me.

**62% is mostly the REGISTER disagreeing with itself.** Five of the eight
disagreements are one shape -- *a control that silently stopped testing
anything* -- which D1 makes `high`, and which the register grades **1 low / 4
moderate / 2 high across 7 records.** The rubric was derived from the half that
says high.

Sharpest instance: the rubric cites `report_only_checks.py` printing clean over
zero apps as its canonical `high`, and that record IS `high`. The holdout's
"printed CLEAN over a run where 33 never executed" is the same defect and is
`moderate`. One shape, two grades, one register. **Accuracy against a
self-inconsistent reference is not a clean measure of the rubric**, which is
convention 3 applied to the reference rather than the sample.

### Three reproducible boundary failures, and I changed NOTHING in the rubric

1. Does a TOOL falsely reporting clean satisfy D1? The acted-on list says yes;
   practice says moderate. **This one needs an owner** -- it moves five of the
   eight, and whichever way it goes the losing half of the corpus needs
   regrading.
2. **No question exists for a LATENT high-consequence exposure.** D3 needs a
   value to have REACHED production, D1 needs something acted on -- so a Tier A
   fabrication path that has not fired yet grades `low` while the register says
   `high`.
3. D1's silence test excludes LOUD money failures and the register does not.

A ratifier who quietly rewrote the boundary they were sent to check would be
committing the §5 failure this document is built around. File keeps its
`-UNRATIFIED` suffix.

### The .js blocker was worse than "cannot measure"

The ledger shelled out with `sys.executable` unconditionally. Handing a
JavaScript file to Python **does not fail loudly** -- it exits non-zero with a
SyntaxError IDENTICALLY every run, so the flip rate is 0.0 and the checker is
classified **STABLE**. The first `.js` promotion would have produced an
unmeasurable registry entry that the ledger called the most reliable tool on
the platform.

Fixed by extension dispatch plus a one-off interpreter PROBE, so a missing
`node` is a named could-not-measure. An unsupported extension returns None,
which is a refusal the caller records and `main()` prints -- a best-guess
interpreter would rebuild the defect.

**And fixing it surfaced a separate fail-open in the same file:** every
execution failure was stored as an ordinary observation, so **a checker that
never ran once was the most stable thing in the fleet.** New `UNRUNNABLE`
verdict, checked before the run-count gate, with two fixtures -- all-error goes
UNRUNNABLE, and **one failed launch among real runs is still a FLIP** so it is
not a blanket amnesty -- and a control that turns the first fixture STABLE when
disabled.

**The list is printed**, because I left the R3 counter computed-and-unshown in
another tool earlier today and did not want the third instance.

`restore_coherence_check.js` stays NOT_PROMOTED on its REMAINING blocker: it
reaches the network to verify a restore. Its entry now records that the runner
half is closed.

---
## 2026-09-14 (Cody) -- the D1 regrade, a blocker I had invented, and a status
## doc that went stale in exactly the way it was written to prevent

Claim: `register-regrade`. Files: `docs/defect-density-register.json`,
`tools/report_only_checks.py`,
`docs/2026-09-02-competitive-gap-status-rederived.md`.

### The D1 regrade -- 10 moved, 7 deliberately not, 2 out of scope

Michael's decision: a tool falsely reporting clean is `high`, whether it ran
none of the work or most-but-not-all. **The discriminator I applied, so the
judgement can be checked rather than the outcome: did the tool EMIT a clean /
pass / green verdict over work it did not do?** A tool that OVER-reported,
exited non-zero, or printed an explicit could-not-tell is NOT this -- it was
loud, and D1's silence half is what separates them. That is the same
discriminator the rubric's own `low` table uses for the ANCHOR-2 control, so
this keeps the corpus consistent with the rubric rather than just moving
records toward the new answer.

Spread 35/33/6/2 -> **25 moderate / 43 high / 6 low / 2 critical.** Verified by
diff that severity was the only field touched and the record count is unchanged.

**MY FIRST SCRIPT KEYED ON THE COMMIT AND MOVED THE WRONG RECORD.** It regraded
both records under `72fa7000`, the second of which went RED when its
precondition was fixed -- a loud expiry, not a false clean. I had handled that
collision explicitly for `5b98fd27` and missed it here. Measured after
catching it: **19 commits carry more than one record, and 48 of 76 records
share a commit with another** -- so a per-commit key is wrong by construction on
nearly two thirds of the register, not merely where I happened to look.
Rewritten to key on a distinctive summary substring, and it REFUSES if any
pattern matches zero or more than one record.

Two app-code records (`scpData`, `mechData` swallowing network errors) are left
OUT OF SCOPE and said so: that is product error-handling, not a tool asserting
confidence, and extending the decision to it is a second decision nobody made.

### The restore-checker blocker was mine and it was wrong

I wrote that `restore_coherence_check.js` needs the network, so a gate carrying
it would make every push depend on the outside world. **Both halves are false.**
`tests/run_restore_coherence_probe.js` already spins up an `http.createServer`
on `127.0.0.1:0`, points `SAIRN_TARGET_URL` at it, and passes 26 arms. And with
no target the tool already exits 2 -- COULD NOT RUN -- which I verified by
running it.

**I asserted a blocker from the tool's description without checking whether it
was true, inside the triage whose entire purpose was to replace vague blockers
with specific ones.** Corrected in the entry rather than reworded.

The real blocker: **its subject does not exist at push time.** There is no
restored database to point at on an ordinary push, and on Supabase free tier
there are no automated backups, so there is nothing to point at. Pointing it at
production would check production's own chain -- a different question that WOULD
make every push talk to the live database.

Triage confirmed closed: 67 check-shaped tools, 59 decided in registries, 8 by
wiring, **0 undecided.**

### The competitive-gap status doc is stale, and #5 is built

That file exists because the 2026-08-26 audit called five shipped features
Absent and three sessions reached for them. **Twelve days later the same thing
has happened to it.** Row #5 says no customer e-signature and no deposit
collection; measured now it is BUILT, WIRED and SERVER-PERSISTED -- an `esig`
namespace, `esig-` DOM ids with live handlers, and `deposit_amount` /
`deposit_status` in `api/sd-data.js` with a dedicated test file.

The row's stated evidence is still TRUE and is about a different field, which
is how it stayed plausible.

**A trap in its own marker method, hit while doing this:** searching `esign`
returns 47 hits in StoneDesk and **every one is `design`**. The real namespace
is `\besig` and is invisible to the obvious search, on a platform that contains
SAIRNdesign.

**Nothing buildable and un-gated is left in that document.** #4 slab-scanner is
still open but needs a third-party interface; everything else is
vendor-blocked, certification-blocked, explicitly not-recommended, or held open
on Michael's call. That is the finding, not a disappointment -- the next real
item needs a different source or a vendor decision.

**And 5 audit docs exist on disk, not 4** -- the
`build-vet-biz-grounds-cash` one was not in the brief's list.

---
## 2026-09-15 — the countersign suite, and a control whose header lied about itself

### Item 83's countersign half is closed

`tests/failsafe/witness_countersign.js`, 30 arms. The probe Hank left behind now
reports **0 of 6 MISSED** with the control still CAUGHT by all four suites.

Each section is keyed to the mutation it kills (M1 SAME_PERSON … M6 the
spend-path boundary) so the suite and the probe can be checked against each
other rather than trusted, and one arm reads the probe's own mutation list and
fails if it grew without this file growing.

**The HTTP layer is stubbed by replacing `require.cache` exports BEFORE the lock
is required.** `api/sv-witness.js` destructures `verifySessionToken` /
`tokenFromRequest` at require time, so stubbing afterwards changes nothing and
every arm would have been driving the real signature verifier while the header
claimed a stub. The real modules are loaded first and only two functions are
overridden.

**The two BOUNDARY arms are the ones more of the old kind could never have
caught.** `witness_recovery.js` proves the window at TTL−1 and TTL+1 — both
sides, neither ON it — and `<=` and `<` agree everywhere except at exactly
`expires_at`. A window LENGTH was proven and the OPERATOR was not. The arms
freeze `Date.now` and land on the millisecond, in both directions.

**A fixture bug worth keeping.** The EXPIRED arm FAILED on the first run,
reporting 200. My `NOW` was a hardcoded wall-clock instant that sat hours in the
FUTURE of this machine, so `PAST` was not past and an expired token was not
expired. Fixtures are now relative to the real clock; only the boundary arms
freeze it. **A fixture that is only sometimes in the past is a fixture that only
sometimes tests anything.**

The probe is KEPT rather than deleted — it is the only thing that can tell a
suite which CATCHES these mutations from one that merely mentions them. Its
closing verdict is now DERIVED from `missed`, because three hardcoded lines
saying the gap was open, printed under a line reading "0 of 6", would be the tool
contradicting its own output.

### SAIRNcode: the gates already had a control. Its HEADER was false.

Routed here as "the six Tier A billing role-gates have never had a
planted-defect mutation arm." **That is not true and I did not build a
duplicate.** `tests/sairncode_gates_mutation_control.js` already carried 20
mutations across BOTH halves (server + `sairncode.html`), every one biting, each
verifying its own sabotage reached the bytes on disk. Removal AND substitution of
a gated resource are both caught — section 5 compares a hand-written table
against measured behaviour, so swapping one resource for another fails it even
though the `length === 6` arm would not.

**What was actually wrong: the file's header said *"api/sd-data.js is never
touched"* and it was written twenty times a run, in this clone, on two TRACKED
files.** The code's own comment twenty lines below said the opposite. Nobody
caught it because every assertion passed — the restore really did work on every
run anybody watched.

Converted to throwaway-worktree isolation: the pattern
`tests/sairnlegacy_fault_probe.py` used **in the same commit**, citing the
2026-09-10 stranded-PROBE-commit incident. Fails CLOSED (exit 2) if the worktree
cannot be made. 108/108, all 20 still bite.

**Then I ran my own fix with its isolation deliberately broken, and it caught me.**
SRC repointed at the clone: 17 arms went red and the structural arm fired — but
all three HASH arms PASSED, because `runSuiteWith`'s `finally` had already put the
original bytes back. **"Restored" and "never written" are different claims, and
comparing end-state bytes cannot tell them apart** — the exact conflation this
change existed to remove, committed inside the fix for it. mtime is now in the
stamp and the write-then-restore fails.

### The competitive-gap doc: the correction had not reached the summary

The 2026-09-14 finding that StoneDesk #5 is BUILT was appended UNDERNEATH a
summary still reading "genuinely open: 4 and 5". **A correction that does not
reach the summary has not landed**, and it was stale in four places, not one: the
row, the summary, the closure table, and — worst — the vendor-blocked list, which
named "GAP 5 (payment processor)". **A vendor-blocked label is the most expensive
kind of stale row, because it stops anyone re-checking at all.**

### Verified

`node --check` clean on both changed JS files; `witness_countersign` 30/30;
`witness_atomicity`, `witness_recovery`, `api/sv-witness.test.js` all exit 0;
`countersign_coverage_probe` 0 of 6 missed, control caught by 4/4;
`sairncode_gates_mutation_control` 108/108 with the clone unwritten;
`control_char` CLEAN (2009 files); `md_table` 0 malformed; `index_duplicate` 0;
MASTER-PLAN and traceability-matrix regenerated, TOOLING-INVENTORY already
matching; `run_master_plan_probe` ALL CHECKS PASS.

**Full suite: 307 files, 12 red — 11 of them RED AT HEAD TOO**, confirmed by
running the same twelve in a throwaway worktree at HEAD before attributing any of
them. The twelfth was `run_master_plan_probe`, which was MINE: adding one test
file moved a derived figure and the generated documents had not been regenerated.
Fixed, and it is why the baseline was worth taking.

**Not pushed at the time of writing, so nothing here is live-verified (PR 3.2).**

---
## 2026-09-15 (later) — a guard, a resilience layer that says what it cannot do, and an audit of what "accepted" costs

### The mutation control now refuses to run mid-rebase

Observed, not anticipated: running the worktree-based control during a `git
rebase` broke the rebase (`unable to read tree`), and the second of two commits
silently did not apply. `git fsck --connectivity-only` was clean — **nothing was
corrupted**; it was a live race between the control's `worktree add/remove/prune`
and the rebase's in-flight refs.

The guard resolves the git dir with `rev-parse --absolute-git-dir` rather than
assuming `.git/` — in a linked worktree `.git` is a FILE, and a hardcoded path
would make the guard pass while the hazard was live, which is worse than no
guard because it reads as coverage. It covers cherry-pick, merge, revert and
bisect too: same condition, and the cherry-pick case is what the recovery used.

**Proven by planting a marker in a throwaway worktree's git dir** — refuses with
exit 2, and with the marker removed the control runs 155/155.

### Circuit breaker + bulkhead — and the part worth reading is what does NOT work

`api/_lib/resilience.js` (34 arms). Timeout, bulkhead, breaker, composed
breaker→bulkhead→timeout so an open circuit costs no socket.

**THE THREE DO NOT SURVIVE THIS RUNTIME EQUALLY, and shipping them as one
feature is how a decorative gate gets built.** A classic in-process breaker —
Hystrix, Resilience4j, Polly — is a per-instance failure counter with a
threshold. `api/_lib/anon-rate-limit.js` MEASURED what that does here on
2026-09-05: 40 concurrent requests against a limit of 20, not one trip, a dozen
instances each counting from 1. For a breaker it is worse than for a limiter,
because **load is what makes a dependency degrade, so the counter is diluted most
at the moment the breaker is supposed to trip.**

So the breaker takes a STORE. Postgres-backed is real; per-instance is honest
about being approximate and **`createBreaker` THROWS if asked to enforce on
one** — the one configuration refused outright, because silently downgrading to
observe leaves a caller believing in a breaker that never trips.

**The circularity is stated rather than discovered later:** the shared store
lives in Supabase, so it cannot break on Supabase. A Supabase breaker is
instance-backed and observe-only BY CONSTRUCTION. The timeout and the bulkhead
are what protect a caller from a slow Supabase, and both work.

**The load-bearing half is the timeout, and it is nearly absent: 684 non-test
`fetch(` call sites in `api/`, ONE with a timeout** (`api/sc-eligibility.js`).
Without a timeout there is nothing for a breaker to count — a hung call does not
fail, it waits, and the invocation dies still holding it.

**NOT DONE, stated plainly: nothing is wired.** The module and its SQL exist;
683 call sites are unchanged. Wiring is a separate, large, per-dependency change.

No effectiveness percentage appears anywhere in the module, and **an arm asserts
that** so it cannot come back in quietly.

### Accepted risks: 9 of 11 have no expiry condition at all

`tools/accepted_risk_expiry_audit.py`. Not `accepted_risk_scan.py` — that asks
whether an acceptance reached a register at all; this reads the ones that did and
asks whether their expiry can ever fire. (The near-miss was real; the name was
close enough that my first 0e search should have found it and did not.)

Criteria locked against 7 synthetic fixtures in BOTH directions before any real
number was believed. Hand-checking the first real run found a population defect —
rows whose STATUS says CLOSED were matching on evidence-cell language that
survives the fix — so the filter reads the status cell. 14 → 11.

**RUNNING 1 · UNINVOKED 1 · MANUAL 0 · UNCONDITIONAL 9.**

**It found its own first case immediately, and it is the one I was sent at.** The
`supabase_admin` row names a trigger and no monitor — while
`tools/ownership_evidence_drift.py` had been watching it since 2026-09-14,
registered report-only, **currently RED at 380 tables against the 251 the
acceptance was measured on**. The risk and its monitor were linked in one
direction only, so any audit reading the row concluded nobody was watching. Row
rebuilt whole; it now moves UNINVOKED → RUNNING.

**And the sharper half, which the fix does not close:** that tool measures a
PROXY — population growth — not the trigger. The trigger is ownership, no clone
can query ownership, so nothing here can ever report the ACL fired. It can only
report that nobody has checked. **The best-instrumented accepted risk on the
platform still cannot close itself.**

### Verified

`node --check` clean; resilience 34/34; mutation control 155/155 with the clone
unwritten and the new guard proven in both directions; expiry-audit selftest 7/7;
`check12_probe` (no tool without an inventory entry) exit 0; md_table 0
malformed; MASTER-PLAN, traceability-matrix and TOOLING-INVENTORY all
regenerated and OK.

**`sql/sairn_circuit_breaker_schema.sql` HAS NOT BEEN RUN** — no clone here has
database access. Its verify block is per-statement with expected answers,
including a real breaker round trip, because the Supabase editor reports success
for the statements it did run.

---
## 2026-09-15 (later still) — a review that was already done, and two premises that were wrong

### Item 1 — dnt_rollup review DISCHARGED, and the review was Hank's

The 12:51Z obligation was open only because `--discharge` did not exist when the
work was done. **Hank had already reviewed it in `ce7764fa`, with both findings.**
I did not claim them. What I added is INDEPENDENT CONFIRMATION BY A DIFFERENT
ROUTE, which is worth more than a second opinion reached the same way:

- **Finding 1** — a readable metric reports `{value:null, unreadable:'suppressed'}`
  while `disclosure.unreadable` is `{}` and `complete` is `true`: three parts of
  one object contradicting each other. Hank reached it through a legacy
  unstamped charge; I reached it through an appointment at a location id the
  charges resource had never seen, registry empty. **Two different populations,
  same cause** — `dnt-rollup.js:151` seeds cells only on buckets that exist when
  that metric runs, and `:178` then treats a MISSING cell identically to a
  SUPPRESSED one. Different inputs reaching the same defect is what makes it a
  property of the code rather than of one fixture.
- **Finding 2** — unreadable AMOUNTS contribute 0 and are counted:
  `100 + null + '' + '$1,200' + '12abc'` reports **112 over 5 rows, complete:true**.
  Agreed with Hank that this is a DISAGREEMENT and not an oversight —
  `dnt-rollup.test.js:199` pins the zeroing deliberately. The objection is that
  nothing NAMES the unread fields and `complete:true` tells a client not to look.
- **NEW, not in Hank's review** — the sum accumulates in FLOATS: `0.1 + 0.2`
  reports `0.30000000000000004`. Low severity for a display report, and the same
  class as the recorded incident where two figures 4.5e-13 apart refused a
  correct bill and was fixed in integer cents.

**Not fixed by me.** I hold a review, not the file; a reviewer who lands the fix
stops being independent of it. Hank's reasoning, and it is right.

### Item 2 — BLOCKED, not skipped. Hank claimed it 0.1h before I looked

`hank / stonedesk / "drawing tool inside corner radius chamfer sink vendor
plumbing"`, claimed 14:42:26Z. The claim matcher blocked it and **the task string
was not reworded to slip past** (PR 4.3).

### Item 4 — the premise is wrong: it is BUILT, except the QR half

Verified per sub-feature rather than by filename, after the StoneDesk #5 lesson
from earlier today:

| claimed | real |
|---|---|
| two-way anonymous thread | **BUILT** — `public-complaint-thread.js`, `{token}` loads / `{token,reply}` appends; a patient reply reopens a Resolved thread to New |
| unguessable link | **BUILT** — `crypto.randomBytes(32).toString('hex')`, 256-bit |
| no PII ever captured | **BUILT** — the insert writes `license_hash, app_id, complaint_id, access_token, data, updated_at, submission_key`. No IP column; IP is used only by the rate limiter, in its own table |
| persistent nav badge | **BUILT** — `complaints-badge`, `rComplaintsBadge()`, counts `status==='New'` |
| QR distribution | **GENUINELY ABSENT** — zero `qr` hits in `sairndental.html`. QR exists in `sairndesign.html`, `stonedesk.html` and `tests/slab_scan_labels.js`, so the platform has the capability and dental never got it. What ships today is a plain text link |

All four complaint suites green. **The real gap is one sub-feature, not a
feature.**

### Item 6 — groundwork only, and the finding is better than the task assumed

190 non-test `Number(`/`parseFloat(`/`parseInt(` call sites, which is too many to
recombine responsibly in one pass. **The useful finding is that the platform has
ALREADY converged on two distinct policies independently**, and they are both
right for their own job:

- **a CONFIG read falls back to a DEFAULT** — `ai-rate-limit.js:117,135,139`,
  `anon-rate-limit.js:126,131`, `cron-jitter.js:68`
- **a MEASUREMENT returns NULL** — `ai-rate-limit.js:164`, `dental-bi.js:89`

`dnt-rollup.js:76` returns **0** for a measurement, which is the outlier — and it
is the same file whose own header says *"NEVER 0. Zero is a measurement."* A
canonical helper should encode the split, not a single "safe number" function;
one policy applied to both jobs would be wrong in one of them.

### Not started, and said plainly

Item 3 (SAIRNdental complaint QR half), item 5 (`sairn-resilience-patterns`
skill), item 78 (formal property verification), and the remaining three item 6
candidates. Not attempted rather than attempted badly.

---
## 2026-09-15 (later still) — the QR half, and a SOC2 answer that is "does not exist"

### Item 1 — QR distribution built, StoneDesk's pattern propagated exactly

`sairndental.html`: a QR on the Complaints panel plus a printable waiting-room
poster. `tests/dnt_complaint_qr.js`, 24 arms.

**The SRI hash is COPIED from `stonedesk.html`, not re-derived**, and an arm
asserts the two are byte-identical. Two hashes for one file is the
claim-in-two-places drift this repo keeps recording.

**The degradation path is the feature, not a nicety.** On a locked-down surgery
network a blocked CDN is the ordinary case. A silently missing QR reads as *"this
practice has no feedback channel"* — the opposite of what the feature says — so
the panel names the failure, says the link still works, and **disables printing
rather than producing a poster with a blank square on it.** Four arms drive that,
plus a control that it still works when the library loads.

**It does not auto-print.** `w.print()` fired immediately races the image decode
and prints a blank square; an arm asserts the call is absent.

**A self-caught scanner defect, the same shape I have recorded before:** my first
"no PII in the QR" arm searched the source for the word `patient` and failed on
the feature's own UI copy — *"no patient or practice data"*, which is the feature
working. Replaced with the real structural property: every `text:` handed to
QRCode must be exactly `cpQRUrl(...)`, plus a driven arm proving no adversarial
slug can smuggle a second parameter past `encodeURIComponent`.

### Item 6 — the answer is not "stalled vs progressing". Two of three do not exist

Searched 1668 tracked files:

| item | real state |
|---|---|
| SOC 2 readiness | **NO SUCH WORK EXISTS.** The only real hit in the repo is a string inside the CTO advisor's AI system prompt (`api/_lib/exec-context.js:169`) listing "HIPAA/SOC2 compliance" as an area of expertise. **That is an AI persona description, not a compliance programme** |
| NHI credential inventory | **EXISTS UNDER ANOTHER NAME** — `docs/SECRETS-INVENTORY.md`, generated, 18 CREDENTIAL / 5 ENDPOINT / 8 ADDRESS, with blast radius from the dependency graph and an absence-behaviour column that separates *fails closed* from *fails open*. Nobody searching "NHI" would find it. **Third time tonight** an item recorded as missing ships under a name nobody searched |
| incident-response plan | **DOES NOT EXIST.** `sairn-decision-gate` asks the question — *"is there a real monitoring and incident-response plan, or does 'we'll handle it if it happens' count as the plan"* — and on this platform the answer today is the second one |
| SAIRNlaw privacy scoping | **ZERO FILES** |

**AND THE ONE THAT EXISTS IS CURRENTLY REFUSING.**
`python tools/secrets_inventory.py --check` returns **REFUSING**: two new secrets
(`SAIRN_AI_CONTENTION_FLOOR`, `SAIRN_AI_TENANT_SHARE`) were added by another clone
with no classification, so the credential inventory cannot regenerate and the
published document is not currently true. **Not fixed here** — classifying
somebody else's new env vars is a judgement about what they unlock, and guessing
it is how a wrong blast-radius number gets published.

### Not started

Items 2 (three recombination passes), 3 (item 78 FPV), 4 (AI-proposes /
human-approves enforcement sweep), 5 (triage-plan staleness tool). Not attempted
rather than attempted badly.

---
## 2026-09-15 (later still) — the AI-approval sweep, and a scanner that was wrong twice before it was right

### Item 1 — `tools/ai_action_approval_audit.py`

**74 AI call sites across all 17 app files. 39 gated BY CONSTRUCTION
(render-only — the save is a separate click). 14 that write in the same handler
that received the model's answer. ZERO carrying an explicit approval gate.**

The zero is the headline and it is not the same as "14 defects". Most of what is
enforced here is enforced *structurally* — the answer goes to the DOM or a form
field and a person clicks save — which is a real control. What does not exist
anywhere on this platform is an explicit `confirm`/`approvedBy`/
`requireApproval` step inside an AI handler.

The 14 write through `sdData(`, `grdData(`, `st(`, `saveSD3Data(`,
`saveAndRender(` — real writes, not the model call. Whether each is a chat
transcript or a proposed business action needs a human read, which is what the
tool says it is for.

**IT WAS WRONG TWICE BEFORE IT WAS RIGHT, and both are recorded in its header
rather than quietly fixed:**

1. **Coverage.** The first pattern matched the literal `api/claude` and the named
   wrappers: 38 sites across **7** apps, while 17 app files mention AI. The
   missing ten hold the URL in a constant (`var PROXY='…/api/claude'`). A
   scanner reading one spelling reports a clean sweep over every app using the
   other — and it would have read as *"ten apps have no AI writes"* rather than
   *"this tool cannot see ten apps."*
2. **The AI call is itself a POST.** `method:'POST'` matched anywhere in the body
   counted as a data write, so **every** AI handler counted as writing and the
   headline read **59**. Caught by spot-checking three findings — `sdInvAI`,
   `commsAIReply`, `invSmartReorder` — whose only POST *was* the model call.
   Wrong in the direction that manufactures alarm, which is how a locator gets
   ignored. Real figure: **14**.

**And a third, which is a defect this codebase already documents and I committed
anyway:** the fix for (2) shipped with a **literal backspace byte** where `\b`
should have been, so the regex could never match and the fix silently did
nothing. Written through a shell heredoc that ate the escape — twice in a row,
including in the attempt to fix it. **The selftest caught it; reading the source
did not, on either pass.** Repaired from a real file rather than a heredoc.

Nine fixtures, both directions, locked before any real number was believed.

### Items 2–4 — NOT STARTED, and deliberately so

The SOC 2 readiness mapping, the NIST SP 800-61 incident-response plan, and the
SAIRNlaw privacy scoping. Each is a substantial document and **a half-written
compliance artefact is worse than none** — it reads as coverage to exactly the
reader who most needs it not to. Same reasoning as refusing to print a poster
with a blank square where the QR should be. Not attempted rather than attempted
badly.

---
## 2026-09-15 (final) — the IR plan's hierarchy corrected, item 78 measured, CRLF recombined

### The incident-response plan: structure corrected against the real source

Michael checked csrc.nist.gov (chat has network, no clone does) and confirmed the
Rev 3 supersession and the six Functions exactly as written. **One real
correction came back and is applied: it is not a flat list of six peers.**
GOVERN/IDENTIFY/PROTECT are a *preparation* level that supports incident response
without being it; DETECT/RESPOND/RECOVER are the incident-response layer; and
**Improvement is a Category INSIDE Identify**, feeding lessons back into all six.

Recorded as a correction rather than silently absorbed — *"written from memory"*
and *"checked against the source"* are different claims, and a reader of a
compliance document is entitled to know which one they hold. The remaining
unverified part is now named: **Category-level naming below §1–§7 has still not
been read against the publication.**

### Item 78 — essentially complete. The remaining gap is Java, not engineering

Verified by running, not reading:

- **CC's FINDING 4 is CLOSED.** `SPEC_NOT_CHECKED_HERE` exists and the run prints
  both uncheckable invariants with their reasons — *AppIsolation* ("requires
  presenting a token minted for one app to another… behaviour, not a role set")
  and *DeactivationBinds* ("the set of roles is unchanged by deactivation, so
  this file is structurally blind to it"). The disclosure CC asked for is there.
- Targets 1, 2 and 3 are built (Fourth), `no-app-key` is empty, 58 of 80 checks
  made, and the row's own words are *"there is no tooling gap left here."*

**The one thing genuinely missing is what every row already discloses: no TLA+
spec on this platform has ever been model-checked.** `command -v java` returns
nothing. **That is a one-line environment blocker, not an engineering gap**, and
writing a hand-translated model checker in JS would check a second copy of the
spec against a second copy of the invariants — the drift problem item 78's own
row warns about, introduced to solve it.

### CRLF-vs-LF recombination — `tools/line_endings.py`

52 files handle line endings independently. **Most are correct**, and they had
already converged on the right primitive: `io.open(..., newline='')` on both read
and write, which is what stops a read-modify-write silently rewriting every line
of a CRLF file.

**What none of them wrote down is that there are THREE jobs, and the recurring
defect lives in the one almost nobody writes:**

| job | who does it right | status |
|---|---|---|
| round-trip a file | ~50 files, `newline=''` | already correct |
| **compare two copies** | **nobody** | **the false-alarm class** |
| flip on purpose | `metamorphic_check.py:161` | correct, kept identical |

**The fix is not "normalise before comparing" — it is that the comparison has
THREE answers and everybody wrote two.** `tr -d '\r'` then compare collapses
*identical* and *differs only in line endings*, which is right for content and
wrong the moment somebody needs to know whether a file was rewritten.
`compare()` returns `IDENTICAL` / `ENDINGS_ONLY` / `DIFFERS`.

**Validated against the real recurring case rather than fixtures alone:** repo
skills vs the user store — **a bare byte compare reports 11 diverged; the true
answer is 0.** Every one is `ENDINGS_ONLY`.

It does **not** migrate the 52. Most are correct, and a mass edit across probes
that mutate tracked files is a poor trade — the module exists so the next one is
not a 53rd implementation.

### Not done

The negative-control-that-cannot-fail recombination. `tools/sabotage_control_check.py`
already measures the class, so it is instrumented but not consolidated.

---
## 2026-09-15 (last) — the negative-control recombination, and the tool was the problem

### `tools/sabotage.py` — plant a defect so failing to plant it is LOUD

Four approaches already existed here and **each is right about a different
failure**, which is why the module offers both planting strategies rather than a
house style:

| approach | catches | who does it |
|---|---|---|
| PRESENCE `anchor in src` | a rename | the common shape |
| UNIQUENESS `count != 1` | hitting the **wrong site** | `countersign_coverage_probe.py` |
| MATERIALISATION read back from disk | the write not landing | `sairncode_gates_mutation_control.js` |
| LINE-NUMBER ablation | ambiguous anchors entirely | `guard_ablation.py` |

`CouldNotSabotage` is an **exception, not a return value** — a caller who
ignores a returned `None` writes exactly the silent no-op the module exists to
remove. 19 arms, both directions, including that CRLF survives planting (a
control must sabotage **one** thing) and that `Planted` restores after the body
raises.

### AND THE MEASURING TOOL WAS UNDER-CREDITING THE BEST CONTROLS

`sabotage_control_check.py` reported **11 UNGUARDED**. Reading one of them —
`entitlement_freshness_control.py`, my own tool's control — found it already
guarded, by `once()`: `assert n == 1` on the original before use.

**Five of the eleven guard by COUNTING the anchor, which is strictly stronger
than the `anchor in src` shape the tool accepted.** Presence catches a rename and
is blind to four matches; a count catches both — and `guard_ablation.py` records
four real gates that `replace(..., 1)` would silently have collapsed into the
first one.

**So the signal was inverted: a probe that did the harder thing scored worse.**
Added the uniqueness shape, with fixtures in **both** directions — including a
negative one proving that counting the *checker's findings* still reads as
unguarded, so the pattern cannot be satisfied by any `.count(` at all.

**Measured: 11 → 6 unguarded, 39 → 44 verifying, of 50. Blind lock 14/14 → 17/17
and still run before the tree is read.**

**`CRITERIA_VERSION` was stale on the very run that accepted the new shape** —
it printed `2026-09-13.2` over criteria that had already moved. A version stamp
that does not travel with the thing it stamps is worse than none, because it is
read as evidence. Bumped, with the rule written next to it.

### CLAUDE.md corrected

It carried *"23 of 39 negative controls never verify their own sabotage"* as
standing guidance. Now re-measured in place with both figures and their dates,
the instruction **not to quote either from there**, and the note that part of the
improvement was the tool rather than the controls.

### Remaining 6, not migrated

`run_invisible_in_pattern_probe`, `run_literal_drift_determinism_probe`,
`run_master_plan_probe`, `run_new_checker_probe`, `run_testability_gate_probe`,
`run_traceability_matrix_probe`. Each needs its own reading — a mechanical
rewrite of somebody else's control is how a working control becomes a broken one,
and four of those six are already RED for unrelated pre-existing reasons.

---
## 2026-09-15 (continued) — two items already built, one answered, one blocked

### Items 1 and 2 — ALREADY BUILT by Fourth, verified by running

**Check 0e before building, and it paid twice.**

| item | state | verified how |
|---|---|---|
| **18** metamorphic relations | **BUILT** — `tools/metamorphic_check.py`, general-purpose and standalone, 5 relations (`identity`, `crlf`, `trailing_ws`, `blank_lines`, `duplicate`) | ran `--fixtures`: the blind lock passes and asserts the sensitive fixture is caught by every SAME relation and the robust one by **none**, so a violation would mean something |
| **28** the generator half | **BUILT** — `tools/new_checker.py` + `tools/checker_kit.py` | its scaffold's `rule()` **raises `NotImplementedError`** and the generated control treats that as "NOTHING was judged". Item 28's one stated property — a fresh checker exits 2, not 0 — holds |
| **32 / R5** sharper reachability | **BUILT** — extends `tools/sairn_reachability_check.py` (16 R5 references), not a second tool | `tests/run_reachability_r5_probe.py` exits 0 |

**The note in the brief — "extract the structural skeleton as a reusable
generator per item 28's fold-in decision, stated here so it doesn't quietly never
happen" — already happened.** `new_checker.py` is that generator, and its
argument is the one worth keeping: *a library is available; a scaffold is what
arrives already wired.* Every defect it was built against was a checker whose
author **had** `checker_kit.py` and skipped one of the three things anyway.

**R5's design decision is also already the one item 32 asked for**: report-only,
never gated to suggest removal, and it splits the inference by direction —
*observed* routes report today, *silent* ones stay gated, because "this route saw
zero" carries no information when almost every route saw zero. An inference from
silence needs a denominator; an inference from a served route does not.

### Item 4 — SAIRNlaw privacy scoping: the app answers a different question

`docs/2026-09-15-sairnlaw-privacy-scoping.md`. Every factual claim re-verified.

**`practice_area` IS FREE TEXT.** No option list, no `MATTER_TYPES`, no
validation; the two areas in the file are sample data. Measured across the app
and the deadline engine: `immigration`, `asylum`, `USCIS`, `I-130/485/N-400`,
`divorce`, `dissolution`, `child support`, `parenting`, `guardian ad litem` — **0
hits each.** The 7 `custody` hits are **all "AI Chain of Custody"**.

**So scoping Privacy to practice area would scope to something the platform
cannot observe, validate or control** — and a firm can change the answer by
typing, with no deploy.

**RECOMMENDATION: IN SCOPE, and drop the practice-area question.** Reached on the
data instead: `law_pimedical` holds personal-injury **medical records**, plus
`law_trusttx` / `law_opaccounts` / `law_bankstatements` (client money and bank
statements), `law_clients`, `law_portalmessages`, `law_portalesign`, `law_picases`
— and `law_barcerts` / `law_clecredits`, which are a **second data subject**
(employees). All ten confirmed registered.

**The method generalises and is the part worth copying: SCOPE FROM THE SCHEMA,
NOT FROM THE SALES DESCRIPTION.** And a correction to the question's premise —
**no vertical has a Privacy scoping document.** This is the first, so it is the
precedent rather than the exception.

Deliberately NOT done in it: no P1–P8 mapping (that would be the first half of a
compliance document with no second half), and no legal determination.

### Item 3 — NHI credential inventory: the real gap, and a blocker that is not mine

Not built, and the reason is specific rather than a shortfall of time.

**`docs/SECRETS-INVENTORY.md` covers ENVIRONMENT VARIABLES ONLY**, because
`tools/secrets_inventory.py` finds credentials by scanning code for
`process.env.X` reads. Three of the four identities the item names are therefore
**structurally invisible to it**:

- the **GitHub PAT** — used by a human and by CI, never read from `process.env`
  in this repo;
- **`sairn_backup_reader`** — a Postgres LOGIN role created by
  `sql/backup_reader_role.sql`, not an env var (and already carrying CC's HIGH
  finding: a published placeholder password made permanent by an idempotence
  guard);
- **each agent's own session access** — four clones with git push rights, whose
  credential is the Windows credential manager, not this repo.

So the deliverable is a **new register keyed on IDENTITY rather than on env var**,
with owner and scope per identity, complementary to the existing tool rather than
replacing it. **The env-var half is additionally blocked right now:**
`secrets_inventory.py --check` is **REFUSING** because `SAIRN_AI_CONTENTION_FLOOR`
and `SAIRN_AI_TENANT_SHARE` have no classification — another clone's two
decisions, and classifying somebody else's secret is a judgement about what
holding it lets you do.

Recommended as its own full slot, with the two unclassified secrets resolved
first.

---
## 2026-09-15 (continued) — the two refusals resolved, and an identity register that found 11 ownerless credentials

### Item 1 — `secrets_inventory.py` generates again

`SAIRN_AI_CONTENTION_FLOOR` and `SAIRN_AI_TENANT_SHARE` classified **TUNING**.
No live claim covered them; the session that added them had released.

**AND THE ANSWER CHANGED FOR A REASON WORTH RECORDING.** I refused to classify
these earlier on the grounds that judging somebody else's secret is a judgement
about what holding it lets you do. **That was right with what I had read and wrong
once I read the code.** `api/_lib/ai-rate-limit.js` documents both at the switch,
in its author's own words: the per-tenant sub-budget and the contention floor
inside the existing per-app AI ceiling, Michael's decision of 2026-09-15. Numeric
thresholds — they name no secret, grant no access, and their absence falls back
to a documented default rather than to zero, which the file says explicitly
because *"a zero share would cap every tenant at nothing the moment the floor is
crossed."*

So the classification is **derived from the author's own documentation, not
guessed.** Inventory: **49 variables — 18 CREDENTIAL / 5 ENDPOINT / 8 ADDRESS /
18 TUNING**, `--check` OK.

### Item 2 — `tools/nhi_register.py` + `docs/NHI-REGISTER.md`

**22 identities**, each with a named owner and a real scope. Keyed on IDENTITY,
not variable name — an env-var credential appears as *a credential belonging to
an identity*.

**IT FOUND ELEVEN CREDENTIALS WITH NO RECORDED OWNER ON ITS FIRST RUN**, and that
is the check working rather than a report about it: `OIDC_CLIENT_SECRET`,
`QB_CLIENT_SECRET`, `COURTLISTENER_API_TOKEN`, `STABILITY_API_KEY`,
`SAIRNCASH_FIREBASE_SERVICE_ACCOUNT`, `SAIRNCASH_STRIPE_WEBHOOK_SECRET`,
`SAIRNCASH_ADMIN_SECRET`, `ALF_PHARMACY_SECRET`, `DENTAL_BI_KEY`, and the two
rate-limit salts. Each scope taken from `secrets_inventory`'s own description of
what the variable unlocks.

**Two it is worth knowing are there at all:** `SAIRNCASH_ADMIN_SECRET` **renews a
trial without paying** — a paywall bypass held as a bearer string; and
`QB_CLIENT_SECRET` is provisioned while StoneDesk GAP 6 records QuickBooks
integration as **deliberately held open**, so it may be a credential for work
nobody is doing.

**Two derived halves make it a check rather than a list**, both refusing rather
than emitting a blank cell — the `tooling_inventory.py` convention:

1. every `CREDENTIAL` in `secrets_inventory.SECRETS` must be attributed to an
   identity;
2. every `create role` in `sql/` must appear. **Minting a login role is the act
   most likely to happen with nobody recording who owns it** — and the one it
   finds, `sairn_backup_reader`, carries CC's HIGH finding unfixed: a published
   placeholder password made permanent by an idempotence guard.

**`SAIRNCASH_STRIPE_WEBHOOK_SECRET` is a separate identity from `stripe-account`
on purpose.** `secrets_inventory` already flags the near-collision with
`STRIPE_WEBHOOK_SECRET` — two variables one word apart — and folding them into
one identity would re-create exactly that confusion.

**A blank `last rotated` means NOBODY KNOWS, not never**, and the document says
so. No clone holds any of these, so every rotation column is attested; none has
been attested yet.

**Limits stated in the file:** it cannot see an identity that exists only in a
console (2 of 22 rows are marked `attested` and cannot be derived), cannot verify
a credential is live or has the scope claimed, and does not check least privilege.

**The selftest crashed instead of reporting on its first run** — section 4 called
`render()` bare, so a real finding killed the selftest rather than being reported
by it. A selftest that dies on a real finding is one nobody can use to fix the
finding. Guarded; 7 arms, both refusal directions driven.

### Item 3 — held, as instructed

---
## 2026-09-15 — a register correction, and I OVERWROTE ANOTHER SESSION'S TOOL

### I destroyed Fourth's item-80 implementation and restored it

**The worst thing I did tonight, and it is first because it should be.** I wrote
`tools/reliability_growth.py` from scratch without checking whether it existed.
**It did** — Fourth built it in `dbfb4282`, and my Write replaced 356 lines with
318. Caught only because `git diff --cached --numstat` showed **deletions on a
file I believed was new**; the Write tool said "updated", not "created", and I
read past it.

**Restored from HEAD, byte-identical, and their blind lock runs.**

**THEIRS IS BETTER AND THAT IS THE PART TO KEEP.** It implements BOTH fitters
(Goel-Okumoto and Musa-Okumoto), **locks them against synthetic series generated
from KNOWN parameters and requires them to be recovered** — so its refusal is a
statement about the DATA rather than possibly a broken tool — and its admissibility
gate is three declared criteria with `MIN_DENOMINATOR`, a Spearman trend test, and
an `EFFORT_RECORDED = False` constant. Its own header records a defect the blind
lock caught before any real data was read: an `a_min` clamp copied across two
models with different semantics, correct for Goel-Okumoto's asymptote and wrong for
Musa-Okumoto's unbounded rate scale — the byte-identical-is-not-safe-in-context
shape. My version fitted no curve at all.

**Check 0e is the rule I already know and I ran it for item 18 and not for this
one.** The lesson is not "be careful": it is that `git status` before a Write on
any `tools/` path is the check, and reading the Write tool's own verb is the
second one.

**Item 84's event tree also already exists** — `tools/pra_event_tree.py`, and it
already refuses a frequency: *"UNKNOWN, and deliberately not estimated… six days
is not a rate"*, reporting end state and consequence tier separately and never
multiplying them. That was item 6 on the queue.

### The NHI register's backup-reader warning was stale, and it was mine

Corrected, and **verified rather than accepted**: `e40e146b` raises while the
placeholder is present (`sql/backup_reader_role.sql:97`) and rotates
**unconditionally** on an existing role (`:117`). Read both lines.

The row now says what is actually open: **the role exists live and whether it
holds the placeholder or the rotated password is UNKNOWN — not resolvable from
source, no clone has database access.** Register entry 101.

### Item 66 — BLOCKED, and the prerequisite is only half met

`injection_phase` did land: **77/77**. But an IBNR development triangle needs a
discovery LAG, which needs an injection DATE — and **only 4 of 77 records carry an
injection commit.** The other 73 say so themselves: *"NOT backfilled by blame:
reconstructing an injection point afterwards…"*, a deliberate refusal. Four points
is not a triangle, and blame-backfilling is the one thing the register declines to
do.

### Item 81 — NOT MEASURED, and I will not quote the number I got

A first pass reported 24 of 25 `api/` files with retry logic and no backoff.
Spot-checking three killed it: `sv-witness.js:462` is the word "retry" in a
comment, `safe-number.js:30` is my own comment about a retry count, and that
file's "backoff" hits were my own citations of `cron-jitter.js`. **The figure is
prose.** Same shape as the AI-approval audit's 59→14, caught the same way.

### Items 67 and 70 — not started

70 needs a decision I cannot make: it deliberately breaks a live scheduled job,
and `api/cron-watchdog.js` alerts by email **only if** `RESEND_API_KEY` and
`RESEND_FROM_EMAIL` are set, which no clone can verify. **Killing a cron to test a
watchdog that may not be able to alert is a real outage with no observer.**

---
## 2026-09-15 — the Money type, item 67 measured, and a bug class that now has a name

### Check 0e ran FIRST this time, on all three, and it caught one

Item 2 (**item 38, completeness checking**) is **ALREADY BUILT** —
`tools/completeness_check.py`, and its own header already states the exact
scoping the brief asked for: *"the pair of item 90 rather than a copy… item 90
makes a class impossible to WRITE… IT CANNOT REACH legacy code that never had a
boundary, and it cannot reach external input BEFORE it is parsed."* Three shapes,
each narrowed by a real false positive. Runs, exits 1 report-only.

Seventh already-built item. **Not rebuilt**, and this time 0e ran before a Write
rather than after a numstat.

### Item 1 — `api/_lib/money.js`, item 90's constructive half. 31/31

`shape_antipattern_check.py` (Hank, live) already **detects** the shape and names
`Number(payload.amount)` at `api/sd-data.js:11796` among others. This is the type
that makes it unwritable.

**Two holes in three lines, and the platform has paid for both:**
`Number('')` / `Number(null)` / `Number([])` are all **0**, so an absent field
becomes a real number; and **`amount <= 0` CANNOT SEE NaN** — every comparison
against NaN is false — while `!(amount > 0)` can. That second one was a **live
hole on attorney trust money**. §3 of the suite *demonstrates* both on raw numbers
beside the typed version, so the comparison is on the record and not only in a
comment.

**The mechanism that makes it structural rather than advisory: `valueOf`,
`toString` and `toJSON` all THROW.** `money + 1`, `money > 0`, `` `${money}` ``
and `JSON.stringify(money)` each fail **at the line that did it**, because every
one of those is a path back into unchecked arithmetic. Plus: construction is a
parse that returns `{ok,…}` with no constructor that takes your word for it; the
brand is a **Symbol** so an object literal cannot forge one; the object is frozen;
and arithmetic accepts only Money, so `plus(5)` throws.

Integer cents throughout. **`'3828.47'` and `3828.47` produce the same integer** —
the 4.5e-13 case that refused a correct bill, with an arm named for it. Dollars
scale **on the string**, because `12.34 * 100` is `1233.9999999999998`. Reuses
`safe-number.js`'s `measureNumber` rather than re-deciding the parse. No currency,
no locale parsing, **no `divide()`** — splitting money is a decision about who
gets the remainder cent.

### Item 3 — `tools/ooda_phases.py`, and the measurement is the finding

**73 of 73 resolvable records were fixed the SAME DAY they were recorded.
Detect-to-fix is zero across the whole register.**

So the only phase this repo times is already as fast as it can be, and **every
second of real exposure lives in a phase nothing times.** The aggregate would show
a platform with no problem. The one real Observe-phase number anybody has is the
cron incident — **silent 24 hours** — and its worse sibling, `send-reminder.js`
returning 500 **every hour for months** on an env-var name mismatch: an Observe
phase in months against an Act phase in minutes.

It **publishes no aggregate**, deliberately — three of four boundaries are
unrecorded, and one-of-four components is the denominator-over-the-subset error.
It reports the one `-25 day` record as an **ANOMALY** (the cited commit is not the
fix) rather than averaging a negative duration away.

**Item 66 and item 67 are blocked on ONE field** — an injection date. 4 of 77
records have one. Worth knowing before either is scheduled again.

### A recurring class that now has a name, because it bit FOUR times today

**A TEXT MATCH COUNTS A WORD'S APPEARANCE IN PROSE THE SAME AS ITS APPEARANCE IN
LOGIC — and the better the prose explains the absence, the more likely the
checker reports the thing as present.**

1. QR suite — "no PII" arm fired on the feature's own copy, *"no patient or
   practice data"*;
2. Tier A gate — the fail-open arm fired on a docstring quoting the old line;
3. `money.test.js` — "no `divide()`" fired on the comment saying why there is
   none;
4. `ooda_phases.py` — "no mean" fired on its own printed sentence *"a mean hides
   it"*.

**It is distinct from the already-logged "quoting old code in a comment" variant**,
which is a special case of it. The defence is to assert on a **structure prose
cannot contain** — an arithmetic mean needs a division by a count, so look for
`/ len(`, not for the word. Both fixes now carry a CONTROL asserting the prose
still contains the word, so the strip stays load-bearing.

---
## 2026-09-16 — item 89 answered from arithmetic, item 46 built

### Item 89 — ALREADY BUILT AND CORRECT. The answer is no-and-yes.

**Confirmed from the threshold arithmetic, not from a word search** — which
mattered, because `chance_expectation()` exists and a text search for
"Bonferroni" or "look-elsewhere" would have found nothing.

**It DOES account for the trials factor**, and in the right way:
`chance_expectation(n, runs, per_run_flip)` is computed and **published as a
number rather than applied as a silent correction**, at three assumed flip
probabilities (0.005 / 0.01 / 0.02), each labelled **ASSUMED, not measured**. The
docstring gives the reason it is not calibrated from the ledger: deriving the
chance rate from the same observations it judges is the validation-eats-its-own-
subject shape.

Live, right now: **46 checkers** (the fleet grew from 33), typical 6 runs — so
1.4–5.3 would be expected to show ≥1 disagreement by chance. Observed: **0 with
exactly one disagreement, 1 with more than one.** The report splits those two
deliberately, because *multiplicity explains singles and does NOT explain
repeats*, and carries a cross-check arm because the split is computed from a
different field than the verdict column.

**But the protection against the worry as posed is a DIFFERENT mechanism, and I
had to measure to find it.** A corrected threshold is not what stops volume
quarantining a good checker — `classify()` returns **WATCH whenever
`disagreements == 1`**, checked *before* the rate comparison, at every run count.
Measured:

| runs | 1 flip | raw rate | vs QUARANTINE_AT 0.05 | verdict |
|---|---|---|---|---|
| 4 | yes | 0.250 | **over** | WATCH |
| 5 | yes | 0.200 | **over** | WATCH |
| 10 | yes | 0.100 | **over** | WATCH |
| 19 | yes | 0.053 | **over** | WATCH |

**Without that branch all four would QUARANTINE.** It is load-bearing, and it is
pinned by fixtures at the fleet's *actual* run counts (6 and 12) — the exact
sub-20 window where the raw rate trips the band. `WATCH_EXPRESSIBLE_AT =
ceil(1/QUARANTINE_AT) = 20` exists to document that boundary.

**Nothing to build.** Volume alone cannot quarantine a checker.

### Item 46 — `api/_lib/record-parity.js`, 25/25

RAID-style single parity over append-only records. **Item 35's hash chain
DETECTS; this CORRECTS.**

    hash of a row        -> "row 412 is wrong"
    hash CHAIN           -> "row 412 is wrong, and it starts there"
    parity over a group  -> "row 412 said EXACTLY THIS"

They compose rather than compete: the chain says *which* row to reconstruct, and
the digest **verifies the reconstruction** — `recover()` refuses to return bytes
whose digest does not match the one recorded when the group was built. Parity
without a digest hands you bytes you cannot check.

**Length is part of the problem, not a detail.** XOR over variable-length records
loses the lengths, so the parity block is padded to the group width and each
member's length is stored — the short-record arm proves no padding survives on
the recovered bytes. Canonical form is `sv-witness.js`'s, reused in spirit: two
encodings of one record must give the same bytes or a reconstruction fails its own
digest.

**The refusals are the substance:**
- **two erasures** → `PARITY_TOO_MANY_MISSING`, naming Reed-Solomon as the real
  remedy rather than implying it is here;
- **a changed survivor** → caught *before* it poisons the XOR. This is the
  sharpest one: a drifted survivor produces nonsense that would pass no check,
  and only the recorded digest makes it detectable;
- **a group of ONE** → refused, because **with one member the parity block IS the
  record** — a second plaintext copy of a controlled-substance entry stored as
  redundancy;
- a duplicate member id → refused, because the survivor set becomes ambiguous.

**Three things it does NOT claim, each asserted by an arm so the header cannot
drift into an overclaim:** it is not a backup (parity beside the rows dies with
them, and this platform takes no automated backups); it **narrows** the
creation-time exposure window rather than closing it (parity needs the plaintext
at write time — there is no way around that; what it removes is needing it *again*
at recovery); and it is not encryption.

**Not wired into `sv-witness.js` yet** — the library and its control are the
reusable core; choosing a group size for the live register is a real decision
(smaller groups survive more loss and cost more parity storage) and it belongs
with whoever owns that table.

### Item 86 — not started

---
## 2026-09-16 — item 86 built, and three items measured rather than assumed

### Item 86 — `tools/bypass_log.py`, wired into both override sites

**What the override was before this: `SAIRN_SEED_GATE=off` returns from the hook
before a single check runs** — the seed gate, the Tier A review gate, the
generated-document check, all of them — **and nothing recorded that it
happened.** A switch labelled for one purpose that disables ten, with no log.

The three battleshort requirements, and one of them was already satisfied:

- **(a) a NAMED check, never all-safety-off** — the blanket form is now recorded
  as its own, worse category, and `KNOWN_CHECKS` names the eleven real gates so a
  named bypass has somewhere to land. **The blanket form is NOT deleted, and that
  is deliberate**: a battleshort exists because sometimes you must ship, and
  removing the only escape hatch from a blocking gate pushes the next emergency
  into `--no-verify`, **which nothing logs at all.**
- **(b) time-bounded, self-reverting** — *already true and not "fixed"*.
  `SAIRN_SEED_GATE=off git push …` is a shell assignment scoped to ONE COMMAND;
  it cannot outlive it, so there is no switch left flipped, and a timer would be
  strictly weaker. The clock is enforced only on a **standing** bypass — the one
  shape that genuinely can be left on — where **no `expires_at` is INVALID rather
  than permanent**, because that is the switch nobody flips back.
- **(c) its own log, so repeats become a pattern** — this is the half that changes
  behaviour. **`PATTERN_AT = 3`, low on purpose**: a threshold high enough to feel
  safe is one nothing reaches. And the output says the thing that matters —
  *a check people legitimately need to bypass is MIS-SPECIFIED; the action is to
  fix the check, not to ask whoever keeps bypassing it to try harder.*

**Driven end to end, not asserted.** A real `SAIRN_SEED_GATE=off git push` payload
through the real hook wrote a real row and still exited 0. **The synthetic row was
then deleted** — a fake entry in an audit log is worse than an empty one.

**And the fail-safe is proven, not claimed.** I replaced `bypass_log.py` with
`raise ImportError` and re-drove the hook: **exit 0, no stdout noise.** A blocking
gate that refused a push because its own *logging* failed would turn bookkeeping
into an outage. The cost is a missing row, which is why the reporter states that
**an empty log is evidence about the HOOK, not about the platform** — `--no-verify`
and a direct API push never reach it.

Control: with no override, the gate still runs and produces output.

**AND THE WIRING WAS POLLUTING THE AUDIT LOG, caught from the staged diff.**
`tests/push_gate/refspec_and_override_probe.py` drives the real hook with a real
`SAIRN_SEED_GATE=off` payload — correctly; that is its job — so wiring the logger
into the override site meant **every suite run appended a row.** Within a few runs
the log would be mostly probe rows and **`PATTERN_AT=3` would fire on `ALL` from
the probe alone: a pattern detector reporting its own test harness as the
pattern.**

Found by `git diff --cached --numstat` showing **1 insertion in a file I had just
deleted** — the same check that caught the overwrite two rounds ago.

**Fixed as a REDIRECT, not a suppression.** The log path is env-overridable and
the probe points it at a throwaway file, so the write really happens and lands
somewhere that is not the audit record. **Skipping the write under test would
leave the wiring never actually exercised**, which is the fail-open shape.
Verified both ways: a full probe run leaves the real log absent, and a redirected
drive still writes.

### Items 72, 74, 26 — not built, and each for a different real reason

**Item 72 (practitioner validation) — the named prerequisite does not exist.**
`sairn-onboarding-designer` is in neither the repo's 33 mirrored skills nor the 61
in the user store. The task says to *point it at* a new purpose; there is nothing
to point. And the substance is not code: getting a real veterinarian, nurse,
funeral director, attorney or dentist to use these apps is a **recruitment and
scheduling act**, and nothing I build can substitute for it. **A click-through by
me is exactly the substitute the item says not to accept.**

**Item 74 (schedule-pressure cross-check) — no deferral record exists to check.**
Nothing on this platform records *why* a check was skipped. The push gate logs
overrides only as of today (above); `run_all_tests.py` reports SKIPPED but not a
reason; and the defect register has no deferral field. **The honest first step is
that the bypass log built today is the beginning of the data item 74 needs** — a
bypass carries a `reason`, and once there are reasons there is something to
cross-check against defect timing. Building the cross-check first would be
building a query over an empty table.

**Item 26 phase 2 (tiering re-check + Copy-Exactly sweep) — not started**, and
the honest note is that `copy_exactly_check.py` already exists with a recorded
decision NOT to promote it, because its output is a known-open state a push cannot
change: 0 of 5 identical on 2026-09-14, four differing because the APP was fixed
and the must-copy-exactly DOCUMENT was not. **Wiring an automatic sweep onto a
checker whose current output is four stale rows would fire on every confirmed
defect and say nothing.** The document and the app agreeing is the precondition.
## 2026-09-16/17 — twelve red suites cleared, and the one that was never actually red

### The headline is not "twelve fixed", it is that ELEVEN OF TWELVE WERE THE PROBE

Every one of these was a suite reported RED. Eleven of them had nothing wrong
with the thing they test — the CONTROL had rotted, been miswired, or was pinned
to a number the app had legitimately moved past. **A red control is not evidence
about the subject, and a green one after a rebaseline is not either unless
somebody looked at what moved.** Each rebaseline below names the commit that
moved it.

### Mutation 9 — the licensing gate was NOT undetected, and that correction matters

The diagnosis handed to me said *deleting the licensing gate from sd-render.js
currently ships completely undetected*. **It does not.** `api/license-trial-gate.test.js:233`
asserts the gate's condition is present in all three handlers and goes red when
it is removed — proven now, not argued.

**What was actually broken is the probe's anchor.** It was the literal line
`if (!isPaid && lic.trial_ends_at && ...`, and `isPaid` was split into
knownPaid / knownNotPaid / cannot-tell (the three-state fix at
`api/sd-render.js:164-177`). The line stopped existing byte-for-byte and the arm
reported **ANCHOR-0** from then on — so the one mutation asking *"does deleting
the whole licensing gate get noticed"* had never been run. **The gap was in the
evidence, not in the gate**, and those are different repairs.

**It reported rather than skipped, which is the only reason it was found.** A
probe that treated a dead anchor as a pass would have been printing nine-of-nine
green over a live security gate nothing was testing.

Fixed as a **compiled regex, not a line**, for the same reason arms 1 and 2
became JSON transforms: say what to change, not what the bytes around it look
like. `main()` still requires exactly one match. 10/10 bite.

### The truthy-sum occurrence — assessed, then burned down rather than baselined

`api/audit-checkpoint.js:396` sums `r.written`. **Not a defect**: `written` is
produced 130 lines above as either the literal `0` or `written.length`, and
`verifyTable()` returns no `written` at all. Nothing outside the module can put
a string there.

**Wrapped in `Number(...)` rather than added to the baseline**, deliberately. A
baseline entry is a standing claim somebody has to keep true; the coercion is
one word and cannot go stale. The baseline file's own instruction is *"to burn
one down: wrap the term in Number(...)"*.

### Cluster A — three pinned counts, one app that grew, and the third column CLOSED

`sairnbiz` moved 13/11/2 → 14/14/0, and **the 2 going to 0 is the interesting
half**: `local_only_shape_probe` recorded sb_po and sb_recv as an OPEN FINDING —
business records with no route to a server. **20afb167 gave them a server call
each.** The finding was RESOLVED, not relaxed, and the checker now lists both as
`named resource`. The fourteenth collection is `sb_ts` from the timesheet work
(b8f40738, a3c44c24), also covered. All three baselines restated together with
what moved, because fixing one would leave the other two reading as separate
defects.

### Cluster B — a test double is a SECOND COPY of a signature

Both probes stub `run_all_tests._run`. `_run()` grew a third return value
(`retried`, the one re-run CONCURRENCY_SENSITIVE files get) and both stubs still
returned two — so every arm died on `ValueError: not enough values to unpack`
**before reaching a single assertion**. The runner was fine.

**Fixed by asking the real function rather than pinning an arity**:
`_GREEN = _run([], [], quiet=True)` — with nothing to run it spawns no
subprocess and returns its own empty result. A fourth value would arrive here
the day it arrives there. Same two-copies-of-one-idea shape the floor probe's
own header describes for `_main_body`/`_hook_body`.

### Cluster C — cleared by B's sibling, as predicted, and the arm was testing the wrong property

`run_app_attribution_probe`'s control asserted the UNALIASED `app_of()`
attributes **zero** files to SAIRNroofing. That held only while no test file was
literally named `sairnroofing*`. One was added (`tests/sairnroofing_fault_probe.py`,
c03646fb) and the name matcher reached it correctly. **The arm went red over a
correctly-added file.**

What the control actually needs is the DELTA — that the ALIAS LAYER, not the
name matcher, moves the bulk. Restated that way (30 aliased vs 1 unaliased, plus
an arm requiring every unaliased hit to carry the app name outright) it does not
rot the next time somebody names a file after an app.
`run_app_attribution_mutation_control` went green with it: **43/43, no second
defect.**

### Cluster D — the diagnosis was wrong, and the real cause is structural

The note said these three *"read the verdict the whole gate stack returns"*.
They do not — `check4_probe` already discriminates on `blocked_by_seam` and
`names_field`. **The real cause: all three build a worktree at LOCAL HEAD, and
in a five-clone repo local HEAD is behind origin/main most of the time.** The
gate then refuses with *"the outgoing range <remote>..<local> could not be read"*
— correctly, because the remote tip is not an object this clone has — **before
the check under test is ever reached.** Measured: both check4 arms exit 1 with
every reason flag False.

Three repairs, and the first is the one that matters:

- **the worktree is built on the FETCHED remote tip**, so the outgoing range is
  exactly the fixture commit;
- **one retry after a fetch** when the range is unreadable — the remote tip moved
  *mid-run* on 2026-09-16 while check7 was between arms, which is how a five-clone
  branch behaves and is not a flake to paper over;
- **`could_not_run` is a third state and exits 3**, never folded into a verdict.
  `blocked_by_seam: False` means *not asked*, not *not blocked*.

**The refusal TEXT is now in the reported dict**, and it paid for itself
immediately: the flags were all False and the text named the real reason on the
first run after it was added.

All three green, for the right reason.

### Tier A sabotage coverage — 41 → 44, and one control found a real gap in its suite

- **`api/sd-data-numeric-guards.test.js`** (law_trusttx — attorney client trust
  money), 6 mutations. **Arm 5 was SILENT and that is the finding**: the arm
  pinning the NaN-blind guard tested the negated-form regex against the WHOLE
  file, and that expression appears **twice** — sen_payer_contracts and
  sen_pay_rates, four hundred lines apart. Rewriting either back to `<= 0` left
  the other satisfying the regex. **The suite now carries one arm per site**,
  anchored on the push target that belongs to each branch, and arms 5 and 6
  break one site each so neither can be satisfied by the other. 10/10 after.
- **`api/sd-data-sb-void-role.test.js`** (sb_po/sb_recv voids — a money
  decision that replaced a CLIENT CONSTANT), 6 mutations including the
  un-void direction, could-not-tell folded into a pass, and **the other
  direction**: a gate that fires on every write rather than on the transition,
  which locks staff out of raising a purchase order. 10/10.
- **`api/sd-data-mech-credentials.test.js`** (EPA 608 — a federal certification),
  8 mutations. **A suite made mostly of refusals is one a gate that refused
  EVERYTHING would satisfy**, so mutation 8 goes the other way: eligibility
  answering rather than refusing an empty requirement list — *"anyone may go"*.
  12/12.

### The measurement, and where it is weaker than the last one

`python tools/run_all_tests.py` **in this clone**, not in a detached worktree at
origin/main — stated rather than glossed, because the twelve fixes live in the
working tree and a worktree at origin/main could not have shown them recovered.
**411 files, 1 SKIPPED** (check9_probe, a precondition, NOT a pass), **17
failing, down from 32.** Every removed row was also run ALONE and read arm by
arm.

**Three of the removed rows were the load-only-red ones I was told NOT to
force-classify** — `sairnlaw_billing_codes`, `stonedesk_server_backup`,
`sairncare/test-alf-alerts-endpoint`. They passed in the full run this time.
**That is not proof they are sound**; it is one more observation of a
load-sensitive shape, and they stay out of CONCURRENCY_SENSITIVE.

**And one row is NEW and is NOT MINE.** `tests/defect_register_capa_control.py`
— three arms that drive `--factors` and expect exit 0 now get exit 2. **378db57e**
*(refuse a defect record whose commit changed nothing but bookkeeping)* added a
refusal that fires on the control's synthetic record. **The CONTROL went red,
not the tool** — the refusal looks correct and the fixture is what has to move.
Left for that commit's author: a control rewritten by somebody who did not add
the rule is a control fitted to the behaviour it found.

### Not done

`run_invisible_in_pattern_probe` still refuses on a stale anchor — **its guard
working as designed**, and it needs a new anchor cross-referenced against
`mutation_anchor_probe`'s own tracked bad anchors, which is a separate piece of
work rather than a line change.
## 2026-09-25 — the H1 retier queue confirmed landed, and SAIRNscape's two Tier A rows stop answering on a licence key

### First, the queue I was sent at was already done, and saying so is the work

The recap listed seven retiers plus two app fixes as "confirm actual state,
then continue with whichever of these are not really done." **All ten were
already on disk**, read out of `docs/CRITICALITY-TIERS.md` and
`docs/defect-density-register.json` rather than taken from the recap:
`sd_approvals` A/A, `law_picases` A/A, `law_clerequirements` A/B, `sc_pctc`
A/B, `sb_perf` A-conf with its role gate, `alf_signals` A-conf,
`alf_activities` A-conf, `sb_vends` confirmed B/B, plus the `rf_buildings`
absent-as-null upsert fix and its register row. **The register update the
recap flagged as unconfirmed was present** (`a5d120f1`, now `6d80e387`).

What was NOT done was landing them. The branch was 8 ahead and 2 behind, and
the push failed twice for two different reasons worth recording:

- **A conflict in `docs/tier-a-reviews.json` on BOTH rebases**, and both times
  the resolution was the same shape: two sessions appended an obligation at the
  same array position, so `git` presented them as alternatives when they are
  both real. Resolved by keeping both objects, not by picking.
- **The push gate refused the range** with *"TIER A CODE CHANGED AND ONLY PART
  OF IT IS RECORDED"*. The H1 batch obligation names four resources;
  `72c69220` also touches `api/_resources/sairncode.js`, which serves six
  Tier A `sc_*` rows. **The gate is right and the distinction is the point** —
  an obligation covers the resources it NAMES, not the ones a later commit in
  the same push happens to touch. Opened a second obligation scoped to that
  commit alone.

**And one citation was re-anchored twice**, which is the cost of rebasing a
record that cites its own sha: the H1 obligation's `what` cited `a23c6344`,
then `093d08d6`, and is now `b2764261`. A citation a reviewer cannot resolve
is exactly the drift `tools/register_freshness_check.py` exists for.

### Then the open item: SAIRNscape's two Tier A resources

All twelve SAIRNscape resources dispatched on the licence hash with **no
session check of any kind**, and the licence key is shipped to the browser —
so the key was the whole authorisation. Two are Tier A on integrity:
`invoices` (money) and `scp_quotes` (the priced quote every invoice descends
from). Same shape as `law_trusttx`, `SF_RESOURCES` and `SDN_RESOURCES`;
SAIRNscape was swept with none of the three.

**The name is the part that makes this fix failable in silence.** SAIRNscape
claimed the bare name `invoices` before the `scp_` convention existed — the
storage table is `scp_invoices`, the RESOURCE the dispatch tests for is
`invoices`. A gate written against the table name gates nothing and **every
refusal arm anywhere still passes**. The suite carries an arm whose only job
is that distinction, and mutating the entry to `scp_invoices` takes it to
16/18 — so the trap is driven, not merely described.

**No client change was needed, and I measured that rather than asserting it**,
because "no diff to review" is when a claim most needs checking:
`scpData()` attaches `X-SD-Auth` on every call whenever a token exists with no
per-call flag to forget (the thing that had to be repaired in
`sairndesign.html`, where 18 of 19 call sites never passed it); every call
site for both resources goes through that one helper; and both login paths
store the token before `scpApplyLoggedIn` → `scpInit` → `scpSyncFromServer`.
Three arms assert all three against the shipped page.

**Driven to fail in three directions before it was believed:** removing the
`SD_SESSION_GATED` entries → 9/18, removing the `SD_GATE_APP` pins → 11/18,
renaming to the table name → 16/18.

Three existing suites moved with it. `api/sd-data-invoices-amount.test.js` was
writing `invoices` with no session and now 403s before the amount guard is
reached — **a 403 and a 400 INVALID_AMOUNT are both "refused" and only one is
what that file exists to test** — so it signs a real session against the hash
the handler DERIVES from the bearer key rather than a typed constant.

### A measurement gap found while closing it, recorded and NOT fixed

`tests/app_session_isolation.js` counts a resource as gated only when it
answers **401**, and `SD_SESSION_GATED` answers **403**. So SAIRNscape still
measures posture `NONE` with two resources gated, and **sairndesign's row has
read "1 of 18" since September while nine of its resources sit in that
table**. The column that exists to notice an ungated app cannot see the
commonest gate on the platform.

Left open deliberately. Widening the comparison to 401-or-403 would silently
re-measure fourteen other rows inside a commit about SAIRNscape, and which
codes count as a gate is the premise the whole column rests on.

### Not done

The other ten SAIRNscape resources stay licence-only — the same Tier A
stopping rule the `sdn` and `sf` gates used. Whether a crew member may read
the schedule, the customer list or the progress photos is a product decision
nobody has made; `scp_vendors` is driven in the new suite so the day somebody
makes it, the widening is visible rather than silent.

---
## 2026-09-26 (Cody) -- cody-q11, eight items, all eight closed

Claim `cody-q11`, released on writing this. Every commit pushed and each
generated document re-checked at the new HEAD after every rebase. Item 5 was
already done by an earlier session and was **not** redone -- confirmed, not
assumed: the correction marker is in
`docs/superpowers/specs/2026-09-02-stonedesk-worldwide-competitive-gap-audit.md`.

**A LEXICAL CLAIM BLOCK, DECLARED PER PR 4.3 RATHER THAN REWORDED.**
`sairn_claim.py` blocked on `cc-queue11` over the shared tokens
`sairncode`/`rules`/`scoping`. Read cc's actual files -- `docs/CRITICALITY-TIERS.md`,
`tools/sairn_push_gate_hook.py`, `api/_lib/compliance-rules.js`,
`docs/2026-09-26-sairncare-compliance-join-scoping.md` -- verified disjoint from
mine, and wrote the claim with the note recording why. The task string was not
changed to slip past the matcher.

### 1. PR 2.5 -- a rebase conflict in a derived document is re-derived

`e1943b32`. The habit existed and was written down nowhere: `d431fdd1` did it
right once and `git log --grep=rebase` shows a long line of
`chore(generated): regenerate after rebase` commits doing it from memory.

Three things the section adds that the habit does not. **Why** a text merge is
specifically wrong -- a generated document is a function of repo state, the two
sides are that function at two different states, and a resolved hunk is it at *no
state at all*, with headline counts from one side and rows from the other and
nothing looking damaged. **The cost is already paid**, on the register with no
generator: `docs/tier-a-reviews.json`, 2026-09-23, a hand-resolved conflict kept
both records and took the wrong side for one record's status fields, so the
discharge commit said the review happened and the register said it was open.
**And the push gate does not reliably catch it** -- check 12 blocks when the base
was clean and NOTICEs-and-allows when the document was already dirty at the base,
which a rebase window is exactly when.

Plus the case no resolution habit reaches: `6ad42dc0`, where a CLEAN rebase left
two generated docs stale because the other clone added tools without touching my
copy. **I then hit that case myself in this session** and it is why every push
below carries a post-rebase `--check` run.

### 2. PR 1.13 -- the waiter sweep, and two questions instead of one

`56887cd5`. Nothing committed on the tooling side carries the fragility
`tools/wait_for.py` fixed, and the method is in the section because a negative
with no method behind it is worth nothing: five axes, and each candidate is clean
for its **own** reason rather than one rule nine times.

**The generalisation the sweep produced:** if the subject died right now, (a)
would this loop ever stop, and (b) would it SAY anything? `wait_for.py`'s
fourteen-hour incident was (a). The one real find fails only (b).

**The find is in the app layer**: ten bounded-and-silent waiters in
`stonedesk.html`, each `setInterval(...,200)` for a global with a
`setTimeout(clearInterval,10000)` beside it and **nothing on the give-up branch**.
Eight wait on `window.addMsg`, which is never defined -- every
`window.addMsg =` sits inside an `install*Hook()` that returns early unless
`window.addMsg` is already a function, so the chain has no head. `:23534` waits
on `window.sendMessage`, which IS defined at `:13272`, so it never fires.
`:23486` waits on a DOM element. **Same silence, three different live behaviours,
which is why each was read rather than counted.**

**NOT FIXED, and this needs Michael.** `stonedesk.html:22686` already records the
state, *proven in the browser*: "window.addMsg is not a function on the live page,
so installMarkdownHook() bails." That comment is the cost of the silence stated
exactly -- somebody had to open a console to learn what one line on the give-up
branch would have printed on every page load. But the same comment records that
one of these hooks paints near-white text on a white bubble, so switching nine
unreviewed interceptors on is a product decision, not a waiter repair.

**And `wait_for.py` is UNWIRED with NO PROBE** -- `git grep` finds it only in its
own source, the generated inventory, and the generator's PURPOSES map. A fix that
lives only in the file that fixed it cannot reach a session typing an inline loop
from memory, which is how the fourteen-hour loop was armed. Recorded as
unexercised too, rather than recommended as if it had been driven.

### 3. The 2026-09-26 corrections land on the ORIGINAL 08-26 and 08-27 audits

`9021f048`. The corrections existed -- in the 09-17 re-derivations and in
`docs/2026-09-26-gap-triage-four-verticals.md` -- and the two documents a reader
actually opens carried none of them. That is the 08-26 audit's own 0.1 failure
one layer out: the correction is written, in a file nobody is pointed at.

The 08-26 banner's sharpest sentence -- *"exactly one, SAIRNdental B2, is
genuinely still open"* -- is wrong in both directions: B2 is closed, and the
banner never covered the rows that ARE open. For 08-27 the correction that matters
is **G3 is CLOSED IN OUR OWN PRODUCT**: the 09-17 pass's headline was that
SAIRNmechanical had reproduced the market gap it documented, and
`mechData('eligibility')` now ships at `:2474` with `eligibility` 1 -> 15.

**EVERY COUNT RE-MEASURED RATHER THAN COPIED, and that is the only reason the
mechanical block is right.** `COI` moved 0 -> 4 and `permit` 0 -> 4 since 09-17 and
**neither is its gap row moving** -- COI is a company-insurance panel that says
"not what a technician holds", the opposite object from G2; permit is a doc-type
list plus a disclaimer that output is NOT "permit-ready", the opposite of G8.
Copying the 09-17 table forward and trusting the deltas would have closed two
absent rows.

### 4. SAIRNcode scoped against the cloud wide-lens audit

`8e112b7b`, `docs/2026-09-26-sairncode-cloud-audit-scoping.md`. The dispatch
blocker was resolved rather than confirmed: the research is on
`origin/claude/wizardly-ride-wtun13` (PR #18, open, unmerged), 9 files, 7,732
insertions. Eight docs plus a handoff, not seven. PR #18's red check is
GitHub-side -- the Copilot scanning agent errors "model not supported" before
analysing anything and has failed its last 8 runs across three PRs.

**Three rows the cloud docs carry as open are closed**, and the cause is
structural: cloud correctly declined to re-derive the internal 09-23 baseline, so
every verdict three days old travelled in unchecked. GP modifier closed
2026-09-23, the same day it was found. A2's eligibility edge closed 2026-09-24.
**And A1's exception queue was never missing** -- `scRouteCodedItems()` at `:7393`
has split two tables since 2026-08-20. The audit searched for the word
`autonomous` (genuinely 0) and read that zero as the mechanism's absence.

So A1's real gap is one half: **nothing leaves this app to a payer without a
human, by construction.**

**The finding neither document makes, because neither had the other:** cloud's 3
says whether a platform needs its own CPT licence to store and redisplay a
customer's UPLOADED code set is unresolved anywhere in published guidance, and our
own 2026-08-20 scope recommends exactly that shape for CDT. The three code sets
are not equally exposed -- ICD-10 is built and public-domain, CPT via the
practice's own developer credential is the safe shape and is unbuilt
(`ALLOWED_SERVICES` is still `{stedi:true}`), and **the CDT upload path must not
be built until counsel answers.**

### 5. The 08-21 trades research re-triaged

`20976294`, `docs/2026-09-26-trades-08-21-triage.md`. Already re-derived on
09-17, so this asks only what moved in nine days. Six commits touched the app or
its libraries and **one does not fit the research's structure at all**:
refrigerant regulation is now three rules and the third is a **US STATE** one --
CARB, 17 CCR 95380, 50 lb and GWP floor 150, against the AIM Act's 15 lb and 53.
Section 4 of that research organises divergence **per country** and section 6
names the need as "EPA 608 (US) / F-Gas (EU)". A sub-national fork whose threshold
agrees with one federal rule and whose floor agrees with neither has no row in
either section. **Section 4 wants re-scoping from "per country" to "per
jurisdiction that can legislate a threshold."**

The generalisable half is the code's asymmetry, not the California fact: because
CARB's floor is *above* the AIM Act's, a contractor stating the refrigerant is not
above 53 settles 150 too, and the converse does not hold. **A three-limb rule set
is not three independent booleans.**

Section 8's dominant-pain row also moved: `MECH_EXPORTS` now holds one dataset,
`mech_credentials`, independently confirmed EXPORTABLE by
`tools/export_coverage_check.py`, beside three buttons still honestly calling
`mechNotLive('CSV export')`. Its reasoning is the reusable part -- it exports the
**records, not the board**, because `latestByKey()` is right for "is this current"
and wrong for a file.

### 6. Vein Match accepts a real slab photo

`e5736a4b` + `0a202343` (generated docs). GAP 4 said Vein Match "works from
photos"; `type="file"` appeared **zero** times between `panel-veinmatch`'s own div
and the next panel's. Step 1 of the two steps the gap triage identified. Step 2,
a calibrated image, is not started and nothing claims one.

Four decisions are the actual work, each held by an arm:

* **media_type is the FILE's type, not a constant.** The other eight image call
  sites hardcode `'image/jpeg'` while accepting `image/*`; a PNG sent as JPEG is a
  well-formed request, so the defect is silent. **NOT fixed at those eight sites**
  -- separate change, flagged not bundled.
* **The cap counts a local `room`, not `_veinPhotos.length`.** FileReader is
  async, so a length check reads 0 for every file in a five-file selection and
  admits all five. The suite's fake FileReader is **deferred on purpose** so a
  revert goes red.
* **The bytes never reach storage.** The row records how many were read.
* **`photos` is photos READ, not attached.** On the catch path the row records 0
  and the output opens in red saying the photos were NOT looked at, because the
  canned fallback is generic and always was.

`sdVeinAnalyze()` now **returns its promise**, and the first suite run proved why:
four arms passed against zero saved rows because storage was read before the chain
ran. 22 arms green, driven in a `vm` against the real module. **Four sabotages on
mutated copies, four caught by the intended arm.** `checkblocks.py` 131/131 both
before and after. Live-verified on the deployed URL via `tools/sairn_http.py`:
`vein-photo-input`, `VEIN_PHOTO_TYPES`, `sdVeinPhotoRemove`, the accept list, the
not-a-measurement line and `Photos Read` all PRESENT.

**AN ORPHAN FOUND AND DELIBERATELY NOT WIRED.** `vmAnalyze()` at ~`:41605` and
`vmPreview()` already do two-photo vein matching. Zero callers; `vm-prev1`,
`vm-prev2`, `vm-loading`, `vm-mat`, `vm-use`, `vm-bundle` do not exist as
elements; only the `display:none` `vm-result` div survives, stranded right after
this panel. Same shape as the Care Guide duplicate deleted at ~`:41583`. **Not
wired:** it regexes a score out of prose and **defaults to 5 when the regex
misses**, which would put a fabricated "Vein Match Score" into the one panel whose
three fabricated KPIs were already zeroed to `'--'`. Deleting another session's
module is Michael's call.

**The suite is NOT registered in `GUARD_TESTS`** -- that list lives in
`tools/sairn_push_gate_hook.py`, which `cc-queue11` holds and is actively fixing.
Registering it would be a write conflict. Run it directly:
`node tests/stonedesk_veinmatch_photos.js`.

### 7. The Tier 2 clearinghouse engagement scoped

`53708880`, `docs/2026-09-26-tier2-clearinghouse-engagement-scoping.md`.
**Probably not an engagement.** Dental A1 is the 270/271 SAIRNcode already runs
live through the practice's own Stedi account -- a port, not a relationship -- and
the incumbent's documented support (read from Stedi's docs here on 2026-08-20)
covers every remaining row. Two boundaries the four-row framing would swallow:
SAIRNsenior A1's transmission half needs an **EVV state aggregator**, which is not
a clearinghouse; and 278 prior auth is a different vendor.

The real work is not the connection. **No X12 claim or remittance code exists
anywhere** -- the two apparent `837`/`835` hits in `sairncode.html` are CPT 90837
and a hex colour. An 837 needs three things a 270/271 does not: a claim builder
(per-app; 837P and 837D are different documents), a **277CA reader**, and an 835
parser. The 277CA is the silent-failure half -- a claim the clearinghouse accepts
and the payer rejects is indistinguishable from a paid one if nothing reads the
acknowledgment. **Sequence: dental A1 port -> 835 -> 837 behind 277CA. Never 837
first.**

**THE BLOCKER, VERIFIED LIVE: `SD_ENCRYPTION_KEY` IS NOT SET.**
`api/_lib/auth.js`'s Stage B split says plainly *"UNTIL SD_ENCRYPTION_KEY IS SET
THIS DEPLOY CHANGES NOTHING"*, and listing the `sairn` project's env var KEYS (no
values decrypted) shows `SD_AUTH_SECRET` present and `SD_ENCRYPTION_KEY` absent
from every target. Today's state is the pre-fix state: one string is both the
session-signing key and the AES key for every secret at rest, unrotatable because
changing it makes every ciphertext undecryptable with nothing erroring at deploy
time. **Adding two more apps' claim-capable credentials under that is going the
wrong way, and one variable fixes it.**

**No vendor comparison was run and no alternative is named**, deliberately -- the
cloud lane that would do it properly exhausted its 200-call search budget, and
naming unverified clearinghouses is the fabrication this platform keeps catching.
Five selection criteria given instead, one of them non-negotiable: a per-practice
credential, because `sc-credentials.js`'s header records the BAA reasoning that
SAIRN never holds a clearinghouse account on a customer's behalf.

### Raised, not acted on -- each needs somebody else's decision

1. **`vmAnalyze()`/`vmPreview()` orphan** -- delete (Care Guide precedent) or
   wire (would ship a fabricated score). Michael.
2. **`tests/stonedesk_veinmatch_photos.js` unregistered in `GUARD_TESTS`** --
   blocked on `cc-queue11` holding that file.
3. **`media_type:'image/jpeg'` hardcoded at eight sites in `stonedesk.html`** --
   silent the moment a PNG is uploaded. Orthogonal to this dispatch.
4. **`SD_ENCRYPTION_KEY` not set** -- one Vercel variable, code already waiting.
5. **`SAIRN_INTERNAL_KEY`'s env var has what looks like its own secret value in
   its plaintext `comment` field** -- returned by the API to anyone who can list
   env vars. Value not reproduced anywhere. Found while checking (4); rotating a
   platform key is not a side effect anybody should take.
6. **`tools/wait_for.py` has no probe** -- the replacement for the fragile loop
   has never been made to fail on purpose.
7. **The CDT upload path must not be built** until counsel answers the CPT
   licensing question.
8. **My own expired-but-unreleased claim `hover-three-fixes`** (118h old at
   session start) still reads open in the record, so another session sees a
   phantom. Not released here because I did not verify its work is done, and
   releasing a claim on unverified work is the same defect in the other
   direction.

---
## 2026-09-26 (Cody) -- cody-q12, five items: four closed, one does not reproduce

Claim `cody-q12`, released on writing this. **A LEXICAL CLAIM BLOCK, DECLARED PER
PR 4.3 rather than reworded.** `sairn_claim.py` blocked on hank over *"same app:
stonedesk"*, and hank's own claim text says **"stonedesk.html is cody-q11's and is
READ ONLY here"** -- their named stonedesk file is `tests/stonedesk_server_backup.js`,
which I do not touch. Also declared in the claim: my item 5 is a **different
class** from hank's queue12 sweep (theirs is unreachable-failure-path /
wrong-field-always-same-answer; mine is a value parsed from model prose with a
silent fallback), so the two cross-reference rather than duplicate.

### 1. The vmAnalyze/vmPreview orphan is deleted

`7d5d3fc8`. Zero callers, no host panel, and `vm-prev1`/`vm-prev2`/`vm-loading`/
`vm-mat`/`vm-use`/`vm-bundle` never existed. Its one surviving host element was a
`display:none` `vm-result` div stranded after `panel-veinmatch`; that went with
it, so neither is left pointing at the other. Care Guide precedent, same
`@REGISTER` form, and it is the **cleanest of the eleven entries: no orphan
storage key at all**, because it persisted nothing -- unlike care-guide-ai's
`sd_cg_history` there was never a second key to collide.

**The tombstone records why it was deleted rather than wired, because "wire it up"
was the cheaper-looking option and was wrong.** It genuinely did two-photo vein
matching, which is what `panel-veinmatch` gained the same day. One line rules it
out: a 1-10 score parsed out of the model's prose, **defaulting to 5 when the
regex missed**, rendered as a 60px filled circle headed "Vein Match Score" with a
verdict beside it. Two details make it the worst version of the class rather than
an average one -- the default sits **inside the vocabulary of real answers** (5 on
1-10 is a believable middling score, not a sentinel), and `||5` sits **inside the
parse as well as outside it**, so `parseInt('0')` being falsy meant a genuine 0
-- the strongest possible do-not-cut-these-together -- also became 5. **Both
failure modes converge on the same number.**

Verified: `checkblocks` 131/131 clean, unchanged from baseline. `div_balance`
4941/4941 PASS, from 4950/4950 -- nine opens and nine closes went, all from the
deleted block. `orphan_register_check` CLEAN with `DELETED_NAMES` 36 -> 38, which
is the tool confirming both names are genuinely no longer defined rather than my
saying so. `dead_dom_readers` 6/6. The 22-arm suite green, and its arm 2e message
moved to past tense so it stops describing code that no longer exists.
**Live-verified on the deployed URL**: `function vmPreview(`,
`async function vmAnalyze(` and `id="vm-result"` all GONE; `vein-photo-input` and
the tombstone PRESENT.

### 2. `defect_register.py --check` DOES NOT REPRODUCE RED, and this is reported rather than worked around

**The dispatch's premise does not hold at HEAD, and I could not make it hold.**
Checked exhaustively rather than glanced at:

* `python tools/defect_register.py --check` -> **exit 0**, *"OK: 315 record(s)
  ... every commit resolves and every field is in vocabulary"*. Run twice, at two
  different HEADs an hour apart (312 records then, 315 now as other sessions
  added three).
* The `1f9936429432` record exists, is complete, and every field is in
  vocabulary: `app: stonedesk`, `layer: product`, `severity: high`,
  `detection_method: code-review`, `injection_phase: requirement`,
  `phase_confidence: stated`, `citation_confidence: clean`, `rules: ["1.11"]`,
  an `injection` block with a 9-day lag, and three contributing factors with
  kinds `process`/`detection`/`detection` and statuses `done`/`done`/`planned`.
* `--verify` -> exit 0. `report_only_checks`' registry entry invokes the same
  `--check`, so there is no stricter variant running elsewhere.
* **AND THE CHECK IS NOT BLIND, which is the part worth keeping.** I re-derived
  every vocabulary from the tool's own constants and audited **all 315 records
  independently** -- `layer`, `severity`, `detection_method`, `injection_phase`,
  `phase_confidence`, `citation_confidence`, `app`, plus every contributing
  factor's `kind` and `action_status`. **Zero out-of-vocabulary values.** That
  matters because `--check` exempts **214 records** from the `app` vocabulary by
  date (`APP_VOCAB_FROM = 2026-09-22`), a deliberate and documented exemption
  whose contents had never been verified. They have been now, once, by a method
  that ignores the exemption. So the green is green because the register is
  clean.

**What I did NOT do: manufacture a fix for a green check.** If the red was real
it was in another clone's working tree or at an earlier commit, and either way it
is not visible or fixable from here.

**AND THE SWEEP FOUND SOMETHING BETTER THAN THE RED WOULD HAVE BEEN.**
`1f993642`'s own `recurrence_open` names a control that does not exist -- *"a
static check over api/*.js asserting every validateLicenseKey caller also reads
.active would have caught this the day it shipped ... NOT built here"* -- and its
third contributing factor carries `action_status: "planned"`.

**Nothing surfaces a planned action. Measured: 62 records carry one**, the oldest
dated 2026-09-14, and `--check` only asserts that the `action` text is non-empty
(line 410). No report, no ageing, no "was this ever done". **That is a bullet
recorded as an intention with nothing reading it back** -- the same shape as an
ACTIVE-WORK bullet being mistaken for a record, 62 times, inside the one document
whose length reads as evidence of thoroughness. **Raised, not built:** a
`--planned` view that ages them is the obvious control and it is somebody's
decision whether the register grows a CAPA follow-up half.

### 3. §4 of the 08-21 trades research gets the axis it was missing

`14bd1ff1`. The research organises regulatory divergence by **country** -- four
blocks -- and that is one axis short, which is why the CARB finding had nowhere
to go. A rule has a **level**, and a sub-national rule can regulate the same
object as a national one on its own threshold with its own comparison operator.

The section did already know US *licensing* is state/municipal. **That is a
different kind of thing and the distinction is the whole point: licensing
attaches to a PERSON, a threshold attaches to a MACHINE, and only the second can
disagree with a federal number about the same machine.**

New §4.1 keys on `(regulated object x level x threshold x comparison x scope
predicate)` and carries all four limbs of the one object where three levels now
exist. Three consequences a per-country structure hides:

1. **The same number is not the same threshold.** Both US rules say 50 lb and the
   **comparisons differ** -- 40 CFR 82.157 reaches an appliance containing 50 lb
   *or more*; 17 CCR 95380 reaches a system containing *more than* 50 lb. **A
   unit at exactly 50.0 lb is IN scope federally and OUT at state level.** One
   shared constant with one shared comparison would have answered one of them
   wrongly and silently. `api/_lib/mech-assets.test.js:439` drives that boundary.
2. **A sub-national rule needs a scope value the national ones do not have** --
   `unknown_jurisdiction`, not `below` and not `not_applicable`. The first gap
   CARB exposed was not the threshold; it was that the registry had no way to say
   *where* an asset was. A per-country table never prompts for that.
3. **Some cross-level implications are sound and their converses are not.** Not
   above GWP 53 settles 150 too; above 53 says nothing about 150, and R-152a at
   about 124 is in AIM scope and out of CARB's.

The **closing paragraph of §4 is amended in place** rather than left, because it
asserts the layering is *"federal and EU-wide forcing function layered on top of
state/provincial LICENSING"* -- which puts the sub-national level on licensing
only. It is compliance at two levels at once. The conclusion that paragraph
reaches survives and is stronger.

**Two limits stated rather than glossed.** CARB was found in **shipped code**, not
in a research pass -- the threshold, floor, operator and citation are as
`api/_lib/mech-assets.js` states them and were not re-read against 17 CCR 95380
here, and that file's own comment lists what it deliberately does not encode.
**And whether other states run comparable programmes is written as UNEXAMINED
rather than answered**: no search was run, so the section asserts neither presence
nor absence. The cheap version of that sentence ("several other states operate
their own HFC programs") would have been a claim with nothing behind it and
indistinguishable from a researched one -- I wrote it, caught it on re-read, and
replaced it.

### 4. The Vein Match suite is NOT going into GUARD_TESTS, and it does not need to

`495c4f8f`, recorded in the suite's own header rather than by editing a registry
it does not belong in.

**It already runs.** `tools/run_all_tests.py` executes after every push and its
own `discover()` returns `tests/stonedesk_veinmatch_photos.js` -- confirmed by
**calling `discover()`**, not by reading its walk, which is the distinction that
matters for a runner whose documented contract is to stay **silent on success**.
A background full-suite run exited 0 with no output, which under that contract is
all-green and is also why it could not confirm discovery on its own.

**It is deliberately not in `GUARD_TESTS`.** That registry's own header states the
admission rule twice: *"EVERY ENTRY IS A RECORDED DEFECT, not a test somebody
liked"*, and it is *"the SEAM class: tests that check two independently-maintained
sides still AGREE ... a test with no real defect behind it does not belong here --
it belongs in the report-only runner."* Every arm of mine lives inside one panel
and its own module, so it fails while its author is looking rather than silently
through a rebase -- the class GUARD_TESTS explicitly excludes. The closest thing
to a seam is arm 6a, and both sides of that agreement are in the same file.
**The header now records what WOULD qualify it**: an assertion that the panel's
outgoing image block and some other owner of the same contract -- `api/claude.js`'s
accepted media types, a separate file with a separate owner -- still agree.
Nothing asserts that today, anywhere.

Confirmed in passing, since it was the stated blocker: **cc-queue11's GUARD_TESTS
duplicate fix landed** -- 10 entries, 10 distinct paths.

### 5. The prose-value-default sweep -- no live instance, and a measured argument against the gate

`495c4f8f`, `docs/2026-09-26-prose-value-default-sweep.md`.

Two passes over 363 files. Mechanical: every extraction, then every ternary/`||`
fallback within three lines that is not in a safe-default set, **with comment
lines excluded** -- because the deleted code is quoted inside its own tombstone,
so a scan that reads comments finds the defect it was written to retire. It did,
on the first run (PR 1.2, inside the scan written to catch it). Then a hand-read
of every hit **plus** every `.match(` on a model-response-named variable,
because pass 1 can only see a fallback that is *written* and a site with no
fallback at all is a different question.

**Ten sites extract from model output and all ten handle a miss correctly, in
five different ways** -- which is the finding, because the convention then
describes existing practice rather than imposing something new. Five return empty
with guarded use (`sairncare`, `sairnsenior`, `sairndental`, `sairnroofing`,
`sairngrounds`); one returns a named third value rendered as itself; two refuse
outright; one renders nothing.

**Two worth copying.** `sairnfreedom.html:4209` asks the **model** for a
confidence flag -- *"Never guess a number when confident is false"* -- and refuses
on four conditions, which turns a parse problem into a protocol: **a parse miss
and a model that knows it is unsure are different events, and only the second can
be asked for.** `sairnlaw.html:6191` states the class's argument in one line:
*"a wrong page count on a rule with a hard page limit is worse than no page
count."*

**One judgment call, and it is not a defect.** `stonedesk.html:42786` defaults
`match_status` to `'Unknown'` and **persists** it. Cleared on three grounds:
`'Unknown'` cannot be mistaken for a verdict the way `5` can; it renders in grey
with the word printed; and `git grep match_status` returns four lines -- schema
comment, write, two render lines -- with **no count and no filter**, so an Unknown
cannot quietly shrink an aggregate. Recorded rather than "fixed" so the next sweep
does not re-open it.

**A GATE IS NOT RECOMMENDED AND THE ARGUMENT IS A NUMBER. 28 candidates, ZERO are
the defect, ONE was worth reading -- 4% precision**, and 23 of 28 are
test-harness fakes (`opts.body ? JSON.parse(opts.body) : null`) which are correct
code and would be noise on every push forever. **The precision cannot be regexed
better**: the real signature requires knowing whether a variable holds model
output, which is data flow, and `txt` in vmAnalyze and `txt` in a dozen string
helpers are the same token. A checker that cannot make that distinction gets
switched off, and a register then claiming the class is monitored is worse than no
checker. The scanner stays in the scratchpad uncommitted for the same reason: a 4%
scanner in `tools/` acquires an inventory entry and a promotion decision it cannot
earn.

### Raised, not acted on

1. **62 register records carry a `planned` contributing-factor action and nothing
   surfaces them** (§2). Oldest 2026-09-14. A `--planned` ageing view is the
   obvious control; whether the register grows a CAPA follow-up half is a
   decision.
2. **`media_type:'image/jpeg'` hardcoded at eight sites in `stonedesk.html`** --
   still open from cody-q11, still orthogonal. Note that `sairnroofing.html:5320`
   already does it right with `pendingPhotoMediaType`, so the fix has a
   same-platform model.
3. **The `defect_register --check` red could not be reproduced** (§2). If it was
   real, it was in another clone's working tree.
4. **Nobody has measured how often each of the ten extraction sites' prompt
   format is actually absent.** Every site is judged on what it does when the
   format is missing, not on how often it is -- and that measurement needs real
   responses, not a scan.
5. **Carried forward unchanged from cody-q11:** `SD_ENCRYPTION_KEY` still unset;
   the `SAIRN_INTERNAL_KEY` comment-field value; `tools/wait_for.py` still has no
   probe; the CDT upload path still must not be built; and my expired
   `hover-three-fixes` claim still reads open in the record.

---
## 2026-09-26 (Cody) -- cody-q13, seven items, all seven closed

Claim `cody-q13`, released on writing this. Every commit pushed; each generated
document re-checked at the new HEAD after every rebase, and **two rebase
conflicts on generated docs were resolved by re-running the generators rather
than merging text, per PR 2.5** -- the section written earlier in the day, used
twice on the same day.

Nothing in `sairnbiz.html`, `sairnsenior.html` or `sairnvet.html` was touched:
`cc-queue12` holds all three, and three of the seven items are about findings in
them.

### 1. Nine waiters in stonedesk.html stop giving up in silence

`76a80486`. Eight blocks poll for `window.addMsg` every 150-200ms and stop after
ten seconds; every one called `clearInterval` and **nothing else**. Eight
chat-enhancement hooks declined to install on every page load and said so
nowhere -- which is why the dormancy had to be found by opening a browser console
on the deployed page.

`sdHookDormant(hook, global)` prints the shared **cause once** and **one line per
hook**: eight identical explanations would be noise, eight names are eight facts.
On `window` because each waiter lives in its own IIFE in its own script block, and
every caller guards on `typeof` so if the first block throws the other eight
degrade to the silence they had rather than to a TypeError.

**THE REPORT IS CONDITIONAL, and that is the part that could have been wrong.**
Each give-up timer fires whether or not its interval already succeeded, so an
unconditional call would announce a dormancy for a hook that installed at t=3s --
the same class of false statement as the silence, in the other direction.

**The message carries the white-on-white constraint with BOTH colours**, because
"hook did not install" without it invites somebody to just install it:
`renderMarkdownRich` hardcodes `#F0F0FF` headings and `rgba(240,240,255,0.8)` list
text for a dark surface while the live `.msg-bubble` is `#FFFFFF`. Arm 4b asserts
both are present -- either alone is not actionable.

**AND A COMMENT IN THAT FILE WAS WRONG, corrected rather than left.** `:21148`
said *"THESE CHIPS ARE NOT DEAD ... installHook() wraps the LIVE addMsg()"*. There
is no `addMsg` in the file: every one of the eight `window.addMsg =` lines sits
inside an `install*Hook()` that returns early unless it is already a function, and
a real `function addMsg(role, content)` survives only in
`archive/branch-lucid-ptolemy-b73vu0/` -- the retired chat that comment's own
first paragraph says was replaced. Two comments in one file disagreed and the
browser-verified one was right. **The 2026-09-08 retarget it justifies is not
reverted**, and the reasoning is written down: it removed a real TypeError from a
path that is currently unreachable, which is the right state for it to be in.

13 arms, four sabotages each caught by the intended arm. **And arm 1a went RED
against a correct file on its first run** -- `/function\s+addMsg\s*\(/` matched
`sdHookDormant`'s own warning text, which contains *"a real `function
addMsg(...)`"* inside a **string literal**, so the comment filter could not remove
it. My disclosure tripped my premise check. The anchor now requires an identifier
parameter list and an opening brace. **Second time in two sessions that my own
prose tripped my own scanner.**

Live-verified: 9 disclosure call sites on the deployed page.

### 2. `defect_register.py --planned` -- the 62 actions the file recorded and never read back

`0456f0cb`. `action_status` has had a `planned` value since the field existed and
`--check` asserted only that such a factor carries non-empty text. 62 planned
actions across 58 records, oldest 12 days.

**TWO COUNTS, NOT ONE, and they differ** -- a record can carry more than one
planned factor. Arm A1 uses a fixture where they differ so a build reporting one
figure twice cannot pass.

**The one mechanical signal it can honestly give:** is the record's fix-commit sha
named in `docs/SAIRN-OPEN-WORK-INDEX.md`? The index carries ~380 sha tokens, so
the comparison is real. **53 of 62 are REGISTER-ONLY** -- reachable from one file,
and that file is not the one anybody opens to pick work.

**It does not fail and does not age into a finding.** A planned action can be
correctly deferred for months, and a checker crying wolf on all 62 from its first
run would be switched off within a day -- after which the register would carry a
control that claims to watch this and does not.

**AND THE COUNT RIDES ON `--check`, which is the command that actually runs.**
`report_only_checks` invokes `--check` on every push; the full report is invoked by
nothing. One line goes out with every push, and if it ever cannot be computed it
says COULD NOT COUNT and says *"that is not zero"*.

`planned_facts()` takes `now` and `idx` injectably so the probe drives synthetic
fixtures; pointing a control at the live register would make every arm depend on
today's record set. 12 arms, `DR_MODULE_DIR` override for negative controls, four
sabotages caught -- including the two that matter: dropping a record with an
unusable date (makes the backlog smaller than it is) and an empty index reading as
TRACKED (fail-open).

### 3. The eight enterprise RCM panels, MEASURED

`5d5f32d8`, `tools/panel_depth.py` + `docs/2026-09-26-sairncode-rcm-panel-depth.md`.
The debt two documents recorded and neither paid -- the 09-23 internal audit
(*"a direct depth check on those eight panels is owed before pitching a large
hospital system"*) and the 09-26 cloud audit, which deferred it again.

**claims 9/9. prebill, hcc, drg, rac, denial, ar, revenue each 6/9, each missing
the SAME three deep signals** -- `server_named`, `domain_verb`, `verb_sent`.

**The sharpest part is what comment-stripping found.** `api/sd-data.js` mentions
`sc_denial`, `sc_ar` and `sc_revenue` repeatedly and **every one of those mentions
is a comment.** Code-line count: `sc_claims` 4, the other seven **0**. All seven
ride the generic `SC_RESOURCES` handler -- no per-resource rule, by construction.
Cross-checked across the whole `sc_` family: `therapy_accumulator` on `sc_claims`
is the **only** domain verb SAIRNcode has.

**TWO NUMBERS, never added** (PRESENT and COULD-NOT-TELL), and **no threshold** --
one would manufacture a pass/fail out of a design question, and several of the
seven may correctly have no domain verb because there is no second fact to compute.

**The fixture lock earned itself before any data was touched.** Version `.1`'s
`sig_panel` searched the raw file and the lock's *"a panel named ONLY in a
comment"* fixture refused the criteria -- exit 2, NOTHING REAL WAS JUDGED. Then
the **first real run** exposed a second error the lock had not predicted:
`domain_verb` credited `sc_prebill` with five verbs (`sc_drg`, `sc_eligibility`,
`sc_fraud`, `sc_hcc`, `sc_pctc`) because `SC_TIER_A_SOFT_DELETE_ONLY` puts several
resource names on one line. Sibling names now excluded by prefix, two fixtures
added, `CRITERIA_VERSION` `.1` -> `.2`. **Declared: one fixture corrected because
its expectation was wrong, two added; none changed to match tool output.**

### 4. The site-asset register exports, three rules kept apart

`94fbf115`. The 08-21 research rates data portability the **dominant** real-world
pain in this category, and the app could produce exactly one register as a file --
not the one carrying the contractor's EPA and CARB position.

**AND MY OWN 08-21 TRIAGE WAS WRONG ABOUT WHERE TO BUILD IT, corrected here.** It
said the three remaining `mechNotLive('CSV export')` buttons were the candidates.
They are not: all three sit inside the SAIRN Suite and SAIRNbiz Connector panels,
whose own headers read *"Links only -- no data sync"*. They are cross-app sync
exports on connectors that do not sync. Wiring them would have answered a
different question and implied the connector works.

**Three rules, six columns, never merged**, each rule's REASON beside its scope
because the reason is the citation an inspector wants. Preamble carries all three
citations, forbids summing, and states the boundary: 82.157 is 50 lb **or more**,
17 CCR 95380 is **more than** 50, so a unit at **exactly 50.0 lb** is in scope
federally and out at state level.

**No supersession here, checked rather than copied.** `evaluateRegistry` does not
reduce -- `rows` is a 1:1 map over every asset -- so reusing the credentials
export's "on the board?" framing would have implied a problem this register does
not have.

**A charge of 0 is a measurement.** `r.refrigerant_charge_lb || ''` is the obvious
accessor and it is wrong: 0 is falsy and blank means NEVER WEIGHED. Driven both
ways.

**And adding a second export made the FIRST one's messages lie**, fixed in the
same change: the not-loaded toast said *"the credential register"* and the success
toast claimed *"including records the board supersedes"*, both hardcoded when
credentials was the only dataset and both false of this one. Arms D1-D3 hold
**both** so fixing one cannot break the other.

20 arms, board built by the **real** `evaluateRegistry` rather than hand-written --
the credential suite's own header records what happens otherwise. Five sabotages,
five caught. Live-verified on the deployment.

**Tier A obligation recorded and assigned to cloud**, and **the record's text was
repaired immediately after recording, with the repair declared in the record**: the
sentence naming the charge accessor was written inside shell backticks, so bash
substituted it away and the obligation landed with a gap exactly where the line to
look at belonged.

### 5. Wave 3 -- CLOSED, with one criterion's wording corrected

`c56f98e5`, `docs/2026-09-26-wave3-audit-closeout.md`.

**StoneDesk is not "8/8 closed"; it is 8 of 8 gaps with no UN-GATED work left.**
GAP 4 step 1 (real image acceptance) landed today; step 2 needs a scanner
interface -- Slabsmith, SideShot, Iride or Mapascan -- and `slabsmith` is still 0
in the file. "8/8 closed" invites *"so Vein Match reads scanner files?"* and the
answer is no. The audit row now carries both halves.

**SAIRNbiz's 1099 fix verified and it is the right shape:** `sb1099Threshold` is
keyed to the **payment date**, which matters because OBBBA CPI-indexes the figure
from 2027 and a constant would have gone stale inside fifteen months.

**SAIRNvet is the least ambiguous of the three:** `7bc26782` corrected a
butorphanol HORSE dose that was 2-4x the FDA-approved equine figure, `f3484b3c`
removed 284 green "Verified" ticks nothing had ever verified, and `980a9d2c` warns
on 315 species-copied doses **derived from the table** rather than hand-listed --
which is the half still true next month.

**AND THERE IS NO "full-platform-audit Wave 1/2/3" ANYWHERE IN THIS REPO.** The
only Wave 3 on disk is the click-through re-verification, a **different** wave
that closed 2026-09-23 over the same three apps -- which is exactly how the two
get confused. The criteria came with the dispatch, so they are written into the
closeout where they can be checked.

### 6. SAIRNbiz -- the four findings beyond the 1099 bug, prioritised

`c56f98e5`, `docs/2026-09-26-sairnbiz-internal-findings-triage.md`. F1 already
cc's and already fixed.

**F4 first, not F2.** The Benefits panel's six invented strings are all still
present; two of them **look computed** (*"Avg 5.2%"*, *"Plan Assets (est.)
$284,000"*), which is the hardest kind of fabrication; and one -- *"Workers Comp --
Active, BWC Ohio"* -- asserts **the Ohio Bureau of Workers' Compensation** to
every customer in every state. The fix is deletion or disclosure and this app has
done it twice.

**AND A ONE-LINE UNBLOCK FOUND UNDER F2.** Cloud says the phantom-wage blocker is
gone because timesheets are store-backed. **Cloud is right and the app's own screen
still says the opposite:** `:1036` justifies leaving the configurable overtime
threshold unwired on the grounds that *"its hours are demo figures, not a real
store"* -- true until 2026-09-15, false since. Hours come from `sb_ts` keyed by
employee id, `saveTimesheet()` is a real writer with a re-checked active-employee
guard, and an employee with no record renders `--` and is excluded rather than
defaulted to a full week. **A stale sentence is holding a feature back with a
reason that stopped being true.** F2 is then two different sizes of work and is
being treated as one.

F3 third (undisclosed omission in a computed figure, low exposure, and it runs
*opposite* to the wage-base overstatement the app **does** disclose). F5 fourth --
one string, in a prompt, in `stonedesk.html` rather than `sairnbiz.html`, and the
remedy is Michael's sentence to write.

### 7. SAIRNsenior -- triaged, and the best build is not in cloud's gap list

`c56f98e5`, `docs/2026-09-26-sairnsenior-cloud-audit-triage.md`.

**PRIORITY 1, new in this triage: a caregiver with an EXPIRED CPR can be assigned
to a client, and the app already knows.** `cpr_expiry` is stored and editable,
`certDaysUntil()` drives two KPIs and renders a **red "Expired"** badge, and the
assignment path at `:2342`/`:2355` reads neither. Two screens, two answers, no
disagreement flagged. Cloud listed this in §7.3 as a candidate it *recorded but did
not investigate*. It is the smallest real build in the audit, and
SAIRNmechanical's `evaluateEligibility` + its 2026-09-17 caller fix is the
precedent -- **including that comment's warning to SURFACE the answer rather than
silently refuse**, which is right here too: a hard refusal would block an agency
covering a shift in an emergency. Limit named: `cpr_expiry` is ONE certification
and `sen_training_records` exists separately, so gate on what is recorded and say
what is not gated.

**PRIORITY 2: cloud's newest gap is HALF BUILT.** §7.1 item 2 says visit
maintenance with reason codes *"does not exist"*; cloud's own §8 flags that as a
grep floor. Read: the **detection** exists -- three named exception types at
`:5482`, an EVV Exceptions KPI, and a table naming client, caregiver, date and
issue. The **resolution** does not; `reason code` is 0. That is cc's item, and the
verification cc was told to do is this: **build onto the existing detector, do not
build a detector.**

**THE BLOCKER CORRECTION, which changes who has to act.** SAIRNsenior's recorded
blocker is *"a trading-partner agreement per aggregator"*. Cloud establishes the
real gate is **a pilot agency per state that names SAIRNsenior** -- Colorado,
Connecticut and Indiana all require the provider to sponsor the vendor first, and
**no signed TPA exists at that layer at all**. The TPA is real but lives at the
837/EDI layer, which is why every competitor names a clearinghouse. **So the first
state is chosen by where the first Medicaid customer is, not by which spec is
cleanest** -- the 08-27 ranking of NY/LA/TX holds for learning and not for
sequencing. Also carries the three market credential-custody models, and notes
that the safest one and the clearinghouse question are gated on the **same unset
`SD_ENCRYPTION_KEY`**.

**Priority 3 carries a metric distinction cloud's ordering hides:** EVV Completion
(30d) already exists; an **edit rate** does not and cannot, because nothing records
an edit. Different numerators, different denominators, and a state threshold
written for one is not a threshold for the other.

### Raised, not acted on

1. **`SD_ENCRYPTION_KEY` still unset** -- now gating two separate decisions (the
   clearinghouse key and SAIRNsenior's per-agency aggregator credentials).
2. **`SAIRN_INTERNAL_KEY`'s env var still has its value in its plaintext
   `comment` field.**
3. **62 planned register actions, 53 register-only** -- now surfaced on every
   push, but surfacing is not doing.
4. **`media_type:'image/jpeg'` hardcoded at eight sites in `stonedesk.html`** --
   and `sairnroofing.html:5320` already does it right with
   `pendingPhotoMediaType`, so the fix has a same-platform model.
5. **The slow-response indicator in `stonedesk.html` can never fire** -- its
   `checkDone` interval clears `_activeTimeout` at 500ms while the indicator is
   set to appear at 8000ms, and the interval only checks that the container
   EXISTS, not that a response arrived. Found while reading the waiters; **not in
   scope and not fixed.**
6. **`tools/wait_for.py` still has no probe.**
7. **The CDT upload path still must not be built** until counsel answers the CPT
   licensing question.
8. **My expired `hover-three-fixes` claim still reads open** in the record.

---

# Queue 13 — 2026-10-05

Full account: `docs/2026-10-05-cody-queue13-report.md` (and its addendum, which
corrects three of its own sections written earlier the same session).
Gate 1: `docs/2026-10-05-gate1-live-migration-signed-in.md`.
## Landed

| sha | what |
|---|---|
| `2f52470b` | **The claim matcher's disclosure rule.** `disclosed_files()` returns `inside - outside` — a path is disclosed only when no clause outside a blocker clause names it — and markers match on a FRONT word boundary, which stopped `blocked` matching inside **UNBLOCKED**. Seven new markers, each measured alone. **BLOCK→CLEAR 0, CLEAR→BLOCK 54, over all 532,512 cross-session pairs.** Four candidates measured and REJECTED (`deferred` 73, `holds` 61, `is <session>'s` 50, `conflict declared` 22), so two of the finding's eight wordings are still open and arm E6 asserts it |
| `d3d2db42` | **Push-gate check 11 read the working tree while the push shipped a commit.** `--rev` on `control_char_check.py`; a named file that cannot be read is exit 2 and is NAMED; `git ls-files -z`, because quoting had hidden a tracked file for 25 days; and check 11 now denies on exit 2, which was falling through as a pass |
| `77b5b536`, `1eb6da5c`, `e1192ce5` | **Item 2 CLOSED: fixture locks for all 7 never-claimed registry tools.** Platform figure moved **26 DEAD → 8**, **56 findings → 36**, **COULD NOT RUN 24 → 22**. The 8 that remain are two CLAIMED tools and are outside the item's scope |
| `36d58d34` | **`schema_provisioning_check.py --pin/--auth`** — Gate 1 went from **37% to 77% answerable** |
| `27287408` | The two measurement documents |
## The thing worth keeping from all of it

**IN FIVE SEPARATE PLACES TODAY THE RULE WAS NOT WEAK — IT WAS REACHED BY A
SECOND ROUTE THAT MADE THE EXISTING EVIDENCE PASS WITHOUT IT.**

* `READ_RE`/`AGG_RE` — one fixture matched both, so neutralising either left the other.
* `DISPLAYISH` — the arm's input matched no other rule either, so it fell through to the same default verdict.
* `TIER_A_ROW` — the isolation that makes every other arm trustworthy bypasses the rule that builds the set.
* `WRITE_VAR_RE` — no consumer at all; the pattern was re-spelled inline.
* `WRAPPER_RE` — its only consumer was a field computed on every run and printed nowhere.

**And the same shape one layer up, in the gate:** check 11's file list came from
the push and its bytes came from the disk, so the proxy and the subject were one
`git show` apart. **And again in Gate 1:** the session gate answered 403, the
sweep recorded REFUSED honestly, and REFUSED is indistinguishable in a summary
from a table nobody asked about — 22 missing tables sat behind that.
## My own mistakes, recorded

1. **A register field was EATEN BY THE SHELL** — the word for the gate's file
   list was written inside bash backticks in a double-quoted `printf`, so the
   sentence landed with a gap exactly where its subject belonged. Scrubber item
   18, while writing about silent failure. Repaired, and the incident is written
   into the field.
2. **Two of my own fixture arms were green on a dead rule**, caught by the
   ablation rather than by reading. A shape-A fixture does not touch
   `WRITE_VAR_RE`; a generic read that resolves does not touch `READ_VAR_RE`.
3. **A driver truncated its own evidence to 500 characters**, so `missing` for
   SAIRNscape was cut off mid-list and I was one step from reporting "1 missing
   table" off a shortened read.
4. **An idempotency check counted comments as statements**, flagging 5 of 18
   safe-to-re-run SQL files as needing hand edits.
5. **A word-boundary on both ends** broke `not touch` matching NOT TOUCHING —
   one of the eight wordings went from covered to blocked, caught by driving all
   eight before committing.
## Raised, not acted on

1. **cc holds `docs/SAIRN-OPEN-WORK-INDEX.md`**, so three findings have no row:
   SAIRNscape `customers` (PII on a licence key alone, READ and WRITE), the 24
   missing tables, and the two apps whose gated resources are unanswerable.
   Written into the registry note for cc.
2. **hank holds the `supplier_lead_times` citation-drift row (73)** and is
   working it. Not touched.
3. **`tests/claims/run_fileset_matcher_probe.py` is RED at HEAD**, 3 failures,
   pre-existing and proven by stashing. My change moves its PINNED figure
   **26 → 0**. NOT re-pinned — that needs a decision about whether the file-set
   matcher still earns its place.
4. **`tools/gap_ledger.py` NOT BUILT.** Inputs ready; one scope call outstanding
   (both pilot apps' newest audit is on PR #18, not on main).
5. **Checks 2, 3, 4, 5, 6, 7, 12 and 12b** build the same working-tree paths
   from the same outgoing range as check 11 did. Not swept.
6. **11 Tier A obligations authored by cody are open**, oldest 2026-09-27.
7. **Item 9 of the previous paste is named by neither the landed list nor the
   refused list.** Not inferred.

---

# Queue 14 — 2026-10-05

`docs/2026-10-05-cody-queue14-inventory.md`,
`docs/2026-10-05-sairnscape-customers-licence-key-alone.md`,
`docs/2026-10-05-gate1-missing-table-triage.md`,
`docs/2026-10-05-cody-mistake-review.md`.
## Landed

| sha | what |
|---|---|
| `cdc92f79` | `tools/gap_ledger.py` + its probe, registered, three generated docs re-derived. 65 rows, 22 apps; pilots SAIRNlaw 5 and SAIRNcode 6 |
| `6b85b23a` | the SAIRNscape finding proven live with a control; Gate-1 triage — 0 of 24 removable, the list is 26 |
| `38514b5b` | `declared_tables()` required `public.` — 28 tables invisible, a file declaring none exited 0 |
| `886f01ac` | the mistake review and this inventory |
## The priority item

**PROVEN:** `read customers` on a bare `SCP-DEMO-2026` → 200 with name, email,
phone and address; `write` with an id-less payload → 400 from the handler body,
nothing stored; **CONTROL** `invoices` and `scp_quotes` on the same bare key →
403 both. **NOT PROVEN: the fix**, because `api/sd-data.js` and
`docs/CRITICALITY-TIERS.md` are cc's and the first was on the stay-off list.

**Root cause is in the register, not the gate.** `customers` is B/B while its
confidentiality cell already says the row carries PII. **The basis was corrected
and the letter was not, and the letter is what the gating sweep reads.**
## What I got wrong, and it is the day's pattern

**Five logged, reviewed, and the review found two more — seven, three live.**
Five of the seven are a reader, counter or matcher applied to a corpus wider
than the sample it was written against, and **every one failed quietly**: a
smaller number, a shorter list, a green arm.

**I verified each tool against its own fixtures and did not verify the fixtures
against the corpus.** The one mechanical change that follows is that **a sweep
must print its own coverage** — three of the five would have been one line each.

The sharpest: the Gate-1 document published counts that were floors, and its
limits section is accurate because **an unstated assumption does not appear in a
limits section.**
## Raised, not acted on

1. **Three of seven items blocked by cc's one claim** — the gate, the retier,
   two index rows, two register notes. All routed in pasteable form.
2. **EIGHT Tier A obligations are waiting on ME**, oldest six days. I am the
   blocker on more review than I am waiting on, and nothing today discharged
   one.
3. **Six of the eight remaining dead rules are mine** —
   `metamorphic_check.py`. The previous batch's scope was never-claimed tools
   and is honestly complete; these are a different item and they are mine.
4. **`gap_ledger.py` is outside the sweep's universe** (162 of 169 rules)
   because registering it needs `report_only_checks.py`, which hank holds.
5. **20 SQL files and a snapshot re-capture owed by Michael**, plus two apps
   whose gated resources are unanswerable until a credential decision.
6. **A blocked push can leave a rebase IN PROGRESS.** `--amend` then rewrites
   the commit being replayed onto. The repo's own guard caught it. **A blocked
   push is not a no-op** and `git status` is the first thing to read after one.
7. **GitHub reports 1 HIGH dependabot vulnerability on the default branch**
   (`security/dependabot/4`), surfaced by a push today. Not mine, not looked at.

---

# Queue 15 — 2026-10-05 (Cody) — the batch closes in one number, and the reset's summary was green where the tools are not

**Resumed after a context reset. Every item below was re-derived against the
repo; nothing was carried across from the pre-reset summary.** Full write-up:
`docs/2026-10-05-cody-queue15-inventory.md`.
## Landed

1. **The registry commit was committed and NOT pushed.** `main` opened **ahead
   1, behind 4**. Rebased onto `origin/main` (no conflict — hank's four touched
   different files) and pushed as `31a1d4fc`. **The unpushed commit was the
   registry one**, which the whole measurement below depends on.
2. **Queue 14's under-counted universe is CLOSED. 162 → 169 rules.** `read 75
   tool(s) from the report-only registry; 169 module-level compiled rule(s)`.
3. **Every moved number in the sweep is attributable to a named change in this
   batch, and nothing else moved.** +7 rules are gap_ledger's seven and all
   seven; `gate1_verify.py` contributes **zero** (it compiles no module-level
   rules); +13 exercised is those 7 plus the 6 metamorphic rules fixed; DEAD
   **8 → 2**, and the 2 remaining are `register_feed_gate.py`'s, **fourth's
   tool**, held by hank. The arithmetic closes: 80+2=82, 82+65=147, 147+22=169.
4. **Nine tools re-run at HEAD, each measured alone.** Seven exit 0. Two do not,
   and they are reported as not-green rather than as done.
5. **Both anchoring fixes proven by the FILE COUNT, not the exit code** — 22
   files swept and 22 probed from a non-root cwd. **Both sweeps exited 0 before
   the fix too, over an empty corpus**, so the exit code was never the evidence.
## Raised, not acted on

1. **`metamorphic_check.py` exits 1 with its one pre-existing rewording
   finding** (`fmea/alf_facility_role_gate_live_probe.py`, relation `case`).
   Six fixed rules are green; **the tool is not.** It appears **0 times** in
   `docs/SAIRN-OPEN-WORK-INDEX.md` — my tool, my gap. **Not logged, and I did
   not edit the index: cc holds it under a live claim this hour.** NEXT ACTION:
   one row, by whoever next holds the index.
2. **The universe is 169 of 169; the sweep's COVERAGE is 147 of 169.** Two
   different numbers. 22 rules are uncleared because their tools WRITE when run,
   the sweep exits **2** and calls its findings a FLOOR. **Reporting the first
   figure as the second would have published a 22-rule hole as a pass.**
3. **Registering two tools did not fix the mechanism that excluded them.** The
   universe is still derived from a hand-maintained list — **75 REGISTRY entries
   against 293 `.py` files in `tools/`**. 293 is the wrong denominator and I do
   not have the right one; **neither does the sweep, and that is the gap.**
4. **20 SQL files and a snapshot re-capture are still owed by Michael.** Ready,
   idempotent, no decision needed. **I did not re-drive the live `PRESENT 0 /
   MISSING 26` baseline** — `--fixtures` green proves the verdict logic, not the
   live state.
5. **A backgrounded `tool > out; echo $?` reports the ECHO's status.** The
   harness said *"exit code 0"* for both long runs; the real codes were **1**
   and **2**, read out of the captured stdout. **Two not-green tools would have
   gone into a standing document as green.** The attribution hook fired on
   nearly every command this session and was right every time.

---

# Queue 16 — 2026-10-06 (Cody) — two hidden universes, three defects of my own, and one item whose premise was false

Full write-up: `docs/2026-10-06-cody-queue16-inventory.md`.
## Landed

1. **The sweep's universe was 169 of 521 rules, not 162 of 169.** Replaced the
   hand-maintained `report_only_checks.REGISTRY` population with `git ls-files
   tools/*.py` + a per-file classification. **295 tracked tools, 150 with rules,
   521 rules — 105 files and 352 rules were outside the universe entirely.**
   Yesterday I closed this hole *two names at a time* and pushed the fix; that
   closed two names and left the mechanism.
2. **The declared exemption list is EMPTY, and the only entry I wrote was
   refused by the check I wrote with it** — `dead_rule_sweep.py` compiles no
   module-level rule, so the mechanical branch already excluded it. All 295
   files are classified by a rule, not a judgement.
3. **The 22 write-when-run rules are measured: COULD NOT RUN 22 → 0.** The
   sandbox already gave isolation; the real blocker was ATTRIBUTION, so the
   corpus is now RESET between runs and reproducibility is proved per tool
   before any ablation counts. **17 exercised, 5 DEAD — the blanket refusal had
   been hiding five real findings.**
4. **The dependabot HIGH is decided on a measurement, not a guess.**
   `firebase-admin@12.7.0` reaches node-forge in exactly ONE place,
   `forge.pki.privateKeyFromPem` — a PARSER. The advisory is about signature
   VERIFICATION. **Not on our path**, four-point re-check trigger written.
5. **`tools/capture_exit.py` built, locked and registered** — the real status to
   a named file, `RUNNING`/`EXIT`/`COULD_NOT_RUN`, and `--read` exits 2 and
   never 0 on a status it cannot read.
6. **Three of my own documents reported this sweep with NO exit code.** Nothing
   claimed either tool green; the quiet version is worse. All three corrected,
   and **the exit code of a past run was not invented** — each says it is
   unrecoverable and records a re-run.
## Three defects of mine, all found by USE

1. **The writer-tier digest included its own mutation** and reported 22 of 22
   exercised. Caught by the negative arm written with it.
2. **`capture_exit.py --read` raised on its FIRST real use.** Every arm passed
   because every arm called `read_status()` and none went through the CLI. *A
   strong lock over one half of a tool says nothing about the other half* — my
   own sentence from the day before. The traceback's exit 1 happened to equal
   the sweep's real 1, so the number was right by accident.
3. **A concurrent sweep deleted the live one's sandbox**, killing a 151-tool run
   29 tools in with a traceback naming an innocent file. The reap is now
   owner-aware and fails closed. **My first version of the arm proving it was
   wrong, and the fix went into the FIXTURE, not the tool** — passing it by
   changing production code would have removed the guard.
## Raised, not acted on

1. **5 newly-found DEAD rules in three tools I do not own** —
   `criticality_tier_check.py`, `defect_register.py`, `hover_separation_audit.py`.
2. **Item 6's premise was FALSE.** hank's `register_feed_gate` cp1252 fix IS in
   `origin/main` (`cd19bd7f`) and **DEAD is still 2, not 0**. Unrelated defects
   sharing a file: an encoding fix cannot move an evidence verdict. Fourth's
   tool.
3. **`tools/push_retry.py --loop` refused my push with a FALSE ATTRIBUTION** —
   "a rebase this tool just performed SHRANK docs/known-red-suites.json 17 → 13".
   My tree was byte-identical to `origin/main` on that file and my commit did not
   touch it; the records were removed by hank's `34c834aa`. Right that records
   vanished, wrong about who did it. Hank's tool, routed.
4. **Two items could only be routed, PR §4.3 declared both times.** cc holds
   `docs/SAIRN-OPEN-WORK-INDEX.md` and `tools/exit_status_attributable.py`; the
   metamorphic row and the false-negative finding are paste-ready in
   `docs/2026-10-05-cody-routed-to-cc.md`. **cc is now working on
   `fmea/alf_facility_role_gate_live_probe.py` directly** — that finding's exact
   subject — so the routing reached the right place.
5. **The methodology lesson is ROUTED, not promoted.** `docs/METHODOLOGY.md` is
   fourth's and `docs/2026-09-13-cross-domain-disciplines.md` is under a
   subject-level block, so a cross-cutting rule is sitting in a dated file,
   which is the eighth convention waiting to happen.
6. **Michael's 20 SQL files are still unrun** and I did not re-drive the
   `PRESENT 0 / MISSING 26` baseline this batch either.

---

# Queue 17 — 2026-10-06 (Cody) — the upgrade beat my own finding, 49 dead rules are none of mine, and 21 refusals were my own bound

Full write-up: `docs/2026-10-06-cody-queue17-inventory.md`.
Routing: `docs/2026-10-06-cody-routed.md`. Handoff: `docs/handoff-cody-2026-10-06.md`.
## Landed

1. **firebase-admin 14.5.0 driven in a scratch copy OUTSIDE the repo, and it is
   green.** 14.5.0 **drops node-forge entirely** — absent from the tree, nothing
   declares it, zero `forge.*` call sites. **0 of 248 suites changed verdict**
   against a 12.7.0 baseline copy. **My own one-call-site finding is superseded**
   and that is said plainly: "the package is not in the tree" needs no trigger.
   **NOT applied** — measuring an upgrade and landing one on a live payment path
   are different actions.
2. **The dead-rule universe at HEAD: 297 tracked tools, 152 in the universe,
   540 rules**, 371 outside the registry. Full ablation at `8f204050`: **517 of
   540 checked, 49 DEAD to own evidence, 101 dead on the real run, 150 findings,
   COULD NOT RUN 36 → 23.**
3. **21 of those 23 were MY OWN 45-SECOND BOUND, not an absence of evidence.**
   `cross_tenant_isolation_scope.py` needs 131s. Re-asked at
   `--corpus-timeout 200`: **21 of 21 answerable, and FOUR ARE DEAD** — the
   bound had been hiding four real findings in cc's tool. The bound is now
   overridable and **printed on every run**, and a timeout has its own verdict.
4. **The old population's verdict changed from 2 to 1.** `--registry-only`
   reproduces the exact pre-2026-10-05 population and now reports **169 of 169
   checked, 0 could-not-run, 33 findings** — the writer tier measures the 22 that
   made it exit 2.
5. **Two concurrent sweeps finish**, distinct sandboxes, zero leftovers.
6. **A Tier A obligation discharged adversarially and it found FOUR defects** in
   hank's `citation_line_drift_check.py` — `_direct_line()` is a substring test
   over raw lines, so a `//` comment reads as access. **The live `sd_comms` rows
   are RIGHT and would survive the write being deleted**, because a comment
   naming it sits five lines below inside the same window.
## Three defects of mine, all in code written the same day

1. **The escape check accused an innocent tool** (`primitive_obsession_check.py`)
   and voided a 23-minute run. Cause: my own `git commit`. Fixed with a HEAD
   discriminator; it then voided a second run blaming nothing, because my own
   `traceability_matrix.py` dirtied the tree. **Fixed properly:** did the clone
   change **in a file the tool wrote inside the sandbox** — which `_writer_sig`
   already returned and I was not using.
2. **The 45s bound misreported 21 rules' cause** and hid four findings.
3. **Seven undecoded `subprocess` sites**, six written that morning, found by a
   tool I was driving as a SUBJECT rather than reading as a checker. The one that
   mattered — `tasklist` in `_pid_alive` — **failed CLOSED**, so the sandbox
   guard held by construction.

**And two of my own ARMS were wrong.** `F9b` asserted a contract I had
deliberately changed; the Tier A control's paired positive S3 failed first — had
it been omitted, three sabotage arms would have "passed" against a tool
returning nothing. **Both fixes went to the ARM, not the tool.**
## Raised, not acted on

1. **53 dead rules routed, 0 diagnosed, 0 mine** — cc 13 across 6 tools, hank 10
   across 4, and **30 across 16 tools with NO OWNER RECORDED ANYWHERE**.
2. **Only 13 of 297 tracked `tools/*.py` carry an `# OWNER:` line**, so every
   routing decision this batch was reconstructed from 2381 claim commits. That
   derivation attributes to the last CLAIMER, not the author.
3. **26 Tier A obligations remain reviewable by me** (35 open of 235, re-measured
   at the end — it was 40/28 at the start; cc discharged nine).
4. **`push_retry.py:717` names the wrong actor** for a vanished ledger record
   (fourth's) and **`exit_status_attributable.py` cannot see the backgrounding
   layer** (cc's). Both proposed, neither patched.
5. **Six cross-cutting methodology rules are sitting in dated files.**
   `docs/METHODOLOGY.md` does not exist at HEAD and is fourth's;
   `2026-09-13-cross-domain-disciplines.md` still holds 12 headings. **The eighth
   convention with a queue of its own.**
6. **Michael's 20 SQL files are still unrun** and I did not re-drive the
   `PRESENT 0 / MISSING 26` baseline this batch either.
7. **Two files written under another session's claim, both appends, both
   declared**: `docs/tier-a-reviews.json` (cc — its own merge policy declares
   append-only union merge, and the push gate refuses a Tier A change with no
   covering obligation) and `tools/tooling_inventory.py` (fourth — hank's
   `gate_parity_check.py` landed undescribed and the generator refused, freezing
   every unrelated correction).

---

# Queue 18 — 2026-10-06 (Cody) — the arm I was told to build killed the upgrade, and 21 refusals were my own bound

Full write-up: `docs/2026-10-06-cody-queue18-items-10-12-13.md`,
`docs/2026-10-06-could-not-run-ledger.md`,
`docs/2026-10-06-sql-runbook-remaining-19.md`.
Handoff: `docs/handoff-cody-2026-10-06b.md`.
## Landed

1. **`firebase-admin@14.5.0` MUST NOT BE LANDED, and my own queue-17
   recommendation is withdrawn.** The mintCustomToken arm (16 assertions, no
   network, signature verified against a generated key) fails on 14.5.0: v13+
   removed the legacy namespace, so `admin.credential`, `admin.auth`,
   `admin.apps`, `admin.app` and `admin.database` are **all undefined** and ALL
   THREE of our functions break. **1 of 249 suites changes verdict and it is
   this arm.** `initializeApp` surviving is what hid it from a load-and-list
   smoke test.
2. **Both HIGH advisories DECIDED: accept**, with the measured basis (the
   advisory is about *verification*; our one `forge.*` call is a *parser* on our
   own key) and four triggers, trigger 1 being the modular-API port.
3. **Two Tier A obligations discharged**, one a 236h takeover from a dead
   session. The eleven blob conversions are fine; **the coverage number is a
   floor** — `api_files()` uses flat `os.listdir`, so 124 subdirectory files
   holding 10 `data:` sites are outside the universe, two of them writing an
   unstripped blob beside its own id column.
4. **A timeout now says `COULD NOT RUN: bound Ns exceeded`** and never "no lock,
   no control". Per-tool bounds from measured runtimes at 2x headroom, printed
   on every run; and **two tools are UNBOUNDABLE** — both exceeded 420s without
   finishing, so no bound is set rather than an invented one.
5. **The 4 dead rules in `cross_tenant_isolation_scope.py` diagnosed, four
   DIFFERENT causes**: one unconditionally redundant regex (0 of 85 matches it
   adds), one broader twin that is load-bearing and would be lost if the wrong
   one were deleted, one masked by an OR across 165 files, one masked by a
   nesting whose branch never fires.
6. **`tools/tool_owner_map.py`** — ownership derived once and written down.
   312 tools, **17 with an `# OWNER:` line**, 66 LAST_CLAIM, 20 CONTESTED,
   **209 NONE — unknown, not unowned.**
## Mine that went wrong, all caught

1. **A verdict passed as a shell argument** got two backticked fragments eaten
   and a third replaced by the output of `id` — **a uid and gid pasted into an
   append-only ledger.** `--body-file` exists for exactly this. Reverted; the
   leak never reached origin.
2. **A `json.dumps` repair** produced 5681 insertions and 5674 deletions on a
   235-record ledger four clones merge. Reverted; the right diff was 15 and 8.
3. **The UNBOUNDABLE guard sat in a function the writer tier never reaches**, so
   it did not fire. Caught by DRIVING the tool.
4. **Two arms matched their own text** — *"my own comments trip my own
   scanners"*, which is in my notes, written twice anyway.
5. **A fabricated check** — `assert.ok(true)` with a paragraph on why it could
   not be tested. It could: a child process has an empty module cache.
6. **I nearly accused the push gate falsely.** Moving the untracked file out and
   re-measuring showed all three `--check` runs exit 0. **The gate was right.**
## Raised, not acted on

1. **The clone was found with `core.bare = true`** and every git write failed
   while `git log` kept working. One-line fix, nothing lost, **cause not
   established and not guessed.** 28 leaked worktrees are the measurable
   condition it happened under; **none are mine** and I did not sweep them.
2. **32 open Tier A obligations, 23 eligible for me, 6 assigned** — re-measured
   at the end; it was 35/26/7 at the start. **Do not quote the old numbers.**
3. **`tests/run_blob_coverage_scope_sabotage.py` is held back untracked** —
   tracking it drifts `docs/TOOLING-INVENTORY.md`, hank's when the decision was
   made. Both verdicts citing it say so.
4. **Three of my five fixed timeouts still owe the 2x rule**, and seven
   methodology rules of mine now sit in dated files.
5. **`db/schema_snapshot.json` has two blockers, not one**: `_constraints`
   absent AND the recorded sha dangling.

---
## 2026-10-06 — queue19 resumed after compaction (Cody)

**Landed in one commit:** `tools/ledger_append.py`, `tools/clone_health_check.py`,
`tools/dep_surface_check.py`, `tools/rework_tracker.py`,
`tests/run_blob_coverage_scope_sabotage.py`, their PURPOSES entries, and all
three generated documents regenerated so nothing drifts. The blocking claim
(hank batch10, which held the inventory) **handed off mid-batch**; re-derived at
`def36696`, not assumed.

**Also landed:** the Tier A discharge of hank's 2026-09-28T03:40:54Z obligation
(`alf_facility`, 207.6h, by takeover, 11 insertions not 5681), and four timeout
bounds re-measured to 2x — `metamorphic_check.py` 120→40 and `SPAWN_BOUND`=5 for
the three `git`-spawn bounds, defined once and imported.

**NOT landed, and why:** the firebase-admin modular port. Its acceptance arm is
green under 12.7.0 AND 14.5.0, the pre-port wrapper is red under 14.5.0, and
every named symbol resolves at both — but **no clean 249-suite pass exists**:
`run_all_tests.py` passed 3h16m without finishing. **ANDON.** The port is held
at `<scratchpad>/held/firebase-admin.ported.js`, branch
`cody/firebase-modular-port`.

Detail: `docs/2026-10-06-cody-queue19b-items-5-7-8-9-10-14.md`.
Handoff: `docs/handoff-cody-2026-10-06d.md`.

---
## 2026-10-07 — batch 20 (Cody): the 6h31m run broke the clone and said nothing

**LIVE INCIDENT, found and repaired.** `tools/run_all_tests.py` ran 23463s
(EXIT 1, 745 files, 91 failures), set `core.bare = true` at 2026-10-07T01:14:02Z
and left `api/sd-data.js` and `api/_lib/subcontractor-compliance.js` mutated --
the latter **syntactically invalid**. Nothing warned, because `_tree()` read
`git status`'s stdout and never its return code, so a could-not-ask was folded
into a clean answer inside the residue check itself. Repaired 10:52:29Z,
residue restored 10:54:42Z. Cause routed to **fourth** with the full artifact:
`docs/2026-10-07-cody-routed-to-fourth.md` -- **his root-cause fix `b23dbc2e`
was already in my tree when this happened**, so the cause is NOT closed.

**Hardened (mine, both landed):** `run_all_tests.py` -- `_tree()` returns a
pair, `core.bare` compared before/after, an unreadable tree is EXIT 2 and
outranks every other verdict, `--selftest` with 10 arms. `capture_exit.py` --
optional `--bound` writing `COULD_NOT_RUN TIMEOUT_<n>s` instead of a code
(cc's routed finding), plus two defects in its own selftest.

**`metamorphic_check.py` 40 -> 145s, and my previous tightening was wrong.** I
had measured the 2.76MB file; the tool bounds a checker against each TRANSFORM
of it, and `t_duplicate` doubles it -- `duplicate_global_check.py` is 0.82s
plain and **71.54s** doubled. The 40s bound failed 3 runs of 3. 145s: one run,
EXIT 0, 0 timeouts.

**Tier A:** claim released 2026-10-06T22:40:01Z so cc could take ranks 7-12;
one discharge by takeover (cc's 2026-09-28T10:44:30Z, 204.2h) with two findings
against her evidence, not her fix.

Detail: `docs/2026-10-07-cody-batch20.md`. Handoff:
`docs/handoff-cody-2026-10-07.md`.

---
## 2026-10-07 — batch 21 (Cody)

**Landed:** `--pinned` moved from a linked worktree to a **throwaway clone**
(item 3; the exact write that broke this clone now leaves `.git/config`
byte-identical); `guard_ablation.py`'s **fabricated positive** — a timed-out
suite counted as proof a guard was LOAD-BEARING, because `run()` returned 124
and `!= 0` cannot tell 124 from a real failure; `eaten_substitution_check.py`
widened to **any position** after it scanned my own eaten-backtick commit and
returned 0; the advisories reconciled to **2 high (one chain) + 1 moderate**
with `@fastify/busboy` measured as a one-line lockfile fix; and
`metamorphic_check.py` now prints **the artifact its bound actually covers**
(5.26MB from the `duplicate` relation, not the 2.76MB file on disk).

**Permissions (item 2):** `~/.claude/settings.json` merged, 12 top-level keys
preserved, `defaultMode: acceptEdits`, allow 11→42, deny 3→25, syntax checked
against the current docs. `Edit`/`Write` remain in `ask` and outrank the mode —
reported, not resolved.

**NOT landed:** item 1's six Tier A reviews (fourth holds the ledger — read-only
only, verdicts captured); item 4's pinned suite (**running**, status-file path
in the handoff); the busboy lockfile line (not in my declared set).

**ANDON HELD:** `cody/firebase-modular-port` is not an ancestor of main and
still applies cleanly.

Detail: `docs/2026-10-07-cody-batch21.md` is NOT written — the batch doc for
this one is the handoff itself plus `docs/2026-10-07-cody-routed.md` and
`docs/postmortem-cody-2026-10-07-bound-measurement.md`.
Handoff: `docs/handoff-cody-2026-10-07.md`.

---
## 2026-10-07 — batch 22 (Cody)

**Landed at `91f918e9`:** `Edit`/`Write` removed from `permissions.ask` so
`defaultMode: acceptEdits` finally governs them (allow 11→42, deny 3→25, ask
6→4, 0 grammar problems); the `@fastify/busboy` lockfile fix applied (three
lines, `package.json` untouched, moderate 1→0); **six** harness exit-0
mismatches cited with command/claimed/real/commit — **my own "five" was wrong
and is corrected**; the advisory position re-measured to **WAIT** on a measured
basis (1 of 1 `forge.*` call sites is a parser on our own key, and node-forge
1.4.0 is the newest published, so no patch exists).

**Item 4's premise was overturned:** the methodology routing **was** received —
commit `4c574225` promoted it as **convention 21**, verbatim, and fourth's own
queue row names the mechanism: paste-ready text in a document that is on `main`.

**ABANDONED:** the two-line register sha correction.
`tools/sairn_rebase_resolve.py` refused it because the ledger's identity key
includes `commit`, so a reseat is a delete-plus-insert on an append-only file.
**A sha reseat is unmergeable there by the ledger's own policy** — routed to cc,
stronger than the 24,724-line diff finding it replaces.

**ANDON HELD.** The suite is still running: 476 reported, **0 FAIL**.

Handoff: `docs/handoff-cody-2026-10-07.md`.
## 2026-10-07 — batch 23 (cody), resumed after a stopped terminal

**Found first, before any item:** batch 22 left the review-gate fix uncommitted
AND the probe **not compiling** — two string literals with a real newline,
`SyntaxError` at line 2198. A probe that cannot be imported reports nothing.
Fixed, then the batch.

**Item 8 — DONE — `8ee6e7c2`.** `--open` stamped `head_sha()`. Re-derived over
the WHOLE ledger instead of the two records that showed it: of 238 records, 63
are checkable and **34 of those 63 (54%) anchor an obligation to a commit whose
diff contains none of the files the record names** — hank 12, cody 12, hover2 4,
cc 4, fourth 2, so **five** independent record sets, not two agreeing. Same
figure at `dea44d22` and at `8ee6e7c2`. `subject_sha(files)` now returns
`(sha, basis)` and the basis is written onto the record as
`opened_at_sha_basis`: `file-set` the real answer, `head` the honest fallback,
`could-not-tell` a refusal. The file list is computed BEFORE the sha and the
record publishes that same list by construction — the first draft derived it
from a smaller set, a quieter version of the same defect. **The fixture fails
before the fix and the pre-fix run is captured, not described:** HEAD's pre-fix
module was extracted to a tempdir and driven against the same two-commit repo
(pre-fix stamped HEAD `cc2b2e81`, post-fix stamped the file's commit
`a4d1301b`, `git show HEAD -- api/x.js` EMPTY in both). The end-to-end arm
drives `_open_record`, which exists in both versions, so it goes red there;
the three `subject_sha` arms cannot, and the probe says so. Probe **EXIT 0, ALL
ARMS PASS, 223 ok — 3 runs, 2 of them at `8ee6e7c2`, first run EXIT 0.**

**Item 5 — the suite FINISHED and the run is VOID.** `EXIT 2 -- COULD NOT RUN:
the clone was broken during this run, so no verdict above is attributable`, 1
run at `c1cd7c41`, 748 files, 183 reported FAIL and **none attributable**,
11,427 s. The trigger was `git status exited 3221225794` = `0xC0000142`, a
process that failed to INITIALISE — **git could not be launched**, which is not
what the message's "something broke this clone" claims. **ANDON HELD** with
captured codes: merge-tree vs origin/main EXIT 0 `f4ebb446d0fa`, vs HEAD EXIT 0
`f2b7bb72c578`, `--is-ancestor` EXIT 1.

**Item 3 — Edit/Write CONFIRMED unprompted** in this fresh session, 10 Edits
and 3 Writes, zero prompts. **The `model` key: NARROWED to the app's own
settings writer**, window tightened to 12:48:04Z–14:30:44Z. Replaying batch
22's `merge.py` against the 12:44:42Z backup reproduces the 14:30:44Z file
except that the replay **keeps** `"model": "sonnet"` — one key, nothing else.
Not provable to the keystroke: no app-side audit log exists.
**AND A WRITE I DID NOT INTEND:** a failed `sed` left that replay pointed at the
live `~/.claude/settings.json` and rewrote it. Verified identical afterwards,
only the mtime moved. Reported, not buried.

**Item 4 — measured, and one name NOT claimed.** `Get-CimInstance
Win32_Process` returns the command lines `wmic` would not — but my suite had
already ended, so it showed only hank's processes. `--pinned` **11,427 s**;
`guard_ablation.py --limit 1` **328 s EXIT 0**;
`run_hover_audit_method_sabotage_probe.py` alone **567 s EXIT 2** (stopped
early on a red baseline, so a lower bound on a DIFFERENT path). Alphabetical
adjacency plus a lower bound is not an identification, so the 35-minute file is
**not named**. Bound PROPOSED from one measured run and labelled weak: 900 s
per file, 14,400 s per run. **No file changed.**

**Item 6 — busboy: the deploy ALREADY matches the lock, read off a real build.**
`dpl_3eBAEBXL1fM4pxZAGzJBG4SgQc5F` printed `Installing dependencies… up to date
in 836ms`; npm would have reported a change had the cached tree disagreed with
the lock. The 3.2.1 is only in the shared `C:\Users\marsh\node_modules`, which
this lockfile does not govern.

**Item 7 — node-forge: 1.4.0 is both installed and newest published. WAIT
holds, trigger written into the handoff. No code change.**

**Item 1 — REPORT ONLY.** 26 open, **6 authored by others and assigned to me**
(49.7h down to 32.8h), 13 more takeover-eligible. **Discharged none**: fourth's
live claim declares the ledger.

**Item 2 — NO memory-checkpoint tool, and NOTHING BUILT.** `tools/` has only
`audit_checkpoint_status.py`, which is about the audit record. The per-item
`CHECKPOINT LOG` habit is real and already per-item, but it writes to the
handoff in the repo, not to the memory directory, and nothing triggers it but
discipline.

**Item 9 — reproducing artifact only, NOT fixed, routed to cc.** Resolver
`EXIT 1 2026-10-07T15:32:27Z`, full REFUSED output, and the ledger's own
`"identity": ["commit", "summary"]` at
`docs/defect-density-register.json:3-9` — so a sha change is a DELETE plus an
INSERT on an append-only ledger. That file is untouched.

**Item 10 — the SQL runbook is PUSHED:** `d8bc39e4`, `--is-ancestor`
rc 0; the follow-on `ae47c86a` likewise.

**Item 11 — method improvement, routed to chat:** *a redirection that fails must
not leave the program pointed at production.* Take the sandbox path as a
required argument with no default, so a failed redirection crashes instead of
writing to the real file.

**Also found, not an item:** 30 stale worktree registrations in this clone — the
exact `.git/config`-sharing mechanism the suite guard names for a `core.bare`
flip. Not pruned (outside declared FILES, one entry locked).

Batch detail: `docs/2026-10-07-cody-batch23.md`.
Handoff: `docs/handoff-cody-2026-10-07.md`, item-12 section.

**LANDED, post-rebase:** `18078d38` item 8, `764a12a4` docs, `f7fcf20e`
register record + the cleanup fix the scrutiny flag caught, `15e56976` the
post-rewrite re-seat, `1adbdc94` the gate rows. Remote tip read with
`git ls-remote`: **1adbdc94**, ahead 0 / behind 0.
## 2026-10-07 — batch 24 (cody)

Per-item checkpoint habit ON (item 2): the handoff is written as each item closes,
not in one pass at the end. Full detail: `docs/handoff-cody-2026-10-07b.md`.

**Two batch premises were wrong and both are corrected.** Item 1 said fourth held
the Tier A ledger; fourth had RELEASED it and the real holder was **cc**, claimed
17 minutes before my attempt — my claim was REFUSED and the refusal recorded, not
overridden. Item 6 said one high and one moderate; there is **no moderate** — both
remaining highs are one node-forge advisory counted twice, unreachable
(`forge.pki.privateKeyFromPem`, return value discarded) with **no patched release**
and no lockfile-only fix, lock byte-verified unchanged.

**And one of my own batch-23 claims is REVERSED:** `--post-rewrite` is NOT the
minimal path. Both it and `--reseat` call the same `save()`, which is
`json.dumps(indent=2)` over the whole register; the one-line diff I saw was the
stored formatting matching the serialiser. The routed finding stands at full width.

**Item 3 is OPEN — the pinned run was KILLED at 586 of ~748 files with 0 FAIL and
no exit line. Second consecutive void run, different cause. ANDON HELD.** Item 4
is **UNKNOWN**: 0xC0000142 did not recur in 262 samples over 2h17m; handle and
commit exhaustion NOT SUPPORTED by measurement, desktop heap **unmeasured** and
not cleared. Item 7 still does **not** name the 35-minute file — but buffering is
ruled out by measurement, and the bound stays UNSET.

**Item 5:** 30 worktree registrations → 2, `.git/config` sha256 byte-identical,
`core.bare` false; the locked one is an interrupted `worktree add`. **Item 10:**
53 of 322 calls in the real leak class, 17 mine, **7 genuine**, 1 fixed — and the
predicate was wrong twice before it was right. **Item 8:** ITEM 15 found in the
documents (three conventions + three owed, all fourth's file).

**The basis fixture I was asked for is a SECOND COPY** — cc had already landed
`tests/run_tier_a_open_basis_probe.py`. Both pass and agree; mine derives its
cutoff from content where cc's pins a sha. Routed to chat, not resolved
unilaterally.
## 2026-10-08 — batch 25 (b2, cody)

Per-item checkpoint, committed per item. Full detail:
`docs/handoff-cody-2026-10-07c.md`. Routed: `docs/2026-10-08-cody-b25-routed.md`.

**THE PINNED SUITE COMPLETED FOR THE FIRST TIME IN THREE BATCHES** — launched
detached so a harness stop could not kill it. `EXIT 1` at 03:21:50Z after
3h13m41s, 759 files, 671 ok, **86 FAIL**, one residue path. A completed RED run,
not a void one. **No clean pass, so the andon is HELD** — on a measurement this
time. **And the watcher beside it was BLIND for the whole run and looked like it
was working:** 14,976 samples, 100% with an empty command line, zero test files,
because `powershell -Command` does not bind trailing args to `param()`. Fixed and
proved.

**Three premises were re-derived and corrected.** Item 1 is blocked by **cc**,
not hank (hank is 8.0h stale, not live). Item 2 is **skipped**: cc's
`superseded_by` support is not on origin/main, so no count delta is reported.
Item 3's sha **does resolve** — it is **orphaned**, not missing — the record is
in the Tier A ledger and not the defect register, and **the reseat tool cannot
reach it at all** because it filters to `status == `open``.

**Items 4, 6, 7 landed with fixtures.** Duplicate ledger arms removed (cc's
probe survives). `capture_exit` now reports **DEAD** for a RUNNING status whose
pid is gone — proved against the real stale file from the killed run.
`--pinned` now **KEEPS** the clone when the post-run tree read fails, which is
the evidence batch 24 had to report UNKNOWN for want of.

**Item 8: 6 of 6 mine and 36 of 36 not-mine, 0 refused.** All 25 files
claim-checked FREE first. **Item 9:** four stale artifacts gone, `.git/config`
sha256 byte-identical. **Items 10–13:** the missing ITEM 15 written, one more
bodyless row found, the runbook's four counts reconciled without picking one,
§3.5 added, and the pre-build name check extended to test files as paste-ready
text.

**And the push took six refusals**, every one correct: three for missing register
records, one for a race, and one for **copy-exactly** — 25 propagations of a
12-line helper with no recorded re-qualification. All answered.

---
## 2026-10-08 — batch 26 (b3), RESUMED after a compaction stop. All 9 items closed.

Resumed at HEAD `7803870b` with items 1–7 already landed, so nothing finished was
re-done and nothing unfinished was skipped. Claim still live at 1.5h; rebased 36
commits onto `origin/main`, rc 0, no conflicts, and **both of my declared files
that had moved upstream were re-verified rather than trusted** — the tier-A probe
EXIT 0 and the `4aa33b4565dd` reseat still reachable from `origin/main`.

**Item 2 overturned its own hypothesis: 76 of 86 pinned-suite failures are REAL**,
3 ARTIFACT, 7 COULD-NOT-RUN, 0 of 86 dirtied the clean clone. The contamination
explained **3**, not 86. **Item 3 was bigger than one record** — `reseat_shas()`
silently filtered to `status == 'open'`, and disclosing the excluded population
showed **72 reviewed records carrying a sha, 32 of them dangling**. **Item 4
CLOSED as not needed**, measured: a standalone backgrounding warning would be new
output on 106 of 107 command lines. **Item 5 NOT TOUCHED** — `scrutiny-flags.json`
is cc's by its writer's `# OWNER` line, and there are **seven** parked stashes, not
the four the item said.

**Item 6's own mechanical check found that the generator had excluded itself from
its own population.** The index declared itself derived and named
`scratchpad/b26/build_index.py` as the regeneration path — not tracked, not in its
own 64-script register, living only in a directory the index itself marks *HIGH —
cleared without warning*. All three chain links are committed now and the index was
**regenerated rather than hand-edited**; `tools/external_file_index_audit.py` went
EXIT 1 → **EXIT 0 CLEAN**, 13 arms, 5 negative. **Convention 26 applied against a
file I had committed myself one commit earlier**: `inventory2.py` dropped its raw
beside itself, which became a live-path fallback the moment it was tracked.

**Item 8** landed as full text in its own section of `docs/METHODOLOGY.md` —
*a contamination warning makes every result in its scope unfalsifiable, so it must
ship with the isolation method* — routed to fourth for a number, not self-promoted,
with every figure re-derived from the TSV rather than quoted.

**Still open and named:** `/context` and `/mcp` need Michael; `autoCompactWindow`
sits beside `autoCompactEnabled = false`; the seven stashes are cc's call; the
session-start check is built and unwired because `.claude/settings.json` is in cc's
FILES; and the long stall is still **not named** — 420 s is the bound, not a
measurement.


---
## 2026-10-12 -- batch 27 (b4), landed 85410985

Eight of nine items resolved. Full account: `SAIRN-report-cody-b4.txt` (869
lines, body hash on line 2), `SAIRN-digest-cody-b4.txt`, handoff at
`docs/handoff-cody-2026-10-12.md`.

- **item 3, law_role_granularity, IS NOT DONE** and must not be "fixed" by a
  session. It needs a bar-rules decision about a law firm's role vocabulary;
  `api/sd-data.js:13789` and `:15719` both decline to invent one in writing, and
  hover2 routed it without prescribing a fix. Three of the brief's premises
  about it were wrong and are corrected in the report with measurements.
- item 2: 3 Tier-A shas reseated on a strong basis, 11 WEAK routed with their
  sessions, 25 refused routed. The brief's "21 and 11" were the wrong way round.
  Three defects found in the reseat tool itself.
- item 4b: `sen_caregivers/read` leaked background-check dates, state caregiver
  IDs and HR notes to every signed-in role. Field-level redaction + the client
  half, because a redacted compliance column rendered identically to "no check
  on file". 18 arms, fail-first 15/3.
- item 4a: `cl_feedback_log` recorded no employee, at both layers, under a
  comment claiming it did. 8 arms, fail-first 4/4. **Guardian Check 29 is NOT
  satisfied** -- the migration has not run against a real database.
- item 5: both push-gate probes moved off a linked worktree (which shares
  `.git/config`) to a throwaway clone. Mechanism verified; the probes' own
  verdicts COULD NOT RUN because a clean push is refused over another session's
  Drive handoff.
- item 6: three duplicate DOM ids, every one a live defect.
- item 7 REMOVED from scope -- fourth holds it, real overlap, not reworded.

**Two things for the next session, both in the handoff's section 0:** this clone
was running with every hook stripped in an uncommitted `.claude/settings.json`
(second clone the same evening), and NINE other-session handoffs on the shared
Drive blocked this clone's push five times -- four of them arriving during the
declarations of their predecessors.


---
## 2026-10-13 -- batch 27 (b5), landed 054ffcd0 (report 489bcda8)

14 of 14 items done. Full account: `SAIRN-report-cody-b5.txt` (699 lines, body
hash on the second-to-last line, verified), `SAIRN-digest-cody-b5.txt` (127
words), handoff at `docs/handoff-cody-2026-10-13.md`.

- **item 1: law_role_granularity IS NOW IMPLEMENTED.** b4 refused it because the
  split was an unmade bar-rules decision; b5 arrived with Michael's decision, so
  `api/_lib/law-roles.js` transcribes it -- ONE 19-row table, ONE `decide()`,
  called from the TWO gates that already existed. Trust resources hard-locked in
  a separate structure so the lock survives a table edit or an override.
  25-arm test, monotonicity as a metamorphic relation, five planted violations
  each asserted to fire. Fail-first measured: 23/2 before, 25/0 after.
- **item 8 CORRECTS MY OWN b4 REPORT.** The sabotage "flake" was not a flake and
  not `os.replace`: 20/20 runs pass in a clean clone, and the b4 log named its
  own cause (a dirty-tree/stage mismatch on `docs/tier-a-reviews.json`) which I
  under-read. The real defect found instead is WORSE -- arms 11/12 race two
  `save_reviews()` onto one path, 305 of 400 driven iterations raise
  `PermissionError`, and 12 of 12 gate-probe logs carry it while all 12 exit 0.
  Permanent and silent, not intermittent. **NOT FIXED, open, owner cody.**
- item 5: TWO sen_caregivers read paths, neither leaks. The second
  (`sen_visits/readiness`) was found by grepping every fetch site.
- item 6: both push-gate probes have verdicts with no network, and a refusal by
  a DIFFERENT check is now a fourth state -- UNPROVEN, said in the verdict line.
- item 7: `tools/dup_dom_ids_check.py`, 22 files, 7,752 ids, 0 duplicates,
  23-arm control pair. Guardian Check 8 had never had a tool.
- items 9/10/11: drafts not missing (112/112; coverage 13%); 145 no-sha records
  split 82/61/2; the matcher collision already fixed by cc, with the residual
  gap being the majority shape (29% of claims declare FILES).

**This branch was MERGED, not rebased** -- `sairn_rebase_resolve.py` correctly
refused to replay a sha re-stamp against its append-only rule. Register merged
by `(commit, summary)`: 522 records, zero lost.
## batch 27 (b6) -- LANDED 2026-10-13, in two sittings

**ON `origin/main` at `e767eb2d`, 0 ahead / 0 behind. 8 of 8 commits verified
ancestors one at a time.** `SAIRN-report-cody-b6.txt` (910 lines, hash rule
self-checked), `SAIRN-digest-cody-b6.txt` (133 words, `digest_lint` CLEAN),
handoffs at `docs/handoff-cody-2026-10-13b.md` (the refused sitting) and
`docs/handoff-cody-2026-10-13c.md` (the landing).

- **items 1/2: arm 11 was announcing a race it had not run.** `_saver` called
  `save_reviews()` with no try/except, so the `PermissionError` that
  `MoveFileEx` raises on a held destination went to `threading`'s printer and
  never to the exit code -- **and both assertions still passed**, because the
  surviving writer leaves a file that parses. RED in 31 of 40 on the old shape,
  GREEN in 40 of 40 with a `PermissionError`-by-name retry. Arm 12 had the same
  hole with a worse answer: `len(names)==1` **is also satisfied by a dead
  writer**. Safety never failed; liveness did. **The product half --
  `save_reviews()` has no retry of its own -- is ROUTED to cc, not fixed.**
- items 3/4/5: three arms are real passes in both remote modes; the citator
  schema is printed in full for Michael to run; the UNPROVEN methodology note
  proposes a rule and **deliberately builds nothing**.
- **item 6 was REFUSED in the first sitting and the refusal was recorded
  verbatim rather than unblocked** (report §7, unchanged). The second sitting
  cleared both **at their cause**: the inventory regenerated, because the drift
  was b6's OWN rewiring of `check4_probe` -> `sairn_seam_check` and
  `check7_probe` -> `preauth_oracle_check`; and the external-file-index refusal
  **disappeared without an edit by me** when cc's warn-not-block change landed.
  **So §7.3's second remedy was never the remedy** and is left standing wrong,
  with §7.4 saying why -- b4 and b5 had already written into that index that
  declaring those handoffs one at a time cannot converge.

**Two failures that are NOT gate refusals and are not recorded as ones:**
`sairn_claim.py`'s own push cannot land from a history carrying a merge commit
(it rebases, replays `009ff176`, hits the same `scrutiny-flags.json` conflict,
and reports NOT CLAIMED twice while the entry sits committed) -- publish the
claim with an ordinary push instead. And the first real push was rejected by a
**ref lock**, not a check: four sessions into one branch, `origin/main` moving
13 then 19 commits then again mid-push. The retry loop re-ran
`tooling_inventory --check` after **each** merge, because a loop that only
retries the push would ship the drift it had just fixed.

**OPEN against b6's reviewer:** the EXTRA SCRUTINY `[WEAKENING]` flag on
`tests/push_gate/check4_probe.py` (assertions net removed, 3 removed 2 added),
recorded under `c465743b34b0` in `docs/scrutiny-flags.json`. This landing did
not discharge it. **Nothing mechanical gates this clone any more** -- hook
entries are 0 by Michael's decision, so `--preflight` IS the gate here and
skipping it is silent.

---
## b19 — 2026-10-16. LANDED at `1e3e61eae` on `origin/main`, read back by content, no `--force`

**b19 began by finishing b18, because b18 had been cut off before writing
anything.** No b18 handoff, report or digest exists on the Drive; three b18
commits sat unpushed for 20 hours with **two files still uncommitted**, and the
b18 claim was still `active`. One of those two files **did not work**:
`tests/run_dead_rule_sweep_probe.py` was EXIT=2, dying after section I's
header, because the sweep is driven THREE ways and only two have call sites —
section I calls `make_sandbox()` **in-process**. Fixed by re-execing the whole
probe under `tools/git_config_isolation.py` once. **And the two wrapped call
sites were reading the wrong number under the right name:** the wrapper's exit
code is its verdict on `.git/config` and `.git/worktrees`, not the wrapped
command's, so every arm reading `rc` had silently changed quantity. The inner
code comes back through `--rc-file` now. New arm **G0** asserts
`SAIRN_GIT_ISOLATION=1` by name, because the refusal banner contains the string
`DEAD RULE SWEEP` and **F2 — the paired positive proving the sweep STARTED —
passed on the message saying it would not.** 84 passed / 0 failed.

**Floor 808 → 824, and it met another clone's 811 in a rebase.** 824 > 811, the
ratchet only rises, 824 is what a triaged full-tree run measured. **The real
finding is next to it:** the 811 version arrived with `lowered_from_813_why`
**absent** — dropped by `raise_floor()`, which rewrites the file from its own
fixed key set — so every hand-written key here survives only to the next raise.
Restored, with the hazard written into the file.

**The five items.** Arm Z's missing `else`, with the **ablation re-run and it
came back RED** (PRE-FIX ablated: exit 0, arm simply absent; POST-FIX ablated:
exit 1, arm Z FAIL) — driver committed at `docs/b19-logs/ablate_arm_z.py`. The
blob-scope and leg_aftercare rows moved `entries` → `recovered` with the
**superseded row quoted inside each rather than deleted**, because in both
cases the row was a faithful record of a real run and the diagnosis around it
was wrong. The control arm's typed *"ten failures above"* reads off
`failed.length`. The b24 F1 re-anchor onto a **balanced block** plus **arm 3**,
which renames the anchor in a COPY of each subject and requires **exit 1, not
exit 3** — ownership decides the exit code. And a new failing-first suite
driving a **23514 through the `alf_op_audits` write guard** (503
NOT_PROVISIONED, on a Tier A log) and a **42703 through the `mech_site_assets`
read guard** (HTTP 200, byte-identical to a 404), with the **151 and 67
populations measured by the suite on every run** rather than quoted.

**Convention 36** — *a check's own rot is not biased toward RED, and the exit
code must be chosen by OWNERSHIP*. Twelfth member of the cannot-fire group,
admitted on two of its three instances and said so. **And `METHODOLOGY.md`'s
"18 promotion rows" was wrong** — 23 then, 24 now, same blob at both commits,
so convention 35 clause 3 says the published number is the wrong one.

**Tier A:** obligation opened 2026-10-16T12:24:12Z on `alf_facility`,
`alf_op_audits`, `leg_aftercare`, `mech_site_assets`, **assigned to cc**.
**Nothing FRESH is assigned to cody** — five obligations, newest **243h** old,
all `--takeover`-able. Measured, not assumed absent.

**NO OVERRIDE OF ANY KIND.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no
`SAIRN_SEED_GATE`. **The push WAS refused once** — the `derived-docs` gate, on
three generated documents b18 and b19 had made stale — and the remedy was to
run their generators, not to skip the gate. No `api/`, `sql/` or `tools/` file
edited; `api/` is COPIED for every counterfactual.

**Left for the next session:** both of cody's claims (`cody-1792078195` from
b18 and `cody-1792149459` from b19) are **still active** — `release` takes a
subject and not an id, so releasing `tests` would have dropped the live one
too. b18's `wt18` worktree was registered against this clone and has been
removed and pruned.

**CORRECTION to the paragraph immediately above, same batch, before the
artefacts were final.** It said both of cody's claims were "still active" and
deliberately left so, because `release` takes a subject and not an id and
would have dropped the live b19 claim with the stale b18 one. **That was the
wrong call, and the premise was wrong in a useful way:** taking both IS the
desired outcome — both are cody's and both are finished — and the cost of
leaving them is two stale claims on `tests` blocking every other clone from
that directory for four hours each, which is the claim system pointed the
wrong way. `python tools/sairn_claim.py release tests` released **both** by
name in one commit and reported *"pushed and verified on origin/main"*.
**NO CLAIMS HELD BY CODY AFTER b19.** The old sentence is left standing above
rather than edited out, because this file is append-only and a published
statement needs a correction and not a silent overwrite.

## b36 item 3 — legacy-blob exposure CLOSED CLEAN (cody, 2026-10-21)

Michael ran `sql/b36-legacy-blob-projection-keys.sql` and reported every count 0.
No live row carries a projection key inside its `data` blob. **Decision: no read
gets flipped.** The 21 inverted `Object.assign(columns, data)` reads that
`api/b36-projection-runtime-differential.test.js` measured are inert. Arm A shows
today's writes cannot create the condition, and the live data shows no older row
holds it.

**Count note:** the SQL has **21** statements, one per exposed resource, and the
reported result says "22 resources". `alf_incidents`, the 22nd paired resource,
was left out of the SQL because its read already lets the column win. So the
22nd count was never queried. That does not change the verdict.

**What would reopen this:** a new write path that does not strip its keys (arm A
fails), or a bulk import or restore that writes `data` directly.
