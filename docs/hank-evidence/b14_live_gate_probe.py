"""b14 post-push live verification (PR 3.2).

Not bare curl: tools/sairn_http.py, which raises on a Vercel challenge rather
than handing back the challenge page as if it were the app. A non-200 is
UNVERIFIED, never verified-good.

WHAT IS AND IS NOT REACHABLE WITHOUT A CREDENTIAL, first, so a thin probe is
not read as a thorough one:

  REACHABLE   the static pages. sairnsenior.html carries the whole
              clock-corrections queue -- the render functions, the disabled
              control, the per-resource error memory -- in its own source, so
              fetching the deployed page and looking for them is a real check
              that the client half shipped, by the same route a browser takes.
              The queue was ALSO driven in a real browser DOM against the
              deployed page: docs/hank-evidence/b14/dom_real_browser.md.
  NOT         approve_clock_correction and propose_clock_correction. The
              endpoint answers 401 NO_LICENSE before the action dispatcher, so
              neither verb can be exercised here. A licence key would be a real
              credential in a script and is not used. Those legs are COULD NOT
              RUN and are driven against the real handler locally instead.

Exit: 0 every reachable leg verified - 1 a leg FAILED - 2 nothing could run.
"""
import os
import sys

sys.path.insert(0, r"C:\Users\marsh\Documents\SAIRN-hank\tools")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import sairn_http                                                # noqa: E402

BASE = "https://sairn.vercel.app"

PAGE_CHECKS = [
    ("/sairnsenior.html", "function renderCorrectionsView",
     "the pending-corrections queue itself"),
    ("/sairnsenior.html", "function senPendingCorrections",
     "the pending-only selector -- an entry with NO status is approved, not pending"),
    ("/sairnsenior.html", "You submitted this one",
     "the DISABLED control's own text: the UI half of approver != submitter"),
    ("/sairnsenior.html", "function vsApproveCorrection",
     "the handler the Approve button calls"),
    ("/sairnsenior.html", "senLastErr",
     "the per-resource error memory, without which the Approve button is a silent no-op"),
    ("/sairnsenior.html", "vs-tab-corrections",
     "the tab, so the queue is reachable at all"),
    # The b13 work this batch builds on, re-checked rather than assumed still there.
    ("/sairnlegacy.html", "function legAdoptServerId",
     "b13's F5 fix is still deployed"),
]

fails, oks, couldnot = [], [], []

for path, needle, why in PAGE_CHECKS:
    url = BASE + path
    try:
        res = sairn_http.fetch(url, no_cache=True)
        body = res.body if hasattr(res, "body") else res
        if isinstance(body, bytes):
            body = body.decode("utf-8", "replace")
        status = getattr(res, "status", None)
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

# ── THE UNREACHABLE LEGS ARE COUNTED, NOT ONLY DESCRIBED ──────────────────
# b13's first probe printed `couldnot=0` directly under a paragraph listing
# three legs that could not run, because they lived in prose and never entered
# the counter. A number beside prose that contradicts it is the number people
# quote.
UNREACHABLE = [
    ("api/sd-data.js sen_visits approve_clock_correction",
     "401 NO_LICENSE is answered before the action dispatcher"),
    ("api/sd-data.js sen_visits propose_clock_correction",
     "same reason"),
    ("api/_lib/compliance-rules.js X1/X2 window fields",
     "reached only through an authenticated SAIRNcare training-compliance read"),
    ("the ten blob conversions",
     "every one is a WRITE path behind a licence key; the scope-key strip is "
     "proven against the real handler locally and has no readable surface here"),
]
couldnot.extend((name, "-", why) for name, why in UNREACHABLE)

print("")
print("THE LEGS THAT COULD NOT RUN, NAMED AND COUNTED:")
for name, why in UNREACHABLE:
    print("  %s -- %s" % (name, why))
print("  Each is driven against the REAL handler locally:")
print("    node api/b14-clock-approval-two-person.test.js            (18 arms)")
print("    node tests/sairncare_compliance_window_boundary.test.js   (15 arms)")
print("    node api/sd-data-stored-blob-scope-keys.test.js           (41 arms)")
print("  And the queue's DOM was driven in a real browser against the deployed")
print("  page: docs/hank-evidence/b14/dom_real_browser.md")
print("")
print("verified=%d  fail=%d  couldnot=%d" % (len(oks), len(fails), len(couldnot)))
if fails:
    sys.exit(1)
if not oks:
    sys.exit(2)
sys.exit(0)
