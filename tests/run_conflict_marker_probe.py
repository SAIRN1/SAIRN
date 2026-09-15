"""Does the conflict-marker gate actually REFUSE a marker, and refuse nothing else?

    python tests/run_conflict_marker_probe.py

THIS FILE IS THE THING I NAMED AND DID NOT BUILD. The open-work row I wrote after
pushing markers to origin said a real fix "needs a control that FAILS on a
marker-bearing fixture and PASSES on a clean one, driven rather than read -- the
same bar the decode sweep was held to." That is sections 1 and 2.

SECTION 3 IS THE HALF THAT MATTERS MORE, and it is why this check can block on
day one. A gate that refuses a marker is easy. A gate that refuses ONLY a marker
is the question, because this repo's own documents QUOTE all three markers in
prose -- the 2026-09-11 open-work row contains `<<<<<<<` inside backticks -- and
`=======` underlines a markdown heading and rules off an ASCII banner in dozens
of files. Every one of those is driven here as a NEGATIVE control.

SECTION 5 DRIVES THE REAL PUSH GATE rather than the tool, because a check
nothing invokes is the failure mode check 10 exists for, and md_table_check has
carried a conflict regex since 2026-09-12 while three separate markers reached
origin anyway.

NOTHING HERE WRITES A TRACKED FILE. Every fixture is a string or a temp file:
markers are exactly what a probe must not leave behind in a shared branch.
"""
import io
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import conflict_marker_check as c                                # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


# Assembled rather than written as literals, so THIS FILE does not contain the
# very thing it detects -- otherwise the whole-tree scan reports its own probe
# and the honest baseline of zero becomes one.
OURS = '<' * 7
BASE = '|' * 7
SPLIT = '=' * 7
THEIRS = '>' * 7

print('\n1. IT FAILS ON A MARKER -- the four shapes git actually writes')
CONFLICT = (
    'function total(rows) {\n'
    + OURS + ' HEAD\n'
    + '  return rows.length;\n'
    + SPLIT + '\n'
    + '  return rows.filter(Boolean).length;\n'
    + THEIRS + ' 98bfea1e (their change)\n'
    + '}\n')
hits = c.scan_text('api/_lib/fixture.js', CONFLICT)
check('a real three-part conflict block is found', len(hits) == 3, hits)
check('...and each marker is named by KIND, so a partial resolution is legible',
      sorted(h[1] for h in hits) == ['ours', 'split', 'theirs'], hits)
check('...with the right line numbers', [h[0] for h in hits] == [2, 4, 6], hits)

check('a LONE opening marker is found -- a half-resolved file is the real case',
      len(c.scan_text('x.js', 'a\n' + OURS + ' HEAD\nb\n')) == 1)
check('a LONE closing marker is found', len(c.scan_text('x.js', THEIRS + ' abc\n')) == 1)
check('a LONE split marker is found -- the one left after deleting both sides',
      len(c.scan_text('x.js', SPLIT + '\n')) == 1)
check('the diff3 BASE marker is found too -- conflictStyle=diff3 writes it',
      len(c.scan_text('x.js', BASE + ' base\n')) == 1)
check('a marker with NO trailing text still counts', len(c.scan_text('x.js', OURS)) == 1)

print('\n2. IT PASSES ON A CLEAN FILE')
check('an ordinary source file is clean',
      c.scan_text('x.js', 'const a = 1;\nmodule.exports = { a };\n') == [])
check('an empty file is clean', c.scan_text('x.js', '') == [])

print('\n3. NEGATIVE CONTROLS -- the things this repo really contains')
# THIS IS THE SECTION THAT LETS THE CHECK BLOCK ON DAY ONE. Each of these is a
# real shape from a real file in this repository.
check('PROSE QUOTING A MARKER inside backticks is NOT a finding -- the '
      '2026-09-11 open-work row does exactly this',
      c.scan_text('docs/X.md',
                  'The cause was `' + OURS + '`/`' + SPLIT + '`/`' + THEIRS
                  + '` markers live on origin/main.\n') == [])
check('a markdown SETEXT underline is not a finding',
      c.scan_text('docs/X.md', 'A Heading\n' + SPLIT + SPLIT + '\n') == [],
      'a heading underline is longer than seven and is still at column zero -- '
      'this arm is why the regex anchors on EXACTLY seven followed by space or '
      'end of line')
check('an ASCII banner rule is not a finding',
      c.scan_text('tools/x.py', '# ' + SPLIT * 8 + '\n') == [])
