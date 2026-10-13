# Handoff — cody, batch 28 (b7), 2026-10-13

**Written at a settled point: everything below is committed and on
`origin/main` except this file and the report and digest that follow it.**

**Nothing was overridden. `SAIRN_SEED_GATE=off` was NOT used, no hook was
restored or re-added, `.claude/settings.json` was never committed by me, no
`api/` file was edited, and no auditor clone was entered.**

---

## 1. Committed state

| | |
|---|---|
| HEAD, before this handoff's own commit | `7c54590f` |
| origin/main | `7c54590f` — **0 ahead, 0 behind**, working tree clean |
| the b7 commits | `db2a47f1` `24e88957` `5ee4406b` `4ff63a51` `cbd9eebd` `a339112d` `3b8f23d3` `e1801b06` `b34308fc` `c322d739` — **all ten verified ancestors of `origin/main`** by `git merge-base --is-ancestor` |
| push | `git push origin main` → `4dd3f1d1..7c54590f  main -> main` |
| claim | `cody-1791888490`, subject `tests`, **HELD at the time of writing; released after the report and digest land.** Age 9.94h, so it is PAST the 4h expiry and anybody reading `--list` should treat it as stale rather than as a live block |

---

## 2. What landed, item by item

| # | Michael's item | state |
|---|---|---|
| 1 | the driven SAIRNfreedom matrix + the `bld_draws` role arms | **DONE.** `tests/sf_role_matrix_driven.test.js` 25 arms / 540 driven cells, exit 0. `tests/bld_draws_role_arms.test.js` 10 arms, exit 0 |
| 2 | the three hank-authored `api/` Tier A records; re-seat the two orphaned shas | **ONE OF TWO RE-SEATED, and the other is REFUSED FOR CAUSE** — see §3. One record reviewed and DISCHARGED, one reviewed and handed over, one unreachable from this clone |
| 3 | build `unproven_arm_check`; re-derive and resolve the `check4_probe` WEAKENING flag | **DONE.** `tools/unproven_arm_check.py` + `tests/run_unproven_arm_probe.py`, 15 arms exit 0. The flag is re-derived and resolved as a FALSE POSITIVE, routed for sign-off because I am its author |
| 4 | `verify_citator_feedback.py --check-only` then `--write` | **STOPPED AS INSTRUCTED. BOTH env vars are missing** — see §4. `--write` was NOT run |
| 5 | the 19 seam pairs → a table with one owner per pair + a closing procedure | **DONE.** `docs/2026-10-13-cody-b7-seam-pair-owners.md`. The table is derived from the tool and verified row-for-row |
| 6 | commit/discard the uncommitted edit to `docs/handoff-cody-2026-10-13c.md`; push; release | **NOTHING TO COMMIT OR DISCARD.** That file was already committed at `72ca3ad1` before this session began, and `git diff origin/main` on it is empty. Pushed without force and confirmed landed. Release follows the report |

**Also landed, from my own b7 claim rather than from Michael's six:**
`tools/git_config_isolation.py` and `tests/run_worktree_isolation_probe.py`
(10 arms, exit 0), **and the guard is ADOPTED into three tools and measured
working** — a bare `python tools/condition_coverage.py` now exits **2 COULD NOT
RUN** with `.git/config` byte-identical (`93070fe59db2`, measured either side)
and zero `.git/worktrees` entries created. That closes **3 of the 13** bare-run
write findings in `docs/2026-10-13-hank-b6-routing.md` item 1.

---

## 3. Item 2 in full, because the instruction and the tool disagreed

Michael's instruction was *"Two have orphaned shas: re-seat them."* **Only one
of the two is re-seatable from this clone, and the refusal on the other is the
tool's, not mine.**

| record | reviewer | what happened |
|---|---|---|
| `2026-10-06T06:14:34Z` | **cody** | **RE-SEATED** `c0be1a702088 -> 8246d8bab707`, basis `FILE-SET SUBSET` — the WEAK basis, needing `--write` **and** `--write-weak-basis`. Reachability re-checked with `git merge-base --is-ancestor` before any review. **Then DISCHARGED**, by me, as the assigned reviewer and not the author |
| `2026-09-27T03:42:29Z` | fourth | **REFUSED `[NO_OBJECT_IN_CLONE]`.** The sha is not in this clone's object store so its subject cannot be read, and no commit anywhere contains its file set. **Reseatable by subject only from the clone whose rebase orphaned it** |
| `2026-10-12T01:51:33Z` | cc | **REACHABLE. Reviewed here, deliberately NOT discharged** — the keystroke belongs to its assignee and `docs/tier-a-reviews.json` is in cc's live claim. Verdict text is in `SAIRN-report-cody-b7.txt` ready to paste |

