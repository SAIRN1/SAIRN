# SAIRN handoff — hank b35 — 2026-10-20

**Subject:** b34 §4 G and H, item C confirmed landed by fourth (not duplicated), and the exact snapshot
format for Michael's re-export. Written before the report, with nothing half-finished.

## 1. PUSHED STATE
`eb36a5b62` (SEN-AUDIT-2026 key + toggle test moved), gate rows, `ea60be266` derived docs.
`origin/main` = `ea60be266`, `0 ahead, 0 behind` before this handoff (re-derive the tip).
**NOT FORCED, ZERO overrides.** One refusal (derived-docs: MASTER-PLAN stale after the test move), fixed
by regenerating.

## 2. CLAIMS HELD
Mine (`hank`, b35), released at the end. `tools/audit_licence.py` added to hank's `assigned_overrides`
(claim check CLEAR before editing).

## 3. THE ITEMS
**Concept (H, before the code):** *a key joins the known-audit list only with the measurement that proved
it exists.*
* **G — re-export the snapshot: NOT DOABLE BY ME** (needs the database). The committed snapshot is still
  `2026-10-20 13:13:22 UTC`, before the widening, so `audit_event_type_check.py` still exits 1. Format below.
* **H — DONE.** `SEN-AUDIT-2026` added to `KNOWN_AUDIT_KEYS` with its dated measurement (b28 check_license
  200; the b34 probe run). The probe's "audit-SHAPED but not known" NOTE is gone.
* **C — CONFIRMED LANDED BY FOURTH, not duplicated.** fourth b45 `687d60360` applied the whole b33 patch
  (stonedesk.html +67, stonedesk-hr.html +11). Live: both pages carry the anti-framing block, LAYER 4 is
  gone, `/stonedesk` carries the map toggle. The one piece fourth left, the held test, I moved to
  `api/b33-fieldmap-toggle.test.js` — 8/0 against the landed page.

## 4. THE SNAPSHOT, FOR MICHAEL'S RE-EXPORT
* **Path:** `db/schema_snapshot.json` (repo root), committed.
* **Built by:** running `sql/schema_snapshot_query.sql` (the current repo copy) in the Supabase SQL
  editor. It returns ONE JSON cell; save that cell's text as a file, then
  `python tools/load_schema_snapshot.py <file>` (read the delta), then `... <file> --write`, then commit.
  The loader refuses a capture that lost tables or is not newer. Same path cc used for the 13:13 capture
  (`b2b02bbd0`). `sql/schema_snapshot_constraints_query.sql` emits only `_constraints` if that is all
  that is needed.
* **Format** (one JSON object):
  * `"_generated_at"`: `now()::text` — e.g. `"2026-10-20 13:13:22.083606+00"`.
  * `"_constraints"`: `{ "<table>": { "<constraint_name>": "<pg_get_constraintdef text>" } }`, public
    schema, CHECK constraints only. The query emits plain text; the 13:13 capture holds base64 of the same
    text. `audit_event_type_check.py` reads either.
  * every other key: `"<table>": ["<column>", ...]`.
* **Success check:** `python tools/audit_event_type_check.py` exits 0 with "every emitted value is in the
  live CHECK".

## 5. OPEN, AND THE EXACT NEXT STEP
| # | open | next step |
|---|---|---|
| G | snapshot predates the widening | Michael re-exports per §4 |
| D | Static Maps on `GOOGLE_MAPS_API_KEY` | Michael; until then the image answers 502 and the link works |
| F | image drawn live with a session | after D: open Field Map signed in, tick "Show map image" |

## 6. TRANSCRIPT
    C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\8dd2a9db-f15f-4fee-9950-08bcb26892c0.jsonl
CONTEXT 77.6% of 1,000,000 -- 775,897 tokens, measured. Trigger 85%.
