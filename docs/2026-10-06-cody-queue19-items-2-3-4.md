# Queue 19 items 2, 3 and 4 — two tools built and BLOCKED FROM LANDING, and the core.bare cause was already found

**2026-10-06 (Cody).** Design note: `docs/2026-10-06-cody-queue19-design-notes.md`.
**Every figure carries its command; re-run rather than quote.**

---

## FLAGGED BACK — ITEMS 2, 3 AND 7 ARE ALL BLOCKED ON ONE CLAIM

`tools/tooling_inventory.py` and `docs/TOOLING-INVENTORY.md` are in **hank's**
live claim, re-checked at HEAD twice during this batch (1.2h old at the second
reading). Measured, not assumed:

```
git add tools/ledger_append.py tools/clone_health_check.py
python tools/tooling_inventory.py --check      EXIT 2
  2 tool(s) in tools/ with no PURPOSES entry ... this is an error:
      clone_health_check.py
      ledger_append.py
```

**A new tool cannot land without an entry in a file another session holds, and
the generator refuses rather than emitting a blank cell.** That refusal then
freezes every other generated document, which is why this is a hard block and
not an inconvenience.

**BOTH TOOLS ARE LEFT UNTRACKED IN THE WORKING TREE, DELIBERATELY.** Measured:
untracked, all three generators `--check` exit **0** — the tool list comes
from `git ls-files tools/`, so an unadded file is invisible to them. So they
sit where they belong, cost nothing, and the next session finds them in place:

| file | state | selftest |
|---|---|---|
| `tools/ledger_append.py` | **untracked, built, locked** | `--fixtures` **EXIT 0**, 20 arms, 6 negative |
| `tools/clone_health_check.py` | **untracked, built, locked** | `--fixtures` **EXIT 0**, 12 arms, 5 negative |
| `tests/run_blob_coverage_scope_sabotage.py` (item 7) | **held since the previous batch** | EXIT 1, 2 findings |

**NEXT STEP, one action for all three:** when `tools/tooling_inventory.py` is
free, add three `PURPOSES` entries, `git add` the three files, regenerate, and
push in ONE commit so nothing drifts.

---

## ITEM 2 — `tools/ledger_append.py`: both of my serious mistakes, closed

`python tools/ledger_append.py --fixtures` — **EXIT 0 from its capture_exit
status file**, 20 arms, 6 of them negative.

| arm group | what it proves |
|---|---|
| backticks, `$(...)`, embedded quotes, **the `id`-output case** | each body survives **verbatim**, and each is paired with *"and NO `uid=` appears"* — the exact corruption that pasted a local uid into `docs/tier-a-reviews.json` |
| **the 5681-vs-15 case** | a 200-record JSON ledger gains one record and `git diff --numstat` adds no more than the entry plus a printed allowance |
| **NEGATIVE: the bound is load-bearing** | an append whose diff exceeds the bound is REFUSED **and REVERTED**, verified by re-counting the records afterwards. Without this arm the bound check is decoration |
| **NEGATIVE: no flag takes body text** | asserted against the argument parser itself — `--body`, `--text`, `--entry`, `--message`, `-m` do not exist |
| three COULD NOT RUN cases | a missing ledger, a path outside the repo, a missing JSON key — and *"the missing ledger was NOT created"* is its own arm |

**AND ITS OWN REPORTER WAS WRONG ON THE FIRST RUN.** `arm()` printed the
failure detail unconditionally, so a PASSING arm read
``ok  backticks survives verbatim -- needle '`b`' absent`` — **the pass and
the failure message on one line.** That is a clean line indistinguishable from
a finding, in my own harness, caught on its first run. An `int` detail also
raised `TypeError` inside the reporter, which would have taken down the whole
run rather than failing one arm. Both fixed before anything else was read.

---

## ITEM 3 — `tools/clone_health_check.py`, and the live run

`python tools/clone_health_check.py` — **EXIT 0**, commit `7dad8620`,
2026-10-06T17:56:34Z.

```
core.bare     : false
git status    : working   (2 dirty path(s))
claim history : 5 session(s)
worktrees     : 28 registered besides the main one (28 LIVE, 0 ORPHAN)
```

### THE 28, AND NOTHING WAS SWEPT

