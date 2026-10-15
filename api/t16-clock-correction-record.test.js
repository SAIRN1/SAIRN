// api/t16-clock-correction-record.test.js
//
// Run:  node api/t16-clock-correction-record.test.js
//
// T16, AS DECIDED BY MICHAEL ON 2026-10-15, and it REPLACES hank's own N1
// refusal rather than sitting beside it.
//
// The defect both answers: the `sen_visits action=write` caregiver branch
// copied every EVV field straight over a row that starts as a copy of the
// stored one, so a SECOND write carrying `clock_in_at` REPLACED a recorded
// EVV time with no trail -- on a path any caregiver reaches on their own
// visit. checkClockEvent refuses only the impossible and explicitly allows a
// PAST time, so an earlier clock-in was accepted and stored.
//
// b12 (N1) closed it by REFUSING the second write: 409 CLOCK_ALREADY_RECORDED,
// nothing written. cody's T16 arm asserted instead that the prior value be
// KEPT OR APPENDED. Both close the silent overwrite; the refusal admits no
// edit at all, which left a caregiver who clocked in at the wrong time on
// their own visit with no route -- `propose_clock_correction` is
// scheduler-only.
//
// THE DECISION: keep the original, append a correction record carrying the old
// value, the new value, the actor, a reason and a timestamp. A caregiver may
// SUBMIT a correction; a scheduler APPROVES it before payroll uses it. So the
// entry is `pending` on arrival and the effective clock does NOT move until a
// second party approves it -- which is the EVV property the refusal was
// protecting, kept, without stranding the caregiver.
//
// Every arm drives the real `api/sd-data.js` handler and the real
// `api/_lib/sen-evv-clock.js`. `writes` records every POST so an arm can
// assert what was actually stored -- an append that also overwrote is not an
// append.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['t16', 'fixture', String(process.pid)].join('-');
process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const KEY = 'k';
const HASH = crypto.createHash('sha256').update(KEY).digest('hex');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

const eCode = (r) => (r && r.body && r.body.error && r.body.error.code) || '';
function mockRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}

require.cache[require.resolve('./_lib/license')] = {
  id: require.resolve('./_lib/license'),
  filename: require.resolve('./_lib/license'),
  loaded: true,
  exports: {
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH,
      trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnsenior' })
  }
};
const { signSessionToken } = require('./_lib/auth');
delete require.cache[require.resolve('./sd-data.js')];
const handler = require('./sd-data.js');
const clock = require('./_lib/sen-evv-clock');

let VISIT = null;
const writes = [];
function senFetch() {
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, headers: { get: () => '' },
               text: async () => '[]',
               json: async () => [{ license_hash: HASH, employee_id: 'E1',
                                    role: 'caregiver', active: true }] };
    }
    if (method !== 'GET') {
      writes.push({ url: u, body: init && init.body });
      return { ok: true, status: 200, headers: { get: () => '' },
               text: async () => '[]',
               json: async () => [JSON.parse(init.body)] };
    }
    if (/sen_visits\?/.test(u)) {
      return { ok: true, status: 200, headers: { get: () => '' },
               text: async () => '[]',
               json: async () => (VISIT ? [VISIT] : []) };
    }
    return { ok: true, status: 200, headers: { get: () => '' },
             text: async () => '[]', json: async () => [] };
  };
}

function tok(role, employeeId) {
  return signSessionToken({ app: 'sairnsenior', employee_id: employeeId,
                            role: role, license_hash: HASH });
}
async function call(action, payload, role, employeeId) {
  writes.length = 0;
  global.fetch = senFetch();
  const res = mockRes();
  await handler({ method: 'POST',
    headers: { authorization: 'Bearer ' + KEY,
               'x-sd-auth': tok(role || 'caregiver', employeeId || 'E1') },
    body: { action: action, resource: 'sen_visits', payload: payload } }, res);
  return { res: res, writes: writes.slice() };
}
const visitWrite = (p) => call('write', p, 'caregiver', 'E1');
// What was actually STORED, read out of the POST body rather than out of the
// response. A handler that answers 200 and writes something else is the exact
// shape this suite exists to catch.
function stored(w) {
  if (!w.length) return null;
  try { return JSON.parse(w[w.length - 1].body).data || null; } catch (e) { return null; }
}
// ── THE FIXTURE TIMES ARE DERIVED FROM NOW, NOT PINNED ──────────────────
// The first draft used fixed 2026-10-15 stamps and every clock arm came back
// 400 CLOCK_IN_FUTURE, because checkClockEvent refuses a time ahead of the
// server that received it -- correctly. A pinned future date makes the whole
// suite measure the fixture; a pinned PAST date goes stale the other way
// (beyond PAST_FLAG_MS it picks up a LATE_REPLAY flag). Relative stamps are
// the only ones that stay the case being tested.
const H = 60 * 60 * 1000;
const NOW = Date.now();
const RECORDED = new Date(NOW - 4 * H).toISOString();
const SUBMITTED = new Date(NOW - 5 * H).toISOString();
const CLOCKED_OUT = new Date(NOW - 1 * H).toISOString();
const CLOCKED_OUT_LATER = new Date(NOW - 0.5 * H).toISOString();
function visitWithClockIn() {
  return { visit_id: 'V1', assigned_employee_id: 'E1',
           data: { status: 'in_progress', clock_in_at: RECORDED } };
}

