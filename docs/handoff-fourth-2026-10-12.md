# HANDOFF — fourth / ted, batch b5, 2026-10-12

**Written BEFORE the report and the digest, on purpose**, and at a point where
nothing is half-finished: every item below is either closed with evidence or
named as not done with who holds it. The report is derived from this, not the
other way round.

**Transcript / working files for this batch:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\26107814-6275-4923-8a05-52f5d7ac19bd\scratchpad\`
— every exit code quoted in the report was captured ALONE into a file there, and
the derivation scripts (`missing3.py`, `drive_reds.py`, `add_reds.py`,
`split_aw3.py`, `phi_ablate.py`, `phi_gate_control.py`, `locks.py`,
`owners.py`, `gen_routing.py`, `inv_strippers.py`) are the working, not prose
about the working.

---

## 0. THE ONE THING THE NEXT SESSION MUST NOT "FIX"

**THIS CLONE'S HOOKS ARE OFF ON PURPOSE.** `.claude/settings.json` in the working
tree carries `"hooks": {}` — 0 hook commands where `HEAD` has 23 — and it is
**uncommitted by design**, because the instruction was for this clone and
committing it would reach every other clone. Michael turned them off and the
compaction keys with them, and **b5 was told to leave them off and re-add
nothing.**

Batch b4 restored them, having found them stripped and unrecorded. That restore
was reversed at the start of b5: `.claude/settings.json` was put back from
`.claude/settings.json.stripped-2026-10-11T2045.bak`, re-parsed to confirm 0 hook
commands, and left dirty. **The next session will see a modified tracked file at
pickup and must not commit it, must not restore it, and must not re-arm
anything.**

Three untracked backups sit in `.claude/` — `settings.json.bak` (the full 23),
`settings.json.hooks.bak` (an intermediate 16), and the stripped one. They are
left because `git status` is the only thing that surfaces them. **Say when they
can be deleted.**

### What goes wrong while they are off, measured rather than predicted

1. **EVERY PUSH FROM THIS CLONE IS REFUSED, and the cause is the hooks-off file
   itself.** `tools/tooling_inventory.py` derives `docs/TOOLING-INVENTORY.md`
   partly from the hook entries in `.claude/settings.json`; with the table empty
   the generator **exits 2 and refuses**, and the push gate blocks on a generated
   document that stopped matching its source. Verbatim, from
   `.githooks/pre-push`:

   ```
   Blocked: this push makes a GENERATED document stop matching what it is
   derived from. It was clean at the base commit and is not at this tip,
   so this push is what changed the answer.

     docs/TOOLING-INVENTORY.md -- the generator REFUSES to run (exit 2)
           hook entries -- read from .claude\settings.json
         A zero here is a BROKEN READER or a MOVED SOURCE, not an empty
         repo -- and the two are indistinguishable downstream, which is
         why this refuses instead of writing a thinner document that
         would pass its own --check every time.
         REFUSING to generate -- the traverse did not close:
         docs\TOOLING-INVENTORY.md: 1 empty source(s): hook entries
         fix: python tools/tooling_inventory.py
   ```

   The generator is **right**: a zero it cannot distinguish from a broken reader
   must refuse. But it means hooks-off and pushing are mutually exclusive in this
   clone until somebody decides which. **That is question 1 for Michael.**

2. **The status-registry row is not written at session start**, so this
   session's claim reads as `DEAD` to every other clone and to the push gate —
   the whole chain b4 traced (`tools/sairn_claim.py:1281` `registry_claims()` →
   `claim_liveness()`, fed by `tools/sairn_status.py --hook` at `SessionStart`).
   Worked around by hand: `sairn_status.py set` was run explicitly.

3. **`tools/clone_health_check.py` does not run at session start**, and it is the
   check that catches `core.bare = true`. This batch found `core.bare` **true**
   mid-run — see §3 — and nothing would have said so.

---

## 1. COMMITTED / PUSHED STATE

| | |
|---|---|
| HEAD | `364df45b` |
| origin/main | `ea976892` |
| position | **4 commits AHEAD, 0 behind. NOTHING FROM b5 IS ON origin/main.** |
| the four | `0e42cfef` claim · `124e0742` b4 bypass-log residue · `6942098b` the b5 work · `364df45b` the scrutiny ledger row |
| push attempts | 3, all REFUSED. `SAIRN_SEED_GATE=off` **was not used**, per the brief. |
| working tree | `.claude/settings.json` modified **by design** (§0); 4 untracked, all accounted for |

**Re-derive, do not trust this table:**

```
git log --oneline -5
git ls-remote origin refs/heads/main
git rev-list --left-right --count origin/main...HEAD
```

### The push refusals, verbatim and in order

* **Attempt 1** (claim commit): `error: Please commit or stash them.` — the
  claim tool rebases, and `git rebase` refuses outright with unstaged changes.
  The unstaged change is the hooks-off `settings.json`, which must stay. Worked
  around for later attempts with `git -c rebase.autoStash=true rebase`, which
  stashes and restores rather than discarding.
* **Attempt 2**: `Blocked: the outgoing range ea976892...3f5bfd01 could not be
  read.` — the remote had moved; **not** a verdict about content. Fixed by
  fetch + rebase.
* **Attempt 3**, two refusals in one block, both true:
  * `EXTERNAL FILE INDEX: ... 3 UNINDEXED work file(s) under a declared external
    directory` — `g:\my drive\sairn-status\handoff-fourth-2026-10-11.md`,
    `SAIRN-handoff-h1-b10.md`, `handoff-h2-2026-10-12.md`. One is mine, two are
    other sessions'. `docs/external-files-index.json` is cc's file; **this is the
    structural problem b4 routed and it has grown from 1 file to 3** — the brief
    orders every session to upload its handoff to Drive, and that directory is
    declared and non-transient, so every compliant session arms a gate that
    blocks the next session's unrelated push. cc's
    `tools/external_file_index_check.py` is canonical per the brief.
  * the `TOOLING-INVENTORY.md` refusal quoted in §0.

**Nothing was overridden and nothing was forced.** Per the brief the refusals are
recorded here and the push was skipped.

---

## 2. ITEM BY ITEM — what is open, and the exact next step for each

| # | item | state | exact next step |
|---|---|---|---|
| 0 | resume check | **DONE** | — |
| 1 | hooks and compaction keys stay off | **DONE** | nothing. See §0 and do not undo it |
| 2 | add the missing red suites | **DONE, 11 not 30** | nothing; read the next row about the 7 GREEN |
| 3 | `phi_cache_scoped_to_user.js` cascade | **DONE in my file; cause NOT established** | the mutator is still unidentified — see §3; the routed fail-open is `tests/seam_check/run_delegation_probe.py:76`, `:80`, `:113`, `:119` |
| 4 | consolidate onto the one stripper | **PARTIAL — 5 of 44 sites** | `docs/2026-10-12-fourth-b5-routing.md` §3 lists the other 39 with exact lines; each needs its own suite run before and after |
| 5 | split the over-ceiling log | **DONE** | nothing. `--standing-doc-sizes` is now 6 over and none is mine |
| 6 | route the 36 SEQ 17-A findings | **DONE (routing only)** | `docs/2026-10-12-fourth-b5-routing.md` §1, 36 rows. **All 17 files are `UNOWNED`** — the `# OWNER:` backlog is the real fix |
| 7 | route the 6 over-ceiling docs | **DONE (routing only)** | routing doc §2 |
| 8 | `cc-review-0a_4251m` | **DONE — removed** | two NEW probe worktrees are LEFT with unreachable heads `fdce1b4b` and `549a372a`; I created them driving item 2's suites |
| 9 | orphan session locks | **DONE — 0 released** | routing doc §5. 8 dead, **0 attributable**, which CORRECTS b4's claim that 2 were hank's |
| 10 | the demo-pins SQL | **DONE — carried** | still untracked, still not mine, **ninth batch** |
| 11 | no `SAIRN_SEED_GATE=off` | **HONOURED** | the refusals are in §1 |
| 12 | convention 33 stays moved | **HONOURED — not touched** | — |
| 13 | delete nothing in `C:\Users\marsh\` | **HONOURED — nothing deleted** | — |
| 14 | build the SHA `--check` | **DONE** | `tools/report_sha_check.py`, 11 fixture arms, run on the b4 and b5 files |
| 15 | claim by FILES, log attempts | **DONE, 1 attempt, CLEAR** | the claim is committed locally and **never reached origin/main**, so treat it as NOT CLAIMED by every other clone |
| 16 | this handoff | **DONE** | — |

### The 7 GREEN is the finding in item 2, not the 11 RED

The brief said 30. **30 is hank's 2026-10-08 figure** (*"101 red, registry
records 75, 30 RED AND NOT RECORDED"*) and it was re-derived rather than carried:
the gap at this HEAD is **23**. All 23 were then **driven ALONE**, because the
register's own `_how_it_was_measured` says the individual drive is the authority
and a run log is not:

| measured state | n | goes in the register? |
|---|---:|---|
| RED, exit 1 | **11** | **yes** — 76 → 87 entries |
| GREEN, exit 0 | **7** | no — the run log that named them red is **stale** |
| COULD NOT RUN, exit 2 | 2 | no |
| SKIPPED, exit 3 | 2 | no — the runner already reports exit 3 apart from pass and fail |
| TIMEOUT at 180 s | 1 | no — a bound exceeded is a lower bound, not a number |

**An entry over a green suite is worse than a missing entry**: while it stands it
makes the next real failure of that file read as KNOWN. The 12 non-red are listed
by name with their measured state in the routing doc.

The first pass of this item called every non-zero exit red, which would have put
the two exit-3 SKIPPED and two exit-2 COULD NOT RUN suites in as failures. That
was caught before anything was written and is in the report.

---

## 3. THE THING NOBODY ASKED FOR, and it is the most important paragraph here

**Driving 23 suites one at a time left two live API files sabotaged and
`core.bare = true` in this clone.**

* `api/sd-data.js` was left missing `, warn_days: gateWarn`
* `api/_lib/subcontractor-compliance.js` was left failing `node --check` —
  `SyntaxError: Identifier 'today' has already been declared`
* `.git/seam-delegation-probe.planting`, the sentinel that exists to leave
  evidence of exactly this, was **absent**
* `git config --get core.bare` → **`true`**, so `git status` returned
  `fatal: this operation must be run in a work tree` and **exit 128**

**The chain, and every link is measured:** a push-gate probe leaves `core.bare`
true (`tests/push_gate/check8_probe.py:209` records the behaviour) → with
`core.bare` true every `git checkout --` fails → `run_delegation_probe.py`'s
restore calls it with `capture_output=True` and **never reads the return code**
(`:76` in the atexit net, `:113` in the context manager's `finally`) so the
restore **silently does nothing** → the sentinel is then removed anyway (`:80`,
`:119`), so the one layer meant to leave evidence **clears itself**.

**And my own driver had the same fail-open.** It captured
`git status --porcelain` before and after every suite and reported the whole-run
delta as `[]` — which was not evidence the tree was clean, it was evidence
**git could not answer**. That conclusion is corrected in the report rather than
left standing.

Both files were restored from `HEAD` and both now pass `node --check`;
`core.bare` was set back to `false`; `tools/clone_health_check.py` then reports
`HEALTHY`.

**ALSO MEASURED AND REFUTED, because a negative result is a result.** The
hypothesis that this is what turns `phi_cache_scoped_to_user.js` red was tested
by ablation — `, warn_days: gateWarn` removed from `api/sd-data.js` exactly as
`run_delegation_probe.py:241` removes it, the suite driven, the file restored
byte-identical and re-driven. **72 passed / 0 failed with the plant in place.**
So that plant is not the cause, **the particular mutator is NOT ESTABLISHED, and
it is not named.**

---

## 4. CLAIMS HELD

| | |
|---|---|
| claim | `fourth`, batch b5, taken on the FIRST attempt — `check` returned CLEAR with a `FILES` list declared |
| state | **committed locally, NEVER PUSHED.** The claim tool said so itself: *"PUSH FAILED after 3 attempts ... treat this as NOT CLAIMED."* |
| consequence | every other clone sees this work as unclaimed and can start it |
| not released | the batch is not finished as this is written; a claim released before the work lands was never on the work |
| session lock | `~/SAIRN-SESSION-LOCKS/fourth.lock`, `CLAUDE_PID 61696`, state `SELF` |
| status row | written by hand twice, because the hook that writes it is off |
| worktrees | 2, both probe residue from item 2, heads `fdce1b4b` and `549a372a`, **unreachable** so left |
| stash | 0 |

**No task string was reworded to dodge a matcher** (PR §4.3). One attempt, one
`FILES` list, CLEAR.

---

## 5. QUESTIONS ONLY MICHAEL CAN ANSWER

1. **HOOKS OFF AND PUSHING ARE MUTUALLY EXCLUSIVE in this clone.** With
   `"hooks": {}` the tooling-inventory generator exits 2 and the push gate blocks
   every push, so b5's work is stranded locally. Three ways out and they are all
   yours: (a) hooks stay off and the generator is taught that an empty hook table
   is a legitimate state in a clone that has them off; (b) hooks stay off and the
   generated-document check is exempted for this clone; (c) hooks go back on.
   **I did none of them.**
2. **The Drive-upload gate has grown from 1 unindexed handoff to 3.** Every
   session is ordered to upload its handoff to Drive and the gate treats the
   result as a violation. Should uploads stop, should that directory be declared
   transient, or should the index get a row per upload automatically?
3. **Three untracked `settings.json` backups** in `.claude/`. Delete, or keep?
4. **`sql/restore_demo_pins_2026-09-29.sql`** — ninth batch carried, not mine, it
   writes credential rows. Commit, delete, or keep carrying?
5. **Two probe worktrees** with unreachable heads, created by driving item 2's
   suites: `fdce1b4b`, `549a372a`. Leave, or clear?
6. **~350 files in `C:\Users\marsh\`** classified as throwaway in b4. Nothing
   deleted and nothing will be without your word. Carried.

---

## 6. WHAT IS NOT DONE, PLAINLY

* **39 of 44 private comment-stripper sites.** Routed with exact lines; each
  needs its own before/after suite run and they are other sessions' files.
* **The cause of `phi_cache_scoped_to_user.js` going red in a whole-tree run.**
  The signal is fixed in my file; the mutator is unidentified and one candidate
  was refuted.
* **The 36 SEQ 17-A findings.** Routed, not fixed — the brief said routing only.
* **The 6 over-ceiling documents.** Routed, not touched — the brief said so.
* **`tests/seam_check/run_delegation_probe.py`'s fail-open restore.** Four exact
  lines routed. Not mine.
* **The `# OWNER:` backlog.** 264 `tools/*.py` with no header, and all 17
  SEQ 17-A files have none either.
* **Everything b5 did is unpushed.** Four commits, HEAD `364df45b`.

**NOTHING IS PARTIAL EXCEPT ITEM 4, and it is named as partial with its
remainder listed row by row.**
