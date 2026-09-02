// service_extension.applies_to_limbs -- the whole mechanism, and every seeded
// row that depends on it, in BOTH directions.
//
// WHAT WAS WRONG. A service extension was declared per ROW and applied AFTER
// resolution, to whichever limb governed. Every multi-trigger row carrying one
// has a second limb no mail rule reaches: eleven run from service of the
// SUMMONS (Rule 4 service, where the extension rules are gated on Rule 5
// service) and Maryland's four run from `date_initial_pleading_is_required`,
// which is not a service event at all. Measured 2026-09-02 against the
// engine's own service_extension.state: FOURTEEN OF FIFTEEN added the days on
// that limb. Direction LATE, and ten of the fourteen are Rule 36 admissions
// rows where the matter is admitted unless answered.
//
// THE FIRST INSTRUMENT WAS WRONG AND THAT IS WORTH KEEPING. A probe that
// compared dates with and without the method reported Hawaii as unaffected. It
// was a collision: 45 days from 1 July lands on Saturday 15 August, and
// add_to_period_then_roll gives Monday 17 August either way. The field that
// says what the engine DID cannot be fooled by arithmetic, so every assertion
// here reads `state` rather than inferring from a date.
//
// EVERY SCOPING DECLARATION BELOW WAS READ FROM THE RULE, NOT INFERRED FROM
// THE LIMB'S NAME. The nine jurisdictions reach the same answer by three
// different routes, which is why each had to be read:
//
//   EXPRESS SUBSECTION CITATION
//     Alabama    Ala. R. Civ. P. 6(d)      "service is made under Rule
//                                           5(b)(2)(C) (by mail) or (E)"
//     Montana    Mont. R. Civ. P. 6(d)     "Rule 5(b)(2)(C), (D), or (E), or (F)"
//     Nebraska   Neb. Ct. R. Pldg. 6-1106(c) "under 6-1105(b)(3)(C)"; 6-1105 is
//                                           "Serving and filing pleadings and
//                                            other documents"
//     New Mexico Rule 1-006(C) NMRA        "under Rule 1-005(C)(1)(e) NMRA";
//                                           1-005 is service of pleadings and
//                                           other papers, 1-004 is process
//   "A NOTICE OR OTHER PAPER" -- Rule 5 vocabulary, no subsection named
//     Hawaii     Haw. R. Civ. P. 6(e)
//     Maryland   Md. Rule 1-203(c)         "after service upon the party of a
//                                           notice or other paper"
//     Wisconsin  Wis. Stat. 801.15(5)
//   THE SAME, PLUS AN EXPRESS RULE 4 CARVE-OUT IN THE RULE'S OWN TEXT
//     Arkansas   Ark. R. Civ. P. 6(d)      "shall not extend the time in which
//                                           the defendant must file an answer
//                                           ... in accordance with Rule 4"
//     Mississippi Miss. R. Civ. P. 6(e)    "This subdivision does not apply to
//                                           responses to service of summons
//                                           under Rule 4."
//
// Mississippi's carve-out was already quoted verbatim in its own standard's
// comment in deadline-engine.js while the row extended on exactly that limb.
// That one was never a reading.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');
const calendars = {};
for (const f of fs.readdirSync(SQL).filter(f => /^sairnlaw_deadline_calendars_.*\.json$/.test(f))) {
  const d = JSON.parse(fs.readFileSync(path.join(SQL, f), 'utf8'));
  for (const row of d.holiday_calendars) {
    calendars[row.jurisdiction] = calendars[row.jurisdiction] || {};
    calendars[row.jurisdiction][String(row.year)] = row.dates;
  }
}
let rules = [];
for (const f of fs.readdirSync(SQL).filter(f => /^sairnlaw_deadline_seed_.*\.json$/.test(f))) {
  rules = rules.concat(JSON.parse(fs.readFileSync(path.join(SQL, f), 'utf8')).rules || []);
}

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

const multi = rules.filter(r => typeof r.trigger_event === 'object' && r.trigger_event.resolve_periods && r.service_extension);

function compute(rule, dates, method) {
  return engine.computeDeadline({
    jurisdiction: rule.jurisdiction, domain: rule.domain, trigger_event: rule.trigger_event.id,
    trigger_date: Object.values(dates)[0], trigger_dates: dates,
    rules: rules, calendars: calendars, as_of: '2026-01-01',
    service_method: method, service_methods: method ? [method] : undefined
  });
}
function drive(rule, whichGoverns) {
  const limbs = rule.trigger_event.limbs;
  const dates = {};
  // The paper-service limb is limb 0 in every seeded row; give the OTHER limb
  // a trigger far enough away that the intended one certainly governs.
  if (whichGoverns === 0) { dates[limbs[0].event] = '2026-07-01'; dates[limbs[1].event] = '2026-03-01'; }
  else { dates[limbs[0].event] = '2026-06-01'; dates[limbs[1].event] = '2026-07-01'; }
  const method = (rule.service_extension.applies_when || ['mail'])[0];
  const out = compute(rule, dates, method);
  return { out: out, expectedGoverning: limbs[whichGoverns].event };
}

