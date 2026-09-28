#!/usr/bin/env python
"""The control for tools/entry_point_scope_check.py -- BOTH directions.

    python tests/run_entry_point_scope_probe.py

Exit 0 all arms pass, 1 any arm fails.

── THE ARM THAT MATTERS: A CLEAN SWEEP FROM THIS TOOL IS WORTH NOTHING ─────
The tool reports CLEAN over tools/ today. A checker that has never been seen to
FIRE on the real defect it was built for is a checker whose clean line is
evidence for the wrong conclusion -- and this one has already reported a
worthless clean sweep once, in its own first version, for exactly that reason
(see section C).

So section B RESTORES THE REAL PRE-FIX SHAPE of tools/tier_a_review_gate.py --
the defect this tool exists for, as it actually stood on 2026-09-27 -- and
demands the tool report it. Nothing on disk is mutated: the pre-fix shape is
reconstructed as a source STRING and classified in process.

── AND THE TWO FALSE POSITIVES THE REAL RUNS PAID FOR ──────────────────────
Section C pins both, because both were real findings the tool printed about
correct code, and a control that only proves a checker fires is half a control:

  1. SHARED SETUP. probe_selector.py calls corpus_probes() BEFORE its `--all`
     branch, and the first version attributed that to the bare run alone -- so
     two doors going through the same setup read as two different populations.
  2. TWO DOORS, TWO QUESTIONS. tier_a_review_gate's `--list` reads the review
     ledger and no scope accessor at all. It is not DISAGREEING about scope; it
     is answering a different question, which a tool is allowed to do.

Both are now fixtures inside the tool AND arms here, because a fixture proves
the criterion and an arm proves the criterion is the one the tool ships.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
TOOL = os.path.join(REPO, 'tools', 'entry_point_scope_check.py')
CONTROLS_FOR = ['entry_point_scope_check.py']

import entry_point_scope_check as E                              # noqa: E402

_pass, _fail = 0, 0


def check(name, cond, detail=''):
    global _pass, _fail
    if cond:
        print('  ok   ' + name)
        _pass += 1
    else:
        print('  FAIL ' + name)
        if detail != '':
            print('       %s' % (detail,))
        _fail += 1


def section(t):
    print('\n' + t)


def run(*args):
    r = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                PYTHONUTF8='1'))
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('ENTRY-POINT SCOPE DIVERGENCE -- the control for the checker')

# ── A. THE CRITERIA LOCK GATES THE RUN ──────────────────────────────────────
section('A. break a criterion and the tool must REFUSE, not report clean')
rc, out = run('--fixtures')
check('A1. the lock passes on the shipped criteria and says how many fixtures',
      rc == 0 and 'criteria lock:' in out, (rc, out[-300:]))
check('A1b. ...and there are enough of them that A1 is not vacuous',
      len(E.FIXTURES) >= 8, len(E.FIXTURES))

_real_families = E.FAMILIES
try:
    # SABOTAGE: collapse every family to one empty tuple. No family can then
    # contain two differing members, so nothing can ever be a finding.
    E.FAMILIES = {'none': ()}
    check('A2a. THE SABOTAGE APPLIES: the real FAMILIES has members and the '
          'broken one does not -- asserted BEFORE the tool is driven, because a '
          'patch that silently failed would leave every arm below green for ever',
          sum(len(v) for v in _real_families.values()) > 5
          and sum(len(v) for v in E.FAMILIES.values()) == 0,
          (sum(len(v) for v in _real_families.values()),
           sum(len(v) for v in E.FAMILIES.values())))
    bad = E.run_fixtures()
    check('A2b. ...and the criteria lock then FAILS, because a fixture that '
          'must report can no longer report',
          bad != [], bad)
finally:
    E.FAMILIES = _real_families
check('A3. the families were RESTORED -- otherwise every arm below runs against '
      'a sabotaged tool and this whole file means nothing',
      E.FAMILIES is _real_families
      and sum(len(v) for v in E.FAMILIES.values()) > 5,
      sorted(E.FAMILIES))

# ── B. IT FIRES ON THE REAL DEFECT, RECONSTRUCTED ───────────────────────────
section('B. the defect this exists for, restored and reported')

# The pre-fix shape of tools/tier_a_review_gate.py, as it stood before the
# 2026-09-27 correction: --explain read the working tree, the push path read a
# commit range, and nothing compared them.
PRE_FIX = '''
def main(argv):
    rows = load_reviews()
    if '--explain' in argv:
        changed = working_diff()
        report(changed)
        return 0
    if '--pre-push' in argv:
        changed = push_range()
        return gate(changed)
'''
_verdict, _detail = E.classify(E.doors(PRE_FIX))
check('B1. THE PRE-FIX SHAPE IS REPORTED -- two doors, two members of the '
      'scope-of-change family',
      _verdict == E.FINDING, (_verdict, _detail))
check('B1b. ...and the finding NAMES the family, so a reader is told what kind '
      'of disagreement it is rather than only that there is one',
      'scope-of-change' in (_detail or {}), sorted(_detail or {}))
check('B1c. ...and names BOTH accessors, which is what makes it actionable',
      {'working_diff', 'push_range'} <= set(
          c for d in (_detail or {}).get('scope-of-change', {}).values()
          for c in d),
      _detail)

POST_FIX = '''
def main(argv):
    rows = load_reviews()
    if '--explain' in argv:
        changed = default_scope_diff()
        report(changed)
        return 0
    if '--pre-push' in argv:
        changed = default_scope_diff()
        return gate(changed)
'''
check('B2. THE SILENT HALF: the SAME tool after its fix -- one accessor, two '
      'doors -- is NOT reported. A checker that flagged the fix too would be '
      'reporting the shape rather than the defect',
      E.classify(E.doors(POST_FIX))[0] != E.FINDING,
      E.classify(E.doors(POST_FIX)))

# ── C. THE TWO FALSE POSITIVES THE REAL RUNS PAID FOR ───────────────────────
section('C. correct code that the first two versions reported')

SHARED_SETUP = '''
def main(argv):
    probes = listdir(TESTS)
    if args.all:
        for p in probes:
            f = walk(p)
    for p in probes:
        f = walk(p)
'''
check('C1. SHARED SETUP is not a divergence -- an enumeration before the branch '
      'belongs to every door. This reported as a finding until the attribution '
      'was fixed, about code that was correct',
      E.classify(E.doors(SHARED_SETUP))[0] != E.FINDING,
      E.classify(E.doors(SHARED_SETUP)))

TWO_QUESTIONS = '''
def main(argv):
    if args.list:
        rows = load_reviews()
        return 0
    d = default_scope_diff()
    rows = load_reviews()
'''
check('C2. TWO DOORS MAY ANSWER DIFFERENT QUESTIONS -- a door reading no scope '
      'accessor at all is not disagreeing about scope. This reported the real '
      'tier_a_review_gate AFTER its fix',
      E.classify(E.doors(TWO_QUESTIONS))[0] != E.FINDING,
      E.classify(E.doors(TWO_QUESTIONS)))

check('C3. --fixtures is NOT counted as a door, so a tool whose only extra flag '
      'is an isolated validation has one door and cannot be a finding',
      E.classify(E.doors('''
def main(argv):
    if args.fixtures:
        run_fixtures()
    if args.check:
        d = tracked('*.py')
'''))[0] == E.CLEAN_ONE_DOOR,
      E.classify(E.doors('''
def main(argv):
    if args.fixtures:
        run_fixtures()
    if args.check:
        d = tracked('*.py')
''')))

# ── D. THE REAL RUN, AND ITS DENOMINATOR ────────────────────────────────────
section('D. the real run says what it read and what it could not')
rc, out = run()
import re                                                        # noqa: E402
_m = re.search(r'read (\d+) tool\(s\); (\d+) have TWO OR MORE', out)
check('D1. the run reads a NON-EMPTY tool list -- a zero would make the verdict '
      'vacuous', bool(_m) and int(_m.group(1)) > 50,
      _m.group(0) if _m else out[:300])
_cu = re.search(r'CHECKED / UNIVERSE: (\d+) of (\d+)', out)
check('D2. CHECKED / UNIVERSE is published, and both figures are real: checked '
      '> 0 and universe > checked, so a collapsed denominator cannot read as '
      'full coverage',
      _cu is not None and int(_cu.group(1)) > 0
      and int(_cu.group(2)) > int(_cu.group(1)),
      _cu.group(0) if _cu else 'no CHECKED / UNIVERSE line')
check('D3. ...and the MULTI-DOOR population is more than a handful, or this tool '
      'is measuring almost nothing and should say so rather than reporting clean',
      bool(_m) and int(_m.group(2)) >= 10,
      _m.group(0) if _m else 'no count line')
check('D4. the isolated flags are named in the output, so the exclusion is '
      'auditable rather than an omission somebody has to notice',
      '--fixtures' in out and 'EXCLUDED BY NAME' in out, out[:600])
check('D5. exit is 0, 1 or 2 and nothing else', rc in (0, 1, 2), rc)

# ── E. ANCHOR ARMS -- what tells us the day this control stops testing ──────
section('E. the anchors this control depends on (discipline 8)')
_src = io.open(TOOL, encoding='utf-8').read()
check('E1. classify() and doors() are still the names this control calls; if '
      'either is renamed every arm above silently stops testing the tool',
      'def classify(' in _src and 'def doors(' in _src, 'a function was renamed')
check('E2. CRITERIA_VERSION is present and appears in the real output, so a '
      'criteria change is visible rather than silent',
      bool(str(getattr(E, 'CRITERIA_VERSION', '')).strip())
      and E.CRITERIA_VERSION in out, getattr(E, 'CRITERIA_VERSION', None))
check('E3. the tool declares this file as its control, so checker_control_check '
      'can find the pair from either end',
      'run_entry_point_scope_probe.py' in _src, 'CONTROLLED_BY is stale')
check('E4. RESOLVE_DEPTH is stated in the source rather than implicit -- the '
      'first version resolved nothing and reported clean for every tool',
      'RESOLVE_DEPTH' in _src and E.RESOLVE_DEPTH >= 2, getattr(E, 'RESOLVE_DEPTH', None))

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
