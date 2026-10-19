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

// ══ C3: THE LICENSURE TIER. WHICH ACTS NEED A BAR-ADMITTED PERSON ═════════
// Michael's answer to practitioner question C3
// (docs/2026-10-16-hank-b17-practitioner-questions.md): the app should carry
// the CONCEPT, as one constant.
//
// MODELLED ON api/sv-auth.js's PRESCRIBER_ROLES, which is the same idea one
// app over: `{ owner, dvm }` exists because a controlled-substance entry is a
// LEGAL ACT BY A LICENSED PERSON, not because the record is sensitive. The
// distinction is not pedantry and C3 says why: a per-resource denial and a
// licensure tier look identical right up to the moment a fourth role is added,
// and C1 adds one in this same batch. With the tier in place, `bookkeeper`
// gets no trust access because it is not bar-admitted -- a property of the
// ROLE, decided once, rather than nineteen table cells somebody has to get
// right.
//
// NOT A SUPERSET OF "SENSITIVE". law_pimedical is health information about an
// identified person and is NOT here: a paralegal may read it, and reading it is
// not the practice of law. This map answers one question only.
const LAW_BAR_ADMITTED_ROLES = Object.freeze(Object.assign(Object.create(null), {
  owner: true,
  attorney: true
}));

// ── THE TRUST LOCK, AND IT IS NOW ACTUALLY CONSULTED FIRST ─────────────────
// IOLTA client trust money is the one figure a bar association audits. These
// resources are bar-admitted-only and HARD-LOCKED: no per-firm override may
// ever grant them to a paralegal, which is why they are a separate structure
// consulted BEFORE the table rather than a value inside it. A policy expressed
// only as a default is a policy an override can erase, and
// docs/2026-10-12-cody-b5-law-permissions-spec.md is explicit that this is the
// one thing the override mechanism may not reach.
//
// ── THE PARAGRAPH ABOVE WAS TRUE OF THE INTENT AND FALSE OF THE CODE ──────
// Until b18 `decide()` applied the table first and re-asserted the lock only
// AFTER the table had already agreed, and the code's own comment at that line
// said so: "re-asserted AFTER the table agrees, not instead of it". Two
// consequences, and the second is the one that mattered:
//
//   1. fourth's b26 H1: on the shipped table the paralegal cell for both
//      locked resources is '', so the table denied and the lock line was
//      never reached. Deleting LAW_TRUST_LOCKED changed no behaviour at all.
//      b17 answered that with STRUCTURAL arms (api/b17-trust-lock-hard.test.js
//      T1-T4) and recorded the order as "deliberate and correct".
//   2. AND IT BLOCKED C2. A two-stage disbursement needs trust policy to have
//      a named exception -- paralegal may PREPARE -- and with the lock last,
//      the only place to express that was a WIDER TABLE GRANT, which is the
//      one thing this lock exists to prevent. Policy that can only be widened
//      by widening the thing guarding it is policy in the wrong place.
//
// SO THE LOCK IS NOW THE FIRST THING CONSULTED and the table never sees a
// locked resource for a non-bar-admitted role. The structural arms still hold
// and the 2x2 still reads the same way; what changed is that the lock now
// OWNS trust policy, including its one exception, instead of restating a
// conclusion the table had already reached.
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

// ══ C2: THE TWO-STAGE DISBURSEMENT ════════════════════════════════════════
// Michael's answer to C2: a paralegal MAY PREPARE a trust disbursement for an
// attorney to authorise. So the refusal b17 proved was holding is the WRONG
// refusal for the prepare half, and the right one for the authorise half.
//
// ONE RESOURCE, NOT BOTH. law_trusttx is the disbursement ledger and is the
// thing a paralegal prepares. law_bankstatements is the BANK's side of the
// reconciliation -- it is not prepared by anybody at the firm, it is imported
// -- so it is deliberately absent and stays bar-admitted-only on every verb.
// A list rather than a condition, so widening it is a visible change.
const LAW_TRUST_TWO_STAGE = Object.freeze(Object.assign(Object.create(null), {
  law_trusttx: true
}));

// Who may prepare. `paralegal` by Michael's answer. NOT `bookkeeper`: C1's
// answer is a money role, and a trust disbursement is client money held in
// trust, which is the one account C2's own question separates from the
// operating account. Adding bookkeeper here is a decision, not a convenience.
const LAW_TRUST_PREPARE_ROLES = Object.freeze(Object.assign(Object.create(null), {
  paralegal: true
}));

