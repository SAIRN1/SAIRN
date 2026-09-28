"""Control pair for tools/fact_sheet_regenerates.py.

Run:  python tests/run_fact_sheet_regenerates_probe.py

CONTROLS_FOR = ['tools/fact_sheet_regenerates.py']
LIVE_PROBE_CLASS = 'FIXTURE'

Five directions:

  edit ONE figure in a COPY of the sheet        -> must be REPORTED, by name
  edit a figure by ONE                          -> must be REPORTED (no tolerance)
  REMOVE a row entirely                         -> must be REPORTED, not silently skipped
  point it at a MISSING sheet                   -> COULD NOT RUN (exit 2, never 0)
  the real sheet, unmodified                    -> SILENT

**THE COPY IS THE POINT.** A control that edited the real sheet would leave the
document Michael is carrying into a meeting in an unknown state if it crashed
between the edit and the restore. `--sheet` exists so this probe never touches it.

THE LAST DIRECTION IS THE ONE THAT MATTERS MOST. A checker that reports every
sheet is useless, and this one has 21 figures to get wrong: if it fired on the
real sheet, nobody would run it, and it would be ignored on the day a figure
really had moved.
"""
import io
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'fact_sheet_regenerates.py')
SHEET_REL = os.path.join('docs', 'FACT-SHEET-2026-09-29.md')
SHEET = os.path.join(REPO, SHEET_REL)
COPY_REL = os.path.join('docs', '_zz_fact_sheet_probe_copy.md')
COPY = os.path.join(REPO, COPY_REL)

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2
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
            print('       %s' % str(detail)[:400])


def run(sheet_rel):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    p = subprocess.run([sys.executable, TOOL, '--sheet', sheet_rel], cwd=REPO,
                       env=env, capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return p.returncode, (p.stdout or '') + (p.stderr or '')


if not os.path.isfile(TOOL) or not os.path.isfile(SHEET):
    print('COULD NOT RUN: the tool or the sheet is not on disk. This control '
          'tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

ORIGINAL = io.open(SHEET, encoding='utf-8', newline='').read()

print('CONTROL PAIR -- tools/fact_sheet_regenerates.py\n')

print('BASELINE -- the real sheet, untouched')
rc, out = run(SHEET_REL)
ok(rc == EXIT_CLEAN,
   'THE ARM THAT MATTERS MOST: the real sheet is clean (exit %d). A checker that '
   'fired here would be ignored on the day a figure really moved.' % rc,
   out[-500:])
m = re.search(r'ALL (\d+) checkable figures', out)
ok(bool(m) and int(m.group(1)) >= 15,
   'and it actually CHECKED something -- %s figures, not zero'
   % (m.group(1) if m else 'no count printed'), out[-300:])
ok('CHECKED / UNIVERSE' in out,
   'and it prints checked/universe, so a silently narrowed run is visible')

try:
    print('\nDIRECTION -- one figure edited in a COPY')
    s = ORIGINAL.replace('| Registered data resources | **390**',
                         '| Registered data resources | **999**', 1)
    assert s != ORIGINAL, 'the anchor for the edit is gone'
    io.open(COPY, 'w', encoding='utf-8', newline='\n').write(s)
    rc, out = run(COPY_REL)
    ok(rc == EXIT_FINDING, 'exits 1 (got %d)' % rc, out[-400:])
    ok('resources' in out and '999' in out,
       'and names the figure AND both values', out[-300:])

    print('\nDIRECTION -- a figure wrong by ONE (no tolerance)')
    s = ORIGINAL.replace('| Registered data resources | **390**',
                         '| Registered data resources | **391**', 1)
    io.open(COPY, 'w', encoding='utf-8', newline='\n').write(s)
    rc, out = run(COPY_REL)
    ok(rc == EXIT_FINDING,
       'off by one is still a finding (got %d) -- a fact sheet with a tolerance '
       'is a fact sheet with a rounding policy nobody agreed' % rc, out[-300:])

    print('\nDIRECTION -- a row REMOVED entirely')
    s = '\n'.join(l for l in ORIGINAL.split('\n')
                  if 'Registered data resources' not in l)
    io.open(COPY, 'w', encoding='utf-8', newline='\n').write(s)
    rc, out = run(COPY_REL)
    ok(rc == EXIT_FINDING,
       'a removed row is REPORTED, not silently skipped (got %d)' % rc, out[-300:])
    ok('NO figure matching this label' in out,
       'and it says the label is gone rather than reporting a match of zero -- '
       'an unanchored check is the next defect along', out[-300:])
finally:
    if os.path.exists(COPY):
        os.remove(COPY)

print('\nDIRECTION -- a MISSING sheet is COULD NOT RUN, never clean')
rc, out = run(os.path.join('docs', '_zz_no_such_sheet.md'))
ok(rc == EXIT_COULD_NOT_RUN,
   'exits 2, not 0 and not 1 (got %d) -- an absent sheet is not a clean one' % rc,
   out[-300:])

print('\nAFTER -- the real sheet is untouched')
ok(io.open(SHEET, encoding='utf-8', newline='').read() == ORIGINAL,
   'byte-identical: this probe never edited the document being carried into a '
   'meeting')
ok(not os.path.exists(COPY), 'and the working copy was removed')

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
