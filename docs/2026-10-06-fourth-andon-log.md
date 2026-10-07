# Andon log — fourth

**Started 2026-10-06 (batch 10), as a standing practice rather than a one-off.**

An **andon pull** is a halt-and-flag: I stop a specific item short of
merge/deploy because of a genuine uncertainty, say so here, and keep going on
everything else. **A pull is never held against the puller.** The thing that
gets held against somebody is shipping past the doubt.

**Zero pulls in a batch is not automatically good.** On a platform whose own
standing conventions are mostly about checks that cannot fire and documents
that went false, a batch with no halts is more likely to mean nobody looked
than that nothing was uncertain. Both numbers are logged — pulls, and the
batch they came from — so a zero can be read as the claim it is.

**Logged either way:** a pull that turns out to have been unnecessary stays in
this file with that outcome written next to it.

| # | Date | Item | Pulled because | Resolution |
|---|---|---|---|---|
| 1 | 2026-10-06 | batch 10 item 2 — merge `constraints.json` into `db/schema_snapshot.json` as `_constraints` | **The named input does not exist.** `constraints.json` is absent from this clone (searched the whole tree, `%USERPROFILE%`, Downloads, Desktop) and from all five sibling clones. It can only be produced by running `sql/schema_snapshot_constraints_query.sql` in the Supabase editor against the live database, which I cannot do. | **HALTED, unmerged.** Everything around it verified instead: the claim is CLEAR, the snapshot's keys are `_generated_at`, `_anon_grant_baseline_2026_08_26`, `_anon_nontable_baseline_2026_08_26` and **no `_constraints`**, 439 tables, generated `2026-10-05 15:10:30+00`; and the preflight's verdict is real, measured, not inferred — see below. **Needs Michael.** |
| 2 | 2026-10-06 | batch 10 item 3 — the `.git/config` writer inside `check8_probe.py` | Pinned to ONE STEP (`dry_push(probe_env=False)`, the first dry-run push whose outgoing range resolves) but **not to one command**. The remaining suspects are inside `tools/sairn_push_gate_hook.py`'s check-12 path, which builds a base worktree and runs **generators from the base commit** with cwd inside a worktree — where a `git config` write lands in the shared config. That is a plausible mechanism and **not a measurement**. | **CONTAINED, NOT ROOT-CAUSED, and labelled as such in the file.** Config is snapshotted, reasserted after every push-shaped step, restored at exit, and backed up for the killed path; `--check-residue` / `--restore-config` repair a killed run. The arm still FAILS, deliberately, because the writer is still there. **PULL CLOSED THE SAME DAY BY SOMEBODY ELSE'S WORK, WHICH IS WHAT A PULL IS FOR.** `docs/2026-10-06-cody-queue19-items-2-3-4.md` reached the same place independently and named the class: cause tag **`SHARED_CONFIG_WRITE_FROM_WORKTREE`** — a `git config` write made with cwd inside a linked worktree lands in the SHARED `.git/config`, so a tool that means to configure its own sandbox configures the clone. That is the hypothesis this pull recorded, confirmed from the other side. Cody also measured that NOTHING in the repo sets `core.bare` directly and that all four `git init --bare` uses are correctly scoped to their own temp directory, so the remaining suspect really is the worktree-cwd class. **UPDATE, batch 11: THE REACH IS FIXED AND THE WRITER IS STILL CC'S.** The fixture is a throwaway `git clone --local` now, not a linked worktree, so a `git config` write inside it cannot land in this clone whoever makes it — 9 driven runs, config byte-identical on 9 of 9, and the arm that used to fail on purpose is green. **That closes the REACH, not the WRITE.** Root cause of the write still OPEN and routed to cc (owner of `tools/sairn_push_gate_hook.py` per `docs/tool-owner-map.json`), not to me. |
| 3 | 2026-10-06 | the instruction to discharge my most overdue Tier A review obligation first | **cody holds `docs/tier-a-reviews.json` under a live claim and the claim's own first line is "Tier A discharges most-overdue-first with adversarial controls"** — the identical work. Discharging into that file would be two sessions writing the same ledger in the same hour. | **HALTED. Nothing written to that file.** My nine eligible obligations are listed in the handoff with their ages so they are not lost, and the most overdue (228h, `alf_staff` + `sen_visits`) is named explicitly. Flagged rather than taken, per the standing rule that a claim overlap is stopped and handed back, not disclosed and proceeded through. |

## Pull 1 — what was verified instead, and the exact next step

The preflight's inability to compare is **measured, not assumed**:

```
python tools/capture_exit.py --status demo.status -- \
  python tools/sairn_sql_preflight.py --live db/schema_snapshot.json sql/sairnlegacy_data_schema.sql
EXIT 0 2026-10-06T16:07:59Z
```

and its CHECK CONSTRAINTS section reads, in full:

```
CHECK CONSTRAINTS
    COULD NOT CHECK      snapshot carries no _constraints key -- re-run
                         sql/schema_snapshot_query.sql to capture them
```

**The merge command is already written down** and nothing new is needed for it
— `sql/schema_snapshot_constraints_query.sql` carries it at its "HOW TO USE"
block. The whole remaining step is:

