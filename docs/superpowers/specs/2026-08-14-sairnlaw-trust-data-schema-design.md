# SAIRNlaw — trust disbursement server-sync, step 1 (data schema + resource wiring)

## Problem

`saveTrustTransaction()` (`sairnlaw.html:2042`) is a real IOLTA-compliance
feature — trust-fund disbursements must never exceed a client's trust
balance — but it currently has nowhere real to write to. `api/sd-data.js`
has zero `law_*` entries anywhere in its resource allowlist; every
`sdnData('write','law_trusttx',...)` call 400s today. The app already
honestly reports this ("Saved on this device only — server sync not yet
enabled") rather than lying about it, but the underlying gap is real: two
staff on two different devices/sessions can each read the same
pre-disbursement balance, both pass the local check, both write — a real
over-disbursement of client trust funds.

Closing that gap needs an atomic server-side check-and-write. That's not
possible yet because there is no server-side data for it to check against
at all — no `sql/sairnlaw_data_schema.sql`, no `law_*` routes in
`api/sd-data.js`. This spec covers only making that data real and durable
(step 1). The atomic check-and-write itself is a separate, later spec
(step 2).

**Verified starting state (2026-08-14):**
- `api/sd-data.js` (~1500 lines, ~100 `resource===` route blocks) has no
  `app_id: 'sairnlaw'` or `law_*` branch anywhere. Confirmed by direct
  grep, not assumed from the backlog note alone.
- 19 distinct `law_*` localStorage keys exist client-side in
  `sairnlaw.html`; none are wired server-side.
- `sql/` has `sairnlaw_audit_log_schema.sql`, `sairnlaw_citator_schema.sql`,
  `sairnlaw_employee_auth_schema.sql` — no business-data schema file.
- `api/law-auth.js` already has the reusable auth primitive this needs:
  `verifySessionToken(token, license_hash, 'sairnlaw')`, returning
  `{employee_id, role}` where `role` is one of `LAW_ROLES =
  ['owner','attorney','paralegal']` (`api/_lib/auth.js:70`).
- `clientLedgerBalance()` (`sairnlaw.html:2002`) and `reconcileTrust()`
  filter the full in-memory transaction list by `client_id` — no existing
  logic depends on a server-side lookup yet.

**Correction (2026-08-16, final review):** the "No `sairnlaw.html` client
change needed" statements below (Routes section, and the "Migration not yet
run" edge case) are true only for auth/write fallback behavior, not for
reads generally — do not read them as "the client already reads from the
server." `sairnlaw.html` has zero `sdnData('read',...)` calls anywhere
(grep-confirmed), so the `law_clients`/`law_matters`/`law_trusttx` read
routes described below are live on the server but currently unreachable
from the client. Writes are genuinely durable server-side; reads are still
100% localStorage. This is write-through, not full cross-device sync yet.
Wiring real client-side reads (with local/server merge semantics) is
deferred to a separate future spec, not part of this pass.

## Scope, decided during brainstorming

- **Three resources, not just trust tx**: `law_clients`, `law_matters`,
  `law_trusttx`. The balance check's dependencies (a matter's owning
  client) mean trust tx alone isn't self-sufficient, and clients/matters
  are core data that should be real regardless.
- **No new role restriction.** All three `LAW_ROLES` can write and void
  trust transactions server-side, matching current (unrestricted)
  client-side behavior exactly. Restricting this would be a separate,
  orthogonal access-control decision, not part of making existing
  behavior durable.
- **Full read+write for law_clients/law_matters**, not a narrow read-only
  mirror — same jsonb-blob-per-row shape every other resource on this
  endpoint uses (`grd_properties`, `grd_jobs`, etc.), since a narrower
  version would need redoing when step 2 lands anyway.
- **`client_id`/`matter_id` stored as real columns**, not just inside the
  jsonb blob, on `law_trusttx` (`client_id`, `matter_id`) and
  `law_matters` (`client_id`) — mirrors the existing `grd_jobs.property_id`
  precedent (added as a real column specifically because a later feature
  needed to query by it). Adding these now avoids a second migration +
  backfill when step 2 starts.
- **`client_id` is trusted as sent by the client**, not derived
  server-side from `matter_id`. This matches the platform-wide precedent
  (no resource on this endpoint validates a cross-reference id against
  another table today) and keeps this step's scope to "make it durable,"
  not "make it correct" — the forgery gap this leaves is real but is
  explicitly step 2's job to close, alongside the atomic balance check
  itself.
- **Void is a plain write**, not a special-cased action. Because there's
  no role restriction (see above), it needs none of `grd_progress_photos`'
  self-QC-gate machinery — the client mutates `status`/`voided_reason`/
  `voided_at` locally and sends the same record through the same write
  route.

## Architecture

**Schema (`sql/sairnlaw_data_schema.sql`, new file):** Same conventions as
`sairngrounds_data_schema.sql` — idempotent (`create table if not
exists`), `pgcrypto` for `gen_random_uuid()`, RLS enabled with no anon
policy (service-role only, `api/sd-data.js` is the only door in), 64KB
`data` size cap matching `MAX_PAYLOAD_BYTES`.

