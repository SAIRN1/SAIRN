// api/_lib/sv-roles.js
//
// SAIRNvet role granularity: ONE data table, read by ONE function.
//
// ── WHY THIS FILE EXISTS (2026-10-14, fourth b15 spec) ────────────────────
// MEASURED, not asserted: 41 of SAIRNvet's 42 resources had NO per-resource
// role check. The one that did is `sv_controlled`, the DEA-relevant register,
// behind PRESCRIBER_ROLES and the witnessing lock.
//
//     grep -nE "SV_[A-Z_]*ROLES" api/sd-data.js        ->  (no output)
//     grep -rn "PRESCRIBER_ROLES" api/ --include=*.js  ->  api/sv-auth.js:118,
//                                                          api/sv-witness.js:54
//
// So a `frontdesk` token wrote sv_soapnotes, sv_labresults, sv_surgery,
// sv_imaging and sv_invoicing exactly as the owner did. The 2026-09-21 session
// gate closed "no session" and left "any session" open -- the same two-step
// this platform has now paid for in sairnlaw, sairnlegacy and here.
//
// The band assignment and the role vocabulary are TRANSCRIBED from
// docs/2026-10-14-fourth-b15-sairnvet-role-matrix.md, not derived here.
// Changing them is a decision of the same kind and needs the same authority.
// Shape copied from api/_lib/leg-roles.js, which solved the same problem on
// the same handler in the same week -- not a third spelling of it.
//
// ── NO DEPRECATED ROLE, AND THAT IS WORTH SAYING RATHER THAN ASSUMING ─────
// SAIRNlegacy needed `staff` kept as a deprecated row mapped to the narrowest
// band, because promoting it would have granted 15 money resources to
// everybody who had a login yesterday. SAIRNvet has no such role: all six
// names in ROLES_BY_APP.sairnvet are the app's own current roster values
// (api/_lib/auth.js:320) and all six get a column here. `Other` was dropped
// from the roster before this work and must stay dropped -- a role that means
// nothing cannot be gated on. So there is no migration tier in this table and
// no row exists to carry one.
//
// ── THE TWO [CONFIRM]s THE SPEC LEFT OPEN ARE IMPLEMENTED AS THE SPEC'S OWN
//    PROPOSED ANSWER, AND NEITHER IS SETTLED ────────────────────────────────
//   * `manager` reads clinical records but writes none. The spec calls this
//     "the least-surprising answer, and the one most likely to be wrong".
//   * `tech` may NOT record a controlled-substance administration. In many
//     states a technician administers under direct supervision and the record
//     is the technician's -- changing this is a legal reading, not a
//     preference, and the witnessing lock is where a co-signature would go.
// Both are named in the handoff rather than buried here.

'use strict';

// ── THE APPEND-ONLY LOCK, FIRST, BECAUSE IT IS NOT A ROW IN THE TABLE ─────
// Rule 2 of the spec. `sv_audit_log` is the dosing trail. A dosing trail that
// can be EDITED is not a trail, and it binds the owner exactly as it binds an
// assistant -- so it is a separate structure consulted independently of the
// role table rather than a value inside it. A rule expressed only as a role
// grant is a rule a role grant can erase.
//
// It does NOT stop a new entry. Appending is the whole purpose of the trail.
const SV_APPEND_ONLY = Object.freeze(Object.assign(Object.create(null), {
  sv_audit_log: true
}));

// ── THE TABLE. 42 ROWS, ONE PER RESOURCE, NO RESOURCE WITHOUT A ROW ───────
// Values are the ACTIONS each role may take: 'rw', 'r', or '' for none.
// `band` is carried on every row because the policy was given as FOUR BANDS
// and the mapping from a band to a resource name is the part a reviewer has to
// be able to check. A wrong band is then visible rather than averaged away.
const R = 'r', RW = 'rw', NO = '';

// The four band templates, written once. A row that follows its band exactly
// spreads the template; a row that departs from it says so on the row, which
// is the only way an exception stays visible in a 42-row table.
const REGULATED = { owner: RW, dvm: RW, manager: R, tech: RW, assistant: R,
                    frontdesk: NO };
const MONEY     = { owner: RW, dvm: R, manager: RW, tech: NO, assistant: NO,
                    frontdesk: NO };
const OPERATIONS = { owner: RW, dvm: RW, manager: RW, tech: RW, assistant: RW,
                     frontdesk: RW };
const REFERENCE = { owner: RW, dvm: R, manager: RW, tech: R, assistant: R,
                    frontdesk: R };
