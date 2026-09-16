// api/_lib/auth.test.js
// REQUIREMENT: a session token cannot be forged or replayed past expiry, and a PIN is
//   verified against a one-way hash rather than compared, for every app that
//   shares this module
//
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
const { signSessionToken, verifySessionToken, hashPin, verifyPin,
        credentialStillActive, AUTH_TABLE_BY_APP, ROLES_BY_APP } = require('./auth');

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

// ════════════════════════════════════════════════════════════════════════════
// credentialStillActive -- A TOKEN IS A CLAIM ABOUT THE PAST
//
// Added 2026-09-16. verifySessionToken proves a token was minted by us, for
// this licence and this app, and has not expired. It proves NOTHING about now.
// A deactivated employee kept read and write access to every gated resource in
// api/sd-data.js for the remaining life of a 12h token -- and deactivation is
// the one control an owner has for somebody who has just left.
//
// These arms run ASYNC, so they use their own runner rather than the sync
// `test()` above; a sync runner silently passes an async body that throws.
// ════════════════════════════════════════════════════════════════════════════
const ASYNC = [];
function atest(name, fn) { ASYNC.push([name, fn]); }

// A fake PostgREST. `rows` is what the table answers with; `mode` makes it
// misbehave in the two ways that must NOT read as a deactivation.
function restStub(rows, mode) {
  const calls = [];
  const rest = (path) => { calls.push(path); return 'https://x/rest/v1/' + path; };
  const fetchImpl = function () {
    if (mode === 'throw') return Promise.reject(new Error('NetworkError'));
    if (mode === 'notok') return Promise.resolve({ ok: false, json: () => Promise.resolve({}) });
    return Promise.resolve({ ok: true, json: () => Promise.resolve(rows) });
  };
  return { rest, calls, fetchImpl };
}

async function withFetch(impl, fn) {
  const real = global.fetch;
  global.fetch = impl;
  try { return await fn(); } finally { global.fetch = real; }
}

const SESSION = { employee_id: 'E1', role: 'admin', app: 'stonedesk' };

atest('an ACTIVE credential passes', async () => {
  const s = restStub([{ active: true }]);
  const r = await withFetch(s.fetchImpl,
    () => credentialStillActive(SESSION, 'LIC', s.rest, {}));
  assert.deepStrictEqual(r, { ok: true });
  assert.ok(/sd_employee_auth\?/.test(s.calls[0]), s.calls[0]);
  assert.ok(/employee_id=eq\.E1/.test(s.calls[0]), s.calls[0]);
});

atest('THE SABOTAGE ARM: a token minted while active is REFUSED once the '
  + 'credential is deactivated mid-life', async () => {
  // One real token, verified twice against the same licence and app. Nothing
  // about the token changes; only the row behind it does.
  const token = signSessionToken({ employee_id: 'E1', role: 'admin',
                                   license_hash: 'LIC', app: 'stonedesk' });
  const before = verifySessionToken(token, 'LIC', 'stonedesk');
  assert.ok(before && before.employee_id === 'E1', 'the token did not verify');

  const live = restStub([{ active: true }]);
  const ok1 = await withFetch(live.fetchImpl,
    () => credentialStillActive(before, 'LIC', live.rest, {}));
  assert.strictEqual(ok1.ok, true, 'an active credential was refused');

  // ── DEACTIVATED. The token is byte-identical and still verifies. ──
  const dead = restStub([{ active: false }]);
  const after = verifySessionToken(token, 'LIC', 'stonedesk');
  assert.ok(after, 'the token stopped verifying, which is NOT what this tests');
  const ok2 = await withFetch(dead.fetchImpl,
    () => credentialStillActive(after, 'LIC', dead.rest, {}));
  assert.strictEqual(ok2.ok, false, 'a DEACTIVATED credential still passed');
  assert.strictEqual(ok2.code, 'CREDENTIAL_INACTIVE', JSON.stringify(ok2));
});

atest('a credential whose row is GONE is refused too -- deleted is not active',
  async () => {
    const s = restStub([]);
    const r = await withFetch(s.fetchImpl,
      () => credentialStillActive(SESSION, 'LIC', s.rest, {}));
    assert.strictEqual(r.code, 'CREDENTIAL_INACTIVE', JSON.stringify(r));
  });

