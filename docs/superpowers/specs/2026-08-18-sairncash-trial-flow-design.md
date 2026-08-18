# SAIRNcash — Server-Side 30-Day Trial Flow (Platform Reference Implementation)

**Status:** Design drafted 2026-08-18, pending review. Not yet implemented.

Decision (2026-08-18): hold off setting up a real Stripe account for now.
Build a 30-day free trial instead — no live Stripe dependency. SAIRNcash
is the reference implementation; the same pattern is intended for every
SAIRN app eventually, as a **separate future pass** (same relationship
StoneDesk's `invSaveStore()` had to the platform-wide honest-failure
`st()` wrapper sweep). This spec covers SAIRNcash only.

## 0. Why SAIRNcash needs a new identity model for this

SAIRNcash currently has **no account/identity system independent of
Stripe** — `isSubscribed()`/`reverifySubscription()`
(`sairncash.html:494-520`) derive everything from a live
`stripe.subscriptions.retrieve()` call; there is no Supabase table
backing a subscriber's identity at all. With Stripe out of the loop for
this feature, a real server-side record has to exist somewhere else —
this is new surface, not an extension of an existing table.

`sairncash_waitlist` (`sql/sairncash_waitlist_schema.sql`) is the only
existing SAIRNcash Supabase table; it's email-only, no expiry concept,
not reusable as-is.

## 1. Data model — new table, `sairncash_trial`

```sql
create table if not exists public.sairncash_trial (
  id               uuid primary key default gen_random_uuid(),
  email            text not null unique,
  trial_token      text not null unique,   -- crypto.randomBytes(32).toString('hex'), 256-bit
  started_at       timestamptz not null default now(),
  expires_at       timestamptz not null,    -- started_at + 30 days, computed server-side only
  status           text not null default 'active' check (status in ('active','expired','revoked')),
  renewal_count    integer not null default 0,
  last_renewed_at  timestamptz,
  last_renewed_note text,                   -- free-text: who/why, entered by whoever approves
  created_at       timestamptz not null default now()
);
```

Same RLS posture as `sairncash_waitlist`: `enable row level security`,
deny-all policy, `grant select, insert, update on ... to service_role`
only. Never touched by the anon key.

`trial_token` is the bearer credential the client holds (mirrors
`subscriptionId` today) — not the email. Email is contact/dedup only.

## 2. Server-side trust boundary (ASVS 8.3.1 / A01)

Every trial-state decision (`active` vs `expired`) is computed **once,
server-side, from `expires_at` compared to the DB's own `now()`** —
never from a client-supplied timestamp, and never purely from
`localStorage`. This is the exact same posture the 2026-08-10 audit
already enforced for `isSubscribed()` (real `expiresAt` from Stripe,
not a client-only 35-day timer) — this spec extends that standard to a
trial-expiry field instead of a subscription-expiry field, per your
instruction.

## 3. New endpoints (`api/sairncash/`)

**`trial-start.js`** — public, POST `{email}`.
- Rejects if `email` already has a row (one trial per email — the only
  anti-abuse control in this v1; see open question 2 below).
- `trial_token = crypto.randomBytes(32).toString('hex')`,
  `expires_at = now() + 30 days` (Postgres/server clock).
- Returns `{trialToken, expiresAt}`. No auth required to call — this is
  the public signup path, same trust level as `checkout.js` today.

**`trial-verify.js`** — public, POST `{trialToken}`.
- Looks up by token, returns `{valid, status, expiresAt}` — `valid`
  computed as `status==='active' && expires_at > now()`, entirely
  server-side. Same shape/role as `verify.js`'s `subscriptionId` branch,
  so the client's existing `saveSub()`-style cache-then-reverify pattern
  extends with minimal new client logic.
- Client calls this once per load (mirrors `reverifySubscription()`),
  falls back to last-known local state **only on a network failure**,
  never on a real server rejection — same fail-open-on-network/
  fail-closed-on-rejection split already documented in the existing
  code's comments.

**`trial-renew.js`** — **admin-only**, POST `{email or trialToken, note}`.
- Gated by `Authorization: Bearer <SAIRNCASH_ADMIN_SECRET>`, checked
  server-side against an env var, same shape as
  `api/sairndental/send-reminder.js`'s `CRON_SECRET` gate (401 if
  missing/wrong, 500 if the env var itself isn't configured — fails
  closed either way). This is the **only** write path that can extend
  `expires_at`.
