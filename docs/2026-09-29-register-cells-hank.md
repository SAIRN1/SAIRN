# Register cells, re-derived at HEAD — delivered as TEXT, not landed

**2026-09-29 (Hank).** Items 2, 4, 5 and 8 of queue24.

**`docs/CRITICALITY-TIERS.md` IS HELD BY `hover`, claimed 0.2h before I checked.**
Per the standing rule, the item is skipped rather than retried, and the holder and
the refusal are recorded verbatim below. Every verdict here was re-derived from the
resource's own writes and reads at HEAD; the replacement cell text is ready to
paste by whoever holds the file.

## The refusal, verbatim

```
BLOCKED -- another session already claimed overlapping work:

  session   : hover
  subject   : hover
  task      : seven-item queue: log the leg_guestbook contradiction against
              hover2's B/B verdict with an independent deciding test; log routable
              citation-drift findings for sd_customers, sd_business_snapshots and
              sf_honor_details; scan the private mirror repo for non-log files and
              credentials; independently validate
              hover2_validation_freshness_check.py on an isolated copy;
              conditionally validate hover2_log_mirror.py; one undirected batch;
              resume the weighted-rotation cold-scan draw.
  FILES: hover_log.py hover_cold_scan_pool.py hover_backup_mirror.py
         docs/CRITICALITY-TIERS.md
  claimed   : 2026-09-29T14:00:36Z (0.2h ago)
  blocked by: same file or resource: docs/criticality-tiers.md
  also share: criticality, docs, tiers

DO NOT start this. Flag it back to the coordinating chat session and let it decide
who runs it.
```

**Note the overlap is genuine, not lexical:** hover's own queue names the
`leg_guestbook` contradiction — item 4 here — so we are both working the same row.
My verdict below is an independent read and should be compared with theirs rather
than replacing it.

---

## Item 2 — SAIRNbiz: two rows that do not exist

An outside HR and accounting professional will use this app on demo data. Neither
resource has a row at all.

### `sb_emps` — **A / A**

| | |
|---|---|
| **Tier** | **A** |
| **Confidentiality** | **A** |

**Consequence if wrong or lost:** *An employee's PAY RATE is wrong, and every
figure computed from the roster is wrong with it — `rTax()` sums
`sbGrossPerPeriod(e)` across active employees to produce gross pay and the FICA
figure. And it is the ONE SAIRNbiz collection that reaches a server, so a corrupt
row propagates to StoneDesk, which READS this roster.*

**Consequence if read by the wrong person:** *A named employee's pay rate, phone,
email, and their EMERGENCY CONTACT — a third party who never dealt with this
company. "An individual's compensation" is named explicitly in the
Confidentiality-A definition, and this row carries it for every employee at once.*

**Evidence:** **ROW WRITTEN 2026-09-29 (hank); the resource had NO ROW AT ALL.**
READ OUT OF THE APP: `saveEmp()` (`sairnbiz.html:2325`) writes
`{id, fn, ln, role, dept, type, rate, pay_freq, start, phone, email, status, ec,
notes}` and carries `ben` forward from the existing record. `rate` is the pay rate;
`ec` is the emergency contact. **CONSUMERS READ, NOT ONLY THE WRITE:** `rTax()`
(`:4148`) filters to active employees and reduces `sbGrossPerPeriod(e)` into gross
and FICA; `rEmps()` and `rEmpTbl()` render the roster.
**GATED, AND THE GATE HAS A SCAR:** `api/sd-data.js:1606` (`employees` write)
requires a real SAIRNbiz session token with a signed `app:'sairnbiz'` claim and an
owner/hr role. It used to gate on `body.app_id === 'sairnbiz'` — a
client-supplied string — so any bearer of a shop's licence key could write payroll
data regardless of role, **bypassing the read gate's RBAC entirely**
(security-auditor finding, 2026-08-03). **CROSS-APP:**
`api/_resources/sairnbiz.js:126` records `sb_emps` as the one SAIRNbiz collection
already synced, via the bespoke `employees` branch, and StoneDesk reads it.
**Michael proposed HIGH; A on both axes is the register's equivalent, and the
confidentiality axis is the one that does not need the money limb to get there.**

### `sb_co` — **A / B**

| | |
|---|---|
| **Tier** | **A** |
| **Confidentiality** | **B** |

**Consequence if wrong or lost:** *The `entity` field selects the company's
estimated-payment schedule, so a wrong one is a MISSED TAX DEADLINE.*

**Consequence if read by the wrong person:** *The company's own registration
details and its EIN. Commercially sensitive; not an elevated class — an EIN is a
business identifier the company prints on every W-9 it issues, unlike an
individual's SSN.*

**Evidence:** **ROW WRITTEN 2026-09-29 (hank); the resource had NO ROW AT ALL.**
READ OUT OF THE APP: `saveCo()` (`sairnbiz.html:4667`) writes every key in
`SB_CO_FIELDS` (`:4647`) — `{name, dba, entity, state, ein, founded, industry,
addr, city, st2, zip, phone, email, web, owner, hr, ctrl}`.
**THE DECIDING TEST IS A READ, NOT THE EIN:** `sbFilingSchedule()` (`:4139`) reads
`sbCo().entity` and returns a filing schedule from `SB_FILING_SCHEDULES`, and the
save toast says so in its own words — *"the Tax panel reads it to pick an
estimated-payment schedule, and a wrong one there is a missed deadline."* That is
the same *something is DECIDED from it* test that promoted `bld_costs` and
`sv_financials`, and it is why this is A rather than B.
**I AM DEPARTING FROM THE PROPOSED MODERATE, IN BOTH DIRECTIONS, AND SAYING SO:**
*upward* on integrity, because a missed statutory deadline is not moderate;
*downward* on confidentiality, because `sb_co` was **WRITE-ONLY** until recently
(`:4640` records that) and an EIN is not a protected personal identifier. If the
proposal meant *"moderate overall"*, the honest disagreement is that the tier is
the WORSE of two axes and the integrity axis here is a filing deadline.
**A SECOND, SHARPER FINDING ON THE SAME ROW, and it is why the cell says
`entity`:** `sbFilingSchedule()` refuses when the recorded value is a legal form
rather than a tax classification — *"a single-member LLC is disregarded, a
multi-member one defaults to a partnership, and either can elect S- or C-corp
treatment"*. The refusal is correct and good. It also means the field carries a
distinction a user can get wrong silently.

---

## Item 4 — `leg_guestbook`: the auditor disagreement, decided from the three facts

**VERDICT: B / B. H1 is right that the "no PII" claim is FALSE. H2 is right about
the tier and WRONG about the reason.** Both bases need correcting.

| Fact | What I read |
|---|---|
| **Who enters the name?** | **Funeral-home staff, not the visitor.** `addGuestbookEntry()` (`sairnlegacy.html:3616`) reads `$('gbname').value` from a form inside the authenticated staff app. There is no public page and no share path. |
| **Who can read the entries?** | **Staff only.** `guestbookEntries()` has four call sites, all internal; `rGuestbook(memorialId)` renders into `#mm-guestbook` in the staff panel. `leg_guestbook` is in `LEG_RESOURCES` (`api/sd-data.js:13183`), so every read needs a verified `sairnlegacy` session. |
| **Displayed publicly?** | **No.** The memorial record carries a `service_details_visible` flag, and nothing publishes the guestbook. |

**So H2's stated reason — "the visitor name is public guestbook content" — is
factually wrong about this app twice over:** the content is not public, and the
visitor did not enter it. **H1's claim is factually right:** the record is
`{id, memorial_id, name, message, created_at}` — a named living person and their
free-text message about a death — and *"no PII"* is false.

**The tier stays B because neither axis reaches A on the register's own bar.** A
mourner's name and a condolence message is not PHI, not clinical, not privileged,
not a vital record or government identifier, not an individual's compensation, not
an authorisation map, and not the firm's confidential commercial position. It is
PII of a non-elevated class, non-public, session-gated.

**AND A PRODUCT OBSERVATION THAT IS NOT A TIER QUESTION:** a memorial guestbook
whose entries are typed by staff and shown to nobody outside the firm is the
SAIRNbuild Client Portal shape again — a feature named for an outside audience that
the outside audience cannot reach.

---

## Item 5 — auditor register findings, re-derived

### `mech_docs` — the cell's absolute no-PII claim is false, **by the redactor's own admission**

**The redaction is incomplete BY DESIGN and says so in its own note.**
`api/_lib/mech-redact.js` carries:

> *"A person's name written in ordinary prose is NOT redacted by this pass — only
> labelled name fields, emails, phones, addresses, SSN/EIN and …"*

and the comment above the patterns: *"The LABEL is matched, never the name —
matching a name would need a dictionary, and a dictionary that knows 'Dave' …"*.

The gate at `api/sd-data.js:14284` applies it server-side and **carries
`redaction.complete` and `redaction.note` ON THE ROW**, deliberately, *"so a reader
of the stored record can see what the pass did and what it could not do."*
**The app's own toast says it too** (`sairnmechanical.html:1780`): *"Saved and
synced — identifiers removed. Names in prose are not."*

**So three separate places state the residue and the tier cell claims the
opposite.** Replacement confidentiality basis:

> *A scanned work order, contract, permit or INVOICE, stored as extracted text.
> **Labelled identifiers are redacted server-side; A PERSON'S NAME IN ORDINARY
> PROSE IS NOT, and the row records that in its own `redaction.complete` and
> `redaction.note` fields.** The pass is a reduction, not a guarantee, and the
> previous cell's absolute no-PII claim contradicted the redactor's own note, the
> gate's own comment and the app's own toast.*

### `mech_takeoffs` — the same shape, and the gate is scoped **by name**

**CONFIRMED AT HEAD.** `MECH_RECORDS` (`api/sd-data.js:14244`) is
`{mech_quotes, mech_checks, mech_docs, mech_takeoffs}` — all four share one
licence-only write branch — and the redaction is:

```js
if (resource === 'mech_docs') {
  const red = mechRedact.redactDocumentText(payload.text);
```

**Scoped to one resource by name.** `saveTakeoff()`
(`sairnmechanical.html:1784`) stores `{id, date, text}` where `text` is the
blueprint-takeoff output and pushes it through `mechPushRecord('mech_takeoffs', …)`.
A takeoff run over a drawing sheet carries whatever text was on the sheet —
title block, owner, architect, site address — **and none of it goes through the
redactor.**

**`api/sd-data.js` IS FOURTH'S. NOT EDITED.** The fix as pasteable text:

```js
      let mPayload = payload;
      // REDACTED FOR EVERY RECORD THAT STORES EXTRACTED TEXT, not for one
      // resource by name. mech_takeoffs goes through this same branch and stored
      // its scan output unredacted: a title block carries an owner, an architect
      // and a site address as readily as a work order does. `mech_docs` was
      // named here because it was the resource being fixed that day, and a
      // name-scoped guard over a four-resource map is the membership defect this
      // repo keeps finding -- LEG_RESOURCES had 36 tables open on the same shape.
      const MECH_REDACTED = { mech_docs: true, mech_takeoffs: true };
      if (MECH_REDACTED[resource] && typeof payload.text === 'string') {
        const red = mechRedact.redactDocumentText(payload.text);
        mPayload = Object.assign({}, payload, {
          text: red.text,
          redaction: {
            applied_at: nowISO(),
            redactions: red.redactions,
            complete: red.complete,
            note: red.note
          }
        });
      }
```

`mech_quotes` and `mech_checks` are **deliberately left out**, matching the
existing comment's reasoning (*"a quote or a cheque stub is not a credential"*) —
neither stores free extracted text. **That is a judgement for the file's owner to
confirm, not mine to assume.**

### `msb_bottle_scans` — **B**, same shape as `msb_food_waste`, with one difference worth recording

