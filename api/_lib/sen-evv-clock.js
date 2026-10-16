// api/_lib/sen-evv-clock.js
// SAIRNsenior EVV clock integrity. 2026-09-26.
//
// PURE -- no I/O. Same shape and the same reason as api/_lib/sen-evv-readiness.js
// and api/_lib/compliance-rules.js: the rules are testable without a database.
//
// ── THE TWO THINGS THIS EXISTS FOR ────────────────────────────────────────
// VERIFIED IN api/sd-data.js BEFORE ANY OF THIS WAS WRITTEN, because both were
// reported as code-search findings and one of the two turned out to be a
// deliberate design decision rather than a gap.
//
//   1. THE CLOCK TIME IS TAKEN FROM THE DEVICE AND NEVER CHECKED. sairnsenior's
//      vsClockIn/vsClockOut send `new Date().toISOString()` from the handset,
//      and the server's caregiver branch does
//          SEN_VISIT_EVV_FIELDS.forEach(f => { if (payload[f] !== undefined)
//                                              visitData[f] = payload[f]; })
//      -- the value is stored verbatim. There is no comparison against server
//      time, no ordering check, and no bound. A handset with a wrong clock
//      produces a wrong EVV record silently, and a caregiver can send any
//      timestamp at all. EVV exists precisely to stop a visit time being
//      caregiver-asserted.
//
//   2. OFFICE STAFF CANNOT CORRECT A CLOCK TIME, AND THAT IS ON PURPOSE. The
//      scheduler branch says so in its own words: "EVV fields are NEVER
//      accepted from a scheduler-tier caller, even on an edit -- preserved from
//      whatever the assigned caregiver already recorded, so a scheduler can
//      never forge a clock-in/out." That guard is right and this module does
//      not weaken it.
//
// ── WHY THE OBVIOUS FIX FOR (1) IS WRONG, IN THE APP'S OWN WORDS ─────────
// "Use the server's clock" is the reflex and it destroys the offline path.
// sairnsenior queues clock events while offline and replays them UNCHANGED,
// and the queue's own comment states the rule: "THE RECORDED TIME IS THE MOMENT
// THE CAREGIVER CLOCKED, NEVER THE MOMENT IT SYNCED ... Re-stamping on flush
// would produce an EVV record that is precise, plausible and false -- worse
// than a missing one, because nothing downstream could tell."
//
// So the claimed time is KEPT, and the server's own observation is recorded
// BESIDE it. The gap between the two is the auditable fact, and it is exactly
// the fact an offline replay makes large and legitimate.
//
// ── AND WHY (2) IS NOT SOLVED BY LETTING THE OFFICE WRITE THE FIELD ──────
// A correction that OVERWRITES the caregiver's record destroys the evidence
// the record is. Federal EVV requires the visit as verified; a state audit that
// finds an edited time with no trail cannot tell a typo correction from a
// fabrication -- which is the same thing the scheduler guard already refuses.
//
// So a correction is ADDITIVE: the original clock fields are never touched, and
// an entry is appended to `clock_corrections` carrying the proposed value, a
// REASON CODE from a closed vocabulary, free text, who proposed it and when.
// Reading a corrected visit is then a decision the reader makes with both
// numbers in front of them, not one the app makes silently.
//
// ── WHAT THIS MODULE DOES NOT DO ─────────────────────────────────────────
// It does not decide whether a corrected time is TRUE. It cannot. It refuses
// the impossible, records the questionable, and leaves the judgement where the
// judgement is.

'use strict';

// A skew this far in the FUTURE is not a slow sync, it is a wrong clock or a
// forged value: a clock event cannot legitimately be stamped ahead of the
// server that receives it. Two minutes absorbs ordinary handset drift and NTP
// lag without absorbing anything meaningful.
const FUTURE_TOLERANCE_MS = 2 * 60 * 1000;

// A PAST skew is NOT refused at any size, and that is the offline path. It is
// recorded, and flagged above this for a reader, because a replay a week later
// is legitimate and a replay a year later is a data-entry accident.
const PAST_FLAG_MS = 7 * 24 * 60 * 60 * 1000;