// Rule 4: the narrowest REGULATED read on the platform. Front desk answers the
// phone, so it reads WHO the client and the patient are and nothing clinical.
// Spelled as its own template rather than as two edits to REGULATED, so "which
// two" is one readable list.
const REGULATED_FRONTDESK = Object.assign({}, REGULATED, { frontdesk: R });

// ── sv_controlled IS DERIVED FROM PRESCRIBER_ROLES, NOT RE-LISTED ─────────
// Rule 1 of the spec: this table adds 41 gates and does not touch the one that
// works. api/sv-auth.js owns the licensed-practitioner pair and exports it for
// exactly this reason -- api/sv-witness.js already imports it rather than
// re-listing the names, and a third copy of { owner, dvm } is a third place for
// the answer to drift. SAIRNsenior paid for the re-listed copy (cross-domain
// convention 7).
//
// EVERY ROLE IN THE TABLE STARTS AT NO AND IS RAISED ONLY BY THAT SET, so a
// seventh role added to ROLES_BY_APP.sairnvet is refused here by construction
// rather than by somebody remembering to add a column.
const PRESCRIBER_ROLES = require('../sv-auth').PRESCRIBER_ROLES;
const CONTROLLED = (function () {
  const o = {};
  Object.keys(REGULATED).forEach(function (role) {
    o[role] = PRESCRIBER_ROLES[role] ? RW : NO;
  });
  return o;
})();

function row(band, bandName, over, why) {
  return Object.freeze(Object.assign({}, band, over || {},
    { band: bandName, why: why || '' }));
}