**Re-derived.** `sairngrounds.html:4779` writes
`{id, product_id, brand_read, fill_pct, date, note}`, and `note` carries a
**dollar estimate** computed at `:4771-4777` from
`((priorScan.fill_pct − fillPct) / 100) × bottle_oz × (cost / bottle_oz)`.

**THE ESTIMATE REACHES NO COMPUTATION.** `note` is rendered at `:4962` and passed
as a *text note* to `msbLogInventoryChange(match.id, 'scan_reading', 0, …)` — with
`qty_delta` **0**. Nothing sums it, prices anything from it, or decides on it.
That is the `msb_food_waste` verdict for the same reason: **a real dollar figure
that carries money without handling it.**

**THE ONE DIFFERENCE, and it is why this row is not simply a copy:** unlike
`msb_food_waste`, the figure here is *derived* from `fill_pct`, and it is written
into the **append-only inventory log** — which the module advertises as
*"3+ years, audit-ready"*. A wrong `fill_pct` puts a wrong dollar estimate into an
audit-ready record permanently. Still B: the log entry is prose, and no
computation reads it. **What would move it: any KPI that sums the estimates.**

### Citation drift — **NOT LANDED, and the +43 pair is not mine to touch**

| Drift | Status |
|---|---|
| `api/_lib/job-risk.js` `:218` → `:222` | **Blocked** — the citation lives in `docs/CRITICALITY-TIERS.md` |
| `sd_customers` and `sd_business_snapshots`, **+43 each** | **Blocked, and ALSO hover's own queue item** — their claim names *"routable citation-drift findings for sd_customers, sd_business_snapshots and sf_honor_details"* |

**The second row is the more important note: hover is already routing those two.**
Landing them here would be duplicate work on a file they hold, which is what PR
§4.3 exists to prevent.

**The double-run requirement applies when they are landed**, and the tool for it now
exists: `tools/idempotence_double_run.py`. **A repoint is not idempotent** — mine
double-shifted ten citations on its first run and four more on its second.

---

## Item 8 — `sv_wildliferehab`: the verdict, and a gap-ledger row

**The verdict was landed on 2026-09-29 before this file was held** — the cell now
reads **B / B**, *NOT a regulated record as this app is built*, with all six
consumers enumerated and the deciding test named: `sv_compliance` exists, carries a
`type` of Federal/State/OSHA/Other, tracks items like *DEA Registration*, contains
**no wildlife-rehabilitation permit**, and does not read this resource.

### Gap-ledger row, for cody's ledger

| app | gap | source | severity |
|---|---|---|---|
| `SAIRNvet` | `sv_compliance` models Federal/State regulated obligations and carries **no wildlife-rehabilitation permit row**, while the app ships a Wildlife Rehabilitation panel. A licensed rehabilitator's permit has record-keeping and renewal duties, and the app that tracks DEA Registration renewal does not track this one. **The machinery exists** — `complianceDaysUntil()` / `subDocIssues()`-shaped expiry tracking is already in `sv_compliance` — so this is a missing ROW, not a missing feature. | `docs/CRITICALITY-TIERS.md` `sv_wildliferehab` cell (hank, 2026-09-29), derived from `sairnvet.html:6471` writes and all six consumers | **MODERATE** — a product gap, not a data defect. Nothing is wrong today; an obligation the practice has is not modelled. |

---

## What is NOT done here, stated plainly

* **No cell was landed.** Every verdict above is text. `docs/CRITICALITY-TIERS.md`
  is hover's until their claim expires or is released.
* **The `mech_takeoffs` fix is text.** `api/sd-data.js` is fourth's.
* **The three citation repoints are not landed**, and two of them are hover's own
  queue item.
* **I did not read the 32 rows** that `tools/citation_no_source_report.py` now
  flags as claiming a read with no line and no group stamp behind them. That is the
  next pass on this register and it is nobody's yet.

---

# Queue25 — item 2. Delivered as TEXT for the same reason, and the refusal is newer

**2026-09-29 (Hank), second pass.** `docs/CRITICALITY-TIERS.md` is **still held by
`hover`** — a *different, later* claim than the one quoted at the top of this file.
Re-checked at the start of this pass:

```
BLOCKED -- another session already claimed overlapping work:

  session   : hover
  subject   : hover
  task      : eight-item queue: print the tier-a obligation row for routing; confirm the relocated tools path is invisible to build-agent gates and denominators; six independent cold reads at HEAD on unregistered or misdescribed resources; conditional validation of hover2's updated log mirror; one undirected batch through the linter; the weighted rotation draw; an in-flight/blocked/stale inventory; a stale-path methodology sweep across all relocated tooling with selftests run from two working directories.

THE PR 4.3 DECLARATION FOR THIS CLAIM IS IN .claude/claims/hover.json UNDER refusals, WRITTEN THERE BY THE CLAIM TOOL, NOT IN THIS STRING. Each component of this claim checks CLEAR on its own.

FILES: hover_backup_mirror.py hover_cold_scan_pool.py hover_log.py docs/CRITICALITY-TIERS.md
  claimed   : 2026-09-29T17:11:40Z (0.5h ago)
  blocked by: same file or resource: docs/criticality-tiers.md
  also share: criticality, docs, tiers

DO NOT start this. Flag it back to the coordinating chat session and let it decide who runs it.
If you believe that claim is dead, confirm with the other session first -- do not just wait 4 hours for it to expire.
```

**hover's own queue names "six independent cold reads at HEAD on unregistered or
misdescribed resources", which is the same population as item 2 below.** Read my
verdicts against theirs rather than instead of them.

---

## 2a — the reused B sentence, swept across the whole register

### The denominator, and which half of it is trustworthy

| figure | value | how stable |
|---|---|---|
| Register rows containing *"neither money nor a regulated record"* or a near variant | **77** | **Exact and stable.** A literal + 5-variant regex over `docs/CRITICALITY-TIERS.md` at HEAD. |
| Of those, rows that ALSO still say *"Classified by the stated B rule rather than individually read"* | **48**, of which **47** are real | **Stable.** The one false positive is `mech_site_assets` (L496), where both phrases appear inside a **quotation of the wording the cell already corrected** on 2026-09-17. |
| Splitting the other 29 into "live justification" vs "quoted as already corrected" | **NOT reported as a number** | **Unstable, and that is the honest answer.** Three successive tunings of the same regex returned 8, 14 and 17 "quoted". A sentence inside quotation entities 160 characters after a `RE-TIERED` verb is not separable by pattern. The nine A-tier rows the splitter disagreed about were each read by hand instead: `sd_email_threats`, `leg_processions`, `law_optx`, `grd_boq_rates`, `bld_change_orders`, `bld_draws`, `rf_draws`, `law_pimedical`, `mech_site_assets` — **all nine are quotations or correctly-qualified live uses. None is false.** |

**The real population is therefore the 47**, and that is the right population on
its own terms: a cell that says out loud it was never individually read is exactly
the cell the sentence can be false on.

### Method, and why it is not "read the cell again"

The independence discipline asks for a **structurally different** method, so the
verdicts below come from the resource's own **write shape**, never from the cell:

1. For each of the 47, extract the field list actually persisted — the object
   literal passed to the app's own write helper (`sdnData('write',…)`, `senData`,
   `scData`, `mechPushRecord`, `dntPushOne`, `st('<key>', …)`), or the
   `CREATE TABLE` column list, whichever exists.
2. Screen those field names against a money pattern and a regulated-record pattern.
3. **Read every flagged resource individually.** Nothing below is reported off the
   screen alone.

**AND THE FIRST VERSION OF THAT SCREEN WAS WRONG IN THE DIRECTION THAT MATTERS.**
A plus/minus 4000-character window around each resource name flagged **62 of 69** —
every `leg_*` row came back with the identical field set, because SAIRNlegacy's
writers sit next to each other in one file. A screen that flags 90% of its
population has found nothing. The window was replaced with a real extraction
(nearest preceding assignment to the variable actually passed to the write call,
brace-matched), which flags **10 of 47**. The 62-row version is recorded here
because it is the shape a reader would otherwise have to take on trust.

**A SECOND HEURISTIC IS STILL DECLARED AS A COULD-NOT-TELL.** For twelve SAIRNvet
resources the `.push({…})` fallback returned demonstrably wrong objects —
`sv_documents` came back with patient-chart fields, `sv_staff` with report fields.
Those twelve were re-extracted from the precise `getItem` to `return st(...)`
window instead, and the `.push` results discarded. No verdict below rests on them.

### FALSE — by name

#### 1. `mech_checks` (L491) — **FALSE on the money limb. This one changes a tier.**

Current cell: `B` / `B`, *"Operational data lost or wrong: neither money nor a
regulated record. Classified by the stated B rule rather than individually read."*

**It is a cheque register.** `saveCheck()` at `sairnmechanical.html:1527` builds
`{id, num, date, payee, amount, memo}` and `:1541` pushes it to `mech_checks`.

**The app's own registry already says so and the register never read it:**
`api/_resources/sairnmechanical.js:51-56` —
*"THE CHECK REGISTER IS THE SHARP ONE. saveCheck() stores {num, date, payee, amount, memo} — a business's record of money it paid out … losing the register loses the audit trail for every cheque written."*

**Deciding test, both ways.** FAILS the B rule: a field literally named `amount`
holding the value of a cheque written, with `payee` naming who it was written to.
Would PASS the B rule if the row carried only `{num, date}` and the amount lived on
an invoice — the argument that correctly keeps `leg_keepsakeorders` at B.

**Replacement cell text:**

| `mech_checks` | **A** | **B** | **A cheque the business wrote is lost, or its amount or payee is wrong — and the cheque number is reused.** `saveCheck()` (`sairnmechanical.html:1527`) stores `{id, num, date, payee, amount, memo}`; `:1541` syncs it. This is the outbound-payment record, which the A rule's money limb covers directly. **THE NUMBER IS THE SECOND HALF:** `crNum` is incremented when the entry is built and put back only if the local write fails (`:1537`), and `mech_crnum` is a separate write that can fail on its own (`:1542`) — so a lost row or a lost counter is how two cheques come to share a number, which the app says in its own comment | A cheque's **payee and amount** — a named third party and what the business paid them. Commercially sensitive and third-party-identifying, but **not an elevated class**: no PHI, no privileged communication, and no bank-account or routing detail sits on this row. Held at **B** on the class, the same reading `invoices` and `grd_boq_rates` already carry | **RE-TIERED B → A on INTEGRITY, 2026-09-29 (hank). THE SIXTH ROW THIS ONE SENTENCE HAS BEEN FOUND FALSE ON.** Derived from the write shape at HEAD, not from this cell. **`mech_checks` IS DELIBERATELY EXCLUDED FROM THE `mech_docs` REDACTION MAP** (`api/sd-data.js:14323`) — *"and a register with the payee redacted is not a register"* — so the `payee` this cell denied the existence of was already named, in the same file, as a field that must NOT be removed. The integrity promotion is the money limb read plainly; the confidentiality axis stays B and is stated separately so it can be disagreed with on its own |

#### 2. `dnt_vendor_contacts` (L318) — **FALSE on the "no PII" clause. Tier holds at B/B.**

`vEditContact()` at `sairndental.html:6607` stores
`contacts[vendor] = {rep_name, phone, email}` — a **named person's direct phone and
email**, keyed by vendor.

**The money clause is TRUE and must not be swept up with it:** the negotiated
discounts live in a *different* resource, `dnt_vendor_pricing_rules`
(`sairndental.html:6411`), which is what the file's own comment at `:6113` means by
*"a negotiated vendor discount is money"*.

**Deciding test, both ways.** FAILS "no PII": `rep_name` + `phone` + `email` is one
identifiable individual. Held at **B** on the CLASS — business-side contact detail
for a supplier's representative, the identical shape already correctly at B for
`bld_suppliers`, `sf_vendors`, `leg_clergy` and (corrected 2026-09-24 for this exact
reason) `sen_applicants`.

