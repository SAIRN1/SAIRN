// api/sd-data-sf-role-matrix.test.js
//
// REQUIREMENT: every one of SAIRNfreedom's 36 resources has a rule for every
//   one of the roles in ROLES_BY_APP.sairnfreedom (ten until 2026-10-13, ELEVEN
//   since a trustee was given a login); the two locks cannot be opened by anything; the
//   capability facts mirrored into api/sd-data.js match the page they were
//   copied from; and the table is actually WIRED into the gate.
//
// Run:  node api/sd-data-sf-role-matrix.test.js
//
// ── THE DEFECT THIS HOLDS ─────────────────────────────────────────────────
// SAIRNfreedom had NO role distinction of any kind until 2026-10-13. Every
// resource was authorised by the licence key alone until the gate waves of
// 2026-09-21 onward, and after those waves by A SESSION OF ANY ROLE -- so a
// chaplain's sign-in could rewrite the general ledger and a service officer
// could edit the officer roster. Ten distinct capability roles, treated as one;
// eleven since 2026-10-13, when Michael gave a post trustee a view-only login.
//
// ── WHY THIS FILE IS FIVE DIFFERENT KINDS OF CHECK AND NOT ONE ────────────
// Modelled on api/sd-data-law-role-matrix.test.js, which exists because a table
// like this has several independent ways to be wrong and only one of them is
// "a rule is missing":
//
//   COMPLETENESS  a resource or a role with no rule -- the state the whole
//                 file exists to end, and the one a human reading the table
//                 will not notice because an absence looks like nothing.
//   THE LOCKS     a default is a policy an override can erase. Both locks are
//                 asserted against `decide()` and not against the table, so
//                 editing the table cannot open them.
//   THE MIRROR    api/sd-data.js copies two facts out of sairnfreedom.html --
//                 which capabilities provision, and which is sole-holder.
//                 A mirrored constant with no check is a constant that drifts.
//   WIRING        a table nothing reads is a document. One arm proves the gate
//                 calls it.
//   VACUITY       every arm above can pass over an empty set. Each one asserts
//                 its own population first.
//
// ── WHAT THIS DOES NOT DO ─────────────────────────────────────────────────
// It does not drive a session per role against the live handler. That is the
// half routed to cody in docs/2026-10-13-hank-b6-routing.md: every role in
// ROLES_BY_APP x 36 resources x 2 verbs is a driven-arm job, and this file is
// the policy's own
// shape rather than its behaviour. A green run here means the POLICY is
// complete, locked, mirrored and wired. It does not mean a signed-in chaplain
// was observed being refused.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { ROLES_BY_APP } = require('./_lib/auth');
const sfRoles = require('./_lib/sf-roles');

const REPO = path.join(__dirname, '..');
const ROLES = ROLES_BY_APP.sairnfreedom;
const REGISTRY = require('./_resources/sairnfreedom.js').resources;
const SRC = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
const PAGE = fs.readFileSync(path.join(REPO, 'sairnfreedom.html'), 'utf8');

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log('  PASS  ' + name); passed++; }
  catch (e) { console.log('  FAIL  ' + name + '\n        ' + e.message); failed++; }
}

