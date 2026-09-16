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


def self_check():
    bad = []
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
