// tests/sairnlaw_invoiced_sync.js
//
// Run:  node tests/sairnlaw_invoiced_sync.js
//
// ── THE HOURS WERE BILLED HERE AND THE SERVER NEVER HEARD ──────────────────
// `saveInvoice()` in sairnlaw.html builds an invoice out of selected time
// entries, then marks each of those entries `invoiced=true` and writes the
// list back with `st('law_timeentries', teList)`. That is localStorage. The
// only network write in the whole function was the invoice itself:
//
//     var syncResult = await sdnData('write','law_invoices',rec);
//
// So the flag that says "these hours have been billed" lived on ONE browser.
// The server's copy of every one of those rows still read `invoiced:false`.
//
// WHY THAT IS A MONEY DEFECT AND NOT A SYNC INCONVENIENCE. `lawHydrateAll()`
// merges ADDITIVELY and never overwrites a locally-held id -- deliberately,
// and its own comment says so. A workstation with no copy yet (a new laptop, a
// cleared profile, the second attorney's machine) therefore hydrates those
// hours FRESH, as `invoiced:false`. `rInvoiceEntryPicker()` filters on
// `t.billable && !t.invoiced`, so it offers them again, as unbilled work, with
// nothing anywhere saying they have already been sent to the client. The same
// hours get invoiced twice.
//
// FOUND 2026-09-21 by cc during the Tier A review of fourth's law_timeentries
// billing-code gate (obligation opened 2026-09-18T23:44:59Z) -- while checking
// whether that gate protects what its record claims it protects. It does; this
// is a different hole in the same resource, and it was recorded in that verdict
// as FINDING 4. NOTE FOR ANYONE FOLLOWING THAT RECORD: the verdict calls the
// function `createInvoice()`. There is no such function -- it is `saveInvoice()`.
// The line numbers in the verdict are right and the name is wrong.
//
// WHAT THIS SUITE DOES NOT CLAIM TO FIX, stated here rather than discovered
// later: a device that ALREADY HOLDS those entries locally keeps its stale
// `invoiced:false` forever, because additive hydration will not overwrite it.
// That is a property of `lawHydrateAll()`, is platform-wide rather than
// specific to billing, and changing it is a design decision about conflict
// resolution that this fix deliberately does not make. What is closed here is
// the case where the SERVER's own record of a billed hour was wrong -- which is
// what every fresh device, and anything reading the table directly, sees.
//
// THESE ARMS ARE THEIR OWN CONTROL. Arms 1 and 3 fail if the `law_timeentries`
// write is removed from `saveInvoice()`, and arm 3 fails if it is added but its
// failure is swallowed -- the shape this app has been bitten by repeatedly,
// where a write that did not land is reported as a success.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairnlaw.html'), 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }
function section(t) { queue.push({ section: t }); }

// The REAL function is lifted out of the shipped file, never retyped. A
// retyped copy is a fixture that drifts from the code it exists to check --
// the mistake tests/sairnlaw_hydrate.js records making with LAW_SYNC_RESOURCES.
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

const ENTRIES = [
  { id: 'TT-1', matter_id: 'M-1', hours: 2, rate: 350, billing_code: 'L100', billable: true, invoiced: false },
  { id: 'TT-2', matter_id: 'M-1', hours: 1, rate: 350, billing_code: 'L110', billable: true, invoiced: false },
  { id: 'TT-3', matter_id: 'M-1', hours: 5, rate: 350, billing_code: 'L120', billable: true, invoiced: false },
];

