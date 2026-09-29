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
