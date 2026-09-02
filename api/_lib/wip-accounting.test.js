// api/_lib/wip-accounting.test.js
// Plain node:assert tests -- no framework, matching api/'s zero-npm-dependency
// convention. Run: node api/_lib/wip-accounting.test.js
//
// Every case is a way this could hand a contractor, an owner or a surety a
// number that is confidently wrong about money.

const assert = require('assert');
const w = require('./wip-accounting');

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
const draw = (o) => Object.assign({
  draw_id: 'DR-1', job_id: 'J1', draw_no: 1, period_end: '2026-08-31',
  pct_complete: 50, amount: 100000, retainage_pct: 10,
  status: 'requested', requested_at: '2026-09-01', amount_received: 0
}, o || {});

// ── it refuses to assume ──────────────────────────────────────────────────

test('every entry point REFUSES without today rather than defaulting to UTC now', () => {
  ['summariseDraw', 'jobWip', 'portfolio'].forEach((fn) => {
    const r = w[fn]({});
    assert.strictEqual(r.ok, false, fn + ' should refuse');
    assert.strictEqual(r.error.code, 'NO_TODAY');
  });
});

// ── retainage is derived, and absent is not zero ──────────────────────────

test('retainage is DERIVED from the percentage, never read from a stored field', () => {
  const d = w.summariseDraw({ today: TODAY, draw: draw({ amount: 45000, retainage_pct: 10, retainage_held: 999999 }) });
  assert.strictEqual(d.retainage_held, 4500, 'a stored held figure must not win over the arithmetic');
  assert.strictEqual(d.net_requested, 40500);
});

test('NO retainage percentage is not zero -- it is unknown, and says so', () => {
  const d = w.summariseDraw({ today: TODAY, draw: draw({ retainage_pct: null }) });
  assert.strictEqual(d.retainage_held, null);
  assert.strictEqual(d.net_requested, null);
  assert.strictEqual(d.outstanding, null,
    'defaulting to zero would tell a contractor the full amount is collectable');
  assert.ok(/no retainage percentage recorded/.test(d.problems.join(' ')));
});

test('an out-of-range retainage percentage is refused, not clamped', () => {
  const d = w.summariseDraw({ today: TODAY, draw: draw({ retainage_pct: 140 }) });
  assert.strictEqual(d.retainage_held, null);
  assert.ok(/outside 0-100/.test(d.problems.join(' ')));
});

test('outstanding never goes negative, and overpayment is surfaced', () => {
  const d = w.summariseDraw({ today: TODAY, draw: draw({ amount_received: 50000 }) });
  assert.strictEqual(d.outstanding, 40000);
  const over = w.summariseDraw({ today: TODAY, draw: draw({ amount_received: 95000 }) });
  assert.strictEqual(over.outstanding, 0);
  assert.strictEqual(over.overpaid, 5000);
});

// ── ageing ────────────────────────────────────────────────────────────────

test('ageing runs from the REQUESTED date, not the period end', () => {
  const d = w.summariseDraw({ today: TODAY, draw: draw({ requested_at: '2026-07-01', period_end: '2026-08-31' }) });
  assert.strictEqual(d.days_outstanding, 63);
  assert.strictEqual(d.aged, true);
});

test('the aged window is a caller setting, not an industry term', () => {
  const d = draw({ requested_at: '2026-08-20' });          // 13 days
  assert.strictEqual(w.summariseDraw({ today: TODAY, draw: d }).aged, false);
  assert.strictEqual(w.summariseDraw({ today: TODAY, draw: d, aged_days: 7 }).aged, true);
});

test('a received draw is not aged, and a missing requested date is flagged', () => {
  assert.strictEqual(w.summariseDraw({ today: TODAY, draw: draw({ status: 'received', requested_at: '2026-01-01' }) }).aged, false);
  const noDate = w.summariseDraw({ today: TODAY, draw: draw({ requested_at: null }) });
  assert.ok(/no requested date/.test(noDate.problems.join(' ')));
});

test('an unrecognised status becomes null WITH a problem, never passed through', () => {
  const d = w.summariseDraw({ today: TODAY, draw: draw({ status: 'sent-ish' }) });
  assert.strictEqual(d.status, null);
  assert.ok(/unrecognised draw status/.test(d.problems[0]));
});

// ── the basis, which is the honesty hinge ─────────────────────────────────

test('percent complete from a draw is LABELLED contractor-stated, not computed', () => {
  const r = w.jobWip({ today: TODAY, job: { job_id: 'J1', contract_value: 200000 }, draws: [draw()] });
  assert.strictEqual(r.basis, 'contractor_stated_percent');
  assert.strictEqual(r.pct_complete, 50);
  assert.strictEqual(r.pct_complete_as_of, '2026-08-31');
  assert.strictEqual(r.earned, 100000);
});

