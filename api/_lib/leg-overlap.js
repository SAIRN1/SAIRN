'use strict';
/* api/_lib/leg-overlap.js -- the SAIRNlegacy server-side double-booking check,
 * in ONE place, for the resources that need it.
 *
 * ── WHY THIS FILE EXISTS, AND WHY IT IS NOT A SECOND COPY ──────────────────
 * This is the THIRD instance of one defect shape. b8 found it on
 * leg_merch_units (two devices, two stale caches, the same casket promised to
 * two families) and closed it with an atomic conditional PATCH. b9's own
 * survey of SAIRNlegacy found `leg_bookings` (closed 2026-10-13, inline in
 * api/sd-data.js) and then found `leg_clergybookings` with the SAME shape and
 * a different resource name.
 *
 * A fourth copy-paste was the obvious next move and it is the wrong one.
 * `api/sd-data.js:15154`'s own comment is the template, and the one thing a
 * copy would have got wrong is in the brief that commissioned this file:
 *
 *   ** THE STATUS LITERAL IS NOT THE SAME ON THE TWO RESOURCES. **
 *   leg_bookings exempts 'Cancelled'. leg_clergybookings skips 'Completed'
 *   (sairnlegacy.html:4820, `b.status==='Completed'`). A byte-identical
 *   propagation would have refused clergy bookings against rows that have
 *   already happened, and would have blocked a cancellation from being
 *   recorded. Cross-domain convention 7: byte-identical is not safe-in-context.
 *
 * So the literal is a PARAMETER with no default. A caller that does not name
 * one gets a thrown error, not a guess -- see `check()`.
 *
 * ── WHAT IS AND IS NOT CLOSED, carried over verbatim in substance ──────────
 * This is a READ-THEN-WRITE, not an atomic lock, and saying so is the point
 * rather than a caveat. The atomic close is a Postgres EXCLUDE constraint over
 * tstzrange and it cannot be written against these tables as they stand: the
 * window lives in `data` jsonb and `text::timestamptz` is STABLE, not
 * IMMUTABLE, so it is rejected in an index expression. It needs real
 * start/end columns or an /rpc/ function. Named as the follow-up, not
 * attempted here with no database to run it against.
 *
 * What IS closed is the stale-cache race -- minutes to hours wide, the one the
 * auditor found, the one that actually happens -- because both devices are now
 * checked against the SERVER's rows instead of their own. What remains is two
 * requests interleaving between this SELECT and the upsert: milliseconds, and
 * it needs two people to click Save in the same instant.
 *
 * ── A WINDOW THAT CANNOT BE READ IS A THIRD STATE ──────────────────────────
 * If an existing row's start_time or end_time does not parse, this cannot tell
 * whether it clashes, so it REFUSES and names the row -- PR §1.11 applied to
 * data instead of to a tool. Unreachable from the app today (both save paths
 * write toISOString()), which is why it has to be deliberate: an unparseable
 * row silently treated as non-overlapping is exactly how this control would
 * stop working.
 *
 * ── THE RETURN CONTRACT ────────────────────────────────────────────────────
 * `check()` returns NULL when the write may proceed, and a
 * `{ status, error: { code, message } }` object when it must not. It never
 * writes a response itself: the caller owns `res`, and a helper that answers
 * on behalf of a handler is a second place that decides a status code.
 */

// The interval test, kept as its own named function because it is the one line
// that must match the client's and is worth being able to point at.
// Half-open: touching ends do not overlap, which is what lets a 10:00-11:00
// and an 11:00-12:00 booking coexist.
function overlaps(aStart, aEnd, bStart, bEnd) {
  return aStart < bEnd && bStart < aEnd;
}

/**
 * spec:
 *   resource      'leg_bookings' | 'leg_clergybookings'
 *   idCol         the table's id column, e.g. 'booking_id'
 *   groupField    the field inside `data` that defines the shared thing being
 *                 double-booked: 'facility_id' or 'clergy_id'
 *   exemptStatus  THE STATUS LITERAL. Rows with this status are skipped, and a
 *                 payload carrying it is not checked at all. REQUIRED.
 *   codePrefix    error-code prefix, e.g. 'BOOKING'
 *   subjectLabel  how the 409 names the thing, e.g. 'That facility'
 *   windowNoun    how the 400 names what is missing, e.g. 'a facility'
 *   payload, licHash, rest, headers, enc, fetchImpl
 */
