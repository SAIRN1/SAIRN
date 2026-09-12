// tests/customer_delete_does_not_resurrect.js
//
// Run:  node tests/customer_delete_does_not_resurrect.js
//
// StoneDesk's customer delete UNDID ITSELF, and the user watched it succeed.
//
//   custDelete()          filtered the record out of the local array. That was
//                         all it did -- no server call of any kind.
//   saveSD3Data()         then wrote the SURVIVORS through, one row each, so
//                         the deleted customer's server row was never touched.
//   sdHydrateCustomers()  merges the server's rows back into the local list BY
//                         ID on the next load and never deletes.
//
// So the customer came back. The confirm said "Delete this customer?" with no
// caveat, which is the part that makes it expensive: there was no reason for
// anyone to check.
//
// IT ALSO REACHED A CUSTOMER. api/stonedesk-track.js resolves a live order
// tracking link against sd_customers by customer_id, so in the window between
// the local delete and the resurrection a customer could still read their job
// status from a record the shop believed was gone.
//
// SECTION 1 REPRODUCES THE DEFECT before asserting the fix, because a
// resurrection test that has never seen a resurrection is asserting a property
// of its own fixture. The mutant restores the pre-fix body and demands the
// record come back.
//
// THE THREE OUTCOMES ARE THE DESIGN, and section 3 is most of this file.
// Collapsing them into "it worked / it failed" forces a choice between a
// deletion that silently undoes itself and a delete button that stops working
// entirely -- and sd_customers does not exist in production today, so the
// not-provisioned path is the LIVE path, not a hypothetical one.
//
// The server half is api/sd-data-customer-soft-delete.test.js.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function grabAt(sig, indent) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  const m = html.slice(s).match(new RegExp('\\r?\\n' + indent + '\\};?(?=\\r?\\n)'));
  assert.ok(m, 'not terminated: ' + sig);
  return html.slice(s).slice(0, m.index + m[0].length);
}
function grabLine(sig) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  return html.slice(s, html.indexOf('\n', s));
}

// The real transport, including the status map custDelete's three-way decision
// reads. Taken from the file rather than re-declared, for the reason this week
// keeps producing: a hand-written copy of a declaration goes stale silently.
const LAYER = [
  grabLine('var _sdAuthRefused = {};'),
  grabLine('var _sdReadFailed  = {};'),
  grabLine('var _sdLastStatus  = {};')
].join('\n') + '\n\n' + [
  'function sdAuthWasRefused(resource) {',
  'function sdReadFailed(resource) {',
  'function sdFetchTimeoutSignal(){',
  'async function sdData(action, resource, payload) {'
].map(s => grabAt(s, '')).join('\n\n') + '\n\n'
  + grabLine('function sdLastStatus(resource) {') + '\n'
  + 'var SD_FETCH_TIMEOUT_MS = 15000;\n';

const UNIT = [
  grabAt('function saveSD3Data() {', ''),
  grabAt('async function sdHydrateCustomers() {', ''),
  grabAt('async function custDelete(id) {', '')
].join('\n\n');

// The pre-fix body, verbatim from the commit that introduced this suite. Used
// only by the mutant in section 1.
const PRE_FIX = [
  'async function custDelete(id) {',
  "  if (!confirm('Delete this customer?')) return;",
  '  sdCustomers = sdCustomers.filter(x => x.id !== id);',
  '  saveSD3Data();',
  '  renderCustomers();',
  '  runAlertScan();',
  '}'
].join('\n');