// opts.picked   -- entry ids checked in the picker
// opts.writes   -- resource -> false to make that write fail, as sdnData() does
function harness(opts) {
  opts = opts || {};
  const picked = opts.picked || ['TT-1', 'TT-2'];
  const stored = {};
  const sent = [];      // every sdnData write, in order
  const toasts = [];
  const local = { law_timeentries: JSON.parse(JSON.stringify(ENTRIES)), law_invoices: [] };

  const fields = { ivmatter: 'M-1', ivsplits: '', 'invoice-err': '' };
  const el = (id) => ({
    get value() { return fields[id] === undefined ? '' : fields[id]; },
    set value(v) { fields[id] = v; },
    get textContent() { return fields[id] === undefined ? '' : fields[id]; },
    set textContent(v) { fields[id] = v; },
  });

  const ctx = {
    JSON, Object, Array, String, Number, Math, Promise, Date,
    console: { warn: () => {} },
    $: el,
    document: { querySelectorAll: () => picked.map((v) => ({ value: v })) },
    matters: () => [{ id: 'M-1', client_id: 'C-1' }],
    timeEntries: () => JSON.parse(JSON.stringify(local.law_timeentries)),
    invoices: () => JSON.parse(JSON.stringify(local.law_invoices)),
    st: (k, v) => { stored[k] = v; local[k] = JSON.parse(JSON.stringify(v)); return true; },
    newId: (p) => p + '-1',
    lawLocalToday: () => '2026-09-21',
    closeInvoiceModal: () => {},
    rBilling: () => {}, rDash: () => {},
    toast: (msg) => { toasts.push(String(msg)); },
    lawWriteFailText: (resource, fallback) => 'SERVER SAID NO (' + resource + '): ' + fallback,
    sdnData: (action, resource, payload) => {
      sent.push({ action, resource, payload: JSON.parse(JSON.stringify(payload)) });
      const ok = (opts.writes || {})[resource];
      return Promise.resolve(ok === false ? null : (payload || true));
    },
    __stored: stored, __sent: sent, __toasts: toasts, __fields: fields,
  };
  vm.createContext(ctx);
  vm.runInContext(fnBody('async function saveInvoice()'), ctx);
  return ctx;
}
const teWrites = (c) => c.__sent.filter((s) => s.resource === 'law_timeentries');

// ═══════════════════════════════════════════════════════════════════════════
section('1. the billed flag reaches the server, which is the whole defect');

test('every entry put on the invoice is written back with invoiced:true', async () => {
  const c = harness({ picked: ['TT-1', 'TT-2'] });
  await c.saveInvoice();
  const w = teWrites(c);
  assert.strictEqual(w.length, 2,
    'expected 2 law_timeentries writes, got ' + w.length
    + ' -- the invoiced flag never left the device');
  assert.deepStrictEqual(w.map((x) => x.payload.id).sort(), ['TT-1', 'TT-2']);
  w.forEach((x) => assert.strictEqual(x.payload.invoiced, true,
    x.payload.id + ' was written without invoiced:true'));
  assert.ok(w.every((x) => x.action === 'write'));
});

test('the whole record is sent, not a patch -- the store holds one JSON blob', async () => {
  // api/sd-data.js upserts `data: payload` wholesale, so a partial payload
  // would REPLACE the row and lose hours, rate and billing_code. It would also
  // be refused outright by api/_lib/law-timeentry.js for the missing code.
  const c = harness({ picked: ['TT-1'] });
  await c.saveInvoice();
  const p = teWrites(c)[0].payload;
  assert.strictEqual(p.billing_code, 'L100', 'billing_code was dropped from the write');
  assert.strictEqual(p.hours, 2);
  assert.strictEqual(p.rate, 350);
});

test('an entry NOT on the invoice is not written at all', async () => {
  const c = harness({ picked: ['TT-1'] });
  await c.saveInvoice();
  assert.deepStrictEqual(teWrites(c).map((x) => x.payload.id), ['TT-1']);
  assert.ok(!teWrites(c).some((x) => x.payload.id === 'TT-3'));
});

