// tools/invariant_registry.js
// THE LOCKED CLASSIFICATION TABLE, plus the synthetic fixtures the runner must
// satisfy before it may touch a real engine.
//
// ── HOW THIS TABLE WAS DERIVED, AND WHY THE METHOD IS RECORDED ───────────
// BY READING EACH ENGINE'S EXPORTS AND ASSERTING THE INVARIANT BY HAND. Not by
// keyword. That is not a style preference: a keyword pass over `debit|credit`
// produced a FALSE PREMISE hours before this file was written -- it classified
// api/_lib/dental-ledger.js as a double-entry engine on five COMMENT lines
// ("as though the patient were in credit"), and a second assumption about file
// naming reported it as untested when api/sd-data-dental-ledger-validation.js
// covers it 282/282. Both had to be walked back. Every row below carries the
// EXPORT it was read from, so the classification can be checked against the
// engine rather than against this table.
//
// ── ACCURACY IS NOT THE SAME QUESTION AS STABILITY ───────────────────────
// ACCURACY  did this row pick the RIGHT invariant type for this engine? Made
//           checkable by a DISCRIMINATOR -- a predicate over the engine's own
//           output shape that must hold for the declared type. A hand judgement
//           with a mechanical check on it, rather than a one-time opinion.
// STABILITY across generated inputs, how often did the invariant hold?
//           9,999/10,000 is a different finding from 10,000/10,000 and the two
//           must never be collapsed into one PASS.
//
// ── MARGIN APPLIES TO INEQUALITIES ONLY ──────────────────────────────────
// Michael's instruction was to skip margin for double-entry, since sum-to-zero
// is exact. Reading the engines, THE SAME IS TRUE OF ROLLUP: "stated total
// equals the sum of its lines" is an equality, and the distance to violating an
// equality is zero or it is already violated. Margin is meaningful only where
// the invariant is an INEQUALITY -- released <= accrued -- and it is reported
// there and nowhere else, rather than printing a meaningless zero to fill a
// column.
'use strict';

const path = require('path');
const REPO = path.join(__dirname, '..');
const L = (n) => require(path.join(REPO, 'api', '_lib', n));

// ── deterministic generator: no Math.random, so a failing case is reproducible
function rng(seed) {
  let s = seed >>> 0;
  return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}
function money(r, max) { return Math.round(r() * max * 100) / 100; }

