// api/b17-closed-period-write-path.test.js
//
// Run:  node api/b17-closed-period-write-path.test.js
//
// REQUIREMENT (MICHAEL, 2026-10-15): pay periods may be closed by owner plus
//   the office-manager / payroll person ONLY, others refused, audit-logged.
//
// ── WHY THIS EXISTS: b16's FREEZE WAS INERT ───────────────────────────────
// b16 built the paid-period freeze in api/_lib/sen-payroll.js and nothing
// could write `sen_settings.payroll_closed_periods`, so there were no closed
// periods anywhere and the freeze was code that could not fire. The b16
// handoff carried it as open item 4 and named the reason the write path was
// not built with it: "who may freeze a pay period" is a permissions decision,
// not a handler detail. Michael has now made it, so this is the write path.
//
// ── THE ONE ARM THAT MATTERS MOST IS W5, AND IT IS AN ABLATION ────────────
// `SEN_PERIOD_CLOSE_ROLES` is { owner, billing } and SAIRNsenior's
// `MANAGEMENT_ROLES` is ALSO { owner, billing }. So the outer management gate
// on the sen_settings write branch already refuses every role the new gate
// would refuse, and THE NEW GATE CANNOT FIRE TODAY. A check that cannot fire
// is indistinguishable from dead code, and a suite that only drove the roles
// as they stand would be asserting nothing about it.
//
// W5 therefore WIDENS MANAGEMENT_ROLES to include 'scheduler' in a copy of
// api/sen-auth.js, and requires the close to STILL be refused 403 by the
// narrower gate. That is the exact future the constant exists for -- its own
// note in api/sen-auth.js says so -- and it is the only way to drive it.
//
// ── AND ONE DEPARTURE, DRIVEN RATHER THAN ASSERTED IN PROSE ───────────────
// A failed audit write REFUSES the close (W10), which is the OPPOSITE of
// api/_lib/audit.js's deliberate best-effort posture for credential grants.
// The argument is in the handler and in the SQL file; the arm is here. Note
// sql/sairnsenior_audit_log_schema.sql has NOT been run, so 503
// AUDIT_UNAVAILABLE is the EXPECTED live answer today -- W10 is not a
// hypothetical.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const AUTH_SRC = path.join(__dirname, 'sen-auth.js');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['b17', 'close', String(process.pid)].join('-');
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

const PERIOD_A = { period_start: '2026-10-01', period_end: '2026-10-15',
                   paid_at: '2026-10-16T00:00:00Z' };
const PERIOD_B = { period_start: '2026-10-16', period_end: '2026-10-31',
                   paid_at: '2026-11-01T00:00:00Z' };