// ── the corpus itself ───────────────────────────────────────────────────
check('sixteen multi-trigger rows carry a service extension', multi.length, 16);
check('and they span nine jurisdictions',
  [...new Set(multi.map(r => r.jurisdiction))].sort(),
  ['al', 'ar', 'hi', 'md', 'mn', 'mo', 'ms', 'mt', 'ne', 'nm', 'wi'].filter(j => multi.some(r => r.jurisdiction === j)));
check('EVERY one declares applies_to_limbs -- an undeclared row is refused, so a gap here is not silent',
  multi.filter(r => !Array.isArray(r.service_extension.applies_to_limbs)).map(r => r.rule_id), []);
check('none scopes the extension to ALL its limbs -- that would be the old behaviour spelled out',
  multi.filter(r => r.service_extension.applies_to_limbs.length >= r.trigger_event.limbs.length).map(r => r.rule_id), []);
check('and every declared limb is one the rule actually has',
  multi.filter(r => r.service_extension.applies_to_limbs
    .some(e => !r.trigger_event.limbs.some(l => l.event === e))).map(r => r.rule_id), []);

// ── BOTH DIRECTIONS, EVERY ROW ──────────────────────────────────────────
{
  const notReached = [], reached = [], wrongGoverning = [];
  for (const r of multi) {
    const a = drive(r, 1);
    if (!a.out.ok) { notReached.push(r.rule_id + ' REFUSED:' + a.out.code); continue; }
    const gov = (a.out.rule && a.out.rule.period_resolution) || null;
    if (a.out.service_extension.state !== 'not_applicable_to_governing_limb') {
      notReached.push(r.rule_id + ' -> ' + a.out.service_extension.state);
    }
    if (a.out.service_extension.governing_event !== a.expectedGoverning) {
      wrongGoverning.push(r.rule_id + ' governed by ' + a.out.service_extension.governing_event);
    }
    const b = drive(r, 0);
    if (!b.out.ok) { reached.push(r.rule_id + ' REFUSED:' + b.out.code); continue; }
    if (b.out.service_extension.state !== 'applied' || b.out.service_extension.days_added < 1) {
      reached.push(r.rule_id + ' -> ' + b.out.service_extension.state + '/' + b.out.service_extension.days_added);
    }
  }
  check('when the NON-service limb governs, no row adds a day -- this is the defect, closed', notReached, []);
  check('and the refusal names the limb that put it out of reach', wrongGoverning, []);
  check('when the PAPER-SERVICE limb governs, every row still adds its days -- coverage kept, not stripped', reached, []);
}

// ── the two states whose rules say it outright ──────────────────────────
{
  const ms = multi.find(r => r.rule_id === 'ms-36a-admissions-answer-later-of');
  const a = drive(ms, 1), b = drive(ms, 0);
  check('Mississippi adds nothing on the summons limb -- Rule 6(e) excludes it in its own final sentence',
    [a.out.service_extension.state, a.out.service_extension.days_added], ['not_applicable_to_governing_limb', 0]);
  check('and still adds three on the request limb', b.out.service_extension.days_added, 3);
  // Asserted against the STANDARD'S OWN comment block, not just anywhere in
  // the file, because the point is that Mississippi's carve-out was sitting
  // in this engine, quoted, while the row extended on exactly that limb.
  // Matching across the comment's line wrapping rather than on one line.
  {
    const eng = fs.readFileSync(path.join(__dirname, 'deadline-engine.js'), 'utf8');
    const decl = eng.indexOf('ms_r_civ_p_6_e: {');
    const blockStart = eng.lastIndexOf('// MISSISSIPPI', decl);
    const block = eng.slice(blockStart, decl);
    check('the carve-out this row was contradicting was already quoted in its own standard\'s comment',
      /does not apply to responses to\s*(?:\/\/\s*)?service of summons under\s*(?:\/\/\s*)?Rule 4/.test(block), true);
  }
}
{
  const ar = multi.find(r => r.rule_id === 'ar-rcp-36a-admission-response-defendant-later-of');
  check('Arkansas adds nothing on the summons limb -- its 6(d) proviso says so and its scope names Rule 5(b)(2)',
    drive(ar, 1).out.service_extension.state, 'not_applicable_to_governing_limb');
  check('and Arkansas still adds its three BUSINESS days on the request limb',
    [drive(ar, 0).out.service_extension.days_added, ar.service_extension.unit], [3, 'business_days']);
}
{
  const hi = multi.find(r => r.rule_id === 'hi-hrcp-36a-admissions-answer-later-of');
  check('Hawaii adds nothing on the summons limb -- "a notice or other paper" is Rule 5 vocabulary',
    drive(hi, 1).out.service_extension.state, 'not_applicable_to_governing_limb');
  check('and Hawaii still adds TWO, the only two on the platform, on the request limb',
    drive(hi, 0).out.service_extension.days_added, 2);
}
{
  const md = multi.filter(r => r.jurisdiction === 'md');
  check('all four Maryland rows scope away from date_initial_pleading_is_required, which is not a service event at all',
    md.every(r => r.service_extension.applies_to_limbs.indexOf('date_initial_pleading_is_required') === -1), true);
}