**Replacement cell text:**

| `dnt_vendor_contacts` | **B** | **B** | A vendor rep's contact detail is lost or wrong, and an order goes to the wrong person. Operational: **neither money nor a regulated record, and that clause is TRUE here** — the negotiated discounts are a separate resource (`dnt_vendor_pricing_rules`, `sairndental.html:6411`), checked rather than assumed | **A NAMED INDIVIDUAL's direct phone number and email address.** `vEditContact()` (`sairndental.html:6607`) stores `{rep_name, phone, email}` per vendor. **The "no PII" clause was false on its face and is corrected 2026-09-29 (hank).** Held at **B** on the CLASS, not on absence: business-side contact detail for a supplier's representative — the same shape already at B for `bld_suppliers`, `sf_vendors` and `sen_applicants` (itself corrected 2026-09-24 for the identical stale clause) | **BASIS CORRECTED 2026-09-29 (hank), TIER UNCHANGED, INDIVIDUALLY READ.** A single-object resource replaced wholesale on hydrate (`:6124`), which is why the unconfirmed-write hold at `:6119` exists. Both stale clauses named: the "no PII" claim and the "never individually read" claim |

#### 3. `sv_staff` (L607) — **FALSE on the "no PII" clause. Tier holds at B/B.**

`getStaff()` / `saveStaff()` at `sairnvet.html:7509` / `:7524` hold
`{id, name, role, credential, nextShift}` — named veterinarians and technicians
(`'Dr. Sarah Mitchell', role:'Owner/DVM', credential:'Current'`).

**The regulated-record clause is TRUE:** `credential` holds a currency *flag*
(`'Current'`), not a licence number, issuer or expiry. The app's regulated records
live in `sv_compliance` — the same deciding test that settled `sv_wildliferehab`.

**Deciding test, both ways.** FAILS "no PII": employee name + role. Held at **B** on
the staff-side convention — employment identity, not client PHI, not money. Would go
to A if `credential` ever held a licence number or an expiry the app computed a
clearance from, which is what `mech_credentials` does one app over.

**Replacement cell text:**

| `sv_staff` | **B** | **B** | A staff roster row is lost or a shift is wrong. Operational: **neither money nor a regulated record, and both clauses are TRUE here** — `credential` holds a currency FLAG (`'Current'`), not a licence number, issuer or expiry, and nothing computes a clearance from it. The app's regulated obligations live in `sv_compliance`, which is the same deciding test that settled `sv_wildliferehab` | **A NAMED EMPLOYEE's identity and professional role** — `getStaff()` (`sairnvet.html:7509`) holds `{id, name, role, credential, nextShift}`, e.g. *Dr. Sarah Mitchell / Owner-DVM*. **The "no PII" clause was false and is corrected 2026-09-29 (hank).** Held at **B** on the staff-side convention: employment identity, the same class as `sen_` and `alf_` roster rows — not client PHI, not money | **BASIS CORRECTED 2026-09-29 (hank), TIER UNCHANGED, INDIVIDUALLY READ** from the write shape at HEAD. **WHAT WOULD MOVE IT:** if `credential` ever carried a licence number or an expiry the app gated dispatch on, this becomes `mech_credentials`' shape and takes A on the regulated limb. Stated so the next reader checks the field rather than the tier |

### TRUE but stale in its own basis — one row

#### `sv_herdhealth` (L587) — the sentence is TRUE; the "never individually read" clause is not.

`getHerds()` / `saveHerds()` (`sairnvet.html:6326` / `:6340`) hold
`{id, herd, species, headCount, lastVisit, status, vaccinationCompliance, scc}`.
**All consumers enumerated:** `renderHerdHealth` (`:6344`), two further readers
(`:6375`, `:6406`), the table at `:6395`, and one CSV export button (`:1180`).
Nothing files, nothing computes against a permit or a reporting window.
`vaccinationCompliance` is a percentage and is `null` in the seed. `herd` is a
**business** name (*Miller Dairy Farm*), not a person.

**Verdict: B/B stands on both axes.** The clause to strike is *"Classified by the
stated B rule rather than individually read"* — it has now been read, and the
deciding test is the app's own `sv_compliance` resource, exactly as for
`sv_wildliferehab`.

### `customers` (L535) — found by this sweep, not on the original list

Not one of the eight named, and reported because the sweep turned it up:
SAIRNscape's `customers` row is `B`/`B` with *"No elevated confidentiality class —
no PII … Classified by the stated B rule rather than individually read"*, while
`sairnscape.html` writes `{id, name, service, recurring, phone, email, address,
notes}` — **a customer's name, phone, email AND street address.** Same false clause,
same class-based B verdict as `dnt_vendor_contacts`. **Not written up as replacement
text here**, because it is outside the eight and I will not extend a held file's
diff by one more row than the item asked for; it belongs to whoever takes the next
pass and is recorded above so it is not lost.

### Clear — flagged by the screen, read, and the sentence holds

`grd_boq_rates` (already A on money, 2026-09-22 — the sentence is quoted as the
corrected wording), `sv_financials` (already A, 2026-09-28, same), `law_optx`,
`law_pimedical`, `law_timeentries`, `bld_draws`, `bld_lien_waivers`,
`leg_deathrecords` (all already A on the relevant axis), `dnt_supplies`
(`unit_cost` is a purchase-price reference on a supply row, not a payment),
`leg_keepsakeorders` (`quantity`, no price field — the charge is on the invoice),
`leg_petcases` (basis already corrected 2026-09-29; the decedent is a pet),
`sb_hire` (`rate` is a POSTED RANGE on a job advert, already public).

---

## 2b — the eight "no register row" resources. **Seven of the eight are not register rows at all, and one does not exist.**

