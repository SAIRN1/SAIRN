#!/usr/bin/env python
# OWNER: cc
# written 2026-10-14, batch b8, queue item 5
"""WHEN does git hand a pre-push hook NO ref lines on stdin?

cc b8 item 5, and it is a REPRODUCTION BEFORE A PATCH -- no change to
tools/register_feed_gate.py is written until this says what the condition is.

THE REFUSAL BEING CHASED, seen twice in cc b7 and recorded in
docs/2026-10-13-cc-routed-b7.md section 2.3:

    register_feed_gate: stdin is not a terminal and carried NO ref lines.

b7 observed it while 9 commits behind, and then observed the OPPOSITE later in
the same batch -- behind again, ref lines present. So "behind" is not the
condition, and nothing else was established. This builds real repositories and
measures git itself.

    python tools/prepush_refline_repro.py [<outdir>]   # measure git
    python tools/prepush_refline_repro.py --message-arms  # lock the message

EIGHT states, each with a pre-push hook that records exactly what it was given:

  A  ahead only (ordinary fast-forward push)
  B  ahead AND behind (diverged -- b7's state)
  C  behind only, nothing to push
  D  up to date, nothing to push
  E  ahead, pushed through a PIPE (`git push | cat`)
  F  ahead, pushed with stdin redirected from /dev/null
  G  ahead, pushed from inside a .sh FILE
  H  ahead, pushed from a python subprocess

E through H are here because the gate's own message blamed a wrapper, and that
claim had never been tested. MEASURED 2026-10-14, git 2.54.0.windows.1:

  ref lines PRESENT : A, E, F, G, H -- so a pipe, a redirected stdin, a shell
                      script and a python subprocess are ALL FINE. git hands
                      the refs to the hook it runs, not to whoever asked.
  ref lines ABSENT  : B (exit 1), C (exit 1), D (exit 0) -- every state where
                      git is NOT GOING TO SEND ANYTHING. That is the condition
                      nobody had named, and it is now the message
                      register_feed_gate.py prints.

`--message-arms` locks the four branches of that message against this
measurement, so the prose and the experiment cannot drift apart: the git half
needs real repositories and takes seconds, the message half is a pure function
and is checked every time somebody edits the gate.

Prints one line per state: the state, git's exit code, how many ref lines the
hook saw, and whether the hook ran at all.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

PY = sys.executable.replace(chr(92), '/')


def run(cwd, *args, **kw):
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', **kw)


def git(cwd, *args, **kw):
    return run(cwd, 'git', *args, **kw)


HOOK = '''#!/bin/sh
# Record EXACTLY what git handed this hook. Never refuse.
REFS=$(cat)
printf '%s' "$REFS" > "$RECORD.refs"
if [ -z "$REFS" ]; then echo "lines=0" > "$RECORD"; else
  echo "lines=$(printf '%s\\n' "$REFS" | grep -c .)" > "$RECORD"; fi
exit 0
'''


def build(tmp, name):
    """A bare 'origin' plus a clone with one commit pushed. -> (work, bare)."""
    bare = os.path.join(tmp, name + '.git')
    work = os.path.join(tmp, name)
    git(tmp, 'init', '--bare', '-q', '-b', 'main', bare)
    git(tmp, 'clone', '-q', bare, work)
    git(work, 'config', 'user.email', 'probe@example.invalid')
    git(work, 'config', 'user.name', 'probe')
    git(work, 'config', 'push.default', 'simple')
    io.open(os.path.join(work, 'base.txt'), 'w').write('base\n')
    git(work, 'add', '-A')
    git(work, 'commit', '-q', '-m', 'base')
    git(work, 'push', '-q', 'origin', 'main')
    return work, bare


def arm_hook(work, record):
    hooks = os.path.join(work, '.git', 'hooks')
    os.makedirs(hooks, exist_ok=True)
    p = os.path.join(hooks, 'pre-push')
    io.open(p, 'w', newline='\n').write(HOOK)
    os.chmod(p, 0o755)
    return {'RECORD': record}


def commit(work, text, name='local.txt'):
    io.open(os.path.join(work, name), 'a').write(text + '\n')
    git(work, 'add', '-A')
    git(work, 'commit', '-q', '-m', text)


def diverge_remote(tmp, bare, text):
    """Another clone pushes, so `bare` moves on without `work` knowing."""
    other = tempfile.mkdtemp(prefix='other-', dir=tmp)
    git(tmp, 'clone', '-q', bare, other)
    git(other, 'config', 'user.email', 'other@example.invalid')
    git(other, 'config', 'user.name', 'other')
    io.open(os.path.join(other, 'remote.txt'), 'a').write(text + '\n')
    git(other, 'add', '-A')
    git(other, 'commit', '-q', '-m', text)
    git(other, 'push', '-q', 'origin', 'main')


def read_record(record):
    if not os.path.isfile(record):
        return None, 'the hook DID NOT RUN'
    txt = io.open(record).read().strip()
    n = int(txt.split('=')[1])
    refs = ''
    if os.path.isfile(record + '.refs'):
        refs = io.open(record + '.refs').read().strip()
    return n, refs[:120]


def state(tmp, name, prepare, push, label):
    work, bare = build(tmp, name)
    record = os.path.join(tmp, name + '.record')
    env = dict(os.environ)
    env.update(arm_hook(work, record))
    prepare(tmp, work, bare)
    rc, out = push(work, env)
    n, detail = read_record(record)
    print('  %-46s git exit %-3s  ref lines: %-6s  %s'
          % (label, rc, 'HOOK DID NOT RUN' if n is None else n,
             (detail or '')[:70]))
    return {'state': label, 'git_exit': rc, 'ref_lines': n,
            'detail': detail, 'push_output': out[-300:]}


def plain_push(work, env):
    r = git(work, 'push', 'origin', 'main', env=env)
    return r.returncode, (r.stdout + r.stderr)


def piped_push(work, env):
    r = run(work, 'sh', '-c', 'git push origin main | cat', env=env)
    return r.returncode, (r.stdout + r.stderr)


def devnull_push(work, env):
    r = run(work, 'sh', '-c', 'git push origin main < /dev/null', env=env)
    return r.returncode, (r.stdout + r.stderr)


def script_push(work, env):
    """A push from inside a .sh FILE -- the case the gate's message blames."""
    s = os.path.join(work, 'do_push.sh')
    io.open(s, 'w', newline=chr(10)).write(
        '#!/bin/sh' + chr(10) + 'git push origin main' + chr(10))
    os.chmod(s, 0o755)
    r = run(work, 'sh', s, env=env)
    return r.returncode, (r.stdout + r.stderr)


