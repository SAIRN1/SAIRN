// api/b17-one-person-agency.test.js
//
// Run:  node api/b17-one-person-agency.test.js
//
// REQUIREMENT (MICHAEL, 2026-10-15 -- H8 RESOLVED): a one-person agency is
//   just the owner with full access; the OWNER may approve their own visit.
//
// ── THE STRANDED STATE THIS REMOVES, AS b16 MEASURED IT ───────────────────
// docs/2026-10-15-hank-b16-h8-self-approval.md stated the dead end exactly:
// in a one-person agency the owner IS the assigned caregiver, so they are the
// only possible approver, so `approveCorrection` refused, so the correction
// could never become effective -- and after b16 BOTH sides agreed the visit
// was stranded: api/_lib/sen-payroll.js paid it nothing (no clock-out) and
// api/_lib/sen-evv-readiness.js reported it not EVV-ready. Unpayable AND
// un-submittable, with the only person who could fix it forbidden from doing
// so. O5 drives exactly that scenario end to end.
//
// ── IT IS A ROLE, NOT A HEADCOUNT, AND THAT IS THE DESIGN DECISION ────────
// The option NOT taken: "permit self-approval when the agency has one
// employee". It is a rule that deletes itself the moment somebody is hired, it
// needs a roster COUNT on a path that currently needs no extra query, and a
// miscounted roster would silently re-open self-approval for a ten-person
// agency. An owner is an owner at any headcount, and the authority Michael
// described is the owner's. So a one-person agency needs NO special case at
// all -- which is the whole point of the resolution.
//
// ── AND THE TRAIL STILL SAYS THERE WAS NO SECOND PARTY ───────────────────
// b13 marked self-approval (`self_approved: true`) and ALLOWED IT FOR
// EVERYONE, which was the right half of the wrong answer. b16 refused it for
// everyone. b17 allows the OWNER and keeps the mark, because "was there a
// second party" is the one question an auditor asks of a corrected EVV time.
// O3 is the arm that makes the mark mean something: an owner approving
// SOMEBODY ELSE'S correction must NOT be marked.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const CLOCK_SRC = path.join(__dirname, '_lib', 'sen-evv-clock.js');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['b17', 'onep', String(process.pid)].join('-');
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
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

const NOW = '2026-10-07T12:00:00.000Z';
const DAY = '2026-10-06';
const REC_IN = DAY + 'T09:00:00.000Z';
const COR_OUT = DAY + 'T13:00:00.000Z';   // 240 minutes, supplied by the fix

function freshClock() {
  delete require.cache[require.resolve('./_lib/sen-evv-clock')];
  return require('./_lib/sen-evv-clock');
}

// The pending entry the module itself produces -- never hand-built, because a
// hand-built entry can disagree with proposeCorrection's real shape.
function pending(clock, filer) {
  const visit = { clock_in_at: REC_IN, clock_out_at: null };
  const p = clock.proposeCorrection(visit,
    { field: 'clock_out_at', proposed_at: COR_OUT,
      reason_code: 'forgot_to_clock_out' }, filer, NOW);
  if (!p.ok) throw new Error('fixture: proposeCorrection refused: '
    + JSON.stringify(p.error));
  return p.entry;
}

// ── ABLATION on api/_lib/sen-evv-clock.js, for O7 ────────────────────────
function ablate(anchor, replacement, fn) {
  const src = fs.readFileSync(CLOCK_SRC, 'utf8');
  const n = src.split(anchor).length - 1;
  if (n !== 1) return { ok: false, why: 'anchor occurs ' + n + ' times, not 1' };
  let r;
  try {
    fs.writeFileSync(CLOCK_SRC, src.split(anchor).join(replacement));
    r = { ok: true, result: fn() };
  } finally {
    fs.writeFileSync(CLOCK_SRC, src);
    if (fs.readFileSync(CLOCK_SRC, 'utf8') !== src) {
      console.log('  HARD ERROR the ablation did not restore '
        + 'api/_lib/sen-evv-clock.js -- DO NOT COMMIT, the file on disk is a mutant');
      process.exit(1);
    }
  }
  return r;
}