// THE ACTION NAME, SPELLED ONCE. `decide(resource, role, 'prepare')` is the
// only verb that reaches the carve-out; every other string is WRITE-class and
// hits the lock. Exported so the handler and the countersignature endpoint
// cannot disagree about the spelling -- which is the drift that cost
// SAIRNsenior a real bug when two halves each called effectiveClock().
const LAW_PREPARE_ACTION = 'prepare';

// ══ b19: THE IOLTA THREE-WAY RECONCILIATION CARVE-OUT (C1's residual) ═════
// b18 added `bookkeeper` and named a limit in its own table comment: a
// bookkeeper CANNOT perform the IOLTA three-way reconciliation, because two of
// its three legs are in LAW_TRUST_LOCKED. This closes that, and it closes it
// by routing the work AWAY from bookkeeper rather than by opening trust to it.
//
// ── THE THREE LEGS ARE RECORDS, NOT ACTS, AND THAT CORRECTS THE PREMISE ───
// A three-way reconciliation compares (a) the trust bank statement's adjusted
// balance, (b) the firm's own trust ledger balance, and (c) the SUM of the
// individual client sub-ledger balances. All three must agree. NONE of the
// three is an act a licence is required to perform, and the instruction this
// implements described them as "bar-admitted-only by law" -- which is not what
// the rules say. What the common-practice sources actually support, in the same
// way api/sv-auth.js's PRESCRIBER_ROLES is supported:
//
//   * ABA Model Rule 1.15 puts the DUTY to safeguard client property on the
//     lawyer, and that duty is non-delegable as a RESPONSIBILITY.
//   * ABA Model Rule 5.3 expressly permits non-lawyer assistants under the
//     lawyer's supervision, so the clerical and arithmetic work of a
//     reconciliation IS delegable -- and in ordinary practice it is delegated.
//   * THE BAR-ADMITTED-ONLY ACT IS THE SIGNATURE, NOT THE ARITHMETIC. New
//     York's Rule 1.15(e) is the clearest: only an attorney admitted in the
//     State may be an authorised SIGNATORY on an attorney trust account.
//     Several states carry an equivalent. That act is AUTHORISING MONEY OUT,
//     which is exactly what C2's two-stage lock above already models.
//   * State bar guidance that mandates periodic three-way reconciliation also
//     puts the REVIEW on the lawyer and warns against a non-lawyer holding
//     sole or unsupervised control of the trust account.
//
// SO THE ROUTING IS RIGHT AND THE REASON IS DIFFERENT. A bookkeeper with trust
// access and no lawyer between them and the money is the specific arrangement
// that guidance warns about; the legs belong to the legal side. But it is not
// because the legs need a licence -- it is because the ACTS on them do, and
// because the responsibility cannot be handed over with the task.
//
// ── A NAMED VERB, NOT A WIDER READ, AND THAT IS THE WHOLE SAFETY ──────────
// `decide('law_trusttx', 'paralegal', 'read')` STAYS DENIED. b17's ARM B is
// precisely the arm that proves the lock refuses a paralegal read, and a
// blanket read grant would undo it. The reconciliation reaches the two legs
// through `LAW_RECONCILE_ACTION` and nothing else, so there is one route in,
// it is spelled once, and every other route is unchanged.
const LAW_RECONCILE_ACTION = 'reconcile';

// WHICH RESOURCES ARE RECONCILIATION LEGS. Both members of the trust lock,
// and exactly those two -- the bank side and the ledger side. The third leg
// (the sum of the client sub-ledgers) is DERIVED from law_trusttx and is not a
// resource of its own, which is why this list has two entries and not three.
const LAW_RECONCILE_LEGS = Object.freeze(Object.assign(Object.create(null), {
  law_trusttx: true,
  law_bankstatements: true
}));

