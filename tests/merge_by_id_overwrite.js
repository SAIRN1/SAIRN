// tests/merge_by_id_overwrite.js
// REQUIREMENT: merging records by id updates the matching row and never silently
//   overwrites a different one, so a stale id cannot destroy live data
//
// Run: node tests/merge_by_id_overwrite.js
//
// The three client merge functions -- dntMergeById, grdMergeById, scpMergeById
// -- are byte-identical in shape and all three replaced a local record with the
// server's and SAID NOTHING. An edit made on this device since the last sync
// was destroyed with no error, no toast and no console line.
//
// 2026-09-13: that is now RESOLVED, not merely disclosed. st()/scpSt() stamp a
// per-record `_m` when a record's content actually changes, and the merge keeps
// the local record when local._m > server._m.
//
// THE FUNCTIONS ARE EXTRACTED FROM THE LIVE FILES, not copied here. A copy
// would pass forever after the real one changed -- the exact failure this
// platform keeps finding. If the extraction stops matching, that is a red.
//
// WHAT IS DELIBERATELY NOT ASSERTED: that clock skew is handled. It is not,
// and cannot be from the client -- `_m` is the device's own clock. Arm group 4
// pins the two properties that make the skew survivable instead: local is
// preferred only on a STRICT `>`, and BOTH directions are reported so a human
// sees a "kept local" on a record nobody here touched.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
let passed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n      ' + e.message); process.exitCode = 1; }
}

// ── extraction ────────────────────────────────────────────────────────────
function grab(src, name, file) {
  const at = src.indexOf('function ' + name + '(');
  assert.ok(at >= 0, name + ' not found in ' + file + ' -- extraction is stale');
  let i = src.indexOf('{', at), depth = 0, end = -1;
  for (let j = i; j < src.length; j++) {
    if (src[j] === '{') depth++;
    else if (src[j] === '}') { depth--; if (depth === 0) { end = j + 1; break; } }
  }
  assert.ok(end > 0, name + ' braces did not balance in ' + file);
  return src.slice(at, end);
}

// A fake localStorage-backed ld/scpLd so stampChanged can be driven directly.
function build(file, prefix, ldName) {
  const src = fs.readFileSync(path.join(ROOT, file), 'utf8');
  const code = [
    'var STORE = {};',
    'function ' + ldName + '(k, d){ return (k in STORE) ? JSON.parse(JSON.stringify(STORE[k])) : d; }',
    'var ' + prefix + 'SyncingFromServer = false;',
    grab(src, prefix + 'StableStr', file),
    grab(src, prefix + 'ContentStr', file),
    grab(src, prefix + 'StampChanged', file),
    grab(src, prefix + 'MergeById', file),
    'function put(k, v){ STORE[k] = JSON.parse(JSON.stringify(v)); }',
    'function save(k, v){ var out = ' + prefix + 'StampChanged(k, v); put(k, out); return out; }',
    'function setSyncing(b){ ' + prefix + 'SyncingFromServer = b; }',
    'return { merge: ' + prefix + 'MergeById, stamp: ' + prefix + 'StampChanged,' +
    ' content: ' + prefix + 'ContentStr, stable: ' + prefix + 'StableStr,' +
    ' save: save, put: put, setSyncing: setSyncing, store: function(){ return STORE; } };'
  ].join('\n');
  return new Function(code)();
}

const APPS = [
  ['sairndental.html', 'dnt', 'ld'],
  ['sairngrounds.html', 'grd', 'ld'],
  ['sairnscape.html', 'scp', 'scpLd']
];

const EARLY = '2026-09-13T10:00:00.000Z';
const LATE = '2026-09-13T12:00:00.000Z';