**The one thing in the review worth carrying forward:** 8 of the 9 resources on
the cc record are in `SD_SESSION_GATED` at HEAD and `dnt_appointments` is **not**
— and that is **my measurement being incomplete, not a gap in the code.** Every
`dnt_*` branch runs through a blanket `dntGate` instead (18 call sites,
app-scoped `verifySessionToken`), which both the read and write branches call on
their first line. Two mechanisms, one guarantee. A reviewer measuring only the
table would have filed a false finding against hank.

**A fourth record surfaced and is MINE to fix, not to re-seat:**
`cody 2026-09-28T03:34:57Z` is `REFUSED [SHA_WRONG_WHEN_WRITTEN]` — the sha was
already wrong when written, which is a different fault from a rebase, and the
tool says *"FIX THE RECORD, not the sha"*. Not touched this batch.

---

## 4. Item 4 — exactly which credential is missing

`python tools/verify_citator_feedback.py --check-only` → **exit 2 COULD NOT RUN**:

```
COULD NOT RUN: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must both be set.
Nothing was read and nothing was written. This is exit 2, not a pass --
a missing credential is not evidence that the schema is correct.
```

**BOTH are missing, not one.** Verified independently of the tool:
`os.environ` carries neither, and `.env.local` in this clone holds exactly one
key, `VERCEL_OIDC_TOKEN`. The tool does not read `.env.local` at all.

**`--write` was NOT run and nothing was guessed.** Michael's confirmation that
`cl_feedback_log` has `employee_id` and `employee_role` is recorded and still
unverified from here: **Guardian Check 29 remains unsatisfied for the b4
`cl_feedback_log` change.** Next step is one of
`SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python tools/verify_citator_feedback.py --check-only`
and then the same with `--write`, from a shell that has them.

---

## 5. THE ONE THING THE NEXT SESSION MUST KNOW BEFORE IT TOUCHES THIS CLONE

**Files in this clone were modified by something other than me, repeatedly,
within seconds of my own edits, and `main` moved while I was on a detached
HEAD.** This is stated as an observation and not as a diagnosis, because I could
not identify the writer: `TaskList` was empty, `.claude/settings.json` has
`hooks: []`, and no background job of mine was running.

**What it cost, measured:**

1. `tools/unproven_arm_check.py` gained a comment asserting an ablation of
   **"0 of 2 before, 2 of 2 after"**. I re-ran that ablation myself against
   `check4_probe.py` and `check7_probe.py` at `c465743b~1`. **The real sequence
   is three numbers: 0 of 2, then 1 of 2, then 2 of 2** — the fail-counter form
   caught only `check7`, because `check4` ends `sys.exit(0 if ok else 1)` and
   names no failure counter at all. Corrected in the tool, in
   `tools/report_only_checks.py` and in the regenerated inventory.
2. `tests/run_unproven_arm_probe.py` briefly carried a **syntax error** and then
   **two duplicate fixture headers**, where a dict keeps the last silently.
   `_parse_fixtures` now **refuses** a duplicate header.
3. **`git add -A` committed a revert I had already verified as reverted.** I
   reverted a broken guard adoption in three of cc's tools, measured all three
   importing again, and then `a339112d` re-staged a concurrent re-add I had not
   re-checked. The commit message of `4ff63a51` says the adoption was reverted
   and **that sentence is false for the committed state**; `3b8f23d3` is the
   amendment and `e1801b06` is the defect record it owed.

**THE STANDING RULE THIS PRODUCES: in this clone, do not stage by wildcard.**
Name paths, and re-read `git diff --cached` immediately before every commit. A
commit message written thirty seconds earlier can be false by the time it is
committed, with no further edit by its author.

**A second consequence:** an attempt to amend a commit two back behind a merge
picked up another session's staged `api/` and `sql/` files and produced a commit
carrying **hank's work under my authorship**. It was discarded unreferenced,
`main` was never moved, and the backup tag **`b7-backup-pre-amend`** still
points at the pre-attempt tip. **Prefer an additive record to a history
rewrite**; the register entry that replaced it needed neither.

---

## 6. Open, and the exact next step for each

