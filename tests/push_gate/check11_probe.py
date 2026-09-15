"""tests/push_gate/check11_probe.py

Run:  python tests/push_gate/check11_probe.py

CHECK 11 -- a raw control byte in what this push ships must be REFUSED.

── WHY IT IS BLOCKING ────────────────────────────────────────────────────────
Promoted from report-only on 2026-09-13 on a real track record. The 2026-09-10
sweep of 1,624 tracked files found FOUR raw control bytes; the same checker
caught a fifth on 2026-09-13 within hours of the file shipping --
`/<BS>delete<BS>/i` in api/sv-auth.test.js, the assertion that SAIRNvet's auth
endpoint deletes no credential row. Zero false positives in either sweep.

Every one is the same mistake: an escape sequence typed as its literal control
character. A `\\b` that became a backspace byte is a regex that can NEVER MATCH,
so the assertion around it passes on the exact input it exists to refuse -- two
of the four were privilege guards in that state. A raw NUL is worse in a
different way: grep answers `Binary file ... matches` and prints no lines, so the
file silently stops being searchable.

── SCOPED TO THE PUSH, AND THAT IS WHAT MAKES BLOCKING SURVIVABLE ────────────
The whole-tree scan is the right question for a sweep and the wrong one for a
gate. api/sv-auth.test.js carries a standing finding inside another session's
active claim, so a tree-wide deny would refuse EVERY push until somebody else's
file was fixed -- the state check 5 has been stuck in since 2026-09-01. Section
E below pins the scoping directly: a push that ships a CLEAN file is allowed
while that standing finding still exists in the tree.

── WHAT IS PLANTED ───────────────────────────────────────────────────────────
A committed text file containing a raw 0x08, which is the shape that has
actually occurred four times. The controls are the same file without the byte,
a binary-extension file that carries one (skipped by design, and the skip is the
reason a .png full of control bytes does not refuse every push), and the
missing-checker case.
"""
import io
import os
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
GATE = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')
TOOL_REL = 'tools/control_char_check.py'
FAIL = []

# Built rather than typed. A heredoc or an editor that helpfully "fixes" the
# escape is exactly how this defect keeps arriving, and a probe that planted a
# two-character `\b` instead of the byte would prove nothing.
BS = bytes([0x08])
NUL = bytes([0x00])


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:400]))
    if not cond:
        FAIL.append(name)


def git(cwd, *args):
    return subprocess.run(['git', '-C', cwd] + list(args), capture_output=True, text=True, encoding='utf-8', errors='replace')


def run_gate(cwd, tip, base):
    line = 'refs/heads/probe %s refs/heads/probe %s\n' % (tip, base)
    r = subprocess.run([sys.executable, GATE, '--pre-push'],
                       input=line, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=cwd)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def commit(wt, rel, body_bytes, subject):
    """Stage one file and commit. The subject must NOT begin with PROBE -- check
    8 refuses those and would answer instead of check 11."""
    full = os.path.join(wt, rel)
    d = os.path.dirname(full)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(full, 'wb').write(body_bytes)
    git(wt, 'add', '-f', rel)
    git(wt, '-c', 'user.name=probe', '-c', 'user.email=probe@local',
        'commit', '-q', '-m', subject)
    return git(wt, 'rev-parse', 'HEAD').stdout.strip()


def sync_tools(wt):
    """Re-copy the working-tree gate and checker into the worktree.

    `git reset --hard` reverts them to committed HEAD, so every reset below has
    to be followed by this or the next arm silently tests the old code.
    """
    for rel in (TOOL_REL, 'tools/sairn_push_gate_hook.py'):
        io.open(os.path.join(wt, rel.replace('/', os.sep)), 'wb').write(
            io.open(os.path.join(REPO, rel.replace('/', os.sep)), 'rb').read())


def worktree():
    d = os.path.join(tempfile.gettempdir(), 'gate-probe11-%d' % os.getpid())
    git(REPO, 'worktree', 'add', '-q', '--detach', d, 'HEAD')
    # THE WORKTREE IS AT COMMITTED HEAD, AND THE GATE RUNS THE WORKTREE'S COPY.
    # Without these two lines the arms below drive the PREVIOUS versions of the
    # gate and the checker, so an uncommitted change cannot be verified until
    # after it is committed -- and the first run of this probe did exactly that:
    # the checker it exercised still scanned the whole tree, so a "clean file is
    # allowed" control failed on a standing finding in somebody else's file
    # while the scoped version in the working tree would have passed it. Third
    # time today this trap has been hit; copying the subject in is the fix.
    sync_tools(d)
    return d


def drop(d):
    git(REPO, 'worktree', 'remove', '--force', d)
    git(REPO, 'worktree', 'prune')


REL = 'probe_check11.txt'
CLEAN = b'a line with a tab\tand a newline, both allowed\n'

