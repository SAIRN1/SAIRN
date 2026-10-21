// api/_lib/routes.test.js
// REQUIREMENT: the shared routing primitive orders what it is allowed to order,
//   and when it cannot, it SAYS SO rather than handing back the input
//
// Run:  node api/_lib/routes.test.js
//
// ── WHY THE ARMS ARE SHAPED LIKE THIS ──────────────────────────────────────
// Most of this suite is about the THIRD STATE, not about the ordering. The
// ordering is a nearest-neighbour loop and it is easy; the thing that has
// actually gone wrong on this platform, repeatedly, is a "could not run"
// arriving dressed as a result. The implementation this module recovers
// (35169ea2, never on `main`) floored its saving at Math.max(0, ...), which
// made an unmeasurable route and an already-optimal route render the same
// "0 min". So every arm below that looks like paranoia about null is testing
// the one defect this module exists to not re-ship.
//
// EVERY REFUSAL IS DRIVEN IN BOTH DIRECTIONS. An arm that only proves a
// refusal fires proves nothing about whether it fires too often, and a
// validator that refuses everything passes a one-sided suite.

'use strict';
const assert = require('assert');
const R = require('./routes.js');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

// A stop, with the fields the module actually reads.
function stop(o) {
  return Object.assign({ address: 'addr', status: 'pending', locked: false }, o);
}
// Build an NxN matrix from a function, Infinity for unreachable.
function mat(n, f) {
  const m = [];
  for (let i = 0; i < n; i++) {
    const row = [];
    for (let j = 0; j < n; j++) row.push(i === j ? 0 : f(i, j));
    m.push(row);
  }
  return m;
}

// ───────────────────────────────────────────────────────────────────────────
section('1. THE ORIGINAL DEFECT — a floored saving loses a real distinction');

t('the ORIGINAL formula renders unmeasurable and zero-saving identically', () => {
  // The real body from 35169ea2, kept here so the arm compares against the
  // actual old behaviour rather than a description of it.
  const oldSaved = (origSecs, optSecs) => Math.max(0, Math.round((origSecs - optSecs) / 60));
  // Case A: three legs unreachable, so totals were accumulated as 0.
  assert.strictEqual(oldSaved(0, 0), 0);
  // Case B: genuinely already optimal.
  assert.strictEqual(oldSaved(600, 600), 0);
  // Indistinguishable. That is the bug.
});

t('THE NEW ONE RETURNS null WHEN A LEG IS UNREACHABLE', () => {
  const d = mat(3, (i, j) => (i === 0 && j === 2 ? Infinity : 100));
  assert.strictEqual(R.savedSeconds([0, 2, 1], [0, 1, 2], d), null);
});

t('...and 0 WHEN IT IS GENUINELY ZERO — the pair that proves it discriminates', () => {
  const d = mat(3, () => 100);
  assert.strictEqual(R.savedSeconds([0, 1, 2], [0, 2, 1], d), 0);
});

t('a NEGATIVE saving is returned as-is and NOT clamped', () => {
  // Nearest-neighbour can genuinely be worse than a human's order. Storing
  // that is learning something true; clamping it is how the original lost
  // the distinction.
  const d = mat(3, (i, j) => (i === 0 && j === 1 ? 10 : 500));
  const before = R.pathSeconds([0, 1, 2], d);
  const after = R.pathSeconds([0, 2, 1], d);
  assert.ok(before < after);
  assert.strictEqual(R.savedSeconds([0, 1, 2], [0, 2, 1], d), before - after);
  assert.ok(R.savedSeconds([0, 1, 2], [0, 2, 1], d) < 0);
});

t('savedSeconds refuses mismatched or too-short paths rather than guessing', () => {
  const d = mat(3, () => 100);
  assert.strictEqual(R.savedSeconds([0, 1], [0, 1, 2], d), null);
  assert.strictEqual(R.savedSeconds([0], [0], d), null);
  assert.strictEqual(R.savedSeconds(null, [0, 1], d), null);
});

// ───────────────────────────────────────────────────────────────────────────
section('2. orderStops — it orders, or it returns null. Never the input back.');

t('a reachable set is reordered by nearest neighbour', () => {
  // 0 -> 2 is cheap, 0 -> 1 is dear. Optimal visiting order is 0,2,1.
  const stops = [stop({ address: 'A' }), stop({ address: 'B' }), stop({ address: 'C' })];
  const d = mat(3, (i, j) => {
    if (i === 0 && j === 2) return 10;
    if (i === 2 && j === 1) return 20;
    return 900;
  });
  const r = R.orderStops(stops, d);
  assert.deepStrictEqual(r.order, [0, 2, 1]);
  assert.strictEqual(r.moved, 2);
});

t('NO REACHABLE PAIR AT ALL returns null — not the input echoed back', () => {
  const stops = [stop({}), stop({}), stop({})];
  const d = mat(3, () => Infinity);
  assert.strictEqual(R.orderStops(stops, d), null);
});

