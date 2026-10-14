// api/sd-data-ai-approval.test.js
//
// Run:  node api/sd-data-ai-approval.test.js
//
// REQUIREMENT: api/sd-data.js refuses a HIGH-RISK, AI-SOURCED record that is
//   leaving draft unless it can put a signed-in employee's name on it -- and
//   the name it puts there comes from the VERIFIED SESSION, never from the
//   payload.
//
// ── WHY mech_quotes IS THE FIXTURE ────────────────────────────────────────
// It is the cleanest of the five high-risk resources to drive: its write is
// licence-gated ONLY (api/sd-data.js's MECH_RECORDS branch says so in its own
// comment -- "a quote or a cheque stub is not a credential"), so a refusal seen
// here is THIS gate and cannot be a session gate answering first. It is also
// the sharpest in substance: `text` is the model's reply over a photographed
// plan and the app shares it as the priced offer.
//
// ── WHAT THIS SUITE ASSERTS THAT THE UNIT TESTS CANNOT ───────────────────
// api/ai-safeguards.test.js drives the policy function in isolation. This one
// drives the REAL handler, and the thing only it can see is ORDERING AND
// REACH: that the refusal happens with ZERO upstream calls, before anything is
// written, and that an ordinary write of the same resource with no ai_source is
// completely untouched. A gate that refused after writing, or that quietly
// applied to every mech_quotes save, would pass every unit test above.
//
// ── THE HONEST LIMIT, STATED HERE BECAUSE IT IS NOT A TEST RESULT ─────────
// No production client stamps `ai_source` on a high-risk resource yet, so this
// refusal is REACHABLE BUT NOT YET REACHED in production. That is a bounded
// dormancy, it is recorded in docs/SAIRN-handoff-hank-b9.md, and this suite is
// what keeps the gate honest until the first adopter arrives.

'use strict';
const assert = require('assert');
const crypto = require('crypto');
const path = require('path');

const ROOT = path.join(__dirname, '..');
process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['ai', 'approval', 'fixture', String(process.pid)].join('-');

const HANDLER = path.join(__dirname, 'sd-data.js');
const ai = require('./_lib/ai-safeguards');
const { signSessionToken } = require('./_lib/auth');

const LICENSE_KEY = 'k';
const LIC_HASH = crypto.createHash('sha256').update(LICENSE_KEY).digest('hex');
const MECH_TOKEN = signSessionToken({
  app: 'sairnmechanical', employee_id: 'mech-emp-1', role: 'owner',
  license_hash: LIC_HASH });
const WRONG_APP_TOKEN = signSessionToken({
  app: 'sairnscape', employee_id: 'scp-emp-1', role: 'owner',
  license_hash: LIC_HASH });

let n = 0, bad = 0;
function ok(cond, label) {
  if (cond) { console.log('  ok   ' + label); n++; }
  else { console.log('  FAIL ' + label); bad++; }
}
function section(s) { console.log('\n' + s); }
const eCode = (r) => (r && r.body && r.body.error && r.body.error.code) || '';

function loadHandler() {
  delete require.cache[require.resolve(HANDLER)];
  return require(HANDLER);
}

// Records EVERY upstream call. The CALL COUNT is the assertion in half the
// arms below: "nothing was written" is a claim about Postgres, and a suite that
// only read the status code could not tell a refusal from a write-then-refuse.
// The licence row and the active-credential pre-check are answered without
// being counted, and counted separately, so the numbers below are this gate's.
async function call(handler, opts) {
  const out = { code: null, body: null, calls: [], credentialChecks: 0 };
  const res = { status(c) { out.code = c; return res; },
                json(b) { out.body = b; return res; }, setHeader() {} };
  const names = { url: ['SUPABASE', 'URL'].join('_'),
                  key: ['SUPABASE', 'SERVICE', 'ROLE', 'KEY'].join('_') };
  const envURL = process.env[names.url], envKey = process.env[names.key];
  const realFetch = global.fetch;
  process.env[names.url] = 'https://stub.invalid';
  process.env[names.key] = ['stub', 'fixture', 'value'].join('-');
  let first = true;
  const replies = (opts.replies || []).slice();
  global.fetch = async (url, init) => {
    if (first) {
      first = false;
      return { ok: true, status: 200,
               json: async () => [{ status: 'active', app_id: null }] };
    }
    if (/_employee_auth\?.*&select=active&limit=1/.test(String(url))) {
      out.credentialChecks++;
      return { ok: true, status: 200, json: async () => [{ active: true }] };
    }
    out.calls.push({ url: String(url), method: (init && init.method) || 'GET',
                     body: (init && init.body) || null });
    const r = replies.length ? replies.shift() : { status: 200, rows: [] };
    return { ok: r.status >= 200 && r.status < 300, status: r.status,
             json: async () => (r.rows === undefined ? [] : r.rows) };
  };
  try {
    await handler({
      method: 'POST',
      headers: Object.assign(
        { authorization: 'Bearer ' + LICENSE_KEY },
        opts.token === null ? {} : { 'x-sd-auth': opts.token }),
      body: { action: 'write', resource: opts.resource,
              app_id: opts.app_id || 'sairnmechanical',
              payload: opts.payload }
    }, res);
  } finally {
    global.fetch = realFetch;
    if (envURL === undefined) delete process.env[names.url]; else process.env[names.url] = envURL;
    if (envKey === undefined) delete process.env[names.key]; else process.env[names.key] = envKey;
  }
  return out;
}

