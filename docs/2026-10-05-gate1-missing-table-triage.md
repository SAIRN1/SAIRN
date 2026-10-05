# Gate 1 — the 24 missing tables triaged, and the sweep that produced them was reading 113 files of 147

**2026-10-05 (Cody).** The instruction was to resolve as many of the 24 as
possible without Michael and escalate only what genuinely needs him.

**NONE OF THE 24 CAN BE REMOVED. The honest answer is that the list got LONGER,
to 26, because my own sweep was not reading the whole of `sql/`.**

---

## 1. THE TRIAGE — 0 of 24 removable

Four questions per missing table, answered from the repo with no live calls:

| question | why it could have shortened the list | answer |
|---|---|---|
| **REGISTERED** in `api/_resources/<app>.js`? | an unregistered table cannot be reached by the app either, so an unrun migration for it blocks nothing today | **24 of 24 ARE registered** |
| **ASKED FOR** in the app's own source? | a table nothing asks for is a migration with no consumer | **24 of 24 are named in both the app HTML and `api/`** |
| **DECLARED IN** more than one `sql/` file? | a second declaration means another file may already have created it under a different name | **24 of 24 are declared exactly ONCE** |
| **PREFLIGHT** clean? | a file that half-applies is worse than one not run | **18 of 18 files report 0 findings** |

**So every one of the 24 is a registered resource the app really uses, created by
exactly one file, and that file is sound.** There is no naming artefact, no
superseded duplicate, and nothing that can be resolved from inside the
repository. `tools/schema_provisioning_check.py` exits 2 on each file only
because no `--live` snapshot was passed, which is the tool refusing to call a
repo-only comparison a pass — not a failure of the file.

### TWO FLAGS I RAISED AND THEN CLEARED AGAINST LIVE STATE

A grant/RLS audit over the 18 files flagged `mech_credentials_schema.sql` and
`sairnroofing_supplier_documents_schema.sql` as **NO POLICY** — RLS enabled with
no `create policy` statement.

**Both are fine and I checked rather than reported.** 91 tables across `sql/`
use that exact pattern and **81 of them are confirmed live and readable today**,
so `service_role` bypasses RLS as designed and the absence of a policy denies
`anon`/`authenticated` outright. The pattern is at least as strict as the
`create policy "svc only X"` form used elsewhere, and both flagged tables are
append-only (`grant select, insert` only — no update, no delete).

**Had I shipped those two flags, Michael would have been sent to hand-edit two
correct files.** Every other grant line on the 18 is `service_role` only; no
`delete`, no `truncate`, no `all`, and no non-`service_role` grantee anywhere.

---

## 2. THE LIST IS 26, NOT 24 — MY SWEEP'S GLOB MISSED 34 SCHEMA FILES

**Found by following one register cell.** `supplier_lead_times`'s tier cell
asserts the table is not provisioned; I went to confirm it against today's live
reading and it was **not in my missing list at all**. It was not in my sweep
either.

The Gate-1 sweep globbed `sql/<app-prefix>*schema*.sql`. Measured:

```
sql/*schema*.sql on disk        147
reached by the prefix glob      113
MISSED                           34   -- 21 of which declare tables, 28 tables
```

**A schema file whose name does not begin with its app's name was invisible.**
`sd_supplier_lead_times_schema.sql`, `sd_crm_schema.sql`, `sd_slabs_schema.sql`,
`sd_slab_lineage_schema.sql`, `sd_hr_schema.sql`, `sd_approvals_schema.sql`,
`sd_progress_photos_schema.sql` and fourteen more.

**So the 402 declared and 24 missing I published were both FLOORS**, and the
document that published them said nothing about it because I did not know.

### THE 28 TABLES, SWEPT SIGNED-IN ON `SD-AUDIT-2026`

```
declared     28
provisioned   6   sd_crm, sd_hr_certs, sd_hr_employees,
                  sd_blocks, sd_bundles, sd_slab_history
MISSING       2   sd_approvals, sd_supplier_lead_times
unreachable  20
```

