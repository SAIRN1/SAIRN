# REQUIREMENT: a write whose promise is dropped and whose caller then raises a
#   toast is REPORTED, and a caller that takes the result in any of the ways
#   this platform really writes -- await, assignment, return, .then, an
#   argument, an array element -- is not
#
"""Control for tools/optimistic_success_scan.py.

    python tests/run_optimistic_success_probe.py

The tool exists because `write_path_fault_scan.py` matched the DATA WRAPPER by
name and therefore could not see a dropped LOCAL HELPER -- sairngrounds reported
clean while announcing "Point captured" for writes that never left the device.

So the failure this probe guards against is the same one, one level further
out: a rule that is too narrow reports a clean app, and a rule that is too wide
reports correct code as broken and gets switched off. Both directions are
driven, and section 3 holds the four widenings that were made only AFTER a real
sweep showed each one firing on code that was right.
"""
CONTROLS_FOR = ['optimistic_success_scan.py']

import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import optimistic_success_scan as S                              # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


WRAP = "async function xData(op,res,row){ return fetch('/x'); }\n"
HELP = "async function saveThing(z){ return await xData('write','t',z); }\n"


def n(body):
    return len(S.scan(WRAP + HELP + 'async function f(){' + body + '}'))


print('\n1. THE TOOL\'S OWN BLIND LOCK RUNS IN THE SUITE')
lines, bad = S.fixtures()
check('every fixture arm passes', bad == 0,
      [l for l in lines if l.startswith('  FAIL')])
check('the lock is not empty', len(lines) >= 8, len(lines))

print('\n2. THE SHAPE IS FOUND')
check('a dropped helper then a toast is a candidate',
      n(" saveThing(z); toast('done'); ") == 1)
check('the DATA WRAPPER dropped directly is a candidate too, so the narrower '
      'tool\'s whole population is still covered',
      n(" xData('write','t',z); toast('done'); ") == 1)
check('a dropped call inside a callback still counts -- a forEach is where the '
      'sairndental purchase-order archive hid',
      n(" [1,2].forEach(function(z){ saveThing(z); }); toast('done'); ") == 1)

print('\n3. THE FOUR WIDENINGS, EACH ADDED AFTER IT FIRED ON CORRECT CODE')
check('await takes the result', n(" await saveThing(z); toast('done'); ") == 0)
check('assignment takes the result', n(" var p=saveThing(z); toast('done'); ") == 0)
check('return takes the result', n(" return saveThing(z); ") == 0)
check('a .then chain takes the result -- nothing precedes the call, so a rule '
      'looking only BACKWARDS called it dropped',
      n(" saveThing(z).then(function(r){}); toast('done'); ") == 0)
check('an ARGUMENT takes the result. `Promise.resolve(f(x))` was reported as '
      'dropped on the very code that had just been fixed',
      n(" Promise.resolve(saveThing(z)); toast('done'); ") == 0)
check('...and so does `arr.push(f(x))`',
      n(" pushes.push(saveThing(z)); toast('done'); ") == 0)
check('an ARRAY ELEMENT takes the result -- three sairngrounds hits were an '
      'awaited Promise.all whose elements the rule could not see',
      n(" await Promise.all([saveThing(a),saveThing(b)]); toast('done'); ") == 0)

print('\n4. IT IS ABOUT THE CLAIM, NOT THE DROP')
check('CONTROL: a dropped write with NO toast is not a candidate',
      n(" saveThing(z); ") == 0)
check('CONTROL: a toast BEFORE the call is not a claim about it',
      n(" toast('Saving...'); saveThing(z); ") == 0)
check('CONTROL: a non-write helper is not a write helper',
      len(S.scan(WRAP + "async function readThing(z){ return await xData('read','t',z); }\n"
                 + "async function f(){ readThing(z); toast('loaded'); }")) == 0)
check('CONTROL: a commented-out call is not a call',
      len(S.scan(WRAP + HELP + 'async function f(){\n  // saveThing(z);\n'
                 + "  toast('done');\n}")) == 0)
check('CONTROL: the helper does not report ITSELF -- the write inside it is '
      'the thing it is supposed to do',
      len(S.scan(WRAP + "async function saveThing(z){ var r=await xData('write','t',z); "
                 + "toast('saved'); return r; }")) == 0)

print('\n5. THE REAL APPS, AND THE THREE FIXES HOLD')
real = {}
for app in ('sairndental.html', 'sairndesign.html', 'sairngrounds.html'):
    src = io.open(os.path.join(REPO, app), encoding='utf-8',
                  errors='replace').read()
    real[app] = S.scan(src)
