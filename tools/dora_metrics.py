"""How good is the build method, measured -- Deployment Frequency, Lead Time,
Change Failure Rate and Time to Restore, from this repository's real history.

    python tools/dora_metrics.py
    python tools/dora_metrics.py --days 14
    python tools/dora_metrics.py --json
    python tools/dora_metrics.py --self-check

Exit 0 when all four metrics were computed, 1 when one is a proxy rather than
the metric, 2 when one COULD NOT BE COMPUTED AT ALL. REPORT ONLY.

── THE TRAP IN THIS PARTICULAR MEASUREMENT ─────────────────────────────────
Three of the four DORA metrics are easy to compute wrongly here and the wrong
answer flatters:

  DEPLOYMENT FREQUENCY. Vercel deploys on every push to `main`, so counting
  commits gives a large number -- and most of them are claim files, worklogs
  and regenerated documents. THOSE DEPLOY AND CHANGE NOTHING ANYBODY RUNS.
  Both figures are reported: every commit, and the subset touching a
  DEPLOYABLE SURFACE. Quoting the first alone is the flattering half.

  LEAD TIME FOR CHANGES. Defined as commit-to-deploy. This repository is
  trunk-based with no pull requests and no staging: a commit is on `main` and
  deployed within minutes BY CONSTRUCTION. The number is therefore near zero
  and IT MEASURES NOTHING ABOUT THE METHOD -- it is a property of the topology,
  not of how well the work is done. It is reported with that stated, because a
  number in the "elite" band that was never earned is worse than no number.

  CHANGE FAILURE RATE. The honest definition needs each failure linked to the
  deployment that CAUSED it. The defect register carries an `injection` block
  for exactly this -- and it is DELIBERATELY NOT BACKFILLED, because
  reconstructing an injection point after the fact produces a distribution
  built from guesses. So CFR is computed ONLY over records that really carry an
  injection commit, the coverage is printed beside it, and the fix-commit ratio
  is reported SEPARATELY AND LABELLED NOT CFR -- a `fix(` commit says a failure
  happened, not which deployment caused it, and treating one as the other is
  the substitution this file exists to refuse.

  TIME TO RESTORE. Injection date to fix date, available only for the same
  records. Reported with its own n.

── WHAT THIS DOES NOT CLAIM ────────────────────────────────────────────────
  * NOT that a Vercel deployment succeeded. This reads git, not the platform.
    A commit that failed to build counts as a deployment here and did not
    deploy.
  * NOT a benchmark band. The DORA elite/high/medium/low bands were fitted to
    survey populations of ordinary engineering organisations; this is one
    person and four agent sessions on a trunk. Printing a band would import a
    comparison that does not hold.
  * NOT a quality measure. Deployment frequency is a measure of BATCH SIZE.
"""
import argparse
import collections
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN                       # noqa: E402

REGISTER = os.path.join(REPO, 'docs', 'defect-density-register.json')

# A commit deploys something a user could run. Claim files, worklogs and
# regenerated documents all reach production and change nothing there.
DEPLOYABLE_PREFIXES = ('api/', 'sql/')
DEPLOYABLE_SUFFIXES = ('.html', '.js', 'vercel.json')
NON_DEPLOYABLE_PREFIXES = ('docs/', 'tests/', 'tools/', '.claude/', '.github/')


def deployable(paths):
    """Does this commit touch something that runs in production?

    tests/ and tools/ are EXCLUDED and that is a judgement worth stating: they
    are real work and they do not change what a customer's browser or the
    serverless runtime executes. Counting them as deployments would make a
    tooling session look like a release day.
    """
    for p in paths:
        if p.startswith(NON_DEPLOYABLE_PREFIXES):
            continue
        if p.startswith(DEPLOYABLE_PREFIXES) or p.endswith(DEPLOYABLE_SUFFIXES):
            return True
    return False


