// api/_lib/leg-roles.js
//
// SAIRNlegacy role granularity: ONE data table, read by ONE function.
//
// ── WHY THIS FILE EXISTS (2026-10-14, fourth b15 spec) ────────────────────
// MEASURED, not asserted: SAIRNlegacy had THREE roles and NO per-resource
// role check anywhere.
//
//     grep -n "sairnlegacy:" api/_lib/auth.js   ->  ['owner','director','staff']
//     grep -nE "LEG_[A-Z_]*ROLES" api/sd-data.js ->  (no output)
//
// So `staff` -- every employee who is not the owner or a director -- read and
// wrote the same 36 resources an owner did, including leg_deathrecords,
// leg_cremations, leg_custodylog and leg_preneed. For comparison sairnlaw had
// one gate and sairnvet had one; this app had zero.
//
// The band assignment and the role vocabulary are TRANSCRIBED from
// docs/2026-10-14-fourth-b15-sairnlegacy-role-matrix.md, not derived here.
// Changing them is a decision of the same kind and needs the same authority.
// Shape copied from api/_lib/law-roles.js, which solved the same problem on
// the same handler two days earlier -- not a second spelling of it.
//
// ── SIX OF THE SEVEN ROLE NAMES ARE [CONFIRM] IN THE SPEC AND STILL ARE ───
// `owner` and `director` are the app's own words. `arranger`, `prep`,
// `office`, `apprentice` and `livery` are the spec's names for job titles a
// funeral home may call something else, and the spec says plainly that nobody
// here has arranged a funeral. They are implemented because a vocabulary is
// needed before a gate can exist; they are NOT settled, and the open question
// is named in the handoff rather than buried in a comment.
//
// ── THE MIGRATION, WHICH IS THE PART THAT CAN BREAK A LIVE PRACTICE ───────
// `staff` STAYS in the vocabulary as a DEPRECATED value mapped to the
// NARROWEST band -- OPERATIONS read/write, no MONEY, no REGULATED write --
// until a human re-assigns each person. A migration that silently promoted
// `staff` to `arranger` would grant 15 money resources to everyone who had a
// login yesterday. That is the single most expensive mistake available here
// and it is why `staff` is a row in this table rather than a rename.

'use strict';

// ── THE APPEND-ONLY LOCK, FIRST, BECAUSE IT IS NOT A ROW IN THE TABLE ─────
// A chain-of-custody log that can be EDITED is not a chain of custody. This is
// the record of which human remains were in whose hands and when, and it binds
// the owner exactly as it binds a driver -- so it is a separate structure
// consulted independently of the role table rather than a value inside it. A
// rule expressed only as a role grant is a rule a role grant can erase.
//
// It does NOT stop a new entry. Appending is the whole purpose of the log.
const LEG_APPEND_ONLY = Object.freeze(Object.assign(Object.create(null), {
  leg_custodylog: true
}));

// ── THE TABLE. 36 ROWS, ONE PER RESOURCE, NO RESOURCE WITHOUT A ROW ───────
// Values are the ACTIONS each role may take: 'rw', 'r', or '' for none.
// `band` is carried on every row because the policy was given as THREE BANDS
// and the mapping from a band to a resource name is the part a reviewer has to
// be able to check. A wrong band is then visible rather than averaged away.
const R = 'r', RW = 'rw', NO = '';

// The three band templates, written once. A row that follows its band exactly
// spreads the template; a row that departs from it says so on the row, which
// is the only way an exception stays visible in a 36-row table.
const REGULATED = { owner: RW, director: RW, arranger: R, prep: R, office: R,
                    apprentice: R, livery: NO, staff: R };
const MONEY     = { owner: RW, director: RW, arranger: RW, prep: NO, office: RW,
                    apprentice: NO, livery: NO, staff: NO };
const OPERATIONS = { owner: RW, director: RW, arranger: RW, prep: R, office: RW,
                     apprentice: R, livery: NO, staff: RW };
// The three OPERATIONS resources livery actually needs: the schedule, and
// nothing else. Spelled as its own template rather than as three edits to
// OPERATIONS, so "which three" is one readable list.
const OPERATIONS_LIVERY = Object.assign({}, OPERATIONS, { livery: R });

function row(band, bandName, over, why) {
  return Object.freeze(Object.assign({}, band, over || {},
    { band: bandName, why: why || '' }));
}

