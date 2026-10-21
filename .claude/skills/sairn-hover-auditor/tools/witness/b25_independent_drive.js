'use strict';
/*
 * b25_independent_drive.js -- H1's OWN drive of hank's b25 fixes (#1619, #1617,
 * #1622), run against the PRE-FIX tree and the POST-FIX tree and compared.
 * Built H1 b74, item 3.
 *
 *   node b25_independent_drive.js <tree-root>        (tree-root contains api/)
 *   node b25_independent_drive.js --compare <pre-root> <post-root>
 *
 * WHY THIS EXISTS WHEN hank's suite is green. api/b25-revoke-race-and-failclosed
 * .test.js is the fix's own author's evidence. It passes 30/30 and I re-ran it,
 * and that proves the suite and the fix agree -- which they would if both shared
 * one misreading. This file asks the same three questions with a different
 * store (pgrest_emulator.js, no shared code), different scenarios, and the one
 * comparison the author's suite cannot make: the SAME scenario against the code
 * as it was BEFORE the fix. A fix is shown by a state that differs between the
 * two trees, not by a green run on one of them.
 *
 * THE OBSERVABLE IS THE STORE'S FINAL STATE, never only the handler's answer.
 * The defect in #1619 and #1617 was a handler that SAID success; asserting on
 * what it said would repeat the defect.
 *
 * INDEPENDENT ABLATIONS (R6-R8). The post-fix register.js is mutated in memory,
 * one clause at a time, and the same race is replayed -- to show which symptom
 * each clause alone prevents, from a mutation I made, not from the author's.
 */
const path = require('path');
const crypto = require('crypto');
const Module = require('module');
const { Emulator, mockRes, capture } = require('./pgrest_emulator');

const TOKEN = 'h1-b74-token';
const TOKEN_HASH = crypto.createHash('sha256').update(TOKEN).digest('hex');
const SECRET = 'whsec_h1_b74';

function setEnv() {
  process.env.SUPABASE_URL = 'https://emu.invalid';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'h1-b74-service-key';
  process.env.STRIPE_WEBHOOK_SECRET = SECRET;
}

function loadFresh(file, transform) {
  // Load a module from disk, optionally transforming its SOURCE first (the
  // ablations), with a private cache so one scenario cannot leak into the next.
  const fs = require('fs');
  let src = fs.readFileSync(file, 'utf8');
  if (transform) src = transform(src);
  const m = new Module(file, null);
  m.filename = file;
  m.paths = Module._nodeModulePaths(path.dirname(file));
  m._compile(src, file);
  return m.exports;
}

/** Remove // and block comments, leaving string / template / regex-free code
 *  text intact enough for a presence test. A small state machine, not a parser:
 *  it tracks the three string delimiters so a "//" inside a URL string survives. */
function stripJsComments(src) {
  let out = '', i = 0, q = null;
  while (i < src.length) {
    const c = src[i], n = src[i + 1];
    if (q) {
      out += c;
      if (c === '\\') { out += n === undefined ? '' : n; i += 2; continue; }
      if (c === q) q = null;
      i++; continue;
    }
    if (c === '"' || c === "'" || c === '`') { q = c; out += c; i++; continue; }
    if (c === '/' && n === '/') { while (i < src.length && src[i] !== '\n') i++; continue; }
    if (c === '/' && n === '*') { i += 2; while (i < src.length && !(src[i] === '*' && src[i + 1] === '/')) i++; i += 2; continue; }
    out += c; i++;
  }
  return out;
}

function agentRow(over) {
  return Object.assign({ id: 'AG-1', token_hash: TOKEN_HASH, status: 'pending', customer_id: 'C-1',
    agent_name: 'h1-agent', plan_status: 'trial', trial_ends_at: null, last_seen_at: null }, over || {});
}

async function register(root, db, transform) {
  const handler = loadFresh(path.join(root, 'api', 'agent', 'register.js'), transform);
  global.fetch = db.fetch;
  const req = { method: 'POST', headers: { authorization: 'Bearer ' + TOKEN } };
  const res = mockRes();
  const cap = await capture(() => handler(req, res));
  return { status: res.statusCode, ok: !!(res.body && res.body.ok), error: res.body && res.body.error && res.body.error.message, lines: cap.lines };
}

function patches(db) { return db.log.filter((e) => e.method === 'PATCH'); }

async function webhook(root, db, event) {
  const handler = loadFresh(path.join(root, 'api', 'agent', 'stripe-webhook.js'));
  global.fetch = db.fetch;
  const raw = JSON.stringify(event);
  const t = Math.floor(Date.now() / 1000);
  const sig = crypto.createHmac('sha256', SECRET).update(t + '.' + raw).digest('hex');
  const EventEmitter = require('events');
  const req = new EventEmitter();
  req.method = 'POST';
  req.headers = { 'stripe-signature': 't=' + t + ',v1=' + sig };
  const res = mockRes();
  const p = handler(req, res);
  setImmediate(() => { req.emit('data', raw); req.emit('end'); });
  const cap = await capture(() => p);
  return { status: res.statusCode, body: res.body, lines: cap.lines };
}

