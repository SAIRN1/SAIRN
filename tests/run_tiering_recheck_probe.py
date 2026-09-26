"""tools/tiering_recheck.py must FIND a recheck candidate, must NOT invent one,
and must refuse rather than pass when a source is missing.

    python tests/run_tiering_recheck_probe.py

WHY THE POSITIVE ARM IS THE ONE THAT NEEDS A FIXTURE. Against the real registers
the tool reports ZERO recheck candidates -- correctly, and for a structural reason
it prints as its headline: the review gate opens an obligation when TIER A code
changes, so 0 of 125 B/C rows have ever been reviewed and no review can surprise
anybody about one. A tool whose real-world output is an empty list has, by
construction, never been shown to be able to report anything. So the positive arm
is driven on a fixture where a B row HAS been reviewed, which is the state the
platform will reach the first time somebody reviews a B row.

Every arm builds a sandbox repo and runs the SHIPPING tool in it. The clone's own
registers are never written, which the closing arm asserts by bytes and mtime --
not by `git status`, because that reports a newly added file as dirty and would go
red on the commit that introduces one.
"""
CONTROLS_FOR = ['tiering_recheck.py']

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL_REL = os.path.join('tools', 'tiering_recheck.py')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def sandbox(tiers_rows, reviews, defects, owner):
    """A repo-shaped throwaway carrying only what the tool reads."""
    d = tempfile.mkdtemp(prefix='sairn-tiering-')
    os.makedirs(os.path.join(d, 'tools'))
    os.makedirs(os.path.join(d, 'docs'))
    os.makedirs(os.path.join(d, 'api', '_resources'))
    shutil.copy(os.path.join(REPO, TOOL_REL), os.path.join(d, TOOL_REL))
    hdr = ('| Resource | Integrity | Confidentiality | I harm | C harm | Evidence |\n'
           '|---|---|---|---|---|---|\n')
    body = ''.join('| `%s` | **%s** | **%s** | x | y | z |\n' % (r, i, c)
                   for r, i, c in tiers_rows)
    io.open(os.path.join(d, 'docs', 'CRITICALITY-TIERS.md'), 'w',
            encoding='utf-8', newline='\n').write(hdr + body)
    io.open(os.path.join(d, 'docs', 'tier-a-reviews.json'), 'w',
            encoding='utf-8', newline='\n').write(json.dumps({'records': reviews}))
    io.open(os.path.join(d, 'docs', 'defect-density-register.json'), 'w',
            encoding='utf-8', newline='\n').write(json.dumps({'records': defects}))
    io.open(os.path.join(d, 'api', '_resources', 'index.js'), 'w',
            encoding='utf-8', newline='\n').write(
        'module.exports = { OWNER_BY_RESOURCE: %s };\n' % json.dumps(owner))
    return d


