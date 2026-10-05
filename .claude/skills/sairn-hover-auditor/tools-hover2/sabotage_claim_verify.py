#!/usr/bin/env python
"""sabotage_claim_verify.py -- which commits claim a sabotage/mutation count
with no matching runnable artifact committed alongside the claim, AND how
much that claim is actually worth once it clears that bar.

BUILT ON DIRECT INSTRUCTION (2026-09-21). This role's own operational
tooling -- it audits commit messages and diffs for a specific claim SHAPE,
never edits platform code, and its subject is this platform's commit
history, the same class of thing hover_coverage_ledger.py already reads.
Squarely inside the core rule's narrow exception, same standard as every
other tool in this directory.

WHY THIS EXISTS. Confirmed tonight as a real, recurring pattern (this role's
own self-log, seq 342): at least three independent review cycles found the
identical shape -- a commit's own message states "N of N sabotages caught"
or "N mutations, all refused" as its verification evidence, and the mutation
script that produced that number was never committed, so a future reader has
prose to trust instead of a control to re-run. All three instances traced to
one build agent's cross-tenant dispatcher suite across three review passes
(phases 1, 2, 3) plus one unrelated feature (the scp setter fix) -- a real,
repeating shape, not one commit reviewed three times.

WHAT THIS CHECKS, PRECISELY, AND WHAT IT DOES NOT. For every commit whose
message contains a sabotage/mutation-count claim, this asks ONE mechanical
question: did THIS COMMIT's own diff add or modify a file whose path
contains "sabotage"? That is deliberately narrower than "does a sabotage
runner for this claim exist anywhere in the repository, ever" -- a repo-wide
search would produce real false negatives in the other direction, credit
a claim on the strength of an unrelated probe elsewhere in the tree just
because it also has "sabotage" in its name. THE SAME-COMMIT CHECK IS NOT A
GUARANTEE THE COMMITTED FILE ACTUALLY IMPLEMENTS THE CLAIMED COUNT EITHER --
that would need reading and running the file, a build agent's job, not this
scan's. A "clear" verdict here means "a plausible artifact was committed
alongside the claim, go verify it does what it says"; a "FLAGGED" verdict
means "there is nothing in this commit's own diff that could possibly
produce the number in its own message" -- and that second claim is checked,
not inferred: a commit with a "sabotage"-shaped file already present
elsewhere in history but NOT touched by this specific commit still flags,
because the question is "did this commit ship its own evidence", not "does
evidence exist somewhere".

-- GRADING, ADDED 2026-09-22, MODELLED ON SLSA -----------------------------
SLSA (Supply-chain Levels for Software Artifacts) grades trust in a build
claim by how verifiable its evidence actually is, rather than a single
trusted/untrusted bit. The flagged/clear question above answers "does
evidence exist at all" -- a real question, but a coarse one: it cannot tell
"nobody has looked at this since the day it was claimed" apart from
"independently re-run and confirmed", and tonight's own 22 re-verifications
are proof those are very different levels of trust. Grading answers the
NARROWER, HARDER question on top of the same clear/flagged gate:

  LEVEL 0 -- FLAGGED. No matching artifact in the claim commit's own diff.
            (Unchanged from above; levels 1-3 only apply once CLEAR.)
  LEVEL 1 -- CLEAR, no re-run evidence found. The artifact exists and was
            committed, but nothing in this repo's history or this role's
            own log shows it has been run again since the claim.
  LEVEL 2 -- CLEAR, AND a LATER commit touches the SAME sabotage-named
            file(s) and itself makes a fresh, recognised claim against
            them (re-uses CLAIM_PATTERNS, not a new fuzzy keyword search --
            see the note at find_self_reclaim() for why). This is a real
            re-run, but git carries no field on this platform that says
            WHICH session authored which commit -- every commit here is
            "Michael Dibert" with the same Claude co-author line regardless
            of clone -- so this level cannot and does not claim the re-run
            was independent, only that one happened.
  LEVEL 3 -- CLEAR, AND this role's OWN self-log (hover-audit-log.jsonl,
            read directly, not inferred) carries a `check`-type entry whose
            `ref` field names this commit. hover is a structurally separate
            fifth role, own clone, own commit history, enforced by
            tools/hover_auditor_scope_gate.py -- it never authors a
            platform commit, so ANY citation here is independent by
            construction, never the claiming session re-checking its own
            work. This is the level tonight's 22 clean re-verifications
            actually established, one at a time, and is the only level this
            tool trusts as fully proven rather than "a re-run happened."

A FOURTH, LOUDER CASE THAT IS NOT ON THE 0-3 SCALE: this role's own log
cites the commit with a `finding`-type entry (a documented discrepancy),
not a `check`. That is reported as its own line, ahead of every level --
the single most important thing this tool can say about a claim is "an
independent check ran and disagreed with it," and folding that into a
number between 1 and 3 would bury it.

GRADING DEGRADES VISIBLY WHEN IT CANNOT RUN, same discipline as everything
else here: if hover-audit-log.jsonl is missing or unparsable, every row's
level is reported as UNKNOWN (self-log unreadable) rather than silently
assumed to be Level 1 -- an unreadable log is not evidence of no
re-verification, the same distinction sairn_status.py's own empty-registry
case draws.

CALIBRATION STATUS, CORRECTED 2026-09-22 -- the original text here was
itself the exact defect shape this tool exists to catch, found by hover2
independently reading this file and confirmed by cc against the same
source (docs/SAIRN-OPEN-WORK-INDEX.md, Tooling row). It claimed
run_fixtures() had a "real-repo section" checking eight named real SHAs
(0b1e017f/5a878e71, 608c310b, cfbb2427, 0dd84d94, 200fe086, deea8c55,
b40c659090, 2cb6460dc5) against the live repo and hover's own
hover-audit-log.jsonl. NO SUCH SECTION EXISTED. run_fixtures() (below) is
entirely synthetic tmpdir fixtures; it never reads the real repo or any
real self-log.

RE-CHECKED DIRECTLY, NOT JUST REMOVED: calling commit_sabotage_files()
against the real repo for all eight named SHAs (2026-09-22) found the
original claim was not only untested but WRONG on three of them. Claimed
CLEARED: 0dd84d94, 200fe086, deea8c55 -- but 0dd84d94 (fix(sd-data): the
json-catch-null sweep finishes...) touches no path containing "sabotage"
and is actually FLAGGED; only 200fe086 and deea8c55 are genuinely CLEARED.
Claimed as real Level-3 (CLEAR + independently re-verified) cases:
b40c659090 and 2cb6460dc5 -- both are actually FLAGGED (Level 0), which
cannot be promoted to Level 3 by this tool's own grade_rows() ("LEVEL 0
cannot be promoted by a hover_log citation"), so the claim was impossible
on its own terms, not merely unverified.

WHAT THIS TOOL IS ACTUALLY CALIBRATED AGAINST, STATED ACCURATELY: the
synthetic fixtures in --selftest / run_fixtures() below, in both
directions (FLAGGED and CLEARED, all four grading levels, the DISCREPANCY
sentinel, and the self-log-unreadable UNKNOWN case) -- these are real and
do pass. THERE IS NO AUTOMATED CHECK AGAINST THE LIVE REPOSITORY. A reader
wanting that assurance must run scan()/commit_sabotage_files() by hand, as
was done for this correction; building a permanent real-repo section
remains a real, disclosed option for later, not done here.

STALENESS FIX ALREADY APPLIED FROM THE START, not retrofitted: uses the
identical discover_repo() / fetch-origin/read-origin-main discipline
hover_coverage_ledger.py and hover_cold_scan_pool.py were fixed to use this
same session, for the identical reason -- a hardcoded or un-fetched clone
would silently under- or over-report which commits exist to check at all.

Run:
  python sabotage_claim_verify.py                 -- full report, graded
  python sabotage_claim_verify.py --flagged-only   -- just the flagged list
  python sabotage_claim_verify.py --no-grade       -- the old binary report only
  python sabotage_claim_verify.py --repo <path>    -- override clone discovery
  python sabotage_claim_verify.py --since <date>   -- only commits after DATE
                                                       (git's own --since syntax)
  python sabotage_claim_verify.py --hover-log <path> -- override self-log path
  python sabotage_claim_verify.py --selftest       -- fixture-based self-check
"""
import json
import os
import re
import subprocess
import sys

