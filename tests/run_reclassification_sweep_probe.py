"""Control for tools/reclassification_sweep.py.

    python tests/run_reclassification_sweep_probe.py

Exit 0  it reads the corpus it is pointed at, and refuses everything it
        cannot read instead of reporting it as containing no match
Exit 1  one of those refusals did not fire

── WHAT THIS IS ABOUT, AND IT IS NOT THE REGEXES ───────────────────────────
This tool decides which states DEEM a caregiver an employee and which
expressly PERMIT an independent contractor. Its output is evidence behind a
compliance position, so its dangerous failure is not a missed pattern -- it is
a CONFIDENT ZERO.

Until 2026-09-22 it produced exactly that. `glob.glob('*.txt')` was unanchored
and non-recursive while the captures live two directories deep, so it swept
the current directory: 22 app HTML files from the repo root, and nothing at
all from docs/sources or docs/sources/sairnsenior. Every run printed
`TALLY: {'DEEM': 0, 'ROLE': 0, 'PERMIT': 0}` and refused nothing. Its own v1
history says Delaware "was found by reading, not by sweeping", which is what a
sweep that reads nothing looks like from outside.

FIVE SEPARATE FAIL-OPENS FED THAT ZERO and each gets arms below, because
fixing four of five would leave the same sentence on screen:

  the corpus glob      swept the cwd, so the answer depended on where you stood
  the pypdf branch     `except Exception: return ''` -- absent library, or an
                       encrypted PDF, read as a document with no match
  the docx branch      the same shape, one function down
  the <400-byte skip   a failed download dropped in silence
  zero files           a tally printed over nothing

EVERY FIXTURE HERE IS SYNTHETIC AND BUILT IN A TEMP DIRECTORY. The criteria
are locked against text this file writes, in both directions, rather than
against the real captures -- whose content changes as states are added, and
which are the very thing the tool is supposed to be judged on.
"""
CONTROLS_FOR = ['reclassification_sweep.py']

import io
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'reclassification_sweep.py')
FAILS = []


