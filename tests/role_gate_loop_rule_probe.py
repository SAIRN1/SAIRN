#!/usr/bin/env python3
"""tests/role_gate_loop_rule_probe.py -- lock the LOOP-FORM crediting rule in
tools/role_gate_negative_coverage.py against synthetic fixtures, in BOTH
directions, before it is ever believed about the real repo.

Run:  python tests/role_gate_loop_rule_probe.py

── WHY THIS PROBE EXISTS BEFORE THE RULE DID ────────────────────────────────
The rule being locked here is the FOURTH attempt at the same job, and the first
three were all wrong (tools/role_gate_negative_coverage.py:driven() records them):

  ORIGINAL, too strict  -- `role: 'x'` only, so a loop over a declared list of
                           roles was invisible and real passing arms read as
                           driven-as=owner.
  ATTEMPT 1, too loose  -- a bare role literal anywhere in a file that asserts a
                           refusal anywhere. Moved uncovered 12 -> 7 and TWO of
                           the five it newly credited were still SILENT under
                           ablation (sd_customers, alf_mar). It would have
                           ABSOLVED TWO REAL GAPS.
  ATTEMPT 2, too strict -- role and resource in the same test arm. NOT DRIVEN
                           jumped 15 -> 29; it stopped seeing the drives at all.

Attempt 1 is the one that matters here. It failed because it attributed roles
FILE-WIDE: a suite can name `caregiver` and assert a 403 about two unrelated
resources. So the new rule is BODY-SCOPED -- roles from a loop credit only the
resources named inside that loop's own braces, found by BRACE MATCHING rather
than a character count. Fixture N2 below is that exact failure, encoded so it
cannot come back, and fixtures N4/N5 are the boundary itself.

CREDITING IS THE DANGEROUS DIRECTION. An over-report asks for an arm that may
already exist; an over-credit marks a real gap as covered and retires the only
thing asking for the arm. So every ambiguity in the boundary scanner resolves to
NO CREDIT, and N6 asserts that rather than leaving it to be inferred.

── CROSS-DOMAIN DISCIPLINE 1 ───────────────────────────────────────────────
docs/2026-09-13-cross-domain-disciplines.md: lock a check's criteria against
synthetic fixtures before running it on real data. Every fixture below is
synthetic. The probe deliberately imports the rule and never touches
api/sd-data.js or any real suite -- a probe that reads real data cannot
distinguish "the rule is right" from "the repo happens to suit it".
"""
import io
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))

import role_gate_negative_coverage as rg  # noqa: E402

# The universe of role names the fixtures draw from. In production this comes
# from api/sd-data.js's own roleSet() declarations; here it is fixed so a fixture
# result can never move because the real file moved.
ROLES = {'owner', 'billing', 'admin', 'nursing', 'med_aide', 'caregiver',
         'activities', 'office'}

FAILURES = []
CHECKS = [0]


def expect(name, got, want):
    CHECKS[0] += 1
    if got != want:
        FAILURES.append('%s\n     wanted: %s\n     got:    %s'
                        % (name, _fmt(want), _fmt(got)))
        print('  FAIL %s' % name)
    else:
        print('  ok   %s' % name)


def _fmt(d):
    return '{' + ', '.join('%s: %s' % (k, sorted(v)) for k, v in sorted(d.items())) + '}'


def run(src):
    return rg.file_driven(src, ROLES)


# ── POSITIVE: the shapes that MUST be credited ──────────────────────────────

P1 = """
  const ALF_NON_MGMT = ['nursing', 'med_aide', 'caregiver', 'activities'];
  for (const role of ALF_NON_MGMT) {
    await test('alf_facility ' + role + ' cannot write', async () => {
      const { res } = await call(HASH_A, 'emp-1', role,
        { action: 'write', resource: 'alf_facility', payload: { id: 'F-A' } }, []);
      assert.strictEqual(res.statusCode, 403, role + ' got in');
      assert.strictEqual(res.body.error.code, 'FORBIDDEN', 'wrong reason');
    });
  }
"""

P2 = """
  for (const role of ['nursing', 'caregiver']) {
    await test('inline list', async () => {
      const { res } = await call(H, 'e', role, { resource: 'alf_mar' }, []);
      assert.strictEqual(res.statusCode, 403, 'nope');
    });
  }
"""

