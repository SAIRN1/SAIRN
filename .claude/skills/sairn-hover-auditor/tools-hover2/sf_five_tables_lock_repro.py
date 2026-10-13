#!/usr/bin/env python
"""sf_five_tables_lock_repro.py -- reproducing artifact for Michael's batch
b15 decision on the five SAIRNfreedom resources the b11/b12 routing doc
named but did not act on: sf_district_imports, sf_events, sf_permit_flags,
sf_products, sf_vehicles (api/sd-data.js's own comment at :1125-1127: "FIVE
MORE ARE TIER A AND STAY UNGATED, AND THAT IS A DECISION I DID NOT MAKE
RATHER THAN AN OVERSIGHT"). That decision is reversed this batch: lock all
five, and build a PER-RESOURCE role matrix (not a single flat gate) -- same
shape as sf_officers (b14, FIXED) and bld_draws's new ownership
requirement, generalized to five resources in one tool rather than five
near-identical one-off scripts.

TWO QUESTIONS, kept separate because they land on different timelines:

  1. SESSION-GATE BASELINE (today, expected REPRODUCES on all 5): is each
     resource reachable with NO session at all? Same two-part test as
     sf_officers_provisioning_bypass_repro.py, generalized --
       (a) resource NOT a key in SD_SESSION_GATED, AND
       (b) the generic SF_RESOURCES write block stores the caller's
           payload verbatim with no role/capability check in between.
     This is the thing hank's lock closes. REPRODUCES on all 5 today.

  2. ROLE MATRIX (forward-looking, expected ABSENT on all 5 today): once
     locked, does EACH resource also carry its OWN role requirement
     (a per-resource entry, not one shared constant covering all five
     identically -- "a role matrix," not "a role")? Modeled as a dict
     literal named SF_FIVE_TABLE_ROLES keyed by resource name, each value
     a roleSet(...) -- the same shape SAIRNvet's per-resource grouping
     uses, chosen so a future tool reading this one does not need a third
     shape invented for the same question. ABSENT on all 5 today --
     confirmed via `git log -S"SF_FIVE_TABLE_ROLES"` and `-S"role matrix"`
     against api/sd-data.js, both empty, before writing this.

Exit code reflects question 1 only (1 REPRODUCES, 0 FIXED, 2 COULD NOT
RUN) -- same contract as every other repro in this directory. Question 2
is reported alongside, never folded into the exit code, because it did
not exist as a claim to verify before this batch and conflating "the
bypass closed" with "the matrix landed" would make a partial fix read as
either fully done or not done at all.

Usage:
  python sf_five_tables_lock_repro.py --all [--repo PATH]
  python sf_five_tables_lock_repro.py --resource NAME
  python sf_five_tables_lock_repro.py --selftest
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

RESOURCES = (
    'sf_district_imports', 'sf_events', 'sf_permit_flags',
    'sf_products', 'sf_vehicles',
)

# batch b18: the ORIGINAL ROLE_MATRIX_DICT pattern below (an inline
# `SF_FIVE_TABLE_ROLES = {...}` literal inside api/sd-data.js) was this
# tool's own GUESS at the shape hank's eventual fix would take, written
# before that fix existed. The REAL fix (commit d7773533) built
# something stronger and different: a single `SF_ROLE_MATRIX` covering
# all 36 sf_ resources, in its OWN file (api/_lib/sf-roles.js, an
# `Object.freeze(Object.assign(Object.create(null), {...}))` literal,
# not a bare `{...}` and not `roleSet()`), wired into api/sd-data.js via
# `require('./_lib/sf-roles')` and a real `sfRoles.decide(...)` call
# that 403s on DENY. Checking only the old guessed shape would have
# reported FALSE for all 5 resources against a fix that is actually
# live -- found live this batch, not assumed. Kept both patterns: the
# old one for the now-false hypothesis (reported honestly if it somehow
# fires), the new one for what hank actually built.
ROLE_MATRIX_DICT = re.compile(r'SF_FIVE_TABLE_ROLES\s*=\s*\{(.*?)\n\s*\};?', re.S)
SF_ROLE_MATRIX_DICT = re.compile(
    r'const SF_ROLE_MATRIX = Object\.freeze\(Object\.assign\('
    r'Object\.create\(null\), \{(.*?)\n\}\)\);', re.S)


def read_src(repo):
    path = os.path.join(repo, 'api', 'sd-data.js')
    if not os.path.isfile(path):
        return None, 'COULD NOT RUN: %s not found' % path
    return open(path, encoding='utf-8').read(), None


def read_sf_roles_src(repo):
    path = os.path.join(repo, 'api', '_lib', 'sf-roles.js')
    if not os.path.isfile(path):
        return None
    return open(path, encoding='utf-8').read()


def session_gate_check(resource, src):
    """-> (reproduces: bool, detail: str) or raises ValueError (COULD NOT
    RUN). Same two-part test as sf_officers_provisioning_bypass_repro.py,
    generalized to any one of the five resource names."""
    gated_m = re.search(r"const SD_SESSION_GATED = \{(.*?)\n    \};", src, re.S)
    if not gated_m:
        raise ValueError('SD_SESSION_GATED object literal not found')
    gated = bool(re.search(r"'%s'\s*:\s*\[" % re.escape(resource), gated_m.group(1)))

    write_m = re.search(
        r"if \(SF_RESOURCES\[resource\] && action === 'write'\) \{(.*?)\n    \}",
        src, re.S)
    if not write_m:
        raise ValueError('generic SF_RESOURCES write block not found')
    write_body = write_m.group(1)
    stores_whole_payload = bool(re.search(r"data:\s*payload\b", write_body))
    has_role_check = bool(re.search(
        r"ROLES|role\s*!==|capability\s*!==|PROVISIONING_CAPS|session\.role",
        write_body))

    reproduces = (not gated) and stores_whole_payload and (not has_role_check)
    detail = ("%s in SD_SESSION_GATED: %s; generic write stores "
              "data:payload verbatim: %s; role/capability check present "
              "in that write block: %s"
              % (resource, gated, stores_whole_payload, has_role_check))
    return reproduces, detail


def role_matrix_check(resource, src):
    """-> (present: bool, allowed_roles: dict|None), the OLD guessed
    shape only (inline SF_FIVE_TABLE_ROLES in api/sd-data.js). Kept as
    a named, separate check rather than deleted -- see sf_role_matrix_
    check() below for what hank actually built."""
    m = ROLE_MATRIX_DICT.search(src)
    if not m:
        return False, None
    entry_m = re.search(
        r"'%s'\s*:\s*roleSet\(\{([^}]*)\}\)" % re.escape(resource), m.group(1))
    if not entry_m:
        return False, None
    allowed = {}
    for rm in re.finditer(r"(\w+)\s*:\s*(true|false)", entry_m.group(1)):
        allowed[rm.group(1)] = (rm.group(2) == 'true')
    return True, allowed


def sf_role_matrix_check(resource, sd_data_src, sf_roles_src):
    """-> (present: bool, wired: bool|None). `present`: does this
    resource have its own entry in api/_lib/sf-roles.js's
    SF_ROLE_MATRIX? `wired`: does api/sd-data.js actually require that
    module and call sfRoles.decide(...) with a real 403 on DENY, or
    does the table exist but nothing calls it (declared-not-enforced
    would be a different, weaker finding than either present-and-wired
    or absent entirely)."""
    if sf_roles_src is None:
        return False, None
    m = SF_ROLE_MATRIX_DICT.search(sf_roles_src)
    if not m:
        return False, None
    present = bool(re.search(
        r"\b%s\s*:\s*\{" % re.escape(resource), m.group(1)))
    if not present:
        return False, None
    required = bool(re.search(
        r"require\(['\"]\./_lib/sf-roles['\"]\)", sd_data_src))
    decide_enforced = bool(re.search(
        r"sfRoles\.decide\([^)]*\)\s*===\s*sfRoles\.DENY", sd_data_src))
    return True, (required and decide_enforced)


def check_one(resource, src, sf_roles_src=None):
    reproduces, gate_detail = session_gate_check(resource, src)
    matrix_present, allowed_roles = role_matrix_check(resource, src)
    sf_matrix_present, sf_matrix_wired = sf_role_matrix_check(
        resource, src, sf_roles_src)
    return {
        'resource': resource,
        'reproduces': reproduces,
        'gate_detail': gate_detail,
        'role_matrix_present': matrix_present,
        'allowed_roles': allowed_roles,
        'sf_role_matrix_present': sf_matrix_present,
        'sf_role_matrix_wired': sf_matrix_wired,
    }


def selftest():
    bad_src = """
    const SD_SESSION_GATED = {
      'sf_accounts': ['read', 'write'],
    };
    if (SF_RESOURCES[resource] && action === 'write') {
      const idCol = SF_RESOURCES[resource];
      const r = await fetch(rest(resource), { body: JSON.stringify({ data: payload }) });
    }