**The 20 unreachable are NOT a finding and asking stonedesk for them was the
wrong question.** They are platform-shared or other-app tables — `employees`,
`ai_memories`, `ledger_entries`, `ledger_lines`, `business_profiles`,
`biometric_consent`, `biometric_template`, `accounting_connections`,
`accounting_consents`, `sairncash_trial`, `sairncash_waitlist`,
`subcontractors`, `sub_assignments`, `sd_slabs`, `sd_employee_profiles`,
`sd_progress_photos`, `sd_webauthn_credentials`,
`sairn_ai_rate_limit_log`, `sairn_circuit_breaker`, `sairn_style_profiles` —
reached through a different registry or a bespoke endpoint, not through
`stonedesk`'s. **Stated rather than counted as 20 new gaps.**

### THE CORRECTED GATE-1 FIGURES

| | published 2026-10-05 | corrected |
|---|---|---|
| schema files swept | 113 | **134** |
| declared tables | 402 | **430** |
| PROVISIONED | 289 | **295** |
| **MISSING** | **24** | **26** |
| SQL files for Michael | 18 | **20** |

### THE TWO ADDITIONAL SQL ACTIONS — MICHAEL

| run this file | creates |
|---|---|
| `sql/sd_approvals_schema.sql` | `sd_approvals` |
| `sql/sd_supplier_lead_times_schema.sql` | `sd_supplier_lead_times` |

