// tests/sairnlaw_billable_rate.js
//
// Run:  node tests/sairnlaw_billable_rate.js
//
// ── THE WORK WAS RECORDED AND THE FEE WAS NOT ──────────────────────────────
// `saveTime()` in sairnlaw.html validated matter_id (required) and hours
// (> 0), and then wrote the rate like this:
//
//     rate: Number($('ttrate').value) || 0
//
// A blank, unparseable or missing rate became ZERO. Silently, with no
// complaint, at either end -- `rate` appeared in no validator anywhere in
// api/. `saveInvoice()` computes the invoice total as hours x rate, so such an
// hour adds $0.00 to the bill while rendering in the billing table as an
// ordinary billable hour: the work is on the record, the fee is not, and
// nothing downstream reports it.
//
// THIS IS THE CODELESS-HOUR DEFECT ONE FIELD OVER, and arguably worse. A
// codeless hour at least shows '--' in the billing table's code column; a
// zero-rate hour shows a number. api/_lib/law-timeentry.js was built three
// days earlier to refuse the first and its review named matter_id and hours as
// the two fields left to the client -- there were THREE, and the third is the
// one with the money on it.
//
// FOUND 2026-09-21 by cc as FINDING 3 of the independent review of that
// module (obligation 2026-09-18T23:44:59Z).
//
// ── ONLY WHEN THE ENTRY IS BILLABLE, AND THAT BOUND IS ASSERTED BOTH WAYS ──
// A no-charge entry legitimately carries rate 0 -- that is what no-charge
// MEANS -- so refusing it would refuse real work. `billable` is read here the
// same way every reader in sairnlaw.html reads it (`t.billable && ...`), which
// makes an ABSENT billable field no-charge rather than an error. A refusal
// that over-reaches is not a stricter gate, it is a different defect; the arms
// below pin the permissive side as hard as the refusing side.
//
// ── WHAT IS STILL NOT CHECKED, AND IT IS THE SAME $0.00 LINE ───────────────
// `hours` remains unvalidated at the SERVER, and hours 0 produces an identical
// $0.00 line. It is deliberately not bundled here -- the scope asked for was
// the rate -- and it is recorded in docs/SAIRN-OPEN-WORK-INDEX.md rather than
// left to be rediscovered. An arm below asserts that gap is REAL, so this
// suite cannot quietly start covering it and leave the row stale.
//
// The negative control is tests/run_sairnlaw_billable_rate_sabotage_probe.py,
// which plants the zero-rate defect back and requires this suite to go RED.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairnlaw.html'), 'utf8').replace(/\r\n/g, '\n');
const { timeEntryProblem, NO_RATE_MESSAGE } = require(path.join(ROOT, 'api/_lib/law-timeentry.js'));

let pass = 0, fail = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }
function section(t) { queue.push({ section: t }); }

function fnBody(name) {
  const at = html.indexOf(name);
  assert.ok(at > 0, 'not found in sairnlaw.html: ' + name);
  const open = html.indexOf('{', at);
  let depth = 0;
  for (let i = open; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) return html.slice(at, i + 1); }
  }
  throw new Error('unbalanced braces reading ' + name);
}

const OK = { billing_code: 'L100', hours: 2, rate: 350, billable: true };
const entry = (patch) => Object.assign({}, OK, patch);

// ═══════════════════════════════════════════════════════════════════════════
section('1. the validator refuses a billable hour that would bill nothing');

test('rate 0 on a BILLABLE hour is refused, and the message says why', () => {
  const p = timeEntryProblem(entry({ rate: 0 }));
  assert.ok(p, 'rate 0 passed');
  assert.match(p, /hours x rate/, p);
  assert.match(p, /\$0\.00/, p);
  assert.match(p, /untick Billable/, p);
});

test('a MISSING rate is refused and says what arrived instead', () => {
  const r = entry({}); delete r.rate;
  const p = timeEntryProblem(r);
  assert.ok(p && /undefined/.test(p), String(p));
});

test('null is refused rather than coerced to 0', () => {
  assert.ok(timeEntryProblem(entry({ rate: null })));
});

test('a NEGATIVE rate is refused -- it would subtract from the invoice', () => {
  const p = timeEntryProblem(entry({ rate: -350 }));
  assert.ok(p && /-350/.test(p), String(p));
});

test('NaN and Infinity are refused, not multiplied', () => {
  assert.ok(timeEntryProblem(entry({ rate: NaN })));
  assert.ok(timeEntryProblem(entry({ rate: Infinity })));
});

