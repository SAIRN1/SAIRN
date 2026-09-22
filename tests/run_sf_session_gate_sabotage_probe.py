"""api/sd-data-sf-session-gate.test.js must REFUSE, not merely agree.

Run: python tests/run_sf_session_gate_sabotage_probe.py

# REQUIREMENT: the arm guarding eleven SAIRNfreedom resources -- a felony and
#   gambling disqualification flag on a named volunteer, minors' names, an ORC
#   2915 payee record, donor identity, a DOB, a health disclosure, and a
#   VA-adjacent referral outcome -- must go RED when any one of them loses its
#   gate, when the gate and the expectedApp map stop agreeing, when the single
#   dispatch check is duplicated, and when the batch silently widens past what
#   was actually approved

A SUITE WRITTEN IN THE SAME HOUR AS THE FIX HAS NEVER REFUSED ANYTHING, and
"it passes" is not evidence it would notice the fix being undone. That is the
whole reason this file exists rather than the six green arms being the end of
it.

SIX MUTATIONS, AND THE TWO THAT MATTER MOST ARE NOT THE OBVIOUS ONE:

MUTATION 2 IS THE ONE THAT READS AS CORRECT. It removes an expectedApp entry
while LEAVING the gate. Nothing looks unprotected -- the resource is still in
SD_SESSION_GATED, a reader scanning for "is it gated" sees yes -- and the real
effect is that expectedApp resolves to 'stonedesk', so every correctly
signed-in SAIRNfreedom caller is refused with FORBIDDEN "sign in first". It
fails CLOSED and CONFUSINGLY, which is the failure that gets a security change
reverted as broken rather than fixed forward. Only the set-equality arm can see
it.

MUTATION 6 IS THE OPPOSITE DIRECTION AND IS EASY TO MISS: the gate WIDENS to
sf_members and sf_signatures, which carry identity and were named in the
2026-09-22 finding but were NOT in the batch Michael approved. Every
"is it gated" assertion still passes; what has happened is a product decision
nobody made, taken silently. The arm that asserts their ABSENCE is what catches
it, and that arm is the one most likely to be deleted by somebody who reads it
as an odd negative.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                      # noqa: E402

SUITE = os.path.join('api', 'sd-data-sf-session-gate.test.js')
SRC = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    ("1. THE ORIGINAL STATE RESTORED for the sharpest resource: sf_operators "
     "loses its gate, so a name + DOB + a FELONY flag and a GAMBLING "
     "disqualification flag are readable and writable on a licence key that is "
     "shipped to the browser",
     SRC,
     "      'sf_operators':           ['read', 'write'],\n",
     ""),

    ("2. THE ONE THAT READS AS CORRECT: sf_youth_participants keeps its gate "
     "and loses its expectedApp entry, so it still LOOKS gated to anyone "
     "scanning for that -- and expectedApp resolves to 'stonedesk', refusing "
     "every correctly signed-in SAIRNfreedom caller with FORBIDDEN 'sign in "
     "first'. Fails closed and confusingly, which is how a security change "
     "gets reverted instead of fixed",
     SRC,
     "      'sf_youth_participants': 'sairnfreedom'\n",
     "\n"),

    ("3. MINORS LOSE THE GATE while every other resource keeps it, so the "
     "batch still looks armed and the one row of children's names does not",
     SRC,
     "      'sf_youth_participants':  ['read', 'write'],\n",
     ""),

    ("4. THE WRITE VERB IS QUIETLY DROPPED from the ORC 2915 payee record -- "
     "reads stay gated, so a caller with no session can still WRITE a "
     "charitable-gaming expense, which is the half that changes the record "
     "rather than the half that reads it",
     SRC,
     "      'sf_gaming_expenses':     ['read', 'write'],",
     "      'sf_gaming_expenses':     ['read'],"),

    ("5. THE SINGLE DISPATCH CHECK IS DUPLICATED -- a second copy is a second "
     "place for the answer to drift, and the copy that loses the read branch "
     "is the half that leaks",
     SRC,
     "    if (SD_SESSION_GATED[resource] && SD_SESSION_GATED[resource].indexOf(action) !== -1) {",
     "    if (SD_SESSION_GATED[resource] && SD_SESSION_GATED[resource].indexOf(action) !== -1) {\n"
     "      if (SD_SESSION_GATED[resource] && SD_SESSION_GATED[resource].indexOf(action) !== -1) { /* copy */ }"),

    ("6. THE OPPOSITE DIRECTION, AND EASY TO MISS: the gate WIDENS to "
     "sf_members and sf_signatures, which carry identity but were NOT in the "
     "approved batch. Every 'is it gated' assertion still passes; a product "
     "decision nobody made has been taken silently, and the open-work row now "
     "disagrees with the code",
     SRC,
     "      'sf_operators':           ['read', 'write'],",
     "      'sf_members':             ['read', 'write'],\n"
     "      'sf_signatures':          ['read', 'write'],\n"
     "      'sf_operators':           ['read', 'write'],"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title=('SAIRNfreedom: eleven resources including a felony flag, minors '
               'and an ORC 2915 payee record must require a session -- on BOTH '
               'verbs, through ONE check, with the expectedApp map agreeing'),
        # BOTH staged: the worktree is at HEAD and neither the gate nor the
        # suite is committed when this first runs, so without staging the
        # baseline measures the OLD three-resource list against the NEW suite,
        # goes red, and no mutation below would mean anything.
        stage=(SUITE, SRC)))
