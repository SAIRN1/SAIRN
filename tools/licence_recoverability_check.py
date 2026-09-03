"""Is any licence sitting in the unrecoverable-credential state right now?

WHY THIS EXISTS
---------------
RF-PINNACLE-2026 entered a state where it had credential rows, zero active
owners, and no way back in through the API. It sat there long enough for a HIGH
PRIORITY row to be written about it, then recovered — and NOTHING NOTICED EITHER
TRANSITION. The index row was still asserting zero active owners on 2026-08-29
when a live roster read showed two. Both the entry and the exit were invisible.

This is the detection half. tools/employee_auth_guard_check.py stops a new SQL
file creating the state; this reports a licence that is already in it.

WHAT THE STATE IS
-----------------
Credential rows exist AND zero of them are both `active` and hold a role in
that app's PROVISIONING_ROLES. Then:

  bootstrap   409 while ANY row exists — the probe does not filter on `active`
  setup       403 — needs an active provisioner
  set_active  403 — same, plus a re-read that the caller's own row is active

ZERO ROWS IS NOT THAT STATE. It re-arms bootstrap and is recovery, not lockout,
and this tool reports it as NO_CREDENTIALS rather than folding it into the
failure count.

THE ROLES ARE NOT ASSUMED
-------------------------
api/provisioner-health.js imports each app's PROVISIONING_ROLES from its own
auth module rather than listing them. Four apps use ['owner']; SAIRNcode uses
['admin'] and StoneDesk ['owner','admin']. A checker that assumed `owner` would
report SAIRNcode healthy forever while checking nothing — the app answers
normally right up until someone needs to recover it. The response echoes the
roles it used so the answer can be audited rather than trusted.

Exit codes:
  0  every licence checked is HEALTHY or NO_CREDENTIALS
  1  at least one licence is in the TRAPDOOR
  2  at least one licence could not be checked — NOT a pass

Usage:
    python tools/licence_recoverability_check.py
    python tools/licence_recoverability_check.py --key DNT-PINNACLE-2026
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import sairn_http  # noqa: E402  -- browser-shaped fetch; see that module


DEFAULT_ENDPOINT = "https://sairn.vercel.app/api/provisioner-health"

# The licences this platform actually has for the five apps that implement
# set_active. These are demo/verification keys already committed in
# sql/*_license_seed.sql, so naming them introduces no secret. An env var wins.
LICENCES = [
    ("stonedesk", "SD_LICENSE_KEY", "SD-PINNACLE-2026"),
    ("stonedesk", "SD_AUDIT_LICENSE_KEY", "SD-AUDIT-2026"),
    ("stonedesk", "SD_PARTNER_LICENSE_KEY", "SD-PARTNER-2026"),
    ("sairndental", "SAIRNDENTAL_LICENSE_KEY", "DNT-PINNACLE-2026"),
    ("sairnmechanical", "SAIRNMECHANICAL_LICENSE_KEY", "MECH-PINNACLE-2026"),
    ("sairnroofing", "SAIRNROOFING_LICENSE_KEY", "RF-PINNACLE-2026"),
    ("sairncode", "SAIRNCODE_LICENSE_KEY", "SC-PINNACLE-2026"),
]


def post(endpoint, key):
    body = json.dumps({"action": "provisioner_health"}).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=body, method="POST",
        headers=sairn_http.with_browser_ua(
            {"Content-Type": "application/json", "Authorization": "Bearer " + key}))
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # A Vercel bot-mitigation challenge is NOT an answer from the app, and a
        # gate that parses it as one reports "could not tell" when the truth is
        # "was blocked". CLAUDE.md already says could-not-tell is not a pass;
        # this makes the two distinguishable instead of identical.
        sairn_http.raise_if_challenge(e)
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:300]}
    except urllib.error.URLError as e:
        return 0, {"error": {"message": "connection failed: %s" % e.reason}}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", help="check one licence key instead of the built-in list")
    ap.add_argument("--endpoint", default=os.environ.get("SAIRN_PROVISIONER_HEALTH_API",
                                                        DEFAULT_ENDPOINT))
    args = ap.parse_args()

    targets = ([("(given)", None, args.key)] if args.key
               else [(a, e, os.environ.get(e) or d) for a, e, d in LICENCES])

    trapped, unknown = [], []
    print("%-16s %-22s %-14s %s" % ("APP", "LICENCE", "STATE", "rows / active provisioners"))
    print("-" * 78)
    for app, _env, key in targets:
        st, res = post(args.endpoint, key)
        if st != 200 or not res.get("ok"):
            msg = (res.get("message") or (res.get("error") or {}).get("message")
                   or json.dumps(res))[:70]
            print("%-16s %-22s %-14s %s" % (app, key, "COULD NOT TELL", msg))
            unknown.append((key, msg))
            continue
        state = res.get("state")
        detail = ("%s / %s   roles=%s"
                  % (res.get("credential_rows"), res.get("active_provisioners"),
                     ",".join(res.get("provisioning_roles") or []))
                  if state in ("HEALTHY", "TRAPDOOR", "NO_CREDENTIALS") else "")
        print("%-16s %-22s %-14s %s" % (res.get("app_id") or app, key, state, detail))
        if state == "TRAPDOOR":
            trapped.append((key, res))

    print("-" * 78)
    if trapped:
        print("\nUNRECOVERABLE LICENCE(S) -- credential rows with no active provisioner:")
        for key, res in trapped:
            print("   %s (%s): %d row(s), 0 active of %s"
                  % (key, res.get("app_id"), res.get("credential_rows"),
                     ",".join(res.get("provisioning_roles") or [])))
        print("\nFix with ONE SQL statement: reactivate or promote a provisioner, or")
        print("delete EVERY credential row for that licence to re-arm bootstrap.")
        print("NEVER delete a subset of the provisioners -- that is how this state")
        print("is created in the first place.")
        return 1

    if unknown:
        print("\nCOULD NOT TELL for %d licence(s). That is NOT a pass -- nothing is"
              % len(unknown))
        print("claimed about them. Re-run, or check the key and the endpoint.")
        return 2

    print("\nAll checked licences are recoverable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
