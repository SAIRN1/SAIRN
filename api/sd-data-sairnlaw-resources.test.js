// api/sd-data-sairnlaw-resources.test.js
// Plain node:assert tests. Run: node api/sd-data-sairnlaw-resources.test.js
//
// PIECE B. sairnlaw.html wrote TWENTY distinct resources across 31 call sites
// and api/_resources/sairnlaw.js registered FOUR. The other fifteen were
// refused by the resource allowlist before any credential mattered -- proven
// live against the deployed endpoint with a control, same bogus licence key
// both times and only the resource name different:
//
//   law_invoices -> 400 "resource must be one of ..."   (refused at the gate)
//   law_matters  -> 401 INVALID_LICENSE                 (past the gate)
//
// 23 call sites, including BILLABLE TIME, invoices, matter documents (six
// sites), operating-account transactions and bank statements. Every failure
// rendered as "server sync not yet enabled for this app".
//
// THE THING MOST WORTH ASSERTING IS NOT THAT THE BRANCH WORKS. It is that all
// four places that must agree DO agree: the client's write calls, the
// registry, the handler map, and the SQL. A resource missing from any one of
// them fails in a different and quieter way --
//
//   in the client but not the registry -> 400 at the allowlist   (this defect)
//   in the registry but no branch      -> "Unsupported action/resource"
//                                         (exactly what law_deadlines did, and
//                                         the note that branch still carries)
//   branch but no table                -> 503 NOT_PROVISIONED
//
// so the cross-check runs in every direction rather than one.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname + path.sep + '..';
const registry = require('./_resources/sairnlaw.js');
const merged = require('./_resources/index.js');
const SRC = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8').replace(/\r\n/g, '\n');
const HTML = fs.readFileSync(path.join(ROOT, 'sairnlaw.html'), 'utf8').replace(/\r\n/g, '\n');
const SQL = fs.readFileSync(path.join(ROOT, 'sql', 'sairnlaw_data_extended_schema.sql'), 'utf8').replace(/\r\n/g, '\n');

const LIC_HASH = 'test-hash';
function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
const mockReq = (body) => ({ method: 'POST', headers: { authorization: 'Bearer GOOD-KEY' }, body: body });
function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: { validateLicenseKey: async () => ({ valid: true, active: true, license_hash: LIC_HASH, trial_ends_at: null, stripe_subscription_id: null }) }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

