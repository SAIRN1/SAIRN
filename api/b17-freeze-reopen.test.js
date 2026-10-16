// api/b17-freeze-reopen.test.js
//
// Run:  node api/b17-freeze-reopen.test.js
//
// ROUTED BY fourth, b26, FINDING H3 (HIGH, on money). THE RULE, in their
// words: "a paid period is reopened only by an APPENDED correction record.
// Never a silent replace."
//
// ── WHAT THEY DROVE, THROUGH THE REAL ENDPOINT WITH A REAL SESSION ───────
//     stored before : {"periods":[{"period_start":"2026-09-01", ...}]}
//     as billing    -> HTTP 200
//     as owner      -> HTTP 200
//     stored after  : {"periods":[]}
//     rows carrying the key: 1   (an APPEND would leave 2+; a REPLACE leaves 1)
//
// and the consequence, the same pay run twice:
//
//     closed_periods = the real one -> period_closed={...} minutes=240 gross=8000
//     closed_periods = EMPTIED      -> period_closed=null  minutes=300 gross=10000
//
// A billing session -- THE SAME ROLE THAT RUNS PAYROLL -- POSTs one settings
// row, gets a 200, and the next pay run reports $100.00 for a period already
// paid at $80.00, with `period_closed: null` stating that nothing is frozen,
// and no record anywhere that the list ever contained anything.
//
// fourth: "A control erasable by the same role that runs payroll, through an
// endpoint whose own comment disclaims validating it, with the prior value
// overwritten, is not a control -- it is a convention."
//
// ── THE TWO HALVES OF THE FIX, AND BOTH ARE DRIVEN HERE ──────────────────
//   1. THE NAMED REFUSAL (P1). The generic `sen_settings` write path refuses
//      `payroll_closed_periods` BY NAME -- not by an allowlist of permitted
//      keys, which is a list the next payroll control also has to be
//      remembered into. P2 is the control: the same path still writes
//      `evv_config`, so P1 is the refusal and not a broken branch.
//   2. THE APPEND-ONLY LEDGER AND ITS REOPEN SEMANTICS (P3-P11). Reopening is
//      ALLOWED -- a payroll error found after the run has to be fixable --
//      and it is an appended row naming the closing it reverses, with a
//      REQUIRED reason, after which both rows survive forever.
//
// ── AND P8 IS THE ARM THAT MATTERS, BECAUSE IT IS THE MONEY ──────────────
// It replays H3's own figures against the REAL api/_lib/sen-payroll.js: 240
// minutes / 8000 cents while frozen, 300 / 10000 after the reopen. The numbers
// are identical to the ones fourth measured. What changed is that producing
// the second one now requires an appended, attributed, reasoned row -- so the
// restatement is still possible and is no longer silent.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const DATA_SRC = path.join(__dirname, 'sd-data.js');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['b17', 'reopen', String(process.pid)].join('-');
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

// ── fourth's SECTION A/B FIXTURE, CARRIED FORWARD ────────────────────────
const CLOSE_A = { closing_id: 'CL-A', kind: 'close',
                  period_start: '2026-10-01', period_end: '2026-10-15',
                  paid_at: '2026-10-16T00:00:00Z', reason: 'October first half' };

function ledgerRow(p, at) {
  return { closing_id: p.closing_id,
           data: { kind: p.kind || 'close', period_start: p.period_start || null,
                   period_end: p.period_end || null, paid_at: p.paid_at || null,
                   reverses: p.reverses || null, reason: p.reason || null },
           created_by: p.created_by || 'S0', created_role: p.created_role || 'owner',
           created_at: at };
}

