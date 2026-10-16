// api/b17-closed-period-write-path.test.js
//
// Run:  node api/b17-closed-period-write-path.test.js
//
// REQUIREMENT (MICHAEL, 2026-10-15): pay periods may be closed by owner plus
//   the office-manager / payroll person ONLY, others refused, audit-logged.
//
// ── WHY THIS EXISTS: b16's FREEZE WAS INERT ───────────────────────────────
// b16 built the paid-period freeze in api/_lib/sen-payroll.js and nothing
// could write the closed-period list, so there were no closed periods anywhere
// and the freeze was code that could not fire. The b16 handoff carried it as
// open item 4 and named the reason the write path was not built with it: "who
// may freeze a pay period" is a permissions decision, not a handler detail.
//
// ── RE-AIMED 2026-10-16 (b17) AT A DIFFERENT RESOURCE, AND WHY ───────────
// This suite's first version drove `sen_settings` with
// `setting_key: 'payroll_closed_periods'`. fourth's b26 FINDING H3 drove the
// hole through the real endpoint: that path upserts with
// `resolution=merge-duplicates`, so a write with a SHORTER list replaces the
// stored one, un-freezing wages already paid with no record the list had ever
// been longer -- and the append-only comparison this suite was asserting was a
// patch on a store whose own comment says it validates nothing.
//
// SO THE CLOSE PATH MOVED to `sen_period_closings`: append-only, one row per
// closing, SELECT and INSERT grants only. Every arm below is the SAME
// REQUIREMENT re-pointed at it -- the role gate, the validation, the
// append-only refusal, the audit-must-land departure. The generic settings
// path now REFUSES the key by name, which is
// api/b17-freeze-reopen.test.js's subject along with the reopen half.
//
// ── THE ONE ARM THAT MATTERS MOST IS W5, AND IT IS AN ABLATION ────────────
// `SEN_PERIOD_CLOSE_ROLES` is { owner, billing } and SAIRNsenior's
// `MANAGEMENT_ROLES` is ALSO { owner, billing }. So any gate that asked
// MANAGEMENT_ROLES would refuse exactly the same roles today, and THE NEW GATE
// CANNOT BE SEEN TO FIRE. A check that cannot fire is indistinguishable from
// dead code, and a suite that only drove the roles as they stand would be
// asserting nothing about it.
//
// W5 therefore WIDENS MANAGEMENT_ROLES to include 'scheduler' in a copy of
// api/sen-auth.js and requires the close to STILL be refused 403 by the
// narrower gate. That is the exact future the constant exists for -- its own
// note in api/sen-auth.js says so -- and it is the only way to drive it.
//
// ── AND ONE DEPARTURE, DRIVEN RATHER THAN ASSERTED IN PROSE ───────────────
// A failed audit write REFUSES the close (W10), which is the OPPOSITE of
// api/_lib/audit.js's deliberate best-effort posture for credential grants.
// The argument is in the handler and in the SQL file; the arm is here. Note
// neither sql/sairnsenior_audit_log_schema.sql nor
// sql/sairnsenior_period_closings_schema.sql has been run, so 503 is the
// EXPECTED live answer today -- W10 is not a hypothetical.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

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

const PERIOD_A = { closing_id: 'CL-A', kind: 'close',
                   period_start: '2026-10-01', period_end: '2026-10-15',
                   paid_at: '2026-10-16T00:00:00Z', reason: 'October first half' };
const PERIOD_B = { closing_id: 'CL-B', kind: 'close',
                   period_start: '2026-10-16', period_end: '2026-10-31',
                   paid_at: '2026-11-01T00:00:00Z', reason: 'October second half' };