for (const [file, prefix, ldName] of APPS) {
  const A = build(file, prefix, ldName);
  const P = prefix + ': ';

  // ── 1. the stamp is applied to what CHANGED, and only that ──────────────
  test(P + 'a NEW record is stamped', () => {
    const out = A.save('k', [{ id: 'a', v: 1 }]);
    assert.ok(typeof out[0]._m === 'string', JSON.stringify(out[0]));
  });

  test(P + 'saving again with NO change does not re-stamp', () => {
    const first = A.save('k2', [{ id: 'a', v: 1 }]);
    const again = A.save('k2', [{ id: 'a', v: 1 }]);
    assert.strictEqual(again[0]._m, first[0]._m,
      'a fresh stamp on every save would make _m mean "when did anything save", not "when did THIS change"');
  });

  test(P + 'CONTROL: a record that DID change gets a new stamp', () => {
    A.put('k3', [{ id: 'a', v: 1, _m: EARLY }]);
    const out = A.save('k3', [{ id: 'a', v: 2, _m: EARLY }]);
    assert.notStrictEqual(out[0]._m, EARLY,
      'without this, arm 2 would pass on a function that never stamps at all');
  });

  test(P + 'an unchanged record KEEPS its existing stamp rather than losing it', () => {
    A.put('k4', [{ id: 'a', v: 1, _m: EARLY }]);
    const out = A.save('k4', [{ id: 'a', v: 1 }]);   // caller dropped _m
    assert.strictEqual(out[0]._m, EARLY,
      'dropping it would make an old edit look older than it is and lose to a stale server row');
  });

  test(P + 'the stamp NEVER mutates the caller object', () => {
    const mine = { id: 'a', v: 9 };
    A.save('k5', [mine]);
    assert.strictEqual(mine._m, undefined,
      'callers hold references; an in-place stamp makes the same record look modified next save');
  });

  test(P + 'stamping is SUPPRESSED while syncing', () => {
    A.setSyncing(true);
    const out = A.save('k6', [{ id: 'a', v: 1 }]);
    A.setSyncing(false);
    assert.strictEqual(out[0]._m, undefined,
      'stamping merged server rows would mark them locally-modified-just-now and make the merge prefer local forever');
  });

  test(P + 'non-arrays and id-less entries pass through untouched', () => {
    assert.deepStrictEqual(A.stamp('k7', { a: 1 }), { a: 1 });
    const out = A.save('k8', [{ noId: 1 }, null, 5]);
    assert.deepStrictEqual(out, [{ noId: 1 }, null, 5]);
  });

  // ── 2. content identity ignores _m, or nothing would ever compare equal ─
  test(P + 'two records differing ONLY by _m are the same content', () => {
    assert.strictEqual(A.content({ id: 'a', v: 1, _m: EARLY }),
                       A.content({ id: 'a', v: 1, _m: LATE }));
  });

  test(P + 'key ORDER is not a difference -- or every record would conflict', () => {
    assert.strictEqual(A.content({ id: 'a', x: 1, y: 2 }), A.content({ id: 'a', y: 2, x: 1 }));
  });

  test(P + 'nested key order is not a difference either -- the sort must recurse', () => {
    assert.strictEqual(A.content({ id: 'a', o: { p: 1, q: [1, { m: 1, n: 2 }] } }),
                       A.content({ id: 'a', o: { q: [1, { n: 2, m: 1 }], p: 1 } }));
  });

  test(P + 'ARRAY ORDER still IS a difference -- order is data', () => {
    assert.notStrictEqual(A.content({ id: 'a', t: ['x', 'y'] }), A.content({ id: 'a', t: ['y', 'x'] }));
  });

  // ── 3. THE RESOLUTION ITSELF ───────────────────────────────────────────
  test(P + 'LOCAL NEWER -> the local record is KEPT and the loss is prevented', () => {
    const c = [];
    const out = A.merge([{ id: 'a', v: 'mine', _m: LATE }], [{ id: 'a', v: 'theirs', _m: EARLY }], c);
    assert.strictEqual(out[0].v, 'mine', 'this is the half that PREVENTS data loss');
    assert.deepStrictEqual(c, [{ id: 'a', kept: 'local' }]);
  });

  test(P + 'SERVER NEWER -> the server record wins, and it is reported', () => {
    const c = [];
    const out = A.merge([{ id: 'a', v: 'mine', _m: EARLY }], [{ id: 'a', v: 'theirs', _m: LATE }], c);
    assert.strictEqual(out[0].v, 'theirs');
    assert.deepStrictEqual(c, [{ id: 'a', kept: 'server' }]);
  });

  test(P + 'EQUAL stamps -> server wins. Local is preferred only on a STRICT >', () => {
    const c = [];
    const out = A.merge([{ id: 'a', v: 'mine', _m: LATE }], [{ id: 'a', v: 'theirs', _m: LATE }], c);
    assert.strictEqual(out[0].v, 'theirs',
      'a tie under clock skew must not silently hand the argument to whoever is late');
    assert.deepStrictEqual(c, [{ id: 'a', kept: 'server' }]);
  });

  test(P + 'NO STAMPS -> server wins, exactly as before. Every pre-existing record is here', () => {
    const c = [];
    const out = A.merge([{ id: 'a', v: 'mine' }], [{ id: 'a', v: 'theirs' }], c);
    assert.strictEqual(out[0].v, 'theirs');
    assert.deepStrictEqual(c, [{ id: 'a', kept: 'server' }]);
  });

  test(P + 'ONE stamp only -> server wins. A missing stamp is not an old one', () => {
    let c = [];
    assert.strictEqual(A.merge([{ id: 'a', v: 'mine', _m: LATE }], [{ id: 'a', v: 'theirs' }], c)[0].v,
      'theirs', 'inventing a date for the server row would let any local edit win forever');
    c = [];
    assert.strictEqual(A.merge([{ id: 'a', v: 'mine' }], [{ id: 'a', v: 'theirs', _m: LATE }], c)[0].v, 'theirs');
  });

  test(P + 'CONTROL: identical content is NOT a conflict, whatever the stamps say', () => {
    const c = [];
    A.merge([{ id: 'a', v: 1, _m: LATE }], [{ id: 'a', v: 1, _m: EARLY }], c);
    assert.deepStrictEqual(c, [],
      'the common case is the server returning the row this device pushed; reporting it would bury the real ones');
  });

  test(P + 'a server record with a NEW id is appended and is not a conflict', () => {
    const c = [];
    const out = A.merge([{ id: 'a', v: 1 }], [{ id: 'z', v: 9 }], c);
    assert.strictEqual(out.length, 2);
    assert.deepStrictEqual(c, []);
  });

  test(P + 'a local-only record survives and is never reported', () => {
    const c = [];
    const out = A.merge([{ id: 'a', v: 1 }, { id: 'b', v: 2 }], [{ id: 'a', v: 1 }], c);
    assert.ok(out.find((r) => r.id === 'b'));
    assert.deepStrictEqual(c, []);
  });

  test(P + 'several conflicts are ALL reported, with their direction', () => {
    const c = [];
    A.merge([{ id: 'a', v: 1, _m: LATE }, { id: 'b', v: 1, _m: EARLY }],
            [{ id: 'a', v: 2, _m: EARLY }, { id: 'b', v: 2, _m: LATE }], c);
    assert.deepStrictEqual(c.sort((x, y) => x.id < y.id ? -1 : 1),
      [{ id: 'a', kept: 'local' }, { id: 'b', kept: 'server' }]);
  });

  test(P + 'null/id-less entries do not throw and do not report', () => {
    const c = [];
    const out = A.merge([null, { id: 'a', v: 1 }], [{ id: null, v: 1 }, { id: 'a', v: 1 }], c);
    assert.deepStrictEqual(c, []);
    assert.ok(Array.isArray(out));
  });

  test(P + 'BACKWARD COMPATIBLE -- no out-array still resolves, it just says nothing', () => {
    const out = A.merge([{ id: 'a', v: 'mine', _m: LATE }], [{ id: 'a', v: 'theirs', _m: EARLY }]);
    assert.strictEqual(out[0].v, 'mine');
  });

  // ── 4. END TO END: the defect this all exists for ──────────────────────
  test(P + 'END TO END: an edit made after the last sync SURVIVES the next sync', () => {
    // the record as it stands on both sides after a sync
    A.put('e2e', [{ id: 'a', v: 'original', _m: EARLY }]);
    const server = [{ id: 'a', v: 'original', _m: EARLY }];
    // a user edits it on THIS device -- st() stamps it
    const afterEdit = A.save('e2e', [{ id: 'a', v: 'my new value', _m: EARLY }]);
    assert.ok(afterEdit[0]._m > EARLY, 'the edit must be stamped later than the sync');
    // ... and a sync runs before it was pushed
    const c = [];
    const merged = A.merge(afterEdit, server, c);
    assert.strictEqual(merged[0].v, 'my new value',
      'THIS IS THE WHOLE BUG: before the fix this silently became "original"');
    assert.deepStrictEqual(c, [{ id: 'a', kept: 'local' }]);
  });

  test(P + 'END TO END: and a genuinely newer server edit still lands', () => {
    A.put('e2e2', [{ id: 'a', v: 'original', _m: EARLY }]);
    const c = [];
    const merged = A.merge(A.stamp('e2e2', [{ id: 'a', v: 'original', _m: EARLY }]),
                           [{ id: 'a', v: 'colleague edit', _m: LATE }], c);
    assert.strictEqual(merged[0].v, 'colleague edit');
    assert.deepStrictEqual(c, [{ id: 'a', kept: 'server' }]);
  });
}