Same procedure as the other eighteen: paste whole, then confirm.

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('sd_approvals', 'sd_supplier_lead_times')
order by table_name;
```

**Two rows is the pass.**

---

## 3. ONE MORE MICHAEL ACTION, AND IT IS NOT A TABLE

**`db/schema_snapshot.json` is 22 DAYS STALE and 51 tables that exist live are
absent from it.** Its own `_generated_at` is `2026-09-13 18:39:55 UTC`; it holds
380 tables; today's signed-in reading confirms 295 present, of which **51 are
not in the capture**.

That matters because `tools/gate_column_check.py` answers *"does this column
exist"* from this file, and **a column missing from a stale capture is
indistinguishable from a column that does not exist.**

**THE ERROR IS ONE-DIRECTIONAL AND THAT IS THE ONE PIECE OF GOOD NEWS: zero
tables the snapshot claims exist are actually missing.** It under-reports and
never over-reports, so nothing has been cleared on its word that should not have
been — but 51 tables are being answered about by a file that has never seen
them.

> **MICHAEL:** run `sql/schema_snapshot_query.sql` whole in the Supabase SQL
> editor, copy the **single JSON value** out of the one result cell, save it over
> `db/schema_snapshot.json`, and **commit it.** Steps 3 and 4 are the ones that
> went missing last time: the query was run on 2026-09-10 and the committed file
> was still the 2026-09-02 capture.

**DO THIS AFTER the 20 schema files**, so the capture includes them and the
re-capture does not immediately need repeating.

---

## 4. THE TWO REGISTER NOTES — WRITTEN, NOT APPLIED

**Item 9 of the earlier queue, re-stated and now measured. `docs/CRITICALITY-TIERS.md`
is held by cc under a live claim (`2026-10-05T11:12:09Z`) and
`sairn_claim.py check` refuses on the declared-FILES collision**, so these are
replacement cell text rather than an edit. Both cells already carry a 2026-09-29
auditor note; what follows is the 2026-10-05 measurement to append to each.

### `supplier_lead_times` — the 09-29 note is CONFIRMED, and now names its file

Driven today, signed in on `SD-AUDIT-2026` at `/api/sd-auth`:
`read supplier_lead_times` → **200, `provisioned: false`, 0 rows.**

Append to the evidence cell:

> **RE-DRIVEN 2026-10-05, SIGNED IN, AND THE 09-29 NOTE HOLDS:** `read
> supplier_lead_times` on `SD-AUDIT-2026` answers 200 with `provisioned: false`,
> so the table still does not exist. **AND THE FILE THAT WOULD CREATE IT IS NOW
> NAMED: `sql/sd_supplier_lead_times_schema.sql`** — one table,
> `sd_supplier_lead_times`, reached through the bare resource name
> `supplier_lead_times`. It is NOT declared in `stonedesk_data_schema.sql`, which
> is why the 2026-09-29 provisioning run could name it missing while the
> 2026-10-05 app-prefix sweep never asked about it at all. Added to Michael's
> queue in `docs/2026-10-05-gate1-missing-table-triage.md`. The row stays **B/B**
> and this is still not a tier claim.

### `sd_inventory` — the opposite answer, and worth recording for that reason

`read sd_inventory` → **200, `provisioned: true`, 0 rows.**

Append to the evidence cell:

> **RE-DRIVEN 2026-10-05, SIGNED IN:** `sd_inventory` answers 200
> `provisioned: true` with **0 rows** on `SD-AUDIT-2026`. The table exists and is
> empty, which is the opposite state from `supplier_lead_times` above and is why
> both were re-driven together: *"no rows"* and *"no table"* are the same screen
> to a user and different facts to this register. The `cost` x `qty` stock-value
> note stands — it is about the computation, which is live in `stonedesk.html`
> regardless of how many rows exist today. Still **B/B**.

---

## 5. WHAT CANNOT BE RESOLVED WITHOUT MICHAEL, AND WHY

**Creating a table is DDL and nothing on this platform can issue it.**
`api/sd-data.js` has no DDL path — by design — so there is no loader, no tool
and no endpoint through which a clone can create any of the 26. Every
alternative was checked and ruled out in section 1.

Beyond the 20 SQL files and the snapshot re-capture, **two apps still need a
decision rather than a paste**:

- **SAIRNvet** — 42 resources unanswerable. `SV-PINNACLE-2026`'s PIN is dead and
  `bootstrap` is permanently closed on that licence by design. Needs a
  credential minted through `setup` by somebody who already holds a session, or
  a new demo licence. **Not a SQL file.**
- **SAIRNfreedom** — 17 resources unanswerable, including a felony flag on a
  named volunteer and minors' names. **CORRECTED SAME DAY: this is NOT a SQL
  file and the sentence that said so was a false escalation.** I wrote *"`sql/sairnfreedom_employee_auth_schema.sql`
  has never been run, so `/api/sf-auth` answers 503"* — **quoted from open-work
  row 156 and never driven.** Driven: `/api/sf-auth` answers **401
  INVALID_CREDENTIALS** on a login and a **role-shaped 403** on `roster`, and
  `api/sf-auth.js` returns 503 `NOT_PROVISIONED` at `:478`/`:508` and 503
  `NOT_GRANTED` at `:512` for exactly those two conditions — so the request got
  past both and **the table exists with privileges.** What blocks the 17 is a
  **credential**: no SAIRNfreedom row exists in
  `docs/2026-09-03-demo-credentials.md`, and `bootstrap` would WRITE one to a
  customer-shaped licence, which is Michael's call and not a reviewer's.
  **Same shape as SAIRNvet above: a decision, not a paste.** Row 156 carries the
  same stale sentence and is cc's to correct.

  **EVERY OTHER FIGURE IN THIS DOCUMENT WAS MEASURED AND THIS ONE WAS QUOTED**,
  which is the whole lesson: a standing row is a claim with a date on it, and
  asking the endpoint costs one request.

---

## WHAT THIS DOES NOT ESTABLISH

- **That 295 provisioned tables are correct.** Existence is not shape, and every
  request here was a read.
- **That the 26 are all of them.** 134 of 147 schema files are now swept; the
  remaining 13 declare no tables, which was checked, but the figure is a floor
  until something sweeps `sql/` without a filename assumption. **That is the
  defect this document found in its own predecessor and it would be dishonest to
  claim the second pass cannot have one too.**
