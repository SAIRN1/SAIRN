"""api/sd-data-employees-refusal.test.js must refuse the DIAGNOSIS becoming the
AUTHORIZATION.

Run: python tests/employees_refusal_probe.py

ONE SENTENCE ANSWERED THREE DIFFERENT FACTS. The employees read said "Your role
does not have access to employee records" for all of: no session, a VALID
session for another app, and a StoneDesk session whose role really is denied.
Only the third is about a role. Found by holding a valid SAIRNbiz owner session
against production and being sent to the role model of an app that was never the
problem.

The fix names the app in the message -- and the only way to name it is to verify
the token a SECOND time WITHOUT expectedApp. THAT SECOND VERIFICATION IS THE
DANGEROUS PART, and the suite's own header says so: it must stay MESSAGE-ONLY.
If the unbound session ever reached the allow path, A SAIRNbiz ROLE WOULD READ A
STONEDESK ROSTER -- including, for an owner, hourly_rate.

So this is a control over a fix whose failure mode is more serious than the
defect it repaired. A better error message that becomes an authorization is a
worse outcome than the confusing message it replaced.

The mutations are the ways that inversion happens, and none of them looks
malicious in a diff:

  * the unbound session is returned into `session`, so the diagnosis IS the
    authorization -- one assignment;
  * the naming branch stops returning, so it falls through to the role check
    carrying a foreign session;
  * the role deny-list stops applying, which is the original gate and the only
    thing standing between a denied StoneDesk role and the roster;
  * the manager payroll strip goes, so a non-owner reads hourly_rate -- a
    separate promise in the same branch, and the one a role check cannot make;
  * the strip SETS the field to undefined instead of DELETING it, leaving the
    key on the object;
  * the strip mutates the UPSTREAM ROW rather than a copy, so the next OWNER
    read finds payroll gone.

MEASURED, NOT ASSERTED: mutation 6 is BLIND to the arms as they stood before
2026-09-16's tightening. Applied to a worktree at the previous commit, the suite
printed 10/10 -- because `=== undefined` is satisfied by a key that is still
there. That is the difference hasOwnProperty makes, and it is the only evidence
that the tightening was worth making.

AND THAT LAST ONE WAS SILENT. `hourly_rate` appeared in NO test anywhere on the
platform: "Manager: full roster visibility, but never payroll" was a promise
made in a comment and asserted by nothing. Three arms added -- the manager sees
no payroll, the OWNER still does (so the first is a strip and not an empty
response), and the STORED row is not mutated, because a delete on the upstream
object would remove payroll from whatever the client library cached and the next
owner read would be missing it too.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-employees-refusal.test.js')
API = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    ("1. THE DIAGNOSIS BECOMES THE AUTHORIZATION, in one assignment. The "
     "unbound verification -- which exists ONLY to name the app in a message -- "
     "is written back into `session`, so a valid SAIRNbiz owner reads a "
     "StoneDesk roster and gets hourly_rate with it",
     API,
     "        const otherApp = verifySessionToken(tokenFromRequest(req), licHash);",
     "        const otherApp = session = verifySessionToken(tokenFromRequest(req), licHash);"),

    # ── MUTATION 2 WAS WITHDRAWN, AND IT IS A SMALL FINDING ────────────────
    # "the APP COMPARISON drops" -- `if (otherApp && otherApp.app !==
    # 'stonedesk')` -> `if (otherApp)` -- is an EQUIVALENT MUTANT, and the
    # reasoning is worth keeping because it is not obvious.
    #
    # This branch is reached only when `session` is falsy, i.e. the SCOPED
    # verification failed. Scoped and unscoped differ by exactly one term: the
    # app. So if the unscoped verification succeeds AND the app really is
    # stonedesk, the scoped one would have succeeded too and `session` would be
    # truthy -- we would never be here. Inside this branch `otherApp.app !==
    # 'stonedesk'` is ALWAYS true.
    #
    # It is correct defence in depth against a future third verification path,
    # it costs nothing, and it is currently unreachable. Counting it as a
    # caught mutation would be a fabricated arm; calling it a coverage gap
    # would be a fabricated finding against a suite that is right.

    ("3. the naming branch STOPS RETURNING and falls through to the role check "
     "carrying a foreign session. The refusal is still written, so the response "
     "looks right, and execution continues past it",
     API,
     "            + 'writes this roster and StoneDesk reads it.' } });\n          return;",
     "            + 'writes this roster and StoneDesk reads it.' } });"),

    ("4. the ROLE DENY-LIST stops applying. This is the gate the whole branch "
     "was built around, and a sales rep reading the roster is the plain version "
     "of the defect -- driven so the arms cannot be passing on the app check "
     "alone",
     API,
     "      if (EMPLOYEES_READ_DENIED_ROLES[session.role]) {",
     "      if (false) {"),

    ("5. the MANAGER PAYROLL STRIP goes, so a non-owner reads hourly_rate. A "
     "separate promise living in the same branch: the role check decides WHO "
     "reads the roster, and this decides WHAT they see -- and no role check can "
     "make that second guarantee",
     API,
     "      if (session.role !== 'owner') {",
     "      if (false) {"),

    ("6. the strip SETS THE FIELD TO undefined instead of DELETING it. The key "
     "stays on the object, `=== undefined` is satisfied, and only "
     "hasOwnProperty can tell -- which is why the arm asserts genuine absence "
     "rather than an undefined read. Over the wire the two serialise "
     "identically, so this is a mutation the client contract cannot see and the "
     "in-process arm can",
     API,
     "          delete copy.hourly_rate;",
     "          copy.hourly_rate = undefined;"),

    ("7. the strip MUTATES THE UPSTREAM ROW rather than a copy, so payroll is "
     "removed from whatever the client library cached and THE NEXT OWNER READ "
     "FINDS IT GONE. The source says 'shallow-copy so we're not mutating "
     "whatever the upstream client library cached'; this deletes the sentence's "
     "reason for existing while leaving the sentence",
     API,
     "          var copy = Object.assign({}, e);\n          delete copy.hourly_rate;\n"
     "          return copy;",
     "          delete e.hourly_rate;\n          return e;"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='the employees read -- the suite must refuse a better error '
              'message that became an authorization'))
