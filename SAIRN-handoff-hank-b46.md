# SAIRN handoff — hank b46 — 2026-10-21

**Subject:** audit-log write for SAIRNlegacy `leg_settings`, and a live owner read/write. Written before the
report, nothing half-finished.

## 1. PUSHED STATE
- `da7c0fc6d` feat(sairnlegacy) — `api/sd-data.js`, `api/b45-leg-settings-owner-write.test.js`,
  `sql/sairnlegacy_audit_log_settings_event.sql`. On `origin/main`, **NOT FORCED.**
- No Tier A obligation: `tools/tier_a_review_gate.py --open` answered that the change names no Tier A resource.
  The b45 obligation on `38b2b5069` is still open for cc.
- This deliverables commit follows.

## 2. CLAIMS HELD
None (released at the end of the batch).

## 3. THE ITEMS
**Audit write — concept:** *every settings change that is actually SAVED writes one row to
`sairnlegacy_audit_log` naming the owner, the time and each changed field's before → after; a failed log write
never undoes the save but the answer says `audited:false`; a refused or no-op write logs nothing (`audited:null`).*
- After the upsert, the normalised before/after of `livery_billing`, `apprentice`, `livery_grants` is diffed; one
  `writeAuditLog()` call, `event_type: 'settings_changed'`, `detail: {resource, first_save, changed}`.
- **The existing migration's CHECK does not admit `settings_changed`**, so
  `sql/sairnlegacy_audit_log_settings_event.sql` adds it (restating the five existing values) with a confirm query.
  **NOT RUN.** Until it runs every save answers `audited:false` — measured live below — and
  `tools/audit_event_type_check.py` reports `settings_changed` as rejected by the live CHECK, which is correct.
- Test `api/b45-leg-settings-owner-write.test.js` **32/0**: A1 row content (owner, licence, field from→to,
  audited:true), A2 refused write / A5 refused role / A3 no-op → no row, A4 failed insert keeps the save
  (audited:false), A6 the SQL lists all six values; **M3** a stub that claims success turns A1 red. Leg suites:
  b22 23/0, b29 21/0, leg-overlap 36/0, leg-role-matrix 37/0.

**Live owner read/write — UNVERIFIED note from b45, now driven.** Demo licence `LEG-PINNACLE-2026`, published
demo owner (`docs/2026-09-03-demo-credentials.md`; PIN read from the file, never printed), via `tools/sairn_http.py`:
| step | result |
|---|---|
| login | 200, role owner |
| read | 200, `saved:true`, `through_the_home`, `grants_supported:true` (grants SQL is live) |
| write `direct_to_family` + a grant `{b46-live-check-driver: {leg_dispatches: true}}` | **200 ok** (no 503), `audited:false` |
| read back | `direct_to_family`, the grant, `updated_by: sairn-demo-owner` |
| restore original | 200 ok; read → `through_the_home`, `{}` — **matches the original** |
The first attempt ran against the pre-b46 deploy (no `audited` key), wrote and restored the same way; the loop
retried until the b46 deploy answered. **The settings row exists after this check** (values = original); if it did
not exist before the first attempt, it now does, with default-equivalent values.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | next step |
|---|---|---|
| A1 | `settings_changed` refused by the live CHECK | Michael: run `sql/sairnlegacy_audit_log_settings_event.sql`; then a changing save answers `audited:true` |
| T1 | Tier A review of `38b2b5069` (b45) | cc |
| U1 | owner UI for leg_settings | fourth (routed) |
| R1 | `tests/sairnlegacy_reservation_lock.js` 35/36 no-id arm, pre-existing | cody |
| F1 | firebase-admin upgrade | cc b44 |

## 5. TRANSCRIPT
 C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
