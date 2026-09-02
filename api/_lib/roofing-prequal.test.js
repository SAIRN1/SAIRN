// api/_lib/roofing-prequal.test.js
// Plain node:assert tests -- no framework, matching api/'s zero-npm-dependency
// convention. Run: node api/_lib/roofing-prequal.test.js
//
// Every case is a way this could tell a contractor they are ready to submit a
// prequalification packet, or that a job is bondable, when neither is true.

const assert = require('assert');
const q = require('./roofing-prequal');

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
const doc = (o) => Object.assign({
  document_id: 'D1', kind: 'emr_letter', issuer: 'Erie Insurance',
  effective_on: '2026-01-01', expires_on: '2027-01-01',
  value: 0.87, value_year: 2026, source: 'our insurer letter, 2026-01-04'
}, o || {});

// ── it refuses to assume ──────────────────────────────────────────────────

test('every entry point REFUSES without today rather than defaulting to UTC now', () => {
  ['documentState', 'packetReadiness', 'bondingCapacity'].forEach((fn) => {
    const r = q[fn]({});
    assert.strictEqual(r.ok, false, fn + ' should refuse');
    assert.strictEqual(r.error.code, 'NO_TODAY');
  });
});

// ── EMR is reported, never judged ─────────────────────────────────────────

test('an EMR is carried through UNJUDGED -- no threshold is this app to assert', () => {
  const d = q.documentState({ today: TODAY, document: doc({ value: 1.42 }) });
  assert.strictEqual(d.value, 1.42);
  assert.strictEqual(d.state, 'current');
  const keys = Object.keys(d).join(' ');
  assert.ok(!/acceptable|pass|good|threshold/.test(keys),
    '"under 1.0" is each GC\'s own criterion, not a rule this engine may apply');
});

test('a figure with no source, or no year, is flagged', () => {
  assert.ok(/no source/.test(q.documentState({ today: TODAY, document: doc({ source: '' }) }).problems.join(' ')));
  assert.ok(/no year/.test(q.documentState({ today: TODAY, document: doc({ value_year: null }) }).problems.join(' ')));
});

// ── expiry ────────────────────────────────────────────────────────────────

test('no expiry recorded is its own state, not "current"', () => {
  const d = q.documentState({ today: TODAY, document: doc({ expires_on: null }) });
  assert.strictEqual(d.state, 'no_expiry_recorded');
  assert.strictEqual(d.days_left, null);
});

test('expired, expiring and current are distinguished, and the window is the caller s', () => {
  assert.strictEqual(q.documentState({ today: TODAY, document: doc({ expires_on: '2026-01-01' }) }).state, 'expired');
  const soon = doc({ expires_on: '2026-09-20' });
  assert.strictEqual(q.documentState({ today: TODAY, document: soon }).state, 'expiring');
  assert.strictEqual(q.documentState({ today: TODAY, document: soon, warn_days: 3 }).state, 'current');
});

// ── packet readiness ──────────────────────────────────────────────────────

test('four failure states, not one -- missing, expired, undated, expiring', () => {
  const r = q.packetReadiness({ today: TODAY,
    required_kinds: ['emr_letter', 'financials', 'safety_program', 'references'],
    documents: [
      doc({ document_id: 'A', kind: 'emr_letter' }),
      doc({ document_id: 'B', kind: 'financials', expires_on: '2026-01-01' }),
      doc({ document_id: 'C', kind: 'safety_program', expires_on: null })
    ] });
  assert.deepStrictEqual(r.missing, ['references']);
  assert.deepStrictEqual(r.expired, ['financials']);
  assert.deepStrictEqual(r.undated, ['safety_program']);
  assert.strictEqual(r.ready, false);
});

test('a CURRENT duplicate beats a stale one of the same kind, and vice versa', () => {
  const r = q.packetReadiness({ today: TODAY, required_kinds: ['financials'], documents: [
    doc({ document_id: 'OLD', kind: 'financials', expires_on: '2026-01-01' }),
    doc({ document_id: 'NEW', kind: 'financials', expires_on: '2027-06-01' })
  ] });
  assert.deepStrictEqual(r.satisfied, ['financials']);
  assert.strictEqual(r.ready, true, 'a stale duplicate must not mask a good document');
  const r2 = q.packetReadiness({ today: TODAY, required_kinds: ['financials'], documents: [
    doc({ document_id: 'OLD', kind: 'financials', expires_on: '2026-01-01' })
  ] });
  assert.strictEqual(r2.ready, false, 'and a good one must not be invented from a stale one');
});

test('expiring counts as satisfied but is still surfaced', () => {
  const r = q.packetReadiness({ today: TODAY, required_kinds: ['emr_letter'],
    documents: [doc({ expires_on: '2026-09-20' })] });
  assert.deepStrictEqual(r.expiring, ['emr_letter']);
  assert.deepStrictEqual(r.satisfied, ['emr_letter']);
  assert.strictEqual(r.ready, true);
});

