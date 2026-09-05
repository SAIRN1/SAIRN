// api/preauth-envelope-ordering.test.js
//
// Run:  node api/preauth-envelope-ordering.test.js
//
// THE SWEEP THAT PRODUCED THIS (2026-09-05). api/sd-data.js and
// api/sd-sub-data.js were each found running their envelope gate -- body parse,
// action enum, resource, payload cap -- ABOVE licence validation, so a caller
// holding no credential could tell one input from another by which refusal came
// back. Two in a row is a pattern, so tools/preauth_oracle_check.py swept every
// handler: 29 carried the shape. This file covers the FOURTEEN non-auth data
// endpoints that were reordered. The fifteen *-auth.js files carry the same
// shape and are deliberately NOT fixed yet -- see the open-work index row.
//
// WHY THE ORDERING IS ASSERTED FROM CODE ANCHORS AND NEVER FROM MESSAGE TEXT.
// The detector this pass shipped had exactly that bug: its boundary regex
// matched `verifySessionToken(` inside a HEADER COMMENT in api/law-auth.js and
// api/mech-auth.js, so both files reported zero findings while carrying the
// defect. sairn-code-scrubber item 16 Shape A. Every anchor below is a code
// construct -- `JSON.parse(body)`, `ACTIONS.indexOf(...)` -- that cannot appear
// in the prose comments this same pass added directly above those gates.
//
// AND WHY THE BEHAVIOURAL HALF STUBS THE LICENCE LOOKUP. On a developer machine
// SUPABASE_URL is unset, so almost any call returns a config 500 and a test
// written against that passes whether the ordering is right or not. That trap
// is api/sd-sub-data-auth-ordering.test.js's own recorded lesson.
//
// NEGATIVE CONTROL, run before this file was committed: moving the envelope
// block back above validateLicenseKey in api/provisioner-health.js turns the
// ordering assertion for that file AND its two behavioural assertions red.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

let pass = 0, fail = 0;
const run = [];
function t(name, fn) { run.push([name, fn]); }
function section(s) { run.push([s, null]); }

// ── PART A: the source ordering, one entry per reordered handler ───────────
// [file, anchor for the envelope gate]. The boundary anchor is the same in
// every file: the single `await validateLicenseKey(` call.
const FILES = [
  ['accounting.js', 'IDENT_RE.test(appId)'],
  ['courtlistener.js', 'JSON.parse(body)'],
  ['dnt-bi.js', 'JSON.parse(body)'],
  ['ledger.js', '.test(appId)'],
  ['legal-citator.js', 'JSON.parse(body)'],
  ['legal-deadlines.js', 'JSON.parse(body)'],
  ['legal-reference.js', 'JSON.parse(body)'],
  ['provisioner-health.js', 'JSON.parse(body)'],
  ['reference-fingerprint.js', 'JSON.parse(body)'],
  ['sc-ai.js', 'JSON.parse(body)'],
  ['sc-credentials.js', 'JSON.parse(body)'],
  ['sc-eligibility.js', 'JSON.parse(body)'],
  ['sd-render.js', 'JSON.parse(body)'],
  ['sd-webauthn.js', 'JSON.parse(body)'],
];

// The SECOND gate in each file, so the test proves the whole envelope moved and
// not just its first line. Absent for the two that have only one gate.
const SECOND_GATE = {
  'courtlistener.js': 'VALID_ACTIONS[action]',
  'dnt-bi.js': null,
  'legal-citator.js': "'feedback', 'verify'].indexOf",
  'legal-deadlines.js': 'ACTIONS.indexOf(action)',
  'legal-reference.js': 'ACTIONS.indexOf(action)',
  'provisioner-health.js': 'ACTIONS.indexOf(body.action)',
  'reference-fingerprint.js': "body.action !== 'fingerprint'",
  'sc-ai.js': 'Array.isArray(body.messages)',
  'sc-credentials.js': "'set', 'clear'].indexOf",
  'sc-eligibility.js': "'search_payer'].indexOf",
  'sd-render.js': 'photoBytes > MAX_PHOTO_BYTES',
  'sd-webauthn.js': "'reg-options', 'reg-verify'",
};

section('--- the source ordering: licence validation above every envelope gate ---');

FILES.forEach(function (entry) {
  const file = entry[0], gate = entry[1];
  t(file + ': validateLicenseKey runs ABOVE the envelope gate', function () {
    const src = fs.readFileSync(path.join(__dirname, file), 'utf8');
    const lic = src.indexOf('await validateLicenseKey(');
    assert.ok(lic !== -1, 'no validateLicenseKey call found in ' + file);
    const env = src.indexOf(gate);
    assert.ok(env !== -1, 'envelope anchor "' + gate + '" not found in ' + file +
      ' -- the gate was DELETED rather than moved, or the anchor went stale');
    assert.ok(lic < env, file + ': the envelope gate still answers before the ' +
      'caller is known (licence at ' + lic + ', gate at ' + env + ')');

    const second = SECOND_GATE[file];
    if (second) {
      const s = src.indexOf(second);
      assert.ok(s !== -1, 'second-gate anchor "' + second + '" not found in ' + file);
      assert.ok(lic < s, file + ': the SECOND envelope gate still runs above ' +
        'licence validation -- only part of the block moved');
    }
  });
});

