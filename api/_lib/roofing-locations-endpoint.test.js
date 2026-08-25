// api/_lib/roofing-locations-endpoint.test.js
// Round-trip tests for the Phase 4a rf_locations / rf_schedule branches of
// api/sd-data.js, through the REAL handler with a stubbed Supabase.
// Run: node api/_lib/roofing-locations-endpoint.test.js
//
// What this proves that the pure module cannot: location_id is stamped on every
// job write and CARRIED FORWARD on an edit that does not name one, a scheduled
// day inherits its location from the job rather than the caller, the schedule
// read applies the crew-or-assignee filter, and set_status cannot be used to
// move a day or restaff it.

const assert = require('assert');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://stub.test';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'k';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'stub-secret';

const auth = require('./auth');
let requests = [];
let store = { jobs: [], locations: [], schedule: [] };

function jsonRes(status, body) { return Promise.resolve({ status, ok: status >= 200 && status < 300, json: () => Promise.resolve(body), text: () => Promise.resolve(JSON.stringify(body)) }); }
function eqParam(u, k) { const m = u.match(new RegExp(k + '=eq\\.([^&]+)')); return m ? decodeURIComponent(m[1]) : null; }

global.fetch = function (url, opts) {
  opts = opts || {};
  const u = String(url); const method = opts.method || 'GET';
  requests.push({ url: u, method, body: opts.body ? JSON.parse(opts.body) : null });
  if (u.indexOf('license_keys') !== -1) return jsonRes(200, [{ key: 'RF', status: 'active', app_id: 'sairnroofing', trial_ends_at: null, stripe_subscription_id: 's' }]);
  if (u.indexOf('rf_locations') !== -1) {
    if (method === 'POST') { const row = JSON.parse(opts.body); store.locations = store.locations.filter((l) => l.location_id !== row.location_id).concat([row]); return jsonRes(200, [row]); }
    return jsonRes(200, store.locations);
  }
  if (u.indexOf('rf_schedule') !== -1) {
    if (method === 'POST') { const row = JSON.parse(opts.body); store.schedule = store.schedule.filter((s) => s.schedule_id !== row.schedule_id).concat([row]); return jsonRes(200, [row]); }
    if (method === 'PATCH') {
      const sid = eqParam(u, 'schedule_id'); const patch = JSON.parse(opts.body);
      store.schedule = store.schedule.map((s) => (s.schedule_id === sid ? Object.assign({}, s, patch) : s));
      return jsonRes(200, store.schedule.filter((s) => s.schedule_id === sid));
    }
    const sid = eqParam(u, 'schedule_id');
    return jsonRes(200, store.schedule.filter((s) => !sid || s.schedule_id === sid));
  }
  if (u.indexOf('rf_jobs') !== -1) {
    if (method === 'POST') { const row = JSON.parse(opts.body); store.jobs = store.jobs.filter((j) => j.job_id !== row.job_id).concat([row]); return jsonRes(200, [row]); }
    const jid = eqParam(u, 'job_id');
    return jsonRes(200, store.jobs.filter((j) => !jid || j.job_id === jid));
  }
  return jsonRes(404, { message: 'unexpected' });
};

const handler = require('../sd-data');
const licHash = require('crypto').createHash('sha256').update('RF').digest('hex');
function tok(emp, role) { return auth.signSessionToken({ license_hash: licHash, app: 'sairnroofing', employee_id: emp, role }); }
const OWNER = tok('OWN', 'owner');
const EST = tok('EST', 'estimator');
const FM = tok('FM', 'foreman');
const CREW = tok('CRW', 'crew');
const OTHER = tok('OTH', 'foreman');

let passed = 0, failed = 0;
async function test(name, fn) { requests = []; try { await fn(); passed++; console.log('  ok - ' + name); } catch (e) { failed++; console.error('  FAIL - ' + name); console.error('    ' + e.message); } }
async function call(action, resource, payload, token) {
  const out = { code: null, body: null };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; } };
  const h = { authorization: 'Bearer RF' }; if (token) h['x-sd-auth'] = token;
  await handler({ method: 'POST', headers: h, body: { action, resource, payload } }, res);
  return out;
}
function job(id) { return store.jobs.filter((j) => j.job_id === id)[0]; }

