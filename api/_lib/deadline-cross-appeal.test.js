// The four cross-appeal rows -- their later_of arithmetic AND their multi-slot
// trigger-document guard.
//
// WHY THIS FILE EXISTS AT ALL. Before 2026-09-02 these four rows were LIVE and
// had ZERO test coverage: no suite referenced any of the four rule ids or any
// of their trigger spec ids. They were not broken by the discriminator work,
// and the reason was simply that nothing was testing them. That gap is closed
// here independently of the guard, because the arithmetic is worth asserting
// whether or not the guard exists.
//
// BOTH MULTI-TRIGGER MECHANISMS ARE EXERCISED, and they are genuinely
// different:
//   resolve_periods  each limb has its OWN count; each period is computed and
//                    the later RESULT governs.  NY 5513(c), Ohio 4(B)(1),
//                    Tex. 26.1(d).
//   resolve          the limbs share ONE count; the later trigger DATE governs
//                    and one period is computed from it.  FRAP 4(b)(1)(A).
// Each row is asserted with each limb winning in turn, so a bug that always
// picked the first limb, or always picked the longer count, would fail.
//
// THE GUARD'S PLACEMENT IS ASSERTED BY A TEST THAT ACTUALLY DETECTS IT, and
// getting that right took two attempts. resolveTrigger() dispatches a
// resolve_periods spec straight into computeBasePeriod() for every limb, ~40
// lines BEFORE the single-trigger guard runs, so a multi-slot guard placed
// beside its sibling would return the right refusal code having already done
// the arithmetic.
//
// THE OBVIOUS ASSERTION DOES NOT CATCH THAT. "The refusal carries no due_date"
// is true of BOTH placements -- the misplaced guard still returns early, and
// the computed limb dates are simply discarded. Moving the guard in a scratch
// copy and re-running left this file at 78/78, which is precisely the
// broken-but-green shape the whole design was written to avoid.
//
// WHAT DOES CATCH IT is an INCOMPLETE set of limb dates. With one limb's date
// missing, the correctly-placed guard refuses TRIGGER_DOCUMENT_UNCONFIRMED
// because it runs first; the misplaced one refuses INCOMPLETE_TRIGGERS,
// because resolveTrigger got there before it. The two refusals come from the
// two functions whose order is in question, so the assertion is about the
// ordering itself rather than about a symptom of it. Verified against a
// deliberately misplaced copy.

const fs = require('fs');
const path = require('path');
const engine = require('./deadline-engine.js');

const SQL = path.join(__dirname, '..', '..', 'sql');

// Every calendar on disk, because these rows span four jurisdictions whose
// calendars live in four different files -- and two of them (oh, us-federal)
// have no 2026 calendar at all, which is why their cases use 2027.
const calendars = {};
for (const f of fs.readdirSync(SQL)) {
  if (!/^sairnlaw_deadline_calendars_.*\.json$/.test(f)) continue;
  let doc;
  try { doc = JSON.parse(fs.readFileSync(path.join(SQL, f), 'utf8')); } catch (e) { continue; }
  for (const row of (doc.holiday_calendars || [])) {
    calendars[row.jurisdiction] = calendars[row.jurisdiction] || {};
    calendars[row.jurisdiction][String(row.year)] = row.dates;
  }
}

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

