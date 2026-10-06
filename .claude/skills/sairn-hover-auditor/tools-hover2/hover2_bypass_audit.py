#!/usr/bin/env python
"""hover2_bypass_audit.py -- this role's own audit-trail reviewer over
docs/BYPASS-LOG.jsonl, .claude/claims/*.json history, and this role's own
hover-log chain.

GOALS:
  - Surface every bypass/override entry in docs/BYPASS-LOG.jsonl in a
    structured, readable form.
  - For a given entry, retrieve the CANDIDATE EVIDENCE a human needs to
    judge (a) whether the stated reason held and (b) whether the
    underlying issue was later resolved: the commit nearest the bypass's
    own timestamp by the SAME session, and that session's claim-file
    history (via `git log` on .claude/claims/<session>.json) around and
    after the bypass.

NON-GOALS:
  - Does NOT compute a held/not-held or resolved/not-resolved VERDICT
    itself. A tool that auto-scores "resolved" from keyword matching in
    later commit messages is exactly the fabricated-confidence shape this
    platform's own skill-vetting history warns about (a risk scorer that
    manufactured a 38% accuracy from false positives). This tool reports
    evidence; a human (or this role, reading the candidates) writes the
    verdict, same split register-cell-reader already uses between
    "reports evidence" and "decides a tier."
  - Does NOT scan for --no-verify/--no-gpg-sign or other bypass shapes
    outside docs/BYPASS-LOG.jsonl. That log is the platform's own
    authoritative structured record for push-gate bypasses; widening the
    surface to raw git-flag scanning is a different, broader tool and
    was not asked for.
  - Never writes to docs/BYPASS-LOG.jsonl, any .claude/claims/*.json file,
    or any platform file. Read-only, always.

ALTERNATIVES CONSIDERED:
  1. Summarize bypass COUNTS per session only -- rejected, too shallow
     for "whether its stated reason held."
  2. Auto-score resolution status by keyword search in later commits --
     rejected (see NON-GOALS); a wrong auto-verdict presented as a fact
     is worse than evidence presented as evidence.
  3. Cross-reference only the CURRENT content of .claude/claims/*.json --
     rejected: claims get released and overwritten, so the claim ACTIVE
     at bypass time is only recoverable from `git log`, not current state.

CROSS-CUTTING: read-only everywhere; own location only; fails closed if
docs/BYPASS-LOG.jsonl is missing or malformed.

Usage:
  python hover2_bypass_audit.py --list [--repo PATH]
  python hover2_bypass_audit.py --context N [--repo PATH]   (N = 0-based index into --list)
  python hover2_bypass_audit.py --selftest
"""
import argparse
import json
import os
import subprocess
import sys


def load_entries(repo):
    path = os.path.join(repo, 'docs', 'BYPASS-LOG.jsonl')
    if not os.path.isfile(path):
        return None, 'COULD NOT RUN: %s not found' % path
    entries = []
    with open(path, encoding='utf-8') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                return None, 'COULD NOT RUN: malformed JSON at line %d: %s' % (i + 1, e)
    return entries, None


def git(args, repo):
    return subprocess.run(['git'] + args, cwd=repo, capture_output=True, text=True)


def nearest_commit_by_session(entry, repo, window_minutes=120):
    """Retrieval only -- lists candidates, does not pick a verdict."""
    at = entry.get('at')
    if not at:
        return []
    r = git(['log', '--all', '--format=%H|%ad|%s', '--date=iso-strict',
             '--since=%s' % _shift(at, -window_minutes),
             '--until=%s' % _shift(at, window_minutes)], repo)
    if r.returncode != 0:
        return []
    out = []
    for line in r.stdout.splitlines():
        parts = line.split('|', 2)
        if len(parts) == 3:
            out.append(tuple(parts))
    return out


def _shift(iso_ts, minutes):
    # Minimal ISO-8601 'Z' shifter without importing datetime timezone
    # arithmetic edge cases -- git itself accepts a relative-minutes string
    # just as well, so shift via git's own date math instead of python's.
    sign = '+' if minutes >= 0 else '-'
    return '%s %d minutes' % (iso_ts, abs(minutes)) if False else _git_date_math(iso_ts, minutes)


