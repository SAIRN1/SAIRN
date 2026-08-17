-- sql/sairnlaw_trust_disbursement_atomic_check.sql
-- SAIRNlaw trust disbursement server-sync, step 2: promotes amount/type/
-- status to real columns on law_trusttx and adds the atomic check-and-write
-- function. See docs/superpowers/specs/2026-08-16-sairnlaw-trust-disbursement-atomic-check-design.md.
-- Safe to re-run -- every statement is idempotent, and the backfill only
-- touches rows where the new columns are still null.

alter table public.law_trusttx add column if not exists amount numeric;
alter table public.law_trusttx add column if not exists type text;
alter table public.law_trusttx add column if not exists status text;

-- Backfill any rows written before this migration (step 1's own
-- live-verification rows, e.g. TR-VERIFY-1, only carried these fields
-- inside the jsonb data blob):
update public.law_trusttx set amount = (data->>'amount')::numeric
  where amount is null and data->>'amount' is not null;
update public.law_trusttx set type = data->>'type'
  where type is null and data->>'type' is not null;
update public.law_trusttx set status = coalesce(data->>'status','Posted')
  where status is null;

-- Constraints added only after backfill, so existing rows already satisfy
-- them. drop-then-add makes re-running this file safe even if a prior
-- partial run already added one of these.
alter table public.law_trusttx drop constraint if exists lawtrusttx_type_check;
alter table public.law_trusttx add constraint lawtrusttx_type_check
  check (type in ('Deposit','Disbursement'));
alter table public.law_trusttx drop constraint if exists lawtrusttx_status_check;
alter table public.law_trusttx add constraint lawtrusttx_status_check
  check (status in ('Posted','Voided'));
alter table public.law_trusttx drop constraint if exists lawtrusttx_amount_positive;
alter table public.law_trusttx add constraint lawtrusttx_amount_positive
  check (amount is null or amount > 0);

create index if not exists idx_lawtrusttx_client_status
  on public.law_trusttx(license_hash, client_id, status);

-- The atomic check-and-write. SECURITY INVOKER (the default) -- runs as
-- whichever role PostgREST authenticates the caller as (service_role, via
-- api/sd-data.js's service-role key), so it passes the same RLS policies
-- (`svc only law_trusttx`) a direct service_role insert already would.
-- pg_advisory_xact_lock is keyed on (license_hash, client_id) -- serializes
-- concurrent disbursement attempts for the SAME client only; different
-- clients' calls never block each other. PostgREST wraps each RPC call in
-- one transaction, so the lock + balance read + insert are genuinely
-- atomic: a second concurrent call for the same client blocks until the
-- first commits, then re-checks against the now-current balance.
create or replace function public.law_check_and_insert_disbursement(
  p_license_hash text, p_trusttx_id text, p_matter_id text, p_client_id text,
  p_amount numeric, p_method text, p_reference_number text,
  p_description text, p_tx_date text, p_created_at text
) returns public.law_trusttx
language plpgsql
as $$
declare
  v_balance numeric;
  v_row public.law_trusttx;
begin
  perform pg_advisory_xact_lock(hashtext(p_license_hash || ':' || p_client_id));
  -- Retry-idempotency: a genuine retry of an already-committed disbursement
  -- (e.g. client response lost to a network blip) must return the existing
  -- row, not re-run the balance check -- the balance sum below would already
  -- include this disbursement, wrongly rejecting an already-valid,
  -- already-committed transaction. Closes a real retry-rejection bug found
  -- in final review (2026-08-17).
  select * into v_row
    from public.law_trusttx
    where license_hash = p_license_hash and trusttx_id = p_trusttx_id;
  if found then
    return v_row;
  end if;
  select coalesce(sum(case when type = 'Deposit' then amount else -amount end), 0)
    into v_balance
    from public.law_trusttx
    where license_hash = p_license_hash and client_id = p_client_id
      and status = 'Posted';
  if p_amount is null or p_amount <= 0 then
    raise exception 'INVALID_AMOUNT: disbursement amount must be a positive number'
      using errcode = 'P0001';
  end if;
  if p_amount > v_balance then
    raise exception 'INSUFFICIENT_TRUST_BALANCE: disbursement % exceeds balance %', p_amount, v_balance
      using errcode = 'P0001';
  end if;
  insert into public.law_trusttx (license_hash, app_id, trusttx_id, matter_id, client_id,
    amount, type, status, data, created_at, updated_at)
  values (p_license_hash, 'sairnlaw', p_trusttx_id, p_matter_id, p_client_id,
    p_amount, 'Disbursement', 'Posted',
    jsonb_build_object('id', p_trusttx_id, 'matter_id', p_matter_id, 'client_id', p_client_id,
      'type', 'Disbursement', 'amount', p_amount, 'method', p_method,
      'reference_number', p_reference_number, 'description', p_description,
      'date', p_tx_date, 'status', 'Posted', 'created_at', p_created_at),
    now(), now())
  on conflict (license_hash, trusttx_id) do nothing
  returning * into v_row;
  return v_row;
end;
$$;

revoke all on function public.law_check_and_insert_disbursement from public;
grant execute on function public.law_check_and_insert_disbursement to service_role;
