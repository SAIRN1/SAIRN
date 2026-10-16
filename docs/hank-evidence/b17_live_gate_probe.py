"""b17 post-push live verification (PR 3.2).

Not bare curl: tools/sairn_http.py, which raises on a Vercel challenge rather
than handing back the challenge page as if it were the app. A non-200 is
UNVERIFIED, never verified-good.

WHAT IS AND IS NOT REACHABLE WITHOUT A CREDENTIAL, STATED FIRST so a thin
probe is not read as a thorough one. b17 landed seven things and only TWO of
them are credential-free reachable, both of them client halves:

  REACHABLE   sairnsenior.html's H8 half -- senIsOwner() and the corrections
              button that now enables for an owner's own submission, plus the
              ABSENCE of senCanClosePeriod(), the dormant helper b17 deleted.
              An absence check is the only way to prove a DELETION deployed.

  REACHABLE   sairnbuild.html's st() backup handler -- the queueing form must
              be there, the swallowing `catch(e){}` must be GONE, and the
              FIRST b17 version with two guarded loggers must also be gone,
              which is what proves the restructure deployed rather than the
              draft.

  NOT         THE WHOLE SERVER HALF, which is the entire consequential part:
                - api/sd-data.js's sen_period_closings resource, both verbs
                - the named refusal of payroll_closed_periods at the generic
                  settings path
                - the replay that derives the effective closed-period set
                - api/_lib/sen-payroll.js's sign guard, overpayments[] and
                  premium_may_be_owed
                - api/_lib/sen-evv-readiness.js's as-of threading
                - api/_lib/law-roles.js's trust lock (no code changed there,
                  but the arms that now cover it are not an endpoint)
              Every one of those answers 401/403 before the dispatcher without
              a licence key AND an employee session. A licence key would be a
              real credential in a committed script and is not used. Each leg
              is COULD NOT RUN here and is driven against the real handler
              locally instead -- which is NOT the same claim.

  AND TWO SQL FILES HAVE NOT BEEN RUN, so even WITH a credential the freeze
  ledger answers 503 NOT_PROVISIONED in production today. The mechanism this
  batch is mostly about cannot be live-verified by anybody until Michael runs
  sql/sairnsenior_period_closings_schema.sql and the audit schema.

SO A GREEN RUN HERE MEANS: the two client halves are deployed. It means
NOTHING about the freeze ledger, the reopen rule, the sign guard or the as-of
threading -- which is six of the seven things b17 did.

Exit: 0 every reachable leg verified - 1 a leg FAILED - 2 nothing could run.
"""
import os
import sys

sys.path.insert(0, r"C:\Users\marsh\Documents\SAIRN-hank\tools")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import sairn_http                                                # noqa: E402

BASE = "https://sairn.vercel.app"

PRESENT = [
    ("/sairnsenior.html", "function senIsOwner",
     "b17 H8: the owner tier alone, which is NOT senIsManagement() -- billing "
     "is management and may not approve somebody else's correction as its own"),
    ("/sairnsenior.html", "mine && !senIsOwner()",
     "...and the button's disabled state really consults it, rather than "
     "keeping a second copy of the rule"),
    ("/sairnsenior.html", "Approve your own",
     "the label says it IS their own, so a self-approval is never an accident"),
    ("/sairnbuild.html", "bldPendingMark(k,'__collection__')",
     "b17: a failed server backup whose rows have no id is marked with a "
     "sentinel rather than marking nothing"),
    ("/sairnbuild.html", "THREW and the record is on this device only",
     "...and it SAYS so, which the empty catch did not"),
    ("/sairnbuild.html", "bldPendingMark() is ABSENT",
     "the RESTRUCTURED form -- it reports when nothing will retry, which the "
     "first b17 version skipped in silence"),
]

# Strings that must NOT be on the deployed pages. An absence is the only way to
# verify a DELETION, and two of b17's changes are deletions.
ABSENT = [
    ("/sairnsenior.html", "function senCanClosePeriod",
     "the DORMANT role helper b17 deleted. Its presence would mean the "
     "deployed page predates the deletion, and a role helper with no caller "
     "reads as 'the client enforces this' to anybody grepping for it"),
    ("/sairnbuild.html", "try{bldSyncCollection(k,v,prev);}catch(e){}",
     "the SWALLOWING catch -- a failed server backup reported as a saved "
     "record. Its presence would mean the fix did not deploy"),
    ("/sairnbuild.html", "could not even QUEUE the failed",
     "the FIRST b17 form, with two guarded loggers. It took the bare-catch "
     "count in st() to three and tests/st_reports_failure.js caught it; its "
     "presence would mean the DRAFT deployed and the restructure did not"),
]