P3 = """
  const EXCLUDED = ['nursing', 'caregiver'];
  EXCLUDED.forEach((role) => {
    test('forEach form', async () => {
      const { res } = await call(H, 'e', role, { resource: 'sen_clients' }, []);
      assert.strictEqual(res.body.error.code, 'FORBIDDEN', 'nope');
    });
  });
"""

# THE BUG THE FIRST CUT OF THIS RULE SHIPPED WITH. `_role_list` required EVERY
# member to be a declared role, so one unrecognised member rejected the whole
# list -- and on the real arm this rule was written for, the member
# `caregiver` is offered in both of sairncare.html's role dropdowns and appears in
# no roleSet in api/sd-data.js. Three real roles went uncredited and the rule
# reported exactly what it had before. The intersection is the right rule; the
# unrecognised member is reported separately rather than swallowed.
P4 = """
  const MIXED = ['nursing', 'activities', 'not_a_declared_role'];
  for (const role of MIXED) {
    await test('mixed list', async () => {
      const { res } = await call(H, 'e', role, { resource: 'alf_staff' }, []);
      assert.strictEqual(res.statusCode, 403, 'nope');
    });
  }
"""


# ── NEGATIVE: the shapes that MUST NOT be credited ──────────────────────────

# The family-contacts shape: the roles are driven, nothing asserts a refusal.
# 18 green arms over a resource with no gate at all is what this must keep
# reporting as uncovered.
N1 = """
  const EVERY_ROLE = ['nursing', 'caregiver'];
  for (const role of EVERY_ROLE) {
    await test('lists contacts', async () => {
      const { res } = await call(H, 'e', role, { resource: 'alf_family_contacts' }, []);
      assert.strictEqual(res.statusCode, 200, 'should read');
    });
  }
"""

# ATTEMPT 1'S EXACT FAILURE. A refusal IS asserted, about alf_clients, inside the
# loop -- and sd_customers is named elsewhere in the same file. File-wide
# attribution credited sd_customers and absolved a gap that ablation proved
# SILENT. Only alf_clients may be credited.
N2 = """
  const NON_MGMT = ['nursing', 'caregiver'];
  for (const role of NON_MGMT) {
    await test('clients refused', async () => {
      const { res } = await call(H, 'e', role, { resource: 'alf_clients' }, []);
      assert.strictEqual(res.statusCode, 403, 'nope');
    });
  }
  await test('customers read as owner', async () => {
    const { res } = await call(H, 'e', 'owner', { resource: 'sd_customers' }, []);
    assert.strictEqual(res.statusCode, 200, 'owner should read');
  });
"""

# Roles named only in prose. Crediting a comment turns a real gap into a pass --
# the same over-crediting that once reported 16 gates for 11.
N3 = """
  // A caregiver or a nursing role must never reach this, and a 403 with
  // FORBIDDEN is what they should get. Not tested yet.
  await test('owner writes', async () => {
    const { res } = await call(H, 'e', 'owner', { resource: 'bld_draws' }, []);
    assert.strictEqual(res.statusCode, 200, 'ok');
  });
"""

# THE BOUNDARY, with nested braces. sen_claims is named AFTER the loop closes and
# must not be swallowed. This is the magic-window defect in the crediting half:
# a fixed-size window from the `for` would reach past the closing brace.
N4 = """
  const NON_MGMT = ['nursing', 'caregiver'];
  for (const role of NON_MGMT) {
    await test('sdn refused', async () => {
      if (role === 'nursing') { const x = { a: 1 }; assert.ok(x); }
      const { res } = await call(H, 'e', role, { resource: 'sdn_clients' }, []);
      assert.strictEqual(res.statusCode, 403, 'nope');
    });
  }
  await test('claims as owner', async () => {
    const { res } = await call(H, 'e', 'owner', { resource: 'sen_claims' }, []);
    assert.strictEqual(res.statusCode, 200, 'ok');
  });
"""

