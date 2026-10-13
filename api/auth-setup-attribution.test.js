// api/auth-setup-attribution.test.js
// REQUIREMENT: every api/*-auth.js `setup` action -- the branch that mints a
//   PIN credential for somebody else, i.e. the moment access is GRANTED --
//   records WHO granted it, and tells the caller whether that record landed.
//
// WHAT WAS WRONG, 2026-10-11. FOURTEEN of the seventeen api/*-auth.js files
// wrote a credential row and recorded nothing: no audit event, and the row
// itself carries no `created_by`. The same files' `set_active` branches audit
// every outcome INCLUDING their refusals. So REVOKING access was
// reconstructible and GRANTING it was not, which is the wrong way round.
// Reported by hover2 as seq958.
//
// THE FIGURE IN THAT FINDING WAS 15 OF 17 AND THE REAL ONE IS 14, and the
// reason is the whole reason this file exists rather than a sweep script in
// somebody's scratchpad. A scan keyed on the string `writeAuditLog` cannot see
// api/law-auth.js, which audits its setup through a LOCAL `audit()` wrapper.
// One wrapper, one file, one off-by-one -- in a figure that was then carried
// through three handoffs. This suite matches on the EFFECT (an audit call of
// any accepted spelling inside the real branch) and prints every file it
// classified, so the next person reads a list rather than a number.
//
// ── WHY A SOURCE-READING SUITE AND NOT A ROUND TRIP ────────────────────────
// It cannot be a round trip: THIRTEEN OF THE SEVENTEEN TARGET TABLES DO NOT
// EXIST IN SUPABASE YET (sql/*_audit_log_schema.sql, extracted 2026-10-11 from
// docs/2026-10-07-hank-migration-sql-for-michael.md, NOT RUN), and two of the
// four that do -- stonedesk_audit_log and sairncode_audit_log -- carry an
// event_type CHECK that REJECTS 'pin_setup', which is STEP 0 of that same
// document and also not run. tools/audit_event_type_check.py is the check that
// owns THAT question and exits 1 on it today. This suite owns a different and
// strictly source-level one: is the call there at all, in every file, with the
// result surfaced. Both are necessary; neither is the other.
//
// SAID PLAINLY SO A GREEN BAR HERE IS NOT MISREAD: passing this file means the
// attribution is WIRED. It does not mean a row lands. Only SAIRNlaw's table
// both exists and permits the value today.
//
// Plain node:assert, no framework -- matching api/sd-data-sf-session-gate.test.js.
// Run: node api/auth-setup-attribution.test.js

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const API_DIR = __dirname;

// ── THE BRANCH, BRACE-MATCHED RATHER THAN WINDOWED ────────────────────────
// A fixed character window after `action === 'setup'` is what produced the
// wrong figure in the first place: the window either overruns into the NEXT
// branch (and credits a file for its neighbour's audit call) or stops short of
// the response line (and misses its own). Brace matching has no window to pick.
function setupBranch(src) {
  const at = src.indexOf("action === 'setup'");
  if (at === -1) return null;
  const open = src.indexOf('{', at);
  if (open === -1) return null;
  let depth = 0;
  for (let i = open; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') {
      depth--;
      if (depth === 0) return src.slice(open, i + 1);
    }
  }
  return null;
}

// ── COMMENTS ARE BLANKED BEFORE ANY MATCH ─────────────────────────────────
// Every one of these files now carries a PARAGRAPH about the attribution
// directly above the call. A raw-text match would be satisfied by that
// paragraph alone -- so deleting the call and keeping the comment would leave
// this suite green, which is the precise shape of a check that stopped
// checking. Blanked, not skipped: the line structure is preserved so a
// reported offset still points somewhere real.
// ── ONE STRIPPER, 2026-10-13 (b8 item 2) ──────────────────────────────────
// The paragraph above is right about WHY this exists and the implementation was
// still private. `/\/\/[^\n]*/g` eats the rest of any line containing `//`
// inside a string or a URL, so the "blanked, not skipped" promise above it was
// only half kept: line structure survived, but a call site sitting after an
// `https://` on the same line was removed along with the comment -- and this
// suite's whole point is that deleting a CALL must not leave it green.
//
// THE LOCAL NAME IS KEPT AND IT IS NOT THE LIBRARY'S `stripComments`. The two
// call sites below pass `branch`, a slice of API JavaScript, so the right
// entry point is `stripJs`; the library's `stripComments` is the HTML-aware one
// and would be wrong here. The name stays so the call sites do not move, and
// this comment is why it is not a contradiction.
const { stripJs } = require('../tests/lib/strip_comments.js');
function stripComments(s) {
  return stripJs(s);
}

