// SAIRNsenior denials-and-appeals, driven verbatim from sairnsenior.html.
//
// WHY THIS EXISTS. The 2026-08-26 worldwide competitive-gap audit records B2
// for SAIRNsenior: "No vendor in the market published a concrete
// denials-and-appeals workflow" and "Medicaid billing opacity" is the loudest
// single Tier B complaint. Half of it was already here -- a denial reason is
// captured and denial PATTERNS are analysed -- and the other half was not:
// `denied` had no action button at all, so the interface wrote the money off
// rather than the agency deciding to.
//
// THE TWO ASSERTIONS THAT MATTER MOST ARE BOTH ABOUT NOT OVERSTATING MONEY:
//
//   * An overturned appeal returns the claim to `submitted`, NOT to `paid`.
//     The payer agreeing to reprocess is not the payer having paid. Booking
//     it as paid would put a number on the Billing screen that no bank
//     statement backs.
//   * The appeal-outcome breakdown counts a claim as denied-EVER by whether
//     it carries a denial reason, not by its CURRENT status. Filtering on
//     status==='denied' -- which the older pattern breakdown does, correctly,
//     for its own question -- drops every appeal that SUCCEEDED, because a
//     won appeal moves the claim to submitted and then paid. That version
//     reports a 0% overturn rate no matter how many were won. The test drives
//     exactly that scenario.
//
// No deadline is ever derived. Payer appeal windows differ by contract and by
// state and this app does not know them; every deadline here is one the
// agency typed in, and a denied claim with none is reported as having none.

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

const SRC = [
  lit('CAM_ROWS', '[', ']'),
  fn('camShow'), fn('camTrim'),
  fn('senRecoveredByAppeal'), fn('senAppealDaysLeft'),
  fn('computeAppealOutcomeFindings'), fn('computeAppealDeadlineFindings'),
  fn('confirmClaimAction'), fn('renderClaimsTable'), fn('blRenderKpis')
].join('\n');

// ── the world ───────────────────────────────────────────────────────────
function world(opts) {
  opts = opts || {};
  const store = { rows: JSON.parse(JSON.stringify(opts.claims || [])) };
  const els = {};
  const fields = Object.assign({}, opts.fields);
  const w = {
    toasts: [], written: [],
    store,
    _camMode: opts.mode || null,
    _camClaimId: opts.claimId || null,
    TODAY: opts.today || '2026-06-15',
    claims: () => JSON.parse(JSON.stringify(store.rows)),
    senIsManagement: () => opts.management !== false,
    readyToBillVisits: () => [],
    senLocalToday: () => w.TODAY,
    certDaysUntil: (d) => d ? Math.round((new Date(d + 'T00:00:00') - new Date(w.TODAY + 'T00:00:00')) / 86400000) : null,
    fmt: (n) => '$' + Number(n || 0).toFixed(0),
    fdate: (d) => d || '--',
    H: (s) => String(s == null ? '' : s),
    toast: (m) => w.toasts.push(m),
    closeClaimActionModal: () => { w._camMode = null; w._camClaimId = null; },
    blUpdateClaim: (id, patch) => {
      w.written.push({ id, patch });
      const c = store.rows.find(x => x.id === id);
      if (c) Object.assign(c, patch);
    },
    $: (id) => {
      if (!els[id]) els[id] = { style: { display: '' }, _v: fields[id] || '', innerHTML: '', textContent: '',
        get value() { return this._v; }, set value(v) { this._v = v; } };
      return els[id];
    },
    els
  };
  return w;
}
function run(w, extra) {
  const names = ['claims', 'senIsManagement', 'readyToBillVisits', 'senLocalToday', 'certDaysUntil', 'fmt', 'fdate', 'H', 'toast', 'closeClaimActionModal', 'blUpdateClaim', '$'];
  const body = 'var _camMode=W._camMode,_camClaimId=W._camClaimId;\n' + SRC +
    '\nreturn { camShow, camTrim, senRecoveredByAppeal, senAppealDaysLeft, computeAppealOutcomeFindings, computeAppealDeadlineFindings, confirmClaimAction, renderClaimsTable, blRenderKpis };';
  const f = new Function('W', ...names, body);
  return f(w, ...names.map(n => w[n]));
}

