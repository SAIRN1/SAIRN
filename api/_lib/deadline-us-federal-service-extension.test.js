// FEDERAL SERVICE-EXTENSION REGRESSION TEST -- Rule 4 service vs Rule 5 service.
//
// DELIBERATELY NARROW. This is not a federal suite; the federal rows have never
// had one, which is exactly how the defect below survived from the first seed
// on 2026-08-21 until 2026-08-27. It covers ONE question -- which rows may
// carry Rule 6(d)'s three days -- because that is the question that was got
// wrong, and a wrong answer here is LATE.
//
// THE DEFECT, for anyone reading this later: frcp-12a1Ai-answer-after-service
// and frcp-12a2-united-states-official-capacity both attached frcp_6d, with no
// reasoning recorded either way. Rule 6(d) adds three days only when "service is
// made under Rule 5(b)(2)(C), (D), or (F)". A summons and complaint are served
// under RULE 4; service on the United States attorney is service of process
// under RULE 4(i). Neither is a Rule 5 paper. Any caller supplying a mailed
// service method on those rows got a date THREE DAYS LATE -- the direction that
// loses a filing, and the opposite of every other disclosed gap in this engine.
//
// It was found while seeding Nevada, whose NRCP 6(d) is worded identically, and
// only because Minnesota's seed had already recorded the correct reading in
// terms: "the summons is served under Rule 4, not Rule 5."
//
// THE RULE THIS TEST ENCODES: the distinction is WHICH RULE EFFECTED SERVICE,
// not how important the pleading is. Run this before adding any federal row
// that carries a service_extension.
//
// Run: node api/_lib/deadline-us-federal-service-extension.test.js
'use strict';

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_us_federal.json'), 'utf8'));
const disc = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_us_federal_discovery.json'), 'utf8'));
const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_2027_2031.json'), 'utf8'));

const rules = seed.rules.concat(disc.rules);
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

function ruleOf(id) {
  const r = rules.find(x => x.rule_id === id);
  if (!r) throw new Error('no such rule: ' + id);
  return r;
}
function added(id, triggerDate, method) {
  const r = ruleOf(id);
  const ev = typeof r.trigger_event === 'string' ? r.trigger_event : r.trigger_event.id;
  const res = engine.computeDeadline({
    jurisdiction: 'us-federal', domain: r.domain, trigger_event: ev,
    trigger_date: triggerDate, service_method: method,
    rules: rules, calendars: calendars, as_of: triggerDate
  });
  if (!res.ok) return 'REFUSED:' + res.code;
  return [res.due_date, res.service_extension ? res.service_extension.days_added : 0];
}

// ── RULE 4 SERVICE: the extension must NOT be attached, and must NOT apply ──
const RULE_4_ROWS = [
  'frcp-12a1Ai-answer-after-service',
  'frcp-12a2-united-states-official-capacity',
  'frcp-12a3-us-officer-individual-capacity'
];
for (const id of RULE_4_ROWS) {
  check('no service_extension on ' + id + ' (Rule 4 service)', !!ruleOf(id).service_extension, false);
  check('and its note says why -- an unexplained gap is how this defect survived',
    (ruleOf(id).authority.note || '').length > 100, true);
}

// The behaviour, not just the field. 1 June 2027 + 21 = 22 June, a Tuesday.
check('answer + mail adds NOTHING (was 2027-06-25, three days LATE)',
  added('frcp-12a1Ai-answer-after-service', '2027-06-01', 'mail'), ['2027-06-22', 0]);
check('answer with no method is unchanged by the fix',
  added('frcp-12a1Ai-answer-after-service', '2027-06-01', undefined), ['2027-06-22', 0]);
// 1 June 2027 + 60 = 31 July, a Saturday, rolls to Monday 2 August.
check('US attorney + mail adds NOTHING, and Rule 4(i)(1)(A)(ii) expressly allows mailing',
  added('frcp-12a2-united-states-official-capacity', '2027-06-01', 'mail'), ['2027-08-02', 0]);

// ── RULE 5 SERVICE: the extension must still be attached and still apply ────
// This half exists so the fix cannot be over-applied. Removing these would be
// the mirror-image error, reporting EARLY.
const RULE_5_ROWS = [
  'frcp-12a1B-counterclaim-crossclaim',
  'frcp-33b2-interrogatory-responses',
  'frcp-34b2A-production-responses',
  'frcp-36a3-admission-responses'
];
for (const id of RULE_5_ROWS) {
  check('service_extension REMAINS on ' + id + ' (Rule 5 service)', !!ruleOf(id).service_extension, true);
}
check('counterclaim + mail still adds three',
  added('frcp-12a1B-counterclaim-crossclaim', '2027-06-01', 'mail'), ['2027-06-25', 3]);
check('counterclaim with no method adds nothing',
  added('frcp-12a1B-counterclaim-crossclaim', '2027-06-01', undefined), ['2027-06-22', 0]);
// 1 June 2027 + 30 = 1 July; +3 = 4 July, Independence Day (a Sunday in 2027,
// observed Monday 5 July on the federal calendar), so it rolls again.
check('interrogatories + mail adds three and rolls off the observed holiday',
  added('frcp-33b2-interrogatory-responses', '2027-06-01', 'mail'), ['2027-07-06', 3]);

// ── The invariant, stated once ─────────────────────────────────────────────
// Every federal row that carries an extension must run from a Rule 5 paper.
// If a future row breaks this, it fails here rather than in front of a user.
{
  const RULE_4_TRIGGERS = /summons|complaint|process|united_states_attorney|officer_or_employee|waiver/i;
  const offenders = rules
    .filter(r => r.service_extension)
    .filter(r => {
      const t = r.trigger_event;
      const names = typeof t === 'string'
        ? [t]
        : [t.id || ''].concat(t.events || [], (t.limbs || []).map(L => L.event || ''));
      return names.some(n => RULE_4_TRIGGERS.test(n));
    })
    .map(r => r.rule_id);
  check('NO federal row carries an extension on a Rule 4 / process trigger', offenders, []);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
process.exit(fail ? 1 : 0);
