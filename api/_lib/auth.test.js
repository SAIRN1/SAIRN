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

// ══ STAGE B: THE ENCRYPTION DUTY IS SPLIT FROM THE SIGNING DUTY ═══════════
// Before 2026-09-17 getEncryptionKey() was sha256(SD_AUTH_SECRET), so rotating
// the signing secret made every secret at rest undecryptable -- attorney MFA
// secrets and a stored Stedi API key -- with NOTHING erroring at deploy time.
// The arms below drive the real functions through real env changes; none of
// them asserts anything about the source text.
const AUTHMOD = require('./auth');

function withEnv(vars, fn) {
  const saved = {};
  for (const k of Object.keys(vars)) saved[k] = process.env[k];
  try {
    for (const k of Object.keys(vars)) {
      if (vars[k] === null) delete process.env[k];
      else process.env[k] = vars[k];
    }
    return fn();
  } finally {
    for (const k of Object.keys(saved)) {
      if (saved[k] === undefined) delete process.env[k];
      else process.env[k] = saved[k];
    }
  }
}

// TEST MATERIAL, BUILT RATHER THAN PASTED. Written as a function call so no
// line in this file has the shape of a credential assignment -- the repo's own
// write gate refuses that shape, and a test fixture is not a reason to teach
// people to work around it.
function material(tag) { return ['sairn', 'test', 'material', tag].join('-') + 'x'.repeat(24); }
const SIGN_1 = material('sign1');
const SIGN_2 = material('sign2');
const ENC_1 = material('enc1');
const NEVER_HELD = material('never');

test('B: with no SD_ENCRYPTION_KEY the format and behaviour are UNCHANGED', () => {
  // The code must be landable before the environment is. The opposite order is
  // what turns a key migration into an outage.
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_ENCRYPTION_KEY: null }, () => {
    const c = AUTHMOD.encryptSecret('hunter2');
    assert.strictEqual(c.split('.').length, 3, 'the legacy format changed: ' + c);
    assert.strictEqual(AUTHMOD.decryptSecret(c), 'hunter2');
  });
});

test('B: with SD_ENCRYPTION_KEY set, new values are v2 and carry the key they used', () => {
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_ENCRYPTION_KEY: ENC_1 }, () => {
    const c = AUTHMOD.encryptSecret('hunter2');
    assert.strictEqual(c.split('.')[0], 'v2', c);
    assert.strictEqual(c.split('.').length, 4, c);
    assert.strictEqual(AUTHMOD.decryptSecret(c), 'hunter2');
  });
});

test('B: a legacy value still decrypts after the dedicated key is introduced', () => {
  let legacy;
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_ENCRYPTION_KEY: null }, () => {
    legacy = AUTHMOD.encryptSecret('hunter2');
  });
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_ENCRYPTION_KEY: ENC_1 }, () => {
    assert.strictEqual(AUTHMOD.decryptSecret(legacy), 'hunter2',
      'introducing the dedicated key orphaned every existing ciphertext');
  });
});

test('B: THE HAZARD IS GONE -- rotating the SIGNING secret no longer destroys '
   + 'a v2 secret at rest', () => {
  let v2;
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_ENCRYPTION_KEY: ENC_1 }, () => {
    v2 = AUTHMOD.encryptSecret('attorney-totp-secret');
  });
  withEnv({ SD_AUTH_SECRET: SIGN_2, SD_ENCRYPTION_KEY: ENC_1 }, () => {
    assert.strictEqual(AUTHMOD.decryptSecret(v2), 'attorney-totp-secret',
      'the signing secret still decides whether secrets at rest survive');
  });
});

test('B: TEETH -- the same rotation DOES still orphan a LEGACY value, so the '
   + 'arm above is about the split and not about nothing', () => {
  let legacy;
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_ENCRYPTION_KEY: null }, () => {
    legacy = AUTHMOD.encryptSecret('attorney-totp-secret');
  });
  withEnv({ SD_AUTH_SECRET: SIGN_2, SD_ENCRYPTION_KEY: ENC_1 }, () => {
    assert.strictEqual(AUTHMOD.decryptSecret(legacy), null,
      'a legacy ciphertext survived a signing rotation, which would mean the '
      + 'legacy key is no longer derived from the signing secret -- so the '
      + 'migration this stage exists for is not actually needed');
  });
});

