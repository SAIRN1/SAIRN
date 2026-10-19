// tests/sd_data_read_unreadable_not_empty.js
// OWNER: cody
// written 2026-10-19, batch b26, item 3
//
// THE CONCEPT UNDER TEST: a read that could not be performed is not an empty
//   table, so a 400 on a read path is CLASSIFIED before any
//   `provisioned: false` is sent -- an undefined-column 400 means the table
//   EXISTS and may be full (503 SCHEMA_OUTDATED), a genuine missing relation
//   falls through to the caller's own `provisioned: false` which is the one
//   case where that answer is TRUE, and a 400 that cannot be classified
//   answers 502 rather than being folded into either.
//
//   node tests/sd_data_read_unreadable_not_empty.js
//
// Exit: 0 every arm passed · 1 an arm FAILED · 3 COULD NOT RUN
//
// ── WHY THIS FILE EXISTS AND WHAT IT IS NOT ────────────────────────────────
// b26 converted 150 read guards in api/sd-data.js that answered HTTP 200
// `{ ok: true, data: [], provisioned: false }` for EVERY 400 -- a dropped or
// renamed column rendered as "this table is empty", at HTTP 200, with nothing
// in the answer that is an error. That is AFFIRMATIVE FALSE SUCCESS on a read
// path and it is the shape fourth/H1 routed for mech_site_assets on
// 2026-10-15: "a compliance board for a refrigerant registry that says 'no
// assets on file' while the table holds fifty of them".
//
// A CONVERSION OF 150 SITES WITH NO ARM IS NOT EVIDENCE OF ANYTHING. The
// conversion is mechanical and `node --check` says only that it parses. This
// file drives ONE converted branch through the real handler and requires the
// four answers to be FOUR DIFFERENT ANSWERS -- and then ABLATES the inserted
// line in a COPY of api/ and requires the arms to go RED, because an arm that
// cannot be made to fail is not an arm.
//
// IT DOES NOT ASSERT that all 150 are correct. It asserts that the helper
// behaves, that one real converted branch reaches it, and that the POPULATION
// is what the converter said it was -- measured from source on every run, so
// a figure printed here can never be older than the file it describes.
//
// THE SUBJECT IS alf_op_audits READ, deliberately. It is a TIER A append-only
// operational-audit log in SAIRNcare, it is the read whose write sibling
// already carries the whole notProvisioned() story (A1/C1 in
// tests/sd_data_not_provisioned_misclass.js), and its 200-shape carries an
// extra `summary` field -- so it also demonstrates the one thing the helper
// was designed around: THE CALLER KEEPS ITS OWN LITERAL. A helper that sent
// the 200 itself would have had to flatten twenty-one distinct shapes.

'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');

const ROOT = path.join(__dirname, '..');
// ONE INJECTION POINT, never set on an ordinary run: the ablation points this
// at a MUTATED COPY so the insertion can be removed without editing api/.
const SD_DATA = process.env.SAIRN_B26_SD_DATA
  || path.join(ROOT, 'api/sd-data.js');

let pass = 0;
const failed = [];
const notes = [];

function ok(l) { pass += 1; console.log('  ok   ' + l); }
function bad(l, why) {
  failed.push(l);
  console.log('  FAIL ' + l + (why ? '\n         ' + String(why).slice(0, 460) : ''));
}
function section(t) { console.log('\n' + t); }
function couldNotRun(why) {
  console.log('COULD NOT RUN: ' + why + ' Nothing was verified.');
  process.exit(3);
}

if (!fs.existsSync(SD_DATA)) couldNotRun(SD_DATA + ' does not exist.');
const API_DIR = path.dirname(SD_DATA);
const SRC = fs.readFileSync(SD_DATA, 'utf8').replace(/\r\n/g, '\n');