t('every reordered handler validates the licence exactly once', function () {
  FILES.forEach(function (entry) {
    const src = fs.readFileSync(path.join(__dirname, entry[0]), 'utf8');
    const n = (src.match(/await validateLicenseKey\(/g) || []).length;
    assert.strictEqual(n, 1, entry[0] + ' validates the licence ' + n + ' times');
  });
});

t('the bearer-presence check still runs FIRST, so a missing credential costs no lookup', function () {
  // Deliberately excludes the two shared endpoints (accounting, ledger), which
  // read the header inline at the validation call and have no separate check,
  // and dnt-bi, whose GET path resolves a feed token instead.
  ['courtlistener.js', 'legal-citator.js', 'legal-deadlines.js', 'legal-reference.js',
    'provisioner-health.js', 'reference-fingerprint.js', 'sc-ai.js', 'sc-credentials.js',
    'sc-eligibility.js', 'sd-render.js', 'sd-webauthn.js'].forEach(function (file) {
    const src = fs.readFileSync(path.join(__dirname, file), 'utf8');
    const noLic = src.indexOf("code: 'NO_LICENSE'");
    const lic = src.indexOf('await validateLicenseKey(');
    assert.ok(noLic !== -1 && noLic < lic, file + ': the bearer-presence check no longer runs first');
  });
});

// ── PART B: the behaviour, through the real handlers ──────────────────────
const LICENSE_PATH = require.resolve('./_lib/license.js');
let licenseAnswer = { valid: false };
require.cache[LICENSE_PATH] = {
  id: LICENSE_PATH, filename: LICENSE_PATH, loaded: true,
  exports: { validateLicenseKey: async () => licenseAnswer },
};
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'test-secret';

function caller(handler) {
  return async function (body, opts) {
    opts = opts || {};
    const res = {
      _s: 0, _j: null,
      status(c) { this._s = c; return this; },
      json(o) { this._j = o; return this; },
      end() { return this; },
      setHeader() { return this; },
    };
    await handler({
      method: opts.method || 'POST',
      headers: { authorization: 'authorization' in opts ? opts.authorization : 'Bearer not-a-real-key' },
      body,
    }, res);
    return { status: res._s, body: res._j, text: JSON.stringify(res._j) };
  };
}

section('--- the behaviour: a junk bearer token learns one thing ---');

const PROBES = [
  {
    file: './provisioner-health.js',
    name: 'provisioner-health',
    bad: { action: 'nonsense' },
    leaks: ['provisioner_health', 'rate_limit_health'],
    envelopeMatch: /action must be one of/,
  },
  {
    file: './sc-eligibility.js',
    name: 'sc-eligibility',
    bad: { action: 'nonsense' },
    leaks: ['search_payer'],
    envelopeMatch: /action must be/,
  },
  {
    file: './sd-render.js',
    name: 'sd-render',
    bad: { material_description: 'granite' },   // photo_base64 missing
    leaks: ['photo_base64'],
    envelopeMatch: /photo_base64 is required/,
  },
];

PROBES.forEach(function (p) {
  const call = caller(require(p.file));

  t(p.name + ': a junk token with a bad envelope is 401, not a 400 naming the gate', async function () {
    licenseAnswer = { valid: false };
    const r = await call(p.bad);
    assert.strictEqual(r.status, 401, 'expected INVALID_LICENSE, got ' + r.status + ' ' + r.text);
    assert.strictEqual(r.body.error.code, 'INVALID_LICENSE');
  });

  t(p.name + ': and the gate\'s own vocabulary appears NOWHERE in that answer', async function () {
    licenseAnswer = { valid: false };
    const r = await call(p.bad);
    p.leaks.forEach(function (n) {
      assert.ok(r.text.indexOf(n) === -1, 'the refusal to an unauthenticated caller discloses "' + n + '"');
    });
  });

  t(p.name + ': NO MALFORMED-VS-WELL-FORMED ORACLE -- both answer identically', async function () {
    licenseAnswer = { valid: false };
    const malformed = await call('{not json');
    const wellFormed = await call(p.bad);
    assert.strictEqual(malformed.status, wellFormed.status);
    assert.strictEqual(malformed.text, wellFormed.text,
      'a malformed body is still distinguishable from a well-formed one');
  });

  t(p.name + ': AN AUTHENTICATED CALLER STILL GETS THE ENVELOPE ERROR -- '
    + 'the reorder must not have deleted the gate', async function () {
    licenseAnswer = { valid: true, active: true, license_hash: 'h', app_id: null };
    const r = await call(p.bad);
    licenseAnswer = { valid: false };
    assert.strictEqual(r.status, 400,
      'a valid licence no longer reaches the envelope gate -- got ' + r.status + ' ' + r.text);
    assert.match(r.text, p.envelopeMatch);
  });

  t(p.name + ': a missing bearer is still NO_LICENSE and costs no lookup', async function () {
    licenseAnswer = { valid: false };
    const r = await call(p.bad, { authorization: '' });
    assert.strictEqual(r.status, 401);
    assert.strictEqual(r.body.error.code, 'NO_LICENSE');
  });

  t(p.name + ': a non-POST is still 405, before anything else', async function () {
    const r = await call({}, { method: 'GET' });
    assert.strictEqual(r.status, 405);
  });
});

(async function () {
  for (const [name, fn] of run) {
    if (!fn) { console.log(name); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
  }
  console.log('\n' + (fail ? 'FAILED  ' : 'ok  ') +
    'pre-auth envelope ordering: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