// ── an overturned appeal must NOT be booked as paid ─────────────────────
{
  const w = world({ claims: [{ id: 'C1', amount: 400, status: 'appealed', denial_reason: 'Missing authorization',
    appeal: { filed_on: '2026-06-01', level: 'first_level', basis: 'EVV record attached', outcome: null } }],
    mode: 'appeal_overturned', claimId: 'C1', fields: { 'cam-outcome-note': 'Payer agreed to reprocess' } });
  run(w).confirmClaimAction();
  check('an overturned appeal returns the claim to submitted, not paid',
    w.written[0].patch.status, 'submitted');
  check('and the outcome is recorded with the date it was decided',
    [w.written[0].patch.appeal.outcome, w.written[0].patch.appeal.outcome_on], ['overturned', '2026-06-15']);
  check('the original basis survives the outcome patch',
    w.written[0].patch.appeal.basis, 'EVV record attached');
  check('so nothing counts as recovered until the claim is actually paid',
    run(w).senRecoveredByAppeal(), 0);
}
{
  const w = world({ claims: [{ id: 'C1', amount: 400, status: 'paid', denial_reason: 'x',
    appeal: { filed_on: '2026-06-01', outcome: 'overturned' } }] });
  check('once it IS paid, the recovery is counted', run(w).senRecoveredByAppeal(), 400);
}
{
  const w = world({ claims: [{ id: 'C1', amount: 400, status: 'paid' },
    { id: 'C2', amount: 900, status: 'submitted', denial_reason: 'x', appeal: { filed_on: '2026-06-01', outcome: 'overturned' } }] });
  check('a paid claim that was never appealed is not recovery, and a won-but-unpaid one is not either',
    run(w).senRecoveredByAppeal(), 0);
}

// ── an upheld appeal is terminal and says so ────────────────────────────
{
  const w = world({ claims: [{ id: 'C1', amount: 400, status: 'appealed', denial_reason: 'x', appeal: { filed_on: '2026-06-01' } }],
    mode: 'appeal_upheld', claimId: 'C1', fields: { 'cam-outcome-note': 'Upheld on review' } });
  run(w).confirmClaimAction();
  check('an upheld appeal moves to appeal_denied',
    [w.written[0].patch.status, w.written[0].patch.appeal.outcome], ['appeal_denied', 'upheld']);
}

// ── filing an appeal ────────────────────────────────────────────────────
{
  const w = world({ claims: [{ id: 'C1', amount: 400, status: 'denied', denial_reason: 'x' }],
    mode: 'appeal', claimId: 'C1', fields: { 'cam-basis': '   ', 'cam-level': 'first_level', 'cam-deadline': '2026-07-01' } });
  run(w).confirmClaimAction();
  check('an appeal with no basis is refused rather than filed', w.written.length, 0);
  check('and the user is told why', /an appeal with no basis is not a filing/.test(w.toasts[0] || ''), true);
}
{
  const w = world({ claims: [{ id: 'C1', amount: 400, status: 'denied', denial_reason: 'x' }],
    mode: 'appeal', claimId: 'C1',
    fields: { 'cam-basis': 'Authorization 44821 was on file', 'cam-level': 'fair_hearing', 'cam-deadline': '2026-07-01' } });
  run(w).confirmClaimAction();
  check('a filed appeal sets the status, the level, the filing date and the deadline',
    [w.written[0].patch.status, w.written[0].patch.appeal.level, w.written[0].patch.appeal.filed_on, w.written[0].patch.appeal_deadline],
    ['appealed', 'fair_hearing', '2026-06-15', '2026-07-01']);
}

// ── the payload-size guard ──────────────────────────────────────────────
// sen_claims carries a 64KB per-claim CHECK constraint. A pasted denial
// letter in the basis field is how a row crosses it, and the write would 400
// while the claim still looked saved locally.
{
  const w = world({ claims: [{ id: 'C1', status: 'denied', denial_reason: 'x' }], mode: 'appeal', claimId: 'C1',
    fields: { 'cam-basis': 'y'.repeat(5000), 'cam-level': 'other', 'cam-deadline': '' } });
  const api = run(w);
  api.confirmClaimAction();
  check('the appeal basis is capped at 1000 characters before it is stored',
    w.written[0].patch.appeal.basis.length, 1000);
  check('and camTrim also trims, not just truncates', api.camTrim('  hi  ', 100), 'hi');
}
{
  const w = world({ claims: [{ id: 'C1', status: 'submitted' }], mode: 'deny', claimId: 'C1',
    fields: { 'cam-reason': 'z'.repeat(900), 'cam-deadline': '2026-07-20' } });
  run(w).confirmClaimAction();
  check('a denial reason is capped at 300 and the deadline is stored alongside it',
    [w.written[0].patch.denial_reason.length, w.written[0].patch.appeal_deadline], [300, '2026-07-20']);
}

