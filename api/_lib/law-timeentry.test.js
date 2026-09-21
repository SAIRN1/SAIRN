// api/_lib/law-timeentry.test.js
// REQUIREMENT: a billable hour cannot reach law_timeentries without a UTBMS
//   billing code -- that record is what invoices are built from, and a
//   codeless hour renders as a normal billable hour with an empty column
//   rather than as anything wrong
//
// The clause "and the LEDES export" was removed from that requirement on
// 2026-09-21: SAIRNlaw has no LEDES export and never has. A requirement is the
// one line an auditor reads to decide what deleting this suite would lose, so
// it must not name a consumer that does not exist. Tracked as a real gap in
// docs/SAIRN-OPEN-WORK-INDEX.md.
//
// Run: node api/_lib/law-timeentry.test.js
//
// TWO HALVES, AND THE SECOND IS THE ONE THAT WAS MISSING FOR REAL.
// The unit half drives timeEntryProblem() directly. The ENDPOINT half drives
// the real api/sd-data.js handler, because the gap this closes was never that
// no function could tell a bad code from a good one -- it was that nothing on
// the write path ASKED. A unit test alone would have passed against the broken
// platform.
'use strict';
const assert = require('assert');
const path = require('path');
const ROOT = path.join(__dirname, '..', '..');

const { timeEntryProblem, MAX_BILLING_CODE_CHARS } = require('./law-timeentry.js');

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + e.message); }
}
async function ta(name, fn) {
  try { await fn(); pass++; console.log('  ok   ' + name); }
  catch (e) { fail++; console.log('  FAIL ' + name + '\n       ' + e.message); }
}
function section(s) { console.log('\n' + s); }

console.log('SAIRNlaw -- a billable hour must carry a UTBMS code, and the SERVER is what says so');

section('1. the validator answers the question it can answer');

t('a real UTBMS code passes', () => {
  assert.strictEqual(timeEntryProblem({ billing_code: 'L100' }), null);
});

t('a code NOT in the shipped list still passes -- membership is deliberately not checked', () => {
  // The app's own comment flags LAW_BILLING_CODES as "entered from memory of
  // the published UTBMS Litigation set, to be verified against the official
  // UTBMS/LEDES list before real billing". A server-side copy used as a
  // REFUSAL would reject a genuine code the list happens to have wrong. This
  // arm is what stops somebody "improving" the gate into that.
  assert.strictEqual(timeEntryProblem({ billing_code: 'X1' }), null);
  assert.strictEqual(timeEntryProblem({ billing_code: 'L999' }), null);
});

t('surrounding whitespace does not make a real code fail', () => {
  assert.strictEqual(timeEntryProblem({ billing_code: '  L100  ' }), null);
});

section('2. what it REFUSES, and the two empties are told apart');

t('an EMPTY code is refused, and the message names what produced it', () => {
  const p = timeEntryProblem({ billing_code: '' });
  assert.ok(p, 'an empty billing_code was accepted');
  assert.match(p, /needs a UTBMS billing code/);
  assert.match(p, /arrived empty/, 'the message does not distinguish empty from absent: ' + p);
});

t('whitespace ONLY is the same as empty', () => {
  assert.ok(timeEntryProblem({ billing_code: '   ' }));
});

t('an ABSENT code is refused and says it was absent, not empty', () => {
  // Not folded together on purpose: `undefined` means a caller that never set
  // the field -- an import, a new write path, a partial payload -- and which
  // of the two happened is the first thing the next person needs.
  const p = timeEntryProblem({});
  assert.ok(p);
  assert.match(p, /no billing_code was sent at all/, p);
  assert.match(p, /undefined/, p);
});

t('null is absent, not empty', () => {
  assert.match(timeEntryProblem({ billing_code: null }), /no billing_code was sent at all/);
});

t('a NUMBER is refused rather than coerced -- 100 is not "L100"', () => {
  assert.match(timeEntryProblem({ billing_code: 100 }), /no billing_code was sent at all/);
});

t('a pasted paragraph is refused at the length bound', () => {
  const p = timeEntryProblem({ billing_code: 'x'.repeat(MAX_BILLING_CODE_CHARS + 1) });
  assert.ok(p, 'an over-long code was accepted');
  assert.match(p, /characters/);
});

t('and the bound itself is inclusive, not off by one', () => {
  assert.strictEqual(timeEntryProblem({ billing_code: 'x'.repeat(MAX_BILLING_CODE_CHARS) }), null);
});

t('a null record does not throw -- a validator that crashes is a 500, not a refusal', () => {
  assert.ok(timeEntryProblem(null));
  assert.ok(timeEntryProblem(undefined));
});

// ── THE ENDPOINT HALF ──────────────────────────────────────────────────────
section('3. the real handler REFUSES it, which is the half that was missing');

process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
licenseMod.validateLicenseKey = async () => ({
  valid: true, active: true, license_hash: 'HASH1', app_id: 'sairnlaw',
  stripe_subscription_id: 'sub_1', trial_ends_at: null
});
const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
authMod.verifySessionToken = (token) => (token ? JSON.parse(token) : null);

// Any write that reaches Supabase is a write this gate FAILED to stop, so the
// mock counts them rather than just answering.
let upserts = 0;
global.fetch = async (url, opts) => {
  if ((opts || {}).method === 'POST') { upserts += 1; }
  return { ok: true, status: 200, json: async () => ([{ data: { ok: true } }]) };
};

delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
const handler = require(path.join(ROOT, 'api/sd-data.js'));

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
async function write(payload) {
  upserts = 0;
  const req = {
    method: 'POST',
    headers: { authorization: 'Bearer testkey',
               'x-test-token': JSON.stringify({ role: 'owner', employee_id: 'E1' }) },
    body: { action: 'write', resource: 'law_timeentries', payload }
  };
  const res = fakeRes();
  await handler(req, res);
  return res;
}
const ENTRY = {
  id: 'TT-1', matter_id: 'M-1', attorney: 'A', date: '2026-09-18',
  hours: 2, rate: 350, description: 'Drafted motion', billable: true, invoiced: false
};

(async () => {
  await ta('a codeless hour is REFUSED with INVALID_TIME_ENTRY, and NOTHING is written', async () => {
    const res = await write(Object.assign({}, ENTRY, { billing_code: '' }));
    assert.strictEqual(res.statusCode, 400, 'status was ' + res.statusCode);
    assert.strictEqual(res.body.error.code, 'INVALID_TIME_ENTRY', JSON.stringify(res.body));
    assert.strictEqual(upserts, 0, 'the row reached Supabase anyway -- the gate ran too late');
  });

  await ta('an hour with NO billing_code field at all is refused the same way', async () => {
    const res = await write(Object.assign({}, ENTRY));
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(upserts, 0);
  });

  await ta('a valid entry still writes -- the gate is not refusing everything', async () => {
    const res = await write(Object.assign({}, ENTRY, { billing_code: 'L100' }));
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(upserts, 1, 'a valid entry did not reach the upsert');
  });

  await ta('the gate is scoped to law_timeentries and does not refuse its neighbours', async () => {
    // Every other law_ resource goes through the same branch. A gate that
    // caught them too would be refusing writes nobody asked it to judge.
    upserts = 0;
    const req = {
      method: 'POST',
      headers: { authorization: 'Bearer testkey',
                 'x-test-token': JSON.stringify({ role: 'owner', employee_id: 'E1' }) },
      body: { action: 'write', resource: 'law_mattertasks', payload: { id: 'MT-1', title: 'x' } }
    };
    const res = fakeRes();
    await handler(req, res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(upserts, 1);
  });

  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  law-timeentry: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
