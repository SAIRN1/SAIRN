"""api/sd-data-law-phase2-session.test.js must REFUSE, not merely agree.

Run: python tests/run_law_phase2_session_sabotage_probe.py

WHY THIS EXISTS AND WHY IT IS NOT FOURTH'S JOB. The phase-2 gate
(`ce835a7e`) closed the last three SAIRNlaw resources that ran on a licence key
alone -- law_clients, law_matters and law_deadlines, the last of which is Tier A
-- and shipped a 24-arm suite with it. That suite had never been observed red.
"24 passed" is a statement about the suite agreeing with the code, not about its
ability to disagree, and the platform measured what that is worth on 2026-09-15:
7 of 154 JavaScript suites had a negative control at all.

FOUR DIRECTIONS, and the fourth is the one that found something:

  1. all three leave the table          -> not gated at all, the shipped state
  2. only the READ halves leave         -> the half-applied fix
  3. SD_GATE_APP loses them             -> the gate falls back to 'stonedesk'
     and refuses every correctly signed-in attorney. An OUTAGE rather than a
     hole, and it passes every hole-shaped arm ever written, because nothing is
     exposed.
  4. the CLIENT stops sending the token -> the gate holds and the app stops
     working.

── WHAT ARM 4 FOUND, AND IT IS A GAP IN THE SUITE RATHER THAN IN THE GATE ────
The phase-2 commit says the client half was "confirmed rather than assumed",
and it was -- by reading sairnlaw.html. NOTHING ASSERTS IT. The string
`X-SD-Auth` does not appear anywhere in that suite, so if the transport stops
attaching the token the 24 arms stay green while every gated SAIRNlaw resource
answers 403 to the real app. That is the shape SAIRNlegacy shipped on
2026-09-21: a gate landed against a client that did not send a token, found
only when somebody read every call site.

So this probe plants that defect, and the suite gains ONE arm that runs
sdnData() rather than scanning for it -- lifted out of the page and executed
against a stub, because a scan for the header NAME passes while the behaviour
is broken. Measured on this platform an hour earlier, on the same shape: a
scanning arm stayed green against `var tok=null;` because the string it looked
for was still sitting there.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-law-phase2-session.test.js')
API = os.path.join('api', 'sd-data.js')
APP = 'sairnlaw.html'

# ANCHOR RE-DERIVED 2026-09-25: law_deadlines stopped being the map's LAST row
# when the SAIRNdesign gates were appended below it, so it gained a trailing
# comma and this three-line block matched NOTHING -- both arms that use it sat
# ANCHOR-0 red on main, testing nothing while looking armed.
ENTRIES = ("      'law_clients': ['read', 'write'],\n"
           "      'law_matters': ['read', 'write'],\n"
           "      'law_deadlines': ['read', 'write'],\n")

MUTATIONS = [
    ("1. ALL THREE LEAVE THE TABLE -- a firm's client list, matter list and "
     "DEADLINES back on the licence key alone, which is exactly the state they "
     "shipped in from 2026-08-16 until 2026-09-22",
     API,
     ENTRIES,
     # TRAILING COMMA REQUIRED: the anchor above now ends in one (law_deadlines
     # is no longer the map's last row), so a replacement without it splices an
     # entry with no separator before the SAIRNdesign rows -- which is a
     # SyntaxError, i.e. a malformed mutant, not a planted defect.
     "      'law_phase2_placeholder_removed': ['read'],\n"),

    ("2. ONLY THE READ HALVES LEAVE -- the half-applied fix a hurried edit "
     "produces: the records are private to read and open to write",
     API,
     ENTRIES,
     "      'law_clients': ['write'],\n"
     "      'law_matters': ['write'],\n"
     "      'law_deadlines': ['write'],\n"),

    ("3. SD_GATE_APP LOSES THEM, so the gate verifies against 'stonedesk' and "
     "refuses every correctly signed-in attorney -- an OUTAGE, not a hole",
     API,
     "      'law_clients': 'sairnlaw',\n"
     "      'law_matters': 'sairnlaw',\n"
     "      'law_deadlines': 'sairnlaw',\n",
     ""),

    ("4. THE CLIENT STOPS SENDING THE TOKEN -- the gate holds and the whole app "
     "starts answering 403, the shape SAIRNlegacy shipped on 2026-09-21",
     APP,
     "  var tok=lawSessionToken();\n  if(tok)h['X-SD-Auth']=tok;\n",
     "  var tok=null;\n  if(tok)h['X-SD-Auth']=tok;\n"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='SAIRNlaw phase 2 -- the suite must refuse four ways of un-gating '
              'or over-gating the last three resources, INCLUDING the client half '
              'it did not assert',
        # api/sd-data.js is staged because a gate and its control written in one
        # session would otherwise be measured against the pre-gate handler at
        # HEAD; sairnlaw.html because mutation 4 plants there.
        stage=(API, APP)))
