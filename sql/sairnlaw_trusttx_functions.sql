-- sql/sairnlaw_trusttx_functions.sql
-- ═══════════════════════════════════════════════════════════════════════
-- THE SINGLE SOURCE OF TRUTH for every law_trusttx function.
-- Consolidated 2026-09-03. Run THIS file. Do not run the three it replaces.
-- ═══════════════════════════════════════════════════════════════════════
--
-- Defines, at their current correct versions:
--
--   law_client_balance()                 the shared balance helper
--   law_check_and_insert_disbursement()  the atomic check-and-write
--   law_check_and_void_deposit()         the atomic void guard
--
-- Safe to re-run -- create-or-replace throughout, no DDL, no data change.
--
-- ── WHY THIS FILE EXISTS: THE CHAIN WAS A LOADED GUN ───────────────────
-- Three files had come to define law_check_and_insert_disbursement(), each
-- superseding the last:
--
--   step 2   sql/sairnlaw_trust_disbursement_atomic_check.sql   (2026-08-16)
--   step 3a  sql/sairnlaw_deposit_void_balance_guard.sql        (2026-08-17)
--   step 3b  sql/sairnlaw_trusttx_cross_client_collision_2026-09-03.sql
--
-- Every one of them was a plain `create or replace`. **Re-running an older
-- file for its OTHER contents silently reverted the function to that file's
-- version, with no error, no warning and no diff anywhere.** Step 2 needed
-- re-running for its table DDL; step 3a for the balance helper and the void
-- guard. Doing either would have restored a version of the disbursement
-- function that hands one client's trust row to another client's request.
--
-- Steps 2 and 3a each carried a prose warning about the file BEFORE them. That
-- is the tell: the trap was already known twice and was answered twice with a
-- comment. A comment does not stop a `\i` in a SQL editor at midnight. So the
-- function bodies have been REMOVED from all three files -- they now point
-- here and define nothing. **The trap is gone because the duplicate text is
-- gone, not because a third warning was added.**
--
-- IF YOU ADD A FOURTH FILE THAT REDEFINES ANY FUNCTION BELOW, YOU HAVE
-- REBUILT THE TRAP. Edit this file instead.
--
-- ── WHAT EACH FUNCTION GUARANTEES, so a future edit knows what it may not
-- ── quietly drop ───────────────────────────────────────────────────────
--
-- law_client_balance()
--   Sums Posted rows only, Deposits positive and everything else negative,
--   for ONE client of ONE licence. `stable`, so a single statement may reuse
--   the result. Both guards below call it rather than re-implementing the
--   sum -- an inline copy in either would be free to drift.
--
-- law_check_and_insert_disbursement()
--   * Advisory lock on (license_hash, client_id). NOT widened to the licence:
--     that would serialize every client in the firm behind one another for a
--     rare collision. Make the rare case loud, not the common case slow.
--   * Retry-idempotency is CLIENT-SCOPED. Same id AND same client returns the
--     stored row without re-running the balance check -- the balance already
--     includes that disbursement, so re-checking would wrongly reject an
--     already-committed transaction.
--   * SAME ID, DIFFERENT CLIENT RAISES. It does not return the other client's
--     row (the 2026-09-03 leak) and does not quietly mint a new id either:
--     re-keying inside the database would put a disbursement in the ledger
--     under an id the firm's own records do not have, found at an audit
--     rather than at the keyboard. The collision is checked BEFORE the
--     balance arithmetic so the caller is told what is actually wrong.
--   * The error does NOT name the other client. The caller may know their id
--     is taken; they may not learn which other client of the firm holds it,
--     and this message reaches a user-facing screen.
--   * NO PATH RETURNS NULL. `on conflict do nothing returning *` yields no
--     row, and api/sd-data.js used to turn a null row into HTTP 200 with the
--     caller's own payload echoed back as the stored record -- a disbursement
--     that reported success and posted nothing.
--
-- law_check_and_void_deposit()
--   * Looks the row up by (license_hash, trusttx_id) and LEARNS client_id
--     from the stored row. It accepts no caller-asserted client at all, so
--     the cross-client leak that hit the disbursement path cannot arise here.
--     Stated because the lookups look superficially like the vulnerable ones
--     and a future reader "fixing them for consistency" would be adding a
--     predicate on a value this function does not take.
--   * Looks up TWICE -- once to learn client_id for the lock key, once after
--     acquiring it -- because another transaction may have changed status or
--     amount while this call waited. Relies on READ COMMITTED, where each
--     statement takes a fresh snapshot; under REPEATABLE READ or SERIALIZABLE
--     the re-select would return the same pre-lock tuple and this guard would
--     quietly stop working with no error anywhere.
--   * The balance guard applies only when the STORED row is a Deposit, never
--     a client-asserted type -- closing a hole where a caller could claim an
--     existing Deposit was a 'Disbursement' to route around this function.

-- ── the shared balance helper ──────────────────────────────────────────
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

-- ── the atomic check-and-write ─────────────────────────────────────────
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
  v_other_client text;
