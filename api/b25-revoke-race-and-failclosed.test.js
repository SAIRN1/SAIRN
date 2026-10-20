// api/b25-revoke-race-and-failclosed.test.js
//
// Run:  node api/b25-revoke-race-and-failclosed.test.js
//
// THREE DEFECTS THAT ALL REPORT SUCCESS: a revoke silently overwritten, a
// zero-row PATCH logged as a plan change, and two controls that permit when
// their setting is absent or misspelled.
//
// CONCEPTS, each stated before its fix (docs/2026-10-20-hank-b25-notes.md):
//   1. A registration must not RESURRECT a revoked agent: the not-revoked
//      condition travels IN THE SAME STATEMENT as the update, and a zero-row
//      result is a REFUSAL, never a success.
//   2. The webhook's log line must say what the WRITE DID, not what was ASKED
//      for -- a PATCH that matched no row changed nothing and is reported that
//      way.
//   3. A control whose setting is MISSING or MISSPELLED must refuse, not
//      permit. `observe` and `enforce` are the only two answers; anything else
//      is a configuration nobody made, and is treated as `enforce`.
//
// ── EVERY SECTION REPRODUCES BEFORE IT ASSERTS THE FIX ───────────────────
// Section A drives TWO CONCURRENT CALLS against a recorded PostgREST that
// revokes the row between the read and the write -- the real window -- and
// asserts the handler refuses. Section D then ABLATES the fix and requires
// the same arm to go red, so the reproduction is not a story about a
// condition that was never there.
//
// Exit: 0 all arms passed - 1 an arm FAILED - 3 an arm is UNPROVEN

'use strict';

process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const crypto = require('crypto');

const REGISTER_SRC = path.join(__dirname, 'agent', 'register.js');
const WEBHOOK_SRC = path.join(__dirname, 'agent', 'stripe-webhook.js');
const MODE_SRC = path.join(__dirname, '_lib', 'fail-closed-mode.js');
const LIMIT_SRC = path.join(__dirname, '_lib', 'ai-rate-limit.js');
const SELF = __filename;
const ARMS_ONLY = process.env.B25_ARMS_ONLY === '1';

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function is(cond, label, detail) { if (cond) ok(label); else bad(label, detail); }
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function eMsg(res) { return (res.body && res.body.error && res.body.error.message) || ''; }

const TOKEN = 'agent-token-placeholder-b25';
const TOKEN_HASH = crypto.createHash('sha256').update(TOKEN).digest('hex');

/**
 * A recorded PostgREST for sairn_agents.
 *
 * `opts.revokeAfterRead` -- THE RACE. The lookup answers `status: 'active'`,
 * and the row is flipped to 'revoked' the instant that read returns. So the
 * handler's own check sees a live agent and the write lands in a world where
 * it is revoked, which is exactly the window and cannot be reproduced by
 * stubbing one answer.
 */