test('the local list is still marked, so this device is right immediately', async () => {
  const c = harness({ picked: ['TT-1', 'TT-2'] });
  await c.saveInvoice();
  const byId = {};
  c.__stored.law_timeentries.forEach((t) => { byId[t.id] = t.invoiced; });
  assert.strictEqual(byId['TT-1'], true);
  assert.strictEqual(byId['TT-2'], true);
  assert.ok(!byId['TT-3']);
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. a write that did not land is SAID, not swallowed');

test('time entries that failed to sync are named, with the consequence', async () => {
  const c = harness({ picked: ['TT-1', 'TT-2'], writes: { law_timeentries: false } });
  await c.saveInvoice();
  const msg = c.__toasts.join(' | ');
  assert.ok(/2 of 2/.test(msg),
    'the toast does not say how many entries are still unbilled on the server: ' + msg);
  assert.ok(/again/i.test(msg),
    'the toast does not say the hours could be invoiced again: ' + msg);
  assert.ok(!/^Invoice created$/.test(c.__toasts[0] || ''),
    'a partial failure was reported as a clean success');
});

test('the INVOICE failing is still reported in its own words', async () => {
  const c = harness({ picked: ['TT-1'], writes: { law_invoices: false } });
  await c.saveInvoice();
  const msg = c.__toasts.join(' | ');
  assert.ok(/SERVER SAID NO \(law_invoices\)/.test(msg), msg);
});

test('both halves failing reports both, not the first one only', async () => {
  const c = harness({ picked: ['TT-1'], writes: { law_invoices: false, law_timeentries: false } });
  await c.saveInvoice();
  const msg = c.__toasts.join(' | ');
  assert.ok(/SERVER SAID NO \(law_invoices\)/.test(msg), 'invoice failure lost: ' + msg);
  assert.ok(/1 of 1/.test(msg), 'time-entry failure lost: ' + msg);
});

test('all clear reports a clean success and nothing alarming', async () => {
  const c = harness({ picked: ['TT-1', 'TT-2'] });
  await c.saveInvoice();
  const msg = c.__toasts.join(' | ');
  assert.ok(/Invoice created/.test(msg), msg);
  assert.ok(!/of 2/.test(msg), 'a clean run warned about unbilled hours anyway: ' + msg);
});

// ═══════════════════════════════════════════════════════════════════════════
section('3. the guards the function already had are untouched');

test('no matter selected still refuses, and nothing is sent', async () => {
  const c = harness({ picked: ['TT-1'] });
  c.__fields.ivmatter = '';
  await c.saveInvoice();
  assert.strictEqual(c.__sent.length, 0);
  assert.match(c.__fields['invoice-err'], /Select a matter/);
});

test('no entries selected still refuses, and nothing is sent', async () => {
  const c = harness({ picked: [] });
  await c.saveInvoice();
  assert.strictEqual(c.__sent.length, 0);
  assert.match(c.__fields['invoice-err'], /Select at least one time entry/);
});

test('a malformed split-fee line refuses BEFORE anything is marked or sent', async () => {
  const c = harness({ picked: ['TT-1'] });
  c.__fields.ivsplits = 'Nobody, 0';
  await c.saveInvoice();
  assert.strictEqual(c.__sent.length, 0);
  assert.ok(!c.__stored.law_timeentries, 'entries were marked invoiced on a refused invoice');
  assert.match(c.__fields['invoice-err'], /malformed/);
});

test('split percentages that do not sum to 100 refuse, and nothing is sent', async () => {
  const c = harness({ picked: ['TT-1'] });
  c.__fields.ivsplits = 'A, 40\nB, 40';
  await c.saveInvoice();
  assert.strictEqual(c.__sent.length, 0);
  assert.match(c.__fields['invoice-err'], /sum to 100/);
});

test('the invoice total is still hours x rate over the picked entries only', async () => {
  const c = harness({ picked: ['TT-1', 'TT-2'] });
  await c.saveInvoice();
  const iv = c.__sent.find((s) => s.resource === 'law_invoices').payload;
  assert.strictEqual(iv.total, 2 * 350 + 1 * 350);
  assert.deepStrictEqual(iv.time_entry_ids, ['TT-1', 'TT-2']);
});

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
  console.log('\nsairnlaw_invoiced_sync: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
