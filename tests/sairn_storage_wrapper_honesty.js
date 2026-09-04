// tests/sairn_storage_wrapper_honesty.js
//
// Run:  node tests/sairn_storage_wrapper_honesty.js
//
// Every SAIRN app keeps its working data in localStorage behind a one-line
// wrapper. The 2026-08-18 platform audit made that wrapper REPORT its failure
// instead of swallowing it -- a quota-exceeded or private-browsing write is
// otherwise lost with nothing shown, nothing logged and nothing returned. That
// audit reached StoneDesk, SAIRNbuild, SAIRNvet and SAIRNdental.
//
// IT DID NOT REACH EVERYWHERE, AND NOTHING NOTICED FOR SIXTEEN DAYS. The
// 2026-09-04 sweep found SAIRNgrounds and SAIRNscape still carrying the bare
// `catch(e){}`, and SAIRNmechanical with no wrapper at all -- three of its
// writes had no try/catch whatever and were followed immediately by a success
// toast, so a full store threw, the toast never ran, and the user was told
// nothing after clicking Save.
//
// This file exists so the next miss is loud. Part 1 drives the three fixed
// wrappers against a store that refuses. Part 2 is a static parity check with
// the still-unfixed apps listed BY NAME -- the list is meant to be burned
// down, and a name left on it after the app is fixed fails here.

'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function read(f) { return fs.readFileSync(path.join(ROOT, f), 'utf8'); }
function balanced(src, start) {
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
function fnFrom(src, decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('not found: ' + decl);
  return balanced(src, i);
}

// A store that refuses every write with the shape a browser actually throws.
function refusingStore() {
  const data = {};
  return {
    data,
    store: {
      getItem: (k) => (k in data ? data[k] : null),
      setItem: () => { const e = new Error('quota'); e.name = 'QuotaExceededError'; e.code = 22; throw e; }
    }
  };
}
function workingStore() {
  const data = {};
  return { data, store: { getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = v; } } };
}

// ── PART 1: the three wrappers fixed on 2026-09-04 ─────────────────────────

// SAIRNgrounds -- st()
{
  const src = read('sairngrounds.html');
  const make = (store, toasts) => new Function('localStorage', 'toast',
    fnFrom(src, 'function st(k,v){') + '\nreturn st;')(store, (m, d) => toasts.push(String(m)));

  const good = workingStore(), gt = [];
  check('grounds: a write that works returns true', make(good.store, gt)('grd_jobs', [1]), true);
  check('grounds: and says nothing', gt.length, 0);
  check('grounds: and actually stores', good.data.grd_jobs, '[1]');

  const bad = refusingStore(), bt = [];
  check('grounds: a refused write returns FALSE, not undefined', make(bad.store, bt)('grd_jobs', [1]), false);
  check('grounds: and tells the user', bt.length, 1);
  check('grounds: naming what did not happen', /NOT saved/.test(bt[0]), true);
  check('grounds: and that the screen is showing the old data',
    /previous data/.test(bt[0]), true);
}

// SAIRNscape -- scpSt()
{
  const src = read('sairnscape.html');
  const make = (store, toasts) => new Function('localStorage', 'scpToast',
    fnFrom(src, 'function scpSt(k,v){') + '\nreturn scpSt;')(store, (m, d) => toasts.push(String(m)));

  const good = workingStore(), gt = [];
  check('scape: a write that works returns true', make(good.store, gt)('scp_jobs', [1]), true);
  check('scape: and says nothing', gt.length, 0);

  const bad = refusingStore(), bt = [];
  check('scape: a refused write returns FALSE', make(bad.store, bt)('scp_jobs', [1]), false);
  check('scape: and tells the user', bt.length, 1);
  check('scape: naming what did not happen', /NOT saved/.test(bt[0]), true);
}

