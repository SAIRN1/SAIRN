# SAIRNlaw Trust Disbursement Atomic Check (Step 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the cross-device over-disbursement race by making SAIRNlaw's trust-fund disbursement balance check real and atomic server-side, replacing the local-only check that can't see another device's concurrent write.

**Architecture:** One new idempotent SQL migration promotes `amount`/`type`/`status` to real columns on `law_trusttx` and adds a Postgres function (`law_check_and_insert_disbursement`) that takes a per-client advisory lock, re-sums the real balance, and atomically rejects-or-inserts. `api/sd-data.js`'s existing `law_trusttx` write block gains one branch: a new Disbursement (not a void) routes through that function via PostgREST's RPC endpoint instead of the plain upsert; everything else (Deposits, voids) keeps the unchanged plain upsert. `sairnlaw.html` gains real handling for a genuine server-side rejection: `sdnData()` returns a distinguishable structured result for this one known error code, and `saveTrustTransaction()` rolls its optimistic local write back out when that happens.

**Tech Stack:** Vanilla Node.js serverless function (`api/sd-data.js`, Vercel), Supabase/PostgREST (including its RPC endpoint for calling a Postgres function), plain SQL (Supabase SQL editor, no migration tool), vanilla JS client (`sairnlaw.html`).

## Global Constraints

- **Only `payload.type === 'Disbursement' && payload.status !== 'Voided'`** routes through the new RPC path. Everything else (Deposit, any void) keeps the exact plain-upsert shape from step 1 — do not add balance logic to those paths.
- **Balance is client-level** (`client_id`), never per-matter — matches `clientLedgerBalance()`'s existing behavior exactly. Do not scope the check by `matter_id`.
- **No FK/existence validation** between `law_clients`/`law_matters`/`law_trusttx` — unchanged from step 1, not introduced here.
- **Do not touch voiding-a-deposit** — that gap is explicitly deferred (logged in `SAIRN-BACKLOG.md`), not part of this plan.
- **`node --check api/sd-data.js` must show zero errors** before any commit that touches it.
- **Every SQL statement must be idempotent** and safe to re-run — this file may be re-run, and it runs against a database that already has step 1's `law_trusttx` table and rows in it (backfill existing rows, don't assume an empty table).
- **`sdnData()`'s return value stays `null` on every failure except the one new structured code.** Do not broaden the "rejected" branch to any `d.error.code` — only `'INSUFFICIENT_TRUST_BALANCE'` — every other existing caller's `if(syncResult)` truthy check must keep working exactly as today.
- **Plan clarification (spec ambiguity, resolved here):** the spec says the rejection message should show "via the existing `$('trust-err')` field... rather than the generic toast," but by the time a rejection response arrives the trust modal has already been closed optimistically (same pattern every other resource in this app uses). Reopening the modal would also reset its typed fields (`openTrustModal()` clears them), which is worse UX than the problem it solves. **Resolution: use the existing `toast()` function with the real server message and a longer duration (7000ms, vs. the existing 5000ms failure toast) instead of the modal's error field.** This achieves the spec's actual intent (show the real reason, not the generic "saved locally only" message) without inventing new modal-reopening behavior the spec never described. Task 3 implements this resolution, not the spec's literal `$('trust-err')` wording.

---

### Task 1: SQL migration — promote amount/type/status, add the atomic function

**Files:**
- Create: `sql/sairnlaw_trust_disbursement_atomic_check.sql`

**Interfaces:**
- Produces: three new columns on `public.law_trusttx` (`amount numeric`, `type text`, `status text`) and one new Postgres function `public.law_check_and_insert_disbursement(p_license_hash text, p_trusttx_id text, p_matter_id text, p_client_id text, p_amount numeric, p_method text, p_reference_number text, p_description text, p_tx_date text, p_created_at text) returns public.law_trusttx` — consumed by Task 2's `api/sd-data.js` code via PostgREST's `rpc/law_check_and_insert_disbursement` endpoint. No code in this repo imports this file — it's handed to a human to run in Supabase's SQL editor.

