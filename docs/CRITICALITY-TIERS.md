# Criticality tiers — by RESOURCE, not by app

**Hand-written on purpose. `python tools/criticality_tier_check.py` checks it and never rewrites it** — the tier and the sentence explaining it are a judgement, and a tool that regenerated this file would delete exactly the part that matters. Same reasoning as `docs/SOUP-REGISTER.md` and `tools/sairn_app_map_check.py`.

## Why this is by resource, and what the app-level version got wrong

Started 2026-09-10 as the third standing discipline, alongside the SOUP register and the traceability matrix. **The first version tiered whole apps, and measuring it is what proved that wrong.**

Eight apps sat at Tier B on the sentence *"nothing recorded ties it to money or a regulated record"* — an absence of RECORDING, because nobody had looked. Measured: every one of the eight had a money-bearing resource reaching a server. All eight moved to A, **and 21 of 22 verticals became Tier A**, at which point the register had stopped discriminating.

**The measurement was honest and the granularity was wrong.** A roofing app's invoicing panel and its colour-theme settings do not carry the same consequence, and one label per app forces them into the same answer. Michael's decision, 2026-09-10: tier by RESOURCE.

**The unit is `api/_resources/<app>.js`** — the same unit the SOUP register and the traceability matrix already operate on, reused rather than invented.

## The tiers

Same A/B/C vocabulary as `docs/SOUP-REGISTER.md`, which already tiers components. One scheme, not two. The tier is the **worst consequence of that resource being wrong**, not how likely it is.

| Tier | A resource qualifies when it... |
|---|---|
| **A** | handles **money** (invoices, payments, ledgers, billing, pricing that feeds them), or **regulated/protected data** (patient records, controlled substances, legal deadlines, financial trust accounts), or **its failure has already caused a documented incident** |
| **B** | is **employee-auth-gated but neither money nor regulated** — internal operational data, scheduling, non-financial records |
| **C** | is **cosmetic, device state, or preference** — the shape already excluded from server sync for being regenerable or per-device |

## How to read the Evidence column, because it is the whole point

A tier asserted with no evidence is a label. **Every Tier A row cites something real** — a commit, an incident, a schema file, a registry line — so a reader checks the claim against that source rather than against this table. The checker refuses a Tier A row with an empty evidence cell.

## Rollup — one line per app

