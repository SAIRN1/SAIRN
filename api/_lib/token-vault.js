// api/_lib/token-vault.js
// Symmetric encryption for third-party OAuth tokens at rest.
//
// ── WHY THIS IS NEW AND NOT REUSED ───────────────────────────────────────
// Checked before writing it, as usual: this platform has no symmetric
// encryption anywhere. api/_lib/auth.js uses scrypt (one-way, for PINs) and
// HMAC (signing, for session tokens), and neither can give a value BACK.
// An OAuth refresh token has to be recoverable to be used, so hashing it is
// not an option and signing it is not encryption. There is also no existing
// table on this platform that stores a third-party token -- verified against
// the 258-table schema snapshot -- so there is no convention to follow here,
// which is precisely why this is its own small file with its own tests rather
// than a few lines inlined into an endpoint.
//
// AES-256-GCM from Node's built-in crypto. No dependency: package.json holds
// exactly three, and adding a crypto library to do what the standard library
// does is how a supply chain grows.
//
// ── THE FAILURE MODE THIS FILE EXISTS TO PREVENT ─────────────────────────
// A missing or malformed key must NEVER fall back to storing the token in the
// clear. That failure is silent, looks like success, and is only discovered by
// somebody reading the database. So every entry point REFUSES rather than
// degrading, and a test asserts that refusing is what happens.
//
// Equally: a decryption that fails must fail. GCM's authentication tag means a
// tampered or truncated ciphertext throws rather than returning plausible
// rubbish, and that error is passed up rather than swallowed into a null the
// caller might treat as "no token".
//
// ── WHAT IT DOES NOT CLAIM ───────────────────────────────────────────────
// This protects tokens AT REST against someone reading the table. It does not
// protect against an attacker who already has the environment, because such an
// attacker has the key. That is the honest boundary of envelope encryption
// with a single environment-held key, and it is stated here so nobody reads
// "encrypted" as a stronger claim than it is.
//
// KEY ROTATION is why the ciphertext carries a version prefix. Rotating means
// decrypting with the old key and re-encrypting with the new one; there is no
// support for two live keys, and adding it should be a deliberate change with
// its own tests rather than something bolted on during an incident.

'use strict';

const crypto = require('crypto');

const VERSION = 'v1';
const ALGO = 'aes-256-gcm';
const KEY_BYTES = 32;
const IV_BYTES = 12;   // 96-bit, the size GCM is specified for
const ENV_VAR = 'ACCOUNTING_TOKEN_KEY';

// Read at call time, not at module load. A module-level read would freeze
// whatever the environment looked like when the function cold-started, and
// makes the whole file untestable without process-wide mutation.
function readKey(explicit) {
  const raw = (typeof explicit === 'string' && explicit) ? explicit : (process.env[ENV_VAR] || '');
  if (!raw) {
    const e = new Error(ENV_VAR + ' is not set -- refusing to store an OAuth token, because the alternative is storing it in the clear');
    e.code = 'NO_KEY';
    throw e;
  }
  if (!/^[0-9a-fA-F]{64}$/.test(raw)) {
    // Length is checked as HEX rather than after decoding, so a key that is
    // half-pasted fails loudly here instead of producing a short buffer that
    // createCipheriv would reject with a less obvious message.
    const e = new Error(ENV_VAR + ' must be exactly 64 hex characters (32 bytes) -- got ' + raw.length + ' characters');
    e.code = 'BAD_KEY';
    throw e;
  }
  return Buffer.from(raw, 'hex');
}

// Returns 'v1.<iv-b64>.<tag-b64>.<ciphertext-b64>'. Dot-separated and base64
// rather than JSON: it goes in a text column, and a format that cannot contain
// a dot in its parts cannot be ambiguous to split.
function encrypt(plaintext, keyHex) {
  if (typeof plaintext !== 'string' || plaintext === '') {
    const e = new Error('nothing to encrypt');
    e.code = 'NO_PLAINTEXT';
    throw e;
  }
  const key = readKey(keyHex);
  const iv = crypto.randomBytes(IV_BYTES);
  const c = crypto.createCipheriv(ALGO, key, iv);
  const ct = Buffer.concat([c.update(plaintext, 'utf8'), c.final()]);
  const tag = c.getAuthTag();
  return [VERSION, iv.toString('base64'), tag.toString('base64'), ct.toString('base64')].join('.');
}

function decrypt(payload, keyHex) {
  if (typeof payload !== 'string' || !payload) {
    const e = new Error('nothing to decrypt');
    e.code = 'NO_PAYLOAD';
    throw e;
  }
  const parts = payload.split('.');
  if (parts.length !== 4 || parts[0] !== VERSION) {
    const e = new Error('unrecognised ciphertext format or version');
    e.code = 'BAD_FORMAT';
    throw e;
  }
  const key = readKey(keyHex);
  const iv = Buffer.from(parts[1], 'base64');
  const tag = Buffer.from(parts[2], 'base64');
  const ct = Buffer.from(parts[3], 'base64');
  const d = crypto.createDecipheriv(ALGO, key, iv);
  d.setAuthTag(tag);
  // Throws on a bad tag. Deliberately NOT wrapped in a try that returns null:
  // "this token has been tampered with" and "there is no token" need opposite
  // responses, and a null would collapse them.
  return Buffer.concat([d.update(ct), d.final()]).toString('utf8');
}

// For an endpoint that wants to report health without holding a token: is the
// vault usable at all? Returns a reason rather than a bare false, because
// "nobody set the key" and "somebody set half of it" are different fixes.
function vaultStatus(keyHex) {
  try {
    readKey(keyHex);
    return { ok: true, usable: true, reason: null };
  } catch (e) {
    return { ok: true, usable: false, code: e.code, reason: e.message };
  }
}

// A convenience for generating one. Never called by the app; here so the value
// is produced by the same code that validates it rather than by a shell
// one-liner somebody adapts slightly wrong.
function generateKeyHex() {
  return crypto.randomBytes(KEY_BYTES).toString('hex');
}

module.exports = {
  ENV_VAR,
  VERSION,
  encrypt,
  decrypt,
  vaultStatus,
  generateKeyHex
};