def python_push(work, env):
    """A push from a python subprocess -- sairn_claim.py's shape."""
    r = run(work, PY, '-c',
            'import subprocess,sys;'
            'r=subprocess.run(["git","push","origin","main"],'
            'capture_output=True,text=True);'
            'sys.stdout.write(r.stdout+r.stderr);sys.exit(r.returncode)',
            env=env)
    return r.returncode, (r.stdout + r.stderr)


def message_arms():
    """Lock register_feed_gate's empty-stdin message to the measurement above.

    Four branches, driven by substituting the ahead/behind reading -- the one
    input that decides which sentence a reader gets. Without this, the next
    edit to that message can quietly go back to blaming a wrapper.
    """
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, 'register_feed_gate.py')
    if not os.path.isfile(target):
        print('COULD NOT RUN: %s is absent, so the message was NOT checked.'
              % target)
        return 2
    sys.path.insert(0, here)
    spec = importlib.util.spec_from_file_location('rfg_subject', target)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:                                     # noqa: BLE001
        print('COULD NOT RUN: register_feed_gate would not import (%s).' % exc)
        return 2
    keep = mod.ahead_behind
    arms = [
        ((3, 9, 'origin/main'), 'NON-FAST-FORWARD',
         'ahead AND behind -- state B, the one b7 was denied in'),
        ((0, 4, 'origin/main'), 'NOTHING TO PUSH',
         'nothing to push -- states C and D'),
        ((2, 0, 'origin/main'), 'REAL ANOMALY',
         'ahead only, no refs anyway -- the earned refusal'),
        ((None, None, 'this branch has no upstream'), 'COULD NOT BE MEASURED',
         'the reading itself failed -- a third state, not a pass'),
    ]
    bad = 0
    print('register_feed_gate empty-stdin MESSAGE ARMS')
    try:
        for triple, want, label in arms:
            mod.ahead_behind = lambda t=triple: t
            msg = mod.no_reflines_reason()
            ok = want in msg.upper()
            # And the measured half must be in EVERY branch, including the
            # refusal of the wrapper story this replaced.
            ok = ok and 'MEASURED, NOT GUESSED' in msg
            ok = ok and 'wrapper explanation this' in msg
            if not ok:
                bad += 1
            print('  %-4s %s' % ('PASS' if ok else 'FAIL', label))
        mod.ahead_behind = keep
        # THE NEGATIVE HALF: the old sentence must be gone, or three of the
        # arms above would pass over a message that still blames a script.
        src = io.open(target, encoding='utf-8').read()
        gone = 'ISSUE THE PUSH DIRECTLY' not in src
        if not gone:
            bad += 1
        print('  %-4s the wrapper diagnosis is GONE from the source, not just '
              'unreached' % ('PASS' if gone else 'FAIL'))
    finally:
        mod.ahead_behind = keep
    print('  %d/%d arm(s) pass' % (5 - bad, 5))
    return 1 if bad else 0


