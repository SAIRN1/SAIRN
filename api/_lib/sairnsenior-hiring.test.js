// SAIRNsenior hiring funnel, driven verbatim from sairnsenior.html.
//
// Competitive-gap audit A5. The audit records applicant tracking as BASELINE
// in this vertical -- native in both AxisCare and Aaniie at Tier A -- and names
// caregiver turnover as "the market's defining operational problem". Verified
// absent before building: `applicant` 0, `recruit` 0, `hiring` 0, `candidate`
// 0, `interview` 0.
//
// WHY THE LOGIC LIVES IN THE PAGE AND THE TEST COMES TO IT. SAIRNsenior is
// local-first (ld/st with a server hydrate) and the referral and training
// panels beside this one compute in-page. Moving one panel's arithmetic to the
// server would have made three panels in one app disagree about where a rate
// is computed. The drift risk that justifies a server module elsewhere is
// answered here by EXTRACTION: every function below is pulled out of the real
// file, so there is no second copy to drift from.
//
// THE ASSERTIONS THAT MATTER ARE THE ONES ABOUT NOT KNOWING YET:
//
//   * A hire made three weeks ago has NO ninety-day answer. It is `too_soon`,
//     excluded from the denominator, and reported separately. Counting it as
//     a failure would make a source look worse the more recently it was used.
//   * A hire rate is over DECIDED applicants only, or a source's rate would
//     fall every time a new person applied to it.
//   * A rate over an empty denominator is null -- never 0, never 100.
//   * A hire with no linked caregiver is `unlinked`, never matched by name.
//     Two caregivers can share a name and a wrong join would credit someone
//     else's work to the wrong source.

