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
# FOUND batch b13: a dedicated bld_draws-specific read/write branch, added
# 2026-10-11 (commit 86189e37) PRECEDING the generic BLD_RESOURCES loop,
# intercepting bld_draws' own read AND write before either ever reaches the
# generic (deliberately ungated) path. The tool's own first-written logic
# had no way to see this -- it only checked whether the GENERIC block itself
# gained a session check, and reported BYPASS CONFIRMED for several batches
# after the real fix had already landed via a DIFFERENT branch entirely.
# Found by re-running this tool against HEAD and reading why a repro the fix
# commit's own message claims closed still printed BYPASS CONFIRMED, rather
# than trusting the stale verdict.
DEDICATED_DRAWS_RW = re.compile(
    r"if \(resource === 'bld_draws' && \(action === 'read' \|\| "
    r"action === 'write'\)\) \{(.*?)\n    \}",
    re.S)
ROLE_SET_LITERAL = re.compile(r'roleSet\(\{([^}]*)\}\)')

# ── MICHAEL'S DECISION, batch b15: upper management/owner only, NOT
# supervisors, access assigned by ownership ────────────────────────────
# The dedicated read/write branch found in b13 (DEDICATED_DRAWS_RW above)
# closed the UNAUTHENTICATED bypass -- it requires A session -- but never
# checked WHICH role that session holds. sairnbuild's role vocabulary is
# owner/pm/office (api/_lib/auth.js:203); 'pm' is the on-site project
# manager, the closest thing this app has to "supervisor." Right now any
# of the three can read AND write bld_draws through this branch with no
# role gate at all -- confirmed live below, not assumed from the comment.
# Michael's decision narrows this to owner only (not pm, and -- per "owner
# only," not plain office staff either) PLUS a per-record ownership
# check, neither of which hank has landed yet (no "supervisor" or
# ownership string found anywhere in api/sd-data.js as of this batch).
# These two checks are forward-looking: they are EXPECTED to fail today
# and are here so the next run against hank's real commit needs no new
# code, only a re-run.


