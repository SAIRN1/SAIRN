// api/b30-cap-per-action.test.js
//
// Run:  node api/b30-cap-per-action.test.js
//
// ── THE CONCEPT, STATED BEFORE THE CODE ─────────────────────────────────────
// A payload cap belongs to the (resource, action) PAIR that writes, because
// "which verb writes" is a fact about the handler and "how big a row may be"
// is a fact about the table -- and api/sd-data.js's cap gate asked NEITHER. It
// read `if (action === 'write')`.
//
// ── THE DEFECT, WHICH IS cody's OWN b29 FINDING ────────────────────────────
// 37 declared verbs across 77 resources bypassed the cap entirely.
// `rf_invoices` carries `rfinv_data_size <= 262144` and writes through
// `issue`, `add_payment`, `reconcile_claim` and `gl_export`, so it was not
// under-capped, IT WAS UNCAPPED: a 10MB payload reached Postgres and came back
// as an opaque constraint error. Recorded in
// docs/2026-10-20-cody-b29-notes.md §3.1 and routed there rather than closed,
// because closing it without measuring risked refusing payloads that work.
//
// ── WHAT THIS SUITE IS ACTUALLY FOR ────────────────────────────────────────
// Two things, and the second matters more than the first.
//
//   1. THE CAP NOW FIRES on a declared verb, and the per-(resource,action)
//      entry wins over the per-resource one. Arms G*.
//   2. IT DID NOT BREAK rt_routes. A 200-stop upsert is ~124KB of LEGITIMATE
//      payload -- `api/_lib/routes.js` permits 200 stops (:464) with
//      500-character addresses (:470) -- and would have been refused at the
//      64KB default. Arms R*. A security fix that refuses a working client is
//      the thing b29 declined to ship blind.
//
// And M1, which is the honest arm: the class map in api/_resources/index.js is
// a DECLARATION, and M1 runs the derivation that was rejected and reports
// every disagreement in both directions rather than asserting either side is
// right.
//
// No database is touched. The real dispatcher runs against a recorded
// PostgREST stand-in.
//
// Exit: 0 all arms passed · 1 an arm FAILED

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['b30', 'cap', 'per', 'action', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const fs = require('fs');
const path = require('path');
const { signSessionToken } = require('./_lib/auth');
const registry = require('./_resources/index.js');

const HASH = 'b30-cap-hash';
const KEY = 'KEY-FOR-' + HASH;
const SD_DATA = path.join(__dirname, 'sd-data.js');

let pass = 0, fail = 0;
const failed = [];
function ok(l) { pass++; console.log('  ok    ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l);
  if (why) console.log('        ' + String(why).slice(0, 900));
}
function is(cond, label, detail) { if (cond) ok(label); else bad(label, detail); }
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function eCode(res) { return (res.body && res.body.error && res.body.error.code) || ''; }
function eMsg(res) { return (res.body && res.body.error && res.body.error.message) || ''; }

function pgMock(calls) {
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    calls.push({ url: u, method: method });
    if (/_employee_auth/.test(u)) {
      const m = u.match(/employee_id=eq\.([^&]+)/);
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: m ? decodeURIComponent(m[1]) : 'emp-1',
          role: 'owner', active: true }] };
    }
    if (/rt_routes/.test(u) && method === 'POST') {
      return { ok: true, status: 200, json: async () => [
        { id: 'ROUTE-1', license_hash: HASH, app_id: 'stonedesk',
          assignee_id: 'EMP-1', route_date: '2031-01-02' }] };
    }
    if (method === 'POST' || method === 'PATCH') {
      let parsed = null;
      try { parsed = JSON.parse(init.body); } catch (e) { parsed = { id: 'x' }; }
      return { ok: true, status: 200,
               json: async () => (Array.isArray(parsed) ? parsed : [parsed]) };
    }
    return { ok: true, status: 200, json: async () => [
      { id: 'row-1', license_hash: HASH, job_id: 'JOB-1', claim_id: 'CLM-1',
        invoice_id: 'INV-1', data: {} }] };
  };
}

function loadHandler(calls, app) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: app })
    }
  };
  global.fetch = pgMock(calls);
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function call(app, resource, action, role, payload) {
  const calls = [];
  const h = loadHandler(calls, app);
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer ' + KEY,
      'x-sd-auth': signSessionToken({
        app: app, employee_id: 'emp-1', role: role, license_hash: HASH })
    },
    body: { action: action, resource: resource, payload: payload }
  }, res);
  return { res: res, calls: calls };
}

function bytesOf(p) { return Buffer.byteLength(JSON.stringify(p), 'utf8'); }

