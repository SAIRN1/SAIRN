# Tier A review — `invoices`, `law_trusttx`, `leg_cremations`, `employees`, `rf_claims`, `rf_jobs`

**fourth / ted, batch b37, 2026-10-19.** Read per row at the real write site
and traced to the consumers, at `HEAD` = `b87eb083`.

**THIS FILE IS A REPORT, NOT A LEDGER ENTRY. Nothing here was written to
`docs/tier-a-reviews.json` — cc holds that file in its active b24 claim.** The
review obligation ledger and this review are different artefacts; routing the
verdicts into the ledger is a one-line append for whoever next holds it, and
the six verdicts below are in the form that append needs.

**Every figure names the command or the `file:line` that produced it. Re-derive
anything you mean to quote, including out of this file.**

---

## 0. VERDICT TABLE

| resource | register tier (I / C) | verdict | the one thing |
|---|---|---|---|
| `invoices` | **A** / **B** | **CONFIRMED** | grounds hold on-row; gate claims re-verified |
| `law_trusttx` | **A** / **A** | **CONFIRMED**, grounds UNDERSTATED | `reference_number` is a check number drawn on an IOLTA account — C-A on its own, independent of privilege |
| `leg_cremations` | **A** / **A** | **CONFIRMED on tier, GROUNDS WRONG on confidentiality** | the row carries **no decedent identity and no government identifier** — the C-grounds describe the *case* row, not this one |
| `employees` | **A** / **A** | **CONFIRMED on tier, GROUNDS WRONG on the stored shape** | the server blob is **9 fields** from `syncEmps()`, not the 13-field `saveEmp()` shape the register quotes; **emergency contact and notes are cited as grounds and are not on the row** |
| `rf_claims` | **A** / **B** | **CONFIRMED — and the declared attribution defect is FIXED at HEAD** | money is **on-row** (`rcv`/`acv`/`depreciation`/`deductible`), so this is not an A-by-chain row at all |
| `rf_jobs` | **A** / **B** | **CONFIRMED — and the declared attribution shape is STILL PRESENT, inert** | both projections put the **blob LAST**; `rf_claims`' read puts the real column last. Inert only because of `storedBlob`'s strip list |

**No row is UNREADABLE.** All six write sites, all six server branches and the
consumers were located and read.

---

## 1. THE INSTRUCTION'S PREMISE, CORRECTED

The instruction named `rf_claims` and `rf_jobs` as *"the 2 declared
mis-attributions."* **That is the right pair and the right word, and it is not
about their TIER — it is about ACTING-EMPLOYEE ATTRIBUTION ON THE WRITE.** The
declaration is in `docs/defect-density-register.json`, not in the tier register:

> *"The last 7 of 15 write branches … that persisted a row recording no acting
> employee … two SAIRNroofing (`rf_claims/write`, `rf_schedule/set_status`)"*

and, separately:

> *"a blob-carried `assigned_employee_id` would overwrite the server-resolved
> value in what the client receives — false ATTRIBUTION on a Tier A bid …
> **The same shape was then found in `rf_jobs`' response construction in the
> same review.**"*

**Searched and NOT found anywhere: any declaration that these two rows' TIER is
mis-attributed.** `grep -n "mis-attribut\|misattribut"` over
`docs/CRITICALITY-TIERS.md` returns **nothing**, and both rows are properly
registered in `api/_resources/sairnroofing.js:15` and `:31`. So the two
verdicts below answer the attribution question that was actually declared, and
the tier question separately.

**AND THE RESULT INVERTS THE PREMISE.** The two rows whose *grounds text* is
genuinely mis-attributed are **`leg_cremations` and `employees`** — §4 and §5.
Neither was named in the instruction.

---

## 2. `invoices` (SAIRNscape, stored `scp_invoices`) — **CONFIRMED**

| | |
|---|---|
| write site | `sairnscape.html:3698` `scpSaveInv()` |
| server | `api/sd-data.js:5929` (`write`), `:5921` (`read`) |
| row | `{id, customer_id, amount, status, issued}` — **5 fields** |

**Integrity A — CONFIRMED, on-row.** `amount` is money and it folds into
totals: `sairnscape.html:2856` renders *"Invoices unpaid 30+ days"* with an
at-risk sum, and `:1945` exports `invoices_unpaid_30plus_days` to an AI tool.
The server branch's own comment records the realised harm rather than a
hypothetical one — a string `amount` folded to `"0100200"`, profit reported
`-99450` where `450` was right, *"and that number was posted to /api/claude as
fact and printed on a tax report."*

**Confidentiality B — CONFIRMED, as stated.** The register says *"no PII, PHI,
privileged communication or financial-account detail belonging to a third party
sits on this row."* **Checked field by field: true.** `customer_id` is a
reference; the name, phone, email and address live on `scp_customers`.

