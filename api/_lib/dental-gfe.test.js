// api/_lib/dental-gfe.test.js
//
// Run:  node api/_lib/dental-gfe.test.js
//
// sairndental.html's issueGfe() has always refused to mark a Good Faith
// Estimate Issued while any element required by 45 CFR 149.610(c)(1) is
// missing, and its comment says why: "an estimate handed to a patient missing
// a required element is a non-compliant document that looks compliant, which
// is worse than no document at all -- the practice believes it has met the
// obligation and has not."
//
// That refusal was BROWSER JAVASCRIPT. The write went to api/sd-data.js's
// generic DNT_RESOURCES handler, which validated payload.id and nothing else
// for fifteen resources, so the server stored status:'Issued' on an incomplete
// estimate. Found 2026-09-04 during a cross-path sweep, one row after the same
// shape was found for the paediatric guardian rule.
//
// The element list is asserted against sairndental.html's own gfeMissing(),
// not against a list retyped here -- a server rule that has silently drifted
// from the rule the practice sees in the app is the defect this file exists to
// prevent, one layer along.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..', '..');
const gfe = require('./dental-gfe');
const app = fs.readFileSync(path.join(ROOT, 'sairndental.html'), 'utf8');
const data = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

const PT = { name: 'A Patient', dob: '1980-04-01' };
const SETTINGS = {
  gfe_legal_name: 'Pinnacle Dental LLC', gfe_npi: '1234567890',
  gfe_tin: '12-3456789', gfe_state: 'OH', practice_address: '1 Main St'
};
const REC = {
  id: 'GFE-1', patient_id: 'PT-1', status: 'Issued',
  primary_description: 'D2740 -- crown, porcelain',
  lines: [{ cdt_code: 'D2740', expected_charge: 1200 }]
};

// ---------------------------------------------------------------------------
section('a complete estimate passes; each missing element is named');

test('complete -> nothing missing, and issuing is allowed', () => {
  assert.deepStrictEqual(gfe.gfeMissing(REC, PT, SETTINGS), []);
  assert.strictEqual(gfe.issuedWithoutRequiredElements(REC, PT, SETTINGS), null);
});

test('every one of the ten elements is detected on its own', () => {
  const cases = [
    ['patient name', () => [REC, { dob: PT.dob }, SETTINGS], /\(c\)\(1\)\(i\) patient name/],
    ['patient dob', () => [REC, { name: PT.name }, SETTINGS], /\(c\)\(1\)\(i\) patient date of birth/],
    ['primary description', () => [Object.assign({}, REC, { primary_description: '' }), PT, SETTINGS], /\(c\)\(1\)\(ii\)/],
    ['no lines', () => [Object.assign({}, REC, { lines: [] }), PT, SETTINGS], /\(c\)\(1\)\(iii\)/],
    ['line without a code', () => [Object.assign({}, REC, { lines: [{ expected_charge: 10 }] }), PT, SETTINGS], /a service code on every line/],
    ['line without a charge', () => [Object.assign({}, REC, { lines: [{ cdt_code: 'D1110' }] }), PT, SETTINGS], /an expected charge on every line/],
    ['legal name', () => [REC, PT, Object.assign({}, SETTINGS, { gfe_legal_name: '' })], /practice legal name/],
    ['npi', () => [REC, PT, Object.assign({}, SETTINGS, { gfe_npi: '' })], /National Provider Identifier/],
    ['tin', () => [REC, PT, Object.assign({}, SETTINGS, { gfe_tin: '' })], /Tax Identification Number/],
    ['state', () => [REC, PT, Object.assign({}, SETTINGS, { gfe_state: '' })], /State where services are furnished/],
    ['address', () => [REC, PT, Object.assign({}, SETTINGS, { practice_address: '' })], /location where services are furnished/],
  ];
  cases.forEach(([label, args, re]) => {
    const miss = gfe.gfeMissing.apply(null, args());
    assert.ok(miss.length > 0, label + ': nothing was reported missing');
    assert.ok(miss.some((m) => re.test(m)), label + ': not named -- got ' + JSON.stringify(miss));
  });
});

test('A ZERO CHARGE IS MISSING, NOT PRESENT', () => {
  // `Number(0) > 0` is false on purpose: a line with no price is not an
  // estimate of anything, and `!l.expected_charge` would also have caught it
  // while wrongly accepting the string "0".
  const zero = Object.assign({}, REC, { lines: [{ cdt_code: 'D1110', expected_charge: 0 }] });
  assert.ok(gfe.gfeMissing(zero, PT, SETTINGS).some((m) => /expected charge/.test(m)));
  const strZero = Object.assign({}, REC, { lines: [{ cdt_code: 'D1110', expected_charge: '0' }] });
  assert.ok(gfe.gfeMissing(strZero, PT, SETTINGS).some((m) => /expected charge/.test(m)));
});

test('a MISSING patient record is a missing name AND dob, not a crash', () => {
  const miss = gfe.gfeMissing(REC, null, SETTINGS);
  assert.ok(miss.some((m) => /patient name/.test(m)));
  assert.ok(miss.some((m) => /date of birth/.test(m)));
});

test('missing settings entirely does not throw', () => {
  assert.doesNotThrow(() => gfe.gfeMissing(REC, PT, null));
  assert.doesNotThrow(() => gfe.gfeMissing(null, null, null));
});

// ---------------------------------------------------------------------------
section('only an ISSUED estimate is refused');

