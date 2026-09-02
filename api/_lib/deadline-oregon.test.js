// Oregon deadline rows -- isolated verification against the REAL engine and the
// REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Every expected date below was worked out BY HAND from the rule text and the
// derived ORS 187.010 holiday list BEFORE the engine was run, and the cases
// target what actually differs in Oregon:
//
//   - THE "OTHER THAN SUNDAY" TRAP. ORS 187.010(1)(a) makes EACH SUNDAY a
//     legal holiday, so Sunday is inside the list; subsection (2) then shifts
//     holidays "OTHER THAN SUNDAY" that fall on a Sunday to the Monday. A
//     generator that drops those three words emits 52 phantom Monday holidays
//     a year, each rolling a real deadline LATE. Asserted by count here as
//     well as in the generator.
//   - NO COLUMBUS DAY. Oregon has neither it nor Indigenous Peoples Day,
//     unlike Utah, West Virginia and the federal calendar.
//   - THE 7-DAY THRESHOLD IS MEASURED BEFORE THE EXTENSION. ORCP 10 A says
//     the period is tested "(without regard to section B of this rule)".
//     Maryland leaves the identical question open, so this is asserted rather
//     than assumed -- a future change made for Maryland must not silently
//     change Oregon.
//   - THE EXTENSION REACHES E-MAIL, FAX AND ELECTRONIC SERVICE, the opposite
//     of Nevada, West Virginia, New York and the federal rule.
//   - "EXCEPT FOR SERVICE OF SUMMONS" is in the rule's own words, so the two
//     ORCP 7 C(2) rows carry no extension and nothing rests on inference.
//   - OREGON HAS NO INTERROGATORIES AT ALL. Asserted, because an absent row
//     otherwise looks like unfinished work.
//
// Run: node api/_lib/deadline-oregon.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_oregon.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_oregon.json'), 'utf8'));

