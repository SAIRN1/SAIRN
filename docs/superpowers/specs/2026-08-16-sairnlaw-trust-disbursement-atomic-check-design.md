# SAIRNlaw — trust disbursement server-sync, step 2 (atomic check-and-write)

## Problem

`saveTrustTransaction()`'s disbursement balance check (`sairnlaw.html:2042`)
reads a local snapshot via `clientLedgerBalance()` and writes with no
`await` in between — zero race window on a single device/session, but it
cannot close a cross-device race: two staff on two different browser
sessions can each read the same pre-disbursement balance, both pass the
check independently, and both write — a real over-disbursement of client
trust funds, a bar-discipline/IOLTA compliance matter, not just a
data-integrity bug.

Step 1 (shipped 2026-08-16, `docs/superpowers/specs/2026-08-14-sairnlaw-trust-data-schema-design.md`)
made `law_trusttx`/`law_clients`/`law_matters` real and durable server-side
but deliberately did not add any balance validation — it was the
prerequisite, not the fix. This spec is the actual fix: a real server-side
atomic check-and-write that re-validates the balance at write time and
rejects the transaction if it would go negative, closing the cross-device
race step 1 explicitly deferred.

**Verified starting state (2026-08-16):**
- `law_trusttx` has `id/license_hash/app_id/trusttx_id/matter_id/client_id/
  data(jsonb)/created_at/updated_at` — `amount`/`type`/`status` currently
  live only inside the `data` jsonb blob, not as real columns.
- `api/sd-data.js`'s `law_trusttx` write block is a plain PostgREST upsert
  (`on_conflict=license_hash,trusttx_id`) — no balance logic of any kind.
- No Postgres function/stored procedure exists anywhere in this codebase's
  Supabase schema today — every other write on this platform is a plain
  table upsert via PostgREST.
- `clientLedgerBalance(clientId, tx)` (`sairnlaw.html:2002`) computes
  balance as `sum(Deposit amounts) - sum(non-Voided Disbursement amounts)`
  for a given `client_id` — a **client-level** balance, not per-matter (a
  client's trust funds are shared across their matters in this app's
  existing model; step 2 does not change that).
- `saveTrustTransaction()` writes to local storage first (optimistic —
  renders immediately), then awaits `sdnData('write','law_trusttx',rec)` in
  the background; today it only toasts pass/fail, with no rollback of the
  local record on any kind of failure.

## Scope, decided during brainstorming

- **Only Disbursement creation goes through the new atomic path.** Deposit
  writes and voids (any write where the resulting `status==='Voided'`) keep
  using the existing plain upsert from step 1 — they only ever increase
  available balance or are a flat status flip, so they carry no
  over-disbursement race risk. This keeps the change minimal: one new
  branch in the existing `law_trusttx` write handler, not a new resource.
- **Client-level balance, matching the app's existing model exactly.** The
  atomic check sums by `client_id`, not `matter_id` — no behavior change
  from what `clientLedgerBalance()` already does today, just made real and
  race-free server-side.
- **Voiding a Deposit that already has disbursements posted against it is
  explicitly OUT of scope for this pass**, even though it's a real,
  related gap (voiding a $500 deposit after a $500 disbursement against it
  retroactively puts the client negative, and nothing today or in this
  spec guards that). Logged to `SAIRN-BACKLOG.md` as a disclosed, deferred
  follow-on — a different failure mode (a rare, already-reason-required
  audit action) from the cross-device concurrent-disbursement race this
  spec exists to close, not folded in here.
- **`amount`/`type`/`status` are promoted to real columns** on
  `law_trusttx`, mirroring step 1's own precedent (`client_id`/`matter_id`
  were promoted specifically because a later feature needed to query by
  them — this is that feature). A real `numeric` `amount` column with a
  `check (amount > 0)` constraint and a real `status` column the function
  can filter on directly is safer and simpler for a money-summing function
  than parsing `data->>'amount'` text into numeric on every call.
