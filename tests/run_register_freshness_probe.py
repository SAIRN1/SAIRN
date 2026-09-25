"""tools/register_freshness_check.py must CATCH drift, refuse a vacuous clean,
and never repair its subject to make its own comparison pass.

Run: python tests/run_register_freshness_probe.py

The tool's own --fixtures lock the per-citation criteria (both directions,
including the UNVERIFIABLE third state). What THIS probe adds is what a
self-carried lock cannot: the CLI's exit-code contract driven end to end
against fixture registers, and a SABOTAGE arm proving the comparator can be
broken and the fixtures notice -- a lock that cannot fail is a lock in name.
"""
CONTROLS_FOR = ['register_freshness_check.py']

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import register_freshness_check as S    # noqa: E402
TOOL = os.path.join(REPO, 'tools', 'register_freshness_check.py')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '  ' + str(detail)[:220]))
    if not cond:
        fails.append(name)


WORK = tempfile.mkdtemp(prefix='regfresh-probe-')


def make_tree(n, tiers_row=None, reviews=None, app_lines=30, fn_line=20,
              tool_src=None):
    root = os.path.join(WORK, 'tree%d' % n)
    os.makedirs(os.path.join(root, 'tools'))
    os.makedirs(os.path.join(root, 'docs'))
    src = ['// filler'] * app_lines
    src[fn_line - 1] = 'function realThing() {'
    io.open(os.path.join(root, 'app.js'), 'w', encoding='utf-8',
            newline='\n').write('\n'.join(src))
    io.open(os.path.join(root, 'tools', 'register_freshness_check.py'), 'w',
            encoding='utf-8', newline='').write(
        tool_src or io.open(TOOL, encoding='utf-8', newline='').read())
    if tiers_row is not None:
        io.open(os.path.join(root, 'docs', 'CRITICALITY-TIERS.md'), 'w',
                encoding='utf-8', newline='\n').write(
            '| Resource | Tier | Confidentiality | W | R | Evidence |\n'
            '|---|---|---|---|---|---|\n' + tiers_row + '\n')
    if reviews is not None:
        io.open(os.path.join(root, 'docs', 'tier-a-reviews.json'), 'w',
                encoding='utf-8', newline='\n').write(json.dumps(reviews))
    return root


