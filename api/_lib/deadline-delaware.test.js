// Delaware Superior Court deadline rows -- isolated verification against the
// REAL engine and the REAL seed/calendar JSON on disk, not a scratch copy.
//
// Six things would be wrong if carried from a neighbour:
//
//   - THE COURT IS PART OF THE JURISDICTION. Del. Ct. Ch. R. 6 is a DIFFERENT
//     computation on the same subject -- different rollover basis, a
//     legal-holiday definition with no Chief Justice limb, backward periods
//     addressed expressly, an hours unit -- and the two agree only on the
//     11-day threshold. Chancery is not seeded and these rows must never be
//     used for one. Asserted through the coverage entry, which leads with it.
//   - ELEVEN, NOT SEVEN. Five of the ten rows are TEN-day periods, so Rule
//     6(a)'s intermediate-day exclusion fires on half the seed. A 7 copied
//     from NJ, NC, WA, MA, MO or SC computes those five as straight calendar
//     days and reports them EARLY.
//   - THE GENERAL ELECTION DAY IS CARRIED, where New Hampshire's was omitted.
//     Delaware's statute and its constitution use the SAME term one reference
//     apart, so the date is a citation rather than a reading. Probed as a
//     positive: a period landing on 3 November 2026 must roll.
//   - SUSSEX COUNTY RETURN DAY IS NOT. County-scoped AND a half day beginning
//     at noon, so carrying it statewide would report LATE. Probed as a
//     negative: a period landing on 5 November 2026 must NOT roll.
//   - RULES 33 AND 34 CARRY A DEFENDANT ELECTION AND RULE 36 DOES NOT.
//     Asserted as a FIELD -- no row is a resolve_periods -- because copying a
//     45-day floor onto the self-executing Rule 36 would tell a defendant a
//     matter is still open when it has already been admitted.
//   - RULE 6(e) IS MAIL-ONLY AND IS NOT AN EXCLUSIVITY RULE. No row carries
//     requires_exclusive, and supplying service_methods must change nothing --
//     the check exists because Utah and Florida were both live when this was
//     written and both DO carry one.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_delaware.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_delaware.json'), 'utf8'));

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
    jurisdiction: 'de', domain: rule.domain, trigger_event: ev,
    trigger_date: triggerDate, rules: seed.rules, calendars: calendars, as_of: triggerDate
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : 'REFUSED:' + r.code);

const ANSWER = 'de-sccr-12a-answer-after-service-20-days';
const APPEAR = 'de-sccr-12a-answer-after-appearance-20-days';
const ROGS = 'de-sccr-33a-interrogatory-answers-30-days';
const PROD = 'de-sccr-34b-production-response-30-days';
const ADMIT = 'de-sccr-36a-admissions-response-30-days';
const NEWTRIAL = 'de-sccr-59b-new-trial-after-judgment-10-days';
const VERDICT = 'de-sccr-59b-new-trial-after-verdict-10-days';
const REPLY = 'de-sccr-59b-reply-affidavits-10-days';

// ── The seed's own shape ──────────────────────────────────────────────────
check('10 rules seeded', seed.rules.length, 10);
check('every row is Delaware civil litigation',
  [...new Set(seed.rules.map(r => r.jurisdiction + '/' + r.domain))], ['de/civil-litigation']);
check('every row uses the Superior Court standard, and the court is in its name',
  [...new Set(seed.rules.map(r => r.computation))], ['de_super_ct_civ_r_6a']);
check('every trigger is unique -- no two rows can match one event',
  seed.rules.length, new Set(seed.rules.map(r => JSON.stringify(r.trigger_event))).size);
check('every row carries a citation, a quote and a retrieval date',
  seed.rules.filter(r => !r.authority || !r.authority.citation || !r.authority.quote || !r.authority.retrieved_at)
    .map(r => r.rule_id), []);
check('NO row is a resolve_periods -- Delaware has no floor anywhere',
  seed.rules.filter(r => typeof r.trigger_event !== 'string').map(r => r.rule_id), []);
check('no backward row is seeded',
  seed.rules.filter(r => (r.count || {}).direction === 'backward').map(r => r.rule_id), []);

// ── The standard ─────────────────────────────────────────────────────────
const std = engine.COMPUTATION_STANDARDS.de_super_ct_civ_r_6a;
check('the standard exists and names the court', std.label, 'Del. Super. Ct. Civ. R. 6(a)');
check('ELEVEN, not seven -- the number half this seed depends on',
  std.short_period_exclusion_days, 11);
