-- sql/sairnroofing_supplier_documents_schema.sql
--
-- SAIRNroofing B6 -- supplier purchase orders, receipts and invoices, and the
-- three-way match between them. Run once in the Supabase SQL editor.
--
-- ── WHY THIS, AND WHAT IT IS NOT ────────────────────────────────────────────
-- docs/2026-09-02-competitive-gap-status-rederived.md records B6 -- "Supplier
-- EDI (PO / ASN / invoice)" -- as the ONLY genuinely open SAIRNroofing item.
-- Re-verified before building rather than taken from the doc: `supplier` and
-- `vendor` each appear ZERO times in sairnroofing.html, and the single
-- `receiving` hit is inside a patent-claim comment.
--
-- THIS IS NOT EDI TRANSPORT. An X12 850/856/810 exchange needs a
-- trading-partner agreement with ABC Supply, Beacon or SRS, an AS2 or VAN
-- connection, and a certification cycle per partner. None of that is
-- engineering this app can do alone, and a screen labelled "EDI" without it
-- would be a claim with nothing behind it.
--
-- What IS buildable, and is where the money is, is the THREE-WAY MATCH those
-- documents exist to enable: what was ordered, what arrived, what was billed,
-- and where the three disagree. That reconciliation is identical whether the
-- documents arrive over EDI, as a PDF, or typed off a paper packing slip. If a
-- trading partner is ever signed, it fills these same rows.
--
-- ── ONE TABLE, THREE DOCUMENT TYPES, KEYED BY PO NUMBER ─────────────────────
-- Modelled the way EDI models it: three documents referencing one purchase
-- order. Separate tables would have forced a join for every match and made
-- "which PO does this receipt belong to" a foreign key that can dangle. Here
-- the PO number IS the key, exactly as it is on the paperwork.
--
-- `lines` is jsonb because a supplier's line shape is the supplier's, not
-- ours, and normalising it into columns would mean discarding whatever does
-- not fit -- on a document that is evidence in a billing dispute.
--
-- ── APPEND-ONLY, AND HERE THAT IS NOT A STYLE CHOICE ────────────────────────
-- These documents are what a contractor argues from when an invoice is wrong.
-- A receipt edited after the fact is worth nothing in that argument. So: plain
-- INSERT, unique (license_hash, document_id), NO UPDATE grant and NO DELETE
-- grant. A corrected invoice is a NEW document; the superseded one stays and
-- the match shows both.
--
-- That is the same reasoning as mech_credentials and the opposite of
-- mech_site_assets -- and the difference is whether the row is evidence or a
-- description. These are evidence.
--
-- ── QUANTITIES ARE NULLABLE INSIDE THE JSONB, ON PURPOSE ────────────────────
-- api/_lib/roofing-supplier-match.js treats a missing quantity as UNKNOWN and
-- never as zero, because "nobody wrote down what arrived" and "nothing
-- arrived" are different facts and only one is the supplier's problem.
-- Defaulting a quantity to 0 anywhere in this pipeline would turn every
-- unscanned delivery into a short shipment and send a contractor to argue
-- about a truck that did arrive.
--
-- ── NO SEED DATA ────────────────────────────────────────────────────────────
-- Not one row, and no seeded supplier names or part numbers anywhere in the
-- engine either -- there is a test asserting that.
--
-- ── SECURITY ────────────────────────────────────────────────────────────────
-- service_role only, RLS on with no anon policy, api/sd-data.js the only door.
-- Read is management or broad-read (api/rf-auth.js BROAD_READ_ROLES) -- an
-- estimator needs to see what material costs. WRITE IS MANAGEMENT ONLY: these
-- rows decide whether an invoice gets paid, and that is not a field-level
-- permission.

create table if not exists public.rf_supplier_documents (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  document_id   text not null,          -- client-generated, stable, unique per licence
  doc_type      text not null,          -- order | receipt | invoice
  po_number     text not null,          -- the key all three share
  supplier      text,
  supplier_ref  text,                   -- the supplier's own invoice / packing-slip number
  job_id        text,                   -- optional link to the job it was bought for
  doc_date      date,
  lines         jsonb not null default '[]'::jsonb,
  notes         text,
  recorded_by   text,                   -- employee_id from the verified session
  created_at    timestamptz not null default now(),
  unique (license_hash, document_id)
);

create index if not exists idx_rf_supdoc_license
  on public.rf_supplier_documents (license_hash, created_at desc);
-- The match question is always "everything under THIS purchase order".
create index if not exists idx_rf_supdoc_po
  on public.rf_supplier_documents (license_hash, po_number, doc_type);

alter table public.rf_supplier_documents enable row level security;

-- SELECT and INSERT only. No UPDATE: a receipt edited after the fact is worth
-- nothing in a billing dispute. No DELETE: it is evidence.
grant select, insert on public.rf_supplier_documents to service_role;

-- ── VERIFY ──────────────────────────────────────────────────────────────────
-- Expect the columns below and ZERO rows.
select column_name, data_type, is_nullable
  from information_schema.columns
 where table_schema = 'public' and table_name = 'rf_supplier_documents'
 order by ordinal_position;

select count(*) as should_be_zero from public.rf_supplier_documents;

-- The grant must be select+insert only. An UPDATE here would quietly make a
-- packing slip editable after the invoice arrived:
select privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public' and table_name = 'rf_supplier_documents'
   and grantee = 'service_role'
 order by privilege_type;
-- Expect exactly: INSERT, SELECT
