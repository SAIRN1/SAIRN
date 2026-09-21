"""Negative control for api/sd-auth-last-admin.test.js.

    python tests/run_sd_auth_last_admin_sabotage_probe.py

Exit 0  every planted defect was REFUSED, and every file touched is
        byte-identical again afterwards
Exit 1  a planted defect SURVIVED, or a file was left modified
Exit 2  COULD NOT RUN -- never folded into either of the other two

── WHY THIS ONE EXISTS SPECIFICALLY ────────────────────────────────────────
The defect this suite covers lived in a Tier A auth path for months behind a
comment asserting it was "unreachable by construction". Nothing was red. The
suite that now covers it is green, and green is a fact about the suite until
something makes it fail on purpose.

── MUTATION 1 IS THE WHOLE POINT ───────────────────────────────────────────
Reverting the guard to count PROVISIONING_ROLES re-creates the original defect
exactly. If the suite passes that, it is testing nothing that matters, and
every other arm is decoration.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITE = os.path.join('api', 'sd-auth-last-admin.test.js')
ENDPOINT = os.path.join('api', 'sd-auth.js')
NODE = 'node'


def die(msg):
    print('\nCOULD NOT RUN -- %s' % msg)
    sys.exit(2)


def read(rel):
    with open(os.path.join(ROOT, rel), 'r', encoding='utf-8', newline='') as fh:
        return fh.read()


def write(rel, text):
    with open(os.path.join(ROOT, rel), 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)


def suite_passes():
    """Anything other than exit 0 is a refusal -- a suite that cannot run has
    not cleared the code either."""
    p = subprocess.run([NODE, SUITE], cwd=ROOT, capture_output=True, text=True)
    return p.returncode == 0


# ── MUTATIONS ───────────────────────────────────────────────────────────────
# Each returns the mutated endpoint source, or None when its anchor is gone --
# which is COULD NOT RUN, never a pass.

def m1_guard_counts_provisioners_again():
    """THE ORIGINAL DEFECT, exactly: the guard counts owner+admin again."""
    s = read(ENDPOINT)
    old = ("      const activeOwners = rowsAll.filter(function (x) {\n"
           "        return x.active === true && GUARD_ROLES.indexOf(x.role) !== -1;\n"
           "      });")
    if old not in s:
        return None
    return s.replace(old, old.replace('GUARD_ROLES', 'PROVISIONING_ROLES'), 1)


def m2_target_test_widens():
    """The guard fires only when the TARGET is an owner. Widening the target
    test back to any provisioner is the half-revert that still refuses the
    headline case, so a single-arm suite passes it."""
    s = read(ENDPOINT)
    old = "if (!nextActive && GUARD_ROLES.indexOf(target.role) !== -1"
    if old not in s:
        return None
    return s.replace(old, "if (!nextActive && PROVISIONING_ROLES.indexOf(target.role) !== -1", 1)


def m3_guard_roles_includes_admin():
    """The constant is widened rather than the call site -- the quiet revert."""
    s = read(ENDPOINT)
    old = "const GUARD_ROLES = [SOLE_ROLE];"
    if old not in s:
        return None
    return s.replace(old, "const GUARD_ROLES = [SOLE_ROLE, 'admin'];", 1)


def m4_inactive_owners_count_as_cover():
    """A deactivated owner starts counting, so the last ACTIVE owner can go."""
    s = read(ENDPOINT)
    old = "        return x.active === true && GUARD_ROLES.indexOf(x.role) !== -1;"
    if old not in s:
        return None
    return s.replace(old, "        return GUARD_ROLES.indexOf(x.role) !== -1;", 1)


def m5_off_by_one():
    """`<= 1` becomes `< 1`, so the guard only fires at ZERO owners -- by which
    point the thing it exists to prevent has already happened."""
    s = read(ENDPOINT)
    old = "target.active === true && activeOwners.length <= 1) {"
    if old not in s:
        return None
    return s.replace(old, "target.active === true && activeOwners.length < 1) {", 1)


def m6_refuses_but_still_writes():
    """The 409 is returned and the PATCH goes out anyway. A suite that reads
    only the status code passes this one."""
    s = read(ENDPOINT)
    old = "        const lastAdminAudited = await audit('credential_change_refused'"
    if old not in s:
        return None
    injected = (
        "        await fetch(rest('sd_employee_auth?license_hash=eq.' + enc(licHash) +\n"
        "          '&employee_id=eq.' + enc(target_id)), { method: 'PATCH',\n"
        "          headers: Object.assign({}, headers, { Prefer: 'return=representation' }),\n"
        "          body: JSON.stringify({ active: nextActive }) });\n" + old)
    return s.replace(old, injected, 1)


def m7_the_old_comment_returns():
    """The claim that protected the defect is re-asserted. Not a code change --
    and that is the point: the sentence is what carried this through review."""
    s = read(ENDPOINT)
    old = "      // ── THIS COMMENT CALLED THE DEFECT A GUARANTEE, AND THAT IS THE PART"
    if old not in s:
        return None
    return s.replace(old,
        "      // Quarantined guard, same as SAIRNcode's: unreachable by\n"
        "      // construction while the caller-still-active check above stands.\n" + old, 1)


def m8_audit_logs_the_wrong_count():
    """The refusal logs the provisioner count, so the audit trail carries a
    number that contradicts the entry beside it."""
    s = read(ENDPOINT)
    old = "active_admins: activeOwners.length, active_provisioners: activeAdmins.length"
    if old not in s:
        return None
    return s.replace(old, "active_admins: activeAdmins.length", 1)


MUTATIONS = [
    ('1. the guard counts PROVISIONING_ROLES again -- THE ORIGINAL DEFECT',
     m1_guard_counts_provisioners_again),
    ('2. the TARGET test widens back to any provisioner -- the half-revert',
     m2_target_test_widens),
    ('3. GUARD_ROLES is widened to include admin -- the quiet revert',
     m3_guard_roles_includes_admin),
    ('4. INACTIVE owners count as cover',
     m4_inactive_owners_count_as_cover),
    ('5. off by one: the guard fires only at ZERO owners, too late',
     m5_off_by_one),
    ('6. refuses 409 AND SENDS THE PATCH ANYWAY -- passes a status-only suite',
     m6_refuses_but_still_writes),
    ('7. the "unreachable by construction" claim is re-asserted -- PROSE ONLY',
     m7_the_old_comment_returns),
    ('8. the refusal audits the provisioner count instead of the owner count',
     m8_audit_logs_the_wrong_count),
]


def main():
    for rel in (SUITE, ENDPOINT):
        if not os.path.isfile(os.path.join(ROOT, rel)):
            die('%s is not in this clone. This probe asserts nothing without it.' % rel)

    pre = subprocess.run(['git', 'status', '--porcelain', SUITE, ENDPOINT],
                         cwd=ROOT, capture_output=True, text=True)
    if pre.returncode != 0:
        die('could not read git status: %s' % (pre.stderr or '').strip())
    already_dirty = sorted(l[3:] for l in pre.stdout.splitlines() if l.strip())

    if not suite_passes():
        die('the suite is ALREADY RED before any mutation. A probe against a '
            'red suite proves nothing.')
    print('baseline: %s is GREEN\n' % SUITE)

    original = read(ENDPOINT)
    survived = []
    try:
        for name, build in MUTATIONS:
            mutated = build()
            if mutated is None:
                die('mutation %r could not be applied -- its anchor is gone. '
                    'That is NOT a pass; the probe has stopped testing what it '
                    'claims to test.' % name)
            if mutated == original:
                die('mutation %r changed nothing.' % name)
            write(ENDPOINT, mutated)
            passed = suite_passes()
            write(ENDPOINT, original)
            if passed:
                survived.append(name)
            print('  %-4s %s' % ('SURV' if passed else 'ok', name))
    finally:
        write(ENDPOINT, original)

    print()
    if read(ENDPOINT) != original:
        print('NOT RESTORED: %s' % ENDPOINT)
        return 1
    print('  ok   %s is byte-identical again' % ENDPOINT)

    if not suite_passes():
        print('  FAIL the suite is not green again with everything restored')
        return 1
    print('  ok   the suite is GREEN again with everything restored')

    post = subprocess.run(['git', 'status', '--porcelain', SUITE, ENDPOINT],
                          cwd=ROOT, capture_output=True, text=True)
    now_dirty = sorted(l[3:] for l in post.stdout.splitlines() if l.strip())
    if now_dirty != already_dirty:
        print('NEWLY DIRTY: %s' % ', '.join(set(now_dirty) - set(already_dirty)))
        return 1
    print('  ok   nothing newly dirty (%d file(s) were already modified before '
          'this run and are not its doing)' % len(already_dirty))

    if survived:
        print('\n%d MUTATION(S) SURVIVED -- the suite passed while the code was '
              'broken:' % len(survived))
        for n in survived:
            print('   %s' % n)
        return 1

    print('\nALL %d MUTATIONS REFUSED.' % len(MUTATIONS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
