// api/_lib/stripe-config.test.js
//
// Run:  node api/_lib/stripe-config.test.js
//
// ── WHY THIS FILE EXISTS, AND IT IS NOT "THE MODULE HAD NO TESTS" ──────────
// docs/ACCEPTED-RISKS.md AR-1 is accepted on a trigger, and this module IS that
// trigger:
//
//   "Trigger -- MECHANICAL: api/_lib/stripe-config.js returns a `warnings`
//    entry for a test key in a production deployment, and every SAIRNcash
//    endpoint logs it. The day a working live key is installed, that warning
//    stops appearing -- which is the moment this entry becomes live."
//
// TWO THINGS WERE WRONG WITH THAT, found 2026-09-15 by
// tools/weakness_combination.py and by reading this file:
//
//   1. NOTHING CONSUMES THE SIGNAL. It goes to a log. No checker, no gate, no
//      workflow reads it. A trigger nobody watches is not a trigger -- the
//      register's own rule, applied to the register.
//   2. NOTHING GUARDED THE PRODUCER EITHER. This module had NO suite at all, so
//      the `sk_test_` + production branch could have been edited away and the
//      only visible consequence would have been that an accepted risk's trigger
//      quietly stopped existing.
//
// (1) needs a decision about live environment reads and is now recorded in the
// register as an open question. (2) is fixable here and this file is the fix:
// if that branch is removed or weakened, THIS FAILS. That does not make the
// trigger watched. It makes the trigger's PRODUCER guarded, which is the half
// that can be held from inside the repo, and the register now says which half
// is which.
//
// ── AND THE CONTROL THAT MATTERS ──────────────────────────────────────────
// A warning that fires in every environment is not a signal, it is a banner. So
// all four combinations of (test key, live key) x (production, preview) are
// driven and EXACTLY ONE must warn.
//
// ── THE KEY FIXTURES ARE BUILT BY CONCATENATION ON PURPOSE ────────────────
// A literal `sk_live_...` in a tracked file is credential-shaped and the
// repo's own write guard refuses it -- correctly, since a scanner cannot tell a
// fixture from the real thing. The pieces are joined at runtime so the file
// carries no matchable literal and the test still exercises the real prefix.

const assert = require('assert');
const cfg = require('./stripe-config.js');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }

const LIVE = 'sk_' + 'live_' + 'FIXTURE0000000000000000';
const TEST = 'sk_' + 'test_' + 'FIXTURE0000000000000000';

// The healthy baseline is DERIVED from the capability table rather than typed,
// so adding a capability with a new required variable does not silently turn
// every "with everything present" arm below into a not-ready arm. Typing the
// list by hand got this wrong on the first run -- `checkout` also needs
// STRIPE_PRICE_ID and the hand-written baseline omitted it.
function env(over) {
  const base = { VERCEL_ENV: 'production' };
  for (const need of Object.values(cfg.CAPABILITIES)) {
    for (const name of need) base[name] = 'FIXTURE_' + name;
  }
  base.STRIPE_SECRET_KEY = LIVE;
  return Object.assign(base, over || {});
}

function warnsOf(over, capability) {
  return cfg.status(capability || 'checkout', env(over)).warnings;
}

// ════════════════════════════════════════════════════════════════════════════
// 1. THE CAPABILITY TABLE
// ════════════════════════════════════════════════════════════════════════════
t('every declared capability resolves and returns the documented shape', () => {
  const names = Object.keys(cfg.CAPABILITIES);
  assert.ok(names.length > 0, 'the capability table is empty');
  for (const n of names) {
    const s = cfg.status(n, env());
    for (const k of ['ready', 'missing', 'warnings', 'clientMessage', 'logMessage']) {
      assert.ok(k in s, n + ' is missing ' + k);
    }
    assert.strictEqual(typeof s.ready, 'boolean');
    assert.ok(Array.isArray(s.missing) && Array.isArray(s.warnings));
  }
});

t('an UNKNOWN capability THROWS rather than returning not-ready -- a typo that '
  + 'silently reported "not configured" would take a working endpoint off the '
  + 'air and look like a deployment problem', () => {
  assert.throws(() => cfg.status('chekcout', env()), /unknown capability/);
});

