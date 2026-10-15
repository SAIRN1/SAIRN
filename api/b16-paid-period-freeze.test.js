// api/b16-paid-period-freeze.test.js
//
// Run:  node api/b16-paid-period-freeze.test.js
//
// REQUIREMENT (MICHAEL'S DECISION, 2026-10-15): paid periods are FROZEN. A
//   clock correction approved after a pay run never rewrites a closed total;
//   it posts as an ADJUSTMENT LINE in the next period.
//
// ── WHY THIS IS THE FIX AND NOT A NICETY ──────────────────────────────────
// b15 landed F1: api/_lib/sen-payroll.js now reads the EFFECTIVE clock, so an
// approved correction reaches pay. That closed a real underpayment -- 60
// minutes and 2000 cents per visit per correction, fourth's b23 repro -- and
// opened the mirror of it, which the b15 handoff named as the open Tier A
// question rather than leaving implied:
//
//   "a correction approved AFTER a pay run silently changes a historical
//    total, because nothing versions a paid period. If a paid period must be
//    frozen, this fix changes history quietly, which is worse than the
//    underpayment it closes."
//
// A wage already paid, reported to a payer and auditable by a state EVV
// programme is not a number that may move because somebody approved a
// correction a week later. The money is still owed -- it is paid FORWARD, with
// a line saying what it is for, which is what a restatement trail is.
//
// ── THE THREE STATES, BECAUSE THERE ARE THREE AND NOT TWO ─────────────────
// An approved correction carries `approved_at_server`. Compared with the
// period's `paid_at` that gives:
//
//   before paid_at  -> it WAS in the as-paid basis. Applies. Nothing to post.
//   after  paid_at  -> it was NOT. Does not move the closed total; posts as an
//                      adjustment in the open period. (F1, F4)
//   no timestamp    -> CANNOT TELL. Applies on the as-paid basis AND is
//                      COUNTED in `undatable_corrections` so the basis is
//                      visibly partly unverifiable. (F7)
//
// An entry with no `status` is approved -- sen-evv-clock.js's own rule, for
// every correction filed before 2026-10-14 -- and those have no
// `approved_at_server` at all. Dropping them would un-pay live corrected
// visits; silently applying them would claim a verified basis. Counting them
// is the only honest third answer. PR §1.11: "could not run" is never folded
// into "passed".
//
// AND A CLOSED PERIOD WITH NO READABLE paid_at REFUSES THE RUN (F10) rather
// than guessing which way to lean. A freeze that cannot say what it froze
// against is the silent-failure shape this platform keeps paying for.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');

const CLOCK_SRC = path.join(__dirname, '_lib', 'sen-evv-clock.js');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 500));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 500));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

// THE REAL MODULE. A reimplementation would pass against the unfixed code.
function freshPayroll(modPath) {
  const p = modPath || './_lib/sen-payroll';
  delete require.cache[require.resolve(p)];
  delete require.cache[require.resolve('./_lib/sen-evv-clock')];
  return require(p);
}

// ── FOURTH's b23 FIXTURE, CARRIED FORWARD UNCHANGED ──────────────────────
// Same visit, same numbers, so the freeze is measured against the figures the
// underpayment was measured against: 240 minutes / 8000 cents recorded,
// 300 / 10000 corrected. The delta the adjustment must carry is therefore 60
// minutes and 2000 cents, which is the same money, moved to a later period.
const RATE_PER_HOUR = 20;           // 2000 cents/hour
const DAY = '2026-10-05';           // inside the CLOSED period
const REC_IN = '2026-10-05T09:00:00Z';
const REC_OUT = '2026-10-05T13:00:00Z';   // 240 min
const COR_OUT = '2026-10-05T14:00:00Z';   // 300 min

const PAID_AT = '2026-10-16T00:00:00Z';
const CLOSED = { period_start: '2026-10-01', period_end: '2026-10-15', paid_at: PAID_AT };
const OPEN_START = '2026-10-16', OPEN_END = '2026-10-31';

function correction(approvedAtServer) {
  const e = {
    id: 'C1', field: 'clock_out_at',
    original_at: REC_OUT, proposed_at: COR_OUT,
    reason_code: 'FORGOT_TO_CLOCK_OUT',
    filed_by: 'E1', filed_at_server: '2026-10-06T10:00:00Z',
    status: 'approved', approved_by: 'S1'
  };
  if (approvedAtServer !== undefined) e.approved_at_server = approvedAtServer;
  return e;
}