| name | state | last write (UTC) | age h | claimed by |
|---|---|---|---|---|
| `check4-probe-67292` | LIVE | 2026-09-30T11:56:43Z | 150.0 | AMBIGUOUS (cc,cody,fourth,hank) |
| `check8-probe-80892` | LIVE | 2026-10-06T16:36:13Z | 1.3 | AMBIGUOUS (cc,cody,fourth,hank) |
| `condcov-47876` | LIVE | 2026-09-30T15:07:09Z | 146.8 | UNATTRIBUTED |
| `condcov-54148` | LIVE | 2026-09-30T12:56:13Z | 149.0 | UNATTRIBUTED |
| `defreg-probe-16292` | LIVE | 2026-09-22T11:23:44Z | 342.5 | AMBIGUOUS (cc,cody,fourth,hank) |
| `defreg-probe-43872` | LIVE | 2026-09-25T16:42:55Z | 265.2 | AMBIGUOUS (cc,cody,fourth,hank) |
| `defreg-vocab-52240` | LIVE | 2026-09-25T23:36:33Z | 258.3 | **cc** (the only unique attribution) |
| `gate-probe11-55060` | LIVE | 2026-09-30T11:53:41Z | 150.0 | AMBIGUOUS (cc,cody,fourth,hank) |
| `gate-probe3-64416` | LIVE | 2026-09-30T11:56:31Z | 150.0 | AMBIGUOUS (cc,cody,fourth,hank) |
| `gate12-41636-7` | LIVE | 2026-09-14T20:59:03Z | 525.0 | UNATTRIBUTED |
| `gate12-67880-1` | LIVE | 2026-09-30T11:53:47Z | 150.0 | UNATTRIBUTED |
| `gate12-80200-6` | LIVE | 2026-10-06T16:33:46Z | 1.4 | UNATTRIBUTED |
| `invis-flag-16048` | LIVE | 2026-09-14T15:56:59Z | 530.0 | AMBIGUOUS (cc,fourth,hank) |
| `newchk-27740` | LIVE | 2026-09-14T16:44:55Z | 529.2 | UNATTRIBUTED |
| `reseat-probe-30012` | LIVE | 2026-09-18T11:39:23Z | 438.3 | AMBIGUOUS (cc,cody,fourth,hank) |
| `sairn-abl-6qhfv9ie` | LIVE | 2026-10-06T08:56:43Z | 9.0 | AMBIGUOUS (cc,cody,fourth,hank) |
| `sairn-abl-bsyg_uas` | LIVE | 2026-09-30T13:18:00Z | 148.6 | AMBIGUOUS (cc,cody,fourth,hank) |
| `sairn-abl-km_s5rih` | LIVE | 2026-10-06T07:34:43Z | 10.4 | AMBIGUOUS (cc,cody,fourth,hank) |
| `sairn-abl-nevmzbd8` | LIVE | 2026-10-06T15:30:25Z | 2.4 | AMBIGUOUS (cc,cody,fourth,hank) |
| `sairn-abl-orijq33k` | LIVE | 2026-10-06T10:07:50Z | 7.8 | AMBIGUOUS (cc,cody,fourth,hank) |
| `sairn-abl-t0p25sor` | LIVE | 2026-09-16T14:17:25Z | 483.7 | AMBIGUOUS (cc,cody,fourth,hank) |
| `sairn-abl-y7nful1x` | LIVE | 2026-09-30T13:30:07Z | 148.4 | AMBIGUOUS (cc,cody,fourth,hank) |
| `sairn-gate-base-4c8732958922` | LIVE | 2026-09-28T01:31:01Z | 208.4 | AMBIGUOUS (cc,cody,fourth,hank) |
| `sairn-sab-q3zkz0fe` | LIVE | 2026-09-26T01:17:53Z | 256.6 | AMBIGUOUS (cc,cody,fourth,hank) |
| `sairn-sab-szec3rh0` | LIVE | 2026-09-25T23:31:08Z | 258.4 | AMBIGUOUS (cc,cody,fourth,hank) |
| `tmp.G76I8J1BA2` | LIVE | 2026-10-05T13:44:38Z | 28.2 | UNATTRIBUTED |
| `tmp.IQV1bOshI2` | LIVE | 2026-10-05T13:34:41Z | 28.4 | UNATTRIBUTED |
| `wt_c9` | LIVE | 2026-09-16T12:36:20Z | 485.3 | UNATTRIBUTED |

**`git worktree prune` would remove NONE of them** — it only forgets entries
whose directory is gone, and all 28 exist. **And two are ACTIVE, not stale:**
`check8-probe-80892` and `gate12-80200-6` were written **1.3 and 1.4 hours
ago**. Sweeping on age would have deleted a live run.

**THE OLDEST IS 530 HOURS — 22 days.** `invis-flag-16048`, `newchk-27740`,
`gate12-41636-7` and `wt_c9` all predate 2026-09-17.

### THE ATTRIBUTION IS WEAK AND THE TOOL SAYS SO RATHER THAN GUESSING

**Only 1 of 28 resolves to a single session.** 17 are `AMBIGUOUS` across all
four build agents and 10 are `UNATTRIBUTED`. The cause is my own heuristic:
it matches name tokens against claimed paths, and tokens like `probe`, `gate`
and `check` match almost every claim.

**That is reported as a limit, not dressed up.** `AMBIGUOUS` is the honest
output of a loose matcher, and a tool that named one session from this
evidence would be inventing an owner — which is the failure the whole
owner-map exists to avoid.