// WHO MAY RECONCILE. The BAR-ADMITTED ROLES: owner and attorney.
//
// `bookkeeper` IS ABSENT AND THAT ABSENCE IS THE DELIVERABLE. It is not an
// omission to be tidied up later: it is the carve-out, and the row comments in
// LAW_ROLE_MATRIX below point here.
//
// ── `paralegal` WAS HERE IN b19 AND CAME OFF IN b20, ON MICHAEL'S DECISION ─
// b19 shipped `{ owner, attorney, paralegal }` and raised the residual as its
// own DECISION-NEEDED: Rule 5.3 supports a non-lawyer doing the WORK under
// supervision, but the same guidance requires the LAWYER TO REVIEW AND APPROVE
// the result, and SAIRNlaw records no attestation anywhere. b19 shipped a
// DISCLOSURE for that gap (LAW_RECONCILE_ATTESTATION below) rather than a
// mechanism.
//
// Michael's answer, 2026-10-19: **`paralegal` comes OFF the list until the
// attestation step exists.** The reasoning is the direction of the error. With
// the grant and no attestation, the app lets a non-lawyer produce a finished
// reconciliation that nothing records a lawyer as having reviewed -- and the
// duty under Rule 1.15 is the lawyer's and non-delegable. Without the grant,
// a firm that delegates the arithmetic in practice is inconvenienced and asks
// for the feature. One of those is a compliance claim the record cannot
// support; the other is a missing feature. The narrow one ships.
//
// THIS IS NOT A WITHDRAWAL OF THE RESEARCH. Rule 5.3 still supports the
// delegation and `LAW_RECONCILE_ATTESTATION.candidate` still names the
// mechanism that would make it safe -- prepared by a paralegal, attested by a
// bar-admitted person, bound to a hash of the exact reconciliation, which is
// the lock api/_lib/countersign.js already runs for C2. The grant is DEFERRED
// behind that mechanism, not refused.
//
// STILL NOT DERIVED FROM LAW_BAR_ADMITTED_ROLES, and the reason survives the
// change even though the two sets are now equal. Arm R2 of
// api/b19-iolta-reconcile-carveout.test.js asserts the RELATIONSHIP (`tier
// plus exactly { paralegal }`), so this edit makes R2 RED -- deliberately and
// expectedly. That red is the mechanism working: the one-line policy change
// cannot be made quietly. See docs/2026-10-19-hank-b20-concepts.md; the arm is
// in api/ and is re-aimed when the suite's owner updates it, not suppressed
// here.
const LAW_RECONCILE_ROLES = Object.freeze(Object.assign(Object.create(null), {
  owner: true,
  attorney: true
}));

// THE HALF THIS DOES NOT BUILD, CARRIED AS A STRUCTURE SO IT CANNOT BE LOST.
// Exported and asserted, so "the lawyer must review it" is a fact in the code
// rather than a sentence in a handoff nobody re-reads.
const LAW_RECONCILE_ATTESTATION = Object.freeze({
  // Is a lawyer's review required by the rules this routing is based on?
  required_by_rule: true,
  // Does this app record one? NO. Measured, not hoped.
  implemented: false,
  basis: 'ABA Model Rule 1.15 (the duty is the lawyer\'s and non-delegable) '
       + 'read with Rule 5.3 (the work is delegable under supervision). State '
       + 'bar guidance mandating periodic three-way reconciliation also puts '
       + 'the review on the lawyer.',
  // b20: RESTATED, because the b19 wording described a grant that no longer
  // exists and a stale true-sounding sentence in an exported constant is worse
  // than none. The gap did NOT close when `paralegal` came off the list -- it
  // narrowed. Only a bar-admitted person can now run a leg, so the person doing
  // the work is qualified; what is still absent is the RECORD.
  gap: 'Nothing in this app records an attestation. A reconciliation run by a '
     + 'bar-admitted person answers "the three legs agree" and never "a lawyer '
     + 'has attested that they agree", and the app must not present the first '
     + 'as the second. Separately, DELEGATION IS NOT AVAILABLE AT ALL until '
     + 'that record exists: `paralegal` was granted in b19 and withdrawn in '
     + 'b20 for exactly this reason, so a firm that delegates the arithmetic '
     + 'in practice cannot do it in the app.',
  // The mechanism that would close it, named rather than invented here.
  candidate: 'the same countersignature lock api/_lib/countersign.js already '
           + 'runs for C2 -- prepared by one role, attested by a bar-admitted '
           + 'one, bound to a hash of the exact reconciliation',
  recorded: '2026-10-19 (b19), hank -- raised as DECISION-NEEDED, not built. '
          + 'DECIDED 2026-10-19 (b20) by Michael: the delegation grant comes '
          + 'OFF until the attestation step exists. The mechanism is still not '
          + 'built; what changed is that the app no longer relies on it being '
          + 'absent.'
});

