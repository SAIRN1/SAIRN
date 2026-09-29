"""tests/run_staging_discipline_probe.py -- attacks tools/staging_discipline_scan.py.

Run:  python tests/run_staging_discipline_probe.py

── THE REAL FIXTURE IS push_retry.py AT TWO POINTS IN ITS OWN HISTORY ────
That file is the exact trap this scanner exists to survive. Its docstring QUOTES
the defective loop it replaces:

    if [ -n "$(git status --porcelain)" ]; then git add -A; git commit --amend; fi

and until 50d16fd4 its CODE also called `git add -A`. So:

  BEFORE the fix, the correct answer is TWO -- the call, and the line that
         PRINTED the same instruction to a human mid-rebase. Not the quote.
  AFTER  the fix, the correct answer is ZERO -- the quote is still there.

The TWO was wrong when this control was written: it expected one, and driving it
found the second. An advice line nobody executes is still a staging instruction
somebody follows.

Both revisions are read out of git rather than hand-written here, because a
hand-written fixture of a file that exists is a second copy that can drift from
it, and this platform has paid for that shape repeatedly.

── AND A KNOWN-BAD CONTROL THAT MUST FAIL ───────────────────────────────
A naive `grep -c 'git add -A'` is run against the SAME post-fix file. It must
report a hit, and the scanner must not. Without that arm, a scanner that had
simply stopped matching anything would pass every arm above: zero hits on a
clean file and zero hits on a dirty one are indistinguishable unless something
proves the dirty file really does contain the string.
"""
CONTROLS_FOR = ['staging_discipline_scan.py']

import io
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'staging_discipline_scan.py')
EXIT_COULD_NOT_RUN = 2

FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:400]))
    if not cond:
        FAIL.append(name)


