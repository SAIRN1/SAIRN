#!/usr/bin/env python
"""hover2_gate_parity_check.py -- this role's OWN sibling-action gate-
asymmetry checker, independent of tools/gate_parity_check.py (hank's).

GOAL: a gate-parity conclusion for the vertical sweep must not rest on
trusting one implementation. This is a separate parser over the same
source file, built from scratch, kept in this role's own location, never
run against or depended on as this role's method for the sweep itself
(hank's tool is read ONLY as evidence when verifying HIS flags, per the
explicit instruction boundary -- never as the engine behind this role's
own vertical-by-vertical sweep).

NON-GOALS: cross-resource (one table read from two different resource
branches) is explicitly OUT of scope here -- that is hank's tool's own
2026-10-06 extension and re-implementing it would just be a second copy of
his algorithm with this role's name on it, not an independent check.
This tool answers the SAME-RESOURCE question only: do this resource's own
sibling actions (read vs write vs any named verb) agree on whether a role
check and an employee-assignment check gate them.

ALTERNATIVES CONSIDERED:
  1. Wrap/call tools/gate_parity_check.py and just re-print its result --
     rejected outright: the whole point is a result that does not depend
     on his code being correct.
  2. A full AST parser (esprima/acorn) for exact control-flow analysis --
     rejected for this pass: the existing hand-verification convention on
     this file (grep-bounded blocks, read the match) already works and a
     second heavyweight parser is not yet justified by a measured failure
     of the regex approach. Revisit if the regex approach is shown wrong.
  3. Per-resource exhaustive AST diffing of EVERY branch field -- rejected
     as over-scoped for a sweep tool; role/assignment are the two axes
     every hand-verification in this log has actually used.

CROSS-CUTTING: reads only (api/sd-data.js); writes nothing to the platform
repo. Shares no code with tools/gate_parity_check.py and was not consulted
while writing the detection patterns below (written from the role/
assignment vocabulary already used by hand in this role's own prior log
entries, e.g. seq622/632/634, not from reading hank's source).

LIMIT, MEASURED NOT ASSUMED: this tool's first real run (against rf_,
2026-10-06) under-detected rf_claims' assess_damage/reconcile assignment
gate -- both call rfAuth.ownsRow(session, claim), a named helper the first
version of ASSIGN_PAT could not see, so they printed assignment=False when
the real code assignment-gates them. Fixed in this same session before
first use by adding the ONE named helper found; this is LEXICAL, same as
tools/gate_parity_check.py's own documented limit, and a DIFFERENT helper
name is still invisible to it. Not claimed complete.

DETECTION (same two axes this role has used by hand all batch):
  role       -- a role-set membership check against session.role
                (SOMETHING_ROLES[session.role] or a roleSet(...) literal
                compared against session.role in the block)
  assignment -- a check comparing session.employee_id against a row's
                assigned_employee_id / employee_id field

Per resource with 2+ actions in the given app's RESOURCE region (keyed by
a caller-supplied prefix, e.g. --prefix rf_), reports each action's
(role, assignment) booleans and flags a GROUP where they disagree.

Usage:
  python hover2_gate_parity_check.py --prefix rf_ [--repo PATH]
  python hover2_gate_parity_check.py --selftest
"""
import argparse
import os
import re
import sys

BLOCK_START = re.compile(r"if \(resource === '(\w+)' && action === '(\w+)'\) \{")
ROLE_PAT = re.compile(r'\b[A-Z][A-Z0-9_]*_ROLES\b')
# Was `\b[A-Z][A-Z0-9_]*_ROLES\[session\.role\]` -- too narrow. rf_schedule's
# set_status (api/sd-data.js:9898) passes rfAuth.MANAGEMENT_ROLES and
# rfAuth.BROAD_READ_ROLES as ARGUMENTS into roofingLocations.canSeeSchedule(),
# never indexed inline, so the indexing-only pattern missed a real role gate
# on this tool's own first real run (same batch as the ownsRow fix above).
# Widened to "a _ROLES identifier appears anywhere in the block" -- looser,
# deliberately: an audit tool that under-detects a gate manufactures the
# exact false asymmetry it exists to rule out, which is worse than a rare
# over-detection (a _ROLES identifier referenced for an unrelated reason).
ASSIGN_PAT = re.compile(r'session\.employee_id\s*===?\s*\w|'
                        r'\w\.assigned_employee_id\s*===?\s*session\.employee_id|'
                        r'session\.employee_id\s*===?\s*\w*\.?assigned_employee_id|'
                        # NAMED helper, found on this tool's own first real run against
                        # rf_claims: rfAuth.ownsRow(session, claim) reads as an inline
                        # assignment check (api/sd-data.js:8899), invisible to the three
                        # literal patterns above. LEXICAL, same as hank's own tool's
                        # documented limit -- a DIFFERENT helper name is still invisible
                        # here. Named rather than claimed complete.
                        r'\w+Auth\.ownsRow\(|'
                        # SECOND named helper, same batch, rf_schedule/read+write:
                        # roofingLocations.canSeeSchedule(session, row, assignee, ...)
                        # performs BOTH the role and the per-row assignee check in one
                        # call -- the role half is already caught by the _ROLES-anywhere
                        # widening above, this catches the assignment half of the SAME
                        # call. Stopping at two named helpers rather than chasing every
                        # possible name: diminishing returns past the shapes actually
                        # found this run, and this tool's docstring already states it
                        # is lexical and not claimed complete.
                        r'canSeeSchedule\(')