async function drive(opts) {
  const o = opts || {};
  const writes = [];
  const inserted = [];
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
      return { ok: true, status: 201, headers: { get: () => '' },
               text: async () => '', json: async () => ([]) };
    }
    if (/sen_period_closings/.test(u) && method === 'GET') {
      // THE STUB ACCUMULATES. A fixture whose read does not reflect its own
      // write cannot test what the handler returns AFTER a write -- P6 asserts
      // the derived set the write produced, and against a static read it would
      // be asserting the state before it. The real table accumulates; so does
      // this.
      const prev = (o.ledger || []).concat(inserted);
      // created_at ORDER IS THE REPLAY ORDER and is supplied explicitly per
      // row rather than derived from array position, because P9 is about
      // order and a fixture that could not express a different order would
      // not be able to test it.
      return res200(prev.map((p, i) => ledgerRow(p, p.at || ('2026-10-2' + i + 'T00:00:00Z'))));
    }
    if (/sen_settings\?/.test(u) && method === 'GET') {
      return res200(o.legacy ? [{ data: { periods: o.legacy } }] : []);
    }
    if (method !== 'GET') {
      let parsed = null;
      try { parsed = JSON.parse(init.body); } catch (e) { parsed = null; }
      const kind = /sen_settings/.test(u) ? 'settings' : 'closing';
      writes.push({ url: u, method: method, kind: kind, body: parsed,
                    prefer: (init.headers && init.headers.Prefer) || '' });
      if (kind === 'closing' && parsed && parsed.data) {
        inserted.push(Object.assign({ closing_id: parsed.closing_id,
          created_by: parsed.created_by, created_role: parsed.created_role,
          at: '2026-10-29T00:00:00Z' }, parsed.data));
      }
      return res200([parsed]);
    }
    return res200([]);
  };

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
    body: { action: o.action || 'write',
            resource: o.resource || 'sen_period_closings',
            payload: o.payload } }, out);
  return { status: out.statusCode, body: out.body, writes: writes,
           closingWrites: writes.filter((w) => w.kind === 'closing'),
           settingsWrites: writes.filter((w) => w.kind === 'settings'),
           auditWrites: writes.filter((w) => w.kind === 'audit') };
}

function code(r) { return r.body && r.body.error && r.body.error.code; }

// ── THE PAY RUN, against the REAL engine, on a derived set ───────────────
// fourth's section B numbers: one visit, 240 minutes as paid, a correction
// approved after paid_at taking it to 300.
function payrollOn(closedPeriods) {
  ['./_lib/sen-payroll', './_lib/sen-evv-clock'].forEach((m) => {
    delete require.cache[require.resolve(m)];
  });
  const senPayroll = require('./_lib/sen-payroll');
  const DAY = '2026-10-05';
  const visit = {
    id: 'V1', visit_id: 'V1', assigned_employee_id: 'E1', scheduled_date: DAY,
    clock_in_at: DAY + 'T09:00:00Z', clock_out_at: DAY + 'T13:00:00Z',
    clock_corrections: [{
      id: 'C1', field: 'clock_out_at', original_at: DAY + 'T13:00:00Z',
      proposed_at: DAY + 'T14:00:00Z', reason_code: 'FORGOT_TO_CLOCK_OUT',
      filed_by: 'E1', filed_at_server: '2026-10-06T10:00:00Z',
      status: 'approved', approved_by: 'S1',
      approved_at_server: '2026-10-20T10:00:00Z'
    }]
  };
  const out = senPayroll.computePayroll({
    visits: [visit], period_start: '2026-10-01', period_end: '2026-10-15',
    week_start_day: 'sunday',
    closed_periods: (closedPeriods || []).map((p) => ({
      period_start: p.period_start, period_end: p.period_end, paid_at: p.paid_at })),
    resolveRate: () => ({ status: 'applied', rate_per_hour: 20 })
  });
  const b = out.caregivers && out.caregivers[0];
  return { minutes: b ? b.minutes : 0, gross: b ? b.gross_cents : 0,
           period_closed: out.period_closed, refused: out.refused };
}

function ablateData(anchor, replacement, fn) {
  const src = fs.readFileSync(DATA_SRC, 'utf8');
  const n = src.split(anchor).length - 1;
  if (n !== 1) return { ok: false, why: 'anchor occurs ' + n + ' times, not 1' };
  let r;
  try {
    fs.writeFileSync(DATA_SRC, src.split(anchor).join(replacement));
    r = { ok: true, result: fn() };
  } finally {
    fs.writeFileSync(DATA_SRC, src);
    if (fs.readFileSync(DATA_SRC, 'utf8') !== src) {
      console.log('  HARD ERROR the ablation did not restore api/sd-data.js -- DO NOT COMMIT');
      process.exit(1);
    }
  }
  return r;
}

const A_REFUSAL = "      if (key === 'payroll_closed_periods') {";

