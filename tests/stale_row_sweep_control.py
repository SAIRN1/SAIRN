"""THE NEGATIVE CONTROL for tools/stale_row_sweep.py.

A checker that has only ever returned a clean answer is one whose behaviour
nobody knows. Every arm here either PLANTS a defect in the tool and requires it
to be reported, or plants nothing and requires silence. Neither half says
anything alone.

THE ARM THAT MATTERS MOST IS ARM 6, and it is not a mutation. It runs the real
tool against the REAL historical index -- `docs/SAIRN-OPEN-WORK-INDEX.md` as it
stood at `50adbda7^`, before the SAIRNvet row was closed -- and requires it to
report that row AND to name `ad588e6c` and `1348466a`, the two commits that had
already fixed it. That is the true positive this tool exists for, and the
PATH-ONLY first version of the tool FAILED IT: the row names no file path at
all. Without this arm that version would have shipped as a confident 46-row
report that could not see the one case in its own docstring.

Exit 0 pass, 1 fail.
"""
CONTROLS_FOR = ['tools/stale_row_sweep.py']

import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'stale_row_sweep.py')

fails = []


def check(cond, label):
    print(('  ok   ' if cond else '  FAIL ') + label)
    if not cond:
        fails.append(label)


def run(path, args, cwd=REPO):
    r = subprocess.run([sys.executable, path] + args, cwd=cwd,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=900)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def mutated(old, new):
    """A scratch copy of the tool with one string replaced. Refuses a no-op.

    A mutation whose anchor does not match is a SKIP that reads as a pass --
    that exact false pass happened twice in one day on this platform, once in a
    probe harness and once in a sabotage run, so it is an error here.
    """
    src = open(TOOL, encoding='utf-8').read()
    if old not in src:
        raise AssertionError('mutation anchor not found, so nothing was '
                             'mutated: %r' % old[:60])
    d = tempfile.mkdtemp(prefix='srsctl-')
    p = os.path.join(d, 'stale_row_sweep.py')
    with open(p, 'w', encoding='utf-8', newline='') as fh:
        fh.write(src.replace(old, new, 1))
    # The tool imports checker_kit from its own directory, so the copy has to
    # sit beside one. Copying the kit is cheaper and more honest than teaching
    # the tool a test-only import path.
    shutil.copy(os.path.join(REPO, 'tools', 'checker_kit.py'),
                os.path.join(d, 'checker_kit.py'))
    return p


print('1. THE UNMODIFIED TOOL PASSES ITS OWN BLIND LOCK')
rc, out = run(TOOL, ['--fixtures'])
check(rc == 0, 'the real tool: --fixtures exits 0')
check('blind lock OK' in out, '...and says so')


print('')
print('2. MUTATION: the DATE comes from anywhere in the row again')
# The real defect this replaced: statute dates quoted in a row's prose read as
# the row's own date, making `since` years too early.
p = mutated("dates = sorted(set(DATE_RE.findall(cells[2])))",
            "dates = sorted(set(DATE_RE.findall(' '.join(cells))))")
rc, out = run(p, ['--fixtures'])
check(rc != 0, 'a citation date read as the row date FAILS the lock')
check('DETAIL cell is not the row date' in out,
      '...and the lock names the arm that caught it')


print('')
print('3. MUTATION: the SYMBOL anchor is removed')
# The path-only version. This is the shape that missed the founding case.
p = mutated("        syms = row_symbols(cells) if glog else []",
            "        syms = []")
rc, out = run(p, ['--fixtures'])
check(rc != 0, 'dropping the symbol anchor FAILS the lock')
check('SYMBOL ANCHOR' in out, '...and names the founding-case fixture')


print('')
print('4. MUTATION: a CLOSED row is swept as if it were open')
p = mutated("    if CLOSED_RE.search(status):\n        return False",
            "    if False:\n        return False")
rc, out = run(p, ['--fixtures'])
check(rc != 0, 'sweeping closed rows FAILS the lock')
check('CLOSED row is not swept' in out or 'reads as closed' in out,
      '...and names a closed-row fixture')


print('')
print('5. MUTATION: an uncheckable row is folded into QUIET')
# The single most repeated defect in this repo's tooling: could-not-run counted
# as clean. If this arm ever goes quiet, the third state has been lost.
p = mutated("            cannot.append((n, subject, why))\n            continue",
            "            quiet.append((n, subject, date))\n            continue")
rc, out = run(p, ['--fixtures'])
check(rc != 0, 'folding uncheckable rows into quiet FAILS the lock')


print('')
print('6. THE TRUE POSITIVE -- the real SAIRNvet row, out of real history')
# Not a fixture. The index as it stood before 50adbda7 closed the row.
r = subprocess.run(['git', 'show', '50adbda7^:docs/SAIRN-OPEN-WORK-INDEX.md'],
                   cwd=REPO, capture_output=True, text=True, encoding='utf-8',
                   errors='replace')
if r.returncode != 0:
    check(False, 'could not read the historical index: %s' % (r.stderr or '').strip()[:80])
else:
    d = tempfile.mkdtemp(prefix='srsidx-')
    idx = os.path.join(d, 'index_before.md')
    with open(idx, 'w', encoding='utf-8', newline='') as fh:
        fh.write(r.stdout)
    rc, out = run(TOOL, ['--index', idx, '--json'])
    try:
        data = json.loads(out[out.index('{'):])
    except Exception as e:
        data = None
        check(False, 'the historical run produced parseable --json (%s)' % e)
    if data:
        hit = [m for m in data['moved'] if m['line'] == 568]
        check(bool(hit), 'the SAIRNvet row (line 568) is reported MOVED')
        if hit:
            detail = ' '.join(hit[0]['detail'])
            check('ad588e6c' in detail,
                  '...and NAMES ad588e6c, the photo fix')
            check('1348466a' in detail,
                  '...and NAMES 1348466a, the finally fix')
            check(hit[0]['since'] == '2026-09-10',
                  '...dated from the row\'s own status cell, not its prose')
            check(not hit[0]['paths'],
                  '...with ZERO file-path anchors -- the symbol anchor is the '
                  'only reason this row is visible at all')

        # THE OTHER HALF. A tool that reported every row would pass every check
        # above. The same historical index must still leave rows QUIET.
        check(data['quiet'] > 0,
              'the same run leaves %d row(s) QUIET -- not a report-everything '
              'rule' % data['quiet'])
        check(len(data['moved']) < data['open_rows'],
              'MOVED (%d) is fewer than the open rows (%d)'
              % (len(data['moved']), data['open_rows']))


print('')
print('7. EXIT CODES, AND THE THIRD STATE WINS')
rc, out = run(TOOL, [])
check(rc in (1, 2), 'the real sweep exits 1 or 2, never 0 while rows are open')
check('CANNOT' in out.upper() or 'uncheckable' in out,
      'uncheckable rows are named in the output')
check('cannot close a row' in out.lower(),
      'the report states it CANNOT close a row -- the limit is on screen, not '
      'only in the docstring')


print('')
print('8. IT WRITES NOTHING')
before = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO,
                        capture_output=True, text=True, encoding='utf-8').stdout
run(TOOL, [])
after = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8').stdout
check(before == after, 'a real run leaves the working tree unchanged')
src = open(TOOL, encoding='utf-8').read()
check("'w'" not in src and '"w"' not in src,
      'the tool contains no write mode at all')


print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('0 failure(s)')