// ── the mechanism refuses rather than guessing ──────────────────────────
{
  const base = multi.find(r => r.rule_id === 'hi-hrcp-36a-admissions-answer-later-of');
  const stripped = JSON.parse(JSON.stringify(base));
  delete stripped.service_extension.applies_to_limbs;
  stripped.rule_id = 'zz-undeclared-probe';
  const dates = {};
  dates[stripped.trigger_event.limbs[0].event] = '2026-07-01';
  dates[stripped.trigger_event.limbs[1].event] = '2026-03-01';
  const out = engine.computeDeadline({
    jurisdiction: 'hi', domain: stripped.domain, trigger_event: stripped.trigger_event.id,
    trigger_date: '2026-07-01', trigger_dates: dates, rules: [stripped], calendars: calendars,
    as_of: '2026-01-01', service_method: 'mail'
  });
  check('a multi-trigger row with an extension and NO declared scope refuses, on the limb that would have earned the days',
    out.service_extension.state, 'refused_undeclared_limb_scope');
  check('and it adds nothing rather than falling back to the old behaviour', out.service_extension.days_added, 0);
  check('the date is still returned, unextended, so the caller is not left with nothing',
    out.ok, true);

  const typo = JSON.parse(JSON.stringify(base));
  typo.service_extension.applies_to_limbs = ['service_of_request_for_admissions'];  // trailing s
  typo.rule_id = 'zz-typo-probe';
  const out2 = engine.computeDeadline({
    jurisdiction: 'hi', domain: typo.domain, trigger_event: typo.trigger_event.id,
    trigger_date: '2026-07-01', trigger_dates: dates, rules: [typo], calendars: calendars,
    as_of: '2026-01-01', service_method: 'mail'
  });
  check('a MISSPELT limb name refuses too -- it would otherwise scope to nothing while looking deliberate',
    out2.service_extension.state, 'refused_undeclared_limb_scope');
  check('and the refusal names the bad entry rather than saying only that something is wrong',
    /service_of_request_for_admissions/.test(out2.service_extension.detail), true);
}
{
  // A single-trigger row has no limbs; declaring scope on one is malformed.
  const single = JSON.parse(JSON.stringify(rules.find(r => r.rule_id === 'de-sccr-33a-interrogatory-answers-30-days')));
  single.service_extension.applies_to_limbs = ['service_of_interrogatories'];
  single.rule_id = 'zz-single-probe';
  const out = engine.computeDeadline({
    jurisdiction: 'de', domain: single.domain, trigger_event: single.trigger_event,
    trigger_date: '2026-06-01', rules: [single], calendars: calendars, as_of: '2026-01-01',
    service_method: 'mail'
  });
  check('a SINGLE-trigger row that declares applies_to_limbs is refused as malformed',
    out.service_extension.state, 'refused_undeclared_limb_scope');
}

// ── single-trigger rows are untouched ───────────────────────────────────
{
  const de = rules.find(r => r.rule_id === 'de-sccr-33a-interrogatory-answers-30-days');
  const out = engine.computeDeadline({
    jurisdiction: 'de', domain: de.domain, trigger_event: de.trigger_event,
    trigger_date: '2026-06-01', rules: rules, calendars: calendars, as_of: '2026-01-01',
    service_method: 'mail'
  });
  check('an ordinary single-trigger row still extends exactly as before',
    [out.due_date, out.service_extension.state, out.service_extension.days_added],
    ['2026-07-06', 'applied', 3]);
  check('and no single-trigger row anywhere declares applies_to_limbs',
    rules.filter(r => typeof r.trigger_event === 'string' && r.service_extension &&
      r.service_extension.applies_to_limbs !== undefined).map(r => r.rule_id), []);
}

// ── the write-time guard ────────────────────────────────────────────────
// validateRulePayload is not exported, so these are SOURCE-PRESENCE checks and
// are labelled as such -- the same convention deadline-trigger-document.test.js
// uses for the same reason. The engine-side assertions above are the
// load-bearing ones; these exist so the write-time rejection cannot be deleted
// unnoticed, which matters here because nothing in that endpoint rejects
// unknown fields and a misspelt KEY would otherwise be stored happily.
{
  const ep = fs.readFileSync(path.join(__dirname, '..', 'legal-deadlines.js'), 'utf8');
  check('the endpoint refuses to STORE a multi-trigger row that does not declare its limb scope',
    /must declare service_extension\.applies_to_limbs/.test(ep), true);
  check('it refuses a limb name the rule does not have',
    /A misspelt entry would scope the extension to nothing while looking deliberate/.test(ep), true);
  check('it refuses the field on a single-trigger rule',
    /has no meaning on a single-trigger rule/.test(ep), true);
  check('and it refuses a declaration naming EVERY limb, which is the old behaviour written longhand',
    /which is the unscoped behaviour written out longhand/.test(ep), true);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
