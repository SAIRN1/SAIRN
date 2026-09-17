"""api/sd-data-numeric-guards.test.js must go RED when its guards are undone.

Run: python tests/sd_data_numeric_guards_probe.py

WHY THIS SUITE AND WHY NOW. It is Tier A -- law_trusttx is attorney client trust
money, the one balance a bar association audits -- and its section 2 is entirely
SOURCE-TEXT assertions against api/sd-data.js. That is a legitimate way to pin a
guard whose failure mode is textual (a comparison written where a domain check
belongs), and it is also the shape that stops testing anything the quietest: an
`indexOf` whose needle has been reworded reports the same `-1` whether the guard
moved, was deleted, or merely had a word changed in its message.

WHAT EACH MUTATION IS AIMED AT, ONE ARM EACH. Every one restores a defect the
suite's own comments say it exists to prevent, and nothing here plants a defect
the suite was never built to see -- a control that breaks a behaviour outside a
suite's remit measures the author's imagination, not the suite.

  1. the trust guard goes back to being a COMPARISON, which is the original
     defect verbatim: `NaN <= 0` is false, so the refusal never fires and the
     amount reaches law_check_and_insert_disbursement() as null;
  2. the trust refusal is reworded, which is the anchor-rot case -- the arm that
     proves the guard sits ABOVE both branches finds the guard by its message
     text, so a reworded message is indistinguishable from a deleted guard and
     the arm must say so rather than pass;
  3. the food-temperature refusal loses its code, so a caller can no longer tell
     BAD_TEMPERATURE from any other 400 and the arm that pins it must bite;
  4. the temperature guard is gated on holding_kind again, so a reading with a
     bad temperature and no holding_kind skips the guard entirely -- the exact
     shape the suite's comment says hides.

  5, 6. THE PAIR THAT FOUND A REAL GAP IN THE SUITE, one site each.
     `sen_payer_contracts KEEPS the negated form` used to test
     `/!\\(Number\\(payload\\.rate_per_hour\\) > 0\\)/` against the WHOLE file,
     and that expression appears TWICE -- once in sen_payer_contracts and once
     in sen_pay_rates, four hundred lines apart. Rewriting either one back to
     `<= 0` left the other satisfying the regex, so the arm stayed green over a
     money guard that had lost its ability to see NaN. Arm 5 planted exactly
     that on 2026-09-16 and the suite was SILENT.

     The suite now carries one arm per site, each anchored on the push target
     that belongs to that branch (`pcProblems`, `prProblems`). Arms 5 and 6
     break one site each, so neither can be satisfied by the other -- which is
     the property the single arm was missing and the reason both are kept.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-numeric-guards.test.js')
SRC = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    # THE DEFECT ITSELF, RESTORED. `Number('abc') <= 0` is false, so the branch
    # falls through and JSON.stringify writes NaN as null.
    ("1. the trust amount guard goes back to a range comparison, which cannot "
     "see NaN",
     SRC, "if (!isFinite(txAmount)) {", "if (txAmount <= 0) {"),
    # ANCHOR ROT, PLANTED ON PURPOSE. The arm locates the guard by this message,
    # so the day somebody rewords it the arm reports on a guard it can no longer
    # find. It must fail rather than pass -- which is the whole difference
    # between a live anchor and a dead one.
    ("2. the trust refusal is reworded, so the arm that proves the guard sits "
     "above BOTH branches can no longer find it",
     SRC, "'law_trusttx payload.amount must be a number — '",
     "'law_trusttx amount is invalid — '"),
    ("3. the food-temperature refusal loses its code, so a caller cannot tell "
     "it from any other 400",
     SRC, "code: 'BAD_TEMPERATURE'", "code: 'BAD_INPUT'"),
    # The guard fired on holding_kind before, so a reading that carried a bad
    # temperature and NO holding_kind was stored ungraded. Put back exactly.
    ("4. the temperature guard is gated on holding_kind again, so a reading "
     "without one skips it",
     SRC,
     "&& payload.temperature_f !== null && !isFinite(Number(payload.temperature_f))) {",
     "&& payload.holding_kind && !isFinite(Number(payload.temperature_f))) {"),
    # ── 5 AND 6 MEASURE THE SUITE, NOT THE SOURCE ──────────────────────────
    # Each breaks ONE of the two sites and leaves the other negated, so a
    # whole-file regex still matches and only a site-anchored arm can bite.
    # Arm 5 is the one that was SILENT on 2026-09-16 and is why the suite now
    # carries an arm per site; arm 6 is the other direction, because a fix
    # proved on one copy is not proved on the copy nobody ran it against.
    ("5. sen_payer_contracts alone goes back to `<= 0` -- the sen_pay_rates "
     "copy is left negated, so a whole-file regex still matches",
     SRC, "if (!(Number(payload.rate_per_hour) > 0)) pcProblems.push(",
     "if (Number(payload.rate_per_hour) <= 0) pcProblems.push("),
    ("6. sen_pay_rates alone goes back to `<= 0` -- the sen_payer_contracts "
     "copy is left negated, which is the same trap the other way round",
     SRC, "if (!(Number(payload.rate_per_hour) > 0)) prProblems.push(",
     "if (Number(payload.rate_per_hour) <= 0) prProblems.push("),
]

if __name__ == '__main__':
    sys.exit(run_probe(SUITE, MUTATIONS,
                       title='negative control -- api/sd-data-numeric-guards.test.js '
                             'must refuse each guard being undone'))
