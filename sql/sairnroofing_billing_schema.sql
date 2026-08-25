-- sql/sairnroofing_billing_schema.sql
-- SAIRNroofing Phase 4b -- estimate -> proposal -> invoice.
--
--   rf_proposals        -- APPEND-ONLY. Each row is an event (issued /
--                          accepted / declined / withdrawn), and an ISSUED row
--                          carries its own copy of the priced lines.
--   rf_invoices         -- MUTABLE header. Payments live in a jsonb array that
--                          the SERVER appends to, one entry per call.
--   rf_invoice_counters -- the gapless sequence, one row per (license,
--                          location), plus the atomic allocator below.
--
-- ── WHY rf_proposals IS APPEND-ONLY AND SNAPSHOTS THE PRICE ──────────────
-- If a proposal referenced rf_jobs.data.estimate instead of copying it,
-- editing the estimate after sending would retroactively change what the
-- customer was told they were quoted, with nothing anywhere recording that it
-- happened. sql/sairnroofing_claims_schema.sql already makes this argument
-- about tear-off photos -- "evidence that can be edited after the fact is not
-- evidence" -- and a price put in front of a customer is the same kind of
-- fact. Re-pricing produces a NEW issued row, which is also what really
-- happened.
--
-- ── WHY PAYMENTS ARE A jsonb ARRAY AND NOT A THIRD TABLE ─────────────────
-- An invoice has a handful of payments and they are always read with the
-- invoice. The server does the appending (the client sends ONE entry, never
-- the whole array), so it is genuinely append-only in practice -- the same
-- shape as rf_jobs' measurement_correction, and for the same reason. A join
-- table would be right the moment somebody needs "every payment received in
-- March across all invoices"; that query does not exist yet, and building for
-- it now would be speculative structure. Recorded so the tradeoff is a
-- decision rather than drift.
--
-- A correction is a NEGATIVE entry naming the payment_id it reverses. Both
-- rows survive; nothing is edited.
--
-- ── THE BALANCE IS NOT A COLUMN, ON PURPOSE ──────────────────────────────
-- There is no balance, amount_paid or amount_due column anywhere below.
-- api/_lib/roofing-billing.js recomputes them on every read from the stored
-- lines and the stored payments. A stored balance is a number that was true
-- once. Same discipline as roofing-claims.js's money_summary and the 3c
-- supplement worksheet.
--
-- ── INVOICE NUMBERS ARE GAPLESS, AND THAT NEEDED A REAL MECHANISM ────────
-- Every other id in this app is a client-generated timestamp (RFJOB-<ts>).
-- That is fine for an internal record and NOT fine for an invoice number:
-- accounting and audit expect a gapless sequence, and a timestamp cannot
-- provide one. Michael's decision 2026-08-25: a server-side sequence per
-- (license, location), reusing the pg_advisory_xact_lock pattern already
-- proven in sql/sairnlaw_trust_disbursement_atomic_check.sql rather than
-- inventing a second concurrency mechanism.
--
-- ── FIELD NAMES ARE THE STANDARD EXPORT ONES ─────────────────────────────
-- bill_to / issue_date / due_date / terms / line_items[description, quantity,
-- unit_price, amount] / subtotal / tax / total. Accounting-system integration
-- is OUT OF SCOPE for 4b and recorded as a closed decision -- but naming these
-- the SAIRN way now would buy a relabelling job later for nothing.
--
-- ── GRANTS ───────────────────────────────────────────────────────────────
-- REVOKE ALL first, then grant only what the code calls. rf_proposals is
-- append-only: SELECT, INSERT, no UPDATE. rf_invoices and rf_invoice_counters
-- are mutable: SELECT, INSERT, UPDATE. NOTHING gets DELETE -- a wrong invoice
-- is voided, which a bookkeeper needs to see, not removed.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

