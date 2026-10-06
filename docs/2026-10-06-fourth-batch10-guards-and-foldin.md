# Batch 10 — structural guards on this batch's work, and the H1/H2 fold-in

**2026-10-06 (Fourth).** Items 8 and 10 of the dispatch, in one place because
the second is a checklist against the first's output.

---

## Item 8 — H1/H2 findings touching my queue, re-derived at HEAD

The hover auditors keep their log in `Documents\SAIRN-hover`, which a build
agent must not reach into. Their findings arrive through
`docs/SAIRN-OPEN-WORK-INDEX.md`, which is where these were read.

| finding | state at HEAD, measured | what I did |
|---|---|---|
| **`FOURTH-ROUTED-F1`** — the 200-byte window over a 96-byte `sdHydrateStore`, routed by me in batch 9 | **APPLIED by hank.** `tests/stonedesk_server_backup.js` now bounds the seam at the balanced close and checks `function sdHydrateStore(` occurs exactly once | Removed from my span sweep's "routed, still open" list. It was the one stonedesk site I made and reverted on a claim block; the owner applied it |
| **`FOURTH-ROUTED-F2`** — three SAIRNsenior gap cells resting on "0 hits" that are no longer 0 | **APPLIED by hank**, and better than I routed it: the cell now gives `aggregator` as **18 occurrences across 13 lines** and says why both numbers are there — *"`grep -c` returns 13 and `grep -o \| wc -l` returns 18 for the same file, and a bare number invites the next reader to disagree with it"* | Nothing. Recorded as discharged |
| **`HOVER-H1-905-910`** — *"the CTO statement says there is NO accounting integration of any kind; the CFO statement 51 lines above it says an endpoint and a schema DO exist"* | **ALREADY DISCHARGED, by my own batch-9 fix.** Driven at HEAD: `getExecContext('cto')` contains `NO accounting integration of any kind` → **false**, contains `api/accounting.js` → **true** | **The index row is STALE and hank holds the index.** Routed below rather than edited |
| **`HOVER-H1-936` item 10** — `tooling_inventory_duplicate_row`, routed to me by name | **REFUTED by hank with a measurement**, before I reached it: 55 tools appear twice in that document and it is the design — two sections, one about WIRING and one about KIND | Nothing. The refutation is right and the row says so |

**One row is owed to hank:** `HOVER-H1-905-910` can be closed. The exec-context
CTO statement was corrected on 2026-10-06 and the contradiction the finding
names does not exist at HEAD.

---

## Item 10 — the four structural guards, applied to this batch's own work

### 1. Never reuse a retired flag name

Two flags are new this batch: `--check-residue` and `--restore-config`.

```
grep -rn -- "--check-residue|--restore-config" --include=*.py --include=*.js --include=*.md .
git log --oneline -S"--check-residue" --all
git log --oneline -S"--restore-config" --all
```

Both names appear **only** in the two files that introduce them (plus the
documents describing them, and cody's queue-19 note which quotes
`--check-residue` back). `git log -S` on each name returns only commits from
**today**, so neither has a prior life and neither is a retired name coming
back. **Clean.**

### 2. Delete dead code behind a retired flag before reuse

**Not triggered.** No flag was retired this batch, so there is no dead branch
to delete. Recorded as not-triggered rather than silently skipped — an unmet
guard and an unchecked one look identical in a report that omits both.

### 3. Required-artifact checklist, per change

| change | tests | rollback | docs | config |
|---|---|---|---|---|
| `run_delegation_probe.py` residue guard | `run_delegation_residue_control.py`, 10 arms + ablation; ARM 4 inside the probe | `git revert`; the guard adds no state outside `.git/seam-delegation-probe.planting`, which `--check-residue` removes | header block + `recurring-bug-classes.md` rows 1 and 5 | none |
| `run_delegation_probe.py` baseline anchor | the probe itself, EXIT 0 where it was 1 | `git revert` | header block + register `why` | none |
| `check8_probe.py` config containment | the probe's own new arm; `--check-residue` and `--restore-config` both driven, both directions | `git revert`; `.git/config.check8-probe-backup` is removed on every ordinary exit | header block + andon log pull 2 | **touches `.git/config` by design** — snapshotted and restored, never edited |
| `sd-data-scp-session-gate.test.js:269` span repoint | arm 6 of `run_fn_span_control.js`, planted both directions | `git revert` | in-file comment with the measurement | none |
| 15 register diagnoses | `known_red_check --fixtures` 6/6, `red_suite_register_check --selftest` 9/9 | `git revert` | the `why` fields are the documentation | none |
| convention 16 | n/a — prose | `git revert` | it is the doc | none |
| `recurring-bug-classes.md`, andon log | n/a — prose | `git revert` | they are the docs | none |

**One row has a real config entry and it is the honest one:** the check8
containment WRITES `.git/config`, because putting it back is the whole point.
It is listed rather than left to be discovered.

### 4. No silent warnings — a real alert, or deleted

| warning | verdict |
|---|---|
| check8's config arm | **REAL ALERT.** It FAILS the suite, names the step the drift happened in, and prints the repair command. It is not a NOTICE line |
| `run_delegation_probe` ARM 4 | **REAL ALERT.** Fails, names every dirty file, prints `git checkout -- <files>` |
| `--check-residue` on a clean tree | prints one line and **exits 0** — not a warning at all, which is correct: it is a question with a negative answer |
| the 50 remaining empty-`why` register entries | **NOT a silent warning.** `tools/red_suite_register_check.py` exits non-zero on any registered suite that passes, so a stale entry is loud. The empty `why` is a stated backlog with a count on it |

**Nothing was left as a print-and-continue.** The one thing that could have
become one — `--check-residue` quietly deleting the sentinel it reported —
was caught by its own control on the first run and is now arm 3d.
