"""Control for tools/assurance_case.py (item 5).

Run: python tests/run_assurance_case_probe.py

The self-check exercises the parsers on synthetic output. This checks the
things only the real tree can answer: that every evidence leaf names a tool
that EXISTS and is registered, that the case's verdict is reproducible by
re-running one leaf independently, and -- the arm that matters most -- that the
case cannot report SUPPORTED while an evidence command is failing.

AN ASSURANCE CASE THAT CANNOT SAY NO IS AN ADVERT. Every arm below is aimed at
that failure mode rather than at arithmetic.
"""
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import assurance_case as A                                       # noqa: E402

CONTROLS_FOR = ['assurance_case.py']

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


print('assurance case control\n')

# ── 1. EVERY LEAF POINTS AT SOMETHING REAL ─────────────────────────────────
leaves = [e for sg in A.ARGUMENT['subgoals'] for e in sg.get('evidence', [])]
check('the case has evidence leaves at all', len(leaves) >= 5, len(leaves))
for e in leaves:
    tool = e['cmd'][0]
    check('%s cites %s, which exists on disk' % (e['id'], tool),
          os.path.exists(os.path.join(REPO, tool)), tool)

# Every cited tool must be a REGISTERED tool, or the case is arguing from
# something nobody else knows about.
#
# THERE ARE TWO REGISTRIES AND THE FIRST VERSION OF THIS ARM KNEW ABOUT ONE.
# `PURPOSES` in tooling_inventory.py describes tools that are NOT wired into
# the report-only runner; `REGISTRY` in report_only_checks.py describes the
# ones that are, and carries its own description. A tool in both is a REFUSAL
# -- two sources that can disagree -- so checking only PURPOSES reported
# `criticality_tier_check.py` and `defect_register.py` as unregistered when
# they were registered in the other place, and "fixing" that broke the
# inventory's own closing error. Registered means EITHER, never both.
sys.path.insert(0, os.path.join(REPO, 'tools'))
import tooling_inventory as T                                    # noqa: E402
import report_only_checks as ROC                                 # noqa: E402
RUNNER = set(x['tool'] if isinstance(x, dict) else x[0] for x in ROC.REGISTRY)
for e in leaves:
    base = os.path.basename(e['cmd'][0])
    in_p, in_r = base in T.PURPOSES, base in RUNNER
    check('%s cites %s, which is registered in PURPOSES or in the runner '
          'REGISTRY' % (e['id'], base), in_p or in_r,
          'in neither registry')
    check('...and %s is not described in BOTH, which the inventory refuses'
          % base, not (in_p and in_r),
          'two descriptions that can disagree is the claim-in-two-places '
          'failure the inventory exists to prevent')

# ── 2. THE VERDICT IS REPRODUCIBLE, RE-DERIVED HERE ────────────────────────
p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'assurance_case.py'),
                    '--json'], capture_output=True, text=True, encoding='utf-8',
                   errors='replace', cwd=REPO,
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
doc = json.loads(p.stdout)
check('the case runs and emits JSON', isinstance(doc.get('subgoals'), list),
      p.stdout[:200])
dev = [g for g in doc['subgoals'] if g['verdict'] in ('SUPPORTED', 'NOT SUPPORTED')]
check('the top verdict follows its children exactly -- no partial credit',
      doc['top_verdict'] == ('SUPPORTED' if all(g['verdict'] == 'SUPPORTED'
                                                for g in dev)
                             else 'NOT SUPPORTED'),
      (doc['top_verdict'], [g['verdict'] for g in dev]))
check('...and the exit code follows the top verdict',
      (p.returncode == 0) == (doc['top_verdict'] == 'SUPPORTED'),
      (p.returncode, doc['top_verdict']))

# ── 3. THE CASE CAN SAY NO, AND DOES TODAY ─────────────────────────────────
# If every goal were supported this arm would be vacuous, and the probe says so
# rather than passing quietly.
unsupported = [g for g in doc['subgoals'] if g['verdict'] == 'NOT SUPPORTED']
check('the case is currently reporting at least one NOT SUPPORTED goal -- it '
      'is not a rubber stamp', unsupported != [],
      'every goal is supported; this arm proves nothing today and should be '
      'replaced by an injected failure')
