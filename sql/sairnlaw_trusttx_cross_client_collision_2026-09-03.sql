-- sql/sairnlaw_trusttx_cross_client_collision_2026-09-03.sql
-- SAIRNlaw trust disbursement, step 3b: closes a CROSS-CLIENT TRUST-ACCOUNT
-- LEAK in law_check_and_insert_disbursement().
--
-- Supersedes the function body in sql/sairnlaw_deposit_void_balance_guard.sql
-- (step 3a), which itself superseded the one in
-- sql/sairnlaw_trust_disbursement_atomic_check.sql (step 2). If either of
-- those files is ever re-run, RE-RUN THIS ONE IMMEDIATELY AFTER -- both would
-- otherwise silently restore the vulnerable version with no error anywhere,
-- exactly as step 3a's own header warns about step 2.
--
-- Safe to re-run -- create-or-replace throughout, no DDL, no data change.
--
-- ════════════════════════════════════════════════════════════════════════
-- WHAT WAS WRONG. THE LOCK AND THE UNIQUENESS KEY DISAGREED.
-- ════════════════════════════════════════════════════════════════════════
-- The advisory lock is taken on (license_hash, client_id) -- the CALLER'S
-- asserted client. The retry-idempotency lookup then matched on
-- (license_hash, trusttx_id) with NO client predicate, and the table's unique
-- constraint is likewise (license_hash, trusttx_id) -- licence-wide.
--
-- One key is per-client and the other is per-licence. Everything below follows
-- from that single mismatch.
--
-- ── FAILURE 1: A CLIENT'S TRUST ROW RETURNED TO ANOTHER CLIENT'S REQUEST ─
-- A disbursement posted for client B, whose trusttx_id already exists under
-- client A, took the retry-idempotency branch and returned A'S ROW. The caller
-- got HTTP 200 {ok:true} carrying A's amount, matter_id, description and
-- reference number -- in a lawyer's trust ledger, that is one client's
-- financial record handed to another client's transaction. No money moved for
-- B and nothing said so.
--
-- ── FAILURE 2: A PHANTOM DISBURSEMENT THAT REPORTS SUCCESS ──────────────
-- `on conflict (license_hash, trusttx_id) do nothing returning *` returns NO
-- ROW on conflict, so v_row stayed NULL and the function returned a null
-- composite. api/sd-data.js then did:
--
--     res.status(200).json({ ok: true, data: row ? row.data : payload });
--
-- -- echoing THE CALLER'S OWN PAYLOAD back as though it were the stored row.
-- The lawyer's screen showed the disbursement posted; the database had no such
-- row; the trust balance on screen and the trust balance in the ledger
-- disagreed, in the client's favour on screen. That is the silent-success
-- class this platform refuses everywhere else, on a trust account.
--
-- ── WHY THE LOCK DID NOT PREVENT IT ────────────────────────────────────
-- Two calls colliding on trusttx_id but naming DIFFERENT clients take
-- DIFFERENT advisory locks, so they do not serialize against each other at
-- all. The lock only ever protected the balance arithmetic for one client; it
-- was never able to protect a licence-wide unique key.
--
-- ── AND IT IS REACHABLE, NOT THEORETICAL ───────────────────────────────
-- sairnlaw.html's id generator is
--
--     newId(prefix) => prefix + '-' + Date.now() + '-' + floor(random()*1000)
--
-- One thousand suffixes per millisecond, not a UUID, and the same generator
-- serves every client in the firm. Two people posting in the same millisecond
-- collide with probability 1/1000, and over a firm's transaction history the
-- birthday bound makes it a question of when. This was found by reading the
-- id generator, not by assuming a UUID.
--
-- ════════════════════════════════════════════════════════════════════════
-- THE FIX, AND WHY IT REFUSES RATHER THAN REPAIRS
-- ════════════════════════════════════════════════════════════════════════
-- 1. The idempotency lookup now carries `and client_id = p_client_id`. A
--    genuine retry -- same id, same client -- still returns the existing row,
--    which is the whole point of that branch and is preserved exactly.
--
-- 2. A same-id/different-client collision now RAISES. It does not silently
--    return the other client's row, and it does not quietly mint a new id on
--    the caller's behalf either. Re-keying someone's trust transaction inside
--    the database, without the firm knowing, would put a disbursement in the
--    ledger under an id their own records do not have -- a reconciliation
--    problem discovered at an audit rather than at the keyboard. The caller is
--    told, and re-submits with a fresh id.
--
-- 3. The `do nothing` null path is closed. If the insert still conflicts after
--    both checks -- a same-id/same-client insert committed by a concurrent
--    transaction between the lookup and the insert -- the row is RE-SELECTED
--    and returned, because that is a true retry and returning it is correct.
--    If even that finds nothing, the function raises rather than returning
--    null. NO PATH RETURNS NULL ANY MORE, which is what let a phantom
--    disbursement report success.
--
-- The advisory lock is left keyed on (license_hash, client_id). Widening it to
-- the licence would serialize every client in the firm behind one another for
-- a collision that is rare -- the correct fix is to make the rare case LOUD,
-- not to make the common case slow.

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

  -- RETRY-IDEMPOTENCY, NOW CLIENT-SCOPED. Same id AND same client is a genuine
  -- retry of an already-committed disbursement (e.g. the response was lost to
  -- a network blip) and must return the existing row rather than re-running
  -- the balance check -- the balance sum already includes this disbursement,
  -- so re-checking would wrongly reject an already-valid transaction. That
  -- behaviour is unchanged; only the client predicate is new.
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

    -- THE NULL PATH, CLOSED. `do nothing` returns no row, so a conflict here
    -- left v_row NULL and the function returned a null composite -- which
    -- api/sd-data.js turned into HTTP 200 with the caller's own payload echoed
    -- back as the stored row. A phantom disbursement that reports success.
    --
    -- Reaching here means a concurrent transaction committed this exact id
    -- between the lookup above and this insert. Re-select to find out which
    -- case it was.
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

-- ── Verify after running ────────────────────────────────────────────────
-- The function's definition should now contain the client predicate and the
-- collision refusal (expect 2 and 1):
--
--   select
--     (select count(*) from regexp_matches(prosrc, 'client_id = p_client_id', 'g')) as client_scoped,
--     (select count(*) from regexp_matches(prosrc, 'TRUSTTX_ID_COLLISION', 'g')) as collision_raises
--   from pg_proc where proname = 'law_check_and_insert_disbursement';
--
-- Reproduce the leak against a scratch licence to confirm it is closed --
-- expect the second call to RAISE, where before it returned the first row:
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
-- live-write verification on this platform has, and the reason
-- SAIRN-OPEN-WORK-INDEX.md tracks hand-written cleanup files.