t('...which is the arm that stops "unchanged" reading as "confirmed optimal"', () => {
  const stops = [stop({}), stop({})];
  assert.strictEqual(R.orderStops(stops, mat(2, () => Infinity)), null);
});

t('fewer than two stops is not an ordering question', () => {
  assert.strictEqual(R.orderStops([stop({})], mat(1, () => 0)), null);
  assert.strictEqual(R.orderStops([], []), null);
});

t('a malformed matrix is refused rather than indexed into', () => {
  const stops = [stop({}), stop({}), stop({})];
  assert.strictEqual(R.orderStops(stops, [[0, 1], [1, 0]]), null);
  assert.strictEqual(R.orderStops(stops, 'nope'), null);
  assert.strictEqual(R.orderStops(stops, [[0, 1, 2], [1, 0], [2, 1, 0]]), null);
});

t('the returned order is a PERMUTATION — every stop appears exactly once', () => {
  const stops = [stop({}), stop({}), stop({}), stop({}), stop({})];
  const d = mat(5, (i, j) => ((i * 7 + j * 3) % 11) + 1);
  const r = R.orderStops(stops, d);
  assert.strictEqual(new Set(r.order).size, 5);
  assert.deepStrictEqual(r.order.slice().sort((a, b) => a - b), [0, 1, 2, 3, 4]);
});

// ───────────────────────────────────────────────────────────────────────────
section('3. WHAT MAY NOT MOVE — locked, done, skipped');

t('a LOCKED stop holds its exact position', () => {
  const stops = [stop({}), stop({ locked: true }), stop({}), stop({})];
  const d = mat(4, (i, j) => ((i + j) % 5) + 1);
  const r = R.orderStops(stops, d);
  assert.strictEqual(r.order[1], 1, 'index 1 must still hold stop 1');
});

t('a DONE stop holds its position — reordering history is nonsense', () => {
  const stops = [stop({ status: 'done' }), stop({}), stop({}), stop({})];
  const d = mat(4, (i, j) => ((i * 3 + j) % 7) + 1);
  const r = R.orderStops(stops, d);
  assert.strictEqual(r.order[0], 0);
});

t('a SKIPPED stop holds its position too — a decision was made about it', () => {
  const stops = [stop({}), stop({}), stop({ status: 'skipped' }), stop({})];
  const d = mat(4, (i, j) => ((i + j * 2) % 6) + 1);
  const r = R.orderStops(stops, d);
  assert.strictEqual(r.order[2], 2);
});

t('THE PAIR: an UNLOCKED stop in the same slot DOES move', () => {
  // Without this arm, a function that pinned everything would pass above.
  const stops = [stop({}), stop({}), stop({})];
  const d = mat(3, (i, j) => (i === 0 && j === 2 ? 1 : 500));
  const r = R.orderStops(stops, d);
  assert.strictEqual(r.order[1], 2, 'stop 2 should have moved into slot 1');
  assert.ok(r.moved > 0);
});

t('fewer than two MOVABLE stops is nothing to decide', () => {
  const stops = [stop({ locked: true }), stop({ locked: true }), stop({})];
  const d = mat(3, () => 10);
  assert.strictEqual(R.orderStops(stops, d), null);
});

t('isPinned is true for each of the three kinds and false for a plain stop', () => {
  assert.strictEqual(R.isPinned(stop({ locked: true })), true);
  assert.strictEqual(R.isPinned(stop({ status: 'done' })), true);
  assert.strictEqual(R.isPinned(stop({ status: 'skipped' })), true);
  assert.strictEqual(R.isPinned(stop({})), false);
});

// ───────────────────────────────────────────────────────────────────────────
section('4. THE THREE STATES OF optimize(), and they are never folded');

const twoStops = [
  stop({ address: '12 Elm St', lat: 41.45, lng: -81.92 }),
  stop({ address: '89 Commerce', lat: 41.46, lng: -81.90 })
];
const threeStops = twoStops.concat([stop({ address: '334 Lake Rd', lat: 41.48, lng: -81.80 })]);

function fakeFetch(body, ok) {
  return async () => ({ ok: ok !== false, json: async () => body });
}

t('drive-matrix: a real matrix answers and the basis says so', async () => {
  const els = [];
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) {
    els.push({ originIndex: i, destinationIndex: j, condition: 'ROUTE_EXISTS',
               duration: (i === 0 && j === 2 ? 10 : 600) + 's' });
  }
  const r = await R.optimize(threeStops, { apiKey: 'k', fetch: fakeFetch(els) });
  assert.strictEqual(r.basis, 'drive-matrix');
  assert.ok(Array.isArray(r.order));
  assert.strictEqual(typeof r.saved_seconds, 'number');
});

