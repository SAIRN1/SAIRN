// api/claude-licence-enforce.test.js
// REQUIREMENT: a REVOKED licence is refused in enforce mode, and is never
//   budgeted as though it were a current one
//
// Run:  node api/claude-licence-enforce.test.js
//
// ── THE DEFECT ─────────────────────────────────────────────────────────────
// api/claude.js:309 derives three states from the licence:
//
//     authState = lic.valid ? (lic.active ? 'valid' : 'inactive') : 'invalid'
//
// so `inactive` -- a licence that EXISTS and has been REVOKED -- is computed.
// Two places then fail to use it:
//
//   :325  the enforce-mode refusal reads
//         `authState === 'absent' || authState === 'invalid'`.
//         A REVOKED LICENCE IS IN NEITHER LIST and is served.
//   :430  `if (authState === 'valid' || authState === 'inactive')` keeps
//         `budgetApp` as the LICENSED app, so a revoked tenant draws on the
//         ceiling that app's paying tenants share, rather than the
//         `anon:<app_id>` pool the comment above it reserves for callers
//         without a valid licence.
//
// `status` is the platform's ONLY licence revocation control -- license_keys
// has no expiry the code enforces -- so being revoked is the entire mechanism
// for cutting off a cancelled, refunded or charged-back account.
//
// ── THE TWO HALVES ARE DIFFERENT KINDS OF DEFECT, AND BOTH ARE HELD HERE ───
// THE REFUSAL is LATENT: SAIRN_CLAUDE_AUTH_MODE defaults to `observe`, so
// nothing is refused today. It arms itself on an ENV VAR rather than on a
// reviewed code change, which is the worst shape for a latent defect -- the
// change that turns it on will not be read as code.
//
// THE BUDGET IS LIVE IN BOTH MODES. Observe mode still serves the request and
// still charges it to the licensed app's pool.
//
// So the arms below drive BOTH env states explicitly. `claudeAuthMode` is read
// inside the handler on every request, so flipping the variable between calls
// is a real mode change and not a module-load artefact -- asserted by arm E0.

'use strict';
const assert = require('assert');

let pass = 0;
const run = [];
function t(name, fn) { run.push([name, fn]); }
function section(s) { run.push([s, null]); }

// ── STUBS, IN THE REQUIRE CACHE BEFORE THE HANDLER LOADS ───────────────────
// Same reason api/claude-cost-controls.test.js does it: the handler
// destructures both at module load, and on a machine with no SUPABASE_URL the
// real licence lookup throws, which would collapse every auth state to `error`
// and make this suite pass whatever the logic does.
const LIMITER = require.resolve('./_lib/ai-rate-limit');
let limiterCalls = [];
require.cache[LIMITER] = {
  id: LIMITER, filename: LIMITER, loaded: true,
  exports: {
    checkAiRateLimit: async (appId, tenantKey) => {
      limiterCalls.push({ appId, tenantKey });
      return { allowed: true, rowId: 'row-1', degraded: false };
    },
    recordAiUsage: async () => {},
  },
};

const LICENCE = require.resolve('./_lib/license');
let licenceAnswer = { valid: true, active: true, license_hash: 'h-live', app_id: 'stonedesk' };
let licenceThrows = false;
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: {
    validateLicenseKey: async () => {
      if (licenceThrows) { const e = new Error('upstream'); e.code = 'UPSTREAM'; throw e; }
      return licenceAnswer;
    },
  },
};

process.env.ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY || 'test-key';
process.env.SAIRN_CLAUDE_AUTH_MODE = 'observe';

delete require.cache[require.resolve('./claude.js')];
const handler = require('./claude.js');

// Anthropic is stubbed: this suite must never make a real paid call.
global.fetch = async function (_url, opts) {
  JSON.parse(opts.body);
  return {
    ok: true, status: 200,
    json: async () => ({ content: [{ type: 'text', text: 'ok' }],
                         usage: { input_tokens: 1, output_tokens: 1 } }),
  };
};

function mockRes() {
  const res = { _s: 0, _j: null };
  res.status = function (c) { res._s = c; return res; };
  res.json = function (o) { res._j = o; return res; };
  res.setHeader = function () { return res; };
  return res;
}

const MSG = [{ role: 'user', content: 'hi' }];

async function call(mode, licence, opts) {
  opts = opts || {};
  process.env.SAIRN_CLAUDE_AUTH_MODE = mode;
  licenceAnswer = licence;
  licenceThrows = !!opts.throws;
  limiterCalls = [];
  const headers = opts.noKey ? {} : { authorization: 'Bearer some-key' };
  const res = mockRes();
  await handler({ method: 'POST', headers,
                  body: { app_id: 'stonedesk', messages: MSG } }, res);
  licenceThrows = false;
  return { status: res._s, body: res._j, budget: limiterCalls[0] };
}

const REVOKED = { valid: true, active: false, license_hash: 'h-rev', app_id: 'stonedesk' };
const CURRENT = { valid: true, active: true, license_hash: 'h-live', app_id: 'stonedesk' };
const UNKNOWN = { valid: false, active: false, license_hash: null, app_id: null };

section('--- E. the env var really switches modes per request ---');