atest('CONTROL: a TRANSPORT FAILURE is NO_ACTIVE_CHECK, never a deactivation. '
  + 'Answering "inactive" would lock every user out whenever the database '
  + 'blinked', async () => {
  const s = restStub(null, 'throw');
  const r = await withFetch(s.fetchImpl,
    () => credentialStillActive(SESSION, 'LIC', s.rest, {}));
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.code, 'NO_ACTIVE_CHECK', JSON.stringify(r));
});

atest('CONTROL: ...and a non-OK response is NO_ACTIVE_CHECK as well, not an '
  + 'empty row list read as "no active credential"', async () => {
  const s = restStub(null, 'notok');
  const r = await withFetch(s.fetchImpl,
    () => credentialStillActive(SESSION, 'LIC', s.rest, {}));
  assert.strictEqual(r.code, 'NO_ACTIVE_CHECK', JSON.stringify(r));
});

atest('CONTROL: NO_ACTIVE_CHECK is NOT ok. The three states are distinct and a '
  + 'caller folding could-not-tell into either is the defect PR 1.11 names',
  async () => {
    const s = restStub(null, 'throw');
    const r = await withFetch(s.fetchImpl,
      () => credentialStillActive(SESSION, 'LIC', s.rest, {}));
    assert.strictEqual(r.ok, false);
    assert.notStrictEqual(r.code, 'CREDENTIAL_INACTIVE');
  });

atest('an app with no employee table is NO_ACTIVE_CHECK -- stonedesk_sub '
  + 'authenticates on sub_id and is deliberately absent from the map',
  async () => {
    const s = restStub([{ active: true }]);
    const r = await withFetch(s.fetchImpl, () => credentialStillActive(
      { employee_id: 'S1', role: 'sub', app: 'stonedesk_sub' }, 'LIC', s.rest, {}));
    assert.strictEqual(r.code, 'NO_ACTIVE_CHECK', JSON.stringify(r));
    assert.strictEqual(s.calls.length, 0, 'it queried a table it has no name for');
  });

atest('no session at all is FORBIDDEN and asks nothing', async () => {
  const s = restStub([{ active: true }]);
  const r = await withFetch(s.fetchImpl,
    () => credentialStillActive(null, 'LIC', s.rest, {}));
  assert.strictEqual(r.code, 'FORBIDDEN');
  assert.strictEqual(s.calls.length, 0);
});

atest('THE MAP IS COMPLETE: every app with roles has a table, except the one '
  + 'deliberately excluded', async () => {
  const missing = Object.keys(ROLES_BY_APP)
    .filter((a) => a !== 'stonedesk_sub' && !AUTH_TABLE_BY_APP[a]);
  assert.deepStrictEqual(missing, [],
    'these apps would silently get NO_ACTIVE_CHECK forever: ' + missing.join(', '));
});

atest('CONTROL: and the map names no app that has no roles -- a stale entry '
  + 'would be dead weight nothing could reach', async () => {
  const extra = Object.keys(AUTH_TABLE_BY_APP).filter((a) => !ROLES_BY_APP[a]);
  assert.deepStrictEqual(extra, [], extra.join(', '));
});

atest('CONTROL: every table name in the map is one a real endpoint uses, so '
  + 'the declaration cannot drift from the schema it names', async () => {
  const fs = require('fs');
  const path = require('path');
  const dir = path.join(__dirname, '..');
  const src = fs.readdirSync(dir).filter((f) => /-auth\.js$/.test(f))
    .map((f) => fs.readFileSync(path.join(dir, f), 'utf8')).join('\n');
  const unused = Object.values(AUTH_TABLE_BY_APP).filter((t) => src.indexOf(t) === -1);
  assert.deepStrictEqual(unused, [],
    'named here and used by no auth endpoint: ' + unused.join(', '));
});

(async function runAsync() {
  for (const [name, fn] of ASYNC) {
    try {
      await fn();
      passed++;
      console.log('  ok - ' + name);
    } catch (err) {
      console.error('  FAIL - ' + name);
      console.error('    ' + err.message);
      process.exitCode = 1;
    }
  }
  console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
})();
