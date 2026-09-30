// api/sd-data-mech-session-gate.test.js
//
// REQUIREMENT: `mech_docs write` needs an employee session, not just the
//   licence key. The licence key is shipped to the browser; it is an
//   identifier for the tenant, never proof of who is asking.
//
// Run:  node api/sd-data-mech-session-gate.test.js
//
// ── THE EXPOSURE THIS CLOSES ──────────────────────────────────────────────
// `MECH_RECORDS` gates all four of mech_quotes, mech_checks, mech_docs and
// mech_takeoffs on the licence alone, and the comment above it reasons that
// "a quote or a cheque stub is not a credential". That is true about
// CREDENTIALS. It does not answer what mech_docs actually holds.
//
// mech_docs is the one of the four whose own server-side redactor
// (api/_lib/mech-redact.js) carries patterns for SSN, EIN and card-length digit
// runs -- because scanDoc() asks a model to "EXTRACT: Every field -- names,
// dates, amounts, codes, reference numbers" off work orders, contracts, permits
// and INVOICES, and the answer is stored. The redactor REDUCES text and NEVER
// REFUSES A WRITE, deliberately, and its own header says so. So it is not the
// gate, and until this change there was no gate: anyone holding the licence key
// could write into the table whose contents the platform has already decided
// need redacting.
//
// ── THE FIX IS A REGISTRY ENTRY, NOT A BESPOKE INLINE GATE ────────────────
// `mech_docs: ['write']` in SD_SESSION_GATED plus `mech_docs: 'sairnmechanical'`
// in SD_GATE_APP. That shape inherits the active-credential pre-gate for free,
// and it is the shape every other app's gating already uses. A hand-written
// `if (!session)` inside the MECH_RECORDS branch would be a second place for
// the same rule to live.
//
// ── AND THE TWO LISTS ARE NEVER GROWN ONE HALF AT A TIME ──────────────────
// SD_GATE_APP's own comment says why, and this repo has paid for it twice:
// a resource gated with no SD_GATE_APP entry resolves expectedApp to
// 'stonedesk', so every correctly signed-in SAIRNmechanical technician is
// refused FORBIDDEN "sign in first". That fails CLOSED and CONFUSINGLY, which
// is the way a security change gets reverted as broken rather than fixed.
// `sf_trustee_audits` was in exactly that state on main on 2026-09-29.
// Arm 2 below drives the RIGHT app and requires it through, which is the arm
// that catches a missing SD_GATE_APP entry.
//
// ── SCOPE IS THE WRITE, AND ONLY THE WRITE, AND ONLY mech_docs ────────────
// Two things are deliberately NOT changed, and arms 3 and 4 hold them there
// rather than leaving it to intention:
//
//   * mech_docs READ stays licence-only. The reported finding is the WRITE.
//   * mech_quotes, mech_checks and mech_takeoffs stay licence-only. Each is its
//     own open-work row -- mech_checks in particular, whose branch comment
//     calls the cheque register "the sharp one". Widening a gate past the row
//     that justified it is the scope growth this platform refuses, and three
//     more tables silently closing is how a narrow fix becomes an outage
//     somebody reverts wholesale.
//
// VERIFIED SAFE FOR THE APP BEFORE CHANGING IT, not after: mechData() calls
// mechHeaders(true) and attaches X-SD-Auth whenever a session exists, and the
// doc scanner sits behind mechEnter(), which only runs after login. No
// signed-in user loses anything; only the licence-key-alone path closes.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['mech', 'docs', 'gate', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { signSessionToken } = require('./_lib/auth');

const HASH = 'mech-docs-gate-hash';
const APP = 'sairnmechanical';
const ME = 'emp-tech-1';

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

function postgrestMock(calls) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, opts: opts || null });
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: HASH, employee_id: ME, role: 'owner', active: true }]; } };
    }
    if (opts && opts.method === 'POST') {
      return { ok: true, status: 200, json: async function () { return [JSON.parse(opts.body)]; } };
    }
    return { ok: true, status: 200, json: async function () { return []; } };
  };
}

function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: HASH,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: APP };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

// `sessionApp` null means NO session token at all -- the licence-key-alone
// caller this whole file is about.
async function call(action, resource, sessionApp, payload) {
  const calls = [];
  const h = loadHandler(postgrestMock(calls));
  const res = mockRes();
  const headers = { authorization: 'Bearer KEY-FOR-' + HASH };
  if (sessionApp) {
    headers['x-sd-auth'] = signSessionToken({
      app: sessionApp, employee_id: ME, role: 'owner', license_hash: HASH });
  }
  await h({
    method: 'POST', headers: headers,
    body: { action: action, resource: resource, app_id: APP,
            payload: payload === undefined ? { id: 'D-1', text: 'plain' } : payload }
  }, res);
  const wrote = calls.some(function (c) {
    return c.opts && c.opts.method === 'POST' && new RegExp(resource).test(c.url);
  });
  return { res: res, wrote: wrote };
}

const SD = path.join(__dirname, 'sd-data.js');
const CODE = fs.readFileSync(SD, 'utf8');