"""
    fixed_no_matrix_src = """
    const SD_SESSION_GATED = {
      'sf_district_imports': ['read', 'write'],
    };
    if (SF_RESOURCES[resource] && action === 'write') {
      const idCol = SF_RESOURCES[resource];
      const r = await fetch(rest(resource), { body: JSON.stringify({ data: payload }) });
    }
"""
    fixed_with_matrix_src = """
    const SD_SESSION_GATED = {
      'sf_district_imports': ['read', 'write'],
    };
    const SF_FIVE_TABLE_ROLES = {
      'sf_district_imports': roleSet({ owner: true, office: true }),
      'sf_vehicles': roleSet({ owner: true }),
    };
    if (SF_RESOURCES[resource] && action === 'write') {
      const idCol = SF_RESOURCES[resource];
      if (resource === 'sf_district_imports' && !SF_FIVE_TABLE_ROLES['sf_district_imports'][session.role]) { return; }
      const r = await fetch(rest(resource), { body: JSON.stringify({ data: payload }) });
    }
"""
    r1 = check_one('sf_district_imports', bad_src)
    assert r1['reproduces'] is True, 'fixture A: ungated+whole-payload must REPRODUCE: %r' % r1
    assert r1['role_matrix_present'] is False, 'fixture A: no matrix declared at all'

    r2 = check_one('sf_district_imports', fixed_no_matrix_src)
    assert r2['reproduces'] is False, 'fixture B: gated must NOT reproduce: %r' % r2
    assert r2['role_matrix_present'] is False, (
        'fixture B: session-gated but NO role matrix -- the lock landed, '
        'the matrix did not; these two must be distinguishable')

    r3 = check_one('sf_district_imports', fixed_with_matrix_src)
    assert r3['reproduces'] is False
    assert r3['role_matrix_present'] is True
    assert r3['allowed_roles'] == {'owner': True, 'office': True}

    r4 = check_one('sf_vehicles', fixed_with_matrix_src)
    assert r4['role_matrix_present'] is True
    assert r4['allowed_roles'] == {'owner': True}, (
        'fixture C: PER-RESOURCE matrix -- sf_vehicles must get its OWN '
        'entry (owner-only), not sf_district_imports\' broader one, '
        'proving this is a matrix and not one shared constant read twice')

    r5 = check_one('sf_products', fixed_with_matrix_src)
    assert r5['role_matrix_present'] is False, (
        'fixture C: a resource with NO entry in the matrix dict must '
        'report absent, not silently inherit another resource\'s roles')

    try:
        session_gate_check('sf_district_imports', 'no relevant literals here')
        assert False, 'fixture D (absent shape) should raise ValueError'
    except ValueError:
        pass

    # ── REAL-SHAPE FIXTURES, batch b18 ──────────────────────────────────
    # hank's actual fix (commit d7773533) did not use SF_FIVE_TABLE_ROLES
    # at all -- it built ONE matrix, SF_ROLE_MATRIX, covering all 36 sf_
    # resources, in its own file (api/_lib/sf-roles.js), wired into
    # api/sd-data.js via require + a real sfRoles.decide(...) === DENY
    # check. The first run of this tool against the real fix reported
    # role_matrix_present=False for all 5 target resources -- a FALSE
    # NEGATIVE, because the tool only ever knew to look for its own
    # guessed shape. sf_role_matrix_check() now reads the real file.
    real_sf_roles_src = """
