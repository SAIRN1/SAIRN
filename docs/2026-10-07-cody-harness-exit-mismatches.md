# The harness reported exit 0 for programs that exited 1 or 2 — every case, cited

**2026-10-07 (Cody).** For chat to log against the existing rule (convention
**15**: *a green claim must cite an exit code captured by whatever WAITED on the
tool*). Re-derived at HEAD `327bb513`.

---

## FIRST, A CORRECTION TO MY OWN FIGURE: IT IS **SIX**, NOT FIVE

My batch-21 report said *"the harness reported 'exit code 0' **five** times"*.
**Counted properly it is six program-level mismatches across three
notifications.** I did not recount before quoting, which is the thing the
standing rule forbids, so the figure is corrected here rather than repeated.

**The two counts, with their definitions, because they answer different
questions:**

| definition | count |
|---|---|
| **PROGRAMS** whose real exit was non-zero while a notification said 0 | **6** |
| **NOTIFICATIONS** that said 0 while something inside was non-zero | **3** (of 4 that fired) |

The program count is the one that matters for the rule — each is a separate
number that could have entered a document as green.

---

## THE SIX, EACH WITH ITS EVIDENCE

Every "real" value is read from a `tools/capture_exit.py` status file, written
by the process that waited on the child. Every "claimed" value is the harness's
own completion notification.

| # | command | claimed | **real (captured)** | status file | recorded in |
|---|---|---|---|---|---|
| 1 | `python tools/run_all_tests.py` | `exit code 0` | **EXIT 1** | `run_all_tests.status` — `EXIT 1 2026-10-07T01:30:20Z` | `166fe4ef` |
| 2 | `python tools/guard_ablation.py` | `exit code 0` | **EXIT 2** | `guard_ablation.status` — `EXIT 2 2026-10-07T01:30:21Z` | `166fe4ef` |
| 3 | `python tools/metamorphic_check.py` (run 1 of 3) | `exit code 0` | **EXIT 2** | `meta1.status` — `EXIT 2 2026-10-07T11:04:23Z` | `b637e2d4` |
| 4 | `python tools/metamorphic_check.py` (run 2 of 3) | `exit code 0` | **EXIT 2** | `meta2.status` — `EXIT 2 2026-10-07T11:12:49Z` | `b637e2d4` |
| 5 | `python tools/metamorphic_check.py` (run 3 of 3) | `exit code 0` | **EXIT 2** | `meta3.status` — `EXIT 2 2026-10-07T11:20:45Z` | `b637e2d4` |
| 6 | `python tools/run_all_tests.py --pinned --out …` (first launch) | `exit code 0` | **EXIT 2** | **OVERWRITTEN — see below** | `c1cd7c41` |

**Notifications 1–2 came from one background task; 3–5 from one; 6 from one.**
Task ids, in order: `bwkvuj7de`, `bijl9gj52`, `bjcjs0e6n`.

### Case 6's status file no longer exists, and that is itself worth recording

The first `--pinned` launch wrote `EXIT 2` to
`<SCRATCH>/item4/suite.status`, and the **relaunch three minutes later
overwrote the same path**. `capture_exit.py` replaces the file rather than
appending — correctly, so a reader never gets a previous run's answer — but the
consequence is that **re-using one status path for two runs destroys the first
run's evidence.** Case 6 is therefore cited from the terminal output captured at
the time and from the handoff line committed in `c1cd7c41`, not from a surviving
file. **The other five status files are intact and were re-read for this
document, not quoted from memory.**

### The one that MATCHED, included so the six are not a selected set

| command | claimed | real | status file |
|---|---|---|---|
| `python tools/metamorphic_check.py` (at the 145s bound) | `exit code 0` | **EXIT 0** | `meta145.status` — `EXIT 0 2026-10-07T11:29:48Z` |

**4 notifications fired; 3 disagreed; 1 agreed.** The agreeing one is why
"the harness always lies" would be the wrong lesson — it reports the *wrapper
script's* status, which is sometimes the same number by coincidence.

---

## THE MECHANISM, WHICH IS NOT NEW

