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
repo -- 130 as of 2026-09-08 and growing, so re-count rather than trust that
number. tests/**/*.py is run by nothing. tests/sairncare/ (18 JS files) and
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

── WIRED REPORT-ONLY, ON MICHAEL'S DECISION 2026-09-08 ──────────────────────
`--hook` runs as an async PostToolUse hook after every `git push` and NEVER
blocks: it exits 0 whatever it finds, and stays silent unless something failed
or was skipped. That is the same promotion path checks 5 and 7 took, for the
same reason -- this one has a KNOWN false-alarm shape (two probes need a clean
tree), and a gate that cries wolf before it has earned trust teaches people to
route around it. Promoting it to blocking is a later decision, and the
precondition it must clear is that the skip case has been quiet in practice.

Silence on a clean run is deliberate. A notice that fires every push is a
notice nobody reads. A SKIPPED file does notify, because "could not run" being
invisible is the whole problem this exists to fix.

Run:  python tools/run_all_tests.py [--quiet]
      python tools/run_all_tests.py --hook   (reads a hook payload on stdin)
"""
import json
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


def hook_main():
    """PostToolUse hook mode: run everything, stay silent unless something is wrong.

    REPORT-ONLY, ON MICHAEL'S DECISION 2026-09-08, and the reasoning is the
    same promotion path checks 5 and 7 took: a gate that produces a false alarm
    before it has earned trust teaches people to route around it. This one has
    a known false-alarm shape -- two probes need a clean tree -- so it reports
    and never blocks until that has been proven quiet in practice.
    It exits 0 ALWAYS. The only thing it can do is say something.

    Silence on a clean run is deliberate: a notice that fires on every push is
    a notice nobody reads. Skipped files DO produce a notice, because "could
    not run" is exactly the thing this hook exists to stop being invisible.
    """
    try:
        json.load(sys.stdin)          # the hook payload; nothing here needs it
    except Exception:
        pass
    js, py, unrun = discover()
    failures, skipped = _run(js, py, quiet=True)
    if not failures and not skipped:
        return 0
    lines = []
    if failures:
        lines.append('%d test file(s) FAILING after this push:' % len(failures))
        lines += ['  %s -- %s' % (rel, tail) for _, rel, tail in failures[:12]]
    if skipped:
        lines.append('%d test file(s) SKIPPED, so they verified nothing:' % len(skipped))
        lines += ['  %s -- %s' % (rel, why) for _, rel, why in skipped[:12]]
    lines.append('Run `python tools/run_all_tests.py` to see the whole picture.')
    lines.append('REPORT ONLY -- this hook never blocks a push. It exists because '
                 'every session was running 53 of these files and calling it the suite.')
    print(json.dumps({
        'systemMessage': 'Full test suite after push: %d failing, %d skipped.'
                         % (len(failures), len(skipped)),
        'hookSpecificOutput': {
            'hookEventName': 'PostToolUse',
            'additionalContext': '\n'.join(lines),
        },
    }))
    return 0


def _run(js, py, quiet):
    failures, skipped = [], []
    for kind, cmd, files in (('node', ['node'], js), ('py', [sys.executable], py)):
        for rel in files:
            r = subprocess.run(cmd + [rel], cwd=REPO, capture_output=True, text=True)
            out = (r.stdout or r.stderr or '').strip().splitlines()
            if r.returncode == 3:
                skipped.append((kind, rel, next((l for l in out if l.startswith('SKIPPED')),
                                                'SKIPPED')))
            elif r.returncode != 0:
                failures.append((kind, rel, out[-1] if out else '(no output)'))
            elif not quiet:
                print('  ok   %-5s %s' % (kind, rel))
    return failures, skipped


def main(argv):
    if '--hook' in argv:
        return hook_main()
    quiet = '--quiet' in argv
    js, py, unrun = discover()
    # EXIT 3 MEANS SKIPPED, and it is reported apart from both other answers.
    # Two push-gate probes commit planted fixtures and reset, so they refuse to
    # run against a dirty tree -- a guard that protects real work and must
    # stay. They used to exit 1 for that, which read as "check 4 is broken"
    # when nothing about check 4 had been examined. A precondition is not a
    # failure, and it is not a pass either.
    failures, skipped = _run(js, py, quiet)

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
