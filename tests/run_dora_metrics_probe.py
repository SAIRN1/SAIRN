"""Control for tools/dora_metrics.py.

Run: python tests/run_dora_metrics_probe.py

The self-check classifies synthetic commits. This checks the tool against the
REAL history a different way -- `git log --name-only` parsed here independently
-- and pins the three places a DORA number quietly becomes flattering:

  * counting every commit as a deployment, which turns a worklog into a release;
  * reporting a trunk-topology lead time as an elite result;
  * reporting a change failure rate without the coverage it was computed over.

Each has its own arm, and each arm fails if the guard is removed.
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import dora_metrics as D                                         # noqa: E402

CONTROLS_FOR = ['dora_metrics.py']

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


commits = D.git_log(30)
print('dora control -- %d commit(s) in the last 30 days\n' % len(commits))
check('git history is readable at all', len(commits) > 0, len(commits))

# ── 1. THE DEPLOYABLE SPLIT, RE-DERIVED INDEPENDENTLY ──────────────────────
# A second parse of git, and a deliberately simpler rule: a commit is
# deployable if ANY path is a root .html, an api/ file or a sql/ file. If the
# tool's classifier drifted, the two counts move apart.
raw = subprocess.run(['git', 'log', '--since=30 days ago', '--format=%H',
                      '--name-only'], cwd=REPO, capture_output=True, text=True,
                     encoding='utf-8', errors='replace').stdout
blocks, cur = [], None
for line in raw.split('\n'):
    line = line.strip()
    if not line:
        continue
    if len(line) == 40 and all(c in '0123456789abcdef' for c in line):
        cur = []
        blocks.append(cur)
    elif cur is not None:
        cur.append(line)


def mine_deployable(paths):
    for p in paths:
        if p.startswith(('docs/', 'tests/', 'tools/', '.claude/', '.github/')):
            continue
        if p.startswith(('api/', 'sql/')) or p.endswith(('.html', '.js')) \
                or p == 'vercel.json':
            return True
    return False


mine = sum(1 for b in blocks if mine_deployable(b))
theirs = sum(1 for c in commits if D.deployable(c[3]))
check('an independent parse of git agrees on the deployable count',
      abs(mine - theirs) <= 1, '%d mine vs %d theirs' % (mine, theirs))
check('...and the split is REAL -- not every commit is deployable',
      theirs < len(commits), '%d of %d' % (theirs, len(commits)))
check('...and it is not zero either, which would mean the classifier matches '
      'nothing', theirs > 0, theirs)

# ── 2. THE THREE FLATTERING FAILURE MODES, EACH WITH ITS OWN ARM ───────────
p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'dora_metrics.py'),
                    '--json'], capture_output=True, text=True, encoding='utf-8',
                   errors='replace', cwd=REPO,
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
doc = json.loads(p.stdout)

check('deployment frequency is reported BOTH ways, not just the large one',
      doc['commits_total'] > doc['commits_deployable'] > 0,
      (doc['commits_total'], doc['commits_deployable']))
check('lead time is marked NOT MEANINGFUL on this topology',
      doc['lead_time']['meaningful'] is False, doc['lead_time'])
check('...and it carries the reason, so the caveat travels with the number',
      len(doc['lead_time'].get('why_not') or '') > 60, doc['lead_time'])

cfr = doc['change_failure_rate']
check('the change failure rate carries the COVERAGE it was computed over',
      'injection_coverage' in cfr and len(cfr.get('coverage_note') or '') > 60,
      cfr)
check('...and that coverage is honest about being partial today',
      0.0 <= cfr['injection_coverage'] < 1.0, cfr['injection_coverage'])
check('the fix-commit ratio is present and NOT called the change failure rate',
      'NOT the change failure rate' in doc['fix_commit_proxy']['name'],
      doc['fix_commit_proxy'].get('name'))
check('...and it is a different number from the CFR, or one of them is wrong',
      abs(doc['fix_commit_proxy']['ratio_over_all_commits']
          - cfr.get('rate_over_deployable', -1)) > 1e-6,
      (doc['fix_commit_proxy']['ratio_over_all_commits'],
       cfr.get('rate_over_deployable')))

ttr = doc['time_to_restore']
check('time to restore reports its own n beside the median',
      ('n' in ttr and ('median_days' in ttr or 'could_not_run' in ttr)), ttr)

# ── 3. NO BENCHMARK BAND ANYWHERE ──────────────────────────────────────────
# The elite/high/medium/low bands were fitted to a survey population this
# platform is not in, and printing one is the single most flattering thing this
# tool could do.
text = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'dora_metrics.py')],
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace', cwd=REPO,
                      env=dict(os.environ, PYTHONIOENCODING='utf-8',
                               PYTHONUTF8='1')).stdout
low = text.lower()
check('the output never claims an ELITE / HIGH / MEDIUM / LOW band',
      not any(('%s performer' % w) in low or ('band: %s' % w) in low
              for w in ('elite', 'high', 'medium', 'low')),
      [w for w in ('elite', 'high', 'medium', 'low') if ('%s performer' % w) in low])
check('...and it says WHY no band is printed, rather than just omitting one',
      'NO BENCHMARK BAND IS PRINTED' in text, text[-300:])

# ── 4. THE CLASSIFIER CAN BE WRONG IN BOTH DIRECTIONS ──────────────────────
check('a commit touching only a worklog is not a deployment',
      not D.deployable(['SAIRN-ACTIVE-WORK-fourth.md']))
check('a commit touching a real app IS a deployment',
      D.deployable(['sairndental.html']))
check('a mixed commit counts once, as deployable',
      D.deployable(['docs/a.md', 'sairndental.html']))

# ── ADDED 2026-09-16 BY THIS TOOL'S FIRST ARTICLE INSPECTION ────────────────
# Two claims in the header had no arm. Both are mechanically checkable, so
# neither is a `cannot-test` -- they were simply unverified, which is the state
# FAI exists to surface.
import io as _io                                                 # noqa: E402

_SRC = _io.open(os.path.join(REPO, 'tools', 'dora_metrics.py'), encoding='utf-8').read()

# CLAIM: exit 2 when it could not run. Every exit-code arm above tests 0 and 1.
_saved_log = D.git_log
try:
    D.git_log = lambda *a, **k: []
    check('CLAIM "exit 2 when a metric could not be computed at all": no git '
          'history is COULD NOT RUN, never an empty-but-clean report',
          D.main(['--quiet']) == 2, 'expected exit 2')
finally:
    D.git_log = _saved_log

# CLAIM: REPORT ONLY. Stated in the header and enforced nowhere until now.
sys.path.insert(0, os.path.join(REPO, 'tools'))
import report_only_checks as _ROC                                # noqa: E402
_RUNNER = [x['tool'] if isinstance(x, dict) else x[0] for x in _ROC.REGISTRY]
check('CLAIM "report only": dora_metrics.py is NOT in the report-only RUNNER registry',
      'dora_metrics.py' not in _RUNNER, _RUNNER[:4])
check('...and IS recorded as a deliberate NOT-PROMOTED decision',
      'dora_metrics.py' in [x[0] for x in _ROC.NOT_PROMOTED])
_GATE = _io.open(os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py'),
                 encoding='utf-8', errors='replace').read()
check('...and the push gate does not invoke it',
      'dora_metrics' not in _GATE)

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
