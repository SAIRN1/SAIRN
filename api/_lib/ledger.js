// api/_lib/ledger.js
// SHARED double-entry general ledger. Pure functions, no I/O, no app names.
//
// ── WHY A NEW TABLE AND NOT gl_entries ───────────────────────────────────
// Verified 2026-09-02 before writing a line. `gl_entries` exists in the live
// database with debit/credit/account_code/posted columns, and NOTHING WRITES
// IT -- zero references across all of api/ and every *.html, which
// sql/full_crud_truncate_sweep_2026-08-24.sql had already recorded as
// "CONFIRMED unreferenced by any live SAIRN code path". It is not an
// unenforced ledger; it is an empty table with accounting-shaped column names.
//
// It is also not reusable, for two reasons that are not preferences:
//   * IT IS KEYED ON shop_id WITH A FOREIGN KEY TO public.shops. That is the
//     Fabricor/StoneDesk shape. Every B2B app here is licence-keyed and never
//     touches `shops`, so adopting it would mean either dropping a live FK or
//     inventing a shop row per licence.
//   * IT CANNOT EXPRESS A TRANSACTION. There is no grouping column -- no
//     journal-entry id that two lines belong to. `reference` is free text and
//     `source_id` points at whatever caused the entry, neither of which pairs
//     a debit with its credit. WITHOUT A GROUPING KEY, "debits equal credits"
//     IS NOT A RULE YOU CAN CHECK. That single missing column is why this is a
//     new model rather than a validator bolted onto the old one.
//
// The only code that ever wrote gl_entries (unmerged lucid-ptolemy branch,
// api/pay.js and api/db.js) inserted ONE row with ONE side populated, no
// counterpart, wrapped in `.catch(() => {})` so a failed post was swallowed
// while the payment reported success. It was a single-sided audit trail using
// accounting words, and it is not being revived.
//
// ── WHY SHARED RATHER THAN sb_-PREFIXED ──────────────────────────────────
// Debits equal credits in every trade. This is the same call as
// api/_lib/wip-accounting.js and the subcontractor compliance layer: one
// engine, licence- and app-scoped tables, SAIRNbiz as the first consumer
// because it is the accounting backbone every B2B app already includes.
// SAIRNbiz today has NO general ledger and no double-entry concept at all --
// zero occurrences of debit, account_code, journal or double-entry in the
// file, verified before this was designed.
//
// ── THE RULE, AND WHERE IT IS ENFORCED ───────────────────────────────────
// An entry may post only when the sum of its debits equals the sum of its
// credits. That is checked HERE, and the endpoint writes nothing until this
// says yes, so no code path can produce an unbalanced posted entry.
//
// HONEST LIMIT, STATED RATHER THAN IMPLIED: a Postgres CHECK constraint
// cannot span rows, so the DATABASE cannot enforce this on its own. The
// guarantee is "no code path writes an unbalanced entry", not "the database
// would refuse one". A trigger could close that and is named as the next step
// rather than quietly assumed. What the database DOES enforce per row is that
// a line carries exactly one side -- see the schema.
//
// ── MONEY IS COMPARED IN CENTS ───────────────────────────────────────────
// 0.1 + 0.2 !== 0.3 in floating point, and a ledger that decides balance with
// a float comparison will one day refuse a correct entry or accept a wrong
// one. Every comparison here is on integer cents.

'use strict';

// The platform's own chart of accounts, copied from the CFO context in
// api/_lib/exec-context.js rather than invented here. Nothing outside this
// list may be posted to: an account code nobody defined is a typo that would
// otherwise create a silent orphan account on a balance sheet.
const ACCOUNTS = {
  '1010': { name: 'Cash - Checking', type: 'asset' },
  '1100': { name: 'Accounts Receivable', type: 'asset' },
  '1200': { name: 'Inventory', type: 'asset' },
  '2010': { name: 'Accounts Payable', type: 'liability' },
  '2100': { name: 'Accrued Wages', type: 'liability' },
  '2110': { name: 'Federal Income Tax Payable', type: 'liability' },
  '2130': { name: 'FICA Payable', type: 'liability' },
  '4010': { name: 'Service Revenue', type: 'revenue' },
  '4020': { name: 'Product Revenue', type: 'revenue' },
  '5010': { name: 'Cost of Goods Sold', type: 'expense' },
  '6010': { name: 'Wages', type: 'expense' },
  '6020': { name: 'Payroll Taxes', type: 'expense' },
  '6030': { name: 'Benefits', type: 'expense' },
  '6100': { name: 'Rent', type: 'expense' },
  '6210': { name: 'Software', type: 'expense' }
};

