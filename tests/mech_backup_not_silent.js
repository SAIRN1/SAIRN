// tests/mech_backup_not_silent.js
//
// REQUIREMENT: a SAIRNmechanical record that is NOT backed up to the server, or a
// collection that is NOT read back from it, is reported to the user's console by
// name rather than looking exactly like a backup or restore that succeeded
//
// Run:  node tests/mech_backup_not_silent.js
//
// SAIRNmechanical's server backup: a push or a read-back that DID NOT HAPPEN
// must say so, never read like one that did (cody b57, the not-run class in
// docs/recurring-bug-classes-2.md C2).
//
//   B  mechBackup(): with window.mechPushRecord missing it WARNS and returns
//      null -- every save site used to skip the push with no message at all.
//   H  mechHydrateAll(): a refused, unparseable or wrongly-shaped read WARNS
//      naming the collection, and a provisioned:false answer does NOT -- the
//      read used to return silently and merge 0, exactly like up to date.
//   X  ablation: the pre-b57 hydrate (silent returns, empty catch) is driven
//      through the same failure and must stay SILENT, so H measures the fix.
//   L  saveDoc / saveTakeoff: the record is ALREADY in localStorage at the
//      moment the push is called -- a setItem moved into the push's .then
//      stayed green before (cc b67 gap a).
//   P  mechPushOne(): a 200 {ok:true} with no `data` is TRUTHY, so saveDoc
//      says "synced" and not "Kept on this device only" (cc b67 gap b).
//   D  saveDoc: a second press while the first push is pending saves NOTHING,
//      and the hold is released on success, rejection and a throwing push
//      (cc b67 gap d -- a double click used to save a duplicate document).
//
// Functions are lifted from the shipped file by brace matching and run with
// stubs; no browser, no network. Exit 0 all pass, 1 any fail.

'use strict';
const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(path.join(__dirname, '..', 'sairnmechanical.html'), 'utf8');

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log('PASS  ' + name); return; }
  fail++; console.log('FAIL  ' + name + (detail ? '\n        ' + detail : ''));
}
function lift(decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('not found: ' + decl);
  let k = src.indexOf('{', i), depth = 0;
  for (; k < src.length; k++) {
    if (src[k] === '{') depth++;
    else if (src[k] === '}' && --depth === 0) return src.slice(i, k + 1);
  }
  throw new Error('unbalanced: ' + decl);
}

