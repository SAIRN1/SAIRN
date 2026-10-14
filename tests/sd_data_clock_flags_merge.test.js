// tests/sd_data_clock_flags_merge.test.js
//
// FAILING-FIRST. RED ON PURPOSE AND MUST STAY RED UNTIL THE api/ OWNER FIXES
// THE MERGE. Registered in docs/known-red-suites.json; wired into NO gate.
//
// ── THE DEFECT, FOUND IN cody b8's TIER A REVIEW AND NOT IN ANY RECORD ─────
// api/sd-data.js, the sen_visits write branch:
//
//     if (clockCheck.flags && clockCheck.flags.length) {
//       visitData.clock_flags = clockCheck.flags;      // <-- ASSIGNMENT
//     }
//
// b8 cited that at api/sd-data.js:6985-6987. **IT HAS SINCE MOVED** -- arm B1
// below re-derives the line number from the file every run rather than carrying
// the citation, because api/sd-data.js is ~14k lines and grows every day.
//
// `checkClockEvent` only ever reports on the clock fields present in THIS
// payload: api/_lib/sen-evv-clock.js returns early for any field the payload
// omits. A visit's two halves arrive as TWO separate writes. So the second
// write's flags REPLACE the first write's, and the clock-in's LATE_REPLAY or
// FUTURE flag is gone with nothing saying it ever existed.
//
// ── IT ONLY SHOWS WHEN BOTH HALVES ARE FLAGGED, WHICH IS THE CASE AN AUDITOR
//    IS LOOKING FOR ────────────────────────────────────────────────────────
// If the clock-out is CLEAN, `flags` is empty, the `if` is false, and the
// clock-in's flag survives by luck. Arm A4 pins that asymmetry, PASSES today,
// and is the reason this defect has never been noticed: the common case hides
// it and the audit case does not.
//
// ── WHY IT IS A DEFECT AND NOT A PREFERENCE ────────────────────────────────
// The comment two lines above the assignment says so itself: "FLAGS ARE STORED,
// NOT ONLY RETURNED. A LATE_REPLAY that appears in one response and nowhere
// else is a finding nobody can audit later." The STAMPS do not have this
// problem because they are KEYED PER FIELD -- clock_in_skew_ms and
// clock_out_skew_ms coexist happily. Arm A3 proves that, passes today, and is
// what makes this finding precise rather than a general complaint about merges.
//
// And the same author got it right one screen away: the sibling
// self-correction marker is deliberately STICKY -- "a later ordinary correction
// must NOT clear a flag whose entry is still sitting in the trail." This is the
// same requirement with the opposite implementation.
//
// ── TWO LEGITIMATE FIXES AND ARM B1 ACCEPTS EITHER ─────────────────────────
//   (a) MERGE BY FIELD -- keep the stored entries whose `field` is not in the
//       incoming set, then concatenate;
//   (b) KEY PER FIELD -- store clock_in_flags / clock_out_flags the way the
//       stamps already are.
// Asserting one would dictate the implementation. api/ is not mine.
//
// ── IT DRIVES THE REAL HANDLER, AND THE STORE IS STATEFUL ──────────────────
// Same technique as api/sd-data-sen-evv-clock.test.js, with one necessary
// difference: that harness returns a FIXED row, and this defect only exists
// ACROSS two writes. So the mock store here is mutable -- the POST of write 1
// becomes the GET of write 2, which is what the real table does. A fixed-row
// harness cannot see this bug at all, and that is probably why nothing did.
//
// Run:  node tests/sd_data_clock_flags_merge.test.js
// Exit: 0 all arms proved and passing · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');

const SD_DATA = path.join(ROOT, 'api/sd-data.js');
const CAREGIVER = 'cg-1';
const VISIT = 'V-1';

