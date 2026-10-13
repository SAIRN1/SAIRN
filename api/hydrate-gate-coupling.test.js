// api/hydrate-gate-coupling.test.js
// REQUIREMENT: no app may have BOTH a session-gated resource AND a hydrate
//   that only ever runs at page-parse time with its refusals swallowed.
//
// ── THE DEFECT THIS GENERALISES (SAIRNfreedom, 2026-10-11) ─────────────────
// sfHydrateAll() had exactly ONE call site, the DOMContentLoaded handler, which
// runs BEFORE any interactive sign-in. Each resource's read carried
// `.catch(function(){})`. So on a browser with nothing in sessionStorage:
//
//     boot -> sign-in pane shown -> hydrate runs with NO session
//          -> every SD_SESSION_GATED resource answers 403
//          -> the per-resource empty catch swallows it
//          -> user signs in -> NOTHING fetches again, for the life of the page
//
// Eighteen resources were in that state, and additive hydration makes "the
// server had nothing" and "the server refused" identical on screen. The console
// warning written for exactly this case sits on the OUTER promise, which never
// rejected, because the inner catch ate the refusal.
//
// ── WHY A COUPLING TEST AND NOT NINE FIXES ────────────────────────────────
// Swept all nine apps with a hydrate on 2026-10-13. Only SAIRNfreedom had all
// three conditions, and it is fixed. SAIRNvet has TWO of the three -- one
// parse-time call site, empty catch -- and is safe ONLY because it has no gated
// resource at all. That is not a property of SAIRNvet's client; it is a
// property of a table in api/sd-data.js that another session edits for
// unrelated reasons.
//
// So the thing worth holding is the COUPLING: the day somebody gates an `sv_`
// resource, this suite fails and names the app, instead of SAIRNvet's backup
// silently going read-dead for every pre-login page load. That is the b5
// convention candidate applied to itself -- a change that moves one fact must
// fail against the check that depends on it, in the same push.
//
// ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
// It does not render a page or drive a login. It reads source. A source
// assertion cannot prove the hydrate WORKS; it can prove the three conditions
// that make it fail silently are not all present at once, which is the
// regression being guarded.
//
// Run: node api/hydrate-gate-coupling.test.js

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const REPO = path.join(__dirname, '..');

// ── COMMENTS ARE BLANKED BEFORE ANY MATCH, AND THE FIRST DRAFT OF THIS SWEEP
//    PAID FOR NOT DOING IT ──────────────────────────────────────────────────
// Every one of these files carries PARAGRAPHS about its own hydrate, several of
// which name the function. Counting those as call sites reported two and three
// sites for apps that have one, and would have cleared the exact app that has a
// real problem. Blanked, offsets preserved, so reported line numbers stay true.
// THE LINE-BASED FORM IS THE REPO IDIOM AND THE FIRST DRAFT'S REGEX FORM WAS
// WRONG ON stonedesk.html. A global `/\*[\s\S]*?\*\//` consumes from any `/*`
// to the next `*/` ANYWHERE in the file -- and a 2MB app file contains `/*`
// inside strings, CSS and regexes. It blanked a region thousands of lines wide
// and the suite then reported StoneDesk's hydrate as NEVER CALLED and its
// gated-resource count as ZERO, both false. Measured: the real call is at
// stonedesk.html:38779 in the `window.fn()` form.
//
// api/sd-data-sf-session-gate.test.js:83 already uses this line form for the
// same reason. ITS ERROR DIRECTION IS STATED rather than left to be
// discovered: a trailing `// ...` on a line of code is NOT blanked, so a
// comment that mentions a hydrate on the same line as real code would count as
// a call site. That is the LENIENT direction for the dormancy arm below, and it
// is accepted because the alternative -- a stripper that can silently eat a
// thousand lines -- is the failure this comment exists to record.
function stripComments(s) {
  return s.split('\n')
    .map((l) => (/^\s*(\/\/|\*|\/\*)/.test(l) ? '' : l))
    .join('\n');
}