UNREACHABLE = [
    "api/sd-data.js -- the sen_period_closings resource, read and write (401 before the dispatcher)",
    "api/sd-data.js -- the named refusal of payroll_closed_periods at the settings path (401)",
    "api/sd-data.js -- senReadClosedPeriods's replay of closings and reopenings (401)",
    "api/_lib/sen-payroll.js -- the sign guard, overpayments[] and premium_may_be_owed (not an endpoint)",
    "api/_lib/sen-evv-readiness.js -- options.closed_periods and read_as_of (401)",
    "api/_lib/law-roles.js -- the trust hard-lock arms (no endpoint; no code changed there)",
    "sql/sairnsenior_period_closings_schema.sql -- NOT RUN, so the ledger is 503 NOT_PROVISIONED live",
    "sql/sairnsenior_audit_log_schema.sql -- NOT RUN, so every close is 503 AUDIT_UNAVAILABLE live",
]

fails, oks, couldnot = [], [], []
bodies = {}


def body_of(path):
    if path in bodies:
        return bodies[path]
    res = sairn_http.fetch(BASE + path, no_cache=True)
    body = res.body if hasattr(res, "body") else res
    if isinstance(body, bytes):
        body = body.decode("utf-8", "replace")
    status = getattr(res, "status", None)
    bodies[path] = (status, body)
    return bodies[path]


def squash(s):
    return "".join(s.split())


for path, needle, why in PRESENT:
    try:
        status, body = body_of(path)
    except Exception as exc:                                     # noqa: BLE001
        couldnot.append((path, needle, "fetch raised: %s" % exc))
        print("COULD NOT RUN  %s  %s" % (path, exc))
        continue
    if status is not None and status != 200:
        couldnot.append((path, needle, "status %s" % status))
        print("COULD NOT RUN  %s  status=%s -- a non-200 is UNVERIFIED, not "
              "verified-good" % (path, status))
        continue
    # WHITESPACE-INSENSITIVE, because a reformat of correct code is not a
    # missing fix and a literal cannot keep up with formatting.
    if squash(needle) in squash(body):
        oks.append((path, needle))
        print("ok             %-38s <- %s" % (needle[:38], why))
    else:
        fails.append((path, needle, why))
        print("FAIL           %s NOT in the DEPLOYED %s -- %s"
              % (needle[:38], path, why))

for path, needle, why in ABSENT:
    try:
        status, body = body_of(path)
    except Exception as exc:                                     # noqa: BLE001
        couldnot.append((path, needle, "fetch raised: %s" % exc))
        print("COULD NOT RUN  %s  %s" % (path, exc))
        continue
    if status is not None and status != 200:
        couldnot.append((path, needle, "status %s" % status))
        print("COULD NOT RUN  %s  status=%s" % (path, status))
        continue
    if squash(needle) in squash(body):
        fails.append((path, needle, why))
        print("FAIL           STILL ON THE DEPLOYED PAGE: %s -- %s"
              % (needle[:38], why))
    else:
        oks.append((path, "ABSENT: " + needle[:30]))
        print("ok             ABSENT %-31s <- %s" % (needle[:31], why))

for u in UNREACHABLE:
    couldnot.append(("-", u, "needs a real credential, or a migration nobody has run"))
    print("COULD NOT RUN  %s" % u)

total = len(oks) + len(fails) + len(couldnot)
print("")
print("verified=%d  failed=%d  could-not-run=%d" % (len(oks), len(fails), len(couldnot)))
print("A COULD-NOT-RUN IS NOT A PASS. %d of the %d legs could not be exercised, "
      "and SIX OF THE SEVEN THINGS b17 DID are among them -- including the "
      "freeze ledger, which cannot be verified live by anybody until two SQL "
      "files are run." % (len(couldnot), total))

if fails:
    sys.exit(1)
if not oks:
    sys.exit(2)
sys.exit(0)
