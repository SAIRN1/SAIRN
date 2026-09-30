// tests/sairnbiz_preview_residual.js
// Run: node tests/sairnbiz_preview_residual.js
//
// THE THREE RESIDUAL FINDINGS from docs/2026-09-29-sairnbiz-preview-check.md
// that the 2026-09-30 re-run explicitly did NOT re-drive -- 7, 10 and 11.
// Every function under test is EXTRACTED BY NAME from the shipped
// sairnbiz.html. An extraction that fails REFUSES rather than falling back to a
// re-typed copy, because a copy is a second source and this suite would then be
// testing the paraphrase instead of the app.
//
// ══ 7. "Revenue Trend YTD" -- AND THE MECHANISM IS NOT WHAT WAS WRITTEN ═════
// The check recorded: "shows Apr 2026 $0, May 2026 $18,520, Aug 2026 $0 while
// invoices dated Jun 1 and Jun 5 exist. June and July are missing."
//
// JUNE IS NOT MISSING. IT IS LABELLED "May".
//
//   new Date('2026-06-01')            -- a DATE-ONLY form, parsed as UTC
//                                        midnight per ECMA-262 21.4.3.2
//   .toLocaleDateString('en-US', ...) -- rendered in the LOCAL zone
//
// In America/New_York (UTC-4) that instant is 2026-05-31 20:00 local, so the
// month renders one behind. Confirmed live 2026-09-30 in the deployed app:
// tz America/New_York, offset 240, ['2026-05','2026-06','2026-09'] rendered as
// ['Apr 2026','May 2026','Aug 2026'].
//
// IT IS SILENT AND IT IS DIRECTIONAL. Every zone west of Greenwich is wrong by
// one month; UTC and every zone east of it is right. A developer in Europe
// cannot reproduce it, and the chart never errors -- it draws a confident wrong
// month. The value beside the label is correct, which is what makes it
// dangerous: the reader has no reason to doubt the row.
//
// THE SAME EXPRESSION IS WRITTEN TWICE -- dashboard #d-rev and P&L #pl-monthly.
//
// AND THE TWO CHARTS SUM DIFFERENT THINGS under near-identical titles:
// #d-rev sums i.paid (cash received), #pl-monthly sums i.amt (invoice value).
// Same month, two figures, and nothing on screen said which was which.
//
// ══ 10. A HELD BILL OFFERED AN ENABLED "Pay" BUTTON ════════════════════════
// The refusal was only discoverable by clicking. The refusal text itself is
// good; what was wrong is that the row gave no sign the button would refuse.
//
// ══ 11. TWO ANSWERS FOR "BIGGEST VENDOR" -- and one of them was also WRONG ══
// AP's "Largest Vendor / By balance" sorted BILLS and took the top one's
// vendor. A vendor owed three $1,000 bills lost to a vendor owed one $2,500
// bill, under a label that says *vendor*. That is not a different question from
// the Vendors panel's answer -- it is a wrong answer to its own question.
// Aggregating by vendor is the fix; the two panels still answer DIFFERENT
// questions afterwards (owed now vs paid this year) and the sub-labels say so.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const FILE = path.join(__dirname, '..', 'sairnbiz.html');
const SRC = fs.readFileSync(FILE, 'utf8');

let pass = 0, fail = 0;

// EVERY arm runs on ONE SERIAL CHAIN, sync and async alike, and that is not
// tidiness. The session arms below swap globals (fetch, sessionStorage) to put
// a stub under the function being tested. Two async arms in flight at once
// share one globalThis and stomp each other's stubs -- which is how four of
// them reported a failure that was the harness's, not the app's. Serialising
// also keeps the printed order the same as the written order.
let chain = Promise.resolve();
function test(name, fn) {
  chain = chain.then(() => Promise.resolve().then(fn).then(
    () => { console.log('  ok   ' + name); pass++; },
    e => { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }));
}
function section(t) { chain = chain.then(() => { console.log('\n' + t); }); }

// Brace-matched extraction of a named function from the shipped file. Refuses
// rather than returning a stand-in -- see the header.
function extract(fnName) {
  const start = SRC.indexOf('function ' + fnName + '(');
  assert.ok(start !== -1, 'could not find function ' + fnName + ' in sairnbiz.html');
  let depth = 0, end = -1;
  for (let k = SRC.indexOf('{', start); k < SRC.length; k++) {
    if (SRC[k] === '{') depth++;
    else if (SRC[k] === '}') { depth--; if (depth === 0) { end = k; break; } }
  }
  assert.ok(end !== -1, 'unbalanced braces reading ' + fnName);
  const src = SRC.slice(start, end + 1);
  // eslint-disable-next-line no-new-func
  return new Function(src + '; return ' + fnName + ';')();
}