const LEG_ROLE_MATRIX = Object.freeze(Object.assign(Object.create(null), {
  // ── REGULATED (9) ───────────────────────────────────────────────────────
  leg_aftercare:     row(REGULATED, 'REGULATED', null, 'bereavement follow-up against a named family'),
  leg_cases:         row(REGULATED, 'REGULATED', null, 'the death case itself'),
  leg_certs:         row(REGULATED, 'REGULATED', null, 'death certificates'),
  // RULE 2: a cremation authorisation is the sharpest irreversible act in this
  // app. The band already gives write to owner and director only; it is
  // restated here because a reader scanning for "who may authorise a
  // cremation" must find an answer on the row, not infer it from a template.
  leg_cremations:    row(REGULATED, 'REGULATED', null, 'cremation authority -- write is owner/director ONLY, never a task role. Whether a SECOND named person is legally required is a state-law question the spec flags and this code does not answer'),
  // RULE 1: append-only for EVERYONE INCLUDING THE OWNER, enforced by
  // LEG_APPEND_ONLY above rather than by this row.
  leg_custodylog:    row(REGULATED, 'REGULATED', null, 'chain of custody -- APPEND-ONLY for every role including owner'),
  // RULE 4: the one REGULATED resource where even read is not broad.
  leg_deathrecords:  row(REGULATED, 'REGULATED', { livery: NO }, 'death records -- read is NOT broad; livery is refused outright'),
  leg_dispatches:    row(REGULATED, 'REGULATED', null, 'removal dispatches'),
  leg_documents:     row(REGULATED, 'REGULATED', null, 'regulated documents'),
  leg_petcases:      row(REGULATED, 'REGULATED', null, 'pet cases -- tier B, banded REGULATED by shape rather than by tier'),

  // ── MONEY (15) ──────────────────────────────────────────────────────────
  leg_catererorders: row(MONEY, 'MONEY', null, 'vendor orders'),
  leg_caterers:      row(MONEY, 'MONEY', null, 'vendor records'),
  leg_floristorders: row(MONEY, 'MONEY', null, 'vendor orders'),
  leg_florists:      row(MONEY, 'MONEY', null, 'vendor records'),
  leg_gplservices:   row(MONEY, 'MONEY', null, 'the General Price List -- what the home charges'),
  leg_insurance:     row(MONEY, 'MONEY', null, 'insurance assignment'),
  leg_invoices:      row(MONEY, 'MONEY', null, 'invoices'),
  leg_keepsakes:     row(MONEY, 'MONEY', null, 'merchandise'),
  leg_liverybookings: row(MONEY, 'MONEY', null, 'banded MONEY by the vendor-order pattern. [CONFIRM] whether livery is invoiced through the home or billed direct -- that decides whether the livery role needs any MONEY read at all'),
  leg_liveryvendors: row(MONEY, 'MONEY', null, 'vendor records -- same [CONFIRM] as leg_liverybookings'),
  leg_merch_catalog: row(MONEY, 'MONEY', null, 'merchandise catalogue'),
  leg_merch_units:   row(MONEY, 'MONEY', null, 'merchandise units -- ALSO carries the b8 reservation lock, which is a transition gate and is unaffected by this table'),
  leg_monuments:     row(MONEY, 'MONEY', null, 'monuments'),
  leg_plots:         row(MONEY, 'MONEY', null, 'plots'),
  // RULE 3: money AND a long-dated obligation. Write is the MONEY band
  // (owner/director/arranger/office). Deletion should be owner-only and a
  // state change rather than a delete -- THERE IS NO DELETE ACTION ON THIS
  // HANDLER, so that half is not implemented and is named in the handoff
  // instead of being silently treated as done.
  leg_preneed:       row(MONEY, 'MONEY', null, 'pre-need -- money AND a long-dated obligation. The owner-only DELETION rule is NOT implemented here: this handler has no delete verb'),

  // ── OPERATIONS (12) ─────────────────────────────────────────────────────
  leg_bookings:      row(OPERATIONS_LIVERY, 'OPERATIONS', null, 'the schedule -- one of the three livery may read'),
  leg_clergy:        row(OPERATIONS, 'OPERATIONS', null, 'clergy contacts'),
  leg_clergybookings: row(OPERATIONS, 'OPERATIONS', null, 'clergy scheduling'),
  leg_facilities:    row(OPERATIONS, 'OPERATIONS', null, 'rooms, vehicles and -- per the seed data -- named staff treated as bookable'),
  leg_guestbook:     row(OPERATIONS, 'OPERATIONS', null, 'guestbook'),
  leg_keepsakeorders: row(OPERATIONS, 'OPERATIONS', null, 'banded OPERATIONS by the spec, despite the name: the ORDER of a keepsake is fulfilment, the keepsake catalogue is the money row'),
  leg_maintenance:   row(OPERATIONS, 'OPERATIONS', null, 'facility maintenance'),
  leg_memorials:     row(OPERATIONS, 'OPERATIONS', null, 'memorial pages'),
  leg_obituaries:    row(OPERATIONS, 'OPERATIONS', null, 'obituaries'),
  leg_processions:   row(OPERATIONS_LIVERY, 'OPERATIONS', null, 'processions -- one of the three livery may read. Tier A, and banded OPERATIONS: it is the route and the running order, not a charge'),
  leg_tributes:      row(OPERATIONS, 'OPERATIONS', null, 'tributes'),
  leg_vehicles:      row(OPERATIONS_LIVERY, 'OPERATIONS', null, 'vehicles -- one of the three livery may read')
}));