function build(opts) {
  opts = opts || {};
  const calls = { fetch: [], notes: [], confirms: [], closed: 0, stored: {} };
  const ctx = {
    console,
    sdCustomers: (opts.customers || []).map(c => Object.assign({}, c)),
    sdPhotos: [],
    st: (k, v) => { calls.stored[k] = v; return true; },
    renderCustomers: () => {},
    runAlertScan: () => {},
    custCloseDetail: () => { calls.closed++; },
    notify: (msg, kind) => calls.notes.push({ msg: String(msg), kind }),
    confirm: msg => { calls.confirms.push(String(msg)); return opts.confirm !== false; },
    sessionStorage: { getItem: () => 'tok', setItem: () => {} },
    sdDataFailed: () => {},
    sdLicenseKey: () => (opts.noLicence ? '' : 'SD-TEST-2026'),
    fetch: async (url, init) => {
      const body = init && init.body ? JSON.parse(init.body) : {};
      calls.fetch.push({ url: String(url), body });
      const r = (opts.route || (() => ({ status: 200, json: { ok: true, data: [] } })))(body);
      if (r && r.thrown) throw new Error(r.thrown);
      return { ok: r.status >= 200 && r.status < 300, status: r.status, json: async () => r.json };
    }
  };
  ctx.globalThis = ctx;
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(LAYER + '\n\n' + (opts.unit || UNIT), ctx,
    { filename: 'stonedesk-customer-delete-extract.js' });
  return { ctx, calls };
}

// A route that answers the delete however the arm wants, and always answers a
// READ with the row still present -- which is what makes resurrection possible
// and is exactly what the server filter removes.
function routes(deleteAnswer, readRows) {
  return body => {
    if (body.action === 'soft_delete') return deleteAnswer;
    if (body.action === 'read') return { status: 200, json: { ok: true, data: readRows || [] } };
    return { status: 200, json: { ok: true, data: null } };
  };
}
const CUST = { id: 'C-1', name: 'A. Customer', status: 'fabricating' };
const OK_DELETE = { status: 200, json: { ok: true, data: { _deleted_at: 'now' } } };

