# HANDOFF — fourth / ted, batch b11, 2026-10-13

**Written BEFORE the report**, at a point where nothing is half-finished: the
b11 work is committed and pushed, `HEAD == origin/main`, no git operation is in
progress, no stash is held, and every item is closed with evidence or named
open with its exact next step.

**NAMING:** `SAIRN-handoff-<session>-b<n>.md`, the convention b10 established
and applied backwards. A batch number is a fact about the work; a date is a fact
about the keyboard, and the two came apart when b9's handoff was typed
`2026-10-16`.

**EVERY FIGURE BELOW NAMES THE COMMAND THAT PRODUCED IT.** That is this batch's
own new rule (item 4), applied to its own handoff first.

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\d1bef68d-f747-45a9-89b1-59dd99a42ae2\scratchpad\`
Derivations are scripts, not prose: `gen_undriven_doc.py` (+
`gen_undriven.log`), `ack_check.py` (+ `ack_check.log`), `index_resolve.py` (+
`index_resolve3.log`, `index_resolve_post.log`), `mk_bydesign.py` (+
`bydesign.log`), `rederive_b11.log`, `meth_b11.md`, `reb.py`, and still cited
from b9/b10: `undriven.txt`, `owner_map.py`, `owner_map.log`,
`drive_red86.jsonl`.

---

## 0. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `708222c2` | `git rev-parse --short=8 HEAD` |
| `origin/main` | `708222c2` | `git rev-parse --short=8 origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| working tree | clean (tracked) | `git status --porcelain` |
| b11 push | `a072c99d..708222c2` | `git rev-list --count a072c99d..708222c2` |
| push forced? | **NO** | one race lost (non-fast-forward), fetched, rebased, landed on the next attempt |
| `SAIRN_SEED_GATE=off` | **not used**, any form | — |
| `.claude/settings.json` | **not committed**; hooks **0 groups, 0 entries** | `json.load(...)['hooks']` |
| files edited under `tools/` | **0** | by instruction; item 2 is route-only |

**`708222c2` IS THE STATE AT FINALISATION OF THIS HANDOFF and is one commit
stale by the time you read it** — a handoff written *before* the report cannot
contain the commit that carries the report. **Re-derive HEAD rather than quoting
this table.**

---

## 1. THE ONE THING THE NEXT SESSION MUST NOT "FIX"

**`tools/tooling_inventory.py` CANNOT BE RUN IN THIS WORKING TREE and that is
correct.** It derives one of seven sources from `.claude/settings.json`, which
has hooks cleared on purpose, reads 0 entries, and refuses (exit 2) rather than
writing a thinner document. **Regenerate it inside a detached worktree of the
commit** and copy the result in. Do not restore hooks.

---

## 2. ITEM BY ITEM, with the exact next step for each open one

| # | item | state | exact next step |
|---|---|---|---|
| 1 | the 36 undriven suites as a routing doc | **DONE — generated, inputs embedded, generator refuses on disagreement** | **cody drives the 36 in a worktree**, one JSON record each; **hank drives his 5** |
| 2 | route `:409` + the 6-arm spec; ruling recorded once | **DONE — routed, and a ruling row created** | **cc writes either half of `DECIDE_OR_NOT_PROMOTED`**: apply the fix, or a `NOT_PROMOTED` entry saying why not |
| 3 | both indexes resolve after the b9 renames | **DONE — 0 dead entries, 0 rename casualties** | nothing |
| 4 | the count-names-its-command rule + re-derive 3 | **DONE — 4 re-derived, 1 moved** | nothing; the rule applies from here on |
| 5 | routed findings unacknowledged by owner | **DONE — 6 of 9 UNACK, measured** | **cody 4, cc 2** — see §4 |
| 6 | push without force, confirm | **DONE — `a072c99d..708222c2`, 0/0** | nothing |
| — | this handoff, before the report | **DONE** | — |

### Item 3 — both indexes resolve, and the three non-resolving tokens are correct

`python scratchpad/index_resolve.py` → **exit 0**.

```
DRIVE INDEX   64 declared paths + 20 authoritative_copy fields, ALL resolve
docs/ INDEX   1,004 lines scanned line by line (2.38MB, never loaded whole),
              155 distinct path tokens, 3 do not resolve
VERDICT       dead Drive entries 0; b10-rename casualties 0;
              unexplained docs/ tokens 0
```

**ALL THREE NON-RESOLVING TOKENS ARE CORRECT AS WRITTEN** and are classified in
the tool itself, so a *fourth* one is visible immediately instead of hiding in a
count that always says three:

* `SAIRN-SESSION-N-HANDOFF.md` — a naming placeholder; `N` is a variable.
* `docs/2026-10-06-cc-routed-to-hank.md` — **the absence IS the finding.** The
  row's own text reads *"CC'S ROUTED TEXT FOR HANK DOES NOT EXIST"*. Repairing
  the reference would delete the finding.
* `docs/backup-reader-verification.json` — a runtime input whose absence is a
  documented handled state; the committed artefact is the `.template.json`.

