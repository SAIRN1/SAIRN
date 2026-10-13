// tests/phi_cache_scoped_to_user.js
//
// Run:  node tests/phi_cache_scoped_to_user.js
//
// SAIRNcare and SAIRNsenior, driven verbatim from their HTML.
//
// THE DEFECT. Both apps promise, ON SCREEN, that the AI is scoped:
//   SAIRNcare   "a Med Aide's AI answers never include a resident assigned to
//                someone else"
//   SAIRNsenior "a caregiver's AI answers never include another caregiver's
//                clients"
// THE SERVER HONOURED THAT. THE LOCAL CACHE DID NOT. Every hydrate is an
// ADDITIVE merge -- it pushes server rows the cache lacks and never removes one
// it has -- and doLogout() cleared only the session key. So on a device where
// two people sign in, which is the ORDINARY case in both industries (one
// station tablet at a nurses' desk; one office machine in a home-care agency),
// the roster an owner hydrated was still in `alf_clients` / `sen_clients` when
// the next person signed in. residents()/clients() read that cache, and BOTH
// the on-screen list and the outbound AI prompt are built from it -- a prompt
// that told the model the list was "already scoped server-side to what they are
// allowed to see".
//
// PHI belonging to people the second user is not assigned to, on screen and in
// an outbound request.
//
// WHAT IS ASSERTED. The cache is purged when the PERSON changes (employee id or
// role) and on sign-out, and is NOT purged otherwise -- the additive merge
// exists so an offline device does not lose rows the server has not seen yet,
// and a purge on every sign-in would throw that away every morning.
//
// ARM 3 IS THE NEGATIVE CONTROL and it is the one that matters: a fix that
// simply purged on every entry would pass every "no leak" assertion here while
// silently deleting a night shift's offline work.
//
// ARM 5 checks the purge LIST against the keys each app actually writes, so an
// app growing a new cached collection cannot quietly fall outside the guard --
// that is how the first draft of this fix named `alf_careplans`, a key that
// does not exist, while the list was otherwise maintained by hand.

'use strict';
const fs = require('fs');
const path = require('path');
const { stripComments } = require('./lib/strip_comments.js');

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log('PASS  ' + name + (detail ? '  ' + detail : '')); return; }
  fail++;
  console.log('FAIL  ' + name + (detail ? '  ' + detail : ''));
}
function eq(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; console.log('PASS  ' + name + '  ' + a); return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}


// ── A DIRTY SUBJECT IS A SKIP, NOT A FAILURE (2026-10-12, batch b5 item 3) ──
// THE SYMPTOM. hank's 2026-10-08 whole-tree table records this file as
// "63 passed, 1 failed" in the suite and "72 passed, 0 failed" ALONE, and files
// it under CASCADE -- "an artefact of the tree being dirty by the time they
// ran." Re-measured here: 72/0 alone, three times, exit 0.
//
// THIS FILE READS SEVEN FILES IT DOES NOT OWN and asserts over their text. Any
// suite that plants a defect in one of them -- and several do, correctly, to
// prove their own arms can fail -- turns an assertion here into a FAIL about a
// file this suite never changed. The three live mutators of sairnbuild.html
// were each checked and each is isolated (a TMP copy plus BLD_HTML, or a staged
// worktree), and the one plant on api/sd-data.js that looked likeliest was
// ABLATED: `, warn_days: gateWarn` removed exactly as
// tests/seam_check/run_delegation_probe.py:241 removes it, 72/0 WITH the plant,
// file restored byte-identical. SO THE PARTICULAR MUTATOR IS NOT ESTABLISHED
// and is not named -- an invented cause ends the investigation.
//
// WHAT IS FIXED IS THE SIGNAL, WHICH IS THIS FILE'S OWN PROBLEM. A suite whose
// subject moved under it must not report FAIL, because FAIL here reads as "the
// PHI cache leaked" -- the most expensive sentence this file can print -- when
// nothing about the cache was examined. Exit 3 is SKIPPED, which
// tools/run_all_tests.py reports apart from both pass and fail (see its
// returncode == 3 branch), so the third state already exists downstream.
// Idiom copied deliberately from tests/seam_check/run_delegation_probe.py,
// which learned it on 2026-09-09.
//
// IT CANNOT MASK A REAL FAILURE: the gate fires only when git says a SUBJECT
// file differs from HEAD, and names the ones that do. If git cannot be
// consulted that is reported and the suite RUNS -- an unreadable git is not
// evidence the tree is dirty, and refusing to run on it would be a worse
// silence than the one being fixed.
const SUBJECTS = [
  'sairncare.html', 'sairnsenior.html', 'sairndental.html', 'sairnbuild.html',
  'stonedesk.html', 'sairnroofing.html', 'api/sd-data.js'
];
{
  const { execFileSync } = require('child_process');
  let porcelain = null;
  try {
    porcelain = execFileSync('git', ['status', '--porcelain', '--'].concat(SUBJECTS),
                             { cwd: path.join(__dirname, '..'), encoding: 'utf8' });
  } catch (e) {
    console.log('NOTE: git could not be consulted (' + e.message.split('\n')[0]
                + '), so a dirty subject cannot be ruled out. RUNNING ANYWAY '
                + 'and saying so, rather than skipping on an unknown.');
  }
  if (porcelain && porcelain.trim()) {
    const dirty = porcelain.trim().split('\n').map((l) => l.slice(3).trim());
    console.log('SKIPPED: a file this suite READS differs from HEAD, so a FAIL '
                + 'here would be about somebody else\'s in-flight change and '
                + 'would read as a PHI cache leak. Nothing about the cache was '
                + 'verified: ' + dirty.join(', '));
    process.exit(3);
  }
}

