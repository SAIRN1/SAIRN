// tests/sairnfreedom_licence_guard_legacy.js
//
// REQUIREMENT: sfLicenceGuard() asks before a DIFFERENT licence opens a device
//   that holds SAIRNfreedom data, including on a device that predates the
//   fingerprint (no sf_lic_fp yet) but still has the old licence key stored.
//
// Run:  node tests/sairnfreedom_licence_guard_legacy.js
//
// THE GAP (cc b70, routed on cody b61): with no fingerprint the guard ADOPTED
// the new key unconditionally, on the ground that "there is no way to know
// which licence its data belongs to". There is: sfUnlock() stores the key
// itself under K_LIC ('sf_license_key'), right beside the data. So a legacy
// device holding licence A's records -- and A's server-confirmed set -- let
// licence B in with no question, and B saw A's data as its own.
//
// The guard is LIFTED from the shipped file and run against a fake storage,
// so these arms test the real function, not a copy of it.

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = path.join(__dirname, '..', 'sairnfreedom.html');
const html = fs.readFileSync(FILE, 'utf8');

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + detail : '')); }
}

// From `var SF_LIC_FP` to the end of sfLicenceGuard, by brace matching.
function liftGuard() {
  const start = html.indexOf("var SF_LIC_FP = 'sf_lic_fp';");
  const head = html.indexOf('function sfLicenceGuard(k) {');
  if (start < 0 || head < 0 || head < start || html.split('function sfLicenceGuard(k) {').length !== 2) return null;
  let i = html.indexOf('{', head), depth = 0;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}' && --depth === 0) break;
  }
  return html.slice(start, i + 1);
}

function store(init) {
  const m = new Map(Object.entries(init || {}));
  const s = {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => { m.set(k, String(v)); },
    removeItem: (k) => { m.delete(k); },
    has: (k) => m.has(k)
  };
  // Object.keys(localStorage) must list the stored keys, as a real Storage does.
  return new Proxy(s, {
    ownKeys: () => [...m.keys()],
    getOwnPropertyDescriptor: (t, k) => (m.has(k) ? { enumerable: true, configurable: true, value: m.get(k) } : undefined),
    get: (t, k) => t[k]
  });
}

function run(lsInit, key, answer) {
  const src = liftGuard();
  const asked = [];
  const ls = store(lsInit), ss = store({});
  const ctx = {
    localStorage: ls, sessionStorage: ss, String, Object, JSON,
    K_LIC: 'sf_license_key',
    // ld() as the app defines it reads JSON; the stored key is st()'s JSON.
    ld: (k, d) => { const r = ls.getItem(k); if (r === null) return d; try { return JSON.parse(r); } catch (e) { return d; } },
    confirm: (msg) => { asked.push(msg); return answer; },
    alert: (msg) => { asked.push('ALERT ' + msg); }
  };
  vm.createContext(ctx);
  vm.runInContext(src + '\nvar __fp = sfLicFingerprint;', ctx);
  const ok = ctx.sfLicenceGuard(key);
  return { ok, asked, ls, fp: ctx.__fp };
}

const A = 'SF-LICENCE-AAAA', B = 'SF-LICENCE-BBBB';

console.log('sairnfreedom.html sfLicenceGuard -- a legacy device (no fingerprint) still asks before a different licence opens it');
if (!liftGuard()) { console.log('COULD NOT RUN: sfLicenceGuard or its preamble is not in ' + FILE + ' exactly once'); process.exit(2); }

{
  const r = run({ sf_license_key: JSON.stringify(A), sf_jobs: '[{"id":"J1"}]', sf_server_confirmed: '{"sf_jobs":["J1"]}' }, B, false);
  check('L1 no fingerprint, licence A stored, own data present, B entered -> the guard ASKS, and a refusal keeps B out',
    r.asked.length === 1 && r.ok === false && r.ls.has('sf_jobs') && r.ls.has('sf_server_confirmed'),
    JSON.stringify({ ok: r.ok, asked: r.asked.length }));
}
{
  const r = run({ sf_license_key: JSON.stringify(A), sf_jobs: '[{"id":"J1"}]', sf_server_confirmed: '{"sf_jobs":["J1"]}' }, B, true);
  check('L2 the same device, the operator accepts -> A\'s records AND A\'s confirmed set are removed, B\'s fingerprint stored',
    r.ok === true && !r.ls.has('sf_jobs') && !r.ls.has('sf_server_confirmed') && r.ls.getItem('sf_lic_fp') === r.fp(B),
    JSON.stringify({ ok: r.ok, jobs: r.ls.has('sf_jobs'), conf: r.ls.has('sf_server_confirmed') }));
}
{
  const r = run({ sf_license_key: JSON.stringify(B), sf_jobs: '[{"id":"J1"}]' }, B, false);
  check('L3 no fingerprint, the SAME licence stored -> adopted with no question and nothing removed',
    r.ok === true && r.asked.length === 0 && r.ls.has('sf_jobs') && r.ls.getItem('sf_lic_fp') === r.fp(B),
    JSON.stringify({ ok: r.ok, asked: r.asked.length }));
}
{
  const r = run({ sf_jobs: '[{"id":"J1"}]' }, B, false);
  check('L4 no fingerprint and no stored key (nothing says whose data it is) -> adopted, as the design chose',
    r.ok === true && r.asked.length === 0 && r.ls.has('sf_jobs'),
    JSON.stringify({ ok: r.ok, asked: r.asked.length }));
}
{
  const r = run({ sf_license_key: '"not-json', sf_jobs: '[{"id":"J1"}]' }, B, false);
  check('L5 a stored key that does not parse is treated as no stored key, not as a different licence',
    r.ok === true && r.asked.length === 0 && r.ls.has('sf_jobs'),
    JSON.stringify({ ok: r.ok, asked: r.asked.length }));
}
{
  const fpA = run({}, A, false).fp(A);
  const r = run({ sf_lic_fp: fpA, sf_jobs: '[{"id":"J1"}]' }, B, false);
  check('L6 control: fingerprint A present, B entered -> asks (the path that already worked)',
    r.asked.length === 1 && r.ok === false, JSON.stringify({ ok: r.ok, asked: r.asked.length }));
}

console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnfreedom licence guard (legacy device): ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
