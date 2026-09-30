// api/sd-data-derive-charges.test.js
//
// REQUIREMENT: `alf_billing derive_charges` may show a line-by-line
//   reconciliation against a prior invoice ONLY when it actually read that
//   invoice's per-event lines. When an invoice is ON FILE but its lines cannot
//   be read, the honest answer is "cannot reconcile, and here is why" -- never
//   a precise net change derived from an empty comparison.
//
// Run:  node api/sd-data-derive-charges.test.js
//
// ── THE DEFECT THIS PINS, AND IT IS THE THIRD TIME THIS ONE SHAPE HAS BEEN
// ── FIXED IN THIS ONE BRANCH ──────────────────────────────────────────────
// api/sd-data.js already carries two comments about it, both written at the
// lines they fixed:
//
//   2026-09-04  an UNREADABLE prior-invoice read fell back to [], so "the
//               reconciliation reported EVERY derived line as new and
//               invoice_exists: false ... Somebody regenerates on the strength
//               of that."
//   2026-09-27  a prior invoice READ PERFECTLY WELL carries no `charge_lines`
//               key at all, so priorLines was ALWAYS [], and "every derived
//               line ADDED, nothing removed, nothing changed, net_change = the
//               ENTIRE amount -- while invoice_exists: true sat beside it,
//               which is what made the figure look like a comparison."
//
// The 2026-09-27 fix was written as
//
//     const priorRow = (invRows[0] && invRows[0].data) || null;
//     if (priorRow && !Array.isArray(priorRow.charge_lines)) { ...unavailable... }
//     else { reconcileAgainstInvoice(derived, (priorRow && priorRow.charge_lines) || []) }
//
// and that guard is REACHED ONLY WHEN `priorRow` IS TRUTHY. A row that exists
// with `data: null` -- or `data` set to anything that is not an object -- makes
// `priorRow` null, so the guard is skipped, the ELSE branch runs, and the tool
// reconciles against [] and reports every derived line ADDED with
// net_change = the whole invoice, beside `invoice_exists: true`.
//
// THAT IS THE EXACT SENTENCE THE 2026-09-27 COMMENT USES ABOUT THE BUG IT WAS
// CLOSING. The fix covered "row present, blob readable, key absent" and left
// "row present, blob NOT readable" on the old path -- which is the 2026-09-04
// case arriving through a different door, because a null blob is unreadable
// data and not absent data.
//
// ── WHY `invoice_exists` STAYS TRUE ───────────────────────────────────────
// It answers whether a row is on file, and a row with a null blob IS on file.
// Flipping it to false would be a second wrong answer: the caller would then be
// told to create an invoice that already exists. What must change is the
// reconciliation, and the arms below assert both halves -- exists TRUE and
// reconciliation REFUSED -- because either one alone can be satisfied wrongly.
//
// ── AND `data: {}` IS DELIBERATELY NOT THE SAME CODE ──────────────────────
// An empty-object blob is a readable invoice with no line detail (the
// 2026-09-27 case). A null blob is an invoice whose stored state could not be
// read at all. Both refuse to reconcile, and they refuse with DIFFERENT codes,
// because a person acting on the message needs to know which one they have.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['alf', 'derive', 'charges', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const { signSessionToken } = require('./_lib/auth');
const careCharges = require('./_lib/care-charges');

const HASH = 'alf-derive-charges-hash';
const APP = 'sairncare';
const ME = 'emp-owner-1';
const RESIDENT = 'res-1';
const MONTH = '2026-09';
const MED_RATE = 12.5;

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

// Two documented, given, priced administrations inside MONTH. Both become
// charge lines, so a false "everything added" reading has a distinctive total
// and the arms can name the number rather than only its shape.
const MAR_ROWS = [
  { entry_id: 'MAR-1', entry_type: 'administration',
    data: { status: 'given', administered_at: MONTH + '-05T08:00:00.000Z',
            medication_name: 'Metformin' } },
  { entry_id: 'MAR-2', entry_type: 'administration',
    data: { status: 'given', administered_at: MONTH + '-06T08:00:00.000Z',
            medication_name: 'Lisinopril' } }
];

// `priorInvoiceRows` is handed straight to the alf_billing read, so a test can
// drive the three states that matter: no row, a row whose blob is null, and a
// row whose blob is a real object.
function postgrestMock(priorInvoiceRows, calls) {
  return async function (url, opts) {
    const u = String(url);
    calls.push({ url: u, opts: opts || null });
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async function () {
        return [{ license_hash: HASH, employee_id: ME, role: 'owner', active: true }]; } };
    }
    if (/alf_mar\?/.test(u)) {
      return { ok: true, status: 200, json: async function () { return MAR_ROWS; } };
    }
    if (/alf_clients\?/.test(u)) {
      return { ok: true, status: 200, json: async function () { return [{ data: {} }]; } };
    }
    if (/alf_activities\?/.test(u)) {
      return { ok: true, status: 200, json: async function () { return []; } };
    }
    if (/alf_facility\?/.test(u)) {
      return { ok: true, status: 200,
               json: async function () { return [{ data: { med_admin_rate: MED_RATE } }]; } };
    }
    if (/alf_billing\?/.test(u)) {
      return { ok: true, status: 200,
               json: async function () { return priorInvoiceRows; } };
    }
    return { ok: true, status: 200, json: async function () { return []; } };
  };
}

