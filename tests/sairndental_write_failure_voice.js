// tests/sairndental_write_failure_voice.js
//
// Run:  node tests/sairndental_write_failure_voice.js
//
// Seventeen save paths in sairndental.html reported EVERY failure as
//
//   "Saved on this device only -- server sync not yet enabled for this app"
//
// and that sentence is FALSE. Sync is enabled: DNT_SYNC_RESOURCES lists sixteen
// resources and dntSyncFromServer() reads all of them. It is not a stale note
// about a feature that is coming; it is a wrong reason shown instead of the
// real one, on every failure, for years of app time.
//
// IT GOT WORSE ON 2026-09-04, by this session's own hand. api/sd-data.js now
// REFUSES a bad dnt_payments, dnt_charges or dnt_coverage_rules write with a
// 400 that says exactly what to fix. Every one of those messages was being
// thrown away and replaced with a claim about a disabled feature. sdnData()
// already recorded the server's own words per resource in dntLastErr; nothing
// outside the provider paths read them.
//
// TWO THINGS ARE ASSERTED, and the second is the one that could rot quietly:
//   1. the false sentence is gone from CODE (it survives in comments, which is
//      deliberate -- the record of what it said is worth keeping);
//   2. each failure branch asks for the error of the resource that function
//      actually WRITES. A helper called with the wrong resource name returns
//      another resource's stale message, which reads as a real explanation and
//      is worse than the generic one it replaced.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'sairndental.html'), 'utf8').replace(/\r\n/g, '\n');
const codeOnly = html.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');

let pass = 0, fail = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }
function section(t) { queue.push({ section: t }); }

function fnBodyAt(at) {
  const open = html.indexOf('{', at);
  let depth = 0;
  for (let i = open; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) return html.slice(at, i + 1); }
  }
  throw new Error('unbalanced braces');
}
function fnBody(name) {
  const at = html.indexOf(name);
  assert.ok(at > 0, 'not found in sairndental.html: ' + name);
  return fnBodyAt(at);
}
const stripComments = (src) => src.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');

// ═══════════════════════════════════════════════════════════════════════════
section('the false sentence is gone from code');

test('no CODE line still claims server sync is not enabled', () => {
  const hits = codeOnly.split('\n').filter((l) => l.indexOf('sync not yet enabled') !== -1);
  assert.deepStrictEqual(hits, [], 'still claimed on ' + hits.length + ' code line(s)');
});

test('...and it IS still present in comments, deliberately', () => {
  // The record of what the message said is worth keeping. If this ever fails,
  // someone scrubbed the history along with the defect.
  assert.ok(html.indexOf('sync not yet enabled') > 0, 'the comment record of the old wording was removed too');
});

