""""--hook" IS PAUSED AS OF 2026-09-10. See docs/2026-09-10-run-all-tests-hook-PAUSED.md.

The PostToolUse/Bash entry that ran this file with --hook has been removed from
.claude/settings.json. FIVE stranded PROBE commits reached origin/main in one
day and a sixth was caught locally; one of them deleted
`service_methods: body.service_methods` from api/legal-deadlines.js -- the exact
line whose absence made SAIRNlaw run Florida five days late for five days.

THE PROBE IS NOT WRONG, THE TRIGGER WAS. tests/push_gate/check4_probe.py commits
to `main` and resets back, which is safe for ONE runner on a QUIET branch; the
hook fired on every Bash tool call, so copies interleaved and whichever commit
survived a reset got published by the next push.

RUNNING THIS FILE BY HAND IS UNAFFECTED and remains the way to run the suite
deliberately. Only the automatic trigger is off. Re-enable per that document,
which carries the exact settings entry and the two conditions.

Run every test file in the repo, and NAME the ones it decided not to run.

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
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Fixtures that are data for another test, not tests themselves. Named, not
# pattern-excluded: a silent category exclusion is how a real test hides.
KNOWN_FIXTURES = {
    'tests/sql_preflight/probe_control.sql',
    'tests/sql_preflight/probe_defects.sql',
}

# ── ONE SUITE RUN AT A TIME PER CLONE (2026-09-09) ───────────────────────────
# WHY. Several probes under tests/ mutate a real tracked file and restore the
# bytes THEY read at their own start, in a finally. That is correct alone and
# wrong in parallel, and nothing serialised these runs: this hook fires on
# every `git push`, async, and on 2026-09-09 THREE concurrent `--hook` runs
# were observed alive in one tree (09:05:38, 09:06:06, 09:06:21) together with
# two copies of tests/seam_check/run_probe.py started in the same second.
#
#   run A snapshots the clean file, mutates it
#   run B snapshots THE MUTATED FILE as its "original"
#   run A restores clean
#   run B restores the mutation -- and it stays on disk
#
# That is how sairnvet.html repeatedly lost the corrupt-store guard from
# ebf2823e overnight, and how tools/reachability_exemptions.json kept a
# zzDefinitelyNotAFinding entry that no live_mode_probe run had failed to
# clean up. THE `finally` WAS NEVER THE DEFECT AND RESTORING HARDER CANNOT FIX
# IT -- both runs restored exactly what they read. The SNAPSHOT was the defect,
# so the fix is that there is only ever one run to snapshot against.
#
# Two things this deliberately does NOT do:
#   * it does not live in the working tree. An untracked lockfile in REPO would
#     show as `??` and make every clean-tree-dependent probe skip -- trading
#     this bug for the cascade the residue section below already warns about.
#   * staleness is by AGE, not by testing the holder's pid. os.kill(pid, 0) on
#     Windows does not test liveness, it calls TerminateProcess. A ceiling well
#     above the 400s hook timeout is the boring answer that cannot kill
#     somebody's process; a killed run costs one skipped cycle, not a
#     permanent block.
LOCK = os.path.join(
    tempfile.gettempdir(),
    'sairn-suite-%s.lock' % hashlib.sha256(REPO.encode('utf-8')).hexdigest()[:16])
LOCK_MAX_AGE = 900


def acquire_lock():
    """True if this process now owns the suite lock, False if another run has it."""
    for _ in range(2):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, ('%d %f\n' % (os.getpid(), time.time())).encode('utf-8'))
            os.close(fd)
            return True
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(LOCK)
            except OSError:
                continue                      # vanished between the calls; retry
            if age < LOCK_MAX_AGE:
                return False
            try:
                os.remove(LOCK)               # abandoned by a killed run
            except OSError:
                return False
    return False


def release_lock():
    try:
        os.remove(LOCK)
    except OSError:
        pass


# ── A SHRINKING SUITE MUST NOT REPORT "ALL N PASS" (2026-09-10) ────────────
# discover() walks tests/ and counts what it finds, and NOTHING said what it
# expected to find. Delete twenty test files and this runner reports
# "ALL 161 TEST FILES PASS" -- a true sentence about a suite that just lost
# twenty guards, and nothing anywhere says so.
#
# Found by the second half of the self-referential-guard sweep
# (docs/2026-09-10-self-referential-guard-sweep.md): a guard that derives its
# own SUBJECT from the thing it guards cannot see that subject disappear. The
# suites were swept first and twelve of thirteen already pinned a count. The
# RUNNER, which derives the largest subject list on the platform, pinned
# nothing.
#
# IT IS A FLOOR AT BOTH ENDS -- `count >= pin`, never an equality.
# MICHAEL'S DECISION, 2026-09-11, and the history is kept because the tradeoff
# is the part worth knowing.
#
# It shipped for a few hours with `tests/run_all_tests_floor_probe.py`
# asserting EQUALITY, on the reasoning that a pin below the real count is a
# dead zone nothing can see. IT FIRED ON THE VERY FIRST REBASE AFTER IT WAS
# WRITTEN -- 181 became 184 because other clones had added tests -- failing the
# suite for a session that had added nothing. With four clones pushing, that is
# not an edge case, it is the normal night.
#
# The call: a floor keeps all of the real protection, because any silent
# DELETION still fails immediately, and drops the only false-positive shape,
# which was a legitimate ADDITION arriving by rebase. A stale floor after
# growth is cosmetic -- it leaves a window in which that many deletions would
# be quiet -- and it is bumped as housekeeping. Friction on every rebase is
# what gets a gate switched off out of annoyance, and a switched-off gate
# protects nothing.
#
# Growth is still PRINTED by the probe, with the number to write. Lowering the
# pin is a deliberate edit that shows up in a diff, which is exactly the moment
# somebody should be asked why the suite is smaller.
#
# THE NUMBER IS THE MEASURED COUNT AT THIS COMMIT, NOT AN ESTIMATE WITH
# HEADROOM -- corrected 2026-09-10, hours after the floor was first written at
# 163 while discover() actually returned 180. Seventeen test files could have
# been deleted with the guard silent, which is 85% of the twenty-file example
# its own comment uses. A floor set below the real count is not a cautious
# floor; it is a dead zone, and an unmeasured one.
#
# THERE IS NO SKEW TO LEAVE HEADROOM FOR, and that was checked rather than
# assumed: this constant travels in the same commit as the test files it
# counts, so a clone behind `main` has the older floor AND the older files.
# A rebase cannot deliver one without the other. Re-measure with
# `python -c "import sys;sys.path.insert(0,'tools');import run_all_tests as
# r;js,py,_=r.discover();print(len(js)+len(py))"`.
MIN_TEST_FILES = 184

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


# ── DOES THIS COMMAND ACTUALLY PUSH? ─────────────────────────────────────────
# `git push` has to appear where a COMMAND goes, not merely somewhere in the
# text. The first version of this gate used a bare `\bgit\s+push\b` against the
# whole command, on the reasoning that a stray mention only costs one
# report-only run -- and the VERY NEXT COMMIT tripped it, because this repo's
# commit messages quote the words: `git commit -F -` with a heredoc explaining
# that "an ordinary `git push origin main` raced one of the probes". The suite
# ran, dirtied the tree mid-commit, and restored itself. Cheap once; not cheap
# as a habit, since the incident this file exists to prevent was a probe commit
# racing a real push.
#
# So a match counts only when everything between the last command separator and
# it is whitespace or `VAR=value` assignments -- which keeps the two real
# spellings used here (`git push ...` and `SAIRN_SEED_GATE=off git push ...`)
# and drops mentions inside prose, since those sit after a backtick or a word.
#
# NAMED FALSE NEGATIVES, because trading a false alarm for a silent one without
# saying so is the failure mode this repo keeps recording: a push wrapped in
# another command -- `sudo git push`, `time git push`, `xargs git push`, or one
# built by a script -- does not match and gets no report. That is the same
# blind spot tools/deploy_verify_notify.py already documents for pushes driven
# from Python, and the cost is a missing report rather than a missing check;
# `python tools/run_all_tests.py` by hand still runs everything.
PUSH_RE = re.compile(
    r"""(?:^|[;&|\n(]|&&|\|\|)          # a command position
        (?:\s*[A-Za-z_][A-Za-z0-9_]*=(?:"[^"]*"|'[^']*'|\S*))*   # env prefixes
        \s*git\s+push\b""",
    re.VERBOSE)


def pushes(cmd):
    """True if this Bash command text runs `git push` as a command."""
    return bool(PUSH_RE.search(cmd))


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
    # ── THE PAYLOAD IS THE GATE. IT IS NOT DECORATION -- corrected 2026-09-09.
    # This read the payload and threw it away under a comment saying "nothing
    # here needs it", on the belief that this entry in .claude/settings.json
    # restricted it to pushes:
    #
    #     { "command": "python tools/run_all_tests.py --hook",
    #       "if": "Bash(git push*)" }        <-- THERE IS NO `if` FIELD
    #
    # A Claude Code hook entry's only gate is `matcher`, which matches the TOOL
    # NAME. `matcher: "Bash"` means every Bash tool call; the unknown key was
    # ignored in silence. Measured 2026-09-09, not reasoned: ten concurrent
    # copies of this suite in one clone inside four minutes on a single push,
    # twenty-seven live processes before it was caught, and a `PROBE clean
    # endpoint change` commit on origin/main because an ordinary push raced one
    # of the probes that commit to `main`.
    #
    # THE LOCK ABOVE IS NOT THIS FIX AND DOES NOT SUBSUME IT. The lock stops a
    # second run from corrupting the first one's restores; it still leaves one
    # full suite -- which mutates tracked files and commits to `main` -- running
    # after every `git status`, `git log` and `node --check` anybody types.
    #
    # Its sibling tools/deploy_verify_notify.py:57 had this gate in code from
    # the start and never misfired. Two hooks, one config block, one wrong
    # belief between them: A HOOK THAT LOOKS GATED IN CONFIG IS UNGATED UNTIL
    # THE HOOK ITSELF CHECKS. Held by tests/run_all_tests_hook_gate_probe.py.
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    cmd = (payload.get('tool_input', {}) or {}).get('command', '') or ''
    # An UNREADABLE or absent payload falls through and runs, deliberately:
    # that is `python tools/run_all_tests.py --hook` typed by hand, and it is
    # the same fail-open standard the other hooks here hold. If a future
    # payload shape stops parsing, this hook goes back to running on every Bash
    # call and this is the line to look at.
    if payload and not pushes(cmd):
        return 0
    # ── A DENIED PUSH IS NOT A PUSH -- added 2026-09-10, hours after the gate
    # above. The command gate was necessary and not sufficient: PostToolUse
    # fires whether or not the command succeeded, so every push the PRE-tool
    # push gate DENIED still launched the whole suite. Observed the same day --
    # two concurrent runs at 09:28 and 09:32 with no successful push between
    # them, and this repo denies pushes routinely (seed drift, pre-auth
    # disclosure, a probe's own fixture). The suite then commits fixtures on
    # `main` and mutates tracked files, so the denial that was supposed to
    # protect the branch is what dirtied it, and the next push attempt raced
    # the probe commit and was denied again. A loop that feeds itself.
    #
    # tools/deploy_verify_notify.py:61 has had this guard from the start, for
    # the same reason stated there: "a failed push has nothing new to verify
    # against". Second time today that file was already right.
    resp = payload.get('tool_response') or {}
    if isinstance(resp, dict) and resp.get('success') is False:
        return 0
    # A second concurrent run does not queue -- it declines and SAYS SO. Running
    # it would corrupt the first one's snapshots (see the LOCK block above), and
    # staying silent about declining would make "the suite ran after that push"
    # false in exactly the way this file exists to stop.
    if not acquire_lock():
        print(json.dumps({
            'systemMessage': 'Full test suite after push: SKIPPED, already running.',
            'hookSpecificOutput': {
                'hookEventName': 'PostToolUse',
                'additionalContext':
                    'The full suite did not run after this push: another run of it '
                    'is still in progress in this clone, and two at once corrupt '
                    "each other's file restores. Nothing was verified by this "
                    'push. The in-flight run covers the same tree.',
            },
        }))
        return 0
    try:
        return _hook_body()
    finally:
        release_lock()


def _hook_body():
    # ── THE FLOOR REACHES THE UNATTENDED COPY TOO (2026-09-10) ───────────────
    # The floor was added to _main_body() first and this function was left
    # alone, which is the exact shape CLAUDE.md records for
    # tools/sairn_claim_hook.py: a defect fixed in the copy a human invokes and
    # left in the copy that runs on its own. It is WORSE here than it looks,
    # because the two copies are not equally important for this particular
    # guard -- a deletion you made yourself is one you can see in your own
    # diff, while a deletion that ARRIVES BY REBASE from another clone is
    # invisible to you and this hook was the only thing positioned to notice.
    # The half that could not see it was the half that mattered.
    #
    # It REPORTS and never blocks, the same standing decision as everything
    # else in this hook (2026-09-08): the exit code stays 0 and the sentence is
    # the whole mechanism.
    js, py, unrun = discover()
    shrunk = (len(js) + len(py)) < MIN_TEST_FILES
    failures, skipped = _run(js, py, quiet=True)
    if not failures and not skipped and not shrunk:
        return 0
    lines = []
    if shrunk:
        lines.append(
            'THE SUITE HAS SHRUNK: %d test files discovered, %d expected at '
            'minimum. Files were DELETED or moved out of tests/ -- possibly not '
            'by you, since a rebase carries another clone\'s deletion in '
            'silently. Do not raise MIN_TEST_FILES to clear this; find out '
            'which guards left.' % (len(js) + len(py), MIN_TEST_FILES))
    if failures:
        lines.append('%d test file(s) FAILING after this push:' % len(failures))
        lines += ['  %s -- %s' % (rel, tail) for _, rel, tail in failures[:12]]
    if skipped:
        lines.append('%d test file(s) SKIPPED, so they verified nothing:' % len(skipped))
        lines += ['  %s -- %s' % (rel, why) for _, rel, why in skipped[:12]]
    lines.append('Run `python tools/run_all_tests.py` to see the whole picture.')
    lines.append('REPORT ONLY -- this hook never blocks a push. It exists because '
                 'every session was running 53 of these files and calling it the suite.')
    # THE HEADLINE CARRIES THE SHRINK, because it is the only line guaranteed
    # to be read. "0 failing, 0 skipped" over an additionalContext saying the
    # suite lost guards is two adjacent statements where one is reassuring and
    # the other is the news -- the badge-beside-an-honest-field shape.
    head = 'Full test suite after push: %d failing, %d skipped.' \
           % (len(failures), len(skipped))
    if shrunk:
        head = 'Full test suite after push: SUITE HAS SHRUNK to %d files ' \
               '(expected >= %d); %d failing, %d skipped.' \
               % (len(js) + len(py), MIN_TEST_FILES, len(failures), len(skipped))
    print(json.dumps({
        'systemMessage': head,
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


def _tree():
    r = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO,
                       capture_output=True, text=True)
    return [l for l in (r.stdout or '').splitlines() if l.strip()]


def main(argv):
    if '--hook' in argv:
        return hook_main()
    # EXIT 3, the same "could not run is not a pass" code the probes use.
    if not acquire_lock():
        print('SKIPPED: another run of this suite already holds the lock for this')
        print('clone. Two at once corrupt each other -- a probe that mutates a')
        print('tracked file snapshots whatever is on disk when it starts, so the')
        print("second run adopts the first's mutation as its 'original' and")
        print('restores that. Nothing was verified. Wait for the other run.')
        return 3
    try:
        return _main_body('--quiet' in argv)
    finally:
        release_lock()


def _main_body(quiet):
    before = _tree()
    js, py, unrun = discover()
    # EXIT 3 MEANS SKIPPED, and it is reported apart from both other answers.
    # Two push-gate probes commit planted fixtures and reset, so they refuse to
    # run against a dirty tree -- a guard that protects real work and must
    # stay. They used to exit 1 for that, which read as "check 4 is broken"
    # when nothing about check 4 had been examined. A precondition is not a
    # failure, and it is not a pass either.
    failures, skipped = _run(js, py, quiet)

    # ── RESIDUE IS REPORTED, BECAUSE A CASCADE LOOKS LIKE A BUG (2026-09-08)
    # Several probes mutate a tracked file and restore it in a finally. If one
    # is interrupted, the residue makes EVERY later clean-tree-dependent probe
    # fail for a reason that has nothing to do with it -- which is exactly what
    # happened while this runner was being written: four files went red at
    # once, and every one of them passed individually on a clean tree.
    #
    # It does NOT restore anything. `git checkout --` on somebody's working
    # tree to make a test suite happy is a far worse trade than a loud
    # sentence. Naming the files and saying results after this point may be
    # cascade is the whole job.
    after = _tree()
    print('')
    print('RAN: %d JS + %d PY = %d files (%d skipped)'
          % (len(js), len(py), len(js) + len(py), len(skipped)))
    shrunk = (len(js) + len(py)) < MIN_TEST_FILES
    if shrunk:
        print('')
        print('THE SUITE HAS SHRUNK: %d files discovered, %d expected at minimum.'
              % (len(js) + len(py), MIN_TEST_FILES))
        print('    Test files have been DELETED or moved out of tests/. A pass '
              'below this line')
        print('    would be a true sentence about a suite that has lost guards. If the '
              'removal')
        print('    was deliberate, lower MIN_TEST_FILES in the same commit and say why.')
    residue = [l for l in after if l not in before]
    if residue:
        print('')
        print('THE SUITE DIRTIED THE TREE (%d path(s)) -- a probe did not clean up:'
              % len(residue))
        for l in residue:
            print('    %s' % l)
        print('    Results above may be CASCADE, not real: a modified tracked file')
        print('    fails every clean-tree probe after it. Restore with git and re-run')
        print('    before believing any failure. Nothing was restored for you.')
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
        if shrunk:
            print('NOT ALL WELL: every discovered file passed, but the suite is '
                  'smaller than it was.')
        else:
            print('ALL %d TEST FILES PASS' % (len(js) + len(py)))
    # An unrecognised file is a warning, not a failure: it may genuinely be a
    # fixture. It exits 0 so this never becomes the thing people switch off,
    # and it is printed every time so it cannot be missed either.
    # THE FLOOR REACHES THE EXIT CODE. A shrunken suite that still exits 0 is a
    # sentence nobody acts on, which is the exact failure mode the sweep that
    # added this is about.
    return 1 if (failures or shrunk) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
