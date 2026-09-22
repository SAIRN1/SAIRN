// api/_lib/sairncode-kx-accumulator.js
// ---------------------------------------------------------------------------
// MEDICARE OUTPATIENT-THERAPY KX THRESHOLD: THE PER-BENEFICIARY, PER-YEAR
// ACCUMULATOR. Pure -- no I/O, no fetch, no LLM. Same functional-core split as
// api/_lib/dnt-rollup.js and api/_lib/law-trust-reconcile.js: the gate, the
// read and the 503 live in the caller; this file takes rows that have already
// been authorised and returns numbers.
//
// ── THE GAP THIS CLOSES, MEASURED BEFORE IT WAS BUILT ─────────────────────
// SAIRNcode's KX RULES were already correct and primary-sourced: CMS
// Transmittal R13437CP (CR 14252, eff. 2026-01-01), $2,480 for PT and SLP
// COMBINED and $2,480 for OT separately, with the $3,000 targeted-medical-
// review threshold handled as a note rather than a modifier change. Two panels
// implement them.
//
// THE NUMBER THEY COMPARED AGAINST WAS TYPED INTO A TEXT BOX.
// `sairncode.html` has `<input id="pt-ytd" placeholder="PT+SLP $ year-to-date">`
// and `<input id="mr-kx-ytd" placeholder="Beneficiary year-to-date $">`. A
// coder who types 2400 gets a clean "KX not required" with nothing behind it,
// and the app has no way to know the figure was a guess. That is the
// fabricated-input shape one level below the fabricated-KPI rule: the function
// is real, the rule is real, and the argument is invented at the keyboard.
//
// ── WHY BEING WRONG IS NOT SYMMETRIC, WHICH DECIDES EVERY RULE BELOW ──────
//   UNDERSTATE the year-to-date figure -> KX omitted where it was required ->
//   the claim is DENIED. Annoying, visible, and resubmittable.
//
//   OVERSTATE it -> KX applied where it was NOT required -> an ATTESTATION OF
//   MEDICAL NECESSITY the record may not support, submitted to Medicare.
//
// The second is a false-claims exposure and the first is a rejection letter.
// So every judgement in this file leans the same way: when the data does not
// support a figure, the figure comes out LOW and says so, and the answer is
// never "KX not required" -- it is "below the threshold ON THE ROWS THIS
// SYSTEM HOLDS". Those are different sentences and only one of them is true.
//
// ── FOUR RULES, AND THEY ARE THE SAME FOUR dnt-rollup.js ARGUED FOR ───────
//
// 1. A ROW WITH NO BENEFICIARY KEY IS ITS OWN BUCKET. Never folded into a
//    beneficiary, never dropped. Folding invents therapy dollars on somebody's
//    threshold; dropping makes the per-beneficiary figures sum to less than the
//    practice's real total with nothing saying so.
//
//    AND IT IS NEVER NAME-MATCHED. `sc_claims.patient` is a free-text name.
//    Accumulating on it is the client-multiplicity defect this platform has
//    already found in StoneDesk (`j.customer.toLowerCase()===n`, no FK) and
//    SAIRNvet (`owner` is a typed last name) -- and HERE the consequence is
//    not a merged contact card, it is one patient's therapy dollars counted
//    against another patient's federal threshold, in both directions at once.
//    Identity comes from `beneficiary_id` or the row is unattributed.
//
// 2. ALLOWED IS NOT BILLED, AND A BILLED-ONLY ROW IS NOT ACCUMULATED. The
//    statute counts ALLOWED charges. Submitted charges are routinely multiples
//    of the allowed amount, so accumulating `amount` would push a beneficiary
//    over the threshold long before Medicare does -- the OVERSTATE direction,
//    which is the false-attestation one. A row with no `allowed_amount` is
//    counted in `excluded.no_allowed`, reported, and left out of the total.
//
// 3. AN EXCLUDED ROW MAKES THE TOTAL A FLOOR, AND THE FLOOR IS LABELLED. If
//    anything about a beneficiary's year could not be read, `is_floor` is true
//    and the verdict below the threshold becomes BELOW_ON_RECORDED rather than
//    BELOW. A caller that renders those two the same way has undone this file.
//
// 4. EVERY FIGURE CARRIES ITS ROW COUNT. A total nobody can trace back to a
//    population is a total nobody can check.
//
// ── PT AND SLP SHARE ONE BUCKET; OT HAS ITS OWN ──────────────────────────
// Straight from the transmittal, and it is the part most often got wrong: it
// is not three thresholds and not one. `DISCIPLINE_BUCKET` is the only place
// that mapping exists.
//
// ── THRESHOLDS ARE KEYED BY YEAR AND AN UNKNOWN YEAR IS A REFUSAL ────────
// The amounts update annually by the Medicare Economic Index under §1833(g).
// `sairncode.html` carried `KX_THRESHOLD_2026` -- a constant named for one year
// with nothing to flag it stale when CY2027 arrives. Defaulting an unknown year
// to the most recent figure would silently price 2027 services against 2026
// amounts and report it as a normal answer. `year_known:false` and null
// thresholds is the honest output, and the caller must not render a verdict.
//
// MONEY IS INTEGER CENTS. Same reasoning as api/_lib/law-trust-reconcile.js:
// two independently-computed values under individually legitimate rounding
// conventions produce a real systematic difference at scale, and an accumulator
// whose own arithmetic drifts manufactures the crossings it exists to detect.
// ---------------------------------------------------------------------------

