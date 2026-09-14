// tests/functional_core_is_pure.js  -- item 92, applied to exactly two places
//
// Run:  node tests/functional_core_is_pure.js
//
// FUNCTIONAL CORE / IMPERATIVE SHELL, ON THE TWO FUNCTIONS THAT DECIDE MONEY.
// Not a platform-wide rewrite: `api/_lib/ledger.js` and `sbMatchPure` in
// sairnbiz.html. Both answer the same kind of question -- may this money move --
// and both are worth being able to test by passing arguments rather than by
// standing up a world.
//
// ── THE CLAIM THAT WAS PROSE UNTIL NOW ──────────────────────────────────────
// api/_lib/ledger.js has said "Pure functions, no I/O, no app names" in its own
// header since the day it was written, and NOTHING CHECKED IT. A purity claim
// nobody verifies is the same shape as a coverage claim nobody measures: true
// when written, silently false the first time somebody needs a timestamp.
//
// So section 1 is a REGRESSION GUARD on that sentence -- no clock, no
// randomness, no network, no storage anywhere in the core -- and section 2
// proves the same of the SAIRNbiz core by DRIVING it with no globals at all.
//
// ── WHAT A PURITY CHECK CAN AND CANNOT SEE ──────────────────────────────────
// This reads the source for the constructs that make a function
// non-deterministic. It CANNOT see impurity reached through a dependency, so
// section 1 checks the core's only import as well; it cannot see a global
// mutated in place; and it is a source scan, so a clock reached through an
// alias would pass. Section 2 is the answer to that -- it runs the SAIRNbiz
// core in a sandbox with NO Date, NO Math.random and NO localStorage, where
// reaching for any of them throws rather than being read.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const rd = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8').replace(/\r\n/g, '\n');
// SB_HTML points this suite at a MUTATED COPY of sairnbiz.html.
// tests/sairnbiz_void_mutation_control.js uses it to prove the void arms below
// actually fail when the exclusion is removed -- the platform measured on
// 2026-09-13 that 23 of 39 negative controls never verify their own sabotage
// applied, and a control that cannot be shown to fail is not evidence of
// anything. Defaults to the shipped file, so an ordinary run is unchanged.
const readBiz = () => (process.env.SB_HTML
  ? fs.readFileSync(process.env.SB_HTML, 'utf8').replace(/\r\n/g, '\n')
  : rd('sairnbiz.html'));

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; console.log('  ok   ' + label); }
function section(s) { console.log('\n' + s); }

// Comments and strings are stripped before scanning. Both files DISCUSS
// `new Date` at length -- calendar-date.js exists because `new Date` silently
// repairs an impossible date -- so a naive search reports the warning against
// the practice as the practice. A check that fires on its own documentation is
// one nobody keeps.
function stripJs(src) {
  const out = [];
  let i = 0;
  while (i < src.length) {
    const c = src[i], nx = src[i + 1];
    if (c === '/' && nx === '/') { const j = src.indexOf('\n', i); i = j < 0 ? src.length : j; continue; }
    if (c === '/' && nx === '*') { const j = src.indexOf('*/', i + 2); i = j < 0 ? src.length : j + 2; continue; }
    if (c === '"' || c === "'" || c === '`') {
      let j = i + 1;
      while (j < src.length) {
        if (src[j] === '\\') { j += 2; continue; }
        if (src[j] === c) break;
        j += 1;
      }
      out.push(c + c);
      i = j + 1;
      continue;
    }
    out.push(c);
    i += 1;
  }
  return out.join('');
}

