'use strict';
/*
 * pgrest_emulator.js -- H1's OWN in-memory PostgREST, for DRIVING a handler or a
 * code fragment instead of reading it. Built H1 b74 (items 3 and 4).
 *
 * WHAT IT IS FOR. Two jobs, one emulator, because both need the same thing -- a
 * data store that applies a filter at WRITE time, against the row's CURRENT
 * state, the way PostgREST/Postgres does:
 *   1. the independent re-drive of hank's b25 fixes (b25_independent_drive.js);
 *   2. the witness test behind every planted bug (planted_witness.js).
 * A fix or a defect that depends on the gap between a read and a write cannot be
 * shown by stubbing one answer; it can only be shown by a store whose state
 * moves while the handler is between its two statements.
 *
 * INDEPENDENCE. Written from scratch from PostgREST's documented URL grammar. It
 * shares no code with api/b25-revoke-race-and-failclosed.test.js's recorded
 * PostgREST, with any api/*.test.js harness, or with any other auditor's tooling.
 *
 * WHAT IT DELIBERATELY DOES NOT DO, said here rather than discovered:
 *   - It supports eq / neq / is / in / gt / gte / lt / lte and NOTHING ELSE. An
 *     operator it does not know THROWS. A silent "no match" on an unsupported
 *     filter would turn every unknown into a clean result, which is the failure
 *     this whole tool exists to avoid.
 *   - It does not model Row Level Security, triggers, embedded selects, or
 *     transactions spanning requests. Each request is atomic; nothing else is.
 *   - It is a MODEL of PostgREST semantics, not PostgREST. A result here proves a
 *     fragment misbehaves against these semantics; it does not prove what a given
 *     deployment does.
 *
 * DETERMINISTIC INTERLEAVING. Every request yields to the macrotask queue once
 * before it is answered, so two handlers started in the same tick advance
 * read-for-read and write-for-write in a fixed, reproducible order. Hooks let a
 * test move the store's state at a named point (after a read is answered, before
 * a write is applied) -- that is the "window" made explicit.
 */

const BASE = 'https://emu.invalid';

function tick() { return new Promise((r) => setImmediate(r)); }

function resp(status, body) {
  const text = body === null || body === undefined ? '' : JSON.stringify(body);
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => null },
    json: async () => {
      if (text === '') throw new SyntaxError('Unexpected end of JSON input');
      return JSON.parse(text);
    },
    text: async () => text,
  };
}

function cmp(op, cur, val) {
  const isNull = cur === null || cur === undefined;
  if (op === 'is') return val === 'null' ? isNull : (val === 'true' ? cur === true : (val === 'false' ? cur === false : false));
  if (op === 'eq') return !isNull && String(cur) === val;
  if (op === 'neq') return isNull ? true : String(cur) !== val;
  if (op === 'in') {
    const list = val.replace(/^\(|\)$/g, '').split(',').map((s) => s.replace(/^"|"$/g, ''));
    return !isNull && list.indexOf(String(cur)) !== -1;
  }
  if (op === 'gt' || op === 'gte' || op === 'lt' || op === 'lte') {
    if (isNull) return false;
    const a = Number(cur), b = Number(val);
    const numeric = Number.isFinite(a) && Number.isFinite(b);
    const x = numeric ? a : String(cur), y = numeric ? b : val;
    return op === 'gt' ? x > y : op === 'gte' ? x >= y : op === 'lt' ? x < y : x <= y;
  }
  throw new Error('pgrest_emulator: unsupported operator "' + op + '" -- add it deliberately, do not guess');
}

class Emulator {
  /**
   * @param {{tables?:Object<string,Object[]>, rpc?:Object<string,Function>}} opts
   *   rpc functions run ATOMICALLY (one synchronous call) against `this.tables`.
   */
  constructor(opts) {
    opts = opts || {};
    this.tables = opts.tables || {};
    this.rpc = opts.rpc || {};
    this.log = [];
    this._hooks = { afterRead: [], beforeWrite: [], afterWrite: [] };
    this.fetch = this.fetch.bind(this);
    this.rest = this.rest.bind(this);
  }

  /** client.rest(path) shape used by several handlers in this repo. */
  rest(path) { return BASE + '/rest/v1/' + path; }

  /** Run `fn(emulator, request)` once, at the named point of the NEXT matching request. */
  once(point, fn) { this._hooks[point].push(fn); return this; }