// THE CLOCK FIELDS THIS MODULE REPORTS ON. Hoisted out of checkClockEvent and
// exported on 2026-10-14 because a SECOND place now has to know the same set:
// the sen_visits write branch merges stored flags on `field`, and the fields it
// treats as superseded by a payload MUST be exactly the fields this function
// re-checks. Two copies of that list would drift the day a third clock field is
// added, and the merge would then keep a stale flag on it forever -- the drift
// that cost SAIRNsenior a real bug (cross-domain convention 7).
const CLOCK_FIELDS = ['clock_in_at', 'clock_out_at'];

// Closed vocabulary. A free-text reason is a field that fills with "correction"
// and answers nothing at audit; the whole point of a reason CODE is that the
// categories can be counted.
const CORRECTION_REASONS = {
  device_clock_wrong: 'The handset clock was wrong when the event was recorded',
  forgot_to_clock_in: 'The caregiver did not clock in at the start of the visit',
  forgot_to_clock_out: 'The caregiver did not clock out at the end of the visit',
  clocked_wrong_visit: 'The event was recorded against the wrong visit',
  device_unavailable: 'No device was available at the time of the visit',
  transcription_error: 'The time was entered incorrectly',
  // ── THE ONE THE ORDINARY CLOCK ROUTE USES (2026-10-15, T16) ─────────────
  // A caregiver who re-clocks through vsClockIn/vsClockOut supplies no reason
  // code -- the UI has no field for one. Refusing without one is the 409 this
  // decision replaced; recording an empty reason is the silent drop. So the
  // route has its own code, and it is a SEPARATE code on purpose: an auditor
  // counting corrections must be able to tell "the caregiver re-sent a
  // different time and said nothing" from a reason somebody chose.
  resubmitted_by_caregiver: 'The caregiver submitted a different time through '
    + 'the ordinary clock route and gave no reason',
  other: 'Something else -- the note is required and must say what'
};

// ── A CORRECTION IS SUBMITTED, THEN APPROVED (2026-10-15, T16) ────────────
// Michael's decision: a caregiver may SUBMIT a correction; a scheduler
// APPROVES it before payroll uses it. So an entry has a state, and the state
// is what effectiveClock() reads -- not the mere presence of an entry.
//
// AN ENTRY WITH NO `status` IS APPROVED, and that is not laxity. Every
// correction written before today was filed by a scheduler through
// propose_clock_correction and was effective the moment it was filed. Reading
// a missing status as pending would silently revert every live corrected visit
// to its uncorrected time -- this change causing the exact defect it fixes, on
// records nobody touched.
const CORRECTION_STATUS = { pending: 'Awaiting a scheduler\'s approval',
                            approved: 'Approved and in effect' };
function entryIsApproved(e) {
  return !!e && (e.status === undefined || e.status === null || e.status === 'approved');
}

function refuse(code, message, extra) {
  return Object.assign({ ok: false, error: { code: code, message: message } }, extra || {});
}

function parseISO(v) {
  if (typeof v !== 'string' || !v) return null;
  const t = Date.parse(v);
  return isFinite(t) ? t : null;
}

