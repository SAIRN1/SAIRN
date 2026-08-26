# SAIRNroofing — Phase 4c + the rfDataRaw read bug (CC, 2026-08-25)

Phase 4 Operations is **complete** (4a, 4d, 4b, 4c). The larger finding of the
session is not 4c: it is that five phases' worth of UI had been passing live
verification while rendering nothing, because every check was aimed at the
endpoint and none at the page.

Commits, in order: `0df5699`, `ee2411f`, `4d86518`, `7d7708e`.

---

## 1. The bug that mattered — `rfDataRaw` returned `d.data`

`rfDataRaw` set `data:(d&&d.data)`. Its sibling `rfAuth` sets `data:d`, and
**every one of its consumers was written against rfAuth's convention** — they
read `r.data.<field>`. A read body is `{ok,provisioned,data:[...],...}`, so
`r.data` was the rows array and `r.data.data` was `undefined` on every call.

Latent from Phase 2 (`31e0337`), where the only callers were writes touching
`r.ok`/`r.msg`. **Live from Phase 3b onward**, the first read caller. Thirteen
consumers across Phases 3b/4a/4b/5 silently rendered empty or null:

schedule list · locations list · invoice list · proposal state · agreement
chain · agreement status (×2) · programmes board · its `roster_size` footer ·
claim ACV-mismatch note · both invoice-issue toasts

**Why months of green never surfaced it.** Every one of those phases passed
live API verification. `curl` exercised the endpoint; nothing exercised this
line. An empty panel reads as "no data yet" — the silent-failure shape, not a
fabrication. Guardian's own *Known Scope Limitation: Auth-Gated Content*
section already warns that a clean code-level pass on a PIN-gated app means
"the code looks right assuming the gate opens", not "the app works". That
warning was correct and had not been acted on for this app.

**The fix was not one line, and assuming it was would have caused a
regression.** Audited per call site against each branch's real response body:

```
OLD data:(d&&d.data)  ->  0/13 consumers correct
NEW data:d            -> 13/13 consumers correct
regressed by the fix  -> none
```

The claim ACV-mismatch note (`rfSaveClaim`) was the **one** consumer correct
under the old convention, because a **write reply nests its record under
`data`** (`api/sd-data.js:2994`) while reads and compute actions put their
payload at the top level. Fixing only the helper would have silently broken the
one thing that worked. Both lines moved together in `ee2411f`.

**Browser-verified after the fix**, as `rf-verify-ui` (owner) against records
created through the app's own write endpoints — schedule day, branch (also
feeding the job's Branch dropdown), proposal `awaiting decision` with a $9,750
total, draft invoice, agreement chain, and a real computed agreement status.
Issue toast now reads `Issued as INV-00001` rather than `Issued as undefined`.

---

## 2. Phase 4c — Reports + CSV export

Five reports: Jobs, Claims, Schedule, Certifications, Invoices.

**The gate is inherited, not re-asserted.** Each report calls the ordinary
gated read for its resource — same action, same session token the matching
panel already uses — and serialises what comes back. Those rows were already
filtered server-side against the session's own `employee_id`, so a CSV cannot
contain a record the caller could not open on screen. Structural, not a rule
the file has to remember. **Zero new lines in `api/sd-data.js`.**

A server-side `action:'export'` branch per resource was the alternative and was
rejected deliberately (Michael's call): it puts a second read path beside the
first, with the gate living in two places that must agree forever. This
codebase has paid for that twice — `api/rf-auth.js`'s header records
SAIRNsenior's gate drifting because role names sat in two files, and the
open-work index still carries the duplicated signature-pad row.

**Proposals deferred with a reason, not forgotten.** `rf_proposals` is the one
read that is per-job, so a cross-job report needs client fan-out or a new
server branch — exactly the shape this design avoids.

**Honest empty states**, because of §1. Three outcomes are distinguished and
**none writes a file**: `provisioned:false` (table not set up), zero visible
rows (says so, and says no file was written rather than an empty one that would
look like a completed export), and a 403 reported as the refusal it is.

**Formula injection neutralised.** A roofing CSV goes to a bookkeeper, so
Excel/Sheets is the normal destination. Cells starting `=` `+` `@` tab or CR
get an apostrophe prefix; a real negative number is exempt — `-1200.50` is a
genuine figure on an overpaid invoice.

### The 4c defect the browser caught

The Jobs export wrote a **blank identifier on all 8 rows**. The column was
mapped to `job_id`, but **`rf_jobs`' read renames it** (`api/sd-data.js:2495`
maps `id: r.job_id`) — the only one of the five that renames; claims, schedule,
certifications and invoices all keep their `<thing>_id`. The panel reported
*"Exported 8 jobs — 7 columns"* and the file had 8 populated rows. Only the
cells were wrong. **Same shape as §1: a green result standing in for a correct
one.** Fixed in `7d7708e`.

