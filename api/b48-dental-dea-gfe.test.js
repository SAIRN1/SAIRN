// api/b48-dental-dea-gfe.test.js
//
// Run:  node api/b48-dental-dea-gfe.test.js
//
// Two server-side dental defects from fourth's b44 audit, left open in b45:
//
// DEA -- CONCEPT: a DEA registration is per REGISTRATION NUMBER (21 CFR
// 1301.12(a): a separate registration for each principal place of business),
// so latestByKey() keys DEA rows by provider + normalised number. Before, the
// key was provider + '' and a provider's second registration silently retired
// the first -- an expired registration vanished from the board.
//
// GFE -- CONCEPT: an Issued estimate PRINTS its own frozen copy of the
// patient's name and DOB, so the server's 45 CFR 149.610(c)(1) check reads that
// copy as well as the server-side patient record. Before, it read only the live
// record and passed an estimate that printed "date of birth --".
//
// MUTATION CONTROLS: the same arms run against mutated copies of each module,
// compiled under the real filename. Every mutant must be KILLED. A mutant whose
// anchor does not match exactly once is COULD NOT RUN, never a pass.
//
// Exit: 0 all arms passed and every mutant killed - 1 an arm FAILED or a
// mutant SURVIVED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const Module = require('module');

const CRED = path.join(__dirname, '_lib', 'dental-credentials.js');
const GFE = path.join(__dirname, '_lib', 'dental-gfe.js');
const SRC = { [CRED]: fs.readFileSync(CRED, 'utf8'), [GFE]: fs.readFileSync(GFE, 'utf8') };
function compile(file, src) {
  const m = new Module(file, module);
  m.filename = file;
  m.paths = Module._nodeModulePaths(path.dirname(file));
  m._compile(src, file);
  return m.exports;
}

const TODAY = '2026-10-21';
const DEA = (o) => Object.assign({ provider_id: 'PRV-1', record_type: 'dea_registration', mate_attested: true,
  mate_attested_on: '2024-03-01', recorded_at: '2026-01-01T00:00:00Z' }, o);
const PT = { name: 'A Patient', dob: '1980-04-01' };
const SETTINGS = { gfe_legal_name: 'Pinnacle Dental LLC', gfe_npi: '1234567890', gfe_tin: '12-3456789',
  gfe_state: 'OH', practice_address: '1 Main St' };
const ISSUED = { id: 'GFE-1', patient_id: 'PT-1', status: 'Issued', patient_name: 'A Patient', patient_dob: '1980-04-01',
  primary_description: 'D2740 -- crown', lines: [{ cdt_code: 'D2740', expected_charge: 1200 }] };