function registryBlock(name) {
  const i = CODE.indexOf('const ' + name + ' = {');
  if (i < 0) return null;
  const j = CODE.indexOf('\n    };', i);
  return j < 0 ? null : CODE.slice(i, j);
}

(async () => {

section('1. THE DEFECT -- mech_docs WRITE on the licence key alone');

await test('no session token: the write is REFUSED', async () => {
  const r = await call('write', 'mech_docs', null);
  assert.ok(r.res.statusCode === 401 || r.res.statusCode === 403,
    'status ' + r.res.statusCode + ' with body ' + JSON.stringify(r.res.body)
    + ' -- the licence key alone reached the write on the one mech_ table whose '
    + 'own redactor has SSN, EIN and card-number patterns');
});

await test('...and NOTHING was written -- a refusal that still stores is not a '
  + 'refusal', async () => {
    const r = await call('write', 'mech_docs', null);
    assert.strictEqual(r.wrote, false,
      'a POST to mech_docs was issued despite the refusal status');
  });

await test('a session for the WRONG app does not open it either', async () => {
  const r = await call('write', 'mech_docs', 'stonedesk');
  assert.strictEqual(r.res.statusCode, 403,
    'status ' + r.res.statusCode + ' -- a StoneDesk token was accepted against a '
    + 'SAIRNmechanical resource');
  assert.strictEqual(r.wrote, false, 'a cross-app token reached the write');
});

section('2. THE ARM THAT CATCHES THE HALF-GROWN PAIR OF LISTS');

await test('a correctly signed-in SAIRNmechanical session IS let through -- this '
  + 'fails if SD_GATE_APP has no mech_docs entry and expectedApp falls back to '
  + 'stonedesk', async () => {
    const r = await call('write', 'mech_docs', APP);
    assert.strictEqual(r.res.statusCode, 200,
      'status ' + r.res.statusCode + ' with body ' + JSON.stringify(r.res.body)
      + ' -- every correctly signed-in technician is refused. That is the '
      + 'fails-closed-and-confusingly state sf_trustee_audits was in on main, '
      + 'and the reason this pair of lists is never grown one half at a time');
    assert.strictEqual(r.wrote, true, 'the write did not reach the table');
  });

section('3. SCOPE -- the READ is unchanged, because the finding was the WRITE');

await test('mech_docs READ still answers on the licence key alone', async () => {
  const r = await call('read', 'mech_docs', null);
  assert.strictEqual(r.res.statusCode, 200,
    'status ' + r.res.statusCode + ' -- the read was closed too. That may well be '
    + 'right, but it is a different decision and it is not this one');
});

section('4. SCOPE -- the three sibling tables are NOT swept in with it');

for (const sib of ['mech_quotes', 'mech_checks', 'mech_takeoffs']) {
  await test(sib + ' WRITE still answers on the licence key alone -- its own '
    + 'open-work row, not this one', async () => {
      const r = await call('write', sib, null, { id: 'X-1', text: 'plain' });
      assert.strictEqual(r.res.statusCode, 200,
        'status ' + r.res.statusCode + ' -- ' + sib + ' was gated by this change. '
        + 'Widening a gate past the row that justified it is the scope growth '
        + 'this platform refuses, and mech_checks in particular is a DECISION '
        + 'nobody has been asked to make yet');
    });
}

section('5. THE TWO LISTS, READ FROM THE SOURCE -- the static half of arm 2');

await test('mech_docs is named in BOTH SD_SESSION_GATED and SD_GATE_APP',
  async () => {
    const gated = registryBlock('SD_SESSION_GATED');
    const gateApp = registryBlock('SD_GATE_APP');
    assert.ok(gated, 'SD_SESSION_GATED block not found -- this arm cannot run, '
      + 'which is not a pass');
    assert.ok(gateApp, 'SD_GATE_APP block not found -- this arm cannot run, '
      + 'which is not a pass');
    assert.ok(/'mech_docs':\s*\[/.test(gated),
      'SD_SESSION_GATED does not name mech_docs');
    assert.ok(/'mech_docs':\s*'sairnmechanical'/.test(gateApp),
      'SD_GATE_APP does not pin mech_docs to sairnmechanical, so expectedApp '
      + 'falls back to stonedesk');
  });

await test('CONTROL: the blocks really were parsed, or arm 5 passes on nothing',
  async () => {
    const gated = registryBlock('SD_SESSION_GATED');
    const gateApp = registryBlock('SD_GATE_APP');
    // A known-present entry that has nothing to do with this change. If these
    // fail, registryBlock() truncated and arm 5's mech_docs assertions were
    // being made against a fragment.
    assert.ok(/'sf_accounts':\s*\[/.test(gated),
      'the SD_SESSION_GATED slice does not even contain sf_accounts, so it is '
      + 'truncated and arm 5 proves nothing');
    assert.ok(/'sf_accounts':\s*'sairnfreedom'/.test(gateApp),
      'the SD_GATE_APP slice is truncated and arm 5 proves nothing');
  });

console.log('\n' + (fail
  ? fail + ' arm(s) FAILED -- ' + pass + ' passed'
  : 'ok  sd-data-mech-session-gate: ' + pass + ' passed, 0 failed'));
process.exit(fail ? 1 : 0);

})();
