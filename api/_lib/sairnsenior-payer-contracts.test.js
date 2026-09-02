// SAIRNsenior payer contract rate resolution, driven verbatim from
// sairnsenior.html.
//
// Competitive-gap audit B4 ("payer contract management across many
// payers/states + MCO authorisation -- Tier-B-defining. Absent."). Verified
// absent before building: `sen_payer_contracts` 0 hits, `rate_per_hour` 0,
// `pcResolve` 0 -- generateClaim() created every claim with a literal `rate:0`
// and the biller typed the number in by hand.
//
// THE FOUR PROPERTIES THIS FILE EXISTS TO HOLD:
//
//   1. THE RATE IS RESOLVED AGAINST THE SERVICE DATE, NEVER TODAY. A claim is
//      billed under the contract in force on the day the work was done.
//      Resolving against today would re-rate historical claims every time a
//      contract renewed, and would silently change what an already-submitted
//      claim says it was worth. Asserted by pricing the same visit under a
//      contract that has since been superseded.
//   2. SPECIFIC BEATS GENERAL, AND AN UNKNOWN STATE MATCHES NOTHING SCOPED.
//      A state-scoped contract outranks an agency-wide one for the same payer.
//      The state comes from the CLIENT'S BRANCH, so a client with no branch has
//      no known state -- '' is "not known", never "no state", and must not
//      match a state-scoped row. Matching it anyway would be assuming the
//      state, which is the whole thing the column exists to stop.
//   3. AMBIGUITY REFUSES AND SAYS WHY. Two equally specific contracts both in
//      force do not resolve to the newer, the higher, or the first row. The
//      claim is created at a VISIBLE zero with the reason stored on it.
//      Billing at a rate nobody chose is worse than billing at zero, because a
//      zero is visible on the screen and a plausible wrong rate is not.
//   4. A ZERO RATE IS NOT A CONTRACT. It is an empty field that would price
//      every claim it matched at nothing while LOOKING resolved -- strictly
//      worse than no contract, which at least says so on the claim. Refused in
//      the browser and again in api/sd-data.js.

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

// hrIsDate and hrSourceKey are extracted rather than restubbed -- the resolver
// depends on their exact behaviour (an ISO-shaped string only, and a
// case/whitespace-insensitive payer key), and a stub that was merely close
// would let a real mismatch pass here.
function build(world) {
  return new Function('W',
    'var clients=W.clients, branches=W.branches, payerContracts=W.payerContracts;\n' +
    fn('hrIsDate') + '\n' + fn('hrSourceKey') + '\n' +
    fn('pcInForce') + '\n' + fn('pcStateForClient') + '\n' + fn('pcResolveRate') + '\n' +
    'return { pcInForce, pcStateForClient, pcResolveRate };'
  )(world);
}

function world(o) {
  o = o || {};
  return {
    clients: () => o.clients || [],
    branches: () => o.branches || [],
    payerContracts: () => o.contracts || []
  };
}

// ── 1. the service date, not today ───────────────────────────────────────
{
  // The 2025 contract paid $26.00/hr and was terminated at the end of that
  // year; the 2026 one pays $28.50. A visit worked in 2025 is billed at the
  // 2025 rate for as long as it exists.
  const C = [
    { id: 'PC1', payer: 'medicaid', plan_name: '2025 rate', rate_per_hour: 26, effective_on: '2025-01-01', term_on: '2025-12-31' },
    { id: 'PC2', payer: 'medicaid', plan_name: '2026 rate', rate_per_hour: 28.5, effective_on: '2026-01-01', term_on: '' }
  ];
  const { pcResolveRate } = build(world({ contracts: C }));
  const old = pcResolveRate('medicaid', '2025-06-14', '');
  const now = pcResolveRate('medicaid', '2026-06-14', '');
  check('a 2025 visit prices at the 2025 rate even though that contract has ended',
    [old.status, old.rate_per_hour, old.contract_id], ['applied', 26, 'PC1']);
  check('a 2026 visit prices at the current rate', [now.status, now.rate_per_hour], ['applied', 28.5]);
  check('a service date on the term date itself is still covered -- term_on is inclusive',
    pcResolveRate('medicaid', '2025-12-31', '').rate_per_hour, 26);
  check('a service date on the effective date itself is covered -- effective_on is inclusive',
    pcResolveRate('medicaid', '2026-01-01', '').rate_per_hour, 28.5);
  check('a service date before either contract began resolves to nothing rather than to the earliest one',
    pcResolveRate('medicaid', '2024-12-31', '').status, 'none');
}
{
  // A term date that is present but unreadable must not be skipped as if the
  // field were blank -- that would turn a malformed end date into an
  // open-ended one and keep pricing claims under an expired contract forever.
  const { pcResolveRate } = build(world({
    contracts: [{ id: 'P1', payer: 'medicaid', rate_per_hour: 29, effective_on: '2026-01-01', term_on: '31/12/2026' }]
  }));
  check('a contract whose end date is unreadable is NOT treated as open-ended',
    pcResolveRate('medicaid', '2026-06-01', '').status, 'none');
}