**THE REAL FIX IS NOT A BETTER MATCHER.** It is that a tool should name its own
worktree after itself and reap it. `dead_rule_sweep.py` does exactly that
(`drs-sandbox-*`, reaped by name on the way in and out) and **it is the only
prefix absent from this table.** That pattern is the one to copy, and it is
routed rather than imposed.

---

## ITEM 4 — THE CAUSE HUNT: ALREADY FOUND, BETTER THAN I WOULD HAVE, AND I AM NOT THE ORIGINATING FINDER

**The instruction said I am the originating finder and I close it. At HEAD that
is not true, and the correction matters more than the item.**
`tests/push_gate/check8_probe.py` lines 31—78 carry a full account dated
**2026-10-06**, written by the session that owns that probe.

### What is already measured there, and it is a measurement not a guess

| | |
|---|---|
| reproduction | **three times, deterministically** — `timeout 240 python tests/push_gate/check8_probe.py`, after a run killed by a per-suite ceiling |
| symptom | `.git/config` gains `[core] bare = true` plus `[user] fx@example.invalid`, and every git command then fails with *"must be run in a work tree"* |
| attribution method | digesting `.git/config` after every suite during a whole-tree run |
| **pinned to ONE STEP** | `dry_push(probe_env=False)` — the first real `git push --dry-run` from the worktree whose outgoing range is READABLE, because the fixture sits on top of `FETCH_HEAD` |
| therefore | the writer is inside the `.githooks/pre-push` chain, on a path reached **only when the range resolves** |

### THE PART WORTH COPYING IS WHY SIX ISOLATIONS CAME BACK CLEAN

Every manual reproduction hit *"the outgoing range ... could not be read"* —
`origin/main` moves hourly here — **so the gate chain exited BEFORE the path
that writes.**

> **A negative result from an isolation that never reached the code is not
> evidence about that code.**

That sentence is the generalisable finding, and it is the same shape as my own
*"a load-and-list smoke test is not evidence of no behaviour change"* — both
are a check that passed without reaching the subject. **Both go into item 13.**

### The remaining suspect, and it is labelled NOT A MEASUREMENT

`tools/sairn_push_gate_hook.py`'s **check-12** path builds a
`sairn-gate-base-*` worktree and **runs generators from the base commit** —
older copies of tools, with cwd inside a worktree, **where a `git config` write
lands in the SHARED config.**

**And that worktree is in the table above:** `sairn-gate-base-4c8732958922`,
208.4h old. **Consistent with the hypothesis, which is not the same as
confirming it.**

### My own contribution, and it is small

I re-derived at HEAD rather than re-hunting:

```
grep -rnE "core\.bare|--bare|init --bare|clone --bare|GIT_DIR" tools/ tests/ .githooks/
  -> NOTHING sets core.bare directly. Four files use `git init --bare` and all
     four do it in their OWN throwaway directory:
       tools/install_git_hooks.py:86
       tests/claims/run_freshness_probe.py:117
       tests/claims/run_push_verify_probe.py:130
       tests/run_cron_liveness_probe.py:424

python tests/push_gate/check8_probe.py --check-residue        EXIT 0
  "no backup: no run of this probe died before restoring .git/config."
```

**SO NOTHING IN THE REPO SETS `core.bare` AND I AM NOT GUESSING WHICH DOES.**
The four `--bare` uses are all legitimate and all scoped to their own temp
directory. The containment is in place and reports no residue right now.

**`tests/seam_check/run_delegation_probe.py` — the second named suspect —
contains NO `init`, `worktree`, `bare`, `GIT_` or `config` call at all.** It is
not a candidate on the evidence in the file.

### CAUSE TAG AND ROUTE

**Cause tag: `SHARED_CONFIG_WRITE_FROM_WORKTREE`** — a `git config` write made
with cwd inside a linked worktree lands in the shared `.git/config`, so a tool
that means to configure its own sandbox configures the clone.

| | |
|---|---|
| **containment** | **DONE, by the probe's owner, and labelled as containment rather than a fix** — config bytes copied before anything runs, restored on every ordinary exit, left as a restorable backup for the one path a process cannot defend against (being killed), and `--check-residue` finds and restores it |
| **root cause** | **OPEN.** Routed to **cc** — `docs/tool-owner-map.json` gives `tools/sairn_push_gate_hook.py` as `CONTESTED`, owner **cc**, also claimed by cody and hank. It is in **no live claim** at HEAD, so cc is free to take it |
| **I did not fix it** | and I did not reproduce it either: reproduction needs a run killed by a ceiling, and the owner has already done it three times |

**ROUTED TO cc, NOT TED.** The instruction said route to ted; the owner map and
the claim history both say the file is cc's. **Claims-checked first, as asked,
and the answer was different from the instruction.**
