// api/_lib/dental-reminder-window.test.js
// Plain node:assert tests -- no test framework, matching api/'s existing
// zero-npm-dependency convention (see api/_lib/auth.test.js).
// Run: node api/_lib/dental-reminder-window.test.js
//
// This is the real, unblocked substitute for the design plan's Task 6
// "window-boundary test" step, which called for exercising the boundary
// via a live curl against the deployed cron endpoint -- that path is
// currently blocked on Namecheap DNS propagation for the Resend sending
// domain. The selection logic itself has no dependency on Resend/DNS at
// all, so it's verified here directly; the live curl test still runs
// once DNS resolves, to confirm actual delivery, not the selection math.

const assert = require('assert');
const { hoursUntil, needsStage } = require('./dental-reminder-window');

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

console.log('api/_lib/dental-reminder-window.js');

var NOW = new Date('2026-08-11T12:00:00.000Z').getTime();
function rowAt(hoursFromNow, sentFlags) {
  return {
    start_time: new Date(NOW + hoursFromNow * 60 * 60 * 1000).toISOString(),
    data: Object.assign({}, sentFlags)
  };
}

test('hoursUntil returns the exact fractional hour distance', () => {
  var r = rowAt(47.5, {});
  assert.strictEqual(Math.round(hoursUntil(r.start_time, NOW) * 100) / 100, 47.5);
});

// ── 48h window: (47, 48] ────────────────────────────────────────────
test('48h: just inside the window (47.5h out) needs the reminder', () => {
  assert.strictEqual(needsStage(rowAt(47.5, {}), '48h', NOW), true);
});
test('48h: exactly at the far (closed) edge, 48h out, needs the reminder', () => {
  assert.strictEqual(needsStage(rowAt(48, {}), '48h', NOW), true);
});
test('48h: just past the far edge, 48.1h out, does NOT need the reminder yet', () => {
  assert.strictEqual(needsStage(rowAt(48.1, {}), '48h', NOW), false);
});
test('48h: exactly at the near (open) edge, 47h out, does NOT need the reminder (excluded)', () => {
  assert.strictEqual(needsStage(rowAt(47, {}), '48h', NOW), false);
});
test('48h: just past the near edge, 46.9h out, does NOT need the reminder (too soon)', () => {
  assert.strictEqual(needsStage(rowAt(46.9, {}), '48h', NOW), false);
});

// ── 2h window: (1, 2] ───────────────────────────────────────────────
test('2h: just inside the window (1.5h out) needs the reminder', () => {
  assert.strictEqual(needsStage(rowAt(1.5, {}), '2h', NOW), true);
});
test('2h: exactly at the far (closed) edge, 2h out, needs the reminder', () => {
  assert.strictEqual(needsStage(rowAt(2, {}), '2h', NOW), true);
});
test('2h: just past the far edge, 2.1h out, does NOT need the reminder yet', () => {
  assert.strictEqual(needsStage(rowAt(2.1, {}), '2h', NOW), false);
});
test('2h: exactly at the near (open) edge, 1h out, does NOT need the reminder (excluded)', () => {
  assert.strictEqual(needsStage(rowAt(1, {}), '2h', NOW), false);
});
test('2h: just past the near edge, 0.9h out (already happening), does NOT need the reminder', () => {
  assert.strictEqual(needsStage(rowAt(0.9, {}), '2h', NOW), false);
});

// ── Idempotency: already-sent flags block a re-send ─────────────────
test('48h: inside the window but reminder_48h_sent_at already set -> does NOT need it again', () => {
  assert.strictEqual(needsStage(rowAt(47.5, { reminder_48h_sent_at: '2026-08-09T00:00:00.000Z' }), '48h', NOW), false);
});
test('2h: inside the window but reminder_2h_sent_at already set -> does NOT need it again', () => {
  assert.strictEqual(needsStage(rowAt(1.5, { reminder_2h_sent_at: '2026-08-11T10:00:00.000Z' }), '2h', NOW), false);
});
test('the two stages are independent: 48h already sent does not block the (later) 2h reminder', () => {
  var row = rowAt(1.5, { reminder_48h_sent_at: '2026-08-09T00:00:00.000Z' });
  assert.strictEqual(needsStage(row, '2h', NOW), true);
});

console.log(passed + ' passed' + (process.exitCode ? ', with failures above' : ''));
