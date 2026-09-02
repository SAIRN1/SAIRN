// SAIRNsenior multi-branch rollup, driven verbatim from sairnsenior.html.
//
// Competitive-gap audit B1, and the enabler for B3 and B5. The audit calls
// multi-branch/multi-state the DEFINING Tier B requirement and records that
// SAIRNroofing and SAIRNdental both capture location while SAIRNsenior
// captures none. Verified absent before building: `location_id` 0,
// `sen_branches` 0, `region` 0 -- the four `branch` hits in the file were all
// comments about server code branches.
//
// THE THREE PROPERTIES THIS FILE EXISTS TO HOLD:
//
//   1. UNASSIGNED IS ALWAYS ITS OWN BUCKET. Every pre-existing client and
//      caregiver has no branch. Folding them into the first office, or
//      dropping them from a total, is how a rollup silently lies -- so the
//      columns are asserted to add up to the agency total.
//   2. A VISIT AND A CLAIM INHERIT THEIR BRANCH FROM THE CLIENT. Stamping it
//      onto the visit at creation would freeze it: moving a client to another
//      office would leave their history attributed to the old one forever.
//      Asserted by moving a client and re-running the rollup.
//   3. NO COST, NO MARGIN. The audit's B5 asks for per-branch P&L; this app
//      holds no payroll, overhead or cost of care, so a profit figure would be
//      an invented number on a screen a Tier B buyer decides from. Revenue and
//      hours are real and reported; the missing half is stated on the panel.

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

// The rollup reads four stores plus two helpers already proven by their own
// suites (hrAddDays/hrIsDate from the hiring build, visitHours from the
// scheduling code). They are extracted too rather than restubbed, so this test
// exercises the real arithmetic end to end.
function build(world) {
  return new Function('W',
    scalar('BR_WINDOW_DAYS') + '\n' +
    'var clients=W.clients, caregivers=W.caregivers, visits=W.visits, claims=W.claims, branches=W.branches;\n' +
    'var H=function(s){return String(s==null?"":s);};\n' +
    fn('hrAddDays') + '\n' + fn('hrIsDate') + '\n' + fn('visitHours') + '\n' +
    fn('brName') + '\n' + fn('brRollup') + '\n' +
    'return { brRollup, brName, BR_WINDOW_DAYS };'
  )(world);
}

const TODAY = '2026-09-02';
function world(o) {
  o = o || {};
  return {
    branches: () => o.branches || [],
    clients: () => o.clients || [],
    caregivers: () => o.caregivers || [],
    visits: () => o.visits || [],
    claims: () => o.claims || []
  };
}
// 2 hours each, inside the window unless overridden.
const VIS = (o) => Object.assign({
  client_id: 'CL1', status: 'completed', scheduled_date: '2026-08-20',
  clock_in_at: '2026-08-20T10:00:00Z', clock_out_at: '2026-08-20T12:00:00Z'
}, o);
const CLM = (o) => Object.assign({ client_id: 'CL1', status: 'submitted', service_date: '2026-08-20', amount: 100 }, o);

const BASE = {
  branches: [{ id: 'B1', name: 'Westlake', state: 'OH', active: true },
             { id: 'B2', name: 'Erie', state: 'PA', active: true }],
  clients: [{ id: 'CL1', branch_id: 'B1' }, { id: 'CL2', branch_id: 'B2' }, { id: 'CL3' }],
  caregivers: [{ id: 'C1', branch_id: 'B1' }, { id: 'C2' }],
  visits: [VIS({ client_id: 'CL1' }), VIS({ client_id: 'CL2' }), VIS({ client_id: 'CL3' })],
  claims: [CLM({ client_id: 'CL1', amount: 100 }), CLM({ client_id: 'CL3', amount: 250 })]
};