// ── AND THE CALL FORM `window.fn()` MUST COUNT, WHICH IS THE SECOND BUG THE
//    FIRST DRAFT HAD ────────────────────────────────────────────────────────
// A lookbehind excluding `[\w.]` to avoid matching `svHydrateAll` inside
// `window.svHydrateAll = ...` also excludes the real call `window.sdHydrateAll()`.
// StoneDesk calls its hydrate ONLY in that form, so the draft reported ZERO
// call sites for an app that calls it correctly from a post-login block, and
// would have accused it. Assignment is excluded by requiring that the `(` is
// not preceded by `=`, rather than by excluding the `window.` prefix.
function callSites(src, fn) {
  const out = [];
  const re = new RegExp('(?:window\\.)?' + fn + '\\s*\\(', 'g');
  let m;
  while ((m = re.exec(src)) !== null) {
    const before = src.slice(Math.max(0, m.index - 24), m.index);
    if (/[=:]\s*(?:window\.)?$/.test(before)) continue;   // an assignment
    if (/function\s+$/.test(before)) continue;            // the definition
    out.push({ line: src.slice(0, m.index).split('\n').length, text: m[0] });
  }
  return out;
}

function gatedResources() {
  const src = fs.readFileSync(path.join(REPO, 'api', 'sd-data.js'), 'utf8');
  const m = src.match(/const SD_SESSION_GATED = \{([\s\S]*?)\n    \};/);
  assert.ok(m, 'SD_SESSION_GATED could not be parsed out of api/sd-data.js, so '
    + 'this suite compared NOTHING -- a third state, not a pass');
  const names = (m[1].match(/'([a-z0-9_]+)'\s*:\s*\[/g) || [])
    .map((s) => s.match(/'([a-z0-9_]+)'/)[1]);
  assert.ok(names.length > 20,
    'only ' + names.length + ' gated resources parsed; the table holds far '
    + 'more, so the regex has drifted and every arm below would pass '
    + 'vacuously');
  return new Set(names);
}

// ── THE APP'S RESOURCE LIST COMES FROM ITS REGISTRY, NOT FROM ITS HTML ─────
// The first draft read `X_SYNCED = [...]` out of each page. Only SAIRNfreedom
// spells it that way, so every other app reported ZERO gated resources --
// including StoneDesk, which has five (slabs, profile, memory, locations,
// customers). The load-bearing arm was therefore only really checking one app
// while printing a clean line for nine.
//
// api/_resources/<app>.js is the authoritative registry: its own header says
// sd-data.js merges those files at load and GENERATES its resource list from
// the merge, so the two cannot drift. That is the source to intersect against.
//
// FAILS CLOSED on an app whose registry cannot be found: returns null, and the
// caller reports it rather than treating the app as having no gated resources,
// which is the direction that would hide the defect.
function appResources(htmlFile) {
  const app = path.basename(htmlFile, '.html');
  const p = path.join(REPO, 'api', '_resources', app + '.js');
  if (!fs.existsSync(p)) return null;
  const src = stripComments(fs.readFileSync(p, 'utf8'));
  const names = (src.match(/'([a-z0-9_]+)'/g) || []).map((s) => s.slice(1, -1));
  return names.length ? names : null;
}

// ── AND THE SD_SESSION_GATED TABLE IS NOT THE ONLY GATE, WHICH IS THE BUG
//    THIS SUITE SHIPPED WITH FOR ONE HOUR ──────────────────────────────────
// The first pass intersected each app's registry against SD_SESSION_GATED
// alone, reported SAIRNvet as `gated=0`, and PASSED it -- while
// api/sd-data.js:13552 reads
//
//     if (SV_RESOURCES[resource]) { ...401 NO_SESSION if absent... }
//
// which gates EVERY SAIRNvet resource, inline, outside the table. SAIRNvet was
// the live instance of the exact defect this suite was written to find, and the
// suite cleared it. Same class as the SAIRNscape progress-photo finding, where
// a gate sitting inside a narrower branch read as no gate to a table scan.
//
// So an app-wide inline gate counts too. Detected by its shape -- a
// `<PREFIX>_RESOURCES[resource]` membership test whose body refuses without a
// session for THIS app -- and the apps it covers are returned as a set of app
// ids rather than resource names, because the gate is on the whole registry.
function appsWithInlineGate() {
  const src = stripComments(fs.readFileSync(path.join(REPO, 'api', 'sd-data.js'), 'utf8'));
  const out = new Set();
  const re = /if\s*\(\s*(\w+)_RESOURCES\[resource\]\s*\)\s*\{([\s\S]{0,700}?)\n    \}/g;
  let m;
  while ((m = re.exec(src)) !== null) {
    const body = m[2];
    // `[^)]*?` CANNOT CROSS THE `)` OF `tokenFromRequest(req)`, and the
    // first draft used it: every block matched, every app came back
    // undefined, and the set was empty while reading as computed.
    const app = (body.match(/verifySessionToken\([\s\S]{0,120}?,\s*'([a-z0-9_]+)'\s*\)/) || [])[1];
    if (app && /NO_SESSION|res\.status\(401\)/.test(body)) out.add(app);
  }
  return out;
}

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log('  PASS  ' + name); passed++; }
  catch (e) { console.log('  FAIL  ' + name + '\n        ' + e.message); failed++; }
}

