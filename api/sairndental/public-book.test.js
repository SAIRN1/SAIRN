// api/sairndental/public-book.test.js
// Plain node:assert tests -- no test framework, matching api/'s existing
// zero-npm-dependency convention (see api/_lib/auth.test.js).
// Run: node api/sairndental/public-book.test.js
//
// Covers only the pre-network-call validation paths (existing
// required-field check + the new photos validation). The full
// resolveSlug -> Supabase -> insert flow needs a real (or live-mocked)
// Supabase environment and is covered by the plan's Task 5 live
// verification instead, not here.

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

var VALID_BASE = {
  slug: 'test-practice', patient: { name: 'Jane Doe', dob: '1990-01-01', phone: '555-0100' },
  provider_id: 'PV-1', procedure_type_id: 'PC-1', start_time: '2026-08-13T14:00:00.000Z'
};

async function main() {
  console.log('api/sairndental/public-book.js');

  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  var originalFetch = global.fetch;
  var originalRequire = require;

  // Set up mocks before requiring public-book
  //
  // ── resolveSlug IS SWITCHABLE, AND IT HAD TO BECOME SO (2026-09-16) ───────
  // public-book.js DESTRUCTURES resolveSlug at module load, so the stub in
  // place at `require` time is the only one it will ever call. An
  // unconditionally-throwing stub therefore made it IMPOSSIBLE for any arm in
  // this block to get past validation -- including the last one, whose title is
  // "passes validation and reaches the network stage".
  //
  // That arm was green anyway, on a three-way disjunction that was satisfied by
  // the 502 the throwing stub produced. Found by
  // tools/negated_status_assertion_scan.py. The flag is the smallest change
  // that lets exactly one arm through while every validation arm keeps the
  // refusal it relies on.
  var allowSlug = false;
  delete require.cache[require.resolve('../_lib/dental-public')];
  require.cache[require.resolve('../_lib/dental-public')] = {
    exports: {
      resolveSlug: async function () {
        if (!allowSlug) throw new Error('resolveSlug should not be called in validation tests');
        return 'lic-hash-fixture';
      },
      checkAndIncrementRateLimit: async function () { return { allowed: true }; },
      readRows: async function () { return []; }
    }
  };

  global.fetch = function () { throw new Error('fetch should never be called for a request that fails validation'); };
  delete require.cache[require.resolve('./public-book.js')];
  var handler = require('./public-book.js');

  await test('missing required field (existing regression: no patient.name) -> 400, never calls fetch', async () => {
    var res = mockRes();
    var body = Object.assign({}, VALID_BASE, { patient: { dob: '1990-01-01', phone: '555-0100' } });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
  });

  await test('4 photos -> 400 TOO_MANY_PHOTOS, never calls fetch', async () => {
    var res = mockRes();
    var body = Object.assign({}, VALID_BASE, { photos: ['data:image/jpeg;base64,AAAA', 'data:image/jpeg;base64,AAAA', 'data:image/jpeg;base64,AAAA', 'data:image/jpeg;base64,AAAA'] });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'TOO_MANY_PHOTOS');
  });

  await test('a malformed photo entry -> 400 INVALID_PHOTO, never calls fetch', async () => {
    var res = mockRes();
    var body = Object.assign({}, VALID_BASE, { photos: ['not-a-real-data-url'] });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'INVALID_PHOTO');
  });

  await test('an oversized combined photos payload -> 400 PHOTOS_TOO_LARGE, never calls fetch', async () => {
    var res = mockRes();
    var big = 'data:image/jpeg;base64,' + 'A'.repeat(1.3 * 1024 * 1024);
    var body = Object.assign({}, VALID_BASE, { photos: [big] });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'PHOTOS_TOO_LARGE');
  });

  // patient_notes cap, added 2026-08-24. The endpoint stored this field with
  // no length check at all -- these tests exist because the DB size
  // constraint on dnt_appointments is derived from the limit, and a bound
  // over an unbounded field is not a bound.
  await test('over-long patient_notes -> 400 NOTES_TOO_LONG, never calls fetch', async () => {
    var res = mockRes();
    var body = Object.assign({}, VALID_BASE, { patient_notes: 'n'.repeat(9000) });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'NOTES_TOO_LONG');
  });

  await test('a non-string patient_notes is ignored, not stored (trim guard)', async () => {
    // public-book.js coerces a non-string to '' before validating, so this
    // must NOT 400 -- it must fall through to the required-field check.
    var res = mockRes();
    var body = Object.assign({}, VALID_BASE, { patient_notes: { evil: true }, slug: undefined });
    await handler(mockReq(body), res);
    assert.strictEqual(res.statusCode, 400);
    assert.ok(!res.body.error.code || res.body.error.code !== 'NOTES_TOO_LONG',
      'a non-string must not be reported as too long');
  });

  await test('ordinary patient_notes passes validation and reaches the network stage', async () => {
    var res = mockRes();
    var reached = false;
    global.fetch = async function () { reached = true; throw new Error('stop here'); };
    var body = Object.assign({}, VALID_BASE, { patient_notes: 'Chipped a molar on Saturday.' });
    allowSlug = true;                     // this arm is the one that must pass
    try { await handler(mockReq(body), res); } catch (e) { /* expected */ }
    allowSlug = false;                    // every other arm keeps the refusal
    // ── WAS A THREE-WAY DISJUNCTION AND PASSED WITHOUT REACHING ANYTHING ───
    // Until 2026-09-16 this read:
    //
    //   assert.ok(reached || res.statusCode !== 400 ||
    //             res.body.error.code !== 'NOTES_TOO_LONG', ...)
    //
    // Satisfied if ANY of the three held -- so a handler that threw before the
    // network stage, or refused with a 500, or refused with a 400 carrying any
    // OTHER code, left `reached` false and the arm GREEN while the title claims
    // the request "reaches the network stage". The arm already records the
    // claim exactly, in `reached`; the other two terms could only weaken it.
    //
    // Found by tools/negated_status_assertion_scan.py on its first real run.
    // Same class as the 2026-09-16 app-session-isolation defect, where a
    // control over attorney trust money asserted `!== 401` against a gate that
    // refuses 403 and printed "is reachable ... and answers 403" in green.
    assert.ok(reached,
      'valid notes must not be rejected by the cap -- the request never reached '
      + 'the network stage at all (status ' + res.statusCode + ', code '
      + ((res.body && res.body.error && res.body.error.code) || 'none') + ')');
  });

  global.fetch = originalFetch;
  console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
}

main();
