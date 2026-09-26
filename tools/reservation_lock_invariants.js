// tools/reservation_lock_invariants.js
//
//   node tools/reservation_lock_invariants.js
//   node tools/reservation_lock_invariants.js --json
//
// ITEM 78, SECOND TARGET. docs/spec/RoleGates.tla took the FIRST target -- the
// cross-app role gates -- and tools/role_gate_invariants.js is the half of it
// that runs. This is the same pair of ideas applied to the one place on this
// platform that has a genuine CONCURRENCY invariant.
//
// ── WHY NOT THE ROLE GATE, WHICH IS WHAT ITEM 78 WAS POINTED AT ────────────
// The question asked was "does a lock genuinely prevent concurrent access".
// THE ROLE GATE IS NOT A LOCK AND HAS NO CONCURRENCY. It is a pure function of
// (session, resource, role set): no shared mutable state, no interleaving, no
// two callers whose order can change the answer. docs/spec/RoleGates.tla
// correctly contains no lock and states no temporal property, and asking an
// interleaving question about it would produce a spec that looked like
// verification and proved nothing.
//
// The platform DOES have a real lock, and it is unmodelled:
//
//   api/sd-data.js:12135   leg_merch_units, status -> 'Reserved'
//     A PATCH whose FILTER carries the precondition:
//       leg_merch_units?license_hash=eq.<lic>
//                       &merch_unit_id=eq.<id>
//                       &data->>status=eq.Available
//     Zero rows returned -> 409 ALREADY_RESERVED.
//
// That is a compare-and-swap executed by Postgres, and the stake is in the
// branch's own words: "the same physical casket/urn promised to two grieving
// families". `slabs` reserve/release is the same shape for a different app.
//
// ── WHAT THIS CHECKS, AND WHAT IT DELIBERATELY DOES NOT ───────────────────
//   IT DOES   enumerate EVERY interleaving of N concurrent reservers against
//             one unit, under two models of the write -- the CAS the code
//             actually performs, and the blind upsert it performs for every
//             OTHER transition -- and assert the mutual-exclusion invariant.
//
//   IT DOES   read the real branch out of api/sd-data.js and refuse to run if
//             the precondition is not there, so this tool cannot keep passing
//             after somebody replaces the CAS with an upsert.
//
//   IT DOES NOT prove anything about Postgres. The CAS is only atomic because
//             a single UPDATE ... WHERE is atomic. That is an assumption about
//             the database, it is stated here rather than hidden, and no
//             JavaScript can discharge it.
//
//   IT DOES NOT model the client's optimistic local write or its rollback.
//             Those are a separate correctness question (does the UI converge)
//             from the one asked here (can two families be promised one unit).
//
// ── EXHAUSTIVE IS AFFORDABLE, WHICH IS WHY THIS TARGET WAS CHOSEN ─────────
// Same reason authorization was the first target. One unit, N reservers, two
// steps each: the state space is tiny and there is no sampling anywhere below.
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const JSON_OUT = process.argv.includes('--json');

// ── THE PRECONDITION IS READ OUT OF THE REAL HANDLER ──────────────────────
// A model checker that agrees with a model is worth nothing. This asserts the
// thing being modelled is still what the code does, and REFUSES rather than
// passing if it is not -- could-not-tell is a third state (PR 1.11).
const SRC = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');
const CAS_FILTER = "&data->>status=eq.Available";
const CAS_GUARD = "resource === 'leg_merch_units' && payload.status === 'Reserved'";
const CAS_409 = 'ALREADY_RESERVED';

const evidence = {
  guard_present: SRC.includes(CAS_GUARD),
  precondition_in_filter: SRC.includes(CAS_FILTER),
  refuses_on_zero_rows: SRC.includes(CAS_409),
};
// The PATCH and the filter must be in the same branch, not merely both in the
// file -- a filter left behind after the method changed would read as present.
const gi = SRC.indexOf(CAS_GUARD);
const branch = gi === -1 ? '' : SRC.slice(gi, gi + 1600);
evidence.filter_inside_the_guard = branch.includes(CAS_FILTER);
evidence.method_is_patch = /method:\s*'PATCH'/.test(branch);

const missing = Object.keys(evidence).filter((k) => !evidence[k]);
if (missing.length) {
  const msg = 'COULD NOT RUN -- the reservation CAS is not in api/sd-data.js in '
    + 'the shape this tool models. Missing: ' + missing.join(', ')
    + '\nNOTHING WAS VERIFIED. This is not a pass. Either the branch moved, or '
    + 'the compare-and-swap was replaced by a blind upsert, and the second is '
    + 'the defect this tool exists to notice.';
  if (JSON_OUT) { console.log(JSON.stringify({ ok: false, could_not_run: true, evidence }, null, 1)); }
  else { console.error(msg); }
  process.exit(2);
}