(async () => {
  console.log('\nrf_locations -- management writes, everyone reads:');
  await test('management can create a location', async () => {
    const r = await call('write', 'rf_locations', { id: 'LOC-CBUS', name: 'Columbus', address: '1 Broad St' }, OWNER);
    assert.strictEqual(r.code, 200);
  });
  await test('an estimator CANNOT create a location -> 403', async () => {
    assert.strictEqual((await call('write', 'rf_locations', { id: 'LOC-X', name: 'X' }, EST)).code, 403);
  });
  await test('a location with no name is refused -> 400', async () => {
    const r = await call('write', 'rf_locations', { id: 'LOC-Y' }, OWNER);
    assert.strictEqual(r.code, 400);
    assert.match(r.body.error.message, /needs a name/);
  });
  await test('any signed-in role can read the registry, and the default id is published', async () => {
    const r = await call('read', 'rf_locations', {}, CREW);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.default_location_id, 'LOC-DEFAULT');
  });
  await test('no session -> 401', async () => {
    assert.strictEqual((await call('read', 'rf_locations', {}, null)).code, 401);
  });

  console.log('\nlocation_id on rf_jobs -- stamped, and carried forward:');
  await test('a job saved with no location gets the default, not a null', async () => {
    const r = await call('write', 'rf_jobs', { id: 'J-A', name: 'No location job', status: 'lead', assigned_employee_id: 'FM' }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(job('J-A').location_id, 'LOC-DEFAULT');
  });
  await test('a job saved WITH a location keeps it', async () => {
    await call('write', 'rf_jobs', { id: 'J-B', name: 'Columbus job', status: 'lead', assigned_employee_id: 'FM', location_id: 'LOC-CBUS' }, OWNER);
    assert.strictEqual(job('J-B').location_id, 'LOC-CBUS');
  });
  await test('an ordinary edit that does not mention location does NOT move the job to the default', async () => {
    // The whole-document-replace trap: an "edit the job name" save from the
    // Overview tab must not silently reattribute the job to another branch.
    await call('write', 'rf_jobs', { id: 'J-B', name: 'Columbus job RENAMED', status: 'lead', assigned_employee_id: 'FM' }, OWNER);
    assert.strictEqual(job('J-B').location_id, 'LOC-CBUS');
    assert.strictEqual(job('J-B').data.name, 'Columbus job RENAMED');
  });
  await test('an explicit location change IS honoured', async () => {
    await call('write', 'rf_jobs', { id: 'J-B', name: 'Columbus job RENAMED', status: 'lead', assigned_employee_id: 'FM', location_id: 'LOC-CLE' }, OWNER);
    assert.strictEqual(job('J-B').location_id, 'LOC-CLE');
  });
  await test('a junk location falls back rather than failing the save', async () => {
    await call('write', 'rf_jobs', { id: 'J-C', name: 'Junk loc', status: 'lead', assigned_employee_id: 'OTH', location_id: '   ' }, OWNER);
    assert.strictEqual(job('J-C').location_id, 'LOC-DEFAULT');
  });
  await test('location_id is not duplicated into the data blob', async () => {
    assert.strictEqual(job('J-B').data.location_id, undefined);
  });
  await test('the job read returns location_id', async () => {
    const r = await call('read', 'rf_jobs', {}, OWNER);
    assert.strictEqual(r.body.data.filter((j) => j.id === 'J-B')[0].location_id, 'LOC-CLE');
  });

  console.log('\nrf_schedule -- management staffs it, the day inherits the job\'s location:');
  await test('management can schedule a day', async () => {
    const r = await call('write', 'rf_schedule', { id: 'S1', job_id: 'J-B', scheduled_date: '2026-09-01', crew: ['FM', 'CRW', 'FM'], status: 'planned' }, OWNER);
    assert.strictEqual(r.code, 200);
  });
  await test('the crew was de-duplicated server-side', async () => {
    assert.deepStrictEqual(store.schedule[0].crew, ['FM', 'CRW']);
  });
  await test('the day inherited the JOB\'s location, not one from the caller', async () => {
    const r = await call('write', 'rf_schedule', { id: 'S2', job_id: 'J-B', scheduled_date: '2026-09-02', crew: ['CRW'], location_id: 'LOC-SOMEWHERE-ELSE' }, OWNER);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(store.schedule.filter((s) => s.schedule_id === 'S2')[0].location_id, 'LOC-CLE');
  });
  await test('an ESTIMATOR cannot staff a crew -> 403', async () => {
    assert.strictEqual((await call('write', 'rf_schedule', { id: 'S9', job_id: 'J-B', scheduled_date: '2026-09-03' }, EST)).code, 403);
  });
  await test('a foreman cannot staff a crew either -> 403', async () => {
    assert.strictEqual((await call('write', 'rf_schedule', { id: 'S9', job_id: 'J-B', scheduled_date: '2026-09-03' }, FM)).code, 403);
  });
  await test('scheduling a non-existent job -> 404', async () => {
    const r = await call('write', 'rf_schedule', { id: 'S9', job_id: 'J-NOPE', scheduled_date: '2026-09-03' }, OWNER);
    assert.strictEqual(r.code, 404);
    assert.strictEqual(r.body.error.code, 'NO_JOB');
  });
  await test('a malformed date is refused -> 400', async () => {
    assert.strictEqual((await call('write', 'rf_schedule', { id: 'S9', job_id: 'J-B', scheduled_date: '09/03/2026' }, OWNER)).code, 400);
  });

  console.log('\nThe schedule read filter -- crew OR assignee, and nothing else:');
  await test('management sees every day', async () => {
    const r = await call('read', 'rf_schedule', {}, OWNER);
    assert.strictEqual(r.body.data.length, 2);
  });
  await test('an estimator sees the whole board too (broad-read)', async () => {
    assert.strictEqual((await call('read', 'rf_schedule', {}, EST)).body.data.length, 2);
  });
  await test('a crew member sees only the days they are ON', async () => {
    // CRW is on both S1 and S2.
    assert.strictEqual((await call('read', 'rf_schedule', {}, CREW)).body.data.length, 2);
  });
  await test('the JOB assignee sees days on their job even when not on the crew', async () => {
    // FM is on S1's crew and is J-B's assignee, so both are visible.
    const r = await call('read', 'rf_schedule', {}, FM);
    assert.strictEqual(r.body.data.length, 2);
  });
  await test('an unrelated foreman sees NOTHING', async () => {
    const r = await call('read', 'rf_schedule', {}, OTHER);
    assert.strictEqual(r.body.data.length, 0);
  });

  console.log('\nset_status -- status only, and it is not a backdoor:');
  await test('a crew member on the day can mark it done', async () => {
    const r = await call('set_status', 'rf_schedule', { schedule_id: 'S1', status: 'done' }, CREW);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(store.schedule.filter((s) => s.schedule_id === 'S1')[0].status, 'done');
  });
  await test('an unrelated foreman cannot -> 403', async () => {
    assert.strictEqual((await call('set_status', 'rf_schedule', { schedule_id: 'S1', status: 'cancelled' }, OTHER)).code, 403);
  });
  await test('set_status CANNOT move the day, change the job, or restaff the crew', async () => {
    const before = JSON.parse(JSON.stringify(store.schedule.filter((s) => s.schedule_id === 'S1')[0]));
    await call('set_status', 'rf_schedule', { schedule_id: 'S1', status: 'confirmed', scheduled_date: '2027-01-01', job_id: 'J-A', crew: ['OTH'], location_id: 'LOC-X' }, CREW);
    const after = store.schedule.filter((s) => s.schedule_id === 'S1')[0];
    assert.strictEqual(after.scheduled_date, before.scheduled_date);
    assert.strictEqual(after.job_id, before.job_id);
    assert.deepStrictEqual(after.crew, before.crew);
    assert.strictEqual(after.location_id, before.location_id);
    assert.strictEqual(after.status, 'confirmed'); // only this moved
  });
  await test('an unknown status is refused -> 400', async () => {
    assert.strictEqual((await call('set_status', 'rf_schedule', { schedule_id: 'S1', status: 'vibing' }, CREW)).code, 400);
  });
  await test('missing schedule_id -> 400; unknown day -> 404', async () => {
    assert.strictEqual((await call('set_status', 'rf_schedule', { status: 'done' }, CREW)).code, 400);
    assert.strictEqual((await call('set_status', 'rf_schedule', { schedule_id: 'NOPE', status: 'done' }, CREW)).code, 404);
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed) process.exit(1);
})();
