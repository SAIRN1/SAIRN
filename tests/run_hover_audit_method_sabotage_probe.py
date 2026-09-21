"""tests/run_defect_register_probe.py must REFUSE a broken hover-audit channel.

Run: python tests/run_hover_audit_method_sabotage_probe.py

# REQUIREMENT: the register's control must go RED when the hover auditor's
#   detection-method value is removed, when it is added with no checkpoint row
#   and therefore silently bucketed as `unknown`, when it is classed as an
#   automated checkpoint so --add demands a tool name from a role that reads
#   diffs, and when the skill's tag and the enum's value drift apart

WHAT WAS OPEN. `.claude/skills/sairn-hover-auditor/SKILL.md` has said since
2026-09-14 that `METHODS` had no `hover-audit` value, that adding one is "a
code edit this role does not make itself", and that findings needing the tag
should be HELD and the fix routed to a build agent. So the absence of one
string in a tuple was keeping real findings out of the register -- the quietest
kind of missing data there is, because nothing anywhere reported a gap: the
register was complete, --check passed, and the findings were in chat.

── WHY THE CHECKPOINT ARM MATTERS AS MUCH AS THE VALUE ────────────────────
`tool_required()` is derived from the checkpoint, so classing this role as an
automated-checker would make --add refuse every hover finding for want of a
--found-by-tool that does not exist. The value being PRESENT and the value
being USABLE are two different things, and arm 3 is the second one.

── AND THE DRIFT ARM IS THE ONE WITH A FUTURE ─────────────────────────────
The enum and the role that uses it live in different files. Arm 4 renames the
tag in the SKILL rather than in the tool, which is the direction this actually
drifts: a role rewrites its own instructions, the register is not touched, and
a hover finding is refused at the moment somebody is recording a real defect.
The control reads the skill rather than repeating the string, so it fails
instead of agreeing with itself.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'run_defect_register_probe.py')
REG = os.path.join('tools', 'defect_register.py')
SKILL = os.path.join('.claude', 'skills', 'sairn-hover-auditor', 'SKILL.md')

MUTATIONS = [
    ("1. THE VALUE IS REMOVED -- the state of this enum until 2026-09-21, in "
     "which the fifth agent's findings had nowhere to go and were held in "
     "chat instead",
     REG, "    'hover-audit',\n)", ")"),

    ("2. THE VALUE IS PRESENT WITH NO CHECKPOINT ROW -- checkpoint_of() comes "
     "back `unknown` and the record is bucketed into a column that means "
     "nothing, which is the failure the unknown state was invented to make "
     "visible",
     REG,
     "    'hover-audit': 'human-read',",
     "    'hover-audit-DISABLED': 'human-read',"),

    ("3. THE ROLE IS CLASSED AS AN AUTOMATED CHECKER -- tool_required() "
     "becomes true, so --add refuses every hover finding for want of a tool "
     "name a diff-reading role does not have",
     REG,
     "    'hover-audit': 'human-read',",
     "    'hover-audit': 'automated-checker',"),

    ("4. THE SKILL RENAMES ITS TAG AND THE ENUM IS NOT TOUCHED -- the "
     "direction this actually drifts, and the arm reads the skill rather than "
     "repeating the string so it cannot agree with itself",
     SKILL,
     'detection_method hover-audit',
     'detection_method hover-review'),
]

sys.exit(run_probe(
    SUITE, MUTATIONS,
    title="SAIRN: the hover auditor's findings must have a detection-method "
          'value that EXISTS, is checkpointed as a human read, and still '
          'matches the tag its own skill tells it to use',
    stage=(REG, SKILL),
))
