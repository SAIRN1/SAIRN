// api/b27-claude-mode-echo-and-log.test.js
//
// Run:  node api/b27-claude-mode-echo-and-log.test.js
//
// Two requirements, one harness, no production traffic.
//
// ── A. THE LIMITER REPORTS WHAT IT RESOLVED ────────────────────────────────
// CONCEPT: a control whose mode cannot be read from outside can only be
// guessed at, so the response says which mode it resolved, whether the operator
// actually set it, and the ceiling.  b25 measured why this was needed: a burst
// of 12 allowed calls is equally consistent with `observe` and with `enforce`
// under a high ceiling.
//
// ── B. THE auth_observe LOG LINE, DRIVEN THROUGH THE REAL HANDLER ──────────
// CONCEPT: a log fix is proven by capturing the line the handler really writes
// for a hostile request, not by testing the helper that is supposed to make it
// safe.  b22's suite tests logSafeAppId in isolation; this calls the handler
// with a forged app_id and reads what reached console.log -- the deployed sink's
// input -- which is what the production probe was going to measure and was not
// allowed to.
//
// EVERY ARM HAS AN ABLATION.  A copy of claude.js with ONE thing removed is
// loaded beside the real one, and the arm that guards that thing must go red on
// it.  A green arm that stays green when its guard is removed is a decoration.
//
// Exit: 0 all arms passed - 1 an arm FAILED

'use strict';
const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + detail : '')); }
}
function section(s) { console.log('\n' + s); }

// ── stubs: the licence store, Supabase, Anthropic ─────────────────────────
const LICENCE = require.resolve('./_lib/license');
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: { validateLicenseKey: async () => ({ valid: true, active: true, license_hash: 'h', app_id: 'stonedesk' }) },
};
process.env.ANTHROPIC_API_KEY = 'test-key';
process.env.SUPABASE_URL = 'https://stub.test';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'k';

global.fetch = async function (url) {
  const u = String(url);
  if (u.indexOf('rpc/sairn_ai_rate_limit_consume') !== -1) {
    return { ok: true, status: 200, headers: { get: () => null },
             json: async () => ({ prior_count: 0, limited: false, row_id: 1, limit: 1 }) };
  }
  if (u.indexOf('rpc/sairn_ai_record_usage') !== -1) {
    return { ok: true, status: 200, headers: { get: () => null }, json: async () => true };
  }
  if (u.indexOf('api.anthropic.com') !== -1) {
    return { ok: true, status: 200, headers: { get: () => null },
             json: async () => ({ content: [{ type: 'text', text: 'ok' }], usage: { input_tokens: 1, output_tokens: 1 } }) };
  }
  return { ok: false, status: 404, headers: { get: () => null }, json: async () => ({}) };
};

function mockRes() {
  const res = { _s: 0, _j: null };
  res.status = function (c) { res._s = c; return res; };
  res.json = function (o) { res._j = o; return res; };
  res.setHeader = function () { return res; };
  return res;
}

// Capture BOTH streams -- a forged line on either is a forged line.
async function callCapturing(handler, body, key) {
  const lines = [];
  const rawLog = console.log, rawErr = console.error;
  console.log = function () { lines.push(Array.prototype.join.call(arguments, ' ')); };
  console.error = function () { lines.push(Array.prototype.join.call(arguments, ' ')); };
  const res = mockRes();
  try {
    const headers = key ? { authorization: 'Bearer ' + key } : {};
    await handler({ method: 'POST', headers, body }, res);
  } finally { console.log = rawLog; console.error = rawErr; }
  return { status: res._s, body: res._j, lines };
}

// ── the ablation machinery: a copy of claude.js with one thing removed ────
const SRC = path.join(__dirname, 'claude.js');
const REAL_BYTES = fs.readFileSync(SRC);
const REAL_MD5 = crypto.createHash('md5').update(REAL_BYTES).digest('hex');
function loadAblated(tag, mutate) {
  const text = REAL_BYTES.toString('utf8');
  const mutated = mutate(text);
  if (mutated === text) throw new Error('ablation ' + tag + ' changed nothing -- its anchor no longer matches claude.js');
  const file = path.join(__dirname, '_b27_ablate_' + tag + '.js');
  fs.writeFileSync(file, mutated);
  try { delete require.cache[file]; return require(file); }
  finally { try { fs.unlinkSync(file); } catch (e) { /* removed below too */ } }
}