// ── THE SUBJECT BRANCH, CLOSED BY BALANCED BRACES ──────────────────────────
// Not by a terminator and not by a character window. The sibling suite paid
// for the other way round: a `\n    if (resource === ` terminator overran by
// a factor of 130 and a precondition arm then reported a shipped defect as
// already fixed.
const OPA_READ = "if (resource === 'alf_op_audits' && action === 'read') {";

// The same balanced-brace slice, over ANY source string. The ablation needs
// it over the mutated COPY, which is a different string from SRC -- and the
// arm that caught the wrong-branch mutation could not have been written
// without it.
function branchIn(text, guard) {
  const i = text.indexOf(guard);
  if (i < 0) return '';
  let j = text.indexOf('{', i);
  if (j < 0) return '';
  let depth = 0;
  for (; j < text.length; j += 1) {
    if (text[j] === '{') depth += 1;
    else if (text[j] === '}') {
      depth -= 1;
      if (depth === 0) return text.slice(i, j + 1);
    }
  }
  return '';
}

function branchOf(guard) {
  const i = SRC.indexOf(guard);
  if (i < 0) return null;
  let j = SRC.indexOf('{', i);
  if (j < 0) return null;
  let depth = 0;
  for (; j < SRC.length; j += 1) {
    if (SRC[j] === '{') depth += 1;
    else if (SRC[j] === '}') {
      depth -= 1;
      if (depth === 0) return SRC.slice(i, j + 1);
    }
  }
  return null;
}

section('PRECONDITIONS -- each a third state, never folded into a pass');
const n = SRC.split(OPA_READ).length - 1;
if (n !== 1) {
  couldNotRun('the branch guard ' + JSON.stringify(OPA_READ) + ' occurs ' + n
            + ' times in ' + SD_DATA + ', so the subject branch could not be '
            + 'located unambiguously.');
}
const BRANCH = branchOf(OPA_READ);
if (!BRANCH) couldNotRun('the subject branch could not be sliced out.');
if (BRANCH.indexOf("resource === 'alf_op_audits' && action === 'write'") >= 0) {
  couldNotRun('the branch slice has OVERRUN into the write branch, so every '
            + 'arm that reads it is reading the wrong code.');
}
ok('P1. the alf_op_audits READ branch located by its own `resource ===` guard '
   + 'and closed by BALANCED BRACES (' + BRANCH.length + ' chars), and the '
   + 'slice does NOT contain the write branch');

// ── THE HELPER MUST EXIST. FAIL CLOSED (PR 1.11). ──────────────────────────
// A suite that drives a handler calling a function that is not there would
// report a 500 and read as a behaviour finding. The dependency is NAMED.
if (SRC.indexOf('async function unreadableNotEmpty(res, r, what) {') < 0) {
  couldNotRun('api/sd-data.js does not define unreadableNotEmpty(), which is '
            + 'the whole subject of this file. It was either never landed or '
            + 'has been removed -- this is NOT a behaviour failure and is not '
            + 'reported as one.');
}
ok('P2. unreadableNotEmpty() is DEFINED in the handler under test -- named as '
   + 'a precondition rather than discovered as a 500');

// COMMENT-STRIPPED, because this branch carries a comment and the sibling
// suite has a recorded case of a precondition satisfied by a comment ABOUT
// the code it was checking for.
const CODE = BRANCH.split('\n').map((l) => l.replace(/\/\/.*$/, '')).join('\n');
if (/if \(await unreadableNotEmpty\(res,\s*\w+,\s*resource\)\) return;/.test(CODE)) {
  ok('P3. ...and the subject branch CALLS it, with arguments, measured on '
     + 'COMMENT-STRIPPED source. So R1-R4 below are REGRESSION arms. If the '
     + 'conversion is ever reverted, P3 goes red before the behaviour arms do '
     + 'and names why');
} else {
  bad('P3. the alf_op_audits read branch no longer calls '
      + '`unreadableNotEmpty(res, …, resource)` -- THE b26 CONVERSION HAS '
      + 'BEEN REVERTED HERE. R1 and R3 are about to fail for a real reason '
      + 'and this arm is the one that says so', CODE.slice(0, 500));
}

