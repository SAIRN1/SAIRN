# HANDOFF — fourth / ted, batch b45, 2026-10-20

**READ THIS FILE ONLY.** It is the whole state. **6 of 6 DONE**, all on
`origin/main` (0/0) and live-verified. No force, no blanket override. Wrapped
at **~77% real context**, inside the 85% hard wrap, with nothing
half-finished.

**THREE THINGS TO READ FIRST:**

1. **Payroll now prices overtime.**
   - A recorded 50-hour week at $20 used to enter payroll as **$1,000**
     while the timesheet showed **$1,100**.
   - One function, `sbWeekPay()`, now feeds payroll gross, annual gross, the
     timesheet panel and the CSV.
   - Three cody-owned suites pinned the old split and were updated, with the
     reasons quoted in place. The two new test files were added to fourth's
     `assigned_overrides`, beside the two b42 entries.
2. **Two items were implemented by delegated agents** (sairndental and the
   Field Map). Both edited under this session's claim and committed nothing.
   I re-ran their drivers, the prior drives and `node --check` before
   committing.
3. **Hank's b33 patch was applied as written** (the stonedesk and
   stonedesk-hr hunks). Its `sairn-path-manifest` hunk was not applied: it is
   hank's own assignment record and was not needed, because `*.html` is
   fourth's by the split.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fc1f8565-6013-48a4-b66b-d27902506016.jsonl`

**Working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fc1f8565-6013-48a4-b66b-d27902506016\scratchpad\b45\`
- `drive_z7.py`
- `agent_dental\driver.py` (`--dir orig` for the RED run, `--mutants`)
- `agent_route\drive_route.py`
- `add_defect.py`
- `land.sh`

**NO SQL THIS BATCH.**

## 1. PUSHED STATE

| | sha (as landed) |
|---|---|
| stonedesk + stonedesk-hr anti-framing (hank's patch) | `687d60360` |
| sairndental, 7 defects | `b5eef18d5` |
| sairnbiz Z7 | `ece9de35b` |
| Field Map lock / confirm / wording | `41f825dbb` |
| register records | `743eb3356`, `62444eecb`, plus the re-seat `d53dfdcc1` |
| scrutiny flags | `344ff09cd` |

**HEAD vs origin/main: 0 / 0.**

**Live on sairn.vercel.app:**
- Z7: **9/9**;
- framing: stonedesk and stonedesk-hr **2/2** protected;
- dental settle-order suite: **8/8**;
- route (b44 arms): **10/10**.

The new code is deployed in all four pages: `sbWeekPay`, `gfeSnapshot`,
`fmSavedText` and `sairn-antiframe`. The new dental and Field Map arms were
driven **locally** against the committed bytes.

**Landing incidents, both resolved without force:**
- **Two register rebase conflicts.** Each time I took upstream's register,
  skipped my record commit and re-added the records with the tool.
- **One GitHub connect timeout.** The retry succeeded.

## 2. CLAIMS

**`fourth`: released at the end of this batch.** `docs/tier-a-reviews.json`
was held by cc and was left out of the claim. No Tier A gate fired this
batch.

## 3. WHAT IS OPEN — EXACT NEXT STEP

1. **DEA keying (cody, `api/_lib/dental-credentials.js:241`).** Key DEA rows
   by provider plus registration number, per 21 CFR 1301.12(a).
2. **Server-side `gfeMissing` (`api/_lib/dental-gfe.js`).** Re-check against
   the issued snapshot rather than the live patient record. The dental CSV's
   DOB column should read the snapshot too.
3. **Field Map coordinates.** StoneDesk stores no latitude/longitude, so
   great-circle ordering stays unreachable. Doing anything here needs a
   geocoding decision (a provider and a key), which is not a code fix. Two
   smaller gaps: a lock is dropped if a job's installer or date changes, and
   the lock button was verified through generated HTML, not a real click.
4. **sairnbiz §6.4, Z8/Z9.** Per-employee pay lines and pay date/period
   (516.2(a)(8)–(12)); home address, DOB-if-under-19 and rate history.
5. **Remove fourth's `assigned_overrides` entries** (4 test files) once cody
   has reviewed the arms.
6. **Carried:**
   - timesheet day seven (cody, `api/sd-data.js:16290`);
   - `sairnSyncAll` 4xx (`stonedesk.html:19938`, now unclaimed);
   - cc owes the Tier A review on `rt_routes` (b44).

## 4. LEFT UNPROVEN

- **No StoneDesk login and no real dental tenant**, so all drives stub or
  intercept the server.
- **Chromium only.**
- **No legal review** of the GFE disclaimer wording.