function main() {
  console.log('SAIRNfreedom role matrix -- 36 resources x every role in ROLES_BY_APP\n');

  // ── VACUITY FIRST. Every arm below iterates one of these. ───────────────
  test('the three populations are real, and the two that have independent '
    + 'sources are EQUAL. A short list here would make every arm below pass '
    + 'over almost no data', () => {
    // ── THE ROLE COUNT WAS HARDCODED AT 10 AND WENT STALE THE DAY A ROLE WAS
    // ── ADDED (2026-10-13).  Michael decided a trustee gets a login,
    // ROLES_BY_APP.sairnfreedom became eleven, and this arm failed for a reason
    // that had nothing to do with what it exists to catch.  Writing 11 here
    // just moves the expiry date.
    //
    // WHAT THIS ARM IS ACTUALLY FOR is non-vacuity: if REGISTRY, ROLES or the
    // row list came back short or empty, every arm below would iterate almost
    // nothing and pass.  So:
    //   * the two populations WITH INDEPENDENT SOURCES are asserted EQUAL --
    //     the registry comes from api/_resources/sairnfreedom.js and the rows
    //     from api/_lib/sf-roles.js, so this is two sources agreeing rather
    //     than one source agreeing with itself;
    //   * the role count, which has only ONE source, gets a FLOOR and a NAMED
    //     ANCHOR instead of an exact figure.
    assert.strictEqual(sfRoles.resources().length, REGISTRY.length,
      'the registry has ' + REGISTRY.length + ' resources and the matrix has '
      + sfRoles.resources().length + ' rows');
    assert.ok(REGISTRY.length >= 36,
      'the registry yielded only ' + REGISTRY.length + ' resources, so the arms '
      + 'below compared almost nothing -- the extraction broke');
    assert.ok(ROLES.length >= 11,
      'ROLES_BY_APP.sairnfreedom yielded only ' + ROLES.length + ' roles');
    for (const anchor of ['post.govern', 'finance.write', 'trustee.audit']) {
      assert.ok(ROLES.indexOf(anchor) !== -1,
        'ROLES_BY_APP.sairnfreedom is missing ' + anchor + ', so either the '
        + 'extraction broke or a capability was dropped');
    }
  });

  // ── THE DERIVED COLUMN, RE-DERIVED INDEPENDENTLY (2026-10-13) ───────────
  // api/_lib/sf-roles.js COMPUTES the trustee.audit column from the
  // finance.write column rather than transcribing 36 cells.  That removes 36
  // chances to disagree with Michael's one-sentence decision -- and it means
  // the table can no longer be asserted against itself, because the rule and
  // the table are the same artefact.
  //
  // SO THIS ARM RE-STATES THE RULE FROM THE DECISION, not from the code, and
  // compares.  A hand-edit to any trustee cell fails here; so does a change to
  // the derivation that nobody decided.
  test('TRUSTEE: view-only on financial records -- every cell re-derived from '
    + 'Michael\'s decision, not read back from the table', () => {
    const wrong = [];
    sfRoles.resources().forEach((r) => {
      const row = sfRoles.SF_ROLE_MATRIX[r];
      // THE DECISION, restated: read what the bonded finance office may write;
      // rw on the trustee's own audit record; nothing else.
      const expected = (r === 'sf_trustee_audits')
        ? 'rw'
        : (row['finance.write'] === 'rw' ? 'r' : '');
      const got = String(row['trustee.audit'] === undefined ? 'MISSING' : row['trustee.audit']);
      if (got !== expected) wrong.push(r + ': expected ' + JSON.stringify(expected) + ', got ' + JSON.stringify(got));
    });
    assert.deepStrictEqual(wrong, [],
      wrong.length + ' trustee cell(s) disagree with the decision: ' + wrong.slice(0, 8).join('; '));
  });

  test('...and that policy is not vacuous in EITHER direction -- a trustee can '
    + 'read the money and cannot read the people', () => {
    // Without this, the arm above is satisfied by a column that is '' every
    // cell (a login that can see nothing) or 'r' every cell (a login that can
    // see the felony flags), because in both cases it would agree with a
    // derivation that produced the same thing.
    const canRead = sfRoles.resources()
      .filter((r) => sfRoles.decide(r, 'trustee.audit', 'read') === sfRoles.ALLOW);
    const canWrite = sfRoles.resources()
      .filter((r) => sfRoles.decide(r, 'trustee.audit', 'write') === sfRoles.ALLOW);
    assert.ok(canRead.length >= 10,
      'a trustee can read only ' + canRead.length + ' records, which is not a '
      + 'financial audit surface');
    assert.ok(canRead.indexOf('sf_ledger') !== -1 && canRead.indexOf('sf_disbursements') !== -1,
      'a trustee cannot read the general ledger or the disbursements, which is '
      + 'the whole of what was decided');
    // AND THE REFUSALS. These are the rows Michael's decision did NOT cover,
    // and they carry the sharpest material in the app: the felony and gambling
    // disqualification flags, minors, health and military status, and the
    // VA-adjacent referrals.
    for (const shut of ['sf_operators', 'sf_youth_participants', 'sf_waivers',
                        'sf_members', 'sf_service_appointments']) {
      assert.strictEqual(sfRoles.decide(shut, 'trustee.audit', 'read'), sfRoles.DENY,
        'a trustee can read ' + shut + ', which the decision did not grant');
    }
    assert.deepStrictEqual(canWrite, ['sf_trustee_audits'],
      'a trustee can write ' + JSON.stringify(canWrite) + ' -- the decision was '
      + 'VIEW-ONLY on financial records, with the quarterly audit itself the '
      + 'one exception');
  });

  // ── COMPLETENESS ────────────────────────────────────────────────────────
  test('THE LOAD-BEARING ONE: every registry resource has a row, and every row '
    + 'is a registry resource', () => {
    const rows = sfRoles.resources();
    const noRow = REGISTRY.filter((r) => rows.indexOf(r) === -1);
    const noResource = rows.filter((r) => REGISTRY.indexOf(r) === -1);
    assert.deepStrictEqual({ noRow: noRow, noResource: noResource },
      { noRow: [], noResource: [] },
      'the table and the registry disagree. A resource with no row is DENIED '
      + 'by decide() -- which is the safe direction and still a bug, because '
      + 'nobody decided it. A row with no resource is a policy for something '
      + 'that does not exist.');
  });

  test('...and every row has a cell for every one of the 10 roles. An absent '
    + 'cell is DENY, which is safe and is still nobody\'s decision', () => {
    const gaps = [];
    sfRoles.resources().forEach((r) => {
      const row = sfRoles.SF_ROLE_MATRIX[r];
      ROLES.forEach((role) => {
        if (!Object.prototype.hasOwnProperty.call(row, role)) gaps.push(r + '/' + role);
      });
    });
    assert.deepStrictEqual(gaps, [],
      gaps.length + ' cell(s) missing: ' + gaps.slice(0, 12).join(', '));
  });

  test('...and every cell is one of the three legal values, so a typo cannot '
    + 'read as a grant', () => {
    const bad = [];
    sfRoles.resources().forEach((r) => {
      const row = sfRoles.SF_ROLE_MATRIX[r];
      ROLES.forEach((role) => {
        const v = row[role];
        if (v !== 'rw' && v !== 'r' && v !== '') bad.push(r + '/' + role + '=' + JSON.stringify(v));
      });
    });
    assert.deepStrictEqual(bad, [],
      'illegal cell value(s): ' + bad.join(', ') + '. decide() treats anything '
      + 'that is not exactly rw or r as no access, so a typo fails closed -- '
      + 'but it fails closed SILENTLY, which is what this arm catches.');
  });

  test('every row carries a `why` naming the capability the grant comes from. '
    + 'A grant with no stated basis is one nobody can review', () => {
    const silent = sfRoles.resources().filter((r) => {
      const w = sfRoles.SF_ROLE_MATRIX[r].why;
      return !w || String(w).length < 20;
    });
    assert.deepStrictEqual(silent, [],
      'row(s) with no usable `why`: ' + silent.join(', '));
  });

  // ── THE TWO GOVERNING ROLES ─────────────────────────────────────────────
  test('both provisioning capabilities are rw on every resource -- a commander '
    + 'who cannot correct a record is a support ticket, not a safety property', () => {
    const gaps = [];
    sfRoles.resources().forEach((r) => {
      sfRoles.PROVISIONING.forEach((role) => {
        if (sfRoles.SF_ROLE_MATRIX[r][role] !== 'rw') gaps.push(r + '/' + role);
      });
    });
    assert.deepStrictEqual(gaps, [], 'not rw: ' + gaps.join(', '));
  });

  // ── THE LOCKS, ASSERTED THROUGH decide() ────────────────────────────────
  test('THE GOVERNANCE LOCK: no role outside the two provisioning capabilities '
    + 'can WRITE sf_officers, whatever the table says', () => {
    assert.ok(Object.keys(sfRoles.SF_GOVERNANCE_LOCKED).length > 0,
      'the governance lock is empty, so this arm checked nothing');
    ROLES.forEach((role) => {
      const v = sfRoles.decide('sf_officers', role, 'write');
      if (sfRoles.PROVISIONING.indexOf(role) !== -1) {
        assert.strictEqual(v, sfRoles.ALLOW, role + ' cannot write the roster');
      } else {
        assert.strictEqual(v, sfRoles.DENY,
          role + ' CAN write the officer roster. That roster is the post\'s '
          + 'governance record and three client-side guards run off it; a write '
          + 'past them can leave the post at zero active provisioners, which is '
          + 'unrecoverable through the API.');
      }
    });
  });

  test('THE MONEY LOCK: only governance and the bonded finance office can WRITE '
    + 'the ledger, the chart of accounts and the two ORC 2915 payee records', () => {
    const locked = Object.keys(sfRoles.SF_MONEY_LOCKED);
    assert.ok(locked.length >= 4, 'the money lock covers only ' + locked.length);
    locked.forEach((res) => {
      ROLES.forEach((role) => {
        const v = sfRoles.decide(res, role, 'write');
        if (sfRoles.FINANCE.indexOf(role) !== -1) {
          assert.strictEqual(v, sfRoles.ALLOW, role + ' cannot write ' + res);
        } else {
          assert.strictEqual(v, sfRoles.DENY, role + ' CAN write ' + res);
        }
      });
    });
  });

  test('NEGATIVE CONTROL on both locks: a resource that is NOT locked is '
    + 'writable by a role outside both lock sets. Without this the two arms '
    + 'above would pass on a decide() that denied every write', () => {
    assert.strictEqual(sfRoles.decide('sf_documents', 'records.write', 'write'),
      sfRoles.ALLOW,
      'records.write cannot write sf_documents, so decide() may be refusing '
      + 'every write and the lock arms prove nothing');
    assert.strictEqual(sfRoles.decide('sf_events', 'ceremonial.manage', 'write'),
      sfRoles.ALLOW, 'ceremonial.manage cannot write sf_events');
  });

  // ── FAIL-CLOSED DIRECTIONS ──────────────────────────────────────────────
  test('decide() fails closed on an unknown sf_ resource, an unknown role, an '
    + 'empty role and an unknown verb -- and answers NOT_SF for another app', () => {
    assert.strictEqual(sfRoles.decide('sf_brand_new', 'post.govern', 'read'),
      sfRoles.DENY, 'a 37th sf_ resource with no row was not denied');
    assert.strictEqual(sfRoles.decide('sf_ledger', 'quartermaster', 'read'),
      sfRoles.DENY, 'an unknown role was not denied');
    assert.strictEqual(sfRoles.decide('sf_ledger', '', 'read'),
      sfRoles.DENY, 'an empty role was not denied');
    assert.strictEqual(sfRoles.decide('sf_documents', 'chaplain.pastoral', 'soft_delete'),
      sfRoles.DENY,
      'an unknown VERB was treated as a read. A future verb must be '
      + 'write-class, or it arrives on a read grant.');
    assert.strictEqual(sfRoles.decide('law_matters', 'post.govern', 'read'),
      sfRoles.NOT_SF,
      'a SAIRNlaw resource got a verdict from the SAIRNfreedom table. This '
      + 'function is called from a gate every app passes through, so folding '
      + 'NOT_SF into ALLOW would make every other app read as approved by this '
      + 'policy.');
  });

  // ── THE MIRROR ──────────────────────────────────────────────────────────
  test('THE MIRROR: the capability facts api/sd-data.js copies from '
    + 'sairnfreedom.html still match the page', () => {
    const provPage = PAGE.match(/var PROVISIONING_CAPS\s*=\s*\[([^\]]*)\]/);
    assert.ok(provPage, 'PROVISIONING_CAPS could not be read out of '
      + 'sairnfreedom.html, so this arm compared NOTHING -- a third state');
    const pageProv = (provPage[1].match(/'([a-z.]+)'/g) || [])
      .map((s) => s.slice(1, -1)).sort();
    const srvProv = (SRC.match(/const SF_PROVISIONING_CAPS = \[([^\]]*)\]/) || [, ''])[1];
    const serverProv = (srvProv.match(/'([a-z.]+)'/g) || [])
      .map((s) => s.slice(1, -1)).sort();
    assert.deepStrictEqual(serverProv, pageProv,
      'SF_PROVISIONING_CAPS in api/sd-data.js has drifted from '
      + 'PROVISIONING_CAPS in sairnfreedom.html. The server guards refuse on '
      + 'the server list; the page hides controls on its own. A drift means the '
      + 'two disagree about who governs the post.');
    assert.deepStrictEqual(serverProv, sfRoles.PROVISIONING.slice().sort(),
      'api/_lib/sf-roles.js PROVISIONING has drifted from the mirrored list in '
      + 'api/sd-data.js, so the role table and the officer guards disagree');
  });

  test('...and the sole-holder capability mirrored into api/sd-data.js is '
    + 'exactly the set the page marks `sole:true`', () => {
    // CAPABILITIES entries are one per line: { id:'x', ..., sole:true, ... }
    const pageSole = [];
    const re = /\{\s*id:\s*'([a-z.]+)'[^}]*\bsole:\s*(true|false)/g;
    let m, seen = 0;
    while ((m = re.exec(PAGE)) !== null) {
      seen++;
      if (m[2] === 'true') pageSole.push(m[1]);
    }
    assert.ok(seen >= 10,
      'only ' + seen + ' CAPABILITIES entries parsed out of sairnfreedom.html; '
      + 'the page declares at least ten, so the regex has drifted and this arm '
      + 'would pass over almost nothing');
    const srvSole = (SRC.match(/const SF_SOLE_CAPS = \[([^\]]*)\]/) || [, ''])[1];
    const serverSole = (srvSole.match(/'([a-z.]+)'/g) || [])
      .map((s) => s.slice(1, -1)).sort();
    assert.deepStrictEqual(serverSole, pageSole.sort(),
      'SF_SOLE_CAPS has drifted from the page. The server refuses a second '
      + 'active holder on its own list, so a capability the page marks sole and '
      + 'the server does not is a rule enforced only in the browser -- which is '
      + 'exactly the state this batch set out to end.');
  });

  // ── WIRING ──────────────────────────────────────────────────────────────
  test('the table is actually WIRED: api/sd-data.js requires sf-roles and calls '
    + 'decide() in the session gate. A table nothing reads is a document', () => {
    assert.match(SRC, /require\('\.\/_lib\/sf-roles'\)/,
      'api/sd-data.js does not require api/_lib/sf-roles.js at all');
    const calls = (SRC.match(/sfRoles\.decide\(/g) || []).length;
    assert.ok(calls >= 1,
      'sfRoles.decide() is never called, so the whole policy is inert');
    assert.match(SRC, /sfRoles\.denyMessage\(/,
      'the refusal does not use denyMessage(), so a denied officer gets a '
      + 'generic message instead of one naming the office that is required');
  });

  test('the three sf_officers guards are enforced SERVER-SIDE, which is the '
    + 'half that was only ever in the browser', () => {
    assert.match(SRC, /LAST_PROVISIONER/,
      'the SPEC 1c last-provisioner refusal is not in api/sd-data.js. It ran '
      + 'only in sairnfreedom.html until 2026-10-13, and a write that does not '
      + 'come from that page went past it.');
    assert.match(SRC, /SOLE_HOLDER/,
      'the sole-holder refusal is not enforced server-side');
    assert.match(SRC, /ROSTER_UNREADABLE/,
      'the roster pre-read does not fail closed. An unreadable roster must '
      + 'refuse the write, not let it through unchecked (PR 1.11).');
  });

  console.log('\n' + passed + ' passed, ' + failed + ' failed');
  console.log('\nWHAT A GREEN RUN DOES NOT SAY: that a signed-in chaplain was '
    + 'observed being\nrefused. No session is driven here. The driven matrix -- '
    + 'EVERY role in\nROLES_BY_APP x 36 resources x 2 verbs, so it grows with '
    + 'the vocabulary rather\nthan with a number written here -- is routed to '
    + 'cody in '
    + 'docs/2026-10-13-hank-b6-routing.md.');
  if (failed) process.exit(1);
}

main();
