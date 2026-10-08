#!/usr/bin/env python
"""sf_sessions_gaming_payout_bypass_repro.py -- reproducing artifact for the
sf_sessions finding (hover-audit-log seq731 addendum 1, seq748 addendum 2),
same shape as sf_officers_provisioning_bypass_repro.py, not a new audit
pass.

Three deterministic checks, all must hold for REPRODUCES:
  1. 'sf_sessions' does NOT appear as a key inside the SD_SESSION_GATED
     object literal (api/sd-data.js) -- no global pre-dispatch session
     gate covers it.
  2. The generic SF_RESOURCES write branch stores the caller's payload
     verbatim ('data: payload' on the statement that builds the upsert
     body), with no intervening role/capability check -- same mechanism
     as sf_officers, since both resources share the one generic dispatch.
  3. sfRecordResults() -- the function that records the ACTUAL GAMING
     PAYOUT (receipts/prizes per game) -- still exists in sairnfreedom.html
     and still writes through st(K_SESSIONS, ...), confirming the client
     half of the finding (the sharpest of sf_sessions' three write sites)
     has not been removed or routed through a different, gated path.

Exit 1 REPRODUCES (all three true -- the bypass is still live for the
payout-recording site specifically).
Exit 0 means at least one condition no longer holds (a fix landed).
Exit 2 COULD NOT RUN (the expected literals are not found at all).

Usage:
  python sf_sessions_gaming_payout_bypass_repro.py [--repo PATH]
  python sf_sessions_gaming_payout_bypass_repro.py --selftest
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def check_server(src):
    gated_m = re.search(r"const SD_SESSION_GATED = \{(.*?)\n    \};", src, re.S)
    if not gated_m:
        raise ValueError("SD_SESSION_GATED object literal not found")
    gated_body = gated_m.group(1)
    sf_sessions_gated = bool(re.search(r"'sf_sessions'\s*:\s*\[", gated_body))

    generic_write_m = re.search(
        r"if \(SF_RESOURCES\[resource\] && action === 'write'\) \{(.*?)\n    \}",
        src, re.S)
    if not generic_write_m:
        raise ValueError("generic SF_RESOURCES write block not found")
    write_body = generic_write_m.group(1)
    stores_whole_payload = bool(re.search(r"data:\s*payload\b", write_body))
    has_role_check = bool(re.search(
        r"ROLES|role\s*!==|capability\s*!==|PROVISIONING_CAPS|session\.role",
        write_body))
    return sf_sessions_gated, stores_whole_payload, has_role_check


def check_client(src):
    func_m = re.search(
        r"function sfRecordResults\(\)\{(.*?)\n\}", src, re.S)
    if not func_m:
        raise ValueError("sfRecordResults() not found in sairnfreedom.html")
    body = func_m.group(1)
    writes_sessions = bool(re.search(r"st\(K_SESSIONS\s*,", body))
    return writes_sessions


def check(server_src, client_src):
    sf_sessions_gated, stores_whole_payload, has_role_check = check_server(server_src)
    writes_sessions = check_client(client_src)

    reproduces = ((not sf_sessions_gated) and stores_whole_payload
                  and (not has_role_check) and writes_sessions)
    detail = (
        "sf_sessions in SD_SESSION_GATED: %s; generic write stores data:payload "
        "verbatim: %s; role/capability check present: %s; sfRecordResults() "
        "still writes st(K_SESSIONS,...): %s"
        % (sf_sessions_gated, stores_whole_payload, has_role_check, writes_sessions))
    return reproduces, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=os.path.abspath(
        os.path.join(HERE, '..', '..', '..', '..')))
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        bad_server = """
    const SD_SESSION_GATED = {
      'sf_accounts': ['read', 'write'],
    };
    if (SF_RESOURCES[resource] && action === 'write') {
      const idCol = SF_RESOURCES[resource];
      const r = await fetch(rest(resource), { body: JSON.stringify({ data: payload }) });
    }
"""
        bad_client = """
function sfRecordResults(){
  var list=getSessions();
  st(K_SESSIONS,list);
}
"""
        rep, detail = check(bad_server, bad_client)
        assert rep is True, "fixture A (planted bug) should REPRODUCE: %r" % detail

        fixed_server = """
    const SD_SESSION_GATED = {
      'sf_accounts': ['read', 'write'],
      'sf_sessions': ['read', 'write'],
    };
    if (SF_RESOURCES[resource] && action === 'write') {
      const idCol = SF_RESOURCES[resource];
      const r = await fetch(rest(resource), { body: JSON.stringify({ data: payload }) });
    }
"""
        rep2, detail2 = check(fixed_server, bad_client)
        assert rep2 is False, "fixture B (gated) should NOT reproduce: %r" % detail2

        removed_client = """
function sfRecordResults(){
  var list=getSessions();
}
"""
        rep3, detail3 = check(bad_server, removed_client)
        assert rep3 is False, "fixture C (client write removed) should NOT reproduce: %r" % detail3

        try:
            check("no relevant literals here at all", bad_client)
            assert False, "fixture D (absent server shape) should raise ValueError"
        except ValueError:
            pass

        try:
            check(bad_server, "no sfRecordResults here at all")
            assert False, "fixture E (absent client function) should raise ValueError"
        except ValueError:
            pass

        print("ALL SELFTEST CASES PASS")
        return 0

    sd_path = os.path.join(args.repo, 'api', 'sd-data.js')
    html_path = os.path.join(args.repo, 'sairnfreedom.html')
    if not os.path.isfile(sd_path):
        print("COULD NOT RUN: %s not found" % sd_path)
        return 2
    if not os.path.isfile(html_path):
        print("COULD NOT RUN: %s not found" % html_path)
        return 2
    server_src = open(sd_path, encoding='utf-8').read()
    client_src = open(html_path, encoding='utf-8').read()
    try:
        reproduces, detail = check(server_src, client_src)
    except ValueError as e:
        print("COULD NOT RUN: %s" % e)
        return 2
    print(("REPRODUCES" if reproduces else "FIXED") + ": " + detail)
    return 1 if reproduces else 0


if __name__ == '__main__':
    sys.exit(main())