# GIT_TIMEOUT_SECONDS: every git subprocess call in this file is bounded
# (2026-09-21, found the hard way). Without this, `git fetch origin --quiet`
# hung with ZERO output for over ten minutes in a real run -- nothing in this
# file prints anything until scan() returns, so a genuine hang and a slow-but-
# working run are indistinguishable from outside. A backgrounded subprocess
# with no TTY is exactly the shape that can silently block forever on an
# interactive credential-helper prompt or a stalled network call; a bounded
# timeout converts that into a loud COULD-NOT-RUN rather than an unbounded
# wait nobody can tell apart from progress. 60s for fetch (a real network
# call); 20s for the local log/show reads (no network, should be near-
# instant -- a real hang there means something is genuinely stuck, not slow).
GIT_TIMEOUT_FETCH = 60
GIT_TIMEOUT_LOCAL = 20

_KNOWN_CLONES = (
    # H2's own clone first -- this is H2's private copy of this tool, reading
    # H2's own self-log, and discover_repo() must default to auditing H2's own
    # working tree. Found 2026-10-05 by this role's own self-audit, the same
    # class of bug hover_coverage_ledger.py's _KNOWN_CLONES already fixed the
    # same day, in a sibling file whose docstring says "Identical contract to
    # hover_coverage_ledger.py's discover_repo()" -- and was identical in this
    # one respect too. With H1's clone listed first, a bare
    # `python sabotage_claim_verify.py` (no --repo) silently checked claimed
    # commits against H1's clone's git state instead of this one. Both clones
    # share one remote (SAIRN1/SAIRN) so most shas resolve identically either
    # way -- but the day H1's clone is mid-fetch, on a different branch, or
    # simply behind, this would silently verify a sabotage claim against the
    # wrong repository's commit list with no error at all.
    'C:/Users/marsh/Documents/SAIRN-hover2',
    'C:/Users/marsh/Documents/SAIRN-hover',
)