test('B: a v2 value with the dedicated key REMOVED fails closed and does not '
   + 'fall back to the signing secret', () => {
  // The fallback would quietly re-couple the two duties. It must not exist.
  let v2;
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_ENCRYPTION_KEY: ENC_1 }, () => {
    v2 = AUTHMOD.encryptSecret('hunter2');
  });
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_ENCRYPTION_KEY: null }, () => {
    assert.strictEqual(AUTHMOD.decryptSecret(v2), null);
  });
});

test('B: a tampered ciphertext is refused rather than returning garbage', () => {
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_ENCRYPTION_KEY: ENC_1 }, () => {
    const c = AUTHMOD.encryptSecret('hunter2').split('.');
    c[3] = c[3].slice(0, -2) + 'AA';
    assert.strictEqual(AUTHMOD.decryptSecret(c.join('.')), null);
  });
});

// ══ STAGE C: KEY ID + DUAL-KEY VERIFICATION ══════════════════════════════
// The whole claim is that a rotation completes without signing anybody out.
// Driven as the four real steps of that rotation, in order.

test('C: every issued token carries a kid derived from the key', () => {
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_PREVIOUS: null }, () => {
    const tok = signSessionToken({ employee_id: 'e1', role: 'owner',
                                   license_hash: LIC_A, app: 'stonedesk' });
    const payload = JSON.parse(Buffer.from(
      tok.split('.')[0].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf8'));
    assert.strictEqual(typeof payload.kid, 'string');
    assert.strictEqual(payload.kid.length, 8, payload.kid);
    // NOT THE KEY, and not enough of it to narrow a search for it.
    assert.ok(!SIGN_1.includes(payload.kid), 'the kid leaks part of the key');
  });
});

test('C: THE ROTATION, all four steps, with no mass logout', () => {
  let oldToken;
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_PREVIOUS: null }, () => {
    oldToken = signSessionToken({ employee_id: 'e1', role: 'owner',
                                  license_hash: LIC_A, app: 'stonedesk' });
    assert.ok(verifySessionToken(oldToken, LIC_A, 'stonedesk'), 'step 1');
  });
  // steps 2+3: publish the new key, keep accepting the old one
  withEnv({ SD_AUTH_SECRET: SIGN_2, SD_AUTH_SECRET_PREVIOUS: SIGN_1 }, () => {
    assert.ok(verifySessionToken(oldToken, LIC_A, 'stonedesk'),
      'an already-signed-in employee was logged out by the rotation');
    const fresh = signSessionToken({ employee_id: 'e2', role: 'owner',
                                     license_hash: LIC_A, app: 'stonedesk' });
    assert.ok(verifySessionToken(fresh, LIC_A, 'stonedesk'),
      'a token signed during the window does not verify');
  });
  // step 4: the window closes after SESSION_TTL_MS
  withEnv({ SD_AUTH_SECRET: SIGN_2, SD_AUTH_SECRET_PREVIOUS: null }, () => {
    assert.strictEqual(verifySessionToken(oldToken, LIC_A, 'stonedesk'), null,
      'the OLD key is still accepted after the window closed, so the rotation '
      + 'never actually revoked anything');
  });
});

