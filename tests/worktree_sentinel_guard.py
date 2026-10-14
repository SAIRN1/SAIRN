#!/usr/bin/env python
"""worktree_sentinel_guard.py -- a suite's colour is not a fact if its sentinel
cannot resolve.

WHY THIS EXISTS, AND IT IS A CORRECTION TO MY OWN WORK. In cody b9 two suites
were driven in an isolated git worktree, crashed, and were reported RED. They
are GREEN. The cause was structural and had nothing to do with the code under
test:

    tests/seam_check/run_delegation_probe.py builds its sentinel as
        os.path.join(REPO, '.git', 'seam-delegation-probe.planting')
    and IN A GIT WORKTREE `.git` IS A 64-BYTE FILE, NOT A DIRECTORY,
    so the sentinel can never be created and the suite dies with
    FileNotFoundError before it asserts anything.

Reporting that exit code as red declared working code broken, and it would have
retired a working ablation -- that control's load-bearing arms are "the plant
really did modify the file" and "the same exception WITHOUT the guard leaves the
plant". A false red on those two is worse than no run at all.

THE RULE THIS MAKES MECHANICAL:

    A suite must not be classified RED or GREEN from a worktree unless every
    sentinel path it builds RESOLVES. If one does not, the only honest answer
    is COULD NOT RUN -- exit 2 -- which is neither colour.

IT IS DERIVED, NOT A HAND LIST. The sentinels are read out of the suite's own
source every run. A hand-maintained list of "suites that need a real clone" is
the thing that goes stale the day somebody adds the third one, and nothing
would say so.

FAIL CLOSED. A suite whose source cannot be read is exit 2 and says which file
and why -- never exit 0. A check that depends on reading a file and silently
passes when it cannot is the defect shape CLAUDE.md puts above all others.

WHAT IT DOES NOT CLAIM:
  * It does not run the suite and it does not judge its colour. It answers one
    question -- MAY a colour be believed from here -- and nothing else.
  * It does not detect every environment-sensitive precondition. It detects the
    `.git`-is-a-file family, which is the one that cost two false verdicts. A
    suite that needs a provisioned session marker, or real sibling clones, is
    NOT caught here; those are named in the b10 handoff as the same class with
    a different mechanism.
  * `--selftest` exercises synthetic trees only. The real-tree answer is
    REPORTED by `--report`, never asserted, because asserting a clean tree
    turns every future real finding into a failure of this guard.

Exit codes:
  0  every named suite is classifiable from this checkout
  2  COULD NOT RUN -- at least one sentinel does not resolve here, or a source
     file could not be read. NOT a judgement about any suite's colour.
  3  usage error
"""

import os
import re
import sys

CRITERIA_VERSION = '2026-10-14.1'

EXIT_OK = 0
EXIT_COULD_NOT_RUN = 2
EXIT_USAGE = 3


def repo_root(start=None):
    """The checkout that contains `start`, found by walking up to a `.git`.

    Returns None rather than guessing: a caller that cannot find a checkout
    must not be told the current directory is one.
    """
    here = os.path.abspath(start or os.path.dirname(os.path.abspath(__file__)))
    while True:
        if os.path.exists(os.path.join(here, '.git')):
            return here
        nxt = os.path.dirname(here)
        if nxt == here:
            return None
        here = nxt


def checkout_kind(repo):
    """'clone' | 'worktree' | 'none'.

    THE WHOLE GUARD TURNS ON THIS ONE FACT: `git worktree add` writes `.git` as
    a FILE containing `gitdir: <path>`, where a normal clone has a DIRECTORY.
    Measured rather than inferred from a git version or a command's output --
    the filesystem is the thing the suites actually trip over.
    """
    dot = os.path.join(repo, '.git')
    if os.path.isdir(dot):
        return 'clone'
    if os.path.isfile(dot):
        return 'worktree'
    return 'none'


# A sentinel built under the checkout's own `.git`. Three spellings, because all
# three appear in this repo and matching only the first would have caught only
# the suite that was already known:
#   os.path.join(REPO, '.git', 'x')      -- the two seam_check suites
#   os.path.join(REPO, '.git/x')
#   REPO + '/.git/x'   /   f'{REPO}/.git/x'
_JOIN_RE = re.compile(
    r"""os\.path\.join\(\s*[A-Za-z_][A-Za-z_0-9]*\s*,\s*       # join(ROOTVAR,
        (?:['"]\.git['"]\s*,\s*['"](?P<two>[^'"]+)['"]          #   '.git', 'x'
        |['"]\.git/(?P<one>[^'"]+)['"])""",
    re.X)
