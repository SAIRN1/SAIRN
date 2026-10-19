// api/_lib/routes.js
// THE SHARED ROUTING PRIMITIVE — ordering a day's stops for one assignee.
//
// Scope and the reasoning behind every decision here:
//   docs/2026-10-19-fourth-b33-routing-primitive-scope.md
// Schema, with the same argument beside the columns it constrains:
//   sql/rt_routes_schema.sql
// Criticality — BOTH resources are Tier A on confidentiality, written before
// this file existed:
//   docs/CRITICALITY-TIERS.md, section `routes`
//
// ── WHY THIS EXISTS AT ALL, AND WHY IT IS NOT NEW CODE ─────────────────────
// A complete implementation of this already existed. Commit 35169ea2
// (2026-06-18) added `?action=maps-optimize` to api/bridge.js: a
// nearest-neighbour ordering over Google Route Matrix drive times. It is NOT
// an ancestor of `main` — `git merge-base --is-ancestor 35169ea2 HEAD` fails,
// and `git branch -a --contains` names only origin/claude/lucid-ptolemy-b73vu0.
// Meanwhile stonedesk.html:12927 has been POSTing to that action on the live
// deployment the whole time and getting HTTP 401, under an error message that
// blames a Maps API key the request never reaches.
//
// So this module is a RECOVERY plus three corrections, not an invention. The
// corrections are named where they are made: `savedSeconds` returning null
// rather than a floored zero, the three-state `basis`, and `locked`.
//
// ── WHAT IS DELIBERATELY NOT HERE ──────────────────────────────────────────
// No geocoding. No live traffic. No time windows. No multi-day. No capacity
// constraints. NO CREW ASSIGNMENT — this orders the stops a human already
// assigned; deciding WHO goes is a different problem with a different failure
// mode and must not ride along in the same scope. No map image rendering.
//
// ── THE SHAPE: PURE CORE, INJECTED EDGES ───────────────────────────────────
// Everything that decides anything is a pure function over plain data, in the
// first half of this file. The I/O half takes its `fetch`, its REST base and
// its headers as arguments. That is not a testing convenience — it is why
// api/_lib/routes.test.js can drive the ordering, the three-state basis and
// every refusal with no database and no network, which is the only way those
// arms get exercised at all.

'use strict';

// ───────────────────────────────────────────────────────────────────────────
// THE THREE BASES, AND WHY 'unavailable' IS ONE OF THEM
//
// 'drive-matrix'  a real drive-time matrix answered and the order comes from it
// 'great-circle'  a straight-line ordering — a LEGITIMATE second basis, but
//                 only while it is labelled as one. It must never be allowed
//                 to pass as drive time, which is why it is a distinct value
//                 rather than a flag on 'drive-matrix'.
// 'manual'        a human ordered it. Not an optimisation and never recorded
//                 as one.
//
// 'unavailable' is NOT in this list, because it is not a basis for a stored
// order — it is the answer "I could not run". It appears in the RESPONSE and
// never in rt_routes.source. CLAUDE.md states the rule this implements: could
// not run is a third state and is never folded into a pass.
// ───────────────────────────────────────────────────────────────────────────
const STORED_BASES = ['manual', 'drive-matrix', 'great-circle'];

const EARTH_RADIUS_M = 6371008.8; // WGS84 mean radius, same constant as
                                  // sairngrounds.html:2793 gcdHaversineM().

// The accuracy ceiling above which a device fix is not usable for ordering.
// Taken from SAIRNgrounds' own rule rather than invented: it refuses to report
// a distance at all once the COMBINED band exceeds 25 m, on the ground that
// +/-27 yards is wider than the gap between golf clubs and is noise wearing a
// distance's clothes. The same logic holds here for a different reason — two
// stops whose fixes are that loose cannot be reliably ordered against each
// other, and an ordering that pretends otherwise is worse than no ordering.
const MAX_COMBINED_ACCURACY_M = 25;

function isFiniteNum(n) {
  return typeof n === 'number' && isFinite(n);
}

