"""api/sd-data-leg-session-gate.test.js must REFUSE, not merely agree.

Run: python tests/run_leg_session_gate_sabotage_probe.py

# REQUIREMENT: the suite guarding SAIRNlegacy's session gate must go RED when
#   the gate is removed, when it is moved BEHIND the query so a refused request
#   has already read the rows, when it stops being scoped to the app, when it
#   covers one branch and not the other, or when the client half that makes it
#   survivable is reverted -- because a gate that is present and wrong looks
#   exactly like a gate that works

WHAT WAS OPEN. Until 2026-09-21 both LEG_RESOURCES branches in api/sd-data.js
went from the licence hash straight to the PostgREST query, with no
verifySessionToken anywhere. Reproduced against the shipped file with a valid
key and NO X-SD-Auth header: leg_deathrecords read answered 200 with rows and
leg_custodylog write answered 200 having upserted. 36 tables, including the
death record and the chain-of-custody log for human remains.

── WHY THE "MOVED BEHIND THE QUERY" ARM IS THE ONE TO KEEP ────────────────
A gate that answers 401 after the fetch has already run is the shape that
passes every status-code assertion and leaks anyway. The suite counts fetch()
calls on a refused request for exactly that reason, and arm 2 is what proves
the counting is load-bearing rather than decorative.

── AND THE CLIENT HALF IS SABOTAGED TOO ───────────────────────────────────
56 of sairnlegacy.html's 58 sdnData() call sites passed no session flag, so
the transport had to start attaching the token unconditionally in the same
commit. Reverting that one line turns the gate into an outage on every read
and write in the app, which is the failure most likely to get a security fix
rolled back rather than a call site fixed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-leg-session-gate.test.js')
SD = os.path.join('api', 'sd-data.js')
APP = 'sairnlegacy.html'

GATE = ("    if (LEG_RESOURCES[resource]) {\n"
        "      const legSess = verifySessionToken(tokenFromRequest(req), licHash, 'sairnlegacy');\n"
        "      if (!legSess) {")

MUTATIONS = [
    ("1. THE GATE IS REMOVED -- the state of this file until 2026-09-21, in "
     "which a bare licence key reads a funeral home's death records",
     SD, GATE,
     "    if (false) {\n"
     "      const legSess = verifySessionToken(tokenFromRequest(req), licHash, 'sairnlegacy');\n"
     "      if (!legSess) {"),

    ("2. THE GATE STOPS REFUSING -- it runs, it verifies, and it lets a null "
     "session through anyway",
     SD,
     "      if (!legSess) {\n"
     "        res.status(401).json({ error: { code: 'NO_SESSION', message: 'Your sign-in could not be verified, so nothing was read or saved. Sign out and sign in again, then try once more.' } });",
     "      if (false) {\n"
     "        res.status(401).json({ error: { code: 'NO_SESSION', message: 'Your sign-in could not be verified, so nothing was read or saved. Sign out and sign in again, then try once more.' } });"),

    ("3. THE APP SCOPING IS DROPPED -- a valid session for ANY other app now "
     "reads and writes these tables, the Check 28 collision",
     SD,
     "      const legSess = verifySessionToken(tokenFromRequest(req), licHash, 'sairnlegacy');",
     "      const legSess = verifySessionToken(tokenFromRequest(req), licHash);"),

    ("4. THE GATE COVERS THE WRITE BRANCH ONLY -- the read is open again, "
     "which is the half that leaks rather than the half that changes them",
     SD, "    if (LEG_RESOURCES[resource]) {",
     "    if (LEG_RESOURCES[resource] && action === 'write') {"),

    # THE FRONT GATE IS REMOVED AND A LATE ONE PUT IN ITS PLACE, in one
    # replacement, because the first version of this arm only ADDED the late
    # check and left the front gate standing -- so the request was refused
    # before the fetch and the arm went SILENT. A mutation that leaves the
    # real guard in place tests nothing, and the probe said so.
    ("5. THE GATE MOVES BEHIND THE QUERY -- it answers 401 having already read "
     "the rows, which passes every status-code assertion and leaks anyway",
     SD,
     "    if (LEG_RESOURCES[resource]) {\n      const legSess = verifySessionToken(tokenFromRequest(req), licHash, 'sairnlegacy');\n      if (!legSess) {\n        res.status(401).json({ error: { code: 'NO_SESSION', message: 'Your sign-in could not be verified, so nothing was read or saved. Sign out and sign in again, then try once more.' } });\n        return;\n      }\n    }\n    if (LEG_RESOURCES[resource] && action === 'read') {\n      const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });",
     "    if (LEG_RESOURCES[resource] && action === 'read') {\n      const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });\n      if (!verifySessionToken(tokenFromRequest(req), licHash, 'sairnlegacy')) {\n        res.status(401).json({ error: { code: 'NO_SESSION', message: 'no' } });\n        return;\n      }"),

    ("6. [CLIENT] THE TRANSPORT STOPS SENDING THE TOKEN -- the gate becomes an "
     "outage on all 56 call sites that pass no flag, which is how a security "
     "fix gets reverted instead of a call site fixed",
     APP,
     "  if(legSession&&legSession.token)h['X-SD-Auth']=legSession.token;",
     "  if(withSession&&legSession&&legSession.token)h['X-SD-Auth']=legSession.token;"),
]

sys.exit(run_probe(
    SUITE, MUTATIONS,
    title='SAIRNlegacy: 36 tables including the chain-of-custody log must '
          'require an employee session -- on BOTH verbs, BEFORE the query, and '
          'scoped to this app',
    stage=(SD, APP),
))