- [ ] **Step 1: Write the migration**

Create `sql/sairnlaw_trust_disbursement_atomic_check.sql`:

```sql
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
  select coalesce(sum(case when type = 'Deposit' then amount else -amount end), 0)
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

- [ ] **Step 2: Hand off for manual execution**

This SQL is NOT run by this task. Note in the task report that a human must run `sql/sairnlaw_trust_disbursement_atomic_check.sql` in Supabase's SQL editor before Task 4's live verification can pass — Tasks 2-3's code can still be written and committed without it having run yet.

- [ ] **Step 3: Commit**

```bash
git add sql/sairnlaw_trust_disbursement_atomic_check.sql
git commit -m "docs: SQL -- SAIRNlaw trust disbursement atomic check-and-write function"
```

---

### Task 2: `api/sd-data.js` — route Disbursements through the atomic function

**Files:**
- Modify: `api/sd-data.js` (the `law_trusttx` write block, currently lines 1973-1985)

**Interfaces:**
- Consumes: `rest()`, `headers`, `licHash`, `nowISO()`, `upstream()` (already defined in the enclosing closure). Calls the new `law_check_and_insert_disbursement` RPC from Task 1 via `POST rest('rpc/law_check_and_insert_disbursement')`.
- Produces: on a genuine rejection, `409 {error:{code:'INSUFFICIENT_TRUST_BALANCE', message:'Disbursement of $<amount> exceeds this client\'s real trust balance of $<balance>', real_balance:<number>}}` — consumed by Task 3's `sairnlaw.html` change. On success (either path), unchanged `{ok:true, data:{...}}` shape.

- [ ] **Step 1: Replace the `law_trusttx` write block**

Find (`api/sd-data.js:1973-1985`):

```js
    if (resource === 'law_trusttx' && action === 'write') {
      if (!payload || !payload.id || !payload.matter_id || !payload.client_id) { res.status(400).json({ error: { message: 'law_trusttx payload.id, payload.matter_id, and payload.client_id are required' } }); return; }
      const r = await fetch(rest('law_trusttx?on_conflict=license_hash,trusttx_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnlaw', trusttx_id: String(payload.id), matter_id: String(payload.matter_id), client_id: String(payload.client_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
```

Replace with:

```js
    if (resource === 'law_trusttx' && action === 'write') {
      if (!payload || !payload.id || !payload.matter_id || !payload.client_id) { res.status(400).json({ error: { message: 'law_trusttx payload.id, payload.matter_id, and payload.client_id are required' } }); return; }
      // Atomic disbursement check-and-write (2026-08-16, step 2). A NEW
      // Disbursement (not a void -- a void write always carries
      // payload.status==='Voided', which stays on the plain upsert below)
      // routes through law_check_and_insert_disbursement() instead of a
      // plain upsert. That Postgres function takes an advisory lock scoped
      // to (license_hash, client_id), re-sums the client's real balance
      // server-side, and rejects atomically if the disbursement would go
      // negative -- closing the cross-device race saveTrustTransaction()'s
      // own local-only check (sairnlaw.html:2048-2050) cannot close on its
      // own. See docs/superpowers/specs/2026-08-16-sairnlaw-trust-disbursement-atomic-check-design.md.
      if (payload.type === 'Disbursement' && payload.status !== 'Voided') {
        if (payload.amount === undefined || payload.amount === null || Number(payload.amount) <= 0) { res.status(400).json({ error: { message: 'law_trusttx payload.amount is required and must be greater than 0 for a Disbursement' } }); return; }
        const r = await fetch(rest('rpc/law_check_and_insert_disbursement'), {
          method: 'POST',
          headers,
          body: JSON.stringify({
            p_license_hash: licHash, p_trusttx_id: String(payload.id), p_matter_id: String(payload.matter_id),
            p_client_id: String(payload.client_id), p_amount: Number(payload.amount), p_method: payload.method || null,
            p_reference_number: payload.reference_number || null, p_description: payload.description || null,
            p_tx_date: payload.date || null, p_created_at: payload.created_at || nowISO()
          })
        });
        if (r.status === 404) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql and sql/sairnlaw_trust_disbursement_atomic_check.sql in Supabase first.' } }); return; }
        if (r.status === 400) {
          const bodyText = await r.text();
          let bodyJson = null; try { bodyJson = JSON.parse(bodyText); } catch (e) {}
          const msg = (bodyJson && bodyJson.message) || bodyText || '';
          if (/relation .* does not exist|function .* does not exist/i.test(msg)) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql and sql/sairnlaw_trust_disbursement_atomic_check.sql in Supabase first.' } }); return; }
          const balMatch = /INSUFFICIENT_TRUST_BALANCE: disbursement ([\d.]+) exceeds balance ([\d.]+)/.exec(msg);
          if (balMatch) {
            const reqAmount = Number(balMatch[1]), realBalance = Number(balMatch[2]);
            res.status(409).json({ error: { code: 'INSUFFICIENT_TRUST_BALANCE', message: 'Disbursement of $' + reqAmount.toFixed(2) + ' exceeds this client\'s real trust balance of $' + realBalance.toFixed(2), real_balance: realBalance } });
            return;
          }
          console.error('law_check_and_insert_disbursement error (status 400):', msg);
          res.status(502).json({ error: { message: 'Data store error — try again', detail: msg } });
          return;
        }
        if (!r.ok) { const rows = await r.json().catch(() => null); return upstream(res, rows); }
        const rpcResult = await r.json();
        const row = Array.isArray(rpcResult) ? rpcResult[0] : rpcResult;
        res.status(200).json({ ok: true, data: row || payload });
        return;
      }
      const r = await fetch(rest('law_trusttx?on_conflict=license_hash,trusttx_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnlaw', trusttx_id: String(payload.id), matter_id: String(payload.matter_id), client_id: String(payload.client_id), amount: (payload.amount !== undefined && payload.amount !== null) ? Number(payload.amount) : null, type: payload.type || null, status: payload.status || 'Posted', data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
```

- [ ] **Step 2: Verify no syntax errors**

Run: `node --check api/sd-data.js`
Expected: no output (clean exit).

- [ ] **Step 3: Commit**

```bash
git add api/sd-data.js
git commit -m "feat: SAIRNlaw -- route new Disbursement writes through the atomic balance check"
```

---

### Task 3: `sairnlaw.html` — client-side rollback on a real rejection

**Files:**
- Modify: `sairnlaw.html:1056-1069` (`sdnData()`)
- Modify: `sairnlaw.html:2042-2059` (`saveTrustTransaction()`)

**Interfaces:**
- Consumes: Task 2's `409 {code:'INSUFFICIENT_TRUST_BALANCE', message, real_balance}` response shape.
- Produces: `sdnData()` returns `{rejected:true, code:'INSUFFICIENT_TRUST_BALANCE', message:<string>}` for that one specific server error code only — every other failure (network, NOT_PROVISIONED, validation 400, any other code) still returns plain `null`, unchanged. `saveTrustTransaction()` checks `syncResult && syncResult.rejected` and rolls the optimistic local write back out when true.

- [ ] **Step 1: Add the structured-rejection branch to `sdnData()`**

Find (`sairnlaw.html:1056-1069`):

```js
function sdnData(action,resource,payload){
  var lic=lawLicenseKey();
  if(!lic)return Promise.resolve(null);
  return fetch(DATA_API,{
    method:'POST',
    headers:{'Content-Type':'application/json','Authorization':'Bearer '+lic},
    body:JSON.stringify({action:action,resource:resource,app_id:APP_ID,payload:payload||{}})
  }).then(function(r){
    return r.json().then(function(d){
      if(!r.ok||!d||!d.ok){console.warn('sdnData '+resource+' failed ('+r.status+'):',(d&&d.error&&(d.error.code||d.error.message))||'unknown');return null;}
      return d.data;
    });
  }).catch(function(e){console.warn('sdnData network error:',e.message);return null;});
}
```

Replace with:

```js
function sdnData(action,resource,payload){
  var lic=lawLicenseKey();
  if(!lic)return Promise.resolve(null);
  return fetch(DATA_API,{
    method:'POST',
    headers:{'Content-Type':'application/json','Authorization':'Bearer '+lic},
    body:JSON.stringify({action:action,resource:resource,app_id:APP_ID,payload:payload||{}})
  }).then(function(r){
    return r.json().then(function(d){
      if(!r.ok||!d||!d.ok){
        // Structured rejection (2026-08-16, trust disbursement atomic
        // check): a genuine server-side rejection carries a real
        // error.code the caller may need to react to differently from an
        // ordinary sync failure (e.g. rolling back an optimistic local
        // write). Scoped to this ONE known code -- every other failure
        // (network error, NOT_PROVISIONED, a plain validation 400, etc.)
        // still returns plain null, unchanged, so no existing caller's
        // `if(syncResult)` truthy check breaks.
        if(d&&d.error&&d.error.code==='INSUFFICIENT_TRUST_BALANCE'){
          return {rejected:true,code:d.error.code,message:d.error.message};
        }
        console.warn('sdnData '+resource+' failed ('+r.status+'):',(d&&d.error&&(d.error.code||d.error.message))||'unknown');
        return null;
      }
      return d.data;
    });
  }).catch(function(e){console.warn('sdnData network error:',e.message);return null;});
}
```

- [ ] **Step 2: Add rollback handling to `saveTrustTransaction()`**

Find (`sairnlaw.html:2042-2059`):

```js
async function saveTrustTransaction(){
  var matterId=$('trmatter').value,amount=Number($('tramount').value)||0;
  if(!matterId){$('trust-err').textContent='Select a matter';return;}
  if(amount<=0){$('trust-err').textContent='Amount must be greater than 0';return;}
  var m=matters().find(function(x){return x.id===matterId;});
  var type=$('trtype').value;
  if(type==='Disbursement'){
    var currentBal=clientLedgerBalance(m.client_id,trustTransactions());
    if(amount>currentBal){$('trust-err').textContent='Disbursement of '+fmt(amount)+' exceeds this client\'s trust balance of '+fmt(currentBal)+' -- trust funds can never go negative';return;}
  }
  var rec={id:newId('TR'),matter_id:matterId,client_id:m?m.client_id:'',type:type,amount:amount,date:$('trdate').value||lawLocalToday(),
    method:$('trmethod').value,reference_number:$('trref').value.trim(),description:$('trdesc').value.trim(),
    status:'Posted',voided_reason:'',voided_at:'',created_at:lawLocalToday()};
  var list=trustTransactions();list.push(rec);st('law_trusttx',list);
  closeTrustModal();rTrust();rDash();
  var syncResult=await sdnData('write','law_trusttx',rec);
  toast(syncResult?'Transaction recorded':'Saved on this device only -- server sync not yet enabled for this app',syncResult?3000:5000);
}
```

Replace with:

```js
async function saveTrustTransaction(){
  var matterId=$('trmatter').value,amount=Number($('tramount').value)||0;
  if(!matterId){$('trust-err').textContent='Select a matter';return;}
  if(amount<=0){$('trust-err').textContent='Amount must be greater than 0';return;}
  var m=matters().find(function(x){return x.id===matterId;});
  var type=$('trtype').value;
  if(type==='Disbursement'){
    var currentBal=clientLedgerBalance(m.client_id,trustTransactions());
    if(amount>currentBal){$('trust-err').textContent='Disbursement of '+fmt(amount)+' exceeds this client\'s trust balance of '+fmt(currentBal)+' -- trust funds can never go negative';return;}
  }
  var rec={id:newId('TR'),matter_id:matterId,client_id:m?m.client_id:'',type:type,amount:amount,date:$('trdate').value||lawLocalToday(),
    method:$('trmethod').value,reference_number:$('trref').value.trim(),description:$('trdesc').value.trim(),
    status:'Posted',voided_reason:'',voided_at:'',created_at:lawLocalToday()};
  var list=trustTransactions();list.push(rec);st('law_trusttx',list);
  closeTrustModal();rTrust();rDash();
  var syncResult=await sdnData('write','law_trusttx',rec);
  // Real server-side rejection (2026-08-16, atomic disbursement check):
  // the optimistic local write above never actually happened server-side,
  // so roll it back rather than leaving a phantom disbursement in local
  // storage that would keep displaying as real (cut sheets, future local
  // balance checks) until someone notices. A plain sync failure (network
  // error, NOT_PROVISIONED, etc.) is unchanged below -- that still just
  // means "not yet synced," a weaker claim than "the server rejected this."
  if(syncResult&&syncResult.rejected){
    var afterList=trustTransactions().filter(function(t){return t.id!==rec.id;});
    st('law_trusttx',afterList);
    rTrust();rDash();
    toast(syncResult.message||'Disbursement rejected -- exceeds this client\'s real trust balance',7000);
    return;
  }
  toast(syncResult?'Transaction recorded':'Saved on this device only -- server sync not yet enabled for this app',syncResult?3000:5000);
}
```

- [ ] **Step 3: Extract and syntax-check the modified script block**

This project's SYNTAX RULE (`CLAUDE.md`) requires `node --check` on every touched script block before any commit — never a bulk find-replace, never trust a partial check. Use whatever HTML-script-block extraction this project already uses (per `sairn-guardian-v2`'s Check 0a — HTML-parser-based extraction, not a `grep -c '<script'` count) to pull the specific `<script>` block containing `sdnData`/`saveTrustTransaction` and run `node --check` on it directly.
Expected: no output (clean exit) for that block.

- [ ] **Step 4: Commit**

```bash
git add sairnlaw.html
git commit -m "feat: SAIRNlaw -- roll back optimistic local write on a real disbursement rejection"
```

---

### Task 4: Full verification sweep, concurrency test, live-verify, and push

**Files:** none (verification only)

- [ ] **Step 1: Full local syntax sweep**

Run: `node --check api/sd-data.js` (clean). Re-run the same HTML-script-block check from Task 3 Step 3 against the full current `sairnlaw.html` (zero failures across all blocks, not just the one touched).

- [ ] **Step 2: Confirm the migration has been run**

Ask whoever is present to confirm `sql/sairnlaw_trust_disbursement_atomic_check.sql` has been run in Supabase's SQL editor (per Task 1's hand-off note) — required before this task's live checks can pass. If it hasn't been run yet, stop here and report that as the blocker rather than proceeding to push with an unverified server layer.

- [ ] **Step 3: Run the full Guardian review before commit/push**

Invoke the `sairn-guardian-v2` skill's full Check 0 + numbered checks against the diff, per CLAUDE.md's standing Push Protocol.

- [ ] **Step 4: Live concurrency test — the actual bug this plan fixes**

Using a real SAIRNlaw license key (e.g. `LAW-TEST-2026`), set up one client with exactly enough balance for one of two simultaneous disbursements, then fire both at once from the same shell:

```bash
# 1. Create a fresh client and matter, deposit exactly $500
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_clients","payload":{"id":"CL-RACE-1","name":"Race Test Client"}}'
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_matters","payload":{"id":"MT-RACE-1","client_id":"CL-RACE-1","matter_name":"Race Test Matter"}}'
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-RACE-DEP","matter_id":"MT-RACE-1","client_id":"CL-RACE-1","type":"Deposit","amount":500}}'

# 2. Fire two $500 disbursements for the SAME client at the same time --
#    only one should succeed. Before this fix, both would have succeeded
#    (the exact bug this plan closes).
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-RACE-A","matter_id":"MT-RACE-1","client_id":"CL-RACE-1","type":"Disbursement","amount":500}}' > /tmp/race_a.json &
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-RACE-B","matter_id":"MT-RACE-1","client_id":"CL-RACE-1","type":"Disbursement","amount":500}}' > /tmp/race_b.json &
wait
cat /tmp/race_a.json; echo; cat /tmp/race_b.json; echo
```

Expected: exactly one of the two responses is `{"ok":true,"data":{...}}` and the other is `{"error":{"code":"INSUFFICIENT_TRUST_BALANCE",...}}` with a `409`. Both succeeding is the bug; both failing is also wrong (one should have room). Confirm via a `law_trusttx` read afterward that only one `TR-RACE-A`/`TR-RACE-B` row actually landed.

- [ ] **Step 5: Live-verify the remaining cases**

```bash
# A Deposit still goes through the unchanged plain-upsert path
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-RACE-DEP2","matter_id":"MT-RACE-1","client_id":"CL-RACE-1","type":"Deposit","amount":100}}'
# Expected: {"ok":true,"data":{...}}

# A single-caller over-balance disbursement is rejected with the real balance
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer LAW-TEST-2026" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-RACE-OVER","matter_id":"MT-RACE-1","client_id":"CL-RACE-1","type":"Disbursement","amount":999999}}'
# Expected: 409 INSUFFICIENT_TRUST_BALANCE with the real current balance in the message
```

Also confirm in the live app (`sairn.vercel.app/sairnlaw`): attempt a disbursement through the actual UI that will genuinely be rejected (a client whose real server balance is lower than what's typed), and confirm the transaction disappears from the Trust panel after the rejection toast, rather than sitting there as a phantom entry.

- [ ] **Step 6: Push**

```bash
git push origin main
```

- [ ] **Step 7: Live-verify against production (post-push)**

Repeat Step 4/5's checks against `sairn.vercel.app` directly if Step 4/5 were run pre-push against a preview URL, or re-confirm the deployed commit hash matches what was pushed (normalize line endings before comparing — CRLF/LF, not content, was the cause of a known false-positive deploy-mismatch class in prior sessions).

- [ ] **Step 8: Write the session handoff**

Use the `sairn-session-handoff` skill to record this feature's landing. Re-derive the current `SAIRNLAW-SESSION-N-HANDOFF.md` number from the repo (don't assume it's still 4 — SESSION3 already exists from step 1). Note explicitly: the concurrency test result (which disbursement won, that exactly one did), that voiding a deposit is still an open, disclosed gap (`SAIRN-BACKLOG.md`), and that reads for `law_clients`/`law_matters`/`law_trusttx` are still not wired client-side (carried forward from step 1's own disclosed gap, unchanged by this plan).

---

## Self-Review Notes

- **Spec coverage:** schema promotion + backfill + constraints + the atomic function (Task 1) match the spec's Architecture section exactly. Routing (Disbursement-not-void → RPC, everything else → unchanged plain upsert) and the 409 error contract (Task 2) match. The client rollback behavior (Task 3) implements the spec's intent with one disclosed, reasoned deviation from its literal wording (Global Constraints' "Plan clarification" — toast instead of reopening the closed modal). The concurrency test (Task 4 Step 4) directly exercises the spec's primary edge case ("two concurrent disbursements for the same client"). Voiding-a-deposit and client-side read-wiring are both explicitly out of scope per the spec and not touched by any task.
- **Placeholder scan:** no TBD/TODO; every step shows real code matching the actual current `api/sd-data.js`/`sairnlaw.html` content (re-read immediately before writing this plan — confirmed exact line numbers and content at both edit sites) or a real runnable command with a stated expected result.
- **Type/name consistency:** `law_check_and_insert_disbursement`'s parameter names (`p_license_hash`, `p_trusttx_id`, `p_matter_id`, `p_client_id`, `p_amount`, `p_method`, `p_reference_number`, `p_description`, `p_tx_date`, `p_created_at`) are spelled identically between the SQL function definition (Task 1) and the RPC call body (Task 2). The `{rejected:true, code, message}` shape is spelled identically between `sdnData()`'s producer (Task 3 Step 1) and `saveTrustTransaction()`'s consumer (Task 3 Step 2). The `INSUFFICIENT_TRUST_BALANCE` error code string appears identically in the SQL RAISE message prefix (Task 1), the regex that parses it (Task 2), the JSON error code (Task 2), and the client-side check (Task 3).