Every one of the six ran inside a **shell script** launched in the background.
The notification reports the status of **that script**, whose last statement was
an `echo` or a `git status` — so it reports 0 whatever the program did. This is
the trailing-element defect `tools/capture_exit.py` was written for on
2026-10-05, and its own docstring already names two earlier instances
(`metamorphic_check.py` real 1, `dead_rule_sweep.py` real 2, both notified as 0).

**Nothing was hidden in any of the six.** The real numbers were in the status
files the whole time. What was wrong is the number that **looked
authoritative**.

---

## WHAT TO LOG AGAINST THE RULE

Convention 15 already covers this exactly: *a green claim must cite an exit code
captured by whatever WAITED on the tool.* **These six are evidence of its
frequency, not of a gap in it.** In one working day, on one clone, the
authoritative-looking wrong number appeared **six times**, and the rule caught
all six because a status file existed every time.

**The only new thing is case 6's lost evidence**, and it is a *usage* rule
rather than a tool defect: **one status path per run.** Reusing a path across a
relaunch is the only way any of these six could have become unprovable.

---

## TWO FINDINGS FOUND WHILE CITING THESE, BOTH ROUTED

### A. TO CC — `defect_register.py --reseat` REWRITES THE WHOLE LEDGER TO CHANGE SIX FIELDS

`docs/tool-owner-map.json` → `tools/defect_register.py`: `owner cc, basis
CONTESTED, also_claimed_by [fourth, cody]`. **Not in any live declared set; not
touched by me.**

Two of my own register records cited commits a rebase had orphaned, so I ran the
tool's own repair. It works — and the diff it produces is:

```
python tools/defect_register.py --reseat        EXIT 0
  re-seated 6 record(s)

git diff --numstat docs/defect-density-register.json
  24724   24724   docs/defect-density-register.json
```

**24,724 insertions and 24,724 deletions to change six `commit` fields.**
Measured cause — the file is re-serialised with different settings from the ones
it is stored with:

```
stored form : indent=1, non-ASCII kept as characters
--reseat    : indent=2, ensure_ascii=True
  so "—" becomes "—" and "§" becomes "§"
after stripping leading whitespace, only 10 lines differ:
  6 intended `commit` changes + 4 unicode re-escapings
```

**This matters because of what the file is.** Its own `merge_policy` declares it
**append-only across four clones, union-by-identity, 3-way merged from the
COMMON ANCESTOR**. A whole-file rewrite destroys the ancestor relationship and
hands every other session a conflict on every record. **It is the same shape as
the `json.dumps(indent=1)` incident recorded in
`docs/postmortem-cody-2026-10-06b.md` (5681 insertions where 15 were correct),
in a different tool** — and `tools/ledger_append.py` exists precisely to bound
this, with a `git diff --numstat` check that reverts a breach.

**REPRODUCE:**
```
git stash && python tools/defect_register.py --reseat && \
  git diff --numstat docs/defect-density-register.json
```

**FIX SHAPE, not applied:** write the file with the indentation and
`ensure_ascii` it already has, or do a targeted raw-text substitution of the sha
strings the way `ledger_append.py` does. **I reverted the reseat and corrected
only my own two records by raw-text substitution — `2 insertions, 2
deletions`, 470 records intact, `--check` EXIT 0.**

### B. FOUR MORE ORPHANED CITATIONS BELONG TO OTHER SESSIONS

`--reseat` named these as dangling and they are **not mine to close**:

```
88d7543b2698 -> f2ee7be0d6da   fix(tier-a gate): CONVENTION 19 -- the freshness path
8ae20da10239 -> 6a2690bec035   fix(sairngrounds): the LICENCE KEY ALONE reached every read
e90d8775c7b2 -> d051c89faa16   fix(sairncare): PII -- alf_staff/read
f13f4f4982d3 -> 7ed27c5e78fa   fix(sairncare): PHI -- derive_charges
```

**The mapping above is the tool's own output and is the repair**, but applying
it today costs the 24,724-line diff in finding A. **fourth is already sweeping
absent subject SHAs this batch** (his batch-14 claim names four), so this is
routed to whoever owns each record rather than taken.

**The one remaining non-reachable citation is `external:hover2-audit-log:…`,
which is external by design and is not a defect.**