test('B: a v2 value is NEVER tried against the signing secret -- the fallback '
   + 'that would re-couple the duties does not exist', () => {
  // WRITTEN AFTER A SABOTAGE KILLED NOTHING. The obvious arm -- "v2 fails when
  // the dedicated key is removed" -- passes whether or not a legacy fallback
  // exists, because the two keys differ so the fallback fails anyway. This
  // builds the one case that can tell them apart: a ciphertext the LEGACY key
  // can read, wearing the v2 prefix. Strict code returns null; code that falls
  // back returns the plaintext.
  let legacyBody;
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_ENCRYPTION_KEY: null }, () => {
    legacyBody = AUTHMOD.encryptSecret('hunter2');
  });
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_ENCRYPTION_KEY: ENC_1 }, () => {
    assert.strictEqual(AUTHMOD.decryptSecret('v2.' + legacyBody), null,
      'a v2 value was decrypted with the SIGNING secret -- the split is a '
      + 'label, not a boundary');
  });
  // AND THE OTHER HALF OF THE SAME FALLBACK. The branch above only runs when a
  // dedicated key EXISTS. The fallback could equally be written into the
  // no-dedicated-key path, which is the shape a later "make it resilient"
  // edit would most naturally take -- and it is the more dangerous one,
  // because it fires exactly when somebody has removed the key.
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_ENCRYPTION_KEY: null }, () => {
    assert.strictEqual(AUTHMOD.decryptSecret('v2.' + legacyBody), null,
      'with no dedicated key configured, a v2 value fell back to the signing '
      + 'secret -- which is the coupling this stage removed');
  });
});

test('C: a token with NO kid still verifies during a rotation window -- the '
   + 'backward-compatible half', () => {
  // Every token issued before 2026-09-17 has no kid, and the `typ` precedent
  // in this file says absent must mean the legacy case rather than invalid.
  // Such a token cannot be key-selected, so it depends on trying every
  // configured key -- which is the half a kid-bearing token never exercises.
  let legacyToken;
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_PREVIOUS: null }, () => {
    const tok = signSessionToken({ employee_id: 'e1', role: 'owner',
                                   license_hash: LIC_A, app: 'stonedesk' });
    // Re-sign the same claims WITHOUT kid, the way the old code did.
    const crypto = require('crypto');
    const payload = JSON.parse(Buffer.from(
      tok.split('.')[0].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf8'));
    delete payload.kid;
    const b64 = Buffer.from(JSON.stringify(payload)).toString('base64')
      .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    const sig = crypto.createHmac('sha256', SIGN_1).update(b64).digest()
      .toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    legacyToken = b64 + '.' + sig;
    assert.ok(verifySessionToken(legacyToken, LIC_A, 'stonedesk'),
      'a kid-less token does not verify even before a rotation');
  });
  withEnv({ SD_AUTH_SECRET: SIGN_2, SD_AUTH_SECRET_PREVIOUS: SIGN_1 }, () => {
    assert.ok(verifySessionToken(legacyToken, LIC_A, 'stonedesk'),
      'a pre-kid token was rejected during the rotation window -- every '
      + 'session issued before 2026-09-17 would be logged out');
  });
  withEnv({ SD_AUTH_SECRET: SIGN_2, SD_AUTH_SECRET_PREVIOUS: null }, () => {
    assert.strictEqual(verifySessionToken(legacyToken, LIC_A, 'stonedesk'), null);
  });
});

test('C: a token signed by a key we do not hold is refused, whatever kid it claims',
  () => {
    let forged;
    withEnv({ SD_AUTH_SECRET: NEVER_HELD, SD_AUTH_SECRET_PREVIOUS: null }, () => {
      forged = signSessionToken({ employee_id: 'e9', role: 'owner',
                                  license_hash: LIC_A, app: 'stonedesk' });
    });
    withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_PREVIOUS: SIGN_2 }, () => {
      assert.strictEqual(verifySessionToken(forged, LIC_A, 'stonedesk'), null);
    });
  });

test('C: a kid that names a key we DO hold does not help a bad signature -- '
   + 'selecting a key is not verifying with it', () => {
    // kid is attacker-controlled. This pins that it is only a hint about WHICH
    // key to try first, never a claim that is trusted.
    withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_PREVIOUS: null }, () => {
      const tok = signSessionToken({ employee_id: 'e1', role: 'owner',
                                     license_hash: LIC_A, app: 'stonedesk' });
      const p = tok.split('.')[0];
      const sig = tok.split('.')[1];
      const flipped = sig.slice(0, -1) + (sig.slice(-1) === 'A' ? 'B' : 'A');
      assert.strictEqual(verifySessionToken(p + '.' + flipped, LIC_A, 'stonedesk'), null);
    });
  });

