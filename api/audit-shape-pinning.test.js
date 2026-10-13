// api/audit-shape-pinning.test.js
// REQUIREMENT: the two credential-grant audit shapes this platform ships stay
//   as they are, and neither is normalized into the other by accident.
//
// ── WHY A TEST THAT PINS A DIVERGENCE INSTEAD OF REMOVING IT ───────────────
// Seventeen api/*-auth.js files record who granted an employee credential.
// SIXTEEN use one shape and api/law-auth.js uses another:
//
//   the family   detail: { target: <employee granted>, granted_role: <role> }
//                via api/_lib/audit.js auditPinSetup(), or hand-written in
//                api/sc-auth.js and api/sd-auth.js with the same keys
//
//   SAIRNlaw     audit('pin_setup', { employee_id, role, detail: { by } })
//                -- a `detail` key NESTED INSIDE `detail`
//
// MICHAEL DECIDED ON 2026-10-13 TO LEAVE IT DIVERGENT. The reason it is a
// decision and not an oversight: normalising SAIRNlaw would rewrite the
// recorded shape of rows ALREADY IN a live legal-sector audit table.
// `sairnlaw_audit_log` is the ONLY one of the seventeen target tables that both
// exists in Supabase AND permits `pin_setup` today, so it is the only one with
// real rows in it -- which makes it the one app where a shape change is a data
// migration rather than a code edit.
//
// ── SO THE RISK IS NOT THE DIVERGENCE, IT IS A TIDY-UP ────────────────────
// A divergence with a reason is stable. A divergence with a reason that lives
// only in a commit message is one refactor away from being "cleaned up" by
// somebody who reads sixteen files doing one thing and one doing another and
// draws the obvious conclusion. This suite is what makes that attempt fail
// loudly instead of silently migrating a regulated log.
//
// IT PINS BOTH DIRECTIONS, which is the part that makes it a pin and not a
// preference: the family must not drift toward SAIRNlaw's nesting either.
//
// ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
// It does not write a row, reach a database, or prove either shape is the
// right one. It reads source. It also does NOT claim the two shapes are
// equivalent or queryable together -- they are not, and that is the cost of
// the decision, stated here rather than discovered by whoever first tries to
// answer "who was granted access" across all seventeen apps.
//
// NO ROW IS REWRITTEN BY ANYTHING IN THIS FILE.
//
// Run: node api/audit-shape-pinning.test.js

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const API = __dirname;

// Line-based comment blanking, the repo idiom -- see
// api/sd-data-sf-session-gate.test.js:83 and the longer note in
// api/hydrate-gate-coupling.test.js about why the regex form is unsafe on big
// files. Every one of these auth files carries a PARAGRAPH about its audit
// call, so a raw match would be satisfied by the prose describing the code.
function code(src) {
  return src.split('\n')
    .map((l) => (/^\s*(\/\/|\*|\/\*)/.test(l) ? '' : l))
    .join('\n');
}

function authFiles() {
  return fs.readdirSync(API)
    .filter((f) => /-auth\.js$/.test(f) && !/\.test\.js$/.test(f))
    .sort();
}

function setupBranch(src) {
  const at = src.indexOf("action === 'setup'");
  if (at === -1) return null;
  const open = src.indexOf('{', at);
  if (open === -1) return null;
  let depth = 0;
  for (let i = open; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (depth === 0) return src.slice(open, i + 1); }
  }
  return null;
}

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log('  PASS  ' + name); passed++; }
  catch (e) { console.log('  FAIL  ' + name + '\n        ' + e.message); failed++; }
}

