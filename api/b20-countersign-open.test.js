// api/b20-countersign-open.test.js
// ---------------------------------------------------------------------------
// b20's `open` action on api/_lib/countersign-endpoint.js -- THE LIST THE
// idx_<app>_countersign_open INDEX WAS BUILT FOR AND NOTHING QUERIED.
//
// WHY A SUITE AT ALL, WHEN THE DISPATCH ASKED FOR A PANEL. Because the panel
// is the CLIENT of a new API surface, and an endpoint action with no arm is
// the platform's cheapest way to ship a lock that does not lock. The three
// properties below are the ones a panel cannot check for itself:
//
//   1. THE LIST LEAKS NO TOKEN. A token is a bearer credential for exactly one
//      irreversible write. Both SQL schemas say in their own comments that "a
//      readable table of live tokens is a table of signatures waiting to be
//      borrowed", so the arm asserts an ABSENCE -- and asserts it over the
//      SERIALISED response rather than by naming three fields, because the
//      next field added would not be named.
//   2. THE STAGE IS ONE IMPLEMENTATION. `status` and `open` must answer
//      identically for the same row, including for the row that is signed AND
//      expired -- the case four nullable columns gets wrong and the whole
//      reason the stage is computed server-side.
//   3. THE CAP IS REPORTED. Neither token table has a DELETE, so unspent
//      expired rows accumulate without bound. A truncated list that does not
//      say so is indistinguishable from a complete one.
//
// DRIVEN, NOT READ. Each arm calls the real route module through a recorded
// PostgREST stand-in, the same harness shape as
// api/b18-countersign-lock.test.js. These arms prove what the ENDPOINT
// answers; they do not prove anything about the deployed URL, and neither SQL
// file has been run, so in production both apps answer 503 NOT_PROVISIONED
// today. Arm D1 asserts that rather than leaving it as a sentence here.
//
// Exit: 0 all arms passed · 1 an arm FAILED
// ---------------------------------------------------------------------------

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['b20', 'countersign', 'open', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const { signSessionToken } = require('./_lib/auth');
const cs = require('./_lib/countersign');

const HASH = 'b20-open-hash';
const KEY = 'KEY-FOR-' + HASH;
// ── THE FIXTURE DECLARES ITSELF A PLACEHOLDER, FOR THE SECOND TIME ────────
// `tools/redaction_check.py`'s `generic_credential_assignment` matched the
// first spelling of this line and REFUSED THE PUSH -- correct behaviour on a
// 16+ character literal assigned to a name containing `token`, and the gate
// deliberately does not echo the match. b18 hit exactly the same refusal on
// exactly the same kind of line and its fix is reused rather than rediscovered:
// `placeholder` is one of the checker's PLACEHOLDER_MARKERS, so the fixture
// SAYS WHAT IT IS instead of being exempted through `SAIRN_SKIP`.
const FIXTURE_TOKEN = 'b20-open-token-placeholder';

// ── THE ABLATION HARNESS, ADDED 2026-10-20 (hank b24) ─────────────────────
// Same shape as api/b23-iolta-attestation.test.js: mutate ONE named layer,
// re-run THIS FILE'S ARMS in a child, read the child's own FAILED: line, and
// restore in a `finally`. The child runs with ARMS_ONLY so the ablations do
// not recurse.
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const SELF = __filename;
const EP_SRC = path.join(__dirname, '_lib', 'countersign-endpoint.js');
const ARMS_ONLY = process.env.B20_OPEN_ARMS_ONLY === '1';

function runSuite(file, armsOnly) {
  const env = armsOnly
    ? Object.assign({}, process.env, { B20_OPEN_ARMS_ONLY: '1' })
    : process.env;
  try {
    const out = execFileSync(process.execPath, [file], {
      env: env, encoding: 'utf8', stdio: 'pipe' });
    return { exit: 0, out: String(out || '') };
  } catch (e) {
    return { exit: typeof e.status === 'number' ? e.status : -1,
             out: String((e && e.stdout) || '') + String((e && e.stderr) || '') };
  }
}
function failedArms(out) {
  const m = String(out || '').match(/FAILED:\s*(.+)/);
  return m ? m[1].trim().split(/\s*,\s*/).filter(Boolean) : [];
}
function ablate(file, find, replace) {
  // BYTES IN, BYTES OUT. This repo has mixed line endings file by file, so a
  // text-mode round trip can rewrite every line and the "restore" would be a
  // reformat. The anchors here are \n; the CRLF spelling is tried too.
  const originalBuf = fs.readFileSync(file);
  const original = originalBuf.toString('utf8');
  let needle = find, repl = replace;
  let hits = original.split(find).length - 1;
  if (hits !== 1) {
    const crlf = find.replace(/\n/g, '\r\n');
    if (original.split(crlf).length - 1 === 1) {
      needle = crlf; repl = replace.replace(/\n/g, '\r\n'); hits = 1;
    }
  }
  if (hits !== 1) {
    return { ok: false, why: 'the ablation anchor matched ' + hits + ' time(s) '
      + 'in ' + path.basename(file) + ', not exactly 1 -- REFUSING to mutate. '
      + 'FIX THE ANCHOR, do not delete the arm. Anchor: ' + find.slice(0, 100) };
  }
  try {
    fs.writeFileSync(file, Buffer.from(original.replace(needle, repl), 'utf8'));
    const mine = runSuite(SELF, true);
    return { ok: true, exit: mine.exit, arms: failedArms(mine.out), out: mine.out };
  } finally {
    fs.writeFileSync(file, originalBuf);
  }
}

let pass = 0, fail = 0;
const failed = [];
// A DRIFTED ABLATION ANCHOR IS A FAILURE IN THIS FILE, not a third state.
// This suite has no `unproven` channel, and the alternative -- printing a note
// and carrying on -- is how an ablation stops ablating and nobody finds out.
// The message says to RE-SEAT the anchor rather than delete the arm.
function cannot(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l + '  (THE ABLATION DID NOT RUN)');
  if (why) console.log('        ' + String(why).slice(0, 400));
}
function ok(l) { pass++; console.log('  ok    ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l);
  if (why) console.log('        ' + String(why).slice(0, 700));
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

// ── THE HARNESS ───────────────────────────────────────────────────────────
// `opts.rows`        the token rows the SELECT finds.
// `opts.role`        the role the EMPLOYEE LOOKUP returns. The endpoint reads
//                    the role from the database row and not from the token, so
//                    this -- not the session claim -- is what gates.
// `opts.tableMissing` PostgREST's real missing-table answer, shaped as the
//                    handler distinguishes it, not as a generic failure.
function pgMock(calls, opts) {
  opts = opts || {};
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    calls.push({ url: u, method: method });
    if (/_countersign_tokens/.test(u)) {
      if (opts.tableMissing) {
        return { ok: false, status: 404,
                 json: async () => ({ code: 'PGRST205',
                   message: 'Could not find the table in the schema cache' }) };
      }
      // A `token_hash=eq.` filter is the `status` lookup and wants ONE row;
      // anything else is the `open` list. Distinguished on the URL so one
      // mock serves both and the two cannot be fed different fixtures --
      // which is the whole premise of arm B.
      if (/token_hash=eq\./.test(u)) {
        const one = (opts.rows || [])[opts.statusIndex || 0];
        return { ok: true, status: 200, json: async () => (one ? [one] : []) };
      }
      return { ok: true, status: 200, json: async () => (opts.rows || []) };
    }
    if (/_employee_auth/.test(u)) {
      const m = u.match(/employee_id=eq\.([^&]+)/);
      const who = m ? decodeURIComponent(m[1]) : 'emp-1';
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: who,
          role: opts.role || 'owner', active: true }] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

async function endpoint(app, which, body, opts) {
  opts = opts || {};
  const calls = [];
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: app })
    }
  };
  global.fetch = pgMock(calls, opts);
  delete require.cache[require.resolve('./' + which)];
  delete require.cache[require.resolve('./_lib/countersign-endpoint')];
  const h = require('./' + which);
  const res = mockRes();
  await h({ method: 'POST',
            headers: { authorization: 'Bearer ' + KEY,
                       'x-sd-auth': signSessionToken({
                         app: app, employee_id: opts.callerId || 'emp-1',
                         role: opts.sessionRole || 'owner',
                         license_hash: HASH }) },
            body: body }, res);
  return { res: res, calls: calls };
}
const openLaw = (opts) => endpoint('sairnlaw', 'law-countersign', { action: 'open' }, opts);
const openLeg = (opts) => endpoint('sairnlegacy', 'leg-countersign', { action: 'open' }, opts);

