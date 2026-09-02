// tests/approval_persistence.js
//
// Run:  node tests/approval_persistence.js
//
// The server half is covered by api/sd-data-approvals.test.js. This covers the
// browser half: that a signed approval actually LEAVES the browser, that a
// failure to leave it is said out loud, and that the app no longer tells a
// customer something it has not done.
//
// Three defects, all in one flow:
//   1. sd_approvals was written to localStorage and read back from NOWHERE in
//      the file. One cache clear destroyed the document proving a customer
//      agreed to a price.
//   2. The total was parsed out of #est-total.textContent. With no quote
//      loaded that element reads an em-dash, which parsed to NaN and then to
//      ZERO -- so a customer could sign a $0 agreement and it saved silently.
//   3. The confirmation said "Your project is reserved" while nothing was
//      reserved: no slab, no schedule slot, no install date.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { const r = fn(); if (r && r.then) throw new Error('async test used sync runner'); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
async function atest(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// Extract the sync function and its cap constant, verbatim.
function grab(startMarker, endRe) {
  const s = html.indexOf(startMarker);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + startMarker);
  const rel = html.slice(s).search(endRe);
  assert.ok(rel > 0, 'unterminated: ' + startMarker);
  return html.slice(s, s + rel);
}
const src =
  grab('var SD_APPROVAL_MAX_BYTES = 64 * 1024;', /\r?\nasync function/) + '\n' +
  grab('async function sdApprovalSync(a){', /\r?\n\}/) + '\n}\n';

function harness(opts) {
  opts = opts || {};
  const toasts = [];
  const sent = [];
  const ctx = {
    console,
    sdData: function () {},                     // presence is what the guard checks
    sdLicenseKey: () => (opts.noLicense ? '' : 'SD-TEST'),
    sessionStorage: { getItem: () => 'tok' },
    showToast: (m, k, t) => toasts.push({ m, k, t }),
    st: () => true,
    _sdApprovals: [],
    sdApprovalsSaveLocal: () => true,
    fetch: async function (url, init) {
      sent.push({ url: String(url), body: init.body });
      if (opts.throws) throw new Error('offline');
      return {
        ok: (opts.status || 200) < 300,
        status: opts.status || 200,
        json: async () => opts.json || { ok: true }
      };
    },
    __toasts: toasts, __sent: sent
  };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  return ctx;
}

const APPROVAL = {
  id: 'APPR1', clientName: 'Ruiz kitchen', quoteNum: 'Q-118', date: '2026-09-02',
  totalAmt: 12400, depositAmt: 6200, sigDataUrl: 'data:image/png;base64,AAAA', depositStatus: 'pending'
};

