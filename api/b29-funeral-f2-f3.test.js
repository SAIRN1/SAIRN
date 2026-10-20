// api/b29-funeral-f2-f3.test.js
//
// Run:  node api/b29-funeral-f2-f3.test.js
//
// ── THE PROMOTION api/b22-funeral-f1-f2-f3-wiring.test.js ASKED FOR ─────────
// b22's F2 and F3 arms drive `legRoles.decide()` DIRECTLY, at module level, and
// its own section D says why that was not enough: "F2 AND F3 ARE CONSULTED BY
// NOTHING." Its arm D1 instructed "delete this arm and promote the F2/F3 arms
// to handler level", and hank's b24 re-aimed D1 to assert the wiring instead.
// THIS FILE IS THE PROMOTION: the same policy questions, asked of the real
// api/sd-data.js dispatcher.
//
// WHY THAT IS A DIFFERENT QUESTION AND NOT A SECOND READING. A module-level arm
// proves the POLICY. It cannot see whether the handler passes the arguments the
// policy needs -- and for `grants` the answer was NO for four batches: the call
// site passed a literal `null`, so F2's widening branch was unreachable in
// production while every module arm for it stayed green. That is the exact
// gap b27's handoff §6.5 recorded and b29 closed.
//
// ── WHAT b29 CHANGED, SO THESE ARMS ARE READ AGAINST THE RIGHT BASELINE ────
//   * `sql/sairnlegacy_settings_livery_grants.sql` -- the per-employee grants
//     column. WRITTEN FOR MICHAEL, NOT RUN. No SQL is executed here.
//   * `api/sd-data.js` now reads it, takes THIS employee's own row of the map,
//     and passes it as `grants`. A missing column falls back to NO grants,
//     which DENIES -- arm G5 is that case, and it is the state production is
//     in today.
//
// No database is touched. The real dispatcher runs against a recorded
// PostgREST stand-in.
//
// Exit: 0 all arms passed · 1 an arm FAILED

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['b29', 'funeral', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const { signSessionToken } = require('./_lib/auth');
const legRoles = require('./_lib/leg-roles');

const HASH = 'b29-leg-hash';
const KEY = 'KEY-FOR-' + HASH;
const DRIVER = 'emp-livery-1';

let pass = 0, fail = 0;
const failed = [];
function ok(l) { pass++; console.log('  ok    ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l);
  if (why) console.log('        ' + String(why).slice(0, 700));
}
function is(cond, label, detail) { if (cond) ok(label); else bad(label, detail); }
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function eCode(res) { return (res.body && res.body.error && res.body.error.code) || ''; }
function eMsg(res) { return (res.body && res.body.error && res.body.error.message) || ''; }

// `opts.settings` is the sairnlegacy_settings row this home has saved, or null
// for a home that has never saved one. `opts.noColumn` makes the settings read
// answer 400 undefined_column for `livery_grants`, which is the state of
// production until Michael runs the migration.
function pgMock(calls, opts) {
  opts = opts || {};
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    calls.push({ url: u, method: method });
    if (/_employee_auth/.test(u)) {
      const m = u.match(/employee_id=eq\.([^&]+)/);
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: m ? decodeURIComponent(m[1]) : DRIVER,
          role: 'livery', active: true }] };
    }
    if (/sairnlegacy_settings/.test(u)) {
      if (opts.noColumn && /livery_grants/.test(u)) {
        return { ok: false, status: 400,
                 text: async () => JSON.stringify({ code: '42703',
                   message: 'column sairnlegacy_settings.livery_grants does not exist' }),
                 json: async () => ({ code: '42703' }) };
      }
      const row = opts.settings === undefined ? null : opts.settings;
      return { ok: true, status: 200, json: async () => (row ? [row] : []) };
    }
    if (method === 'POST' || method === 'PATCH') {
      return { ok: true, status: 200, json: async () => [{ id: 'x' }] };
    }
    return { ok: true, status: 200, json: async () => [{ data: {} }] };
  };
}

function loadHandler(calls, opts) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnlegacy' })
    }
  };
  global.fetch = pgMock(calls, opts);
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function read(resource, role, opts, employeeId) {
  const calls = [];
  const h = loadHandler(calls, opts);
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer ' + KEY,
      'x-sd-auth': signSessionToken({
        app: 'sairnlegacy', employee_id: employeeId || DRIVER, role: role,
        license_hash: HASH })
    },
    body: { action: 'read', resource: resource, payload: {} }
  }, res);
  return { res: res, calls: calls };
}

const DENIED = (res) => res.statusCode === 403 && eCode(res) === 'FORBIDDEN';
const ALLOWED = (res) => res.statusCode === 200;