const SF_ROLE_MATRIX = Object.freeze(Object.assign(Object.create(null), {
  sf_district_imports: { 'post.govern': 'rw', why: 'x' },
  sf_events: { 'post.govern': 'rw', why: 'x' },
}));
"""
    sd_data_wired_src = """
    const sfRoles = require('./_lib/sf-roles');
    const SD_SESSION_GATED = {
      'sf_district_imports': ['read', 'write'],
    };
    if (sfRoles.decide(resource, gateSession.role, action) === sfRoles.DENY) { return; }
    if (SF_RESOURCES[resource] && action === 'write') {
      const idCol = SF_RESOURCES[resource];
      const r = await fetch(rest(resource), { body: JSON.stringify({ data: payload }) });
    }
"""
    sd_data_unwired_src = """
    const SD_SESSION_GATED = {
      'sf_district_imports': ['read', 'write'],
    };
    // sfRoles exists but nothing here requires or calls it
    if (SF_RESOURCES[resource] && action === 'write') {
      const idCol = SF_RESOURCES[resource];
      const r = await fetch(rest(resource), { body: JSON.stringify({ data: payload }) });
    }
"""

    r6 = check_one('sf_district_imports', sd_data_wired_src, real_sf_roles_src)
    assert r6['sf_role_matrix_present'] is True, (
        'real-shape fixture: sf_district_imports has a real SF_ROLE_MATRIX '
        'entry and must be detected -- this is the exact false negative '
        'b18 found live')
    assert r6['sf_role_matrix_wired'] is True, (
        'real-shape fixture: require + a real sfRoles.decide(...) === '
        'DENY check are both present -- must report wired=True')

    r7 = check_one('sf_products', sd_data_wired_src, real_sf_roles_src)
    assert r7['sf_role_matrix_present'] is False, (
        'real-shape fixture: sf_products has NO entry in this fixture\'s '
        'matrix -- must report absent, not inherit a sibling\'s presence')

    r8 = check_one('sf_district_imports', sd_data_unwired_src, real_sf_roles_src)
    assert r8['sf_role_matrix_present'] is True
    assert r8['sf_role_matrix_wired'] is False, (
        'real-shape fixture: the matrix table exists but nothing in '
        'api/sd-data.js requires it or calls decide() -- declared-not-'
        'enforced must report wired=False, a WEAKER state than either '
        'present-and-wired or absent, and must not be conflated with '
        'either')

    print('ALL SELFTEST CASES PASS (8 arms)')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=os.path.abspath(
        os.path.join(HERE, '..', '..', '..', '..')))
    ap.add_argument('--resource')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    targets = [args.resource] if args.resource else (list(RESOURCES) if args.all else [])
    if not targets:
        print('usage: --resource NAME | --all | --selftest')
        return 2

    src, err = read_src(args.repo)
    if err:
        print(err)
        return 2
    sf_roles_src = read_sf_roles_src(args.repo)
    if sf_roles_src is None:
        print('NOTE: api/_lib/sf-roles.js not found at this --repo -- the '
              'real role-matrix check (sf_role_matrix_present/_wired) will '
              'report False/None for everything below; the session-gate '
              'verdict is unaffected.')

    any_reproduces = False
    for resource in targets:
        if resource not in RESOURCES:
            print('%-24s COULD_NOT_RUN  not one of the 5 named resources' % resource)
            any_reproduces = True
            continue
        try:
            r = check_one(resource, src, sf_roles_src)
        except ValueError as e:
            print('%-24s COULD_NOT_RUN  %s' % (resource, e))
            any_reproduces = True
            continue
        verdict = 'REPRODUCES' if r['reproduces'] else 'FIXED'
        print('%-24s %-10s %s' % (resource, verdict, r['gate_detail']))
        print('%-24s %-10s role matrix present: %s, allowed roles: %s'
              % (resource, 'MATRIX(old guess)', r['role_matrix_present'], r['allowed_roles']))
        print('%-24s %-10s SF_ROLE_MATRIX present: %s, wired+enforced: %s'
              % (resource, 'MATRIX(real)', r['sf_role_matrix_present'], r['sf_role_matrix_wired']))
        if r['reproduces']:
            any_reproduces = True
    return 1 if any_reproduces else 0


if __name__ == '__main__':
    sys.exit(main())
