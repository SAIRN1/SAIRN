// tests/licence_guard_legacy_device.js
//
// REQUIREMENT: every app's licence guard asks before a DIFFERENT licence opens
//   a device that holds the app's data -- including a device from before the
//   fingerprint (no <p>_lic_fp yet) that still has the previous key stored.
//
// Run:  node tests/licence_guard_legacy_device.js
//
// THE FLAW (cody b65 found it in sairnfreedom; b66 swept the other twelve):
// with no fingerprint each guard ADOPTED the new key, on the stated premise
// that nothing says whose data is on the device. Every one of these apps
// stores the key itself, under its own prefix, beside that data. So licence B
// opened licence A's local records with no question.
//
// Each guard is LIFTED from the shipped file, from its `var <P>_LIC_FP`
// preamble to the end of the guard, and run against a fake Storage.

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

// file -> [fingerprint key var, guard name, stored-key name, stored as JSON?]
const APPS = {
  'sairndental.html':  ['DNT_LIC_FP', 'dntLicenceGuard', 'dnt_license_key', false],
  'sairnsenior.html':  ['SEN_LIC_FP', 'senLicenceGuard', 'sen_license_key', false],
  'sairncare.html':    ['ALF_LIC_FP', 'alfLicenceGuard', 'alf_license_key', false],
  'sairnbuild.html':   ['BLD_LIC_FP', 'bldLicenceGuard', 'bld_license_key', false],
  'sairndesign.html':  ['SDN_LIC_FP', 'sdnLicenceGuard', 'sdn_license_key', false],
  'sairnlaw.html':     ['LAW_LIC_FP', 'lawLicenceGuard', 'law_license_key', false],
  'sairnlegacy.html':  ['LEG_LIC_FP', 'legLicenceGuard', 'leg_license_key', false],
  'sairnroofing.html': ['RF_LIC_FP', 'rfLicenceGuard', 'rf_license_key', false],
  'sairncode.html':    ['SC_LIC_FP', 'scLicenceGuard', 'sc_license_key', false],
  'sairnbiz.html':     ['SB_LIC_FP', 'sbLicenceGuard', 'sb_lic', true],
  'sairngrounds.html': ['GRD_LIC_FP', 'grdLicenceGuard', 'grd_lic', true],
  'sairnscape.html':   ['SCP_LIC_FP', 'scpLicenceGuard', 'scp_lic', true],
  'sairnfreedom.html': ['SF_LIC_FP', 'sfLicenceGuard', 'sf_license_key', true],
  // cody b70: the two apps that stored a licence key beside local data with no guard
  'sairnvet.html':     ['SV_LIC_FP', 'svLicenceGuard', 'sv_license', true],
  'sairnmechanical.html': ['SAIRNMECHANICAL_LIC_FP', 'sairnmechanicalLicenceGuard', 'sairnmechanical_license_key', false]
};

let pass = 0, fail = 0, couldNot = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + detail : '')); }
}

function lift(html, fpVar, guard) {
  const start = html.search(new RegExp('var ' + fpVar + "\\s*=\\s*'[a-z]+_lic_fp';"));
  const sig = 'function ' + guard + '(k) {';
  const head = html.indexOf(sig);
  if (start < 0 || head < start || html.split(sig).length !== 2) return null;
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
  return new Proxy(s, {
    ownKeys: () => [...m.keys()],
    getOwnPropertyDescriptor: (t, k) => (m.has(k) ? { enumerable: true, configurable: true, value: m.get(k) } : undefined),
    get: (t, k) => t[k]
  });
}

function run(src, guard, lsInit, key, answer) {
  const asked = [];
  const ls = store(lsInit);
  const ctx = {
    localStorage: ls, sessionStorage: store({}), String, Object, JSON, Array,
    confirm: (msg) => { asked.push(msg); return answer; },
    alert: (msg) => { asked.push('ALERT ' + msg); }
  };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  const ok = ctx[guard](key);
  return { ok, asked, ls };
}

