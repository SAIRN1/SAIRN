# api/sd-data.js resource inventory — hank b5, 2026-10-13 (READ ONLY)

**`api/sd-data.js` WAS NOT EDITED.** `git diff --quiet api/sd-data.js` is clean.
Produced by grep and offset reads only, cross-referenced against
`api/_resources/*.js`, `SD_SESSION_GATED`, the app-wide inline gates, the
gate helpers, and `api/sd-data-scp-session-gate.test.js`'s `UNGATED_REST`.

## HOW THE GATE COLUMN IS DERIVED, and why the naive version is wrong

There are **four** mechanisms, not one. A scan that reads only the first
reports most of this file as ungated, which is how SAIRNvet kept a
parse-time-only hydrate while every one of its resources answered 401:

1. **`TABLE`** — a row in `SD_SESSION_GATED`. Pre-dispatch, both verbs.
2. **`INLINE-APP`** — `<PREFIX>_RESOURCES[resource]` → 401, covering an
   app's WHOLE registry at once. Three apps: sairnlaw, sairnlegacy, sairnvet.
3. **`PER-BRANCH`** — `verifySessionToken` inside the resource's own
   branch, or a gate helper (`dntGate`, `sdExecGate`). This is the
   largest group and the one a table scan cannot see.
4. **`BY DESIGN`** — ungated and NAMED as such with its columns read out
   of the schema (`UNGATED_REST`).

5. **`NAMED-SET PRE-DISPATCH`** — a hand-written set of resource names plus
   `hasOwnProperty.call(SET, resource)` → 401, before any branch runs.
   **ONE instance and it was found by a failing suite, not by this scan:**
   `GRD_SESSION_RESOURCES` at `api/sd-data.js:4343-4366`, **21 SAIRNgrounds
   resources**. Its six Tier A members had been reported `NO GATE FOUND` by the
   first version of this document and `ungated` by the first version of the
   sweep, because the branches themselves still go straight from the resource
   test to the fetch — the gate is above them.

   `api/sd-data-cross-tenant-dispatchers.test.js` carried a deliberate
   `app: null` tripwire for exactly this and **it fired**: 14 arms UNREACHED on
   401 for as long as the gate had existed. Config re-pointed in b5; the suite
   went 405/14 → **419/0**, and those six resources' tenant isolation is tested
   for the first time since the gate landed.

   **So the honest count of mechanisms is FIVE, and the fifth was discovered by
   a red suite rather than by reading the file.** Any future sweep that reads
   fewer than five will under-report.

**`NO GATE FOUND` IS A THIRD STATE, NOT A VERDICT.** It means this scan
could not find a gate within 45 lines of any branch for that resource. It
is where a sweep starts, not a list of findings.

## Totals

| classification | count |
|---|---|
| TABLE | **15** |
| INLINE-APP | **3** |
| PER-BRANCH | **83** |
| BY DESIGN | **5** |
| NO GATE FOUND | **46** |
| **resources the dispatch branches on** | **152** |

Note `TABLE` reads 15 here while `SD_SESSION_GATED` holds 46 rows: the
difference is rows for resources whose branch is keyed some other way
(e.g. `BLD_RESOURCES[resource]`), so they never appear as `resource ===`.

## Per resource

