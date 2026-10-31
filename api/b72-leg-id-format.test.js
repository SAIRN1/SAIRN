// hank b72 (H1 #1734, the SERVER half): the SAIRNlegacy write branch in
// api/sd-data.js required only that payload.id be non-empty, so a caller with a
// write grant could store an id holding a quote and markup, which ran in the
// browser of whoever opened the page. The client sinks were fixed in
// af2db16b3 (JA()). This pins the server half: an id holding a quote, backtick, <, >, &, backslash or control character, or longer
// than 128, is refused 400 BAD_ID BEFORE any upstream call.
//
// Harness shape from tests/sairnlegacy_reservation_lock.js: the REAL handler,
// a signed session, every upstream call recorded.
//
//   A. hostile ids are refused 400 BAD_ID with ZERO upstream writes, on every
//      one of the 36 SAIRNlegacy data resources.
//   B. every id shape the app really produces is accepted: newId() output for
//      every prefix in sairnlegacy.html, every seed literal in the file, and
//      the derived AC- / ACX- aftercare keys.
//   X. ABLATION: with the check removed from a copy of the handler, arm A's
//      first id reaches an upstream write -- the gap was real.
'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const Module = require('module');

const ROOT = path.join(__dirname, '..');
process.env[['SD', 'AUTH', 'SECRET'].join('_')] = ['b72', 'leg', 'id', 'fixture', String(process.pid)].join('-');
const LEG = require(path.join(ROOT, 'api/_resources/sairnlegacy.js'));
const LEG_DATA = LEG.resources.filter((r) => r !== 'leg_settings');
const HANDLER = path.join(ROOT, 'api/sd-data.js');
const HTML = fs.readFileSync(path.join(ROOT, 'sairnlegacy.html'), 'utf8');
const LICENSE_KEY = 'k';
const LIC_HASH = crypto.createHash('sha256').update(LICENSE_KEY).digest('hex');
const TOKEN = require(path.join(ROOT, 'api/_lib/auth')).signSessionToken({
  app: 'sairnlegacy', employee_id: 'emp-1', role: 'owner', license_hash: LIC_HASH });

let passed = 0, failed = 0;
function arm(name, ok, detail) {
  if (ok) { passed++; console.log('  ok   ' + name); }
  else { failed++; console.log('  FAIL ' + name + (detail ? '  -- ' + detail : '')); }
}

function loadHandler(src) {
  delete require.cache[require.resolve(HANDLER)];
  if (!src) return require(HANDLER);
  const m = new Module(HANDLER, module);
  m.filename = HANDLER;
  m.paths = Module._nodeModulePaths(path.dirname(HANDLER));
  m._compile(src, HANDLER);
  return m.exports;
}

async function call(handler, resource, payload) {
  const out = { code: null, body: null, writes: 0 };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; }, setHeader() {} };
  const U = ['SUPABASE', 'URL'].join('_'), K = ['SUPABASE', 'SERVICE', 'ROLE', 'KEY'].join('_');
  const saved = [process.env[U], process.env[K]];
  const realFetch = global.fetch;
  process.env[U] = 'https://stub.invalid';
  process.env[K] = ['stub', 'fixture', 'value'].join('-');
  let first = true;
  global.fetch = async (url, init) => {
    if (first) { first = false; return { ok: true, status: 200, json: async () => [{ status: 'active', app_id: null }] }; }
    if (/_employee_auth\?/.test(String(url)) && /select=active/.test(String(url))) {
      return { ok: true, status: 200, json: async () => [{ active: true }] };
    }
    const method = (init && init.method) || 'GET';
    if (method !== 'GET') out.writes += 1;
    return { ok: true, status: 200, json: async () => [] };
  };
  try {
    await handler({ method: 'POST', headers: { authorization: 'Bearer ' + LICENSE_KEY, 'x-sd-auth': TOKEN },
                    body: { action: 'write', resource, app_id: 'sairnlegacy', payload } }, res);
  } finally {
    global.fetch = realFetch;
    [U, K].forEach((n, i) => { if (saved[i] === undefined) delete process.env[n]; else process.env[n] = saved[i]; });
  }
  return out;
}

const HOSTILE = ["KO-1');alert(1);//", 'KO-1"><img src=x onerror=alert(1)>', 'a`b', 'x'.repeat(129), 'a\\b', 'line\nbreak', "O'Brien"];