function visit(corrections) {
  const v = {
    id: 'V1', visit_id: 'V1', assigned_employee_id: 'E1',
    scheduled_date: DAY, clock_in_at: REC_IN, clock_out_at: REC_OUT
  };
  if (corrections) v.clock_corrections = corrections;
  return v;
}

function resolveRate() { return { status: 'applied', rate_per_hour: RATE_PER_HOUR }; }

function run(opts, modPath) {
  const senPayroll = freshPayroll(modPath);
  const o = opts || {};
  return senPayroll.computePayroll({
    visits: o.visits,
    period_start: o.period_start,
    period_end: o.period_end,
    week_start_day: 'sunday',
    closed_periods: o.closed_periods,
    resolveRate: resolveRate
  });
}

function cg(out) {
  return out && out.caregivers && out.caregivers[0] ? out.caregivers[0] : null;
}

// ── THE MUTANT, for F8. Same directory so relative requires resolve. ──────
function ablate(anchor, replacement, tag, fn) {
  const src = fs.readFileSync(CLOCK_SRC, 'utf8');
  const n = src.split(anchor).length - 1;
  if (n !== 1) return { ok: false, why: 'anchor occurs ' + n + ' times, not 1' };
  const backup = src;
  try {
    fs.writeFileSync(CLOCK_SRC, src.split(anchor).join(replacement));
    const back = fs.readFileSync(CLOCK_SRC, 'utf8');
    if (back.indexOf(replacement) === -1) {
      return { ok: false, why: 'the mutant did not land on disk' };
    }
    return { ok: true, result: fn() };
  } finally {
    fs.writeFileSync(CLOCK_SRC, backup);
    const restored = fs.readFileSync(CLOCK_SRC, 'utf8');
    if (restored !== backup) {
      console.log('  HARD ERROR the ablation did not restore '
        + 'api/_lib/sen-evv-clock.js -- DO NOT COMMIT, the file on disk is a mutant');
      process.exit(1);
    }
  }
}

const A_ASOF = 'if (asOfMs === null) return true;';

