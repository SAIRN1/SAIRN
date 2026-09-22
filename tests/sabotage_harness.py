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
  * `stage` EVERY FILE THE SUITE READS THAT THIS SESSION HAS TOUCHED, not just
    the suite. The worktree is at HEAD. If the suite asserts something about a
    fix that is still uncommitted -- the app file, the lib, the tool -- the
    baseline measures the OLD code against the NEW suite, goes red, and plants
    nothing. THE SYMPTOM IS NOT OBVIOUS FROM THE MESSAGE: the probe says "the
    baseline is red, so no mutation below would mean anything", and the red arm
    is about your own change rather than about any mutation, so it reads as a
    broken suite. Two sessions hit this hours apart on 2026-09-21/22 and made
    the same one-line fix independently -- cody staging `api/sd-data.js` into
    `tests/session_gate_table_probe.py`, cc staging `sairnvet.html` into
    `tests/sairnvet_controlled_export_probe.py`. Neither found the other's note,
    because both were comments beside a call rather than a rule here. The
    baseline failure now NAMES the likely files; see `_unstaged_suspects()`.

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


# ── THE RUNNER IS CHOSEN BY EXTENSION (2026-09-18) ──────────────────────────
# `node` was hardcoded, so this harness -- whose own header calls it "the ONE
# worktree-isolated sabotage harness every new negative control uses" -- could
# not drive a PYTHON suite at all. Every control built on it guards a .js
# suite, which is why nobody had hit it.
#
# IT FAILED IN THE SAFE DIRECTION AND THAT IS WORTH RECORDING: node on a .py
# file exits non-zero, the baseline arm reports RED and the harness stops with
# "no mutation below would mean anything" rather than counting four refusals it
# never obtained. The defect cost a confusing message, not a false pass.
#
# A .js suite still goes to node, byte for byte as before.
def _run_suite(wt, suite):
    runner = ([sys.executable] if suite.endswith('.py') else ['node'])
    r = subprocess.run(runner + [os.path.join(wt, suite)], cwd=wt,
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


# ── CARRYING THE SESSION IDENTITY INTO THE WORKTREE (2026-09-18) ────────────
# A git worktree gets its OWN `.git/worktrees/<id>/` directory, so the marker
# hover #258 introduced -- this clone's session name, deliberately NOT derived
# from a directory name -- is absent inside it. Any suite that reaches
# session_name() therefore dies on NoIdentity before a single mutation is
# planted, and the baseline arm reports RED.
#
# THIS IS NOT THE SPOOF #258 CLOSED, and the difference is worth stating
# because the two look alike. A spoof is a clone claiming to be a DIFFERENT
# session. This copies THIS clone's own already-provisioned identity into a
# disposable copy of THIS clone, so the suite sees the same answer it would see
# here. It cannot invent one: if this clone is unprovisioned the helper raises
# and the probe reports COULD NOT RUN rather than guessing a name.
#
# OPT-IN, so no existing control changes behaviour.
def _carry_identity(wt):
    """Write this clone's session marker into the worktree's private git dir."""
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import sairn_session_identity as ident
    name = ident.session_name()            # raises if THIS clone is unprovisioned
    g = subprocess.run(['git', '-C', wt, 'rev-parse', '--absolute-git-dir'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if g.returncode != 0:
        raise RuntimeError('could not locate the worktree git dir: '
                           + g.stderr.strip()[:200])
    p = os.path.join(g.stdout.strip(), ident.MARKER)
    with io.open(p, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(name + '\n')
    return name


def _unstaged_suspects(suite, stage):
    """Files this clone has modified, named by the suite, and NOT staged.

    A guess, and it says so where it prints. The point is not to be right --
    it is that a session reading "the baseline is red" should be handed the
    list it would otherwise have to assemble by hand, which is what two
    sessions did independently before deciding to add one `stage` entry each.

    Deliberately NARROW: only files git reports as modified, and only those the
    suite mentions by path. A broader guess would print half the repo and be
    ignored, which is the failure mode of every noisy diagnostic.
    """
    try:
        dirty = subprocess.run(['git', '-C', REPO, 'status', '--porcelain'],
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace').stdout
    except OSError:
        return []
    changed = []
    for line in dirty.splitlines():
        rel = line[3:].strip().strip('"')
        if ' -> ' in rel:
            rel = rel.split(' -> ')[-1]
        if rel:
            changed.append(rel.replace('\\', '/'))
    if not changed:
        return []
    try:
        body = io.open(os.path.join(REPO, suite), encoding='utf-8',
                       errors='replace').read()
    except OSError:
        return []
    staged = {suite.replace('\\', '/')} | {s.replace('\\', '/') for s in stage}
    out = []
    for rel in changed:
        if rel in staged:
            continue
        # The suite has to NAME it -- by full path or by basename. A suite that
        # never mentions a file cannot be red because of it.
        base = rel.rsplit('/', 1)[-1]
        if rel in body or (len(base) > 6 and base in body):
            out.append(rel)
    return sorted(set(out))


def run_probe(suite, mutations, title='', stage=(), carry_identity=False):
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
        if carry_identity:
            try:
                who = _carry_identity(wt)
                print('  (session identity %r carried into the worktree -- see '
                      '_carry_identity)' % who)
            except Exception as e:                            # noqa: BLE001
                print('COULD NOT RUN: the session identity could not be carried '
                      'into the worktree, so the suite would die on NoIdentity '
                      'before anything was planted -- NOTHING WAS VERIFIED. %s'
                      % e)
                return 3
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
            # ── AND THE COMMONEST CAUSE IS NAMED, NOT LEFT TO BE GUESSED ──
            # See the sixth discipline in this module's header. The message
            # above is true and, on its own, sent two sessions hunting a
            # broken suite when the real cause was a file this clone has
            # changed and the worktree does not have.
            suspects = _unstaged_suspects(suite, stage)
            if suspects:
                print('\n  FILES THIS CLONE HAS CHANGED THAT THE SUITE NAMES '
                      'AND `stage` DOES NOT:')
                for rel in suspects:
                    print('      %s' % rel)
                print('  The worktree is at HEAD, so the baseline just measured '
                      'the OLD')
                print('  version of these against a suite that expects the new '
                      'one. If that')
                print('  is what happened, add them to `stage` -- that is what '
                      'the argument')
                print('  is for. If it is not, this list is noise and the suite '
                      'is really red.')
            return 1

        originals = {}
        for rel in sorted({m[1] for m in mutations}):
            originals[rel] = _read(wt, rel)

        for name, rel, old, new in mutations:
            src = originals[rel]
            # ── A MUTATION MAY NOW BE SEVERAL EDITS APPLIED TOGETHER ────────
            # (2026-09-21) Some properties are held by TWO guards that are
            # mutually redundant, and removing either one alone is SILENT by
            # construction -- the other catches it. A harness that can only
            # plant one edit cannot express "both of these must go", so the
            # only committed control for such a property was no control at
            # all: each single mutation reads as an unpinned guard and the
            # conjunction nobody can plant reads as untested.
            #
            # Found in api/sc-credentials.js, where the first-path UNKNOWN
            # check and the final gate are exactly that pair.
            #
            # A PLAIN STRING STILL BEHAVES EXACTLY AS BEFORE, byte for byte --
            # it is normalised to a one-element list and every existing
            # control takes the same path it always did. ANCHOR-0 and ANCHOR-2
            # are still failures, now PER EDIT, because a pair mutation with
            # one stale anchor is a mutation that plants half a defect and
            # reports on it as if it planted the whole one.
            olds = [old] if isinstance(old, str) else list(old)
            news = [new] if isinstance(new, str) else list(new)
            if len(olds) != len(news):
                check(name, False, 'MALFORMED: %d old text(s) and %d new'
                      % (len(olds), len(news)))
                continue
            cur, bad = src, None
            for i, (o, n) in enumerate(zip(olds, news)):
                hits = cur.count(o.encode('utf-8'))
                if hits != 1:
                    bad = 'ANCHOR-%d in %s%s' % (
                        hits, rel, '' if len(olds) == 1 else ' (edit %d of %d)'
                        % (i + 1, len(olds)))
                    break
                cur = cur.replace(o.encode('utf-8'), n.encode('utf-8'), 1)
            if bad:
                check(name, False, bad)
                continue
            _write(wt, rel, cur)
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
