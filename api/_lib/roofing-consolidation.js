// api/_lib/roofing-consolidation.js
// SAIRNroofing gap B5 -- multi-entity financial consolidation.
//
// PURE -- no I/O, no LLM, and NO MONEY ARITHMETIC. See "what this does not do".
//
// ── THE GAP, AND WHY rf_locations DID NOT ALREADY COVER IT ───────────────
// The 2026-08-26 competitive-gap audit's Tier-B item B5: multi-entity
// financial consolidation for PE rollups, with the note "rf_locations is
// attribution-only by design. Branch != entity." That note is correct and it
// is the whole problem. A rollup owns several LEGAL ENTITIES; each entity
// operates one or more BRANCHES. Roofing already had branches. It had no
// level above them, and no way to total the book by the thing that actually
// files a tax return.
//
// ── ATTRIBUTION IS DERIVED, NEVER STAMPED ────────────────────────────────
// The design decision this whole file turns on. entity_id lives ON THE
// LOCATION and nowhere else. No invoice, job, draw or schedule row carries
// one, and none ever should.
//
// The consequence is the point: MOVING A BRANCH BETWEEN ENTITIES MOVES ITS
// ENTIRE HISTORY, because history was never labelled -- it is attributed on
// read, through whichever entity the branch belongs to now. Stamping entity_id
// at write would freeze each row to the entity that owned the branch that day,
// so a divestiture would leave revenue permanently attributed to a company
// that no longer operates it, and the only fix would be a backfill migration
// over every financial table.
//
// The invariant that proves it: reassigning a location changes the BUCKETS and
// must not change the GRAND TOTAL. Every result carries `input_total`,
// `grand_total` and `reconciles` so a caller -- or a test -- can check that
// rather than trust it.
//
// ── WHAT THIS DOES NOT DO, DELIBERATELY ──────────────────────────────────
// It does not compute money. Callers hand it rows that already carry `total`,
// `paid` and `balance` from api/_lib/roofing-billing.js's summarizeInvoice(),
// which is the one implementation of invoice arithmetic on this platform. A
// second one here would be a figure that drifts from the Billing panel, which
// is the exact defect the platform keeps writing rules about. This engine's
// job is ATTRIBUTION AND ROLLUP; the money is somebody else's answer.
//
// ── UNASSIGNED IS A BUCKET, NOT A ROUNDING ERROR ─────────────────────────
// Two different things land outside every entity and they are kept APART:
//   * a location on file with no entity_id -- nobody has assigned it yet;
//   * a row naming a location that is NOT on file -- a dangling reference,
//     including every row still carrying the implicit 'LOC-DEFAULT'.
// Both are counted, both are shown, and neither is quietly folded into an
// entity or dropped from the total. A consolidation that silently loses rows
// is worse than no consolidation.

'use strict';

// The two non-entity buckets. Prefixed so they can never collide with a real
// contractor-generated entity_id.
const UNASSIGNED = '__unassigned';
const UNKNOWN_LOCATION = '__unknown_location';

function str(v) { return typeof v === 'string' ? v.trim() : ''; }
function num(v) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return (typeof n === 'number' && isFinite(n)) ? n : null;
}
function money(n) { return Math.round(n * 100) / 100; }

function emptyBucket(id, name, kind) {
  return {
    entity_id: id, name: name, kind: kind,
    location_ids: [], row_count: 0,
    total: 0, paid: 0, balance: 0
  };
}

