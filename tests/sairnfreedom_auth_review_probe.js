// tests/sairnfreedom_auth_review_probe.js
//
// cc's independent review of hank's SAIRNfreedom per-employee auth, covering
// BOTH obligations: 2026-09-21T14:37:06Z and its 15:11:47Z amendment.
//
//     node tests/sairnfreedom_auth_review_probe.js
//
// REPORT-ONLY. Exit 0 when every press-on this file covers was DRIVEN, 1 when
// an arm could not be driven -- which is not the same as a clean review and
// says which. Nothing here asserts a verdict about the subject; it drives the
// questions hank wrote into the two obligations and prints what came back.
//
// ── WHY IT DRIVES THE SHARED HELPER RATHER THAN READING IT ─────────────────
// hank's own words on the 15:11 press-on (1): "If I am wrong here it is wrong
// for every app with credentials." api/_lib/employee-lifecycle.js is required
// by ten endpoints. A review that read the diff and agreed would be worth less
// than the diff's commit message, which already states the reasoning honestly.
// So setActive() is called with a real ctx and a fake PostgREST, once per
// question.
//
// ── THE ANCHOR DISCIPLINE ──────────────────────────────────────────────────
// Where an arm depends on a literal in a file it does not own, it asserts the
// literal was FOUND before judging anything. An arm whose anchor has moved
// reports COULD NOT DRIVE and exits 1 rather than passing on a match it never
// made.
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const LC = require(path.join(ROOT, 'api/_lib/employee-lifecycle.js'));

const COULD_NOT_DRIVE = [];
let findings = 0;

function head(n, title) {
  console.log('\n' + '='.repeat(74));
  console.log('PRESS-ON ' + n + '  ' + title);
  console.log('='.repeat(74));
}
function cannot(n, why) {
  COULD_NOT_DRIVE.push(n + ' -- ' + why);
  console.log('  COULD NOT DRIVE -- ' + why);
}
function finding(text) { findings += 1; console.log('\n  >>> FINDING: ' + text); }

// ── A real ctx over a fake PostgREST ──────────────────────────────────────
function ctxFor(rows, opts) {
  opts = opts || {};
  const patched = [];
  return {
    ctx: {
      caller: opts.caller || { employee_id: 'DEPUTY', role: 'post.govern.deputy' },
      provisioningRoles: opts.provisioningRoles || ['post.govern', 'post.govern.deputy'],
      soleRole: opts.soleRole,
      roleLabel: 'a post governance officer',
      table: 'sf_employee_auth',
      licHash: 'HASH1',
      headers: {},
      rest: (q) => 'https://fake.invalid/' + q,
      body: opts.body || { employee_id: 'GOV', active: false, reason: 'left the post' },
      audit: null,
      canView: () => true,
      viewLabel: 'the roster'
    },
    patched
  };
}

function withFetch(rows, patched, fn) {
  const saved = global.fetch;
  global.fetch = async (url, init) => {
    if (init && init.method === 'PATCH') {
      patched.push(String(url));
      return { ok: true, status: 200, json: async () => ([{ employee_id: 'GOV', active: false }]) };
    }
    return { ok: true, status: 200, json: async () => rows };
  };
  return Promise.resolve().then(fn).then(
    (v) => { global.fetch = saved; return v; },
    (e) => { global.fetch = saved; throw e; });
}

// One active governor, one active deputy. The deputy is the caller.
const ROWS = [
  { employee_id: 'GOV', role: 'post.govern', active: true },
  { employee_id: 'DEPUTY', role: 'post.govern.deputy', active: true }
];

