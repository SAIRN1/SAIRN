"""Does the rewrite map still describe the repo, and does every chain converge?

WRITTEN BEFORE THE TOOL. Every arm was run against a missing
tools/rewrite_convergence_map.py first and every one failed.

THE SUBJECT IS A REAL LIVELOCK, NOT A HYPOTHETICAL. On 2026-09-29 nine
consecutive commits in one branch did nothing but re-seat register shas:

  1. the push loop rebases;
  2. .githooks/post-rewrite re-seats the register onto the rewritten shas,
     writes the file, and CORRECTLY refuses to commit on anyone's behalf --
     leaving the tree dirty;
  3. the regenerate step stages only the three GENERATED docs, so the register
     stays dirty;
  4. amend_safety() is right to refuse a dirty tree, the push is blocked, the
     loop rebases again, and step 2 repeats.

NOTHING IN THAT CHAIN IS WRONG ON ITS OWN, which is why reading each part in
isolation found nothing for nine commits. Only the closed loop is wrong. So the
check has to be over the CHAIN, and that is what --simulate is.

── THE ARMS ────────────────────────────────────────────────────────────────
B1  --verify on the real repo                        -> anchors resolve, exit 0
B2  an anchor that no longer appears                 -> exit 2 COULD NOT RUN,
    never 0: the map's claim is no longer checkable
B3  an anchor that appears MORE THAN ONCE            -> also refused; an
    ambiguous anchor is not evidence
B4  a hook on disk that the map does not name        -> exit 1; the map going
    stale silently is the failure mode of every map
B5  --simulate on the real chain                     -> every start state
    reaches a push or a fixed point within N steps
B6  KNOWN-BAD CONTROL: the fold-in step ablated      -> MUST report
    NON-CONVERGENT. This reconstructs the nine-commit livelock exactly; if the
    simulation still passes with the fix removed, it is asserting nothing.
B7  KNOWN-BAD CONTROL: an actor whose own write
    re-triggers it                                   -> MUST report
    NON-CONVERGENT
B8  every actor declares self_retrigger explicitly   -> an actor with the
    field absent or empty is a claim nobody made

B6 IS THE ONLY ARM THAT PROVES THE OTHERS MEAN ANYTHING. A convergence check
run on already-converging code passes whether or not it can see divergence at
all. Per the twelfth cross-domain discipline: remove ONE named layer from
already-clean code and measure what that layer alone catches.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'rewrite_convergence_map.py')

PASS, FAIL = [], []


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append(name)
    print('%-4s %-64s %s' % ('ok' if ok else 'FAIL', name, detail))


def run(args, cwd=None):
    p = subprocess.run([sys.executable, TOOL] + args, cwd=cwd or REPO,
                       capture_output=True, text=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


if not os.path.isfile(TOOL):
    print('COULD NOT RUN -- tools/rewrite_convergence_map.py does not exist.')
    print('That is not a pass. Every arm below is unrun.')
    sys.exit(2)

# ── B1 ──────────────────────────────────────────────────────────────────────
rc, out = run(['--verify'])
check('B1 real-repo --verify: anchors resolve and coverage is complete',
      rc == 0, 'exit=%d' % rc)
if rc != 0:
    print(out)

# ── B2 / B3 / B4 -- a mirrored tree, so the real repo is never edited ───────
def mirror():
    d = tempfile.mkdtemp(prefix='rewrite_map_probe_')
    for sub in ('tools', '.githooks', 'docs'):
        src = os.path.join(REPO, sub)
        if os.path.isdir(src):
            os.makedirs(os.path.join(d, sub), exist_ok=True)
    shutil.copy2(TOOL, os.path.join(d, 'tools'))
    for fn in os.listdir(os.path.join(REPO, '.githooks')):
        shutil.copy2(os.path.join(REPO, '.githooks', fn),
                     os.path.join(d, '.githooks', fn))
    # EVERY declared actor's file, read off the map rather than listed here --
    # the list version went stale the moment --derive added two actors, and the
    # mirror arms failed for a reason that had nothing to do with what they
    # test. A fixture that names its subjects by hand is a fixture that breaks
    # when the subject list is the thing under test.
    import json as _json
    import subprocess as _sp
    _m = _json.loads(_sp.run([sys.executable, TOOL, '--map', '--json'],
                             cwd=REPO, capture_output=True, text=True).stdout)
    for _f in sorted(set(a['file'] for a in _m['actors'])):
        if _f.startswith('.githooks/'):
            continue
        _src = os.path.join(REPO, _f.replace('/', os.sep))
        if os.path.isfile(_src):
            os.makedirs(os.path.join(d, os.path.dirname(_f)), exist_ok=True)
            shutil.copy2(_src, os.path.join(d, _f.replace('/', os.sep)))
    for fn in ():
        p = os.path.join(REPO, 'tools', fn)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(d, 'tools', fn))
    return d


d = mirror()
try:
    rc, out = run(['--verify', '--root', d])
    check('B1b the mirror verifies before it is damaged', rc == 0, 'exit=%d' % rc)

    # B2 -- delete an anchor
    target = os.path.join(d, '.githooks', 'post-rewrite')
    src = io.open(target, encoding='utf-8', newline='').read()
    anchor = '--post-rewrite'
    assert anchor in src, 'the probe itself is out of date: %s not in the hook' % anchor
    io.open(target, 'w', encoding='utf-8', newline='').write(
        src.replace(anchor, '--REMOVED-BY-PROBE'))
    rc, out = run(['--verify', '--root', d])
    check('B2 an anchor that no longer appears is exit 2 COULD NOT RUN',
          rc == 2, 'exit=%d' % rc)

    # B3 -- make the anchor ambiguous
    io.open(target, 'w', encoding='utf-8', newline='').write(
        src + '\n# duplicate for the probe: ' + anchor + '\n')
    rc, out = run(['--verify', '--root', d])
    check('B3 an anchor appearing more than once is refused', rc == 2,
          'exit=%d' % rc)

    # restore, then B4 -- a hook the map does not name
    io.open(target, 'w', encoding='utf-8', newline='').write(src)
    io.open(os.path.join(d, '.githooks', 'post-checkout'), 'w',
            encoding='utf-8', newline='').write('#!/bin/sh\nexit 0\n')
    rc, out = run(['--verify', '--root', d])
    check('B4 a hook on disk the map does not name is exit 1', rc == 1,
          'exit=%d' % rc)
finally:
    shutil.rmtree(d, ignore_errors=True)

# ── B5 / B6 / B7 -- the simulation ──────────────────────────────────────────
rc, out = run(['--simulate'])
check('B5 every start state converges on the real chain', rc == 0,
      'exit=%d' % rc)
if rc != 0:
    print(out)

rc, out = run(['--simulate', '--without', 'fold_reseat'])
check('B6 KNOWN-BAD: ablating fold_reseat is NON-CONVERGENT',
      rc == 1 and 'NON-CONVERGENT' in out, 'exit=%d' % rc)

rc, out = run(['--simulate', '--inject-loop'])
check('B7 KNOWN-BAD: a self-retriggering actor is NON-CONVERGENT',
      rc == 1 and 'NON-CONVERGENT' in out, 'exit=%d' % rc)

# ── B8 -- every actor states whether its write re-triggers it ──────────────
rc, out = run(['--map', '--json'])
if rc != 0:
    check('B8 every actor declares self_retrigger', False, 'exit=%d' % rc)
else:
    try:
        m = json.loads(out)
        bad = [a['name'] for a in m['actors']
               if not a.get('self_retrigger') or not a.get('trigger')
               or not a.get('writes')]
        check('B8 every actor declares trigger, writes and self_retrigger',
              not bad, 'incomplete: %s' % (bad or 'none'))
    except ValueError as e:
        check('B8 every actor declares self_retrigger', False, 'bad JSON: %s' % e)



# ══ ITEM 7: A DECLARATION IS NOT A MEASUREMENT ════════════════════════════
# Arms B1-B8 above all take ACTORS as given. These do not.
print('')
print('E. the actor set, DERIVED from the repo rather than declared')

rc, out = run(['--derive'])
check('E1 --derive: nothing is derived that is neither declared nor exempted',
      rc == 0, 'exit=%d' % rc)
if rc != 0:
    print(out)
check('E2 --derive reads core.hooksPath rather than assuming .githooks',
      'core.hooksPath' in out, '')
check('E3 --derive prints BOTH directions of the difference',
      'DERIVED, NEITHER DECLARED' in out or 'UNACCOUNTED FOR' in out,
      'and DECLARED BUT NOT DERIVED: %s' % ('DECLARED BUT NOT DERIVED' in out))

# E4 -- THE KNOWN-BAD CONTROL FOR THE DERIVATION. An undeclared actor planted
# in a scratch tree must be caught. Without this, E1 passing means only that
# the repo happens to be clean, which is also what a derivation that found
# nothing would report.
d = mirror()
try:
    planted = os.path.join(d, 'tools', 'zz_undeclared_actor.py')
    io.open(planted, 'w', encoding='utf-8', newline='\n').write(
        'import subprocess\n'
        '# An actor nobody declared: it commits on THIS tree, and it builds no\n'
        '# sandbox, so clause 2 has to see it.\n'
        'def land():\n'
        "    subprocess.run(['git', 'add', '-A'])\n"
        "    subprocess.run(['git', 'commit', '-m', 'landed'])\n")
    rc, out = run(['--derive', '--root', d])
    check('E4 KNOWN-BAD: an undeclared actor in the tree FAILS the map check',
          rc == 1 and 'zz_undeclared_actor.py' in out, 'exit=%d' % rc)

    # E5 -- the other direction: a file that mutates only its OWN sandbox must
    # NOT be reported. That is the discriminator the first derivation lacked,
    # and without it the answer was 85 files instead of 15.
    sandboxed = os.path.join(d, 'tools', 'zz_sandbox_only.py')
    io.open(sandboxed, 'w', encoding='utf-8', newline='\n').write(
        'import subprocess, tempfile\n'
        'def fixture():\n'
        '    wt = tempfile.mkdtemp()\n'
        "    subprocess.run(['git', 'init', wt])\n"
        "    subprocess.run(['git', '-C', wt, 'add', '-A'])\n"
        "    subprocess.run(['git', '-C', wt, 'commit', '-m', 'fixture'])\n")
    os.remove(planted)
    rc, out = run(['--derive', '--root', d])
    check('E5 a file that mutates only its OWN sandbox is not an actor',
          'zz_sandbox_only.py' not in out, 'exit=%d' % rc)
finally:
    shutil.rmtree(d, ignore_errors=True)

print('')
print('F. every declared "does not re-trigger" is DRIVEN TWICE, not believed')
# A self_retrigger answer of NO is a claim about behaviour. For the three
# regenerators it is checkable directly and cheaply: run the actor, snapshot
# the bytes it wrote, run it again, and require the second run to change
# nothing. A generator that stamps a run time into its own output fails this,
# which is exactly the shape --simulate's --inject-loop control models.
import hashlib
import subprocess as _sub

REGENS = [(a['name'], a['file'], a['writes'])
          for a in json.loads(run(['--map', '--json'])[1])['actors']
          if a['kind'] == 'regenerator']
check('F0 the regenerators are read off the map, not listed here',
      len(REGENS) >= 3, '%d found' % len(REGENS))

for name, tool, writes in REGENS:
    target = None
    for tok in writes.replace(',', ' ').split():
        if '/' in tok and '.' in tok:
            target = tok.strip('.,')
            break
    if not target or not os.path.isfile(os.path.join(REPO, target)):
        check('F %s: target readable' % name, False,
              'could not resolve the written file from the map: %r' % writes)
        continue

    def digest():
        return hashlib.sha256(
            io.open(os.path.join(REPO, target), 'rb').read()).hexdigest()

    before = digest()
    r1 = _sub.run([sys.executable, os.path.join(REPO, tool)], cwd=REPO,
                  capture_output=True, text=True)
    once = digest()
    r2 = _sub.run([sys.executable, os.path.join(REPO, tool)], cwd=REPO,
                  capture_output=True, text=True)
    twice = digest()
    check('F %-26s second run changes nothing (%s)' % (name, target),
          r1.returncode == 0 and r2.returncode == 0 and once == twice,
          'exit=%d,%d  first-run-changed=%s' % (r1.returncode, r2.returncode,
                                                before != once))

print('')
print('%d passed, %d failed' % (len(PASS), len(FAIL)))
for f in FAIL:
    print('  FAILED: %s' % f)
sys.exit(1 if FAIL else 0)