/** Is this resource one of the reconciliation legs? */
function isReconcileLeg(resource) {
  return !!LAW_RECONCILE_LEGS[resource];
}

// PREPARING IS NOT WRITING THE LEDGER, and this is the property the whole
// shape rests on. A prepared disbursement is a PENDING row that moves money
// nowhere; only a bar-admitted countersignature converts it. The mechanism is
// api/law-countersign.js -- a token bound to a hash of the exact record, held
// in a table rather than in memory, spendable only by a DIFFERENT, currently
// active, bar-admitted employee. If that endpoint is not reachable, this
// carve-out grants the ability to write a pending row that nobody can
// authorise, which is a dead end and not an opening.

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
//
// ══ C1: THE FOURTH COLUMN, `bookkeeper` ═══════════════════════════════════
// Michael's answer to C1: the person who enters time, raises invoices and
// reconciles the operating account IS A MEMBER OF STAFF. So this is a fourth
// role on the employee table, not a scoped external login -- the smaller of
// the two builds C1 described, and the one it asked about employment to pick
// between.
//
// THE COLUMN IS WRITTEN OUT ON ALL NINETEEN ROWS AND NOT TEMPLATED, for the
// same reason the `why` text is on every row: a role whose access is computed
// by a rule is a role nobody can read off the table. Three grants, three
// reads, thirteen denials.
//
// WHAT IT IS FOR, from C1's own wording: "enters time, raises invoices and
// reconciles the operating account". That is law_timeentries, law_invoices,
// law_opaccounts and law_optx -- and nothing else gets a WRITE.
//
// WHAT IT DELIBERATELY CANNOT REACH, which is the whole point of adding a role
// rather than handing out an attorney token: the matter file. law_matterdocs,
// law_picases, law_pimedical, law_portalesign and law_portalmessages are ''.
// A bookkeeper does not need a client's medical records to raise an invoice,
// and C1's own framing is that handing a non-lawyer every matter document is
// one of the two wrong answers the firm is currently forced to choose between.
//
// AND IT CANNOT REACH TRUST, BY THE TIER AND NOT BY THESE CELLS. Both trust
// cells read '' below, but that is the belt: `bookkeeper` is absent from
// LAW_BAR_ADMITTED_ROLES, so the lock refuses it before the table is consulted
// at all. THIS IS A LIMIT WORTH SAYING OUT LOUD RATHER THAN DISCOVERING: a
// bookkeeper cannot perform the IOLTA three-way reconciliation, because two of
// its three legs are locked. If that is the firm's real workflow, C1's answer
// is incomplete and the follow-up question is named in the b18 handoff.
const LAW_ROLE_MATRIX = Object.freeze(Object.assign(Object.create(null), {
  // ── CASES, DOCUMENTS, CALENDAR, CONTACTS, TASKS, TIME: paralegal read+write
  law_matters:          { owner: 'rw', attorney: 'rw', paralegal: 'rw', bookkeeper: 'r',  why: 'cases. bookkeeper READ only: an invoice is raised against a matter, so the matter has to be nameable -- and nothing about billing requires changing it' },
  law_picases:          { owner: 'rw', attorney: 'rw', paralegal: 'rw', bookkeeper: '',   why: 'cases -- named explicitly in the policy, despite being Tier A/A on settlement figures. bookkeeper NONE: a settlement figure is matter work product, not billing' },
  law_clients:          { owner: 'rw', attorney: 'rw', paralegal: 'rw', bookkeeper: 'r',  why: 'contacts. bookkeeper READ only: an invoice is addressed to a client' },
  law_matterdocs:       { owner: 'rw', attorney: 'rw', paralegal: 'rw', bookkeeper: '',   why: 'documents. bookkeeper NONE -- THE MATTER FILE IS THE LINE C1 EXISTS TO DRAW' },
  law_portalesign:      { owner: 'rw', attorney: 'rw', paralegal: 'rw', bookkeeper: '',   why: 'documents -- an executed e-signature record IS a document. bookkeeper NONE, same line' },
  law_deadlines:        { owner: 'rw', attorney: 'rw', paralegal: 'rw', bookkeeper: '',   why: 'calendar. bookkeeper NONE: a litigation deadline is not a billing artefact' },
  law_mattermilestones: { owner: 'rw', attorney: 'rw', paralegal: 'rw', bookkeeper: '',   why: 'calendar. bookkeeper NONE' },
  law_mattertasks:      { owner: 'rw', attorney: 'rw', paralegal: 'rw', bookkeeper: '',   why: 'tasks. bookkeeper NONE' },
  law_timeentries:      { owner: 'rw', attorney: 'rw', paralegal: 'rw', bookkeeper: 'rw', why: 'time entries. bookkeeper READ+WRITE -- "enters time" is the first item in C1\'s own description of the job' },

  // ── BILLING, INVOICES, MEDICAL: paralegal read only
  law_invoices:         { owner: 'rw', attorney: 'rw', paralegal: 'r', bookkeeper: 'rw', why: 'invoices. bookkeeper READ+WRITE -- "raises invoices". Note this is WIDER than paralegal on the same row, which is correct and is the first cell in this table where that happens' },
  law_opaccounts:       { owner: 'rw', attorney: 'rw', paralegal: 'r', bookkeeper: 'rw', why: 'billing -- the firm OPERATING account, deliberately not a trust account. bookkeeper READ+WRITE -- "reconciles the operating account"' },
  law_optx:            { owner: 'rw', attorney: 'rw', paralegal: 'r', bookkeeper: 'rw', why: 'billing -- operating-account transactions, deliberately not trust transactions. bookkeeper READ+WRITE: the reconciliation is performed against these rows' },
  law_pimedical:        { owner: 'rw', attorney: 'rw', paralegal: 'r', bookkeeper: '',   why: 'law_pimedical, named explicitly in the policy as read-only. bookkeeper NONE -- health information about an identified person is not billing data, and this is the row most worth being wrong about in the narrow direction' },

  // ── TRUST: paralegal none on WRITE, and the LOCK above decides, not these cells
  law_trusttx:          { owner: 'rw', attorney: 'rw', paralegal: '', bookkeeper: '', why: 'TRUST -- IOLTA client money. The LOCK decides this row, not these cells: bar-admitted only, with TWO named exceptions and no others -- C2\'s two-stage `prepare`, which paralegal may perform and which writes a PENDING row rather than the ledger, and b19\'s `reconcile`, which is leg (b) of the three-way reconciliation and is granted to the BAR-ADMITTED ROLES only -- b19 included `paralegal` and b20 took it off until an attestation record exists. `bookkeeper` is absent from BOTH, and that absence is C1\'s carve-out rather than an omission' },
  law_bankstatements:   { owner: 'rw', attorney: 'rw', paralegal: '', bookkeeper: '', why: 'TRUST -- leg (a) of the IOLTA three-way reconciliation, the bank side. Deliberately NOT in LAW_TRUST_TWO_STAGE, because nobody at the firm prepares a bank statement -- but it IS in LAW_RECONCILE_LEGS, because reconciling is exactly what it is for. `bookkeeper` cannot reach it on any verb' },

  // ── NOT IN ANY NAMED CATEGORY: paralegal none, by the stated default
  law_portalmessages:   { owner: 'rw', attorney: 'rw', paralegal: '', bookkeeper: '', why: 'not in a named category. Client portal CORRESPONDENCE is not "documents" and not "contacts"; denied by the stated default rather than guessed into a category. FLAGGED as the most likely of the six denials to need revisiting -- a paralegal who cannot read client messages on a matter they work may be the wrong answer operationally, and widening it is the same kind of decision as the rest of this table' },
  law_barcerts:         { owner: 'rw', attorney: 'rw', paralegal: '', bookkeeper: '', why: 'not in a named category -- an attorney\'s bar admission record' },
  law_clecredits:       { owner: 'rw', attorney: 'rw', paralegal: '', bookkeeper: '', why: 'not in a named category -- an attorney\'s continuing-legal-education credits' },
  law_clerequirements:  { owner: 'rw', attorney: 'rw', paralegal: '', bookkeeper: '', why: 'not in a named category -- CLE requirements per jurisdiction' }
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
 *  - any action that is not 'read' or 'prepare' -> treated as WRITE-class, so
 *    a future verb (soft_delete, export) cannot slip through on a read grant
 *  - a trust-locked resource                  -> DENY unless the role is
 *    BAR-ADMITTED, decided FIRST and without consulting the table at all, so
 *    an override layer that forgets the lock cannot open it and a table edit
 *    cannot either
 *  - a 'prepare' on anything that is NOT a two-stage trust resource -> treated
 *    as WRITE-class. The verb is not a general back door; it means one thing
 *    on one resource.
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
  // ── THE LOCK, FIRST, AND WITHOUT READING THE TABLE (b18) ─────────────────
  // This is the ordering change. The table is not consulted for a locked
  // resource held by a role that is not bar-admitted -- so the lock is the
  // thing that refuses, the thing that owns the one exception, and the thing a
  // reader finds when they ask who may touch client trust money.
  if (LAW_TRUST_LOCKED[resource] && LAW_BAR_ADMITTED_ROLES[role] !== true) {
    // C2's ONE exception, and it is as narrow as three conditions can make it:
    // the named verb, a resource that is two-stage, and a role on the prepare
    // list. A prepared row is pending and moves no money; see the block above
    // LAW_PREPARE_ACTION.
    if (action === LAW_PREPARE_ACTION
        && LAW_TRUST_TWO_STAGE[resource] === true
        && LAW_TRUST_PREPARE_ROLES[role] === true) {
      return ALLOW;
    }
    // b19's SECOND exception, the same three-condition shape: the named verb,
    // a resource that is a reconciliation LEG, and a role on the reconcile
    // list. It yields the two legs to the LEGAL SIDE and never to
    // `bookkeeper`, which is C1's carve-out.
    //
    // b20: THE BRANCH IS NOW UNREACHABLE AND IS KEPT ON PURPOSE. Since
    // `paralegal` came off LAW_RECONCILE_ROLES, every member of that set is
    // also in LAW_BAR_ADMITTED_ROLES, so the enclosing `if` has already let
    // them past and nothing arrives here. It is NOT dead code to delete: it is
    // the exception shape the attestation decision will re-populate, and
    // deleting it would make re-granting `paralegal` a lock rewrite rather
    // than a one-line set change. Named rather than left to be rediscovered,
    // because an unreachable branch nobody declared is item 8's shape.
    //
    // IT IS READ-SHAPED BY CONSTRUCTION, not by a flag. `reconcile` is not in
    // any write path -- api/sd-data.js's law_trust_reconcile branch is
    // read-only and computes a comparison -- so there is nothing to narrow
    // here. A caller that wanted to WRITE a leg would have to ask for a write
    // verb, and the branch above refuses it.
    if (action === LAW_RECONCILE_ACTION
        && LAW_RECONCILE_LEGS[resource] === true
        && LAW_RECONCILE_ROLES[role] === true) {
      return ALLOW;
    }
    return DENY;
  }
  // ── A NAMED VERB MEANS ONE THING, ON THE RESOURCES THAT DEFINE IT ───────
  // FOUND BY DRIVING IT, not by reading it: `decide('law_invoices',
  // 'bookkeeper', 'reconcile')` returned ALLOW. Nothing is locked on that row,
  // so it fell through to the table, `reconcile` was treated as WRITE-class
  // like any unknown verb, and bookkeeper holds `rw` on invoices -- so a verb
  // that means "perform leg (a) or (b) of a trust reconciliation" was granted
  // on a resource that has no legs. `prepare` had the same hole and nobody had
  // asked.
  //
  // THE WRITE-CLASS DEFAULT IS STILL RIGHT FOR AN *UNKNOWN* VERB -- a future
  // `soft_delete` or `export` must not ride in on a read grant, which is what
  // that rule is for. It is wrong for a verb this module NAMES: a named verb
  // is defined on a named set of resources and is meaningless off it. So the
  // two are separated, and the direction is narrowing.
  const NAMED_VERB_RESOURCES = {};
  NAMED_VERB_RESOURCES[LAW_PREPARE_ACTION] = LAW_TRUST_TWO_STAGE;
  NAMED_VERB_RESOURCES[LAW_RECONCILE_ACTION] = LAW_RECONCILE_LEGS;
  if (Object.prototype.hasOwnProperty.call(NAMED_VERB_RESOURCES, action)
      && NAMED_VERB_RESOURCES[action][resource] !== true) {
    return DENY;
  }

  const row = LAW_ROLE_MATRIX[resource];
  const grant = (role && Object.prototype.hasOwnProperty.call(row, role))
    ? String(row[role] || '')
    : '';
  // Any OTHER verb that is not 'read' is WRITE-class. The two named verbs
  // cannot reach this line for a resource that does not define them -- the
  // guard above returned -- and for a resource that DOES define them, the
  // locked branch further up already answered.
  const wantsWrite = (action !== 'read');
  const allowed = wantsWrite ? (grant === 'rw') : (grant === 'rw' || grant === 'r');
  if (!allowed) return DENY;
  return ALLOW;
}

/** Every resource the table covers. Used by the matrix test, not by the handler. */
function resources() {
  return Object.keys(LAW_ROLE_MATRIX);
}

/**
 * The refusal message a caller sees. One sentence, no policy dump.
 *
 * THE TRUST SENTENCE NOW NAMES THE ROUTE WHERE THERE IS ONE (b18). A refusal
 * that does not say what the person may do instead sends them to the wrong
 * place to get it fixed -- the same reason leg-roles' message names the role.
 * A paralegal refused law_trusttx on a WRITE can prepare it; saying so is the
 * difference between a policy and a wall.
 *
 * AND IT IS OFFERED ON A WRITE ONLY. First draft offered it on a READ too,
 * because the condition was `action !== PREPARE` and `'read'` satisfies that.
 * A paralegal refused a READ of the trust ledger cannot fix it by preparing
 * anything -- the route does not exist for that verb -- so the refusal would
 * have sent them to do something that could not help. Caught by arm B4 of
 * api/b18-countersign-lock.test.js, which is why that arm asserts the ABSENCE
 * of the word on a read.
 */
function denyMessage(resource, role, action) {
  if (LAW_TRUST_LOCKED[resource]) {
    const wantsWrite = (action !== 'read' && action !== LAW_PREPARE_ACTION
                        && action !== LAW_RECONCILE_ACTION
                        && action !== undefined && action !== null && action !== '');
    // b19: A BOOKKEEPER REFUSED A RECONCILIATION LEG GETS THE REASON, NOT THE
    // GENERIC TRUST SENTENCE. "Available to the owner and attorneys only" is
    // true and useless to the person whose job title is on the invoice they
    // just raised -- they will ask for a permission nobody is going to grant,
    // because the answer is that this work is not theirs. The refusal says so.
    if (isReconcileLeg(resource) && role === 'bookkeeper') {
      return 'Client trust records are not part of the bookkeeping role. The '
           + 'IOLTA three-way reconciliation is the firm\'s legal staff\'s '
           + 'work and a lawyer is answerable for it; the operating account is '
           + 'yours. Ask an attorney if a trust figure needs checking.';
    }
    if (LAW_TRUST_TWO_STAGE[resource] === true
        && LAW_TRUST_PREPARE_ROLES[role] === true
        && wantsWrite) {
      return 'Only an attorney or the firm owner can authorise money out of '
           + 'client trust. You can PREPARE this disbursement for an attorney '
           + 'to review and authorise -- nothing moves until they do.';
    }
    return 'Client trust records are available to the firm owner and attorneys only';
  }
  return 'Your role (' + String(role || 'unknown') + ') does not have access to this record';
}

module.exports = {
  LAW_ROLE_MATRIX, LAW_TRUST_LOCKED, LAW_EXCLUDED,
  // b18, Michael's counsel practitioner answers. Exported so a suite can
  // assert them and so no second file re-lists a role name.
  LAW_BAR_ADMITTED_ROLES,
  LAW_TRUST_TWO_STAGE, LAW_TRUST_PREPARE_ROLES, LAW_PREPARE_ACTION,
  // b19, C1's IOLTA carve-out. LAW_RECONCILE_ROLES is what api/sd-data.js's
  // law_trust_reconcile gate must READ rather than re-list -- that gate has
  // carried a hand-written `roleSet({ owner: true })` and its own comment
  // calling the widening "the open question, not a rejected one". This is the
  // answer, in the module that owns law role policy.
  LAW_RECONCILE_ACTION, LAW_RECONCILE_LEGS, LAW_RECONCILE_ROLES,
  LAW_RECONCILE_ATTESTATION, isReconcileLeg,
  ALLOW, DENY, NOT_LAW,
  decide, resources, denyMessage
};
