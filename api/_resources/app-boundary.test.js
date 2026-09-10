// api/_resources/app-boundary.test.js
// Run:  node api/_resources/app-boundary.test.js
//
// THE GAP THIS CLOSES, found by the independent review of the 2026-09-05
// scoping change and fixed on Michael's decision: scoping the resource LIST was
// a message control, not an access control. Against the real handler with an
// active `stonedesk` licence:
//
//     __nope__      -> 400 with the scoped list
//     law_matters   -> 200        <-- another app's resource type
//     sc_denial     -> 200
//     leg_cases     -> 200
//
// No cross-tenant DATA leak -- every row is license_hash-scoped, so what came
// back was that licence's own empty slice -- but the CAPABILITY to address
// another app's resource types was not gated at all.
//
// A foreign resource now answers EXACTLY as a resource that does not exist,
// which closes the enumeration oracle in the same move: before this, an
// authenticated caller could classify any guessed name one request at a time.
//
// THE MEASUREMENT IS AN ASSERTION HERE, not a note in a commit. Enforcing this
// is only safe because no app legitimately calls another app's resource on this
// endpoint, and that was measured across every app HTML before it shipped. The
// last section re-derives it on every run, so an app that starts making a
// cross-app call fails here rather than in production.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', '..');
const reg = require('./index');
const HANDLER = path.join(__dirname, '..', 'sd-data.js');

let pass = 0, fail = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }
function section(t) { queue.push({ section: t }); }

// ── the registry half ──────────────────────────────────────────────────────
section('isVisibleTo');

test('shared is visible to every registered app, and to an unknown one', () => {
  for (const app of reg.APP_NAMES.concat(['not-an-app', null])) {
    for (const name of reg.RESOURCE_NAMES_BY_APP.shared) {
      assert.ok(reg.isVisibleTo(name, app), name + ' hidden from ' + app);
    }
  }
});

test('every app can see everything it owns', () => {
  for (const app of reg.APP_NAMES) {
    if (app === 'shared') continue;
    for (const name of reg.RESOURCE_NAMES_BY_APP[app]) {
      assert.ok(reg.isVisibleTo(name, app), app + ' cannot see its own ' + name);
    }
  }
});

test('NO app can see another app\'s resources -- all pairs, not a sample', () => {
  const bad = [];
  for (const app of reg.APP_NAMES) {
    if (app === 'shared') continue;
    for (const name of reg.RESOURCE_NAMES) {
      const owner = reg.OWNER_BY_RESOURCE[name];
      if (owner === app || owner === 'shared') continue;
      if (reg.isVisibleTo(name, app)) bad.push(app + ' -> ' + name + ' (owned by ' + owner + ')');
    }
  }
  assert.deepStrictEqual(bad, [], bad.slice(0, 10).join('; '));
});

test('an UNATTRIBUTABLE licence is allowed through, deliberately', () => {
  // Same conservative direction as the scoped list, for the same reason:
  // nothing read lic.app_id before 2026-09-04, so refusing an unrecognised one
  // would break a real customer nobody can enumerate. The handler logs each.
  [null, undefined, '', '  ', 'not-an-app', 'shared'].forEach((app) => {
    assert.ok(reg.isVisibleTo('law_matters', app), 'app_id ' + JSON.stringify(app) + ' was gated');
  });
});

test('SAIRNcash is registered, with the empty list that is still true', () => {
  // WAS 'SAIRNvet AND SAIRNcash' UNTIL 2026-09-09, and it FIRED when SAIRNvet's
  // backup landed, which is the tripwire working rather than a stale test.
  // SAIRNvet now owns 41 resources and sairnvet.html really does request them;
  // sairncash.html still does not call this endpoint at all, so its list is
  // still the measured answer. What the assertion was protecting -- "registered
  // resources it does not use, a claim nothing backs" -- is now enforced for
  // BOTH apps by the next test, against the app HTML rather than against zero.
  assert.ok(reg.isKnownApp('sairncash'), 'sairncash is still unattributable');
  assert.deepStrictEqual(reg.RESOURCE_NAMES_BY_APP.sairncash, [],
    'sairncash registered resources it does not use -- a claim nothing backs');
  assert.ok(reg.isVisibleTo('shared_knowledge', 'sairncash'), 'sairncash cannot reach shared');
  assert.ok(!reg.isVisibleTo('law_matters', 'sairncash'), 'sairncash can reach another app');
});