def run(d, *args):
    r = subprocess.run([sys.executable, TOOL_REL] + list(args), cwd=d,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


SEVERE = {'app': 'demoapp', 'detection_method': 'independent-review',
          'severity': 'high', 'summary': 'a real high-severity finding'}
MINOR = {'app': 'demoapp', 'detection_method': 'independent-review',
         'severity': 'low', 'summary': 'a cosmetic finding'}
OTHER = {'app': 'demoapp', 'detection_method': 'code-review',
         'severity': 'critical', 'summary': 'found by reading, not by review'}
OWNER = {'x_money': 'demoapp', 'x_notes': 'demoapp', 'x_audit': 'demoapp'}

# ---------------------------------------------------------------------------
print('1. THE POSITIVE -- a reviewed B row in a surprising app IS a candidate')
d = sandbox([('x_money', 'B', 'B'), ('x_audit', 'A', 'A')],
            [{'resources': ['x_money'], 'verdict': 'reviewed'}],
            [SEVERE], OWNER)
rc, out = run(d)
check('a B row that HAS been reviewed, in an app with a severe '
      'independent-review find, is a RECHECK candidate',
      'RECHECK CANDIDATES: 1' in out and 'x_money' in out, out[-400:])
check('...and --candidates exits 1 so a caller can branch on it',
      run(d, '--candidates')[0] == 1, 'exit=%s' % run(d, '--candidates')[0])
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n2. CONTROL -- the SAME row unreviewed is NOT a candidate')
# This is the arm that keeps the criterion honest. The first version of the tool
# required only the app signal and returned 95 undifferentiated candidates, every
# one with reviews=0. A claim that "the reviews found something the tier did not
# anticipate" requires the reviews to have looked AT THE ROW.
d = sandbox([('x_money', 'B', 'B'), ('x_audit', 'A', 'A')], [], [SEVERE], OWNER)
rc, out = run(d)
check('an UNREVIEWED B row in the same app is NOT a recheck candidate',
      'RECHECK CANDIDATES: 0' in out, out[-300:])
check('...it lands in the review-SCHEDULING bucket instead, which is a different '
      'finding and says so',
      'UNREVIEWED IN A SURPRISING APP: 1' in out, out[-400:])
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n3. CONTROL -- severity and detection_method both have to match')
d = sandbox([('x_money', 'B', 'B')],
            [{'resources': ['x_money'], 'verdict': 'reviewed'}],
            [MINOR], OWNER)
rc, out = run(d)
check('a LOW-severity independent-review find does not raise a candidate',
      'RECHECK CANDIDATES: 0' in out, out[-250:])
shutil.rmtree(d, ignore_errors=True)
d = sandbox([('x_money', 'B', 'B')],
            [{'resources': ['x_money'], 'verdict': 'reviewed'}],
            [OTHER], OWNER)
rc, out = run(d)
check('a CRITICAL find by a method other than independent-review does not '
      'raise one either -- this tool is about review surprise, not defects',
      'RECHECK CANDIDATES: 0' in out, out[-250:])
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n4. EARNING and UNEXAMINED are distinct, and neither is folded into a pass')
d = sandbox([('x_audit', 'A', 'A'), ('x_notes', 'B', 'B')],
            [{'resources': ['x_audit'], 'verdict': 'v1'},
             {'resources': ['x_audit'], 'verdict': 'v2'}],
            [], OWNER)
rc, out = run(d)
check('an A row reviewed twice with no severe find reads as EARNING ITS COST',
      'EARNING ITS COST: 1' in out and 'x_audit' in out, out[-400:])
check('a row with NO review and NO defect data is UNEXAMINED, a third state',
      'UNEXAMINED: 1' in out, out[-400:])
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n5. AN UNATTRIBUTED ROW IS A REGISTRY GAP, not a tier finding')
d = sandbox([('x_orphan', 'B', 'B')], [], [SEVERE], OWNER)   # not in OWNER
rc, out = run(d)
check('a tiered row absent from OWNER_BY_RESOURCE is reported UNATTRIBUTED',
      'UNATTRIBUTED: 1' in out and 'x_orphan' in out, out[-400:])
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n6. THE CORPUS SIZE IT REPORTS IS RECORDS, NOT RECORD-RESOURCE PAIRS')
# THIS ARM EXISTS BECAUSE THE TOOL GOT IT WRONG. It printed the SUM of the
# per-resource review counts and labelled it "review record(s)". One record naming
# twelve resources contributes twelve, so on the real register it announced 789
# reviews over a corpus of 167 -- a 4.7x overstatement, in the one direction that
# makes the tool look better founded than it is. Both numbers are useful and both
# are now labelled; neither may wear the other's name.
d = sandbox([('x_money', 'B', 'B'), ('x_notes', 'B', 'B'), ('x_audit', 'A', 'A')],
            [{'resources': ['x_money', 'x_notes', 'x_audit'], 'verdict': 'one pass'}],
            [], OWNER)
rc, out = run(d)
check('ONE review record naming three resources reports 1 record, not 3',
      '1 review record(s)' in out, out[:300])
check('...and reports the 3 pairs SEPARATELY, under their own name',
      '3 record-resource pair(s)' in out, out[:300])
check('...and never calls the pair count a review count -- the exact overstatement '
      'this tool shipped first', '3 review record(s)' not in out, out[:300])
shutil.rmtree(d, ignore_errors=True)
# And against the REAL register, computed here rather than hardcoded, so this arm
# cannot go stale as the corpus grows.
_rr = json.load(io.open(os.path.join(REPO, 'docs', 'tier-a-reviews.json'),
                        encoding='utf-8'))['records']
_pairs = sum(len(r.get('resources') or []) for r in _rr)
rc, out = run(REPO)
check('on the real register it reports the record count (%d), not the pair count '
      '(%d)' % (len(_rr), _pairs),
      ('%d review record(s)' % len(_rr)) in out
      and ('%d review record(s)' % _pairs) not in out, out[:300])
check('...and the two numbers really do differ, so the arm above is testing '
      'something', len(_rr) != _pairs, 'records == pairs; this arm proves nothing')

# ---------------------------------------------------------------------------
print('\n7. EVERY MISSING OR UNREADABLE SOURCE IS EXIT 2, NEVER 0')
d = sandbox([('x_money', 'B', 'B')], [], [SEVERE], OWNER)
for rel, how in (('docs/tier-a-reviews.json', 'deleted'),
                 ('docs/defect-density-register.json', 'deleted'),
                 ('docs/CRITICALITY-TIERS.md', 'deleted')):
    p = os.path.join(d, rel.replace('/', os.sep))
    keep = io.open(p, 'rb').read()
    os.remove(p)
    rc, out = run(d)
    check('%s %s -> exit 2 COULD NOT TELL' % (rel, how),
          rc == 2 and 'COULD NOT TELL' in out, 'exit=%s' % rc)
    io.open(p, 'wb').write(keep)
p = os.path.join(d, 'docs', 'tier-a-reviews.json')
keep = io.open(p, 'rb').read()
io.open(p, 'w', encoding='utf-8', newline='\n').write('{ not json')
rc, out = run(d)
check('an unparseable review file -> exit 2, and it says nothing was correlated',
      rc == 2 and 'will not parse' in out, 'exit=%s' % rc)
io.open(p, 'wb').write(keep)

# THE ROW ANCHOR MOVING IS NOT "no resources". A register whose format changed
# would otherwise report every row UNEXAMINED and exit 0 -- a clean run over
# nothing, which is the failure this whole class of tool keeps having.
io.open(os.path.join(d, 'docs', 'CRITICALITY-TIERS.md'), 'w',
        encoding='utf-8', newline='\n').write('| Resource |\n|---|\n| x_money |\n')
rc, out = run(d)
check('a register whose ROW ANCHOR no longer matches is exit 2, not a clean run '
      'over zero rows', rc == 2 and 'NOTHING was correlated' in out,
      'exit=%s :: %s' % (rc, out[-200:]))
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n8. AND THE REAL REGISTERS -- so the arms above are not a fixture dialect')
real = [os.path.join(REPO, 'docs', f) for f in
        ('CRITICALITY-TIERS.md', 'tier-a-reviews.json', 'defect-density-register.json')]
before = [(io.open(p, 'rb').read(), os.path.getmtime(p)) for p in real]
rc, out = run(REPO)
check('it runs against the shipping registers and exits 0', rc == 0, 'exit=%s' % rc)
check('...and leads with the structural finding rather than an empty list',
      'BLIND IN THE DIRECTION A RE-CHECK MOST NEEDS' in out, out[:300])
check('...and reports the real B/C review coverage, which is what makes RECHECK '
      'empty', 'Tier B/C' in out, out[:600])
after = [(io.open(p, 'rb').read(), os.path.getmtime(p)) for p in real]
check('IT WROTE NOTHING to any real register -- identical bytes AND unchanged '
      'mtimes, so a write-then-restore would fail this too', before == after,
      'a register was written')

shutil.rmtree(tempfile.mkdtemp(prefix='sairn-tiering-noop-'), ignore_errors=True)
print('\n%s  run_tiering_recheck_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