def blocks(src, prefix):
    matches = list(BLOCK_START.finditer(src))
    out = []
    for i, m in enumerate(matches):
        resource, action = m.group(1), m.group(2)
        if not resource.startswith(prefix):
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(src)
        out.append((resource, action, src[start:end]))
    return out


def analyze(src, prefix):
    per_resource = {}
    for resource, action, body in blocks(src, prefix):
        per_resource.setdefault(resource, {})[action] = {
            'role': bool(ROLE_PAT.search(body)),
            'assignment': bool(ASSIGN_PAT.search(body)),
        }
    return per_resource


def report(per_resource):
    groups_flagged = 0
    lines = []
    for resource in sorted(per_resource):
        actions = per_resource[resource]
        if len(actions) < 2:
            continue
        roles = set(v['role'] for v in actions.values())
        assigns = set(v['assignment'] for v in actions.values())
        if len(roles) > 1 or len(assigns) > 1:
            groups_flagged += 1
            diffs = []
            if len(roles) > 1:
                diffs.append('role')
            if len(assigns) > 1:
                diffs.append('assignment')
            lines.append('! %s differs on: %s' % (resource, ', '.join(diffs)))
            for action in sorted(actions):
                v = actions[action]
                lines.append('    %-20s role=%-5s assignment=%s' %
                             (action, v['role'], v['assignment']))
    return groups_flagged, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prefix')
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if not args.prefix:
        print('usage: --prefix PREFIX_ | --selftest')
        sys.exit(2)

    path = os.path.join(args.repo, 'api', 'sd-data.js')
    if not os.path.isfile(path):
        print('COULD NOT RUN: %s not found' % path)
        sys.exit(2)
    src = open(path, encoding='utf-8').read()
    per_resource = analyze(src, args.prefix)
    if not per_resource:
        print('COULD NOT RUN: no resources matching prefix %r found' % args.prefix)
        sys.exit(2)

    groups_flagged, lines = report(per_resource)
    print('resources examined: %d (prefix %r)' % (len(per_resource), args.prefix))
    for l in lines:
        print(l)
    print('%d group(s) flagged' % groups_flagged)
    sys.exit(1 if groups_flagged else 0)


def selftest():
    fixture = """
    if (resource === 'fx_a' && action === 'read') {
      if (!FX_ROLES[session.role]) { return; }
      const ok = row.assigned_employee_id === session.employee_id;
    }
    if (resource === 'fx_a' && action === 'write') {
      if (!FX_ROLES[session.role]) { return; }
    }
    if (resource === 'fx_clean' && action === 'read') {
      if (!FX_ROLES[session.role]) { return; }
    }
    if (resource === 'fx_clean' && action === 'write') {
      if (!FX_ROLES[session.role]) { return; }
    }
    if (resource === 'fx_helper' && action === 'read') {
      if (!xyAuth.ownsRow(session, row)) { return; }
    }
    if (resource === 'fx_argrole' && action === 'read') {
      if (!canSeeRow(session, entry, xyAuth.MANAGEMENT_ROLES)) { return; }
    }
    if (resource === 'fx_sched' && action === 'read') {
      const ok = canSeeSchedule(session, row, assignee, xyAuth.MANAGEMENT_ROLES);
    }
"""
    per_resource = analyze(fixture, 'fx_')
    groups_flagged, lines = report(per_resource)
    ok = (groups_flagged == 1 and
          per_resource['fx_a']['read'] == {'role': True, 'assignment': True} and
          per_resource['fx_a']['write'] == {'role': True, 'assignment': False} and
          per_resource['fx_clean']['read'] == per_resource['fx_clean']['write'] and
          per_resource['fx_helper']['read']['assignment'] is True and
          per_resource['fx_argrole']['read']['role'] is True and
          per_resource['fx_sched']['read'] == {'role': True, 'assignment': True})
    print('SELFTEST %s: %d group(s) flagged (expected 1: fx_a, assignment divergence); fx_clean correctly unflagged; fx_helper, fx_argrole, fx_sched (three named-helper shapes) correctly detected' %
          ('PASS' if ok else 'FAIL', groups_flagged))
    return 0 if ok else 1


if __name__ == '__main__':
    main()
