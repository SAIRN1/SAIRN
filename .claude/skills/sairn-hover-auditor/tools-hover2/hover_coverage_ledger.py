#!/usr/bin/env python
"""hover_coverage_ledger.py (hover2's own independent build) -- of the
platform's review-shaped commits, which has this role's OWN self-log ever
actually cited.

Built from the CONTRACT in hover-interface-specs-2026-09-22.md #2, not from
hover1's source (different clone, no access, and copying would defeat the
point of two independently-coded tools). Where the contract names a real
trap already hit by hover1's own implementation, the fix is applied here
from the start rather than discovered the same way twice:

  * SHA matching is VARIABLE-LENGTH (6-40 hex chars) with PREFIX comparison
    in either direction -- never a fixed-width word-boundary regex, which
    silently produces zero matches against a full 40-char SHA (a
    homogeneous hex run has no internal \\b for a {7,10} anchor to land on).
  * "review-shaped commit" is split into two sub-shapes on the subject line,
    not treated as one bucket: a `chore(review): record ...` commit only
    BOOKS an obligation (nothing has been reviewed yet); a `review(...): ...`
    or `chore(review): discharge ...` commit is a REAL discharge. Only the
    second kind belongs in "uncovered and actionable" -- the first kind
    being uncovered is not a gap, it is a queue entry with no review yet.
  * Always fetches origin and reads origin/main, never local HEAD -- a
    second clone (this one) existing on an unfetched branch is exactly the
    scenario that makes a stale local view wrong, the same staleness fix
    already applied in sabotage_claim_verify.py this session.

WHAT "COVERED" MEANS, STATED RATHER THAN IMPLIED: a SHA token for the commit
appears somewhere in ANY entry's `ref` field in THIS role's own self-log.
That is "cited", not "independently re-driven to a real standard" -- a SHA
appearing in `ref` because it was read and discussed reads identically, to
this tool, to one that was reproduced with an original harness and a real
planted mutation. See --grade for the finer distinction, modelled on the
same SLSA-style levels this role built into sabotage_claim_verify.py
tonight, reused here because the contract names this exact undifferentiated-
trust problem as worth fixing rather than repeating silently a second time.

Run:
  python hover_coverage_ledger.py                  -- report, ungraded
  python hover_coverage_ledger.py --grade           -- SLSA-style levels on covered
  python hover_coverage_ledger.py --repo <path>     -- override repo discovery
  python hover_coverage_ledger.py --selftest        -- fixture-based self-check
"""
import json
import os
import re
import subprocess
import sys

GIT_TIMEOUT_FETCH = 60
GIT_TIMEOUT_LOCAL = 20

_KNOWN_CLONES = (
    # H2's own clone first -- this is H2's private copy of this tool, reading
    # H2's own self-log, and discover_repo() must default to auditing H2's own
    # working tree. Found 2026-10-05: with H1's clone listed first, a bare
    # `python hover_coverage_ledger.py` (no --repo) silently scanned H1's
    # clone's git history instead of this one. It produced the SAME numbers
    # today only because both clones happened to be at identical commits for
    # every review-shaped commit checked -- that is luck, not correctness, and
    # the day H1's clone is mid-pull, on a different branch, or simply behind,
    # this would silently report coverage against the wrong repository's
    # commit list with no error at all.
    'C:/Users/marsh/Documents/SAIRN-hover2',
    'C:/Users/marsh/Documents/SAIRN-hover',
)

SELF_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'hover-audit-log.jsonl')

# A REAL discharge: `review(x): ...` (any subject prefix), or a `chore(review):`
# subject whose own text says DISCHARGE rather than RECORD. Matched narrowly
# on the verb because "chore(review): record the obligation" and
# "chore(review): discharge cody ..." share the same conventional prefix and
# mean opposite things -- the contract names this exact conflation as the
# gap hover1's own build has not closed.
REVIEW_SUBJECT_RE = re.compile(r'^review\(', re.I)
CHORE_REVIEW_RE = re.compile(r'^chore\(review\):\s*(.*)$', re.I)
RECORD_VERB_RE = re.compile(r'^\s*record\b', re.I)

_HEX_TOKEN = re.compile(r'[0-9a-f]{6,40}')


class NoRepo(Exception):
    pass


def _run_git(args, timeout, **kw):
    try:
        return subprocess.run(args, timeout=timeout, encoding='utf-8',
                              errors='replace', **kw)
    except subprocess.TimeoutExpired:
        raise NoRepo('%s did not return within %ss -- treated as COULD NOT '
                     'RUN rather than waited on indefinitely.'
                     % (' '.join(args), timeout))


