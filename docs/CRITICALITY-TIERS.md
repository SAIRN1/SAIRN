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
| `sairnbiz` | 10 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairnbuild` | 32 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairncare` | 13 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairncode` | 28 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairndental` | 24 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairndesign` | 18 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairnfreedom` | 35 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairngrounds` | 30 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairnlaw` | 19 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairnlegacy` | 36 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairnmechanical` | 6 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairnroofing` | 27 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairnscape` | 12 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairnsenior` | 15 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairnvet` | 41 | — | — | — | **NOT YET RE-TIERED** — stage 2. Its app-level tier is withdrawn rather than carried forward, because an app-level tier is the thing this restructure found to be wrong |
| `sairncash` | 0 | 0 | 0 | 0 | **NO REGISTERED RESOURCES.** Nothing to tier today; `api/sairncash/checkout.js` returns `Stripe not configured`. It becomes relevant the day a key is set, which is the trigger its old app-level row already named |
| `stonedesk` | 36 | **10** | 25 | 1 | **RE-TIERED** — invoicing, financial jobs, pricing rules, negotiated prices, quote history, AI quotes, order history, public quote requests, employee records, certifications |

## `stonedesk` — the worked example, all 36 registered resources

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

## The gaps — read this section first

- **Fifteen apps are NOT YET RE-TIERED, and their app-level tiers are WITHDRAWN rather than carried forward.** Carrying them would be carrying the thing this restructure exists because it was wrong. `stonedesk` is done as the worked example — 36 resources, and the mix is the signal: **10 A, 25 B, 1 C**. That says which tenth of the flagship deserves the heaviest scrutiny, which "StoneDesk is Tier A" never did.
- **346 resources remain across the other fifteen apps** (382 registered platform-wide, counted by the checker from the registries themselves -- an earlier hand count said 405 and was wrong, because the grep matched quoted strings that are not resource names). That is the honest size of stage 2, stated rather than discovered later.
- **Tier A is hand-verified; B and C are classified by the stated rule.** A row's tier is a judgement either way, but the A rows are the ones a reader acts on, so they carry individually-written evidence. Saying 369 rows were each individually read would not be true, and the checker enforces the difference: an A row must not cite the rule alone.
- **Four StoneDesk collections are deliberately absent from the resource table**: `sd_settings`, `sd_alert_settings`, `sd_ai_counts` and `sd_market_history`. They are real data and would be Tier C, but they are **not registered resources** — they were excluded from the server backup on purpose, with the reason recorded (device config, a regenerable counter, derived history). The table's unit is the registry, and stretching it to cover unregistered keys would make the counts mean two things at once.
- **Reconciling the hand list against the registry caught seven wrong names in this file's own first draft**, including `sd_slabs`, which is a promoted table rather than a registered resource. The list is now derived from `api/_resources/stonedesk.js` and the classification mapped onto it, which is why the checker can hold it.
- **`sairncash` has no registered resources at all** and no row. It becomes relevant the day a Stripe key is set, which is the trigger its old app-level row already named.

## What a tier is FOR

It is not a badge. It decides three things, and it should be cited when it does:

1. **How much verification a change needs before it ships.** A change touching a Tier A resource is where independent review and a live check stop being optional.
2. **Whether a guard belongs in the blocking set.** `GUARD_TESTS` in `tools/sairn_push_gate_hook.py` is the blocking registry; a Tier A resource with no guard is a finding.
3. **What an incident costs, before it happens.** Written down so nobody has to form that judgement during the incident, which is the worst moment to be forming it for the first time.