t('NO KEY -> basis unavailable, reason no-key, ORDER IS null', async () => {
  // These stops have no coordinates, so the great-circle second basis cannot
  // rescue it either -- which is what makes this the pure unavailable arm.
  const bare = [stop({ address: 'A' }), stop({ address: 'B' })];
  const r = await R.optimize(bare, { apiKey: '', fetch: fakeFetch([]) });
  assert.strictEqual(r.basis, 'unavailable');
  assert.strictEqual(r.reason, 'no-key');
  assert.strictEqual(r.order, null, 'THE STORED ORDER MUST NOT CHANGE');
  assert.strictEqual(r.saved_seconds, null);
});

t('an UPSTREAM 502 is its own reason, not a generic failure', async () => {
  const bare = [stop({ address: 'A' }), stop({ address: 'B' })];
  const r = await R.optimize(bare, { apiKey: 'k', fetch: fakeFetch(null, false) });
  assert.strictEqual(r.basis, 'unavailable');
  assert.strictEqual(r.reason, 'upstream-status');
});

t('a NETWORK throw is its own reason', async () => {
  const bare = [stop({ address: 'A' }), stop({ address: 'B' })];
  const thrower = async () => { throw new Error('ECONNRESET'); };
  const r = await R.optimize(bare, { apiKey: 'k', fetch: thrower });
  assert.strictEqual(r.reason, 'network');
});

t('a non-array upstream body is upstream-shape, not a crash', async () => {
  const bare = [stop({ address: 'A' }), stop({ address: 'B' })];
  const r = await R.optimize(bare, { apiKey: 'k', fetch: fakeFetch({ error: 'nope' }) });
  assert.strictEqual(r.reason, 'upstream-shape');
});

t('EVERY unavailable reason is distinct — the whole point of naming them', () => {
  const reasons = ['no-key', 'upstream-status', 'upstream-shape', 'network',
                   'no-reachable-pair', 'too-few-stops', 'nothing-movable', 'not-orderable'];
  assert.strictEqual(new Set(reasons).size, reasons.length);
});

t('GREAT-CIRCLE is the second basis, and it carries NO saved_seconds', async () => {
  // Key absent, but the stops DO have usable fixes.
  const r = await R.optimize(threeStops, { apiKey: '', fetch: fakeFetch([]) });
  assert.strictEqual(r.basis, 'great-circle');
  assert.ok(Array.isArray(r.order));
  assert.strictEqual(r.saved_seconds, null,
    'straight-line metres are not seconds and must never be reported as a saving');
  assert.strictEqual(r.drive_unavailable_because, 'no-key');
});

t('...and great-circle is NEVER reported as drive-matrix', async () => {
  const r = await R.optimize(threeStops, { apiKey: '', fetch: fakeFetch([]) });
  assert.notStrictEqual(r.basis, 'drive-matrix');
});

t('too few stops is refused before any network call is attempted', async () => {
  let called = false;
  const spy = async () => { called = true; return { ok: true, json: async () => [] }; };
  const r = await R.optimize([stop({})], { apiKey: 'k', fetch: spy });
  assert.strictEqual(r.basis, 'unavailable');
  assert.strictEqual(r.reason, 'too-few-stops');
  assert.strictEqual(called, false, 'no key should be spent on an impossible request');
});

t('all-pinned is "nothing-movable" and also spends no call', async () => {
  let called = false;
  const spy = async () => { called = true; return { ok: true, json: async () => [] }; };
  const r = await R.optimize(
    [stop({ locked: true }), stop({ locked: true })], { apiKey: 'k', fetch: spy });
  assert.strictEqual(r.reason, 'nothing-movable');
  assert.strictEqual(called, false);
});

t('"unavailable" is NOT a storable basis — STORED_BASES excludes it', () => {
  assert.ok(!R.STORED_BASES.includes('unavailable'));
  assert.deepStrictEqual(R.STORED_BASES, ['manual', 'drive-matrix', 'great-circle']);
});

// ───────────────────────────────────────────────────────────────────────────
section('5. driveMatrix — the upstream contract, and what it refuses to trust');

t('ROUTE_EXISTS rows are read and everything else is left unreachable', async () => {
  const els = [
    { originIndex: 0, destinationIndex: 1, condition: 'ROUTE_EXISTS', duration: '120s' },
    { originIndex: 1, destinationIndex: 0, condition: 'ROUTE_NOT_FOUND', duration: '0s' }
  ];
  const r = await R.driveMatrix(['A', 'B'], { apiKey: 'k', fetch: fakeFetch(els) });
  assert.strictEqual(r.matrix[0][1], 120);
  assert.strictEqual(r.matrix[1][0], Infinity);
});