begin
  perform pg_advisory_xact_lock(hashtext(p_license_hash || ':' || p_client_id));

  -- RETRY-IDEMPOTENCY, CLIENT-SCOPED. Same id AND same client is a genuine
  -- retry of an already-committed disbursement (e.g. the response was lost to
  -- a network blip) and must return the existing row rather than re-running
  -- the balance check -- the balance sum already includes this disbursement,
  -- so re-checking would wrongly reject an already-valid transaction.
  select * into v_existing
    from public.law_trusttx
    where license_hash = p_license_hash
      and trusttx_id = p_trusttx_id
      and client_id = p_client_id;
  v_existing_found := found;

  if v_existing_found then
    v_row := v_existing;
  else
    -- SAME ID, DIFFERENT CLIENT. Checked BEFORE the balance arithmetic so the
    -- caller is told what is actually wrong rather than being handed an
    -- INSUFFICIENT_TRUST_BALANCE about a balance that was never the problem.
    select client_id into v_other_client
      from public.law_trusttx
      where license_hash = p_license_hash and trusttx_id = p_trusttx_id;
    if found then
      -- The other client's id is NOT included in the message. The caller is
      -- entitled to know their id is taken; they are not entitled to learn
      -- which other client of the firm holds it, and this error crosses back
      -- to a user-facing screen.
      raise exception
        'TRUSTTX_ID_COLLISION: transaction id % already exists under a different client for this license -- resubmit with a new id',
        p_trusttx_id
        using errcode = 'P0001';
    end if;

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

    -- THE NULL PATH, CLOSED. Reaching here means a concurrent transaction
    -- committed this exact id between the lookup above and this insert.
    -- Re-select to find out which case it was.
    if v_row.trusttx_id is null then
      select * into v_existing
        from public.law_trusttx
        where license_hash = p_license_hash
          and trusttx_id = p_trusttx_id
          and client_id = p_client_id;
      if found then
        -- Same client committed it a moment ago: a true retry, and returning
        -- it is the correct, idempotent answer.
        v_row := v_existing;
      else
        -- It exists under a DIFFERENT client -- the same collision as above,
        -- reached through the race rather than the lookup. Same refusal.
        raise exception
          'TRUSTTX_ID_COLLISION: transaction id % was taken by a different client while this disbursement was being written -- resubmit with a new id',
          p_trusttx_id
          using errcode = 'P0001';
      end if;
    end if;
  end if;

  -- NO PATH BELOW THIS LINE CAN RETURN NULL. Asserted rather than assumed: if
  -- a future edit reintroduces one, this raises instead of handing the caller
  -- a success it did not earn.
  if v_row.trusttx_id is null then
    raise exception
      'DISBURSEMENT_NOT_WRITTEN: no trust transaction row was produced for % -- nothing was posted',
      p_trusttx_id
      using errcode = 'P0001';
  end if;

  return v_row;
end;
$$;

revoke all on function public.law_check_and_insert_disbursement from public;
grant execute on function public.law_check_and_insert_disbursement to service_role;

-- ── the atomic deposit-void guard ──────────────────────────────────────
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
  -- Re-select after the lock: relies on PostgREST/Postgres's default READ
  -- COMMITTED isolation, where each statement after this point takes a fresh
  -- snapshot -- if this connection pool were ever changed to REPEATABLE READ
  -- or SERIALIZABLE, this re-select would silently return the same pre-lock
  -- tuple and this guard's whole point (seeing another transaction's
  -- committed effects) would quietly stop working with no error anywhere.
  select * into v_row
    from public.law_trusttx
    where license_hash = p_license_hash and trusttx_id = p_trusttx_id;
  if v_row.status <> 'Posted' then
    raise exception 'ALREADY_VOIDED: trust transaction % is not in Posted status', p_trusttx_id
      using errcode = 'P0001';
  end if;
  -- Only a Deposit-void can decrease a client's balance (a Disbursement-void
  -- only ever increases it) -- so the balance guard applies only when the
  -- STORED row (not a client-supplied type claim) is actually a Deposit.
  if v_row.type = 'Deposit' then
    if v_row.amount is null then
      raise exception 'DATA_INTEGRITY: trust transaction % has no amount recorded', p_trusttx_id
        using errcode = 'P0001';
    end if;
    v_balance_without := public.law_client_balance(p_license_hash, v_row.client_id) - v_row.amount;
    if v_balance_without < 0 then
      raise exception 'VOID_WOULD_NEGATIVE_BALANCE: void of % would leave balance %', v_row.amount, v_balance_without
        using errcode = 'P0001';
    end if;
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

-- ── Verify after running ───────────────────────────────────────────────
-- All three functions present, and the disbursement guard carrying the
-- client predicate (2) and both collision refusals (2):
--
--   select proname from pg_proc
--    where proname in ('law_client_balance',
--                      'law_check_and_insert_disbursement',
--                      'law_check_and_void_deposit')
--    order by proname;   -- expect 3 rows
--
--   select
--     (select count(*) from regexp_matches(prosrc, 'client_id = p_client_id', 'g')) as client_scoped,
--     (select count(*) from regexp_matches(prosrc, 'TRUSTTX_ID_COLLISION', 'g')) as collision_raises
--   from pg_proc where proname = 'law_check_and_insert_disbursement';
--   -- expect client_scoped = 2, collision_raises = 2
--
-- Reproduce the cross-client leak against a scratch licence to confirm it is
-- closed -- expect the second call to RAISE, where before it returned the
-- first client's row:
--
--   select public.law_check_and_insert_disbursement(
--     'SCRATCH-HASH','TX-COLLIDE-1','M1','CLIENT-A',10,'Check',null,'a',null,null);
--   -- (fund CLIENT-B first with a Deposit, then:)
--   select public.law_check_and_insert_disbursement(
--     'SCRATCH-HASH','TX-COLLIDE-1','M1','CLIENT-B',10,'Check',null,'b',null,null);
--   -- expected: ERROR TRUSTTX_ID_COLLISION, not CLIENT-A's row
--
-- Then delete the scratch rows. law_trusttx carries no delete grant, so that
-- cleanup is a SQL-editor statement -- the same constraint every other
-- live-write verification on this platform has.