- **Atomicity via a Postgres function + advisory lock**, not a
  serializable-transaction-with-retry. `pg_advisory_xact_lock(hashtext(
  license_hash || ':' || client_id))` at the top of the function serializes
  concurrent calls for the *same client only* (different clients never
  block each other) — the standard, correct Postgres pattern for this
  exact "check then insert" race, and simpler to get right in one
  PostgREST RPC round-trip than a client-driven serializable-retry loop
  would be.
- **A real, necessary client-side change** (unlike step 1, which needed
  none): on a genuine server rejection (`409 INSUFFICIENT_TRUST_BALANCE`,
  not a network/sync failure), `saveTrustTransaction()` rolls the
  optimistically-written local record back out of `law_trusttx` in local
  storage, re-renders, and shows the server's real computed balance in the
  error — the transaction never actually happened, so local state must not
  keep claiming it did. A mere sync/network failure (today's existing
  "saved locally only" toast) is unchanged — that path still means "this
  might be a valid transaction that just hasn't synced yet," which is a
  different, weaker claim than "the server affirmatively rejected this."

## Architecture

**Schema migration** (new file, `sql/sairnlaw_trust_disbursement_atomic_check.sql`,
idempotent, extends `law_trusttx` — does not touch `law_clients`/
`law_matters`):
```
alter table public.law_trusttx add column if not exists amount numeric;
alter table public.law_trusttx add column if not exists type text;
alter table public.law_trusttx add column if not exists status text;
-- backfill any rows written before this migration (step 1's own
-- live-verification rows, e.g. TR-VERIFY-1) from the jsonb blob:
update public.law_trusttx set amount = (data->>'amount')::numeric
  where amount is null and data->>'amount' is not null;
update public.law_trusttx set type = data->>'type'
  where type is null and data->>'type' is not null;
update public.law_trusttx set status = coalesce(data->>'status','Posted')
  where status is null;
-- constraints added only after backfill, so existing rows already satisfy them:
alter table public.law_trusttx add constraint lawtrusttx_type_check
  check (type in ('Deposit','Disbursement'));
alter table public.law_trusttx add constraint lawtrusttx_status_check
  check (status in ('Posted','Voided'));
alter table public.law_trusttx add constraint lawtrusttx_amount_positive
  check (amount is null or amount > 0);
create index if not exists idx_lawtrusttx_client_status
  on public.law_trusttx(license_hash, client_id, status);
```
The `write` handler continues to always populate `amount`/`type`/`status`
as real columns going forward (alongside the existing `data` jsonb, which
keeps carrying every other field — `method`/`reference_number`/
`description`/etc. — unpromoted, matching step 1's own "only promote what
a query needs" rule).

**The atomic function** (same migration file):
```sql
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
  select coalesce(sum(case when type='Deposit' then amount else -amount end), 0)
    into v_balance
    from public.law_trusttx
    where license_hash = p_license_hash and client_id = p_client_id
      and status = 'Posted';
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
```
PostgREST wraps each RPC call in one transaction, so the lock, the balance
read, and the insert are genuinely atomic — a second concurrent call for
the same `client_id` blocks on the advisory lock until the first commits,
then re-checks against the now-current (post-first-insert) balance. Calls
for different clients never block each other (the lock key includes
`client_id`). `on conflict ... do nothing` matches step 1's idempotent-retry
shape (a client retrying the same `trusttx_id` after a network blip doesn't
double-insert).

**Routing in `api/sd-data.js`'s `law_trusttx` write block:** branch on
`payload.type`:
- `payload.type === 'Disbursement'` **and** it's a new record (not a void
  — a void write always carries `payload.status==='Voided'`, which routes
  to the existing plain upsert instead): POST to
  `rest/v1/rpc/law_check_and_insert_disbursement` with the payload's
  fields. On a Postgres exception whose message starts with
  `INSUFFICIENT_TRUST_BALANCE`, respond `409
  {code:'INSUFFICIENT_TRUST_BALANCE', message:'Disbursement of $<amount>
  exceeds this client's real trust balance of $<balance>',
  real_balance:<balance>}` (parse both numbers out of the Postgres error
  message). Any other RPC error is a genuine server error — `502`, same as
  `upstream()`'s existing convention.
- Everything else (`Deposit`, or any write with `status==='Voided'`): the
  existing plain upsert from step 1, completely unchanged.