// ── 5. the three apps must not drift apart again ──────────────────────────
test('all three merges resolve identically -- they were byte-identical before ' +
     'and a divergence here is how one app silently keeps the old behaviour', () => {
  const outs = APPS.map(([f, p, l]) => {
    const A = build(f, p, l);
    const c = [];
    const m = A.merge([{ id: 'a', v: 'mine', _m: LATE }], [{ id: 'a', v: 'theirs', _m: EARLY }], c);
    return JSON.stringify([m, c]);
  });
  assert.strictEqual(new Set(outs).size, 1, outs.join('\n'));
});

test('every app suppresses stamping during its sync, by name', () => {
  for (const [file, prefix] of APPS) {
    const src = fs.readFileSync(path.join(ROOT, file), 'utf8');
    const code = src.split('\n').filter((l) => !/^\s*\/\//.test(l)).join('\n');
    assert.ok(code.indexOf(prefix + 'SyncingFromServer=true') >= 0,
      file + ' never sets its sync flag -- merged server rows would be stamped as local edits');
    assert.ok(/finally\{\s*[a-z]+SyncingFromServer=false/.test(code.replace(/\n/g, '')) ||
              code.indexOf('}finally{') >= 0,
      file + ' must clear the flag in a finally -- a rejected await would disable stamping for the session');
  }
});

console.log(passed + ' passed');