// ── The rollup ───────────────────────────────────────────────────────────
// `rows` are already-summarised financial rows: { location_id, total, paid,
// balance }. `locations` map a location to its CURRENT entity. `entities` name
// them. Nothing else is consulted.
function consolidate(input) {
  input = input || {};
  const entities = Array.isArray(input.entities) ? input.entities : [];
  const locations = Array.isArray(input.locations) ? input.locations : [];
  const rows = Array.isArray(input.rows) ? input.rows : [];

  // location_id -> entity_id, from the location's CURRENT assignment. This one
  // lookup is the entire mechanism.
  const locEntity = Object.create(null);
  const locName = Object.create(null);
  locations.forEach(function (l) {
    const lid = str(l && l.location_id);
    if (!lid) return;
    locEntity[lid] = str(l.entity_id) || null;
    locName[lid] = str(l.name) || lid;
  });

  const buckets = Object.create(null);
  entities.forEach(function (e) {
    const eid = str(e && e.entity_id);
    if (!eid) return;
    buckets[eid] = emptyBucket(eid, str(e.legal_name) || eid, 'entity');
    buckets[eid].active = e.active !== false;
  });
  buckets[UNASSIGNED] = emptyBucket(UNASSIGNED, 'Unassigned — branch has no entity', 'unassigned');
  buckets[UNKNOWN_LOCATION] = emptyBucket(UNKNOWN_LOCATION, 'Unassigned — location not on file', 'unknown_location');

  // Locations listed per bucket even before any money lands, so an entity with
  // no invoices this period still shows the branches it owns rather than
  // vanishing from the consolidation.
  Object.keys(locEntity).forEach(function (lid) {
    const eid = locEntity[lid];
    const b = (eid && buckets[eid]) ? buckets[eid] : buckets[UNASSIGNED];
    if (b.location_ids.indexOf(lid) === -1) b.location_ids.push(lid);
  });

  let inputTotal = 0, inputPaid = 0, inputBalance = 0;
  const problems = [];
  let unreadable = 0;

  rows.forEach(function (r) {
    const t = num(r && r.total), p = num(r && r.paid), bal = num(r && r.balance);
    if (t === null) {
      // A row whose total cannot be read is COUNTED, never silently skipped --
      // a consolidation that quietly drops rows understates the book by
      // exactly the ones nobody can read.
      unreadable++;
      return;
    }
    inputTotal += t; inputPaid += (p || 0); inputBalance += (bal === null ? t - (p || 0) : bal);

    const lid = str(r.location_id);
    let b;
    if (!lid || !(lid in locEntity)) {
      // Includes every row still carrying the implicit 'LOC-DEFAULT' when no
      // such location row exists. Named as its own bucket rather than merged
      // with "no entity assigned", because the fixes differ: one is assign the
      // branch, the other is create the branch.
      b = buckets[UNKNOWN_LOCATION];
    } else {
      const eid = locEntity[lid];
      b = (eid && buckets[eid]) ? buckets[eid] : buckets[UNASSIGNED];
      if (eid && !buckets[eid]) {
        // The location names an entity that is not on file. Not silently
        // treated as unassigned without saying so.
        if (problems.indexOf('location "' + lid + '" names entity "' + eid + '", which is not on file') === -1) {
          problems.push('location "' + lid + '" names entity "' + eid + '", which is not on file');
        }
      }
    }
    if (b.location_ids.indexOf(lid || '(none)') === -1) b.location_ids.push(lid || '(none)');
    b.row_count++;
    b.total += t; b.paid += (p || 0);
    b.balance += (bal === null ? t - (p || 0) : bal);
  });

  const list = Object.keys(buckets).map(function (k) {
    const b = buckets[k];
    b.total = money(b.total); b.paid = money(b.paid); b.balance = money(b.balance);
    return b;
  });

  const grandTotal = money(list.reduce(function (s, b) { return s + b.total; }, 0));
  if (unreadable) {
    problems.push(unreadable + ' row(s) had no readable total and are in NO bucket -- the consolidation is short by them');
  }

  return {
    ok: true,
    entities: list.filter(function (b) { return b.kind === 'entity'; })
      .sort(function (a, b) { return a.name < b.name ? -1 : a.name > b.name ? 1 : 0; }),
    // Kept out of `entities` so a caller cannot total the list and think it is
    // the whole book.
    unassigned: list.filter(function (b) { return b.kind !== 'entity'; }),
    grand_total: grandTotal,
    grand_paid: money(list.reduce(function (s, b) { return s + b.paid; }, 0)),
    grand_balance: money(list.reduce(function (s, b) { return s + b.balance; }, 0)),
    // THE INVARIANT, stated in the response rather than assumed. Reassigning a
    // location must change the buckets and leave this alone. A caller can
    // check it; the tests do.
    input_total: money(inputTotal),
    reconciles: money(inputTotal) === grandTotal,
    rows_in: rows.length,
    rows_unreadable: unreadable,
    problems: problems
  };
}

