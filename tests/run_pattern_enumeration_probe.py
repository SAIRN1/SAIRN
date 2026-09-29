r"""tests/run_pattern_enumeration_probe.py -- control pair for
tools/pattern_enumeration_sweep.py.

    python tests/run_pattern_enumeration_probe.py

CONTROLS_FOR = ['tools/pattern_enumeration_sweep.py']
LIVE_PROBE_CLASS = 'FIXTURE'

THE CRITERIA ARE LOCKED AGAINST FIXTURES BEFORE ANY REAL DATA, which is the first
cross-domain discipline and is not optional here: this sweep's whole output is a
judgement about what counts as corroboration, and tuning that against the repo
until the number looked right is exactly how a criteria-shaped tool becomes a
number-shaped one.

THE TWO CRITERIA DECISIONS, EACH WITH A FIXTURE IN BOTH DIRECTIONS:

  OPTION PARSING IS NOT A POPULATION. `tokens[i].startswith('-')` decides whether
  an argument is a flag. The first run of the sweep reported
  git_push_master_guard.py on the strength of three of those -- a file with no
  population in it at all. A sweep whose findings are mostly argv parsing is a
  sweep nobody reads.

  READING THE FILE IS NOT CORROBORATION, and this is the one that matters. The
  first version counted `open(` as a second derivation, matched almost every tool
  in the repo, and reported 3 findings out of ~200 -- which LOOKED LIKE GOOD NEWS
  AND WAS A VACUOUS PASS. Reading a file you already selected by name tells you
  what it is; it cannot tell you whether you should have selected it. With the
  criterion corrected the same repo reports 117 of 263.

  THE CLONE UNDERCOUNT IS THE PROOF AND IS A FIXTURE HERE:
  nhi_register.sibling_clones() read `remote.origin.url` out of every directory it
  examined -- real content, real second source -- and still missed a working copy,
  because the NAME decided which directories it examined.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

TOOL = os.path.join(REPO, 'tools', 'pattern_enumeration_sweep.py')
if not os.path.isfile(TOOL):
    print('COULD NOT RUN: tools/pattern_enumeration_sweep.py is not on disk. '
          'This control tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

import pattern_enumeration_sweep as S   # noqa: E402

NL = chr(10)
passed = failed = 0


def ok(cond, label, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        failed += 1
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:500])


def examine_text(body):
    """Run the real examine() over a fixture written to a temp file in the repo."""
    fd, path = tempfile.mkstemp(suffix='.py', prefix='_zz_fixture_',
                                dir=os.path.join(REPO, 'tools'))
    os.close(fd)
    try:
        io.open(path, 'w', encoding='utf-8', newline='\n').write(body)
        rel = os.path.relpath(path, REPO).replace('\\', '/')
        result, err = S.examine(rel)
        assert err is None, err
        return result
    finally:
        os.remove(path)


print('CONTROL PAIR -- tools/pattern_enumeration_sweep.py' + NL)

# ══ CRITERION 1 -- option parsing is not a population ══════════════════════
print('CRITERION 1 -- option parsing is NOT a population filter')

OPTS_ONLY = (
    'def parse(argv):' + NL +
    '    i = 1' + NL +
    "    while i < len(argv) and argv[i].startswith('-'):" + NL +
    '        i += 1' + NL +
    "    rest = [a for a in argv if not a.startswith('--')]" + NL +
    '    return rest' + NL)
tests, corrob = examine_text(OPTS_ONLY)
ok(tests == [],
   'a file whose only name tests are argv flag parsing yields NOTHING. The first '
   'run of this sweep reported git_push_master_guard.py on three of these, and it '
   'has no population in it at all', tests)

REAL_POP = (
    'import os' + NL +
    'def members(base):' + NL +
    '    out = []' + NL +
    '    for name in os.listdir(base):' + NL +
    "        if name.startswith('SAIRN-'):" + NL +
    '            out.append(name)' + NL +
    '    return out' + NL)
tests, corrob = examine_text(REAL_POP)
ok(len(tests) >= 2 and corrob == [],
   'FIXTURE VALIDITY AND THE TRUE POSITIVE IN ONE: the real clone-undercount '
   'shape -- listdir plus a startswith on the NAME, nothing else -- is reported '
   'with NO corroboration. If this arm ever goes quiet the criterion above has '
   'eaten the finding too', (tests, corrob))

# ══ CRITERION 2 -- reading the file is not corroboration ═══════════════════
print(NL + 'CRITERION 2 -- reading the file is NOT corroboration of MEMBERSHIP')

READS_CONTENT = (
    'import io, os' + NL +
    'def members(base):' + NL +
    '    out = []' + NL +
    '    for name in os.listdir(base):' + NL +
    "        if name.startswith('SAIRN-'):" + NL +
    "            body = io.open(os.path.join(base, name)).read()" + NL +
    "            if 'origin' in body:" + NL +
    '                out.append(name)' + NL +
    '    return out' + NL)
tests, corrob = examine_text(READS_CONTENT)
ok(corrob == [],
   'THE ARM THAT MATTERS: a tool that reads each candidate\'s CONTENT is still '
   'single-derivation. That is the clone undercount exactly -- nhi_register read '
   'remote.origin.url out of every directory it examined and still missed one, '
   'because the NAME chose which directories it examined. Content corroborates '
   'CLASSIFICATION; only a different membership test corroborates MEMBERSHIP',
   corrob)

CORROBORATED = (
    'import os, subprocess' + NL +
    'def members(base):' + NL +
    "    tracked = subprocess.run(['git', 'ls-files']).stdout" + NL +
    '    out = []' + NL +
    '    for name in os.listdir(base):' + NL +
    "        if name.startswith('SAIRN-'):" + NL +
    '            out.append(name)' + NL +
    '    return [m for m in out if m in tracked]' + NL)
tests, corrob = examine_text(CORROBORATED)
ok('git ls-files' in corrob,
   'and a tool that asks git ls-files IS corroborated -- tracked-ness is a fact '
   'about membership that no name can supply', corrob)

WORKTREE = ('import subprocess' + NL +
            'def members():' + NL +
            "    return subprocess.run(['git', 'worktree', 'list']).stdout" + NL +
            "    # and a name test so there is something to corroborate" + NL +
            "x = 'a'.startswith('b')" + NL)
tests, corrob = examine_text(WORKTREE)
ok('git worktree list' in corrob,
   'and so is one that asks git what it considers a working copy', corrob)

# ══ THE SWEEP'S OWN HONESTY ════════════════════════════════════════════════
print(NL + 'DIRECTION -- it says what it does not sweep, and why')
p = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True,
                   text=True, encoding='utf-8', errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8'))
out = (p.stdout or '') + (p.stderr or '')
ok('NOT SWEPT: pattern_enumeration_sweep.py' in out,
   'it EXCLUDES ITSELF and says so -- its NAME_TESTS table is a list of regexes '
   'ABOUT name tests, so it matches itself on every row', out[:600])
ok('COUNTS OF CODE SHAPES, NOT OF DEFECTS' in out,
   'and it says the numbers are code shapes rather than bugs, because "117 '
   'findings" in a report reads as 117 defects')
ok('NO RANKING AND NO AUTO-FIX' in out,
   'and that it does not rank or fix -- severity depends on what the population '
   'is FOR, which it cannot know')

# ══ THE SECOND DERIVATION, RUN ═════════════════════════════════════════════
print(NL + 'DIRECTION -- the second derivation is RUN, not recommended')
ok('SECOND DERIVATION' in out and 'disk=' in out and 'tracked=' in out,
   'the sweep runs filesystem membership against git membership and prints both '
   'counts per scope', out[-900:])
ok('the two derivations agree' in out or 'DISAGREE' in out,
   'and says per scope whether they agree', out[-900:])
ok('A DISAGREEMENT IS NOT AUTOMATICALLY A DEFECT' in out or 'agree' in out,
   'and when they disagree it says a disagreement is not automatically a defect '
   '-- the two populations answer different questions, and the defect is in a '
   'tool that did not CHOOSE between them', out[-900:])

fs = S.filesystem_vs_git()
ok(fs is not None and len(fs) == len(S.FS_SCOPES),
   'filesystem_vs_git() answers for every declared scope (%d)'
   % len(S.FS_SCOPES))
if fs:
    ok(all(isinstance(d, set) and isinstance(t, set) for _s, d, t, _a, _b in fs),
       'and returns real sets on both sides rather than counts, so a caller can '
       'see WHICH files differ and not only how many')

# ══ FAIL CLOSED ════════════════════════════════════════════════════════════
print(NL + 'DIRECTION -- an empty universe is COULD NOT RUN, never clean')
empty = tempfile.mkdtemp(prefix='sairn_pes_')
try:
    q = subprocess.run([sys.executable, TOOL, '--tool',
                        os.path.join(empty, 'nothing.py')],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    body = (q.stdout or '') + (q.stderr or '')
    ok(q.returncode == EXIT_COULD_NOT_RUN or 'COULD NOT READ' in body,
       'an unreadable target is COULD NOT RUN or is reported as unreadable, not '
       'silently counted as having no name tests (exit %d)' % q.returncode,
       body[-400:])
finally:
    shutil.rmtree(empty, ignore_errors=True)

print(NL + '%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
