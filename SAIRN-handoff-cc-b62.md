# SAIRN handoff: cc, batch b62, 2026-10-28

**All six items are closed. #965 is verified LIVE for all five sairnsenior
roles.**

- Landed: `bfe18165`.
- The clone reads 0 0 against origin.
- No `--force`, no override, no skip.

| | |
|---|---|
| Claims held | `sairnsenior` (b62, released with this handoff) |
| Context | see the digest's CONTEXT line (measured) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\332ab89b-94aa-4880-931e-d17413636dfc.jsonl` |

## 1. Item 1: phone stays visible to scheduler and coordinator

This is Michael's decision. No code change.

## 2. Item 2: SEN-AUDIT-0002, provisioned and run

**A premise correction, measured 2026-10-28 on project
`ejrlrrkvhtllxbbypdjb`.** SEN audit credentials did already exist. SEN-AUDIT-2026
is active and holds:
- `audit-owner` (owner);
- `hank-b27-caregiver` and `hank-b49-caregiver`;
- 0 caregiver rows.

That is the payroll probe's licence, and it carries permanent `sen_visits`
writes. A role-scope read needs a roster in which every row is known, so this
batch minted a SEPARATE licence as instructed.

**Why the key is `0002`.** The audit-key shape is `^[A-Z]{2,6}-AUDIT-\d{4}$`,
and `sairnsenior.html` accepts only `SEN-`, `DEMO-` or `SAIRN-` keys. So the
digits are a SERIAL, not a year.

| Licence | Employee ID | Role | PIN |
|---|---|---|---|
| SEN-AUDIT-0002 | fs-owner | owner | 74816982 |
| SEN-AUDIT-0002 | fs-billing | billing | 52958575 |
| SEN-AUDIT-0002 | fs-scheduler | scheduler | 54401975 |
| SEN-AUDIT-0002 | fs-coordinator | coordinator | 34513907 |
| SEN-AUDIT-0002 | fs-caregiver | caregiver | 70654769 |

The same table is in the header of
`sql/sen_audit_0002_role_scope_credentials_2026-10-28.sql`. Publishing it
follows the 2026-10-20 precedent. **Rotate every PIN the day this licence holds
a real person's record.**

**Fixture rows (`sen_caregivers`):**
- `CG-FS-SELF` belongs to `fs-caregiver`.
- `CG-FS-PEER` belongs to `fs-peer`, an employee with no credential.

Every value is synthetic.

**How it was written:**
- Each hash comes from `hashPin()`. Every PIN passed its own `verifyPin()`, and
  `00000000` failed.
- PR 3.4 guard and salt check are included.
- `employee_auth_guard_check` OK. `sql_preflight` 0 findings.
- The live constraints and columns were checked before writing.

**Rehearsal:**
- The same SQL ran with the final guard changed to `raise exception 'REHEARSAL
  OK…'`, so the run always rolls back.
- Result: 5 credentials, 1 provisioner, 2 fixtures.
- A read afterwards showed 0/0/0, so **nothing persisted**.

**The real run:** committed, then read back. The licence is active with app
sairnsenior and plan demo. The 5 credentials are active with the written salts.
The 2 fixture rows are present.

**`tools/audit_licence.py`:** SEN-AUDIT-0002 is added to `KNOWN_AUDIT_KEYS`.

## 3. Item 3: the live verification of #965. VERIFIED

`python tools/sairn_field_scope_check.py --live` ran against sairn.vercel.app
on SEN-AUDIT-0002. Output: `scratchpad\live62.txt`.

| Role | Rows | Fields | Result |
|---|---|---|---|
| owner | CG-FS-PEER, CG-FS-SELF | all 12 | flags as declared |
| billing | CG-FS-PEER, CG-FS-SELF | all 12 | flags as declared |
| scheduler | CG-FS-PEER, CG-FS-SELF | 9; no bgcheck_date, notes or state_caregiver_id | flags as declared |
| coordinator | CG-FS-PEER, CG-FS-SELF | the same 9 | flags as declared |
| caregiver | **CG-FS-SELF only** | the same 9 | flags as declared |

**How `--live` was extended this batch:**
- It now checks the declared response flags.
- It now checks the paired positive: a roster-tier role must get a row that is
  not its own.
- The `sen_caregivers` live block covers all five roles.

**Why the overall exit is still 2.** The other three rules (`sen_settings`,
`rf_settings`, `alf_facility`) have no live block, and the tool says so rather
than passing them.

**To re-run,** set these and run `--live`:
- `SEN_AUDIT_LICENSE=SEN-AUDIT-0002`
- `SEN_{OWNER,BILLING,SCHEDULER,COORDINATOR,CAREGIVER}_{EMP,PIN}` from the table
  in §2.

## 4. Item 4: the sweep, ROUTED. The owner of each finding is named