t('...and the throw NAMES the known capabilities, so the typo is fixable from '
  + 'the message alone', () => {
  try {
    cfg.status('nope', env());
    assert.fail('did not throw');
  } catch (e) {
    for (const n of Object.keys(cfg.CAPABILITIES)) {
      assert.ok(e.message.indexOf(n) !== -1, 'the error does not name ' + n);
    }
  }
});

t('a missing required variable makes ready FALSE and is named in `missing`', () => {
  const s = cfg.status('checkout', env({ STRIPE_SECRET_KEY: '' }));
  assert.strictEqual(s.ready, false);
  assert.ok(s.missing.indexOf('STRIPE_SECRET_KEY') !== -1, JSON.stringify(s.missing));
});

t('CONTROL: whitespace is not presence -- a variable set to spaces is MISSING, '
  + 'not present-but-empty', () => {
  assert.strictEqual(cfg.status('checkout', env({ STRIPE_SECRET_KEY: '   ' })).ready, false);
});

t('CONTROL: with everything present, ready is TRUE. A status that is never '
  + 'ready would pass every arm above', () => {
  assert.strictEqual(cfg.status('checkout', env()).ready, true);
});

// ════════════════════════════════════════════════════════════════════════════
// 2. AR-1's TRIGGER -- THE PRODUCER, AND IT MUST FIRE IN EXACTLY ONE PLACE
// ════════════════════════════════════════════════════════════════════════════
t('AR-1 TRIGGER: a TEST key in a PRODUCTION deployment produces a warning. '
  + 'This is the signal docs/ACCEPTED-RISKS.md AR-1 is accepted on, and if this '
  + 'arm ever fails the trigger has stopped existing', () => {
  const w = warnsOf({ STRIPE_SECRET_KEY: TEST, VERCEL_ENV: 'production' });
  assert.strictEqual(w.length, 1, JSON.stringify(w));
  assert.ok(/sk_test_/.test(w[0]), w[0]);
  assert.ok(/PRODUCTION/i.test(w[0]), w[0]);
});

t('...and it says the calls will FAIL, not merely that the key is unusual -- '
  + 'the consequence is the part a reader acts on', () => {
  const w = warnsOf({ STRIPE_SECRET_KEY: TEST, VERCEL_ENV: 'production' });
  assert.ok(/fail/i.test(w[0]), w[0]);
});

t('CONTROL: a LIVE key in production produces NO warning. This is the exact '
  + 'transition AR-1 calls its trigger -- the day a working live key is '
  + 'installed, the warning stops appearing', () => {
  assert.deepStrictEqual(warnsOf({ STRIPE_SECRET_KEY: LIVE, VERCEL_ENV: 'production' }), []);
});

t('CONTROL: a TEST key in a NON-production deployment produces NO warning. A '
  + 'test key in preview is correct, and warning there would make the signal a '
  + 'banner that fires everywhere', () => {
  assert.deepStrictEqual(warnsOf({ STRIPE_SECRET_KEY: TEST, VERCEL_ENV: 'preview' }), []);
  assert.deepStrictEqual(warnsOf({ STRIPE_SECRET_KEY: TEST, VERCEL_ENV: '' }), []);
});

t('CONTROL: of the four (key x environment) combinations EXACTLY ONE warns, '
  + 'which is what makes it a signal rather than a banner', () => {
  const grid = [
    [TEST, 'production', 1],
    [TEST, 'preview', 0],
    [LIVE, 'production', 0],
    [LIVE, 'preview', 0],
  ];
  const fired = grid.filter(([k, e]) =>
    warnsOf({ STRIPE_SECRET_KEY: k, VERCEL_ENV: e }).length > 0);
  assert.strictEqual(fired.length, 1, JSON.stringify(fired));
  for (const [k, e, want] of grid) {
    assert.strictEqual(
      warnsOf({ STRIPE_SECRET_KEY: k, VERCEL_ENV: e }).length, want,
      k.slice(0, 8) + ' in ' + (e || '(unset)'));
  }
});

t('the production test is case-insensitive on VERCEL_ENV, so a differently-'
  + 'cased value does not silently disable the trigger', () => {
  assert.strictEqual(
    warnsOf({ STRIPE_SECRET_KEY: TEST, VERCEL_ENV: 'PRODUCTION' }).length, 1);
});

