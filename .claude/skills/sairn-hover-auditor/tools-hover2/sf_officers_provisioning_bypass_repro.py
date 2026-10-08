#!/usr/bin/env python
"""sf_officers_provisioning_bypass_repro.py -- reproducing artifact for the
SAIRNfreedom sf_officers finding (hover-audit-log, batch O item 10), not a
new audit pass.

Two deterministic checks, both must hold for REPRODUCES:
  1. 'sf_officers' does NOT appear as a key inside the SD_SESSION_GATED
     object literal (api/sd-data.js) -- i.e. no global pre-dispatch session
     gate covers it.
  2. The generic SF_RESOURCES write branch stores the caller's payload
     verbatim ('data: payload' or 'data: payload }' on the same statement
     that builds the upsert body for an SF_RESOURCES write) with no
     intervening role/capability check between the SF_RESOURCES[resource]
     write guard and that store.

Exit 1 REPRODUCES (both conditions true -- the bypass is still live).
Exit 0 means at least one condition no longer holds (a fix landed).
Exit 2 COULD NOT RUN (the expected literals are not found at all -- the
file shape changed enough that this tool cannot answer either way).

Usage:
  python sf_officers_provisioning_bypass_repro.py [--repo PATH]
  python sf_officers_provisioning_bypass_repro.py --selftest
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def check(src):
    """Returns (reproduces: bool, detail: str) or raises ValueError if the
    expected shapes are not found at all (COULD NOT RUN)."""
    gated_m = re.search(r"const SD_SESSION_GATED = \{(.*?)\n    \};", src, re.S)
    if not gated_m:
        raise ValueError("SD_SESSION_GATED object literal not found")
    gated_body = gated_m.group(1)
    sf_officers_gated = bool(re.search(r"'sf_officers'\s*:\s*\[", gated_body))

    generic_write_m = re.search(
        r"if \(SF_RESOURCES\[resource\] && action === 'write'\) \{(.*?)\n    \}",
        src, re.S)
    if not generic_write_m:
        raise ValueError("generic SF_RESOURCES write block not found")
    write_body = generic_write_m.group(1)
    # Whole-payload store with nothing resembling a role/capability check
    # between the resource guard and the store.
    stores_whole_payload = bool(re.search(r"data:\s*payload\b", write_body))
    has_role_check = bool(re.search(
        r"ROLES|role\s*!==|capability\s*!==|PROVISIONING_CAPS|session\.role",
        write_body))

    reproduces = (not sf_officers_gated) and stores_whole_payload and (not has_role_check)
    detail = (
        "sf_officers in SD_SESSION_GATED: %s; generic write stores data:payload verbatim: %s; "
        "role/capability check present in that write block: %s"
        % (sf_officers_gated, stores_whole_payload, has_role_check))
    return reproduces, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=os.path.abspath(
        os.path.join(HERE, '..', '..', '..', '..')))
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        bad_src = """
    const SD_SESSION_GATED = {
      'sf_accounts': ['read', 'write'],
    };
    if (SF_RESOURCES[resource] && action === 'write') {
      const idCol = SF_RESOURCES[resource];
      const r = await fetch(rest(resource), { body: JSON.stringify({ data: payload }) });
    }
"""
        rep, detail = check(bad_src)
        assert rep is True, "fixture A (planted bug) should REPRODUCE: %r" % detail

        fixed_src = """
    const SD_SESSION_GATED = {
      'sf_accounts': ['read', 'write'],
      'sf_officers': ['read', 'write'],
    };
    if (SF_RESOURCES[resource] && action === 'write') {
      const idCol = SF_RESOURCES[resource];
      const r = await fetch(rest(resource), { body: JSON.stringify({ data: payload }) });
    }
"""
        rep2, detail2 = check(fixed_src)
        assert rep2 is False, "fixture B (gated) should NOT reproduce: %r" % detail2

        role_checked_src = """
    const SD_SESSION_GATED = {
      'sf_accounts': ['read', 'write'],
    };
    if (SF_RESOURCES[resource] && action === 'write') {
      const idCol = SF_RESOURCES[resource];
      if (resource === 'sf_officers' && !PROVISIONING_CAPS.includes(...)) { return; }
      const r = await fetch(rest(resource), { body: JSON.stringify({ data: payload }) });
    }
"""
        rep3, detail3 = check(role_checked_src)
        assert rep3 is False, "fixture C (role-checked) should NOT reproduce: %r" % detail3

        try:
            check("no relevant literals here at all")
            assert False, "fixture D (absent shape) should raise ValueError"
        except ValueError:
            pass

        print("ALL SELFTEST CASES PASS")
        return 0

    path = os.path.join(args.repo, 'api', 'sd-data.js')
    if not os.path.isfile(path):
        print("COULD NOT RUN: %s not found" % path)
        return 2
    src = open(path, encoding='utf-8').read()
    try:
        reproduces, detail = check(src)
    except ValueError as e:
        print("COULD NOT RUN: %s" % e)
        return 2
    print(("REPRODUCES" if reproduces else "FIXED") + ": " + detail)
    return 1 if reproduces else 0


if __name__ == '__main__':
    sys.exit(main())