(async function () {
  section('the approval leaves the browser');

  await atest('a successful sync marks the record synced and sends the real fields', async () => {
    const c = harness({ json: { ok: true } });
    const ok = await c.sdApprovalSync(APPROVAL);
    assert.strictEqual(ok, true);
    assert.strictEqual(APPROVAL.synced, true);
    const body = JSON.parse(c.__sent[0].body);
    assert.strictEqual(body.resource, 'sd_approvals');
    assert.strictEqual(body.payload.total_amount, 12400);
    assert.strictEqual(body.payload.client_name, 'Ruiz kitchen');
    assert.strictEqual(body.payload.signature_png, 'data:image/png;base64,AAAA');
    delete APPROVAL.synced;
  });

  await atest('ALREADY_RECORDED counts as synced -- the row IS on the server', async () => {
    const a = Object.assign({}, APPROVAL);
    const c = harness({ status: 409, json: { error: { code: 'ALREADY_RECORDED', message: 'x' } } });
    assert.strictEqual(await c.sdApprovalSync(a), true);
    assert.strictEqual(a.synced, true);
    assert.strictEqual(c.__toasts.length, 0, 'it alarmed the shop over a row that is safely stored');
  });

  section('a failure to leave the browser is said OUT LOUD');

  await atest('a server error says THIS DEVICE ONLY and quotes the reason', async () => {
    const a = Object.assign({}, APPROVAL);
    const c = harness({ status: 503, json: { error: { code: 'NOT_PROVISIONED', message: 'run sql/sd_approvals_schema.sql' } } });
    assert.strictEqual(await c.sdApprovalSync(a), false);
    assert.ok(!a.synced);
    assert.strictEqual(c.__toasts.length, 1);
    assert.match(c.__toasts[0].m, /THIS DEVICE ONLY/);
    assert.match(c.__toasts[0].m, /sd_approvals_schema\.sql/, 'the actual reason was swallowed');
  });

  await atest('being offline says it exists nowhere else YET, and does not throw', async () => {
    const a = Object.assign({}, APPROVAL);
    const c = harness({ throws: true });
    assert.strictEqual(await c.sdApprovalSync(a), false);
    assert.match(c.__toasts[0].m, /exists nowhere else yet/i);
  });

  await atest('no licence: refuses quietly rather than posting an unauthenticated write', async () => {
    const c = harness({ noLicense: true });
    assert.strictEqual(await c.sdApprovalSync(Object.assign({}, APPROVAL)), false);
    assert.strictEqual(c.__sent.length, 0);
  });

  section('the 64KB budget is checked before the customer walks away');

  await atest('a signature over budget is caught HERE, with what to do about it', async () => {
    const a = Object.assign({}, APPROVAL, { sigDataUrl: 'data:image/png;base64,' + 'A'.repeat(70000) });
    const c = harness({});
    assert.strictEqual(await c.sdApprovalSync(a), false);
    assert.strictEqual(c.__sent.length, 0, 'it sent a payload it knew would be rejected');
    assert.match(c.__toasts[0].m, /sign again with a simpler mark/);
    assert.match(c.__toasts[0].m, /limit 64KB/);
  });

  await atest('the cap matches the endpoint\'s real one, not a larger invented one', () => {
    assert.match(html, /var SD_APPROVAL_MAX_BYTES = 64 \* 1024;/);
    const api = fs.readFileSync(path.join(__dirname, '..', 'api', 'sd-data.js'), 'utf8');
    assert.match(api, /MAX_PAYLOAD_BYTES/);
    assert.ok(!/SIGNATURE_TOO_LARGE/.test(api), 'a dead second cap is back in the endpoint');
  });

  section('no $0 approvals, and no claims the app cannot back');

  test('the total comes from lastCalc, not from the rendered element', () => {
    assert.match(html, /typeof lastCalc !== 'undefined' && lastCalc && Number\(lastCalc\.total\) > 0/);
  });

  test('a non-positive total REFUSES and says nothing was signed', () => {
    assert.match(html, /if \(!\(totalAmt > 0\)\) \{/);
    assert.match(html, /Nothing was recorded, and nothing was signed/);
  });

  test('"Your project is reserved" is gone -- nothing was reserved', () => {
    assert.ok(!html.includes('Your project is reserved.'),
      'the app still tells a customer their project is reserved when it is not');
    assert.match(html, /Your approval is recorded/);
    assert.match(html, /the date is booked once it is received/);
  });

  test('the heading no longer promises a reservation either', () => {
    assert.ok(!/Approve &amp; Reserve Your Project/.test(html));
  });

  section('and it can be read back, which it never could');

  test('there is somewhere to see signed approvals', () => {
    assert.match(html, /id="sd-approvals-list"/);
    assert.match(html, /Signed Approvals/);
  });

  test('a row that never reached the server is BADGED, not shown as normal', () => {
    assert.match(html, /THIS DEVICE ONLY<\/span>/);
  });

  test('approvals are loaded on login, not only when one is signed', () => {
    assert.match(html, /'loadWeather','sdApprovalsLoad'/);
  });

  test('a local-only row survives the server merge rather than being dropped', () => {
    // It is precisely the row nothing else in the world has.
    const i = html.indexOf('async function sdApprovalsLoad');
    const block = html.slice(i, i + 1800);
    assert.match(block, /_sdApprovals\.forEach\(function\(a\)\{ if\(a&&a\.id\) byId\[a\.id\]=a; \}\)/);
  });

  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' APPROVAL-PERSISTENCE ASSERTIONS PASS'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
})();