// checkClockEvent(payload, existingData, serverNowISO) -> verdict
//
// `payload` is what the caregiver sent, `existingData` the visit's stored data
// (so an ordering check can see a clock_in stored on an earlier request), and
// `serverNowISO` the receiving server's own time.
//
// Returns { ok: true, stamps: {...}, flags: [...] } or a refusal. `stamps` is
// what the caller should MERGE alongside the claimed fields -- never instead of
// them.
function checkClockEvent(payload, existingData, serverNowISO) {
  payload = payload || {};
  existingData = existingData || {};
  const now = parseISO(serverNowISO);
  if (now === null) {
    // The server not knowing its own time is a could-not-check, not a pass.
    return refuse('NO_SERVER_TIME',
      'The receiving server did not supply its own time, so no skew or '
      + 'ordering check was performed. Nothing was verified about this clock '
      + 'event.');
  }

  const flags = [];
  const stamps = {};
  let touched = 0;

  CLOCK_FIELDS.forEach(function (field) {
    if (payload[field] === undefined) return;
    touched++;
    const claimed = parseISO(payload[field]);
    if (claimed === null) {
      flags.push({ field: field, code: 'UNPARSEABLE', value: payload[field] });
      return;
    }
    const skew = claimed - now;
    // THE SERVER'S OWN OBSERVATION, BESIDE THE CLAIM AND NOT INSTEAD OF IT.
    stamps[field.replace('_at', '_received_at')] = serverNowISO;
    stamps[field.replace('_at', '_skew_ms')] = skew;
    if (skew > FUTURE_TOLERANCE_MS) {
      flags.push({ field: field, code: 'FUTURE', skew_ms: skew });
    } else if (skew < -PAST_FLAG_MS) {
      flags.push({ field: field, code: 'LATE_REPLAY', skew_ms: skew });
    }
  });

  if (!touched) {
    // Nothing clock-shaped in this payload. Not an error -- a scheduling write
    // goes through the same handler -- and explicitly not a pass either.
    return { ok: true, checked: false, stamps: {}, flags: [] };
  }

  // ── THE REFUSALS. Only the impossible. ──────────────────────────────────
  const unparseable = flags.filter(function (f) { return f.code === 'UNPARSEABLE'; });
  if (unparseable.length) {
    return refuse('CLOCK_UNPARSEABLE',
      'A clock time was not a readable timestamp: '
      + unparseable.map(function (f) { return f.field + '=' + JSON.stringify(f.value); }).join(', ')
      + '. It is refused rather than stored, because an unreadable EVV time is '
      + 'not a time and storing it produces a visit that looks verified.',
      { flags: flags });
  }

  const future = flags.filter(function (f) { return f.code === 'FUTURE'; });
  if (future.length) {
    return refuse('CLOCK_IN_FUTURE',
      'A clock time is more than ' + Math.round(FUTURE_TOLERANCE_MS / 60000)
      + ' minutes AHEAD of the server: '
      + future.map(function (f) {
          return f.field + ' by ' + Math.round(f.skew_ms / 60000) + ' min';
        }).join(', ')
      + '. A clock event cannot be stamped later than the moment it is '
      + 'received, so this is a wrong device clock or a forged value -- not a '
      + 'slow sync, which only ever runs the other way. Correct the device '
      + 'clock and re-record, or file a correction with a reason code.',
      { flags: flags });
  }

  // ── ORDERING, AGAINST THE STORED VALUE AS WELL AS THE PAYLOAD ───────────
  // A clock-out normally arrives on its own request, so comparing only within
  // the payload would never see the clock-in at all.
  const inAt = parseISO(payload.clock_in_at !== undefined
    ? payload.clock_in_at : existingData.clock_in_at);
  const outAt = parseISO(payload.clock_out_at !== undefined
    ? payload.clock_out_at : existingData.clock_out_at);
  if (inAt !== null && outAt !== null && outAt < inAt) {
    return refuse('CLOCK_OUT_BEFORE_IN',
      'The clock-out (' + new Date(outAt).toISOString() + ') is BEFORE the '
      + 'clock-in (' + new Date(inAt).toISOString() + '). A negative visit '
      + 'duration is billed as zero or as a huge number depending on which '
      + 'way the subtraction falls, and either is a claim nobody can defend.',
      { flags: flags });
  }

  return { ok: true, checked: true, stamps: stamps, flags: flags };
}