// ── SELF-ISOLATING SETUP, 2026-10-13 (b8 item 4) ──────────────────────────
// THE PROBLEM THIS CLOSES IS NOT "MODULE STATE" IN THE USUAL SENSE. This suite
// holds no mutable globals and shares no objects between arms -- each simulated
// browser gets its own `store`. What it DID do is read its seven subjects at
// FOUR different points during the run: a top-level const at :263, two more at
// :381 and :389, and `readApp()` inside two loops. So a subject edited by
// anything else WHILE this suite was running changed the answer an arm got
// depending on where in the file that arm sat, which is order-dependence
// wearing a different hat -- the suite was sampling a moving subject.
//
// EVERY SUBJECT IS NOW READ EXACTLY ONCE, HERE, BEFORE ANY ARM RUNS, and every
// later read is served from that snapshot. After this point the suite cannot
// see a mid-run change at all: 72 arms all measure the same seven files as they
// stood at setup. Combined with the precondition above (which SKIPS if a
// subject is already dirty at start) and the diagnostic at the end (which NAMES
// a subject that moved by the time a failure happened), the three cover the
// three distinct moments something could interfere.
//
// FROZEN, so a later edit to this file cannot accidentally mutate the snapshot
// and reintroduce the thing being removed. And NOT CACHED LAZILY: a lazy cache
// would still take its first read whenever the first arm asked, which is the
// defect with an extra step.
const SNAP = Object.freeze(SUBJECTS.reduce((acc, rel) => {
  acc[rel] = fs.readFileSync(path.join(__dirname, '..', rel), 'utf8');
  return acc;
}, {}));

function readApp(file) {
  // A subject outside the declared seven would be read live and silently
  // reintroduce the order-dependence, so it is an error rather than a fallback.
  if (!Object.prototype.hasOwnProperty.call(SNAP, file)) {
    throw new Error('readApp(' + JSON.stringify(file) + '): not one of this '
      + "suite's declared SUBJECTS, so it has no snapshot. Add it to SUBJECTS "
      + 'rather than reading it live -- a live read is what b8 item 4 removed.');
  }
  return SNAP[file];
}

// THE KEYS THE APP ACTUALLY WRITES -- FROM CODE, NOT FROM PROSE.
//
// ADDED 2026-10-07 because arm 5a was RED on a key that does not exist as a
// write. The extraction ran over the raw file, so the two lines of
// sairnsenior.html:5772,5774 that say -- in a comment, as a decision --
//
//     // no literal setItem('sen_settings') or st('sen_settings') write either
//     // There is no `st('sen_settings')` because there must not be one
//
// were counted as two write sites for `sen_settings`, and arm 5a then demanded
// that a non-existent cache be purged or exempted. THE COMMENT EXPLAINING THAT A
// KEY IS NEVER WRITTEN WAS READ AS THE KEY BEING WRITTEN, which is the same
// defect shape this repo already paid for in tools/truthy_sum_check.py (the
// pattern quoted in a comment is not code) and in tools/comment_quote_check.py.
//
// Fixing it by naming `sen_settings` as an exclusion would have been WRONG in the
// direction that matters: it would put a key in SEN_UNSCOPED_CACHES to satisfy a
// checker, and the next real unpurged cache would then look like more of the
// same. The write site is what was wrong, not the app.
//
// tests/lib/strip_comments.js is used rather than a fifth private version --
// see that file's header for the three ways the private versions were wrong,
// including the `accept="image/*"` one that opened a comment in THIS VERY APP.
// Arm 5e is the control, in both directions, and it FAILS without this.
function writtenKeys(src, prefix) {
  const re = new RegExp("[ls][dt]\\('(" + prefix + "[a-z_]+)'", 'g');
  const out = new Set();
  let m;
  while ((m = re.exec(stripComments(src))) !== null) out.add(m[1]);
  return out;
}

