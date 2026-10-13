#!/usr/bin/env python
"""bld_draws_ownership_rule_probe.py -- BASELINE ONLY, for a NOT-YET-BUILT
rule: restrict bld_draws (SAIRNbuild progress-billing draw schedule) to
owner + upper management, denying every other real sairnbuild role.

THIS SCRIPT DOES NOT IMPLEMENT THE RULE. Hover role is read-only audit --
spec and baseline-test, never fix. See the companion spec:
.claude/skills/sairn-hover-auditor/references/bld-draws-ownership-rule-probe-spec.md

GOAL: report, by static read of the real source (not by trusting a comment
or a prior finding), what TODAY's dedicated bld_draws read/write gate
(api/sd-data.js, 'if (resource === bld_draws && (action===read||write))')
actually requires -- a session check, a role check, both, or neither -- and
derive the adversarial matrix's CURRENT-code column from that. The NEW-RULE
column is fixed policy (section 4 of the spec), not derived from source,
since the rule does not exist in source yet.

REAL ROLE VOCABULARY, confirmed against api/_lib/auth.js ROLES_BY_APP, not
invented: sairnbuild: ['owner', 'pm', 'office']. There is no 'supervisor' and
no 'employee' role in this app. 'Upper management' is read as the SAME tier
sd-data.js itself already names for this resource family --
BLD_BID_MANAGEMENT_ROLES = {owner, office} -- so 'pm' is the role the new
rule would deny. This is a judgment call (see spec section 2), stated here,
not silently assumed.

ALTERNATIVES CONSIDERED:
  1. Fire live HTTP requests with session tokens of each role -- rejected,
     same reason as bld_draws_bypass_repro.py: no demo credential for
     SAIRNbuild is available to this role, and no live server to call.
  2. Reuse bld_draws_bypass_repro.py directly -- rejected: that tool answers
     a DIFFERENT question (does a bespoke gated action have a same-resource
     ungated sibling). This probe answers whether the DEDICATED branch
     itself (which that tool already confirmed exists and is session-gated)
     also carries a ROLE check, which it does not yet, and what the
     cross-tenant control looks like independently of role.

Read-only against api/sd-data.js and api/_lib/auth.js. Writes nothing.
"""
import argparse
import os
import re
import sys

REAL_ROLES_SAIRNBUILD = ['owner', 'pm', 'office']
MANAGEMENT_ROLES = ['owner', 'office']  # BLD_BID_MANAGEMENT_ROLES, sd-data.js:5642
DENIED_UNDER_NEW_RULE = ['pm']

# Anchor-to-anchor extraction, not brace-counting: the dedicated branch
# contains its OWN nested `if (action === 'write') { ... }` block, whose
# closing brace is indented deeper than the outer branch's closing brace.
# A non-greedy "up to the first 4-space-indented close brace" regex (the
# shape bld_draws_bypass_repro.py uses for its OWN, shallower targets) would
# stop at the first nested close here and under-read the block. The dedicated
# branch's own next sibling in source is the generic BLD_RESOURCES loop,
# which is a stable, unique anchor immediately following it at HEAD -- so
# this probe reads "from the branch's own open brace to that anchor"
# instead of trying to balance braces with regex.
DEDICATED_RW_START = re.compile(
    r"if \(resource === 'bld_draws' && \(action === 'read' \|\| "
    r"action === 'write'\)\) \{")
NEXT_ANCHOR = re.compile(r"if \(BLD_RESOURCES\[resource\] && action === 'read'\) \{")

ROLE_GUARD = re.compile(r"[A-Z][A-Z0-9_]*_ROLES")
SESSION_CHECK = re.compile(r"verifySessionToken")

# auth.js's own token<->tenant binding -- the control for matrix row 5
# (cross-tenant). Looked for as a real statement, not inferred from a
# variable name alone: the specific comparison that makes a session token
# issued for one license_hash invalid when checked against another.
AUTH_BINDING_CHECK = re.compile(
    r"payload\.license_hash\s*!==\s*license_hash")
VERIFY_SESSION_TOKEN_FN = re.compile(
    r"function verifySessionToken\([^)]*\)\s*\{(.*?)\n[ \t]*\}", re.S)


def extract_dedicated_branch(src):
    m = DEDICATED_RW_START.search(src)
    if not m:
        return None
    n = NEXT_ANCHOR.search(src, m.end())
    if not n:
        return None
    return src[m.end():n.start()]


def extract_verify_session_token_body(auth_src):
    m = VERIFY_SESSION_TOKEN_FN.search(auth_src)
    if not m:
        return None
    return m.group(1)


