// api/sd-data-sen-self-correction-flag.test.js
//
// REQUIREMENT: a clock correction filed by the person the visit is assigned to
//   is MARKED AS SUCH — on the entry and on the row — and is not refused.
//
// Run:  node api/sd-data-sen-self-correction-flag.test.js
//
// ── THE FINDING THIS CLOSES ───────────────────────────────────────────────
// `propose_clock_correction` is gated on `SEN_VISIT_SCHEDULER_ROLES`, and the
// refusal says why: *"a caregiver correcting their own clock time with nobody
// else involved is the unverified self-assertion EVV exists to stop."*
//
// That reasoning is right and the gate does not implement it. It is a ROLE
// check. `owner` IS a scheduler role, so in a small agency the person who is
// both the owner and the assigned caregiver passes it — and **nothing anywhere
// compares `session.employee_id` to the visit's `assigned_employee_id`.** The
// one-person operation the exclusion was worried about locking out is exactly
// the one that gets an unmarked self-correction on a federal EVV record.
//
// ── WHY A FLAG AND NOT A REFUSAL ──────────────────────────────────────────
// Refusing would create the lockout for real: in a one-person agency there is
// nobody else to file it, and a caregiver who mis-typed their clock-in would
// have no route at all. The record already survives — `proposed_by` is on every
// entry and the trail is append-only — so what is missing is not the evidence
// but the SIGNAL. A state auditor reading a hundred visits should not have to
// join two fields by eye to find the self-corrected ones.
//
// So: allowed, recorded, and visible without reading the array.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['sen', 'selfcorr', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const HASH = 'sen-selfcorr-hash';
const APP = 'sairnsenior';
const OWNER = 'emp-owner-1';
const OTHER = 'emp-caregiver-2';
const VISIT = 'V-1';

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

function postgrestMock(role, assignee, visitData, calls) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, opts: opts || null });
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: HASH, employee_id: OWNER, role: role, active: true }]; } };
    }
    if (/sen_visits\?/.test(u) && (!opts || opts.method !== 'POST')) {
      return { ok: true, status: 200, json: async function () {
        return [{ visit_id: VISIT, assigned_employee_id: assignee,
                  data: visitData }]; } };
    }
    if (opts && opts.method === 'POST') {
      const sent = JSON.parse(opts.body);
      return { ok: true, status: 200, text: async function () { return opts.body; },
               json: async function () { return [sent]; } };
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

const VISIT_DATA = {
  clock_in_at: '2026-09-29T09:00:00.000Z',
  clock_out_at: '2026-09-29T12:00:00.000Z',
  status: 'completed'
};

async function correct(role, assignee, correction) {
  const calls = [];
  const h = loadHandler(postgrestMock(role, assignee,
    JSON.parse(JSON.stringify(VISIT_DATA)), calls));
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + HASH,
      'x-sd-auth': signSessionToken({ app: APP, employee_id: OWNER,
                                      role: role, license_hash: HASH })
    },
    body: { action: 'propose_clock_correction', resource: 'sen_visits',
            app_id: APP, payload: { id: VISIT, correction: correction } }
  }, res);
  const post = calls.filter(function (c) {
    return c.opts && c.opts.method === 'POST' && /sen_visits/.test(c.url);
  })[0];
  const stored = post ? JSON.parse(post.opts.body).data : null;
  return { res: res, stored: stored,
           entries: (stored && stored.clock_corrections) || [] };
}

// The module requires a REASON CODE from a fixed vocabulary, not free text --
// "a free-text reason fills with the word 'correction' and answers nothing at
// audit". Using the real vocabulary here rather than a plausible-looking string.
const FIX = { field: 'clock_in_at', proposed: '2026-09-29T08:45:00.000Z',
              reason_code: 'forgot_to_clock_in',
              reason: 'caregiver reported a mis-typed clock-in',
              proposed_at: '2026-09-29T13:00:00.000Z' };