function balancedFrom(src, start) {
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced');
}
function fn(src, decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('not found: ' + decl);
  return balancedFrom(src, i);
}
function arrayDecl(src, name) {
  const i = src.indexOf('var ' + name + ' =');
  if (i < 0) throw new Error('not found: ' + name);
  const j = src.indexOf('];', i);
  return src.slice(i, j + 2);
}

// One simulated browser. localStorage persists across sign-ins, which is the
// entire scenario -- a shared device.
function makeWorld(app) {
  const src = readApp(app.file);
  const data = {};
  const store = {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v); },
    removeItem: (k) => { delete data[k]; }
  };
  const body = [
    arrayDecl(src, app.listName),
    arrayDecl(src, app.unscopedName),
    fn(src, 'function ' + app.purgeFn + '('),
    fn(src, 'function ' + app.changedFn + '('),
    'function enter(d){ if(' + app.changedFn + '(d))' + app.purgeFn + '(); }',
    'function logout(){ ' + app.purgeFn + '(); try{localStorage.removeItem("' + app.ownerKey + '");}catch(e){} }',
    'return { enter: enter, logout: logout, list: ' + app.listName +
      ', unscoped: ' + app.unscopedName + ' };'
  ].join('\n');
  // eslint-disable-next-line no-new-func
  const api = new Function('localStorage', body)(store);
  return { api, data, src };
}

const APPS = [
  { name: 'SAIRNcare', file: 'sairncare.html', prefix: 'alf_', listName: 'ALF_SCOPED_CACHES',
    purgeFn: 'alfPurgeScopedCaches', changedFn: 'alfCacheOwnerChanged',
    ownerKey: 'alf_cache_owner', phi: 'alf_clients', unscopedName: 'ALF_UNSCOPED_CACHES',
    enterFn: 'alfEnterApp' },
  { name: 'SAIRNsenior', file: 'sairnsenior.html', prefix: 'sen_', listName: 'SEN_SCOPED_CACHES',
    purgeFn: 'senPurgeScopedCaches', changedFn: 'senCacheOwnerChanged',
    ownerKey: 'sen_cache_owner', phi: 'sen_clients', unscopedName: 'SEN_UNSCOPED_CACHES',
    enterFn: 'senEnterApp' },
  // THE SHARPEST OF THE THREE. This one caches the financial resources whose
  // server gate was closed the same day (ddbd1f2c) AND the patient-scoped ones,
  // so the stale cache defeated both at once on a shared operatory tablet.
  { name: 'SAIRNdental', file: 'sairndental.html', prefix: 'dnt_', listName: 'DNT_SCOPED_CACHES',
    purgeFn: 'dntPurgeScopedCaches', changedFn: 'dntCacheOwnerChanged',
    ownerKey: 'dnt_cache_owner', phi: 'dnt_patients_list', unscopedName: 'DNT_UNSCOPED_CACHES',
    enterFn: 'dntEnterApp',
    roles: ['owner', 'provider'],
    promise: 'only the owner can add a provider or change which sign-in is linked to one' },
  // FOUND BY DERIVING THE LIST, not by noticing a fourth. api/sd-data.js holds
  // exactly nine read branches that filter rows by the caller's own employee
  // id; bld_bids (:3516) and bld_tna (:3590) are two of them, and bld_tna is an
  // employee's OWN training-needs assessment.
  { name: 'SAIRNbuild', file: 'sairnbuild.html', prefix: 'bld_', listName: 'BLD_SCOPED_CACHES',
    purgeFn: 'bldPurgeScopedCaches', changedFn: 'bldCacheOwnerChanged',
    ownerKey: 'bld_cache_owner', phi: 'bld_bids', unscopedName: 'BLD_UNSCOPED_CACHES',
    enterFn: 'bldEnterApp',
    roles: ['owner', 'field'],
    promise: 'superseded versions stay visible, never overwritten' }
];

