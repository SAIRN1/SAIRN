// New Hampshire deadline rows -- isolated verification against the REAL engine
// and the REAL seed/calendar JSON on disk, not a scratch copy of either.
//
// Five things would be wrong if carried from a neighbour:
//
//   - ★ THERE IS NO MAILED-SERVICE EXTENSION. Not a shorter one -- NONE. New
//     Hampshire is the first seeded jurisdiction with no such provision
//     anywhere in its civil rules, because its periods run from FILING and from
//     THE DATE ON THE CLERK'S NOTICE rather than from service. An `add: 3`
//     copied from any neighbour reports LATE on every New Hampshire deadline.
//     Asserted as a FIELD (no row carries one) and as a DATE (every row returns
//     the identical answer under mail, electronic and facsimile).
//   - NO SHORT-PERIOD EXCLUSION AT ANY LENGTH. Rule 2 is two sentences and has
//     none. Four seeded rows are TEN days, which Arkansas's 14 and Alabama's
//     and Wisconsin's 11 would all have excluded weekends from.
//   - RSA 288:2 IS A SUNDAY RULE ONLY. 4 July 2026 is a Saturday, so Friday 3
//     July must NOT roll -- where Idaho and Nebraska both carry that Friday.
//   - THE BIENNIAL ELECTION DAY IS OMITTED. Tuesday 3 November 2026 must NOT
//     roll, and that is a deliberate reading probed as a negative.
//   - ADMISSIONS ARE A PLAIN THIRTY. No floor, no election, no later_of --
//     New Hampshire protects the defendant by forbidding the REQUEST for the
//     first 30 days instead, so nothing in this seed is a resolve_periods.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_newhampshire.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_newhampshire.json'), 'utf8'));

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
    jurisdiction: 'nh', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : ('REFUSED:' + r.code));
const codeOf = r => (r.ok ? 'OK:' + r.due_date : r.code);
const ANSWER = 'nh-scr-4e-answer-and-appearance-30-days';
const OBJECTION = 'nh-scr-13a-objection-to-motion-10-days';

// ── The seed's own shape ──────────────────────────────────────────────────
check('13 rules seeded', seed.rules.length, 13);
check('every rule is New Hampshire civil litigation on nh_scr_2',
  seed.rules.filter(r => r.jurisdiction === 'nh' && r.domain === 'civil-litigation'
    && r.computation === 'nh_scr_2').length, 13);
check('every rule cites the official Judicial Branch civil-rules page, a verbatim quote and retrieved_at',
  seed.rules.filter(r => r.authority.url === 'https://www.courts.nh.gov/rules-superior-court-state-new-hampshire/civil-rules'
    && r.authority.quote && r.authority.quote.length > 40
    && r.authority.retrieved_at === '2026-08-31').length, 13);
check('ONE effective date for all thirteen -- the 1 October 2013 adoption, because the published rules carry no per-rule dates at all',
  [...new Set(seed.rules.map(r => r.effective_from))], ['2013-10-01']);
check('NO row is a later_of -- New Hampshire has no floor and no election anywhere',
  seed.rules.filter(r => typeof r.trigger_event !== 'string').map(r => r.rule_id), []);
check('NO backward row is seeded',
  seed.rules.filter(r => r.count && r.count.direction === 'backward').map(r => r.rule_id), []);
check('every trigger event is distinct -- no two rows compete for one name',
  seed.rules.map(r => r.trigger_event).length,
  new Set(seed.rules.map(r => r.trigger_event)).size);

// ── ★ NO SERVICE EXTENSION EXISTS, AS A FIELD AND AS A DATE ──────────────
check('NOT ONE ROW carries a service_extension',
  seed.rules.filter(r => r.service_extension).map(r => r.rule_id), []);
check('and no service-extension standard was added for nh',
  Object.keys(engine.SERVICE_EXTENSION_STANDARDS).filter(k => k.indexOf('nh_') === 0), []);
// The field being absent is necessary and not sufficient: a standard defaulting
// somewhere else could still pay out. Every row is therefore computed three
// ways and must return one date.
{
  const bad = [];
  for (const r of seed.rules) {
    const plain = dateOf(compute(r.rule_id, '2026-03-10'));
    for (const m of ['mail', 'electronic', 'facsimile', 'other_consented_means']) {
      if (dateOf(compute(r.rule_id, '2026-03-10', { service_method: m })) !== plain) {
        bad.push(r.rule_id + ':' + m);
      }
    }
  }
  check('EVERY row returns the identical date under mail, electronic, facsimile and consented means', bad, []);
}
// The neighbours seeded immediately before New Hampshire still pay out on their
// own facts, so the absence here is New Hampshire's and did not leak outward.
check('Idaho, Nebraska and Hawaii still carry their own amounts',
  ['sairnlaw_deadline_seed_idaho.json', 'sairnlaw_deadline_seed_nebraska.json',
   'sairnlaw_deadline_seed_hawaii.json']
    .map(f => [...new Set(JSON.parse(fs.readFileSync(path.join(SQL, f), 'utf8')).rules
      .filter(r => r.service_extension).map(r => r.service_extension.add))]),
  [[3], [3], [2]]);

