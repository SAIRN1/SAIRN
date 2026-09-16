#!/usr/bin/env python
r"""register_feed_gate.py -- a defect closure cannot complete without feeding
the register. Item 41's prevent-by-construction pattern, applied to the
measurement substrate instead of to a ledger entry.

    python tools/register_feed_gate.py --pre-push     # hook entry, DENIES
    python tools/register_feed_gate.py --backlog      # the historical gap
    python tools/register_feed_gate.py --self-check

── THE ROOT CAUSE THIS EXISTS FOR, FOUND FIVE TIMES IN ONE DAY ─────────────
Every one of these is a tool that reports a vacuous number because nobody feeds
its input, and each was diagnosed independently before the pattern was named:

  item 4   the FMEA loop scored 0% -- `every draft postdates every defect`.
           The register's newest record was 2026-09-14 while 2026-09-15
           produced a long list of fixed defects, including an isolation race
           on attorney trust money.
  item 23  the claim-provenance chain: THREE records, all by one author, all
           written within 24 seconds of each other, untouched for 36 hours.
  item 62  spread-skill calibration: no paired reviewer verdicts exist at all.
  item 68  Cohen's kappa: same missing input, one level down.
  item 99  graduated consent, in its own document's words -- "stated and
           UNENFORCEABLE, because the fact it depends on is not recorded".

A RECORDING TOOL WITH NO STRUCTURAL REQUIREMENT THAT REAL ACTIVITY FEEDS IT
WILL REPORT A VACUOUS NUMBER FOREVER, however much real work is happening. The
fix is not another reminder. It is to put the requirement where the work
already has to pass.

── MEASURED BEFORE IT WAS DESIGNED, WHICH DECIDED THE SHAPE ────────────────
66 `fix(` commits touching code since 2026-09-13. **62 of them cite no register
record.** A gate that refused all of those would refuse essentially every push
on the platform, and a wall produces overrides -- which this repo already
records costing more than the gate saved.

So it carries a REQUIREMENT DATE and applies only to commits from that date
forward. That is not a softening invented here: it is the same mechanism
`tools/first_article_check.py` uses for exactly the same problem -- introducing
a mandatory record without retroactively blocking work that predates the rule.
**The 62 are not forgiven, they are REPORTED** by `--backlog`, so the gap stays
visible instead of being cleared by a date.

── THE ESCAPE HATCH, AND WHY THERE HAS TO BE ONE ───────────────────────────
Not every `fix(` is a defect in shipped behaviour. A gate with no honest way to
say so is a gate people learn to word their commit subjects around, and then it
measures nothing while looking strict.

    no-defect-record: <reason>

as a commit trailer, with a real sentence. THE REASON IS MANDATORY AND IS
CHECKED FOR LENGTH, the same decision `defect_register.py` made for
`not-citable`: a vocabulary with no honest escape hatch does not produce
honesty, it produces a forced value, and a bare refusal with no note is the
thing that makes the field meaningless.

── WHICH WAY IT FAILS ──────────────────────────────────────────────────────
If the register cannot be read or parsed, THE PUSH IS DENIED. A gate whose
input is missing has not checked anything, and "could not tell" is never folded
into "passed" (PR SS1.11). That is the whole subject of this file.
"""

import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, 'docs', 'defect-density-register.json')

# ── THE REQUIREMENT DATE ────────────────────────────────────────────────────
# Commits authored BEFORE this are reported by --backlog and never block. Set
# once, to the day this shipped. Moving it forward would forgive a gap rather
# than close one, and an arm asserts it has not moved.
REQUIREMENT_DATE = '2026-09-16'

# A fix to prose is not a defect closure in shipped behaviour. NARROW ON
# PURPOSE AND STATED ON EVERY RUN: a silent exclusion reads as "covered
# everything" when it did not.
CODE_PREFIXES = ('api/', 'sql/', 'tools/', 'tests/')
CODE_SUFFIXES = ('.html', '.js', '.py', '.sql')
FIX_RE = re.compile(r'^fix\(', re.I)
ESCAPE_RE = re.compile(r'^no-defect-record:\s*(.+)$', re.I | re.M)
MIN_REASON = 30

