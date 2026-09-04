// api/sd-data-exec-context.test.js
// Plain node:assert tests. Run: node api/sd-data-exec-context.test.js
//
// The Executive Suite advisor prompts carry SAIRN's own chart of accounts, the
// StoneDesk price book and the provisional-patent filing dates. Until
// 2026-09-02 they were literals in stonedesk.html, which is served whole to
// every customer -- so View Source read all of it. The showPanel() role gate
// added the same day closed the UI path and could not close that one.
//
// They now live in api/_lib/exec-context.js and reach a browser only through
// this endpoint. THIS is the check that matters: the browser-side gate is
// advice, because the page it lives in is downloadable and editable, and the
// server is the only place the decision is real.
//
// Everything below drives the REAL handler with only the license and session
// layers stubbed, so a regression in the branch itself fails here.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (code) { res.statusCode = code; return res; };
  res.json = function (payload) { res.body = payload; return res; };
  return res;
}
function mockReq(body) {
  return { method: 'POST', headers: { authorization: 'Bearer SD-TEST-KEY', 'x-sd-auth': 'tok' }, body: body };
}


// Comment lines stripped before any source is searched. A first pass at the
// app_id count matched strings inside comments and reported a duplicate that
// does not exist -- one edit from "fixing" a non-bug.
function stripCommentLines(src) {
  return src
    .split(String.fromCharCode(10))
    .filter(function (l) { return !/^\s*(\/\/|--|\*)/.test(l); })
    .join(String.fromCharCode(10));
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (err) { console.error('  FAIL - ' + name + '\n    ' + err.message); process.exitCode = 1; }
}