// ── unassigned is a bucket, and the totals prove nothing was dropped ─────
{
  const out = build(world(BASE)).brRollup(TODAY, 30);
  const names = out.rows.map((r) => r.name);
  check('every branch on file gets a row even before it has anything',
    names.indexOf('Westlake') !== -1 && names.indexOf('Erie') !== -1, true);
  check('and Unassigned is its own row rather than being folded into an office',
    names.indexOf('Unassigned') !== -1, true);
  check('Unassigned sorts LAST -- it is a gap to close, not a branch to rank',
    names[names.length - 1], 'Unassigned');
  check('client counts add up to every client, none dropped and none double-counted',
    out.totals.clients, BASE.clients.length);
  check('caregiver counts add up too',
    out.totals.caregivers, BASE.caregivers.length);
  // TOTALS ADDING UP IS NOT ENOUGH AND THE NEGATIVE CONTROL PROVED IT:
  // attributing every unassigned client to the first branch still totals
  // correctly, still leaves an Unassigned row (the unassigned CAREGIVER makes
  // one), and passed this file 28/28. The bucket each row lands in has to be
  // asserted directly, not inferred from a sum.
  // Order is hours desc, then clients, then name -- Westlake and Erie tie on
  // both counts here, so Erie leads alphabetically. Asserted as-is rather than
  // loosened, because the ordering is a product decision worth pinning.
  check('each branch counts exactly its OWN clients and caregivers, not a share of the unassigned',
    out.rows.map((r) => [r.name, r.clients, r.caregivers]),
    [['Erie', 1, 0], ['Westlake', 1, 1], ['Unassigned', 1, 1]]);
  check('completed visits and hours add up to the agency total',
    [out.totals.visits, out.totals.hours], [3, 6]);
  check('and the unassigned client\'s work is counted, not silently discarded',
    out.rows.find((r) => r.name === 'Unassigned').hours, 2);
}

// ── the branch is DERIVED from the client, not frozen on the visit ───────
{
  const before = build(world(BASE)).brRollup(TODAY, 30);
  const moved = JSON.parse(JSON.stringify(BASE));
  moved.clients[0].branch_id = 'B2';   // CL1 moves from Westlake to Erie
  const after = build(world(moved)).brRollup(TODAY, 30);
  check('moving a client moves their whole history with them',
    [before.rows.find((r) => r.name === 'Westlake').hours,
     after.rows.find((r) => r.name === 'Westlake').hours,
     after.rows.find((r) => r.name === 'Erie').hours],
    [2, 0, 4]);
  check('and the agency total does not move at all',
    [before.totals.hours, after.totals.hours], [6, 6]);
}

// ── the window, and both of its edges ────────────────────────────────────
{
  const w = build(world(Object.assign({}, BASE, {
    visits: [VIS({ scheduled_date: '2026-09-02' }), VIS({ scheduled_date: '2026-08-03' }),
             VIS({ scheduled_date: '2026-08-02' }), VIS({ scheduled_date: '2026-09-03' })]
  }))).brRollup(TODAY, 30);
  check('today and the 30-day boundary are both INSIDE the window, and either side of it is out',
    w.totals.visits, 2);
}
{
  const w = build(world(Object.assign({}, BASE, {
    visits: [VIS({ status: 'scheduled' }), VIS({ status: 'in_progress' }), VIS({ status: 'completed' })]
  }))).brRollup(TODAY, 30);
  check('only COMPLETED visits count -- a scheduled one is not delivered work',
    w.totals.visits, 1);
}