// ── modal field isolation ───────────────────────────────────────────────
{
  const w = world({});
  const api = run(w);
  api.camShow(['cam-basis-row']);
  const shown = ['cam-rate-row', 'cam-reason-row', 'cam-deadline-row', 'cam-level-row', 'cam-basis-row', 'cam-outcome-note-row']
    .filter(r => w.els[r] && w.els[r].style.display === 'block');
  check('camShow shows exactly the requested row and hides every other one', shown, ['cam-basis-row']);
}

// ── THE COUNTING TRAP: a won appeal must not vanish from the history ────
{
  const claims = [
    // won, and since paid -- current status `paid`
    { id: 'A', amount: 500, status: 'paid', denial_reason: 'Missing authorization', appeal: { filed_on: '2026-05-01', outcome: 'overturned' } },
    // won, awaiting payment -- current status `submitted`
    { id: 'B', amount: 300, status: 'submitted', denial_reason: 'Missing authorization', appeal: { filed_on: '2026-05-02', outcome: 'overturned' } },
    // lost -- current status `appeal_denied`
    { id: 'C', amount: 200, status: 'appeal_denied', denial_reason: 'Missing authorization', appeal: { filed_on: '2026-05-03', outcome: 'upheld' } },
    // filed, undecided
    { id: 'D', amount: 100, status: 'appealed', denial_reason: 'Duplicate claim', appeal: { filed_on: '2026-06-10', outcome: null } },
    // denied, never appealed
    { id: 'E', amount: 700, status: 'denied', denial_reason: 'Duplicate claim' }
  ];
  const f = run(world({ claims })).computeAppealOutcomeFindings();
  check('every claim that was ever denied is counted, whatever its status is now',
    f.denied_ever_count, 5);
  check('and all four filed appeals are in the history, including the two that were WON and are no longer `denied`',
    f.appealed_claim_count, 4);
  check('decided means overturned or upheld -- the pending one is excluded',
    [f.decided_count, f.overturned_count], [3, 2]);
  check('the overturn rate is over DECIDED appeals, so a new filing cannot lower it',
    f.overturn_rate_of_decided, 66.7);
  check('only the overturned-and-paid claim counts as money recovered', f.amount_recovered_and_paid, 500);
  const auth = f.by_reason.find(r => r.reason === 'Missing authorization');
  check('the busiest denial reason leads the breakdown', f.by_reason[0].reason, 'Missing authorization');
  check('and it reports appealed/overturned/upheld/pending separately',
    [auth.appealed, auth.overturned, auth.upheld, auth.pending], [3, 2, 1, 0]);
  check('with dollars appealed and dollars actually recovered kept apart',
    [auth.amount_appealed, auth.amount_recovered], [1000, 500]);
  const dup = f.by_reason.find(r => r.reason === 'Duplicate claim');
  check('a reason with only a pending appeal has NO overturn rate rather than a zero',
    [dup.pending, dup.overturn_rate_of_decided], [1, null]);
}

// ── an empty history is not a finding that appeals do not work ──────────
{
  const f = run(world({ claims: [{ id: 'E', amount: 700, status: 'denied', denial_reason: 'Duplicate claim' }] })).computeAppealOutcomeFindings();
  check('with nothing appealed yet it returns a note, not an empty breakdown',
    [f.appealed_claim_count, f.by_reason], [0, undefined]);
  check('and the note says explicitly that this is not evidence against appealing',
    /not a finding that appeals do not work/.test(f.note), true);
}

// ── deadlines: only ever the ones the agency entered ────────────────────
{
  const claims = [
    { id: 'A', amount: 100, status: 'denied', denial_reason: 'r1', appeal_deadline: '2026-06-20' },  // 5 days
    { id: 'B', amount: 200, status: 'denied', denial_reason: 'r2', appeal_deadline: '2026-06-10' },  // passed
    { id: 'C', amount: 300, status: 'denied', denial_reason: 'r3', appeal_deadline: '2026-09-01' },  // far off
    { id: 'D', amount: 400, status: 'denied', denial_reason: 'r4' },                                  // none entered
    { id: 'E', amount: 500, status: 'appealed', denial_reason: 'r5', appeal_deadline: '2026-06-16', appeal: { filed_on: '2026-06-01' } }
  ];
  const f = run(world({ claims })).computeAppealDeadlineFindings();
  check('only claims still sitting at `denied` are counted -- one already appealed is not chased',
    f.denied_open_count, 4);
  check('a denied claim with no deadline is counted separately, never given an assumed window',
    f.without_recorded_deadline, 1);
  check('the closing list is soonest-first and includes one already past',
    f.closing_within_14_days.map(x => [x.appeal_deadline, x.days_left]), [['2026-06-10', -5], ['2026-06-20', 5]]);
  check('a deadline outside the window is not listed',
    f.closing_within_14_days.some(x => x.appeal_deadline === '2026-09-01'), false);
  check('and the note states that nothing is assumed', /is NOT given an assumed window/.test(f.note), true);
  check('senAppealDaysLeft returns null rather than 0 when no deadline was entered',
    run(world({})).senAppealDaysLeft({ status: 'denied' }), null);
}