# Where this role's own self-log lives, relative to THIS file -- the same
# directory, always; both known hover clones keep their tool and their log
# side by side (confirmed 2026-09-22: SAIRN-hover2 keeps none of this on
# disk on this machine at all, which is a separate, already-reported gap --
# see hover_log #398 -- and is exactly why grading degrades to UNKNOWN
# rather than assuming "no citation" when the log cannot be read, rather
# than crashing or reporting a false Level 1).
HOVER_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'hover-audit-log.jsonl')

# Every real phrasing seen in this platform's own commit messages tonight,
# not a single pattern guessed in advance. Each captures the claimed count as
# group 1 where the phrasing states one; some shapes ("ALL N ARMS PASS") name
# arms rather than mutations and are kept as their own pattern rather than
# forced to share a capture-group shape that would not fit both.
CLAIM_PATTERNS = (
    # "18 of 18 sabotages caught", "9 of 9 valid sabotages caught"
    re.compile(r'\b(\d+)\s+of\s+\1\s+(?:valid\s+)?sabotages?\s+caught', re.I),
    # "10 mutations ALL REFUSED", "13 mutations, all refused"
    re.compile(r'\b(\d+)\s+mutations?[,\s]+ALL\s+REFUSED', re.I),
    # "ALL 17 ARMS PASS", "ALL 14 ARMS PASS"
    re.compile(r'\bALL\s+(\d+)\s+ARMS?\s+PASS', re.I),
    # "9 OF 9 SABOTAGES", section-header style without the trailing "caught"
    re.compile(r'\b(\d+)\s+OF\s+\1\s+SABOTAGES\b', re.I),
)

SABOTAGE_PATH = re.compile(r'sabotage', re.I)

LEVEL_LABEL = {
    0: 'LEVEL 0 -- FLAGGED (no artifact)',
    1: 'LEVEL 1 -- CLEAR, no re-run evidence',
    2: 'LEVEL 2 -- CLEAR, re-run found (session not attributable)',
    3: 'LEVEL 3 -- CLEAR, INDEPENDENTLY RE-VERIFIED (hover)',
}


def discover_repo(argv=None):
    """Identical contract to hover_coverage_ledger.py's discover_repo()."""
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


def _run_git(args, timeout, **kw):
    """subprocess.run, bounded, translating a hang into a loud COULD-NOT-RUN
    (NoRepo, same as every other unreadable-repo failure this file already
    reports the same way) rather than an unbounded wait indistinguishable
    from a slow-but-working run. See GIT_TIMEOUT_* above for why this
    exists."""
    try:
        return subprocess.run(args, timeout=timeout, encoding='utf-8',
                               errors='replace', **kw)
    except subprocess.TimeoutExpired:
        raise NoRepo(
            '%s did not return within %ss -- treated as COULD NOT RUN rather '
            'than waited on indefinitely. A real hang here (credential '
            'prompt, stalled network) is otherwise indistinguishable from a '
            'slow-but-working run, since nothing prints until the whole scan '
            'completes.' % (' '.join(args), timeout))


def extract_claim(message):
    """The (count, matched_text) of the FIRST sabotage/mutation-count claim
    in a commit message, or None. Only the first is reported per commit --
    a commit citing several counts for several sub-changes is a real shape
    (0dd84d94's own body lists per-site counts) this tool does not try to
    pull apart per sub-claim; it answers "did THIS commit ship ANY matching
    artifact", not "does every individual number in it have one"."""
    for pat in CLAIM_PATTERNS:
        m = pat.search(message)
        if m:
            return (m.group(1), m.group(0))
    return None


