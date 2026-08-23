// Isolated test of api/alf-alerts.js's request gating (Phase 3 item 4).
//
// THIS FILE EXISTS BECAUSE OF A REAL PRODUCTION DEFECT: the first version of
// alf-alerts.js opened with `if (req.method !== 'POST') return 405`. Vercel
// crons issue a **GET**, so the scheduled sweep returned 405 on every firing
// and the alerting feature silently never delivered anything. Every unit test
// passed throughout, because none of them exercised the HTTP method Vercel
// actually uses -- it was caught only by reading the real production cron log.
// The first check below is the regression guard for exactly that.
'use strict';
const path = require('path');
const ROOT = path.join(__dirname, '..', '..');

// Dummy fixture values, not secrets. Assembled rather than written as literal
// assignments so this file carries nothing credential-shaped.
const FIXTURE = {
  cronToken: ['test', 'cron', 'fixture'].join('-'),
  mailToken: ['test', 'mail', 'fixture'].join('-'),
  fromAddress: 'alerts@example.test'
};
process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = ['fake', 'service', 'value'].join('-');
process.env.CRON_SECRET = FIXTURE.cronToken;
process.env.RESEND_API_KEY = FIXTURE.mailToken;
// RESEND_FROM_EMAIL, not RESEND_FROM_ADDRESS. See the second regression guard
// below -- this test previously set the name the code read, so both sides were
// consistently wrong together and the suite passed while production never sent.
process.env.RESEND_FROM_EMAIL = FIXTURE.fromAddress;

const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
licenseMod.validateLicenseKey = async () => ({
  valid: true, active: true, license_hash: 'HASH1', app_id: 'sairncare'
});
const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
authMod.verifySessionToken = (token) => (token ? JSON.parse(token) : null);

let FACILITIES = [{ license_hash: 'HASH1', data: { name: 'Test ALF', med_window_minutes: 60, alert_email: 'don@example.test' } }];
let MAR_ROWS = [];
let EMAILS = [];

global.fetch = async (url, opts) => {
  opts = opts || {};
  const method = (opts.method || 'GET').toUpperCase();
  if (/api\.resend\.com\/emails/.test(url)) {
    EMAILS.push(JSON.parse(opts.body));
    return { ok: true, status: 200, json: async () => ({ id: 'em_1' }) };
  }
  if (/alf_facility\?license_hash=eq\./.test(url)) {
    return { ok: true, status: 200, json: async () => [{ facility_id: 'FAC-DEFAULT', data: FACILITIES[0].data }] };
  }
  if (/alf_facility\?select=license_hash,data/.test(url)) {
    return { ok: true, status: 200, json: async () => FACILITIES.slice() };
  }
  if (/alf_mar\?license_hash=eq\./.test(url)) {
    return { ok: true, status: 200, json: async () => MAR_ROWS.slice() };
  }
  throw new Error('Unmocked fetch: ' + method + ' ' + url);
};

delete require.cache[require.resolve(path.join(ROOT, 'api/alf-alerts.js'))];
const handler = require(path.join(ROOT, 'api/alf-alerts.js'));

const CRON_AUTH = 'Bearer ' + FIXTURE.cronToken;

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
async function call(method, headers, body) {
  const res = fakeRes();
  await handler({ method: method, headers: headers || {}, body: body || {} }, res);
  return res;
}

let pass = 0, fail = 0;
async function check(n, f) { try { await f(); pass++; console.log('PASS ' + n); } catch (e) { fail++; console.log('FAIL ' + n + ' -- ' + e.message); } }
function assertEq(a, b, m) { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error((m || 'mismatch') + ': expected ' + JSON.stringify(b) + ' got ' + JSON.stringify(a)); }
function assertTrue(v, m) { if (!v) throw new Error(m || 'expected truthy'); }