- Sets `expires_at = now() + 30 days` fresh (not additive) —
  "renewable" per your instruction means a clean new 30-day window from
  the moment of approval, not stacking on top of whatever time was left.
  Increments `renewal_count`, stamps `last_renewed_at`/
  `last_renewed_note` for an audit trail (ASVS 16 logging — who
  approved, when).
- Never callable from `sairncash.html` or any public surface — no
  self-service renew button anywhere in the client, matching your
  correction that this is an approval gate, not a request-and-get flow.

## 4. Client-side (`sairncash.html`)

- New signup CTA (likely replacing/sitting alongside the current
  "Claim early access" waitlist button) calling `trial-start.js`,
  storing `{trialToken, expiresAt}` in `localStorage` under a new key
  (e.g. `sairncash_trial`) — cache only, never trusted as source of
  truth, same posture `sairncash_sub` already has.
- `isSubscribed()`/`reverifySubscription()` extended (or a parallel
  `isTrialActive()`/`reverifyTrial()` pair, TBD during implementation)
  so the app's gated features check "real paid subscription OR active
  trial" rather than subscription alone.
- Expired-trial UI state: since renewal is admin-approval-only, the
  expired state shows something like "Your trial has ended — contact
  us to continue" with **no self-serve renew action** — matches your
  correction directly.

## 5. Security checklist applied (owasp-security pass)

- **A01/ASVS 8.3.1** — trial state authoritative server-side only,
  renewal behind a server-enforced secret the client never holds.
- **ASVS 7.2.3** — `trial_token` from `crypto.randomBytes(32)` (256-bit
  entropy), not sequential/guessable, not derived from email.
- **A06/ASVS 6.3.1 (anti-automation)** — **real gap, not solved by this
  v1**: `trial-start.js` has no rate-limiting or bot defense beyond the
  one-trial-per-email uniqueness constraint. Nothing on this platform
  currently provides rate-limiting infra (checked — no precedent
  anywhere in `api/`), so this would be new infrastructure, not a
  quick add. Flagging as an accepted v1 gap rather than silently
  shipping it unmentioned — see open question 2.
- **A09/ASVS 16 (logging)** — every renewal stamps who/when/why
  (`last_renewed_note`, `last_renewed_at`, `renewal_count`) directly on
  the row; no separate log table needed at this volume.
- **Fail-closed on rejection, fail-soft on network error** — carried
  forward unchanged from the existing `reverifySubscription()`
  precedent, applied identically to the trial-verify path.
- **No secrets in client code** — `SAIRNCASH_ADMIN_SECRET` stays
  server-side only, set in Vercel env vars, never referenced from
  `sairncash.html`.

## 6. Explicitly out of scope for this task

- No live Stripe dependency (per your decision).
- No Bridge/cross-app data pull (per your instruction — stays deferred).
- No platform-wide rollout — SAIRNcash only; replicating this pattern
  to the other 10 apps is a separate future pass, not part of this task.
- No self-service renewal of any kind.
- No bot/abuse defense beyond email-uniqueness (flagged above, not
  solved here).

## 7. Open questions before implementation starts

1. **Admin-renewal auth mechanism.** Recommend the `Bearer
   SAIRNCASH_ADMIN_SECRET` env-var gate (§3, matches the existing
   `CRON_SECRET` precedent) for v1 — meaning "renew this trial" is a
   direct API call (curl, or a tiny internal-only unauthenticated-by-
   click-but-secret-gated page), not a built admin dashboard with its
   own login. Acceptable for v1, or do you want a real clickable
   admin-approval UI (which would need its own auth system built first —
   bigger scope)?
2. **Anti-abuse strength.** v1 as designed only blocks re-trialing the
   *same* email — someone can still get unlimited trials with new
   emails. Acceptable for now (matches "renewal needs your manual
   approval anyway, so abuse is capped by your attention" reasoning), or
   do you want something stronger before this ships?
3. **Trial-ending in-app notice** ("5 days left in your trial") — not
   explicitly requested, but the existing pivot spec's "no dark
   patterns, notice before anything happens" standard (§3.2) would
   suggest one. Small addition — include in this pass, or hold for
   later?
