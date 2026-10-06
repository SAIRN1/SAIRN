# Fourth — batch 9 inventory, 2026-10-06

**Fourteen items dispatched. What landed, what did not, and what I got wrong.**
Every exit code below was captured from the run it describes, per convention 15
adopted in this batch.

---

## 0. The three things worth reading if you read nothing else

1. **A whole-tree test run corrupts this clone.**
   `tests/push_gate/check8_probe.py` leaves `.git/config` with
   `core.bare = true`, after which *every* git command fails with
   `fatal: this operation must be run in a work tree`. Observed three times
   today. `tests/seam_check/run_delegation_probe.py` leaves `api/sd-data.js`
   and `api/_lib/subcontractor-compliance.js` carrying planted sabotage, one of
   which does not parse. Both attributed by digesting a watch-list after every
   suite. Neither is fixed and the mechanism of the first is **not pinned**.
   Full account: `docs/2026-10-06-whole-tree-run-and-the-runner-that-corrupts-its-clone.md`.
2. **`tools/suite_override_consistency.py`, which I wrote yesterday, could not
   fire.** Its majority rule is satisfied by no app-file override anywhere in
   the tree, so `findings 0` over 488 suites was the only answer it could give —
   including for the incident it was written for. Rule changed, corpus widened
   from `tests/` to `tests/` + `api/`, and it now reports **155 findings, 0 of
   them under a majority convention**.
3. **Two headline cells in standing status documents were false**, and in both
   cases the correction already existed somewhere else and nobody came back to
   the row. SAIRNroofing A5 cited an EXPIRED CLAIM as its evidence; SAIRNdental
   B2 said `dnt_rollup` had no caller eleven days after `b179d967` gave it one.

---

## 1. Item by item

| # | Item | State | Where |
|---|---|---|---|
| 1 | verify nothing uncommitted or truncated | **done** | `node --check` 0 on every touched file; tree clean apart from one untracked SQL file that is not mine (see §3) |
| 2 | gap doc: exactly one A5 row | **done** | one row at `:68`; the duplicate the screen showed was not in the file |
| 3 | exec-context: the old false clause gone from the JOINED output | **done** | 0 stale hits across all roles; suites 20/20 and 10/10 |
| 4 | report items 6, 9, 10 of the previous batch | **done** | §2 below |
| 5 | commit and push per item | **done** | 14 pushes to `origin/main` |
| 6 | verify every headline in every `docs/` gap doc | **PARTIAL — 5 of 35 docs** | §4, and the coverage is stated rather than rounded up |
| 7 | highest-severity still-open gap, app with no work in flight — build it | **done** | SAIRNlegacy F2, declinability. 31 arms |
| 8 | drive every suite once, register the reds outside the register | **done** | 739 driven, 77 re-driven alone, register 13 → 80 |
| 9 | `tools/red_suite_register_check.py` | **done** | 9 fixtures + 3 controls; registered with an `# OWNER:` line |
| 10 | route the SAIRNbiz suite to cc | **done** | `docs/2026-10-06-fourth-routed-to-cc.md` |
| 11 | verify every other verified statement in exec-context | **done** | two more false clauses found and fixed |
| 12 | a gap doc with no stale headline — build the buildable half | **done** | SAIRNdesign procurement middle. 21 arms |
| 13 | two methodology conventions | **done, plus one of cody's** | conventions 13, 14, 15 |
| 14 | inventory | this file | |

---

## 2. The three previous-batch items whose results were never seen

### Item 6 — the spanOf class

**148 sites locate a function by name; 110 take no span at all.** Of the 38
that do, **24 could be paired mechanically** with their source and compared
against the function's own balanced closing brace:

```
AGREES ............ 9
LONG/SHORT by 1 ... 6   a trailing newline between `}` and the next symbol
artefact .......... 2   my measuring script's cheaper brace walk, not the test
REAL .............. 5   wrong, and wrong in the direction that fails GREEN
```

**The remaining 14 of 38 were not mechanically pairable and are NOT claimed as
checked.** 24 of 38 is the coverage.

The five, with file:line and the measurement:

| site | bound | true span | direction |
|---|---|---|---|
| `tests/sairnlegacy_processions_isolation.js:138` | `+1200` | 923 | positive + LONG → false green |
| `tests/sairnlegacy_processions_isolation.js:159` | `+1400` | 1118 | positive + LONG → false green |
| `tests/sairnvet_scribe_review_probe.js:96` | next symbol | +80 past the close | positive + LONG → false green |
| `tests/sairnvet_formulary_source_honesty.js:521` | `+4000` | 9,895 | **absence** + SHORT → false green, 60% of the function never searched |
| `tests/stonedesk_server_backup.js:260` | `+200` | 96 | positive + LONG → false green |

**Each repoint is proven by a planted control**, not by the suite staying green —
all five were green before and after. `tests/run_fn_span_control.js` plants, per
arm, an input on which the old and new bounds must disagree and asserts both
sides plus the real source:

```
5 proven, 0 NOT PROVEN, 0 failed
```

The first run came back **2 NOT PROVEN** — a `String.replace` that hit only the
first occurrence, and a rename the predicate still matched as a prefix — which
is the control reporting it had not separated the bounds rather than counting
itself as evidence.

**Two are ROUTED, NOT FIXED.** `tests/stonedesk_server_backup.js` is blocked by
hank's claim on stonedesk (edit made, then reverted; the control arm's name says
the hole is still open) and `tests/sairnbiz_vendor_ytd_derivation.js:100` is in
cc's.

### Item 9 — `suite_override_consistency` counts per verdict

**The dispatch's "269 suites" could not be reproduced.** `discover()` reports
**344 JS + 395 PY** suite files today; the JS corpus this tool examines is
**488** because `api/` adds 144. 269 is not quoted anywhere.

Over 488 JS suites, with every flag fixed:

```
FINDING          155     of which 0 under a majority convention
HONOURS           38
NO_CONVENTION     21
CROSS_APP         16     cannot be judged -- NOT judged clean
NO_APP_HTML      258
TOTAL            488
```

Two defects in the tool, both found by making it report a denominator: the
corpus was `tests/` only (excluding 144 `api/**/*.test.js`, which changes family
ratios rather than merely narrowing coverage), and the **majority rule could not
fire anywhere** — `LEG_HTML` 2 of 7, `SD_HTML` 6 of 70, `SB_HTML` 7 of 20,
`DNT_HTML` 5 of 18, `SEN_HTML` 3 of 15. Shared credential vars are no longer
counted as file-substitution conventions. Selftest 9 cases, 0 failed, with a
control proving three fixtures separate the two rules.

### Item 10 — the five RECOVERED suites

Each driven alone. Exit codes, each on its own line:

```
api/sd-data-memory-app-scope.test.js
0
tests/claims/run_freshness_probe.py
0
tests/run_invisible_in_pattern_probe.py
0
tests/run_master_plan_probe.py
0
tests/sairnlaw_hydrate.js
0
```

All five confirmed green. The 2026-10-05 reconciliation holds.

---

## 3. Two things in this clone that are NOT mine and were left alone

* **`sql/restore_demo_pins_2026-09-29.sql`** — untracked, 10KB, mtime
  2026-10-05, a carefully written credential-restore runbook from an earlier
  session. It makes the push gate refuse any command that commits and pushes in
  one step, which is why every push in this batch was two commands. **Not
  committed, not moved, not deleted.** It writes credential rows, so per
  PR §3.4 it needs the recoverability guard checked by whoever owns it.
* **15 leaked git worktrees** in `%TEMP%` from probes killed before their
  cleanup ran. `git worktree prune` removes none, because the directories still
  exist. Removing another session's temp worktree while that session may still
  be using it is not a cleanup.

---

## 4. Item 6, and the coverage is stated rather than rounded up

**35 gap documents exist** (`docs/*gap*.md`, `docs/cloud-research/*gap*.md`,
`docs/superpowers/specs/*competitive*.md`), carrying roughly **204 status
claims**. **I verified 5 documents.** Which five, and what moved:

