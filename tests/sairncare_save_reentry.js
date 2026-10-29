// tests/sairncare_save_reentry.js
//
// REQUIREMENT: a second press of a SAIRNcare save while the first press's
// server write is still in flight records NOTHING a second time -- and the
// hold is released once that write answers, is refused, rejects or throws.
//
// Run:  node tests/sairncare_save_reentry.js [path-to-sairncare.html]
//
// THE DEFECT (cody b64 re-entry sweep, fixed cody b65). Each handler below
// sends its record and only closes its modal / clears its form after the
// server answers. The trigger stayed live for that wait with every value still
// in place, so a second press sent the same record again -- under a NEW id for
// family contacts, staff credentials and operational audits, and for a
// controlled-substance count a second local MAR entry for one witnessed count.
//
//   F1-F3  alfFamilySave   (family contact + medication-status consent)
//   K1-K3  saveCsCount     (two-person controlled-substance count)
//   R1-R3  saveCredEntry   (staff credential / training hours)
//   O1-O3  saveOpAudit     (operational audit check)
//   Arm meanings: tests/lib/save_reentry_harness.js.
//
// No browser, no network. An extraction that fails exits 2.
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const H = require('./lib/save_reentry_harness.js');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairncare.html');
const html = fs.readFileSync(FILE, 'utf8').replace(/\r\n/g, '\n');
const lift = H.makeLift(html, FILE);

let pass = 0, fail = 0, finished = false;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 400) : '')); }
}

let seq = 0;
const SPECS = [
  {
    id: 'F', name: 'alfFamilySave',
    ok: { ok: true, status: 200, body: { ok: true } },
    refused: { ok: false, status: 403, body: null, error: { message: 'management only' } },
    src: H.optional(html, /var alfFamilySaving\s*=\s*false;/) + '\n' + lift('window.alfFamilySave=function(){'),
    fields: { 'fc-id': '', 'fc-resident': 'RES-1', 'fc-name': 'Jo Family', 'fc-rel': 'daughter', 'fc-consent': 'false' },
    given: (write) => ({ alfIsManagement: () => true, alfFamilyData: write }),
    press: (ctx) => ctx.alfFamilySave()
  },
  {
    id: 'K', name: 'saveCsCount',
    ok: { id: 'x' }, refused: null,
    src: H.optional(html, /var csCountSaving\s*=\s*false;/) + '\n' + lift('async function saveCsCount(){'),
    fields: { 'cs-medication': 'MED-1', 'cs-witness': 'EMP-2' },
    given: (write, box) => ({
      csWitnessToken: 'tok', csWitnessWho: 'EMP-2', csPendingId: null,
      csBuildRec: () => ({ id: 'CNT-' + (++seq) }),
      marWrite: write,
      marEntries: () => box.rows.slice(),
      st: (k, list) => { if (k === 'alf_mar') box.rows = list; return true; },
      marPayload: (t, rec) => rec,
      alfLastErrText: () => '', alfWriteVerdict: () => 'MISSED'
    }),
    // The witness signs in again before each press, as the modal requires --
    // a refused count clears the token on purpose.
    refill: (ctx) => { ctx.csWitnessToken = 'tok'; ctx.csWitnessWho = 'EMP-2'; },
    press: (ctx) => ctx.saveCsCount()
  },
  {
    id: 'R', name: 'saveCredEntry',
    ok: { id: 'x' }, refused: null,
    src: H.optional(html, /var crSaving\s*=\s*false;/) + '\n' + lift('async function saveCredEntry(){'),
    fields: { 'cr-type': 'license', 'cr-staff': 'EMP-1', 'cr-notes': '', 'cr-credname': 'RN licence', 'cr-expires': '2027-06-30' },
    given: (write) => ({ newId: (p) => p + '-' + (++seq), alfData: write, alfStaffName: () => 'Sam' }),
    press: (ctx) => ctx.saveCredEntry()
  },
  {
    id: 'O', name: 'saveOpAudit',
    ok: { id: 'x', passed: true }, refused: null,
    src: H.optional(html, /var opaSaving\s*=\s*false;/) + '\n' + lift('async function saveOpAudit(){'),
    fields: { 'opa-date': '2026-10-29', 'opa-notes': '', 'opa-subject': 'Kitchen sanitiser log', 'opa-passed': '1' },
    given: (write) => ({ _opaType: 'checklist', newId: (p) => p + '-' + (++seq), alfData: write }),
    press: (ctx) => ctx.saveOpAudit()
  }
];

(async () => {
  for (const s of SPECS) {
    console.log(s.name);
    await H.drive({ check, id: s.id, name: s.name, mk: H.mkFor(s), ok: s.ok, refused: s.refused });
  }
  finished = true;
  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairncare save re-entry: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('COULD NOT RUN: ' + e.stack); process.exit(2); });
// A run that ends with an arm still waiting (the IIFE unsettled) exits 0 in
// node with nothing printed. It must read as COULD NOT RUN.
process.on('exit', () => { if (!finished) { console.log('COULD NOT RUN: the run ended before its last arm'); process.exitCode = 2; } });
