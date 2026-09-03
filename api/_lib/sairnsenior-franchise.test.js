// SAIRNsenior franchise agreements and royalty statements, driven verbatim
// from sairnsenior.html.
//
// Competitive-gap audit item B3 ("franchise-network reporting and royalty
// calculation", Tier-B-defining). Verified absent before building:
// `franchise` 0 occurrences, `royalt` 0. The audit records WellSky's claim of 8
// of the 10 largest personal-care franchise networks as a real moat and notes
// most Tier A tools do not attempt this.
//
// THE SIX PROPERTIES THIS FILE EXISTS TO HOLD:
//
//   1. A DENIED CLAIM IS NOT REVENUE. The branch rollup (B1) counts every
//      non-draft claim as billed, which is right for an operational view -- it
//      WAS billed. As a royalty base it is wrong: charging a percentage of a
//      claim the payer refused takes real cash for work nobody was paid for.
//   2. AN APPEALED CLAIM IS IN NEITHER BUCKET. Billed, then denied, outcome
//      undecided. Counting it overstates what is owed; dropping it silently
//      leaves a statement that does not reconcile. It is its own line.
//   3. THE BASE IS DECLARED, NEVER DEFAULTED. Billed and collected differ by
//      months of cash and the difference favours one side of the agreement.
//   4. A PAID CLAIM WITH NO PAYMENT DATE LANDS IN NO PERIOD. Claims marked paid
//      before 2026-09-02 have no paid_date and are not back-filled -- inventing
//      the month money arrived changes what a unit owes.
//   5. NOTHING IS STORED. The statement is recomputed from sen_claims every
//      time it is drawn, and the server strips a client-supplied
//      royalty_amount.
//   6. A UNIT THAT CANNOT BE COMPUTED IS NAMED, NOT DROPPED. A network total
//      that quietly omits three units is wrong in a way nothing on the screen
//      would reveal.

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

const TODAY = '2026-09-02';

function build(world) {
  return new Function('W',
    'var clients=W.clients, branches=W.branches, claims=W.claims, franchiseAgreements=W.franchiseAgreements;\n' +
    'var H=function(s){return String(s==null?"":s);};\n' +
    'var senLocalToday=function(){return "' + TODAY + '";};\n' +
    fn('hrIsDate') + '\n' + fn('brName') + '\n' +
    fn('frInForce') + '\n' + fn('frResolveAgreement') + '\n' +
    fn('frRevenueBase') + '\n' + fn('frStatement') + '\n' + fn('frNetwork') + '\n' +
    'return { frInForce, frResolveAgreement, frRevenueBase, frStatement, frNetwork };'
  )(world);
}
function world(o) {
  o = o || {};
  return {
    clients: () => o.clients || [],
    branches: () => o.branches || [],
    claims: () => o.claims || [],
    franchiseAgreements: () => o.agreements || []
  };
}

const BRANCHES = [{ id: 'B1', name: 'Westlake', state: 'OH' }, { id: 'B2', name: 'Erie', state: 'PA' }];
const CLIENTS = [{ id: 'CL1', branch_id: 'B1' }, { id: 'CL2', branch_id: 'B2' }, { id: 'CL3' }];
const AG = { id: 'F1', branch_id: 'B1', unit_code: 'OH-014', franchisee_name: 'Wexler Care LLC',
  royalty_pct: 5, ad_fund_pct: 2, royalty_base: 'billed', effective_on: '2026-01-01', term_on: '' };
// One claim of each status, all in August, all on unit B1.
const CLM = (o) => Object.assign({ client_id: 'CL1', service_date: '2026-08-15', amount: 100 }, o);
const AUG = { from: '2026-08-01', to: '2026-08-31' };

