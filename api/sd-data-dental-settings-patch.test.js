// api/sd-data-dental-settings-patch.test.js
// Plain node:assert tests. Run: node api/sd-data-dental-settings-patch.test.js
//
// dnt_settings is one record written by three panels -- Booking Settings, the
// GFE practice identity, and the denials panel's appeal windows. It used to
// store `data: payload`, replacing the whole blob, so whatever a panel sent WAS
// the row and every save was a whole-record overwrite:
//
//   workstation B saves an appeal window   -> row holds [X, Y]
//   workstation A saves the practice identity from a copy read before that
//     -> sends [X] -> Y is gone, silently
//
// It is now a PATCH: the handler reads the current row and merges the payload
// onto it. THE TEST THAT MATTERS IS THE INTERLEAVED ONE -- two workstations
// saving DIFFERENT keys inside one round trip, both surviving. Everything else
// here exists so that test cannot pass for the wrong reason.
//
// The store is MODELLED rather than stubbed per-call: the fake PostgREST holds
// a row, answers reads from it, and applies merge-duplicates on write. A stub
// that just returned a fixed row could not show a lost update at all, which is
// the failure this file exists to prove is gone.

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');

const LIC_HASH = 'test-hash';

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  return res;
}
function mockReq(body, token) {
  var headers = { authorization: 'Bearer GOOD-KEY' };
  if (token) headers['x-sd-auth'] = token;
  return { method: 'POST', headers: headers, body: body };
}
const tok = (role) => signSessionToken({ app: 'sairndental', employee_id: 'emp-' + role, role: role, license_hash: LIC_HASH });

// A tiny PostgREST that behaves the way the real one does for this table:
// a select filtered to one settings_id, and an upsert that replaces the row's
// columns. `opts.readStatus` forces the current-row read to fail.
function makeStore(initial, opts) {
  opts = opts || {};
  const state = { row: initial ? JSON.parse(JSON.stringify(initial)) : null, reads: 0, writes: 0 };
  const fetchImpl = async function (url, init) {
    const isWrite = init && init.method === 'POST';
    if (!isWrite) {
      state.reads++;
      if (opts.readStatus && opts.readStatus !== 200) {
        return { ok: false, status: opts.readStatus, json: async () => ({ message: 'boom' }) };
      }
      return { ok: true, status: 200, json: async () => (state.row ? [{ data: state.row.data }] : []) };
    }
    state.writes++;
    const sent = JSON.parse(init.body);
    state.row = { data: sent.data, booking_slug: sent.booking_slug };
    return { ok: true, status: 200, json: async () => [{ data: state.row.data }] };
  };
  return { state, fetchImpl };
}

function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: LIC_HASH, trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

const write = (patch) => ({ action: 'write', resource: 'dnt_settings', payload: patch });

let passed = 0, total = 0;
async function test(name, fn) {
  total++;
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (err) { console.error('  FAIL - ' + name + '\n    ' + err.message); process.exitCode = 1; }
}