def commit_sabotage_files(repo, sha):
    """The SET of paths this commit's own diff added or modified whose path
    contains 'sabotage' -- --name-only over the commit's own tree-diff, not
    a repo-wide search -- see the module docstring for why that distinction
    is the whole point of this check. Empty set, not False, so grading can
    reuse the same call to ask BOTH "did this commit ship evidence" (bool)
    AND "which file, so a later commit can be checked against the same
    one" (Level 2)."""
    r = _run_git(
        ['git', 'show', '--name-only', '--pretty=format:', sha],
        GIT_TIMEOUT_LOCAL,
        cwd=repo, capture_output=True, text=True, check=True
    )
    files = set()
    for line in r.stdout.splitlines():
        line = line.strip()
        if line and SABOTAGE_PATH.search(line):
            files.add(line)
    return files


def commit_touches_sabotage_file(repo, sha):
    """Back-compat wrapper -- the bool half of commit_sabotage_files()."""
    return bool(commit_sabotage_files(repo, sha))


def scan(repo, since=None):
    """[(sha, subject, claim_count, claim_text, has_sabotage_file, ...)] for
    every commit whose message contains a sabotage/mutation-count claim,
    oldest first. ALWAYS fetches origin first and reads origin/main -- same
    staleness discipline as the ledger and cold-scan-pool tools, for the
    identical reason: a claim made on origin/main and not yet pulled into
    whichever clone is discovered must still be seen.

    Each row also carries 'sha_full' and 'full_message' (not shown by the
    plain report) and 'sabotage_files' (the set from commit_sabotage_files())
    -- all three exist only so grade_rows() can cross-reference a claim
    commit against LATER ones without a second full-history git call."""
    if not repo or not os.path.isdir(repo):
        raise NoRepo('no readable clone: %r (checked --repo, '
                      '$HOVER_LEDGER_REPO, and %s)' % (repo, ', '.join(_KNOWN_CLONES)))
    _run_git(['git', 'fetch', 'origin', '--quiet'], GIT_TIMEOUT_FETCH,
              cwd=repo, capture_output=True, text=True, check=True)
    cmd = ['git', 'log', '--pretty=format:%H%x00%s%x00%B%x1e', 'origin/main']
    if since:
        cmd.append('--since=' + since)
    out = _run_git(cmd, GIT_TIMEOUT_FETCH, cwd=repo, capture_output=True,
                    text=True, check=True).stdout
    rows = []
    for record in out.split('\x1e'):
        if not record.strip('\n').strip():
            continue
        sha, _, rest = record.partition('\x00')
        subject, _, full = rest.partition('\x00')
        sha = sha.lstrip('\n')
        claim = extract_claim(full)
        if not claim:
            continue
        count, text = claim
        files = commit_sabotage_files(repo, sha)
        rows.append({
            'sha': sha[:10], 'sha_full': sha, 'subject': subject,
            'claim_count': count, 'claim_text': text,
            'has_sabotage_file': bool(files), 'sabotage_files': files,
            'full_message': full,
        })
    rows.reverse()  # oldest first
    return rows


# ---------------------------------------------------------------------------
# GRADING
# ---------------------------------------------------------------------------

def read_hover_log(path=None):
    """Every entry in this role's own self-log, or None if it cannot be
    read at all (missing file, unparsable JSON on some line). None is a
    distinct return from [] on purpose -- an EMPTY log is a real, readable
    fact (nothing has been checked yet, every row is Level 1 at best); an
    UNREADABLE log means grading has no basis to say that, the same
    distinction sairn_status.py's own docs draw between an empty registry
    and one nothing writes to."""
    path = path or HOVER_LOG_PATH
    if not os.path.isfile(path):
        return None
    entries = []
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entries.append(json.loads(line))
    except (OSError, ValueError):
        return None
    return entries


_HEX_TOKEN = re.compile(r'[0-9a-f]{6,40}')


def _sha_in_ref(sha_full, ref_field):
    """True if `ref_field` (this role's own free-text ref string, e.g.
    "ce7764fa,d3d8c5b2,61031df2") names `sha_full`. PREFIX MATCH, EITHER
    DIRECTION, MINIMUM 6 HEX CHARS -- refs in this log have been written at
    inconsistent lengths (8 and 10 hex chars both appear in this very
    session's own entries), and a sha this tool computes is always the
    git-log-returned full 40 or the 10-char slice scan() stores. A 6-char
    floor is git's own convention for "short enough to be readable, long
    enough that an accidental collision in a repo this size is not a real
    risk" -- reused rather than invented."""
    if not ref_field:
        return False
    sha_full = sha_full.lower()
    for token in _HEX_TOKEN.findall(ref_field.lower()):
        if sha_full.startswith(token) or token.startswith(sha_full):
            return True
    return False