const SV_ROLE_MATRIX = Object.freeze(Object.assign(Object.create(null), {
  // ── REGULATED (23) ──────────────────────────────────────────────────────
  // RULE 2: append-only for EVERY role including owner, enforced by
  // SV_APPEND_ONLY above rather than by this row.
  sv_audit_log:    row(REGULATED, 'REGULATED', null, 'the dosing trail -- APPEND-ONLY for every role including owner'),
  // RULE 4: one of the two resources front desk may read.
  sv_clients:      row(REGULATED_FRONTDESK, 'REGULATED', null, 'client identity -- one of the two front desk may read, so the phone can be answered'),
  sv_coggins:      row(REGULATED, 'REGULATED', null, 'Coggins tests -- an EIA certificate is a state-reportable equine record'),
  sv_compliance:   row(REGULATED, 'REGULATED', null, 'the practice compliance record: what was checked and when'),
  // RULE 1: NOT a band row. Derived from api/sv-auth.js's PRESCRIBER_ROLES.
  sv_controlled:   row(CONTROLLED, 'REGULATED', null, 'the DEA-relevant controlled-substance register -- owner/dvm only, DERIVED from PRESCRIBER_ROLES, and the witnessing lock on top of it is untouched by this table'),
  sv_dental:       row(REGULATED, 'REGULATED', null, 'dental charting under anaesthesia -- a clinical procedure record'),
  sv_documents:    row(REGULATED, 'REGULATED', null, 'the clinical document set: records released, referrals, lab reports'),
  sv_equinedental: row(REGULATED, 'REGULATED', null, 'equine dental floating -- a procedure record, separate table from sv_dental'),
  sv_farmcalls:    row(REGULATED, 'REGULATED', null, 'farm calls -- the visit record for food and production animals'),
  sv_imaging:      row(REGULATED, 'REGULATED', null, 'radiographs and ultrasound with their interpretations'),
  sv_labresults:   row(REGULATED, 'REGULATED', null, 'laboratory results -- a diagnostic finding on a named patient'),
  sv_lameness:     row(REGULATED, 'REGULATED', null, 'lameness examinations and grading -- a clinical assessment'),
  // RULE 4: the other resource front desk may read.
  sv_patients:     row(REGULATED_FRONTDESK, 'REGULATED', null, 'patient identity -- the other of the two front desk may read'),
  sv_peerconsults: row(REGULATED, 'REGULATED', null, 'peer consultations -- another clinician\'s opinion on this patient'),
  sv_prepurchase:  row(REGULATED, 'REGULATED', null, 'pre-purchase examinations -- a clinical opinion a sale turns on'),
  sv_referrals:    row(REGULATED, 'REGULATED', null, 'referrals out, with the clinical reason for them'),
  sv_reproduction: row(REGULATED, 'REGULATED', null, 'breeding and reproduction records -- clinical, and money turns on them'),
  // RULE 3: a consent recorded by somebody who cannot take consent is worse
  // than no record, so tech drops from the band's `rw` to read.
  sv_scribe_consent: row(REGULATED, 'REGULATED', { tech: R }, 'the ambient scribe\'s consent record -- WRITE IS owner/dvm ONLY, which is a departure from this band: a consent recorded by somebody who cannot take consent is worse than no record. No audio ever reaches this table'),
  sv_soapnotes:    row(REGULATED, 'REGULATED', null, 'the SOAP note -- the clinical record of a visit, and the one a technician legitimately writes'),
  sv_surgery:      row(REGULATED, 'REGULATED', null, 'surgical records -- procedure, anaesthesia and outcome'),
  sv_teleconsults: row(REGULATED, 'REGULATED', null, 'telemedicine consultations -- a clinical encounter at a distance'),
  sv_vitals:       row(REGULATED, 'REGULATED', null, 'vitals -- taken by a technician or assistant and written by the technician'),
  sv_wellness:     row(REGULATED, 'REGULATED', null, 'wellness plans and preventive-care schedules'),

  // ── MONEY (4) ───────────────────────────────────────────────────────────
  // THE CLINICIAN/MONEY SEPARATION IS THE POINT OF THIS BAND: `dvm` reads and
  // does not write, `manager` writes. The spec calls this the arm most likely
  // to be argued with, and it is deliberate -- an associate veterinarian
  // adjusting what a client is charged is a different act from treating the
  // animal, and the practice manager is the person who runs the office.
  sv_billing:      row(MONEY, 'MONEY', null, 'what the client is billed -- the practice manager\'s surface, not the clinician\'s'),
  sv_financials:   row(MONEY, 'MONEY', null, 'practice financials -- the clinician/money separation in its clearest form'),
  // RULE 4's money counterpart: front desk takes payment at the counter.
  sv_invoicing:    row(MONEY, 'MONEY', { frontdesk: R }, 'invoices -- the ONE money resource front desk may read, because the invoice is what is settled at the counter'),
  sv_petinsurance: row(MONEY, 'MONEY', null, 'pet insurance claims and policies -- money with a third party on the other end'),

  // ── OPERATIONS (13) ─────────────────────────────────────────────────────
  // EVERY ROLE READS AND WRITES EVERY OPERATIONS RESOURCE. That is the spec's
  // decision and it is the band that makes the matrix usable: a front desk
  // that cannot move an appointment cannot do its job.
  sv_boarding:     row(OPERATIONS, 'OPERATIONS', null, 'boarding -- tier A, banded OPERATIONS: it is occupancy, not a clinical record. [CONFIRM] in the spec'),
  sv_comms:        row(OPERATIONS, 'OPERATIONS', null, 'client communications log -- who was called about what'),
  sv_conservation: row(OPERATIONS, 'OPERATIONS', null, 'conservation programme records'),
  sv_examrooms:    row(OPERATIONS, 'OPERATIONS', null, 'exam-room occupancy and turnover'),
  sv_herdhealth:   row(OPERATIONS, 'OPERATIONS', null, 'herd health programmes -- production planning rather than an individual record'),
  sv_mobilevet:    row(OPERATIONS, 'OPERATIONS', null, 'the mobile unit\'s route and stock'),
  sv_multisite:    row(OPERATIONS, 'OPERATIONS', null, 'multi-site configuration -- tier A, banded OPERATIONS. [CONFIRM] in the spec'),
  sv_portal:       row(OPERATIONS, 'OPERATIONS', null, 'the client portal -- tier A and client-visible, which is why the spec flags it [CONFIRM]: if it SENDS on the practice\'s behalf it may belong in a narrower band'),
  sv_reminders:    row(OPERATIONS, 'OPERATIONS', null, 'automated reminders -- tier A and client-visible, same [CONFIRM] as sv_portal'),
  sv_scheduling:   row(OPERATIONS, 'OPERATIONS', null, 'the appointment book -- every role in the building moves appointments, which is why this band is wide'),
  sv_staff:        row(OPERATIONS, 'OPERATIONS', null, 'the staff roster as APP DATA -- shifts and contact details, NOT credentials. The credential roster is api/sv-auth.js\'s `roster` action behind MANAGEMENT_ROLES and is unaffected by this row'),
  sv_whiteboard:   row(OPERATIONS, 'OPERATIONS', null, 'the day\'s whiteboard -- who is in the building and what is happening'),
  sv_wildliferehab: row(OPERATIONS, 'OPERATIONS', null, 'wildlife rehabilitation intake and release'),

  // ── REFERENCE (2) ───────────────────────────────────────────────────────
  sv_reports:      row(REFERENCE, 'REFERENCE', null, 'saved report definitions -- read by everybody, written where the band says'),
  sv_speciesref:   row(REFERENCE, 'REFERENCE', null, 'the species reference data -- doses and norms by species, read by everybody who treats anything')
}));