test('cost_to_cost is used ONLY when costs are actually supplied', () => {
  const r = w.jobWip({ today: TODAY, job: { job_id: 'J1', contract_value: 200000 }, draws: [draw()],
    cost_to_date: 30000, estimated_total_cost: 120000 });
  assert.strictEqual(r.basis, 'cost_to_cost');
  assert.strictEqual(r.pct_complete, 25, 'the draw said 50 -- costs win when they exist, and the label says so');
});

test('the LATEST draw by period end supplies the percent, not the first', () => {
  const r = w.jobWip({ today: TODAY, job: { job_id: 'J1', contract_value: 200000 }, draws: [
    draw({ draw_id: 'A', period_end: '2026-06-30', pct_complete: 20 }),
    draw({ draw_id: 'B', period_end: '2026-08-31', pct_complete: 70 })
  ] });
  assert.strictEqual(r.pct_complete, 70);
});

test('no percent and no costs means earned is NOT guessed', () => {
  const r = w.jobWip({ today: TODAY, job: { job_id: 'J1', contract_value: 200000 },
    draws: [draw({ pct_complete: null })] });
  assert.strictEqual(r.basis, 'none');
  assert.strictEqual(r.earned, null);
  assert.strictEqual(r.over_under, null);
  assert.strictEqual(r.position, 'unknown');
});

test('no contract value means earned is NOT guessed either', () => {
  const r = w.jobWip({ today: TODAY, job: { job_id: 'J1', contract_value: null }, draws: [draw()] });
  assert.strictEqual(r.earned, null);
  assert.ok(/no contract value/.test(r.problems.join(' ')));
});

// ── over/under ────────────────────────────────────────────────────────────

test('over-billed and under-billed are named, not just signed', () => {
  const over = w.jobWip({ today: TODAY, job: { job_id: 'J1', contract_value: 100000 }, draws: [draw({ amount: 80000, pct_complete: 50 })] });
  assert.strictEqual(over.earned, 50000);
  assert.strictEqual(over.over_under, 30000);
  assert.strictEqual(over.position, 'over_billed');
  const under = w.jobWip({ today: TODAY, job: { job_id: 'J1', contract_value: 100000 }, draws: [draw({ amount: 20000, pct_complete: 50 })] });
  assert.strictEqual(under.position, 'under_billed');
});

test('draws belonging to another job are not counted against this one', () => {
  const r = w.jobWip({ today: TODAY, job: { job_id: 'J1', contract_value: 100000 }, draws: [
    draw({ draw_id: 'MINE', job_id: 'J1', amount: 10000 }),
    draw({ draw_id: 'THEIRS', job_id: 'J2', amount: 90000 })
  ] });
  assert.strictEqual(r.requested_total, 10000);
  assert.strictEqual(r.draw_count, 1);
});

test('an unusable retainage percentage makes the total an UNDERCOUNT, and says so', () => {
  const r = w.jobWip({ today: TODAY, job: { job_id: 'J1', contract_value: 100000 }, draws: [
    draw({ draw_id: 'A', amount: 50000, retainage_pct: 10 }),
    draw({ draw_id: 'B', amount: 50000, retainage_pct: null })
  ] });
  assert.strictEqual(r.retainage_held, 5000);
  assert.ok(/undercount/.test(r.problems.join(' ')), 'a low number with no warning is the silent failure');
});

// ── the book ──────────────────────────────────────────────────────────────

test('the portfolio splits over- from under-billed rather than netting them', () => {
  const p = w.portfolio({ today: TODAY, jobs: [
    { job_id: 'J1', contract_value: 100000 },
    { job_id: 'J2', contract_value: 100000 }
  ], draws: [
    draw({ draw_id: 'A', job_id: 'J1', amount: 80000, pct_complete: 50 }),
    draw({ draw_id: 'B', job_id: 'J2', amount: 20000, pct_complete: 50 })
  ] });
  assert.strictEqual(p.over_billed, 30000);
  assert.strictEqual(p.under_billed, 30000, 'netting these to zero would hide both');
  assert.strictEqual(p.retainage_held, 10000);
});

test('jobs that could not be computed are LISTED, never silently omitted', () => {
  const p = w.portfolio({ today: TODAY, jobs: [
    { job_id: 'GOOD', contract_value: 100000 },
    { job_id: 'BAD', contract_value: null }
  ], draws: [draw({ draw_id: 'A', job_id: 'GOOD' }), draw({ draw_id: 'B', job_id: 'BAD' })] });
  assert.strictEqual(p.not_computable.length, 1);
  assert.strictEqual(p.not_computable[0].job_id, 'BAD');
  assert.ok(p.not_computable[0].reasons.join(' ').length > 0,
    'a WIP schedule that omits what it could not compute reads as a complete book');
});

console.log(passed + ' passed');
