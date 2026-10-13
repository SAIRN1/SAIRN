# HANDOFF — fourth / ted, batch b7, 2026-10-13

**Written BEFORE the report and the digest**, at a point where nothing is
half-finished.

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\26107814-6275-4923-8a05-52f5d7ac19bd\scratchpad\`
Logs named in each item below. Derivations are scripts, not prose:
`phi_binary.py` + `bisect/round-00.log`, `group_b.py`, `swap2.py`,
`b6_suites.py` + `g4a_*.log` / `g4b_*.log`, `item6_supersede.py`,
`item7_skilldiff.py`, `item9_locks.py`, `resolve_bypass.py`, `counts7.py`.

---

## 0. THE THREE THINGS THE NEXT SESSION MUST NOT "FIX"

1. **HOOKS AND THE COMPACTION KEYS ARE OFF ON PURPOSE.**
   `.claude/settings.json` carries `"hooks": {}` and is **uncommitted by
   design**. b4 restored them not knowing; b5 reversed that on instruction; b6
   and b7 re-added nothing. Do not commit it, do not restore it.
2. **`sql/restore_demo_pins_2026-09-29.sql`** — still carried, untracked, not
   mine, eleventh batch. Three untracked `settings.json` backups likewise.
3. **`refs/salvage/b6-*`** — two refs pinning commits whose worktrees are gone.
   **Delete them only once a push lands**; the exact commands are in routing doc
   §14.

Nothing in `C:\Users\marsh\` was deleted.

---

## 1. COMMITTED / PUSHED STATE

| | |
|---|---|
| HEAD | `3abb71ed` |
| position | **17 ahead, 16 behind.** The rebase landed; others have pushed since |
| push attempts | **ONE**, as instructed. **REFUSED.** No override, no `SAIRN_SEED_GATE=off` |
| what refused it | `docs/TOOLING-INVENTORY.md` — the generator exits 2 because the hook table is empty, which is item 0 above |
| what did NOT refuse it | the **external-files gate was CLEAR at push time**: `UNINDEXED 0`, exit 0. That was the gate item 2 made the push conditional on |
| commits this batch | 7 |
| diff stat of the work commit | `19 files changed, 535 insertions(+), 41 deletions(-)` |

**Re-derive:**

```
git log --oneline -8
git rev-list --left-right --count origin/main...HEAD
python tools/external_file_index_check.py
```

### The rebase: ONE conflict, and it was in a file that is not mine

`docs/BYPASS-LOG.jsonl` conflicted — 7 rows from origin/main (all hank's)
against 1 row of mine. **Reported as instructed, and resolved by UNION rather
than by a choice**, because that file is an append-only audit log: a conflict in
it is never a disagreement about content, it is two sessions appending at the
same place. Ordered by each row's own `at` field; the script refuses unless the
output row count equals ours + theirs, and every row was re-parsed as JSON. 77
+ 7 + 1 = 85 rows, by session: cody 13, fourth 47, hank 11, cc 14.

**No other file conflicted**, and my b6 work survived the replay (verified by
counting `stripJs` call sites in two of the files it touched).

### The external-files gate has moved again since the push

At push time: **0 unindexed**. Now: **3**, none of them mine —
`handoff-hank-2026-10-12.md`, `handoff-h2-2026-10-12d.md`,
`SAIRN-handoff-h1-b13.md`. The queue refills as fast as it drains because every
session is ordered to upload a handoff to a declared non-transient directory.
Routed since b5; still open.

---

## 2. ITEM BY ITEM, with the exact next step for each open one

| # | item | state | exact next step |
|---|---|---|---|
| 1 | sync and rebase | **DONE** | one conflict, union-resolved, reported above |
| 2 | one push attempt | **REFUSED, not overridden** | the blocker is the hooks-off generator; nothing to do here without a decision on item 0 |
| 3 | binary-bisect the phi_cache polluter | **RULED OUT AT CLASS LEVEL** | nothing. The diagnostic now names the subject if it recurs |
| 4 | the remaining 29 stripper sites | **27 DONE, 2 DECLINED with reasons** | 3 sites remain in 3 files, one of them NEW from another session — routing doc §10 and below |
| 5 | temporary-state leak check | **DONE, report only** | promote it to a hook only if a leak class turns out to be chronic |
| 6 | the 4 unresolvable register hashes | **DONE** | checker exits 0 with `SUPERSEDED (4)` |
| 7 | hover-auditor skill divergence | **DONE, printed and routed** | cc's; nothing edited in either store |
| 8 | `refs/salvage/b6-*` | **LISTED, KEPT** | delete after a push lands; commands in routing doc §14 |
| 9 | lock table | **DONE — 0 released** | `fourth.lock` released at report close |
| 10 | b7 claim | **DONE, and it IS visible** | see below |
| 11 | `report_sha_check` on the b7 report | **DONE at report close** | — |
| 12 | this handoff | **DONE** | — |
| 13 | report + digest + uploads | after this file | — |

### Item 10 — the claim is visible, and that is now measured rather than assumed

The b7 claim was taken by FILES (24 of them) and committed locally; the push is
refused, so it is **not** on origin/main. It **is** mirrored into
`~/SAIRN-SESSION-LOCKS/status/fourth.json` and therefore visible to the five
other sessions on this machine without a fetch — 1 claim, 24 files, confirmed by
reading the row back. b6 established the mechanism and routed the misleading
message to cc (`tools/sairn_claim.py:1966`, `:1921`, `:2414`); that routing
stands.

**The b6 claim was still active at b7 pickup and was released first**, so the
record says one thing. Same shape as b6 found at its own pickup: a claim is not
released by a batch ending.

### Item 4 — what is left, and why the three are not a shortfall

| file | site | why it is NOT consolidated |
|---|---|---|
| `api/sairnvet-transcribe.test.js` | :152 | the regex is quoted **inside a comment** describing a previous version. The file already uses a scanner. An inventory false positive |
| `api/alf-append-only-read-order.test.js` | :192 | strips a trailing comment from **SQL** statement lines. `stripJs` is the wrong language |
| `api/auth-setup-attribution.test.js` | 1 site | **NEW since the b5 inventory**, another session's file, not part of the 29 |

27 consolidated: 4 in group A (api/), 23 in group B (tests/). **Every function
chosen from its SUBJECT**: HTML → `stripComments`, bare JS or a slice taken from
inside a script → `stripJs`. Four slices bounded by two function declarations
take `stripJs` *because* `stripComments` would believe a slice starting inside a
script is outside one.

**Every suite driven before and after; all 17 identical both times.** One is
worth flagging: **`tests/faults/sd_write_faults.js` was ALREADY RED at
baseline** — exit 1, 7 passed / 11 FAILED — and is red after with the same
counts. Pre-existing, unchanged by the swap, and **not in
`docs/known-red-suites.json`**, which makes it an unregistered red suite.

---

## 3. ITEM 3 — THE CLASS IS RULED OUT, WHICH IS MORE THAN A NARROWED RANGE

b6 eliminated 8 candidates one at a time. b7 was told to binary-bisect instead.
**It terminated in ONE run rather than log2(95)≈7, because the root predicate is
false.** All 95 candidates — every suite that names one of phi_cache's seven
subjects AND contains a write primitive — were driven in order, then phi_cache:

* subjects moved: **none** (0 `MOVED` lines in `bisect/round-00.log`)
* `core.bare` after: false
* phi_cache after: **exit 0, 72 passed, 0 failed**

**So the polluter is not a suite that writes a subject.** There is nothing to
halve, and saying so is the result.

**THE NEXT OCCURRENCE NAMES ITSELF.** A diagnostic now runs at the END of
`tests/phi_cache_scoped_to_user.js`, on the failure path only: it re-reads all
seven subjects and prints which differ from HEAD, or states that all seven are
clean so the failure is **not** tree pollution. **It does not change the exit
code** — a diagnostic that downgraded a failure to a skip would be the same
silence one level along.

---

## 4. ITEM 5 — AND THE KNOWN LIVE CASE IS NO LONGER LIVE

`tools/temp_state_leak_check.py`, report only, wired to nothing. Four facts
across a probe: `core.bare`, `user.name`, `user.email` (with a probe-identity
test) and worktree registrations. **Control pair: 14 arms, 0 failed, both
directions** — four planted leaks fired, every clean arm silent, restoring each
value cleared it, and a missing snapshot or unreadable worktree list is COULD
NOT RUN rather than a pass. Controls run in a throwaway repo.

**THE NAMED CASE DID NOT REPRODUCE.** `tests/push_gate/check8_probe.py:209`
records in its own comment that a dry-run push "was reliably leaving
`core.bare = true` behind". Driven at this HEAD on a quiet tree:
**exit 0, NO LEAK — all four facts unchanged.** `check4_probe.py` likewise:
the probe itself exits 1, and the leak check reports **NO LEAK**. So either that
path has been fixed since the comment was written or it does not run here. **The
check is built and proven by its controls; the live instance it was pointed at
is gone.**

**One earlier run of this check was contaminated** by my own background bisect
and named a worktree the bisect had removed. Recorded rather than quietly
re-run: a two-point-in-time comparison cannot tell a concurrent sweep from its
subject, and that is a limit of the method.

**No edits were made to cody's files.** `check8_probe.py` is named, not touched.

---

## 5. CLAIMS AND EXTERNAL HOLDS

| hold | count | detail |
|---|---:|---|
| worktrees besides the main one | **0** | |
| `git stash` | **0** | |
| session locks held by me | **1** | `fourth.lock`, pid 61696 — **released at report close** |
| session locks released by me | **0** | none of the 8 dead ones is attributable to me |
| repo claims held | **1** | the b7 claim, 24 files, local + mirrored to the registry |
| repo claims released | **1** | the b6 claim, still active at pickup |
| refs created by me, still live | **2** | `refs/salvage/b6-*`, kept per item 8 |

`fourth.lock` **was recreated after b6 released it** — `sairn_claim.py` takes the
lock on its own start path, so a release at report close does not survive the
next batch's first claim. Worth knowing before reading a lock table as drift.

---

## 6. WHAT IS OPEN, AND WHY

* **3 stripper sites in 3 files** — two declined with reasons above, one new
  from another session.
* **`tests/faults/sd_write_faults.js` is red and unregistered.** 7 passed, 11
  failed at baseline, pre-existing. Not mine to diagnose; it needs a register
  entry or a fix.
* **The phi_cache polluter** — class ruled out; the suite now self-reports.
* **The hover-auditor divergence** — +362/-12, one-way, routed to cc.
* **`tests/seam_check/run_delegation_probe.py:76, :80, :113, :119`** — the
  fail-open restore. cody's.
* **`tools/session_lock_check.py:128, :349, :357`** — why 8 dead locks are
  unattributable. Fourth batch. cc's.
* **`tools/clone_health_check.py:209-211`** — detects `core.bare=true`, nothing
  refuses on it. cc's.
* **`tools/sairn_claim.py:1966, :1921, :2414`** — the "nothing published"
  message that is wrong on this machine. cc's.
* **The two upstream defects behind the `not_red` five** — two sabotage controls
  blocked on registered-red baselines, one failing blind lock blocking two
  push-gate probes.
* **17 unpushed commits, 16 behind.** Nothing from b5, b6 or b7 is on
  origin/main.
* **The external-files queue** — 3 unindexed handoffs, none mine, refilled by
  compliance.

**Nothing is partial except item 4, and its remainder is three named sites with
a reason each.**
