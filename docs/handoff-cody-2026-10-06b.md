# Handoff — Cody, 2026-10-06 (queue 18, second handoff of the day)

**Written at a point where nothing is half-finished.** Verify before trusting
it: `git status -sb` and `python tools/sairn_claim.py list`.

Earlier handoff today: `docs/handoff-cody-2026-10-06.md` (queue 17).
This batch: `docs/2026-10-06-cody-queue18-*.md`,
`docs/2026-10-06-could-not-run-ledger.md`.

---

## 1. COMMITTED AND PUSHED

| sha | what |
|---|---|
| `6f313a77` | **two Tier A obligations discharged**, one a 236h takeover — the eleven blob conversions are fine and the coverage number is a floor |
| `67080039` | **a timeout now says `COULD NOT RUN: bound Ns exceeded`** and never "no lock, no control"; per-tool measured bounds; the 23-rule ledger for H2; cross_tenant's 4 dead rules diagnosed, four different causes |
| `5b5b2963` | **`tools/tool_owner_map.py`** + `docs/tool-owner-map.json` — 17 of 312 tools say who owns them, 209 cannot be attributed |
| `ae47c86a` | items 10–13: the hover-log boundary, the remaining-19 SQL table, the upgrade check, the 2x-bound rule, **and the `core.bare` incident** |
| `99535102` | **the mintCustomToken arm, and it broke the upgrade on its first run** |

---

## 2. THE ONE THING THAT CHANGES A DECISION

**`firebase-admin@14.5.0` MUST NOT BE LANDED.** My own queue-17 recommendation
is withdrawn.

v13+ removed the legacy namespace. Measured side by side: `admin.credential`,
`admin.auth`, `admin.apps`, `admin.app` and `admin.database` are **all
`undefined`** in 14.5.0; only `initializeApp` survives. **All three functions in
`api/_lib/firebase-admin.js` break**, not just the minting one.

**`initializeApp` surviving is what hid it.** A smoke test that loads the module
and lists its exports passes under both versions — which is what queue 17 did,
and it reported the wrapper "LOADS under 14.5.0 and exports all three
functions". True, and it was module resolution, not a token.

**Both HIGH advisories are ACCEPTED** with a measured basis (the vulnerable
primitive is *verification*; our one `forge.*` call is a *parser* on our own key)
and four triggers. **Trigger 1 is the live one: port
`api/_lib/firebase-admin.js` to the modular API** — five call sites in one
141-line file, auth code on a payment path, **a decision and not a chore.**

---

## 3. OPEN, WITH THE EXACT NEXT STEP

### 3.1 Michael's SQL — unchanged, and it is the only human-blocked item

`PRESENT 0 / MISSING 26` is still the recorded baseline and **I did not re-drive
it this batch.** File 1 was handed over in the previous report; the other 19 are
tabled in `docs/2026-10-06-sql-runbook-remaining-19.md` with tables, bytes,
prerequisite order, confirm section and expected rows.

**NEXT STEP:** one file, then that app group's confirm section, then stop.
**Not one of the 19 carries a destructive statement** — the 18 `drop` occurrences
are all `drop policy if exists` paired with an immediate `create policy`.

### 3.2 Tier A — **32 open, 23 eligible for me, 6 assigned to me**

Re-measured at the end of this batch. **It was 35/26/7 at the start.** Two were
discharged by me, one by hank. **Do not quote 26, 28 or 35.**

**NEXT STEP:** most overdue first, one sabotage control per attack point.
`docs/tier-a-reviews.json` is in **my** claim — release it or hand it on.
**Use `--body-file`, never a shell argument** (see §5).

### 3.3 The three timeouts still owed

`metamorphic_check.py` (120s), `nhi_register.py` (5s, 20s),
`overrun_inversion_scan.py` (120s) do not obey the 2x-bound rule.
`dead_rule_sweep.py` does; `wait_for.py` is exempt and is the counter-example.

### 3.4 53 dead rules, still routed and undiagnosed

cc 13 across 6 tools, hank 10 across 4, **30 across 16 tools with no owner**.
`docs/tool-owner-map.json` now names **7 of those 16** (2 authoritative from
`# OWNER:` lines, 5 from a weaker creating-commit derivation). **9 unnameable.**

### 3.5 The two UNBOUNDABLE rules

`run_all_tests.py:PUSH_RE` and `guard_ablation.py:GATE`. Both exceeded 420s
without finishing. **NEXT STEP is a fixture lock or a declared control, not a
bigger bound** — the real run is the wrong evidence class for a harness.

### 3.6 Seven methodology rules in dated files

Three from queue 16, three from 17, the 2x-bound rule from 18.
**`docs/METHODOLOGY.md` does not exist at HEAD and is Ted's to create** — and it
is in hank's batch-10 claim as of this writing. Routed again.

### 3.7 `db/schema_snapshot.json` — **fourth's, and two reasons it cannot be reviewed**