// Grow a payload by MEASUREMENT until its JSON encoding crosses a target. The
// rest of the payload contributes bytes too, so arithmetic on the filler
// length alone would sit a few bytes off the boundary the arm claims to test.
function sizedTo(base, targetBytes, fillerKey) {
  let lo = 0, hi = targetBytes + 8192;
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2);
    const p = Object.assign({}, base);
    p[fillerKey] = 'x'.repeat(mid);
    if (bytesOf(p) < targetBytes) lo = mid + 1; else hi = mid;
  }
  const out = Object.assign({}, base);
  out[fillerKey] = 'x'.repeat(lo);
  return out;
}

const TOO_LARGE = (res) => res.statusCode === 413
  && eCode(res) === 'PAYLOAD_TOO_LARGE';

(async function main() {
  // ═══════════════════════════════════════════════════════════════════════
  section('G. THE GATE NOW FIRES ON A DECLARED VERB');
  // ═══════════════════════════════════════════════════════════════════════

  // G1 IS THE REPRODUCTION, and it is the exact example b29's notes named:
  // rf_invoices writes through `issue` and its row cap is 262144, so before
  // b30 a payload of ANY size reached Postgres.
  {
    const p = sizedTo({ id: 'INV-1', job_id: 'JOB-1' }, 300 * 1024, 'blob');
    const { res } = await call('sairnroofing', 'rf_invoices', 'issue',
      'owner', p);
    is(TOO_LARGE(res),
       'G1. THE REPRODUCTION: a ' + bytesOf(p) + '-byte `issue` on rf_invoices '
       + '-> 413. Before b30 the cap read `action === "write"` and this verb '
       + 'bypassed it entirely',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // G2. THE MESSAGE NAMES THE PAIR. A reader told only the resource would
  // recompress against the wrong budget on a sibling verb -- rt_routes/upsert
  // and rt_routes/write have different caps by design.
  {
    const p = sizedTo({ id: 'INV-1', job_id: 'JOB-1' }, 300 * 1024, 'blob');
    const { res } = await call('sairnroofing', 'rf_invoices', 'issue',
      'owner', p);
    is(/rf_invoices\/issue/.test(eMsg(res)) && /65536/.test(eMsg(res)),
       'G2. the 413 names `rf_invoices/issue` and the cap that applied',
       eMsg(res));
  }

  // G3. EVERY OTHER DECLARED VERB TOO, not just the one b29 named. A
  // compute-only verb is capped as well -- the gate is fail-closed on the verb
  // so that a misclassification in ACTION_CLASS costs a comment, not a hole.
  for (const [app, resource, action] of [
    ['sairnroofing', 'rf_invoices', 'gl_export'],
    ['sairnroofing', 'rf_claims', 'assess_damage'],
    ['stonedesk', 'slabs', 'reserve']
  ]) {
    const p = sizedTo({ id: 'X-1', job_id: 'JOB-1', claim_id: 'CLM-1' },
      300 * 1024, 'blob');
    const { res } = await call(app, resource, action, 'owner', p);
    is(TOO_LARGE(res),
       'G3[' + resource + '/' + action + ']. a 300KB payload on a declared '
       + 'verb -> 413',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // G4. AND `read` IS NOT CAPPED. A read payload is a FILTER; it writes no row
  // and capping it would be a new restriction on something that was never the
  // defect. This arm is what stops the fix being widened past its reason.
  {
    const p = sizedTo({ job_id: 'JOB-1' }, 200 * 1024, 'blob');
    const { res } = await call('sairnroofing', 'rf_invoices', 'read',
      'owner', p);
    is(!TOO_LARGE(res),
       'G4. a ' + bytesOf(p) + '-byte READ is NOT refused for size -- the cap '
       + 'covers every verb EXCEPT read',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // G5. THE PER-RESOURCE CAP STILL WINS where there is no pair entry, on a
  // DECLARED VERB. b28 and b29 gave six resources their own caps and those
  // applied only to `write`; step 2 of the resolution is why they now apply to
  // every verb of the same resource.
  {
    const p = sizedTo({ id: 'AG-1', claim_id: 'CLM-1' }, 300 * 1024, 'blob');
    const { res } = await call('sairnroofing', 'rf_claim_agreements',
      'agreement_status', 'owner', p);
    is(!TOO_LARGE(res),
       'G5. a 300KB `agreement_status` is NOT refused -- rf_claim_agreements '
       + 'carries a 1572864 per-resource cap and it now reaches every verb',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // ═══════════════════════════════════════════════════════════════════════
  section('R. rt_routes -- THE REGRESSION THIS FIX COULD HAVE SHIPPED');
  // ═══════════════════════════════════════════════════════════════════════

  // R1. A FULL 200-STOP ROUTE. ~124KB of legitimate payload, which the 64KB
  // default would have refused. This is why the per-(resource,action) entry
  // exists and why b29 declined to close the gap without measuring.
  const bigRoute = {
    app_id: 'stonedesk', assignee_id: 'EMP-1', route_date: '2031-01-02',
    stops: Array.from({ length: 200 }, (_, i) => ({
      address: (i + 1) + ' ' + 'A'.repeat(480) + ' Street',
      job_ref: 'JOB-' + i, status: 'pending'
    }))
  };
  {
    const { res } = await call('stonedesk', 'rt_routes', 'upsert', 'owner',
      bigRoute);
    is(!TOO_LARGE(res),
       'R1. a full 200-stop upsert (' + bytesOf(bigRoute) + ' bytes) is NOT '
       + 'refused for size -- api/_lib/routes.js permits exactly this',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // R2. AND IT IS NOT UNCAPPED EITHER. Past the derived ceiling it refuses,
  // so the pair entry is a cap and not an exemption.
  {
    const over = sizedTo(bigRoute, 200 * 700 + 32768 + 1, 'notes_filler');
    const { res } = await call('stonedesk', 'rt_routes', 'upsert', 'owner',
      over);
    is(TOO_LARGE(res) && /rt_routes\/upsert/.test(eMsg(res)),
       'R2. past the derived ceiling (' + bytesOf(over) + ' bytes) -> 413 '
       + 'naming rt_routes/upsert -- a cap, not an exemption',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // R3. `reorder` IS DELIBERATELY ABSENT from the pair table -- it carries a
  // `seq` array of ids, not stops -- so it falls to the default. Asserted
  // rather than left implicit, because "we forgot reorder" and "reorder does
  // not need it" look identical in a table.
  {
    const p = sizedTo({ app_id: 'stonedesk', assignee_id: 'EMP-1',
      route_date: '2031-01-02', seq: ['a', 'b'] }, 100 * 1024, 'blob');
    const { res } = await call('stonedesk', 'rt_routes', 'reorder', 'owner', p);
    is(TOO_LARGE(res) && /65536/.test(eMsg(res)),
       'R3. `reorder` is not in the pair table and falls to 64KB -- a 100KB '
       + 'reorder is refused',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // ═══════════════════════════════════════════════════════════════════════
  section('C. THE CLASS MAP -- completeness, and its own honesty');
  // ═══════════════════════════════════════════════════════════════════════

  // C1. EVERY DECLARED VERB IS CLASSIFIED. The assertion lives at module load
  // in api/_resources/index.js and throws; this arm proves the throw is real
  // rather than written, by checking the loaded map covers the loaded
  // registry. A load-time assertion nobody exercises is a comment.
  {
    const verbs = new Set();
    for (const r of Object.keys(registry.EXTRA_ACTIONS)) {
      registry.EXTRA_ACTIONS[r].forEach((v) => verbs.add(v));
    }
    const unclassified = [...verbs].filter((v) =>
      registry.ACTION_CLASS[v] !== 'write-class'
      && registry.ACTION_CLASS[v] !== 'compute-only').sort();
    is(verbs.size >= 30 && unclassified.length === 0,
       'C1. all ' + verbs.size + ' declared verbs are classified write-class '
       + 'or compute-only',
       'unclassified: ' + JSON.stringify(unclassified));
  }

  // C2. AND NO STALE ENTRY. A verb classified here and since removed from
  // every registry is dead weight; the load-time assertion deliberately does
  // NOT throw on it, because refusing to load over a stale entry would make
  // deleting a resource fail. Reported here instead.
  {
    const verbs = new Set();
    for (const r of Object.keys(registry.EXTRA_ACTIONS)) {
      registry.EXTRA_ACTIONS[r].forEach((v) => verbs.add(v));
    }
    const stale = Object.keys(registry.ACTION_CLASS)
      .filter((v) => !verbs.has(v)).sort();
    is(stale.length === 0,
       'C2. no ACTION_CLASS entry names a verb no registry declares',
       'stale: ' + JSON.stringify(stale));
  }

  // C3. `read` AND `write` ARE NOT IN THE CLASS MAP. They are universal and
  // api/_resources/index.js already throws if a module declares either as an
  // extra verb; an entry here would be a second, disagreeing place to learn
  // what `write` is.
  is(registry.ACTION_CLASS.read === undefined
     && registry.ACTION_CLASS.write === undefined,
     'C3. the universal verbs are absent from the class map',
     'read=' + registry.ACTION_CLASS.read
       + ' write=' + registry.ACTION_CLASS.write);

  // ── M1. THE DERIVATION THAT WAS REJECTED, RUN ANYWAY ───────────────────
  // The class map is a DECLARATION. The honest first attempt was to derive it
  // by scanning api/sd-data.js for each verb's branch and testing whether the
  // span contains a write method -- and that scan is NOT trustworthy: it
  // reported `consolidate` as having no branch at all, and `reserve` and
  // `release_retainage` as compute-only, because the span ends at the next
  // `if (resource ===` boundary and several branches put the write after a
  // nested resource test.
  //
  // SO THIS ARM REPORTS DISAGREEMENTS IN BOTH DIRECTIONS AGAINST A PINNED
  // SET, rather than asserting either side is right. A new disagreement is a
  // finding -- either the scan has a new blind spot or a verb's class changed
  // -- and a disagreement that DISAPPEARS is a finding too, because it means
  // the pin is stale. Neither can happen quietly.
  const KNOWN_SCAN_DISAGREEMENTS = [
    'consolidate', 'release_retainage', 'reserve'
  ];
  {
    const { stripJs } = require('../tests/lib/strip_comments.js');
    const src = stripJs(fs.readFileSync(SD_DATA, 'utf8'));
    const lines = src.split('\n');
    const bounds = [];
    lines.forEach((l, i) => {
      if (/action === '[a-z_]+'/.test(l) || /^\s*if \(resource === /.test(l)) {
        bounds.push(i);
      }
    });
    const spanFrom = (i) => {
      const nx = bounds.find((b) => b > i);
      return lines.slice(i, nx === undefined ? lines.length : nx).join('\n');
    };
    const disagree = [];
    for (const verb of Object.keys(registry.ACTION_CLASS)) {
      const re = new RegExp("action === '" + verb + "'");
      let scanWrites = false;
      lines.forEach((l, i) => {
        if (re.test(l)) {
          const sp = spanFrom(i);
          if (/method: '(POST|PATCH|DELETE|PUT)'/.test(sp) || /\/rpc\//.test(sp)) {
            scanWrites = true;
          }
        }
      });
      const declared = registry.ACTION_CLASS[verb] === 'write-class';
      if (declared !== scanWrites) disagree.push(verb);
    }
    disagree.sort();
    is(JSON.stringify(disagree)
       === JSON.stringify(KNOWN_SCAN_DISAGREEMENTS.slice().sort()),
       'M1. the rejected derivation disagrees with the declaration on exactly '
       + 'the ' + KNOWN_SCAN_DISAGREEMENTS.length + ' pinned verbs -- no new '
       + 'blind spot, and no pin that has gone stale',
       'found ' + JSON.stringify(disagree) + '\n        pinned '
         + JSON.stringify(KNOWN_SCAN_DISAGREEMENTS.slice().sort()));
  }

  // ═══════════════════════════════════════════════════════════════════════
  section('S. THE STRUCTURAL ARMS');
  // ═══════════════════════════════════════════════════════════════════════

  // S1. THE GATE'S CONDITION. Every behaviour arm above would still pass if
  // the condition were widened to include `read` as well -- G4 would not,
  // which is why G4 exists -- but none of them can see a revert to
  // `action === 'write'` on a resource whose per-resource cap happens to
  // cover the test payload. The source is what says which verbs are gated.
  {
    const { stripJs } = require('../tests/lib/strip_comments.js');
    const src = stripJs(fs.readFileSync(SD_DATA, 'utf8'));
    is(/if \(action !== 'read'\) \{/.test(src)
       && !/if \(action === 'write'\) \{\s*\n\s*const payloadBytes/.test(src),
       'S1. the cap gate is `if (action !== \'read\')` and the old '
       + '`action === \'write\'` form is gone',
       'new=' + /if \(action !== 'read'\) \{/.test(src));
  }

  // S2. AND THE RESOLUTION IS ONE FUNCTION. Three steps spelled at two call
  // sites is how the law reconcile role list came to refuse an attorney in
  // production for eight batches from a hand-written copy.
  {
    const { stripJs } = require('../tests/lib/strip_comments.js');
    const src = stripJs(fs.readFileSync(SD_DATA, 'utf8'));
    const uses = (src.match(/payloadCapFor\(/g) || []).length;
    is(/function payloadCapFor\(resource, action\)/.test(src) && uses === 2,
       'S2. payloadCapFor() is declared once and called from exactly one site '
       + '(2 source occurrences: the declaration and the call)',
       'occurrences=' + uses);
  }

  // S3. PROTOTYPE SAFETY on the pair table. It is indexed by a key built from
  // a CLIENT-SUPPLIED resource and action, and on a plain literal a crafted
  // pair could resolve to an inherited function, which `payloadBytes > fn`
  // reads as false -- the cap switched off by a name.
  {
    const { stripJs } = require('../tests/lib/strip_comments.js');
    const src = stripJs(fs.readFileSync(SD_DATA, 'utf8'));
    is(/PAYLOAD_CAP_BY_ACTION = Object\.create\(null\)/.test(src),
       'S3. the pair table is built with Object.create(null)',
       'not found');
  }

  // S4. AND THE rt_routes CEILING IS DERIVED, NOT TYPED. A literal 172768
  // would be a number nobody could check; the constants name their source
  // lines in api/_lib/routes.js.
  {
    const { stripJs } = require('../tests/lib/strip_comments.js');
    const src = stripJs(fs.readFileSync(SD_DATA, 'utf8'));
    is(/const RT_STOPS_MAX = 200;/.test(src)
       && /const RT_ROUTE_CAP_BYTES = RT_STOPS_MAX \* RT_STOP_WORST_BYTES \+ 32768;/.test(src),
       'S4. the rt_routes ceiling is RT_STOPS_MAX * RT_STOP_WORST_BYTES + an '
       + 'allowance, not a typed number',
       'not in the expected form');
  }

  // ═══════════════════════════════════════════════════════════════════════
  section('W. rf_invoices: THE ROOM GOES TO `write`, NOT `issue` (b31)');
  // ═══════════════════════════════════════════════════════════════════════

  // W1. A write the TABLE would accept (rfinv_data_size 262144) is not refused
  // for size. At the 64KB default this was a 413.
  {
    const p = sizedTo({ id: 'INV-1', job_id: 'JOB-1' }, 250 * 1024, 'bill_to');
    const { res } = await call('sairnroofing', 'rf_invoices', 'write', 'owner', p);
    is(!TOO_LARGE(res),
       'W1. a ' + bytesOf(p) + '-byte rf_invoices `write` (inside the table '
       + 'ceiling) is NOT refused for size',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // W2. ...and the new number is a ceiling, not an exemption.
  {
    const p = sizedTo({ id: 'INV-1', job_id: 'JOB-1' }, 300 * 1024, 'bill_to');
    const { res } = await call('sairnroofing', 'rf_invoices', 'write', 'owner', p);
    is(TOO_LARGE(res) && /rf_invoices\/write/.test(eMsg(res))
       && /294912/.test(eMsg(res)),
       'W2. a ' + bytesOf(p) + '-byte `write` -> 413 naming rf_invoices/write '
       + 'and 294912',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // W3. `issue` WAS NOT RAISED. Its measured payload is 61-87 bytes, so a
  // loosened cap would be a gate widened for no measured need. This arm is
  // what fails if somebody sets a per-RESOURCE rf_invoices cap instead.
  {
    const p = sizedTo({ invoice_id: 'INV-1' }, 100 * 1024, 'blob');
    const { res } = await call('sairnroofing', 'rf_invoices', 'issue', 'owner', p);
    is(TOO_LARGE(res) && /65536/.test(eMsg(res)),
       'W3. a ' + bytesOf(p) + '-byte `issue` is still refused at 65536',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // W4. THE CEILING IS DERIVED FROM THE TABLE, NOT RETYPED: the SQL's own
  // constraint is read and compared, so a migration that moves it fails here.
  {
    const { stripJs } = require('../tests/lib/strip_comments.js');
    const src = stripJs(fs.readFileSync(SD_DATA, 'utf8'));
    const sql = fs.readFileSync(path.join(__dirname, '..', 'sql',
      'sairnroofing_billing_schema.sql'), 'utf8');
    const m = /rfinv_data_size check \(octet_length\(data::text\) <= (\d+)\)/.exec(sql);
    const c = /const RF_INVOICE_DATA_CEILING = (\d+);/.exec(src);
    is(m && c && m[1] === c[1]
       && /const RF_INVOICE_WRITE_CAP_BYTES = RF_INVOICE_DATA_CEILING \+ 32768;/.test(src),
       'W4. the write cap is the SQL constraint (' + (m && m[1]) + ') plus a '
       + 'stated allowance, not a typed number',
       'sql=' + (m && m[1]) + ' code=' + (c && c[1]));
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed'
    + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