console.log('The cache is scoped to the person, not just the read\n');

// -- ARM -1: THE GUARD IS WIRED IN, not merely present ---------------------
// ADDED 2026-09-15 BY THIS SUITE'S FIRST NEGATIVE CONTROL.
// tests/phi_cache_scope_probe.py replaced the real
//   if(alfCacheOwnerChanged(d))alfPurgeScopedCaches();
// with a bare `alfCacheOwnerChanged(d);` -- the guard evaluated, its answer
// thrown away, the purge never called -- and THIS SUITE STAYED GREEN.
//
// The reason is structural and worth stating. makeWorld() builds its own
//   function enter(d){ if(changed(d)) purge(); }
// out of the two pieces. That is the right way to drive the MECHANISM in
// isolation, and it means every arm below proves the two functions work
// together WITHOUT EVER PROVING THE APP CALLS THEM THAT WAY. The suite was
// testing a wiring it had written itself.
//
// So this arm reads each app's REAL entry function and asserts the guarded
// call is inside it -- anchored to that function's own body rather than to the
// file, because a match anywhere in 2MB of HTML is satisfied by the comment
// block that explains the mechanism.
APPS.forEach(function (app) {
  const body = fn(readApp(app.file), 'function ' + app.enterFn + '(');
  const guarded = new RegExp('if\\s*\\(\\s*' + app.changedFn
      + '\\s*\\([^)]*\\)\\s*\\)\\s*' + app.purgeFn + '\\s*\\(');
  ok(app.name + ': ' + app.enterFn + '() calls the purge, GUARDED',
    guarded.test(body),
    guarded.test(body) ? '' : 'the two functions can both be perfect and the '
      + 'roster still survives a second sign-in, because nothing connects them');
  const discarded = new RegExp('(^|[;{}])\\s*' + app.changedFn + '\\s*\\([^)]*\\)\\s*;');
  ok(app.name + ': ...and the guard result is not DISCARDED',
    !discarded.test(body),
    discarded.test(body) ? app.changedFn + ' is called on its own line' : '');
});

// -- ARM 0: THE SCOPE ITSELF IS DERIVED, NOT REMEMBERED --------------------
// api/sd-data.js is the only place that scopes a read to the caller's own
// employee id. Counting those branches is what turned "twelve apps, untriaged"
// into six apps and a finite list -- and it is what stops this suite silently
// falling behind a NEW scoped read added tomorrow. If this number moves, an app
// gained or lost a scoped read and this file must be revisited, not adjusted.
const API = readApp('api/sd-data.js');
const SCOPED_READS = (API.match(/out = out\.filter\(\(r\) => r\.(?:assigned|subject)_employee_id === session\.employee_id\)/g) || []).length;
eq('0a  api/sd-data.js scoped-read branches across six apps', SCOPED_READS, 9);
ok('0b  and every app carrying one is covered here, or named as another session\'s',
   SCOPED_READS === 9,
   'care x2, senior x2, build x2, stonedesk, roofing; sairndesign is Fourth\'s file');