**The row's own gate claims re-verified, not inherited:**
`'invoices': ['read', 'write']` in `SD_SESSION_GATED` (`:1466`) and
`'invoices': 'sairnscape'` in `SD_GATE_APP` (`:1871`). **The register's
"NAMED TRIGGER" warning is correct and still load-bearing:** the resource is
`invoices`, the table is `scp_invoices`, and `:1870` says in the source itself
that *"there is no 'scp_invoices' resource to pin."*

---

## 3. `law_trusttx` (SAIRNlaw) — **CONFIRMED, grounds UNDERSTATED**

| | |
|---|---|
| write site | `sairnlaw.html:3518` `saveTrustTransaction()` |
| row | `{id, matter_id, client_id, type, amount, date, method, reference_number, description, status, voided_reason, voided_at, created_at}` — **13 fields** |

**Integrity A — CONFIRMED.** IOLTA client trust money, and the disbursement
balance check is on-row (`:3525`, *"trust funds can never go negative"*).

**Confidentiality A — CONFIRMED, and the register's grounds are narrower than
the row.** The register rests C-A on privilege: *"the existence and detail of
the matter, not only the communications inside it."* True — `matter_id`,
`client_id` and a free-text `description` are all on-row.

**What the register does not say, and should:** `method` can be `Check`, and
`reference_number` is then **a check number drawn on the firm's IOLTA
account**. That is *financial-account detail belonging to a third party*, which
the register's own Confidentiality-A definition catches **independently of
privilege**. The row would be C-A on that ground alone with the privilege
argument deleted. **This is a second independent basis, not a correction** —
worth adding because a single-ground A row is one re-reading away from being
argued down.

---

## 4. `leg_cremations` (SAIRNlegacy) — **CONFIRMED on tier, GROUNDS WRONG**

| | |
|---|---|
| write site | `sairnlegacy.html:3190` `saveCremation()` |
| row | `{id, case_id, crematory_name, scheduled_datetime, status, authorization_on_file, id_verified, waiting_period_observed, witness_present, disposition_type, disposition_details, completed_datetime, created_at}` — **13 fields** |

**Integrity A — CONFIRMED, on-row and strongly.** `authorization_on_file`,
`id_verified` and `waiting_period_observed` are **regulated determinations
stored as booleans on this row**. The register's irreversibility argument holds:
a cremation cannot be corrected against the thing it describes.

**Confidentiality A — THE TIER IS DEFENSIBLE, THE GROUNDS AS WRITTEN ARE NOT.**
The register says:

> *"A deceased person's identity, cause or circumstances, or the government
> identifiers attached to them, are disclosed"* … *"The record carries the
> authorisation and the identifiers it rests on"*

**Read against the 13 fields: it does not.** There is **no decedent name, no
cause, no circumstance and no government identifier on this row**. There is
`case_id` — a reference. `authorization_on_file` is a **boolean**, not the
authorisation; the register's phrase *"carries the authorisation and the
identifiers it rests on"* describes a document this row does not store.

**Why the tier still stands, stated as a chain rather than asserted:**
`case_id` + `scheduled_datetime` + `crematory_name` + `disposition_details`,
joined to the case, discloses the disposition of a named decedent — and
`disposition_details` is free text into which a funeral director will write
exactly the circumstance the grounds are about. **That is an A-by-chain
argument and the register should say so**, the way the `rf_jobs` row does. A
row whose grounds name content it does not carry is the failure mode the
register's own 2026-09-22 3.2 pass exists to prevent, arriving one layer up.

**EXACT NEXT STEP:** rewrite the `leg_cremations` confidentiality cell as a
traced chain through `case_id`, naming `disposition_details` as the on-row
free-text channel. Do **not** retier. Needs whoever next holds
`docs/CRITICALITY-TIERS.md`; **never edit the row by splitting on `|`.**

---

## 5. `employees` (SAIRNbiz writes, StoneDesk reads) — **CONFIRMED on tier, GROUNDS WRONG on the stored shape**

| | |
|---|---|
| client write | `sairnbiz.html:2433` `saveEmp()` → **local** `sb_emps` |
| what actually ships | `sairnbiz.html:5066` `syncEmps()` |
| server | `api/sd-data.js:2603` (`write`), `:2477` (`read`) |

**THE INTEGRITY-A CITATION HOLDS EXACTLY, RE-DERIVED RATHER THAN TRUSTED.**
`stonedesk.html:43148` is the line, unmoved, and it does what the register says:

```
var avg=e.reduce(function(s,x){return s+(parseFloat(x.hourly_rate)||0);},0)/e.length;
```

presented as *"Avg labor rate: $…/hr from SAIRNbiz"* in a banner injected into
`panel-jobcost`. **Cross-app, which is the part a per-app reading misses.**

