# SAIRN handoff — hank b45 — 2026-10-21

**Subject:** SAIRNlegacy `leg_settings` — the owner's F2/F3 write path (routed from cody b40). Built, pushed, live.
Firebase-admin upgrade HELD (cc's active claim). Written before the report, nothing half-finished.

## 1. PUSHED STATE
- `38b2b5069` feat(sairnlegacy) — `api/sd-data.js`, `api/_resources/sairnlegacy.js`,
  `api/b45-leg-settings-owner-write.test.js`, `api/b22-funeral-f1-f2-f3-wiring.test.js` (D2 re-aimed),
  `tests/sairnlegacy_reservation_lock.js` (declared in `docs/sairn-path-manifest.json`).
- `f03aeb65d` Tier A obligation (cites `38b2b5069` on origin) + regenerated MASTER-PLAN / traceability.
- Both on `origin/main`, landed on the first attempt. **NOT FORCED.** This deliverables commit follows.
- **Live:** `POST /api/sd-data` `leg_settings` read with licence `LEG-PINNACLE-2026` and no session →
  **401 NO_SESSION** (the branch is reached); an unregistered `leg_` name → **400**. No session was used; an owner
  read/write was not driven live.

## 2. CLAIMS HELD
None (released at the end of the batch). The claim check BLOCKED on fourth b51 by app name (sairnlegacy); fourth's
FILES are `sairnlegacy.html` and a11y tests, plus the shared path manifest — proceeded per PR §4.3.

## 3. THE ITEMS
**1–2. leg_settings — concept:** *a home's F2/F3 settings are set by its OWNER alone, and only as the values
decide()'s own normalisers would produce; anything a normaliser would silently narrow at read time is REFUSED at
write time, so what the owner saved is exactly what decide() enforces.*
- Own branch before `LEG_RESOURCES` (table `sairnlegacy_settings`, one row/licence, no `data` column) — **not** in
  `LEG_RESOURCES`/`LEG_ROLE_MATRIX`, because the role-matrix suite's A2 requires every matrix row to be a
  dispatched data resource. Registered in `api/_resources/sairnlegacy.js`, which also puts it behind the
  active-credential pre-gate.
- Owner only (director/apprentice/livery 403). `livery_billing` ∈ `LEG_LIVERY_BILLING_VALUES`; `apprentice` lists
  must name real record types, not overlap, and `countersign` only names countersign-required resources;
  `presence_disclosure` boolean; `livery_grants` `{emp: {resource: true}}`, each resource `liveryGrantable()` under
  the MERGED billing (`leg_liveryvendors` never). Absent fields keep what's stored. Missing `livery_grants` column:
  a write naming grants → 503 NOT_PROVISIONED naming the SQL file; one that doesn't still saves.
- **Tests:** `api/b45-leg-settings-owner-write.test.js` **25/0** — who, read, 10 refusals, unprovisioned column,
  **E: decide() enforces exactly what was saved**, M: owner-check and grantability mutants each turn red.
  b22 23/0 (D2 was a tripwire saying "re-aim when leg_settings lands" — re-aimed), b29 21/0, leg-overlap 36/0,
  leg-role-matrix 37/0. `tests/sairnlegacy_reservation_lock.js`: loops scoped to the 36 data resources + an arm
  that leg_settings is the only exclusion; its **35/36 "no payload.id" arm is identical at HEAD (pre-existing)**.

**3. firebase-admin 12.7.0 → 13.10.0 — HELD.** cc's active b44 claim covers exactly this (package.json, lockfile,
mint test). Also: `npm install` is denied at user + project level (b39), so this clone could not update the
lockfile anyway. Not started; no mint test written to avoid duplicating cc.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | next step |
|---|---|---|
| L1 | audit-log row per settings write (schema says updated_by is not an audit trail) | hank, if dispatched |
| L2 | `sql/sairnlegacy_settings_livery_grants.sql` not run | Michael: run it; until then grants writes answer 503 |
| L3 | no owner UI in `sairnlegacy.html` calls `leg_settings` | fourth (html) |
| L4 | owner read/write not driven live (needs a SAIRNlegacy owner session) | Michael / whoever has one |
| T1 | Tier A review of `38b2b5069` | cc |
| F1 | firebase-admin upgrade | cc b44 (claimed) |
| R1 | `tests/sairnlegacy_reservation_lock.js` 35/36 no-id arm, pre-existing | cody |

## 5. TRANSCRIPT
 C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