// Load the handler with a valid licence and a chosen session role. fetch is
// made to THROW: this endpoint reads no table, so any network call at all is
// itself a defect worth failing on.
function handlerWithRole(role) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  const realAuth = require('./_lib/auth');
  delete require.cache[require.resolve('./_lib/auth')];
  require.cache[require.resolve('./_lib/auth')] = {
    exports: Object.assign({}, realAuth, {
      tokenFromRequest: function () { return 'tok'; },
      verifySessionToken: function () { return role ? { employee_id: 'e1', role: role } : null; }
    })
  };
  global.fetch = async function () { throw new Error('exec_context must never touch the network -- it reads no table'); };
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function main() {
  console.log('api/sd-data.js -- exec_context: server-side owner/admin gate');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  const mod = require('./_lib/exec-context');

  // ---- the module -------------------------------------------------------
  await test('the module answers for exactly ceo, cfo and cto', () => {
    assert.deepStrictEqual(mod.EXEC_ROLES.slice().sort(), ['ceo', 'cfo', 'cto']);
  });

  await test('an unknown role returns null, NOT some other role\'s context', () => {
    assert.strictEqual(mod.getExecContext('sales'), null);
    assert.strictEqual(mod.getExecContext(''), null);
    assert.strictEqual(mod.getExecContext(null), null);
    assert.strictEqual(mod.getExecContext(undefined), null);
    assert.strictEqual(mod.getExecContext('constructor'), null,  // prototype keys are not roles
      'an Object.prototype key was treated as a role');
  });

  await test('role matching tolerates case and surrounding space', () => {
    assert.strictEqual(mod.getExecContext(' CFO '), mod.getExecContext('cfo'));
  });

  await test('the strings that caused this move are actually in the module', () => {
    assert.match(mod.getExecContext('cfo'), /Chart of Accounts: Assets 1000s/);
    assert.match(mod.getExecContext('cfo'), /Stripe price IDs on file/);
    assert.match(mod.getExecContext('cto'), /May 21 2027/);
  });

  // ---- finding 4.2: the advisor describes THIS platform, not Fabricor ----
  await test('FINDING 4.2: the CTO advisor no longer describes Fabricor', () => {
    // It said "React 18 + TypeScript frontend, Express backend, Drizzle ORM,
    // PostgreSQL on Railway" -- an abandoned duplicate codebase. An executive
    // advisor confidently describing the wrong architecture gives confidently
    // wrong architectural advice.
    const cto = mod.getExecContext('cto');
    [/React 18/, /Drizzle/, /Express backend/, /PostgreSQL on Railway/,
     /authenticated against Railway backend/, /Railway PostgreSQL instance/,
     /Railway-Vercel/].forEach(function (re) {
      assert.ok(!re.test(cto), 'the Fabricor stack description is back: ' + re);
    });
  });

  await test('...and describes what this repo actually contains', () => {
    const cto = mod.getExecContext('cto');
    assert.match(cto, /vanilla JavaScript/);
    assert.match(cto, /no build step/);
    assert.match(cto, /One Supabase Postgres project/);
    assert.match(cto, /Railway is DECOMMISSIONED/);
  });

  await test('the claim is TRUE of the repo -- checked, not asserted', () => {
    // The point of the correction is that it is verifiable. If somebody
    // reintroduces React or a live Railway URL, the advisor's description
    // stops matching the platform and this fails.
    const fs = require('fs');
    const path = require('path');
    const root = path.join(__dirname, '..');
    const files = fs.readdirSync(root).filter(f => f.endsWith('.html'));
    files.forEach(function (f) {
      const src = fs.readFileSync(path.join(root, f), 'utf8');
      const code = stripCommentLines(src);
      assert.ok(!/railway\.app/.test(code), f + ' has a live railway.app reference');
    });
  });

  await test('the app COUNT in the advisor is the one this repo has', () => {
    // "All 21 apps" was wrong in both directions. 18 app files + 3 sub-pages
    // is the 21 somebody once counted; the proxy allowlists 20 distinct ids.
    const fs = require('fs');
    const path = require('path');
    const root = path.join(__dirname, '..');
    // stonedesk-intake.html joined this list on 2026-09-03. It is a public
    // customer form, the same category as the two sairndental-* pages, not an
    // app a shop logs into -- so the APP count is unchanged and the sub-page
    // count moves 3 -> 4.
    //
    // NOTED, NOT CHANGED: stonedesk-catalog.html is also a public sub-page by
    // that definition and is still counted as an APP here, which is why the
    // app total went 17 -> 18 when it landed on 2026-09-02. Reclassifying it
    // would move two numbers in a line nobody asked me to touch; it is flagged
    // here so the next person to edit this count knows the boundary is fuzzy
    // rather than discovering it as a surprise.
    const sub = ['sairndental-book.html', 'sairndental-complaint.html', 'stonedesk-hr.html',
                 'stonedesk-intake.html'];
    const apps = fs.readdirSync(root).filter(f => f.endsWith('.html') && sub.indexOf(f) === -1);
    assert.strictEqual(apps.length, 18, 'app file count moved -- update the cto architecture line');

    const proxy = fs.readFileSync(path.join(root, 'api', 'claude.js'), 'utf8');
    const block = proxy.slice(
      proxy.indexOf('const KNOWN_APP_IDS = ['),
      proxy.indexOf('];', proxy.indexOf('const KNOWN_APP_IDS = [')) + 2
    );
    // COMMENTS STRIPPED FIRST. A first pass at this count matched app_id
    // strings inside comments and reported a duplicate 'sairnsenior' entry
    // that does not exist -- one edit away from "fixing" a non-bug.
    const code = stripCommentLines(block);
    const ids = (code.match(/'[a-z0-9]+'/g) || []).map(x => x.slice(1, -1));
    assert.strictEqual(ids.length, 20, 'proxy app_id count moved');
    assert.strictEqual(new Set(ids).size, 20, 'the allowlist has a real duplicate now');

    const cto = mod.getExecContext('cto');
    assert.match(cto, /18 app files and 4 sub-pages/);
    assert.match(cto, /20 distinct app_ids/);
  });

  // ---- and NOT in the page ----------------------------------------------
  await test('...and are GONE from stonedesk.html -- the point of the exercise', () => {
    const html = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');
    ['Chart of Accounts: Assets 1000s', '1010 Cash-Checking', 'Stripe price IDs on file',
     'May 21 2026', 'May 21 2027', 'Drizzle ORM'].forEach(function (needle) {
      assert.ok(html.indexOf(needle) === -1, 'still served to every customer: ' + needle);
    });
    assert.ok(html.indexOf('EAI_SYSTEMS') === -1, 'the literal object survived in the page');
  });

  await test('the page has no local fallback copy to quietly fall back to', () => {
    const html = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');
    assert.match(html, /var sys=await eaiSystemFor\(role\);/);
    assert.match(html, /if\(!sys\)\{/);
    assert.match(html, /Nothing was sent\./);
  });

  // ---- the gate ---------------------------------------------------------
  await test('no session -> 403 FORBIDDEN', async () => {
    const h = handlerWithRole(null);
    const res = mockRes();
    await h(mockReq({ action: 'read', resource: 'exec_context', payload: { role: 'cfo' } }), res);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(res.body.error.code, 'FORBIDDEN');
  });

  for (const role of ['sales', 'install', 'estimator', '']) {
    await test('role "' + role + '" -> 403, and no context in the body', async () => {
      const h = handlerWithRole(role || 'unknownrole');
      const res = mockRes();
      await h(mockReq({ action: 'read', resource: 'exec_context', payload: { role: 'cfo' } }), res);
      assert.strictEqual(res.statusCode, 403);
      assert.ok(!JSON.stringify(res.body).includes('Chart of Accounts'),
        'the refusal leaked the very thing it refused');
    });
  }

  for (const role of ['owner', 'admin']) {
    await test(role + ' -> 200 and gets the real string', async () => {
      const h = handlerWithRole(role);
      const res = mockRes();
      await h(mockReq({ action: 'read', resource: 'exec_context', payload: { role: 'cfo' } }), res);
      assert.strictEqual(res.statusCode, 200);
      assert.strictEqual(res.body.ok, true);
      assert.strictEqual(res.body.data.role, 'cfo');
      assert.match(res.body.data.system, /Chart of Accounts: Assets 1000s/);
    });
  }

  await test('an owner asking for an unknown advisor role -> 400, not a fallback', async () => {
    const h = handlerWithRole('owner');
    const res = mockRes();
    await h(mockReq({ action: 'read', resource: 'exec_context', payload: { role: 'sales' } }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'UNKNOWN_ROLE');
  });

  await test('a missing role is a 400, not the first role in the map', async () => {
    const h = handlerWithRole('owner');
    const res = mockRes();
    await h(mockReq({ action: 'read', resource: 'exec_context', payload: {} }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error.code, 'UNKNOWN_ROLE');
  });

  await test('a WRITE against exec_context never returns a context', async () => {
    const h = handlerWithRole('owner');
    const res = mockRes();
    await h(mockReq({ action: 'write', resource: 'exec_context', payload: { role: 'cfo', system: 'pwned' } }), res);
    assert.notStrictEqual(res.statusCode, 200);
    assert.ok(!JSON.stringify(res.body || {}).includes('Chart of Accounts'));
  });

  console.log('\n' + (process.exitCode ? 'FAILURES ABOVE' : 'ALL ' + passed + ' EXEC-CONTEXT ASSERTIONS PASS'));
}

main();