// ── 1 & 2. denied is not revenue; appealed is in neither bucket ─────────
{
  const W = world({ branches: BRANCHES, clients: CLIENTS, agreements: [AG], claims: [
    CLM({ id: 'C1', status: 'submitted', amount: 1000 }),
    CLM({ id: 'C2', status: 'paid', amount: 500, paid_date: '2026-08-20' }),
    CLM({ id: 'C3', status: 'denied', amount: 400 }),
    CLM({ id: 'C4', status: 'appeal_denied', amount: 300 }),
    CLM({ id: 'C5', status: 'appealed', amount: 200 }),
    CLM({ id: 'C6', status: 'draft', amount: 900 })
  ] });
  const rev = build(W).frRevenueBase('B1', 'billed', AUG.from, AUG.to);
  check('only submitted and paid claims are in the billed base', [rev.included, rev.n_included], [1500, 2]);
  check('denied and appeal-denied are excluded and REPORTED, not silently dropped',
    [rev.denied, rev.n_denied], [700, 2]);
  check('an appealed claim is in neither included nor denied -- it has its own line',
    [rev.disputed, rev.n_disputed], [200, 1]);
  check('a draft claim is billed to nobody and is in no bucket but its own',
    [rev.draft, rev.n_draft], [900, 1]);
  // The arithmetic that matters: royalty is charged on 1500, not on the 2600
  // the operational rollup would call "billed", and not on the 3500 total.
  const s = build(W).frStatement('B1', AUG.from, AUG.to);
  check('royalty and ad fund are charged on the included base only',
    [s.royalty, s.ad_fund, s.total_due], [75, 30, 105]);
  check('the base used is carried on the statement so it can be checked',
    [s.royalty_base, s.royalty_pct, s.ad_fund_pct], ['billed', 5, 2]);
  check('the ad fund is its own figure, never folded into the royalty',
    s.royalty + s.ad_fund === s.total_due && s.royalty !== s.total_due, true);
}

// ── 3. billed and collected are different money, and the base decides ───
{
  // Work done in August, paid in September. On a BILLED basis it is August
  // revenue; on a COLLECTED basis it is September revenue. Same claim, two
  // periods -- which is exactly why the base cannot be guessed.
  const claims = [CLM({ id: 'C1', status: 'paid', amount: 1000, service_date: '2026-08-15', paid_date: '2026-09-10' })];
  const billed = build(world({ branches: BRANCHES, clients: CLIENTS, agreements: [AG], claims }));
  const collAg = Object.assign({}, AG, { royalty_base: 'collected' });
  const coll = build(world({ branches: BRANCHES, clients: CLIENTS, agreements: [collAg], claims }));
  check('on a BILLED basis the claim is August revenue',
    billed.frRevenueBase('B1', 'billed', AUG.from, AUG.to).included, 1000);
  check('on a COLLECTED basis the same claim is NOT August revenue',
    coll.frRevenueBase('B1', 'collected', AUG.from, AUG.to).included, 0);
  check('and it IS September revenue on a collected basis',
    coll.frRevenueBase('B1', 'collected', '2026-09-01', '2026-09-30').included, 1000);
  // A submitted-but-unpaid claim is revenue on one basis and not the other.
  const unpaid = [CLM({ id: 'C9', status: 'submitted', amount: 700 })];
  check('a submitted, unpaid claim counts as billed revenue and not as collected',
    [build(world({ branches: BRANCHES, clients: CLIENTS, agreements: [AG], claims: unpaid })).frRevenueBase('B1', 'billed', AUG.from, AUG.to).included,
     build(world({ branches: BRANCHES, clients: CLIENTS, agreements: [collAg], claims: unpaid })).frRevenueBase('B1', 'collected', AUG.from, AUG.to).included],
    [700, 0]);
}

// ── 4. a paid claim with no payment date is in NO period ────────────────
{
  const collAg = Object.assign({}, AG, { royalty_base: 'collected' });
  const W = world({ branches: BRANCHES, clients: CLIENTS, agreements: [collAg], claims: [
    CLM({ id: 'C1', status: 'paid', amount: 1000 }),                                  // legacy: no paid_date
    CLM({ id: 'C2', status: 'paid', amount: 500, paid_date: '2026-08-20' })
  ] });
  const rev = build(W).frRevenueBase('B1', 'collected', AUG.from, AUG.to);
  check('a paid claim with no payment date is excluded and counted separately',
    [rev.included, rev.n_included, rev.undated_paid, rev.n_undated_paid], [500, 1, 1000, 1]);
  // It must not appear in ANY period -- not this one, not a wider one.
  const wide = build(W).frRevenueBase('B1', 'collected', '2020-01-01', '2030-12-31');
  check('and it lands in no period at all, however wide the window',
    [wide.included, wide.n_undated_paid], [500, 1]);
  check('the panel says why they are not back-filled',
    /inventing the month money arrived changes what a unit owes/.test(src), true);
}