// ── THE POPULATION, MEASURED ON THIS RUN AND NOT QUOTED ────────────────────
// A number typed into a document drifts toward the first figure somebody
// wrote down -- which is how "151/57" survived six batches as the headline
// for a population that was really 150 real guards plus a COMMENT and a
// value-returning closure guard.
const SHAPE = /if \((\w+)\.status === 404 \|\| \1\.status === 400\) \{/g;
const POP = { total: 0, read_helper: 0, write_helper: 0, raw503: 0, raw200: 0,
              other: 0 };
let m;
SHAPE.lastIndex = 0;
while ((m = SHAPE.exec(SRC)) !== null) {
  POP.total += 1;
  // Balanced-brace branch, NOT a line window. A fixed window is the thing
  // b24 named "window bleed" and measured at 1-of-4 precision in a different
  // tool; the sibling suite's own counter uses a 6-line window and counts an
  // occurrence inside a COMMENT.
  let j = SRC.indexOf('{', m.index);
  let d = 0;
  let end = -1;
  for (let k = j; k < SRC.length; k += 1) {
    if (SRC[k] === '{') d += 1;
    else if (SRC[k] === '}') { d -= 1; if (d === 0) { end = k + 1; break; } }
  }
  const b = end > 0 ? SRC.slice(j, end) : '';
  if (b.indexOf('unreadableNotEmpty(') >= 0) POP.read_helper += 1;
  else if (/notProvisioned(Text)?\s*\(\s*(res|response)\s*,/.test(b)) POP.write_helper += 1;
  else if (/status\(503\)/.test(b) && b.indexOf('NOT_PROVISIONED') >= 0) POP.raw503 += 1;
  else if (/status\(200\)/.test(b) && b.indexOf('provisioned: false') >= 0) POP.raw200 += 1;
  else POP.other += 1;
}
ok('P4. the guard population is MEASURED from source on this run, by BALANCED '
   + 'BRACE and not by a line window: ' + POP.total + ' guards -- '
   + POP.read_helper + ' through unreadableNotEmpty(), ' + POP.write_helper
   + ' through notProvisioned(), ' + POP.raw503 + ' raw 503, ' + POP.raw200
   + ' raw 200, ' + POP.other + ' other');
if (POP.read_helper < 100) {
  bad('P5. the b26 read conversion must still be present at scale -- at least '
      + '100 guards routing through unreadableNotEmpty(). Fewer means a bulk '
      + 'revert, which no single-branch arm would notice',
      JSON.stringify(POP));
} else {
  ok('P5. ...and the read conversion is present AT SCALE ('
     + POP.read_helper + ' guards), so a bulk revert is visible here and not '
     + 'only at the one branch P3 checks');
}

// ── THE HARNESS. licence, session and fetch mocked; nothing real is reached ─
const LIC_HASH = 'hash-of-the-b26-unreadable-licence';
const LICENCE = require.resolve(path.join(API_DIR, '_lib/license.js'));
let LIC_APP = 'sairncare';
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: {
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: LIC_HASH,
      stripe_subscription_id: 'sub_1', trial_ends_at: null, app_id: LIC_APP
    }),
    hashLicense: () => LIC_HASH,
  },
};

process.env.SUPABASE_URL = 'https://example.invalid';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-for-the-test';
process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  process.env[['SD', 'AUTH', 'SECRET'].join('_')]
  || ['b26', 'unreadable', String(process.pid)].join('-');
const { signSessionToken } = require(path.join(API_DIR, '_lib/auth.js'));