-- ---------------------------------------------------------------------------
-- 1. Proposals -- append-only.
-- ---------------------------------------------------------------------------
create table if not exists public.rf_proposals (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnroofing',
  proposal_id  text not null,                      -- client-generated (RFPRO-<ts>)
  job_id       text not null,                      -- references rf_jobs.job_id
  event_type   text not null,                      -- issued | accepted | declined | withdrawn
  -- On a decision row, the proposal_id of the ISSUED row it responds to. The
  -- engine will not apply a decision that does not name its target, so an old
  -- decline cannot stick to a later re-quote.
  supersedes   text,
  recorded_by  text not null,                      -- server-stamped from the session
  data         jsonb not null default '{}'::jsonb, -- issued: line_items, tax_rate, tax, issued_on,
                                                     --         valid_until, terms, notes
                                                     -- decision: decided_on, acceptance_method,
                                                     --         accepted_by, signature_data, reason
  created_at   timestamptz not null default now(),
  unique (license_hash, proposal_id),
  constraint rfpro_event_check check (event_type in ('issued','accepted','declined','withdrawn')),
  constraint rfpro_supersedes_check check (event_type = 'issued' or supersedes is not null),
  -- 1.5MB, matching rf_claim_agreements: an acceptance signature is optional
  -- but when captured it is an image, not app data.
  constraint rfpro_data_size check (octet_length(data::text) <= 1572864)
);

create index if not exists idx_rfpro_license_job on public.rf_proposals(license_hash, job_id);

-- ---------------------------------------------------------------------------
-- 2. Invoices.
-- ---------------------------------------------------------------------------
create table if not exists public.rf_invoices (
  id             uuid primary key default gen_random_uuid(),
  license_hash   text not null,
  app_id         text not null default 'sairnroofing',
  invoice_id     text not null,                    -- client-generated internal id
  -- The customer-facing, gapless number. NULL while the invoice is a draft --
  -- a number is allocated when it is issued, so an abandoned draft does not
  -- burn one and leave a gap.
  invoice_number text,
  invoice_seq    integer,
  job_id         text not null,
  location_id    text not null default 'LOC-DEFAULT',
  claim_id       text,                             -- optional link, see the reconcile verb
  status         text not null default 'draft',
  issue_date     date,
  due_date       date,
  data           jsonb not null default '{}'::jsonb,  -- bill_to, terms, line_items, tax_rate, tax, notes
  payments       jsonb not null default '[]'::jsonb,  -- server-appended, one entry per call
  created_by     text not null,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (license_hash, invoice_id),
  -- The number is unique per license once allocated. Partial index so the many
  -- NULLs on drafts do not collide with each other.
  constraint rfinv_status_check check (status in ('draft','issued','paid','void')),
  constraint rfinv_issued_needs_number check (status = 'draft' or invoice_number is not null),
  constraint rfinv_issued_needs_date check (status = 'draft' or issue_date is not null),
  constraint rfinv_payments_is_array check (jsonb_typeof(payments) = 'array'),
  constraint rfinv_data_size check (octet_length(data::text) <= 262144),
  constraint rfinv_payments_size check (octet_length(payments::text) <= 65536)
);

create unique index if not exists idx_rfinv_number
  on public.rf_invoices(license_hash, invoice_number)
  where invoice_number is not null;
create index if not exists idx_rfinv_license_job on public.rf_invoices(license_hash, job_id);
create index if not exists idx_rfinv_claim on public.rf_invoices(license_hash, claim_id);

-- ---------------------------------------------------------------------------
-- 3. The counter + the atomic allocator.
-- ---------------------------------------------------------------------------
create table if not exists public.rf_invoice_counters (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  location_id  text not null default 'LOC-DEFAULT',
  prefix       text not null default 'INV',
  next_seq     integer not null default 1,
  updated_at   timestamptz not null default now(),
  unique (license_hash, location_id),
  constraint rfinvc_seq_positive check (next_seq >= 1)
);