const REGISTRY = [
  {
    id: 'ledger.validateEntry',
    engine: 'api/_lib/ledger.js',
    type: 'DOUBLE-ENTRY',
    evidence: 'read from exports: validateEntry() computes `debits` and `credits` by ' +
      'reduce over the lines and sets balanced = (debits === credits && debits > 0); ' +
      'trialBalance() totals both sides independently.',
    // The declared type must be visible in the engine's own OUTPUT, or the
    // classification is a claim about nothing.
    // READ FROM A REAL CALL, not guessed: validateEntry() returns
    // debit_total / credit_total / difference. My first draft asserted
    // `debits_cents` and got `undefined === undefined` -> TRUE on every case,
    // a VACUOUS 2000/2000. The ACCURACY field caught it while STABILITY read
    // perfect, which is the entire reason the two are reported separately.
    // READS THE CENTS, NOT THE DISPLAY FLOATS (2026-09-13). The float fields
    // have been through money(), and comparing them is what led me to report
    // this engine as a float `===` with no tolerance band. It was never that:
    // the balance decision is `debits === credits` on integer cents and always
    // has been. The engine was exact; only its OUTPUT was lossy.
    discriminator: (out) => out && Number.isInteger(out.debit_total_cents) &&
      Number.isInteger(out.credit_total_cents),
    gen: (r) => {
      const n = 2 + Math.floor(r() * 3);
      const lines = [];
      let owed = 0;
      for (let i = 0; i < n - 1; i++) {
        const amt = money(r, 500) + 0.01;
        owed += Math.round(amt * 100);
        lines.push({ account_code: '1000', debit: amt, credit: 0, memo: 'd' });
      }
      lines.push({ account_code: '4000', debit: 0, credit: Math.round(owed) / 100, memo: 'c' });
      return { today: '2026-09-13',
               entry: { entry_date: '2026-09-13', memo: 'generated', lines: lines } };
    },
    run: (input) => {
      const out = L('ledger.js').validateEntry(input);
      return { debit_total_cents: out.debit_total_cents,
               credit_total_cents: out.credit_total_cents,
               difference_cents: out.difference_cents,
               balanced: out.balanced, raw: out };
    },
    holds: (o) => Number.isInteger(o.debit_total_cents) &&
                  Number.isInteger(o.credit_total_cents) &&
                  o.debit_total_cents === o.credit_total_cents,
    // ── EXACT INTEGER CENTS, SO THE MARGIN IS WHOLE CENTS OF IMBALANCE ──
    // CORRECTED 2026-09-13. This previously read "exact === on FLOATS, which is
    // itself the finding" and recommended moving the engine to integer cents.
    // The engine was ALREADY integer cents -- `balanced` is `debits === credits`
    // on values from Math.round(v*100). I had been reading debit_total, a
    // display float produced by money(), and drew a conclusion about the check
    // from the shape of its output.
    //
    // The margin is therefore real and in whole cents: how far from balanced
    // this entry came. 0 means exactly balanced; any non-zero value means the
    // entry is already refused. The alarm sits at 1 cent -- the smallest
    // representable step -- because on an exact integer check there is no
    // fractional drift to detect before failure, and pretending otherwise
    // would be a fabricated band.
    // SIGN CONVENTION, and the first version got it wrong in a way worth
    // recording: margin is HEADROOM, so positive is safe and the alarm fires
    // BELOW it. With alarmAt() returning 1, every perfectly balanced entry
    // (margin 0) counted as inside the band -- 2000 of 2000 runs alarmed on
    // entries that were exactly correct. An alarm that fires on every healthy
    // case is the margin-column version of a banner that always shouts.
    //
    // alarmAt is 0 here, so the band fires only on a real imbalance. THAT MEANS
    // ZERO ALARMS IS THE EXPECTED OUTPUT, NOT A CLEAN BILL OF HEALTH: an exact
    // integer check has no pre-failure band by construction, and there is no
    // drift to detect before failure. The number is reported so the difference
    // between "no drift" and "no band to drift in" stays visible.
    margin: (o) => -Math.abs(Number(o.difference_cents) || 0),
    alarmAt: () => 0
  },
  {
    id: 'roofing-billing.computeTotals',
    engine: 'api/_lib/roofing-billing.js',
    type: 'ROLLUP',
    evidence: 'read from exports: normalizeLineItems() + computeTotals() -- a stated ' +
      'invoice total derived from its line items, with summarizeInvoice() reading it back.',
    discriminator: (out) => out && typeof out.stated === 'number' &&
      typeof out.computed === 'number',
    gen: (r) => {
      const n = 1 + Math.floor(r() * 5);
      const items = [];
      for (let i = 0; i < n; i++) {
        items.push({ description: 'item ' + i, quantity: 1 + Math.floor(r() * 4),
                     unit_price: money(r, 900) + 0.01 });
      }
      return { line_items: items, tax_rate: Math.round(r() * 1000) / 10000 };
    },
    run: (input) => {
      // POSITIONAL ARGUMENTS, read from the real signature:
      // computeTotals(lineItems, taxRate, taxAmount). My first draft passed an
      // OPTIONS OBJECT, which normalizeLineItems() read as zero lines -- so it
      // returned subtotal 0 against a real computed sum and reported 0/2000.
      // TYPE CONFIRMED with 0% stability: the accuracy half was right and the
      // adapter was wrong, which is the other direction the split distinguishes.
      const B = L('roofing-billing.js');
      const lines = B.normalizeLineItems(input.line_items);
      const t = B.computeTotals(input.line_items, input.tax_rate);
      const computed = lines.reduce(function (s, l) { return s + Number(l.amount || 0); }, 0);
      return { stated: Math.round(Number(t.subtotal || 0) * 100) / 100,
               computed: Math.round(computed * 100) / 100, raw: t };
    },
    holds: (o) => Math.abs(o.stated - o.computed) < 0.005,
    // ── CORRECTED 2026-09-13: I SAID THIS HAD NO MARGIN AND I WAS WRONG ──
    // The earlier note read "also an equality", and that was right about the
    // MATHEMATICS and wrong about the IMPLEMENTATION. `stated == sum of lines`
    // is an equality on paper; in code it is `|stated - computed| < 0.005`, and
    // that 0.005 is a real tolerance band with real headroom. The margin is how
    // much of the band is unused.
    //
    // ALARM AT 20% OF THE BAND -- tighter than the violation point of 0, per
    // docs/2026-09-13-cross-domain-disciplines.md item 4. A rollup drifting to
    // within a fifth of a cent of its own tolerance is a finding before it is a
    // failure.
    margin: (o) => 0.005 - Math.abs(o.stated - o.computed),
    alarmAt: () => 0.001
  },
  {
    id: 'wip-accounting.jobWip',
    engine: 'api/_lib/wip-accounting.js',
    type: 'CONSERVATION',
    evidence: 'read from exports: jobWip() returns retainage_held alongside ' +
      'retainage_released and the accrued figure; the identity is held = accrued - ' +
      'released, and released must never exceed accrued. An INEQUALITY -- the only ' +
      'one of the four, though all four now report a margin: the other three ' +
      'are equalities in the MATHEMATICS and tolerance bands in the CODE.',
    discriminator: (out) => out && typeof out.accrued === 'number' &&
      typeof out.released === 'number',
    gen: (r) => {
      const n = 1 + Math.floor(r() * 4);
      const draws = [];
      for (let i = 0; i < n; i++) {
        draws.push({ draw_id: 'D' + i, job_id: 'J1', amount: money(r, 50000) + 1,
                     retainage_pct: Math.floor(r() * 15), pct_complete: Math.floor(r() * 100),
                     period_end: '2026-08-0' + (1 + (i % 9)),
                     status: r() > 0.5 ? 'paid' : 'submitted' });
      }
      return { job: { job_id: 'J1', contract_value: 100000 }, draws: draws,
               today: '2026-09-13' };
    },
    run: (input) => {
      const w = L('wip-accounting.js').jobWip(input);
      return { accrued: Number(w.retainage_accrued || w.retainage_held || 0)
                        + Number(w.retainage_released || 0),
               released: Number(w.retainage_released || 0),
               held: Number(w.retainage_held || 0), raw: w };
    },
    holds: (o) => o.released <= o.accrued + 0.005,
    // MARGIN, and the ALARM IS SET TIGHTER THAN THE FAILURE POINT. Violation is
    // released > accrued, i.e. margin < 0. The alarm fires at 1% of accrued --
    // a run that came within a penny of going negative is a finding even though
    // it did not violate anything.
    margin: (o) => o.accrued - o.released,
    alarmAt: (o) => 0.01 * Math.max(o.accrued, 1)
  },
  {
    id: 'care-charges.reconcileAgainstInvoice',
    engine: 'api/_lib/care-charges.js',
    type: 'CONSERVATION',
    evidence: 'read from the function body: the returned delta is ' +
      'sum(added.amount) - sum(removed.amount) + sum(changed.to - changed.from). ' +
      'The stated delta must equal its three components.',
    discriminator: (out) => out && typeof out.stated === 'number' &&
      typeof out.computed === 'number',
    gen: (r) => {
      const mk = (n, f) => { const a = []; for (let i = 0; i < n; i++) a.push(f(i)); return a; };
      return {
        derived: mk(1 + Math.floor(r() * 3),
                    (i) => ({ code: 'A' + i, amount: money(r, 300) + 0.01 })),
        invoice: { lines: mk(1 + Math.floor(r() * 3),
                             (i) => ({ code: 'A' + i, amount: money(r, 300) + 0.01 })) }
      };
    },
    run: (input) => {
      const C = L('care-charges.js');
      const out = C.reconcileAgainstInvoice(input);
      const add = (out.added || []).reduce((s, l) => s + Number(l.amount || 0), 0);
      const rem = (out.removed || []).reduce((s, l) => s + Number(l.amount || 0), 0);
      const chg = (out.changed || []).reduce((s, c) => s + (Number(c.to || 0) - Number(c.from || 0)), 0);
      return { stated: Math.round(Number(out.delta || 0) * 100) / 100,
               computed: Math.round((add - rem + chg) * 100) / 100, raw: out };
    },
    holds: (o) => Math.abs(o.stated - o.computed) < 0.005,
    // Same correction as the rollup row above: the identity is an equality, the
    // CHECK is a 0.005 tolerance, and the unused part of that tolerance is a
    // real margin.
    margin: (o) => 0.005 - Math.abs(o.stated - o.computed),
    alarmAt: () => 0.001
  }
];