// PAST_FLAG_MS is 7 days (api/_lib/sen-evv-clock.js), so anything older than
// that is flagged LATE_REPLAY -- which is the OFFLINE PATH WORKING, not an
// error. Both halves below are 10 days old so both are flagged, and the
// clock-out is 8 hours AFTER the clock-in so the ordering refusal does not
// fire. Read the constant rather than trusting this sentence:
const CLOCK = require(path.join(ROOT, 'api/_lib/sen-evv-clock.js'));
const PAST_FLAG_DAYS = CLOCK.PAST_FLAG_MS / 86400000;
const OLD_IN_MS = Date.now() - (PAST_FLAG_DAYS + 3) * 86400000;
const OLD_IN = new Date(OLD_IN_MS).toISOString();
const OLD_OUT = new Date(OLD_IN_MS + 8 * 3600000).toISOString();
// A clock-out that is RECENT -- inside the flag window, so it is not flagged --
// and still after the clock-in. This is arm A4's clean second write.
const FRESH_OUT = new Date(Date.now() - 3600000).toISOString();

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 320));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 320));
}

// ── THE STATEFUL HARNESS ───────────────────────────────────────────────────
function loadHandler() {
  const writes = [];
  const store = { data: {} };

  const licPath = require.resolve(path.join(ROOT, 'api/_lib/license.js'));
  delete require.cache[licPath];
  require.cache[licPath] = {
    id: licPath, filename: licPath, loaded: true,
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: 'test-hash',
                 app_id: 'sairnsenior', trial_ends_at: null,
                 stripe_subscription_id: null };
      }
    }
  };

  const authPath = require.resolve(path.join(ROOT, 'api/_lib/auth.js'));
  const realAuth = require(authPath);
  delete require.cache[authPath];
  require.cache[authPath] = {
    id: authPath, filename: authPath, loaded: true,
    exports: Object.assign({}, realAuth, {
      tokenFromRequest: function () { return 'tok'; },
      verifySessionToken: function () {
        // A CAREGIVER, deliberately: SEN_VISIT_SCHEDULER_ROLES does not include
        // one, so the request takes the EVV branch rather than the scheduling
        // branch. A scheduler-tier caller cannot reach the clock fields at all,
        // so driving this as an owner would exercise the wrong half.
        return { employee_id: CAREGIVER, role: 'caregiver',
                 app: 'sairnsenior', subject: CAREGIVER };
      }
    })
  };

  global.fetch = async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (method === 'POST') {
      const body = JSON.parse(init.body);
      writes.push(body);
      // THE POST OF WRITE 1 BECOMES THE GET OF WRITE 2. This is the whole
      // reason the suite can see the defect.
      if (body && body.data) store.data = body.data;
      return { ok: true, status: 200, json: async () => [body] };
    }
    if (u.indexOf('sen_visits') !== -1) {
      return { ok: true, status: 200,
               json: async () => [{ assigned_employee_id: CAREGIVER,
                                    data: store.data }] };
    }
    // NOT a silent empty list for anything else -- an unmocked read that
    // answers [] makes an arm pass for a reason nobody chose.
    throw new Error('Unmocked fetch: ' + method + ' ' + u);
  };

  const sdPath = require.resolve(SD_DATA);
  delete require.cache[sdPath];
  return { handler: require(sdPath), writes: writes, store: store };
}

function res() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
function req(payload) {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer SEN-TEST-KEY', 'x-sd-auth': 'tok' },
    body: { action: 'write', resource: 'sen_visits', payload: payload },
  };
}
function fieldsOf(flags) {
  return (Array.isArray(flags) ? flags : []).map((f) => f && f.field);
}