const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', '..', 'sairnsenior.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function balanced(start, open, close) {
  let i = src.indexOf(open, start), depth = 0;
  if (i < 0) throw new Error('no ' + open);
  for (; i < src.length; i++) {
    if (src[i] === open) depth++;
    else if (src[i] === close) { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced');
}
function fn(name) {
  const start = src.indexOf('function ' + name + '(');
  if (start < 0) throw new Error('not found: ' + name);
  return balanced(start, '{', '}');
}
function lit(name, open, close) {
  const start = src.indexOf('var ' + name + '=');
  if (start < 0) throw new Error('not found: var ' + name);
  return balanced(start, open, close) + ';';
}
function scalar(name) {
  const m = src.match(new RegExp('var ' + name + '=([^;]+);'));
  if (!m) throw new Error('not found: var ' + name);
  return 'var ' + name + '=' + m[1] + ';';
}

const API = new Function(
  lit('HR_STAGES', '[', ']') + '\n' + lit('HR_DECIDED', '{', '}') + '\n' + scalar('HR_RETENTION_DAYS') + '\n' +
  fn('hrSourceKey') + '\n' + fn('hrAddDays') + '\n' + fn('hrIsDate') + '\n' +
  fn('hrRetentionFor') + '\n' + fn('hrFunnel') + '\n' + fn('hrBySource') + '\n' +
  'return { HR_STAGES, HR_DECIDED, HR_RETENTION_DAYS, hrRetentionFor, hrFunnel, hrBySource, hrSourceKey, hrAddDays };'
)();

const TODAY = '2026-09-02';
const A = (o) => Object.assign({ id: 'x', name: 'N', source: 'Indeed', stage: 'applied', applied_on: '2026-01-01' }, o);
const V = (o) => Object.assign({ assigned_employee_id: 'C1', status: 'completed', scheduled_date: '2026-06-01' }, o);

// ── the shape ───────────────────────────────────────────────────────────
check('the pipeline has seven stages and three of them are terminal',
  [API.HR_STAGES.length, Object.keys(API.HR_DECIDED).sort()],
  [7, ['hired', 'rejected', 'withdrawn']]);
check('ninety days is the default window', API.HR_RETENTION_DAYS, 90);
check('the window is an argument, not a constant baked into the arithmetic',
  /function hrRetentionFor\(a,vis,today,windowDays\)/.test(src), true);

// ── retention ───────────────────────────────────────────────────────────
check('a completed visit on or after the mark is retention',
  API.hrRetentionFor(A({ stage: 'hired', hired_on: '2026-01-01', caregiver_id: 'C1' }), [V({ scheduled_date: '2026-04-01' })], TODAY, 90).status,
  'retained');
check('the mark is INCLUSIVE -- a visit exactly on hire+90 counts',
  API.hrRetentionFor(A({ stage: 'hired', hired_on: '2026-01-01', caregiver_id: 'C1' }), [V({ scheduled_date: API.hrAddDays('2026-01-01', 90) })], TODAY, 90).status,
  'retained');
check('and a visit one day before the mark does not',
  API.hrRetentionFor(A({ stage: 'hired', hired_on: '2026-01-01', caregiver_id: 'C1' }), [V({ scheduled_date: API.hrAddDays('2026-01-01', 89) })], TODAY, 90).status,
  'lapsed');
check('a hire too recent to measure is TOO SOON, not a failure, and says when it becomes measurable',
  [API.hrRetentionFor(A({ stage: 'hired', hired_on: '2026-08-20', caregiver_id: 'C1' }), [], TODAY, 90).status,
   API.hrRetentionFor(A({ stage: 'hired', hired_on: '2026-08-20', caregiver_id: 'C1' }), [], TODAY, 90).measurable_on],
  ['too_soon', '2026-11-18']);
check('the too-soon boundary flips on the day the window closes',
  [API.hrRetentionFor(A({ stage: 'hired', hired_on: '2026-06-05', caregiver_id: 'C1' }), [], TODAY, 90).status,
   API.hrRetentionFor(A({ stage: 'hired', hired_on: '2026-06-04', caregiver_id: 'C1' }), [], TODAY, 90).status],
  ['too_soon', 'lapsed']);
check('a hire with no caregiver linked is UNLINKED, never matched by name',
  API.hrRetentionFor(A({ stage: 'hired', hired_on: '2026-01-01' }), [V()], TODAY, 90).status, 'unlinked');
check('a hire with no hire date is unlinked too, and says which is missing',
  [API.hrRetentionFor(A({ stage: 'hired', caregiver_id: 'C1' }), [], TODAY, 90).status,
   API.hrRetentionFor(A({ stage: 'hired', caregiver_id: 'C1' }), [], TODAY, 90).reason],
  ['unlinked', 'no hire date recorded']);
check('another caregiver\'s completed work is never credited to this hire',
  API.hrRetentionFor(A({ stage: 'hired', hired_on: '2026-01-01', caregiver_id: 'C1' }), [V({ assigned_employee_id: 'C2' })], TODAY, 90).status,
  'lapsed');
check('a scheduled-but-not-completed visit is not evidence of retention',
  API.hrRetentionFor(A({ stage: 'hired', hired_on: '2026-01-01', caregiver_id: 'C1' }), [V({ status: 'scheduled' })], TODAY, 90).status,
  'lapsed');
check('an applicant who was never hired has no retention answer at all',
  API.hrRetentionFor(A({ stage: 'rejected' }), [], TODAY, 90).status, 'not_hired');
check('a shorter window is honoured rather than ignored',
  API.hrRetentionFor(A({ stage: 'hired', hired_on: '2026-08-20', caregiver_id: 'C1' }), [V({ scheduled_date: '2026-09-01' })], TODAY, 7).status,
  'retained');

// ── the funnel ──────────────────────────────────────────────────────────
check('stage counts are counts, and an unrecognised stage is counted separately rather than dropped',
  (() => { const f = API.hrFunnel([A({}), A({ stage: 'hired' }), A({ stage: 'ghosted' })]);
    return [f.total, f.counts.applied, f.counts.hired, f.unknown_stage]; })(),
  [3, 1, 1, 1]);

// ── per source ──────────────────────────────────────────────────────────
const LIST = [
  A({ id: '1', source: 'Indeed', stage: 'hired', hired_on: '2026-01-01', caregiver_id: 'C1' }),   // retained
  A({ id: '2', source: 'indeed ', stage: 'hired', hired_on: '2026-01-01', caregiver_id: 'C2' }),  // lapsed
  A({ id: '3', source: 'Indeed', stage: 'rejected' }),
  A({ id: '4', source: 'Indeed', stage: 'applied' }),                                            // pending
  A({ id: '5', source: 'Employee referral', stage: 'hired', hired_on: '2026-08-25', caregiver_id: 'C3' }), // too soon
  A({ id: '6', source: 'Employee referral', stage: 'hired', hired_on: '2026-01-01' }),            // unlinked
  A({ id: '7', source: '', stage: 'withdrawn' })
];
const VIS = [V({ assigned_employee_id: 'C1', scheduled_date: '2026-05-01' })];
const ROWS = API.hrBySource(LIST, VIS, TODAY, 90);

check('sources differing only by case and whitespace are ONE source, not two half-samples',
  ROWS.filter((r) => /indeed/i.test(r.source)).length, 1);
check('the hire rate is over DECIDED applicants -- the pending one is not in the denominator',
  (() => { const r = ROWS.find((x) => /indeed/i.test(x.source)); return [r.applicants, r.decided, r.pending, r.hired, r.hire_rate_of_decided]; })(),
  [4, 3, 1, 2, 66.7]);
check('retention is over MEASURABLE hires -- too_soon and unlinked are excluded from the denominator',
  (() => { const r = ROWS.find((x) => x.source === 'Employee referral');
    return [r.hired, r.too_soon, r.unlinked, r.measurable_retention, r.retention_rate]; })(),
  [2, 1, 1, 0, null]);
check('a source with nothing measurable reports null, never 0% and never 100%',
  ROWS.filter((r) => r.retention_rate === 0 || r.retention_rate === 100).map((r) => r.source), []);
check('an applicant with no source recorded is grouped and labelled rather than dropped',
  ROWS.some((r) => r.source === '(no source recorded)'), true);
check('every applicant lands in exactly one source row',
  ROWS.reduce((s, r) => s + r.applicants, 0), LIST.length);

// RANKING IS THE PRODUCT DECISION, so it is asserted directly: a source that
// sends volume and produces nobody who stays must not outrank one that sends
// few and produces caregivers who do.
{
  const ranked = API.hrBySource([
    A({ id: 'v1', source: 'Volume board', stage: 'hired', hired_on: '2026-01-01', caregiver_id: 'V1' }),
    A({ id: 'v2', source: 'Volume board', stage: 'applied' }),
    A({ id: 'v3', source: 'Volume board', stage: 'applied' }),
    A({ id: 'v4', source: 'Volume board', stage: 'applied' }),
    A({ id: 'q1', source: 'Word of mouth', stage: 'hired', hired_on: '2026-01-01', caregiver_id: 'Q1' }),
    A({ id: 'q2', source: 'Word of mouth', stage: 'hired', hired_on: '2026-01-01', caregiver_id: 'Q2' })
  ], [V({ assigned_employee_id: 'Q1', scheduled_date: '2026-05-01' }), V({ assigned_employee_id: 'Q2', scheduled_date: '2026-05-01' })], TODAY, 90);
  check('ranked by caregivers who stayed, not by applications', ranked.map((r) => r.source),
    ['Word of mouth', 'Volume board']);
  check('and the loser is reported honestly rather than hidden',
    ranked[1].retention_rate, 0);
}

// ── the page ────────────────────────────────────────────────────────────
check('the panel is wired into nav', /if\(id==='hiring'\)hrRender\(\);/.test(src), true);
check('and gated on the intake roles, matching the referral panel rather than management-only',
  /function hrRender\(\)\{\s*\r?\n\s*var ok=senIsBroadRead\(\);/.test(src), true);
check('a hire is refused at entry if it has no date, rather than stored and reported unlinked forever',
  /A hire needs the date it happened/.test(src), true);
check('the retention limit is stated to the user, not just in a comment',
  /whose visits were never marked completed reads as lapsed/.test(src), true);
check('sample size is printed beside every rate',
  (src.match(/\(&#?\w*'?\+r\.hired\+'\/'\+r\.decided\+'\)/) ? true :
    src.indexOf("'/'+r.decided+'") !== -1), true);
check('the resource is registered so the provisioning probe can see it',
  /'sen_applicants'/.test(fs.readFileSync(path.join(__dirname, '..', '_resources', 'sairnsenior.js'), 'utf8')), true);
{
  const sd = fs.readFileSync(path.join(__dirname, '..', 'sd-data.js'), 'utf8');
  check('the server branch knows the id column', /sen_applicants: 'applicant_id'/.test(sd), true);
  // A SINGLE TERNARY WAS CORRECT FOR TWO FILES AND SILENTLY WRONG FOR A THIRD:
  // a new resource would have been told to run the referrals schema. A map
  // goes stale loudly instead.
  // ASSERTING THE MAP EXISTS IS NOT ENOUGH AND THE NEGATIVE CONTROL PROVED IT:
  // reverting the refusal site to the old ternary while leaving the map
  // declared passed this file 32/32. The map has to be the thing actually
  // consulted, and no ternary may survive at that site -- the same
  // decorative-assertion trap as the trust-void guard placement.
  check('the setup-file map exists AND is what the refusal consults',
    [/SEN_REFERRAL_SETUP_FILE = \{[\s\S]*sen_applicants: 'sql\/sairnsenior_applicants_schema\.sql'/.test(sd),
     /const setupFile = SEN_REFERRAL_SETUP_FILE\[resource\];/.test(sd),
     /const setupFile = \(resource\.indexOf/.test(sd)],
    [true, true, false]);
  // Asserted on a real GRANT STATEMENT, not on the word "delete" -- the file's
  // own comment explains why no delete grant is here, and matching the prose
  // made this fail on its own explanation the first time it ran.
  check('the schema file exists and no grant statement in it confers delete',
    (() => { const s = fs.readFileSync(path.join(__dirname, '..', '..', 'sql', 'sairnsenior_applicants_schema.sql'), 'utf8');
      const grants = s.split(/\r?\n/).filter((l) => /^\s*grant\b/i.test(l));
      return [/create table if not exists public\.sen_applicants/.test(s),
        grants.some((l) => /\bdelete\b/i.test(l))]; })(),
    [true, false]);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
