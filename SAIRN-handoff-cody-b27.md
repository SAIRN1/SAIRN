# Handoff — cody, batch b27, 2026-10-19 — WRAPPED UP ON INSTRUCTION

**Written at a point where nothing is half-finished.** A wrap-up order arrived
while item 4 was mid-edit. **The one half-finished thing was REVERTED, not left
to look closed**, and §4 says exactly why. Everything else is committed, green
and verified.

---

## 1. FINISHED vs REVERTED vs OPEN — plainly, before anything else

| item | state | what that means |
|---|---|---|
| **1. `rt_routes` branch + extraActions** | **FINISHED** | Landed **exactly as routed**, asserted byte-identical to the document's own fenced block. **And the feature was still dead** — a fourth gate nobody knew about. Fixed, with 6 dispatcher arms + an ablation |
| **2a. `office_manager` in `ALF_NON_MGMT`** | **FINISHED** | Plus a completeness arm so the sixth role cannot repeat it. 30 arms, exit 0 |
| **2b. law reconcile reads the module** | **FINISHED** | An attorney was being refused in production by a copy b19 had already superseded |
| **2c. the fifth `decide` argument** | **FINISHED, and the routing was incomplete twice** | Landed and driven. Routed step 2 was **tried, driven and removed** — it breaks an invariant two arms assert. 18 new arms |
| **3. R1c / R1f / R2 re-aimed** | **FINISHED** | 34 arms, exit 0 (was 29/3). Two arms added, not just re-aimed |
| **3b. the `leg_clergy` rollup row** | **NOT CLOSED — ROUTED** | **fourth holds `docs/CRITICALITY-TIERS.md`.** Fix proven in a worktree, `PROBLEMS:14 → 9` |
| **4. the 12 unproducible tails** | **REVERTED — 0 of 12 measured** | The hooks were **unreachable**. §4 |
| **5a. the 10 census timeouts at 300s** | **FINISHED** | **Identical to 120s. They are real hangs.** b26's caveat is closed |
| **5b. the 4 undiagnosed recoveries** | **FINISHED** | All four diagnosed to a named commit or a routed fix landing |
| **5c. the two stale worktrees** | **FINISHED** | Both removed from `git worktree list` |

---

## 2. Committed and pushed state