def analyze(sd_src, auth_src):
    out = {
        'branch_found': False,
        'has_session_check': None,
        'has_role_check': None,
        'auth_fn_found': False,
        'has_tenant_binding_check': None,
    }
    branch = extract_dedicated_branch(sd_src)
    if branch is not None:
        out['branch_found'] = True
        out['has_session_check'] = bool(SESSION_CHECK.search(branch))
        out['has_role_check'] = bool(ROLE_GUARD.search(branch))
    vst_body = extract_verify_session_token_body(auth_src)
    if vst_body is not None:
        out['auth_fn_found'] = True
        out['has_tenant_binding_check'] = bool(AUTH_BINDING_CHECK.search(vst_body))
    return out


def derive_matrix(r):
    """Row-by-row CURRENT-code verdict, derived from what was actually
    found in source -- never hardcoded to 'allow' regardless of input."""
    rows = []
    if r['branch_found'] and r['has_session_check']:
        unauth_current = 'DENY (401 NO_SESSION)'
    elif r['branch_found']:
        unauth_current = 'ALLOW -- NO SESSION CHECK FOUND (unexpected at HEAD; re-verify)'
    else:
        unauth_current = 'COULD NOT DETERMINE (branch not found)'
    rows.append(('1. unauthenticated / no token', unauth_current, 'DENY (unchanged)'))

    for role in REAL_ROLES_SAIRNBUILD:
        if not r['branch_found']:
            current = 'COULD NOT DETERMINE (branch not found)'
        elif not r['has_session_check']:
            current = 'COULD NOT DETERMINE (branch has no session check at all)'
        elif r['has_role_check']:
            current = ('ALLOW' if role in MANAGEMENT_ROLES else 'DENY') + ' (role check present)'
        else:
            current = 'ALLOW (session-only gate, no role check -- every real role passes)'
        new_rule = 'ALLOW' if role not in DENIED_UNDER_NEW_RULE else 'DENY'
        rows.append(('%d. role=%s, same tenant' % (len(rows) + 1, role), current, new_rule))

    if r['auth_fn_found'] and r['has_tenant_binding_check']:
        cross_tenant_current = 'DENY (verifySessionToken: payload.license_hash !== license_hash)'
    elif r['auth_fn_found']:
        cross_tenant_current = 'ALLOW -- NO TENANT BINDING CHECK FOUND (unexpected at HEAD; re-verify)'
    else:
        cross_tenant_current = 'COULD NOT DETERMINE (verifySessionToken not found)'
    rows.append(('%d. cross-tenant: session for license_hash A used against license_hash B'
                  % (len(rows) + 1), cross_tenant_current, 'DENY (unchanged -- orthogonal control)'))

    rows.append(('%d. pm, draw tied to a job pm IS assigned to ("ownership")' % (len(rows) + 1),
                  'ALLOW (no ownership/job scoping exists on bld_draws or bld_jobs at all -- see spec section 3)',
                  'NOT YET DEFINABLE -- no schema to express "tied to" (flagged, not answered)'))
    rows.append(('%d. pm, draw tied to a job pm is NOT assigned to' % (len(rows) + 1),
                  'ALLOW (same reason)',
                  'NOT YET DEFINABLE (same reason)'))
    return rows