// proposeCorrection(visitData, proposal, actor, atISO) -> verdict
//
// ADDITIVE, ALWAYS. Returns the entry to APPEND to visitData.clock_corrections.
// The caller must not write the corrected value into clock_in_at/clock_out_at:
// this module deliberately does not return one, so a caller cannot do it by
// copying a field across.
function proposeCorrection(visitData, proposal, actor, atISO) {
  visitData = visitData || {};
  proposal = proposal || {};
  const field = proposal.field;
  if (field !== 'clock_in_at' && field !== 'clock_out_at') {
    return refuse('BAD_FIELD',
      'A correction names clock_in_at or clock_out_at. Got '
      + JSON.stringify(field) + '.');
  }
  if (!CORRECTION_REASONS[proposal.reason_code]) {
    return refuse('BAD_REASON_CODE',
      'reason_code must be one of: ' + Object.keys(CORRECTION_REASONS).join(', ')
      + '. A free-text reason fills with the word "correction" and answers '
      + 'nothing at audit; the categories exist so they can be counted.');
  }
  const note = String(proposal.note || '').trim();
  if (proposal.reason_code === 'other' && note.length < 12) {
    return refuse('NOTE_REQUIRED',
      'reason_code "other" needs a note saying what actually happened. An '
      + '"other" with no note is the category that swallows every real reason.');
  }
  const proposed = parseISO(proposal.proposed_at);
  if (proposed === null) {
    return refuse('PROPOSED_UNPARSEABLE',
      'proposed_at is not a readable timestamp: '
      + JSON.stringify(proposal.proposed_at));
  }
  if (!actor) {
    return refuse('NO_ACTOR',
      'A correction is attributed or it is not a correction. The caller must '
      + 'supply the employee id from the verified session, never from the '
      + 'payload.');
  }
  const at = parseISO(atISO);
  if (at === null) {
    return refuse('NO_SERVER_TIME',
      'The receiving server did not supply its own time, so the correction '
      + 'cannot be dated and is refused rather than dated by the caller.');
  }

  // THE ORIGINAL IS CARRIED IN THE ENTRY, not just left in place, so the trail
  // is readable on its own without re-deriving what the field used to hold.
  return {
    ok: true,
    entry: {
      field: field,
      original_at: visitData[field] === undefined ? null : visitData[field],
      proposed_at: proposal.proposed_at,
      reason_code: proposal.reason_code,
      reason_label: CORRECTION_REASONS[proposal.reason_code],
      note: note || null,
      proposed_by: actor,
      proposed_at_server: atISO,
      // PENDING ON ARRIVAL, ALWAYS. A caller that holds the approving right
      // calls approveCorrection() on the entry itself -- it does not get to
      // mint an approved one, because then "approved" would mean whatever the
      // caller decided it meant.
      status: 'pending',
      approved_by: null,
      approved_at_server: null
    }
  };
}

