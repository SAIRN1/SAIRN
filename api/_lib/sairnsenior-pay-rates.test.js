// SAIRNsenior caregiver pay rates and per-branch gross margin, driven verbatim
// from sairnsenior.html.
//
// Competitive-gap audit item B5 ("consolidated + per-branch P&L",
// Tier-B-defining). Verified absent before building, word-boundary rather than
// substring: `pay_rate` 0, `hourly_rate` 0, `wage` 0, `cost_of_care` 0,
// `labor_cost` 0, `gross_margin` 0. The 3 `payroll` and 2 `overhead` hits were
// SAIRNsenior's own B1 disclosure saying it holds none of them.
//
// THIS CLOSES A GAP THE APP DECLARED ON ITSELF. The Branches panel shipped
// earlier the same day printing "No cost, overhead or payroll data is held by
// this app, so no margin or profit figure is computed here -- the revenue half
// is real and the other half is absent rather than estimated." That was the
// right call with no cost data. This is the missing half.
//
// THE FIVE PROPERTIES THIS FILE EXISTS TO HOLD:
//
//   1. A VISIT IS COSTED AT THE WAGE IN FORCE ON THE DAY IT WAS WORKED, never
//      today's. Resolving against today would silently restate every
//      historical margin the next time anyone got a rise -- including margins
//      already reported to an owner or a lender.
//   2. A MISSING RATE IS COUNTED, NEVER TREATED AS FREE LABOUR. Cost missing
//      means cost understated means margin OVERSTATED, so the branch with the
//      worst record-keeping would look like the most profitable one. The
//      direction of the error is known, so the panel says "overstated" rather
//      than "uncertain".
//   3. AMBIGUITY REFUSES, as it does for a payer contract and an
//      authorisation. Costing a visit at a wage nobody chose puts a wrong
//      number straight into the margin.
//   4. BURDEN SITS ON THE RATE AND ZERO MEANS "NOT MODELLED". A W-2 aide
//      carries employer taxes and workers' comp; a 1099 contractor does not.
//      One agency-wide figure would be wrong for any agency running both.
//   5. THIS IS GROSS MARGIN AND NOT PROFIT, and the panel says so. Direct
//      labour is the only cost. Calling it a P&L would be the fabrication the
//      panel previously refused outright.

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
function scalar(name) {
  const m = src.match(new RegExp('var ' + name + '=([^;]+);'));
  if (!m) throw new Error('not found: var ' + name);
  return 'var ' + name + '=' + m[1] + ';';
}

const TODAY = '2026-09-02';

function build(world) {
  return new Function('W',
    scalar('BR_WINDOW_DAYS') + '\n' +
    'var clients=W.clients, caregivers=W.caregivers, visits=W.visits, claims=W.claims, branches=W.branches, payRates=W.payRates;\n' +
    'var H=function(s){return String(s==null?"":s);};\n' +
    // Stubbed so a break that switches the cost resolver to TODAY asserts
    // cleanly instead of throwing ReferenceError. A crashing negative control
    // undercounts itself -- same lesson as the unguarded .map() in the
    // authorisation suite.
    'var senLocalToday=function(){return "' + TODAY + '";};\n' +
    fn('hrAddDays') + '\n' + fn('hrIsDate') + '\n' + fn('hrSourceKey') + '\n' + fn('visitHours') + '\n' +
    fn('prInForce') + '\n' + fn('prResolveRate') + '\n' + fn('visitLabourCost') + '\n' +
    fn('brName') + '\n' + fn('brRollup') + '\n' +
    'return { prInForce, prResolveRate, visitLabourCost, brRollup };'
  )(world);
}
function world(o) {
  o = o || {};
  return {
    branches: () => o.branches || [],
    clients: () => o.clients || [],
    caregivers: () => o.caregivers || [],
    visits: () => o.visits || [],
    claims: () => o.claims || [],
    payRates: () => o.payRates || []
  };
}
// Two clocked hours on the given day, worked by the given employee.
function vis(emp, date, hours, clientId) {
  return { id: 'V' + emp + date, client_id: clientId || 'CL1', status: 'completed', scheduled_date: date,
    assigned_employee_id: emp,
    clock_in_at: date + 'T10:00:00.000Z',
    clock_out_at: date + 'T' + String(10 + hours).padStart(2, '0') + ':00:00.000Z' };
}
const RATE = { id: 'PR1', employee_id: 'EMP1', rate_per_hour: 20, burden_pct: 0,
  effective_on: '2026-01-01', term_on: '' };

