// api/stripe-config.test.js
// REQUIREMENT: one module answers whether Stripe is configured, reproduces the
//   two disagreements that actually happened between the five files that used
//   to answer it independently, and refuses to claim the one thing it cannot
//   know without calling Stripe
//
//
// Run:  node api/stripe-config.test.js
//
// ITEM 94. Five files answered "is Stripe configured" independently and three
// of them disagreed about the same environment. The arms that matter are not
// "does it return an object" -- they are the two disagreements that actually
// happened, reproduced against the module, plus the one thing the module must
// refuse to claim.

'use strict';
const assert = require('assert');
const cfg = require('./_lib/stripe-config');

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass += 1; console.log('  ok   ' + name); }
  catch (e) { fail += 1; console.log('  FAIL ' + name + '\n        ' + e.message); }
}

// ── THE STATE PRODUCTION WAS ACTUALLY IN ON 2026-09-14 ────────────────────
const PROD = { STRIPE_SECRET_KEY: 'sk_test_expired', VERCEL_ENV: 'production' };

console.log('1. the disagreement that happened, reproduced');

t('checkout is NOT ready, and the missing one is the PRICE ID -- not the key', () => {
  const s = cfg.status('checkout', PROD);
  assert.strictEqual(s.ready, false);
  assert.deepStrictEqual(s.missing, ['STRIPE_PRICE_ID']);
});

t('portal IS ready in the same environment -- the two really do differ', () => {
  assert.strictEqual(cfg.status('portal', PROD).ready, true);
});

t('AND THAT IS THE WHOLE BUG: one environment, two answers, and the difference '
  + 'is now visible in one place instead of being spread across two files', () => {
  const a = cfg.status('checkout', PROD), b = cfg.status('portal', PROD);
  assert.notStrictEqual(a.ready, b.ready);
  assert.ok(a.missing.length && !b.missing.length);
});

console.log('\n2. what a caller may say, and what it may not');

t('the client message is identical across capabilities, so no reader can infer '
  + 'a cause from it the way the old per-file strings invited', () => {
  const msgs = Object.keys(cfg.CAPABILITIES).map((c) => cfg.status(c, PROD).clientMessage);
  assert.strictEqual(new Set(msgs).size, 1, JSON.stringify(msgs));
});

t('and it never names an environment variable -- every one of these endpoints '
  + 'is unauthenticated', () => {
  Object.keys(cfg.CAPABILITIES).forEach((c) => {
    const s = cfg.status(c, PROD);
    s.missing.concat(['STRIPE_SECRET_KEY', 'STRIPE_PRICE_ID']).forEach((v) => {
      assert.strictEqual(s.clientMessage.indexOf(v), -1, c + ' leaked ' + v);
    });
  });
});

t('the LOG message does name them, because that is where somebody debugging is', () => {
  assert.ok(/STRIPE_PRICE_ID/.test(cfg.status('checkout', PROD).logMessage));
});

console.log('\n3. READY IS NOT WORKING -- the claim the module must refuse');

t('a present but TEST key in production is ready:true AND carries a warning', () => {
  const s = cfg.status('portal', PROD);
  assert.strictEqual(s.ready, true);
  assert.strictEqual(s.warnings.length, 1, JSON.stringify(s.warnings));
  assert.ok(/TEST key/.test(s.warnings[0]));
});

t('CONTROL: a live key in production produces NO warning, so the arm above is '
  + 'not passing because everything warns', () => {
  const s = cfg.status('portal', { STRIPE_SECRET_KEY: 'sk_live_x', VERCEL_ENV: 'production' });
  assert.strictEqual(s.warnings.length, 0, JSON.stringify(s.warnings));
});

t('a test key OUTSIDE production is not warned about -- that is the correct '
  + 'place for one', () => {
  const s = cfg.status('portal', { STRIPE_SECRET_KEY: 'sk_test_x', VERCEL_ENV: 'preview' });
  assert.strictEqual(s.warnings.length, 0);
});

console.log('\n4. absence, and the shapes that look like presence');

t('an empty string is NOT present -- an env var set to "" is the classic '
  + 'deployment shape that passes a bare falsy check only by luck', () => {
  assert.strictEqual(cfg.status('portal', { STRIPE_SECRET_KEY: '   ' }).ready, false);
});

t('a missing variable is reported by name in `missing`', () => {
  assert.deepStrictEqual(cfg.status('portal', {}).missing, ['STRIPE_SECRET_KEY']);
});

t('the webhook capabilities need DIFFERENT variables from each other, which is '
  + 'why this is a table and not one condition', () => {
  assert.deepStrictEqual(cfg.status('webhook:agent', {}).missing, ['STRIPE_WEBHOOK_SECRET']);
  assert.deepStrictEqual(cfg.status('webhook:sairncash', {}).missing,
    ['SAIRNCASH_STRIPE_WEBHOOK_SECRET', 'STRIPE_SECRET_KEY']);
});

console.log('\n5. a typo must not read as "not configured"');

t('an unknown capability THROWS -- returning not-ready would take a working '
  + 'endpoint off the air and look like a deployment problem', () => {
  assert.throws(() => cfg.status('portall', PROD), /unknown capability/);
});

t('...and the error names the ones that exist', () => {
  try { cfg.status('nope', PROD); } catch (e) {
    assert.ok(e.message.indexOf('checkout') !== -1, e.message);
  }
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
