# SAIRNdesign Invoice-per-Proposal Uniqueness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the real cross-device duplicate-invoice race
(`SAIRN-BACKLOG.md`) by adding a real DB-level uniqueness constraint on
`(license_hash, proposal_id)` for `sdn_invoices` and mapping its
violation to a clean rejection, per
`docs/superpowers/specs/2026-08-10-sairndesign-invoice-uniqueness-design.md`.

**Requires a schema migration Michael must run manually in Supabase's
SQL editor** — I have no DB execution access from this environment (no
`SUPABASE_URL`/service key, no `psql`, no `supabase` CLI locally,
confirmed this session). The application code (Task 1, Task 2) is safe
to ship *before* the migration runs — Postgres won't return a 23505
conflict on `proposal_id` until the index exists, so nothing regresses
in the meantime. Constraint enforcement itself can only be verified
*after* the migration is applied.

## Global Constraints

- No change to `sdnData()` or its other ~20 call sites in this file —
  `saveInvoice()` makes its own direct fetch for this one write. (Spec
  §5)
- `setInvoiceStatus()` (updates an existing `invoice_id` in place) must
  keep working exactly as today — the new constraint must never fire on
  it. (Spec §2)
- `node --check api/sd-data.js` must pass after every change.
- `python tools/checkblocks.py sairndesign.html` /
  `div_balance_check.py` must stay clean after every change.

---

### Task 1: SQL migration (write only — Michael runs it)

**Files:** Create `sql/sairndesign_invoice_uniqueness.sql`

- [ ] **Step 1: Write the migration**

```sql
-- sql/sairndesign_invoice_uniqueness.sql
-- Closes SAIRN-BACKLOG.md's "SAIRNdesign invoicing needs a real
-- server-side uniqueness constraint" entry (logged 2026-08-09).
-- saveInvoice()'s existing client-side "already invoiced" check has
-- zero race window on one device but cannot close a cross-device race.
-- This index makes a second concurrent insert for the same proposal
-- fail atomically at the DB layer (23505 unique_violation), which
-- api/sd-data.js's sdn_invoices write branch maps to a clean 409
-- DUPLICATE_INVOICE response.
--
-- Coexists with the table's existing (license_hash, invoice_id) upsert
-- key: setInvoiceStatus() updates an EXISTING invoice_id in place
-- (proposal_id unchanged), which never re-triggers this constraint --
-- only a genuinely NEW invoice_id for an already-invoiced proposal_id
-- does.
--
-- Run this in Supabase's SQL editor. Verify after running:
--   select indexname from pg_indexes where tablename='sdn_invoices';
-- should include sdninv_license_proposal_unique.
CREATE UNIQUE INDEX IF NOT EXISTS sdninv_license_proposal_unique
  ON public.sdn_invoices (license_hash, (data->>'proposal_id'));
```

- [ ] **Step 2: Flag to the user**

This migration is not run as part of this plan's execution — surface it
explicitly at the end of this session's work so it doesn't get lost as
a silent TODO.

---

### Task 2: `api/sd-data.js` — map the 23505 conflict to a clean 409

**Files:** Modify `api/sd-data.js:1606-1622`
(`if (SDN_RESOURCES[resource] && action === 'write')`)

- [ ] **Step 1: Write the implementation**

Insert a check for the 409 case right after the existing
`404`/`400` NOT_PROVISIONED check:

```js
      const r = await fetch(rest(resource + '?on_conflict=license_hash,' + idCol), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairndesign', [idCol]: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdesign data tables are not set up yet — run sql/sairndesign_data_schema.sql in Supabase first.' } }); return; }
      // Invoice-per-proposal uniqueness (2026-08-10): once
      // sql/sairndesign_invoice_uniqueness.sql's index exists, a genuinely
      // new invoice for an already-invoiced proposal_id fails here with
      // Postgres 23505 (PostgREST maps it to 409) -- map it to a clean,
      // real rejection instead of the generic upstream() 502. Scoped to
      // sdn_invoices only: no other SDN_RESOURCES table has this
      // constraint, so this branch can never misfire for them.
      if (r.status === 409 && resource === 'sdn_invoices') {
        res.status(409).json({ error: { code: 'DUPLICATE_INVOICE', message: 'This proposal already has an invoice.' } });
        return;
      }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
```

- [ ] **Step 2: Syntax-check**

Run: `node --check api/sd-data.js`
Expected: no output, exit 0.

- [ ] **Step 3: Pre-migration regression check (live)**

Before the migration runs, confirm this branch is genuinely inert and
nothing regresses:

```bash
curl -s -w '\nHTTP:%{http_code}\n' -X POST https://sairn.vercel.app/api/sd-data \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer SDN-PINNACLE-2026' \
  -d '{"action":"write","resource":"sdn_invoices","payload":{"id":"INV-TEST-1","invoice_number":"INV-TEST","proposal_id":"PR-TEST","project_id":"PJ-TEST","client_id":"CL-TEST","amount":100,"status":"Draft"}}'

curl -s -w '\nHTTP:%{http_code}\n' -X POST https://sairn.vercel.app/api/sd-data \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer SDN-PINNACLE-2026' \
  -d '{"action":"write","resource":"sdn_invoices","payload":{"id":"INV-TEST-2","invoice_number":"INV-TEST-2","proposal_id":"PR-TEST","project_id":"PJ-TEST","client_id":"CL-TEST","amount":50,"status":"Draft"}}'
```

