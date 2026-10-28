# SAIRN handoff: cc, batch b63, 2026-10-28

**All six items are closed.**
- `--live` now covers all four field-scope rules: **22/22 role arms, exit 0**.
- Every live block was shown to FAIL against a known-bad handler, through the
  same live code path.

**Landed state:**
- Landed `dcdba0e6`. The clone reads 0 0 against origin.
- No `--force`, no override, no skip.

| | |
|---|---|
| Claims held | `field-scope` (b63, released with this handoff) |
| Context | see the digest's CONTEXT line (measured) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\332ab89b-94aa-4880-931e-d17413636dfc.jsonl` |

## 1. Item 1: live blocks for sen_settings, rf_settings and alf_facility

**Each rule now has a `live` block in `tools/field_scope_rules.json`:**

| Rule | Licence | Auth endpoint |
|---|---|---|
| `sen_settings` | SEN-AUDIT-0002 | `/api/sen-auth` |
| `rf_settings` | RF-AUDIT-0002 | `/api/rf-auth` |
| `alf_facility` | ALF-AUDIT-0002 | `/api/alf-auth` |

**The judge changed.** b62's live mode compared item KEYS against field names,
and that cannot read a nested shape like sen_settings' `{setting_key, value}`.
- `--live` now uses **the same marker judge as the handler mode**.
- The audit licence holds the rule's own fixture rows, and their marker values
  are generated from the checker's `seed()`.
- A leak is the same `LEAK` line in both modes.
- `updated_at` is timestamptz and cannot hold `FSMK…`, so its marker is a
  distinctive 2001-02-03 instant, written as `{"marker": …}`.

**Live run, `--live --env-file scratchpad\fieldscope.env`, against
sairn.vercel.app.** Output is in `scratchpad\live63.txt`.

| Rule | Privileged roles | Restricted roles |
|---|---|---|
| sen_caregivers | owner, billing: 22/22 markers | scheduler, coordinator: 16/22; caregiver: 8/22 (its own row only) |
| sen_settings | owner, billing: 12/12 | scheduler, coordinator, caregiver: 3/12 (state, aggregator, agency name) |
| rf_settings | owner, admin: 10/10 | estimator, foreman, crew: 2/10 (damage_threshold value and source) |
| alf_facility | owner, billing: 15/15 | nursing, med_aide, caregiver, activities, office_manager: 8/15 (no rate card) |

Every arm received exactly its declaration. **22 arms, exit 0.**

## 2. Item 2: credentials provisioned and RUN

**The file:** `sql/field_scope_live_fixtures_2026-10-28.sql`.
- It mints RF-AUDIT-0002 (sairnroofing) and ALF-AUDIT-0002 (sairncare), with one
  credential per role.
- It writes every rule's fixture rows from `seed()`.
- b62's two sen_caregivers rows are UPDATED into marker rows, so SEN-AUDIT-0002
  still holds exactly 2.

**Why new licences.** The judge is closed-world, so every row a role can read
must be known. Upserting a marker `damage_threshold` onto RF-AUDIT-2026 would
also overwrite the value the roofing probes run against.

**How it was written:**
- PINs come from `hashPin()`; `verifyPin()` is true for each PIN and false for
  `00000000`, all twelve.
- PR 3.4 guard, a salt check on every credential, and a count guard on every
  fixture table.
- `employee_auth_guard_check`: 1 guarded, 0 unguarded. `sql_preflight`: 0
  findings.

**How it was run:**
1. **Rehearsed** in an always-rollback transaction: every guard passed. A read
   afterwards showed nothing persisted.
   - The rehearsal used a condensed but equivalent guard block.
   - The real run then executed the file's exact guards.
2. **Run** and read back:
   - both licences active;
   - RF 5/5 and ALF 7/7 credentials active;
   - fixtures exactly 2 / 3 / 3 / 1.

