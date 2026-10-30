// tests/stonedesk_presence_fixes_b69.js
//
// REQUIREMENT: three StoneDesk compliance displays claim only what the record
//   holds -- cc b56's presence stress, scenarios T2a/T2b, T3a/T3b and T4a.
//
// Run:  node tests/stonedesk_presence_fixes_b69.js [path-to-stonedesk.html]
//
// WRITTEN BEFORE THE FIX and run against the unfixed app (the optional path
// argument): arms 2, 3, 5, 6 and 8 failed. Arms 1, 4 and 7 are CONTROLS -- a
// fully documented sub is still COMPLIANT, a shop with current training and
// an ECP owner still scores 100% green -- so the fix cannot pass by refusing
// every green.
//
// tools/stonedesk_presence_stress.py is the measuring instrument these arms
// were taken from; it exits 1 while OTHER scenarios (T1, E, I, M, X) still
// fail, so it cannot be this file's regression gate. These arms are.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.resolve(__dirname, '..', 'stonedesk.html');
const html = fs.readFileSync(FILE, 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
// A function body by brace depth from its unique signature.
function grab(sig) {
  const at = html.indexOf(sig);
  assert.ok(at !== -1 && html.indexOf(sig, at + 1) === -1, 'signature not unique: ' + sig);
  let i = html.indexOf('{', at), depth = 0;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}' && --depth === 0) return html.slice(at, i + 1);
  }
  throw new Error('unterminated: ' + sig);
}
const subData = fs.readFileSync(path.resolve(__dirname, '..', 'api', 'sd-sub-data.js'), 'utf8');

// ── the pill, fed by the REAL server-side complianceStatus ──
const pctx = vm.createContext({ console });
vm.runInContext('const EXPIRING_SOON_DAYS = ' + /const EXPIRING_SOON_DAYS = (\d+)/.exec(subData)[1] + ';\n'
  + 'function localTodayISO(){ return "2026-10-27"; }\n'
  + grab('function escHtml(s){') + '\n', pctx);
vm.runInContext(subData.slice(subData.indexOf('function complianceStatus('),
  subData.indexOf('\n}\n', subData.indexOf('function complianceStatus(')) + 3), pctx);
vm.runInContext('var _subxCompliance = true;\n' + grab('function subxCompliancePill(s){'), pctx);
const pill = (row) => pctx.subxCompliancePill({ compliance: pctx.complianceStatus(row, '2026-10-27') });

// ── the safety score ──
const SAFE = grab('function safetyUpdateKPIs() {');
function safety(data) {
  const els = {};
  const doc = { getElementById: (id) => (els[id] = els[id] || { textContent: '', style: {} }) };
  const ctx = vm.createContext({ document: doc, sdSafetyData: data, Date, Math, console });
  vm.runInContext(SAFE + '\nsafetyUpdateKPIs();', ctx);
  return { text: String(els['safe-kpi4'].textContent), color: els['safe-kpi4'].style.color };
}
const GREEN = '#15803d';

console.log('STONEDESK PRESENCE FIXES (fourth b69) -- ' + FILE);

