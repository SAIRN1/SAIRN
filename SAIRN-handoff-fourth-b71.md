# HANDOFF — fourth / ted, batch b71, 2026-10-30

**READ THIS FILE ONLY.** It is the whole state.

- **All five items are done.** Every fix below is cited by commit hash, not line number (item 4's convention).
- Both claims are released. Nothing is held locally.

**Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\83c60d05-1589-4389-a5cf-cd99265bab76.jsonl`

## 1. STATE — every b71 commit, with its own ancestor check

Run after `git fetch`, against **origin/main = `f50758d13f5e`**. Each row is the literal command and its exit code (0 = on origin/main).

| commit | subject | check | result |
|---|---|---|---|
| `f50758d13` | chore(claims): fourth releases sairngrounds | `git merge-base --is-ancestor f50758d13 origin/main` | exit 0 |
| `f55400f2b` | chore(claims): fourth releases stonedesk | `git merge-base --is-ancestor f55400f2b origin/main` | exit 0 |
| `0e1eb7c01` | chore(fourth b71): gate scrutiny rows | `git merge-base --is-ancestor 0e1eb7c01 origin/main` | exit 0 |
| `0eea0a294` | register+tier-a(fourth b71): records for c178ee514 and 958131e3a; review obligation | `git merge-base --is-ancestor 0eea0a294 origin/main` | exit 0 |
| `79aa5607a` | fix(stonedesk, fourth b71): every fourth-owned presence FAIL closed -- M1, E1-E4, I1-I3, X | `git merge-base --is-ancestor 79aa5607a origin/main` | exit 0 |
| `3d695069c` | fix(sairngrounds, fourth b71): grdData sends app_id -- G-1, migrate decision "yes" applied | `git merge-base --is-ancestor 3d695069c origin/main` | exit 0 |
| `76d05b432` | chore(claims): fourth claims stonedesk | `git merge-base --is-ancestor 76d05b432 origin/main` | exit 0 |
| `dd3ec4dfd` | chore(claims): fourth claims sairngrounds | `git merge-base --is-ancestor dd3ec4dfd origin/main` | exit 0 |

**Rebase note.** The fixes were rebased before landing:
- the StoneDesk fix was `958131e3a` and is now **`79aa5607a`**;
- G-1 was `c178ee514` and is now **`3d695069c`**.

The register citations were re-seated by `push_retry`.

**Live checks (measured):**
- `stonedesk.html` is byte-identical to origin/main and carries the b71 markers.
- `sairngrounds.html` is byte-identical and carries `app_id: APP_ID, payload: payload`.

## 2. DISPATCH ITEMS

1. **F3 live drive on LEG-AUDIT-2026: P1 PASS, P4 PASS, P8 PASS.**
   - The owner logged in with the PIN Michael gave in chat; I added B71-DIR (director) and B71-APP (apprentice).
   - **P1**, empty F3: 403 `APPRENTICE_NOT_CLEARED`, no token.
   - **P4**, F3 cleared, no supervisor: 403 `SUPERVISOR_REQUIRED`, no token.
   - **P8**, F3 cleared, B71-DIR named: 200, token minted.
   - Teardown: F3 restored to `[]` and read back.
   - The evidence and residue list (committed in `79aa5607a`) are in `docs/live-residue/2026-10-30-fourth-b71-f3-live-drive.json`.
   - **Residue:** one unspent token (10-minute expiry). B71-DIR and B71-APP were **left active** for future drives.
   - **The PINs are in the fourth scratchpad** (`leg-audit-*.pin`), never in the repo. Michael should move them to the password manager.
   - Correction to the dispatch: before this batch only the owner existed on LEG-AUDIT-2026 (measured). The director and apprentice were not bootstrapped.
2. **StoneDesk M1, E1–E4, I1–I3, X1–X3: all PASS** (`79aa5607a`).
   - cc's `tools/stonedesk_presence_stress.py` gives **19 PASS, 7 CONTROL-OK**. The only FAILs left are T1a/T1b/T1d (hank's api).
   - **E1/E2 (signature):** no pad refuses, and at least 3 pixels of real ink are required.
   - **E3:** a shown total that disagrees with the calculated one refuses.
   - **E4:** a name matching two customers marks neither.
   - **I1:** a deposit above the invoice amount refuses.
   - **I2:** Paid is announced only after a successful save.
   - **I3:** a deposit request clears the stale deposit field.
   - **X1:** YTD sums this year only.
   - **X2:** a rate outside 0–30% refuses.
   - **X3:** the 1099 tile shows `--`.
   - **M1:** a blank slab cost claims no margin.
   - **Tests:**
     - `tests/stonedesk_presence_fixes_b69.js` **arm 11** gates on the tool's verdict list: 11/0.
     - `invoice_panel_kpis` and `stonedesk_save_reentry`: exit 0.
     - `sd_tax_money_coercion` keeps its **one pre-existing** failure and gained no new one. My first X1 version broke two of its arms; I re-wrote it as a one-line fold.
3. **G-1, migrate (`3d695069c`).**
   - `grdData` now sends `app_id: APP_ID`.
   - **Migration measured read-only: 0 rows to move.**
     - `rt_routes`: 0 rows.
     - `ai_memories`: 0 grounds rows.
     - The profile, render-usage and shared-knowledge tables are keyed by licence with no app column.
     - `employees`: all `sairnbiz`.
   - `key_collision_check`: exit 1 before and after, **output byte-identical**. Its one unacknowledged collision, `stonedesk_quote_history`, is pre-existing.
   - `sairn_field_scope_check`: **38/38 clean** before and after.
   - Grounds suites and `b76-shared-deleted-row-session-app`: exit 0. **Zero regression.**
4. **Methodology:** every fix is cited by commit hash (§1 and §2).
5. **L3a still FAILs by design, measured after the b71 fixes.**
   - `tools/sairnlegacy_presence_stress.py`: L3a FAIL, L3b PASS, L3e PASS, L3c control OK.
   - `sairnlegacy_declinability`: 31/0, so C2 holds.
6. Handoff, then report, then push.

## 3. OPEN — exact next steps

| # | item | owner | next step |
|---|---|---|---|
| 1 | PINs for LEG-AUDIT-2026 (owner given in chat; director and apprentice generated) in the fourth scratchpad | Michael | Move them to the password manager and delete the files |
| 2 | StoneDesk T1a/T1b/T1d (api) | hank | Index row `SDP-PRESENCE-FOURTH-B69` |
| 3 | SAIRNlegacy L1/L2 (api) | hank | Index row `LGP-PRESENCE-FOURTH-B69` |
| 4 | Update both index rows: E/I/M/X are now closed by `79aa5607a` | fourth | Next batch, with a fresh fetch |
| 5 | Carried from b70 §3 | as listed there | Unchanged |