const A = 'LICENCE-AAAA-2026', B = 'LICENCE-BBBB-2026';

console.log('every licence guard -- a legacy device (no fingerprint) still asks before a different licence opens it');
for (const [file, [fpVar, guard, keyName, json]] of Object.entries(APPS)) {
  const html = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
  const src = lift(html, fpVar, guard);
  if (!src) { couldNot++; console.log('  COULD NOT RUN ' + file + ': ' + guard + ' or its ' + fpVar + ' preamble is not there exactly once'); continue; }
  const fpKey = (src.match(new RegExp('var ' + fpVar + "\\s*=\\s*'([a-z]+_lic_fp)';")) || [])[1];
  const pre = keyName.split('_')[0] + '_';
  const stored = (k) => (json ? JSON.stringify(k) : k);
  const data = pre + 'records';
  {
    const r = run(src, guard, { [keyName]: stored(A), [data]: '[{"id":"R1"}]' }, B, false);
    check(file + ' L1: no fingerprint, licence A stored, B entered -> ASKS, and a refusal keeps B out with A\'s data intact',
      r.asked.length === 1 && r.ok === false && r.ls.has(data), JSON.stringify({ ok: r.ok, asked: r.asked.length }));
  }
  {
    const r = run(src, guard, { [keyName]: stored(A), [data]: '[{"id":"R1"}]' }, B, true);
    check(file + ' L2: ...and accepting removes A\'s records',
      r.ok === true && !r.ls.has(data), JSON.stringify({ ok: r.ok, data: r.ls.has(data) }));
  }
  {
    const r = run(src, guard, { [keyName]: stored(B), [data]: '[{"id":"R1"}]' }, B, false);
    check(file + ' L3: no fingerprint, the SAME licence stored -> no question, nothing removed, fingerprint recorded',
      r.ok === true && r.asked.length === 0 && r.ls.has(data) && !!r.ls.getItem(fpKey),
      JSON.stringify({ ok: r.ok, asked: r.asked.length }));
  }
  {
    const r = run(src, guard, { [data]: '[{"id":"R1"}]' }, B, false);
    check(file + ' L4: no fingerprint and no stored key -> adopted, as the design chose',
      r.ok === true && r.asked.length === 0 && r.ls.has(data), JSON.stringify({ ok: r.ok, asked: r.asked.length }));
  }
  // CASE (cc b76 F1 on cody b65's 2026-10-29T19:12:48Z record): the server
  // treats a key differing only in case as the SAME licence
  // (api/_lib/license.js retries upper-case), so the guard must not offer to
  // wipe a licence's own records over it.
  const lower = A.toLowerCase();
  {
    const r = run(src, guard, { [keyName]: stored(lower), [data]: '[{"id":"R1"}]' }, A, false);
    check(file + ' L5: no fingerprint, the same licence stored in lower case -> no question, nothing removed',
      r.ok === true && r.asked.length === 0 && r.ls.has(data), JSON.stringify({ ok: r.ok, asked: r.asked.length }));
  }
  {
    const fp = run(src, guard, {}, lower, false).ls.getItem(fpKey);   // the fingerprint a lower-case entry recorded
    const r = run(src, guard, { [fpKey]: fp, [keyName]: stored(lower), [data]: '[{"id":"R1"}]' }, A, false);
    check(file + ' L6: fingerprint of the lower-case key recorded, same licence re-entered in upper case -> no question',
      !!fp && r.ok === true && r.asked.length === 0 && r.ls.has(data), JSON.stringify({ fp: !!fp, ok: r.ok, asked: r.asked.length }));
  }
}

console.log('\n' + (fail || couldNot ? 'FAILED' : 'ok') + '  licence guard (legacy device), ' + Object.keys(APPS).length +
  ' apps: ' + pass + ' passed, ' + fail + ' failed, ' + couldNot + ' could not run');
process.exit(couldNot ? 2 : fail ? 1 : 0);