// ── money ────────────────────────────────────────────────────────────────
{
  const out = build(world(BASE)).brRollup(TODAY, 30);
  check('billed is attributed through the client, and unassigned keeps its own',
    [out.rows.find((r) => r.name === 'Westlake').billed,
     out.rows.find((r) => r.name === 'Unassigned').billed,
     out.totals.billed],
    [100, 250, 350]);
}
{
  const w = build(world(Object.assign({}, BASE, {
    claims: [CLM({ status: 'draft', amount: 999 }), CLM({ status: 'paid', amount: 40 })]
  }))).brRollup(TODAY, 30);
  check('a DRAFT claim is not billed to anyone yet and is not counted as revenue',
    w.totals.billed, 40);
}
// NO MARGIN, NO PROFIT, NO COST -- asserted on the source, because the failure
// mode is a plausible number appearing rather than an exception being thrown.
//
// ASSERTED ON THE EXTRACTED FUNCTION BODY, not on a window of the file. The
// first version matched from the SECOND occurrence of "brRollup" -- its call
// site inside brRender -- straight into the panel's own disclosure, which
// contains the words "no margin or profit figure is computed here". The test
// failed on the sentence that exists to say the thing it was checking for.
check('the rollup itself computes no margin, profit or cost figure',
  /(margin|profit|cost_of|overhead)/i.test(fn('brRollup')), false);
check('and the panel says the missing half is absent rather than estimated',
  /No cost, overhead or payroll data is held by this app/.test(src), true);

// ── a branch this device cannot name ─────────────────────────────────────
{
  const w = build(world({ branches: [], clients: [{ id: 'CL1', branch_id: 'GONE' }] }));
  check('a client pointing at a branch this device does not hold says so',
    w.brName('GONE'), '(branch not on this device)');
  check('and is NOT relabelled Unassigned -- it was assigned, to something not here',
    w.brRollup(TODAY, 30).rows.map((r) => r.name), ['(branch not on this device)']);
  check('an empty branch_id is Unassigned', w.brName(''), 'Unassigned');
}

// ── the state, and what it does NOT yet do ───────────────────────────────
check('the state is refused unless it is two letters, in the page',
  /State must be a 2-letter code/.test(src), true);
{
  const sd = fs.readFileSync(path.join(__dirname, '..', 'sd-data.js'), 'utf8');
  check('and refused again on the server, so the page cannot merely look like it saved',
    /sen_branches: state must be a 2-letter code/.test(sd), true);
  check('read is open to any signed-in employee and write is management-only',
    /sen_branches[\s\S]{0,1600}?Only management can add or change a branch/.test(sd), true);
  check('the resource is registered so the provisioning probe can see it',
    /'sen_branches'/.test(fs.readFileSync(path.join(__dirname, '..', '_resources', 'sairnsenior.js'), 'utf8')), true);
}
// THE HONEST LIMIT IS ON THE SCREEN, not only in a comment. The column is
// captured and reported and is NOT yet what EVV or training is matched on;
// leaving that unsaid would let a two-state agency read it as enforced.
check('the panel states that the branch state is not yet what EVV or training reads',
  /not yet<\/strong> what the EVV configuration or the training requirement is matched on/.test(src), true);

// ── assignment is wired into the two roster records ──────────────────────
check('a client carries branch_id', /branch_id:\(\$\('cl-branch'\)&&\$\('cl-branch'\)\.value\)\|\|''/.test(src), true);
check('a caregiver carries branch_id', /branch_id:\(\$\('cg-branch'\)&&\$\('cg-branch'\)\.value\)\|\|''/.test(src), true);
check('both modals fill their select on open and on edit',
  (src.match(/brFillSelect\('cl-branch'/g) || []).length === 2 &&
  (src.match(/brFillSelect\('cg-branch'/g) || []).length === 2, true);
check('the panel is wired into nav', /if\(id==='branches'\)brRender\(\);/.test(src), true);
{
  const sql = fs.readFileSync(path.join(__dirname, '..', '..', 'sql', 'sairnsenior_branches_schema.sql'), 'utf8');
  const grants = sql.split(/\r?\n/).filter((l) => /^\s*grant\b/i.test(l));
  check('the schema exists and no grant confers delete -- a closed office keeps its history',
    [/create table if not exists public\.sen_branches/.test(sql), grants.some((l) => /\bdelete\b/i.test(l))],
    [true, false]);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