check('a marker INDENTED by one space is not a finding -- git writes at '
      'column zero, and accepting whitespace starts matching prose',
      c.scan_text('x.js', ' ' + OURS + ' HEAD\n') == [])
check('eight angle brackets is not a marker', c.scan_text('x.js', '<' * 8 + ' HEAD\n') == [])
check('six angle brackets is not a marker', c.scan_text('x.js', '<' * 6 + ' HEAD\n') == [])
check('a marker mid-line is not a finding',
      c.scan_text('x.js', 'const s = "' + OURS + '";\n') == [])
check('a shell heredoc-ish line is not a finding',
      c.scan_text('x.sh', 'cat <<EOF\n' + 'hello\n' + 'EOF\n') == [])

print('\n4. THE MEASURED BASELINE, re-measured rather than quoted')
# The whole justification for blocking on day one is that the real
# false-positive rate is zero. If that ever stops being true, this arm fails and
# the gate has to be reconsidered -- which is the correct order.
hits, skipped, unreadable = c.scan(c.tracked())
check('ZERO markers across every tracked file -- this is the claim that lets '
      'check 14 block on day one, and it is re-measured here rather than cited',
      hits == [], [h['file'] + ':' + str(h['line']) for h in hits[:6]])
check('...over a real population, so the zero is not an empty scan',
      len(c.tracked()) > 1500, len(c.tracked()))
check('binary files are SKIPPED AND NAMED, never silently clean',
      isinstance(skipped, list) and len(skipped) >= 1, skipped[:3])
check('nothing was unreadable', unreadable == [], unreadable)

print('\n5. THE GATE IS WIRED, AND IT DENIES -- driven, not read')
hook = io.open(os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py'),
               encoding='utf-8').read()
check('the push gate invokes conflict_marker_check.py',
      'conflict_marker_check.py' in hook,
      'the check exists and nothing calls it -- md_table_check has carried a '
      'conflict regex since 2026-09-12 and three markers reached origin anyway')
# ASSERTED ON THE CODE, NOT ON THE MESSAGE. The first version of this arm
# searched for the sentence "neither clean nor a finding" and FAILED -- the
# string is real but wraps across two source lines, so the substring does not
# exist. A source assertion that matches prose is an assertion about how
# somebody happened to line-wrap; this one is about the branch.
check('...and an unexpected exit is treated as neither clean nor a finding',
      '_cm.returncode not in (0, 1)' in hook,
      'the hook does not distinguish an unexpected exit from a clean one, so a '
      'crash in the marker check would read as a push with no markers')

tmp = tempfile.mkdtemp(prefix='conflict-marker-probe-')
try:
    bad = os.path.join(tmp, 'unmerged.js')
    io.open(bad, 'w', encoding='utf-8', newline='\n').write(CONFLICT)
    good = os.path.join(tmp, 'clean.js')
    io.open(good, 'w', encoding='utf-8', newline='\n').write('const a = 1;\n')

    r = subprocess.run([sys.executable,
                        os.path.join(REPO, 'tools', 'conflict_marker_check.py'),
                        '--files', bad],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=180)
    check('the TOOL exits 1 on a marker-bearing file', r.returncode == 1,
          'exit %s\n%s' % (r.returncode, r.stdout[:200]))
    check('...and says WHY it matters rather than only where',
          'not a style problem' in r.stdout.lower(), r.stdout[:300])

    r2 = subprocess.run([sys.executable,
                         os.path.join(REPO, 'tools', 'conflict_marker_check.py'),
                         '--files', good],
                        cwd=REPO, capture_output=True, text=True,
                        encoding='utf-8', errors='replace', timeout=180)
    check('CONTROL: it exits 0 on a clean file, so exit 1 is about the marker '
          'and not about the --files mode', r2.returncode == 0,
          'exit %s\n%s' % (r2.returncode, r2.stdout[:200]))
finally:
    try:
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)
    except OSError:
        pass

print('\n6. THE INCIDENT THAT md_table_check MISSED, driven through BOTH checks')
# The point is not that md_table_check is wrong. It is that a marker in a .js
# file was never in its scope, and that is why this had to be a separate check
# rather than a wider regex.
sys.path.insert(0, os.path.join(REPO, 'tools'))
import md_table_check as md                                      # noqa: E402
js = CONFLICT
check('md_table_check has no opinion about a .js file -- correctly, it reads '
      'markdown tables', not hasattr(md, 'scan_js'),
      'it grew a JS path; this section needs rewriting')
check('...and the new check DOES', len(c.scan_text('api/_lib/dnt-rollup.js', js)) == 3)

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
