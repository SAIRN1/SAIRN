"""The control for tools/sairn_rebase_resolve.py -- it must RESOLVE one class and REFUSE the other.

Run: python tests/run_rebase_resolve_probe.py

Every arm builds a REAL conflict in a throwaway git worktree -- two branches
editing the same line, rebased into each other -- rather than hand-writing a
file with markers in it. A tool whose whole subject is what a rebase leaves
behind must be tested against what a rebase actually leaves behind; a
hand-written fixture would agree with whatever I imagined git does.

BOTH DIRECTIONS ON EVERY ARM, because a tool that refuses everything passes
"it refused the source file" and a tool that stages everything passes "it staged
the generated one".

NOTHING HERE TOUCHES THE REAL CLONE. Each arm gets its own worktree on its own
detached branch and removes it in a finally.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = os.path.join(REPO, 'tools', 'sairn_rebase_resolve.py')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:500]))
    if not cond:
        fails.append(name)


def git(wt, *args):
    return subprocess.run(['git', '-C', wt] + list(args),
                          capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def run_tool(wt, *extra):
    r = subprocess.run([sys.executable, TOOL] + list(extra), cwd=wt,
                       capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def with_conflict(tag, rel, mutate_a, mutate_b, body):
    """Make a real rebase conflict on `rel`, then hand the worktree to `body`."""
    wt = tempfile.mkdtemp(prefix='sairn-reb-')
    shutil.rmtree(wt, ignore_errors=True)
    add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach',
                          wt, 'HEAD'], capture_output=True, text=True)
    if add.returncode != 0:
        print('SKIPPED: could not create a worktree -- nothing was verified.')
        print(add.stderr.strip()[:300])
        sys.exit(3)
    try:
        path = os.path.join(wt, rel)
        orig = io.open(path, encoding='utf-8', newline='').read()

        # UNIQUE PER ARM. Branch names are REPO-global, not worktree-local:
        # a shared `probe-base` made every arm after the first fail to create
        # its fixture, and those arms then reported on a tree with no conflict
        # in it. A fixture that silently does not exist is worse than one that
        # fails, because the arms still print.
        base, other = 'probe-base-' + tag, 'probe-other-' + tag
        git(wt, 'branch', '-D', base)
        git(wt, 'branch', '-D', other)
        git(wt, 'checkout', '-q', '-b', base)
        io.open(path, 'w', encoding='utf-8', newline='').write(mutate_a(orig))
        git(wt, 'add', rel)
        git(wt, '-c', 'user.email=p@p', '-c', 'user.name=probe',
            'commit', '-q', '-m', 'probe A')

        git(wt, 'checkout', '-q', '-b', other, 'HEAD~1')
        io.open(path, 'w', encoding='utf-8', newline='').write(mutate_b(orig))
        git(wt, 'add', rel)
        git(wt, '-c', 'user.email=p@p', '-c', 'user.name=probe',
            'commit', '-q', '-m', 'probe B')

        r = git(wt, '-c', 'user.email=p@p', '-c', 'user.name=probe',
                'rebase', base)
        conflicted = git(wt, 'diff', '--name-only', '--diff-filter=U').stdout.split()
        return body(wt, rel, conflicted, r)
    finally:
        subprocess.run(['git', '-C', wt, 'rebase', '--abort'],
                       capture_output=True)
        shutil.rmtree(wt, ignore_errors=True)
        subprocess.run(['git', '-C', REPO, 'worktree', 'prune'],
                       capture_output=True)
        # Branches outlive the worktree. Left behind, the NEXT RUN of this probe
        # collides exactly as the arms did.
        for b in ('probe-base-' + tag, 'probe-other-' + tag):
            subprocess.run(['git', '-C', REPO, 'branch', '-D', b],
                           capture_output=True)


print('sairn_rebase_resolve -- resolve one class, REFUSE the other\n')

# ── 1. A SOURCE FILE MUST BE REFUSED ───────────────────────────────────────
# api/_lib/dnt-rollup.js is the file the real incident happened to. Using it
# rather than a neutral one is deliberate: the arm names the thing it protects.
SRC = 'api/_lib/dnt-rollup.js'


def src_arm(wt, rel, conflicted, reb):
    check('a real rebase conflict was created on the SOURCE file',
          rel in conflicted, 'conflicted=%r rebase=%s' % (conflicted, reb.stderr[:200]))
    if rel not in conflicted:
        return
    rc, out = run_tool(wt)
    check('...and the tool REFUSES it, exit 1', rc == 1, 'exit %d\n%s' % (rc, out[-400:]))
    check('...and names the file', rel in out, out[-300:])
    check('...and classifies it SOURCE, not generated', 'SOURCE' in out, out[-300:])
    # NOT `git diff --cached`: during a conflicted rebase git holds UNMERGED
    # entries at stages 1/2/3 and that command lists the path regardless of
    # whether anything resolved it. The question is whether the path is still
    # UNMERGED, which is what "unresolved" actually means.
    still = git(wt, 'diff', '--name-only', '--diff-filter=U').stdout.split()
    check('...and leaves it UNRESOLVED -- a partial resolution is the same '
          'failure in a different hat', rel in still, still)


with_conflict('src', SRC,
              lambda s: s.replace('const SEP', 'const SEP_A', 1),
              lambda s: s.replace('const SEP', 'const SEP_B', 1),
              src_arm)

# ── 2. A GENERATED DOCUMENT MUST BE RESOLVED ───────────────────────────────
GEN = 'docs/TOOLING-INVENTORY.md'


def gen_arm(wt, rel, conflicted, reb):
    check('a real rebase conflict was created on the GENERATED document',
          rel in conflicted, 'conflicted=%r' % (conflicted,))
    if rel not in conflicted:
        return
    rc, out = run_tool(wt, '--dry')
    check('--dry reports it as GENERATED and changes nothing',
          rc == 0 and 'GENERATED' in out, 'exit %d\n%s' % (rc, out[-400:]))
    still = git(wt, 'diff', '--name-only', '--diff-filter=U').stdout.split()
    check('...and --dry really left it conflicted', rel in still, still)

    rc, out = run_tool(wt)
    check('the real run regenerates and stages it, exit 0', rc == 0,
          'exit %d\n%s' % (rc, out[-500:]))
    body = io.open(os.path.join(wt, rel), encoding='utf-8', errors='replace').read()
    check('...and NO conflict marker survives in the staged file',
          '\n<<<<<<<' not in body and '\n>>>>>>>' not in body,
          'markers still present')
    staged = git(wt, 'diff', '--name-only', '--cached').stdout.split()
    check('...and it really is staged', rel in staged, staged)


with_conflict('gen', GEN,
              lambda s: s + '\nprobe A\n',
              lambda s: s + '\nprobe B\n',
              gen_arm)

# ── 3. MIXED: ONE OF EACH MEANS REFUSE EVERYTHING ──────────────────────────
# The dangerous middle case. Resolving the generated half and leaving the source
# half is a state somebody finishes by hand under time pressure.
def mixed_arm(wt, rel, conflicted, reb):
    # add a second, GENERATED conflict on top of the source one
    gen_path = os.path.join(wt, GEN)
    io.open(gen_path, 'a', encoding='utf-8', newline='').write('\nprobe mixed\n')
    git(wt, 'add', GEN)
    rc, out = run_tool(wt)
    check('MIXED: one source + one generated -> REFUSES, exit 1', rc == 1,
          'exit %d\n%s' % (rc, out[-400:]))
    still = git(wt, 'diff', '--name-only', '--diff-filter=U').stdout.split()
    check('...and the SOURCE half is still unresolved, so nothing was done '
          'by halves', rel in still, still)


with_conflict('mixed', SRC,
              lambda s: s.replace('const SEP', 'const SEP_A', 1),
              lambda s: s.replace('const SEP', 'const SEP_B', 1),
              mixed_arm)

# ── 4. THE BACKSTOP DOES NOT TRUST THE CLASSIFICATION ──────────────────────
# A file that DECLARES itself generated but whose generator does not exist must
# be COULD NOT TELL (2), never source and never generated. Guessing either way
# is how this tool would re-create the incident it exists to prevent.
def liar_arm(wt, rel, conflicted, reb):
    if rel not in conflicted:
        check('fixture: the liar file is conflicted', False, conflicted)
        return
    path = os.path.join(wt, rel)
    body = io.open(path, encoding='utf-8', errors='replace').read()
    io.open(path, 'w', encoding='utf-8', newline='').write(
        '**GENERATED by `python tools/no_such_generator.py`. Do not hand-edit.**\n'
        + body)
    rc, out = run_tool(wt)
    check('a file naming a generator that does not exist is COULD NOT TELL (2)',
          rc == 2, 'exit %d\n%s' % (rc, out[-400:]))
    check('...and says nothing was staged', 'not a pass' in out or 'Nothing was staged' in out,
          out[-300:])


with_conflict('liar', SRC,
              lambda s: s.replace('const SEP', 'const SEP_A', 1),
              lambda s: s.replace('const SEP', 'const SEP_B', 1),
              liar_arm)

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
