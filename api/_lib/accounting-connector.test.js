// api/_lib/accounting-connector.test.js
// Plain node:assert tests -- no framework, matching api/'s zero-npm-dependency
// convention. Run: node api/_lib/accounting-connector.test.js
//
// Three of these tests exist to make a product promise expensive to break. If
// somebody later adds a write path, an auto-connect, or a scope that expands
// silently, one of these fails and they have to delete it on purpose.

const assert = require('assert');
const a = require('./accounting-connector');

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

const TODAY = '2026-09-02';
const consent = (o) => Object.assign({
  provider: 'quickbooks_online', granted_by: 'owner@acme.example',
  granted_on: '2026-09-01', scopes: ['financial_summary'], revoked_on: null
}, o || {});

// ── it refuses to assume ──────────────────────────────────────────────────

test('every entry point REFUSES without today rather than defaulting to UTC now', () => {
  ['validateConsent', 'authoriseRead', 'connectionState'].forEach((fn) => {
    const r = a[fn]({});
    assert.strictEqual(r.ok, false, fn + ' should refuse');
    assert.strictEqual(r.error.code, 'NO_TODAY');
  });
});

// ── PROMISE 1: read-only, enforced ────────────────────────────────────────

test('EVERY non-GET method is refused, whatever the entity or the consent', () => {
  ['POST', 'PUT', 'PATCH', 'DELETE', 'post'].forEach((m) => {
    const r = a.authoriseRead({ today: TODAY, consent: consent(), entity: 'Account', method: m });
    assert.strictEqual(r.allowed, false, m + ' must be refused');
    assert.ok(/read-only and never writes/.test(r.reasons.join(' ')));
  });
});

test('the allowlist FAILS CLOSED -- an entity nobody thought of is refused', () => {
  const r = a.authoriseRead({ today: TODAY, consent: consent({ scopes: a.SCOPES }), entity: 'JournalEntry' });
  assert.strictEqual(r.allowed, false, 'a deny-list would have let this through');
  assert.ok(/not on the read allowlist/.test(r.reasons.join(' ')));
});

test('no employee, payroll or customer-PII entity is on the allowlist at all', () => {
  ['Employee', 'TimeActivity', 'Customer', 'Payroll'].forEach((e) => {
    assert.strictEqual(a.READABLE_ENTITIES.indexOf(e), -1,
      e + ' must not be readable: the findings do not need it and holding it is liability with no benefit');
  });
});

// ── PROMISE 2: explicit opt-in, provable ──────────────────────────────────

test('NO CONSENT means refused -- not defaulted, not assumed', () => {
  const r = a.authoriseRead({ today: TODAY, entity: 'Account' });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.error.code, 'NO_CONSENT');
});

test('a consent missing WHO or WHEN is not a weaker consent, it is not one', () => {
  const noWho = a.validateConsent({ today: TODAY, consent: consent({ granted_by: '' }) });
  assert.strictEqual(noWho.usable, false);
  assert.ok(/nobody is named/.test(noWho.reasons.join(' ')));
  const noWhen = a.validateConsent({ today: TODAY, consent: consent({ granted_on: null }) });
  assert.strictEqual(noWhen.usable, false);
  assert.ok(/no grant date/.test(noWhen.reasons.join(' ')));
});

test('an empty scope list is refused rather than treated as "everything"', () => {
  const r = a.validateConsent({ today: TODAY, consent: consent({ scopes: [] }) });
  assert.strictEqual(r.usable, false);
  assert.ok(/no scopes were consented to/.test(r.reasons.join(' ')));
});

test('an unrecognised scope is REFUSED, never silently dropped', () => {
  const r = a.validateConsent({ today: TODAY, consent: consent({ scopes: ['financial_summary', 'everything'] }) });
  assert.strictEqual(r.usable, false,
    'silently narrowing what somebody consented to is its own dishonesty, and widening it is worse');
  assert.ok(/unrecognised scope\(s\): everything/.test(r.reasons.join(' ')));
});

test('revocation takes effect and is its own state, not "invalid"', () => {
  const r = a.validateConsent({ today: TODAY, consent: consent({ revoked_on: '2026-09-01' }) });
  assert.strictEqual(r.state, 'revoked');
  assert.strictEqual(r.usable, false);
  const future = a.validateConsent({ today: TODAY, consent: consent({ revoked_on: '2027-01-01' }) });
  assert.strictEqual(future.usable, true, 'a revocation dated in the future has not happened yet');
});