// ── 1. the wage in force on the day the work was done ───────────────────
{
  // Paid 18/hr until the end of July, 22/hr from August. A visit worked in
  // July stays costed at 18 for as long as it exists.
  const R = [
    { id: 'P1', employee_id: 'EMP1', rate_per_hour: 18, effective_on: '2026-01-01', term_on: '2026-07-31' },
    { id: 'P2', employee_id: 'EMP1', rate_per_hour: 22, effective_on: '2026-08-01', term_on: '' }
  ];
  const { visitLabourCost, prResolveRate } = build(world({ payRates: R }));
  check('a July visit is costed at July\'s wage, not at the rise that followed',
    visitLabourCost(vis('EMP1', '2026-07-15', 2)).cost, 36);
  check('an August visit is costed at the new wage', visitLabourCost(vis('EMP1', '2026-08-15', 2)).cost, 44);
  check('the term date is inclusive at both ends',
    [prResolveRate('EMP1', '2026-07-31').rate_per_hour, prResolveRate('EMP1', '2026-08-01').rate_per_hour], [18, 22]);
  check('a date before any rate resolves to nothing, not to the earliest rate',
    prResolveRate('EMP1', '2025-12-31').status, 'none');
  // "has rates but none in force on that date" and "has no rates at all" are
  // different problems with different fixes, so they are different messages.
  check('and the refusal says the caregiver HAS rates on file rather than none, and how many',
    /2 pay rate\(s\) on file but none in force on 2025-12-31/.test(prResolveRate('EMP1', '2025-12-31').reason), true);
  check('a caregiver with nothing on file gets the other message',
    /No pay rate is on file for this caregiver/.test(prResolveRate('EMP9', '2026-08-20').reason), true);
}
{
  const { prInForce } = build(world());
  check('a rate with no effective date is never in force', prInForce({ effective_on: '' }, TODAY), false);
  // A present-but-unreadable end date must not be skipped as if blank -- that
  // would turn a superseded wage into an open-ended one and keep costing visits
  // at it forever. Same rule as pcInForce, same reason.
  check('a rate whose end date is unreadable is NOT treated as open-ended',
    prInForce({ effective_on: '2026-01-01', term_on: '31/07/2026' }, TODAY), false);
}

// ── 2. a missing rate is counted, never treated as free labour ──────────
{
  const { visitLabourCost } = build(world({ payRates: [RATE] }));
  const known = visitLabourCost(vis('EMP1', '2026-08-20', 2));
  const unknown = visitLabourCost(vis('EMP9', '2026-08-20', 2));
  check('a costed visit reports applied with the money', [known.status, known.cost], ['applied', 40]);
  // THE WHOLE POINT: cost zero and status none, so a caller can tell "this cost
  // nothing" from "this cost is not known". Collapsing those two is what makes
  // a badly-recorded branch look profitable.
  check('an uncosted visit reports cost 0 AND a status that says the cost is unknown',
    [unknown.status, unknown.cost, unknown.hours], ['none', 0, 2]);
  check('the hours are still real on an uncosted visit -- only the money is missing',
    unknown.hours, 2);
  check('a visit that was never clocked has no hours and therefore no cost',
    visitLabourCost({ assigned_employee_id: 'EMP1', scheduled_date: '2026-08-20' }).cost, 0);
}
{
  // One branch fully costed, one branch with a caregiver who has no rate. The
  // uncosted branch must not read as the more profitable one without saying so.
  const W = world({
    branches: [{ id: 'B1', name: 'Westlake', state: 'OH' }, { id: 'B2', name: 'Erie', state: 'PA' }],
    clients: [{ id: 'CL1', branch_id: 'B1' }, { id: 'CL2', branch_id: 'B2' }],
    visits: [vis('EMP1', '2026-08-20', 2, 'CL1'), vis('EMP9', '2026-08-20', 2, 'CL2')],
    claims: [
      { client_id: 'CL1', status: 'submitted', service_date: '2026-08-20', amount: 100 },
      { client_id: 'CL2', status: 'submitted', service_date: '2026-08-20', amount: 100 }
    ],
    payRates: [RATE]
  });
  const out = build(W).brRollup(TODAY, 30);
  const b1 = out.rows.find((r) => r.branch_id === 'B1');
  const b2 = out.rows.find((r) => r.branch_id === 'B2');
  check('the costed branch reports real labour cost and a real margin',
    [b1.labour_cost, b1.margin, b1.margin_pct, b1.uncosted_visits, b1.margin_overstated],
    [40, 60, 60, 0, false]);
  check('the uncosted branch reports a HIGHER margin and is flagged overstated for it',
    [b2.labour_cost, b2.margin, b2.uncosted_visits, b2.uncosted_hours, b2.margin_overstated],
    [0, 100, 1, 2, true]);
  check('the consolidated total is flagged overstated whenever any branch is',
    [out.totals.labour_cost, out.totals.margin, out.totals.uncosted_visits, out.totals.margin_overstated],
    [40, 160, 1, true]);
  check('the consolidated figures are the sum of the rows shown, so the total cannot disagree with the table',
    [out.rows.reduce((s, r) => s + r.labour_cost, 0), out.rows.reduce((s, r) => s + r.margin, 0)],
    [out.totals.labour_cost, out.totals.margin]);
}
{
  // A margin percentage over zero revenue is not 0% and not 100% -- it is not a
  // ratio. Rendering either would be inventing a result from an empty
  // denominator, the same rule the hiring panel's rates already follow.
  const out = build(world({
    branches: [{ id: 'B1', name: 'Westlake' }],
    clients: [{ id: 'CL1', branch_id: 'B1' }],
    visits: [vis('EMP1', '2026-08-20', 2, 'CL1')],
    claims: [],
    payRates: [RATE]
  })).brRollup(TODAY, 30);
  const b1 = out.rows.find((r) => r.branch_id === 'B1');
  check('a branch with cost and no revenue reports a NEGATIVE margin and a null percentage',
    [b1.margin, b1.margin_pct], [-40, null]);
  check('and the consolidated percentage is null too, not zero',
    out.totals.margin_pct, null);
}

