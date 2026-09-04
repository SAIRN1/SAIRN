// api/sairndental/public-book-guardian.test.js
//
// Run:  node api/sairndental/public-book-guardian.test.js
//
// sairndental.html's Add Patient form has always refused to save a patient
// under 18 without a guardian name and at least one guardian contact method,
// and a comment beside rcReachable() asserted it as a property of the system:
//
//     "this form already enforces that -- a minor cannot be saved without a
//      guardian phone or email"
//
// TRUE OF THAT FORM, FALSE OF THE SYSTEM. api/sairndental/public-book.js is
// the other way in -- public, unauthenticated, and the one a parent actually
// uses -- and the patient object it wrote did not merely leave the guardian
// fields empty, it did not contain the keys.
//
// Two consequences, neither visible from the response: a paediatric record
// existed with no guardian contact, and rcReachable() then fell back to
// whatever phone number was typed into a public form -- possibly the child's.
// Meanwhile the practice believed the rule held, because the form they look at
// every day does enforce it.
//
// These assertions are mostly SOURCE-LEVEL rather than behavioural. The
// endpoint needs a live Supabase and a resolvable slug before it reaches the
// guardian check, and standing one up to prove a validation rule would test
// the fixture more than the rule. What the age arithmetic does is exercised
// directly, because that is where an off-by-one actually lives.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..', '..');
const ep = fs.readFileSync(path.join(__dirname, 'public-book.js'), 'utf8');
const page = fs.readFileSync(path.join(ROOT, 'sairndental-book.html'), 'utf8');
const app = fs.readFileSync(path.join(ROOT, 'sairndental.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// Pull the two real implementations and run them side by side.
function grab(src, sig, term) {
  const i = src.indexOf(sig);
  assert.ok(i > 0, sig + ' not found');
  const rel = src.slice(i).indexOf(term);
  assert.ok(rel > 0, sig + ' is not terminated');
  return src.slice(i, i + rel) + term;
}
// The SERVER rule now lives in one place, shared by both server write paths --
// api/_lib/dental-guardian.js. It used to be a private copy inside
// public-book.js, which is precisely how the rule ended up enforced on one
// server path and not the other, so it is required here rather than scraped
// out of a file.
const guardianLib = require(path.join(ROOT, 'api', '_lib', 'dental-guardian.js'));
const isMinorDob = guardianLib.isMinorDob;
const guardianProblem = guardianLib.guardianProblem;

// The BROWSER copy stays separate and is still scraped, because it is
// deliberately a different answer on unreadable input -- see the arm below.
const clientFn = grab(page, 'function bkIsMinor(dob){', '\n}');

function make(src, name) {
  const ctx = { Date: Date, String: String, Number: Number, isNaN: isNaN, console: console };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  return ctx[name];
}
const bkIsMinor = make(clientFn, 'bkIsMinor');

function isoYearsAgo(years, offsetDays) {
  const d = new Date();
  d.setFullYear(d.getFullYear() - years);
  if (offsetDays) d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
section('the age arithmetic, which is where an off-by-one would live');

test('a clear minor and a clear adult', () => {
  assert.strictEqual(isMinorDob(isoYearsAgo(10)), true);
  assert.strictEqual(isMinorDob(isoYearsAgo(40)), false);
});

test('THE BOUNDARY: 18 today is NOT a minor; one day short still is', () => {
  assert.strictEqual(isMinorDob(isoYearsAgo(18)), false, 'exactly 18 today was treated as a minor');
  assert.strictEqual(isMinorDob(isoYearsAgo(18, 1)), true, 'one day short of 18 was treated as an adult');
});

test('the client copy agrees with the server on every one of those', () => {
  [isoYearsAgo(10), isoYearsAgo(40), isoYearsAgo(18), isoYearsAgo(18, 1), isoYearsAgo(17)]
    .forEach((d) => assert.strictEqual(bkIsMinor(d), isMinorDob(d), 'disagree on ' + d));
});

test('THEY DIVERGE ON UNREADABLE INPUT, AND THAT IS THE POINT', () => {
  // The server treats an unparseable or missing DOB as a MINOR: its input is
  // untrusted, so it asks for a guardian rather than waving the caller
  // through. The browser copy returns false, which is right there -- the field
  // is required and already checked, and hiding the fields on a half-typed
  // date would fight the user.
  ['', null, undefined, 'not-a-date', '2020-13-45', '1990'].forEach((bad) => {
    assert.strictEqual(isMinorDob(bad), true,
      'the SERVER waved through an unreadable DOB: ' + JSON.stringify(bad));
  });
  assert.strictEqual(bkIsMinor(''), false, 'the client hides the fields for an empty date');
  assert.strictEqual(bkIsMinor('not-a-date'), false);
});

// ---------------------------------------------------------------------------
section('the endpoint refuses, and refuses before it writes anything');

test('a minor without a guardian is a 400 GUARDIAN_REQUIRED', () => {
  assert.match(ep, /code: 'GUARDIAN_REQUIRED'/);
  // The message now comes from the shared module, so assert it there.
  assert.match(guardianProblem({ dob: '2015-01-01' }) || '',
    /under 18, so the record needs a parent or guardian name and either a phone number or an email address/);
});

test('THE CHECK IS REACHABLE -- the refusal is driven by the rule, not a constant', () => {
  // Asserting the presence of an error string is not asserting that anything
  // can produce it: an earlier version of this arm survived an `if (false)`
  // wrapped around the whole block. Now the predicate itself is exercised.
  assert.ok(guardianProblem({ dob: '2015-01-01' }), 'a minor with no guardian is not refused');
  assert.strictEqual(guardianProblem({ dob: '1980-01-01' }), null, 'an adult is refused');
  const code = ep.replace(/\/\/[^\n]*/g, '');
  assert.match(code, /const guardianGap = guardianProblem\(/,
    'the endpoint no longer consults the shared rule');
  assert.match(code, /if \(guardianGap\) \{/,
    'the endpoint computes the verdict and does not act on it');
});

test('the rule is name AND (phone OR email) -- the same one the app uses', () => {
  // Behavioural now, not a regex over one spelling of it.
  const dob = '2015-01-01';
  assert.ok(guardianProblem({ dob: dob }), 'no guardian at all is allowed');
  assert.ok(guardianProblem({ dob: dob, guardian: { name: 'A Parent' } }),
    'a name with no contact method is allowed');
  assert.ok(guardianProblem({ dob: dob, guardian: { phone: '5555555555' } }),
    'a phone with no name is allowed');
  assert.strictEqual(guardianProblem({ dob: dob, guardian: { name: 'A Parent', phone: '5555555555' } }), null);
  assert.strictEqual(guardianProblem({ dob: dob, guardian: { name: 'A Parent', email: 'p@example.com' } }), null);
  // The app's stored field names must satisfy it too -- that is the shape
  // api/sd-data.js receives from sairndental.html.
  assert.strictEqual(guardianProblem({ dob: dob, guardian_name: 'A Parent', guardian_phone: '5555555555' }), null,
    'the stored field names are not accepted, so the in-app write would be refused wrongly');
  const appRule = app.replace(/\/\/[^\n]*/g, '');
  assert.match(appRule, /if\(isMinor&&\(!gName\|\|\(!gPhone&&!gEmail\)\)\)/,
    'the in-app browser rule changed shape -- the paths would now disagree');
});

test('BOTH SERVER PATHS USE THE SAME MODULE -- neither keeps a private copy', () => {
  // The whole defect was one rule with two implementations, one of which did
  // not exist. A second inline copy is the way back to that.
  const data = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');
  assert.match(ep, /require\('\.\.\/_lib\/dental-guardian'\)/);
  assert.match(data, /require\('\.\/_lib\/dental-guardian'\)/);
  assert.ok(!/function isMinorDob\(/.test(ep),
    'public-book.js has grown its own copy of the age rule again');
  assert.ok(!/function isMinorDob\(/.test(data),
    'sd-data.js has grown its own copy of the age rule');
});

test('the AUTHENTICATED write path enforces it too, which it did not before', () => {
  const data = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');
  const code = data.replace(/\/\/[^\n]*/g, '');
  const i = code.indexOf("if (DNT_RESOURCES[resource] && action === 'write')");
  assert.ok(i > 0, 'the generic dnt write block moved');
  const block = code.slice(i, i + 4000);
  assert.match(block, /if \(resource === 'dnt_patients'\) \{/,
    'the generic write no longer special-cases dnt_patients for the guardian rule');
  assert.match(block, /dntGuardianProblem\(payload\)/);
  assert.match(block, /code: 'GUARDIAN_REQUIRED'/);
});

test('THE REFUSAL COMES BEFORE THE PATIENT ROW IS WRITTEN', () => {
  // Refusing after the write would leave exactly the record the rule exists to
  // prevent, and the endpoint has already been bitten once by ordering (the
  // phantom patient_id fixed on 2026-09-03).
  const iCheck = ep.indexOf("code: 'GUARDIAN_REQUIRED'");
  const iWrite = ep.indexOf('const newPatient =');
  assert.ok(iCheck > 0 && iWrite > 0, 'could not locate both points');
  assert.ok(iCheck < iWrite, 'the guardian check runs after the patient row is built');
});

test('the guardian keys are written for EVERY patient, not only minors', () => {
  // Two shapes of dnt_patients row would mean a reader has to know which door
  // a record came through.
  const i = ep.indexOf('const newPatient =');
  const block = ep.slice(i, i + 700);
  ['guardian_name', 'guardian_relationship', 'guardian_phone', 'guardian_email']
    .forEach((k) => assert.ok(block.indexOf(k) !== -1, k + ' is missing from the written record'));
});

test('an adult gets EMPTY guardian fields, not the ones that were posted', () => {
  // ALL FOUR, not just the first. A negative control that made only
  // guardian_email unconditional passed an earlier version of this arm, which
  // checked guardian_name and stopped.
  const i = ep.indexOf('const newPatient =');
  const block = ep.slice(i, i + 900);
  ['guardian_name', 'guardian_relationship', 'guardian_phone', 'guardian_email'].forEach((k) => {
    assert.ok(new RegExp(k + ': isMinor \\?').test(block),
      k + ' is stored unconditionally -- an adult booking could carry it');
  });
});

// ---------------------------------------------------------------------------
section('the page asks for them, and asks at the right moment');

test('the booking page has the four guardian inputs', () => {
  ['bk-guardian-name', 'bk-guardian-relationship', 'bk-guardian-phone', 'bk-guardian-email']
    .forEach((id) => assert.ok(page.indexOf('id="' + id + '"') !== -1, id + ' is missing'));
});

test('...they start hidden, and are posted to the endpoint', () => {
  assert.match(page, /id="bk-guardian-group" style="display:none"/);
  assert.match(page, /guardian:\s*\{/);
});

test('it refuses at the DETAILS step, before photos and the slot pick', () => {
  // Walking a parent through photo upload and then refusing is a worse
  // experience than asking on the form that is already open.
  //
  // THE GATE IS ASSERTED, NOT JUST THE MESSAGE. An earlier version checked
  // only that the words "under 18" appeared before showStep('photo'), and a
  // negative control replacing `if(bkIsMinor(dob))` with `if(false)` sailed
  // past it -- the message was still there, unreachable. Same class as the
  // endpoint arm two sections up.
  const i = page.indexOf('function continueToPhotoStep()');
  const block = page.slice(i, i + 1400);
  assert.match(block, /if\(bkIsMinor\(dob\)\)\{/,
    'the page-side guardian check is no longer gated on the patient being a minor');
  assert.match(block, /under 18/);
  assert.ok(block.indexOf("showStep('photo')") > block.indexOf('if(bkIsMinor(dob)){'),
    'the step advances before the guardian check');
});

test('THE INIT BUG IS CLOSED ON BOTH PAGES', () => {
  // A restored date of birth never fires onchange, so the fields stayed hidden
  // while the save still demanded them -- the user was told a field was
  // required with nothing on screen to type it into.
  assert.match(page, /showStep\('details'\);\s*(\/\/[^\n]*\n\s*)*onBkDobChange\(\);/,
    'the booking page does not re-evaluate the guardian fields when the step is shown');
  const iR = app.indexOf('function rPatients()');
  const rBlock = app.slice(iR, app.indexOf('\n}', iR));
  assert.match(rBlock, /onPtDobChange\(\)/,
    'the in-app patients panel still only toggles on change');
});

// ---------------------------------------------------------------------------
section('the comment that was true of one form and false of the system');

test('the old absolute claim is gone', () => {
  // Line-wrapping stripped first, and the assertion is on the CLAIM rather
  // than on one formatting of it. The first version matched the exact two-line
  // original and a negative control that restored the same sentence on ONE
  // line sailed past -- an assertion that only catches a defect typed the way
  // it was typed last time.
  const flat = app.replace(/\r?\n\s*\/\/ ?/g, ' ');
  const claim = /this form already enforces that -- a minor cannot be saved without a guardian/i;
  const hits = (flat.match(new RegExp(claim.source, 'gi')) || []);
  // The corrected comment quotes the old wording deliberately, in the past
  // tense, so one occurrence is expected -- inside a "THIS COMMENT USED TO
  // SAY" block. More than that, or one outside it, is the claim coming back.
  assert.ok(hits.length <= 1, 'the old absolute claim appears ' + hits.length + ' times');
  if (hits.length === 1) {
    const i = flat.search(claim);
    const context = flat.slice(Math.max(0, i - 260), i);
    assert.match(context, /USED TO SAY|used to say/,
      'the absolute claim is being asserted again rather than quoted as history');
  }
});

test('...and what replaced it names the path that used to bypass it', () => {
  const i = app.indexOf('function rcReachable');
  // Comment markers and line breaks are stripped first. The phrase being
  // asserted wraps across a `\n// ` in the source, and the first version of
  // this arm matched the raw text and failed on a comment that was present and
  // correct -- the same line-wrapped-prose false negative that has bitten three
  // assertions in this repo today.
  const before = app.slice(Math.max(0, i - 1800), i)
    .replace(/\r?\n\s*\/\/ ?/g, ' ');
  assert.match(before, /public-book\.js/,
    'the corrected comment does not name the endpoint that bypassed the rule');
  assert.match(before, /Both paths now enforce the same rule/);
  assert.match(before, /TRUE OF THIS FORM AND FALSE OF THE SYSTEM/);
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' GUARDIAN ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