**THE RESOLVER'S OWN FIRST RUN PRODUCED A FALSE DEAD ENTRY** and it is fixed and
named: it matched a **suffix** of `backup-reader-verification.template.json`
because nothing anchored the token's left edge. A resolver that invents a dead
entry sends somebody to repair a correct row — and in an index five sessions
write, that repair is an edit to another session's finding.

---

## 3. CLAIMS AND EXTERNAL HOLDS

| hold | count | detail | command |
|---|---:|---|---|
| repo claims held | **1** | b11, 9 declared FILES, committed **and pushed** | `sairn_claim.py list` |
| session locks held | **1** | `fourth.lock`. Release DENIED by the permission layer for a **fifth** successive batch — a standing fact about this clone, not an event | — |
| locks released by me | **0** | none of the dead ones is attributable to me | — |
| worktrees besides main | **4** | **none mine**: `gate12-65340-3`, `invis-c0-75132`, `sairn-abl-q_gv10j5`, `sairn-gate-base-d78d62e71203` — the last is the push gate's own throwaway, which it failed to remove and says so on stderr | `git worktree list` |
| `git stash` | **0** | | `git stash list` |
| `refs/salvage/*` | **0** | bundled, verified, deleted in b9 | `git for-each-ref refs/salvage/` |

**Nothing was edited outside the declared `FILES` set.** **No file under
`tools/` was edited**, by instruction.

---

## 4. WHAT IS OPEN, AND WHY — with the owner and the exact next step

### UNACKNOWLEDGED ROUTED FINDINGS — 6 of 9, `python scratchpad/ack_check.py`

**cody — 4, all from b9. Next step for each: a commit touching the line, or a
`NOT_PROMOTED` entry naming the file AND the line. Nothing else closes it.**

* `tests/faults/grd_write_faults.js:385` — UNACK
* `tests/push_gate/check8_probe.py:209` — UNACK
* `tests/sairnlegacy_session_gate_review_probe.js:202` — UNACK
* `tests/seed_never_syncs_platform.js:274` — UNACK

**cc — 2, both MENTION_ONLY, which is NOT acknowledgement.**

* `tools/hover_auditor_scope_gate.py:409` — now also carries a row in
  `docs/by-design-register.json`, owner cc, state `DECIDE_OR_NOT_PROMOTED`.
  **Next step: either half of that state.**
* `tools/session_lock_check.py:128` — routed in b9;
  `docs/2026-10-13-fourth-routed-to-cc.md`.

**hank — 0 routed `file:line` findings**, stated rather than left as an empty
section. What hank owns is a count, not a line: **5 red suites under `api/`**,
and the audit-log constraint result (3 of 16 tables rejecting 11 emitted values,
plus `sv_audit_log` with no `event_type` CHECK at all), which needs one live
`pg_constraint` read nobody in this clone can do.

### The rest

* **36 registered red suites have NEVER been driven** — **cody's**, all under
  `tests/`. `docs/2026-10-13-fourth-b10-undriven-suites.md`. 180s × 36 is up to
  1.8 hours, so drive them **in a worktree** (several write when run); exit 0
  moves the entry out of `entries`, exit 2/3/timeout **must not**.
* **21 of 84 register entries carry no `why`**, and **5 of the 48 driven came
  back COULD NOT RUN** — the sharper group: a suite that cannot run has no
  verdict and reads as "still red" for ever.
* **The unfetched-base CHECKER is specified and built by nobody.** A fifth gate
  can still be authored with the shape. Recorded as a *planned* action on defect
  record `55777a74` and now as a ruling row.
* **4 pre-existing bad rows in `docs/scrutiny-flags.json`** — already on
  `origin/main`, **cody's files**. They make `tools/sairn_rebase_resolve.py`
  REFUSE on every scrutiny-flags conflict, a tax on every rebase in every clone.
* **`docs/TOOLING-INVENTORY.md` under-reports every pre-commit-wired tool as
  UNWIRED** — the generator reads `.claude/settings.json` hooks and the push
  gate and reads `.githooks/` for neither. Needs an eighth derivation source, in
  a file two sessions contest.
* **Nothing mechanises the NEXT FREE heading count** (34 headings, NEXT FREE 35,
  `re.finditer(r'(?m)^## (\d+)\.')`). No check refuses a duplicate or a gap.
* **Nothing mechanises the new count-names-its-command rule either**, and it is
  weaker for it: a named command can still be the WRONG command. The rule makes
  a figure checkable, not correct, and catching a wrong command needs a reader.
* **`docs/by-design-register.json` has exactly 1 row and no tool reads it.** It
  is a register nothing validates — no `--check`, no gate. That is a real limit
  of this batch and the obvious next piece of work on it.
* **Drive-side handoffs are UNINDEXED for other sessions** — none mine; the
  check is warn-only on handoff names, so it reports and does not refuse.
  Deliberately not declared by me: declaring another session's artefact is what
  produced the five hand-declared rows already in that file.
* **`fourth.lock`** — still held; release denied five batches running.

**Nothing is partial.** Every item is another session's, or an observation with
its owner named, or a measurement with its command stated.
