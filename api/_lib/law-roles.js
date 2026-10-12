// api/_lib/law-roles.js
//
// SAIRNlaw role granularity: ONE data table, read by ONE function.
//
// ── WHY THIS FILE EXISTS (2026-10-12, hover2 seq 757) ──────────────────────
// Until today exactly ONE role check existed across SAIRNlaw's whole data
// surface -- LAW_RECONCILE_ROLES, owner-only, on law_trust_reconcile -- and the
// other 19 law_ resources were session-gated with no role distinction at all.
// A SAIRNlaw session of any role could read and write law_picases (settlement
// figures, attorney work product), law_pimedical (health information about an
// identified person held by a law firm) and law_bankstatements (the raw input to
// an IOLTA three-way reconciliation) exactly as freely as a managing attorney.
// The 19-resource table and the tier citations are hover2's, in
// docs/2026-10-08-hover2-law-role-granularity-routing.md.
//
// THE POLICY BELOW IS NOT THIS FILE'S INVENTION AND MUST NOT BE TREATED AS ONE.
// api/sd-data.js said twice, in writing, that the split was "a product decision
// with no obvious answer" and "a bar-rules judgement for the firm", and the
// auditor routed the finding without prescribing a fix. The categories here --
// what a paralegal may read, may write, and may never touch -- were decided by
// Michael and are transcribed, not derived. Changing them is the same kind of
// decision and needs the same authority.
//
// ── ONE TABLE, ONE FUNCTION, AND WHY THAT SHAPE RATHER THAN PER-RESOURCE IFS ─
// The failure this app already had is the shape to avoid: a role check written
// at one call site and not the nineteen others, which is indistinguishable from
// no policy at all when read one branch at a time. A single table makes the
// WHOLE policy readable in one screen and makes "which resources have no rule"
// a question a test can ask -- which is what
// api/sd-data-law-role-matrix.test.js does. Two call sites exist in
// api/sd-data.js and that is not a third copy of the policy: they are the two
// gates that were ALREADY there (the SD_SESSION_GATED block for four resources
// and the LAW_RESOURCES prelude for fifteen), and each passes the same three
// arguments to the same function.

'use strict';

// ── THE TRUST LOCK, FIRST, BECAUSE IT IS NOT A ROW IN THE TABLE ────────────
// IOLTA client trust money is the one figure a bar association audits. These
// resources are owner-and-attorney-only and HARD-LOCKED: no per-firm override
// may ever grant them to a paralegal, which is why they are a separate
// structure consulted BEFORE the table rather than a value inside it. A policy
// expressed only as a default is a policy an override can erase, and
// docs/2026-10-12-cody-b5-law-permissions-spec.md is explicit that this is the
// one thing the override mechanism may not reach.
//
// law_bankstatements is in here, and that is a judgment worth its own line: it
// is not a trust LEDGER, it is the bank side of the IOLTA three-way
// reconciliation, so it carries the same account's balances and the same
// audit exposure. docs/CRITICALITY-TIERS.md:425 rates it A on integrity for
// exactly that reason.
const LAW_TRUST_LOCKED = Object.freeze(Object.assign(Object.create(null), {
  law_trusttx: true,
  law_bankstatements: true
}));

// ── THE TABLE. 19 ROWS, ONE PER RESOURCE, NO RESOURCE WITHOUT A ROW ────────
// Values are the ACTIONS each role may take: 'rw', 'r', or '' for none.
// owner and attorney are full access on all nineteen by decision; paralegal is
// the row that carries the policy.
//
// EVERY ROW CARRIES THE CATEGORY IT WAS PLACED IN, because the policy was given
// as categories ("cases, documents, calendar, contacts, tasks and time
// entries") and the mapping from a category to a resource name is the part a
// reviewer has to be able to check. Where a resource was NOT clearly inside a
// named category it is DENIED to paralegal, which is the stated default, and
// the row says so rather than leaving the reader to infer it from an absence.
const LAW_ROLE_MATRIX = Object.freeze(Object.assign(Object.create(null), {
  // ── CASES, DOCUMENTS, CALENDAR, CONTACTS, TASKS, TIME: paralegal read+write
  law_matters:          { owner: 'rw', attorney: 'rw', paralegal: 'rw', why: 'cases' },
  law_picases:          { owner: 'rw', attorney: 'rw', paralegal: 'rw', why: 'cases -- named explicitly in the policy, despite being Tier A/A on settlement figures' },
  law_clients:          { owner: 'rw', attorney: 'rw', paralegal: 'rw', why: 'contacts' },
  law_matterdocs:       { owner: 'rw', attorney: 'rw', paralegal: 'rw', why: 'documents' },
  law_portalesign:      { owner: 'rw', attorney: 'rw', paralegal: 'rw', why: 'documents -- an executed e-signature record IS a document' },
  law_deadlines:        { owner: 'rw', attorney: 'rw', paralegal: 'rw', why: 'calendar' },
  law_mattermilestones: { owner: 'rw', attorney: 'rw', paralegal: 'rw', why: 'calendar' },
  law_mattertasks:      { owner: 'rw', attorney: 'rw', paralegal: 'rw', why: 'tasks' },
  law_timeentries:      { owner: 'rw', attorney: 'rw', paralegal: 'rw', why: 'time entries' },

  // ── BILLING, INVOICES, MEDICAL: paralegal read only
  law_invoices:         { owner: 'rw', attorney: 'rw', paralegal: 'r', why: 'invoices' },
  law_opaccounts:       { owner: 'rw', attorney: 'rw', paralegal: 'r', why: 'billing -- the firm OPERATING account, deliberately not a trust account' },
  law_optx:             { owner: 'rw', attorney: 'rw', paralegal: 'r', why: 'billing -- operating-account transactions, deliberately not trust transactions' },
  law_pimedical:        { owner: 'rw', attorney: 'rw', paralegal: 'r', why: 'law_pimedical, named explicitly in the policy as read-only' },

  // ── TRUST: paralegal none, and HARD-LOCKED above
  law_trusttx:          { owner: 'rw', attorney: 'rw', paralegal: '', why: 'TRUST -- IOLTA client money, hard-locked, no override may open it' },
  law_bankstatements:   { owner: 'rw', attorney: 'rw', paralegal: '', why: 'TRUST -- the bank side of the IOLTA three-way reconciliation, hard-locked' },

  // ── NOT IN ANY NAMED CATEGORY: paralegal none, by the stated default
  law_portalmessages:   { owner: 'rw', attorney: 'rw', paralegal: '', why: 'not in a named category. Client portal CORRESPONDENCE is not "documents" and not "contacts"; denied by the stated default rather than guessed into a category. FLAGGED as the most likely of the six denials to need revisiting -- a paralegal who cannot read client messages on a matter they work may be the wrong answer operationally, and widening it is the same kind of decision as the rest of this table' },
  law_barcerts:         { owner: 'rw', attorney: 'rw', paralegal: '', why: 'not in a named category -- an attorney\'s bar admission record' },
  law_clecredits:       { owner: 'rw', attorney: 'rw', paralegal: '', why: 'not in a named category -- an attorney\'s continuing-legal-education credits' },
  law_clerequirements:  { owner: 'rw', attorney: 'rw', paralegal: '', why: 'not in a named category -- CLE requirements per jurisdiction' }
}));

