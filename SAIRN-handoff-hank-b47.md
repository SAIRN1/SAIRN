# SAIRN handoff — hank b47 — 2026-10-21

**Subject:** live verification of `audited:true` for SAIRNlegacy `leg_settings` now that
`sql/sairnlegacy_audit_log_settings_event.sql` has run. No code changed. Written before the report, nothing
half-finished.

## 1. PUSHED STATE
Only these three documents. **NOT FORCED.** Re-derive the tip after the push.

## 2. CLAIMS HELD
None.

## 3. THE ITEM
Same script as b46 (`tools/sairn_http.py`, demo licence `LEG-PINNACLE-2026`, published demo owner, PIN read from
`docs/2026-09-03-demo-credentials.md` and never printed): change one value, read back, restore the original.

| step | result |
|---|---|
| login | 200, role owner |
| read | 200, `saved:true`, `through_the_home`, `grants_supported:true` |
| write `direct_to_family` + grant `{b46-live-check-driver: {leg_dispatches: true}}` | 200 ok, **`audited:true`** |
| read back | `direct_to_family`, the grant, `updated_by: sairn-demo-owner` |
| restore original | 200 ok, **`audited:true`** |
| read after restore | `through_the_home`, `{}` — **matches the original** |

`audited:true` means the audit insert returned 2xx; the rows themselves were not read back — there is no read
path for `sairnlegacy_audit_log` from the API, and this batch did not query the database.

**Stale signal, not a defect:** `tools/audit_event_type_check.py` (hank-owned) still prints
`the LIVE CHECK rejects settings_changed`. Its "live" CHECK comes from `db/schema_snapshot.json`, last captured
**2026-10-21 06:58**, before the SQL ran. The tool states the snapshot is a point in time. It clears at the next
snapshot export (carried item B, Michael).

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | next step |
|---|---|---|
| B | schema snapshot re-export (clears the stale settings_changed finding) | Michael |
| T1 | Tier A review of `38b2b5069` (b45) | cc |
| U1 | owner UI for leg_settings | fourth |

## 5. TRANSCRIPT
 C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