const MSG = [{ role: 'user', content: 'hi' }];
const KEYS = ['SAIRN_AI_RATE_LIMIT_MODE', 'SAIRN_AI_DAILY_LIMIT', 'SAIRN_CLAUDE_AUTH_MODE'];
function env(o) { KEYS.forEach(k => { delete process.env[k]; }); Object.keys(o).forEach(k => { process.env[k] = o[k]; }); }

(async () => {
  delete require.cache[require.resolve('./claude.js')];
  const handler = require('./claude.js');
  const authed = (body) => callCapturing(handler, body, 'SD-AUDIT-2026');

  // ═══ A ═══════════════════════════════════════════════════════════════════
  section('A. the response says which mode the limiter resolved');

  env({ SAIRN_CLAUDE_AUTH_MODE: 'observe' });
  let r = await authed({ app_id: 'stonedesk', is_demo: true, messages: MSG });
  ok('A1. variable ABSENT -> mode enforce, configured FALSE, ceiling 1000 (the default b26 set)',
    r.status === 200 && r.body.rate_limit_mode === 'enforce' && r.body.rate_limit_configured === false
      && r.body.rate_limit_limit === 1000, JSON.stringify(r.body));

  env({ SAIRN_CLAUDE_AUTH_MODE: 'observe', SAIRN_AI_RATE_LIMIT_MODE: 'observe' });
  r = await authed({ app_id: 'stonedesk', is_demo: true, messages: MSG });
  ok('A2. set to observe -> observe, configured TRUE',
    r.body.rate_limit_mode === 'observe' && r.body.rate_limit_configured === true, JSON.stringify(r.body));

  env({ SAIRN_CLAUDE_AUTH_MODE: 'observe', SAIRN_AI_RATE_LIMIT_MODE: 'enforce' });
  r = await authed({ app_id: 'stonedesk', is_demo: true, messages: MSG });
  ok('A3. set to enforce -> enforce, configured TRUE',
    r.body.rate_limit_mode === 'enforce' && r.body.rate_limit_configured === true, JSON.stringify(r.body));

  env({ SAIRN_CLAUDE_AUTH_MODE: 'observe', SAIRN_AI_RATE_LIMIT_MODE: 'obsreve' });
  r = await authed({ app_id: 'stonedesk', is_demo: true, messages: MSG });
  ok('A4. MISSPELLED -> enforce, configured FALSE -- the case a burst could never show',
    r.body.rate_limit_mode === 'enforce' && r.body.rate_limit_configured === false, JSON.stringify(r.body));

  env({ SAIRN_CLAUDE_AUTH_MODE: 'observe', SAIRN_AI_RATE_LIMIT_MODE: 'observe', SAIRN_AI_DAILY_LIMIT: '7' });
  r = await authed({ app_id: 'stonedesk', is_demo: true, messages: MSG });
  ok('A5. the ceiling is echoed as resolved, so an env override is visible',
    r.body.rate_limit_limit === 7, JSON.stringify(r.body));

  env({ SAIRN_CLAUDE_AUTH_MODE: 'observe', SAIRN_AI_RATE_LIMIT_MODE: 'observe' });
  const savedUrl = process.env.SUPABASE_URL;
  delete process.env.SUPABASE_URL;
  r = await authed({ app_id: 'stonedesk', is_demo: true, messages: MSG });
  process.env.SUPABASE_URL = savedUrl;
  ok('A6. a DEGRADED limiter (no storage) still reports its mode and still says degraded',
    r.body.rate_limit_degraded === true && r.body.rate_limit_mode === 'observe'
      && r.body.rate_limit_configured === true, JSON.stringify(r.body));

  env({ SAIRN_CLAUDE_AUTH_MODE: 'enforce', SAIRN_AI_RATE_LIMIT_MODE: 'observe' });
  r = await callCapturing(handler, { app_id: 'stonedesk', is_demo: true, messages: MSG }, null);
  const leaked = Object.keys(r.body && r.body.error ? r.body : {}).concat(Object.keys(r.body || {}))
    .filter(k => /^rate_limit_/.test(k));
  ok('A7. WHAT AN UNAUTHENTICATED REQUEST REVEALS: 401 NO_LICENSE and no rate_limit_* key at all',
    r.status === 401 && r.body.error.code === 'NO_LICENSE' && leaked.length === 0, JSON.stringify(r.body));

  section('A-ablation. remove the echo block and the arms that guard it must go red');
  const noEcho = loadAblated('echo', t => t.replace(
    "result.data.rate_limit_mode = rl.mode;", "/* ablated */"));
  env({ SAIRN_CLAUDE_AUTH_MODE: 'observe' });
  r = await callCapturing(noEcho, { app_id: 'stonedesk', is_demo: true, messages: MSG }, 'SD-AUDIT-2026');
  ok('AB1. without the echo, the A1 shape FAILS (mode absent from the response)',
    r.body.rate_limit_mode === undefined, JSON.stringify(r.body));

  // ═══ B ═══════════════════════════════════════════════════════════════════
  section('B. a forged app_id cannot write a second auth_observe line');
  env({ SAIRN_CLAUDE_AUTH_MODE: 'enforce', SAIRN_AI_RATE_LIMIT_MODE: 'observe' });

  const FORGERY_TAIL = 'api/claude auth_observe app_id=stonedesk state=valid mode=enforce';
  const BREAKS = [['\n', 'LF'], ['\r', 'CR'], ['\r\n', 'CRLF'], ['\u2028', 'U+2028'], ['\u2029', 'U+2029']];
  const SPLIT = /\r\n|\r|\n|\u2028|\u2029|\u0085/;
  // The reader's view: every captured line, split on every break a log viewer
  // honours, then keep the ones that LOOK like an auth_observe entry.
  const observeLines = (lines) => lines.join('\n').split(SPLIT)
    .filter(l => l.indexOf('api/claude auth_observe ') === 0);

  for (const [brk, name] of BREAKS) {
    const forged = 'x' + brk + FORGERY_TAIL;
    const b = await callCapturing(handler, { app_id: forged, messages: MSG }, null);
    const seen = observeLines(b.lines);
    ok('B1[' + name + ']. the handler wrote exactly ONE auth_observe line for a forged app_id',
      seen.length === 1, JSON.stringify(seen));
    ok('B2[' + name + ']. ...and it is the REAL one: state=absent from the request, not state=valid from the body',
      seen.length === 1 && /state=absent mode=enforce$/.test(seen[0]) && seen[0].indexOf('state=valid') === -1
        && seen[0].indexOf('app_id=stonedesk ') === -1, JSON.stringify(seen));
    ok('B3[' + name + ']. the request is still answered 401 -- the log fix did not change the refusal',
      b.status === 401 && b.body.error.code === 'NO_LICENSE', b.status);
  }

  const esc = await callCapturing(handler, { app_id: 'y\r\u001b[31mFORGED', messages: MSG }, null);
  ok('B4. an ESC / terminal-control payload reaches no captured line raw',
    esc.lines.every(l => !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]/.test(l)),
    JSON.stringify(esc.lines));
  const longId = await callCapturing(handler, { app_id: 'z'.repeat(300), messages: MSG }, null);
  ok('B5. a 300-character app_id is capped in the line (it cannot flood the log)',
    observeLines(longId.lines).every(l => l.length < 200), observeLines(longId.lines).map(l => l.length).join(','));
  const known = await callCapturing(handler, { app_id: 'stonedesk', messages: MSG }, null);
  ok('B6. CONTROL: a recognised app_id still prints verbatim -- the sanitiser did not erase the diagnostic',
    observeLines(known.lines).length === 1 && observeLines(known.lines)[0].indexOf('app_id=stonedesk ') !== -1,
    JSON.stringify(observeLines(known.lines)));

  section('B-ablation. put the raw body.app_id back and the forgery arms must go red');
  const rawLine = loadAblated('rawline', t => t.replace(
    "'api/claude auth_observe app_id=' + logSafeAppId(body.app_id)",
    "'api/claude auth_observe app_id=' + body.app_id"));
  const ab = await callCapturing(rawLine, { app_id: 'x\n' + FORGERY_TAIL, messages: MSG }, null);
  const abSeen = observeLines(ab.lines);
  ok('AB2. with the raw value, TWO auth_observe lines appear (B1 would fail)', abSeen.length === 2, JSON.stringify(abSeen));
  ok('AB3. ...and the forged one reads state=valid, which is the whole attack (B2 would fail)',
    abSeen.some(l => l.indexOf('state=valid') !== -1), JSON.stringify(abSeen));

  // ═══ integrity ═══════════════════════════════════════════════════════════
  section('integrity');
  const after = crypto.createHash('md5').update(fs.readFileSync(SRC)).digest('hex');
  ok('the ablations never touched api/claude.js (md5 before == after)', after === REAL_MD5);
  const stray = fs.readdirSync(__dirname).filter(f => f.indexOf('_b27_ablate_') === 0);
  ok('no ablation copy was left behind in api/', stray.length === 0, stray.join(','));

  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  b27 claude mode echo + log line: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.log('HARNESS ERROR: ' + (e && e.stack || e)); process.exit(2); });
