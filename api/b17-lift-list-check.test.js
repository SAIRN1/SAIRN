// api/b17-lift-list-check.test.js
//
// Run:  node api/b17-lift-list-check.test.js
//
// REQUIREMENT: an `api/` suite that LIFTS a function out of an app's HTML page
//   must lift (or stub) every page-level function that function CALLS. A
//   missing callee is a `ReferenceError` at run time, which is a HARD ERROR
//   with no arm name and no counts -- a suite that is DEAD, not failing.
//
// ── IT HAS HAPPENED TWICE, AND THE SECOND TIME WAS THIS BATCH ─────────────
// b15 added `senEffClock` to sairnsenior.html and not to the lift lists of
// the three suites that extract `visitHours`/`azBurnDown`. All three died at
// "ReferenceError: senEffClock is not defined" before asserting anything --
// 191 arms, including every arm over `sen_pay_rates`, which is one of the
// resources an open Tier A obligation is written over. NONE of the three was
// in docs/known-red-suites.json, so they were invisible to anything that
// reads that file, and b16 found them only by running the whole api/ tree.
//
// THEN b17 ADDED `senIsOwner` TO `_renderCorrectionsRows` AND
// api/b14-clock-approval-two-person.test.js DIED THE SAME WAY, in the same
// session that was fixing the first instance. Two occurrences in two batches
// is the point at which a convention becomes a check. b16's handoff carried
// it as open item 2 with the exact next step, which is this file.
//
// ── WHAT IT CHECKS ───────────────────────────────────────────────────────
// For each api/ suite that lifts from an app HTML page:
//   1. collect the LIFT LIST -- every `fn('x')`, `lift('x')` and `NEEDED`
//      entry the suite names
//   2. for each lifted function's REAL SOURCE, collect every `name(` callee
//   3. a callee is a FINDING when it is a PAGE-LEVEL `function name(` in that
//      same HTML, is NOT in the lift list, and is NOT supplied by the suite's
//      own sandbox/stubs
//
// ── WHAT IT DOES NOT CHECK, SAID PLAINLY ────────────────────────────────
// FREE VARIABLES. `senIsOwner()` reads the page-level variable `prole`, which
// is not a function and would not be caught here -- and that is the SECOND
// error b14 hit this batch, after the callee one. Covering it means resolving
// every identifier against a real scope chain, which is a parser and not a
// regex. NAMED rather than quietly out of scope, and recorded as owed work in
// the b17 handoff. A suite that printed only what it covers would read as
// though it covered both.
//
// ALSO NOT CHECKED: a callee reached through a property (`obj.fn()`), a
// dynamically named call, or a function the page defines as `var f =
// function(){}` rather than `function f(){}`. The third is measured below
// (arm L5) so the gap has a size rather than a shrug.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');

const API = __dirname;
const ROOT = path.join(__dirname, '..');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 3000));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 800));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

// ── JS KEYWORDS AND BUILT-INS that look like calls and are not page code ──
const NOT_A_CALLEE = {};
('if for while switch catch return typeof function new delete void do else '
 + 'String Number Boolean Array Object JSON Math Date RegExp Error Promise Map '
 + 'Set WeakMap parseInt parseFloat isNaN isFinite encodeURIComponent '
 + 'decodeURIComponent setTimeout clearTimeout setInterval alert confirm '
 + 'prompt require await async of in instanceof').split(' ')
  .forEach((k) => { NOT_A_CALLEE[k] = true; });

// ── THE SUITES THAT LIFT, and the page each lifts from ───────────────────
// DISCOVERED, not listed: a hand-written list of suites is the staleness this
// whole file exists to stop.
function walk(dir, out) {
  fs.readdirSync(dir, { withFileTypes: true }).forEach((e) => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== 'node_modules') walk(p, out); return; }
    if (/\.test\.js$/.test(e.name)) out.push(p);
  });
  return out;
}