(async function main() {
  console.log('StoneDesk customers -- a delete that used to undo itself\n');

  // ══ 1. the defect, reproduced ════════════════════════════════════════════
  section('MUTATION: the pre-fix delete really does come back');

  await test('MUTANT: local-only delete + hydrate merge = the customer returns', async () => {
    const b = build({
      customers: [CUST],
      unit: [grabAt('function saveSD3Data() {', ''),
             grabAt('async function sdHydrateCustomers() {', ''),
             PRE_FIX].join('\n\n'),
      // The server still holds the row, because the pre-fix delete never told
      // it anything.
      route: routes(OK_DELETE, [CUST])
    });
    await b.ctx.custDelete('C-1');
    assert.strictEqual(b.ctx.sdCustomers.length, 0, 'precondition: it was not removed locally');
    await b.ctx.sdHydrateCustomers();
    assert.strictEqual(b.ctx.sdCustomers.length, 1,
      'the mutant did NOT resurrect the customer -- this suite would be proving nothing');
    assert.strictEqual(b.ctx.sdCustomers[0].id, 'C-1');
  });

  // ══ 2. the fix ═══════════════════════════════════════════════════════════
  section('a confirmed delete sticks, because the SERVER stops returning it');

  await test('the call is soft_delete on sd_customers, carrying only the id', async () => {
    const b = build({ customers: [CUST], route: routes(OK_DELETE, []) });
    await b.ctx.custDelete('C-1');
    const sent = b.calls.fetch[0];
    assert.strictEqual(sent.body.action, 'soft_delete');
    assert.strictEqual(sent.body.resource, 'sd_customers');
    assert.deepStrictEqual(sent.body.payload, { id: 'C-1' });
  });

  await test('and the hydrate no longer brings it back', async () => {
    const b = build({ customers: [CUST], route: routes(OK_DELETE, []) });
    await b.ctx.custDelete('C-1');
    assert.strictEqual(b.ctx.sdCustomers.length, 0);
    await b.ctx.sdHydrateCustomers();
    assert.strictEqual(b.ctx.sdCustomers.length, 0, 'the customer came back after a real delete');
  });

  await test('the confirm says the record is kept, not destroyed', async () => {
    const b = build({ customers: [CUST], confirm: false });
    await b.ctx.custDelete('C-1');
    const msg = b.calls.confirms[0] || '';
    assert.ok(/kept/i.test(msg), 'the confirm does not say the record is kept: ' + msg);
    assert.strictEqual(b.calls.fetch.length, 0, 'declining the confirm still called the server');
  });

  await test('the detail modal closes on success', async () => {
    const b = build({ customers: [CUST], route: routes(OK_DELETE, []) });
    await b.ctx.custDelete('C-1');
    assert.strictEqual(b.calls.closed, 1);
  });

  // ══ 3. three outcomes, not two ═══════════════════════════════════════════
  section('a delete the server did not confirm must not be applied locally');

  const KEEPS = [
    ['a 500', { status: 500, json: { error: { message: 'boom' } } }],
    ['a 502', { status: 502, json: { error: { message: 'boom' } } }],
    ['a network throw', { thrown: 'offline' }]
  ];
  for (const [label, answer] of KEEPS) {
    await test(label + ' KEEPS the customer -- removing it locally is what lets it return', async () => {
      const b = build({ customers: [CUST], route: routes(answer, [CUST]) });
      await b.ctx.custDelete('C-1');
      assert.strictEqual(b.ctx.sdCustomers.length, 1, 'the record was removed on an unconfirmed delete');
      const note = b.calls.notes[b.calls.notes.length - 1];
      assert.strictEqual(note.kind, 'err');
      assert.ok(/nothing was changed/i.test(note.msg), note.msg);
      assert.strictEqual(b.calls.closed, 0, 'the modal closed on a refused delete');
    });
  }

  for (const code of [401, 403]) {
    await test('a ' + code + ' keeps it and says it is a PERMISSION problem, not an outage', async () => {
      const b = build({ customers: [CUST],
        route: routes({ status: code, json: { error: { code: 'NO_SESSION' } } }, [CUST]) });
      await b.ctx.custDelete('C-1');
      assert.strictEqual(b.ctx.sdCustomers.length, 1);
      assert.ok(/signed in/i.test(b.calls.notes[b.calls.notes.length - 1].msg));
    });
  }

  // THE LIVE PATH. sd_customers does not exist in production today -- the
  // public-surface migration has never been run -- so every delete answers 503.
  // If that were treated as a failure the button would simply stop working.
  await test('a 503 (no table yet -- the state TODAY) removes it locally and sticks', async () => {
    const b = build({ customers: [CUST],
      route: routes({ status: 503, json: { error: { code: 'NOT_PROVISIONED' } } }, []) });
    await b.ctx.custDelete('C-1');
    assert.strictEqual(b.ctx.sdCustomers.length, 0, 'the delete button is dead until the migration runs');
    const note = b.calls.notes[b.calls.notes.length - 1];
    assert.strictEqual(note.kind, 'ok');
  });

  await test('a 404 (no server row for this id) removes it locally and sticks', async () => {
    const b = build({ customers: [CUST],
      route: routes({ status: 404, json: { error: { code: 'NOT_FOUND' } } }, []) });
    await b.ctx.custDelete('C-1');
    assert.strictEqual(b.ctx.sdCustomers.length, 0);
  });

  // UNDEFINED IS NOT A FAILURE, and this is the arm that says so. sdData()
  // returns null without calling anything when there is no licence key, so no
  // status is ever recorded -- and an unlicensed install has no server rows at
  // all. Treating "never called" like "the call failed" would make an offline
  // install unable to delete anything.
  await test('no licence: nothing is sent, and the local delete still works', async () => {
    const b = build({ customers: [CUST], noLicence: true, route: routes(OK_DELETE, [CUST]) });
    await b.ctx.custDelete('C-1');
    assert.strictEqual(b.calls.fetch.length, 0, 'an unlicensed install called the server');
    assert.strictEqual(b.ctx.sdCustomers.length, 0, 'an unlicensed install could not delete');
  });

  await test('a delete never writes the deleted record back through saveSD3Data', async () => {
    const b = build({ customers: [CUST, { id: 'C-2', name: 'B. Customer' }],
                      route: routes(OK_DELETE, []) });
    await b.ctx.custDelete('C-1');
    const written = b.calls.fetch.filter(f => f.body.action === 'write')
      .map(f => f.body.payload && f.body.payload.id);
    assert.ok(!written.includes('C-1'), 'saveSD3Data pushed the deleted customer back up');
    assert.ok(written.includes('C-2'), 'the surviving customer was not written through');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