_SLASH_RE = re.compile(r"""['"]/?\.git/(?P<name>[A-Za-z0-9_.\-]+)['"]""")


_COMMENT_RE = re.compile(r'^[ \t]*#.*$', re.M)
_DOCSTRING_RE = re.compile(r'"""(?:.|\n)*?"""|\'\'\'(?:.|\n)*?\'\'\'')


def strip_prose(src):
    """Comments and triple-quoted blocks removed before any match.

    EVERY FILE THAT DISCUSSES THIS DEFECT NAMES `.git` IN PROSE -- including
    this one, and including the two suites it was written for, whose own
    comments explain the sentinel. Matching the word rather than the construct
    would make the guard fire on the documentation of the thing it checks,
    which is the false-positive shape named in advance. Arm 5d pins it.
    """
    return _DOCSTRING_RE.sub('', _COMMENT_RE.sub('', src))


def sentinels_in(src):
    """Every `.git/<name>` sentinel the source builds, de-duplicated, in order.

    Returns a list of names relative to `.git`. A directory component is kept
    as written -- `.git/worktrees/x` is a different question from `.git/x` and
    conflating them would make the guard answer about the wrong path.
    """
    src = strip_prose(src)
    names = []
    for m in _JOIN_RE.finditer(src):
        names.append(m.group('two') or m.group('one'))
    for m in _SLASH_RE.finditer(src):
        names.append(m.group('name'))
    out = []
    for n in names:
        if n not in out:
            out.append(n)
    return out


def resolves(repo, name):
    """Can `<repo>/.git/<name>` be created or read from here?

    The question is about the PARENT: a sentinel that does not exist yet is
    fine, a sentinel whose parent is not a directory is not. That is exactly
    the worktree case -- the parent is `.git`, and it is a file.
    """
    target = os.path.join(repo, '.git', name)
    return os.path.isdir(os.path.dirname(target))


# A sibling test module pulled in by name, e.g.
#   import run_delegation_probe as mod      /    from run_delegation_probe import plant
# A SUITE INHERITS ITS IMPORT'S CONSTRAINT, and this is not hypothetical: the
# suite that forced this guard into existence --
# tests/seam_check/run_delegation_residue_control.py -- builds NO sentinel of
# its own. It calls the probe's `plant`, dies at the probe's line, and would
# have been CLASSIFIABLE and therefore falsely red without this. A guard that
# misses the exact file that motivated it is a guard that did not learn.
_IMPORT_RE = re.compile(
    r'^\s*(?:from\s+(?P<from>[A-Za-z_][A-Za-z_0-9]*)\s+import\b'
    r'|import\s+(?P<plain>[A-Za-z_][A-Za-z_0-9]*))', re.M)


# THE REPO'S OWN CONVENTION, AND IT IS THE MOST RELIABLE OF THE THREE.
# A control declares its subject by path:  CONTROLS_FOR = ['tests/x/y.py']
_CONTROLS_FOR_RE = re.compile(
    r'CONTROLS_FOR\s*=\s*\[(?P<body>[^\]]*)\]', re.S)
# A module loaded BY PATH rather than by name, which is how this repo's
# controls actually reach their subject:
#   PROBE = os.path.join(REPO, 'tests', 'seam_check', 'run_delegation_probe.py')
#   spec  = importlib.util.spec_from_file_location('x', PROBE)
_PATH_JOIN_RE = re.compile(
    r"os\.path\.join\(\s*[A-Za-z_][A-Za-z_0-9]*\s*,\s*"
    r"(?P<parts>(?:['\"][^'\"]+['\"]\s*,\s*)*['\"][^'\"]+\.py['\"])\s*\)")
_QUOTED_RE = re.compile(r"['\"]([^'\"]+)['\"]")