// ── THE FIXTURES ──────────────────────────────────────────────────────────
// FOUR ROWS, ONE PER STAGE, and the fourth is the one that matters: SIGNED AND
// EXPIRED. That row is why the stage is computed server-side at all -- a panel
// reading `countersign_employee_id` would render it "signed" when the
// authorisation it carried is dead.
const PAST = '2020-01-01T00:00:00.000Z';
const FUTURE = '2099-01-01T00:00:00.000Z';
const ROW_AWAITING = {
  resource: 'law_trusttx', prepared_by: 'emp-para', prepared_role: 'paralegal',
  countersign_employee_id: null, countersign_role: null, countersigned_at: null,
  spent_at: null, expires_at: FUTURE
};
const ROW_SIGNED = {
  resource: 'law_trusttx', prepared_by: 'emp-para', prepared_role: 'paralegal',
  countersign_employee_id: 'emp-atty', countersign_role: 'attorney',
  countersigned_at: '2026-10-19T00:00:00.000Z',
  spent_at: null, expires_at: FUTURE
};
const ROW_EXPIRED = {
  resource: 'law_trusttx', prepared_by: 'emp-para', prepared_role: 'paralegal',
  countersign_employee_id: null, countersign_role: null, countersigned_at: null,
  spent_at: null, expires_at: PAST
};
const ROW_SIGNED_THEN_EXPIRED = {
  resource: 'law_trusttx', prepared_by: 'emp-para', prepared_role: 'paralegal',
  countersign_employee_id: 'emp-atty', countersign_role: 'attorney',
  countersigned_at: '2020-01-01T00:00:00.000Z',
  spent_at: null, expires_at: PAST
};
const ALL_FOUR = [ROW_AWAITING, ROW_SIGNED, ROW_EXPIRED, ROW_SIGNED_THEN_EXPIRED];

