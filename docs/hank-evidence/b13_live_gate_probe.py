"""b13 post-push live verification (PR 3.2).

Not bare curl: tools/sairn_http.py, which raises on a Vercel challenge rather
than handing back the challenge page as if it were the app. A 403 is
UNVERIFIED, never verified-good.

WHAT IS AND IS NOT REACHABLE WITHOUT A CREDENTIAL, stated first so a reader
does not read a thin probe as a thorough one:

  REACHABLE   the static pages. sairnlegacy.html carries BOTH halves of F4/F5
              in its own source, so fetching the deployed page and looking for
              the new functions is a real check that the client half shipped --
              the same method a browser would use to get them.
  NOT         every api/sd-data.js branch this batch touched. The endpoint
              answers 401 NO_LICENSE before it reaches the resource/action
              dispatcher, so neither the new approve_clock_correction verb nor
              the leg_aftercare key derivation can be exercised from here. A
              licence key would be a real credential in a script and is not
              used. Those legs are COULD NOT RUN, and arms in
              api/t16-clock-correction-record.test.js and
              api/leg-aftercare-key-unambiguous.test.js drive them against the
              real handler locally instead.

Exit: 0 every reachable leg verified - 1 a leg FAILED - 2 nothing could run.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools"))
try:
    import sairn_http
except ImportError:
    sys.path.insert(0, r"C:\Users\marsh\Documents\SAIRN-hank\tools")
    import sairn_http

BASE = "https://sairn.vercel.app"

PAGE_CHECKS = [
    # (page, needle, what it proves)
    ("/sairnlegacy.html", "function legAcEsc",
     "F4: the delimiter-escaping helper the new key derivation calls"),
    ("/sairnlegacy.html", "ACX-",
     "F4: the escaped key form itself, so the deployed page can emit it"),
    ("/sairnlegacy.html", "^CS-[0-9]+-[0-9]+$",
     "F4: the legacy-safe guard, which is what preserves every existing id"),
    ("/sairnlegacy.html", "function legAdoptServerId",
     "F5: the local row adopting the id the server actually stored"),
    ("/sairnlegacy.html", "legMarkSynced(resource,srvId)",
     "F5: the SERVER's id being marked synced rather than the client's"),
]

fails = []
oks = []
couldnot = []

for path, needle, why in PAGE_CHECKS:
    url = BASE + path
    try:
        res = sairn_http.fetch(url, no_cache=True)
        body = res.body if hasattr(res, "body") else res
        if isinstance(body, bytes):
            body = body.decode("utf-8", "replace")
        status = getattr(res, "status", None)
    except Exception as exc:                                    # noqa: BLE001
        couldnot.append((path, needle, "fetch raised: %s" % exc))
        print("COULD NOT RUN  %s  %s" % (path, exc))
        continue
    if status is not None and status != 200:
        # A 403 is UNVERIFIED. It is NOT folded into a pass.
        couldnot.append((path, needle, "status %s" % status))
        print("COULD NOT RUN  %s  status=%s -- a non-200 is UNVERIFIED, not "
              "verified-good" % (path, status))
        continue
    if needle in body:
        oks.append((path, needle))
        print("ok             %s  <- %s" % (needle[:42], why))
    else:
        fails.append((path, needle, why))
        print("FAIL           %s NOT in the DEPLOYED %s -- %s"
              % (needle[:42], path, why))

# ── THE NAMED-UNREACHABLE LEGS ARE COUNTED, NOT ONLY DESCRIBED ────────────
# The first run of this probe printed `couldnot=0` immediately under a
# paragraph listing three legs that could not run, because those legs were
# described in prose and never entered the counter. A number beside prose that
# contradicts it is the number people quote.
UNREACHABLE = [
    ("api/sd-data.js sen_visits approve_clock_correction",
     "401 NO_LICENSE is answered before the action dispatcher, so the new verb "
     "cannot be reached without a real credential in this script"),
    ("api/sd-data.js leg_aftercare key derivation", "same reason"),
    ("api/_lib/compliance-rules.js T18 position-token validation",
     "reached only through an authenticated SAIRNcare training-compliance read"),
]
couldnot.extend((name, "-", why) for name, why in UNREACHABLE)

print("")
print("THE LEGS THAT COULD NOT RUN AND WHY, NAMED RATHER THAN OMITTED:")
print("  api/sd-data.js sen_visits approve_clock_correction -- 401 NO_LICENSE")
print("    is answered before the action dispatcher, so the new verb cannot be")
print("    reached without a real credential in this script.")
print("  api/sd-data.js leg_aftercare key derivation -- same reason.")
print("  api/_lib/compliance-rules.js T18 -- reached only through an")
print("    authenticated SAIRNcare training-compliance read.")
print("  Each of those is driven against the REAL handler locally:")
print("    node api/t16-clock-correction-record.test.js        (27 arms)")
print("    node api/leg-aftercare-key-unambiguous.test.js      (14 arms)")
print("    node api/t18-positions-vocabulary.test.js           (17 arms)")
print("")
print("verified=%d  fail=%d  couldnot=%d" % (len(oks), len(fails), len(couldnot)))
if fails:
    sys.exit(1)
if not oks:
    sys.exit(2)
sys.exit(0)
