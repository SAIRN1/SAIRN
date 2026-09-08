// tests/sairndental_outbound_queue.js
//
// Run:  node tests/sairndental_outbound_queue.js
//
// A ledger row kept because the server was unreachable used to stay on that one
// workstation forever -- dntSyncFromServer() only READS -- and re-entering it
// after the connection returned DOUBLED it, because a second entry gets a new
// id and dntMergeById() keeps both rows. Better than losing it, and not the
// same as fixed. This covers the outbound queue that closes it.
//
// THE LOAD-BEARING ASSERTION IS THE ONE ABOUT api/sd-data.js, not about the
// client. The whole design rests on the server's dnt_* write being an UPSERT on
// (license_hash, id) -- `?on_conflict=...` with `Prefer: resolution=merge-
// duplicates`. If that ever becomes a plain insert, this queue starts
// duplicating every row whose response was lost on the way back, silently, and
// nothing in the client would notice. So the contract is asserted HERE, in the
// suite for the feature that depends on it, rather than trusted.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairndental.html'), 'utf8').replace(/\r\n/g, '\n');

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
// The harness fakes fetch(), not sdnData(), for the same reason the
// write-failure suite does: stubbing the wrapper would encode the assumption
// that every null means the same thing, which is the assumption the whole
// pending/refused split exists to break.
const MODES = {
  accepted: () => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ok: true, data: [{ id: 'X' }] }) }),
  refused: () => Promise.resolve({
    ok: false, status: 400,
    json: () => Promise.resolve({ ok: false, error: { code: 'INVALID_CHARGE', message: 'A charge amount must be greater than zero.' } }),
  }),
  offline: () => Promise.reject(new TypeError('Failed to fetch')),
};

function harness(opts) {
  opts = opts || {};
  const calls = { sent: [], toasts: [], rendered: 0 };
  const store = Object.assign({}, opts.store || {});
  let mode = opts.mode || 'offline';
  const ctx = {
    JSON, Object, Array, Number, Math, Promise, String, TypeError, Date,
    console: { warn: () => {}, error: () => {} },
    DATA_API: '/api/sd-data', APP_ID: 'sairndental',
    dntHeaders: () => ({}),
    dntLicenseKey: () => 'DNT-TEST-2026',
    fetch: (url, init) => {
      calls.sent.push(JSON.parse((init && init.body) || '{}'));
      return MODES[mode]();
    },
    dntLastErr: {},
    // The real ld()/st() pair, against an in-memory store.
    ld: (k, d) => (k in store ? JSON.parse(JSON.stringify(store[k])) : d),
    st: (k, v) => { if (opts.storageFull) return false; store[k] = JSON.parse(JSON.stringify(v)); return true; },
    patients: () => [{ id: 'PT-1', insurance_payer: 'Delta' }],
    computeEstimatedInsurance: () => ({ amount: 40, found: true }),
    charges: () => (store.dnt_charges_list || []),
    payments: () => (store.dnt_payments_list || []),
    newId: (p) => p + '-FIXED',
    dntLocalToday: () => '2026-09-08',
    toast: (m) => calls.toasts.push(m),
    $: () => null,
    H: (s) => String(s == null ? '' : s),
    fmt: (n) => '$' + Number(n || 0).toFixed(2),
    rBilling: () => { calls.rendered++; },
    __calls: calls, __store: store,
    __setMode: (m) => { mode = m; },
  };
  vm.createContext(ctx);
  vm.runInContext([
    fnBody('function sdnData('),
    fnBody('function dntLastErrCode('),
    fnBody('function dntLastErrText('),
    fnBody('function dntWriteRefused('),
    fnBody('function dntWriteFailText('),
    "var DNT_PENDING_KEY='dnt_pending_writes';",
    fnBody('function dntPendingAll('),
    fnBody('function dntPendingCount('),
    fnBody('function dntRefusedAll('),
    fnBody('function dntPendingAdd('),
    'var _dntFlushing=false;',
    fnBody('async function dntFlushPending('),
    fnBody('async function dntFlushAndReport('),
    fnBody('function dntPendingBannerHtml('),
    fnBody('async function addChargeEntry('),
    fnBody('async function addPaymentEntry('),
  ].join('\n'), ctx);
  return ctx;
}

// ═══════════════════════════════════════════════════════════════════════════
section('the server contract the whole design rests on');

test('api/sd-data.js still UPSERTS dnt_* writes on (license_hash, id)', () => {
  // Not a client test, and deliberately in this file: a retry is only safe
  // because the server merges on the row id the client generated. If this ever
  // becomes a plain insert, every retry of a row whose response was lost adds a
  // SECOND charge, silently, and nothing on the client can tell.
  const api = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');
  // ANCHORED ON THE SAIRNDENTAL BLOCK, not on the on_conflict call. That call
  // appears SIX times -- once per app sharing the generic write -- so an
  // indexOf() on it lands on whichever comes first in the file, and this arm
  // spent its first run asserting a different app's line. Found by the probe
  // breaking the dental one and this staying green.
  const at = api.indexOf("app_id: 'sairndental', [idCol]: String(payload.id)");
  assert.ok(at > 0, "the sairndental generic write no longer keys the row on payload.id");
  const block = api.slice(at - 500, at + 200);
  assert.match(block, /rest\(resource \+ '\?on_conflict=license_hash,' \+ idCol\)/,
    'the sairndental dnt_* write no longer posts with on_conflict on the id column -- a retry would insert a second row');
  assert.match(block, /resolution=merge-duplicates/,
    'on_conflict is present but the Prefer header no longer merges -- a retry would conflict or duplicate');
});