// ── 2. specific beats general; an unknown state matches nothing scoped ───
{
  const C = [
    { id: 'PCW', payer: 'medicaid', plan_name: 'agency-wide', rate_per_hour: 27, effective_on: '2026-01-01', term_on: '' },
    { id: 'PCO', payer: 'medicaid', plan_name: 'Ohio', state: 'OH', rate_per_hour: 30, effective_on: '2026-01-01', term_on: '' }
  ];
  const W = world({
    contracts: C,
    branches: [{ id: 'BR1', name: 'Westlake', state: 'OH' }, { id: 'BR2', name: 'Erie', state: 'PA' }],
    clients: [
      { id: 'CL1', branch_id: 'BR1' },   // Ohio
      { id: 'CL2', branch_id: 'BR2' },   // Pennsylvania
      { id: 'CL3' },                     // no branch at all
      { id: 'CL4', branch_id: 'BR9' }    // branch not on this device
    ]
  });
  const { pcResolveRate, pcStateForClient } = build(W);
  check('the state comes from the client branch, and is blank when there is no branch or the branch is unknown',
    ['CL1', 'CL2', 'CL3', 'CL4'].map(pcStateForClient), ['OH', 'PA', '', '']);
  check('an Ohio client gets the Ohio rate, not the agency-wide one -- specific beats general',
    pcResolveRate('medicaid', '2026-06-01', 'OH').rate_per_hour, 30);
  check('a Pennsylvania client falls back to agency-wide -- the Ohio contract does not travel',
    pcResolveRate('medicaid', '2026-06-01', 'PA').rate_per_hour, 27);
  check('a client with no known state gets agency-wide, never the scoped row',
    pcResolveRate('medicaid', '2026-06-01', '').rate_per_hour, 27);
}
{
  // The dangerous shape: ONLY a state-scoped contract exists, and the client's
  // state is unknown. Applying it would be assuming the state.
  const { pcResolveRate } = build(world({
    contracts: [{ id: 'PCO', payer: 'medicaid', state: 'OH', rate_per_hour: 30, effective_on: '2026-01-01', term_on: '' }]
  }));
  const r = pcResolveRate('medicaid', '2026-06-01', '');
  check('a state-scoped contract is NOT applied to a client whose state is unknown', r.status, 'none');
  check('and the refusal says the branch is not recorded rather than claiming no contract exists',
    /scoped to another state/.test(r.reason) && /not recorded/.test(r.reason), true);
  check('the same contract is also not applied in a DIFFERENT known state',
    pcResolveRate('medicaid', '2026-06-01', 'PA').status, 'none');
}