// ── THE 20th RESOURCE IS DELIBERATELY ABSENT AND THAT IS NOT AN OMISSION ───
// law_trust_reconcile already has the only pre-existing role gate on this app
// (LAW_RECONCILE_ROLES, OWNER-ONLY) and is excluded from hover2's table for
// that reason. It is NOT added here and its gate is NOT widened to attorney,
// even though the trust policy above is "owner and attorney": api/sd-data.js's
// own comment on that gate says adding attorney "IS THE OPEN QUESTION, not a
// rejected one ... widening it is a bar-rules judgement for the firm", and this
// batch's instruction was about the nineteen. Listed here so a reader who
// notices the asymmetry finds a decision rather than a gap.
const LAW_EXCLUDED = Object.freeze(['law_trust_reconcile']);

// Verdicts. Three, not two: NOT_LAW is a real answer and must not be folded
// into ALLOW, because the SD_SESSION_GATED call site passes every app's gated
// resources through this function and a silent ALLOW for a non-law resource
// would read as "this table approved it".
const ALLOW = 'ALLOW';
const DENY = 'DENY';
const NOT_LAW = 'NOT_LAW';

/**
 * The one function. (resource, role, action) -> ALLOW | DENY | NOT_LAW.
 *
 * FAILS CLOSED IN EVERY DIRECTION THAT MATTERS:
 *  - a law resource with no row in the table  -> DENY (the table is the policy;
 *    a resource nobody wrote a rule for is not "allowed by default", which is
 *    precisely the state this whole file exists to end)
 *  - a role not in the row                    -> DENY (a fourth role added to
 *    ROLES_BY_APP.sairnlaw without a column here gets nothing, loudly, rather
 *    than inheriting owner's access)
 *  - a missing or empty role                  -> DENY
 *  - any action that is not 'read'            -> treated as WRITE-class, so a
 *    future verb (soft_delete, export) cannot slip through on a read grant
 *  - a trust-locked resource                  -> DENY for anything the table
 *    does not grant, checked SEPARATELY so an override layer that forgets the
 *    lock still cannot open it
 */
function decide(resource, role, action) {
  if (!resource || !Object.prototype.hasOwnProperty.call(LAW_ROLE_MATRIX, resource)) {
    // Not one of the nineteen. Either not a law resource at all, or the one
    // excluded resource with its own gate. Say so rather than deciding.
    return (String(resource || '').indexOf('law_') === 0
            && LAW_EXCLUDED.indexOf(resource) === -1)
      ? DENY        // a NEW law_ resource nobody added to the table: fail closed
      : NOT_LAW;
  }
  const row = LAW_ROLE_MATRIX[resource];
  const grant = (role && Object.prototype.hasOwnProperty.call(row, role))
    ? String(row[role] || '')
    : '';
  const wantsWrite = (action !== 'read');
  const allowed = wantsWrite ? (grant === 'rw') : (grant === 'rw' || grant === 'r');
  if (!allowed) return DENY;
  // The lock is re-asserted AFTER the table agrees, not instead of it. The
  // table already denies paralegal on both locked resources; this line is what
  // survives somebody editing the table or layering an override on top.
  if (LAW_TRUST_LOCKED[resource] && role !== 'owner' && role !== 'attorney') {
    return DENY;
  }
  return ALLOW;
}

/** Every resource the table covers. Used by the matrix test, not by the handler. */
function resources() {
  return Object.keys(LAW_ROLE_MATRIX);
}

/** The refusal message a caller sees. One sentence, no policy dump. */
function denyMessage(resource, role) {
  if (LAW_TRUST_LOCKED[resource]) {
    return 'Client trust records are available to the firm owner and attorneys only';
  }
  return 'Your role (' + String(role || 'unknown') + ') does not have access to this record';
}

module.exports = {
  LAW_ROLE_MATRIX, LAW_TRUST_LOCKED, LAW_EXCLUDED,
  ALLOW, DENY, NOT_LAW,
  decide, resources, denyMessage
};