function arms(cred, gfe) {
  const out = [];
  const check = (name, cond, detail) => out.push({ name, ok: !!cond, detail });
  const T = (f) => { try { return f(); } catch (e) { return 'THREW ' + e.message; } };

  let r = T(() => cred.latestByKey([DEA({ entry_id: 'A', number: 'AB1234563' }), DEA({ entry_id: 'B', number: 'FB7654321', recorded_at: '2026-05-01T00:00:00Z' })]));
  check('D1. two registrations for one provider are TWO records', Array.isArray(r) && r.length === 2, JSON.stringify(r));
  r = T(() => cred.latestByKey([DEA({ entry_id: 'A', number: 'AB1234563', expires_on: '2026-01-31' }),
    DEA({ entry_id: 'B', number: 'ab 123-4563', expires_on: '2029-01-31', recorded_at: '2026-05-01T00:00:00Z' })]));
  check('D2. a renewal of the SAME registration (case, spaces, hyphens differ) supersedes it',
    Array.isArray(r) && r.length === 1 && r[0].entry_id === 'B', JSON.stringify(r));
  r = T(() => cred.evaluateBoard([DEA({ entry_id: 'A', number: 'AB1234563', expires_on: '2026-08-01' }),
    DEA({ entry_id: 'B', number: 'FB7654321', expires_on: '2029-01-31', recorded_at: '2026-05-01T00:00:00Z' })], [], TODAY));
  check('D3. the board shows the expired first registration next to the newer one',
    r && r.counts && r.counts.expired === 1 && r.counts.ok === 1, JSON.stringify(r && r.counts));
  r = T(() => cred.latestByKey([DEA({ entry_id: 'A' }), DEA({ entry_id: 'B', recorded_at: '2026-05-01T00:00:00Z' })]));
  check('D4. rows with no number still key as one (cannot be told apart)', Array.isArray(r) && r.length === 1 && r[0].entry_id === 'B', JSON.stringify(r));
  r = T(() => cred.latestByKey([{ provider_id: 'PRV-1', record_type: 'state_license', state: 'OH', entry_id: 'A' },
    { provider_id: 'PRV-1', record_type: 'state_license', state: 'oh', entry_id: 'B' }]));
  check('D5. control: state licences still key by state only', Array.isArray(r) && r.length === 1, JSON.stringify(r));

  let m = T(() => gfe.gfeMissing(Object.assign({}, ISSUED, { patient_dob: '' }), PT, SETTINGS));
  check('G1. Issued, printed copy has NO DOB, live record has one -> DOB missing (the defect)',
    Array.isArray(m) && m.length === 1 && /date of birth/.test(m[0]), JSON.stringify(m));
  m = T(() => gfe.gfeMissing(Object.assign({}, ISSUED, { patient_name: '' }), PT, SETTINGS));
  check('G2. Issued, printed copy has NO name -> name missing', Array.isArray(m) && m.length === 1 && /patient name/.test(m[0]), JSON.stringify(m));
  m = T(() => gfe.gfeMissing(ISSUED, null, SETTINGS));
  check('G3. Issued, printed copy complete but NO server-side patient -> still refused (caller copy alone not trusted)',
    Array.isArray(m) && m.some((x) => /patient name/.test(x)) && m.some((x) => /date of birth/.test(x)), JSON.stringify(m));
  m = T(() => gfe.gfeMissing(Object.assign({}, ISSUED, { status: 'Draft', patient_name: '', patient_dob: '' }), PT, SETTINGS));
  check('G4. a Draft reads the live record; its save-time copy is not checked', Array.isArray(m) && m.length === 0, JSON.stringify(m));
  m = T(() => gfe.issuedWithoutRequiredElements(ISSUED, PT, SETTINGS));
  check('G5. a complete Issued estimate is allowed', m === null, JSON.stringify(m));
  m = T(() => gfe.issuedWithoutRequiredElements(Object.assign({}, ISSUED, { status: ' issued ', patient_dob: '' }), PT, SETTINGS));
  check('G6. the refusal message names the DOB, status case/space-insensitive', typeof m === 'string' && /date of birth/.test(m), JSON.stringify(m));
  return out;
}

const MUTANTS = [
  { name: 'M1 DEA key reverted to provider only', file: CRED,
    anchor: "rec.record_type === 'dea_registration' ? deaKey(rec.number) : ''", repl: "''" },
  { name: 'M2 DEA number not normalised', file: CRED,
    anchor: "return String(s == null ? '' : s).toUpperCase().replace(/[\\s-]+/g, '');", repl: "return String(s == null ? '' : s);" },
  { name: 'M3 the printed DOB not checked', file: GFE,
    anchor: " || (issued && !r.patient_dob)", repl: '' },
  { name: 'M4 the printed name not checked', file: GFE,
    anchor: " || (issued && !r.patient_name)", repl: '' },
  { name: 'M5 the live record dropped for an Issued estimate', file: GFE,
    anchor: "if (!pt || !pt.name || (issued && !r.patient_name))", repl: "if (issued ? !r.patient_name : (!pt || !pt.name))" },
];

let fail = 0, couldNot = 0;
const real = arms(require(CRED), require(GFE));
real.forEach((a) => {
  if (a.ok) console.log('  ok   ' + a.name);
  else { fail++; console.log('  FAIL ' + a.name + (a.detail ? '\n       ' + String(a.detail).slice(0, 300) : '')); }
});
MUTANTS.forEach((mu) => {
  const n = SRC[mu.file].split(mu.anchor).length - 1;
  if (n !== 1) { couldNot++; console.log('  COULD NOT RUN ' + mu.name + ': anchor found ' + n + ' times'); return; }
  const mod = compile(mu.file, SRC[mu.file].replace(mu.anchor, mu.repl));
  const res = mu.file === CRED ? arms(mod, require(GFE)) : arms(require(CRED), mod);
  const killedBy = res.filter((a) => !a.ok).map((a) => a.name.split('.')[0]);
  if (killedBy.length) console.log('  ok   ' + mu.name + ' -- KILLED by ' + killedBy.join(', '));
  else { fail++; console.log('  FAIL ' + mu.name + ' -- SURVIVED: no arm noticed'); }
});
console.log('\n' + (couldNot ? 'COULD NOT RUN' : fail ? 'FAILED' : 'ok') + '  b48 dental DEA + GFE: ' + real.filter((a) => a.ok).length + '/' + real.length
  + ' arms, ' + MUTANTS.length + ' mutants, ' + fail + ' failed, ' + couldNot + ' could not run');
process.exit(couldNot ? 2 : fail ? 1 : 0);
