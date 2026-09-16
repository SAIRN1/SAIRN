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

test('THE ORDER: the re-check runs AFTER the token is verified and BEFORE any '
  + 'resource handler', () => {
    const verify = CODE.indexOf('const gateSession = verifySessionToken(');
    const recheck = CODE.indexOf('await credentialStillActive(');
    assert.ok(verify > 0, 'the session gate moved');
    assert.ok(recheck > verify,
      'the re-check runs before the token is verified, so it would query for a '
      + 'session that may not exist');
    const firstHandler = CODE.indexOf("if (resource === 'profile'");
    assert.ok(firstHandler > recheck,
      'a resource handler runs before the re-check, so that resource is still '
      + 'reachable with a deactivated credential');
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
    const block = CODE.slice(CODE.indexOf('await credentialStillActive('));
    const refuse = block.indexOf("code === 'CREDENTIAL_INACTIVE'");
    assert.ok(refuse > -1 && refuse < 400,
      'the refusal is not conditioned on CREDENTIAL_INACTIVE specifically, so '
      + 'any could-not-tell would refuse the caller');
  });

test('...and it is LOGGED, so a run of them is visible rather than silent',
  () => {
    const block = CODE.slice(CODE.indexOf('await credentialStillActive('),
                             CODE.indexOf('await credentialStillActive(') + 1200);
    assert.ok(/console\.warn/.test(block),
      'a re-check that did not run passes in silence');
    assert.ok(/NO_ACTIVE_CHECK|stillActive\.code/.test(block),
      'the log does not name which state it was');
  });

test('CONTROL: the logging cannot itself refuse a request', () => {
  const block = CODE.slice(CODE.indexOf('await credentialStillActive('),
                           CODE.indexOf('await credentialStillActive(') + 1200);
  assert.ok(/try\s*\{[\s\S]{0,400}console\.warn/.test(block),
    'console.warn is not guarded, so a logging failure would throw out of the '
    + 'gate and refuse a caller for the wrong reason');
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
