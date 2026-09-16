"""A self-test is only a check if it can FAIL. This breaks each tool and requires it to.

    python tests/run_selftest_independence_probe.py
    python tests/run_selftest_independence_probe.py --list

── WHY THIS EXISTS, AND WHAT IT IS NOT ────────────────────────────────────────
`tests/run_selftest_sweep_probe.py` closed the wiring gap: six tools carried a
`--selftest` that nothing ran, and now something runs them. That proved they
PASS. It proved nothing about whether they can fail.

`docs/2026-09-13-cross-domain-disciplines.md` section 5 is the reason that
matters: the deep check runs with its subject NOT trusted. A `_selftest()` is
written in the same file, in the same commit, by the same hand as the code it
checks. Running it does not make it independent. **Breaking the subject from
OUTSIDE and requiring the self-test to notice does** -- that judgment is made
here, by a different file, against a defect the tool's author did not choose.

── THE THREE SUBJECTS, AND WHY THESE THREE ────────────────────────────────────
All Tier A by consequence-if-wrong, and all three MUTATE TRACKED FILES, which is
what makes a silent self-test expensive:

  sabotage.py      plants a defect in a real source file. Its whole safety
                   property is that a failed plant REFUSES rather than reporting
                   on an untouched file.
  line_endings.py  rewrites the bytes of tracked files. A wrong three-state
                   answer reports a checkout artefact as drift, or drift as a
                   checkout artefact.
  nhi_register.py  writes a governance document and REFUSES when the
                   hand-written half no longer covers the repo. A refusal that
                   stopped refusing would publish a credential register with
                   holes in it.

── EVERY MUTANT IS DECLARED WITH THE ARM IT SHOULD TRIP ───────────────────────
A mutation harness that only reports a count says nothing about WHICH check is
load-bearing. Each entry below names the self-test arm it is aimed at, so a
survivor is immediately actionable: either the arm does not cover that line, or
the line does not matter.

── SAFETY ─────────────────────────────────────────────────────────────────────
Each tool is mutated IN PLACE and restored in a `finally`. `git status
--porcelain` is captured before and after and any difference FAILS -- the same
guard the sweep probe uses, and for the same reason: "it restores itself" is the
assumption, not the evidence.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (tool, flag, [(name, aimed_at_arm, old, new)])
SUBJECTS = [
    ('tools/sabotage.py', '--selftest', [
        ('plant accepts a DUPLICATED anchor',
         'a DUPLICATED anchor refuses rather than hitting the first',
         '    n = src.count(anchor)\n    if n != occurrences:',
         '    n = src.count(anchor)\n    if False:'),
        ('plant accepts a NO-OP replacement',
         'a no-op replacement refuses -- the purest form of the bug',
         '    if out == src:', '    if False:'),
        ('plant_at_line ignores the expected line, so a STALE INDEX damages a '
         'random line',
         'a STALE index refuses instead of damaging a random line',
         '    if lines[idx].rstrip() != expected.rstrip():',
         '    if False:'),
        ('write_and_verify skips the read-back, so the claim is about memory '
         'and not about the bytes the next process reads',
         'a marker that is NOT in the text refuses',
         '    if marker not in on_disk:', '    if False:'),
        ('Planted stops restoring the subject',
         'the subject is restored after an exception',
         '        if self.original is not None:', '        if False:'),
    ]),
    ('tools/line_endings.py', '--selftest', [
        ('compare() collapses to TWO states -- the false-alarm shape the module '
         'exists to remove',
         'same content, different endings -> ENDINGS_ONLY',
         "    if normalise(a) == normalise(b):\n        return 'ENDINGS_ONLY'",
         "    if False:\n        return 'ENDINGS_ONLY'"),
        ('compare() calls a real difference ENDINGS_ONLY, which is the '
         'dangerous direction: drift reported as a checkout artefact',
         'a real difference is NOT masked by normalising',
         "    return 'DIFFERS'", "    return 'ENDINGS_ONLY'"),
        ('MIXED is folded into one of the two pure answers',
         'mixed is its own answer, not one of the two',
         "                     else 'MIXED' if crlf and lone_lf",
         "                     else 'CRLF' if crlf and lone_lf"),
    ]),
    ('tools/nhi_register.py', '--selftest', [
        ('the refusal stops firing on an UNATTRIBUTED credential, so the '
         'register publishes with a hole in it',
         'an unattributed CREDENTIAL refuses',
         '    if unattributed or unregistered:',
         '    if unregistered:'),
        ('the refusal stops firing on an UNREGISTERED role',
         'a `create role` with no entry refuses',
         '    if unattributed or unregistered:',
         '    if unattributed:'),
        ('every declared credential is treated as attributed, so nothing can '
         'ever be unattributed',
         'an unattributed CREDENTIAL refuses',
         '    unattributed = [c for c in env_credentials() if c not in declared]',
         '    unattributed = []'),
    ]),
]

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def porcelain():
    p = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return None if p.returncode != 0 else sorted(p.stdout.splitlines())


def run_selftest(tool, flag):
    p = subprocess.run([sys.executable, tool, flag], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=180)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


if '--list' in sys.argv[1:]:
    for tool, flag, muts in SUBJECTS:
        print('%s  %s  (%d mutants)' % (tool, flag, len(muts)))
        for name, arm, _o, _n in muts:
            print('    %-62s -> %s' % (name[:62], arm[:60]))
    sys.exit(0)

BEFORE = porcelain()
check('git status is readable, so the tree can be compared afterwards -- '
      'without it nothing here could safely mutate a tracked file',
      BEFORE is not None)

for tool, flag, muts in SUBJECTS:
    print('\n%s -- %d mutant(s)' % (tool, len(muts)))
    path = os.path.join(REPO, tool)
    ORIG = io.open(path, encoding='utf-8').read()

    rc, out = run_selftest(tool, flag)
    check('%s: the self-test passes UNMUTATED, or every arm below is '
          'meaningless' % os.path.basename(tool), rc == 0, out[-300:])

    try:
        for name, arm, old, new in muts:
            if old not in ORIG:
                check('%s: ANCHOR MISSING -- the mutant could not be planted, so '
                      'the arm did not run. That is a could-not-tell and is not '
                      'a pass' % name, False, old[:160])
                continue
            io.open(path, 'w', encoding='utf-8', newline='\n').write(
                ORIG.replace(old, new, 1))
            c = subprocess.run([sys.executable, '-m', 'py_compile', path],
                               capture_output=True)
            if c.returncode != 0:
                check('%s: the mutant does not compile, so nothing was tested'
                      % name, False, (c.stderr or b'')[:200])
                continue
            mrc, mout = run_selftest(tool, flag)
            check('%s -> caught' % name, mrc != 0,
                  'the self-test still PASSED with this planted. The arm it was '
                  'aimed at is "%s" -- either that arm does not cover this line, '
                  'or the line does not matter.' % arm)
            if mrc != 0:
                named = arm.split(' -- ')[0][:40].lower() in mout.lower()
                check('   ...and the arm that caught it is the one aimed at: %s'
                      % arm[:60], named or 'FAIL' in mout,
                      mout[-300:])
    finally:
        io.open(path, 'w', encoding='utf-8', newline='\n').write(ORIG)

    rc, out = run_selftest(tool, flag)
    check('%s: the self-test passes again after restore, so the mutants left '
          'nothing behind' % os.path.basename(tool), rc == 0, out[-300:])

print('\nTHE TREE MUST BE AS IT WAS')
AFTER = porcelain()
check('git status is still readable', AFTER is not None)
if BEFORE is not None and AFTER is not None:
    check('byte-for-byte unchanged. Three tools were deliberately broken and '
          'restored; "the finally clause runs" is the assumption this arm '
          'refuses to make', BEFORE == AFTER,
          {'appeared': [l for l in AFTER if l not in BEFORE][:5],
           'disappeared': [l for l in BEFORE if l not in AFTER][:5]})

print('\nWHAT THIS DOES AND DOES NOT ESTABLISH')
print('  IT DOES: each self-test FAILS when its subject is broken from outside,')
print('  against a defect its author did not choose. That is the independence')
print('  running it in the suite cannot supply.')
print('  IT DOES NOT: prove the self-test covers everything. A mutant nobody')
print('  wrote is a line nobody checked, and the list above is finite by hand.')

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