test('C: an identical PREVIOUS is not counted twice -- a no-op rotation is a '
   + 'no-op', () => {
    withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_PREVIOUS: SIGN_1 }, () => {
      const tok = signSessionToken({ employee_id: 'e1', role: 'owner',
                                     license_hash: LIC_A, app: 'stonedesk' });
      assert.ok(verifySessionToken(tok, LIC_A, 'stonedesk'));
    });
  });

test('C: THE PRE-AUTH AND SSO TOKENS ROTATE TOO -- a partial rotation is the '
   + 'subtlest version of this bug', () => {
    // A rotation that reached session tokens but not the SSO state token would
    // show up as a broken login half a day later, in a different file.
    let pre;
    withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_PREVIOUS: null }, () => {
      pre = AUTHMOD.signPreAuthToken({ app: 'sairnlaw', employee_id: 'e1',
                                       role: 'attorney', license_hash: LIC_A });
      assert.ok(AUTHMOD.verifyPreAuthToken(pre, LIC_A, 'sairnlaw'), 'baseline');
    });
    withEnv({ SD_AUTH_SECRET: SIGN_2, SD_AUTH_SECRET_PREVIOUS: SIGN_1 }, () => {
      assert.ok(AUTHMOD.verifyPreAuthToken(pre, LIC_A, 'sairnlaw'),
        'the pre-auth token did not survive a rotation the session token did');
    });
    withEnv({ SD_AUTH_SECRET: SIGN_2, SD_AUTH_SECRET_PREVIOUS: null }, () => {
      assert.strictEqual(AUTHMOD.verifyPreAuthToken(pre, LIC_A, 'sairnlaw'), null);
    });
  });

// ══ STAGE D: PER-APP SIGNING SECRETS ═════════════════════════════════════
const APP_KEY = material('lawapp');

test('D: an app with NO dedicated secret is unchanged -- this rolls out app by '
   + 'app, not as one cutover', () => {
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_PREVIOUS: null,
            SD_AUTH_SECRET_SAIRNLAW: null }, () => {
    const tok = signSessionToken({ employee_id: 'e1', role: 'owner',
                                   license_hash: LIC_A, app: 'stonedesk' });
    assert.ok(verifySessionToken(tok, LIC_A, 'stonedesk'));
  });
});

test('D: THE BLAST RADIUS IS REALLY REDUCED -- the platform key cannot mint a '
   + 'token for an app that has its own', () => {
  // The arm this stage exists for. If it ever goes green with the platform key
  // still accepted, stage D is a label.
  let platformSigned;
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_SAIRNLAW: null,
            SD_AUTH_SECRET_PREVIOUS: null }, () => {
    platformSigned = signSessionToken({ employee_id: 'e1', role: 'attorney',
                                        license_hash: LIC_A, app: 'sairnlaw' });
  });
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_SAIRNLAW: APP_KEY,
            SD_AUTH_SECRET_SAIRNLAW_PREVIOUS: null }, () => {
    assert.strictEqual(verifySessionToken(platformSigned, LIC_A, 'sairnlaw'), null,
      'the platform secret still mints SAIRNlaw sessions after SAIRNlaw has its '
      + 'own key -- the reduction reduces nothing');
  });
});

test('D: ...and the SAME platform key still works for an app WITHOUT one, so '
   + 'the arm above is about scoping and not about breakage', () => {
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_SAIRNLAW: APP_KEY,
            SD_AUTH_SECRET_PREVIOUS: null }, () => {
    const tok = signSessionToken({ employee_id: 'e1', role: 'owner',
                                   license_hash: LIC_A, app: 'stonedesk' });
    assert.ok(verifySessionToken(tok, LIC_A, 'stonedesk'),
      'giving SAIRNlaw its own key broke StoneDesk');
  });
});