def load():
    import importlib.util
    spec = importlib.util.spec_from_file_location('sds', TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def git_show(rev, path):
    r = subprocess.run(['git', '-C', REPO, 'show', rev + ':' + path],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.stdout if r.returncode == 0 else None


if not os.path.isfile(TOOL):
    sys.stderr.write('COULD NOT RUN: tools/staging_discipline_scan.py is not on '
                     'disk. This control tested nothing, which is a third state '
                     'and not a pass.\n')
    sys.exit(EXIT_COULD_NOT_RUN)

sds = load()
NL = chr(10)

print('CONTROL PAIR -- tools/staging_discipline_scan.py' + NL)

# ── A. THE REAL FILE, AFTER ITS FIX ──────────────────────────────────────
print('A. push_retry.py as it stands: the hazard is QUOTED, not called')
after = io.open(os.path.join(REPO, 'tools', 'push_retry.py'),
                encoding='utf-8').read()
hits_after = sds.scan_text(after, 'tools/push_retry.py')
ok('the scanner reports NO breadth-staging call site',
   hits_after == [], hits_after)

naive = len(re.findall(r'git add -A', after))
ok('KNOWN-BAD CONTROL: a naive grep DOES match, %d time(s)' % naive, naive >= 1,
   'the quote is gone from the file, so this control no longer proves the '
   'scanner is doing anything -- pick another fixture rather than deleting '
   'the arm')
ok('...so the scanner and the naive grep DISAGREE, which is the whole point',
   naive >= 1 and hits_after == [])

# ── B. THE SAME FILE, BEFORE ITS FIX ─────────────────────────────────────
print(NL + 'B. push_retry.py before 50d16fd4: the hazard is CALLED')
before = git_show('50d16fd4~1', 'tools/push_retry.py')
if before is None:
    # The revision is not in this clone. NOT a pass: the arm that proves the
    # scanner can find a real call site did not run.
    ok('the pre-fix revision could be read out of git', False,
       'git show 50d16fd4~1:tools/push_retry.py failed -- shallow clone, or the '
       'commit was rewritten. This arm proves the scanner CAN find a real site; '
       'without it every arm above is satisfied by a scanner that finds nothing.')
else:
    hits_before = sds.scan_text(before, 'tools/push_retry.py')
    ok('the scanner finds the real call site', len(hits_before) >= 1, hits_before)
    # TWO, AND THE ARM SAID ONE UNTIL IT WAS DRIVEN. The pre-fix file had the
    # call at :434 AND a printed instruction at :414 telling a human to run
    # `git add -A && git rebase --continue` mid-rebase -- the same defect one
    # level out, fixed in the same commit. My expectation of one was a guess
    # about a file I had already read; the arm corrected it. Counting it is the
    # point: an advice line nobody executes is still a staging instruction
    # somebody follows.
    ok('...and exactly TWO -- the call and the printed instruction -- with the '
       'docstring quote still not counted',
       len(hits_before) == 2,
       'found %d: %s' % (len(hits_before), hits_before))
    if hits_before:
        line, shape, raw = hits_before[0]
        ok('...and it names the CODE line, not the docstring',
           "git('add', '-A')" in raw or 'add' in raw,
           'excerpt = %r' % raw)
        ok('...and the line number lands on that line in the real text',
           before.split(NL)[line - 1].strip() == raw or
           raw in before.split(NL)[line - 1],
           'line %d = %r' % (line, before.split(NL)[line - 1].strip()))

# ── C. SYNTHETIC FIXTURES, BOTH DIRECTIONS ───────────────────────────────
print(NL + 'C. synthetic fixtures -- every shape, and every near-miss')

Q3 = chr(34) * 3
CASES = [
    ('a shell git add -A',          'os.system("git add -A")', 1),
    ('a shell git add .',           'os.system("git add .")', 1),
    ('a shell git add -u',          'os.system("git add -u")', 1),
    ('a shell git commit -a',       'os.system("git commit -a -m x")', 1),
    ('an ARGLIST git add -A',       "subprocess.run(['git', 'add', '-A'])", 1),
    ('an ARGLIST git commit -a',    "subprocess.run(['git', 'commit', '-a'])", 1),
    ('a COMMENT mentioning it',     '# never run git add -A here', 0),
    ('a DOCSTRING quoting it',      Q3 + 'do not: git add -A' + Q3, 0),
    ('git add BY NAME',             "subprocess.run(['git', 'add', '--', 'a.py'])", 0),
    ('git add -Alpha (not -A)',     'os.system("git add -Alpha")', 0),
    ('the word "git added"',        'x = "git added a file"', 0),
    ('a path containing a dot',     'os.system("git add tools/a.py")', 0),
    # THE DISCRIMINATOR THIS TOOL'S OWN CONTROL FORCED. push_retry.py's refusal
    # MESSAGES quote the hazard inside string literals, and a string literal is
    # code to the comment-stripper -- correctly, because a real arglist call
    # lives in string literals too. Backticks are the difference: nothing that
    # is actually run is wrapped in them. Both directions, or the exemption
    # becomes a way to hide a real call by decorating it.
    ('a BACKTICKED mention in a message',
     'msg = "`git add -A` would stage the markers"', 0),
    ('...but a real call in a string still counts',
     'os.system("git add -A")', 1),
    ('...and a backticked mention BESIDE a real call counts once',
     'os.system("git add -A")  # see `git add -A` above', 1),
]
for label, body, want in CASES:
    src = 'import os, subprocess' + NL + body + NL
    got = sds.scan_text(src, 'tools/zz_fixture.py')
    ok('%-28s -> %d site(s)' % (label, want),
       got is not None and len(got) == want, got)

# ── D. THE UNIVERSE IS REPORTED AND NON-EMPTY ────────────────────────────
print(NL + 'D. the run itself')
r = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True,
                   text=True, encoding='utf-8', errors='replace')
out = r.stdout + r.stderr
ok('it exits 0 -- report-only, findings do not fail the run', r.returncode == 0,
   out[-300:])
ok('it prints CHECKED / UNIVERSE', 'CHECKED / UNIVERSE' in out)
m = re.search(r'CHECKED / UNIVERSE\s*:\s*(\d+) / (\d+)', out)
ok('and the universe is non-empty and fully checked',
   bool(m) and int(m.group(2)) > 100 and m.group(1) == m.group(2),
   m.group(0) if m else out[:200])
ok('it says REPORT-ONLY in its own output, not only in its header',
   'REPORT-ONLY' in out)

print(NL + '%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
