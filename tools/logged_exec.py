#!/usr/bin/env python3
# OWNER: cc
"""Run a patch-apply or hook-touching command with its full argv logged FIRST.

    python tools/logged_exec.py -- git apply path/to/x.patch
    python tools/logged_exec.py --log      # print the log
    python tools/logged_exec.py --fixtures

THE RULE (cc b59, methodology): every command that applies a patch or touches
a hook or gate file is run through this wrapper, never typed into a shell.
The wrapper:
  1. writes the exact argv, the cwd, the time and the session to
     .git/sairn-exec-log.jsonl BEFORE it runs, so the command is on record even
     if it is what breaks the tree;
  2. REFUSES any argument that is a shell operator (>, >>, 2>, |, &&, ;) or
     that starts with one. It runs the command WITHOUT a shell, so such a token
     would be passed through literally, never interpreted. A redirect wanted
     here means the command is being run the wrong way;
  3. records the size and git blob hash of every gate file before and after,
     and exits 3 if any gate changed during the run.

WHY: on 2026-10-27, at about 11:04, tools/sairn_push_gate_hook.py was
truncated to 0 bytes and empty files named `cd` and `git` appeared in cc's
clone, during a window in which a patch was applied in that clone by a command
nobody captured (cc b58 handoff, section 1). Empty files named after the
first word of each command segment are the signature of a redirect attaching
to the next token, and with no argv on record the cause could not be
reconstructed.

Exit codes: the command's own exit code; 2 for a refusal (a shell operator,
no command, or a log that cannot be written); 3 when a gate file changed.
"""
import datetime
import json
import os
import subprocess
import sys

GATES = ('tools/sairn_push_gate_hook.py', 'tools/register_feed_gate.py',
         'tools/copy_exactly_gate.py', 'tools/hover_auditor_scope_gate.py',
         '.githooks/pre-push', '.githooks/pre-commit', '.githooks/post-rewrite')
SHELL_OPS = ('>', '>>', '2>', '2>>', '&>', '|', '||', '&&', ';', '<')


def shell_op(arg):
    """The shell operator an argument is, or starts with; else None."""
    a = str(arg)
    for op in sorted(SHELL_OPS, key=len, reverse=True):
        if a == op or a.startswith(op):
            return op
    return None


def git(*a):
    r = subprocess.run(['git'] + list(a), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ''


def snapshot(root):
    out = {}
    for g in GATES:
        p = os.path.join(root, g)
        out[g] = (os.path.getsize(p), git('hash-object', p)) if os.path.isfile(p) else (None, None)
    return out


def tree(root):
    """Every path git status names, with its size. Diffed before/after, this is
    where a redirect inside a `cmd /c` or `sh -c` argument actually landed --
    the argv alone cannot say, because the redirect is inside one argument."""
    r = subprocess.run(['git', '-C', root, 'status', '--porcelain', '--untracked-files=all'],
                       capture_output=True, text=True)
    out = {}
    for ln in r.stdout.splitlines():
        p = ln[3:].strip().strip('"')
        f = os.path.join(root, p)
        out[p] = (ln[:2], os.path.getsize(f) if os.path.isfile(f) else None)
    return out


def append_line(log, obj):
    """One JSON line, LF-terminated on every platform. Both writers used to
    open the log in TEXT mode, so on Windows every row ended CRLF -- the class
    H1 fixed in its own block_log() (5c572340), found here by cc b69's audit of
    cc-owned write paths. newline='\\n' turns the translation off."""
    with open(log, 'a', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps(obj) + '\n')


def run_fixtures():
    cases = [(shell_op('>'), '>'), (shell_op('>tools/x.py'), '>'), (shell_op('2>&1'), '2>'),
             (shell_op('|'), '|'), (shell_op('&&'), '&&'), (shell_op('git'), None),
             (shell_op('a>b'), None), (shell_op('-m'), None)]
    bad = ['shell_op got %r, wanted %r' % (g, w) for g, w in cases if g != w]
    import tempfile
    lp = os.path.join(tempfile.mkdtemp(prefix='logged-exec-'), 'log.jsonl')
    append_line(lp, {'a': 1})
    append_line(lp, {'b': 2})
    raw = open(lp, 'rb').read()
    if b'\r' in raw or raw.count(b'\n') != 2:
        bad.append('append_line wrote %r -- not two LF-only rows' % raw)
    return bad, len(cases) + 1


def main(argv):
    if '--fixtures' in argv:
        bad, n = run_fixtures()
        print('LOGGED EXEC -- %d/%d fixtures' % (n - len(bad), n))
        for b in bad:
            print('  ! ' + b)
        return 2 if bad else 0
    root = git('rev-parse', '--show-toplevel')
    gitdir = git('rev-parse', '--absolute-git-dir')
    if not root or not gitdir:
        print('COULD NOT RUN: not inside a git work tree.')
        return 2
    log = os.path.join(gitdir, 'sairn-exec-log.jsonl')
    if '--log' in argv:
        print(open(log, encoding='utf-8').read() if os.path.isfile(log) else '(no log yet)')
        return 0
    if '--' not in argv or not argv[argv.index('--') + 1:]:
        print('usage: python tools/logged_exec.py -- <command> [args...]')
        return 2
    cmd = argv[argv.index('--') + 1:]
    ops = [(a, shell_op(a)) for a in cmd if shell_op(a)]
    rec = {'at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
           'session': os.environ.get('SAIRN_SESSION') or '', 'cwd': os.getcwd(), 'argv': cmd,
           'shell_operators': [a for a, _ in ops], 'refused': bool(ops)}
    try:
        append_line(log, rec)
    except OSError as e:
        print('REFUSED: the exec log could not be written (%s), so the command is not run.' % e)
        return 2
    print('LOGGED argv: %s' % json.dumps(cmd))
    if ops:
        print('REFUSED: argument(s) %s are shell operators. This runs WITHOUT a shell, so a '
              'redirect would not happen here -- and in a shell it is the shape that truncated '
              'the push gate on 2026-10-27. Run the command without the redirect.' % [a for a, _ in ops])
        return 2
    before, tree0 = snapshot(root), tree(root)
    rc = subprocess.run(cmd).returncode
    after, tree1 = snapshot(root), tree(root)
    changed = [g for g in GATES if before[g] != after[g]]
    delta = sorted('%s %s %s bytes' % (st, p, sz) for p, (st, sz) in tree1.items()
                   if tree0.get(p) != (st, sz))
    append_line(log, {'at': rec['at'], 'argv': cmd, 'rc': rc, 'gates_changed': changed,
                      'tree_delta': delta})
    for d in delta:
        print('TREE CHANGED: %s' % d)
    if changed:
        print('GATE FILE CHANGED during this command: %s. Check it before any push.' % ', '.join(changed))
        return 3
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
