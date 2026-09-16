"""The negative control for tools/hover_separation_ci.py.

    python tests/hover_separation_ci_probe.py

The checker's own `--fixtures` classify synthetic commit dicts. This builds a
REAL git repository, makes REAL commits, and asserts the checker refuses the
violating one and passes the clean one -- because a correct classifier wired to
a range-reader that returns nothing reports exactly the same green.

── WHY THAT DISTINCTION IS NOT PEDANTIC HERE ───────────────────────────────
This checker's first version could never have fired at all. It keyed on
`hover_separation_audit.attribute()`, and a commit in which the auditor also
touches platform code is UNATTRIBUTABLE by construction -- so the one commit
the gate exists to refuse was the one it could not see. The synthetic fixtures
caught that before it shipped. What they cannot catch is the range-reading half
silently returning an empty list, which is what this file is for.

── IT BUILDS ITS OWN REPOSITORY AND NEVER TOUCHES THIS ONE ─────────────────
Every commit below is made in a throwaway directory under the system temp dir.
Nothing is committed to, mutated in, or restored in this clone -- so there is
no window in which a probe's fixture commit could be picked up by a push, which
is how five stranded PROBE commits reached origin on 2026-09-10.
"""
# REQUIREMENT: the separation checker is driven against a REAL git repository
#   with REAL commits, because a correct classifier wired to a range-reader
#   that returns nothing reports exactly the same green as one that works
#
import os
import shutil
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['tools/hover_separation_ci.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(REPO, 'tools', 'hover_separation_ci.py')
SKILL_DIR = '.claude/skills/sairn-hover-auditor'

# THE SUBPROCESS ARMS STAY THE PRIMARY EVIDENCE. Everything about a verdict --
# exit code, the wording of a refusal, whether the range was read at all -- is
# driven through the real CLI, because that is what CI invokes and an in-process
# call would not exercise it.
#
# The import is for the two arms that CANNOT be asked of a CLI: comparing two
# module constants for drift, and re-running the SUPERSEDED criteria against the
# same commits to show the rewrite was necessary. Both are statements about the
# module's internals; neither has a command line.
sys.path.insert(0, os.path.join(REPO, 'tools'))
import hover_separation_ci as R                                  # noqa: E402

FAILS = []


def arm(label, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + label
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        FAILS.append(label)


def git(wt, *args):
    return subprocess.run(['git', '-C', wt] + list(args), capture_output=True,
                          text=True, encoding='utf-8', errors='replace')


def write(wt, rel, body):
    p = os.path.join(wt, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(body)


def commit(wt, files, message):
    for rel, body in files.items():
        write(wt, rel, body)
    git(wt, 'add', '-A')
    r = git(wt, '-c', 'user.email=probe@fixture', '-c', 'user.name=probe',
            'commit', '-q', '-m', message)
    if r.returncode != 0:
        raise RuntimeError('commit failed: ' + (r.stderr or '')[:200])
    return git(wt, 'rev-parse', 'HEAD').stdout.strip()


def commits_for(wt, rng):
    """The checker's own range reader, pointed at the throwaway repo.

    Used by the ablation arm, which has to classify the SAME commits the shape
    rule saw -- reading them a second way would make the comparison meaningless.
    """
    import os as _os
    cwd = _os.getcwd()
    _os.chdir(wt)
    try:
        commits, err = R.commits_in(rng)
        if commits is None:
            raise RuntimeError('range unreadable in fixture repo: %s' % err)
        return commits
    finally:
        _os.chdir(cwd)


def run_checker(wt, rng):
    """The checker, run against the throwaway repo rather than this one."""
    r = subprocess.run([sys.executable, CHECKER, '--range', rng],
                       cwd=wt, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def tracked_dirty():
    st = git(REPO, 'status', '--porcelain').stdout
    return set(l for l in st.split('\n')
               if l.strip() and not l.startswith('??'))


def main():
    # ── THE BASELINE, TAKEN BEFORE ANYTHING RUNS (added 2026-09-16) ─────────
    # Arm 7 used to assert the clone had NO tracked file modified at all, which
    # answers a different question from the one it names. A session with
    # uncommitted work of its own made it go red, and the failure said "this
    # clone has no tracked file modified by the probe" about files the probe had
    # never touched -- measured, not hypothetical: it fired mid-session on
    # sixteen unrelated edits.
    #
    # This repo already has the sentence for that class and already has the
    # answer: "a tracked file modified DURING a suite run is indistinguishable
    # from residue after one", which tests/push_gate/check9_probe.py resolves by
    # reporting COULD NOT TELL rather than by guessing. The cheaper resolution
    # here is that the probe knows what the tree looked like before it started,
    # so the DIFFERENCE is attributable to it and nothing else is.
    before = tracked_dirty()
    wt = tempfile.mkdtemp(prefix='hover-sep-probe-')
    try:
        r = git(wt, 'init', '-q', '-b', 'main')
        if r.returncode != 0:
            print('COULD NOT RUN: git init failed -- NOTHING WAS VERIFIED. '
                  'This is not a pass.\n  ' + (r.stderr or '')[:200])
            return 3

        base = commit(wt, {'README.md': 'fixture repo\n'}, 'base')

        # 1. A CLEAN AUDITOR COMMIT -- its own skill directory only.
        clean = commit(wt, {SKILL_DIR + '/SKILL.md': 'audit notes\n'},
                       'auditor: notes')
        code, out = run_checker(wt, '%s..%s' % (base, clean))
        arm('a commit inside the auditor\'s own directory PASSES',
            code == 0, 'exit %s\n%s' % (code, out[-500:]))
        arm('...and it was seen, not skipped -- the range was not empty',
            '1 commit(s) in range' in out and
            '1 touch the auditor\'s skill directory' in out, out[:400])

        # 2. THE VIOLATION. The auditor's directory AND platform code, together.
        bad = commit(wt, {SKILL_DIR + '/SKILL.md': 'audit notes v2\n',
                          'api/sd-data.js': '// platform code\n'},
                     'auditor: notes, and a handler edit')
        code, out = run_checker(wt, '%s..%s' % (clean, bad))
        arm('a commit mixing the auditor\'s directory with PLATFORM CODE is '
            'REFUSED', code == 1, 'exit %s\n%s' % (code, out[-600:]))
        arm('...and the refusal NAMES the offending path',
            'api/sd-data.js' in out, out[-600:])
        # WHITESPACE-NORMALISED, because the tool WRAPS that sentence across
        # two print() calls and the literal phrase never appears contiguously.
        # The first version of this arm searched for it as written and went red
        # against correct output -- an assertion about formatting wearing the
        # costume of an assertion about content.
        arm('...and quotes the rule rather than only failing',
            'Never write, edit, or push platform code' in ' '.join(out.split()),
            out[-600:])

        # 3. THE OTHER DIRECTION, and it is the arm that matters most: a
        #    platform-only commit must NOT be refused. Without it, arm 2 is
        #    satisfied by a checker that refuses everything.
        plat = commit(wt, {'api/sd-data.js': '// more platform code\n'},
                      'a build agent edit')
        code, out = run_checker(wt, '%s..%s' % (bad, plat))
        arm('a platform-only commit is NOT refused -- the auditor is not the '
            'only committer', code == 0, 'exit %s\n%s' % (code, out[-500:]))

        # 4. BOOKKEEPING IS NOT PLATFORM CODE. A claim file alongside the
        #    auditor's directory must stay clean, or the one convention that
        #    could make the auditor identifiable could never be adopted.
        book = commit(wt, {SKILL_DIR + '/SKILL.md': 'audit notes v3\n',
                           '.claude/claims/hover.json': '[]\n'},
                      'auditor: notes and a claim')
        code, out = run_checker(wt, '%s..%s' % (plat, book))
        arm('the auditor\'s directory plus a CLAIM FILE is not a violation',
            code == 0, 'exit %s\n%s' % (code, out[-500:]))

        # 4b. THE BOUNDARY RUNNING THE OTHER WAY, IN REAL GIT. CLAUDE.md states
        #     it in terms -- "A build agent must not reach into that clone" --
        #     and it was covered only by a constructed commit dict in
        #     --fixtures. A synthetic arm and an end-to-end arm are not the same
        #     evidence, and the FAI on this tool named the difference as a gap
        #     rather than letting the fixture stand in for it.
        reach = commit(wt, {SKILL_DIR + '/SKILL.md': 'audit notes v4\n',
                            '.claude/claims/cody.json': '[]\n',
                            'api/sd-data.js': '// a build agent edit\n'},
                       'a build agent reaching into the auditor clone')
        code, out = run_checker(wt, '%s..%s' % (book, reach))
        arm('a BUILD AGENT reaching into the auditor\'s directory alongside '
            'platform work is REFUSED, in real git', code == 1,
            'exit %s\n%s' % (code, out[-500:]))
        arm('...and the refusal names the platform path, not the claim file',
            'api/sd-data.js' in out and 'claims/cody.json' not in out,
            out[-500:])

        # 4c. THE SCOPE DEFINITIONS MUST STILL AGREE, and the check must be
        #     able to say they do not. Two constants that must match, with
        #     nothing comparing them, is how they stop matching.
        gate, audit, agree = R.scope_definitions_agree()
        arm('the two scope definitions agree today', agree, (gate, audit))
        _real = R.A.AUDITOR_SCOPE
        try:
            R.A.AUDITOR_SCOPE = ('.claude/skills/somewhere-else/',)
            arm('...and the comparison can REPORT drift, so it is not comparing '
                'nothing', not R.scope_definitions_agree()[2])
        finally:
            R.A.AUDITOR_SCOPE = _real
        arm('...and it agrees again once restored', R.scope_definitions_agree()[2])

        # 4d. THE ABLATION. v1 keyed on hover_separation_audit.attribute(), and
        #     a commit in which the auditor ALSO touches platform code is
        #     unattributable BY CONSTRUCTION -- so the one commit the gate
        #     exists to refuse was the one it could not see. Shipped that way it
        #     would have been a green required check that meant nothing.
        #
        #     This drives the OLD criteria at the SAME violating commit and
        #     requires it to stay silent. Without this arm, "the mixed commit is
        #     refused" is true and says nothing about whether the rewrite was
        #     necessary.
        v1 = [c for c in commits_for(wt, '%s..%s' % (clean, bad))
              if R.A.attribute(c)[0] == 'hover' and R.offending(c)]
        arm('ABLATION: the v1 attribution rule finds NOTHING in the very commit '
            'the shape rule refuses -- which is why it was replaced',
            not v1, v1)

        # 5. AN UNREADABLE RANGE IS A THIRD STATE, not a pass.
        code, out = run_checker(wt, 'deadbeefdeadbeef..HEAD')
        arm('an unreadable range is COULD NOT RUN (exit 2), never a pass',
            code == 2, 'exit %s\n%s' % (code, out[-400:]))
        arm('...and it says nothing was checked',
            'NOTHING WAS CHECKED' in out.upper(), out[-400:])

        # 6. THE BLIND LOCK IS REACHABLE AND PASSES.
        r = subprocess.run([sys.executable, CHECKER, '--fixtures'],
                           cwd=REPO, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        arm('the checker\'s own --fixtures pass', r.returncode == 0,
            (r.stdout or r.stderr)[-400:])

        # 7. NOTHING WAS DONE TO THIS CLONE -- measured as a DIFFERENCE from
        # the baseline, so what the arm names is what the arm tests.
        introduced = sorted(tracked_dirty() - before)
        arm('this probe modified no tracked file in this clone',
            not introduced,
            'introduced: %s' % introduced[:5])
        if before:
            # Not a failure and not silence. The arm is still valid -- a
            # difference is attributable whatever the starting point -- but a
            # reader is entitled to know it ran against a tree that was already
            # dirty, because that is the condition under which the OLD arm gave
            # a wrong answer.
            print('  note  the working tree already had %d modified tracked '
                  'file(s) before this probe started; arm 7 measured the '
                  'DIFFERENCE, not the total' % len(before))
    finally:
        shutil.rmtree(wt, ignore_errors=True)

    print('\n%d failure(s)' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
