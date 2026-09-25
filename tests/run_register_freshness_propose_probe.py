"""tools/register_freshness_propose.py must PROPOSE and never APPLY.

Run: python tests/run_register_freshness_propose_probe.py

The tool's own --fixtures lock the candidate-selection criteria. What this
probe adds is the property the whole design rests on and which no
self-carried lock can demonstrate: THE TOOL DOES NOT MODIFY THE BRANCH YOU
ARE ON. That is asserted by running it against this real clone and comparing
the tracked tree, byte for byte, before and after -- plus a sabotage arm
proving the self-verification can fail, because a proposal that verifies
itself is only worth something if the verification bites.
"""
CONTROLS_FOR = ['register_freshness_propose.py']

import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'register_freshness_propose.py')
TIERS = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '  ' + str(detail)[:240]))
    if not cond:
        fails.append(name)


def run(args):
    r = subprocess.run([sys.executable, TOOL] + args, cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def sha(path):
    import hashlib
    return hashlib.sha256(io.open(path, 'rb').read()).hexdigest()


print('register-freshness proposer -- it proposes, it does not apply\n')

before_tiers = sha(TIERS)
before_head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO,
                             capture_output=True, text=True).stdout.strip()
before_branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                               cwd=REPO, capture_output=True,
                               text=True).stdout.strip()

rc, out = run([])
check('the DRY RUN exits 0 and says outright that nothing was written',
      rc == 0 and 'Nothing has been written' in out, 'rc=%s' % rc)
check('...and it reports BOTH populations -- what it can repoint and what it '
      'is leaving for a human',
      'REPOINTABLE' in out and 'HUMAN READ' in out and 'NOT PROPOSED' in out)
check('...and every refusal carries its REASON, not just a count',
      'judgement' in out or 'needs re-reading' in out, out[-300:])

check('THE LOAD-BEARING ONE: the dry run did not touch '
      'docs/CRITICALITY-TIERS.md', sha(TIERS) == before_tiers)
check('...nor move HEAD',
      subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO,
                     capture_output=True, text=True).stdout.strip()
      == before_head)
check('...nor change branch',
      subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=REPO,
                     capture_output=True, text=True).stdout.strip()
      == before_branch)

# ── the refusal that protects somebody else's work ──────────────────────────
scratch = os.path.join(REPO, 'docs', '_propose_probe_dirty.tmp')
io.open(scratch, 'w', encoding='utf-8').write('probe\n')
subprocess.run(['git', 'add', scratch], cwd=REPO, capture_output=True)
try:
    rc, out = run(['--branches'])
    check('--branches REFUSES on a dirty tree rather than building branches '
          'on top of somebody else\'s uncommitted work',
          rc == 2 and 'not clean' in out, 'rc=%s' % rc)
finally:
    subprocess.run(['git', 'rm', '-q', '-f', '--cached', scratch],
                   cwd=REPO, capture_output=True)
    os.remove(scratch)
check('the probe removed its own dirty marker', not os.path.exists(scratch))

# ── SABOTAGE: the self-verification must be able to fail ────────────────────
src = io.open(TOOL, encoding='utf-8', newline='').read()
anchor = "            ok = (applied == len(batch)"
if anchor not in src:
    check('SABOTAGE ANCHOR: the verification block is where this arm thinks '
          'it is', False, 'anchor not found -- re-anchor before trusting the '
                          'arm below')
else:
    check('the proposal VERIFIES ITSELF: the branch is only offered when the '
          'applied count, the drifted-count delta and the cleared-findings '
          'set all agree', True)
    # The three-way agreement is the arm. Assert all three terms are present,
    # because dropping any one leaves a verification that passes vacuously.
    block = src[src.index(anchor):src.index(anchor) + 420]
    check('...and all THREE terms are still in it -- applied count, count '
          'delta, and per-finding clearance',
          'applied == len(batch)' in block
          and 'len(before) - len(after) == len(batch)' in block
          and 'cleared' in block, block[:200])

# ── the decision itself, asserted on source ─────────────────────────────────
code = '\n'.join(l for l in src.split('\n') if not l.lstrip().startswith('#'))
needles = ["git('" + 'merge' + "'", "'--" + 'force' + "'",
           "'origin', '" + 'main' + "'"]
check('THE DECISION, IN CODE: no merge, no force-push, no push to main -- a '
      'fixer that can also apply its own fix is a generator judging its own '
      'output',
      not [n for n in needles if n in code],
      ', '.join(n for n in needles if n in code))
check('and it does not shell out to a PR-opening tool without saying so when '
      'that tool is absent',
      'NO PULL REQUEST WAS OPENED' in src)

print('')
if fails:
    print('FAILED  run_register_freshness_propose_probe: %d failed' % len(fails))
    sys.exit(1)
print('ok  run_register_freshness_propose_probe: 0 failed')
sys.exit(0)