'use strict';

// Rows with no `beneficiary_id`. Its own bucket, never a beneficiary.
const UNATTRIBUTED = '__unattributed__';

// PT and SLP COMBINED, OT SEPARATE. The one place this mapping lives.
const DISCIPLINE_BUCKET = { PT: 'pt_slp', SLP: 'pt_slp', OT: 'ot' };

// Per-year, in integer cents. A year absent from this table is NOT defaulted.
// Source: CMS Transmittal R13437CP (CR 14252, effective 1 January 2026),
// 2026 Annual Update of Per-Beneficiary Threshold Amounts. The MR threshold is
// §1833(g)(7)(B) as added by BBA 2018 §50202.
const THRESHOLDS_BY_YEAR = {
  2026: { pt_slp: 248000, ot: 248000, mr: 300000 },
};

/** Money to integer cents, or null when the value is not money at all.
 *  null is NOT 0 -- a figure that cannot be read is a figure that cannot be
 *  accumulated, and calling it zero is the silent-omission shape rule 2 is
 *  about. Negative is also null: an allowed amount below zero is an
 *  adjustment this file has no rule for, and guessing at one would move a
 *  federal threshold. */
function cents(v) {
  if (v === undefined || v === null) return null;
  if (typeof v === 'string' && v.trim() === '') return null;
  const n = typeof v === 'number' ? v : Number(String(v).trim());
  if (!Number.isFinite(n) || n < 0) return null;
  return Math.round(n * 100);
}

/** The four-digit year of a YYYY-MM-DD date, or null.
 *  STRICT ON PURPOSE, and the precedent is named: api/_lib/credential-expiry.js
 *  records that `new Date` does not reject an impossible date, it SILENTLY
 *  REPAIRS IT -- so `2026-02-31` becomes March and a service moves between
 *  calendar years. A threshold is annual; the year is the bucket. */
function yearOf(v) {
  if (typeof v !== 'string') return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v.trim());
  if (!m) return null;
  const y = Number(m[1]), mo = Number(m[2]), d = Number(m[3]);
  const dt = new Date(Date.UTC(y, mo - 1, d));
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1
      || dt.getUTCDate() !== d) return null;
  return y;
}

function normaliseDiscipline(v) {
  const s = String(v === undefined || v === null ? '' : v).trim().toUpperCase();
  return Object.prototype.hasOwnProperty.call(DISCIPLINE_BUCKET, s) ? s : null;
}

function beneficiaryKey(row) {
  const raw = row && row.beneficiary_id;
  const s = (typeof raw === 'string') ? raw.trim() : '';
  return s === '' ? null : s;
}

/**
 * @param {object} input
 *   rows  {Array}  sc_claims rows as the server holds them. A row participates
 *                  only if it carries a `discipline` this file recognises --
 *                  every other claim in the register is simply not a therapy
 *                  service and is counted in `not_therapy`, not in `excluded`.
 *   year  {number} the calendar year being accumulated.
 * @returns {object} see the module header. Never throws on bad input rows;
 *   a row it cannot read is a counted exclusion, because throwing would take
 *   the whole practice's figure out over one malformed record.
 */
