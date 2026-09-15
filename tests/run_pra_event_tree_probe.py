"""tests/run_pra_event_tree_probe.py -- item 84's event tree can be shown to
DISCRIMINATE, and to refuse the number it must not invent.

    python tests/run_pra_event_tree_probe.py

THE TWO WAYS A RISK ANALYSIS GOES WRONG HERE, and they are not symmetric:

  * IT INVENTS A NUMBER. A probabilistic risk assessment classically multiplies
    a frequency by a consequence. There is no defensible frequency on this
    platform -- the defect register counts DEFECTS FOUND IN CODE over six days,
    a different population from component failures in production, bounded by
    how hard anyone looked. Section 2 pins that the tool refuses, in the report
    AND in the JSON, and that nothing multiplies a tier by anything.

  * IT LOOKS LIKE STRUCTURE AND IS NOT. An event tree whose branches all
    resolve the same way still prints eight end states and occupies one, and a
    reader who does not notice reads structure that is not there. Section 3
    pins that a constant branch is REPORTED as constant -- and that the tree
    genuinely discriminates on the real input set, which it did not until the
    unguarded secrets were added as initiating events.
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import pra_event_tree as P                                       # noqa: E402

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


print('1. the blind lock, and the ordering claim it protects')
check('1a  every end-state fixture classifies as written', P.run_fixtures() == [],
      P.run_fixtures())
check('1b  all eight combinations of three binaries have a NAMED end state -- a '
      'gap would silently drop a reachable outcome', len(P.END_STATES) == 8)
check('1c  the worst state is the all-silent one, NOT the one with the most '
      'failed branches',
      'WORST REACHABLE STATE' in P.END_STATES[(False, False, False)][1])
check('1d  CONTROL: a two-failure state is explicitly NOT the worst, so the '
      'table is not a severity ladder in disguise',
      'WORST' not in P.END_STATES[(False, True, False)][1])
check('1e  every end state is NAMED rather than numbered -- "state 6" is not '
      'something a reader can argue with',
      all(v[0] and not v[0][0].isdigit() for v in P.END_STATES.values()))

print('2. the number it refuses to invent')
r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'pra_event_tree.py')],
                   capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
out = r.stdout or ''
check('2a  the report says FREQUENCY: UNKNOWN', 'FREQUENCY: UNKNOWN' in out)
check('2b  ...and says WHY, naming the population problem rather than just '
      'declining', 'different population' in out and 'six days is not a rate' in out.lower())
check('2c  the end state and the tier are stated as reported SEPARATELY',
      'never multiplied' in out or 'SEPARATELY' in out)
j = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'pra_event_tree.py'),
                    '--json'], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
check('2d  the JSON carries frequency: null -- a consumer cannot pick up a '
      'number the report declined to give', '"frequency": null' in (j.stdout or ''))
# THE ARM LOOKS FOR A SCORE, NOT FOR THE WORD. The first version matched
# /risk.score/ anywhere and failed on the report's own sentence explaining why
# there is no score -- a check firing on its own documentation, which is the
# same defect the secrets inventory hit on delete grants. It now looks for a
# score with a VALUE: a JSON key containing "score", or a printed "score: <n>".
check('2e  no risk SCORE with a VALUE appears anywhere -- a single fused figure '
      'is the shape this refuses. (The report may SAY the word while explaining '
      'the refusal; a check that fires on its own documentation is one nobody keeps)',
      not re.search(r'"[a-z_]*score[a-z_]*"\s*:', j.stdout or '', re.I)
      and not re.search(r'score\s*[:=]\s*[0-9]', out, re.I))

print('3. it discriminates, and says so when it does not')
check('3a  more than one end state is occupied on the real input set -- until '
      'the unguarded secrets were added as initiating events, every component '
      'landed in one and the tree was a shape rather than a result',
      len(re.findall(r'^  [A-Z][A-Z, ]+\s+\(\d+\)$', out, re.M)) >= 2,
      re.findall(r'^  ([A-Z][A-Z, ]+)\s+\(\d+\)$', out, re.M))
check('3b  a branch that took ONE value on this input set is reported as such',
      'DID NOT DISCRIMINATE' in out)
check('3c  ...and it names WHICH branch and how many events, so the reader can '
      'weigh it', re.search(r'is (True|False) for every one of the \d+ initiating', out) is not None)
check('3d  the KIND is printed beside the end state -- a TUNING value with a '
      'documented default in the worst state is the default working, and '
      'reporting it like a credential would be the analysis misleading',
      'READ THE KIND COLUMN' in out)

print('4. the inputs are read, not restated')
check('4a  the audit tables come from api/audit-checkpoint.js, so the two cannot drift',
      P.audit_tables() == {'sairnlaw_audit_log', 'sairncode_audit_log', 'stonedesk_audit_log'},
      sorted(P.audit_tables()))
check('4b  the tiers come from docs/CRITICALITY-TIERS.md and there are real ones',
      len(P.tiers()) > 300 and 'A' in set(P.tiers().values()), len(P.tiers()))
check('4c  the initiating events come from docs/SPOF-REGISTER.md, which is '
      'itself checked against the live graph by dependency_graph --register',
      len(P.spof_components()) >= 5, len(P.spof_components()))
check('4d  the header states the split between the two initiating-event sources '
      'rather than attributing all of them to the register -- the first version '
      'of this line said "the 20 components in docs/SPOF-REGISTER.md", which was '
      'false the moment the second source was added',
      'from docs/SECRETS-INVENTORY.md with NO GUARD FOUND' in out)

print('5. it says what it cannot see')
src = open(os.path.join(REPO, 'tools', 'pra_event_tree.py'), encoding='utf-8').read()
check('5a  it states that a component PRESENT AND WRONG is the FMEA\'s question, '
      'not this one -- the two tools do not overlap by accident',
      'present and WRONG is the FMEA' in src)
check('5b  ...and that it enumerates what is REACHABLE, which is about structure '
      'and not about history', 'statement about structure, not about history' in src)

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
