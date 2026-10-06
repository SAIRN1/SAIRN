#!/usr/bin/env python
"""dnt_appointments_write_gate_repro.py -- reproducing artifact: dnt_appointments
write has neither a role check nor a provider-ownership check, while its own
sibling read scopes non-broad-read roles to their own linked provider
(DNT_PATIENT_BROAD_READ_ROLES = {owner, frontdesk}, api/sd-data.js:13746).
Found while re-deriving the SAIRNdental gate-parity vertical independently
with this role's own tool (item 4, dependency re-derivation), not an
original target.

Exit 1 REPRODUCES (no role/provider-ownership check on write). Exit 0 if a
real fix lands. Exit 2 COULD NOT RUN.

Usage: python dnt_appointments_write_gate_repro.py [--repo PATH] [--selftest]
"""
import argparse
import os
import re
import sys


def check(repo):
    path = os.path.join(repo, 'api', 'sd-data.js')
    if not os.path.isfile(path):
        return None, 'COULD NOT RUN: %s not found' % path
    src = open(path, encoding='utf-8').read()
    m = re.search(r"if \(resource === 'dnt_appointments' && action === 'write'\) \{(.*?)\n    if \(resource ===",
                  src, re.DOTALL)
    if not m:
        return None, 'COULD NOT RUN: dnt_appointments write block not found'
    body = m.group(1)
    has_role = bool(re.search(r'_ROLES', body))
    has_provider_check = ('providerId' in body) or bool(re.search(r'provider_id\s*===?', body))
    reproduces = not has_role and not has_provider_check
    return reproduces, 'role_check=%r provider_ownership_check=%r' % (has_role, has_provider_check)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    reproduces, detail = check(args.repo)
    if reproduces is None:
        print(detail)
        sys.exit(2)
    print(('REPRODUCES' if reproduces else 'CLEAN') + ': ' + detail)
    sys.exit(1 if reproduces else 0)


def selftest():
    import tempfile
    bad = "if (resource === 'dnt_appointments' && action === 'write') {\n  doSomething();\n}\n    if (resource ===\n"
    good = "if (resource === 'dnt_appointments' && action === 'write') {\n  if (!X_ROLES[session.role]) return;\n}\n    if (resource ===\n"
    results = []
    for label, text in (('bad', bad), ('good', good)):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, 'api'))
        with open(os.path.join(d, 'api', 'sd-data.js'), 'w', encoding='utf-8') as f:
            f.write(text)
        reproduces, detail = check(d)
        results.append((label, reproduces, detail))
    ok = results[0][1] is True and results[1][1] is False
    print('SELFTEST %s: %r' % ('PASS' if ok else 'FAIL', results))
    return 0 if ok else 1


if __name__ == '__main__':
    main()