Expected (pre-migration): **both** succeed 200 — confirms the branch
doesn't false-positive before the index exists (nothing to violate yet).

- [ ] **Step 4: Post-migration verification (after Michael runs Task 1)**

Re-run the same two calls against fresh `id`s. Expected: first 200,
second 409 with `error.code === "DUPLICATE_INVOICE"`. Read back via
`{"action":"read","resource":"sdn_invoices"}` and confirm only the first
invoice's row exists for that `proposal_id`.

- [ ] **Step 5: Commit**

```
git add api/sd-data.js
git commit -m "fix: api/sd-data.js -- map sdn_invoices proposal_id conflict to 409 DUPLICATE_INVOICE

..."
```

---

### Task 3: `sairndesign.html` — honest rejection message

**Files:** Modify `sairndesign.html:2279-2292` (`saveInvoice()`)

- [ ] **Step 1: Write the implementation**

```js
async function saveInvoice(){
  var pid=$('invproposal').value;
  var p=proposals().find(function(x){return x.id===pid;});
  if(!p){toast('Select an approved proposal first');return;}
  var alreadyInvoiced=invoices().some(function(i){return i.proposal_id===pid;});
  if(alreadyInvoiced){toast('This proposal already has an invoice');return;}
  var rec={id:newId('INV'),invoice_number:'INV-'+Date.now().toString().slice(-6),proposal_id:pid,
    project_id:p.project_id,client_id:p.client_id,amount:proposalTotal(p),cost_basis:proposalCostTotal(p),
    due_date:$('invdue').value,status:'Draft',issued_date:sdnLocalToday(),paid_date:'',created_at:sdnLocalToday()};
  var list=invoices();list.push(rec);st('sdn_invoices',list);
  closeInvoiceModal();rInvoicing();
  var lic=sdnLicenseKey();
  if(!lic){toast('Saved on this device only -- server sync failed, try again with a connection',6000);return;}
  try{
    var r=await fetch(DATA_API,{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+lic},
      body:JSON.stringify({action:'write',resource:'sdn_invoices',app_id:APP_ID,payload:rec})});
    var d=await r.json().catch(function(){return null;});
    if(r.status===409&&d&&d.error&&d.error.code==='DUPLICATE_INVOICE'){
      // Server rejected it -- a duplicate genuinely landed first (or was
      // already there from before this session started). Roll the local
      // optimistic insert back and tell staff the truth.
      list=invoices().filter(function(i){return i.id!==rec.id;});
      st('sdn_invoices',list);rInvoicing();
      toast(d.error.message,6000);
      return;
    }
    toast((r.ok&&d&&d.ok)?'Invoice created':'Saved on this device only -- server sync failed, try again with a connection',(r.ok&&d&&d.ok)?3000:6000);
  }catch(e){
    toast('Saved on this device only -- server sync failed, try again with a connection',6000);
  }
}
```

- [ ] **Step 2: Syntax-check**

```
python tools/checkblocks.py sairndesign.html
python tools/div_balance_check.py sairndesign.html
```
Expected: 0 failed blocks, `RESULT:PASS`.

- [ ] **Step 3: Live interaction test**

Pre-migration: create an invoice for a real approved proposal, confirm
success. Post-migration (once Task 1 runs): attempt a second invoice
for the same proposal from a second session, confirm the honest
rejection and that the invoice list still shows only the first one.

- [ ] **Step 4: Commit**

```
git add sairndesign.html
git commit -m "fix: SAIRNdesign -- saveInvoice() surfaces the real 409 rejection

..."
```

---

### Task 4: Push, live-verify what's verifiable now, close the loop

- [ ] **Step 1:** Full local re-check (`checkblocks.py`,
  `div_balance_check.py` on `sairndesign.html`; `node --check` on
  `api/sd-data.js`).
- [ ] **Step 2:** Push all commits + the new SQL file (the file itself
  is safe to commit even though the migration hasn't run).
- [ ] **Step 3:** Re-run Task 2 Step 3's pre-migration regression check
  against the live endpoint — confirm still both-succeed (migration not
  yet run).
- [ ] **Step 4:** Report to the user that
  `sql/sairndesign_invoice_uniqueness.sql` needs to be run in Supabase
  before this fix is actually load-bearing, and that Task 2 Step 4 /
  Task 3 Step 3's post-migration checks are the way to confirm it once
  it has been.
- [ ] **Step 5:** Update `SAIRN-BACKLOG.md` — mark this entry
  "code-complete, pending DB migration" rather than fully resolved
  until the migration is confirmed run, and correct the "same
  scope-class as SAIRNlaw/SAIRNbuild" language (this one needed a single
  index, not a from-scratch resource+schema build).
