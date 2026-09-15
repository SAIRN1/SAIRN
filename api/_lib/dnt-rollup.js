// api/_lib/dnt-rollup.js
// ---------------------------------------------------------------------------
// SAIRNdental cross-location ROLL-UP -- the read side of the multi-location
// model, and a PURE function on purpose.
//
// WHAT THIS CLOSES. api/_lib/dnt-location.js shipped the write half on
// 2026-08-24 and named this explicitly in its own NOT IN SCOPE list: "any
// server-side cross-location aggregation". Its reasoning for the split is worth
// repeating because it is why this can be built now at all:
//
//   "Consolidated reporting, a per-location booking page, and a client-side
//    location selector can all be built later at the same cost. Attribution
//    cannot -- a charge, payment, AR entry or appointment recorded without a
//    location can never be assigned to one afterwards."
//
// The attribution was the deadline. This is the part that waited, and it is
// competitive-gap row SAIRNdental B2 -- the only in-house, un-gated item left
// across all four competitive-gap audits as of the 2026-09-15 re-derivation.
//
// ── PURE, AND THAT IS ITEM 92'S PATTERN, NOT A STYLE PREFERENCE ────────────
// Every fetch, every gate and every 503 lives in the caller. This file takes
// rows that have already been read and authorised and returns numbers. That is
// the functional-core / imperative-shell split item 92 applied to the two
// functions that decide money, and a roll-up is the same kind of thing: an
// arithmetic claim somebody will act on.
//
// ── THE FOUR RULES THAT MAKE THIS A REPORT RATHER THAN A FABRICATION ───────
//
// 1. UNASSIGNED IS A BUCKET, NEVER A LOCATION AND NEVER DROPPED.
//    Rows written before stampLocation shipped carry no location_id.
//    api/_lib/dental-bi.js already refuses to back-fill them: "Rows written
//    before that shipped have none and report null rather than being
//    back-filled with a default this feed would be inventing." Folding them
//    into LOC-DEFAULT would attribute a real charge to an office that may not
//    have taken it; dropping them would make the per-location figures sum to
//    less than the practice's real total with nothing saying so. They get their
//    own line.
//
// 2. A location_id ON ROWS BUT NOT IN THE REGISTRY IS ITS OWN BUCKET TOO.
//    A location removed from dnt_settings.data.locations still has history. It
//    is reported as an unregistered id, not merged and not hidden -- the
//    registry is the CURRENT list of offices, not the list of offices that ever
//    existed.
//
// 3. A RESOURCE THAT COULD NOT BE READ SUPPRESSES ITS OWN METRICS ENTIRELY.
//    This is the rule the whole file exists for. A roll-up that silently omits
//    an unprovisioned table prints "Production: $12,400" when the true answer
//    is "we could not read charges". The number looks authoritative and is
//    smaller than reality by an unknown amount, which is worse than no number.
//    Every metric therefore carries the resource it came from, and an
//    unreadable resource yields `null` plus a named entry in `unreadable`.
//    NEVER 0. Zero is a measurement.
//
// 4. EVERY FIGURE CARRIES ITS ROW COUNT. A total nobody can trace back to a
//    population is a total nobody can check.
//
// ── WHAT IT DELIBERATELY DOES NOT DO ──────────────────────────────────────
// No ranking, no "best performing location", no period-over-period change. Each
// of those is a judgement dressed as a number, and the competitive row asks for
// consolidated REPORTING, not a scoreboard. A caller that wants a comparison
// has the per-location figures and can make it explicitly.
// ---------------------------------------------------------------------------

'use strict';

const { DEFAULT_LOCATION_ID } = require('./dnt-location');

// The id used for rows that carry no location at all. Deliberately NOT
// DEFAULT_LOCATION_ID: that string means "the implicit single practice, stamped
// on purpose", and this means "nobody ever recorded one". Reusing it would
// destroy exactly the distinction rule 1 exists to keep.
const UNASSIGNED = '__unassigned__';
// Accumulator key separator. A NUL cannot occur in a location id --
// dnt-location.js validates them -- so `bucket + SEP + metric` is unambiguous
// where a hyphen or a colon would not be.
const SEP = '\u0000';

// Is this field READABLE as a number at all? Distinct from num() on purpose: a
// literal 0 is readable and means zero; a blank, absent or unparseable value is
// not readable and means nothing. num() collapses both to 0, which is right for
// the arithmetic and wrong for the disclosure -- finding 2.
function readable(v) {
  if (v === undefined || v === null) return false;
  if (typeof v === 'string' && v.trim() === '') return false;
  return Number.isFinite(typeof v === 'number' ? v : parseFloat(v));
}

