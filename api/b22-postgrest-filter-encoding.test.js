// api/b22-postgrest-filter-encoding.test.js
//
// Run:  node api/b22-postgrest-filter-encoding.test.js
//
// REQUIREMENT (b22, findings-register #1599): every identifier interpolated
// into a PostgREST filter must pass through `encodeURIComponent` AT THE POINT
// OF CONCATENATION, so a request-supplied value cannot add or alter query
// parameters.
//
// ── WHY THIS IS A REAL DEFECT AND NOT A STYLE NIT ─────────────────────────
// PostgREST takes its filters from the query string. A value spliced in raw
// is not quoted or escaped by anything downstream -- an `&` in it STARTS A NEW
// PARAMETER. So `command_id = "x&select=*"` turns
//
//   ?id=eq.x&select=*&agent_id=eq.<uuid>&select=id
//
// into a query with a caller-chosen `select`. The caller cannot reach another
// tenant's rows that way -- the ownership filter is still ANDed -- but it can
// change the PROJECTION, add an `order`, add a `limit`, or append a second
// filter on a column the handler never meant to expose. The handler then reads
// `cmds[0].id` out of a row shaped by the caller.
//
// ── THE SHAPE FINDING #1599 NAMES, AND WHY IT IS THE WORST KIND ───────────
// `api/agent/enqueue.js` encoded `agent_id` correctly at :126 and spliced THE
// SAME VALUE raw at :77. One file, one identifier, both spellings. A reviewer
// who greps for `encodeURIComponent` finds it present and moves on; the hit
// that matters is the one that is ABSENT, and absence is what a grep for the
// right thing cannot show.
//
// ── WHAT THIS SUITE DRIVES ────────────────────────────────────────────────
// The REAL handlers, through a recorded fetch, with an injection-shaped
// identifier -- so the arms measure the URL that would actually be sent rather
// than asserting that a string appears in the source. `crypto` is real; the
// env is stubbed because SUPABASE_URL is unset on a developer machine and a
// suite written against the real one would pass whether the fix is right or
// wrong.
//
// Exit: 0 all arms passed - 1 an arm FAILED

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';

// THE INJECTION PAYLOAD. An `&` and a `select` are the whole point: unencoded
// they become a new query parameter, encoded they stay one opaque value.
const EVIL = 'x&select=*&order=created_at.desc';
const BENIGN = '11111111-2222-3333-4444-555555555555';

let calls = [];
let agentRow = [{ id: 'agent-uuid-1', status: 'active' }];
let cmdRow = [{ id: 'cmd-1' }];
global.fetch = async (url, opts) => {
  const u = String(url);
  calls.push({ url: u, method: (opts && opts.method) || 'GET' });
  if (u.indexOf('sairn_agents?') !== -1) {
    return { ok: true, status: 200, json: async () => agentRow,
             text: async () => JSON.stringify(agentRow) };
  }
  if (u.indexOf('sairn_agent_commands') !== -1) {
    // The INSERT path (enqueue) and the SELECT path (result) both land here.
    // Both must come back with a row carrying an `id`: enqueue reads
    // `inserted[0].id` and throws without it, which prints a stack that reads
    // like an arm failure when the arm actually passed.
    return { ok: true, status: 200, json: async () => cmdRow,
             text: async () => JSON.stringify(cmdRow) };
  }
  return { ok: true, status: 200, json: async () => ([{ id: 'row-1' }]),
           text: async () => '[{"id":"row-1"}]' };
};

function mockRes() {
  const r = { _s: 0, _j: null };
  r.status = (s) => { r._s = s; return r; };
  r.json = (j) => { r._j = j; return r; };
  return r;
}

// `h` is the handler under test so the ablation arms can drive a lifted copy
// through the identical call shape rather than a second hand-written one.
async function post(h, body) {
  calls = [];
  const res = mockRes();
  await h({ method: 'POST',
            headers: { authorization: 'Bearer agent-token-abc' },
            body: body }, res);
  return { status: res._s, body: res._j, calls: calls.slice() };
}

// The command lookup is the query the defect was in -- picked by its filter
// rather than by call index, so a handler that adds a call does not silently
// re-point this helper at the wrong URL.
function cmdLookup(r) {
  return r.calls.filter((c) => c.url.indexOf('sairn_agent_commands?id=eq.') !== -1)[0];
}