const checkoutEvent = (agentId) => ({ type: 'checkout.session.completed',
  data: { object: { metadata: { agent_id: agentId } } } });

async function runTree(root) {
  setEnv();
  const out = {};
  const revokeAfterRead = (db) => db.once('afterRead', (e) => { e.tables.sairn_agents[0].status = 'revoked'; });

  // ── #1619 REGISTER ───────────────────────────────────────────────────────
  let db = new Emulator({ tables: { sairn_agents: [agentRow()] } });
  revokeAfterRead(db);
  let r = await register(root, db);
  out.R1_revoke_inside_window = { handler: r.status, finalStatus: db.tables.sairn_agents[0].status, patchUrls: patches(db).map((p) => p.keys.join('&')) };

  db = new Emulator({ tables: { sairn_agents: [agentRow()] } });
  r = await register(root, db);
  out.R2_clean_registration = { handler: r.status, finalStatus: db.tables.sairn_agents[0].status };

  db = new Emulator({ tables: { sairn_agents: [agentRow({ status: 'revoked' })] } });
  r = await register(root, db);
  out.R3_revoked_at_read = { handler: r.status, finalStatus: db.tables.sairn_agents[0].status, writes: patches(db).length };

  db = new Emulator({ tables: { sairn_agents: [agentRow({ status: 'active' })] } });
  const both = await Promise.all([register(root, db), register(root, db)]);
  out.R4_two_concurrent_live = { handlers: both.map((x) => x.status), finalStatus: db.tables.sairn_agents[0].status };

  // an agent revoked BEFORE the second of two concurrent calls reads: the
  // second must not resurrect it either (the revoke lands between the calls).
  db = new Emulator({ tables: { sairn_agents: [agentRow({ status: 'active' })] } });
  db.once('afterRead', (e) => { e.tables.sairn_agents[0].status = 'revoked'; });
  const pair = await Promise.all([register(root, db), register(root, db)]);
  out.R4b_revoke_between_two_calls = { handlers: pair.map((x) => x.status).sort(), finalStatus: db.tables.sairn_agents[0].status };

  // ── ABLATIONS of the post-fix register.js, mine (only meaningful on post) ──
  const ablate = {
    R6_no_cas_clause: (s) => s.replace('+ \'&status=neq.revoked\'', '+ \'\''),
    R7_minimal_return: (s) => s.replace("Prefer: 'return=representation'", "Prefer: 'return=minimal'"),
    R8_no_zero_row_check: (s) => s.replace(/if \(!Array\.isArray\(updated\) \|\| updated\.length === 0\) \{[\s\S]*?\n    \}\n/, ''),
  };
  out.ablations = {};
  for (const [id, tf] of Object.entries(ablate)) {
    const base = require('fs').readFileSync(path.join(root, 'api', 'agent', 'register.js'), 'utf8');
    const changed = tf(base) !== base;
    db = new Emulator({ tables: { sairn_agents: [agentRow()] } });
    revokeAfterRead(db);
    const a1 = await register(root, db, tf);
    const race = { handler: a1.status, finalStatus: db.tables.sairn_agents[0].status };
    db = new Emulator({ tables: { sairn_agents: [agentRow()] } });
    const a2 = await register(root, db, tf);
    out.ablations[id] = { mutationApplied: changed, race, cleanRegistration: { handler: a2.status, finalStatus: db.tables.sairn_agents[0].status } };
  }

  // ── #1617 WEBHOOK ─────────────────────────────────────────────────────────
  db = new Emulator({ tables: { sairn_agents: [agentRow({ status: 'active' })] } });
  let w = await webhook(root, db, checkoutEvent('GHOST-9'));
  out.W1_zero_row = { http: w.status, plan: db.tables.sairn_agents[0].plan_status, log: w.lines.log, error: w.lines.error.map((s) => s.slice(0, 90)) };

  db = new Emulator({ tables: { sairn_agents: [agentRow({ status: 'active' })] } });
  w = await webhook(root, db, checkoutEvent('AG-1'));
  out.W2_real_row = { http: w.status, plan: db.tables.sairn_agents[0].plan_status, log: w.lines.log, error: w.lines.error };

  db = new Emulator({ tables: { sairn_agents: [agentRow({ status: 'active' })] } });
  w = await webhook(root, db, checkoutEvent('AG-1&plan_status=eq.paid'));
  out.W3_injection_shaped_id = { http: w.status, plan: db.tables.sairn_agents[0].plan_status, patchKeys: patches(db).map((p) => p.keys.join(',')), log: w.lines.log, error: w.lines.error.map((s) => s.slice(0, 70)) };

  // The data store accepts the PATCH but the row count cannot be read: emulate a
  // 204 even though the handler asked for a representation.
  db = new Emulator({ tables: { sairn_agents: [agentRow({ status: 'active' })] } });
  const real = db.fetch;
  global.__h1_blind = (url, init) => real(url, init).then(async (r) => (init && init.method === 'PATCH') ? { ok: true, status: 204, json: async () => { throw new SyntaxError('no body'); }, text: async () => '' } : r);
  const handler = loadFresh(path.join(root, 'api', 'agent', 'stripe-webhook.js'));
  global.fetch = global.__h1_blind;
  {
    const raw = JSON.stringify(checkoutEvent('AG-1'));
    const t = Math.floor(Date.now() / 1000);
    const sig = crypto.createHmac('sha256', SECRET).update(t + '.' + raw).digest('hex');
    const EventEmitter = require('events');
    const req = new EventEmitter(); req.method = 'POST'; req.headers = { 'stripe-signature': 't=' + t + ',v1=' + sig };
    const res = mockRes();
    const p = handler(req, res);
    setImmediate(() => { req.emit('data', raw); req.emit('end'); });
    const cap = await capture(() => p);
    out.W4_count_unreadable = { http: res.statusCode, log: cap.lines.log, error: cap.lines.error.map((s) => s.slice(0, 70)) };
  }

  // ── #1622 FAIL-CLOSED MODE ────────────────────────────────────────────────
  const lim = require(path.join(root, 'api', '_lib', 'ai-rate-limit.js'));
  const spell = [undefined, '', '   ', 'enforce', 'observe', 'enforcs', 'observ', 'off', '0', 'false', 'true', 'ENFORCE', 'Observe ', 'enforce\n'];
  out.L2_isEnforcing_by_spelling = {};
  const keep = process.env.SAIRN_AI_RATE_LIMIT_MODE;
  for (const v of spell) {
    if (v === undefined) delete process.env.SAIRN_AI_RATE_LIMIT_MODE; else process.env.SAIRN_AI_RATE_LIMIT_MODE = v;
    out.L2_isEnforcing_by_spelling[JSON.stringify(v === undefined ? '<unset>' : v)] = lim.isEnforcing();
  }
  if (keep === undefined) delete process.env.SAIRN_AI_RATE_LIMIT_MODE; else process.env.SAIRN_AI_RATE_LIMIT_MODE = keep;

  // The counter is unreachable (every request fails): the DEGRADED axis. It must
  // still answer, and the unset flag must read as enforce on the post-fix tree.
  delete process.env.SAIRN_AI_RATE_LIMIT_MODE;
  global.fetch = async () => { throw new Error('emulated: counter unreachable'); };
  let degraded;
  try {
    const c = await capture(() => lim.checkAiRateLimit('stonedesk', 'T-1'));
    degraded = { mode: c.value && c.value.mode, allowed: c.value && c.value.allowed, degraded: c.value && c.value.degraded };
  } catch (e) { degraded = { threw: String(e && e.message).slice(0, 80) }; }
  out.L3_unset_flag_counter_unreachable = degraded;

  // COMMENTS STRIPPED FIRST. The fix's own comment quotes the old line verbatim
  // ("It was `String(process.env.SAIRN_CLAUDE_AUTH_MODE || 'observe')`"), so a
  // raw regex over the file matches the explanation of the fix -- the first
  // version of this arm reported the old default PRESENT on the fixed tree for
  // exactly that reason.
  const claudeCode = stripJsComments(require('fs').readFileSync(path.join(root, 'api', 'claude.js'), 'utf8'));
  out.L4_claude_js = {
    oldDefaultInCode: /SAIRN_CLAUDE_AUTH_MODE\s*\|\|\s*'observe'/.test(claudeCode),
    resolvedViaSharedRule: /failClosedMode\.resolveMode\(\s*'SAIRN_CLAUDE_AUTH_MODE'/.test(claudeCode),
  };
  return out;
}

async function main() {
  const a = process.argv.slice(2);
  if (a[0] === '--compare') {
    const { execFileSync } = require('child_process');
    const run = (root) => JSON.parse(execFileSync(process.execPath, [__filename, root], { encoding: 'utf8', maxBuffer: 1 << 24 }));
    const pre = run(a[1]), post = run(a[2]);
    console.log(JSON.stringify({ pre, post }, null, 1));
    return;
  }
  const out = await runTree(path.resolve(a[0]));
  process.stdout.write(JSON.stringify(out));
}
main().catch((e) => { console.error('DRIVE ERROR', e && e.stack); process.exit(2); });
