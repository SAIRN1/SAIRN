# CC inventory — batch 8, 2026-10-06

**Resumed after a context reset mid-edit.** The brief was a prior session's own
report, so the first act was to re-derive every item against the file and the git
state rather than continue from it. Two items were in a different condition than
the brief described and one was already done; those are reported as such rather
than fixed as described.

---

## 0. Premise log — what the brief said, and what was true at HEAD

| Item | Premise at HEAD |
|---|---|
| 1 "the +93 scratchpad edit for the wrong-subject check, no confirmation it runs" | **FALSE IN ITS LOCATION.** The scratchpad was **empty** — the work was a `--post` mode in `tools/exit_status_attributable.py`, uncommitted in the working tree. **UNWIRED, and that was the real gap:** `settings.json` named only `--hook`. |
| 2 "the pre-commit +56 edit, untested" | **PREMISE HELD on the test; FALSE on the state.** The fix was already **committed** at `a3f6ae01`; `git status` showed the hook clean. The *test* was genuinely absent. |
| 3 "items 2 and 7 may be local only" | **HELD.** `sairnbiz.html`, `tools/exit_status_attributable.py` and the index row were uncommitted; the *claim* commit `fd8e3682` had pushed. |
| 4a "the seq 464/467 law-auth arm — apply it if absent" | **ALREADY SATISFIED.** No literal `464`/`467` in the file, which is what made it look open. 19/19 green and three mutations prove the coverage. **Nothing applied.** |
| 4b "hank's registry-tail fix — did it land" | **IT LANDED (`ff2671c5`), AND IT IS NOT THE E2 FIX.** Two different fixes were being treated as one. E2 is still red. |
| 5 "write 37/18/2/6/11 into row 82" | **PARTLY DECLINED, with a measurement.** The figure is in the row as one of **four reads with three distinct answers**; it is not presented as current. |
| 6 "spot-check the last 4–5 claims against PR §2.7" | **SIX checked, six held or were correctly measured-then-stale.** |
| — "the exit_status_attributable false positives" (2 known) | **FIVE classes, not two.** Three more were found during the batch. |

---

## 1. Landed, with shas

| What | Sha | Verified by |
|---|---|---|
| `sbVendorPaidUndatedOtherYear()` split + three notes in `rVends` | `3cf3d5ec` | `tests/sairnbiz_undated_payee_notes.js` **11/0**, both ablations driven; 3 JS blocks `node --check` clean |
| …and **live** on the deployed file | `3cf3d5ec` | HTTP 200, 414,693 bytes: the new function and both new notes present ×1, the old function name **absent** |
| `--post` observer + FP3/FP4 fixes, wired `PostToolUse/Bash` | `3cf3d5ec` | `--selftest` **32/0** at the time of that commit; `--post` driven on 6 payload shapes and retroactively against both real instances |
| Register citations re-seated after the amend | `e49b9e37` | `defect_register.py --check`: 444 records, every commit resolves |
| FP5 (a separator inside a quoted argument) | *this batch, below* | `--selftest` **38/0**, plus two arms pinning the **separator half** directly |

---

## 2. The item that matters most: a tool that read the wrong subject, five ways

`tools/exit_status_attributable.py` exists because a status was read off the wrong
subject and a false accusation reached a standing document. **It committed the same
class of error five times, and all five were found by it firing on a command I had
just typed — none by reading it.**

| # | class | why it was wrong | found by |
|---|---|---|---|
| 1 | a tool path inside a quoted body or heredoc | nothing ran it | my own harness, last batch |
| 2 | the tool in the LAST element | its status *is* the command's status | last batch |
| 3 | a tool path as another program's **file operand** | `grep`/`sed` ran; the tool was a file being read | **fired 4× on me while fixing it** |
| 4 | the hook firing on **its own recommended remedy** | the status *was* measured alone | **me, and independently by Fourth** |
| 5 | a `;` or `&#124;` **inside a quoted argument** | not a shell separator at all | **fired on my `sairn_status.py set --task "…; …"`** |

**CLASS 5 WAS NEVER ONLY A SUBJECT-HALF PROBLEM, and that is the finding worth
carrying.** `analyse()` splits the same text, so *every* command carrying a quoted
semicolon — a commit message, a `--task`, a `sed` script — was being decomposed
wrongly by the **attribution** half too, and the wrong decomposition then decided
which element "owns" the status. Separators are now located in the **quote-masked**
text and the slices taken from the **raw** text; `mask_quoted` preserving length
exactly is what makes those offsets interchangeable, a property written for the
subject matcher and now load-bearing twice.