def imported_siblings(repo, suite_path, src):
    """Other .py modules this suite pulls in, as absolute paths.

    THREE ROUTES, because one would have missed the file that motivated the
    guard. tests/seam_check/run_delegation_residue_control.py does NOT
    `import run_delegation_probe` -- it builds a path and uses
    importlib.util.spec_from_file_location. A guard that only understood
    `import <name>` would have reported it CLASSIFIABLE and therefore red,
    which is the original defect wearing a new hat.

      (a) CONTROLS_FOR = ['tests/.../x.py']   -- this repo's own convention
      (b) os.path.join(ROOTVAR, 'tests', ..., 'x.py')  -- a path-loaded module
      (c) import <sibling> / from <sibling> import ...

    ONE LEVEL ONLY, and that bound is deliberate rather than lazy: a full
    transitive walk needs cycle handling and would answer about modules the
    suite never touches, and the measured shape here is a control reaching the
    probe it controls. A deeper chain is NOT covered and --report does not
    claim it is.
    """
    code = strip_prose(src)
    here = os.path.dirname(os.path.abspath(suite_path))
    me = os.path.abspath(suite_path)
    out = []

    def add(cand):
        if os.path.isfile(cand) and os.path.abspath(cand) != me and cand not in out:
            out.append(cand)

    # (a) the declared subject
    for m in _CONTROLS_FOR_RE.finditer(code):
        for rel in _QUOTED_RE.findall(m.group('body')):
            if rel.endswith('.py'):
                add(os.path.join(repo, rel.replace('/', os.sep)))

    # (b) a module loaded by a built path
    for m in _PATH_JOIN_RE.finditer(code):
        parts = _QUOTED_RE.findall(m.group('parts'))
        if parts and parts[-1].endswith('.py'):
            add(os.path.join(repo, *parts))

    # (c) an ordinary sibling import
    for m in _IMPORT_RE.finditer(code):
        name = m.group('from') or m.group('plain')
        add(os.path.join(here, name + '.py'))

    return out


def classify(repo, suite_path):
    """(verdict, detail) for one suite.

    verdict is 'CLASSIFIABLE' or 'COULD-NOT-RUN'. NEVER a colour -- this
    function does not run anything.
    """
    try:
        with open(suite_path, 'r', encoding='utf-8', errors='replace') as fh:
            src = fh.read()
    except OSError as exc:
        # FAIL CLOSED. Unreadable is not "has no sentinel".
        return ('COULD-NOT-RUN',
                'its source could not be read, so its sentinels were never '
                'looked for: %s' % exc)

    found = sentinels_in(src)
    inherited = []
    for sib in imported_siblings(repo, suite_path, src):
        try:
            with open(sib, 'r', encoding='utf-8', errors='replace') as fh:
                sibsrc = fh.read()
        except OSError as exc:
            # FAIL CLOSED again: an import that cannot be read is not an
            # import with no sentinels.
            return ('COULD-NOT-RUN',
                    'it imports %s, whose source could not be read, so that '
                    'module\'s sentinels were never looked for: %s'
                    % (os.path.basename(sib), exc))
        for n in sentinels_in(sibsrc):
            if n not in found:
                found.append(n)
                inherited.append(os.path.basename(sib) + ':' + n)
    if not found:
        return ('CLASSIFIABLE', 'builds no .git sentinel')

    kind = checkout_kind(repo)
    bad = [n for n in found if not resolves(repo, n)]
    via = (' (inherited: %s)' % ', '.join(inherited)) if inherited else ''
    if not bad:
        return ('CLASSIFIABLE',
                'sentinel(s) resolve here (%s checkout): %s%s'
                % (kind, ', '.join(found), via))

    return ('COULD-NOT-RUN',
            'this is a %s and .git is a %s here, so %s cannot be created%s. Its '
            'exit code is NOT a colour -- re-drive it in the live clone'
            % (kind,
               'file' if kind == 'worktree' else 'missing',
               ', '.join('.git/' + n for n in bad),
               via))


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    flags = set(a for a in argv if a.startswith('--'))

    if '--selftest' in flags:
        return selftest()

    repo = repo_root()
    if repo is None:
        sys.stdout.write('COULD NOT RUN: no checkout found above %s. This is '
                         'not "no sentinels".\n'
                         % os.path.dirname(os.path.abspath(__file__)))
        return EXIT_COULD_NOT_RUN

    if '--report' in flags and not args:
        return report(repo)

    if not args:
        sys.stdout.write(__doc__.split('Exit codes:')[0])
        sys.stdout.write('usage: python tests/worktree_sentinel_guard.py '
                         '<suite.py> [...]\n'
                         '       python tests/worktree_sentinel_guard.py '
                         '--report\n'
                         '       python tests/worktree_sentinel_guard.py '
                         '--selftest\n')
        return EXIT_USAGE

    print('WORKTREE SENTINEL GUARD -- criteria %s' % CRITERIA_VERSION)
    print('  checkout : %s  (%s)' % (repo, checkout_kind(repo)))
    print('')
    blocked = []
    for rel in args:
        path = rel if os.path.isabs(rel) else os.path.join(repo, rel)
        verdict, detail = classify(repo, path)
        mark = '  ok   ' if verdict == 'CLASSIFIABLE' else '  ???  '
        print('%s%-52s %s' % (mark, rel, detail))
        if verdict != 'CLASSIFIABLE':
            blocked.append(rel)

    print('')
    if blocked:
        print('  COULD NOT RUN (%d of %d): %s'
              % (len(blocked), len(args), ', '.join(blocked)))
        print('  Their exit codes must NOT be recorded as red OR green from '
              'this checkout.')
        return EXIT_COULD_NOT_RUN
    print('  %d of %d classifiable from here.' % (len(args), len(args)))
    return EXIT_OK


