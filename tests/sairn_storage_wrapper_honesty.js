// tests/sairn_storage_wrapper_honesty.js
//
// Run:  node tests/sairn_storage_wrapper_honesty.js
//
// Every SAIRN app keeps its working data in localStorage behind a one-line
// wrapper. The 2026-08-18 platform audit made that wrapper REPORT its failure
// instead of swallowing it -- a quota-exceeded or private-browsing write is
// otherwise lost with nothing shown, nothing logged and nothing returned. That
// audit reached StoneDesk, SAIRNbuild, SAIRNvet and SAIRNdental.
//
// IT DID NOT REACH EVERYWHERE, AND NOTHING NOTICED FOR SIXTEEN DAYS. The
// 2026-09-04 sweep found SAIRNgrounds and SAIRNscape still carrying the bare
// `catch(e){}`, and SAIRNmechanical with no wrapper at all -- three of its
// writes had no try/catch whatever and were followed immediately by a success
// toast, so a full store threw, the toast never ran, and the user was told
// nothing after clicking Save.
//
// This file exists so the next miss is loud. Part 1 drives the three fixed
// wrappers against a store that refuses. Part 2 is a static parity check with
// the still-unfixed apps listed BY NAME -- the list is meant to be burned
// down, and a name left on it after the app is fixed fails here.

'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function read(f) { return fs.readFileSync(path.join(ROOT, f), 'utf8'); }
function balanced(src, start) {
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
function fnFrom(src, decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('not found: ' + decl);
  return balanced(src, i);
}

// A store that refuses every write with the shape a browser actually throws.
function refusingStore() {
  const data = {};
  return {
    data,
    store: {
      getItem: (k) => (k in data ? data[k] : null),
      setItem: () => { const e = new Error('quota'); e.name = 'QuotaExceededError'; e.code = 22; throw e; }
    }
  };
}
function workingStore() {
  const data = {};
  return { data, store: { getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = v; } } };
}

// ── PART 1: the three wrappers fixed on 2026-09-04 ─────────────────────────

// SAIRNgrounds -- st()
{
  const src = read('sairngrounds.html');
  const make = (store, toasts) => new Function('localStorage', 'toast',
    fnFrom(src, 'function st(k,v){') + '\nreturn st;')(store, (m, d) => toasts.push(String(m)));

  const good = workingStore(), gt = [];
  check('grounds: a write that works returns true', make(good.store, gt)('grd_jobs', [1]), true);
  check('grounds: and says nothing', gt.length, 0);
  check('grounds: and actually stores', good.data.grd_jobs, '[1]');

  const bad = refusingStore(), bt = [];
  check('grounds: a refused write returns FALSE, not undefined', make(bad.store, bt)('grd_jobs', [1]), false);
  check('grounds: and tells the user', bt.length, 1);
  check('grounds: naming what did not happen', /NOT saved/.test(bt[0]), true);
  check('grounds: and that the screen is showing the old data',
    /previous data/.test(bt[0]), true);
}

// SAIRNscape -- scpSt()
{
  const src = read('sairnscape.html');
  const make = (store, toasts) => new Function('localStorage', 'scpToast',
    fnFrom(src, 'function scpSt(k,v){') + '\nreturn scpSt;')(store, (m, d) => toasts.push(String(m)));

  const good = workingStore(), gt = [];
  check('scape: a write that works returns true', make(good.store, gt)('scp_jobs', [1]), true);
  check('scape: and says nothing', gt.length, 0);

  const bad = refusingStore(), bt = [];
  check('scape: a refused write returns FALSE', make(bad.store, bt)('scp_jobs', [1]), false);
  check('scape: and tells the user', bt.length, 1);
  check('scape: naming what did not happen', /NOT saved/.test(bt[0]), true);
}

