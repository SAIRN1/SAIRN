"""tests/app_session_isolation.js must REFUSE -- and it PASSED while printing
its own refutation.

Run: python tests/app_session_isolation_probe.py

THE ARM SAID THIS, IN GREEN, ON origin/main:

    ok  PHASE 1 (2026-09-05, still open): law_trusttx is reachable with the
        LICENCE ALONE -- no session -- and answers 403

It asserted `out.code !== 401`. law_trusttx was gated on 2026-09-16 and
SD_SESSION_GATED refuses with 403 FORBIDDEN, not 401, so the arm stayed green
and interpolated into its own message the status code that disproves the
sentence it was asserting. REACHABILITY WAS ENCODED AS THE NEGATION OF ONE
REFUSAL CODE, and the refusal that arrived was the other one.

The file's own comment, six lines above that loop, says: "a silent canary and a
healthy canary look identical." This canary sang the wrong note and was counted
as singing.

THIS IS THE THIRD UN-INVERTED PHASE ARM FOUND IN ONE SESSION and the only one
that did not go red. The other two -- in api/sd-data-sairnlaw-resources.test.js
and api/sd-data-session-gate.test.js -- failed loudly and sat failing. This one
is worse: nothing to notice, nothing to ignore, and the suite reporting ALL 54
ASSERTIONS PASS the whole time.

WHAT THIS SUITE IS FOR, which is why the arm mattered. For a licence with no
`app_id` -- the entire pre-2026-09-04 population, which nobody can enumerate --
THE ONLY THING BETWEEN ONE APP'S SESSION AND ANOTHER APP'S DATA IS THE
`expectedApp` ARGUMENT INSIDE EACH BRANCH. The licence boundary is deliberately
open for an unattributable licence; this file is what checks the other half.

The mutations are the properties:

  * law_trusttx becomes reachable again with the licence alone -- the pre-fix
    state, and the thing the broken arm could not see;
  * a still-open resource is gated early, which fails a staff member with the
    app already open;
  * the gated resource is quietly dropped from BOTH phase lists, leaving the
    boundary entirely while the suite goes green having stopped asking;
  * it is moved back into the still-ungated loop, which is the pre-fix
    classification and now fails because reachability is asserted as 200;
  * expectedApp reverts to the hardcoded 'stonedesk', which refuses every
    correctly signed-in attorney and whose obvious repair is to remove the gate.

── ONE MUTATION WAS WITHDRAWN, AND THE REASON IS THE POINT ───────────────────
The obvious seventh is "put `!== 401` back". It is an EQUIVALENT MUTANT as the
file now stands: the only resource that answers 403 is in PHASE_2_GATED, which
is asserted positively, so the remaining loop sees nothing but 200s and `!== 401`
and `=== 200` agree on every input it will ever get. Counting it would have
inflated this probe by one arm that proves nothing.

THE ORIGINAL DEFECT NEEDED BOTH HALVES -- a resource in the wrong list AND a
predicate too weak to notice -- and mutation 5 drives the half that is
observable. That is the distinction this platform paid for once already, when a
mutant swapping `if (!session) return false;` for `session = session || {};` was
nearly reported as a coverage gap in the roofing claim gate: MANAGEMENT_ROLES
[undefined] is already falsy, so the two are identical for every input, and
calling it a gap would have been a fabricated finding against a suite that was
right.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'app_session_isolation.js')
API = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    ("1. THE DEFECT THE BROKEN ARM COULD NOT SEE. law_trusttx leaves the session "
     "registry, so attorney IOLTA trust money is reachable on the licence key "
     "alone again -- the exact state this suite reported as healthy for as long "
     "as it was asserting `!== 401`",
     API,
     "      'law_trusttx': ['read', 'write']\n    };",
     "    };"),

    ("2. only the READ is gated. The quiet half: a trust ledger that can be "
     "read by anyone holding the licence key errors nowhere, and the write "
     "refusal makes the feature look protected",
     API,
     "      'law_trusttx': ['read', 'write']",
     "      'law_trusttx': ['write']"),

    ("3. a still-open resource is gated EARLY -- law_deadlines joins the "
     "registry before its phase-2 day, which fails a staff member with the app "
     "already open on a cached page that sends no token",
     API,
     "      'law_trusttx': ['read', 'write']",
     "      'law_deadlines': ['read', 'write'],\n      'law_trusttx': ['read', 'write']"),

    ("4. law_trusttx is dropped from BOTH phase lists -- it leaves the boundary "
     "entirely and the suite goes green having stopped asking about it. Only the "
     "partition arm sees this, and only because the two lists are required to "
     "reconstruct the original four",
     SUITE,
     "const PHASE_1_UNGATED = ['law_clients', 'law_matters', 'law_trusttx', 'law_deadlines'];",
     "const PHASE_1_UNGATED = ['law_clients', 'law_matters', 'law_deadlines'];"),

    ("5. law_trusttx MOVES BACK into the still-ungated loop -- the pre-fix "
     "classification. It answers 403, the loop demands 200, and the arm fails. "
     "The ORIGINAL defect needed BOTH halves: this list error AND reachability "
     "expressed as `!== 401`, which is why mutating the assertion alone is "
     "WITHDRAWN below rather than counted",
     SUITE,
     "  const PHASE_2_GATED = ['law_trusttx'];",
     "  const PHASE_2_GATED = [];"),

    ("6. the EXPECTED APP reverts to the hardcoded 'stonedesk'. Every correctly "
     "signed-in attorney is refused, and the obvious repair for THAT symptom is "
     "to take the gate off. This is the mutation that was SILENT until the "
     "expectedApp arms were added -- every other arm drives with NO session, "
     "and a no-session refusal is the same 403 whichever app the gate expected",
     API,
     "    const SD_GATE_APP = { 'law_trusttx': 'sairnlaw' };",
     "    const SD_GATE_APP = {};"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='app session isolation -- the suite must refuse a gate that moves, '
              'and must no longer report a 403 as "reachable"',
        stage=[SUITE]))