// Great-circle distance in metres. Haversine on the WGS84 mean radius.
function haversineM(a, b) {
  const toRad = Math.PI / 180;
  const lat1 = a.lat * toRad, lat2 = b.lat * toRad;
  const dLat = (b.lat - a.lat) * toRad;
  const dLng = (b.lng - a.lng) * toRad;
  const h = Math.sin(dLat / 2) * Math.sin(dLat / 2)
          + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

// THE ERROR BANDS ARE ADDED, NEVER AVERAGED. Averaging would understate the
// one number that must not flatter — this is SAIRNgrounds' rule, lifted
// deliberately rather than re-derived. A pair with no accuracy recorded is
// treated as usable: absent is not the same as bad, and refusing an ordinary
// geocoded address because it carries no device accuracy would refuse almost
// every real stop.
function pairIsUsable(a, b) {
  if (!isFiniteNum(a.lat) || !isFiniteNum(a.lng)) return false;
  if (!isFiniteNum(b.lat) || !isFiniteNum(b.lng)) return false;
  const accA = isFiniteNum(a.accuracy_m) ? a.accuracy_m : 0;
  const accB = isFiniteNum(b.accuracy_m) ? b.accuracy_m : 0;
  return (accA + accB) <= MAX_COMBINED_ACCURACY_M;
}

// ───────────────────────────────────────────────────────────────────────────
// WHICH STOPS MAY MOVE
//
// Three kinds of stop hold their position and the reasons are different:
//   status 'done'    — it already happened. Reordering history is nonsense.
//   status 'skipped' — a decision was made about it; moving it would un-make
//                      that decision silently.
//   locked true      — a real day has fixed appointments. An optimiser that
//                      moves a 9 AM commitment to save four minutes of driving
//                      is worse than no optimiser.
//
// StoneDesk's existing fmRunOptimize already does the `done` half
// (stonedesk.html:12920-12923). That behaviour is PRESERVED here, not
// reinvented — the `locked` half is the addition.
// ───────────────────────────────────────────────────────────────────────────
function isPinned(stop) {
  return stop.locked === true || stop.status === 'done' || stop.status === 'skipped';
}

// ───────────────────────────────────────────────────────────────────────────
// orderStops(stops, durations) -> { order, moved } | null
//
// `stops`     array in CURRENT seq order.
// `durations` NxN matrix of seconds, durations[i][j] = i -> j, over the SAME
//             indices as `stops`. A missing/unreachable pair is Infinity.
//
// Returns an array of INDICES INTO `stops` in the new order. Pinned stops keep
// their exact index position; the movable ones are nearest-neighboured into
// the remaining slots, in slot order.
//
// RETURNS null WHEN IT CANNOT ORDER. It never falls back to the as-given order
// and reports that as a result — a caller receiving an array is receiving a
// computed ordering, always. That distinction is the whole point of the
// function's contract and is asserted in both directions by the test suite.
// ───────────────────────────────────────────────────────────────────────────
function orderStops(stops, durations) {
  if (!Array.isArray(stops) || stops.length < 2) return null;
  const n = stops.length;
  if (!Array.isArray(durations) || durations.length !== n) return null;
  for (const row of durations) {
    if (!Array.isArray(row) || row.length !== n) return null;
  }

  const slots = [];        // index -> true when the slot is free to be filled
  const result = new Array(n).fill(-1);
  for (let i = 0; i < n; i++) {
    if (isPinned(stops[i])) result[i] = i; else slots.push(i);
  }
  if (slots.length < 2) return null;  // nothing to decide

  const movable = slots.slice();
  const unvisited = new Set(movable);

  // THE CHAIN STARTS FROM THE LAST PINNED STOP BEFORE THE FIRST FREE SLOT,
  // when there is one — the crew is physically there, so the first hop is from
  // where they are rather than from an arbitrary stop. With no preceding
  // pinned stop the chain starts at the movable stop that was already first,
  // which preserves the caller's own choice of opening stop rather than
  // substituting one.
  let from = null;
  for (let i = slots[0] - 1; i >= 0; i--) {
    if (result[i] !== -1) { from = i; break; }
  }
  if (from === null) {
    from = movable[0];
    unvisited.delete(from);
    result[slots[0]] = from;
  }

  let anyRealHop = false;
  for (const slot of slots) {
    if (result[slot] !== -1) continue;
    let best = -1, bestDur = Infinity;
    for (const j of unvisited) {
      const d = durations[from][j];
      if (isFiniteNum(d) && d < bestDur) { bestDur = d; best = j; }
    }
    if (best === -1) {
      // EVERY REMAINING PAIR IS UNREACHABLE FROM HERE. Take the next unvisited
      // in the caller's original order rather than dropping it — a stop the
      // optimiser cannot place is still a stop the crew has to make. This is
      // recorded, not silent: `moved` below reports how much was actually
      // decided, so a caller can tell a real ordering from a shuffle.
      best = movable.find((j) => unvisited.has(j));
      if (best === undefined || best === -1) break;
    } else {
      anyRealHop = true;
    }
    unvisited.delete(best);
    result[slot] = best;
    from = best;
  }

  if (result.some((v) => v === -1)) return null;
  // NOT ONE REACHABLE PAIR IN THE WHOLE SET. That is not an ordering, it is the
  // input handed back, and returning it would be a reordering we did not
  // compute.
  if (!anyRealHop) return null;

  let moved = 0;
  for (let i = 0; i < n; i++) if (result[i] !== i) moved++;
  return { order: result, moved: moved };
}

// ───────────────────────────────────────────────────────────────────────────
// savedSeconds(originalIdx, newIdx, durations) -> number | null
//
// NULL MEANS NOT COMPUTED, AND THAT IS THE WHOLE POINT OF THIS FUNCTION.
//
// The 2026-06-18 implementation this was recovered from computed:
//     Math.max(0, Math.round((totalOriginal - totalOptimized) / 60))
// which renders "we could not tell" and "we saved nothing" as the SAME figure
// on screen. They are different facts. A route whose matrix had three
// unreachable pairs and a route that was already optimal both showed "0 min",
// and a reader could not tell which they were looking at.
//
// Here: if any leg of EITHER path is not a finite duration, the comparison is
// not available and the answer is null. A caller MUST render null as no claim
// at all — never as "saves ~0 min".
//
// A NEGATIVE RESULT IS RETURNED AS-IS AND IS NOT CLAMPED. A nearest-neighbour
// heuristic can genuinely produce a worse path than the one a human chose, and
// a caller that stores a negative saving has learned something true. Clamping
// is how the original lost the distinction in the first place.
// ───────────────────────────────────────────────────────────────────────────
function pathSeconds(idx, durations) {
  let total = 0;
  for (let i = 0; i < idx.length - 1; i++) {
    const d = durations[idx[i]][idx[i + 1]];
    if (!isFiniteNum(d)) return null;
    total += d;
  }
  return total;
}

function savedSeconds(originalIdx, newIdx, durations) {
  if (!Array.isArray(originalIdx) || !Array.isArray(newIdx)) return null;
  if (originalIdx.length !== newIdx.length || originalIdx.length < 2) return null;
  const before = pathSeconds(originalIdx, durations);
  const after = pathSeconds(newIdx, durations);
  if (before === null || after === null) return null;
  return Math.round(before - after);
}

// ───────────────────────────────────────────────────────────────────────────
// greatCircleMatrix(stops) -> matrix | null
//
// The second basis. Seconds are NOT invented from distance — no assumed speed
// appears anywhere in this file, because a speed would turn a straight-line
// distance into a fabricated drive time and that is precisely the lie the
// basis label exists to prevent. The matrix carries METRES, and the caller
// that uses it records basis 'great-circle' and stores NO saved_seconds.
//
// Returns null when fewer than two stops carry a usable fix — a partial
// straight-line ordering over the subset that happens to be geocoded would be
// an ordering of a different set of stops than the one asked about.
// ───────────────────────────────────────────────────────────────────────────
function greatCircleMatrix(stops) {
  if (!Array.isArray(stops) || stops.length < 2) return null;
  const n = stops.length;
  let usablePairs = 0;
  const m = [];
  for (let i = 0; i < n; i++) {
    m.push(new Array(n).fill(Infinity));
  }
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      if (i === j) { m[i][j] = 0; continue; }
      if (pairIsUsable(stops[i], stops[j])) {
        m[i][j] = haversineM(stops[i], stops[j]);
        usablePairs++;
      }
    }
  }
  return usablePairs > 0 ? m : null;
}