test('an EMPTY required list is never "ready" -- there is no default GC form', () => {
  const r = q.packetReadiness({ today: TODAY, required_kinds: [], documents: [doc()] });
  assert.strictEqual(r.ready, false,
    'every GC prequalification form differs; shipping a guess would say ready when it is not');
  assert.deepStrictEqual(r.extra, ['emr_letter']);
});

test('documents the GC did not ask for are listed but do not count toward readiness', () => {
  const r = q.packetReadiness({ today: TODAY, required_kinds: ['financials'], documents: [
    doc({ kind: 'financials' }), doc({ document_id: 'X', kind: 'bond_letter' })
  ] });
  assert.deepStrictEqual(r.extra, ['bond_letter']);
  assert.strictEqual(r.ready, true);
});

// ── bonding ───────────────────────────────────────────────────────────────

const bond = (o) => Object.assign({
  surety: 'Travelers', agent: 'Hall & Co', single_project_limit: 2000000,
  aggregate_limit: 5000000, effective_on: '2026-01-01', expires_on: '2027-01-01',
  source: 'surety letter 2026-01-15'
}, o || {});

test('remaining aggregate is limit minus the backlog the CALLER supplied', () => {
  const b = q.bondingCapacity({ today: TODAY, bonding: bond(), committed_backlog: 3200000, backlog_basis: 'contract value less earned, from the WIP schedule' });
  assert.strictEqual(b.remaining_aggregate, 1800000);
  assert.strictEqual(b.aggregate_used_pct, 64);
  assert.strictEqual(b.backlog_basis, 'contract value less earned, from the WIP schedule');
});

test('over the aggregate is REPORTED, never clamped to zero', () => {
  const b = q.bondingCapacity({ today: TODAY, bonding: bond(), committed_backlog: 6000000 });
  assert.strictEqual(b.remaining_aggregate, -1000000);
  assert.strictEqual(b.over_aggregate, 1000000,
    'it is precisely the condition a surety needs to hear about');
});

test('no aggregate, or no backlog, means remaining is NOT worked out', () => {
  assert.strictEqual(q.bondingCapacity({ today: TODAY, bonding: bond({ aggregate_limit: null }), committed_backlog: 1 }).remaining_aggregate, null);
  assert.strictEqual(q.bondingCapacity({ today: TODAY, bonding: bond() }).remaining_aggregate, null);
});

test('a candidate job within both limits is within capacity', () => {
  const b = q.bondingCapacity({ today: TODAY, bonding: bond(), committed_backlog: 3200000, candidate_value: 900000 });
  assert.strictEqual(b.candidate, 'within_capacity');
  assert.deepStrictEqual(b.candidate_reasons, []);
});

test('over the single-project limit and over the remaining aggregate are named separately', () => {
  const big = q.bondingCapacity({ today: TODAY, bonding: bond(), committed_backlog: 0, candidate_value: 2500000 });
  assert.strictEqual(big.candidate, 'over_capacity');
  assert.ok(/single-project limit/.test(big.candidate_reasons.join(' ')));
  const full = q.bondingCapacity({ today: TODAY, bonding: bond(), committed_backlog: 4500000, candidate_value: 900000 });
  assert.ok(/remaining aggregate/.test(full.candidate_reasons.join(' ')));
});

test('CANNOT TELL is a real answer and is not "within capacity"', () => {
  const b = q.bondingCapacity({ today: TODAY, bonding: bond({ single_project_limit: null }), committed_backlog: 0, candidate_value: 100 });
  assert.strictEqual(b.candidate, 'cannot_tell',
    'a contractor told a job is bondable on a missing limit bids work it cannot bond');
  const b2 = q.bondingCapacity({ today: TODAY, bonding: bond(), candidate_value: 100 });
  assert.strictEqual(b2.candidate, 'cannot_tell');
});

test('an EXPIRED surety letter blocks the candidate and is its own reason', () => {
  const b = q.bondingCapacity({ today: TODAY, bonding: bond({ expires_on: '2026-01-01' }), committed_backlog: 0, candidate_value: 100 });
  assert.strictEqual(b.letter_state, 'expired');
  assert.ok(/surety letter has expired/.test(b.candidate_reasons.join(' ')));
  assert.strictEqual(b.candidate, 'over_capacity');
});

test('limits with no source are flagged even when the arithmetic works', () => {
  const b = q.bondingCapacity({ today: TODAY, bonding: bond({ source: '' }), committed_backlog: 1000000 });
  assert.strictEqual(b.remaining_aggregate, 4000000);
  assert.ok(/no source recorded/.test(b.problems.join(' ')));
});

console.log(passed + ' passed');