APPS.forEach(function (app) {
  const OWNER = { employee_id: 'EMP-OWNER', role: 'owner' };
  const roles = app.roles || ['owner', app.prefix === 'alf_' ? 'med_aide' : 'caregiver'];
  const AIDE  = { employee_id: 'EMP-AIDE',  role: roles[1] };

  // ── ARM 1: the leak itself
  let w = makeWorld(app);
  w.api.enter(OWNER);
  w.data[app.phi] = JSON.stringify([{ id: 'R-1', name: 'Everyone on the roster' }]);
  ok('1a  ' + app.name + ': first sign-in does NOT purge (nothing to leak yet)',
     w.data[app.phi] !== undefined, 'cache survives the first entry');
  w.api.enter(AIDE);
  eq('1b  ' + app.name + ": a different person's sign-in clears the PHI cache",
     w.data[app.phi], undefined);

  // ── ARM 2: a role change on the SAME login counts
  w = makeWorld(app);
  w.api.enter(OWNER);
  w.data[app.phi] = JSON.stringify([{ id: 'R-1' }]);
  w.api.enter({ employee_id: 'EMP-OWNER', role: AIDE.role });
  eq('2a  ' + app.name + ': a narrowed ROLE on the same login clears it too',
     w.data[app.phi], undefined);

  // ── ARM 3: NEGATIVE CONTROL -- the SAME person keeps their cache
  w = makeWorld(app);
  w.api.enter(AIDE);
  w.data[app.phi] = JSON.stringify([{ id: 'R-9', name: 'written offline' }]);
  w.api.enter(AIDE);
  ok('3a  CONTROL: ' + app.name + ' keeps the cache when the same person returns',
     w.data[app.phi] !== undefined,
     'offline rows the server has not seen yet survive');
  w.api.enter(AIDE);
  w.api.enter(AIDE);
  ok('3b  CONTROL: ' + app.name + ' still keeps it after repeated sign-ins',
     w.data[app.phi] !== undefined, '');

  // ── ARM 4: sign-out clears it, and forgets whose it was
  w = makeWorld(app);
  w.api.enter(OWNER);
  w.data[app.phi] = JSON.stringify([{ id: 'R-1' }]);
  w.api.logout();
  eq('4a  ' + app.name + ': sign-out clears the PHI cache', w.data[app.phi], undefined);
  eq('4b  ' + app.name + ': and drops the cache-owner marker', w.data[app.ownerKey], undefined);

  // ── ARM 4c: SAIRNdental only -- the FINANCIAL caches go too, because those
  // are the ones whose server gate closed the same day.
  if (app.prefix === 'dnt_') {
    const MONEY = ['dnt_payments_list', 'dnt_charges_list', 'dnt_denial_list',
                   'dnt_gfe_list', 'dnt_txplans_list'];
    const w2 = makeWorld(app);
    w2.api.enter(OWNER);
    MONEY.forEach(function (k) { w2.data[k] = '[{"id":"X"}]'; });
    w2.api.enter(AIDE);
    eq('4c  ' + app.name + ': every financial cache is cleared for the next person',
       MONEY.filter(function (k) { return w2.data[k] !== undefined; }), []);
  }

  // ── ARM 5: the purge list covers every cached collection the app writes
  const written = writtenKeys(w.src, app.prefix);
  // EVERY key must be in EXACTLY ONE of the two lists. An exclusion is a
  // decision with a reason beside it in the source, not an omission -- that is
  // the difference between this and the allowlists that caused the bugs this
  // week. Excluding by silence is how a new cached collection falls outside the
  // guard without anyone deciding it should.
  const list = new Set(w.api.list);
  const unscoped = new Set(w.api.unscoped);
  const missing = [...written].filter((k) => !list.has(k) && !unscoped.has(k)).sort();
  const phantom = [...list].filter((k) => !written.has(k)).sort();
  const both = [...list].filter((k) => unscoped.has(k)).sort();
  eq('5a  ' + app.name + ': every cached key is purged OR explicitly excluded', missing, []);
  eq('5b  ' + app.name + ': the purge list names nothing that does not exist', phantom, []);
  eq('5c  ' + app.name + ': no key is in both lists', both, []);
  ok('5d  ' + app.name + ': the exclusion list is non-empty and reasoned',
     unscoped.size > 0 && /DELIBERATELY NOT PURGED/.test(w.src),
     [...unscoped].join(', '));
  // 5d reads the RAW source on purpose: the reason it is looking for IS a
  // comment. Only the write-site extraction may not see prose.

  // ── ARM 5e: THE CONTROL ON THE EXTRACTOR, BOTH DIRECTIONS.
  // Without it, arm 5a's input is trusted, and arm 5a spent a batch red over a
  // key quoted in a comment that says the key is never written. A checker whose
  // own input is unverified reports the defects of its parser as defects of its
  // subject.
  const P = app.prefix;
  const REAL = '<script>function f(){ st(\'' + P + 'ghost\', 1); }</script>\n';
  const QUOTED = '<script>\n'
    + '// no literal setItem(\'' + P + 'ghost\') or st(\'' + P + 'ghost\') write either\n'
    + '/* There is no `st(\'' + P + 'ghost\')` because there must not be one. */\n'
    + 'function f(){ return 1; }\n</script>\n';
  eq('5e  ' + app.name + ': a REAL st() write IS counted',
     [...writtenKeys(REAL, P)], [P + 'ghost']);
  eq('5e  ' + app.name + ': ...and the SAME text in // and /* */ comments is NOT',
     [...writtenKeys(QUOTED, P)], []);

  // ── ARM 6: the on-screen promise this exists to make true is still there
  const promise = app.promise || (app.prefix === 'alf_'
    ? 'never include a resident assigned to someone else'
    : "never include another caregiver's clients");
  ok('6a  ' + app.name + ': the on-screen claim is still made',
     w.src.indexOf(promise) !== -1,
     'if this is ever deleted, delete this guard too -- or find out why it was untrue');
});


