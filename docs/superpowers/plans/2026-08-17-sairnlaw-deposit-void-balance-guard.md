# SAIRNlaw Deposit-Void Balance Guard (Step 3a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the disclosed deposit-void balance gap (`SAIRN-BACKLOG.md`) by making voiding a Deposit go through the same atomic, advisory-lock-guarded check step 2 already uses for Disbursement creation.

**Architecture:** One new idempotent SQL migration extracts a shared `law_client_balance()` helper (both step 2's existing function and the new one call it), edits step 2's `law_check_and_insert_disbursement()` to use it (no behavior change), and adds `law_check_and_void_deposit()` — looks up the row, locks per-client, re-verifies the row under the lock, rejects `ALREADY_VOIDED`/`VOID_WOULD_NEGATIVE_BALANCE`, else voids it. `api/sd-data.js`'s `law_trusttx` write block gains one more branch routing Deposit-voids through the new RPC; Deposit-creates and Disbursement-voids keep the unchanged plain upsert. `sairnlaw.html`'s `sdnData()` extends its structured-rejection codes; `confirmVoid()` rolls back its optimistic local mutation on a real rejection.

**Tech Stack:** Vanilla Node.js serverless function (`api/sd-data.js`, Vercel), Supabase/PostgREST RPC, plain SQL (Supabase SQL editor, no migration tool), vanilla JS client (`sairnlaw.html`).

## Global Constraints

- **Only `payload.type === 'Deposit' && payload.status === 'Voided'` routes through the new RPC.** Deposit-create, Disbursement-void, and Disbursement-create (step 2, unchanged) all keep their existing paths untouched.
- **Balance is client-level**, via the shared `law_client_balance()` helper — matches every other balance computation in this feature.
- **Plan-level refinement beyond the spec's literal architecture text** (found while writing this plan, same category as step 1's and step 2's own disclosed mid-build corrections): `law_check_and_void_deposit()` does the row lookup **twice** — once before acquiring the advisory lock (to learn `client_id`, needed for the lock key, since unlike the disbursement function this one doesn't receive `client_id` as a parameter), and once again immediately after acquiring the lock. The spec only described the first lookup. The second, post-lock lookup is added here because the pre-lock read is a genuine stale-read risk: another transaction could change this exact row's `status`/`amount` between the first read and lock acquisition, and the `ALREADY_VOIDED`/balance checks must use the row's state as of *after* the lock is held, not before. Cheap to add, closes a real TOCTOU gap in the design as originally described.
- **`node --check api/sd-data.js` must show zero errors** before any commit that touches it.
- **`python tools/checkblocks.py sairnlaw.html` must show `FAILED_BLOCKS:0`** before any commit that touches it (this file has exactly one `<script>` block, confirmed in step 2's Task 3).
- **Every SQL statement must be idempotent** (`create or replace function` throughout) — this file runs against a database that already has step 2's tables/functions live.
- **`sdnData()`'s structured-rejection branch stays scoped to named codes only** — extending it to `VOID_WOULD_NEGATIVE_BALANCE`/`ALREADY_VOIDED` must not broaden it to match any `d.error.code`; every other existing caller's `if(syncResult)` truthy check must keep working exactly as today.
- Do not touch Deposit-create, Disbursement-void, `law_clients`/`law_matters`, or the still-unwired client-side reads (separate, disclosed gaps, out of scope for this plan).

---

### Task 1: SQL migration — `law_client_balance()` helper + `law_check_and_void_deposit()`

**Files:**
- Create: `sql/sairnlaw_deposit_void_balance_guard.sql`

**Interfaces:**
- Produces: `public.law_client_balance(p_license_hash text, p_client_id text) returns numeric` and `public.law_check_and_void_deposit(p_license_hash text, p_trusttx_id text, p_voided_reason text) returns public.law_trusttx` — consumed by Task 2's `api/sd-data.js` code via `rpc/law_check_and_void_deposit`. Also `create or replace`s `public.law_check_and_insert_disbursement` (step 2's existing function) to call the new helper — same signature, same behavior, no caller-visible change. No code in this repo imports this file — it's handed to a human to run in Supabase's SQL editor.

- [ ] **Step 1: Write the migration**

Create `sql/sairnlaw_deposit_void_balance_guard.sql`:

```sql
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
```

- [ ] **Step 2: Hand off for manual execution**

