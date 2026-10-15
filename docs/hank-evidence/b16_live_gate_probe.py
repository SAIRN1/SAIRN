"""b16 post-push live verification (PR 3.2).

Not bare curl: tools/sairn_http.py, which raises on a Vercel challenge rather
than handing back the challenge page as if it were the app. A non-200 is
UNVERIFIED, never verified-good.

WHAT IS AND IS NOT REACHABLE WITHOUT A CREDENTIAL, stated FIRST so a thin
probe is not read as a thorough one. b16 landed four things and only ONE of
them is credential-free reachable:

  REACHABLE   sairnsenior.html's F2 half. The page carries senEvvException()
              and senEffClock() in its own source, so fetching the DEPLOYED
              page and looking for them is a real check that the client half
              shipped, by the same route a browser takes. The GPS arms are
              checked too -- the raw `clock_out_lat` read must STILL be there,
              because F2 deliberately did not move it.

  NOT         THE WHOLE SERVER HALF, which is most of the batch:
                - api/_lib/sen-payroll.js's freeze and adjustment lines
                - api/_lib/sen-evv-clock.js's effectiveClockAsOf
                - api/_lib/sen-evv-readiness.js element 6
                - api/sd-data.js's payroll_closed_periods read, the
                  NO_ACTIVE_CHECK log, and the SD_LINEAGE/SD_HR id change
              The payroll action answers 401 NO_LICENSE before the dispatcher,
              and the SD_HR read needs an owner/admin SESSION on top of that. A
              licence key would be a real credential in a script and is not
              used. Every one of those legs is COULD NOT RUN here and is driven
              against the real handler locally instead -- which is NOT the same
              claim and the report says so.

SO A GREEN RUN HERE MEANS: the client half of F2 is deployed. It means nothing
about the freeze, which is the largest and most consequential change in the
batch and which has NO live verification at all.

Exit: 0 every reachable leg verified - 1 a leg FAILED - 2 nothing could run.
"""
import os
import sys

sys.path.insert(0, r"C:\Users\marsh\Documents\SAIRN-hank\tools")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import sairn_http                                                # noqa: E402

BASE = "https://sairn.vercel.app"

PAGE_CHECKS = [
    ("/sairnsenior.html", "function senEvvException",
     "b16 F2: the ONE EVV exception predicate, shared by the filter and the label"),
    ("/sairnsenior.html", "senEvvException(v)!==null",
     "...and the filter really calls it, rather than keeping its own copy"),
    ("/sairnsenior.html", "function senEffClock",
     "the effective-clock helper F2's time-span arm reads"),
    ("/sairnsenior.html", "v.clock_out_lat",
     "the GPS arm is STILL RAW -- F2 moved the time span and deliberately not "
     "the location, because a correction supplies a time and never a coordinate"),
    # b15's work this batch builds on, re-checked rather than assumed still there.
    ("/sairnsenior.html", "function renderCorrectionsView",
     "b15's hydrate-first corrections queue is still deployed"),
]

# A string that must NOT be on the deployed page. The old duplicated condition
# is the thing senEvvException replaced; if it is still there, the filter and
# the label can disagree again and the deploy is PARTIAL.
ABSENT_CHECKS = [
    ("/sairnsenior.html", "(v.clock_in_at&&!v.clock_out_at&&v.status==='in_progress')||",
     "the OLD duplicated exception condition -- its presence would mean the "
     "deployed page is not this commit"),
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


for path, needle, why in PAGE_CHECKS:
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
    if needle in body:
        oks.append((path, needle))
        print("ok             %-34s <- %s" % (needle[:34], why))
    else:
        fails.append((path, needle, why))
        print("FAIL           %s NOT in the DEPLOYED %s -- %s"
              % (needle[:34], path, why))

for path, needle, why in ABSENT_CHECKS:
    try:
        status, body = body_of(path)
    except Exception as exc:                                     # noqa: BLE001
        couldnot.append((path, needle, "fetch raised: %s" % exc))
        print("COULD NOT RUN  %s  %s" % (path, exc))
        continue
    if status is not None and status != 200:
        couldnot.append((path, needle, "status %s" % status))
        continue
    if needle in body:
        fails.append((path, needle, why))
        print("FAIL           the OLD condition is STILL on the deployed page -- %s" % why)
    else:
        oks.append((path, "ABSENT: " + needle[:30]))
        print("ok             %-34s <- %s" % ("ABSENT old condition", why))

# ── THE UNREACHABLE LEGS ARE COUNTED, NOT ONLY DESCRIBED ──────────────────
UNREACHABLE = [
    "api/_lib/sen-payroll.js -- the freeze and the adjustment line (401 NO_LICENSE)",
    "api/_lib/sen-evv-clock.js -- effectiveClockAsOf (not an endpoint)",
    "api/_lib/sen-evv-readiness.js -- element 6 on the effective clock (401)",
    "api/sd-data.js -- the payroll_closed_periods read from sen_settings (401)",
    "api/sd-data.js -- the NO_ACTIVE_CHECK log wording (a server log, not a response)",
    "api/sd-data.js -- SD_LINEAGE/SD_HR id: the column wins (needs an owner session)",
]
for u in UNREACHABLE:
    couldnot.append(("-", u, "needs a real credential; not used here"))
    print("COULD NOT RUN  %s" % u)

print("")
print("verified=%d  failed=%d  could-not-run=%d" % (len(oks), len(fails), len(couldnot)))
print("A COULD-NOT-RUN IS NOT A PASS. %d of the %d legs in this batch could not "
      "be exercised without a credential, and the freeze -- the largest change "
      "-- is one of them." % (len(couldnot), len(oks) + len(fails) + len(couldnot)))
if fails:
    sys.exit(1)
if not oks:
    sys.exit(2)
sys.exit(0)