// ───────────────────────────────────────────────────────────────────────────
// driveMatrix(addresses, deps) -> {matrix} | {unavailable: reason}
//
// Google Route Matrix. The key is read from the environment here and NEVER
// returned, logged or echoed — the 2026-06-18 original got this right and the
// reason is kept with it: it used the standard computeRouteMatrix endpoint
// rather than the experimental optimizeWaypointOrder, because that feature is
// gated behind a manual Google Support enablement request and a nearest-
// neighbour ordering over real drive times does not depend on a flag that
// might not be turned on for this project.
//
// EVERY FAILURE PATH NAMES ITSELF. 'no-key', 'upstream-status',
// 'upstream-shape', 'network' and 'no-reachable-pair' are distinct reasons,
// because "could not optimise" with no reason is the shape that sent a reader
// to check a Vercel environment variable that was not the problem — see
// stonedesk.html's existing catch arm, which this replaces.
// ───────────────────────────────────────────────────────────────────────────
const ROUTE_MATRIX_URL =
  'https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix';

async function driveMatrix(addresses, deps) {
  const d = deps || {};
  const doFetch = d.fetch || (typeof fetch === 'function' ? fetch : null);
  const key = d.apiKey !== undefined
    ? d.apiKey
    : (typeof process !== 'undefined' && process.env
        ? process.env.GOOGLE_MAPS_API_KEY : undefined);

  if (!key) return { unavailable: 'no-key' };
  if (!doFetch) return { unavailable: 'network' };
  if (!Array.isArray(addresses) || addresses.length < 2) {
    return { unavailable: 'no-reachable-pair' };
  }

  const points = addresses.map((a) => ({ waypoint: { address: String(a) } }));
  let res;
  try {
    res = await doFetch(ROUTE_MATRIX_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': key,
        'X-Goog-FieldMask': 'originIndex,destinationIndex,duration,condition'
      },
      body: JSON.stringify({
        origins: points, destinations: points, travelMode: 'DRIVE'
      })
    });
  } catch (e) {
    return { unavailable: 'network' };
  }
  if (!res || !res.ok) return { unavailable: 'upstream-status' };

  let elements;
  try { elements = await res.json(); } catch (e) {
    return { unavailable: 'upstream-shape' };
  }
  if (!Array.isArray(elements)) return { unavailable: 'upstream-shape' };

  const n = addresses.length;
  const m = [];
  for (let i = 0; i < n; i++) m.push(new Array(n).fill(Infinity));
  let reachable = 0;
  for (const el of elements) {
    if (!el || el.condition !== 'ROUTE_EXISTS') continue;
    const oi = el.originIndex, di = el.destinationIndex;
    if (!Number.isInteger(oi) || !Number.isInteger(di)) continue;
    if (oi < 0 || oi >= n || di < 0 || di >= n) continue;
    const secs = parseInt(String(el.duration).replace('s', ''), 10);
    if (!isFiniteNum(secs)) continue;
    m[oi][di] = secs;
    if (oi !== di) reachable++;
  }
  for (let i = 0; i < n; i++) m[i][i] = 0;
  if (reachable === 0) return { unavailable: 'no-reachable-pair' };
  return { matrix: m };
}