(async () => {
  const handler = loadHandler();

  // A: on every data resource, every hostile id -> 400 BAD_ID, nothing written.
  // A resource whose write an EARLIER gate refuses (leg_cremations: the
  // countersignature lock answers 403 first) never reaches the id check; it
  // still must write nothing, and it is named rather than counted as BAD_ID.
  const failsA = [], earlier = new Set();
  for (const r of LEG_DATA) {
    if (r === 'leg_aftercare') continue; // its id is derived; covered in A2
    for (const id of HOSTILE) {
      const o = await call(handler, r, { id, case_id: 'CS-1-1', checkin_type: 'other' });
      const badId = o.code === 400 && o.body && o.body.error && o.body.error.code === 'BAD_ID';
      if (o.writes !== 0 || o.code < 400) failsA.push(r + ' ' + JSON.stringify(id) + ' -> ' + o.code + ' writes ' + o.writes);
      else if (!badId) earlier.add(r + ' (' + o.code + ')');
    }
  }
  arm('A. ' + (LEG_DATA.length - 1) + ' resources x ' + HOSTILE.length + ' hostile ids: every one refused with 0 upstream writes',
    failsA.length === 0, failsA.slice(0, 3).join(' | '));
  arm('A1. every resource that reaches the id check answers BAD_ID; only the countersigned leg_cremations is refused earlier',
    Array.from(earlier).join(',') === 'leg_cremations (403)', Array.from(earlier).join(', '));
  const ac = await call(handler, 'leg_aftercare', { id: 'ignored', case_id: "CS-1');alert(1);//", checkin_type: '1-WEEK' });
  arm('A2. leg_aftercare: a hostile case_id cannot smuggle markup through the DERIVED key (checked after the rewrite)',
    ac.code === 400 && ac.body.error.code === 'BAD_ID' && ac.writes === 0, JSON.stringify([ac.code, ac.writes]));

  // B: every id shape the app produces passes the format check (any later
  // refusal is another gate's, never BAD_ID).
  const prefixes = Array.from(new Set((HTML.match(/newId\('([A-Z]+)'\)/g) || []).map((s) => s.slice(7, -2))));
  const literals = Array.from(new Set((HTML.match(/\bid\s*:\s*'([^']*)'/g) || []).map((s) => s.replace(/^.*'([^']*)'$/, '$1'))));
  const good = prefixes.map((p) => p + '-' + Date.now() + '-' + 999).concat(literals)
    .concat(['AC-CS-1730000000000-12-1-WEEK', 'ACX-CS~11~12-OTHER']);
  const failsB = [];
  for (const id of good) {
    const o = await call(handler, 'leg_keepsakeorders', { id, case_id: 'CS-1-1' });
    if (o.body && o.body.error && o.body.error.code === 'BAD_ID') failsB.push(id);
  }
  arm('B. ' + good.length + ' real id shapes (' + prefixes.length + ' newId prefixes, ' + literals.length + ' seed literals, 2 aftercare keys) are NOT refused as BAD_ID',
    prefixes.length > 30 && failsB.length === 0, failsB.slice(0, 5).join(', '));
  const acGood = await call(handler, 'leg_aftercare', { id: 'x', case_id: 'CS-1730000000000-12', checkin_type: '1 week' });
  arm('B2. a normal aftercare check-in is not refused as BAD_ID', !(acGood.body && acGood.body.error && acGood.body.error.code === 'BAD_ID'),
    JSON.stringify(acGood.body).slice(0, 160));

  // P (hank b73, cc b58 stress L2a): "Paid" is a fact about the payments.
  const inv = (payments, status) => ({ id: 'IV-1730000000000-1', case_id: 'CS-1-1',
    line_items: [{ label: 'Basic', amount: 5000 }], payments, status });
  const p1 = await call(handler, 'leg_invoices', inv([], 'Paid'));
  arm('P1. a $5,000 invoice filed Paid with NO payment: 409 INVOICE_NOT_PAID, 0 writes',
    p1.code === 409 && p1.body.error.code === 'INVOICE_NOT_PAID' && p1.writes === 0, JSON.stringify([p1.code, p1.writes]));
  const p2 = await call(handler, 'leg_invoices', inv([{ amount: 4999.99, source: 'Cash' }], 'Paid'));
  arm('P2. one cent short is still not Paid', p2.code === 409 && p2.writes === 0, JSON.stringify([p2.code, p2.writes]));
  const p3 = await call(handler, 'leg_invoices', inv([{ amount: 3000, source: 'Cash' }, { amount: 2000, source: 'Check' }], 'Paid'));
  arm('P3. CONTROL: paid in full across two payments is accepted', p3.code === 200 && p3.writes > 0, JSON.stringify([p3.code, p3.writes]));
  const p4 = await call(handler, 'leg_invoices', inv([{ amount: 1000, source: 'Cash' }], 'Partial'));
  arm('P4. CONTROL: a Partial invoice is not held to the Paid rule', p4.code === 200 && p4.writes > 0, JSON.stringify([p4.code, p4.writes]));

  // X: the same hostile write against the handler with the check cut out.
  const src = fs.readFileSync(HANDLER, 'utf8');
  const cut = src.replace(/if \(String\(payload\.id\)\.length > 128 \|\|[^\n]*\{\n[^\n]*BAD_ID[^\n]*\n\s*return;\n\s*\}/, '');
  arm('X. the check was found and cut for the ablation', cut !== src);
  const old = await call(loadHandler(cut), 'leg_keepsakeorders', { id: HOSTILE[0], case_id: 'CS-1-1' });
  arm('X. ABLATION: without the check the hostile id reaches an upstream write', old.writes > 0 && old.code === 200, JSON.stringify([old.code, old.writes]));
  loadHandler();

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  process.exit(failed ? 1 : 0);
})();
