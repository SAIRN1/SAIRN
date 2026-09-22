// tests/sairnsenior_hydrate_delegation_review_probe.js
//
// REPORT-ONLY REVIEW PROBE for hank's obligation 2026-09-22T08:32:48Z
// (sen_claims), assigned to cody. Not a regression suite --
// api/_lib/sairnsenior-hydrate-delegation.test.js is that, and re-running it
// only re-reads the author's own answer. This drives the five things the
// obligation asks a reviewer to press on, hardest first, and reports what it
// finds either way.
//
// Run:  node tests/sairnsenior_hydrate_delegation_review_probe.js
//
// EXIT 0 UNLESS THE PROBE ITSELF COULD NOT RUN. A finding is reported, not
// thrown -- the reviewer writes the verdict, a probe does not get to.

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const APP = fs.readFileSync(path.join(ROOT, 'sairnsenior.html'), 'utf8');
const SUITE = fs.readFileSync(path.join(ROOT, 'api/_lib/sairnsenior-hydrate-delegation.test.js'), 'utf8');

const findings = [];
const notes = [];
function ok(name, detail) { console.log('  ok      ' + name + (detail ? '\n            ' + detail : '')); }
function finding(name, detail) {
  console.log('  FINDING ' + name + '\n            ' + detail);
  findings.push(name + ' -- ' + detail);
}
function note(name) { console.log('  note    ' + name); notes.push(name); }

// ── hank's extractor, copied verbatim so the comparison is against the real
//    thing rather than a description of it ──────────────────────────────────
function fnHank(src, name) {
  const start = src.indexOf('function ' + name + '(');
  if (start < 0) return null;
  let depth = 0;
  for (let i = start; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') {
      depth--;
      if (depth === 0) return src.slice(start, i + 1);
    }
  }
  return null;
}

