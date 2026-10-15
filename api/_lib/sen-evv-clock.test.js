// api/_lib/sen-evv-clock.test.js
//
//   node api/_lib/sen-evv-clock.test.js
//
// THE TWO SAIRNsenior EVV FINDINGS, VERIFIED IN api/sd-data.js BEFORE ANY OF
// THIS WAS BUILT -- and one of the two turned out not to be a gap.
//
//   REAL:  the caregiver branch stores clock_in_at/clock_out_at VERBATIM from
//          the payload. No server-time comparison, no ordering check, no bound.
//          A wrong handset clock produces a wrong EVV record silently.
//   NOT A GAP: office staff cannot edit a clock time because the scheduler
//          branch refuses EVV fields ON PURPOSE -- "so a scheduler can never
//          forge a clock-in/out". This module does not weaken that guard; a
//          correction is ADDITIVE and never replaces the caregiver's value.
//
// ── THE ARM THAT MATTERS MOST IS THE ONE THAT DOES NOT REFUSE ────────────
// "Use the server's clock" destroys the offline path, and sairnsenior's own
// queue comment says why: re-stamping on flush "would produce an EVV record
// that is precise, plausible and false -- worse than a missing one". So a LATE
// replay must pass, carrying its skew, and B2 is that arm. Without it every
// refusal below is satisfied by a module that refuses everything.

'use strict';
const assert = require('assert');
const c = require('./sen-evv-clock');

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { console.log('  ok   ' + name); pass++; }
  else { console.log('  FAIL ' + name + (detail ? '\n        ' + detail : '')); fail++; }
}
function section(t) { console.log('\n' + t); }

const NOW = '2026-09-26T12:00:00.000Z';
const nowMs = Date.parse(NOW);
const iso = (deltaMs) => new Date(nowMs + deltaMs).toISOString();

section('A. THE SERVER RECORDS ITS OWN OBSERVATION BESIDE THE CLAIM');
let r = c.checkClockEvent({ clock_in_at: iso(-30 * 1000) }, {}, NOW);
ok('an ordinary clock-in is ACCEPTED', r.ok === true && r.checked === true, JSON.stringify(r));
ok('...and the claimed value is NOT replaced -- the module returns no clock_in_at',
   r.ok && r.stamps.clock_in_at === undefined, JSON.stringify(r.stamps));
ok('...the server time is recorded beside it',
   r.ok && r.stamps.clock_in_received_at === NOW, JSON.stringify(r.stamps));
ok('...and so is the skew, which is the auditable fact',
   r.ok && r.stamps.clock_in_skew_ms === -30000, JSON.stringify(r.stamps));

section('B. THE OFFLINE PATH MUST STILL WORK -- the control on every refusal');
r = c.checkClockEvent({ clock_in_at: iso(-3 * 60 * 60 * 1000) }, {}, NOW);
ok('B1 a three-hour-late replay is ACCEPTED, not refused',
   r.ok === true && !r.flags.length, JSON.stringify(r));
r = c.checkClockEvent({ clock_in_at: iso(-30 * 24 * 60 * 60 * 1000) }, {}, NOW);
ok('B2 a THIRTY-DAY-late replay is ACCEPTED and FLAGGED, never refused -- '
   + 're-stamping it would be precise, plausible and false',
   r.ok === true && r.flags.some(function (f) { return f.code === 'LATE_REPLAY'; }),
   JSON.stringify(r));

section('C. THE REFUSALS -- only the impossible');
r = c.checkClockEvent({ clock_in_at: iso(10 * 60 * 1000) }, {}, NOW);
ok('C1 a time ten minutes in the FUTURE is refused',
   r.ok === false && r.error.code === 'CLOCK_IN_FUTURE', JSON.stringify(r.error || {}));
ok('...and the message says why the future is different from a slow sync',
   r.ok === false && /only ever runs the other way/.test(r.error.message));
r = c.checkClockEvent({ clock_in_at: iso(60 * 1000) }, {}, NOW);
ok('C2 a ONE-minute future skew is tolerated -- handset drift is not forgery',
   r.ok === true, JSON.stringify(r.error || {}));
r = c.checkClockEvent({ clock_in_at: 'yesterday afternoon' }, {}, NOW);
ok('C3 an unparseable timestamp is refused, not stored',
   r.ok === false && r.error.code === 'CLOCK_UNPARSEABLE', JSON.stringify(r.error || {}));

