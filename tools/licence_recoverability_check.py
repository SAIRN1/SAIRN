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
  1  at least one licence is UNRECOVERABLE -- TRAPDOOR or SOLE_ROLE_TRAPDOOR
  2  at least one licence could not be checked — NOT a pass

SOLE_ROLE_TRAPDOOR ADDED 2026-09-21, AND IT WOULD HAVE EXITED 0 UNTIL TODAY.
This tool keyed its verdict on `state == "TRAPDOOR"` alone, so a licence in the
new state -- an active provisioner, but NO row holding the role that only that
role can create -- printed its state and then reported all-clear. An
unrecoverable licence with a zero exit code is this platform's most-repeated
defect shape (PR 1.11) wearing a different hat: the check RAN, and its silence
was the answer. The verdict is now derived from a NAMED SET, and an
unrecognised state is COULD NOT TELL rather than a pass.

SOLE_ROLE_DEGRADED is deliberately NOT in that set and does NOT exit 1: every
sole-role holder is inactive, and an active provisioner can reactivate one
through set_active with no SQL at all. Driven against the real api/sd-auth.js
before it was classified. It is printed as a warning, because it is one deleted
row away from the state above.

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

# -- THE STATE VOCABULARY, NAMED HERE SO AN UNKNOWN ONE CANNOT PASS ---------
# api/provisioner-health.js owns these. Listing them is a deliberate
# duplication and the ONLY one in this file -- tables, roles and sole roles are
# all read from the endpoint's response precisely so they cannot drift. The
# duplication buys the property that matters: a state added there and not here
# is COULD NOT TELL (exit 2), never a silent pass.
#
# That is not hypothetical. Until 2026-09-21 the verdict was
# `state == "TRAPDOOR"`, so SOLE_ROLE_TRAPDOOR -- a licence that genuinely
# cannot be recovered through the API -- would have printed itself and then
# exited 0.
KNOWN_STATES = (
    "HEALTHY",
    "NO_CREDENTIALS",
    "TRAPDOOR",
    "SOLE_ROLE_TRAPDOOR",
    "SOLE_ROLE_DEGRADED",
)

# The subset meaning NOBODY CAN RECOVER THIS THROUGH THE APP. Exit 1.
# SOLE_ROLE_DEGRADED is deliberately absent: an active provisioner can
# reactivate an inactive sole-role holder, which was DRIVEN against the real
# api/sd-auth.js rather than assumed.
UNRECOVERABLE = ("TRAPDOOR", "SOLE_ROLE_TRAPDOOR")

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

    trapped, unknown, degraded = [], [], []
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
        # AN UNRECOGNISED STATE IS NOT A PASS. The old code tested
        # `state in (...)` for the detail line and `== "TRAPDOOR"` for the
        # verdict, so a state added at the endpoint arrived here, printed
        # itself, and was counted as fine.
        if state not in KNOWN_STATES:
            msg = ("endpoint reported unknown state %r -- this tool has not "
                   "been taught it" % state)
            print("%-16s %-22s %-14s %s"
                  % (res.get("app_id") or app, key, "COULD NOT TELL", msg))
            unknown.append((key, msg))
            continue
        sole = res.get("sole_role")
        detail = ("%s rows / %s active   roles=%s"
                  % (res.get("credential_rows"), res.get("active_provisioners"),
                     ",".join(res.get("provisioning_roles") or [])))
        if sole:
            detail += ("   sole=%s (%s row(s), %s active)"
                       % (sole, res.get("sole_role_rows"),
                          res.get("active_sole_role")))
        print("%-16s %-22s %-14s %s"
              % (res.get("app_id") or app, key, state, detail))
        if state in UNRECOVERABLE:
            trapped.append((key, res))
        elif state == "SOLE_ROLE_DEGRADED":
            degraded.append((key, res))

    print("-" * 78)
    if degraded:
        # PRINTED BEFORE THE VERDICT so an early return cannot swallow it.
        # Not an error: no SQL is needed for this one.
        print("")
        print("ONE STEP FROM UNRECOVERABLE -- every sole-role holder is INACTIVE:")
        for key, res in degraded:
            print("   %s (%s): %s row(s) of %r, 0 active. An active provisioner"
                  % (key, res.get("app_id"), res.get("sole_role_rows"),
                     res.get("sole_role")))
            print("      can reactivate one through set_active -- no SQL required.")
            print("      But nobody can CREATE one, so if that row is deleted the")
            print("      licence is unrecoverable.")


    if trapped:
        print("\nUNRECOVERABLE LICENCE(S):")
        for key, res in trapped:
            if res.get("state") == "SOLE_ROLE_TRAPDOOR":
                print("   %s (%s): %d row(s) and %s active provisioner(s), but"
                      % (key, res.get("app_id"), res.get("credential_rows"),
                         res.get("active_provisioners")))
                print("      NO %r row at all. Ordinary provisioning still works,"
                      % res.get("sole_role"))
                print("      which is why this read as HEALTHY until 2026-09-21.")
                print("      Insert or promote a %r." % res.get("sole_role"))
            else:
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
