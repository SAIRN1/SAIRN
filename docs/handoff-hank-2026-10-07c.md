# Hank handoff — 2026-10-07, batch b1

Written **before** the final report and at a point where nothing is half
finished. Everything below is either landed on `origin/main`, explicitly open
with its next step, or explicitly refused with the refusal recorded.

---

## PUSHED STATE — the only sentence that matters first

**`origin/main` is at `bf174f30`. My seven commits are `6b5d442b..bf174f30`.
`git fetch && git log origin/main..HEAD` → ahead 0, behind 0.**

| sha | what |
|---|---|
| `72d757ef` | the audit `event_type` vs CHECK-constraint checker + its probe |
| `320ddabe` | six tools REFUSE a missing argument — exit 2, not exit 1 |
| `4ec0d5d5` | the last **7 of 15** attribution write paths — **0 of 49 unattributed** |
| `1ae447cf` | the **seventh** argv refusal, `tools/va_rule_currency.py` |
| `947dfda0` | **RETRACTION** — the auditor-namespace crash routing to fourth |
| `661ff87c` | **RULE E**, routed not promoted |
| `bf174f30` | the derived artefacts: 3 register records, the Tier A obligation, 3 generated docs |

**The three defect-register records cite `320ddabe`, `4ec0d5d5` and `1ae447cf`,
and all three are ancestors of `origin/main`** — verified with
`git merge-base --is-ancestor` after the push, not assumed.

**POST-PUSH LIVE VERIFICATION, and its ceiling stated rather than omitted**
(`tools/sairn_http.py`, not bare curl, per PR §3.2):

```
/api/sd-data  POST, no auth   HTTP 401 Unauthorized      <- the endpoint's own refusal
/api/sd-data  GET             HTTP 405 Method Not Allowed
/stonedesk.html               HTTP 200, real body
```

Not a 403 and not `X-Vercel-Mitigated`, so this is the app answering, not a
challenge. **WHAT IS NOT VERIFIED:** the `updatedBy` stamp itself. It only
exists on a row written by an AUTHENTICATED session against a real licence and
a real table. No credential was used and none was manufactured. The suite proves
it on the OUTBOUND REQUEST with a mocked fetch; a live round trip is a different
claim and **has not been made**.

---

## THE PUSH TOOK FOUR GATE REFUSALS AND ALL FOUR WERE RIGHT

Recorded because the ORDER turned out to be the whole problem:

1. **defect register not fed** — three commits closed defects with no record.
2. **three generated documents stale** — exit 1, which means regenerate (exit 2
   would have meant a generator's hand-written half had drifted).
3. **Tier A code changed with no recorded review obligation** — seven resources.
4. twice, **"the outgoing range could not be read"** — a stale local
   `origin/main` ref while other sessions were pushing.

### THE ORDERING RULE THIS PAID FOR, and the next session should not re-learn it

**Anything derived from a SHA, or from the OUTGOING RANGE, must be produced
AFTER the final rebase.** A defect-register record cites the commit it
describes; a Tier A obligation is derived from the outgoing range. Every rebase
rewrites both. The register records were written **three times** before they
were right, and a record whose `commit` field resolves to nothing is exactly the
vacuous row that file exists to prevent — `--check` would have caught it only
after the push.

`scratchpad/land.sh` encodes it as **rebase → derive → commit → push, re-derived
on every cycle** rather than remembered. It landed on cycle 1 once the order was
right.

**And one git fact that cost a cycle:** after `git reset --soft`, the INDEX still
holds the change, so `git checkout -- <path>` restores the worktree *from the
change* and leaves it **staged** — the next rebase then refuses on an unclean
index. Use `git restore --source=HEAD --staged --worktree -- <path>`.

---

## ITEM BY ITEM

### 1–2. State check — DONE
Two commits were already local-only and unpushed at session start; both are now
on `origin/main`. Nothing from the outstanding batch was redone.

### 3. The earlier suite run — ANSWERED, and the answer changed mid-batch

**Three `run_all_tests.py` launches existed:**

| launch | state | output |
|---|---|---|
| Oct 6 18:24 | DEAD | 0 bytes |
| Oct 7 **10:26**, `wt-suite` worktree — *the clean-worktree run* | **DEAD** | **0 bytes** |
| Oct 7 **08:48**, live clone, python PID 81700 | **was ALIVE at 4h05m, FINISHED at 13:05** | 47KB |

**THE "ZERO BYTES" WAS BUFFERING, NOT SILENCE.** `python tools/run_all_tests.py >
file` buffers stdout; an orphaned or killed run therefore leaves a zero-byte file
and loses everything it had already printed. **Use `python -u`.** That is the
root cause of all three zero-byte files and it is one flag.

The 08:48 run finished **EXIT 1 — 752 files (350 JS + 402 PY), 657 ok / 91 FAIL /
4 skipped / 2 not run.** **ITS OWN OUTPUT DISQUALIFIES IT:**

> `THE SUITE DIRTIED THE TREE (3 path(s)) -- a probe did not clean up:`
> `M api/sd-data.js`, `M docs/scrutiny-flags.json`,
> `M tests/sd_data_write_attribution_three_apps.js`
> `Results above may be CASCADE, not real.`

It ran in the LIVE clone while I was editing those exact files. **91 is not a
usable number.** No second run was started while it was alive.

### 3b. A clean-worktree run IS IN FLIGHT, and it is not a result yet

Started only after the 08:48 run had exited, so it is not a second concurrent
run. **Unbuffered, which is the point.**

```
worktree : <scratchpad>/wt-suite2      (detached, was HEAD before the rebase)
command  : python -u tools/run_all_tests.py
output   : <scratchpad>/suite.clean.out        <- FILLS PROGRESSIVELY
```

**At the time of writing: 435 ok, 0 FAIL, still running.** The contrast with 91
FAIL in the dirty clone is the cascade hypothesis holding so far — **but a
partial run is not a result and this is not a clean-suite claim.**

**NEXT STEP:** read `suite.clean.out` to the end. `EXIT=` is appended on the last
line. If it is gone or truncated, re-run with `-u` in a fresh worktree; do not
re-run in the live clone.

### 4. Migration SQL — PRINTED, APPLIED NOWHERE
`docs/2026-10-07-hank-migration-sql-for-michael.md`, committed, unchanged this
batch, reproduced in full in the final report.

**THE DISPATCH'S PREMISE IS STALE AND THIS IS THE CORRECTION: STEP 0 IS *THREE*
ALTERs, NOT TWO.** `sairncode_audit_log` **and** `stonedesk_audit_log` **and
`sairnlaw_audit_log`**. The third hid because its four writers pass no `table:`
argument and fall through `const target = table || DEFAULT_AUDIT_TABLE`
(`api/_lib/audit.js:45`); the first sweep bucketed them as *"target could not be
resolved"* and left them out — a could-not-tell that was really a known answer,
hiding **six of the eleven** rejected values.

**NEXT STEP: Michael runs STEP 0 PRE-FLIGHT, then 0a/0b/0c. They repair code that
is already pushed and currently inert.** The twelve new tables enable code
nobody has written yet.

### 5. CHECK-constraint sweep — DONE. 4 tables, 9 writer→table pairings.
**3 of 3 tables carrying a CHECK reject at least one emitted value. 11 distinct
values, 12 writer-level rejected pairs, 7 files.** `sv_audit_log` has **no CHECK
and no writers** and is reported separately, never counted clean. Full matrix in
the report.

### 6. Attribution — DONE. **UNATTRIBUTED 0 of 49.**
Was 15 of 49. Eight landed earlier; five SAIRNsenior and two SAIRNroofing land
here.

**NOTHING WAS BLOCKED ON THE MIGRATION** — the migration is about AUDIT tables;
all fifteen of these are DATA tables.

**AND ONE OF MY OWN EARLIER REFUSALS WAS WRONG.** Two roofing paths were left
under one shared reason — *"neither sends `data`, so stamping would REPLACE the
stored blob"*. True of ONE. `rf_claims/write` **does** send `data: dataBlob`
(`api/sd-data.js:7772`) and took the ordinary stamp. Only
`rf_schedule/set_status` matched, and took a read-then-merge.

Suite **20 arms, 3 runs, exit 0, 20/0 each**; targeted mutation **16/4, exit 1**;
`api/sd-data.js` restored byte-identical by sha256.

**OPEN, NAMED, NOT DONE:** `rf_schedule.set_status`'s read-then-merge accepts a
narrow lost-update window (a concurrent writer changing `data` between the select
and the PATCH). A **`status_changed_by` column** removes the trade. `created_by`
is NOT reusable — it is `not null` and means who CREATED the day. **That is a
migration and is deliberately outside this batch.**

### 7. Tier A discharge — RE-CHECKED ONCE, STILL BLOCKED, NOTHING DISCHARGED

**23 open · 16 ELIGIBLE for hank · oldest 10.65 days (256 h)**, opened
`2026-09-27T02:06:03Z`, author cody. Eligible by author: cody 6, fourth 5, cc 3,
hover2 2.

```
python tools/sairn_claim.py check platform "tier a review discharge eligible"
exit 1  BLOCKED
  cc    0.1h   shared phrase: "discharge eligible"
  cody  1.5h   shared phrase: "discharge eligible"
```

**THE OWNERSHIP PREMISE EVERYONE WAS CARRYING IS STALE AND HERE IS THE CORRECTED
CHAIN:** fourth held `docs/tier-a-reviews.json`, then **released** it at
`2026-10-07T16:36:02Z` and replaced it with a batch16 claim that does not declare
it. **CC claimed it at 17:24:00Z and is actively discharging.** Three sessions
(cody, fourth and me) each stood down on a claim that was already released.

**NEXT STEP:** nobody re-derives this from a handoff. Re-run the claims check at
HEAD; if cc's claim has closed, the 16 are discharge-eligible most-overdue-first.

### 8. The eight IndexError tools — SEVEN FIXED, ONE ROUTED

The nine crashers were `checkblocks`, `div_balance_check`, `extract_scripts`,
`js_code_only_diff`, `literal_drift_check`, `nav_panel_check`, `gh_push`,
`va_rule_currency` (IndexError) and `hover_separation_ci` (AttributeError — see
item 10).

**`tools/va_rule_currency.py` FIXED, and the reason it had been left is the
reason it had to be taken.** `docs/tool-owner-map.json` says
`"basis": "NONE", "owner": null` — **no owner at all**, not UNKNOWN. A file
nobody owns cannot be routed to anyone, so a routing list was not deferral, it
was declining to decide while looking like deferral.

**Its defect is not the one the other six had.** Two required arguments; given
ONE it did not raise — it matched no rule, **printed nothing and exited 0**.
Silent success on a run that examined no rule. Arm C exists for exactly that
case and arm B cannot reach it.

**`tools/gh_push.py:182` ROUTED TO CC** — owner map: `cc`, basis `LAST_CLAIM`
`812857c0`. `docs/2026-10-07-hank-routed.md` §1 carries the line, the one-line
reproducing command and the exact change. **It matters more than the other
seven: it PUSHES.** Deliberately NOT added to the probe's `SUBJECTS` — an arm for
a file I am not fixing makes the probe red on arrival for its owner.

Probe **23/23, exit 0**; mutation **18/5, exit 1**.

### 9. Re-runs at a longer bound — DONE. **Bound: 600 s, stated.**

21 programs, isolated worktree. **green 3 · findings 6 · could-not-run 9 ·
TIMEOUT at 600 s 3 · crashes 0.**

All seven item-8 tools exit **2** — they refuse without an argument, which is the
point. Of the 14 re-run 90 s timeouts: 3 green, 6 findings, 2 could-not-run,
**3 still TIMEOUT at 600 s** — `dead_rule_sweep.py`, `guard_ablation.py`,
`red_suite_register_check.py`.

`assurance_case.py` came in at **86.8 s** — it was failing a 90 s bound on
variance alone, not on being slow.

**`run_all_tests.py` is the 15th and was NOT driven here** — the dispatch's item 3
says do not start a second, and PID 81700 was alive when this sweep started. It
is covered by item 3b instead.

**NEXT STEP for the three that still time out:** none of them has a measured
runtime, only a lower bound of 600 s. Measure one alone with no other load before
proposing any bound — a bound set from a loaded machine is the mistake
convention 10 names.

### 10. Retraction — DONE. **CHAT HOLDS IT.**
`docs/2026-10-06-hank-routed-to-fourth.md` §9 is marked retracted **in place**;
its text and reproducing command are left intact as evidence.

**The finding stands and was re-derived at HEAD:** `python
tools/hover_separation_ci.py` → exit 1, `AttributeError: module
'hover_separation_audit' has no attribute 'AUDITOR_SCOPE'`, at
`tools/hover_separation_ci.py:97`.

**Why the routing was wrong:** those two files are the **detect** half of the
build/audit boundary, and `CLAUDE.md` says a build agent must not reach into that
machinery. **Fourth is a build agent.** Handing a build agent the repair of the
detector that constrains build agents recreates the exact separation the gate
holds.

**The shape of my mistake:** I reasoned about **tool ownership** (who may edit
this file) when the governing question was **role separation** (who may be
*asked* to). The owner map has no column for the second and an owner lookup that
returns an answer feels like a completed check.

**Nothing in the hover auditor namespace was touched, read for this purpose, or
routed by me. No new agent is named.**

### 11. Methodology — BLOCKED, ROUTED. **`docs/METHODOLOGY.md` NOT TOUCHED.**

The claims tool was run **first**, as instructed, and it refused — so no claim was
taken and none needed releasing:

```
python tools/sairn_claim.py check methodology "docs/METHODOLOGY.md one entry from batch b1"
exit 1  BLOCKED
  cody   1.3h   same file or resource: docs/methodology.md
  fourth 0.8h   same file or resource: docs/methodology.md
```

**And fourth's own item 12 is verbatim this work.** `RULE E` is written into
`docs/2026-10-07-hank-routed.md` §3 for chat to land.

> **RULE E — a refusal is scoped to the case that justified it, and an unscoped
> refusal spreads to cases it does not fit.** Two instances this batch, both
> mine. Convention 7 is its mirror (propagating a proven FIX without
> re-qualifying the target); every existing convention polices what gets DONE and
> nothing polices what gets DECLINED — a decline leaves no diff, no arm and no
> exit code, so there is nothing for a checker to read. Mechanical form: a
> refusal covering more than one item must cite, **per item**, the fact that
> makes the reason true of **that** item.

---

## CLAIMS HELD, AND WHAT I DID NOT TOUCH

**HELD:** `hank` / `platform`, this batch.

**CLAIMS-CHECKED AND REFUSED — not overridden, not reworded:**

| work | blocked by | what I did instead |
|---|---|---|
| Tier A **discharge** | cc 0.1h, cody 1.5h | listed 16 eligible, discharged none |
| `docs/METHODOLOGY.md` entry | cody 1.3h, fourth 0.8h | routed RULE E |

**APPENDED THROUGH A TOOL, NEVER EDITED, AND DECLARED:**

- `docs/defect-density-register.json` — in **cody's** batch24 FILES. Cody's own
  stated discipline is *"I only APPEND through the tool and I do not edit it"*,
  which is what three `--add` calls are. `tools/defect_register.py` is **cc's**
  and was not edited. Claims-check CLEAR.
- `docs/tier-a-reviews.json` — **cc's**, and cc is discharging from it. The gate
  required an obligation to be RECORDED. **Recording is not discharging** — the
  gate refuses any record whose reviewer is its own author, and this one is
  **assigned to cc**.

**LEFT DIRTY ON PURPOSE AND PARKED IN A STASH:** `docs/scrutiny-flags.json`. It
is **cc's** file and the rows in it were written by **cc's own
`scrutiny_flag` tool**, recording my commits. I will not commit a file I do not
own and I will not revert a record another session's tool just wrote.

```
git stash list     # several entries named "cc scrutiny rows (round N)"
```

**NEXT STEP:** cc decides. The rows are correct; only their home is not mine.

---

## OPEN WORK, WITH THE EXACT NEXT STEP PER ITEM

| # | open item | exact next step | owner |
|---|---|---|---|
| 1 | clean-suite run in flight | read `<scratchpad>/suite.clean.out` to the `EXIT=` line; if truncated, re-run `python -u` in a **fresh worktree**, never the live clone | next hank |
| 2 | STEP 0 ALTERs (**three**, not two) | run the PRE-FLIGHT `pg_constraint` query, then 0a / 0b / 0c | Michael |
| 3 | the twelve new audit tables | only after STEP 0; each needs its three code lines and `AUDIT_TABLES` before it records anything | Michael, then a build session |
| 4 | `sv_audit_log` | has **no CHECK and no writers**. Adding it to `AUDIT_TABLES` is one line; whether it should GAIN a CHECK is a judgement about SAIRNvet | chat |
| 5 | `rf_schedule.status_changed_by` | a column migration; removes the lost-update window the read-then-merge accepts | chat → Michael |
| 6 | `tools/gh_push.py:182` | add the `len(sys.argv)` guard, exit 2; then append `'gh_push.py'` to `SUBJECTS` and drop it from `NOT_MINE` | **cc** |
| 7 | `tools/hover_separation_ci.py:97` | decide which comparison the `AUDITOR_SHARED_SCOPE` constant **plus predicate** is meant to make; a blind substitution makes the check pass while dropping what the predicate covers | **chat** |
| 8 | Tier A: 16 eligible, oldest 256 h | re-run the claims check at HEAD; if cc's claim has closed, discharge most-overdue-first | whoever is free |
| 9 | Tier A obligation for THIS batch | assigned to **cc**; or anyone after 48 h with `--takeover` | **cc** |
| 10 | RULE E | land into `docs/METHODOLOGY.md` when it is unclaimed | chat / fourth |
| 11 | 3 tools still TIMEOUT at 600 s | measure ONE alone, unloaded, before proposing any bound | next hank |
| 12 | `docs/scrutiny-flags.json` stashes | cc decides whether to commit them | **cc** |
| 13 | two worktrees | `git worktree remove` `wt9` and `wt-suite2` **after** the suite run finishes and its output is read | next hank |

---

## TRANSCRIPT AND ARTEFACTS

**Session scratchpad (every captured exit code, every `.out`, the landing
script, the mutation backups):**

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a517bec7-3fd2-4475-835c-6432b2acaa34\scratchpad
```

Named files worth keeping:

| file | what |
|---|---|
| `item9.json` / `item9.log` | item 9, every exit code and elapsed time at the 600 s bound |
| `i9.<tool>.out` | each program's full output |
| `suite.clean.out` | the in-flight clean-worktree suite run, unbuffered |
| `full_sweep.py` / `item5.out` | item 5's full CHECK matrix |
| `land.sh`, `repoint.py`, `reg_add.py`, `land.msg.txt` | how the push was landed |
| `live.out` | the post-push live verification |
| `attr.*.out`, `probe.*.out` | the measured runs and mutations |

**Previous session's scratchpad**, which holds the 08:48 suite output
(`f.rat.out`, 47KB) and `tools_sweep.tsv`:

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\16753c01-e018-4c71-af08-342c1baa72e6\scratchpad
```

**Per-item memory checkpoint**, written after every item before the next began:
`~/.claude/projects/C--Users-marsh-Documents-SAIRN-hank/memory/hank-b1-progress.md`

**Backup branches** cut before the two non-fast-forward operations, so nothing in
this batch is unrecoverable: `backup/hank-b1-a721bb25`,
`backup/hank-b1-fb65c5fc`.