section('D. ORDERING, AGAINST THE STORED VALUE -- a clock-out arrives alone');
r = c.checkClockEvent({ clock_out_at: iso(-2 * 60 * 60 * 1000) },
                      { clock_in_at: iso(-60 * 60 * 1000) }, NOW);
ok('D1 a clock-out BEFORE the STORED clock-in is refused',
   r.ok === false && r.error.code === 'CLOCK_OUT_BEFORE_IN', JSON.stringify(r.error || {}));
ok('...THIS IS THE ARM A PAYLOAD-ONLY CHECK WOULD MISS: the clock-in is not in '
   + 'this payload at all, it is on the visit',
   r.ok === false);
r = c.checkClockEvent({ clock_out_at: iso(-30 * 60 * 1000) },
                      { clock_in_at: iso(-60 * 60 * 1000) }, NOW);
ok('D2 a normal clock-out after the stored clock-in is accepted', r.ok === true,
   JSON.stringify(r.error || {}));

section('E. COULD-NOT-CHECK IS A THIRD STATE');
r = c.checkClockEvent({ clock_in_at: iso(0) }, {}, null);
ok('E1 no server time refuses rather than skipping the check',
   r.ok === false && r.error.code === 'NO_SERVER_TIME', JSON.stringify(r.error || {}));
r = c.checkClockEvent({ services_notes: 'tidied the kitchen' }, {}, NOW);
ok('E2 a payload with no clock field is ok:true but checked:FALSE -- not a pass',
   r.ok === true && r.checked === false, JSON.stringify(r));

section('F. A CORRECTION IS ADDITIVE, ATTRIBUTED, AND CODED');
const visit = { clock_in_at: iso(-4 * 60 * 60 * 1000) };
let p = c.proposeCorrection(visit,
  { field: 'clock_in_at', proposed_at: iso(-5 * 60 * 60 * 1000),
    reason_code: 'device_clock_wrong' }, 'emp-7', NOW);
ok('F1 a coded correction is accepted', p.ok === true, JSON.stringify(p.error || {}));
ok('...and it carries the ORIGINAL, so the trail reads on its own',
   p.ok && p.entry.original_at === visit.clock_in_at, JSON.stringify(p.entry || {}));
ok('...and who proposed it, from the session and not the payload',
   p.ok && p.entry.proposed_by === 'emp-7');
ok('F2 THE MODULE NEVER RETURNS A REPLACEMENT VALUE for clock_in_at, so a '
   + 'caller cannot overwrite the caregiver record by copying a field across',
   p.ok && p.entry.clock_in_at === undefined && p.clock_in_at === undefined,
   JSON.stringify(p));

p = c.proposeCorrection(visit, { field: 'clock_in_at', proposed_at: iso(0),
                                 reason_code: 'because' }, 'emp-7', NOW);
ok('F3 an unknown reason code is refused', p.ok === false && p.error.code === 'BAD_REASON_CODE',
   JSON.stringify(p.error || {}));
p = c.proposeCorrection(visit, { field: 'clock_in_at', proposed_at: iso(0),
                                 reason_code: 'other', note: 'x' }, 'emp-7', NOW);
ok('F4 reason_code "other" with no real note is refused -- it is the category '
   + 'that swallows every real reason',
   p.ok === false && p.error.code === 'NOTE_REQUIRED', JSON.stringify(p.error || {}));
p = c.proposeCorrection(visit, { field: 'clock_in_at', proposed_at: iso(0),
                                 reason_code: 'device_clock_wrong' }, null, NOW);
ok('F5 an unattributed correction is refused', p.ok === false && p.error.code === 'NO_ACTOR');
p = c.proposeCorrection(visit, { field: 'status', proposed_at: iso(0),
                                 reason_code: 'device_clock_wrong' }, 'emp-7', NOW);
ok('F6 a correction to a non-clock field is refused -- this is not a general '
   + 'edit channel into the EVV record', p.ok === false && p.error.code === 'BAD_FIELD');

