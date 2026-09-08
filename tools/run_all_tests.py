"""Run every test file in the repo, and NAME the ones it decided not to run.

WHY THIS EXISTS, and it is not tidiness. On 2026-09-08 two probes were found
red, and neither had been red for a reason anybody chose:

  tests/fail_open_browser_probe.py       -- 2 arms dead since the fourteenth
                                            storage loader was fixed
  tests/reachability/live_mode_probe.py  -- 5 arms dead since 2026-09-02, six
                                            days, because the seven findings it
                                            named were removed the day after it
                                            was written

Both are the same shape -- a probe pinned to a current defect rots the moment
that defect is fixed -- and both went unnoticed for the same reason: EVERY
SESSION RUNS `for f in tests/*.js`, which is 53 of the 125 test files in this
repo. tests/**/*.py is run by nothing. tests/sairncare/ (18 JS files) and
tests/sairnsenior/ are run by nothing. api/*.test.js only if someone remembers.

So "the suite passes" has been a claim about 42% of the suite, stated in good
faith in commit after commit, including mine.

── WHAT IT DOES ──────────────────────────────────────────────────────────────
Walks tests/ recursively and api/ shallowly, runs every .js through node and
every .py through this interpreter, and reports pass/fail per file with a
non-zero exit if any failed.

── WHAT IT REFUSES TO DO SILENTLY ───────────────────────────────────────────
It prints an UNRUN section naming every file under tests/ that it did not
execute, whatever the reason -- a .sql fixture, a .mjs nobody anticipated, a
new extension. A runner that quietly ignores what it does not recognise is how
this problem started, so the discovery rule is visible on every run rather
than implied by a number.

It does NOT run anything under __pycache__, and it does not treat a fixture
(.sql, .json) as a failure -- those are listed as unrun and expected.

── WHAT IT IS NOT ────────────────────────────────────────────────────────────
Not a gate. Nothing here blocks a push; wiring it into the push hook is a
separate decision with a real cost (125 subprocesses) and belongs to whoever
owns that hook. This is the one command that tells the truth when someone
chooses to ask.

Run:  python tools/run_all_tests.py [--quiet]
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Fixtures that are data for another test, not tests themselves. Named, not
# pattern-excluded: a silent category exclusion is how a real test hides.
KNOWN_FIXTURES = {
    'tests/sql_preflight/probe_control.sql',
    'tests/sql_preflight/probe_defects.sql',
}


def discover():
    js, py, unrun = [], [], []
    for root, dirs, files in os.walk(os.path.join(REPO, 'tests')):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in sorted(files):
            rel = os.path.relpath(os.path.join(root, f), REPO).replace(os.sep, '/')
            if f.endswith('.js'):
                js.append(rel)
            elif f.endswith('.py'):
                py.append(rel)
            else:
                unrun.append(rel)
    api = os.path.join(REPO, 'api')
    for f in sorted(os.listdir(api)):
        if f.endswith('.test.js'):
            js.append('api/' + f)
    return js, py, unrun


def main(argv):
    quiet = '--quiet' in argv
    js, py, unrun = discover()
    # EXIT 3 MEANS SKIPPED, and it is reported apart from both other answers.
    # Two push-gate probes commit planted fixtures and reset, so they refuse to
    # run against a dirty tree -- a guard that protects real work and must
    # stay. They used to exit 1 for that, which read as "check 4 is broken"
    # when nothing about check 4 had been examined. A precondition is not a
    # failure, and it is not a pass either.
    failures, skipped = [], []
    for kind, cmd, files in (('node', ['node'], js), ('py', [sys.executable], py)):
        for rel in files:
            r = subprocess.run(cmd + [rel], cwd=REPO, capture_output=True, text=True)
            out = (r.stdout or r.stderr or '').strip().splitlines()
            if r.returncode == 3:
                first = next((l for l in out if l.startswith('SKIPPED')), 'SKIPPED')
                skipped.append((kind, rel, first))
            elif r.returncode != 0:
                failures.append((kind, rel, out[-1] if out else '(no output)'))
            elif not quiet:
                print('  ok   %-5s %s' % (kind, rel))

    print('')
    print('RAN: %d JS + %d PY = %d files (%d skipped)'
          % (len(js), len(py), len(js) + len(py), len(skipped)))
    if skipped:
        print('SKIPPED (%d) -- a precondition was not met, NOT a pass:' % len(skipped))
        for kind, rel, why in skipped:
            print('    %-52s %s' % (rel, why))
    # Named on every run, pass or fail. The point of this section is that a
    # file this runner does not understand is VISIBLE rather than absent.
    print('NOT RUN (%d):' % len(unrun))
    for rel in unrun:
        note = 'known fixture' if rel in KNOWN_FIXTURES else 'UNRECOGNISED -- is this a test?'
        print('    %-52s %s' % (rel, note))
    surprises = [u for u in unrun if u not in KNOWN_FIXTURES]

    if failures:
        print('')
        print('FAILURES (%d):' % len(failures))
        for kind, rel, tail in failures:
            print('  FAIL %-5s %-52s %s' % (kind, rel, tail))
    print('')
    ran = len(js) + len(py) - len(skipped)
    if failures:
        print('%d FAILING TEST FILE(S)' % len(failures))
    elif skipped:
        print('%d of %d test files pass; %d SKIPPED and therefore unverified '
              '-- read the SKIPPED list' % (ran, len(js) + len(py), len(skipped)))
    elif surprises:
        print('all %d ran clean, but %d file(s) under tests/ were not recognised '
              '-- read the NOT RUN list' % (len(js) + len(py), len(surprises)))
    else:
        print('ALL %d TEST FILES PASS' % (len(js) + len(py)))
    # An unrecognised file is a warning, not a failure: it may genuinely be a
    # fixture. It exits 0 so this never becomes the thing people switch off,
    # and it is printed every time so it cannot be missed either.
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