def find_independent_reverification(sha_full, hover_entries):
    """The FIRST (oldest) entry in this role's own self-log whose `ref`
    names this commit, or None. Returns the whole entry, not just a bool,
    so the caller can read its `type` -- a `check` entry is confirmation
    (LEVEL 3); a `finding` entry is a documented DISCREPANCY, which this
    tool reports louder than any of the four levels, never folds into one.

    WHY A CITATION HERE IS ALWAYS INDEPENDENT, STRUCTURALLY, NOT BY
    CONVENTION: hover is the platform's own separately-enforced fifth role
    -- CLAUDE.md, tools/hover_auditor_scope_gate.py (prevent) and
    tools/hover_separation_audit.py (detect) keep it from ever committing
    platform code at all, so it cannot be the session that authored the
    claim it is citing. That is the one place in this whole grading scheme
    where "independent" is a proven fact rather than an inference -- which
    is exactly why Level 3 is the only level this tool calls fully proven."""
    if hover_entries is None:
        return None
    for e in hover_entries:
        if _sha_in_ref(sha_full, e.get('ref', '')):
            return e
    return None


def find_self_reclaim(row, later_rows):
    """A LATER row (already claim-pattern-matched by scan() itself) whose
    'sabotage_files' intersects this row's, or None. DELIBERATELY REUSES
    CLAIM_PATTERNS RATHER THAN A NEW "re-run"/"confirmed"/"verified again"
    KEYWORD SEARCH -- this repo's own history already names the failure
    mode a fresh fuzzy-keyword pass would repeat: comment_quote_check.py
    exists because a probe asserting on a COMMENT instead of the code it
    describes is silent and self-flattering, and a "confirmed" keyword
    match has the identical shape -- it would fire on a commit that only
    SAYS a prior claim was confirmed, not one that re-ran anything. A
    second CLAIM_PATTERNS match is not perfect either (still text, not an
    executed control) but it is the one signal this file has already
    calibrated against real commits in both directions, rather than a new,
    unvetted one invented for this feature alone.

    WHAT THIS CANNOT TELL, STATED RATHER THAN IMPLIED AWAY: whether the
    later commit was authored by the SAME session as the original claim.
    Every commit on this platform is "Michael Dibert" with the same
    Claude co-author line regardless of which clone produced it, and
    nothing else in git metadata carries a session field. So a Level 2
    verdict means "a re-run happened", not "the claiming session re-ran
    its own work" -- the SLSA framing asked for that finer distinction and
    this repo's own git history does not carry the field that would let
    this tool draw it honestly. Reported as a known limit, not silently
    narrowed to fit."""
    for later in later_rows:
        if row['sabotage_files'] & later['sabotage_files']:
            return later
    return None


def grade_rows(rows, hover_entries):
    """Attaches 'level' (0-3), 'level_note' and 'discrepancy' (an
    independent-finding entry, or None) to every row IN PLACE, and returns
    rows. hover_entries=None (self-log unreadable) makes every CLEAR row's
    level 'UNKNOWN' rather than a guessed 1 -- see read_hover_log()."""
    for i, row in enumerate(rows):
        if not row['has_sabotage_file']:
            row['level'] = 0
            row['level_note'] = ''
            row['discrepancy'] = None
            continue
        hit = find_independent_reverification(row['sha_full'], hover_entries)
        if hit is not None and hit.get('type') == 'finding':
            row['level'] = 'DISCREPANCY'
            row['level_note'] = ('INDEPENDENT CHECK FOUND A DISCREPANCY -- '
                                  'hover_log #%s' % hit.get('seq', '?'))
            row['discrepancy'] = hit
            continue
        row['discrepancy'] = None
        if hit is not None:
            row['level'] = 3
            row['level_note'] = 'independently re-verified -- hover_log #%s' % hit.get('seq', '?')
            continue
        if hover_entries is None:
            row['level'] = 'UNKNOWN'
            row['level_note'] = 'self-log unreadable -- cannot rule out an independent check'
            continue
        later = find_self_reclaim(row, rows[i + 1:])
        if later is not None:
            row['level'] = 2
            row['level_note'] = 're-claimed in %s (session not attributable)' % later['sha']
            continue
        row['level'] = 1
        row['level_note'] = 'no re-run evidence found'
    return rows


