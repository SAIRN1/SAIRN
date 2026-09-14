"""tests/reachability/action_demand_probe.py -- R7 can be shown to FIRE on an
action nobody asks for, and to stay quiet on one that is asked for.

    python tests/reachability/action_demand_probe.py

R7 IS R6'S INSIGHT ON A SECOND AXIS, and finding it there is why R6 was worth
generalising rather than filing. R6 asked whether a RESOURCE is asked for,
because /api/sd-data is one route carrying 385 of them. The sweep that followed
found the shape is not unique to that route: 182 individually-addressable
ACTIONS are dispatched across 27 routes, and R4 and R5 measure reachability at
the ROUTE for every one of them. api/law-auth.js alone dispatches on 19 distinct
action strings behind a single path.

THE FAILURE MODE THIS SUITE IS MOSTLY ABOUT IS THE CLOSED LOOP, exactly as for
R6. A route is where its own action strings are WRITTEN. Counting that as a
caller would make every action reachable by definition and the rung would be a
mirror. Section 2 pins the exclusion and pins that the exclusion is what makes a
finding possible.

AND THE SECOND FAILURE MODE IS THE ONE THE STANDING RULE EXISTS FOR: an admin
verb run by hand once a quarter, an OAuth callback a provider posts to, and a
seeding action used at install are quiet, correct, and indistinguishable from
dead code from inside the repo. Section 4 pins that R7 cannot gate and that its
output says so.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sairn_reachability_check as R                             # noqa: E402

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


def run_r7():
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                                     'sairn_reachability_check.py')],
                       capture_output=True, text=True, cwd=REPO)
    out = p.stdout or ''
    i = out.find('=== R7:')
    return (out[i:] if i >= 0 else ''), p.returncode


print('1. the rung runs, and says what it measured')
sect, rc = run_r7()
check('1a  R7 appears in a full run', sect != '')
check('1b  it prints BOTH denominators -- routes and actions -- so a short list '
      'cannot read as a clean tree',
      'routes dispatching on' in sect and 'individually addressable actions' in sect)
check('1c  it names the unit mismatch it exists for', 'THE UNIT IS THE ACTION' in sect)
check('1d  it states that it never gates and never suggests removal',
      'report only, never gates' in sect)
check('1e  it says what it CANNOT see, including a caller OUTSIDE this repo',
      'CANNOT SEE' in sect and 'outside this' in sect)

print('2. THE CLOSED LOOP -- a route is not its own caller')
routes = R._action_dispatch()
check('2a  the dispatch scan finds real routes with real actions',
      len(routes) >= 10 and sum(len(v) for v in routes.values()) > 100,
      '%d routes, %d actions' % (len(routes), sum(len(v) for v in routes.values())))
sample = 'api/accounting.js'
check('2b  a route under test is excluded from its own caller corpus',
      sample in routes and "'consent'" not in R._callers_excluding(sample))
own = io.open(os.path.join(REPO, sample.replace('/', os.sep)), encoding='utf-8').read()
check('2c  CONTROL: the action IS written in the route itself, so the exclusion '
      'is what makes the finding possible rather than the string being absent',
      "'consent'" in own)
check('2d  CONTROL: the corpus is not simply empty -- an action that IS asked '
      'for appears in it', "'login'" in R._callers_excluding(sample)
      or "'status'" in R._callers_excluding(sample))

print('3. FIRES on an action nobody asks for, quiet on one that is')
findings = []
for rel in sorted(routes):
    callers = R._callers_excluding(rel)
    for a in routes[rel]:
        if ("'" + a + "'") in callers or ('"' + a + '"') in callers:
            continue
        findings.append((rel, a))
check('3a  FIRES: it finds the uncalled actions', len(findings) >= 5, len(findings))
check('3b  ...including api/accounting.js consent, which no app HTML and no '
      'other api module names', ('api/accounting.js', 'consent') in findings)
check('3c  SILENT: the overwhelming majority of actions ARE named somewhere, so '
      'the rung is not reporting every action it can see',
      len(findings) < sum(len(v) for v in routes.values()) / 4,
      '%d of %d' % (len(findings), sum(len(v) for v in routes.values())))
# THE ARM THAT MATTERS FOR A ROUTE-LEVEL BLIND SPOT: a busy route with many
# actions must still be able to produce a finding. If every finding came from
# quiet routes, R7 would be measuring the same thing R4 already does.
busy = [r for r in routes if len(routes[r]) >= 5]
check('3d  the rung can see inside a BUSY route -- at least one finding comes '
      'from a route dispatching on 5 or more actions, which is the blind spot '
      'R4 and R5 cannot reach',
      any(rel in busy for rel, _ in findings),
      sorted({rel for rel, _ in findings if rel in busy}))

print('4. it cannot gate, and it invents no justifications')
check('4a  a full run still exits 0 with 17 open R7 rows -- R7 cannot change the '
      'exit code', rc == 0, 'exit %d' % rc)
check('4b  NO acknowledgement is pre-loaded: none of these routes states why its '
      'actions have no caller, and acknowledging one would mean inventing the '
      'justification', R.R7_ACKNOWLEDGED == {}, R.R7_ACKNOWLEDGED)
check('4c  ...and the output SAYS that is deliberate rather than leaving an '
      'empty section to read as nothing-to-say',
      'NONE PRE-LOADED, DELIBERATELY' in sect)
src = io.open(os.path.join(REPO, 'tools', 'sairn_reachability_check.py'),
              encoding='utf-8').read()
check('4d  a stale acknowledgement would be reported, so the mechanism is ready '
      'before the first entry rather than added with it',
      "STALE ACKNOWLEDGEMENT(S) -- the action HAS a caller now" in src)

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
