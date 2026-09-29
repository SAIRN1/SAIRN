r"""tests/run_nhi_clone_enumeration_probe.py -- the working copies sharing the
push credential are found by what they ARE, not by what they are NAMED.

    python tests/run_nhi_clone_enumeration_probe.py

WHY THIS EXISTS, AND IT IS THE THIRD INSTANCE OF ONE UNDERCOUNT.

`clone-push-access` in docs/NHI-REGISTER.md is the row that says which working
copies can push to origin/main. Every clone in that row holds the same
credential, so the row IS the rotation blast radius.

  1. 2026-09-16 -- CLAUDE.md said "Four clones" and named four while a fifth
     existed and was pushing. Corrected when landing_verification.py found it.
  2. 2026-09-17 -- this register's own row said "FOUR working copies" and named
     four, for the same reason. The fix was to stop typing the list and COUNT
     FROM DISK, and the tool's header says so at length.
  3. TODAY -- the derivation counts `SAIRN-*` siblings. There is a seventh
     working copy at `Documents\SAIRN`, a clone of the same remote, on main,
     which the name filter skips. The count was derived and still wrong, because
     the PREDICATE was a naming convention rather than the thing being asked.

That is the shape worth keeping: deriving a population does not make it right if
the filter encodes a habit. The real question is "is this directory a git clone
of the same origin", and nothing about a hyphen answers it.

**THE FIXTURES ARE REAL REPOSITORIES.** `git init` and a real
`remote.origin.url` on each, in a throwaway parent directory, because the whole
defect is about what the enumeration does with directories on disk and a mocked
listdir would have agreed with whatever the code already did.
"""
import os
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

TOOL = os.path.join(REPO, 'tools', 'nhi_register.py')
if not os.path.isfile(TOOL):
    print('COULD NOT RUN: tools/nhi_register.py is not on disk. This control '
          'tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

import nhi_register as nhi   # noqa: E402

if not hasattr(nhi, 'sibling_clones'):
    print('COULD NOT RUN: nhi_register.sibling_clones is gone. The control '
          'tested nothing.')
    sys.exit(EXIT_COULD_NOT_RUN)

passed = failed = 0


def ok(cond, label, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        failed += 1
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:400])


def rmtree(path):
    def onerror(fn, p, exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            fn(p)
        except Exception:
            pass
    shutil.rmtree(path, onerror=onerror)


def make_clone(parent, name, origin):
    """A real git repository with a real origin, or no repository at all."""
    path = os.path.join(parent, name)
    os.makedirs(path)
    if origin is None:
        return path
    subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=path,
                   capture_output=True, text=True)
    subprocess.run(['git', 'remote', 'add', 'origin', origin], cwd=path,
                   capture_output=True, text=True)
    return path


print('CONTROL PAIR -- nhi_register.sibling_clones()\n')

SAME = 'https://github.com/SAIRN1/SAIRN.git'
OTHER = 'https://github.com/SAIRN1/SOMETHING-ELSE.git'

parent = tempfile.mkdtemp(prefix='sairn_nhi_probe_')
try:
    me = make_clone(parent, 'SAIRN-me', SAME)

    # THE ARM THAT MATTERS. A clone of the same remote whose directory name
    # carries no hyphen -- which is the real `Documents\SAIRN`, the seventh
    # working copy, holding the same push credential.
    make_clone(parent, 'SAIRN', SAME)

    # Same remote, a name nobody would have guessed at all.
    make_clone(parent, 'checkout-of-sairn', SAME)

    # A DIFFERENT remote, correctly named. Must NOT be counted: it does not
    # hold this credential and inflating the blast radius is its own error.
    make_clone(parent, 'SAIRN-unrelated', OTHER)

    # Named like a clone, is not one.
    make_clone(parent, 'SAIRN-notes', None)

    found = nhi.sibling_clones(repo=me)

    ok('SAIRN-me' in found,
       'it finds ITSELF -- the enumeration that cannot see its own clone is '
       'broken rather than answering zero')
    ok('SAIRN' in found,
       'THE ARM THAT MATTERS: a clone of the same remote NOT named SAIRN-* is '
       'counted. This is the real Documents\\SAIRN, the seventh working copy '
       'holding the same push credential, and the name filter skipped it -- the '
       'third instance of this undercount', found)
    ok('checkout-of-sairn' in found,
       'and so is one whose name matches no convention at all -- the predicate '
       'is "clone of the same origin", not a spelling', found)
    ok('SAIRN-unrelated' not in found,
       'a clone of a DIFFERENT remote is NOT counted -- it does not hold this '
       'credential, and over-counting a rotation blast radius is its own error',
       found)
    ok('SAIRN-notes' not in found,
       'and a directory named like a clone but holding no repository is not '
       'counted', found)
    ok(len(found) == 3,
       'exactly the 3 real same-origin clones, no more (got %d: %s)'
       % (len(found), found))
finally:
    rmtree(parent)

# ── FAIL CLOSED, which the tool's own header promises ───────────────────────
print('\nDIRECTION -- it must RAISE rather than fall back to a list')
lonely = tempfile.mkdtemp(prefix='sairn_nhi_lonely_')
try:
    me = make_clone(lonely, 'only-me', SAME)
    # Break the origin so the tool cannot learn what "the same remote" means.
    subprocess.run(['git', 'remote', 'remove', 'origin'], cwd=me,
                   capture_output=True, text=True)
    try:
        nhi.sibling_clones(repo=me)
        ok(False, 'a clone with no origin must raise CouldNotTell')
    except nhi.CouldNotTell as exc:
        ok('origin' in str(exc),
           'a clone with no remote.origin.url raises CouldNotTell naming the '
           'reason, rather than reverting to a hardcoded list -- a register that '
           'quietly reverts reports the exact defect it was changed to fix')
    except Exception as exc:
        ok(False, 'raised the wrong exception: %r' % exc)
finally:
    rmtree(lonely)

# ── AND THE REAL CLONE, reported not asserted ──────────────────────────────
print('\nTHE REAL MACHINE -- reported, not asserted')
try:
    real = nhi.sibling_clones()
    print('  --   %d working copies of this remote on disk right now: %s'
          % (len(real), ', '.join(real)))
    ok(os.path.basename(REPO) in real,
       'this clone counts itself among them (%s)' % os.path.basename(REPO), real)
except Exception as exc:
    ok(False, 'the real enumeration raised: %r' % exc)

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
