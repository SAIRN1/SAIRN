// api/_lib/firebase-mint.test.js
// ---------------------------------------------------------------------------
// DRIVES THE REAL mintCustomToken PATH. No network, no Firebase project, and
// no stub of firebase-admin itself.
//
// WHY THIS EXISTS. The dependabot HIGH on node-forge sits under
// firebase-admin, and the upgrade 12.7.0 -> 14.5.0 was measured as "0 of 248
// suites changed verdict" -- which was true and bounded by what the suites
// cover. NO SUITE DROVE A REAL mintCustomToken, so the one code path the
// advisory actually touches was the one path nothing exercised. Said as a
// limit in docs/2026-10-05-dependabot-high-triage.md on 2026-10-06; this is
// that limit closed.
//
// THE ADVISORY'S CALL SITE IS ON THIS PATH. In 12.7.0 the only forge.* call in
// the whole SDK is `forge.pki.privateKeyFromPem(this.privateKey)` inside
// ServiceAccount's constructor -- reached by `admin.credential.cert(json)`,
// which is exactly what getAdminApp() does. So driving mintCustomToken drives
// the parser the advisory is about.
//
// THERE IS NO NETWORK BOUNDARY TO STUB, AND THAT IS THE POINT.
// createCustomToken() signs a JWT locally with the service-account private key
// -- RS256, in-process, no HTTP. So the "real path" is fully reachable offline
// with a THROWAWAY key generated here. Nothing is mocked: real
// credential.cert(), real initializeApp(), real createCustomToken().
//
// THE KEY IS GENERATED PER RUN AND IS NOT A SECRET. crypto.generateKeyPairSync
// produces it in memory; it is never written to disk and corresponds to no
// real Firebase project. A fixed test key committed to a repo is a credential;
// a generated one is arithmetic.
// ---------------------------------------------------------------------------
'use strict';

const assert = require('assert');
const crypto = require('crypto');

let pass = 0;
const fails = [];

function check(name, fn) {
  try {
    fn();
    pass += 1;
  } catch (err) {
    fails.push(name + ' -- ' + (err && err.message ? err.message : String(err)));
  }
}

function b64urlToBuf(s) {
  return Buffer.from(s.replace(/-/g, '+').replace(/_/g, '/'), 'base64');
}

