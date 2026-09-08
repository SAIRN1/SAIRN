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
  //
  // IT ONLY SAW DIRECT WRITERS UNTIL 2026-09-08, and a mutation probe is what
  // said so. Changing submitCharge to ask for 'dnt_payments' -- exactly the
  // defect this test exists to catch, in the function that reports the CHARGE
  // ledger -- left it green, because submitCharge contains no sdnData('write')
  // of its own; it calls addChargeEntry(). So the three functions carrying the
  // ledger's failure sentences were outside the walk entirely. A second hole
  // in the same walk as Fourth's finding 4, found by probing rather than by
  // reading, and the walk now follows ONE level of helper call. The map is
  // derived from the file, not listed here, so a new helper is covered by
  // existing it rather than by remembering to add it.
  const re = /(?:async\s+)?function\s+(\w+)\s*\(/g;
  const writesOf = {};
  {
    let d;
    const dre = /(?:async\s+)?function\s+(\w+)\s*\(/g;
    while ((d = dre.exec(html)) !== null) {
      let b;
      try { b = fnBodyAt(d.index); } catch (e) { continue; }
      const w = [...stripComments(b).matchAll(/sdnData\('write','(dnt_\w+)'/g)].map((x) => x[1]);
      if (w.length) writesOf[d[1]] = w;
    }
  }
  let m, checked = 0;
  const problems = [];
  while ((m = re.exec(html)) !== null) {
    let body;
    try { body = fnBodyAt(m.index); } catch (e) { continue; }
    const code = stripComments(body);
    const writes = [...code.matchAll(/sdnData\('write','(dnt_\w+)'/g)].map((x) => x[1]);
    Object.keys(writesOf).forEach((helper) => {
      if (helper === m[1]) return;
      if (new RegExp('\\b' + helper + '\\s*\\(').test(code)) {
        writesOf[helper].forEach((w) => { if (writes.indexOf(w) === -1) writes.push(w); });
      }
    });
    if (!writes.length) continue;
    if (code.indexOf('syncResult?') === -1 && code.indexOf('!result.syncResult') === -1
        && code.indexOf('!syncResult') === -1) continue;
    // TIGHTENED 2026-09-08, on Fourth's finding 4. This used to exempt any
    // function containing the BARE STRING 'dntLastErrText(' without looking at
    // which resource it asked for -- so a path could ask for another resource
    // entirely and pass. The four paths that took the exemption were
    // hand-checked as correct at the time, which is exactly the kind of fact
    // that stops being true without anyone noticing. Both helpers are now
    // collected and both are checked against what the function writes.
    const asked = [...code.matchAll(/dntWriteFailText\('(dnt_\w+)'/g)].map((x) => x[1])
      .concat([...code.matchAll(/dntLastErrText\('(dnt_\w+)'/g)].map((x) => x[1]));
    if (!asked.length) {
      // A dedicated writer surfaces the error itself. A path that reports
      // NOTHING is not fine, and neither is one that asks with a variable --
      // this walk cannot check that pairing, so it must not silently pass it.
      //
      // THE ONE HONEST EXEMPTION: a helper that HANDS THE OUTCOME BACK. Adding
      // `refused` to addChargeEntry/addPaymentEntry on 2026-09-08 put the token
      // `!syncResult` in their bodies, which pulled two functions into this walk
      // that deliberately say nothing -- they return {syncResult, refused} and
      // their callers do the talking. Written as a named exemption rather than
      // by loosening the entry condition, because the callers are asserted
      // separately below and this must not become a way for a silent path to
      // pass.
      const handsBack = /return\s*\{[^}]*syncResult:/.test(code);
      if (!handsBack && code.indexOf('dntSettingsWrite(') === -1) {
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
// THE HARNESS RUNS THE REAL sdnData(), NOT A STUB THAT RETURNS null.
//
// The previous version stubbed sdnData to `Promise.resolve(refuse ? null : x)`,
// which encoded the very assumption Fourth's review overturned: that every null
// means the same thing. A stub written in the shape I already believed could
// never have caught it. So the fake is one layer lower -- at fetch() -- and the
// classification code under test is the file's own.
//
// (The same lesson landed the same week on the write-without-readback checker:
// hand-verifying with the tool's own grep reproduced its blind spot instead of
// testing it. A check that shares the assumption verifies nothing.)
section('sdnData tells a REFUSAL from a row the server never saw');

const MODES = {
  accepted: () => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ok: true, data: [{ id: 'X' }] }) }),
  // A real 400 from api/sd-data.js: the server looked at the row and said no,
  // in its own words, which are worth showing.
  refused: () => Promise.resolve({
    ok: false, status: 400,
    json: () => Promise.resolve({ ok: false, error: { code: 'INVALID_PAYMENT', message: 'A payment amount must be a number greater than zero.' } }),
  }),
  // A Vercel HTML error page. r.json() REJECTS, so this lands in the same
  // .catch as an offline save and used to render as "Unexpected token '<'".
  htmlErrorPage: () => Promise.resolve({
    ok: false, status: 500,
    json: () => Promise.reject(new SyntaxError('Unexpected token \'<\', "<!DOCTYPE "... is not valid JSON')),
  }),
  offline: () => Promise.reject(new TypeError('Failed to fetch')),
  // A 5xx that DOES parse. The server errored; it did not judge the row.
  serverError: () => Promise.resolve({ ok: false, status: 503, json: () => Promise.resolve({ ok: false }) }),
};

function harness(mode, opts) {
  opts = opts || {};
  const calls = { sent: [], stored: [], warned: [] };
  const ctx = {
    JSON, Object, Array, Number, Math, Promise, SyntaxError, TypeError,
    console: { warn: (...a) => calls.warned.push(a.join(' ')), error: () => {} },
    DATA_API: '/api/sd-data', APP_ID: 'sairndental',
    dntHeaders: () => ({}),
    dntLicenseKey: () => (opts.noLicence ? '' : 'DNT-TEST-2026'),
    fetch: () => MODES[mode](),
    dntLastErr: {},
    patients: () => [{ id: 'PT-1', insurance_payer: 'Delta' }],
    computeEstimatedInsurance: () => ({ amount: 40, found: true }),
    charges: () => [], payments: () => [],
    st: (k, v) => { calls.stored.push({ key: k, rows: v.length }); return !opts.storageFull; },
    newId: (p) => p + '-1',
    dntLocalToday: () => '2026-09-05',
    __calls: calls,
  };
  vm.createContext(ctx);
  vm.runInContext([
    fnBody('function sdnData('),
    fnBody('function dntLastErrCode('),
    fnBody('function dntLastErrText('),
    fnBody('function dntWriteRefused('),
    fnBody('function dntWriteFailText('),
    fnBody('async function addChargeEntry('),
    fnBody('async function addPaymentEntry('),
  ].join('\n'), ctx);
  return ctx;
}

test('an OFFLINE save never shows the raw browser exception', async () => {
  const c = harness('offline');
  await c.sdnData('write', 'dnt_charges', { id: 'CH-1' });
  assert.strictEqual(c.dntLastErrCode('dnt_charges'), 'NETWORK', 'the code should still record what happened');
  assert.strictEqual(c.dntLastErrText('dnt_charges'), '',
    'a fetch rejection reached the user as "Failed to fetch" instead of the sentence saying nothing was saved');
  const shown = c.dntWriteFailText('dnt_charges', 'The charge was not saved -- nothing was recorded on this device or the server.');
  assert.strictEqual(shown.indexOf('Failed to fetch'), -1, 'the exception displaced the fallback');
  assert.match(shown, /nothing was recorded/);
  assert.ok(c.__calls.warned.join(' ').indexOf('Failed to fetch') >= 0,
    'the exception should still be in the console -- suppressed for the user, not destroyed');
});

test('a Vercel HTML error page does not become the message either', async () => {
  const c = harness('htmlErrorPage');
  await c.sdnData('write', 'dnt_payments', { id: 'PM-1' });
  assert.strictEqual(c.dntLastErrText('dnt_payments'), '');
  const shown = c.dntWriteFailText('dnt_payments', 'The payment was not saved -- nothing was recorded on this device or the server.');
  assert.strictEqual(shown.indexOf('not valid JSON'), -1);
  assert.match(shown, /nothing was recorded/);
});

test("a REFUSAL still shows the server's own words -- that half must not regress", async () => {
  const c = harness('refused');
  await c.sdnData('write', 'dnt_payments', { id: 'PM-1' });
  assert.strictEqual(c.dntLastErrText('dnt_payments'), 'A payment amount must be a number greater than zero.');
  assert.strictEqual(c.dntWriteFailText('dnt_payments', 'generic'), 'A payment amount must be a number greater than zero.');
  assert.strictEqual(c.dntWriteRefused('dnt_payments'), true);
});

test('NETWORK, a 5xx and an HTML page are all NOT refusals', async () => {
  for (const mode of ['offline', 'htmlErrorPage', 'serverError']) {
    const c = harness(mode);
    await c.sdnData('write', 'dnt_charges', { id: 'CH-1' });
    assert.strictEqual(c.dntWriteRefused('dnt_charges'), false, mode + ' was classed as a refusal');
  }
});

test('no licence does not inherit an earlier failure of the same resource', async () => {
  // Fourth's finding 4, second half: this branch returned null without touching
  // dntLastErr, so a stale server sentence was shown as the reason.
  const c = harness('refused');
  await c.sdnData('write', 'dnt_payments', { id: 'PM-1' });
  assert.strictEqual(c.dntLastErrText('dnt_payments'), 'A payment amount must be a number greater than zero.');
  c.dntLicenseKey = () => '';
  await c.sdnData('write', 'dnt_payments', { id: 'PM-2' });
  assert.strictEqual(c.dntLastErrCode('dnt_payments'), 'NO_LICENCE');
  assert.strictEqual(c.dntLastErrText('dnt_payments'), '',
    "the previous refusal's sentence was shown as the reason for an unrelated failure");
  assert.strictEqual(c.dntWriteRefused('dnt_payments'), false);
});

// ═══════════════════════════════════════════════════════════════════════════
section('a REFUSED row is kept nowhere; a row the server never saw is not lost');

test('a REFUSED charge is stored nowhere', async () => {
  const c = harness('refused');
  const r = await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  assert.strictEqual(r.syncResult, null);
  assert.strictEqual(r.refused, true);
  assert.strictEqual(c.__calls.stored.length, 0,
    'a charge the server refused stayed in this device ledger -- patientBalance() and dnAging() would count it');
});

test('a REFUSED payment is stored nowhere', async () => {
  const c = harness('refused');
  const r = await c.addPaymentEntry('PT-1', 100, 'Cash');
  assert.strictEqual(r.syncResult, null);
  assert.strictEqual(r.refused, true);
  assert.strictEqual(c.__calls.stored.length, 0);
});

test('an OFFLINE charge is KEPT locally rather than dropped', async () => {
  // The defect Fourth found: a practice on a flaky connection lost every charge
  // and payment it entered, because addChargeEntry returned early on ANY null.
  const c = harness('offline');
  const r = await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  assert.strictEqual(r.syncResult, null);
  assert.strictEqual(r.refused, false);
  assert.deepStrictEqual(c.__calls.stored.map((x) => x.key), ['dnt_charges_list'],
    'the charge was lost -- not on the server, not on the device, nowhere');
});

test('an OFFLINE payment is KEPT locally rather than dropped', async () => {
  const c = harness('offline');
  const r = await c.addPaymentEntry('PT-1', 100, 'Cash');
  assert.strictEqual(r.refused, false);
  assert.deepStrictEqual(c.__calls.stored.map((x) => x.key), ['dnt_payments_list']);
});

test('a 5xx and a missing licence keep the row too', async () => {
  const a = harness('serverError');
  await a.addChargeEntry('PT-1', '', 'PR-1', 100);
  assert.strictEqual(a.__calls.stored.length, 1, 'a 5xx dropped the charge');
  const b = harness('accepted', { noLicence: true });
  await b.addPaymentEntry('PT-1', 100, 'Cash');
  assert.strictEqual(b.__calls.stored.length, 1, 'an unlicensed device dropped the payment');
});

test('KEEPING a row is a claim, and a full localStorage makes it false', async () => {
  // Introduced BY this fix and closed in the same pass: "recorded on this
  // device only" is a promise about local storage, and st() can fail. It was
  // safe to ignore its return while a kept row implied the server already had
  // it. It is not safe now.
  const ok = harness('offline');
  const r1 = await ok.addChargeEntry('PT-1', '', 'PR-1', 100);
  assert.strictEqual(r1.kept, true);
  const full = harness('offline', { storageFull: true });
  const r2 = await full.addChargeEntry('PT-1', '', 'PR-1', 100);
  assert.strictEqual(r2.kept, false, 'a failed local write still reported the row as kept');
  const p = await harness('offline', { storageFull: true }).addPaymentEntry('PT-1', 100, 'Cash');
  assert.strictEqual(p.kept, false);
});

test('all three ledger callers read `kept` before promising the device has it', () => {
  ['async function submitCharge()', 'async function submitPayment()', 'async function submitCompleteVisit()'].forEach((f) => {
    const code = stripComments(fnBody(f));
    assert.ok(code.indexOf('result.kept') > 0,
      f + ' says the row is on this device without checking that it landed there');
    assert.match(code, /NOT saved anywhere/, f + ' has no sentence for "nowhere at all"');
  });
});

test('an ACCEPTED charge and payment are both stored', async () => {
  const c = harness('accepted');
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

test('a REFUSED payment leaves the amount in the box; a kept one clears it', () => {
  const code = stripComments(fnBody('async function submitPayment()'));
  const guard = code.indexOf('if(!result.syncResult)');
  const refusedBranch = code.indexOf('if(result.refused)');
  const clear = code.indexOf("$('pm-add-amount').value=''");
  assert.ok(guard > 0 && clear > guard,
    'the input is cleared before the write is known to have landed -- the amount is gone with the message');
  // Tighter than the index check above, which would pass even if the refused
  // path cleared the box: the refused branch must RETURN before any clear.
  assert.ok(refusedBranch > 0, 'submitPayment no longer tells a refusal from an unreachable server');
  const refusedBody = code.slice(refusedBranch, clear);
  assert.match(refusedBody, /return;/,
    'the refused branch falls through to the clear -- the amount the server rejected is gone from the box');
});

test('both submit paths tell a REFUSAL from a server they could not reach', () => {
  ['async function submitCharge()', 'async function submitPayment()'].forEach((f) => {
    const code = stripComments(fnBody(f));
    assert.ok(code.indexOf('result.refused') > 0, f + ' reports one sentence for two different facts');
    assert.match(code, /THIS DEVICE ONLY/,
      f + ' does not say the row is on this device and nowhere else');
    assert.match(code, /will not upload by itself/,
      f + ' implies the row will sync later -- there is no outbound retry queue in this app');
  });
});

// ── FINDING 3, and it is the one a static assertion would have missed ──────
// toast() is one element setting textContent, so the LAST call wins. The old
// code let setAppointmentStatus() toast its honest failure and then wrote
// 'Visit completed, charge added' over the top of it. What matters is not that
// a guard exists, it is which sentence is on screen when the dust settles.
function visitHarness(apptSynced) {
  const toasts = [];
  const ctx = {
    JSON, Object, Array, Number, Math, Promise,
    cvAppointmentId: 'AP-1',
    appointments: () => [{ id: 'AP-1', patient_id: 'PT-1', procedure_type_id: 'PR-1', status: 'Confirmed' }],
    $: () => ({ value: '100' }),
    toast: (m) => toasts.push(m),
    closeCompleteVisitModal: () => {},
    addChargeEntry: () => Promise.resolve({ rec: { id: 'CH-1' }, syncResult: [{ id: 'CH-1' }], refused: false }),
    setAppointmentStatus: () => Promise.resolve({ appt: { id: 'AP-1' }, syncResult: apptSynced ? [{ id: 'AP-1' }] : null }),
    dntWriteFailText: (r, fb) => fb,
    __toasts: toasts,
  };
  vm.createContext(ctx);
  vm.runInContext(fnBody('async function submitCompleteVisit()'), ctx);
  return ctx;
}

test('a FAILED appointment write does not get announced as a completed visit', async () => {
  const c = visitHarness(false);
  await c.submitCompleteVisit();
  const last = c.__toasts[c.__toasts.length - 1];
  assert.notStrictEqual(last, 'Visit completed, charge added',
    'the honest failure was overwritten -- the visit reads Completed here and Confirmed everywhere else');
  assert.match(last, /VISIT STATUS was not/, 'the message does not say which half failed');
  assert.match(last, /charge WAS recorded/, 'the message does not say the charge landed, which it did');
});

test('a fully successful visit still says so', async () => {
  const c = visitHarness(true);
  await c.submitCompleteVisit();
  assert.strictEqual(c.__toasts[c.__toasts.length - 1], 'Visit completed, charge added');
});

test('setAppointmentStatus returns whether it landed, or the check above is blind', () => {
  const code = stripComments(fnBody('async function setAppointmentStatus('));
  assert.match(code, /return\s*\{appt:a,\s*syncResult:syncResult\}/,
    'it returns the appointment alone again -- submitCompleteVisit cannot tell a synced status change from a local-only one');
});

test('submitCharge stops after a refusal instead of announcing success', () => {
  const code = stripComments(fnBody('async function submitCharge()'));
  const guard = code.indexOf('if(!result.syncResult)');
  const success = code.indexOf("toast('Charge added')");
  assert.ok(guard > 0 && success > guard);
  assert.match(code.slice(guard, success), /return;/,
    'submitCharge falls through to "Charge added" after a failed write');
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
