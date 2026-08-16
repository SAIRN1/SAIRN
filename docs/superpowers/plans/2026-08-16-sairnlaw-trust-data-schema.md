# SAIRNlaw Trust Data Schema (Step 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `law_clients`, `law_matters`, and `law_trusttx` real, durable, server-synced resources — replacing today's localStorage-only behavior — without yet adding the atomic disbursement check (that's a separate, later plan/spec).

**Architecture:** One new idempotent SQL migration (`sql/sairnlaw_data_schema.sql`) creating three tables, each following the platform's existing `license_hash`-scoped jsonb-blob-per-row shape (same as `grd_properties`/`grd_jobs`). Six new route blocks in `api/sd-data.js` (read+write × 3), inserted after the existing `dnt_appointments` block, following the exact `grd_jobs` shape: Bearer-license-key auth only (no session-token check — see Global Constraints), upsert via `on_conflict`, graceful degrade to `provisioned:false` on a missing table for reads, `503 NOT_PROVISIONED` for writes.

**Tech Stack:** Vanilla Node.js serverless function (`api/sd-data.js`, Vercel), Supabase/PostgREST, plain SQL (Supabase SQL editor, no migration tool).

## Global Constraints

- **Zero role gating beyond the existing Bearer license key check.** All three `LAW_ROLES` (`owner`/`attorney`/`paralegal`) may write/void every resource in this plan — matches current unrestricted client behavior. Do not add a `verifySessionToken`/role check to any block in this plan.
- **No session-token check at all.** `sairnlaw.html`'s `sdnData()` never sends `X-SD-Auth`; requiring a session would 401 every real call. Auth = Bearer license key only, exactly like `grd_jobs`/`dnt_appointments`.
- **`client_id`/`matter_id` are trusted as sent by the client**, not derived or validated against another table. No FK/existence check between `law_clients` → `law_matters` → `law_trusttx` in this plan.
- **64KB payload cap** is already uniform and automatic (`MAX_PAYLOAD_BYTES`, enforced before any resource-specific code runs) — no new size-check code needed.
- **`node --check api/sd-data.js` must show zero errors** before any commit that touches it (project standing rule).
- **Every SQL statement must be idempotent** (`create table if not exists`, `drop policy if exists` before `create policy`) — this file may be re-run.
- Do not touch the other 16 unwired `law_*` client resources, and do not build the atomic balance-check endpoint — both are explicitly out of scope for this plan (spec §"Explicitly out of scope").

---

### Task 1: SQL schema — `law_clients`, `law_matters`, `law_trusttx`

**Files:**
- Create: `sql/sairnlaw_data_schema.sql`

**Interfaces:**
- Produces: three tables (`public.law_clients`, `public.law_matters`, `public.law_trusttx`) that Task 2's `api/sd-data.js` code queries via PostgREST (`license_hash`, `client_id`/`matter_id`/`trusttx_id`, `data` jsonb, `updated_at`). No code in this repo imports this file — it's handed to a human to run in Supabase's SQL editor.

- [ ] **Step 1: Write the migration**

Create `sql/sairnlaw_data_schema.sql`:

```sql
-- sql/sairnlaw_data_schema.sql
-- SAIRNlaw application data — Supabase schema (step 1 of trust disbursement
-- server-sync; see docs/superpowers/specs/2026-08-14-sairnlaw-trust-data-schema-design.md)
--
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- law_clients/law_matters/law_trusttx resources will work. Every statement
-- is idempotent — safe to re-run. Until this runs, sairnlaw.html falls back
-- to its existing localStorage-only behavior (saveTrustTransaction() etc.
-- already toast "Saved on this device only -- server sync not yet enabled
-- for this app" on a failed sync, the same pattern render_usage/
-- shared_knowledge use for "migration not run yet").
--
-- KEYING: license_hash = sha256(license_key), matching every other app's
-- tables. app_id is stamped 'sairnlaw' explicitly on every write.
--
-- client_id (on law_matters) and matter_id/client_id (on law_trusttx) are
-- real columns, not just fields inside the jsonb blob -- added now so a
-- later balance-check feature (step 2, not built in this migration) can
-- query trust transactions by client without a second migration + backfill.
-- Mirrors the existing grd_jobs.property_id precedent. These are NOT
-- foreign keys and are NOT validated against law_clients/law_matters at
-- write time (matches this platform's existing precedent of trusting
-- client-supplied linking ids) -- deliberately deferred, not an oversight.
--
-- SECURITY MODEL: service-role only, RLS enabled with no anon policy --
-- same as every table in sql/stonedesk_data_schema.sql /
-- sql/sairngrounds_data_schema.sql. api/sd-data.js is the only door in.
--
-- SIZE CAP: 64KB per row's data jsonb, matching api/sd-data.js's uniform
-- MAX_PAYLOAD_BYTES.

create extension if not exists pgcrypto;

create table if not exists public.law_clients (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnlaw',
  client_id    text not null,                        -- client-generated id
  data         jsonb not null default '{}'::jsonb,    -- name, type, phone, email, address, notes
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, client_id),
  constraint lawclients_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_lawclients_license on public.law_clients(license_hash);

create table if not exists public.law_matters (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnlaw',
  matter_id    text not null,                        -- client-generated id
  client_id    text not null,
  data         jsonb not null default '{}'::jsonb,    -- matter_number, matter_name, practice_area, status, ...
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, matter_id),
  constraint lawmatters_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_lawmatters_license on public.law_matters(license_hash);
create index if not exists idx_lawmatters_client on public.law_matters(client_id);

create table if not exists public.law_trusttx (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnlaw',
  trusttx_id   text not null,                        -- client-generated id
  matter_id    text not null,
  client_id    text not null,
  data         jsonb not null default '{}'::jsonb,    -- type, amount, date, method, reference_number, description, status, ...
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, trusttx_id),
  constraint lawtrusttx_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_lawtrusttx_license on public.law_trusttx(license_hash);
create index if not exists idx_lawtrusttx_client on public.law_trusttx(client_id);

-- ── RLS: service-role only (mirror sairngrounds_data_schema.sql) ─────────
alter table public.law_clients enable row level security;
alter table public.law_matters enable row level security;
alter table public.law_trusttx enable row level security;

drop policy if exists "svc only law_clients" on public.law_clients;
drop policy if exists "svc only law_matters" on public.law_matters;
drop policy if exists "svc only law_trusttx" on public.law_trusttx;

create policy "svc only law_clients" on public.law_clients
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only law_matters" on public.law_matters
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
create policy "svc only law_trusttx" on public.law_trusttx
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update, delete on public.law_clients  to service_role;
grant select, insert, update, delete on public.law_matters  to service_role;
grant select, insert, update, delete on public.law_trusttx  to service_role;
```

- [ ] **Step 2: Hand off for manual execution**

This SQL is NOT run by this task. Note in the task report that a human must run `sql/sairnlaw_data_schema.sql` in Supabase's SQL editor before Task 6's live curl verification can pass — Tasks 2-5's code can still be written and committed without it having run yet (writes will correctly 503 `NOT_PROVISIONED` until then).

- [ ] **Step 3: Commit**

```bash
git add sql/sairnlaw_data_schema.sql
git commit -m "docs: SQL -- SAIRNlaw data schema (law_clients/law_matters/law_trusttx)"
```

---

### Task 2: Register the three resource names in `api/sd-data.js`