// Verdicts. Three, not two: NOT_LEG is a real answer and is never folded into
// ALLOW, because a silent ALLOW for a non-leg resource would read as "this
// table approved it".
const ALLOW = 'ALLOW';
const DENY = 'DENY';
const NOT_LEG = 'NOT_LEG';

/**
 * The one function. (resource, role, action) -> ALLOW | DENY | NOT_LEG.
 *
 * FAILS CLOSED IN EVERY DIRECTION THAT MATTERS:
 *  - a leg_ resource with no row    -> DENY. The table IS the policy; a
 *    resource nobody wrote a rule for is not "allowed by default", which is
 *    exactly the state this file exists to end.
 *  - a role not in the row          -> DENY. An eighth role added to
 *    ROLES_BY_APP.sairnlegacy without a column here gets nothing, loudly,
 *    rather than inheriting owner's access.
 *  - a missing or empty role        -> DENY.
 *  - any action that is not 'read'  -> treated as WRITE-class, so a future
 *    verb cannot slip through on a read grant.
 *
 * APPEND-ONLY IS NOT DECIDED HERE and the split is deliberate: whether a
 * custody write is an append or an edit depends on whether the row already
 * exists, which is a database question. `isAppendOnly()` answers "does this
 * resource have the rule", the handler answers "is this an edit".
 */
function decide(resource, role, action) {
  if (!resource || !Object.prototype.hasOwnProperty.call(LEG_ROLE_MATRIX, resource)) {
    return (String(resource || '').indexOf('leg_') === 0)
      ? DENY        // a NEW leg_ resource nobody added to the table: fail closed
      : NOT_LEG;
  }
  const r = LEG_ROLE_MATRIX[resource];
  const grant = (role && Object.prototype.hasOwnProperty.call(r, role))
    ? String(r[role] || '')
    : '';
  const wantsWrite = (action !== 'read');
  const allowed = wantsWrite ? (grant === 'rw') : (grant === 'rw' || grant === 'r');
  return allowed ? ALLOW : DENY;
}

/** Does this resource carry the append-only rule? */
function isAppendOnly(resource) {
  return !!LEG_APPEND_ONLY[resource];
}

/** Every resource the table covers. Used by the matrix test, not the handler. */
function resources() { return Object.keys(LEG_ROLE_MATRIX); }

/**
 * The refusal message. IT NAMES THE ROLE, not only the resource -- negative
 * control L1 in the spec requires that, because "you cannot do this" with no
 * subject sends a person to the wrong place to get it fixed.
 */
function denyMessage(resource, role) {
  return 'Your role (' + String(role || 'unknown') + ') does not have access '
       + 'to this record';
}

/** The append-only refusal, separately, because it is not a role problem. */
function appendOnlyMessage(resource) {
  return 'The chain-of-custody log cannot be edited by anyone, including the '
       + 'owner -- a custody record that can be changed is not a custody '
       + 'record. Add a new entry instead. Nothing was saved.';
}

module.exports = {
  LEG_ROLE_MATRIX, LEG_APPEND_ONLY,
  ALLOW, DENY, NOT_LEG,
  decide, isAppendOnly, resources, denyMessage, appendOnlyMessage
};