// THE HTML THE SUITE REALLY READS. A suite that reads no HTML is NOT a
// lifting suite, whatever its local helpers happen to be called -- `fn(` is
// also an ordinary callback-parameter name. Requiring a readFileSync of an
// .html file is what tells the two apart, and it is why L2 reports an
// out-of-scope suite as OUT OF SCOPE with its reason rather than as a suite
// this check failed to understand.
function pageOf(src) {
  // Two real spellings, measured rather than assumed:
  //   readFileSync(path.join(ROOT, 'sairnsenior.html'), 'utf8')     -- b1x suites
  //   const HTML = path.join(__dirname,'..','..','sairnsenior.html');
  //   const src  = fs.readFileSync(HTML, 'utf8');                   -- _lib suites
  // The second is why the first draft of this function reported seven real
  // lifting suites as "reads no HTML": it only looked INSIDE the
  // readFileSync() parentheses, and those suites put the filename in a
  // variable one line above. A checker that mis-classifies the majority of
  // its population as out of scope is the silent-universe failure, and it
  // reported CLEAN over four suites instead of eleven.
  const direct = /readFileSync\(([^;]{0,200}?)\)/g;
  let m;
  while ((m = direct.exec(src)) !== null) {
    const h = /['"]([A-Za-z0-9._-]+\.html)['"]/.exec(m[1]);
    if (h) return h[1];
  }
  // A filename assigned to a variable that is then read. The ASSIGNMENT plus a
  // readFileSync of that variable, both required -- a filename in a comment is
  // still not a read.
  const assign = /\b(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=[^;]{0,200}?['"]([A-Za-z0-9._-]+\.html)['"]/g;
  while ((m = assign.exec(src)) !== null) {
    const varName = m[1], file = m[2];
    if (new RegExp('readFileSync\\(\\s*' + varName + '\\b').test(src)) return file;
  }
  return null;
}

// ── STRINGS AND COMMENTS ARE NOT CODE, and this cost the first draft ─────
// The page is full of `onclick="blSetRate(...)"` inside template strings. A
// callee regex over raw source reads every one of those as a call, which
// produced sixteen "missing callees" for a four-line function. Stripped
// before any callee scan.
function stripStringsAndComments(s) {
  let out = '';
  let i = 0;
  const n = s.length;
  while (i < n) {
    const c = s[i];
    if (c === '/' && s[i + 1] === '/') {
      while (i < n && s[i] !== '\n') i += 1;
      continue;
    }
    if (c === '/' && s[i + 1] === '*') {
      i += 2;
      while (i < n && !(s[i] === '*' && s[i + 1] === '/')) i += 1;
      i += 2;
      continue;
    }
    if (c === '\'' || c === '"' || c === '`') {
      const q = c;
      i += 1;
      while (i < n && s[i] !== q) {
        if (s[i] === '\\') i += 1;
        i += 1;
      }
      i += 1;
      out += '""';
      continue;
    }
    out += c;
    i += 1;
  }
  return out;
}

function liftListOf(src) {
  const names = {};
  // fn('x') and lift('x') -- the two helper spellings in use.
  let m;
  const call = /\b(?:fn|lift)\(\s*'([A-Za-z_$][A-Za-z0-9_$]*)'\s*\)/g;
  while ((m = call.exec(src)) !== null) names[m[1]] = true;
  // A NEEDED/array-of-names list handed to lift()/fn() in bulk.
  const arr = /const\s+(?:NEEDED|FUNCS|LIFTS|NAMES)\s*=\s*\[([\s\S]*?)\]/g;
  while ((m = arr.exec(src)) !== null) {
    (m[1].match(/'([A-Za-z_$][A-Za-z0-9_$]*)'/g) || [])
      .forEach((q) => { names[q.replace(/'/g, '')] = true; });
  }
  // world([...]) / a bare array literal passed straight in.
  const w = /\b(?:world|build)\(\s*\[([\s\S]*?)\]\s*\)/g;
  while ((m = w.exec(src)) !== null) {
    (m[1].match(/'([A-Za-z_$][A-Za-z0-9_$]*)'/g) || [])
      .forEach((q) => { names[q.replace(/'/g, '')] = true; });
  }
  return names;
}

function stubbedOf(src) {
  // Anything the suite supplies itself: sandbox object keys, and
  // `'var X=...'` / `'var X=W.y'` strings injected into a new Function body.
  const names = {};
  let m;
  const key = /^\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*:/gm;
  while ((m = key.exec(src)) !== null) names[m[1]] = true;
  const varDecl = /\bvar\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=/g;
  while ((m = varDecl.exec(src)) !== null) names[m[1]] = true;
  const localFn = /\bfunction\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(/g;
  while ((m = localFn.exec(src)) !== null) names[m[1]] = true;
  const constDecl = /\bconst\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=/g;
  while ((m = constDecl.exec(src)) !== null) names[m[1]] = true;
  // `var x=W.y, z=W.w;` destructuring-by-hand, used by the _lib suites.
  const multi = /\bvar\s+([A-Za-z_$][A-Za-z0-9_$,\s=.W]*);/g;
  while ((m = multi.exec(src)) !== null) {
    (m[1].match(/([A-Za-z_$][A-Za-z0-9_$]*)\s*=/g) || [])
      .forEach((q) => { names[q.replace(/\s*=$/, '')] = true; });
  }
  return names;
}

// The page's own `function name(` declarations, and the body of each.
//
// BRACE-MATCHED, NOT SLICED TO THE NEXT DECLARATION. The first draft took
// html.slice(thisDeclaration, nextDeclaration), which swallows everything in
// between whenever an intervening function is indented (the regex anchored on
// a newline) -- so a four-line function appeared to call sixteen things. That
// is b14's fixed-width-window lesson in a different costume: a span bounded by
// a GUESS instead of by the structure it is meant to cover.
function pageFunctions(html) {
  const defs = {};
  const re = /(^|\n)[ \t]*function ([A-Za-z_$][A-Za-z0-9_$]*)\s*\(/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    const name = m[2];
    const open = html.indexOf('{', m.index + m[0].length - 1);
    if (open === -1) continue;
    let depth = 0, i = open, end = -1;
    for (; i < html.length; i += 1) {
      const c = html[i];
      if (c === '{') depth += 1;
      else if (c === '}') { depth -= 1; if (!depth) { end = i; break; } }
      else if (c === '\'' || c === '"' || c === '`') {
        const q = c; i += 1;
        while (i < html.length && html[i] !== q) {
          if (html[i] === '\\') i += 1;
          i += 1;
        }
      }
    }
    if (end === -1) continue;
    // FIRST DECLARATION WINS. A duplicate global is a finding in its own
    // right and tools/html_script_check.py already owns it; here the point is
    // only that the body belongs to the function named.
    if (!defs[name]) defs[name] = html.slice(open, end + 1);
  }
  return defs;
}

function calleesIn(body) {
  const out = {};
  const code = stripStringsAndComments(body);
  let m;
  const re = /(^|[^.\w$])([A-Za-z_$][A-Za-z0-9_$]*)\s*\(/g;
  while ((m = re.exec(code)) !== null) {
    const n = m[2];
    if (!NOT_A_CALLEE[n]) out[n] = true;
  }
  return out;
}

// `override` maps a repo-relative suite path to replacement SOURCE TEXT, so
// an arm can re-run the whole scan against a hypothetical suite WITHOUT
// writing a mutant to disk. L7 uses it to replay both real incidents.
function scan(override) {
  const over = override || {};
  const findings = [];
  const suites = [];
  const outOfScope = [];
  walk(API, []).sort().forEach((f) => {
    const rel = path.relative(ROOT, f).split(path.sep).join('/');
    if (rel === 'api/b17-lift-list-check.test.js') return;   // not itself
    const src = Object.prototype.hasOwnProperty.call(over, rel)
      ? over[rel] : fs.readFileSync(f, 'utf8');
    const lifts = liftListOf(src);
    const names = Object.keys(lifts);
    if (!names.length) return;
    const page = pageOf(src);
    if (!page) {
      // OUT OF SCOPE, WITH ITS REASON, and NOT folded into L1's pass. A suite
      // that reads no HTML is not lifting from a page -- its `fn(` is an
      // ordinary callback name. L2 pins the COUNT of these, so a real lifting
      // suite cannot hide in the bucket.
      outOfScope.push({ file: rel, matched: names.length });
      return;
    }
    let html = null;
    try { html = fs.readFileSync(path.join(ROOT, page), 'utf8'); }
    catch (e) { html = null; }
    if (html === null) {
      findings.push({ file: rel, kind: 'NO_PAGE',
        detail: 'names ' + page + ', which could not be read' });
      return;
    }
    const defs = pageFunctions(html);
    const stubs = stubbedOf(src);
    const missing = [];
    names.forEach((n) => {
      const body = defs[n];
      if (!body) return;            // not a page-level function; L4 counts these
      Object.keys(calleesIn(body)).forEach((c) => {
        if (c === n) return;
        if (lifts[c] || stubs[c]) return;
        if (!defs[c]) return;       // not page code: a browser global etc.
        missing.push(n + ' -> ' + c);
      });
    });
    suites.push({ file: rel, page: page, lifted: names.length,
                  missing: missing });
    if (missing.length) {
      findings.push({ file: rel, kind: 'MISSING_CALLEE', detail: missing.join(', ') });
    }
  });
  return { findings: findings, suites: suites, outOfScope: outOfScope };
}

// ── THE BASELINE. Measured 2026-10-15 with B17_EMIT_BASELINE=1. ─────────
// Regenerate with:  B17_EMIT_BASELINE=1 node api/b17-lift-list-check.test.js
// Keyed by file and by `caller -> callee`, never by line number -- a
// line-keyed allowlist is itself a fixed-width window and would go red every
// time anything above it moved, which is the b14 defect wearing the gate's
// clothes.
const BASELINE = {
  'api/_lib/sairnsenior-authorizations.test.js': [
    'azPaint -> $',
    'azPaint -> H',
    'azPaint -> certDaysUntil',
    'azPaint -> senIsBroadRead',
    'azPaint -> senIsManagement',
    'openAzModal -> $',
    'openAzModal -> H',
    'openAzModal -> clients',
    'senHydrateAuthorizations -> senData',
    'senHydrateAuthorizations -> senIsBroadRead',
    'senHydrateAuthorizations -> senLicenseKey',
    'senHydrateAuthorizations -> senServerWinsMerge',
    'senHydrateAuthorizations -> senSyncedBootstrap',
  ],
  'api/_lib/sairnsenior-branches.test.js': [
    'brRollup -> $',
    'brRollup -> brPaint',
    'brRollup -> brRender',
    'brRollup -> closeBrModal',
    'brRollup -> fmt',
    'brRollup -> newId',
    'brRollup -> openBrModal',
    'brRollup -> senData',
    'brRollup -> senHydratePayRates',
    'brRollup -> senIsManagement',
    'brRollup -> st',
    'brRollup -> toast',
  ],
  'api/_lib/sairnsenior-franchise.test.js': [
    'brName -> brRollup',
    'brName -> caregivers',
    'brName -> hrAddDays',
    'brName -> visitHours',
    'brName -> visitLabourCost',
    'brName -> visits',
    'frPaint -> $',
    'frPaint -> fdate',
    'frPaint -> fmt',
    'frPaint -> senIsManagement',
  ],
  'api/_lib/sairnsenior-pay-rates.test.js': [
    'brRollup -> $',
    'brRollup -> brPaint',
    'brRollup -> brRender',
    'brRollup -> closeBrModal',
    'brRollup -> fmt',
    'brRollup -> newId',
    'brRollup -> openBrModal',
    'brRollup -> senData',
    'brRollup -> senIsManagement',
    'brRollup -> st',
    'brRollup -> toast',
    'senHydratePayRates -> senData',
    'senHydratePayRates -> senIsManagement',
    'senHydratePayRates -> senLicenseKey',
    'senHydratePayRates -> senServerWinsMerge',
    'senHydratePayRates -> senSyncedBootstrap',
  ],
  'api/_lib/sairnsenior-payer-contracts.test.js': [
    'senHydratePayerContracts -> senData',
    'senHydratePayerContracts -> senIsManagement',
    'senHydratePayerContracts -> senLicenseKey',
    'senHydratePayerContracts -> senServerWinsMerge',
    'senHydratePayerContracts -> senSyncedBootstrap',
  ],
  'api/b14-clock-approval-two-person.test.js': [
    '_renderCorrectionsRows -> vsRenderKpis',
  ],
};
const BASELINE_COUNT = Object.keys(BASELINE)
  .reduce((s, k) => s + BASELINE[k].length, 0);

function main() {
  console.log('api/b17-lift-list-check.test.js');
  console.log('  a lifted function\'s page-level callees must be lifted too');

  const r = scan();

  // ── L1: NO **NEW** UNLIFTED CALLEE ─────────────────────────────────────
  // A BASELINE GATE, AND THE REASON IS A MEASUREMENT RATHER THAN A PREFERENCE.
  // The scan is REACHABILITY-BLIND: it sees that `brRollup` calls
  // `openBrModal` and cannot know that no arm ever takes that branch. 57 such
  // pairs exist today across 6 suites, and every one of those suites is
  // GREEN -- so demanding zero would mean 57 edits to silence findings that
  // are not breaking anything, which is how a checker gets switched off.
  //
  // WHAT THE BASELINE STILL CATCHES IS EXACTLY THE DEFECT IT WAS BUILT FOR.
  // Both real incidents were a NEW callee appearing inside an ALREADY-LIFTED
  // function:
  //   b15  visitHours/azBurnDown gained senEffClock   -> 3 suites died, 191 arms
  //   b17  _renderCorrectionsRows gained senIsOwner   -> b14 died
  // Both are a new pair, so both fail L1. Arm L7 drives that claim rather
  // than asserting it.
  //
  // EXACT IN BOTH DIRECTIONS: a vanished baseline entry fails too, because a
  // tolerated-list that outlives its entries is how a gate stops testing
  // anything (cross-domain discipline 8).
  {
    const live = {};
    r.suites.forEach((s) => { if (s.missing.length) live[s.file] = s.missing.slice().sort(); });
    if (process.env.B17_EMIT_BASELINE) {
      console.log(JSON.stringify(live, null, 2));
      process.exit(0);
    }
    const added = [], gone = [];
    Object.keys(live).sort().forEach((f) => {
      const base = (BASELINE[f] || []).slice();
      live[f].forEach((p) => {
        const at = base.indexOf(p);
        if (at === -1) added.push(f + ' :: ' + p); else base.splice(at, 1);
      });
    });
    Object.keys(BASELINE).sort().forEach((f) => {
      const l = (live[f] || []).slice();
      BASELINE[f].forEach((p) => {
        const at = l.indexOf(p);
        if (at === -1) gone.push(f + ' :: ' + p); else l.splice(at, 1);
      });
    });
    const liveCount = Object.keys(live).reduce((s, f) => s + live[f].length, 0);
    is(added.length === 0 && gone.length === 0,
       'L1. NO NEW unlifted page-level callee, and no stale baseline entry. '
     + liveCount + ' tolerated pair(s) across ' + Object.keys(live).length
     + ' suite(s), ' + BASELINE_COUNT + ' in the baseline, over '
     + r.suites.length + ' lifting suite(s) scanned',
       (added.length
         ? 'NEW -- a lifted function now calls a page-level function this suite '
           + 'does not lift or stub. At run time that is "ReferenceError: <name> '
           + 'is not defined": a HARD ERROR with no arm name and no counts, '
           + 'which is a DEAD suite and not a failing one. Add it to the lift '
           + 'list, or stub it and say why:\n               '
           + added.join('\n               ')
         : '')
     + (gone.length
         ? (added.length ? '\n           ' : '')
           + 'STALE -- these baseline entries no longer exist. That is the good '
           + 'news: delete them from BASELINE.\n               '
           + gone.join('\n               ')
         : ''));
  }

  // ── L2: NOTHING WAS SKIPPED SILENTLY ──────────────────────────────────
  // Two different reasons a suite is not in L1, kept apart because they are
  // different answers. A NAMED page that cannot be READ is a real problem; a
  // suite that reads no HTML at all is out of scope and is COUNTED so the
  // bucket cannot quietly grow into a hiding place. Folding either into L1's
  // pass is PR 1.11 inside the checker itself.
  {
    const unreadable = r.findings.filter((f) => f.kind === 'NO_PAGE');
    const oos = r.outOfScope;
    is(unreadable.length === 0 && oos.length <= 1,
       'L2. no lifting suite was skipped silently: ' + unreadable.length
     + ' named a page that could not be read, and ' + oos.length
     + ' read no HTML at all and are OUT OF SCOPE with their name printed below',
       'unreadable: ' + unreadable.map((f) => f.file + ' -- ' + f.detail).join('; ')
     + ' | out of scope: ' + oos.map((f) => f.file + ' (' + f.matched
       + ' name(s) matched the lift pattern)').join('; '));
    oos.forEach((f) => {
      console.log('           OUT OF SCOPE  ' + f.file + ' -- reads no .html, so '
        + 'its ' + f.matched + ' pattern match(es) are not page lifts');
    });
  }

  // ── L3: THE SCAN FOUND A REAL POPULATION ──────────────────────────────
  // Without this arm an empty discovery -- a renamed helper, a moved
  // directory -- passes L1 and L2 forever over nothing.
  {
    const totalLifted = r.suites.reduce((s, x) => s + x.lifted, 0);
    is(r.suites.length >= 10 && totalLifted >= 40,
       'L3. the scan is over a real population: ' + r.suites.length
     + ' lifting suite(s) and ' + totalLifted + ' lifted name(s). An empty '
     + 'discovery would pass L1 and L2 over nothing, forever',
       'suites=' + r.suites.length + ' liftedNames=' + totalLifted);
  }

  // ── L4: THE DETECTOR FINDS A PLANTED MISS ─────────────────────────────
  // The real case, reproduced in memory: a page function that calls another
  // page function, with only the first in the lift list. Nothing is written
  // to disk, so there is no mutant to leave behind.
  {
    const html = '\nfunction outer(v){return inner(v)+1;}\n'
               + 'function inner(v){return v*2;}\n';
    const defs = pageFunctions(html);
    const lifts = { outer: true };
    const stubs = {};
    const found = [];
    Object.keys(lifts).forEach((n) => {
      Object.keys(calleesIn(defs[n] || '')).forEach((c) => {
        if (c !== n && !lifts[c] && !stubs[c] && defs[c]) found.push(n + ' -> ' + c);
      });
    });
    is(found.length === 1 && found[0] === 'outer -> inner',
       'L4. the detector flags a PLANTED miss (`outer` lifted, `inner` called '
     + 'and not lifted). Without this arm a broken regex passes L1 forever',
       'found=' + JSON.stringify(found));
  }

  // ── L5: AND THE SHAPE IT CANNOT SEE HAS A MEASURED SIZE ──────────────
  // `var f = function(){}` is not matched by the page-function scanner, so a
  // callee declared that way is invisible to L1. MEASURED on the real pages
  // rather than described, so the gap is a number and not a shrug.
  {
    const pages = {};
    r.suites.forEach((s) => { pages[s.page] = true; });
    const counts = [];
    Object.keys(pages).sort().forEach((p) => {
      let html = null;
      try { html = fs.readFileSync(path.join(ROOT, p), 'utf8'); }
      catch (e) { return; }
      const decl = (html.match(/\nfunction [A-Za-z_$][A-Za-z0-9_$]*\s*\(/g) || []).length;
      const expr = (html.match(/\n(?:var|let|const) [A-Za-z_$][A-Za-z0-9_$]*\s*=\s*function\s*\(/g) || []).length;
      counts.push(p + ': ' + decl + ' declarations, ' + expr
        + ' var-assigned function expressions (INVISIBLE to L1)');
    });
    is(counts.length > 0,
       'L5. the blind spot is MEASURED, not described -- ' + counts.join(' | ')
     + '. A callee declared `var f = function(){}` is not matched by the '
     + 'page-function scanner and L1 cannot see it',
       'no page could be read to measure the blind spot');
  }

  // ── L6: THE FREE-VARIABLE GAP IS STATED, because it bit THIS batch ───
  // `senIsOwner()` reads the page-level variable `prole`. b14's suite hit
  // "ReferenceError: prole is not defined" immediately AFTER the callee error
  // this check would have caught. Covering it needs a real scope chain.
  {
    const b14 = path.join(API, 'b14-clock-approval-two-person.test.js');
    let src = null;
    try { src = fs.readFileSync(b14, 'utf8'); } catch (e) { src = null; }
    is(src !== null && /prole:/.test(src),
       'L6. the FREE-VARIABLE gap is stated and is live: this check covers '
     + 'CALLEES, and api/b14-clock-approval-two-person.test.js also needed the '
     + 'page VARIABLE `prole` stubbed, which L1 would not have caught. That '
     + 'suite now stubs it with a comment saying so; the general check is '
     + 'owed work and is named in the b17 handoff',
       'b14 readable=' + (src !== null)
     + ' stubs prole=' + (src !== null && /prole:/.test(src)));
  }

  // ── L7: BOTH REAL INCIDENTS, REPLAYED AGAINST THIS CHECK ──────────────
  // The claim L1's baseline rests on is that the defect it was built for IS a
  // NEW pair. That is a claim, so it is driven: each incident is recreated by
  // REMOVING the callee from the suite's lift list in memory (nothing is
  // written to disk) and the scan is re-run. A new pair must appear for the
  // right caller and callee.
  //
  // If an incident does NOT produce a new pair, this gate would have slept
  // through it and the baseline design is wrong -- which is exactly what this
  // arm exists to find out.
  {
    const cases = [
      { file: 'api/b14-clock-approval-two-person.test.js',
        strip: 'senIsOwner', expect: '_renderCorrectionsRows -> senIsOwner',
        incident: 'b17 added senIsOwner to _renderCorrectionsRows' },
      { file: 'api/b15-client-effective-clock.test.js',
        strip: 'senEffClock', expect: 'visitHours -> senEffClock',
        incident: 'b15 added senEffClock to visitHours' }
    ];
    const results = [];
    cases.forEach((c) => {
      let src = null;
      try { src = fs.readFileSync(path.join(ROOT, c.file), 'utf8'); }
      catch (e) { src = null; }
      if (src === null) { results.push(c.file + ': UNREADABLE'); return; }
      // Remove the name from every lift-list spelling, and from any stub.
      const stripped = src
        .replace(new RegExp("'" + c.strip + "'\\s*,?", 'g'), '')
        .replace(new RegExp("\\b" + c.strip + "\\s*:", 'g'), '_removed_:');
      const r2 = scan({ [c.file]: stripped });
      const s2 = r2.suites.filter((x) => x.file === c.file)[0];
      const live = s2 ? s2.missing : [];
      const base = BASELINE[c.file] || [];
      const isNew = live.indexOf(c.expect) !== -1 && base.indexOf(c.expect) === -1;
      results.push(c.file + ': ' + (isNew ? 'CAUGHT' : 'MISSED')
        + ' (' + c.incident + ') live=' + JSON.stringify(live));
    });
    is(results.every((x) => /: CAUGHT /.test(x)),
       'L7. BOTH real incidents replayed: removing the callee from the lift '
     + 'list produces a NEW pair that L1\'s baseline would FAIL on. '
     + results.join(' | '),
       results.join('\n           '));
  }

  console.log('');
  r.suites.forEach((s) => {
    console.log('  scanned  ' + s.file + '  <- ' + s.page
      + '  (' + s.lifted + ' lifted, ' + s.missing.length + ' missing)');
  });
  console.log('');
  console.log('  passed ' + pass + '  failed ' + fail + '  unproven ' + unproven);
  if (fail) console.log('  FAILING ARMS: ' + failed.join(' '));
  if (unproven) console.log('  UNPROVEN ARMS: ' + notProved.join(' '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main();