**Client change (`sairnlaw.html`):** `saveTrustTransaction()` keeps its
optimistic local write, but its `sdnData()` result handling gains a branch
for the new rejection shape. `sdnData()` (`sairnlaw.html:1056`) currently
collapses every failure (4xx, 5xx, network error) to `null` — this spec
needs the real distinction, so `sdnData()` gains an optional richer return
for a recognized structured error (`{rejected:true, code, message}`)
without changing its return shape for every other caller (still `null` on
any failure they don't specifically check for). On `rejected &&
code==='INSUFFICIENT_TRUST_BALANCE'`: remove the just-added record from
the local `law_trusttx` list, `st('law_trusttx', list)`, re-render
(`rTrust();rDash();`), and show the server's real message via the existing
`$('trust-err')` field (the same error slot `saveTrustTransaction()`
already uses for its own local pre-check) rather than the generic toast.
Any other failure (network, 5xx, `null`): unchanged — today's "saved
locally only" toast.

## Explicitly out of scope for this pass

- Guarding void-of-a-deposit against already-posted disbursements (logged
  to `SAIRN-BACKLOG.md` as a disclosed follow-on, not silently dropped).
- Any change to Deposit writes or void writes — both keep the plain
  upsert from step 1 unchanged.
- Any change to `law_clients`/`law_matters`.
- Wiring real client-side reads for any of the three step-1 resources
  (separate, already-disclosed future item from step 1's final review).
- A UI affordance showing the *live* server balance before a disbursement
  is attempted (e.g. a real-time balance display) — this pass only handles
  the rejection case after the fact; a pre-flight balance fetch is a
  separate, smaller future enhancement if the rejection rate in practice
  warrants it.

## Edge cases

- **Two concurrent disbursements for the same client, combined total
  exceeding balance:** the second call blocks on the advisory lock until
  the first's transaction commits, then re-sums with the first disbursement
  already counted — correctly rejects if the combined total would go
  negative. This is the exact race this spec exists to close.
- **Two concurrent disbursements for *different* clients:** never block
  each other (lock key is per-`client_id`) — no unnecessary serialization
  across unrelated clients.
- **A disbursement retried after a network failure (same `trusttx_id`):**
  `on conflict ... do nothing` means a genuine retry of an already-accepted
  disbursement doesn't double-count against balance or double-insert;
  `returning *` yields no row in that case, which the write handler treats
  as success (idempotent replay), matching step 1's `resolution=merge-
  duplicates` upsert semantics for every other resource.
- **Migration not yet run:** the RPC call itself 404s/400s (function
  doesn't exist) — the same `NOT_PROVISIONED` detection step 1 already
  uses (route on the RPC call's 404/400 the same way the plain upsert
  routes do) so this degrades the same honest way, not a new failure mode.
- **A Disbursement payload missing `amount`/`type`:** rejected before ever
  reaching the RPC call, by the same required-field validation step 1
  already has (`payload.id`/`payload.matter_id`/`payload.client_id`) plus
  a new check for `payload.amount` on the Disbursement path specifically
  (Deposits don't strictly need this pre-check since they hit the plain
  upsert, but the DB's own `amount > 0` constraint is the final backstop
  either way).

## Testing / verification plan

The Postgres function itself is the one piece of new logic in this whole
platform worth a real concurrency test, not just a live curl round-trip:
after a human runs the migration, fire two genuinely concurrent
disbursement requests for the same client (via two parallel `curl`
processes backgrounded in the same shell, both targeting a balance that
can only support one of them) and confirm exactly one succeeds and the
other gets a real `409 INSUFFICIENT_TRUST_BALANCE` with the correct
computed balance — not both succeeding (the bug this spec exists to fix)
and not both failing. Also live-verify: a valid disbursement within
balance succeeds and appears via `law_trusttx` read; an over-balance
disbursement from a single caller is rejected with the real balance in the
message; a Deposit still goes through the unchanged plain-upsert path; a
void still goes through the unchanged plain-upsert path; the client-side
rollback (local record removed, real error shown) by attempting a
disbursement that will genuinely be rejected through the actual
`sairnlaw.html` UI, not just via curl.