def selftest():
    fx_current_shape = """
    const BLD_RESOURCES = { bld_draws: 'draw_id' };
    if (resource === 'bld_draws' && (action === 'read' || action === 'write')) {
      const dSession = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      if (!dSession) {
        res.status(401).json({ error: { code: 'NO_SESSION' } });
        return;
      }
      if (action === 'write') {
        const RELEASE_OWNED = ['retainage_released'];
        if (dId) {
          if (pr.status === 404) {
            RELEASE_OWNED.forEach((k) => { delete payload[k]; });
          } else if (!pr.ok) {
            return;
          } else {
            RELEASE_OWNED.forEach((k) => {});
          }
        } else {
          RELEASE_OWNED.forEach((k) => {});
        }
      }
    }
    if (BLD_RESOURCES[resource] && action === 'read') {
      const r = await fetch(x);
    }
    """
    fx_role_gated_future = """
    const BLD_RESOURCES = { bld_draws: 'draw_id' };
    const BLD_BID_MANAGEMENT_ROLES = roleSet({ owner: true, office: true });
    if (resource === 'bld_draws' && (action === 'read' || action === 'write')) {
      const dSession = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
      if (!dSession) { return; }
      if (!BLD_BID_MANAGEMENT_ROLES[dSession.role]) { return; }
      if (action === 'write') {
        if (dId) {
          if (pr.status === 404) {
          } else if (!pr.ok) {
          } else {
          }
        } else {
        }
      }
    }
    if (BLD_RESOURCES[resource] && action === 'read') {
      const r = await fetch(x);
    }
    """
    fx_auth_with_binding = """
    function verifySessionToken(token, license_hash, expectedApp) {
      const payload = verifySignedPayload(token);
      if (!payload || !payload.app) return null;
      if (expectedApp && payload.app !== expectedApp) return null;
      if (!license_hash || payload.license_hash !== license_hash) return null;
      return { employee_id: payload.employee_id, role: payload.role, app: payload.app };
    }
    """
    fx_auth_no_binding = """
    function verifySessionToken(token, license_hash, expectedApp) {
      const payload = verifySignedPayload(token);
      if (!payload || !payload.app) return null;
      return { employee_id: payload.employee_id, role: payload.role, app: payload.app };
    }
    """

    r1 = analyze(fx_current_shape, fx_auth_with_binding)
    assert r1['branch_found'] is True
    assert r1['has_session_check'] is True
    assert r1['has_role_check'] is False, (
        'current-shape fixture (mirrors HEAD as read 2026-10-13) must show '
        'NO role check -- this is the gap the new rule closes')
    assert r1['has_tenant_binding_check'] is True

    r2 = analyze(fx_role_gated_future, fx_auth_with_binding)
    assert r2['has_role_check'] is True, (
        'ablation: a fixture WITH BLD_BID_MANAGEMENT_ROLES inside the '
        'dedicated branch must be detected as having a role check -- '
        'proves this is a real detector, not a hardcoded False')

    r3 = analyze(fx_current_shape, fx_auth_no_binding)
    assert r3['has_tenant_binding_check'] is False, (
        'ablation: an auth fixture with the binding line REMOVED must be '
        'detected as missing it -- proves the tenant-binding check is a '
        'real detector, not a hardcoded True')

    m1 = derive_matrix(r1)
    pm_row = [row for row in m1 if 'role=pm' in row[0]][0]
    assert 'ALLOW' in pm_row[1], 'current-shape: pm must be ALLOW today (the gap)'
    assert pm_row[2] == 'DENY', 'new rule: pm must be DENY'
    office_row = [row for row in m1 if 'role=office' in row[0]][0]
    assert office_row[2] == 'ALLOW', 'new rule: office must remain ALLOW'
    owner_row = [row for row in m1 if 'role=owner' in row[0]][0]
    assert owner_row[2] == 'ALLOW', 'new rule: owner must remain ALLOW'

    m2 = derive_matrix(r2)
    pm_row2 = [row for row in m2 if 'role=pm' in row[0]][0]
    assert 'DENY' in pm_row2[1], (
        'if the role check were already present, pm should already show '
        'DENY in the CURRENT column -- proves derive_matrix reads the '
        'analyze() result rather than a fixed assumption')

    print('SELFTEST PASS: current-shape (session-only, no role check) -> '
          'pm=ALLOW-today/DENY-new, office/owner=ALLOW both; role-check '
          'ablation detected; tenant-binding-removed ablation detected; '
          'hypothetical future-gated fixture correctly flips pm to DENY-today')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())

    sd_path = os.path.join(args.repo, 'api', 'sd-data.js')
    auth_path = os.path.join(args.repo, 'api', '_lib', 'auth.js')
    missing = [p for p in (sd_path, auth_path) if not os.path.isfile(p)]
    if missing:
        print('COULD NOT RUN: missing %s' % ', '.join(missing))
        sys.exit(2)

    sd_src = open(sd_path, encoding='utf-8').read()
    auth_src = open(auth_path, encoding='utf-8').read()
    r = analyze(sd_src, auth_src)

    print('=== bld_draws ownership-rule probe -- BASELINE ONLY, rule NOT built ===')
    print('Real sairnbuild roles (api/_lib/auth.js ROLES_BY_APP): %s'
          % REAL_ROLES_SAIRNBUILD)
    print('No "supervisor" or "employee" role exists in this app.')
    print('"Upper management" read as BLD_BID_MANAGEMENT_ROLES = %s (existing '
          'precedent at sd-data.js:5642); pm is the role the new rule denies.'
          % MANAGEMENT_ROLES)
    print()
    print('Dedicated bld_draws read/write branch found: %s' % r['branch_found'])
    print('  has verifySessionToken call: %s' % r['has_session_check'])
    print('  has a *_ROLES role-guard: %s' % r['has_role_check'])
    print('verifySessionToken() found in auth.js: %s' % r['auth_fn_found'])
    print('  has payload.license_hash !== license_hash tenant-binding check: %s'
          % r['has_tenant_binding_check'])
    print()
    if not r['branch_found'] or not r['auth_fn_found']:
        print('COULD NOT RUN cleanly: one or both anchors not found -- source '
              'shape has changed since this probe was written (2026-10-13). '
              'Fix the anchors before trusting the matrix below.')
        sys.exit(2)

    print('--- Adversarial matrix: CURRENT (HEAD) vs NEW RULE (not yet built) ---')
    for name, current, new_rule in derive_matrix(r):
        print('%s' % name)
        print('    current : %s' % current)
        print('    new rule: %s' % new_rule)
    print()
    print('Full narrative: .claude/skills/sairn-hover-auditor/references/'
          'bld-draws-ownership-rule-probe-spec.md')
    sys.exit(0)


if __name__ == '__main__':
    main()