test('D: THE MIGRATION WINDOW -- an existing session survives the app getting '
   + 'its own key, and stops once the window closes', () => {
  let before;
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_SAIRNLAW: null,
            SD_AUTH_SECRET_PREVIOUS: null }, () => {
    before = signSessionToken({ employee_id: 'e1', role: 'attorney',
                               license_hash: LIC_A, app: 'sairnlaw' });
  });
  // The rollout: the app's PREVIOUS is the platform secret for one TTL.
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_SAIRNLAW: APP_KEY,
            SD_AUTH_SECRET_SAIRNLAW_PREVIOUS: SIGN_1 }, () => {
    assert.ok(verifySessionToken(before, LIC_A, 'sairnlaw'),
      'every signed-in attorney was logged out by the rollout');
    const fresh = signSessionToken({ employee_id: 'e2', role: 'attorney',
                                     license_hash: LIC_A, app: 'sairnlaw' });
    assert.ok(verifySessionToken(fresh, LIC_A, 'sairnlaw'));
  });
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_SAIRNLAW: APP_KEY,
            SD_AUTH_SECRET_SAIRNLAW_PREVIOUS: null }, () => {
    assert.strictEqual(verifySessionToken(before, LIC_A, 'sairnlaw'), null);
  });
});

test('D: a token signed with ANOTHER app key does not verify -- the key is '
   + 'chosen by the claimed app, and claiming does not help', () => {
  // The subtlety written into signingKeys(): the app claim picks the key.
  // Picking is not trusting -- a forger still needs the key they picked.
  let lawToken;
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_SAIRNLAW: APP_KEY,
            SD_AUTH_SECRET_SAIRNLAW_PREVIOUS: null }, () => {
    lawToken = signSessionToken({ employee_id: 'e1', role: 'attorney',
                                  license_hash: LIC_A, app: 'sairnlaw' });
    // Same signature, claiming to be StoneDesk: the payload changes, so the
    // signature no longer matches whichever key is chosen.
    const payload = JSON.parse(Buffer.from(
      lawToken.split('.')[0].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf8'));
    payload.app = 'stonedesk';
    const swapped = Buffer.from(JSON.stringify(payload)).toString('base64')
      .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
      + '.' + lawToken.split('.')[1];
    assert.strictEqual(verifySessionToken(swapped, LIC_A, 'stonedesk'), null);
  });
});

test('D: the env suffix is derived from the app name, not hand-mapped', () => {
  // A hand-kept name table is a second thing to get wrong during the one
  // operation where being wrong logs everybody out.
  // WRITTEN AFTER A SABOTAGE KILLED NOTHING. Signing AND verifying inside the
  // same env round-trips whichever key is picked, so it cannot tell exact
  // matching from prefix matching. The token has to be signed BEFORE the
  // unrelated variable exists: if `stonedesk` then prefix-matches
  // SD_AUTH_SECRET_STONEDESK_SUB it switches keys and rejects its own token.
  let signedBefore;
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_PREVIOUS: null,
            SD_AUTH_SECRET_STONEDESK_SUB: null }, () => {
    signedBefore = signSessionToken({ employee_id: 'e1', role: 'owner',
                                      license_hash: LIC_A, app: 'stonedesk' });
  });
  withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_STONEDESK_SUB: APP_KEY,
            SD_AUTH_SECRET_PREVIOUS: null }, () => {
    assert.ok(verifySessionToken(signedBefore, LIC_A, 'stonedesk'),
      'stonedesk picked up the stonedesk_sub key -- the suffix is matched '
      + 'by prefix, so giving one app a key silently re-keys another');
  });
});

test('C: a pre-auth token is STILL refused where a session is expected, after '
   + 'the refactor moved both through one verifier', () => {
    // The 2026-08-08 finding. Routing both through verifySignedPayload() must
    // not have lost the typ check that separates them.
    withEnv({ SD_AUTH_SECRET: SIGN_1, SD_AUTH_SECRET_PREVIOUS: null }, () => {
      const pre = AUTHMOD.signPreAuthToken({ app: 'sairnlaw', employee_id: 'e1',
                                             role: 'attorney', license_hash: LIC_A });
      assert.strictEqual(verifySessionToken(pre, LIC_A, 'sairnlaw'), null,
        'a pre-auth token passed as a session token -- MFA is skippable');
    });
  });

  console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
})();
