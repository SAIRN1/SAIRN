"""Does tools/purge_evidence_gate.py actually stop a prune that destroyed its own forensics?

WRITTEN BEFORE THE TOOL. Every arm below was run against a missing
tools/purge_evidence_gate.py first and every one of them failed, which is the
only way to know the arms are load-bearing rather than vacuous.

THE DEFECT THIS EXISTS FOR IS A REAL ONE, ON THIS CLONE. 2026-09-28 a session
purged a credential from SAIRN-fourth and reported ZERO unreachable objects.
2026-09-29 the same search found ONE. The evidence that would have said which
reading was wrong -- the object's mtime and the reflog entry keeping it alive --
had been destroyed by the `reflog expire --expire-unreachable=now` and
`gc --prune=now` that fixed the problem. The fix and the forensics are the same
command and the fix has to win, so the ONLY remaining defence is recording the
evidence BEFORE the command runs.

── THE ARMS, AND WHY EACH ONE IS HERE ──────────────────────────────────────
A1  a fixture that prunes with no record at all              -> MUST be flagged
A2  a fixture that records, then prunes                      -> MUST pass
A3  a fixture whose "record" is only in a COMMENT above the
    prune                                                    -> MUST be flagged
A4  a fixture whose prune is itself only in a comment        -> MUST NOT be
    flagged (a note about gc is not a gc)
A4b a fixture whose prune text is only in a DOCSTRING        -> MUST NOT be
    flagged; a line-oriented stripper cannot see a docstring at all
A4c a fixture running `git worktree prune`                    -> MUST NOT be
    flagged; it removes administrative files and destroys no object
A4d a fixture whose prune text is only in a PROSE STRING
    CONSTANT in a data table                                  -> MUST NOT be
    flagged
A5  --require-record with no record present                  -> MUST refuse
A6  --require-record with a record dated before today        -> MUST refuse
A7  --require-record with a record dated today               -> MUST pass
A8  --record when `git` cannot run                           -> MUST exit 2
    COULD NOT RUN, never 0
A9  --record writes fsck --unreachable AND object mtimes     -> both keys
    present and non-null, or the record is not evidence
A10 the real repo, audited                                   -> clean, and the
    report carries the DISCLOSED section so nothing is dropped silently

A3 IS THE ARM THAT MATTERS and it is the sixth instance of its class on this
platform: a control whose condition is satisfiable by comment text instead of
behaviour. The gate strips comments before asking whether the record call is
present.

A4b, A4c AND A4d ARE HERE BECAUSE THE FIRST VERSION OF THE GATE FAILED ALL
THREE. It matched text over comment-stripped lines and produced 40 findings on
this repo, every one of them wrong: 37 were `git worktree prune`, and 3 were
prose inside docstrings and a description table. The gate now walks the Python
AST and reads only the string constants inside calls that actually execute a
subprocess, so a docstring and a data table fall out by construction. These
arms are what stop that from regressing into a text match again.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GATE = os.path.join(REPO, 'tools', 'purge_evidence_gate.py')

PASS, FAIL = [], []


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append(name)
    print('%-4s %-62s %s' % ('ok' if ok else 'FAIL', name, detail))


def run(args, cwd=None, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([sys.executable, GATE] + args, cwd=cwd or REPO,
                       capture_output=True, text=True, env=e)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


# ── fixtures ────────────────────────────────────────────────────────────────
F_NO_RECORD = '''\
import subprocess
def cleanup():
    subprocess.run(['git', 'reflog', 'expire', '--expire-unreachable=now', '--all'])
    subprocess.run(['git', 'gc', '--prune=now'])
'''

F_RECORDED = '''\
import subprocess
def cleanup():
    subprocess.run([sys.executable, 'tools/purge_evidence_gate.py', '--record'])
    subprocess.run(['git', 'gc', '--prune=now'])
'''

F_COMMENT_ONLY_RECORD = '''\
import subprocess
def cleanup():
    # tools/purge_evidence_gate.py --record was run by hand before this, honest
    # purge_evidence_gate.py --record
    subprocess.run(['git', 'gc', '--prune=now'])
'''

F_COMMENT_ONLY_PRUNE = '''\
import subprocess
def cleanup():
    # A note: git gc --prune=now and reflog expire --expire-unreachable=now
    # would destroy the forensics, so this function deliberately does neither.
    subprocess.run(['git', 'fsck', '--unreachable'])
'''

F_DOCSTRING_ONLY_PRUNE = '''\
"""A tool whose docstring describes the incident.