def discover_repo(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if '--repo' in argv:
        i = argv.index('--repo')
        if i + 1 < len(argv):
            return argv[i + 1]
    env = os.environ.get('HOVER_LEDGER_REPO')
    if env:
        return env
    for candidate in _KNOWN_CLONES:
        if os.path.isdir(os.path.join(candidate, '.git')):
            return candidate
    return None


def classify_subject(subject):
    """('discharge', text) | ('record', text) | None -- None means this
    commit is not review-shaped at all and is out of scope entirely."""
    if REVIEW_SUBJECT_RE.match(subject):
        return 'discharge', subject
    m = CHORE_REVIEW_RE.match(subject)
    if m:
        rest = m.group(1)
        if RECORD_VERB_RE.match(rest):
            return 'record', subject
        return 'discharge', subject
    return None


def scan_review_commits(repo, since=None):
    """[{'sha','sha_full','subject','kind'}] for every review-shaped commit
    on origin/main, oldest first. Always fetches origin first -- see the
    module docstring."""
    if not repo or not os.path.isdir(repo):
        raise NoRepo('no readable clone: %r (checked --repo, '
                     '$HOVER_LEDGER_REPO, and %s)' % (repo, ', '.join(_KNOWN_CLONES)))
    _run_git(['git', 'fetch', 'origin', '--quiet'], GIT_TIMEOUT_FETCH,
             cwd=repo, capture_output=True, text=True, check=True)
    cmd = ['git', 'log', '--pretty=format:%H%x00%s', 'origin/main']
    if since:
        cmd.append('--since=' + since)
    out = _run_git(cmd, GIT_TIMEOUT_FETCH, cwd=repo, capture_output=True,
                   text=True, check=True).stdout
    rows = []
    for line in out.split('\n'):
        if not line.strip():
            continue
        sha, _, subject = line.partition('\x00')
        cls = classify_subject(subject)
        if cls is None:
            continue
        kind, _text = cls
        rows.append({'sha': sha[:10], 'sha_full': sha, 'subject': subject, 'kind': kind})
    rows.reverse()
    return rows


def read_self_log(path=None):
    """Every entry in THIS role's own self-log, or None if unreadable/
    missing. Never reads another session's log -- coverage is a per-session
    fact, and fusing logs here would be the same mistake the multi-log
    self-log tooling fix this session exists to prevent, from the other
    direction (fusing chains instead of refusing to see them)."""
    path = path or SELF_LOG_PATH
    if not os.path.isfile(path):
        return None
    entries = []
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except (OSError, ValueError):
        return None
    return entries


def _sha_in_ref(sha_full, ref_field):
    """Variable-length (6-40 hex chars), prefix-match either direction --
    the fix for the fixed-width word-boundary trap named in the contract."""
    if not ref_field:
        return False
    sha_full = sha_full.lower()
    for token in _HEX_TOKEN.findall(ref_field.lower()):
        if sha_full.startswith(token) or token.startswith(sha_full):
            return True
    return False


def is_covered(sha_full, self_log_entries):
    if not self_log_entries:
        return False
    return any(_sha_in_ref(sha_full, e.get('ref', '')) for e in self_log_entries)


def build_ledger(repo, since=None, self_log_path=None):
    """(commits, self_log_entries). commits carry an added 'covered' bool."""
    commits = scan_review_commits(repo, since=since)
    entries = read_self_log(self_log_path)
    for c in commits:
        c['covered'] = is_covered(c['sha_full'], entries)
    return commits, entries


def grade(commits, self_log_entries):
    """Attaches 'level' to every covered commit, SLSA-style, same shape as
    sabotage_claim_verify.py's grading built earlier this session:
      1 -- covered, no re-citation found
      2 -- covered, cited by MORE THAN ONE self-log entry (a real re-look,
           though this role citing itself twice is not independent the way
           a second hover instance's citation would be -- stated as a known
           limit, not oversold as level 3)
    Level 3 (a DIFFERENT session's citation) is not reachable from a
    single-session self-log by construction -- this tool intentionally never
    reads another session's log, so it cannot claim that level honestly."""
    for c in commits:
        if not c['covered']:
            c['level'] = 0
            continue
        hits = sum(1 for e in (self_log_entries or []) if _sha_in_ref(c['sha_full'], e.get('ref', '')))
        c['level'] = 2 if hits > 1 else 1


def _print_report(commits, graded=False):
    discharge = [c for c in commits if c['kind'] == 'discharge']
    record_only = [c for c in commits if c['kind'] == 'record']
    covered = [c for c in discharge if c['covered']]
    uncovered = [c for c in discharge if not c['covered']]
    print('HOVER COVERAGE LEDGER -- %d review-shaped commit(s): %d discharge, '
          '%d record-only (queued, not yet reviewable as a gap)'
          % (len(commits), len(discharge), len(record_only)))
    print('Of the %d discharge commits: %d covered by this role\'s self-log, '
          '%d NOT' % (len(discharge), len(covered), len(uncovered)))
    print('')
    print('UNCOVERED (%d) -- eligible for this role to look at:' % len(uncovered))
    for c in uncovered:
        print('  %s  %s' % (c['sha'], c['subject']))
    print('')
    print('COVERED (%d):' % len(covered))
    for c in covered:
        if graded:
            print('  %s  L%d  %s' % (c['sha'], c['level'], c['subject']))
        else:
            print('  %s  %s' % (c['sha'], c['subject']))
    if record_only:
        print('')
        print('RECORD-ONLY, not a coverage gap (%d) -- an obligation was '
              'booked, nothing has been reviewed yet:' % len(record_only))
        for c in record_only:
            print('  %s  %s' % (c['sha'], c['subject']))


def main(argv):
    if '--selftest' in argv:
        return 0 if run_fixtures() else 1
    repo = discover_repo(argv)
    try:
        commits, entries = build_ledger(repo)
    except NoRepo as e:
        print('COULD NOT RUN: %s' % e)
        return 2
    graded = '--grade' in argv
    if graded:
        grade(commits, entries)
    if entries is None:
        print('NOTE: this role\'s own self-log could not be read -- every '
             'commit reports as NOT covered, which may be a missing log '
             'rather than a real gap. Treat with that caveat.')
        print('')
    _print_report(commits, graded=graded)
    return 0


def run_fixtures():
    ok = [0]
    bad = []

    def ck(name, cond):
        if cond:
            ok[0] += 1
            print('  ok   ' + name)
        else:
            bad.append(name)
            print('  FAIL ' + name)

    ck('review( subject classifies as discharge',
       classify_subject('review(x): discharge cody')[0] == 'discharge')
    ck('chore(review): record ... classifies as record',
       classify_subject('chore(review): record the obligation on leg_invoices')[0] == 'record')
    ck('chore(review): discharge ... classifies as discharge (same prefix, '
       'different verb)',
       classify_subject('chore(review): discharge cc 20:00:00Z')[0] == 'discharge')
    ck('an unrelated commit subject is not review-shaped at all',
       classify_subject('fix(sairnlaw): a real bug') is None)

    full = 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0'
    ck('a full 40-char sha IS matched in a ref field containing it (the trap '
       'a fixed {7,10}-width word-boundary regex would silently miss)',
       _sha_in_ref(full, 'discharged ' + full + ' clean'))
    ck('a short (10-char) ref token still matches the full sha via prefix',
       _sha_in_ref(full, 'discharged ' + full[:10] + ' clean'))
    ck('an unrelated sha in ref does not match',
       not _sha_in_ref(full, 'discharged 0000000000000000000000000000000000000000'))
    ck('an empty ref field never matches', not _sha_in_ref(full, ''))

    entries = [{'ref': full[:10] + ', other stuff'}]
    ck('is_covered() true when the log cites the commit', is_covered(full, entries))
    ck('is_covered() false with no entries at all', is_covered(full, None) is False)
    ck('is_covered() false when entries exist but none cite this sha',
       is_covered(full, [{'ref': 'unrelated'}]) is False)

    commits = [
        {'sha_full': 'aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111', 'kind': 'discharge'},
        {'sha_full': 'bbbb2222bbbb2222bbbb2222bbbb2222bbbb2222', 'kind': 'discharge'},
    ]
    log = [{'ref': 'aaaa1111'}, {'ref': 'aaaa1111 again, re-checked'}]
    for c in commits:
        c['covered'] = is_covered(c['sha_full'], log)
    grade(commits, log)
    ck('grade(): a commit cited by TWO entries is level 2',
       commits[0]['level'] == 2)
    ck('grade(): a commit cited by zero entries is level 0',
       commits[1]['level'] == 0)
    only_once = [{'sha_full': 'cccc', 'kind': 'discharge', 'covered': True}]
    grade(only_once, [{'ref': 'cccc'}])
    ck('grade(): a commit cited by exactly one entry is level 1',
       only_once[0]['level'] == 1)

    print('')
    print('%d ok, %d failed' % (ok[0], len(bad)))
    return not bad


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