(async function main() {
  console.log('sen_visits clock_flags -- ASSIGNED, NOT MERGED '
            + '-- criteria 2026-10-14.1 (FAILING-FIRST)\n');

  console.log('A. the two-write sequence, against the real handler');

  // ── WRITE 1 then WRITE 2, both flagged. ─────────────────────────────────
  let h = loadHandler();
  let r1 = res();
  await h.handler(req({ id: VISIT, clock_in_at: OLD_IN }), r1);

  if (r1.statusCode !== 200) {
    cannot('A1. write 1 (a late clock-in) did not reach the store, so the '
         + 'two-write sequence could not be driven at all',
           'status=' + r1.statusCode + ' body=' + JSON.stringify(r1.body));
    cannot('A2. depends on write 1', 'see A1');
    cannot('A3. depends on write 1', 'see A1');
  } else {
    const afterOne = h.store.data;
    const f1 = fieldsOf(afterOne.clock_flags);
    if (f1.indexOf('clock_in_at') !== -1) {
      ok('A2. CONTROL -- write 1 really DID store a clock_in_at flag ('
       + JSON.stringify(afterOne.clock_flags.map((f) => f.code))
       + '). WITHOUT THIS ARM, A1 below could fail because nothing was ever '
       + 'stored, which is a different bug from a flag being lost');
    } else {
      bad('A2. CONTROL -- a clock-in ' + Math.round(PAST_FLAG_DAYS + 3)
        + ' days old must be flagged and stored',
          'clock_flags=' + JSON.stringify(afterOne.clock_flags));
    }

    let r2 = res();
    await h.handler(req({ id: VISIT, clock_out_at: OLD_OUT }), r2);

    if (r2.statusCode !== 200) {
      cannot('A1. write 2 (a late clock-out) was refused, so the replacement '
           + 'could not be observed',
             'status=' + r2.statusCode + ' body=' + JSON.stringify(r2.body));
      cannot('A3. depends on write 2', 'see A1');
    } else {
      const afterTwo = h.store.data;
      const f2 = fieldsOf(afterTwo.clock_flags);
      const keptIn = f2.indexOf('clock_in_at') !== -1;
      const hasOut = f2.indexOf('clock_out_at') !== -1;

      if (keptIn && hasOut) {
        ok('A1. THE ARM THIS FILE EXISTS FOR -- after a flagged clock-in AND a '
         + 'flagged clock-out, BOTH flags are on the row. The second write '
         + 'merges rather than replacing');
      } else if (hasOut && !keptIn) {
        bad('A1. the clock-in\'s flag was DISCARDED by the clock-out\'s write. '
          + 'An auditor reading this visit cannot tell it was replayed late on '
          + 'the way in',
            'clock_flags after write 1 = ' + JSON.stringify(f1)
          + ' ; after write 2 = ' + JSON.stringify(f2)
          + ' -- the array was REPLACED, not merged');
      } else {
        bad('A1. after two flagged writes the row must carry a flag for each '
          + 'half', 'clock_flags = ' + JSON.stringify(afterTwo.clock_flags));
      }

      // THE PRECISION ARM. The stamps are keyed per field and survive; the
      // flags are one unkeyed array and do not. This is what makes the finding
      // specific rather than "merging is hard".
      const bothStamps = afterTwo.clock_in_skew_ms !== undefined
                      && afterTwo.clock_out_skew_ms !== undefined
                      && !!afterTwo.clock_in_received_at
                      && !!afterTwo.clock_out_received_at;
      if (bothStamps) {
        ok('A3. CONTROL -- the SKEW STAMPS for BOTH halves coexist on the same '
         + 'row (clock_in_skew_ms and clock_out_skew_ms, both received_at '
         + 'present). So per-field keying already works here and A1 is a defect '
         + 'in the unkeyed ARRAY specifically, not in the handler\'s merging');
      } else {
        bad('A3. CONTROL -- the per-field stamps should both survive two writes',
            JSON.stringify({
              in_skew: afterTwo.clock_in_skew_ms,
              out_skew: afterTwo.clock_out_skew_ms,
              in_rcv: afterTwo.clock_in_received_at,
              out_rcv: afterTwo.clock_out_received_at }));
      }

      // The claimed times must still be the caregiver's own, across BOTH
      // writes. A regression pin on the thing that already works -- the whole
      // point of the EVV wiring is that a late replay is kept, not rewritten.
      if (afterTwo.clock_in_at === OLD_IN && afterTwo.clock_out_at === OLD_OUT) {
        ok('A5. REGRESSION PIN -- both claimed times survived two writes '
         + 'unchanged. A fix to A1 must not start re-stamping anything');
      } else {
        bad('A5. the claimed times must not be rewritten',
            JSON.stringify({ in: afterTwo.clock_in_at,
                             out: afterTwo.clock_out_at }));
      }
    }
  }

  // ── A4. THE ASYMMETRY THAT HIDES THE BUG. ───────────────────────────────
  console.log('\nA4. the asymmetry -- why nobody has noticed');
  h = loadHandler();
  let r3 = res();
  await h.handler(req({ id: VISIT, clock_in_at: OLD_IN }), r3);
  if (r3.statusCode !== 200) {
    cannot('A4. the clean-second-write case could not be driven',
           'write 1 status=' + r3.statusCode);
  } else {
    let r4 = res();
    await h.handler(req({ id: VISIT, clock_out_at: FRESH_OUT }), r4);
    if (r4.statusCode !== 200) {
      cannot('A4. the clean clock-out was refused',
             'status=' + r4.statusCode + ' ' + JSON.stringify(r4.body));
    } else {
      const f = fieldsOf(h.store.data.clock_flags);
      if (f.indexOf('clock_in_at') !== -1) {
        ok('A4. CONTROL -- with a CLEAN clock-out the clock-in\'s flag '
         + 'SURVIVES, because `flags` is empty and the `if` never fires. THIS '
         + 'IS WHY THE DEFECT IS INVISIBLE IN NORMAL USE and shows only when '
         + 'both halves are flagged -- the audit case');
      } else {
        bad('A4. a clean second write must not clear the first write\'s flag '
          + 'either', 'clock_flags = ' + JSON.stringify(h.store.data.clock_flags));
      }
    }
  }

  // ── B. THE SOURCE, WITH THE CITATION RE-DERIVED EVERY RUN ───────────────
  console.log('\nB. the source line, re-derived rather than cited');

  let src = null;
  try { src = fs.readFileSync(SD_DATA, 'utf8'); } catch (e) { src = null; }
  if (src === null) {
    cannot('B1. api/sd-data.js is not readable at ' + SD_DATA, 'ENOENT');
  } else {
    const lines = src.split(/\r?\n/);
    const ASSIGN = 'visitData.clock_flags = clockCheck.flags;';
    const at = [];
    lines.forEach(function (l, i) {
      if (l.indexOf(ASSIGN) !== -1 && !/^\s*(\/\/|\*)/.test(l)) at.push(i + 1);
    });

    const keyed = /clock_in_flags|clock_out_flags/.test(src);

    if (at.length === 0 && keyed) {
      ok('B1. the bare assignment is GONE and per-field flag keys '
       + '(clock_in_flags / clock_out_flags) are present -- resolution (b), '
       + 'keyed the way the stamps already are');
    } else if (at.length === 0) {
      ok('B1. the bare assignment ' + JSON.stringify(ASSIGN) + ' is no longer '
       + 'in api/sd-data.js, so the replacement cannot happen by that route. '
       + 'Arms A1-A4 are what say the behaviour is actually right');
    } else if (at.length !== 1) {
      cannot('B1. the assignment matched ' + at.length + ' time(s) (lines '
           + at.join(', ') + '), not once, so this arm cannot say which site '
           + 'it measured', 'uniqueness guard');
    } else {
      bad('B1. api/sd-data.js:' + at[0] + ' still BARE-ASSIGNS clock_flags. '
        + 'MEASURED NOW, NOT CITED: b8 recorded this at :6985-6987 and the '
        + 'file has moved since. Fix by merging on `field`, or by keying per '
        + 'field as clock_in_skew_ms/clock_out_skew_ms already are -- EITHER '
        + 'IS ACCEPTED BY THIS ARM',
          'line ' + at[0] + ': ' + lines[at[0] - 1].trim());
    }
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, '
            + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  console.log('\nEXPECTED RED until the api/ owner merges instead of assigning. '
            + 'Registered in docs/known-red-suites.json; no gate reads this. '
            + 'FIX ROUTED TO hank.');
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})();
