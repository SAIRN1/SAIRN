"""Control pair for tools/fact_sheet_regenerates.py.

Run:  python tests/run_fact_sheet_regenerates_probe.py

CONTROLS_FOR = ['tools/fact_sheet_regenerates.py']
LIVE_PROBE_CLASS = 'FIXTURE'

Directions, one per `print('\\nDIRECTION` below plus the baseline -- COUNT THEM
THERE rather than trusting a word written here, which was "Five" while there
were seven:

  edit ONE figure in a COPY of the sheet        -> must be REPORTED, by name
  edit a figure by ONE                          -> must be REPORTED (no tolerance)
  REMOVE a row entirely                         -> must be REPORTED, not silently skipped
  edit a RESTATEMENT in the prose               -> must be REPORTED and CORRECTED
  REWORD the sentence a restatement lives in    -> must be REPORTED as unanchored
  --update on a deliberately stale figure       -> CORRECTED, and the run stamped
  a BROKEN command under --update               -> old figure stands, exit 2, NO stamp
  point it at a MISSING sheet                   -> COULD NOT RUN (exit 2, never 0)
  the real sheet, unmodified                    -> SILENT

**THE COPY IS THE POINT.** A control that edited the real sheet would leave the
document Michael is carrying into a meeting in an unknown state if it crashed
between the edit and the restore. `--sheet` exists so this probe never touches it.

THE LAST DIRECTION IS THE ONE THAT MATTERS MOST. A checker that reports every
sheet is useless, and this one has every row AND every restatement to get wrong:
if it fired on the real sheet, nobody would run it, and it would be ignored on
the day a figure really had moved.
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

# READ OUT OF THE SHEET, never written down here. A control that hardcodes the
# figure it edits stops editing anything the day that figure moves -- and it
# keeps passing, because `str.replace` of an absent needle is a silent no-op.
_m = re.search(r'\| Registered data resources \| \*\*([\d,]+)\*\*', ORIGINAL)
if not _m:
    print('COULD NOT RUN: the row this control edits is not in the sheet. It '
          'tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)
RES_ROW = _m.group(0)
RES_VALUE = _m.group(1)

print('CONTROL PAIR -- tools/fact_sheet_regenerates.py\n')

print('BASELINE -- the real sheet, untouched')
rc, out = run(SHEET_REL)
ok(rc == EXIT_CLEAN,
   'THE ARM THAT MATTERS MOST: the real sheet is clean (exit %d). A checker that '
   'fired here would be ignored on the day a figure really moved.' % rc,
   out[-500:])
m = re.search(r'ALL (\d+) checkable figures and (\d+) restatements', out)
ok(bool(m) and int(m.group(1)) >= 15,
   'and it actually CHECKED something -- %s figures, not zero'
   % (m.group(1) if m else 'no count printed'), out[-300:])
ok(bool(m) and int(m.group(2)) >= 10,
   'and it checked the RESTATEMENTS too -- %s of them. The sheet says several '
   'figures again in prose, and on 2026-09-28 the rows were refreshed while the '
   'sentence under them still read 6,885' % (m.group(2) if m else 'none'),
   out[-300:])
ok('CHECKED / UNIVERSE' in out and 'RESTATEMENTS' in out,
   'and it prints checked/universe, so a silently narrowed run is visible')
ok('FIGURES THIS TOOL DOES NOT CHECK AT ALL' in out
   and 'the panel counts' in out,
   'and it NAMES what it does not check, so the coverage number cannot read as '
   'having covered the whole sheet')

try:
    print('\nDIRECTION -- one figure edited in a COPY')
    s = ORIGINAL.replace(RES_ROW, '| Registered data resources | **999**', 1)
    assert s != ORIGINAL, 'the anchor for the edit is gone'
    io.open(COPY, 'w', encoding='utf-8', newline='\n').write(s)
    rc, out = run(COPY_REL)
    ok(rc == EXIT_FINDING, 'exits 1 (got %d)' % rc, out[-400:])
    ok('resources' in out and '999' in out,
       'and names the figure AND both values', out[-300:])

    print('\nDIRECTION -- a figure wrong by ONE (no tolerance)')
    s = ORIGINAL.replace(RES_ROW, '| Registered data resources | **%d**'
                         % (int(RES_VALUE.replace(',', '')) + 1), 1)
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

ANCHOR_RX = r'(\*\*What this figure is and is not\.\*\* )([\d,]+)( is the count since)'

print('\nDIRECTION -- a RESTATEMENT edited in the prose')
# The figure with no command of its own. This is the arm the whole restatement
# layer exists for: on 2026-09-28 the rows were refreshed and the checker exited
# 0 while the sentence under the commits row still read 6,885, because nothing
# looked at a number that was written out in a sentence rather than in a table.
try:
    s, n = re.subn(ANCHOR_RX, r'\g<1>4321\g<3>', ORIGINAL, count=1)
    ok(n == 1, 'the anchor for the restatement edit is present in the real sheet')
    io.open(COPY, 'w', encoding='utf-8', newline='\n').write(s)
    rc, out = run(COPY_REL)
    ok(rc == EXIT_FINDING,
       'a restated figure that drifted is REPORTED (got %d)' % rc, out[-400:])
    ok('prose_defects_total' in out and '4321' in out,
       'and names the restatement AND the wrong value', out[-400:])

    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    p4 = subprocess.run([sys.executable, TOOL, '--sheet', COPY_REL, '--update',
                         '--now', '2026-01-01 00:00'], cwd=REPO, env=env,
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace')
    after = io.open(COPY, encoding='utf-8').read()
    ok(p4.returncode == EXIT_CLEAN,
       '--update exits 0 on it (got %d)' % p4.returncode, (p4.stdout or '')[-300:])
    ok('4321' not in after,
       'and the restatement was CORRECTED, not left standing in the prose')
finally:
    if os.path.exists(COPY):
        os.remove(COPY)

print('\nDIRECTION -- the SENTENCE a restatement lives in is REWORDED')
# An anchor that stops matching is the eighth cross-domain discipline: nothing
# announces the day a check stops testing anything. A reworded sentence must be
# a FINDING, never a quiet skip that leaves the run looking clean.
try:
    s = ORIGINAL.replace('is the count since', 'is the tally since', 1)
    assert s != ORIGINAL, 'the anchor for the rewording edit is gone'
    io.open(COPY, 'w', encoding='utf-8', newline='\n').write(s)
    rc, out = run(COPY_REL)
    ok(rc == EXIT_FINDING,
       'a reworded sentence is REPORTED, not silently skipped (got %d)' % rc,
       out[-400:])
    ok('no longer matches its anchor' in out and 'prose_defects_total' in out,
       'and it says the anchor is gone, by name -- a check that quietly stopped '
       'testing anything is indistinguishable from one that passed', out[-400:])

    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    p5 = subprocess.run([sys.executable, TOOL, '--sheet', COPY_REL, '--update',
                         '--now', '2026-01-01 00:00'], cwd=REPO, env=env,
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace')
    after = io.open(COPY, encoding='utf-8').read()
    ok(p5.returncode == EXIT_COULD_NOT_RUN,
       'and --update refuses to call that a clean run (got %d)' % p5.returncode,
       (p5.stdout or '')[-300:])
    ok('Figures refreshed 2026-01-01' not in after,
       'and does NOT stamp it refreshed')
finally:
    if os.path.exists(COPY):
        os.remove(COPY)

print('\nDIRECTION -- --update CORRECTS a deliberately stale figure')
try:
    s = ORIGINAL.replace(RES_ROW, '| Registered data resources | **12345**', 1)
    assert s != ORIGINAL, 'the anchor for the stale-figure edit is gone'
    io.open(COPY, 'w', encoding='utf-8', newline='\n').write(s)
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    p2 = subprocess.run([sys.executable, TOOL, '--sheet', COPY_REL, '--update',
                         '--now', '2026-01-01 00:00'], cwd=REPO, env=env,
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace')
    after = io.open(COPY, encoding='utf-8').read()
    ok(p2.returncode == EXIT_CLEAN,
       'the update run exits 0 (got %d)' % p2.returncode, (p2.stdout or '')[-300:])
    ok('**12345**' not in after,
       'THE ARM THAT MATTERS: the stale figure was CORRECTED, not left standing')
    ok(RES_ROW in after,
       'and corrected to the value the command actually returns')
    ok('Figures refreshed 2026-01-01 00:00' in after,
       'and the run time is stamped, so a reader can see how fresh it is')
finally:
    if os.path.exists(COPY):
        os.remove(COPY)

print('\nDIRECTION -- a BROKEN command leaves the old figure AND exits non-zero')
try:
    io.open(COPY, 'w', encoding='utf-8', newline='\n').write(ORIGINAL)
    before = io.open(COPY, encoding='utf-8').read()
    # GIT_DIR pointed at nothing breaks every git-derived figure from OUTSIDE the
    # tool -- no test-only branch inside production code, which would be a second
    # code path nobody exercises in anger.
    env = dict(os.environ, PYTHONIOENCODING='utf-8',
               GIT_DIR=os.path.join(REPO, '_zz_no_such_git_dir'))
    p3 = subprocess.run([sys.executable, TOOL, '--sheet', COPY_REL, '--update',
                         '--now', '1999-01-01 00:00'], cwd=REPO, env=env,
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace')
    after = io.open(COPY, encoding='utf-8').read()
    ok(p3.returncode == EXIT_COULD_NOT_RUN,
       'it exits 2 COULD NOT RUN, not 0 (got %d) -- "updated" and "updated as far '
       'as it could" are never the same answer' % p3.returncode,
       (p3.stdout or '')[-300:])
    ok('LEFT ALONE, derivation could not run' in (p3.stdout or ''),
       'and it says WHICH figures it left alone')
    for label in ('| Commits since 2026-05-15 |',
                  '| Verification tools and checkers |'):
        b = [l for l in before.split('\n') if l.startswith(label)]
        a = [l for l in after.split('\n') if l.startswith(label)]
        ok(b == a and b != [],
           'the old figure is untouched for %r -- a blank or a zero in a printed '
           'document is worse than a number that was true once' % label,
           'before=%s after=%s' % (b[:1], a[:1]))
    ok('Figures refreshed 1999-01-01' not in after,
       'AND THE FAILED RUN DID NOT STAMP A FRESH TIME. Caught by this arm on its '
       'first run: stale figures under a just-refreshed stamp makes the one signal '
       'a reader checks the one that lies')
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
