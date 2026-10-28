// tools/field_scope_driver.js -- drives the REAL api handler for
// tools/sairn_field_scope_check.py. Not run by hand.
//
//   node tools/field_scope_driver.js < cases.json > results.json
//
// stdin:  { "handler": "<abs path to api/sd-data.js>", "cases": [
//            { "app", "role", "employee_id", "body", "tables": { name: [row] } } ] }
// stdout: { "results": [ { "status", "body" } | { "error" } ] }
//
// The handler is loaded fresh for every case with only two things replaced:
// api/_lib/license (any key is a valid licence for the case's app) and global
// fetch (a PostgREST stand-in over the case's seeded tables). The session
// token is signed by the REAL api/_lib/auth, so the role reaches the handler
// the way a deployed request carries it.
//
// THE MOCK IS UNFAITHFUL ONLY IN THE LOUD DIRECTION. `<col>=eq.<v>` filters
// rows that have that column; a row that lacks the column does not match,
// so an unmodelled filter returns FEWER rows and a declared-visible field goes
// missing -- a failure, never a silent pass. `select=` is honoured. Any other
// URL answers 200 []. A POST echoes what it was sent.
'use strict';

const path = require('path');

const HASH = 'field-scope-hash';

function readStdin() {
  return new Promise((resolve) => {
    let s = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (c) => { s += c; });
    process.stdin.on('end', () => resolve(s));
  });
}

function pgMock(tables, sess) {
  return async function (url, opts) {
    const u = String(url);
    const m = u.match(/\/rest\/v1\/([a-z0-9_]+)(\?|$)/);
    const ok = (rows) => ({ ok: true, status: 200, json: async () => rows, text: async () => JSON.stringify(rows) });
    if (!m) return ok([]);
    const table = m[1];
    const q = u.indexOf('?') >= 0 ? u.slice(u.indexOf('?') + 1) : '';
    const eqs = [];
    let select = null;
    q.split('&').forEach((part) => {
      const e = part.match(/^([a-z0-9_]+)=eq\.(.*)$/);
      if (e) { eqs.push([e[1], decodeURIComponent(e[2])]); return; }
      const s = part.match(/^select=(.*)$/);
      if (s) select = decodeURIComponent(s[1]).split(',').map((x) => x.trim());
    });
    if (/_employee_auth$/.test(table)) {
      return ok([{ license_hash: HASH, employee_id: sess.employee_id, role: sess.role,
                   active: true, name: 'probe' }]);
    }
    if (opts && opts.method && opts.method !== 'GET') {
      let sent = null;
      try { sent = JSON.parse(opts.body); } catch (_e) { sent = null; }
      return ok(Array.isArray(sent) ? sent : [sent]);
    }
    const rows = (tables[table] || []).filter((r) =>
      eqs.every(([k, v]) => Object.prototype.hasOwnProperty.call(r, k) && String(r[k]) === v));
    return ok(rows.map((r) => {
      if (!select || select.indexOf('*') !== -1) return r;
      const out = {};
      select.forEach((c) => { if (c in r) out[c] = r[c]; });
      return out;
    }));
  };
}

async function runCase(handlerPath, c) {
  const apiDir = path.dirname(handlerPath);
  const licPath = require.resolve(path.join(apiDir, '_lib', 'license'));
  require.cache[licPath] = { id: licPath, filename: licPath, loaded: true, exports: {
    validateLicenseKey: async () => ({ valid: true, active: true, license_hash: HASH,
      trial_ends_at: null, stripe_subscription_id: null, app_id: c.app })
  } };
  const tables = {};
  Object.keys(c.tables || {}).forEach((t) => {
    tables[t] = c.tables[t].map((r) => Object.assign({ license_hash: HASH, app_id: c.app }, r));
  });
  global.fetch = pgMock(tables, c);
  Object.keys(require.cache).forEach((k) => {
    if (k.startsWith(apiDir) && k !== licPath) delete require.cache[k];
  });
  const auth = require(path.join(apiDir, '_lib', 'auth'));
  const handler = require(handlerPath);
  const res = { statusCode: null, body: null, headers: {} };
  res.status = (s) => { res.statusCode = s; return res; };
  res.json = (b) => { res.body = b; return res; };
  res.send = (b) => { res.body = b; return res; };
  res.end = (b) => { if (b !== undefined) res.body = b; return res; };
  res.setHeader = (k, v) => { res.headers[k] = v; };
  const req = { method: 'POST', headers: {
    authorization: 'Bearer FIELD-SCOPE-KEY',
    'x-sd-auth': auth.signSessionToken({ app: c.app, employee_id: c.employee_id,
                                         role: c.role, license_hash: HASH })
  }, body: c.body, query: {} };
  await handler(req, res);
  return { status: res.statusCode, body: res.body };
}