def report(repo):
    """The real tree, REPORTED and not asserted.

    An assertion that no suite in this repo has an unresolvable sentinel would
    turn every future real one into a failure of this guard -- the same reason
    tools/unproven_arm_check.py reports its real-tree count rather than
    asserting it.
    """
    print('WORKTREE SENTINEL GUARD -- REPORT, criteria %s' % CRITERIA_VERSION)
    print('  checkout : %s  (%s)' % (repo, checkout_kind(repo)))
    tests_dir = os.path.join(repo, 'tests')
    scanned = with_sent = blocked = 0
    names = []
    for root, dirs, files in os.walk(tests_dir):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in sorted(files):
            if not f.endswith('.py'):
                continue
            scanned += 1
            p = os.path.join(root, f)
            rel = os.path.relpath(p, repo).replace('\\', '/')
            verdict, detail = classify(repo, p)
            if 'builds no .git sentinel' not in detail:
                with_sent += 1
                names.append((rel, verdict, detail))
            if verdict != 'CLASSIFIABLE':
                blocked += 1
    print('  python suites scanned                 %d' % scanned)
    print('  building a .git sentinel              %d' % with_sent)
    print('  NOT CLASSIFIABLE from this checkout   %d' % blocked)
    for rel, verdict, detail in names:
        print('    %-7s %-48s %s' % (verdict, rel, detail[:90]))
    print('')
    print('  REPORTED, NOT ASSERTED. In a real clone the expected answer is 0 '
          'blocked; in a')
    print('  worktree a non-zero count is the guard working, not a finding '
          'about the repo.')
    return EXIT_OK