function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: HASH,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: APP };
      }
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function derive(priorInvoiceRows) {
  const calls = [];
  const h = loadHandler(postgrestMock(priorInvoiceRows, calls));
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer KEY-FOR-' + HASH,
      'x-sd-auth': signSessionToken({ app: APP, employee_id: ME,
                                      role: 'owner', license_hash: HASH })
    },
    body: { action: 'derive_charges', resource: 'alf_billing', app_id: APP,
            payload: { resident_id: RESIDENT, month: MONTH } }
  }, res);
  return res;
}

// The two charge lines a correct derivation produces, in the shape a stored
// invoice would carry them -- used by the arm that drives a real reconciliation
// so "reconciled" is distinguishable from "reconciled against nothing".
function realPriorLines() {
  return [
    { event_id: 'MAR-1', type: 'medication_administration', date: MONTH + '-05',
      quantity: 1, unit_rate: MED_RATE, amount: MED_RATE },
    { event_id: 'MAR-2', type: 'medication_administration', date: MONTH + '-06',
      quantity: 1, unit_rate: MED_RATE, amount: MED_RATE }
  ];
}

(async () => {

section('0. THE FIXTURE IS NOT VACUOUS -- charges really are derived, or every '
      + 'arm below passes on an empty comparison');

await test('two priced administrations become two charge lines totalling '
  + (MED_RATE * 2), async () => {
    const res = await derive([]);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(res.body.ok, true, JSON.stringify(res.body));
    assert.strictEqual((res.body.lines || []).length, 2,
      'expected 2 derived lines, got ' + JSON.stringify(res.body.lines));
    assert.strictEqual(res.body.total, MED_RATE * 2,
      'total is ' + res.body.total + ' -- the fixture does not price anything, '
      + 'so a net_change assertion below would be comparing 0 with 0');
  });

section('1. THE DEFECT -- an invoice on file whose blob is NULL');

await test('data: null -- reconciliation is REFUSED, not computed against []',
  async () => {
    const res = await derive([{ entry_id: 'INV-' + RESIDENT + '-' + MONTH, data: null }]);
    assert.strictEqual(res.statusCode, 200, JSON.stringify(res.body));
    assert.strictEqual(res.body.invoice_exists, true,
      'the row IS on file; saying otherwise tells the caller to create an '
      + 'invoice that already exists');
    assert.strictEqual(res.body.reconciliation_vs_invoice, null,
      'reconciliation_vs_invoice is ' + JSON.stringify(res.body.reconciliation_vs_invoice)
      + ' -- a comparison was reported against an invoice whose lines were '
      + 'never read');
    assert.ok(res.body.reconciliation_unavailable,
      'no reconciliation_unavailable code, so nothing on the screen says why '
      + 'the comparison is missing');
    // A LENGTH, NOT `/\S{20}/`. The first draft of this arm used that regex and
    // it demanded twenty consecutive NON-SPACE characters, which no English
    // sentence has -- so it failed against a perfectly good reason and would
    // have passed against the string 'aaaaaaaaaaaaaaaaaaaa'. Inverted on both
    // sides.
    assert.ok(String(res.body.reconciliation_unavailable_reason || '').length >= 40,
      'the refusal carries no readable reason: '
      + JSON.stringify(res.body.reconciliation_unavailable_reason));
  });

await test('...and the refused case does NOT report every derived line as added '
  + 'with net_change = the whole invoice', async () => {
    const res = await derive([{ entry_id: 'INV-' + RESIDENT + '-' + MONTH, data: null }]);
    const rec = res.body.reconciliation_vs_invoice;
    assert.ok(!rec || rec.net_change !== MED_RATE * 2,
      'net_change came back ' + (rec && rec.net_change) + ', which is the entire '
      + 'invoice -- the exact false figure the 2026-09-27 comment describes');
  });

await test('a NULL blob and an EMPTY-OBJECT blob refuse with DIFFERENT codes -- '
  + 'unreadable state and absent line detail are not the same problem',
  async () => {
    const nul = await derive([{ entry_id: 'X', data: null }]);
    const empty = await derive([{ entry_id: 'X', data: {} }]);
    assert.ok(nul.body.reconciliation_unavailable, 'null blob did not refuse');
    assert.ok(empty.body.reconciliation_unavailable, 'empty blob did not refuse');
    assert.notStrictEqual(nul.body.reconciliation_unavailable,
                          empty.body.reconciliation_unavailable,
      'both refuse with ' + nul.body.reconciliation_unavailable
      + ' -- a person acting on the message cannot tell which they have');
  });

await test('a blob that is not an object at all (a string) also refuses',
  async () => {
    const res = await derive([{ entry_id: 'X', data: 'corrupted' }]);
    assert.strictEqual(res.body.invoice_exists, true);
    assert.strictEqual(res.body.reconciliation_vs_invoice, null,
      'a string blob was reconciled against');
    assert.ok(res.body.reconciliation_unavailable, 'no refusal code');
  });

section('2. THE CASES THAT MUST NOT CHANGE -- or the fix is a new defect');

await test('NO invoice on file: invoice_exists false, and every derived line '
  + 'genuinely IS new', async () => {
    const res = await derive([]);
    assert.strictEqual(res.body.invoice_exists, false);
    assert.ok(res.body.reconciliation_vs_invoice,
      'with no invoice on file there is nothing unreadable, so the comparison '
      + 'against [] is the RIGHT answer and must still be given');
    assert.strictEqual(res.body.reconciliation_vs_invoice.added.length, 2);
    assert.strictEqual(res.body.reconciliation_unavailable, undefined,
      'a refusal was emitted for a case that needs no refusal');
  });

await test('an invoice WITH real charge_lines reconciles, and reports no change',
  async () => {
    const res = await derive([{ entry_id: 'X',
                                data: { charge_lines: realPriorLines() } }]);
    assert.strictEqual(res.body.invoice_exists, true);
    assert.ok(res.body.reconciliation_vs_invoice,
      'a readable invoice with line detail was refused');
    assert.strictEqual(res.body.reconciliation_vs_invoice.added.length, 0,
      'lines already on the invoice were reported as newly added');
    assert.strictEqual(res.body.reconciliation_vs_invoice.net_change, 0,
      'net_change is ' + res.body.reconciliation_vs_invoice.net_change
      + ' against an identical invoice');
  });

await test('an invoice with a CHANGED amount still reports the change -- the '
  + 'reconciliation is not merely switched off', async () => {
    const lines = realPriorLines();
    lines[0].amount = 1;
    const res = await derive([{ entry_id: 'X', data: { charge_lines: lines } }]);
    const rec = res.body.reconciliation_vs_invoice;
    assert.ok(rec, 'no reconciliation at all');
    assert.strictEqual(rec.changed.length, 1,
      'the changed line was not detected: ' + JSON.stringify(rec.changed));
    assert.strictEqual(rec.net_change, MED_RATE - 1);
  });

section('3. KNOWN-BAD CONTROL -- the pre-fix expression on the same fixture, so '
      + 'arm 1 is reading the fix and not a fixture that never discriminated');

await test('the 2026-09-27 guard, replayed exactly, SKIPS a null blob and '
  + 'reconciles against [] -- every line added, net_change the whole invoice',
  async () => {
    const derived = careCharges.deriveCharges({
      month: MONTH, resident_id: RESIDENT,
      rate_card: { med_admin_rate: MED_RATE },
      events: MAR_ROWS.map(function (r) {
        return { id: r.entry_id, type: 'medication_administration',
                 resident_id: RESIDENT, date: r.data.administered_at.slice(0, 10),
                 description: r.data.medication_name };
      })
    });
    assert.strictEqual(derived.lines.length, 2, 'the control fixture derived nothing');

    // VERBATIM the shape api/sd-data.js carried before this fix.
    const invRows = [{ entry_id: 'X', data: null }];
    const priorRow = (invRows[0] && invRows[0].data) || null;
    const invoiceExists = !!(Array.isArray(invRows) && invRows.length);
    let unavailable, rec;
    if (priorRow && !Array.isArray(priorRow.charge_lines)) {
      unavailable = 'PRIOR_INVOICE_HAS_NO_CHARGE_LINES';
      rec = null;
    } else {
      rec = careCharges.reconcileAgainstInvoice(
        derived, (priorRow && priorRow.charge_lines) || []);
    }

    assert.strictEqual(invoiceExists, true);
    assert.strictEqual(unavailable, undefined,
      'the pre-fix guard refused a null blob, so it never had this hole and '
      + 'arm 1 proves nothing');
    assert.ok(rec, 'the pre-fix shape produced no reconciliation');
    assert.strictEqual(rec.added.length, 2,
      'the pre-fix shape did not report every line as added, so the fixture '
      + 'does not reproduce the reported defect');
    assert.strictEqual(rec.net_change, MED_RATE * 2,
      'the pre-fix shape did not report the whole invoice as the net change');
  });

await test('CONTROL: the same pre-fix shape is CORRECT for the empty-object '
  + 'blob -- which is why that half looked closed', async () => {
    const invRows = [{ entry_id: 'X', data: {} }];
    const priorRow = (invRows[0] && invRows[0].data) || null;
    // `{}` is truthy, so the 2026-09-27 guard IS reached. This is the arm that
    // shows the earlier fix was real and was simply reached by the wrong test.
    assert.ok(priorRow, 'an empty object should be truthy');
    assert.ok(priorRow && !Array.isArray(priorRow.charge_lines),
      'the 2026-09-27 guard would not have fired for {} either');
  });

console.log('\n' + (fail
  ? fail + ' arm(s) FAILED -- ' + pass + ' passed'
  : 'ok  sd-data-derive-charges: ' + pass + ' passed, 0 failed'));
process.exit(fail ? 1 : 0);

})();