(async () => {
  // ── THE REGRESSION GUARD ─────────────────────────────────────────────
  await check('a Vercel cron GET is ACCEPTED, not 405 -- the defect this file exists for', async () => {
    MAR_ROWS = [];
    const res = await call('GET', { authorization: CRON_AUTH });
    assertTrue(res.statusCode !== 405, 'a cron GET must never be rejected as a bad method');
    assertEq(res.statusCode, 200);
    assertEq(res.body.ok, true);
  });

  await check('an unauthenticated GET is still rejected (405), so the endpoint is not open', async () => {
    const res = await call('GET', {});
    assertEq(res.statusCode, 405);
  });

  await check('a GET with the WRONG cron token is not treated as a cron', async () => {
    const res = await call('GET', { authorization: 'Bearer not-the-right-value' });
    assertEq(res.statusCode, 405, 'falls through to the interactive path, which is POST-only');
  });

  // ── cron sweep behaviour ─────────────────────────────────────────────
  await check('the sweep emails when a dose is genuinely late', async () => {
    EMAILS = [];
    MAR_ROWS = [{
      entry_id: 'MED-L', resident_id: 'RES-1', entry_type: 'medication_order',
      data: { name: 'Metformin', schedule_times: ['00:05'], pharmacy_status: 'accepted' }
    }];
    const res = await call('GET', { authorization: CRON_AUTH });
    assertEq(res.statusCode, 200);
    const r = res.body.results[0];
    // Guarded so the assertion is never vacuous if this runs in the first minutes of a UTC day.
    if (r.late > 0) {
      assertEq(r.emailed, true, 'a late dose must actually send');
      assertEq(EMAILS.length, 1);
      assertTrue(/late medication/i.test(EMAILS[0].subject));
      assertEq(EMAILS[0].to, ['don@example.test']);
    } else {
      assertEq(r.emailed, false, 'nothing late means nothing sent');
    }
  });

  await check('a pharmacy order still PENDING REVIEW never triggers a late alert', async () => {
    EMAILS = [];
    MAR_ROWS = [{
      entry_id: 'RXIN-1', resident_id: 'RES-1', entry_type: 'medication_order',
      data: { name: 'Warfarin', schedule_times: ['00:05'], source: 'pharmacy', pharmacy_status: 'pending_review' }
    }];
    const res = await call('GET', { authorization: CRON_AUTH });
    assertEq(res.body.results[0].late, 0, 'nobody was cleared to give it yet');
    assertEq(EMAILS.length, 0);
  });

  await check('with NO window policy the sweep skips that facility instead of guessing one', async () => {
    const saved = FACILITIES[0].data;
    FACILITIES = [{ license_hash: 'HASH1', data: { name: 'Test ALF', alert_email: 'don@example.test' } }];
    const res = await call('GET', { authorization: CRON_AUTH });
    assertEq(res.body.results[0].skipped, 'NO_WINDOW_POLICY');
    FACILITIES = [{ license_hash: 'HASH1', data: saved }];
  });

  await check('a late dose with no alert_email is counted but reported unsent, not silently dropped', async () => {
    EMAILS = [];
    const saved = FACILITIES[0].data;
    FACILITIES = [{ license_hash: 'HASH1', data: { name: 'Test ALF', med_window_minutes: 60 } }];
    MAR_ROWS = [{
      entry_id: 'MED-L2', resident_id: 'RES-1', entry_type: 'medication_order',
      data: { name: 'Metformin', schedule_times: ['00:05'], pharmacy_status: 'accepted' }
    }];
    const res = await call('GET', { authorization: CRON_AUTH });
    const r = res.body.results[0];
    if (r.late > 0) {
      assertEq(r.emailed, false);
      assertEq(r.skipped, 'NO_ALERT_EMAIL', 'the gap must be named, not hidden');
    }
    assertEq(EMAILS.length, 0);
    FACILITIES = [{ license_hash: 'HASH1', data: saved }];
  });

  // ── THE SECOND REGRESSION GUARD ──────────────────────────────────────
  // A REAL PRODUCTION DEFECT, same shape as the 405 one above: this file read
  // RESEND_FROM_ADDRESS, a variable that has never existed in the Vercel
  // project. The real one is RESEND_FROM_EMAIL, configured alongside
  // RESEND_API_KEY. Every test passed, because the test set the same wrong
  // name the code read -- both halves were wrong together, so nothing
  // disagreed. The cron 503'd EMAIL_NOT_CONFIGURED on every firing.
  //
  // The guard therefore cannot be "the code reads NAME_X" -- that is what was
  // already circular. It has to be a claim about the OUTGOING PAYLOAD: whatever
  // env var the sender comes from, `from` must not arrive at Resend empty.
  // Resend rejects an empty from, so an empty one here is a real send failure.
  await check('the outgoing Resend payload carries a non-empty from address', async () => {
    EMAILS = [];
    MAR_ROWS = [{
      entry_id: 'MED-FROM', resident_id: 'RES-1', entry_type: 'medication_order',
      data: { name: 'Metformin', schedule_times: ['00:05'], pharmacy_status: 'accepted' }
    }];
    const res = await call('GET', { authorization: CRON_AUTH });
    if (res.body.results[0].late > 0) {
      assertEq(EMAILS.length, 1);
      assertTrue(EMAILS[0].from, 'from must be populated -- an undefined from means the env var name in the code does not match a real one');
      assertEq(EMAILS[0].from, FIXTURE.fromAddress);
    }
  });

  await check('with the sender variable unset the sweep 503s and NAMES the missing variable', async () => {
    EMAILS = [];
    const savedFrom = process.env.RESEND_FROM_EMAIL;
    delete process.env.RESEND_FROM_EMAIL;
    const res = await call('GET', { authorization: CRON_AUTH });
    assertEq(res.statusCode, 503);
    assertEq(res.body.error.code, 'EMAIL_NOT_CONFIGURED');
    // Naming it is the point: the previous message listed both variables
    // unconditionally, which sent a whole session hunting for an absent
    // RESEND_API_KEY that was in fact present and correct.
    assertTrue(/RESEND_FROM_EMAIL/.test(res.body.error.message), 'the message must name the variable that is actually missing');
    assertTrue(!/RESEND_API_KEY/.test(res.body.error.message), 'it must NOT name a variable that is present');
    assertEq(EMAILS.length, 0);
    process.env.RESEND_FROM_EMAIL = savedFrom;
  });

  await check('a Resend REJECTION is logged as an error, not swallowed into a 200', async () => {
    // The cron's JSON response body goes nowhere -- Vercel keeps the status
    // code and discards it. Before this, Resend rejecting every message looked
    // identical to a perfect sweep from the outside: 200, no signal, nobody
    // notified. The log line is the only observable difference.
    EMAILS = [];
    const realFetch = global.fetch;
    global.fetch = async (url, opts) => {
      if (/api\.resend\.com\/emails/.test(url)) {
        return { ok: false, status: 422, text: async () => 'domain not verified' };
      }
      return realFetch(url, opts);
    };
    const errors = [];
    const realErr = console.error;
    console.error = (m) => errors.push(String(m));
    MAR_ROWS = [{
      entry_id: 'MED-REJ', resident_id: 'RES-1', entry_type: 'medication_order',
      data: { name: 'Metformin', schedule_times: ['00:05'], pharmacy_status: 'accepted' }
    }];
    const res = await call('GET', { authorization: CRON_AUTH });
    console.error = realErr;
    global.fetch = realFetch;
    if (res.body.results[0].late > 0) {
      assertEq(res.body.results[0].emailed, false, 'a rejected send must not be reported as emailed');
      assertTrue(errors.some((e) => /Resend send FAILED/.test(e)), 'the rejection must reach the production log');
      assertTrue(errors.some((e) => /domain not verified/.test(e)), 'the log must carry the reason Resend gave, not just "failed"');
    }
  });

  await check('a SUCCESSFUL send logs the provider message id, so success is observable too', async () => {
    // The counterpart to the test above. Logging only failures makes "delivered"
    // and "never attempted" produce byte-identical output: both are a 200 with
    // an empty log. That ambiguity is not theoretical -- it is exactly what made
    // the 2026-08-23 18:00 UTC firing unverifiable from the log alone. A send
    // that Resend accepted must say so, with the id Resend issued.
    EMAILS = [];
    const infos = [];
    const realLog = console.log;
    console.log = (m) => infos.push(String(m));
    MAR_ROWS = [{
      entry_id: 'MED-OK', resident_id: 'RES-1', entry_type: 'medication_order',
      data: { name: 'Metformin', schedule_times: ['00:05'], pharmacy_status: 'accepted' }
    }];
    const res = await call('GET', { authorization: CRON_AUTH });
    console.log = realLog;
    if (res.body.results[0].late > 0) {
      assertEq(res.body.results[0].emailed, true, 'an accepted send must be reported as emailed');
      assertTrue(infos.some((m) => /Resend send OK/.test(m)), 'a successful send must reach the production log');
      assertTrue(infos.some((m) => /resend_id em_1/.test(m)), "the log must carry Resend's message id, which is the actual proof of acceptance");
    }
  });

  // ── interactive path ─────────────────────────────────────────────────
  await check('the interactive check requires a session', async () => {
    const res = await call('POST', { authorization: 'Bearer licensevalue' }, { action: 'check' });
    assertEq(res.statusCode, 401);
    assertEq(res.body.error.code, 'NO_SESSION');
  });

  await check('billing has no access to a medication exception report (403)', async () => {
    const res = await call('POST', {
      authorization: 'Bearer licensevalue',
      'x-test-token': JSON.stringify({ role: 'billing', employee_id: 'B1' })
    }, { action: 'check' });
    assertEq(res.statusCode, 403);
  });

  await check('nursing CAN run the interactive check, and it declares its channels honestly', async () => {
    MAR_ROWS = [];
    const res = await call('POST', {
      authorization: 'Bearer licensevalue',
      'x-test-token': JSON.stringify({ role: 'nursing', employee_id: 'N1' })
    }, { action: 'check' });
    assertEq(res.statusCode, 200);
    assertEq(res.body.channels.in_app, true);
    assertTrue(/unavailable/i.test(res.body.channels.sms), 'SMS must be declared unavailable, never implied sent');
    assertTrue(/not sent/i.test(res.body.channels.email), 'the interactive check must not imply it emailed anyone');
  });

  await check('the interactive check sends NO email', async () => {
    EMAILS = [];
    await call('POST', {
      authorization: 'Bearer licensevalue',
      'x-test-token': JSON.stringify({ role: 'owner', employee_id: 'O1' })
    }, { action: 'check' });
    assertEq(EMAILS.length, 0);
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