// ───────────────────────────────────────────────────────────────────────────
// optimize(stops, deps) -> the response object
//
// THE THREE STATES, AND THEY ARE NEVER FOLDED:
//
//   { basis:'drive-matrix', order, saved_seconds, moved }
//   { basis:'great-circle', order, saved_seconds:null, moved }
//       — a real ordering from straight-line distance. NO saved_seconds, ever:
//         there is no drive time to have saved, and emitting one would be the
//         fabrication the basis label exists to prevent.
//   { basis:'unavailable', reason, order:null, saved_seconds:null }
//       — THE STORED ORDER DOES NOT CHANGE. `order` is null rather than the
//         input echoed back, so a caller cannot mistake "unchanged" for
//         "confirmed optimal".
// ───────────────────────────────────────────────────────────────────────────
async function optimize(stops, deps) {
  const d = deps || {};
  if (!Array.isArray(stops) || stops.length < 2) {
    return { basis: 'unavailable', reason: 'too-few-stops', order: null, saved_seconds: null };
  }
  const movable = stops.filter((s) => !isPinned(s));
  if (movable.length < 2) {
    return { basis: 'unavailable', reason: 'nothing-movable', order: null, saved_seconds: null };
  }

  const identity = stops.map((_, i) => i);
  const drive = await driveMatrix(stops.map((s) => s.address), d);

  if (drive.matrix) {
    const ordered = orderStops(stops, drive.matrix);
    if (ordered) {
      return {
        basis: 'drive-matrix',
        order: ordered.order,
        moved: ordered.moved,
        saved_seconds: savedSeconds(identity, ordered.order, drive.matrix)
      };
    }
    // The matrix answered but produced no orderable set. That is a different
    // fact from the matrix not answering, and it keeps its own reason.
    return {
      basis: 'unavailable', reason: 'not-orderable', order: null, saved_seconds: null
    };
  }

  // SECOND BASIS. Only reached because the first did not answer, and it is
  // labelled so a reader can never mistake it for drive time.
  const gc = greatCircleMatrix(stops);
  if (gc) {
    const ordered = orderStops(stops, gc);
    if (ordered) {
      return {
        basis: 'great-circle',
        order: ordered.order,
        moved: ordered.moved,
        // NOT a saving. Straight-line metres are not seconds and no assumed
        // speed exists in this file to turn one into the other.
        saved_seconds: null,
        drive_unavailable_because: drive.unavailable
      };
    }
  }

  return {
    basis: 'unavailable',
    reason: drive.unavailable,
    order: null,
    saved_seconds: null
  };
}

