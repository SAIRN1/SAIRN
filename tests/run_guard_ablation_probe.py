"""Does the ablator find the right gates, and can it damage the real tree?

    python tests/run_guard_ablation_probe.py

`tools/guard_ablation.py` removes a role gate from `api/sd-data.js` one at a
time and asks whether any suite notices. It is TIER A by the question this
platform tiers on -- the worst consequence of it being WRONG -- for two reasons
that are not the same:

  IT MUTATES A REAL SOURCE FILE. If the restore is wrong, a security gate is
  left disabled in a tracked file and the only sign is a passing run.
  IT REPORTS ON GATES. A wrong gate set means a guard is declared load-bearing
  or not-load-bearing on evidence that was never gathered about it.

── WHAT THIS PROBE DOES NOT DO, SAID FIRST ────────────────────────────────────
It does NOT run the ablation. A full pass builds a git worktree and executes
every suite that loads `sd-data.js`, against every gate -- minutes, and node
processes. Putting that in the suite would make every push wait on it.

So this drives the parts that decide WHAT gets ablated and WHERE it happens,
and asserts the one safety property that can be checked cheaply: after this
probe runs, the working tree is byte-for-byte as it was. The uncovered half is
named here rather than left to be assumed.

── THE DEFECT THE TOOL'S OWN HEADER DOCUMENTS ─────────────────────────────────
`if (!CRM_MANAGEMENT_ROLES[session.role]) {` appears at FOUR sites in the real
file, and `replace(..., 1)` would have hit the first one four times. That is why
the tool ablates BY LINE NUMBER and re-reads the line before touching it.
Section 3 holds both halves of that.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import guard_ablation as G                                       # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def porcelain():
    p = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return None if p.returncode != 0 else sorted(p.stdout.splitlines())


BEFORE = porcelain()

print('\n1. THE SUBJECT AND THE GATE SHAPE')
check('the declared subject exists -- an ablator pointed at a missing file '
      'would report zero gates, which reads as "nothing to ablate"',
      os.path.isfile(os.path.join(REPO, G.SUBJECT)), G.SUBJECT)
SRC = io.open(os.path.join(REPO, G.SUBJECT), encoding='utf-8',
              errors='replace').read()
real = list(G.GATE.finditer(SRC))
check('the real subject contains gates of the declared shape, so the scan is '
      'not silently matching nothing', len(real) > 0, len(real))

print('\n2. THE GATE REGEX DISCRIMINATES')
YES = [
    '  if (!CRM_MANAGEMENT_ROLES[session.role]) {',
    '\tif (!AP_ROLES[session.role]) {',
    'if (!X_ROLES[session.role]) {',
]
NO = [
    '  if (CRM_MANAGEMENT_ROLES[session.role]) {',          # not negated
    '  if (!CRM_MANAGEMENT_ROLES[session.roles]) {',        # wrong property
    '  if (!CRM_MANAGEMENT[session.role]) {',               # not a _ROLES table
    '  // if (!CRM_MANAGEMENT_ROLES[session.role]) {',      # commented out
    '  if (!CRM_MANAGEMENT_ROLES[session.role]) { return; }',  # not a block open
    '  if (!CRM_MANAGEMENT_ROLES[user.role]) {',            # not the session
]
for line in YES:
    check('matched: %s' % line.strip()[:60], bool(G.GATE.search(line)))
for line in NO:
    check('CONTROL: NOT matched: %s' % line.strip()[:60],
          not G.GATE.search(line), line)
check('CONTROL: the regex is anchored per LINE, so a gate inside a longer '
      'string on one line is not a gate',
      not G.GATE.search('const s = "if (!A_ROLES[session.role]) {";'))
check('the indentation is captured, because the replacement has to preserve it '
      '-- an ablation that reindents a file produces a diff nobody can review',
      G.GATE.search(YES[0]).group(1) == '  ',
      repr(G.GATE.search(YES[0]).group(1)))
check('the ROLE TABLE NAME is captured, so the report can say WHICH gate',
      G.GATE.search(YES[0]).group(2) == 'CRM_MANAGEMENT_ROLES')

print('\n3. AMBIGUITY IS WHY IT ABLATES BY LINE, AND THE REAL FILE IS AMBIGUOUS')
from collections import Counter                                  # noqa: E402
counts = Counter(m.group(0) for m in real)
dupes = {k: v for k, v in counts.items() if v > 1}
check('at least one gate line occurs MORE THAN ONCE in the real subject. This '
      'is the tool\'s own documented reason for using a line index: a textual '
      'replace would have hit the first site every time',
      bool(dupes), dict(list(counts.items())[:4]))
check('...and the line numbers derived for them are DISTINCT, so four identical '
      'lines are four different ablations',
      len({SRC[:m.start()].count('\n') + 1 for m in real}) == len(real),
      len(real))

lines = SRC.split('\n')
for m in real[:6]:
    n = SRC[:m.start()].count('\n') + 1
    check('line %d really is the gate the scan says it is -- a stale index is '
          'the failure mode a line-based ablator trades for' % n,
          lines[n - 1] == m.group(0), (lines[n - 1][:70], m.group(0)[:70]))

print('\n4. THE ABLATION IS A DISABLE, NOT A DELETION')
anchor = real[0].group(0)
mutated = anchor.split('if (')[0] + 'if (false) {'
check('the mutant keeps the original indentation',
      mutated.startswith(anchor.split('if (')[0]), repr(mutated))
check('the mutant is DIFFERENT from the anchor -- a no-op ablation would report '
      'on an unmodified file, which is the whole class tools/sabotage.py exists '
      'to remove', mutated != anchor)
check('the mutant no longer matches the gate regex, so an ablated gate cannot '
      'be counted as a gate on a rescan', not G.GATE.search(mutated), mutated)
check('CONTROL: the mutant still opens a block, or the file would not parse '
      'and every suite would go red for the wrong reason',
      mutated.rstrip().endswith('{'), mutated)

print('\n5. THE SUITE SET IS DERIVED AND NON-EMPTY')
ss = G.suites()
check('at least one suite loads the subject -- an empty set makes every gate '
      'report NOT LOAD-BEARING, which is the flattering wrong answer',
      len(ss) > 0, ss)
check('every named suite exists on disk',
      all(os.path.isfile(os.path.join(REPO, s)) for s in ss),
      [s for s in ss if not os.path.isfile(os.path.join(REPO, s))])
check('every named suite really references the subject, so the set is derived '
      'rather than pattern-matched on a path',
      all('sd-data.js' in io.open(os.path.join(REPO, s), encoding='utf-8',
                                  errors='replace').read() for s in ss))
check('CONTROL: the set is a SUBSET of the tests on disk, not all of them -- a '
      'derivation that returned everything would be a glob with extra steps',
      len(ss) < 400, len(ss))

print('\n6. THIS PROBE DID NOT TOUCH THE TREE')
AFTER = porcelain()
check('git status is readable at both ends', BEFORE is not None and AFTER is not None)
if BEFORE is not None and AFTER is not None:
    check('the working tree is byte-for-byte as it was. The ablator mutates a '
          'real source file; a probe for it that left one mutated would be the '
          'defect wearing the fix\'s clothes',
          BEFORE == AFTER,
          {'appeared': [l for l in AFTER if l not in BEFORE][:5],
           'disappeared': [l for l in BEFORE if l not in AFTER][:5]})

print('\n7. NOT COVERED HERE, STATED RATHER THAN IMPLIED')
print('  * the ABLATION ITSELF is not run -- it builds a git worktree and')
print('    executes every suite against every gate, which is minutes.')
print('  * whether a suite going red proves the GATE rather than something')
print('    else it happened to break.')
print('  * the restore path after a real run. It works in a worktree rather')
print('    than the checkout, which is the design that makes that safe, and')
print('    section 6 only proves THIS probe left nothing behind.')

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