// ── THE DRIVER. The REAL api/sd-data.js, a REAL signed session. ───────────
// `writes` captures every non-GET upstream call, so an arm can assert not only
// the status but that NO ROW WAS WRITTEN -- a refusal with the row already in
// the table is the same failure wearing a refusal.
async function drive(opts) {
  const o = opts || {};
  const writes = [];
  const licResolved = require.resolve('./_lib/license');
  require.cache[licResolved] = {
    id: licResolved, filename: licResolved, loaded: true,
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH, trial_ends_at: null,
        stripe_subscription_id: null, app_id: 'sairnsenior' })
    }
  };
  const res200 = (rows) => ({ ok: true, status: 200, headers: { get: () => '' },
    text: async () => JSON.stringify(rows), json: async () => rows });
  global.fetch = async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (/_employee_auth\?/.test(u)) {
      return res200([{ license_hash: HASH, employee_id: 'S1',
                       role: o.role || 'owner', active: true }]);
    }
    if (/sairnsenior_audit_log/.test(u)) {
      writes.push({ url: u, method: method, kind: 'audit',
                    body: (() => { try { return JSON.parse(init.body); } catch (e) { return null; } })() });
      if (o.auditFails) {
        return { ok: false, status: 400, headers: { get: () => '' },
                 text: async () => 'violates check constraint "sairnsenior_audit_log_event_type_check"',
                 json: async () => ({}) };
      }
      return { ok: true, status: 201, headers: { get: () => '' },
               text: async () => '', json: async () => ([]) };
    }
    if (/sen_settings\?/.test(u) && method === 'GET') {
      if (o.prevReadFails) {
        return { ok: false, status: 500, headers: { get: () => '' },
                 text: async () => '{}', json: async () => ({ message: 'boom' }) };
      }
      const prev = o.prev === undefined ? [] : o.prev;
      return res200(prev.length
        ? [{ data: { periods: prev } }] : []);
    }
    if (method !== 'GET') {
      let parsed = null;
      try { parsed = JSON.parse(init.body); } catch (e) { parsed = null; }
      writes.push({ url: u, method: method, kind: 'settings', body: parsed });
      return res200([parsed]);
    }
    return res200([]);
  };

  // A FRESH MODULE GRAPH EVERY DRIVE. b16 paid for this: an ablation restores
  // the FILE in its finally and the loaded module object stays in
  // require.cache, so a later arm runs against the mutant and reports it as a
  // wiring failure. Restoring a file is not unloading it.
  ['./_lib/sen-evv-clock', './_lib/sen-payroll', './_lib/audit',
   './sen-auth.js', './sd-data.js'].forEach((m) => {
    try { delete require.cache[require.resolve(m)]; } catch (e) { /* absent */ }
  });
  const handler = require('./sd-data.js');
  const { signSessionToken } = require('./_lib/auth');
  const out = { statusCode: null, body: null };
  out.status = (c) => { out.statusCode = c; return out; };
  out.json = (b) => { out.body = b; return out; };
  await handler({ method: 'POST',
    headers: { authorization: 'Bearer ' + KEY,
               'x-sd-auth': signSessionToken({ app: 'sairnsenior',
                 employee_id: 'S1', role: o.role || 'owner', license_hash: HASH }) },
    body: { action: 'write', resource: 'sen_settings',
            payload: { setting_key: 'payroll_closed_periods',
                       value: { periods: o.periods === undefined ? [PERIOD_A] : o.periods } } } }, out);
  const settingsWrites = writes.filter((w) => w.kind === 'settings');
  return { status: out.statusCode, body: out.body, writes: writes,
           settingsWrites: settingsWrites,
           auditWrites: writes.filter((w) => w.kind === 'audit') };
}

function code(r) { return r.body && r.body.error && r.body.error.code; }

// ── ABLATION on api/sen-auth.js, for W5 ──────────────────────────────────
function ablateAuth(anchor, replacement, fn) {
  const src = fs.readFileSync(AUTH_SRC, 'utf8');
  const n = src.split(anchor).length - 1;
  if (n !== 1) return { ok: false, why: 'anchor occurs ' + n + ' times, not 1' };
  let r;
  try {
    fs.writeFileSync(AUTH_SRC, src.split(anchor).join(replacement));
    r = { ok: true, result: fn() };
  } finally {
    fs.writeFileSync(AUTH_SRC, src);
    if (fs.readFileSync(AUTH_SRC, 'utf8') !== src) {
      console.log('  HARD ERROR the ablation did not restore api/sen-auth.js -- DO NOT COMMIT');
      process.exit(1);
    }
  }
  return r;
}

const A_MGMT = "const MANAGEMENT_ROLES = roleSet({ owner: true, billing: true });";