// ── SYNTHETIC FIXTURES: hand-decided, and the runner refuses to touch a real
// ── engine until all of them classify as written.
// FIELD NAMES CORRECTED 2026-09-13, declared rather than quiet: these said
// debits_cents/credits_cents, guessed rather than read. validateEntry()
// actually returns debit_total/credit_total, and the guess made `holds` compare
// undefined with undefined -- TRUE on every case, a vacuous 2000/2000. THE LOCK
// THEN CAUGHT THE CORRECTION ITSELF: renaming the fields in `holds` broke the
// balanced-posting CONTROL until the fixtures were brought to the real names.
// That is the criteria being corrected to match the ENGINE, not loosened to
// match a result -- the distinction this file exists to keep visible.
const FIXTURES = [
  // MOVED TO CENTS 2026-09-13 when the criteria did, and the LOCK CAUGHT IT --
  // the balanced-posting CONTROL went red the moment `holds` started reading
  // debit_total_cents, before a single engine was called. Third time the lock
  // has stopped a field change from being measured against stale fixtures.
  { name: 'a deliberately UNBALANCED posting is caught',
    type: 'DOUBLE-ENTRY', holds: REGISTRY[0].holds,
    input: { debit_total_cents: 10000, credit_total_cents: 9900 }, expect: false },
  { name: 'CONTROL: a balanced posting passes',
    type: 'DOUBLE-ENTRY', holds: REGISTRY[0].holds,
    input: { debit_total_cents: 10000, credit_total_cents: 10000 }, expect: true },
  { name: 'a posting with NO totals at all is caught, not read as balanced',
    type: 'DOUBLE-ENTRY', holds: REGISTRY[0].holds,
    input: {}, expect: false },
  { name: 'a FLOAT total is refused -- a value that has been through money() is not the exact one',
    type: 'DOUBLE-ENTRY', holds: REGISTRY[0].holds,
    input: { debit_total_cents: 100.5, credit_total_cents: 100.5 }, expect: false },
  { name: 'a rollup whose stated total does not match its lines is caught',
    type: 'ROLLUP', holds: REGISTRY[1].holds,
    input: { stated: 100.00, computed: 99.99 }, expect: false },
  { name: 'CONTROL: a rollup that matches to the cent passes',
    type: 'ROLLUP', holds: REGISTRY[1].holds,
    input: { stated: 100.00, computed: 100.00 }, expect: true },
  { name: 'conservation: releasing MORE than was ever accrued is caught',
    type: 'CONSERVATION', holds: REGISTRY[2].holds,
    input: { accrued: 1000, released: 1000.01 }, expect: false },
  { name: 'CONTROL: releasing exactly what was accrued passes',
    type: 'CONSERVATION', holds: REGISTRY[2].holds,
    input: { accrued: 1000, released: 1000 }, expect: true },
  { name: 'conservation delta that disagrees with its components is caught',
    type: 'CONSERVATION', holds: REGISTRY[3].holds,
    input: { stated: 50, computed: 49 }, expect: false }
];

// The margin alarm must fire BEFORE the violation point, not at it.
const MARGIN_FIXTURES = [
  { name: 'the alarm fires on a near-miss that has NOT violated anything',
    row: REGISTRY[2], o: { accrued: 1000, released: 999.99 }, expectAlarm: true },
  { name: 'CONTROL: a comfortable margin does not alarm',
    row: REGISTRY[2], o: { accrued: 1000, released: 500 }, expectAlarm: false }
];

module.exports = { REGISTRY, FIXTURES, MARGIN_FIXTURES, rng, VERSION: '2026-09-13.1' };
