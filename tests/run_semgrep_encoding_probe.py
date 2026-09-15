"""tools/run_semgrep.py must produce a VERDICT when its output is captured.

Run: python tests/run_semgrep_encoding_probe.py

── THE DEFECT THIS PINS (2026-09-15) ───────────────────────────────────────
semgrep's own `--test` output contains U+2713. On Windows, Python encodes
stdout with the LOCALE encoding -- cp1252 -- whenever stdout is NOT a terminal,
which is to say whenever a hook, a CI step or another script CAPTURES it.
`print(out.strip())` then raised:

    UnicodeEncodeError: 'charmap' codec can't encode character '\\u2713'

AND THE FAILURE MODE IS THE WORST SHAPE THIS REPO RECORDS. semgrep had already
run and already PASSED. What the caller received was neither a verdict nor a
clean failure: a traceback, and a non-zero exit, from a check that succeeded.
A gate reading that exit code concludes the scan failed. The tool works
perfectly when a human runs it in a terminal and breaks in exactly the
configuration that matters.

── WHY THIS IS A SEPARATE FILE AND NOT AN ARM INSIDE run_semgrep.py ────────
The bug is in the OUTPUT BOUNDARY, so it cannot be observed from inside the
process doing the printing. It is only visible to a parent that captures the
child's stdout with a hostile encoding -- which is what this file is.

── FAIL-CLOSED, NOT SKIP-IF-ABSENT (PR 1.11) ───────────────────────────────
If semgrep is not installed, this does NOT quietly pass. It says which tool is
missing, says nothing was verified, and exits non-zero. "Could not run" is a
third state and is never folded into "passed".
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = os.path.join('tools', 'run_semgrep.py')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:500]))
    if not cond:
        fails.append(name)


def run_captured(cwd, encoding):
    """Run the tool with stdout CAPTURED and a hostile encoding, the way a
    hook does. capture_output is the whole point -- it is what makes Python
    choose the locale encoding instead of the terminal's."""
    e = dict(os.environ)
    e['PYTHONIOENCODING'] = encoding
    p = subprocess.run([sys.executable, TOOL, '--test'], cwd=cwd, env=e,
                       capture_output=True)
    out = (p.stdout or b'') + (p.stderr or b'')
    return p.returncode, out.decode('utf-8', 'replace')


print('tools/run_semgrep.py -- a captured stdout must still get a verdict\n')

wt = tempfile.mkdtemp(prefix='sairn-sg-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True)
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

try:
    shutil.copyfile(os.path.join(REPO, TOOL), os.path.join(wt, TOOL))
    ORIG = io.open(os.path.join(wt, TOOL), encoding='utf-8', newline='').read()

    # ── ARM 0: IS SEMGREP EVEN HERE ────────────────────────────────────────
    rc, out = run_captured(wt, 'utf-8')
    if 'semgrep is not installed' in out:
        print('  COULD NOT RUN -- semgrep is not installed in this environment.')
        print('  Nothing was verified. That is not a pass. `pip install semgrep`.')
        sys.exit(2)

    # ── ARM 1: THE VACUITY GUARD, AND IT IS THE LOAD-BEARING ONE ───────────
    # If semgrep ever stops printing a non-ASCII character, this whole file
    # passes with OR without the fix and proves nothing. So the first thing
    # asserted is that the hazard still exists in the real output.
    nonascii = sorted(set(ch for ch in out if ord(ch) > 127))
    check('semgrep output still contains a non-ASCII character, so this probe '
          'is not vacuous', bool(nonascii),
          'the output is pure ASCII now -- there is nothing left for cp1252 to '
          'fail on, and every arm below would pass for the wrong reason')
    if nonascii:
        print('         (hazard present: %s)'
              % ', '.join('U+%04X' % ord(c) for c in nonascii[:6]))

    # ── ARM 2: THE REAL CONFIGURATION ──────────────────────────────────────
    rc, out = run_captured(wt, 'cp1252')
    check('cp1252 + captured stdout still produces a verdict, not a traceback',
          'UnicodeEncodeError' not in out, out[-400:])
    check('...and the exit code is the SCAN result, not an encoding crash',
          rc in (0, 1), 'exit %d' % rc)
    check('...and the verdict text actually arrived',
          'tests passed' in out or 'NO TESTS RAN' in out, out[-300:])

    # ── ARM 3: THE NEGATIVE CONTROL, WHICH VERIFIES ITS OWN SABOTAGE ───────
    # 23 of 39 controls on this platform never check that their sabotage
    # applied. One that did not apply runs the tool UNCHANGED, gets a pass, and
    # reports a green arm about a mutation that never existed.
    # The DEFINITION and the CALL are counted separately and both must be
    # exactly one. A first version of this arm looked for the bare call text
    # and expected two hits -- but `def _make_stdout_safe():` ends in a colon,
    # so it matched once and the fixture check failed on the SHIPPED file.
    # Counting the wrong thing is how a control ends up asserting nothing.
    n_def = ORIG.count('def _make_stdout_safe():')
    n_call = ORIG.count('\n_make_stdout_safe()\n')
    if n_def != 1 or n_call != 1:
        check('fixture valid: the guard is defined once and called once',
              False, 'found %d definition(s) and %d top-level call(s), '
              'expected 1 and 1' % (n_def, n_call))
    else:
        broken = ORIG.replace('\n_make_stdout_safe()\n', '\n', 1)
        if broken == ORIG:
            check('the sabotage applied', False,
                  'could not remove the call site -- nothing was mutated, so '
                  'the arm below would be about the SHIPPED file')
        else:
            io.open(os.path.join(wt, TOOL), 'w', encoding='utf-8',
                    newline='').write(broken)
            on_disk = io.open(os.path.join(wt, TOOL), encoding='utf-8',
                              newline='').read()
            check('the sabotage reached disk', on_disk != ORIG,
                  'the mutated copy is identical to the original')
            rc2, out2 = run_captured(wt, 'cp1252')
            check('WITHOUT the guard the same run really does crash -- so the '
                  'arms above are testing the fix and not the weather',
                  'UnicodeEncodeError' in out2,
                  'removing the guard changed nothing; either the hazard is '
                  'gone or the guard is not what is doing the work\n' + out2[-300:])
            io.open(os.path.join(wt, TOOL), 'w', encoding='utf-8',
                    newline='').write(ORIG)

    # ── THE CLOSING CONTROL ────────────────────────────────────────────────
    restored = io.open(os.path.join(wt, TOOL), encoding='utf-8',
                       newline='').read() == ORIG
    check('the tool is byte-identical to the working tree afterwards', restored,
          'a restore did not land')
finally:
    shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(['git', '-C', REPO, 'worktree', 'prune'], capture_output=True)
    print('\n  the throwaway worktree is gone: %s' % (not os.path.isdir(wt)))

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