// ── the agreement resolves against the PERIOD END, not today ────────────
{
  const A1 = Object.assign({}, AG, { id: 'A1', royalty_pct: 4, effective_on: '2026-01-01', term_on: '2026-06-30' });
  const A2 = Object.assign({}, AG, { id: 'A2', royalty_pct: 6, effective_on: '2026-07-01', term_on: '' });
  const { frResolveAgreement, frInForce } = build(world({ branches: BRANCHES, clients: CLIENTS, agreements: [A1, A2] }));
  check('a March statement resolves under the agreement that governed March',
    frResolveAgreement('B1', '2026-03-31').royalty_pct, 4);
  check('an August statement resolves under the current agreement',
    frResolveAgreement('B1', '2026-08-31').royalty_pct, 6);
  check('both ends of the agreement period are inclusive',
    [frInForce(A1, '2026-01-01'), frInForce(A1, '2026-06-30'), frInForce(A1, '2026-07-01')], [true, true, false]);
  check('an agreement whose end date is unreadable is not treated as open-ended',
    frInForce(Object.assign({}, A1, { term_on: '30/06/2026' }), '2026-03-31'), false);
  check('a unit with agreements but none in force says so, and how many',
    /2 agreement\(s\) on file but none in force on 2025-12-31/.test(frResolveAgreement('B1', '2025-12-31').reason), true);
  check('a unit with nothing on file is told no royalty is COMPUTED, not that it is zero',
    /That is not the same as a royalty of zero/.test(frResolveAgreement('B2', '2026-08-31').reason), true);
  // ASSERTED THROUGH frStatement, NOT ONLY ON THE RESOLVER. The first version
  // checked frResolveAgreement directly and the negative control that made
  // frStatement resolve against TODAY passed 78/78 -- because every period in
  // the other worlds fell under the same agreement as today. This asks for a
  // MARCH statement while today is September, under two different agreements,
  // so re-running an old statement is asserted to reproduce the old number.
  const marchClaims = [CLM({ id: 'M1', status: 'submitted', amount: 1000, service_date: '2026-03-15' })];
  const st = build(world({ branches: BRANCHES, clients: CLIENTS, agreements: [A1, A2], claims: marchClaims }))
    .frStatement('B1', '2026-03-01', '2026-03-31');
  check('a March statement charges March\'s percentage even though today is September',
    [st.royalty_pct, st.royalty], [4, 40]);
}
{
  const A1 = Object.assign({}, AG, { id: 'A1', royalty_pct: 4 });
  const A2 = Object.assign({}, AG, { id: 'A2', royalty_pct: 9 });
  const { frResolveAgreement, frStatement } = build(world({ branches: BRANCHES, clients: CLIENTS, agreements: [A1, A2],
    claims: [CLM({ id: 'C1', status: 'submitted', amount: 1000 })] }));
  const r = frResolveAgreement('B1', '2026-08-31');
  check('two agreements in force for one unit do not resolve', r.status, 'ambiguous');
  check('no percentage is carried on an ambiguous result -- not the lower, not the higher',
    [r.royalty_pct, r.agreement_id], [undefined, undefined]);
  check('the reason says a royalty charged on guessed terms is money taken wrongly',
    /money taken on a contract this software guessed at/.test(r.reason), true);
  check('and the statement refuses rather than charging something',
    [frStatement('B1', AUG.from, AUG.to).status, frStatement('B1', AUG.from, AUG.to).royalty],
    ['ambiguous', undefined]);
}

