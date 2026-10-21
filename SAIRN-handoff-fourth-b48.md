# HANDOFF — fourth / ted, batch b48, 2026-10-21

**READ THIS FILE ONLY.** It is the whole state. **Everything is landed and
live. No force, no gate skip.** Wrapped at a safe point at **~32% real
context**.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210.jsonl`

**Working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210\scratchpad\`
- `drive_lock.py [root]`: Field Map, real clicks, 12 arms;
- `drive_gfecsv.py [root]`: dental export, 4 arms;
- `live_gfe.py`: live dental refusal check; refused writes only, nothing stored;
- `live_geo.py`: live geocode, 9 arms;
- `add_defect48.py`: the two register records.

## 1. STATE

| item | sha (origin) | state |
|---|---|---|
| geocode re-check after Michael's key fix | — | **live 9/9**: 2 located, nonsense → ZERO_RESULTS, Static Maps 200 |
| b45 status | ece9de35b / b5eef18d5 / 41f825dbb | overtime done; 7 of 9 dental done; lock/confirm/wording done |
| dental DEA keying | `b14228a45` | live (server) |
| dental GFE printed-copy check + export | `b14228a45` | **live 6/6** (real login, refused writes only) |
| Field Map lock follows the stop | `013d368cd` | live; page bytes = origin |
| Field Map real-click test | scratchpad `drive_lock.py` | 12/12 |
| register + overrides + docs | `c02d1efbd`, `f4e8222d7` | landed |

## 2. WHAT WAS BUILT

- **DEA.**
  - **Concept:** a registration is per number (21 CFR 1301.12(a)).
  - `latestByKey` now keys DEA rows by provider plus `deaKey(number)`, which is upper-cased with spaces and hyphens stripped.
- **GFE.**
  - **Concept:** an Issued estimate prints its frozen `patient_name`/`patient_dob`. So `dental-gfe.js` checks that printed copy **and** the server-side patient record.
  - The app's GFE export now reads `gfeSnapshot()`.
  - `api/b48-dental-dea-gfe.test.js`: RED 6/11 → GREEN 11/11, with 5 in-file mutants killed.
  - The `dental-gfe.test.js` fixture now carries the printed copy (14/14).
- **Field Map.**
  - **Concept:** a lock belongs to the stop. `fmLockedSet()` reads every order record, and the toggle clears the lock everywhere before setting it.
  - Tested with a real Playwright click on the rendered My Day card: RED 6/12 → GREEN 12/12, 2 mutants killed.
- **Regressions:**
  - b45 route: 33/33 behavioural arms. Its own "copy-through" mutant anchor no longer matches, because this fix rewrote that line; `drive_lock.py` covers it now.
  - b46 geocode: 38/38.

## 3. OPEN — NEXT STEPS

1. **Pre-existing reds, not mine (they fail the same way at HEAD):**
   - `tests/sairndental_ledger_export.js` and its `_mutation_control`;
   - `tests/sairndental_rollup_panel.js` ("panels, nav targets and sidebar ids are three identical sets").
2. **Still open on these fixes:**
   - a DEA row with no number keys as one per provider;
   - a re-typed DEA number leaves the old row live;
   - the server does not compare the printed copy to the live record;
   - a lock carried to a new day keeps its old index in the new route.
3. **Carried:**
   - cc owes the Tier A review of Z8 display (`dbac30771`);
   - review fourth's `assigned_overrides`, which now hold 10 entries.

## 4. CLAIMS

`fourth`: released at wrap. No SQL this batch.