test('a Draft may be incomplete -- that is what a draft is for', () => {
  const draft = Object.assign({}, REC, { status: 'Draft', primary_description: '', lines: [] });
  assert.ok(gfe.gfeMissing(draft, PT, SETTINGS).length > 0, 'the fixture is not actually incomplete');
  assert.strictEqual(gfe.issuedWithoutRequiredElements(draft, PT, SETTINGS), null,
    'a draft was refused -- the feature would be unusable while being filled in');
});

test('an incomplete Issued estimate is refused, and the message lists what is missing', () => {
  const bad = Object.assign({}, REC, { primary_description: '', lines: [] });
  const msg = gfe.issuedWithoutRequiredElements(bad, PT, SETTINGS);
  assert.ok(msg, 'an incomplete issued estimate was allowed');
  assert.match(msg, /45 CFR 149\.610\(c\)\(1\)/);
  assert.match(msg, /\(c\)\(1\)\(ii\)/);
  assert.match(msg, /\(c\)\(1\)\(iii\)/);
});

test('status matching is case- and space-insensitive', () => {
  const bad = Object.assign({}, REC, { primary_description: '', lines: [] });
  ['Issued', 'issued', ' ISSUED '].forEach((st) => {
    assert.ok(gfe.issuedWithoutRequiredElements(Object.assign({}, bad, { status: st }), PT, SETTINGS),
      'status ' + JSON.stringify(st) + ' was not treated as issued');
  });
});

// ---------------------------------------------------------------------------
section('the server rule matches the one the practice sees in the app');

test('THE ELEMENT LABELS ARE IDENTICAL to sairndental.html gfeMissing()', () => {
  // A differently-worded refusal from the API would reasonably read as a
  // different problem. Scraped from the app rather than retyped, so drift
  // fails here rather than being discovered by a practice.
  const i = app.indexOf('function gfeMissing(rec){');
  assert.ok(i > 0, 'gfeMissing not found in sairndental.html');
  const block = app.slice(i, app.indexOf('\n}', i));
  const appLabels = (block.match(/miss\.push\('([^']+)'\)/g) || [])
    .map((m) => m.replace(/^miss\.push\('/, '').replace(/'\)$/, '')).sort();

  const libSrc = fs.readFileSync(path.join(__dirname, 'dental-gfe.js'), 'utf8');
  const j = libSrc.indexOf('function gfeMissing(');
  const libBlock = libSrc.slice(j, libSrc.indexOf('\n}', j));
  const libLabels = (libBlock.match(/miss\.push\('([^']+)'\)/g) || [])
    .map((m) => m.replace(/^miss\.push\('/, '').replace(/'\)$/, '')).sort();

  assert.deepStrictEqual(libLabels, appLabels,
    'the server and the app name different elements -- a practice would see two problems where there is one');
});

// ---------------------------------------------------------------------------
section('the generic write actually calls it');

test('sd-data.js consults the rule on a dnt_gfe write', () => {
  const code = data.replace(/\/\/[^\n]*/g, '');
  assert.match(code, /require\('\.\/_lib\/dental-gfe'\)/);
  assert.match(code, /dntGfe\.issuedWithoutRequiredElements\(/);
  assert.match(code, /code: 'GFE_INCOMPLETE'/);
  // THE REFUSAL IS DRIVEN BY THE VERDICT, not merely present in the file. A
  // control that changed `if (problem)` to `if (false)` passed an earlier
  // version of this arm -- the same computed-then-discarded shape as the
  // CourtListener limiter, which is the third time that pattern has appeared
  // today. Asserting the branch tests the value is the only thing that catches
  // it.
  assert.match(code, /if \(problem\) \{ res\.status\(400\)/,
    'the GFE verdict is computed and not acted on');
});

test('...ONLY when the status is issued, so a draft costs no extra reads', () => {
  const code = data.replace(/\/\/[^\n]*/g, '');
  assert.match(code, /resource === 'dnt_gfe' && String\(\(payload\.status \|\| ''\)\)\.trim\(\)\.toLowerCase\(\) === 'issued'/,
    'the gfe check is not gated on the status, so every draft save pays for two reads');
});

test('THE PATIENT AND PRACTICE DETAILS ARE READ SERVER-SIDE, not taken from the payload', () => {
  // Half the required elements live on records the caller is not sending, and
  // trusting a caller's copy of the practice's own NPI would make the check
  // theatre.
  const code = data.replace(/\/\/[^\n]*/g, '');
  const i = code.indexOf("resource === 'dnt_gfe' &&");
  const block = code.slice(i, i + 1600);
  assert.match(block, /rest\('dnt_patients\?license_hash=eq\./);
  assert.match(block, /rest\('dnt_settings\?license_hash=eq\./);
  assert.ok(!/payload\.gfe_npi|payload\.settings/.test(block),
    'practice identifiers are being taken from the payload');
});

test('AN UNREADABLE CHECK REFUSES -- it does not read as "nothing missing"', () => {
  const code = data.replace(/\/\/[^\n]*/g, '');
  const i = code.indexOf("resource === 'dnt_gfe' &&");
  const block = code.slice(i, i + 1600);
  assert.match(block, /if \(!ptR\.ok \|\| !stR\.ok\)/,
    'a failed read of the patient or settings is not handled');
  assert.match(block, /GFE_CHECK_UNAVAILABLE/);
  const iFail = block.indexOf('if (!ptR.ok || !stR.ok)');
  const iUse = block.indexOf('issuedWithoutRequiredElements');
  assert.ok(iFail > 0 && iFail < iUse, 'the failure is checked after the rule has already run');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' GFE ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
