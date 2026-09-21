"""Negative control for api/_lib/last-admin-sole-role.test.js.

    python tests/run_last_admin_sole_role_sabotage_probe.py

Exit 0  every planted defect was REFUSED by the suite, and every file this
        probe touched is byte-identical again afterwards
Exit 1  a planted defect SURVIVED (the suite passed while the code was broken),
        or a file was left modified
Exit 2  COULD NOT RUN -- never folded into either of the other two

── WHY A SUITE NEEDS THIS ──────────────────────────────────────────────────
`api/_lib/last-admin-sole-role.test.js` is green. So was every suite on this
platform on the day the defect it now catches was shipping in three apps: a
superintendent, an HR officer or a crew lead could deactivate the last owner,
200, PATCH sent, licence dead. Nothing was red, because nothing was looking.

A GREEN SUITE IS EVIDENCE ABOUT THE SUITE UNTIL SOMETHING MAKES IT FAIL ON
PURPOSE. Each mutation below re-introduces the real defect, or breaks the fix
in a way a plausible future edit would, and the suite must go red for each.

── THE ONE THAT MATTERS MOST IS MUTATION 2 ─────────────────────────────────
Deleting `SOLE_ROLE` is loud. Changing the call site to pass `null` while
LEAVING the constant declared is the quiet one -- the file still reads as
though it has a sole role, and only the call site tells the truth. That is why
`endpointConsts()` parses what the call site PASSES and not merely what the
file declares, and mutation 2 is the arm that proves it does.
"""

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITE = os.path.join('api', '_lib', 'last-admin-sole-role.test.js')
ENGINE = os.path.join('api', '_lib', 'employee-lifecycle.js')
APPS = [os.path.join('api', f) for f in ('grd-auth.js', 'sb-auth.js', 'scp-auth.js')]


def die(msg, code=2):
    print('\nCOULD NOT RUN -- %s' % msg)
    sys.exit(code)


def read(rel):
    with open(os.path.join(ROOT, rel), 'r', encoding='utf-8', newline='') as fh:
        return fh.read()


def write(rel, text):
    with open(os.path.join(ROOT, rel), 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)


def suite_passes():
    """True when the suite exits 0. Anything else -- including a crash -- is a
    refusal, because a suite that cannot run has not cleared the code either."""
    p = subprocess.run([NODE, SUITE], cwd=ROOT, capture_output=True, text=True)
    return p.returncode == 0, (p.stdout or '') + (p.stderr or '')


NODE = 'node'

# ── THE MUTATIONS ───────────────────────────────────────────────────────────
# Each returns a dict {relative_path: mutated_source} or None when it cannot be
# applied, which is COULD NOT RUN and never a pass.

def m1_remove_sole_role_pass():
    """The original defect, exactly: the call site stops forwarding soleRole."""
    out = {}
    for rel in APPS:
        s = read(rel)
        if 'soleRole: SOLE_ROLE,\n' not in s:
            return None
        out[rel] = s.replace('        soleRole: SOLE_ROLE,\n', '', 1)
    return out


def m2_pass_null_but_keep_the_constant():
    """The QUIET one -- the file still declares SOLE_ROLE, the call site lies."""
    out = {}
    for rel in APPS:
        s = read(rel)
        if 'soleRole: SOLE_ROLE,' not in s:
            return None
        out[rel] = s.replace('soleRole: SOLE_ROLE,', 'soleRole: null,', 1)
    return out


def m3_sole_role_not_in_provisioning_roles():
    """Over-restriction: a sole role nobody holds refuses EVERY deactivation."""
    rel = APPS[0]
    s = read(rel)
    if "const SOLE_ROLE = 'owner';" not in s:
        return None
    return {rel: s.replace("const SOLE_ROLE = 'owner';",
                           "const SOLE_ROLE = 'proprietor';", 1)}


def m4_guard_counts_over_roles_again():
    """The engine stops honouring soleRole -- the fix undone one layer down,
    where no endpoint diff would show it."""
    s = read(ENGINE)
    old = 'const guardRoles = soleRole ? [soleRole] : roles;'
    if old not in s:
        return None
    return {ENGINE: s.replace(old, 'const guardRoles = roles;', 1)}


def m5_guard_ignores_active():
    """An INACTIVE holder starts counting as cover, so the last ACTIVE owner
    can be deactivated because a deactivated one exists."""
    s = read(ENGINE)
    old = "(x) => x.active === true && guardRoles.indexOf(x.role) !== -1);"
    if old not in s:
        return None
    return {ENGINE: s.replace(old, "(x) => guardRoles.indexOf(x.role) !== -1);", 1)}