**AND THE CHAIN SURVIVES A NAME MISMATCH THAT LOOKS FATAL.** `saveEmp()` writes
the field as **`rate`**, and StoneDesk reads **`hourly_rate`** — on those two
lines alone the average would be `$0.00` for every roster and the hazard would
not exist. It holds because `syncEmps()` **renames on the way out**
(`sairnbiz.html:5072`, `hourly_rate: e.rate`). **Checked, because a broken
chain and a working one are indistinguishable from either end alone.**

**THE GROUNDS TEXT IS WRONG ABOUT WHAT IS STORED.** The register says:

> *"The stored `data` blob is SAIRNbiz's whole employee record —
> `{fn, ln, role, dept, type, rate, pay_freq, start, phone, email, status, ec, notes}`,
> from `saveEmp()` in `sairnbiz.html`"*

**That is the localStorage shape, not the stored one.** `syncEmps()` sends
**nine** fields:

```
{first_name, last_name, role, department, employment_type, hourly_rate, start_date, phone, email}
```

So **`ec` (emergency contact), `notes`, `pay_freq` and `status` are cited as
confidentiality grounds and are not in the blob.** `status` is a real column,
not blob content. **Confidentiality A still holds on `hourly_rate` alone** —
compensation, which the C-A definition names explicitly — plus `phone` and
`email`. The tier is right; the sentence under it over-claims.

**ONE THING THE REGISTER IS RIGHT ABOUT IN A WAY WORTH KEEPING:** the write is
`data: emp.data || emp` (`api/sd-data.js:2630` — the register cites `:2604`,
which is the branch head, so the citation is coarse but not wrong). **The
`|| emp` fallback does accept an arbitrary caller object**, so an owner/hr
session *could* put the whole 13-field record in the blob. It is dormant for
the one shipped caller, which sends `emp.data`. So the register's "whole
employee record" claim is **reachable but not realised** — a distinction the
cell should make rather than collapse.

**`employees` IS REGISTERED, AND THE TOOL SAYING OTHERWISE IS cc's KNOWN
DEFECT.** `python tools/criticality_tier_check.py` reports
`NOT A RESOURCE  employees has a row and is not registered in any
api/_resources/*.js`. It **is** registered, at `api/_resources/shared.js:55`.
`apps_with_registries()` skips `shared` by name at
`tools/criticality_tier_check.py:236`. **Measured: that one skip accounts for
7 of the 14 `PROBLEMS`** — `profile`, `memory`, `employees`, `slabs`,
`render_usage`, `shared_knowledge`, `employee_profile`, all confirmed present
in `shared.js` — **plus the `GONE shared has a rollup line and no resource
registry` line, which is 8**, matching cc's b35 measurement exactly. **Not
re-reported as a new finding; it is cc's open item and the count agrees.**

---

## 6. `rf_claims` (SAIRNroofing) — **CONFIRMED; the declared defect is FIXED**

| | |
|---|---|
| write site | `sairnroofing.html:2321` |
| server | `api/sd-data.js:9670` (`write`), `:9652` (`read`) |
| row | `{id, job_id, carrier, claim_number, adjuster, date_of_loss, peril, policy_type, status, waiting_on_carrier, rcv, depreciation, acv, deductible, acv_check_received, final_invoice_submitted, recoverable_depreciation_released}` — **17 fields** |

**Integrity A — CONFIRMED, AND NOT BY CHAIN.** Five money fields sit directly
on the row: `rcv`, `depreciation`, `acv`, `deductible`,
`recoverable_depreciation_released`. The register's one-word grounds
(*"Money."*) are literally true here, which is worth stating because it is the
opposite of `rf_jobs` one row below it in the same app.

**Confidentiality B — CONFIRMED, as stated.** The register's exclusion list is
*"no health, legal-privilege, government-identifier or compensation data on
this row."* **Checked field by field: true.** `claim_number` is
insurer-issued, not governmental. The property owner's name and address are on
`rf_jobs`, reached through `job_id`.

**THE TWO DECLARED ATTRIBUTION DEFECTS ARE BOTH CLOSED AT HEAD:**

1. **No acting employee on the write — FIXED.** `api/sd-data.js:9728` appends
   `{ updatedBy: session.employee_id, updatedByRole: session.role }` **as the
   last `Object.assign` source**, and the source says why that position is
   deliberate: *"a caller-supplied `updatedBy` surviving in the payload is
   overwritten HERE. First position would let the payload win."*
2. **Smuggled `assigned_employee_id` in the blob — FIXED.**
   `storedBlob(payload, ['id', 'job_id', 'assigned_employee_id', 'status'])`
   at `:9711` strips it on the way in.

---

## 7. `rf_jobs` (SAIRNroofing) — **CONFIRMED; the declared shape is STILL PRESENT and inert**