This SQL is NOT run by this task. Note in the task report that a human must run `sql/sairnlaw_deposit_void_balance_guard.sql` in Supabase's SQL editor before Task 4's live verification can pass — Tasks 2-3's code can still be written and committed without it having run yet.

- [ ] **Step 3: Commit**

```bash
git add sql/sairnlaw_deposit_void_balance_guard.sql
git commit -m "docs: SQL -- SAIRNlaw deposit-void balance guard (law_client_balance helper + law_check_and_void_deposit)"
```

---

### Task 2: `api/sd-data.js` — route Deposit-voids through the atomic guard

**Files:**
- Modify: `api/sd-data.js` (the `law_trusttx` write block, currently lines 1973-2019)

**Interfaces:**
- Consumes: `rest()`, `headers`, `licHash` (already defined in the enclosing closure). Calls the new `law_check_and_void_deposit` RPC from Task 1 via `POST rest('rpc/law_check_and_void_deposit')`.
- Produces: on a genuine rejection, `409 {error:{code:'ALREADY_VOIDED',...}}` or `409 {error:{code:'VOID_WOULD_NEGATIVE_BALANCE', message, real_balance}}` or `409 {error:{code:'NOT_FOUND',...}}` — consumed by Task 3's `sairnlaw.html` change. On success, unchanged `{ok:true, data:{...}}` shape.

- [ ] **Step 1: Insert the Deposit-void branch**

Find (`api/sd-data.js`, exact current content):

```js
    if (resource === 'law_trusttx' && action === 'write') {
      if (!payload || !payload.id || !payload.matter_id || !payload.client_id) { res.status(400).json({ error: { message: 'law_trusttx payload.id, payload.matter_id, and payload.client_id are required' } }); return; }
      if (payload.type !== 'Deposit' && payload.type !== 'Disbursement') { res.status(400).json({ error: { message: "law_trusttx payload.type must be exactly 'Deposit' or 'Disbursement'" } }); return; }
      // Atomic disbursement check-and-write (2026-08-16, step 2). A NEW
```

Replace with:

```js
    if (resource === 'law_trusttx' && action === 'write') {
      if (!payload || !payload.id || !payload.matter_id || !payload.client_id) { res.status(400).json({ error: { message: 'law_trusttx payload.id, payload.matter_id, and payload.client_id are required' } }); return; }
      if (payload.type !== 'Deposit' && payload.type !== 'Disbursement') { res.status(400).json({ error: { message: "law_trusttx payload.type must be exactly 'Deposit' or 'Disbursement'" } }); return; }
      // Atomic deposit-void balance guard (2026-08-17, step 3a). Voiding a
      // Deposit is the one void that can DECREASE a client's balance (a
      // Disbursement-void only ever increases it, so it stays on the plain
      // upsert below, unguarded, same reasoning as step 2's Deposit-create/
      // void-in-general exemption). Routes through
      // law_check_and_void_deposit() instead of a plain upsert. See
      // docs/superpowers/specs/2026-08-17-sairnlaw-deposit-void-balance-guard-design.md.
      if (payload.type === 'Deposit' && payload.status === 'Voided') {
        const r = await fetch(rest('rpc/law_check_and_void_deposit'), {
          method: 'POST',
          headers,
          body: JSON.stringify({
            p_license_hash: licHash, p_trusttx_id: String(payload.id),
            p_voided_reason: payload.voided_reason || null
          })
        });
        if (r.status === 404) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql and sql/sairnlaw_deposit_void_balance_guard.sql in Supabase first.' } }); return; }
        if (r.status === 400) {
          const bodyText = await r.text();
          let bodyJson = null; try { bodyJson = JSON.parse(bodyText); } catch (e) {}
          const msg = (bodyJson && bodyJson.message) || bodyText || '';
          if (/relation .* does not exist|function .* does not exist/i.test(msg)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql and sql/sairnlaw_deposit_void_balance_guard.sql in Supabase first.' } }); return; }
          if (/^ALREADY_VOIDED/.test(msg)) { res.status(409).json({ error: { code: 'ALREADY_VOIDED', message: 'This transaction has already been voided.' } }); return; }
          if (/^NOT_FOUND/.test(msg)) { res.status(409).json({ error: { code: 'NOT_FOUND', message: 'This transaction could not be found on the server.' } }); return; }
          const balMatch = /VOID_WOULD_NEGATIVE_BALANCE: void of (-?[\d.]+) would leave balance (-?[\d.]+)/.exec(msg);
          if (balMatch) {
            const realBalance = Number(balMatch[2]);
            res.status(409).json({ error: { code: 'VOID_WOULD_NEGATIVE_BALANCE', message: 'Voiding this deposit would leave this client\'s real trust balance at $' + realBalance.toFixed(2) + ' — void rejected.', real_balance: realBalance } });
            return;
          }
          console.error('law_check_and_void_deposit error (status 400):', msg);
          res.status(502).json({ error: { message: 'Data store error — try again', detail: msg } });
          return;
        }
        if (!r.ok) { const rows = await r.json().catch(() => null); return upstream(res, rows); }
        const voidRpcResult = await r.json();
        const voidRow = Array.isArray(voidRpcResult) ? voidRpcResult[0] : voidRpcResult;
        res.status(200).json({ ok: true, data: voidRow ? voidRow.data : payload });
        return;
      }
      // Atomic disbursement check-and-write (2026-08-16, step 2). A NEW
```

