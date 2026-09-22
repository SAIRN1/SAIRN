"""tests/claims/run_fileset_matcher_probe.py must REFUSE, not merely agree.

Run: python tests/claims/run_fileset_matcher_sabotage_probe.py

# REQUIREMENT: the suite guarding the file-set matcher must go RED when the
#   file check stops deciding, when a missing declaration is folded into CLEAR
#   instead of falling back to the lexical rule, when an intersection stops
#   refusing, when a disjoint pair stops clearing, when the demoted lexical
#   match stops being printed, and when the separator normalisation is dropped

WHAT THIS CHANGE DID, and the sabotage arms are aimed at each half separately.
`block_reason()` answers "do these two strings talk about the same thing" -- a
proxy for "would these two sessions edit the same file". Claims now declare
`FILES:`, so the real question is answerable, and the primary check became the
file-set intersection with the lexical rule demoted to a warning.

MEASURED over 318 cross-session pairs among the claims that declare files: 153
blocked, 43 with intersecting files (kept), 110 with disjoint files (cleared).

── THE ARM THAT MATTERS MOST IS 2, NOT 1 ──────────────────────────────────
Arm 1 turns the file check off, which every arm notices. Arm 2 changes ONE
line -- `a is None or b is None` becomes `not a or not b`, then returns 'clear'
-- so a claim that declares no files stops falling back to the lexical matcher
and is silently cleared instead. 774 of the 805 claims in the record declare
nothing, so that single character is the difference between a narrower matcher
and no matcher at all for 96% of the corpus. It is the could-not-tell-folded-
into-a-pass shape this platform records more than any other, and it is exactly
what a reviewer skims past.

── AND ARM 4 IS WHY ARM 3 IS NOT ENOUGH ───────────────────────────────────
Refusing every pair would satisfy "an intersection still refuses" and undo the
entire change. Arm 4 makes disjoint sets refuse too, and the suite has to
notice that the 110 stopped clearing.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'claims', 'run_fileset_matcher_probe.py')
TOOL = os.path.join('tools', 'sairn_claim.py')

MUTATIONS = [
    ("1. THE FILE CHECK STOPS DECIDING -- every verdict falls back to the word "
     "matcher, which is the state that produced 110 false blocks and cost two "
     "sessions three collisions each in one night",
     TOOL,
     "        fv, fshared = file_verdict(task, c.get('task'))",
     "        fv, fshared = 'unknown', set()"),

    ("2. A MISSING DECLARATION IS FOLDED INTO CLEAR instead of falling back to "
     "the lexical rule -- one line, and the matcher stops existing for the 774 "
     "claims of 805 that declare no files",
     TOOL,
     "    if a is None or b is None:\n        return 'unknown', set()",
     "    if a is None or b is None:\n        return 'clear', set()"),

    ("3. AN INTERSECTION STOPS REFUSING -- the strongest signal the tool has is "
     "computed and then ignored, and two sessions edit one file",
     TOOL,
     "    return ('refuse' if shared else 'clear'), shared",
     "    return 'clear', shared"),

    ("4. DISJOINT SETS REFUSE TOO -- every arm about a real collision still "
     "passes and the whole change is undone, which is what a blanket refusal "
     "always looks like from the blocking side",
     TOOL,
     "    return ('refuse' if shared else 'clear'), shared",
     "    return 'refuse', shared"),

    ("5. THE DEMOTED LEXICAL MATCH STOPS BEING PRINTED -- the block is dropped "
     "AND the reason for it disappears, so a matcher that went quiet says "
     "nothing about having done so",
     TOOL,
     "            weak.append((c, shared, 'LEXICAL ONLY -- ' + reason\n"
     "                         + '; the declared file sets are DISJOINT'))\n"
     "            continue",
     "            continue"),

    ("6. THE SEPARATOR NORMALISATION IS DROPPED -- one clone writing "
     "docs\\\\x.json and another writing docs/x.json no longer share a file, "
     "which is a false CLEAR on a real collision and the direction that costs "
     "hours rather than seconds",
     TOOL,
     "    found = {f.replace('\\\\', '/') for f in FILE_TOKEN.findall(m.group(1))}",
     "    found = set(FILE_TOKEN.findall(m.group(1)))"),
]

sys.exit(run_probe(
    SUITE, MUTATIONS,
    title='SAIRN: the claim matcher must decide on the DECLARED FILE SET, fall '
          'back to the word matcher when either side declares none, and say so '
          'either way',
    stage=(TOOL,),
))
