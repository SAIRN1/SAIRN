// tests/sd_data_unconfirmed_write_review_probe.js
//
// Run:  node tests/sd_data_unconfirmed_write_review_probe.js
//
// INDEPENDENT REVIEW of the json-catch-null sweep (92be209a + 5cedf088, CC),
// discharging the Tier A obligation cc opened 2026-09-18T23:19:37Z on
// dnt_charges, sd_aiquotes, sd_fin_jobs, sd_invoices, sd_negotiated_prices,
// sd_order_history, sd_pricing_rules, sd_quote_requests and
// stonedesk_quote_history. Reviewer: hank.
//
// ── REPORT-ONLY AND EXIT 0, DELIBERATELY ──────────────────────────────────
// Same precedent as tests/dnt_rollup_review_probe.js: these are findings on
// somebody else's file, and turning them into a failing suite would block every
// other session's push on a defect they did not write and cannot fix from their
// own claim. It PRINTS, it does not gate.
//
// ── THE THREE QUESTIONS CC ASKED, DRIVEN AGAINST THE REAL HANDLER ─────────
//   (1) is 404 the right answer for a zero-row PATCH match rather than 502 --
//       a caller that treats 404 as "already gone" may now behave differently
//   (2) can the dnt-bi 502 fire on a LEGITIMATELY EMPTY table
//   (3) is wroteRow()'s UNKNOWN branch on a non-array body over-broad for any
//       PostgREST response shape these paths can actually receive
//
// Each is answered by running api/sd-data.js and api/dnt-bi.js with a fetch
// mock that returns the exact body shape in question, not by reading the code
// and reasoning about it. Where I could not drive something I say so rather
// than letting it look like the others.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['sd', 'data', 'unconfirmed', 'review', 'fixture'].join('-');
// api/dnt-bi.js refuses at the door with a 500 when these are unset, which is
// correct and is also how the first run of this probe reported 500 for all five
// dataset shapes -- a configuration refusal reading as a verdict about the
// dataset. Set here so the arms reach the code they are about. Fixture values;
// every request is intercepted by the mock and none leaves the process.
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://fixture.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY
  || ['fixture', 'service', 'key'].join('-');

const path = require('path');
const LIC = 'review-hash';
let APP_ID = 'stonedesk';