// The WHOLE assignment that renders a given element's innerHTML -- not just its
// first line. A renderer split across lines for readability must not read as an
// absent renderer; that is a check that stops testing anything the day someone
// reformats the file (cross-domain disciplines, item 8).
function rendererLine(id) {
  const needle = "$('" + id + "').innerHTML";
  const first = SRC.indexOf(needle);
  assert.ok(first !== -1, 'could not find a renderer for #' + id);
  assert.strictEqual(SRC.indexOf(needle, first + 1), -1,
    'more than one renderer for #' + id + ' -- this check cannot tell which is live');
  // Runs to the end of the statement, taken as whole lines until the running
  // paren balance returns to zero on a line ending in `;`. A one-line renderer
  // and a renderer broken over eight lines both come back whole.
  const lines = SRC.slice(0, first).split('\n');
  const startLine = lines.length - 1;
  const all = SRC.split('\n');
  let depth = 0, out = [];
  for (let i = startLine; i < all.length; i++) {
    out.push(all[i]);
    for (const ch of all[i]) { if (ch === '(') depth++; else if (ch === ')') depth--; }
    if (depth <= 0 && /;\s*$/.test(all[i])) return out.join('\n');
  }
  throw new Error('unterminated renderer statement for #' + id);
}

// ═════════════════════════════════════════════════════════════════════════════
section('7. MONTH LABEL -- the UTC off-by-one');

test('sbMonthLabel exists as a named function (one derivation, not two)', () => {
  extract('sbMonthLabel');
});

test('no date-only string is handed to new Date() for a month label', () => {
  // The exact shipped defect. Anchored on the expression, not on a line number.
  assert.ok(!/new Date\(\s*m\s*\+\s*'-01'\s*\)/.test(SRC),
    "new Date(m+'-01') still present -- that is the UTC-midnight parse");
  assert.ok(!/new Date\(\s*mo\s*\+\s*'-01'\s*\)/.test(SRC),
    "new Date(mo+'-01') still present");
});

test('both charts call the shared helper', () => {
  assert.ok(rendererLine('d-rev').includes('sbMonthLabel('),
    '#d-rev does not call sbMonthLabel');
  assert.ok(rendererLine('pl-monthly').includes('sbMonthLabel('),
    '#pl-monthly does not call sbMonthLabel');
});

test('LIVE CASE, America/New_York: the three months the app actually rendered', () => {
  // Reproduces the deployed reading verbatim. As shipped this returned
  // ['Apr 2026','May 2026','Aug 2026'].
  const sbMonthLabel = extract('sbMonthLabel');
  const before = process.env.TZ;
  try {
    process.env.TZ = 'America/New_York';
    assert.deepStrictEqual(
      ['2026-05', '2026-06', '2026-09'].map(sbMonthLabel),
      ['May 2026', 'Jun 2026', 'Sep 2026']);
  } finally { if (before === undefined) delete process.env.TZ; else process.env.TZ = before; }
});

test('every month of a year is right in four zones, both sides of Greenwich', () => {
  // Two negative offsets (where the defect bites), UTC, and one positive
  // offset (to prove the fix does not push the other way instead).
  const sbMonthLabel = extract('sbMonthLabel');
  const NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const before = process.env.TZ;
  try {
    for (const tz of ['America/New_York', 'Pacific/Honolulu', 'UTC', 'Asia/Tokyo']) {
      process.env.TZ = tz;
      for (let m = 1; m <= 12; m++) {
        const key = '2026-' + String(m).padStart(2, '0');
        assert.strictEqual(sbMonthLabel(key), NAMES[m - 1] + ' 2026',
          tz + ' rendered ' + key + ' as ' + sbMonthLabel(key));
      }
      // The January boundary is where an off-by-one also eats the YEAR.
      assert.strictEqual(sbMonthLabel('2027-01'), 'Jan 2027', tz + ' year boundary');
    }
  } finally { if (before === undefined) delete process.env.TZ; else process.env.TZ = before; }
});