function main() {
  console.log('api/b16-paid-period-freeze.test.js');
  console.log('  a paid period is frozen; a later approval is paid forward');

  // ── F1: THE FREEZE ──────────────────────────────────────────────────────
  let f1 = null;
  try {
    f1 = run({ visits: [visit([correction('2026-10-20T00:00:00Z')])],
               period_start: CLOSED.period_start, period_end: CLOSED.period_end,
               closed_periods: [CLOSED] });
    const b = cg(f1);
    const closed = f1 && f1.period_closed;
    is(!!b && b.minutes === 240 && b.gross_cents === 8000
       && !!closed && closed.paid_at === PAID_AT,
       'F1. a CLOSED period recomputes to its AS-PAID basis -- 240 minutes and '
     + '8000 cents, not the 300/10000 the later approval would produce -- and '
     + 'the output NAMES the period as closed with its paid_at',
       'minutes=' + (b && b.minutes) + ' cents=' + (b && b.gross_cents)
     + ' period_closed=' + JSON.stringify(closed)
     + ' refused=' + JSON.stringify(f1 && f1.refused));
  } catch (e) {
    bad('F1. a CLOSED period recomputes to its AS-PAID basis', e && e.stack);
  }

  // ── F2: CONTROL -- the freeze is about the APPROVAL TIME, not closedness
  // Without this arm "a closed period ignores every correction" passes F1, and
  // that would un-pay corrections that were genuinely in the as-paid figure.
  try {
    const out = run({ visits: [visit([correction('2026-10-10T00:00:00Z')])],
                      period_start: CLOSED.period_start, period_end: CLOSED.period_end,
                      closed_periods: [CLOSED] });
    const b = cg(out);
    is(!!b && b.minutes === 300 && b.gross_cents === 10000,
       'F2. CONTROL -- a correction approved BEFORE paid_at still applies in '
     + 'the closed period: 300 minutes, 10000 cents. The freeze compares '
     + 'approval time to paid_at; it does not blank the period',
       'minutes=' + (b && b.minutes) + ' cents=' + (b && b.gross_cents));
  } catch (e) {
    bad('F2. CONTROL -- a correction approved BEFORE paid_at still applies', e && e.stack);
  }

  // ── F3: CONTROL -- nothing is frozen in an OPEN period ──────────────────
  try {
    const openVisit = visit([correction('2026-10-20T00:00:00Z')]);
    openVisit.scheduled_date = '2026-10-20';
    openVisit.clock_in_at = '2026-10-20T09:00:00Z';
    openVisit.clock_out_at = '2026-10-20T13:00:00Z';
    openVisit.clock_corrections[0].original_at = '2026-10-20T13:00:00Z';
    openVisit.clock_corrections[0].proposed_at = '2026-10-20T14:00:00Z';
    const out = run({ visits: [openVisit], period_start: OPEN_START,
                      period_end: OPEN_END, closed_periods: [CLOSED] });
    const b = cg(out);
    is(!!b && b.minutes === 300 && b.gross_cents === 10000 && !out.period_closed,
       'F3. CONTROL -- a visit in the OPEN period uses the effective clock as '
     + 'it always did: 300 minutes, 10000 cents, and the period is not '
     + 'reported closed. b15\'s F1 fix is intact',
       'minutes=' + (b && b.minutes) + ' cents=' + (b && b.gross_cents)
     + ' period_closed=' + JSON.stringify(out.period_closed));
  } catch (e) {
    bad('F3. CONTROL -- an OPEN period still uses the effective clock', e && e.stack);
  }

  // ── F4: THE ADJUSTMENT LINE -- the money is paid FORWARD, not lost ──────
  let f4 = null;
  try {
    f4 = run({ visits: [visit([correction('2026-10-20T00:00:00Z')])],
               period_start: OPEN_START, period_end: OPEN_END,
               closed_periods: [CLOSED] });
    const adj = (f4 && f4.adjustments) || [];
    const a = adj[0];
    const b = cg(f4);
    is(adj.length === 1 && a && a.employee_id === 'E1'
       && a.minutes_delta === 60 && a.cents_delta === 2000
       && a.visit_id === 'V1' && a.closed_period_start === CLOSED.period_start
       && a.closed_period_end === CLOSED.period_end && a.paid_at === PAID_AT
       && !!b && b.adjustment_cents === 2000,
       'F4. the ADJUSTMENT LINE -- running the NEXT period posts +60 minutes '
     + 'and +2000 cents for V1, naming the closed period it belongs to and '
     + 'the paid_at it was approved after. The same money fourth measured as '
     + 'unpaid, paid in the period where the approval happened',
       'adjustments=' + JSON.stringify(adj)
     + ' adjustment_cents=' + (b && b.adjustment_cents));
  } catch (e) {
    bad('F4. the ADJUSTMENT LINE posts +60 minutes and +2000 cents', e && e.stack);
  }

  // ── F5: THE ADJUSTMENT IS NOT FOLDED INTO THE OPEN WEEK'S FLSA MATHS ────
  // Folding 60 minutes of a 5-October visit into the week of 16 October would
  // recompute overtime for hours worked in a week that is CLOSED, which is the
  // thing being frozen, one step removed. gross_cents keeps its existing
  // meaning -- the sum of the weeks -- so every existing caller is unchanged,
  // and the new money is named separately.
  if (f4) {
    const b = cg(f4);
    const weekMinutes = b ? (b.weeks || []).reduce((s, w) => s + w.minutes, 0) : null;
    is(!!b && weekMinutes === 0 && b.gross_cents === 0
       && b.adjustment_cents === 2000 && b.total_payable_cents === 2000,
       'F5. the adjustment is OUTSIDE the FLSA week maths -- weeks carry 0 '
     + 'minutes, gross_cents stays 0, and the money appears in '
     + 'adjustment_cents with total_payable_cents = gross + adjustment. '
     + 'Folding a closed week\'s hours into an open week would recompute '
     + 'overtime on a frozen week',
       'weekMinutes=' + weekMinutes + ' gross=' + (b && b.gross_cents)
     + ' adj=' + (b && b.adjustment_cents)
     + ' payable=' + (b && b.total_payable_cents));
  } else {
    cannot('F5. the adjustment is OUTSIDE the FLSA week maths', 'F4 did not run');
  }

  // ── F6: AND THE OVERTIME CONSEQUENCE IS NAMED, NOT COMPUTED ─────────────
  // Straight time at the rate in force on the SERVICE date. If those 60
  // minutes push the closed week past 40 hours there is an overtime premium
  // this does not compute, and an adjustment presented as complete would be a
  // wrong number with no warning on it.
  if (f4) {
    const nc = (f4.not_computed || []).join(' | ');
    is(/overtime/i.test(nc) && /adjustment/i.test(nc),
       'F6. the output NAMES the overtime consequence of an adjustment as not '
     + 'computed, rather than presenting a straight-time delta as a finished '
     + 'restatement',
       'not_computed=' + nc.slice(0, 300));
  } else {
    cannot('F6. the overtime consequence of an adjustment is NAMED', 'F4 did not run');
  }

  // ── F7: CANNOT TELL is a third answer and it is COUNTED ─────────────────
  try {
    const out = run({ visits: [visit([correction(undefined)])],
                      period_start: CLOSED.period_start, period_end: CLOSED.period_end,
                      closed_periods: [CLOSED] });
    const b = cg(out);
    is(!!b && b.minutes === 300 && b.gross_cents === 10000
       && b.undatable_corrections === 1 && out.undatable_corrections === 1,
       'F7. an approved correction with NO approved_at_server CANNOT be dated: '
     + 'it applies on the as-paid basis AND is counted in '
     + 'undatable_corrections, per caregiver and per period, so a partly '
     + 'unverifiable basis is visible instead of silent',
       'minutes=' + (b && b.minutes) + ' undatable(cg)='
     + (b && b.undatable_corrections) + ' undatable(period)='
     + out.undatable_corrections);
  } catch (e) {
    bad('F7. an undatable approved correction is applied AND counted', e && e.stack);
  }

  // ── F8: NO CLOSED PERIODS -> THE OLD ANSWER, UNCHANGED ─────────────────
  // Every existing caller passes no `closed_periods`. If this arm moves, the
  // freeze has changed pay for agencies that never closed a period.
  try {
    const out = run({ visits: [visit([correction('2026-10-20T00:00:00Z')])],
                      period_start: CLOSED.period_start, period_end: CLOSED.period_end });
    const b = cg(out);
    is(!!b && b.minutes === 300 && b.gross_cents === 10000
       && !out.period_closed && (out.adjustments || []).length === 0,
       'F8. CONTROL -- with NO closed_periods supplied the answer is exactly '
     + 'b15\'s: 300 minutes, 10000 cents, no period_closed, no adjustments. '
     + 'An agency that has never closed a period is unaffected',
       'minutes=' + (b && b.minutes) + ' cents=' + (b && b.gross_cents)
     + ' period_closed=' + JSON.stringify(out.period_closed)
     + ' adjustments=' + JSON.stringify(out.adjustments));
  } catch (e) {
    bad('F8. CONTROL -- no closed_periods gives b15\'s answer', e && e.stack);
  }

  // ── F9: A CLOSED PERIOD WITH NO READABLE paid_at REFUSES ───────────────
  try {
    const out = run({ visits: [visit([correction('2026-10-20T00:00:00Z')])],
                      period_start: CLOSED.period_start, period_end: CLOSED.period_end,
                      closed_periods: [{ period_start: '2026-10-01',
                                         period_end: '2026-10-15',
                                         paid_at: 'whenever' }] });
    const r = out && out.refused;
    is(!!r && r.code === 'UNDATED_CLOSED_PERIOD',
       'F9. a closed-period record whose paid_at cannot be read REFUSES the '
     + 'run (UNDATED_CLOSED_PERIOD) instead of guessing which corrections '
     + 'were in the as-paid basis. Could-not-tell is not folded into either '
     + 'answer',
       'refused=' + JSON.stringify(r)
     + ' caregivers=' + JSON.stringify(out && out.caregivers));
  } catch (e) {
    bad('F9. an unreadable paid_at REFUSES the run', e && e.stack);
  }

  // ── F11: IT POSTS ONCE. The double-pay guard. ───────────────────────────
  // Without this the adjustment would post again in EVERY period after the
  // approval, forever -- the same 2000 cents paid every fortnight, which is a
  // worse defect than the one being closed. The rule is that the adjustment
  // belongs to the period containing the approval instant.
  try {
    const nov = run({ visits: [visit([correction('2026-10-20T00:00:00Z')])],
                      period_start: '2026-11-01', period_end: '2026-11-15',
                      closed_periods: [CLOSED] });
    const b = cg(nov);
    is((nov.adjustments || []).length === 0
       && (!b || b.adjustment_cents === 0),
       'F11. the adjustment posts ONCE -- running the period AFTER the one '
     + 'containing the approval posts nothing. An adjustment that re-posted '
     + 'every period would pay the same 2000 cents forever',
       'adjustments=' + JSON.stringify(nov.adjustments)
     + ' adjustment_cents=' + (b && b.adjustment_cents));
  } catch (e) {
    bad('F11. the adjustment posts ONCE', e && e.stack);
  }

  // ── F12: AN ADJUSTMENT THAT CANNOT BE COMPUTED IS NAMED, NEVER A ZERO ───
  // A correction that INVERTS the visit (clock_out before clock_in) has no
  // usable corrected basis. A 0-cent line would say "nothing is owed"; this
  // says a human has to look.
  try {
    const invert = correction('2026-10-20T00:00:00Z');
    invert.proposed_at = '2026-10-05T08:00:00Z';   // before clock_in
    const out = run({ visits: [visit([invert])],
                      period_start: OPEN_START, period_end: OPEN_END,
                      closed_periods: [CLOSED] });
    const sk = (out.adjustments_skipped || [])[0];
    is((out.adjustments || []).length === 0 && !!sk
       && sk.reason === 'corrected_basis_unusable' && sk.visit_id === 'V1',
       'F12. an adjustment whose CORRECTED basis is unusable is reported in '
     + 'adjustments_skipped with a reason, and no 0-cent adjustment line is '
     + 'written. A zero would read as "nothing owed"',
       'adjustments=' + JSON.stringify(out.adjustments)
     + ' skipped=' + JSON.stringify(out.adjustments_skipped));
  } catch (e) {
    bad('F12. an uncomputable adjustment is NAMED, never a zero', e && e.stack);
  }

  // ── F17: effectiveClock MUST NOT THROW ON ANY ROW computePayroll ACCEPTS
  // One of the three questions the b15 Tier A obligation routed to fourth:
  // "whether effectiveClock can throw on any row shape computePayroll
  // accepts -- a throw there takes out a WHOLE PAY RUN where the old code
  // excluded one visit." Answered with a measurement rather than forwarded as
  // a reading, because the question is cheap to drive and an argument from the
  // source is what the b15 fix was already trusting.
  //
  // THE BLAST RADIUS IS THE POINT. computePayroll has no per-visit try/catch:
  // every guard it has returns or counts an exclusion. So one hostile row
  // throwing inside the substitution does not exclude that visit, it fails the
  // run for every caregiver in the period.
  try {
    const hostile = [
      null, undefined, 0, '', 'a string', true, [],
      { assigned_employee_id: 'E1' },
      { assigned_employee_id: 'E1', clock_corrections: null },
      { assigned_employee_id: 'E1', clock_corrections: 'not an array' },
      { assigned_employee_id: 'E1', clock_corrections: [null, undefined, 0, 'x'] },
      { assigned_employee_id: 'E1', clock_corrections: [{ field: 'clock_out_at' }] },
      { assigned_employee_id: 'E1', scheduled_date: DAY,
        clock_corrections: [{ field: 'clock_out_at', status: 'approved',
                              proposed_at: null, approved_at_server: 0 }] },
      { assigned_employee_id: 'E1', scheduled_date: DAY,
        clock_in_at: {}, clock_out_at: [],
        clock_corrections: [{ field: 'clock_out_at', proposed_at: {} }] },
      { assigned_employee_id: 'E1', scheduled_date: 12345,
        clock_corrections: [{ field: 'clock_out_at', status: 'approved',
                              proposed_at: COR_OUT,
                              approved_at_server: { nope: 1 } }] }
    ];
    let thrown = null;
    let out = null;
    try {
      out = run({ visits: hostile, period_start: CLOSED.period_start,
                  period_end: CLOSED.period_end, closed_periods: [CLOSED] });
    } catch (e) { thrown = e; }
    is(thrown === null && out !== null && out.refused === null
       && Array.isArray(out.caregivers),
       'F17. ' + hostile.length + ' hostile row shapes -- null, primitives, a '
     + 'string, a non-array clock_corrections, entries with null/object '
     + 'proposed_at and a non-string approved_at_server -- produce a run, not '
     + 'a throw. computePayroll has NO per-visit try/catch, so one throw in '
     + 'the substitution would fail the whole pay period and not one visit',
       'threw=' + (thrown && thrown.stack));
  } catch (e) {
    bad('F17. effectiveClock does not throw on any row computePayroll accepts',
        e && e.stack);
  }

  // ── F10: ABLATION -- remove the as-of comparison, F1 must flip ─────────
  if (f1 && cg(f1) && cg(f1).minutes === 240) {
    const r = ablate(A_ASOF, 'if (asOfMs === null || true) return true;', 'asof',
      () => run({ visits: [visit([correction('2026-10-20T00:00:00Z')])],
                  period_start: CLOSED.period_start, period_end: CLOSED.period_end,
                  closed_periods: [CLOSED] }));
    if (!r.ok) {
      cannot('F10. ABLATION of the as-of comparison flips F1', r.why);
    } else {
      const b = cg(r.result);
      is(!!b && b.minutes === 300,
         'F10. ABLATION -- with the as-of comparison in '
       + 'api/_lib/sen-evv-clock.js neutered, the closed period goes back to '
       + '300 minutes. F1 is testing THAT comparison and not the period '
       + 'bounds (ablated minutes=' + (b && b.minutes) + ')',
         'ablated minutes=' + (b && b.minutes) + ' -- still 240, so F1 passes '
       + 'for some other reason and proves nothing about the freeze');
    }
  } else {
    cannot('F10. ABLATION of the as-of comparison flips F1',
           'F1 did not produce the frozen 240, so there is no freeze to ablate');
  }

  // The module arms end here; the WIRING arms follow in wiring(), and the
  // single summary and exit code are printed there. Two summaries would be
  // two answers to 'did this suite pass'.
}