# A brace inside a STRING must not move the boundary. A naive depth counter reads
# the '{' in the message below as a nesting level and then closes the body one
# brace early -- which silently under-credits here, and in the mirror case
# (an unmatched '}' in a string) over-credits, which is the unsafe direction.
N5 = """
  const NON_MGMT = ['nursing'];
  for (const role of NON_MGMT) {
    await test('braces in strings', async () => {
      const { res } = await call(H, 'e', role, { resource: 'bld_tna' }, []);
      assert.strictEqual(res.statusCode, 403, 'expected {"code":"FORBIDDEN"} but got ' + role);
    });
  }
  await test('quote_requests as admin', async () => {
    const { res } = await call(H, 'e', 'admin', { resource: 'sd_quote_requests' }, []);
    assert.strictEqual(res.statusCode, 200, 'ok');
  });
"""

# AMBIGUITY RESOLVES TO NO CREDIT. The body never closes -- a truncated read, a
# broken edit, a conflict-marker casualty. The honest answer is that the boundary
# could not be found, and the honest consequence is no credit, NOT a body that
# runs to end-of-file and credits everything after it.
N6 = """
  const NON_MGMT = ['nursing', 'caregiver'];
  for (const role of NON_MGMT) {
    await test('unterminated', async () => {
      const { res } = await call(H, 'e', role, { resource: 'alf_staff_credentials' }, []);
      assert.strictEqual(res.statusCode, 403, 'nope');
"""

# A list that is NOT roles must not smuggle its resource in. `of` over a table of
# resources is a real shape in these suites; nothing in it names a role, so the
# loop contributes nothing.
N7 = """
  const RESOURCES = ['alf_clients', 'alf_mar'];
  for (const resource of RESOURCES) {
    await test('each resource', async () => {
      const { res } = await call(H, 'e', 'owner', { resource: resource }, []);
      assert.strictEqual(res.statusCode, 403, 'nope');
    });
  }
"""


def main():
    print('ROLE-GATE LOOP-RULE PROBE -- synthetic fixtures, both directions')
    print('')
    print('POSITIVE -- a real loop-form arm must be credited:')
    expect('P1 declared list, for-of, 403 + FORBIDDEN inside the body',
           run(P1), {'alf_facility': {'nursing', 'med_aide', 'caregiver', 'activities'}})
    expect('P2 inline array literal in the for-of',
           run(P2), {'alf_mar': {'nursing', 'caregiver'}})
    expect('P3 .forEach((role) => ...) over a declared list',
           run(P3), {'sen_clients': {'nursing', 'caregiver'}})
    expect('P4 a MIXED list credits its declared members and drops the rest '
           '(a subset test credited NOTHING here)',
           run(P4), {'alf_staff': {'nursing', 'activities'}})
    print('')
    print('NEGATIVE -- the over-crediting that would absolve a real gap:')
    expect('N1 roles driven but NO refusal asserted (the family-contacts shape)',
           run(N1), {})
    expect('N2 a refusal about alf_clients does NOT credit sd_customers '
           '(attempt 1\'s exact failure)',
           run(N2), {'alf_clients': {'nursing', 'caregiver'}})
    expect('N3 roles named only in a comment',
           run(N3), {})
    expect('N4 a resource AFTER the loop closes is not swallowed (nested braces)',
           run(N4), {'sdn_clients': {'nursing', 'caregiver'}})
    expect('N5 a { inside a string does not move the boundary',
           run(N5), {'bld_tna': {'nursing'}})
    expect('N6 an unterminated body credits NOTHING rather than running to EOF',
           run(N6), {})
    expect('N7 a for-of over RESOURCES names no role and credits nothing',
           run(N7), {})
    print('')

    if FAILURES:
        print('%d of %d FAILED:' % (len(FAILURES), CHECKS[0]))
        for f in FAILURES:
            print('  - %s' % f)
        print('')
        print('THE RULE IS NOT LOCKED. Do not run it against the real repo and do')
        print('not re-pin the ratchet on its output.')
        return 1
    print('%d/%d passed -- the loop rule is locked in both directions.' % (CHECKS[0], CHECKS[0]))
    print('')
    print('STILL NOT A VERDICT. This proves the RULE does what it says on shapes')
    print('whose right answer is known. It does not prove any real gate is tested --')
    print('only --ablate does that. Never lower the pin on this probe alone.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