async function main() {
  const { privateKey, publicKey } = crypto.generateKeyPairSync('rsa', {
    modulusLength: 2048,
    privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
    publicKeyEncoding: { type: 'spki', format: 'pem' },
  });

  // A service account shaped exactly as firebase-admin expects. project_id,
  // private_key and client_email are the three fields ServiceAccount requires,
  // and the private_key is the one node-forge parsed in 12.7.0.
  process.env.SAIRNCASH_FIREBASE_SERVICE_ACCOUNT = JSON.stringify({
    type: 'service_account',
    project_id: 'zz-mint-arm',
    private_key: privateKey,
    client_email: 'zz-mint-arm@zz-mint-arm.iam.gserviceaccount.com',
  });

  const { mintCustomToken } = require('./firebase-admin.js');

  // ── THE PAIRED NEGATIVES FIRST ──────────────────────────────────────────
  // A token minted for a bad uid would be the worst outcome here, so the
  // refusals are asserted before the success. If these passed and the mint
  // below failed, the arm would still be measuring something.
  for (const bad of [null, undefined, '', 0, {}, []]) {
    let threw = false;
    try {
      await mintCustomToken(bad);
    } catch (e) {
      threw = true;
    }
    check('REFUSES a non-string uid: ' + JSON.stringify(bad), function () {
      assert.strictEqual(threw, true, 'minted a token for ' + JSON.stringify(bad));
    });
  }

  // ── THE REAL MINT ───────────────────────────────────────────────────────
  const uid = 'cus_ZZMINTARM0001';
  const token = await mintCustomToken(uid);

  check('mintCustomToken returns a non-empty string', function () {
    assert.strictEqual(typeof token, 'string');
    assert.ok(token.length > 100, 'token is implausibly short: ' + token.length);
  });

  const parts = String(token).split('.');
  check('the token is a three-part JWS', function () {
    assert.strictEqual(parts.length, 3, 'got ' + parts.length + ' part(s)');
  });

  const header = JSON.parse(b64urlToBuf(parts[0]).toString('utf8'));
  const payload = JSON.parse(b64urlToBuf(parts[1]).toString('utf8'));

  check('header alg is RS256 -- the signing actually happened, and with the '
        + 'asymmetric algorithm rather than a none/HS fallback', function () {
    assert.strictEqual(header.alg, 'RS256');
  });

  check('payload uid is EXACTLY the uid passed in -- this is the claim RTDB '
        + 'rules check as auth.uid === $customerId', function () {
    assert.strictEqual(payload.uid, uid);
  });

  check('payload sub and iss are the service-account client_email', function () {
    assert.strictEqual(payload.sub,
      'zz-mint-arm@zz-mint-arm.iam.gserviceaccount.com');
    assert.strictEqual(payload.iss,
      'zz-mint-arm@zz-mint-arm.iam.gserviceaccount.com');
  });

  // MY FIRST VERSION OF THIS ARM WAS WRONG AND THE RUN SAID SO. I asserted the
  // LEGACY audience, which contains `verifyCustomToken`. The real value is the
  // modern IdentityToolkit v1 audience and contains no such word. Corrected to
  // what firebase-admin actually emits, with both halves asserted so the arm
  // still distinguishes a custom token from any other credential shape.
  check('payload aud is the IdentityToolkit v1 audience, so this is a CUSTOM '
        + 'TOKEN and not some other credential shape', function () {
    assert.strictEqual(String(payload.aud),
      'https://identitytoolkit.googleapis.com/'
      + 'google.identity.identitytoolkit.v1.IdentityToolkit',
      'aud was ' + payload.aud);
  });

  check('exp is in the future and at most one hour out', function () {
    const now = Math.floor(Date.now() / 1000);
    assert.ok(payload.exp > now, 'already expired');
    assert.ok(payload.exp - now <= 3600 + 60, 'exp more than an hour out');
  });

  // ── THE SIGNATURE, VERIFIED AGAINST THE PUBLIC HALF ─────────────────────
  // This is the arm that proves the private key was really parsed and really
  // used. Every assertion above would still pass against a token whose
  // signature was garbage.
  check('THE SIGNATURE VERIFIES against the public half of the generated key '
        + '-- so credential.cert() parsed the PEM and createCustomToken() '
        + 'signed with it, which is the whole path the advisory touches',
    function () {
      const ok = crypto.createVerify('RSA-SHA256')
        .update(parts[0] + '.' + parts[1])
        .verify(publicKey, b64urlToBuf(parts[2]));
      assert.strictEqual(ok, true, 'signature did not verify');
    });

  check('NEGATIVE HALF: a tampered payload does NOT verify, so the arm above '
        + 'is not passing because verify() returns true for anything',
    function () {
      const tampered = Buffer.from(JSON.stringify(
        Object.assign({}, payload, { uid: 'cus_SOMEONE_ELSE' })
      )).toString('base64url');
      const ok = crypto.createVerify('RSA-SHA256')
        .update(parts[0] + '.' + tampered)
        .verify(publicKey, b64urlToBuf(parts[2]));
      assert.strictEqual(ok, false, 'a tampered token verified');
    });

  // ── AND THE CONFIG REFUSAL, DRIVEN IN A CHILD PROCESS ──────────────────
  // The first version of this arm was `assert.ok(true)` with a paragraph
  // explaining why it could not be tested. THAT IS A FABRICATED CHECK -- the
  // exact shape this repo scans for -- and the real obstacle was only that the
  // module caches its app in THIS process. A child process has an empty module
  // cache, so the refusal is drivable and is driven.
  const child = require('child_process').spawnSync(process.execPath, ['-e',
    "delete process.env.SAIRNCASH_FIREBASE_SERVICE_ACCOUNT;"
    + "require('./api/_lib/firebase-admin.js').mintCustomToken('cus_x')"
    + ".then(function(){process.exit(9)})"
    + ".catch(function(e){process.exit(e && e.code === 'CONFIG' ? 0 : 8)})"],
    { cwd: process.cwd(), encoding: 'utf8' });
  check('a MISSING service account is a CONFIG error and mints NOTHING -- '
        + 'driven in a child process, because this process has already '
        + 'initialised the app',
    function () {
      assert.strictEqual(child.status, 0,
        'child exited ' + child.status + ' (9 = it MINTED a token without a '
        + 'credential, 8 = threw something other than CONFIG) '
        + String(child.stderr || '').slice(0, 300));
    });

  if (fails.length) {
    console.error('api/_lib/firebase-mint.test.js: ' + fails.length + ' FAILED');
    fails.forEach(function (f) { console.error('  ! ' + f); });
    process.exit(1);
  }
  console.log('api/_lib/firebase-mint.test.js: all ' + pass
    + ' assertions passed -- REAL mintCustomToken, real credential.cert(), '
    + 'signature verified, no network');
}

main().catch(function (err) {
  console.error('api/_lib/firebase-mint.test.js: THREW -- ' + (err && err.stack ? err.stack : err));
  process.exit(1);
});
