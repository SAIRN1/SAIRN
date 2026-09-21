"""Negative control for api/provisioner-health-sole-role.test.js.

    python tests/run_provisioner_health_sole_role_sabotage_probe.py

Exit 0  every planted defect was REFUSED, and every file touched is
        byte-identical again afterwards
Exit 1  a planted defect SURVIVED, or a file was left modified
Exit 2  COULD NOT RUN -- never folded into either of the other two

── WHY A MONITOR NEEDS THIS MORE THAN MOST CODE ────────────────────────────
This endpoint's failure mode is silence. A guard that stops working refuses
something it should allow, and somebody complains within the hour. A MONITOR
that stops working reports HEALTHY, and nobody complains at all -- which is
precisely what it did before 2026-09-21: a StoneDesk licence with no owner row
reported HEALTHY for as long as that state existed.

So the arms that matter are not the ones proving it detects the bad state. They
are the ones proving it CANNOT be quietly returned to reporting green.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITE = os.path.join('api', 'provisioner-health-sole-role.test.js')
ENDPOINT = os.path.join('api', 'provisioner-health.js')
SD_AUTH = os.path.join('api', 'sd-auth.js')
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
    p = subprocess.run([NODE, SUITE], cwd=ROOT, capture_output=True, text=True)
    return p.returncode == 0


# ── MUTATIONS. Each returns {rel: source} or None when its anchor is gone. ──

def m1_count_over_provisioning_roles_again():
    """THE ORIGINAL BLIND SPOT: the sole-role count goes back to every role."""
    s = read(ENDPOINT)
    old = "      ? rows.filter((x) => x && x.role === cfg.sole) : [];"
    if old not in s:
        return None
    return {ENDPOINT: s.replace(
        old, "      ? rows.filter((x) => x && cfg.roles.indexOf(x.role) !== -1) : [];", 1)}


def m2_sole_states_never_evaluated():
    """`cfg.sole` is dropped from the map, so the new states cannot fire and
    every licence reports HEALTHY again -- the quiet revert."""
    s = read(ENDPOINT)
    old = "sole: sd.SOLE_ROLE }"
    if old not in s:
        return None
    return {ENDPOINT: s.replace(old, "sole: undefined }", 1)}


def m3_trapdoor_collapsed_into_degraded():
    """The two sole-role states are merged, so 'no owner row at all' is
    reported as the recoverable one and nobody is told SQL is required."""
    s = read(ENDPOINT)
    old = "    else if (cfg.sole && soleRows.length === 0) state = 'SOLE_ROLE_TRAPDOOR';"
    if old not in s:
        return None
    return {ENDPOINT: s.replace(
        old, "    else if (cfg.sole && soleRows.length === 0) state = 'SOLE_ROLE_DEGRADED';", 1)}


def m4_degraded_claims_unrecoverable():
    """The opposite error: a recoverable state cries emergency. A monitor that
    over-reports gets ignored, which ends in the same silence."""
    s = read(ENDPOINT)
    old = "      SOLE_ROLE_DEGRADED: 'RECOVERABLE, BUT ONE STEP FROM THE TRAPDOOR:"
    if old not in s:
        return None
    return {ENDPOINT: s.replace(
        old, "      SOLE_ROLE_DEGRADED: 'UNRECOVERABLE THROUGH THE API:", 1)}


def m5_app_dropped_from_the_map():
    """One app quietly leaves the map -- exactly how ten of them came to be
    unwatched in the first place."""
    s = read(ENDPOINT)
    old = "  sairngrounds: { table: grd.EMPLOYEE_TABLE, roles: grd.PROVISIONING_ROLES, sole: grd.SOLE_ROLE },\n"
    if old not in s:
        return None
    return {ENDPOINT: s.replace(old, "", 1)}


def m6_role_hardcoded_in_the_map():
    """The rule is restated in the map instead of imported, which is the drift
    the file's own header exists to prevent."""
    s = read(ENDPOINT)
    old = "  stonedesk: { table: sd.EMPLOYEE_TABLE, roles: sd.PROVISIONING_ROLES, sole: sd.SOLE_ROLE },"
    if old not in s:
        return None
    return {ENDPOINT: s.replace(
        old, "  stonedesk: { table: sd.EMPLOYEE_TABLE, roles: ['owner', 'admin'], sole: 'owner' },", 1)}


def m7_message_stops_naming_the_role():
    """The operator is told a provisioner is missing without being told WHICH
    role to insert -- on a two-role app that is the one fact they need."""
    s = read(ENDPOINT)
    old = 'this licence holds NO "\' + cfg.sole + \'" row at all'
    if old not in s:
        return None
    return {ENDPOINT: s.replace(old, 'this licence holds NO provisioner row at all', 1)}


def m8_the_endpoint_starts_writing():
    """A health check that writes is not one. The header's read-only claim is
    load-bearing: this endpoint is reachable with a licence key alone."""
    s = read(ENDPOINT)
    old = "    const rows = (await r.json()) || [];"
    if old not in s:
        return None
    return {ENDPOINT: s.replace(
        old, old + "\n    await fetch(sb.rest(cfg.table), { method: 'POST', headers: sb.headers, body: '{}' });", 1)}


MUTATIONS = [
    ('1. the sole-role count goes back to every provisioning role -- THE ORIGINAL BLIND SPOT',
     m1_count_over_provisioning_roles_again),
    ('2. cfg.sole dropped, so the new states can never fire -- the quiet revert',
     m2_sole_states_never_evaluated),
    ('3. "no sole-role row at all" reported as the RECOVERABLE state',
     m3_trapdoor_collapsed_into_degraded),
    ('4. the recoverable state cries UNRECOVERABLE -- over-reporting ends in the same silence',
     m4_degraded_claims_unrecoverable),
    ('5. an app quietly leaves the map -- how ten came to be unwatched',
     m5_app_dropped_from_the_map),
    ('6. a role list is hardcoded in the map instead of imported',
     m6_role_hardcoded_in_the_map),
    ('7. the refusal stops naming WHICH role is missing',
     m7_message_stops_naming_the_role),
    ('8. the health check starts WRITING',
     m8_the_endpoint_starts_writing),
]


def main():
    for rel in (SUITE, ENDPOINT, SD_AUTH):
        if not os.path.isfile(os.path.join(ROOT, rel)):
            die('%s is not in this clone.' % rel)

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
            patch = build()
            if patch is None:
                die('mutation %r could not be applied -- its anchor is gone. '
                    'That is NOT a pass; the probe has stopped testing what it '
                    'claims to test.' % name)
            for rel, src in patch.items():
                if src == read(rel):
                    die('mutation %r changed nothing.' % name)
                write(rel, src)
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
        print('\n%d MUTATION(S) SURVIVED -- the suite passed while the monitor '
              'was broken:' % len(survived))
        for n in survived:
            print('   %s' % n)
        return 1

    print('\nALL %d MUTATIONS REFUSED.' % len(MUTATIONS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