let pass = 0, fail = 0;
const failed = [];
function t(name, fn) {
  return Promise.resolve().then(fn)
    .then(() => { console.log('  ok   ' + name); pass++; })
    .catch((e) => {
      console.log('  FAIL ' + name + '\n       ' + e.message);
      fail++; failed.push(name.split('.')[0]);
    });
}
function section(s) { console.log('\n' + s); }

// ── THE ABLATION ANCHORS, NAMED ONCE ─────────────────────────────────────
// Both ablation arms cut the SAME encoder call out of a lifted copy. Named so
// a future change to that line is a one-line re-seat, and so a drifted anchor
// fails LOUDLY instead of silently ablating nothing -- which is the failure
// b22 hit on the sibling bridge suite and had to fix.
const RESULT_ENCODED =
  "'/rest/v1/sairn_agent_commands?id=eq.' + encodeURIComponent(command_id) + '&agent_id=eq.' + encodeURIComponent(agentId) + '&select=id'";
const RESULT_RAW =
  "'/rest/v1/sairn_agent_commands?id=eq.' + command_id + '&agent_id=eq.' + agentId + '&select=id'";

function liftAblated(file, from, to, tag) {
  const src = fs.readFileSync(path.join(__dirname, file), 'utf8');
  assert.notStrictEqual(src.indexOf(from), -1,
    'the ablation anchor was not found in ' + file + ' -- it has drifted, so '
    + 'this arm is no longer ablating anything. RE-SEAT THE ANCHOR, do not '
    + 'delete the arm.');
  const tmp = path.join(__dirname, '.abl-' + tag + '-' + process.pid + '.js');
  fs.writeFileSync(tmp, src.replace(from, to), 'utf8');
  return tmp;
}

