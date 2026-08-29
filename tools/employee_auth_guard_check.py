"""Every SQL file that writes credential rows must prove it cannot leave a
licence unrecoverable.

WHY THIS EXISTS
---------------
RF-PINNACLE-2026 spent an unknown stretch of time in a state where it had
credential rows, zero active owners, and no way back in through the API:

  bootstrap   409 while ANY row exists -- the existence probe deliberately does
              not filter on `active`
  setup       403 -- needs an active caller in PROVISIONING_ROLES
  set_active  403 -- same gate, plus a re-read that the caller's own row is
              still active

THE API CANNOT CREATE THAT STATE. `set_active` refuses self-deactivation and
refuses to deactivate the last active provisioner, and it re-reads the roster
rather than trusting the token, so the active-provisioner count cannot cross
1 -> 0 by any API path. It was created by SQL -- verification passes that wrote
`active: false`, and a cleanup script that would have deleted some owner rows
while leaving others.

So SQL is the only door into the trapdoor, and until 2026-08-29 nothing was on
it. This is the thing on it.

WHAT COUNTS AS SAFE
-------------------
Two end states, and only two:

  A. ZERO credential rows for that licence  -> bootstrap is re-armed. This is
     RECOVERY, not lockout, and conflating the two cost a day of confusion.
  B. AT LEAST ONE row that is `active` AND holds a role in that app's
     PROVISIONING_ROLES -> setup and set_active both work.

Deleting or deactivating SOME provisioners while leaving others is the only
dangerous shape.

WHAT THIS CHECKS
----------------
Any file under sql/ that INSERTs, UPDATEs or DELETEs a `*_employee_auth` table
must have both:

  * a transaction (`commit;`) -- a guard that cannot roll anything back is
    decoration, and most of the older files have no transaction at all; and
  * the guard marker, `ZERO active provisioners`, from a `do $$` block that
    raises on the unsafe end state.

READ EACH APP'S OWN PROVISIONING_ROLES. SAIRNcode's is `admin`; the other four
are `owner` or `owner`+`admin`. A guard that hardcodes `owner` passes SAIRNcode
clean forever while checking nothing -- the app answers normally right up until
someone needs to recover it.

  SAIRNdental    ['owner']            api/dnt-auth.js
  SAIRNmechanical['owner']            api/mech-auth.js
  SAIRNroofing   ['owner']            api/rf-auth.js
  SAIRNcode      ['admin']            api/sc-auth.js
  StoneDesk      ['owner', 'admin']   api/sd-auth.js

GRANDFATHERED FILES ARE LISTED, NOT HIDDEN
------------------------------------------
Nineteen writers predate this check and are recorded in GRANDFATHERED below
with the date. They are NOT fixed -- most have no transaction, so adding a
raising guard would abort nothing, and wrapping already-run scripts in one is a
separate job. Listing them keeps the number visible and burnable down. A file
that leaves this list must gain a guard, not be deleted from it.

Exit codes:
  0  every writer is guarded, or explicitly grandfathered
  1  an unguarded, un-grandfathered writer exists

Usage:
    python tools/employee_auth_guard_check.py
    python tools/employee_auth_guard_check.py --changed a.sql b.sql
"""

import argparse
import glob
import io
import os
import re
import sys

SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql")
MARKER = "ZERO active provisioners"
WRITE_RE = re.compile(
    r"(insert\s+into|update|delete\s+from)\s+public\.[a-z_]*employee_auth", re.I)
COMMIT_RE = re.compile(r"^\s*commit\s*;", re.I | re.M)

