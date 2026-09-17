"""api/sd-data-food-temp-unevaluated.test.js must go RED when the withheld
verdict is turned back into a substituted one.

Run: python tests/sd_data_food_temp_unevaluated_probe.py

WHY THIS SUITE IS TIER A. alf_op_audits food_temp rows are the compliance
artifact an inspector reads. The 2026-09-04 defect it pins is the sharpest
shape on this platform: a facility with a STRICTER local limit was graded
against the LOOSER FDA default, so a 41F cold-holding reading that should have
failed at their 40F was RECORDED AS A PASS. Nothing errored. The log simply
said the right thing about the wrong rule.

THE PROPERTY IS A THREE-WAY DISTINCTION AND ALL THREE MATTER:

  could-not-READ the thresholds -> record the reading, WITHHOLD the verdict
  did-not-CONFIGURE thresholds  -> grade on the FDA default, disclosed
  configured thresholds         -> grade on theirs

Two of those produce a `passed` value and one produces null, and collapsing any
pair is a defect that looks like a working feature. Mutations 1-3 collapse them
in each direction.

AND THE READING IS NEVER REFUSED. Refusing the write would discard an
observation somebody physically performed -- the artifact itself. So a suite
of "must refuse" arms would be the wrong shape here entirely: mutations 4 and 5
break the WRITE-ANYWAY property, which is the half a refusal-shaped control
would never notice.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-food-temp-unevaluated.test.js')
SRC = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    # THE 2026-09-04 DEFECT, RESTORED. `{}` reaches evaluateFoodTemp, which
    # falls back to the FDA figures -- the facility's stricter limit silently
    # replaced by the national one, and a failing reading logged as a pass.
    ("1. an unreadable threshold falls back to {} again, so the FDA default is "
     "substituted for a limit the facility actually set",
     SRC,
     "          let facRows = null;\n"
     "          if (facR.ok) facRows = await facR.json().catch(function () { return null; });",
     "          let facRows = [];\n"
     "          if (facR.ok) facRows = await facR.json().catch(function () { return []; });"),
    ("2. a non-array body stops counting as unreadable, so a malformed "
     "response is graded as if it were thresholds",
     SRC, "          if (!Array.isArray(facRows)) {", "          if (facRows === null) {"),
    # THE OTHER COLLAPSE. A facility that configured nothing is a REAL default
    # with a disclosed source; treating it as unreadable would withhold a
    # verdict that is legitimately available and stop grading working at all.
    #
    # ── THE FIRST VERSION OF THIS ARM WAS A NO-OP AND CAME BACK SILENT ─────
    # It changed `thresholds: fac.food_thresholds || {}` to `|| null`, which
    # LOOKS like a different value and is not one: op-audit.js:53 opens with
    # `const override = opts.thresholds || {}`, so null and {} are the same
    # argument. The bytes changed, the behaviour did not, and the harness
    # correctly reported the suite green -- a control arm can fail by testing
    # nothing just as an assertion can, and it does not announce which.
    # Re-aimed at the branch condition, where the collapse is real.
    ("3. an EMPTY facility table is treated as unreadable, so a facility that "
     "configured nothing is never graded at all",
     SRC, "          if (!Array.isArray(facRows)) {",
     "          if (!Array.isArray(facRows) || !facRows.length) {"),
    # ── 4 AND 5 ARE THE OTHER DIRECTION ────────────────────────────────────
    # The reading must LAND even when it cannot be graded. A control made only
    # of refusal arms would be satisfied by a branch that refused the write,
    # which is the one outcome this design rules out by name.
    ("4. the ungraded reading is REFUSED instead of recorded -- the compliance "
     "observation is discarded rather than stored unevaluated",
     SRC,
     "            console.error('sd-data: alf_facility food-threshold read failed, HTTP', facR.status, '-- recording the reading UNEVALUATED');\n"
     "            passed = null;",
     "            res.status(503).json({ error: { code: 'THRESHOLDS_UNAVAILABLE', message: 'Could not read thresholds' } });\n"
     "            return;"),
    ("5. the withheld verdict stops saying WHY -- `passed` is null with no "
     "state, which reads as not-yet-graded rather than could-not-grade",
     SRC, "              state: 'facility_threshold_unavailable',", "              state: undefined,"),
    ("6. the whole grading branch is skipped, so a food_temp reading is stored "
     "with whatever `passed` the client sent",
     SRC,
     "        if (payload.record_type === 'food_temp' && payload.holding_kind && payload.temperature_f !== undefined) {",
     "        if (false && payload.holding_kind && payload.temperature_f !== undefined) {"),
]

if __name__ == '__main__':
    sys.exit(run_probe(SUITE, MUTATIONS,
                       title='negative control -- api/sd-data-food-temp-unevaluated.test.js '
                             'must refuse each way a withheld verdict becomes a substituted one'))