(async () => {
  // ── B. mechBackup ─────────────────────────────────────────────────────────
  const backupSrc = lift('function mechBackup(resource,rec){');
  function runBackup(win) {
    const warned = [];
    const fn = new Function('window', 'console', backupSrc + '\nreturn mechBackup;')(
      win, { warn: (m) => warned.push(String(m)) });
    return { out: fn('mech_quotes', { id: 1 }), warned };
  }
  {
    const r = runBackup({});
    ok('B1 no backup module: returns null, not undefined-as-success', r.out === null, String(r.out));
    ok('B2 ...and WARNS that the record was NOT backed up, naming the collection',
       r.warned.length === 1 && /NOT backed up/.test(r.warned[0]) && /mech_quotes/.test(r.warned[0]),
       JSON.stringify(r.warned));
  }
  {
    const r = runBackup({ mechPushRecord: (res, rec) => 'pushed:' + res });
    ok('B3 CONTROL: with the module present it pushes and says nothing',
       r.out === 'pushed:mech_quotes' && r.warned.length === 0, JSON.stringify(r));
  }

  // ── H. mechHydrateAll ─────────────────────────────────────────────────────
  const hydrateSrc = lift('function mechHydrateAll() {');
  async function runHydrate(src, answer, localValue) {
    const warned = [];
    const store = { k1: localValue === undefined ? '[]' : localValue };
    const fn = new Function(
      'mechLic', 'mechData', 'MECH_SYNCED', 'MECH_ID_FIELD', 'mechSt', 'localStorage', 'console',
      src + '\nreturn mechHydrateAll;')(
      () => 'LIC',
      () => (answer instanceof Error ? Promise.reject(answer) : Promise.resolve(answer)),
      [['mech_quotes', 'k1']], {},
      (k, v) => { store[k] = JSON.stringify(v); return true; },
      { getItem: (k) => store[k] },
      { warn: (m) => warned.push(String(m)) });
    const merged = await fn();
    return { merged, warned };
  }
  const cases = [
    ['a 500', { status: 500, body: { ok: false } }, undefined, true],
    ['an unparseable body (mechData gives {})', { status: 200, body: {} }, undefined, true],
    ['a non-list data field', { status: 200, body: { ok: true, data: { x: 1 } } }, undefined, true],
    ['a corrupt local copy', { status: 200, body: { ok: true, data: [{ id: 9 }] } }, '{not json', true],
    ['a network error', new Error('offline'), undefined, true],
    // THE SERVER'S REAL UNPROVISIONED ANSWER (api/sd-data.js, MECH_RECORDS
    // read branch): ok:true, an empty list, provisioned:false. This fixture
    // was {ok:false,provisioned:false} -- a shape the server never sends, so
    // the arm drove a branch real traffic does not reach (cc b67 gap c).
    ['provisioned:false, the real {ok:true,data:[],provisioned:false} answer',
     { status: 200, body: { ok: true, data: [], provisioned: false } }, undefined, false],
    ['an up-to-date empty list', { status: 200, body: { ok: true, data: [] } }, undefined, false]
  ];
  for (const [label, answer, local, shouldWarn] of cases) {
    const r = await runHydrate(hydrateSrc, answer, local);
    ok('H ' + label + (shouldWarn ? ' WARNS, naming mech_quotes' : ' does NOT warn'),
       shouldWarn ? (r.warned.length === 1 && /mech_quotes/.test(r.warned[0]) && /NOT read back/.test(r.warned[0]))
                  : r.warned.length === 0,
       JSON.stringify(r));
  }
  {
    const r = await runHydrate(hydrateSrc, { status: 200, body: { ok: true, data: [{ id: 7 }] } });
    ok('H CONTROL: a real new row still merges (1) silently', r.merged === 1 && r.warned.length === 0, JSON.stringify(r));
  }

  // ── X. ablation: the pre-b57 body, same failure, must be silent ──────────
  const old = hydrateSrc
    .replace(/function unread\(why\) \{[\s\S]*?\n      \}\n/, '')
    .replace(/if \(!r \|\| r\.status !== 200 \|\| !r\.body \|\| !r\.body\.ok\) \{[\s\S]*?return;\n        \}/,
             'if (!r || r.status !== 200 || !r.body || !r.body.ok) return;')
    .replace(/\.catch\(function \(e\) \{ unread\([^)]*\)[^}]*\}\)/, '.catch(function () {})');
  ok('X0 the ablation actually applied: no unread() helper, the silent return and the empty catch are back',
     old.indexOf('function unread') < 0
       && /!r\.body\.ok\) return;/.test(old)
       && /\.catch\(function \(\) \{\}\)/.test(old),
     'ablation did not apply -- X1 would be measuring the fixed body');
  {
    let r;
    try { r = await runHydrate(old, { status: 500, body: { ok: false } }); } catch (e) { r = { error: String(e) }; }
    ok('X1 ABLATION: the old body says NOTHING about a 500 -- so H measures the fix',
       r && !r.error && r.warned.length === 0 && r.merged === 0, JSON.stringify(r));
  }

  // ── shared harness for the two save sites ────────────────────────────────
  // mechBackup is the seam: each call records what localStorage held AT THAT
  // MOMENT, then answers with whatever `push` returns (or throws).
  const flush = () => new Promise((r) => setImmediate(r));
  // The guard declaration is lifted if it exists, so the pre-fix file (no
  // declaration, no reference) runs unchanged and D1 measures the fix.
  const guardDecl = (src.match(/var mechDocSaving\s*=\s*false;/) || [''])[0];
  function makeSave(decl, outId, key, push) {
    const store = {}, toasts = [], pushes = [];
    const env = {
      document: { getElementById: (id) => (id === outId ? { textContent: 'WO 4417 RTU-4' } : null) },
      localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } },
      showToast: (m) => toasts.push(String(m)),
      mechRedactLocal: (t) => ({ text: t, redacted: false }),
      mechBackup: (res, rec) => { pushes.push({ res, rec, localAtPush: store[key] }); return push(res, rec); },
      APP_ID: 'APP', MECH_REDACT_NOTE: 'note'
    };
    const names = Object.keys(env);
    const fnName = decl.slice('function '.length, decl.indexOf('('));
    const fn = new Function(...names, guardDecl + '\n' + lift(decl) + '\nreturn ' + fnName + ';')(
      ...names.map((n) => env[n]));
    const rows = () => { try { return JSON.parse(store[key] || '[]'); } catch (e) { return null; } };
    return { fn, store, toasts, pushes, rows };
  }
  const inLocalAtPush = (p) => {
    try { return JSON.parse(p.localAtPush || '[]').some((x) => x && x.id === p.rec.id); } catch (e) { return false; }
  };

  // ── L. the local write comes BEFORE the push ─────────────────────────────
  for (const [label, decl, outId, key, res] of [
    ['saveDoc', 'function saveDoc(){', 'doc-out', 'APP_docs', 'mech_docs'],
    ['saveTakeoff', 'function saveTakeoff(){', 'bp-out', 'APP_takeoffs', 'mech_takeoffs']
  ]) {
    const s = makeSave(decl, outId, key, () => Promise.resolve({ id: 1 }));
    s.fn();
    await flush();
    ok('L ' + label + ': the record is already in localStorage when the push is called',
       s.pushes.length === 1 && s.pushes[0].res === res && inLocalAtPush(s.pushes[0]),
       JSON.stringify({ pushes: s.pushes, store: s.store }));
  }

  // ── P. mechPushOne: truthy on success even with no `data` ────────────────
  const pushOneSrc = lift('function mechPushOne(resource, rec) {');
  function makePushOne(answer) {
    const warned = [];
    const fn = new Function('MECH_ID_FIELD', 'mechData', 'console', pushOneSrc + '\nreturn mechPushOne;')(
      {}, () => Promise.resolve(answer), { warn: (m) => warned.push(String(m)) });
    return { fn, warned };
  }
  {
    const p = makePushOne({ status: 200, body: { ok: true } });
    const out = await p.fn('mech_docs', { id: 5 });
    ok('P1 a 200 {ok:true} with NO data is truthy, not undefined', out === true && p.warned.length === 0,
       JSON.stringify({ out, warned: p.warned }));
  }
  {
    const p = makePushOne({ status: 200, body: { ok: true, data: { id: 5, text: 'x' } } });
    const out = await p.fn('mech_docs', { id: 5 });
    ok('P2 CONTROL: a 200 with the stored row returns that row', out && out.id === 5 && out.text === 'x',
       JSON.stringify(out));
  }
  {
    const p = makePushOne({ status: 503, body: { ok: false } });
    const out = await p.fn('mech_docs', { id: 5 });
    ok('P3 CONTROL: a refused write returns null and warns', out === null && p.warned.length === 1,
       JSON.stringify({ out, warned: p.warned }));
  }
  {
    const p = makePushOne({ status: 200, body: { ok: true } });
    const s = makeSave('function saveDoc(){', 'doc-out', 'APP_docs', (res, rec) => p.fn(res, rec));
    s.fn();
    await flush(); await flush();
    ok('P4 saveDoc over a 200 {ok:true} with no data says "Saved and synced", not "Kept on this device only"',
       s.toasts.length === 1 && /^Saved and synced/.test(s.toasts[0]), JSON.stringify(s.toasts));
  }

  // ── D. one save at a time ────────────────────────────────────────────────
  {
    let answer;
    const s = makeSave('function saveDoc(){', 'doc-out', 'APP_docs',
      () => new Promise((r) => { answer = r; }));
    s.fn();
    await flush();
    s.fn();                       // the double click, push still pending
    await flush();
    const rows = s.rows();
    ok('D1 a second save while the first push is pending creates NO second record, and says so',
       rows && rows.length === 1 && s.pushes.length === 1 && s.toasts.some((t) => /Still saving/.test(t)),
       JSON.stringify({ rows: rows && rows.length, pushes: s.pushes.length, toasts: s.toasts }));
    if (answer) answer({ id: 1 });
    await flush(); await flush();
    s.fn();
    await flush();
    ok('D2 once the push answers, the next save goes through',
       s.rows().length === 2 && s.pushes.length === 2, JSON.stringify({ rows: s.rows().length, toasts: s.toasts }));
  }
  for (const [label, push] of [
    ['a REJECTED push', () => Promise.reject(new Error('offline'))],
    ['a push that THROWS', () => { throw new Error('boom'); }]
  ]) {
    const s = makeSave('function saveDoc(){', 'doc-out', 'APP_docs', push);
    let threw = null;
    try { s.fn(); await flush(); await flush(); s.fn(); await flush(); await flush(); } catch (e) { threw = String(e); }
    ok('D3 after ' + label + ' the hold is released: the next save goes through, and each says "Kept on this device only"',
       !threw && s.rows().length === 2 && s.toasts.filter((t) => /^Kept on this device only/.test(t)).length === 2,
       JSON.stringify({ threw, rows: s.rows().length, toasts: s.toasts }));
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