const A_OWNERSELF = "const ownerSelf = isSelf && String(approverRole) === 'owner';";

// ── THE CLIENT SIDE, lifted from the real page ───────────────────────────
const HTML = (function () {
  try { return fs.readFileSync(path.join(ROOT, 'sairnsenior.html'), 'utf8'); }
  catch (e) { return null; }
})();

async function main() {
  console.log('api/b17-one-person-agency.test.js');
  console.log('  H8 resolved: the owner may approve their own, and the stranded '
            + 'state is gone');

  const clock = freshClock();

  // ── O1: THE OWNER MAY APPROVE THEIR OWN ─────────────────────────────────
  let o1 = null;
  try {
    const e = pending(clock, 'E1');
    o1 = clock.approveCorrection(e, 'E1', NOW, 'owner');
    is(o1.ok === true && o1.entry.status === 'approved'
       && o1.entry.approved_by === 'E1'
       && o1.entry.approved_at_server === NOW
       && o1.entry.self_approved === true
       && o1.entry.self_approval_basis === 'owner',
       'O1. an OWNER approving their OWN correction is ALLOWED, and the entry '
     + 'carries self_approved:true with basis \'owner\' plus a real '
     + 'approved_at_server',
       JSON.stringify(o1));
  } catch (e) {
    bad('O1. an OWNER may approve their own correction', e && e.stack);
  }

  // ── O2: CONTROL -- EVERY OTHER ROLE IS STILL REFUSED ───────────────────
  // Without this arm "self-approval is allowed" passes O1, which is b13's
  // defect restored: a caregiver's own edited EVV time effective on filing.
  for (const role of ['scheduler', 'coordinator', 'billing', 'caregiver']) {
    try {
      const e = pending(clock, 'E1');
      const v = clock.approveCorrection(e, 'E1', NOW, role);
      is(v.ok === false && v.error.code === 'SELF_APPROVAL_REFUSED',
         'O2. CONTROL -- a ' + role + ' approving their OWN is still refused '
       + 'SELF_APPROVAL_REFUSED. The exception is the OWNER, not self-approval',
         JSON.stringify(v));
    } catch (e) {
      bad('O2. CONTROL -- a ' + role + ' self-approval is still refused', e && e.stack);
    }
  }

  // ── O3: THE MARK MEANS SOMETHING ───────────────────────────────────────
  // An owner approving SOMEBODY ELSE'S correction is an ordinary two-person
  // approval and must NOT be marked. If it were, `self_approved` would mean
  // "an owner touched it" and an auditor could not find the entries that had
  // no second party.
  try {
    const e = pending(clock, 'E9');
    const v = clock.approveCorrection(e, 'E1', NOW, 'owner');
    is(v.ok === true && v.entry.status === 'approved'
       && !('self_approved' in v.entry)
       && !('self_approval_basis' in v.entry),
       'O3. an OWNER approving SOMEBODY ELSE\'S correction is approved and is '
     + 'NOT marked self_approved. The mark identifies entries with no second '
     + 'party, not entries an owner handled',
       JSON.stringify(v.entry));
  } catch (e) {
    bad('O3. an owner approving another\'s is not marked self-approved', e && e.stack);
  }

  // ── O4: BACKWARD COMPATIBLE -- no role argument behaves as b16 did ─────
  // api/b14-clock-approval-two-person.test.js arm S11 calls
  // approveCorrection(entry, 'E1', atISO) with THREE arguments and requires a
  // refusal. That arm must not move, and this is the same call.
  try {
    const e = pending(clock, 'E1');
    const v = clock.approveCorrection(e, 'E1', NOW);
    is(v.ok === false && v.error.code === 'SELF_APPROVAL_REFUSED',
       'O4. BACKWARD COMPATIBLE -- called with no approverRole (the b16 '
     + 'three-argument form, which arm S11 of '
     + 'api/b14-clock-approval-two-person.test.js still uses) self-approval is '
     + 'refused exactly as before',
       JSON.stringify(v));
  } catch (e) {
    bad('O4. the three-argument form still refuses self-approval', e && e.stack);
  }

  // ── O5: THE STRANDED STATE, END TO END, THROUGH THE REAL HANDLER ───────
  // The one-person agency: the owner IS the assigned caregiver, the clock-out
  // was never recorded, and only the correction supplies it. Before b17 this
  // visit was unpayable AND un-submittable forever.
  try {
    const licResolved = require.resolve('./_lib/license');
    require.cache[licResolved] = {
      id: licResolved, filename: licResolved, loaded: true,
      exports: {
        validateLicenseKey: async () => ({
          valid: true, active: true, license_hash: HASH, trial_ends_at: null,
          stripe_subscription_id: null, app_id: 'sairnsenior' })
      }
    };
    const pendingEntry = pending(clock, 'OWN1');
    const visitData = {
      scheduled_date: DAY, status: 'completed',
      clock_in_at: REC_IN, clock_out_at: null,
      clock_in_lat: 41.1, clock_in_lng: -81.5,
      clock_out_lat: 41.1, clock_out_lng: -81.5,
      service_type: 'Personal care',
      clock_corrections: [pendingEntry]
    };
    let stored = null;
    const res200 = (rows) => ({ ok: true, status: 200, headers: { get: () => '' },
      text: async () => JSON.stringify(rows), json: async () => rows });
    global.fetch = async function (url, init) {
      const u = String(url);
      const method = (init && init.method) || 'GET';
      if (/_employee_auth\?/.test(u)) {
        return res200([{ license_hash: HASH, employee_id: 'OWN1',
                         role: 'owner', active: true }]);
      }
      if (/sen_visits\?/.test(u) && method === 'GET') {
        return res200([{ visit_id: 'V1', assigned_employee_id: 'OWN1',
                         data: stored || visitData }]);
      }
      if (method !== 'GET') {
        let p = null;
        try { p = JSON.parse(init.body); } catch (e) { p = null; }
        if (p && p.data) stored = p.data;
        return res200([p]);
      }
      return res200([]);
    };
    ['./_lib/sen-evv-clock', './_lib/sen-payroll', './_lib/sen-evv-readiness',
     './sd-data.js'].forEach((m) => {
      try { delete require.cache[require.resolve(m)]; } catch (e) { /* absent */ }
    });
    const handler = require('./sd-data.js');
    const { signSessionToken } = require('./_lib/auth');
    const token = signSessionToken({ app: 'sairnsenior', employee_id: 'OWN1',
      role: 'owner', license_hash: HASH });
    const out = { statusCode: null, body: null };
    out.status = (c) => { out.statusCode = c; return out; };
    out.json = (b) => { out.body = b; return out; };
    await handler({ method: 'POST',
      headers: { authorization: 'Bearer ' + KEY, 'x-sd-auth': token },
      body: { action: 'approve_clock_correction', resource: 'sen_visits',
              payload: { id: 'V1', correction_index: 0 } } }, out);

    // Now the two consumers, on the row the handler actually stored.
    const payroll = require('./_lib/sen-payroll');
    const readiness = require('./_lib/sen-evv-readiness');
    const row = Object.assign({ id: 'V1', assigned_employee_id: 'OWN1' },
      stored || visitData);
    const pay = payroll.computePayroll({
      visits: [row], period_start: DAY, period_end: DAY,
      week_start_day: 'sunday',
      resolveRate: () => ({ status: 'applied', rate_per_hour: 20 })
    });
    const b = pay.caregivers && pay.caregivers[0];
    const rd = readiness.checkVisit(row, { id: 'C1' }, { id: 'OWN1' }, null);
    const spans = ((rd && rd.missing) || []).filter((m) => m.element === 'time_span');
    is(out.statusCode === 200 && !!b && b.minutes === 240
       && b.gross_cents === 8000 && spans.length === 0,
       'O5. THE STRANDED STATE IS GONE, end to end through the real handler: '
     + 'the owner self-approves (200), payroll pays the visit 240 minutes and '
     + '8000 cents, and the EVV readiness check reports NO time-span gap. '
     + 'Before b17 the same visit was unpayable AND un-submittable forever',
       'status=' + out.statusCode + ' minutes=' + (b && b.minutes)
     + ' cents=' + (b && b.gross_cents)
     + ' time_span=' + JSON.stringify(spans.map((m) => m.reason))
     + ' body=' + JSON.stringify(out.body && out.body.error));
  } catch (e) {
    bad('O5. the stranded state is gone end to end', e && e.stack);
  }

  // ── O6: THE CLIENT'S BUTTON, lifted from the real page ────────────────
  // The server half is useless if the page still disables the control. This
  // was the last thing standing between a one-person agency and a payable
  // visit, and it is a source check because the render is a template string.
  if (HTML === null) {
    cannot('O6. the client enables Approve for an owner on their own entry',
           'sairnsenior.html could not be read');
  } else {
    const hasOwnerFn = /function senIsOwner\(\)\{return prole==='owner';\}/.test(HTML);
    const gateUsesOwner = /mine && !senIsOwner\(\)/.test(HTML);
    const oldGate = /\+'<td>'\+\(mine\s*\n?\s*\?\s*'<button class="btn sm" disabled/.test(HTML);
    const labelsOwn = /Approve your own/.test(HTML);
    is(hasOwnerFn && gateUsesOwner && !oldGate && labelsOwn,
       'O6. the page defines senIsOwner(), the queue\'s disabled state is '
     + '`mine && !senIsOwner()`, the unconditional `mine` gate is GONE, and a '
     + 'self-approval is labelled "Approve your own" so it is never an accident',
       'senIsOwner=' + hasOwnerFn + ' gateUsesOwner=' + gateUsesOwner
     + ' oldGateStillThere=' + oldGate + ' labelled=' + labelsOwn);
  }

  // ── O7: ABLATION -- remove the owner condition and O1 must flip ───────
  if (o1 && o1.ok) {
    const r = ablate(A_OWNERSELF, "const ownerSelf = false;", () => {
      const c2 = freshClock();
      const e = pending(c2, 'E1');
      return c2.approveCorrection(e, 'E1', NOW, 'owner');
    });
    if (!r.ok) {
      cannot('O7. ABLATION -- removing the owner condition flips O1', r.why);
    } else {
      is(r.result.ok === false
         && r.result.error.code === 'SELF_APPROVAL_REFUSED',
         'O7. ABLATION -- with the ownerSelf condition neutered, the SAME call '
       + 'O1 makes is refused again, so O1 is testing that condition and not '
       + 'some other change to the module',
         'ablated verdict=' + JSON.stringify(r.result));
    }
  } else {
    cannot('O7. ABLATION -- removing the owner condition flips O1',
           'O1 did not succeed, so there is nothing to ablate');
  }

  // ── O8: THE b16 DOCUMENT THAT SAID THIS WAS UNBUILT IS CORRECTED ──────
  // A standing document left saying "RECORDED, NOT BUILT" is a lie the moment
  // this lands, and that is the staleness class CLAUDE.md names.
  {
    const p = path.join(ROOT, 'docs', '2026-10-15-hank-b16-h8-self-approval.md');
    let doc = null;
    try { doc = fs.readFileSync(p, 'utf8'); } catch (e) { doc = null; }
    if (doc === null) {
      cannot('O8. the b16 H8 document is corrected, not left saying UNBUILT',
             'docs/2026-10-15-hank-b16-h8-self-approval.md could not be read');
    } else {
      is(/RESOLVED/.test(doc) && /b17/.test(doc)
         && !/^# H8 — the one-person agency has no route/m.test(doc),
         'O8. docs/2026-10-15-hank-b16-h8-self-approval.md now records H8 as '
       + 'RESOLVED and names b17. Leaving a standing document saying "RECORDED, '
       + 'NOT BUILT" is the staleness class that costs the next session real '
       + 'time',
         'mentions RESOLVED=' + /RESOLVED/.test(doc)
       + ' mentions b17=' + /b17/.test(doc));
    }
  }

  console.log('');
  console.log('  passed ' + pass + '  failed ' + fail + '  unproven ' + unproven);
  if (fail) console.log('  FAILING ARMS: ' + failed.join(' '));
  if (unproven) console.log('  UNPROVEN ARMS: ' + notProved.join(' '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main().catch((e) => { console.log('  HARD ERROR ' + (e && e.stack)); process.exit(1); });