// The constructs that make a function's answer depend on something other than
// its arguments.
const IMPURE = [
  [/\bnew\s+Date\b/, 'new Date'],
  [/\bDate\.now\b/, 'Date.now'],
  [/\bMath\.random\b/, 'Math.random'],
  [/\bfetch\s*\(/, 'fetch'],
  [/\blocalStorage\b/, 'localStorage'],
  [/\bsessionStorage\b/, 'sessionStorage'],
  [/\bprocess\.env\b/, 'process.env'],
  [/\brequire\s*\(\s*['"](?:fs|http|https|child_process|net)['"]/, 'a node I/O module'],
];

console.log('SAIRN: the functional core decides, the shell does the I/O\n');

section('1. api/_lib/ledger.js -- the purity its own header claims');
{
  const core = stripJs(rd('api/_lib/ledger.js'));
  const found = IMPURE.filter(([re]) => re.test(core)).map(([, name]) => name);
  ok(found.length === 0,
     'the ledger core contains none of: ' + IMPURE.map(([, x]) => x).join(', ')
     + (found.length ? ' -- FOUND ' + found.join(', ') : ''));
  ok(/Pure functions, no I\/O/.test(rd('api/_lib/ledger.js')),
     '...and its header still makes that claim, so this arm is guarding a '
     + 'sentence somebody wrote rather than one nobody did');

  // A SOURCE SCAN CANNOT SEE IMPURITY REACHED THROUGH A DEPENDENCY, so the
  // core's imports are checked too. It has exactly one.
  const imports = [...rd('api/_lib/ledger.js').matchAll(/require\(\s*'([^']+)'\s*\)/g)]
    .map((m) => m[1]);
  ok(imports.length === 1 && imports[0] === './calendar-date',
     'the core imports exactly one module, ./calendar-date: ' + imports.join(', '));
  const dep = stripJs(rd('api/_lib/calendar-date.js'));
  // calendar-date DOES read the clock -- in todayFrom(nowMs), which takes the
  // time as an argument and falls back. What matters is that the ledger uses
  // only the pure half.
  ok(/isCalendarDate/.test(rd('api/_lib/ledger.js')) && !/todayFrom/.test(stripJs(rd('api/_lib/ledger.js'))),
     'and it uses only that module\'s PURE half (isCalendarDate), never '
     + 'todayFrom, which is the one that can reach Date.now');
  ok(/Date\.now/.test(dep),
     'CONTROL: calendar-date.js really does contain a clock, so the arm above '
     + 'is distinguishing two halves of a real module rather than passing on a '
     + 'file that has no clock to avoid');
}

section('2. the cents-to-money rule lives in ONE place');
{
  const core = require(path.join(ROOT, 'api/_lib/ledger.js'));
  ok(typeof core.money === 'function' && typeof core.cents === 'function',
     'the core EXPORTS the money rule, so a shell can use it instead of '
     + 'reinventing it');
  ok(core.money(12345) === 123.45 && core.cents(123.45) === 12345,
     'and it round-trips: cents(123.45) -> 12345 -> money -> 123.45');
  const shell = stripJs(rd('api/ledger.js'));
  // THE FINDING THIS ARM EXISTS FOR: the endpoint did `l.debit_cents / 100`
  // when building the rows it writes, a second money rule beside NINE uses of
  // money() inside the core. They agree only while debit_cents is an integer,
  // which cents() happens to guarantee and nothing asserted.
  ok(!/_cents\s*\/\s*100/.test(shell),
     'the SHELL does no cents-to-money arithmetic of its own -- it was doing '
     + '`l.debit_cents / 100` next to nine uses of money() in the core');
  ok(/ledger\.money\(/.test(shell),
     '...it calls the core\'s money() instead');
  ok(/\/\s*100/.test(stripJs(rd('api/_lib/ledger.js'))),
     'CONTROL: the division still exists, in the core, where it belongs -- the '
     + 'arm above would also pass if the rule had simply been deleted');
}

section('3. sbMatchPure -- driven with NO world at all');
{
  const html = readBiz();
  function grab(sig) {
    const start = html.indexOf(sig);
    assert.ok(start > 0, 'not found in sairnbiz.html: ' + sig);
    let i = html.indexOf('{', start + sig.length - 1), depth = 0, q = null;
    for (; i < html.length; i++) {
      const c = html[i], p = html[i - 1];
      if (q) { if (c === q && p !== '\\') q = null; continue; }
      if (c === '"' || c === "'" || c === '`') { q = c; continue; }
      if (c === '/' && html[i + 1] === '/') { i = html.indexOf('\n', i); continue; }
      if (c === '/' && html[i + 1] === '*') { i = html.indexOf('*/', i) + 1; continue; }
      if (c === '{') depth++;
      else if (c === '}') { depth--; if (!depth) return html.slice(start, i + 1); }
    }
    throw new Error('unterminated: ' + sig);
  }

  // THE SANDBOX IS THE ASSERTION. No localStorage, no ld, no st -- and Date
  // and Math.random replaced with things that THROW. A core that reaches for
  // any of them fails here with the name of what it reached for, rather than
  // quietly returning a different answer on a different day.
  const reached = [];
  const ctx = {
    fmt: (v) => '$' + Number(v).toFixed(2),
    SB_MATCH_TOLERANCE: 0.00,
    Math: { abs: Math.abs, round: Math.round,
            get random() { reached.push('Math.random'); throw new Error('Math.random'); } },
    get Date() { reached.push('Date'); throw new Error('Date'); },
    get localStorage() { reached.push('localStorage'); throw new Error('localStorage'); },
    get ld() { reached.push('ld'); throw new Error('ld'); },
    get sbPOAll() { reached.push('sbPOAll'); throw new Error('sbPOAll'); },
    get sbRecvAll() { reached.push('sbRecvAll'); throw new Error('sbRecvAll'); }
  };
  vm.createContext(ctx);
  // sbIsVoid joined the core's dependencies on 2026-09-14 with the void
  // mechanism. It is loaded here rather than stubbed BECAUSE the sandbox is the
  // assertion: a stub would pass whatever the shipped predicate did, and the
  // whole point of section 3 is that the code under test is the code that ships.
  for (const sig of ['function sbMoneyCents(v){', 'function sbVendorKey(v){',
                     'function sbIsVoid(r){',
                     'function sbMatchPure(pos,recs,po_num,vendor,amt){']) {
    vm.runInContext(grab(sig), ctx);
  }

  const pos = [{ po_num: 'PO-2026-001', vendor: 'Stone World', amt: 1200 }];
  const recs = [{ id: 'RC1', po_num: 'PO-2026-001', vendor: 'Stone World', val: 1200 }];

  // THE REACH IS CAUGHT AND REPORTED AS A FINDING, not left to crash the file.
  // The first version let the sandbox's throwing getters propagate, so putting
  // `sbPOAll()` back inside the core produced a stack trace rather than a named
  // failure -- detection, but the kind that reads as a broken test instead of a
  // broken subject. A control whose output is indistinguishable from its own
  // breakage is one somebody will re-run instead of read.
  let good = null, threw = null;
  try {
    good = ctx.sbMatchPure(pos, recs, 'PO-2026-001', 'Stone World', 1200);
  } catch (e) { threw = e && e.message; }
  ok(threw === null,
     'the core did not reach for anything the sandbox withholds'
     + (threw ? ' -- IT REACHED FOR ' + threw : ''));
  ok(good && good.ok === true,
     'a matched bill is MATCHED with no localStorage, no clock and no randomness '
     + 'in the sandbox at all');
  ok(reached.length === 0,
     'and the core reached for none of them: ' + (reached.join(', ') || 'nothing'));

  // DETERMINISM, asserted rather than assumed: the same arguments twice.
  ok(JSON.stringify(ctx.sbMatchPure(pos, recs, 'PO-2026-001', 'Stone World', 1200))
     === JSON.stringify(good),
     'the same arguments give the same answer -- which is the whole property '
     + 'the split buys');

  section('4. ...and every refusal is reachable by ARGUMENT');
  // Four cases that previously needed four localStorage fixtures.
  const cases = [
    ['no PO number', () => ctx.sbMatchPure(pos, recs, '', 'Stone World', 1200),
     /no purchase order number/],
    ['a PO that does not exist', () => ctx.sbMatchPure(pos, recs, 'PO-2026-999', 'Stone World', 1200),
     /no purchase order PO-2026-999 exists/],
    ['nothing received', () => ctx.sbMatchPure(pos, [], 'PO-2026-001', 'Stone World', 1200),
     /nothing has been recorded as received/],
    ['a vendor mismatch', () => ctx.sbMatchPure(pos, recs, 'PO-2026-001', 'Atlas Marble', 1200),
     /vendor differs/],
    ['a partial delivery billed in full',
     () => ctx.sbMatchPure(pos, [{ po_num: 'PO-2026-001', vendor: 'Stone World', val: 400 }],
                           'PO-2026-001', 'Stone World', 1200),
     /against \$400\.00 actually received/],
    ['ONE CENT over the PO',
     () => ctx.sbMatchPure(pos, recs, 'PO-2026-001', 'Stone World', 1200.01),
     /billed \$1200\.01 against a PO of \$1200\.00/],
    ['two POs sharing a number',
     () => ctx.sbMatchPure([pos[0], { po_num: 'PO-2026-001', vendor: 'Stone World', amt: 9900 }],
                           recs, 'PO-2026-001', 'Stone World', 1200),
     /2 different purchase orders are numbered/],
    // ── VOID (2026-09-14) ──────────────────────────────────────────────────
    // THE REFUSAL MUST NOT SAY THE PO DOES NOT EXIST. It does exist, somebody
    // voided it, and "no purchase order PO-2026-001 exists" sends the reader
    // looking for a lost record instead of raising the replacement.
    ['a voided PO',
     () => ctx.sbMatchPure([{ po_num: 'PO-2026-001', vendor: 'Stone World', amt: 1200, status: 'Void' }],
                           recs, 'PO-2026-001', 'Stone World', 1200),
     /purchase order PO-2026-001 has been voided/],
    ['every PO of that number voided',
     () => ctx.sbMatchPure([{ po_num: 'PO-2026-001', vendor: 'Stone World', amt: 1200, status: 'Void' },
                            { po_num: 'PO-2026-001', vendor: 'Stone World', amt: 9900, status: 'Void' }],
                           recs, 'PO-2026-001', 'Stone World', 1200),
     /all 2 purchase orders numbered PO-2026-001 have been voided/],
    ['every receipt voided',
     () => ctx.sbMatchPure(pos, [{ id: 'RC1', po_num: 'PO-2026-001', vendor: 'Stone World', val: 1200, status: 'Void' }],
                           'PO-2026-001', 'Stone World', 1200),
     /every receipt against PO-2026-001 has been voided/],
    // A voided receipt must not still inflate the received total. Two receipts
    // of $1200, one of them voided in error-correction, against a $1200 bill:
    // if the void were ignored the sum would be $2400 and the bill refused.
    ['a receipt voided as a duplicate no longer inflates the total',
     () => ctx.sbMatchPure(pos, [recs[0],
                                 { id: 'RC2', po_num: 'PO-2026-001', vendor: 'Stone World', val: 1200 }],
                           'PO-2026-001', 'Stone World', 1200),
     /against \$2400\.00 actually received/]
  ];
  for (const [label, run, re] of cases) {
    const r = run();
    ok(r.ok === false && re.test(r.reasons.join(' ')),
       label + ': refused, and the reason still reads the same -- ' + r.reasons[0]);
  }
  ok(reached.length === 0,
     'CONTROL: across every case above the core still touched no clock, no '
     + 'storage and no randomness -- ' + (reached.join(', ') || 'nothing reached'));

  section('4b. a void CLEARS the refusal it was raised to clear');
  // This is the whole justification for the mechanism. Every arm below is a
  // bill that was refused BEFORE the void and matches AFTER it, with the
  // voided row still present in the arguments -- excluded from the decision,
  // never removed from the record.
  {
    // (i) TWO POs SHARING A NUMBER. The ambiguity guard refuses outright, and
    // before 2026-09-14 nothing in the product could clear it: the PO raised in
    // error on a second device was permanent and blocked a correct bill.
    const dupe = { po_num: 'PO-2026-001', vendor: 'Stone World', amt: 9900 };
    const blocked = ctx.sbMatchPure([pos[0], dupe], recs, 'PO-2026-001', 'Stone World', 1200);
    ok(blocked.ok === false && /2 different purchase orders are numbered/.test(blocked.reasons.join(' ')),
       'BEFORE: two POs numbered PO-2026-001 refuse the bill outright');
    const cleared = ctx.sbMatchPure(
      [pos[0], Object.assign({}, dupe, { status: 'Void', void_reason: 'raised in error on the shop terminal' })],
      recs, 'PO-2026-001', 'Stone World', 1200);
    ok(cleared.ok === true,
       'AFTER: voiding the one raised in error leaves a single live PO and the '
       + 'correct bill MATCHES -- while both rows stay on the record');

    // (ii) A RECEIPT ENTERED TWICE. Before the void, the received total is
    // double and the refusal names "$2400.00 actually received" against a
    // number nobody in the product could correct.
    const twice = [recs[0], { id: 'RC2', po_num: 'PO-2026-001', vendor: 'Stone World', val: 1200 }];
    const inflated = ctx.sbMatchPure(pos, twice, 'PO-2026-001', 'Stone World', 1200);
    ok(inflated.ok === false && /\$2400\.00 actually received/.test(inflated.reasons.join(' ')),
       'BEFORE: a receipt entered twice inflates the received total to $2400.00');
    const corrected = ctx.sbMatchPure(pos,
      [recs[0], Object.assign({}, twice[1], { status: 'Void', void_reason: 'keyed twice' })],
      'PO-2026-001', 'Stone World', 1200);
    ok(corrected.ok === true,
       'AFTER: voiding the duplicate receipt restores the $1200.00 total and the '
       + 'bill MATCHES');

    // (iii) THE VOID IS NOT A BLANKET AMNESTY. A voided receipt stops
    // contributing its VALUE and stops contributing its VENDOR -- one rule, not
    // two -- but a live receipt naming the wrong vendor still refuses.
    const wrongVendor = { id: 'RC3', po_num: 'PO-2026-001', vendor: 'Atlas Marble', val: 0 };
    const namesIt = ctx.sbMatchPure(pos, [recs[0], wrongVendor], 'PO-2026-001', 'Stone World', 1200);
    ok(namesIt.ok === false && /a receipt names "Atlas Marble"/.test(namesIt.reasons.join(' ')),
       'BEFORE: a live receipt naming the wrong vendor refuses the bill');
    const voidedIt = ctx.sbMatchPure(pos,
      [recs[0], Object.assign({}, wrongVendor, { status: 'Void', void_reason: 'logged against the wrong PO' })],
      'PO-2026-001', 'Stone World', 1200);
    ok(voidedIt.ok === true,
       'AFTER: voiding that receipt clears the vendor reason too -- the void is '
       + 'one rule applied to the whole row, not a per-field exception');

    // (iv) THE NEGATIVE CONTROL. A status the predicate does not recognise must
    // NOT be treated as void. `sbIsVoid` compares against the exact string
    // 'Void', and a row carrying 'void', 'VOID' or 'Cancelled' is still live --
    // so a typo in a future writer fails visibly rather than silently excluding
    // a real receipt from a financial control.
    for (const bogus of ['void', 'VOID', 'Voided', 'Cancelled', 'Open', '']) {
      const r = ctx.sbMatchPure(pos,
        [recs[0], { id: 'RC4', po_num: 'PO-2026-001', vendor: 'Stone World', val: 1200, status: bogus }],
        'PO-2026-001', 'Stone World', 1200);
      ok(r.ok === false && /\$2400\.00 actually received/.test(r.reasons.join(' ')),
         'CONTROL: status "' + bogus + '" is NOT void -- the receipt still counts');
    }
    ok(reached.length === 0,
       'CONTROL: the void arms reached for no clock, no storage and no '
       + 'randomness either -- ' + (reached.join(', ') || 'nothing reached'));
  }

  // THE FLOAT CASE THE INDEPENDENT REVIEW FOUND, now expressible as two
  // arguments rather than a storage fixture. 1870.93 + 1957.54 sums to
  // 3828.4700000000003 in binary floating point.
  const partials = [{ po_num: 'PO-2026-002', vendor: 'V', val: 1870.93 },
                    { po_num: 'PO-2026-002', vendor: 'V', val: 1957.54 }];
  const floatCase = ctx.sbMatchPure([{ po_num: 'PO-2026-002', vendor: 'V', amt: 3828.47 }],
                                    partials, 'PO-2026-002', 'V', 3828.47);
  ok(floatCase.ok === true,
     'two partial deliveries summing to 3828.4700000000003 in floating point '
     + 'still MATCH, because the comparison is in integer cents');
}

section('5. the shell is thin, and stays thin');
{
  const html = readBiz();
  const m = /function sbThreeWayMatch\(po_num,vendor,amt\)\{([\s\S]{0,400}?)\n\}/.exec(html);
  ok(!!m, 'the shell is still present under its original name, so every caller '
     + 'is unchanged');
  const body = m[1];
  ok(/sbMatchPure\(/.test(body), 'the shell delegates to the core');
  // THE ARM THAT MATTERS OVER TIME. The moment the shell starts filtering,
  // summing or comparing, the core stops being the whole decision and a reader
  // has to check two places to know what the gate does.
  ok(!/filter\(|reduce\(|Math\.abs|reasons/.test(body),
     'and the shell does NO filtering, summing or comparing of its own -- '
     + 'body is: ' + body.trim().replace(/\s+/g, ' '));
}

console.log('\nALL ' + n + ' ASSERTIONS PASS');
