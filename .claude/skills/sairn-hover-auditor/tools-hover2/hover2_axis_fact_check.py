#!/usr/bin/env python
"""hover2_axis_fact_check.py -- converts part of the independence-grade
P (principal) axis assignment from a narrative assertion into a
deterministic, re-derivable check (item 8, batch K: non-LLM coverage
conversion of the 3 model-judgment-only verdicts named at seq657).

GOAL: "P=0, self-review" has been ASSERTED every batch from memory of
this platform's own structure. This checks the one piece of it that is
actually mechanical: every commit in recent history, across every named
session (hover2 included), is authored under the SAME git identity --
a real, re-derivable fact supporting "one principal controls everyone",
not a judgment call about intent.

NON-GOALS: this does NOT derive S (substrate). No file on this platform
mechanically states which model each build-agent session runs; CLAUDE.md
states a model-selection POLICY ("Sonnet 5 High" default), which is
evidence of intent, not a runtime fact this tool can check. S stays an
asserted judgment call, named here as NOT converted rather than silently
claimed solved.

This also does NOT decide what the finding of "one email" MEANS for the
P axis value -- that interpretation (same git identity implies the same
controlling principal) is stated once, in the docstring, as the proxy's
stated limit, not re-argued by the tool's output.

ALTERNATIVES CONSIDERED:
  1. Check `.claude/claims/*.json` for a "principal"/"org" field --
     rejected: no such field exists in the claim schema (verified by
     reading tools/sairn_claim.py's own write path first), so this would
     be inventing a signal that is not actually there.
  2. Ask each build agent to self-report its controlling principal --
     rejected: a self-report is exactly the self-narrative evidence this
     whole independence grade exists to grade LOW; using one to derive
     the grade would be circular.

Read-only against `git log`. Writes nothing.
"""
import argparse
import subprocess
import sys

KNOWN_FIXTURE_IDENTITIES = {'fx@example.invalid'}


def check(repo, n):
    out = subprocess.run(
        ['git', '-C', repo, 'log', '--format=%ae', '-%d' % n],
        capture_output=True, text=True, check=True).stdout
    emails = [e.strip() for e in out.splitlines() if e.strip()]
    if not emails:
        return {'ok': False, 'reason': 'no commits read'}
    real = [e for e in emails if e not in KNOWN_FIXTURE_IDENTITIES]
    fixture = [e for e in emails if e in KNOWN_FIXTURE_IDENTITIES]
    distinct_real = sorted(set(real))
    return {
        'ok': True,
        'n_checked': len(emails),
        'distinct_real_identities': distinct_real,
        'fixture_commits_excluded': len(fixture),
        'single_principal': len(distinct_real) == 1,
    }


def selftest():
    # Can't fabricate git history here without writing to a repo (out of
    # scope for a read-only tool's selftest); instead assert the
    # structural invariant the real run depends on using a constructed
    # email list, the same shape `check()`'s core logic consumes.
    def core(emails):
        real = [e for e in emails if e not in KNOWN_FIXTURE_IDENTITIES]
        return len(set(real)) == 1

    assert core(['a@x.com', 'a@x.com', 'fx@example.invalid']) is True, (
        'ablation: one real identity plus an excluded fixture must read single_principal=True')
    assert core(['a@x.com', 'b@x.com']) is False, (
        'ablation: two distinct real identities must read single_principal=False')
    print('SELFTEST PASS: single-identity-plus-fixture=True, two-distinct-identities=False')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default='.')
    ap.add_argument('--n', type=int, default=50)
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    r = check(args.repo, args.n)
    if not r['ok']:
        print('COULD NOT RUN: %s' % r['reason'])
        sys.exit(2)
    print('commits checked: %d' % r['n_checked'])
    print('fixture-identity commits excluded (named, not silently dropped): %d'
          % r['fixture_commits_excluded'])
    print('distinct REAL committer identities: %s' % r['distinct_real_identities'])
    print('P-axis proxy (same git identity across every checked commit): %s'
          % r['single_principal'])
    print('REMINDER, stated not re-argued: this is a proxy for "same principal '
          'controls everyone", not a formal proof of session-dispatch control. '
          'S (substrate) is NOT checked here -- no mechanical runtime-model fact '
          'exists on this platform to derive it from.')
    sys.exit(0 if r['single_principal'] else 1)


if __name__ == '__main__':
    main()
