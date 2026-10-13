#!/usr/bin/env python
"""sf_post_staff_gate_probe.py -- baseline probe for the NOT-YET-IMPLEMENTED
"post staff" gate rule on the five Tier A SAIRNfreedom resources named in
docs/handoff-hank-2026-10-12.md, section "Five Tier A SAIRNfreedom resources
are still ungated, by decision": sf_district_imports, sf_events,
sf_permit_flags, sf_products, sf_vehicles.

Modeled on tools-hover2/scp_session_gate_repro.py's convention (static
regex/text analysis of api/sd-data.js, no live HTTP calls, selftest fixture
pinning the parsing logic). Differs from that template in one structural way,
because the code it is reading differs: SAIRNscape's sf_/scp_ sibling
resources each have their OWN per-resource dispatch branch
(`if (resource === 'x' && action === 'y') { ... }`), so that template also
checks for a branch-local, unconditional verifySessionToken call. ALL sf_
resources -- gated and ungated alike -- dispatch through two resource-generic
branches keyed only by `SF_RESOURCES[resource]` (api/sd-data.js:13767,
:13775); neither branch calls verifySessionToken for ANY resource. So for sf_
resources the only per-resource gate signal that exists is membership in
SD_SESSION_GATED (api/sd-data.js:817) with the action in its verb list. This
script checks exactly that, plus a sanity sweep confirming no individual
`resource === 'sf_x'` branch exists anywhere in the file for any of the five
(ruling out undocumented partial protection, per the task's own instruction
not to assume this).

This script does not call api/sd-data.js, does not open a network
connection, and does not implement the gate. It is read-only static analysis,
written to establish today's baseline ahead of a product decision that has
not been made (see the spec at
.claude/skills/sairn-hover-auditor/references/sf-post-staff-gate-rule-probe-spec.md).

Exit 1 REPRODUCES (at least one of the 5 resources is gated on NEITHER axis,
for either read or write -- i.e. the known-open baseline). Exit 0 FIXED (all
5 are in SD_SESSION_GATED for both read and write, which would deny both the
unauthenticated axis and the cross-post axis via verifySessionToken's own
license_hash check, api/_lib/auth.js:606 -- not expected on main today).
Exit 2 COULD NOT RUN.

Usage:
  python sf_post_staff_gate_probe.py --all [--repo PATH]
  python sf_post_staff_gate_probe.py --resource sf_vehicles --action read
  python sf_post_staff_gate_probe.py --selftest
"""
import argparse
import os
import re
import sys

RESOURCES = [
    'sf_district_imports', 'sf_events', 'sf_permit_flags', 'sf_products',
    'sf_vehicles',
]

ACTIONS = ('read', 'write')

# Matches an individual per-resource dispatch branch, the shape used by
# every OTHER sf_ resource family member in this file EXCEPT the generic
# SF_RESOURCES branches -- used here only to confirm none of the 5 has one
# (i.e. no undocumented special-case branch), not to find a gate inside it.
INDIVIDUAL_BRANCH_RE = re.compile(
    r"if \(resource === '(%s)' && action === '(\w+)'\) \{" %
    '|'.join(re.escape(r) for r in RESOURCES))


def read_src(repo):
    path = os.path.join(repo, 'api', 'sd-data.js')
    if not os.path.isfile(path):
        return None, 'COULD NOT RUN: %s not found' % path
    return open(path, encoding='utf-8').read(), None


def session_gated_map(src):
    """Parses SD_SESSION_GATED (api/sd-data.js:817) into {resource: [verbs]}.
    Returns None if the block itself cannot be found -- a structural change
    this probe must not silently misread as "nothing gated"."""
    m = re.search(r'const SD_SESSION_GATED = \{(.*?)\n    \};', src, re.DOTALL)
    if not m:
        return None
    block = m.group(1)
    out = {}
    for rm in re.finditer(r"'(\w+)':\s*\[([^\]]*)\]", block):
        name = rm.group(1)
        verbs = re.findall(r"'(\w+)'", rm.group(2))
        out[name] = verbs
    return out


def sf_resources_set(src):
    """Parses SF_RESOURCES (api/sd-data.js:13738) into a set of resource
    names, confirming each of the 5 really is a dispatchable resource (and
    not, say, a typo in the handoff) rather than assuming it from the name
    alone."""
    m = re.search(r'const SF_RESOURCES = \{(.*?)\n    \};', src, re.DOTALL)
    if not m:
        return None
    return set(re.findall(r'(\w+):\s*\'\w+_id\'', m.group(1)))


def individual_branches_found(src):
    """Any per-resource `resource === 'sf_x'` branch for one of the 5, found
    ANYWHERE in the file. Expected to be empty -- confirms no undocumented
    partial/special-case protection exists outside the generic SF_RESOURCES
    dispatch."""
    return sorted(set(m.group(1) for m in INDIVIDUAL_BRANCH_RE.finditer(src)))