**AND MY FIRST FIX FOR CLASS 4 WAS THE DEFECT IT FIXES.** It accepted a status read
*anywhere* after the tool, which silently blesses:

    tool > /tmp/o 2>&1; tail -3 /tmp/o; echo "exit=$?"     # $? is TAIL'S

Fourth's `docs/2026-10-05-exit-status-attributable-false-positive.md` had already
written the sharper discriminator: **the question is not what sits last on the
line, it is whether anything EXECUTED between the tool and the expansion.** That
is what is implemented. An independent report beat my own fix to the right answer,
which is the argument for the independent-review channel in one line.

### Ablation, per arm, from a clean baseline of 0 wrong

| layer ablated | arms it alone catches |
|---|---|
| A — invocation position | **2** |
| B — the was-it-measured suppression | **6** |
| B tightened to Fourth's rule (vs. my looser first version) | **2**, incl. Fourth's shape 3 |
| C — quote-aware separator splitting | **1** |

22 arms in the ablation set; 38 in the shipped selftest.

---

## 3. The `--post` observer, and its own two defects

It prints the **observed** repository state after a git write — HEAD subject,
ahead/behind, uncommitted count. **It reports state, never a verdict**, because the
failure in all four original instances was substituting a plausible story for a
cheap measurement.

**Retroactively proven against two of the four, driven not argued:** the no-op push
read as a refusal (`ahead=0` straight from `rev-list`), and the commit from a
missing message file (driven for real: exit **128**, HEAD unmoved, and the note
says so).

**Its own fail-open, fixed before wiring.** `if rc_head != 0 or rc_ab != 0: return 0`
is a silent skip — a clone with no comparable `origin/main` makes the observer
vanish, indistinguishable from "nothing worth saying". **PR §1.11, in the file whose
subject is exactly that.**

**Its own stale-input defect, found an hour after wiring.** On the first real push
the note read *"ahead 1 / behind 0"* and the push was refused because origin had
moved **six** commits. The number was right about the **local** `origin/main` ref
and wrong about the remote. **PR §1.10 / discipline 8.** It does not fetch — a
report-only hook must not touch the network — so it now names what it compared
against and how old that is, and past 90 minutes says outright to treat the
behind-count as unknown. `_ref_age()` returns `''` rather than a guess.

---

## 4. `.githooks/pre-commit:70` — both statuses driven separately

The block is lifted out of the hook **by line range** and run twice against a stub
`git`: success-with-no-match → `rc=0`, empty list, silent; read-failure → `rc=1`,
*"could not read the staged file list"*, audit **never reached**. **rc A=0, B=1 —
identical under the old `|| true`.**

**The fixture was wrong first and it looked exactly like the hook being wrong.**
Both cases returned 0 initially: an `awk` terminator anchored with `$` on a line
ending in `)`, so the extraction ran past the grep line into an unrelated `exit 0`;
and a `C:/…` `PATH` spelling, so the stub was never found and the real program ran
in a real repo. Both are now asserted before the cases run, and a failed extraction
says **COULD NOT RUN**, not FAIL.

---

## 5. seq 464/467 — proven by mutation, nothing applied

| mutation applied alone | red arms |
|---|---|
| licence filter dropped, matter filter kept | **3**, incl. *"THE LOOKUP IS LICENCE-SCOPED"* |
| genuinely unscoped — confirms ANY licence's matter | **3** |
| the `+=` refactor | **1 — the canary ONLY** |

**My own probe miscounted first**, reading the suite's `FAILED` summary line as an
arm and reporting 4/4/2. Corrected to 3/3/1. A wrong-subject read inside the batch
whose subject is wrong-subject reads.

---

## 6. E2 — measured two ways, and the blocker has MOVED

**75 registry entries, 5 offenders, the same five** — `assertion_label_shape_check.py`,
`entry_point_scope_check.py`, `parse_zero_third_state_check.py`,
`fact_sheet_regenerates.py`, `verification_owed_report.py`. Confirmed by evaluating
the arm's own expression against the imported `REGISTRY`, **and** by the full probe
where **E2 is the only FAIL**.

**The blocker on re-wiring `seam_cannot_tell_watch.py` and `doc_checker_coverage.py`
is no longer hank.** `tools/report_only_checks.py` is **cody's**, named in cody's
live queue16 claim list. Re-checked fresh, not assumed. Left untouched. That is the
honest resolution of the item, not a fix.

---

## 7. Row 82 — four reads, three answers