// SAIRNmechanical -- mechSt(), plus the three callers that claimed an outcome
{
  const src = read('sairnmechanical.html');
  function mech(store, toasts, fields) {
    const els = {};
    Object.keys(fields || {}).forEach((id) => { els[id] = { value: fields[id], textContent: '' }; });
    return new Function('localStorage', 'showToast', 'document', 'APP_ID', 'crNum',
      fnFrom(src, 'function mechSt(key, value) {') + '\n' +
      fnFrom(src, 'function saveCheck(){') + '\n' +
      fnFrom(src, 'function savePricing(){') + '\n' +
      fnFrom(src, 'function getPricing(){') + '\n' +
      fnFrom(src, 'function defaultPricing(){') + '\n' +
      'function renderCR(){}\n' +
      'return { mechSt: mechSt, saveCheck: saveCheck, savePricing: savePricing,' +
      '         crNum: function(){ return crNum; } };'
    )(store, (m, d) => toasts.push(String(m)), { getElementById: (id) => els[id] || null },
      'mech', 1001);
  }

  const good = workingStore(), gt = [];
  check('mech: a write that works returns true', mech(good.store, gt).mechSt('mech_x', { a: 1 }), true);
  const bad = refusingStore(), bt = [];
  check('mech: a refused write returns FALSE', mech(bad.store, bt).mechSt('mech_x', { a: 1 }), false);
  check('mech: and tells the user', bt.length, 1);

  // The check-number defect. crNum is incremented while `entry` is built, so a
  // failed write that left it advanced would make the NEXT check reuse the
  // number -- two different payments, one check number, in a register.
  {
    const s = refusingStore(), t = [];
    const w = mech(s.store, t, { 'cr-date': '2026-09-04', 'cr-payee': 'Acme', 'cr-amount': '250', 'cr-memo': '' });
    w.saveCheck();
    check('mech: a failed check write puts the check number BACK', w.crNum(), 1001);
    check('mech: and does not claim the check was saved',
      t.filter((m) => /^Check #\d+ saved$/.test(m)).length, 0);
  }
  {
    const s = workingStore(), t = [];
    const w = mech(s.store, t, { 'cr-date': '2026-09-04', 'cr-payee': 'Acme', 'cr-amount': '250', 'cr-memo': '' });
    w.saveCheck();
    check('mech: a successful check still confirms', t, ['Check #1001 saved']);
    check('mech: and the number advanced', w.crNum(), 1002);
    check('mech: and both keys were written',
      [typeof s.data.mech_checks, s.data.mech_crnum], ['string', '1002']);
  }
  // savePricing() claimed "Field Quote will use your rates". getPricing()
  // reads this key back, so on a failed write Field Quote keeps the old rates.
  {
    const s = refusingStore(), t = [];
    const w = mech(s.store, t, { 'r-std': '95', 'r-lead': '130', 'r-markup': '35', 'r-profit': '25' });
    w.savePricing();
    check('mech: a failed pricing write does not claim Field Quote will use the rates',
      t.filter((m) => /Field Quote will use your rates/.test(m)).length, 0);
    check('mech: it says the write failed instead', /NOT saved/.test(t[0] || ''), true);
  }
}

// ── PART 2: parity, and an honest list of what is still wrong ──────────────
//
// A one-line `function st(k,v){try{...setItem...}catch(e){}}` is the exact
// shape the platform audit removed. This finds it across every app page.
//
// SCOPE OF THIS SCAN, said rather than discovered: it matches ONE-LINE
// wrappers only. An app whose wrapper spans several lines, or is named
// something else, is NOT checked here and its absence from the output means
// nothing. That is why the expected list below is written out by name instead
// of asserting a count.
{
  const swallowing = [];
  fs.readdirSync(ROOT).filter((f) => f.endsWith('.html')).sort().forEach((f) => {
    const src = read(f);
    const m = src.match(/function\s+(\w*[Ss]t)\s*\(\s*\w+\s*,\s*\w+\s*\)\s*\{try\{localStorage\.setItem\([^}]*\}catch\(e\)\{\}\}/);
    if (m) swallowing.push(f);
  });

  // Known and NOT fixed by the 2026-09-04 sweep, which was dispatched for
  // SAIRNbuild, SAIRNvet, SAIRNmechanical, SAIRNgrounds and SAIRNscape only.
  // These are the same defect in apps that were out of scope; they are
  // reported, not fixed, and this list is meant to shrink.
  //
  // SHRANK 2026-09-04 (CC): sairnbiz.html removed. Its st() now returns a
  // boolean and says "THIS DID NOT SAVE" on a refused write, latched per key.
  // Fixed as part of the SAIRNbiz server-backup work rather than by this
  // sweep -- st() was the hook that change needed, and a hook that pushes to a
  // server on the strength of a write it never confirmed is the same defect
  // wearing a worse disguise. Held by tests/sairnbiz_server_backup.js, which
  // carries its own mutation probe restoring the empty catch.
  const KNOWN_UNFIXED = ['sairndesign.html', 'sairnlaw.html', 'sairnlegacy.html'];

  check('the swallowing wrappers are exactly the ones still on the list',
    swallowing, KNOWN_UNFIXED);
  check('SAIRNgrounds is no longer among them', swallowing.indexOf('sairngrounds.html'), -1);
  check('SAIRNscape is no longer among them', swallowing.indexOf('sairnscape.html'), -1);
}

console.log((fail ? 'FAILED' : 'ok') + '  sairn-storage-wrapper-honesty: ' +
  pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