- [ ] **Step 2: Verify no syntax errors**

Run: `node --check api/sd-data.js`
Expected: no output (clean exit).

- [ ] **Step 3: Commit**

```bash
git add api/sd-data.js
git commit -m "feat: SAIRNlaw -- route Deposit-void writes through the atomic balance guard"
```

---

### Task 3: `sairnlaw.html` — extend rejection codes, roll back on a real void rejection

**Files:**
- Modify: `sairnlaw.html:1056-1083` (`sdnData()`)
- Modify: `sairnlaw.html:2097-2107` (`confirmVoid()`)

**Interfaces:**
- Consumes: Task 2's `409 {code:'VOID_WOULD_NEGATIVE_BALANCE'|'ALREADY_VOIDED', message, ...}` response shapes.
- Produces: `sdnData()` returns `{rejected:true, code, message}` for `INSUFFICIENT_TRUST_BALANCE` (unchanged, step 2), `VOID_WOULD_NEGATIVE_BALANCE`, and `ALREADY_VOIDED` — every other failure still returns plain `null`, unchanged. `confirmVoid()` checks `syncResult && syncResult.rejected` and reverts its optimistic local mutation when true.

- [ ] **Step 1: Extend `sdnData()`'s structured-rejection check**

Find (`sairnlaw.html:1074-1076`):

```js
        if(d&&d.error&&d.error.code==='INSUFFICIENT_TRUST_BALANCE'){
          return {rejected:true,code:d.error.code,message:d.error.message};
        }
```

Replace with:

```js
        if(d&&d.error&&(d.error.code==='INSUFFICIENT_TRUST_BALANCE'||d.error.code==='VOID_WOULD_NEGATIVE_BALANCE'||d.error.code==='ALREADY_VOIDED')){
          return {rejected:true,code:d.error.code,message:d.error.message};
        }
```

- [ ] **Step 2: Add rollback handling to `confirmVoid()`**

Find (`sairnlaw.html:2097-2107`, exact current content):

```js
async function confirmVoid(){
  var reason=$('voidreason').value.trim();
  if(!reason){$('void-err').textContent='A reason is required to void a trust transaction';return;}
  var list=trustTransactions();
  var t=list.find(function(x){return x.id===voidTxId;});if(!t)return;
  t.status='Voided';t.voided_reason=reason;t.voided_at=new Date().toISOString();
  st('law_trusttx',list);
  closeVoidModal();rTrust();rDash();
  var syncResult=await sdnData('write','law_trusttx',t);
  toast(syncResult?'Transaction voided':'Voided on this device only -- server sync not yet enabled',syncResult?3000:5000);
}
```

Replace with:

```js
async function confirmVoid(){
  var reason=$('voidreason').value.trim();
  if(!reason){$('void-err').textContent='A reason is required to void a trust transaction';return;}
  var list=trustTransactions();
  var t=list.find(function(x){return x.id===voidTxId;});if(!t)return;
  t.status='Voided';t.voided_reason=reason;t.voided_at=new Date().toISOString();
  st('law_trusttx',list);
  closeVoidModal();rTrust();rDash();
  var syncResult=await sdnData('write','law_trusttx',t);
  // Real server-side rejection (2026-08-17, deposit-void balance guard):
  // the optimistic local void above never actually happened server-side,
  // so revert it rather than leaving a phantom void in local storage that
  // would keep displaying as real (future local balance checks) until
  // someone notices. A plain sync failure (network error, NOT_PROVISIONED,
  // etc.) is unchanged below -- that still just means "not yet synced."
  if(syncResult&&syncResult.rejected){
    var revertList=trustTransactions();
    var revertT=revertList.find(function(x){return x.id===t.id;});
    if(revertT){revertT.status='Posted';revertT.voided_reason='';revertT.voided_at='';}
    st('law_trusttx',revertList);
    rTrust();rDash();
    toast(syncResult.message||'Void rejected -- this transaction was not voided',7000);
    return;
  }
  toast(syncResult?'Transaction voided':'Voided on this device only -- server sync not yet enabled',syncResult?3000:5000);
}
```

- [ ] **Step 3: Full syntax sweep**

Run: `python tools/checkblocks.py sairnlaw.html`
Expected: `TOTAL_BLOCKS:1` `FAILED_BLOCKS:0`.

- [ ] **Step 4: Commit**

```bash
git add sairnlaw.html
git commit -m "feat: SAIRNlaw -- roll back optimistic local void on a real balance-guard rejection"
```

---

### Task 4: Full verification sweep, concurrency test, live-verify, and push

**Files:** none (verification only)

- [ ] **Step 1: Full local syntax sweep**

Run: `node --check api/sd-data.js` (clean). Run: `python tools/checkblocks.py sairnlaw.html` (`FAILED_BLOCKS:0`).

- [ ] **Step 2: Confirm the migration has been run**

Ask whoever is present to confirm `sql/sairnlaw_deposit_void_balance_guard.sql` has been run in Supabase's SQL editor (per Task 1's hand-off note) — required before this task's live checks can pass. If it hasn't been run yet, stop here and report that as the blocker rather than proceeding to push with an unverified server layer.

- [ ] **Step 3: Run the full Guardian review before commit/push**

Invoke the `sairn-guardian-v2` skill's applicable checks against the diff, per CLAUDE.md's standing Push Protocol (this diff is backend + one client function pair, not HTML panels — apply Check 0a syntax, no-hardcoded-secrets, and Check 28 cross-app/resource-name collision checks; design/nav/KPI checks are not applicable).

- [ ] **Step 4: Live concurrency test — the actual bug this plan fixes**

Using a real SAIRNlaw license key (e.g. `LAW-TEST-2026`), set up a client with exactly one $500 Deposit (balance $500), then fire a Disbursement-create for $500 and a void of that same Deposit **simultaneously** — proving the same advisory lock genuinely serializes across both operations, not just within one kind:

```bash
# 1. Fresh client + matter + one $500 deposit
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_clients","payload":{"id":"CL-VOIDRACE-1","name":"Void Race Client"}}'
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_matters","payload":{"id":"MT-VOIDRACE-1","client_id":"CL-VOIDRACE-1","matter_name":"Void Race Matter"}}'
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-VOIDRACE-DEP","matter_id":"MT-VOIDRACE-1","client_id":"CL-VOIDRACE-1","type":"Deposit","amount":500}}'

# 2. Simultaneously: void that deposit, AND disburse $500 against it
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-VOIDRACE-DEP","matter_id":"MT-VOIDRACE-1","client_id":"CL-VOIDRACE-1","type":"Deposit","amount":500,"status":"Voided","voided_reason":"race test"}}' > /tmp/voidrace_void.json &
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-VOIDRACE-DISB","matter_id":"MT-VOIDRACE-1","client_id":"CL-VOIDRACE-1","type":"Disbursement","amount":500}}' > /tmp/voidrace_disb.json &
wait
cat /tmp/voidrace_void.json; echo; cat /tmp/voidrace_disb.json; echo
```

Expected: exactly one of the two succeeds. If the void wins first: the disbursement is correctly rejected (`INSUFFICIENT_TRUST_BALANCE`, real balance $0 after the void). If the disbursement wins first: the void is correctly rejected (`VOID_WOULD_NEGATIVE_BALANCE`, since voiding would leave the balance at -$500). Either outcome is correct — what's wrong is both succeeding. Confirm via a `law_trusttx` read afterward which one actually landed.

- [ ] **Step 5: Live-verify the remaining cases**

