# Which tenants share a backend — the real map, 2026-09-17

**This is a MAP, not a fix.** Nothing here was changed. The question asked was
"where does one customer's bad behaviour currently have blast radius touching
other customers", and the answer is worth having before anything is partitioned.

**READ THE LAST COLUMN BEFORE THE FIRST.** Several of these are shared *by
design* and partitioning them would cost more than the blast radius is worth.
Saying which is which is the point; a list of everything shared is not a
finding, it is an inventory.

**WHAT "TENANT" MEANS HERE**, because the platform has two nested senses and
conflating them is how a scope gets misjudged: an **APP** (`sairnlaw`,
`stonedesk`, …) and a **LICENCE** inside it (one law firm, one countertop
shop). Blast radius differs between the two and each row says which.

---

## The map

| # | Shared resource | Shared across | One tenant can… | Isolation today | Partitionable? |
|---|---|---|---|---|---|
| 1 | **Supabase project** (`SUPABASE_URL`, one `SUPABASE_SERVICE_ROLE_KEY`, 46 modules) | **every app, every licence** | exhaust connections, lock a shared row, fill disk | licence-scoped rows; no pool or storage quota per tenant | **Not realistically.** One project is the platform's whole data model; separating it is a re-architecture, not a partition. **Mitigate instead** — timeouts and bulkheads at the caller, which `api/_lib/resilience.js` now does for one call site |
| 2 | **`sairn_ai_rate_limit_consume` RPC / daily AI budget** | app-wide, with a per-licence sub-budget | consume the app's AI ceiling | **Partially bulkheaded already** (2026-09-15): past `SAIRN_AI_CONTENTION_FLOOR` a licence may hold at most `SAIRN_AI_TENANT_SHARE`, default half. Circuit-broken observe-only + bulkhead + timeout since 2026-09-17 | **Already partitioned, and the residual is the APP dimension** — see the finding below |
| 3 | **`ANTHROPIC_API_KEY`** (`api/claude.js`) | **every app, every licence** | burn the org's Anthropic quota; trip provider-side rate limits for everyone | only the SAIRN-side daily counter in row 2 | **Realistic but not cheap.** Per-app keys would scope provider-side limits and cost. A single key is also a single revocation |
| 4 | **`SD_AUTH_SECRET`** — one session-signing secret | **every app** | nothing directly; but one leak forges sessions **platform-wide** | none — it is one secret by construction | **Realistic:** per-app signing secrets. This is a SPOF for *confidentiality*, not for availability, and it is the highest-value row here |
| 5 | **`STRIPE_SECRET_KEY`** | every app that charges | trigger provider-side rate limits; one leak reaches all revenue | none | Per-app restricted keys are a real Stripe feature. **Realistic** |
| 6 | **`COURTLISTENER_API_TOKEN`** | every SAIRNlaw licence | exhaust a third party's shared, revocable quota | `cl_rate_limit_consume` RPC | **Not partitionable** — the token is the vendor's, not ours. Already limited; the residual is that `courtlistener.js` **refuses** on a limiter outage (verified 2026-09-15), so a counting failure stops the citator for every firm at once |
| 7 | **Vercel project** — one function pool, one `CRON_SECRET` | every app | exhaust concurrent function slots | none | **Not realistically.** Same shape as row 1 |
| 8 | **`api/bridge.js` `push`** — `bridge_data`, upsert on `shop_id`, **no `Authorization` header at all** | every StoneDesk shop | **write to any other shop's `shop_id`** | none, and the file says so in its own header | **Realistic and cheap** — the endpoint has no read side with any caller (verified 2026-08-24), so the narrowest fix is deleting the write path rather than authenticating it |
| 9 | **`sd-data.js` shared resources** (`employees`, `shared_knowledge`) | across apps, within a licence | nothing cross-licence | licence-scoped and session-gated | Shared **on purpose**; this is the working cross-app path |
| 10 | **`anon-rate-limit.js`** — per-instance counter | every app | **defeat it entirely by arriving concurrently** | none that survives scale-out | Already known: 40 concurrent requests against a limit of 20 produced **zero** trips, 2026-09-05. Needs the shared store, not partitioning |

---

## The findings worth acting on, in order

### 1. `app_id` is CLIENT-SUPPLIED, so the AI budget's app dimension is targetable

`api/claude.js` takes `app_id` **from the request body** and checks it against an
allowlist. The **licence** dimension is different: `claudeTenantKey` is the
verified `license_hash`, so the per-tenant sub-budget added on 2026-09-15 is
sound.

**The consequence is narrow and real:** anyone who knows an allowlisted
`app_id` — they are in shipped frontend code, so everyone does — can spend
against *that app's* ceiling without holding a licence for it. The sub-budget
caps what any one **licence** takes; it does not cap what an **unlicensed
caller** takes from the app pool.

**Not fixed here.** The fix is to derive `app_id` from the verified licence
rather than trust the body, and that changes the demo/anonymous path, which is
a product decision.

### 2. `SD_AUTH_SECRET` is the highest-value single secret and is shared platform-wide

One signing secret across every app. It is not an availability risk — no tenant
can exhaust it — but one leak forges sessions **everywhere at once**, which is a
strictly larger blast radius than any row above it. Per-app signing secrets are
a contained change: the secret is read in one module, `api/_lib/auth.js`.

### 3. `api/bridge.js push` accepts no `Authorization` header

Anyone can upsert any `shop_id`. The file states this and defends it for shop
metadata. **The cheap fix is deletion, not auth:** `pull` has zero callers
across all app files, so `bridge_data` is written and never read.

### 4. The circularity that bounds row 1 forever

The shared circuit-breaker store lives in Supabase. **A Supabase breaker is
therefore instance-backed and observe-only by construction** — asking a database
whether the database is reachable returns the answer you already have. Timeouts
and bulkheads are what actually protect a caller from a slow Supabase, and both
work per-instance. This is stated in `api/_lib/resilience.js` and is repeated
here so nobody proposes the shared breaker for row 1 as an improvement.

---

## What this map does NOT cover, stated so the gap is known

- **Postgres-level contention** — shared locks, autovacuum, plan cache. Row 1 is
  named from the code, not measured against the live database, and nothing here
  says which shared row is actually hot.
- **Storage and egress quotas.** No per-tenant accounting exists to read.
- **The SAIRN Intelligence Network's shared key**, flagged elsewhere as a SPOF.
  **CORRECTED 2026-09-25: the sentence here said "it is not in this
  repository's `api/` surface", and that is false.** `api/network.js` exists
  and has since 2026-08-01 (`8c7d2e7d`); its schema is `sql/network_schema.sql`
  and `network_insights` is present in `db/schema_snapshot.json`, so the table
  is live. What IS true and was the real point: the endpoint is **cross-tenant
  by design** -- it aggregates every install sharing an `app_id`, keyed on the
  same SUPABASE_SERVICE_ROLE_KEY as everything else, and the row it would add
  to the map above is `network_insights` / all shops of one app / no
  `license_hash` column at all. Mapped now rather than named.
- **Whether any of this has ever happened.** This is a map of what is POSSIBLE.
  No incident is claimed, and no row here should be read as one.