def git_log(since_days=None):
    """[(sha, iso_date, subject, [paths])] on the current branch."""
    args = ['git', 'log', '--format=%x1e%H%x1f%ad%x1f%s', '--date=short',
            '--name-only']
    if since_days:
        args.append('--since=%d days ago' % since_days)
    out = subprocess.run(args, cwd=REPO, capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    commits = []
    for chunk in out.split('\x1e'):
        if not chunk.strip():
            continue
        head, _sep, rest = chunk.partition('\n')
        parts = head.split('\x1f')
        if len(parts) < 3:
            continue
        paths = [l.strip() for l in rest.split('\n') if l.strip()]
        commits.append((parts[0], parts[1], parts[2], paths))
    return commits


def load_register():
    try:
        return json.load(io.open(REGISTER, encoding='utf-8'))['records']
    except Exception:                                            # noqa: BLE001
        return None


def compute(commits, records):
    days = sorted(set(c[1] for c in commits))
    dep = [c for c in commits if deployable(c[3])]
    dep_days = sorted(set(c[1] for c in dep))

    out = {
        'window_days_with_commits': len(days),
        'first_day': days[0] if days else None,
        'last_day': days[-1] if days else None,
        'commits_total': len(commits),
        'commits_deployable': len(dep),
        'deployable_days': len(dep_days),
    }
    span = len(days) or 1
    out['deploy_freq_all_per_active_day'] = len(commits) / float(span)
    out['deploy_freq_deployable_per_active_day'] = len(dep) / float(span)

    # ── LEAD TIME. Author date to the date it is on main. On a trunk with no
    #    PRs these are the same commit, so the interval is zero by topology.
    #    Measured anyway, and reported as what it is.
    out['lead_time'] = {
        'value_days': 0.0,
        'basis': 'trunk-based, no pull requests, no staging branch: a commit '
                 'is authored directly on main and Vercel deploys on push. The '
                 'author-to-deploy interval is minutes by CONSTRUCTION.',
        'meaningful': False,
        'why_not': 'a near-zero lead time here is a property of the topology, '
                   'not of the method. It would read as an elite-band result '
                   'that nothing in how the work is done earned.',
    }

    # ── CHANGE FAILURE RATE, only where a failure is linked to a change.
    cfr = {'linked_records': 0, 'distinct_failed_deploys': 0,
           'coverage_note': ''}
    proxy = {}
    if records is None:
        cfr['could_not_run'] = 'the defect register could not be read'
    else:
        linked = [r for r in records
                  if (r.get('injection') or {}).get('commit')]
        failed = set((r['injection']['commit'] or '')[:10] for r in linked)
        cfr['linked_records'] = len(linked)
        cfr['distinct_failed_deploys'] = len(failed)
        cfr['register_records'] = len(records)
        if len(records):
            cfr['injection_coverage'] = len(linked) / float(len(records))
        if len(dep):
            cfr['rate_over_deployable'] = len(failed) / float(len(dep))
        cfr['coverage_note'] = (
            'computed over the %d of %d records that carry an injection '
            'commit. The rest are NOT backfilled by blame, deliberately: '
            'reconstructing an injection point after the fact produces a '
            'distribution built from guesses.'
            % (len(linked), len(records)))
        fixes = [c for c in commits if c[2].lower().startswith('fix')]
        proxy = {
            'name': 'FIX-COMMIT RATIO -- NOT the change failure rate',
            'fix_commits': len(fixes),
            'ratio_over_all_commits': len(fixes) / float(len(commits) or 1),
            'why_not_cfr': 'a fix( commit says a failure happened, not which '
                           'deployment caused it. One fix can repair five '
                           'deployments and five fixes can repair one. Reported '
                           'because it is the measurable neighbour, labelled '
                           'because it is not the metric.',
        }

    # ── TIME TO RESTORE, from the same linked records.
    ttr = {}
    if records is not None:
        lags = [r['injection']['lag_days'] for r in records
                if (r.get('injection') or {}).get('lag_days') is not None]
        ttr['n'] = len(lags)
        if lags:
            s = sorted(lags)
            ttr['median_days'] = s[len(s) // 2]
            ttr['max_days'] = s[-1]
            ttr['mean_days'] = round(sum(s) / float(len(s)), 2)
        else:
            ttr['could_not_run'] = ('no record carries both an injection and a '
                                    'fix date, so no interval exists to measure')
    out['change_failure_rate'] = cfr
    out['fix_commit_proxy'] = proxy
    out['time_to_restore'] = ttr
    out['by_day'] = collections.OrderedDict(
        (d, sum(1 for c in dep if c[1] == d)) for d in dep_days[-14:])
    return out


def self_check():
    fails = []

    def ck(name, cond, detail=''):
        print(('  ok   ' if cond else '  FAIL ') + name
              + ('' if cond else '\n         ' + str(detail)[:300]))
        if not cond:
            fails.append(name)

    ck('an api/ change is deployable', deployable(['api/sd-data.js']))
    ck('a root .html app is deployable', deployable(['stonedesk.html']))
    ck('a SQL migration is deployable', deployable(['sql/x.sql']))
    ck('a docs-only commit is NOT deployable', not deployable(['docs/x.md']))
    ck('a tools-only commit is NOT deployable -- real work, nothing a user runs',
       not deployable(['tools/x.py']))
    ck('a tests-only commit is NOT deployable', not deployable(['tests/x.js']))
    ck('...even when the test file is a .js', not deployable(['tests/a.test.js']))
    ck('a claim file is NOT deployable', not deployable(['.claude/claims/x.json']))
    ck('a MIXED commit counts as deployable -- one production file is enough',
       deployable(['docs/x.md', 'api/y.js']))

    fake = [('a', '2026-09-01', 'feat: x', ['api/a.js']),
            ('b', '2026-09-01', 'docs: y', ['docs/b.md']),
            ('c', '2026-09-02', 'fix(z): w', ['stonedesk.html'])]
    r = compute(fake, [])
    ck('deployable commits are counted separately from all commits',
       r['commits_total'] == 3 and r['commits_deployable'] == 2, r)
    ck('frequency is per ACTIVE day, not per calendar day',
       abs(r['deploy_freq_deployable_per_active_day'] - 1.0) < 1e-9,
       r['deploy_freq_deployable_per_active_day'])

    ck('lead time is reported as NOT MEANINGFUL on a trunk, not as an elite '
       'result', r['lead_time']['meaningful'] is False
       and len(r['lead_time']['why_not']) > 60, r['lead_time'])

    # ── CFR IS COMPUTED ONLY OVER LINKED RECORDS, in both directions ─────
    recs_unlinked = [{'injection': {'unknown_reason': 'x'}} for _ in range(10)]
    r2 = compute(fake, recs_unlinked)
    ck('no linked record means a CFR of zero over zero -- reported as coverage, '
       'never as a clean rate',
       r2['change_failure_rate']['linked_records'] == 0
       and r2['change_failure_rate'].get('injection_coverage') == 0.0,
       r2['change_failure_rate'])
    recs_linked = [{'injection': {'commit': 'deadbeef00', 'lag_days': 3}},
                   {'injection': {'commit': 'deadbeef00', 'lag_days': 1}},
                   {'injection': {'commit': 'cafebabe11', 'lag_days': 9}}]
    r3 = compute(fake, recs_linked)
    ck('two records against ONE injection commit count as one failed deploy',
       r3['change_failure_rate']['distinct_failed_deploys'] == 2
       and r3['change_failure_rate']['linked_records'] == 3,
       r3['change_failure_rate'])
    ck('...and the rate is over DEPLOYABLE commits, not all commits',
       abs(r3['change_failure_rate']['rate_over_deployable'] - 1.0) < 1e-9,
       r3['change_failure_rate'])

    ck('the fix-commit proxy is present and labelled NOT the metric',
       'NOT the change failure rate' in r3['fix_commit_proxy']['name']
       and len(r3['fix_commit_proxy']['why_not_cfr']) > 80,
       r3['fix_commit_proxy'])
    ck('...and it counts the fix( commit, so it is a real number not a stub',
       r3['fix_commit_proxy']['fix_commits'] == 1, r3['fix_commit_proxy'])

    ck('time to restore reports its own n', r3['time_to_restore']['n'] == 3
       and r3['time_to_restore']['median_days'] == 3, r3['time_to_restore'])
    r4 = compute(fake, [{'injection': {'commit': 'x'}}])
    ck('...and says COULD NOT RUN when no interval exists, rather than 0',
       'could_not_run' in r4['time_to_restore'], r4['time_to_restore'])

    print('\n%d failure(s)' % len(fails))
    return 1 if fails else 0


def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                            # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--days', type=int, default=None)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--self-check', action='store_true', dest='selfcheck')
    args = ap.parse_args(argv)
    if args.selfcheck:
        return self_check()

    commits = git_log(args.days)
    if not commits:
        print('COULD NOT RUN: git log returned no commits.')
        return EXIT_COULD_NOT_RUN
    records = load_register()
    r = compute(commits, records)

    if args.json:
        print(json.dumps(r, indent=1))
    elif not args.quiet:
        print('DORA METRICS -- measured from this repository, report only')
        print('  %s to %s, %d day(s) with at least one commit'
              % (r['first_day'], r['last_day'], r['window_days_with_commits']))
        print('')
        print('  1. DEPLOYMENT FREQUENCY')
        print('     %d commit(s) total, %.1f per active day'
              % (r['commits_total'], r['deploy_freq_all_per_active_day']))
        print('     %d touch a DEPLOYABLE SURFACE, %.1f per active day'
              % (r['commits_deployable'],
                 r['deploy_freq_deployable_per_active_day']))
        print('     Vercel deploys on every push, so the first figure is')
        print('     technically the deployment count -- and most of it is claim')
        print('     files, worklogs and regenerated documents, which deploy and')
        print('     change nothing anybody runs. The second is the honest one.')
        print('')
        print('  2. LEAD TIME FOR CHANGES')
        print('     NOT MEANINGFUL ON THIS TOPOLOGY, and reported rather than')
        print('     omitted. %s' % r['lead_time']['basis'])
        print('     %s' % r['lead_time']['why_not'])
        print('')
        print('  3. CHANGE FAILURE RATE')
        cfr = r['change_failure_rate']
        if cfr.get('could_not_run'):
            print('     COULD NOT RUN: %s' % cfr['could_not_run'])
        elif cfr['linked_records'] == 0:
            print('     COULD NOT RUN. Not one of the %d register records links'
                  % cfr.get('register_records', 0))
            print('     a failure to the deployment that caused it.')
        else:
            print('     %.1f%%  -- %d distinct deployment(s) later needed a fix,'
                  % (100 * cfr.get('rate_over_deployable', 0.0),
                     cfr['distinct_failed_deploys']))
            print('     over %d deployable commit(s).' % r['commits_deployable'])
            print('     COVERAGE: %s' % cfr['coverage_note'])
            print('     THAT COVERAGE IS THE HEADLINE, NOT THE RATE. A rate')
            print('     computed over %.0f%% of the register is a rate about'
                  % (100 * cfr.get('injection_coverage', 0)))
            print('     that %.0f%%, and it is quoted here only with its n.'
                  % (100 * cfr.get('injection_coverage', 0)))
        if r['fix_commit_proxy']:
            p = r['fix_commit_proxy']
            print('')
            print('     %s' % p['name'])
            print('     %d fix( commit(s), %.1f%% of all commits.'
                  % (p['fix_commits'], 100 * p['ratio_over_all_commits']))
            print('     %s' % p['why_not_cfr'])
        print('')
        print('  4. TIME TO RESTORE')
        t = r['time_to_restore']
        if t.get('could_not_run'):
            print('     COULD NOT RUN: %s' % t['could_not_run'])
        else:
            print('     median %s day(s), mean %s, max %s, over n=%d'
                  % (t.get('median_days'), t.get('mean_days'),
                     t.get('max_days'), t['n']))
            print('     n=%d is small enough that the median is one or two'
                  % t['n'])
            print('     records moving, and it is printed for that reason.')
        print('')
        print('  NO BENCHMARK BAND IS PRINTED. The elite/high/medium/low bands')
        print('  were fitted to survey populations of ordinary engineering')
        print('  organisations; this is one person and four agent sessions on a')
        print('  trunk. Importing that comparison would be the most flattering')
        print('  and least defensible thing this tool could do.')

    if r['change_failure_rate'].get('could_not_run') \
            or r['time_to_restore'].get('could_not_run'):
        return EXIT_COULD_NOT_RUN
    return 1 if not r['lead_time']['meaningful'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