// ── THE TWO WRITE MODELS ──────────────────────────────────────────────────
// `cas` is what the code does for status->Reserved. `blind` is what it does for
// every other transition, and is included as the CONTROL: if the invariant held
// under both, this tool would be asserting nothing about the lock.
function cas(unit, actor) {
  if (unit.status !== 'Available') return { ok: false, code: CAS_409 };
  unit.status = 'Reserved';
  unit.reserved_for = actor;
  return { ok: true };
}
function blind(unit, actor) {
  unit.status = 'Reserved';
  unit.reserved_for = actor;
  return { ok: true };
}

// ── EVERY INTERLEAVING, ENUMERATED ────────────────────────────────────────
// Each actor runs two steps: READ (observe status) then WRITE. An interleaving
// is any sequence of those 2N steps in which each actor's READ precedes its
// WRITE. Generated exhaustively, not sampled.
function interleavings(n) {
  const out = [];
  (function walk(seq, pending) {
    if (seq.length === 2 * n) { out.push(seq.slice()); return; }
    for (let a = 0; a < n; a++) {
      if (pending[a] === 0) { pending[a] = 1; seq.push([a, 'READ']); walk(seq, pending); seq.pop(); pending[a] = 0; }
      else if (pending[a] === 1) { pending[a] = 2; seq.push([a, 'WRITE']); walk(seq, pending); seq.pop(); pending[a] = 1; }
    }
  })([], new Array(n).fill(0));
  return out;
}

function runModel(write, n) {
  let violations = 0, traces = [];
  for (const seq of interleavings(n)) {
    const unit = { status: 'Available', reserved_for: null };
    const observed = {};
    const winners = [];
    for (const [a, step] of seq) {
      if (step === 'READ') { observed[a] = unit.status; continue; }
      // The client re-checks its OWN observation before confirming -- the
      // stale-local-copy check at sairnlegacy.html:2635. Modelled because
      // without it the client would not even attempt, and the question is
      // whether the SERVER is what stops it.
      if (observed[a] !== 'Available') continue;
      const r = write(unit, a);
      if (r.ok) winners.push(a);
    }
    // THE INVARIANT: at most one actor is ever told its reservation succeeded.
    if (winners.length > 1) { violations++; if (traces.length < 3) traces.push({ seq: seq.map((s) => s.join(':')), winners }); }
  }
  return { interleavings: interleavings(n).length, violations, traces };
}

const report = { evidence, models: {} };
let failed = false;
for (const n of [2, 3, 4]) {
  const c = runModel(cas, n);
  const b = runModel(blind, n);
  report.models['n=' + n] = { interleavings: c.interleavings, cas_violations: c.violations, blind_violations: b.violations };
  if (c.violations !== 0) { failed = true; report.models['n=' + n].cas_traces = c.traces; }
  // THE CONTROL: the blind model MUST violate. If it does not, the enumeration
  // is not reaching the interleaving that matters and a clean CAS result would
  // be meaningless -- the vacuous-pass shape this platform keeps recording.
  if (b.violations === 0) { failed = true; report.models['n=' + n].control_did_not_bite = true; }
}

if (JSON_OUT) { console.log(JSON.stringify({ ok: !failed, ...report }, null, 1)); process.exit(failed ? 1 : 0); }

console.log('RESERVATION LOCK -- mutual exclusion over every interleaving');
console.log('  subject: api/sd-data.js leg_merch_units status->Reserved (PATCH with');
console.log('           &data->>status=eq.Available in the filter, 409 on zero rows)');
console.log('');
console.log('  the modelled branch is still the code\'s shape:');
for (const k of Object.keys(evidence)) console.log('    ok   ' + k);
console.log('');
for (const n of [2, 3, 4]) {
  const m = report.models['n=' + n];
  console.log('  ' + n + ' concurrent reservers, ' + m.interleavings + ' interleavings');
  console.log('      CAS    violations: ' + m.cas_violations
    + (m.cas_violations === 0 ? '   (mutual exclusion holds)' : '   *** INVARIANT VIOLATED ***'));
  console.log('      blind  violations: ' + m.blind_violations
    + (m.blind_violations > 0 ? '   (CONTROL bites -- the enumeration reaches the race)'
                             : '   *** CONTROL DID NOT BITE -- the clean result above means nothing ***'));
  if (m.cas_traces) m.cas_traces.forEach((t) => console.log('      trace: ' + t.seq.join(' ') + ' -> winners ' + t.winners));
}
console.log('');
console.log('ASSUMPTION THIS CANNOT DISCHARGE: the CAS is atomic only because a');
console.log('single UPDATE ... WHERE is atomic in Postgres. That is a property of');
console.log('the database, not of this model, and no JavaScript here proves it.');
console.log('');
console.log(failed ? 'FAILED' : 'HOLDS -- at most one reserver is ever told it succeeded, under every');
if (!failed) console.log('interleaving enumerated, and the blind-upsert control violates in all three.');
process.exit(failed ? 1 : 0);
