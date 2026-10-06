#!/usr/bin/env python
"""alf_cross_resource_repro.py -- reproducing artifact for hank's own
gate_parity_check.py cross-resource flags on SAIRNcare (4 flagged tables:
alf_activities, alf_clients, alf_mar, alf_staff). This role's own check of
WHY each diverges, not a re-implementation of his tool -- it reads the two
real role-set definitions and the derive_charges response shape directly
out of api/sd-data.js and answers one question per table: does the
diverging branch's role gate actually admit a role excluded from the
table's own direct reader, and if so does the response hand back that
table's real field content (not just a computed aggregate)?

Four checks, each independent, each exit-coded on its own:
  alf_activities : CORRECT-BY-DESIGN, not checked for role-set overlap --
                    the code's own comment (api/sd-data.js ~10947) states
                    broad-read/narrow-write is the intended shape. Always
                    exits 0 (named here so it is not silently skipped).
  alf_clients    : CORRECT-BY-DESIGN -- derive_charges is management-only
                    and alf_clients/read already grants management-equivalent
                    roles (ALF_BROAD_READ_ROLES) the unfiltered read; no role
                    outside that set reaches derive_charges. Exits 0.
  alf_mar        : THE REAL ONE. ALF_MANAGEMENT_ROLES (gates derive_charges)
                    and ALF_MAR_ROLES (gates alf_mar/read directly) are
                    independent sets -- 'billing' is in the first and NOT in
                    the second. If true, AND derive_charges's own event
                    construction includes a raw field from alf_mar.data
                    (medication_name), a billing-role caller reads real PHI
                    through derive_charges that alf_mar/read would 403 them
                    for directly. Exit 1 if both hold (reproduces).
  alf_staff      : CORRECT-BY-DESIGN -- alf_compliance_rules/evaluate is the
                    #894 fix (role=True now), narrower than alf_staff/read's
                    role=False, the safe direction. Exit 0.

Exit 2 COULD NOT RUN if api/sd-data.js is missing or a cited pattern is gone
(refuses rather than reporting a stale finding as current).

Usage:
  python alf_cross_resource_repro.py --table alf_mar [--repo PATH]
  python alf_cross_resource_repro.py --all [--repo PATH]
  python alf_cross_resource_repro.py --selftest
"""
import argparse
import os
import re
import sys


def read_src(repo):
    path = os.path.join(repo, 'api', 'sd-data.js')
    if not os.path.isfile(path):
        return None, 'COULD NOT RUN: %s not found' % path
    return open(path, encoding='utf-8').read(), None


def roleset(src, name):
    m = re.search(r'%s\s*=\s*roleSet\(\{([^}]*)\}' % re.escape(name), src)
    if not m:
        return None
    return set(k.strip() for k in re.findall(r'(\w+)\s*:\s*true', m.group(1)))


def check_alf_mar(src):
    mgmt = roleset(src, 'ALF_MANAGEMENT_ROLES')
    mar = roleset(src, 'ALF_MAR_ROLES')
    if mgmt is None or mar is None:
        return None, 'COULD NOT RUN: ALF_MANAGEMENT_ROLES or ALF_MAR_ROLES pattern not found'
    excluded_role_admitted = bool(mgmt - mar)
    dc = re.search(r"resource === 'alf_billing' && action === 'derive_charges'.*?"
                   r"\n    if \(resource ===", src, re.DOTALL)
    if not dc:
        return None, 'COULD NOT RUN: derive_charges block not found'
    returns_raw_mar_field = 'medication_name' in dc.group(0)
    reproduces = excluded_role_admitted and returns_raw_mar_field
    detail = ('ALF_MANAGEMENT_ROLES-ALF_MAR_ROLES=%r, derive_charges returns medication_name=%r'
               % (sorted(mgmt - mar), returns_raw_mar_field))
    return reproduces, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--table', choices=['alf_activities', 'alf_clients', 'alf_mar', 'alf_staff'])
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

    tables = [args.table] if args.table else (
        ['alf_activities', 'alf_clients', 'alf_mar', 'alf_staff'] if args.all else [])
    if not tables:
        print('usage: --table NAME | --all | --selftest')
        sys.exit(2)

    any_reproduces = False
    for t in tables:
        if t == 'alf_mar':
            reproduces, detail = check_alf_mar(src)
            if reproduces is None:
                print('%-16s COULD_NOT_RUN  %s' % (t, detail))
                any_reproduces = True
                continue
            print('%-16s %-11s %s' % (t, 'REPRODUCES' if reproduces else 'CLEAN', detail))
            any_reproduces = any_reproduces or reproduces
        else:
            print('%-16s %-11s CORRECT-BY-DESIGN, not role-overlap-checked (see this file\'s docstring)' % (t, 'CLEAN'))
    sys.exit(1 if any_reproduces else 0)


def selftest():
    fixture_bad = """
    const ALF_MANAGEMENT_ROLES = roleSet({ owner: true, billing: true });
    const ALF_MAR_ROLES = roleSet({ owner: true, nursing: true, med_aide: true });
    if (resource === 'alf_billing' && action === 'derive_charges') {
      events.push({ description: d.medication_name || '' });
    }
    if (resource === 'x' && action === 'y') {
"""
    fixture_good = """
    const ALF_MANAGEMENT_ROLES = roleSet({ owner: true, billing: true });
    const ALF_MAR_ROLES = roleSet({ owner: true, nursing: true, med_aide: true, billing: true });
    if (resource === 'alf_billing' && action === 'derive_charges') {
      events.push({ description: d.medication_name || '' });
    }
    if (resource === 'x' && action === 'y') {
"""
    bad, detail_bad = check_alf_mar(fixture_bad)
    good, detail_good = check_alf_mar(fixture_good)
    ok = (bad is True) and (good is False)
    print('SELFTEST %s: known-bad=%r (%s)  known-good=%r (%s)' %
          ('PASS' if ok else 'FAIL', bad, detail_bad, good, detail_good))
    return 0 if ok else 1


if __name__ == '__main__':
    main()