**THE ITEM ASKED FOR EIGHT ROWS AND I AM DELIVERING ONE PLUS FOUR ROUTED FINDINGS,
so the disagreement is stated first rather than buried.** The register says what its
unit is in its own header: *"**The unit is `api/_resources/<app>.js`** — the same
unit the SOUP register and the traceability matrix already operate on, reused rather
than invented."* Checked at HEAD: **none of the eight names appears in any app's
`resources` array.** They are `localStorage` keys. Writing eight rows for them would
silently redefine the register's unit to "any key the app writes" — which is the
same class of mistake the header already records and corrected once (*"The first
version tiered whole apps, and measuring it is what proved that wrong"*). A register
whose unit moves without saying so stops being comparable across apps.

So each is resolved to what it actually is, with the deciding test, and the ones that
carry a real risk are routed to the place that already owns them.

| named | what it actually is, at HEAD | deciding test | where it belongs |
|---|---|---|---|
| `scp_customers` | **A local storage key for an ALREADY-REGISTERED resource.** `sairnscape.html:2734` maps `['customers','scp_customers']` — the server resource is `customers`, which has a row at L535 | Is the name in `api/_resources/sairnscape.js`'s `resources` array? **No** — `'customers'` is | Nowhere new. **But L535's own "no PII" clause is FALSE** (name, phone, email, address) — see 2a |
| `scp_invoices` | Same shape: `['invoices','scp_invoices']`, and `invoices` has a row at L536 (**A/B**, "Money") | Same test, same answer | Nowhere new. Already correctly A |
| `sen_evv_config` | **A LEGACY KEY NOTHING WRITES ANY MORE.** Three occurrences in `sairnsenior.html`: a comment (`:1754`), the `SEN_UNSCOPED_CACHES` list (`:1761`), and a **one-way migration read** at `:5732` that lifts it into `sen_settings.evv_config` | `grep -n sen_evv_config sairnsenior.html` returns no `st(` or `setItem` — **no writer exists.** The live resource is `sen_settings`, whose registry comment at `api/_resources/sairnsenior.js:58` already says it *"holds 'agency_profile' and 'evv_config'"* | Nowhere new. **Finding (3) below:** `SEN_UNSCOPED_CACHES` declares a key nothing writes |
| `sen_evv_queue` | **An offline outbox, not a record store.** `SEN_EVV_QUEUE_KEY` (`:3015`), capped at 200 (`:3017`), FIFO stop-on-first-failure flush (`senFlushEvvQueue`, `:3037`). Entries are `{queued_at, payload}` and are **deleted on successful send** | Does it hold anything after a successful sync? **No** — it is a transport buffer for `sen_visits`, which is registered | Nowhere new. It is upstream of a registered resource, not a resource |
| `law_strike_log` | A local-only jury-strike log: `juryStrikeLog`/`juryStrikeSave` (`sairnlaw.html:7156`/`:7157`), three consumers, `{juror_id, reason, juror_statement, case_relevance, recorded_at, recorded_by}` | In `api/_resources/sairnlaw.js`? **No.** Nor in its `notSynced` list, which holds only `law_billingcodes` | **Finding (2) below.** Not a register row — a missing `notSynced` declaration, which `tools/local_only_collection_check.py` is the existing owner of |
| `sd_owner_pin` | **A DEAD KEY. One occurrence in the entire repository** — inside `itaClearData`'s keep-list at `stonedesk.html:42326`. Nothing writes it, nothing reads it | `grep -rn "owner_pin\|ownerPin\|OWNER_PIN" --include=*.html --include=*.js --include=*.sql .` → **one hit, the keep-list itself** | **Finding (1) below.** A register row here would register a resource that does not exist |
| `sf_district_keypair` | **An ECDSA P-256 PRIVATE key JWK in `localStorage`, in the clear.** `sfEnsureKeypair()` (`sairnfreedom.html:7215`) generates it with `extractable: true`, exports both JWKs and stores `{privateJwk, publicJwk, created}` at `:7224` | In the `resources` array? **No.** It is in `api/_resources/sairnfreedom.js`'s **declared exclusion block** (`:85-86`): *"SIGNING KEY MATERIAL. It must not leave the device, and a backup is the opposite of that"* | **Finding (4) below.** The exclusion is a real, reasoned declaration and `tests/sairnfreedom_key_reconciliation.js` already executes it. What is missing is a **criticality statement**, not a sync row |
| **`sf_district_known_keys`** — *reported to me as `sf_known_keys`, which does not exist* | **THE REAL NAME, recorded RENAMED-REAL-2026-09-30.** `K_KNOWNKEYS='sf_district_known_keys'` at `sairnfreedom.html:7163`, read by `getKnownKeys()` at `:7481`: the trust-on-first-use fingerprint map `{entity_id -> {fingerprint, firstSeen}}`. In `api/_resources/sairnfreedom.js`'s declared EXCLUSION block (`:88-91`), **not** in its `resources` array | `grep -rn sf_known_keys .` → **nothing**. THE COMMAND IS QUOTED VERBATIM AND NOT REWRITTEN: it returning nothing is what establishes that the reported name does not exist, and substituting the real name into it would destroy the evidence while looking like a correction | **A NAME NOBODY CAN LOOK UP IS WORSE THAN A WRONG TIER**, which is why this is recorded under the real name rather than left as a footnote. **ITS INTEGRITY IS THE SHARP AXIS and it is the opposite way round from `sf_district_keypair`:** a stolen private key forges signed district reports, while a tampered fingerprint makes a forged report **VERIFY SILENTLY on this device**. A lost key regenerates (`sfEnsureKeypair` does exactly that); a tampered trust anchor does not announce itself |

### The four findings this resolves into

**(1) `sd_owner_pin` is preserved by a demo wipe and written by nothing.** `itaClearData`
(`stonedesk.html:42326`) deletes every `sd_`-prefixed key except
`['sd_owner_pin','sd_license_key','sd_plan', ITA_USERS_KEY, ITA_AUDIT_KEY]`. Four of
those five are live. `sd_owner_pin` is the fifth and has no writer and no reader
anywhere in the repo. **Two readings and both need action:** either an owner-PIN
feature was removed and its guard was not, in which case the keep-list is stale; or
one was planned and the guard was written first, in which case the guard is a promise
about a field that will be stored under a different name and will therefore be wiped.
**Severity MODERATE**, not high — nothing is broken today, and that is exactly why it
will still be there when it does matter. **Deciding test:** set
`localStorage['sd_owner_pin']`, run `itaClearData()`, confirm it survives — it will,
proving the guard works and protects nothing.

**(2) `law_strike_log` is a local-only collection with no declaration.** Every
`sairnlaw` key is meant to be in the `resources` array or in `notSynced`, which is
what `tools/local_only_collection_check.py` reads and what
`tests/sairnfreedom_key_reconciliation.js` does mechanically for SAIRNfreedom. This
one is in neither, so *"a peremptory-strike record lives in one browser"* is currently
**news rather than a decision** — the exact distinction `sairnmechanical.js` states
above its own `notSynced` list (*"A declaration is NOT coverage … What it changes is
whether that is news"*). **Severity MODERATE.** The record matters: a Batson challenge
is answered from the contemporaneous reason recorded at the time of the strike, and one
cache clear removes it. **Deciding test:** add `'law_strike_log'` to `notSynced` with
its reason; `local_only_collection_check.py` should go from silent to accounted-for on
that key.

**(3) `SEN_UNSCOPED_CACHES` declares a key nothing writes.** `sen_evv_config` is in
the unscoped list at `sairnsenior.html:1761` with a reason — *"editable offline —
purging it on a shift change would throw away an unsynced settings edit"* — that is
**no longer true**, because there is no writer: the settings edit now lands in
`sen_settings`. The migration read at `:5732` is one-way. **Severity LOW**, and it is
recorded because `tests/phi_cache_scoped_to_user.js` fails if a key is in *neither*
list and passes if it is in *either* — so a dead key sitting in the unscoped list is
invisible to the very test that governs the list. That is the item-8 shape (*nothing
announces the day a check stops testing anything*) in a two-line list. **Deciding
test:** the test should also require that every listed key has a writer; it would then
fail on this one.

**(4) `sf_district_keypair` — the criticality statement that is missing, written here.**
Not as a register row, because it is not a register unit. As a paragraph for whoever
next edits `docs/CRITICALITY-TIERS.md`, in the section on local-only keys:

> **`sf_district_keypair` (SAIRNfreedom, local-only, NOT an `api/_resources` unit).**
> Would be **A on confidentiality** if it were a register unit. `sfEnsureKeypair()`
> (`sairnfreedom.html:7215`) generates an ECDSA P-256 key pair with
> `generateKey(KEY_ALG, true, ['sign','verify'])` — `extractable: true` — exports
> **both** JWKs and stores `{privateJwk, publicJwk, created}` in `localStorage` at
> `:7224`. Any script running in that origin can read the private key and sign a
> district report indistinguishable from a genuine one. **The mitigations are real and
> bound the statement without defeating it:** it is deliberately excluded from backup
> (`api/_resources/sairnfreedom.js:85`), the exclusion is executed rather than asserted
> by `tests/sairnfreedom_key_reconciliation.js`, and import is verify-first with
> trust-on-first-use fingerprinting that flags a changed key loudly. Those defend the
> key against LEAVING the device. They do nothing about a reader ON it.
> **`extractable: true` is the load-bearing choice** and it is forced by the design —
> a non-extractable `CryptoKey` cannot be `JSON.stringify`d into `localStorage`, so
> persisting the identity across reloads at all requires extractability. The honest
> statement is therefore *"this is the cost of a device-local signing identity in a
> browser"*, not *"this is a defect"* — and it should be written down as a cost rather
> than left unstated, which is the only part that is wrong today.

---

## 2c — raw model output persisted with no redaction, in four more places. **Pasteable text for `fourth`.**

`api/sd-data.js` is fourth's. **Nothing below is applied.**

### The precedent is already in that file, which is what makes this a line rather than a design

`api/sd-data.js:14288-14360` redacts model-extracted text **at the boundary**, driven
by a map rather than a resource name, with the reason written out:

> *"WHAT EARNS REDACTION IS PROVENANCE: text a model extracted from an IMAGE,
> containing whatever was in the photograph, which no human chose to store. Adding a
> third such field is now a line in this map."*

All four resources below are that exact provenance, and none of them goes through it.
`api/_lib/mech-redact.js` and the `mechRedact` require at `:83` already exist.

### The four, with the field and the insertion point

| resource | field(s) carrying model output over a photograph | written at | server write branch |
|---|---|---|---|
| `rf_photos` | `ai_analysis` (from `pendingAiRawText`) | `sairnroofing.html:5348` | `api/sd-data.js:7190` (`resource === 'rf_photos'`, read+write) |
| `scp_progress_photos` | `ai_analysis` | `sairnscape.html:3425` | `api/sd-data.js:4987` (`scp_progress_photos` write) |
| `grd_progress_photos` | `ai_analysis` | `sairngrounds.html:3490` | `api/sd-data.js:4106` (`grd_progress_photos` write) |
| `bld_photo_analyses` | **`full` AND `summary`** — `summary` is `full.slice(0,140)`, so redacting only one leaves the identifiers in the other | `sairnbuild.html:3665` | `api/sd-data.js:12260` (the generic `BLD_RESOURCES[resource] && action === 'write'` branch) |

### The change, in the same shape the file already uses

Add one map beside the existing `MECH_SCANNED_TEXT`, near the top of the handler so
all four branches can reach it:

```js
// ── MODEL OUTPUT OVER A PHOTOGRAPH, REDACTED AT THIS BOUNDARY ─────────────
// Same rule and same reason as MECH_SCANNED_TEXT below: what earns redaction is
// PROVENANCE -- text a model extracted from an IMAGE, containing whatever was in
// the frame, which no human chose to store. Four resources, one list, so adding a
// fifth is a line rather than a fifth copy of this comment.
//
// THE VALUE IS AN ARRAY, NOT A STRING, and bld_photo_analyses is why: fpSave()
// (sairnbuild.html:3665) stores BOTH `full` and `summary`, where summary is
// full.slice(0,140). Redacting one and not the other leaves the identifiers in
// the first 140 characters -- which is the half the list view renders.
const PHOTO_MODEL_TEXT = {
  rf_photos:            ['ai_analysis'],
  scp_progress_photos:  ['ai_analysis'],
  grd_progress_photos:  ['ai_analysis'],
  bld_photo_analyses:   ['full', 'summary']
};
function redactPhotoModelText(resource, payload) {
  const fields = PHOTO_MODEL_TEXT[resource];
  if (!fields || !payload) return payload;
  let out = payload, applied = 0, complete = true, notes = [];
  for (const f of fields) {
    if (payload[f] === undefined || payload[f] === null) continue;
    const red = mechRedact.redactDocumentText(payload[f]);
    out = Object.assign({}, out, { [f]: red.text });
    applied += red.redactions;
    if (!red.complete) complete = false;
    if (red.note && notes.indexOf(red.note) === -1) notes.push(red.note);
  }
  if (out === payload) return payload;
  // Carried ON THE ROW, not just returned -- a row that looked redacted with no
  // account of its limits is the false confidence this exists to avoid. Same
  // decision, same wording, as the mech_docs block.
  return Object.assign({}, out, {
    redaction: {
      applied_at: nowISO(),
      redactions: applied,
      complete: complete,
      note: notes.join(' ')
    }
  });
}
```

Then **one line** in each of the four write branches, immediately after the existing
`payload.id` validation and **before** the `fetch(rest(...))` that sends it:

```js
      payload = redactPhotoModelText(resource, payload);
```

For the `BLD_RESOURCES` branch, `payload` is used twice in the body it sends
(`[idCol]: String(payload.id)` and `data: payload`), so assigning back to `payload`
covers both. In the three dedicated branches the same assignment is enough.

### Three things this deliberately does NOT do, each with the reason

* **It does not refuse the write.** A photo whose analysis still contains something
  after the pass is stored, redacted as far as the pass can and with the residue named
  on the row — because refusing loses the field worker's capture and teaches people to
  stop photographing, and a feature nobody uses protects nothing. Verbatim the
  argument already in the `mech_docs` block.
* **It does not touch `photo_b64`.** The image itself is the record. Redacting the
  photograph is the over-redaction failure the same block names — *"a different way to
  lose the record"*.
* **It does not redact the local copy.** The client-side redactor is a convenience and
  never a boundary. This is the boundary, and it applies regardless of what the caller
  sent, including a caller that is not the app.

### What must be true before this lands, and it is not true yet

**`api/_lib/mech-redact.js` was written for SCANNED WORK ORDERS, and three of these
four are OUTDOOR SITE PHOTOS.** Its pattern set has not been re-qualified against a
progress-photo analysis, and byte-identical is not safe-in-context. Before this lands,
somebody should drive `redactDocumentText` over a real `ai_analysis` string from each
of the four and confirm (a) it removes what it should and (b) it does **not** remove
the quantities `parsed_quantities` is derived from in `rf_photos`, which would silently
break the takeoff. **Stated as a precondition rather than done here**, because
`api/sd-data.js` and its suite are fourth's and a fixture proving this is part of the
same change.

---

# Queue25 — item 6. The counts were wrong, and the fix was the tool, not 38 cells

**2026-09-29 (Hank).** The item asked me to re-read and cite, or downgrade, the
**32** rows claiming an individual read with no evidence and the **6** carrying no
stated basis at all. **Reading all 38 by hand is what the number was for, and it
showed that 33 of the 38 were the report's own criteria being wrong.**

## Before and after, on 391 rows

| bucket | before (`2026-09-29.1`) | after (`2026-09-29.2`) | delta |
|---|---|---|---|
| cite at least one line | 182 | **184** | +2 |
| CITE NOTHING | 209 | **207** | −2 |
| … ADMIT they were not read individually | 65 | 65 | 0 |
| … carry a 3.2 GROUP STAMP | 106 | 106 | 0 |
| … show a **DATED or FIELD-LIST read** *(new bucket)* | — | **31** | +31 |
| … **CLAIM a read with none of the above** | **32** | **0** | **−32** |
| neither stated | 6 | **5** | −1 |

**NOT ONE REGISTER ROW WAS EDITED TO GET THERE.** Every movement is a criterion
of `tools/citation_no_source_report.py` being corrected. The three corrections:

**1. A dated per-row read stamp was being read as no evidence at all — 27 rows.**
Twenty-seven of the 32 carry *"**Confidentiality individually read 2026-09-22**"*,
or the same with words in between (*"confidentiality individually read and left at
B, 2026-09-23"*). That is the 3.2 pass's per-row stamp **without a group label** —
the identical kind of disclosure `GROUP_STAMP` already accepted, one degree less
labelled. **This is the same mistake the tool had already corrected once**, when
the bucket went from 138 to 32 for exactly this reason, and it stopped one shape
short.

**2. A field list lifted out of the source was being read as no evidence — 4 rows.**
`sv_scribe_consent` carries *"READ OUT OF THE APP: `{asked_at, date, patient,
answer, statement_version, asked_by}`"*; `rf_company_programs` and
`rf_job_warranties` carry *"READ OUT OF THE **HANDLER**: `{…}`"*. A field list
taken out of the code IS the evidence; it simply has no line number. **And a rule
keyed on the single word `APP` would have missed both `HANDLER` rows**, which is
why the pattern now takes `READ OUT OF THE <ANYTHING>:` followed by a brace list.

**3. `re-derived` fired on prose about the DATA, not about a read — 1 row.**
`law_mattermilestones`'s only trigger was *"the matter survives it and the stage
can be **re-derived**"* — a sentence about whether a lost milestone can be
reconstructed. It was a false accusation, and the sole one. The alternative now
requires the object: `re-derived at HEAD`, `re-derived from the`, `re-derived out of`.

**And one separate fix, measured at exactly 2 rows so it is not overstated:**
`CITE = r':\d{3,5}'` **could not see a line number under 100.** The three-digit
floor is right for a bare `:NN` in prose, and wrong for a citation attached to a
path — and `api/_resources/*.js` declarations live at the TOP of their files, so
`api/_resources/stonedesk.js:27` (`style_profile`) and
`api/_resources/sairnroofing.js:56` (`rf_proposals`) were both counted as citing
nothing. Two of 391. **Reported anyway, because a citation rule that silently
excludes the first 99 lines of every file is wrong about a shape it will keep
meeting.**

## The honest reading of a zero

`CONTRADICTORY` now reads **0**, and the tool prints its own history beside it
rather than a clean bill: *138, then 32, then 0, with no row edited.* **The figure
to carry forward is the one that has not moved: 207 of 391 rows point at no LINE,
142 of them Tier A.** That is a real coverage gap. What is closed is the claim that
32 rows asserted evidence they did not have.

## Controls locked, both directions

`tests/run_citation_no_source_probe.py`: **29 arms, 0 failures**, up from 12. Every
new shape has a known-bad twin, because a fix that empties a bucket by widening is
indistinguishable from a fix that empties it by measuring:

* a date **before** the claim with no axis word → **still a contradiction**
* an axis and a read with **no date** → **still a contradiction**
* the words *"READ OUT OF THE APP"* with **no field list** → **still a contradiction**
* `re-derived at HEAD` → **still counted** (the narrowing did not kill the real form)
* a bare two-digit `:45` with **no path** → **not** promoted to a citation
* a cell carrying **both** a group stamp and a dated read → reported under the
  **GROUP**, because a reader can disagree with a named group and cannot disagree
  with a date (14 real `sv_` rows carry both)

## The 5 that are genuinely uncited — read at HEAD, citations below as TEXT

`docs/CRITICALITY-TIERS.md` is hover's, so these are replacement fragments. **Each
was read, not grepped**: a located line is not a read, and citing a line I had only
located would manufacture exactly the evidence these rows are accused of lacking.

### `law_matterdocs` (L432) — **A/A holds, and there are FOUR write paths, not one**

Append to the evidence cell:

> **CITED 2026-09-29 (hank), read at HEAD. FOUR WRITE PATHS, and the register knew
> of none of them.** `saveMatterDoc()` (`sairnlaw.html:3118`) writes
> `{id, matter_id, title, doc_type, url_or_ref, content_text, ocr_text, source,
> shared_with_client, revisions, uploaded_date, created_at}` and syncs at `:3124`.
> Three more build the same shape: the OCR path (`:4064`, synced `:4070`) puts the
> scanned text into **both** `content_text` and `ocr_text` and seeds `revisions`
> with a full `content_snapshot`; the email path (`:4084`, synced `:4090`); and the
> **AI-draft path (`:4213`, synced `:4219`), whose `last_edited_by` is literally
> `'AI Draft (unreviewed)'`**. Two further syncs at `:4120` and `:4311` write an
> edited row back. Server map entry `api/sd-data.js:13120`.
> **THE FIELD THAT SHARPENS THE CONFIDENTIALITY ARGUMENT IS `shared_with_client`,
> and it is `false` on every one of the four creation paths** — so disclosure to
> the client is a per-document decision recorded on the row, which makes a wrong
> value a disclosure event rather than a display bug. **And `revisions[]` carries
> `content_snapshot`, so the row holds the document's HISTORY as well as its
> current text** — the integrity limb is not one document but every version of it.

### `law_mattermilestones` (L437) — **A/A holds; this row was a FALSE POSITIVE, and the citation is added anyway**

> **CITED 2026-09-29 (hank), read at HEAD. THIS ROW WAS NEVER CONTRADICTORY —
> `tools/citation_no_source_report.py` matched the word `re-derived` inside this
> cell's own sentence *"the stage can be re-derived"*, which is about reconstructing
> lost DATA, and accused the row of asserting a read it never claimed. The tool is
> fixed; the citation is added because the row genuinely had none.**
> `saveMilestone()` (`sairnlaw.html:3098`) writes
> `{id, matter_id, title, date, notes, created_at}` and syncs at `:3101`. Server map
> entry `api/sd-data.js:13121`. **The confidentiality argument this cell already
> makes is confirmed by the field list: `notes` is free text about what is happening
> on an identified client's matter and when**, which is the *"says what is happening
> to an identified client"* limb, now with the field behind it.

### `leg_documents` (L462) — **A/A holds, and the cell's own field list is confirmed verbatim**

> **CITED 2026-09-29 (hank), read at HEAD, and the cell's field list was already
> right — which is worth saying, because a row can be uncited and correct.**
> `saveDoc()` (`sairnlegacy.html:2788`) writes
> `{id, case_id, doc_type, status, esign_name, esign_at, content_text, created_at}`
> and syncs at `:2792`; `sendDoc()` re-writes the row at `:2799` and a third path at
> `:2820`. Server map entry `api/sd-data.js:13211`. `esign_name` and `esign_at` are
> empty at creation and filled on execution, which is the point: **the same row is a
> draft and then an executed instrument, so the integrity limb covers a transition
> and not just a record.**

### `sen_visits` (L566) — **A/A holds, and the THIRD write path is the one no citation would have found**

> **CITED 2026-09-29 (hank), read at HEAD. THREE WRITE PATHS AND THEY ARE NOT
> INTERCHANGEABLE.** (1) `saveVisit()` (`sairnsenior.html:3139`) writes
> `{id, client_id, client_name, scheduled_date, scheduled_start, scheduled_end,
> service_type, assigned_employee_id, status}` and syncs at `:3145` — and it is
> **gated before the record is built** by `senCertGate()` (`:3137-3138`) so a
> refusal leaves nothing behind. (2) The clock path syncs the EVV payload at
> `:3078`. (3) **The offline queue flush at `:3047` replays `sen_evv_queue`
> entries into this resource FIFO, stopping at the first failure** — so while a
> device is offline the durable record of a payable visit is in an unregistered
> `localStorage` key and not here. Server write branch `api/sd-data.js:6065`.
> **That third path is why `sen_evv_queue` needs a home of its own** (see the
> unit-disagreement row in `docs/SAIRN-OPEN-WORK-INDEX.md`): this cell's A/A rests
> on `sen_visits` being the record, and for as long as a device is offline it is not.

### `sf_signatures` (L375) — **A/A holds, and the row binds a person to a document VERSION and HASH**

> **CITED 2026-09-29 (hank), read at HEAD.** The key alias is
> `K_SIGNATURES='sf_signatures'` (`sairnfreedom.html:6326`), read by
> `getSignatures()` (`:6333`); the single write is `st(K_SIGNATURES, list)` at
> `:6498`, pushing `{id, docId, docTitle, version, hash, signer, typed, signed}`
> (`:6496-6497`). Server map entry `api/sd-data.js:12689`.
> **THE ROW CARRIES THE DOCUMENT'S `version` AND `hash`, which is what makes the
> A-integrity argument stronger than "an executed signature":** the signature is
> bound to a specific version of a specific document, so altering either the row or
> the document breaks a link that was the whole point of capturing it.
> **AND THE SIGNATURE IS A TYPED NAME CHECKED AGAINST THE SELECTED SIGNER**
> (`:6489-6494`), which refuses a mismatch with the app's own sentence — *"A
> signature that does not match the name it is filed under is not evidence of
> anything."* That refusal is the reason `typed` and `signer` are both stored rather
> than one being derived from the other, and a reader of this row should know the
> check exists before judging the tier.

---

# The finding from the discharged review, routed — `sc-denial-reconcile.js`

**2026-09-29 (Hank).** Discharging cody's `2026-09-27T03:53:49Z` obligation
(committed `0786c19a`) produced one finding. **The code is correct on all three
named worries; what is wrong is one reason string that names a cause it does not
know.**

**WHO HOLDS THE FILE: nobody.** `python tools/sairn_claim.py check hank
"api/_lib/sc-denial-reconcile.js negative aggregate count reason wording"` returns
**CLEAR**. cc's live claim is `api/sd-data.js` and a derive-charges test; cody's
`cody-review20` is a discharge obligation, not this file. It is printed here rather
than applied because `api/_lib/sc-denial-reconcile.js` is **not in hank's queue25
claim file list**, and the author of record is **cody** (the obligation's
`author_session`). Cody or whoever claims it next should paste it.

## The finding

`api/_lib/sc-denial-reconcile.js:166-170`:

```js
    } else if (r.aggregate_count === null) {
      state = 'no_aggregate_count';
      reason = 'The aggregate row carries no usable count, so the two cannot be '
        + 'compared. This is NOT a count of zero -- nobody has entered one.';
```

**A NEGATIVE count reaches this branch, and somebody did enter one — they entered
`-1`.** Driven, not read:

| entered | state reached |
|---|---|
| `0`, no events | `aggregate_only` — *"An aggregate count of 0 with no logged events"* |
| `0`, 3 events | `events_higher` |
| `''` or `null` | `no_aggregate_count` |
| **`-1`** | **`no_aggregate_count`** |

The first three are exactly right. **The module's INTENT is already right too:**
arm `A2` at `api/_lib/sc-denial-reconcile.test.js:72` asserts
`countOf(-1) === null` **deliberately**, under the assertion message *"a count of
zero IS entered data and must survive"*. So the refusal is intended; only the
reported REASON collapses two different facts.

**Why it matters on this resource rather than being pedantry: an empty count is an
unfinished row, and a negative denial count is a data-entry fault or a sign error
somebody should look at today.** Both arrive at the reader as the same sentence, and
the sentence asserts the one that is false.

## The change — a sentence, not a redesign

**Do NOT add a fourth state.** A `unusable_aggregate_count` state would have to be
counted in `totals`, which changes the partition every caller reads, for a
distinction the reader can be told in words. Replace lines `:168-170` with:

```js
    } else if (r.aggregate_count === null) {
      state = 'no_aggregate_count';
      // ── THE REASON USED TO SAY "nobody has entered one" AND THAT IS A CAUSE
      // THIS BRANCH CANNOT KNOW (corrected 2026-09-29, routed by hank while
      // discharging the 2026-09-27T03:53:49Z review). countOf() returns null for
      // an EMPTY field and for a value that is not a non-negative whole number
      // alike, so a hand-typed `-1` landed here wearing "nobody has entered one".
      // On a denial register those are different problems: an empty count is an
      // unfinished row, and a negative count is a sign error somebody should see
      // today. THE REFUSAL IS CORRECT AND STAYS -- test arm A2 pins
      // countOf(-1) === null on purpose. Only the sentence was wrong.
      reason = 'The aggregate row carries no usable count, so the two cannot be '
        + 'compared. This is NOT a count of zero: the field is either empty or '
        + 'holds a value that is not a non-negative whole number.';
```

**And one more arm, so the sentence cannot drift back.** In
`api/_lib/sc-denial-reconcile.test.js`, beside `A2`:

```js
test('A2b. the no_aggregate_count REASON does not name a cause it cannot know',
  () => {
    const empty = reconcile([{ code: 'A', count: '', amount: 100 }],
                            [{ code: 'A', amount: 100 }]);
    const negative = reconcile([{ code: 'A', count: -1, amount: 100 }],
                               [{ code: 'A', amount: 100 }]);
    assert.strictEqual(empty.rows[0].state, 'no_aggregate_count');
    assert.strictEqual(negative.rows[0].state, 'no_aggregate_count',
      'a negative count must still be refused -- A2 pins countOf(-1) === null');
    // THE ARM IS ON THE CLAIM, NOT ON THE WORDING. It does not require any
    // particular sentence; it requires that the sentence does not assert the
    // ONE thing this branch cannot distinguish.
    for (const r of [empty.rows[0], negative.rows[0]]) {
      assert.ok(!/nobody has entered one/i.test(r.reason),
        'the reason claims the field is empty, and it cannot tell: ' + r.reason);
    }
  });
```

## The header note — the denominator, if a headline ratio is ever added

**`totals` deliberately has no single headline figure, and that is why it cannot
flatter anything.** Driven with a code present only in the aggregates and a
different code present only in the events: `codes 2, agrees 0, aggregate_only 1,
events_only 1, not_comparable 0`. `byCode` is built from **both** sides, so `codes`
counts the **union**, `agrees` is reachable only where both sides exist and match,
and every non-comparable state has its own bucket.

**If a headline ratio is ever added, `agrees / codes` is the WRONG denominator.**
Add this to the `MONEY IS COMPARED IN CENTS` header block:

> ── IF A HEADLINE RATIO IS EVER ADDED, THE DENOMINATOR IS NOT `codes` ────────
> `totals` has no single figure on purpose, which is why it cannot flatter the
> result. Should one be wanted, **`agrees / codes` is wrong**: `codes` is the
> UNION of both stores, so every row that could not be compared at all —
> `aggregate_only`, `events_only`, `no_aggregate_count` — pushes the ratio down
> and makes a reconciliation of two stores that barely overlap look like a
> reconciliation that disagrees. **The honest figure is `agrees` over the codes
> that were actually COMPARABLE:**
>
>     agrees / (agrees + aggregate_higher + events_higher)
>
> with the other four buckets printed beside it rather than folded in, because a
> ratio whose denominator hides the unmatched rows is the fabricated-KPI shape
> this module's own header already refuses.

## What this does NOT claim

* **The code is correct.** All three of cody's named worries were driven against
  the real module: the third state is right, the cents arithmetic is sound (both
  sides go through the same `Math.round(n*100)`, so a rounding artefact can only
  shift both halves identically), and `agrees` does not flatter the total.
* **The module is still UNWIRED**, confirmed independently: grepping the whole repo
  for `sc-denial-reconcile` outside the module and its own suite returns nothing.
  That is declared loudly in its header and in three test arms, which is the right
  treatment for the SAIRNmechanical G3 defect — not something to fix quietly.
* **Nothing above is applied.** The file is not in my claim.

---

# 2026-09-30 — reconciliation against fourth and H1, and the register-scope ruling

**Hank.** `docs/CRITICALITY-TIERS.md` checked **CLEAR** at the start of this pass
(hover released it), so the cells below are **LANDED**, not delivered as text. Claim
is exact file paths only, nothing reworded to pass the matcher.

---

## 1. Reconciled against `docs/2026-09-29-cells-fourth.md` — conflicts by resource

### `locations` — **NO CONFLICT, AND THE REASON IS A GAP IN MY OWN SWEEP**

Fourth's cell and mine are disjoint because **`locations` was invisible to the
2026-09-29 money-sentence sweep.** That sweep's population was *rows carrying
"neither money nor a regulated record"* **and** *"classified by the stated B rule
rather than individually read"* — 47 rows. `locations`' integrity cell read
*"Shared operational reference; `api/_lib/dnt-location.js` stamps location on
writes elsewhere"* and **never carried the money sentence**, so the selector
skipped it — while its CONFIDENTIALITY cell did carry the never-individually-read
clause, and the row does hold a street address.

> **A selector keyed on one clause cannot see a row that fails the other.** My 47
> was the intersection; the never-read population alone is larger. Fourth found the
> row my population definition excluded by construction, and that is the finding
> rather than a disagreement.

**Two corrections to fourth's delivered text, both landed:**

1. **A DRIFTED CITATION I INTRODUCED BY PASTING IT.** `api/sd-data.js:1302` is the
   right line — it reads `'locations': 'stonedesk'` — but `register_freshness_check`
   reported it DRIFTED because the sentence named `sd_locations` beside it and that
   identifier resolves to `:2846/:2854/:2887`. Rewritten to cite the app-map entry
   by the identifier actually on the line, and the table separately at `:2887`.
2. **The delivered text says the write is management-only *because* of the rename.**
   That is the code's stated reason and not the whole one: `:2872-2876` gates the
   whole write verb, rename included.

**Fourth's central claim is confirmed and is the sharper half:** the previous basis
cited `api/_lib/dnt-location.js`, SAIRNdental's write-side stamp (its own header,
lines 1-8), for a row whose resource is StoneDesk's. A different app's file is not
evidence for this row.

### `sv_herdhealth` — **SAME VERDICT, FOUR CONFLICTS IN THE EVIDENCE, THREE OF THEM MINE**

Both reads land **B/B** and both strike *"classified by the stated B rule rather
than individually read"*. The evidence conflicts:

| | fourth | hank (2026-09-29) | settled at HEAD |
|---|---|---|---|
| **`scc`** | somatic cell count, the milk-quality figure a dairy is held to for saleability | **not mentioned at all** | **FOURTH IS RIGHT.** The input is labelled *"Somatic Cell Count (thousands, dairy only)"* at `sairnvet.html:6387`; written at `:6415-6416`; averaged `:6361-6362`; published as `avgSCC` at `:6370`. **My read listed the field and characterised only `vaccinationCompliance` as the regulated-adjacent one — I missed the stronger of the two.** |
| **consumers** | `renderHerdHealth`, `openHerdEdit`, `saveHerdEdit`, `removeHerd`, `addHerd`, the getter | *"renderHerdHealth, two further readers (`:6375`, `:6406`), the table, one CSV export"* | **MINE IS WRONG.** `:6375` and `:6406` are `openHerdEdit` and `saveHerdEdit` — a form renderer and a **WRITER**. An enumeration offered as the deciding test had mislabelled a writer as a reader. |
| **egress** | *"no report, no export and no regulator path"* | *"one CSV export button (`:1180`)"* | **BOTH, AND THEY ARE COMPATIBLE ONLY FOR A REASON THAT HAD TO BE CHECKED.** The export is real — `exportTableCSV('panel-herdhealth-table', ...)` at `sairnvet.html:1180` — and it **cannot reach either figure**, because the exported table's `<thead>` is `Herd \| Species \| Head Count \| Last Visit \| Status` (`:1185`) and neither `scc` nor `vaccinationCompliance` is a column. Fourth's sentence is too strong as written; the conclusion survives. |
| **rename blast radius** | does not exist here; the herd name is not editable and nothing outside references a herd | not addressed | **FOURTH IS RIGHT, verified:** `openHerdEdit` (`:6374-6398`) exposes five fields and the name is heading text only; `saveHerdEdit` (`:6405-6421`) writes only those five. |
| **line numbers** | `:6386` for the SCC input | — | **OFF BY ONE.** `:6386` is the vaccination-compliance input; SCC is `:6387`. Corrected in the landed cell. |

---

## 2. H1's `leg_guestbook` replacement cell — **APPLIES CLEANLY, AND IT IS LANDED**

**H1's quotation of the cell matched byte for byte at HEAD before the edit**, so the
replacement applied with no ambiguity. H1's proposal is not a tier change: *"repoint
the cell to state honestly what is on the row … and re-tier the confidentiality axis
from that accurate description rather than the current false 'no PII' claim"*, with
the trigger *"if a public-facing memorial page is ever built."*

**OLD LINE (`docs/CRITICALITY-TIERS.md:467`), verbatim:**

```
| `leg_guestbook` | **B** | **B** | Operational data lost or wrong | No elevated confidentiality class -- no PII, PHI, privileged communication, or financial-account detail on this row. Classified by the stated B rule rather than individually read | Operational data lost or wrong: neither money nor a regulated record. Classified by the stated B rule rather than individually read |
```

**NEW LINE — B/B, the false clause struck, the trigger named.** Landed in `c97acbf9`
and then corrected once more; read it at `docs/CRITICALITY-TIERS.md:467`. The three
load-bearing facts, each the code's own statement rather than an inference from field
names: the name is entered by **staff** (`sairnlegacy.html:3580-3582`, *"Guestbook
entries are logged by staff on the family's behalf until real public hosting
exists"*); **nothing is public** (*"Internal content record only -- deliberately no
public URL/hosting"*); **only staff read it** (`rGuestbook()` `:3630` renders into
`#gb-list`). **So H2's stated reason — intentionally public guestbook content — is
wrong about this app twice over.**

**THE CHECKER REFUSED MY FIRST TWO ATTEMPTS AT THIS CELL AND WAS RIGHT BOTH TIMES.**
`criticality_tier_check.py` raised `ASSERTS A GATE`: my cell said the row was
session-gated and named `api/sd-data.js:13299`. The register's own header forbids it
— *"This table states what the data IS. Whether a gate exists is a code fact it does
not assert"* — and my second attempt tripped the same arm by explaining the first.
The clause is gone, not softened.

**AND A CORRECTION TO MY OWN 2026-09-29 VERDICT:** it cited `#mm-guestbook` as the
render target. At HEAD it is `#gb-list` (`:3631`).

---

## 3. H1's open register findings — **THE COUNT IS 16, NOT 18, AND H1 SAYS SO**

**I could not derive 18 and did not manufacture it.** Three derivations:

| derivation | count |
|---|---|
| H1's own statement, log #732 item 6: *"the 16 open register findings at fresh HEAD"* — and it names them | **16** |
| resources named by a **structured-routable FINDING** in H1's log, excluding its own tooling (`hover2_log_mirror`, `tools_hover2_store_sync`) | **17** |
| the same, plus `sd_inventory` (named by a *check*, #685, and still carrying the never-read clause) | 18 |

**18 is reachable only by counting one check as a finding.** H1's own 16 is the
number to use, and the third column is how a reader gets to 18 if they were told it.

### The list, keyed by resource — apply-ready text, or the reason not

| # | resource | status now | apply-ready, or why not |
|---|---|---|---|
| 1 | **`mech_checks`** | **LANDED** `c97acbf9` | B → A on integrity. Item 4 below. |
| 2 | **`leg_guestbook`** | **LANDED** `c97acbf9` | Item 2 above. |
| 3 | **`sd_customers`** | **CANNOT APPLY YET** | H1 cites `stonedesk.html:25556`; `register_freshness_check` reports that cite DRIFTED — `custSave` is now at `:25599`. The finding needs its citation re-derived before a cell is written on it, and re-deriving somebody else's finding is not the same as applying it. |
| 4 | **`sd_business_snapshots`** | **CANNOT APPLY YET** | Same shape: H1 cites `:6864`, and the 2026-09-29 pass recorded a +43 drift on this row. The row also needs a money-limb judgement I have not made. |
| 5 | **`sf_honor_details`** | **CANNOT APPLY YET** | H1 cites `:5496` and a +1381 drift plus five missing fields (`ours`, `shared`, `issued`, `recovered`, `presented`). A 1381-line drift means the cite must be re-derived, not repointed. |
| 6 | **`sf_bottle_fills`** | **CANNOT APPLY YET** | H1's finding is that the cell cites `sfRecordBottleFill` where the real name is `sfBottleFill`. That is an identifier correction I have not verified at HEAD, and applying an unverified rename into the register is the defect this whole pass is about. |
| 7 | **`sf_documents`** | **CANNOT APPLY YET** | H1 cites `:5637` plus a +832 drift. Same reason as 5. |
| 8 | **`sb_emps`** | **CANNOT APPLY — NO ROW EXISTS** | Not in `api/_resources/sairnbiz.js`. Settled by the item-7 ruling: adding a row makes `criticality_tier_check.py` print `NOT A RESOURCE` and turns `run_criticality_tier_probe.py` RED on main. Cell text stands in this document from queue24. |
| 9 | **`sb_co`** | **CANNOT APPLY — NO ROW EXISTS** | Same. |
| 10 | **`sen_evv_queue`** | **CANNOT APPLY — NO ROW EXISTS, AND THE RULING SAYS WHY** | Item 7. H1's A/A risk assessment is correct and the venue is wrong. |
| 11 | **`law_strike_log`** | **CANNOT APPLY — NO ROW EXISTS** | Item 7. |
| 12 | **`sf_district_keypair`** | **CANNOT APPLY — NO ROW EXISTS** | Item 7. It is in `api/_resources/sairnfreedom.js`'s declared EXCLUSION block (`:85-86`), not its `resources` array. |
| 13 | **`sf_district_known_keys`** | **CANNOT APPLY — NO ROW EXISTS** | Item 7, and item 8: this is the real name. |
| 14 | **`sen_evv_config`** | **CANNOT APPLY — NO ROW EXISTS, AND NOTHING WRITES IT** | Item 7. A legacy key with a one-way migration read at `sairnsenior.html:5732` and no writer. |
| 15 | **`sd_owner_pin`** | **CANNOT APPLY — NO ROW EXISTS AND THE KEY IS DEAD** | Item 6. A row here would register a resource that does not exist. |
| 16 | **`supplier_lead_times`** | **CANNOT APPLY YET** | H1's #730 correction row settles a REPO fact (`sql/sd_supplier_lead_times_schema.sql` exists, landed `070fa0ad`) and explicitly leaves the LIVE fact open — an authenticated table-existence read COULD NOT RUN from that clone. The register note must not assert the half that could not be read. |

**Two landed of sixteen. Eight cannot be applied because the register's unit forbids
a row at all, five need a citation re-derived first, and one must not assert a live
fact nobody could read.** None is blocked by a claim.

---

## 4. `mech_checks` — proposal A over proposal B, on the evidence

**PROPOSAL A** (H1 #718(a) and #732 item 2): re-tier **A integrity / B
confidentiality**, plus a gate change adding `'mech_checks': ['write']` to
`SD_SESSION_GATED`.
**PROPOSAL B** (H1 #718(a), the fallback): leave the tier, rewrite the two false
clauses — *"At minimum the 'neither money nor a regulated record' and 'no PII'
clauses must be rewritten … whatever the tier lands."*

**PROPOSAL A. Three reasons, in order of weight.**

1. **The register's own precedent decides it.** `invoices` is A-integrity on the bare
   ground *"Money"*. A cheque register produced by the surface that writes the
   instrument is the same class with a sharper loss mode.
2. **H1 supplies a fact my method could not see, and it is what tips it.** The
   surrounding panel is a cheque-**WRITING** surface: `updateCheck()`
   (`sairnmechanical.html:1466`) renders a printable cheque with the amount in words
   (`numWords`, `:1477`) and a signature pad (`clearSig`, `:1465`). A write-shape
   extraction sees `{id, num, date, payee, amount, memo}` and cannot see what the
   panel around it does.
3. **Proposal B's own wording refuses it.** *"whatever the tier lands"* concedes that
   the tier is the open question and then declines to answer it. A register whose
   basis is corrected while its tier is left unexamined is the state this row was
   already in.

**H1's gate change is routed, not taken:** `SD_SESSION_GATED` lives in
`api/sd-data.js`, which is not in this claim.

### The final cell, as landed

Read it at `docs/CRITICALITY-TIERS.md:491`. Tier **A**, confidentiality **B**;
integrity basis names `saveCheck()` at `sairnmechanical.html:1527` and the
cheque-number half (`crNum` restored only on a LOCAL write failure at `:1537`, while
`mech_crnum` is a separate write that can fail on its own at `:1542`); the evidence
cell names both independent reads, the two places the platform already said this in
code, and the refusal of proposal B.

### The six rows on which "neither money nor a regulated record" has been false

1. **`sd_exec_msgs`** — found by an incident, not a read; the row sat at B on *"an
   internal message lost"* while the actual risk was who could READ it. This row is
   why the register has a second axis at all.
2. **`bld_change_orders`** — money under the sentence, found by reading the app.
3. **`bld_warranty`** — a `cost` column summed into a Total Cost KPI.
4. **`bld_inspections`** — municipal code determinations.
5. **`bld_toolbox_talks`** — OSHA instruction evidence.
6. **`mech_checks`** — `saveCheck()` persists `payee` and `amount`. 2026-09-30.

**3, 4 and 5 are one event:** all 15 `bld_` B rows carried the identical rule
sentence, nobody had opened any of them, and three were wrong — a 20% error rate on
one app's B tier, found by reading.

---

## 5. The review obligation for ted's `sen_visits`

**Reviewer named by ROLE, not by agent**, as required — and the role is the point of
the rule rather than a formality.

> **REVIEWER: any build session OTHER than the author of the change, holding no
> claim on `api/_resources/sairnsenior.js`, `sairnsenior.html` or
> `api/sd-data.js`'s `sen_` branches at the time of review.**
>
> Naming a role and not an agent is deliberate. The standing rule is that a Tier A
> change is reviewed by a session other than the one that wrote it, *because the
> author shares the blind spot that produced the code* — and an obligation addressed
> to `ted` survives only as long as that name maps to a session, while an obligation
> addressed to *a non-author build session* survives a rename, a clone being retired,
> and the 48-hour `--takeover` window. **The hover auditor is explicitly NOT eligible:**
> it does not build, its scope is `.claude/skills/sairn-hover-auditor/`, and using it
> as a reviewer of record would make the one independent role a participant in the
> thing it audits.
>
> **WHAT THE REVIEW MUST DRIVE, not read.** `sen_visits` is A/A on both axes and the
> integrity limb is payroll: it and `sen_pay_rates` are the two inputs and the output
> is what a caregiver is PAID — hours × rate with FLSA weighted-average overtime on
> top — so a wrong or lost visit is simultaneously a mispriced invoice and an
> underpaid person, and an underpayment carries liquidated damages regardless of
> intent.
>
> 1. **THE THIRD WRITE PATH, which is the one a reader misses.** `saveVisit()`
>    (`sairnsenior.html:3139`) is gated by `senCertGate()` BEFORE the record is built
>    (`:3137-3138`) so a refusal leaves nothing behind — drive that refusal and
>    confirm no partial row. The clock path syncs at `:3078`. **And the offline queue
>    flush at `:3047` replays `sen_evv_queue` into this resource FIFO, stopping at the
>    first failure** — so while a device is offline the durable record of a payable
>    visit is in an unregistered `localStorage` key and NOT in `sen_visits`. Drive an
>    offline clock-in and clock-out, then a flush, and confirm the clock-out cannot be
>    applied before the clock-in.
> 2. **The confidentiality limb is the EVV payload**, not the visit row alone:
>    `SEN_VISIT_EVV_FIELDS` carries `clock_in_lat`/`clock_in_lng`, which is a named
>    client's HOME by coordinate. Confirm a read without a verified session is 401
>    and that a caregiver cannot read another caregiver's visit.
> 3. **The one thing this obligation does NOT ask for**, so the reviewer does not
>    waste a pass on it: no judgement on whether `sen_evv_queue` should have a
>    register row. That is settled — it is not an `api/_resources` unit — and the
>    open question is its VENUE, which is Michael's and is recorded in the open-work
>    index.
>
> **A verdict of "reviewed, no findings" is refused unless it names which of the
> three it drove.** The gate already refuses a record whose reviewer is its own
> author; this sentence is the other half, and it is here because a discharge that
> names nothing is indistinguishable from one that read nothing.

---

## 6. `sd_owner_pin` — every remaining mention, `path:line`

Full-repo grep, `.git/` excluded. **Exactly one is code; the other eight are this
week's own paperwork about it.**

| path:line | what it is |
|---|---|
| **`stonedesk.html:42326`** | **THE ONLY CODE REFERENCE.** Inside `itaClearData()`'s keep-list: `var keep=['sd_owner_pin','sd_license_key','sd_plan',ITA_USERS_KEY,ITA_AUDIT_KEY];`. Nothing writes the key and nothing reads it. |
| `docs/2026-09-29-register-cells-hank.md:498` | my finding row |
| `docs/2026-09-29-register-cells-hank.md:504` | my finding, paragraph (1) |
| `docs/2026-09-29-register-cells-hank.md:506` | the keep-list quoted |
| `docs/2026-09-29-register-cells-hank.md:507` | *"is the fifth and has no writer and no reader"* |
| `docs/2026-09-29-register-cells-hank.md:514` | the deciding test |
| `docs/SAIRN-OPEN-WORK-INDEX.md:78` | the eight-resource unit-disagreement row |
| `docs/SAIRN-OPEN-WORK-INDEX.md:79` | the `sd_owner_pin` row |
| `.claude/claims/hover.json:412` | H1's nine-item queue text, naming the trigger statement |

**AND MY OWN CITATION OF IT HAD ALREADY DRIFTED.** The five references above say
`:42280`; the line is **`:42326`** at HEAD — 46 lines, inside 24 hours, on a finding
whose entire content is *"there is exactly one reference and here it is."* Corrected
in this document below. It is the cheapest possible demonstration of why a bare line
number in a standing document needs a re-derivation cadence.

---

## 7. Register scope — **IT TIERS RESOURCES, AND THE RULING IS MECHANICAL**

Not a judgement. `tools/criticality_tier_check.py` enforces a **bijection**, in both
directions, and its own refusal message states the rule verbatim:

> `NOT A RESOURCE  %s has a row and is not registered in any api/_resources/*.js.`
> **`The unit of this table is the registry.`**

and the other direction:

> `NO TIER      %s/%s is registered and has no row.`

Measured at HEAD, after this pass: `RESOURCES_REGISTERED:391`,
`RESOURCE_ROWS:391`, `PROBLEMS:0`. **One row per registered resource, none extra,
none missing.** The register's own header says the same in prose — *"The unit is
`api/_resources/<app>.js`"* — but the prose is not what settles it; the arm is.

### The two rows it settles

**`sen_evv_queue` — NO ROW. H1 is right about the risk and wrong about the venue.**
It is not in `api/_resources/sairnsenior.js`'s `resources` array; it is
`SEN_EVV_QUEUE_KEY` (`sairnsenior.html:3015`), a device-local FIFO capped at 200.
Adding a row makes the checker print `NOT A RESOURCE` and turns
`tests/run_criticality_tier_probe.py` RED on main — **the cost of the row is a red
probe, which is checkable rather than arguable.** H1's A/A reasoning stands on its
own terms: while offline this queue is the ONLY copy of wage-determining,
EVV-regulated clock events joined to a client's home location.

**`law_strike_log` — NO ROW.** Same test, same answer. `juryStrikeLog`/`juryStrikeSave`
at `sairnlaw.html:7156-7157`; not in `api/_resources/sairnlaw.js`'s `resources`
array, and not in its `notSynced` list either, which holds only `law_billingcodes`.

### What the ruling does NOT do, and this is the open half

**It settles the venue and it does not settle the risk.** Both keys hold something
worth a tier and the register cannot hold it. The existing venue with teeth is the
app's `notSynced` declaration plus `tools/local_only_collection_check.py` — which
records that a key is device-local **and carries no tier**. So the platform can say
*"this lives on one device"* and cannot say *"and losing it loses a wage-determining
record."*

**That gap is Michael's to close and there are only two honest ways:** extend the
register's unit to stored data — which changes the unit for all 391 rows and must be
said out loud in the header, because tiering the wrong unit is the mistake the
register already made once and corrected — or give `notSynced` a criticality field of
its own. Recorded in the open-work index; not decided here.

---

## 8. The item-2 correction confirmed — the eight, and the real name

**Re-verified at HEAD. None of the eight is in any `api/_resources/*.js` `resources`
array**, which under the item-7 ruling is what makes a register row possible:

| named | what it actually is |
|---|---|
| `scp_customers` | a localStorage key for the ALREADY-REGISTERED resource `customers` — `sairnscape.html:2734` maps `['customers','scp_customers']` |
| `scp_invoices` | same shape: `['invoices','scp_invoices']`; `invoices` has a row and is A/B |
| `sen_evv_config` | a legacy key **with no writer** — three references in `sairnsenior.html` and not one is a write |
| `sen_evv_queue` | a device-local FIFO outbox for `sen_visits`, cap 200 |
| `law_strike_log` | a device-local jury-strike log, `sairnlaw.html:7156-7157` |
| `sd_owner_pin` | **a dead key** — one reference repo-wide, in its own keep-list |
| `sf_district_keypair` | an extractable ECDSA P-256 **private** key JWK in `localStorage`; in SAIRNfreedom's declared EXCLUSION block, not its `resources` array |
| **`sf_district_known_keys`** *(reported as `sf_known_keys`, which does not exist)* | **THE REAL NAME, recorded RENAMED-REAL-2026-09-30** — `K_KNOWNKEYS` at `sairnfreedom.html:7163`, the trust-on-first-use fingerprint map; in SAIRNfreedom's declared EXCLUSION block, not its `resources` array |

> ### The real name is `sf_district_known_keys`
>
> `grep -rn sf_known_keys .` returns **nothing**. The key is
> **`sf_district_known_keys`**, bound as `K_KNOWNKEYS` at `sairnfreedom.html:7163`
> and read by `getKnownKeys()` at `:7481`. It is the **trust-on-first-use fingerprint
> map** for other districts' signing keys, and
> `api/_resources/sairnfreedom.js:88-91` states why it is device-local: *"syncing it
> would let one device's first-seen decision silently become another device's trust
> anchor."*
>
> **Its integrity is the sharper axis and it is the opposite way round from its
> sibling.** `sf_district_keypair` is a confidentiality problem — a stolen private key
> forges signed district reports. `sf_district_known_keys` is an **integrity** problem:
> edit one fingerprint and a forged district report **verifies silently on this
> device**. That is trust-anchor tampering, and a lost key regenerates while a
> tampered anchor does not announce itself.

---

## 9. The four idempotence timeouts — last line reached, and the write target

**Measured, not parsed.** Each tool was run in a throwaway copy of the tracked tree
with output streamed to a file, because `subprocess.run(timeout=)` raises
`TimeoutExpired` and takes the partial stdout with it — which is exactly why the
sweep itself cannot answer this question about its own could-not-tells.

| tool | last line reached at the 240s bound | tracked files it had written |
|---|---|---|
| **`dead_rule_sweep.py`** | `criteria lock: 6/6 fixtures classify correctly, on hand-built sources only` — **2 output lines in 240 seconds** | **20**, and they are tool sources: `accepted_risk_expiry_audit.py`, `ai_action_approval_audit.py`, `assertion_label_shape_check.py`, `cleanup_confirm_check.py`, `committer_identity_check.py`, `completeness_check.py`, `dependency_graph.py`, `discarded_verdict_check.py` + 12 more |
| **`guard_ablation.py`** | `? EMPLOYEE_PROFILE_MANAGE_ROLES :1757 SILENT 152 suites, none noticed` | **0** |
| **`metamorphic_check.py`** | `blind lock: LOCKED (10 fixture comparisons)` | **0** |
| **`run_all_tests.py`** | `ok node api/sd-data-alf-isolation.test.js` — 237 output lines | **0** |

### What the measurement settles, and it is the answer the rejected regex was reaching for

**THREE OF THE FOUR WRITE NOTHING TRACKED.** `guard_ablation.py` works inside a
worktree it builds itself; `metamorphic_check.py` writes only under a
`tempfile.mkdtemp()` root; `run_all_tests.py` writes a lock under
`tempfile.gettempdir()` and a report only to an explicit `--out`. **They have no
tracked-tree idempotence question at all**, so the sweep double-running them will
always say "no change", slowly, forever.

**On 2026-09-29 I built a regex that tried to derive exactly this and REJECTED it**
because it excluded `guard_ablation` by looking only at `jsonout` and never seeing
its `io.open(os.path.join(wt, SUBJECT), 'w')` — the verdict was right and was reached
by not looking. **Running the tools answers the same question by observation**, and
it agrees with the verdict the regex reached unsoundly. That is the difference
between a correct answer and a justified one.

**AND THE FOURTH IS THE OPPOSITE, WHICH THE REGEX ALSO MISSED.**
`dead_rule_sweep.py` had written **20 tracked tool sources** in 240 seconds — it
neutralises a rule in a tool, runs the corpus against it, and restores in a
`finally`. So it is the only one of the four with a real tracked-tree idempotence
question, and its own `finally` plus a post-restore byte comparison is the control
that answers it.

**A RISK WORTH NAMING, and it is not a defect in the sweep:** killed mid-loop,
`dead_rule_sweep.py` leaves 20 tool sources in the NEUTRALISED state. Inside the
sweep's scratch copy that is harmless and self-cleaning. Run directly in a real
clone and interrupted, it is 20 patched tools with nothing marking them — the same
shape already recorded about `guard_ablation --ablate` editing the platform's largest
dispatcher in place. It produced 2 output lines in 4 minutes, so an operator has no
signal that it is mid-loop rather than hung.

---

## 10. `citation_class_check.py` against my three corrected buckets — **THE COMPARISON CANNOT BE MADE, AND THAT IS THE FINDING**

**The tool does not measure register buckets.** It lives at
`.claude/skills/sairn-hover-auditor/tools/citation_class_check.py` — the auditor's
scope, read-only from here, nothing written into it — and it classifies
**`path:line` citations inside the hover audit log's own entries** against
`~/Documents/SAIRN-hover`, into five classes:

`WRONG-AT-DERIVATION` · `MOVED-SINCE` · `NOT-A-REPO-PATH` · `UNVERIFIABLE-NO-SHA` · `HOLDS`

My three corrected buckets are about `docs/CRITICALITY-TIERS.md`:

`cited` · `disclosed` · `3.2 group stamp` · `dated-or-field-list read` · `contradictory`

**Different subject, different corpus, non-overlapping class vocabulary. There is no
bucket in one that corresponds to a bucket in the other**, so "where do the tool and
my hand count disagree" has no answer to give. Reporting a disagreement figure would
have required inventing a mapping.

### Two real findings from running it anyway

**(1) IT CANNOT BE RUN FROM A BUILD CLONE AT ALL, AND IT FAILS OPEN IN THE WORST
SHAPE.** `LOG = os.path.join(HERE, 'hover-audit-log.jsonl')` resolves beside the
tool, and the mirrored copy in a build clone has no log next to it. The run:

```
  7 ok, 0 failed
Traceback (most recent call last):
  ...
FileNotFoundError: ... .claude\skills\sairn-hover-auditor\tools\hover-audit-log.jsonl
```

**The fixture gate prints `7 ok, 0 failed` and THEN crashes.** A reader who stops at
the pass line sees a clean tool. It is a stale-path defect of exactly the class
H1's own queue names — *"a stale-path methodology sweep across all relocated tooling
with selftests run from two working directories"* — and it is in the tool that sweep
would be run with. **There is no `--log` argument**, so the corpus run is impossible
from here without editing the tool, which is out of scope. Routed, not fixed.

**(2) ITS OWN FULL-LOG FIGURES, from H1's log #732 item 9:** `HOLDS 567 |
MOVED-SINCE 114 | WRONG-AT-DERIVATION 54 | NOT-A-REPO-PATH 42 | NO-SHA 261`. Driven
from a scratch copy with the log path overridden — the auditor's directory untouched
— **the WRONG-AT-DERIVATION list reproduces**, 20 entry groups including seqs 638,
640, 643, 654, 658, 672, 685, 690, 702, 718, 730, 732, 733. H1's own header says the
54 are a worklist and not 54 confessions, and spot-reads show known tool-noise shapes
in the residue; that reading is confirmed rather than challenged here.

### What I could compare, and did

The register buckets moved as a result of this pass, measured before and after:

| bucket | before `c97acbf9` | after |
|---|---|---|
| cite at least one line | 184 | **191** |
| CITE NOTHING | 207 | **200** |
| … admit they were not read individually | 65 | **58** |
| … 3.2 group stamp | 106 | 106 |
| … dated or field-list read | 31 | 31 |
| … **CLAIM a read with none of the above** | **0** | **0** |
| neither stated | 5 | 5 |

**Seven rows moved from "never individually read" into "cited", which is exactly the
seven cells landed, and the contradiction bucket stayed at zero.** No hand count
disagrees with the tool, because the tool's counts ARE the hand count here: the
seven were read individually and the report re-derived the buckets afterwards.

---

## 11. The check — **BUILT, AND IT MUST NOT BLOCK. The answer is a measurement.**

`tools/tier_sentence_gate.py` + `tests/run_tier_sentence_gate_probe.py`, report-only.

> **If a row asserts the money clause, and the resource's own write persists a field
> whose NAME is in a small closed money list, report the row and the field.**

### It catches the real historical defect, and goes quiet once fixed

Driven over `docs/CRITICALITY-TIERS.md` **as it stood before `c97acbf9`** — not over
a fixture — it reports **exactly one row, `mech_checks`, naming `amount` and
`payee`**. Driven over HEAD it reports **nothing**, and `mech_checks` is still SEEN
and classified `QUOTED`, because the corrected cell quotes the clause to say it was
false. That pair is the probe's central arm. **19 arms, 0 failures.**

### FEASIBLE AS A PRE-COMMIT GATE? **NO — and the number is printed on every run**

| | |
|---|---|
| rows asserting the money clause | **76** |
| of those, with an extractable write shape | **35 of 50** (**70%**) |
| threshold at which blocking becomes arguable | **95%** |
| verdict | **NOT MET** |

Both ways of handling the other 30% are wrong for a gate:

* **FAIL OPEN** on an unresolved resource — report a pass it never performed. PR §1.11
  verbatim, inside the gate meant to enforce the register.
* **FAIL CLOSED** — refuse the ordinary edit to a file five sessions touch. A gate
  that blocks the ordinary case gets switched off, and then protects nothing.

So the third state is printed per resource — 15 `COULD-NOT-TELL`, named — and the
check stays report-only. **The honest venue for it is a PostToolUse report on an edit
to the register, the shape `citation_drift_hook.py` already is and the shape that
works.**

### What it deliberately cannot do, each for a measured reason

* **It does not screen the REGULATED limb.** `sv_herdhealth.scc` is somatic cell
  count and no field name would know; `sv_staff.credential` holds `'Current'`, a
  currency flag, so a `credential` pattern fires on a row where B is correct.
* **It does not screen the "no PII" clause.** Two of the three rows found false on
  2026-09-29 failed on PII, and a `name`/`phone`/`email` screen fires on most
  business-contact rows where B is right on the CLASS.
* **So it would have caught ONE of the three rows found that day, and the one this
  week.** Stated in the tool's own header rather than left for a reader to work out.

### Two defects in it, both caught by its own controls on the first run

1. **The push-helper pattern was case-sensitive.** The real call is
   `window.mechPushRecord('mech_checks', entry)` with a **capital P**, and a lowercase
   `push(?:Record|One)` matched nothing — so the one row the check was built for came
   back `COULD-NOT-TELL`. **An extractor that silently resolves nothing reports
   "nobody could tell" rather than "the regex has a capital letter wrong."** Caught by
   the arm asserting `mech_checks` must be `MONEY-FIELD`, and a paired arm now
   requires a name written nowhere to still resolve to nothing, so the widening did
   not make every lookup succeed.
2. **My first probe arm was wrong, not the tool.** It expected `mech_checks` to vanish
   from the asserting population once corrected. It does not — the corrected cell
   quotes the clause — and asserting `QUOTED` is the stronger claim, because it proves
   the quotation exclusion works on the real corrected row rather than on a fixture.