// ── RULE 3, ONE LEVEL DOWN (2026-09-15) ────────────────────────────────────
// The independent review raised this and it was raised as a DISAGREEMENT
// rather than an oversight, because dnt-rollup.test.js:199 pins the zeroing
// deliberately and it is right to: a NaN would poison the whole total, which is
// worse. The objection was narrower. Rule 3 above says of an unreadable
// RESOURCE: "NEVER 0. Zero is a measurement." An unreadable FIELD was doing
// exactly that -- `100 + null + '' + '$1,200' + '12abc'` reported
// `{value:112, rows:5}` with `complete:true`, an authoritative figure short by
// an unknown amount, positively asserting it was whole.
//
// THE FIX IS NOT A CHANGE TO THE ARITHMETIC, which is why the existing arm
// still passes unchanged: an unreadable amount still contributes 0 and the row
// is still counted. What changes is that the roll-up now SAYS how many it could
// not read, per metric, and `complete` goes false when any were.
//
// `parseFloat` became `measureNumber` (api/_lib/safe-number.js) in the same
// edit, and that IS a behaviour change worth naming: parseFloat PARTIALLY
// PARSES, so `'12abc'` was silently 12 and `'1,200'` was silently 1. A
// plausible wrong number is worse than an unreadable one, because nothing looks
// wrong. Both are now counted as unread. `'not a number'` is NaN under both, so
// the pinned arm is unaffected.
const { measureNumber } = require('./safe-number');

// A row's location, as recorded. `data` is the jsonb blob every SAIRNdental
// resource stores; sd-data.js hands rows through with it merged or nested
// depending on the resource, so both shapes are read and neither is assumed.
function locationOf(row) {
  const v = (row && (row.location_id
    || (row.data && row.data.location_id)));
  return (typeof v === 'string' && v.trim()) ? v.trim() : UNASSIGNED;
}

/**
 * @param {object} input
 *   registry   {Array<{id,name}>}  dnt_settings.data.locations, or []
 *   sets       {object}  resource name -> { rows: [...] } | { unreadable: 'why' }
 *   metrics    {Array}   [{ key, resource, kind:'count'|'sum', field? , label }]
 * @returns {object} the roll-up, shaped so a caller cannot accidentally read a
 *   suppressed metric as zero.
 */