async function main() {
  console.log('api/sd-data.js -- SAIRNdental dnt_settings PATCH semantics');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  process.env.SD_AUTH_SECRET = ['dental', 'settings', 'patch', 'fixture'].join('-');

  const EXISTING = {
    data: {
      id: 'default', booking_slug: 'pinnacle', timezone: 'America/New_York',
      appeal_windows: [{ payer: 'Delta', days: 90 }],
      gfe_legal_name: 'Pinnacle Dental LLC', gfe_npi: '1234567890',
      locations: [{ id: 'main', name: 'Main office' }]
    },
    booking_slug: 'pinnacle'
  };

  // ── THE ONE THAT MATTERS ────────────────────────────────────────────────
  await test('TWO WORKSTATIONS, DIFFERENT KEYS, ONE ROUND TRIP: both survive', async () => {
    // Both read the same starting row. B adds an appeal window; A, holding the
    // copy from BEFORE B's write, saves the practice identity. Under the old
    // whole-record PUT, A's save carried B's key at its stale value and erased
    // the new window. Under PATCH, A never mentions appeal_windows.
    const { state, fetchImpl } = makeStore(EXISTING);
    const handler = loadHandler(fetchImpl);

    const bRes = mockRes();
    await handler(mockReq(write({
      id: 'default',
      appeal_windows: [{ payer: 'Delta', days: 90 }, { payer: 'Aetna', days: 180 }]
    }), tok('owner')), bRes);
    assert.strictEqual(bRes.statusCode, 200, JSON.stringify(bRes.body));

    const aRes = mockRes();
    await handler(mockReq(write({
      id: 'default', gfe_legal_name: 'Pinnacle Dental LLC', gfe_npi: '9999999999',
      gfe_tin: '11-1111111', gfe_state: 'OH'
    }), tok('owner')), aRes);
    assert.strictEqual(aRes.statusCode, 200, JSON.stringify(aRes.body));

    const row = state.row.data;
    assert.strictEqual(row.appeal_windows.length, 2, "workstation B's appeal window was erased -- the race is NOT closed");
    assert.strictEqual(row.appeal_windows[1].payer, 'Aetna');
    assert.strictEqual(row.gfe_npi, '9999999999', "workstation A's own save did not land");
  });

  await test('CONTROL: a whole-record payload still overwrites, so the arm above is about the PATCH and not the store', async () => {
    // Same store, same order -- but A sends the WHOLE record from its stale
    // copy, which is exactly what the client used to do. The window is lost.
    // Without this, the test above could pass on any store that never loses
    // anything.
    const { state, fetchImpl } = makeStore(EXISTING);
    const handler = loadHandler(fetchImpl);
    const stale = JSON.parse(JSON.stringify(EXISTING.data));

    await handler(mockReq(write({ id: 'default', appeal_windows: [{ payer: 'Delta', days: 90 }, { payer: 'Aetna', days: 180 }] }), tok('owner')), mockRes());
    await handler(mockReq(write(Object.assign({}, stale, { gfe_npi: '9999999999' })), tok('owner')), mockRes());

    assert.strictEqual(state.row.data.appeal_windows.length, 1,
      'a whole-record send did NOT overwrite -- the store is not modelling the real behaviour, so the arm above proves nothing');
  });

  // ── the merge itself ────────────────────────────────────────────────────
  await test('keys the patch does not mention are kept', async () => {
    const { state, fetchImpl } = makeStore(EXISTING);
    const handler = loadHandler(fetchImpl);
    await handler(mockReq(write({ id: 'default', gfe_tin: '11-1111111' }), tok('owner')), mockRes());
    assert.strictEqual(state.row.data.timezone, 'America/New_York');
    assert.strictEqual(state.row.data.gfe_legal_name, 'Pinnacle Dental LLC');
    assert.deepStrictEqual(state.row.data.locations, [{ id: 'main', name: 'Main office' }]);
    assert.strictEqual(state.row.data.gfe_tin, '11-1111111');
  });

  await test('keys the patch DOES mention are replaced, including arrays', async () => {
    // removePayerTerm() sends the shortened list; a patch that mentions the key
    // must replace it, not union with it, or a removal could never be saved.
    const { state, fetchImpl } = makeStore(EXISTING);
    const handler = loadHandler(fetchImpl);
    await handler(mockReq(write({ id: 'default', appeal_windows: [] }), tok('owner')), mockRes());
    assert.deepStrictEqual(state.row.data.appeal_windows, []);
  });

  await test('the response is the MERGED record, not the patch', async () => {
    // The client caches this as its local copy. Handing back the patch would
    // leave the device holding a settings object missing every key that panel
    // does not own -- the same wipe from the other direction.
    const { fetchImpl } = makeStore(EXISTING);
    const handler = loadHandler(fetchImpl);
    const res = mockRes();
    await handler(mockReq(write({ id: 'default', gfe_tin: '11-1111111' }), tok('owner')), res);
    assert.strictEqual(res.body.data.timezone, 'America/New_York');
    assert.strictEqual(res.body.data.gfe_tin, '11-1111111');
  });

  await test('the promoted booking_slug column comes from the MERGED record', async () => {
    // It has a unique index and the public booking endpoints resolve against
    // it. Taking it from a patch that does not mention it would NULL the column
    // while data.booking_slug still held the slug, and the practice's booking
    // link would stop resolving.
    const { state, fetchImpl } = makeStore(EXISTING);
    const handler = loadHandler(fetchImpl);
    await handler(mockReq(write({ id: 'default', gfe_tin: '11-1111111' }), tok('owner')), mockRes());
    assert.strictEqual(state.row.booking_slug, 'pinnacle',
      'a patch that never mentioned booking_slug nulled the promoted column');
  });

  await test('a first save with no existing row still writes the patch', async () => {
    const { state, fetchImpl } = makeStore(null);
    const handler = loadHandler(fetchImpl);
    const res = mockRes();
    await handler(mockReq(write({ id: 'default', booking_slug: 'newshop' }), tok('owner')), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(state.row.data.booking_slug, 'newshop');
    assert.strictEqual(state.row.booking_slug, 'newshop');
  });

  // ── refusals ────────────────────────────────────────────────────────────
  await test('FAIL-CLOSED: an unreadable current row -> 503, and nothing is written', async () => {
    // Merging onto a base that could not be read is exactly the clobber this
    // change exists to prevent, and a check that silently did not run is
    // indistinguishable from one that passed. Same standard as the GFE check
    // and the coverage-rule uniqueness read.
    const { state, fetchImpl } = makeStore(EXISTING, { readStatus: 500 });
    const handler = loadHandler(fetchImpl);
    const res = mockRes();
    await handler(mockReq(write({ id: 'default', gfe_tin: '11-1111111' }), tok('owner')), res);
    assert.strictEqual(res.statusCode, 503, JSON.stringify(res.body));
    assert.strictEqual(res.body.error.code, 'SETTINGS_READ_UNAVAILABLE');
    assert.strictEqual(state.writes, 0, 'a refused save still reached the store');
  });

  await test('an UNPROVISIONED table is not a read failure -- the write proceeds to NOT_PROVISIONED', async () => {
    const { fetchImpl } = makeStore(EXISTING, { readStatus: 404 });
    const handler = loadHandler(async function (url, init) {
      if (init && init.method === 'POST') return { ok: false, status: 404, json: async () => ({}) };
      return fetchImpl(url, init);
    });
    const res = mockRes();
    await handler(mockReq(write({ id: 'default', gfe_tin: '1' }), tok('owner')), res);
    assert.strictEqual(res.statusCode, 503);
    assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED');
  });

  await test('payload.id is still required, and bad locations are still refused before any read', async () => {
    const { state, fetchImpl } = makeStore(EXISTING);
    let handler = loadHandler(fetchImpl);
    const noId = mockRes();
    await handler(mockReq(write({ booking_slug: 'x' }), tok('owner')), noId);
    assert.strictEqual(noId.statusCode, 400);
    assert.match(noId.body.error.message, /payload\.id is required/);

    const badLoc = mockRes();
    await handler(mockReq(write({ id: 'default', locations: 'not-an-array' }), tok('owner')), badLoc);
    assert.strictEqual(badLoc.statusCode, 400);
    assert.strictEqual(badLoc.body.error.code, 'BAD_LOCATIONS');
    assert.strictEqual(state.reads, 0, 'a round trip was spent on a payload that could never be stored');
  });

  await test('no session -> 401 NO_SESSION, and nothing is read or written', async () => {
    const { state, fetchImpl } = makeStore(EXISTING);
    const handler = loadHandler(fetchImpl);
    const res = mockRes();
    await handler(mockReq(write({ id: 'default', gfe_tin: '1' }), null), res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(res.body.error.code, 'NO_SESSION');
    assert.strictEqual(state.reads + state.writes, 0);
  });

  console.log('\n' + passed + ' / ' + total + ' passed');
  if (passed !== total) process.exitCode = 1;
}

main();