// A stored ledger row, as PostgREST would return it.
function ledgerRow(p, at) {
  return { closing_id: p.closing_id,
           data: { kind: p.kind || 'close', period_start: p.period_start,
                   period_end: p.period_end, paid_at: p.paid_at,
                   reverses: p.reverses || null, reason: p.reason || null },
           created_by: 'S0', created_role: 'owner',
           created_at: at || '2026-10-16T00:00:00Z' };
}

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
    if (/sen_period_closings/.test(u) && method === 'GET') {
      if (o.prevReadFails) {
        return { ok: false, status: 500, headers: { get: () => '' },
                 text: async () => '{}', json: async () => ({ message: 'boom' }) };
      }
      if (o.notProvisioned) {
        return { ok: false, status: 404, headers: { get: () => '' },
                 text: async () => 'relation "public.sen_period_closings" does not exist',
                 json: async () => ({}) };
      }
      const prev = o.prev === undefined ? [] : o.prev;
      return res200(prev.map((p, i) => ledgerRow(p,
        '2026-10-1' + (6 + i) + 'T00:00:00Z')));
    }
    // THE LEGACY sen_settings ROW. Empty unless an arm supplies one -- no real
    // agency has one, measured, and the union reads it anyway.
    if (/sen_settings\?/.test(u) && method === 'GET') {
      if (o.legacyReadFails) {
        return { ok: false, status: 500, headers: { get: () => '' },
                 text: async () => '{}', json: async () => ({ message: 'boom' }) };
      }
      return res200(o.legacy ? [{ data: { periods: o.legacy } }] : []);
    }
    if (method !== 'GET') {
      let parsed = null;
      try { parsed = JSON.parse(init.body); } catch (e) { parsed = null; }
      writes.push({ url: u, method: method, kind: 'closing', body: parsed });
      if (o.insertRejects) {
        return { ok: false, status: 400, headers: { get: () => '' },
                 text: async () => o.insertRejects, json: async () => ({}) };
      }
      return res200([parsed]);
    }
    return res200([]);
  };

  // A FRESH MODULE GRAPH EVERY DRIVE. b16 paid for this: an ablation restores
  // the FILE in its finally and the loaded module object stays in
  // require.cache, so a later arm runs against the mutant and reports it as a
  // wiring failure. Restoring a file is not unloading it.
  ['./_lib/sen-evv-clock', './_lib/sen-payroll', './_lib/audit',
   './_lib/sen-evv-readiness', './sen-auth.js', './sd-data.js'].forEach((m) => {
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
    body: { action: o.action || 'write', resource: 'sen_period_closings',
            payload: o.payload === undefined ? PERIOD_A : o.payload } }, out);
  return { status: out.statusCode, body: out.body, writes: writes,
           closingWrites: writes.filter((w) => w.kind === 'closing'),
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
    const wrote = w1.closingWrites[0];
    is(w1.status === 200 && !!wrote
       && wrote.body.closing_id === 'CL-A'
       && wrote.body.data.kind === 'close'
       && wrote.body.data.period_start === PERIOD_A.period_start
       && wrote.body.data.paid_at === PERIOD_A.paid_at
       && !/on_conflict|merge-duplicates/.test(wrote.url + JSON.stringify(wrote))
       && Array.isArray(w1.body.effective_closed_periods),
       'W1. an OWNER closes a pay period: 200, ONE appended row carrying the '
     + 'period and its paid_at, no upsert, and the derived set comes back',
       w1.status + ' ' + JSON.stringify(wrote && wrote.body));
  } catch (e) {
    bad('W1. an OWNER closes a pay period', e && e.stack);
  }

  // ── W2: AND SO CAN THE BILLING / PAYROLL ROLE ──────────────────────────
  try {
    const r = await drive({ role: 'billing' });
    is(r.status === 200 && r.closingWrites.length === 1,
       'W2. the BILLING (office-manager/payroll) role closes a pay period: 200. '
     + 'Michael named "owner plus office manager / payroll person" and billing '
     + 'IS this app\'s back-office/payroll tier',
       r.status + ' ' + code(r));
  } catch (e) {
    bad('W2. the BILLING role closes a pay period', e && e.stack);
  }

  // ── W3/W4: THE ROLES THAT MAY NOT, and NOTHING IS WRITTEN ──────────────
  for (const role of ['scheduler', 'coordinator', 'caregiver']) {
    try {
      const r = await drive({ role: role });
      is(r.status === 403 && code(r) === 'FORBIDDEN' && r.closingWrites.length === 0
         && /limited to/.test(String(r.body && r.body.error && r.body.error.message)),
         'W3. a ' + role + ' is REFUSED 403 and writes NO row',
         r.status + ' ' + code(r) + ' writes=' + r.closingWrites.length);
    } catch (e) {
      bad('W3. a ' + role + ' is REFUSED', e && e.stack);
    }
  }

  // ── W5: THE ARM THAT MAKES THE NEW GATE MEAN ANYTHING ──────────────────
  try {
    const r = ablateAuth(A_MGMT,
      "const MANAGEMENT_ROLES = roleSet({ owner: true, billing: true, scheduler: true });",
      () => drive({ role: 'scheduler' }));
    if (!r.ok) {
      cannot('W5. ABLATION -- a WIDENED MANAGEMENT_ROLES does not widen who may close', r.why);
    } else {
      const got = await r.result;
      is(got.status === 403 && code(got) === 'FORBIDDEN'
         && got.closingWrites.length === 0,
         'W5. ABLATION -- with MANAGEMENT_ROLES widened to include scheduler, a '
       + 'scheduler is STILL refused the close. SEN_PERIOD_CLOSE_ROLES is the '
       + 'gate, not the general back-office bucket, and this is the only arm '
       + 'under which the difference is observable',
         got.status + ' ' + code(got) + ' writes=' + got.closingWrites.length);
    }
  } catch (e) {
    cannot('W5. ABLATION -- a WIDENED MANAGEMENT_ROLES does not widen who may close',
      e && e.stack);
  }

  // ── W6: APPEND-ONLY. The same closing_id is never rewritten. ───────────
  // THE MIRROR OF THE DEFECT b16 CLOSED, and the mirror of H3: a correction
  // approved after a pay run must not restate a closed total, and REWRITING
  // the closing does exactly that by a different door with no trail at all.
  try {
    const r = await drive({ role: 'owner', prev: [PERIOD_A],
                            payload: Object.assign({}, PERIOD_A,
                              { paid_at: '2026-12-01T00:00:00Z' }) });
    is(r.status === 409 && code(r) === 'CLOSING_IMMUTABLE'
       && r.closingWrites.length === 0
       && /append-only/.test(String(r.body.error.message))
       && /reopen/.test(String(r.body.error.message)),
       'W6. re-writing an existing closing_id (here: moving its paid_at later, '
     + 'which would make an owed adjustment vanish) is 409 CLOSING_IMMUTABLE, '
     + 'writes nothing, and the message names the reopen route',
       r.status + ' ' + code(r) + ' writes=' + r.closingWrites.length);
  } catch (e) {
    bad('W6. rewriting a closing is refused', e && e.stack);
  }

  // ── W7: CONTROL -- append-only means APPEND IS ALLOWED ─────────────────
  // Without this, W6 could be passing because the branch refuses everything.
  try {
    const r = await drive({ role: 'owner', prev: [PERIOD_A], payload: PERIOD_B });
    is(r.status === 200 && r.closingWrites.length === 1
       && r.closingWrites[0].body.closing_id === 'CL-B',
       'W7. CONTROL -- appending a SECOND closing alongside the first is 200, so '
     + 'W6 is the immutability rule and not a branch that refuses everything',
       r.status + ' ' + code(r));
  } catch (e) {
    bad('W7. CONTROL -- appending a closing is allowed', e && e.stack);
  }

  // ── W7b: AND THE SAME PERIOD CANNOT BE CLOSED TWICE ───────────────────
  // Two closings for one period means two freeze instants and the replay
  // would have to pick one -- a wrong answer available for free.
  try {
    const r = await drive({ role: 'owner', prev: [PERIOD_A],
                            payload: Object.assign({}, PERIOD_A,
                              { closing_id: 'CL-A2', paid_at: '2026-12-01T00:00:00Z' }) });
    is(r.status === 409 && code(r) === 'PERIOD_ALREADY_CLOSED'
       && r.closingWrites.length === 0,
       'W7b. closing the SAME period under a new closing_id is 409 '
     + 'PERIOD_ALREADY_CLOSED -- one period, one freeze instant',
       r.status + ' ' + code(r));
  } catch (e) {
    bad('W7b. the same period cannot be closed twice', e && e.stack);
  }

  // ── W8: A paid_at NOBODY CAN READ IS REFUSED AT THE WRITE ──────────────
  // Validated here as well as in the engine, and that is not a second copy of
  // the rule: the engine REFUSES A PAY RUN on a bad record
  // (UNDATED_CLOSED_PERIOD), so a bad write stored today breaks every pay run
  // from then on. Refusing the WRITE is the only place the person who made the
  // mistake is still present.
  try {
    const r = await drive({ role: 'owner',
      payload: Object.assign({}, PERIOD_A, { paid_at: 'whenever' }) });
    is(r.status === 400 && code(r) === 'INVALID_CLOSING'
       && r.closingWrites.length === 0
       && /paid_at/.test(String(r.body.error.message)),
       'W8. a closing whose paid_at cannot be read is 400 INVALID_CLOSING at the '
     + 'WRITE, not a pay run that refuses forever afterwards',
       r.status + ' ' + code(r) + ' ' + JSON.stringify(r.body));
  } catch (e) {
    bad('W8. an unreadable paid_at is refused at the write', e && e.stack);
  }

  // ── W9: A MISSING closing_id IS NOT A GENERATED ONE ───────────────────
  // The id is the append-only key. Generating one server-side would make a
  // retried request produce TWO closings for one act.
  try {
    const r = await drive({ role: 'owner',
      payload: { kind: 'close', period_start: '2026-10-01',
                 period_end: '2026-10-15', paid_at: '2026-10-16T00:00:00Z' } });
    is(r.status === 400 && code(r) === 'INVALID_CLOSING'
       && /closing_id/.test(String(r.body.error.message))
       && r.closingWrites.length === 0,
       'W9. a missing closing_id is 400 and is NOT generated server-side -- the '
     + 'id is what makes a retried request a refusal instead of a duplicate',
       r.status + ' ' + code(r));
  } catch (e) {
    bad('W9. a missing closing_id is refused', e && e.stack);
  }

  // ── W9b: AND AN UNKNOWN kind IS REFUSED BEFORE THE DATABASE SEES IT ───
  try {
    const r = await drive({ role: 'owner',
      payload: Object.assign({}, PERIOD_A, { kind: 'delete' }) });
    is(r.status === 400 && code(r) === 'INVALID_CLOSING'
       && /kind/.test(String(r.body.error.message))
       && r.closingWrites.length === 0,
       'W9b. kind "delete" is 400 in the handler -- the senpc_kind CHECK in the '
     + 'schema is the second defence, not the first',
       r.status + ' ' + code(r));
  } catch (e) {
    bad('W9b. an unknown kind is refused', e && e.stack);
  }

  // ── W10: THE AUDIT ROW MUST LAND, AND THIS IS THE DEPARTURE ────────────
  try {
    const r = await drive({ role: 'owner', auditFails: true });
    is(r.status === 503 && code(r) === 'AUDIT_UNAVAILABLE'
       && r.closingWrites.length === 0
       && /sairnsenior_audit_log_schema\.sql/.test(String(r.body.error.message)),
       'W10. a FAILED audit write REFUSES the close (503 AUDIT_UNAVAILABLE) and '
     + 'writes NO closing. api/_lib/audit.js is best-effort for credential '
     + 'grants on purpose -- a logging outage must not lock somebody out of '
     + 'their own app -- and the trade is the OTHER WAY for a wage freeze, '
     + 'which is retryable a minute later. The message names the file to run',
       r.status + ' ' + code(r) + ' writes=' + r.closingWrites.length);
  } catch (e) {
    bad('W10. a failed audit write refuses the close', e && e.stack);
  }

  // ── W11: AND THE AUDIT ROW CARRIES WHAT WAS CLOSED, not just "changed" ──
  if (w1 && w1.status === 200) {
    try {
      const a = w1.auditWrites[0];
      const b = a && a.body;
      is(!!b && b.event_type === 'pay_period_closed' && b.employee_id === 'S1'
         && b.role === 'owner'
         && b.detail && b.detail.closing_id === 'CL-A'
         && b.detail.period_start === PERIOD_A.period_start
         && b.detail.paid_at === PERIOD_A.paid_at,
         'W11. the audit row names the event, the employee, the role AND the '
       + 'period and instant that were frozen -- "settings changed" would not '
       + 'let anybody reconstruct which wage stopped being restatable',
         JSON.stringify(b));
    } catch (e) { bad('W11. the audit row names what was closed', e && e.stack); }
  } else {
    cannot('W11. the audit row names what was closed', 'W1 did not succeed');
  }

  // ── W12: AN UNREADABLE EXISTING LEDGER IS NOT AN EMPTY ONE ────────────
  try {
    const r = await drive({ role: 'owner', prevReadFails: true });
    is(r.status === 503 && code(r) === 'CLOSED_PERIODS_UNREADABLE'
       && r.closingWrites.length === 0,
       'W12. a FAILED read of the existing ledger is 503 and writes nothing -- '
     + 'treating it as empty would let a closing be replaced silently, which '
     + 'is the defect this ledger exists to prevent',
       r.status + ' ' + code(r) + ' writes=' + r.closingWrites.length);
  } catch (e) {
    bad('W12. an unreadable existing ledger refuses the write', e && e.stack);
  }

  // ── W12b: AND SO IS AN UNREADABLE LEGACY SETTINGS ROW ─────────────────
  // The union has two sources and BOTH of them failing-open would unfreeze a
  // period. Named separately so the 503 says which one.
  try {
    const r = await drive({ role: 'owner', legacyReadFails: true });
    is(r.status === 503 && code(r) === 'CLOSED_PERIODS_UNREADABLE'
       && r.closingWrites.length === 0
       && /sen_settings/.test(String(r.body.error.message)),
       'W12b. a FAILED read of the LEGACY settings row also refuses, and the '
     + 'message names which of the two sources could not be read',
       r.status + ' ' + code(r) + ' ' + JSON.stringify(r.body && r.body.error));
  } catch (e) {
    bad('W12b. an unreadable legacy row refuses the write', e && e.stack);
  }

  // ── W12c: THE TABLE NOT EXISTING YET IS AN HONEST EMPTY, NOT A 503 ────
  // 404/400 from PostgREST means the migration has not been run. An agency
  // with no ledger has never closed a period, which is a real answer. The
  // INSERT then fails with the same 404 and says which file to run.
  try {
    const r = await drive({ role: 'owner', notProvisioned: true,
      insertRejects: 'relation "public.sen_period_closings" does not exist' });
    is(r.status === 503 && code(r) === 'NOT_PROVISIONED'
       && /sairnsenior_period_closings_schema\.sql/.test(String(r.body.error.message)),
       'W12c. with the table absent the READ is an honest empty and the INSERT '
     + 'answers 503 NOT_PROVISIONED naming the schema file -- today\'s expected '
     + 'live answer, since neither SQL file has been run',
       r.status + ' ' + code(r));
  } catch (e) {
    bad('W12c. an unprovisioned table names the schema file', e && e.stack);
  }

  // ── W13: THE event_type IS IN THE LIVE CHECK CONSTRAINT ───────────────
  try {
    const sql = fs.readFileSync(
      path.join(__dirname, '..', 'sql', 'sairnsenior_audit_log_schema.sql'), 'utf8');
    const hasClose = sql.indexOf("'pay_period_closed'") !== -1;
    const hasReopen = sql.indexOf("'pay_period_reopened'") !== -1;
    is(hasClose && hasReopen,
       'W13. BOTH event types this branch emits are INSIDE the audit table\'s '
     + 'CHECK constraint. An event_type missing from a CHECK is a silently '
     + 'dropped audit row everywhere else on this platform; here it is a '
     + 'refusal, so it would be loud -- but it would still block every close',
       'close=' + hasClose + ' reopen=' + hasReopen);
  } catch (e) {
    cannot('W13. both event types are in the audit table CHECK constraint',
      e && e.message);
  }

  // ── W14: THE CONSTANT IS ITS OWN, not a reference to MANAGEMENT_ROLES ──
  try {
    const src = fs.readFileSync(AUTH_SRC, 'utf8');
    const own = /const SEN_PERIOD_CLOSE_ROLES = roleSet\(\{[^}]*owner: true[^}]*billing: true[^}]*\}\);/
      .test(src);
    const alias = /SEN_PERIOD_CLOSE_ROLES\s*=\s*MANAGEMENT_ROLES/.test(src);
    is(own && !alias,
       'W14. SEN_PERIOD_CLOSE_ROLES is { owner, billing } and is a SEPARATE '
     + 'object from MANAGEMENT_ROLES, declared with its own roleSet() call. '
     + 'Aliasing it would reintroduce exactly the silent widening W5 drives',
       'own=' + own + ' alias=' + alias);
  } catch (e) {
    cannot('W14. SEN_PERIOD_CLOSE_ROLES is its own constant', e && e.message);
  }

  // ── W15: THE RESOURCE IS REGISTERED, not just implemented ─────────────
  // An implemented-and-undeclared resource is unreachable and the 400 it gets
  // back looks exactly like a client bug. `tombstones` shipped dead that way.
  try {
    const reg = require('./_resources/sairnsenior.js');
    const listed = JSON.stringify(reg).indexOf('sen_period_closings') !== -1;
    is(listed,
       'W15. sen_period_closings is REGISTERED in api/_resources/sairnsenior.js, '
     + 'so the provisioning probe can see it and the dispatcher can reach it',
       'listed=' + listed);
  } catch (e) { bad('W15. the resource is registered', e && e.stack); }

  console.log('');
  console.log('  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log('  FAILED: ' + failed.join(', '));
  if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main();