async function main() {
  console.log('api/b17-closed-period-write-path.test.js');
  console.log('  closing a pay period: who may, what is refused, and what is logged');

  // ── W1: THE OWNER CAN CLOSE ─────────────────────────────────────────────
  let w1 = null;
  try {
    w1 = await drive({ role: 'owner' });
    const wrote = w1.settingsWrites[0];
    is(w1.status === 200 && !!wrote
       && wrote.body.setting_key === 'payroll_closed_periods'
       && Array.isArray(wrote.body.data.periods)
       && wrote.body.data.periods.length === 1
       && wrote.body.updated_by === 'S1',
       'W1. an OWNER closes a pay period: 200, the row is written with the '
     + 'period, and updated_by comes from the verified session',
       'status=' + w1.status + ' code=' + code(w1)
     + ' wrote=' + JSON.stringify(wrote && wrote.body));
  } catch (e) {
    bad('W1. an OWNER closes a pay period', e && e.stack);
  }

  // ── W2: AND SO CAN THE BILLING / PAYROLL ROLE ──────────────────────────
  try {
    const r = await drive({ role: 'billing' });
    is(r.status === 200 && r.settingsWrites.length === 1,
       'W2. the BILLING (office-manager/payroll) role closes a pay period: 200. '
     + 'Michael named owner PLUS the payroll person, so a suite that only '
     + 'drove owner would not have tested the decision',
       'status=' + r.status + ' code=' + code(r));
  } catch (e) {
    bad('W2. the BILLING role closes a pay period', e && e.stack);
  }

  // ── W3/W4: THE ROLES THAT MAY NOT, and NOTHING IS WRITTEN ──────────────
  for (const role of ['scheduler', 'coordinator', 'caregiver']) {
    try {
      const r = await drive({ role: role });
      is(r.status === 403 && code(r) === 'FORBIDDEN'
         && r.settingsWrites.length === 0,
         'W3. a ' + role + ' is REFUSED 403 and writes NO row',
         'status=' + r.status + ' code=' + code(r)
       + ' writes=' + r.settingsWrites.length);
    } catch (e) {
      bad('W3. a ' + role + ' is REFUSED', e && e.stack);
    }
  }

  // ── W5: THE ARM THAT MAKES THE NEW GATE MEAN ANYTHING ──────────────────
  // SEN_PERIOD_CLOSE_ROLES == MANAGEMENT_ROLES today, so the outer gate
  // refuses everything the inner one would and the inner one cannot fire.
  // Widen MANAGEMENT_ROLES to include 'scheduler' -- the exact future the
  // constant exists for -- and the close must STILL be refused.
  if (w1 && w1.status === 200) {
    const r = ablateAuth(A_MGMT,
      "const MANAGEMENT_ROLES = roleSet({ owner: true, billing: true, scheduler: true });",
      () => drive({ role: 'scheduler' }));
    if (!r.ok) {
      cannot('W5. ABLATION -- a WIDENED MANAGEMENT_ROLES does not widen who may close', r.why);
    } else {
      const got = await r.result;
      is(got.status === 403 && code(got) === 'FORBIDDEN'
         && got.settingsWrites.length === 0
         && /limited to/.test(String(got.body && got.body.error && got.body.error.message)),
         'W5. ABLATION -- with MANAGEMENT_ROLES widened to include scheduler, a '
       + 'scheduler passes the OUTER management gate and is STILL refused 403 '
       + 'by SEN_PERIOD_CLOSE_ROLES. Without this arm the new gate cannot fire '
       + 'and is indistinguishable from dead code',
         'ablated status=' + got.status + ' code=' + code(got)
       + ' writes=' + got.settingsWrites.length
       + ' message=' + JSON.stringify(got.body && got.body.error && got.body.error.message));
    }
  } else {
    cannot('W5. ABLATION -- a WIDENED MANAGEMENT_ROLES does not widen who may close',
           'W1 did not succeed, so there is no working close to compare against');
  }

  // ── W6: APPEND-ONLY. Un-closing restates paid wages. ───────────────────
  try {
    const r = await drive({ role: 'owner', prev: [PERIOD_A, PERIOD_B],
                            periods: [PERIOD_B] });
    is(r.status === 409 && code(r) === 'CLOSED_PERIOD_IMMUTABLE'
       && r.settingsWrites.length === 0
       && /2026-10-01/.test(String(r.body.error.message)),
       'W6. a write that DROPS an already-closed period is 409 '
     + 'CLOSED_PERIOD_IMMUTABLE, names the affected period, and writes '
     + 'nothing. Un-closing a period restates wages already paid -- the same '
     + 'defect the freeze exists to prevent, by a different door and with no '
     + 'trail at all',
       'status=' + r.status + ' code=' + code(r)
     + ' msg=' + String(r.body && r.body.error && r.body.error.message).slice(0, 180));
  } catch (e) {
    bad('W6. dropping a closed period is refused', e && e.stack);
  }

  // ── W7: CONTROL -- append-only means APPEND IS ALLOWED ─────────────────
  // Without this arm "refuse every write when anything is already closed"
  // passes W6, and an agency could never close a second period.
  try {
    const r = await drive({ role: 'owner', prev: [PERIOD_A],
                            periods: [PERIOD_A, PERIOD_B] });
    is(r.status === 200 && r.settingsWrites.length === 1
       && r.settingsWrites[0].body.data.periods.length === 2,
       'W7. CONTROL -- ADDING a period while keeping the existing one is 200 '
     + 'with both. Append-only is append-ONLY, not freeze-forever',
       'status=' + r.status + ' code=' + code(r)
     + ' periods=' + JSON.stringify(r.settingsWrites[0] && r.settingsWrites[0].body.data.periods));
  } catch (e) {
    bad('W7. CONTROL -- appending a period is allowed', e && e.stack);
  }

  // ── W8: A paid_at NOBODY CAN READ IS REFUSED AT THE WRITE ──────────────
  // The engine already refuses a PAY RUN on this (UNDATED_CLOSED_PERIOD), so
  // a bad record stored today breaks every run from then on. The write is the
  // only moment the person who made the mistake is still present.
  try {
    const r = await drive({ role: 'owner',
      periods: [{ period_start: '2026-10-01', period_end: '2026-10-15',
                  paid_at: 'whenever' }] });
    is(r.status === 400 && code(r) === 'INVALID_SETTING'
       && /paid_at/.test(String(r.body.error.message))
       && r.settingsWrites.length === 0,
       'W8. a period whose paid_at cannot be read is 400 INVALID_SETTING at '
     + 'the WRITE, naming paid_at, and nothing is stored. Stored, it would '
     + 'refuse every pay run from then on with the author long gone',
       'status=' + r.status + ' code=' + code(r)
     + ' msg=' + String(r.body && r.body.error && r.body.error.message).slice(0, 160));
  } catch (e) {
    bad('W8. an unreadable paid_at is refused at the write', e && e.stack);
  }

  // ── W9: A MISSING ARRAY IS NOT "NOTHING IS CLOSED" ─────────────────────
  try {
    const r = await drive({ role: 'owner', periods: null });
    is(r.status === 400 && code(r) === 'INVALID_SETTING'
       && r.settingsWrites.length === 0,
       'W9. value.periods missing is 400, not an empty list -- an absent array '
     + 'read as "nothing is closed" would unfreeze every paid period',
       'status=' + r.status + ' code=' + code(r));
  } catch (e) {
    bad('W9. a missing periods array is refused', e && e.stack);
  }

  // ── W10: THE AUDIT ROW MUST LAND, AND THIS IS THE DEPARTURE ────────────
  try {
    const r = await drive({ role: 'owner', auditFails: true });
    is(r.status === 503 && code(r) === 'AUDIT_UNAVAILABLE'
       && r.settingsWrites.length === 0
       && r.auditWrites.length === 1,
       'W10. a FAILED audit write REFUSES the close (503 AUDIT_UNAVAILABLE) and '
     + 'nothing is stored. This is the OPPOSITE of auditPinSetup\'s best-effort '
     + 'posture and the trade is the other way: a grant blocked by a logging '
     + 'outage locks somebody out of their own app, while a pay-period close is '
     + 'retryable and is audited precisely because it freezes money',
       'status=' + r.status + ' code=' + code(r)
     + ' settingsWrites=' + r.settingsWrites.length
     + ' auditWrites=' + r.auditWrites.length);
  } catch (e) {
    bad('W10. a failed audit write refuses the close', e && e.stack);
  }

  // ── W11: AND THE AUDIT ROW CARRIES WHAT WAS ADDED, not just "changed" ──
  if (w1 && w1.status === 200) {
    const a = w1.auditWrites[0];
    is(!!a && a.body && a.body.event_type === 'pay_period_closed'
       && a.body.employee_id === 'S1' && a.body.role === 'owner'
       && a.body.detail && Array.isArray(a.body.detail.added)
       && a.body.detail.added.length === 1
       && a.body.detail.added[0].paid_at === PERIOD_A.paid_at,
       'W11. the audit row names the event, the employee, the role AND the '
     + 'period(s) ADDED with their paid_at -- "settings changed" would not tell '
     + 'an auditor which wages got frozen',
       'audit=' + JSON.stringify(a && a.body));
  } else {
    cannot('W11. the audit row names what was added', 'W1 did not succeed');
  }

  // ── W12: AN UNREADABLE EXISTING LIST IS NOT AN EMPTY ONE ──────────────
  try {
    const r = await drive({ role: 'owner', prevReadFails: true });
    is(r.status === 503 && code(r) === 'CLOSED_PERIODS_UNREADABLE'
       && r.settingsWrites.length === 0,
       'W12. a FAILED read of the existing list is 503 and writes nothing -- '
     + 'treating it as empty would let an already-closed period be dropped '
     + 'silently, which is W6 defeated by a transport blip',
       'status=' + r.status + ' code=' + code(r));
  } catch (e) {
    bad('W12. an unreadable existing list refuses the write', e && e.stack);
  }

  // ── W13: THE event_type IS IN THE LIVE CHECK CONSTRAINT ───────────────
  // tools/audit_event_type_check.py exits COULD NOT RUN for api/sd-data.js --
  // it needs a `const APP = '...'` in the caller to resolve a table and
  // sd-data.js serves every app, so it has none. MEASURED, not assumed: that
  // tool prints "This is NOT 'every event type is allowed'. Nothing was
  // compared." So this arm covers the gap for THIS emitter rather than
  // trusting a checker that refused to look. (The tool is cc's; the gap is
  // routed, not edited.)
  {
    let sql = null;
    try { sql = fs.readFileSync(path.join(ROOT, 'sql',
      'sairnsenior_audit_log_schema.sql'), 'utf8'); } catch (e) { sql = null; }
    if (sql === null) {
      cannot('W13. pay_period_closed is in the audit table CHECK constraint',
             'sql/sairnsenior_audit_log_schema.sql could not be read');
    } else {
      const m = /event_type\s+text\s+not\s+null\s+check\s*\(\s*event_type\s+in\s*\(([\s\S]*?)\)\s*\)/i.exec(sql);
      const inside = m ? m[1] : '';
      is(!!m && /'pay_period_closed'/.test(inside),
         'W13. the event_type this branch emits is INSIDE the audit table\'s '
       + 'CHECK constraint. An event_type missing from a CHECK is a silently '
       + 'dropped audit row everywhere else on this platform; here it is a '
       + 'refusal, so it would be loud -- but it would still block every close',
         'constraint parsed=' + !!m + ' contents=' + inside.replace(/\s+/g, ' ').slice(0, 300));
    }
  }

  // ── W14: THE CONSTANT IS ITS OWN, not a reference to MANAGEMENT_ROLES ──
  {
    const senAuth = require('./sen-auth.js');
    const src = fs.readFileSync(AUTH_SRC, 'utf8');
    const close = senAuth.SEN_PERIOD_CLOSE_ROLES || {};
    const sameObject = senAuth.SEN_PERIOD_CLOSE_ROLES === senAuth.MANAGEMENT_ROLES;
    is(!!close.owner && !!close.billing && !close.scheduler && !close.coordinator
       && !close.caregiver && !sameObject
       && /const SEN_PERIOD_CLOSE_ROLES = roleSet\(/.test(src),
       'W14. SEN_PERIOD_CLOSE_ROLES is { owner, billing } and is a SEPARATE '
     + 'object from MANAGEMENT_ROLES, declared with its own roleSet() call. '
     + 'Aliasing it would reintroduce exactly the silent widening W5 drives',
       'roles=' + JSON.stringify(close) + ' sameObject=' + sameObject);
  }

  console.log('');
  console.log('  passed ' + pass + '  failed ' + fail + '  unproven ' + unproven);
  if (fail) console.log('  FAILING ARMS: ' + failed.join(' '));
  if (unproven) console.log('  UNPROVEN ARMS: ' + notProved.join(' '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main().catch((e) => { console.log('  HARD ERROR ' + (e && e.stack)); process.exit(1); });
