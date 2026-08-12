# SAIRNdental Anonymous-Optional Patient Complaint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the anonymous-optional patient complaint feature per
`docs/superpowers/specs/2026-08-12-sairndental-complaint-design.md` — a
patient-facing public form (message + optional name), a private
thread the patient returns to via a one-time access-token link, and a
staff-side panel where only the `owner` role can respond/resolve, with
a persistent nav badge so an open thread can't be silently ignored.

**Architecture:** A new `dnt_complaints` Supabase resource that is
**read-only** through `api/sd-data.js`'s generic Bearer-license path —
every real mutation (new complaint, patient reply, owner reply/resolve)
goes through three new dedicated endpoints
(`public-complaint-submit.js`, `public-complaint-thread.js`,
`complaint-respond.js`) that each do a fresh read immediately before
writing, never a client-supplied full-record overwrite. A new public
HTML page (`sairndental-complaint.html`, pattern-matched to
`sairndental-book.html`) serves both the initial submission
(`?slug=`) and the returning-patient thread view/reply (`?token=`).
The staff side (`sairndental.html`) gets the standard accessor + panel
+ sync triad, plus a role-gated respond UI and a live nav badge.

**Tech Stack:** No new dependencies — reuses this app's existing
`ld()`/`st()`/`toast()`/`H()`/`$()`/`sdnData()`/`dntLicenseKey()`
helpers, `api/_lib/dental-public.js`'s `resolveSlug()`/
`checkAndIncrementRateLimit()`, and `api/_lib/license.js`'s
`validateLicenseKey()`. Node's built-in `crypto` for the access token.
Plain `node:assert` tests, matching `api/sairndental/public-book.test.js`'s
existing zero-framework convention.

## Global Constraints

- **Field whitelist is exhaustive** (spec §1): the `data` jsonb blob
  for a `dnt_complaints` row is exactly `{id, patient_name, status,
  messages, created_at}` — nothing else, in every task below. No fee,
  phone, or email field, ever.
- **`dnt_complaints` is read-only through `api/sd-data.js`'s generic
  path — enforced with a real `400`, not just a client-side habit**
  (spec §1, deviation 2). The staff app never calls
  `sdnData('write','dnt_complaints',...)`.
- **`access_token` is a real, promoted, unique, indexed column**, not
  buried in `data` — generated once via `crypto.randomBytes(32).toString('hex')`,
  never regenerated (spec §1, deviation 1).