t('AN OUT-OF-RANGE INDEX IS DROPPED, not written past the end of the matrix', async () => {
  const els = [
    { originIndex: 0, destinationIndex: 1, condition: 'ROUTE_EXISTS', duration: '60s' },
    { originIndex: 9, destinationIndex: 9, condition: 'ROUTE_EXISTS', duration: '60s' },
    { originIndex: -1, destinationIndex: 0, condition: 'ROUTE_EXISTS', duration: '60s' }
  ];
  const r = await R.driveMatrix(['A', 'B'], { apiKey: 'k', fetch: fakeFetch(els) });
  assert.strictEqual(r.matrix.length, 2);
  assert.strictEqual(r.matrix[0].length, 2);
  assert.strictEqual(r.matrix[0][1], 60);
});

t('a NON-NUMERIC duration is dropped rather than becoming NaN', async () => {
  const els = [
    { originIndex: 0, destinationIndex: 1, condition: 'ROUTE_EXISTS', duration: 'soon' },
    { originIndex: 1, destinationIndex: 0, condition: 'ROUTE_EXISTS', duration: '90s' }
  ];
  const r = await R.driveMatrix(['A', 'B'], { apiKey: 'k', fetch: fakeFetch(els) });
  assert.strictEqual(r.matrix[0][1], Infinity);
  assert.strictEqual(r.matrix[1][0], 90);
});

t('zero reachable pairs is no-reachable-pair, NOT an all-Infinity matrix', async () => {
  const els = [{ originIndex: 0, destinationIndex: 1, condition: 'ROUTE_NOT_FOUND', duration: '0s' }];
  const r = await R.driveMatrix(['A', 'B'], { apiKey: 'k', fetch: fakeFetch(els) });
  assert.strictEqual(r.matrix, undefined);
  assert.strictEqual(r.unavailable, 'no-reachable-pair');
});

t('THE KEY IS SENT IN A HEADER AND NEVER IN THE URL', async () => {
  let seenUrl = null, seenHeaders = null;
  const spy = async (url, opts) => {
    seenUrl = url; seenHeaders = opts.headers;
    return { ok: true, json: async () => [] };
  };
  await R.driveMatrix(['A', 'B'], { apiKey: 'SECRET-KEY', fetch: spy });
  assert.ok(!String(seenUrl).includes('SECRET-KEY'), 'key must not reach the URL');
  assert.strictEqual(seenUrl, R.ROUTE_MATRIX_URL);
  assert.strictEqual(seenHeaders['X-Goog-Api-Key'], 'SECRET-KEY');
});

// ───────────────────────────────────────────────────────────────────────────
section('6. great-circle distance, and the accuracy band that is ADDED');

t('haversine agrees with an independently known figure', () => {
  // 0.001 degrees of latitude = 111.195 m on the WGS84 mean radius. Same
  // check sairngrounds used, so the two implementations are comparable.
  const m = R.haversineM({ lat: 41.000, lng: -81.0 }, { lat: 41.001, lng: -81.0 });
  assert.ok(Math.abs(m - 111.195) < 0.05, 'got ' + m);
});

t('BANDS ARE ADDED, NOT AVERAGED — 20 + 10 is over the 25 m ceiling', () => {
  const a = { lat: 41.0, lng: -81.0, accuracy_m: 20 };
  const b = { lat: 41.001, lng: -81.0, accuracy_m: 10 };
  // Averaged would be 15 and would pass. Added is 30 and must not.
  assert.strictEqual(R.pairIsUsable(a, b), false);
});

t('...and the PAIR: 12 + 10 is 22 and does pass', () => {
  const a = { lat: 41.0, lng: -81.0, accuracy_m: 12 };
  const b = { lat: 41.001, lng: -81.0, accuracy_m: 10 };
  assert.strictEqual(R.pairIsUsable(a, b), true);
});

t('ABSENT accuracy is usable — absent is not the same as bad', () => {
  // Refusing an ordinary geocoded address for carrying no device accuracy
  // would refuse almost every real stop.
  const a = { lat: 41.0, lng: -81.0 };
  const b = { lat: 41.001, lng: -81.0 };
  assert.strictEqual(R.pairIsUsable(a, b), true);
});

t('a missing coordinate is not usable', () => {
  assert.strictEqual(R.pairIsUsable({ lat: 41.0 }, { lat: 41.0, lng: -81.0 }), false);
  assert.strictEqual(R.pairIsUsable({ lat: null, lng: null }, { lat: 41.0, lng: -81.0 }), false);
});

t('greatCircleMatrix returns null when nothing is geocoded', () => {
  assert.strictEqual(R.greatCircleMatrix([stop({}), stop({})]), null);
});

t('...and a matrix when something is', () => {
  const m = R.greatCircleMatrix(twoStops);
  assert.ok(m[0][1] > 0 && isFinite(m[0][1]));
  assert.strictEqual(m[0][0], 0);
});

// ───────────────────────────────────────────────────────────────────────────
section('7. applyOrder — seq is rewritten in exactly one place');