function accumulateTherapy(input) {
  const rows = (input && Array.isArray(input.rows)) ? input.rows : [];
  const year = (input && Number.isInteger(input.year)) ? input.year : null;
  const th = (year !== null
    && Object.prototype.hasOwnProperty.call(THRESHOLDS_BY_YEAR, year))
    ? THRESHOLDS_BY_YEAR[year] : null;

  const excluded = {
    no_allowed: 0, no_discipline: 0, no_date: 0, wrong_year: 0, no_beneficiary: 0,
  };
  let notTherapy = 0;
  const byBen = Object.create(null);
  const unattributed = { pt_slp_cents: 0, ot_cents: 0, rows: 0 };

  const bucketFor = (key) => {
    if (!byBen[key]) {
      byBen[key] = {
        beneficiary_id: key,
        pt_slp_cents: 0, ot_cents: 0,
        rows_counted: 0, rows_excluded: 0,
      };
    }
    return byBen[key];
  };

  rows.forEach((row) => {
    const disc = normaliseDiscipline(row && row.discipline);
    if (disc === null) {
      // NOT AN EXCLUSION. A dental claim in the register is not a therapy row
      // that failed to parse, and counting it as one would make every practice
      // look like it had lost most of its therapy data.
      notTherapy += 1;
      return;
    }
    const key = beneficiaryKey(row);
    const y = yearOf(row && row.date);
    const c = cents(row && row.allowed_amount);

    // ORDER MATTERS AND IS DELIBERATE: a row is attributed to exactly one
    // exclusion reason, the FIRST one that applies, so the counts sum to the
    // number of rows and a reader can add them up. Counting a row under every
    // reason it fails would make the tally larger than the population.
    if (y === null) { excluded.no_date += 1; if (key) bucketFor(key).rows_excluded += 1; return; }
    if (year !== null && y !== year) { excluded.wrong_year += 1; return; }
    if (c === null) { excluded.no_allowed += 1; if (key) bucketFor(key).rows_excluded += 1; return; }
    if (key === null) {
      // Rule 1. Counted, reported, and NEVER attached to a name.
      excluded.no_beneficiary += 1;
      unattributed[DISCIPLINE_BUCKET[disc] + '_cents'] += c;
      unattributed.rows += 1;
      return;
    }
    const b = bucketFor(key);
    b[DISCIPLINE_BUCKET[disc] + '_cents'] += c;
    b.rows_counted += 1;
  });

  // ── THE VERDICT PER BUCKET, AND THE THREE-STATE ANSWER ────────────────
  // AT_OR_OVER  the recorded total has reached the threshold. Safe to state
  //             regardless of missing rows: a floor that has crossed has
  //             crossed, and more rows can only push it further over.
  // BELOW       under the threshold, and NOTHING about this beneficiary's
  //             year was excluded, so the figure is a real total.
  // BELOW_ON_RECORDED  under the threshold on what is held, with rows missing.
  //             This is NOT "KX not required" and a caller that renders it as
  //             such has undone rule 3.
  // UNKNOWN_YEAR  no threshold on file for this year. No verdict at all.
  const verdict = (amountCents, limitCents, isFloor) => {
    if (limitCents === null || limitCents === undefined) return 'UNKNOWN_YEAR';
    if (amountCents >= limitCents) return 'AT_OR_OVER';
    return isFloor ? 'BELOW_ON_RECORDED' : 'BELOW';
  };

  const beneficiaries = Object.keys(byBen).sort().map((k) => {
    const b = byBen[k];
    const isFloor = b.rows_excluded > 0;
    return {
      beneficiary_id: b.beneficiary_id,
      pt_slp_cents: b.pt_slp_cents,
      ot_cents: b.ot_cents,
      rows_counted: b.rows_counted,
      rows_excluded: b.rows_excluded,
      // Rule 3. The single field a caller must branch on before writing any
      // sentence containing the words "not required".
      is_floor: isFloor,
      kx: {
        pt_slp: verdict(b.pt_slp_cents, th && th.pt_slp, isFloor),
        ot: verdict(b.ot_cents, th && th.ot, isFloor),
      },
      // The MR threshold is a DOCUMENTATION-REVIEW exposure, not a denial and
      // not a different modifier. Reported beside KX and never merged with it.
      mr: {
        pt_slp: verdict(b.pt_slp_cents, th && th.mr, isFloor),
        ot: verdict(b.ot_cents, th && th.mr, isFloor),
      },
    };
  });

  return {
    year: year,
    year_known: th !== null,
    thresholds_cents: th ? { pt_slp: th.pt_slp, ot: th.ot, mr: th.mr } : null,
    beneficiaries: beneficiaries,
    unattributed: unattributed,
    excluded: excluded,
    not_therapy_rows: notTherapy,
    // Rule 4. Every figure above is traceable to this population.
    total_rows: rows.length,
  };
}

module.exports = {
  accumulateTherapy,
  cents,
  yearOf,
  UNATTRIBUTED,
  DISCIPLINE_BUCKET,
  THRESHOLDS_BY_YEAR,
};