| | |
|---|---|
| commits | **seven**, on `main`. §7 records the push |
| claim | `platform`, taken **BEFORE any work** with a FILES list. **STILL HELD** as this is written — released with the report |
| overrides | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`, no call to `tools/gate_skip.py` |
| boundaries honoured | **`tools/` not touched** (cc's) — five were RUN. **`api/bridge.js` and `api/*-countersign.js` not touched** (hank's). **No `.html` file touched** (fourth's) — two were READ. **`api/_lib/leg-roles.js` DROPPED from the claim** on a real block. **`docs/CRITICALITY-TIERS.md` not touched** — fourth holds it |
| live writes | **NONE.** No endpoint called, no row seeded, no Supabase request |
| SQL for Michael | **NONE.** No new `sql/` file; `sql/sairnlegacy_settings_schema.sql` already exists and Michael confirmed the table is live |

```
05decae97  feat(rt_routes): land the handler branch and the extraActions line
           exactly as routed, and nothing else
bac3f3201  fix(rt_routes): the branch landed and the feature was STILL DEAD
1439d8069  feat(roles): the three routed role and policy changes
c7b26406b  fix(known-red): a STABLE LAST LINE in each of the 12 suites
d13439c43  revert(known-red): the hooks were UNREACHABLE -- 0 of 12 measured
0928916ab  feat(census): the 10 timeouts RE-DRIVEN AT 300s -- real hangs
```

---

## 3. The one pattern this batch is about

**Three of the routed instructions were incomplete, and every one was found by
DRIVING the routed change rather than by reading it.**

1. **`rt_routes`** — the branch, the registry entry and the `extraActions`
   declaration were all correct and the feature was **dead**.
   `isVisibleTo('rt_routes','stonedesk')` was **false**, so `checkEnvelope`
   answered 400 before the branch ran. A **fourth** gate the routing document
   did not know about.
2. **`leg_settings` in `LEG_RESOURCES`** — breaks an invariant two arms assert
   (`handler=37 table=36`). The fix needs a row in hank's file.
3. **`prepare`** — not a declared verb for any `leg_` resource, so the
   dispatcher 400s it. **My first arm asserted `!== 403` and that 400 satisfied
   it** — it would have reported F3 working while every request was refused.

---

## 4. Item 4 — REVERTED, and this is the whole reason

**`c7b26406b` landed a fix that does nothing. `d13439c43` takes it back out.**

```
python docs/b27-logs/stable_last_line.py --drive
-> 0 of 12 subjects now end with SUITE-RESULT
```

**THE CAUSE, MEASURED.** These probes call `sys.exit(...)` at **module level**,
and the hook was appended at the **end** of the file:

```
tests/run_rebase_resolve_probe.py:213   sys.exit(1 if fails else 0)
tests/run_rebase_resolve_probe.py:215   # ── A STABLE LAST LINE ───────
```

`sys.exit()` raises `SystemExit`, which propagates out of the module body, so
everything after it — **including the `atexit.register()` call** — is never
reached. The reasoning that put it at the end was sound on its own terms
(`atexit` handlers run in **reverse** registration order, so the earliest
registration fires last) and it was reasoning about **a line that does not
execute**.

**A COMMITTED FIX THAT DOES NOTHING IS WORSE THAN AN OPEN ITEM.**
`docs/known-red-suites.json` was **never updated**, so all 12 rows still carry
their original tails and still read `UNPRODUCIBLE` — the register is exactly
where b26 left it and **nothing claims otherwise**.

**KEPT:** the tool and its measured negative result
(`docs/b27-logs/stable_last_line.py`, `stable_last_line.json`), because the
measurement is the finding.

---

## 5. Verification

```
EXIT=0  node --check api/sd-data.js  api/_resources/{index,routes}.js
EXIT=0  node api/_lib/routes.test.js                63 arms (was 56)
EXIT=0  node api/b27-leg-settings.test.js           18 arms, NEW
EXIT=0  node api/b19-iolta-reconcile-carveout.test.js  34 (was 29/3)
EXIT=0  node api/sd-data-alf-isolation.test.js      30 (was 28)
EXIT=0  node api/sd-data-leg-role-matrix.test.js    37, regression
EXIT=0  node api/sd-data-leg-overlap.test.js        36, regression
EXIT=0  node api/sd-data-session-gate.test.js       22, regression
EXIT=0  python tools/md_table_check.py              all files clean
EXIT=0  python docs/b27-logs/ablate_b27.py          4 legs, EVERY subject arm
        RED and every named control GREEN; live tree asserted unwritten
EXIT=1  python docs/b27-logs/stable_last_line.py --drive   0 of 12 -- §4
        api/_resources/extra-actions.test.js        41/7, IDENTICAL to the
        figure b26 registered it known-red at -- NOT a regression
```

**THREE POST-CONDITIONS AND CONTROLS WERE WRONG ON THEIR FIRST SPELLING AND
EACH REFUSED OR FAILED RATHER THAN PASSING QUIETLY.** The lander's "branch is
above the fallthrough" arm compared against a string that appears **three
times**, twice in comments. D5's ablation control was **inside the blast
radius**. L1's ablation subject could not move at all. Each is recorded where
it happened.

**THE LIVE TREE WAS NEVER WRITTEN BY ANY ABLATION**, asserted rather than
intended: `git status --porcelain` captured before and after the whole run and
compared.

---

## 6. Open — every item, why, and the exact next step

### 6.1 → ITEM 4. The 12 tails are still unproducible

**NEXT STEP, with the measured constraint:** register the hook **at the TOP of
the file**, before the module-level `sys.exit()` runs — accepting that it then
fires **last** among `atexit` handlers and may print before a cleanup handler's
output. For the one `.js` subject, `process.on('exit')` at the top is
unconditionally correct. **Verify by DRIVING, not by reading:**
`python docs/b27-logs/stable_last_line.py --drive` is the arm and it is written.

### 6.2 → THE 3 ROLLUP FINDINGS. Routed to fourth, fix proven

`docs/b27-logs/ROUTED-TO-fourth-rollup-close.md` — three commands,
`PROBLEMS:14 → 9`, `md_table_check` clean, driven in a worktree. **Two of the
five are b25's `customers` retier, three are b26's `leg_clergy`. Both are
cody's own.** fourth holds the file.

### 6.3 → `leg_settings` IN `LEG_RESOURCES`. Routed to hank

Needs a `LEG_ROLE_MATRIX` row in `api/_lib/leg-roles.js` first, or arms A1/A2
go red (`handler=37 table=36`). The entry is inert without it for three
measured reasons, so **nothing is lost by waiting**.

### 6.4 → `prepare` AS A DECLARED VERB. Routed, needs hank's half

One line in `api/_resources/sairnlegacy.js` — but **a declared verb with no
handler branch asserts a capability that answers 400**, which is the exact
reason fourth held the `rt_routes` line back. The branch is the
countersignature flow in `api/leg-countersign.js`, **hank's**. Arms V1/V2
measure the gate today and go red the moment it changes.

### 6.5 → THE F2 LIVERY GRANT. Half-wired, and S1c says so

`decide()`'s branch 4 needs a per-employee grant and `api/sd-data.js` passes
`null`. **S1c asserts the request is STILL refused for exactly that reason**, so
the half that landed is not mistaken for the whole.

### 6.6 → THE TEN HANGING SUITES. Measured, not diagnosed

They do not finish in 300s. **Six of the ten are push-gate or git-hook probes —
a suggestive cluster, not a cause.** Why each hangs is undiagnosed and recorded
as undiagnosed.

### 6.7 → `tests/law_reconcile_role_vocab_check.py`. Re-aim target recorded

It parsed the literal item 2b deleted. **It was already exit 2 for an unrelated
reason** (its own `ROLES_BY_APP` regex matches neither file), so it is red
either way. The re-aim target is now `api/_lib/law-roles.js`.

### 6.8 → NO LIVE ENDPOINT CHECK AND NO LIVE RENDER

**Nothing establishes that `rt_routes` answers a real request against a real
Supabase.** The branch is landed, reachable in the dispatcher, and unproven in
production. The deployed `alf_facility` role gate is **still UNVERIFIED** —
`tools/alf_facility_role_gate_live_probe.py` exits 2 for want of `ALF_LICENSE`.

### 6.9 → MICHAEL. Nothing is blocked on you, and no SQL is owed

No new `sql/` file. All five instructed items are implemented or reverted with
a measured reason.

---

## 7. The push

Recorded in full in `SAIRN-report-cody-b27.txt`. Three other clones push this
trunk and the gate suite takes ~90s, so the loop in
`<scratch>/push27.sh` retries, **committing every hook-written file on every
round and stashing none** — those rows are keyed per COMMIT, so a stash held
across a rebase keys them to shas that no longer exist.

---

## 8. Scratch and transcript

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\f979712d-5568-4f2c-90db-611d70cdc27b.jsonl`
— 5,428,474 bytes. **This session carries b26 AND b27**; b27 begins at the
fresh-start paste naming the six items.

**REAL MEASURED CONTEXT: `CONTEXT 82.2% of 1,000,000 -- 822,170 tokens,
measured.`** Pasted exactly as `python tools/context_verify.py --digest-line`
printed it, which is the only form the push gate accepts.

**Scratch:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\f979712d-5568-4f2c-90db-611d70cdc27b\scratchpad\`
— `push27.sh`, `push27.log`, `b27_dispatch_section.js`.

**Worktrees: BOTH b27 ONES ARE OUT OF `git worktree list`.** `b27drive` was
removed cleanly; **`b27census` refused with `Permission denied` and its
registration was cleared by `git worktree prune`, so the DIRECTORY REMAINS ON
DISK** and can be deleted by hand. `b27rollup` was removed when its measurement
finished. Nothing in the repo depends on any of them.

Four worktrees registered against this clone are **not mine** and were left
alone: `gate-probe3-17976`, `gate12-27236-2`, `gate12-37660-1`,
`sairn-gate-base-4938f4321584` (locked), `sairn-gate-tip-a1f366786b7e`.

---

*Written at a point where nothing is half-finished: item 4's ineffective commit
is reverted and recorded, every other item is committed and green, and §6 gives
the exact next step for each open one.*