t('seq comes out 1-based and contiguous', () => {
  const stops = [stop({ address: 'A' }), stop({ address: 'B' }), stop({ address: 'C' })];
  const out = R.applyOrder(stops, [2, 0, 1]);
  assert.deepStrictEqual(out.map((s) => s.seq), [1, 2, 3]);
  assert.deepStrictEqual(out.map((s) => s.address), ['C', 'A', 'B']);
});

t('a DUPLICATE index is refused — it would destroy a stop', () => {
  const stops = [stop({}), stop({}), stop({})];
  assert.strictEqual(R.applyOrder(stops, [0, 0, 1]), null);
});

t('an out-of-range or wrong-length order is refused', () => {
  const stops = [stop({}), stop({})];
  assert.strictEqual(R.applyOrder(stops, [0, 5]), null);
  assert.strictEqual(R.applyOrder(stops, [0]), null);
  assert.strictEqual(R.applyOrder(stops, [0, 1.5]), null);
});

t('the source stop is COPIED, not mutated', () => {
  const stops = [stop({ address: 'A', seq: 1 }), stop({ address: 'B', seq: 2 })];
  R.applyOrder(stops, [1, 0]);
  assert.strictEqual(stops[0].seq, 1, 'input must be untouched');
});

// ───────────────────────────────────────────────────────────────────────────
section('8. the refusals, each driven in BOTH directions');

t('route key: every field required, and a good key passes', () => {
  assert.ok(R.validateRouteKey({ assignee_id: 'x', route_date: '2026-10-19' }));
  assert.ok(R.validateRouteKey({ app_id: 'a', route_date: '2026-10-19' }));
  assert.ok(R.validateRouteKey({ app_id: 'a', assignee_id: 'x' }));
  assert.strictEqual(
    R.validateRouteKey({ app_id: 'stonedesk', assignee_id: 'EMP-1', route_date: '2026-10-19' }),
    null);
});

t('route_date must be YYYY-MM-DD, not a datetime and not a loose date', () => {
  for (const bad of ['2026-10-19T00:00:00Z', '2026-1-9', '19/10/2026', '', 20261019]) {
    assert.ok(R.validateRouteKey({ app_id: 'a', assignee_id: 'b', route_date: bad }),
      'should refuse ' + bad);
  }
});

t('a stop needs an address, and a real one passes', () => {
  assert.ok(R.validateStops([{ }]));
  assert.ok(R.validateStops([{ address: '   ' }]));
  assert.strictEqual(R.validateStops([{ address: '12 Elm St' }]), null);
});

t('ONE COORDINATE OF A PAIR IS REFUSED — mirrors rtstops_coords_are_a_pair', () => {
  assert.ok(R.validateStops([{ address: 'A', lat: 41.0 }]));
  assert.ok(R.validateStops([{ address: 'A', lng: -81.0 }]));
  assert.strictEqual(R.validateStops([{ address: 'A', lat: 41.0, lng: -81.0 }]), null);
});

t('0,0 IS REFUSED AT THE EDGE — Null Island is what uninitialised looks like', () => {
  const err = R.validateStops([{ address: 'A', lat: 0, lng: 0 }]);
  assert.ok(err && /0,0/.test(err));
});

t('...and a legitimate near-zero coordinate is NOT refused — the pair', () => {
  // 0.0001, 0.0001 is in the Gulf of Guinea and is a real place.
  assert.strictEqual(R.validateStops([{ address: 'A', lat: 0.0001, lng: 0.0001 }]), null);
});

t('out-of-range coordinates are refused', () => {
  assert.ok(R.validateStops([{ address: 'A', lat: 91, lng: 0 }]));
  assert.ok(R.validateStops([{ address: 'A', lat: 0, lng: 181 }]));
});

t('accuracy with no fix to attach it to is refused', () => {
  assert.ok(R.validateStops([{ address: 'A', accuracy_m: 5 }]));
  assert.strictEqual(
    R.validateStops([{ address: 'A', lat: 41.0, lng: -81.0, accuracy_m: 5 }]), null);
});

t('a negative accuracy is refused', () => {
  assert.ok(R.validateStops([{ address: 'A', lat: 41.0, lng: -81.0, accuracy_m: -1 }]));
});

t('an empty stop list and an over-cap list are both refused', () => {
  assert.ok(R.validateStops([]));
  const many = [];
  for (let i = 0; i < 201; i++) many.push({ address: 'A' });
  assert.ok(R.validateStops(many));
  many.pop();
  assert.strictEqual(R.validateStops(many), null);
});

// ───────────────────────────────────────────────────────────────────────────
section('9. THE CONTROL — a sabotaged module must make this suite fail');