// ── The computation standard ─────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.nh_scr_2;
check('nh_scr_2 has NO short-period exclusion at all -- undefined, not a small number',
  [std.label, std.impl, std.short_period_exclusion_days, std.short_period_exclusion_directions],
  ['N.H. Super. Ct. R. 2', 'frcp_6a', undefined, undefined]);
check('and every citation suffix is EMPTY -- Rule 2 is one unlettered paragraph',
  [std.base_period_suffix, std.months_years_suffix,
   std.rollover_suffix_forward, std.rollover_suffix_backward], ['', '', '', '']);

// ── The calendar: ten dates, and what is not in it ───────────────────────
const d2026 = Object.fromEntries(calendars.nh['2026'].map(d => [d.date, d.name]));
check('the 2026 calendar has exactly ten dates',
  Object.keys(d2026).sort(),
  ['2026-01-01', '2026-01-19', '2026-02-16', '2026-05-25', '2026-07-04',
   '2026-09-07', '2026-10-12', '2026-11-11', '2026-11-26', '2026-12-25']);
check('the statutory names are New Hampshire\'s own, not the federal ones',
  [d2026['2026-01-19'], d2026['2026-02-16'], d2026['2026-10-12']],
  ['Martin Luther King, Jr. Civil Rights Day', 'Washington\'s Birthday', 'Columbus Day']);
check('THE BIENNIAL ELECTION DAY IS ABSENT -- Tuesday 3 November 2026',
  '2026-11-03' in d2026, false);
check('the RSA 288:2 shift has NO Saturday limb, so Friday 3 July is absent and the Saturday itself is present',
  ['2026-07-03' in d2026, '2026-07-04' in d2026], [false, true]);
check('NO Juneteenth, NO day after Thanksgiving, NO Good Friday, NO Patriots\' Day',
  ['2026-06-19' in d2026, '2026-11-27' in d2026, '2026-04-03' in d2026, '2026-04-20' in d2026],
  [false, false, false, false]);
check('Columbus Day IS enumerated -- Hawaii has none, Idaho and Nebraska do',
  '2026-10-12' in d2026, true);
check('no 2027 calendar exists', Object.keys(calendars.nh), ['2026']);
// The 3 July question, settled against the two calendars that answer it the
// other way. Idaho and Nebraska carry that Friday from Saturday-shift clauses
// inside the very sections their rules cite; RSA 288:2 has no such clause.
check('Idaho and Nebraska DO carry Friday 3 July 2026 and New Hampshire does not',
  ['sairnlaw_deadline_calendars_idaho.json', 'sairnlaw_deadline_calendars_nebraska.json']
    .map(f => JSON.parse(fs.readFileSync(path.join(SQL, f), 'utf8'))
      .holiday_calendars.some(c => c.year === 2026 && c.dates.some(d => d.date === '2026-07-03')))
    .concat(['2026-07-03' in d2026]),
  [true, true, false]);

// ── Arithmetic ───────────────────────────────────────────────────────────
check('a plain 30-day answer period',
  dateOf(compute(ANSWER, '2026-03-10')), '2026-04-09');
check('a period landing on COLUMBUS DAY rolls to the Tuesday',
  dateOf(compute(ANSWER, '2026-09-12')), '2026-10-13');
check('a period landing on Saturday 4 July rolls through the weekend to Monday the 6th',
  dateOf(compute(ANSWER, '2026-06-04')), '2026-07-06');
check('a period landing on THANKSGIVING rolls to the Friday -- which is NOT a New Hampshire holiday',
  dateOf(compute(ANSWER, '2026-10-27')), '2026-11-27');
// The two deliberate absences, probed as negatives.
check('a period landing on Friday 3 July does NOT roll -- RSA 288:2 is a Sunday rule only',
  dateOf(compute(ANSWER, '2026-06-03')), '2026-07-03');
check('a period landing on the biennial election day does NOT roll -- it is omitted on purpose',
  dateOf(compute(ANSWER, '2026-10-04')), '2026-11-03');
check('a period landing on Juneteenth does NOT roll -- New Hampshire has no Juneteenth',
  dateOf(compute(ANSWER, '2026-05-20')), '2026-06-19');

// ── ★ NO SHORT-PERIOD EXCLUSION, PROVED AS A DATE ───────────────────────
// Friday 6 March + 10 straight days is Monday 16 March. If intermediate
// weekends were excluded -- as Arkansas would below 14 days and Alabama and
// Wisconsin below 11 -- the answer would be Friday 20 March.
check('a TEN-day objection period counts straight through both weekends',
  dateOf(compute(OBJECTION, '2026-03-06')), '2026-03-16');
check('and it is NOT the business-day answer',
  dateOf(compute(OBJECTION, '2026-03-06')) !== '2026-03-20', true);
check('a ten-day period landing on a Saturday still rolls to the Monday',
  dateOf(compute(OBJECTION, '2026-03-04')), '2026-03-16');

