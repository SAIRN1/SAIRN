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

ROLE_MATRIX_DICT = re.compile(r'SF_FIVE_TABLE_ROLES\s*=\s*\{(.*?)\n\s*\};?', re.S)


def read_src(repo):
    path = os.path.join(repo, 'api', 'sd-data.js')
    if not os.path.isfile(path):
        return None, 'COULD NOT RUN: %s not found' % path
    return open(path, encoding='utf-8').read(), None


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
    """-> (present: bool, allowed_roles: dict|None). Forward-looking --
    expected (False, None) on every resource until hank's matrix lands."""
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


def check_one(resource, src):
    reproduces, gate_detail = session_gate_check(resource, src)
    matrix_present, allowed_roles = role_matrix_check(resource, src)
    return {
        'resource': resource,
        'reproduces': reproduces,
        'gate_detail': gate_detail,
        'role_matrix_present': matrix_present,
        'allowed_roles': allowed_roles,
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

    print('ALL SELFTEST CASES PASS (5 arms)')
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

    any_reproduces = False
    for resource in targets:
        if resource not in RESOURCES:
            print('%-24s COULD_NOT_RUN  not one of the 5 named resources' % resource)
            any_reproduces = True
            continue
        try:
            r = check_one(resource, src)
        except ValueError as e:
            print('%-24s COULD_NOT_RUN  %s' % (resource, e))
            any_reproduces = True
            continue
        verdict = 'REPRODUCES' if r['reproduces'] else 'FIXED'
        print('%-24s %-10s %s' % (resource, verdict, r['gate_detail']))
        print('%-24s %-10s role matrix present: %s, allowed roles: %s'
              % (resource, 'MATRIX', r['role_matrix_present'], r['allowed_roles']))
        if r['reproduces']:
            any_reproduces = True
    return 1 if any_reproduces else 0


if __name__ == '__main__':
    sys.exit(main())