// ── --serve: the LIVE path, against a handler you choose (cc b63) ─────────
//   node tools/field_scope_driver.js --serve <config.json>
// config: { handler, port, app, tables, creds: { <employee_id>: { pin, role } } }
// Serves POST /api/*-auth {action:'login'} and POST /api/sd-data over HTTP, so
// `sairn_field_scope_check.py --live` can be pointed at a KNOWN-BAD handler
// (SAIRN_LIVE_BASE=http://127.0.0.1:<port>) and must report the leak through
// exactly the code path it uses against the deployed one. A live check that has
// only ever seen a clean server has proved nothing about what it would catch.
async function serve(cfgPath) {
  const http = require('http');
  const cfg = JSON.parse(require('fs').readFileSync(cfgPath, 'utf8'));
  const server = http.createServer((req, res) => {
    let raw = '';
    req.on('data', (c) => { raw += c; });
    req.on('end', async () => {
      const send = (code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(obj)); };
      let body = {};
      try { body = raw ? JSON.parse(raw) : {}; } catch (_e) { return send(400, { error: 'bad json' }); }
      try {
        if (/-auth$/.test(req.url.split('?')[0])) {
          const c = cfg.creds[body.employee_id];
          if (body.action !== 'login' || !c || String(c.pin) !== String(body.pin)) return send(401, { error: { code: 'BAD_LOGIN' } });
          const auth = require(path.join(path.dirname(cfg.handler), '_lib', 'auth'));
          return send(200, { ok: true, token: auth.signSessionToken({ app: cfg.app, employee_id: body.employee_id,
            role: c.role, license_hash: HASH }) });
        }
        const token = req.headers['x-sd-auth'] || '';
        const auth = require(path.join(path.dirname(cfg.handler), '_lib', 'auth'));
        const sess = auth.verifySessionToken(token, HASH, cfg.app) || { employee_id: '', role: '' };
        const keep = { log: console.log, warn: console.warn, error: console.error, info: console.info };
        console.log = console.warn = console.error = console.info = () => {};
        let out;
        try {
          out = await runCase(cfg.handler, { app: cfg.app, role: sess.role, employee_id: sess.employee_id,
            body, tables: cfg.tables, token });
        } finally { Object.assign(console, keep); }
        return send(out.status || 500, out.body);
      } catch (e) { return send(500, { error: String(e && e.message || e) }); }
    });
  });
  server.listen(cfg.port, '127.0.0.1', () => { process.stdout.write('LISTENING ' + cfg.port + '\n'); });
}

(async function () {
  if (process.argv[2] === '--serve') {
    process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'field-scope-driver-secret';
    process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://field-scope.supabase.co';
    process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'field-scope-key';
    return serve(process.argv[3]);
  }
  process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET || 'field-scope-driver-secret';
  process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://field-scope.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'field-scope-key';
  const input = JSON.parse(await readStdin());
  const results = [];
  // console output from the handler would corrupt stdout, which is the result channel
  const quiet = () => {};
  const keep = { log: console.log, warn: console.warn, error: console.error, info: console.info };
  for (const c of input.cases) {
    console.log = console.warn = console.error = console.info = quiet;
    try { results.push(await runCase(input.handler, c)); }
    catch (e) { results.push({ error: String(e && e.stack || e).slice(0, 600) }); }
    finally { Object.assign(console, keep); }
  }
  process.stdout.write(JSON.stringify({ results }));
})().catch((e) => { process.stderr.write(String(e && e.stack || e)); process.exit(2); });
