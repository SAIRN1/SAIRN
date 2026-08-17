# SAIRNlaw — trust disbursement server-sync, step 3a (deposit-void balance guard)

## Problem

Step 2 (`docs/superpowers/specs/2026-08-16-sairnlaw-trust-disbursement-atomic-check-design.md`)
closed the cross-device over-disbursement race by making Disbursement
*creation* go through an atomic, advisory-lock-guarded balance check. It
explicitly left one related gap open, logged to `SAIRN-BACKLOG.md`
("SAIRNlaw void-of-deposit can retroactively negative a client's
balance"): voiding a *Deposit* is not checked against the resulting
balance at all — it goes through the same plain, unguarded upsert as
every other void. Concrete sequence: Deposit $500 (balance $500) →
Disbursement $500 (balance $0, correctly allowed) → someone voids the
*Deposit* (a required-reason action, already possible today) → the
client's real balance goes negative, with a $500 disbursement now
standing against zero real deposited funds. This spec closes that gap.

**Verified starting state (2026-08-17):**
- `confirmVoid()` (`sairnlaw.html:2097-2107`) mutates the local record's
  `status`/`voided_reason`/`voided_at` in place (keeping every other
  field — `type`, `amount`, `client_id`, `matter_id` — unchanged from the
  original record) and sends it through `sdnData('write','law_trusttx',t)`
  — the exact same call shape as a create.
- `api/sd-data.js`'s `law_trusttx` write block (`:1973`) currently routes
  `payload.type === 'Disbursement' && payload.status !== 'Voided'`
  (`:1986`) through `rpc/law_check_and_insert_disbursement`; every other
  write — including *every* void, Deposit or Disbursement — falls through
  to the plain upsert.
- `law_check_and_insert_disbursement()` (`sql/sairnlaw_trust_disbursement_atomic_check.sql`)
  computes the client's balance inline (`select coalesce(sum(case when
  type='Deposit' then amount else -amount end),0) ... where status =
  'Posted'`) — no shared/reusable helper exists yet.
- `sdnData()` (`sairnlaw.html:1056`) already has a narrow structured-
  rejection branch (step 2) that returns `{rejected:true,code,message}`
  for exactly one known error code (`INSUFFICIENT_TRUST_BALANCE`) and
  `null` for everything else.

## Scope, decided during brainstorming

- **Only voiding a Deposit is guarded.** `payload.status==='Voided' &&
  payload.type==='Deposit'` routes through the new atomic function.
  Voiding a Disbursement only ever *increases* the client's balance
  (removes a prior deduction) — no negative-balance risk — so it keeps
  the exact plain upsert unchanged, symmetric with step 2's own reasoning
  for why Deposit-creation and voids didn't need guarding there.
- **Double-void is guarded too.** The new function rejects voiding a row
  whose current server-side `status` is not `'Posted'` (i.e., already
  voided) with a real error, rather than silently re-processing or
  trusting the client to never offer that action.
- **Balance computation is extracted into a shared helper**,
  `law_client_balance(p_license_hash, p_client_id) returns numeric` —
  both `law_check_and_insert_disbursement()` (edited to call it instead
  of its inline query — same live behavior, no logic change) and the new
  void-guard function call it. Single source of truth for the one
  computation this entire feature's money-correctness rests on.
- **Client-side rollback mirrors step 2's exactly.** On a real
  `VOID_WOULD_NEGATIVE_BALANCE` or `ALREADY_VOIDED` rejection,
  `confirmVoid()` reverts its optimistic local mutation (`status` back to
  `'Posted'`, clear `voided_reason`/`voided_at`) rather than leaving a
  local record that claims a void happened when the server refused it.

## Architecture

**Schema (new migration, `sql/sairnlaw_deposit_void_balance_guard.sql`,
idempotent, extends step 2's tables/functions):**

- `create or replace function law_client_balance(p_license_hash text,
  p_client_id text) returns numeric` — the exact balance query already
  live in `law_check_and_insert_disbursement()`, extracted verbatim.
- `law_check_and_insert_disbursement()` is `create or replace`d to call
  `law_client_balance(p_license_hash, p_client_id)` in place of its
  inline `select coalesce(sum(...))...` — the only change to this
  already-shipped, live-verified function; every other line (advisory
  lock, retry-idempotency check, `INVALID_AMOUNT` guard, insert, unified
  return point) stays exactly as step 2 left it.
- New function `law_check_and_void_deposit(p_license_hash text,
  p_trusttx_id text, p_voided_reason text) returns public.law_trusttx`:
  takes `pg_advisory_xact_lock(hashtext(p_license_hash || ':' ||
  <the row's own client_id>))` — the row must be looked up first (before
  the client_id needed for the lock key is even known), so the lock is
  acquired immediately after that lookup, not before it, unlike the
  disbursement function (which receives `client_id` as a parameter
  already). Rejects `NOT_FOUND` if no row matches `(license_hash,
  trusttx_id)`. Rejects `ALREADY_VOIDED` if the found row's `status <>
  'Posted'`. Computes `law_client_balance(p_license_hash, v_row.client_id)
  - v_row.amount` (the balance *without* this deposit); rejects
  `VOID_WOULD_NEGATIVE_BALANCE` if that would be negative. Otherwise
  updates the row's `status`, `voided_reason`, `voided_at`, and `data`
  jsonb (merging the void fields into the existing blob, same shape
  `confirmVoid()` already sends), returns the updated row.

**Routing (`api/sd-data.js`, `law_trusttx` write block):** one new branch,
checked before the existing Disbursement-RPC branch (`:1986`):
`payload.status === 'Voided' && payload.type === 'Deposit'` → POST to
`rpc/law_check_and_void_deposit` with `p_license_hash`, `p_trusttx_id:
String(payload.id)`, `p_voided_reason: payload.voided_reason || null`.
400-body parsing (same pattern as step 2's `dnt_appointments`-derived
convention): message starting `NOT_FOUND` or containing "does not
exist"/"relation ... does not exist" → `503 NOT_PROVISIONED`; message
starting `ALREADY_VOIDED` → `409 {code:'ALREADY_VOIDED', message:'This
transaction has already been voided.'}`; message starting
`VOID_WOULD_NEGATIVE_BALANCE: void of <amount> would leave balance
<balance>` (mirroring step 2's `INSUFFICIENT_TRUST_BALANCE` message
shape, same `-?[\d.]+` capture regex for the negative-safe case) → `409
{code:'VOID_WOULD_NEGATIVE_BALANCE', message:'Voiding this deposit would
leave this client's real trust balance at $<balance> — void rejected.',
real_balance:<balance>}`; anything else → `502` with detail, same as
every other resource on this endpoint. Every other void (Disbursement)
and every Deposit-create keep the exact existing plain-upsert path,
completely untouched.

**Client (`sairnlaw.html`):** `sdnData()`'s existing narrow structured-
rejection branch (`d.error.code==='INSUFFICIENT_TRUST_BALANCE'`) extends
to also match `'VOID_WOULD_NEGATIVE_BALANCE'` and `'ALREADY_VOIDED'` —
same `{rejected:true,code,message}` return shape, same scoping (every
other error code, and every other caller of `sdnData()`, unaffected).
`confirmVoid()` gains the same rollback branch `saveTrustTransaction()`
got in step 2: on `syncResult && syncResult.rejected`, revert the local
record's `status` to `'Posted'` and clear `voided_reason`/`voided_at`
(the exact fields `confirmVoid()` itself just set optimistically),
`st('law_trusttx', list)`, re-render (`rTrust();rDash();`), and show
`syncResult.message` via a 7000ms toast — matching step 2's plan-level
resolution (toast, not reopening a closed modal) for the identical UX
reason (the void modal is already closed by the time a rejection
arrives).

## Explicitly out of scope for this pass

- Any change to Disbursement-void or Deposit-create — both keep the
  unchanged plain upsert.
- Any change to `law_clients`/`law_matters`, or to the still-unwired
  client-side reads for any of the three step-1 resources (separate,
  already-disclosed, unrelated gap).
- The cross-client `trusttx_id` collision edge case
  (`SAIRN-BACKLOG.md`, 2026-08-17 entry) — explicitly assessed as
  theoretical/unreachable, no action here.
- Any UI change beyond the rollback-and-toast on rejection (no new
  confirmation step, no pre-flight "would this go negative" preview
  before the void is attempted).

## Edge cases

- **Voiding a deposit that would leave the balance at exactly $0:**
  allowed — the check is `< 0`, not `<= 0`, matching the disbursement
  function's own `p_amount > v_balance` (strictly greater) convention for
  what counts as a rejection.
- **Voiding a deposit whose client has other, unrelated deposits and
  disbursements:** `law_client_balance()` sums the client's *entire*
  Posted ledger, so a void is correctly evaluated against the full
  picture, not just transactions touching the same matter — matches the
  existing client-level (not matter-level) balance model used everywhere
  else in this feature.
- **A concurrent Disbursement-create and Deposit-void for the same
  client:** both now take the same advisory lock
  (`hashtext(license_hash || ':' || client_id)`), so they genuinely
  serialize against each other, not just against their own kind — this is
  the scenario step 3a's live concurrency test specifically exercises.
- **Migration not yet run:** the new RPC call 404s/400s with a
  "function ... does not exist" message, degrading to the same honest
  `503 NOT_PROVISIONED` every other not-yet-migrated resource on this
  endpoint uses.
- **A void payload missing `voided_reason`:** already rejected client-side
  today (`confirmVoid()`'s own `if(!reason)` check, `sairnlaw.html:2098`)
  before any server call — unchanged by this spec.

## Testing / verification plan

Live concurrency test analogous to step 2's, proving the lock genuinely
serializes across *both* operations, not just within one: set up a client
with a single $500 Deposit (balance $500), then fire a Disbursement-create
for $500 and a void of that same Deposit *simultaneously* — exactly one
should succeed (whichever wins the lock first), and the other should be
rejected with the real, post-first-transaction balance (not a stale
pre-lock read). Also live-verify: voiding a deposit within safe balance
succeeds; voiding a deposit that would go negative is rejected with the
real balance in the message; voiding an already-voided deposit is
rejected with `ALREADY_VOIDED`; voiding a Disbursement still goes through
the unchanged plain path; a Deposit-create still goes through the
unchanged plain path; the client-side rollback (local record reverted to
`Posted`, real error shown) through the actual `sairnlaw.html` UI on a
genuine rejection, not just via curl.