def _role_set(src, name):
    """{'owner': True, ...} parsed from `const NAME = roleSet({...})`, or
    None if NAME is not declared in src at all."""
    m = re.search(r'const %s = roleSet\(\{([^}]*)\}\)' % re.escape(name), src)
    if not m:
        return None
    out = {}
    for rm in re.finditer(r"(\w+)\s*:\s*(true|false)", m.group(1)):
        out[rm.group(1)] = (rm.group(2) == 'true')
    return out


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
    # THE REAL batch-b13 REGRESSION SHAPE: a dedicated bld_draws read/write
    # branch, gated, sitting BEFORE the still-ungated generic BLD_RESOURCES
    # loop. Commit 86189e37 closed the bypass this exact way and this
    # tool's prior version reported BYPASS CONFIRMED against it regardless,
    # because it never looked for this branch at all.
    fx_dedicated_branch_fix = """
    const BLD_RESOURCES = { bld_draws: 'draw_id', bld_jobs: 'job_id' };
    if (resource === 'bld_draws' && (action === 'wip' || action === 'release_retainage')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      if (!BLD_BID_MANAGEMENT_ROLES[session.role]) { return; }
    }
    if (resource === 'bld_draws' && (action === 'read' || action === 'write')) {
      const dSession = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      if (!dSession) { return; }
    }
    if (BLD_RESOURCES[resource] && action === 'read') {
      const r = await fetch(x);
    }
    """
    # NEGATIVE CONTROL for the same shape: the dedicated branch EXISTS but
    # has no session check of its own -- must still report bypass=True,
    # because a present-but-ungated dedicated branch closes nothing.
    fx_dedicated_branch_ungated = """
    const BLD_RESOURCES = { bld_draws: 'draw_id', bld_jobs: 'job_id' };
    if (resource === 'bld_draws' && (action === 'wip' || action === 'release_retainage')) {
      const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      if (!BLD_BID_MANAGEMENT_ROLES[session.role]) { return; }
    }
    if (resource === 'bld_draws' && (action === 'read' || action === 'write')) {
      const r = await fetch(x);
    }
    if (BLD_RESOURCES[resource] && action === 'read') {
      const r = await fetch(x);
    }
    """

    v1 = analyze(fx_vulnerable)
    v2 = analyze(fx_fixed)
    v3 = analyze(fx_no_bespoke_gate)
    v4 = analyze(fx_dedicated_branch_fix)
    v5 = analyze(fx_dedicated_branch_ungated)
    assert v1['bypass'] is True, 'ablation: known-vulnerable fixture must flag bypass=True'
    assert v2['bypass'] is False, 'ablation: gated-generic fixture must flag bypass=False'
    assert v3['bypass'] is False, (
        'ablation: if the bespoke branch itself has no gate, this is not a '
        "BYPASS of a gate (there is none to bypass) -- a different finding, "
        'out of this tool\'s stated scope')
    assert v4['bypass'] is False, (
        'REGRESSION, batch b13: a dedicated, gated bld_draws read/write '
        'branch ahead of the generic loop must report NO BYPASS')
    assert v5['bypass'] is True, (
        'control pair for the above: the dedicated branch present but '
        'UNGATED must still report BYPASS CONFIRMED, not be mistaken for '
        'a real fix merely because the branch exists')
    print('SELFTEST PASS: vulnerable=bypass, fixed=no-bypass, '
          'ungated-bespoke=no-bypass (different question, correctly not '
          'flagged), dedicated-gated-branch=no-bypass, '
          'dedicated-ungated-branch=bypass (control pair)')

    # ── MUTATION PROOF, batch b15, Michael's decision ──────────────────
    # No real post-fix commit exists yet (hank's change has not landed --
    # confirmed via `git log -S"supervisor"` and `-S"ownership"` against
    # api/sd-data.js, both empty, before writing this). The PRE-FIX
    # fixture below is the REAL current shape of the dedicated read/write
    # branch (session required, no role check at all) -- not a stand-in,
    # copied from the live analyze() read above. The POST-FIX fixture is
    # SYNTHETIC: the target shape stated in the decision (owner-only role
    # gate + a per-record ownership check), built so this tool's own
    # assertions are proven to fire on the real current gap and fall
    # silent on the shape hank's change is expected to produce, without
    # waiting for that commit to exist first.
    fx_pre_fix_real_shape = """
    if (resource === 'bld_draws' && (action === 'read' || action === 'write')) {
      const dSession = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      if (!dSession) { return; }
      const r = await fetch(x);
    }
    """
    fx_post_fix_synthetic = """
    if (resource === 'bld_draws' && (action === 'read' || action === 'write')) {
      const dSession = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      if (!dSession) { return; }
      if (!BLD_DRAW_OWNER_ONLY_ROLES[dSession.role]) { return; }
      if (dSession.role !== 'owner' && draw.owner_id !== dSession.employee_id) { return; }
      const r = await fetch(x);
    }
    const BLD_DRAW_OWNER_ONLY_ROLES = roleSet({ owner: true });
    """
    mp1 = analyze(fx_pre_fix_real_shape)
    mp2 = analyze(fx_post_fix_synthetic)
    assert mp1['dedicated_rw_role_check_present'] is False, (
        'mutation proof, pre-fix: today\'s real dedicated branch shape has '
        'NO role check -- must fire (be False), not be mistaken for fixed')
    assert mp1['supervisor_pm_denied'] is False, (
        'mutation proof, pre-fix: supervisor (pm) must be RED (not denied) '
        'on the real current shape')
    assert mp1['owner_allowed'] is True, (
        'mutation proof, pre-fix: owner must still be allowed today (any '
        'session passes) -- this was never the gap')
    assert mp1['ownership_check_present'] is False, (
        'mutation proof, pre-fix: no ownership check exists today')
    assert mp2['dedicated_rw_role_check_present'] is True, (
        'mutation proof, post-fix: the synthetic fixed shape must register '
        'a role check -- if this fires False the detector, not the fix, is '
        'broken')
    assert mp2['supervisor_pm_denied'] is True, (
        'mutation proof, post-fix: supervisor (pm) must be GREEN (denied) '
        'once the owner-only role gate lands')
    assert mp2['owner_allowed'] is True, (
        'mutation proof, post-fix: owner must remain allowed after the fix')
    assert mp2['ownership_check_present'] is True, (
        'mutation proof, post-fix: the per-record ownership check must be '
        'detected once present')
    print('MUTATION PROOF PASS: pre-fix (real current shape) fires on '
          'supervisor_pm_denied=False/ownership_check_present=False; '
          'post-fix (synthetic target shape) is silent on both -- '
          'detector proven to distinguish the two before hank\'s real '
          'commit exists')
    return 0


