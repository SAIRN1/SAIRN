// api/ai-safeguards.test.js
//
// Run:  node api/ai-safeguards.test.js
//
// REQUIREMENT, in two halves:
//
//   (1) THE POLICY IS A TOTAL PARTITION OF THE AI-WRITING RESOURCES. Every
//       resource that stores model prose is either high-risk (needs a human
//       name before it leaves draft) or explicitly excluded WITH A REASON.
//       A resource in neither is the failure this suite exists for: it would be
//       covered by nothing and look covered from inside either map.
//
//   (2) THE PER-EMPLOYEE AI NOTICE IS ACKNOWLEDGED ONCE, under that employee's
//       own login, with a date and a version -- and the popup never comes back
//       for a version already acknowledged.
//
// ── WHAT A GREEN RUN DOES NOT SAY ─────────────────────────────────────────
// It does not say the live database has the two columns. api/ai-notice.js
// answers 503 AI_NOTICE_NOT_PROVISIONED until
// sql/2026-10-14-hank-b9-ai-safeguards.sql is run, and that path is DRIVEN
// below -- but a green suite is not a migrated database.

'use strict';
const assert = require('assert');
const crypto = require('crypto');
const path = require('path');

const ROOT = path.join(__dirname, '..');
// Assembled rather than written as a literal, so this file carries nothing
// credential-shaped. Set BEFORE api/_lib/auth.js is required.
process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['ai', 'safeguards', 'fixture', String(process.pid)].join('-');

const ai = require('./_lib/ai-safeguards');
const reg = require('./_resources');
const { AI_SCANNED_TEXT } = require('./_lib/ai-scan-redaction');
const { signSessionToken, AUTH_TABLE_BY_APP } = require('./_lib/auth');

let n = 0, bad = 0;
function ok(cond, label) {
  if (cond) { console.log('  ok   ' + label); n++; }
  else { console.log('  FAIL ' + label); bad++; }
}
function section(s) { console.log('\n' + s); }

const LICENSE_KEY = 'k';
const LIC_HASH = crypto.createHash('sha256').update(LICENSE_KEY).digest('hex');
const APP = 'sairnfreedom';
const TOKEN = signSessionToken({
  app: APP, employee_id: 'emp-1', role: 'post.govern', license_hash: LIC_HASH });
const OTHER_APP_TOKEN = signSessionToken({
  app: 'sairnlaw', employee_id: 'emp-1', role: 'attorney', license_hash: LIC_HASH });
const OTHER_LIC_TOKEN = signSessionToken({
  app: APP, employee_id: 'emp-1', role: 'post.govern',
  license_hash: crypto.createHash('sha256').update('other').digest('hex') });

console.log('AI SAFEGUARDS -- the policy partition, the approval gate and the '
            + 'one-time notice\n');