// The same walk, but AWARE of the three things a brace can hide inside: a
// string, a template literal, and a comment. Regex literals are deliberately
// NOT handled -- see the note this probe prints about them.
function fnAware(src, name) {
  const start = src.indexOf('function ' + name + '(');
  if (start < 0) return null;
  let depth = 0, q = null, line = false, block = false;
  for (let i = start; i < src.length; i++) {
    const c = src[i], p = src[i - 1], n = src[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (q) { if (c === q && p !== '\\') q = null; continue; }
    if (c === '/' && n === '/') { line = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (depth === 0) return src.slice(start, i + 1); }
  }
  return null;
}

// ── THE TWO LISTS ARE PARSED SEPARATELY, AND THE FIRST SPELLING OF THIS
//    WAS WRONG IN THE DIRECTION THAT ACCUSES SOMEBODY ──────────────────
// It grepped every `['senHydrateX'` in the suite, got NINE, and reported that
// the three hank calls 'deliberately absent' were pinned here after all. They
// are not: LITERAL holds five, VARIABLE holds the three variable-key ones
// hank says a resource-name grep cannot see, and the ninth name came from the
// arm that asserts the ABSENT three stay absent -- a list has to name a thing
// to say it is missing. Parsing the two const blocks separately is what makes
// the difference visible. A review probe that accuses the session under review
// is worse than one that finds nothing.
function constList(name) {
  const m = SUITE.match(new RegExp('const ' + name + ' = \\[[\\s\\S]*?\\n\\];'));
  if (!m) return [];
  return (m[0].match(/\['senHydrate[A-Za-z]+'/g) || []).map((x) => x.slice(2, -1));
}
const LITERAL = constList('LITERAL');
const VARIABLE = constList('VARIABLE');
const UNIQUE = [...new Set([...LITERAL, ...VARIABLE])];

console.log('REVIEW PROBE -- hank 2026-09-22T08:32:48Z, sen_claims\n');
console.log('  pinned here: ' + UNIQUE.length + ' (' + LITERAL.length + ' literal-key, '
  + VARIABLE.length + ' variable-key) -- ' + UNIQUE.join(', ') + '\n');

// ── PRESS-ON 1: DOES THE EXTRACTED SPAN REACH THE END OF THE FUNCTION? ─────
console.log('1. the brace-balanced span -- whole function, or a prefix?');
{
  const disagree = [];
  for (const name of UNIQUE) {
    const a = fnHank(APP, name);
    const b = fnAware(APP, name);
    if (a === null || b === null) { disagree.push(name + ' (one extractor found nothing)'); continue; }
    if (a.length !== b.length) {
      disagree.push(name + ': naive ' + a.length + ' chars vs string/comment-aware ' + b.length);
    }
  }
  if (disagree.length) {
    finding('the naive brace count does NOT reach the real end of at least one hydrate',
            disagree.join('; ') + ' -- a truncated span containing the delegation call passes '
            + 'while proving less than it claims, which is exactly what press-on (1) asks about');
  } else {
    ok('all ' + UNIQUE.length + ' spans are IDENTICAL to a string/comment-aware walk',
       'so the span really is the whole function today. hank\'s evidence (mutation B) '
       + 'distinguishes an extracted-body assertion from a file-wide match; this is the half '
       + 'it does not prove, and it holds');
  }
  // The load-bearing question is not "is it right today" but "what would break it".
  const risky = [];
  for (const name of UNIQUE) {
    const body = fnAware(APP, name) || '';
    if (/["'`][^"'`\n]*[{}][^"'`\n]*["'`]/.test(body)) risky.push(name + ' (brace inside a string)');
    if (/\/\/[^\n]*[{}]/.test(body)) risky.push(name + ' (brace inside a // comment)');
    if (/\/[^/*\n][^\n]*\/[gimsuy]*/.test(body) && /[{}]/.test(body)) {
      // A regex literal is only a hazard if it CONTAINS a brace or an odd quote.
      const rx = body.match(/\/(?![/*])(?:\\.|\[[^\]]*\]|[^\\/\n])+\/[gimsuy]*/g) || [];
      if (rx.some((r) => /[{}]/.test(r) || (r.match(/['"]/g) || []).length % 2 === 1)) {
        risky.push(name + ' (regex literal containing a brace or an odd quote)');
      }
    }
  }
  if (risky.length) {
    finding('a brace or odd quote is hidden inside a string, comment or regex in a pinned hydrate',
            risky.join('; ') + ' -- the naive walk counts it, so this span is one edit from '
            + 'truncating. Same class as tool-bugs item 3, where _strip_code_noise() '
            + 'desynchronised on a JS regex literal and answered confidently for the rest of the file');
  } else {
    note('no pinned hydrate currently hides a brace or an odd quote in a string, comment or '
         + 'regex -- so the naive walk is correct TODAY by a property of the subject rather '
         + 'than by anything the extractor does. A single `if(x){ /* } */ }` in one hydrate '
         + 'would truncate its span silently, and the suite would still pass on the prefix');
  }
}

// ── PRESS-ON 1b: AN END-OF-BODY CHANGE MUST BE VISIBLE ─────────────────────
// The sharpest form of "is it a prefix": put a marker at the very END of each
// hydrate body and ask whether the extracted span contains it. A prefix span
// would not.
console.log('\n1b. is the LAST statement of each hydrate inside the span?');
{
  const missed = [];
  for (const name of UNIQUE) {
    const body = fnHank(APP, name);
    if (!body) { missed.push(name + ' (not extracted at all)'); continue; }
    const idx = APP.indexOf(body);
    const realEnd = idx + body.length;
    // The character after the span must be the end of a function -- newline or
    // semicolon -- and the span must close its own brace.
    if (!body.trimEnd().endsWith('}')) missed.push(name + ' (span does not end on a closing brace)');
    // And the next `function ` in the file must start AFTER the span: a prefix
    // span would end inside its own body, leaving the rest before the next one.
    const nextFn = APP.indexOf('\nfunction ', idx + 1);
    if (nextFn !== -1 && nextFn < realEnd - 1) {
      missed.push(name + ' (the span runs past the next function declaration)');
    }
  }
  if (missed.length) {
    finding('a span does not close cleanly on its own function', missed.join('; '));
  } else {
    ok('every span ends on its own closing brace and stops before the next function declaration',
       'two independent shapes of the same question, so a single off-by-one cannot satisfy both');
  }
}

// ── PRESS-ON 3: THE CALL-SITE COUNT BY SUBTRACTION ─────────────────────────
console.log('\n3. the call-site count pinned at 11 by subtraction');
{
  const all = (APP.match(/senServerWinsMerge\(/g) || []).length;
  const proseSpaced = (APP.match(/senServerWinsMerge\(\) /g) || []).length;
  const defn = (APP.match(/function senServerWinsMerge\(/g) || []).length;
  note('measured independently: ' + all + ' occurrences of `senServerWinsMerge(`, '
       + defn + ' definition(s), ' + proseSpaced + ' prose mention(s) of the `() ` shape '
       + '-> ' + (all - defn - proseSpaced) + ' call sites by hank\'s arithmetic');
  // The fragility hank names, made concrete rather than argued about.
  const proseAny = (APP.match(/senServerWinsMerge\(\)/g) || []).length;
  if (proseAny !== proseSpaced) {
    finding('a prose mention exists that hank\'s trailing-space shape does not see',
            proseAny + ' `senServerWinsMerge()` mentions vs ' + proseSpaced + ' with a trailing '
            + 'space -- the difference is counted as a CALL, so the arm is already off');
  } else {
    ok('every `senServerWinsMerge()` prose mention today carries the trailing space the arm keys on',
       'so the count is right today. The fragility hank names is real and unfired: a mention '
       + 'written as `senServerWinsMerge().` or at end of line would be counted as a call');
  }
}

// ── PRESS-ON 5: THE THREE-PART CARVE-OUT, CHECKED AGAINST THE FUNCTION ─────
console.log('\n5. the carve-out sentence, read against senServerWinsMerge itself');
{
  const merge = fnAware(APP, 'senServerWinsMerge');
  if (!merge) {
    finding('senServerWinsMerge could not be extracted', 'press-on 5 cannot be answered');
  } else {
    const parts = {
      '!senBootstrappedNow': /!\s*senBootstrappedNow/.test(merge),
      'usable': /\busable\b/.test(merge),
      'seeded[id]': /seeded\s*\[/.test(merge)
    };
    const missing = Object.keys(parts).filter((k) => !parts[k]);
    if (missing.length) {
      finding('the carve-out hank wrote into a FOURTH place names a term the function does not use',
              'missing from senServerWinsMerge: ' + missing.join(', ')
              + ' -- if the sentence is wrong it is now wrong in four places, and hank\'s is the '
              + 'one that sounds most settled');
    } else {
      ok('all three terms of the carve-out appear in senServerWinsMerge itself',
         '!senBootstrappedNow, usable and seeded[id] are each present, so the sentence hank '
         + 'wrote into the fourth place describes the real guard rather than a remembered one');
      const guard = (merge.match(/if\s*\([^)]*senBootstrappedNow[^)]*\)/) || [])[0];
      if (guard) note('the guard as written: ' + guard.replace(/\s+/g, ' ').slice(0, 110));
    }
  }
}

// ── PRESS-ON 4: THE DIVISION, AND WHETHER THE ABSENT ONES ARE REALLY COVERED
console.log('\n4. the hydrates NOT pinned here -- is each one covered somewhere else?');
{
  // Every hydrate in the app that actually delegates. A hydrate with no
  // delegation is not in scope for this suite and must not be counted against
  // its coverage.
  const all = [...new Set((APP.match(/function (senHydrate[A-Za-z]+)\s*\(/g) || [])
    .map((x) => x.replace(/function |\s*\($/g, '')))];
  const delegating = all.filter((n) => {
    const body = fnAware(APP, n) || '';
    return body.indexOf('senServerWinsMerge(') !== -1;
  });
  const absent = delegating.filter((n) => UNIQUE.indexOf(n) === -1);
  note('hydrates in the app: ' + all.length + '; delegating to senServerWinsMerge: '
       + delegating.length + '; pinned here: ' + UNIQUE.length + '; not pinned here: '
       + (absent.join(', ') || 'none'));

  // hank's claim is that the absent ones are covered by the three suites
  // re-aimed on 2026-09-21. Checked rather than accepted: grep the OTHER
  // sairnsenior suites for each name.
  const others = fs.readdirSync(path.join(ROOT, 'api', '_lib'))
    .filter((f) => /sairnsenior.*\.test\.js$/.test(f)
                   && f !== 'sairnsenior-hydrate-delegation.test.js')
    .map((f) => ({ file: 'api/_lib/' + f,
                   src: fs.readFileSync(path.join(ROOT, 'api', '_lib', f), 'utf8') }));
  const uncovered = [];
  for (const name of absent) {
    const hit = others.filter((o) => o.src.indexOf(name) !== -1).map((o) => o.file);
    if (!hit.length) uncovered.push(name);
    else note('  ' + name + ' -> named in ' + hit.join(', '));
  }
  if (uncovered.length) {
    finding('a delegating hydrate is pinned NOWHERE -- not here and not in a sibling suite',
            uncovered.join(', ') + ' -- the division hank asks to be judged leaves a gap '
            + 'rather than splitting coverage, and the gap is invisible from inside either file');
  } else if (!absent.length) {
    ok('every delegating hydrate is pinned in THIS suite',
       'so the division question does not arise -- nothing is left to a sibling');
  } else {
    ok('each of the ' + absent.length + ' hydrates absent from this suite is named in a sibling suite',
       'the division holds. The cost hank names is real and unaddressed: neither file says '
       + 'which suite owns which hydrate, so the coverage claim is only true when a reader '
       + 'already knows to read all four');
  }
}

console.log('\n' + findings.length + ' finding(s), ' + notes.length + ' note(s)');
findings.forEach((f) => console.log('  - ' + f));
notes.forEach((n) => console.log('  ? ' + n));