| resource | branch line(s) | gate | basis | app |
|---|---|---|---|---|
| `alf_activities` | 11571–11582 (2) | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `alf_billing` | 11073–11334 (3) | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `alf_claim_routes` | 11989–12007 (2) | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `alf_clients` | 7348–7363 (2) | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `alf_compliance_rules` | 12542–12622 (3) | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `alf_facility` | 11659–11675 (2) | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `alf_family_contacts` | 12117 | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `alf_incidents` | 11398–11501 (2) | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `alf_mar` | 10808–10851 (2) | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `alf_op_audits` | 12896–12919 (2) | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `alf_payer_rules` | 11845–11934 (3) | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `alf_signals` | 11745–11763 (2) | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `alf_staff` | 10687–10708 (2) | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `alf_staff_credentials` | 12797–12818 (2) | PER-BRANCH | verifySessionToken in the branch | sairncare |
| `bld_bids` | 5918–5937 (2) | PER-BRANCH | verifySessionToken in the branch | sairnbuild |
| `bld_draws` | 5673–13273 (2) | PER-BRANCH | verifySessionToken in the branch | sairnbuild |
| `bld_tna` | 6000–6022 (2) | PER-BRANCH | verifySessionToken in the branch | sairnbuild |
| `customers` | 5109–5117 (2) | TABLE | SD_SESSION_GATED [read, write] | sairnscape |
| `dnt_appointments` | 15669–15700 (2) | PER-BRANCH | via dntGate() | sairndental |
| `dnt_charges` | 14818 | NO GATE FOUND | — | sairndental |
| `dnt_complaints` | 15622–15631 (2) | PER-BRANCH | via dntGate() | sairndental |
| `dnt_coverage_rules` | 14832 | NO GATE FOUND | — | sairndental |
| `dnt_cred_rules` | 15895–15912 (2) | PER-BRANCH | via dntGate() | sairndental |
| `dnt_credentials` | 15955–16033 (3) | PER-BRANCH | via dntGate() | sairndental |
| `dnt_denial` | 14925 | NO GATE FOUND | — | sairndental |
| `dnt_gfe` | 15157 | NO GATE FOUND | — | sairndental |
| `dnt_operatories` | 15119 | NO GATE FOUND | — | sairndental |
| `dnt_patients` | 14776 | NO GATE FOUND | — | sairndental |
| `dnt_payments` | 14799 | NO GATE FOUND | — | sairndental |
| `dnt_procedure_types` | 14957 | NO GATE FOUND | — | sairndental |
| `dnt_provider_hours` | 15016 | NO GATE FOUND | — | sairndental |
| `dnt_providers` | 14724–15038 (3) | NO GATE FOUND | — | sairndental |
| `dnt_recall_outreach` | 15086 | NO GATE FOUND | — | sairndental |
| `dnt_referrals` | 15063 | NO GATE FOUND | — | sairndental |
| `dnt_rollup` | 15468 | PER-BRANCH | via dntGate() | sairndental |
| `dnt_settings` | 15517–15526 (2) | PER-BRANCH | via dntGate() | sairndental |
| `dnt_supplies` | 15109–15267 (2) | PER-BRANCH | via dntGate() | sairndental |
| `dnt_txplans` | 14987 | NO GATE FOUND | — | sairndental |
| `dnt_vendor_orders` | 15137 | NO GATE FOUND | — | sairndental |
| `employee_profile` | 3053–3079 (2) | PER-BRANCH | verifySessionToken in the branch | shared |
| `employees` | 1843–1969 (2) | PER-BRANCH | verifySessionToken in the branch | shared |
| `exec_context` | 2926 | PER-BRANCH | verifySessionToken in the branch | stonedesk |
| `golf_zones` | 4431–4439 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_boq_rates` | 4858–4866 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_cart_orders` | 4690–4698 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_designs` | 4711–4719 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_dreamclose` | 4586–4594 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_ecosystem_reports` | 4636–4644 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_invasive_sightings` | 4615–4623 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_invoices` | 4565–4573 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_irr_controllers` | 4732–4740 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_irr_schedules` | 4774–4782 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_irr_zones` | 4753–4761 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_progress_photos` | 4501–4509 (2) | PER-BRANCH | verifySessionToken in the branch | sairngrounds |
| `grd_rounds` | 4669–4677 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_schedule` | 4467–4475 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_training_completions` | 4837–4845 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_training_courses` | 4816–4824 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_vendors` | 4879–4887 (2) | NO GATE FOUND | — | sairngrounds |
| `grd_water_features` | 4795–4803 (2) | NO GATE FOUND | — | sairngrounds |
| `invoices` | 5193–5201 (2) | TABLE | SD_SESSION_GATED [read, write] | sairnscape |
| `jobs` | 4389–4397 (2) | NO GATE FOUND | — | sairngrounds |
| `law_clients` | 16105–16113 (2) | TABLE | SD_SESSION_GATED [read, write] | sairnlaw |
| `law_deadlines` | 16165–16173 (2) | TABLE | SD_SESSION_GATED [read, write] | sairnlaw |
| `law_matters` | 16126–16134 (2) | TABLE | SD_SESSION_GATED [read, write] | sairnlaw |
| `law_timeentries` | 14248 | INLINE-APP | every sairnlaw resource, 401 NO_SESSION | sairnlaw |
| `law_trust_reconcile` | 16211 | INLINE-APP | every sairnlaw resource, 401 NO_SESSION | sairnlaw |
| `law_trusttx` | 16287–16295 (2) | TABLE | SD_SESSION_GATED [read, write] | sairnlaw |
| `leg_merch_units` | 14349 | INLINE-APP | every sairnlegacy resource, 401 NO_SESSION | sairnlegacy |
| `locations` | 3147–3155 (2) | TABLE | SD_SESSION_GATED [read, write] | stonedesk |
| `mech_credentials` | 2702 | PER-BRANCH | verifySessionToken in the branch | sairnmechanical |
| `mech_insurance_policies` | 2491 | PER-BRANCH | verifySessionToken in the branch | sairnmechanical |
| `mech_site_assets` | 2264 | PER-BRANCH | verifySessionToken in the branch | sairnmechanical |
| `memory` | 1620–1814 (5) | TABLE | SD_SESSION_GATED [read, write] | shared |
| `msb_bottle_scans` | 4998–5006 (2) | NO GATE FOUND | — | sairngrounds |
| `msb_food_cost_log` | 5061–5069 (2) | NO GATE FOUND | — | sairngrounds |
| `msb_food_scans` | 5019–5027 (2) | NO GATE FOUND | — | sairngrounds |
| `msb_food_waste` | 5040–5048 (2) | NO GATE FOUND | — | sairngrounds |
| `msb_inventory_log` | 4977–4985 (2) | NO GATE FOUND | — | sairngrounds |
| `msb_licenses` | 4956–4964 (2) | NO GATE FOUND | — | sairngrounds |
| `msb_products` | 4900–4908 (2) | PER-BRANCH | verifySessionToken in the branch | sairngrounds |
| `msb_sale_hours` | 5082–5091 (2) | NO GATE FOUND | — | sairngrounds |
| `msb_sales` | 4921–4929 (2) | PER-BRANCH | verifySessionToken in the branch | sairngrounds |
| `profile` | 1780–1790 (2) | TABLE | SD_SESSION_GATED [read, write] | shared |
| `properties` | 4368–4376 (2) | NO GATE FOUND | — | sairngrounds |
| `quotes` | 4410–4418 (2) | NO GATE FOUND | — | sairngrounds |
| `remnants` | 3205–3213 (2) | NO GATE FOUND | — | stonedesk |
| `render_usage` | 5429 | PER-BRANCH | verifySessionToken in the branch | shared |
| `rf_bonding` | 8461–8610 (3) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_buildings` | 8971–9005 (3) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_cert_rules` | 7801–7819 (2) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_certifications` | 7854–7934 (3) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_claim_agreements` | 10524–10606 (3) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_claim_photos` | 8106–8130 (2) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_claims` | 7985–9425 (4) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_company_programs` | 9867–9928 (3) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_contingency_rules` | 10475–10485 (2) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_draws` | 8796 | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_entities` | 9999 | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_invoices` | 9583 | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_job_hazard_assessments` | 8652–8762 (3) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_job_warranties` | 9180–9284 (3) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_jobs` | 7523–7538 (2) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_locations` | 10136–10160 (2) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_photos` | 7729 | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_prequal_documents` | 8461–8507 (3) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_proposals` | 9489–9519 (2) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_roof_sections` | 8971–9121 (3) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_safety_equipment` | 8652–8690 (3) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_schedule` | 10215–10358 (4) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_settings` | 8195–8208 (2) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_supplier_documents` | 2141 | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `rf_warranty_tiers` | 9180–9243 (3) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `sb_perf` | 14006 | PER-BRANCH | verifySessionToken in the branch | sairnbiz |
| `sb_po` | 14103 | NO GATE FOUND | — | sairnbiz |
| `sb_ts` | 13950 | NO GATE FOUND | — | sairnbiz |
| `sc_auth_requests` | 16751 | PER-BRANCH | verifySessionToken in the branch | sairncode |
| `sc_settings` | 16704–16726 (2) | PER-BRANCH | verifySessionToken in the branch | sairncode |
| `schedule` | 5172–5180 (2) | NO GATE FOUND | — | sairnscape |
| `scp_designs` | 5251–5259 (2) | TABLE | SD_SESSION_GATED [read, write] | sairnscape |
| `scp_irr_controllers` | 5272–5280 (2) | BY DESIGN | named in UNGATED_REST with its columns read | sairnscape |
| `scp_irr_schedules` | 5314–5322 (2) | BY DESIGN | named in UNGATED_REST with its columns read | sairnscape |
| `scp_irr_zones` | 5293–5301 (2) | BY DESIGN | named in UNGATED_REST with its columns read | sairnscape |
| `scp_jobs` | 5130–5138 (2) | BY DESIGN | named in UNGATED_REST with its columns read | sairnscape |
| `scp_progress_photos` | 5382–5390 (2) | TABLE | SD_SESSION_GATED [read, write] | sairnscape |
| `scp_quotes` | 5151–5159 (2) | TABLE | SD_SESSION_GATED [read, write] | sairnscape |
| `scp_vendors` | 5356–5364 (2) | TABLE | SD_SESSION_GATED [read, write] | sairnscape |
| `scp_water_features` | 5335–5343 (2) | BY DESIGN | named in UNGATED_REST with its columns read | sairnscape |
| `sd_approvals` | 2824 | PER-BRANCH | verifySessionToken in the branch | stonedesk |
| `sd_crm` | 4225–4248 (2) | PER-BRANCH | verifySessionToken in the branch | stonedesk |
| `sd_customers` | 3681 | PER-BRANCH | verifySessionToken in the branch | stonedesk |
| `sd_exec_msgs` | 13429–13828 (3) | PER-BRANCH | via sdExecGate() | stonedesk |
| `sd_public_shop` | 4010 | PER-BRANCH | verifySessionToken in the branch | stonedesk |
| `sd_quote_requests` | 4074 | PER-BRANCH | verifySessionToken in the branch | stonedesk |
| `sdn_clients` | 5562–5581 (2) | PER-BRANCH | verifySessionToken in the branch | sairndesign |
| `sdn_invoices` | 13165 | TABLE | SD_SESSION_GATED [read, write] | sairndesign |
| `sen_authorizations` | 6989 | PER-BRANCH | verifySessionToken in the branch | sairnsenior |
| `sen_branches` | 6852 | PER-BRANCH | verifySessionToken in the branch | sairnsenior |
| `sen_caregivers` | 6325–6341 (2) | PER-BRANCH | verifySessionToken in the branch | sairnsenior |
| `sen_claims` | 6648 | PER-BRANCH | verifySessionToken in the branch | sairnsenior |
| `sen_clients` | 6088–6107 (2) | PER-BRANCH | verifySessionToken in the branch | sairnsenior |
| `sen_franchise_agreements` | 7156 | PER-BRANCH | verifySessionToken in the branch | sairnsenior |
| `sen_pay_rates` | 7078 | PER-BRANCH | verifySessionToken in the branch | sairnsenior |
| `sen_payer_contracts` | 6914 | PER-BRANCH | verifySessionToken in the branch | sairnsenior |
| `sen_settings` | 7234–7247 (2) | PER-BRANCH | verifySessionToken in the branch | sairnsenior |
| `sen_visits` | 6412–6782 (5) | PER-BRANCH | verifySessionToken in the branch | sairnsenior |
| `shared_knowledge` | 5478–5494 (3) | NO GATE FOUND | — | shared |
| `slabs` | 3114–3302 (3) | TABLE | SD_SESSION_GATED [read, write, reserve, release] | shared |
| `style_profile` | 2965 | PER-BRANCH | verifySessionToken in the branch | stonedesk |
| `sub_assignments` | 8264–8370 (3) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `subcontractors` | 8264–8311 (3) | PER-BRANCH | verifySessionToken in the branch | sairnroofing |
| `supplier_lead_times` | 2029 | PER-BRANCH | verifySessionToken in the branch | stonedesk |