```bash
# Void within safe balance succeeds
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_clients","payload":{"id":"CL-VOIDOK-1","name":"Void OK Client"}}'
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_matters","payload":{"id":"MT-VOIDOK-1","client_id":"CL-VOIDOK-1","matter_name":"Void OK Matter"}}'
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-VOIDOK-DEP","matter_id":"MT-VOIDOK-1","client_id":"CL-VOIDOK-1","type":"Deposit","amount":300}}'
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-VOIDOK-DEP","matter_id":"MT-VOIDOK-1","client_id":"CL-VOIDOK-1","type":"Deposit","amount":300,"status":"Voided","voided_reason":"clean test"}}'
# Expected: {"ok":true,...}

# Voiding an already-voided deposit is rejected
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-VOIDOK-DEP","matter_id":"MT-VOIDOK-1","client_id":"CL-VOIDOK-1","type":"Deposit","amount":300,"status":"Voided","voided_reason":"second attempt"}}'
# Expected: 409 ALREADY_VOIDED

# Disbursement-void still uses the unchanged plain upsert
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-RACE-C","matter_id":"MT-RACE-1","client_id":"CL-RACE-1","type":"Disbursement","amount":100,"status":"Voided","voided_reason":"plain path check"}}'
# Expected: {"ok":true,...} (this TR-RACE-C row exists from step 2's own live verification)
```

Also confirm in the live app (`sairn.vercel.app/sairnlaw`): attempt a void through the actual UI on a deposit whose void would genuinely be rejected, and confirm the transaction reverts to `Posted` in the Trust panel after the rejection toast, rather than sitting there as a phantom void.

- [ ] **Step 6: Push**

```bash
git push origin main
```

- [ ] **Step 7: Live-verify against production (post-push)**

Repeat Step 4/5's checks against `sairn.vercel.app` directly if they were run pre-push against a preview URL, or re-confirm the deployed commit hash matches what was pushed.

- [ ] **Step 8: Write the session handoff**

Use the `sairn-session-handoff` skill to record this feature's landing. Re-derive the current `SAIRNLAW-SESSION-N-HANDOFF.md` number from the repo (don't assume — SESSION4 already exists from step 2). Note explicitly: the concurrency test result (which operation won, whichever it was), and that this closes the last disclosed money-correctness gap in the trust-disbursement feature — the two remaining open items (cross-client `trusttx_id` collision, still-unwired client-side reads) are unrelated and untouched by this plan.

---

## Self-Review Notes

- **Spec coverage:** the shared `law_client_balance()` helper, the edit to `law_check_and_insert_disbursement()`, and the new `law_check_and_void_deposit()` function (Task 1) match the spec's Architecture section, plus the disclosed plan-level refinement (double lookup around the lock) documented in Global Constraints. Routing (Deposit-void-only → new RPC, everything else unchanged) and the three new error codes (Task 2) match. The client rollback (Task 3) mirrors step 2's exact pattern as the spec specifies. The concurrency test (Task 4 Step 4) directly exercises the spec's stated edge case — the lock serializing a void against a disbursement for the same client, not just against another void.
- **Placeholder scan:** no TBD/TODO; every step shows real code matching the actual current `sql/sairnlaw_trust_disbursement_atomic_check.sql`/`api/sd-data.js`/`sairnlaw.html` content (re-read immediately before writing this plan — confirmed exact line numbers and content at every edit site) or a real runnable command with a stated expected result.
- **Type/name consistency:** `law_client_balance`'s signature is identical everywhere it's declared (Task 1) and called (Task 1's edited disbursement function, Task 1's new void function). `law_check_and_void_deposit`'s parameter names (`p_license_hash`, `p_trusttx_id`, `p_voided_reason`) match between the SQL definition (Task 1) and the RPC call body (Task 2). The three error codes (`VOID_WOULD_NEGATIVE_BALANCE`, `ALREADY_VOIDED`, `NOT_FOUND`) are spelled identically in the SQL `RAISE` messages (Task 1), the regexes/string checks that parse them (Task 2), the JSON error codes (Task 2), and the client-side check (Task 3) — except `NOT_FOUND`, which is deliberately not added to `sdnData()`'s structured-rejection list (Task 3), since `confirmVoid()` always sends a `trusttx_id` for a record it already has locally — a `NOT_FOUND` there would be a genuine server-state anomaly worth surfacing as a plain sync failure (existing `null`/toast path), not a "rejected" state to roll back differently.
