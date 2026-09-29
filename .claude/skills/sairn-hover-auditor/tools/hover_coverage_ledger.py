#!/usr/bin/env python
"""hover_coverage_ledger.py -- which of the platform's own discharged Tier A
review obligations this role has actually independently re-verified, and
which are genuinely untouched.

BUILT ON DIRECT INSTRUCTION (2026-09-21), item 1 of a five-item queue about
this role's own setup, not the platform's. This is this role's own
operational tooling -- it records and verifies the hover auditor's OWN
re-verification activity, not platform code -- so building it is squarely
inside the narrow exception the core rule already states, the same one
hover_log.py, undirected_sweep_freshness.py and seed_corpus.md already sit
inside.

WHY THIS EXISTS. Every re-verification pass this session picked a fresh
target by hand: pull the git log, grep for `review(`/`chore(review):`
commits, cross a mental list of what had already been touched against
memory of the last several turns. That method has no persistence past this
conversation and no way to answer "have I actually covered this one yet"
except by re-reading the whole review-commit history again -- which is
itself the manual process this tool replaces. Without a ledger, the same
resource can be re-picked (harmless, but wasted effort) while a genuinely
untouched one sits unchecked (the real risk) -- and neither is visible
without literally diffing memory against the full git log by hand.

THE TWO SOURCES, DELIBERATELY THE SIMPLE ONES RATHER THAN A FUZZY JOIN.
docs/tier-a-reviews.json is the platform's own structured registry of
discharged obligations, but it carries no review-COMMIT-sha field (only the
ORIGINAL commit under review, in `commit`) -- matching a review verdict to
its own git commit would mean fuzzy-joining on `reviewed_at` timestamp and
`reviewer_session`, which is a guess dressed as a join. What this role has
actually referenced, every time, all session, is the review commit's own
short sha, typed directly into `--ref` on the hover_log entry that
discusses it. So the ledger is built from the two things that are exact:

  A. every `review(...)` / `chore(review):` commit subject in `git log`,
     which is the real, authoritative, review-commit-shaped subset of
     history -- the same regex this role has typed into `git log | grep`
     by hand on every turn of this thread.
  B. every commit-sha-shaped token inside any `check`/`finding` entry's
     `ref` field in this role's own self-log, extracted structurally,
     never by re-deriving what "was probably meant" from prose.

A commit's short sha (7-10 hex chars) appearing ANYWHERE in a hover_log
entry's `ref` field is treated as coverage, on the same standard already
used throughout this thread's own reporting. THIS IS A REAL LIMIT AND IS
NAMED RATHER THAN HIDDEN: a sha cited in `ref` because it was READ and
discussed is not distinguished here from one that was independently DRIVEN
with an own harness and mutation -- that finer distinction lives only in
each entry's own summary prose, which this tool does not parse. The ledger
answers "was this commit referenced by hover at all", not "was it driven
to the standard SKILL.md requires" -- a coarser, cheaper, and honestly
disclosed question.

STALENESS, FOUND AND FIXED 2026-09-21 (same day this tool was built, by the
SECOND hover session running it from a different clone). REPO was a single
hardcoded path to THIS session's own clone. The moment a second, independent
hover session (SAIRN-hover2) existed and ran this same tool, it silently read
SAIRN-hover's local checkout regardless of which clone was actually running
it -- so the ledger's "uncovered" answer depended on whichever clone happened
to have pulled most recently, not on real platform state. That is exactly the
failure this tool exists to prevent, one level up: a coverage answer that
LOOKS authoritative while quietly measuring the wrong thing. Twice in one
session this required falling back to a manual `git log --grep` sweep to find
review commits the ledger had missed -- the actual, measured symptom of this
bug, not a hypothetical one.

FIXED TWO WAYS, NOT ONE, because either alone leaves a gap. (1) discover_repo()
no longer hardcodes a clone -- it checks --repo, then $HOVER_LEDGER_REPO, then
a short list of known hover clones, first one that exists. (2) EVEN WITH THE
RIGHT CLONE PICKED, a stale local branch still lies: `git log --all` reads
whatever that clone's local refs say, and a clone that has not pulled reports
an outdated answer under its own name. So this now ALWAYS `git fetch origin`
first (read-only, touches only remote-tracking refs, never the working tree
or index of a clone this role does not own) and reads commits from
`origin/main` specifically, never local `--all` -- the answer is now the same
regardless of which clone runs it or when that clone last pulled.
`git fetch` was chosen over `git pull` deliberately: a pull would write to
another session's working tree, which is exactly the cross-clone mutation the
platform's own separation rules exist to forbid; a fetch only updates refs
this process reads, never anything a build agent's own session has open.

Run:
  python hover_coverage_ledger.py                 -- full report
  python hover_coverage_ledger.py --uncovered-only -- just the pick-from list
  python hover_coverage_ledger.py --repo <path>    -- override clone discovery
  python hover_coverage_ledger.py --selftest       -- fixture-based self-check
"""
import json
import os
import re
import subprocess
import sys

