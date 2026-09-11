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

function readApp(file) { return fs.readFileSync(path.join(__dirname, '..', file), 'utf8'); }

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
    ownerKey: 'alf_cache_owner', phi: 'alf_clients', unscopedName: 'ALF_UNSCOPED_CACHES' },
  { name: 'SAIRNsenior', file: 'sairnsenior.html', prefix: 'sen_', listName: 'SEN_SCOPED_CACHES',
    purgeFn: 'senPurgeScopedCaches', changedFn: 'senCacheOwnerChanged',
    ownerKey: 'sen_cache_owner', phi: 'sen_clients', unscopedName: 'SEN_UNSCOPED_CACHES' },
  // THE SHARPEST OF THE THREE. This one caches the financial resources whose
  // server gate was closed the same day (ddbd1f2c) AND the patient-scoped ones,
  // so the stale cache defeated both at once on a shared operatory tablet.
  { name: 'SAIRNdental', file: 'sairndental.html', prefix: 'dnt_', listName: 'DNT_SCOPED_CACHES',
    purgeFn: 'dntPurgeScopedCaches', changedFn: 'dntCacheOwnerChanged',
    ownerKey: 'dnt_cache_owner', phi: 'dnt_patients_list', unscopedName: 'DNT_UNSCOPED_CACHES',
    roles: ['owner', 'provider'],
    promise: 'only the owner can add a provider or change which sign-in is linked to one' },
  // FOUND BY DERIVING THE LIST, not by noticing a fourth. api/sd-data.js holds
  // exactly nine read branches that filter rows by the caller's own employee
  // id; bld_bids (:3516) and bld_tna (:3590) are two of them, and bld_tna is an
  // employee's OWN training-needs assessment.
  { name: 'SAIRNbuild', file: 'sairnbuild.html', prefix: 'bld_', listName: 'BLD_SCOPED_CACHES',
    purgeFn: 'bldPurgeScopedCaches', changedFn: 'bldCacheOwnerChanged',
    ownerKey: 'bld_cache_owner', phi: 'bld_bids', unscopedName: 'BLD_UNSCOPED_CACHES',
    roles: ['owner', 'field'],
    promise: 'superseded versions stay visible, never overwritten' }
];

console.log('The cache is scoped to the person, not just the read\n');

// -- ARM 0: THE SCOPE ITSELF IS DERIVED, NOT REMEMBERED --------------------
// api/sd-data.js is the only place that scopes a read to the caller's own
// employee id. Counting those branches is what turned "twelve apps, untriaged"
// into six apps and a finite list -- and it is what stops this suite silently
// falling behind a NEW scoped read added tomorrow. If this number moves, an app
// gained or lost a scoped read and this file must be revisited, not adjusted.
const API = fs.readFileSync(path.join(__dirname, '..', 'api', 'sd-data.js'), 'utf8');
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
  const written = new Set();
  const re = new RegExp("[ls][dt]\\('(" + app.prefix + "[a-z_]+)'", 'g');
  let m;
  while ((m = re.exec(w.src)) !== null) written.add(m[1]);
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
const SD = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');
ok('7a  StoneDesk purges the assignment-scoped CRM cache',
   /var SD_SCOPED_CACHES = \['sd_crm'\];/.test(SD), '');
eq('7b  StoneDesk wires the check into EVERY sign-in path, not one',
   (SD.match(/window\.sdCacheOwnerCheck === 'function'\) window\.sdCacheOwnerCheck\(\)/g) || []).length, 3);
ok('7c  and doLogout purges it',
   /currentUser = null;[\s\S]{0,260}sdPurgeScopedCaches\(\);/.test(SD), '');

const RF = fs.readFileSync(path.join(__dirname, '..', 'sairnroofing.html'), 'utf8');
ok('8a  SAIRNroofing clears the in-memory job list on sign-out',
   /rfSession=null;[\s\S]{0,1600}currentJobs=\[\];/.test(RF), '');
const rfKeys = [...new Set((RF.match(/localStorage\.(?:setItem|getItem|removeItem)\('rf_[a-z_]+'/g) || [])
  .map((m) => m.replace(/^.*'(rf_[a-z_]+)'$/, '$1')))].sort();
eq('8b  CONTROL: SAIRNroofing persists nothing scoped, which is why 8a is the whole fix',
   rfKeys, ['rf_license_key', 'rf_session']);

console.log('\n%d passed, %d failed', pass, fail);
process.exit(fail ? 1 : 0);