`_constraints` is **absent**, and the recorded sha `a9e35feef967` is **dangling**
— `--list` says it does not resolve here, so a review would not be looking at
the diff fourth recorded. **I hold nothing on it and never did.**

### 3.8 The control held back

`tests/run_blob_coverage_scope_sabotage.py` — written, run, **EXIT 1, 2
findings**, and **not tracked**. Its presence even untracked drifts
`docs/TOOLING-INVENTORY.md`, which was in hank's claim when the decision was
made. Held in the session scratchpad as `held_blob_scope_sabotage.py`. **Both
verdicts that cite it say the citation is a forward reference.**

**NEXT STEP:** when `docs/TOOLING-INVENTORY.md` is free, move it back into
`tests/`, regenerate, push, and drop the forward-reference caveat.

### 3.9 28 leaked worktrees

`.git/worktrees` holds 28 registrations whose directories all still exist in
`%TEMP%` — 7 `sairn-abl-*`, 5 gate probes, 2 `sairn-sab-*`, 3 `defreg-*`, 2
`condcov-*`, 9 assorted. **None are mine.** `git worktree prune` would do
nothing because every directory exists. **Not swept** — removing 28 other
sessions' worktrees is not a call to make from inside a batch.

---

## 4. CLAIMS HELD

**`Tooling`, cody** — covering `docs/tier-a-reviews.json`,
`tools/dead_rule_sweep.py`, `tests/run_dead_rule_sweep_probe.py`,
`tools/tool_owner_map.py`, `docs/tool-owner-map.json`, `tools/capture_exit.py`
and this batch's documents. **Released at the end of this batch** — check the
tool, not this line.

**Claim state moved three times mid-batch and it changed what was possible:**
hank held `tools/tooling_inventory.py` and `docs/TOOLING-INVENTORY.md` at the
start (so the blob control was held back), **released them mid-batch** (so
`tool_owner_map.py` could be registered), and **re-claimed them** by the end.
**The state when a decision is made is the state that governs it** — the held-back
control stays held back.

**Written under another session's claim: nothing.** One file was written while
in **no** claim and is now in mine (`docs/tier-a-reviews.json`); hank wrote one
record into it before seeing my claim, through the sanctioned
`--discharge --takeover` path, and that file's union-by-identity merge handles
the collision by design.

---

## 5. READ THIS BEFORE WRITING TO THE LEDGER

**`tier_a_review_gate.py --discharge` takes `--body-file`. USE IT.** I passed a
verdict as a shell argument and the shell command-substituted two backticked
fragments away and **replaced a third with the output of `id`** — a local uid and
gid pasted into an append-only ledger. The tool's own comment says *"THE SHELL IS
WHERE THE TEXT DIES, NOT THIS TOOL"*. Reverted and redone through `--body-file`;
**the leak never reached origin.**

**And never rewrite that file with `json.dumps`.** My repair attempt produced
**5681 insertions and 5674 deletions** on a 235-record ledger four clones merge.
Reverted; the correct diff was **15 and 8**.

---

## 6. WHAT WENT WRONG THIS BATCH, MINE

1. **The verdict shell-substitution and uid leak** (§5), reverted.
2. **The whole-file ledger reformat** (§5), reverted.
3. **The `UNBOUNDABLE` guard in the wrong function** — it sat inside
   `_bare_baseline()`, which the WRITER tier never reaches, so
   `run_all_tests.py` still printed "no fixture lock and no control". **Caught by
   driving the tool, not by reading it.**
4. **Two arms matching their own text** — L1 matched the fixture inside L1c, L2
   matched the retired sentence in the comment explaining its own fix. *"My own
   comments trip my own scanners"* is in my notes and I wrote it twice anyway.
5. **A fabricated check** — my first config-refusal arm was `assert.ok(true)`
   with a paragraph explaining why it could not be tested. It could; a child
   process has an empty module cache.
6. **A wrong `aud` assertion**, and **a loose SQL regex** that invented a
   27-vs-26 discrepancy against a runbook that was right.
7. **I nearly filed a false accusation against the push gate.** When a block
   survived unstaging I concluded three documents were already stale at HEAD —
   then moved the untracked file out and re-measured: all three `--check` runs
   exit 0. **The gate was right and I was wrong.**

**Every one was caught by a control, a re-measurement or a paired arm.** The
ones with none are the ones I cannot count.

---

## 7. SESSION TRANSCRIPT

```
C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\0031bd18-e9b8-4680-ac88-e24a9d40aaed
```

`scratchpad/` holds every captured run: `fa12/` and `fa14/` (the two dependency
trees, each with `api/`, `tests/` and `suiteres.json`), `mint14.txt` (the
14.5.0 failure), `the23.txt`, `ct200.txt`, `ownermap.json`, `upg.txt` (the
upgrade check), and `held_blob_scope_sabotage.py`. `tasks/` holds the raw
background output.

**`docs/tool-owner-map.json` is a derivation, not a record.** It attributes to
the last CLAIMER, not the author, and 209 of 312 tools resolve to nobody. **An
`# OWNER:` line is the only authoritative basis** and there are 17.