function rollup(input) {
  const registry = Array.isArray(input && input.registry) ? input.registry : [];
  const sets = (input && input.sets) || {};
  const metrics = Array.isArray(input && input.metrics) ? input.metrics : [];

  // ── which resources could not be read, by name ──────────────────────────
  const unreadable = {};
  Object.keys(sets).forEach((r) => {
    if (sets[r] && sets[r].unreadable) unreadable[r] = String(sets[r].unreadable);
  });

  // ── the buckets: every registered location, plus whatever the rows show ──
  const known = {};
  registry.forEach((l) => {
    const id = l && typeof l.id === 'string' ? l.id : null;
    if (id) known[id] = (l.name || id);
  });
  // DEFAULT_LOCATION_ID is a real bucket even when the registry is empty: it is
  // what a single-practice licence's rows are stamped with, and a roll-up that
  // showed nothing for the only office anybody has would be absurd.
  const buckets = {};
  const touch = (id) => {
    if (!buckets[id]) {
      buckets[id] = {
        location_id: id,
        name: id === UNASSIGNED ? null : (known[id] || null),
        registered: id === UNASSIGNED ? false : Object.prototype.hasOwnProperty.call(known, id),
        metrics: {}
      };
    }
    return buckets[id];
  };
  Object.keys(known).forEach(touch);
  // DEFAULT_LOCATION_ID IS SEEDED ONLY WHEN THE REGISTRY IS EMPTY, and the
  // first version of this file seeded it unconditionally. That was wrong in
  // both directions and the test suite caught it: a two-office practice got a
  // phantom third bucket for an office nobody has, AND that phantom was then
  // reported under `unregistered_location_ids`, which is supposed to mean "an
  // id on real rows that the registry does not know about" -- a signal that a
  // location was removed while it still had history. Manufacturing that signal
  // out of a seed would make the one thing on this report worth investigating
  // fire on every multi-location licence.
  //
  // If rows DO carry LOC-DEFAULT on a licence that has a registry, touch()
  // creates the bucket during the row pass and it is correctly flagged
  // unregistered -- because that genuinely means rows were written before the
  // offices were registered, which is exactly what somebody should see.
  if (Object.keys(known).length === 0) touch(DEFAULT_LOCATION_ID);

  // ── the arithmetic, IN TWO PASSES, AND THE SPLIT IS A REVIEW FINDING ────
  // FINDING 1 (Hank, independent review ce7764fa, 2026-09-15). The first
  // version seeded every bucket's cell INSIDE the per-metric loop, over the
  // buckets that existed WHEN THAT METRIC RAN. A later metric's row pass then
  // created a new bucket via touch() -- in the reported case the unassigned
  // one, from a single legacy charge with no location -- and that bucket never
  // got a cell for the EARLIER metrics. The totals loop treated a MISSING cell
  // identically to a SUPPRESSED one, so an ordinary two-office practice with
  // one pre-stamp charge reported patients and appointments as UNMEASURABLE
  // while `disclosure.unreadable` was EMPTY: a client could not even say which
  // resource had failed, because none had.
  //
  // MISSING AND SUPPRESSED ARE DIFFERENT FACTS. Missing means "no rows for this
  // resource in this bucket", which is 0 and is a measurement. Suppressed means
  // "could not read the resource", which is null. Collapsing them is rule 3
  // running backwards.
  //
  // IT WAS ORDER-DEPENDENT, which is what made it a defect rather than a
  // policy: the same data with the metric list in a different order reported a
  // real figure. A number that is a function of argument order is not a
  // measurement. So the bucket set is settled FIRST and the cells are
  // materialised once, over the final set.
  const acc = {};
  metrics.forEach((m) => {
    const set = sets[m.resource];
    if (!set || set.unreadable || !Array.isArray(set.rows)) return;
    set.rows.forEach((row) => {
      const b = touch(locationOf(row));
      const k = b.location_id + SEP + m.key;
      const cell = acc[k] || (acc[k] = { value: 0, rows: 0, unreadableRows: 0 });
      cell.rows += 1;
      if (m.kind === 'sum') {
        // FINDING 2 (same review). `num()` coerces a blank, absent or
        // unparseable amount to 0, so three unreadable charges among four
        // reported an authoritative total short by an unknown amount AND said
        // `complete: true`. That is rule 3's own sentence one level down -- at
        // the FIELD rather than at the RESOURCE.
        //
        // THE ARITHMETIC IS UNCHANGED, deliberately: an unreadable amount still
        // contributes 0 rather than poisoning the sum with NaN, and the arm
        // that pins that keeps passing. What changes is that the rows it could
        // not read are COUNTED AND NAMED, and `complete` goes false when there
        // are any. A figure short by an unknown amount may exist; positively
        // asserting that it is whole may not.
        const raw = row[m.field] !== undefined ? row[m.field]
          : (row.data && row.data[m.field]);
        if (!readable(raw)) cell.unreadableRows += 1;
        cell.value += num(raw);
      } else {
        cell.value += 1;
      }
    });
  });

  // PASS 2: materialise a cell on every bucket for every metric, over the FINAL
  // bucket set. A bucket created by a later metric's rows now gets an honest 0
  // for the earlier ones instead of nothing at all.
  metrics.forEach((m) => {
    const set = sets[m.resource];
    const dead = !set || set.unreadable || !Array.isArray(set.rows);
    Object.keys(buckets).forEach((id) => {
<<<<<<< HEAD
      buckets[id].metrics[m.key] = dead
        ? { value: null, rows: null, unread: null,
            unreadable: (set && set.unreadable) || 'resource not supplied' }
        : { value: 0, rows: 0, unread: 0 };
    });
    if (dead) return;
    set.rows.forEach((row) => {
      const b = touch(locationOf(row));
      if (!b.metrics[m.key]) b.metrics[m.key] = { value: 0, rows: 0, unread: 0 };
      const cell = b.metrics[m.key];
      cell.rows += 1;
      if (m.kind !== 'sum') { cell.value += 1; return; }
      const raw = row[m.field] !== undefined ? row[m.field]
        : (row.data && row.data[m.field]);
      const n = measureNumber(raw);
      // The row still counts -- it exists, it just carries no readable amount --
      // and the amount it could not read is now NAMED instead of being an
      // invisible 0 inside a total that calls itself complete.
      if (n === null) { cell.unread += 1; return; }
      cell.value += n;
=======
      if (dead) {
        buckets[id].metrics[m.key] = {
          value: null, rows: null,
          unreadable: (set && set.unreadable) || 'resource not supplied'
        };
        return;
      }
      const cell = acc[id + SEP + m.key];
      buckets[id].metrics[m.key] = cell
        ? { value: cell.value, rows: cell.rows, unreadable_rows: cell.unreadableRows }
        : { value: 0, rows: 0, unreadable_rows: 0 };
>>>>>>> 6fefae0e (fix(dnt_rollup,transport): both review findings closed, and a hand-written transport name that rotted against a correct refactor)
    });
  });

  // ── the totals line, which must agree with the buckets by construction ──
  // Summing the buckets rather than the rows is deliberate: two independent
  // passes over the same data is how a roll-up ends up with a total that does
  // not match its own rows.
  const ids = Object.keys(buckets).sort();
  const totals = {};
  let unreadableFieldRows = 0;
  metrics.forEach((m) => {
<<<<<<< HEAD
    let v = 0, rows = 0, unread = 0, suppressed = false;
=======
    let v = 0, rows = 0, bad = 0, suppressed = false;
>>>>>>> 6fefae0e (fix(dnt_rollup,transport): both review findings closed, and a hand-written transport name that rotted against a correct refactor)
    ids.forEach((id) => {
      const cell = buckets[id].metrics[m.key];
      // A MISSING cell can no longer happen -- pass 2 materialises one on every
      // bucket -- but the distinction stays explicit rather than being assumed
      // away, because assuming it away is what produced finding 1.
      if (!cell || cell.value === null) { suppressed = true; return; }
<<<<<<< HEAD
      v += cell.value; rows += cell.rows; unread += (cell.unread || 0);
=======
      v += cell.value; rows += cell.rows; bad += (cell.unreadable_rows || 0);
>>>>>>> 6fefae0e (fix(dnt_rollup,transport): both review findings closed, and a hand-written transport name that rotted against a correct refactor)
    });
    unreadableFieldRows += bad;
    totals[m.key] = suppressed
<<<<<<< HEAD
      ? { value: null, rows: null, unread: null,
          unreadable: unreadable[m.resource] || 'suppressed' }
      : { value: v, rows: rows, unread: unread };
=======
      ? { value: null, rows: null, unreadable: unreadable[m.resource] || 'suppressed' }
      : { value: v, rows: rows, unreadable_rows: bad };
>>>>>>> 6fefae0e (fix(dnt_rollup,transport): both review findings closed, and a hand-written transport name that rotted against a correct refactor)
  });
  // Rolled up across metrics so `complete` has one thing to read, and so a
  // caller can show the count without walking every bucket.
  const unreadFields = Object.keys(totals).reduce(
    (n, k) => n + (totals[k] && totals[k].unread ? totals[k].unread : 0), 0);

  const unassigned = buckets[UNASSIGNED] || null;
  return {
    locations: ids.filter((id) => id !== UNASSIGNED).map((id) => buckets[id]),
    // Hoisted out of `locations` so no caller can iterate offices and
    // accidentally render "__unassigned__" as one.
    unassigned: unassigned,
    totals: totals,
    // The honest header a client must be able to show. `complete` is false the
    // moment anything was unreadable OR any row lacks a location -- both make
    // the per-location figures an incomplete partition of the practice.
    disclosure: {
      complete: Object.keys(unreadable).length === 0
<<<<<<< HEAD
        && unreadFields === 0
        && !(unassigned && Object.keys(unassigned.metrics).some(
          (k) => unassigned.metrics[k] && unassigned.metrics[k].rows > 0)),
      unreadable: unreadable,
      // NAMED, because the row count alone is only a mitigation for somebody
      // who already suspects something. 4 rows against $100 is visible to a
      // reader who looks; `complete: true` was telling them not to.
      unread_fields: unreadFields,
=======
        && unreadableFieldRows === 0
        && !(unassigned && Object.keys(unassigned.metrics).some(
          (k) => unassigned.metrics[k] && unassigned.metrics[k].rows > 0)),
      unreadable: unreadable,
      // Named rather than only folded into `complete`: a client showing the
      // header has to be able to say WHY, and "3 of 4 charges carried no
      // readable amount" is a different sentence from "one office has no
      // location on its rows".
      unreadable_field_rows: unreadableFieldRows,
>>>>>>> 6fefae0e (fix(dnt_rollup,transport): both review findings closed, and a hand-written transport name that rotted against a correct refactor)
      unregistered_location_ids: ids.filter(
        (id) => id !== UNASSIGNED && !buckets[id].registered),
      registry_size: Object.keys(known).length
    }
  };
}

module.exports = { rollup, UNASSIGNED };