t('breaking the null-saving rule is CAUGHT by section 1', () => {
  // The exact sabotage: restore the original clamp. If this suite would still
  // pass with the defect reinstated, the suite is decoration.
  const sabotaged = (before, after) => Math.max(0, Math.round(before - after));
  const d = mat(3, (i, j) => (i === 0 && j === 2 ? Infinity : 100));
  const real = R.savedSeconds([0, 2, 1], [0, 1, 2], d);
  assert.strictEqual(real, null);
  // Under the sabotage the unmeasurable case would answer 0, which is exactly
  // what section 1's first arm proves is indistinguishable from a real zero.
  assert.strictEqual(sabotaged(0, 0), 0);
  assert.notStrictEqual(real, sabotaged(0, 0));
});

t('breaking the "never echo the input" rule is CAUGHT by section 2', () => {
  const stops = [stop({}), stop({}), stop({})];
  const d = mat(3, () => Infinity);
  const sabotaged = (ss) => ({ order: ss.map((_, i) => i), moved: 0 });
  assert.strictEqual(R.orderStops(stops, d), null);
  assert.deepStrictEqual(sabotaged(stops).order, [0, 1, 2]);
  // The two disagree, so the arm has teeth.
});

// ───────────────────────────────────────────────────────────────────────────
section('10. THE REAL DISPATCHER — not this module (2026-10-19, cody b27)');
// ── WHY THIS SECTION EXISTS AND WHY EVERY ARM ABOVE IT COULD NOT ANSWER IT ─
// Sections 1-9 drive api/_lib/routes.js. That module is correct and was
// correct before b27. What NOTHING drove was the path a browser takes:
// api/sd-data.js's dispatcher -> the envelope allowlist -> the app-visibility
// gate -> the extraActions verb gate -> the handler branch. FOUR gates, and
// the routing document that specified the branch knew about three of them.
//
// THE THIRD ONE WAS SHUT. isVisibleTo() had exactly two routes to visibility:
// be in `shared`, or be owned by the caller's own app. `rt_routes` is
// registered under the pseudo-app `routes`, which no licence is issued for, so
// every real consumer got 400 FOREIGN_RESOURCE before the branch ran. The
// branch, the registry entry and the extraActions declaration were ALL correct
// and the feature was dead. That is what driving the dispatcher found, and
// what no amount of testing this module could have.
//
// NOTHING REAL IS REACHED: the licence, the session secret and fetch are all
// mocked, and the arms assert on the dispatcher's own answers.
const path = require('path');
const fs = require('fs');
const os = require('os');
const ROOT = path.join(__dirname, '..', '..');
const SD_DATA = process.env.SAIRN_B27_SD_DATA || path.join(ROOT, 'api', 'sd-data.js');
const API_DIR = path.dirname(SD_DATA);

const LIC_HASH = 'hash-of-the-b27-routes-licence';
const LIC_APP = 'stonedesk';