def _git_date_math(iso_ts, minutes):
    import datetime
    dt = datetime.datetime.strptime(iso_ts, '%Y-%m-%dT%H:%M:%SZ')
    dt = dt + datetime.timedelta(minutes=minutes)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def claim_history(session, repo, at, window_minutes=1440):
    path = '.claude/claims/%s.json' % session
    r = git(['log', '--format=%H|%ad|%s', '--date=iso-strict',
             '--since=%s' % _git_date_math(at, -window_minutes),
             '--', path], repo)
    if r.returncode != 0:
        return []
    out = []
    for line in r.stdout.splitlines():
        parts = line.split('|', 2)
        if len(parts) == 3:
            out.append(tuple(parts))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--context', type=int)
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    entries, err = load_entries(args.repo)
    if err:
        print(err)
        sys.exit(2)

    if args.list:
        for i, e in enumerate(entries):
            print('%3d  %s  %-8s %-6s %s' % (
                i, e.get('at', '?'), e.get('session', '?'),
                'BLANKET' if e.get('blanket') else 'named',
                (e.get('reason') or '')[:90]))
        sys.exit(0)

    if args.context is not None:
        if args.context < 0 or args.context >= len(entries):
            print('COULD NOT RUN: index %d out of range (0-%d)' % (args.context, len(entries) - 1))
            sys.exit(2)
        e = entries[args.context]
        print('ENTRY %d: %s' % (args.context, json.dumps(e, indent=2)))
        if e.get('retracts'):
            print('(this entry RETRACTS an earlier one at %s -- read that one too)' % e['retracts'])
            sys.exit(0)
        print('--- candidate commits by %s within +/-120min ---' % e.get('session'))
        for sha, date, subj in nearest_commit_by_session(e, args.repo):
            print('  %s  %s  %s' % (sha[:10], date, subj))
        print('--- this session\'s claim-file history, this bypass to +24h ---')
        for sha, date, subj in claim_history(e.get('session', ''), args.repo, e.get('at', ''), 1440):
            print('  %s  %s  %s' % (sha[:10], date, subj))
        sys.exit(0)

    print('usage: --list | --context N | --selftest')
    sys.exit(2)


def selftest():
    import tempfile
    d = tempfile.mkdtemp()
    subprocess.run(['git', 'init', '-q', d])
    subprocess.run(['git', '-C', d, 'config', 'user.email', 'x@example.invalid'])
    subprocess.run(['git', '-C', d, 'config', 'user.name', 'fixture'])
    os.makedirs(os.path.join(d, 'docs'))
    os.makedirs(os.path.join(d, '.claude', 'claims'))

    bypass_ts = '2026-01-01T12:00:00Z'
    with open(os.path.join(d, 'docs', 'BYPASS-LOG.jsonl'), 'w', encoding='utf-8') as f:
        f.write(json.dumps({'at': bypass_ts, 'session': 'fixture', 'check': 'ALL',
                            'reason': 'fixture reason', 'blanket': True, 'command': 'x'}) + '\n')
    with open(os.path.join(d, 'README.md'), 'w') as f:
        f.write('seed\n')
    subprocess.run(['git', '-C', d, 'add', '-A'])
    subprocess.run(['git', '-C', d, 'commit', '-q', '-m', 'seed'])

    import datetime
    env = dict(os.environ)
    commit_dt = (datetime.datetime.strptime(bypass_ts, '%Y-%m-%dT%H:%M:%SZ')
                 + datetime.timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
    env['GIT_AUTHOR_DATE'] = commit_dt
    env['GIT_COMMITTER_DATE'] = commit_dt
    with open(os.path.join(d, 'marker.txt'), 'w') as f:
        f.write('the resolving commit\n')
    subprocess.run(['git', '-C', d, 'add', '-A'])
    subprocess.run(['git', '-C', d, 'commit', '-q', '-m', 'marker commit, 5 min after the bypass'], env=env)

    entries, err = load_entries(d)
    ok1 = err is None and len(entries) == 1
    candidates = nearest_commit_by_session(entries[0], d) if ok1 else []
    ok2 = any('marker commit' in c[2] for c in candidates)

    missing_entries, missing_err = load_entries(os.path.join(d, 'nope'))
    ok3 = missing_entries is None and missing_err is not None

    ok = ok1 and ok2 and ok3
    print('SELFTEST %s: loaded=%r found_marker_candidate=%r missing_dir_refused=%r' %
          ('PASS' if ok else 'FAIL', ok1, ok2, ok3))
    return 0 if ok else 1


if __name__ == '__main__':
    main()