// ── END TO END THROUGH THE REAL api/sd-data.js PAYROLL ACTION ─────────────
// The module arms above prove the rule. These prove the WIRING, and the one
// that matters most is F14: the closed-period list must come from the
// agency's own sen_settings and never from the caller, because a caller who
// can declare a period open can restate a wage already paid.
const crypto = require('crypto');
process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['b16', 'freeze', String(process.pid)].join('-');
process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';
const KEY = 'k';
const HASH = crypto.createHash('sha256').update(KEY).digest('hex');

async function driveHandler(opts) {
  const o = opts || {};
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
    if (/_employee_auth\?/.test(u)) {
      return res200([{ license_hash: HASH, employee_id: 'S1', role: 'owner', active: true }]);
    }
    if (/sen_settings\?.*payroll_closed_periods/.test(u)) {
      if (o.settingsFail) {
        return { ok: false, status: 500, headers: { get: () => '' },
                 text: async () => '{}', json: async () => ({ message: 'boom' }) };
      }
      return res200(o.settingsRows === undefined
        ? [{ data: { periods: [CLOSED] } }] : o.settingsRows);
    }
    if (/sen_pay_rates\?/.test(u)) {
      return res200([{ rate_id: 'R1', data: { employee_id: 'E1',
        rate_per_hour: RATE_PER_HOUR, effective_on: '2026-01-01', term_on: '' } }]);
    }
    if (/sen_visits\?/.test(u)) {
      return res200([{ visit_id: 'V1', assigned_employee_id: 'E1',
        data: { scheduled_date: DAY, clock_in_at: REC_IN, clock_out_at: REC_OUT,
                clock_corrections: [correction('2026-10-20T00:00:00Z')] } }]);
    }
    if ((init && init.method) && init.method !== 'GET') return res200([]);
    return res200([]);
  };
  // ── THE ABLATION'S MUTANT SURVIVES IN require.cache, AND IT COST A FALSE
  //    RED. F10 writes a mutated api/_lib/sen-evv-clock.js, requires it, and
  //    restores the FILE in its finally -- but the loaded module object stays
  //    in require.cache, so the wiring arms below ran against the neutered
  //    comparison and F13/F14 reported 300 minutes as though the handler
  //    wiring were missing. Restoring a file is not the same as unloading it,
  //    and only one of the two is visible in `git diff`.
  delete require.cache[require.resolve('./_lib/sen-evv-clock')];
  delete require.cache[require.resolve('./_lib/sen-payroll')];
  delete require.cache[require.resolve('./sd-data.js')];
  const handler = require('./sd-data.js');
  const { signSessionToken } = require('./_lib/auth');
  const out = { statusCode: null, body: null };
  out.status = (c) => { out.statusCode = c; return out; };
  out.json = (b) => { out.body = b; return out; };
  const payload = { period_start: o.period_start, period_end: o.period_end,
                    week_start_day: 'sunday' };
  if (o.payloadClosed !== undefined) payload.closed_periods = o.payloadClosed;
  await handler({ method: 'POST',
    headers: { authorization: 'Bearer ' + KEY,
               'x-sd-auth': signSessionToken({ app: 'sairnsenior',
                 employee_id: 'S1', role: 'owner', license_hash: HASH }) },
    body: { action: 'payroll', resource: 'sen_visits', payload: payload } }, out);
  return out;
}

