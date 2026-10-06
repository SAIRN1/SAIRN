# OWNER: hank
"""run_worktree_root_home_repo_probe.py -- the three probes that derive a clone
root must not answer about the HOME repository, and this DRIVES that rather than
reading the code for a `rev-parse`.

    python tests/run_worktree_root_home_repo_probe.py
    python tests/run_worktree_root_home_repo_probe.py --selftest

── THE HAZARD, AND IT IS SPECIFIC TO THIS MACHINE ────────────────────────────
`C:\\Users\\marsh` IS ITSELF A GIT REPOSITORY. So a bare
`git rev-parse --show-toplevel` run from ANY directory beneath the home
directory does not fail -- it walks up, finds `~/.git`, and EXITS 0 with a
confident answer about the wrong repository. The failure is a fail-OPEN: the
tool keeps running, imports whatever it finds, and reports about a tree nobody
asked about.

The three subjects previously hardcoded one clone's absolute path, which was the
same defect in a louder costume: run from any other clone they imported THAT
clone's tools. `a249565f` named it; `c586d0e3` moved them to git.

── WHY THIS FILE EXISTS WHEN THE SOURCE ALREADY SAYS `rev-parse` ─────────────
Reading the source proves the CALL is there. It cannot prove the call is
ANCHORED, or that the ANSWER is checked, and both are what make the difference
here -- an unanchored `rev-parse` is strictly worse than the hardcoded path it
replaced, because it is confidently wrong instead of obviously wrong. So each
subject's own `_repo_root()` is extracted and EXECUTED with `__file__` pointed at
a copy sitting under the home repository, which is the exact situation that
produces the wrong answer.

── THE FOUR ARMS PER SUBJECT, AND ARM D IS WHY B MEANS ANYTHING ──────────────
    A  the function was EXTRACTED at all -- without this, a renamed `_repo_root`
       would make every arm below run on an empty namespace and "pass"
    B  run from under HOME: the answer is NOT the home repo, and the fallback is
       ANNOUNCED on stderr rather than taken silently
    C  run from its real place in this clone: the answer is EXACTLY this clone
       -- without this, a function that returned `None` always would satisfy B
    D  a NAIVE `git rev-parse --show-toplevel` from that same copy directory
       DOES answer the home repo -- so B is the anchoring working, and not git
       merely being unavailable or the home repo having quietly stopped being one

── WHAT THIS DOES NOT COVER ─────────────────────────────────────────────────
It does not run the probes themselves: two of the three make live network
requests against an audit licence, and driving those is a different job with
different residue. It covers the ROOT DERIVATION only. And it is a probe about
THIS machine's layout: on a machine whose home directory is not a repository the
hazard does not exist and arm D says so by failing to reproduce it, which is
reported as COULD NOT RUN rather than as a pass.

EXIT: 0 all arms hold, 1 at least one subject can answer about the wrong repo,
2 COULD NOT RUN.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRITERIA_VERSION = '2026-10-06.1'
SUBJECTS = ('probe_public_book_guardian.py',
            'rf_claim_gate_live_probe.py',
            'rf_roundtrip_probe.py')


def extract_repo_root(src):
    """The `def _repo_root():` block, by indentation, or None.

    EXTRACTED CODE, NOT A WINDOW OF THE FILE -- scrubber item 16 shape A. And
    the caller MUST treat None as a refusal: a renamed function that silently
    extracted nothing would leave every arm below asserting over an empty
    namespace, which is the vacuous-green shape this file is otherwise about.
    """
    m = re.search(r'^def _repo_root\(\):\s*$', src, re.M)
    if not m:
        return None
    lines = src[m.start():].split('\n')
    out = [lines[0]]
    for line in lines[1:]:
        if line.strip() and not line.startswith((' ', '\t')):
            break
        out.append(line)
    return '\n'.join(out)


REFUSED = object()


def call_repo_root(block, as_file):
    """Run the extracted function with `__file__` set to `as_file`.

    Returns `(answer, stderr_text)`, where `answer` is `REFUSED` when the
    function raised `SystemExit` instead of returning. BOTH HALVES MATTER AND
    THEY ARE DIFFERENT CLAIMS: stderr is captured because an announcement is
    half the requirement, and the refusal is captured because the other half is
    that nothing usable comes back. A warning printed beside a returned path is
    still a wrong answer to every caller that does not read stderr -- which was
    the real state of all three subjects before 2026-10-06.
    """
    ns = {'os': os, 'sys': sys, '__file__': as_file}

    class Cap(object):
        def __init__(self):
            self.buf = []

        def write(self, s):
            self.buf.append(s)

        def flush(self):
            pass

    cap = Cap()
    real = sys.stderr
    sys.stderr = cap
    try:
        exec(block, ns)                                          # noqa: S102
        try:
            ans = ns['_repo_root']()
        except SystemExit:
            ans = REFUSED
    finally:
        sys.stderr = real
    return ans, ''.join(cap.buf)


def norm(p):
    return os.path.normcase(os.path.abspath(str(p))).replace('\\', '/').rstrip('/')


def main(argv):
    print('WORKTREE ROOT vs THE HOME REPOSITORY -- criteria %s'
          % CRITERIA_VERSION)

    home = os.path.expanduser('~')
    p = subprocess.run(['git', '-C', home, 'rev-parse', '--show-toplevel'],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        print('COULD NOT RUN: %s is not a git repository on this machine, so '
              'the hazard these three probes guard against cannot be '
              'reproduced here. This is NOT "the probes are safe" -- nothing '
              'was driven.' % home)
        return 2
    home_root = p.stdout.decode('utf-8', 'replace').strip()
    print('  home repo : %s' % home_root)
    print('  this clone: %s' % REPO)
    if norm(home_root) == norm(REPO):
        print('COULD NOT RUN: the home repository and this clone are the same '
              'tree, so a right answer and a wrong one are indistinguishable.')
        return 2
    print('')

    npass = nfail = 0

    def ck(label, cond, extra=''):
        nonlocal npass, nfail
        if cond:
            npass += 1
            print('  ok   ' + label)
        else:
            nfail += 1
            print('  FAIL ' + label)
            if extra:
                print('       ' + str(extra)[:400])

    # A scratch directory DIRECTLY UNDER HOME -- inside the home repository's
    # worktree and inside no clone. That is the situation, not a simulation of it.
    sandbox = tempfile.mkdtemp(prefix='worktree-root-probe-', dir=home)
    try:
        for name in SUBJECTS:
            print('%s' % name)
            real_path = os.path.join(REPO, 'tools', name)
            if not os.path.isfile(real_path):
                ck('A. %s -- the subject exists' % name, False,
                   'not found at ' + real_path)
                continue
            src = io.open(real_path, encoding='utf-8').read()
            block = extract_repo_root(src)
            ck('A. `def _repo_root():` was EXTRACTED from the real file. '
               'Without this arm a rename would leave every arm below '
               'asserting over an empty namespace', block is not None)
            if block is None:
                continue

            copy = os.path.join(sandbox, name)
            shutil.copyfile(real_path, copy)

            # ── D FIRST, because it is what makes B mean anything.
            q = subprocess.run(['git', '-C', sandbox, 'rev-parse',
                                '--show-toplevel'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            naive = q.stdout.decode('utf-8', 'replace').strip()
            ck('D. a NAIVE `git rev-parse --show-toplevel` from %s DOES answer '
               'the home repo (%s). The hazard is REAL here and arm B is the '
               'anchoring working, not git being unavailable'
               % (os.path.basename(sandbox), home_root),
               q.returncode == 0 and norm(naive) == norm(home_root),
               'exit=%d answer=%r' % (q.returncode, naive))

            ans, err = call_repo_root(block, copy)
            ck('B. run from under HOME, _repo_root() does NOT answer the home '
               'repo. Answering it would be a FAIL-OPEN: exit 0, a confident '
               'path, and every later import about the wrong tree',
               ans is REFUSED or norm(ans) != norm(home_root),
               'answered %r' % (ans,))
            ck('B1. ...and it is ANNOUNCED on stderr. A silent fallback is the '
               'same defect one level down -- the caller cannot tell a derived '
               'root from a guessed one',
               bool(err.strip()), 'stderr was empty')
            # ── B2 IS THE ARM THAT FOUND THE REAL DEFECT, 2026-10-06.
            # Before the fix, B1 PASSED and B FAILED: the warning was printed
            # and `C:\\Users\\marsh` was returned anyway, because the fallback
            # `os.path.dirname(here)` of a copy sitting directly under HOME IS
            # the home repository. A warning plus a usable string is not a
            # refusal -- the one process that could tell has already decided to
            # carry on, and nothing downstream reads stderr.
            ck('B2. ...and it REFUSES rather than returning ANY path. '
               '"Could not tell" is a third state and is never folded into an '
               'answer (PR 1.11). This is the arm that caught the real defect: '
               'the unchecked __file__ fallback landed on the home repo, which '
               'is the exact wrong answer the anchoring exists to avoid',
               ans is REFUSED, 'returned %r instead of refusing' % (ans,))

            ans2, err2 = call_repo_root(block, real_path)
            ck('C. run from its REAL place in this clone, _repo_root() answers '
               'EXACTLY this clone. Without this arm a function that always '
               'returned None would satisfy B',
               norm(ans2) == norm(REPO), 'answered %r, wanted %r' % (ans2, REPO))
            ck('C1. ...and says NOTHING on stderr, so the warning in B1 is a '
               'real signal rather than noise printed on every run',
               not err2.strip(), 'stderr was %r' % err2[:200])
            print('')
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    left = os.path.isdir(sandbox)
    ck('Z. the scratch directory under HOME is REMOVED. A probe that leaves '
       'residue in somebody\'s home repository is a worse problem than the one '
       'it checks', not left, sandbox)

    print('%d passed, %d failed' % (npass, nfail))
    return 1 if nfail else 0


if __name__ == '__main__':
    argv = [a for a in sys.argv[1:] if a != '--selftest']
    sys.exit(main(argv))
