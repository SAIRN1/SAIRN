# HANDOFF — fourth / ted, batch b47, 2026-10-21

**READ THIS FILE ONLY.** It is the whole state. **Everything is landed. No
force, no gate skip.** Wrapped at a safe point, with nothing half-done, at
**~22% real context**.

**THE ONE THING TO READ FIRST:** the geocode code is live and behaves
correctly, but **Google refuses the Maps key**:
- every address returns `UPSTREAM_STATUS` / `REQUEST_DENIED`;
- the Static Maps image mode on the same key gets HTTP 403.

So no real coordinate has ever come back. Fixing it is a Google Cloud
console action for Michael, not code:
- billing on for the project behind `GOOGLE_MAPS_API_KEY`;
- the Geocoding API and the Maps Static API enabled;
- key restrictions that allow server-side calls from Vercel.

After that, re-run `scratchpad/live_geo.py` (path below).

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210.jsonl`

**Working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210\scratchpad\`
- `drive_z8d.py [base]`: 37 Z8 display arms. Pass `https://sairn.vercel.app/` to drive live.
- `live_geo.py`: real login on SD-AUDIT-2026, real Google, read-only.
- `syn.py`: syntax checker for every script block.

## 1. STATE

| item | sha (origin) | state |
|---|---|---|
| 1 geocode landed | `769590aca` + Tier A `e7c9ba9e1` | live; cc discharged the review (`56418eb62`), SOUND |
| 1 live check | — | 4/9: login, deploy, gate and named failures OK; **Google REQUEST_DENIED** |
| 2 Z8 display + (a)(4)/(a)(5) | `170d75f8e` + Tier A `dbac30771` | **live 37/37** |
| 3 scrutiny rows | `b2539f7f7`, `9bcba36d3` | landed |
| 4 `.bak` | — | removed by Michael (the permission layer denied my `rm`) |
| 5 concept line | stated before code; in the commit and code comments | done |
| 6 push | all of the above | landed, no force |
| + geocode arms in repo (cc b34 gap) | `c04a3baaa`, manifest/docs `9bcba36d3` | 19/19, 4/4 mutants killed |

## 2. WHAT WAS BUILT

- **Z8 display** (`sairnbiz.html`).
  - The run table gains a Pay Date column and a per-run `<details>` with the
    lines the run **stored**. A rate change after a run does not re-price its
    lines; an arm and a mutant cover that.
  - A run from before b46 says "not recorded" for both lines and pay date.
  - The payroll CSV gains its line columns from `sbPayLine()`: period
    start/end, pay date (+ source), regular/OT hours, straight-time, OT
    premium, withholding/net "not computed", workweek start.
  - **No address or DOB goes into the CSV.**
- **(a)(5):** `sbWorkweekStart()` derives the day from `sbWeekStart()` →
  "Monday 00:00, local time, all employees". It is stamped on each run as
  `workweek_start`.
- **(a)(4):** the employee modal gains `esex` (blank = not recorded). It is
  device-only; an arm proves `syncEmps` does not send it.
- **Tests:** RED 5/30 → GREEN 37/37. Five mutants were killed; one survived
  at first and got its own arm. All 18 `tests/sairnbiz*.js` pass; b46 Z8/Z9
  58/58.
- **`api/b46-route-geocode.test.js`:**
  - the b46 18 arms plus cc's foreign-licence arm S19;
  - cc's 4 mutants run in-file, with an anchor-uniqueness guard (exit 2 COULD
    NOT RUN);
  - declared in fourth's `assigned_overrides`; MASTER-PLAN and the
    traceability matrix regenerated.

## 3. OPEN — NEXT STEPS

1. **Google key** (Michael, console). Then re-run `live_geo.py`; it expects
   2 located, 1 named failure.
2. **Tier A review owed by cc:** Z8 display (`employees`, sairnbiz.html),
   recorded at `dbac30771`.
3. **Vercel deployed out of order:** `e7c9ba9e1` went live at 15:14Z, then
   the OLDER `7a549be28` replaced it a minute later. Production briefly lost
   the geocode. Worth a platform row: "a clean push is not proof" now has a
   second shape.
4. **Carried:**
   - cody: DEA keying, server `gfeMissing`, timesheet day seven;
   - review fourth's `assigned_overrides` (5 tests, `api/route-map.js`,
     `api/b46-route-geocode.test.js`);
   - `partial_match` stays "no coordinate" (one-line change if wanted).

## 4. CLAIMS

`fourth` is released at wrap. No SQL this batch.