| App | Registered resources | A | B | C | Status |
|---|---|---|---|---|---|
| `sairnbiz` | 10 | **2** | 8 | 0 | **RE-TIERED** — `sb_incidents`, `sb_payruns` |
| `sairnbuild` | 32 | **5** | 27 | 0 | **RE-TIERED** — `bld_bids`, `bld_costs`, `bld_incidents`, `bld_price_points`, `bld_sub_bids` |
| `sairncare` | 13 | **7** | 6 | 0 | **RE-TIERED** — `alf_billing`, `alf_claim_routes`, `alf_compliance_rules`, `alf_incidents`, `alf_op_audits`, `alf_payer_rules`, `alf_staff_credentials` |
| `sairncode` | 28 | **7** | 20 | 1 | **RE-TIERED** — `sc_ar`, `sc_claims`, `sc_compliance`, `sc_credential_scope`, `sc_denial`, `sc_denial_events`, `sc_revenue` |
| `sairndental` | 24 | **11** | 12 | 1 | **RE-TIERED** — `dnt_ar`, `dnt_charges`, `dnt_coverage_rules`, `dnt_credentials`, `dnt_denial`, `dnt_gfe`, `dnt_patients`, `dnt_payments`, `dnt_revenue`, `dnt_txplans`, `dnt_vendor_pricing_rules` |
| `sairndesign` | 18 | **2** | 16 | 0 | **RE-TIERED** — `sdn_discounts`, `sdn_invoices` |
| `sairnfreedom` | 35 | **3** | 32 | 0 | **RE-TIERED** — `sf_accounts`, `sf_ledger`, `sf_vendor_prices` |
| `sairngrounds` | 30 | **4** | 26 | 0 | **RE-TIERED** — `grd_invoices`, `msb_food_cost_log`, `msb_licenses`, `quotes` |
| `sairnlaw` | 19 | **5** | 14 | 0 | **RE-TIERED** — `law_barcerts`, `law_deadlines`, `law_invoices`, `law_opaccounts`, `law_trusttx` |
| `sairnlegacy` | 36 | **3** | 33 | 0 | **RE-TIERED** — `leg_certs`, `leg_invoices`, `leg_preneed` |
| `sairnmechanical` | 6 | **2** | 4 | 0 | **RE-TIERED** — `mech_credentials`, `mech_quotes` |
| `sairnroofing` | 27 | **7** | 19 | 1 | **RE-TIERED** — `rf_cert_rules`, `rf_certifications`, `rf_claim_agreements`, `rf_claim_photos`, `rf_claims`, `rf_contingency_rules`, `rf_invoices` |
| `sairnscape` | 12 | **2** | 10 | 0 | **RE-TIERED** — `invoices`, `scp_quotes` |
| `sairnsenior` | 15 | **3** | 11 | 1 | **RE-TIERED** — `sen_claims`, `sen_pay_rates`, `sen_payer_contracts` |
| `sairnvet` | 41 | **5** | 36 | 0 | **RE-TIERED** — `sv_audit_log`, `sv_billing`, `sv_compliance`, `sv_controlled`, `sv_patients` |
| `sairncash` | 0 | 0 | 0 | 0 | **NO REGISTERED RESOURCES.** Nothing to tier today; `api/sairncash/checkout.js` returns `Stripe not configured`. It becomes relevant the day a key is set, which is the trigger its old app-level row already named |
| `stonedesk` | 36 | **10** | 25 | 1 | **RE-TIERED** — invoicing, financial jobs, pricing rules, negotiated prices, quote history, AI quotes, order history, public quote requests, employee records, certifications |