## `NO GATE FOUND` — 46, the population for any future sweep

- `dnt_charges` (sairndental) — branch 14818
- `dnt_coverage_rules` (sairndental) — branch 14832
- `dnt_denial` (sairndental) — branch 14925
- `dnt_gfe` (sairndental) — branch 15157
- `dnt_operatories` (sairndental) — branch 15119
- `dnt_patients` (sairndental) — branch 14776
- `dnt_payments` (sairndental) — branch 14799
- `dnt_procedure_types` (sairndental) — branch 14957
- `dnt_provider_hours` (sairndental) — branch 15016
- `dnt_providers` (sairndental) — branch 14724–15038
- `dnt_recall_outreach` (sairndental) — branch 15086
- `dnt_referrals` (sairndental) — branch 15063
- `dnt_txplans` (sairndental) — branch 14987
- `dnt_vendor_orders` (sairndental) — branch 15137
- `golf_zones` (sairngrounds) — branch 4431–4439
- `grd_boq_rates` (sairngrounds) — branch 4858–4866
- `grd_cart_orders` (sairngrounds) — branch 4690–4698
- `grd_designs` (sairngrounds) — branch 4711–4719
- `grd_dreamclose` (sairngrounds) — branch 4586–4594
- `grd_ecosystem_reports` (sairngrounds) — branch 4636–4644
- `grd_invasive_sightings` (sairngrounds) — branch 4615–4623
- `grd_invoices` (sairngrounds) — branch 4565–4573
- `grd_irr_controllers` (sairngrounds) — branch 4732–4740
- `grd_irr_schedules` (sairngrounds) — branch 4774–4782
- `grd_irr_zones` (sairngrounds) — branch 4753–4761
- `grd_rounds` (sairngrounds) — branch 4669–4677
- `grd_schedule` (sairngrounds) — branch 4467–4475
- `grd_training_completions` (sairngrounds) — branch 4837–4845
- `grd_training_courses` (sairngrounds) — branch 4816–4824
- `grd_vendors` (sairngrounds) — branch 4879–4887
- `grd_water_features` (sairngrounds) — branch 4795–4803
- `jobs` (sairngrounds) — branch 4389–4397
- `msb_bottle_scans` (sairngrounds) — branch 4998–5006
- `msb_food_cost_log` (sairngrounds) — branch 5061–5069
- `msb_food_scans` (sairngrounds) — branch 5019–5027
- `msb_food_waste` (sairngrounds) — branch 5040–5048
- `msb_inventory_log` (sairngrounds) — branch 4977–4985
- `msb_licenses` (sairngrounds) — branch 4956–4964
- `msb_sale_hours` (sairngrounds) — branch 5082–5091
- `properties` (sairngrounds) — branch 4368–4376
- `quotes` (sairngrounds) — branch 4410–4418
- `remnants` (stonedesk) — branch 3205–3213
- `sb_po` (sairnbiz) — branch 14103
- `sb_ts` (sairnbiz) — branch 13950
- `schedule` (sairnscape) — branch 5172–5180
- `shared_knowledge` (shared) — branch 5478–5494