// STONEDESK AND SAIRNROOFING ARE ASSERTED SEPARATELY, because neither fits the
// shape above and saying so is better than bending them into it:
//   StoneDesk has ONE assignment-scoped key (sd_crm) among many practice-wide
//     ones, and THREE sign-in paths rather than one enter function.
//   SAIRNroofing persists NOTHING scoped -- checked, not assumed -- so its
//     exposure is an in-memory list across a same-tab re-login.
const SD = readApp('stonedesk.html');
ok('7a  StoneDesk purges the assignment-scoped CRM cache',
   /var SD_SCOPED_CACHES = \['sd_crm'\];/.test(SD), '');
eq('7b  StoneDesk wires the check into EVERY sign-in path, not one',
   (SD.match(/window\.sdCacheOwnerCheck === 'function'\) window\.sdCacheOwnerCheck\(\)/g) || []).length, 3);
ok('7c  and doLogout purges it',
   /currentUser = null;[\s\S]{0,260}sdPurgeScopedCaches\(\);/.test(SD), '');

const RF = readApp('sairnroofing.html');
ok('8a  SAIRNroofing clears the in-memory job list on sign-out',
   /rfSession=null;[\s\S]{0,1600}currentJobs=\[\];/.test(RF), '');
const rfKeys = [...new Set((RF.match(/localStorage\.(?:setItem|getItem|removeItem)\('rf_[a-z_]+'/g) || [])
  .map((m) => m.replace(/^.*'(rf_[a-z_]+)'$/, '$1')))].sort();
eq('8b  CONTROL: SAIRNroofing persists nothing scoped, which is why 8a is the whole fix',
   rfKeys, ['rf_license_key', 'rf_session']);

console.log('\n%d passed, %d failed', pass, fail);

// ── ON FAILURE, NAME THE DIRTY SUBJECT (2026-10-14, b7 item 3) ─────────────
// The precondition at the top of this file SKIPS when a subject is already
// dirty, which handles the case where the pollution is in place before the
// first arm runs. It does NOT handle the case this file has actually been
// seen in: dirty DURING the run, by a suite executing concurrently or by one
// whose restore lands late. There the precondition passes, an arm fails, and
// the output says "the PHI cache leaked" about somebody else's in-flight edit.
//
// So the question is asked again at the END, and only on failure. Two batches
// have now gone looking for the polluting suite by elimination and by bisect;
// this makes the NEXT occurrence name the file itself, which is cheaper than
// either and does not expire.
//
// IT DOES NOT CHANGE THE VERDICT. The exit code is still `fail ? 1 : 0` -- a
// diagnostic that downgraded a failure to a skip would be the same silence one
// level along, and the dirty subject might be the real defect rather than
// pollution. It prints evidence and leaves the judgement to the reader.
if (fail) {
  const { execFileSync } = require('child_process');
  let dirty = null;
  try {
    const out = execFileSync('git', ['status', '--porcelain', '--'].concat(SUBJECTS),
                             { cwd: path.join(__dirname, '..'), encoding: 'utf8' });
    dirty = out.trim() ? out.trim().split('\n').map((l) => l.slice(3).trim()) : [];
  } catch (e) {
    console.log('DIAGNOSTIC: git could not be consulted (' + e.message.split('\n')[0]
                + '). Whether a subject is dirty is UNKNOWN, which is not the same '
                + 'as clean -- see core.bare.');
  }
  if (dirty && dirty.length) {
    console.log('DIAGNOSTIC: %d of this suite\'s %d subjects DIFFER FROM HEAD right '
                + 'now: %s', dirty.length, SUBJECTS.length, dirty.join(', '));
    console.log('DIAGNOSTIC: a failure here may be about that edit and not about the '
                + 'PHI cache. Re-run alone on a clean tree before believing it.');
  } else if (dirty) {
    console.log('DIAGNOSTIC: all %d subjects are clean against HEAD, so this failure '
                + 'is NOT tree pollution.', SUBJECTS.length);
  }
}
process.exit(fail ? 1 : 0);
