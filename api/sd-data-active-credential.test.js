// api/sd-data-active-credential.test.js
// REQUIREMENT: a session token whose credential has since been DEACTIVATED
//   cannot reach a gated resource in api/sd-data.js, and a re-check that
//   could not run is logged rather than folded into either answer
//
// Run:  node api/sd-data-active-credential.test.js
//
// ── WHY A STRUCTURAL TEST AND NOT A DRIVEN ONE ─────────────────────────────
// api/sd-data.js is ~6000 lines behind an env-configured Supabase client, and
// every existing test for it in this directory reads the SOURCE rather than
// executing the handler. The BEHAVIOUR of the re-check is driven for real in
// api/_lib/auth.test.js -- eleven arms including the sabotage one, where a
// single token is verified before and after the row behind it is flipped.
// What THIS file holds is that sd-data actually calls it, in the right place,
// and handles its three answers as three.
//
// ── THE DEFECT ─────────────────────────────────────────────────────────────
// verifySessionToken proves a token was minted by this platform and has not
// expired. It proves nothing about NOW. Until 2026-09-16 a deactivated
// employee kept read and write access to every gated resource here for the
// remaining life of a 12h token. api/sc-auth.js closed this for its own
// roster/set_active on 2026-08-23 and api/_lib/employee-lifecycle.js carries it
// for the apps that share it; NOTHING closed it for the data path, which is
// thirteen apps' resources.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const SRC = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8')
  .replace(/\r\n/g, '\n');
const CODE = SRC.replace(/^\s*\/\/[^\n]*$/gm, '');   // comments never count

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (err) {
    console.error('  FAIL - ' + name);
    console.error('    ' + err.message);
    process.exitCode = 1;
  }
}

test('the re-check is IMPORTED from the shared module, not reimplemented here',
  () => {
    assert.ok(/require\('\.\/_lib\/auth'\)/.test(CODE), 'no auth import');
    assert.ok(/credentialStillActive/.test(CODE),
      'sd-data does not reference credentialStillActive at all');
    assert.ok(!/AUTH_TABLE_BY_APP\s*=/.test(CODE),
      'a SECOND copy of the table map lives here, which is the drift the shared '
      + 'module exists to prevent');
  });