# ── THE SUBJECT IS NOT THE CHANGE, AND ON 2026-09-16 THAT WAS PROVED ───────
# Everything above keys on the SUBJECT. `a8528025` is on origin/main carrying
# `chore(register): arm 7 attributed somebody else's edits to the probe` -- a
# message written for a 50-line append to docs/defect-density-register.json --
# and its actual content is a 232s-to-25s performance fix to
# tools/retry_backoff_check.py plus three REGISTRY entries. FIX_RE did not
# match, so this gate never asked, and no record cites it. A real fix is on
# origin/main unrecorded.
#
# THE DOCSTRING ABOVE ALREADY ANTICIPATED THE DELIBERATE VERSION -- "a gate
# people learn to word their commit subjects around". What it did not
# anticipate is that a rebase can do it BY ACCIDENT, to somebody who was not
# trying, and that is what happened: author date 10:48:38, commit date
# 10:57:53, and another session held a claim for "rebase resolve semantic merge
# for the two json registers" four minutes earlier.
#
# ── WHAT A CONTENT CHECK CAN AND CANNOT DO, MEASURED BEFORE IT WAS BUILT ───
# "Does this diff fix a defect" is NOT mechanically decidable, and the honest
# thing is to say so rather than ship a classifier that guesses. Two content
# rules were measured against 807 real commits since 2026-09-13 before this one
# was chosen:
#
#   chore/docs touching code files            27 hits -- 6 of them my own
#                                             docs(tracing) comment additions
#   ...restricted to EXECUTABLE line changes  20 hits -- MIN_TEST_FILES bumps,
#                                             inventory rows, REGISTRY entries;
#                                             almost all honest chore work
#
# A gate that fires twenty times to catch one is a gate people switch off, which
# this file's own header says in as many words. Both were rejected.
#
# ── THE RULE THAT WAS KEPT, AND WHY IT IS PRECISE ─────────────────────────
# A REUSED MESSAGE leaves a signature: two commits with a BYTE-IDENTICAL
# subject whose FILE SETS DO NOT INTERSECT AT ALL. Measured over the same 807
# commits: 1,293 duplicate-subject pairs overlap in files and are not flagged --
# `chore(claims): cc releases cc` repeats by design and always touches its one
# claim file -- and exactly THREE pairs are disjoint. All three are real message
# reuse, including a8528025 and a `chore(claims)` commit whose content is a
# MASTER-PLAN regeneration rather than a claim.
#
# THREE IN EIGHT HUNDRED, AND ALL THREE TRUE. That is a signal worth blocking
# on. It closes the ACCIDENTAL bypass -- the one that actually happened and
# that nobody had anticipated. It does NOT close the deliberate one: a unique,
# honestly-typed, wrong subject still passes, and the escape hatch plus a human
# reader are what that rests on. Said here rather than left to be discovered.
SUBJECT_REUSE_DAYS = 14
REUSE_ESCAPE_RE = re.compile(r'^subject-reuse:\s*(.+)$', re.I | re.M)

EXIT_OK, EXIT_DENY, EXIT_COULD_NOT_RUN = 0, 1, 2


def git(*args):
    r = subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.returncode, r.stdout, r.stderr


