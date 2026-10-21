# SAIRN handoff — cody b33 (2026-10-20)

Four items. **The sweep found four LIVE inverted projections and fixed them.**
**Item 3's premise was wrong: the "eight still-open defects" are cc's b29, not
mine** — reported in full, none fixed (the instruction was to report).

| Item | State |
|---|---|
| 1. one-line concept before the scan | **DONE** — notes §1 and the test header, written before the scan ran |
| 2. sweep for inverted `Object.assign(columns, blob)` | **DONE — 4 live sites fixed, 12-arm test, 5 red under ablation** |
| 3. report "my b29 eight defects" | **DONE — they are cc's; 5 of 8 are routed to cody and ALL FIVE are still open at HEAD** |
| 4. push | see the report for the verified remote state |

## 1. Concept (stated before the scan)

In `Object.assign(a, b)` the later source wins, so a projection with the
authoritative columns first and a stored/client blob last lets the blob override
the server's value. The scan finds every keyed literal that precedes a
non-literal source; **each hit is classified by hand** — LIVE only if the blob
can actually carry the key, INERT if the write path allowlists or strips it.

## 2. The sweep

`docs/b33-sweep/projection_order_scan.py` (comment/string-masked, also catches
`{ key: v, ...blob }`; **10 fixtures lock the criteria and it refuses to run if
they fail**) and `docs/b33-sweep/strip_cross.py` (keys vs nearby `storedBlob`
strip lists). Over `api/` (190 files): 139 raw hits, 68 blob-projection hits in
`sd-data.js`, 18 whose keys were in no nearby strip list → read by hand.

**LIVE, fixed (columns/stamped fields now last):**
1. `alf_payer_rules` write response — client `payload.data` stored unstripped, so
   a sent `verified_by`/`state`/`rule_id` won in the response.
2. `alf_compliance_rules` write response — same.
3. `bld_draws` `wip` (+ the two `release_retainage` summaries) — generic writer
   stores the payload with no `draw_id` strip.
4. `sd-sub-data.js` `flattenProgressPhoto` — write strips identity and `qc_*`
   keys but **not `created_at`**, so a payload value overrode the column.

All response/read-side: **no stored column was ever wrong.**
`api/b33-projection-order-sweep.test.js` 12/0; ablating all four → A1, B1, C1,
D1, S1 red (7/5).

**INERT:** allowlisted blobs (`sd_public_shop`, `sd_quote_requests` public
intake, `sen_visits`, `rf_photos`), the roster simulation at `sd-data.js` ~2631,
and `sd-sub-data` jobs (strip list proved). **Not individually proved: ~50
`{ id: … } ← blob` sites classified INERT only because their keys sit inside a
`storedBlob` strip list within ±260 lines.** A runtime differential per resource
would prove them; it was not run. That is the biggest hole in this sweep.

**Not swept:** `*.html` (not a trust boundary); merges built in two statements
(`const out = {…}; Object.assign(out, blob)`).

## 3. Item 3 — the eight defects (cc's b29, `docs/2026-10-20-cc-b29-notes.md` §1)

Full table with HEAD line numbers is in `docs/2026-10-20-cody-b33-notes.md` §3.
Routed to **cody (all OPEN at HEAD, untouched):**
1. dental missing-table 503 names a file that does not create `dnt_gfe` /
   `dnt_recall_outreach` / `dnt_txplans` (`sd-data.js` ~18175).
2. `rf_prequal_documents` / `rf_bonding` write on a missing table → generic 502
   (`~10593`, `~10695`).
3. **`accounting.js` ~296: the revoke PATCH is never checked; the endpoint
   answers `tokens_discarded:true` regardless — false success on a credential
   discard.** Sharpest of the eight.
4. `accounting.js` `:143`/`:261`: any 400 reported as NOT_PROVISIONED.
5. `sd_quote_request_photos` written, never read (`stonedesk-public.js:317`).
Routed to hank (stonedesk.html style profile) and fourth (sairnroofing.html JHA,
sairnsenior.html contract) — **not re-verified; not my files.**

## 4. Gates this batch

- **Path scope:** `api/sd-sub-data.js` and the new test are foreign `api/`
  paths; declared in `assigned_overrides`, b32's list **replaced**.
- **Tier A:** obligation on `alf_payer_rules`, `alf_compliance_rules`, `bld_draws`
  OPENED and **assigned to cc** (point (d) names the ~50 heuristic sites).
- Push loop: `push_retry.py` git() still has a 120s subprocess bound; use a direct
  `git push` with a long timeout if it reports "timed out".

## 5. Verification

```
EXIT=0  node api/b33-projection-order-sweep.test.js     12/0
EXIT=0  python docs/b33-sweep/projection_order_scan.py --fixtures   10/10
EXIT=0  34 suites touching alf rules / bld_draws / progress_photos / sd-sub-data
        — 32 green; 2 red (api/sd-data-scp-licence-only.test.js 15/9,
        tests/sairnfreedom_auth_review_probe.js) IDENTICAL at HEAD (stash
        differential), both already in docs/known-red-suites.json
EXIT=0  node --check api/sd-data.js api/sd-sub-data.js
```

## 6. Next

- Decide whether to fix defects 1–5 (cody's). #3 first.
- Prove the ~50 heuristic sites with a per-resource runtime differential, or
  accept the strip-list proximity argument.
- H1 #1613/#1614 remains **HELD** for H1's own report (per Michael).
- cc: discharge the b33 obligation (and b31's `sc_claims`/`sc_dme`, b32's `rf_jobs`).
