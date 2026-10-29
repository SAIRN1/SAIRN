# HANDOFF — fourth / ted, batch b68, 2026-10-29

**READ THIS FILE ONLY.** It is the whole state.

- **Batch number.** The dispatch's last line said `done b67`, but b67 had already wrapped and landed (`b41840602`). This batch is **b68**: one writer per counter, and reusing b67 would collide with a landed handoff.
- **Everything below is on origin/main.** Nothing is held locally.
- Wrapped at about 33% real context (the digest's CONTEXT line is the measured figure).

**Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\83c60d05-1589-4389-a5cf-cd99265bab76.jsonl`

## 1. STATE

Each landing is a SHA plus `merge-base --is-ancestor origin/main`, checked after `git fetch`. Every one below answered **yes**.

| what | commit |
|---|---|
| bld_bids session-flag arm: 2 gaps fixed (test) | `a4de92258` |
| cody b17 Tier A discharge | `ff95e3962` |
| register record, a4de92258 | `4b74b63fe` |
| sairncash: typed $0 prior-year tax kept | `63272f29d` |
| hank b18 discharge, C6 cause tags, tests/ overrides | `df92c5700` |
| cody b23, hank b21 and cc b27 discharges | `37b78f187` |
| sairnbuild: WIP forecast writer (`17821dc5c` before the rebase) | `519ca798b` |
| register and C6 tag for the forecast fix | `71867733e` |
| cc b38 discharge (HIGH routed) | `be41c3463` |
| known-red capa reconfirmed; C6 sha corrected | `84131479e` |
| claims released (sairncash, sairnbuild) | `fb35ee324`, `cd3c28c59` |

**Live pages, fetched after deploy:** `sairncash.html`, `sairnbuild.html` and `sairnmechanical.html` are each byte-identical to `origin/main`, and each fix marker is present.

## 2. DISPATCH ITEMS

1. **Re-orient.**
   - HEAD `b41840602` was 1 behind `fcc8bcaf0` (a cron commit); fast-forwarded.
   - The b67 handoff was read whole.
   - The window is declared at 1M, because b67 ran the same model string and measured 708,856 tokens.
2. **Backlog** (b67 §8):
   - **#2 CLOSED.** The live mech page is identical to origin, and its three save functions are present.
   - **#18 CLOSED**, `63272f29d`. The suite was red 4 of 6 before the fix and is 6/0 after.
   - **#15 CLOSED**, `519ca798b`. Its suite was red 5 of 6 before and is 6/0 after. Seven build suites are exit 0 both before and after.
   - **#3 NOT STARTED.** `sairn_claim check` BLOCKED on cody's live `sairnmechanical` claim, 0.1h old. Flagged and not proceeded with, per the overlap rule.
3. **Review obligations: all 6 assigned to fourth are discharged.** `obligation_surface.py --mine` now reports 0 open. Oldest first:

   | obligation | verdict |
   |---|---|
   | cody b17 bld_bids (340h) | 2 gaps found by planted mutation and **fixed** |
   | hank b18 law/legacy countersign | (a) and (b) hold; (c) MODERATE and (d) LOW routed |
   | hank b21 bridge | holds, **live-verified**; LOW optional |
   | cody b23 rollup | 3 findings routed |
   | cc b27 schema capture | holds against the **live DB**; re-capture due |
   | cc b38 deleted-row pre-gate | **HIGH** routed |

   Every verdict is in `docs/tier-a-reviews.json`.
4. **known-red-suites.json.**
   - The capa entry was **already** moved to `recovered` by fourth b66 (`29da9532c`), and nothing has touched the control since.
   - Re-driven alone this batch: exit 0, tree unchanged. Recorded as `reconfirmed_b68` on that entry.
   - The whole-register re-drive (`tools/red_suite_register_check.py`) was started and **had not finished at wrap**, after more than 2h. 62 entries at up to 420s each. **Its verdict on the other 62 entries is NOT claimed.**
5. **Cause tags.** `docs/recurring-bug-classes-2.md` §C6 covers every fix, and each fix commit message carries its own tag.

## 3. FINDINGS ROUTED (exact next step each)

| finding | owner | next step |
|---|---|---|
| **HIGH: deleted-row check on shared/routes resources follows `memApp = body.app_id \|\| 'stonedesk'`** (`api/sd-data.js:2247`, `:2351`), a caller-chosen field. Measured, DELETED row: `employees/read` (app_id=sairnbiz) 200; `employees/write` (no app_id) 200 with POST executed; `render_usage` 200; `rt_routes` 200. **`sairngrounds.html` grdData sends no body.app_id, so the stock client of a deleted grounds employee is served.** Arm S2 of `api/b38-deleted-row-platform.test.js` codifies it | cc | Scope by the TOKEN's app (or `lic.app_id`). Add shared/routes to the D/I/C population, and make S2 assert 403 |
| MODERATE: a transport throw in the active check fails OPEN (`api/_lib/auth.js:1184`, `NO_ACTIVE_CHECK`) | cc | Decide whether to fail closed; it is documented as deliberate |
| **MODERATE: F3 `forbidden` is not enforced on the countersign route.** `api/_lib/countersign-endpoint.js:200` and `countersign.js:426` check the preparer by ROLE only, so with cremations forbidden an apprentice still gets a token and a director files it: 200 | hank | Consult the home apprentice policy at prepare and at settle, with an arm red before the fix |
| Question: may an apprentice prepare a cremation under an EMPTY F3? b18 D2 says yes; the F3 default comment says no | **Michael** | Decide |
| LOW: the countersign token's spender is not bound | hank | Bind it, or record why not |
| `api/sd-data-leg-session-gate.test.js` 19/1: it anchors the pre-b56 `sdnData` signature | hank | Re-anchor to the `extraBody` form (`sairnlegacy.html:1631`) |
| rollup suite: retargeting the sidebar while `// nav('rollup')` sits in a JS comment is ACCEPTED 18/18; the read as dead code is accepted; hidden markup is accepted | cody | Assert sb-rollup's OWN onclick; prove the read is reachable |
| LOW: `api/bridge.js` header vs `KNOWN_ACTIONS` has no drift guard | hank | Optional one-line arm |
| `db/schema_snapshot.json` is 200.6h old; freshness exits 1 | **Michael** | Run `sql/schema_snapshot_query.sql`, then `python tools/load_schema_snapshot.py --write` |
| **CORRECTION:** my bld_bids verdict says `a4de92258` "carries its own obligation". **It does not.** The gate refused `--open`: no Tier A name sits on a changed line | cody | Review `a4de92258` anyway. Is SESSION_FLAG_ARG too strict for a legitimate refactor? |
| 4 tests/ overrides declared for fourth in `docs/sairn-path-manifest.json` (`_b68_added_three_test_files_for_fourth`) | cody | Review the arms, then remove those override lines |

Status-board notes FOR HANK and FOR CC carry the two main findings.

## 4. OPEN (carried from b67 §8 unless marked NEW)

| # | open item | owner | exact next step |
|---|---|---|---|
| 1 | Mechanical SQL not run | Michael | Run `sql/sairnmechanical_jobs_invoices_inspections_schema.sql`, then save and read back one job, one invoice and one inspection on MECH-AUDIT-2026 |
| 3 | Mech: no re-entrancy guard on `mechJobSave`, `mechInvoiceSave`, `mechInspectionSave` | fourth or cody | After cody releases `sairnmechanical`, use the `046e3f4f7` pattern, fixture-first |
| 4 | Mech: invoice numbers are per device, not per licence | fourth | Design a server counter, or a collision check on hydrate |
| 5 | H1 #1713, #1754 and #1779 have no closure entry | hover H1 | Auditor's to write |
| 6 | PIN files in the b65 scratchpad | Michael | Move them to the password manager; the path is in b67 §8 #6 |
| 7 | `SV-AUDIT-2026` is not in `KNOWN_AUDIT_KEYS` | cc | `tools/audit_licence.py` |
| 8 | Claim matcher self-matches "files fix" | cc | `tools/sairn_claim.py` |
| 9 | Deny hook refuses `sh -n .githooks/pre-push` | cc | Exempt read-only syntax checks |
| 10, 11 | Orphan scrutiny rows; install_git_hooks / `--supersede` | cc | `docs/2026-10-28-fourth-b62-root-causes.md` §1–3 |
| 12 | staging_discipline fixture | cody | Stage by name in `push_retry.py`'s selftest |
| 13 | Vet: the register is rewritten in place | fourth | `sv_controlled` append-only; this needs a row-identity decision |
| 14 | Vet: no countersign call | fourth | Wire `api/sv-witness.js` countersign into the app |
| 16 | Build: the lien waiver does not gate payment | Michael decides | If yes, a server check before `saveChk()` |
| 17 | Grounds: quote lines lose their text; no pesticide record | fourth | Fix the `saveQuote()` parse; the pesticide record is a product decision |
| 19 | About 10 b49 probe visits read unreviewed | probe-residue cleaner | Review or remove them |
| 20 | Allow rule `push_timeout_guard.py --live-drive` | Michael | Optional |
| 21 NEW | Finish the known-red whole-register re-drive | fourth | `python tools/red_suite_register_check.py`, in the background (more than 2h). Move any RECOVERED entry the way b66 moved capa |
| 22 NEW | Local branch `b67-mech` has 2 commits that are NOT patch-equivalent to main (`3226e4c30`, `413302d6e`; probably superseded by their rebased twins) | fourth | Confirm, then `git branch -D b67-mech`. Not deleted, because it was not proven redundant |
| 23 NEW | Falsy-zero money saves (`Number(v) \|\| null`) and readers with no writer, elsewhere | anyone | Sweep; both are recurrence-open in the register |

## 5. CLAIMS

`fourth` held `sairnbuild` and `sairncash` this batch. **Both are released** (`fb35ee324`, `cd3c28c59`).