async function main() {
  console.log('api/b17-freeze-reopen.test.js');
  console.log('  the settings route is refused by name; a reopen is an appended row');

  // ── P1: THE NAMED REFUSAL ───────────────────────────────────────────────
  let p1 = null;
  try {
    p1 = await drive({ role: 'billing', resource: 'sen_settings',
      payload: { setting_key: 'payroll_closed_periods', value: { periods: [] } } });
    const msg = String(p1.body && p1.body.error && p1.body.error.message);
    is(p1.status === 409 && code(p1) === 'CLOSED_PERIODS_NOT_A_SETTING'
       && p1.settingsWrites.length === 0
       && /sen_period_closings/.test(msg)
       && p1.body.error.use_instead
       && p1.body.error.use_instead.resource === 'sen_period_closings',
       'P1. a BILLING session POSTing payroll_closed_periods as a settings key is '
     + '409 CLOSED_PERIODS_NOT_A_SETTING, writes NOTHING, and is told the '
     + 'append-only resource to use instead -- this is fourth\'s H3 repro, '
     + 'refused',
       p1.status + ' ' + code(p1) + ' writes=' + p1.settingsWrites.length);
  } catch (e) { bad('P1. the named refusal', e && e.stack); }

  // ── P2: CONTROL. The settings path still works for a real setting. ─────
  // Without this, P1 could be passing because the branch refuses everything.
  try {
    const r = await drive({ role: 'owner', resource: 'sen_settings',
      payload: { setting_key: 'evv_config',
                 value: { state: 'OH', aggregator: 'sandata' } } });
    is(r.status === 200 && r.settingsWrites.length === 1
       && r.settingsWrites[0].body.setting_key === 'evv_config',
       'P2. CONTROL -- the SAME settings path still writes evv_config, so P1 is '
     + 'a named refusal and not a broken branch',
       r.status + ' ' + code(r) + ' writes=' + r.settingsWrites.length);
  } catch (e) { bad('P2. CONTROL -- the settings path still works', e && e.stack); }

  // ── P3: A REOPEN WITHOUT A REASON IS REFUSED ───────────────────────────
  // The row is the only thing that will ever explain why a paid period was
  // un-frozen. An unexplained reopening is the silent restatement in slow
  // motion.
  try {
    const r = await drive({ role: 'owner', ledger: [CLOSE_A],
      payload: { closing_id: 'RO-1', kind: 'reopen', reverses: 'CL-A' } });
    is(r.status === 400 && code(r) === 'INVALID_CLOSING'
       && /reason is REQUIRED/.test(String(r.body.error.message))
       && r.closingWrites.length === 0,
       'P3. a reopen with no reason is 400 and writes nothing -- the reason is '
     + 'the only record of why a paid period was un-frozen',
       r.status + ' ' + code(r));
  } catch (e) { bad('P3. a reopen requires a reason', e && e.stack); }

  // ── P4: A REOPEN MUST NAME A CLOSING THAT IS IN EFFECT ─────────────────
  try {
    const r = await drive({ role: 'owner', ledger: [CLOSE_A],
      payload: { closing_id: 'RO-1', kind: 'reopen', reverses: 'CL-NOPE',
                 reason: 'typo' } });
    is(r.status === 409 && code(r) === 'NOTHING_TO_REOPEN'
       && r.closingWrites.length === 0,
       'P4. a reopen naming a closing that does not exist is 409 '
     + 'NOTHING_TO_REOPEN -- a ledger that accepts no-op rows is a ledger '
     + 'whose replay nobody can follow',
       r.status + ' ' + code(r));
  } catch (e) { bad('P4. a reopen must name a live closing', e && e.stack); }

  // ── P5: AND REOPENING THE SAME CLOSING TWICE IS REFUSED, BY NAME ───────
  try {
    const r = await drive({ role: 'owner',
      ledger: [Object.assign({ at: '2026-10-20T00:00:00Z' }, CLOSE_A),
               { closing_id: 'RO-1', kind: 'reopen', reverses: 'CL-A',
                 reason: 'first reopen', at: '2026-10-21T00:00:00Z' }],
      payload: { closing_id: 'RO-2', kind: 'reopen', reverses: 'CL-A',
                 reason: 'again' } });
    is(r.status === 409 && code(r) === 'NOTHING_TO_REOPEN'
       && /already reopened by "RO-1"/.test(String(r.body.error.message))
       && r.closingWrites.length === 0,
       'P5. reopening an already-reopened closing is 409 and NAMES the row that '
     + 'reversed it, rather than saying "not found" about something that is '
     + 'plainly in the ledger',
       r.status + ' ' + code(r) + ' ' + String(r.body.error.message).slice(0, 120));
  } catch (e) { bad('P5. a double reopen is refused by name', e && e.stack); }

  // ── P6: THE SUCCESSFUL REOPEN, AND THE CLOSE ROW SURVIVES ─────────────
  let p6 = null;
  try {
    p6 = await drive({ role: 'owner', ledger: [CLOSE_A],
      payload: { closing_id: 'RO-1', kind: 'reopen', reverses: 'CL-A',
                 reason: 'paid_at was wrong -- the run was reissued' } });
    const w = p6.closingWrites[0];
    const eff = p6.body && p6.body.effective_closed_periods;
    is(p6.status === 200 && !!w
       && w.body.closing_id === 'RO-1' && w.body.data.kind === 'reopen'
       && w.body.data.reverses === 'CL-A'
       && /paid_at was wrong/.test(String(w.body.data.reason))
       && w.body.created_by === 'S1' && w.body.created_role === 'owner'
       && Array.isArray(eff) && eff.length === 0,
       'P6. a reopen with a reason is 200: ONE appended row naming what it '
     + 'reverses and why, attributed to the VERIFIED session, and the derived '
     + 'set no longer holds the period',
       p6.status + ' ' + JSON.stringify(w && w.body));
  } catch (e) { bad('P6. the successful reopen', e && e.stack); }

  // ── P6b: AND IT IS AN INSERT, NOT AN UPSERT ───────────────────────────
  // `on_conflict` / `merge-duplicates` is the exact mechanism H3 exploited.
  // The unique index must be allowed to REFUSE.
  if (p6 && p6.status === 200) {
    try {
      const w = p6.closingWrites[0];
      const u = String(w.url);
      is(!/on_conflict/.test(u) && !/merge-duplicates/.test(String(w.prefer || '')),
         'P6b. the ledger write carries NO on_conflict and NO merge-duplicates, '
       + 'so the unique index can refuse -- an upsert here IS H3',
         u + ' Prefer=' + w.prefer);
    } catch (e) { bad('P6b. the ledger write is an insert', e && e.stack); }
  } else {
    cannot('P6b. the ledger write is an insert', 'P6 did not succeed');
  }

  // ── P7: THE REOPEN IS AUDITED AS ITS OWN EVENT ────────────────────────
  if (p6 && p6.status === 200) {
    try {
      const a = p6.auditWrites[0] && p6.auditWrites[0].body;
      is(!!a && a.event_type === 'pay_period_reopened'
         && a.employee_id === 'S1' && a.role === 'owner'
         && a.detail && a.detail.reverses === 'CL-A'
         && /paid_at was wrong/.test(String(a.detail.reason)),
         'P7. the reopen is audited as pay_period_reopened, naming who, what it '
       + 'reverses and why -- a close and a reopen are different events and '
       + 'sharing one event_type would make the log unreadable',
         JSON.stringify(a));
    } catch (e) { bad('P7. the reopen is audited as its own event', e && e.stack); }
  } else {
    cannot('P7. the reopen is audited as its own event', 'P6 did not succeed');
  }

  // ── P8: THE MONEY. H3's OWN FIGURES, against the REAL engine. ─────────
  // THIS IS THE ARM THE WHOLE FILE EXISTS FOR. The restatement is still
  // reachable -- it has to be, a payroll error must be fixable -- and it now
  // requires an appended, attributed, reasoned row to reach it.
  try {
    const frozen = payrollOn([{ period_start: CLOSE_A.period_start,
      period_end: CLOSE_A.period_end, paid_at: CLOSE_A.paid_at }]);
    const reopened = payrollOn([]);
    is(frozen.minutes === 240 && frozen.gross === 8000 && !!frozen.period_closed
       && reopened.minutes === 300 && reopened.gross === 10000
       && reopened.period_closed === null,
       'P8. THE MONEY -- frozen: 240 minutes / 8000 cents with period_closed '
     + 'set; after the reopen: 300 / 10000 with period_closed null. fourth\'s '
     + 'exact section-B figures. What changed is that the second one now needs '
     + 'an appended row naming who reopened it and why',
       JSON.stringify({ frozen: frozen, reopened: reopened }));
  } catch (e) { bad('P8. THE MONEY', e && e.stack); }

  // ── P9: THE REPLAY IS ORDERED, and order is not decoration ────────────
  // close -> reopen -> close(new id) is a period that IS frozen. A replay
  // that ignored order would answer the opposite on the same three rows.
  try {
    const r = await drive({ role: 'owner', action: 'read',
      ledger: [
        Object.assign({ at: '2026-10-20T00:00:00Z' }, CLOSE_A),
        { closing_id: 'RO-1', kind: 'reopen', reverses: 'CL-A',
          reason: 'wrong instant', at: '2026-10-21T00:00:00Z' },
        { closing_id: 'CL-A2', kind: 'close', period_start: CLOSE_A.period_start,
          period_end: CLOSE_A.period_end, paid_at: '2026-10-25T00:00:00Z',
          reason: 'reissued', at: '2026-10-22T00:00:00Z' }
      ] });
    const eff = (r.body && r.body.effective_closed_periods) || [];
    is(r.status === 200 && eff.length === 1 && eff[0].closing_id === 'CL-A2'
       && eff[0].paid_at === '2026-10-25T00:00:00Z'
       && (r.body.reopened || []).length === 1
       && r.body.data.length === 3,
       'P9. close -> reopen -> close replays to FROZEN at the NEW instant, with '
     + 'all three rows still present and the reopening still reported. The '
     + 'history is the record; the derived set is the answer',
       JSON.stringify({ eff: eff, reopened: r.body && r.body.reopened,
         rows: r.body && r.body.data && r.body.data.length }));
  } catch (e) { bad('P9. the replay is ordered', e && e.stack); }

  // ── P10: THE LEGACY SETTINGS ROW IS IN THE UNION AND IS REOPENABLE ────
  // No agency has one -- measured 2026-10-16 -- and it is read anyway,
  // because "nobody has one" is a fact about today and silently dropping a
  // freeze is unrecoverable. THE UNION IS THE MIGRATION.
  try {
    const legacy = [{ period_start: '2026-09-01', period_end: '2026-09-15',
                      paid_at: '2026-09-20T00:00:00Z' }];
    const read = await drive({ role: 'owner', action: 'read', legacy: legacy });
    const eff = (read.body && read.body.effective_closed_periods) || [];
    const synthetic = 'legacy:2026-09-01..2026-09-15';
    const reopen = await drive({ role: 'owner', legacy: legacy,
      payload: { closing_id: 'RO-L', kind: 'reopen', reverses: synthetic,
                 reason: 'migrated and corrected' } });
    is(eff.length === 1 && eff[0].period_start === '2026-09-01'
       && reopen.status === 200
       && (reopen.body.effective_closed_periods || []).length === 0,
       'P10. a LEGACY sen_settings period is in the derived set and can be '
     + 'reopened by its synthetic id (' + synthetic + ') -- the union is the '
     + 'migration, in code, where it can be tested',
       JSON.stringify({ eff: eff, reopen: reopen.status, code: code(reopen) }));
  } catch (e) { bad('P10. the legacy row is in the union', e && e.stack); }

  // ── P11: A CAREGIVER CANNOT EVEN READ THE LEDGER ──────────────────────
  // Which periods are frozen is back-office information. The write gate is
  // narrower still and is driven in api/b17-closed-period-write-path.test.js.
  try {
    const r = await drive({ role: 'caregiver', action: 'read' });
    is(r.status === 403 && code(r) === 'FORBIDDEN',
       'P11. a caregiver reading the freeze ledger is 403 -- the READ is '
     + 'management and the WRITE is narrower still',
       r.status + ' ' + code(r));
  } catch (e) { bad('P11. the read is gated', e && e.stack); }

  // ── P12: ABLATION. REMOVE THE NAMED REFUSAL AND H3 COMES BACK. ───────
  // Without this arm, P1 could be passing because of some other condition on
  // the settings branch, and the thing fourth actually found would be
  // untested. The mutant makes the key unreachable by that name, which is
  // exactly the pre-b17 state: the write falls through to the generic upsert.
  try {
    const r = ablateData(A_REFUSAL, "      if (key === 'NEVER_MATCHES_ANYTHING') {", () =>
      drive({ role: 'billing', resource: 'sen_settings',
        payload: { setting_key: 'payroll_closed_periods', value: { periods: [] } } }));
    if (!r.ok) {
      cannot('P12. ABLATION -- without the named refusal the H3 write succeeds', r.why);
    } else {
      const got = await r.result;
      is(got.status === 200 && got.settingsWrites.length === 1
         && Array.isArray(got.settingsWrites[0].body.data.periods)
         && got.settingsWrites[0].body.data.periods.length === 0,
         'P12. ABLATION -- with the named refusal removed the same request is '
       + '200 and writes `{"periods":[]}` to the settings row, which is H3 '
       + 'exactly. So P1 is testing the refusal and not something else',
         got.status + ' ' + JSON.stringify(got.settingsWrites[0]
           && got.settingsWrites[0].body && got.settingsWrites[0].body.data));
    }
  } catch (e) { bad('P12. ABLATION -- the named refusal is what P1 tests', e && e.stack); }

  console.log('');
  console.log('  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log('  FAILED: ' + failed.join(', '));
  if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main();
