"""api/sd-data-active-credential.test.js must REFUSE, not merely agree.

Run: python tests/active_credential_gate_probe.py

THE ONLY CRITICAL RECORD IN THE DEFECT REGISTER THAT REACHED REAL TENANT DATA
ON THE REAL DEPLOYMENT. Until 2026-09-16 a DEACTIVATED employee kept gated read
AND write access to thirteen apps' resources for the remaining life of a 12h
token, because api/sd-data.js verified a token's signature and expiry and never
asked whether the credential behind it was still active. Deactivation is the one
control an owner has over somebody who has just left.

THE SUITE WAS WRITTEN THE SAME HOUR AS THE FIX AND HAD NEVER REFUSED ANYTHING.
That is the state every same-hour suite ships in, and it is indistinguishable
from a suite that works. It is also a STRUCTURAL suite -- it reads the source
rather than driving the handler -- which is the right choice for a 6000-line
env-configured endpoint and also the shape with the most ways to pass while
testing nothing: an anchor that drifts, a regex window that is too wide, an
assertion of PRESENCE satisfied by the comment explaining the mechanism.

EVERY MUTATION BELOW IS A CHANGE SOMEBODY COULD PLAUSIBLY MAKE WHILE TIDYING,
and each removes exactly one property:

  * the await is dropped -- the call is still right there, reads as correct, and
    gates on a promise nobody looked at;
  * the refusal stops being conditioned on CREDENTIAL_INACTIVE, so a database
    blink refuses every employee in the app -- the failure the third state
    exists to avoid, and the one whose obvious repair is to remove the gate;
  * the refusal is conditioned on the WRONG state, so a deactivated employee is
    let through and a could-not-tell is refused -- both wrong, in silence;
  * the 403 becomes a 401, which reads as a session problem and sends the user
    to sign in again, which they can do, because their credential is the thing
    that is off;
  * the log goes, so a re-check that never ran passes in silence;
  * the log loses its try/catch, so a logging failure throws out of the gate and
    refuses a caller for a reason that has nothing to do with them;
  * a SECOND copy of the app-to-table map appears locally -- the drift the
    shared module exists to prevent, and the map has no derivable rule, so a
    stale copy silently answers NO_ACTIVE_CHECK for the app it missed.

WHAT THIS PROBE DOES NOT CLAIM: that the suite's arms cover the re-check's
BEHAVIOUR. They cannot -- the behaviour is driven in api/_lib/auth.test.js,
including the sabotage arm where one token is verified before and after the row
behind it is flipped. This measures whether THIS file notices the wiring being
taken apart.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-active-credential.test.js')
API = os.path.join('api', 'sd-data.js')

# ── ANCHORS ARE WRITTEN INLINE, NOT HOISTED INTO CONSTANTS ──────────────────
# tools/mutation_anchor_check.py reads this list with `ast` rather than by
# importing it -- deliberately, because importing a probe RUNS it. A tuple
# element that is a NAME therefore cannot be resolved, and four arms here were
# reported as ANCHOR-0, "this anchor matches nothing", purely because their
# anchors were module constants. The probe itself passed the whole time; what
# went red was the platform check that asks whether every anchor still points at
# real code -- and an anchor checker emitting four false zeros is exactly as
# useless as one emitting none. Implicit string concatenation is fine: ast folds
# it into a single literal. A name is not.

MUTATIONS = [
    ("1. the AWAIT is dropped -- fire and forget. The call is still there and "
     "reads as correct at a glance; the gate now tests a pending promise, whose "
     "`.ok` is undefined, so nothing is ever refused",
     API,
     "      const stillActive = await credentialStillActive(gateSession, "
     "licHash, rest, headers);",
     "      const stillActive = credentialStillActive(gateSession, "
     "licHash, rest, headers);"),

    ("2. the refusal stops being conditioned on CREDENTIAL_INACTIVE, so a "
     "transport failure or an app with no employee table refuses EVERY "
     "employee. The obvious repair for that symptom is to delete the gate",
     API,
     "      if (!stillActive.ok && stillActive.code === "
     "'CREDENTIAL_INACTIVE') {",
     "      if (!stillActive.ok) {"),

    ("3. the refusal is conditioned on the WRONG state -- a deactivated "
     "employee is let through and a could-not-tell is refused. Both answers "
     "inverted, neither visible",
     API,
     "      if (!stillActive.ok && stillActive.code === "
     "'CREDENTIAL_INACTIVE') {",
     "      if (!stillActive.ok && stillActive.code === 'NO_ACTIVE_CHECK') {"),

    ("4. 403 becomes 401, which reads as a session problem and tells the user "
     "to sign in again -- which they can, because the thing that is off is "
     "their credential, not their session",
     API,
     "        res.status(403).json({ error: { code: stillActive.code, message: stillActive.message } });",
     "        res.status(401).json({ error: { code: stillActive.code, message: stillActive.message } });"),

    ("5. the log goes. A re-check that DID NOT RUN now passes in total silence, "
     "and the third state becomes indistinguishable from a pass",
     API,
     "          console.warn('sd-data: active-credential re-check DID NOT RUN for app \"'",
     "          void ('sd-data: active-credential re-check DID NOT RUN for app \"'"),

    ("6. the log loses its try/catch, so a logging failure throws out of the "
     "gate and refuses a caller for a reason that has nothing to do with them",
     API,
     "        try {\n          console.warn('sd-data: active-credential re-check DID NOT RUN",
     "        if (true) {\n          console.warn('sd-data: active-credential re-check DID NOT RUN"),

    ("7. a SECOND copy of the app-to-table map appears in sd-data.js. The map "
     "has no derivable rule -- four apps use a prefix, the rest the full name, "
     "and sairncare's table is not alf_* -- so a stale local copy answers "
     "NO_ACTIVE_CHECK for whichever app it missed, silently",
     API,
     "      const stillActive = await credentialStillActive(gateSession, "
     "licHash, rest, headers);",
     "      const AUTH_TABLE_BY_APP = { stonedesk: 'sd_employee_auth' };\n"
     "      const stillActive = await credentialStillActive(gateSession, "
     "licHash, rest, headers);"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='the active-credential re-check -- the suite must refuse a gate '
              'that is present, called, and doing nothing'))