// ── The two Rule 43 limbs, and the two Rule 22 limbs ─────────────────────
{
  const jury = 'nh-scr-43-motion-to-set-aside-jury-verdict-10-days';
  const other = 'nh-scr-43-motion-to-set-aside-other-verdict-or-decree-10-days';
  check('both Rule 43 rows quote the same sentence and split on the trigger, not the number',
    [seed.rules.find(r => r.rule_id === jury).authority.quote ===
       seed.rules.find(r => r.rule_id === other).authority.quote,
     seed.rules.find(r => r.rule_id === jury).trigger_event,
     seed.rules.find(r => r.rule_id === other).trigger_event],
    [true, 'rendition_of_jury_verdict', 'date_on_written_notice_of_verdict_or_decree']);
  check('a jury verdict returned on 6 March and a decree noticed on 6 March give the same date, for different reasons',
    [dateOf(compute(jury, '2026-03-06')), dateOf(compute(other, '2026-03-06'))],
    ['2026-03-16', '2026-03-16']);
}
{
  const p = 'nh-scr-22b1-plaintiff-automatic-disclosure-30-days';
  const d = 'nh-scr-22b2-defendant-automatic-disclosure-60-days';
  check('the automatic-disclosure limbs are 30 and 60 and run from DIFFERENT filings',
    [seed.rules.find(r => r.rule_id === p).count.value,
     seed.rules.find(r => r.rule_id === d).count.value,
     seed.rules.find(r => r.rule_id === p).trigger_event ===
       seed.rules.find(r => r.rule_id === d).trigger_event],
    [30, 60, false]);
  check('off one Answer filed 10 March they are a month apart',
    [dateOf(compute(p, '2026-03-10')), dateOf(compute(d, '2026-03-10'))],
    ['2026-04-09', '2026-05-11']);
}

// ── Admissions: a plain thirty, not a later_of ───────────────────────────
{
  const rid = 'nh-scr-28a1-admissions-response-30-days';
  const rule = seed.rules.find(r => r.rule_id === rid);
  check('the admissions row is a single-trigger plain period',
    [typeof rule.trigger_event, rule.count.value, rule.count.unit],
    ['string', 30, 'calendar_days']);
  check('it answers from ONE date, where a floor state would refuse INCOMPLETE_TRIGGERS',
    codeOf(compute(rid, '2026-03-10')), 'OK:2026-04-09');
  check('and the note records that the protection sits on the REQUESTING party instead',
    /AFTER 30 DAYS AFTER the date the defendant is served/.test(rule.authority.note), true);
}

// ── Refusals ─────────────────────────────────────────────────────────────
check('a 2027 trigger refuses -- the calendar is not generated forward',
  codeOf(compute(ANSWER, '2027-03-01')), 'NOT_PROVISIONED');
check('a trigger before the 1 October 2013 adoption refuses',
  codeOf(compute(ANSWER, '2013-09-30')), 'NO_RULE_IN_FORCE');
check('an unseeded New Hampshire event does not fall through to another rule',
  codeOf(engine.computeDeadline({
    jurisdiction: 'nh', domain: 'civil-litigation', trigger_event: 'service_of_request_for_admission_deadline_for_signatures',
    trigger_date: '2026-03-10', rules: seed.rules, calendars: calendars, as_of: '2026-03-10'
  })), 'NO_MATCHING_RULE');

// ── The coverage disclosure ──────────────────────────────────────────────
const cov = engine.JURISDICTION_COVERAGE.nh;
check('New Hampshire discloses an incomplete calendar whose error direction is EARLY',
  [!!cov, cov.complete, cov.direction], [true, false, 'early']);
check('the disclosure names the omitted day, the exact date, and the statute that dates it',
  [/biennial election/i.test(cov.detail), /3 NOVEMBER 2026/.test(cov.detail),
   /RSA 653:7/.test(cov.detail), /never defines/i.test(cov.detail)],
  [true, true, true, true]);
check('and it states why 3 July does not roll here',
  [/SUNDAY RULE ONLY/.test(cov.detail), /no Saturday limb/i.test(cov.detail)], [true, true]);
check('and it records the two periods dropped for want of an effective date',
  [/13A/.test(cov.detail), /summary-judgment objection/i.test(cov.detail)], [true, true]);
check('and it records that the published rules carry no amendment history',
  /no amendment history/i.test(cov.detail), true);
check('the summary warns about the missing extension rather than leaving it to be discovered',
  /NO mailed-service extension/i.test(cov.summary), true);

// ── Nothing else moved ───────────────────────────────────────────────────
check('the coverage table gained nh and nothing else',
  Object.keys(engine.JURISDICTION_COVERAGE).sort(),
  ['al', 'ar', 'fl', 'hi', 'id', 'ks', 'ma', 'md', 'mn', 'mo', 'ms', 'ne', 'nh', 'nm', 'nv', 'ut', 'va', 'wi']);
check('New Hampshire adds no service-completion standard',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);
check('and no other computation standard lost its short-period threshold',
  [engine.COMPUTATION_STANDARDS.hi_hrcp_6.short_period_exclusion_days,
   engine.COMPUTATION_STANDARDS.ne_25_2221.short_period_exclusion_days],
  [7, undefined]);

console.log((fail ? 'FAIL ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