const Q = (over) => Object.assign(
  { id: 'Q-1', trade: 'HVAC', date: '2026-10-14',
    text: 'Replace the rooftop unit. Materials and labour: $14,200.' },
  over || {});
const written = (r) => {
  const w = r.calls.filter((c) => c.method === 'POST' || c.method === 'PATCH');
  if (!w.length) return null;
  try { return JSON.parse(w[0].body); } catch (e) { return {}; }
};

console.log('api/sd-data.js -- an AI-written quote cannot leave draft without a '
            + 'name on it\n');

(async () => {
  const h = loadHandler();

  // ── 0. THE FIXTURE IS THE REAL POLICY ────────────────────────────────────
  section('0. the fixture');
  ok(ai.isHighRisk('mech_quotes'),
     'mech_quotes is high-risk in the shared policy, so this suite is driving '
     + 'the real table and not a local copy of one');
  ok(ai.HIGH_RISK_AI.mech_quotes.app === 'sairnmechanical',
     '...and the policy says SAIRNmechanical owns it, which is the app whose '
     + 'session the gate must demand');

  // ── 1. AN ORDINARY WRITE IS UNTOUCHED ────────────────────────────────────
  // THE OVER-REFUSAL ARM, AND IT GOES FIRST ON PURPOSE. A gate that applied to
  // every mech_quotes save would break every existing SAIRNmechanical user,
  // and every other arm in this file would still pass.
  section('1. a quote with no ai_source is completely untouched');
  {
    const r = await call(h, { resource: 'mech_quotes', payload: Q(), token: null,
      replies: [{ status: 201, rows: [{ data: Q() }] }] });
    ok(r.code === 200,
       'an ordinary quote still saves with the licence key alone -- ' + r.code
       + ' ' + JSON.stringify(r.body).slice(0, 90));
    ok(r.calls.length === 1 && r.calls[0].method === 'POST',
       '...in exactly one upstream write, as before -- '
       + r.calls.map((c) => c.method).join(','));
    const w = written(r);
    ok(w && !w.data.ai_approved_by,
       '...and nothing stamps an approval onto a record nobody claimed was '
       + 'AI-written');
  }

  // ── 2. THE REFUSAL ───────────────────────────────────────────────────────
  section('2. an AI-sourced quote leaving draft with NO session is refused');
  {
    const r = await call(h, { resource: 'mech_quotes', token: null,
      payload: Q({ ai_source: 'claude:field-quote' }) });
    ok(r.code === 403 && eCode(r) === 'AI_APPROVAL_REQUIRED',
       'refused 403 AI_APPROVAL_REQUIRED -- ' + r.code + ' ' + eCode(r));
    ok(r.calls.length === 0,
       'AND NOTHING WAS WRITTEN: zero upstream calls. A refusal after the '
       + 'write would leave an unapproved quote in the table and report a '
       + 'refusal, which is the worst of both. Took ' + r.calls.length);
    ok(/sign in/i.test((r.body.error.message) || ''),
       '...and the message tells the user what to do rather than naming a '
       + 'field they have never heard of');
  }
  {
    // A status that is not a draft status is the same refusal, so the gate is
    // not keyed on the ABSENCE of status alone.
    const r = await call(h, { resource: 'mech_quotes', token: null,
      payload: Q({ ai_source: 'claude:field-quote', status: 'final' }) });
    ok(r.code === 403 && eCode(r) === 'AI_APPROVAL_REQUIRED',
       'an explicit non-draft status is refused the same way -- ' + r.code);
  }

  // ── 3. A DRAFT IS ALLOWED ────────────────────────────────────────────────
  section('3. a DRAFT may be saved unapproved -- the gate is on leaving draft');
  {
    const p = Q({ ai_source: 'claude:field-quote', status: 'draft' });
    const r = await call(h, { resource: 'mech_quotes', payload: p, token: null,
      replies: [{ status: 201, rows: [{ data: p }] }] });
    ok(r.code === 200 && r.calls.length === 1,
       'an AI-sourced DRAFT saves with no session -- ' + r.code + ', '
       + r.calls.length + ' call(s)');
    const w = written(r);
    ok(w && !w.data.ai_approved_by,
       '...and it is stored WITHOUT an approval, so the footer will read '
       + '"not reviewed" rather than naming somebody who never saw it');
  }

  // ── 4. THE SERVER WRITES THE NAME ────────────────────────────────────────
  section('4. with a real SAIRNmechanical session the server stamps the name '
          + 'ITSELF');
  {
    const p = Q({ ai_source: 'claude:field-quote',
                  // THE FORGED NAME. The whole reason the server sets this
                  // field is that a payload can arrive already "approved" by
                  // somebody who never saw it.
                  ai_approved_by: 'the-owner',
                  ai_approved_at: '1999-01-01T00:00:00.000Z' });
    const r = await call(h, { resource: 'mech_quotes', payload: p,
      token: MECH_TOKEN, replies: [{ status: 201, rows: [{ data: p }] }] });
    ok(r.code === 200, 'the write succeeds -- ' + r.code);
    const w = written(r);
    ok(w && w.data.ai_approved_by === 'mech-emp-1',
       'the stored record names the SIGNED-IN employee, not the payload\'s '
       + 'claim -- got ' + (w && w.data.ai_approved_by));
    ok(w && w.data.ai_approved_at && w.data.ai_approved_at !== '1999-01-01T00:00:00.000Z',
       '...and the approval time is the server\'s, so a backdated review '
       + 'cannot be claimed -- got ' + (w && w.data.ai_approved_at));
    ok(w && w.data.ai_source === 'claude:field-quote',
       '...and ai_source survives, because the disclosure is the other half of '
       + 'the footer');
    ok(ai.aiFooter(w.data) === 'AI-assisted, reviewed by mech-emp-1',
       '...so the derived footer reads: ' + ai.aiFooter(w.data));
  }

  // ── 5. THE WRONG APP'S SESSION IS NOT A REVIEWER ─────────────────────────
  // Guardian Check 28. Role names like 'owner' exist in several apps'
  // vocabularies, so a SAIRNscape session would otherwise supply a perfectly
  // plausible reviewer name for a SAIRNmechanical quote.
  section('5. a session for ANOTHER SAIRN app cannot approve');
  {
    const r = await call(h, { resource: 'mech_quotes',
      payload: Q({ ai_source: 'claude:field-quote' }), token: WRONG_APP_TOKEN });
    ok(r.code === 403 && eCode(r) === 'AI_APPROVAL_REQUIRED',
       'refused -- ' + r.code + ' ' + eCode(r));
    ok(r.calls.length === 0, '...and nothing was written');
  }

  // ── 6. THE GATE IS NARROW ────────────────────────────────────────────────
  // An excluded resource must be able to carry ai_source with no session. If
  // this went red, the disclosure field would have become unusable for every
  // app that is not ready to add an approval step -- which is all of them.
  section('6. a DELIBERATELY-EXCLUDED resource takes ai_source with no session');
  {
    const p = { id: 'TK-1', text: 'Takeoff.', ai_source: 'claude:x' };
    const r = await call(h, { resource: 'mech_docs',
      payload: { id: 'D-1', text: 'A plan read.', ai_source: 'claude:x' },
      token: MECH_TOKEN, replies: [{ status: 201, rows: [{ data: p }] }] });
    ok(r.code !== 403 || eCode(r) !== 'AI_APPROVAL_REQUIRED',
       'mech_docs -- excluded in the policy -- is not refused by this gate. '
       + 'Got ' + r.code + ' ' + eCode(r));
  }
  {
    // And a resource with no AI involvement at all, through the same handler.
    const r = await call(h, { resource: 'mech_checks',
      payload: { id: '1041', payee: 'A supplier', amount: 120 },
      token: null, replies: [{ status: 201, rows: [{ data: { id: '1041' } }] }] });
    ok(r.code === 200 && r.calls.length === 1,
       'the cheque register -- no AI anywhere near it -- is unaffected. '
       + r.code + ', ' + r.calls.length + ' call(s)');
  }

  // ── 7. AND THE OTHER FOUR HIGH-RISK RESOURCES ARE REACHED TOO ────────────
  // THE PREFIX-RULE TRAP, AVOIDED. Driving one resource and trusting a shared
  // table is how a policy comes to cover one name. Each is driven through the
  // real handler with no session; each must refuse without writing.
  section('7. every high-risk resource refuses, not just the fixture');
  for (const r of Object.keys(ai.HIGH_RISK_AI)) {
    const app = ai.HIGH_RISK_AI[r].app;
    const res = await call(h, { resource: r, app_id: app, token: null,
      payload: { id: 'X-1', customer_id: 'C-1', job_id: 'J-1',
                 schedule_id: 'S-1', property_id: 'P-1',
                 ai_source: 'claude:x' } });
    ok(res.code === 403 && eCode(res) === 'AI_APPROVAL_REQUIRED'
       && res.calls.length === 0,
       r + ' (' + app + ') refuses with nothing written -- ' + res.code + ' '
       + eCode(res) + ', ' + res.calls.length + ' call(s)');
  }

  console.log('\n' + n + ' passed, ' + bad + ' failed');
  process.exit(bad ? 1 : 0);
})();