def cited_commits():
    """The set of 8-char shas any register record cites. (set, problem)."""
    try:
        d = json.load(io.open(REGISTER, encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return None, '%s could not be read: %s' % (REGISTER, exc)
    recs = d['records'] if isinstance(d, dict) and 'records' in d else d
    if not isinstance(recs, list):
        return None, '%s does not contain a record list' % REGISTER
    out = set()
    for r in recs:
        c = (r.get('commit') or '').strip()
        if c:
            out.add(c[:8])
    return out, ''


def touches_code(sha):
    code, out, _e = git('show', '--name-only', '--format=', sha)
    if code != 0:
        return None
    files = [f.strip().replace('\\', '/') for f in out.split('\n') if f.strip()]
    return [f for f in files
            if f.startswith(CODE_PREFIXES) or f.endswith(CODE_SUFFIXES)]


def commits_in(rng):
    """[(sha, date, subject, body)] for a range. None on failure."""
    code, out, _e = git('log', '--format=%H%x1f%ad%x1f%s%x1f%b%x1e',
                        '--date=short', rng)
    if code != 0:
        return None
    rows = []
    for chunk in out.split('\x1e'):
        chunk = chunk.strip('\n')
        if not chunk.strip():
            continue
        parts = chunk.split('\x1f')
        if len(parts) < 4:
            return None
        rows.append((parts[0], parts[1], parts[2], parts[3]))
    return rows


def judge(rows, cited):
    """(owed, escaped, backlog). Pure -- the half worth testing exhaustively."""
    owed, escaped, backlog = [], [], []
    for sha, date, subject, body in rows:
        if not FIX_RE.match(subject):
            continue
        files = touches_code(sha)
        if files is None:
            owed.append((sha, date, subject, 'the file list could not be read'))
            continue
        if not files:
            continue
        if date < REQUIREMENT_DATE:
            if sha[:8] not in cited:
                backlog.append((sha[:8], date, subject))
            continue
        if sha[:8] in cited:
            continue
        m = ESCAPE_RE.search(body or '')
        if m and len(m.group(1).strip()) >= MIN_REASON:
            escaped.append((sha[:8], date, subject, m.group(1).strip()))
            continue
        if m:
            owed.append((sha[:8], date, subject,
                         'a no-defect-record trailer with only %d characters of '
                         'reason; %d are required, because a bare refusal is what '
                         'makes the field meaningless'
                         % (len(m.group(1).strip()), MIN_REASON)))
            continue
        owed.append((sha[:8], date, subject, 'no register record cites it'))
    return owed, escaped, backlog


def subject_file_index(days):
    """{subject: [(sha, frozenset(files))]} over a bounded window. None on
    failure.

    ONE `git log` call, not one per commit. The per-commit version needed ~800
    subprocesses over this window, which is not a thing to put in front of a
    push behind a 150-second timeout.

    THE WINDOW IS BOUNDED AND IS PRINTED ON EVERY RUN (PR 1.7). A reused
    message older than the window is invisible here, and a sampling window that
    does not say what it did not look at reads as "checked everything".
    """
    code, out, _e = git('log', '--since=%d days ago' % days, '--no-renames',
                        '--name-only', '--format=%x1e%H%x1f%s')
    if code != 0:
        return None
    index = {}
    for chunk in out.split('\x1e'):
        if not chunk.strip():
            continue
        head, _, rest = chunk.partition('\n')
        if '\x1f' not in head:
            continue
        sha, _, subject = head.partition('\x1f')
        files = frozenset(f.strip().replace('\\', '/')
                          for f in rest.split('\n') if f.strip())
        index.setdefault(subject, []).append((sha.strip(), files))
    return index


def judge_subject_reuse(rows, index):
    """[(sha, subject, other_sha)] for outgoing commits wearing a message that
    an earlier commit already used on a DISJOINT set of files.

    Pure given the index, which is the half worth driving from a rule table.
    """
    out = []
    for sha, _date, subject, body in rows:
        m = REUSE_ESCAPE_RE.search(body or '')
        if m and len(m.group(1).strip()) >= MIN_REASON:
            continue
        mine = None
        for s, files in index.get(subject, []):
            if s == sha:
                mine = files
                break
        if mine is None:
            continue
        for s, files in index.get(subject, []):
            if s == sha:
                continue
            # An EMPTY file set is a merge commit or an empty commit; it
            # intersects nothing by definition and would flag every pair it is
            # in. Not a reused message, so not judged.
            if not files or not mine:
                continue
            if not (files & mine):
                out.append((sha[:8], subject, s[:8]))
                break
    return out


def outgoing_range(stdin_text):
    """The range a pre-push hook is being asked about. (rng, problem)."""
    ZERO = '0' * 40
    lines = [l for l in (stdin_text or '').split('\n') if l.strip()]
    if not lines:
        return None, 'no ref lines on stdin -- cannot tell what is being pushed'
    for line in lines:
        parts = line.split()
        if len(parts) < 4:
            return None, 'unparseable pre-push ref line: %r' % line
        _lref, lsha, _rref, rsha = parts[:4]
        if lsha == ZERO:
            continue
        return (lsha if rsha == ZERO else '%s..%s' % (rsha, lsha)), ''
    return None, ''          # deletes only; nothing to check



# -- RISK SEQUENCING FOR THE BACKLOG ----------------------------------------
# 422 unrecorded closures cannot be worked in commit order, and working them in
# ANY order without a stated rule is how the easy ones get done and the
# trust-money one stays open. The bands are read from
# docs/CRITICALITY-TIERS.md's own "what goes wrong" column rather than from a
# list invented here: the register already treats that document as the
# authority on what Tier A means, and a second opinion about criticality is the
# thing that produces two.
#
# BAND 1 IS NOT SIMPLY "TIER A" -- it is Tier A SPLIT BY WHAT THE ROW SAYS GOES
# WRONG, because the queue's whole purpose is that the sharpest end is worked
# first:
#   1a  MONEY or REGULATED   trust accounts, controlled substances, billing
#   1b  PII / PHI            patient, member and employee records
#   1c  other Tier A
# BAND 2 is server-side code touching no Tier A resource; BAND 3 is tooling and
# tests. A commit lands in the HIGHEST band any of its files reaches.
RISK_WORDS = (
    ('1a', ('money', 'regulated', 'dea', 'iolta', 'controlled', 'trust')),
    ('1b', ('phi', 'pii', 'patient', 'medical', 'personal')),
)
TIER_A_ROW = re.compile(
    r'^\|\s*`(\w+)`\s*\|\s*\*\*A\*\*\s*\|([^|]*)\|([^|]*)', re.M)
REST_PATH = re.compile(r"(?:/rest/v1/|rest\(\s*['\"])(\w+)")


def tier_a_bands():
    """{resource: band} read from the tiers document. (dict, problem)."""
    path = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')
    try:
        src = io.open(path, encoding='utf-8').read()
    except OSError as exc:
        return None, str(exc)
    rows = {}
    for m in TIER_A_ROW.finditer(src):
        blob = (m.group(2) + ' ' + m.group(3)).lower()
        band = '1c'
        for b, words in RISK_WORDS:
            if any(w in blob for w in words):
                band = b
                break
        rows[m.group(1)] = band
    return rows, ''


def by_risk(cited, want_band=None, want_limit=25):
    bands, problem = tier_a_bands()
    if bands is None:
        print('COULD NOT RUN: the tiers document is unreadable (%s), so no '
              'commit can be banded -- and an unbanded queue is not a queue.'
              % problem)
        return EXIT_COULD_NOT_RUN
    rows = commits_in('--all')
    if rows is None:
        print('COULD NOT RUN: git log failed')
        return EXIT_COULD_NOT_RUN
    _o, _e, backlog = judge(rows, cited)
    out = []
    # ── BAND BY THE DIFF, NOT BY THE FILE, AND THE FIRST VERSION GOT THIS
    # ── WRONG IN THE WORST POSSIBLE DIRECTION.
    # Scanning each changed FILE for Tier A resource names put 54 commits in
    # band 1a, every one of them reporting the identical three resources --
    # because `api/sd-data.js` addresses EVERY resource on the platform and
    # nearly every fix touches it. The band was therefore a property of one
    # file's size, not of the change.
    #
    # A SEQUENCER THAT PUTS EVERYTHING IN THE TOP BAND IS WORSE THAN NO
    # SEQUENCER: it looks like a priority order and is a fabricated one, which
    # is the defect this repo polices hardest. Only ADDED and REMOVED lines are
    # read now, so the band reflects what the commit actually changed.
    for sha, date, subject in backlog:
        code, diff, _e2 = git('show', '--format=', '--unified=0', sha)
        band, hits = '3', set()
        if code == 0:
            for line in diff.split(chr(10)):
                if line.startswith('+++ ') or line.startswith('--- '):
                    continue
                if line.startswith('diff --git'):
                    for f in line.split():
                        if f.startswith(('a/api/', 'b/api/', 'a/sql/', 'b/sql/')) \
                                and band == '3':
                            band = '2'
                    continue
                if not line[:1] in ('+', '-'):
                    continue
                for r in set(REST_PATH.findall(line)) & set(bands):
                    hits.add(r)
        if hits:
            band = min(bands[r] for r in hits)
        out.append((band, date, sha, subject, sorted(hits)[:3]))
    out.sort(key=lambda r: (r[0], r[1]))
    counts = {}
    for r in out:
        counts[r[0]] = counts.get(r[0], 0) + 1
    print('DEFECT-REGISTER BACKLOG, SEQUENCED BY REAL RISK')
    print('  %d unrecorded closures before %s' % (len(out), REQUIREMENT_DATE))
    for b, label in (('1a', 'Tier A -- MONEY or REGULATED'),
                     ('1b', 'Tier A -- PII / PHI'),
                     ('1c', 'Tier A -- other'),
                     ('2', 'server-side, no Tier A resource'),
                     ('3', 'tooling and tests')):
        print('    band %-3s %-34s %d' % (b, label, counts.get(b, 0)))
    print('')
    print('  A COMMIT LANDS IN THE HIGHEST BAND ANY OF ITS FILES REACHES, and')
    print('  the band comes from the tiers document rather than from a list')
    print('  invented here.')
    print('')
    # ── A BOUNDED WINDOW INTO A BAND (added 2026-09-15) ────────────────────
    # Bands 2 and 3 are still not printed in full and the reason below stands.
    # But a queue nobody can SEE is not a queue either, and band 1 being clear
    # made band 2 the head with no way to read it. `--band N --limit M` prints
    # a bounded slice, oldest first, so a session can take a shift off the
    # front without anybody pasting a 400-line list into a report.
    if want_band:
        slice_ = [r for r in out if r[0] == want_band][:want_limit]
        print('  BAND %s, OLDEST %d OF %d -- a bounded window, not the queue.'
              % (want_band, len(slice_), counts.get(want_band, 0)))
        print('  Taking a shift off the front is the intended use. Registering')
        print('  all %d in one pass is how a queue becomes a wall, which is the'
              % counts.get(want_band, 0))
        print('  argument this tool already makes about printing them.')
        print('')
        for b, date, sha, subject, hits in slice_:
            print('  %-3s %s  %s  %s' % (b, date, sha, subject[:60]))
        print('')
        return EXIT_OK

    for b, date, sha, subject, hits in out:
        if b.startswith('1'):
            print('  %-3s %s  %s  %s' % (b, date, sha, subject[:52]))
            if hits:
                print('        via %s' % ', '.join(hits))
    print('')
    print('  ONLY THE TIER A BANDS ARE PRINTED. Bands 2 and 3 are counted above')
    print('  and deliberately not listed: a 400-line list nobody reads is how a')
    print('  queue becomes a wall.')
    print('')
    print('  WHAT THIS CANNOT SEE, and it is the same limit the gate checker')
    print('  self-reported: a file addressing its table any way OTHER than a')
    print('  /rest/v1/ or rest() path -- a variable, a helper, a generic')
    print('  dispatcher, an RPC. That UNDER-bands rather than over-bands, so a')
    print('  band-1 list is a FLOOR and band 2 is not a clearance.')
    return EXIT_OK


def deny(owed, escaped):
    print('')
    print('Blocked: this push closes a defect and does not feed the register.')
    print('')
    print('A RECORDING TOOL NOBODY FEEDS REPORTS A VACUOUS NUMBER FOREVER. That')
    print('was diagnosed five separate times on 2026-09-15 -- the FMEA loop at')
    print('0%%, the provenance chain at three records by one author, spread-skill')
    print('and kappa with no paired verdicts at all, and item 99 calling its own')
    print('rule "stated and UNENFORCEABLE, because the fact it depends on is not')
    print('recorded". This is the requirement moved to where the work already')
    print('has to pass.')
    print('')
    for sha, date, subject, why in owed:
        print('  %s  %s  %s' % (sha, date, subject[:62]))
        print('      %s' % why)
    print('')
    print('  Record it:')
    print('    python tools/defect_register.py --add --commit <sha> ...')
    print('  (--help lists the required fields; it refuses a record it cannot')
    print('   check, which is why this gate can rely on one existing.)')
    print('')
    print('  OR, if this fix is genuinely not a defect in shipped behaviour,')
    print('  say so IN THE COMMIT with a real sentence:')
    print('')
    print('    no-defect-record: <at least %d characters saying why>' % MIN_REASON)
    print('')
    print('  A bare refusal is refused. That is the same decision the register')
    print('  itself made for `not-citable`: an escape hatch with no note does')
    print('  not produce honesty, it produces a field that means nothing.')
    if escaped:
        print('')
        print('  Accepted on this push via the trailer (%d):' % len(escaped))
        for sha, _d, subject, why in escaped:
            print('    %s %s -- %s' % (sha, subject[:44], why[:70]))
    print('')
    print('Override by putting SAIRN_SEED_GATE=off at the FRONT of the push '
          'command itself (SAIRN_SEED_GATE=off git push ...), not in a separate '
          'export. Say so out loud if you do.')
    return EXIT_DENY


def main(argv):
    if '--self-check' in argv:
        return self_check()

    cited, problem = cited_commits()
    if cited is None:
        if '--backlog' in argv:
            print('COULD NOT RUN: %s' % problem)
            return EXIT_COULD_NOT_RUN
        print('')
        print('Blocked: the defect register could not be read, so this gate has')
        print('checked NOTHING.')
        print('  %s' % problem)
        print('')
        print('Denying rather than passing. A gate whose input is missing has not')
        print('checked anything, and "could not tell" is never folded into')
        print('"passed" -- which is the entire subject of this gate.')
        return EXIT_COULD_NOT_RUN

    if '--by-risk' in argv:
        band = limit = None
        if '--band' in argv:
            i = argv.index('--band')
            band = argv[i + 1] if len(argv) > i + 1 else None
            if band not in ('1a', '1b', '1c', '2', '3'):
                sys.stderr.write('--band takes 1a, 1b, 1c, 2 or 3\n')
                return EXIT_COULD_NOT_RUN
            limit = 25
            if '--limit' in argv:
                j = argv.index('--limit')
                if len(argv) > j + 1 and argv[j + 1].isdigit():
                    limit = int(argv[j + 1])
        return by_risk(cited, band, limit)

    if '--backlog' in argv:
        rows = commits_in('--all')
        if rows is None:
            print('COULD NOT RUN: git log failed')
            return EXIT_COULD_NOT_RUN
        owed, escaped, backlog = judge(rows, cited)
        print('DEFECT-REGISTER FEED BACKLOG')
        print('  requirement date : %s (commits before it never block)' % REQUIREMENT_DATE)
        print('  register records : %d, citing %d distinct commits'
              % (len(cited), len(cited)))
        print('  fix() commits touching code BEFORE the requirement date with no')
        print('  record: %d' % len(backlog))
        print('')
        print('  THESE ARE NOT FORGIVEN BY THE DATE, THEY ARE REPORTED BY IT.')
        print('  Measured 2026-09-15 before this gate was designed: 66 such')
        print('  commits since 2026-09-13 and 62 with no record. A gate that')
        print('  refused all of them would refuse essentially every push, and a')
        print('  wall produces overrides.')
        for sha, date, subject in backlog[:25]:
            print('    %s  %s  %s' % (sha, date, subject[:62]))
        if len(backlog) > 25:
            print('    ... and %d more' % (len(backlog) - 25))
        print('')
        print('  SCOPE, STATED RATHER THAN IMPLIED: only `fix(` subjects, and only')
        print('  commits touching %s or *%s.'
              % (', '.join(CODE_PREFIXES), ', *'.join(CODE_SUFFIXES)))
        print('  A defect closed under a different subject prefix is invisible to')
        print('  this, and that is a real limit rather than a filter.')
        return EXIT_OK

    if '--pre-push' not in argv:
        print(__doc__)
        return EXIT_COULD_NOT_RUN

    stdin_text = '' if sys.stdin.isatty() else sys.stdin.read()
    rng, problem = outgoing_range(stdin_text)
    if rng is None and problem:
        print('')
        print('Blocked: this gate could not tell what is being pushed.')
        print('  %s' % problem)
        print('')
        print('Denying rather than passing, for the same reason as above.')
        return EXIT_COULD_NOT_RUN
    if rng is None:
        return EXIT_OK

    rows = commits_in(rng)
    if rows is None:
        print('')
        print('Blocked: the outgoing range %s could not be read.' % rng)
        return EXIT_COULD_NOT_RUN

    owed, escaped, _backlog = judge(rows, cited)
    if owed:
        return deny(owed, escaped)

    # ── THE CONTENT HALF ────────────────────────────────────────────────────
    index = subject_file_index(SUBJECT_REUSE_DAYS)
    if index is None:
        print('')
        print('Blocked: the subject-reuse window could not be read, so whether a')
        print('commit in this push wears another commit\'s message is UNKNOWN.')
        print('')
        print('That is the check whose absence let a real fix reach origin/main')
        print('unrecorded on 2026-09-16, so it refuses rather than passing.')
        return EXIT_COULD_NOT_RUN
    reused = judge_subject_reuse(rows, index)
    if reused:
        print('')
        print('Blocked: a commit in this push wears a message ANOTHER commit already')
        print('used, on a completely different set of files.')
        print('')
        for sha, subject, other in reused:
            print('  %s  %s' % (sha, subject[:66]))
            print('      the same subject is already on %s, and the two share NO file'
                  % other)
        print('')
        print('THIS IS WHAT A REBASE OR AN --amend LOOKS LIKE WHEN IT PUTS THE WRONG')
        print('MESSAGE ON A CHANGESET. It matters here because every other check in')
        print('this gate reads the SUBJECT: on 2026-09-16 a8528025 reached origin/main')
        print('wearing a chore(register) message while containing a real performance')
        print('fix, so nothing asked it for a defect record and none cites it.')
        print('')
        print('THE FIX IS USUALLY TO REWORD THE SUBJECT so it describes the change.')
        print('If the reuse is deliberate and correct, say so as a trailer with a real')
        print('sentence -- at least %d characters:' % MIN_REASON)
        print('')
        print('    subject-reuse: <why these are genuinely the same change>')
        print('')
        print('WINDOW: the last %d days. A reused message older than that is not'
              % SUBJECT_REUSE_DAYS)
        print('visible to this check, which is stated rather than implied.')
        return EXIT_DENY
    return EXIT_OK


# ── the rule table, proved before it is applied ─────────────────────────────
CASES = [
    ('a fix after the date with a record', 'fix(x): y', '2026-09-20', True, '', 'ok'),
    ('a fix after the date with NO record', 'fix(x): y', '2026-09-20', False, '', 'owed'),
    ('...with a REAL trailer', 'fix(x): y', '2026-09-20', False,
     'no-defect-record: a comment typo in a header, nothing shipped changed at all',
     'escaped'),
    ('...with a BARE trailer', 'fix(x): y', '2026-09-20', False,
     'no-defect-record: typo', 'owed'),
    ('a fix BEFORE the date with no record', 'fix(x): y', '2026-09-10', False, '', 'backlog'),
    ('a non-fix commit after the date', 'feat(x): y', '2026-09-20', False, '', 'ok'),
    ('a chore after the date', 'chore(x): y', '2026-09-20', False, '', 'ok'),
]


# The subject-reuse half, driven with no repository at all. Every case is a
# hand-built index, and the two CONTROL cases are the ones that matter: a gate
# that flagged every duplicate subject would satisfy the positives alone, and
# `chore(claims): cc releases cc` repeats 19 times in a fortnight by design.
REUSE_CASES = [
    ('a unique subject', 'fix(x): y', '', {'fix(x): y': [('a' * 40, {'api/x.js'})]}, False),
    ('the same subject, OVERLAPPING files -- a repeat by design',
     'chore(claims): cc releases cc', '',
     {'chore(claims): cc releases cc': [('a' * 40, {'.claude/claims/cc.json'}),
                                        ('b' * 40, {'.claude/claims/cc.json'})]}, False),
    ('the same subject, DISJOINT files -- a reused message',
     'chore(register): x', '',
     {'chore(register): x': [('a' * 40, {'tools/retry_backoff_check.py'}),
                             ('b' * 40, {'docs/defect-density-register.json'})]}, True),
    ('...and a real trailer excuses it',
     'chore(register): x',
     'subject-reuse: the register append and its regenerated document, split only '
     'because the push gate demands two commits',
     {'chore(register): x': [('a' * 40, {'tools/retry_backoff_check.py'}),
                             ('b' * 40, {'docs/defect-density-register.json'})]}, False),
    ('...and a BARE trailer does not',
     'chore(register): x', 'subject-reuse: same thing',
     {'chore(register): x': [('a' * 40, {'tools/retry_backoff_check.py'}),
                             ('b' * 40, {'docs/defect-density-register.json'})]}, True),
    ('an EMPTY file set is a merge, not a reused message',
     'chore(x): y', '',
     {'chore(x): y': [('a' * 40, {'api/x.js'}), ('b' * 40, set())]}, False),
    ('a subject the index does not know -- nothing to compare against',
     'fix(z): unseen', '', {}, False),
]


def self_check():
    bad = []
    for label, subject, body, index, want in REUSE_CASES:
        idx = dict((k, [(s, frozenset(f)) for s, f in v]) for k, v in index.items())
        got = bool(judge_subject_reuse([('a' * 40, '2026-09-20', subject, body)], idx))
        print('    %-58s -> %-7s %s'
              % (label, 'FLAGGED' if got else 'clean',
                 'ok' if got == want else 'EXPECTED ' + ('FLAGGED' if want else 'clean')))
        if got != want:
            bad.append((label, got, want))
    print('')
    print('    subject-reuse window: %d days' % SUBJECT_REUSE_DAYS)
    print('')
    for label, subject, date, has_record, body, want in CASES:
        sha = 'a' * 40
        cited = {sha[:8]} if has_record else set()
        # touches_code is the only impure call in judge(); stub it so the rule
        # table is driven with no repository at all.
        real = globals()['touches_code']
        globals()['touches_code'] = lambda _s: ['api/x.js']
        try:
            owed, escaped, backlog = judge([(sha, date, subject, body)], cited)
        finally:
            globals()['touches_code'] = real
        got = ('owed' if owed else 'escaped' if escaped
               else 'backlog' if backlog else 'ok')
        print('    %-42s -> %-9s %s'
              % (label, got, 'ok' if got == want else 'EXPECTED ' + want))
        if got != want:
            bad.append((label, got, want))
    # The date must not drift forward: moving it forgives a gap rather than
    # closing one.
    print('')
    print('    requirement date: %s' % REQUIREMENT_DATE)
    if REQUIREMENT_DATE != '2026-09-16':
        bad.append(('requirement date moved', REQUIREMENT_DATE, '2026-09-16'))
        print('    ! THE REQUIREMENT DATE HAS MOVED. Moving it forward forgives')
        print('      every commit in between rather than closing the gap.')
    print('\n%d case(s) wrong' % len(bad))
    return EXIT_OK if not bad else EXIT_DENY


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