// SAIRNmechanical -- mechSt(), plus the three callers that claimed an outcome
{
  const src = read('sairnmechanical.html');
  function mech(store, toasts, fields) {
    const els = {};
    Object.keys(fields || {}).forEach((id) => { els[id] = { value: fields[id], textContent: '' }; });
    // `window` IS REQUIRED, and its absence was a hard crash rather than a
    // failure. Added 2026-09-10 along with the two helpers below, after
    // `2a61b739` taught saveCheck() to mint an id: three separate sessions
    // independently reported this file as broken the same night and each
    // deferred it as somebody else's lane, so it sat red while being a
    // PLATFORM-WIDE wrapper test -- it dies inside this block, before it ever
    // reaches stonedesk.html or sairnvet.html, so every app after
    // sairnmechanical was covered by nothing at all.
    //
    // `typeof window.mechPushRecord` does NOT guard an undeclared `window`:
    // typeof is only safe on a bare identifier, so the property access threw
    // ReferenceError. Supplied as an empty object, which is the honest
    // fixture -- saveCheck() treats a missing mechPushRecord as "no backup
    // wired" and carries on, which is exactly the state these arms are about.
    return new Function('localStorage', 'showToast', 'document', 'APP_ID', 'crNum', 'window',
      fnFrom(src, 'function mechSt(key, value) {') + '\n' +
      // saveCheck() has called these since 2a61b739. Extracted from the real
      // file, never stubbed: a stub mechCheckId() would let the collision fix
      // it exists for rot while these arms stayed green, which is the
      // fixture-supplies-the-thing-it-tests shape this repo has already been
      // bitten by once.
      fnFrom(src, 'function mechCheckId(){') + '\n' +
      fnFrom(src, 'function mechEnsureCheckIds(checks){') + '\n' +
      fnFrom(src, 'function saveCheck(){') + '\n' +
      fnFrom(src, 'function savePricing(){') + '\n' +
      fnFrom(src, 'function getPricing(){') + '\n' +
      fnFrom(src, 'function defaultPricing(){') + '\n' +
      'function renderCR(){}\n' +
      'return { mechSt: mechSt, saveCheck: saveCheck, savePricing: savePricing,' +
      '         mechCheckId: mechCheckId,' +
      '         crNum: function(){ return crNum; } };'
    )(store, (m, d) => toasts.push(String(m)), { getElementById: (id) => els[id] || null },
      'mech', 1001, {});
  }

  const good = workingStore(), gt = [];
  check('mech: a write that works returns true', mech(good.store, gt).mechSt('mech_x', { a: 1 }), true);
  const bad = refusingStore(), bt = [];
  check('mech: a refused write returns FALSE', mech(bad.store, bt).mechSt('mech_x', { a: 1 }), false);
  check('mech: and tells the user', bt.length, 1);

  // The check-number defect. crNum is incremented while `entry` is built, so a
  // failed write that left it advanced would make the NEXT check reuse the
  // number -- two different payments, one check number, in a register.
  {
    const s = refusingStore(), t = [];
    const w = mech(s.store, t, { 'cr-date': '2026-09-04', 'cr-payee': 'Acme', 'cr-amount': '250', 'cr-memo': '' });
    w.saveCheck();
    check('mech: a failed check write puts the check number BACK', w.crNum(), 1001);
    check('mech: and does not claim the check was saved',
      t.filter((m) => /^Check #\d+ saved$/.test(m)).length, 0);
  }
  {
    const s = workingStore(), t = [];
    const w = mech(s.store, t, { 'cr-date': '2026-09-04', 'cr-payee': 'Acme', 'cr-amount': '250', 'cr-memo': '' });
    w.saveCheck();
    check('mech: a successful check still confirms', t, ['Check #1001 saved']);
    check('mech: and the number advanced', w.crNum(), 1002);
    check('mech: and both keys were written',
      [typeof s.data.mech_checks, s.data.mech_crnum], ['string', '1002']);
  }
  // savePricing() claimed "Field Quote will use your rates". getPricing()
  // reads this key back, so on a failed write Field Quote keeps the old rates.
  {
    const s = refusingStore(), t = [];
    const w = mech(s.store, t, { 'r-std': '95', 'r-lead': '130', 'r-markup': '35', 'r-profit': '25' });
    w.savePricing();
    check('mech: a failed pricing write does not claim Field Quote will use the rates',
      t.filter((m) => /Field Quote will use your rates/.test(m)).length, 0);
    check('mech: it says the write failed instead', /NOT saved/.test(t[0] || ''), true);
  }
}

// ── PART 2: parity, and an honest list of what is still wrong ──────────────
//
// A one-line `function st(k,v){try{...setItem...}catch(e){}}` is the exact
// shape the platform audit removed. This finds it across every app page.
//
// SCOPE OF THIS SCAN, said rather than discovered: it matches ONE-LINE
// wrappers only. An app whose wrapper spans several lines, or is named
// something else, is NOT checked here and its absence from the output means
// nothing. That is why the expected list below is written out by name instead
// of asserting a count.
{
  const swallowing = [];
  fs.readdirSync(ROOT).filter((f) => f.endsWith('.html')).sort().forEach((f) => {
    const src = read(f);
    const m = src.match(/function\s+(\w*[Ss]t)\s*\(\s*\w+\s*,\s*\w+\s*\)\s*\{try\{localStorage\.setItem\([^}]*\}catch\(e\)\{\}\}/);
    if (m) swallowing.push(f);
  });

  // Known and NOT fixed by the 2026-09-04 sweep, which was dispatched for
  // SAIRNbuild, SAIRNvet, SAIRNmechanical, SAIRNgrounds and SAIRNscape only.
  // These are the same defect in apps that were out of scope; they are
  // reported, not fixed, and this list is meant to shrink.
  //
  // SHRANK 2026-09-04 (CC): sairnbiz.html removed. Its st() now returns a
  // boolean and says "THIS DID NOT SAVE" on a refused write, latched per key.
  // Fixed as part of the SAIRNbiz server-backup work rather than by this
  // sweep -- st() was the hook that change needed, and a hook that pushes to a
  // server on the strength of a write it never confirmed is the same defect
  // wearing a worse disguise. Held by tests/sairnbiz_server_backup.js, which
  // carries its own mutation probe restoring the empty catch.
  // EMPTIED 2026-09-04 (Hank): sairndesign.html, sairnlaw.html and
  // sairnlegacy.html were the last three, and all three now return whether the
  // write happened and ALWAYS log when it did not -- the same shape as
  // SAIRNdental's st() (75b9c07), which is where the defect was first found the
  // hard way. Held by tests/st_reports_failure.js, which drives the real
  // functions against a fake localStorage that can be told to be full, and
  // carries seven negative controls including one that restores the empty
  // catch.
  //
  // THE LIST STAYING EMPTY IS NOW THE ASSERTION. It shrank from a
  // report-what-is-broken list to a regression guard, and that is a different
  // job: a NEW app copying the swallowing one-liner fails here on the day it
  // lands rather than being added to a list and waiting for a sweep.
  const KNOWN_UNFIXED = [];

  check('NO app swallows a failed localStorage write any more',
    swallowing, KNOWN_UNFIXED);
  check('SAIRNgrounds is no longer among them', swallowing.indexOf('sairngrounds.html'), -1);
  check('SAIRNscape is no longer among them', swallowing.indexOf('sairnscape.html'), -1);
  check('SAIRNdesign is no longer among them', swallowing.indexOf('sairndesign.html'), -1);
  check('SAIRNlaw is no longer among them', swallowing.indexOf('sairnlaw.html'), -1);
  check('SAIRNlegacy is no longer among them', swallowing.indexOf('sairnlegacy.html'), -1);
}

// ── PART 3: the shape PART 2 CANNOT SEE -- added 2026-09-04 ────────────────
//
// Part 2 matches `catch(e){}` and its own header says an app whose wrapper is
// spelled differently is not checked and its absence means nothing. That limit
// was disclosed, and it was also hiding real defects:
//
//     function st(k,v){try{localStorage.setItem(k,JSON.stringify(v));
//                          return true;}catch(e){return false;}}
//
// returns a boolean, so it is NOT a swallowing catch and never appeared on the
// Part 2 list. But MEASURED per file: every one of SAIRNcare's 28 and
// SAIRNfreedom's 78 st() call sites ignored that boolean, and the catch logged
// nothing. A refused write produced a `false` that no code read and no console
// recorded -- indistinguishable, from the outside, from the empty catch Part 2
// exists to find. A boolean nobody reads is not a report.
//
// So this scans for a write wrapper whose catch NEITHER logs NOR tells the
// user, whatever it returns.
//
// SCOPE, again said rather than discovered: it brace-matches the function body
// from `function NAME(a, b) {`, so it sees multi-line wrappers Part 2 misses --
// but only two-argument functions containing `localStorage.setItem`. A wrapper
// taking one argument or three is invisible here. A wrapper that TOASTS is
// deliberately NOT listed: SAIRNgrounds, SAIRNmechanical and SAIRNscape tell
// the user directly, which is the louder half, not the missing one.
//
// A COMMENT USED TO COUNT AS SPEAKING. Found 2026-09-10 (Cody) while fixing the
// crash below, by mutation rather than by reading: silencing every real
// `console.error` in `sairnvet.html`'s `st()` left this block GREEN, because two
// lines of its body are PROSE mentioning "the next success toast" and
// "showToast() above", and the `speaks` regex was run over raw source. So the
// one assertion that matters here -- `mute` is empty, therefore NO app has a
// silent write wrapper -- was satisfiable by a code comment, in a repo whose
// comments are deliberately long and frequently quote the very calls they
// describe. An assertion a comment can satisfy is close to unfalsifiable.
//
// MEASURED BEFORE AND AFTER, because the honest question is whether this was
// masking anything today: across all 17 app files, ZERO wrappers speak only via
// a comment. Every one has a real console or toast call in code, so stripping
// changes no verdict right now and `mute` stays empty either way. The defect was
// LATENT -- it would have masked the next regression, which is the single thing
// this block exists to catch ("the next one added fails here by name"). Fixed
// because a tripwire that cannot trip is worse than no tripwire, not because it
// was lying today.
//
// The stripper is a state machine, not a regex, for the reason
// tools/jscomments.py records at length: three of seven regex strippers in
// tools/ were destroying 90% of their input and reporting CLEAN on what
// survived. It is held by arms below, including the control that a `//` inside a
// string literal (a URL) is NOT treated as a comment.
const BACKSLASH = String.fromCharCode(92);
function stripJsComments(src) {
  let out = '', i = 0, quote = null;
  const n = src.length;
  while (i < n) {
    const c = src[i], d = src[i + 1];
    if (quote) {
      if (c === BACKSLASH) { out += c + (d || ''); i += 2; continue; }
      if (c === quote) quote = null;
      out += c; i++; continue;
    }
    if (c === '"' || c === "'" || c === '`') { quote = c; out += c; i++; continue; }
    if (c === '/' && d === '/') { while (i < n && src[i] !== '\n') i++; continue; }
    if (c === '/' && d === '*') {
      i += 2;
      while (i < n && !(src[i] === '*' && src[i + 1] === '/')) i++;
      i += 2; continue;
    }
    out += c; i++;
  }
  return out;
}
{
  const mute = [];
  fs.readdirSync(ROOT).filter((f) => f.endsWith('.html')).sort().forEach((f) => {
    const src = read(f);
    const re = /function\s+(\w+)\s*\(\s*\w+\s*,\s*\w+\s*\)\s*\{/g;
    let m;
    while ((m = re.exec(src)) !== null) {
      const open = src.indexOf('{', m.index);
      let depth = 0, j = open;
      for (; j < src.length && j - open < 4000; j++) {
        if (src[j] === '{') depth++;
        else if (src[j] === '}' && --depth === 0) break;
      }
      const body = src.slice(m.index, j + 1);
      if (body.indexOf('localStorage.setItem') === -1) continue;
      // Comments stripped before ANY speaking test, here and on the delegation
      // hop below. The brace-matching above still runs on raw source on purpose:
      // a `{` or `}` inside a comment is vanishingly rare in this codebase and
      // stripping first would shift every index out from under the match.
      const code = stripJsComments(body);
      let speaks = /console\.|toast|Toast|alert\(/.test(code);
      // DELEGATION COUNTS (2026-09-04). The first version looked for a literal
      // console/toast call inside the wrapper, so a catch that calls a NAMED
      // helper which logs read as silent. StoneDesk has two wrappers, st() and
      // stRaw(), sharing one sdStorageFailed() -- and the alternative to
      // teaching this check was duplicating the message in both, which is the
      // drift this whole file exists to catch. So: any function this wrapper
      // calls, whose own body speaks, counts as speaking. One hop only, and
      // the callee must be defined in the same file -- a deeper chain would
      // let anything be argued into "speaking".
      if (!speaks) {
        // Call names read from the STRIPPED body, so a function name merely
        // MENTIONED in prose -- "see showToast() above", which sairnvet's st()
        // really does say -- is not treated as a call this wrapper makes.
        const called = code.match(/(?<![\w.$])([A-Za-z_$][\w$]*)\s*\(/g) || [];
        speaks = called.some((c) => {
          const nm = c.replace(/\s*\($/, '');
          const dm = new RegExp('function\\s+' + nm + '\\s*\\(').exec(src);
          if (!dm) return false;
          const o = src.indexOf('{', dm.index);
          let d = 0, k = o;
          for (; k < src.length && k - o < 4000; k++) {
            if (src[k] === '{') d++;
            else if (src[k] === '}' && --d === 0) break;
          }
          return /console\.|toast|Toast|alert\(/
            .test(stripJsComments(src.slice(dm.index, k + 1)));
        });
      }
      if (!speaks) mute.push(f + ':' + m[1]);
    }
  });

  // Reported, NOT fixed. Written out by name for the same reason Part 2's list
  // was: a count cannot tell you which one moved. This list is meant to shrink,
  // and adding to it is the wrong direction.
  //
  // stonedesk.html and sairnvet.html were claimed by other sessions at the time
  // this was written, so they were measured and listed rather than touched.
  // sairnbuild.html's st() is a different animal -- it carries a server-backup
  // hook and its own okWrite flag -- and needs reading before it is changed.
  // SHRANK 2026-09-04 (Hank): sairnvet.html:st removed. Its outer catch now
  // logs, with the quota named and a non-quota failure NOT blamed on it. That
  // one was never a copy-paste of the others -- the same function carries this
  // file's unreadable-store refusal, so the fix had to be read into an
  // existing guard rather than pasted over it. Held by
  // tests/sv_storage_guard.js, which drives the real st() and svLoad() against
  // a fake localStorage and a fake DOM, and carries a control per shape.
  // BURNED DOWN TO ZERO 2026-09-04 (Cody). The last four are fixed:
  // sairnbuild:st (86 call sites, 44 ignoring the return), sairnsenior:st
  // (32 sites, ALL 32 ignoring it), stonedesk:st (101 sites, 24 ignoring)
  // and stonedesk:stRaw (22 sites, 19 ignoring) -- each measured in its own
  // file rather than assumed from the siblings, because they are not the same
  // animal: sairnbuild's carries the server-backup hook and its own okWrite
  // flag, and StoneDesk's two share one helper.
  //
  // AN EMPTY LIST IS THE POINT AND ALSO THE RISK. It now asserts that NO app
  // has a silent write wrapper, so the next one added fails here by name. It
  // is not evidence that no silent write exists anywhere -- see this block's
  // scope note above: one- and three-argument wrappers are still invisible.
  const KNOWN_MUTE = [];

  check('no app writes to localStorage with a catch that says nothing',
    mute, KNOWN_MUTE);
  // The delegation hop must not become a way to argue anything into
  // "speaking". A wrapper calling a helper that is itself silent is still
  // silent, and a call to a function that does not exist in the file proves
  // nothing -- both asserted against synthetic sources rather than trusted.
  {
    const probe = (body, extra) => {
      const src2 = 'function stX(a, b) {' + body + '}\n' + (extra || '');
      const re = /function\s+(\w+)\s*\(\s*\w+\s*,\s*\w+\s*\)\s*\{/g;
      const m = re.exec(src2);
      const open = src2.indexOf('{', m.index);
      let d = 0, j = open;
      for (; j < src2.length; j++) {
        if (src2[j] === '{') d++;
        else if (src2[j] === '}' && --d === 0) break;
      }
      const b = src2.slice(m.index, j + 1);
      // Stripped at the same three points as the real detector above. This probe
      // is a SECOND COPY of that logic, which is the drift this whole file exists
      // to catch -- so when one side learns something the other has to, or the
      // arms below end up proving a function nothing runs.
      const bc = stripJsComments(b);
      let speaks = /console\.|toast|Toast|alert\(/.test(bc);
      if (!speaks) {
        const called = bc.match(/(?<![\w.$])([A-Za-z_$][\w$]*)\s*\(/g) || [];
        speaks = called.some((c) => {
          const nm = c.replace(/\s*\($/, '');
          const dm = new RegExp('function\\s+' + nm + '\\s*\\(').exec(src2);
          if (!dm) return false;
          const o = src2.indexOf('{', dm.index);
          let dd = 0, k = o;
          for (; k < src2.length; k++) {
            if (src2[k] === '{') dd++;
            else if (src2[k] === '}' && --dd === 0) break;
          }
          return /console\.|toast|Toast|alert\(/
            .test(stripJsComments(src2.slice(dm.index, k + 1)));
        });
      }
      return speaks;
    };
    check('a catch calling a helper that LOGS counts as speaking',
      probe('try{localStorage.setItem(a,b);}catch(e){oops(e);}',
            'function oops(e){console.error(e);}'), true);
    check('a catch calling a helper that says NOTHING is still silent',
      probe('try{localStorage.setItem(a,b);}catch(e){oops(e);}',
            'function oops(e){return false;}'), false);
    check('a catch calling a function that is not in the file is still silent',
      probe('try{localStorage.setItem(a,b);}catch(e){elsewhere(e);}'), false);
    check('and a bare empty catch is still silent',
      probe('try{localStorage.setItem(a,b);}catch(e){}'), false);

    // ── A COMMENT IS NOT A REPORT (2026-09-10) ──────────────────────────────
    // The shape found live: sairnvet.html's st() body carries the lines
    //   "// Every non-success exit latches the key so the next success toast is"
    //   "// corrected rather than believed -- see showToast() above."
    // and those two alone kept this block green after every real console call in
    // that function was removed. Both directions are asserted -- a wrapper whose
    // only mention of a toast is prose must be LISTED, and a wrapper that really
    // speaks must still pass, or the strip would turn a false negative into a
    // false positive and the list would go red on working code.
    check('a catch whose only "toast" is a COMMENT is silent',
      probe('try{localStorage.setItem(a,b);}catch(e){/* the success toast is '
            + 'corrected next time -- see showToast() above */ return false;}'), false);
    check('...including a line comment, which is how the real one was written',
      probe('try{localStorage.setItem(a,b);}catch(e){\n'
            + '  // the next success toast is corrected rather than believed\n'
            + '  return false;}'), false);
    check('a PROSE MENTION of a logging helper is not a call to it',
      probe('try{localStorage.setItem(a,b);}catch(e){ // see oops() above\n return false;}',
            'function oops(e){console.error(e);}'), false);
    check('and a real call beside a comment still speaks',
      probe('try{localStorage.setItem(a,b);}catch(e){ // see oops() above\n oops(e);}',
            'function oops(e){console.error(e);}'), true);

    // THE STRIPPER ITSELF, because a stripper that eats code would turn every
    // working wrapper into a finding. tools/jscomments.py exists because three
    // of seven regex strippers in tools/ were destroying 90% of their input.
    check('the stripper does NOT treat a // inside a string as a comment',
      /console\./.test(stripJsComments(
        'var u = "https://x/y"; console.error(u);')), true);
    check('...nor a /* inside a string',
      /console\./.test(stripJsComments(
        "var s = '/* not a comment */'; console.warn(s);")), true);
    check('...nor one inside a template literal',
      /toast/.test(stripJsComments('var t = `a // b`; toast(t);')), true);
    check('an escaped quote does not end the string early',
      /console\./.test(stripJsComments(
        'var s = "it\\" // still a string"; console.log(s);')), true);
    check('a real block comment IS removed',
      /console\./.test(stripJsComments('/* console.error(1) */ return false;')), false);

    // THE MEASUREMENT THAT MADE THE STRIP SAFE TO LAND, kept as a standing arm
    // rather than a sentence in a commit message. Zero wrappers relied on prose
    // the day it was added, so the strip changed no verdict.
    //
    // IT IS ALSO THE TRIPWIRE, and it is sharper than the `mute` list above.
    // A wrapper listed here is one whose ONLY mention of a console or a toast is
    // a comment -- it may still pass the list by DELEGATION (sairnvet's st()
    // calls svSyncCollection(), which logs about a failed server push, nothing
    // to do with the localStorage write), so the list can stay empty while the
    // write-failure path has gone quiet. Verified that way: silencing every real
    // console.error in sairnvet's st() turns THIS arm red and leaves the list
    // green. If this fires, read the named wrapper's catch before anything else.
    check('no wrapper speaks only in prose -- a comment is not a report', (() => {
      const changed = [];
      fs.readdirSync(ROOT).filter((f) => f.endsWith('.html')).sort().forEach((f) => {
        const src = read(f);
        const re2 = /function\s+(\w+)\s*\(\s*\w+\s*,\s*\w+\s*\)\s*\{/g;
        let mm;
        while ((mm = re2.exec(src)) !== null) {
          const open = src.indexOf('{', mm.index);
          let d = 0, j2 = open;
          for (; j2 < src.length && j2 - open < 4000; j2++) {
            if (src[j2] === '{') d++;
            else if (src[j2] === '}' && --d === 0) break;
          }
          const bd = src.slice(mm.index, j2 + 1);
          if (bd.indexOf('localStorage.setItem') === -1) continue;
          const sp = /console\.|toast|Toast|alert\(/;
          if (sp.test(bd) !== sp.test(stripJsComments(bd))) changed.push(f + ':' + mm[1]);
        }
      });
      return changed;
    })(), []);
  }
  // The five fixed ones, named individually so a regression points at the app
  // rather than at a list diff.
  ['sairndental.html', 'sairndesign.html', 'sairnlaw.html', 'sairnlegacy.html',
   'sairncare.html', 'sairnfreedom.html', 'sairnbiz.html',
   'sairnvet.html'].forEach((f) => {
    check(f + ' speaks when a write is refused',
      mute.filter((x) => x.indexOf(f + ':') === 0).length, 0);
  });
}

console.log((fail ? 'FAILED' : 'ok') + '  sairn-storage-wrapper-honesty: ' +
  pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