(async () => {
  // ══ 1. THE PARTITION ════════════════════════════════════════════════════
  section('1. every AI-writing resource is decided, and no resource is decided '
          + 'twice');
  {
    const prose = Object.keys(AI_SCANNED_TEXT).sort();
    ok(prose.length >= 8,
       'the AI-prose population is real -- ' + prose.length + ' resources. A '
       + 'short list here would make every arm below pass over almost nothing');

    const high = Object.keys(ai.HIGH_RISK_AI);
    const not = Object.keys(ai.NOT_HIGH_RISK_AI);
    const both = high.filter((r) => not.indexOf(r) !== -1);
    ok(both.length === 0,
       'no resource is in BOTH maps -- a resource that is high-risk and '
       + 'excluded is two answers and the first one read wins'
       + (both.length ? ': ' + both.join(', ') : ''));

    // THE LOAD-BEARING ONE. Deliberately asserted in the direction that
    // catches a NEW AI surface: a resource added to AI_SCANNED_TEXT with no
    // risk decision fails here, which is the only moment anybody is looking.
    const undecided = prose.filter((r) =>
      high.indexOf(r) === -1 && not.indexOf(r) === -1);
    ok(undecided.length === 0,
       'EVERY resource that stores model prose has a risk decision'
       + (undecided.length ? ' -- UNDECIDED: ' + undecided.join(', ') : ''));

    // The other direction, which catches the opposite drift: a decision about
    // a resource that no longer stores model prose, or never did.
    const phantomNot = not.filter((r) => prose.indexOf(r) === -1);
    ok(phantomNot.length === 1 && phantomNot[0] === 'sf_bottle_fills',
       'the ONLY excluded resource that is not in AI_SCANNED_TEXT is '
       + 'sf_bottle_fills, and that is deliberate: it stores a NUMBER a model '
       + 'determined rather than prose, so the redaction map has no business '
       + 'with it while the disclosure policy does. Found: '
       + (phantomNot.join(', ') || 'none'));
    const phantomHigh = high.filter((r) => prose.indexOf(r) === -1);
    ok(phantomHigh.length === 0,
       'no high-risk entry names a resource that stores no model prose'
       + (phantomHigh.length ? ' -- ' + phantomHigh.join(', ') : ''));

    // EVERY REASON IS A REAL SENTENCE. A one-word exclusion is the CAPA box
    // this field exists instead of.
    const thin = not.filter((r) => String(ai.NOT_HIGH_RISK_AI[r]).trim().length < 60)
      .concat(high.filter((r) => String(ai.HIGH_RISK_AI[r].why).trim().length < 60));
    ok(thin.length === 0,
       'every entry in both maps carries a real reason, not a label'
       + (thin.length ? ' -- thin: ' + thin.join(', ') : ''));

    // AND THE APP ON EACH HIGH-RISK ENTRY IS CHECKED AGAINST THE REGISTRY,
    // because the gate verifies a session for it. A wrong app here would
    // verify a token for an app with no business approving the record.
    const wrongApp = high.filter((r) =>
      reg.OWNER_BY_RESOURCE[r] !== ai.HIGH_RISK_AI[r].app);
    ok(wrongApp.length === 0,
       'every high-risk entry names the app that OWNS the resource, derived '
       + 'from api/_resources rather than trusted'
       + (wrongApp.length ? ' -- ' + wrongApp.map((r) =>
            r + ' says ' + ai.HIGH_RISK_AI[r].app + ', registry says '
            + reg.OWNER_BY_RESOURCE[r]).join('; ') : ''));
  }

  // ══ 2. THE APPROVAL GATE, BOTH DIRECTIONS ═══════════════════════════════
  section('2. the approval gate');
  {
    const never = () => null;              // nobody is signed in
    const signed = (app) => ({ employee_id: 'emp-7', app: app });
    const now = () => '2026-10-14T00:00:00.000Z';

    ok(ai.enforceAiApproval('mech_quotes', { id: 'Q1' }, never, now) === null,
       'a record with NO ai_source is untouched -- the server cannot know a '
       + 'model wrote prose, so an unstamped record gets no gate and that '
       + 'limit is the reason the field exists');

    ok(ai.enforceAiApproval('msb_food_scans', { ai_source: 'claude:x' }, never, now) === null,
       'an AI-sourced record on a DELIBERATELY-EXCLUDED resource is allowed '
       + 'with no session -- disclosure and approval are different safeguards');

    ok(ai.enforceAiApproval('mech_quotes',
        { ai_source: 'claude:x', status: 'draft' }, never, now) === null,
       'a DRAFT may be unapproved -- the gate is on leaving draft, not on '
       + 'writing one');

    {
      const r = ai.enforceAiApproval('mech_quotes', { ai_source: 'claude:x' }, never, now);
      ok(r && r.status === 403 && r.code === 'AI_APPROVAL_REQUIRED',
         'an AI-sourced high-risk record with NO status and NO session is '
         + 'REFUSED -- absent status is FINAL, not draft, which is the '
         + 'direction that keeps the gate from being silent on the resources '
         + 'that have no status field at all');
    }
    {
      const r = ai.enforceAiApproval('mech_quotes',
        { ai_source: 'claude:x', status: 'final' }, never, now);
      ok(r && r.code === 'AI_APPROVAL_REQUIRED',
         'and the same with an explicit non-draft status');
    }
    {
      // THE FORGED NAME. This is the whole point of the server setting the
      // field: a payload that arrives already "approved" by somebody who never
      // saw it must not be believed.
      const p = { ai_source: 'claude:x', ai_approved_by: 'the-boss',
                  ai_approved_at: '1999-01-01T00:00:00.000Z' };
      const r = ai.enforceAiApproval('mech_quotes', p, signed, now);
      ok(r === null && p.ai_approved_by === 'emp-7',
         'a forged ai_approved_by in the payload is OVERWRITTEN from the '
         + 'verified session -- got ' + p.ai_approved_by);
      ok(p.ai_approved_at === now(),
         '...and so is ai_approved_at, so a backdated review cannot be '
         + 'claimed -- got ' + p.ai_approved_at);
    }
    {
      // A forged name with NO session must be refused, not accepted on the
      // strength of the field already being there.
      const p = { ai_source: 'claude:x', ai_approved_by: 'the-boss' };
      const r = ai.enforceAiApproval('mech_quotes', p, never, now);
      ok(r && r.code === 'AI_APPROVAL_REQUIRED',
         'a payload that arrives pre-approved with no session is still '
         + 'refused -- the field is not evidence, the session is');
    }
    {
      // THE APP THE GATE ASKS FOR. A verifier that is handed the wrong app
      // would be the Check 28 collision; assert the argument, not just the
      // outcome.
      const asked = [];
      ai.enforceAiApproval('rf_photos', { ai_source: 'claude:x' },
        (app) => { asked.push(app); return { employee_id: 'e' }; }, now);
      ok(asked.length === 1 && asked[0] === 'sairnroofing',
         'the gate verifies the session for the app that OWNS the resource -- '
         + 'asked for ' + JSON.stringify(asked));
    }
  }

  // ══ 3. THE FOOTER ═══════════════════════════════════════════════════════
  section('3. the footer is derived, and an unreviewed one SAYS SO');
  {
    ok(ai.aiFooter({ id: 'x' }) === '',
       'a record with no ai_source gets no footer at all');
    ok(ai.aiFooter({ ai_source: 'claude:x' }) === 'AI-assisted — not reviewed',
       'an AI-sourced record nobody approved reads "not reviewed" rather than '
       + 'rendering nothing -- a MISSING footer and an unreviewed one look '
       + 'identical to a reader and only one of them is true');
    ok(ai.aiFooter({ ai_source: 'claude:x', ai_approved_by: 'J. Smith' })
         === 'AI-assisted, reviewed by J. Smith',
       'and an approved one names the reviewer');
  }

  // ══ 4. THE NOTICE STATE ═════════════════════════════════════════════════
  section('4. the one-time notice, as a pure function of the credential row');
  {
    ok(ai.aiNoticeState(null).required === true,
       'a row that does not exist yet is REQUIRED -- the state every existing '
       + 'credential starts in, and not an error');
    ok(ai.aiNoticeState({}).required === true,
       'and so is a row with no ack columns set');
    ok(ai.aiNoticeState({ ai_notice_version: ai.CURRENT_NOTICE_VERSION,
                          ai_notice_acked_at: 'T' }).required === false,
       'the current version acknowledged is NOT required -- this is the '
       + 'no-repeat-popups property');
    ok(ai.aiNoticeState({ ai_notice_version: '2020-01' }).required === true,
       'an OLD version is required again, which a boolean could not express');
    ok(ai.aiNoticeState({ ai_notice_version: '2020-01' }).acked_version === '2020-01',
       '...and the old version is still readable, so "which text did this '
       + 'person see" stays answerable until the new ack lands');
    ok(typeof ai.CURRENT_NOTICE_VERSION === 'string'
       && ai.CURRENT_NOTICE_VERSION.length > 0,
       'the version is a non-empty string -- ' + ai.CURRENT_NOTICE_VERSION);
  }

  // ══ 5. THE ENDPOINT ═════════════════════════════════════════════════════
  // Drives the REAL handler with a stubbed upstream, recording every call.
  section('5. api/ai-notice.js -- the endpoint, driven');
  {
    const names = { url: ['SUPABASE', 'URL'].join('_'),
                    key: ['SUPABASE', 'SERVICE', 'ROLE', 'KEY'].join('_') };
    const handler = require('./ai-notice.js');

    async function call(opts) {
      const out = { code: null, body: null, calls: [] };
      const res = { status(c) { out.code = c; return res; },
                    json(b) { out.body = b; return res; }, setHeader() {} };
      const envURL = process.env[names.url], envKey = process.env[names.key];
      const realFetch = global.fetch;
      process.env[names.url] = 'https://stub.invalid';
      process.env[names.key] = ['stub', 'fixture', 'value'].join('-');
      const replies = (opts.replies || []).slice();
      let first = true;
      global.fetch = async (url, init) => {
        if (first) {
          first = false;                       // the licence row
          return { ok: true, status: 200,
                   json: async () => [{ status: 'active', app_id: null }] };
        }
        out.calls.push({ url: String(url), method: (init && init.method) || 'GET',
                         body: (init && init.body) || null });
        const r = replies.length ? replies.shift() : { status: 200, rows: [] };
        return { ok: r.status >= 200 && r.status < 300, status: r.status,
                 json: async () => (r.rows === undefined ? [] : r.rows) };
      };
      try {
        await handler({
          method: opts.method || 'POST',
          headers: Object.assign(
            { authorization: 'Bearer ' + LICENSE_KEY },
            opts.token === null ? {} : { 'x-sd-auth': opts.token || TOKEN }),
          body: Object.assign({ action: opts.action, app_id: APP }, opts.extra || {})
        }, res);
      } finally {
        global.fetch = realFetch;
        if (envURL === undefined) delete process.env[names.url]; else process.env[names.url] = envURL;
        if (envKey === undefined) delete process.env[names.key]; else process.env[names.key] = envKey;
      }
      return out;
    }

    {
      const r = await call({ action: 'state', token: null });
      ok(r.code === 401 && r.body.error.code === 'NO_SESSION' && r.calls.length === 0,
         'NO SESSION is refused and reaches the database zero times -- '
         + r.code + ', ' + r.calls.length + ' call(s)');
    }
    {
      const r = await call({ action: 'ack', token: OTHER_APP_TOKEN,
                             extra: { version: ai.CURRENT_NOTICE_VERSION } });
      ok(r.code === 401 && r.calls.length === 0,
         'a token minted for ANOTHER SAIRN app cannot ack -- ' + r.code);
    }
    {
      const r = await call({ action: 'ack', token: OTHER_LIC_TOKEN,
                             extra: { version: ai.CURRENT_NOTICE_VERSION } });
      ok(r.code === 401 && r.calls.length === 0,
         'a token for another LICENCE cannot ack -- cross-tenant ack is the '
         + 'highest-value bug in this feature. ' + r.code);
    }
    {
      const r = await call({ action: 'state', extra: { app_id: 'not-an-app' } });
      ok(r.code === 400 && r.body.error.code === 'UNKNOWN_APP',
         'an app with no credential table is a NAMED refusal, not a guessed '
         + 'table name -- ' + r.code);
    }
    {
      const r = await call({ action: 'nonsense' });
      ok(r.code === 400 && /action must be one of/.test(r.body.error.message),
         'an unknown action names the vocabulary');
    }
    {
      const r = await call({ action: 'state', method: 'GET' });
      ok(r.code === 405, 'GET is refused -- ' + r.code);
    }
    {
      const r = await call({ action: 'state',
        replies: [{ status: 200, rows: [{ ai_notice_version: null, ai_notice_acked_at: null }] }] });
      ok(r.code === 200 && r.body.data.required === true,
         'a credential that has never acked is required -- ' + r.code);
      ok(/employee_id=eq\.emp-1/.test(r.calls[0].url)
         && r.calls[0].url.indexOf('license_hash=eq.' + LIC_HASH) !== -1,
         '...and the read is filtered on BOTH the employee from the token and '
         + 'the licence, so no request shape can read another row');
    }
    {
      const r = await call({ action: 'state', replies: [{ status: 200, rows: [] }] });
      ok(r.code === 403 && r.body.error.code === 'CREDENTIAL_INACTIVE',
         'a token that VERIFIES but whose row is gone is refused, not told it '
         + 'is up to date -- ' + r.code);
    }
    {
      const r = await call({ action: 'ack', extra: { version: 'whatever-i-like' } });
      ok(r.code === 400 && r.body.error.code === 'NOTICE_VERSION_MISMATCH'
         && r.calls.length === 0,
         'an arbitrary version string is REFUSED rather than stored -- storing '
         + 'it would either re-prompt forever or never prompt again, and both '
         + 'look like a working ack. ' + r.code);
    }
    {
      const r = await call({ action: 'ack',
        extra: { version: ai.CURRENT_NOTICE_VERSION },
        replies: [{ status: 200, rows: [{ ai_notice_version: null, ai_notice_acked_at: null }] },
                  { status: 200, rows: [{ ai_notice_version: ai.CURRENT_NOTICE_VERSION,
                                          ai_notice_acked_at: '2026-10-14T00:00:00.000Z' }] }] });
      ok(r.code === 200 && r.body.data.required === false,
         'a first ack records and the notice stops being required -- ' + r.code);
      ok(r.calls.length === 2 && r.calls[1].method === 'PATCH',
         '...in a read then a PATCH -- ' + r.calls.map((c) => c.method).join(','));
      const sent = JSON.parse(r.calls[1].body);
      ok(sent.ai_notice_version === ai.CURRENT_NOTICE_VERSION
         && typeof sent.ai_notice_acked_at === 'string',
         '...writing the version AND the date -- ' + JSON.stringify(sent));
    }
    {
      const already = { ai_notice_version: ai.CURRENT_NOTICE_VERSION,
                        ai_notice_acked_at: '2026-01-01T00:00:00.000Z' };
      const r = await call({ action: 'ack',
        extra: { version: ai.CURRENT_NOTICE_VERSION },
        replies: [{ status: 200, rows: [already] }] });
      ok(r.code === 200 && r.body.already === true && r.calls.length === 1,
         'a SECOND ack of the same version writes nothing -- idempotent, and '
         + 'acked_at is evidence of when the person actually read it so a '
         + 'refresh loop must not keep moving it. '
         + r.calls.length + ' call(s)');
      ok(r.body.data.acked_at === already.ai_notice_acked_at,
         '...and the original date comes back unchanged');
    }
    {
      // A FAILED ACK MUST NEVER READ AS ACKED.
      const r = await call({ action: 'ack',
        extra: { version: ai.CURRENT_NOTICE_VERSION },
        replies: [{ status: 200, rows: [{ ai_notice_version: null }] },
                  { status: 500, rows: { message: 'boom' } }] });
      ok(r.code === 502 && r.body.error.code === 'ACK_NOT_SAVED',
         'a failed write is an ERROR, so `state` still says required and the '
         + 'notice comes back next login -- ' + r.code);
    }
    {
      // THE MIGRATION NOT HAVING RUN IS A THIRD STATE.
      const r = await call({ action: 'state',
        replies: [{ status: 400,
                    rows: { message: 'column "ai_notice_version" does not exist' } }] });
      ok(r.code === 503 && /NOT_PROVISIONED/.test(JSON.stringify(r.body)),
         'an unmigrated database is COULD NOT TELL -- it names the sql file '
         + 'rather than answering required true or false, either of which '
         + 'would be a confident wrong answer. ' + r.code);
    }
    {
      // The ack path has to reach the same conclusion, or the two halves
      // disagree about whether the feature exists.
      const r = await call({ action: 'ack',
        extra: { version: ai.CURRENT_NOTICE_VERSION },
        replies: [{ status: 400,
                    rows: { message: 'column "ai_notice_acked_at" does not exist' } }] });
      ok(r.code === 503, '...and so does the ack path -- ' + r.code);
    }
  }

  // ══ 6. THE SQL COVERS EVERY APP WITH CREDENTIALS ════════════════════════
  section('6. the migration is derived, not a list of sixteen table names');
  {
    const fs = require('fs');
    const sql = fs.readFileSync(
      path.join(ROOT, 'sql/2026-10-14-hank-b9-ai-safeguards.sql'), 'utf8');
    ok(/information_schema\.tables/.test(sql),
       'the migration finds its tables in information_schema rather than '
       + 'listing them -- a hand-written list would be a seventeenth copy of '
       + 'AUTH_TABLE_BY_APP and would miss every app added afterwards');
    ok(/add column if not exists ai_notice_version/.test(sql)
       && /add column if not exists ai_notice_acked_at/.test(sql),
       'both columns are added idempotently');
    ok(/raise exception/.test(sql),
       'a loop that matched NOTHING raises rather than exiting clean -- an '
       + 'empty match otherwise reads exactly like a successful run');
    const tables = Object.keys(AUTH_TABLE_BY_APP).map((a) => AUTH_TABLE_BY_APP[a]);
    const offPattern = tables.filter((t) => !/_employee_auth$/.test(t));
    ok(offPattern.length === 0,
       'every credential table in AUTH_TABLE_BY_APP ends in `_employee_auth`, '
       + 'which is what the migration\'s suffix match depends on. '
       + tables.length + ' table(s) checked'
       + (offPattern.length ? ' -- OFF PATTERN: ' + offPattern.join(', ') : ''));
  }

  console.log('\n' + n + ' passed, ' + bad + ' failed  ('
              + Object.keys(ai.HIGH_RISK_AI).length + ' high-risk, '
              + Object.keys(ai.NOT_HIGH_RISK_AI).length + ' excluded, '
              + Object.keys(AUTH_TABLE_BY_APP).length + ' app(s) with credentials)');
  console.log('\nWHAT A GREEN RUN DOES NOT SAY: that the live database has the two\n'
              + 'columns, or that any client stamps ai_source on a high-risk resource\n'
              + 'yet. The first is a SQL run; the second is named in the handoff.');
  process.exit(bad ? 1 : 0);
})();