async function wiring() {
  // F13: END TO END -- the freeze reaches the endpoint
  try {
    const out = await driveHandler({ period_start: CLOSED.period_start,
                                     period_end: CLOSED.period_end });
    const d = out.body && out.body.data;
    const b = d && d.caregivers && d.caregivers[0];
    is(out.statusCode === 200 && b && b.minutes === 240 && b.gross_cents === 8000
       && d.period_closed && d.period_closed.paid_at === PAID_AT,
       'F13. END TO END through the real api/sd-data.js payroll action: the '
     + 'closed period read from sen_settings freezes the run to 240 minutes '
     + 'and 8000 cents, and period_closed is in the response',
       'status=' + out.statusCode + ' minutes=' + (b && b.minutes)
     + ' cents=' + (b && b.gross_cents)
     + ' period_closed=' + JSON.stringify(d && d.period_closed));
  } catch (e) {
    bad('F13. END TO END the freeze reaches the endpoint', e && e.stack);
  }

  // F14: THE CALLER CANNOT DECLARE A PERIOD OPEN
  try {
    const out = await driveHandler({ period_start: CLOSED.period_start,
                                     period_end: CLOSED.period_end,
                                     payloadClosed: [] });
    const d = out.body && out.body.data;
    const b = d && d.caregivers && d.caregivers[0];
    is(out.statusCode === 200 && b && b.minutes === 240
       && !!(d && d.period_closed),
       'F14. a caller sending closed_periods:[] in the payload CANNOT '
     + 'un-freeze the period -- the list comes from the agency\'s sen_settings '
     + 'and the payload field is ignored. Otherwise anyone who can run '
     + 'payroll could restate a wage already paid',
       'status=' + out.statusCode + ' minutes=' + (b && b.minutes)
     + ' period_closed=' + JSON.stringify(d && d.period_closed));
  } catch (e) {
    bad('F14. a caller cannot un-freeze a period through the payload', e && e.stack);
  }

  // F15: AN UNREADABLE SETTINGS TABLE REFUSES
  try {
    const out = await driveHandler({ period_start: CLOSED.period_start,
                                     period_end: CLOSED.period_end,
                                     settingsFail: true });
    const code = out.body && out.body.error && out.body.error.code;
    is(out.statusCode === 503 && code === 'CLOSED_PERIODS_UNREADABLE'
       && !(out.body && out.body.data),
       'F15. a FAILED read of the closed-period list is 503 '
     + 'CLOSED_PERIODS_UNREADABLE and computes nothing. Treating it as "no '
     + 'period is closed" would silently restate every wage already paid -- '
     + 'the louder of the two failures, so it is the one that refuses',
       'status=' + out.statusCode + ' code=' + code);
  } catch (e) {
    bad('F15. an unreadable closed-period list refuses the run', e && e.stack);
  }

  // F16: AND NO SETTINGS ROW AT ALL IS AN HONEST EMPTY, not a refusal
  try {
    const out = await driveHandler({ period_start: CLOSED.period_start,
                                     period_end: CLOSED.period_end,
                                     settingsRows: [] });
    const d = out.body && out.body.data;
    const b = d && d.caregivers && d.caregivers[0];
    is(out.statusCode === 200 && b && b.minutes === 300
       && !(d && d.period_closed),
       'F16. CONTROL -- an agency with NO closed-period row runs exactly as it '
     + 'did before b16: 300 minutes, nothing frozen. The refusal in F15 is '
     + 'about a FAILED READ, not about an absent record',
       'status=' + out.statusCode + ' minutes=' + (b && b.minutes)
     + ' period_closed=' + JSON.stringify(d && d.period_closed));
  } catch (e) {
    bad('F16. CONTROL -- no closed-period row is an honest empty', e && e.stack);
  }

  console.log('');
  console.log('  passed ' + pass + '  failed ' + fail + '  unproven ' + unproven);
  if (fail) console.log('  FAILING ARMS: ' + failed.join(' '));
  if (unproven) console.log('  UNPROVEN ARMS: ' + notProved.join(' '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main();
wiring();