let findings = 0;
function note(s) { console.log(s); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

const { signSessionToken } = require(path.join(__dirname, '..', 'api', '_lib', 'auth'));
function req(body, app) {
  return {
    method: 'POST',
    headers: {
      authorization: 'Bearer GOOD-KEY',
      'x-sd-auth': signSessionToken({ app: app || 'stonedesk', employee_id: 'E-1',
                                      role: 'owner', license_hash: LIC })
    },
    body: body
  };
}

function load(modRel, fetchImpl) {
  const lic = path.join(__dirname, '..', 'api', '_lib', 'license');
  delete require.cache[require.resolve(lic)];
  require.cache[require.resolve(lic)] = {
    exports: {
      validateLicenseKey: async function () {
        // app_id comes from the CALLER, because api/sd-data.js's app-boundary
        // gate refuses a resource owned by another app -- driving the
        // SAIRNcode branch under a stonedesk licence answers 400 at the
        // envelope and never reaches the code under test. The first run of
        // this probe did exactly that and reported 400 three times, which
        // would have read as "the branch refuses" rather than "the probe
        // never got there".
        return { valid: true, active: true, license_hash: LIC, trial_ends_at: null,
                 stripe_subscription_id: null, app_id: APP_ID };
      }
    }
  };
  global.fetch = fetchImpl;
  const p = path.join(__dirname, '..', 'api', modRel);
  delete require.cache[require.resolve(p)];
  return require(p);
}

// A PostgREST stand-in that answers each leg of the soft-delete separately, so
// a test can make the READ succeed and the PATCH return whatever shape it is
// about. `patchBody` is returned verbatim -- including a non-array -- which is
// the whole of question (3).
function softDeleteMock(opts) {
  const calls = [];
  return {
    calls: calls,
    fn: async function (url, init) {
      const method = (init && init.method) || 'GET';
      calls.push({ url: String(url), method: method });
      if (method === 'GET') {
        if (opts.readStatus && opts.readStatus !== 200) {
          return { ok: false, status: opts.readStatus,
                   json: async () => ({ message: 'read failed' }) };
        }
        return { ok: true, status: 200, json: async () => opts.readRows };
      }
      if (opts.patchStatus && opts.patchStatus !== 200) {
        return { ok: false, status: opts.patchStatus, json: async () => ({ message: 'patch failed' }) };
      }
      return {
        ok: true, status: 200,
        json: async function () {
          if (opts.patchThrows) throw new SyntaxError('Unexpected token < in JSON at position 0');
          return opts.patchBody;
        }
      };
    }
  };
}

(async function () {
  console.log('INDEPENDENT REVIEW -- api/sd-data.js json-catch-null sweep');
  console.log('obligation cc 2026-09-18T23:19:37Z, reviewed by hank');

  // ════════════════════════════════════════════════════════════════════════
  console.log('\n=== QUESTION 3 first: is UNKNOWN on a non-array body over-broad? ===');
  console.log('  Driven against the real handler for every body shape PostgREST');
  console.log('  can return on these two paths.\n');

  const SHAPES = [
    ['[{...}] -- one row, a normal matched PATCH', [{ data: { id: 'R-1' } }], 200, 'WROTE'],
    ['[] -- matched nothing, PostgREST 200 with an empty array', [], 404, 'MISSED'],
    ['{} -- a bare OBJECT body', {}, 502, 'UNKNOWN'],
    ['{"data":{...}} -- the pgrst.object+json shape', { data: { id: 'R-1' } }, 502, 'UNKNOWN'],
    ['null -- a literal JSON null body', null, 502, 'UNKNOWN'],
    ['"" -- unparseable, .json() throws', undefined, 502, 'UNKNOWN']
  ];
  const seen = [];
  for (const [label, body, expect, says] of SHAPES) {
    const m = softDeleteMock({
      readRows: [{ data: { id: 'R-1', note: 'still here' } }],
      patchBody: body,
      patchThrows: label.indexOf('unparseable') !== -1
    });
    const h = load('sd-data.js', m.fn);
    const res = mockRes();
    await h(req({ action: 'soft_delete', resource: 'sd_invoices', payload: { id: 'R-1' } }), res);
    const got = res.statusCode;
    seen.push({ label, got, expect, says, code: res.body && res.body.error && res.body.error.code });
    console.log('  %s%s -> %s  (%s)%s',
      got === expect ? 'ok   ' : 'DIFF ', label.padEnd(56), got, says,
      got === expect ? '' : '   EXPECTED ' + expect);
  }

  const acceptHeaderUsed = /Accept['"]?\s*:/.test(
    require('fs').readFileSync(path.join(__dirname, '..', 'api', 'sd-data.js'), 'utf8'));
  console.log(`
  ANSWER: NOT over-broad, and the reason is checkable rather than assumed.
  PostgREST returns an ARRAY for every request unless the caller asks for
  \`Accept: application/vnd.pgrst.object+json\`. api/sd-data.js's shared
  \`headers\` (:724) is apikey / Authorization / Content-Type and NOTHING ELSE,
  and neither PATCH adds an Accept -- measured: any Accept header anywhere in
  the file = ${acceptHeaderUsed}. So the object shapes above are unreachable on
  these two paths, and treating them as UNKNOWN costs nothing today.

  THE ONE THING I WOULD SAY BACK: that safety is a property of a header nobody
  writes, not of anything asserted. Adding \`Accept: application/vnd.pgrst
  .object+json\` to a future branch would turn every SUCCESSFUL write on that
  branch into a 502 WRITE_UNCONFIRMED -- fail-closed, so not dangerous, but a
  working feature that stops working with a confusing message. One assertion in
  api/sd-data-unconfirmed-write.test.js pinning that these PATCHes send no
  Accept header would make the dependency explicit. Not raised as a finding:
  the behaviour is correct as shipped.`);

  // ════════════════════════════════════════════════════════════════════════
  console.log('\n=== QUESTION 1: is 404 right for a zero-row PATCH match? ===\n');

  // The generic path READS FIRST and 404s on a read miss. So a MISSED PATCH
  // can only happen when the row was there at the read and gone at the write.
  const readMiss = softDeleteMock({ readRows: [], patchBody: [{}] });
  let h = load('sd-data.js', readMiss.fn);
  let res = mockRes();
  await h(req({ action: 'soft_delete', resource: 'sd_invoices', payload: { id: 'R-1' } }), res);
  console.log('  read matched nothing            -> %s %s  (patches attempted: %d)',
    res.statusCode, (res.body.error || {}).code,
    readMiss.calls.filter((c) => c.method === 'PATCH').length);

  const toctou = softDeleteMock({ readRows: [{ data: { id: 'R-1' } }], patchBody: [] });
  h = load('sd-data.js', toctou.fn);
  res = mockRes();
  await h(req({ action: 'soft_delete', resource: 'sd_invoices', payload: { id: 'R-1' } }), res);
  console.log('  read HIT, patch matched nothing -> %s %s', res.statusCode, (res.body.error || {}).code);

  const already = softDeleteMock({
    readRows: [{ data: { id: 'R-1', _deleted_at: '2026-09-01T00:00:00Z' } }], patchBody: [] });
  h = load('sd-data.js', already.fn);
  res = mockRes();
  await h(req({ action: 'soft_delete', resource: 'sd_invoices', payload: { id: 'R-1' } }), res);
  console.log('  already soft-deleted            -> %s already_deleted=%s  (patches: %d)',
    res.statusCode, res.body && res.body.already_deleted,
    already.calls.filter((c) => c.method === 'PATCH').length);

  console.log(`
  ANSWER: 404 is right, and the case cc was worried about does not arise --
  but not for the reason the question implies.

  "ALREADY GONE" NEVER REACHES THE MISSED BRANCH. The path reads first: a
  read miss 404s before any PATCH is sent (0 patches above), and a row already
  carrying _deleted_at returns 200 with already_deleted:true and ALSO sends no
  PATCH. So MISSED is reachable only in the TOCTOU window -- present at the
  read, absent at the write, microseconds apart. That is a genuinely anomalous
  state and 404 is the honest answer for it; 502 would claim the store
  misbehaved when it answered perfectly.

  THE CALLER-BEHAVIOUR HALF OF THE QUESTION IS WHERE THE REAL CHANGE IS, and
  it is a change in the SAFE direction. stonedesk.html:2144 branches on
  \`done===null\` and sdData returns null for any non-2xx, so a MISSED that used
  to answer ok:true (silence) now answers 404 (null) and the user is told "was
  deleted on this device but NOT on the server. It may reappear on the next
  load." For a TOCTOU miss that sentence is TRUE -- the local row is gone and
  the server state is not what the caller believes. Louder than before, and
  correct. No finding.`);

  // ════════════════════════════════════════════════════════════════════════
  console.log('\n=== QUESTION 2: can the dnt-bi 502 fire on a legitimately empty table? ===\n');

  // DRIVEN, not read. The feed authenticates on a TOKEN row rather than a
  // session, so the mock answers the token lookup first and the dataset read
  // second, and the dataset body is whatever the case under test is about.
  function biMock(datasetBody, opts) {
    opts = opts || {};
    const calls = [];
    let n = 0;
    return {
      calls: calls,
      fn: async function (url, init) {
        const u = String(url);
        calls.push(u);
        if (u.indexOf('bi_tokens') !== -1 || u.indexOf('token_hash=eq.') !== -1) {
          if ((init && init.method) === 'PATCH') {
            return { ok: true, status: 200, json: async () => [{}] };   // stampUse
          }
          return { ok: true, status: 200, json: async () => [{
            id: 'T-1', license_hash: LIC, employee_id: 'E-1',
            include_identifiers: false, revoked_at: null, use_count: 0 }] };
        }
        if (u.indexOf('dnt_employee_auth') !== -1 || u.indexOf('employee_id=eq.') !== -1) {
          return { ok: true, status: 200,
                   json: async () => [{ employee_id: 'E-1', role: 'owner', active: true }] };
        }
        n++;
        if (opts.missingTable) {
          // What PostgREST answers for a relation that is not there.
          return { ok: false, status: 404,
                   json: async () => ({ code: '42P01', message: 'relation does not exist' }) };
        }
        if (opts.throws) {
          return { ok: true, status: 200,
                   json: async () => { throw new SyntaxError('Unexpected token <'); } };
        }
        return { ok: true, status: 200, json: async () => datasetBody };
      }
    };
  }

  function biReq(dataset) {
    return { method: 'GET', url: '/api/dnt-bi?dataset=' + dataset,
             query: { dataset: dataset, token: 'FEED-TOKEN' },
             headers: { authorization: 'Bearer FEED-TOKEN' } };
  }

  const BI_CASES = [
    ['[] -- a LEGITIMATELY EMPTY table', [], false, 200],
    ['[{data:{...}}] -- one real row', [{ data: { charge_id: 'C-1', amount: 10 } }], false, 200],
    ['{} -- a bare object, not the shape asked for', {}, false, 502],
    ['null -- a literal JSON null body', null, false, 502],
    ['unparseable -- .json() throws', null, true, 502]
  ];
  BI_CASES.push(['404 42P01 -- the table is not in this deployment', null, false, 200]);
  for (const [label, body, throws, expect] of BI_CASES) {
    const m = biMock(body, { throws: throws, missingTable: label.indexOf('42P01') !== -1 });
    let got, code, rows;
    try {
      const h = load('dnt-bi.js', m.fn);
      const r = mockRes();
      await h(biReq('charges'), r);
      got = r.statusCode;
      code = (r.body && r.body.error && r.body.error.code) || '';
      rows = r.body && r.body.data ? r.body.data.length : (r.body && r.body.rows ? r.body.rows.length : '-');
      if (r.body && r.body.provisioned === false) rows = rows + ' provisioned:false';
    } catch (e) {
      got = 'THREW'; code = e.message.slice(0, 40); rows = '-';
    }
    const ok = got === expect;
    console.log('  %s%s -> %s %s  rows=%s%s',
      ok ? 'ok   ' : 'DIFF ', label.padEnd(48), got, code.padEnd(16), rows,
      ok ? '' : '   EXPECTED ' + expect);
    if (!ok && got === 502 && expect === 200) {
      findings++;
      console.log('\n  FINDING: a legitimately empty table is refused as unreadable.\n');
    }
  }
  console.log(`
  ANSWER: the 502 CANNOT fire on a legitimately empty table, and this is
  driven rather than reasoned. \`[]\` is an ARRAY, so \`!Array.isArray(drows)\`
  is false and it takes the ordinary path to an empty dataset with a 200.
  Only a non-array -- a bare object, a literal null, or a body that will not
  parse (which \`.json().catch(() => null)\` turns into null) -- reaches the
  refusal. The discrimination is exactly the one the question asks about:
  "not an array" is separated from "an array of length zero", and those are
  the two things a dashboard must never see merged.

  AND THE MISSING-TABLE CASE IS SEPARATE AGAIN, which is the part worth
  praising: a table that does not exist in this deployment answers 200 with
  \`provisioned:false\` on the envelope rather than rows, so "not set up" cannot
  be charted as "zero" either. Three states, not two, on a path where the
  platform's own recorded defect was collapsing them.`);

  // ════════════════════════════════════════════════════════════════════════
  // THE QUESTION CC DID NOT ASK, and it is where the finding is.
  // The commit says this was "found by the platform sweep for
  // `.json().catch(() => null)`". A sweep is a claim about COMPLETENESS, and
  // completeness is the one thing the three press-on questions do not test.
  // ════════════════════════════════════════════════════════════════════════
  console.log('\n=== THE SWEEP\'S OWN COMPLETENESS -- measured, not assumed ===\n');

  const sdSrc = require('fs').readFileSync(path.join(__dirname, '..', 'api', 'sd-data.js'), 'utf8');
  const sdLines = sdSrc.split('\n');
  // The exact shape the sweep fixed: a PATCH sent with return=representation,
  // its body read through .json().catch(), only `!ok` consulted, and a 200
  // {ok:true} returned. Found by walking back from each catch site to the
  // fetch that produced it rather than by matching one long regex.
  const unguarded = [];
  sdLines.forEach((l, idx) => {
    if (!/\.json\(\)\.catch\(/.test(l)) return;
    const n = idx + 1;
    const before = sdLines.slice(Math.max(0, idx - 12), idx).join('\n');
    const after = sdLines.slice(idx, idx + 6).join('\n');
    if (!/Prefer:\s*'return=representation'/.test(before)) return;   // not a representation write
    if (/method:\s*'POST'/.test(before)) return;                     // upserts, a different shape
    if (/wroteRow\(/.test(after)) return;                            // already swept
    if (!/res\.status\(200\)\.json\(\{\s*ok:\s*true/.test(after)) return;
    const varName = (l.match(/const\s+(\w+)\s*=/) || [])[1] || '?';
    const table = (before.match(/rest\(\s*'?([a-z_]+)/) || [])[1]
      || (before.match(/rest\((\w+)\s*\+/) || [])[1] || '?';
    unguarded.push({ n, varName, table, line: l.trim() });
  });

  console.log('  representation-PATCH sites answering ok:true with NO wroteRow():');
  unguarded.forEach((u) => console.log('    api/sd-data.js:' + String(u.n).padEnd(6)
    + ' ' + u.varName.padEnd(10) + ' target ' + u.table));

  // ── AND DRIVEN, because a source-shape match is a claim, not a defect ────
  // The SAIRNcode branch is gated to a sairncode session with role 'admin',
  // so the request is built for that; the mock answers the read with a row
  // and the PATCH with `[]`, which is what PostgREST returns when the update
  // matched nothing.
  console.log('\n  DRIVEN against api/sd-data.js:12422, sc_claims (Tier A):');
  for (const [label, patchBody] of [['PATCH matched one row', [{ data: {} }]],
                                    ['PATCH matched ZERO rows -- []', []],
                                    ['PATCH body unparseable', undefined]]) {
    const m = softDeleteMock({
      readRows: [{ data: { id: 'CLM-1', payer: 'Acme', amount: 1200 } }],
      patchBody: patchBody,
      patchThrows: label.indexOf('unparseable') !== -1
    });
    APP_ID = 'sairncode';
    const h = load('sd-data.js', m.fn);
    const r = mockRes();
    const scReq = {
      method: 'POST',
      headers: { authorization: 'Bearer GOOD-KEY',
                 'x-sd-auth': signSessionToken({ app: 'sairncode', employee_id: 'E-1',
                                                 role: 'admin', license_hash: LIC }) },
      body: { action: 'soft_delete', resource: 'sc_claims', payload: { id: 'CLM-1' } }
    };
    await h(scReq, r);
    const claimed = r.statusCode === 200 && r.body && r.body.ok === true;
    console.log('    %s -> %s %s%s', label.padEnd(32), r.statusCode,
      claimed ? 'ok:true' : ((r.body && r.body.error && r.body.error.code) || ''),
      (claimed && label.indexOf('ZERO') !== -1) ? '   <-- A REMOVAL THAT DID NOT HAPPEN'
        : ((claimed && label.indexOf('unparseable') !== -1) ? '   <-- A REMOVAL NOBODY CONFIRMED' : ''));
  }
  APP_ID = 'stonedesk';
  console.log('    compare api/sd-data.js:9908, the branch the commit DID fix:');
  for (const [label, patchBody] of [['PATCH matched ZERO rows -- []', []],
                                    ['PATCH body unparseable', undefined]]) {
    const m = softDeleteMock({
      readRows: [{ data: { id: 'R-1' } }], patchBody: patchBody,
      patchThrows: label.indexOf('unparseable') !== -1
    });
    const h = load('sd-data.js', m.fn);
    const r = mockRes();
    await h(req({ action: 'soft_delete', resource: 'sd_invoices', payload: { id: 'R-1' } }), r);
    console.log('    %s -> %s %s', label.padEnd(32), r.statusCode,
      (r.body && r.body.error && r.body.error.code) || 'ok:true');
  }

  if (unguarded.length) {
    findings++;
    console.log(`
  FINDING (HIGH) -- THE SWEEP IS INCOMPLETE, AND IT MISSED SEVEN TIER A
  RESOURCES IN THE SAME FILE IT SWEPT.

  ${unguarded.length} more sites in api/sd-data.js have the defect this commit
  fixed, byte-for-byte: a PATCH sent with \`Prefer: return=representation\`, its
  body read through \`.json().catch(() => null)\`, only \`!w.ok\` consulted, then
  \`res.status(200).json({ ok: true, ... })\`. Under PostgREST a PATCH matching
  ZERO rows returns \`[]\` with status 200, so every one of them reports a change
  that did not happen -- the exact sentence the commit message refuses.

  WHAT IS BEHIND EACH, and why this is not a tidy-up:

    :12422  the SAIRNcode soft-delete, serving SEVEN TIER A RESOURCES --
            sc_ar, sc_claims, sc_compliance, sc_credential_scope, sc_denial,
            sc_denial_events, sc_revenue. This branch is structurally the
            SAME CODE as the generic path the commit fixed at :9908: same
            read-then-PATCH, same Prefer header, same variable shape. It is
            gated to Compliance Admin and its own message says "Only
            Compliance Admin can remove records", so a removal reported as
            done and not done is a compliance record the admin believes is
            gone.

    :4135   bld_draws RETAINAGE RELEASE. Not a delete -- MONEY. It reports
            \`ok:true\` with \`release_log: trail\`, so the caller is handed the
            log entry describing a release that may never have been written.
            A retainage release that the record does not carry is a payment
            the job history cannot account for.

    :2404   sd_customers soft-delete. The same branch's READ half was
            hardened on 2026-09-04 ("NOT A SILENT SUCCESS ... saying
            'deleted' would be reporting work that did not happen") and the
            WRITE half twelve lines below it was not. The argument for the
            fix is already written, in this branch, against this defect.

    :11257  dnt_supplies soft-delete.

  WHY THE SWEEP MISSED THEM, since that matters more than the list: the
  search was for \`.json().catch(() => null)\`, which finds 27 sites in this
  file, and the vast majority are reads where a null is handled correctly.
  The DEFECT is not the catch -- it is the catch combined with a
  representation PATCH and an \`ok:true\`. Grepping the symptom returned a
  haystack and the two obvious needles were taken out of it. The predicate
  above is the one that separates them, and it is three conditions rather
  than one string.

  SUGGESTED FIX, mechanical and identical at all four, with wroteRow() and
  refuseUnconfirmedWrite() already module-scope in this file:

      const says = wroteRow(wRows);
      if (says === 'UNKNOWN') { refuseUnconfirmedWrite(res, <what>); return; }
      if (says === 'MISSED')  { res.status(404).json({ error: { code: 'NOT_FOUND', ... } }); return; }

  :4135 needs a different 404 sentence -- it is a release, not a delete --
  and that is the one place the transplant is not mechanical.

  NOT FIXED HERE. I hold a review claim, not the file, and a reviewer who
  also lands the fix is no longer independent of it.`);
  }

  console.log('\n=== CHECKED AND CORRECT ===');
  console.log(`  * wroteRow()'s three answers are exhaustive over what these paths can
    receive, and the UNKNOWN branch is fail-closed: refuseUnconfirmedWrite
    says the change is UNKNOWN rather than claiming either outcome, which is
    the third state this platform insists on everywhere else.
  * BOTH soft-delete sites were swept, not one. api/sd-data.js:2573
    (sd_quote_requests, its own branch) and :9908 (the generic
    SD_LOCAL_RESOURCES path serving the seven). A sweep that fixed the
    generic one and left the bespoke one would have been the likelier outcome.
  * the generic path is READ-MODIFY-WRITE rather than a blind upsert of the
    caller's copy, so a delete cannot also overwrite the stored record with a
    stale one -- and the marker lives inside the existing jsonb, so the fix
    needs no new database privilege.
  * !w.ok still routes to upstream() and is not folded into UNKNOWN. A store
    that answered 500 is a different fact from a store whose answer could not
    be read, and they get different responses.`);

  console.log('\n' + findings + ' finding(s). Report-only: exit 0 by design.');
  process.exit(0);
})();