// ── 3. ambiguity refuses ────────────────────────────────────────────────
{
  const R = [
    { id: 'P1', employee_id: 'EMP1', rate_per_hour: 18, effective_on: '2026-01-01', term_on: '' },
    { id: 'P2', employee_id: 'EMP1', rate_per_hour: 22, effective_on: '2026-06-01', term_on: '' }
  ];
  const { prResolveRate, visitLabourCost } = build(world({ payRates: R }));
  const r = prResolveRate('EMP1', '2026-08-20');
  check('two rates in force for one caregiver on one date do not resolve', r.status, 'ambiguous');
  check('no wage is carried on an ambiguous result -- not the newer, not the higher',
    [r.rate_per_hour, r.rate_id], [undefined, undefined]);
  check('both candidates are named so the overlap can be fixed',
    (r.candidates || []).map((c) => c.id).sort(), ['P1', 'P2']);
  check('the reason says a wrong number would go straight into the margin',
    /straight into the margin/.test(r.reason), true);
  check('an ambiguous rate leaves the visit UNCOSTED rather than picking one',
    visitLabourCost(vis('EMP1', '2026-08-20', 2)).status, 'ambiguous');
  const fixed = build(world({ payRates: [Object.assign({}, R[0], { term_on: '2026-05-31' }), R[1]] }))
    .prResolveRate('EMP1', '2026-08-20');
  check('ending one of them resolves it, as the message instructs',
    [fixed.status, fixed.rate_per_hour], ['applied', 22]);
}
{
  // Employee ids are compared case- and whitespace-insensitively on both sides,
  // because one side is typed into a roster and the other is stored on a visit.
  const { prResolveRate } = build(world({
    payRates: [{ id: 'P1', employee_id: ' Emp1 ', rate_per_hour: 20, effective_on: '2026-01-01' }]
  }));
  check('employee matching survives case and stray whitespace',
    prResolveRate('EMP1', '2026-08-20').rate_per_hour, 20);
  check('a visit with no caregiver is refused for that reason',
    /names no caregiver/.test(prResolveRate('', '2026-08-20').reason), true);
  check('a visit with no service date is refused for that reason',
    /no service date/.test(prResolveRate('EMP1', '').reason), true);
}