t('E0. observe and enforce differ for an ABSENT licence -- if this arm fails, '
  + 'every mode arm below is measuring one mode twice', async () => {
    const obs = await call('observe', CURRENT, { noKey: true });
    const enf = await call('enforce', CURRENT, { noKey: true });
    assert.strictEqual(obs.status, 200,
      'observe mode refused an unauthenticated caller: ' + JSON.stringify(obs.body));
    assert.strictEqual(enf.status, 401,
      'enforce mode did not refuse an unauthenticated caller, so the variable '
      + 'is not being read per request: ' + JSON.stringify(enf.body));
  });

section('--- A. a REVOKED licence is refused in enforce mode ---');

t('A1. THE ARM THIS FILE EXISTS FOR: enforce mode REFUSES a licence that '
  + 'exists and has been revoked', async () => {
    const r = await call('enforce', REVOKED);
    assert.notStrictEqual(r.status, 200,
      'a REVOKED licence was served in enforce mode. `status` is the only '
      + 'revocation control this platform has, so this is the whole mechanism '
      + 'for cutting off a cancelled or charged-back account.');
    assert.strictEqual(r.status, 403,
      'expected 403 (the licence is real and withdrawn) rather than '
      + r.status + '. 401 would tell the caller to supply a licence they '
      + 'already have.');
    assert.ok(r.body && r.body.error && /INACTIVE/.test(r.body.error.code || ''),
      'the refusal does not name the reason, so a support call cannot tell '
      + 'revoked from wrong-key: ' + JSON.stringify(r.body));
  });

t('A2. ...and it is refused BEFORE any paid call is made', async () => {
    const r = await call('enforce', REVOKED);
    assert.strictEqual(r.budget, undefined,
      'the rate limiter ran for a revoked licence, so the request reached the '
      + 'spending path before being refused');
  });

section('--- B. the controls: the fix must not refuse anybody else ---');

t('B1. a CURRENT licence still works in enforce mode', async () => {
    const r = await call('enforce', CURRENT);
    assert.strictEqual(r.status, 200, JSON.stringify(r.body));
  });

t('B2. an ABSENT licence still gets 401 in enforce mode, not the new code',
  async () => {
    const r = await call('enforce', CURRENT, { noKey: true });
    assert.strictEqual(r.status, 401);
    assert.strictEqual(r.body.error.code, 'NO_LICENSE');
  });

t('B3. an UNKNOWN key still gets 401, and is not reported as revoked',
  async () => {
    const r = await call('enforce', UNKNOWN);
    assert.strictEqual(r.status, 401);
    assert.strictEqual(r.body.error.code, 'NO_LICENSE');
  });

t('B4. OUR OWN OUTAGE DOES NOT DEMOTE A CUSTOMER: when the licence store '
  + 'cannot be read, enforce mode still serves', async () => {
    const r = await call('enforce', CURRENT, { throws: true });
    assert.strictEqual(r.status, 200,
      'an unreachable licence store refused a paying customer -- punishing '
      + 'them for our failure, which this handler already decided against');
  });

t('B5. observe mode refuses NOBODY, including a revoked licence -- the mode '
  + 'is what changes, not the classification', async () => {
    const r = await call('observe', REVOKED);
    assert.strictEqual(r.status, 200,
      'observe mode refused, which would break every live app the day this '
      + 'lands: ' + JSON.stringify(r.body));
  });

section('--- C. the LIVE half: a revoked licence is not budgeted as current ---');

t('C1. in OBSERVE mode a revoked licence does NOT draw on the licensed app\'s '
  + 'pool', async () => {
    const r = await call('observe', REVOKED);
    assert.ok(r.budget, 'the limiter did not run at all');
    assert.notStrictEqual(r.budget.appId, 'stonedesk',
      'a revoked tenant is charged to the ceiling stonedesk\'s PAYING tenants '
      + 'share. The comment above that branch reserves anon:<app_id> for '
      + 'callers without a valid licence, and a withdrawn licence is not a '
      + 'valid entitlement.');
    assert.strictEqual(r.budget.appId, 'anon:stonedesk');
  });

t('C2. CONTROL: a CURRENT licence IS charged to its own app, so C1 is not a '
  + 'rule that sends everybody to the anonymous pool', async () => {
    const r = await call('observe', CURRENT);
    assert.strictEqual(r.budget.appId, 'stonedesk');
    assert.strictEqual(r.budget.tenantKey, 'h-live',
      'a current licence lost its tenant sub-budget');
  });

t('C3. CONTROL: an ABSENT licence is still anon, unchanged by this fix',
  async () => {
    const r = await call('observe', CURRENT, { noKey: true });
    assert.strictEqual(r.budget.appId, 'anon:stonedesk');
  });

t('C4. and OUR OUTAGE still keeps the claimed app -- the error state is not '
  + 'swept into the revoked one', async () => {
    const r = await call('observe', CURRENT, { throws: true });
    assert.strictEqual(r.budget.appId, 'stonedesk',
      'a licence store we could not read demoted a customer to the anonymous '
      + 'pool, which is the behaviour the handler explicitly rejected');
  });

(async () => {
  console.log('api/claude.js -- a REVOKED licence, in both auth modes\n');
  for (const [name, fn] of run) {
    if (!fn) { console.log(name); continue; }
    try {
      await fn();
      pass++;
      console.log('  ok   ' + name);
    } catch (err) {
      process.exitCode = 1;
      console.log('  FAIL ' + name);
      console.log('       ' + err.message);
    }
  }
  console.log('\n' + pass + ' passed'
    + (process.exitCode ? ', with failures above' : ''));
})();