const ROWS = {
  ny: { file: 'newyork', jur: 'ny', id: 'ny-cplr-5513c-cross-appeal',
        guarded: 'service_upon_appellant_of_judgment_with_written_notice_of_entry',
        open: 'service_of_the_adverse_partys_notice_of_appeal' },
  oh: { file: 'state_appellate', jur: 'oh', id: 'oh-appr-4B1-cross-appeal',
        guarded: 'entry_of_final_order',
        open: 'filing_of_the_first_notice_of_appeal' },
  tx: { file: 'texas', jur: 'tx', id: 'tx-trap-261d-cross-appeal-ordinary',
        guarded: 'signing_of_the_judgment',
        open: 'filing_of_the_first_notice_of_appeal' },
  fed: { file: 'us_federal', jur: 'us-federal', id: 'frap-4b1A-criminal-notice-of-appeal',
         guarded: 'entry_of_judgment_or_order_being_appealed',
         open: 'filing_of_government_notice_of_appeal' },
};
const seeds = {};
for (const k of Object.keys(ROWS)) {
  seeds[k] = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_' + ROWS[k].file + '.json'), 'utf8'));
}
function ruleOf(k) { return seeds[k].rules.find(r => r.rule_id === ROWS[k].id); }
function confirmFor(k) {
  const o = {}; o[ROWS[k].guarded] = ROWS[k].guarded; return o;
}
function compute(k, dates, extra) {
  const rule = ruleOf(k);
  return engine.computeDeadline(Object.assign({
    jurisdiction: ROWS[k].jur, domain: rule.domain, trigger_event: rule.trigger_event.id,
    trigger_dates: dates, rules: seeds[k].rules, calendars: calendars,
    as_of: Object.values(dates)[0]
  }, extra || {}));
}
const dateOf = r => (r.ok ? r.due_date : 'REFUSED:' + r.code);
function d(k, guardedDate, openDate) {
  const o = {}; o[ROWS[k].guarded] = guardedDate; o[ROWS[k].open] = openDate; return o;
}

// ── The rows are what this file thinks they are ──────────────────────────
for (const k of Object.keys(ROWS)) {
  const r = ruleOf(k);
  check(k + ': the row exists and is appellate', [!!r, r.domain], [true, 'appellate']);
  const t = r.trigger_event;
  const events = t.limbs ? t.limbs.map(L => L.event) : t.events;
  check(k + ': it has exactly two limbs', events.length, 2);
  check(k + ': both the guarded and the unguarded limb are among them',
    [events.includes(ROWS[k].guarded), events.includes(ROWS[k].open)], [true, true]);
  check(k + ': it resolves later_of', t.resolve_periods || t.resolve, 'later_of');
  check(k + ': exactly one limb is guarded, and it is the term of art',
    Object.keys(r.trigger_documents || {}), [ROWS[k].guarded]);
  check(k + ': the guarded limb REFUSES when unconfirmed',
    r.trigger_documents[ROWS[k].guarded].on_unconfirmed, 'refuse');
  check(k + ': the declaration id matches its key',
    r.trigger_documents[ROWS[k].guarded].id, ROWS[k].guarded);
  check(k + ': it carries no singular declaration', r.trigger_document, undefined);
}
check('three rows use resolve_periods and one uses resolve -- both mechanisms are covered',
  Object.keys(ROWS).map(k => ruleOf(k).trigger_event.resolve_periods ? 'periods' : 'dates').sort(),
  ['dates', 'periods', 'periods', 'periods']);

// ── NEW YORK CPLR 5513(c): 10 days from the adverse notice, 30 from service
//    with written notice of entry, later governs ──────────────────────────
// Both served 1 June 2026: 10 days -> Thu 11 June, 30 days -> Wed 1 July.
check('NY: the 30-day limb governs when both dates are the same',
  dateOf(compute('ny', d('ny', '2026-06-01', '2026-06-01'), { trigger_documents: confirmFor('ny') })),
  '2026-07-01');
// Adverse notice served 1 July: 10 days -> Sat 11 July, which rolls to Mon the
// 13th, and that beats the 30-day limb's 1 July.
check('NY: the 10-day limb governs when the adverse notice comes later, and its result rolls off a Saturday',
  dateOf(compute('ny', d('ny', '2026-06-01', '2026-07-01'), { trigger_documents: confirmFor('ny') })),
  '2026-07-13');

// ── OHIO App.R. 4(B)(1): 30 days from entry, 10 from the first notice ─────
// Ohio has no 2026 calendar on this platform, so these use 2027.
check('OH: the 30-day entry limb governs when both dates are the same',
  dateOf(compute('oh', d('oh', '2027-06-01', '2027-06-01'), { trigger_documents: confirmFor('oh') })),
  '2027-07-01');
// First notice filed 25 June 2027: +10 = Mon 5 July, which is the OBSERVED
// Independence Day (4 July 2027 is a Sunday), so it rolls to Tue the 6th --
// and that beats the entry limb's 1 July.
check('OH: the 10-day limb governs when the first notice is later, and rolls off the observed holiday',
  dateOf(compute('oh', d('oh', '2027-06-01', '2027-06-25'), { trigger_documents: confirmFor('oh') })),
  '2027-07-06');

