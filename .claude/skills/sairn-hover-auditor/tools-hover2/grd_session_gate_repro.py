#!/usr/bin/env python
"""grd_session_gate_repro.py -- reproducing artifact for the SAIRNgrounds
grd_* session-gate finding (hover-audit-log seq630), not a new audit pass.
One resource, one deterministic check: does verifySessionToken appear
anywhere in that resource's read+write dispatch block in api/sd-data.js.

Exit 1 REPRODUCES the finding (zero session-check calls found -- the gap is
still there). Exit 0 means the gap is gone for that resource (fixed).
Exit 2 COULD NOT RUN (resource not found in the file, or the file is
missing) -- never silently folded into exit 0.

Usage:
  python grd_session_gate_repro.py --resource grd_dreamclose [--repo PATH]
  python grd_session_gate_repro.py --all [--repo PATH]   # every known resource, one line each
  python grd_session_gate_repro.py --selftest
"""
import argparse
import os
import re
import sys

RESOURCES = [
    'grd_schedule', 'grd_progress_photos', 'grd_invoices', 'grd_dreamclose',
    'grd_invasive_sightings', 'grd_ecosystem_reports', 'grd_rounds',
    'grd_cart_orders', 'grd_designs', 'grd_irr_controllers', 'grd_irr_zones',
    'grd_irr_schedules', 'grd_water_features', 'grd_training_courses',
    'grd_training_completions', 'grd_boq_rates', 'grd_vendors',
    'quotes', 'golf_zones',
]

BLOCK_RE = re.compile(r"if \(resource === '(%s)' && action === '(\w+)'\) \{" %
                      '|'.join(re.escape(r) for r in RESOURCES))


def blocks(src):
    """Yields (resource, action, block_text) for every dispatch branch,
    bounded by the next `if (resource ===` or end of file -- same bound
    convention this role's earlier grep-loop used by hand."""
    matches = list(BLOCK_RE.finditer(src))
    for i, m in enumerate(matches):
        start = m.end()
        end = len(src)
        nxt = src.find('\n    if (resource ===', start)
        if nxt != -1:
            end = nxt
        yield m.group(1), m.group(2), src[start:end]


def check_one(resource, repo):
    """Per-ACTION, not merged across a resource's siblings -- a resource with
    a gated 'read' and an ungated 'write' is still REPRODUCES for write.
    Returns (has_session_per_action: {action: bool}, caveat_or_None, err_or_None).
    CAVEAT: grd_progress_photos' write block DOES contain verifySessionToken,
    but only inside a nested `if (payload.qc_status === ...)` branch (hover
    seq630's own finding) -- present in the block is not the same claim as
    unconditional on the action's default path, and this tool's first real
    run (2026-10-06) conflated the two until this caveat was added. Named
    rather than silently reported as FIXED."""
    path = os.path.join(repo, 'api', 'sd-data.js')
    if not os.path.isfile(path):
        return None, None, 'COULD NOT RUN: %s not found' % path
    src = open(path, encoding='utf-8').read()
    found = [(a, b) for (r, a, b) in blocks(src) if r == resource]
    if not found:
        return None, None, 'COULD NOT RUN: no dispatch branch for %r in %s' % (resource, path)
    per_action = {a: ('verifySessionToken' in b) for (a, b) in found}
    caveat = None
    if resource == 'grd_progress_photos' and per_action.get('write'):
        caveat = ('PARTIAL: verifySessionToken only inside a qc_status '
                  'conditional, not on the default write path')
    return per_action, caveat, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--resource')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if args.all:
        repo = args.repo
        any_reproduces = False
        for r in RESOURCES:
            per_action, caveat, err = check_one(r, repo)
            if err:
                print('%-26s COULD_NOT_RUN  %s' % (r, err))
                any_reproduces = True
                continue
            for action, has in sorted(per_action.items()):
                state = 'FIXED' if has else 'REPRODUCES'
                note = (' (' + caveat + ')') if (caveat and action == 'write') else ''
                print('%-26s %-8s %s%s' % (r, action, state, note))
                if not has:
                    any_reproduces = True
        sys.exit(1 if any_reproduces else 0)

    if not args.resource:
        print('usage: --resource NAME | --all | --selftest')
        sys.exit(2)

    per_action, caveat, err = check_one(args.resource, args.repo)
    if err:
        print(err)
        sys.exit(2)
    any_reproduces = False
    for action, has in sorted(per_action.items()):
        state = 'FIXED' if has else 'REPRODUCES'
        note = (' -- ' + caveat) if (caveat and action == 'write') else ''
        print('%s %s: %s%s' % (args.resource, action, state, note))
        if not has:
            any_reproduces = True
    sys.exit(1 if any_reproduces else 0)


def selftest():
    fixture_fixed = """
    if (resource === 'fx_gated' && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'fx');
      if (!session) { return; }
      res.status(200).json({ ok: true });
    }
    if (resource === 'fx_ungated' && action === 'read') {
      res.status(200).json({ ok: true, data: [] });
    }
"""
    import tempfile
    tmpdir = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmpdir, 'api'))
    with open(os.path.join(tmpdir, 'api', 'sd-data.js'), 'w', encoding='utf-8') as f:
        f.write(fixture_fixed)

    global RESOURCES, BLOCK_RE
    old_resources, old_re = RESOURCES, BLOCK_RE
    RESOURCES = ['fx_gated', 'fx_ungated']
    BLOCK_RE = re.compile(r"if \(resource === '(%s)' && action === '(\w+)'\) \{" %
                          '|'.join(re.escape(r) for r in RESOURCES))
    try:
        gated, _, err1 = check_one('fx_gated', tmpdir)
        ungated, _, err2 = check_one('fx_ungated', tmpdir)
        missing, _, err3 = check_one('fx_nonexistent', tmpdir)
        ok = (err1 is None and gated == {'read': True} and
              err2 is None and ungated == {'read': False} and
              err3 is not None and missing is None)
        print('SELFTEST %s: gated=%r(err=%r) ungated=%r(err=%r) missing=%r(err=%r)' %
              ('PASS' if ok else 'FAIL', gated, err1, ungated, err2, missing, err3))
        return 0 if ok else 1
    finally:
        RESOURCES, BLOCK_RE = old_resources, old_re


if __name__ == '__main__':
    main()