(async () => {

section('1. A SELF-CORRECTION IS ALLOWED AND MARKED');

await test('an owner correcting a visit assigned to THEMSELVES is accepted',
  async () => {
    const r = await correct('owner', OWNER, FIX);
    assert.strictEqual(r.res.statusCode, 200,
      'the self-correction was refused: ' + JSON.stringify(r.res.body)
      + ' -- a refusal recreates the one-person lockout this flag exists to '
      + 'avoid');
  });

await test('...and the ENTRY carries the flag, in the append-only trail',
  async () => {
    const r = await correct('owner', OWNER, FIX);
    assert.strictEqual(r.entries.length, 1, 'no correction entry was appended');
    assert.strictEqual(r.entries[0].self_correction, true,
      'entry = ' + JSON.stringify(r.entries[0]));
  });

await test('...and the ROW carries it too, so a list view sees it without '
  + 'opening the array', async () => {
    const r = await correct('owner', OWNER, FIX);
    assert.strictEqual(r.stored.has_self_correction, true,
      'stored row = ' + JSON.stringify(Object.keys(r.stored)));
  });

await test('...and the RESPONSE says so, so the filer is told at the time',
  async () => {
    const r = await correct('owner', OWNER, FIX);
    assert.strictEqual(r.res.body.self_correction, true,
      'response = ' + JSON.stringify(r.res.body));
  });

section('2. THE CONTROLS -- an ordinary correction must be untouched');

await test('a scheduler correcting SOMEBODY ELSE\'S visit is NOT flagged',
  async () => {
    // The arm that matters most. A flag that fires on every correction is a
    // flag nobody reads, and it would libel every legitimate office correction
    // in the system.
    const r = await correct('owner', OTHER, FIX);
    assert.strictEqual(r.res.statusCode, 200, JSON.stringify(r.res.body));
    assert.strictEqual(r.entries.length, 1);
    assert.notStrictEqual(r.entries[0].self_correction, true,
      'an ordinary correction was marked as a self-correction');
    assert.notStrictEqual(r.stored.has_self_correction, true,
      'the row was marked on an ordinary correction');
  });

await test('the flag is STICKY on the row -- a later ordinary correction does '
  + 'not clear it', async () => {
    // Otherwise one routine edit after a self-correction erases the signal,
    // while the entry that caused it is still sitting in the trail.
    const calls = [];
    const data = JSON.parse(JSON.stringify(VISIT_DATA));
    data.clock_corrections = [{ field: 'clock_in_at', proposed_by: OWNER,
                                self_correction: true }];
    data.has_self_correction = true;
    const h = loadHandler(postgrestMock('owner', OTHER, data, calls));
    const res = mockRes();
    await h({ method: 'POST',
      headers: { authorization: 'Bearer KEY-FOR-' + HASH,
        'x-sd-auth': signSessionToken({ app: APP, employee_id: OWNER,
                                        role: 'owner', license_hash: HASH }) },
      body: { action: 'propose_clock_correction', resource: 'sen_visits',
              app_id: APP, payload: { id: VISIT, correction: FIX } } }, res);
    const post = calls.filter(function (c) {
      return c.opts && c.opts.method === 'POST' && /sen_visits/.test(c.url);
    })[0];
    const stored = JSON.parse(post.opts.body).data;
    assert.strictEqual(stored.has_self_correction, true,
      'an ordinary correction cleared the row flag a previous self-correction '
      + 'had set, while its entry is still in the trail');
    assert.strictEqual(stored.clock_corrections.length, 2);
  });

await test('a CAREGIVER is still refused outright -- the role gate is unchanged',
  async () => {
    // The flag is not a relaxation. Everything the role gate refused before, it
    // still refuses.
    const r = await correct('caregiver', OWNER, FIX);
    assert.strictEqual(r.res.statusCode, 403,
      'the role gate was weakened: ' + JSON.stringify(r.res.body));
  });

await test('the caregiver\'s own CLOCK TIME is still never overwritten',
  async () => {
    const r = await correct('owner', OWNER, FIX);
    assert.strictEqual(r.stored.clock_in_at, VISIT_DATA.clock_in_at,
      'the correction overwrote the recorded time instead of appending');
    assert.strictEqual(r.stored.clock_out_at, VISIT_DATA.clock_out_at);
  });

await test('NEGATIVE CONTROL: the harness can tell the two cases apart',
  async () => {
    // Without this a handler that set the flag on everything, or on nothing,
    // could satisfy one arm above and this suite would still look meaningful.
    const self = await correct('owner', OWNER, FIX);
    const other = await correct('owner', OTHER, FIX);
    assert.notStrictEqual(!!self.entries[0].self_correction,
                          !!other.entries[0].self_correction,
      'both cases produced the same flag value, so no arm above is measuring '
      + 'the comparison it claims to measure');
  });

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' SELF-CORRECTION-FLAG ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);

})();