## `stonedesk` — all 36 registered resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `sd_invoices` | **A** | A customer billed wrongly | Money. In the 21-resource backup (`93d37aa5`) and carries `soft_delete`, so a wrong invoice is hidden rather than destroyed |
| `sd_fin_jobs` | **A** | A job costed wrongly, and the invoice built from it wrong | Money. Backed up and soft-deletable in the same registry block |
| `sd_pricing_rules` | **A** | Every quote built afterwards priced wrong | Money, and upstream of it: pricing rules feed quotes, so one wrong rule is not one wrong record |
| `sd_negotiated_prices` | **A** | A customer-specific price applied to the wrong customer | Money. Per-customer pricing is the shape where a leak is also a commercial disclosure |
| `stonedesk_quote_history` | **A** | A quote wrong, or a superseded quote presented as current | Money. The open-work row on the 26 local-only collections named quote history first |
| `sd_aiquotes` | **A** | An AI-drafted quote priced wrong and sent | Money, and generated rather than typed -- the fabricated-number class Guardian check 0b exists for |
| `sd_order_history` | **A** | An order recorded against the wrong job or customer | Money. Named in the local-only measurement alongside invoices |
| `sd_quote_requests` | **A** | A public quote request written into a money surface by an unauthenticated caller | Inherits by the 2026-09-10 public-surface decision: `stonedesk-catalog.html` issues `quote_request` through `/api/stonedesk-public` |
| `sd_hr_employees` | **A** | An employee record wrong, or readable by the wrong role | Identity. The employees seam is the one three other apps read; `api/sd-data.js` gates it on a StoneDesk session and refused a SAIRNbiz owner on 2026-09-10 |
| `sd_hr_certs` | **A** | A lapsed certification shown as current | Regulated-adjacent: a certification record is what a customer or inspector is told about competence |
| `sd_customers` | **B** | Customer contact records lost or merged wrongly | Auth-gated operational data. PII, but not in the protected classes the A criteria name (patient records, controlled substances, legal deadlines, trust accounts) |
| `sd_approvals` | **B** | An approval recorded against the wrong item | Auth-gated workflow state; no money field and no regulated record |
| `sd_blocks` | **B** | Block inventory wrong | Operational inventory, same family as slabs |
| `sd_bundles` | **B** | Bundle grouping wrong | Operational inventory, same family |
| `sd_slab_history` | **B** | Slab lineage wrong | `sql/sd_slab_lineage_schema.sql` documents it as append-only event history |
| `sd_inventory` | **B** | Stock counts wrong | Operational. In the 21-resource backup |
| `sd_remakes` | **B** | A remake recorded against the wrong job | Operational rework tracking; cost lives on the job, not here |
| `sd_comms` | **B** | A customer message lost | Operational communications log |
| `sd_sms_log` | **B** | An SMS record lost | Operational communications log |
| `sd_email_threats` | **B** | A flagged email lost | Operational security triage log |
| `sd_field_stops` | **B** | A field visit record lost | Operational scheduling |
| `sd_exec_msgs` | **B** | An internal message lost | Internal operational messaging |
| `sd_drawings` | **B** | A drawing lost | Operational production artefact |
| `sd_templates` | **B** | A template wrong | Operational configuration, read individually and placed IN the backup on purpose |
| `sd_nesting_saved` | **B** | A saved nesting layout lost | Operational production artefact |
| `sd_veinmatch` | **B** | A vein match lost | Operational production artefact |
| `sd_seamai` | **B** | A seam plan lost | Operational production artefact |
| `sd_photos` | **B** | A job photo lost | Operational. Measured NOT server-backed before the backup work and moved in deliberately |
| `sd_business_snapshots` | **B** | A snapshot wrong | Derived operational reporting |
| `sd_crm` | **B** | A CRM note lost | Operational relationship tracking |
| `sd_public_shop` | **B** | The public shop listing wrong | Public-facing catalogue content; the WRITE path is `sd_quote_requests`, tiered A above |
| `locations` | **B** | A location record wrong | Shared operational reference; `api/_lib/dnt-location.js` stamps location on writes elsewhere |
| `remnants` | **B** | Remnant stock wrong | Operational inventory |
| `supplier_lead_times` | **B** | A lead time wrong | Operational supplier reference |
| `exec_context` | **B** | Executive context wrong | Derived operational summary; `api/sd-data-exec-context.test.js` covers it |
| `style_profile` | **C** | A style preference resets | Preference data; `docs/2026-09-02-nexus-style-profile-design.md` scopes it as presentation |

## The other fifteen apps

### `sairnbiz` — 10 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `sb_ap` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sb_bud` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sb_exps` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sb_hire` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sb_incidents` | **A** | An OSHA injury log wrong or incomplete | REGULATED. The OSHA Form 300 log built in `fb85a4d9` after the open-work row found the Safety tile counting a collection nothing could write |
| `sb_invs` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sb_payruns` | **A** | A payroll run wrong | Money, and the most consequential kind -- payroll. `sairnbiz.html` is also the only writer of the platform-shared `employees` roster |
| `sb_perf` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sb_train` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sb_vends` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |

### `sairnbuild` — 32 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `bld_bids` | **A** | A bid submitted at the wrong price | Money, and a bid is a priced commitment rather than a record of one |
| `bld_change_orders` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_checks` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_comm_log` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_costs` | **A** | A job cost wrong, and every bid built from it wrong | Money, upstream: five client write sites, and costs are what bids are computed from |
| `bld_daily_logs` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_deliveries` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_documents` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_draws` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_equipment` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_incidents` | **A** | A safety incident log wrong | REGULATED, same OSHA shape as SAIRNbiz |
| `bld_inspections` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_jobs` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_lien_waivers` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_photo_analyses` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_pos` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_price_points` | **A** | Pricing wrong across every future bid | Money, upstream of bids |
| `bld_punchlist` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_referrals` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_reviews` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_rfis` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_schedule_entries` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_selections` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_sub_bids` | **A** | A subcontractor bid wrong | Money. Feeds the bid above |
| `bld_submittals` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_subs` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_suppliers` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_tasks` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_timesheet` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_tna` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_toolbox_talks` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `bld_warranty` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |

### `sairncare` — 13 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `alf_activities` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `alf_billing` | **A** | A resident billed wrongly | Money |
| `alf_claim_routes` | **A** | A claim sent to the wrong payer | Money |
| `alf_clients` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `alf_compliance_rules` | **A** | A regulated ALF compliance rule wrong on a live licence | REGULATED. Per-licence reference table under the load-state gate, built after a seed correction shipped unloaded |
| `alf_facility` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `alf_incidents` | **A** | A resident incident record wrong | REGULATED: incident reporting in a licensed care setting |
| `alf_mar` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `alf_op_audits` | **A** | An operational audit record wrong | REGULATED: an audit trail is what an inspector is shown |
| `alf_payer_rules` | **A** | A claim routed against the wrong payer rule | Money AND regulated: a per-licence reference table under `tools/sairn_load_state_check.py --app sairncare` |
| `alf_signals` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `alf_staff` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `alf_staff_credentials` | **A** | An expired credential shown as current for a care worker | REGULATED: licensure on a care-giving role |

### `sairncode` — 28 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `sc_anesthesia` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_anesthesia_base_units` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_ar` | **A** | Receivables wrong | Money |
| `sc_auth` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_auth_requests` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_claims` | **A** | A claim wrong or misrouted | Money |
| `sc_coded_items` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_compliance` | **A** | A compliance determination wrong | REGULATED, and it is the product`s core claim |
| `sc_credential_scope` | **A** | A credential scoped wider than it should be | REGULATED, and identity-adjacent: CLAUDE.md records that SAIRNcode`s PROVISIONING_ROLES is `admin`, not `owner` |
| `sc_denial` | **A** | A denial recorded wrong, and the appeal window with it | Money. Same shape as SAIRNdental`s denials, where an unparseable date silently removed the closing-soon warning |
| `sc_denial_events` | **A** | A denial event lost | Money: the event history an appeal is argued from |
| `sc_dme` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_drg` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_eligibility` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_encoder` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_fraud` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_hcc` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_pctc` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_prebill` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_providers` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_query` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_rac` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_revenue` | **A** | Revenue reported wrong | Money |
| `sc_scrubrules` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_settings` | **C** | A preference resets | Device/practice preference |
| `sc_specialty_checklists` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_specialty_checks` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sc_telehealth` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |

### `sairndental` — 24 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `dnt_appointments` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `dnt_ar` | **A** | Receivables ageing wrong | Money |
| `dnt_charges` | **A** | A patient charged wrongly | Money. `api/_lib/dental-ledger.js` -- a negative charge shows credit on the billing panel while the ageing report does not move |
| `dnt_complaints` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `dnt_coverage_rules` | **A** | An insurance estimate locked onto a charge from a wrong rule | Money. `computeEstimatedInsurance()` LOCKS its result onto the charge and never recomputes |
| `dnt_cred_rules` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `dnt_credentials` | **A** | A lapsed clinical credential shown as current | REGULATED: licensure on a clinical role |
| `dnt_denial` | **A** | An appeal deadline passes unnoticed | Money. An unparseable `denied_on` left the row looking like a denial with a known window while dropping out of the closing-soon filter |
| `dnt_gfe` | **A** | A federally required estimate issued incomplete | REGULATED: 45 CFR 149.610(c)(1), enforced server-side in `api/_lib/dental-gfe.js` |
| `dnt_operatories` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `dnt_patients` | **A** | A patient record wrong, or a paediatric record with no guardian contact | PROTECTED. The guardian rule is enforced server-side in `api/_lib/dental-guardian.js` |
| `dnt_payments` | **A** | A payment recorded wrongly | Money. A negative payment made `dnAging()` report MORE outstanding than the charge it paid |
| `dnt_procedure_types` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `dnt_provider_hours` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `dnt_providers` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `dnt_recall_outreach` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `dnt_referrals` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `dnt_revenue` | **A** | Revenue reported wrong | Money |
| `dnt_settings` | **C** | A preference resets | Device/practice preference; `api/sd-data-dental-settings-patch.test.js` treats it as a PATCH-merged settings object |
| `dnt_supplies` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `dnt_txplans` | **A** | A priced treatment plan wrong | Money: per-item fees and the patient portion |
| `dnt_vendor_contacts` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `dnt_vendor_orders` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `dnt_vendor_pricing_rules` | **A** | Supply pricing wrong across every order | Money, upstream |