| doc | verdict |
|---|---|
| `2026-09-02-competitive-gap-status-rederived.md` | **26 rows re-derived** — all 12 roofing, all 14 dental. **2 cells false** (roofing A5, dental B2); 21 roofing + 11 dental identifiers located at HEAD with file:line. SAIRNsenior and StoneDesk sections **NOT checked** — hank's claim |
| `2026-09-17-sairndental-competitive-gap-rederived.md` | **all 14 rows.** 13 hold, 1 moved — the one that was the document's title. Four places corrected |
| `2026-09-15-...-mechanical-and-five-apps.md` | §2.2's claim that two surfaces were fixed: **one was.** The pointer owed since 2026-09-15 is now written. §3.1's headline closed 3 days after it was written |
| `2026-09-17-sairnroofing-competitive-gap-rederived.md` | A5 row + §3 (done in the prior session, verified here) |
| `cloud-research/sairnlegacy-competitive-gap-audit-2026-10-05.md` | F1 **already closed** when Part 2 called it "CONFIRMED AND WORSE"; F2 closed by this batch |
| `cloud-research/sairndesign-competitive-gap-audit-2026-10-05.md` | findings 2 and 3 closed by this batch; finding 1 moved to REFUSED-AND-DISCLOSED |

**30 of 35 documents were not re-verified in this batch and are not claimed as
checked.** Mostly the `cloud-research/*external*` audits, whose claims are
market research rather than code — but each also carries an internal-findings
section that makes checkable claims, and those were not re-derived either.

**The pattern across the five that were checked is worth more than the five:**
every stale headline had a correction that already existed somewhere else — in
another document, in a commit message, in the same file eighty lines down. Not
one needed new research. **The build that closes a row does not edit the row**,
and the 2026-09-25 pass that named that failure is now itself one of the
documents it describes.

---

## 5. What I got wrong, in order

1. **I ran the whole tree without `--pinned`.** `tools/run_all_tests.py`'s own
   header says a detached worktree at a fixed commit is the only way to get a
   stable answer on a branch five clones push to hourly. The tree moved under
   the run and at least one verdict is provably wrong because of it.
2. **I re-counted app files with a rule I invented** — "a sub-page is a root
   `.html` with a hyphen" — got 17+5 where the repo's own explicit list gives
   18+4, and nearly "corrected" a correct line in `exec-context.js`.
3. **I reported a duplicate `'sairnsenior'` in `KNOWN_APP_IDS`.** There is
   none; my count matched strings inside comments — the exact mistake that
   file's suite warns about in a comment saying a first pass did it and was
   "one edit away from fixing a non-bug". PR §1.2, in the hour after reading it.
4. **Three test matchers wrong, all three about string literals rather than
   code**: whitespace-stripping that removed the space inside `' checked'`,
   whitespace-stripping that removed the space inside `<span style=`, and a
   `[^:]*` that cannot cross the colon in `color:var(--muted)`.
5. **The first `legInvoiceFields()` wrote `amount: 0`** for the unpriced line
   its own composer refuses to display — a refusal on screen beside a silent
   zero in the writer. Caught by writing the ablation arm, not by reading.
6. **Two fixtures in `red_suite_register_check --selftest` were wrong** and the
   fixtures were fixed, not the rule.

2 and 3 are why convention 14 is numbered rather than noted. 1 is the one that
cost the most and is the easiest to avoid next time.

---

## 6. Open, owed, and routed

* **66 register entries carry an empty `why`** — driven, never diagnosed. The
  largest single addition the red register has had.
* **14 of 38 span sites unpaired.** Named in the defect record.
* **`tests/push_gate/check8_probe.py` and `tests/seam_check/run_delegation_probe.py`
  are unfixed**, and check8's mechanism is unestablished.
* **30 of 35 gap documents unverified** (§4).
* **283 `tools/*.py` carry no `# OWNER:` line** — 15 of 298 do. Cody routed
  this; re-counted rather than quoted, and the checker
  (`tools/tool_owner_header_check.py`) already exists, so the work is the
  headers.
* **cc's three methodology conventions were NOT RECEIVED** — the document
  naming them is not on `main`. Recorded as missing in `docs/METHODOLOGY.md`
  rather than guessed at.
* **`tools/red_suite_register_check.py` was designed around a 13-entry
  register and the register is now 80.** Its own argument — "thirteen files,
  not 738, so it is cheap enough to run every batch" — is weaker at 80, and
  driving all 80 took longer than a ten-minute ceiling allowed. A `--since` or
  a per-entry staleness filter is the obvious next change and is **not made
  here**.
* **`docs/METHODOLOGY.md` ownership is now contested in description:** cc and
  cody's earlier claims say fourth holds it, cody's latest says hank does. I
  created it; whoever edits it next should settle that rather than inherit it.
