// tests/mech_check_register_identity.js
//
// Run:  node tests/mech_check_register_identity.js
//
// SAIRNmechanical's cheque register, driven verbatim from sairnmechanical.html.
//
// THE DEFECT, found by an independent review of 6ddb8154 before a single row
// existed on the server. mech_checks reached the server keyed on the CHEQUE
// NUMBER (`MECH_ID_FIELD = { mech_checks: 'num' }`), the write is an upsert on
// (license_hash, check_id), `crNum` starts at 1001 on any device with no local
// `_crnum`, and `_crnum` is deliberately not synced. So a second workstation
// issues its own #1001 and its write UPDATES the first device's #1001 in the
// durable record. Both survive locally, mechHydrateAll() is additive-only, and
// neither device ever pulls the other's -- the audit trail is the copy that
// loses a cheque, and nothing reports it.
//
// WHAT IS ASSERTED. check_id is a MINTED per-record id; the cheque number stays
// an ordinary data field, unchanged, still shown to the user; and a repeated
// number is REPORTED rather than resolved -- at save time in the toast and on
// every render at the top of the register.
//
// ARM 2 IS THE NEGATIVE CONTROL AND IT IS THE POINT. It reproduces the OLD key
// choice against the same two saves and asserts the two devices really did
// collide on one identity. A fixture that cannot demonstrate the trap proves
// nothing about the fix.

'use strict';
const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', 'sairnmechanical.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; console.log('PASS  ' + name); return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}
function ok(name, cond, detail) {
  if (cond) { pass++; console.log('PASS  ' + name + (detail ? '  ' + detail : '')); return; }
  fail++;
  console.log('FAIL  ' + name + (detail ? '  ' + detail : ''));
}

function balanced(start) {
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
function fn(decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('not found: ' + decl);
  return balanced(i);
}

// One simulated workstation. Storage starts EMPTY, which is the whole scenario:
// a device with no local `_crnum` begins at 1001.
function device(startingChecks) {
  const data = {};
  if (startingChecks) data['sairnmechanical_checks'] = JSON.stringify(startingChecks);
  const store = {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = v; }
  };
  const pushed = [];
  const toasts = [];
  const els = {
    'cr-date': { value: '2026-09-10' },
    'cr-payee': { value: 'Acme Supply' },
    'cr-amount': { value: '250' },
    'cr-memo': { value: 'parts' },
    'cr-num': { textContent: '' },
    'cr-history': { innerHTML: '' }
  };
  const win = {
    crypto: require('crypto').webcrypto,
    mechPushRecord: (resource, rec) => { pushed.push({ resource, rec }); }
  };

  const api = new Function(
    'localStorage', 'window', 'document', 'showToast', 'APP_ID', 'crypto',
    'var crNum = parseInt(localStorage.getItem(APP_ID + "_crnum") || "1001");\n' +
    fn('function mechSt(key, value) {') + '\n' +
    fn('function mechCheckId(){') + '\n' +
    fn('function mechEnsureCheckIds(checks){') + '\n' +
    fn('function saveCheck(){') + '\n' +
    fn('function renderCR(checks){') + '\n' +
    fn('function loadCR(){') + '\n' +
    'return { saveCheck: saveCheck, renderCR: renderCR, loadCR: loadCR,' +
    '         mechCheckId: mechCheckId, mechEnsureCheckIds: mechEnsureCheckIds,' +
    '         crNum: function(){ return crNum; } };'
  )(
    store,
    win,
    { getElementById: (id) => els[id] || null },
    (m) => toasts.push(String(m)),
    'sairnmechanical',
    win.crypto
  );
  return { api, data, pushed, toasts, els, checks: () => JSON.parse(data['sairnmechanical_checks'] || '[]') };
}

console.log('SAIRNmechanical cheque-register identity\n');

// ── ARM 1: two fresh devices both issue #1001, and the server sees TWO records
const A = device();
const B = device();
A.api.saveCheck();
B.api.saveCheck();

const pushA = A.pushed[0], pushB = B.pushed[0];
check('1a  both devices really did issue the same cheque number',
      [pushA.rec.num, pushB.rec.num], [1001, 1001]);