### `sairndesign` — 18 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `sdn_clients` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_colorcodes` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_contracts` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_discounts` | **A** | A discount applied wrongly | Money |
| `sdn_invoices` | **A** | An invoice wrong on a design engagement | Money. Eight client write sites |
| `sdn_moodboards` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_pos` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_projects` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_proposals` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_referrals` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_roomdims` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_samplerequests` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_samples` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_schedule` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_specitems` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_team` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_timeentries` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sdn_vendors` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |

### `sairnfreedom` — 35 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `sf_accounts` | **A** | An account balance wrong | Money. Matched as a C candidate by a keyword rule because "accounts" contains "counts" -- corrected by hand, which is why A is not rule-classified |
| `sf_bottle_fills` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_ceremonial_items` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_disbursements` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_district_imports` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_documents` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_donations` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_donor_awards` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_donor_tiers` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_events` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_gaming_expenses` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_honor_details` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_inventory_counts` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_ledger` | **A** | A member organisation`s ledger wrong | Money |
| `sf_members` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_national_categories` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_officers` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_operators` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_permit_flags` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_products` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_rentals` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_service_appointments` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_service_hours` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_service_referrals` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_sessions` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_shifts` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_signatures` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_staff` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_tickets` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_vehicle_service` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_vehicles` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_vendor_prices` | **A** | Vendor pricing wrong | Money, upstream |
| `sf_vendors` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_waivers` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sf_youth_participants` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |

### `sairngrounds` — 30 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `golf_zones` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_boq_rates` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_cart_orders` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_designs` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_dreamclose` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_ecosystem_reports` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_invasive_sightings` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_invoices` | **A** | An invoice wrong on a grounds contract | Money. Six client write sites |
| `grd_irr_controllers` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_irr_schedules` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_irr_zones` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_progress_photos` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_rounds` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_schedule` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_training_completions` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_training_courses` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_vendors` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `grd_water_features` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `jobs` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `msb_bottle_scans` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `msb_food_cost_log` | **A** | Food costing wrong | Money |
| `msb_food_scans` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `msb_food_waste` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `msb_inventory_log` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `msb_licenses` | **A** | A licence shown as current when it has lapsed | REGULATED: operating licences |
| `msb_products` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `msb_sale_hours` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `msb_sales` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `properties` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `quotes` | **A** | A quote wrong | Money |

### `sairnlaw` — 19 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `law_bankstatements` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_barcerts` | **A** | A bar admission shown as current when it is not | REGULATED: licensure to practise |
| `law_clecredits` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_clerequirements` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_clients` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_deadlines` | **A** | A court deadline computed wrong, and a filing missed | REGULATED. The endpoint dropped `service_methods` and Florida ran five days late for five days |
| `law_invoices` | **A** | A client billed wrongly | Money |
| `law_matterdocs` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_mattermilestones` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_matters` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_mattertasks` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_opaccounts` | **A** | An operating account balance wrong | Money. Matched as a C candidate on "counts" inside "accounts" -- corrected by hand |
| `law_optx` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_picases` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_pimedical` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_portalesign` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_portalmessages` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_timeentries` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `law_trusttx` | **A** | A client trust account transaction wrong | REGULATED AND MONEY, and the least forgiving pair on the platform: a lawyer`s trust account is held for a client |

### `sairnlegacy` — 36 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `leg_aftercare` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_bookings` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_cases` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_catererorders` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_caterers` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_certs` | **A** | A certificate record wrong | REGULATED: death certificates and permits |
| `leg_clergy` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_clergybookings` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_cremations` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_custodylog` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_deathrecords` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_dispatches` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_documents` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_facilities` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_floristorders` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_florists` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_gplservices` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_guestbook` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_insurance` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_invoices` | **A** | An invoice wrong on a funeral or pre-need account | Money, against PRE-NEED accounts -- money held against a future obligation. Nine client write sites |
| `leg_keepsakeorders` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_keepsakes` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_liverybookings` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_liveryvendors` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_maintenance` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_memorials` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_merch_catalog` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_merch_units` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_monuments` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_obituaries` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_petcases` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_plots` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_preneed` | **A** | A pre-need contract wrong | Money held against a future obligation, and a contract |
| `leg_processions` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_tributes` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `leg_vehicles` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |

### `sairnmechanical` — 6 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `mech_checks` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `mech_credentials` | **A** | A lapsed technician credential shown as current | REGULATED: licensure on a mechanical trade |
| `mech_docs` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `mech_quotes` | **A** | A job quoted wrong | Money |
| `mech_site_assets` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `mech_takeoffs` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |

### `sairnroofing` — 27 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `rf_bonding` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_buildings` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_cert_rules` | **A** | Certification rules wrong on a live licence | REGULATED: per-licence reference table under the load-state gate |
| `rf_certifications` | **A** | A lapsed manufacturer certification shown as current | REGULATED: certification is what a warranty depends on |
| `rf_claim_agreements` | **A** | A contingency agreement wrong | Money and a contract |
| `rf_claim_photos` | **A** | Claim evidence lost | Money: photographs are what a claim is proved with |
| `rf_claims` | **A** | An insurance claim wrong | Money |
| `rf_company_programs` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_contingency_rules` | **A** | Contingency terms wrong on a live licence | Money AND a per-licence reference table under the load-state gate |
| `rf_draws` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_entities` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_invoices` | **A** | An invoice issued wrong, or a payment against the wrong invoice | Money, and the strongest on the platform: the resource carries the verbs `[issue, add_payment, reconcile_claim]` and `sairnroofing.html:2912` calls `add_payment` live |
| `rf_job_hazard_assessments` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_job_warranties` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_jobs` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_locations` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_photos` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_prequal_documents` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_proposals` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_roof_sections` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_safety_equipment` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_schedule` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_settings` | **C** | A preference resets | Device/company preference |
| `rf_supplier_documents` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `rf_warranty_tiers` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sub_assignments` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `subcontractors` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |

### `sairnscape` — 12 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `customers` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `invoices` | **A** | An invoice wrong | Money |
| `schedule` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `scp_designs` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `scp_irr_controllers` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `scp_irr_schedules` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `scp_irr_zones` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `scp_jobs` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `scp_progress_photos` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `scp_quotes` | **A** | A quote wrong | Money |
| `scp_vendors` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `scp_water_features` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |

### `sairnsenior` — 15 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `sen_applicants` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sen_authorizations` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sen_branches` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sen_caregivers` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sen_claims` | **A** | A claim wrong or misrouted | Money |
| `sen_clients` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sen_franchise_agreements` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sen_pay_rates` | **A** | A caregiver paid at the wrong rate | Money, and it is somebody`s wages |
| `sen_payer_contracts` | **A** | A payer contract term wrong | Money |
| `sen_referral_sources` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sen_referrals` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sen_settings` | **C** | A preference resets | Device/agency preference |
| `sen_training_records` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sen_training_rules` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sen_visits` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |

### `sairnvet` — 41 resources

| Resource | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `sv_audit_log` | **A** | An audit row wrong, and wrong everywhere except where it was corrected | REGULATED. Additive-only hydration means a correction never reaches a second workstation -- disclosed on screen in `ad588e6c` |
| `sv_billing` | **A** | A client billed wrongly | Money |
| `sv_boarding` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_clients` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_coggins` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_comms` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_compliance` | **A** | A compliance record wrong | REGULATED |
| `sv_conservation` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_controlled` | **A** | A controlled-substance balance wrong in a DEA-relevant register | REGULATED, and it has already happened: the demo seed pushed invented Ketamine, Butorphanol and Fentanyl balances to the live server (`a858cab7`), with no delete path anywhere in the product |
| `sv_dental` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_documents` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_equinedental` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_examrooms` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_farmcalls` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_financials` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_herdhealth` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_imaging` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_invoicing` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_labresults` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_lameness` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_mobilevet` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_multisite` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_patients` | **A** | A patient record wrong | PROTECTED: clinical records |
| `sv_peerconsults` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_petinsurance` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_portal` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_prepurchase` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_referrals` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_reminders` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_reports` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_reproduction` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_scheduling` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_soapnotes` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_speciesref` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_staff` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_surgery` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_teleconsults` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_vitals` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_wellness` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_whiteboard` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |
| `sv_wildliferehab` | **B** | Operational data lost or wrong | Employee-auth-gated operational data: neither money nor a regulated record. Classified by the stated B rule rather than individually read -- see the gaps note on why A is hand-verified and B is not |

## The gaps — read this section first

- **All 17 apps are re-tiered: 382 resources, 78 A, 299 B, 5 C.** That is **20% Tier A**, and the distribution is the point. The app-level version put 21 of 22 verticals at A and told a reader nothing; this says which fifth of the platform carries the consequence.
- **Tier A is hand-verified, one written evidence each. B and C are classified by the stated rule.** A row's tier is a judgement either way, but the A rows are the ones a reader acts on, so they carry individually-written evidence naming a commit, an incident, a regulation or a registry line. **Saying all 382 had each been individually read would not be true**, and the checker enforces the difference: a Tier A row with an empty evidence cell is refused.
- **⚠ THE KEYWORD PASS WAS WRONG IN BOTH DIRECTIONS, which is exactly why A is not rule-classified.** It proposed `sf_accounts` and `law_opaccounts` as Tier C because *"accounts"* contains *"counts"* — two money resources one character away from being filed as preferences. It also missed `dnt_coverage_rules`, `dnt_txplans`, `leg_preneed` and `rf_contingency_rules`, all of which are money and none of which match a money keyword. Every one was corrected by hand, and each correction is named in its own row.
- **Every hand-written A entry was reconciled against the registries and none was orphaned.** An entry naming a resource that does not exist would be evidence written for nothing; the generator fails if one appears.
- **The B tier is 299 rows and it is the honest weak point of this file.** Each says the same thing — auth-gated, not money, not regulated — because that is what the rule says, not because 299 files were read. A resource misfiled as B is the failure mode that matters, and the only defence here is that the A criteria are broad on purpose: money *and* anything upstream of money, regulated data *and* licensure, plus any resource with a documented incident.
- **Four StoneDesk collections are deliberately absent**: `sd_settings`, `sd_alert_settings`, `sd_ai_counts`, `sd_market_history`. Real data, and Tier C by the rule, but **not registered resources** — excluded from the server backup on purpose with the reason recorded. The table's unit is the registry; stretching it would make the counts mean two things at once.
- **`sairncash` has zero registered resources.** Nothing to tier today; it becomes relevant the day a Stripe key is set.
- **The earlier platform count of 405 was wrong and is corrected to 382.** A hand grep matched quoted strings that are not resource names; the checker counts from the registries themselves.

## What a tier is FOR

It is not a badge. It decides three things, and it should be cited when it does:

1. **How much verification a change needs before it ships.** A change touching a Tier A resource is where independent review and a live check stop being optional.
2. **Whether a guard belongs in the blocking set.** `GUARD_TESTS` in `tools/sairn_push_gate_hook.py` is the blocking registry; a Tier A resource with no guard is a finding.
3. **What an incident costs, before it happens.** Written down so nobody has to form that judgement during the incident, which is the worst moment to be forming it for the first time.
