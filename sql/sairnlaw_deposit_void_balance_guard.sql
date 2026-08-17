-- sql/sairnlaw_deposit_void_balance_guard.sql
-- SAIRNlaw trust disbursement server-sync, step 3a: closes the deposit-void
-- balance gap disclosed in SAIRN-BACKLOG.md ("SAIRNlaw void-of-deposit can
-- retroactively negative a client's balance"). Extracts law_client_balance()
-- as a shared helper (used by both this and step 2's disbursement function)
-- and adds law_check_and_void_deposit(), the atomic guard for voiding a
-- Deposit. See docs/superpowers/specs/2026-08-17-sairnlaw-deposit-void-balance-guard-design.md.
-- Safe to re-run -- create-or-replace throughout.

create or replace function public.law_client_balance(p_license_hash text, p_client_id text)
returns numeric
language sql
stable
as $$
  select coalesce(sum(case when type = 'Deposit' then amount else -amount end), 0)
    from public.law_trusttx
    where license_hash = p_license_hash and client_id = p_client_id
      and status = 'Posted';
$$;

revoke all on function public.law_client_balance from public;
grant execute on function public.law_client_balance to service_role;

-- law_check_and_insert_disbursement() now calls the shared helper instead
-- of its own inline balance query -- same live behavior, single source of
-- truth. Every other line (advisory lock, retry-idempotency check,
-- INVALID_AMOUNT guard, insert, unified return point) is unchanged from
-- sql/sairnlaw_trust_disbursement_atomic_check.sql.
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
  v_existing public.law_trusttx;
  v_existing_found boolean;
begin
  perform pg_advisory_xact_lock(hashtext(p_license_hash || ':' || p_client_id));
  select * into v_existing
    from public.law_trusttx
    where license_hash = p_license_hash and trusttx_id = p_trusttx_id;
  v_existing_found := found;
  if v_existing_found then
    v_row := v_existing;
  else
    v_balance := public.law_client_balance(p_license_hash, p_client_id);
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
  end if;
  return v_row;
end;
$$;

revoke all on function public.law_check_and_insert_disbursement from public;
grant execute on function public.law_check_and_insert_disbursement to service_role;

-- New: the atomic deposit-void guard. Unlike law_check_and_insert_disbursement,
-- client_id isn't known until the row is looked up, so this does the lookup
-- TWICE: once before the lock (to learn client_id for the lock key), and
-- once again immediately after acquiring it, since another transaction could
-- have changed this row's status/amount while this call waited for the lock
-- -- the ALREADY_VOIDED and balance checks below must see post-lock state.
create or replace function public.law_check_and_void_deposit(
  p_license_hash text, p_trusttx_id text, p_voided_reason text
) returns public.law_trusttx
language plpgsql
as $$
declare
  v_row public.law_trusttx;
  v_balance_without numeric;
  v_voided_at timestamptz;
begin
  select * into v_row
    from public.law_trusttx
    where license_hash = p_license_hash and trusttx_id = p_trusttx_id;
  if not found then
    raise exception 'NOT_FOUND: no trust transaction % for this license', p_trusttx_id
      using errcode = 'P0001';
  end if;
  perform pg_advisory_xact_lock(hashtext(p_license_hash || ':' || v_row.client_id));
  select * into v_row
    from public.law_trusttx
    where license_hash = p_license_hash and trusttx_id = p_trusttx_id;
  if v_row.status <> 'Posted' then
    raise exception 'ALREADY_VOIDED: trust transaction % is not in Posted status', p_trusttx_id
      using errcode = 'P0001';
  end if;
  v_balance_without := public.law_client_balance(p_license_hash, v_row.client_id) - v_row.amount;
  if v_balance_without < 0 then
    raise exception 'VOID_WOULD_NEGATIVE_BALANCE: void of % would leave balance %', v_row.amount, v_balance_without
      using errcode = 'P0001';
  end if;
  v_voided_at := now();
  update public.law_trusttx
    set status = 'Voided',
        data = data || jsonb_build_object('status', 'Voided', 'voided_reason', p_voided_reason, 'voided_at', v_voided_at),
        updated_at = v_voided_at
    where license_hash = p_license_hash and trusttx_id = p_trusttx_id
    returning * into v_row;
  return v_row;
end;
$$;

revoke all on function public.law_check_and_void_deposit from public;
grant execute on function public.law_check_and_void_deposit to service_role;
