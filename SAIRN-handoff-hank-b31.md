# SAIRN handoff — hank b31 — 2026-10-20

**Subject:** the Sync All Apps button removed (Michael's decision), with a defect b29 missed found on the
way out — the button stamped "Last sync" on every click whatever the server said; and one SQL file that
creates three credential rows (two audit owners, one demo caregiver), written and guarded, **not run**.
Written before the report, with nothing half-finished. Notes: `docs/2026-10-20-hank-b31-notes.md`.

## 1. PUSHED STATE
Fix `6131e5a90`, derived docs + register `20b91e8c4`, register re-seat `2dc77b36e` — `origin/main` was
`2dc77b36e` at the last fetch, `0 ahead, 0 behind` (this handoff lands after it; re-derive the tip).
**NOT FORCED, ZERO gate overrides.** Two rebases moved the fix sha (`7e4195975` → `8ea00b19e` →
`6131e5a90`); the post-rewrite hook re-seated the register record each time and the pushed register now
cites `6131e5a90`, verified with `git show origin/main:docs/defect-density-register.json`.
**Live-verified on the deployed page:** no Sync All Apps button, no `window.sairnSyncAll`, no
`sairn-last-sync` element, no `full-sync` request; the CSV Export button is still there.

## 2. CLAIMS HELD
Mine (`hank`, b31), released at the end. cc still holds `tools/tooling_inventory.py` and `CLAUDE.md`.

## 3. THE ITEMS
3. **Concept (stated before the diff):** *a control that can never do what its label says is removed —
   not left to fail, and not "fixed" into a write nobody reads.*
1. **Sync button — REMOVED.** Button, "Last sync" element, `sairnSyncAll`, `sairnUpdateLastSync` and its
   on-load restore, and the `SAIRN_BRIDGE` constant only it used. **Found on the way:** the onclick was
   `sairnSyncAll();sairnUpdateLastSync()` — the second call stamped the time unconditionally, so b29's
   honest-failure fix never reached the screen. b29's live drive called the function, not the button.
   `api/b29-stonedesk-sync-honesty.test.js` section A now asserts the absence: 6 arms, each red against
   the pre-removal page; 10/0 overall. Register fed (one record, three factors).
2. **Credential SQL — WRITTEN, NOT RUN.** `sql/audit_owner_and_demo_caregiver_credentials_2026-10-20.sql`:
   platform `hashPin()` round-tripped through `verifyPin()`; PR 3.4 recoverability guard on each licence
   (`employee_auth_guard_check.py`: guarded 1, unguarded 0); a salt check proving each published PIN is
   the stored one; one transaction; read-only verify selects at the end. PINs are in the SQL header and
   the report, following `sql/sairnfreedom_demo_owner_credential_2026-10-13.sql`.
   **Assumption:** the "caregiver demo account" was placed on the DEMO licence `SEN-PINNACLE-2026`.
4. **Push:** §1.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | why | next step |
|---|---|---|---|
| A | **run the credential SQL** | I may not run it; no DB access | Michael: paste `sql/audit_owner_and_demo_caregiver_credentials_2026-10-20.sql` into the Supabase SQL editor; expect three `notice` lines and three verify rows, active |
| B | **straight-time-floor live proof** | needs A | `! SEN_LICENSE=SEN-AUDIT-2026 SEN_OWNER_PIN=<audit-owner PIN> SEN_CAREGIVER_PIN=<any 6-8 digits> python docs/2026-10-20-hank-b27-sen-straight-time-floor-live-probe.py` — the probe provisions `hank-b27-caregiver` itself. First server contact for that probe |
| C | **trust-lock live proof** | the probe signs in as `hank-b23-owner`, NOT `audit-owner` | either run it with the b23 owner PIN, or let the next batch make `OWNER_ID` an env override (`tools/law_trust_lock_live_probe.py` is in hank's `assigned_overrides`) so the new `audit-owner` PIN can drive it |
| D | `getBusinessContext()` reads the now-unwritten `stonedesk_last_sync` | no callers, so invisible | delete it, or drop the key |
| E | b29/b27 open lists | unchanged | `SAIRN-handoff-hank-b29.md`, `SAIRN-handoff-hank-b27.md` |

## 5. EVIDENCE
Live: deployed `/stonedesk` (§1). Offline: `b29-stonedesk-sync-honesty` 10/0 with each A-arm red against
the pre-removal page; `b21-bridge-unknown-action` 20/0; stonedesk 128 blocks 0 errors; credential guard
checker exit 0; hash round-trip true/false for all three. **Not covered:** the SQL has never executed.

## 6. TRANSCRIPT
    C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\8dd2a9db-f15f-4fee-9950-08bcb26892c0.jsonl
CONTEXT 58.4% of 1,000,000 -- 583,623 tokens, measured. Trigger was 85%, set as my red-flag threshold.

## 7. WHAT I GOT WRONG
b29's live verification drove `window.sairnSyncAll()` instead of clicking the button, and so reported a
fixed button that still stamped a sync time on every click. Recorded in the register as a detection factor.