check('NO weekend_days declaration -- Rule 6(a) names both weekend days itself',
  std.weekend_days, undefined);
check('no per-direction exclusion flag -- Rule 6(a) does not address backward periods',
  std.short_period_exclusion_directions, undefined);
check('every subdivision suffix is empty rather than invented',
  [std.base_period_suffix, std.months_years_suffix, std.rollover_suffix_forward, std.rollover_suffix_backward],
  ['', '', '', '']);

// ── The dates. Hand-computed from the rule first, then asserted ──────────
// 1 June 2026 is a Monday. +20 = Sunday 21 June, which rolls to Monday the 22nd.
check('20-day answer from 1 June lands on Sunday and rolls to Monday', dateOf(compute(ANSWER, '2026-06-01')), '2026-06-22');
check('the appearance row is a separate trigger with the same count',
  dateOf(compute(APPEAR, '2026-06-01')), '2026-06-22');
// +30 = Wednesday 1 July, no roll.
check('30-day interrogatory answer from 1 June', dateOf(compute(ROGS, '2026-06-01')), '2026-07-01');
check('production and admissions carry the same 30 days',
  [dateOf(compute(PROD, '2026-06-01')), dateOf(compute(ADMIT, '2026-06-01'))], ['2026-07-01', '2026-07-01']);

// THE ELEVEN-DAY EXCLUSION, which is the whole reason the threshold matters.
// 1 June + 10 days EXCLUDING intermediate weekends = Monday 15 June:
// Jun 2,3,4,5 = 4 days, weekend skipped, Jun 8-12 = 9, Jun 15 = 10.
// Straight calendar counting would give Thursday 11 June -- four days earlier.
check('a TEN-day period excludes intermediate weekends, landing on 15 June',
  dateOf(compute(NEWTRIAL, '2026-06-01')), '2026-06-15');
check('the conditional rendition limb computes identically from its own trigger',
  dateOf(compute(VERDICT, '2026-06-01')), '2026-06-15');
check('and a THIRTY-day period does not exclude them -- the threshold is a boundary, not a mode',
  dateOf(compute(ROGS, '2026-06-01')), '2026-07-01');

// ── The mail extension ───────────────────────────────────────────────────
// 30 + 3 added to the period = Saturday 4 July, which rolls through Sunday to
// Monday 6 July. Note it does NOT stop on Friday 3 July, which is itself a
// holiday -- the roll walks past both.
check('mail adds three days to the period, and the lengthened end then rolls',
  dateOf(compute(ROGS, '2026-06-01', { service_method: 'mail' })), '2026-07-06');
check('the extension applies to the 10-day response rows too',
  dateOf(compute(REPLY, '2026-06-01', { service_method: 'mail' })), '2026-06-18');
check('electronic service adds NOTHING -- Rule 6(e) is mail-only',
  dateOf(compute(ROGS, '2026-06-01', { service_method: 'email' })), '2026-07-01');
check('nor does hand delivery or facsimile',
  ['hand_delivery', 'facsimile', 'other_consented_means'].map(m => dateOf(compute(ROGS, '2026-06-01', { service_method: m }))),
  ['2026-07-01', '2026-07-01', '2026-07-01']);
check('NO extension on the answer-to-process row -- deliberately omitted while the federal question is open',
  dateOf(compute(ANSWER, '2026-06-01', { service_method: 'mail' })), '2026-06-22');
check('nor on the new-trial row, whose period runs from entry of judgment rather than from service',
  dateOf(compute(NEWTRIAL, '2026-06-01', { service_method: 'mail' })), '2026-06-15');
check('exactly six of the ten rows carry a service extension',
  seed.rules.filter(r => r.service_extension).length, 6);
check('and every one of them is the mail-only Rule 6(e) standard',
  [...new Set(seed.rules.filter(r => r.service_extension).map(r => r.service_extension.standard))],
  ['de_super_ct_civ_r_6e']);

// EXCLUSIVITY: Utah and Florida both carry requires_exclusive and both were
// live when this was written. Delaware's rule says "service is by mail" with
// no "only" or "exclusively", so supplying the full set must change nothing.
check('no row declares requires_exclusive',
  seed.rules.filter(r => (r.service_extension || {}).requires_exclusive).map(r => r.rule_id), []);
check('supplying service_methods does not change a Delaware date',
  [dateOf(compute(ROGS, '2026-06-01', { service_method: 'mail', service_methods: ['mail'] })),
   dateOf(compute(ROGS, '2026-06-01', { service_method: 'mail', service_methods: ['mail', 'email'] }))],
  ['2026-07-06', '2026-07-06']);