# Writers that predate the check, 2026-08-29. Recorded so the count is visible.
# Do not add to this list -- add a guard instead.
GRANDFATHERED = {
    "rbac_test_artifact_cleanup.sql",
    "sairnbuild_visual_review_cleanup.sql",
    "sairncode_gate_test_coder_cleanup.sql",
    "sairncode_verify_admin_seed.sql",
    "sairndental_verify_auth_cleanup_2026-08-27.sql",
    "sairndental_verify_tiering_cleanup_2026-08-27.sql",
    "sairnlaw_test_license_reset_2026-08-13.sql",
    "sairnlaw_test_license_reset_2026-08-18.sql",
    "sairnmechanical_verify_auth_cleanup_2026-08-27.sql",
    "sairnroofing_verify_accounts_cleanup.sql",
    "sairnroofing_verify_admin_seed.sql",
    "sairnroofing_verify_cleanup.sql",
    "sairnroofing_verify_damage_cleanup_2026-08-26.sql",
    "sairnroofing_verify_foremen_seed.sql",
    "sairnsenior_evv_readiness_verify_cleanup_2026-08-27.sql",
    "sairnsenior_verify_cleanup_2026-08-25.sql",
    "stonedesk_audit_license_credential_reset.sql",
    "stonedesk_verify_admin_seed.sql",
    # Schema definition, not a data write -- it seeds nothing and targets no
    # licence, so there is no end state for a guard to assert.
    "sd_employee_auth_schema.sql",
}


def classify(path):
    src = io.open(path, encoding="utf-8", newline="").read()
    if not WRITE_RE.search(src):
        return None
    return {
        "name": os.path.basename(path),
        "guarded": MARKER in src,
        "txn": bool(COMMIT_RE.search(src)),
    }


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--changed", nargs="*", default=None,
                    help="only check these paths (used by the push hook)")
    args = ap.parse_args()

    paths = ([p for p in args.changed if p.endswith(".sql") and os.path.isfile(p)]
             if args.changed is not None
             else sorted(glob.glob(os.path.join(SQL_DIR, "*.sql"))))

    writers = [c for c in (classify(p) for p in paths) if c]
    bad = [c for c in writers
           if not (c["guarded"] and c["txn"]) and c["name"] not in GRANDFATHERED]
    ok = [c for c in writers if c["guarded"] and c["txn"]]
    old = [c for c in writers if c["name"] in GRANDFATHERED]

    print("employee_auth writers checked: %d" % len(writers))
    print("  guarded         : %d" % len(ok))
    print("  grandfathered   : %d  (predate 2026-08-29; not fixed, just visible)" % len(old))
    print("  UNGUARDED       : %d" % len(bad))

    if not bad:
        if writers:
            print("\nOK -- every writer either carries the guard or is on the")
            print("grandfathered list.")
        else:
            print("\nOK -- no file in this set writes a credential row.")
        return 0

    print("\nUNGUARDED CREDENTIAL WRITER(S):")
    for c in bad:
        why = []
        if not c["guarded"]:
            why.append("no guard")
        if not c["txn"]:
            why.append("no transaction (a guard here could not roll back)")
        print("   %-58s %s" % (c["name"], ", ".join(why)))

    print("""
Add a guard before the final `commit;`, using THAT APP'S OWN PROVISIONING_ROLES
(SAIRNcode's is `admin`, not `owner`). Copy the block from
sql/sairnroofing_access_panel_verify_cleanup_2026-08-28.sql, or:

do $$
declare
  lh   text := encode(digest('<LICENCE-KEY>', 'sha256'), 'hex');
  rows int; prov int;
begin
  select count(*) into rows from public.<app>_employee_auth where license_hash = lh;
  select count(*) into prov from public.<app>_employee_auth
   where license_hash = lh and active = true and role = any (array['owner']);
  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: would leave % credential row(s) and ZERO active provisioners. '
      'Delete EVERY row for this licence, or leave at least one active '
      'provisioner. Never a subset of the provisioners.', rows;
  end if;
  raise notice 'Guard passed: % row(s), % active provisioner(s).', rows, prov;
end $$;

Zero rows is SAFE -- it re-arms bootstrap and is recovery, not lockout.""")
    return 1


if __name__ == "__main__":
    sys.exit(main())
