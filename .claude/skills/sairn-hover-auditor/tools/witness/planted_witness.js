'use strict';
/*
 * planted_witness.js -- a WITNESS TEST for every seed in hover_planted_bug_recall
 * .SEEDS. Built H1 b74, item 4 ("confirm each planted bug actually has a working
 * witness test before trusting any recall number from the set").
 *
 *   node planted_witness.js <dir>      (dir holds <id>.js per seed + meta.json)
 *   HOVER_WITNESS_SABOTAGE=no-interleave node planted_witness.js <dir>
 *
 * WHAT A WITNESS IS. A recall number says "the detector found X of the N planted
 * bugs". That number means nothing unless each planted bug IS a bug. A seed is a
 * string a human believed was defective; this file RUNS it and observes the
 * defect: the class invariant is violated by the fragment, executed against a
 * store (pgrest_emulator.js) that moves while the fragment is between its read
 * and its write. A detector's verdict is never consulted here -- the witness is
 * independent of every detector, which is the point.
 *
 * WHAT MAKES A WITNESS "WORKING". Four things, each checked, none assumed:
 *   1. it RUNS the seed (a harness error is a failed witness, never a skip);
 *   2. it observes the violation on a planted seed (BUG_WITNESSED);
 *   3. it CAN come out the other way -- every class has a clean twin that must
 *      read NO_BUG_OBSERVED under the identical scenario, and every seed has a
 *      control arm showing the harness does not violate the invariant by itself;
 *   4. the race-dependent ones depend on the RACE: with HOVER_WITNESS_SABOTAGE=
 *      no-interleave (the two calls run one after the other, the hook never
 *      fires) they must flip to NO_BUG_OBSERVED. A witness that still "finds"
 *      a lost update with no concurrency was measuring something else.
 *
 * ASSUMED HELPER CONTRACTS, DECLARED PER SEED. Several fragments call a helper
 * they do not define (loadEmployee, readCount, one_write ...). The witness gives
 * each the most natural implementation -- a plain read, and an ID-ONLY write --
 * and says so in `assumed`. A witness on such a seed shows the fragment is
 * defective GIVEN that contract; if the real helper adds the guard itself, the
 * seed is not a bug in that codebase. That is a limit of snippet-scoped review,
 * stated, not hidden.
 *
 * NOT CLAIMED: that this proves anything about production, or that a witness for
 * a hard/hard2 seed would flip if THAT seed were fixed (only the six clean twins
 * are fixed counterparts). The witness shows the seed misbehaves; it does not
 * grade the detectors that are later scored against it.
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');
const { Emulator, mockRes, BASE } = require('./pgrest_emulator');

const SABOTAGE = process.env.HOVER_WITNESS_SABOTAGE || '';
const NO_RACE = SABOTAGE === 'no-interleave';
const dir = process.argv[2];
const meta = JSON.parse(fs.readFileSync(path.join(dir, 'meta.json'), 'utf8'));
const codeOf = (id) => fs.readFileSync(path.join(dir, id + '.js'), 'utf8');

function ctxWith(emu, extra) {
  const lines = [];
  const con = { log: (...a) => lines.push(a.join(' ')), error: (...a) => lines.push('ERR ' + a.join(' ')), warn: () => {} };
  const base = { fetch: emu ? emu.fetch : undefined, console: con, Buffer, URL, setTimeout,
    U: BASE, H: { apikey: 'k' }, lines };
  return vm.createContext(Object.assign(base, extra || {}));
}
const block = (code, ctx) => vm.runInContext('(async () => {\n' + code + '\n})()', ctx);
const decls = (code, ctx) => vm.runInContext(code, ctx);
const sym = (ctx, name) => vm.runInContext(name, ctx);
async function attempt(f) {
  try { return { ok: true, v: await f() }; } catch (e) { return { ok: false, err: String((e && e.message) || e).slice(0, 80) }; }
}
async function two(fa, fb) {
  if (NO_RACE) { const a = await attempt(fa); const b = await attempt(fb); return [a, b]; }
  return Promise.all([attempt(fa), attempt(fb)]);
}
const race = (emu, fn) => { if (!NO_RACE) emu.once('afterRead', fn); };

// ── read-modify-write counters: money-toctou and lost-update-counter ───────
// INVARIANT: the stored value equals init + delta * (number of calls that
// RETURNED WITHOUT AN ERROR). Two calls that both "succeed" but move the value
// once have lost an update; a CAS that refuses the loser keeps it true.
async function rmw(id, spec) {
  const code = codeOf(id);
  const build = () => {
    const emu = new Emulator({ tables: { [spec.table]: [Object.assign({ id: spec.rowId }, { [spec.field]: spec.init })] }, rpc: spec.rpc });
    const ctx = ctxWith(emu, spec.extra ? spec.extra(emu) : {});
    if (spec.style === 'decls') decls(code, ctx);
    return { emu, ctx, op: spec.op(emu, ctx, code) };
  };
  let a = build();
  const res = await two(a.op, a.op);
  const okN = res.filter((r) => r.ok).length;
  const final = a.emu.tables[spec.table][0][spec.field];
  const expected = spec.init + spec.delta * okN;
  const bug = final !== expected;
  // CONTROL: the same two calls one after the other. The invariant must hold.
  let b = build();
  const r1 = await attempt(b.op); const r2 = await attempt(b.op);
  const seqOk = [r1, r2].filter((r) => r.ok).length;
  const controlFinal = b.emu.tables[spec.table][0][spec.field];
  return { bug, control_ok: controlFinal === spec.init + spec.delta * seqOk && seqOk >= 1,
    evidence: { racing: { successes: okN, final, expected }, sequential: { successes: seqOk, final: controlFinal } },
    assumed: spec.assumed || null };
}

// ── zero-row false success ────────────────────────────────────────────────
// INVARIANT: a write that matched NO row must not return as a success. The
// store cannot have changed (there is no row), so a call that returns normally
// has reported a change that did not happen.
async function zeroRow(id, spec) {
  const code = codeOf(id);
  const run = async (rowId) => {
    const emu = new Emulator({ tables: { [spec.table]: [Object.assign({ id: 'REAL' }, spec.row)] } });
    const ctx = ctxWith(emu, spec.extra ? spec.extra() : {});
    decls(code, ctx);
    const r = await attempt(() => spec.call(ctx, rowId));
    return { threw: !r.ok, err: r.err, log: ctx.lines.concat(ctx.__audit || []).join(' | ').slice(0, 90), row: emu.tables[spec.table][0] };
  };
  const ghost = await run('GHOST');
  const real = await run('REAL');
  return { bug: !ghost.threw,
    control_ok: !real.threw && real.row[spec.changed.field] === spec.changed.to,
    evidence: { ghostReturnedNormally: !ghost.threw, ghostLog: ghost.log, realUpdated: real.row[spec.changed.field] === spec.changed.to },
    assumed: null };
}

// ── revocation clobber ────────────────────────────────────────────────────
// INVARIANT: a principal deactivated between the guard's READ and the WRITE is
// still deactivated afterwards. CONTROL: one deactivated BEFORE the read is
// refused and stays so -- the guard is real, the race is the only hole.
async function revoke(id, spec) {
  const code = codeOf(id);
  const run = async (initial, racing) => {
    const emu = new Emulator({ tables: { [spec.table]: [Object.assign({ id: 'X1' }, spec.base, initial)] } });
    const res = mockRes();
    const ctx = ctxWith(emu, Object.assign({ res }, spec.extra ? spec.extra(emu) : {}));
    let fired = false;
    if (racing) race(emu, (e) => { Object.assign(e.tables[spec.table][0], spec.deactivate); fired = true; });
    if (spec.style === 'decls') decls(code, ctx);
    const r = await attempt(() => (spec.style === 'block' ? block(code, ctx) : spec.call(ctx, res)));
    return { emu, res, r, fired: () => fired };
  };
  const raced = await run(spec.live, true);
  const finalRaced = raced.emu.tables[spec.table][0];
  // A VIOLATION needs the deactivation to have HAPPENED. With no interleaving
  // the in-flight change never fires, the row was never deactivated, and a final
  // state of 'active' is simply a normal registration, not a clobber.
  const bug = raced.fired() && spec.isRestored(finalRaced);
  const pre = await run(spec.deactivate, false);
  const finalPre = pre.emu.tables[spec.table][0];
  return { bug, control_ok: !spec.isRestored(finalPre) && pre.res.statusCode === 403,
    evidence: { deactivationInFlight: raced.fired(), racedHandler: raced.res.statusCode, racedFinal: spec.view(finalRaced), preDeactivated: { handler: pre.res.statusCode, final: spec.view(finalPre) } },
    assumed: spec.assumed || null };
}

// ── client-trusted role ───────────────────────────────────────────────────
// INVARIANT: the privileged sink is not reached on the strength of a claim the
// SERVER did not verify. ATTACK: a forged / unsigned claim of the privilege.
// CONTROL: a claim of NO privilege is refused (the handler is not simply open).
const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64');
async function trusted(id, spec) {
  const code = codeOf(id);
  const run = async (req) => {
    const calls = [];
    const res = mockRes();
    const ctx = ctxWith(null, Object.assign({ module: { exports: {} }, calls }, spec.helpers(calls, res)));
    decls(code, ctx);
    const r = await attempt(() => ctx.module.exports(req, res));
    return { calls: calls.length, status: res.statusCode, r };
  };
  const attack = await run(spec.attack);
  const control = await run(spec.control);
  const extra = spec.extraAttack ? await run(spec.extraAttack) : null;
  const goodAllowed = spec.legit ? (await run(spec.legit)).calls > 0 : true;
  return { bug: attack.calls > 0 || (extra ? extra.calls > 0 : false),
    control_ok: control.calls === 0 && goodAllowed,
    evidence: { forgedClaimReachedSink: attack.calls > 0, extraAttackReachedSink: extra ? extra.calls > 0 : null,
      unprivilegedRefused: control.calls === 0, legitimateAllowed: spec.legit ? goodAllowed : null },
    assumed: spec.assumed || null };
}

// ── PostgREST filter injection ────────────────────────────────────────────
// INVARIANT: bytes the CALLER controls are DATA, never URL STRUCTURE. WITNESS:
// the multiset of query-parameter NAMES the fragment emits is identical for a
// benign value and for a value that carries an extra parameter.
async function injection(id, spec) {
  const code = codeOf(id);
  const keysFor = async (v) => {
    const urls = [];
    const f = async (u) => { urls.push(String(u)); return { ok: true, status: 200, json: async () => [], text: async () => '[]' }; };
    const ctx = ctxWith(null, Object.assign({ fetch: f }, spec.vars(v)));
    if (spec.style === 'decls') decls(code, ctx);
    const r = await attempt(() => block(code, ctx));
    if (!urls.length) return { error: r.err || 'no request was made', keys: null };
    return { keys: Array.from(new URL(urls[0]).searchParams.keys()) };
  };
  const base = await keysFor('M1');
  const a1 = await keysFor('M1&select=*');
  const a2 = await keysFor('M1&' + spec.dupKey + '=neq.zzz');
  const same = (x, y) => x.keys && y.keys && JSON.stringify(x.keys) === JSON.stringify(y.keys);
  const bug = !!(a1.keys && base.keys && !same(base, a1)) || !!(a2.keys && base.keys && !same(base, a2));
  return { bug, control_ok: !!base.keys && base.keys.includes(spec.dupKey),
    evidence: { benign: base.keys, injectedSelect: a1.keys, injectedDuplicateFilter: a2.keys },
    assumed: null };
}

// ── the table: one entry per seed id ──────────────────────────────────────
const ledgerClient = (emu) => ({ rest: emu.rest, headers: { apikey: 'k' } });
const S = {};

S['mt-1'] = () => rmw('mt-1', { table: 'ledger', rowId: 'L1', field: 'balance', init: 1000, delta: -100, style: 'decls',
  op: (emu, ctx) => () => sym(ctx, 'settle')(ledgerClient(emu), 'L1') });
S['mt-2'] = () => rmw('mt-2', { table: 'ledger', rowId: 'L1', field: 'amount_due', init: 500, delta: 50, style: 'decls',
  op: (emu, ctx) => () => sym(ctx, 'applyFee')(ledgerClient(emu), 'L1', 50) });
S['mt-3'] = () => rmw('mt-3', { table: 'quotes', rowId: 'Q1', field: 'total', init: 700, delta: 25, style: 'decls',
  op: (emu, ctx) => () => sym(ctx, 'reprice')(ledgerClient(emu), 'Q1', 25) });
S['mt-c'] = () => rmw('mt-c', { table: 'ledger', rowId: 'L1', field: 'balance', init: 1000, delta: -100, style: 'decls',
  assumed: 'each caller read the balance earlier and passes it as the compare-and-set value',
  op: (emu, ctx) => () => sym(ctx, 'settle')(ledgerClient(emu), 'L1', emu.tables.ledger[0].balance) });

S['lu-1'] = () => rmw('lu-1', { table: 'cl_citing_treatments', rowId: 7, field: 'followed_count', init: 0, delta: 1, style: 'block',
  extra: (emu) => ({ sb: ledgerClient(emu), id: 7, f: 'followed_count' }),
  op: (emu, ctx, code) => () => block(code, ctx) });
S['lu-2'] = () => rmw('lu-2', { table: 'counters', rowId: 'C1', field: 'n', init: 0, delta: 1, style: 'decls',
  assumed: 'readCount is a plain read of the counter and writeCount an ID-ONLY write of the new value',
  extra: (emu) => {
    const sb = ledgerClient(emu);
    return { sb,
      readCount: async (s, id) => (await (await emu.fetch(s.rest('counters?id=eq.' + id + '&select=n'))).json())[0].n,
      writeCount: async (s, id, n) => { await emu.fetch(s.rest('counters?id=eq.' + id), { method: 'PATCH', headers: s.headers, body: JSON.stringify({ n }) }); } };
  },
  op: (emu, ctx) => () => sym(ctx, 'bump')(ledgerClient(emu), 'C1') });
S['lu-3'] = () => rmw('lu-3', { table: 'pages', rowId: 'P1', field: 'view_count', init: 0, delta: 1, style: 'block',
  assumed: 'the fragment starts AFTER the row was read; the harness supplies that read as a preamble',
  extra: (emu) => ({ sb: ledgerClient(emu), pid: 'P1' }),
  op: (emu, ctx, code) => () => block("const row = (await (await fetch(sb.rest('pages?id=eq.' + pid))).json())[0];\n" + code, ctx) });
S['lu-c'] = () => rmw('lu-c', { table: 'cl_citing_treatments', rowId: 7, field: 'followed_count', init: 0, delta: 1, style: 'block',
  assumed: 'increment_treatment_count is an ATOMIC server-side increment (a single UPDATE ... SET f = f + 1)',
  rpc: { increment_treatment_count: (args, emu) => { const r = emu.tables.cl_citing_treatments.find((x) => String(x.id) === String(args.p_id)); r[args.p_field] = (r[args.p_field] || 0) + 1; return null; } },
  extra: (emu) => ({ sb: ledgerClient(emu), id: 7, f: 'followed_count' }),
  op: (emu, ctx, code) => () => block(code, ctx) });

const zrHttp = (emu) => ({ url: BASE, headers: { apikey: 'k' } });
S['zr-1'] = () => zeroRow('zr-1', { table: 'sairn_agents', row: { plan_status: 'trial' }, changed: { field: 'plan_status', to: 'paid' },
  call: (ctx, rid) => sym(ctx, 'setPlanStatus')(BASE, { apikey: 'k' }, rid, 'paid') });
S['zr-2'] = () => zeroRow('zr-2', { table: 'invoices', row: { status: 'open' }, changed: { field: 'status', to: 'paid' },
  extra: () => { const a = []; return { audit: (m) => a.push(m), __a: a }; },
  call: async (ctx, rid) => { await sym(ctx, 'markPaid')(BASE, { apikey: 'k' }, rid); ctx.__audit = ctx.__a; } });
S['zr-3'] = () => zeroRow('zr-3', { table: 'claims', row: { state: 'open' }, changed: { field: 'state', to: 'closed' },
  extra: () => { const a = []; return { log: (m) => a.push(m), __a: a }; },
  call: async (ctx, rid) => { await sym(ctx, 'closeClaim')(BASE, { apikey: 'k' }, rid); ctx.__audit = ctx.__a; } });
S['zr-c'] = () => zeroRow('zr-c', { table: 'sairn_agents', row: { plan_status: 'trial' }, changed: { field: 'plan_status', to: 'paid' },
  call: (ctx, rid) => sym(ctx, 'setPlanStatus')(BASE, { apikey: 'k' }, rid, 'paid') });

S['rc-1'] = () => revoke('rc-1', { table: 'sairn_agents', style: 'block', base: { token_hash: 'TH1' }, live: { status: 'pending' }, deactivate: { status: 'revoked' },
  extra: () => ({ th: 'TH1' }), isRestored: (r) => r.status === 'active', view: (r) => r.status });
S['rc-c'] = () => revoke('rc-c', { table: 'sairn_agents', style: 'block', base: { token_hash: 'TH1' }, live: { status: 'pending' }, deactivate: { status: 'revoked' },
  extra: () => ({ th: 'TH1' }), isRestored: (r) => r.status === 'active', view: (r) => r.status });
const empHelpers = (emu) => ({
  pinHash: 'PH1', nowIso: () => '2026-10-20T00:00:00Z',
  loadEmployee: async (u, h, ph) => (await (await emu.fetch(u + '/rest/v1/employees?pin_hash=eq.' + ph + '&select=*')).json())[0],
  patchEmployee: async (u, h, id, fields) => { await emu.fetch(u + '/rest/v1/employees?id=eq.' + id, { method: 'PATCH', headers: h, body: JSON.stringify(fields) }); },
  deny: (r, why) => { r.status(403).json({ error: why }); } });
S['rc-2'] = () => revoke('rc-2', { table: 'employees', style: 'block', base: { pin_hash: 'PH1' }, live: { active: true }, deactivate: { active: false },
  assumed: 'loadEmployee is a plain read and patchEmployee an ID-ONLY write', extra: empHelpers,
  isRestored: (r) => r.active === true, view: (r) => r.active });
const staffHelpers = (emu) => ({
  one: async (u, h, t, id) => (await (await emu.fetch(u + '/rest/v1/' + t + '?id=eq.' + id + '&select=*')).json())[0],
  one_write: async (u, h, t, id, fields) => { await emu.fetch(u + '/rest/v1/' + t + '?id=eq.' + id, { method: 'PATCH', headers: h, body: JSON.stringify(fields) }); },
  touch: () => ({ last_seen: '2026-10-20T00:00:00Z' }), id: 'X1' });
S['rc-3'] = () => revoke('rc-3', { table: 'staff', style: 'block', base: {}, live: { suspended: false }, deactivate: { suspended: true },
  assumed: 'one is a plain read and one_write an ID-ONLY write', extra: staffHelpers,
  isRestored: (r) => r.suspended === false, view: (r) => r.suspended });

const hmac = (s) => crypto.createHmac('sha256', 'witness-secret').update(s).digest('hex');
const mkTok = (claims) => { const p = Buffer.from(JSON.stringify(claims)).toString('base64'); return p + '.' + hmac(p); };
S['ct-1'] = () => trusted('ct-1', {
  helpers: (calls) => ({ writeTrustDisbursement: async (a, p) => { calls.push([a, p]); } }),
  attack: { body: { role: 'admin', amount: 100, payee: 'X' }, headers: {} },
  control: { body: { role: 'clerk', amount: 100, payee: 'X' }, headers: {} } });
S['ct-2'] = () => trusted('ct-2', {
  assumed: 'hasRole(have, need) is a plain equality test',
  helpers: (calls, res) => ({ hasRole: (h, n) => h === n, deny: (r) => { r.status(403).end(); }, postLedgerEntry: async (t, c) => { calls.push([t, c]); } }),
  attack: { body: { cents: 100 }, headers: { 'x-session': b64({ role: 'owner', tenant: 'T1' }) } },
  control: { body: { cents: 100 }, headers: { 'x-session': b64({ role: 'clerk', tenant: 'T1' }) } } });
S['ct-3'] = () => trusted('ct-3', {
  helpers: (calls) => ({ moveFunds: async (t, c) => { calls.push([t, c]); } }),
  attack: { body: { cents: 100 }, headers: { authorization: 'h.' + Buffer.from(JSON.stringify({ scope: 'treasury', tenant: 'T1' })).toString('base64') + '.forged' } },
  control: { body: { cents: 100 }, headers: { authorization: 'h.' + Buffer.from(JSON.stringify({ scope: 'ops', tenant: 'T1' })).toString('base64') + '.forged' } } });
S['ct-c'] = () => trusted('ct-c', {
  assumed: 'verifySessionToken checks an HMAC the caller cannot compute; readEmployeeRow reads the CURRENT row',
  helpers: (calls) => {
    let active = true;
    return { tokenFromRequest: (req) => String((req.headers && req.headers.authorization) || '').replace(/^Bearer /, ''),
      verifySessionToken: (t) => { const [p, s] = String(t).split('.'); if (!p || !s || hmac(p) !== s) return null; try { return JSON.parse(Buffer.from(p, 'base64').toString()); } catch (e) { return null; } },
      readEmployeeRow: async (sub) => ({ sub, active: sub !== 'GONE', role: 'admin' }),
      hasRole: (h, n) => h === n, deny: (r) => { r.status(403).end(); }, writeTrustDisbursement: async (a, p) => { calls.push([a, p]); } };
  },
  attack: { body: { amount: 1, payee: 'X' }, headers: { authorization: 'Bearer ' + Buffer.from(JSON.stringify({ sub: 'E1', role: 'admin' })).toString('base64') + '.forged' } },
  extraAttack: { body: { amount: 1, payee: 'X' }, headers: { authorization: 'Bearer ' + mkTok({ sub: 'GONE' }) } },
  control: { body: { amount: 1, payee: 'X' }, headers: {} },
  legit: { body: { amount: 1, payee: 'X' }, headers: { authorization: 'Bearer ' + mkTok({ sub: 'E1' }) } } });

S['fi-1'] = () => injection('fi-1', { dupKey: 'matter_id', vars: (v) => ({ req: { body: { matter_id: v } } }) });
S['fi-2'] = () => injection('fi-2', { dupKey: 'client_id', vars: (v) => ({ body: { clientId: v } }) });
S['fi-3'] = () => injection('fi-3', { dupKey: 'patient_id', vars: (v) => ({ req: { query: { pid: v } } }) });
S['fi-c'] = () => injection('fi-c', { dupKey: 'matter_id', vars: (v) => ({ req: { body: { matter_id: v } } }) });

(async () => {
  const out = [];
  for (const m of meta) {
    const fn = S[m.id];
    if (!fn) { out.push({ id: m.id, cls: m.cls, kind: m.kind, verdict: 'NO_WITNESS_DEFINED' }); continue; }
    try {
      const r = await fn();
      out.push({ id: m.id, cls: m.cls, kind: m.kind, bug: r.bug, control_ok: r.control_ok,
        verdict: r.bug ? 'BUG_WITNESSED' : 'NO_BUG_OBSERVED', evidence: r.evidence, assumed: r.assumed || null });
    } catch (e) {
      out.push({ id: m.id, cls: m.cls, kind: m.kind, verdict: 'HARNESS_ERROR', error: String((e && e.stack) || e).slice(0, 300) });
    }
  }
  process.stdout.write(JSON.stringify({ sabotage: SABOTAGE || null, handled: Object.keys(S), results: out }));
})();
