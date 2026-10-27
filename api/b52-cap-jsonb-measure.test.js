// api/b52-cap-jsonb-measure.test.js
//
// Run:  node api/b52-cap-jsonb-measure.test.js
//
// HOVER H2 seq1109 (cody b52). The per-resource caps in api/sd-data.js are
// EQUAL to their tables' `*_data_size` constraints, so that an oversized
// write gets a clear 413 rather than an unclassified store error. Equal
// numbers, different measures: the gate counted compact JSON, the constraint
// counts octet_length(data::text) on jsonb, which has a space after every ':'
// and ','. A record could clear the gate and then be refused by the table.
//
// J arms pin the measure against jsonb text written out by hand. G arms drive
// the real dispatcher at the dnt_appointments ceiling. X restores the compact
// measure in a compiled copy of sd-data.js and requires G1's payload to get
// PAST the gate -- so G1 is measuring the fix.
//
// No database is touched. Exit: 0 all arms passed · 1 an arm FAILED

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['b52', 'cap', 'jsonb', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const fs = require('fs');
const path = require('path');
const Module = require('module');
const { signSessionToken } = require('./_lib/auth');
const { jsonbTextBytes } = require('./_lib/jsonb-text-bytes');
const photoVal = require('./_lib/dental-photo-validation');

const SD_DATA = path.join(__dirname, 'sd-data.js');
const SD_DATA_SRC = fs.readFileSync(SD_DATA, 'utf8');
const HASH = 'b52-cap-hash';
const KEY = 'KEY-FOR-' + HASH;
const CEILING = photoVal.STORAGE_CEILING_BYTES;

let pass = 0, fail = 0;
function is(cond, label, detail) {
  if (cond) { pass++; console.log('  ok    ' + label); }
  else { fail++; console.log('  FAIL  ' + label + (detail ? '\n        ' + String(detail).slice(0, 600) : '')); }
}

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
const eCode = (res) => (res.body && res.body.error && res.body.error.code) || '';

function loadHandler(source) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairndental' })
    }
  };
  global.fetch = async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (/_employee_auth/.test(u)) {
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: 'emp-1', role: 'owner', active: true }] };
    }
    if (method === 'POST' || method === 'PATCH') {
      let parsed = null;
      try { parsed = JSON.parse(init.body); } catch (e) { parsed = {}; }
      return { ok: true, status: 200, json: async () => [Array.isArray(parsed) ? parsed[0] : parsed] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
  delete require.cache[require.resolve(SD_DATA)];
  if (!source) return require(SD_DATA);
  const m = new Module(SD_DATA, module);
  m.filename = SD_DATA;
  m.paths = Module._nodeModulePaths(__dirname);
  m._compile(source, SD_DATA);
  return m.exports;
}

async function write(handler, payload) {
  const res = mockRes();
  const realErr = console.error;
  console.error = function () {};
  try {
    await handler({ method: 'POST', headers: {
      authorization: 'Bearer ' + KEY,
      'x-sd-auth': signSessionToken({ app: 'sairndental', employee_id: 'emp-1', role: 'owner', license_hash: HASH })
    }, body: { action: 'write', resource: 'dnt_appointments', payload: payload } }, res);
  } finally { console.error = realErr; }
  return res;
}

// An ARRAY-HEAVY appointment: many small elements, so jsonb text carries far
// more separator bytes than compact JSON. Grown until COMPACT is just under
// the ceiling -- the shape that cleared the old gate.
function arrayHeavyUnder(limit) {
  const base = { id: 'AP-B52', status: 'Pending', patient_id: 'PT-1', provider_id: 'PV-1',
                 procedure_type_id: 'PC-1', start_time: '2027-01-01T10:00:00Z',
                 end_time: '2027-01-01T10:20:00Z', location_id: 'main', tags: [] };
  const compact = (v) => Buffer.byteLength(JSON.stringify(v), 'utf8');
  // Each element after the first adds exactly 2 compact bytes (",1"). Sized
  // by arithmetic, then CHECKED by measurement in arm J2 -- never trusted.
  const room = limit - 64 - compact(base);
  base.tags = new Array(Math.floor(room / 2)).fill(1);
  return base;
}

(async () => {
  console.log('CAP MEASURE -- the gate counts what the constraint counts (hover H2 seq1109)');

  // ── J. THE MEASURE, against jsonb text written out by hand ──────────────
  const J = [
    [{ a: 1, b: [1, 2] }, '{"a": 1, "b": [1, 2]}'],
    [{}, '{}'], [[], '[]'],
    [[{ x: null, y: true }, []], '[{"x": null, "y": true}, []]'],
    [{ s: 'é"\n' }, '{"s": "é\\"\\n"}'],
    [{ n: { m: ['p', 2.5] } }, '{"n": {"m": ["p", 2.5]}}'],
    [{ u: undefined, k: 1 }, '{"k": 1}']
  ];
  const bad = J.filter(([v, pg]) => jsonbTextBytes(v) !== Buffer.byteLength(pg, 'utf8'));
  is(bad.length === 0, 'J1. jsonbTextBytes equals the byte length of hand-written jsonb text on ' + J.length + ' shapes (escapes, UTF-8, empty, nested, undefined dropped)',
     JSON.stringify(bad.map(([v, pg]) => [pg, jsonbTextBytes(v)])));

  const heavy = arrayHeavyUnder(CEILING);
  const heavyCompact = Buffer.byteLength(JSON.stringify(heavy), 'utf8');
  const heavyJsonb = jsonbTextBytes(heavy);
  is(heavyCompact <= CEILING && heavyJsonb > CEILING,
     'J2. CONTROL: the fixture is under the ceiling compact (' + heavyCompact + ') and over it as jsonb text (' + heavyJsonb + ') -- the H2 window, made real',
     'ceiling ' + CEILING);

  // ── G. THE REAL GATE ────────────────────────────────────────────────────
  {
    const res = await write(loadHandler(null), heavy);
    is(res.statusCode === 413 && eCode(res) === 'PAYLOAD_TOO_LARGE',
       'G1. that record is refused AT THE GATE with 413 PAYLOAD_TOO_LARGE, not passed on to a store that would refuse it unclassified',
       res.statusCode + ' ' + eCode(res));
  }
  {
    const small = { id: 'AP-B52-S', status: 'Pending', patient_id: 'PT-1', photos: ['data:image/jpeg;base64,' + 'A'.repeat(200000)] };
    const res = await write(loadHandler(null), small);
    is(res.statusCode !== 413,
       'G2. a 200KB photo booking, under the ceiling in both measures, is NOT refused by the size gate', res.statusCode + ' ' + eCode(res));
  }
  {
    // b53 (Michael's decision): the 64KB DEFAULT is measured as jsonb text too.
    // An array-heavy record under 65,536 compact and over it as jsonb, on a
    // resource with no per-resource cap, is now refused at the gate.
    const rec = { id: 'PT-B53', items: [] };
    const room = 65536 - 64 - Buffer.byteLength(JSON.stringify(rec), 'utf8');
    rec.items = new Array(Math.floor(room / 2)).fill(1);
    const c = Buffer.byteLength(JSON.stringify(rec), 'utf8'), j = jsonbTextBytes(rec);
    const res = mockRes();
    const realErr = console.error; console.error = function () {};
    try {
      await loadHandler(null)({ method: 'POST', headers: { authorization: 'Bearer ' + KEY,
        'x-sd-auth': signSessionToken({ app: 'sairndental', employee_id: 'emp-1', role: 'owner', license_hash: HASH }) },
        body: { action: 'write', resource: 'dnt_patients', payload: rec } }, res);
    } finally { console.error = realErr; }
    is(c <= 65536 && j > 65536 && res.statusCode === 413 && eCode(res) === 'PAYLOAD_TOO_LARGE',
       'G3. the 64KB DEFAULT also measures jsonb text (b53): ' + c + ' compact / ' + j + ' jsonb -> 413 at the gate',
       res.statusCode + ' ' + eCode(res));
  }

  // ── X. ABLATION: the compact measure restored -> G1's record clears the gate.
  {
    const NEW = "    const payloadBytes = jsonbTextBytes(\n"
              + "      resource.indexOf('dnt_') === 0 ? dntLocation.stampLocation(payload) : payload);";
    const OLD = "    const payloadBytes = Buffer.byteLength(JSON.stringify(payload), 'utf8');";
    if (SD_DATA_SRC.split(NEW).length - 1 !== 1) {
      is(false, 'X. ablation anchor', 'the b52 measure does not occur exactly once in api/sd-data.js');
    } else {
      const res = await write(loadHandler(SD_DATA_SRC.replace(NEW, OLD)), heavy);
      is(res.statusCode !== 413,
         'X. ABLATION: with the compact measure restored, G1\'s record gets PAST the gate (' + res.statusCode + ') -- the window was real and G1 measures the fix',
         res.statusCode + ' ' + eCode(res));
    }
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