def analyze(src):
    out = {'bld_draws_in_dict': False, 'generic_read_has_session': None,
           'bespoke_has_session': None, 'bespoke_has_role': None,
           'dedicated_rw_present': False, 'dedicated_rw_has_session': None,
           'bypass': None,
           # batch b15, Michael's decision -- see module docstring above
           # ROLE_SET_LITERAL for why these are forward-looking:
           'dedicated_rw_role_check_present': None,
           'dedicated_rw_allowed_roles': None,
           'supervisor_pm_denied': None, 'owner_allowed': None,
           'ownership_check_present': None}
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
    dm = DEDICATED_DRAWS_RW.search(src)
    if dm:
        out['dedicated_rw_present'] = True
        body = dm.group(1)
        out['dedicated_rw_has_session'] = 'verifySessionToken' in body
        role_var = re.search(r'([A-Z][A-Z0-9_]*_ROLES)\s*\[', body)
        out['dedicated_rw_role_check_present'] = bool(role_var)
        if role_var:
            allowed = _role_set(src, role_var.group(1))
            out['dedicated_rw_allowed_roles'] = allowed
            if allowed is not None:
                out['supervisor_pm_denied'] = not allowed.get('pm', False)
                out['owner_allowed'] = allowed.get('owner', False)
        else:
            # NO role check on this branch at all -- every sairnbuild role
            # that can authenticate, including 'pm', reads and writes
            # bld_draws today. 'pm' is therefore NOT denied (False), and
            # 'owner' is allowed only because EVERY role is (not because
            # owner was singled out) -- both facts worth keeping distinct
            # from "owner allowed because owner is the only role granted."
            out['supervisor_pm_denied'] = False
            out['owner_allowed'] = out['dedicated_rw_has_session']
        out['ownership_check_present'] = bool(re.search(
            r'owner_id|assigned_to|ownership', body, re.I))
    if not (out['bld_draws_in_dict'] and gm and bm):
        return out
    # A dedicated, earlier-in-source bld_draws read/write branch that itself
    # requires a session CLOSES the bypass regardless of what the generic
    # BLD_RESOURCES loop still does for the other 29 resources -- a JS
    # dispatch chain of sequential `if (...) { ...; return; }` blocks means
    # the dedicated branch runs first and the generic one is never reached
    # for this resource at all. Checked before the generic-block comparison
    # so a real fix via this route is never reported as still-open.
    if out['dedicated_rw_present'] and out['dedicated_rw_has_session'] is True:
        out['bypass'] = False
        return out
    if (out['generic_read_has_session'] is False
            and out['bespoke_has_session'] is True):
        out['bypass'] = True
    else:
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
    print("dedicated bld_draws read/write branch present: %s, has verifySessionToken: %s"
          % (r['dedicated_rw_present'], r['dedicated_rw_has_session']))
    print('-- ROLE GRANULARITY (Michael\'s decision, batch b15): owner/upper-'
          'management only, not supervisors (pm), access assigned by '
          'ownership. This is a SEPARATE question from the bypass verdict '
          'below and does not change its exit code. --')
    print('  dedicated_rw role check present: %s (allowed roles: %s)'
          % (r['dedicated_rw_role_check_present'], r['dedicated_rw_allowed_roles']))
    print('  supervisor (pm) DENIED: %s -- %s'
          % (r['supervisor_pm_denied'],
             'GREEN' if r['supervisor_pm_denied'] else
             'RED, expected until hank\'s change lands'))
    print('  owner ALLOWED: %s -- %s'
          % (r['owner_allowed'],
             'GREEN' if r['owner_allowed'] else 'RED'))
    print('  per-record ownership check present: %s -- %s'
          % (r['ownership_check_present'],
             'GREEN' if r['ownership_check_present'] else
             'RED, expected until hank\'s change lands (not built yet)'))
    if r['bypass'] is True:
        print('BYPASS CONFIRMED: the generic action=read path returns the same '
              "bld_draws.data column with NO session check, routing around the "
              "bespoke action=wip/release_retainage path's session+role gate on "
              'the identical table.')
        sys.exit(1)
    elif r['bypass'] is False:
        if r['dedicated_rw_present'] and r['dedicated_rw_has_session']:
            print('NO BYPASS: a dedicated, gated bld_draws read/write branch '
                  'intercepts this resource before the generic (deliberately '
                  'ungated) BLD_RESOURCES loop is ever reached.')
        else:
            print('NO BYPASS: generic read path and bespoke path agree on gating.')
        sys.exit(0)
    else:
        print('COULD NOT RUN: one or both blocks not found by this pattern -- '
              'source shape has changed since this tool was written.')
        sys.exit(2)


if __name__ == '__main__':
    main()