1. Run `sql/schema_snapshot_constraints_query.sql` in the Supabase SQL editor.
2. Save the single JSON cell as `constraints.json`.
3. Merge it (the one-liner in that file), **including an empty
   `{"_constraints": {}}`** — the file says why: an empty object means *asked,
   and there are none*, a missing key means *never asked*, and the preflight
   distinguishes them.
4. Re-run the preflight; the CHECK CONSTRAINTS section must report a
   comparison rather than a could-not-check.

**`constraints.json` itself is not committed** — per the dispatch, and because
it is a transcription of live database state, not a repo artefact.

---

# BATCH 11 CONTINUATION — 2026-10-06, after the context exhaustion

## PULL 4 — this clone was CORRUPT when the session opened, AFTER the fix commit

**Halted on:** the session's first command, `git status --porcelain`, failed
with `fatal: this operation must be run in a work tree`.
`git config --get core.bare` returned **`true`**, with the fixture identity
`fx@example.invalid` also present in `.git/config`.

**Why it was a pull.** `b23dbc2e` ("fix(check8): ROOT CAUSE, not containment —
the fixture is a throwaway CLONE now") landed at 16:03 and the corruption was
observed at ~17:50. Two readings fit and, at the time of the pull, the evidence
did not separate them:

1. the fix did not work, or does not cover every path; or
2. the fix works, the residue was left on disk by an earlier run, and
   **nothing repairs it**.

**RESOLVED LATER THE SAME SESSION — READING 2.** `python
tests/push_gate/check8_probe.py` was then run **in the live clone** at HEAD
`7eabd192` with `.git/config` copied beforehand:

    === CONFIG DELTA ===   CONFIG UNCHANGED   (byte-for-byte diff)
    === STATUS DELTA ===   STATUS UNCHANGED
    === HEAD ===           7eabd192, unmoved

and the probe now carries its own arms for it — *"and the CLONE was never
touched — no commit, no modified file"* and *"...and neither was `.git/config`
— byte-identical to the pre-run copy"*, both **ok**. The writer is fixed. The
residue was pre-fix and nothing cleaned it up.

**The thing worth escalating is true either way:** `.git/config` is
**untracked**. No commit, no `git status`, no push gate and no pull can see
the residue. It survives every fetch and every rebase, and the only symptom is
that every subsequent git command in the clone fails outright. There is a
fixed writer and **no detector for what it already wrote**. That gap is
separate from the writer, is in nobody's claim, and is named here rather than
folded into item 4's result.

Repaired by hand with `git config --unset core.bare`, verified by
`git config --get core.bare` returning nothing and `git status` working again.

## PULL 5 — two of my nine Tier A obligations CANNOT be reviewed, and the gate says so

`python tools/tier_a_review_gate.py --list` — **PROGRAM_EXIT=1**, at HEAD
`762b084b`, 2026-10-06. **31 open obligations; 9 eligible to fourth** (records
authored by another session and assigned to `fourth`), most overdue first:

| author | identity | resources | overdue | freshness |
|---|---|---|---|---|
| hank | 2026-09-27T03:42:29Z | alf_staff, sen_visits | **235h** | **COULD-NOT-TELL** — sha `54e4835ac96e` UNREACHABLE |
| cody | 2026-09-28T03:34:57Z | dnt_ar, dnt_revenue | **211h** | **COULD-NOT-TELL** — sha `f88105a88287` UNREACHABLE |
| hank | 2026-09-28T03:40:54Z | alf_facility | 211h | STALE — moved since `1faa4d99526a` (reachable) |
| cc | 2026-09-29T17:47:11Z | alf_activities, alf_billing, alf_clients, alf_facility, alf_mar | 173h | fresh |
| cody | 2026-09-30T10:58:02Z | rf_claims, rf_invoices, sen_visits | 156h | fresh |
| cody | 2026-09-30T12:08:26Z | sv_audit_log | 154h | fresh |
| hank | 2026-09-30T12:59:51Z | bld_change_orders, bld_inspections, bld_toolbox_talks, bld_warranty, mech_checks, quotes, sd_exec_msgs | 154h | fresh |
| hank | 2026-10-05T09:03:14Z | grd_irr_zones, grd_rounds | 37h | fresh |
| cody | 2026-10-05T13:23:46Z | invoices, scp_quotes, sd_sms_log | 33h | fresh |

(A tenth row assigned to `fourth` — identity `2026-10-05T09:50:00Z`,
`invoices` — is **authored by fourth** and is therefore not eligible to me.
Counted out rather than silently skipped.)

**Halted on:** the **two most overdue** carry `** COULD-NOT-TELL ** the
recorded sha does not resolve in this clone`. Verified independently with
`git cat-file -e <sha>^{commit}`: `54e4835ac96e` and `f88105a88287` are both
UNREACHABLE, while `1faa4d99526a`, `1da31d4ceb77` and `15843e311da8` resolve —
so this is per-record, not a broken clone or a missing fetch. Four of the six
distinct SHAs in the overdue block are gone, rebased away without a reseat.

**A review obligation whose subject commit cannot be read cannot be
discharged.** Signing it off would be an assertion that somebody read a diff
that is not in this clone, which is precisely the thing the review record
exists to make true. "Could not tell" is the third state and it is not a pass.
**Escalated rather than discharged, and rather than discharged with a caveat.**

## THE WRITE IS BLOCKED AND I DID NOT OVERRIDE IT

`docs/tier-a-reviews.json` is **cody's**. cody's claim has passed the 4-hour
expiry timer, but `python tools/sairn_status.py` reports **cody `working`
LIVE** on "queue19 resume", and queue19's own first item is *"Tier A discharge
most-overdue-first"* — the identical work. **Expiry is a timer, not a
release.** The nine rows above are listed so the work is ready to land and are
**not** discharged; nothing in that file was written by this session.

*(SHA re-seat 2026-10-06: the six commits this file cites were rewritten by a `git pull --rebase` onto eleven upstream commits shortly after they landed. The pre-rebase SHAs 100b82fc (now `6b77545f`), 7c911e5c (now `326d277e`) and 6984634e (now `7eabd192`) are ORPHANED -- on no ref, absent from every other clone, and gc-eligible here; the equivalents 6b77545f, 326d277e and 7eabd192 are cited above and are verified ON `origin/main`.

CORRECTED 2026-10-07, AND THE CORRECTION MATTERS MORE THAN THE WORD: this note first said those SHAs were UNREACHABLE, verified with `git cat-file -e <sha>^{commit}`. **That command tests whether the OBJECT EXISTS, not whether any ref reaches it**, and an orphaned commit's object survives until `git gc`. So `cat-file -e` answered OK for all four orphans and would have let a re-seat pass itself as verified. The test that answers the question actually being asked is `git merge-base --is-ancestor <sha> origin/main`, which distinguishes three states where `cat-file` sees two: ON a ref, ORPHANED-but-present, and ABSENT. The same mistake would have reported the two unreviewable Tier A SHAs as fine had they been orphaned here rather than genuinely absent -- `54e4835ac96e` is ABSENT, which is why `cat-file` happened to be right about it. **A reachability claim verified by an existence check is a third state collapsed into two**, which is convention 17 arriving in a second place within one batch, and it is recorded here rather than promoted to an eighteenth. Every MEASUREMENT in this file was taken BEFORE those eleven upstream commits arrived, so the tree it describes is the rewritten commit's parent tree, not its current one. Re-seated by hand because `.githooks/post-rewrite` re-seats the defect register and the generated tracking documents, and this file is neither.)*

---

## PULL 6 — the suite runner's `--pinned` mode BREAKS THE CLONE, in the mode that exists to prevent it

**Halted on:** `python tools/run_all_tests.py --pinned --pinned-ignore-dirty`
finished (**`PROGRAM_EXIT=1`**, 782 lines, pinned at `762b084b`) and left this
clone with `core.bare = true` and `git status` answering
`fatal: this operation must be run in a work tree`. Repaired by hand for the
**second time in one session**.

**Why it is a halt and not just a bug report.** The mechanism is proven and it
is generic, not specific to any one probe:

    git worktree add -q --detach <WT> HEAD
    git -C <WT> config core.bare true      # exit 0
    → the CLONE's .git/config gains `bare = true`, byte-for-byte the delta the run left

A linked worktree has no config of its own. **So `--pinned` isolates files and
does not isolate configuration, and ANY probe in the suite that writes git
config reaches the live clone.** `check8_probe`, the known past writer, is
`ok` in this run and leaves the config byte-identical standalone — it is not
the cause. The caller is not yet identified and four standalone candidate runs
came back clean, which proves nothing because standalone is not in a worktree.

**AND IT MAKES EVERY EXISTING SUITE VERDICT AMBIGUOUS.** Two probes have
opposite results depending only on the environment, same SHA, minutes apart:
`seam_check/run_delegation_probe.py` is **FAIL** in the worktree and **exit 0
green** in the clone; `push_gate/check8_probe.py` is **ok** in the worktree and
**exit 1** in the clone. No record on this platform states which environment
produced a verdict — including `docs/known-red-suites.json`, whose entries
carry a `tail` and no environment field. **Escalated because that invalidates
the premise of the red register itself, which is not mine to redesign.**

**NOT FIXED, and the reason is a measurement:** the strategy change is a
throwaway clone instead of a worktree — the fix `b23dbc2e` already applied one
layer down — and it can only be verified by a full pinned run, now measured at
**over two hours** in this environment against 22 minutes for 656 lines earlier
the same day. Landing an unverified change to the one tool every session uses
to ask "does the suite pass", at the end of a batch, with no way to re-run it
before handing off, is not a trade worth making.
`docs/2026-10-07-fourth-routed-pinned-worktree-shared-config.md` carries the
artifact, both candidate fixes with the weaker one marked as not actually
closing it, and the one-command-per-candidate next step.

**`tools/run_all_tests.py` is in NO active claim** at `9e380383` —
`python tools/sairn_claim.py check tooling "run_all_tests pinned worktree
isolation shared config"` → `CLEAR`. So this is unowned, not blocked.