- **Both `public-complaint-thread.js` and `complaint-respond.js` must
  do a fresh read of the row immediately before writing** — never
  trust a client-held or request-scoped-stale copy of `messages`
  (spec §0's race-handling decision, §2). This is the actual point of
  the design; do not "simplify" it back into a single read at the top
  of the function reused for the write.
- **State-transition rule, one rule, no special cases** (spec §0, §7):
  any patient-authored message sets `status` to `'New'`, regardless of
  the current status. An owner `reply` sets `'Awaiting Patient'`; an
  owner `resolve` sets `'Resolved'`.
- **Owner-only responding/closing is a UI-level gate only**
  (`prole==='owner'` in `sairndental.html`), matching this app's
  existing role-gating convention exactly. `complaint-respond.js`
  itself only requires a valid, active license key for the practice —
  do not add a role check there that doesn't exist anywhere else in
  this codebase yet (spec §0 — stated explicitly as an accepted,
  disclosed limitation, not a gap to silently "fix" here).
- **No delete function anywhere in this feature.**
- Message length cap: 4000 characters, enforced on submission, on a
  patient's thread reply, and on an owner's reply/resolve text — same
  constant (`MAX_MESSAGE_LEN`) in all three server files.
- Rate limits: 5 submissions/hour/IP on `public-complaint-submit.js`,
  20 replies/hour/IP on `public-complaint-thread.js`'s `reply` path
  only (loading a thread with no `reply` is never rate-limited).
  `complaint-respond.js` is authenticated, so no rate limit, matching
  every other authenticated write in this app.
- `dnt_complaints` must be added to `DNT_SYNC_RESOURCES`
  (locate `sairndental.html` by content search, not line number — it
  will have shifted by the time Task 8 runs) and
  `dntSyncFromServer()`'s re-render block in the same pass this
  feature ships (spec §4).
- `python tools/checkblocks.py sairndental.html` /
  `div_balance_check.py` / `duplicate_global_check.py` clean after
  every `sairndental.html` change. `node --check` on every new/changed
  `.js` file. Push Protocol: full local checks before push, real
  live-verify after.

---

### Task 1: `dnt_complaints` Supabase table

**Files:**
- Create: `sql/sairndental_complaints_schema.sql`

**Interfaces:**
- Produces: a live `public.dnt_complaints` table (once run manually in
  Supabase — this repo's standing convention, SQL files are committed
  but not auto-applied) with columns `license_hash`, `app_id`,
  `complaint_id`, `access_token` (unique, indexed), `data` (jsonb),
  `created_at`, `updated_at`. Task 2's `api/sd-data.js` read handler and
  Tasks 3-5's endpoints all depend on this exact shape.

- [ ] **Step 1: Write the migration**

```sql
-- sql/sairndental_complaints_schema.sql
-- New table for SAIRNdental's anonymous-optional patient complaint
-- feature (2026-08-12). Matches every existing dnt_* table's shape
-- (see sql/sairndental_referrals_schema.sql for the closest
-- precedent) -- license_hash-scoped, jsonb data payload, 64KB size
-- cap -- but with one deliberate deviation: access_token is a real,
-- promoted, unique, indexed column (same reasoning as
-- dnt_settings.booking_slug in
-- sql/sairndental_availability_booking_schema.sql), because the
-- public thread endpoint must resolve a token directly to a record
-- without already knowing which practice it belongs to. See
-- docs/superpowers/specs/2026-08-12-sairndental-complaint-design.md §1.

create table if not exists public.dnt_complaints (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  complaint_id text not null, access_token text not null unique, data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, complaint_id), constraint dntcp_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntcp_license on public.dnt_complaints(license_hash);
create index if not exists idx_dntcp_token on public.dnt_complaints(access_token);

-- ── RLS: service-role only, matching sql/sairndental_referrals_schema.sql's
-- established pattern for every dnt_* table. ──
alter table public.dnt_complaints enable row level security;
drop policy if exists "svc only dnt_complaints" on public.dnt_complaints;
create policy "svc only dnt_complaints" on public.dnt_complaints for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
grant select, insert, update, delete on public.dnt_complaints to service_role;
```

- [ ] **Step 2: Self-check against the precedent**

Read `sql/sairndental_referrals_schema.sql` and
`sql/sairndental_availability_booking_schema.sql`'s `dnt_settings`
block back-to-back with the file just written; confirm the shape
matches exactly except for the two deliberate deviations
(`complaint_id`/`access_token` naming, the extra unique index). There
is no SQL syntax checker in this repo (same honest limitation the
referral-tracking plan already noted) — this read-back is the only
local verification available. Real verification happens in Task 10
once Michael runs it in Supabase.

- [ ] **Step 3: Commit**

```bash
git add sql/sairndental_complaints_schema.sql
git commit -m "feat: SAIRNdental -- dnt_complaints table (read-only resource, promoted access_token column)"
```

---

### Task 2: `api/sd-data.js` — read-only `dnt_complaints` registration

**Files:** Modify `api/sd-data.js`

**Interfaces:**
- Consumes: Task 1's `public.dnt_complaints` table shape.
- Produces: `resource:'dnt_complaints', action:'read'` returns
  `{ok:true, data:[...], provisioned:bool}` (array of `data` blobs,
  same shape every other resource's read returns) — Task 6's staff
  sync depends on this. `action:'write'` against this resource always
  returns a `400 READ_ONLY_RESOURCE` — this is a deliberate contract,
  not a bug; no later task should ever call
  `sdnData('write','dnt_complaints',...)`.

- [ ] **Step 1: Add to the `RESOURCES` allowlist**

Locate the line `dnt_settings: true, dnt_referrals: true` (inside the
`RESOURCES` object near the top of the file) and change it to:

```js
  dnt_settings: true, dnt_referrals: true, dnt_complaints: true
```

- [ ] **Step 2: Add to the resource-allowlist error message**

Locate the long comma-separated resource-list string (the `400`
response body a couple hundred lines down, ending
`...dnt_denial, dnt_ar, dnt_revenue, dnt_settings, dnt_referrals'`) —
this is the exact string that was missing `dnt_referrals` in a real,
already-fixed bug earlier this project (`4f76eda`, "add dnt_referrals
to RESOURCES gate"). Append `, dnt_complaints` immediately before the
closing `'`. **Do not skip this step** — it's the identical bug class,
and it silently 400s every live request if missed, exactly like it did
for referrals.

- [ ] **Step 3: Add the dedicated read-only handler**

Locate the `dnt_settings` write handler's closing `return; }` (the
block that ends with the `SLUG_TAKEN` response), and insert this new
block immediately after it, before the `dnt_appointments` comment
block:

```js
    // dnt_complaints (2026-08-12) -- own dedicated handler, not the
    // generic DNT_RESOURCES block above, for two reasons: (1)
    // access_token is a real promoted column (unique index), same
    // reasoning as dnt_settings.booking_slug, resolved directly by
    // the public complaint endpoints; (2) this resource is READ-ONLY
    // through this generic Bearer-license path -- action:'write' is
    // explicitly rejected below, on purpose. All real mutations (new
    // complaint, patient reply, owner reply/resolve) go through the
    // dedicated read-then-append-write endpoints in
    // api/sairndental/public-complaint-submit.js,
    // public-complaint-thread.js, and complaint-respond.js instead,
    // specifically to avoid the exact race a full-record client
    // overwrite here would allow (a patient's reply landing between
    // this staff app's read and its write, silently dropped). See
    // docs/superpowers/specs/2026-08-12-sairndental-complaint-design.md §0/§1.
    if (resource === 'dnt_complaints' && action === 'read') {
      const r = await fetch(rest('dnt_complaints?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
      if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
      return;
    }
    if (resource === 'dnt_complaints' && action === 'write') {
      res.status(400).json({ error: { code: 'READ_ONLY_RESOURCE', message: 'dnt_complaints cannot be written via this generic endpoint -- use api/sairndental/complaint-respond.js instead.' } });
      return;
    }
```

- [ ] **Step 4: Syntax-check**

```bash
node --check api/sd-data.js
```

Expected: no output (success).

- [ ] **Step 5: Commit**

```bash
git add api/sd-data.js
git commit -m "feat: SAIRNdental -- register dnt_complaints as read-only in api/sd-data.js"
```

---

### Task 3: `api/sairndental/public-complaint-submit.js`

**Files:**
- Create: `api/sairndental/public-complaint-submit.js`
- Test: `api/sairndental/public-complaint-submit.test.js`

**Interfaces:**
- Consumes: `resolveSlug(slug)` and `checkAndIncrementRateLimit(req,
  windowMinutes, maxCount)` from `../_lib/dental-public` (both already
  exist, unchanged).
- Produces: `POST {slug, message, patient_name?}` → `{ok:true,
  token}` on success. This `token` is what Task 9's public page shows
  the patient and what Task 4's `public-complaint-thread.js` resolves.

- [ ] **Step 1: Write the failing test**

```js
// api/sairndental/public-complaint-submit.test.js
// Plain node:assert tests -- no test framework, matching
// api/sairndental/public-book.test.js's existing convention.
// Run: node api/sairndental/public-complaint-submit.test.js
//
// Covers only the pre-network-call validation paths (required fields,
// message length cap, rate limiting). The full
// resolveSlug -> Supabase insert flow needs a real Supabase
// environment and is covered by Task 10's live verification instead.

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  res.setHeader = function (key, value) { return res; };
  res.end = function () { return res; };
  return res;
}
function mockReq(body) {
  return { method: 'POST', headers: {}, body: body };
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
  console.log('api/sairndental/public-complaint-submit.js');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  delete require.cache[require.resolve('../_lib/dental-public')];
  require.cache[require.resolve('../_lib/dental-public')] = {
    exports: {
      resolveSlug: function () { throw new Error('resolveSlug should not be called in validation tests'); },
      checkAndIncrementRateLimit: async function () { return { allowed: true }; }
    }
  };
  global.fetch = function () { throw new Error('fetch should never be called for a request that fails validation'); };
  delete require.cache[require.resolve('./public-complaint-submit.js')];
  var handler = require('./public-complaint-submit.js');

  await test('missing slug -> 400, never calls fetch', async () => {
    var res = mockRes();
    await handler(mockReq({ message: 'Hello' }), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('missing message -> 400, never calls fetch', async () => {
    var res = mockRes();
    await handler(mockReq({ slug: 'test-practice' }), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('message over 4000 chars -> 400 MESSAGE_TOO_LONG, never calls fetch', async () => {
    var res = mockRes();
    await handler(mockReq({ slug: 'test-practice', message: 'x'.repeat(4001) }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'MESSAGE_TOO_LONG');
  });

  await test('rate-limited -> 429, never calls fetch', async () => {
    require.cache[require.resolve('../_lib/dental-public')].exports.checkAndIncrementRateLimit = async function () { return { allowed: false }; };
    delete require.cache[require.resolve('./public-complaint-submit.js')];
    var rlHandler = require('./public-complaint-submit.js');
    var res = mockRes();
    await rlHandler(mockReq({ slug: 'test-practice', message: 'Hello' }), res);
    assert.strictEqual(res.statusCode, 429);
    assert.strictEqual(res.body.error.code, 'RATE_LIMITED');
  });

  await test('field-whitelist regression (design spec §1/§7): happy-path insert payload.data has exactly {id, patient_name, status, messages, created_at}, nothing else', async () => {
    var capturedBody = null;
    delete require.cache[require.resolve('../_lib/dental-public')];
    require.cache[require.resolve('../_lib/dental-public')] = {
      exports: {
        resolveSlug: async function () { return 'hash-abc'; },
        checkAndIncrementRateLimit: async function () { return { allowed: true }; }
      }
    };
    global.fetch = async function (url, opts) {
      capturedBody = JSON.parse(opts.body);
      return { ok: true, json: async function () { return [capturedBody]; }, text: async function () { return ''; } };
    };
    delete require.cache[require.resolve('./public-complaint-submit.js')];
    var handler = require('./public-complaint-submit.js');
    var res = mockRes();
    await handler(mockReq({ slug: 'test-practice', message: 'Front desk was rude', patient_name: 'Jane' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.ok(res.body.token, 'expected a token in the response');
    assert.ok(capturedBody, 'expected fetch to have been called with a body');
    var dataKeys = Object.keys(capturedBody.data).sort();
    assert.deepStrictEqual(dataKeys, ['created_at', 'id', 'messages', 'patient_name', 'status']);
    assert.strictEqual(capturedBody.data.status, 'New');
    assert.strictEqual(capturedBody.data.messages.length, 1);
    assert.strictEqual(capturedBody.data.messages[0].from, 'patient');
    assert.strictEqual(capturedBody.data.messages[0].text, 'Front desk was rude');
  });

  console.log(passed + ' passed');
}

main();
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node api/sairndental/public-complaint-submit.test.js
```

Expected: `Cannot find module './public-complaint-submit.js'` (the
file doesn't exist yet).

- [ ] **Step 3: Write the implementation**

```js
// api/sairndental/public-complaint-submit.js
// Genuinely public, unauthenticated endpoint -- no license key
// anywhere in this file, same category as public-book.js/
// public-availability.js. Creates a new dnt_complaints thread and
// returns the one-time access_token the patient must save to
// view/reply later -- there is no recovery path if it's lost (design
// spec §0, disclosed, not a bug).

const crypto = require('crypto');
const { resolveSlug, checkAndIncrementRateLimit } = require('../_lib/dental-public');

function supabaseHeaders(extra) {
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return Object.assign({ apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' }, extra || {});
}
function rest(path) {
  return process.env.SUPABASE_URL + '/rest/v1/' + path;
}
function newId(prefix) {
  return prefix + '-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
}
const MAX_MESSAGE_LEN = 4000;

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) { res.status(500).json({ error: { message: 'Server configuration error' } }); return; }

  const body = req.body || {};
  const slug = body.slug;
  const message = typeof body.message === 'string' ? body.message.trim() : '';
  const patientName = typeof body.patient_name === 'string' ? body.patient_name.trim() : '';
  if (!slug || !message) { res.status(400).json({ error: { message: 'slug and message are required' } }); return; }
  if (message.length > MAX_MESSAGE_LEN) { res.status(400).json({ error: { code: 'MESSAGE_TOO_LONG', message: 'Message is too long -- please keep it under ' + MAX_MESSAGE_LEN + ' characters' } }); return; }

  try {
    const rl = await checkAndIncrementRateLimit(req, 60, 5); // 5 submissions per hour per IP
    if (!rl.allowed) { res.status(429).json({ error: { code: 'RATE_LIMITED', message: 'Too many attempts -- please call the office or try again later' } }); return; }

    const licenseHash = await resolveSlug(slug);
    if (!licenseHash) { res.status(404).json({ error: { code: 'UNKNOWN_SLUG', message: 'Practice link not found' } }); return; }

    const complaintId = newId('COMP');
    const accessToken = crypto.randomBytes(32).toString('hex');
    const nowISO = new Date().toISOString();
    const data = {
      id: complaintId, patient_name: patientName, status: 'New',
      messages: [{ from: 'patient', text: message, at: nowISO }],
      created_at: nowISO.slice(0, 10)
    };

    const insertRes = await fetch(rest('dnt_complaints'), {
      method: 'POST',
      headers: Object.assign({}, supabaseHeaders(), { Prefer: 'return=representation' }),
      body: JSON.stringify({
        license_hash: licenseHash, app_id: 'sairndental', complaint_id: complaintId,
        access_token: accessToken, data: data, updated_at: nowISO
      })
    });
    if (insertRes.status === 404 || insertRes.status === 400) {
      const bodyText = await insertRes.text().catch(function () { return ''; });
      if (/relation .* does not exist|does not exist/i.test(bodyText)) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental complaint tables are not set up yet.' } });
        return;
      }
      console.error('SAIRNdental public-complaint-submit insert error:', bodyText);
      res.status(502).json({ error: { message: 'Could not submit -- try again' } });
      return;
    }
    if (!insertRes.ok) {
      const errBody = await insertRes.json().catch(() => null);
      console.error('SAIRNdental public-complaint-submit insert error:', errBody);
      res.status(502).json({ error: { message: 'Could not submit -- try again' } });
      return;
    }

    res.status(200).json({ ok: true, token: accessToken });
  } catch (err) {
    console.error('SAIRNdental public-complaint-submit error:', err.message);
    res.status(502).json({ error: { message: 'Could not submit -- try again' } });
  }
};
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node api/sairndental/public-complaint-submit.test.js
```

Expected: `5 passed`, no `FAIL` lines.

- [ ] **Step 5: Syntax-check**

```bash
node --check api/sairndental/public-complaint-submit.js
```

- [ ] **Step 6: Commit**

```bash
git add api/sairndental/public-complaint-submit.js api/sairndental/public-complaint-submit.test.js
git commit -m "feat: SAIRNdental -- public-complaint-submit.js endpoint + tests"
```

---

### Task 4: `api/sairndental/public-complaint-thread.js`

**Files:**
- Create: `api/sairndental/public-complaint-thread.js`
- Test: `api/sairndental/public-complaint-thread.test.js`

**Interfaces:**
- Consumes: `checkAndIncrementRateLimit` from `../_lib/dental-public`.
- Produces: `POST {token, reply?}` → `{ok:true, status, patient_name,
  messages}`. Task 5's cross-endpoint race test and Task 9's public
  page both call this exact shape.

- [ ] **Step 1: Write the failing test**

```js
// api/sairndental/public-complaint-thread.test.js
// Plain node:assert tests. Run: node api/sairndental/public-complaint-thread.test.js

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  res.setHeader = function (key, value) { return res; };
  res.end = function () { return res; };
  return res;
}
function mockReq(body) {
  return { method: 'POST', headers: {}, body: body };
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
  console.log('api/sairndental/public-complaint-thread.js');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  await test('missing token -> 400, never calls fetch', async () => {
    delete require.cache[require.resolve('../_lib/dental-public')];
    require.cache[require.resolve('../_lib/dental-public')] = { exports: { checkAndIncrementRateLimit: async function () { return { allowed: true }; } } };
    global.fetch = function () { throw new Error('fetch should never be called for a request that fails validation'); };
    delete require.cache[require.resolve('./public-complaint-thread.js')];
    var handler = require('./public-complaint-thread.js');
    var res = mockRes();
    await handler(mockReq({}), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('unknown token -> 404 UNKNOWN_TOKEN', async () => {
    delete require.cache[require.resolve('../_lib/dental-public')];
    require.cache[require.resolve('../_lib/dental-public')] = { exports: { checkAndIncrementRateLimit: async function () { return { allowed: true }; } } };
    global.fetch = async function () { return { ok: true, json: async function () { return []; } }; };
    delete require.cache[require.resolve('./public-complaint-thread.js')];
    var handler = require('./public-complaint-thread.js');
    var res = mockRes();
    await handler(mockReq({ token: 'no-such-token' }), res);
    assert.strictEqual(res.statusCode, 404);
    assert.strictEqual(res.body.error.code, 'UNKNOWN_TOKEN');
  });

  await test('reply over 4000 chars -> 400 MESSAGE_TOO_LONG, never calls fetch', async () => {
    delete require.cache[require.resolve('../_lib/dental-public')];
    require.cache[require.resolve('../_lib/dental-public')] = { exports: { checkAndIncrementRateLimit: async function () { throw new Error('should not be called -- length check comes first'); } } };
    global.fetch = function () { throw new Error('fetch should never be called for a request that fails validation'); };
    delete require.cache[require.resolve('./public-complaint-thread.js')];
    var handler = require('./public-complaint-thread.js');
    var res = mockRes();
    await handler(mockReq({ token: 'tok-1', reply: 'x'.repeat(4001) }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'MESSAGE_TOO_LONG');
  });

  await test('reply rate-limited -> 429, never calls fetch', async () => {
    delete require.cache[require.resolve('../_lib/dental-public')];
    require.cache[require.resolve('../_lib/dental-public')] = { exports: { checkAndIncrementRateLimit: async function () { return { allowed: false }; } } };
    global.fetch = function () { throw new Error('fetch should never be called once rate-limited'); };
    delete require.cache[require.resolve('./public-complaint-thread.js')];
    var handler = require('./public-complaint-thread.js');
    var res = mockRes();
    await handler(mockReq({ token: 'tok-1', reply: 'hi' }), res);
    assert.strictEqual(res.statusCode, 429);
    assert.strictEqual(res.body.error.code, 'RATE_LIMITED');
  });

  await test('load-only (no reply) never rate-limit-checked', async () => {
    var rlCalled = false;
    delete require.cache[require.resolve('../_lib/dental-public')];
    require.cache[require.resolve('../_lib/dental-public')] = { exports: { checkAndIncrementRateLimit: async function () { rlCalled = true; return { allowed: true }; } } };
    global.fetch = async function () { return { ok: true, json: async function () { return [{ license_hash: 'h', complaint_id: 'COMP-1', data: { status: 'New', patient_name: '', messages: [] } }]; } }; };
    delete require.cache[require.resolve('./public-complaint-thread.js')];
    var handler = require('./public-complaint-thread.js');
    var res = mockRes();
    await handler(mockReq({ token: 'tok-1' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(rlCalled, false);
  });

  console.log(passed + ' passed');
}

main();
```

- [ ] **Step 2: Run test to verify it fails**

```bash
node api/sairndental/public-complaint-thread.test.js
```

Expected: `Cannot find module './public-complaint-thread.js'`.

- [ ] **Step 3: Write the implementation**

```js
// api/sairndental/public-complaint-thread.js
// Genuinely public, unauthenticated endpoint. {token} loads a thread;
// {token, reply} also appends the patient's reply. Always does a
// fresh read of the current row immediately before writing (never
// trusts a client-supplied prior message list) -- the "server-side
// append" half of design spec §0's race-handling decision. Reopens a
// Resolved/Awaiting Patient thread back to 'New' on any patient reply
// -- the one uniform state rule from design spec §0, no special-
// casing per prior status.

const { checkAndIncrementRateLimit } = require('../_lib/dental-public');

function supabaseHeaders(extra) {
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return Object.assign({ apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' }, extra || {});
}
function rest(path) {
  return process.env.SUPABASE_URL + '/rest/v1/' + path;
}
const MAX_MESSAGE_LEN = 4000;

async function fetchByToken(token) {
  const r = await fetch(rest('dnt_complaints?access_token=eq.' + encodeURIComponent(token) + '&select=license_hash,complaint_id,data'), { headers: supabaseHeaders() });
  if (!r.ok) return null;
  const rows = await r.json();
  return (Array.isArray(rows) && rows[0]) || null;
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) { res.status(500).json({ error: { message: 'Server configuration error' } }); return; }

  const body = req.body || {};
  const token = body.token;
  const reply = typeof body.reply === 'string' ? body.reply.trim() : '';
  if (!token) { res.status(400).json({ error: { message: 'token is required' } }); return; }
  if (reply && reply.length > MAX_MESSAGE_LEN) { res.status(400).json({ error: { code: 'MESSAGE_TOO_LONG', message: 'Message is too long -- please keep it under ' + MAX_MESSAGE_LEN + ' characters' } }); return; }

  try {
    if (reply) {
      const rl = await checkAndIncrementRateLimit(req, 60, 20); // 20 replies per hour per IP
      if (!rl.allowed) { res.status(429).json({ error: { code: 'RATE_LIMITED', message: 'Too many messages -- please try again later' } }); return; }
    }

    // Fresh read, right before writing -- never the pre-request snapshot.
    const row = await fetchByToken(token);
    if (!row) { res.status(404).json({ error: { code: 'UNKNOWN_TOKEN', message: "This link isn't valid -- check that you copied it correctly" } }); return; }

    let data = row.data;
    if (reply) {
      const nowISO = new Date().toISOString();
      data = Object.assign({}, data, {
        messages: (data.messages || []).concat([{ from: 'patient', text: reply, at: nowISO }]),
        status: 'New'
      });
      const writeRes = await fetch(rest('dnt_complaints?on_conflict=license_hash,complaint_id'), {
        method: 'POST',
        headers: Object.assign({}, supabaseHeaders(), { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({ license_hash: row.license_hash, app_id: 'sairndental', complaint_id: row.complaint_id, access_token: token, data: data, updated_at: nowISO })
      });
      if (!writeRes.ok) {
        const errBody = await writeRes.json().catch(() => null);
        console.error('SAIRNdental public-complaint-thread write error:', errBody);
        res.status(502).json({ error: { message: 'Could not send -- try again' } });
        return;
      }
      const writtenRows = await writeRes.json();
      data = (Array.isArray(writtenRows) && writtenRows[0] && writtenRows[0].data) || data;
    }

    res.status(200).json({ ok: true, status: data.status, patient_name: data.patient_name, messages: data.messages });
  } catch (err) {
    console.error('SAIRNdental public-complaint-thread error:', err.message);
    res.status(502).json({ error: { message: 'Could not load -- try again' } });
  }
};
```

- [ ] **Step 4: Run test to verify it passes**

```bash
node api/sairndental/public-complaint-thread.test.js
```

Expected: `5 passed`, no `FAIL` lines.

- [ ] **Step 5: Syntax-check**

```bash
node --check api/sairndental/public-complaint-thread.js
```

- [ ] **Step 6: Commit**

```bash
git add api/sairndental/public-complaint-thread.js api/sairndental/public-complaint-thread.test.js
git commit -m "feat: SAIRNdental -- public-complaint-thread.js endpoint + tests"
```

---

### Task 5: `api/sairndental/complaint-respond.js` + race-handling regression test

**Files:**
- Create: `api/sairndental/complaint-respond.js`
- Test: `api/sairndental/complaint-respond.test.js`
- Test: `api/sairndental/complaint-race.test.js`

**Interfaces:**
- Consumes: `validateLicenseKey(key)` from `../_lib/license`
  (returns `{valid, active, license_hash, ...}`, unchanged).
- Produces: `POST {complaint_id, action:'reply'|'resolve', text?}`
  with `Authorization: Bearer <license_key>` → `{ok:true, status,
  messages}`. Task 7's staff panel calls this exact shape.

- [ ] **Step 1: Write the failing tests**

```js
// api/sairndental/complaint-respond.test.js
// Plain node:assert tests. Run: node api/sairndental/complaint-respond.test.js

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  return res;
}
function mockReq(body, authz) {
  return { method: 'POST', headers: authz ? { authorization: authz } : {}, body: body };
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
  console.log('api/sairndental/complaint-respond.js');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  await test('missing Authorization header -> 401 NO_LICENSE', async () => {
    delete require.cache[require.resolve('../_lib/license')];
    require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { throw new Error('should not be called with no header'); } } };
    delete require.cache[require.resolve('./complaint-respond.js')];
    var handler = require('./complaint-respond.js');
    var res = mockRes();
    await handler(mockReq({ complaint_id: 'COMP-1', action: 'reply', text: 'hi' }), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'NO_LICENSE');
  });

  await test('invalid license -> 401 INVALID_LICENSE', async () => {
    delete require.cache[require.resolve('../_lib/license')];
    require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { return { valid: false }; } } };
    delete require.cache[require.resolve('./complaint-respond.js')];
    var handler = require('./complaint-respond.js');
    var res = mockRes();
    await handler(mockReq({ complaint_id: 'COMP-1', action: 'reply', text: 'hi' }, 'Bearer BAD-KEY'), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'INVALID_LICENSE');
  });

  await test('inactive license -> 403 LICENSE_INACTIVE', async () => {
    delete require.cache[require.resolve('../_lib/license')];
    require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { return { valid: true, active: false }; } } };
    delete require.cache[require.resolve('./complaint-respond.js')];
    var handler = require('./complaint-respond.js');
    var res = mockRes();
    await handler(mockReq({ complaint_id: 'COMP-1', action: 'reply', text: 'hi' }, 'Bearer INACTIVE-KEY'), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(res.body.error.code, 'LICENSE_INACTIVE');
  });

  await test("action other than reply/resolve -> 400", async () => {
    delete require.cache[require.resolve('../_lib/license')];
    require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { return { valid: true, active: true, license_hash: 'h' }; } } };
    delete require.cache[require.resolve('./complaint-respond.js')];
    var handler = require('./complaint-respond.js');
    var res = mockRes();
    await handler(mockReq({ complaint_id: 'COMP-1', action: 'delete' }, 'Bearer GOOD-KEY'), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test("action:'reply' with no text -> 400", async () => {
    delete require.cache[require.resolve('../_lib/license')];
    require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { return { valid: true, active: true, license_hash: 'h' }; } } };
    delete require.cache[require.resolve('./complaint-respond.js')];
    var handler = require('./complaint-respond.js');
    var res = mockRes();
    await handler(mockReq({ complaint_id: 'COMP-1', action: 'reply' }, 'Bearer GOOD-KEY'), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('unknown complaint_id -> 404 NOT_FOUND', async () => {
    delete require.cache[require.resolve('../_lib/license')];
    require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { return { valid: true, active: true, license_hash: 'h' }; } } };
    global.fetch = async function () { return { ok: true, json: async function () { return []; } }; };
    delete require.cache[require.resolve('./complaint-respond.js')];
    var handler = require('./complaint-respond.js');
    var res = mockRes();
    await handler(mockReq({ complaint_id: 'NO-SUCH', action: 'resolve' }, 'Bearer GOOD-KEY'), res);
    assert.strictEqual(res.statusCode, 404);
    assert.strictEqual(res.body.error.code, 'NOT_FOUND');
  });

  console.log(passed + ' passed');
}

main();
```

```js
// api/sairndental/complaint-race.test.js
// Cross-endpoint regression test for design spec §0's race-handling
// decision: both public-complaint-thread.js (patient reply) and
// complaint-respond.js (owner reply) must each do a FRESH read
// immediately before writing, never trust a client-held/stale copy of
// the messages array -- otherwise a sequence of "patient replies,
// then owner replies" would silently lose the patient's message the
// moment the owner's request was built from state that predates it.
// Also covers the one state-transition rule from spec §0/§7.
// Run: node api/sairndental/complaint-race.test.js

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  res.setHeader = function () { return res; };
  res.end = function () { return res; };
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
  console.log('api/sairndental/complaint-race.test.js');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  // Shared in-memory "table" -- one row, mutated by whichever endpoint
  // writes to it, read fresh by the other. This is the actual thing
  // under test: does each endpoint re-read this shared state right
  // before it writes, or does it trust a value it already had?
  var store = {
    license_hash: 'abc123hash', complaint_id: 'COMP-1', access_token: 'tok-xyz',
    data: { id: 'COMP-1', patient_name: 'Jane', status: 'New', messages: [{ from: 'patient', text: 'Original complaint', at: '2026-08-12T10:00:00.000Z' }] }
  };

  global.fetch = async function (url, opts) {
    var u = String(url);
    if (!opts || !opts.method || opts.method === 'GET') {
      if (u.indexOf('access_token=eq.') !== -1 || u.indexOf('complaint_id=eq.') !== -1) {
        return { ok: true, json: async function () { return [Object.assign({}, store)]; } };
      }
    }
    if (opts && opts.method === 'POST') {
      var body = JSON.parse(opts.body);
      store = { license_hash: body.license_hash, complaint_id: body.complaint_id, access_token: body.access_token, data: body.data };
      return { ok: true, json: async function () { return [store]; } };
    }
    throw new Error('unexpected fetch: ' + u);
  };

  delete require.cache[require.resolve('../_lib/dental-public')];
  require.cache[require.resolve('../_lib/dental-public')] = { exports: { checkAndIncrementRateLimit: async function () { return { allowed: true }; } } };
  delete require.cache[require.resolve('../_lib/license')];
  require.cache[require.resolve('../_lib/license')] = { exports: { validateLicenseKey: async function () { return { valid: true, active: true, license_hash: 'abc123hash' }; } } };

  delete require.cache[require.resolve('./public-complaint-thread.js')];
  delete require.cache[require.resolve('./complaint-respond.js')];
  var threadHandler = require('./public-complaint-thread.js');
  var respondHandler = require('./complaint-respond.js');

  await test('patient reply, then owner reply -- both messages survive, in order', async () => {
    var threadRes = mockRes();
    await threadHandler({ method: 'POST', headers: {}, body: { token: 'tok-xyz', reply: 'Still waiting to hear back' } }, threadRes);
    assert.strictEqual(threadRes.statusCode, 200);
    assert.strictEqual(store.data.messages.length, 2);
    assert.strictEqual(store.data.status, 'New');

    var respondRes = mockRes();
    await respondHandler({ method: 'POST', headers: { authorization: 'Bearer DNT-TEST-KEY' }, body: { complaint_id: 'COMP-1', action: 'reply', text: 'Thanks, looking into it now' } }, respondRes);
    assert.strictEqual(respondRes.statusCode, 200);

    // The real regression: the owner's write must be built from a
    // FRESH read that already includes the patient's reply, not a
    // stale 1-message snapshot.
    assert.strictEqual(store.data.messages.length, 3);
    assert.strictEqual(store.data.messages[0].text, 'Original complaint');
    assert.strictEqual(store.data.messages[1].text, 'Still waiting to hear back');
    assert.strictEqual(store.data.messages[2].text, 'Thanks, looking into it now');
    assert.strictEqual(store.data.status, 'Awaiting Patient');
  });

  await test('patient reply after Resolved reopens to New (state-transition rule)', async () => {
    store.data.status = 'Resolved';
    var threadRes = mockRes();
    await threadHandler({ method: 'POST', headers: {}, body: { token: 'tok-xyz', reply: 'One more thing' } }, threadRes);
    assert.strictEqual(threadRes.statusCode, 200);
    assert.strictEqual(store.data.status, 'New');
  });

  await test("owner resolve with no text appends nothing, sets Resolved", async () => {
    var respondRes = mockRes();
    var before = store.data.messages.length;
    await respondHandler({ method: 'POST', headers: { authorization: 'Bearer DNT-TEST-KEY' }, body: { complaint_id: 'COMP-1', action: 'resolve' } }, respondRes);
    assert.strictEqual(respondRes.statusCode, 200);
    assert.strictEqual(store.data.messages.length, before);
    assert.strictEqual(store.data.status, 'Resolved');
  });

  console.log(passed + ' passed');
}

main();
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
node api/sairndental/complaint-respond.test.js
node api/sairndental/complaint-race.test.js
```

Expected: both fail with `Cannot find module './complaint-respond.js'`.

- [ ] **Step 3: Write the implementation**

```js
// api/sairndental/complaint-respond.js
// Authenticated (Bearer license key), but NOT part of
// api/sd-data.js's generic RESOURCES dispatch -- dnt_complaints is
// enforced read-only there (design spec §1). This is the dedicated,
// atomic (fresh read-then-write) endpoint for the owner's side of the
// thread: reply and/or resolve. Owner-only enforcement is UI-level
// only in the staff app (design spec §0) -- this endpoint itself only
// checks that the caller holds a valid, active license for this
// practice, same trust boundary as every other authenticated write on
// this platform.

const { validateLicenseKey } = require('../_lib/license');

function supabaseHeaders(extra) {
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return Object.assign({ apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' }, extra || {});
}
function rest(path) {
  return process.env.SUPABASE_URL + '/rest/v1/' + path;
}
const MAX_MESSAGE_LEN = 4000;

async function fetchByComplaintId(licenseHash, complaintId) {
  const r = await fetch(rest('dnt_complaints?license_hash=eq.' + encodeURIComponent(licenseHash) + '&complaint_id=eq.' + encodeURIComponent(complaintId) + '&select=complaint_id,access_token,data'), { headers: supabaseHeaders() });
  if (!r.ok) return null;
  const rows = await r.json();
  return (Array.isArray(rows) && rows[0]) || null;
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) { res.status(500).json({ error: { message: 'Server configuration error' } }); return; }

  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) { res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } }); return; }

  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    console.error('complaint-respond license validation error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error -- try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }

  const body = req.body || {};
  const complaintId = body.complaint_id;
  const action = body.action;
  const text = typeof body.text === 'string' ? body.text.trim() : '';
  if (!complaintId) { res.status(400).json({ error: { message: 'complaint_id is required' } }); return; }
  if (action !== 'reply' && action !== 'resolve') { res.status(400).json({ error: { message: "action must be 'reply' or 'resolve'" } }); return; }
  if (action === 'reply' && !text) { res.status(400).json({ error: { message: 'text is required for a reply' } }); return; }
  if (text.length > MAX_MESSAGE_LEN) { res.status(400).json({ error: { code: 'MESSAGE_TOO_LONG', message: 'Message is too long -- please keep it under ' + MAX_MESSAGE_LEN + ' characters' } }); return; }

  try {
    // Fresh read, right before writing -- the other half of design
    // spec §0's race-handling decision. Scoped by license_hash +
    // complaint_id together -- a valid key must never reach another
    // practice's record.
    const row = await fetchByComplaintId(lic.license_hash, complaintId);
    if (!row) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Complaint not found' } }); return; }

    const nowISO = new Date().toISOString();
    let messages = row.data.messages || [];
    if (action === 'reply' || (action === 'resolve' && text)) {
      messages = messages.concat([{ from: 'owner', text: text, at: nowISO }]);
    }
    const status = action === 'resolve' ? 'Resolved' : 'Awaiting Patient';
    const data = Object.assign({}, row.data, { messages: messages, status: status });

    const writeRes = await fetch(rest('dnt_complaints?on_conflict=license_hash,complaint_id'), {
      method: 'POST',
      headers: Object.assign({}, supabaseHeaders(), { Prefer: 'resolution=merge-duplicates,return=representation' }),
      body: JSON.stringify({ license_hash: lic.license_hash, app_id: 'sairndental', complaint_id: row.complaint_id, access_token: row.access_token, data: data, updated_at: nowISO })
    });
    if (!writeRes.ok) {
      const errBody = await writeRes.json().catch(() => null);
      console.error('SAIRNdental complaint-respond write error:', errBody);
      res.status(502).json({ error: { message: 'Could not save -- try again' } });
      return;
    }
    const writtenRows = await writeRes.json();
    const savedData = (Array.isArray(writtenRows) && writtenRows[0] && writtenRows[0].data) || data;
    res.status(200).json({ ok: true, status: savedData.status, messages: savedData.messages });
  } catch (err) {
    console.error('SAIRNdental complaint-respond error:', err.message);
    res.status(502).json({ error: { message: 'Could not save -- try again' } });
  }
};
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
node api/sairndental/complaint-respond.test.js
node api/sairndental/complaint-race.test.js
```

Expected: `6 passed` and `3 passed` respectively, no `FAIL` lines.

- [ ] **Step 5: Syntax-check**

```bash
node --check api/sairndental/complaint-respond.js
```

- [ ] **Step 6: Commit**

```bash
git add api/sairndental/complaint-respond.js api/sairndental/complaint-respond.test.js api/sairndental/complaint-race.test.js
git commit -m "feat: SAIRNdental -- complaint-respond.js endpoint + race-handling regression test"
```

---

### Task 6: Staff data layer (`complaints()`, `respondToComplaint()`)

**Files:** Modify `sairndental.html`

**Interfaces:**
- Consumes: existing `ld()`, `st()`, `toast()`, `dntLicenseKey()`,
  `prole`.
- Produces: `complaints()` — Task 7's `rComplaints()` reads this.
  `respondToComplaint(id, action)` — Task 7's Send Response/Mark
  Resolved buttons call this with exactly these two arguments.
  `COMPLAINT_RESPOND_API` — the URL constant Task 7's function uses.

- [ ] **Step 1: Add the API constant**

Locate `var DATA_API='https://sairn.vercel.app/api/sd-data';` and add
immediately after it:

```js
var COMPLAINT_RESPOND_API='https://sairn.vercel.app/api/sairndental/complaint-respond';
```

- [ ] **Step 2: Add the accessor and `respondToComplaint()`**

Locate `function referrals(){return ld('dnt_referrals_list',[]);}` and
insert immediately after it (before the "REFERRAL TRACKING" comment
block, so this new block sits between the two existing resource
sections rather than inside either):

```js
function complaints(){return ld('dnt_complaints_list',[]);}

// ── PATIENT COMPLAINTS (2026-08-12) ──────────────────────────────────
// dnt_complaints is READ-ONLY through sdnData()/api/sd-data.js's
// generic path (design spec §1) -- this function never calls
// sdnData('write','dnt_complaints',...). All real mutation goes
// through the dedicated complaint-respond.js endpoint, which does its
// own fresh read-then-write server-side (design spec §0). Owner-only
// enforcement is UI-level here (prole==='owner'), matching this app's
// existing role-gating convention -- see design spec §0 for why that's
// a stated, accepted limitation, not a gap.
async function respondToComplaint(id, action) {
  if (prole !== 'owner') { toast('Only the practice owner can respond'); return; }
  var text = '';
  if (action === 'reply') {
    var ta = $('cp-reply-' + id);
    text = ta ? ta.value.trim() : '';
    if (!text) { toast('Write a response first'); return; }
  }
  var lic = dntLicenseKey();
  if (!lic) { toast('Not logged in'); return; }
  try {
    var r = await fetch(COMPLAINT_RESPOND_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + lic },
      body: JSON.stringify({ complaint_id: id, action: action, text: text })
    });
    var d = await r.json();
    if (!r.ok || !d || !d.ok) { toast((d && d.error && d.error.message) || 'Could not save -- try again'); return; }
    var list = complaints();
    var c = list.find(function (x) { return x.id === id; });
    if (c) { c.status = d.status; c.messages = d.messages; st('dnt_complaints_list', list); }
    rComplaints();
    toast(action === 'resolve' ? 'Marked resolved' : 'Response sent');
  } catch (e) {
    toast('Could not connect -- check your connection and try again');
  }
}
```

- [ ] **Step 3: Structural checks**

```bash
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
python tools/duplicate_global_check.py sairndental.html
```

Expected: `FAILED_BLOCKS:0`, `RESULT:PASS`, `DUPLICATE_NAMES:0` on all
three (matches the clean baseline confirmed before this plan started).

- [ ] **Step 4: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- complaints() data layer + respondToComplaint()"
```

---

### Task 7: Complaints panel UI + nav badge

**Files:** Modify `sairndental.html`

**Interfaces:**
- Consumes: Task 6's `complaints()`, `respondToComplaint()`; existing
  `settings()`, `H()`, `prole`.
- Produces: `rComplaints()` and `rComplaintsBadge()` — Task 8's
  `nav()` dispatch and `dntSyncFromServer()` re-render block call
  `rComplaints()` (which internally calls `rComplaintsBadge()`).

- [ ] **Step 1: Add the `.badge br` red-pill styling check**

No new CSS needed — `.badge` (generic pill) and `.br` (red modifier,
`background:#FEE2E2;color:#991B1B`) both already exist in
`sairndental.html`'s stylesheet (confirmed by reading the file before
writing this plan). Skip straight to markup.

- [ ] **Step 2: Add the nav button with a live badge**

Locate `<button class="sb" id="sb-referrals" onclick="nav('referrals')"><span class="sico">&#128257;</span>Referrals</button>`
and insert immediately after it, still inside the same `Patients`
section:

```html
      <button class="sb" id="sb-complaints" onclick="nav('complaints')"><span class="sico">&#128172;</span>Complaints<span class="badge br" id="complaints-badge" style="display:none;margin-left:8px"></span></button>
```

- [ ] **Step 3: Add the panel HTML**

Locate the closing `</div>` of `panel-referrals` (immediately after
the `referrals-table` block, before `<div class="panel" id="panel-providers">`
— locate by content search for `panel-providers`) and insert this new
panel immediately before it:

```html
      <div class="panel" id="panel-complaints">
        <div class="ph"><div><div class="ptitle">Complaints</div><div class="psub">Anonymous-optional patient feedback, routed privately &mdash; every open thread needs a real owner response, not a passive drop-box.</div></div></div>
        <div class="card"><div class="cb">
          <div style="font-size:11px;color:var(--muted)" id="cp-link-preview"></div>
        </div></div>
        <div class="card"><div class="ch"><div class="ct">Threads</div></div><div class="cb" id="cp-list"></div></div>
      </div>
```

- [ ] **Step 4: Add `rComplaints()` and `rComplaintsBadge()`**

Locate `function rReferrals(){` and its closing `}` (ends with the
`No referrals on file yet` line), and insert this new block
immediately after it:

```js
function cpBadgeCount(){return complaints().filter(function(c){return c.status==='New';}).length;}
function rComplaintsBadge(){
  var n=cpBadgeCount();
  var b=$('complaints-badge');
  if(!b)return;
  if(n>0){b.textContent=String(n);b.style.display='inline-block';}else{b.style.display='none';}
}
function rComplaints(){
  rComplaintsBadge();
  var list=complaints().slice().sort(function(a,b){
    var order={'New':0,'Awaiting Patient':1,'Resolved':2};
    var byStatus=(order[a.status]||0)-(order[b.status]||0);
    if(byStatus!==0)return byStatus;
    return (b.updated_at||'').localeCompare(a.updated_at||'');
  });
  var s=settings();
  var linkEl=$('cp-link-preview');
  if(linkEl)linkEl.textContent=s.booking_slug?('Patient feedback link: sairn.vercel.app/sairndental-complaint?slug='+s.booking_slug):'Set a public link slug on the Booking Settings panel to get your patient feedback link.';
  var host=$('cp-list');
  if(!host)return;
  if(!list.length){host.innerHTML='<div style="color:var(--muted);text-align:center;padding:20px">No complaints on file yet</div>';return;}
  var isOwner=prole==='owner';
  host.innerHTML=list.map(function(c){
    var msgsHtml=(c.messages||[]).map(function(m){
      var who=m.from==='owner'?'Practice':(c.patient_name?H(c.patient_name):'Anonymous patient');
      return '<div style="margin-bottom:8px"><div style="font-size:11px;color:var(--muted);font-weight:600">'+who+' &middot; '+H(new Date(m.at).toLocaleString())+'</div><div style="font-size:13px">'+H(m.text)+'</div></div>';
    }).join('');
    var statusClass=c.status==='New'?'br':(c.status==='Resolved'?'bg':'bw');
    var respondHtml=isOwner?(
      '<div class="fg"><textarea id="cp-reply-'+c.id+'" rows="2" placeholder="Write a response..." style="width:100%;border:1px solid var(--border);border-radius:8px;padding:10px 12px;font-size:14px;font-family:inherit"></textarea></div>'+
      '<button class="btn bp bs" onclick="respondToComplaint(\''+c.id+'\',\'reply\')">Send Response</button> '+
      (c.status!=='Resolved'?'<button class="btn bo bs" onclick="respondToComplaint(\''+c.id+'\',\'resolve\')">Mark Resolved</button>':'')
    ):'<div style="font-size:12px;color:var(--muted)">Only the practice owner can respond.</div>';
    return '<div class="card" style="margin-bottom:12px"><div class="cb">'+
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">'+
      '<div style="font-weight:600">'+(c.patient_name?H(c.patient_name):'Anonymous')+'</div>'+
      '<span class="badge '+statusClass+'">'+H(c.status)+'</span></div>'+
      msgsHtml+respondHtml+'</div></div>';
  }).join('');
}
```

- [ ] **Step 5: Structural checks**

```bash
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
python tools/duplicate_global_check.py sairndental.html
```

Expected: `FAILED_BLOCKS:0`, `RESULT:PASS`, `DUPLICATE_NAMES:0`.

- [ ] **Step 6: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- Complaints panel UI + persistent nav badge"
```

---

### Task 8: Sync integration + nav dispatch

**Files:** Modify `sairndental.html`

**Interfaces:**
- Consumes: Task 6/7's `complaints()`, `rComplaints()`.
- Produces: `dnt_complaints` genuinely participates in
  `dntSyncFromServer()`'s sweep — nothing downstream depends on this
  beyond correctness itself; this is the last wiring step.

- [ ] **Step 1: Add to `DNT_SYNC_RESOURCES`**

Locate the `DNT_SYNC_RESOURCES` array (contains
`['dnt_referrals','dnt_referrals_list']` as its last entry) and add a
new entry immediately after it:

```js
  ['dnt_referrals','dnt_referrals_list'],
  ['dnt_complaints','dnt_complaints_list']
```

(i.e. add a trailing comma to the existing `dnt_referrals` line and
add the new line, keeping the array's closing `];` where it was.)

- [ ] **Step 2: Add to the re-render block**

Locate
`rCoverage();rPending();rAppointments();rBilling();rReferrals();` in
`dntSyncFromServer()` and change it to:

```js
    rCoverage();rPending();rAppointments();rBilling();rReferrals();rComplaints();
```

- [ ] **Step 3: Add to `nav()`'s dispatch**

Locate `if(id==='referrals')rReferrals();` inside `function nav(id){`
and add immediately after it:

```js
  if(id==='complaints')rComplaints();
```

- [ ] **Step 4: Structural checks**

```bash
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
python tools/duplicate_global_check.py sairndental.html
```

Expected: `FAILED_BLOCKS:0`, `RESULT:PASS`, `DUPLICATE_NAMES:0`.

- [ ] **Step 5: Commit**

```bash
git add sairndental.html
git commit -m "feat: SAIRNdental -- wire dnt_complaints into the real-sync sweep and nav dispatch"
```

---

### Task 9: Public page `sairndental-complaint.html`

**Files:**
- Create: `sairndental-complaint.html`

**Interfaces:**
- Consumes: Task 3's `public-complaint-submit.js` (`{slug, message,
  patient_name}` → `{ok, token}`) and Task 4's
  `public-complaint-thread.js` (`{token, reply?}` → `{ok, status,
  patient_name, messages}`).
- Produces: the patient-facing page itself — nothing downstream in
  this plan depends on it, but it must never expose the practice's
  license key (regression-tested live in Task 10, matching
  `sairndental-book.html`'s own precedent check).

- [ ] **Step 1: Write the page**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Patient Feedback</title>
<style>
:root{--p:#0EA5E9;--pd:#0284C7;--pt:#E0F2FE;--bg:#F8FAFC;--card:#fff;--border:#E2E8F0;--text:#0F172A;--muted:#64748B;--danger:#EF4444;--sh:0 1px 4px rgba(0,0,0,.08);}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);font-size:15px;}
.wrap{max-width:560px;margin:0 auto;padding:32px 20px 60px;}
.logo{font-size:22px;font-weight:800;color:var(--pd);text-align:center;margin-bottom:4px;}
.sub{color:var(--muted);font-size:13px;text-align:center;margin-bottom:28px;}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:var(--sh);}
.fg{margin-bottom:14px;}
label{display:block;font-size:12px;font-weight:600;color:var(--muted);margin-bottom:5px;text-transform:uppercase;letter-spacing:.4px;}
input,textarea{width:100%;border:1px solid var(--border);border-radius:8px;padding:10px 12px;font-size:14px;outline:none;background:#fff;font-family:inherit;}
input:focus,textarea:focus{border-color:var(--p);}
.btn{border:none;border-radius:8px;padding:11px 18px;font-size:14px;font-weight:600;cursor:pointer;background:var(--p);color:#fff;width:100%;}
.btn:hover{background:var(--pd);}
.btn:disabled{opacity:.5;cursor:not-allowed;}
.msg{font-size:13px;color:var(--muted);text-align:center;padding:10px;}
.msg.err{color:var(--danger);}
.msg.ok{background:var(--pt);color:var(--pd);border-radius:8px;padding:16px;font-weight:600;}
.step{display:none;}
.step.on{display:block;}
.thread-msg{margin-bottom:12px;}
.thread-who{font-size:11px;color:var(--muted);font-weight:600;margin-bottom:2px;}
.thread-text{font-size:14px;}
.token-box{background:var(--pt);border-radius:8px;padding:14px;font-size:12px;word-break:break-all;margin-bottom:14px;}
</style>
</head>
<body>
<div class="wrap">
  <div class="logo">Patient Feedback</div>
  <div class="sub">Private, direct to the practice owner</div>

  <div id="step-loading" class="step on"><div class="msg" id="loading-msg">Loading...</div></div>

  <div id="step-submit" class="step">
    <div class="card">
      <div class="fg"><label>Your Message</label><textarea id="cp-message" rows="5" placeholder="Tell us what happened..."></textarea></div>
      <div class="fg"><label>Your Name (optional)</label><input type="text" id="cp-name" placeholder="Leave blank to stay anonymous"></div>
      <button class="btn" id="cp-submit-btn" onclick="submitComplaint()">Send</button>
      <div class="msg" id="cp-submit-msg"></div>
    </div>
  </div>

  <div id="step-submitted" class="step">
    <div class="card">
      <div class="msg ok">Your message has been sent to the practice owner.</div>
      <div class="fg" style="margin-top:16px"><label>Save This Link</label></div>
      <div class="token-box" id="cp-saved-link"></div>
      <div class="msg">Bookmark this link or write it down &mdash; it's the only way to see the practice's response and reply. There is no way to recover it if you lose it.</div>
    </div>
  </div>

  <div id="step-thread" class="step">
    <div class="card">
      <div style="font-size:12px;color:var(--muted);font-weight:600;margin-bottom:4px" id="cp-thread-status"></div>
      <div id="cp-thread-messages"></div>
    </div>
    <div class="card">
      <div class="fg"><label>Reply</label><textarea id="cp-thread-reply" rows="3" placeholder="Write a reply..."></textarea></div>
      <button class="btn" id="cp-thread-reply-btn" onclick="submitThreadReply()">Send Reply</button>
      <div class="msg" id="cp-thread-msg"></div>
    </div>
  </div>
</div>

<script>
var SUBMIT_API='https://sairn.vercel.app/api/sairndental/public-complaint-submit';
var THREAD_API='https://sairn.vercel.app/api/sairndental/public-complaint-thread';
var params=new URLSearchParams(window.location.search);
var slug=params.get('slug');
var token=params.get('token');

function showStep(id){
  document.querySelectorAll('.step').forEach(function(s){s.classList.remove('on');});
  document.getElementById('step-'+id).classList.add('on');
}
function esc(s){var d=document.createElement('div');d.textContent=String(s==null?'':s);return d.innerHTML;}

function init(){
  if(token){loadThread();return;}
  if(slug){showStep('submit');return;}
  document.getElementById('loading-msg').textContent='No link provided. Ask your practice for their real feedback link.';
  document.getElementById('loading-msg').className='msg err';
}

async function submitComplaint(){
  var message=document.getElementById('cp-message').value.trim();
  var name=document.getElementById('cp-name').value.trim();
  var msgEl=document.getElementById('cp-submit-msg');
  if(!message){msgEl.textContent='Please write a message first.';msgEl.className='msg err';return;}
  var btn=document.getElementById('cp-submit-btn');
  btn.disabled=true;btn.textContent='Sending...';msgEl.textContent='';
  try{
    var res=await fetch(SUBMIT_API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slug:slug,message:message,patient_name:name})});
    var data=await res.json();
    if(!res.ok||!data.ok){
      msgEl.textContent=(data.error&&data.error.message)||'Could not send -- try again';
      msgEl.className='msg err';
      btn.disabled=false;btn.textContent='Send';
      return;
    }
    var link=window.location.origin+window.location.pathname+'?token='+data.token;
    document.getElementById('cp-saved-link').textContent=link;
    showStep('submitted');
  }catch(e){
    msgEl.textContent='Could not connect. Check your connection and try again.';msgEl.className='msg err';
    btn.disabled=false;btn.textContent='Send';
  }
}

function renderThread(data){
  document.getElementById('cp-thread-status').textContent='Status: '+data.status;
  document.getElementById('cp-thread-messages').innerHTML=(data.messages||[]).map(function(m){
    var who=m.from==='owner'?'Practice':'You';
    return '<div class="thread-msg"><div class="thread-who">'+esc(who)+' &middot; '+esc(new Date(m.at).toLocaleString())+'</div><div class="thread-text">'+esc(m.text)+'</div></div>';
  }).join('');
  showStep('thread');
}

async function loadThread(){
  try{
    var res=await fetch(THREAD_API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:token})});
    var data=await res.json();
    if(!res.ok||!data.ok){
      document.getElementById('loading-msg').textContent=(data.error&&data.error.message)||"This link isn't valid.";
      document.getElementById('loading-msg').className='msg err';
      return;
    }
    renderThread(data);
  }catch(e){
    document.getElementById('loading-msg').textContent='Could not connect. Check your connection and try again.';
    document.getElementById('loading-msg').className='msg err';
  }
}

async function submitThreadReply(){
  var reply=document.getElementById('cp-thread-reply').value.trim();
  var msgEl=document.getElementById('cp-thread-msg');
  if(!reply){msgEl.textContent='Write a reply first.';msgEl.className='msg err';return;}
  var btn=document.getElementById('cp-thread-reply-btn');
  btn.disabled=true;btn.textContent='Sending...';msgEl.textContent='';
  try{
    var res=await fetch(THREAD_API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:token,reply:reply})});
    var data=await res.json();
    if(!res.ok||!data.ok){
      msgEl.textContent=(data.error&&data.error.message)||'Could not send -- try again';
      msgEl.className='msg err';
      btn.disabled=false;btn.textContent='Send Reply';
      return;
    }
    document.getElementById('cp-thread-reply').value='';
    btn.disabled=false;btn.textContent='Send Reply';
    renderThread(data);
  }catch(e){
    msgEl.textContent='Could not connect. Check your connection and try again.';msgEl.className='msg err';
    btn.disabled=false;btn.textContent='Send Reply';
  }
}

init();
</script>
</body>
</html>
```

- [ ] **Step 2: Structural self-check**

This is a standalone page, not part of `sairndental.html`, so the repo's
`tools/*.py` checks (written for the main app file) don't apply. Read
the file back once and confirm every opened tag has a matching close
and every `id=` referenced in the `<script>` block exists in the HTML
above it (`step-loading`, `step-submit`, `step-submitted`,
`step-thread`, `cp-message`, `cp-name`, `cp-submit-btn`,
`cp-submit-msg`, `cp-saved-link`, `cp-thread-status`,
`cp-thread-messages`, `cp-thread-reply`, `cp-thread-reply-btn`,
`cp-thread-msg`).

- [ ] **Step 3: Confirm no vercel.json change is needed**

`vercel.json`'s `buildCommand` already does `cp *.html dist/` (a
wildcard, fixed for exactly this reason during the availability-
booking feature — see
`docs/superpowers/specs/2026-08-10-sairndental-availability-booking-design.md`).
Read `vercel.json` back and confirm the wildcard is still there, not a
re-narrowed explicit list — if it's been narrowed since, add
`sairndental-complaint.html` explicitly and note that as a real,
separate fix in Task 10.

- [ ] **Step 4: Commit**

```bash
git add sairndental-complaint.html
git commit -m "feat: SAIRNdental -- public patient complaint page (submit + thread view/reply)"
```

---

### Task 10: End-to-end verification, push, live-verify

- [ ] **Step 1:** Confirm the migration has actually been run in
  Supabase before live-testing (this repo's standing convention — SQL
  files are committed but run manually; `dnt_complaints` reads/writes
  will return `NOT_PROVISIONED`/`503` until it has). If not yet run,
  surface this plainly rather than assuming.
- [ ] **Step 2:** Full local re-check: `checkblocks.py` /
  `div_balance_check.py` / `duplicate_global_check.py` on
  `sairndental.html`; `node --check` on `api/sd-data.js` and all five
  new `.js` files under `api/sairndental/`; run all four new test
  files (`public-complaint-submit.test.js`,
  `public-complaint-thread.test.js`, `complaint-respond.test.js`,
  `complaint-race.test.js`) and confirm zero `FAIL` lines across all.
- [ ] **Step 3:** Push to `main`.
- [ ] **Step 4: Live RESOURCES-gate check (the actual regression test
  for Task 2's Step 2 — this exact bug class already happened once for
  `dnt_referrals`).** `curl` a `POST` to `https://sairn.vercel.app/api/sd-data`
  with a bogus bearer token and `resource:'dnt_complaints'`; confirm
  the response is **not** `"resource must be one of..."` (which would
  mean the allowlist edit was missed) — some other error (license/auth)
  is expected and correct.
- [ ] **Step 5: Live read-only enforcement check.** Using the real
  `DNT-PINNACLE-2026` demo practice's license key, `POST` to
  `api/sd-data` with `{action:'write', resource:'dnt_complaints',
  payload:{id:'x'}}`; confirm a real `400 READ_ONLY_RESOURCE`, not a
  silent success.
- [ ] **Step 6: Live end-to-end submission + thread test.** Get the
  demo practice's real `booking_slug` from its Booking Settings panel.
  Visit `sairndental-complaint.html?slug=<that slug>` in a real
  browser, submit a message with no name (anonymous path), confirm the
  saved-link screen shows a real token URL. Open that URL in a fresh
  private/incognito window, confirm the original message renders.
  Reply as the patient, confirm it appears and the thread persists on
  reload.
- [ ] **Step 7: Live owner-response + nav-badge test.** Log into the
  demo practice as `owner` (PIN `1234` unless changed), open the
  Complaints panel, confirm the new thread shows with a `New` badge and
  the nav badge count is at least 1. Send a response, confirm the nav
  badge count decreases and the panel shows `Awaiting Patient`. Reload
  the patient's token URL, confirm the owner's response appears there.
- [ ] **Step 8: Live reopen-on-reply test (the actual test for the
  state-transition rule).** As the owner, mark the same thread
  Resolved; confirm the nav badge doesn't count it. As the patient (via
  the token URL), send one more reply; confirm the thread flips back to
  `New` and the nav badge count increases again on the staff side after
  a sync/refresh.
- [ ] **Step 9: Live non-owner gate test.** Log out, log back in as
  `frontdesk` (PIN `2345` unless changed), open the Complaints panel,
  confirm the respond/resolve controls are absent and the "Only the
  practice owner can respond" message shows instead.
- [ ] **Step 10: License-key exposure check (the actual test for
  `sairndental-book.html`'s own precedent).** View source / inspect
  network requests on the live `sairndental-complaint.html` page;
  confirm the practice's license key never appears anywhere in the
  served HTML, JS, or any request payload.
- [ ] **Step 11:** Delete any test complaint records created in Steps
  6-9 — per the already-logged platform-wide limitation, there is no
  delete API anywhere on this platform, so this means reporting the
  exact `complaint_id`s for manual Supabase-dashboard deletion, the
  same honest limitation already disclosed for referrals.
- [ ] **Step 12:** Update
  `docs/superpowers/specs/2026-08-12-sairndental-complaint-design.md`'s
  status line with the real commit SHAs and confirmed-live date.

---

**Not started. Awaiting explicit go-ahead before any code in Tasks
1-10 is written**, per standing instruction.