function pgMock(calls, opts) {
  opts = opts || {};
  const row = { id: 'AG-1', customer_id: 'CUS-1', agent_name: 'probe',
                status: opts.status || 'active', plan_status: 'trialing',
                trial_ends_at: null };
  const state = { status: row.status };
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    calls.push({ url: u, method: method });
    if (method === 'GET' || !init) {
      const found = /token_hash=eq\./.test(u) && !opts.noRow;
      const answer = found ? [Object.assign({}, row, { status: state.status })] : [];
      if (opts.revokeAfterRead) state.status = 'revoked';
      return { ok: true, status: 200, json: async () => answer };
    }
    if (method === 'PATCH') {
      // THE CONDITION IS ENFORCED HERE, AS PostgREST WOULD. If the URL carries
      // `status=neq.revoked` and the row IS revoked, zero rows come back --
      // which is the whole property under test. If the URL does NOT carry it,
      // the write lands regardless, which is the pre-fix behaviour.
      const conditional = /status=neq\.revoked/.test(u);
      const blocked = conditional && state.status === 'revoked';
      if (opts.patchFails) {
        return { ok: false, status: 500, text: async () => 'boom',
                 json: async () => ({ message: 'boom' }) };
      }
      if (!blocked) state.status = 'active';
      const n = blocked ? 0 : 1;
      return { ok: true, status: 200,
               json: async () => (opts.patchNonArray ? { not: 'an array' }
                                                     : Array(n).fill(row)),
               text: async () => '' };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

function loadRegister(fetchImpl) {
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./agent/register.js')];
  return require('./agent/register.js');
}

async function callRegister(opts) {
  const calls = [];
  const h = loadRegister(pgMock(calls, opts));
  const res = mockRes();
  await h({ method: 'POST', headers: { authorization: 'Bearer ' + TOKEN } }, res);
  return { res: res, calls: calls };
}

// ── THE ABLATION HARNESS. Buffer in, buffer out: this repo has mixed line
// endings file by file, so a text round trip would rewrite every line and the
// restore would be a reformat.
function runSuite(armsOnly) {
  const env = armsOnly ? Object.assign({}, process.env, { B25_ARMS_ONLY: '1' })
                       : process.env;
  try {
    const out = execFileSync(process.execPath, [SELF], {
      env: env, encoding: 'utf8', stdio: 'pipe' });
    return { exit: 0, out: String(out || '') };
  } catch (e) {
    return { exit: typeof e.status === 'number' ? e.status : -1,
             out: String((e && e.stdout) || '') + String((e && e.stderr) || '') };
  }
}
function failedArms(out) {
  const m = String(out || '').match(/FAILED:\s*(.+)/);
  return m ? m[1].trim().split(/\s*,\s*/).filter(Boolean) : [];
}
function ablate(file, find, replace) {
  const buf = fs.readFileSync(file);
  const src = buf.toString('utf8');
  let needle = find, repl = replace, hits = src.split(find).length - 1;
  if (hits !== 1) {
    const crlf = find.replace(/\n/g, '\r\n');
    if (src.split(crlf).length - 1 === 1) {
      needle = crlf; repl = replace.replace(/\n/g, '\r\n'); hits = 1;
    }
  }
  if (hits !== 1) {
    return { ok: false, why: 'the ablation anchor matched ' + hits + ' time(s) '
      + 'in ' + path.basename(file) + ', not exactly 1 -- REFUSING to mutate. '
      + 'FIX THE ANCHOR, do not delete the arm. Anchor: ' + find.slice(0, 100) };
  }
  try {
    fs.writeFileSync(file, Buffer.from(src.replace(needle, repl), 'utf8'));
    const mine = runSuite(true);
    return { ok: true, exit: mine.exit, arms: failedArms(mine.out) };
  } finally {
    fs.writeFileSync(file, buf);
  }
}

(async () => {
  console.log('b25 revoke race / zero-row PATCH / fail-closed settings'
            + (ARMS_ONLY ? '  [ARMS ONLY]' : '') + '\n');

  // ══ A. THE REVOKE WINDOW ════════════════════════════════════════════════
  section('A. api/agent/register.js -- a revoke inside the read-then-write window');

  const a1 = await callRegister({ revokeAfterRead: true });
  is(a1.res.statusCode === 403 && /revoked/i.test(eMsg(a1.res)),
     'A1. THE RACE: the lookup sees an ACTIVE agent, the row is revoked the '
   + 'instant that read returns, and the registration is REFUSED 403. Before '
   + 'the fix the write had an id-only filter and answered ok:true, having '
   + 'overwritten the revoke with "active"',
     a1.res.statusCode + ' ' + eMsg(a1.res));

  const patchUrl = (a1.calls.filter((c) => c.method === 'PATCH')[0] || {}).url || '';
  is(/status=neq\.revoked/.test(patchUrl),
     'A2. ...and the condition is IN THE WRITE, not in a second read. One '
   + 'statement, so there is no window between checking and acting',
     patchUrl.slice(-90));

  const a3 = await callRegister({ revokeAfterRead: true });
  const patchCount = a3.calls.filter((c) => c.method === 'PATCH').length;
  is(patchCount === 1,
     'A3b. exactly ONE write is attempted -- the handler does not retry into '
   + 'the race it just lost',
     'PATCH calls: ' + patchCount);

  const a4 = await callRegister({});
  is(a4.res.statusCode === 200 && a4.res.body && a4.res.body.ok === true,
     'A4. THE CLEAN CONTROL: with no revoke in the window a normal '
   + 'registration still succeeds 200 ok:true. Without this, A1 is equally '
   + 'consistent with "registration is broken"',
     a4.res.statusCode + ' ' + JSON.stringify(a4.res.body && a4.res.body.ok));

  const a5 = await callRegister({ status: 'revoked' });
  is(a5.res.statusCode === 403,
     'A5. the ORDINARY refusal -- already revoked at read time -- still '
   + 'answers 403 with the SAME message, so a caller cannot tell the race '
   + 'from the plain case and try to win it',
     a5.res.statusCode + ' ' + eMsg(a5.res));
  is(a5.calls.filter((c) => c.method === 'PATCH').length === 0,
     'A5b. ...and that path attempts NO write at all',
     'PATCH calls: ' + a5.calls.filter((c) => c.method === 'PATCH').length);

  const a6 = await callRegister({ patchNonArray: true });
  is(a6.res.statusCode === 403,
     'A6. A NON-ARRAY BODY IS A REFUSAL. "Could not tell whether the row was '
   + 'updated" is a third state and is never folded into ok:true',
     a6.res.statusCode + ' ' + eMsg(a6.res));

  const a7 = await callRegister({ patchFails: true });
  is(a7.res.statusCode === 502,
     'A7. and an upstream FAILURE is still 502, distinct from the 403 -- a '
   + 'broken data store and a revoked agent are different answers',
     a7.res.statusCode);

  // TWO CONCURRENT CALLS, which is the shape the dispatch asked for. Both
  // enter with an active row; the first write flips it; the mock's row is
  // shared, so the second sees what the first left behind.
  {
    const calls = [];
    const f = pgMock(calls, {});
    const h = loadRegister(f);
    const r1 = mockRes(), r2 = mockRes();
    await Promise.all([
      h({ method: 'POST', headers: { authorization: 'Bearer ' + TOKEN } }, r1),
      h({ method: 'POST', headers: { authorization: 'Bearer ' + TOKEN } }, r2)
    ]);
    is(r1.statusCode === 200 && r2.statusCode === 200,
       'A8. TWO CONCURRENT registrations of a live agent both succeed -- the '
     + 'new condition is `neq.revoked`, not a single-use lock, and two honest '
     + 'registrations are not a conflict',
       r1.statusCode + ' / ' + r2.statusCode);
  }

  // ══ B. THE ZERO-ROW PATCH ═══════════════════════════════════════════════
  section('B. api/agent/stripe-webhook.js -- a PATCH that changed nothing');

  const whSrc = fs.readFileSync(WEBHOOK_SRC, 'utf8');
  const fnAt = whSrc.indexOf('async function setPlanStatus(');
  const fnBody = fnAt < 0 ? '' : whSrc.slice(fnAt, whSrc.indexOf('\n}', fnAt) + 2);
  const code = fnBody.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');

  is(fnAt > 0 && /return=representation/.test(code),
     'B1. setPlanStatus asks for `return=representation`, so the row count is '
   + 'READABLE. With `return=minimal` PostgREST answers 204 for one row and '
   + 'for none, and the function cannot tell them apart -- which was the '
   + 'defect, not an implementation detail',
     'representation present: ' + /return=representation/.test(code));

  is(/rows\.length === 0/.test(code) && /NO AGENT ROW MATCHED/.test(code),
     'B2. a ZERO-ROW result is detected and logged as NO AGENT ROW MATCHED, '
   + 'saying plan_status was NOT set. The old line said `plan_status set to '
   + '"paid"` for a row that does not exist, and that log line is the only '
   + 'record this endpoint leaves',
     'zero-row branch present');

  is(/console\.error/.test(code) && /console\.log/.test(code),
     'B3. the two outcomes go to DIFFERENT streams -- a real change to '
   + 'console.log, nothing-changed and could-not-tell to console.error -- so '
   + 'a log search for failures finds them',
     'both streams used');

  is(/row\(s\) changed/.test(code),
     'B4. and the SUCCESS line now carries the row count, so "it worked" and '
   + '"it worked on one row" are the same sentence rather than two readings',
     'count in the success line');

  is(!/throw new Error\([^)]*rows\.length/.test(code),
     'B5. a zero-row match does NOT throw. Throwing would make Stripe retry '
   + 'an event that can never succeed, forever -- the distinction needed is '
   + 'between did-it and did-nothing, and both are normal for a webhook whose '
   + 'payload names a row this database may not have',
     'no throw on the zero-row path');

  // ══ C. THE SETTINGS THAT DEFAULTED PERMISSIVE ═══════════════════════════
  section('C. api/_lib/fail-closed-mode.js -- absent and misspelled now ENFORCE');

  const mode = require('./_lib/fail-closed-mode');
  const cases = [
    ['observe', 'observe', true], ['OBSERVE', 'observe', true],
    ['  enforce  ', 'enforce', true],
    [undefined, 'enforce', false], [null, 'enforce', false],
    ['', 'enforce', false], ['   ', 'enforce', false],
    ['enforcs', 'enforce', false], ['off', 'enforce', false],
    ['true', 'enforce', false], ['observ', 'enforce', false]
  ];
  let allRight = true;
  const wrong = [];
  cases.forEach(([raw, wantMode, wantCfg]) => {
    const r = mode.resolveMode('X', raw);
    if (r.mode !== wantMode || r.configured !== wantCfg) {
      allRight = false;
      wrong.push(JSON.stringify(raw) + ' -> ' + r.mode + '/' + r.configured);
    }
  });
  is(allRight,
     'C1. eleven spellings resolve correctly: only the exact words observe and '
   + 'enforce are CONFIGURED; absent, empty, whitespace and four plausible '
   + 'typos all resolve to ENFORCE with configured:false',
     wrong.join('; '));

  is(mode.resolveMode('X', undefined).reason
     && /NOT SET/.test(mode.resolveMode('X', undefined).reason)
     && /enforcs/.test(mode.resolveMode('X', 'enforcs').reason),
     'C2. ...and each unconfigured answer carries a REASON naming the variable '
   + 'and quoting what it actually held. A control that silently HARDENED is '
   + 'as hard to operate as one that silently relaxed',
     mode.resolveMode('X', 'enforcs').reason);

  is(mode.resolveMode('X', 'observe').configured === true
     && mode.resolveMode('X', 'observe').reason === null,
     'C3. THE NEGATIVE CONTROL: a deliberate `observe` is configured and '
   + 'carries no reason, so C1 is not just "everything enforces"',
     'observe stays observe');

  // ── COMMENTS STRIPPED, AND C4/C5 FAILED ON A CORRECT FILE WITHOUT IT ────
  // Both arms assert an ABSENCE -- that the old `|| 'observe'` default is gone
  // -- and both fixes QUOTE the old line in the comment explaining them. So the
  // negation read the prose about the code and reported the fix as missing.
  // Same class as b24's D2, caught here within the hour rather than by an
  // ablation. Whole comment lines only; stated because a `//` inside a string
  // literal would be stripped too, and there is none in these files' code.
  const codeOnly = (p) => fs.readFileSync(p, 'utf8').split('\n')
    .filter((l) => !l.trim().startsWith('//') && !l.trim().startsWith('*'))
    .join('\n');

  const claudeSrc = codeOnly(path.join(__dirname, 'claude.js'));
  is(/failClosedMode\.resolveMode\(/.test(claudeSrc)
     && /'SAIRN_CLAUDE_AUTH_MODE'/.test(claudeSrc)
     && !/SAIRN_CLAUDE_AUTH_MODE \|\| 'observe'/.test(claudeSrc),
     'C4. api/claude.js resolves SAIRN_CLAUDE_AUTH_MODE through the shared rule '
   + 'and the old `|| \'observe\'` default is GONE FROM THE CODE',
     'old default still in code: '
     + /SAIRN_CLAUDE_AUTH_MODE \|\| 'observe'/.test(claudeSrc));

  const limitSrc = codeOnly(LIMIT_SRC);
  is(/failClosedMode\.isEnforcing\(/.test(limitSrc)
     && !/SAIRN_AI_RATE_LIMIT_MODE \|\| ''/.test(limitSrc),
     'C5. api/_lib/ai-rate-limit.js does the same, so the two controls cannot '
   + 'drift into disagreeing about what an unset flag means',
     'old default still in code: '
     + /SAIRN_AI_RATE_LIMIT_MODE \|\| ''/.test(limitSrc));

  delete require.cache[require.resolve('./_lib/ai-rate-limit')];
  const savedMode = process.env.SAIRN_AI_RATE_LIMIT_MODE;
  delete process.env.SAIRN_AI_RATE_LIMIT_MODE;
  const rl = require('./_lib/ai-rate-limit');
  is(rl.isEnforcing() === true,
     'C6. DRIVEN, not read: with SAIRN_AI_RATE_LIMIT_MODE deleted the limiter '
   + 'reports ENFORCING. This is the arm that would catch the default being '
   + 'put back',
     'isEnforcing()=' + rl.isEnforcing());
  process.env.SAIRN_AI_RATE_LIMIT_MODE = 'observe';
  is(rl.isEnforcing() === false,
     'C7. ...and a deliberate `observe` still does NOT enforce, so C6 is not '
   + '"it always enforces"',
     'isEnforcing()=' + rl.isEnforcing());
  if (savedMode === undefined) delete process.env.SAIRN_AI_RATE_LIMIT_MODE;
  else process.env.SAIRN_AI_RATE_LIMIT_MODE = savedMode;

  // THIS ONE DELIBERATELY READS THE COMMENTS, because what it asserts IS the
  // prose: that the file records the distinction between a configuration
  // failure and a measurement one. C4/C5 strip comments because they assert
  // code; this asserts documentation, and says so.
  is(/CONFIGURATION AXIS ONLY|measurement failure, not a configuration one/i
       .test(fs.readFileSync(LIMIT_SRC, 'utf8')),
     'C8. and the file says the DEGRADED axis is untouched -- "I could not '
   + 'reach the counter" still fails open, because enforcing a limit nobody '
   + 'could count is the worst of both worlds',
     'axis distinction stated');

  if (ARMS_ONLY) {
    console.log('\n  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
    if (failed.length) console.log('  FAILED: ' + failed.join(', '));
    if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
    process.exit(fail ? 1 : (unproven ? 3 : 0));
  }

  // ══ D. THE ABLATIONS ════════════════════════════════════════════════════
  section('D. ABLATIONS -- remove ONE layer and measure what it alone catches');

  const d0 = runSuite(true);
  is(d0.exit === 0,
     'D0. THE CONTROL: with nothing ablated the arms-only child run is GREEN. '
   + 'Every ablation below is measured against this',
     'child exit ' + d0.exit + '\n' + String(d0.out).slice(-300));

  const d1 = ablate(REGISTER_SRC,
    "        + '&status=neq.revoked',",
    "        ,");
  if (!d1.ok) cannot('D1. the write condition is load-bearing', d1.why);
  else {
    is(d1.exit === 1 && d1.arms.indexOf('A1') !== -1 && d1.arms.indexOf('A2') !== -1,
       'D1. removing `&status=neq.revoked` from the WRITE makes A1 and A2 FAIL '
     + '-- the pre-fix behaviour reproduced on purpose: the revoke is silently '
     + 'overwritten and the caller is told ok:true',
       'exit ' + d1.exit + ' arms=' + d1.arms.join(','));
    is(d1.arms.indexOf('A4') === -1 && d1.arms.indexOf('A5') === -1,
       'D1b. ...and A4/A5 stay GREEN, so one condition was removed and not the '
     + 'handler',
       'arms=' + d1.arms.join(','));
  }

  const d2 = ablate(REGISTER_SRC,
    "    if (!Array.isArray(updated) || updated.length === 0) {",
    "    if (false) {");
  if (!d2.ok) cannot('D2. the zero-row refusal is load-bearing', d2.why);
  else {
    is(d2.exit === 1 && d2.arms.indexOf('A1') !== -1,
       'D2. and removing only the ZERO-ROW CHECK -- leaving the condition in '
     + 'the URL -- still makes A1 FAIL. So the database half and the handler '
     + 'half are BOTH required: the condition without the check is a guard '
     + 'nothing can read',
       'exit ' + d2.exit + ' arms=' + d2.arms.join(','));
    is(d2.arms.indexOf('A6') !== -1,
       'D2b. ...and A6 goes red with it, which is the could-not-tell case '
     + 'falling back into ok:true',
       'arms=' + d2.arms.join(','));
  }

  const d3 = ablate(MODE_SRC,
    "  return {\n    mode: ENFORCE,\n    configured: false,",
    "  return {\n    mode: OBSERVE,\n    configured: false,");
  if (!d3.ok) cannot('D3. the fail-closed default is load-bearing', d3.why);
  else {
    is(d3.exit === 1 && d3.arms.indexOf('C1') !== -1 && d3.arms.indexOf('C6') !== -1,
       'D3. flipping the unconfigured answer back to `observe` makes C1 and C6 '
     + 'FAIL -- C6 drives the real limiter, so this is the old permissive '
     + 'default reproduced and caught',
       'exit ' + d3.exit + ' arms=' + d3.arms.join(','));
    is(d3.arms.indexOf('C3') === -1 && d3.arms.indexOf('C7') === -1,
       'D3b. ...and C3/C7 stay GREEN, so a deliberate `observe` is unaffected',
       'arms=' + d3.arms.join(','));
  }

  const d4 = ablate(WEBHOOK_SRC,
    "    headers: { ...headers, Prefer: 'return=representation' },",
    "    headers: { ...headers, Prefer: 'return=minimal' },");
  if (!d4.ok) cannot('D4. the readable row count is load-bearing', d4.why);
  else {
    is(d4.exit === 1 && d4.arms.indexOf('B1') !== -1,
       'D4. putting `return=minimal` back makes B1 FAIL -- the row count stops '
     + 'being readable and the zero-row branch becomes unreachable',
       'exit ' + d4.exit + ' arms=' + d4.arms.join(','));
  }

  console.log('\n  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log('  FAILED: ' + failed.join(', '));
  if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => {
  console.error('\n  HARNESS ERROR -- the suite did not finish, which is NOT a '
    + 'pass:\n', e);
  process.exit(1);
});