async function check(spec) {
  if (!spec || typeof spec.exemptStatus !== 'string' || !spec.exemptStatus) {
    // FAIL CLOSED, LOUDLY. A default here would be the copy-paste defect this
    // file exists to prevent, wearing a safer-looking costume: whichever
    // literal was chosen as the default would be silently wrong for the other
    // resource and nothing downstream could tell.
    throw new Error('leg-overlap: exemptStatus is required and has no default '
      + '-- leg_bookings exempts Cancelled, leg_clergybookings skips Completed');
  }
  const payload = spec.payload || {};
  const P = spec.codePrefix;
  const notProvisioned = {
    status: 503,
    error: {
      code: 'NOT_PROVISIONED',
      message: 'SAIRNlegacy data tables are not set up yet — run '
             + 'sql/sairnlegacy_data_schema.sql in Supabase first.'
    }
  };

  // THE EXEMPTION, AND IT RUNS BEFORE ANYTHING ELSE. A gate that refused a
  // cancellation because the booking it is cancelling overlaps something would
  // be the fix causing the harm; the same is true of marking a clergy booking
  // Completed after the service has happened.
  if (payload.status === spec.exemptStatus) return null;

  const startMs = Date.parse(payload.start_time);
  const endMs = Date.parse(payload.end_time);
  const groupValue = payload[spec.groupField];
  if (!groupValue || !Number.isFinite(startMs) || !Number.isFinite(endMs)
      || endMs <= startMs) {
    return {
      status: 400,
      error: {
        code: P + '_WINDOW_REQUIRED',
        message: 'This booking could not be saved to the server: it needs '
               + spec.windowNoun + ' and a start and end time, with the end '
               + 'after the start. Nothing was saved.'
      }
    };
  }

  const q = await spec.fetchImpl(spec.rest(
    spec.resource + '?license_hash=eq.' + spec.enc(spec.licHash) +
    '&data->>' + spec.groupField + '=eq.' + spec.enc(String(groupValue)) +
    '&select=' + spec.idCol + ',data'
  ), { headers: spec.headers });
  if (q.status === 404 || q.status === 400) return notProvisioned;
  const held = await q.json();
  if (!q.ok) return { upstream: held };

  const selfId = String(payload.id);
  const unreadable = [];
  const clash = (Array.isArray(held) ? held : []).find((row) => {
    if (String(row[spec.idCol]) === selfId) return false;
    const d = row.data || {};
    if (d.status === spec.exemptStatus) return false;
    const s = Date.parse(d.start_time), e = Date.parse(d.end_time);
    if (!Number.isFinite(s) || !Number.isFinite(e)) {
      unreadable.push(String(row[spec.idCol]));
      return false;
    }
    return overlaps(startMs, endMs, s, e);
  });

  if (clash) {
    const cd = clash.data || {};
    return {
      status: 409,
      error: {
        code: P + '_CONFLICT',
        message: spec.subjectLabel + ' is already booked ' + String(cd.start_time)
               + ' to ' + String(cd.end_time) + ' by booking '
               + String(clash[spec.idCol]) + ', made on another device. '
               + 'Nothing was saved -- pick a different time or '
               + spec.groupField.replace('_id', '') + '.'
      }
    };
  }

  // THE CONFLICT IS REPORTED FIRST AND THE INDETERMINATE SECOND, deliberately:
  // a definite clash is a better answer than "could not tell", and both are
  // refusals, so the caller is not worse off either way.
  if (unreadable.length) {
    return {
      status: 409,
      error: {
        code: P + '_CHECK_INDETERMINATE',
        message: 'This booking was NOT saved, because the double-booking check '
               + 'could not be completed: booking ' + unreadable.join(', ')
               + ' on this ' + spec.groupField.replace('_id', '') + ' has a '
               + 'start or end time the server cannot read, so it is not '
               + 'possible to tell whether your booking overlaps it. Report '
               + 'this -- it is a data problem, not something you did.'
      }
    };
  }

  return null;
}

// The two call sites' parameter sets, declared HERE rather than at the call
// site, so the pair can be read side by side and the differing literal is
// visible instead of being two screens apart in a 15,000-line file.
const SPECS = {
  leg_bookings: {
    groupField: 'facility_id',
    exemptStatus: 'Cancelled',
    codePrefix: 'BOOKING',
    subjectLabel: 'That facility',
    windowNoun: 'a facility'
  },
  leg_clergybookings: {
    groupField: 'clergy_id',
    // NOT 'Cancelled'. sairnlegacy.html:4820 skips 'Completed', and
    // advanceClergyBooking() is the only path that sets it: Requested ->
    // Confirmed -> Completed. There is no Cancelled status on this resource at
    // all, so copying leg_bookings' literal would have produced a gate that
    // skips nothing and refuses services that already happened.
    exemptStatus: 'Completed',
    codePrefix: 'CLERGY_BOOKING',
    subjectLabel: 'That clergy contact',
    windowNoun: 'a clergy contact'
  }
};

module.exports = { check: check, overlaps: overlaps, SPECS: SPECS };