// Verdicts. Three, not two: NOT_SV is a real answer and is never folded into
// ALLOW, because a silent ALLOW for a non-sv resource would read as "this
// table approved it".
const ALLOW = 'ALLOW';
const DENY = 'DENY';
const NOT_SV = 'NOT_SV';

/**
 * The one function. (resource, role, action) -> ALLOW | DENY | NOT_SV.
 *
 * FAILS CLOSED IN EVERY DIRECTION THAT MATTERS:
 *  - an sv_ resource with no row    -> DENY. The table IS the policy; a
 *    resource nobody wrote a rule for is not "allowed by default", which is
 *    exactly the state this file exists to end.
 *  - a role not in the row          -> DENY. A seventh role added to
 *    ROLES_BY_APP.sairnvet without a column here gets nothing, loudly,
 *    rather than inheriting owner's access.
 *  - a missing or empty role        -> DENY.
 *  - any action that is not 'read'  -> treated as WRITE-class, so a future
 *    verb cannot slip through on a read grant.
 *
 * APPEND-ONLY IS NOT DECIDED HERE and the split is deliberate: whether an
 * audit write is an append or an edit depends on whether the row already
 * exists, which is a database question. `isAppendOnly()` answers "does this
 * resource have the rule", the handler answers "is this an edit".
 */
function decide(resource, role, action) {
  if (!resource || !Object.prototype.hasOwnProperty.call(SV_ROLE_MATRIX, resource)) {
    return (String(resource || '').indexOf('sv_') === 0)
      ? DENY        // a NEW sv_ resource nobody added to the table: fail closed
      : NOT_SV;
  }
  const r = SV_ROLE_MATRIX[resource];
  const grant = (role && Object.prototype.hasOwnProperty.call(r, role))
    ? String(r[role] || '')
    : '';
  const wantsWrite = (action !== 'read');
  const allowed = wantsWrite ? (grant === 'rw') : (grant === 'rw' || grant === 'r');
  return allowed ? ALLOW : DENY;
}

/** Does this resource carry the append-only rule? */
function isAppendOnly(resource) {
  return !!SV_APPEND_ONLY[resource];
}

/** Every resource the table covers. Used by the matrix test, not the handler. */
function resources() { return Object.keys(SV_ROLE_MATRIX); }

/**
 * The refusal message. IT NAMES THE ROLE, not only the resource -- negative
 * control V3 in the spec requires more than that for one resource, because
 * "you cannot do this" with no subject sends a person to the wrong place to
 * get it fixed.
 *
 * AND IT TAKES THE RESOURCE, BECAUSE ONE OF THEM HAS A DIFFERENT SENTENCE.
 * V3 requires the sv_controlled refusal to name the licensed-practitioner
 * requirement rather than a generic forbidden: a technician who is told "your
 * role does not have access" will ask for their role to be widened, and the
 * true answer is that the entry is a legal act by a licensed veterinarian and
 * no amount of role widening changes that. api/_lib/law-roles.js takes a
 * resource for the same reason.
 */
function denyMessage(role, resource) {
  if (resource === 'sv_controlled') {
    return 'A controlled-substance entry is a legal act by a licensed '
         + 'veterinarian, so only an Owner/DVM or an Associate DVM can make '
         + 'one. Your role (' + String(role || 'unknown') + ') cannot, and '
         + 'widening it would not change that. Ask a veterinarian to record '
         + 'it. Nothing was saved.';
  }
  return 'Your role (' + String(role || 'unknown') + ') does not have access '
       + 'to this record';
}

/**
 * The append-only refusal, separately, because it is not a role problem. It
 * takes the resource and USES it: SV_APPEND_ONLY could carry a second table
 * one day, and a message that names "the dosing trail" for a resource that is
 * not it would be a confident wrong answer.
 */
const APPEND_ONLY_NOUN = { sv_audit_log: 'The dosing trail' };
function appendOnlyMessage(resource) {
  const noun = APPEND_ONLY_NOUN[resource] || 'This record';
  return noun + ' cannot be edited by anyone, including the owner -- a dosing '
       + 'record that can be changed is not a dosing record. Add a new entry '
       + 'instead. Nothing was saved.';
}

module.exports = {
  SV_ROLE_MATRIX, SV_APPEND_ONLY,
  ALLOW, DENY, NOT_SV,
  decide, isAppendOnly, resources, denyMessage, appendOnlyMessage
};