- `law_clients`: `id uuid pk, license_hash, app_id='sairnlaw', client_id
  text, data jsonb, created_at, updated_at`. `unique(license_hash,
  client_id)`. Index on `license_hash`.
- `law_matters`: same shape + `client_id text not null` as a real column.
  `unique(license_hash, matter_id)`. Indexes on `license_hash` and
  `client_id`.
- `law_trusttx`: same shape + `matter_id text not null` and `client_id
  text not null` as real columns. `unique(license_hash, trusttx_id)`.
  Indexes on `license_hash` and `client_id` (the column step 2's balance
  query will filter on).

**Routes (`api/sd-data.js`):** Six new blocks (read+write × 3 resources),
inserted alongside the existing sairngrounds/sairnscape blocks, following
the exact `grd_jobs` shape:
- `read`: `select data where license_hash=eq.<hash>`; on missing table
  (`404`/`400` from PostgREST) return `200 {ok:true, data:[],
  provisioned:false}` — graceful degrade, not an error.
- `write`: upsert via `on_conflict=license_hash,<id-column>`,
  `Prefer: resolution=merge-duplicates,return=representation`; on missing
  table return `503 {code:'NOT_PROVISIONED', message:'...run
  sql/sairnlaw_data_schema.sql first.'}`.
- Required-field validation (400 on failure, matching every existing
  block): `law_clients` write needs `payload.id`; `law_matters` needs
  `payload.id + payload.client_id`; `law_trusttx` needs `payload.id +
  payload.matter_id + payload.client_id`.
- **Correction (2026-08-16, found while writing the implementation plan):**
  no session-token check. `sairnlaw.html`'s `sdnData()` (the function every
  `law_trusttx`/`law_clients`/`law_matters` write goes through) never
  attaches the `X-SD-Auth` session header — only `lawAuth()` calls do — so
  a `verifySessionToken()` requirement as originally written here would
  401 every real call this feature exists to fix. It also matches no
  existing precedent: every other plain-write resource in `api/sd-data.js`
  authenticates via the Bearer license key alone (scoped by
  `license_hash`); `verifySessionToken`/role checks appear only on
  specifically role-gated actions (QC decisions, payroll reads) — none of
  which apply here per the "no new role restriction" decision above.
  Auth for all six new blocks is Bearer license key only, same as
  `grd_jobs`/`dnt_appointments`/every comparable resource. No
  `sairnlaw.html` client change needed.

## Explicitly out of scope for this pass

- The atomic disbursement check-and-write endpoint (step 2).
- Any cross-device race protection.
- Any FK/existence validation between `law_clients` → `law_matters` →
  `law_trusttx` (server trusts client-supplied linking ids, matching
  platform precedent).
- Any role restriction on who can write/void trust transactions.
- The other 16 unwired `law_*` client resources (`opaccounts`, `optx`,
  `deadlines`, `invoices`, etc.) — not touched by this pass.
- Any actual DB migration execution — the SQL is written and handed to a
  human to run in Supabase's SQL editor (this environment has no DB
  execution access, confirmed precedent from prior SAIRNlaw/SAIRNdesign/
  SAIRNlegacy builds).

## Edge cases

- **Migration not yet run**: reads degrade to `[] + provisioned:false`
  (matches every existing resource's fallback); writes return
  `503 NOT_PROVISIONED` with an actionable message, and the existing
  client-side toast ("Saved on this device only — server sync not yet
  enabled") continues to fire exactly as it does today — no client change
  needed for this case, it already handles a `null`/failed `sdnData()`
  result correctly.
- **A trust tx write references a matter_id/client_id that doesn't
  actually exist**: accepted as-is (see scope decision) — this is the
  known, disclosed gap step 2 closes, not a step 1 defect.
- **Payload over 64KB**: rejected at the endpoint's existing
  `MAX_PAYLOAD_BYTES` gate before any DB call, same as every other
  resource — no new logic needed.
- **A void write**: goes through the same `law_trusttx` write block as a
  create; no special server logic distinguishes the two.

## Testing / verification plan

No new pure-function logic to unit-test — required-field checks only,
matching the untested `grd_jobs`/`grd_properties` precedent (this
endpoint's plain CRUD blocks are verified live, not via Node test files).
After a human runs the migration: live-verify via direct `curl` (per this
project's standing Push Protocol) that `law_clients`/`law_matters`/
`law_trusttx` writes round-trip correctly, that a missing-table read
degrades to `provisioned:false` (test against a fresh/unmigrated license
if available, otherwise verify the code path by inspection plus the
existing `grd_jobs` live precedent), that a request with a missing/invalid
Bearer license key is rejected the same way every other resource already
is (existing endpoint-level check, not new logic), and that
`saveTrustTransaction()`/`confirmVoid()` in the live app now show "Transaction
recorded"/"Transaction voided" instead of the server-sync-disabled toast.