// ── 3. ambiguity refuses, and names the candidates ───────────────────────
{
  const C = [
    { id: 'PCA', payer: 'medicaid', plan_name: 'Buckeye', rate_per_hour: 27, effective_on: '2026-01-01', term_on: '' },
    { id: 'PCB', payer: 'medicaid', plan_name: 'CareSource', rate_per_hour: 31, effective_on: '2026-03-01', term_on: '' }
  ];
  const { pcResolveRate } = build(world({ contracts: C }));
  const r = pcResolveRate('medicaid', '2026-06-01', '');
  check('two equally specific contracts in force do not resolve', r.status, 'ambiguous');
  check('no rate is carried on an ambiguous result -- not the newer, not the higher, not the first row',
    [r.rate_per_hour, r.contract_id], [undefined, undefined]);
  // `|| []` rather than a bare r.candidates: under the negative control that
  // makes ambiguity resolve to the newest row, this line threw a TypeError and
  // took the remaining forty assertions with it -- so one break was reported
  // as two failures when it was really more. A suite that dies partway through
  // undercounts every break after the first.
  check('both candidates are named so the conflict can actually be fixed',
    (r.candidates || []).map((c) => c.id).sort(), ['PCA', 'PCB']);
  check('the reason states the refusal rather than only reporting a count',
    /billing at a rate nobody chose is worse than billing at zero/.test(r.reason), true);
  // Giving one of them a term date resolves it -- the fix the message names is
  // asserted to be the fix that works.
  const fixed = build(world({ contracts: [Object.assign({}, C[0], { term_on: '2026-02-28' }), C[1]] }))
    .pcResolveRate('medicaid', '2026-06-01', '');
  check('terminating one of them resolves the overlap, as the message instructs',
    [fixed.status, fixed.rate_per_hour], ['applied', 31]);
  // Two contracts in the SAME state are ambiguous; a state-scoped one plus an
  // agency-wide one is not, because they are not equally specific.
  const scoped = build(world({
    contracts: [
      { id: 'P1', payer: 'medicaid', state: 'OH', rate_per_hour: 30, effective_on: '2026-01-01' },
      { id: 'P2', payer: 'medicaid', state: 'OH', rate_per_hour: 33, effective_on: '2026-01-01' }
    ]
  })).pcResolveRate('medicaid', '2026-06-01', 'OH');
  check('two contracts scoped to the same state are ambiguous', scoped.status, 'ambiguous');
}

// ── the "none" cases each say something different ────────────────────────
{
  const { pcResolveRate } = build(world({ contracts: [] }));
  check('a visit with no service date is refused for that reason, not for a missing contract',
    /no service date/.test(pcResolveRate('medicaid', '', '').reason), true);
  check('a client with no payer is refused for that reason',
    /no payer recorded/.test(pcResolveRate('', '2026-06-01', '').reason), true);
  check('no contract on file names the date it was looking for',
    /covering 2026-06-01/.test(pcResolveRate('medicaid', '2026-06-01', '').reason), true);
}
{
  // Payer matching is case- and whitespace-insensitive on both sides, because
  // one side is a select value and the other was typed.
  const { pcResolveRate } = build(world({
    contracts: [{ id: 'P1', payer: ' Medicaid ', rate_per_hour: 29, effective_on: '2026-01-01' }]
  }));
  check('payer matching survives case and stray whitespace',
    pcResolveRate('MEDICAID', '2026-06-01', '').rate_per_hour, 29);
}
{
  // A contract with no effective_on cannot be matched to any service date, and
  // must not be treated as "always in force".
  const { pcResolveRate } = build(world({
    contracts: [{ id: 'P1', payer: 'medicaid', rate_per_hour: 29, effective_on: '' }]
  }));
  check('a contract with no effective date is never in force', pcResolveRate('medicaid', '2026-06-01', '').status, 'none');
}

// ── 4. the claim carries the outcome, priced or not ──────────────────────
check('generateClaim resolves against the SERVICE date and the client branch state, not today',
  /pcResolveRate\(\(cl&&cl\.payer\)\|\|'',v\.scheduled_date,pcStateForClient\(v\.client_id\)\)/.test(src), true);
check('an unresolved rate produces a literal zero on the row, not a guess',
  /rate:rate\.status==='applied'\?rate\.rate_per_hour:0/.test(src) &&
  /amount:rate\.status==='applied'\?Math\.round\(rate\.rate_per_hour\*hoursBilled\*100\)\/100:0/.test(src), true);
check('the reason is STORED on the claim, not only shown in a toast that scrolls away',
  /rate_source:rate\.status,rate_source_note:rate\.reason\|\|''/.test(src), true);
check('a zero-rate claim tells the biller it is zero and why, and stays on screen longer',
  /Claim created at a ZERO rate/.test(src) && /rate\.status==='applied'&&!rate\.requires_authorization\?4000:9000/.test(src), true);
check('a payer needing prior authorisation says so at the moment the claim is made',
  /This payer requires prior authorisation/.test(src), true);