test('the id the client generates is stable for the life of the row', () => {
  // newId() is called ONCE, when the record is built, and never again on a
  // retry. A retry that re-generated the id would defeat the upsert entirely.
  ['async function addChargeEntry(', 'async function addPaymentEntry('].forEach((f) => {
    const code = stripComments(fnBody(f));
    assert.strictEqual((code.match(/newId\(/g) || []).length, 1, f + ' generates more than one id');
  });
  const flush = stripComments(fnBody('async function dntFlushPending('));
  assert.strictEqual(flush.indexOf('newId('), -1,
    'the flush generates a new id -- every retry would create a second row');
  assert.match(flush, /sdnData\('write',\s*p\.resource,\s*p\.rec\)/,
    'the flush does not resend the queued record verbatim');
});

// ═══════════════════════════════════════════════════════════════════════════
section('what gets queued, and what must not');

test('an UNREACHABLE charge is queued', async () => {
  const c = harness({ mode: 'offline' });
  const r = await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  assert.strictEqual(r.queued, true);
  assert.strictEqual(c.dntPendingCount(), 1);
  assert.strictEqual(c.__store.dnt_pending_writes[0].rec.id, 'CH-FIXED');
});

test('a REFUSED charge is queued nowhere -- the server already judged it', async () => {
  const c = harness({ mode: 'refused' });
  const r = await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  assert.strictEqual(r.refused, true);
  assert.strictEqual(r.queued, false);
  assert.strictEqual(c.dntPendingCount(), 0, 'a refused row would retry forever and never land');
});

test('a REFUSED payment is queued nowhere either', async () => {
  // Asserted separately rather than assumed from the charge arm: the two
  // functions carry their own copy of the guard, and a fix applied to one and
  // not the other is this platform's most-repeated shape.
  const c = harness({ mode: 'refused' });
  const r = await c.addPaymentEntry('PT-1', 100, 'Cash');
  assert.strictEqual(r.refused, true);
  assert.strictEqual(r.queued, false);
  assert.strictEqual(c.dntPendingCount(), 0);
});

test('a payment this device could not store is NOT queued', async () => {
  const c = harness({ mode: 'offline', storageFull: true });
  const r = await c.addPaymentEntry('PT-1', 100, 'Cash');
  assert.strictEqual(r.kept, false);
  assert.strictEqual(r.queued, false);
});

test('an ACCEPTED charge is not queued', async () => {
  const c = harness({ mode: 'accepted' });
  const r = await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  assert.ok(r.syncResult);
  assert.strictEqual(r.queued, false);
  assert.strictEqual(c.dntPendingCount(), 0);
});

test('a row this device could not even store is NOT queued', async () => {
  // Queueing it would upload a charge the practice cannot see on any screen.
  const c = harness({ mode: 'offline', storageFull: true });
  const r = await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  assert.strictEqual(r.kept, false);
  assert.strictEqual(r.queued, false);
});

test('re-queueing the SAME id replaces rather than appends', async () => {
  // Otherwise the queue itself reintroduces the duplication it exists to stop.
  const c = harness({ mode: 'offline' });
  await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  assert.strictEqual(c.dntPendingCount(), 1);
});

// ═══════════════════════════════════════════════════════════════════════════
section('the flush');

test('a queued row uploads when the connection returns, with the SAME id', async () => {
  const c = harness({ mode: 'offline' });
  await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  await c.addPaymentEntry('PT-1', 60, 'Cash');
  assert.strictEqual(c.dntPendingCount(), 2);
  c.__calls.sent.length = 0;
  c.__setMode('accepted');
  const r = await c.dntFlushPending();
  assert.strictEqual(r.sent, 2);
  assert.strictEqual(c.dntPendingCount(), 0, 'the queue did not drain');
  const ids = c.__calls.sent.map((b) => b.payload.id);
  assert.deepStrictEqual(ids, ['CH-FIXED', 'PM-FIXED'],
    'the retry did not resend the original ids -- the upsert would create new rows');
});

test('a flush that is still offline keeps everything and counts the attempt', async () => {
  const c = harness({ mode: 'offline' });
  await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  const r = await c.dntFlushPending();
  assert.strictEqual(r.sent, 0);
  assert.strictEqual(r.left, 1);
  assert.strictEqual(c.__store.dnt_pending_writes[0].attempts, 1);
});

test('a queued row the server later REFUSES stops being pending and is SHOWN', async () => {
  const c = harness({ mode: 'offline' });
  await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  c.__setMode('refused');
  const r = await c.dntFlushPending();
  assert.strictEqual(r.refused, 1);
  assert.strictEqual(c.dntPendingCount(), 0, 'it would retry forever');
  assert.strictEqual(c.dntRefusedAll().length, 1, 'it vanished instead of being reported');
  assert.match(c.dntRefusedAll()[0].refused_message, /greater than zero/,
    "the server's own words were dropped");
});

test('...and the local ledger row is NOT deleted behind the practice', async () => {
  const c = harness({ mode: 'offline' });
  await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  assert.strictEqual(c.__store.dnt_charges_list.length, 1);
  c.__setMode('refused');
  await c.dntFlushPending();
  assert.strictEqual(c.__store.dnt_charges_list.length, 1,
    'a charge the practice entered and can see was erased by a background flush');
});

test('a flush with nothing pending does not report having run', async () => {
  const c = harness({ mode: 'accepted' });
  const r = await c.dntFlushPending();
  assert.strictEqual(r.ran, false);
  assert.strictEqual(c.__calls.sent.length, 0, 'an empty queue still hit the network');
});

test('two flushes cannot overlap', async () => {
  const c = harness({ mode: 'offline' });
  await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  c.__setMode('accepted');
  const [a, b] = await Promise.all([c.dntFlushPending(), c.dntFlushPending()]);
  assert.strictEqual(a.sent + b.sent, 1, 'the same row was uploaded by both flushes');
});

// ═══════════════════════════════════════════════════════════════════════════
section('what the person is told');

test('a refusal during a background flush speaks; a quiet upload does not', async () => {
  const c = harness({ mode: 'offline' });
  await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  c.__setMode('accepted');
  await c.dntFlushAndReport(true);
  assert.deepStrictEqual(c.__calls.toasts, [], 'a boot-time upload nobody asked for made noise');

  const d = harness({ mode: 'offline' });
  await d.addChargeEntry('PT-1', '', 'PR-1', 100);
  d.__setMode('refused');
  await d.dntFlushAndReport(true);
  assert.strictEqual(d.__calls.toasts.length, 1, 'a refusal was silent because the flush was quiet');
  assert.match(d.__calls.toasts[0], /REFUSED/);
});

test('the banner tells the person NOT to re-enter a queued row', async () => {
  // The duplication this whole feature prevents is the human one: the server
  // cannot double a retry, a receptionist re-typing a charge can.
  const c = harness({ mode: 'offline' });
  await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  const banner = c.dntPendingBannerHtml();
  assert.match(banner, /waiting to upload/);
  assert.match(banner, /Do not re-enter/i, 'nothing tells them re-entering would double it');
});

test('the banner names a refused entry, its amount and the reason', async () => {
  const c = harness({ mode: 'offline' });
  await c.addChargeEntry('PT-1', '', 'PR-1', 100);
  c.__setMode('refused');
  await c.dntFlushPending();
  const banner = c.dntPendingBannerHtml();
  assert.match(banner, /refused by the server/);
  assert.match(banner, /\$100\.00/);
  assert.match(banner, /greater than zero/);
});

test('an empty queue renders nothing at all', () => {
  const c = harness({ mode: 'accepted' });
  assert.strictEqual(c.dntPendingBannerHtml(), '');
});

// ═══════════════════════════════════════════════════════════════════════════
section('it drains on the three moments a connection can have returned');

test('boot flushes, quietly, and registers the online listener', () => {
  const code = stripComments(fnBody('function init('));
  assert.match(code, /dntFlushAndReport\(true\)/, 'boot does not drain the queue');
  assert.match(code, /addEventListener\('online'/, 'nothing reacts to the connection returning');
});

test('the Refresh button flushes BEFORE it reads', () => {
  const code = stripComments(fnBody('async function dntRefreshPending('));
  const flush = code.indexOf('dntFlushAndReport(');
  const read = code.indexOf('dntSyncFromServer(');
  assert.ok(flush > 0 && read > flush,
    'the refresh reads before it uploads, so a queued row is not on the server it just read from');
});

test('there is no second timer', () => {
  // A polling interval racing dntSyncFromServer() for the same rows would be a
  // second scheduler for one job -- the shape this platform keeps recording.
  const code = stripComments(html);
  assert.strictEqual(code.indexOf('setInterval'), -1,
    'a timer was added; the queue is meant to drain on boot, Refresh and online');
});

test('the three ledger callers say the row will upload, not that it is stranded', () => {
  ['async function submitCharge()', 'async function submitPayment()',
    'async function submitCompleteVisit()'].forEach((f) => {
    const code = stripComments(fnBody(f));
    assert.ok(code.indexOf('result.queued') > 0, f + ' does not distinguish a queued row');
    assert.match(code, /QUEUED/, f + ' never says the row is queued');
  });
  assert.strictEqual(stripComments(html).indexOf('will not upload by itself'), -1,
    'a caller still tells the person the row is stranded, which is no longer true');
});

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
  console.log('\nsairndental_outbound_queue: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
