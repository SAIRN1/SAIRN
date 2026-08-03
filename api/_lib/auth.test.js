// api/_lib/auth.test.js
// ---------------------------------------------------------------------------
// Plain node:assert tests — no test framework, matching api/'s existing
// zero-npm-dependency convention (see api/_lib/auth.js's own header).
// Run: SD_AUTH_SECRET=test-secret node api/_lib/auth.test.js
//
// WHY THIS EXISTS: TDD commitment made 2026-08-03, after api/sd-auth.js's
// setup action and api/sd-data.js's employees read gate both shipped
// calling verifySessionToken() WITHOUT expectedApp — meaning a valid
// SAIRNbiz 'owner' token could have silently passed StoneDesk-only checks,
// since 'owner' is a valid role in both apps' vocabularies. That bug was
// only caught by manual self-review before push, not by anything
// automated. Going forward: any new auth/permission code gets a failing
// test written first, confirming a wrong-app credential is rejected,
// before the implementation. This file is that test for the code that
// already shipped — the Semgrep rule
// (.semgrep/verify-session-token-app-scope.yml) catches the missing-
// argument pattern at the source level; this catches the same bug class
// at the behavior level, so a future refactor that keeps the argument but
// breaks the actual cross-app check logic still gets caught.
// ---------------------------------------------------------------------------

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'test-secret-do-not-use-in-prod';

const assert = require('assert');
const { signSessionToken, verifySessionToken, hashPin, verifyPin } = require('./auth');

const LIC_A = 'license-hash-shop-a';
const LIC_B = 'license-hash-shop-b';

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

console.log('api/_lib/auth.js');

// ── Core cross-app rejection (the exact bug class found 2026-08-03) ───────
test('a stonedesk token verifies against expectedApp:stonedesk', () => {
  const token = signSessionToken({ employee_id: 'e1', role: 'owner', license_hash: LIC_A, app: 'stonedesk' });
  const session = verifySessionToken(token, LIC_A, 'stonedesk');
  assert.ok(session, 'expected a valid session');
  assert.strictEqual(session.role, 'owner');
  assert.strictEqual(session.app, 'stonedesk');
});

test('a stonedesk token is REJECTED against expectedApp:sairnbiz', () => {
  const token = signSessionToken({ employee_id: 'e1', role: 'owner', license_hash: LIC_A, app: 'stonedesk' });
  const session = verifySessionToken(token, LIC_A, 'sairnbiz');
  assert.strictEqual(session, null, 'a StoneDesk token must never verify as a SAIRNbiz token');
});

test('a sairnbiz owner token is REJECTED against expectedApp:stonedesk (the literal shipped bug)', () => {
  // 'owner' is a valid role in BOTH apps' vocabularies -- this is exactly
  // the scenario that would have silently passed before expectedApp was
  // wired through every call site.
  const token = signSessionToken({ employee_id: 'e2', role: 'owner', license_hash: LIC_A, app: 'sairnbiz' });
  const session = verifySessionToken(token, LIC_A, 'stonedesk');
  assert.strictEqual(session, null, 'a SAIRNbiz owner token must never pass a StoneDesk-only gate');
});

test('a token with no expectedApp check still returns its own app claim', () => {
  const token = signSessionToken({ employee_id: 'e3', role: 'hr', license_hash: LIC_A, app: 'sairnbiz' });
  const session = verifySessionToken(token, LIC_A, null);
  assert.ok(session);
  assert.strictEqual(session.app, 'sairnbiz');
});

// ── License/tenant scoping ─────────────────────────────────────────────────
test('a token minted for one license is REJECTED against a different license', () => {
  const token = signSessionToken({ employee_id: 'e1', role: 'owner', license_hash: LIC_A, app: 'stonedesk' });
  const session = verifySessionToken(token, LIC_B, 'stonedesk');
  assert.strictEqual(session, null, 'a token must not verify against a different shop');
});

// ── Role vocabulary enforcement ────────────────────────────────────────────
test('signing with a role not in the app\'s vocabulary throws', () => {
  assert.throws(() => {
    signSessionToken({ employee_id: 'e1', role: 'sales', license_hash: LIC_A, app: 'sairnbiz' }); // 'sales' is StoneDesk-only
  });
});

test('signing with an unknown app throws', () => {
  assert.throws(() => {
    signSessionToken({ employee_id: 'e1', role: 'owner', license_hash: LIC_A, app: 'sairnhr' });
  });
});

// ── Tampering / expiry ──────────────────────────────────────────────────────
test('a tampered payload is REJECTED', () => {
  const token = signSessionToken({ employee_id: 'e1', role: 'owner', license_hash: LIC_A, app: 'stonedesk' });
  const [payloadB64, sigB64] = token.split('.');
  const tampered = payloadB64.slice(0, -2) + 'xx' + '.' + sigB64;
  assert.strictEqual(verifySessionToken(tampered, LIC_A, 'stonedesk'), null);
});

test('an expired token is REJECTED', () => {
  // Sign, then hand-craft an already-expired copy using the real secret so
  // only exp is being exercised, not the signature path.
  const crypto = require('crypto');
  const payload = { app: 'stonedesk', employee_id: 'e1', role: 'owner', license_hash: LIC_A, iat: Date.now() - 1000, exp: Date.now() - 500 };
  const b64 = (s) => Buffer.from(s).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const payloadB64 = b64(JSON.stringify(payload));
  const sig = crypto.createHmac('sha256', process.env.SD_AUTH_SECRET).update(payloadB64).digest();
  const token = payloadB64 + '.' + b64(sig);
  assert.strictEqual(verifySessionToken(token, LIC_A, 'stonedesk'), null);
});

// ── PIN hashing/verification (scrypt, timing-safe) ─────────────────────────
test('a correct PIN verifies against its own hash', () => {
  const { pin_hash, pin_salt } = hashPin('123456');
  assert.strictEqual(verifyPin('123456', pin_hash, pin_salt), true);
});

test('a wrong PIN is rejected', () => {
  const { pin_hash, pin_salt } = hashPin('123456');
  assert.strictEqual(verifyPin('654321', pin_hash, pin_salt), false);
});

test('verifyPin with no stored hash (unknown employee_id case) returns false, not throw', () => {
  assert.strictEqual(verifyPin('123456', null, null), false);
});

console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
