// tests/merge_by_id_overwrite.js
// Run: node tests/merge_by_id_overwrite.js
//
// The three client merge functions -- dntMergeById, grdMergeById, scpMergeById
// -- are byte-identical in shape and all three replaced a local record with the
// server's and SAID NOTHING. An edit made on this device since the last sync
// was destroyed with no error, no toast and no console line.
//
// WHAT THIS DOES NOT TEST, because the code deliberately does not do it: it is
// NOT updated_at-based conflict resolution. Measured on the real files before
// any of this was written -- no record in any of the three apps carries a
// modification timestamp, the server's `updated_at` is a COLUMN and the generic
// read is `select=data`, so it never reaches the client. A merge comparing
// local.updated_at with sr.updated_at would compare undefined with undefined on
// every record and resolve server-wins exactly as before, while LOOKING like a
// fix. Arm 7 pins that the fields genuinely are absent, so the day somebody
// adds them this file says so.
//
// THE FUNCTIONS ARE EXTRACTED FROM THE LIVE FILES, not copied here. A copy
// would pass forever after the real one changed -- the exact failure this
// platform keeps finding. If the extraction stops matching, that is a red.

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
function extract(file, prefix) {
  const src = fs.readFileSync(path.join(ROOT, file), 'utf8');
  const grab = (name) => {
    const at = src.indexOf('function ' + name + '(');
    assert.ok(at >= 0, name + ' not found in ' + file + ' -- extraction is stale');
    // brace-match from the first { after the signature
    let i = src.indexOf('{', at), depth = 0, end = -1;
    for (let j = i; j < src.length; j++) {
      if (src[j] === '{') depth++;
      else if (src[j] === '}') { depth--; if (depth === 0) { end = j + 1; break; } }
    }
    assert.ok(end > 0, name + ' braces did not balance in ' + file);
    return src.slice(at, end);
  };
  const code = grab(prefix + 'StableStr') + '\n' + grab(prefix + 'MergeById') +
    '\nreturn {merge: ' + prefix + 'MergeById, stable: ' + prefix + 'StableStr};';
  return new Function(code)();
}

const APPS = [
  ['sairndental.html', 'dnt'],
  ['sairngrounds.html', 'grd'],
  ['sairnscape.html', 'scp']
];

for (const [file, prefix] of APPS) {
  const { merge, stable } = extract(file, prefix);
  const L = () => [{ id: 'a', v: 1 }, { id: 'b', v: 2 }];

  test(prefix + ': a DIFFERING server record is reported, not silently swallowed', () => {
    const c = [];
    const out = merge(L(), [{ id: 'a', v: 99 }], c);
    assert.deepStrictEqual(c, ['a'], JSON.stringify(c));
    assert.strictEqual(out.find((r) => r.id === 'a').v, 99,
      'server still wins -- this reports the loss, it does not change the rule');
  });

  test(prefix + ': CONTROL -- an IDENTICAL server record is NOT reported', () => {
    const c = [];
    merge(L(), [{ id: 'a', v: 1 }], c);
    assert.deepStrictEqual(c, [],
      'the common case is the server returning the row this device pushed; ' +
      'reporting that would bury the real ones');
  });

  test(prefix + ': key ORDER is not a difference -- or every record would report', () => {
    const c = [];
    merge([{ id: 'a', x: 1, y: 2 }], [{ id: 'a', y: 2, x: 1 }], c);
    assert.deepStrictEqual(c, [],
      'plain JSON.stringify would call these different and make the signal useless');
  });

  test(prefix + ': nested key order is not a difference either', () => {
    const c = [];
    merge([{ id: 'a', o: { p: 1, q: [1, { m: 1, n: 2 }] } }],
          [{ id: 'a', o: { q: [1, { n: 2, m: 1 }], p: 1 } }], c);
    assert.deepStrictEqual(c, [], 'the stable stringify must recurse');
  });

  test(prefix + ': ARRAY ORDER still IS a difference -- order is data', () => {
    const c = [];
    merge([{ id: 'a', tags: ['x', 'y'] }], [{ id: 'a', tags: ['y', 'x'] }], c);
    assert.deepStrictEqual(c, ['a'],
      'sorting array elements would hide a real reordering');
  });

  test(prefix + ': a server record with a NEW id is appended and is NOT a conflict', () => {
    const c = [];
    const out = merge(L(), [{ id: 'z', v: 9 }], c);
    assert.strictEqual(out.length, 3);
    assert.deepStrictEqual(c, [], 'nothing local was replaced');
  });

  test(prefix + ': a local-only record survives and is never reported', () => {
    const c = [];
    const out = merge(L(), [{ id: 'a', v: 1 }], c);
    assert.ok(out.find((r) => r.id === 'b'), 'local-only row must survive');
    assert.deepStrictEqual(c, []);
  });

  test(prefix + ': BACKWARD COMPATIBLE -- calling with no out-array behaves as before', () => {
    const out = merge(L(), [{ id: 'a', v: 99 }]);
    assert.strictEqual(out.find((r) => r.id === 'a').v, 99);
    assert.strictEqual(out.length, 2);
  });

  test(prefix + ': several differing records are ALL named, not just counted', () => {
    const c = [];
    merge(L(), [{ id: 'a', v: 9 }, { id: 'b', v: 8 }], c);
    assert.deepStrictEqual(c.sort(), ['a', 'b']);
  });

  test(prefix + ': null/!id entries do not throw and do not report', () => {
    const c = [];
    const out = merge([null, { id: 'a', v: 1 }], [{ id: null, v: 1 }, { id: 'a', v: 1 }], c);
    assert.deepStrictEqual(c, []);
    assert.ok(Array.isArray(out));
  });

  test(prefix + ': stable stringify handles primitives and null without throwing', () => {
    assert.strictEqual(stable(null), 'null');
    assert.strictEqual(stable(1), '1');
    assert.strictEqual(stable('s'), '"s"');
    assert.strictEqual(stable(undefined), 'null', 'undefined must not yield the string "undefined"');
  });
}

// ── 7. the premise this fix rests on, pinned so it cannot rot silently ────
test('NO app carries a record-level modification timestamp -- the reason this is ' +
     'disclosure and not updated_at resolution', () => {
  for (const [file] of APPS) {
    const src = fs.readFileSync(path.join(ROOT, file), 'utf8');
    // Strip comments: this file's own explanation NAMES updated_at repeatedly,
    // and matching that would be the comment-quoting class (process rules 1.2).
    const code = src.replace(/\/\*[\s\S]*?\*\//g, ' ')
                    .split('\n').filter((l) => !/^\s*\/\//.test(l)).join('\n');
    const assigns = code.match(/(updated_at|modified_at|_ts)\s*[:=]\s*(new Date|Date\.now)/g) || [];
    assert.deepStrictEqual(assigns, [],
      file + ' now stamps records (' + assigns.join(', ') + ') -- a real ' +
      'updated_at comparison has become possible and this disclosure-only ' +
      'merge should be upgraded. That is the point of this arm.');
  }
});

console.log(passed + ' passed');