test('it is CALLED, and awaited -- a dropped promise here would gate on nothing',
  () => {
    assert.ok(/await\s+credentialStillActive\(/.test(CODE),
      'credentialStillActive is referenced but never awaited');
  });

test('THE ORDER: the re-check runs AFTER a token is verified and BEFORE any '
  + 'resource handler', () => {
    // RE-ANCHORED 2026-09-26. This read `const gateSession = verifySessionToken(`
    // -- the SD_SESSION_GATED gate -- and went red when the re-check moved ABOVE
    // that gate to the single entry point. The property it guards did not change:
    // a token must be verified before the credential behind it is looked up.
    // What changed is WHICH verification, so the anchor is now the pre-gate's.
    const verify = CODE.indexOf('const preSession = verifySessionToken(');
    const recheck = CODE.indexOf('await credentialStillActive(');
    assert.ok(verify > 0, 'the pre-gate session verification moved');
    assert.ok(recheck > verify,
      'the re-check runs before any token is verified, so it would query for a '
      + 'session that may not exist');
    const firstHandler = CODE.indexOf("if (resource === 'profile'");
    assert.ok(firstHandler > recheck,
      'a resource handler runs before the re-check, so that resource is still '
      + 'reachable with a deactivated credential');
  });

test('COVERAGE: the re-check is NOT inside a per-resource conditional -- the arm '
  + 'this file spent its whole life without', () => {
    // THE DEFECT THIS ARM EXISTS FOR IS THIS FILE'S OWN. Eight arms passed for
    // ten days while the re-check covered 70 of 132 gates, because every one of
    // them was satisfied by ONE correct call site and nothing asked HOW MANY
    // gates it stood in front of. `/await credentialStillActive\(/` is satisfied
    // by a single match.
    const recheck = CODE.indexOf('await credentialStillActive(');
    assert.ok(recheck > 0, 'no re-check call site at all');
    const gated = CODE.indexOf('if (SD_SESSION_GATED[resource]');
    assert.ok(gated > 0, 'the SD_SESSION_GATED block moved');
    assert.ok(recheck < gated,
      'the re-check sits INSIDE or AFTER the SD_SESSION_GATED conditional, so it '
      + 'covers only the resources on that list and every other gate in this '
      + 'file is uncovered -- which was true, silently, until 2026-09-26');
  });

test('COVERAGE: it precedes EVERY verifySessionToken gate in the file, not just '
  + 'the first', () => {
    // A pre-gate that sat above the first gate and below the second would pass
    // the arm above and still leave 131 gates open. Counted, not sampled.
    const recheck = CODE.indexOf('await credentialStillActive(');
    const gates = [];
    const re = /verifySessionToken\(/g;
    let m;
    while ((m = re.exec(CODE)) !== null) gates.push(m.index);
    assert.ok(gates.length > 50,
      'only ' + gates.length + ' verifySessionToken gates found -- the gate '
      + 'spelling changed and this arm is measuring almost nothing');
    // The pre-gate's own verification is the one gate that legitimately precedes
    // the re-check; every other must follow it.
    const before = gates.filter((g) => g < recheck);
    assert.strictEqual(before.length, 1,
      before.length + ' verifySessionToken gates run BEFORE the re-check. Exactly '
      + 'one may -- the pre-gate\'s own. The others are uncovered.');
  });

test('COVERAGE: there is exactly ONE re-check call site, so the three-state '
  + 'handling cannot drift between copies', () => {
    const n = (CODE.match(/await\s+credentialStillActive\(/g) || []).length;
    assert.strictEqual(n, 1,
      n + ' call sites. Two would also mean two employee-row reads on every '
      + 'request to a SD_SESSION_GATED resource.');
  });

test('the pre-gate does NOT authenticate -- an absent or unverifiable token is '
  + 'not refused there', () => {
    // If the pre-gate refused a missing or bad token it would break every
    // licence-only route in this file, which is most of them. The refusal must
    // stay with the per-branch gates. Asserted structurally: the re-check is
    // reached only inside BOTH guards, and neither guard has an else-refuse.
    const i = CODE.indexOf('const preToken = tokenFromRequest(req);');
    assert.ok(i > 0, 'the pre-gate token read moved');
    const block = CODE.slice(i, CODE.indexOf('if (SD_SESSION_GATED[resource]'));
    assert.ok(/if\s*\(preToken\)\s*\{/.test(block),
      'the pre-gate does not guard on a token being present');
    assert.ok(/if\s*\(preSession\)\s*\{/.test(block),
      'the pre-gate does not guard on the token verifying');
    assert.ok(!/preToken\)[\s\S]{0,80}res\.status\(4/.test(block),
      'a missing token is refused by the pre-gate, which would break every '
      + 'licence-only resource in this file');
    assert.ok(!/!preSession[\s\S]{0,120}res\.status\(4/.test(block),
      'an unverifiable token is refused by the pre-gate rather than by the '
      + 'branch that actually requires a session');
  });

test('a DEACTIVATED credential is refused with 403 CREDENTIAL_INACTIVE', () => {
  const m = CODE.match(/CREDENTIAL_INACTIVE[\s\S]{0,400}?res\.status\((\d+)\)/)
    || CODE.match(/res\.status\((\d+)\)[\s\S]{0,400}?CREDENTIAL_INACTIVE/);
  assert.ok(m, 'no refusal path mentions CREDENTIAL_INACTIVE');
  assert.strictEqual(m[1], '403', 'refused with ' + m[1] + ' rather than 403');
});

test('CONTROL: NO_ACTIVE_CHECK does NOT refuse -- a transport failure is not a '
  + 'deactivation, and refusing everybody when the database blinks is a worse '
  + 'failure than the one being closed', () => {
    // RE-ANCHORED 2026-09-26. This read `indexOf(...) < 400` -- a character
    // DISTANCE from the call site -- and went red when the pre-gate grew the
    // app-scope derivation between the two. A magic window measures proximity,
    // not the property, and it fails on ordinary code exactly as the 4200-char
    // window in tests/roofing_claim_gate_single_source.js did on a comment.
    //
    // THE PROPERTY IS "no could-not-tell reaches a refusal". Asserted as that:
    // every 403 in the pre-gate block is reachable only through a
    // CREDENTIAL_INACTIVE condition, and NO_ACTIVE_CHECK never appears in a
    // refusal path at all.
    const start = CODE.indexOf('const preToken = tokenFromRequest(req);');
    assert.ok(start > 0, 'the pre-gate moved');
    const block = CODE.slice(start, CODE.indexOf('if (SD_SESSION_GATED[resource]', start));
    assert.ok(block.length > 200, 'the pre-gate block came out too short to assert over');
    const refusals = (block.match(/res\.status\(4\d\d\)/g) || []).length;
    assert.strictEqual(refusals, 1,
      refusals + ' refusal(s) in the pre-gate. One is the CREDENTIAL_INACTIVE '
      + 'path; a second would be a could-not-tell refusing a caller.');
    assert.ok(/CREDENTIAL_INACTIVE[\s\S]*res\.status\(403\)/.test(block),
      'the single refusal is not conditioned on CREDENTIAL_INACTIVE, so any '
      + 'could-not-tell would refuse the caller');
    // NO_ACTIVE_CHECK must reach only a log. It is named nowhere near a status.
    assert.ok(!/NO_ACTIVE_CHECK[\s\S]{0,200}res\.status\(/.test(block),
      'NO_ACTIVE_CHECK leads to a refusal, which would lock everybody out of an '
      + 'app whose employee table is not provisioned');
  });

test('a MISSING row on an UNSCOPED resource is not called a deactivation', () => {
  // THE FIRST DRAFT OF THE PRE-GATE GOT THIS WRONG AND THREE ARMS OF
  // api/sd-data-law-phase2-session.test.js said so. Running above the
  // per-resource app scoping means the pre-gate sees valid tokens belonging to
  // ANOTHER app on this licence, which have no row in their own app's table --
  // and answering "this credential has been deactivated, sign in again" to
  // somebody whose credential is fine sends them to reset a password that was
  // never the problem. An explicit active:false is still refused unconditionally.
  const start = CODE.indexOf('const preToken = tokenFromRequest(req);');
  const block = CODE.slice(start, CODE.indexOf('if (SD_SESSION_GATED[resource]', start));
  assert.ok(/reason === 'inactive'/.test(block),
    'the pre-gate does not distinguish an explicit active:false from an empty '
    + 'result, so a cross-app token is reported as a deactivated credential');
  assert.ok(/preScoped/.test(block),
    'nothing conditions the missing-row refusal on the resource\'s expected app '
    + 'matching the token\'s');
  // AND IT MUST NOT BE WEAKER THAN THE BRANCH GATE IT SITS ABOVE: the expected
  // app is derived with the same `|| 'stonedesk'` default, not a second guess.
  assert.ok(/SD_GATE_APP\[resource\] \|\| 'stonedesk'/.test(block),
    'the pre-gate derives the expected app differently from the branch gate, '
    + 'which is how the `memory` defect happened in the first place');
});

// ── THE PRE-GATE BLOCK, LOCATED ONCE ───────────────────────────────────────
// RE-ANCHORED 2026-09-28. The two arms below read
// `CODE.slice(indexOf('await credentialStillActive('), +1200)` -- a character
// DISTANCE from the call site, the THIRD in this file after the 400-char one
// re-anchored on 2026-09-26 and the 4200-char one in
// tests/roofing_claim_gate_single_source.js. The pre-gate has since grown the
// app-scope derivation, the hard-refusal condition and the no-row branch, and
// 1200 characters now stop PART-WAY THROUGH THE FIRST console.warn. The
// COULD-NOT-RUN log both arms are named for sits entirely OUTSIDE the window.
//
// NEITHER ARM WENT RED. They were being satisfied by the no-row log instead:
// `/NO_ACTIVE_CHECK|preActive\.code/` matched `preActive.code ===
// 'CREDENTIAL_INACTIVE'` in the REFUSAL CONDITION rather than in any log at
// all, and `/try\s*\{[\s\S]{0,400}console\.warn/` matched the no-row log's
// try. tests/active_credential_gate_probe.py arms 5 and 6 were both SILENT --
// deleting the could-not-run log, and stripping its try/catch, each left this
// suite green. A magic window measures proximity, not the property.
//
// Anchored instead on the block's real ends, which the arms above already use.
function preGateBlock() {
  const start = CODE.indexOf('const preToken = tokenFromRequest(req);');
  assert.ok(start > 0, 'the pre-gate token read moved');
  const end = CODE.indexOf('if (SD_SESSION_GATED[resource]', start);
  assert.ok(end > start, 'the SD_SESSION_GATED block moved or no longer follows '
    + 'the pre-gate, so this block has no honest end');
  const block = CODE.slice(start, end);
  assert.ok(block.length > 200,
    'the pre-gate block came out too short to assert over');
  return block;
}

test('...and the COULD-NOT-RUN state is LOGGED, so a run of them is visible '
  + 'rather than silent', () => {
    const block = preGateBlock();
    // THE PROPERTY IS ABOUT ONE BRANCH, so it is asserted over that branch and
    // not over the whole pre-gate: the no-row branch beside it also logs, and
    // either log satisfying both arms is exactly the hole being closed here.
    const eb = block.indexOf('} else if (!preActive.ok) {');
    assert.ok(eb > 0,
      'the pre-gate has no separate branch for a could-not-tell answer, so '
      + 'NO_ACTIVE_CHECK is folded into one of the other two states');
    const couldNotRun = block.slice(eb);
    assert.ok(/console\.warn/.test(couldNotRun),
      'a re-check that did not run passes in silence');
    assert.ok(/NO_ACTIVE_CHECK|preActive\.code|stillActive\.code/.test(couldNotRun),
      'the log does not name which state it was');
    // ONCE PER REQUEST, NOT ONCE PER GATED RESOURCE -- decided explicitly when
    // the pre-gate was built, so the log carries the resource and action to keep
    // a run of them attributable now that it fires above the dispatch.
    assert.ok(/resource\s*\+\s*'\/'\s*\+\s*action/.test(couldNotRun),
      'the could-not-run log does not say which resource/action it was for, so a '
      + 'run of them cannot be attributed from the logs');
  });

test('CONTROL: the logging cannot itself refuse a request -- EVERY log in the '
  + 'pre-gate is guarded, counted rather than sampled', () => {
    // COUNTED IS THE WHOLE POINT. `/try\s*\{[\s\S]{0,400}console\.warn/` is a
    // single-match test: one guarded log satisfied it while a second sat
    // unguarded, which is precisely what arm 6 plants.
    const block = preGateBlock();
    const warns = (block.match(/console\.warn/g) || []).length;
    assert.ok(warns >= 2,
      'only ' + warns + ' log(s) in the pre-gate. There are two distinct '
      + 'outcomes that must be logged rather than dropped -- a no-row on an '
      + 'unscoped resource, and a could-not-run -- so one of them has gone '
      + 'silent or this arm is measuring less than it claims.');
    // `[^}]` between the two, so a removed `try` cannot be covered by the
    // PREVIOUS try: the `} catch` that closes it lies in between.
    const guarded = (block.match(/try\s*\{[^}]{0,200}console\.warn/g) || []).length;
    assert.strictEqual(guarded, warns,
      guarded + ' of ' + warns + ' logs in the pre-gate are inside a try. An '
      + 'unguarded console.warn throws out of the gate and refuses a caller for '
      + 'a reason that has nothing to do with them.');
  });

test('CONTROL: this file would notice the gate being deleted -- the anchors it '
  + 'reads are the real ones', () => {
    // A structural test whose anchors no longer exist passes vacuously. Both
    // strings are asserted present rather than assumed by the arms above.
    assert.ok(CODE.indexOf('const gateSession = verifySessionToken(') > 0);
    assert.ok(CODE.indexOf('await credentialStillActive(') > 0);
  });

console.log(passed + ' passed'
  + (process.exitCode ? ', with failures above' : ''));
