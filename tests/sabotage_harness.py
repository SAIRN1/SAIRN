"""The ONE worktree-isolated sabotage harness every new negative control uses.

WHY A SHARED MODULE AND NOT A COPY. This repo has already paid for the other
choice: `tools/` held SEVEN separate `strip_comments` implementations and three
of them were destroying 90% of their input while reporting clean. The harness
below carries five disciplines that were each learned the expensive way, and a
copied harness is a copy that will drift from all five:

  * IT MUTATES A THROWAWAY GIT WORKTREE, never this clone. A probe that edits
    tracked files is indistinguishable from residue when it dies, and a stranded
    PROBE commit reached origin twice in two days on 2026-09-10 -- once deleting
    a field that had already made SAIRNlaw compute Florida deadlines five days
    late.
  * THE SUITE UNDER TEST IS COPIED IN FROM THIS CLONE, not taken from HEAD. A
    worktree at HEAD does not contain a suite that has not been committed yet,
    so the baseline would be red for a reason that has nothing to do with the
    subject -- and "red" is the verdict being read.
  * THE BASELINE RUNS FIRST. Without it every "BITES" could be a suite that was
    already failing, and the whole probe would report success while proving
    nothing.
  * ANCHOR-0 AND ANCHOR-2 ARE FAILURES, NOT SKIPS. A stale anchor is how this
    class of probe quietly stops testing anything, and an anchor matching twice
    plants in whichever place came first -- asserting something about a line
    nobody chose. Cluster 5b98fd27 carried exactly that defect.
  * DIRT IS COMPARED BEFORE AGAINST AFTER. Asking only "is this file dirty now"
    fires on the author's own uncommitted work, which is how a probe becomes one
    people ignore -- and that is how real residue gets through.

Usage:

    from sabotage_harness import run_probe
    SUITE = os.path.join('api', 'my-suite.test.js')
    MUTATIONS = [(name, relative_file, exact_old_text, new_text), ...]
    sys.exit(run_probe(SUITE, MUTATIONS, title='what this suite must refuse'))
"""
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace').stdout.strip()


def _run_suite(wt, suite):
    r = subprocess.run(['node', os.path.join(wt, suite)], cwd=wt,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def _read(wt, rel):
    with io.open(os.path.join(wt, rel), 'rb') as f:
        return f.read()


def _write(wt, rel, data):
    with io.open(os.path.join(wt, rel), 'wb') as f:
        f.write(data)


def _dirty_now():
    out = subprocess.run(['git', '-C', REPO, 'status', '--porcelain',
                          '--untracked-files=no'], capture_output=True,
                         text=True, encoding='utf-8', errors='replace').stdout
    return set(l.strip() for l in out.split('\n') if l.strip())


def run_probe(suite, mutations, title='', stage=()):
    """0 when every planted defect was refused, 1 when one was not, 3 when the
    probe could not run at all -- which is NOT a pass and says so.

    `stage` names EXTRA files to copy in from this clone alongside the suite.
    The worktree is at HEAD, so a fix that is not committed yet is not in it and
    the baseline goes red for a reason that has nothing to do with the subject.
    Without this a control could only ever run AFTER its fix was pushed, which
    is the wrong order: the control is what says the suite bites, and a suite
    that has never refused anything is exactly what a same-hour fix ships with.
    Every staged file must also be restorable, so they are snapshotted with the
    mutation targets and hash-checked at the end like everything else.
    """
    fails, ran = [], []

    def check(name, cond, detail=''):
        print(('  ok   ' if cond else '  FAIL ') + name
              + ('' if cond else '  ' + detail))
        ran.append(name)
        if not cond:
            fails.append(name)

    print((title or ('negative control for ' + suite)) + '\n')
    dirty_before = _dirty_now()

    wt = tempfile.mkdtemp(prefix='sairn-sab-')
    shutil.rmtree(wt, ignore_errors=True)
    add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach',
                          wt, 'HEAD'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace')
    if add.returncode != 0:
        print('COULD NOT RUN: no worktree -- NOTHING WAS VERIFIED. This is not '
              'a pass.')
        print(add.stderr.strip()[:300])
        return 3
    try:
        try:
            for rel in [suite] + list(stage):
                dst = os.path.join(wt, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy(os.path.join(REPO, rel), dst)
        except OSError as e:
            print('COULD NOT RUN: the suite would not stage into the worktree '
                  '-- NOTHING WAS VERIFIED. %s' % e)
            return 3

        rc, out = _run_suite(wt, suite)
        check('0. the suite is GREEN in the worktree before anything is '
              'planted (exit %s)' % rc, rc == 0,
              '\n       '.join([l for l in out.split('\n') if l.strip()][-4:]))
        if rc != 0:
            print('\n  The baseline is red, so no mutation below would mean '
                  'anything. Stopping.')
            return 1

        originals = {}
        for rel in sorted({m[1] for m in mutations}):
            originals[rel] = _read(wt, rel)

        for name, rel, old, new in mutations:
            src = originals[rel]
            hits = src.count(old.encode('utf-8'))
            if hits != 1:
                check(name, False, 'ANCHOR-%d in %s' % (hits, rel))
                continue
            _write(wt, rel, src.replace(old.encode('utf-8'),
                                        new.encode('utf-8'), 1))
            rc, out = _run_suite(wt, suite)
            check(name, rc != 0,
                  'SILENT -- the suite passed with this defect planted')
            _write(wt, rel, src)

        for rel, data in originals.items():
            check('the worktree copy of %s is byte-identical again' % rel,
                  hashlib.sha256(_read(wt, rel)).hexdigest()
                  == hashlib.sha256(data).hexdigest())
        rc, out = _run_suite(wt, suite)
        check('and the suite is GREEN again with everything restored (exit %s)'
              % rc, rc == 0)
    finally:
        shutil.rmtree(wt, ignore_errors=True)
        subprocess.run(['git', '-C', REPO, 'worktree', 'prune'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')

    new_dirt = sorted(_dirty_now() - dirty_before)
    check('this run left NOTHING newly dirty in this clone -- %d file(s) were '
          'already modified before it started and are not this probe\'s doing'
          % len(dirty_before), not new_dirt, '; '.join(new_dirt))

    print()
    if fails:
        print('%d ARM(S) FAILED:' % len(fails))
        for f in fails:
            print('  - ' + f)
        return 1
    print('ALL %d ARMS PASS -- every planted defect was refused (%d mutations).'
          % (len(ran), len(mutations)))
    return 0
