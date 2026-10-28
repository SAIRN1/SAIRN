// tests/mech_backup_not_silent.js
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
    ['provisioned:false (a real answer)', { status: 200, body: { ok: false, provisioned: false } }, undefined, false],
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

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