**Ownership** (`docs/sairn-path-manifest.json`, Michael's split):
- every one of the 23 reads is a branch in `api/sd-data.js`, which is **hank's**
  layer;
- hank also did the latest sairncare MAR work (`76193dc9`, sairncare b51);
- client-side residue is **fourth's** (`*.html`).

**The route:**
- `tools/field_scope_rules.json` is now assigned to hank in the manifest, so he
  can declare rules himself.
- From that point the blocking check 4c enforces each declared rule.
- The routing note is posted to the status registry, in cc's row: "FOR HANK…".

| # | Read (api/sd-data.js, b61 lines) | b61 verdict | Owner | What the next paste should ask for |
|---|---|---|---|---|
| 1 | **alf_mar/read** :13032 | DIFFERENTIATED | **hank** | FIRST. Declare the per-role design with a facility column, so the same-ID-different-facility class is visible to the mock. |
| 2 | sen_clients/read :7207 | DIFFERENTIATED | **hank** | Declare the tiers (broad read for owner/billing/coordinator/scheduler; caregiver gets assigned clients only). |
| 3 | sen_visits/read :7609 | DIFFERENTIATED | **hank** | Declare, including the SCHEDULE/EVV field split. |
| 4 | rf_claims/read :10062 | DIFFERENTIATED | **hank** | Declare. |
| 5 | alf_clients/read :9404 | DIFFERENTIATED | hank | Declare. |
| 6 | alf_staff/read :12911 | DIFFERENTIATED | hank | Declare. |
| 7 | alf_staff_credentials/read :15382 | DIFFERENTIATED | hank | Declare. |
| 8 | rf_jobs/read :9578 | DIFFERENTIATED | hank | Declare. |
| 9 | rf_certifications/read :9918 | DIFFERENTIATED | hank | Declare. |
| 10 | sd_crm/read :5330 | DIFFERENTIATED | hank | Declare. |
| 11 | sdn_clients/read :6669 | DIFFERENTIATED | hank | Declare. |
| 12 | bld_bids/read :7038 | DIFFERENTIATED | hank | Declare. |
| 13 | employee_profile/read :4057 | OWN-ROW ONLY | hank | Declare, including the `payload.all` path the sweep did not drive. |
| 14 | rf_company_programs/read :12055 | OWN-ROW ONLY | hank | Declare. |
| 15 | alf_billing/read :13309 | OWN-ROW ONLY | hank | Declare. |
| 16 | alf_claim_routes/read :14269 | OWN-ROW ONLY | hank | Declare. |
| 17 | exec_context/read :3921 | COULD NOT TELL (needs payload) | hank | Declare, with the request payload. |
| 18 | bld_tna/read :7119 | COULD NOT TELL (unmodelled filter) | hank | Declare, with the filter column. |
| 19 | rf_schedule/read :12418 | COULD NOT TELL (unmodelled filter) | hank | Declare, with the filter column. |
| 20 | employees/read :2782 | COULD NOT TELL (no table parse) | hank | Declare. |
| 21 | rf_warranty_tiers/read :11393 | COULD NOT TELL (no table parse) | hank | Declare. |
| 22 | alf_incidents/read :13676 | COULD NOT TELL (no table parse) | hank | Declare. |
| 23 | dnt_rollup/read :18948 | COULD NOT TELL (no table parse) | hank | Declare. |
| R1 | Caregiver devices holding a pre-fix roster cache (`sairnsenior.html`) | client residue | **fourth** | Purge or replace `sen_caregivers` on hydrate when `roster_scope` is `own`. |
| R2 | sen_visits/readiness presence side door (H1 1274, low) | hover finding | **hank** | Unchanged. |

None of these is fixed in this batch, by instruction.

## 5. Item 5: the write_attribution failures. Confirmed pre-existing

- `tests/sd_data_write_attribution_three_apps.js` was run on exports of
  `6a8237ae` (the parent of b61's fix `f02a61f0`) and of HEAD.
- Both runs: 17 passed, 3 failed. The three FAIL lines are **identical**:
  - B: `rf_schedule` must store the session employee;
  - C1: 14 of 15, the miss is `rf_schedule=undefined`;
  - D3: `rf_schedule/set_status` must merge.
- The full outputs differ in ONE diagnostic line only, a source offset
  (`stamp=265813` against `266247`). It moved by the bytes b61 inserted.
- The file's `sen_caregivers` arm passes in both runs.
- **Not touched by the field-scope change. Left alone.**
- Owner: hank for `rf_schedule` in `api/`, cody for the test file.

## 6. OPEN

| Item | Owner | Next step |
|---|---|---|
| Declare the 23 reads (§4) | hank | alf_mar first, in `tools/field_scope_rules.json` |
| Pre-fix roster cache on devices | fourth | §4 R1 |
| Live blocks for `sen_settings`, `rf_settings` and `alf_facility` | cc, when asked | Each needs audit-licence role credentials, like SEN-AUDIT-0002 |
| `rf_schedule` attribution failures | hank / cody | Pre-existing (§5) |
| The truncation | none | Dormant, low priority |