// ───────────────────────────────────────────────────────────────────────────
// applyOrder(stops, order) -> stops in the new order, with seq rewritten 1..n
// Pure. The seq rewrite is here rather than at the call site so that the one
// invariant this table exists to hold — seq is 1-based, contiguous and unique
// within a route — is enforced in exactly one place.
// ───────────────────────────────────────────────────────────────────────────
function applyOrder(stops, order) {
  if (!Array.isArray(order) || order.length !== stops.length) return null;
  const seen = new Set();
  for (const i of order) {
    if (!Number.isInteger(i) || i < 0 || i >= stops.length || seen.has(i)) return null;
    seen.add(i);
  }
  return order.map((srcIdx, pos) =>
    Object.assign({}, stops[srcIdx], { seq: pos + 1 }));
}

// ───────────────────────────────────────────────────────────────────────────
// VALIDATION — the refusals, each with its own message
//
// Separate from the handler so the test suite drives them directly. A refusal
// that is only reachable through a live request is a refusal nobody tests.
// ───────────────────────────────────────────────────────────────────────────
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function validateRouteKey(payload) {
  const p = payload || {};
  if (!p.app_id || typeof p.app_id !== 'string') return 'app_id is required';
  if (!p.assignee_id || typeof p.assignee_id !== 'string') return 'assignee_id is required';
  if (typeof p.route_date !== 'string' || !ISO_DATE.test(p.route_date)) {
    return 'route_date is required as YYYY-MM-DD';
  }
  return null;
}

function validateStops(stops) {
  if (!Array.isArray(stops) || stops.length === 0) return 'stops must be a non-empty array';
  if (stops.length > 200) return 'stops is capped at 200 per route';
  for (let i = 0; i < stops.length; i++) {
    const s = stops[i] || {};
    if (typeof s.address !== 'string' || !s.address.trim()) {
      return 'stops[' + i + '].address is required';
    }
    if (s.address.length > 500) return 'stops[' + i + '].address is over 500 chars';
    const hasLat = s.lat !== undefined && s.lat !== null;
    const hasLng = s.lng !== undefined && s.lng !== null;
    // BOTH OR NEITHER, mirroring rtstops_coords_are_a_pair. A lone coordinate
    // is not a partial fix, it is a wrong one.
    if (hasLat !== hasLng) return 'stops[' + i + '] has one coordinate of a pair';
    if (hasLat) {
      if (!isFiniteNum(s.lat) || s.lat < -90 || s.lat > 90) return 'stops[' + i + '].lat out of range';
      if (!isFiniteNum(s.lng) || s.lng < -180 || s.lng > 180) return 'stops[' + i + '].lng out of range';
      // 0,0 IS REFUSED AT THE EDGE AS WELL AS AT THE DATABASE. Null Island is
      // what an uninitialised coordinate looks like, and a stop there is
      // indistinguishable from a stop in the Gulf of Guinea.
      if (s.lat === 0 && s.lng === 0) return 'stops[' + i + '] is at 0,0 — send null coordinates instead';
    }
    if (s.accuracy_m !== undefined && s.accuracy_m !== null) {
      if (!isFiniteNum(s.accuracy_m) || s.accuracy_m < 0) return 'stops[' + i + '].accuracy_m is not a non-negative number';
      if (!hasLat) return 'stops[' + i + '] has accuracy_m with no fix to attach it to';
    }
  }
  return null;
}

module.exports = {
  STORED_BASES,
  MAX_COMBINED_ACCURACY_M,
  EARTH_RADIUS_M,
  haversineM,
  pairIsUsable,
  isPinned,
  orderStops,
  pathSeconds,
  savedSeconds,
  greatCircleMatrix,
  driveMatrix,
  optimize,
  applyOrder,
  validateRouteKey,
  validateStops,
  ROUTE_MATRIX_URL
};