def main():
    if '--message-arms' in sys.argv:
        return message_arms()
    tmp = tempfile.mkdtemp(prefix='prepush-repro-')
    results = []
    print('PRE-PUSH REF-LINE REPRODUCTION -- real repositories, real git')
    print('  git: %s' % git(tmp, '--version').stdout.strip())
    print('  tmp: %s' % tmp)
    print('')
    try:
        results.append(state(
            tmp, 'a', lambda t, w, b: commit(w, 'ahead-1'), plain_push,
            'A  ahead only'))
        def prep_b(t, w, b):
            commit(w, 'ahead-1')
            diverge_remote(t, b, 'remote-1')
            git(w, 'fetch', '-q', 'origin')
        results.append(state(tmp, 'b', prep_b, plain_push,
                             'B  ahead AND behind (b7 state)'))
        def prep_c(t, w, b):
            diverge_remote(t, b, 'remote-1')
            git(w, 'fetch', '-q', 'origin')
        results.append(state(tmp, 'c', prep_c, plain_push,
                             'C  behind only, nothing to push'))
        results.append(state(tmp, 'd', lambda t, w, b: None, plain_push,
                             'D  up to date, nothing to push'))
        results.append(state(
            tmp, 'e', lambda t, w, b: commit(w, 'ahead-1'), piped_push,
            'E  ahead, pushed through a pipe'))
        results.append(state(
            tmp, 'f', lambda t, w, b: commit(w, 'ahead-1'), devnull_push,
            'F  ahead, stdin from /dev/null'))
        results.append(state(
            tmp, 'g', lambda t, w, b: commit(w, 'ahead-1'), script_push,
            'G  ahead, pushed from inside a .sh FILE'))
        results.append(state(
            tmp, 'h', lambda t, w, b: commit(w, 'ahead-1'), python_push,
            'H  ahead, pushed from a python subprocess'))
    finally:
        print('')
        out = os.path.join(sys.argv[1], 'prepush_repro_results.json') \
            if len(sys.argv) > 1 else 'prepush_repro_results.json'
        io.open(out, 'w').write(json.dumps(results, indent=2))
        print('  raw results: %s' % out)
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
