#!/usr/bin/env python
"""scp_session_gate_repro.py -- reproducing artifact: most SAIRNscape (scp_)
resources have no session gate at all, found during the undirected sweep
(lowest-mention-count pick, item 6, batch J) while reading the recent
5e33157e fix (which armed 'customers'/'invoices'/'scp_quotes' via the
platform's own two-list mechanism: SD_SESSION_GATED + SD_GATE_APP,
api/sd-data.js:817/1237). Checks BOTH possible gates per resource, unlike
grd_session_gate_repro.py (SAIRNgrounds has no SD_SESSION_GATED entries at
all, so only the per-branch check applied there) -- SAIRNscape genuinely
has three resources gated this way and six/eight that are not, so a
correct check here must look at both mechanisms or it mis-reports the
three real ones as reproducing too.

Exit 1 REPRODUCES (gated by NEITHER mechanism). Exit 0 FIXED (gated by
either). Exit 2 COULD NOT RUN.

Usage:
  python scp_session_gate_repro.py --all [--repo PATH]
  python scp_session_gate_repro.py --resource scp_designs --action read
  python scp_session_gate_repro.py --selftest
"""
import argparse
import os
import re
import sys

RESOURCES = [
    'scp_jobs', 'scp_quotes', 'scp_designs', 'scp_irr_controllers',
    'scp_irr_zones', 'scp_irr_schedules', 'scp_water_features',
    'scp_vendors', 'scp_progress_photos', 'customers', 'invoices',
]

BLOCK_RE = re.compile(r"if \(resource === '(%s)' && action === '(\w+)'\) \{" %
                      '|'.join(re.escape(r) for r in RESOURCES))


def read_src(repo):
    path = os.path.join(repo, 'api', 'sd-data.js')
    if not os.path.isfile(path):
        return None, 'COULD NOT RUN: %s not found' % path
    return open(path, encoding='utf-8').read(), None


def session_gated_set(src):
    """Resources in SD_SESSION_GATED, a SEPARATE pre-dispatch gate from the
    per-branch verifySessionToken pattern. Parsed from the literal block,
    not assumed -- a resource here never calls verifySessionToken itself
    and is still genuinely gated."""
    m = re.search(r'const SD_SESSION_GATED = \{(.*?)\n    \};', src, re.DOTALL)
    if not m:
        return None
    return set(re.findall(r"'(\w+)':\s*\[", m.group(1)))


def per_action_blocks(src, resource):
    out = {}
    for rm, am, body_start in ((m.group(1), m.group(2), m.end())
                               for m in BLOCK_RE.finditer(src) if m.group(1) == resource):
        nxt = src.find('\n    if (resource ===', body_start)
        out[am] = src[body_start:nxt if nxt != -1 else body_start + 600]
    return out


def check_one(resource, repo, gated_set):
    src, err = read_src(repo)
    if err:
        return None, err
    if gated_set is None:
        return None, 'COULD NOT RUN: SD_SESSION_GATED block not found'
    blocks = per_action_blocks(src, resource)
    if not blocks:
        return None, 'COULD NOT RUN: no dispatch branch for %r' % resource
    result = {}
    for action, body in blocks.items():
        global_gate = resource in gated_set
        branch_gate = 'verifySessionToken' in body
        result[action] = global_gate or branch_gate
    return result, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--resource')
    ap.add_argument('--action')
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
    gated_set = session_gated_set(src)

    targets = [args.resource] if args.resource else (RESOURCES if args.all else [])
    if not targets:
        print('usage: --resource NAME [--action ACTION] | --all | --selftest')
        sys.exit(2)

    any_reproduces = False
    for r in targets:
        result, err = check_one(r, args.repo, gated_set)
        if err:
            print('%-24s COULD_NOT_RUN  %s' % (r, err))
            any_reproduces = True
            continue
        for action, gated in sorted(result.items()):
            if args.action and action != args.action:
                continue
            print('%-24s %-10s %s' % (r, action, 'FIXED' if gated else 'REPRODUCES'))
            if not gated:
                any_reproduces = True
    sys.exit(1 if any_reproduces else 0)


def selftest():
    fixture = """
    const SD_SESSION_GATED = {
      'fx_global_gated': ['read', 'write'],
    };
    if (resource === 'fx_global_gated' && action === 'read') {
      res.status(200).json({ ok: true });
    }
    if (resource === 'fx_branch_gated' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'fx');
    }
    if (resource === 'fx_ungated' && action === 'read') {
      res.status(200).json({ ok: true, data: [] });
    }
"""
    import tempfile
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, 'api'))
    with open(os.path.join(d, 'api', 'sd-data.js'), 'w', encoding='utf-8') as f:
        f.write(fixture)

    global RESOURCES, BLOCK_RE
    old_r, old_re = RESOURCES, BLOCK_RE
    RESOURCES = ['fx_global_gated', 'fx_branch_gated', 'fx_ungated']
    BLOCK_RE = re.compile(r"if \(resource === '(%s)' && action === '(\w+)'\) \{" %
                          '|'.join(re.escape(r) for r in RESOURCES))
    try:
        src, _ = read_src(d)
        gated_set = session_gated_set(src)
        g1, _ = check_one('fx_global_gated', d, gated_set)
        g2, _ = check_one('fx_branch_gated', d, gated_set)
        g3, _ = check_one('fx_ungated', d, gated_set)
        g4, err4 = check_one('fx_nonexistent', d, gated_set)
        ok = (gated_set == {'fx_global_gated'} and
              g1 == {'read': True} and g2 == {'read': True} and
              g3 == {'read': False} and g4 is None and err4 is not None)
        print('SELFTEST %s: global=%r branch=%r ungated=%r missing_err=%r' %
              ('PASS' if ok else 'FAIL', g1, g2, g3, err4))
        return 0 if ok else 1
    finally:
        RESOURCES, BLOCK_RE = old_r, old_re


if __name__ == '__main__':
    main()