// ── What a location move would do ────────────────────────────────────────
// Answers the question before somebody clicks: which entity does this branch
// belong to now, which would it belong to, and how much of the book moves.
// It does NOT perform the move -- the move is an ordinary write to the
// location row, and this is the preview.
function previewMove(input) {
  input = input || {};
  const lid = str(input.location_id);
  if (!lid) return { ok: false, error: { code: 'NO_LOCATION', message: 'no location_id supplied' } };
  const to = str(input.to_entity_id) || null;

  const before = consolidate(input);
  const moved = (Array.isArray(input.locations) ? input.locations : []).map(function (l) {
    return (str(l && l.location_id) === lid) ? Object.assign({}, l, { entity_id: to }) : l;
  });
  const after = consolidate(Object.assign({}, input, { locations: moved }));

  const find = function (res, id) {
    const all = res.entities.concat(res.unassigned);
    for (let i = 0; i < all.length; i++) if (all[i].entity_id === id) return all[i];
    return null;
  };
  const fromEntity = (function () {
    const l = (Array.isArray(input.locations) ? input.locations : [])
      .filter(function (x) { return str(x && x.location_id) === lid; })[0];
    return l ? (str(l.entity_id) || null) : null;
  })();

  const fromB = find(before, fromEntity || UNASSIGNED);
  const toB = find(after, to || UNASSIGNED);
  return {
    ok: true,
    location_id: lid,
    from_entity_id: fromEntity,
    to_entity_id: to,
    amount_moving: fromB ? money((fromB.total) - ((find(after, fromEntity || UNASSIGNED) || { total: 0 }).total)) : null,
    from_total_before: fromB ? fromB.total : null,
    to_total_after: toB ? toB.total : null,
    // The whole point, restated per move: the book does not change size.
    grand_total_before: before.grand_total,
    grand_total_after: after.grand_total,
    grand_total_unchanged: before.grand_total === after.grand_total
  };
}

// ── The filter, living next to the rule it must agree with ───────────────
// Added 2026-09-02 when the money panels were made entity-aware. It is HERE
// and not in each endpoint on purpose: "which entity does this row belong to"
// must have exactly one answer, and a filter that resolved it a second way
// would eventually disagree with the consolidation totals on the same screen.
//
// Returns a predicate over a location_id. `wanted` is an entity_id, or the
// UNASSIGNED bucket, or null/'' meaning no filter at all.
//
// UNASSIGNED deliberately matches BOTH shapes the consolidation keeps apart --
// a branch with no entity, and a row whose location is not on file. On the
// consolidation board those are two rows because the fixes differ; as a FILTER
// they are one selection, because "show me what is not attributed to anybody"
// is a single question. The board is where the distinction earns its keep.
function entityMatcher(input) {
  input = input || {};
  const wanted = str(input.entity_id);
  if (!wanted) return function () { return true; };
  const locEntity = Object.create(null);
  (Array.isArray(input.locations) ? input.locations : []).forEach(function (l) {
    const lid = str(l && l.location_id);
    if (lid) locEntity[lid] = str(l.entity_id) || null;
  });
  if (wanted === UNASSIGNED || wanted === UNKNOWN_LOCATION) {
    return function (locationId) {
      const lid = str(locationId);
      return !lid || !(lid in locEntity) || !locEntity[lid];
    };
  }
  return function (locationId) {
    const lid = str(locationId);
    return !!lid && locEntity[lid] === wanted;
  };
}

module.exports = {
  UNASSIGNED,
  UNKNOWN_LOCATION,
  consolidate,
  previewMove,
  entityMatcher
};