// ── 4. burden sits on the rate; zero means not modelled ─────────────────
{
  const { visitLabourCost } = build(world({
    payRates: [
      { id: 'W2', employee_id: 'EMP1', rate_per_hour: 20, burden_pct: 25, effective_on: '2026-01-01' },
      { id: 'C99', employee_id: 'EMP2', rate_per_hour: 20, burden_pct: 0, effective_on: '2026-01-01' }
    ]
  }));
  check('burden is applied on top of the wage, per worker',
    visitLabourCost(vis('EMP1', '2026-08-20', 2)).cost, 50);
  check('a worker with zero burden costs the wage alone -- 0 is allowed, not an error',
    visitLabourCost(vis('EMP2', '2026-08-20', 2)).cost, 40);
  check('the burden actually used is reported back, so a screen can show which figure it is',
    [visitLabourCost(vis('EMP1', '2026-08-20', 2)).burden_pct,
     visitLabourCost(vis('EMP2', '2026-08-20', 2)).burden_pct], [25, 0]);
  // A missing burden_pct is not a missing rate. It defaults to zero and the
  // visit is still costed -- refusing here would throw away a real wage over an
  // optional field.
  const noBurden = build(world({ payRates: [{ id: 'P1', employee_id: 'EMP1', rate_per_hour: 20, effective_on: '2026-01-01' }] }))
    .visitLabourCost(vis('EMP1', '2026-08-20', 2));
  check('an omitted burden defaults to zero and does not make the visit uncosted',
    [noBurden.status, noBurden.cost], ['applied', 40]);
}

// ── 5. gross margin, and the panel says what it is not ──────────────────
check('the panel states this is billed revenue minus direct labour only',
  /Gross margin is billed revenue minus direct labour only\.<\/strong>/.test(src), true);
check('the panel refuses the words profit and P&L outright',
  /not profit and not a P&amp;L<\/strong>/.test(src), true);
check('and lists what is excluded rather than leaving it to be assumed',
  /no rent, supervision, mileage, software, administration or insurance/.test(src), true);
check('the panel says labour is costed at the wage in force on the service date',
  /in force on the service date<\/strong>, never today/.test(src), true);
check('the overstated warning names the DIRECTION of the error, not just uncertainty',
  /is <strong>overstated<\/strong> &mdash; not merely uncertain/.test(src), true);
check('and the zero-burden case is disclosed as "not modelled", not as "no burden"',
  /Zero is allowed and means it is not modelled<\/strong>/.test(src), true);