The evidence was destroyed by the `reflog expire --expire-unreachable=now` and
`gc --prune=now` that fixed the problem, which is why this exists.
"""
import subprocess


def cleanup():
    """Runs a read-only fsck. Does NOT run git gc --prune=now."""
    subprocess.run(['git', 'fsck', '--unreachable'])
'''

F_WORKTREE_PRUNE = '''\
import shutil
import subprocess
def teardown(wt):
    shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(['git', '-C', '.', 'worktree', 'prune'], capture_output=True)
'''

F_HELPER_GC = '''\
import subprocess
def git(repo, *args):
    return subprocess.run(['git', '-C', repo] + list(args), capture_output=True)
def cleanup(repo):
    git(repo, 'reflog', 'expire', '--expire-unreachable=now', '--all')
    git(repo, 'gc', '--prune=now')
'''

F_HELPER_WORKTREE = '''\
import subprocess
def git(repo, *args):
    return subprocess.run(['git', '-C', repo] + list(args), capture_output=True)
def cleanup(repo):
    git(repo, 'worktree', 'prune')
'''

F_PROSE_STRING_PRUNE = '''\
DESCRIPTIONS = {
    'credential_purge_check.py': ('CHECKER', "a credential value still in some "
        "clone's object store. Built because the reflog expire "
        "--expire-unreachable=now and gc --prune=now that fixed the problem also "
        "destroyed the only forensics."),
}
'''


def fixture_dir():
    d = tempfile.mkdtemp(prefix='purge_evidence_probe_')
    os.makedirs(os.path.join(d, 'tools'))
    return d


def write(d, rel, body):
    p = os.path.join(d, rel)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
    return p


def audit_flags(d, rel):
    rc, out = run(['--audit', '--root', d])
    return rc, out, rel in out.replace('\\', '/')


if not os.path.isfile(GATE):
    print('COULD NOT RUN -- tools/purge_evidence_gate.py does not exist.')
    print('That is not a pass. Every arm below is unrun.')
    sys.exit(2)

# ── A1 / A2 / A3 / A4 ───────────────────────────────────────────────────────
for name, body, want_flag in (
        ('A1 prune with no record is flagged', F_NO_RECORD, True),
        ('A2 record then prune passes', F_RECORDED, False),
        ('A3 record only in a comment is flagged', F_COMMENT_ONLY_RECORD, True),
        ('A4 prune only in a comment is not flagged', F_COMMENT_ONLY_PRUNE, False),
        ('A4b prune only in a docstring is not flagged', F_DOCSTRING_ONLY_PRUNE, False),
        ('A4c git worktree prune is not flagged', F_WORKTREE_PRUNE, False),
        ('A4d prune in a prose string constant is not flagged', F_PROSE_STRING_PRUNE, False),
        ('A4e a local git() helper running gc IS flagged', F_HELPER_GC, True),
        ('A4f a local git() helper running worktree prune is not flagged', F_HELPER_WORKTREE, False)):
    d = fixture_dir()
    try:
        write(d, 'tools/fixture_cleanup.py', body)
        rc, out, named = audit_flags(d, 'tools/fixture_cleanup.py')
        if want_flag:
            check(name, rc == 1 and named, 'exit=%d named=%s' % (rc, named))
        else:
            check(name, rc == 0, 'exit=%d' % rc)
    finally:
        shutil.rmtree(d, ignore_errors=True)

# ── A5 / A6 / A7 -- --require-record ────────────────────────────────────────
d = fixture_dir()
try:
    rc, out = run(['--require-record', '--dir', os.path.join(d, 'records')])
    check('A5 no record at all refuses', rc != 0, 'exit=%d' % rc)

    recs = os.path.join(d, 'records')
    os.makedirs(recs)
    stale = {'recorded_at': '2026-01-01T00:00:00Z', 'clone': os.path.basename(REPO),
             'unreachable': [], 'object_mtimes': {}}
    io.open(os.path.join(recs, '2026-01-01-stale.json'), 'w', encoding='utf-8').write(
        json.dumps(stale))
    rc, out = run(['--require-record', '--dir', recs])
    check('A6 a record dated before today refuses', rc != 0, 'exit=%d' % rc)

    rc, out = run(['--record', '--dir', recs])
    if rc != 0:
        check('A7 a record dated today passes', False, 'could not --record: exit=%d' % rc)
    else:
        rc2, out2 = run(['--require-record', '--dir', recs])
        check('A7 a record dated today passes', rc2 == 0, 'exit=%d' % rc2)

    # ── A9 -- the record has to BE evidence ─────────────────────────────────
    files = [f for f in os.listdir(recs) if f != '2026-01-01-stale.json']
    if not files:
        check('A9 record carries fsck output and object mtimes', False, 'no record written')
    else:
        rec = json.load(io.open(os.path.join(recs, files[0]), encoding='utf-8'))
        ok = ('unreachable' in rec and rec['unreachable'] is not None
              and 'object_mtimes' in rec and rec['object_mtimes'] is not None
              and 'fsck_exit' in rec)
        check('A9 record carries fsck output and object mtimes', ok,
              'keys=%s' % sorted(rec.keys()))
finally:
    shutil.rmtree(d, ignore_errors=True)

# ── A8 -- git unavailable must be COULD NOT RUN, not a clean record ─────────
d = fixture_dir()
try:
    rc, out = run(['--record', '--dir', os.path.join(d, 'records')],
                  env={'SAIRN_PURGE_EVIDENCE_GIT': os.path.join(d, 'no-such-git')})
    check('A8 git unavailable is exit 2 COULD NOT RUN', rc == 2,
          'exit=%d' % rc)
    wrote = os.path.isdir(os.path.join(d, 'records')) and \
        [f for f in os.listdir(os.path.join(d, 'records'))]
    check('A8b no record is written when git could not run', not wrote,
          'wrote=%s' % (wrote or 'nothing'))
finally:
    shutil.rmtree(d, ignore_errors=True)

# ── A10 -- the real repo ────────────────────────────────────────────────────
rc, out = run(['--audit'])
has_sections = 'EXECUTABLE' in out and 'DISCLOSED' in out
check('A10 real-repo audit carries both sections', has_sections, 'exit=%d' % rc)
check('A10b real repo has no unguarded history-destroying command', rc == 0,
      'exit=%d -- see the EXECUTABLE section above' % rc)

print('')
print('%d passed, %d failed' % (len(PASS), len(FAIL)))
for f in FAIL:
    print('  FAILED: %s' % f)
sys.exit(1 if FAIL else 0)