undeveloped = [g for g in doc['subgoals'] if g['verdict'] == 'UNDEVELOPED']
check('...and it DRAWS its undeveloped goals rather than omitting them',
      undeveloped != [], [g['goal'] for g in doc['subgoals']])

# ── 4. IT CANNOT REPORT SUPPORTED WHILE A LEAF IS FAILING ──────────────────
# Injected directly, because the real tree happens to be failing today and a
# tree that is always failing would pass arm 3 for the wrong reason.
inject = {'subgoals': [{'goal': 'Z', 'claim': 'c', 'evidence': [
    {'id': 'zz', 'cmd': ['-c', 'import sys;sys.exit(3)'],
     'expect': A._exit_zero('injected failure'), 'why': 'x' * 40}]}]}
rows, top, _c = A.evaluate(inject)
check('an evidence command exiting non-zero makes its goal NOT SUPPORTED',
      top == 'NOT SUPPORTED' and rows[0]['evidence'][0]['verdict'] == 'DOES NOT SUPPORT',
      rows)
inject2 = {'subgoals': [{'goal': 'Z', 'claim': 'c', 'evidence': [
    {'id': 'zz', 'cmd': ['-c', 'import sys;sys.exit(0)'],
     'expect': A._exit_zero('injected pass'), 'why': 'x' * 40}]}]}
_r2, top2, _c2 = A.evaluate(inject2)
check('...and a passing command makes it SUPPORTED, so the verdict is not '
      'pinned', top2 == 'SUPPORTED', top2)

# A command that cannot run at all is a THIRD state, never folded into "does
# not support" -- the reader needs to know nothing was measured.
inject3 = {'subgoals': [{'goal': 'Z', 'claim': 'c', 'evidence': [
    {'id': 'zz', 'cmd': ['-c', 'import time;time.sleep(5)'],
     'expect': A._exit_zero('never gets here'), 'why': 'x' * 40}]}]}
_saved = A._run
try:
    A._run = lambda cmd, timeout=180: _saved(cmd, timeout=1)
    rows3, _t3, cnr3 = A.evaluate(inject3)
    check('an evidence command that CANNOT RUN is its own state, not a refusal',
          rows3[0]['evidence'][0]['verdict'] == 'COULD NOT RUN' and cnr3 != [],
          rows3)
finally:
    A._run = _saved

# ── 5. THE ASSUMPTIONS ARE PUBLISHED, not buried in the source ─────────────
check('the JSON carries the assumptions, so a consumer sees what the argument '
      'rests on', len(doc.get('assumptions') or []) >= 3, doc.get('assumptions'))
# ── THE LABEL CLAIMED A PER-LEAF BOUND THAT context IS NOT, FIXED 2026-09-28 ─
# It read `len(context) >= 2` under the label "the context that bounds EVERY
# LEAF". `ARGUMENT['context']` is a DOCUMENT-level scope statement -- it bounds
# the whole argument, not each evidence leaf -- so "every leaf" was a claim about
# a population this field does not range over, and a floor of 2 could not have
# checked it if it had.
#
# BOTH HALVES ARE NOW REAL, and they are separate arms because they are separate
# facts: the document-level context is PUBLISHED (a floor is the right tool -- it
# is a not-empty check and says so), and the per-leaf claim the old label implied
# is now actually made, against every leaf, with no floor.
check('the JSON publishes the document-level context that bounds the ARGUMENT '
      '-- at least two statements, a not-empty check and not a coverage claim',
      len(doc.get('context') or []) >= 2, doc.get('context'))