// approveCorrection(entry, approver, atISO, approverRole) -> verdict
//
// MUTATES NOTHING. Returns the approved entry for the caller to store in place
// of the pending one -- the array is append-only in LENGTH, and an approval is
// a transition on an entry already in it, not a second entry. Two records for
// one decision is the double-count shape, and an auditor counting corrections
// would see twice as many as were filed.
//
// ── `approverRole` IS THE H8 RESOLUTION (2026-10-15, b17, MICHAEL) ─────────
// "A one-person agency is just the owner with full access; the owner may
// approve their own visit."
//
// IT IS A ROLE AND NOT A HEADCOUNT, deliberately. The alternative that was
// NOT built is "permit self-approval when the agency has one employee", and it
// is the worse design in a way worth writing down: it is a rule that deletes
// itself the moment somebody is hired, it needs a roster COUNT at approval
// time (an extra query, on a path that currently needs none), and a miscounted
// roster would silently re-open self-approval for a ten-person agency. An
// OWNER is an owner whether the agency has one employee or fifty, and the
// authority Michael described is the owner's authority.
//
// SO A ONE-PERSON AGENCY NEEDS NO SPECIAL CASE AT ALL -- which is the whole
// point of the resolution. It is the owner, the owner may self-approve, and
// nothing anywhere has to know the agency is one person.
//
// THE TRAIL STILL SAYS SO. A self-approved entry carries `self_approved: true`
// and `self_approval_basis: 'owner'`, because b13's `self_approved: true`
// marking was the right half of the wrong answer: marking it and allowing
// EVERYONE was wrong, and allowing the owner without marking it would lose the
// one fact an auditor needs -- that this correction had no second party.
//
// BACKWARD COMPATIBLE. `approverRole` undefined behaves exactly as before:
// self-approval refused. Every existing caller that does not pass it keeps the
// b16 behaviour, which is what arm S11 of api/b14-clock-approval-two-person.test.js
// already asserts and which must not move.
function approveCorrection(entry, approver, atISO, approverRole) {
  if (!entry || typeof entry !== 'object') {
    return refuse('NO_ENTRY', 'There is no correction at that position to approve.');
  }
  if (entryIsApproved(entry)) {
    return refuse('ALREADY_APPROVED',
      'That correction is already in effect (approved by '
      + JSON.stringify(entry.approved_by || 'an earlier filer') + ').'
      + ' Nothing was written: a second approval record for one decision would '
      + 'double-count at audit.');
  }
  if (!approver) {
    return refuse('NO_APPROVER',
      'An approval is attributed or it is not an approval. The caller must '
      + 'supply the employee id from the verified session, never the payload.');
  }
  // ── THE APPROVER MUST DIFFER FROM THE SUBMITTER (2026-10-15, Michael) ────
  // b13 MARKED this case (`self_approved: true`) and allowed it, on the
  // argument that a one-person agency has nobody else and refusing would
  // strand them. MICHAEL DECIDED THE OTHER WAY: an approval by the submitter
  // is not an approval, so it is refused rather than flagged.
  //
  // IT LIVES HERE AND NOT ONLY IN THE HANDLER. A rule enforced in one branch
  // of one endpoint is a rule the next caller does not get, and this module
  // already owns every other correction rule -- the reason vocabulary, the
  // attribution, the server time. The handler maps this to 403.
  //
  // THE CONSEQUENCE IS NAMED, NOT HIDDEN: in a one-person agency the owner IS
  // the assigned caregiver and there is now NO route to make any correction
  // effective. That is the decided trade and it is a workflow change, not a
  // side effect.
  const isSelf = String(entry.proposed_by) === String(approver);
  const ownerSelf = isSelf && String(approverRole) === 'owner';
  if (isSelf && !ownerSelf) {
    return refuse('SELF_APPROVAL_REFUSED',
      'This correction was submitted by '
      + JSON.stringify(String(entry.proposed_by))
      + ' and cannot be approved by the same person. ANOTHER scheduler or '
      + 'manager has to approve it before payroll or an EVV export uses it -- '
      + 'an edited EVV time with no second party cannot be told from a '
      + 'fabricated one, which is the whole reason the submission is pending. '
      + 'THE ONE EXCEPTION IS THE OWNER, who may approve their own (2026-10-15, '
      + 'Michael): a one-person agency is the owner with full access. '
      + 'Nothing was written.');
  }
  if (parseISO(atISO) === null) {
    return refuse('NO_SERVER_TIME',
      'The receiving server did not supply its own time, so the approval '
      + 'cannot be dated and is refused rather than dated by the caller.');
  }
  // b17: `self_approved` is stamped ONLY when it really was a self-approval,
  // and it is stamped rather than inferred later -- the entry is the record,
  // and "was there a second party" is the one question an auditor asks of a
  // corrected EVV time. `approved_at_server` is set on BOTH paths, which b16's
  // freeze depends on: an approval with no instant lands in the undatable
  // bucket, and for a one-person agency that would be EVERY correction.
  return { ok: true, entry: Object.assign({}, entry, ownerSelf
    ? { status: 'approved', approved_by: approver, approved_at_server: atISO,
        self_approved: true, self_approval_basis: 'owner' }
    : { status: 'approved', approved_by: approver, approved_at_server: atISO }) };
}

// ── A CORRECTION IS APPROVED **AS AT** A MOMENT (2026-10-15, b16) ──────────
// MICHAEL'S DECISION: paid periods are FROZEN. A correction approved after a
// pay run never rewrites a closed total; it posts as an adjustment line in the
// next period. That makes "is this correction in effect" a question with a
// TIME in it, and the time belongs HERE, in the one function that decides what
// approved means -- not in sen-payroll.js, which would then hold a second copy
// of the approval rule, which is exactly the shape F1 was.
//
// THREE ANSWERS, NOT TWO, and the third is the one that matters:
//
//   asOf is null          -> no freeze in play. Current truth. Every existing
//                            caller, unchanged.
//   approved_at_server
//     parses and <= asOf  -> it WAS in the as-paid basis. In effect.
//     parses and  > asOf  -> it was NOT. NOT in effect as at asOf; the caller
//                            pays it forward as an adjustment.
//     does not parse      -> CANNOT TELL. Treated as in effect on the as-paid
//                            basis AND COUNTED in `undatable`, because every
//                            correction filed before 2026-10-14 is approved by
//                            the no-status rule above and carries no
//                            `approved_at_server` at all. Dropping them would
//                            un-pay live corrected visits; applying them
//                            silently would claim a verified basis nobody can
//                            check. PR §1.11 -- could-not-tell is never folded
//                            into either answer.
function approvedAsOf(e, asOfMs) {
  if (!entryIsApproved(e)) return false;
  if (asOfMs === null) return true;
  const t = parseISO(e.approved_at_server);
  if (t === null) return true;
  return t <= asOfMs;
}