def run_in(root):
    r = subprocess.run([sys.executable,
                        os.path.join(root, 'tools', 'register_freshness_check.py')],
                       cwd=root, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


ROW_OK = '| `fx_res` | **A** | **B** | w | r | the gate `realThing()` at `app.js:20` holds |'
ROW_DRIFT = '| `fx_res` | **A** | **B** | w | r | the gate `realThing()` at `app.js:5` holds |'

print('register freshness -- the checker must catch drift, not certify it\n')

rc, out = run_in(make_tree(1, tiers_row=ROW_OK,
                           reviews={'records': []}))
check('a register whose one citation is TRUE is exit 0', rc == 0, 'rc=%s' % rc)

rc, out = run_in(make_tree(2, tiers_row=ROW_DRIFT, reviews={'records': []}))
check('a DRIFTED citation is exit 1 and names the cell, the cite and where '
      'the identifier went',
      rc == 1 and 'fx_res' in out and 'line(s) 20' in out, 'rc=%s' % rc)

rc, out = run_in(make_tree(3, tiers_row=None, reviews=None))
check('BOTH registers absent is exit 2 COULD NOT TELL, never 0',
      rc == 2, 'rc=%s' % rc)

rc, out = run_in(make_tree(4,
    tiers_row='| `fx_res` | **A** | **B** | w | r | prose with no citation at all |',
    reviews={'records': []}))
check('registers present but ZERO checkable citations is exit 2 -- nothing '
      'measured must never read as all-clean',
      rc == 2 and 'ZERO checkable' in out, 'rc=%s' % rc)

rc, out = run_in(make_tree(5, tiers_row=ROW_OK, reviews={'records': [
    {'author_session': 'x', 'opened_at': 'T1',
     'files': ['ghost.js'], 'what': '', 'verdict': ''}]}))
check('a review record whose files[] pointer is GONE is exit 1 naming it',
      rc == 1 and 'ghost.js' in out, 'rc=%s' % rc)

rc, out = run_in(make_tree(6, tiers_row=ROW_OK, reviews={'records': [
    {'author_session': 'x', 'opened_at': 'T1',
     'files': ['app.js'], 'what': 'fixed in deadbeef99', 'verdict': ''}]}))
check('a prose sha that does not resolve is exit 1 (this fixture tree is not '
      'a git repo, so ANY sha fails -- which is the point being driven)',
      rc == 1 and 'deadbeef99' in out, 'rc=%s' % rc)


# ── THE DEAD-FUNCTION ARM, AND THE HOUR IT WAS BLIND (2026-09-25) ───────────
# check_dead_functions() reports a cell naming a function that exists in NONE
# of the files it cites. Its exclusion asks "does this name exist anywhere in
# the app sources" so a cross-app precedent (`sbThreeWayMatch`, real, in
# sairnbiz.html, cited by bld_deliveries) is not reported.
#
# THE FIRST VERSION SEARCHED EVERY TRACKED .py TOO -- INCLUDING ITS OWN
# SOURCE -- and its comment block names `saveTimeEntry()` as the defect it
# was built to catch. So the check was SILENT on the exact case it exists
# for: the documentation of a dead function kept that function alive. Found
# by an adversarial pass planting names through it, not by review. These arms
# drive the planted cases so it cannot go blind that way again.
def dead_function_arm():
    pc = {}
    known = {'sdn_timeentries', 'bld_deliveries'}

    def reports(ev):
        return bool(S.check_dead_functions('fx', ev, pc, known))

    check('THE ORIGINAL DEFECT: a cell naming `saveTimeEntry()` -- renamed to '
          'saveTime() -- REPORTS. The tool\'s own docstring names it, and for '
          'an hour that kept it alive',
          reports("`saveTimeEntry()` at `sairndesign.html:10`"))
    check('a name that exists NOWHERE at all reports',
          reports("`definitelyNotARealFunctionXyz()` at `sairndesign.html:10`"))
    check('CONTROL: the REAL function in that file is silent -- else the arm '
          'above passes by reporting everything',
          not reports("`saveTime()` at `sairndesign.html:10`"))
    check('CONTROL: a cross-app precedent is silent, which is the whole '
          'reason the exclusion exists',
          not reports("`sbThreeWayMatch()` at `sairndesign.html:10`"))
    check('a snake_case name written with () still reports -- the '
          'function-shape narrowing is about the CALL form, not only camelCase',
          reports("`save_time_entry()` at `sairndesign.html:10`"))
    check('a registered RESOURCE name is never treated as a function',
          not reports("`sdn_timeentries` at `sairndesign.html:10`"))
    check('THE SELF-REFERENCE GUARD: the exclusion does not search tools/ or '
          'tests/, so a tool naming a function in prose cannot keep it alive',
          not S._exists_anywhere('definitelyNotARealFunctionXyz')
          and S._exists_anywhere('saveTime'))


dead_function_arm()

# ── SABOTAGE: break the comparator, the fixture lock must refuse to judge ────
src = io.open(TOOL, encoding='utf-8', newline='').read()
anchor = 'IDENT_WINDOW = 8'
assert src.count(anchor) == 1, 'sabotage anchor stale'
mutated = src.replace(anchor, 'IDENT_WINDOW = 100000')
rc, out = run_in(make_tree(7, tiers_row=ROW_DRIFT, reviews={'records': []},
                           tool_src=mutated))
check('SABOTAGE: widening the window to the whole file (drift becomes '
      'invisible) is caught by the tool\'s own fixture lock BEFORE anything '
      'real is judged -- exit 2, not a clean 0',
      rc == 2 and 'FIXTURE LOCK FAILED' in out, 'rc=%s out=%s' % (rc, out[:150]))

# the never-repair property, asserted on source rather than behaviour: the
# tool must not open either register for writing.
check('the tool never opens a register for WRITING -- compare, never '
      'regenerate-then-pass',
      not re.search(r"open\([^)]*(TIERS|REVIEWS)[^)]*['\"]w", src)
      and "io.open(TIERS, 'w'" not in src and "io.open(REVIEWS, 'w'" not in src)

shutil.rmtree(WORK, ignore_errors=True)
check('the probe removed its fixture trees -- item 34, no leaked temporary '
      'state', not os.path.exists(WORK))

print('')
if fails:
    print('FAILED  run_register_freshness_probe: %d failed' % len(fails))
    sys.exit(1)
print('ok  run_register_freshness_probe: 0 failed')
sys.exit(0)