console.log('T16. a second clock write APPENDS a correction and never replaces\n');

(async () => {
  // ── 1. THE FIRST WRITE IS UNTOUCHED ─────────────────────────────────────
  VISIT = { visit_id: 'V1', assigned_employee_id: 'E1', data: { status: 'scheduled' } };
  {
    const { res, writes: w } = await visitWrite({ id: 'V1', clock_in_at: RECORDED });
    const d = stored(w) || {};
    is(res.statusCode === 200 && d.clock_in_at === RECORDED
       && d.clock_corrections === undefined,
       'T16a. CONTROL -- a FIRST clock-in on a visit with none recorded is '
     + 'stored as the clock time itself and raises NO correction entry. '
     + 'Without this arm the whole design could be "every clock write is a '
     + 'pending correction" and nothing would ever be an EVV record',
       'status=' + res.statusCode + ' stored=' + JSON.stringify(d).slice(0, 180));
  }

  // ── 2. THE ARM THE DECISION IS ───────────────────────────────────────────
  VISIT = visitWithClockIn();
  {
    const { res, writes: w } = await visitWrite({ id: 'V1', clock_in_at: SUBMITTED });
    const d = stored(w) || {};
    const list = Array.isArray(d.clock_corrections) ? d.clock_corrections : [];
    is(res.statusCode === 200 && w.length === 1,
       'T16b. a DIFFERENT clock_in_at over a recorded one is ACCEPTED, not '
     + 'refused. This is the half that replaces N1: a caregiver who clocked in '
     + 'at the wrong time on their own visit had no route at all under the 409, '
     + 'because propose_clock_correction is scheduler-only',
       'status=' + res.statusCode + ' code=' + eCode(res) + ' writes=' + w.length);
    is(d.clock_in_at === RECORDED,
       'T16c. ...and THE ORIGINAL IS STILL THE CLOCK TIME ON THE ROW. An '
     + 'append that also moved the field would be the overwrite wearing a '
     + 'trail -- "a state audit that finds an edited time with no trail cannot '
     + 'tell a typo correction from a fabrication", and a trail beside a '
     + 'silently moved value answers that no better',
       'stored clock_in_at=' + JSON.stringify(d.clock_in_at)
     + ' expected=' + JSON.stringify(RECORDED));
    is(list.length === 1,
       'T16d. ...and exactly ONE correction entry was appended',
       'entries=' + JSON.stringify(list).slice(0, 220));
    const e = list[0] || {};
    is(e.field === 'clock_in_at' && e.original_at === RECORDED
       && e.proposed_at === SUBMITTED,
       'T16e. ...carrying the OLD value and the NEW value. Both numbers, on '
     + 'the record, which is the whole point of an additive correction',
       JSON.stringify(e).slice(0, 240));
    is(e.proposed_by === 'E1',
       'T16f. ...attributed to the actor from the VERIFIED SESSION. A '
     + 'correction attributed from the payload is a correction attributed by '
     + 'whoever is submitting it',
       'proposed_by=' + JSON.stringify(e.proposed_by));
    is(typeof e.reason_code === 'string' && e.reason_code
       && typeof e.reason_label === 'string' && e.reason_label,
       'T16g. ...with a reason from the closed vocabulary and its label. A '
     + 'correction with a blank reason is the silent drop with extra steps -- '
     + 'and the caller supplied none here, so the route\'s own code is used '
     + 'and is NOT left empty',
       'reason_code=' + JSON.stringify(e.reason_code)
     + ' label=' + JSON.stringify(e.reason_label));
    is(typeof e.proposed_at_server === 'string'
       && !isNaN(Date.parse(e.proposed_at_server)),
       'T16h. ...and a SERVER timestamp for when it was submitted, which is a '
     + 'different fact from the time being proposed',
       'proposed_at_server=' + JSON.stringify(e.proposed_at_server));
    is(e.status === 'pending',
       'T16i. ...and it is PENDING. "A scheduler approves it before payroll '
     + 'uses it" is the decision, so an unapproved self-submitted time must '
     + 'not be indistinguishable from an approved one',
       'status=' + JSON.stringify(e.status));
    is(res.body && res.body.clock_correction
       && res.body.clock_correction.status === 'pending'
       && /approv/i.test(JSON.stringify(res.body.clock_correction)),
       'T16j. ...and the CALLER IS TOLD at the time -- the submission is '
     + 'pending and needs an approval. A 200 that looks like an accepted clock '
     + 'change is affirmative false success, which is worse than a refusal',
       JSON.stringify(res.body).slice(0, 240));
  }

  // ── 3. PAYROLL DOES NOT SEE A PENDING CORRECTION ────────────────────────
  console.log('\nT16. a pending correction does not move the effective clock');
  {
    const pending = { clock_in_at: RECORDED,
      clock_corrections: [{ field: 'clock_in_at', original_at: RECORDED,
                            proposed_at: SUBMITTED, reason_code: 'transcription_error',
                            proposed_by: 'E1', proposed_at_server: RECORDED,
                            status: 'pending' }] };
    const eff = clock.effectiveClock(pending, 'clock_in_at');
    is(eff.value === RECORDED && eff.corrected === false,
       'T16k. effectiveClock IGNORES a pending entry -- the effective value is '
     + 'still the recorded one. This is the arm that carries the approval '
     + 'requirement into the number payroll reads; without it `pending` is a '
     + 'decoration',
       JSON.stringify(eff).slice(0, 200));
    is(eff.pending === true || (Array.isArray(eff.pending) && eff.pending.length === 1)
       || (eff.pending_count === 1),
       'T16l. ...and it SAYS a correction is awaiting approval rather than '
     + 'dropping it from view. A submission nobody can see is a submission '
     + 'nobody will approve',
       JSON.stringify(eff).slice(0, 200));
    const approved = { clock_in_at: RECORDED,
      clock_corrections: [{ field: 'clock_in_at', original_at: RECORDED,
                            proposed_at: SUBMITTED, reason_code: 'transcription_error',
                            proposed_by: 'E1', proposed_at_server: RECORDED,
                            status: 'approved', approved_by: 'S1',
                            approved_at_server: RECORDED }] };
    const effA = clock.effectiveClock(approved, 'clock_in_at');
    is(effA.value === SUBMITTED && effA.corrected === true
       && effA.original_at === RECORDED,
       'T16m. ...and an APPROVED entry does move it, with the original still '
     + 'returned beside it',
       JSON.stringify(effA).slice(0, 200));
    // LEGACY ENTRIES HAVE NO `status` AND MUST NOT BE UN-CORRECTED BY THIS
    // CHANGE. Every correction written before today was effective the moment
    // it was filed by a scheduler, and reading them as pending would silently
    // revert live records to their uncorrected times.
    const legacy = { clock_in_at: RECORDED,
      clock_corrections: [{ field: 'clock_in_at', original_at: RECORDED,
                            proposed_at: SUBMITTED, reason_code: 'transcription_error',
                            proposed_by: 'boss', proposed_at_server: RECORDED }] };
    const effL = clock.effectiveClock(legacy, 'clock_in_at');
    is(effL.value === SUBMITTED && effL.corrected === true,
       'T16n. CONTROL -- an entry written BEFORE this change, with no `status` '
     + 'at all, is still effective. Treating a missing status as pending would '
     + 'silently revert every live corrected visit to its uncorrected time, '
     + 'which is this change causing the defect it is fixing',
       JSON.stringify(effL).slice(0, 200));
  }

  // ── 4. THE APPROVAL IS A SECOND PARTY ───────────────────────────────────
  console.log('\nT16. the approval route, and who may use it');
  {
    VISIT = { visit_id: 'V1', assigned_employee_id: 'E1',
      data: { clock_in_at: RECORDED,
              clock_corrections: [{ field: 'clock_in_at', original_at: RECORDED,
                proposed_at: SUBMITTED, reason_code: 'transcription_error',
                reason_label: 'The time was entered incorrectly',
                proposed_by: 'E1', proposed_at_server: RECORDED,
                status: 'pending' }] } };
    const bad = await call('approve_clock_correction',
                           { id: 'V1', correction_index: 0 }, 'caregiver', 'E1');
    is(bad.res.statusCode === 403 && bad.writes.length === 0,
       'T16o. a CAREGIVER cannot approve -- 403 and nothing written. The whole '
     + 'reason the correction is pending is that an unverified self-assertion '
     + 'is what EVV exists to stop; a caregiver who can approve their own '
     + 'submission has the overwrite back with two extra fields',
       'status=' + bad.res.statusCode + ' code=' + eCode(bad.res)
     + ' writes=' + bad.writes.length);
    const good = await call('approve_clock_correction',
                            { id: 'V1', correction_index: 0 }, 'owner', 'S1');
    const d = stored(good.writes) || {};
    const e = (Array.isArray(d.clock_corrections) ? d.clock_corrections : [])[0] || {};
    is(good.res.statusCode === 200 && e.status === 'approved',
       'T16p. a SCHEDULER-tier caller approves it, and the entry becomes '
     + 'approved',
       'status=' + good.res.statusCode + ' code=' + eCode(good.res)
     + ' entry=' + JSON.stringify(e).slice(0, 200));
    is(e.approved_by === 'S1' && typeof e.approved_at_server === 'string'
       && !isNaN(Date.parse(e.approved_at_server)),
       'T16q. ...recording WHO approved it and WHEN, from the session and the '
     + 'server. An approval with no approver is the same unattributed act the '
     + 'submission was not allowed to be',
       JSON.stringify(e).slice(0, 220));
    is(e.original_at === RECORDED && e.proposed_at === SUBMITTED
       && d.clock_in_at === RECORDED,
       'T16r. ...and APPROVAL STILL DOES NOT MOVE THE FIELD. The row\'s '
     + 'clock_in_at is the caregiver\'s original forever; what approval moves '
     + 'is which value effectiveClock reports',
       'row clock_in_at=' + JSON.stringify(d.clock_in_at)
     + ' entry=' + JSON.stringify(e).slice(0, 160));
    const again = await call('approve_clock_correction',
                             { id: 'V1', correction_index: 0 }, 'owner', 'S1');
    is(again.res.statusCode === 200 || again.res.statusCode === 409,
       'T16s. re-approving is answered deliberately rather than silently '
     + 'appending a second approval. Either is defensible; what is not is a '
     + 'second approval record for one decision',
       'status=' + again.res.statusCode + ' code=' + eCode(again.res));
    const oob = await call('approve_clock_correction',
                           { id: 'V1', correction_index: 7 }, 'owner', 'S1');
    is(oob.res.statusCode === 400 && oob.writes.length === 0,
       'T16t. an index that is not there is refused 400 with nothing written, '
     + 'not quietly ignored with a 200',
       'status=' + oob.res.statusCode + ' code=' + eCode(oob.res)
     + ' writes=' + oob.writes.length);
  }

  // ── 5. THE CONTROLS THAT STOP THIS BECOMING A WIDER CHANGE ──────────────
  console.log('\nT16 controls -- what must NOT have moved');
  {
    VISIT = visitWithClockIn();
    const { res, writes: w } = await visitWrite({ id: 'V1', clock_in_at: RECORDED });
    const d = stored(w) || {};
    is(res.statusCode === 200 && d.clock_corrections === undefined,
       'T16u. CONTROL -- an IDENTICAL re-send appends NOTHING. sairnsenior '
     + 'queues clock events offline and replays them UNCHANGED, so the same '
     + 'visit legitimately arrives twice; turning every replay into a pending '
     + 'correction would bury the real ones',
       'status=' + res.statusCode + ' stored=' + JSON.stringify(d).slice(0, 160));
  }
  {
    VISIT = visitWithClockIn();
    const { res, writes: w } = await visitWrite(
      { id: 'V1', clock_out_at: CLOCKED_OUT });
    const d = stored(w) || {};
    is(res.statusCode === 200 && d.clock_out_at === CLOCKED_OUT
       && d.clock_corrections === undefined,
       'T16v. CONTROL -- the OTHER half of the visit still writes normally. '
     + 'The rule is per field and a clock-out after a clock-in is the ordinary '
     + 'case, not a correction',
       'status=' + res.statusCode + ' stored=' + JSON.stringify(d).slice(0, 160));
  }
  {
    VISIT = { visit_id: 'V1', assigned_employee_id: 'E1',
              data: { clock_in_at: RECORDED, clock_out_at: CLOCKED_OUT } };
    const { res, writes: w } = await visitWrite(
      { id: 'V1', clock_out_at: CLOCKED_OUT_LATER });
    const d = stored(w) || {};
    const list = Array.isArray(d.clock_corrections) ? d.clock_corrections : [];
    is(res.statusCode === 200 && d.clock_out_at === CLOCKED_OUT
       && list.length === 1 && list[0].field === 'clock_out_at',
       'T16w. clock_out_at is covered by the same rule, not just clock_in_at. '
     + 'A rule proven on one of two fields covers one of two fields',
       'status=' + res.statusCode + ' stored=' + JSON.stringify(d).slice(0, 200));
  }
  {
    // THE SCHEDULER GUARD IS NOT WEAKENED BY ANY OF THIS. EVV fields are never
    // accepted from a scheduler-tier caller, on a new visit or an edit.
    VISIT = visitWithClockIn();
    const { writes: w } = await call('write',
      { id: 'V1', clock_in_at: SUBMITTED, assigned_employee_id: 'E1' }, 'owner', 'S1');
    const d = stored(w) || {};
    const list = Array.isArray(d.clock_corrections) ? d.clock_corrections : [];
    is(d.clock_in_at === RECORDED && list.length === 0,
       'T16x. CONTROL -- a SCHEDULER-tier write still cannot touch an EVV '
     + 'field, and does not get a correction entry as a side door either. '
     + 'Their route is propose_clock_correction, which this change leaves '
     + 'alone',
       'stored=' + JSON.stringify(d).slice(0, 200));
  }
  {
    // THE IMPOSSIBLE IS STILL REFUSED. A correction trail must not become a
    // way to store a time checkClockEvent would have rejected.
    VISIT = visitWithClockIn();
    const future = new Date(Date.now() + 60 * 60 * 1000).toISOString();
    const { res, writes: w } = await visitWrite({ id: 'V1', clock_in_at: future });
    is(res.statusCode === 400 && w.length === 0,
       'T16y. CONTROL -- a time AHEAD of the server that received it is still '
     + 'refused 400 with nothing written. The append path must not become a '
     + 'route around checkClockEvent',
       'status=' + res.statusCode + ' code=' + eCode(res) + ' writes=' + w.length);
  }
  {
    // A CALLER-SUPPLIED REASON IS HONOURED. The route's own code is a default,
    // not a replacement for what the caregiver said.
    VISIT = visitWithClockIn();
    const { writes: w } = await visitWrite({ id: 'V1', clock_in_at: SUBMITTED,
      correction: { reason_code: 'device_clock_wrong' } });
    const e = ((stored(w) || {}).clock_corrections || [])[0] || {};
    is(e.reason_code === 'device_clock_wrong',
       'T16z. a reason the caller DID supply is the one recorded. The route\'s '
     + 'own code covers the silent case and does not overwrite a real one',
       'reason_code=' + JSON.stringify(e.reason_code));
  }

  {
    // ── SUPERSEDED BY MICHAEL'S b14 DECISION, 2026-10-15 ─────────────────
    // This arm asserted that a scheduler filing through
    // propose_clock_correction was APPROVED AT THE MOMENT OF FILING and
    // immediately effective, on the argument that the route is scheduler-tier
    // only so the approving authority IS the caller. The decision is that the
    // approver must DIFFER from the submitter -- and on this route they were
    // the same person by construction, so approve-at-filing is exactly what it
    // forbids. The entry now stays PENDING for a second scheduler.
    //
    // Rewritten rather than deleted, so the route stays covered here too; the
    // full two-person contract is driven in
    // api/b14-clock-approval-two-person.test.js.
    VISIT = { visit_id: 'V1', assigned_employee_id: 'E1',
              data: { clock_in_at: RECORDED } };
    const { res, writes: w } = await call('propose_clock_correction',
      { id: 'V1', correction: { field: 'clock_in_at', proposed_at: SUBMITTED,
                                reason_code: 'transcription_error' } },
      'owner', 'S1');
    const d = stored(w) || {};
    const e = ((d.clock_corrections) || [])[0] || {};
    const eff = clock.effectiveClock(d, 'clock_in_at');
    is(res.statusCode === 200 && e.status === 'pending'
       && eff.value === RECORDED && eff.corrected === false
       && d.clock_in_at === RECORDED,
       'T16aa. a SCHEDULER filing through propose_clock_correction files it '
     + 'PENDING and does NOT make it effective -- the filer cannot be the '
     + 'approver. The row\'s own clock_in_at is still untouched either way, '
     + 'which is the property that has not moved',
       'status=' + res.statusCode + ' entry=' + JSON.stringify(e).slice(0, 200)
     + ' eff=' + JSON.stringify(eff.value));
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => { console.error(e); process.exit(1); });
