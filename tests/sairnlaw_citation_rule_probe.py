"""tests/sairnlaw_citation_rule.js must go RED when the converged rule is undone.

Run: python tests/sairnlaw_citation_rule_probe.py

WHY THIS CONTROL AND WHY IMMEDIATELY. The suite it guards was written in the
same hour as the fix it pins, which is the one moment a suite has never been
watched go red -- and a citation rule that quietly stops being enforced is the
exact failure it exists to prevent. `tools/ai_prompt_refusal_check.py` REPORTED
this divergence for days and nothing failed, because it can see whether a call
site references a rule constant and cannot read what the constant SAYS.

MUTATION 1 IS THE REGRESSION ITSELF, BYTE FOR BYTE: the old
MT_CRITIQUE_CITATION_RULE, restored verbatim from the version this fix
replaced. It told the model *"If you cite a case, give its real reporter
citation"* -- generation, licensed by a post-hoc badge. If that can come back
green, the suite is decoration.

ONE PROPERTY PER MUTATION, and the last is the other direction: a suite made of
prohibitions is one a page with no AI at all would satisfy, so mutation 6
removes the BACKSTOP rather than the rule and must still bite.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'sairnlaw_citation_rule.js')
SRC = 'sairnlaw.html'

OLD_PERMISSIVE = (
    "var MT_CRITIQUE_CITATION_RULE='If you cite a case, give its real reporter "
    "citation and do not invent one. If you are not confident a citation is real, "
    "describe the principle without a citation instead. Every citation you produce "
    "here is checked automatically against a real case reporter after you answer and "
    "is shown to the user marked verified or unverified, so a fabricated one will be "
    "visible as such -- it will not pass unnoticed. This is a practice/training "
    "surface; it is the one place in this application permitted to emit a citation in "
    "citable-reference format, and the user is told to confirm anything not marked "
    "verified before relying on it.';")

MUTATIONS = [
    # THE REGRESSION, RESTORED VERBATIM. This is the state the tree was in
    # before 2026-09-17 and the one arm 2 exists for.
    ("1. the withdrawn permission comes back -- the critique step is told to "
     "give a real reporter citation again",
     SRC, "var MT_CRITIQUE_CITATION_RULE='CITATION RULE FOR THIS STEP:",
     OLD_PERMISSIVE + "\nvar _MT_DEAD_CRITIQUE_RULE='CITATION RULE FOR THIS STEP:"),
    ("2. the critique rule loses its prohibition and only offers advice",
     SRC, 'do not generate a case citation, statute citation or docket number in '
          'citable-reference format (the volume/reporter/page/year pattern, e.g. '
          '"384 U.S. 436 (1966)"',
     'prefer not to lean on a case citation, statute citation or docket number in '
     'citable-reference format (the volume/reporter/page/year pattern, e.g. '
     '"384 U.S. 436 (1966)"'),
    # The verbatim carve-out is what keeps the rule usable. Removing it makes
    # the rule stricter, which a suite of prohibitions would happily accept --
    # so the arm that requires it is the one that stops the rule being turned
    # into something that breaks the feature.
    ("3. the decomposition rule loses its verbatim carve-out, so it forbids "
     "even repeating what the user wrote",
     SRC, "You MAY repeat such a string back if -- and only if -- it appears "
          "verbatim in the position the user wrote",
     "You may not repeat such a string back under any circumstance in the position "
     "the user wrote"),
    ("4. document review stops carrying LAW_CITATION_RULE -- a work-product "
     "surface with no citation rule at all",
     SRC, "'You are reviewing a legal document for a law firm. Give specific, "
          "actionable feedback (clarity, structure, missing elements, risk flags) "
          "-- do not rewrite the whole document unless asked. '+LAW_CITATION_RULE",
     "'You are reviewing a legal document for a law firm. Give specific, "
     "actionable feedback (clarity, structure, missing elements, risk flags) "
     "-- do not rewrite the whole document unless asked. '"),
    ("5. the panel stops promising it -- the user-facing claim and the rule "
     "part company",
     SRC, "never presents an unverified case citation",
     "presents case citations for reference"),
    # ── THE OTHER DIRECTION ────────────────────────────────────────────────
    # Everything above breaks a PROHIBITION, and a page that forbade everything
    # would pass all of them. This one removes the mechanical check instead: the
    # rule stays perfect and the backstop is gone.
    # ANCHORED ON THE CRITIQUE'S OWN CALL. The first version of this arm
    # mutated `mtVerifyCitations(claimCites)` -- which is the DECOMPOSE path's
    # verification, three hundred lines earlier -- and came back SILENT. Two
    # paths call the same verifier for different outputs, and a control that
    # breaks the wrong one proves nothing about the path it names.
    ("6. the critique path stops verifying its output -- the rule is intact "
     "and nothing checks it any more",
     SRC, "      mtVerifyCitations(cites).then(function (checked) {",
     "      Promise.resolve(cites).then(function (checked) {"),
]

if __name__ == '__main__':
    # sairnlaw.html IS STAGED FROM THIS CLONE, not taken from HEAD. The fix this
    # control is written against is not committed at the moment it first runs,
    # and a worktree at HEAD carries the OLD permissive rule -- so the baseline
    # went red for a reason with nothing to do with the subject. That is the
    # case the harness's `stage` argument exists for, and running the control
    # only after its fix had landed would be the wrong order: the control is
    # what says the suite bites.
    sys.exit(run_probe(SUITE, MUTATIONS, stage=(SRC,),
                       title='negative control -- tests/sairnlaw_citation_rule.js must '
                             'refuse each way the converged citation rule can be undone'))