test('every resource the two NEW registries claim is really requested by its app', () => {
  // The converse of "every resource an app HTML asks for is its own or shared",
  // and the half that actually replaces the empty-list assertion: a registered
  // name with no caller passes the allowlist and then falls through to
  // "Unsupported action/resource combination", which is a WORSE failure than
  // not registering it -- the exact trap api/_resources/sairnlaw.js records for
  // law_deadline_rules. Scoped to the two registries written on 2026-09-09
  // rather than to every app, because the older ones predate the convention and
  // widening this is its own pass with its own evidence.
  const fs = require('fs');
  const path = require('path');
  const root = path.join(__dirname, '..', '..');
  // MATCHED AGAINST THE SYNC LIST, NOT AGAINST THE FILE TEXT. Both apps name
  // their resources with the localStorage key verbatim, so `src.includes(name)`
  // would pass on the storage key alone and prove nothing about whether the
  // backup is wired -- a green check over a resource nothing pushes, which is
  // the shape this test replaced.
  [['sairnvet', 'sairnvet.html', 'SV_SYNCED'],
   ['sairnfreedom', 'sairnfreedom.html', 'SF_SYNCED']].forEach(([app, file, listName]) => {
    const src = fs.readFileSync(path.join(root, file), 'utf8');
    const m = src.match(new RegExp('var ' + listName + '\\s*=\\s*\\[([^\\]]*)\\]'));
    assert.ok(m, file + ' has no ' + listName + ' -- the backup is not wired');
    const synced = (m[1].match(/'([a-z0-9_]+)'/g) || []).map((s) => s.slice(1, -1));
    const registered = reg.RESOURCE_NAMES_BY_APP[app];
    assert.ok(registered.length > 0, app + ' registry went empty');
    const unregistered = synced.filter((n) => !registered.includes(n));
    assert.deepStrictEqual(unregistered, [],
      listName + ' pushes names the registry does not allow (they 400 at the gate): '
      + unregistered.join(', '));
    const unpushed = registered.filter((n) => !synced.includes(n));
    assert.deepStrictEqual(unpushed, [],
      app + ' registers names ' + listName + ' never pushes -- these pass the '
      + 'allowlist and then fall through to "Unsupported action/resource '
      + 'combination", which is worse than not registering them: '
      + unpushed.join(', '));
    assert.ok(reg.isVisibleTo('shared_knowledge', app), app + ' cannot reach shared');
    assert.ok(!reg.isVisibleTo('law_matters', app), app + ' can reach another app');
  });
});

// ── through the REAL handler ───────────────────────────────────────────────
section('through the REAL sd-data handler');