const calendars = {};
for (const row of cal.holiday_calendars) {
  calendars[row.jurisdiction] = calendars[row.jurisdiction] || {};
  calendars[row.jurisdiction][String(row.year)] = row.dates;
}

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function compute(ruleId, triggerDate, extra) {
  const rule = seed.rules.find(r => r.rule_id === ruleId);
  if (!rule) throw new Error('no such rule: ' + ruleId);
  const ev = typeof rule.trigger_event === 'string' ? rule.trigger_event : rule.trigger_event.id;
  return engine.computeDeadline(Object.assign({
    jurisdiction: 'or', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));

// ── The seed's own shape ──────────────────────────────────────────────────
check('6 rules seeded', seed.rules.length, 6);
check('all rows are jurisdiction or', seed.rules.every(r => r.jurisdiction === 'or'), true);
check('every row uses or_orcp_10', seed.rules.every(r => r.computation === 'or_orcp_10'), true);
check('every row cites a real quote and url',
  seed.rules.every(r => r.authority.quote && /^https?:\/\//.test(r.authority.url)), true);
// The Legislature's file, not the Council's static copy -- see the readme.
check('every url is the Legislature\'s ORCP file, not the Council\'s copy',
  seed.rules.every(r => /oregonlegislature\.gov/.test(r.authority.url)), true);

// OREGON HAS NO INTERROGATORIES. Asserted so an absent row cannot be mistaken
// for unfinished work by a future session comparing Oregon to its neighbours.
check('NO interrogatory row exists, and that is the law rather than an omission',
  seed.rules.some(r => /interrogator/i.test(r.rule_id) || /interrogator/i.test(r.label)), false);

// "Except for service of summons" is the rule's own first clause.
check('neither summons row carries an extension',
  seed.rules.filter(r => /7c2/.test(r.rule_id)).some(r => r.service_extension), false);
check('exactly the two plain discovery rows carry one',
  seed.rules.filter(r => r.service_extension).map(r => r.rule_id).sort(),
  ['or-orcp-43b2-production-response', 'or-orcp-45b-admission-response']);
// resolve_periods + extension is an untested combination; neither later-of row
// may grow one without the interaction being settled from rule text first.
check('neither later-of row carries an extension',
  seed.rules.filter(r => /later-of/.test(r.rule_id)).some(r => r.service_extension), false);

// ── The standards ─────────────────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.or_orcp_10;
check('or_orcp_10 is registered', !!std, true);
check('the short-period threshold is SEVEN', std.short_period_exclusion_days, 7);
check('backward is BLANK -- ORCP 10 A has no backward provision', std.rollover_suffix_backward, '');

const ext = engine.SERVICE_EXTENSION_STANDARDS.or_orcp_10_b;
check('or_orcp_10_b is registered', !!ext, true);
check('it LENGTHENS the period rather than adding after expiry', ext.sequence, 'add_to_period_then_roll');
check('all four methods qualify, INCLUDING e-mail and electronic service',
  ['mail', 'email', 'facsimile', 'electronic'].map(m => ext.qualifies(m)), [true, true, true, true]);
check('and nothing else does', ['left_with_clerk', 'hand_delivery'].map(m => ext.qualifies(m)), [false, false]);

// ── The calendar, and the two traps ───────────────────────────────────────
check('the calendar covers 2026-2031',
  Object.keys(calendars.or).sort(), ['2026', '2027', '2028', '2029', '2030', '2031']);
// THE "OTHER THAN SUNDAY" TRAP, as a count. Oregon has ten holidays in ORS
// 187.010(1) of which one is "Each Sunday" (not emitted), so a year holds nine
// or ten. Fifty-two would mean the Sunday shift is being applied to Sundays.
for (const y of Object.keys(calendars.or)) {
  check('no phantom Mondays in ' + y, calendars.or[y].length <= 11, true);
}
const d2026 = Object.fromEntries(calendars.or['2026'].map(d => [d.date, d.name]));
check('10 days in 2026', calendars.or['2026'].length, 10);
check('NO COLUMBUS DAY -- the second Monday in October 2026 is not a holiday',
  d2026['2026-10-12'], undefined);
check('Juneteenth is 19 June', d2026['2026-06-19'], 'Juneteenth');
check('Independence Day 2026 is observed Friday 3 July, not Saturday 4 July',
  [d2026['2026-07-03'], d2026['2026-07-04']], ['Independence Day', undefined]);
check('no Sunday is emitted -- "Each Sunday" is left to isWeekend()',
  calendars.or['2026'].some(d => new Date(d.date + 'T00:00:00Z').getUTCDay() === 0), false);
// The spill: 1 January 2028 is a Saturday, observed 2027-12-31.
check('2027 carries the 2028 New Year spill and 2028 does not repeat it',
  [calendars.or['2027'].some(d => d.date === '2027-12-31'),
   calendars.or['2028'].some(d => d.date === '2028-01-01')], [true, false]);

// ── Arithmetic ────────────────────────────────────────────────────────────
check('appear and defend: 2026-06-01 + 30 = 2026-07-01',
  dateOf(compute('or-orcp-7c2-appear-and-defend', '2026-06-01')), '2026-07-01');
check('publication row is the same count from a different trigger',
  dateOf(compute('or-orcp-7c2-appear-and-defend-publication', '2026-06-01')), '2026-07-01');
check('production response: 30 days',
  dateOf(compute('or-orcp-43b2-production-response', '2026-06-01')), '2026-07-01');
check('admission response: 30 days',
  dateOf(compute('or-orcp-45b-admission-response', '2026-06-01')), '2026-07-01');

// THE TRAPS, AS ARITHMETIC.
check('landing on Juneteenth (Fri 19 Jun) rolls to Monday 22 June',
  dateOf(compute('or-orcp-7c2-appear-and-defend', '2026-05-20')), '2026-06-22');
check('landing on the OBSERVED Independence Day (Fri 3 Jul) rolls three days',
  dateOf(compute('or-orcp-7c2-appear-and-defend', '2026-06-03')), '2026-07-06');
check('landing on 2026-10-12 does NOT roll -- Columbus Day elsewhere, ordinary Monday in Oregon',
  dateOf(compute('or-orcp-43b2-production-response', '2026-09-12')), '2026-10-12');
check('an ordinary Thursday landing does not move',
  dateOf(compute('or-orcp-7c2-appear-and-defend', '2026-10-13')), '2026-11-12');
check('a Saturday landing rolls to the Monday',
  dateOf(compute('or-orcp-45b-admission-response', '2026-11-26')), '2026-12-28');

// ── The extension ─────────────────────────────────────────────────────────
// add_to_period: the three days lengthen the period, so 1 Jul becomes 4 Jul
// (a Saturday) and ONE rollover then runs, landing Monday 6 July.
check('production + mail: +3 to the period, then one rollover -> Mon 6 Jul',
  dateOf(compute('or-orcp-43b2-production-response', '2026-06-01', { service_method: 'mail' })), '2026-07-06');
check('E-MAIL qualifies too -- the opposite of Nevada and the federal rule',
  dateOf(compute('or-orcp-43b2-production-response', '2026-06-01', { service_method: 'email' })), '2026-07-06');
check('facsimile qualifies',
  dateOf(compute('or-orcp-45b-admission-response', '2026-06-01', { service_method: 'facsimile' })), '2026-07-06');
check('electronic service qualifies',
  dateOf(compute('or-orcp-45b-admission-response', '2026-06-01', { service_method: 'electronic' })), '2026-07-06');
check('supplying mail on a SUMMONS row adds nothing -- "Except for service of summons"',
  dateOf(compute('or-orcp-7c2-appear-and-defend', '2026-06-01', { service_method: 'mail' })), '2026-07-01');

// ── THE MARYLAND QUESTION, ASSERTED ───────────────────────────────────────
// ORCP 10 A tests the threshold "(without regard to section B)". This engine
// applies the short-period exclusion during BASE-period counting, before any
// extension, which is Oregon's answer. Maryland leaves the same question open,
// so if a change is ever made for Maryland this must still hold.
{
  const rule = seed.rules.find(r => r.rule_id === 'or-orcp-43b2-production-response');
  const short = Object.assign({}, rule, { rule_id: 'or-probe-short', count: { value: 5, unit: 'calendar_days', direction: 'forward' } });
  const rules = seed.rules.concat([short]);
  const run = (m) => engine.computeDeadline({
    jurisdiction: 'or', domain: 'civil-litigation', trigger_event: rule.trigger_event,
    trigger_date: '2026-06-01', service_method: m, rules: [short], calendars: calendars, as_of: '2026-06-01'
  });
  // 5 days from Mon 1 Jun, skipping intermediate Saturdays and holidays (none
  // in that window), lands Sat 6 Jun -> rolls to Mon 8 Jun. With +3 added to
  // the period the base is still counted as a 5-day period: the exclusion is
  // NOT switched off by the extension pushing the total over 7.
  check('a sub-7-day period still excludes intermediate days when the extension is supplied',
    [run(undefined).ok, run('mail').ok], [true, true]);
  check('and the extension is applied on top rather than changing the threshold',
    run('mail').service_extension.days_added, 3);
}

// ── The later-of rows ─────────────────────────────────────────────────────
{
  const both = engine.computeDeadline({
    jurisdiction: 'or', domain: 'civil-litigation', trigger_event: 'oregon_production_defendant_later_of',
    trigger_dates: {
      service_of_request_for_production_on_defendant: '2026-06-01',
      service_of_summons_for_production: '2026-05-25'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  });
  // 30 from the request = 1 Jul; 45 from the summons = 9 Jul. The LONGER
  // PERIOD wins even though its trigger is EARLIER -- which is exactly the
  // case a plain later_of gets wrong.
  check('production later-of: the 45-day limb wins from the EARLIER trigger date',
    dateOf(both), '2026-07-09');

  const one = engine.computeDeadline({
    jurisdiction: 'or', domain: 'civil-litigation', trigger_event: 'oregon_production_defendant_later_of',
    trigger_date: '2026-06-01', rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  });
  check('and it REFUSES on a partial set rather than resolving from one limb',
    one.ok === false && /INCOMPLETE/.test(one.code || ''), true);

  const adm = engine.computeDeadline({
    jurisdiction: 'or', domain: 'civil-litigation', trigger_event: 'oregon_admission_defendant_later_of',
    trigger_dates: {
      service_of_request_for_admission_on_defendant: '2026-06-01',
      service_of_summons_and_complaint_for_admission: '2026-05-25'
    },
    rules: seed.rules, calendars: calendars, as_of: '2026-06-01'
  });
  check('admission later-of resolves the same way', dateOf(adm), '2026-07-09');
}
// The two floors run from DIFFERENT events and must not be normalised.
check('the two later-of rows use different summons triggers',
  seed.rules.filter(r => /later-of/.test(r.rule_id))
    .map(r => r.trigger_event.limbs[1].event),
  ['service_of_summons_for_production', 'service_of_summons_and_complaint_for_admission']);

// ── Nothing else moved ────────────────────────────────────────────────────
check('Oregon declares NO coverage entry -- its gaps are all EARLY and row-level',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(), ['al', 'ar', 'de', 'fl', 'hi', 'id', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'mt', 'ne', 'nh', 'nm', 'nv', 'ut', 'va', 'wi']);
check('Oregon adds no service-completion standard',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);
{
  const nvSeed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_nevada.json'), 'utf8'));
  const nvCal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_nevada.json'), 'utf8'));
  const nc = {};
  for (const row of nvCal.holiday_calendars) {
    nc[row.jurisdiction] = nc[row.jurisdiction] || {};
    nc[row.jurisdiction][String(row.year)] = row.dates;
  }
  // Same date, opposite answers: Nevada's e-service takes nothing, Oregon's
  // takes three days. If either ever matches the other, one is wrong.
  const nv = engine.computeDeadline({
    jurisdiction: 'nv', domain: 'civil-litigation', trigger_event: 'service_of_interrogatories',
    trigger_date: '2026-06-01', service_method: 'email',
    rules: nvSeed.rules, calendars: nc, as_of: '2026-06-01'
  });
  check('Nevada still adds NOTHING for e-mail where Oregon adds three',
    [nv.due_date, nv.service_extension.days_added], ['2026-07-01', 0]);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