**Files:**
- Modify: `api/sd-data.js:91` (RESOURCES map) and `api/sd-data.js:179` (400 error message's resource list)

**Interfaces:**
- Consumes: nothing new.
- Produces: `RESOURCES.law_clients`, `RESOURCES.law_matters`, `RESOURCES.law_trusttx` all `true` — Tasks 3/4/5's route blocks are unreachable (fall through to the generic 400) without this.

- [ ] **Step 1: Add the three resource keys to the allowlist**

Find (`api/sd-data.js:80-92`):

```js
  // SAIRNdental (2026-08-10) -- see sql/sairndental_data_schema.sql. All 12 prefixed dnt_.
  dnt_patients: true, dnt_providers: true, dnt_operatories: true, dnt_provider_hours: true,
  dnt_procedure_types: true, dnt_coverage_rules: true, dnt_appointments: true, dnt_charges: true,
  dnt_payments: true, dnt_denial: true, dnt_ar: true, dnt_revenue: true,
  // SAIRNdental availability + booking (2026-08-10) -- see
  // sql/sairndental_availability_booking_schema.sql. dnt_appointments was
  // already added above but gets its OWN dedicated read/write handler
  // below (not the generic DNT_RESOURCES block) because it now has real
  // promoted columns the EXCLUDE constraints check against -- still
  // listed here since this map only gates "is this a known resource
  // string," not which code path handles it.
  dnt_settings: true, dnt_referrals: true, dnt_complaints: true
};
```

Replace with:

```js
  // SAIRNdental (2026-08-10) -- see sql/sairndental_data_schema.sql. All 12 prefixed dnt_.
  dnt_patients: true, dnt_providers: true, dnt_operatories: true, dnt_provider_hours: true,
  dnt_procedure_types: true, dnt_coverage_rules: true, dnt_appointments: true, dnt_charges: true,
  dnt_payments: true, dnt_denial: true, dnt_ar: true, dnt_revenue: true,
  // SAIRNdental availability + booking (2026-08-10) -- see
  // sql/sairndental_availability_booking_schema.sql. dnt_appointments was
  // already added above but gets its OWN dedicated read/write handler
  // below (not the generic DNT_RESOURCES block) because it now has real
  // promoted columns the EXCLUDE constraints check against -- still
  // listed here since this map only gates "is this a known resource
  // string," not which code path handles it.
  dnt_settings: true, dnt_referrals: true, dnt_complaints: true,
  // SAIRNlaw trust disbursement server-sync, step 1 (2026-08-16) -- see
  // sql/sairnlaw_data_schema.sql and
  // docs/superpowers/specs/2026-08-14-sairnlaw-trust-data-schema-design.md.
  // No role gating on these three -- all LAW_ROLES (owner/attorney/
  // paralegal) may write, matching sairnlaw.html's current unrestricted
  // client-side behavior. Auth is Bearer license key only, same as
  // grd_jobs -- sdnData() never sends a session token to this endpoint.
  law_clients: true, law_matters: true, law_trusttx: true
};
```

- [ ] **Step 2: Add the three names to the 400 error message**

Find (`api/sd-data.js:179`, end of the resource list string, immediately before the closing `'` and `}`):

```
dnt_settings, dnt_referrals, dnt_complaints'
```

Replace with:

```
dnt_settings, dnt_referrals, dnt_complaints, law_clients, law_matters, law_trusttx'
```

- [ ] **Step 3: Verify no syntax errors**

Run: `node --check api/sd-data.js`
Expected: no output (clean exit).

- [ ] **Step 4: Commit**

```bash
git add api/sd-data.js
git commit -m "feat: SAIRNlaw -- register law_clients/law_matters/law_trusttx resource names"
```

---

### Task 3: `law_clients` read/write routes

**Files:**
- Modify: `api/sd-data.js` (new block inserted immediately before the `// Should be unreachable given the guards above.` line, currently the line right after the `dnt_appointments` write block's closing `}`)

**Interfaces:**
- Consumes: `rest()`, `enc()`, `headers`, `licHash`, `nowISO()`, `upstream()` (all already defined in the enclosing `module.exports` closure — same as every existing block).
- Produces: `resource:'law_clients'` read (returns `{ok:true, data:[...], provisioned:true|false}`) and write (upsert, `{ok:true, data:{...}}` or `503 NOT_PROVISIONED`) — consumed by `sairnlaw.html`'s existing `sdnData('read'|'write','law_clients',...)` calls (`clients()`/`saveClient()`, already in the client, no client change needed).

- [ ] **Step 1: Add the `law_clients` block**

Find (`api/sd-data.js`, end of file inside `module.exports`):

```js
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // Should be unreachable given the guards above.
    res.status(400).json({ error: { message: 'Unsupported action/resource combination' } });
```

Replace with:

```js
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // ── SAIRNlaw trust disbursement server-sync, step 1 (2026-08-16) ──────
    // See sql/sairnlaw_data_schema.sql and
    // docs/superpowers/specs/2026-08-14-sairnlaw-trust-data-schema-design.md.
    // No verifySessionToken/role check on any of these three resources --
    // see that spec's "Correction (2026-08-16)" section for why (sdnData()
    // never sends a session token to this endpoint; auth is the Bearer
    // license key alone, same as grd_jobs).
    if (resource === 'law_clients' && action === 'read') {
      const r = await fetch(rest('law_clients?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'law_clients' && action === 'write') {
      if (!payload || !payload.id) { res.status(400).json({ error: { message: 'law_clients payload.id is required' } }); return; }
      const r = await fetch(rest('law_clients?on_conflict=license_hash,client_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnlaw', client_id: String(payload.id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // Should be unreachable given the guards above.
    res.status(400).json({ error: { message: 'Unsupported action/resource combination' } });
```

- [ ] **Step 2: Verify no syntax errors**

Run: `node --check api/sd-data.js`
Expected: no output (clean exit).

- [ ] **Step 3: Commit**

```bash
git add api/sd-data.js
git commit -m "feat: SAIRNlaw -- law_clients read/write routes in api/sd-data.js"
```

---

### Task 4: `law_matters` read/write routes

**Files:**
- Modify: `api/sd-data.js` (new block inserted immediately after Task 3's `law_clients` write block's closing `}`, before `// Should be unreachable given the guards above.`)

**Interfaces:**
- Consumes: same closure variables as Task 3.
- Produces: `resource:'law_matters'` read/write — consumed by `sairnlaw.html`'s existing `matters()`/`saveMatter()` (no client change needed). Row payloads carry `client_id` (already present on every `saveMatter()` record, per `sairnlaw.html:1798`).

- [ ] **Step 1: Add the `law_matters` block**

Find (`api/sd-data.js`, immediately after Task 3's new `law_clients` write block):

```js
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // Should be unreachable given the guards above.
    res.status(400).json({ error: { message: 'Unsupported action/resource combination' } });
```

Replace with:

```js
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'law_matters' && action === 'read') {
      const r = await fetch(rest('law_matters?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'law_matters' && action === 'write') {
      if (!payload || !payload.id || !payload.client_id) { res.status(400).json({ error: { message: 'law_matters payload.id and payload.client_id are required' } }); return; }
      const r = await fetch(rest('law_matters?on_conflict=license_hash,matter_id'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnlaw', matter_id: String(payload.id), client_id: String(payload.client_id), data: payload, updated_at: nowISO() })
      });
      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlaw data tables are not set up yet — run sql/sairnlaw_data_schema.sql in Supabase first.' } }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // Should be unreachable given the guards above.
    res.status(400).json({ error: { message: 'Unsupported action/resource combination' } });
```

- [ ] **Step 2: Verify no syntax errors**

Run: `node --check api/sd-data.js`
Expected: no output (clean exit).

- [ ] **Step 3: Commit**

```bash
git add api/sd-data.js
git commit -m "feat: SAIRNlaw -- law_matters read/write routes in api/sd-data.js"
```

---

### Task 5: `law_trusttx` read/write routes

**Files:**
- Modify: `api/sd-data.js` (new block inserted immediately after Task 4's `law_matters` write block's closing `}`, before `// Should be unreachable given the guards above.`)

**Interfaces:**
- Consumes: same closure variables as Task 3/4.
- Produces: `resource:'law_trusttx'` read/write — consumed by `sairnlaw.html`'s existing `trustTransactions()`/`saveTrustTransaction()`/`confirmVoid()` (`sairnlaw.html:2042`/`2069`, no client change needed — `saveTrustTransaction()` already calls `sdnData('write','law_trusttx',rec)` with `rec.id`/`rec.matter_id`/`rec.client_id` all present, and `confirmVoid()` sends the same mutated record through the same call).

- [ ] **Step 1: Add the `law_trusttx` block**

Find (`api/sd-data.js`, immediately after Task 4's new `law_matters` write block):

```js
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }

    // Should be unreachable given the guards above.
    res.status(400).json({ error: { message: 'Unsupported action/resource combination' } });
```

Replace with:

```js
      res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
      return;
    }
    if (resource === 'law_trusttx' && action === 'read') {
      const r = await fetch(rest('law_trusttx?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
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

    // Should be unreachable given the guards above.
    res.status(400).json({ error: { message: 'Unsupported action/resource combination' } });
```

- [ ] **Step 2: Verify no syntax errors**

Run: `node --check api/sd-data.js`
Expected: no output (clean exit).

- [ ] **Step 3: Commit**

```bash
git add api/sd-data.js
git commit -m "feat: SAIRNlaw -- law_trusttx read/write routes in api/sd-data.js"
```

---

### Task 6: Full verification sweep, live-verify, and push

**Files:** none (verification only)

- [ ] **Step 1: Full local syntax sweep**

Run: `node --check api/sd-data.js`
Expected: no output (clean exit). No `sairnlaw.html` change was made in this plan, so no HTML-script-block check is needed for it.

- [ ] **Step 2: Confirm the migration has been run**

Ask whoever is present to confirm `sql/sairnlaw_data_schema.sql` has been run in Supabase's SQL editor (per Task 1's hand-off note) — required before this task's live curl checks can pass. If it hasn't been run yet, stop here and report that as the blocker rather than proceeding to push with an unverified server layer.

- [ ] **Step 3: Run the full Guardian review before commit/push**

Invoke the `sairn-guardian-v2` skill's full Check 0 + numbered checks against the diff, per CLAUDE.md's standing Push Protocol.

- [ ] **Step 4: Live curl verification against production**

Real DB-backed, not simulated — requires Step 2's migration to actually be live. Using a real SAIRNlaw license key:

```bash
# 1. law_clients write, then read it back
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer <LICENSE_KEY>" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_clients","payload":{"id":"CL-TEST-1","name":"Test Client"}}'
# Expected: {"ok":true,"data":{"id":"CL-TEST-1","name":"Test Client"}}

curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer <LICENSE_KEY>" -H "Content-Type: application/json" \
  -d '{"action":"read","resource":"law_clients"}'
# Expected: {"ok":true,"data":[{"id":"CL-TEST-1",...}],"provisioned":true}

# 2. law_matters write referencing that client
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer <LICENSE_KEY>" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_matters","payload":{"id":"MT-TEST-1","client_id":"CL-TEST-1","matter_name":"Test Matter"}}'
# Expected: {"ok":true,"data":{"id":"MT-TEST-1","client_id":"CL-TEST-1",...}}

# 3. law_trusttx write referencing that matter/client
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer <LICENSE_KEY>" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-TEST-1","matter_id":"MT-TEST-1","client_id":"CL-TEST-1","type":"Deposit","amount":500}}'
# Expected: {"ok":true,"data":{"id":"TR-TEST-1",...}}

# 4. Missing required field is rejected
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer <LICENSE_KEY>" -H "Content-Type: application/json" \
  -d '{"action":"write","resource":"law_trusttx","payload":{"id":"TR-TEST-2"}}'
# Expected: 400, {"error":{"message":"law_trusttx payload.id, payload.matter_id, and payload.client_id are required"}}

# 5. A second SAIRNlaw license cannot see the first license's rows (cross-license scoping)
curl -s -X POST https://sairn.vercel.app/api/sd-data \
  -H "Authorization: Bearer <OTHER_LICENSE_KEY>" -H "Content-Type: application/json" \
  -d '{"action":"read","resource":"law_trusttx"}'
# Expected: {"ok":true,"data":[],...} -- does NOT include TR-TEST-1
```

Also confirm in the live app: open `sairn.vercel.app/sairnlaw`, create a real trust transaction via the UI, and confirm the toast reads "Transaction recorded" (not "Saved on this device only — server sync not yet enabled").

- [ ] **Step 5: Push**

```bash
git push origin main
```

- [ ] **Step 6: Live-verify against production (post-push)**

Repeat Step 4's checks against `sairn.vercel.app/sairnlaw` directly if Step 4 was run pre-push against a preview URL, or re-confirm the deployed commit hash matches what was pushed (normalize line endings before comparing — CRLF/LF, not content, was the cause of a known false-positive deploy-mismatch class in prior sessions).

- [ ] **Step 7: Write the session handoff**

Use the `sairn-session-handoff` skill to record this feature's landing. Check whether the most recent `SAIRNLAW-SESSION-N-HANDOFF.md` number is still current (re-derive from the repo, don't assume) and note explicitly that step 2 (the atomic disbursement check-and-write) is a separate, not-yet-started follow-on, not part of what this session shipped.

---

## Self-Review Notes

- **Spec coverage:** all three resources (`law_clients`/`law_matters`/`law_trusttx`) get schema + read + write (Tasks 1, 3, 4, 5). `client_id`/`matter_id` real columns per the spec's decision (Task 1). No role gating, no session check, per the spec's decisions and the 2026-08-16 correction (Global Constraints, and called out in each route block's own comment). `client_id` trusted as-sent, no FK validation (explicitly noted in Task 1's SQL comment and Global Constraints). Missing-table degrade behavior (`provisioned:false` on read, `503 NOT_PROVISIONED` on write) matches the spec's Edge Cases section exactly. Testing plan matches the spec's own (no new pure-function unit tests; live curl verification in Task 6).
- **Placeholder scan:** no TBD/TODO; every step shows real code matching the actual current `api/sd-data.js` content (re-read immediately before writing this plan — confirmed exact line content at the insertion point and the `RESOURCES`/error-string locations) or a real runnable command with a stated expected result.
- **Type/name consistency:** `law_clients`/`law_matters`/`law_trusttx` resource strings, `client_id`/`matter_id`/`trusttx_id`/`data`/`license_hash` column names, and the `payload.id`/`payload.client_id`/`payload.matter_id` field names are spelled identically across the SQL (Task 1), the route code (Tasks 3-5), and the existing client code they must match (`sairnlaw.html`'s `rec.id`/`rec.client_id`/`rec.matter_id`, confirmed by reading `saveClient()`/`saveMatter()`/`saveTrustTransaction()` directly rather than assumed).
