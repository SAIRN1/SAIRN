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
    // ── THE EXACT FIGURES, ALONGSIDE THE DISPLAY ONES (2026-09-13) ───────
    // THE BALANCE DECISION WAS ALREADY EXACT and always has been: `debits` and
    // `credits` above are integer cents from validateLine()'s Math.round(v*100),
    // and `balanced` is `debits === credits` on integers. Nothing about the
    // engine's correctness changes here.
    //
    // What was missing is that the only totals a CONSUMER could read were the
    // float ones. tools/invariant_runner.js compared `debit_total` -- a value
    // that has been through money() -- and I concluded from it that the check
    // itself was a float `===` with no tolerance band. It is not. The engine
    // was exact and the OUTPUT was lossy, which is a different defect and a
    // much smaller one.
    //
    // ADDITIVE ON PURPOSE. The float fields are unchanged and every existing
    // caller and assertion keeps working -- api/ledger.js:176 and :276 forward
    // them, and ledger.test.js asserts on them directly. A consumer that needs
    // exactness now has it without anything being taken away from one that
    // needs the display value.
    debit_total_cents: debits,
    credit_total_cents: credits,
    difference_cents: debits - credits,
    // WHICH PATH BUILT THIS (2026-09-13, item 41). entryFromTransfers() below
    // makes imbalance UNREPRESENTABLE; this path only makes it REFUSED. Both
    // return this same object, so without a field naming the path every later
    // reader would assume the stronger guarantee applies to both.
    built_from: 'lines',
    problems: problems
  };
}

// ── Balanced by construction ─────────────────────────────────────────────
// A TRANSFER is one amount moving from one account to another: a debit account,
// a credit account, and a single figure. Every transfer contributes THE SAME
// CENTS TO BOTH TOTALS, so an entry assembled from transfers cannot come out
// unbalanced -- not "is checked and found balanced", INCAPABLE of being
// otherwise. That is the difference between refusing a bad state and not being
// able to express one, and it is the whole point of this function.
//
// SAME PATTERN AS reversalOf(), which already builds its mirror here rather
// than leaving a caller to get it subtly wrong. This applies it to creation.
//
// ── WHAT IT DOES NOT DO, so nobody reads more into it ───────────────────
//   * IT PREVENTS IMBALANCE, NOT BEING WRONG. A mistyped amount still produces
//     a perfectly balanced entry with the wrong figure in it.
//   * IT CANNOT EXPRESS AN m:n ENTRY. Several accounts on BOTH sides has no
//     unique transfer decomposition -- debit A 100 / B 50 against credit C 120
//     / D 30 can be written as (A->C 100, B->C 20, B->D 30) or as (A->C 90,
//     A->D 10, B->C 30, B->D 20), and the ledger cannot tell which pairing the
//     accounting means because it generally means neither. Those entries keep
//     using validateEntry() with a line array. Anything with a single account
//     on one side -- payroll, an invoice, a payment -- decomposes uniquely and
//     belongs here.
//
// ── AGGREGATION IS REAL AND IS NOT A DETAIL ─────────────────────────────
// Three transfers all debiting 6010 become ONE debit line for 6010, not three.
// That is the entry a person expects, and it is a genuine difference from what
// the caller literally typed. Debits and credits are aggregated SEPARATELY and
// never netted against each other: an account that is debited in one transfer
// and credited in another gets both lines. Netting them would be a judgement
// about what the transaction meant, and this function does not make those.
//
// EVERY OTHER RULE IS validateEntry's. The chart of accounts, the memo, the
// date, the at-least-two-lines rule -- one implementation, delegated to, so
// there is no second copy to drift. This function's only added guarantee is
// balance.
function entryFromTransfers(input) {
  input = input || {};
  const today = isDate(input.today) ? input.today : null;
  if (!today) {
    return { ok: false, error: { code: 'NO_TODAY', message: 'today (YYYY-MM-DD) is required -- this engine will not assume a clock' } };
  }
  const e = input.entry || null;
  if (!e) return { ok: false, error: { code: 'NO_ENTRY', message: 'no entry supplied' } };

  const raw = Array.isArray(e.transfers) ? e.transfers : [];
  const problems = [];
  if (!raw.length) problems.push('an entry needs at least one transfer');

  // Insertion order is preserved so the lines come out in the order the caller
  // described them, which is what makes the result readable back.
  const debitOrder = [];
  const creditOrder = [];
  const debitBy = {};
  const creditBy = {};

  raw.forEach(function (tr, i) {
    const t = tr || {};
    const from = str(t.debit_account);
    const to = str(t.credit_account);
    const amt = cents(t.amount);
    let bad = false;

    if (!from) { problems.push('transfer ' + i + ': no debit_account'); bad = true; }
    else if (!ACCOUNTS[from]) { problems.push('transfer ' + i + ': debit_account "' + from + '" is not in the chart of accounts'); bad = true; }
    if (!to) { problems.push('transfer ' + i + ': no credit_account'); bad = true; }
    else if (!ACCOUNTS[to]) { problems.push('transfer ' + i + ': credit_account "' + to + '" is not in the chart of accounts'); bad = true; }
    // The same account on both sides balances perfectly and moves nothing. It
    // is a typo every time, and letting it through would put two lines on the
    // books that cancel and mean nothing.
    if (from && to && from === to) {
      problems.push('transfer ' + i + ': debit_account and credit_account are both "' + from + '" -- a transfer to itself moves nothing');
      bad = true;
    }
    if (amt === null) { problems.push('transfer ' + i + ': amount is not a number'); bad = true; }
    else if (amt <= 0) { problems.push('transfer ' + i + ': amount must be greater than zero -- reverse the accounts instead of using a negative'); bad = true; }

    if (bad) return;
    if (debitBy[from] === undefined) { debitBy[from] = 0; debitOrder.push(from); }
    if (creditBy[to] === undefined) { creditBy[to] = 0; creditOrder.push(to); }
    debitBy[from] += amt;
    creditBy[to] += amt;
  });

  // money() round-trips exactly here: every figure is an integer cent count
  // produced by cents(), and validateEntry() puts it straight back through
  // Math.round(v * 100).
  const lines = [];
  debitOrder.forEach(function (code) {
    lines.push({ account_code: code, debit: money(debitBy[code]), credit: 0, memo: null });
  });
  creditOrder.forEach(function (code) {
    lines.push({ account_code: code, debit: 0, credit: money(creditBy[code]), memo: null });
  });

  const v = validateEntry({
    today: today,
    entry: {
      entry_date: e.entry_date, memo: e.memo, source_app: e.source_app,
      source_kind: e.source_kind, source_id: e.source_id, lines: lines
    }
  });
  if (!v.ok) return v;

  // A transfer-level problem is not a line-level problem and the line indices
  // would not map back to it, so they are reported together and the transfer
  // ones come first -- they are the ones the caller can act on.
  v.problems = problems.concat(v.problems);
  v.postable = v.problems.length === 0;
  v.built_from = 'transfers';
  v.transfer_count = raw.length;
  return v;
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
  entryFromTransfers,
  reversalOf,
  trialBalance
};