def _print_report(rows, flagged_only=False, graded=True):
    flagged = [r for r in rows if not r['has_sabotage_file']]
    clear = [r for r in rows if r['has_sabotage_file']]
    if not flagged_only:
        print('SABOTAGE CLAIM VERIFY -- %d commit(s) claim a sabotage/mutation '
              'count, %d with no sabotage-named file in the SAME commit, %d clear'
              % (len(rows), len(flagged), len(clear)))
        print('"CLEAR" MEANS A PLAUSIBLE ARTIFACT WAS COMMITTED ALONGSIDE THE '
              'CLAIM, not that it was verified to implement the claimed count -- '
              'see the module docstring before treating a clear row as fully proven.')
        if graded:
            by_level = {}
            for r in clear:
                by_level.setdefault(r.get('level'), 0)
                by_level[r.get('level')] += 1
            discrepancies = [r for r in clear if r.get('discrepancy')]
            print('GRADED (SLSA-style): ' + ', '.join(
                '%s=%d' % (k, v) for k, v in sorted(by_level.items(), key=lambda kv: str(kv[0]))))
            if discrepancies:
                print('*** %d DISCREPANC%s FOUND BY AN INDEPENDENT CHECK -- read these first ***'
                      % (len(discrepancies), 'Y' if len(discrepancies) == 1 else 'IES'))
                for r in discrepancies:
                    print('  %s  %s' % (r['sha'], r['level_note']))
        print()
    print('FLAGGED (%d) -- claim, no matching artifact in this commit\'s own diff:' % len(flagged))
    for r in flagged:
        print('  %s  [%s]  %s' % (r['sha'], r['claim_text'], r['subject']))
    if not flagged_only:
        print()
        print('CLEAR (%d):' % len(clear))
        for r in clear:
            if graded:
                print('  %s  [%s]  %s  -- %s (%s)' % (
                    r['sha'], r['claim_text'], r['subject'],
                    LEVEL_LABEL.get(r.get('level'), 'LEVEL %s' % r.get('level')),
                    r.get('level_note', '')))
            else:
                print('  %s  [%s]  %s' % (r['sha'], r['claim_text'], r['subject']))