  _fire(point, req) {
    const fn = this._hooks[point].shift();
    if (fn) fn(this, req);
  }

  _parse(url) {
    const u = new URL(String(url), BASE);
    const parts = u.pathname.split('/').filter(Boolean);
    const i = parts.indexOf('v1');
    const rest = i >= 0 ? parts.slice(i + 1) : parts;
    const filters = [];
    let select = null;
    for (const [k, v] of u.searchParams.entries()) {
      if (k === 'select') { select = v; continue; }
      if (k === 'order' || k === 'limit' || k === 'offset' || k === 'on_conflict' || k === 'columns') continue;
      const m = /^(eq|neq|is|in|gt|gte|lt|lte)\.(.*)$/s.exec(v);
      if (!m) throw new Error('pgrest_emulator: unsupported filter "' + k + '=' + v + '"');
      filters.push({ col: k, op: m[1], val: m[2] });
    }
    return { rest, filters, select, keys: Array.from(u.searchParams.keys()), href: u.href };
  }

  _match(row, filters) {
    for (const f of filters) if (!cmp(f.op, row[f.col], f.val)) return false;
    return true;
  }

  _project(rows, select) {
    if (!select || select === '*') return rows.map((r) => Object.assign({}, r));
    const cols = select.split(',').map((s) => s.trim()).filter(Boolean);
    return rows.map((r) => { const o = {}; cols.forEach((c) => { if (c in r) o[c] = r[c]; }); return o; });
  }

  async fetch(url, init) {
    init = init || {};
    const method = String(init.method || 'GET').toUpperCase();
    const headers = init.headers || {};
    const prefer = String(headers.Prefer || headers.prefer || '');
    const q = this._parse(url);
    const entry = { method, url: String(url), keys: q.keys, prefer, body: init.body === undefined ? null : init.body };
    this.log.push(entry);
    await tick();

    if (q.rest[0] === 'rpc') {
      const fn = this.rpc[q.rest[1]];
      if (!fn) return resp(404, { message: 'rpc ' + q.rest[1] + ' not defined in the emulator' });
      const args = init.body ? JSON.parse(init.body) : {};
      return resp(200, fn(args, this));
    }
    const table = q.rest[0];
    if (!this.tables[table]) return resp(404, { message: 'relation ' + table + ' does not exist in the emulator' });
    const rows = this.tables[table];

    if (method === 'GET') {
      const out = this._project(rows.filter((r) => this._match(r, q.filters)), q.select);
      const r = resp(200, out);
      this._fire('afterRead', entry);
      return r;
    }
    if (method === 'PATCH' || method === 'DELETE') {
      this._fire('beforeWrite', entry);
      const hit = rows.filter((r) => this._match(r, q.filters));
      if (method === 'PATCH') {
        const patch = JSON.parse(init.body);
        hit.forEach((r) => Object.assign(r, patch));
      } else {
        hit.forEach((r) => rows.splice(rows.indexOf(r), 1));
      }
      this._fire('afterWrite', entry);
      return /return=representation/.test(prefer)
        ? resp(200, hit.map((r) => Object.assign({}, r)))
        : resp(204, null);
    }
    if (method === 'POST') {
      this._fire('beforeWrite', entry);
      const body = JSON.parse(init.body);
      const list = Array.isArray(body) ? body : [body];
      list.forEach((r) => rows.push(Object.assign({}, r)));
      this._fire('afterWrite', entry);
      return /return=representation/.test(prefer) ? resp(201, list) : resp(201, null);
    }
    throw new Error('pgrest_emulator: unsupported method ' + method);
  }
}

/** A res object recording what a handler said. */
function mockRes() {
  const r = { statusCode: null, body: null, ended: false };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  r.end = () => { r.ended = true; return r; };
  r.setHeader = () => r;
  return r;
}

/** Capture console.log/warn/error for the duration of fn(), restoring on any exit. */
async function capture(fn) {
  const lines = { log: [], warn: [], error: [] };
  const saved = { log: console.log, warn: console.warn, error: console.error };
  ['log', 'warn', 'error'].forEach((k) => { console[k] = (...a) => lines[k].push(a.map(String).join(' ')); });
  try { return { value: await fn(), lines }; }
  finally { console.log = saved.log; console.warn = saved.warn; console.error = saved.error; }
}

module.exports = { Emulator, mockRes, capture, BASE, tick };