# Known hover-adjacent clones, checked in this order when --repo and
# $HOVER_LEDGER_REPO are both absent. Not exhaustive by design -- a third
# hover clone would need adding here OR (better) an explicit --repo, the same
# "never hardcode, never silently guess" standard CLAUDE.md already states
# for the four build clones.
_KNOWN_CLONES = (
    'C:/Users/marsh/Documents/SAIRN-hover',
    'C:/Users/marsh/Documents/SAIRN-hover2',
)
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'hover-audit-log.jsonl')

REVIEW_SUBJECT = re.compile(r'^(review\(|chore\(review\):)', re.I)
SHA_TOKEN = re.compile(r'\b[0-9a-f]{7,10}\b')


def discover_repo(argv=None):
    """Which clone's git history to read -- never a single hardcoded path.

    Order: --repo <path> on the command line, then $HOVER_LEDGER_REPO, then
    the first of _KNOWN_CLONES that exists on disk with a .git directory.
    Returns None (COULD NOT TELL) rather than a guess if nothing resolves --
    the caller must fail closed on that, not fall back to a default.
    """
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


class NoRepo(Exception):
    pass


def review_commits(repo):
    """[(short_sha, subject)] for every review-shaped commit on origin/main,
    oldest first.

    ALWAYS fetches first (read-only) and reads origin/main rather than local
    `--all` -- see the module docstring's STALENESS section for why local
    branch state cannot be trusted here regardless of which clone is asked.
    `git log --oneline` already returns short shas (the same length this role
    has cited by hand all session); no separate short/full normalisation step
    is needed as long as both sides of the comparison come from the same
    command shape, which they do here.
    """
    if not repo or not os.path.isdir(repo):
        raise NoRepo('no readable clone: %r (checked --repo, '
                      '$HOVER_LEDGER_REPO, and %s)' % (repo, ', '.join(_KNOWN_CLONES)))
    try:
        subprocess.run(['git', 'fetch', 'origin', '--quiet'],
                        cwd=repo, capture_output=True, text=True,
                        encoding='utf-8', check=True)
        # encoding='utf-8' explicit on both calls -- text=True alone
        # decodes with the OS locale's preferred encoding (cp1252 on
        # Windows), which crashes on the first non-ASCII byte in a real
        # commit subject or file. Found live in hover_pure_js_exec.py
        # against the real stonedesk.html; applied here defensively since
        # commit subjects on this platform routinely carry non-ASCII prose.
        out = subprocess.run(
            ['git', 'log', '--oneline', 'origin/main'],
            cwd=repo, capture_output=True, text=True, encoding='utf-8',
            check=True
        ).stdout
    except subprocess.CalledProcessError as e:
        # A failed fetch/log (no network, dead remote, no origin/main) must
        # surface through the SAME "COULD NOT RUN" contract as an unreadable
        # clone, not an uncaught traceback that skips main()'s except NoRepo
        # and exits 1 instead of the documented 2 -- found by chaos-injection
        # (a real unreachable origin), not by inspection alone.
        raise NoRepo('git fetch/log failed in %s: %s'
                      % (repo, (e.stderr or str(e)).strip()))
    commits = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        sha, _, subject = line.partition(' ')
        if REVIEW_SUBJECT.match(subject):
            commits.append((sha, subject))
    commits.reverse()  # oldest first
    return commits


def load_log_entries(path=LOG_PATH):
    try:
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()
    except OSError as e:
        raise NoRepo('could not read self-log %s: %s' % (path, e))
    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except ValueError as e:
            raise NoRepo('self-log %s has a malformed line: %s' % (path, e))
    return entries


def referenced_shas(entries):
    """set of every sha-shaped token appearing in any check/finding entry's
    ref field. Structural extraction, not prose-reading -- the same
    discipline hover_log.py's own structured fields already use."""
    refs = set()
    for e in entries:
        if e.get('type') not in ('check', 'finding'):
            continue
        ref = e.get('ref') or ''
        refs.update(SHA_TOKEN.findall(ref.lower()))
    return refs


def ledger(repo, log_path=LOG_PATH):
    commits = review_commits(repo)
    entries = load_log_entries(log_path)
    refs = referenced_shas(entries)
    rows = []
    for sha, subject in commits:
        covered = sha.lower() in refs
        rows.append({'sha': sha, 'subject': subject, 'covered': covered})
    return rows