(async () => {
  console.log('b22 -- PostgREST filter values are encoded, not spliced');

  // ── A. THE ARM ──────────────────────────────────────────────────────────
  section('A. an injection-shaped identifier is encoded into ONE filter value');

  const result = require('./agent/result.js');

  await t('A1. api/agent/result.js -- a command_id of "' + EVIL + '" lands '
        + 'PERCENT-ENCODED, so the `&` cannot start a new query parameter',
    async () => {
      const r = await post(result, { command_id: EVIL, ok: true, result: {} });
      const q = cmdLookup(r);
      assert.ok(q, 'the command lookup never happened: '
        + JSON.stringify(r.calls.map((c) => c.url)));
      assert.ok(q.url.indexOf('id=eq.' + encodeURIComponent(EVIL)) !== -1,
        'the value is not encoded in the filter: ' + q.url);
      // THE DECISIVE ASSERTION, and it is about what the URL does NOT contain.
      // Counting `&` is what distinguishes "encoded" from "merely present":
      // the handler's own query has exactly one `&` (before agent_id) plus one
      // (before select); a raw EVIL adds two more.
      const amps = (q.url.match(/&/g) || []).length;
      assert.strictEqual(amps, 2,
        'the caller added ' + (amps - 2) + ' query parameter(s) -- the value was '
        + 'spliced raw: ' + q.url);
      assert.strictEqual(q.url.indexOf('&select=*'), -1,
        'a caller-chosen select reached the query: ' + q.url);
      assert.strictEqual(q.url.indexOf('&order='), -1,
        'a caller-chosen order reached the query: ' + q.url);
    });

  await t('A2. ...and the OWNERSHIP filter survives intact beside it. An '
        + 'encoder that also mangled agent_id would pass A1 and break the '
        + 'check that makes this endpoint safe at all', async () => {
    const r = await post(result, { command_id: EVIL, ok: true, result: {} });
    const q = cmdLookup(r);
    assert.ok(q.url.indexOf('&agent_id=eq.agent-uuid-1') !== -1,
      'the agent ownership filter is missing or altered: ' + q.url);
    assert.ok(/&select=id(&|$)/.test(q.url),
      'the handler own select is missing or altered: ' + q.url);
  });

  await t('A3. api/agent/enqueue.js -- THE FILE FINDING #1599 NAMES, where the '
        + 'SAME identifier was encoded at :126 and spliced raw at :77. The '
        + 'agent lookup now encodes it', async () => {
    const enqueue = require('./agent/enqueue.js');
    const r = await post(enqueue,
      { agent_id: EVIL, operation: 'noop', params: {} });
    const q = r.calls.filter((c) => c.url.indexOf('sairn_agents?id=eq.') !== -1)[0];
    assert.ok(q, 'the agent lookup never happened: '
      + JSON.stringify(r.calls.map((c) => c.url)));
    assert.ok(q.url.indexOf('id=eq.' + encodeURIComponent(EVIL)) !== -1,
      'agent_id is not encoded: ' + q.url);
    assert.strictEqual(q.url.indexOf('&select=*'), -1, q.url);
  });

  // ── B. THE NEGATIVE CONTROL ─────────────────────────────────────────────
  section('B. NEGATIVE CONTROL -- the encoder is not a wall');

  await t('B1. a BENIGN uuid still produces a working lookup and is byte-for-byte '
        + 'unchanged by the encoder. Without this arm the fix could be refusing '
        + 'or mangling every id and every arm above would still pass', async () => {
    const r = await post(result, { command_id: BENIGN, ok: true, result: {} });
    const q = cmdLookup(r);
    assert.ok(q, 'the command lookup never happened');
    assert.ok(q.url.indexOf('id=eq.' + BENIGN) !== -1,
      'a plain uuid came out altered -- encodeURIComponent must be a no-op on '
      + 'it: ' + q.url);
    assert.strictEqual(encodeURIComponent(BENIGN), BENIGN,
      'this arm depends on a uuid being encoder-invariant; if that ever '
      + 'changes the arm is wrong, not the fix');
  });

  await t('B2. ...and the handler still REACHES its happy path on a benign id -- '
        + 'it PATCHes the command row. An encoder that broke the lookup would '
        + 'leave the handler answering 404 and B1 alone would not notice',
    async () => {
      const r = await post(result, { command_id: BENIGN, ok: true, result: {} });
      const patched = r.calls.filter((c) => c.method === 'PATCH');
      assert.ok(patched.length >= 1,
        'no PATCH was issued, so the benign path did not complete: '
        + JSON.stringify(r.calls));
      assert.strictEqual(r.status, 200, JSON.stringify(r.body));
    });

  // ── C. THE ABLATION ─────────────────────────────────────────────────────
  section('C. ABLATION -- put the raw splice back and A1 must go RED');

  await t('C1. with encodeURIComponent REMOVED from the command lookup, the '
        + 'injection lands RAW and the caller adds its own query parameters -- '
        + 'the pre-fix behaviour reproduced on purpose, so A1 is testing this '
        + 'encoder and not something else', async () => {
    const tmp = liftAblated('agent/result.js', RESULT_ENCODED, RESULT_RAW, 'raw');
    try {
      const h = require(tmp);
      const r = await post(h, { command_id: EVIL, ok: true, result: {} });
      const q = cmdLookup(r);
      assert.ok(q, 'the ablated handler made no command lookup at all -- the '
        + 'ablation removed the wrong thing');
      assert.ok(q.url.indexOf('&select=*') !== -1,
        'the ablated handler STILL encoded the value, so C1 proves nothing: '
        + q.url);
      const amps = (q.url.match(/&/g) || []).length;
      assert.ok(amps > 2,
        'the raw splice did not add query parameters, so the payload is not '
        + 'actually injecting: ' + q.url);
    } finally {
      try { fs.unlinkSync(tmp); } catch (e) { /* best effort */ }
    }
  });

  await t('C2. CLEAN -- the ablated copy still serves a BENIGN id normally. '
        + 'Without this, C1 would also pass if the ablation had simply '
        + 'corrupted the file', async () => {
    const tmp = liftAblated('agent/result.js', RESULT_ENCODED, RESULT_RAW, 'clean');
    try {
      const h = require(tmp);
      const r = await post(h, { command_id: BENIGN, ok: true, result: {} });
      assert.strictEqual(r.status, 200, JSON.stringify(r.body));
      assert.ok(r.calls.filter((c) => c.method === 'PATCH').length >= 1,
        'the ablated copy does not complete the benign path either');
    } finally {
      try { fs.unlinkSync(tmp); } catch (e) { /* best effort */ }
    }
  });

  // ── D. THE SWEEP, AS A STANDING ARM ─────────────────────────────────────
  section('D. the sweep that found the class, kept as an arm');

  await t('D1. ZERO production files splice a value into a PostgREST filter '
        + 'without an encoder. This is the arm that stops the NEXT one from '
        + 'being written -- fixing fifteen sites and not asserting the class '
        + 'leaves the sixteenth to be found the same way', async () => {
    const OPS = ['eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'like', 'ilike', 'in',
                 'is', 'cs', 'cd', 'ov', 'fts', 'plfts', 'phfts', 'wfts',
                 'match', 'imatch'];
    const pat = new RegExp("=(?:" + OPS.join('|') + ")\\.\\s*['\"]\\s*\\+\\s*([A-Za-z_$][\\w$.\\[\\]()]*)");
    // THE ONE ALLOWLISTED SHAPE, WITH ITS REASON. api/_lib/leg-overlap.js
    // encodes through a NAMESPACED encoder (`spec.enc(...)`) injected by its
    // caller, which a bare-name check cannot recognise. Allowlisted by NAME so
    // a new raw splice in that same file still fails this arm.
    const ENCODED_VIA_NAMESPACE = /\b\w+\.enc\(/;
    const walk = (dir, out) => {
      for (const n of fs.readdirSync(dir)) {
        const p = path.join(dir, n);
        const st = fs.statSync(p);
        if (st.isDirectory()) { if (n !== 'node_modules') walk(p, out); }
        else if (n.endsWith('.js') && n.indexOf('.test.') === -1) out.push(p);
      }
      return out;
    };
    const bad = [];
    for (const f of walk(__dirname, [])) {
      const lines = fs.readFileSync(f, 'utf8').split('\n');
      lines.forEach((line, i) => {
        const s = line.trim();
        if (s.startsWith('//') || s.startsWith('*')) return;
        const m = pat.exec(line);
        if (!m) return;
        const expr = m[1];
        if (/^(encodeURIComponent|encodeURI|enc|String)/.test(expr)) return;
        if (ENCODED_VIA_NAMESPACE.test(line)) return;
        bad.push(path.relative(__dirname, f).replace(/\\/g, '/') + ':' + (i + 1)
                 + '  ' + expr);
      });
    }
    assert.strictEqual(bad.length, 0,
      'raw PostgREST filter interpolation found in ' + bad.length
      + ' place(s):\n       ' + bad.join('\n       '));
  });

  await t('D2. ...and the sweep itself still FINDS a raw splice when one exists. '
        + 'A detector that only ever returns clean is indistinguishable from a '
        + 'detector that matches nothing, which is why this arm feeds it a '
        + 'known-bad line', async () => {
    const OPS = ['eq', 'in'];
    const pat = new RegExp("=(?:" + OPS.join('|') + ")\\.\\s*['\"]\\s*\\+\\s*([A-Za-z_$][\\w$.\\[\\]()]*)");
    const BAD = "  const r = await fetch(rest('t?id=eq.' + command_id), {});";
    const GOOD = "  const r = await fetch(rest('t?id=eq.' + encodeURIComponent(command_id)), {});";
    const mBad = pat.exec(BAD);
    assert.ok(mBad, 'the sweep pattern does not match a known raw splice -- it '
      + 'would report clean on the very defect it exists to find, and D1 would '
      + 'be passing vacuously');
    // THE CAPTURE CARRIES TRAILING PUNCTUATION on purpose -- the class includes
    // `()` so that `encodeURIComponent(x)` is captured whole and recognised.
    // That means `... + command_id)` captures `command_id)`, so the contract is
    // a PREFIX test and never equality. Asserting equality here is what made
    // the first draft of this arm fail against a working pattern.
    assert.ok(/^command_id/.test(mBad[1]),
      'the capture is not the spliced identifier: ' + JSON.stringify(mBad[1]));
    assert.ok(!/^(encodeURIComponent|encodeURI|enc|String)/.test(mBad[1]),
      'the raw fixture was classified as encoded: ' + JSON.stringify(mBad[1]));
    const mGood = pat.exec(GOOD);
    assert.ok(mGood && /^encodeURIComponent/.test(mGood[1]),
      'the sweep cannot tell an encoded splice from a raw one: '
      + JSON.stringify(mGood && mGood[1]));
  });

  console.log('\nb22 postgrest filter encoding: ' + pass + ' passed, ' + fail + ' failed');
  if (fail) console.log('FAILED: ' + failed.join(', '));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no arm result should be read as a pass:', e);
  process.exit(1);
});
