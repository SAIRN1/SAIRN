#!/usr/bin/env python
"""bld_draws_bypass_repro.py -- this role's OWN static repro for a same-
resource, cross-action gate bypass found during the undirected sweep (item
5, batch K) on SAIRNbuild (bld_).

GOAL: confirm, by direct source read rather than by trusting a comment,
that resource 'bld_draws' is reachable through TWO different action names
in api/sd-data.js, one gated and one not, both resolving the same table.

  (a) action='read' / 'write' dispatches through BLD_RESOURCES (the
      generic 30-resource pair the file's own comment calls "the shared
      job record... every role... reads them", deliberately no session
      gate) -- `select=data` off the bld_draws table.
  (b) action='wip' / 'release_retainage' dispatches through a BESPOKE
      branch, gated with verifySessionToken + BLD_BID_MANAGEMENT_ROLES,
      whose own comment calls the same information "management-level" --
      `select=draw_id,data` off the SAME bld_draws table.

A caller with no session cannot reach (b) but CAN reach (a) and receive
the identical `data` column the gated branch exists to restrict -- the
role check on 'wip' is bypassed simply by asking for 'read' instead.

NON-GOALS: this does not assert anything about the OTHER 29 generic
BLD_RESOURCES entries, which the file's own comment reasons about
separately and which this role's gate-parity sweep (a different tool,
different question) already covers; this is specific to bld_draws having
a documented "management-level" bespoke action that the generic path
routes around.

ALTERNATIVES CONSIDERED:
  1. Fire a live HTTP request against a demo tenant, the way the
     scp_/customers finding upstream was proven -- rejected: no demo
     credential for SAIRNbuild is available to this role, and NO BUILDER
     EXECUTION / no live traffic is the standing rule for batch K. A
     static read of the actual dispatch code is the next best evidence
     and is what every other repro tool in this directory already does
     for the generic-vs-bespoke shape.
  2. Reuse hover2_gate_parity_check.py -- rejected: that tool compares
     sibling ACTIONS of the literal shape `action === 'read'`/`'write'`
     on the SAME `if (resource === 'x' && action === 'y')` block; it
     cannot see a generic dict-keyed dispatch (`BLD_RESOURCES[resource]`)
     or a compound action condition (`action === 'wip' || action ===
     'release_retainage'`) at all, which is exactly why this gap was
     never flagged by it (named in the routing doc, not hidden).

Read-only against api/sd-data.js. Writes nothing.
"""
import argparse
import os
import re
import sys

GENERIC_READ = re.compile(
    r"if \(BLD_RESOURCES\[resource\] && action === 'read'\) \{(.*?)\n    \}",
    re.S)
BESPOKE_DRAWS = re.compile(
    r"if \(resource === 'bld_draws' && \(action === 'wip' \|\| "
    r"action === 'release_retainage'\)\) \{(.*?)\n    \}",
    re.S)
BLD_RESOURCES_DICT = re.compile(r"const BLD_RESOURCES = \{(.*?)\};", re.S)


def selftest():
    fx_vulnerable = """
    const BLD_RESOURCES = { bld_draws: 'draw_id', bld_jobs: 'job_id' };
    if (resource === 'bld_draws' && (action === 'wip' || action === 'release_retainage')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      if (!BLD_BID_MANAGEMENT_ROLES[session.role]) { return; }
    }
    if (BLD_RESOURCES[resource] && action === 'read') {
      const r = await fetch(x);
    }
    """
    fx_fixed = """
    const BLD_RESOURCES = { bld_draws: 'draw_id', bld_jobs: 'job_id' };
    if (resource === 'bld_draws' && (action === 'wip' || action === 'release_retainage')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      if (!BLD_BID_MANAGEMENT_ROLES[session.role]) { return; }
    }
    if (BLD_RESOURCES[resource] && action === 'read') {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      const r = await fetch(x);
    }
    """
    fx_no_bespoke_gate = """
    const BLD_RESOURCES = { bld_draws: 'draw_id', bld_jobs: 'job_id' };
    if (resource === 'bld_draws' && (action === 'wip' || action === 'release_retainage')) {
      const r = await fetch(x);
    }
    if (BLD_RESOURCES[resource] && action === 'read') {
      const r = await fetch(x);
    }
    """
    v1 = analyze(fx_vulnerable)
    v2 = analyze(fx_fixed)
    v3 = analyze(fx_no_bespoke_gate)
    assert v1['bypass'] is True, 'ablation: known-vulnerable fixture must flag bypass=True'
    assert v2['bypass'] is False, 'ablation: gated-generic fixture must flag bypass=False'
    assert v3['bypass'] is False, (
        'ablation: if the bespoke branch itself has no gate, this is not a '
        "BYPASS of a gate (there is none to bypass) -- a different finding, "
        'out of this tool\'s stated scope')
    print('SELFTEST PASS: vulnerable=bypass, fixed=no-bypass, '
          'ungated-bespoke=no-bypass (different question, correctly not flagged)')
    return 0


def analyze(src):
    out = {'bld_draws_in_dict': False, 'generic_read_has_session': None,
           'bespoke_has_session': None, 'bespoke_has_role': None, 'bypass': None}
    m = BLD_RESOURCES_DICT.search(src)
    if m and 'bld_draws' in m.group(1):
        out['bld_draws_in_dict'] = True
    gm = GENERIC_READ.search(src)
    if gm:
        out['generic_read_has_session'] = 'verifySessionToken' in gm.group(1)
    bm = BESPOKE_DRAWS.search(src)
    if bm:
        out['bespoke_has_session'] = 'verifySessionToken' in bm.group(1)
        out['bespoke_has_role'] = bool(re.search(r'[A-Z][A-Z0-9_]*_ROLES', bm.group(1)))
    if (out['bld_draws_in_dict'] and gm and bm
            and out['generic_read_has_session'] is False
            and out['bespoke_has_session'] is True):
        out['bypass'] = True
    elif gm and bm:
        out['bypass'] = False
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    path = os.path.join(args.repo, 'api', 'sd-data.js')
    if not os.path.isfile(path):
        print('COULD NOT RUN: %s not found' % path)
        sys.exit(2)
    src = open(path, encoding='utf-8').read()
    r = analyze(src)
    print('bld_draws present in BLD_RESOURCES dict: %s' % r['bld_draws_in_dict'])
    print("generic BLD_RESOURCES 'read' block has verifySessionToken: %s"
          % r['generic_read_has_session'])
    print("bespoke bld_draws wip/release_retainage block has verifySessionToken: %s, "
          "has a *_ROLES check: %s" % (r['bespoke_has_session'], r['bespoke_has_role']))
    if r['bypass'] is True:
        print('BYPASS CONFIRMED: the generic action=read path returns the same '
              "bld_draws.data column with NO session check, routing around the "
              "bespoke action=wip/release_retainage path's session+role gate on "
              'the identical table.')
        sys.exit(1)
    elif r['bypass'] is False:
        print('NO BYPASS: generic read path and bespoke path agree on gating.')
        sys.exit(0)
    else:
        print('COULD NOT RUN: one or both blocks not found by this pattern -- '
              'source shape has changed since this tool was written.')
        sys.exit(2)


if __name__ == '__main__':
    main()
