# SAIRNcash 30-Day Trial Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SAIRNcash a server-side-authoritative 30-day free trial (no Stripe dependency), with admin-approval-only renewal, as the platform's reference implementation for this pattern.

**Architecture:** A new `sairncash_trial` Supabase table is the single source of truth for trial state. Three new `api/sairncash/*.js` endpoints (public start, public verify, admin-gated renew) talk to it via the same raw-REST-with-service-role-key pattern every other `api/sairncash/*.js` file already uses (see `waitlist.js`). Pure expiry/validity math is extracted into `api/_lib/sairncash-trial.js` so it's unit-testable without mocking Supabase, matching this repo's existing `api/_lib/dental-reminder-window.js` precedent. `sairncash.html` gets a parallel `getTrial()/saveTrial()/isTrialActive()/reverifyTrial()` set that mirrors the existing `getSub()/saveSub()/isSubscribed()/reverifySubscription()` subscription code exactly, so `initApp()`'s gate becomes "real subscription OR active trial."

**Tech Stack:** Vercel serverless functions (CommonJS, zero new npm deps — `crypto` is a Node built-in), Supabase REST (service-role key, no ORM, matching every existing `api/sairncash/*.js`), plain `node:assert` tests (no framework, matching `api/_lib/*.test.js` and `api/sairndental/send-reminder.test.js`), vanilla JS in `sairncash.html`'s single `<script>` block.

## Global Constraints

- **Syntax rule (CLAUDE.md):** run `node --check` on every touched file (or, for `sairncash.html`, on the extracted `<script>` block content) before moving to the next task. Zero errors before any commit.
- **Never bulk-replace.** Every `sairncash.html` edit in this plan is a targeted insertion/edit at a specific line range — re-read the file immediately before editing if any earlier task's line numbers may have shifted it.
- **Push protocol (CLAUDE.md):** before the final push, run sairn-guardian-v2's Check 0 + numbered checks against every changed file. After pushing, live-verify each new endpoint against `sairn.vercel.app` with real `curl`/browser calls — never assume from a clean `git push` alone.
- **Error shape:** every new endpoint returns errors as `{error:{code, message}}` (code optional) or `{error:{message}}`, matching `waitlist.js`/`verify.js`. Success is `res.status(200).json({...})`.
- **`SAIRNCASH_ADMIN_SECRET`** is a new Vercel env var this plan introduces — it does not exist yet. `trial-renew.js` must fail closed (500) if it's unset, exactly like `send-reminder.js` does for `CRON_SECRET`.
- **Trial banner threshold: N = 5 days.** Confirmed by Michael 2026-08-18.
- **SAIRNcash only.** No other app's file is touched by this plan.

---

### Task 1: `sairncash_trial` Supabase schema

**Files:**
- Create: `sql/sairncash_trial_schema.sql`

**Interfaces:**
- Produces: table `public.sairncash_trial` with columns `id, email, trial_token, started_at, expires_at, status, renewal_count, last_renewed_at, last_renewed_note, created_at` — every later task's Supabase REST calls depend on these exact column names.

- [ ] **Step 1: Write the migration file**

```sql
-- sql/sairncash_trial_schema.sql
-- Real backing table for SAIRNcash's 30-day free trial (no Stripe
-- dependency -- Michael's 2026-08-18 decision to hold off on a real
-- Stripe account and build a trial instead). Same server-authoritative
-- standard the 2026-08-10 audit already enforced for isSubscribed()
-- (real expiresAt, never a client-only timer), extended to a
-- trial-expiry field instead of a subscription-expiry field. See
-- docs/superpowers/specs/2026-08-18-sairncash-trial-flow-design.md.
--
-- trial_token is the bearer credential the client holds (mirrors
-- subscriptionId's role in the existing Stripe flow) -- not the email.
-- Renewal is admin-approval-only (api/sairncash/trial-renew.js, gated
-- by SAIRNCASH_ADMIN_SECRET) -- never self-service.
--
-- Run this in Supabase's SQL editor.
create table if not exists public.sairncash_trial (
  id                 uuid primary key default gen_random_uuid(),
  email              text not null unique,
  trial_token        text not null unique,
  started_at         timestamptz not null default now(),
  expires_at         timestamptz not null,
  status             text not null default 'active' check (status in ('active','expired','revoked')),
  renewal_count      integer not null default 0,
  last_renewed_at    timestamptz,
  last_renewed_note  text,
  created_at         timestamptz not null default now()
);
create index if not exists idx_sairncash_trial_token on public.sairncash_trial (trial_token);
alter table public.sairncash_trial enable row level security;
drop policy if exists "svc only sairncash_trial" on public.sairncash_trial;
create policy "svc only sairncash_trial" on public.sairncash_trial
  for all using (false) with check (false);
grant select, insert, update on public.sairncash_trial to service_role;
revoke all on public.sairncash_trial from anon, authenticated;

-- Verify after running:
--   select * from sairncash_trial limit 5;
-- should return 0 rows (empty table, no error).
```

