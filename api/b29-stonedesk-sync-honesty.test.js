// api/b29-stonedesk-sync-honesty.test.js
//
// Run:  node api/b29-stonedesk-sync-honesty.test.js
//
// CONCEPT. A sync is reported as done only when the server said ok; a non-ok
// answer is shown as a failure and the "Last sync" time is left alone.
//
// `fetch` resolves on a 4xx/5xx, so sairnSyncAll's try/catch never saw the
// bridge's 400 and the page said "All apps synced" having synced nothing.
// MEASURED on the deployed page before this fix: bridge status 400, toasts
// ["Syncing all connected apps...", "All apps synced"], "Last sync: --" ->
// "Last sync: 7:32:13 AM".
//
// The real function is lifted out of stonedesk.html and run against stubs, so
// this tests the code the page ships and not a copy of it. Every arm that guards
// the fix is paired with an ablation that removes ONE thing and must go red.
//
// ALSO HERE: sendToNetwork is gone and the memory write it sat beside is not.
//
// Exit: 0 all arms passed - 1 an arm FAILED

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');
let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 400) : '')); }
}
function section(s) { console.log('\n' + s); }

function lift(src, startMarker, endMarker) {
  const i = src.indexOf(startMarker);
  if (i === -1) throw new Error('marker not found: ' + startMarker);
  const j = src.indexOf(endMarker, i);
  if (j === -1) throw new Error('end marker not found after: ' + startMarker);
  return src.slice(i, j + endMarker.length);
}
const SYNC_SRC = lift(HTML, 'window.sairnSyncAll = async function()', '\n};');

async function runSync(fnSrc, fetchImpl) {
  const toasts = [];
  const el = { textContent: 'Last sync: --' };
  const ctx = {
    window: {}, toasts,
    sairnToast: (m) => toasts.push(m),
    SAIRN_BRIDGE: 'https://example.invalid/api/bridge', SAIRN_APP_ID: 'stonedesk',
    document: { getElementById: (id) => (id === 'sairn-last-sync' ? el : null) },
    fetch: fetchImpl, Date, console
  };
  vm.createContext(ctx);
  vm.runInContext(fnSrc, ctx);
  await ctx.window.sairnSyncAll();
  return { toasts, last: el.textContent };
}
const answer = (status) => async () => ({ ok: status >= 200 && status < 300, status });

(async () => {
  section('A. sairnSyncAll reports what the server said');
  for (const st of [400, 401, 500]) {
    const r = await runSync(SYNC_SRC, answer(st));
    ok('A1[' + st + ']. a ' + st + ' is reported as a FAILURE naming the status',
      r.toasts[r.toasts.length - 1].indexOf('Sync failed') === 0 && r.toasts[r.toasts.length - 1].indexOf('HTTP ' + st) !== -1,
      JSON.stringify(r.toasts));
    ok('A2[' + st + ']. ..."All apps synced" is NEVER shown', r.toasts.every((t) => t.indexOf('All apps synced') === -1), JSON.stringify(r.toasts));
    ok('A3[' + st + ']. ...and the Last sync time is LEFT ALONE', r.last === 'Last sync: --', r.last);
  }
  const good = await runSync(SYNC_SRC, answer(200));
  ok('A4. CONTROL: a 200 still says "All apps synced" and stamps the time -- the fix did not break success',
    good.toasts[good.toasts.length - 1] === 'All apps synced' && /^Last sync: /.test(good.last) && good.last !== 'Last sync: --', JSON.stringify(good));
  const down = await runSync(SYNC_SRC, async () => { throw new Error('offline'); });
  ok('A5. a transport failure still lands in the catch, unchanged', down.toasts[down.toasts.length - 1].indexOf('Bridge offline') === 0, JSON.stringify(down.toasts));

  section('A-ablation. remove the ok check and the same 400 must read as success again');
  const GUARD = /\n\s*if \(!syncRes\.ok\) \{[\s\S]*?\n\s*\}\n/;
  ok('AB0. the guard is present in the shipped source (the ablation has something to remove)', GUARD.test(SYNC_SRC));
  const ablated = await runSync(SYNC_SRC.replace(GUARD, '\n'), answer(400));
  ok('AB1. WITHOUT the guard a 400 toasts "All apps synced" and stamps the time -- the bug, reproduced',
    ablated.toasts.indexOf('All apps synced') !== -1 && ablated.last !== 'Last sync: --', JSON.stringify(ablated));

  section('B. sendToNetwork is gone; the memory write beside it is not');
  ok('B1. no sendToNetwork definition or call remains in stonedesk.html', HTML.indexOf('sendToNetwork') === -1);
  ok('B2. the live, anonymised path (sendNetworkInsight -> api/network) is still wired',
    HTML.indexOf('function sendNetworkInsight(') !== -1 && /sendNetworkInsight\('feature_usage'/.test(HTML));
  const LEARN_SRC = lift(HTML, 'function learnFromResponse(question, answer)', '\n}\n');
  const store = {}; const calls = [];
  const lctx = {
    APP_ID: 'stonedesk', localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = v; } },
    st: (k, v) => { store[k] = JSON.stringify(v); }, sdLocalToday: () => '2026-10-20',
    fetch: (...a) => { calls.push(a); return Promise.resolve({ ok: true }); }, JSON, Date, console
  };
  vm.createContext(lctx);
  vm.runInContext(LEARN_SRC + '\nthis.learn = learnFromResponse;', lctx);
  const longAnswer = 'x'.repeat(160);
  lctx.learn('how much for a 30 sq ft kitchen?', longAnswer);
  ok('B3. a long answer is still written to local memory', store['stonedesk_memory'] && JSON.parse(store['stonedesk_memory']).length === 1, JSON.stringify(store));
  ok('B4. ...and learnFromResponse makes NO network call at all -- the question and answer leave nowhere',
    calls.length === 0, JSON.stringify(calls));

  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  b29 stonedesk sync honesty: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('HARNESS ERROR: ' + (e && e.stack || e)); process.exit(2); });
