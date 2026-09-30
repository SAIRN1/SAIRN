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
    for fn in ('push_retry.py', 'defect_register.py', 'master_plan.py',
               'traceability_matrix.py', 'tooling_inventory.py'):
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

print('')
print('%d passed, %d failed' % (len(PASS), len(FAIL)))
for f in FAIL:
    print('  FAILED: %s' % f)
sys.exit(1 if FAIL else 0)