// THE SESSION HEADER IS READ OUT OF auth.js, NOT TYPED. The blob-scope suite
// paid for the other way round: `x-sd-session` was typed, tokenFromRequest()
// reads `x-sd-auth`, and every gated site failed its precondition -- a suite
// reporting defects and measuring none.
const AUTH_SRC = fs.readFileSync(path.join(API_DIR, '_lib/auth.js'), 'utf8');
const HDR_M = AUTH_SRC.match(/function tokenFromRequest\(req\)\s*\{\s*\n\s*const h = req\.headers\[['"]([a-z0-9-]+)['"]\]/);
if (!HDR_M) {
  couldNotRun('the session header could not be read out of '
            + 'api/_lib/auth.js tokenFromRequest(), so this suite cannot '
            + 'present a session and every arm would fail its precondition '
            + 'for a reason that is not about the classification.');
}
const SESSION_HEADER = HDR_M[1];

let inject = null;
global.fetch = async (url, opts) => {
  const u = String(url);
  const method = (opts && opts.method) || 'GET';
  if (inject && u.indexOf(inject.table) >= 0 && method === inject.method) {
    const raw = typeof inject.body === 'string'
      ? inject.body : JSON.stringify(inject.body);
    return {
      ok: false, status: inject.status,
      json: async () => (typeof inject.body === 'string' ? null : inject.body),
      text: async () => raw,
    };
  }
  if (/_employee_auth\?/.test(u)) {
    return { ok: true, status: 200, json: async () => [{ active: true }] };
  }
  return { ok: true, status: 200, json: async () => [] };
};

delete require.cache[require.resolve(SD_DATA)];
const handler = require(SD_DATA);

function fakeRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}

async function read(opts) {
  const o = opts || {};
  LIC_APP = 'sairncare';
  inject = o.inject || null;
  const headers = { authorization: 'Bearer testkey' };
  headers[SESSION_HEADER] = signSessionToken({
    app: 'sairncare', employee_id: 'E1', role: 'owner',
    license_hash: LIC_HASH });
  const req = { method: 'POST', headers: headers,
                body: { action: 'read', resource: 'alf_op_audits',
                        payload: {} } };
  const res = fakeRes();
  await handler(req, res);
  inject = null;
  return res;
}

function code(res) {
  return (res.body && res.body.error && res.body.error.code) || '';
}

const TBL = 'alf_op_audits?license_hash';
// Named after a column that select ACTUALLY ASKS FOR, so the fixture is a
// state the store can really be in rather than a plausible-looking string.
const PG_42703 = { code: '42703',
  message: 'column alf_op_audits.reviewed_by does not exist',
  details: null, hint: null };
const PG_404 = { code: 'PGRST205',
  message: 'Could not find the table \'public.alf_op_audits\' in the schema '
  + 'cache', details: null, hint: null };
const PG_RELATION = { code: '42P01',
  message: 'relation "public.alf_op_audits" does not exist',
  details: null, hint: null };
// A 400 THE CLASSIFIER CANNOT CLASSIFY. PostgREST's own operator-parse
// refusal -- a real body, not an invented one, and the state a BUG IN THIS
// FILE produces rather than a missing migration.
const PG_UNCLASSIFIABLE = { code: 'PGRST100',
  message: 'unexpected "x" expecting "-", digit, "." or end of input',
  details: 'unexpected "x" expecting "-", digit, "." or end of input',
  hint: null };

(async function main() {
  console.log('READ-SIDE: UNREADABLE IS NOT EMPTY -- criteria 2026-10-19.1');
  console.log('handler under test: ' + SD_DATA);

  section('C. CONTROL FIRST -- without it nothing below is attributable');
  const c0 = await read({});
  if (c0.statusCode === 200 && c0.body && c0.body.provisioned === true) {
    ok('C0. CONTROL, store healthy: the read answers 200 with '
       + '`provisioned: true` -- so every arm below is a comparison between '
       + 'two REAL answers and not a harness that never reached the branch');
  } else {
    bad('C0. CONTROL, store healthy: the read must answer 200 with '
        + '`provisioned: true`, or nothing below has measured the guard',
        'status=' + c0.statusCode + ' body='
        + JSON.stringify(c0.body).slice(0, 300));
  }

  section('R. THE FOUR STATES, AND THEY MUST BE FOUR DIFFERENT ANSWERS');

  const r1 = await read({ inject: { table: TBL, method: 'GET', status: 400,
                                    body: PG_42703 } });
  if (r1.statusCode === 503 && code(r1) === 'SCHEMA_OUTDATED') {
    ok('R1. a 400 carrying Postgres 42703 -- A DROPPED OR RENAMED COLUMN -- '
       + 'answers 503 SCHEMA_OUTDATED and is NOT reported as an empty table. '
       + 'This is the arm the whole conversion exists for: the table may hold '
       + 'fifty audit observations and the old answer was `data: []` at HTTP '
       + '200 with nothing in it that is an error');
  } else {
    bad('R1. a 42703 on the read must answer 503 SCHEMA_OUTDATED. An HTTP 200 '
        + '`provisioned: false` here is AFFIRMATIVE FALSE SUCCESS on a Tier A '
        + 'append-only compliance log',
        'status=' + r1.statusCode + ' code=' + JSON.stringify(code(r1))
        + ' body=' + JSON.stringify(r1.body).slice(0, 260));
  }

  const r2 = await read({ inject: { table: TBL, method: 'GET', status: 404,
                                    body: PG_404 } });
  if (r2.statusCode === 200 && r2.body && r2.body.provisioned === false) {
    ok('R2. CONTROL: a GENUINE missing table still answers 200 '
       + '`provisioned: false` -- the fix did not trade one wrong answer for '
       + 'another. R1 and R2 together are the pair, and R2 is the one case '
       + 'where `provisioned: false` is TRUE');
  } else {
    bad('R2. a genuine missing table must still answer 200 '
        + '`provisioned: false`. If R1 is green and R2 is red the classifier '
        + 'has been pointed the wrong way rather than fixed',
        'status=' + r2.statusCode + ' body='
        + JSON.stringify(r2.body).slice(0, 260));
  }

  const r3 = await read({ inject: { table: TBL, method: 'GET', status: 400,
                                    body: PG_UNCLASSIFIABLE } });
  if (r3.statusCode === 502 && code(r3) === 'UPSTREAM_UNCLASSIFIED') {
    ok('R3. a 400 the classifier CANNOT classify answers 502 '
       + 'UPSTREAM_UNCLASSIFIED and is NOT folded into either of the other '
       + 'two. "Could not tell" is a third state; folding it in is how the '
       + 'original defect was built. NAMED TRADE: a malformed-filter bug in '
       + 'api/sd-data.js used to render as an empty board and now renders as '
       + 'a 502 -- louder, and it was always a defect and always invisible');
  } else {
    bad('R3. an unclassifiable 400 must answer 502 UPSTREAM_UNCLASSIFIED',
        'status=' + r3.statusCode + ' code=' + JSON.stringify(code(r3))
        + ' body=' + JSON.stringify(r3.body).slice(0, 260));
  }

  const r4 = await read({ inject: { table: TBL, method: 'GET', status: 400,
                                    body: PG_RELATION } });
  if (r4.statusCode === 200 && r4.body && r4.body.provisioned === false) {
    ok('R4. a 400 that says `relation ... does not exist` -- which is how '
       + 'PostgREST answers a missing table on SOME versions, and the real '
       + 'reason 400 was folded in with 404 in the first place -- still '
       + 'answers 200 `provisioned: false`. THE ORIGINAL REASON FOR THE '
       + 'DEFECT IS PRESERVED RATHER THAN DISCARDED');
  } else {
    bad('R4. a 400 carrying `relation ... does not exist` must answer 200 '
        + '`provisioned: false` -- the reason the 400 was folded in with the '
        + '404 is real and must survive the fix',
        'status=' + r4.statusCode + ' body='
        + JSON.stringify(r4.body).slice(0, 260));
  }

  // ── THE FOUR MUST BE FOUR. Four green arms could still be four copies of
  //    one answer if the fixtures happened to collide.
  const sig = (x) => x.statusCode + '|' + JSON.stringify(x.body);
  const distinct = new Set([sig(r1), sig(r2), sig(r3)]).size;
  if (distinct === 3 && sig(r2) === sig(r4)) {
    ok('R5. and the answers are REALLY DISTINCT: 42703, a missing table and '
       + 'an unclassifiable 400 produce three different (status, body) pairs, '
       + 'while the missing-relation 400 produces the SAME bytes as the 404 -- '
       + 'which is correct, they are the same state');
  } else {
    bad('R5. the three states must produce three distinct answers and the two '
        + 'missing-table spellings must produce the same one',
        'distinct=' + distinct + ' r2===r4: ' + (sig(r2) === sig(r4))
        + '\n         r1=' + sig(r1).slice(0, 120)
        + '\n         r2=' + sig(r2).slice(0, 120)
        + '\n         r3=' + sig(r3).slice(0, 120)
        + '\n         r4=' + sig(r4).slice(0, 120));
  }
  notes.push('42703        -> ' + sig(r1).slice(0, 150));
  notes.push('404          -> ' + sig(r2).slice(0, 150));
  notes.push('400 PGRST100 -> ' + sig(r3).slice(0, 150));
  notes.push('400 42P01    -> ' + sig(r4).slice(0, 150));

  // ── THE ABLATION. An arm that cannot be made to fail is not evidence. ────
  section('A. ABLATION -- remove the inserted line in a COPY and require RED');
  if (process.env.SAIRN_B26_SD_DATA) {
    ok('A1. (not run: this IS the ablation child)');
  } else {
    const INSERT = BRANCH.match(
      /\n(\s+)if \(await unreadableNotEmpty\(res, (\w+), resource\)\) return;/);
    if (!INSERT) {
      bad('A1. PRECONDITION: the inserted classification line could not be '
          + 'matched inside the subject branch, so the ablation could not be '
          + 'built. Read P3, which answers whether it is there at all',
          BRANCH.slice(0, 600));
    } else {
      const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'b26-unreadable-'));
      const copyDir = path.join(tmp, 'api');
      // ── LIBRARY DOWN FIRST, THEN THE MUTATION, THEN READ IT BACK ────────
      // b24's ablation harness wrote the subject first and copied api/_lib
      // OVER it, so for any subject inside api/_lib the --before leg silently
      // drove the DISK copy and reported an arm that does not exist at HEAD.
      // The write is READ BACK AND COMPARED here -- an assertion rather than
      // a careful ordering, because that was the third such defect.
      fs.cpSync(path.join(ROOT, 'api'), copyDir, { recursive: true });
      const copy = path.join(copyDir, 'sd-data.js');
      // ── THE MUTATION IS SCOPED TO THE SUBJECT BRANCH, NOT THE FILE ──────
      // THE FIRST SPELLING WAS `src.replace(INSERT[0], '')` AND IT ABLATED
      // THE WRONG BRANCH, recorded rather than quietly fixed. The inserted
      // line is BYTE-IDENTICAL at all 150 converted sites, so a file-wide
      // replace removes the FIRST one -- a branch several thousand lines away
      // from the subject -- and the child would then have reported R1 and R3
      // GREEN while the thing the suite claims to ablate was untouched. **An
      // ablation that mutates a different instance of the same pattern is a
      // control that proves nothing and reads as one that proves everything.**
      // Caught by the readback guard b24 paid for, firing for a different
      // reason than it was written for.
      const copySrc = fs.readFileSync(copy, 'utf8').replace(/\r\n/g, '\n');
      const bi = copySrc.indexOf(OPA_READ);
      const before = copySrc.split(INSERT[0]).length - 1;
      if (bi < 0 || before < 1) {
        bad('A1. PRECONDITION on the COPY: the subject branch or the inserted '
            + 'line could not be found in it, so the mutation could not be '
            + 'scoped', 'branch index ' + bi + ', insertions ' + before);
        fs.rmSync(tmp, { recursive: true, force: true });
      } else {
      const head = copySrc.slice(0, bi);
      const tailSrc = copySrc.slice(bi).replace(INSERT[0], '');
      const want = head + tailSrc;
      fs.writeFileSync(copy, want, 'utf8');
      const back = fs.readFileSync(copy, 'utf8').replace(/\r\n/g, '\n');
      const after = back.split(INSERT[0]).length - 1;
      const subjGone = branchIn(back, OPA_READ).indexOf('unreadableNotEmpty(') < 0;
      if (back !== want || after !== before - 1 || !subjGone) {
        bad('A1. the ablated copy is not what was intended, so the child '
            + 'would have driven the wrong code. THIS IS THE ARM b24 ADDED '
            + 'AFTER A SILENT CLOBBER DROVE THE DISK COPY FOR A WHOLE LEG, '
            + 'and it is asserting THREE things: the write read back, the '
            + 'insertion count fell by EXACTLY ONE, and the one that went is '
            + 'the SUBJECT branch\'s',
            'readback matches: ' + (back === want)
            + ', insertions ' + before + ' -> ' + after
            + ' (want ' + (before - 1) + ')'
            + ', subject branch clean: ' + subjGone);
        fs.rmSync(tmp, { recursive: true, force: true });
      } else {
        const { execFileSync } = require('child_process');
        let out = '';
        let childCode = null;
        try {
          out = execFileSync(process.execPath, [__filename], {
            encoding: 'utf8',
            env: Object.assign({}, process.env, { SAIRN_B26_SD_DATA: copy }),
            cwd: ROOT,
          });
          childCode = 0;
        } catch (e) {
          out = (e.stdout || '') + (e.stderr || '');
          childCode = e.status;
        }
        const r1Red = /^  FAIL R1\. /m.test(out);
        const r3Red = /^  FAIL R3\. /m.test(out);
        const p3Red = /^  FAIL P3\. /m.test(out);
        const r2Green = /^  ok   R2\. /m.test(out);
        if (r1Red && r3Red && p3Red && r2Green) {
          ok('A1. ABLATION on a COPY of api/, the ONE inserted line removed '
             + 'and nothing else: R1 goes RED, R3 goes RED, P3 goes RED and '
             + '**R2 STAYS GREEN**. So the arms measure THE INSERTION and not '
             + 'something else -- R2 green in both legs is what makes R1 and '
             + 'R3 attributable, because a mutation that broke the whole '
             + 'branch would take R2 with it (child exit ' + childCode + ')');
        } else {
          bad('A1. ABLATION: with the inserted line removed in a copy, R1, R3 '
              + 'and P3 must go RED and R2 must stay GREEN. If they do not, '
              + 'these arms are no longer measuring the conversion and green '
              + 'ones mean nothing',
              'child exit ' + childCode + '  R1 red: ' + r1Red
              + '  R3 red: ' + r3Red + '  P3 red: ' + p3Red
              + '  R2 green: ' + r2Green + '\n         ' + out.slice(-700));
        }
        fs.rmSync(tmp, { recursive: true, force: true });
      }
      }
    }
  }

  if (notes.length) {
    section('MEASURED, NOT ASSERTED -- the answers as shipped');
    notes.forEach((x) => console.log('  * ' + x));
  }

  console.log('\n' + pass + ' passed, ' + failed.length + ' failed');
  if (failed.length) {
    console.log(failed.length + ' ARM(S) FAILED:');
    failed.forEach((f) => console.log('  - ' + f));
    console.log('\nNO ARM HERE IS EXPECTED RED. A P arm means an anchor moved '
              + 'or the conversion was reverted; C0 means the branch was not '
              + 'reached and nothing below it is attributable; an R arm is a '
              + 'behaviour regression in the read-side classifier; and A1 '
              + 'means the ablation can no longer make R1 and R3 fail, which '
              + 'makes every green R arm worthless.');
    process.exit(1);
  }
  process.exit(0);
}());