// ── the role gate holds on all three ────────────────────────────────────
{
  const w = world({ management: false, claims: [{ id: 'A', status: 'denied', denial_reason: 'r', appeal_deadline: '2026-06-20' }] });
  const api = run(w);
  check('a non-management role gets null from the appeal analyses, same gate as the panel',
    [api.computeAppealOutcomeFindings(), api.computeAppealDeadlineFindings()], [null, null]);
}

// ── the table: denied is no longer a dead end ───────────────────────────
{
  const w = world({ claims: [
    { id: 'A', client_name: 'Ada', amount: 100, status: 'denied', denial_reason: 'r', appeal_deadline: '2026-06-20' },
    { id: 'B', client_name: 'Ben', amount: 200, status: 'denied', denial_reason: 'r' },
    { id: 'C', client_name: 'Cy', amount: 300, status: 'denied', denial_reason: 'r', appeal_deadline: '2026-06-01' },
    { id: 'D', client_name: 'Dee', amount: 400, status: 'appealed', denial_reason: 'r', appeal: { filed_on: '2026-06-02', outcome: null } },
    { id: 'E', client_name: 'Eve', amount: 500, status: 'appeal_denied', denial_reason: 'r', appeal: { filed_on: '2026-05-02', outcome: 'upheld' } }
  ] });
  run(w).renderClaimsTable();
  const h = w.els['bl-claimstbody'].innerHTML;
  check('a denied claim offers an Appeal action', /blStartAppeal\('A'\)/.test(h), true);
  check('an appealed claim offers both outcomes',
    [/blAppealOverturned\('D'\)/.test(h), /blAppealUpheld\('D'\)/.test(h)], [true, true]);
  check('an entered deadline is shown as a countdown', /Appeal by 2026-06-20 -- 5d left/.test(h), true);
  check('a passed deadline says so rather than showing a negative count',
    /Appeal deadline passed 14d ago/.test(h), true);
  check('a denied claim with no deadline says none is recorded rather than showing nothing',
    /No appeal deadline recorded/.test(h), true);
  check('an appealed claim shows when it was filed', /Appeal filed 2026-06-02/.test(h), true);
  check('appeal_denied renders as readable text, not a raw enum', /appeal denied/.test(h), true);
  check('and an upheld outcome is visible on the row', /Appeal filed 2026-05-02 -- upheld/.test(h), true);
}

// ── the KPI row ─────────────────────────────────────────────────────────
{
  const w = world({ claims: [
    { id: 'A', amount: 500, status: 'paid', denial_reason: 'r', appeal: { filed_on: '2026-05-01', outcome: 'overturned' } },
    { id: 'B', amount: 300, status: 'appealed', denial_reason: 'r', appeal: { filed_on: '2026-06-01' } },
    { id: 'C', amount: 200, status: 'denied', denial_reason: 'r' }
  ] });
  run(w).blRenderKpis();
  const h = w.els['bl-kpi-row'].innerHTML;
  check('the KPI row reports claims under appeal',
    h.indexOf('Under Appeal</div><div class="kval">1</div>') !== -1, true);
  check('and recovery is the paid-and-overturned figure only',
    h.indexOf('Recovered by Appeal</div><div class="kval">$500</div>') !== -1, true);
  check('the recovery tile says what it counts, so the number cannot be read as won-appeals',
    /Appealed, overturned, and since paid/.test(h), true);
}

// ── the AI tool must expose all three, under the same gate ──────────────
check('get_ops_attention returns the two new analyses alongside the existing ones',
  [/appeal_outcomes:computeAppealOutcomeFindings\(\)/.test(src), /appeal_deadlines:computeAppealDeadlineFindings\(\)/.test(src)],
  [true, true]);
check('and its description forbids inventing an appeal window',
  /never state or estimate one/.test(src), true);
check('and forbids reading an empty appeal history as evidence against appealing',
  /that is an empty history, NOT evidence that appeals do not work/.test(src), true);

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