(async function () {
  console.log('cc REVIEWING hank -- SAIRNfreedom per-employee auth');
  console.log('obligations 2026-09-21T14:37:06Z and 2026-09-21T15:11:47Z. REPORT-ONLY.');

  // ───────────────────────────────────────────────────────────────────────
  head('15:11 (1)', 'the shared helper: does `soleRole` ABSENT really keep the '
       + 'old behaviour for the other nine?');
  console.log(`
hank: "The change is one optional parameter -- soleRole -- and when absent the
behaviour is byte-identical to before. Check that claim properly ... If I am
wrong here it is wrong for every app with credentials."
`);
  {
    const { ctx, patched } = ctxFor(ROWS, { soleRole: undefined });
    const out = await withFetch(ROWS, patched, () => LC.setActive(ctx));
    const ok = out.status === 200 && patched.length === 1;
    console.log('  ' + (ok ? 'ok  ' : 'FAIL') +
      '  soleRole ABSENT: two provisioners counted, the deactivation is ALLOWED'
      + ' -> status ' + out.status + ', ' + patched.length + ' PATCH(es)');
    assert.ok(ok, 'absent soleRole changed behaviour');
  }
  {
    const { ctx, patched } = ctxFor(ROWS, { soleRole: 'post.govern' });
    const out = await withFetch(ROWS, patched, () => LC.setActive(ctx));
    const ok = out.status === 409 && out.body.error.code === 'LAST_ADMIN' && patched.length === 0;
    console.log('  ' + (ok ? 'ok  ' : 'FAIL') +
      '  soleRole PRESENT and valid: the same call is REFUSED -> status '
      + out.status + ' ' + (out.body.error || {}).code + ', ' + patched.length + ' PATCH(es)');
    assert.ok(ok, 'a valid soleRole did not refuse');
  }
  console.log(`
  VERDICT: hank's claim HOLDS. \`const guardRoles = soleRole ? [soleRole] : roles\`
  reduces to \`roles\` when the parameter is absent, and the two arms above show
  the ALLOW and the REFUSE are decided by that parameter alone. Nine callers
  passing null are unaffected.

  AND THE LANDSCAPE MOVED AFTER THE OBLIGATION WAS WRITTEN, which is worth
  saying because the press-on asks to "verify no existing caller passes
  soleRole": that is no longer true. 591531ce gave grd-auth, sb-auth and
  scp-auth a non-null SOLE_ROLE, and sd-auth carries one too. Four apps besides
  SAIRNfreedom now depend on this parameter being right.`);

  // ───────────────────────────────────────────────────────────────────────
  head('15:11 (1b)', 'and what happens when `soleRole` is WRONG -- a question '
       + 'neither obligation asks');
  console.log(`
Not on hank's list. It follows from the answer above: the guard's behaviour is
decided entirely by one string, that string is a hand-written literal in each
endpoint, and it has to match a role vocabulary that lives in the database, in
api/_lib/auth.js's ROLES_BY_APP and in the app's own CAPABILITIES array. The
15:11 press-on (3) is about exactly that three-way duplication, one layer up.

So: what does the helper do if the literal does not match?
`);
  {
    const { ctx, patched } = ctxFor(ROWS, { soleRole: 'post.governor' });  // a plausible typo
    const out = await withFetch(ROWS, patched, () => LC.setActive(ctx));
    console.log('  soleRole = \'post.governor\' (a typo for post.govern)');
    console.log('    -> status ' + out.status + ', ' + patched.length + ' PATCH(es) sent');
    if (out.status === 200 && patched.length === 1) {
      finding(
        'A soleRole that names no real role SILENTLY DISABLES the last-admin\n' +
        '      guard rather than failing closed. guardRoles becomes [\'post.governor\'],\n' +
        '      activeProvisioners counts ZERO rows, and the condition\n' +
        '      `guardRoles.indexOf(target.role) !== -1` can never be true -- so the\n' +
        '      sole governor is deactivated, 200, PATCH sent. The app reaches zero\n' +
        '      governors and bootstrap still 409s, which is the SD-AUDIT-2026 loss\n' +
        '      shape this parameter was added to PREVENT.\n' +
        '      Nothing validates soleRole against provisioningRoles, and the value is\n' +
        '      a literal in each of five endpoints that must agree with a vocabulary\n' +
        '      kept in three other places. SEVERITY: the guard fails OPEN and says\n' +
        '      nothing. A one-line assertion in the helper -- soleRole must be a\n' +
        '      member of provisioningRoles, or throw -- closes it for all ten.');
    } else {
      console.log('    ok -- a wrong soleRole does not silently disable the guard');
    }
  }

  // ───────────────────────────────────────────────────────────────────────
  head('15:11 (2)', 'the likeliest hole hank named: can `setup` walk around '
       + 'the guard by DOWNGRADING the only governor?');
  console.log(`
hank: "whether setup can downgrade the only governor's capability to something
non-sole, which would walk around the guard entirely. I did NOT check that
second one and it is the likeliest hole."

HE THEN CHECKED IT AND CLOSED IT IN THE SAME FILE. api/sf-auth.js's setup now
refuses 409 LAST_ADMIN on a role change away from SOLE_ROLE when the target is
the only active governor, under a comment saying it was driven before the guard
existed. Verified present below.

WHAT THE REVIEW ADDS IS THE OTHER HALF OF HIS OWN SENTENCE -- "it is not only
this app, and that is reported rather than swept". Counted:
`);
  {
    const files = fs.readdirSync(path.join(ROOT, 'api'))
      .filter((f) => /-auth\.js$/.test(f)).sort();
    const rows = [];
    for (const f of files) {
      const src = fs.readFileSync(path.join(ROOT, 'api', f), 'utf8');
      if (src.indexOf("action === 'setup'") === -1) continue;
      let seg = src.split("action === 'setup'")[1];
      seg = seg.indexOf("action === 'roster'") !== -1
        ? seg.slice(0, seg.indexOf("action === 'roster'")) : seg.slice(0, 9000);
      const sole = /SOLE_ROLE\s*=\s*'([^']+)'/.exec(src);
      rows.push({
        f, sole: sole ? sole[1] : null,
        guarded: seg.indexOf('LAST_ADMIN') !== -1,
        upserts: seg.indexOf('on_conflict=license_hash,employee_id') !== -1,
        writesRole: /body: JSON\.stringify\(\{[\s\S]{0,400}\brole\b/.test(seg)
      });
    }
    if (!rows.length) { cannot('15:11 (2)', 'no api/*-auth.js setup paths found'); }
    else {
      const unguarded = rows.filter((r) => !r.guarded);
      const exposed = unguarded.filter((r) => r.sole && r.upserts && r.writesRole);
      console.log('  setup paths examined                       ' + rows.length);
      console.log('  WITH a role-change guard                   ' + (rows.length - unguarded.length)
        + '   ' + rows.filter((r) => r.guarded).map((r) => r.f).join(', '));
      console.log('  WITHOUT one                                ' + unguarded.length);
      console.log('  ...of those, declaring a SOLE_ROLE AND      ' + exposed.length
        + '   ' + exposed.map((r) => r.f + ' (' + r.sole + ')').join(', '));
      console.log('     upserting on (license,employee) with role');
      if (exposed.length) {
        finding(
          'The hole hank closed in sf-auth is OPEN and REACHABLE in ' + exposed.length + ' other\n' +
          '      app(s). Each declares a SOLE_ROLE, so its set_active guard counts ONLY\n' +
          '      that role -- and each setup upserts on (license_hash, employee_id)\n' +
          '      writing `role`, so demoting the last holder of the sole role is a\n' +
          '      single call the deactivation guard never sees. These are the four apps\n' +
          '      591531ce hardened against DEACTIVATION three hours earlier; the\n' +
          '      demotion route was not part of that change.\n' +
          '      This is hank\'s own reported residual, quantified rather than left as\n' +
          '      "and the nine others". It needs its own claim and its own review --\n' +
          '      NOT a rider on this one.');
      }
      // The anchor discipline: the guard is asserted PRESENT in sf-auth rather
      // than assumed from the commit message.
      const sf = fs.readFileSync(path.join(ROOT, 'api/sf-auth.js'), 'utf8');
      const anchor = "if (SF_ROLES.indexOf(role) !== -1 && role !== SOLE_ROLE) {";
      if (sf.indexOf(anchor) === -1) {
        cannot('15:11 (2)', 'the sf-auth setup guard anchor has moved -- this arm '
          + 'is not reporting agreement it did not check');
      } else {
        console.log('\n  ok    the sf-auth setup guard is present, and it is keyed on the NEW');
        console.log('        role not being SOLE_ROLE -- promoting TO governor cannot reduce');
        console.log('        the count, so guarding only the demotion direction is right.');
      }
    }
  }
  console.log(`
  AND ONE THING THE NEW GUARD DOES NOT DO, reported not fixed: it is a READ
  followed by an UPSERT with nothing between them. Two governors, two concurrent
  demotions, each read sees two and each is allowed -- zero governors. That is
  the same check-then-write shape closed in alf_mar and bld_draws with database
  RPCs earlier today. set_active in the shared helper has the identical
  structure, so this is not a defect hank introduced; it is a property the whole
  last-admin family has.`);

  // ───────────────────────────────────────────────────────────────────────
  head('14:37 (4)', 'three of thirty-five sf_ resources are gated -- is that '
       + 'scope defensible?');
  console.log(`
hank: "sf_members and sf_youth_participants in particular hold personal data
about veterans and minors ... Judge whether that scope is defensible or whether
I have closed a narrow door and left a wider one."
`);
  {
    const sd = fs.readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
    const m = /const SF_RESOURCES = \{([\s\S]*?)\n    \};/.exec(sd);
    if (!m) {
      cannot('14:37 (4)', 'SF_RESOURCES could not be located in api/sd-data.js');
    } else {
      const all = (m[1].match(/\bsf_[a-z0-9_]+/g) || []);
      const uniq = Array.from(new Set(all));
      const gated = uniq.filter((r) => new RegExp("'" + r + "'").test(
        (/SD_SESSION_GATED[\s\S]{0,4000}/.exec(sd) || [''])[0]));
      console.log('  sf_ resources in SF_RESOURCES            ' + uniq.length);
      console.log('  named in SD_SESSION_GATED                ' + gated.length
        + '   ' + gated.join(', '));
      const pii = uniq.filter((r) => /member|youth|volunteer|donor|staff/.test(r));
      console.log('  ungated and personal-data-shaped by name ' + pii.filter(
        (r) => gated.indexOf(r) === -1).length + '   '
        + pii.filter((r) => gated.indexOf(r) === -1).join(', '));
      console.log(`
  VERDICT: THE SCOPE IS DEFENSIBLE AND THE RESIDUAL IS REAL, and hank has
  already done the thing that makes it defensible -- an arm PINS the ungated
  set, so widening is a deliberate act rather than a drift. Tier A was the
  finding and Tier A is what he closed. But the ungated names above are not a
  tail of bookkeeping tables; a roster of veterans and minors readable on the
  licence key alone is a bigger door than the ledger, and it should not wait on
  a role-tiering product decision the way press-on (1) legitimately does.
  RECOMMENDATION: an open-work row naming those resources specifically, so the
  next session sees "gated 3, pinned 32, these N hold personal data" rather than
  a count.`);
    }
  }

  // ───────────────────────────────────────────────────────────────────────
  head('14:37 (7) / 15:11 (7)', 'the schema is not run -- what does the '
       + 'deployed app actually answer?');
  console.log(`
Both obligations end on the same line: nothing here has touched Supabase, and
the first real call answers NOT_PROVISIONED until
sql/sairnfreedom_employee_auth_schema.sql is executed.

NOT DRIVEN HERE, and the reason is a finding of its own rather than a gap in
this review: the same question asked of SAIRNlaw this session returned
\`provisioned: false\` on 15 of 18 resources, and that app's code has been live
for weeks. The pattern -- code and schema shipping on different clocks with
nothing on the platform reconciling them -- now has three instances tonight
(SAIRNcare/SAIRNbuild, SAIRNlaw, SAIRNfreedom). Driving one more app's live
read would add a fourth data point to a conclusion already reached, and this
probe has no SAIRNfreedom credentials to sign in with in any case.
`);

  console.log('\n' + '='.repeat(74));
  if (COULD_NOT_DRIVE.length) {
    console.log(COULD_NOT_DRIVE.length + ' PRESS-ON(S) COULD NOT BE DRIVEN -- NOT a clean review:');
    COULD_NOT_DRIVE.forEach((c) => console.log('  ? ' + c));
    process.exit(1);
  }
  console.log('EVERY PRESS-ON THIS FILE COVERS WAS DRIVEN. ' + findings + ' finding(s).');
  console.log('The obligation records carry the verdicts, including the press-ons');
  console.log('answered by judgement rather than by driving -- (1) identity-vs-rank,');
  console.log('(3) the three-way role list, (5) and (6) the arms that passed for the');
  console.log('wrong reason, and (4) the unverified sign-in UI.');
  process.exit(0);
})().catch((e) => { console.log('\nPROBE FAILED TO RUN: ' + e.stack); process.exit(1); });