def m6_refuses_but_still_writes():
    """The nastiest shape: the 409 is returned and the PATCH goes out anyway.
    A suite reading only the status code passes this."""
    s = read(ENGINE)
    old = """  if (!nextActive && guardRoles.indexOf(target.role) !== -1 &&
      target.active === true && activeProvisioners.length <= 1) {"""
    if old not in s:
        return None
    # Issue the PATCH first, then refuse -- status says no, store says yes.
    injected = """  if (!nextActive && guardRoles.indexOf(target.role) !== -1 &&
      target.active === true && activeProvisioners.length <= 1) {
    await fetch(
      ctx.rest(ctx.table + '?license_hash=eq.' + encodeURIComponent(ctx.licHash) +
               '&employee_id=eq.' + encodeURIComponent(target_id)),
      { method: 'PATCH',
        headers: Object.assign({}, ctx.headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({ active: nextActive }) });"""
    return {ENGINE: s.replace(old, injected, 1)}


MUTATIONS = [
    ('1. the call site stops forwarding soleRole -- THE ORIGINAL DEFECT, all three apps',
     m1_remove_sole_role_pass),
    ('2. the call site passes null while SOLE_ROLE STAYS DECLARED -- the quiet one',
     m2_pass_null_but_keep_the_constant),
    ('3. SOLE_ROLE names a role nobody holds -- the OVER-RESTRICTIVE failure',
     m3_sole_role_not_in_provisioning_roles),
    ('4. the engine stops honouring soleRole at all -- the fix undone one layer down',
     m4_guard_counts_over_roles_again),
    ('5. the guard counts INACTIVE holders as cover',
     m5_guard_ignores_active),
    ('6. the guard refuses 409 AND SENDS THE PATCH ANYWAY -- passes a status-only suite',
     m6_refuses_but_still_writes),
]


def main():
    for rel in [SUITE, ENGINE] + APPS:
        if not os.path.isfile(os.path.join(ROOT, rel)):
            die('%s is not in this clone. This probe asserts nothing without it.' % rel)

    # A DIRTY TREE MAKES "RESTORED" UNPROVABLE, so it is established up front
    # rather than discovered at the end.
    pre = subprocess.run(['git', 'status', '--porcelain'] + [SUITE, ENGINE] + APPS,
                         cwd=ROOT, capture_output=True, text=True)
    if pre.returncode != 0:
        die('could not read git status: %s' % (pre.stderr or '').strip())
    already_dirty = sorted(l[3:] for l in pre.stdout.splitlines() if l.strip())

    ok, out = suite_passes()
    if not ok:
        die('the suite is ALREADY RED before any mutation. Fix that first -- a '
            'probe against a red suite proves nothing.\n\n' + out[-1500:])
    print('baseline: %s is GREEN\n' % SUITE)

    originals = {rel: read(rel) for rel in [ENGINE] + APPS}
    results = []
    try:
        for name, build in MUTATIONS:
            patch = build()
            if patch is None:
                die('mutation %r could not be applied -- the anchor it edits is '
                    'gone. That is NOT a pass; the probe has stopped testing '
                    'what it claims to test.' % name)
            for rel, src in patch.items():
                write(rel, src)
            passed, _ = suite_passes()
            for rel in patch:
                write(rel, originals[rel])
            results.append((name, passed))
            print('  %-4s %s' % ('SURV' if passed else 'ok', name))
    finally:
        for rel, src in originals.items():
            write(rel, src)

    print()
    survived = [n for n, p in results if p]
    for rel in [ENGINE] + APPS:
        if read(rel) != originals[rel]:
            print('NOT RESTORED: %s' % rel)
            sys.exit(1)
    print('  ok   every file this probe touched is byte-identical again')

    ok, _ = suite_passes()
    print('  %s   the suite is GREEN again with everything restored'
          % ('ok  ' if ok else 'FAIL'))
    if not ok:
        sys.exit(1)

    post = subprocess.run(['git', 'status', '--porcelain'] + [SUITE, ENGINE] + APPS,
                          cwd=ROOT, capture_output=True, text=True)
    now_dirty = sorted(l[3:] for l in post.stdout.splitlines() if l.strip())
    if now_dirty != already_dirty:
        print('NEWLY DIRTY: %s' % ', '.join(set(now_dirty) - set(already_dirty)))
        sys.exit(1)
    print('  ok   nothing newly dirty (%d file(s) were already modified before '
          'this run and are not its doing)' % len(already_dirty))

    if survived:
        print('\n%d MUTATION(S) SURVIVED -- the suite passed while the code was '
              'broken:' % len(survived))
        for n in survived:
            print('   %s' % n)
        sys.exit(1)

    print('\nALL %d MUTATIONS REFUSED.' % len(MUTATIONS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
