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
// ── RE-AIMED IN b31: THE BUTTON IS GONE, SO SECTION A NOW ASSERTS ITS ABSENCE ──
// Michael's decision: remove "Sync All Apps" rather than leave a control that
// can never succeed (nothing reads bridge_data) or "fix" it into a latest-wins
// write that would overwrite the expense queue. CONCEPT: a control that can
// never do what its label says is removed. b29's arms tested the function's
// honesty; the function no longer exists, so they would throw on the lift. They
// are replaced, not deleted silently. ONE THING b29 MISSED, found while
// removing it: the button's onclick ALSO called sairnUpdateLastSync()
// unconditionally, so the time was stamped on every click whatever the server
// said -- b29's live drive called window.sairnSyncAll() directly and never
// clicked the button, which is why it did not see that.
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
(async () => {
  section('A. the sync button and everything only it used are gone (b31)');
  ok('A1. no sairnSyncAll definition remains', HTML.indexOf('window.sairnSyncAll =') === -1 && HTML.indexOf('function sairnSyncAll') === -1);
  ok('A2. no onclick calls sairnSyncAll or sairnUpdateLastSync', !/onclick="[^"]*(sairnSyncAll|sairnUpdateLastSync)\(/.test(HTML));
  ok('A3. no sairnUpdateLastSync definition remains (it stamped the time unconditionally)', HTML.indexOf('function sairnUpdateLastSync') === -1);
  ok('A4. no "Last sync" element remains for anything to stamp', HTML.indexOf('id="sairn-last-sync"') === -1);
  ok('A5. no request of type full-sync is built anywhere in the page', HTML.indexOf("type:'full-sync'") === -1);
  ok('A6. CONTROL: the CSV Export button beside it is still there -- the removal did not take the container',
    HTML.indexOf('onclick="sairnExportCSV()"') !== -1 && HTML.indexOf('window.sairnExportCSV = function()') !== -1);

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