callers = {app: {c for c, _h, _l, _m in hits} for app, hits in real.items()}
check('sairndental addSupply no longer drops its push -- the fix that started '
      'this sweep', 'addSupply' not in callers['sairndental.html'],
      sorted(callers['sairndental.html']))
check('sairndental vPlaceOrder no longer drops its per-vendor pushes',
      'vPlaceOrder' not in callers['sairndental.html'],
      sorted(callers['sairndental.html']))
check('sairndesign markRoomARPoint no longer drops saveRoomDimensions',
      'markRoomARPoint' not in callers['sairndesign.html'],
      sorted(callers['sairndesign.html']))
check('sairndesign saveRoomDimensions RETURNS whether it synced, or no caller '
      'could condition anything on it',
      'return !!syncResult' in io.open(
          os.path.join(REPO, 'sairndesign.html'), encoding='utf-8',
          errors='replace').read())
check('CONTROL: the scanner still finds SOMETHING in these apps, so the three '
      'arms above are not passing because it stopped looking',
      sum(len(v) for v in real.values()) > 0,
      {k: len(v) for k, v in real.items()})
check('the sairngrounds gcdSaveRound callers are STILL reported -- they are an '
      'accepted decision recorded at the site, and a tool that learned to hide '
      'them would hide the next one too',
      any(c.startswith('gcd') for c in callers['sairngrounds.html']),
      sorted(callers['sairngrounds.html']))

print('\n6. IT REFUSES TO REPORT A VERDICT IT CANNOT SUPPORT')
src_tool = io.open(os.path.join(REPO, 'tools', 'optimistic_success_scan.py'),
                   encoding='utf-8', errors='replace').read()
check('the output says these are CANDIDATES and not defects',
      'CANDIDATES, NOT DEFECTS' in src_tool)
check('...and that a clean run is a FLOOR because it follows one hop',
      'FLOOR, NOT A CLEARANCE' in src_tool)
check('...and it names the branch false positive with a MEASURED number rather '
      'than as a caveat', 'dominant false positive' in src_tool.lower()
      and 'FOUR were this shape' in src_tool,
      [l.strip()[:70] for l in src_tool.splitlines()
       if 'false positive' in l.lower()][:3])
check('CONTROL: no word list decides whether a message reads as success -- that '
      'would be wrong in both directions and is why the rule is structural',
      'success' not in src_tool.lower().split('def scan')[1].split('def ')[0])

# ── ADDED 2026-09-16 BY THIS TOOL'S FIRST ARTICLE INSPECTION ────────────────
# THE SAME TWO CLAIMS, A FOURTH TIME. assurance_case.py, risk_event_tree.py and
# dora_metrics.py each stated an exit-2 COULD-NOT-RUN contract and a REPORT ONLY
# contract with no arm for either; so does this one. Four tools by two sessions
# is a habit, not a coincidence: the interesting exits carry a verdict, and the
# exit that carries none is the one nobody writes a test for.
import subprocess as _sp                                         # noqa: E402

# CLAIM: exit 2 when the fixture lock fails -- "no app was read", which must not
# be reachable as a clean run.
_saved_fix = S.fixtures
try:
    S.fixtures = lambda: (['injected lock failure'], ['broken'])
    check('CLAIM "exit 2": a FAILED FIXTURE LOCK is COULD-NOT-RUN, never a '
          'clean scan', S.main([]) == 2, 'expected exit 2')
finally:
    S.fixtures = _saved_fix

# CLAIM: exit 2 when no app could be listed. A zero-length target list with a
# passing lock would otherwise report "nothing found" on an empty sweep.
_saved_apps = S.apps
try:
    S.apps = lambda: []
    check('CLAIM "exit 2": NO APPS LISTED is COULD-NOT-RUN, not a clean sweep '
          'over zero files', S.main([]) == 2, 'expected exit 2')
finally:
    S.apps = _saved_apps

# CLAIM: REPORT ONLY -- every hit needs a human.
sys.path.insert(0, os.path.join(REPO, 'tools'))
import report_only_checks as _ROC                                # noqa: E402
_RUNNER = [x['tool'] if isinstance(x, dict) else x[0] for x in _ROC.REGISTRY]
check('CLAIM "report only": optimistic_success_scan.py is NOT in the '
      'report-only RUNNER registry',
      'optimistic_success_scan.py' not in _RUNNER, _RUNNER[:4])
check('...and IS recorded as a deliberate NOT-PROMOTED decision',
      'optimistic_success_scan.py' in [x[0] for x in _ROC.NOT_PROMOTED])
_GATE = io.open(os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py'),
                encoding='utf-8', errors='replace').read()
check('...and the push gate does not invoke it',
      'optimistic_success_scan' not in _GATE)

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