**The new credentials** (SEN-AUDIT-0002's five are unchanged from b62):

| Licence | Employee ID | Role | PIN |
|---|---|---|---|
| RF-AUDIT-0002 | fs-owner | owner | 28528653 |
| RF-AUDIT-0002 | fs-admin | admin | 65138684 |
| RF-AUDIT-0002 | fs-estimator | estimator | 61452245 |
| RF-AUDIT-0002 | fs-foreman | foreman | 32313368 |
| RF-AUDIT-0002 | fs-crew | crew | 20734995 |
| ALF-AUDIT-0002 | fs-owner | owner | 86576619 |
| ALF-AUDIT-0002 | fs-billing | billing | 78310947 |
| ALF-AUDIT-0002 | fs-nursing | nursing | 57096965 |
| ALF-AUDIT-0002 | fs-med-aide | med_aide | 33024433 |
| ALF-AUDIT-0002 | fs-caregiver | caregiver | 86286640 |
| ALF-AUDIT-0002 | fs-activities | activities | 47801717 |
| ALF-AUDIT-0002 | fs-office-manager | office_manager | 17478561 |

- The same table is in the SQL header. Audit licences only. **Rotate the PINs
  if one of these licences ever holds a real record.**
- Both keys are added to `KNOWN_AUDIT_KEYS`.
- `scratchpad\fieldscope.env` holds all 37 `*_EMP`/`*_PIN`/licence variables for
  `--env-file`. It is not committed.

## 3. Item 3: is the registry schema ready for hank? YES, and it is proven, not asserted

**New: `--validate`.** It is a strict schema check, and every run now applies it
first. It catches:
- unknown keys at the rule, role and live levels;
- a missing required key;
- a duplicate id or tag;
- a `see` naming an undeclared tag or set;
- a role spec without exactly one of `see` / `refused`;
- a marker literal used twice.

**Locked:**
- The blind lock is 16 → **20 arms**. It caught the fixture rule itself lacking
  `declared_from` on the first run, and that was fixed.
- Run on the current registry, it found a real stale key, `owner_field`.

**Format trial for `alf_mar`.** I built it in scratch, not committed. It was
read off the branch, so it is **NOT a design**.
- It has self and peer rows on `assigned_employee_id`, a timestamp marker on
  `created_at`, owner/nursing `see` all, med_aide `self.*`, and four roles
  `refused`.
- Results: it validates clean, its anchor is found exactly once, and it is
  **7/7 driven** in handler mode.
- A `see_fields` typo is reported as an error.
- **The format can express what alf_mar needs.**

**The author's guide is in the registry's `_comment`.** It covers:
- the required keys;
- seeding every column the branch filters on;
- typed-column markers;
- every role must be declared;
- how to check;
- the mock's limits: only `eq.` and `select=` are honoured, so `in.` / `neq.` /
  `order` / `limit` return MORE rows, which shows up as a loud false LEAK;
- how to add a live block and prove that it can fail.

**Access:** hank already has `tools/field_scope_rules.json` as an assigned
override (b62).

## 4. Item 4: the red-flag threshold. ALREADY DONE, THEN SUPERSEDED. No change made

- **cc b24 (2026-10-19)** raised it 70 → 80 for builders only, with the auditors
  left at 70. That is `docs/2026-10-19-cc-b24-notes.md` §Item 4.
- **cc b33 (2026-10-21, `a87a4beb`)** set it to 85 for builders AND auditors, to
  match the 85% wrap-up rule; an unidentified clone stays at 70.
- **Measured now:** `red_at()` gives cc/hank/cody/fourth/hover/hover2 = 85 and an
  unknown clone = 70.
- **One inconsistency, flagged and not changed.** CLAUDE.md's batch-deliverables
  section still says "Wrap up at 80%". `tools/sairn_status_line.py` cites
  "85% REAL-context wrap-up (Michael, standing rule from cc b29)". One of the
  two is stale. That is Michael's call.

## 5. Item 5: every live block reproduced a real bad case

`--replay --handler-ref <sha> --only <rule>` runs `check_live()` **unchanged**:
the same HTTP calls, login and judge. It runs against `field_scope_driver.js
--serve`, which serves the handler at `<sha>` on 127.0.0.1 with the rule's own
fixtures.

| Block | Bad handler | Caught |
|---|---|---|
| sen_caregivers | `f02a61f0^` (the pre-#965-fix code) | **LEAK `[caregiver]`: peer aide_type, branch_id, caregiver_id, cpr_expiry, name, phone, program, status. The original 8-field leak**, plus 5 FLAG findings |
| sen_settings | `e444dc83^` (pre-tiering) | LEAK to scheduler, coordinator and caregiver: api_secret, tax_id, rate, updated_by/at |
| rf_settings | `85206564^` (pre-tiering) | LEAK to estimator, foreman and crew: the `constructor` key value, crew_rates, updated_by/at |
| alf_facility | **ablated**: its redaction is as old as the resource (`fd1bd67e`), so no pre-fix code exists; the `delete` line was removed | LEAK of all 7 rate fields to all 5 non-management roles, **while `rates_visible` still said false**. Only the markers caught it. |

- **Control:** `--replay` against the current tree passes 22/22. The failures
  are caused by the bad handlers, not by the harness.
- **How I read the instruction.** The literal 8-peer-field SEN leak can only
  occur on sen_caregivers, so it was reproduced against that block. Each NEW
  block was proven against its own real bad case, through the same live path.

## 6. OPEN

| Item | Owner | Next step |
|---|---|---|
| The 23 routed reads (b62 §4) | hank | Declare them in `tools/field_scope_rules.json`, alf_mar first. Run `--validate`, then the default run. |
| The 80% vs 85% wrap-up wording | Michael | Pick one. CLAUDE.md and `sairn_status_line.py` disagree. |
| The pre-fix roster cache on caregiver devices | fourth | Unchanged (b62 R1). |
| `rf_schedule` attribution failures | hank / cody | Pre-existing. |
| The truncation | none | Dormant. |
