// hank b68 (S4, from the b67 S3 triage): api/agent/poll.js delivered a
// command with a PATCH by id alone, so two concurrent polls that both read it
// as pending both delivered it, and the agent ran one command twice.
//
// The fake store below applies a PATCH's `status=eq.pending` filter the way
// PostgREST does -- one row update at a time -- and holds both polls' reads
// until both have read, which is the interleaving that loses.
//
// Arm X re-runs the race against poll.js as committed at 1fcd7e9f2 (before the
// fix) and REQUIRES the double delivery, so this test cannot pass on code that
// never had the defect.
'use strict';
const path = require('path');
const Module = require('module');
const { execFileSync } = require('child_process');

let passed = 0, failed = 0;
function arm(name, ok, detail) {
  if (ok) { passed++; console.log('  ok   ' + name); }
  else { failed++; console.log('  FAIL ' + name + (detail ? '  -- ' + detail : '')); }
}

function fakeRes() {
  const r = { code: null, body: null };
  r.status = (c) => { r.code = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}

function install(opts) {
  const store = { cmd: { id: 'c1', status: 'pending', operation: 'op', params: {} }, patches: 0 };
  let reads = 0, release, gate = new Promise((r) => { release = r; });
  let clockJump = 0;
  const realNow = Date.now;
  Date.now = () => realNow() + clockJump;
  global.fetch = async (url, init) => {
    const method = (init && init.method) || 'GET';
    const json = (status, body) => ({ ok: status < 300, status, json: async () => body });
    if (url.includes('/sairn_agents?token_hash=')) return json(200, [{ id: 'a1', status: 'active', plan_status: 'paid' }]);
    if (url.includes('/sairn_agents?id=')) return json(204, null);
    if (url.includes('/sairn_agent_commands?agent_id=') && method === 'GET') {
      const rows = store.cmd.status === 'pending' ? [Object.assign({}, store.cmd)] : [];
      if (rows.length && reads < 2) { reads++; if (reads === 2) release(); await gate; }
      if (!rows.length) clockJump = 60000; // end the loser's wait at once
      return json(200, rows);
    }
    if (url.includes('/sairn_agent_commands?id=') && method === 'PATCH') {
      if (opts.patchFails) return json(503, { message: 'down' });
      store.patches++;
      const guarded = url.includes('status=eq.pending');
      if (guarded && store.cmd.status !== 'pending') return json(200, []);
      store.cmd.status = 'delivered';
      return json(200, [Object.assign({}, store.cmd)]);
    }
    throw new Error('unexpected fetch ' + method + ' ' + url);
  };
  return { store, restore: () => { Date.now = realNow; } };
}

async function race(handler, opts) {
  const env = install(opts || {});
  process.env.SUPABASE_URL = 'https://fake.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'svc';
  const req = { method: 'POST', headers: { authorization: 'Bearer t' } };
  const a = fakeRes(), b = fakeRes();
  await Promise.all([handler(req, a), handler(req, b)]);
  env.restore();
  const delivered = [a, b].filter((r) => r.code === 200 && r.body && r.body.command).length;
  return { a, b, delivered, store: env.store };
}

function loadFrom(src, name) {
  const m = new Module(name, module);
  m.filename = name;
  m.paths = Module._nodeModulePaths(path.dirname(name));
  m._compile(src, name);
  return m.exports;
}

(async () => {
  const fixed = require('./agent/poll.js');

  const r1 = await race(fixed);
  arm('R1. two concurrent polls of one pending command -> exactly ONE delivers it', r1.delivered === 1,
      'delivered ' + r1.delivered);
  arm('R2. the other poll answers command:null, not an error', [r1.a, r1.b].some((r) => r.code === 200 && r.body.command === null));

  const r3 = await race(fixed, { patchFails: true });
  arm('R3. a failed deliver PATCH delivers nothing (502) and the row stays pending',
      r3.delivered === 0 && [r3.a, r3.b].every((r) => r.code === 502) && r3.store.cmd.status === 'pending',
      JSON.stringify([r3.a.code, r3.b.code, r3.store.cmd.status]));

  let oldSrc = null;
  try {
    oldSrc = execFileSync('git', ['show', '1fcd7e9f2:api/agent/poll.js'], { cwd: path.join(__dirname, '..') }).toString();
  } catch (e) { /* reported below */ }
  if (!oldSrc) {
    arm('X. ABLATION could not run: the pre-fix poll.js is not readable from git', false);
  } else {
    const old = loadFrom(oldSrc, path.join(__dirname, 'agent', 'poll.prefix.js'));
    const rx = await race(old);
    arm('X. ABLATION: the pre-fix poll.js delivers the same command TWICE under this race -- the defect was real',
        rx.delivered === 2, 'delivered ' + rx.delivered);
  }

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  process.exit(failed ? 1 : 0);
})();