test('an unsupported provider is refused', () => {
  const r = a.validateConsent({ today: TODAY, consent: consent({ provider: 'xero' }) });
  assert.strictEqual(r.usable, false);
  assert.ok(/is not one this connector supports/.test(r.reasons.join(' ')));
});

// ── scopes gate entities, and are DERIVED not stored ──────────────────────

test('entities come from the consented scopes, so the map can change under a consent', () => {
  const r = a.validateConsent({ today: TODAY, consent: consent({ scopes: ['expenses_and_vendors'] }) });
  assert.deepStrictEqual(r.entities.sort(), ['Bill', 'Purchase', 'Vendor']);
  assert.strictEqual(r.entities.indexOf('Invoice'), -1);
});

test('an allowlisted entity OUTSIDE the consented scopes is still refused', () => {
  const r = a.authoriseRead({ today: TODAY, consent: consent({ scopes: ['financial_summary'] }), entity: 'Invoice' });
  assert.strictEqual(r.allowed, false);
  assert.ok(/outside the scopes this customer consented to/.test(r.reasons.join(' ')));
});

test('the happy path is allowed, and carries what was consented for the log', () => {
  const r = a.authoriseRead({ today: TODAY, consent: consent(), entity: 'Account' });
  assert.strictEqual(r.allowed, true);
  assert.deepStrictEqual(r.reasons, []);
  assert.strictEqual(r.consent.granted_by, 'owner@acme.example');
  assert.deepStrictEqual(r.consent.scopes, ['financial_summary']);
});

test('a refusal names EVERY reason, not the first one', () => {
  const r = a.authoriseRead({ today: TODAY, consent: consent({ revoked_on: '2026-08-01' }), entity: 'JournalEntry', method: 'POST' });
  assert.strictEqual(r.allowed, false);
  assert.ok(r.reasons.length >= 3, 'got: ' + JSON.stringify(r.reasons));
});

// ── PROMISE 3: connection state never overstates itself ───────────────────

test('valid consent with NO connection is pending, never "connected"', () => {
  const r = a.connectionState({ today: TODAY, consent: consent() });
  assert.strictEqual(r.status, 'pending_consent');
  // My first draft asserted "has not happened yet" -- a phrase that exists only
  // in the COMMENT above that branch, not in the string it returns. The code
  // was right and the test was quoting the wrong line; fixed here rather than
  // by widening the regex until it passed.
  assert.ok(/has not completed the connection/.test(r.reason), r.reason);
});

test('no consent and no connection is not_connected, a different answer', () => {
  const r = a.connectionState({ today: TODAY, consent: consent({ scopes: [] }) });
  assert.strictEqual(r.status, 'not_connected');
});

test('a live connection whose consent was revoked says the token must be DISCARDED', () => {
  const r = a.connectionState({ today: TODAY, consent: consent({ revoked_on: '2026-08-01' }),
    connection: { status: 'connected', realm_id: '123', refresh_token_present: true } });
  assert.strictEqual(r.status, 'revoked');
  assert.ok(/discarded, not merely ignored/.test(r.reason));
});

test('a connection with no refresh token is an ERROR whatever its stored status says', () => {
  const r = a.connectionState({ today: TODAY, consent: consent(),
    connection: { status: 'connected', realm_id: '123', refresh_token_present: false } });
  assert.strictEqual(r.status, 'error');
  assert.ok(/cannot survive the access token expiring/.test(r.problems.join(' ')));
});

test('an expired access token is reported without pretending the link is dead', () => {
  const r = a.connectionState({ today: TODAY, consent: consent(),
    connection: { status: 'connected', realm_id: '123', refresh_token_present: true, expires_on: '2026-08-01' } });
  assert.strictEqual(r.status, 'connected');
  assert.ok(/must be refreshed before the next read/.test(r.problems.join(' ')));
});

test('an unrecognised connection status becomes error WITH a problem', () => {
  const r = a.connectionState({ today: TODAY, consent: consent(),
    connection: { status: 'probably-fine', refresh_token_present: true } });
  assert.strictEqual(r.status, 'error');
  assert.ok(/unrecognised connection status/.test(r.problems.join(' ')));
});

// ── the module surface itself ─────────────────────────────────────────────

test('this module cannot reach the network -- it exports decisions, not actions', () => {
  const src = require('fs').readFileSync(__dirname + '/accounting-connector.js', 'utf8');
  ['fetch(', 'require(\'https\')', 'require("https")', 'XMLHttpRequest'].forEach((needle) => {
    assert.strictEqual(src.indexOf(needle), -1,
      'found "' + needle + '": the endpoint acts, this file only decides');
  });
});

console.log(passed + ' passed');
