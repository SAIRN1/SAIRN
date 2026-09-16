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
import os
import shutil
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['tools/hover_separation_ci.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(REPO, 'tools', 'hover_separation_ci.py')
SKILL_DIR = '.claude/skills/sairn-hover-auditor'

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


def run_checker(wt, rng):
    """The checker, run against the throwaway repo rather than this one."""
    r = subprocess.run([sys.executable, CHECKER, '--range', rng],
                       cwd=wt, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def main():
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

        # 7. NOTHING WAS DONE TO THIS CLONE.
        st = git(REPO, 'status', '--porcelain').stdout
        dirty = [l for l in st.split('\n')
                 if l.strip() and not l.startswith('??')]
        arm('this clone has no tracked file modified by the probe',
            not dirty, dirty[:5])
    finally:
        shutil.rmtree(wt, ignore_errors=True)

    print('\n%d failure(s)' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