check('the branch row marks an overstated margin rather than printing it plain',
  /r\.margin_overstated\?' <span class="badge bw"/.test(src), true);
// ANCHORED TO STATEMENT POSITION, not merely to the text existing. The first
// version matched `bits.push('Consolidated: ...` anywhere, so the negative
// control that disabled it with `if(false)` PASSED 76/76 -- the line was still
// in the file and no longer ran. Scrubber item 16 shape B: testing existence
// where the requirement is use.
check('the consolidated line is printed unconditionally, not merely present in the file',
  /\n\s*bits\.push\('Consolidated: '\+fmt\(out\.totals\.billed\)/.test(src), true);

// ── the panel exists and is reachable ───────────────────────────────────
['panel-payrates', 'prmodal', 'pr-tbody', 'pr-denied', 'pr-content', 'pr-conflicts',
 'pr-add-btn', 'pr-modal-title', 'pr-employee', 'pr-rate', 'pr-burden', 'pr-effective',
 'pr-term', 'pr-notes'].forEach((id) => {
  check('the DOM node #' + id + ' that the code reads actually exists', new RegExp('id="' + id + '"').test(src), true);
});
check('the panel is wired into nav', /if\(id==='payrates'\)prRender\(\);/.test(src), true);
check('the sidebar button exists and points at it', /id="sb-payrates" onclick="nav\('payrates'\)"/.test(src), true);
check('something on screen opens the modal', /onclick="openPrModal\(\)"/.test(src), true);
check('the branch table header carries a cell for each new column and the empty state spans them all',
  ['br-th-cost', 'br-th-margin', 'br-th-marginpct', 'br-th-uncosted'].every((i) => new RegExp('id="' + i + '"').test(src))
  && /colspan="11"/.test(src), true);
check('all five money columns are hidden from a non-manager, header and cells alike',
  /\['br-th-revenue','br-th-cost','br-th-margin','br-th-marginpct','br-th-uncosted'\]\.forEach/.test(src) &&
  (src.match(/<td style="display:none"><\/td>/g) || []).length >= 5, true);

// ── the rate is keyed to what a visit actually carries ──────────────────
// If this is ever keyed to a sen_caregivers row id instead, every join fails
// and every visit silently costs nothing -- which reads as a perfect margin.
check('the cost resolver reads assigned_employee_id, the field a visit stores',
  /prResolveRate\(v&&v\.assigned_employee_id,v&&v\.scheduled_date\)/.test(src), true);
check('the modal picks the caregiver from the auth roster rather than free text',
  /var roster=_senRoster\|\|\[\];/.test(src) && /<select id="pr-employee">/.test(src), true);

// ── sync discipline, same as the two builds before it ───────────────────
check('hydration replaces the local row rather than only adding unseen ones',
  /function senHydratePayRates\(\)/.test(src) &&
  /JSON\.stringify\(byId\[r\.id\]\)!==JSON\.stringify\(r\)/.test(src), true);
check('Branches hydrates pay rates before drawing a margin, so a fresh device does not read margin equal to revenue',
  /if\(isMgmt\)senHydratePayRates\(\)\.then\(function\(changed\)\{if\(changed\)brPaint\(\);\}\);/.test(src), true);
check('saving repaints without hydrating -- a hydrate racing the write would undo the edit',
  /closePrModal\(\);prPaint\(\);/.test(src), true);

// ── the browser refusals ────────────────────────────────────────────────
// ASSERTED ON THE EXTRACTED savePayRate BODY, not on the file. savePayerContract
// contains the SAME guards with the SAME wording -- `if(!(rate>0)){toast(`, "An
// effective date is required", "The end date is before the start date" -- so a
// file-wide match would have passed on the contract build's code while this
// function had none of it. The negative control that removed savePayRate's zero
// guard proved it: 2 matches, break not applied, would have read as caught.
{
  const save = fn('savePayRate');
  check('the browser refuses a zero or negative wage', /if\(!\(rate>0\)\)\{toast\(/.test(save), true);
  check('the browser refuses a burden outside 0..99.99 and allows zero',
    /if\(!isFinite\(burden\)\|\|burden<0\|\|burden>=100\)\{toast\(/.test(save), true);
  check('the browser requires an effective date and refuses an inverted period',
    /An effective date is required/.test(save) && /The end date is before the start date/.test(save), true);
  check('the browser refuses a rate keyed to nobody',
    /a rate keyed to nobody costs nothing and looks like it costs nothing/.test(save), true);
}

// ── the server refusals ─────────────────────────────────────────────────
{
  const api = fs.readFileSync(path.join(__dirname, '..', 'sd-data.js'), 'utf8');
  check('the gate is management-only on BOTH verbs -- narrower than the authorisation gate beside it',
    /Only management can view or manage pay rates/.test(api) &&
    /resource === 'sen_pay_rates' && \(action === 'read' \|\| action === 'write'\)/.test(api), true);
  // ANCHORED TO prProblems. sen_payer_contracts pushes the IDENTICAL strings
  // "rate_per_hour must be greater than zero", "effective_on must be
  // YYYY-MM-DD" and "term_on is before effective_on" into pcProblems a few
  // hundred lines above. A bare text match therefore passed on the CONTRACT
  // branch's validation while this branch had none -- proved by the negative
  // control that removed this branch's zero-wage guard and still scored 76/76.
  check('the server refuses a zero wage -- asserted on THIS branch, not the contract branch above',
    /prProblems\.push\('rate_per_hour must be greater than zero'\)/.test(api), true);
  check('the server refuses a burden outside 0..99.99 while allowing zero',
    /prProblems\.push\('burden_pct must be between 0 and 99\.99 \(0 means not modelled\)'\)/.test(api) &&
    /prBurden < 0 \|\| prBurden >= 100/.test(api), true);
  check('an omitted burden is coerced to zero on the server rather than rejected',
    /payload\.burden_pct === undefined \|\| payload\.burden_pct === '' \? 0 : Number\(payload\.burden_pct\)/.test(api), true);
  check('the server requires an employee id and a valid period',
    /prProblems\.push\('employee_id is required'\)/.test(api) &&
    /prProblems\.push\('effective_on must be YYYY-MM-DD'\)/.test(api) &&
    /prProblems\.push\('term_on is before effective_on'\)/.test(api), true);
  check('an unprovisioned table says so instead of reporting a successful write',
    /run sql\/sairnsenior_pay_rates_schema\.sql in Supabase first/.test(api), true);
  check('the resource is registered',
    /'sen_pay_rates'/.test(fs.readFileSync(path.join(__dirname, '..', '_resources', 'sairnsenior.js'), 'utf8')), true);
}

{
  const sql = fs.readFileSync(path.join(__dirname, '..', '..', 'sql', 'sairnsenior_pay_rates_schema.sql'), 'utf8');
  const grants = sql.split(/\r?\n/).filter((l) => /^\s*grant\b/i.test(l));
  check('the schema exists and no grant confers delete -- a superseded wage keeps the visits it costed',
    [/create table if not exists public\.sen_pay_rates/.test(sql), grants.some((l) => /\bdelete\b/i.test(l))],
    [true, false]);
  check('RLS is on and there is no anon policy',
    /enable row level security/.test(sql) && /revoke all on public\.sen_pay_rates from anon, authenticated/.test(sql), true);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
