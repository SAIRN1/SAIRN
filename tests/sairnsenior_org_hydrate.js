// tests/sairnsenior_org_hydrate.js
//
// Run:  node tests/sairnsenior_org_hydrate.js
//
// sen_branches and sen_applicants were written to the server, stored locally,
// and read back by nothing. Thirteen of this app's fifteen resources had a
// hydrate; these two did not. So a franchise branch added at head office was
// invisible on every other workstation -- brName() rendered "(unassigned)" for
// clients really assigned to it -- and an applicant entered by one recruiter
// was invisible to the next. Both sat in Postgres the whole time.
//
// FOUND BY tools/write_without_readback_check.py on its first real run, then
// confirmed by hand in a way that did NOT share the tool's assumption. That
// distinction is load-bearing: the same run flagged two SAIRNcare resources
// which turned out to be read through an object-literal call the tool could
// not see, and the "hand check" that confirmed them had used the same
// positional grep as the tool. A verification that shares the checker's blind
// spot verifies nothing.
//
// The checker can only see that a read EXISTS. These drive the function, so
// the merge semantics are held by something too -- a hydrate that reads both
// resources and then clobbers local edits would pass the checker and lose
// work.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'sairnsenior.html'), 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }

function fnBody(name) {
  const at = html.indexOf(name);
  assert.ok(at > 0, 'not found in sairnsenior.html: ' + name);
  const open = html.indexOf('{', at);
  let depth = 0;
  for (let i = open; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) return html.slice(at, i + 1); }
  }
  throw new Error('unbalanced braces');
}

function harness(opts) {
  opts = opts || {};
  const stored = {};
  const reads = [];
  const ctx = {
    JSON, Object, Array, Promise,
    senLicenseKey: () => (opts.noLicense ? '' : 'SEN-PINNACLE-2026'),
    ld: (k, d) => (opts.local && opts.local[k] ? JSON.parse(JSON.stringify(opts.local[k])) : d),
    st: (k, v) => { stored[k] = v; return true; },
    senData: (action, resource) => {
      reads.push(resource);
      const r = (opts.server || {})[resource];
      return Promise.resolve(r === undefined ? [] : r);
    },
    __stored: stored, __reads: reads,
  };
  vm.createContext(ctx);
  vm.runInContext(fnBody('function senHydrateOrg()'), ctx);
  return ctx;
}

test('both resources are read', async () => {
  const c = harness({});
  await c.senHydrateOrg();
  assert.strictEqual(c.__reads.slice().sort().join(','), 'sen_applicants,sen_branches');
});

test('server records not held locally are merged in', async () => {
  const c = harness({ server: { sen_branches: [{ id: 'B-1' }, { id: 'B-2' }] } });
  const merged = await c.senHydrateOrg();
  assert.strictEqual(merged, true);
  assert.strictEqual(c.__stored.sen_branches.map((x) => x.id).join(','), 'B-1,B-2');
});

test('a locally present id is NEVER overwritten', async () => {
  // The checker cannot see this. A hydrate that reads both resources and then
  // clobbers a local edit passes it and loses work.
  const c = harness({
    local: { sen_branches: [{ id: 'B-1', name: 'RENAMED HERE' }] },
    server: { sen_branches: [{ id: 'B-1', name: 'server copy' }, { id: 'B-2' }] },
  });
  await c.senHydrateOrg();
  const rows = c.__stored.sen_branches;
  assert.strictEqual(rows.length, 2, 'the merge duplicated or dropped a row');
  assert.strictEqual(rows.find((x) => x.id === 'B-1').name, 'RENAMED HERE');
});

test('a FAILED read leaves that resource alone', async () => {
  // senData() returns null for a failure, a missing licence and an
  // unprovisioned table alike. None of those may empty a local list.
  const c = harness({ local: { sen_applicants: [{ id: 'A-1' }] }, server: { sen_applicants: null } });
  await c.senHydrateOrg();
  assert.strictEqual(c.__stored.sen_applicants, undefined, 'a failed read wrote to local storage');
});

test('one resource failing does not stop the other merging', async () => {
  const c = harness({ server: { sen_branches: null, sen_applicants: [{ id: 'A-9' }] } });
  const merged = await c.senHydrateOrg();
  assert.strictEqual(merged, true);
  assert.strictEqual(c.__stored.sen_applicants.length, 1);
  assert.strictEqual(c.__stored.sen_branches, undefined);
});

test('nothing new means nothing written -- a no-op boot costs no storage write', async () => {
  const c = harness({ local: { sen_branches: [{ id: 'B-1' }] }, server: { sen_branches: [{ id: 'B-1' }] } });
  const merged = await c.senHydrateOrg();
  assert.strictEqual(merged, false);
  assert.deepStrictEqual(Object.keys(c.__stored), []);
});

test('no licence key means no reads at all', async () => {
  const c = harness({ noLicense: true });
  assert.strictEqual(await c.senHydrateOrg(), false);
  assert.strictEqual(c.__reads.length, 0);
});

test('it is CALLED at boot, and repaints both panels on a merge', () => {
  // The checker explicitly cannot tell whether a read is ever invoked. A
  // hydrate that exists and is never called reads clean there.
  const code = html.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
  const at = code.indexOf('senHydrateOrg().then(');
  assert.ok(at > 0, 'senHydrateOrg is never called');
  const after = code.slice(at, at + 260);
  assert.match(after, /brRender\(\)/, 'branches are merged but never repainted');
  assert.match(after, /hrRender\(\)/, 'applicants are merged but never repainted');
  assert.ok(code.lastIndexOf('init();', at) > 0, 'it should run after init() has painted local data');
});

(async () => {
  for (const item of queue) {
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
  console.log('\nsairnsenior_org_hydrate: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
