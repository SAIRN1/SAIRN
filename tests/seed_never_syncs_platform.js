// tests/seed_never_syncs_platform.js
//
// Run:  node tests/seed_never_syncs_platform.js
//
// THE INVARIANT: on any app whose storage setter carries a server-backup hook,
// DEMO SEED DATA MUST NOT BE ABLE TO REACH THE SERVER.
//
// SAIRNvet broke it on 2026-09-10 and it was live -- the schema had been run.
// 39 of its 41 synced collections seeded demo rows lazily (every getX() wrote
// sample data on first read when the key was absent), st() carried the hook,
// and svSyncSuppressed was only ever set while HYDRATING. Opening the
// controlled-substance panel on a fresh device pushed invented Ketamine,
// Butorphanol and Fentanyl balances into a DEA-relevant register, and
// additive-only hydration with no delete path meant they spread and could not
// be removed from the app.
//
// THIS FILE EXISTS BECAUSE THAT WAS ONE INSTANCE OF A CLASS. Measured across
// all 22 root HTML files, FIVE carry an st()-hooked backup, and they are safe
// for three different reasons -- which is precisely why "it looked fine" was
// not evidence for any of them:
//
//   sairnbiz     one-pass sbSeedRows(), wrapped by sbSyncPaused in a finally
//   sairnbuild   one-pass bldSeedRows(), wrapped by bldSeeding in a finally
//   sairnvet     39 LAZY per-getter seeds, each wrapped by svSeedStore (today)
//   sairnfreedom safe by ABSENCE -- it seeds nothing at all
//   stonedesk    safe by ABSENCE -- all of its synced caches default to empty
//
// The last two are the reason this is a test and not a note. They are safe
// because nothing seeds those keys TODAY. Add one seeded default to a synced
// StoneDesk collection and it becomes SAIRNvet, with a suppression flag that
// only covers hydration and looks like it covers seeding.
//
// WHAT IS GATED, AND WHAT IS ONLY REPORTED. Sections 1, 2, 4 and 5 assert.
// Section 3 asserts on a LITERAL seed at the write site -- which, measured
// against the real pre-fix sairnvet.html, would NOT have caught this incident:
// its seeds are `var seed = [...]` then `saveX(seed)`, so the write site sees
// a variable and section 3 passes clean.
//
// Section 3b looks for that shape and is REPORT-ONLY on purpose. Four attempts
// at gating it produced, in order: a blind (NONE) on two correct apps, an
// unterminated regex that threw, a regex that matched nothing while printing
// ok, and finally two honest false positives on StoneDesk -- sdDrawingsAll()
// (a pure reader) and saveQuote() (a real user save). The heuristic cannot
// separate a seed from a save or a reader without parsing, and a checker that
// cries wolf gets routed around. So it PRINTS what it sees for a human to read
// and asserts only two things it can actually prove: that the scan still SEES
// sairnvet's 39 (a detector going blind must not read as an app being clean),
// and that none of them is unwrapped.
//
// A pass here is "no literal seed reaches a synced key, and sairnvet's 39 are
// still wrapped" -- never "no seed can possibly reach the server".

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   - ' + name); pass++; }
  catch (e) { console.log('  FAIL - ' + name + '\n         ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// True when a parsed default carries any real value, at any depth. An object
// of empty objects and empty arrays is a shape, not a seed.
function hasContent(v) {
  if (v === null || v === undefined) return false;
  if (Array.isArray(v)) return v.some(hasContent);
  if (typeof v === 'object') return Object.keys(v).some((k) => hasContent(v[k]));
  if (typeof v === 'string') return v.length > 0;
  return true;
}

function rootHtml() {
  const out = execFileSync('git', ['ls-files', '*.html'], { cwd: ROOT, encoding: 'utf8' });
  return out.split('\n').filter((f) => f && f.indexOf('/') === -1);
}

function bodyOf(src, at) {
  const open = src.indexOf('{', at);
  let d = 0;
  for (let i = open; i < src.length; i++) {
    if (src[i] === '{') d++;
    else if (src[i] === '}') { d--; if (d === 0) return { body: src.slice(at, i + 1), start: at, end: i + 1 }; }
  }
  return null;
}

// An app is IN SCOPE when its storage setter calls a *SyncCollection hook.
// DERIVED, not listed: an app that grows one tomorrow is picked up here rather
// than being quietly out of scope forever.
function hookedApps() {
  const found = [];
  rootHtml().forEach((file) => {
    const src = fs.readFileSync(path.join(ROOT, file), 'utf8').replace(/\r\n/g, '\n');
    const fnRe = /function (\w+)\(\s*\w+\s*,\s*\w+\s*\)\s*\{/g;
    let m;
    while ((m = fnRe.exec(src))) {
      const b = bodyOf(src, m.index);
      if (!b || b.body.indexOf('localStorage.setItem') === -1) continue;
      const hm = /\b(\w*SyncCollection)\s*\(/.exec(b.body);
      if (!hm) continue;
      found.push({ file, src, setter: m.group ? m.group(1) : m[1], hook: hm[1] });
      break;
    }
  });
  return found;
}

const APPS = hookedApps();

// The flag the hook returns early on. Read out of the hook's own guard lines
// rather than assumed, because the five apps spell it three different ways
// (sbSyncPaused, bldSeeding, sdSyncSuppressed/svSyncSuppressed/sfSyncSuppressed)
// and a name-shaped guess produced a BLIND (NONE) on sairnbiz the first time
// this was measured -- the exact portability trap sairn-portfolio-triage warns
// about.
function suppressionFlag(app) {
  const at = app.src.indexOf('function ' + app.hook + '(');
  const b = bodyOf(app.src, at);
  assert.ok(b, app.file + ': could not read ' + app.hook);
  const head = b.body.slice(0, 700);
  // EVERY identifier in every early-return guard, not the first one. The first
  // version captured only the leading identifier and reported sairnbiz and
  // sairnbuild as having NO GUARD -- their guards are
  // `if(sbSyncPaused||sbBackupUnavailable)return;` and
  // `if (!_bldSyncOn[key] || bldSeeding) return;`, so the flag is the SECOND
  // term. A blind (NONE) on two apps that are in fact correct is the exact
  // portability failure sairn-portfolio-triage documents; caught by the number
  // being implausible, not by the tool saying anything.
  const names = [];
  const gre = /if\s*\(([^)]*)\)\s*return/g;
  let mm;
  while ((mm = gre.exec(head))) {
    (mm[1].match(/[A-Za-z_$][\w$]*/g) || []).forEach((n) => names.push(n));
  }
  return names.filter((n) => /suppress|paused|seeding/i.test(n))[0] || null;
}

function syncedKeys(app) {
  const m = /var (\w*_?SYNCED)\s*=\s*\[([\s\S]*?)\]/.exec(app.src);
  if (!m) return [];
  return (m[2].match(/'([\w]+)'/g) || []).map((s) => s.replace(/'/g, ''));
}

// ═══════════════════════════════════════════════════════════════════════════
section('1. the scope is derived, and it is not empty');

test('every app with an st()-hooked backup is found', () => {
  const names = APPS.map((a) => a.file).sort();
  assert.ok(APPS.length >= 5,
    'only ' + APPS.length + ' hooked app(s) found -- the detector stopped matching, '
    + 'which would make every assertion below vacuous. Found: ' + names.join(', '));
  ['sairnbiz.html', 'sairnbuild.html', 'sairnfreedom.html', 'sairnvet.html', 'stonedesk.html']
    .forEach((f) => assert.ok(names.indexOf(f) !== -1, f + ' is no longer detected as hooked'));
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. every hooked app has a suppression flag its hook honours');

APPS.forEach((app) => {
  test(app.file + ' -- the hook returns early on a suppression flag', () => {
    const flag = suppressionFlag(app);
    assert.ok(flag, app.file + ': ' + app.hook + ' has no suppression guard, so nothing '
      + 'can stop a seed or a hydrate echoing back to the server');
    const setTrue = (app.src.match(new RegExp('\\b' + flag + '\\s*=\\s*true', 'g')) || []).length;
    assert.ok(setTrue >= 1, app.file + ': ' + flag + ' is read but never set');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
section('3. no synced key is written from a LITERAL seed outside a wrapped seeder');

APPS.forEach((app) => {
  test(app.file + ' -- literal seed writes are suppressed or absent', () => {
    const keys = syncedKeys(app);
    assert.ok(keys.length > 0, app.file + ': no *_SYNCED list found, so this check saw nothing');
    // Where the app's one-pass seeder lives, if it has one. Its whole body is
    // a permitted region only because the flag wraps the CALL to it.
    // A *SeedRows function only counts as THIS APP'S one-pass seeder if it
    // actually writes synced keys. StoneDesk has a local seedRows() inside its
    // sd_remnant module that RETURNS demo rows for load() to hand back and
    // never writes anything -- and sd_remnant is not even synced. Matching on
    // the name alone made this assert that a function with no write in it must
    // be called inside a suppression flag, which is not a defect and not a
    // requirement.
    let region = null;
    let seederName = null;
    const sre = /function (\w*[Ss]eedRows)\s*\(/g;
    let sm;
    while ((sm = sre.exec(app.src))) {
      const b = bodyOf(app.src, sm.index);
      if (!b) continue;
      const writesSynced = keys.some((k) => b.body.indexOf("st('" + k + "'") !== -1);
      if (!writesSynced) continue;
      seederName = [null, sm[1]];
      region = [b.start, b.end];
      break;
    }
    const flag = suppressionFlag(app);
    if (seederName && flag) {
      // The seeder must be CALLED inside the flag, not merely exist.
      const callGuard = new RegExp(flag + '\\s*=\\s*true[\\s\\S]{0,200}' + seederName[1] + '\\s*\\(');
      assert.ok(callGuard.test(app.src),
        app.file + ': ' + seederName[1] + '() is not called inside ' + flag);
    }
    const offenders = [];
    keys.forEach((key) => {
      const re = new RegExp("st\\(\\s*'" + key + "'\\s*,\\s*\\[\\s*\\{", 'g');
      let mm;
      while ((mm = re.exec(app.src))) {
        const inSeeder = region && mm.index >= region[0] && mm.index < region[1];
        // A lazy per-getter seed is legitimate only through a wrapper that
        // sets the flag -- SAIRNvet's svSeedStore. Anything else is a literal
        // seed on a live path.
        const before = app.src.slice(Math.max(0, mm.index - 200), mm.index);
        const wrapped = /SeedStore\s*\(/.test(before);
        if (!inSeeder && !wrapped) offenders.push(key + ' @' + mm.index);
      }
    });
    assert.deepStrictEqual(offenders, [],
      app.file + ': literal seed rows written to a SYNCED key on an unsuppressed path: '
      + offenders.join(', '));
  });
});

// ═══════════════════════════════════════════════════════════════════════════
section('3b. THE LAZY SHAPE: a getter that writes on first read must be wrapped');

// SECTION 3 WOULD NOT HAVE CAUGHT THE INCIDENT THIS FILE IS NAMED FOR, and
// that was found by running it against the real pre-fix sairnvet.html rather
// than assuming. It looks for a LITERAL at the st() call site; SAIRNvet's
// seeds are `var seed = [...]` followed by `saveX(seed)`, so the write site
// sees a variable and section 3 passes clean. 1 of 14 failed, and only the
// app-specific assertion in section 5.
//
// This is the shape that actually bites: a getter that returns early when the
// key is present, and otherwise WRITES a default before returning it. On a
// hooked app that write reaches the server. It is generic -- no app names, no
// key names -- so it covers the next app to grow one.
APPS.forEach((app) => {
  test(app.file + ' -- the lazy-seed scan is REPORTED, not gated', () => {
    const keys = syncedKeys(app);
    assert.ok(keys.length > 0, app.file + ': no *_SYNCED list found, so this check saw nothing');
    const candidates = [];
    const getRe = /function (\w+)\s*\(\s*\)\s*\{/g;
    let m;
    while ((m = getRe.exec(app.src))) {
      const b = bodyOf(app.src, m.index);
      if (!b) continue;
      const readsKey = keys.filter((k) => b.body.indexOf("'" + k + "'") !== -1)[0];
      if (!readsKey) continue;
      if (!/getItem\(/.test(b.body) || !/return\s/.test(b.body)) continue;
      const lits = [];
      const litRe = /(?:var|let|const)\s+(\w+)\s*=\s*[\[\{]/g;
      let lm;
      while ((lm = litRe.exec(b.body))) lits.push(lm[1]);
      if (!lits.length) continue;
      // indexOf, not a constructed RegExp. Building one here collapsed its
      // escapes on the way into this file TWICE -- once into an unterminated
      // group that threw, once into `[w$]+s*(s*` which is valid, matches
      // nothing, and reported a clean zero. The second is the dangerous one:
      // a regex that silently matches nothing is a checker that has gone blind
      // while still printing ok. The blindness assertion below exists because
      // of it, and string matching removes the escaping layer that caused it.
      const passesLiteral = lits.some((v) =>
        b.body.indexOf('(' + v + ')') !== -1 || b.body.indexOf(', ' + v + ')') !== -1);
      if (!passesLiteral) continue;
      const wrapped = /SeedStore\s*\(/.test(b.body) ||
        /(Suppress|Paused|Seeding)\w*\s*=\s*true/.test(b.body);
      candidates.push({ fn: m[1], key: readsKey, wrapped: wrapped });
    }
    const unwrapped = candidates.filter((c) => !c.wrapped);
    if (unwrapped.length) {
      console.log('         REPORT ONLY -- ' + app.file + ': ' + unwrapped.length
        + ' getter(s) match the lazy-seed shape and are not suppressed. READ THEM; '
        + 'this heuristic cannot tell a seed from a save or a pure reader: '
        + unwrapped.map((c) => c.fn + '->' + c.key).slice(0, 8).join(', '));
    }
    // THE ONLY ASSERTION HERE IS ABOUT THE SCAN, NOT THE APPS.
    if (app.file === 'sairnvet.html') {
      assert.ok(candidates.length >= 39,
        'the lazy-seed scan matched only ' + candidates.length + ' getter(s) on sairnvet.html, '
        + 'which is where 39 of this shape are known to exist -- the detector has gone '
        + 'blind rather than the app having been fixed twice');
      assert.strictEqual(unwrapped.length, 0,
        'sairnvet has ' + unwrapped.length + ' unwrapped lazy seed(s) again: '
        + unwrapped.map((c) => c.fn).join(', '));
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
section('4. the two apps that are safe BY ABSENCE stay that way');

test('stonedesk -- every synced cache still defaults to EMPTY', () => {
  // StoneDesk is safe today for a reason nothing enforces: its 21 synced
  // collections all initialise from an empty literal, so there is no seed to
  // push. Its suppression flag covers HYDRATION ONLY -- the same shape
  // SAIRNvet had. One seeded default on one of these keys and it becomes the
  // same live defect, with a flag that looks like it covers seeding.
  const app = APPS.filter((a) => a.file === 'stonedesk.html')[0];
  assert.ok(app, 'stonedesk.html is no longer detected as hooked');
  const keys = syncedKeys(app);
  assert.ok(keys.length >= 20, 'SD_SYNCED shrank to ' + keys.length + ' -- read why before trusting this');
  const seeded = [];
  keys.forEach((key) => {
    // The cache variable is whatever a declaration initialises from this key.
    const re = new RegExp("(?:var|let|const)\\s+\\w+\\s*=\\s*[^;\\n]*getItem\\(\\s*'" + key + "'[^;\\n]*", 'g');
    const decls = app.src.match(re) || [];
    decls.forEach((d) => {
      // The default is whatever follows the || . Empty literals are safe.
      const def = /\|\|\s*'([^']*)'/.exec(d);
      if (!def) return;
      // PARSED, not pattern-matched. sd_pricing_rules defaults to
      // {"vendorDiscounts":{},"categoryDiscounts":[],"productOverrides":{}} --
      // a SHAPE whose every leaf is empty, which a `{"` test called seeded
      // content. What matters is whether the default carries any actual value.
      let parsed;
      try { parsed = JSON.parse(def[1]); } catch (e) { return; }
      if (hasContent(parsed)) seeded.push(key + ' <- ' + def[1].slice(0, 60));
    });
  });
  assert.deepStrictEqual(seeded, [],
    'a synced StoneDesk cache now defaults to seeded content, and sdSyncSuppressed '
    + 'only covers hydration: ' + seeded.join('; '));
});

test('sairnfreedom -- still seeds nothing into a synced key', () => {
  const app = APPS.filter((a) => a.file === 'sairnfreedom.html')[0];
  assert.ok(app, 'sairnfreedom.html is no longer detected as hooked');
  // It writes through K_* constants, so a literal-key scan reports a clean it
  // never earned -- that vacuity was found during the review of this app and
  // is why the constants are resolved here instead.
  const consts = {};
  let m;
  const cre = /(K_\w+)\s*=\s*'(\w+)'/g;
  while ((m = cre.exec(app.src))) consts[m[1]] = m[2];
  assert.ok(Object.keys(consts).length > 20,
    'only ' + Object.keys(consts).length + ' key constants resolved -- the scan went blind');
  const offenders = [];
  const wre = /st\(\s*(K_\w+)\s*,\s*\[\s*\{/g;
  while ((m = wre.exec(app.src))) offenders.push(consts[m[1]] || m[1]);
  assert.deepStrictEqual(offenders, [],
    'sairnfreedom now seeds literal rows into: ' + offenders.join(', '));
});

// ═══════════════════════════════════════════════════════════════════════════
section('5. SAIRNvet specifically -- the app this came from');

test('svSeedStore still wraps every lazy seed', () => {
  const app = APPS.filter((a) => a.file === 'sairnvet.html')[0];
  assert.ok(app, 'sairnvet.html is no longer detected as hooked');
  assert.ok(/function svSeedStore\(/.test(app.src), 'svSeedStore was removed');
  const wrapped = (app.src.match(/svSeedStore\(/g) || []).length - 1;
  assert.ok(wrapped >= 39, 'only ' + wrapped + ' seed sites go through svSeedStore; expected 39+');
  // tests/sairnvet_seed_never_syncs.js drives these for real. This is the
  // platform-level tripwire, not a second copy of that.
});

// ═══════════════════════════════════════════════════════════════════════════
console.log('\n' + pass + '/' + (pass + fail) + ' passed  (' + APPS.length + ' hooked apps in scope)');
process.exit(fail ? 1 : 0);