- [ ] **Step 2: Commit**

```bash
git add sql/sairncash_trial_schema.sql
git commit -m "docs: SQL -- sairncash_trial schema (30-day trial, no Stripe dependency)"
```

Note: this file is not runnable by the agent — flag to Michael to run it in Supabase's SQL editor before Task 3's endpoint can be live-tested end-to-end. Tasks 2 and 5's auth-gate tests don't need the table to exist (Task 2 is pure logic, Task 5's tests only exercise the auth-gate branch that returns before any DB call).

---

### Task 2: Pure trial-logic helper + tests

**Files:**
- Create: `api/_lib/sairncash-trial.js`
- Create: `api/_lib/sairncash-trial.test.js`

**Interfaces:**
- Produces: `computeExpiry(startMs)` → ISO string, `isTrialValid(row, nowMs)` → boolean, `daysLeft(expiresAtIso, nowMs)` → integer (≥0). Tasks 3, 4, and 5 import all three by name from `./sairncash-trial.js` (relative to `api/sairncash/*.js`, so `../_lib/sairncash-trial.js` from that directory).

- [ ] **Step 1: Write the failing test**

```javascript
// api/_lib/sairncash-trial.test.js
// Plain node:assert tests -- no test framework, matching this
// directory's existing convention (dental-reminder-window.test.js).
// Run: node api/_lib/sairncash-trial.test.js

const assert = require('assert');
const { computeExpiry, isTrialValid, daysLeft } = require('./sairncash-trial.js');

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (err) {
    console.error('  FAIL - ' + name);
    console.error('    ' + err.message);
    process.exitCode = 1;
  }
}

console.log('api/_lib/sairncash-trial.js');

test('computeExpiry returns exactly 30 days after the given start time', () => {
  const start = Date.UTC(2026, 0, 1, 0, 0, 0);
  const expiry = computeExpiry(start);
  assert.strictEqual(expiry, new Date(Date.UTC(2026, 0, 31, 0, 0, 0)).toISOString());
});

test('isTrialValid: true when active and expires_at is in the future', () => {
  const now = Date.UTC(2026, 0, 15);
  const row = { status: 'active', expires_at: new Date(Date.UTC(2026, 0, 20)).toISOString() };
  assert.strictEqual(isTrialValid(row, now), true);
});

test('isTrialValid: false when active but expires_at is in the past', () => {
  const now = Date.UTC(2026, 0, 25);
  const row = { status: 'active', expires_at: new Date(Date.UTC(2026, 0, 20)).toISOString() };
  assert.strictEqual(isTrialValid(row, now), false);
});

test('isTrialValid: false when status is revoked, even if expires_at is future', () => {
  const now = Date.UTC(2026, 0, 15);
  const row = { status: 'revoked', expires_at: new Date(Date.UTC(2026, 0, 20)).toISOString() };
  assert.strictEqual(isTrialValid(row, now), false);
});

test('isTrialValid: false when expires_at exactly equals now (boundary, not inclusive)', () => {
  const now = Date.UTC(2026, 0, 20);
  const row = { status: 'active', expires_at: new Date(now).toISOString() };
  assert.strictEqual(isTrialValid(row, now), false);
});

test('daysLeft: rounds up partial days (4 days 1 hour left -> 5)', () => {
  const now = Date.UTC(2026, 0, 15, 0, 0, 0);
  const expiresAt = new Date(Date.UTC(2026, 0, 19, 1, 0, 0)).toISOString();
  assert.strictEqual(daysLeft(expiresAt, now), 5);
});

test('daysLeft: exactly N whole days left -> N (no rounding up an extra day)', () => {
  const now = Date.UTC(2026, 0, 15, 0, 0, 0);
  const expiresAt = new Date(Date.UTC(2026, 0, 20, 0, 0, 0)).toISOString();
  assert.strictEqual(daysLeft(expiresAt, now), 5);
});

test('daysLeft: never returns negative once already expired', () => {
  const now = Date.UTC(2026, 0, 25);
  const expiresAt = new Date(Date.UTC(2026, 0, 20)).toISOString();
  assert.strictEqual(daysLeft(expiresAt, now), 0);
});

console.log(passed + ' passed');
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node api/_lib/sairncash-trial.test.js`
Expected: FAIL — `Cannot find module './sairncash-trial.js'`

- [ ] **Step 3: Write minimal implementation**

```javascript
// api/_lib/sairncash-trial.js
// Pure trial-expiry/validity logic for SAIRNcash's 30-day free trial --
// no network/DB access, testable in isolation (sairncash-trial.test.js).
// Extracted so trial-start.js, trial-verify.js, and trial-renew.js all
// share one real computation instead of three copies that could drift.
// See docs/superpowers/specs/2026-08-18-sairncash-trial-flow-design.md.

var THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

function computeExpiry(startMs) {
  return new Date(startMs + THIRTY_DAYS_MS).toISOString();
}

function isTrialValid(row, nowMs) {
  if (!row || row.status === 'revoked') return false;
  return new Date(row.expires_at).getTime() > nowMs;
}

function daysLeft(expiresAtIso, nowMs) {
  var remainingMs = new Date(expiresAtIso).getTime() - nowMs;
  if (remainingMs <= 0) return 0;
  return Math.ceil(remainingMs / (24 * 60 * 60 * 1000));
}

module.exports = { computeExpiry: computeExpiry, isTrialValid: isTrialValid, daysLeft: daysLeft };
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node api/_lib/sairncash-trial.test.js`
Expected: all 8 tests print `ok`, final line `8 passed`, exit code 0.

- [ ] **Step 5: `node --check`**

Run: `node --check api/_lib/sairncash-trial.js && node --check api/_lib/sairncash-trial.test.js`
Expected: no output, exit code 0.

- [ ] **Step 6: Commit**

```bash
git add api/_lib/sairncash-trial.js api/_lib/sairncash-trial.test.js
git commit -m "feat: SAIRNcash -- pure trial expiry/validity helper + tests"
```

---

### Task 3: `trial-start.js` (public signup endpoint)

**Files:**
- Create: `api/sairncash/trial-start.js`

**Interfaces:**
- Consumes: `computeExpiry(startMs)` from `../_lib/sairncash-trial.js` (Task 2).
- Produces: `POST /api/sairncash/trial-start` — request `{email}`, success response `{trialToken, expiresAt}` (200), duplicate-email response `{error:{code:'ALREADY_EXISTS', message}}` (409), missing-table response `{error:{code:'NOT_PROVISIONED', message}}` (503). Task 6's `startTrial()` client function depends on this exact request/response shape.

- [ ] **Step 1: Write the implementation**

(No isolated unit test for this file — like `waitlist.js` and `checkout.js`, it's a thin REST-call wrapper with no pure branch worth extracting beyond what Task 2 already covers. Its correctness is checked in Task 7's live verification, same as its two siblings.)

```javascript
// api/sairncash/trial-start.js
// Creates a real, server-authoritative 30-day trial -- no Stripe
// dependency (Michael's 2026-08-18 decision). One trial per email;
// the only anti-abuse control in v1 (confirmed acceptable by Michael --
// renewal is admin-approval-gated anyway, see trial-renew.js).
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// REQUIRES migration: sql/sairncash_trial_schema.sql.
// See docs/superpowers/specs/2026-08-18-sairncash-trial-flow-design.md.

const crypto = require('crypto');
const { computeExpiry } = require('../_lib/sairncash-trial.js');

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }

  const email = req.body && req.body.email;
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    res.status(400).json({ error: { message: 'Valid email required' } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  try {
    const trialToken = crypto.randomBytes(32).toString('hex');
    const startedAt = Date.now();
    const expiresAt = computeExpiry(startedAt);

    const r = await fetch(SUPABASE_URL + '/rest/v1/sairncash_trial', {
      method: 'POST',
      headers: {
        apikey: SERVICE_KEY,
        Authorization: 'Bearer ' + SERVICE_KEY,
        'Content-Type': 'application/json',
        Prefer: 'return=minimal'
      },
      body: JSON.stringify({
        email: email,
        trial_token: trialToken,
        started_at: new Date(startedAt).toISOString(),
        expires_at: expiresAt
      })
    });

    if (r.status === 404) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Trial table not set up yet -- run sql/sairncash_trial_schema.sql in Supabase first.' } });
      return;
    }
    if (r.status === 409) {
      res.status(409).json({ error: { code: 'ALREADY_EXISTS', message: 'This email already has a SAIRNcash trial. Contact support if you need help accessing it.' } });
      return;
    }
    if (!r.ok) {
      const bodyText = await r.text().catch(() => '');
      console.error('SAIRNcash trial-start insert failed:', r.status, bodyText);
      res.status(502).json({ error: { message: 'Could not start trial -- try again' } });
      return;
    }

    res.status(200).json({ trialToken: trialToken, expiresAt: expiresAt });
  } catch (e) {
    console.error('SAIRNcash trial-start error:', e.message);
    res.status(502).json({ error: { message: 'Could not start trial -- try again' } });
  }
};
```

- [ ] **Step 2: `node --check`**

Run: `node --check api/sairncash/trial-start.js`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add api/sairncash/trial-start.js
git commit -m "feat: SAIRNcash -- trial-start.js (public 30-day trial signup, no Stripe)"
```

---

### Task 4: `trial-verify.js` (public re-verification endpoint)

**Files:**
- Create: `api/sairncash/trial-verify.js`

**Interfaces:**
- Consumes: `isTrialValid(row, nowMs)`, `daysLeft(expiresAtIso, nowMs)` from `../_lib/sairncash-trial.js` (Task 2).
- Produces: `POST /api/sairncash/trial-verify` — request `{trialToken}`, response `{valid, expiresAt, daysLeft}` (200; `valid:false` when not found, expired, or revoked -- no error status for a normal "no longer valid" answer, matching `verify.js`'s `subscriptionId` branch shape). Task 6's `reverifyTrial()` depends on this exact response shape.

- [ ] **Step 1: Write the implementation**

```javascript
// api/sairncash/trial-verify.js
// Re-verifies a SAIRNcash trial against the real server-side record --
// called once per app load (mirrors verify.js's subscriptionId
// re-verification branch). Never trusts a client-supplied date; expiry
// is always computed from this table's own expires_at compared to this
// request's own server clock.
//
// Side effect: if a trial is found expired but its status column still
// says 'active', flips it to 'expired' here (best-effort, does not fail
// the response if this write fails) -- keeps the table honest for
// direct Supabase-dashboard inspection instead of silently staying
// 'active' forever after the real expiry passes.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// See docs/superpowers/specs/2026-08-18-sairncash-trial-flow-design.md.

const { isTrialValid, daysLeft } = require('../_lib/sairncash-trial.js');

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }

  const trialToken = req.body && req.body.trialToken;
  if (!trialToken) {
    res.status(400).json({ error: { message: 'Missing trialToken' } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  try {
    const r = await fetch(
      SUPABASE_URL + '/rest/v1/sairncash_trial?trial_token=eq.' + encodeURIComponent(trialToken) + '&select=status,expires_at',
      { headers: { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY } }
    );
    if (!r.ok) {
      const bodyText = await r.text().catch(() => '');
      console.error('SAIRNcash trial-verify lookup failed:', r.status, bodyText);
      res.status(502).json({ error: { message: 'Could not verify trial' } });
      return;
    }
    const rows = await r.json();
    if (!rows || rows.length === 0) {
      res.status(200).json({ valid: false });
      return;
    }
    const row = rows[0];
    const now = Date.now();
    const valid = isTrialValid(row, now);

    if (!valid && row.status === 'active') {
      // Best-effort write-back; a failure here doesn't change the real
      // answer this response already computed.
      fetch(
        SUPABASE_URL + '/rest/v1/sairncash_trial?trial_token=eq.' + encodeURIComponent(trialToken),
        {
          method: 'PATCH',
          headers: {
            apikey: SERVICE_KEY,
            Authorization: 'Bearer ' + SERVICE_KEY,
            'Content-Type': 'application/json',
            Prefer: 'return=minimal'
          },
          body: JSON.stringify({ status: 'expired' })
        }
      ).catch((e) => console.error('SAIRNcash trial-verify status write-back failed:', e.message));
    }

    res.status(200).json({
      valid: valid,
      expiresAt: row.expires_at,
      daysLeft: daysLeft(row.expires_at, now)
    });
  } catch (e) {
    console.error('SAIRNcash trial-verify error:', e.message);
    res.status(502).json({ error: { message: 'Could not verify trial' } });
  }
};
```

- [ ] **Step 2: `node --check`**

Run: `node --check api/sairncash/trial-verify.js`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add api/sairncash/trial-verify.js
git commit -m "feat: SAIRNcash -- trial-verify.js (server-authoritative trial re-check)"
```

---

### Task 5: `trial-renew.js` (admin-gated renewal endpoint) + auth-gate tests

**Files:**
- Create: `api/sairncash/trial-renew.js`
- Create: `api/sairncash/trial-renew.test.js`

**Interfaces:**
- Consumes: `computeExpiry(startMs)` from `../_lib/sairncash-trial.js` (Task 2).
- Produces: `POST /api/sairncash/trial-renew`, header `Authorization: Bearer <SAIRNCASH_ADMIN_SECRET>` required, request `{email, note}`, response `{ok:true, expiresAt, renewalCount}` (200). Never called from `sairncash.html` — curl/direct-API only, per Michael's confirmed decision.

- [ ] **Step 1: Write the failing test**

```javascript
// api/sairncash/trial-renew.test.js
// Plain node:assert tests -- no test framework, matching
// send-reminder.test.js's convention exactly (same auth-gate class of
// endpoint: a shared-secret Bearer check that returns before any
// network call, genuinely testable without mocking Supabase).
// Run: node api/sairncash/trial-renew.test.js

const assert = require('assert');

var ADMIN_SECRET_ENV_NAME = 'SAIRNCASH_ADMIN_SECRET';
var fixtureValue = 'unit-test-fixture-' + Date.now() + '-' + Math.floor(Math.random() * 1e6);

function setFixtureEnv(name, value) { process.env[name] = value; }
function clearEnv(name) { delete process.env[name]; }

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  return res;
}

let passed = 0;
async function test(name, fn) {
  try {
    await fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (err) {
    console.error('  FAIL - ' + name);
    console.error('    ' + err.message);
    process.exitCode = 1;
  }
}

async function main() {
  console.log('api/sairncash/trial-renew.js');

  await test('missing SAIRNCASH_ADMIN_SECRET env var -> 500, never reaches the auth check', async () => {
    clearEnv(ADMIN_SECRET_ENV_NAME);
    delete require.cache[require.resolve('./trial-renew.js')];
    var handler = require('./trial-renew.js');
    var res = mockRes();
    await handler({ method: 'POST', headers: {}, body: {} }, res);
    assert.strictEqual(res.statusCode, 500);
  });

  await test('secret set, no Authorization header -> 401', async () => {
    setFixtureEnv(ADMIN_SECRET_ENV_NAME, fixtureValue);
    delete require.cache[require.resolve('./trial-renew.js')];
    var handler = require('./trial-renew.js');
    var res = mockRes();
    await handler({ method: 'POST', headers: {}, body: {} }, res);
    assert.strictEqual(res.statusCode, 401);
  });

  await test('secret set, wrong Authorization header -> 401', async () => {
    setFixtureEnv(ADMIN_SECRET_ENV_NAME, fixtureValue);
    delete require.cache[require.resolve('./trial-renew.js')];
    var handler = require('./trial-renew.js');
    var res = mockRes();
    await handler({ method: 'POST', headers: { authorization: 'Bearer wrong-value' }, body: {} }, res);
    assert.strictEqual(res.statusCode, 401);
  });

  await test('non-POST method -> 405, checked before the auth gate', async () => {
    setFixtureEnv(ADMIN_SECRET_ENV_NAME, fixtureValue);
    delete require.cache[require.resolve('./trial-renew.js')];
    var handler = require('./trial-renew.js');
    var res = mockRes();
    await handler({ method: 'GET', headers: { authorization: 'Bearer ' + fixtureValue }, body: {} }, res);
    assert.strictEqual(res.statusCode, 405);
  });

  console.log(passed + ' passed');
}

main();
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node api/sairncash/trial-renew.test.js`
Expected: FAIL — `Cannot find module './trial-renew.js'`

- [ ] **Step 3: Write minimal implementation**

```javascript
// api/sairncash/trial-renew.js
// Admin-only: grants the next real 30-day trial window. Gated by
// Authorization: Bearer SAIRNCASH_ADMIN_SECRET, same shape as
// api/sairndental/send-reminder.js's CRON_SECRET gate -- fails closed
// (500) if the env var itself is unset, 401 if the header is
// missing/wrong. Never callable from sairncash.html; confirmed by
// Michael 2026-08-18 that renewal is a manual-approval action, not
// self-service -- this is the only write path that can extend
// expires_at.
//
// Sets a fresh 30-day window from the moment of approval (not
// additive -- doesn't stack onto whatever time was left).
//
// REQUIRES env: SAIRNCASH_ADMIN_SECRET, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// See docs/superpowers/specs/2026-08-18-sairncash-trial-flow-design.md.

const { computeExpiry } = require('../_lib/sairncash-trial.js');

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'POST only' } });
    return;
  }
  if (!process.env.SAIRNCASH_ADMIN_SECRET) {
    console.error('SAIRNCASH_ADMIN_SECRET not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }
  if (req.headers.authorization !== 'Bearer ' + process.env.SAIRNCASH_ADMIN_SECRET) {
    res.status(401).json({ error: { message: 'Unauthorized' } });
    return;
  }

  const email = req.body && req.body.email;
  const note = (req.body && req.body.note) || null;
  if (!email) {
    res.status(400).json({ error: { message: 'Missing email' } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }

  try {
    const lookupR = await fetch(
      SUPABASE_URL + '/rest/v1/sairncash_trial?email=eq.' + encodeURIComponent(email) + '&select=renewal_count',
      { headers: { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY } }
    );
    if (!lookupR.ok) {
      res.status(502).json({ error: { message: 'Could not look up trial' } });
      return;
    }
    const rows = await lookupR.json();
    if (!rows || rows.length === 0) {
      res.status(404).json({ error: { message: 'No trial found for that email' } });
      return;
    }

    const now = Date.now();
    const expiresAt = computeExpiry(now);
    const nextRenewalCount = (rows[0].renewal_count || 0) + 1;

    const patchR = await fetch(
      SUPABASE_URL + '/rest/v1/sairncash_trial?email=eq.' + encodeURIComponent(email),
      {
        method: 'PATCH',
        headers: {
          apikey: SERVICE_KEY,
          Authorization: 'Bearer ' + SERVICE_KEY,
          'Content-Type': 'application/json',
          Prefer: 'return=minimal'
        },
        body: JSON.stringify({
          status: 'active',
          expires_at: expiresAt,
          renewal_count: nextRenewalCount,
          last_renewed_at: new Date(now).toISOString(),
          last_renewed_note: note
        })
      }
    );
    if (!patchR.ok) {
      const bodyText = await patchR.text().catch(() => '');
      console.error('SAIRNcash trial-renew patch failed:', patchR.status, bodyText);
      res.status(502).json({ error: { message: 'Could not renew trial' } });
      return;
    }

    res.status(200).json({ ok: true, expiresAt: expiresAt, renewalCount: nextRenewalCount });
  } catch (e) {
    console.error('SAIRNcash trial-renew error:', e.message);
    res.status(502).json({ error: { message: 'Could not renew trial' } });
  }
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node api/sairncash/trial-renew.test.js`
Expected: all 4 tests print `ok`, final line `4 passed`, exit code 0.

- [ ] **Step 5: `node --check`**

Run: `node --check api/sairncash/trial-renew.js && node --check api/sairncash/trial-renew.test.js`
Expected: no output, exit code 0.

- [ ] **Step 6: Commit**

```bash
git add api/sairncash/trial-renew.js api/sairncash/trial-renew.test.js
git commit -m "feat: SAIRNcash -- trial-renew.js (admin-secret-gated, fresh 30-day window)"
```

---

### Task 6: `sairncash.html` client wiring

**Files:**
- Modify: `sairncash.html:91` (CSS — add `.trial-badge` class)
- Modify: `sairncash.html:247-266` (paywall markup — add trial CTA + expired-trial state)
- Modify: `sairncash.html:268-278` (app-topbar — add trial-days-left badge)
- Modify: `sairncash.html:494-529` (subscription block — add parallel trial functions immediately after)
- Modify: `sairncash.html:562-575` (`initApp()` — extend the gate to include trial)

**Interfaces:**
- Consumes: `POST /api/sairncash/trial-start` (Task 3), `POST /api/sairncash/trial-verify` (Task 4) — exact request/response shapes as defined in those tasks.
- Produces: `getTrial()`, `saveTrial(d)`, `isTrialActive()`, `async reverifyTrial()`, `async startTrial()`, `renderTrialBadge()` — no other task depends on these (this is the last task), but keep names exact for anyone extending this later.

- [ ] **Step 1: Re-read the current file around each target region**

Line numbers below assume no prior edit in this task has shifted them yet — re-read `sairncash.html` immediately before each edit if unsure, per the Global Constraints no-bulk-replace rule.

- [ ] **Step 2: Add the trial-badge CSS**

Add immediately after the existing `.pw-trial-note` rule (`sairncash.html:91`):

```css
.trial-badge{background:rgba(0,229,196,0.12);border:1px solid rgba(0,229,196,0.3);border-radius:8px;padding:4px 10px;font-size:11px;font-weight:600;color:var(--pulse)}
```

- [ ] **Step 3: Update the paywall markup**

Replace the `pw-price`/`pw-period` block through the `#subBtn` button block
(`sairncash.html:251-264` — from `<div class="pw-price">` through the
closing `</div>` of `.pw-card`) with:

```html
      <div class="pw-trial-note" id="pwTrialNote">Start with a 30-day free trial -- no credit card. After 30 days your trial ends; renewal is by request, reviewed manually (not an automatic charge).</div>
      <ul class="pw-features">
        <li><span>✓</span>Unlimited AI with Claude</li>
        <li><span>✓</span>Quarterly tax set-aside tracking</li>
        <li><span>✓</span>Deduction categorization</li>
        <li><span>✓</span>Phone + computer synced live</li>
      </ul>
      <input class="pw-email" type="email" id="pwEmail" placeholder="your@email.com">
      <button class="pw-btn" id="trialBtn" onclick="startTrial()">Start your 30-day free trial</button>
      <div class="pw-error" id="pwError"></div>
      <p class="pw-note">No credit card required · No hidden fees</p>
      <p class="pw-not-tax-filing">SAIRNcash tracks, categorizes, and estimates what you owe. It does not file your taxes -- hand off to your accountant or filing software (TurboTax, H&amp;R Block, a CPA) when it's time to file.</p>
      <div class="pw-error" id="trialExpiredNote" style="display:none">Your trial has ended. Renewal is reviewed manually -- contact us to continue.</div>
    </div>
```

(This removes the `$9.99/mo` price display along with the old `startCheckout()` button from the default paywall view — showing a price next to a "free trial, no credit card" CTA would read as a mixed signal, the same class of issue the pivot spec's "no dark patterns" standard already calls out for the paid flow. The paid-Stripe path itself is dormant per Michael's decision to hold off on Stripe, not deleted from the codebase — `checkout.js`/`verify.js`'s `sessionId` branch and `startCheckout()`/`handleStripeReturn()` in the script stay untouched, ready for a future task if Stripe is turned back on and a real price is decided. Full removal of that dormant code is out of scope here; only the paywall's default-visible CTA and price display change.)

- [ ] **Step 4: Add the trial badge to the app topbar**

In `app-topbar-right` (`sairncash.html:271-277`), insert a new span immediately after `<span class="pro-badge">PRO</span>`:

```html
        <span class="trial-badge" id="trialBadge" style="display:none"></span>
```

- [ ] **Step 5: Add the parallel trial functions**

Insert immediately after the existing `showAccount()`/`signOut()` block (`sairncash.html:522-529`, right before the `// ── USAGE ──` comment or equivalent next section marker):

```javascript
// ── TRIAL (30-day, no Stripe dependency) ────────────────────────────
// 2026-08-18: server-authoritative trial, same standard as
// isSubscribed()/reverifySubscription() above -- real expires_at from
// the server, never a client-only timer. Renewal is admin-approval-only
// (api/sairncash/trial-renew.js) -- no self-service renew path exists
// anywhere in this client code, by design.
function getTrial() { try { return JSON.parse(localStorage.getItem('sairncash_trial') || 'null'); } catch { return null; } }
function saveTrial(d) { localStorage.setItem('sairncash_trial', JSON.stringify(d)); }
function isTrialActive() {
  const t = getTrial();
  if (!t || !t.expiresAt) return false;
  return Date.now() < new Date(t.expiresAt).getTime();
}
async function reverifyTrial() {
  const t = getTrial();
  if (!t || !t.trialToken) return false;
  try {
    const res = await fetch('/api/sairncash/trial-verify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ trialToken: t.trialToken }) });
    const data = await res.json();
    if (data.valid) { saveTrial({ trialToken: t.trialToken, expiresAt: data.expiresAt, daysLeft: data.daysLeft }); return true; }
    return false;
  } catch (e) {
    return isTrialActive();
  }
}
async function startTrial() {
  const btn = document.getElementById('trialBtn');
  const err = document.getElementById('pwError');
  const email = document.getElementById('pwEmail').value.trim();
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    err.textContent = 'Enter a valid email to start your trial'; err.style.display = 'block';
    return;
  }
  btn.disabled = true; btn.textContent = 'Starting trial...'; err.style.display = 'none';
  try {
    const res = await fetch('/api/sairncash/trial-start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) });
    const data = await res.json();
    if (data.trialToken) {
      saveTrial({ trialToken: data.trialToken, expiresAt: data.expiresAt, daysLeft: 30 });
      await initApp();
    } else {
      throw new Error((data.error && data.error.message) || 'Could not start trial');
    }
  } catch (e) {
    err.textContent = 'Error: ' + e.message; err.style.display = 'block';
    btn.disabled = false; btn.textContent = 'Start your 30-day free trial';
  }
}
function renderTrialBadge() {
  const t = getTrial();
  const badge = document.getElementById('trialBadge');
  if (!badge) return;
  if (t && typeof t.daysLeft === 'number' && t.daysLeft <= 5) {
    badge.textContent = t.daysLeft <= 0 ? 'Trial ending' : t.daysLeft + ' day' + (t.daysLeft === 1 ? '' : 's') + ' left';
    badge.style.display = 'inline-block';
  } else {
    badge.style.display = 'none';
  }
}
```

- [ ] **Step 6: Extend `initApp()`'s gate**

In `initApp()` (`sairncash.html:562-575`), replace:

```javascript
async function initApp() {
  const justPaid = await handleStripeReturn();
  if (justPaid || await reverifySubscription()) {
    showAppShell();
    // Firebase sync only starts once a real, verified customerId exists
    // (2026-08-10 isolation fix) -- never before, never with a fallback
    // shared path. initFinanceSync() waits for it to finish setting up
    // window._fbIncomeRef/_fbDeductionsRef before attaching listeners.
    if (window._initFirebaseSync) { await window._initFirebaseSync(); initFinanceSync(); initProfileSync(); }
  } else {
    document.getElementById('paywall').style.display = 'flex';
    document.getElementById('appShell').classList.remove('show');
  }
}
```

with:

```javascript
async function initApp() {
  const justPaid = await handleStripeReturn();
  const hasTrial = getTrial() && await reverifyTrial();
  if (justPaid || await reverifySubscription() || hasTrial) {
    showAppShell();
    renderTrialBadge();
    // Firebase sync only starts once a real, verified customerId exists
    // (2026-08-10 isolation fix) -- never before, never with a fallback
    // shared path. initFinanceSync() waits for it to finish setting up
    // window._fbIncomeRef/_fbDeductionsRef before attaching listeners.
    if (window._initFirebaseSync) { await window._initFirebaseSync(); initFinanceSync(); initProfileSync(); }
  } else {
    document.getElementById('paywall').style.display = 'flex';
    document.getElementById('appShell').classList.remove('show');
    const hadTrial = getTrial();
    document.getElementById('trialExpiredNote').style.display = hadTrial ? 'block' : 'none';
    document.getElementById('trialBtn').style.display = hadTrial ? 'none' : 'block';
  }
}
```

(A user whose trial has expired keeps a `sairncash_trial` entry in `localStorage` with a now-invalid token — `getTrial()` still finds it, so the expired-state branch shows the "contact us" message instead of a fresh "start trial" button, satisfying "no self-serve renew" even for a returning expired-trial user on the same browser.)

- [ ] **Step 7: Extract and check the script block**

```bash
node -e "
const fs = require('fs');
const html = fs.readFileSync('sairncash.html', 'utf8');
const m = html.match(/<script>([\s\S]*)<\/script>/);
fs.writeFileSync('/tmp/sairncash-script-check.js', m[1]);
"
node --check /tmp/sairncash-script-check.js
```

Expected: no output, exit code 0. (Per CLAUDE.md's syntax rule — run this after every edit in this task, not just once at the end, if editing incrementally across steps 2-6.)

- [ ] **Step 8: Commit**

```bash
git add sairncash.html
git commit -m "feat: SAIRNcash -- wire 30-day trial into paywall/topbar/initApp (no Stripe path)"
```

---

### Task 7: Push, live-verify, update coordination doc

**Files:**
- None created/modified — verification only.

- [ ] **Step 1: Run sairn-guardian-v2's Check 0 + numbered checks**

Against `sairncash.html` and every new `api/sairncash/*.js` / `api/_lib/sairncash-trial.js` file, per CLAUDE.md's Push Protocol. Do not push on a partial check.

- [ ] **Step 2: Push**

```bash
git push origin main
```

If rejected (another session pushed in the meantime — this repo has concurrent sessions, see `SAIRN-ACTIVE-WORK.md`): `git fetch origin main`, confirm the new commits don't touch any file this plan touched, `git rebase origin/main`, push again.

- [ ] **Step 3: Flag the SQL migration and admin-secret env var to Michael**

Neither is runnable/settable by the agent:
- `sql/sairncash_trial_schema.sql` needs to be run in Supabase's SQL editor.
- `SAIRNCASH_ADMIN_SECRET` needs to be set in Vercel's environment variables (any high-entropy value — e.g. `openssl rand -hex 32` — is fine; it's a shared secret, not a user-facing credential).

Both are hard prerequisites for Step 4 below — wait for confirmation both are done before live-verifying.

- [ ] **Step 4: Live-verify each endpoint against `sairn.vercel.app`**

```bash
# trial-start: real signup
curl -s -X POST https://sairn.vercel.app/api/sairncash/trial-start \
  -H "Content-Type: application/json" \
  -d '{"email":"hank-trial-verify-test@example.com"}'
# Expect: {"trialToken":"...","expiresAt":"..."} -- save the trialToken for the next calls.

# trial-start: duplicate email correctly rejected
curl -s -X POST https://sairn.vercel.app/api/sairncash/trial-start \
  -H "Content-Type: application/json" \
  -d '{"email":"hank-trial-verify-test@example.com"}'
# Expect: 409 {"error":{"code":"ALREADY_EXISTS", ...}}

# trial-verify: real token returns valid:true, daysLeft:30
curl -s -X POST https://sairn.vercel.app/api/sairncash/trial-verify \
  -H "Content-Type: application/json" \
  -d '{"trialToken":"<the real token from above>"}'
# Expect: {"valid":true,"expiresAt":"...","daysLeft":30}

# trial-verify: garbage token returns valid:false, not an error
curl -s -X POST https://sairn.vercel.app/api/sairncash/trial-verify \
  -H "Content-Type: application/json" \
  -d '{"trialToken":"not-a-real-token"}'
# Expect: {"valid":false}

# trial-renew: no Authorization header -> 401
curl -s -X POST https://sairn.vercel.app/api/sairncash/trial-renew \
  -H "Content-Type: application/json" \
  -d '{"email":"hank-trial-verify-test@example.com"}'
# Expect: 401

# trial-renew: real admin secret -> fresh 30-day window
curl -s -X POST https://sairn.vercel.app/api/sairncash/trial-renew \
  -H "Authorization: Bearer <real SAIRNCASH_ADMIN_SECRET>" \
  -H "Content-Type: application/json" \
  -d '{"email":"hank-trial-verify-test@example.com","note":"live-verification test renewal"}'
# Expect: {"ok":true,"expiresAt":"...","renewalCount":1}
```

- [ ] **Step 5: Browser click-through**

Using Playwright (or claude-in-chrome), navigate to `sairn.vercel.app/sairncash`, start a trial with a fresh test email, confirm `showAppShell()` fires and the app is usable, confirm the trial badge is hidden (30 days left, above the 5-day threshold). This is the same live-verification discipline used for the SAIRNlaw void-rollback check earlier this session — a code-review pass is not a substitute for watching it actually happen in a real browser against the real deployment.

- [ ] **Step 6: Update `SAIRN-ACTIVE-WORK-hank.md`**

Clear this task's active-work line, same pattern as every other cleared entry in that file this session. (Updated 2026-08-24: this step originally said `SAIRN-ACTIVE-WORK.md`. That file was split per session — Hank appends to `SAIRN-ACTIVE-WORK-hank.md`, CC to `-cc.md`, Cody to `-cody.md`. Nothing is appended to the shared file any more.)

```bash
git add SAIRN-ACTIVE-WORK-hank.md
git commit -m "docs: SAIRN-ACTIVE-WORK-hank.md -- clear Hank's SAIRNcash trial-flow build task, done"
git push origin main
```
