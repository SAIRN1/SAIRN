// api/b60-sc-trial-exempt.test.js
//
// Run:  node api/b60-sc-trial-exempt.test.js
//
// REQUIREMENT (Michael's S2 decision, hank b60): SAIRNcode's 30-day trial gate
// (sairncode.html checkTrialGate) exempts demo/internal licences and NOTHING else.
// The exemption is decided by the server, not the browser.
//
//   S1  api/sc-auth.js login AND bootstrap answer trial_exempt: true only for plan 'demo'.
//       'trial', 'b2b_starter', null and 'Demo' all answer false, so a real customer
//       licence is never exempt.
//   C1  checkTrialGate(true) lets an EXPIRED trial through. false, undefined and the
//       string 'true' still raise the expired screen, so a missing or odd field fails
//       closed. The function is extracted from the shipped sairncode.html and run.
//   C2  both call sites pass `result.trial_exempt === true`, not the raw field.
//   M   mutants: the server check widened to true, and the client check loosened to
//       truthy. Each must turn its arm red.
'use strict';
process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'b60-sc-trial-exempt';
process.env.SUPABASE_URL = 'https://stub.supabase.local';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'stub-key';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { hashPin } = require('./_lib/auth');

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function mockRes() { const r = { statusCode: null, body: null }; r.status = (c) => { r.statusCode = c; return r; }; r.json = (b) => { r.body = b; return r; }; r.setHeader = () => r; return r; }

const PIN = String(10000000 + require('crypto').randomInt(89999999));   // a fresh fixture PIN each run, never a constant
const ROW = Object.assign({ employee_id: 'sairn-demo-owner', role: 'admin', failed_attempts: 0, locked_until: null }, hashPin(PIN));

async function scAuth(file, plan, action) {
  const LIC = require.resolve('./_lib/license');
  require.cache[LIC] = { id: LIC, filename: LIC, loaded: true, exports: { validateLicenseKey: async () => ({
    valid: true, active: true, license_hash: 'h-b60', app_id: 'sairncode', app_scope: 'match', plan_tier: plan }) } };
  global.fetch = async (u, o) => {
    const m = (o && o.method) || 'GET';
    if (/audit_log/.test(String(u))) return { ok: true, status: 201, json: async () => [{}], text: async () => '[]' };
    if (m === 'GET') return { ok: true, status: 200, json: async () => (action === 'bootstrap' ? [] : [ROW]) };
    return { ok: true, status: 201, json: async () => [ROW], text: async () => '[]' };
  };
  delete require.cache[require.resolve(file)];
  const h = require(file); const res = mockRes();
  const q = [console.error, console.warn]; console.error = console.warn = () => {};
  try {
    await h({ method: 'POST', headers: { authorization: 'Bearer SC-B60' },
      body: { action, employee_id: 'sairn-demo-owner', pin: PIN } }, res);
  } finally { [console.error, console.warn] = q; }
  return res;
}

function extractGate(html) {
  const start = html.indexOf('        function checkTrialGate(');
  const end = html.indexOf('        window.checkTrialGate = checkTrialGate;');
  if (start < 0 || end < 0 || end < start) throw new Error('checkTrialGate not found in sairncode.html');
  return html.slice(start, end);
}
function runGate(fnSrc, arg) {
  const store = { sc_trial_start: String(Date.now() - 45 * 86400000) };   // started 45 days ago: expired
  const shown = { screen: false };
  const el = { classList: { add: () => { shown.screen = true; }, remove: () => {} }, textContent: '' };
  const ctx = { Date, Math, parseInt, isNaN, String,
    localStorage: { getItem: (k) => store[k] || null, setItem: (k, v) => { store[k] = v; } },
    document: { getElementById: () => el } };
  vm.createContext(ctx);
  vm.runInContext(fnSrc + '\nthis.__r = checkTrialGate(__arg);', Object.assign(ctx, { __arg: arg }));
  return { allowed: ctx.__r, screen: shown.screen };
}

async function serverArms(file, label) {
  for (const action of ['login', 'bootstrap']) {
    await test(label + ' S1 [' + action + '] plan demo -> trial_exempt true', async () => {
      const r = await scAuth(file, 'demo', action);
      assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
      assert.strictEqual(r.body.trial_exempt, true);
    });
    for (const plan of ['trial', 'b2b_starter', null, 'Demo']) {
      await test(label + ' S1 [' + action + '] plan ' + JSON.stringify(plan) + ' -> trial_exempt false', async () => {
        const r = await scAuth(file, plan, action);
        assert.strictEqual(r.statusCode, 200, JSON.stringify(r.body));
        assert.strictEqual(r.body.trial_exempt, false);
      });
    }
  }
}
async function clientArms(html, label) {
  const g = extractGate(html);
  await test(label + ' C1 an explicit true lets an EXPIRED trial through', async () => {
    const r = runGate(g, true); assert.strictEqual(r.allowed, true); assert.strictEqual(r.screen, false);
  });
  for (const v of [false, undefined, 'true', 1]) {
    await test(label + ' C1 ' + JSON.stringify(v) + ' -> the real gate runs and the expired screen shows', async () => {
      const r = runGate(g, v); assert.strictEqual(r.allowed, false); assert.strictEqual(r.screen, true);
    });
  }
}

(async () => {
  console.log('SAIRNcode trial gate -- demo exemption, decided by the server (S2)');
  const HTML = fs.readFileSync(path.join(__dirname, '..', 'sairncode.html'), 'utf8');
  await serverArms('./sc-auth.js', 'live');
  await clientArms(HTML, 'live');
  await test('live C2 both call sites pass result.trial_exempt === true', async () => {
    const n = HTML.split('await scOnAuthenticated(result.token, result.role, result.employee_id, result.trial_exempt === true);').length - 1;
    assert.strictEqual(n, 2, n + ' call sites pass the strict comparison');
    assert.ok(HTML.indexOf('if (!checkTrialGate(trialExempt)) return;') !== -1, 'scOnAuthenticated does not hand the flag to the gate');
  });

  // mutation controls
  const src = fs.readFileSync(path.join(__dirname, 'sc-auth.js'), 'utf8');
  const a = "const trialExempt = lic.plan_tier === 'demo';";
  if (src.split(a).length !== 2) throw new Error('server mutation anchor not unique');
  const mf = path.join(__dirname, '.b60-mutant-sc-auth.js');
  fs.writeFileSync(mf, src.split(a).join('const trialExempt = true;'));
  const before = fail, p0 = pass; const log = console.log; console.log = () => {};
  try { await serverArms(mf, 'M'); } finally { console.log = log; try { fs.unlinkSync(mf); } catch (e) { /* gone */ } }
  const red1 = fail - before; fail = before; pass = p0;
  await test('M1. server widened to every plan -> S1 red (' + red1 + ' arm(s))', async () => { assert.ok(red1 > 0); });
  const b = 'if (trialExempt === true) return true;';
  if (HTML.split(b).length !== 2) throw new Error('client mutation anchor not unique');
  const before2 = fail, p1 = pass; console.log = () => {};
  try { await clientArms(HTML.split(b).join('if (trialExempt) return true;'), 'M'); } finally { console.log = log; }
  const red2 = fail - before2; fail = before2; pass = p1;
  await test('M2. client loosened to truthy -> C1 red (' + red2 + ' arm(s))', async () => { assert.ok(red2 > 0); });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exitCode = fail ? 1 : 0;
})();