def _print_report(rows, uncovered_only=False):
    covered = [r for r in rows if r['covered']]
    uncovered = [r for r in rows if not r['covered']]
    if not uncovered_only:
        print('HOVER COVERAGE LEDGER -- %d review-shaped commits, %d referenced by this role, %d not'
              % (len(rows), len(covered), len(uncovered)))
        print('COVERAGE HERE MEANS "cited in a hover_log ref field", not "driven to SKILL.md\'s own '
              'standard" -- that finer distinction is not tracked by this tool. See the module '
              'docstring before treating a covered row as more than that.')
        print()
    print('UNCOVERED (%d) -- pick from here first on the next re-verification pass:' % len(uncovered))
    for r in uncovered:
        print('  %s  %s' % (r['sha'], r['subject']))
    if not uncovered_only:
        print()
        print('COVERED (%d):' % len(covered))
        for r in covered:
            print('  %s  %s' % (r['sha'], r['subject']))


def run_fixtures():
    """Blind-lock style: locked BEFORE this run against real data, same
    discipline every other hover tool in this directory already follows."""
    import tempfile

    ok_count = [0]
    fail_count = [0]

    def ck(name, cond):
        if cond:
            ok_count[0] += 1
            print('  ok   ' + name)
        else:
            fail_count[0] += 1
            print('  FAIL ' + name)

    # --- referenced_shas() ---
    entries = [
        {'type': 'check', 'ref': 'abc1234,def5678'},
        {'type': 'finding', 'ref': 'commit 9999999 and tools/foo.py'},
        {'type': 'note', 'ref': 'aaaa111'},  # not check/finding -- must NOT count
        {'type': 'check', 'ref': None},      # missing ref -- must not crash
    ]
    refs = referenced_shas(entries)
    ck('a sha inside a comma-joined ref field is found', 'abc1234' in refs)
    ck('...and a second one in the same field', 'def5678' in refs)
    ck('a sha embedded in prose inside ref is found', '9999999' in refs)
    ck('a note-type entry (not check/finding) contributes NOTHING',
       'aaaa111' not in refs)
    ck('a missing ref field does not crash the scan', True)  # got this far

    # --- discover_repo(): the actual bug fixed today, tested directly ------
    ck('--repo on the command line wins over everything',
       discover_repo(['--repo', '/explicit/path']) == '/explicit/path')
    old_env = os.environ.get('HOVER_LEDGER_REPO')
    try:
        os.environ['HOVER_LEDGER_REPO'] = '/env/path'
        ck('$HOVER_LEDGER_REPO is used when --repo is absent',
           discover_repo([]) == '/env/path')
        del os.environ['HOVER_LEDGER_REPO']
        global _KNOWN_CLONES
        real_clones = _KNOWN_CLONES
        try:
            _KNOWN_CLONES = ('/definitely/does/not/exist/anywhere',)
            ck('no --repo, no env, no existing candidate -> None (COULD NOT '
               'TELL), never a silent guess', discover_repo([]) is None)
        finally:
            _KNOWN_CLONES = real_clones
    finally:
        if old_env is None:
            os.environ.pop('HOVER_LEDGER_REPO', None)
        else:
            os.environ['HOVER_LEDGER_REPO'] = old_env

    # --- review_commits(): a real bare "origin" + a real push, because the
    # STALENESS FIX ITSELF is "fetch origin, read origin/main" -- a fixture
    # with no real remote would never exercise the line that was actually
    # broken. bare_repo stands in for GitHub; work_repo stands in for a
    # hover clone, exactly the shape SAIRN-hover/SAIRN-hover2 actually are.
    tmpdir = tempfile.mkdtemp()
    bare_repo = os.path.join(tmpdir, 'origin.git')
    work_repo = os.path.join(tmpdir, 'work')
    subprocess.run(['git', 'init', '-q', '--bare', bare_repo], check=True)
    subprocess.run(['git', 'init', '-q', work_repo], check=True)
    subprocess.run(['git', 'config', 'user.email', 'x@x.com'], cwd=work_repo, check=True)
    subprocess.run(['git', 'config', 'user.name', 'x'], cwd=work_repo, check=True)
    subprocess.run(['git', 'checkout', '-q', '-b', 'main'], cwd=work_repo, check=True)
    subprocess.run(['git', 'remote', 'add', 'origin', bare_repo], cwd=work_repo, check=True)
    msgs = [
        'review(tier-a): a real review commit',
        'chore(review): discharge something',
        'chore(claims): fourth claims something',   # must NOT match
        'fix(sd-data): unrelated product fix',       # must NOT match
        'reviewed by hand, not a real subject match', # must NOT match (no paren/colon shape)
    ]
    for i, m in enumerate(msgs):
        open(os.path.join(work_repo, 'f%d.txt' % i), 'w').write(str(i))
        subprocess.run(['git', 'add', '.'], cwd=work_repo, check=True)
        subprocess.run(['git', 'commit', '-q', '-m', m], cwd=work_repo, check=True)
    subprocess.run(['git', 'push', '-q', 'origin', 'main'], cwd=work_repo, check=True)

    ck('review_commits() on a repo with no --repo/env/candidate match refuses '
       'rather than reading nothing',
       _raises(NoRepo, review_commits, None))
    ck('review_commits() on a non-directory path also refuses',
       _raises(NoRepo, review_commits, '/definitely/does/not/exist'))

    commits = review_commits(work_repo)
    subjects = [s for _, s in commits]
    ck('review(...) subject IS matched', any(s.startswith('review(') for s in subjects))
    ck('chore(review): subject IS matched', any(s.startswith('chore(review):') for s in subjects))
    ck('chore(claims): is NOT matched', not any(s.startswith('chore(claims):') for s in subjects))
    ck('an unrelated fix(...) is NOT matched', not any('unrelated product fix' in s for s in subjects))
    ck('exactly 2 of 5 commits matched', len(commits) == 2)
    ck('oldest-first ordering (the review() commit was made before chore(review):)',
       subjects[0].startswith('review('))

    # --- THE ACTUAL STALENESS FIX, DRIVEN: a SECOND clone of the SAME
    # bare origin, behind on its own local branch, must still report the
    # SAME commits as work_repo -- because both read origin/main, not their
    # own local HEAD. This is the exact two-clone scenario that went stale
    # tonight, reproduced in miniature and proven fixed rather than argued.
    stale_clone = os.path.join(tmpdir, 'stale_clone')
    subprocess.run(['git', 'clone', '-q', bare_repo, stale_clone], check=True)
    # The bare repo's own HEAD symref was never pointed at 'main' (it was
    # created empty, before the first push), so the clone above checks out
    # nothing. Point it at main explicitly -- a real clone of a real GitHub
    # repo would not need this, but this fixture's bare repo does.
    subprocess.run(['git', 'checkout', '-q', '-b', 'main', 'origin/main'],
                    cwd=stale_clone, check=True)
    # Reset the stale clone's own local main back one commit, so its local
    # HEAD genuinely disagrees with origin/main -- the real shape of "a
    # clone that has not pulled recently".
    subprocess.run(['git', 'reset', '-q', '--hard', 'HEAD~1'], cwd=stale_clone, check=True)
    stale_local_log = subprocess.run(
        ['git', 'log', '--oneline'], cwd=stale_clone,
        capture_output=True, text=True, check=True).stdout
    ck('the fixture really did desync the stale clone\'s own local branch '
       'from origin (a real precondition, not assumed) -- 4 commits locally, '
       'not the 5 that were pushed',
       len([l for l in stale_local_log.splitlines() if l.strip()]) == 4)
    stale_commits = review_commits(stale_clone)
    ck('THE STALE CLONE STILL REPORTS THE FULL, CURRENT SET -- fetch+origin/main '
       'reads past its own out-of-date local HEAD',
       len(stale_commits) == len(commits) == 2)
    ck('and the two clones agree on the exact same shas, not just the same count',
       {s for s, _ in stale_commits} == {s for s, _ in commits})

    # --- end-to-end: a fabricated review commit + a fabricated log entry ---
    log_tmp = os.path.join(tmpdir, 'fake_log.jsonl')
    fake_sha = commits[0][0]
    with open(log_tmp, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'type': 'check', 'ref': fake_sha}) + '\n')
    rows = ledger(repo=work_repo, log_path=log_tmp)
    covered_shas = {r['sha'] for r in rows if r['covered']}
    ck('end-to-end: the referenced commit is COVERED', fake_sha in covered_shas)
    ck('end-to-end: the other real review commit is UNCOVERED',
       any(not r['covered'] for r in rows) and len(rows) == 2)

    print()
    print('%d ok, %d failed' % (ok_count[0], fail_count[0]))
    return fail_count[0] == 0


def _raises(exc_type, fn, *a, **kw):
    try:
        fn(*a, **kw)
        return False
    except exc_type:
        return True


def main(argv):
    if '--selftest' in argv:
        ok = run_fixtures()
        sys.exit(0 if ok else 1)
    uncovered_only = '--uncovered-only' in argv
    repo = discover_repo(argv)
    try:
        rows = ledger(repo)
    except NoRepo as e:
        print('COULD NOT RUN: %s' % e)
        return 2
    _print_report(rows, uncovered_only=uncovered_only)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
