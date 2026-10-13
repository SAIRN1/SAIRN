# Handoff — cody, batch b7, 2026-10-13

**ALL SIX ITEMS DONE. ON `origin/main` at `7c54590f`, 0 ahead / 0 behind, tree
clean.** Nothing below is half-finished; every open thing is open because it
belongs to somebody else or because a tool refused and the refusal is recorded.

---

## 1. Committed and pushed

| | |
|---|---|
| HEAD / origin/main | `7c54590f` — identical, `0 0` |
| b7 commits, each tested as an ancestor of origin/main | `db2a47f1` item 1 · `24e88957` item 3a · `5ee4406b` item 3b · `4ff63a51` items 2+3c+5 · `a339112d` OWNER lines · `3b8f23d3` item 3c correction · `e1801b06` the register record · `b34308fc` + `7c54590f` merges — **9 of 9 ON-ORIGIN** |
| claim | `tests` — **released after this handoff, the report and the digest** |
| settings.json | never committed. No hook restored or re-added. `SAIRN_SEED_GATE` never used |

**The final push is a NO-OP that the gate refuses, and I did not override it.**
Verbatim: *"Blocked: this gate could not tell what is being pushed.
register_feed_gate: stdin is not a terminal and carried NO ref lines."* The
gate's own text names this as case 1 — *"the push was issued from inside a SHELL
SCRIPT, a pipe or any other wrapper … ISSUE THE PUSH DIRECTLY — that is the fix,
and there is nothing wrong with the change."* **Every command in this harness is
wrapped in a shell, so a direct push looks identical to the gate and is refused
too.** The work is already on `origin/main` — proved by `git merge-base
--is-ancestor` per commit, not by the push's exit code. cc holds the
no-ref-lines message as a live item.

---

## 2. Per item

| # | item | state |
|---|---|---|
| 1 | the driven SAIRNfreedom matrix + bld_draws arms | **DONE** — §3 |
| 2 | the three hank-authored Tier A records | **ONE reviewed, ONE unreseatable and routed, ONE not mine** — §4 |
| 3 | `unproven_arm_check` + the check4 WEAKENING flag | **DONE, and the flag is a FALSE POSITIVE I may not sign off** — §5 |
| 4 | git-worktree / `.git/config` isolation | **DONE and ADOPTED in all three tools** — §6 |
| 5 | the 19 seam pairs | **DONE — they are ONE problem, not 19** — §7 |
| 6 | push and confirm | **LANDED** — §1 |

---

## 3. Item 1 — 540 driven cells, and the 180 that cannot be driven

`tests/sf_role_matrix_driven.test.js` — 25 arms, exit 0. Ten roles × **27**
session-gated `sf_` resources × 2 verbs = **540 cells**, expectation from
`SF_ROLE_MATRIX` and observation from the handler, never both from the table.
282 DENY cells each also assert **no row was fetched before the 403**.

**The denominator is printed rather than implied.** 720 cells exist; only 540
can be driven, because **9 of the 36 resources are licence-key-only — no
session, so no role to decide against.** Those nine are NAMED and their 180
cells are reported NOT-DRIVEN, never counted as passes. The control pair runs
**first** and asserts the inverted assertion throws.

`tests/bld_draws_role_arms.test.js` — 10 arms, exit 0. `pm` denied read AND
write with the parsed message and no row fetched; `owner` and `office` reach the
handler, which is what makes the `pm` arms evidence. **Arm 4 was SPLIT after
measuring:** `signSessionToken` refuses to mint a session for an unlisted role,
so the gate's unknown-role branch is unreachable from outside and is proved at
the table and labelled NOT DRIVEN.

---

## 4. Item 2 — and the claim discrepancy, declared rather than buried

**MY CLAIM SAID `docs/tier-a-reviews.json` WAS A DECLARED CONFLICT I WOULD NOT
WRITE, AND IT WAS WRITTEN.** cc and fourth both still declare that path. The
reason is that Michael's brief asked for item 2 directly, and a direct
instruction outranks my own avoidance — but **the claim string still says
report-only, so the record and the reality disagree and this paragraph is the
correction.** It is in my status row too. If it collides with an in-flight edit,
mine is in `4ff63a51` onward and **I will take the rebase.**

| record | state | next step |
|---|---|---|
| `2026-10-06T06:14:34Z` (owner cody) | **RE-SEATED** to `8246d8ba` on a FILE-SET SUBSET basis, stamped `opened_at_sha_reseated` + basis, verified reachable from origin/main **before** review, then **REVIEWED PASS** | none. Not a self-review: hank authored it |
| `2026-09-27T03:42:29Z` (owner fourth) | **CANNOT BE RE-SEATED FROM HERE.** `--reseat-shas` refuses `NO_OBJECT_IN_CLONE`: the sha is not in this clone's object store **and no commit anywhere carries its file set** | **hank** runs `python tools/tier_a_review_gate.py --reseat-shas` in `Documents\SAIRN-hank`, or fetches the object in. An unreachable record is unreviewable, not passing |
| `2026-10-12T01:51:33Z` (owner cc) | already `reseated: true`, status open, **assigned to cc** | **cc** discharges it. Not mine to sign |

What the PASS verdict does **not** discharge, recorded in the verdict itself:
`ALF_FAMILY_READ_ROLES` includes `billing` on a clinical record. The author
inherited that set rather than narrowing it, which was right for that fix.
**"Should billing read a MAR at all" is a SAIRNcare role-vocabulary judgement
and belongs to Michael.**

---

## 5. Item 3 — the checker, and the flag it cannot sign

**`tools/unproven_arm_check.py`**, REPORT-ONLY, registered in
`tools/report_only_checks.py` with its measured count. Probe
`tests/run_unproven_arm_probe.py`: **15 arms, 0 failed, 0 unproven.** Real tree:
399 files, 146 with a summary construct, 1 in scope, **0 findings**.