# ── THE CONTROL PAIR. Both directions, on synthetic trees, because a guard
#    tested one way is a guard nobody has shown to discriminate. ───────────
def selftest():
    import tempfile
    import shutil

    passed = []
    failed = []

    def arm(name, got, want):
        if got == want:
            passed.append(name)
            print('  ok   %-72s' % name)
        else:
            failed.append(name)
            print('  FAIL %-72s got %r want %r' % (name, got, want))

    tmp = tempfile.mkdtemp(prefix='wsg_')
    try:
        SUITE = ("import os\n"
                 "REPO = os.path.dirname(__file__)\n"
                 "SENTINEL = os.path.join(REPO, '.git', 'probe.planting')\n")
        NOSENT = ("import os\n"
                  "P = os.path.join(os.sep, 'tmp', 'nothing')\n")

        # (1) A REAL CLONE: `.git` is a directory, so the sentinel resolves.
        clone = os.path.join(tmp, 'clone')
        os.makedirs(os.path.join(clone, '.git'))
        s1 = os.path.join(clone, 'suite.py')
        with open(s1, 'w', encoding='utf-8') as fh:
            fh.write(SUITE)
        arm('1a. a real clone (.git is a DIRECTORY) -> CLASSIFIABLE',
            classify(clone, s1)[0], 'CLASSIFIABLE')
        arm('1b. ...and the checkout is identified as a clone',
            checkout_kind(clone), 'clone')

        # (2) A WORKTREE: `.git` is a FILE. THE ARM THIS GUARD EXISTS FOR.
        wt = os.path.join(tmp, 'wt')
        os.makedirs(wt)
        with open(os.path.join(wt, '.git'), 'w', encoding='utf-8') as fh:
            fh.write('gitdir: ' + os.path.join(clone, '.git', 'worktrees', 'wt'))
        s2 = os.path.join(wt, 'suite.py')
        with open(s2, 'w', encoding='utf-8') as fh:
            fh.write(SUITE)
        arm('2a. THE ARM THAT MATTERS: a worktree (.git is a FILE) -> '
            'COULD-NOT-RUN', classify(wt, s2)[0], 'COULD-NOT-RUN')
        arm('2b. ...and it is identified as a worktree',
            checkout_kind(wt), 'worktree')
        arm('2c. ...and the reason names the sentinel it cannot create',
            '.git/probe.planting' in classify(wt, s2)[1], True)

        # (3) CONTROL -- the guard must NOT refuse everything in a worktree.
        #     Without this arm, "always COULD-NOT-RUN in a worktree" would
        #     satisfy arm 2 and make the guard useless.
        s3 = os.path.join(wt, 'nosent.py')
        with open(s3, 'w', encoding='utf-8') as fh:
            fh.write(NOSENT)
        arm('3. CONTROL: a suite with NO .git sentinel is CLASSIFIABLE even in '
            'a worktree', classify(wt, s3)[0], 'CLASSIFIABLE')

        # (4) FAIL CLOSED -- unreadable is not "has no sentinel".
        arm('4. an unreadable source is COULD-NOT-RUN, never CLASSIFIABLE',
            classify(wt, os.path.join(wt, 'does_not_exist.py'))[0],
            'COULD-NOT-RUN')

        # (5) THE THREE SPELLINGS. Matching only os.path.join(REPO,'.git','x')
        #     would have caught exactly the one suite already known.
        arm('5a. join(ROOT, ".git", "x") is seen',
            sentinels_in("os.path.join(ROOT, '.git', 'a.lock')"), ['a.lock'])
        arm('5b. join(ROOT, ".git/x") is seen',
            sentinels_in('os.path.join(ROOT, ".git/b.lock")'), ['b.lock'])
        arm('5c. a bare "/.git/x" literal is seen',
            sentinels_in('P = REPO + "/.git/c.lock"'), ['c.lock'])
        arm('5d. CONTROL: prose mentioning .git trips nothing',
            sentinels_in('# in a worktree .git is a file, not a directory\n'),
            [])

        # (7) THE INHERITED SENTINEL. A control that imports the probe it
        #     controls inherits the probe's constraint, and this is the exact
        #     file that motivated the guard: run_delegation_residue_control.py
        #     builds NO sentinel of its own.
        ctrl = os.path.join(wt, 'control.py')
        with open(ctrl, 'w', encoding='utf-8') as fh:
            fh.write('import suite\nsuite.plant()\n')
        arm('7a. THE ONE THAT MOTIVATED THE GUARD: a control that imports a '
            'sentinel-building probe INHERITS its constraint',
            classify(wt, ctrl)[0], 'COULD-NOT-RUN')
        arm('7b. ...and the reason says which import it came from',
            'suite.py:probe.planting' in classify(wt, ctrl)[1], True)
        # The clone already holds suite.py from arm 1, so the inheriting
        # control can import it there unchanged.
        ctrl_ok = os.path.join(clone, 'control.py')
        with open(ctrl_ok, 'w', encoding='utf-8') as fh:
            fh.write('import suite\nsuite.plant()\n')
        arm('7c. CONTROL: the same inheriting control is CLASSIFIABLE from a '
            'real clone -- the inheritance is not a blanket refusal',
            classify(clone, ctrl_ok)[0], 'CLASSIFIABLE')
        nosib = os.path.join(wt, 'nosib.py')
        with open(nosib, 'w', encoding='utf-8') as fh:
            fh.write('import os\nimport json\nimport sys\n')
        arm('7d. CONTROL: importing stdlib modules inherits nothing',
            classify(wt, nosib)[0], 'CLASSIFIABLE')

        # (6) THE GUARD AGAINST ITSELF, and the first draft of this arm was
        #     WRONG in a way worth keeping. It asserted this file builds NO
        #     sentinel, and it failed: the arms above hold fixture SOURCE in
        #     string literals, so `.git/probe.planting` and friends are really
        #     in this file. Stripping prose fixed the comment and docstring
        #     hits; the fixture literals are genuine text and no amount of
        #     stripping removes them.
        #
        #     So the arm now asserts the property that actually matters -- the
        #     guard must not block ITSELF from a real clone, which is the only
        #     environment where its own verdict is consumed. That is true, it
        #     is falsifiable, and it does not require pretending the fixtures
        #     are not there.
        me = os.path.abspath(__file__)
        shutil.copyfile(me, os.path.join(clone, 'guard_copy.py'))
        arm('6a. the guard does not block ITSELF from a real clone -- the only '
            'checkout where its verdict is consumed',
            classify(clone, os.path.join(clone, 'guard_copy.py'))[0],
            'CLASSIFIABLE')
        arm('6b. ...and its own fixture literals ARE seen, which is why 6a is '
            'about resolution and not about absence',
            len(sentinels_in(open(me, encoding='utf-8').read())) > 0, True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('')
    print('  %d passed, %d failed' % (len(passed), len(failed)))
    if failed:
        print('  FAILED: %s' % ', '.join(failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