test('a malformed month is returned as-is, never as a wrong month', () => {
  const sbMonthLabel = extract('sbMonthLabel');
  assert.strictEqual(sbMonthLabel(''), '');
  assert.strictEqual(sbMonthLabel('nonsense'), 'nonsense');
  assert.strictEqual(sbMonthLabel(null), '');
});

test('the label is ESCAPED at both render sites -- it echoes the date field', () => {
  // FOUND BY GUARDIAN CHECK 25 DURING THIS OWN FIX, 2026-09-30. The month key
  // is `(i.date||'').slice(0,7)` -- seven characters of a user-entered invoice
  // date. The shipped code fed it to new Date() and got "Invalid Date" back, so
  // it was safe BY ACCIDENT; returning the string unchanged (which is right,
  // because inventing a month would be the original defect again) puts those
  // seven characters straight into innerHTML unless they are escaped.
  for (const id of ['d-rev', 'pl-monthly']) {
    assert.ok(/H\(sbMonthLabel\(/.test(rendererLine(id)),
      '#' + id + ' injects the month label unescaped');
  }
  // And the escaper must actually be reached for a hostile value.
  const sbMonthLabel = extract('sbMonthLabel');
  assert.strictEqual(sbMonthLabel('<img sr'), '<img sr',
    'the function silently rewrote a malformed key instead of returning it');
});

// ═════════════════════════════════════════════════════════════════════════════
section('7b. THE TWO CHARTS SAY WHICH BASIS THEY ARE ON');

test('#d-rev still sums i.paid -- the math is not what changed', () => {
  assert.ok(/byMonth\[mo\]=\(byMonth\[mo\]\|\|0\)\+\(i\.paid\|\|0\)/.test(SRC),
    'the dashboard chart no longer sums i.paid');
});

test('#d-rev is no longer titled Revenue, because it is cash received', () => {
  const card = SRC.split('\n').find(l => l.includes('id="d-rev"'));
  assert.ok(card, 'could not find the #d-rev card markup');
  assert.ok(!/Revenue Trend YTD/.test(card),
    'the card still reads "Revenue Trend YTD" over a sum of i.paid');
  assert.ok(/Cash Collected/i.test(card),
    'the card does not say it is cash collected: ' + card.trim());
});

test('#pl-monthly sums i.amt and says so', () => {
  assert.ok(/byMonth\[mo\]=\(byMonth\[mo\]\|\|0\)\+i\.amt/.test(SRC),
    'the P&L chart no longer sums i.amt');
  const card = SRC.split('\n').find(l => l.includes('id="pl-monthly"'));
  assert.ok(card, 'could not find the #pl-monthly card markup');
  assert.ok(/Invoiced/i.test(card),
    'the P&L card does not name its basis (invoiced): ' + card.trim());
});

test('the "Monthly Revenue" KPI no longer claims a comparison it never draws', () => {
  // k-rev = invs.reduce(s + i.paid) over EVERY invoice ever. It is not monthly
  // and there is no last month on screen to be "vs".
  const kpi = SRC.split('\n').find(l => l.includes('id="k-rev"'));
  assert.ok(kpi, 'could not find the #k-rev KPI markup');
  assert.ok(!/vs last month/.test(kpi),
    'the KPI still reads "vs last month" and no comparison is computed');
  assert.ok(!/>Monthly Revenue</.test(kpi),
    'the KPI still reads "Monthly Revenue" over an all-time cash total');
});

// ═════════════════════════════════════════════════════════════════════════════
section('11. LARGEST VENDOR -- aggregated by vendor, not by bill');

test('sbTopVendorByBalance exists as a named function', () => {
  extract('sbTopVendorByBalance');
});

test('THE DEFECT: three small bills from one vendor beat one large bill', () => {
  const f = extract('sbTopVendorByBalance');
  const bills = [
    { vendor: 'Alpha Stone', bal: 1000 },
    { vendor: 'Alpha Stone', bal: 1000 },
    { vendor: 'Alpha Stone', bal: 1000 },
    { vendor: 'Beta Supply', bal: 2500 }
  ];
  // As shipped this returned Beta Supply -- the largest single BILL.
  assert.strictEqual(f(bills).name, 'Alpha Stone');
  assert.strictEqual(f(bills).bal, 3000);
});

test('vendor names differing only by case and padding are one vendor', () => {
  const f = extract('sbTopVendorByBalance');
  const bills = [
    { vendor: ' Alpha Stone ', bal: 900 },
    { vendor: 'ALPHA STONE', bal: 900 },
    { vendor: 'Beta Supply', bal: 1500 }
  ];
  assert.strictEqual(f(bills).name.toLowerCase().trim(), 'alpha stone');
  assert.strictEqual(f(bills).bal, 1800);
});

test('settled and zero-balance bills do not make a vendor the largest', () => {
  const f = extract('sbTopVendorByBalance');
  assert.strictEqual(f([{ vendor: 'Gamma', bal: 0 }, { vendor: 'Delta', bal: 5 }]).name, 'Delta');
  assert.strictEqual(f([{ vendor: 'Gamma', bal: 0 }]), null);
  assert.strictEqual(f([]), null);
  assert.strictEqual(f(null), null);
});

test('an unnamed vendor is not aggregated into a blank bucket that wins', () => {
  const f = extract('sbTopVendorByBalance');
  const r = f([{ vendor: '', bal: 9999 }, { vendor: 'Named', bal: 1 }]);
  assert.strictEqual(r.name, 'Named');
});

test('a tie is broken by name, so two renders cannot disagree', () => {
  const f = extract('sbTopVendorByBalance');
  const a = f([{ vendor: 'Zeta', bal: 100 }, { vendor: 'Alpha', bal: 100 }]);
  const b = f([{ vendor: 'Alpha', bal: 100 }, { vendor: 'Zeta', bal: 100 }]);
  assert.strictEqual(a.name, b.name);
});

test('the AP panel uses it', () => {
  assert.ok(/sbTopVendorByBalance\(bills\)/.test(SRC),
    'rAP() does not call sbTopVendorByBalance');
  assert.ok(!/bills\.filter\(function\(b\)\{return b\.bal>0;\}\)\.sort/.test(SRC),
    'the per-bill sort is still there');
});

test('the two panels state different questions, so the answers may differ', () => {
  const ap = SRC.split('\n').find(l => l.includes('id="ap-top"'));
  const vn = SRC.split('\n').find(l => l.includes('id="vn-top"'));
  assert.ok(ap && vn, 'could not find both vendor KPI markups');
  assert.ok(!/>By balance</.test(ap), 'AP sub-label is still the ambiguous "By balance"');
  assert.ok(!/>By spend</.test(vn), 'Vendors sub-label is still the ambiguous "By spend"');
  assert.ok(/owed/i.test(ap), 'AP sub-label does not say it is what is owed: ' + ap.trim());
  assert.ok(/paid/i.test(vn) && /year/i.test(vn),
    'Vendors sub-label does not say it is paid this year: ' + vn.trim());
});

// ═════════════════════════════════════════════════════════════════════════════
section('10. A HELD BILL SAYS WHY BEFORE IT IS CLICKED');

test('sbBillAction exists as a named function', () => {
  extract('sbBillAction');
});

test('a matched bill is payable', () => {
  const f = extract('sbBillAction');
  const r = f({ status: 'Open', matched: true }, { ok: true, reasons: [] });
  assert.strictEqual(r.payable, true);
  assert.strictEqual(r.paid, false);
});

test('a paid bill is neither payable nor refused', () => {
  const f = extract('sbBillAction');
  const r = f({ status: 'Paid', matched: true }, { ok: true, reasons: [] });
  assert.strictEqual(r.paid, true);
  assert.strictEqual(r.payable, false);
});

test('THE DEFECT: a held bill is not payable AND carries its reason', () => {
  const f = extract('sbBillAction');
  const r = f({ status: 'Held', matched: false, vendor: 'Midwest Stone Supply', amt: 640,
                match_reasons: ['no purchase order number on this bill'] },
              { ok: false, reasons: ['no purchase order number on this bill'] });
  assert.strictEqual(r.payable, false);
  assert.strictEqual(r.reason, 'no purchase order number on this bill');
});

test('BOTH halves of the gate are honoured, same as sbPayBill', () => {
  const f = extract('sbBillAction');
  // Stored verdict true, live evaluation false -- a PO deleted after entry.
  assert.strictEqual(f({ status: 'Open', matched: true },
                       { ok: false, reasons: ['the purchase order is gone'] }).payable, false);
  // Stored verdict false, live evaluation true -- a PO corrected after entry.
  assert.strictEqual(f({ status: 'Open', matched: false, match_reasons: ['no PO'] },
                       { ok: true, reasons: [] }).payable, false);
});

test('a refusal with no stated reason still says something, never blank', () => {
  const f = extract('sbBillAction');
  const r = f({ status: 'Open', matched: false }, { ok: false, reasons: [] });
  assert.strictEqual(r.payable, false);
  assert.ok(r.reason && r.reason.length > 0, 'reason was empty');
});

test('the AP row renderer uses it and disables the refusing button', () => {
  const row = rendererLine('aptbody');
  assert.ok(/sbBillAction\(/.test(row), 'the AP row does not call sbBillAction');
  assert.ok(/disabled/.test(row),
    'the AP row never renders a disabled control -- the refusal is still click-only');
});

test('the reason is rendered into the row, not only into the toast', () => {
  const row = rendererLine('aptbody');
  assert.ok(/\.reason/.test(row),
    'the row renderer never reads the refusal reason');
});

// ═════════════════════════════════════════════════════════════════════════════
section('8. A SURVIVING SESSION IS RESTORED, AND ONLY THE SERVER MAY SAY SO');

// Driven live 2026-09-30 against https://sairn.vercel.app/sairnbiz.html.
// Signed in, then reloaded. What came back:
//
//   pin gate ................. display: flex     (the PIN screen is up)
//   sb_session_token ......... still present, 339 chars
//   sb_session_role .......... still "owner"
//   that same token on /api/sd-data ... HTTP 200, 5 rows
//
// SO THE RE-LOGIN WAS NOT A SECURITY BOUNDARY. sessionStorage survives a
// reload by definition -- it is cleared when the TAB closes, not when the page
// does -- and the token was still live and still accepted. The app simply never
// re-applied it: sbApplyLoggedIn() is reachable only from sbDoLogin() and
// sbDoBootstrap(), so nothing restores a session that was never lost.
//
// AND THE TWO HALVES DISAGREED WITH EACH OTHER. sbBackupFetch() reads that same
// sessionStorage token directly, so the sync layer kept using the credential
// while the screen said signed out. Retyping the PIN minted a second session
// for a user who already had one.
//
// It is fixed by RESTORING, not by clearing: the token is a signed 12h bearer
// (api/_lib/auth.js SESSION_TTL_MS). Deleting the browser's copy does not
// revoke it, so clearing would have bought the appearance of security and none
// of it, at the cost of a PIN on every reload.
//
// THE RESTORE IS SERVER-CHECKED, because a local token is attacker-writable.
// Driven, same session, same resource:
//
//   real token ............. HTTP 200
//   garbage token .......... HTTP 401 NO_SESSION
//   empty token ............ HTTP 401 NO_SESSION
//   tampered signature ..... HTTP 401 NO_SESSION
//
// The probe discriminates, so it is a check and not a rubber stamp. The auth
// check also runs BEFORE the provisioning check -- a garbage token against an
// unprovisioned resource still answers 401 -- which is why 503 counts as
// "the session was accepted" below and only 401/403 count as refused.

async function withStubs(opts, body) {
  const saved = {};
  const set = (k, v) => { saved[k] = globalThis[k]; globalThis[k] = v; };
  const store = Object.assign({}, opts.session || {});
  const calls = { applied: [], fetched: 0, removed: [] };
  set('SB_SESSION_KEY', 'sb_session_token');
  set('SB_ROLE_KEY', 'sb_session_role');
  set('SB_EMPLOYEE_KEY', 'sb_session_employee_id');
  set('DATA_API', 'https://example.invalid/api/sd-data');
  set('sessionStorage', {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: k => { calls.removed.push(k); delete store[k]; }
  });
  set('ld', (k, d) => (k === 'sb_lic' ? ('lic' in opts ? opts.lic : 'SB-TEST-2026') : d));
  set('sbApplyLoggedIn', role => { calls.applied.push(role); });
  set('fetch', () => {
    calls.fetched++;
    if (opts.reject) return Promise.reject(new Error('network'));
    return Promise.resolve({ status: opts.status, ok: opts.status >= 200 && opts.status < 300 });
  });
  // AWAITED inside the try, not returned from it. Restoring the globals while
  // the body's promise is still in flight would pull the stubs out from under
  // the function under test.
  try { return await body(calls, store); }
  finally { for (const k of Object.keys(saved)) {
    if (saved[k] === undefined) delete globalThis[k]; else globalThis[k] = saved[k]; } }
}
const LIVE = { sb_session_token: 'tok', sb_session_role: 'owner', sb_session_employee_id: 'e1' };

test('sbRestoreSession exists as a named function', () => {
  extract('sbRestoreSession');
});

test('the boot block attempts the restore', () => {
  const boot = SRC.slice(SRC.lastIndexOf("$('pin').classList.add('on')"));
  assert.ok(/sbRestoreSession\(/.test(boot),
    'the boot block never calls sbRestoreSession');
});

test('no token: no request is made at all', () => withStubs({ session: {}, status: 200 }, async (c) => {
  const f = extract('sbRestoreSession');
  assert.strictEqual(await f(), false);
  assert.strictEqual(c.fetched, 0, 'it called the server with no token to check');
  assert.deepStrictEqual(c.applied, []);
}));

test('no licence: no request is made', () => withStubs({ session: LIVE, lic: null, status: 200 }, async (c) => {
  const f = extract('sbRestoreSession');
  assert.strictEqual(await f(), false);
  assert.strictEqual(c.fetched, 0);
}));

test('THE FIX: a token the server accepts restores the session', () =>
  withStubs({ session: LIVE, status: 200 }, async (c) => {
    const f = extract('sbRestoreSession');
    assert.strictEqual(await f(), true);
    assert.strictEqual(c.fetched, 1, 'it restored without asking the server');
    assert.deepStrictEqual(c.applied, ['owner']);
  }));

test('an unprovisioned resource still proves the session (auth is checked first)', () =>
  withStubs({ session: LIVE, status: 503 }, async (c) => {
    const f = extract('sbRestoreSession');
    assert.strictEqual(await f(), true);
    assert.deepStrictEqual(c.applied, ['owner']);
  }));

test('401 REFUSED: the gate stays up and the dead token is cleared', () =>
  withStubs({ session: LIVE, status: 401 }, async (c, store) => {
    const f = extract('sbRestoreSession');
    assert.strictEqual(await f(), false);
    assert.deepStrictEqual(c.applied, [], 'it let a refused token in');
    assert.strictEqual(store.sb_session_token, undefined, 'the dead token was left behind');
    assert.strictEqual(store.sb_session_role, undefined);
    assert.strictEqual(store.sb_session_employee_id, undefined);
  }));

test('403 REFUSED: same as 401', () =>
  withStubs({ session: LIVE, status: 403 }, async (c, store) => {
    const f = extract('sbRestoreSession');
    assert.strictEqual(await f(), false);
    assert.deepStrictEqual(c.applied, []);
    assert.strictEqual(store.sb_session_token, undefined);
  }));

test('COULD NOT TELL is a third state: 500 neither restores NOR clears', () =>
  withStubs({ session: LIVE, status: 500 }, async (c, store) => {
    const f = extract('sbRestoreSession');
    assert.strictEqual(await f(), false);
    assert.deepStrictEqual(c.applied, [], 'a 500 must not be read as a valid session');
    assert.strictEqual(store.sb_session_token, 'tok',
      'a server error signed the user out of a session that may be perfectly good');
  }));

test('COULD NOT TELL: a network failure neither restores NOR clears', () =>
  withStubs({ session: LIVE, reject: true, status: 0 }, async (c, store) => {
    const f = extract('sbRestoreSession');
    assert.strictEqual(await f(), false);
    assert.deepStrictEqual(c.applied, []);
    assert.strictEqual(store.sb_session_token, 'tok',
      'going offline threw away a valid session');
  }));

test('a token with no stored role does not restore as a blank role', () =>
  withStubs({ session: { sb_session_token: 'tok' }, status: 200 }, async (c) => {
    const f = extract('sbRestoreSession');
    assert.strictEqual(await f(), false);
    assert.deepStrictEqual(c.applied, [], "it applied a session with no role");
  }));

test('the token is sent as X-SD-Auth, so the server can actually judge it', () => {
  const src = SRC.slice(SRC.indexOf('function sbRestoreSession('));
  assert.ok(/X-SD-Auth/i.test(src.slice(0, 1400)),
    'sbRestoreSession does not send the session header');
});

// ═════════════════════════════════════════════════════════════════════════════
chain.then(() => {
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
});