function main() {
  console.log('credential-grant audit shapes -- two of them, pinned\n');

  const files = authFiles();
  test('the file population was found -- a short listing would make every arm '
    + 'below vacuous', () => {
    assert.ok(files.length >= 17,
      'expected at least 17 api/*-auth.js files, found ' + files.length);
  });

  // ── SHAPE 1: THE FAMILY ──────────────────────────────────────────────────
  test('api/_lib/audit.js auditPinSetup() emits the FAMILY shape: event_type '
    + 'pin_setup, detail keys exactly { target, granted_role }', () => {
    const src = code(fs.readFileSync(path.join(API, '_lib', 'audit.js'), 'utf8'));
    const fn = src.match(/async function auditPinSetup\([\s\S]{0,1200}?\n\}/);
    assert.ok(fn, 'auditPinSetup() could not be isolated in api/_lib/audit.js, '
      + 'so this arm checked NOTHING -- a third state, not a pass');
    const body = fn[0];
    assert.match(body, /event_type:\s*'pin_setup'/,
      'the shared helper no longer emits event_type pin_setup. Every table DDL '
      + 'in sql/*_audit_log_schema.sql lists that exact value in its CHECK '
      + 'constraint, so a renamed event is a write that fails at the database '
      + 'and returns attributed:false.');
    assert.match(body, /detail:\s*\{\s*target:\s*target,\s*granted_role:\s*granted_role\s*\}/,
      'the shared helper\'s detail keys changed. api/sc-auth.js and '
      + 'api/sd-auth.js write the same two keys BY HAND, so a change here '
      + 'silently splits the family in two.');
    assert.doesNotMatch(body, /detail:\s*\{[^}]*\bdetail\b/,
      'the FAMILY shape has grown a `detail` nested inside `detail`. That is '
      + 'SAIRNlaw\'s shape, and the family drifting toward it is the direction '
      + 'this suite pins against just as hard as the other way round.');
  });

  test('...and the two hand-written family members still agree with the helper '
    + 'key for key', () => {
    ['sc-auth.js', 'sd-auth.js'].forEach((f) => {
      const b = setupBranch(code(fs.readFileSync(path.join(API, f), 'utf8')));
      assert.ok(b, f + ' has no isolable setup branch');
      assert.match(b, /detail:\s*\{\s*target:\s*employee_id,\s*granted_role:\s*role\s*\}/,
        f + ' no longer writes { target, granted_role } by hand. These two '
        + 'predate the helper and were deliberately NOT converted to it -- '
        + 'rewriting working audit paths to route through new code is a risk '
        + 'with no finding behind it -- so they are pinned here instead.');
    });
  });

  // ── SHAPE 2: SAIRNlaw, LEFT DIVERGENT ON PURPOSE ─────────────────────────
  test('api/law-auth.js KEEPS its divergent shape: audit(\'pin_setup\', ...) '
    + 'with a `detail` nested inside `detail`', () => {
    const b = setupBranch(code(fs.readFileSync(path.join(API, 'law-auth.js'), 'utf8')));
    assert.ok(b, 'api/law-auth.js has no isolable setup branch');
    assert.match(b, /\baudit\(\s*'pin_setup'/,
      'api/law-auth.js no longer audits its setup through the local audit() '
      + 'wrapper. If this was a conversion to auditPinSetup(), IT IS A DATA '
      + 'MIGRATION AND NOT A REFACTOR: sairnlaw_audit_log is the only one of '
      + 'the seventeen target tables that exists AND permits pin_setup today, '
      + 'so it is the only one holding real rows in the old shape.');
    assert.match(b, /detail:\s*\{\s*by:\s*caller\.employee_id\s*\}/,
      'api/law-auth.js\'s nested `detail: { by }` is gone. Michael decided on '
      + '2026-10-13 to LEAVE this divergent. Normalising it rewrites the shape '
      + 'of rows already in a live legal-sector audit table.');
  });

  test('NEGATIVE CONTROL: the two shapes are genuinely DIFFERENT, so the arms '
    + 'above are not both satisfied by one pattern. Without this, a single '
    + 'shape could pass as both', () => {
    const fam = setupBranch(code(fs.readFileSync(path.join(API, 'sd-auth.js'), 'utf8')));
    const law = setupBranch(code(fs.readFileSync(path.join(API, 'law-auth.js'), 'utf8')));
    assert.doesNotMatch(fam, /detail:\s*\{\s*by:/,
      'a family member writes SAIRNlaw\'s `detail: { by }`');
    assert.doesNotMatch(law, /detail:\s*\{\s*target:/,
      'SAIRNlaw writes the family\'s `detail: { target, ... }`');
  });

  test('the DIVERGENCE IS EXACTLY ONE FILE WIDE -- no third shape, and no '
    + 'second file quietly adopting SAIRNlaw\'s', () => {
    const nested = [];
    files.forEach((f) => {
      const b = setupBranch(code(fs.readFileSync(path.join(API, f), 'utf8')));
      if (!b) return;
      if (/detail:\s*\{[^}]*\bby\b/.test(b) && f !== 'law-auth.js') nested.push(f);
    });
    assert.deepStrictEqual(nested, [],
      'these files have adopted SAIRNlaw\'s nested shape: ' + nested.join(', ')
      + '. One documented exception is a decision; two is a second convention '
      + 'nobody decided on, and a cross-app query over the audit logs then has '
      + 'to know which files are in which camp.');
  });

  test('the COST of the decision is recorded in the code, not only in a commit '
    + 'message -- api/_lib/audit.js names law-auth.js and says why', () => {
    const src = fs.readFileSync(path.join(API, '_lib', 'audit.js'), 'utf8');
    assert.match(src, /law-auth\.js/,
      'api/_lib/audit.js no longer mentions api/law-auth.js. The reason the '
      + 'divergence exists has to live beside the helper somebody would use to '
      + '"fix" it, or the next refactor has no way to find it.');
    assert.match(src, /legal-sector|already in|live/i,
      'the note beside the helper no longer says WHY law-auth.js is exempt. '
      + '"Left alone" with no reason is indistinguishable from forgotten.');
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  console.log('\nWHAT A GREEN RUN DOES NOT SAY: that the two shapes can be '
    + 'queried together. They\nCANNOT, and that is the accepted cost. It also '
    + 'says nothing about whether a row\nlands -- 16 of the 17 target tables '
    + 'either do not exist or reject pin_setup in\ntheir CHECK constraint. '
    + 'tools/audit_event_type_check.py owns that question.');
  if (failed) process.exit(1);
}

main();