(async function main() {
  // ═══════════════════════════════════════════════════════════════════════
  section('V. F2 -- leg_liveryvendors IS NOT GRANTABLE, AT THE ENDPOINT');
  // ═══════════════════════════════════════════════════════════════════════

  // b22's B2 proves this at the module. THE PROMOTION: the same claim through
  // the dispatcher, under every setting AND with an explicit grant, because
  // this table carries the pricing an invoice is built from and "no
  // arrangement needs it" has to hold where requests actually arrive.
  for (const setting of [undefined, 'through_the_home', 'direct_to_family']) {
    const { res } = await read('leg_liveryvendors', 'livery', {
      settings: setting === undefined ? null : {
        livery_billing: setting, apprentice: {},
        livery_grants: { [DRIVER]: { leg_liveryvendors: true } }
      }
    });
    is(DENIED(res),
       'V1[' + String(setting) + ']. a livery driver WITH an explicit '
       + 'leg_liveryvendors grant is still refused 403 -- the pricing table is '
       + 'not grantable under any arrangement',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // ═══════════════════════════════════════════════════════════════════════
  section('G. F2 -- THE WIDENING, WHICH NOTHING COULD REACH BEFORE b29');
  // ═══════════════════════════════════════════════════════════════════════

  // G1. THE REPRODUCTION, AND IT IS THE WHOLE POINT OF THE ITEM. Under
  // direct_to_family, with this driver granted their own bookings, the read is
  // ALLOWED. Before b29 the call site passed `grants: null`, so this answered
  // 403 no matter what any home configured -- the policy existed, was tested,
  // and could not be reached.
  {
    const { res } = await read('leg_liverybookings', 'livery', {
      settings: { livery_billing: 'direct_to_family', apprentice: {},
                  livery_grants: { [DRIVER]: { leg_liverybookings: true } } }
    });
    is(ALLOWED(res),
       'G1. direct_to_family + a per-employee grant for THIS driver -> 200. '
       + 'The grants argument reaches decide() for the first time',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // G2. THE SETTING ALONE GRANTS NOTHING. b22's B4 at module level; here at the
  // endpoint. This is the arm that stops "turn on direct_to_family" being read
  // as "let the drivers in".
  {
    const { res } = await read('leg_liverybookings', 'livery', {
      settings: { livery_billing: 'direct_to_family', apprentice: {},
                  livery_grants: {} }
    });
    is(DENIED(res),
       'G2. direct_to_family with an EMPTY grants map -> 403. Personnel still '
       + 'have to perform the grant',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // G3. THE GRANT ALONE GRANTS NOTHING EITHER. Under the default the booking is
  // the HOME's commercial record, and no per-employee grant reaches it.
  {
    const { res } = await read('leg_liverybookings', 'livery', {
      settings: { livery_billing: 'through_the_home', apprentice: {},
                  livery_grants: { [DRIVER]: { leg_liverybookings: true } } }
    });
    is(DENIED(res),
       'G3. through_the_home WITH a grant -> 403. The pairing is the policy; '
       + 'neither half is sufficient',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // G4. SOMEBODY ELSE'S GRANT IS NOT THIS DRIVER'S. The map is keyed by
  // employee id and the handler takes THIS session's row. Handing `decide()`
  // the whole home-wide object would make every lookup `undefined` -- still a
  // refusal, so the bug would look like correct behaviour. This arm is the one
  // that can tell those apart.
  {
    const { res } = await read('leg_liverybookings', 'livery', {
      settings: { livery_billing: 'direct_to_family', apprentice: {},
                  livery_grants: { 'emp-somebody-else': { leg_liverybookings: true } } }
    });
    is(DENIED(res),
       'G4. a grant belonging to ANOTHER employee -> 403 for this one',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // G5. THE STATE PRODUCTION IS IN TODAY. The column does not exist, the
  // settings read answers 400 undefined_column, the handler re-reads without
  // it -- and the answer is a REFUSAL, not a 500 and not a silent widening.
  // F2's per-home half keeps working, which is why the fallback re-reads
  // instead of giving up on the row.
  {
    const { res, calls } = await read('leg_liverybookings', 'livery', {
      noColumn: true,
      settings: { livery_billing: 'direct_to_family', apprentice: {} }
    });
    const reads = calls.filter((c) => /sairnlegacy_settings/.test(c.url));
    is(DENIED(res) && reads.length === 2
       && /livery_grants/.test(reads[0].url)
       && !/livery_grants/.test(reads[1].url),
       'G5. the column ABSENT (production today) -> the read is re-issued '
       + 'without it and the answer is 403, never a 500 and never a widening',
       res.statusCode + ' ' + eCode(res) + ' settings reads='
         + reads.length + ' ' + JSON.stringify(reads.map((c) =>
             /livery_grants/.test(c.url) ? 'with' : 'without')));
  }

  // G6. A MALFORMED MAP FAILS NARROW. `true`, an array and a string are the
  // three realistic ways a jsonb column gets the wrong shape, and the DB
  // constraint in the migration only stops the first. All three must deny.
  for (const bad of [true, ['x'], 'direct_to_family', 42]) {
    const { res } = await read('leg_liverybookings', 'livery', {
      settings: { livery_billing: 'direct_to_family', apprentice: {},
                  livery_grants: bad }
    });
    is(DENIED(res),
       'G6[' + JSON.stringify(bad) + ']. a malformed livery_grants value -> '
       + '403, never a widening',
       res.statusCode + ' ' + eCode(res));
  }

  // G7. AND `=== true` IS THE GRANT, NOT TRUTHINESS. A `1` or a `"yes"` in the
  // map is a configuration mistake and must not open a resource -- the same
  // convention tests/role_maps_have_no_prototype.js holds every role map to.
  for (const v of [1, 'yes', {}, 'true']) {
    const { res } = await read('leg_liverybookings', 'livery', {
      settings: { livery_billing: 'direct_to_family', apprentice: {},
                  livery_grants: { [DRIVER]: { leg_liverybookings: v } } }
    });
    is(DENIED(res),
       'G7[' + JSON.stringify(v) + ']. a truthy-but-not-true grant value -> 403',
       res.statusCode + ' ' + eCode(res));
  }

  // ═══════════════════════════════════════════════════════════════════════
  section('A. F3 -- apprentice clearance, owner-configurable, AT THE ENDPOINT');
  // ═══════════════════════════════════════════════════════════════════════

  // A1. THE DEFAULT GRANTS NOTHING NEW. A home that has never answered F3
  // keeps exactly the shipped policy -- so an apprentice reading a resource
  // the matrix allows is allowed, and this arm's value is that it proves the
  // settings read being EMPTY is not itself a refusal.
  const APPRENTICE_OK = Object.keys(legRoles.LEG_ROLE_MATRIX || {})
    .find((r) => legRoles.decide(r, 'apprentice', 'read') === legRoles.ALLOW);
  {
    is(typeof APPRENTICE_OK === 'string',
       'A0. the matrix allows an apprentice at least one read, so A1 has a '
       + 'subject -- without this the arms below could pass vacuously',
       'found ' + String(APPRENTICE_OK));
  }
  if (APPRENTICE_OK) {
    const { res } = await read(APPRENTICE_OK, 'apprentice', { settings: null },
      'emp-app-1');
    is(ALLOWED(res),
       'A1. no settings row at all -> an apprentice keeps the shipped policy '
       + 'on ' + APPRENTICE_OK + ', 200',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // A2. AND A HOME CAN TAKE IT AWAY. `forbidden` is F3's narrow direction and
  // b22's F2 ablation proves the DENY wins inside the module; this proves the
  // home's answer reaches it through the handler.
  if (APPRENTICE_OK) {
    const { res } = await read(APPRENTICE_OK, 'apprentice', {
      settings: { livery_billing: 'through_the_home',
                  apprentice: { forbidden: [APPRENTICE_OK] },
                  livery_grants: {} }
    }, 'emp-app-1');
    is(DENIED(res),
       'A2. a home that lists ' + APPRENTICE_OK + ' as forbidden -> 403. F3\'s '
       + 'per-home answer reaches the policy through the handler',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // A3. AN UNRECOGNISED RESOURCE NAME IN `forbidden` IS DROPPED, NOT OBEYED
  // BLINDLY, and it must not take the real one down with it. A typo in a
  // settings screen must neither open nor close something else.
  if (APPRENTICE_OK) {
    const { res } = await read(APPRENTICE_OK, 'apprentice', {
      settings: { livery_billing: 'through_the_home',
                  apprentice: { forbidden: ['leg_not_a_resource'] },
                  livery_grants: {} }
    }, 'emp-app-1');
    is(ALLOWED(res),
       'A3. a typo in `forbidden` does not collaterally refuse '
       + APPRENTICE_OK + ' -- 200',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // ═══════════════════════════════════════════════════════════════════════
  section('S. THE STRUCTURAL ARM -- the handler passes BOTH arguments');
  // ═══════════════════════════════════════════════════════════════════════

  // S1. The behaviour arms above would all still pass if `grants` were wired
  // and `home` reverted to null, because every G arm that needs `home` also
  // needs `grants`. Asserting the call site is what separates them -- and the
  // literal `null` this replaced is exactly what a reverted wiring looks like.
  {
    const fs = require('fs');
    const path = require('path');
    const { stripJs } = require('../tests/lib/strip_comments.js');
    const src = stripJs(
      fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8'));
    const m = src.match(/legRoles\.decide\(resource, legSess\.role, action, ([^,]+), ([^)]+)\)/);
    is(m && m[1].trim() === 'legGrants' && m[2].trim() === 'legHome',
       'S1. the call site passes legGrants and legHome -- neither is a literal '
       + 'null, which is what the reverted state looked like',
       m ? ('grants=' + m[1].trim() + ' home=' + m[2].trim())
         : 'the five-argument call site was not found -- re-aim this arm');
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed'
    + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