| # | open item | owner | exact next step |
|---|---|---|---|
| 1 | `sql/sairnlaw_citator_schema.sql` is run, but the verification is not | **Michael** | supply `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, then §4's two commands. `--write` has never run |
| 2 | Tier A `2026-09-27T03:42:29Z` sha is dangling | **hank** | in `Documents\SAIRN-hank`: `python tools/tier_a_review_gate.py --reseat-shas --write --only 2026-09-27T03:42:29Z`. It cannot be done from any other clone |
| 3 | Tier A `2026-10-12T01:51:33Z` reviewed, not discharged | **cc** | paste the verdict from `SAIRN-report-cody-b7.txt` §3 into `--discharge hank 2026-10-12T01:51:33Z --body-file <path>`. **Narrow it or review the client-side half first** — I did not drive a browser and that half is UNREVIEWED |
| 4 | Tier A obligation for my own b7 tests | **hank** (assigned, LIVE) | `bld_draws, sf_disbursements, sf_gaming_expenses, sf_ledger, sf_officers`. What to check: that no expectation in either suite is transcribed rather than derived |
| 5 | the 19 seam pairs | **cc** | `docs/2026-10-13-cody-b7-seam-pair-owners.md` §4 — a FORWARDS-ALL classification in `tools/sairn_seam_check.py`, with a control pair, a before/after count and an ablation. **An exemption entry is refused as the remedy** |
| 6 | 4 WEAKENING flags resolved by their own author | **any session but cody** | `docs/scrutiny-flags.json`, under `c465743b`, `db2a47f1`, `24e88957`, `4ff63a51`. Each carries a one-command reproduction; none is signed off |
| 7 | ten of hank's thirteen bare-run write findings | **cc** | `docs/2026-10-13-hank-b6-routing.md` item 1. Three are now guarded. **If you adopt the guard, put the block BELOW the module docstring and alias `os`** — above it, two of three raised `NameError` and one silently emptied `__doc__` |
| 8 | `cody 2026-09-28T03:34:57Z` Tier A record has a wrong sha | **cody** | `REFUSED [SHA_WRONG_WHEN_WRITTEN]`. Fix the RECORD's file list, not the sha |
| 9 | `defect_register.py --check` exits 1 | **hank** | `f9a4e5a0032b` — "neither the commit nor its subject is in this repo". An unpushed sha from another clone. Pre-existing, arrived by merge, not mine |
| 10 | `scrutiny_ledger_check.py` exits 1, 12 CONTRADICTED rows | **cc** | pre-existing at `72ca3ad1` AND on `origin/main`, verified by parsing both — **not caused by b7**. 2 are keyed to `f8fade035082` with empty diffs |
| 11 | `api/sf-auth.test.js` trustee question | **Michael** | `docs/2026-10-13-hank-b6-routing.md` §8. Untouched: it needs a role-vocabulary decision, not code |
| 12 | the sairnbuild Draw Requests panel is not role-gated client-side | unassigned | a `pm` now sees a 403 rather than a hidden tab. Server refusal is correct and shipped; the panel half is a client change nobody has been asked for |

---

## 7. Cleanup

**Nothing of any other agent's was deleted, and no live data was touched.**

**Restored rather than deleted:** `tools/condition_coverage.py`,
`tools/dead_rule_sweep.py`, `tools/guard_ablation.py` were reverted once (and
later re-arrived; §5.3) and `docs/SAIRN-handoff-hank-b7.md` was taken **verbatim
from `MERGE_HEAD`** rather than merged, so nothing this session did can appear as
an edit to another agent's handoff.

**Moved out of the repo:** `seam_table.md`, a generated scratch table that a
one-off script wrote to the repo root, now in the scratchpad. **It was never
committed** — caught by reading `git status` rather than by remembering.

**Kept on purpose:** the scratchpad evidence directory below. It is the
**EVIDENCE-path the digest points at**, so deleting it would break the only link
between the report's measurements and the runs that produced them. It holds the
suite logs, the three preflight runs, the re-derivation and AST logs for the
`check4` flag, the `c465743b~1` ablation, and the verdict texts.

**Tag left behind on purpose:** `b7-backup-pre-amend` → `b1a0b692`. It is the
pre-amend tip from §5 and is cheap insurance until somebody confirms nothing was
lost. **Delete it once this handoff is read.**

**EVIDENCE-path:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\dcd1868a-9820-4e70-94ba-b9e04667b149\scratchpad\b7\`

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\dcd1868a-9820-4e70-94ba-b9e04667b149.jsonl`

---

*b6's handoff is `docs/handoff-cody-2026-10-13c.md` and is unchanged by this
session.*
