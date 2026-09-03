// SAIRNdental real-sync vs a full localStorage -- driven verbatim from
// sairndental.html.
//
// THE DEFECT, and it is the silent-failure class in its purest form:
//
//     function st(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}
//
// A bare empty catch. A QuotaExceededError was swallowed whole -- nothing
// stored, nothing shown, nothing logged. Then dntSyncFromServer() did:
//
//     if(serverData.length){st(key,...);changed=true;}
//
// -- setting `changed` UNCONDITIONALLY, so a failed write still triggered a
// full re-render from ld(), which returns the OLD data. The screen refreshed
// itself back to stale. And failureCount counted only NETWORK failures, so
// dntRefreshPending() reported "Refreshed from server".
//
// Real data pulled off the server, silently discarded, success claimed, stale
// screen. Nothing anywhere said otherwise.
//
// IT IS REACHABLE BY DESIGN, not by abuse: appointments carry base64 PHOTOS, so
// dnt_appointments_list is the key that reaches the ~5MB origin quota first --
// and once it does, EVERY later st() in the same sweep fails the same way.
//
// The functions below are EXTRACTED from sairndental.html and driven against a
// fake localStorage that can be told to be full. Nothing is reimplemented: a
// stub of st() would be a stub of the very thing under test.

const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', '..', 'sairndental.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function balanced(start) {
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
function fn(decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('not found: ' + decl);
  return balanced(i);
}
function scalarVar(name) {
  const m = src.match(new RegExp('var ' + name + ' = ([^;]+);'));
  if (!m) throw new Error('not found: var ' + name);
  return 'var ' + name + ' = ' + m[1] + ';';
}

// A localStorage that can be told to refuse. `fullFrom` makes every write from
// the Nth call onward throw the real DOMException shape a browser throws.
function makeStore(fullFrom) {
  const data = {};
  let writes = 0;
  return {
    store: {
      getItem: (k) => (k in data ? data[k] : null),
      setItem: (k, v) => {
        writes++;
        if (fullFrom && writes >= fullFrom) {
          const e = new Error('quota');
          e.name = 'QuotaExceededError';
          e.code = 22;
          throw e;
        }
        data[k] = v;
      }
    },
    data: data,
    writeCount: () => writes
  };
}

function build(store, logs) {
  return new Function('localStorage', 'console',
    scalarVar('dntQuotaHit') + '\n' +
    fn('function dntIsQuotaError(e)') + '\n' +
    fn('function st(k,v)') + '\n' +
    fn('function ld(k,d)') + '\n' +
    fn('function dntStorageFailureMessage(result)') + '\n' +
    'return { st: st, ld: ld, msg: dntStorageFailureMessage,' +
    '         quotaHit: function(){ return dntQuotaHit; } };'
  )(store, { error: (m) => logs.push(String(m)) });
}

// ── st() reports, and logs, instead of swallowing ──────────────────────
{
  const s = makeStore(0), logs = [];
  const w = build(s.store, logs);
  check('a write that succeeds returns true', w.st('k', { a: 1 }), true);
  check('and is actually stored', JSON.parse(s.data.k), { a: 1 });
  check('nothing is logged on the happy path', logs.length, 0);
}
{
  const s = makeStore(1), logs = [];   // full from the very first write
  const w = build(s.store, logs);
  check('a write that hits the quota returns FALSE rather than nothing',
    w.st('dnt_appointments_list', [{ id: 'A' }]), false);
  check('the key is absent -- the data really was discarded',
    's' in s.data || 'dnt_appointments_list' in s.data, false);
  check('and it is LOGGED, always -- a vanished write must not vanish from the console too',
    logs.length, 1);
  check('the log names the key and says storage is full',
    /dnt_appointments_list/.test(logs[0]) && /storage is FULL/i.test(logs[0]), true);
  check('the quota flag is set so a caller can tell full from broken', w.quotaHit(), true);
}
{
  // A NON-quota failure must not be reported as a full disk. Telling a practice
  // to clear photos when the real cause is something else sends them to delete
  // clinical records for nothing.
  const data = {};
  const store = { getItem: (k) => (k in data ? data[k] : null),
                  setItem: () => { const e = new Error('nope'); e.name = 'SecurityError'; throw e; } };
  const logs = [];
  const w = build(store, logs);
  check('a non-quota failure still returns false', w.st('k', 1), false);
  check('but is NOT reported as a full disk', w.quotaHit(), false);
  check('and the log says what actually happened',
    /storage is FULL/i.test(logs[0]), false);
}
{
  // The circular-reference case: JSON.stringify throws before localStorage is
  // ever reached. Must be a clean false, not an unhandled throw.
  const s = makeStore(0), logs = [];
  const w = build(s.store, logs);
  const cyc = {}; cyc.self = cyc;
  check('an unserialisable value fails cleanly rather than throwing', w.st('k', cyc), false);
  check('and is not blamed on the quota', w.quotaHit(), false);
}

// ── the message the practice actually reads ────────────────────────────
{
  const s = makeStore(0), logs = [];
  const w = build(s.store, logs);
  check('no storage failures produces no message', w.msg({ storage_failures: [] }), '');
  const full = w.msg({ storage_failures: ['dnt_appointments_list', 'dnt_charges_list'], storage_full: true });
  check('a full disk says so in the first words', /^This device is OUT OF STORAGE/.test(full), true);
  check('it counts what was lost', /2 record set\(s\) were downloaded but NOT saved/.test(full), true);
  check('it warns the screen is stale, which is the part that costs money',
    /what is on screen may be out of date/.test(full), true);
  // Naming the photos is the difference between an actionable message and a
  // dead end -- they are base64 and are what fills the quota.
  check('it names the photos, so there is something to actually do',
    /Appointment photos are usually what fills it/.test(full), true);
  check('and it says the server still has everything, so nobody panics',
    /Nothing on the server was lost/.test(full), true);
  const other = w.msg({ storage_failures: ['dnt_charges_list'], storage_full: false });
  check('a non-quota refusal does NOT claim the device is out of storage',
    /OUT OF STORAGE/.test(other), false);
}

// ── the sweep: changed, failures, and the report ───────────────────────
// Asserted on the real source, because dntSyncFromServer is async and reaches
// sdnData/rDash/a dozen renderers -- driving it would mean stubbing so much
// that the stubs, not the code, would be under test.
const SYNC = fn('async function dntSyncFromServer()');
check('`changed` is set ONLY when the write landed -- it used to be unconditional',
  /if\(st\(key,dntMergeById\(ld\(key,\[\]\),serverData\)\)\) changed=true;\s*\n\s*else storageFailures\.push\(key\);/.test(SYNC), true);
check('the settings write is checked the same way',
  /if\(st\('dnt_settings_obj',serverSettings\)\) changed=true;/.test(SYNC), true);
check('and so is the credential-rules write',
  /if\(st\('dnt_cred_rules_list',ruleData\)\) changed=true;/.test(SYNC), true);
check('every storage failure is collected, not counted into the network total',
  (SYNC.match(/storageFailures\.push\(/g) || []).length, 3);
check('the result carries them out, so a caller can report them',
  /storage_failures:storageFailures, storage_full:dntQuotaHit/.test(SYNC), true);
// The network failure count must NOT absorb storage failures -- they need
// different messages and different fixes.
check('failureCount still has exactly its three network sites, unchanged',
  (SYNC.match(/failureCount\+\+/g) || []).length, 3);
check('failureCount is incremented only in the non-array (network) branches',
  /\}else\{\s*\n\s*failureCount\+\+;/.test(SYNC), true);

// ── both callers speak, including the one nobody presses ───────────────
const REFRESH = fn('async function dntRefreshPending()');
check('the Refresh button no longer says "Refreshed from server" after a storage failure',
  /else if\(result&&result\.storage_failures&&result\.storage_failures\.length\)\{[\s\S]{0,400}?toast\(dntStorageFailureMessage\(result\), 12000\);/.test(REFRESH), true);
check('and the honest branch comes BEFORE the success branch, or it is unreachable',
  REFRESH.indexOf('storage_failures') < REFRESH.indexOf("'Refreshed from server'"), true);
const INIT = fn('function init()');
check('the BACKGROUND sync reports too -- it is the one nobody triggers',
  /dntSyncFromServer\(\)\.then\(function\(result\)\{[\s\S]{0,300}?toast\(dntStorageFailureMessage\(result\), 12000\);/.test(INIT), true);

// ── the empty catch is gone for good ───────────────────────────────────
const ST = fn('function st(k,v)');
check('st no longer swallows -- there is no bare empty catch left in it',
  /catch\(e\)\{\}/.test(ST), false);
check('and it returns a boolean on both paths',
  /return true;/.test(ST) && /return false;/.test(ST), true);
// 44 existing callers ignore the return value. That is fine and deliberate --
// the change is additive -- but it must stay a plain boolean, not a throw.
check('st still never throws, so the 44 callers that ignore it are unaffected',
  /throw/.test(ST), false);

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