-- SECURITY INVOKER (the default) -- runs as whichever role PostgREST
-- authenticates the caller as (service_role, via api/sd-data.js's service-role
-- key), so it passes the same RLS policies a direct insert would.
--
-- pg_advisory_xact_lock is keyed on (license_hash, location_id), so two
-- branches of the same shop never block each other and two licenses never do.
-- PostgREST wraps each RPC call in one transaction, so the lock, the read, the
-- increment and the return are genuinely atomic: a second concurrent call for
-- the same counter blocks until the first commits, then reads the new value.
-- Directly modelled on law_check_and_insert_disbursement.
create or replace function public.rf_allocate_invoice_number(
  p_license_hash text,
  p_location_id  text
) returns table (invoice_number text, invoice_seq integer, prefix text)
language plpgsql
as $$
declare
  v_prefix text;
  v_seq    integer;
begin
  perform pg_advisory_xact_lock(hashtext(p_license_hash), hashtext(coalesce(p_location_id, 'LOC-DEFAULT')));

  insert into public.rf_invoice_counters (license_hash, location_id)
  values (p_license_hash, coalesce(p_location_id, 'LOC-DEFAULT'))
  on conflict (license_hash, location_id) do nothing;

  update public.rf_invoice_counters
     set next_seq = next_seq + 1, updated_at = now()
   where license_hash = p_license_hash
     and location_id = coalesce(p_location_id, 'LOC-DEFAULT')
  returning next_seq - 1, rf_invoice_counters.prefix into v_seq, v_prefix;

  return query select (v_prefix || '-' || lpad(v_seq::text, 5, '0'))::text, v_seq, v_prefix;
end;
$$;

-- ---------------------------------------------------------------------------
-- 4. RLS + grants.
-- ---------------------------------------------------------------------------
alter table public.rf_proposals enable row level security;
alter table public.rf_invoices enable row level security;
alter table public.rf_invoice_counters enable row level security;

drop policy if exists "svc only rf_proposals" on public.rf_proposals;
create policy "svc only rf_proposals" on public.rf_proposals
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists "svc only rf_invoices" on public.rf_invoices;
create policy "svc only rf_invoices" on public.rf_invoices
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists "svc only rf_invoice_counters" on public.rf_invoice_counters;
create policy "svc only rf_invoice_counters" on public.rf_invoice_counters
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

revoke all on public.rf_proposals from service_role;
grant select, insert on public.rf_proposals to service_role;
revoke all on public.rf_invoices from service_role;
grant select, insert, update on public.rf_invoices to service_role;
revoke all on public.rf_invoice_counters from service_role;
grant select, insert, update on public.rf_invoice_counters to service_role;
revoke all on public.rf_proposals, public.rf_invoices, public.rf_invoice_counters
  from anon, authenticated;

grant execute on function public.rf_allocate_invoice_number(text, text) to service_role;

-- Verify after running:
--   select count(*) from rf_proposals;         -- expect 0
--   select count(*) from rf_invoices;          -- expect 0
--   select count(*) from rf_invoice_counters;  -- expect 0
--
-- Grants (expect rf_proposals = INSERT,SELECT ; the other two =
-- INSERT,SELECT,UPDATE ; no DELETE and no TRUNCATE on any of the three):
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name in ('rf_proposals','rf_invoices','rf_invoice_counters')
--    group by table_name;
--
-- The allocator is gapless and starts at 1 (expect INV-00001 then INV-00002,
-- and a counters row with next_seq = 3 afterwards):
--   select * from public.rf_allocate_invoice_number('testhash', 'LOC-DEFAULT');
--   select * from public.rf_allocate_invoice_number('testhash', 'LOC-DEFAULT');
--   select * from public.rf_invoice_counters where license_hash = 'testhash';
-- Then clean the probe up:
--   delete from public.rf_invoice_counters where license_hash = 'testhash';
--
-- The issued-invoice constraints bite (each expects an ERROR, not a row):
--   insert into public.rf_invoices (license_hash, invoice_id, job_id, status, created_by)
--   values ('t','I','J','issued','x');            -- rfinv_issued_needs_number