(async function main() {
  console.log('b20 -- the `open` action: the list the index was built for');

  // ── A. THE ACTION EXISTS AND ANSWERS ────────────────────────────────────
  section('A. the action exists, is allowlisted, and stages every row');
  {
    const ep = require('./_lib/countersign-endpoint');
    is(ep.ACTIONS.indexOf('open') !== -1,
       'A1. `open` is in the endpoint\'s ACTIONS allowlist, so the 400 that '
     + 'refuses an unknown action names it too -- the refusal message is '
     + 'derived from this array, not written out',
       JSON.stringify(ep.ACTIONS));

    const a = await openLaw({ rows: ALL_FOUR });
    const b = a.res.body || {};
    is(a.res.statusCode === 200 && Array.isArray(b.items) && b.items.length === 4,
       'A2. four unspent rows in, four staged items out',
       a.res.statusCode + ' ' + JSON.stringify(b).slice(0, 200));

    const stages = (b.items || []).map((i) => i.stage);
    is(JSON.stringify(stages) === JSON.stringify(
         ['awaiting_signature', 'signed', 'expired', 'expired']),
       'A3. THE FOURTH ROW IS THE DELIVERABLE: signed-and-then-expired reads '
     + '`expired`, not `signed`. A panel reading countersign_employee_id would '
     + 'have shown a dead authorisation as a live one',
       JSON.stringify(stages));
  }

  // ── B. ONE STAGE IMPLEMENTATION, NOT TWO ────────────────────────────────
  section('B. `status` and `open` answer identically -- one ladder, not two');
  {
    let agreed = 0;
    const seen = [];
    for (let i = 0; i < ALL_FOUR.length; i++) {
      const viaOpen = await openLaw({ rows: ALL_FOUR });
      const viaStatus = await endpoint('sairnlaw', 'law-countersign',
        { action: 'status', token: FIXTURE_TOKEN },
        { rows: ALL_FOUR, statusIndex: i });
      const o = ((viaOpen.res.body || {}).items || [])[i];
      const s = (viaStatus.res.body || {}).stage;
      seen.push({ open: o && o.stage, status: s });
      if (o && o.stage === s) agreed++;
    }
    is(agreed === ALL_FOUR.length,
       'B1. all four rows get the SAME stage from `open` as from `status`. '
     + 'Both call one `stageOf`; two copies of that ladder would be two '
     + 'answers to "what is this record" and the list is the one a signer reads',
       JSON.stringify(seen));
  }

  // ── C. THE LIST LEAKS NO BEARER CREDENTIAL ──────────────────────────────
  section('C. no token, no token_hash, no content_hash');
  {
    // The fixture rows deliberately DO NOT carry those columns, because the
    // handler's own SELECT does not ask for them -- so this arm proves the
    // SELECT, not the fixture. Asserted by inspecting the query the handler
    // actually sent, and then over the serialised body as a second, blunter
    // check that would survive a future column being added to STAGE_COLUMNS.
    const a = await openLaw({ rows: ALL_FOUR });
    const listCall = a.calls.filter((c) => /_countersign_tokens/.test(c.url)
                                        && !/token_hash=eq\./.test(c.url))[0];
    const sel = listCall ? decodeURIComponent(listCall.url) : '';
    is(sel && !/token_hash/.test(sel.split('select=')[1] || '')
           && !/content_hash/.test(sel),
       'C1. the SELECT asks for no token_hash and no content_hash -- the leak '
     + 'is closed at the query, so no fixture or serialiser is carrying this arm',
       sel.slice(0, 300));

    const serialised = JSON.stringify(a.res.body || {});
    is(!/token_hash|content_hash/.test(serialised)
       && !/"token"/.test(serialised)
       && serialised.indexOf(FIXTURE_TOKEN) === -1
       && serialised.indexOf(cs.hashToken(FIXTURE_TOKEN)) === -1,
       'C2. and the WHOLE serialised response contains no token, no token hash '
     + 'and no content hash. Asserted over the serialisation rather than by '
     + 'naming fields, because the next field added would not be named',
       serialised.slice(0, 300));
  }

  // ── D. THE QUERY IS THE INDEX'S PREDICATE ───────────────────────────────
  section('D. the query matches idx_<app>_countersign_open, and the refusals');
  {
    const a = await openLaw({ rows: [] });
    const listCall = a.calls.filter((c) => /_countersign_tokens/.test(c.url)
                                        && !/token_hash=eq\./.test(c.url))[0];
    const u = listCall ? decodeURIComponent(listCall.url) : '';
    is(/license_hash=eq\./.test(u) && /spent_at=is\.null/.test(u)
       && /order=expires_at/.test(u),
       'D1. license_hash + spent_at is null, ordered by expires_at -- exactly '
     + 'the partial index\'s key and predicate. Written to match the index '
     + 'rather than hoping the planner finds a use for it',
       u.slice(0, 300));

    const miss = await openLaw({ rows: ALL_FOUR, tableMissing: true });
    is(miss.res.statusCode === 503 && eCode(miss.res) === 'NOT_PROVISIONED',
       'D2. with the SQL unrun the list answers 503 NOT_PROVISIONED and names '
     + 'the file -- which is the state production is in TODAY. "Inert until '
     + 'the SQL runs" and "lists everything until the SQL runs" are opposite '
     + 'facts and this is which one it is',
       miss.res.statusCode + ' ' + eCode(miss.res));

    const notSigner = await openLaw({ rows: ALL_FOUR, role: 'paralegal' });
    is(notSigner.res.statusCode === 403
       && eCode(notSigner.res) === 'NOT_QUALIFIED_TO_SIGN',
       'D3. a PARALEGAL is refused the law queue. The gate is '
     + 'profile.signerRoles -- the same set `countersign` checks -- so the '
     + 'list and the act it leads to cannot disagree about who is qualified',
       notSigner.res.statusCode + ' ' + eCode(notSigner.res));

    const legSigner = await openLeg({ rows: [ROW_AWAITING], role: 'director' });
    const legDriver = await openLeg({ rows: [ROW_AWAITING], role: 'livery' });
    is(legSigner.res.statusCode === 200 && legDriver.res.statusCode === 403,
       'D4. and the SAME action gates on each app\'s OWN signer set, driven '
     + 'through both route files: a SAIRNlegacy `director` is let in and a '
     + '`livery` driver is not. One mechanism, two profiles -- not one '
     + 'hardcoded role list serving both',
       'director=' + legSigner.res.statusCode + ' livery=' + legDriver.res.statusCode);
  }

  // ── E. THE CAP IS REPORTED, NEVER SILENT ────────────────────────────────
  section('E. truncation is stated, because neither table has a DELETE');
  {
    const under = await openLaw({ rows: ALL_FOUR });
    is((under.res.body || {}).truncated === false
       && (under.res.body || {}).cap === 200,
       'E1. a short list reports truncated:false and names the cap. The flag '
     + 'is present on BOTH outcomes -- a field that only appears when '
     + 'truncation happened is a field a client forgets to look for',
       JSON.stringify({ t: (under.res.body || {}).truncated,
                        c: (under.res.body || {}).cap }));

    const many = [];
    for (let i = 0; i < 250; i++) many.push(ROW_AWAITING);
    const over = await openLaw({ rows: many });
    const ob = over.res.body || {};
    is(ob.truncated === true && ob.items.length === 200,
       'E2. 250 rows in -> 200 items and truncated:true. One extra row is '
     + 'fetched purely to DETECT the condition: a truncated list that does not '
     + 'say it was truncated is indistinguishable from a complete one, which '
     + 'is this platform\'s most expensive defect shape',
       JSON.stringify({ t: ob.truncated, n: ob.items && ob.items.length }));

    const cap = await openLaw({ rows: [] });
    const capUrl = cap.calls.filter((c) => /_countersign_tokens/.test(c.url)
                                        && !/token_hash=eq\./.test(c.url))[0];
    is(capUrl && /limit=201/.test(decodeURIComponent(capUrl.url)),
       'E3. ...and the limit SENT is cap+1, so the detection is in the query '
     + 'rather than inferred from a full page -- a list of exactly 200 real '
     + 'rows must not report itself as truncated',
       capUrl && decodeURIComponent(capUrl.url).slice(-60));
  }

  // ── F. WHAT THE LIST SAYS IT IS NOT ─────────────────────────────────────
  section('F. the response carries its own limit');
  {
    const a = await openLaw({ rows: ALL_FOUR });
    const b = a.res.body || {};
    is(typeof b.note === 'string' && /read-only/.test(b.note)
       && /prepared it/.test(b.note),
       'F1. the response states that the list is read-only and that authorising '
     + 'needs the reference the PREPARER holds. In the payload rather than in '
     + 'the HTML, so two apps cannot grow two wordings of one limitation',
       b.note);
    is(Array.isArray(b.stages) && b.stages.length === 4
       && b.stages.indexOf('awaiting_signature') !== -1,
       'F2. and it ships the stage vocabulary, so a panel renders the four '
     + 'names the server computes instead of a list of its own that can drift',
       JSON.stringify(b.stages));
  }

  if (ARMS_ONLY) {
    console.log('\n  ' + pass + ' passed, ' + fail + ' failed');
    if (fail) console.log('  FAILED: ' + failed.join(', '));
    process.exit(fail ? 1 : 0);
  }

  // ── G. THE ABLATIONS, ADDED 2026-10-20 (hank b24) ───────────────────────
  // THIS SUITE HAD NONE, and that was found by a census rather than by review:
  // of the nine b18-b23 suites, six carried a real ablation and three did not.
  // Every arm above could have been passing because the thing in FRONT of the
  // guard was working -- fourth's b26 finding H1 in a different file.
  //
  // Per ARM, not per exit code. Each ablation removes ONE named layer from
  // api/_lib/countersign-endpoint.js and names the arm that must redden AND
  // the arms that must stay green, because an ablation that breaks the whole
  // file measures nothing.
  section('G. ABLATIONS -- remove ONE layer and measure what it alone catches');

  const g0 = runSuite(SELF, true);
  is(g0.exit === 0,
     'G0. THE CONTROL: with nothing ablated the arms-only child run is GREEN '
   + '(exit 0). Every ablation below is measured against this',
     'child exit ' + g0.exit + '\n' + String(g0.out).slice(-300));

  // G1. THE STAGE LADDER'S ORDER. Put `signed` ahead of `expired` and the
  // signed-then-expired row reads `signed` -- a record whose signature has
  // lapsed rendering as ready to file. A3 is the arm that sees it.
  const g1 = ablate(EP_SRC,
    "  return row.spent_at ? 'filed'\n       : expired ? 'expired'\n"
    + "       : row.countersign_employee_id ? 'signed'\n"
    + "       : 'awaiting_signature';",
    "  return row.spent_at ? 'filed'\n"
    + "       : row.countersign_employee_id ? 'signed'\n"
    + "       : expired ? 'expired'\n"
    + "       : 'awaiting_signature';");
  if (!g1.ok) {
    cannot('G1. the stage ladder ORDER is load-bearing', g1.why);
  } else {
    is(g1.exit === 1 && g1.arms.indexOf('A3') !== -1,
       'G1. putting `signed` ahead of `expired` makes arm A3 FAIL -- so the '
     + 'ORDER is the policy, and a signed-then-expired row would otherwise '
     + 'render as ready to file',
       'exit ' + g1.exit + ' arms=' + g1.arms.join(','));
    is(g1.arms.indexOf('A1') === -1 && g1.arms.indexOf('C1') === -1,
       'G1b. ...and A1/C1 stay GREEN -- the action still exists and still '
     + 'leaks no token, so one layer was removed and not the floor',
       'arms=' + g1.arms.join(','));
  }

  // G2. THE UNSPENT FILTER. Drop `&spent_at=is.null` and the query no longer
  // matches idx_<app>_countersign_open -- the index this action was built for.
  // D1 is the arm that reads the URL.
  const g2 = ablate(EP_SRC,
    "          '&spent_at=is.null&select=' + STAGE_COLUMNS +",
    "          '&select=' + STAGE_COLUMNS +");
  if (!g2.ok) {
    cannot('G2. the unspent filter is load-bearing', g2.why);
  } else {
    is(g2.exit === 1 && g2.arms.indexOf('D1') !== -1,
       'G2. dropping `spent_at=is.null` makes arm D1 FAIL -- the list would '
     + 'return already-filed records and stop matching the partial index',
       'exit ' + g2.exit + ' arms=' + g2.arms.join(','));
  }

  // G3. THE COLUMN LIST. Add `token_hash` to the shared select and the
  // serialised answer carries a bearer-credential hash. C2 asserts an ABSENCE
  // over the whole serialised response precisely so the NEXT field added is
  // caught without being named, and this is the arm that proves that works.
  const g3 = ablate(EP_SRC,
    "const STAGE_COLUMNS = 'resource,prepared_by,prepared_role,'",
    "const STAGE_COLUMNS = 'token_hash,resource,prepared_by,prepared_role,'");
  if (!g3.ok) {
    cannot('G3. the token-free column list is load-bearing', g3.why);
  } else {
    is(g3.exit === 1
       && (g3.arms.indexOf('C1') !== -1 || g3.arms.indexOf('C2') !== -1),
       'G3. adding `token_hash` to the shared select makes C1 or C2 FAIL -- so '
     + 'the absence assertion really does catch a field nobody named',
       'exit ' + g3.exit + ' arms=' + g3.arms.join(','));
  }

  console.log('\n  ' + pass + ' passed, ' + fail + ' failed');
  if (fail) console.log('  FAILED: ' + failed.join(', '));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no arm result should be read as a pass:', e);
  process.exit(1);
});
