# HANDOFF — fourth / ted, batch b44, 2026-10-20

**READ THIS FILE ONLY.** It is the whole state. **6 of 6 DONE**, all on
`origin/main` (0/0), with the touched pages live-verified. No force, no
override. Wrapped at **~69% real context**, inside the 80% red flag, with
nothing half-finished.

**THREE THINGS TO READ FIRST:**

1. **The StoneDesk Field Map optimiser had never applied a single successful
   answer** since the b34 repoint.
   - `sdData()` returns `j.data`. The server answers `optimize` with no
     `data` key, so a 200 reordering stored nothing and the button said *"the
     server did not answer"*. Meanwhile the server had already written
     `optimized_at` for that run.
   - Fixed through the **named transport `sdDataEnvelope()`**, which is the
     route that `tests/stonedesk_bare_envelope_actions.js` prescribes instead
     of a second carve-out in `sdData()`. My first attempt was that carve-out;
     two cody suites failed on it, and I followed their design rather than
     editing them.
   - **A Tier A review obligation is recorded and assigned to cc**
     (`3c35dfdf`).
2. **SAIRNbiz's payroll gross pays overtime hours at the straight rate.**
   `sbGrossPerPeriod()` (`sairnbiz.html:3681`) treats a 50-hour week as
   50 × rate, while the timesheet panel applies 1.5× above the threshold. Two
   screens disagree on the same week's pay. Audit only this batch; Z7 in
   §6.4 of the sairnbiz audit is the exact fix.
3. **Two of the six items were already done when dispatched.** The sairnbiz
   worldwide audit existed (b41), so b44 added its US limb (§6). The
   satellites' resolved states could not be driven, because no StoneDesk shop
   has a published catalog and the dental demo slug has no bookable
   procedures. Both are stated as they are, not worked around.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fc1f8565-6013-48a4-b66b-d27902506016.jsonl`
(the same session as b41–b43)

**Working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fc1f8565-6013-48a4-b66b-d27902506016\scratchpad\b44\`
- **Drives, all re-runnable against a base URL:** `drive_sat.py`,
  `drive_b4.py`, `drive_route.py`, `drive_design_b41.py`.
- **Subagent evidence:** `agent_dental\`, `agent_biz\`, `agent_route\`.
- Also: `fix_*.py`, `add_defect.py`, `land.sh`.

**NO SQL THIS BATCH.**

---

## 1. COMMITTED / PUSHED STATE

| | sha | |
|---|---|---|
| satellites anti-framing | `7cce0d6d` (+ register `f0fbbd1c`) | item 1 |
| sairndesign B4 | `b3758e78` | item 2 |
| sairnbiz audit §6 (US limb) | `046bbdd3` | item 3 |
| sairndental correctness audit | `b952ae04` | item 4 |
| Field Map optimiser | `72dfaf5c` (+ register `bb2658ca`, Tier A obligation `3c35dfdf`) | item 5 |
| **HEAD vs origin/main** | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |

**Live on sairn.vercel.app:**
- optimiser **10/10**;
- B4 **28/28**;
- framing: **20 of 20** guarded pages hidden in both modes (16 apps plus 4
  satellites);
- satellites: **4/4** hidden with real parameters.

**Still clickable when framed: `stonedesk` and `stonedesk-hr`.** Hank has
released `stonedesk.html`; it was not in this batch's scope.

## 2. CLAIMS HELD

**`fourth`: released at the end of this batch.** Held:
- the 4 satellites, `sairndesign.html` and `stonedesk.html` (added once hank
  released it);
- the sairnbiz audit doc and the dental audit doc;
- the register and `docs/tier-a-reviews.json` (CLEAR when written);
- the deliverables.

`sairnbiz.html` and `sairndental.html` were **audit-only**, 0 commits.

## 3. ITEMS

- **1. Satellites.**
  - **Parameterisation concept:** use the identifier the owner actually hands
    out; a value counts as real only if the live API resolves it.
  - **Embed intent, checked first:** Booking Settings offers only a public
    link, and neither owner app has an embed snippet.
  - **RED:** with `?slug=verify-test-slug`, `sairndental-complaint` was
    clickable when framed.
  - **GREEN:** 4/4 hidden.
- **2. B4.**
  - **What it adds:** project occupancy, plus a dining/work surface type and
    top height on spec items.
  - **902.3:** checked per item; 28–34 in, both ends inclusive.
  - **226.1:** shown as N of M, needing at least ceil(5%) of items. Unknown
    heights make the result **not established** rather than met. Residential
    projects are out of scope; for employee-only projects, work surfaces are
    out but dining surfaces still count.
  - **Stated on screen:** the count is per item, while 226.1 counts seats.
- **3. sairnbiz US limb.**
  - 29 CFR 516.2(a)'s 12 required records mapped to the write sites.
  - Gaps: no home address, DOB, sex, stored workweek start, rate history,
    per-employee pay lines, or pay date/period.
  - Retention periods quoted (516.5, 516.6, 31.6001-1(e)(2)).
  - The payroll overtime defect (§6.1).
- **4. Dental audit.** 9 confirmed defects, most reproduced. Next steps are
  ordered in §4 of the doc.
- **5. Field Map optimiser.** **RED 5/10 → GREEN 10/10**, plus a permutation
  check on the order the server returns. Other findings are recorded, not
  fixed: `locked` is never sent, great-circle mode is unreachable without
  coordinates, the banner semantics for 0 vs null savings, and the
  mid-route pin in `routes.js`.

## 4. WHAT IS OPEN — EXACT NEXT STEP PER ITEM

1. **sairnbiz Z7, payroll OT premium** (`sairnbiz.html:3681`). Write one
   shared function computing `(t-ot)*rate + ot*rate*1.5` from the recorded
   week, and have `sbGrossPerPeriod`, `rTS` and the CSV all call it. Prove
   it with a 50-hour week.
2. **Dental, in order** (audit §4):
   1. appeal timeliness decided against `submitted_on`;
   2. GFE completeness checks the printed snapshot;
   3. the two GFE disclaimers;
   4. `cdStatusBadge` uses `revalidation_days`;
   5. the holiday sentence says *later*, and the 31-Dec observance is caught;
   6. DEA rows keyed per registration (cody, server side).
3. **stonedesk / stonedesk-hr anti-framing.** Insert the
   `scratchpad/b43/fix_frame.py` block below any CSP, remove the late LAYER 4
   buster (~`stonedesk.html:3122`), and prove it with `drive_frame.py
   --expect-protected=stonedesk,stonedesk-hr`.
4. **Field Map leftovers:**
   - `locked`: decide whether StoneDesk should send it, and add the UI if so;
   - send coordinates if great-circle mode should ever run;
   - confirm a manual press;
   - render a saving of 0 as "already optimal";
   - `routes.js` mid-route pin restart (shared module).
5. **Bare-envelope guard:** derive its `DATA_LESS` list from the endpoint
   instead of a hand list (cody's test file; routed, not edited).
6. **Satellites, resolved states:** seed procedure types for the demo slug,
   or publish a demo StoneDesk catalog, then re-drive. That is a data change
   for whoever owns the demo tenant.
7. **Carried:**
   - timesheet day seven (cody, `api/sd-data.js:16290`);
   - `sairnSyncAll` 4xx (stonedesk);
   - cc's Tier A obligations;
   - remove fourth's `assigned_overrides` entry once cody has reviewed.

## 5. LEFT UNPROVEN

- **No StoneDesk login was available**, so the optimiser was proven against
  the server's exact response shape via an intercepted endpoint, not against
  a live tenant.
- **The two audits are static or locally driven reads**, with no legal review.
- **Chromium only.**
