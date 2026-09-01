// Every seeded jurisdiction must have a display label.
//
// WHY THIS FILE EXISTS. `jurLabel()` in api/legal-deadlines.js is
// `JURISDICTION_LABELS[code] || code`, so a jurisdiction with no entry falls
// back to its own two-letter code and nothing anywhere reports it. On
// 2026-09-01, TWELVE of the thirty-six live jurisdictions were doing exactly
// that -- al, ar, de, hi, id, ks, md, ms, ne, nh, nm and wi. Every one had
// been seeded after the map was last extended, and a lawyer picking a
// jurisdiction in the UI saw "nh" rather than "New Hampshire".
//
// It is the same shape as the two other silent-fallback defects found the same
// day: `service_methods` dropped by the endpoint, and `service_extension.order`
// read by nothing. A missing entry is indistinguishable from a deliberate one
// unless something compares the two lists, so this file compares them.
//
// THE SOURCE OF TRUTH IS THE SEED FILES ON DISK, not a hand-kept roster. A new
// state's seed lands and this file fails on the same commit, before the label
// can go missing in production.

const fs = require('fs');
const path = require('path');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

const SQL = path.join(__dirname, '..', '..', 'sql');
const ENDPOINT = path.join(__dirname, '..', 'legal-deadlines.js');

// Every jurisdiction that appears in any seed file.
const seeded = new Set();
for (const f of fs.readdirSync(SQL)) {
  if (!/^sairnlaw_deadline_seed_.*\.json$/.test(f)) continue;
  let doc;
  try { doc = JSON.parse(fs.readFileSync(path.join(SQL, f), 'utf8')); } catch (e) { continue; }
  for (const r of (doc.rules || [])) if (r.jurisdiction) seeded.add(r.jurisdiction);
}

// The label map, read out of the endpoint source. It is a module-level const
// in a file that exports only a handler, so parsing is the available route --
// the same approach deadline-endpoint-inputs.test.js takes to the payload.
const src = fs.readFileSync(ENDPOINT, 'utf8');
const start = src.indexOf('const JURISDICTION_LABELS = {');
check('the label map was found in the endpoint', start !== -1, true);
let i = start + 'const JURISDICTION_LABELS = {'.length, depth = 1, body = '';
while (i < src.length && depth > 0) {
  const ch = src[i];
  if (ch === '{') depth++;
  else if (ch === '}') depth--;
  if (depth > 0) body += ch;
  i++;
}
const bodyNoComments = body.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
const labelled = new Set(
  [...bodyNoComments.matchAll(/(?:^|,)\s*'?([a-z][a-z-]*)'?\s*:/g)].map(m => m[1])
);

check('the map parsed and is not empty', labelled.size >= 20, true);
check('the seed scan found a plausible number of jurisdictions', seeded.size >= 30, true);

const unlabelled = [...seeded].filter(j => !labelled.has(j)).sort();
check('EVERY seeded jurisdiction has a display label', unlabelled, []);

// Named individually so a regression says which one, not just how many.
for (const j of ['de', 'nh', 'wi', 'md', 'al', 'ar', 'hi', 'id', 'ks', 'ms', 'ne', 'nm']) {
  check(j + ' has a label', labelled.has(j), true);
}

// The federal pseudo-jurisdiction is not in a state seed's jurisdiction field
// in the same way, so assert it separately rather than assuming the sweep saw it.
check('the federal jurisdiction is labelled', labelled.has('us-federal'), true);

// A label must not simply repeat the code -- that is the fallback wearing a
// disguise, and it would pass a presence check while showing the user nothing.
const echoed = [...labelled].filter(k => {
  const m = bodyNoComments.match(new RegExp("(?:^|,)\\s*'?" + k + "'?\\s*:\\s*'([^']+)'"));
  return m && m[1] === k;
});
check('no label is just the code repeated back', echoed, []);

console.log('\ndeadline-jurisdiction-labels: ' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
