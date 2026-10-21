# HANDOFF — fourth / ted, batch b46, 2026-10-21

**READ THIS FILE ONLY.** It is the whole state. **5 of 6 landed; 1 is
committed but held locally behind a Tier A review obligation that I cannot
record.** No force, no skip. Wrapped at **~80.5% real context**, at a safe
point.

**THE ONE THING TO READ FIRST: the geocoding commit (`53f62b866`) is NOT on
origin.** The push gate refuses it with *"Tier A code changed with no
recorded review obligation — rt_routes, stonedesk.html"*. Recording one means
writing `docs/tier-a-reviews.json`, and **cc holds that file**. I did not
skip the gate. I pushed the Z8/Z9 commit on its own as a prefix
(`37b5dc630`). The geocoding commit, a scrutiny-flags commit and this
batch's deliverables commit sit on top of it, locally.

**EXACT NEXT STEP:** when cc releases `docs/tier-a-reviews.json`, run
`python tools/tier_a_review_gate.py --open "fourth b46: Field Map geocode
(api/route-map.js action:'geocode', stonedesk.html coordinate cache +
attach)"`, commit that file, then land with
`scratchpad/b45/land.sh`.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fc1f8565-6013-48a4-b66b-d27902506016.jsonl`

**Working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fc1f8565-6013-48a4-b66b-d27902506016\scratchpad\b46\`
- `agent_biz\drive_z8z9.py`: 58 arms;
- `agent_geo\drive_geo.py`: 38 arms;
- `agent_geo\geo_server.test.js`.

## 1. STATE

| item | sha | state |
|---|---|---|
| 1 Field Map geocoding (Geocoding API, existing Maps key) | `53f62b866` | **LOCAL — held (Tier A)** |
| 2 sairnbiz Z8/Z9 | `37b5dc630` | **on origin, live** |
| 3 permission fix (`fix-deny.ps1`) | n/a (local settings) | **done — 8 deny entries** |
| 4 context discipline | — | applied this batch |
| 5 concept lines | in commits and code comments | done |
| 6 push | Z8/Z9 landed; geocode held | **partial, by the gate** |

**Live:**
- the Z8/Z9 code is deployed (`sbPayLine` is in the served page);
- Z7 9/9 on live;
- Z8/Z9 is 58/58 locally.

## 2. WHAT WAS BUILT

- **Geocoding** is an `action:'geocode'` mode on `api/route-map.js`.
  - It reuses that file's gate and its `GOOGLE_MAPS_API_KEY`.
  - Each call takes up to 25 addresses. Each comes back as a coordinate or a
    named failure, never 0,0 and never a guess.
  - The client caches real fixes in `sd_fm_geocode`, attaches lat/lng where
    known, and says how many stops had no coordinates.
  - Tests: RED 10/38 → GREEN 38/38, 4/4 mutation controls killed.
  - `api/route-map.js` was added to fourth's `assigned_overrides`.
  - **Open decision:** `partial_match` is treated as no coordinate. Allowing
    it is a one-line change.
- **Z8/Z9:**
  - each pay run gets per-employee lines through `sbWeekPay()`;
  - each line carries its pay period and pay date (516.2(a)(8)–(12));
  - withholding and net pay read "not computed";
  - home address, DOB with an "under 19" badge, and a rate history, with
    `sbRateForWeek()` pricing each week at its own rate;
  - **sync was deliberately not extended**, because the shared `employees`
    row is readable by StoneDesk managers.
  - Tests: RED 6/58 → GREEN 58/58; all 18 sairnbiz suites pass.
  - `tests/sairnbiz_preview_fixes.js` was added to fourth's
    `assigned_overrides`.
- **Permission fix:** the first run used `-File`, which joined all eight
  entries into one malformed rule. I re-ran it with array syntax and removed
  the malformed entry. The file now has exactly the 8 requested entries.

## 3. OPEN — NEXT STEPS

1. **Land the geocode** once cc releases `tier-a-reviews.json` (steps
   above). Then live-check it with a real StoneDesk login. Google was never
   called for real: the response was stubbed, and the key's quota is
   unmeasured.
2. **Z8 display:**
   - the pay-runs table does not show the lines or the pay date yet;
   - the payroll CSV is unchanged;
   - 516.2(a)(4) sex and (a)(5) workweek start are still not stored.
3. **Carried:**
   - cody: DEA keying, server `gfeMissing`, timesheet day seven;
   - cc: Tier A review on `rt_routes` (b44);
   - review fourth's `assigned_overrides` (5 test files plus
     `api/route-map.js`).

## 4. CLAIMS

**`fourth`: claim LEFT ACTIVE on purpose.** Releasing would push HEAD, which carries the held geocode commit the Tier A gate refuses. The active claim also protects `stonedesk.html` and `api/route-map.js` while that commit waits. Release it after the geocode lands. The geocode commit is local
only, so the next session should re-claim `stonedesk.html` and
`api/route-map.js` before landing it.