// ── TEXAS 26.1(d): 30 days from signing, 14 from the first notice ────────
check('TX: the 30-day signing limb governs when both dates are the same',
  dateOf(compute('tx', d('tx', '2026-06-01', '2026-06-01'), { trigger_documents: confirmFor('tx') })),
  '2026-07-01');
check('TX: the 14-day limb governs when the first notice is later',
  dateOf(compute('tx', d('tx', '2026-06-01', '2026-06-25'), { trigger_documents: confirmFor('tx') })),
  '2026-07-09');

// ── FRAP 4(b)(1)(A): ONE shared 14-day count, later trigger DATE governs ──
// This is the other mechanism, and the assertion that distinguishes it: the
// answer is the SAME whichever limb carries the later date, because there is
// one count applied to whichever date is later.
check('FED: the later of the two DATES governs -- government notice later',
  dateOf(compute('fed', d('fed', '2027-05-01', '2027-07-01'), { trigger_documents: confirmFor('fed') })),
  '2027-07-15');
check('FED: and the same 14 days run when the ENTRY is the later date',
  dateOf(compute('fed', d('fed', '2027-07-01', '2027-05-01'), { trigger_documents: confirmFor('fed') })),
  '2027-07-15');
check('FED: a nearer pair gives a nearer date, so the count is really being applied',
  dateOf(compute('fed', d('fed', '2027-06-01', '2027-05-01'), { trigger_documents: confirmFor('fed') })),
  '2027-06-15');

// ── The multi-slot guard, on every row ───────────────────────────────────
for (const k of Object.keys(ROWS)) {
  const dates = k === 'ny' ? d('ny', '2026-06-01', '2026-06-01')
    : k === 'tx' ? d('tx', '2026-06-01', '2026-06-01')
    : d(k, '2027-06-01', '2027-06-01');

  const un = compute(k, dates);
  check(k + ': REFUSES when the guarded limb is unconfirmed',
    [un.ok, un.code], [false, 'TRIGGER_DOCUMENT_UNCONFIRMED']);
  check(k + ': and no date rides along with the refusal', un.due_date, undefined);
  // THE ORDERING PROOF. With a limb date missing, whichever of the two
  // functions runs first decides the refusal: the document guard gives
  // TRIGGER_DOCUMENT_UNCONFIRMED, resolveTrigger gives INCOMPLETE_TRIGGERS.
  // Asserting the code here is asserting the order, not a symptom of it.
  const partial = {}; partial[ROWS[k].guarded] = dates[ROWS[k].guarded];
  check(k + ': THE GUARD RUNS BEFORE resolveTrigger -- an incomplete limb set still refuses on the DOCUMENT',
    compute(k, partial).code, 'TRIGGER_DOCUMENT_UNCONFIRMED');
  check(k + ': and with no limb dates at all it is still the document refusal',
    compute(k, {}).code, 'TRIGGER_DOCUMENT_UNCONFIRMED');
  check(k + ': the refusal names the limb it is about', un.limb, ROWS[k].guarded);
  check(k + ': and says a partial answer is not safe under later_of',
    /LATER of its limbs|no partial answer is safe/.test(un.message), true);

  const wrong = {}; wrong[ROWS[k].guarded] = 'some_other_document';
  const mm = compute(k, dates, { trigger_documents: wrong });
  check(k + ': an affirmative WRONG document refuses',
    [mm.ok, mm.code, mm.due_date], [false, 'TRIGGER_DOCUMENT_MISMATCH', undefined]);

  // Confirming the UNGUARDED limb does not satisfy the guarded one.
  const other = {}; other[ROWS[k].open] = ROWS[k].open;
  check(k + ': confirming the unguarded limb does not unlock the guarded one',
    compute(k, dates, { trigger_documents: other }).code, 'TRIGGER_DOCUMENT_UNCONFIRMED');

  const ok = compute(k, dates, { trigger_documents: confirmFor(k) });
  check(k + ': a correct confirmation computes and records the limb as confirmed',
    [ok.ok, ok.trigger_documents[ROWS[k].guarded].state], [true, 'confirmed']);
  check(k + ': and the unguarded limb is absent from the report rather than faked',
    Object.keys(ok.trigger_documents), [ROWS[k].guarded]);
  check(k + ': the singular field stays null on a multi-trigger row', ok.trigger_document, null);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
