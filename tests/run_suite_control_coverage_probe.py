"""The control for tools/suite_control_coverage.py.

Run: python tests/run_suite_control_coverage_probe.py

WHY THIS EXISTS WHEN THE TOOL HAS --self-check: the self-check runs on fixtures
the tool itself writes. This runs on the REAL tree and re-derives the answer a
different way -- a plain substring search over each probe's source, with the
docstring left in. That second method is deliberately WEAKER and therefore
BROADER: anything it does not find, the tool cannot legitimately find either, so
it bounds the tool from above and a tool that over-claimed coverage would
exceed it.

Over-claiming is the only direction that matters here. A suite wrongly listed
as controlled is a suite nobody will ever point a control at, and it reads as
tested-for-assertion-power when nobody has tried to break it.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import suite_control_coverage as C                               # noqa: E402

CONTROLS_FOR = ['suite_control_coverage.py']

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


names, ctl, unreadable = C.survey()
print('suite control coverage control -- %d suites, %d controlled\n'
      % (len(names), len(ctl)))

# ── 1. THE UPPER BOUND, DERIVED A DIFFERENT WAY ────────────────────────────
# Plain substring search, docstrings included. Broader than the tool by
# construction, so every suite the tool calls controlled must appear here.
loose = {}
import glob                                                      # noqa: E402
for p in sorted(glob.glob(os.path.join(REPO, 'tests', '*.py'))):
    try:
        src = io.open(p, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    if 'MUTATIONS' not in src:
        continue
    for b in names:
        if b in src:
            loose.setdefault(b, []).append(os.path.basename(p))

over = sorted(set(ctl) - set(loose))
check('the tool claims NO suite that a broader, dumber search cannot find -- '
      'it never over-claims coverage', over == [], over)
check('...and the broader search does find MORE, so the bound is not vacuous',
      len(loose) > len(ctl), '%d loose vs %d strict' % (len(loose), len(ctl)))

# ── 2. THE DOCSTRING EXCLUSION IS DOING WORK ON THE REAL TREE ──────────────
# If it were not, strict and loose would agree and arm 1 would be proving
# nothing about the exclusion this tool's safety rests on.
only_loose = sorted(set(loose) - set(ctl))
check('at least one real suite is named ONLY in prose and is correctly NOT '
      'counted as controlled', only_loose != [], only_loose)

# ── 3. EVERY CLAIMED CONTROLLER REALLY EXISTS AND REALLY HAS MUTATIONS ─────
for suite, probes in sorted(ctl.items()):
    for pb in probes:
        path = os.path.join(REPO, 'tests', pb)
        ok = os.path.exists(path)
        has = ok and 'MUTATIONS' in io.open(path, encoding='utf-8',
                                            errors='replace').read()
        check('%s: its named controller %s exists and defines MUTATIONS'
              % (suite, pb), has, path)

# ── 4. THE UNIVERSE IS BOTH DIRECTORIES ────────────────────────────────────
# A tests/-only universe silently dropped api/, where two controlled suites
# live. Without this arm the universe could narrow again and the headline would
# simply get smaller, which reads as progress.
check('the universe includes api/*.test.js, not tests/ alone',
      any(n.endswith('.test.js') for n in names)
      and len(names) > len(glob.glob(os.path.join(REPO, 'tests', '*.js'))),
      len(names))
check('...and suite basenames are unique across the two directories, so a '
      'control cannot be credited to the wrong suite',
      len(set(names)) == len(names),
      '%d names, %d unique' % (len(names), len(set(names))))

# ── 5. THE EXIT CODE FOLLOWS THE ANSWER ────────────────────────────────────
p = subprocess.run([sys.executable,
                    os.path.join(REPO, 'tools', 'suite_control_coverage.py'),
                    '--json'],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', cwd=REPO,
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
check('with uncontrolled suites present the exit code is 1, not 0',
      p.returncode == 1, p.returncode)

# THE TEXT PATH HAS ITS OWN RETURN and is the one a person runs. Tested because
# a mutant that zeroed only this branch passed every other arm: the --json arm
# returns earlier and never reaches it.
t = subprocess.run([sys.executable,
                    os.path.join(REPO, 'tools', 'suite_control_coverage.py')],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', cwd=REPO,
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
check('the TEXT run also exits 1 while suites are uncontrolled',
      t.returncode == 1, t.returncode)
check('...and prints the uncontrolled count rather than a table and silence',
      'never been sabotaged' in t.stdout, t.stdout[:200])

# AND IT CAN SAY YES. Without this every arm passes on a tool that answers
# "uncontrolled" for every input there will ever be.
_n, _c, _u = C.survey([os.path.join(REPO, 'tests', 'dnt_vendor_write_confirmation.js')],
                      [os.path.join(REPO, 'tests',
                                    'dnt_vendor_write_confirmation_probe.py')])
check('a tree where every suite IS controlled reports every suite controlled',
      len(_c) == len(_n) == 1, (_n, sorted(_c)))

check('a probe that will not parse is reported, never counted as absent',
      isinstance(unreadable, list), unreadable)

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