/** True when an approved entry carries no readable approval instant, so it
 *  cannot be placed on either side of a freeze. Counted, never silent. */
function undatableApproval(e) {
  return entryIsApproved(e) && parseISO(e.approved_at_server) === null;
}

// effectiveClock(visitData, field) -> { value, corrected, entry }
//
// What a reader should SEE. The latest correction wins for display; the
// original is still in the record and is returned alongside, because a screen
// that shows only the corrected value has quietly become the overwrite this
// module exists to avoid.
//
// AS OF NOW, DELIBERATELY. This is the signature every caller already uses and
// it keeps meaning "current truth": the EVV readiness check and the client's
// anomaly checks want the same answer a pay run for an OPEN period gets, which
// is the whole of F2. Only a run of a CLOSED period passes an asOf, through
// effectiveClockAsOf below.
function effectiveClock(visitData, field) {
  return effectiveClockAsOf(visitData, field, null);
}

// effectiveClockAsOf(visitData, field, asOfISO) -> same shape, plus `undatable`
//
// `asOfISO` null (or unreadable -- see the caller's refusal) means no freeze.
function effectiveClockAsOf(visitData, field, asOfISO) {
  visitData = visitData || {};
  const asOfMs = asOfISO === null || asOfISO === undefined ? null : parseISO(asOfISO);
  const original = visitData[field] === undefined ? null : visitData[field];
  const list = Array.isArray(visitData.clock_corrections) ? visitData.clock_corrections : [];
  const mine = list.filter(function (c) { return c && c.field === field; });
  // ── ONLY AN APPROVED CORRECTION MOVES THE NUMBER (2026-10-15, T16) ──────
  // This used to take the latest entry of any kind. With a caregiver able to
  // SUBMIT one through the ordinary clock route, that would make a
  // self-asserted time effective the instant it was sent -- the overwrite
  // back, with a trail attached. "A scheduler approves it before payroll uses
  // it" is implemented HERE, in the function payroll reads, and not only as a
  // field on the entry: a `pending` nothing consults is a decoration.
  const approved = mine.filter(function (c) { return approvedAsOf(c, asOfMs); });
  const pending = mine.filter(function (c) { return !entryIsApproved(c); });
  // APPROVED, BUT NOT YET as at asOf. Named separately from `pending` because
  // the two are different facts going to different people: a pending entry
  // needs a scheduler, a not-yet entry needs an adjustment line. Folding them
  // together would make the carry-forward invisible.
  const notYet = asOfMs === null ? []
    : mine.filter(function (c) { return entryIsApproved(c) && !approvedAsOf(c, asOfMs); });
  const base = {
    // SAID, NOT DROPPED. A submission no screen shows is a submission nobody
    // will ever approve, which is the refusal again by a slower route.
    pending: pending.length ? true : false,
    pending_count: pending.length,
    pending_entries: pending.length ? pending : null,
    // The carry-forward set, and the count of approvals that cannot be placed
    // on either side of the freeze. Both are 0/[] when no asOf is in play, so
    // every existing caller sees the shape it saw before plus two zeroes.
    not_yet_count: notYet.length,
    not_yet_entries: notYet.length ? notYet : null,
    undatable: asOfMs === null ? 0 : mine.filter(undatableApproval).length
  };
  if (!approved.length) {
    return Object.assign({ value: original, corrected: false, entry: null,
                           original_at: original }, base);
  }
  const latest = approved[approved.length - 1];
  return Object.assign({
    value: latest.proposed_at, corrected: true, entry: latest,
    original_at: original
  }, base);
}

module.exports = {
  FUTURE_TOLERANCE_MS: FUTURE_TOLERANCE_MS,
  PAST_FLAG_MS: PAST_FLAG_MS,
  CLOCK_FIELDS: CLOCK_FIELDS,
  CORRECTION_REASONS: CORRECTION_REASONS,
  CORRECTION_STATUS: CORRECTION_STATUS,
  checkClockEvent: checkClockEvent,
  proposeCorrection: proposeCorrection,
  approveCorrection: approveCorrection,
  entryIsApproved: entryIsApproved,
  undatableApproval: undatableApproval,
  effectiveClock: effectiveClock,
  effectiveClockAsOf: effectiveClockAsOf
};