// ── the zero-rate refusal, in both places ────────────────────────────────
check('the browser refuses a zero or negative rate', /if\(!\(rate>0\)\)\{toast\(/.test(src), true);
check('the browser requires an effective date', /An effective date is required/.test(src), true);
check('the browser refuses an end date before the start date', /The end date is before the start date/.test(src), true);
{
  const api = fs.readFileSync(path.join(__dirname, '..', 'sd-data.js'), 'utf8');
  check('the server refuses a zero rate too -- the browser check is not the only one',
    /rate_per_hour must be greater than zero/.test(api), true);
  check('the server refuses a free-text state, blank meaning agency-wide',
    /must be a 2-letter code \(blank means agency-wide\)/.test(api), true);
  check('the server gate is management-only on BOTH verbs -- a contracted rate is financial data',
    /resource === 'sen_payer_contracts' && \(action === 'read' \|\| action === 'write'\)/.test(api) &&
    /Only management can view or manage payer contracts/.test(api), true);
  check('an unprovisioned table says so instead of reporting a successful write',
    /run sql\/sairnsenior_payer_contracts_schema\.sql in Supabase first/.test(api), true);
  check('the resource is registered',
    /'sen_payer_contracts'/.test(fs.readFileSync(path.join(__dirname, '..', '_resources', 'sairnsenior.js'), 'utf8')), true);
}

// ── the panel actually exists and is reachable ───────────────────────────
// Added after the first attempt at this feature shipped the resolver, the API
// gate and the schema with NO panel markup at all: pcRender is null-guarded
// throughout, so every element being absent rendered a blank screen in silence
// rather than throwing. A dead nav button that fails quietly is worse than one
// that crashes, and nothing in the suite would have caught it.
['panel-contracts', 'pcmodal', 'pc-tbody', 'pc-denied', 'pc-content', 'pc-conflicts',
 'pc-payer', 'pc-plan', 'pc-state', 'pc-rate', 'pc-effective', 'pc-term', 'pc-auth', 'pc-auth-note',
 'pc-modal-title'].forEach((id) => {
  check('the DOM node #' + id + ' that the code reads actually exists', new RegExp('id="' + id + '"').test(src), true);
});
check('the panel is wired into nav', /if\(id==='contracts'\)pcRender\(\);/.test(src), true);
check('the sidebar button exists and points at it', /id="sb-contracts" onclick="nav\('contracts'\)"/.test(src), true);
check('something on screen actually opens the modal -- the resolver is unreachable without it',
  /onclick="openPcModal\(\)"/.test(src), true);

// ── hydration: the server copy of a rate wins over a stale local one ─────
check('contracts hydrate from the server, replacing the local row rather than only adding unseen ones',
  /function senHydratePayerContracts\(\)/.test(src) &&
  /JSON\.stringify\(byId\[c\.id\]\)!==JSON\.stringify\(c\)/.test(src), true);
check('Billing hydrates contracts alongside claims, so a fresh device does not price a screenful of claims at zero',
  /Promise\.all\(\[senHydrateClaims\(\),senHydratePayerContracts\(\)\]\)/.test(src), true);
check('saving repaints without hydrating -- a hydrate racing the write would undo the edit on screen',
  /closePcModal\(\);pcPaint\(\);/.test(src), true);

// ── money is displayed to the cent ───────────────────────────────────────
// A rate is the number this whole feature exists to get right; showing $28.50
// as "$28" is a rounding of the display that nobody can reconcile against a
// remittance.
check('fmt shows cents rather than rounding to whole dollars',
  /minimumFractionDigits:2,maximumFractionDigits:2/.test(src) &&
  !/minimumFractionDigits:0,maximumFractionDigits:0/.test(src), true);

{
  const sql = fs.readFileSync(path.join(__dirname, '..', '..', 'sql', 'sairnsenior_payer_contracts_schema.sql'), 'utf8');
  const grants = sql.split(/\r?\n/).filter((l) => /^\s*grant\b/i.test(l));
  check('the schema exists and no grant confers delete -- a retired contract keeps the claims it priced',
    [/create table if not exists public\.sen_payer_contracts/.test(sql), grants.some((l) => /\bdelete\b/i.test(l))],
    [true, false]);
  check('RLS is on and there is no anon policy', /enable row level security/.test(sql) && /revoke all on public\.sen_payer_contracts from anon, authenticated/.test(sql), true);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