function main() {
  console.log('hydrate / session-gate coupling -- the b4 silent-failure class\n');

  const gated = gatedResources();
  const inlineApps = appsWithInlineGate();
  const apps = fs.readdirSync(REPO).filter((f) => /\.html$/.test(f)).sort();
  assert.ok(apps.length >= 10, 'only ' + apps.length + ' app files found');

  const rows = [];
  apps.forEach((f) => {
    const raw = fs.readFileSync(path.join(REPO, f), 'utf8');
    const src = stripComments(raw);
    const def = src.match(/function\s+(\w*[Hh]ydrateAll)\s*\(/);
    if (!def) return;
    const fn = def[1];
    const sites = callSites(src, fn);
    const body = src.slice(def.index, def.index + 6000);
    const emptyCatch = /\.catch\(\s*function\s*\(\s*\)\s*\{\s*\}\s*\)/.test(body)
      || /\.catch\(\(\)\s*=>\s*\{\s*\}\)/.test(body);
    // A call at column 0 runs when the script is parsed -- i.e. before any
    // interactive sign-in, whatever the page shows.
    const lines = src.split('\n');
    const parseTime = sites.filter((s) =>
      new RegExp('^(?:window\\.)?' + fn + '\\s*\\(').test(lines[s.line - 1] || ''));
    const reg = appResources(f);
    const appId = path.basename(f, '.html');
    // An app-wide inline gate means EVERY one of its resources is gated.
    const mine = inlineApps.has(appId) ? (reg || ['<all, inline gate>'])
               : (reg ? reg.filter((r) => gated.has(r)) : null);
    rows.push({ f: f, fn: fn, sites: sites, emptyCatch: emptyCatch,
                parseTime: parseTime, gated: mine, noRegistry: reg === null });
  });

  test('the sweep found the apps that HAVE a hydrate -- a zero here would make '
    + 'every arm below vacuous', () => {
    assert.ok(rows.length >= 8,
      'only ' + rows.length + ' app(s) with a *HydrateAll were found. The '
      + 'platform has at least eight; the detector has drifted.');
  });

  test('every hydrate has at least ONE real call site -- a hydrate nobody '
    + 'calls is dormant code wearing a feature\'s name (Guardian 0d)', () => {
    const dead = rows.filter((r) => r.sites.length === 0)
      .map((r) => r.f + ':' + r.fn);
    assert.deepStrictEqual(dead, [],
      'these hydrates are never called: ' + dead.join(', ')
      + '. NOTE for whoever hits this: the `window.fn()` call form counts, and '
      + 'a detector that excludes it accuses StoneDesk, which calls its '
      + 'hydrate only that way.');
  });

  test('THE LOAD-BEARING ONE: no app has a gated resource AND a parse-time-only '
    + 'hydrate AND a swallowing catch', () => {
    const bad = rows.filter((r) =>
      r.gated.length > 0 && r.emptyCatch
      && r.parseTime.length > 0 && r.sites.length === r.parseTime.length);
    const detail = bad.map((r) => r.f + ' (' + r.fn + ', parse-time at line '
      + r.parseTime.map((s) => s.line).join('/') + ', ' + r.gated.length
      + ' gated: ' + r.gated.slice(0, 6).join(', ') + ')');
    assert.deepStrictEqual(detail, [],
      'SILENT-FAILURE CLASS PRESENT: ' + detail.join(' | ')
      + '\n        The hydrate runs once at parse time, before any interactive '
      + 'sign-in; each gated resource answers 403; the empty per-resource catch '
      + 'swallows it; and nothing fetches again for the life of the page. '
      + 'Additive hydration then makes "the server had nothing" and "the server '
      + 'refused" identical on screen. THE FIX IS A SECOND CALL SITE on the '
      + 'interactive sign-in path, as sairnfreedom.html\'s '
      + 'sfHydrateAfterSignIn() does -- not removing the catch.');
  });

  // ── THE VACUITY ARM WAS RE-POINTED WITHIN THE HOUR, AND BY ITSELF ────────
  // It first read "at least one app DOES have both a swallowing catch and a
  // parse-time call, so the gated-resource term is the only thing holding it
  // clean", and named SAIRNvet. Then SAIRNvet was FIXED -- in this same batch,
  // because the inline-gate detector above found it was not merely two-of-three
  // but the live defect -- and the arm went red saying exactly what it was
  // written to say: "that is good news and it makes the arm above
  // unfalsifiable, so re-point it or retire it rather than leaving a green bar
  // over no data."
  //
  // AN ARM ANCHORED ON A REAL APP BEING BROKEN RETIRES ITSELF THE DAY THE APP
  // IS FIXED. So the detector is now driven against SYNTHETIC FIXTURES, both
  // directions, which is what the platform's own convention asks for and what
  // keeps this falsifiable no matter how healthy the apps get.
  test('NEGATIVE AND POSITIVE CONTROL on fixtures, not on a real app being '
    + 'broken: the detector flags the three-condition shape and clears each '
    + 'single-condition change to it', () => {
    const BAD = [
      'function zzHydrateAll(){',
      '  return Promise.all(LIST.map(function(k){',
      '    return zzData(\'read\',k,null).then(function(r){ merge(r); })',
      '      .catch(function(){});',
      '  }));',
      '}',
      'zzHydrateAll().then(function(n){ if(n) render(); });',
      ''].join('\n');
    const probe = (src) => {
      const s = stripComments(src);
      const def = s.match(/function\s+(\w*[Hh]ydrateAll)\s*\(/);
      if (!def) return null;
      const fn = def[1];
      const sites = callSites(s, fn);
      const body = s.slice(def.index, def.index + 6000);
      const emptyCatch = /\.catch\(\s*function\s*\(\s*\)\s*\{\s*\}\s*\)/.test(body)
        || /\.catch\(\(\)\s*=>\s*\{\s*\}\)/.test(body);
      const lines = s.split('\n');
      const parseTime = sites.filter((x) =>
        new RegExp('^(?:window\\.)?' + fn + '\\s*\\(').test(lines[x.line - 1] || ''));
      return { emptyCatch: emptyCatch, parseTimeOnly: parseTime.length > 0
                 && sites.length === parseTime.length, sites: sites.length };
    };
    const bad = probe(BAD);
    assert.ok(bad && bad.emptyCatch && bad.parseTimeOnly,
      'the PLANTED three-condition shape was not detected: '
      + JSON.stringify(bad) + '. Every clean verdict this suite prints rests '
      + 'on this detector working, so a miss here voids all of them.');
    // (1) a second, post-sign-in call site clears it -- the real fix shape.
    const fixedBySecondCall = probe(BAD + 'function enterApp(){ zzHydrateAll(); }\n');
    assert.strictEqual(fixedBySecondCall.parseTimeOnly, false,
      'adding a NON-parse-time call site did not clear parseTimeOnly, so the '
      + 'detector cannot tell the fixed shape from the broken one and would '
      + 'keep accusing an app that has been repaired');
    // (2) a reporting catch clears it the other way.
    const fixedByCatch = probe(BAD.replace('.catch(function(){});',
      '.catch(function(e){ console.warn(e); });'));
    assert.strictEqual(fixedByCatch.emptyCatch, false,
      'a catch that REPORTS was still read as swallowing, so the detector '
      + 'would accuse an app whose refusals are visible');
    // (3) and the two must be independent -- neither change may clear BOTH,
    // or the arm would pass on any edit at all.
    assert.strictEqual(fixedBySecondCall.emptyCatch, true,
      'adding a call site also cleared emptyCatch, so the two conditions are '
      + 'not being measured independently');
    assert.strictEqual(fixedByCatch.parseTimeOnly, true,
      'changing the catch also cleared parseTimeOnly, same problem');
  });

  const twoOfThree = rows.filter((r) =>
    r.emptyCatch && r.parseTime.length > 0 && r.sites.length === r.parseTime.length);
  if (twoOfThree.length) {
    console.log('\nTWO-OF-THREE, safe ONLY because nothing is gated -- the day '
      + 'one of these apps gains a gate, the arm above fails:');
    twoOfThree.forEach((r) => {
      console.log('  ! ' + r.f + ' (' + r.fn + ', '
        + (r.gated ? r.gated.length : '?') + ' gated resources)');
    });
  }

  console.log('\nPER-APP, PRINTED SO THIS IS A LIST AND NOT A COUNT:');
  rows.forEach((r) => {
    console.log('  %s  %s  sites=%s  parseTimeOnly=%s  emptyCatch=%s  gated=%d',
      r.f.padEnd(22), r.fn.padEnd(16),
      r.sites.map((s) => s.line).join(',') || '-',
      (r.parseTime.length > 0 && r.sites.length === r.parseTime.length) ? 'YES' : 'no',
      r.emptyCatch, r.gated.length);
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  if (failed) process.exit(1);
}

main();