| reading | source |
|---|---|
| 40 / 23 / 1 / 6 / 10 | hank's prepared text |
| 37 / 18 / 2 / 6 / 11 | cc, same afternoon |
| 39 / 18 / 3 / 7 / 11 | cc, under an hour later |
| 39 / 18 / 3 / 7 / 11 | cc, this batch |

The row previously said *"drifted FOUR times"* while listing three readings — the
same looseness one level up — so it now states exactly what was observed and that
**the last two agreeing is not evidence it has settled.** A reseat breakdown is a
reading of a live ledger five clones write to, not a property of the tool.

---

## 8. `PR §2.7` spot-check — six claims, each re-run

| claim | verdict |
|---|---|
| the reseat breakdown was 37/18/2/6/11 at HEAD | **was run; now 39/18/3/7/11** — measured then, stale now |
| `+=` reddens only the canary; unscoped reddens three | **HOLDS**, re-driven |
| `SUBJECT_DIRS` literal-backspace fixed, hook fires | **HOLDS** — it fired on me repeatedly |
| manifest not regenerated, 7 drifts | **HOLDS** — 9 now, 7 not mine |
| the comment classifier reads `ln-6 .. ln+3` | **HOLDS** — `tools/fail_open_scan.py:313` |
| E2 still 5 failures, same five | **HOLDS** — two independent measurements |

**Six for six were actually run before being written.** The rule held on its first
batch under test.

---

## 9. Methodology, recorded because it is what produced the findings

1. **Re-derive the brief before executing it.** Three of eight premises were wrong
   about *where* or *whether*, and one item was already done. The brief was my own
   prior report, which is the least trustworthy kind.
2. **Every "could not run" gets its own exit.** Three fixtures in this batch were
   wrong, and in each case the wrongness first presented as the subject being
   wrong. A probe that cannot distinguish its own failure from its subject's
   failure will blame the subject.
3. **Ablate per arm, from zero.** An ablation run from a non-clean baseline measures
   nothing; the script aborts if the baseline has any wrong arm.
4. **Union, then count, on an append-only record.** The `tier-a-reviews.json`
   conflict was resolved as a union and then *proven*: 231 ∪ 231 = 232, nothing lost
   and nothing invented, checked by record identity rather than by line count.
5. **Live-verify the specific string, not the push.** HTTP 200 and five string
   checks, with the removed name asserted **absent** — a present-only check cannot
   tell a successful rename from a duplicated function.

---

## 10. Declared, not fixed

* **`hook_integrity_check.py`: 9 drifts, 2 mine.** The check was **already red at
  HEAD before I touched anything.** The other seven belong to at least four
  sessions, two of them in live-claimed files (`register_feed_gate.py` hank,
  `report_only_checks.py` cody). `--regenerate` is all-or-nothing, so closing my two
  gaps would bless four other sessions' unrecorded changes.
* **`index_duplicate_check`: 3 undeclared near-duplicate pairs** (lines 88/89,
  199/201, 239/243). All pre-existing; none is the row I edited.
* **A sixth false positive, in a different hook.** `sairn_push_gate_hook.py` matches
  the two-word git write verbs **in the command text**, so writing this batch's
  work-log entry through a shell heredoc was refused twice as if it were a push.
  Fourth's document records the same shape in `deploy_verify_notify.py` as its
  instance 3. **Not mine and not in my claim** — recorded because it is now two
  hooks with one defect, and the workaround (write the body to a file, append with a
  tool) is worth knowing before somebody loses an hour.
* **`tools/sairn_rebase_resolve.py` exists for the ledger conflict I resolved by
  hand.** The result was verified to match union-by-identity, but using the tool
  would have been cheaper and I did not look for it first.

---

## 11. Blind spots — 6

1. **The `--post` observer has no probe under `tests/`.** Its arms live in the
   tool's own selftest, which is the shape I have criticised in others.
2. It reads `origin/main` **by name**; a clone on a differently-named upstream gets
   the could-not-read branch every time and that is unmeasured in the other clones.
3. The invocation-position rule knows **seven** interpreter names and will miss an
   eighth silently — a false negative, chosen deliberately, unmeasured.
4. **No measurement exists of the notice's own precision over a session.** All five
   classes were found by it firing on a command I had just written, which is
   anecdote, not a rate. Recorded as an owed action on the register record.
5. E2's five offenders are named but the import-time refusal is in a file I do not
   hold, so the **intake** defect is open and will recur on the next promotion.
6. Every mutation proof here ran against a worktree at a specific base; a fifth
   reseat reading will exist before anybody reads this.