// Three accepted spellings, because three exist in the tree and all three
// produce a row:
//   auditPinSetup(...)        the shared helper (14 files, 2026-10-11)
//   writeAuditLog(... 'pin_setup' ...)  hand-written (api/sc-auth.js, api/sd-auth.js)
//   audit('pin_setup', ...)   a local wrapper (api/law-auth.js)
function attributionIn(branch) {
  const code = stripComments(branch);
  const helper = /\bauditPinSetup\s*\(/.test(code);
  const direct = /\bwriteAuditLog\s*\(/.test(code) && /'pin_setup'/.test(code);
  const wrapped = /\baudit\s*\(\s*'pin_setup'/.test(code);
  return { helper, direct, wrapped, any: helper || direct || wrapped };
}

// The response must SURFACE the outcome. An audit call whose false return is
// dropped on the floor leaves "recorded" and "not recorded" identical to
// whoever just granted the access -- which is the silent-failure half of the
// same defect, and is why api/sc-auth.js added `attributed` rather than just
// the call.
function surfacesOutcome(branch) {
  const code = stripComments(branch);
  return /attributed\s*:/.test(code) || /\bawait audit\(\s*'pin_setup'/.test(code);
}

function authFiles() {
  return fs.readdirSync(API_DIR)
    .filter((f) => /-auth\.js$/.test(f) && !/\.test\.js$/.test(f))
    .sort();
}

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log('  PASS  ' + name); passed++; }
  catch (e) { console.log('  FAIL  ' + name + '\n        ' + e.message); failed++; }
}

function main() {
  console.log('api/*-auth.js setup attribution -- who granted the access\n');

  const files = authFiles();

  test('the file population was actually found -- a zero-length listing would '
    + 'make every assertion below vacuously true', () => {
    assert.ok(files.length >= 17,
      'expected at least the 17 known api/*-auth.js files, found '
      + files.length + ': ' + files.join(', ') + '. An empty or short '
      + 'population passes every per-file loop below over no data, which is '
      + 'a green run that checked nothing.');
  });

  const branches = {};
  test('every one of them HAS a setup branch this suite can isolate -- an '
    + 'unparseable file must be a FAILURE, never a skip', () => {
    const unparseable = [];
    files.forEach((f) => {
      const src = fs.readFileSync(path.join(API_DIR, f), 'utf8');
      const b = setupBranch(src);
      if (!b) unparseable.push(f);
      else branches[f] = b;
    });
    assert.deepStrictEqual(unparseable, [],
      'no setup branch could be brace-matched in: ' + unparseable.join(', ')
      + '. These would otherwise drop silently out of the loop below and be '
      + 'counted as neither attributed nor missing -- the third state this '
      + 'platform refuses to fold into a pass.');
  });

  test('THE LOAD-BEARING ONE: all 17 setup branches record who granted the '
    + 'access', () => {
    const missing = [];
    const how = {};
    Object.keys(branches).forEach((f) => {
      const a = attributionIn(branches[f]);
      if (!a.any) missing.push(f);
      else how[f] = a.helper ? 'helper' : (a.wrapped ? 'local audit()' : 'direct');
    });
    Object.keys(how).sort().forEach((f) => {
      console.log('        ' + f.padEnd(20) + how[f]);
    });
    assert.deepStrictEqual(missing, [],
      'setup grants a credential and records nothing in: ' + missing.join(', ')
      + '. Each of these can hand somebody a working sign-in with no trace of '
      + 'who did it, while set_active in the same file audits its refusals.');
  });

  test('...and every one SURFACES whether the record landed, because the write '
    + 'is best-effort and returns false on failure', () => {
    const silent = Object.keys(branches).filter((f) => !surfacesOutcome(branches[f]));
    assert.deepStrictEqual(silent, [],
      'the audit outcome is dropped on the floor in: ' + silent.join(', ')
      + '. A false return nobody reads makes an unrecorded attribution '
      + 'indistinguishable from a recorded one to the person who just '
      + 'granted the access.');
  });

  test('NEGATIVE CONTROL: the detector reports a branch with NO audit call, '
    + 'and is NOT satisfied by a comment that merely talks about one. Without '
    + 'this arm every assertion above would pass on a detector that returned '
    + 'true for everything', () => {
    const bare = `{
      const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
      const rows = await r.json();
      res.status(200).json({ ok: true, employee_id, role });
    }`;
    assert.strictEqual(attributionIn(bare).any, false,
      'a setup branch with no audit call of any spelling was reported as '
      + 'attributed');
    const commentOnly = `{
      // WHO GRANTED THE ACCESS IS RECORDED. auditPinSetup(SUPABASE_URL, ...)
      // writeAuditLog(U, K, { event_type: 'pin_setup' }) -- see audit.js
      /* audit('pin_setup', {}) */
      res.status(200).json({ ok: true, employee_id, role });
    }`;
    assert.strictEqual(attributionIn(commentOnly).any, false,
      'PROSE about the attribution satisfied the detector. Every one of the '
      + 'real files carries exactly such a paragraph, so this is the way this '
      + 'suite would go green over deleted code.');
    assert.strictEqual(surfacesOutcome(commentOnly), false,
      'a comment mentioning `attributed` satisfied the outcome check');
  });

  test('NEGATIVE CONTROL: brace matching stops at the END of the setup branch '
    + 'and does not run on into the next one -- otherwise a neighbouring '
    + 'branch\'s audit call would be credited to setup', () => {
    const two = `
      if (action === 'setup') {
        const r = await fetch(x);
        res.status(200).json({ ok: true });
      }
      if (action === 'set_active') {
        await writeAuditLog(U, K, { event_type: 'pin_setup' });
      }`;
    const b = setupBranch(two);
    assert.ok(b, 'the fixture branch did not brace-match at all');
    assert.strictEqual(attributionIn(b).any, false,
      'the set_active branch\'s audit call was read as setup\'s. This is the '
      + 'exact error a fixed-size window makes, and it would report a file '
      + 'as fixed while its grant path records nothing.');
  });

  test('every app id that reaches the shared helper has an AUDIT_TABLE_BY_APP '
    + 'entry -- the helper fails CLOSED on a missing one, so a typo is a '
    + 'silent no-record rather than a crash', () => {
    const map = require('./_lib/audit').AUDIT_TABLE_BY_APP;
    assert.ok(map && Object.keys(map).length > 0,
      'AUDIT_TABLE_BY_APP is absent or empty, so this arm compared nothing');
    const unmapped = [];
    Object.keys(branches).forEach((f) => {
      if (!attributionIn(branches[f]).helper) return;
      const src = fs.readFileSync(path.join(API_DIR, f), 'utf8');
      const m = src.match(/^const APP = '([a-z0-9_]+)'/m);
      assert.ok(m, f + ' calls the helper but has no `const APP` to resolve');
      if (!map[m[1]]) unmapped.push(f + ' (app ' + m[1] + ')');
    });
    assert.deepStrictEqual(unmapped, [],
      'these call auditPinSetup with an app the map does not know, so every '
      + 'grant they record is refused inside the helper and logged '
      + 'server-side only: ' + unmapped.join(', '));
  });

  test('the two apps that share one audit table still BOTH resolve to it -- '
    + 'stonedesk and stonedesk_sub are deliberate, and a map that lost one '
    + 'would split "who was granted access to this licence" across two '
    + 'queries', () => {
    const map = require('./_lib/audit').AUDIT_TABLE_BY_APP;
    assert.strictEqual(map.stonedesk, 'stonedesk_audit_log');
    assert.strictEqual(map.stonedesk_sub, 'stonedesk_audit_log');
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  console.log('\nWHAT A GREEN RUN DOES NOT SAY: that a row lands. Thirteen of '
    + 'the target\ntables are not created in Supabase yet, and '
    + 'stonedesk_audit_log and\nsairncode_audit_log carry an event_type CHECK '
    + 'that REJECTS \'pin_setup\'.\nThat is STEP 0 and STEPS 1-13 of '
    + 'docs/2026-10-07-hank-migration-sql-for-michael.md,\nand '
    + 'tools/audit_event_type_check.py is the check that owns it.');
  if (failed) process.exit(1);
}

main();