**ABLATION CORRECTED IT TWICE AND THAT IS THE REASON TO BELIEVE THE ZERO.**
Against the only two real instances — `check4_probe.py` and `check7_probe.py` at
`c465743b~1` — the first version caught **NEITHER**. A2 was gated on a pass/fail
summary line and neither probe has one; both were quarantined as NOT ASSESSED,
which is the right failure direction and still a checker that cannot fire.
**0 of 2 before, 2 of 2 after.** And the probe tripped its own subject: fixtures
held as concatenated literals are still literals, so A2 fired on the probe at
line 127. Fixtures now live in one triple-quoted block — the tool's own
documented escape hatch.

**The check4_probe WEAKENING flag is a FALSE POSITIVE.** All five lines the
detector counted are `print()` calls or a string fragment; **zero are
assertions**. Confirmed by a structurally different method: `ast.parse` gives
assert 2→2, raise 1→1, `sys.exit` 7→7, +110 lines; and the probe's real
mechanism GREW (ARM labels 3→4, conditions 3→5). The only count that fell is
`print()`, 26→24.

**NOT SELF-DISCHARGED.** I wrote `c465743b`, so I may not sign it off — the same
self-review the Tier A gate refuses at write time. The resolution in
`docs/scrutiny-flags.json` carries the measurement and a one-command
reproduction and is **ROUTED TO ANY SESSION OTHER THAN cody.** The flag row is
untouched; a resolution is a review record, not a deletion.

---

## 6. Item 4 — isolation, with the premise corrected

**The premise was half wrong and the correction is pinned by a test.** MEASURED:
`git worktree add` leaves `.git/config` **byte-identical** on this git version;
it creates `.git/worktrees/<name>`. Probe arm 7 asserts that so the original
wording cannot creep back.

**The real damage is also measured.** A bare `python tools/guard_ablation.py
--help` created `.git/worktrees/sairn-abl-8c6o2uub` in this clone and **left it
there** when the run was killed. `git status` never showed it, `git worktree
prune` would not take it while its temp directory survived, and a stale entry
makes the next `add` refuse. Cleaned by hand.

`tools/git_config_isolation.py` snapshots `.git/config` + `.git/worktrees`, runs
the command with `GIT_CONFIG_GLOBAL` / `GIT_CONFIG_NOSYSTEM` hardened, then
compares and **restores** — exit 0 unchanged / 1 changed-and-restored / 2 could
not run / 3 could not start. **ADOPTED:** `condition_coverage.py`,
`dead_rule_sweep.py` and `guard_ablation.py` now call `require_isolation()`
before their `worktree add`.

**OTHER SESSIONS WILL SEE A BEHAVIOUR CHANGE** and it is in my status row: a
bare live run of those three now exits **2 COULD NOT RUN** with the one-command
fix printed. `dead_rule_sweep.py --help` still exits 0 with usage — probe arm 10
exists because four of hank's thirteen bare-run findings fired on `--help`, and
a guard that refuses `--help` is a guard somebody removes.

Probe `tests/run_worktree_isolation_probe.py`: **10 arms, 0 failed, 0
unproven**, including the control that proves arm 2 is not vacuous.

---

## 7. Item 5 — 19 pairs, ONE problem

`docs/2026-10-13-cody-b7-seam-pair-owners.md`, table DERIVED from
`tools/sairn_seam_check.py` output, not retyped from the b6 report. Parsing the
19 rows: **1 distinct callee, 1 symbol, 1 cause** — every one is `roleSet()` in
`api/_lib/auth.js`. So the answer is not 19 owners; it is one owner and a
closing procedure the next batch can reuse. Every row still carries an owner.

---

## 8. Open, with the exact next step

1. **`2026-09-27T03:42:29Z` Tier A record** → **hank**, in hank's clone. §4.
2. **`2026-10-12T01:51:33Z` Tier A record** → **cc** discharges. §4.
3. **The check4 WEAKENING resolution** → any session except cody, re-run the two
   commands in the resolution block. §5.
4. **`billing` reading a MAR** → **Michael**. Role vocabulary, not a code fix.
5. **My four new test files are traced to no requirement.**
   `docs/traceability-matrix.md` now reports 204 untraced, up from 200, and that
   rise is mine. Next step: add a requirement citation to each of the four, or
   accept the gap deliberately.
6. **12 CONTRADICTED rows in `docs/scrutiny-flags.json`** — `f8fade035082` and
   others name a commit whose diff for the path is EMPTY.
   `tools/scrutiny_ledger_check.py` exits 1 on them. **Pre-existing, not mine,
   not touched** → whoever owns the ledger writer.
7. **One register record is external and unverified** (`f9a4e5a0032b`, hank's).
   It was DELETED on my side during a merge and I **restored** it — the
   append-only policy says a union must not drop an ancestor record.
8. **`sairn_claim.py`'s own push still cannot land from a history with a merge
   commit** (carried from b6). Publish claims with an ordinary push.

---

## 9. Cleanup

Removed: my own scratch logs under `C:\Users\marsh\AppData\Local\Temp`
(`b7_*.log`, `b7_factors.json`, `b5_check4.py`, `b5_check7.py`, the `b7abl/`
ablation tree) and the stale `.git/worktrees/sairn-abl-8c6o2uub` entry plus its
temp directory. No other agent's files, no live data, nothing in the repo.

**Kept:** `…/scratchpad/b6/` — still the EVIDENCE-path the b6 digests point at.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\ae793edc-d4b2-4ede-8ebe-300bf5362392.jsonl`

---

*Written before the report, at a point where everything above is committed and
pushed except this file and the report and digest that follow it.*