test('sync really is enabled, which is what made the sentence false', () => {
  // Asserted rather than asserted-about: the claim "sync is enabled" is the
  // whole basis for calling the old message wrong.
  const list = fnBody('var DNT_SYNC_RESOURCES=[');
  const count = (list.match(/\['dnt_/g) || []).length;
  assert.ok(count >= 10, 'expected a real sync list, found ' + count + ' entries');
  assert.ok(html.indexOf('async function dntSyncFromServer()') > 0);
});

// ═══════════════════════════════════════════════════════════════════════════
section('every failure branch asks for the RIGHT resource');

test('each write path names the resource it actually writes', () => {
  // Walk every function that contains a dnt_* write and a syncResult toast.
  // A helper called with the wrong resource returns another resource's stale
  // message -- which reads as a real explanation and is worse than a generic
  // one, so the pairing is what gets asserted, not the presence of the call.
  const re = /(?:async\s+)?function\s+(\w+)\s*\(/g;
  let m, checked = 0;
  const problems = [];
  while ((m = re.exec(html)) !== null) {
    let body;
    try { body = fnBodyAt(m.index); } catch (e) { continue; }
    const code = stripComments(body);
    const writes = [...code.matchAll(/sdnData\('write','(dnt_\w+)'/g)].map((x) => x[1]);
    if (!writes.length) continue;
    if (code.indexOf('syncResult?') === -1 && code.indexOf('!result.syncResult') === -1
        && code.indexOf('!syncResult') === -1) continue;
    const asked = [...code.matchAll(/dntWriteFailText\('(dnt_\w+)'/g)].map((x) => x[1]);
    if (!asked.length) {
      // Some paths surface the error another way (dntLastErrText directly, or
      // a dedicated writer). Those are fine; a path that reports NOTHING is not.
      if (code.indexOf('dntLastErrText(') === -1 && code.indexOf('dntSettingsWrite(') === -1) {
        problems.push(m[1] + ' writes ' + writes.join('/') + ' and reports no real reason on failure');
      }
      continue;
    }
    checked++;
    asked.forEach((a) => {
      if (writes.indexOf(a) === -1) {
        problems.push(m[1] + " asks for '" + a + "' but writes '" + writes.join('/') + "'");
      }
    });
  }
  assert.ok(checked >= 12, 'expected to check a dozen or more write paths, checked ' + checked);
  assert.deepStrictEqual(problems, [], problems.join('; '));
});

test('the helper falls back rather than showing an empty toast', () => {
  const h = stripComments(fnBody('function dntWriteFailText('));
  assert.match(h, /dntLastErrText\(resource\)\|\|fallback\|\|/,
    'a missing server message would render as an empty toast');
});

// ═══════════════════════════════════════════════════════════════════════════
section('the two ledger writes I made refusable do not keep a refused row');

function ledgerHarness(opts) {
  opts = opts || {};
  const calls = { sent: [], stored: [] };
  const ctx = {
    JSON, Object, Array, Number, Math, Promise,
    patients: () => [{ id: 'PT-1', insurance_payer: 'Delta' }],
    computeEstimatedInsurance: () => ({ amount: 40, found: true }),
    charges: () => [], payments: () => [],
    st: (k, v) => { calls.stored.push({ key: k, rows: v.length }); return true; },
    newId: (p) => p + '-1',
    dntLocalToday: () => '2026-09-04',
    sdnData: (a, r, payload) => { calls.sent.push({ resource: r, payload }); return Promise.resolve(opts.refuse ? null : payload); },
    __calls: calls,
  };
  vm.createContext(ctx);
  vm.runInContext(fnBody('async function addChargeEntry(') + '\n' + fnBody('async function addPaymentEntry('), ctx);
  return ctx;
}

test('a REFUSED charge is stored nowhere', async () => {
  const c = ledgerHarness({ refuse: true });
  const r = await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  assert.strictEqual(r.syncResult, null);
  assert.strictEqual(c.__calls.stored.length, 0,
    'a charge the server refused stayed in this device ledger -- patientBalance() and dnAging() would count it');
});

test('a REFUSED payment is stored nowhere', async () => {
  const c = ledgerHarness({ refuse: true });
  const r = await c.addPaymentEntry('PT-1', 100, 'Cash');
  assert.strictEqual(r.syncResult, null);
  assert.strictEqual(c.__calls.stored.length, 0);
});

test('an ACCEPTED charge and payment are both stored', async () => {
  const c = ledgerHarness({});
  await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  await c.addPaymentEntry('PT-1', 100, 'Cash');
  assert.deepStrictEqual(c.__calls.stored.map((x) => x.key), ['dnt_charges_list', 'dnt_payments_list']);
});

test('the server call happens BEFORE the local store, in both', () => {
  ['async function addChargeEntry(', 'async function addPaymentEntry('].forEach((f) => {
    const code = stripComments(fnBody(f));
    const sent = code.indexOf("sdnData('write'");
    const stored = code.indexOf('st(');
    assert.ok(sent > 0 && stored > sent, f + ' writes locally before the server has taken it');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
section('the callers stop pretending too');

test('a refused visit charge does NOT mark the appointment completed', () => {
  // The button says "Visit completed, charge added". Completing the
  // appointment while the charge went nowhere is a visit that looks billed and
  // is not.
  const code = stripComments(fnBody('async function submitCompleteVisit()'));
  const guard = code.indexOf('if(!result.syncResult)');
  const complete = code.indexOf("setAppointmentStatus(a.id,'Completed')");
  assert.ok(guard > 0, 'no refusal guard');
  assert.ok(complete > guard, 'the appointment is completed before the charge is known to have landed');
  assert.match(code, /was not marked completed/, 'the message does not say the visit was left alone');
});

test('a refused payment leaves the amount in the box to correct', () => {
  const code = stripComments(fnBody('async function submitPayment()'));
  const guard = code.indexOf('if(!result.syncResult)');
  const clear = code.indexOf("$('pm-add-amount').value=''");
  assert.ok(guard > 0 && clear > guard,
    'the input is cleared before the write is known to have landed -- the amount is gone with the message');
});

test('submitCharge stops after a refusal instead of announcing success', () => {
  const code = stripComments(fnBody('async function submitCharge()'));
  assert.match(code, /if\(!result\.syncResult\)\{toast\(dntWriteFailText\('dnt_charges'/);
  assert.match(code, /return;\}\n\s*toast\('Charge added'\)/);
});

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
  console.log('\nsairndental_write_failure_voice: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
