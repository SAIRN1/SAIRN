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
  other: 'Something else -- the note is required and must say what'
};

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

  ['clock_in_at', 'clock_out_at'].forEach(function (field) {
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
      proposed_at_server: atISO
    }
  };
}

// effectiveClock(visitData, field) -> { value, corrected, entry }
//
// What a reader should SEE. The latest correction wins for display; the
// original is still in the record and is returned alongside, because a screen
// that shows only the corrected value has quietly become the overwrite this
// module exists to avoid.
function effectiveClock(visitData, field) {
  visitData = visitData || {};
  const original = visitData[field] === undefined ? null : visitData[field];
  const list = Array.isArray(visitData.clock_corrections) ? visitData.clock_corrections : [];
  const mine = list.filter(function (c) { return c && c.field === field; });
  if (!mine.length) return { value: original, corrected: false, entry: null, original_at: original };
  const latest = mine[mine.length - 1];
  return {
    value: latest.proposed_at, corrected: true, entry: latest,
    original_at: original
  };
}

module.exports = {
  FUTURE_TOLERANCE_MS: FUTURE_TOLERANCE_MS,
  PAST_FLAG_MS: PAST_FLAG_MS,
  CORRECTION_REASONS: CORRECTION_REASONS,
  checkClockEvent: checkClockEvent,
  proposeCorrection: proposeCorrection,
  effectiveClock: effectiveClock
};
