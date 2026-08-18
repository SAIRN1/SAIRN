// api/_lib/sairncash-trial.test.js
// Plain node:assert tests -- no test framework, matching this
// directory's existing convention (dental-reminder-window.test.js).
// Run: node api/_lib/sairncash-trial.test.js

const assert = require('assert');
const { computeExpiry, isTrialValid, daysLeft } = require('./sairncash-trial.js');

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

console.log('api/_lib/sairncash-trial.js');

test('computeExpiry returns exactly 30 days after the given start time', () => {
  const start = Date.UTC(2026, 0, 1, 0, 0, 0);
  const expiry = computeExpiry(start);
  assert.strictEqual(expiry, new Date(Date.UTC(2026, 0, 31, 0, 0, 0)).toISOString());
});

test('isTrialValid: true when active and expires_at is in the future', () => {
  const now = Date.UTC(2026, 0, 15);
  const row = { status: 'active', expires_at: new Date(Date.UTC(2026, 0, 20)).toISOString() };
  assert.strictEqual(isTrialValid(row, now), true);
});

test('isTrialValid: false when active but expires_at is in the past', () => {
  const now = Date.UTC(2026, 0, 25);
  const row = { status: 'active', expires_at: new Date(Date.UTC(2026, 0, 20)).toISOString() };
  assert.strictEqual(isTrialValid(row, now), false);
});

test('isTrialValid: false when status is revoked, even if expires_at is future', () => {
  const now = Date.UTC(2026, 0, 15);
  const row = { status: 'revoked', expires_at: new Date(Date.UTC(2026, 0, 20)).toISOString() };
  assert.strictEqual(isTrialValid(row, now), false);
});

test('isTrialValid: false when expires_at exactly equals now (boundary, not inclusive)', () => {
  const now = Date.UTC(2026, 0, 20);
  const row = { status: 'active', expires_at: new Date(now).toISOString() };
  assert.strictEqual(isTrialValid(row, now), false);
});

test('daysLeft: rounds up partial days (4 days 1 hour left -> 5)', () => {
  const now = Date.UTC(2026, 0, 15, 0, 0, 0);
  const expiresAt = new Date(Date.UTC(2026, 0, 19, 1, 0, 0)).toISOString();
  assert.strictEqual(daysLeft(expiresAt, now), 5);
});

test('daysLeft: exactly N whole days left -> N (no rounding up an extra day)', () => {
  const now = Date.UTC(2026, 0, 15, 0, 0, 0);
  const expiresAt = new Date(Date.UTC(2026, 0, 20, 0, 0, 0)).toISOString();
  assert.strictEqual(daysLeft(expiresAt, now), 5);
});

test('daysLeft: never returns negative once already expired', () => {
  const now = Date.UTC(2026, 0, 25);
  const expiresAt = new Date(Date.UTC(2026, 0, 20)).toISOString();
  assert.strictEqual(daysLeft(expiresAt, now), 0);
});

console.log(passed + ' passed');