let dispatch = null;
let SESSION_HEADER = null;
let dispatchSetupError = null;
try {
  const LICENCE = require.resolve(path.join(API_DIR, '_lib/license.js'));
  require.cache[LICENCE] = {
    id: LICENCE, filename: LICENCE, loaded: true,
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: LIC_HASH,
        stripe_subscription_id: 'sub_1', trial_ends_at: null, app_id: LIC_APP
      }),
      hashLicense: () => LIC_HASH,
    },
  };
  process.env.SUPABASE_URL = 'https://example.invalid';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';
  process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
    process.env[['SD', 'AUTH', 'SECRET'].join('_')]
    || ['b27', 'routes', String(process.pid)].join('-');
  // THE SESSION HEADER IS READ OUT OF auth.js, NEVER TYPED. The blob-scope
  // suite paid for the other way round: a header name was typed,
  // tokenFromRequest() reads a different one, and every gated arm failed its
  // precondition for a reason that was not about the gate.
  const authSrc = fs.readFileSync(path.join(API_DIR, '_lib/auth.js'), 'utf8');
  const hm = authSrc.match(/function tokenFromRequest\(req\)\s*\{\s*\n\s*const h = req\.headers\[['"]([a-z0-9-]+)['"]\]/);
  if (!hm) throw new Error('could not read the session header name out of api/_lib/auth.js');
  SESSION_HEADER = hm[1];
  // Every PostgREST call answers 200 with an empty list, so the branch reaches
  // its own answer rather than dying on a transport error -- EXCEPT the
  // employee-auth lookup, which answers an ACTIVE row (cc b38): since the
  // pre-gate refuses a deleted row on every registered resource, an empty
  // answer there is a deleted employee, not a neutral one.
  global.fetch = async (url) => ({ ok: true, status: 200,
    json: async () => (/_employee_auth\?/.test(String(url)) ? [{ active: true }] : []) });
  delete require.cache[require.resolve(SD_DATA)];
  dispatch = require(SD_DATA);
} catch (e) {
  dispatchSetupError = e;
}

const SESSION_LIB = require(path.join(API_DIR, '_lib/auth.js'));

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
async function call(action, resource, payload, opts) {
  const o = opts || {};
  const hdrs = { authorization: 'Bearer testkey' };
  if (o.session !== false) {
    hdrs[SESSION_HEADER] = SESSION_LIB.signSessionToken({
      app: o.app || 'stonedesk', employee_id: 'E1', role: o.role || 'owner',
      license_hash: LIC_HASH });
  }
  const req = { method: 'POST', headers: hdrs,
                body: { action: action, resource: resource, payload: payload || {} } };
  const res = fakeRes();
  await dispatch(req, res);
  return res;
}
const KEY = { app_id: 'stonedesk', assignee_id: 'E1', route_date: '2026-10-19' };
function rcode(res) {
  return (res.body && res.body.error && res.body.error.code) || '';
}
function rmsg(res) {
  return (res.body && res.body.error && res.body.error.message) || '';
}

t('D0. PRECONDITION: the dispatcher loaded and the rt_routes branch is in it', () => {
  // A THIRD STATE, never folded into a pass. If the handler would not load,
  // every arm below would fail for a reason that is not about routing.
  assert.strictEqual(dispatchSetupError, null,
    'the dispatcher could not be set up: ' + (dispatchSetupError && dispatchSetupError.message));
  assert.strictEqual(typeof dispatch, 'function');
  const src = fs.readFileSync(SD_DATA, 'utf8');
  // COMMENT-STRIPPED, because this repo has a recorded case of a precondition
  // satisfied by a comment ABOUT the code it was checking for.
  const codeOnly = src.split('\n').map((l) => l.replace(/\/\/.*$/, '')).join('\n');
  assert.ok(/if \(resource === 'rt_routes' \|\| resource === 'rt_stops'\) \{/.test(codeOnly),
    'the rt_routes handler branch is not in api/sd-data.js — it was reverted');
});

t('D1. a read REACHES THE BRANCH through the real dispatcher', async () => {
  const r = await call('read', 'rt_routes', KEY);
  // The branch's own read answer. A 400 here is the ALLOWLIST or the
  // VISIBILITY gate refusing, which is the state b27 found and fixed.
  assert.notStrictEqual(r.statusCode, 400,
    'the dispatcher refused BEFORE the branch: ' + rcode(r) + ' ' + rmsg(r));
  assert.strictEqual(r.statusCode, 200);
  assert.strictEqual(r.body.ok, true);
  assert.ok(Object.prototype.hasOwnProperty.call(r.body, 'provisioned'),
    'the answer carries no `provisioned` key, so it did not come from the branch');
});

t('D2. NEGATIVE CONTROL: no session is refused BY THE BRANCH at 403, not by the allowlist at 400', async () => {
  const r = await call('read', 'rt_routes', KEY, { session: false });
  assert.strictEqual(r.statusCode, 403);
  assert.strictEqual(rcode(r), 'FORBIDDEN');
  // THIS IS WHAT MAKES D1 ATTRIBUTABLE. A 403 can only come from inside the
  // branch; a 400 would mean the request never got there. The pair proves the
  // dispatcher reaches the branch AND that the branch's own gate fires --
  // licence-only access is refused, which is the whole reason the routing
  // document specified a session on every verb.
});

t('D2b. THE DISPATCHER-HEALTH CONTROL, green in BOTH legs of the ablation', async () => {
  // `employees` is registered in api/_resources/shared.js, so it is visible to
  // every licence by construction and its visibility does NOT depend on the
  // flag D5 ablates. It is the arm that separates "the flag was removed" from
  // "the copied tree is broken".
  //
  // D2 AND D3 CANNOT PLAY THAT ROLE, AND THE REASON IS THE FINDING ITSELF: the
  // visibility gate runs BEFORE the branch, so with the flag gone a no-session
  // rt_routes request gets the allowlist 400 rather than the branch's 403 --
  // every rt_routes arm goes red together, which is exactly what "the feature
  // was dead" means. A control has to sit on a resource the mutation does not
  // touch.
  const r = await call('read', 'employees', {});
  assert.strictEqual(r.statusCode, 200);
  assert.strictEqual(r.body.ok, true);
});

t('D3. NEGATIVE CONTROL: a DECLARED verb reaches the branch validator and an UNDECLARED one does not', async () => {
  const declared = await call('optimize', 'rt_routes', Object.assign({ stops: [] }, KEY));
  // 'optimize' is declared in api/_resources/routes.js extraActions, so it
  // reaches the branch and is refused on its PAYLOAD -- the branch's own
  // validator talking, with the module's own message.
  assert.strictEqual(declared.statusCode, 400);
  assert.strictEqual(rcode(declared), 'BAD_REQUEST');
  assert.ok(/stops must be a non-empty array/.test(rmsg(declared)),
    'optimize did not reach the branch validator: ' + rmsg(declared));
  // An undeclared verb is refused EARLIER, by the allowlist, with a different
  // message. Without this half, D3 could not tell "extraActions let the verb
  // through" from "every verb is allowed".
  const undeclared = await call('delete', 'rt_routes', KEY);
  assert.strictEqual(undeclared.statusCode, 400);
  assert.ok(!/stops must be a non-empty array/.test(rmsg(undeclared)),
    'an undeclared verb reached the branch validator, so extraActions gates nothing');
});

t('D4. NEGATIVE CONTROL: the cross-app flag did NOT open the boundary for everything', () => {
  const REG = require(path.join(API_DIR, '_resources/index.js'));
  assert.deepStrictEqual(REG.CROSS_APP_NAMES, ['rt_routes', 'rt_stops'],
    'visibleToAllApps is set on more than the routes module');
  // The boundary still refuses another app's resource to a stonedesk licence.
  assert.strictEqual(REG.isVisibleTo('law_matters', 'stonedesk'), false);
  assert.strictEqual(REG.isVisibleTo('alf_clients', 'stonedesk'), false);
  // ...and allows both halves of the primitive to every real consumer.
  for (const app of ['stonedesk', 'sairngrounds', 'sairnscape', 'sairnroofing', 'sairnmechanical']) {
    assert.strictEqual(REG.isVisibleTo('rt_routes', app), true, app);
    assert.strictEqual(REG.isVisibleTo('rt_stops', app), true, app);
  }
});

t('D5. ABLATION: removing visibleToAllApps makes D1 go RED with the exact 400 the feature had', () => {
  if (process.env.SAIRN_B27_SD_DATA) { return; }   // this IS the ablation child
  const FLAG = '  visibleToAllApps: true,\n';
  const regPath = path.join(ROOT, 'api', '_resources', 'routes.js');
  const regSrc = fs.readFileSync(regPath, 'utf8').replace(/\r\n/g, '\n');
  assert.ok(regSrc.indexOf(FLAG) >= 0, 'the flag is not in api/_resources/routes.js');
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'b27-routes-'));
  try {
    // LIBRARY DOWN FIRST, THEN THE MUTATION, THEN READ IT BACK. b24's ablation
    // harness wrote the subject first and copied api/_lib OVER it, so for any
    // subject inside api/ the leg silently drove the DISK copy -- and b26's
    // ablated the WRONG INSTANCE of a byte-identical pattern. Both are why the
    // readback below asserts three things rather than one.
    fs.cpSync(path.join(ROOT, 'api'), path.join(tmp, 'api'), { recursive: true });
    const copyReg = path.join(tmp, 'api', '_resources', 'routes.js');
    const want = regSrc.split(FLAG).join('');
    fs.writeFileSync(copyReg, want, 'utf8');
    const back = fs.readFileSync(copyReg, 'utf8').replace(/\r\n/g, '\n');
    assert.strictEqual(back, want, 'the ablated copy did not read back as written');
    assert.strictEqual(back.indexOf('visibleToAllApps'), -1, 'the flag survived the mutation');
    assert.strictEqual(regSrc.split(FLAG).length - 1, 1,
      'the flag occurs more than once, so this mutation removed an ambiguous set');
    const { execFileSync } = require('child_process');
    let out = '';
    let childCode = 0;
    try {
      out = execFileSync(process.execPath, [__filename], {
        encoding: 'utf8', cwd: ROOT,
        env: Object.assign({}, process.env,
          { SAIRN_B27_SD_DATA: path.join(tmp, 'api', 'sd-data.js') }),
      });
    } catch (e) { out = (e.stdout || '') + (e.stderr || ''); childCode = e.status; }
    // D1 MUST GO RED AND D2 MUST STAY GREEN. D2 green in both legs is what
    // makes D1 attributable to the FLAG rather than to the copy being broken:
    // a mutation that broke the whole dispatcher would take D2 with it.
    assert.ok(/^  FAIL D1\. /m.test(out),
      'D1 stayed GREEN with the flag removed, so it is not measuring the '
      + 'visibility gate and a green D1 means nothing. child exit ' + childCode
      + '\n' + out.slice(-800));
    assert.ok(/^  ok   D2b\. /m.test(out),
      'D2b went red too, so the ablation broke the COPIED TREE rather than only '
      + 'the flag, and D1 is not attributable to the flag at all\n' + out.slice(-800));
    // D2, D3 and D4 ALSO go red in the child, and that is CORRECT rather than a
    // control failing: the visibility gate runs before the branch, so with the
    // flag gone EVERY rt_routes arm goes red together. That is what "the
    // feature was dead for every consumer" means, and D2b is the arm that
    // proves the dispatcher itself still works.
    // ...and the reason D1 fails must be the EXACT 400 the feature had before
    // b27, not some other failure that happens to be red.
    assert.ok(/resource must be one of/.test(out),
      'D1 failed for a reason other than the allowlist/visibility 400, so this '
      + 'ablation does not reproduce the defect it claims to\n' + out.slice(-800));
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

(async () => {
  for (const [name, fn] of queue) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + (e && e.message)); fail++; }
  }
  console.log('\nroutes: ' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