| | |
|---|---|
| write site | `sairnroofing.html:5477` — **the register cites `:5254`, which is now `rfSetScheduleStatus()`. CITATION DRIFTED; the field list it quotes is exactly right** |
| server | `api/sd-data.js:9194` (`write`), `:9190` (`read`) |
| row | `{id, name, address, job_class, status, assigned_employee_id, location_id?}` |

**Integrity A — CONFIRMED BY CHAIN, and the chain was re-traced at HEAD rather
than read out of the register:**

* `api/sd-data.js:11434` — an invoice is written with
  `location_id: (gate.job && gate.job.location_id) || roofingLocations.DEFAULT_LOCATION_ID`.
  **The invoice inherits its branch from the job, and a job with no location
  does not error — it silently picks the default branch.**
* `api/_lib/roofing-consolidation.js:88`/`:128` buckets that invoice into a
  legal entity by exactly that field.
* `api/sd-data.js:9363` — the job write itself carries an existing job's
  location forward and stamps `DEFAULT_LOCATION_ID` for a new job with none.

**No money field is on this row.** The register is explicit that this is why the
first reading of it was wrong, and it is right to be.

**Confidentiality B — CONFIRMED.** `name` and `address` are on-row: a customer
list, commercially sensitive, no elevated class.

### 7.1 THE DECLARED SHAPE — present, inert, and inert for a reason worth naming

`rf_claims`' read puts the **real columns last**, which is the safe order
(`:9660`):

```js
Object.assign({}, x.data || {}, { claim_id, job_id, assigned_employee_id, status })
```

**`rf_jobs` inverts it in BOTH directions.** `Object.assign` applies sources
left to right and the later one wins, so in both of these **the blob wins**:

```js
// read, :9190
Object.assign({ id: r.job_id, job_class: …, assigned_employee_id: …, location_id: … }, r.data)
// write response, :9375
Object.assign({ id: payload.id, job_class: jobClass, assigned_employee_id: requestedAssignee || '', location_id: locationId }, jobData)
```

**IT IS NOT AN ACCESS-CONTROL BYPASS, and saying so precisely matters.** The
row-level privacy filter at `:9188` tests `r.assigned_employee_id` — the real
column — **before** the overlay, so a narrow role still receives only its own
rows. What the inversion can corrupt is the **attribution the client is
told**: an assignee or a branch other than the one the server authorised and
stored, on a Tier A row whose whole A-grounds are branch attribution.

**IT IS INERT TODAY, AND IT HAS NEVER NOT BEEN — MEASURED, NOT ASSUMED.** It is
inert only because `storedBlob(payload, ['id', 'job_class',
'assigned_employee_id', 'location_id'])` at `:9346` strips all four keys on write. I
checked for a historical window in which a smuggled copy could have been
persisted and **there is none**:

| field | first stripped | introduced | window |
|---|---|---|---|
| `assigned_employee_id` | `2c349af8` (Phase 1) | `2c349af8` | **none** |
| `location_id` | `68668ece` (Phase 4a) | `68668ece` — **same commit** | **none** |

`git log -S` on both strings, `git show 2c349af8:api/sd-data.js`. So **no stored
`rf_jobs` row carries a blob copy of either column**, and the hazard is purely
forward-looking.

**WHY IT IS STILL WORTH FIXING RATHER THAN CLOSING AS INERT:** the strip list
and the projection order are the **same single point of failure in two
directions at once**. Remove one name from that list — or add a fifth real
column and forget to list it — and the read *and* the write response both start
serving the caller's value in the same move, on the row whose Tier A exists
because branch attribution decides which legal entity an invoice belongs to.
`rf_claims` does not have that dependency because its order is safe on its own.

**EXACT NEXT STEP, two lines, no behaviour change today:** flip both
`Object.assign` calls so the real columns are the **last** source, matching
`rf_claims`/read. Needs whoever next holds `api/sd-data.js` — **cody holds it
in its active b27 claim**, so this is routed, not taken. A test arm that plants
`assigned_employee_id` and `location_id` in the payload and asserts the
response carries the server-resolved values is the control that makes the fix
mean something; without it the fix and the strip are indistinguishable.

---

## 8. WHAT THIS REVIEW DID NOT ESTABLISH

* **Nothing was driven against a live deployment.** Every verdict is a source
  read plus `git log`. No row was written, no response was observed.
* **The `rf_jobs` inversion is reasoned from `Object.assign` semantics and the
  strip list, not reproduced.** A test that plants the two keys would settle it
  in either direction and does not exist.
* **The `employees` 9-vs-13 field finding is from the shipped client only.**
  The `|| emp` fallback's reachability is read from the branch, not exercised.
* **No row was re-tiered and none needed to be.** Two grounds cells are wrong
  and both are wrong in the direction of over-claiming, which does not change a
  tier.
* **`docs/tier-a-reviews.json` was not written to** — cc holds it. The six
  verdicts above are in the shape that append needs.
