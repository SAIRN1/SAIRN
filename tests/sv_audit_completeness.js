// tests/sv_audit_completeness.js
// REQUIREMENT: the DEA dosing-register banner claims completeness ONLY when
//   the rows received match the server's own Content-Range count; a missing
//   count reads as UNVERIFIED, never as complete; and a mismatch is said in
//   bold with both numbers
//
// Run:  node tests/sv_audit_completeness.js
//
// ── THE DEFECT THIS PINS ───────────────────────────────────────────────────
// sairnvet.html's banner said "The server copy is not capped" on every
// successful read, with nothing anywhere verifying the rows received were all
// the rows the table holds. PostgREST truncates silently under max-rows, and a
// truncated response is byte-identical to a complete one -- on the register an
// inspector reads for exactly the property being claimed. Found H1 seq #512;
// the fix pattern is api/audit-checkpoint.js:137, applied to this read path.
//
// The SERVER half is driven against the real handler with a stubbed PostgREST
// (three Content-Range shapes). The CLIENT half is source-shape: the banner
// builder lives inside a DOM handler and the three states are asserted on the
// strings it can produce.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// ── server half ────────────────────────────────────────────────────────────
function mockRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
function loadHandler(contentRange, rowCount) {
  delete require.cache[require.resolve('../api/_lib/license')];
  require.cache[require.resolve('../api/_lib/license')] = {
    exports: { validateLicenseKey: async () => ({ valid: true, active: true, license_hash: 'H', trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnvet' }) }
  };
  const realAuth = require('../api/_lib/auth');
  delete require.cache[require.resolve('../api/_lib/auth')];
  require.cache[require.resolve('../api/_lib/auth')] = {
    exports: Object.assign({}, realAuth, {
      tokenFromRequest: () => 'tok',
      verifySessionToken: () => ({ employee_id: 'e1', role: 'owner' })
    })
  };
  global.fetch = async (url, init) => {
    const rows = [];
    for (let i = 0; i < rowCount; i++) rows.push({ data: { id: 'A' + i } });
    return {
      ok: true, status: 200,
      headers: { get: (k) => (k.toLowerCase() === 'content-range' ? contentRange : null) },
      json: async () => rows
    };
  };
  delete require.cache[require.resolve('../api/sd-data.js')];
  return require('../api/sd-data.js');
}
async function readAudit(contentRange, rowCount) {
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'k';
  const h = loadHandler(contentRange, rowCount);
  const res = mockRes();
  await h({ method: 'POST', headers: { authorization: 'Bearer K' },
            body: { action: 'read', resource: 'sv_audit_log', app_id: 'sairnvet', payload: {} } }, res);
  return res;
}

(async function main() {
  section('the server states its own count, or states that it cannot');

  await test('a countable response carries total, and it is the number after the slash', async () => {
    const r = await readAudit('0-2/1207', 3);
    assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
    assert.strictEqual(r.body.total, 1207);
    assert.strictEqual(r.body.data.length, 3);
  });

  await test('THE TRUNCATION CASE IS REPRESENTABLE: 3 rows of 1207 is not hidden', async () => {
    // This is the whole point. Before the fix the response had no way to say
    // "there were more", so the client had no way to know.
    const r = await readAudit('0-2/1207', 3);
    assert.notStrictEqual(r.body.total, r.body.data.length,
      'the fixture is broken -- it no longer models a truncated read');
  });

  await test('"*" -- PostgREST for "I did not count" -- is total:null, never 0', async () => {
    // Reading * as a number would claim an empty table over a full one.
    const r = await readAudit('0-2/*', 3);
    assert.strictEqual(r.body.total, null);
  });

  await test('an ABSENT Content-Range is total:null too -- could-not-tell is a third state', async () => {
    const r = await readAudit(null, 3);
    assert.strictEqual(r.body.total, null);
  });

  await test('the request actually asks PostgREST to count -- no Prefer, no header back', async () => {
    let prefer = null;
    const h = loadHandler('0-0/1', 1);
    const saved = global.fetch;
    global.fetch = async (url, init) => {
      prefer = init && init.headers && init.headers.Prefer;
      return saved(url, init);
    };
    const res = mockRes();
    await h({ method: 'POST', headers: { authorization: 'Bearer K' },
              body: { action: 'read', resource: 'sv_audit_log', app_id: 'sairnvet', payload: {} } }, res);
    assert.match(String(prefer), /count=exact/,
      'the read never asks for a count, so Content-Range carries no total and every read is UNVERIFIED');
  });

  section('the client banner: three states, none folded into another');

  const html = fs.readFileSync(path.join(__dirname, '..', 'sairnvet.html'), 'utf8');

  await test('THE LIE IS GONE: "not capped" is no longer claimed anywhere', async () => {
    const lines = html.replace(/<!--[\s\S]*?-->/g, '').split(/\r?\n/)
      .filter(l => !/^\s*(\/\/|\*)/.test(l))
      .filter(l => /not capped/i.test(l));
    assert.deepStrictEqual(lines, [],
      'the unverified completeness claim survives: ' + JSON.stringify(lines));
  });

  await test('the banner has the three states, and each says what it is', async () => {
    const i = html.indexOf('var completeness;');
    assert.ok(i > 0, 'the completeness branch is gone from svRenderDoseAudit');
    const body = html.slice(i, i + 1800);
    assert.match(body, /env\.total === rows\.length/, 'no verified branch');
    assert.match(body, /INCOMPLETE: the server states it holds/, 'no truncation branch, said in bold');
    assert.match(body, /unverified/, 'no unknown-total branch');
  });

  await test('the VERIFIED claim requires the comparison, not just a 200', async () => {
    const i = html.indexOf('var completeness;');
    const body = html.slice(i, i + 1800);
    const verified = body.indexOf("typeof env.total === 'number' && env.total === rows.length");
    assert.ok(verified > 0,
      'completeness is claimed without comparing the received rows to the server\'s count');
  });

  await test('svData\'s envelope forwards total, and absence stays null', async () => {
    const i = html.indexOf('wantEnvelope ?');
    assert.ok(i > 0, 'the envelope return is gone');
    const line = html.slice(i, i + 300);
    assert.match(line, /total/, 'the envelope drops the total on the floor');
    assert.match(line, /typeof d\.total === 'number' \? d\.total : null/,
      'a non-numeric total is not normalised to null -- garbage flows into the comparison');
  });

  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' SV-AUDIT-COMPLETENESS ASSERTIONS PASS'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
}());