# THE UNIVERSE IS THE LEAVES OF *DEVELOPED* SUBGOALS, and the first version of
# this arm got that wrong and said so loudly. evaluate() emits `'evidence': []`
# for a subgoal carrying `undeveloped`, so its declared leaves never reach the
# JSON -- correctly, because an undeveloped goal has no evidence to report. An
# arm over ALL declared leaves therefore fails against a tool behaving exactly
# as designed, which is a control that punishes correct code.
#
# WHAT IS ACTUALLY WORTH PINNING is that a leaf can only disappear WITH ITS
# SUBGOAL MARKED UNDEVELOPED -- a leaf vanishing from a DEVELOPED subgoal is the
# real failure, and it is silent: the JSON would simply be shorter. A slow leaf
# is NOT an exception here: evaluate() emits it with verdict NOT RUN THIS PASS,
# so it is present and accounted for, and this arm proves that too.
_developed = [sg for sg in A.ARGUMENT['subgoals'] if 'undeveloped' not in sg]
_expect_ids = set(e['id'] for sg in _developed for e in sg.get('evidence', []))
_doc_leaf_ids = set(r.get('id') for sg in (doc.get('subgoals') or [])
                    for r in (sg.get('evidence') or []))
check('the DEVELOPED-subgoal leaf set was derived and is non-empty -- an empty '
      'universe is how the two arms below pass without checking anything',
      len(_expect_ids) >= 5, sorted(_expect_ids))
check('...and EVERY leaf of a developed subgoal reaches the published JSON, '
      'including the slow ones, which appear as NOT RUN THIS PASS rather than '
      'silently shortening the document (%d leaves)' % len(_expect_ids),
      _expect_ids - _doc_leaf_ids == set(),
      'MISSING FROM THE JSON: %s' % sorted(_expect_ids - _doc_leaf_ids))
check('...and the JSON invents no leaf the tree does not declare',
      _doc_leaf_ids - set(e['id'] for e in leaves) == set(),
      'IN THE JSON ONLY: %s'
      % sorted(_doc_leaf_ids - set(e['id'] for e in leaves)))
check('...and an UNDEVELOPED subgoal publishes an EMPTY evidence list rather '
      'than omitting the subgoal, so a consumer can see the gap',
      all((sg.get('evidence') or []) == []
          for sg in (doc.get('subgoals') or [])
          if sg.get('verdict') == 'UNDEVELOPED'),
      [sg.get('goal') for sg in (doc.get('subgoals') or [])
       if sg.get('verdict') == 'UNDEVELOPED' and (sg.get('evidence') or []) != []])

# ── ADDED 2026-09-16 BY THIS TOOL'S FIRST ARTICLE INSPECTION ────────────────
# Two claims in the header had no arm. Both are mechanically checkable, so
# neither is a `cannot-test` -- they were simply unverified, which is the state
# FAI exists to surface.
import io as _io                                                 # noqa: E402

_SRC = _io.open(os.path.join(REPO, 'tools', 'assurance_case.py'), encoding='utf-8').read()

# CLAIM: exit 2 when it could not run. Every exit-code arm above tests 0 and 1.
_saved_eval = A.evaluate
try:
    A.evaluate = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('injected'))
    check('CLAIM "exit 2 when the argument could not be evaluated": an '
          'evaluation that raises is COULD NOT RUN, not a refusal',
          A.main(['--quiet']) == 2, 'expected exit 2')
finally:
    A.evaluate = _saved_eval

# CLAIM: REPORT ONLY. Stated in the header and enforced nowhere until now.
sys.path.insert(0, os.path.join(REPO, 'tools'))
import report_only_checks as _ROC                                # noqa: E402
_RUNNER = [x['tool'] if isinstance(x, dict) else x[0] for x in _ROC.REGISTRY]
check('CLAIM "report only": assurance_case.py is NOT in the report-only RUNNER registry',
      'assurance_case.py' not in _RUNNER, _RUNNER[:4])
check('...and IS recorded as a deliberate NOT-PROMOTED decision',
      'assurance_case.py' in [x[0] for x in _ROC.NOT_PROMOTED])
_GATE = _io.open(os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py'),
                 encoding='utf-8', errors='replace').read()
check('...and the push gate does not invoke it',
      'assurance_case' not in _GATE)

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