function loadHandler() {
  delete require.cache[require.resolve(HANDLER)];
  return require(HANDLER);
}
async function call(handler, resource, appId, action) {
  const out = { code: null, body: null };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; },
                setHeader() {} };
  const envURL = process.env.SUPABASE_URL, envKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const realFetch = global.fetch;
  process.env.SUPABASE_URL = 'https://stub.invalid';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'stub-key';
  global.fetch = async () => ({ ok: true, status: 200, json: async () => [{ status: 'active', app_id: appId }] });
  try {
    await handler({ method: 'POST', headers: { authorization: 'Bearer k' },
                    body: { action: action || 'read', resource, payload: {} } }, res);
  } finally {
    global.fetch = realFetch;
    if (envURL === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = envURL;
    if (envKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = envKey;
  }
  return out;
}

test('THE THREE THE REVIEW FOUND ARE REFUSED for a stonedesk licence', async () => {
  const h = loadHandler();
  for (const r of ['law_matters', 'sc_denial', 'leg_cases']) {
    const out = await call(h, r, 'stonedesk');
    assert.strictEqual(out.code, 400, r + ' returned ' + out.code + ' -- the boundary is open');
  }
});

test('...and are INDISTINGUISHABLE from a name that does not exist', async () => {
  // The oracle. If these bodies ever differ, an authenticated caller can
  // classify every guessed name one request at a time again.
  const h = loadHandler();
  const invented = await call(h, '__no_such_resource__', 'stonedesk');
  for (const r of ['law_matters', 'sc_denial', 'leg_cases', 'dnt_patients', 'rf_jobs']) {
    const foreign = await call(h, r, 'stonedesk');
    assert.strictEqual(foreign.code, invented.code, r);
    assert.deepStrictEqual(foreign.body, invented.body, r + ' is distinguishable from an invented name');
  }
});

test('a licence still reaches its OWN resources and the shared ones', async () => {
  const h = loadHandler();
  for (const [r, app] of [['sd_crm', 'stonedesk'], ['profile', 'stonedesk'],
                          ['dnt_patients', 'sairndental'], ['shared_knowledge', 'sairnvet']]) {
    const out = await call(h, r, app);
    assert.notStrictEqual(out.code, 400,
      app + ' was refused its own ' + r + ': ' + JSON.stringify(out.body));
  }
});

test('an unattributable licence is NOT gated -- the documented fallback', async () => {
  const h = loadHandler();
  const out = await call(h, 'law_matters', null);
  assert.notStrictEqual(out.code, 400, 'the fallback direction changed: ' + JSON.stringify(out.body));
});

test('SAIRN_APP_BOUNDARY=off disables the boundary and NOTHING ELSE', async () => {
  const prev = process.env.SAIRN_APP_BOUNDARY;
  process.env.SAIRN_APP_BOUNDARY = 'off';
  try {
    const h = loadHandler();
    assert.notStrictEqual((await call(h, 'law_matters', 'stonedesk')).code, 400,
      'the override does not work -- an outage would have no escape hatch');
    // The unregistered check must survive the override.
    assert.strictEqual((await call(h, '__no_such_resource__', 'stonedesk')).code, 400,
      'the override also disabled the unregistered-resource check');
  } finally {
    if (prev === undefined) delete process.env.SAIRN_APP_BOUNDARY; else process.env.SAIRN_APP_BOUNDARY = prev;
  }
});

test('the override is OFF by default -- the gate is on unless someone says so', async () => {
  assert.ok(!process.env.SAIRN_APP_BOUNDARY, 'the environment has it set; this run proves nothing');
  const h = loadHandler();
  assert.strictEqual((await call(h, 'law_matters', 'stonedesk')).code, 400);
});

// ── the measurement, re-derived every run ──────────────────────────────────
section('no app makes a cross-app call on this endpoint');

test('every resource an app HTML asks sd-data for is its own or shared', () => {
  // THE PREMISE THE WHOLE GATE RESTS ON. Enforcing is only safe because nothing
  // legitimately crosses; a measurement taken once is a claim by tomorrow, so
  // this re-takes it.
  //
  // THE FIRST VERSION OF THIS ASSERTION MISSED THREE OF THE FOUR REALISTIC WAYS
  // A CROSS-APP CALL GETS WRITTEN, which the independent review proved by
  // injecting them: it only matched a literal `xData('verb','name')`, so a call
  // through `rfDataRaw(` or `hrCall(` -- helpers that do not contain "Data" --
  // and a name added to a SYNC ARRAY all passed while the suite printed green.
  // The helper name is now irrelevant, and array literals are read.
  //
  // `jobs` and `progress_photos` in stonedesk.html are not exceptions: they
  // POST to /api/sd-sub-data, a different endpoint with its own three-name
  // registry, confirmed by reading the fetch call rather than inferring.
  const SUB_DATA_ONLY = new Set(['jobs', 'progress_photos', 'roster']);
  const VERBS = "read|write|delete|route|evaluate|derive_charges|reconcile|assess_damage|" +
                "set_status|agreement_status|issue|add_payment|reconcile_claim|reserve|qc-review";
  const problems = [];
  let scanned = 0, callSites = 0;

  for (const f of fs.readdirSync(ROOT).filter((n) => n.endsWith('.html'))) {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
    if (src.indexOf('/api/sd-data') === -1) continue;
    const app = f.replace(/\.html$/, '').replace(/-.*$/, '');
    if (!reg.isKnownApp(app)) continue;
    scanned++;

    const asked = new Set();
    // 1. ANY helper, not just one whose name contains "Data": fn('verb','name')
    let m;
    const byVerb = new RegExp(String.raw`\w+\(\s*['"](?:` + VERBS + String.raw`)['"]\s*,\s*['"]([a-z0-9_]+)['"]`, 'g');
    while ((m = byVerb.exec(src)) !== null) asked.add(m[1]);
    // 2. fn(actionVariable, 'name')
    const byVar = /\w+\(\s*[A-Za-z_$][\w$]*\s*,\s*['"]([a-z0-9_]+)['"]/g;
    while ((m = byVar.exec(src)) !== null) asked.add(m[1]);
    // 3. an explicit envelope: resource:'name'
    const byField = /['"]?resource['"]?\s*:\s*['"]([a-z0-9_]+)['"]/g;
    while ((m = byField.exec(src)) !== null) asked.add(m[1]);
    // 4. SYNC / RESOURCE ARRAYS -- how five apps name their resources. The
    //    review added a foreign name to BLD_SYNCED and the old sweep missed it.
    const arrays = /(?:var|const|let)\s+\w*(?:SYNC\w*|RESOURCES?|RESOURCE_\w+)\s*=\s*\[([\s\S]{0,4000}?)\]/g;
    while ((m = arrays.exec(src)) !== null) {
      const names = m[1].match(/['"]([a-z0-9_]+)['"]/g) || [];
      names.forEach((n) => asked.add(n.slice(1, -1)));
    }

    for (const n of asked) {
      if (SUB_DATA_ONLY.has(n)) continue;
      const owner = reg.OWNER_BY_RESOURCE[n];
      if (!owner) continue;               // unregistered: already a 400
      callSites++;
      if (owner !== 'shared' && owner !== app) {
        problems.push(f + ' asks for ' + n + ', owned by ' + owner);
      }
    }
  }

  assert.ok(scanned >= 10, 'only scanned ' + scanned + ' app files');
  // NOT just a file count: the old version was satisfied by files that named
  // nothing. This requires the sweep to have actually resolved resource names.
  assert.ok(callSites >= 100,
    'only resolved ' + callSites + ' resource references -- the patterns stopped matching');
  assert.deepStrictEqual(problems, [],
    'A CROSS-APP CALL NOW EXISTS AND THE BOUNDARY WILL BREAK IT:' + problems.join('; '));
});

(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.fn(); console.log('  ok   ' + item.name); pass++; }
    catch (e) { console.log('  FAIL ' + item.name + '\n       ' + e.message); fail++; }
  }
  console.log('\napp-boundary: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