const handlerBlock = (() => {
  const a = SRC.indexOf('const LAW_RESOURCES = {');
  assert.ok(a > 0, 'LAW_RESOURCES map not found in api/sd-data.js');
  const b = SRC.indexOf('const LEG_RESOURCES = {', a);
  return SRC.slice(a, b);
})();
const HANDLED = (() => {
  const map = handlerBlock.slice(0, handlerBlock.indexOf('};'));
  const out = {};
  (map.match(/law_\w+:\s*'\w+'/g) || []).forEach((p) => {
    const [k, v] = p.split(':').map((x) => x.trim().replace(/'/g, ''));
    out[k] = v;
  });
  return out;
})();
const CLIENT_WRITES = [...new Set([...HTML.matchAll(/sdnData\('write','(law_\w+)'/g)].map((m) => m[1]))];
const BESPOKE = ['law_clients', 'law_matters', 'law_trusttx', 'law_deadlines'];

let passed = 0, total = 0;
async function test(name, fn) {
  total++;
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

async function main() {
  console.log('api/sd-data.js -- SAIRNlaw extended resources');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
  process.env.SD_AUTH_SECRET = ['law', 'resources', 'fixture'].join('-');

  // ── the four-way cross-check ────────────────────────────────────────────
  await test('EVERY resource the client writes is registered -- the defect itself', () => {
    const missing = CLIENT_WRITES.filter((r) => registry.resources.indexOf(r) === -1);
    assert.deepStrictEqual(missing, [],
      'written by sairnlaw.html and refused at the allowlist: ' + missing.join(', '));
    assert.ok(CLIENT_WRITES.length >= 19, 'expected 19+ law writes in the client, found ' + CLIENT_WRITES.length);
  });

  await test('every registered resource has a HANDLER -- registering a name is not sufficient', () => {
    // A registered name with no branch passes the allowlist and falls through
    // to "Unsupported action/resource combination", which is exactly what
    // law_deadlines returned until its branch existed.
    const orphans = registry.resources.filter((r) => !HANDLED[r] && BESPOKE.indexOf(r) === -1);
    assert.deepStrictEqual(orphans, [], 'registered with no handler: ' + orphans.join(', '));
  });

  await test('every handled resource has a TABLE, and the id column matches', () => {
    Object.keys(HANDLED).forEach((r) => {
      assert.ok(SQL.indexOf('create table if not exists public.' + r + ' (') !== -1, 'no table for ' + r);
      assert.ok(SQL.indexOf('grant select, insert, update on public.' + r + ' to service_role;') !== -1, 'no grant for ' + r);
      const t = SQL.slice(SQL.indexOf('create table if not exists public.' + r + ' ('));
      const body = t.slice(0, t.indexOf(');'));
      assert.ok(body.indexOf('\n  ' + HANDLED[r] + ' text not null,') !== -1, r + ' has no ' + HANDLED[r] + ' column');
      assert.ok(body.indexOf('unique (license_hash, ' + HANDLED[r] + ')') !== -1, r + ' is not unique on (license_hash, ' + HANDLED[r] + ')');
    });
  });

  await test('no handler is orphaned the other way -- every mapped name is registered', () => {
    const extra = Object.keys(HANDLED).filter((r) => registry.resources.indexOf(r) === -1);
    assert.deepStrictEqual(extra, [], 'handled but unregistered: ' + extra.join(', '));
    assert.strictEqual(Object.keys(HANDLED).length, 15);
  });

  await test('the four bespoke resources were NOT folded into the generic map', () => {
    // law_matters and law_trusttx promote real columns (client_id, matter_id,
    // amount, type, status) a generic loop would not populate, and law_trusttx
    // carries a balance guard. Folding them in would drop both.
    BESPOKE.forEach((r) => assert.ok(!HANDLED[r], r + ' was folded into the generic map -- its promoted columns and guard would be lost'));
    BESPOKE.forEach((r) => assert.ok(SRC.indexOf("resource === '" + r + "'") > 0, r + ' lost its bespoke branch'));
  });

  await test('no law_ resource collides with another app', () => {
    registry.resources.forEach((r) => assert.strictEqual(merged.OWNER_BY_RESOURCE[r], 'sairnlaw', r + ' is not owned by sairnlaw'));
    assert.strictEqual(new Set(merged.RESOURCE_NAMES).size, merged.RESOURCE_NAMES.length, 'duplicate resource names platform-wide');
  });

  await test('the SQL grants no delete anywhere', () => {
    assert.ok(!/\bdelete\b/i.test(SQL.replace(/^--.*$/gm, '')), 'a delete grant appeared in the schema');
  });

  // ── the branch itself ───────────────────────────────────────────────────
  await test('a write reaches the store with the right id column and a derived license_hash', async () => {
    let sent = null;
    const handler = loadHandler(async (url, init) => {
      sent = { url: String(url), body: JSON.parse(init.body) };
      return { ok: true, status: 200, json: async () => [{ data: { id: 'TT-1' } }] };
    });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'law_timeentries', payload: { id: 'TT-1', matter_id: 'M-1', hours: 2.5 } }), res);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(sent.body.timeentry_id, 'TT-1');
    assert.strictEqual(sent.body.app_id, 'sairnlaw');
    assert.strictEqual(sent.body.license_hash, LIC_HASH);
    assert.ok(sent.url.indexOf('on_conflict=license_hash,timeentry_id') !== -1, sent.url);
  });

  await test('a read returns the rows and provisioned:true', async () => {
    const handler = loadHandler(async () => ({ ok: true, status: 200, json: async () => [{ data: { id: 'IV-1' } }] }));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'law_invoices' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.provisioned, true);
    assert.strictEqual(res.body.data[0].id, 'IV-1');
  });

  await test('an UNPROVISIONED read is provisioned:false, not an empty success', async () => {
    // "nothing saved yet" and "this was never migrated" must not collapse into
    // each other -- the client counts the second as a failure and says so.
    const handler = loadHandler(async () => ({ ok: false, status: 404, json: async () => ({}) }));
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'law_picases' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.provisioned, false);
    assert.deepStrictEqual(res.body.data, []);
  });

  await test('an UNPROVISIONED write names the SQL file to run', async () => {
    const handler = loadHandler(async () => ({ ok: false, status: 404, json: async () => ({}) }));
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'law_pimedical', payload: { id: 'PM-1' } }), res);
    assert.strictEqual(res.statusCode, 503);
    assert.strictEqual(res.body.error.code, 'NOT_PROVISIONED');
    assert.match(res.body.error.message, /sairnlaw_data_extended_schema\.sql/);
  });

  await test('a write with no payload.id is refused before any query', async () => {
    const handler = loadHandler(async () => { throw new Error('fetch must not be called'); });
    const res = mockRes();
    await handler(mockReq({ action: 'write', resource: 'law_barcerts', payload: { staff_name: 'x' } }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.match(res.body.error.message, /payload\.id is required/);
  });

  await test('every one of the fifteen answers on both verbs', async () => {
    for (const r of Object.keys(HANDLED)) {
      const rh = loadHandler(async () => ({ ok: true, status: 200, json: async () => [] }));
      const rr = mockRes();
      await rh(mockReq({ action: 'read', resource: r }), rr);
      assert.strictEqual(rr.statusCode, 200, r + ' read -> ' + rr.statusCode + ' ' + JSON.stringify(rr.body));
      const wh = loadHandler(async () => ({ ok: true, status: 200, json: async () => [{ data: { id: 'X' } }] }));
      const wr = mockRes();
      await wh(mockReq({ action: 'write', resource: r, payload: { id: 'X' } }), wr);
      assert.strictEqual(wr.statusCode, 200, r + ' write -> ' + wr.statusCode + ' ' + JSON.stringify(wr.body));
    }
  });

  await test('an unknown law_ name is still refused -- the allowlist did not become a wildcard', () => {
    assert.ok(!HANDLED['law_notathing']);
    assert.strictEqual(registry.resources.indexOf('law_notathing'), -1);
  });

  console.log('\n' + passed + ' / ' + total + ' passed');
  if (passed !== total) process.exitCode = 1;
}

main();