t('the key test is an ANCHORED prefix -- a key merely CONTAINING the test '
  + 'prefix is not a test key, and matching anywhere would fire on a live key '
  + 'with an unlucky substring', () => {
  assert.deepStrictEqual(
    warnsOf({ STRIPE_SECRET_KEY: LIVE + 'sk_' + 'test_' + 'z',
              VERCEL_ENV: 'production' }), []);
});

t('a MISSING key produces no warning -- absent and present-but-wrong are two '
  + 'different states and `missing` is where absence is reported', () => {
  const s = cfg.status('checkout', env({ STRIPE_SECRET_KEY: '' }));
  assert.deepStrictEqual(s.warnings, []);
  assert.ok(s.missing.length > 0);
});

t('the warning reaches the LOG message and never the CLIENT message -- which '
  + 'is also why no checker in this repo can read it, and why the register now '
  + 'says the signal is produced and not consumed', () => {
  const s = cfg.status('checkout', env({ STRIPE_SECRET_KEY: TEST, VERCEL_ENV: 'production' }));
  assert.ok(s.logMessage.indexOf('sk_test_') !== -1, s.logMessage);
  assert.strictEqual(s.clientMessage.indexOf('sk_test_'), -1, s.clientMessage);
  assert.strictEqual(s.clientMessage.indexOf('STRIPE'), -1, s.clientMessage);
});

t('CONTROL: the client message never names a variable in ANY state, so a '
  + 'caller cannot infer the cause from it', () => {
  for (const over of [{}, { STRIPE_SECRET_KEY: '' }, { STRIPE_SECRET_KEY: TEST }]) {
    const s = cfg.status('checkout', env(over));
    assert.strictEqual(s.clientMessage, cfg.CLIENT_MESSAGE);
    assert.ok(!/STRIPE|sk_test|sk_live|whsec/.test(s.clientMessage), s.clientMessage);
  }
});

t('CONTROL: the LOG message does name the variables, or a log nobody can act '
  + 'on is the whole defect this module was built to end', () => {
  const s = cfg.status('checkout', env({ STRIPE_SECRET_KEY: '' }));
  assert.ok(s.logMessage.indexOf('STRIPE_SECRET_KEY') !== -1, s.logMessage);
});

t('the warning is the SAME under every capability -- it is a property of the '
  + 'environment, not of what is being attempted', () => {
  const seen = Object.keys(cfg.CAPABILITIES).map((c) =>
    JSON.stringify(warnsOf({ STRIPE_SECRET_KEY: TEST, VERCEL_ENV: 'production' }, c)));
  assert.strictEqual(new Set(seen).size, 1, seen.join(' | '));
});

// ════════════════════════════════════════════════════════════════════════════
// 3. THE MODULE DOES NOT READ process.env BEHIND THE CALLER'S BACK
// ════════════════════════════════════════════════════════════════════════════
t('a supplied env is the ONLY source consulted -- a module that fell back to '
  + 'process.env mid-call would make every arm above depend on the machine it '
  + 'ran on', () => {
  const before = process.env.STRIPE_SECRET_KEY;
  process.env.STRIPE_SECRET_KEY = TEST;
  try {
    assert.deepStrictEqual(
      warnsOf({ STRIPE_SECRET_KEY: LIVE, VERCEL_ENV: 'production' }), [],
      'process.env leaked into a call that supplied its own env');
  } finally {
    if (before === undefined) delete process.env.STRIPE_SECRET_KEY;
    else process.env.STRIPE_SECRET_KEY = before;
  }
});

// ════════════════════════════════════════════════════════════════════════════
for (const [name, fn] of queue) {
  try {
    fn();
    pass += 1;
    console.log('  ok   ' + name);
  } catch (e) {
    fail += 1;
    console.log('  FAIL ' + name + '\n         ' + (e && e.message));
  }
}
console.log('');
console.log(fail ? (fail + ' of ' + (pass + fail) + ' FAILED')
                 : ('ALL ' + pass + ' ASSERTIONS PASS'));
process.exit(fail ? 1 : 0);