// ── The calendar ─────────────────────────────────────────────────────────
const dates2026 = cal.holiday_calendars.find(c => c.year === 2026).dates.map(d => d.date);
check('twelve dates for 2026', dates2026.length, 12);
check('only 2026 is provisioned', cal.holiday_calendars.map(c => c.year), [2026]);
check('Saturdays are NOT enumerated, although sec. 501(a)(11) makes them holidays',
  dates2026.filter(d => engine.dayOfWeek(d) === 6), []);

// INDEPENDENCE DAY IS OBSERVED ON THE FRIDAY. 4 July 2026 is a Saturday and
// sec. 501(b) shifts a Saturday-falling holiday to the preceding Friday.
check('Friday 3 July 2026 is carried as the observed Independence Day', dates2026.includes('2026-07-03'), true);
check('and 4 July itself is not separately enumerated', dates2026.includes('2026-07-04'), false);
// A 30-day period from 3 June lands on Friday 3 July, a holiday, and must roll
// past it, past Saturday and past Sunday to Monday 6 July.
check('a period landing on 3 July rolls past the observed holiday and the weekend',
  dateOf(compute(ROGS, '2026-06-03')), '2026-07-06');

// THE GENERAL ELECTION DAY IS CARRIED -- the opposite call to New Hampshire's,
// and the reason is that Del. Const. art. V sec. 1 fixes the date using the
// same term the holiday statute uses.
check('Tuesday 3 November 2026 is carried as General Election Day', dates2026.includes('2026-11-03'), true);
check('a period landing on 3 November rolls to the 4th',
  dateOf(compute(ROGS, '2026-10-04')), '2026-11-04');

// SUSSEX COUNTY RETURN DAY IS NOT -- probed as a negative, because carrying a
// county-scoped half day statewide would report LATE.
check('Thursday 5 November 2026 is NOT carried', dates2026.includes('2026-11-05'), false);
check('a period landing on 5 November does NOT roll',
  dateOf(compute(ROGS, '2026-10-06')), '2026-11-05');

check('the calendar refuses a year it does not hold rather than deriving one',
  dateOf(compute(ROGS, '2027-06-01')), 'REFUSED:NOT_PROVISIONED');

// ── Effective dates come from each rule's own amendment history ──────────
check('a pre-1991 trigger refuses on effective_from',
  dateOf(compute(ADMIT, '1990-06-01')), 'REFUSED:NO_RULE_IN_FORCE');
check('Rule 34 carries a LATER effective date than Rule 33 despite an identical period',
  [seed.rules.find(r => r.rule_id === PROD).effective_from,
   seed.rules.find(r => r.rule_id === ROGS).effective_from],
  ['2019-08-01', '1997-11-12']);
check('no row invents an effective_to',
  seed.rules.filter(r => r.effective_to !== null).map(r => r.rule_id), []);

// ── Coverage, and it leads with scope ────────────────────────────────────
const cov = engine.JURISDICTION_COVERAGE.de;
check('Delaware declares a coverage entry', [!!cov, cov.complete, cov.direction], [true, false, 'early']);
check('the summary leads with SUPERIOR COURT ONLY', /^SUPERIOR COURT ONLY/.test(cov.summary), true);
check('and the detail names Chancery explicitly', /Ct\. Ch\. R\. 6/.test(cov.detail), true);
check('the Prothonotary limb is disclosed', /Prothonotary/.test(cov.detail), true);
check('Sussex Return Day is disclosed as omitted', /Sussex/.test(cov.detail), true);
check('and the entry records that the election day is NOT omitted',
  /General Election day is CARRIED|GENERAL ELECTION DAY IS CARRIED/.test(cov.detail), true);
check('a real computation carries the disclosure',
  [compute(ROGS, '2026-06-01').ok, !!compute(ROGS, '2026-06-01').coverage], [true, true]);

// ── Nothing else moved ───────────────────────────────────────────────────
check('Delaware adds no service-completion standard',
  Object.keys(engine.SERVICE_COMPLETION_STANDARDS), ['mo_rule_43_01_d']);
check('the Rule 6(e) extension standard is mail-only',
  ['mail', 'email', 'facsimile', 'hand_delivery', 'other_consented_means']
    .map(m => engine.SERVICE_EXTENSION_STANDARDS.de_super_ct_civ_r_6e.qualifies(m)),
  [true, false, false, false, false]);

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