// ── 6. the network total names what it could not compute ───────────────
{
  // B1 has an agreement; B2 does not; CL3 has no branch at all.
  const W = world({ branches: BRANCHES, clients: CLIENTS, agreements: [AG], claims: [
    CLM({ id: 'C1', client_id: 'CL1', status: 'submitted', amount: 1000 }),
    CLM({ id: 'C2', client_id: 'CL2', status: 'submitted', amount: 800 }),
    CLM({ id: 'C3', client_id: 'CL3', status: 'submitted', amount: 600 })
  ] });
  const net = build(W).frNetwork(AUG.from, AUG.to);
  check('only units with an agreement produce a statement', net.rows.map((r) => r.branch_id), ['B1']);
  // `|| {}` rather than a bare index: the break that drops uncomputable units
  // left this undefined and threw, which reports the break as caught while
  // hiding how many assertions it really broke.
  const unc = net.uncomputable[0] || {};
  check('a unit that produced none is NAMED rather than dropped',
    [net.uncomputable.length, unc.branch_id, /No franchise agreement is on file/.test(unc.reason || '')],
    [1, 'B2', true]);
  check('the network total covers only the units it could compute', net.totals.included, 1000);
  // The dangerous one: B2's 800 is NOT in the total, and that omission is
  // visible rather than silent.
  check('revenue from a unit with no agreement is not folded into another unit',
    net.rows.every((r) => r.revenue.included !== 1800), true);
  // THIS ASSERTION FOUND A REAL BUG RATHER THAN CONFIRMING ONE. CL3 has no
  // `branch_id` KEY at all, so the first version's `(c?c.branch_id:'')`
  // yielded undefined, `undefined !== ''` dropped it, and its revenue
  // disappeared from EVERY total on the screen -- charged to nobody and
  // reported to nobody, which is the exact failure this line exists to prevent.
  // A claim whose client is not on this device took the same path.
  check('revenue from clients with no branch is reported on its own and charged to nobody',
    [net.unattached.included, net.unattached.n_included], [600, 1]);
  {
    const missing = build(world({ branches: BRANCHES, clients: CLIENTS, agreements: [AG],
      claims: [CLM({ id: 'CX', client_id: 'GONE', status: 'submitted', amount: 250 })] }));
    check('a claim whose client is not on this device also lands in unattached, not nowhere',
      missing.frNetwork(AUG.from, AUG.to).unattached.included, 250);
  }
  check('the panel says attributing it would invoice a franchisee for work outside their territory',
    /invoice a franchisee for work outside their territory/.test(src), true);
}
{
  // Mixed bases across a network do not add up to a meaningful quantity, and
  // the code says so rather than printing a plain total.
  const A1 = Object.assign({}, AG, { id: 'A1', branch_id: 'B1', royalty_base: 'billed' });
  const A2 = Object.assign({}, AG, { id: 'A2', branch_id: 'B2', royalty_base: 'collected' });
  const net = build(world({ branches: BRANCHES, clients: CLIENTS, agreements: [A1, A2], claims: [] })).frNetwork(AUG.from, AUG.to);
  check('a network running two royalty bases is flagged, not silently summed',
    [net.mixed_bases, net.bases.sort()], [true, ['billed', 'collected']]);
  const single = build(world({ branches: BRANCHES, clients: CLIENTS, agreements: [A1], claims: [] })).frNetwork(AUG.from, AUG.to);
  check('a network on one base is not flagged', single.mixed_bases, false);
  check('and the panel states the mixed total is not like-for-like',
    /is not a like-for-like figure/.test(src), true);
}
{
  // Zero royalty is a legitimate record (a corporate-owned unit), and must
  // produce a statement rather than being refused as an empty field.
  const zero = Object.assign({}, AG, { royalty_pct: 0, ad_fund_pct: 0 });
  const s = build(world({ branches: BRANCHES, clients: CLIENTS, agreements: [zero],
    claims: [CLM({ id: 'C1', status: 'submitted', amount: 1000 })] })).frStatement('B1', AUG.from, AUG.to);
  check('a zero-royalty unit still produces a statement showing its revenue',
    [s.status, s.revenue.included, s.royalty, s.total_due], ['applied', 1000, 0, 0]);
}

// ── nothing is stored ───────────────────────────────────────────────────
check('no browser code path reads or writes a stored royalty amount',
  /royalty_amount/.test([fn('frStatement'), fn('frNetwork'), fn('frRevenueBase'),
                          fn('frResolveAgreement'), fn('saveFranchiseAgreement'), fn('frPaint')].join('\n')), false);
check('the payment date is recorded when a claim is marked paid',
  /function blMarkPaid\(id\)\{blUpdateClaim\(id,\{status:'paid',paid_date:senLocalToday\(\)\}\);\}/.test(src), true);

// ── the panel exists and is reachable ──────────────────────────────────
['panel-franchise', 'frmodal', 'fr-tbody', 'fr-agreements', 'fr-denied', 'fr-content',
 'fr-warnings', 'fr-add-btn', 'fr-modal-title', 'fr-branch', 'fr-unit', 'fr-franchisee',
 'fr-royalty', 'fr-adfund', 'fr-base', 'fr-effective', 'fr-term', 'fr-notes',
 'fr-from', 'fr-to'].forEach((id) => {
  check('the DOM node #' + id + ' that the code reads actually exists', new RegExp('id="' + id + '"').test(src), true);
});
check('the panel is wired into nav', /if\(id==='franchise'\)frRender\(\);/.test(src), true);
check('the sidebar button exists and points at it', /id="sb-franchise" onclick="nav\('franchise'\)"/.test(src), true);
check('something on screen opens the modal', /onclick="openFrModal\(\)"/.test(src), true);
check('changing either period date redraws the statement',
  (src.match(/id="fr-(from|to)" type="date" onchange="frPaint\(\)"/g) || []).length, 2);
check('the panel states that a denied claim is not revenue, in those words',
  /<strong>A denied claim is not revenue\.<\/strong>/.test(src), true);
check('and that an appealed claim is in neither bucket',
  /<strong>A claim under appeal is in neither bucket<\/strong>/.test(src), true);
check('the base select opens BLANK so a base is chosen rather than accepted',
  /<option value="">-- choose, there is no default --<\/option>/.test(src), true);
