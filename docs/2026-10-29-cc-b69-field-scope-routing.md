# Field-scope: owners for the 23 undeclared role-scoped reads (cc b69, 2026-10-29)

**Background.** The b61 sweep found 23 role-scoped read branches in
`api/sd-data.js` that `tools/field_scope_rules.json` does not cover.

- b62 routed all 23 to **hank**, because `api/` is hank's layer.
- Since then hank has declared none of them, and nobody else could. The
  manifest assigned the rules file to hank alone.

This batch gives each read a **real owner**, and cc declares the three that
are cc's.

## How an owner was chosen

### `git blame` did not answer it

The role-scoping lines in 21 of the 23 branches date from one sweeping
refactor (`48866588`) or from commits whose subjects name no session. Blame
gives a refactor's author, not the app's designer.

### The rule used instead: the app's claim history

Each read goes to the session that has claimed its app most often,
**all-time**, counted from `chore(claims): <who> claims <app>` subjects in git:

| App | Claims, all-time | Owner |
|---|---|---|
| sairnsenior | hank 15, fourth 8, cc 4, cody 2 | **hank** |
| sairncare (alf_) | fourth 8, cc 5, cody 4, hank 2 | **fourth** |
| sairnroofing (rf_) | cody 10, cc 5, hank 4 | **cody** |
| sairnbuild (bld_) | cody 6, hank 5, cc 3, fourth 2 | **cody** |
| stonedesk | cc 35, fourth 30, hank 16, cody 10 | **cc** |
| sairndental | cc 17, hank 14, fourth 10, cody 4 | **cc** |

### Two exceptions, each stated

- **`alf_mar` stays with hank.** hank made the latest role-scope design on
  that exact resource: sairncare b51 `76193dc9` (the family_mar grantee gate)
  and the b53 MAR work.
- **Platform reads with no single app go to hank.** These are `employees`,
  `employee_profile` and `sdn_clients`. `sdn_clients` is used by sairnbiz,
  sairnbuild and sairncare. hank owns the `api/` layer they live in.

## Declared by cc this batch

All three were written from their DESIGN commits, never read off the branch.

| Read | Declared from | Design |
|---|---|---|
| `sd_crm.read` | `a4f0a1a0` (2026-08-19) | owner/admin see every lead; others see their own assigned leads; unassigned leads are management-only |
| `dnt_rollup.read` | `af5aeddf` (2026-09-15) | owner only; no row-level data in the body (counts and sums, keyed by office); frontdesk and provider refused |
| `exec_context.read` | `562d1ded` (2026-09-02) | owner/admin only; sales and install refused; no table |

**Result:** handler mode across all 8 rules is **38/38 clean**.

**Ablation.** I declared four wrong designs, and each was caught:
- sales seeing a peer lead: MISSING;
- owner missing the unassigned lead: LEAK;
- dental provider not refused: COULD NOT RUN, never a pass;
- exec_context sales not refused: COULD NOT RUN, never a pass.

**Not live-driven yet.** Live blocks for stonedesk and sairndental need audit
credentials and seeded fixtures, as `sen_branches` got in b64.

## Queued, with owners

Each owner declares its own rows in `tools/field_scope_rules.json`. The
rules file is now in **cody's and fourth's** `assigned_overrides` as well as
hank's.

Follow the "ADDING A RULE" steps in the file's own `_comment`, then run:

    python tools/sairn_field_scope_check.py --validate
    python tools/sairn_field_scope_check.py

| # | Read | b61 verdict | Owner | Note |
|---|---|---|---|---|
| 1 | `alf_mar/read` | DIFFERENTIATED | **hank** | Declare a facility column, so the same-ID-different-facility class is visible. |
| 2 | `sen_clients/read` | DIFFERENTIATED | **hank** | Broad read for owner, billing, coordinator and scheduler; caregivers get their assigned clients only. |
| 3 | `sen_visits/read` | DIFFERENTIATED | **hank** | Include the SCHEDULE/EVV field split. |
| 4 | `employees/read` | COULD NOT TELL | **hank** | Platform roster; no table parse. |
| 5 | `employee_profile/read` | OWN-ROW ONLY | **hank** | Include the `payload.all` path. |
| 6 | `sdn_clients/read` | DIFFERENTIATED | **hank** | Used by three apps. |
| 7 | `alf_clients/read` | DIFFERENTIATED | **fourth** | Also carries the open b64 decision on medications and diagnosis for billing and activities. |
| 8 | `alf_staff/read` | DIFFERENTIATED | **fourth** | |
| 9 | `alf_staff_credentials/read` | DIFFERENTIATED | **fourth** | |
| 10 | `alf_billing/read` | OWN-ROW ONLY | **fourth** | |
| 11 | `alf_claim_routes/read` | OWN-ROW ONLY | **fourth** | |
| 12 | `alf_incidents/read` | COULD NOT TELL | **fourth** | |
| 13 | `rf_claims/read` | DIFFERENTIATED | **cody** | |
| 14 | `rf_jobs/read` | DIFFERENTIATED | **cody** | |
| 15 | `rf_certifications/read` | DIFFERENTIATED | **cody** | |
| 16 | `rf_company_programs/read` | OWN-ROW ONLY | **cody** | |
| 17 | `rf_schedule/read` | COULD NOT TELL | **cody** | Unmodelled filter; declare the filter column. |
| 18 | `rf_warranty_tiers/read` | COULD NOT TELL | **cody** | |
| 19 | `bld_bids/read` | DIFFERENTIATED | **cody** | |
| 20 | `bld_tna/read` | COULD NOT TELL | **cody** | Unmodelled filter. |
| -- | `sd_crm/read`, `dnt_rollup/read`, `exec_context/read` | -- | cc | **DECLARED** in b69 |

**Count:** hank 6, fourth 6, cody 8, cc 3 (declared) = 23.