def run_fixtures():
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

    ck('"18 of 18 sabotages caught"',
       extract_claim('18 of 18 sabotages caught') is not None)
    ck('"9 of 9 valid sabotages caught"',
       extract_claim('9 of 9 valid sabotages caught') is not None)
    ck('"10 mutations ALL REFUSED"',
       extract_claim('10 mutations ALL REFUSED') is not None)
    ck('"13 mutations, all refused"',
       extract_claim('13 mutations, all refused') is not None)
    ck('"ALL 17 ARMS PASS"', extract_claim('ALL 17 ARMS PASS') is not None)
    ck('a mismatched count ("18 of 19") is NOT a claim -- the pattern is '
       'anchored on the SAME number twice, a real defect shape it should not '
       'itself manufacture a false claim out of',
       extract_claim('18 of 19 sabotages caught') is None)
    ck('ordinary prose with no claim shape returns None',
       extract_claim('this commit fixes a typo') is None)
    ck('extracted count is the real number, not a fixed placeholder',
       extract_claim('7 of 7 sabotages caught')[0] == '7')

    tmpdir = tempfile.mkdtemp()
    bare_repo = os.path.join(tmpdir, 'origin.git')
    work_repo = os.path.join(tmpdir, 'work')
    subprocess.run(['git', 'init', '-q', '--bare', bare_repo], check=True)
    subprocess.run(['git', 'init', '-q', work_repo], check=True)
    subprocess.run(['git', 'config', 'user.email', 'x@x.com'], cwd=work_repo, check=True)
    subprocess.run(['git', 'config', 'user.name', 'x'], cwd=work_repo, check=True)
    subprocess.run(['git', 'checkout', '-q', '-b', 'main'], cwd=work_repo, check=True)
    subprocess.run(['git', 'remote', 'add', 'origin', bare_repo], cwd=work_repo, check=True)

    def commit(files, message):
        for name, content in files.items():
            path = os.path.join(work_repo, name)
            d = os.path.dirname(path)
            if d and not os.path.isdir(d):
                os.makedirs(d)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        subprocess.run(['git', 'add', '.'], cwd=work_repo, check=True)
        subprocess.run(['git', 'commit', '-q', '-m', message], cwd=work_repo, check=True)
        return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=work_repo,
                               capture_output=True, text=True, check=True,
                               encoding='utf-8').stdout.strip()

    sha_bad1 = commit({'tests/run_cross_tenant_scope_probe.py': 'unrelated grader control'},
           'feat(isolation): the suite\n\n18 of 18 sabotages caught, all refused.')
    sha_l1 = commit({'tests/run_thing_sabotage_probe.py': 'real mutation runner'},
           'fix(thing): closes the finding\n\n9 of 9 sabotages caught, all refused.')
    sha_bad2 = commit({'docs/tier-a-reviews.json': '{}'},
           'review(x): discharge\n\nAlso flagged: rests on sabotage counts '
           'whose probes are not committed. 5 of 5 sabotages caught is prose only.')
    commit({'README.md': 'hello'}, 'docs: unrelated change with no claim')
    commit({'tests/run_other_sabotage_probe.py': 'v1'},
           'feat(other): first pass\n\n6 of 6 sabotages caught.')
    sha_l2_later = commit({'tests/run_other_sabotage_probe.py': 'v2, re-run after a refactor'},
           'chore(other): re-ran after the refactor\n\n6 of 6 sabotages caught, all refused.')
    sha_l3 = commit({'tests/run_thirdthing_sabotage_probe.py': 'v1'},
           'fix(thirdthing): closes the finding\n\n4 of 4 sabotages caught, all refused.')
    sha_disc = commit({'tests/run_fourththing_sabotage_probe.py': 'claims more than it drives'},
           'fix(fourththing): closes the finding\n\n11 of 11 sabotages caught, all refused.')

    subprocess.run(['git', 'push', '-q', 'origin', 'main'], cwd=work_repo, check=True)

    ck('scan() on a repo with no --repo/env/candidate refuses',
       _raises(NoRepo, scan, None))

    rows = scan(work_repo)
    ck('exactly 7 of 8 commits carry a recognised claim -- only the plain '
       'README commit has none', len(rows) == 7)
    by_subject = {r['subject']: r for r in rows}
    bad1 = by_subject.get('feat(isolation): the suite')
    good1 = by_subject.get('fix(thing): closes the finding')
    bad2 = by_subject.get('review(x): discharge')
    ck('the 5a878e71-shaped commit (claim, unrelated probe file) is FLAGGED',
       bad1 is not None and bad1['has_sabotage_file'] is False)
    ck('the fixed-commit-shaped one (claim, a real sabotage-named file) is CLEAR',
       good1 is not None and good1['has_sabotage_file'] is True)
    ck('the review-commit-shaped one (claim in prose, docs-only diff) is FLAGGED',
       bad2 is not None and bad2['has_sabotage_file'] is False)
    ck('oldest-first ordering holds', rows[0]['subject'] == 'feat(isolation): the suite')

    stale_clone = os.path.join(tmpdir, 'stale_clone')
    subprocess.run(['git', 'clone', '-q', bare_repo, stale_clone], check=True)
    subprocess.run(['git', 'checkout', '-q', '-b', 'main', 'origin/main'],
                    cwd=stale_clone, check=True)
    subprocess.run(['git', 'reset', '-q', '--hard', 'HEAD~2'], cwd=stale_clone, check=True)
    stale_local = subprocess.run(['git', 'log', '--oneline'], cwd=stale_clone,
                                  capture_output=True, text=True, check=True,
                                  encoding='utf-8', errors='replace').stdout
    ck('fixture precondition: the stale clone\'s own local log really is '
       'short by more than 2 commits', len(stale_local.splitlines()) < len(rows) + 2)
    stale_rows = scan(stale_clone)
    ck('THE STALE CLONE STILL SEES EVERY CLAIM COMMIT -- fetch+origin/main '
       'reads past its own out-of-date local HEAD, same fix as the other two '
       'tools', len(stale_rows) == len(rows))

    rows_by_sha = {r['sha_full']: r for r in rows}
    l1_row = rows_by_sha[sha_l1]
    l2_row = rows_by_sha.get(_find_sha_for_subject(rows, 'feat(other): first pass'))
    l3_row = rows_by_sha[sha_l3]
    disc_row = rows_by_sha[sha_disc]

    grade_rows(list(rows), None)
    fresh = scan(work_repo)
    grade_rows(fresh, None)
    fresh_by_sha = {r['sha_full']: r for r in fresh}
    ck('grading with an UNREADABLE self-log reports UNKNOWN, not a guessed Level 1',
       fresh_by_sha[sha_l1]['level'] == 'UNKNOWN')

    rows2 = scan(work_repo)
    grade_rows(rows2, [])
    rows2_by_sha = {r['sha_full']: r for r in rows2}
    ck('LEVEL 1: clear, no later re-claim, empty hover_log -> level 1',
       rows2_by_sha[sha_l1]['level'] == 1)
    l2_sha = _find_sha_for_subject(rows2, 'feat(other): first pass')
    ck('LEVEL 2: a later commit re-touches the same sabotage file and '
       're-asserts a claim -> level 2, and the level_note names the later sha',
       rows2_by_sha[l2_sha]['level'] == 2
       and sha_l2_later[:10] in rows2_by_sha[l2_sha]['level_note'])
    ck('the LATER (re-claiming) commit itself is graded on its OWN merits, '
       'not just credited as evidence for the earlier one -- it has no '
       'further re-claim after it, so it is Level 1 itself',
       rows2_by_sha[sha_l2_later]['level'] == 1)

    fake_log_l3 = [{'seq': 999, 'type': 'check', 'ref': sha_l3[:10],
                     'summary': 'fixture: re-verified'}]
    rows3 = scan(work_repo)
    grade_rows(rows3, fake_log_l3)
    rows3_by_sha = {r['sha_full']: r for r in rows3}
    ck('LEVEL 3: a hover_log `check` entry citing the sha -> level 3, '
       'independent by construction',
       rows3_by_sha[sha_l3]['level'] == 3
       and rows3_by_sha[sha_l3]['discrepancy'] is None)
    ck('a SHORT ref (10 hex chars) still matches the FULL 40-char sha -- '
       'prefix match, not exact-string match',
       _sha_in_ref(sha_l3, sha_l3[:10]) and not _sha_in_ref(sha_l3, sha_disc[:10]))

    fake_log_disc = [{'seq': 1000, 'type': 'finding', 'ref': sha_disc[:10],
                       'summary': 'fixture: independent check found a real gap'}]
    rows4 = scan(work_repo)
    grade_rows(rows4, fake_log_disc)
    rows4_by_sha = {r['sha_full']: r for r in rows4}
    ck('DISCREPANCY: a hover_log `finding` entry citing the sha is NEVER '
       'reported as a numbered level -- level is the DISCREPANCY sentinel, '
       'not 3, discrepancy is populated, and the note says so',
       rows4_by_sha[sha_disc]['level'] == 'DISCREPANCY'
       and rows4_by_sha[sha_disc]['discrepancy'] is not None
       and 'DISCREPANCY' in rows4_by_sha[sha_disc]['level_note'])

    rows5 = scan(work_repo)
    fake_log_bad1 = [{'seq': 1001, 'type': 'check', 'ref': sha_bad1[:10]}]
    grade_rows(rows5, fake_log_bad1)
    rows5_by_sha = {r['sha_full']: r for r in rows5}
    ck('LEVEL 0 cannot be promoted by a hover_log citation -- no artifact '
       'means no artifact, regardless of who looked',
       rows5_by_sha[sha_bad1]['level'] == 0)

    good_log_path = os.path.join(tmpdir, 'good_log.jsonl')
    with open(good_log_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'seq': 1, 'type': 'check', 'ref': 'abc123'}) + '\n')
        f.write(json.dumps({'seq': 2, 'type': 'finding', 'ref': 'def456'}) + '\n')
    entries = read_hover_log(good_log_path)
    ck('read_hover_log() on a real, valid file returns the real entries',
       entries is not None and len(entries) == 2 and entries[0]['seq'] == 1)
    ck('read_hover_log() on a MISSING file returns None, not []',
       read_hover_log(os.path.join(tmpdir, 'does_not_exist.jsonl')) is None)
    bad_log_path = os.path.join(tmpdir, 'bad_log.jsonl')
    with open(bad_log_path, 'w', encoding='utf-8') as f:
        f.write('not json at all\n')
    ck('read_hover_log() on an UNPARSABLE file returns None, not a crash '
       'and not a silent empty list',
       read_hover_log(bad_log_path) is None)

    print()
    print('%d ok, %d failed' % (ok_count[0], fail_count[0]))
    return fail_count[0] == 0


def _find_sha_for_subject(rows, subject):
    for r in rows:
        if r['subject'] == subject:
            return r['sha_full']
    return None


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
    flagged_only = '--flagged-only' in argv
    graded = '--no-grade' not in argv
    since = None
    if '--since' in argv:
        i = argv.index('--since')
        if i + 1 < len(argv):
            since = argv[i + 1]
    hover_log_path = None
    if '--hover-log' in argv:
        i = argv.index('--hover-log')
        if i + 1 < len(argv):
            hover_log_path = argv[i + 1]
    repo = discover_repo(argv)
    try:
        rows = scan(repo, since=since)
    except NoRepo as e:
        print('COULD NOT RUN: %s' % e)
        return 2
    if graded:
        hover_entries = read_hover_log(hover_log_path)
        if hover_entries is None:
            print('NOTE: this role\'s own self-log (%s) could not be read -- '
                  'every CLEAR row grades as UNKNOWN rather than a guessed '
                  'Level 1. Run with --no-grade for the plain binary report.'
                  % (hover_log_path or HOVER_LOG_PATH))
            print()
        grade_rows(rows, hover_entries)
    _print_report(rows, flagged_only=flagged_only, graded=graded)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