// A posted entry is never edited. Accounting corrects with a REVERSING entry,
// so the history of what was believed and when survives. 'void' exists only
// for an entry that was never posted.
const ENTRY_STATUSES = ['draft', 'posted', 'void'];

// Normal balance by account type, used to explain a balance rather than to
// decide one. Debits increase assets and expenses; credits increase
// liabilities, equity and revenue.
const DEBIT_POSITIVE = { asset: true, expense: true };

function str(v) { return typeof v === 'string' ? v.trim() : ''; }
function isDate(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }

// Money in, cents out. Returns null for anything that is not a finite number,
// so a string amount is REFUSED rather than coerced -- "1,200.00" parsed
// loosely becomes 1, and a ledger is the last place to find that out.
function cents(v) {
  if (typeof v !== 'number' || !isFinite(v)) return null;
  return Math.round(v * 100);
}
function money(c) { return Math.round(c) / 100; }

// ── One line ─────────────────────────────────────────────────────────────
function validateLine(line, index) {
  const problems = [];
  const l = line || {};
  const code = str(l.account_code);
  if (!code) problems.push('line ' + index + ': no account code');
  else if (!ACCOUNTS[code]) problems.push('line ' + index + ': account code "' + code + '" is not in the chart of accounts');

  const d = l.debit === undefined || l.debit === null || l.debit === '' ? 0 : cents(l.debit);
  const c = l.credit === undefined || l.credit === null || l.credit === '' ? 0 : cents(l.credit);
  if (d === null) problems.push('line ' + index + ': debit is not a number');
  if (c === null) problems.push('line ' + index + ': credit is not a number');
  if (d !== null && d < 0) problems.push('line ' + index + ': debit is negative -- post the other side instead of a negative amount');
  if (c !== null && c < 0) problems.push('line ' + index + ': credit is negative -- post the other side instead of a negative amount');
  // EXACTLY ONE SIDE. A line carrying both is ambiguous about what it means,
  // and a line carrying neither is noise that still has to be stored and
  // reconciled. Both are refused rather than normalised.
  if (d === 0 && c === 0) problems.push('line ' + index + ': neither a debit nor a credit');
  if (d && c) problems.push('line ' + index + ': carries BOTH a debit and a credit -- split it into two lines');

  return {
    ok: problems.length === 0,
    account_code: code || null,
    account_name: ACCOUNTS[code] ? ACCOUNTS[code].name : null,
    account_type: ACCOUNTS[code] ? ACCOUNTS[code].type : null,
    debit_cents: d || 0,
    credit_cents: c || 0,
    memo: str(l.memo) || null,
    problems: problems
  };
}

// ── One entry, and the rule ──────────────────────────────────────────────
function validateEntry(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const e = input.entry || null;
  if (!e) return { ok: false, error: { code: 'NO_ENTRY', message: 'no entry supplied' } };

  const problems = [];
  if (!isDate(e.entry_date)) problems.push('entry_date must be YYYY-MM-DD');
  if (!str(e.memo)) problems.push('an entry needs a memo -- a ledger line nobody can explain later is a ledger line nobody can audit');

  const raw = Array.isArray(e.lines) ? e.lines : [];
  const lines = raw.map(validateLine);
  lines.forEach(function (l) { l.problems.forEach(function (p) { problems.push(p); }); });

  // A single-sided entry is the exact defect the old gl_entries writers
  // shipped, so it is named rather than folded into "does not balance".
  if (raw.length < 2) problems.push('an entry needs at least two lines -- one debit and one credit; a single-sided post is what the previous ledger did and is not double-entry');

  const debits = lines.reduce(function (s, l) { return s + l.debit_cents; }, 0);
  const credits = lines.reduce(function (s, l) { return s + l.credit_cents; }, 0);
  const balanced = debits === credits && debits > 0;

  if (raw.length >= 2 && debits === credits && debits === 0) {
    problems.push('every line is zero -- an entry that moves nothing is not an entry');
  } else if (raw.length >= 2 && debits !== credits) {
    // THE RULE. Stated with both totals and the gap, because "does not
    // balance" without the numbers is a message somebody has to reproduce by
    // hand before they can act on it.
    problems.push('does not balance: debits ' + money(debits) + ' vs credits ' + money(credits) +
      ', out by ' + money(Math.abs(debits - credits)));
  }

  return {
    ok: true,
    balanced: balanced,
    postable: problems.length === 0,
    entry_date: isDate(e.entry_date) ? e.entry_date : null,
    memo: str(e.memo) || null,
    source_app: str(e.source_app) || null,
    source_kind: str(e.source_kind) || null,
    source_id: str(e.source_id) || null,
    lines: lines,
    debit_total: money(debits),
    credit_total: money(credits),
    difference: money(debits - credits),
    problems: problems
  };
}