ok('1b  device A pushes a MINTED id, not the number',
   typeof pushA.rec.id === 'string' && /^CHK-/.test(pushA.rec.id) && String(pushA.rec.id) !== '1001',
   pushA.rec.id);
ok('1c  the two devices\' ids differ, so neither upsert can overwrite the other',
   pushA.rec.id !== pushB.rec.id, pushA.rec.id + ' vs ' + pushB.rec.id);
check('1d  the cheque number survives as ordinary data', pushA.rec.num, 1001);
check('1e  it is pushed to mech_checks', pushA.resource, 'mech_checks');

// ── ARM 2: NEGATIVE CONTROL -- the old key really did collide
// mechPushOne() keys on MECH_ID_FIELD[resource] || 'id'. Under the old map that
// was 'num' for mech_checks. Same two records, old rule:
const oldKeyA = pushA.rec['num'], oldKeyB = pushB.rec['num'];
ok('2a  CONTROL: under the OLD key both devices produced ONE identity',
   String(oldKeyA) === String(oldKeyB), String(oldKeyA) + ' === ' + String(oldKeyB));
ok('2b  CONTROL: and the source no longer maps mech_checks to the number',
   !/MECH_ID_FIELD\s*=\s*\{\s*mech_checks/.test(src),
   'MECH_ID_FIELD carries no mech_checks entry');

// ── ARM 3: a repeated number is REPORTED, at save time and on every render
const C = device();
C.api.saveCheck();                       // #1001
C.data['sairnmechanical_crnum'] = '1001'; // operator resets the book by hand
const C2 = device(C.checks());
C2.api.saveCheck();                       // #1001 again, same register

const dupToast = C2.toasts[C2.toasts.length - 1];
ok('3a  the save toast names the repeat', /already in this register/.test(dupToast), dupToast.slice(0, 70) + '...');
ok('3b  and says nothing was overwritten', /none overwritten/.test(dupToast), '');
ok('3c  the register renders a repeat banner',
   /Repeated check number/.test(C2.els['cr-history'].innerHTML), '');
ok('3d  the banner names the number', /#1001/.test(C2.els['cr-history'].innerHTML), '');
check('3e  BOTH records are kept locally', C2.checks().length, 2);

// ── ARM 4: NEGATIVE CONTROL -- a register with no repeat says nothing
const D = device();
D.api.saveCheck();
const cleanToast = D.toasts[D.toasts.length - 1];
check('4a  CONTROL: an ordinary save toast is plain', cleanToast, 'Check #1001 saved');
ok('4b  CONTROL: and renders no banner',
   !/Repeated check number/.test(D.els['cr-history'].innerHTML), '');

// ── ARM 5: cheques written before the change get an id, and it is stable
const LEGACY = [{ num: 1001, date: '2026-09-01', payee: 'Old', amount: '10', memo: '' }];
const E = device(LEGACY);
E.api.loadCR();
const firstId = E.checks()[0].id;
ok('5a  a legacy record with no id is backfilled', typeof firstId === 'string' && /^CHK-/.test(firstId), firstId);
E.api.loadCR();
check('5b  and the id does not change on the next load', E.checks()[0].id, firstId);
ok('5c  the legacy record was NOT pushed to the server',
   E.pushed.length === 0, 'pushed ' + E.pushed.length);

// ── ARM 6: the register is loaded when the panel opens, not only after a save
ok('6a  showPage wires check-register to loadCR',
   /id === 'check-register' && typeof window\.loadCR === 'function'/.test(src), '');
ok('6b  and the wiring is in the showPage that is exported to window',
   src.indexOf("id === 'check-register'") > src.indexOf('window.showPage = showPage') - 4000 &&
   src.indexOf("id === 'check-register'") < src.indexOf('window.showPage = showPage'),
   'inside the exported copy, not the shadowed one');

// ── ARM 7: the backup is read back, not write-only
ok('7a  mechHydrateAll is actually called',
   /mechHydrateAll\(\)\s*\.then/.test(src), 'invoked in mechEnter');

console.log('\n%d passed, %d failed', pass, fail);
process.exit(fail ? 1 : 0);