Then audited **all 62 columns** rather than just the one caught. Nine more
resolved empty; all traced to absent test data and **proved so by seeding the
values**, not by reasoning — a claim with every money field, a second invoice
with terms + claim link, and three certifications covering the record types
that actually carry `jurisdiction` (`local_license`) and `has_expiry` (a card
declaring it has none). Final: **62/62 resolve, zero wrong paths.**

### Gate proven against a narrow role

`rf-verify-fmA` (foreman, Phase 4a fixture, PIN in
`sql/sairnroofing_verify_foremen_seed.sql`):

| Report | Owner | Foreman |
|---|---|---|
| Jobs | 8 | **1** (own assignment only) |
| Claims | 1 | **0** |
| Schedule | 1 | **0** |
| Certifications | 3 | **0** |
| Invoices | 2 | **403 FORBIDDEN** |

Rows visible to the foreman but not the owner: **0**. In the browser the scope
note flips to *"only the records assigned to you"*, the Invoices button is
**absent from the DOM entirely** (`rpt-btn-invoices` does not exist), the Jobs
CSV contains exactly their one job, and Certifications exercised the
empty-state path with **no file written**, confirmed on disk.

---

## 3. A false alarm I raised and corrected — read this before trusting a counter claim

I reported an invoice-counter regression. **There was none.** Issuing produced
`INV-00001` where I expected `INV-00003`, and I jumped to "the counter reset"
without reading the key it is on.

`rf_invoice_counters` is keyed **`(license_hash, location_id)`** — one row per
licence *per branch* (`sql/sairnroofing_billing_schema.sql:9`, `unique` at
:146), and the allocator takes the invoice's own branch
(`api/sd-data.js:3337`). The verify job was on a new branch `LOC-UIVERIFY`, so
it drew from a fresh counter starting at 1. Confirmed directly: `LOC-DEFAULT`
at `next_seq = 3` exactly where 4b left it, `LOC-UIVERIFY` at `2`.
`LOC-DEFAULT/INV-00001` and `LOC-UIVERIFY/INV-00001` are different invoices in
independent sequences, by design.

Also worth knowing: **`rf_invoice_counters` has no read path.** `api/sd-data.js`
touches it only through `rpc/rf_allocate_invoice_number`, which increments — so
through the API the only way to observe it is to burn a number. Reading it
requires a direct SQL query.

---

## 4. State on disk

- **Test data cleaned up.** `sql/_scratch_rf_uiverify_cleanup.sql` (gitignored)
  was written and run. `rf-verify-ui` deactivated, never deleted. The
  `LOC-UIVERIFY` counter row was **deliberately left** — deleting it restarts
  that branch at a number already issued, the one direction a gapless sequence
  cannot be repaired in.
- `rf-verify-fmA` / `fmB` left **active** on purpose — Phase 4a fixtures that
  predate this session.
- **No roofing table grants DELETE to `service_role`** — all fourteen grant
  lines are select/insert(/update). Cleanup scripts must run as the SQL editor
  (postgres). The app genuinely cannot delete any of it.
- `.gitignore` now carries `sql/_scratch_*` (`0df5699`); those files had sat
  untracked for several sessions, one `git add -A` from being committed with
  real `license_hash` values in them.

## 5. Open items

1. **Tax provenance (open-work row 141) is now visible in exports.** Both
   invoices export `tax_basis_derived: amount` despite having neither a tax
   rate nor a tax amount. Pre-existing, not introduced by 4c — but the CSV
   gives it a wider audience than the panel did.
2. **Cross-job Proposals report** — deferred from 4c with the reason above.
3. **Duplicated signature pad** (`rfSigInit` / `rfPropSigInit`) — still open,
   still drifting.
4. **The methodology point, which outlives all three.** Every real defect this
   session was found by *opening the artefact* — the rendered panel, the
   downloaded file — never by the operation reporting success. Two separate
   bugs had a green success message sitting directly on top of them. Before any
   future phase is called verified, something has to look at what a user
   actually sees.