test("the STRING '350' is refused, and the message names the type", () => {
  // Deliberately stricter than billing_code's treatment, and the module says
  // why: there the valid SET is unverified so a refusal could reject real
  // work; a numeric rate carries no such uncertainty, the app always sends a
  // Number, and accepting a string would store a string in a column an invoice
  // MULTIPLIES -- the validate-one-thing/store-another seam this same module
  // was criticised for over billing_code.trim().
  const p = timeEntryProblem(entry({ rate: '350' }));
  assert.ok(p, "the string '350' passed");
  assert.match(p, /send a number, not a string/, p);
});

test('a real billable hour still passes -- the gate is not refusing everything', () => {
  assert.strictEqual(timeEntryProblem(entry({ rate: 350 })), null);
  assert.strictEqual(timeEntryProblem(entry({ rate: 0.5 })), null);
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. a NO-CHARGE entry is left alone, which is the other half');

test('billable:false with rate 0 PASSES -- that is what no-charge means', () => {
  assert.strictEqual(timeEntryProblem(entry({ billable: false, rate: 0 })), null);
});

test('billable:false with no rate field at all PASSES', () => {
  const r = entry({ billable: false }); delete r.rate;
  assert.strictEqual(timeEntryProblem(r), null);
});

test('an ABSENT billable field is no-charge, the same way every reader in the app reads it', () => {
  // sairnlaw.html filters with `t.billable && ...` in rBilling(), rDash() and
  // rInvoiceEntryPicker(). A validator that treated absent as billable would
  // be stricter than the app it protects and would refuse rows nothing can
  // ever put on an invoice.
  const r = entry({ rate: 0 }); delete r.billable;
  assert.strictEqual(timeEntryProblem(r), null);
  const readers = (html.match(/\.billable&&/g) || []).length;
  assert.ok(readers >= 2,
    'expected the app to still read billable as a truthiness filter, found ' + readers);
});

test('the billing-code refusals still come FIRST and are unchanged', () => {
  // A rate check that reordered the existing refusals would change which
  // message a caller gets for a payload that is wrong twice.
  const p = timeEntryProblem(entry({ billing_code: '', rate: 0 }));
  assert.match(p, /UTBMS billing code/, p);
});

// ═══════════════════════════════════════════════════════════════════════════
section('3. the REAL endpoint refuses it, which is the half a client cannot fake');

const endpoint = (() => {
  process.env.SUPABASE_URL = 'https://fake.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';
  const licenseMod = require(path.join(ROOT, 'api/_lib/license.js'));
  licenseMod.validateLicenseKey = async () => ({
    valid: true, active: true, license_hash: 'HASH1', app_id: 'sairnlaw',
    stripe_subscription_id: 'sub_1', trial_ends_at: null,
  });
  const authMod = require(path.join(ROOT, 'api/_lib/auth.js'));
  authMod.tokenFromRequest = (req) => req.headers['x-test-token'] || null;
  authMod.verifySessionToken = (token) => (token ? JSON.parse(token) : null);
  let upserts = 0;
  global.fetch = async (url, opts) => {
    if ((opts || {}).method === 'POST') { upserts += 1; }
    return { ok: true, status: 200, json: async () => ([{ data: { ok: true } }]) };
  };
  delete require.cache[require.resolve(path.join(ROOT, 'api/sd-data.js'))];
  const handler = require(path.join(ROOT, 'api/sd-data.js'));
  return async function write(payload) {
    upserts = 0;
    const res = { statusCode: null, body: null };
    res.status = (c) => { res.statusCode = c; return res; };
    res.json = (b) => { res.body = b; return res; };
    await handler({
      method: 'POST',
      headers: { authorization: 'Bearer testkey',
                 'x-test-token': JSON.stringify({ role: 'owner', employee_id: 'E1' }) },
      body: { action: 'write', resource: 'law_timeentries', payload },
    }, res);
    return { res, upserts };
  };
})();
const ENDPOINT_ENTRY = {
  id: 'TT-1', matter_id: 'M-1', attorney: 'A', date: '2026-09-21',
  billing_code: 'L100', hours: 2, description: 'Drafted motion', invoiced: false,
};

test('a billable zero-rate hour is REFUSED with INVALID_TIME_ENTRY and NOTHING is written', async () => {
  const r = await endpoint(Object.assign({}, ENDPOINT_ENTRY, { billable: true, rate: 0 }));
  assert.strictEqual(r.res.statusCode, 400, 'status was ' + r.res.statusCode);
  assert.strictEqual(r.res.body.error.code, 'INVALID_TIME_ENTRY', JSON.stringify(r.res.body));
  assert.strictEqual(r.upserts, 0, 'the row reached Supabase anyway -- the gate ran too late');
});

test('a no-charge zero-rate hour still WRITES through the same endpoint', async () => {
  const r = await endpoint(Object.assign({}, ENDPOINT_ENTRY, { billable: false, rate: 0 }));
  assert.strictEqual(r.res.statusCode, 200, JSON.stringify(r.res.body));
  assert.strictEqual(r.upserts, 1, 'a no-charge entry was refused');
});

test('a real billable hour still writes', async () => {
  const r = await endpoint(Object.assign({}, ENDPOINT_ENTRY, { billable: true, rate: 350 }));
  assert.strictEqual(r.res.statusCode, 200, JSON.stringify(r.res.body));
  assert.strictEqual(r.upserts, 1);
});

// ═══════════════════════════════════════════════════════════════════════════
section('4. the browser refuses it too, before anything is stored anywhere');

function client(opts) {
  const fields = Object.assign({
    ttmatter: 'M-1', tthours: '2', ttrate: '350', ttattorney: 'A',
    ttdate: '2026-09-21', ttcode: 'L100', ttdesc: 'Drafted motion',
  }, opts.fields || {});
  const checked = opts.billable === undefined ? true : opts.billable;
  const stored = {}; const sent = []; const toasts = [];
  const ctx = {
    JSON, Object, Array, String, Number, Math, Promise, Date,
    console: { warn: () => {} },
    $: (id) => ({
      get value() { return fields[id] === undefined ? '' : fields[id]; },
      set value(v) { fields[id] = v; },
      get checked() { return id === 'ttbillable' ? checked : false; },
    }),
    timeEntries: () => [],
    st: (k, v) => { stored[k] = v; return true; },
    newId: (p) => p + '-1',
    lawLocalToday: () => '2026-09-21',
    closeTimeModal: () => {}, rBilling: () => {}, rDash: () => {},
    toast: (m) => { toasts.push(String(m)); },
    lawWriteFailText: (r, f) => 'SERVER SAID NO (' + r + '): ' + f,
    sdnData: (action, resource, payload) => {
      sent.push({ action, resource, payload });
      return Promise.resolve(payload || true);
    },
    __stored: stored, __sent: sent, __toasts: toasts,
  };
  vm.createContext(ctx);
  vm.runInContext(fnBody('async function saveTime()'), ctx);
  return ctx;
}

test('a blank rate on a billable entry is refused and NOTHING is saved', async () => {
  const c = client({ fields: { ttrate: '' } });
  await c.saveTime();
  assert.strictEqual(c.__sent.length, 0, 'it reached the network');
  assert.ok(!c.__stored.law_timeentries, 'it was written to localStorage anyway');
  assert.match(c.__toasts.join(' '), /rate above zero/, c.__toasts.join(' '));
});

test('a rate of 0, and a non-numeric rate, are refused the same way', async () => {
  for (const v of ['0', 'abc', '-5']) {
    const c = client({ fields: { ttrate: v } });
    await c.saveTime();
    assert.strictEqual(c.__sent.length, 0, 'rate ' + JSON.stringify(v) + ' reached the network');
  }
});

test('a NO-CHARGE entry with a blank rate still saves from the browser', async () => {
  const c = client({ fields: { ttrate: '' }, billable: false });
  await c.saveTime();
  assert.strictEqual(c.__sent.length, 1, 'a no-charge entry was blocked');
  assert.strictEqual(c.__sent[0].payload.billable, false);
  assert.strictEqual(c.__sent[0].payload.rate, 0);
});

test('a normal billable entry saves, and the rate it SENDS is the one it checked', async () => {
  // The bug class this whole suite is about is a value that is judged and then
  // not the value that is stored. `rate` is computed once and used for both.
  const c = client({ fields: { ttrate: '425.50' } });
  await c.saveTime();
  assert.strictEqual(c.__sent.length, 1);
  assert.strictEqual(c.__sent[0].payload.rate, 425.5);
  assert.strictEqual(c.__stored.law_timeentries[0].rate, 425.5);
});

test('the matter and hours guards still come first and are unchanged', async () => {
  const a = client({ fields: { ttmatter: '' } });
  await a.saveTime();
  assert.match(a.__toasts.join(' '), /Select a matter/);
  const b = client({ fields: { tthours: '0' } });
  await b.saveTime();
  assert.match(b.__toasts.join(' '), /Hours must be greater than 0/);
});

// ═══════════════════════════════════════════════════════════════════════════
section('5. the OTHER factor of the same $0.00 line -- hours, closed 2026-09-21');

// THIS SECTION USED TO ASSERT THE OPPOSITE. It carried one arm pinning hours
// as STILL UNVALIDATED at the server, so that the open-work row saying so
// could not quietly become a lie. Michael's direction closed the gap; the arm
// is inverted rather than deleted, because the inversion is the record that
// the pin was honoured instead of being dropped when it became inconvenient.
//
// hours 0 and rate 0 produce the IDENTICAL invoice line -- $0.00 on work that
// renders as ordinary billable time. One factor being guarded and the other
// not was never a coherent position; it was a scope boundary, and it is gone.

test('a billable entry at 0 HOURS is REFUSED, and nothing is written', async () => {
  const r = await endpoint(Object.assign({}, ENDPOINT_ENTRY, { billable: true, rate: 350, hours: 0 }));
  assert.strictEqual(r.res.statusCode, 400, 'status was ' + r.res.statusCode);
  assert.strictEqual(r.res.body.error.code, 'INVALID_TIME_ENTRY', JSON.stringify(r.res.body));
  assert.strictEqual(r.upserts, 0, 'the row reached Supabase anyway');
});

test('missing, string, negative, NaN and Infinity hours are all refused', () => {
  const noHours = entry({}); delete noHours.hours;
  assert.ok(timeEntryProblem(noHours));
  const p = timeEntryProblem(entry({ hours: '2' }));
  assert.ok(p && /send a number, not a string/.test(p), String(p));
  assert.ok(timeEntryProblem(entry({ hours: -2 })));
  assert.ok(timeEntryProblem(entry({ hours: NaN })));
  assert.ok(timeEntryProblem(entry({ hours: Infinity })));
  assert.ok(timeEntryProblem(entry({ hours: null })));
});

test('a real billable entry, and a fractional one, still pass', () => {
  assert.strictEqual(timeEntryProblem(entry({ hours: 2 })), null);
  assert.strictEqual(timeEntryProblem(entry({ hours: 0.1 })), null);
});

test('a NO-CHARGE entry at 0 hours is left alone -- narrower than the browser, on purpose', async () => {
  // saveTime() refuses hours <= 0 on EVERY entry. This refuses it only on a
  // BILLABLE one, because a zero-hour no-charge row cannot reach an invoice
  // and refusing it would refuse work the app has no reason to stop. Where the
  // two differ the stricter one is the client's, and a caller that bypasses
  // the client gets the narrower rule rather than a guess at the wider one.
  assert.strictEqual(timeEntryProblem(entry({ billable: false, hours: 0 })), null);
  const r = await endpoint(Object.assign({}, ENDPOINT_ENTRY, { billable: false, rate: 0, hours: 0 }));
  assert.strictEqual(r.res.statusCode, 200, JSON.stringify(r.res.body));
  assert.strictEqual(r.upserts, 1);
});

test('the RATE refusal still comes first when both factors are zero', () => {
  // Both are wrong; the caller is told about one. Pinned so the message a firm
  // sees does not silently change when either check is edited.
  const p = timeEntryProblem(entry({ hours: 0, rate: 0 }));
  assert.match(p, /hourly rate above zero/, p);
});

test('matter_id is STILL unvalidated here, and the module says so', () => {
  // The remaining named gap, pinned the same way the hours gap was, so the
  // comment and the index row cannot drift from the code. matter_id's failure
  // is an orphaned entry rather than a wrong number on a bill, which is why it
  // was left; if somebody closes it, this arm fails and the record gets
  // updated with it.
  const noMatter = entry({}); delete noMatter.matter_id;
  assert.strictEqual(timeEntryProblem(noMatter), null,
    'matter_id is now validated -- good, but the module comment and the '
    + 'open-work row still say it is not');
  const src = fs.readFileSync(path.join(ROOT, 'api/_lib/law-timeentry.js'), 'utf8');
  assert.match(src, /STILL NOT CHECKED HERE: `matter_id`/,
    'the module stopped naming the gap it is still carrying');
});

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
  console.log('\nsairnlaw_billable_rate: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