check('the statement table header carries a cell for each column the row renders',
  /<th>Unit<\/th><th>Franchisee<\/th><th>Base<\/th>/.test(src) && /colspan="9"/.test(src), true);

// ── the browser refusals, asserted on the extracted function ───────────
// saveFranchiseAgreement's neighbours carry near-identical guards with
// near-identical wording; a file-wide match would pass on theirs.
{
  const save = fn('saveFranchiseAgreement');
  check('the browser refuses a missing base with no default applied',
    /if\(base!=='billed'&&base!=='collected'\)\{toast\(/.test(save), true);
  check('the browser allows zero royalty but refuses out-of-range',
    /if\(!isFinite\(royalty\)\|\|royalty<0\|\|royalty>=100\)\{toast\(/.test(save) &&
    /royaltyRaw===''\?0:Number\(royaltyRaw\)/.test(save), true);
  check('the browser requires a unit and an effective date',
    /Pick the unit this agreement covers/.test(save) && /An effective date is required/.test(save), true);
  check('the browser refuses an inverted period', /if\(term<eff\)\{toast\(|if\(term&&term<eff\)\{toast\(/.test(save), true);
}

// ── the server refusals ────────────────────────────────────────────────
{
  const api = fs.readFileSync(path.join(__dirname, '..', 'sd-data.js'), 'utf8');
  check('the gate is management-only on both verbs',
    /Only management can view or manage franchise agreements/.test(api) &&
    /resource === 'sen_franchise_agreements' && \(action === 'read' \|\| action === 'write'\)/.test(api), true);
  // Anchored to frProblems: the pay-rate and contract branches above push
  // messages of the same shape, and a bare text match would pass on theirs.
  // ANCHORED TO THE GUARD, not to the message. The message text survives when
  // the `if` around it is disabled, and the negative control that defaulted the
  // base on the server passed 78/78 against the earlier version. Scrubber item
  // 16 shape B: existence where the requirement is use.
  check('the server requires a base and states there is no default',
    /\['billed', 'collected'\]\.indexOf\(String\(payload\.royalty_base \|\| ''\)\) < 0/.test(api) &&
    /frProblems\.push\("royalty_base must be 'billed' or 'collected' -- there is no default/.test(api), true);
  check('the server range-checks both percentages while allowing zero',
    /frProblems\.push\('royalty_pct must be between 0 and 99\.99'\)/.test(api) &&
    /frProblems\.push\('ad_fund_pct must be between 0 and 99\.99'\)/.test(api) &&
    /payload\.royalty_pct === undefined \|\| payload\.royalty_pct === '' \? 0 : Number\(payload\.royalty_pct\)/.test(api), true);
  check('the server requires a branch -- the unit IS a branch',
    /frProblems\.push\('branch_id is required -- the unit IS a branch'\)/.test(api), true);
  check('the server requires a valid agreement period',
    /frProblems\.push\('effective_on must be YYYY-MM-DD'\)/.test(api) &&
    /frProblems\.push\('term_on is before effective_on'\)/.test(api), true);
  check('the server STRIPS a client-supplied royalty_amount rather than storing it',
    /delete frBody\.royalty_amount;/.test(api), true);
  check('an unprovisioned table says so instead of reporting a successful write',
    /run sql\/sairnsenior_franchise_schema\.sql in Supabase first/.test(api), true);
  check('the resource is registered',
    /'sen_franchise_agreements'/.test(fs.readFileSync(path.join(__dirname, '..', '_resources', 'sairnsenior.js'), 'utf8')), true);
}

{
  const sql = fs.readFileSync(path.join(__dirname, '..', '..', 'sql', 'sairnsenior_franchise_schema.sql'), 'utf8');
  const grants = sql.split(/\r?\n/).filter((l) => /^\s*grant\b/i.test(l));
  check('the schema exists and no grant confers delete -- a statement already issued keeps its justification',
    [/create table if not exists public\.sen_franchise_agreements/.test(sql), grants.some((l) => /\bdelete\b/i.test(l))],
    [true, false]);
  check('RLS is on and there is no anon policy',
    /enable row level security/.test(sql) && /revoke all on public\.sen_franchise_agreements from anon, authenticated/.test(sql), true);
  // Asserted on the column list, not the file: the prose above it explains at
  // length why there is no stored amount. Scrubber item 16 shape A.
  const cols = sql.slice(sql.indexOf('create table if not exists'), sql.indexOf(');', sql.indexOf('create table if not exists')));
  check('the table has no royalty_amount column', /royalty_amount/.test(cols), false);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