test('1. CONTROL: COI, licence and W-9 all on file -> COMPLIANT', () => {
  assert.ok(/>COMPLIANT</.test(pill({ coi_expiry: '2027-06-01', licence_expiry: '2027-06-01', w9_on_file: true })));
});
test('2. T2a: no licence and no W-9 -> NOT green, and both are named', () => {
  const h = pill({ coi_expiry: '2027-06-01', licence_expiry: null, w9_on_file: false });
  assert.ok(!/>COMPLIANT</.test(h), h);
  assert.ok(/LICENCE/.test(h) && /W-9/.test(h), 'the missing documents are not named: ' + h);
});
test('3. T2b: no certificate of insurance -> NOT green, and COI is named', () => {
  const h = pill({ coi_expiry: null, licence_expiry: '2027-06-01', w9_on_file: true });
  assert.ok(!/>COMPLIANT</.test(h) && /COI/.test(h), h);
});
test('4. CONTROL: current training + ECP owner -> 100% green', () => {
  const r = safety({ training: [{ expiry: '2027-09-01' }], incidents: [], inspections: [], ecp: { owner: 'Dana Ortiz' } });
  assert.strictEqual(r.text, '100%'); assert.strictEqual(r.color, GREEN);
});
test('5. T3a: an EMPTY safety record is not a green score', () => {
  const r = safety({ training: [], incidents: [], inspections: [], ecp: {} });
  assert.notStrictEqual(r.color, GREEN, JSON.stringify(r));
  assert.ok(!/%$/.test(r.text), 'a percentage was shown for a record with nothing on it: ' + r.text);
});
test('6. T3b: 2019 training with NO expiry is not current -> not green', () => {
  const r = safety({ training: [{ date: '2019-01-01', expiry: '' }], incidents: [], inspections: [], ecp: { owner: 'Dana Ortiz' } });
  assert.notStrictEqual(r.color, GREEN, JSON.stringify(r));
});
test('7. CONTROL: an expired course still costs points (the old deduction is kept)', () => {
  const r = safety({ training: [{ expiry: '2027-09-01' }, { expiry: '2020-01-01' }], incidents: [], inspections: [], ecp: { owner: 'D' } });
  assert.strictEqual(r.text, '90%');
});
test('8. T4a: the OSHA 1926.1153 panel carries no literal exposure figures', () => {
  const at = html.indexOf('Silica Exposure Monitoring (OSHA 1926.1153)');
  const block = html.slice(at, html.indexOf('PPE Checklist', at)).replace(/<!--[\s\S]*?-->/g, '');
  assert.ok(!/Dry Cut Violations|Wet Cut Days|Air Samples YTD/.test(block), 'literal tiles still shown');
  assert.ok(/Not tracked/.test(block), 'the panel does not say the data is not tracked');
});

// ── fourth b70: cc b56 M3 and M2, finUpdateKPIs ──
function kpis(quotes) {
  const els = {};
  const ctx = vm.createContext({ console, JSON, String, parseFloat, Math,
    localStorage: { getItem: (k) => (k === 'stonedesk_quote_history' ? JSON.stringify(quotes) : null) },
    document: { getElementById: (id) => (els[id] = els[id] || { textContent: '', value: '' }) } });
  vm.runInContext(grab('function finUpdateKPIs(){') + '\nfinUpdateKPIs();', ctx);
  return { margin: els['fin-kpi-margin'].textContent, revenue: els['fin-kpi-revenue'].textContent };
}
test('9. M3: a quote whose total is a NUMBER does not crash the KPI row, and revenue counts it', () => {
  const r = kpis([{ total: 12400 }, { total: '$600' }]);
  assert.strictEqual(r.revenue, '$13,000', JSON.stringify(r));
});
test('10. M2: with no cost read, no margin is claimed (was 65% from a hardcoded 0.35 ratio)', () => {
  const r = kpis([{ total: '$10,000' }]);
  assert.ok(!/%$/.test(r.margin), 'a margin was claimed with no cost basis: ' + r.margin);
});

// ── fourth b71: every StoneDesk presence scenario fourth owns stays PASS ──
// cc's tools/stonedesk_presence_stress.py drives the real functions. It exits
// 1 while hank's api-side T1a/T1b/T1d still fail, so it cannot gate on its own
// exit code; this arm gates on its VERDICT LIST instead. Measured before the
// b71 fixes: E1-E4, I1-I3, M1 and X1-X3 were FAIL. Skipped (not passed) when
// a path argument points at another copy, because the tool reads the repo's.
test('11. cc b56 stress: no FAIL outside hank\'s T1a/T1b/T1d, and every CONTROL holds', () => {
  if (process.argv[2]) { console.log('       (skipped: the stress tool reads the repo copy, not ' + FILE + ')'); return; }
  const out = require('child_process').spawnSync('python',
    [path.resolve(__dirname, '..', 'tools', 'stonedesk_presence_stress.py')], { encoding: 'utf8' }).stdout || '';
  const fails = (out.match(/^FAIL\s+(\S+)/gm) || []).map((l) => l.split(/\s+/)[1]);
  const controlsBad = (out.match(/^CONTROL-FAIL\s+(\S+)/gm) || []);
  assert.ok(/^(PASS|CONTROL-OK)\s/m.test(out), 'the stress tool produced no verdicts -- could not run');
  assert.deepStrictEqual(fails.filter((id) => ['T1a', 'T1b', 'T1d'].indexOf(id) === -1), [],
    'fourth-owned scenarios FAIL: ' + fails.join(', '));
  assert.deepStrictEqual(controlsBad, [], 'a CONTROL failed: ' + controlsBad.join(', '));
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