section('G. READING A CORRECTED VISIT SHOWS BOTH NUMBERS');
// ── G1 WAS A STALE EXPECTATION, NOT A DEFECT (corrected 2026-10-15, hank b16)
// This fixture used the entry `proposeCorrection` returns, which is ALWAYS
// `status: 'pending'`, and then asserted `corrected === true`. That was right
// until the T16 rule landed on 2026-10-15: ONLY AN APPROVED CORRECTION MOVES
// THE NUMBER, because a caregiver can submit one through the ordinary clock
// route and a self-asserted time becoming effective on submission is the
// overwrite this module exists to prevent.
//
// So the arm was asserting the behaviour the rule was written to remove, and
// it had been red since. Fixed by APPROVING the entry -- through the module's
// own approveCorrection, with a DIFFERENT approver because self-approval is
// refused -- rather than by weakening the assertion. G1b is the paired
// control: the pending entry must still move nothing, which is the half that
// would otherwise be lost.
const pendingEntry = c.proposeCorrection(visit,
  { field: 'clock_in_at', proposed_at: iso(-5 * 3600000),
    reason_code: 'device_clock_wrong' }, 'emp-7', NOW).entry;
const approvedEntry = c.approveCorrection(pendingEntry, 'sched-1', NOW).entry;
const corrected = Object.assign({}, visit, { clock_corrections: [approvedEntry] });
const stillPending = Object.assign({}, visit, { clock_corrections: [pendingEntry] });
const eff = c.effectiveClock(corrected, 'clock_in_at');
ok('G1 an APPROVED correction is what a reader sees', eff.corrected === true
   && eff.value === iso(-5 * 3600000), JSON.stringify(eff));
ok('G1b CONTROL -- a PENDING correction moves nothing and is reported as '
   + 'pending rather than dropped', (function () {
     const p = c.effectiveClock(stillPending, 'clock_in_at');
     return p.corrected === false && p.value === visit.clock_in_at
       && p.pending === true && p.pending_count === 1;
   })(), JSON.stringify(c.effectiveClock(stillPending, 'clock_in_at')));
ok('G2 ...and the ORIGINAL is returned alongside it, so a screen showing only '
   + 'the correction has to do that deliberately',
   eff.original_at === visit.clock_in_at, JSON.stringify(eff));
const uncorrected = c.effectiveClock(visit, 'clock_in_at');
ok('G3 an uncorrected visit reports corrected:false and its own value',
   uncorrected.corrected === false && uncorrected.value === visit.clock_in_at);

section('H. CONTROL -- the guard SAIRNsenior already has is not weakened');
// ── H1 IS AN ALLOWLIST AND THAT IS DELIBERATE, BUT IT HAD GONE STALE ──────
// The arm's job is to force a HUMAN DECISION on every new export from this
// module: nothing here may become a way to write a clock field directly, and
// an allowlist catches that where a deny-list of suspicious names would not.
//
// It was red because the list stopped at six exports while the module grew to
// twelve -- CORRECTION_STATUS and approveCorrection and entryIsApproved
// (2026-10-14/15), CLOCK_FIELDS, and b16's undatableApproval and
// effectiveClockAsOf. Updated 2026-10-15 (hank b16) to the real twelve, with
// each one's reason for being safe, because an allowlist nobody can read is an
// allowlist somebody will delete.
//
// A STALE ALLOWLIST IS WORSE THAN NONE: it was red for a week, so a NEW unsafe
// export would have changed nothing about the output a reader saw.
ok('H1 the module exports NO way to write clock_in_at directly',
   Object.keys(c).every(function (k) {
     return [
       // constants -- values, not writers
       'FUTURE_TOLERANCE_MS', 'PAST_FLAG_MS', 'CLOCK_FIELDS',
       'CORRECTION_REASONS', 'CORRECTION_STATUS',
       // pure verdicts and proposals. None of these writes anything; each
       // RETURNS what the caller must store, which is why the caller's write
       // is still the only write.
       'checkClockEvent', 'proposeCorrection', 'approveCorrection',
       'entryIsApproved', 'undatableApproval',
       // readers
       'effectiveClock', 'effectiveClockAsOf'
     ].indexOf(k) !== -1;
   }), JSON.stringify(Object.keys(c)));
ok('H2 checkClockEvent returns stamps whose keys are all *_received_at or '
   + '*_skew_ms -- never a clock field, so merging them cannot overwrite one',
   (function () {
     const s = c.checkClockEvent({ clock_in_at: iso(-10), clock_out_at: iso(-5) }, {}, NOW).stamps;
     return Object.keys(s).length === 4
       && Object.keys(s).every(function (k) { return /_received_at$|_skew_ms$/.test(k); });
   })());

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