print('\nA. the fixture really carries the byte before anything is asserted')
wt = worktree()
try:
    ok('the worktree exists and is detached', os.path.isdir(os.path.join(wt, 'tools')))
    base = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    tip = commit(wt, REL, b'assert(/' + BS + b'delete' + BS + b'/i.test(x));\n',
                 'fixture: a regex with a literal backspace')
    raw = io.open(os.path.join(wt, REL), 'rb').read()
    ok('the planted file contains a RAW 0x08, not the two-character escape',
       BS in raw and b'\\b' not in raw, repr(raw))
    # The checker must see it on its own, or the gate arm proves nothing.
    c = subprocess.run([sys.executable, os.path.join(REPO, TOOL_REL),
                        os.path.join(wt, REL)], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
    ok('the checker itself reports it (exit 1)', c.returncode == 1,
       'exit=%d %s' % (c.returncode, (c.stdout or '')[-200:]))

    print('\nB. CHECK 11 -- the GATE refuses the push')
    rc, out = run_gate(wt, tip, base)
    low = out.lower()
    ok('the gate refuses', rc != 0, 'exit=%d\n%s' % (rc, out[-400:]))
    ok('...and the refusal is CHECK 11, naming the raw byte',
       'raw control byte' in low, out[-500:])
    ok('...and it names the file and the byte value',
       REL in out and '0x08' in out, out[-500:])
    ok('...and it says the regex can never match, which is the reason it blocks',
       'never match' in low, out[-500:])
    ok('...and it is NOT the PROBE-fixture check answering instead',
       'PROBE fixture commit' not in out, out[-300:])

    print('\nC. a raw NUL is refused too -- the other shape that has occurred')
    git(wt, 'reset', '-q', '--hard', base); sync_tools(wt)
    tip2 = commit(wt, REL, b'var sep = "' + NUL + b'";\n',
                  'fixture: a NUL used as a separator')
    rc, out = run_gate(wt, tip2, base)
    ok('the gate refuses a raw NUL', rc != 0, 'exit=%d\n%s' % (rc, out[-400:]))
    ok('...and names it', '0x00' in out, out[-400:])

    print('\nD. CONTROL -- the same file WITHOUT the byte is allowed')
    # Without this, every arm above is "the gate refuses this filename".
    git(wt, 'reset', '-q', '--hard', base); sync_tools(wt)
    tip3 = commit(wt, REL, CLEAN, 'fixture: the same file, escapes typed properly')
    rc, out = run_gate(wt, tip3, base)
    ok('a clean text file is allowed, tabs and newlines included', rc == 0,
       'exit=%d\n%s' % (rc, out[-400:]))

    print('\nE. CONTROL -- a finding ELSEWHERE in the tree does NOT block a clean push')
    # THE SCOPING ARM, AND IT PLANTS ITS OWN ELSEWHERE (rewritten 2026-09-14).
    # It used to assert that api/sv-auth.test.js still carried raw backspaces --
    # somebody else's file, inside another session's claim. They fixed it, the
    # tree went clean, and this arm failed while the behaviour it tests was
    # perfectly correct. A control whose precondition is another session's
    # UNFIXED DEFECT expires the moment they do their job.
    #
    # So it commits a dirty file into the BASE, then pushes a clean one on top:
    # the outgoing range holds only the clean file while the worktree still
    # carries a finding. If check 11 read the tree instead of the push, this
    # would be refused.
    git(wt, 'reset', '-q', '--hard', base); sync_tools(wt)
    dirty_base = commit(wt, 'probe_check11_elsewhere.txt',
                        b'x = "' + BS + b'";\n',
                        'fixture: a control byte that this push will not ship')
    tip6 = commit(wt, REL, CLEAN, 'fixture: a clean file pushed over a dirty tree')
    standing = subprocess.run([sys.executable, os.path.join(REPO, TOOL_REL),
                               os.path.join(wt, 'probe_check11_elsewhere.txt')],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
    ok('the worktree really does carry a finding somewhere else',
       standing.returncode == 1, (standing.stdout or '')[-200:])
    rc6, out6 = run_gate(wt, tip6, dirty_base)
    ok('...and a push that does not SHIP it is allowed, so the check is scoped',
       rc6 == 0, 'exit=%d\n%s' % (rc6, out6[-400:]))

    print('\nF. a BINARY file carrying control bytes is not refused')
    git(wt, 'reset', '-q', '--hard', base); sync_tools(wt)
    tip4 = commit(wt, 'probe_check11.png', b'\x89PNG\r\n\x1a\n' + NUL * 8,
                  'fixture: a png, which is full of control bytes by nature')
    rc4, out4 = run_gate(wt, tip4, base)
    ok('a binary-extension file is skipped rather than refused', rc4 == 0,
       'exit=%d\n%s' % (rc4, out4[-400:]))

    print('\nG. a MISSING checker is refused, not skipped')
    git(wt, 'reset', '-q', '--hard', base); sync_tools(wt)
    tip5 = commit(wt, REL, b'x = "' + BS + b'";\n', 'fixture: a byte to check')
    victim = os.path.join(wt, TOOL_REL)
    ok('the checker is present before the sabotage removes it',
       os.path.isfile(victim), victim)
    os.remove(victim)
    ok('...and the sabotage really applied -- it is gone',
       not os.path.exists(victim), victim)
    try:
        rc5, out5 = run_gate(wt, tip5, base)
    finally:
        git(wt, 'checkout', '-q', '--', TOOL_REL)
    ok('the gate refuses when the checker is absent', rc5 != 0,
       'exit=%d\n%s' % (rc5, out5[-400:]))
    ok('...and names the exact path it looked for',
       victim.replace('\\', '/') in out5.replace('\\', '/'),
       'looked for %s in\n%s' % (victim, out5[-400:]))
    ok('...and the checker is restored in the worktree', os.path.isfile(victim))
finally:
    drop(wt)
    ok('the throwaway worktree is removed', not os.path.isdir(wt))
    ok('no fixture was left on this clone',
       not any(os.path.exists(os.path.join(REPO, p))
               for p in (REL, 'probe_check11.png',
                         'probe_check11_elsewhere.txt')))
    ok('this clone still has its own control-byte checker',
       os.path.isfile(os.path.join(REPO, TOOL_REL)))

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