def ok(label, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + label
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        FAILS.append(label)


def run(*args, **kw):
    p = subprocess.run([sys.executable, TOOL] + list(args),
                       cwd=kw.get('cwd', REPO), capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=300)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


# A statute-shaped fixture, long enough to clear the 400-byte floor. The
# trigger phrase is one of the real PERMIT patterns; the rest is filler that
# must NOT match anything, so a pattern that matched everything would fail the
# negative arm below rather than passing every positive one.
FILLER = ('The department shall adopt rules for the licensure of agencies '
          'providing services in the home, including standards for records, '
          'inspections, renewal, and the qualifications of personnel. ' * 6)
PERMITS = FILLER + ' The licensee shall employ or contract with a qualified '\
                   'dietician to supervise nutritional care. ' + FILLER
CLEAN = FILLER + ' Nothing in this chapter limits the authority of the '\
                 'department to inspect a licensed agency. ' + FILLER

tmp = tempfile.mkdtemp(prefix='reclass-probe-')
try:
    # ── 1. A DIRECTORY THAT IS NOT THERE IS A REFUSAL, NOT A ZERO ──────────
    rc, out = run(os.path.join(tmp, 'no-such-dir'))
    ok('a missing corpus directory exits 2', rc == 2, 'rc=%r' % rc)
    ok('...and says COULD NOT RUN rather than printing a tally',
       'COULD NOT RUN' in out and 'TALLY' not in out, out[:200])

    # ── 2. AN EMPTY DIRECTORY IS THE SAME REFUSAL ──────────────────────────
    empty = os.path.join(tmp, 'empty')
    os.makedirs(empty)
    rc, out = run(empty)
    ok('an empty corpus exits 2', rc == 2, 'rc=%r' % rc)
    ok('...and prints NO TALLY, because a zero over nothing reads exactly '
       'like a zero over fifty states', 'TALLY' not in out, out[:200])

    # ── 3. IT WALKS. The whole original defect in one arm: the fixture is two
    # ── directories deep, which is where the real captures are.
    deep = os.path.join(tmp, 'corpus', 'sairnsenior', 'ZZ')
    os.makedirs(deep)
    io.open(os.path.join(deep, 'ZZ-statute.txt'), 'w', encoding='utf-8').write(PERMITS)
    root = os.path.join(tmp, 'corpus')
    rc, out = run(root)
    ok('a document TWO directories deep is swept', 'files: 1' in out, out[:300])
    ok('...and its PERMIT hit is found', "'PERMIT': 1" in out, out[-300:])
    ok('...and the run is clean', rc == 0, 'rc=%r' % rc)

    # ── 4. THE ANSWER DOES NOT DEPEND ON WHERE YOU ARE STANDING ────────────
    rc2, out2 = run(root, cwd=tempfile.gettempdir())
    ok('the same corpus gives the same tally from a different cwd',
       out.split('TALLY:')[-1] == out2.split('TALLY:')[-1],
       '%r vs %r' % (out.split('TALLY:')[-1][:80], out2.split('TALLY:')[-1][:80]))

    # ── 5. AND IT DOES NOT MATCH EVERYTHING. A positive-only control passes
    # ── against a tool that flags every document it sees.
    clean = os.path.join(tmp, 'clean', 'sairnsenior', 'YY')
    os.makedirs(clean)
    io.open(os.path.join(clean, 'YY-statute.txt'), 'w', encoding='utf-8').write(CLEAN)
    rc, out = run(os.path.join(tmp, 'clean'))
    ok('a document with none of the phrases scores zero',
       "{'DEEM': 0, 'ROLE': 0, 'PERMIT': 0}" in out, out[-300:])
    ok('...and that zero is reported WITH its denominator, so it cannot be '
       'confused with the old zero-over-nothing',
       'swept 1 of 1 candidate file(s)' in out, out[-300:])

    # ── 6. A FILE THAT CANNOT BE READ IS A THIRD STATE ─────────────────────
    mixed = os.path.join(tmp, 'mixed', 'sairnsenior', 'XX')
    os.makedirs(mixed)
    io.open(os.path.join(mixed, 'XX-statute.txt'), 'w', encoding='utf-8').write(PERMITS)
    # Not a real .docx: a zip with no word/document.xml. The old code returned
    # '' here and the document was swept as containing no match.
    # PADDED PAST THE 400-BYTE FLOOR ON PURPOSE. The first version of this
    # fixture was 130 bytes, so it was caught by the size skip and never
    # reached the reader at all -- the arm would have been asserting the wrong
    # refusal while looking green, which is the shape this whole file is about.
    bad = os.path.join(mixed, 'XX-broken.docx')
    with zipfile.ZipFile(bad, 'w') as z:
        z.writestr('not-the-file-we-want.xml', '<x>' + ('padding ' * 200) + '</x>')
    assert os.path.getsize(bad) >= 400, 'the unreadable fixture must clear the size floor'
    rc, out = run(os.path.join(tmp, 'mixed'))
    ok('an unreadable document makes the run exit 1', rc == 1, 'rc=%r' % rc)
    ok('...and is named with its reason', 'XX-broken.docx' in out and
       'could not be read as a .docx' in out, out[-400:])
    ok('...and the tally still covers the file that COULD be read, rather '
       'than the whole run being thrown away', "'PERMIT': 1" in out, out[-400:])
    ok('...and the swept count says 1 of 2, so the denominator is visible',
       'swept 1 of 2 candidate file(s)' in out, out[-400:])

    # ── 7. A FAILED DOWNLOAD IS NAMED, NOT DROPPED ─────────────────────────
    small = os.path.join(tmp, 'small', 'sairnsenior', 'WW')
    os.makedirs(small)
    io.open(os.path.join(small, 'WW-truncated.txt'), 'w', encoding='utf-8').write('too short')
    io.open(os.path.join(small, 'WW-statute.txt'), 'w', encoding='utf-8').write(PERMITS)
    rc, out = run(os.path.join(tmp, 'small'))
    ok('a file under 400 bytes is REPORTED rather than silently skipped',
       'WW-truncated.txt' in out and 'UNDER 400 BYTES' in out, out[-400:])
    ok('...and it does not fail the run, because a short capture is a '
       'download problem rather than an unreadable document', rc == 0,
       'rc=%r' % rc)

    # ── 8. A DOCUMENT THAT READS AS EMPTY IS NOT A DOCUMENT WITH NO MATCH ──
    # An .out file of pure whitespace, over the size floor: the old code hit
    # `if not t: continue` and counted it as swept-and-clean.
    blank = os.path.join(tmp, 'blank', 'sairnsenior', 'VV')
    os.makedirs(blank)
    io.open(os.path.join(blank, 'VV-empty.out'), 'w', encoding='utf-8').write(' ' * 500)
    rc, out = run(os.path.join(tmp, 'blank'))
    ok('a whitespace-only capture is reported as EMPTY, not as no-match',
       'read as EMPTY' in out, out[-400:])
    ok('...and takes the run to exit 1', rc == 1, 'rc=%r' % rc)

    # ── 9. A PDF THAT CANNOT BE PARSED, AND A pypdf THAT IS NOT THERE ──────
    # Two different failures behind one file extension, and the tool says
    # which -- "pypdf is not installed" is a fixable instruction, "this PDF is
    # encrypted" is a fact about the capture, and one message for both sends
    # the next reader to the wrong place.
    pdfs = os.path.join(tmp, 'pdfs', 'sairnsenior', 'UU')
    os.makedirs(pdfs)
    io.open(os.path.join(pdfs, 'UU-statute.txt'), 'w', encoding='utf-8').write(PERMITS)
    io.open(os.path.join(pdfs, 'UU-broken.pdf'), 'w', encoding='utf-8').write(
        '%PDF-1.4 this is not actually a pdf ' + ('x' * 500))
    rc, out = run(os.path.join(tmp, 'pdfs'))
    ok('a PDF that cannot be parsed is named rather than swept as clean',
       'UU-broken.pdf' in out and 'could not be parsed as a PDF' in out, out[-400:])
    ok('...and takes the run to exit 1', rc == 1, 'rc=%r' % rc)

    # THE LIBRARY, NOT THE DOCUMENT. pypdf is shadowed by a package with no
    # PdfReader in it, so `from pypdf import PdfReader` raises ImportError
    # exactly as it would on a clone that never installed it. This is the
    # WIDEST of the failures -- absent pypdf meant every PDF in the corpus was
    # swept as containing no match -- and it cannot be reached any other way
    # on a machine where the library IS installed.
    shadow = os.path.join(tmp, 'shadow')
    os.makedirs(os.path.join(shadow, 'pypdf'))
    io.open(os.path.join(shadow, 'pypdf', '__init__.py'), 'w',
            encoding='utf-8').write('# deliberately empty: no PdfReader\n')
    env = dict(os.environ)
    env['PYTHONPATH'] = shadow + os.pathsep + env.get('PYTHONPATH', '')
    p = subprocess.run([sys.executable, TOOL, os.path.join(tmp, 'pdfs')],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=300, env=env)
    out = (p.stdout or '') + (p.stderr or '')
    ok('an absent pypdf is reported as the LIBRARY being missing, not as the '
       'document being clean', 'needs pypdf' in out and 'NOT swept' in out,
       out[-400:])
    ok('...and takes the run to exit 1 rather than 0', p.returncode == 1,
       'rc=%r' % p.returncode)
    ok('...while the .txt beside it is still swept, so one missing library '
       'does not throw away the whole corpus', "'PERMIT': 1" in out, out[-400:])

    # ── 10. THE DEFAULT CORPUS IS THE REPOSITORY'S, NOT THE CWD ────────────
    # RUN WITH NO ARGUMENT, FROM A FOREIGN DIRECTORY. Every arm above passes
    # an explicit path, so none of them exercises the default at all -- and
    # the default is where the original defect lived. Without this, replacing
    # `else CORPUS` with `else '.'` changes nothing any other arm can see.
    foreign = os.path.realpath(tmp)
    rc, out = run(cwd=foreign)
    expected = os.path.join(REPO, 'docs', 'sources')
    first = out.split('\n')[0] if out else ''
    ok('with no argument it sweeps the repository corpus, from a cwd that is '
       'not the repository', ('corpus: ' + expected) in out, first or '(no output)')
    # ASSERTED AGAINST THE CWD ITSELF, not against a substring of the system
    # temp directory. The first spelling used `tempfile.gettempdir() not in
    # ...`, and the sabotage harness builds its worktree UNDER the temp
    # directory -- so the repository corpus legitimately contained that
    # string and the baseline went red for a reason that had nothing to do
    # with any mutation. The question was always "is the corpus the cwd?", so
    # that is what it now asks.
    reported = first[len('corpus: '):].strip() if first.startswith('corpus: ') else ''
    ok('...and the corpus it chose is NOT the directory it was run from',
       bool(reported) and os.path.realpath(reported) != foreign,
       'reported %r, cwd %r' % (reported, foreign))

    src = io.open(TOOL, encoding='utf-8').read()
    ok("the default root is docs/sources under the repo, derived from the "
       "tool's own path", "os.path.join(REPO, 'docs', 'sources')" in src)
    # PARSED, NOT GREPPED, and the first version of this arm got it wrong the
    # way this platform keeps recording. `"glob.glob('*." not in src` fired on
    # the COMMENT that explains what the old code did -- a check that cannot
    # tell code from text describing code, PR 1.2, inside the control for a
    # tool whose docstring necessarily quotes its own former defect. The AST
    # cannot be fooled by prose.
    import ast
    tree = ast.parse(src)
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == 'glob']
    imports = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import)
               for a in n.names]
    ok('no glob.glob() call survives in the CODE -- asserted through the AST, '
       'so the comment quoting the old defect cannot satisfy or break it',
       not calls, '%d glob call(s) remain' % len(calls))
    ok('and the glob module is no longer imported at all',
       'glob' not in imports, imports)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('\n%d failure(s)' % len(FAILS))
for f in FAILS:
    print('  - ' + f)
sys.exit(1 if FAILS else 0)
