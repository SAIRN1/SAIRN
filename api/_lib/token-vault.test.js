// api/_lib/token-vault.test.js
// Plain node:assert tests. Run: node api/_lib/token-vault.test.js
//
// This is security-critical code whose worst failure is SILENT: a token stored
// in the clear looks exactly like a token stored safely until somebody opens
// the table. Most of these tests are about refusing, not about round-tripping.
//
// Note on naming: the variables below are keyA/keyB and the sample strings are
// deliberately bland. An earlier draft used realistic-looking names and values
// and was refused by the repo's credential-shaped-content hook -- correctly, on
// the pattern rather than on the intent. Test fixtures do not need to look like
// real secrets to test a vault.

const assert = require('assert');
const v = require('./token-vault');

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (e) {
    console.error('  FAIL - ' + name + '\n      ' + e.message);
    process.exitCode = 1;
  }
}
function throws(fn, code) {
  try { fn(); } catch (e) { return e.code === code ? true : ('wrong code: ' + e.code); }
  return 'did not throw';
}

const keyA = v.generateKeyHex();
const keyB = v.generateKeyHex();
const SAMPLE = 'sample-value-one';

// ── it round-trips ────────────────────────────────────────────────────────

test('a value survives encrypt -> decrypt unchanged', () => {
  assert.strictEqual(v.decrypt(v.encrypt(SAMPLE, keyA), keyA), SAMPLE);
});

test('unicode and long values survive', () => {
  const s = 'välue-' + 'x'.repeat(4000) + '-€';
  assert.strictEqual(v.decrypt(v.encrypt(s, keyA), keyA), s);
});

test('the same input encrypts differently every time (random IV)', () => {
  const a = v.encrypt('same', keyA), b = v.encrypt('same', keyA);
  assert.notStrictEqual(a, b, 'a deterministic ciphertext leaks equality between rows');
  assert.strictEqual(v.decrypt(a, keyA), v.decrypt(b, keyA));
});

test('the ciphertext does not contain the input, and is versioned', () => {
  const out = v.encrypt(SAMPLE, keyA);
  assert.strictEqual(out.indexOf(SAMPLE), -1);
  assert.ok(out.startsWith('v1.'), 'versioned so a future key rotation can tell formats apart');
});

// ── THE FAILURE THIS FILE EXISTS TO PREVENT ───────────────────────────────

test('NO KEY refuses -- it never falls back to storing the value in the clear', () => {
  const saved = process.env[v.ENV_VAR];
  delete process.env[v.ENV_VAR];
  try {
    assert.strictEqual(throws(() => v.encrypt(SAMPLE), 'NO_KEY'), true,
      'a silent plaintext fallback looks like success and is only found by reading the database');
    assert.strictEqual(throws(() => v.decrypt('v1.a.b.c'), 'NO_KEY'), true);
  } finally {
    if (saved === undefined) delete process.env[v.ENV_VAR]; else process.env[v.ENV_VAR] = saved;
  }
});

test('a HALF-PASTED key is refused rather than silently padded', () => {
  assert.strictEqual(throws(() => v.encrypt(SAMPLE, keyA.slice(0, 40)), 'BAD_KEY'), true);
  assert.strictEqual(throws(() => v.encrypt(SAMPLE, 'not-hex-at-all'), 'BAD_KEY'), true);
});

test('vaultStatus REPORTS the reason rather than a bare false', () => {
  assert.strictEqual(v.vaultStatus(keyA).usable, true);
  const bad = v.vaultStatus('abc');
  assert.strictEqual(bad.usable, false);
  assert.strictEqual(bad.code, 'BAD_KEY');
  assert.ok(/64 hex characters/.test(bad.reason), '"nobody set it" and "somebody set half of it" are different fixes');
});

// ── tampering must FAIL, not return rubbish ───────────────────────────────

test('a tampered ciphertext THROWS -- GCM authenticates, it does not guess', () => {
  const good = v.encrypt(SAMPLE, keyA);
  const parts = good.split('.');
  const flipped = Buffer.from(parts[3], 'base64');
  flipped[0] = flipped[0] ^ 0xff;
  const bad = [parts[0], parts[1], parts[2], flipped.toString('base64')].join('.');
  let threw = false;
  try { v.decrypt(bad, keyA); } catch (e) { threw = true; }
  assert.ok(threw, 'returning plausible rubbish here would be worse than failing');
});

test('the WRONG key throws rather than returning something', () => {
  const out = v.encrypt(SAMPLE, keyA);
  let threw = false;
  try { v.decrypt(out, keyB); } catch (e) { threw = true; }
  assert.ok(threw);
});

test('a truncated or reshaped payload is refused by FORMAT before any crypto', () => {
  assert.strictEqual(throws(() => v.decrypt('v1.only.three', keyA), 'BAD_FORMAT'), true);
  assert.strictEqual(throws(() => v.decrypt('v2.a.b.c', keyA), 'BAD_FORMAT'), true);
  assert.strictEqual(throws(() => v.decrypt('', keyA), 'NO_PAYLOAD'), true);
});

test('encrypting nothing is an explicit refusal, not an empty ciphertext', () => {
  assert.strictEqual(throws(() => v.encrypt('', keyA), 'NO_PLAINTEXT'), true);
  assert.strictEqual(throws(() => v.encrypt(null, keyA), 'NO_PLAINTEXT'), true);
});

// ── the error must never carry the sensitive material ─────────────────────

test('no thrown message contains the key or the input value', () => {
  const probes = [
    () => v.encrypt(SAMPLE, 'short'),
    () => v.decrypt('v1.a.b.c', 'short'),
    () => v.decrypt(v.encrypt(SAMPLE, keyA), keyB)
  ];
  probes.forEach((fn, i) => {
    try { fn(); assert.fail('probe ' + i + ' should have thrown'); }
    catch (e) {
      if (e && e.code === 'ERR_ASSERTION') throw e;
      const m = String(e && e.message);
      assert.strictEqual(m.indexOf(keyA), -1, 'probe ' + i + ' leaked a key');
      assert.strictEqual(m.indexOf(keyB), -1, 'probe ' + i + ' leaked a key');
      assert.strictEqual(m.indexOf(SAMPLE), -1, 'probe ' + i + ' leaked the input');
    }
  });
});

test('generateKeyHex produces a key this module accepts', () => {
  const k = v.generateKeyHex();
  assert.strictEqual(k.length, 64);
  assert.strictEqual(v.vaultStatus(k).usable, true);
  assert.strictEqual(v.decrypt(v.encrypt('x', k), k), 'x');
});

console.log(passed + ' passed');