def check_one(resource, gated_map, sf_set, individual):
    if sf_set is not None and resource not in sf_set:
        return None, 'COULD NOT RUN: %r not found in SF_RESOURCES' % resource
    verbs = gated_map.get(resource, []) if gated_map is not None else []
    has_individual_branch = resource in individual
    result = {}
    for action in ACTIONS:
        # Gated iff SD_SESSION_GATED lists this action for this resource.
        # (No per-action-body check is possible here -- see module docstring
        # -- because the generic branch is shared by all 36 SF_RESOURCES and
        # carries no verifySessionToken call for any of them.)
        gated = action in verbs
        result[action] = {
            'gated': gated,
            'axis_unauthenticated_denied': gated,
            'axis_cross_post_denied': gated,
            'partial_protection_found': has_individual_branch,
        }
    return result, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--resource')
    ap.add_argument('--action', choices=ACTIONS)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    src, err = read_src(args.repo)
    if err:
        print(err)
        sys.exit(2)

    gated_map = session_gated_map(src)
    sf_set = sf_resources_set(src)
    if gated_map is None:
        print('COULD NOT RUN: SD_SESSION_GATED block not found')
        sys.exit(2)
    if sf_set is None:
        print('COULD NOT RUN: SF_RESOURCES block not found')
        sys.exit(2)
    individual = individual_branches_found(src)

    targets = [args.resource] if args.resource else (RESOURCES if args.all else [])
    if not targets:
        print('usage: --resource NAME [--action read|write] | --all | --selftest')
        sys.exit(2)

    any_reproduces = False
    for r in targets:
        result, err = check_one(r, gated_map, sf_set, individual)
        if err:
            print('%-24s COULD_NOT_RUN  %s' % (r, err))
            any_reproduces = True
            continue
        for action, info in sorted(result.items()):
            if args.action and action != args.action:
                continue
            state = 'FIXED' if info['gated'] else 'REPRODUCES'
            print('%-24s %-6s %-11s unauth_denied=%-5s cross_post_denied=%-5s '
                  'partial_protection_found=%s' %
                  (r, action, state, info['axis_unauthenticated_denied'],
                   info['axis_cross_post_denied'], info['partial_protection_found']))
            if not info['gated']:
                any_reproduces = True

    if individual:
        print('NOTE: individual resource===%r dispatch branch(es) found: %s' %
              ('sf_x', ', '.join(individual)))
    else:
        print('NOTE: no individual per-resource dispatch branch found for '
              'any of the 5 -- all dispatch only through the generic '
              'SF_RESOURCES read/write branches, confirming no undocumented '
              'partial protection exists.')

    sys.exit(1 if any_reproduces else 0)


def selftest():
    fixture = """
    const SD_SESSION_GATED = {
      'sf_gated_both': ['read', 'write'],
      'sf_gated_read_only': ['read'],
    };
    const SD_GATE_APP = {
      'sf_gated_both': 'sairnfreedom',
    };
    const SF_RESOURCES = {
      sf_gated_both: 'gated_both_id', sf_gated_read_only: 'gated_read_only_id',
      sf_ungated: 'ungated_id'
    };
    if (SF_RESOURCES[resource] && action === 'read') {
      res.status(200).json({ ok: true, data: [] });
    }
    if (SF_RESOURCES[resource] && action === 'write') {
      res.status(200).json({ ok: true });
    }
    if (resource === 'sf_special_cased' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnfreedom');
    }
"""
    import tempfile
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, 'api'))
    with open(os.path.join(d, 'api', 'sd-data.js'), 'w', encoding='utf-8') as f:
        f.write(fixture)

    global RESOURCES, INDIVIDUAL_BRANCH_RE
    old_r, old_re = RESOURCES, INDIVIDUAL_BRANCH_RE
    RESOURCES = ['sf_gated_both', 'sf_gated_read_only', 'sf_ungated', 'sf_special_cased']
    INDIVIDUAL_BRANCH_RE = re.compile(
        r"if \(resource === '(%s)' && action === '(\w+)'\) \{" %
        '|'.join(re.escape(r) for r in RESOURCES))
    try:
        src, _ = read_src(d)
        gated_map = session_gated_map(src)
        sf_set = sf_resources_set(src)
        individual = individual_branches_found(src)

        g1, _ = check_one('sf_gated_both', gated_map, sf_set, individual)
        g2, _ = check_one('sf_gated_read_only', gated_map, sf_set, individual)
        g3, _ = check_one('sf_ungated', gated_map, sf_set, individual)
        g4, err4 = check_one('sf_nonexistent', gated_map, sf_set, individual)
        g5, _ = check_one('sf_special_cased', gated_map, sf_set, individual)

        ok = (
            gated_map == {'sf_gated_both': ['read', 'write'], 'sf_gated_read_only': ['read']}
            and sf_set == {'sf_gated_both', 'sf_gated_read_only', 'sf_ungated'}
            and g1['read']['gated'] is True and g1['write']['gated'] is True
            and g2['read']['gated'] is True and g2['write']['gated'] is False
            and g3['read']['gated'] is False and g3['write']['gated'] is False
            and g4 is None and err4 is not None and 'COULD NOT RUN' in err4
            # sf_special_cased is NOT in RESOURCES' SF_RESOURCES map in this
            # fixture, so check_one must report COULD_NOT_RUN for it even
            # though it has an individual branch -- the individual-branch
            # sweep is informational (partial_protection_found), it must
            # never substitute for the SD_SESSION_GATED gate check itself.
            and g5 is None
            and individual == ['sf_special_cased']
        )
        print('SELFTEST %s: gated_map=%r sf_set=%r g1=%r g2=%r g3=%r '
              'missing_err=%r individual=%r' %
              ('PASS' if ok else 'FAIL', gated_map, sf_set, g1, g2, g3, err4, individual))
        return 0 if ok else 1
    finally:
        RESOURCES, INDIVIDUAL_BRANCH_RE = old_r, old_re


if __name__ == '__main__':
    main()
