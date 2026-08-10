# SAIRNdesign — Invoice-per-Proposal Uniqueness

**Status:** Design approved 2026-08-10. Not yet implemented.

Closes `SAIRN-BACKLOG.md`'s "SAIRNdesign invoicing needs a real
server-side uniqueness constraint" entry (logged 2026-08-09).

## 1. Current state (verified against live code)

`saveInvoice()` (`sairndesign.html:2279`) checks
`invoices().some(i => i.proposal_id === pid)` against the **local**
snapshot, then writes through the generic `sdn_invoices` route
(`api/sd-data.js:1606-1622`) — upsert keyed on `(license_hash,
invoice_id)`. Each invoice gets its own `newId('INV')`, so two
concurrent creates for the same proposal never collide on that key —
both inserts succeed, producing two invoices for one approved proposal.
`proposal_id` lives only inside the `data` jsonb blob
(`sql/sairndesign_data_schema.sql:190-200`) — it is not a promoted
column and has no constraint of its own today.

## 2. Design decision

**This one genuinely needs a schema change** — unlike #1, there is no
way to express "reject if this proposal already has a row" atomically
without something in Postgres to enforce it. A `UNIQUE INDEX` on the
expression `(license_hash, (data->>'proposal_id'))` is the minimal form
— no new column, no table rewrite, just an index that also acts as a
constraint. Coexists cleanly with the existing `(license_hash,
invoice_id)` upsert key: `setInvoiceStatus()` updates an *existing*
`invoice_id` in place (`proposal_id` unchanged), so it never
re-triggers this constraint — only a genuinely new `invoice_id` for an
already-invoiced `proposal_id` does.

**Manual step required, out of my control:** I have no Supabase/DB
execution access from this environment (no `SUPABASE_URL`/service key,
no `psql`, no `supabase` CLI) — same as every other schema change this
session (`sql/sairnlegacy_data_schema.sql` etc. were always written for
Michael to run in Supabase's SQL editor, never executed by me directly).
The server-side 409-mapping code below is written and safe to ship
ahead of the migration (it's simply unreachable — Postgres won't return
a 23505 conflict on `proposal_id` until the index exists — so no
regression either way), but the actual race isn't closed until
`sql/sairndesign_invoice_uniqueness.sql` is run against the live DB.
Live-verify for this fix is split accordingly: everything except real
constraint enforcement can be verified now; constraint enforcement
needs to be re-verified after the migration runs.

## 3. Migration (`sql/sairndesign_invoice_uniqueness.sql`)

```sql
CREATE UNIQUE INDEX IF NOT EXISTS sdninv_license_proposal_unique
  ON public.sdn_invoices (license_hash, (data->>'proposal_id'));
```

## 4. Server change (`api/sd-data.js`)

Inside the existing `if (SDN_RESOURCES[resource] && action === 'write')`
block (`api/sd-data.js:1606`): if the POST returns 409 (PostgREST's
mapping of Postgres's 23505 unique_violation) and `resource ===
'sdn_invoices'`, return a clean `{error:{code:'DUPLICATE_INVOICE',
message:'This proposal already has an invoice.'}}` instead of falling
into the generic `upstream()` 502 "Data store error — try again" (which
is both the wrong status code and actively misleading for a correctly-
rejected write).

## 5. Client change (`sairndesign.html`)

Same reasoning as SAIRNlegacy's fix (#1, §4): `sdnData()`
(`sairndesign.html:961`) collapses every non-2xx response to `null` and
has its own ~20 other call sites in this file (a separate copy from
SAIRNlegacy's — no shared module between the two apps) — not touching
it. `saveInvoice()` (`sairndesign.html:2279-2292`) makes its own direct
`fetch(DATA_API, ...)` call for this one write so it can read the real
response body/status. On a `DUPLICATE_INVOICE` 409, show that real
reason and refresh the invoice list, instead of the generic "Saved on
this device only — server sync failed, try again with a connection"
fallback (wrong message for this failure — it wasn't a connectivity
problem, it was a correct rejection). On any other failure, keep
today's fallback message.

## 6. Testing

- Pure logic: confirm the migration's index blocks a second insert with
  the same `(license_hash, proposal_id)` via direct `curl` against
  `api/sd-data.js` (two sequential writes, second must 409) — **only
  possible after the migration runs**.
- Before the migration: confirm no regression — normal invoice
  create/update flow works exactly as today.
- Live interaction (post-migration): create an invoice for a proposal
  through the UI, confirm success; attempt a second invoice for the
  same proposal, confirm the honest rejection message.