// ── The reversing entry ──────────────────────────────────────────────────
// The ONLY correction mechanism. A posted entry is immutable, so fixing one
// means posting its mirror and then posting the right one. Built here rather
// than left to a caller so the mirror cannot be got subtly wrong.
function reversalOf(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const src = input.entry || null;
  if (!src) return { ok: false, error: { code: 'NO_ENTRY', message: 'no entry supplied' } };
  if (str(src.status) !== 'posted') {
    return { ok: false, error: { code: 'NOT_POSTED', message: 'only a posted entry can be reversed -- an unposted one is voided instead' } };
  }
  const lines = (Array.isArray(src.lines) ? src.lines : []).map(function (l) {
    // Sides swapped, amounts unchanged. Not negated: a negative debit is not
    // a credit in any ledger a reader would recognise.
    return {
      account_code: l.account_code,
      debit: (typeof l.credit === 'number' ? l.credit : 0) || 0,
      credit: (typeof l.debit === 'number' ? l.debit : 0) || 0,
      memo: l.memo || null
    };
  });
  return {
    ok: true,
    entry: {
      entry_date: isDate(input.reversal_date) ? input.reversal_date : today,
      memo: 'Reversal of ' + (str(src.entry_id) || 'entry') + ': ' + (str(src.memo) || ''),
      source_app: str(src.source_app) || null,
      source_kind: 'reversal',
      source_id: str(src.entry_id) || null,
      lines: lines
    }
  };
}

// ── Trial balance ────────────────────────────────────────────────────────
// The check that the whole book still balances, not just one entry. Derived
// from stored lines on every read and never persisted, so it cannot drift
// away from what it summarises.
function trialBalance(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const rows = Array.isArray(input.lines) ? input.lines : [];
  const acc = Object.create(null);
  let dTot = 0, cTot = 0, skipped = 0;
  rows.forEach(function (r) {
    const code = str(r && r.account_code);
    const d = cents(typeof r.debit === 'number' ? r.debit : 0);
    const c = cents(typeof r.credit === 'number' ? r.credit : 0);
    // A stored line that cannot be read is COUNTED, never silently dropped: a
    // trial balance that quietly omits rows balances for the wrong reason.
    if (!code || !ACCOUNTS[code] || d === null || c === null) { skipped++; return; }
    const a = acc[code] || (acc[code] = { account_code: code, name: ACCOUNTS[code].name, type: ACCOUNTS[code].type, debit_cents: 0, credit_cents: 0 });
    a.debit_cents += d; a.credit_cents += c; dTot += d; cTot += c;
  });
  const accounts = Object.keys(acc).sort().map(function (k) {
    const a = acc[k];
    const net = a.debit_cents - a.credit_cents;
    return {
      account_code: a.account_code, name: a.name, type: a.type,
      debit: money(a.debit_cents), credit: money(a.credit_cents),
      // Signed the way an accountant reads it: positive means the account sits
      // on its normal side.
      balance: money(DEBIT_POSITIVE[a.type] ? net : -net)
    };
  });
  return {
    ok: true, today: today, accounts: accounts,
    debit_total: money(dTot), credit_total: money(cTot),
    difference: money(dTot - cTot),
    in_balance: dTot === cTot,
    lines_in: rows.length,
    lines_skipped: skipped,
    problems: skipped ? [skipped + ' stored line(s) could not be read and are in NO account above -- the totals are short by them'] : []
  };
}

module.exports = {
  ACCOUNTS,
  ENTRY_STATUSES,
  validateLine,
  validateEntry,
  reversalOf,
  trialBalance
};
