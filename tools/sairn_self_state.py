"""sairn_self_state.py -- what is THIS session's real current state, derived.

    python tools/sairn_self_state.py                # this clone, last 7 days
    python tools/sairn_self_state.py --days 14
    python tools/sairn_self_state.py --session cc   # somebody else's, read-only
    python tools/sairn_self_state.py --json
    python tools/sairn_self_state.py --self-check

Exit 0 when nothing needs attention, 1 when something does, 2 when a source
could not be read -- never folded into either of the others (PR 1.11).

── WHY A TOOL AND NOT A SUMMARY ────────────────────────────────────────────
The weekly reconciliation this exists for has been done in prose, and prose is
where the platform's recorded failures live: a work queue naming an item number
that was in no registry; an index row asserting zero active owners while a live
read showed two; a clone registry that said "Four clones" for weeks after a
fifth was pushing; my own `_not_a_blanket_sweep` sentence claiming every file
was judged, two days after it stopped being true. Every one of those was a
person writing down a true thing and the thing then changing.

So this reads the SOURCES, every run:

    git log / git status           what actually landed, and what has not
    tools/sairn_claim.py           what this session told the others it is on
    tools/tier_a_review_gate.py    what it OWES and what it could DISCHARGE
    SAIRN-ACTIVE-WORK-<s>.md       what it said it did
    ~/SAIRN-SESSION-LOCKS/status   what it is advertising right now

── THE PART THAT IS NOT A DASHBOARD ────────────────────────────────────────
Four of those five are easy to print and useless to compare. The reconciliation
is the point, and it is three questions a summary cannot answer about itself:

  1. A CLAIM WITH NO WORKLOG ENTRY. The session told four other sessions it was
     working on something and left no record that it did. Either the work is
     unrecorded or the claim was wrong; both are worth a minute.
  2. AN OBLIGATION THIS SESSION OWES, PAST DEADLINE. The register's own
     deadline, applied to this session's own debts rather than to everyone's.
  3. A STALE `blocked_on`. A row whose state is not `blocked` and which still
     names a blocker. It has happened twice -- mine on 2026-09-17, cc's on
     2026-09-18, advertising a block on a claim that had been RELEASED.

── WHAT GIT CANNOT TELL YOU, SAID ONCE AND LOUDLY ──────────────────────────
COMMIT AUTHORSHIP IS NOT DERIVABLE. Every clone commits as the same git
identity. `tools/hover_separation_audit.py` already establishes the only honest
rule: a commit is attributable when it touches a session's OWN claim file or
worklog, and EVERYTHING ELSE IS UNATTRIBUTED. That is most real work.

This file does not guess past that line. Commits inside a claim window are
reported as a WINDOW -- a superset containing every other session's pushes too
-- and are labelled that way in the output. A tool that silently claimed them
would be manufacturing exactly the confident-and-wrong state the weekly pass
exists to catch.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS_DIR = os.path.join(os.path.expanduser('~'), 'SAIRN-SESSION-LOCKS', 'status')

EXIT_CLEAN = 0
EXIT_ATTENTION = 1
EXIT_COULD_NOT_RUN = 2

# The register's own deadline for an open obligation.
OBLIGATION_DEADLINE_H = 24


class CouldNotTell(Exception):
    pass


def run(cmd, cwd=REPO):
    """Text output, ENCODING PINNED.

    `text=True` alone decodes with the locale default, which is cp1252 here. cc
    recorded that fail-open in tier_a_review_gate.py on 2026-09-15 -- the reader
    raised on this repo's box-drawing characters and the call returned TRUNCATED
    stdout rather than failing -- and I reproduced it in nhi_register.py the day
    after. A tool that reads git output gets this wrong once per platform.
    """
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=60)
    except Exception as e:                                       # noqa: BLE001
        raise CouldNotTell('%s failed: %s' % (' '.join(cmd[:3]), e))
    if p.returncode != 0 and not p.stdout:
        raise CouldNotTell('%s exited %d: %s'
                           % (' '.join(cmd[:3]), p.returncode,
                              (p.stderr or '').strip()[:200]))
    return p.stdout


def clone_session():
    """This clone's session name, from the directory rather than from a list."""
    base = os.path.basename(REPO)
    return base.split('-', 1)[1].lower() if '-' in base else base.lower()


# ── the five sources ────────────────────────────────────────────────────────

def git_state():
    out = {}
    out['branch'] = run(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip()
    dirty = [l for l in run(['git', 'status', '--porcelain']).splitlines()
             if l.strip() and not l.startswith('??')]
    out['dirty'] = dirty
    out['untracked'] = [l[3:] for l in run(['git', 'status', '--porcelain']).splitlines()
                        if l.startswith('??')]
    try:
        counts = run(['git', 'rev-list', '--left-right', '--count',
                      'origin/main...HEAD']).split()
        out['behind'], out['ahead'] = int(counts[0]), int(counts[1])
    except Exception:                                            # noqa: BLE001
        out['behind'] = out['ahead'] = None
    return out


def my_commits(session, days):
    """Commits provably this session's: they touch its claim file or worklog.

    The hover_separation_audit rule, reused rather than re-derived. Anything
    else is UNATTRIBUTED and is not counted here.
    """
    since = '--since=%d.days' % days
    claim = '.claude/claims/%s.json' % session
    log = 'SAIRN-ACTIVE-WORK-%s.md' % session
    txt = run(['git', 'log', since, '--format=%H\x1f%ad\x1f%s', '--date=short',
               '--', claim, log])
    rows = []
    for line in txt.splitlines():
        if '\x1f' not in line:
            continue
        sha, date, subj = line.split('\x1f', 2)
        rows.append({'sha': sha[:12], 'date': date, 'subject': subj})
    return rows


def claim_history(session, days):
    """(claims, releases) parsed from the claim-file commit subjects.

    The claim TOOL shows only what is active now. The history of what this
    session said it was on lives in those commit subjects, and that is the half
    the reconciliation needs.
    """
    since = '--since=%d.days' % days
    txt = run(['git', 'log', since, '--format=%H\x1f%ad\x1f%s', '--date=short',
               '--', '.claude/claims/%s.json' % session])
    claims, releases = [], []
    for line in txt.splitlines():
        if '\x1f' not in line:
            continue
        sha, date, subj = line.split('\x1f', 2)
        m = re.search(r'\b(claims|releases)\b\s+(.*)$', subj)
        if not m:
            continue
        what = m.group(2).strip()
        (claims if m.group(1) == 'claims' else releases).append(
            {'sha': sha[:12], 'date': date, 'what': what})
    return claims, releases


def worklog_entries(session, days):
    """Entries added to this session's own log inside the window.

    Read from the DIFF rather than from the file, so an entry written last month
    is not counted as this week's work -- which is exactly the mistake a person
    re-reading their own log makes.
    """
    path = os.path.join(REPO, 'SAIRN-ACTIVE-WORK-%s.md' % session)
    if not os.path.isfile(path):
        raise CouldNotTell('no worklog at %s -- this session has none, or the '
                           'name is wrong' % os.path.basename(path))
    txt = run(['git', 'log', '--since=%d.days' % days, '-p', '--format=%H',
               '--', 'SAIRN-ACTIVE-WORK-%s.md' % session])
    added = []
    for line in txt.splitlines():
        if line.startswith('+- ') and len(line) > 12:
            added.append(line[3:].strip())
    return added


def obligations(session):
    """(owed_by_me, dischargeable_by_me) from the review register."""
    p = os.path.join(REPO, 'docs', 'tier-a-reviews.json')
    try:
        with io.open(p, encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception as e:                                       # noqa: BLE001
        raise CouldNotTell('docs/tier-a-reviews.json did not parse (%s) -- so '
                           'NOTHING is known about obligations, which is not '
                           'the same as none' % e)
    recs = data['records'] if isinstance(data, dict) and 'records' in data else data
    open_recs = [r for r in recs
                 if r.get('status') != 'reviewed' and not r.get('discharged_at')]
    mine = [r for r in open_recs if r.get('author_session') == session]
    theirs = [r for r in open_recs if r.get('author_session') != session]
    return mine, theirs


def status_rows():
    if not os.path.isdir(STATUS_DIR):
        raise CouldNotTell('no status registry at %s' % STATUS_DIR)
    rows = {}
    for name in sorted(os.listdir(STATUS_DIR)):
        if not name.endswith('.json'):
            continue
        try:
            with io.open(os.path.join(STATUS_DIR, name), encoding='utf-8') as fh:
                rows[name[:-5]] = json.load(fh)
        except Exception:                                        # noqa: BLE001
            rows[name[:-5]] = {'_unreadable': True}
    return rows


# ── the reconciliation ──────────────────────────────────────────────────────

def _age_hours(iso):
    try:
        t = time.strptime(iso.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
    except Exception:                                            # noqa: BLE001
        return None
    return (time.time() - time.mktime(t) + time.timezone) / 3600.0


def _words(text):
    return set(w for w in re.findall(r'[a-z0-9_]{4,}', (text or '').lower()))


STOP = _words('the and for that with this from into work item items continue '
              'fourth cody hank claim claims release releases chore docs fix '
              'feat test tools then than when what which have been next '
              'more some other another thing things stuff pass again')


def reconcile(session, days):
    """Three questions a written summary cannot answer about itself."""
    findings = []
    claims, _releases = claim_history(session, days)
    log = worklog_entries(session, days)
    log_words = set()
    for e in log:
        log_words |= _words(e)

    # 1. A CLAIM WITH NO WORKLOG TRACE.
    #
    # DELIBERATELY CRUDE AND DELIBERATELY UNDER-CLAIMING. The test is whether
    # any distinctive word from the claim appears anywhere in the window's log
    # entries. A claim whose words are all generic ("continue work on the next
    # item") cannot be matched by ANY method and is reported as UNCHECKABLE
    # rather than as unrecorded -- a third state, because saying "you did not
    # log this" about a claim nobody could match is a false accusation the
    # reader has no way to refute.
    for c in claims:
        distinctive = _words(c['what']) - STOP
        if not distinctive:
            findings.append(('UNCHECKABLE', 'claim %s (%s) has no distinctive '
                             'words, so no method can match it against the log'
                             % (c['sha'], c['date'])))
            continue
        if not (distinctive & log_words):
            findings.append(('NO-LOG', 'claimed %s (%s) and no worklog entry in '
                             'this window mentions any of: %s'
                             % (c['date'], c['sha'],
                                ', '.join(sorted(distinctive)[:6]))))

    # 2. OBLIGATIONS THIS SESSION OWES, PAST THE REGISTER'S OWN DEADLINE.
    mine, theirs = obligations(session)
    for r in mine:
        age = _age_hours(r.get('opened_at', ''))
        if age is not None and age > OBLIGATION_DEADLINE_H:
            findings.append(('OWED', 'opened %s, %.0fh -- %s'
                             % (r['opened_at'], age,
                                ', '.join(r.get('resources') or [])[:60])))

    # 3. STALE BLOCKERS, ACROSS EVERY SESSION.
    #
    # Not only this one, on purpose: a stale blocked_on is advertised TO the
    # other sessions, so the session that can see it is not the session that
    # wrote it. Mine sat stale on 2026-09-17 and cc's on 2026-09-18, naming a
    # claim of mine that had been released hours earlier.
    for name, row in status_rows().items():
        if row.get('_unreadable'):
            findings.append(('UNREADABLE', 'status row %s did not parse' % name))
            continue
        if row.get('state') != 'blocked' and str(row.get('blocked_on') or '').strip():
            findings.append(('STALE-BLOCK', '%s reads state=%s and still names a '
                             'blocker: %s' % (name, row.get('state'),
                                              str(row['blocked_on'])[:90])))
    return findings, claims, log, mine, theirs


# ── report ──────────────────────────────────────────────────────────────────

def report(session, days, as_json):
    try:
        g = git_state()
        commits = my_commits(session, days)
        findings, claims, log, owed, dischargeable = reconcile(session, days)
        rows = status_rows()
    except CouldNotTell as e:
        print('COULD NOT RUN: %s' % e)
        print('Nothing below is a clean result -- a source that could not be '
              'read is a third state and is never folded into "nothing to '
              'report".')
        return EXIT_COULD_NOT_RUN

    me = rows.get(session, {})
    if as_json:
        print(json.dumps({
            'session': session, 'window_days': days, 'git': g,
            'attributable_commits': commits, 'claims': claims,
            'worklog_entries': len(log),
            'obligations_owed': len(owed),
            'obligations_dischargeable': len(dischargeable),
            'findings': [{'kind': k, 'detail': d} for k, d in findings],
            'status_row': me}, indent=1))
        return EXIT_ATTENTION if findings else EXIT_CLEAN

    print('SELF STATE -- %s, derived, window %d day(s)' % (session, days))
    print('')
    print('  GIT')
    print('    branch %s   ahead %s   behind %s'
          % (g['branch'], g['ahead'], g['behind']))
    if g['ahead']:
        print('    *** %d commit(s) exist ONLY in this clone' % g['ahead'])
    if g['dirty']:
        print('    *** %d tracked file(s) modified and uncommitted:' % len(g['dirty']))
        for d in g['dirty'][:8]:
            print('        %s' % d)
    if g['untracked']:
        print('    %d untracked file(s): %s'
              % (len(g['untracked']), ', '.join(g['untracked'][:4])))

    print('')
    print('  ATTRIBUTABLE COMMITS -- %d' % len(commits))
    print('    Commits touching this session\'s OWN claim file or worklog.')
    print('    EVERYTHING ELSE IS UNATTRIBUTED: every clone commits as one git')
    print('    identity, so real work cannot be attributed from git at all.')
    for c in commits[:6]:
        print('      %s %s  %s' % (c['sha'], c['date'], c['subject'][:64]))
    if len(commits) > 6:
        print('      ... and %d more' % (len(commits) - 6))

    print('')
    print('  WHAT IT TOLD THE OTHERS -- %d claim(s) in the window' % len(claims))
    for c in claims[:5]:
        print('      %s  %s' % (c['date'], c['what'][:88]))

    print('')
    print('  WHAT IT SAID IT DID -- %d worklog entr(y/ies) added' % len(log))

    print('')
    print('  REVIEW OBLIGATIONS')
    print('    owed BY this session (waiting on somebody else) : %d' % len(owed))
    print('    open and authored by OTHERS (this session could discharge): %d'
          % len(dischargeable))

    print('')
    print('  STATUS ROW NOW')
    if not me:
        print('    *** none -- this session is invisible to the other four')
    else:
        print('    state=%s  updated=%s' % (me.get('state'), me.get('updated')))
        print('    task : %s' % str(me.get('task') or '(none)')[:88])

    print('')
    if findings:
        print('  NEEDS ATTENTION -- %d' % len(findings))
        for kind, detail in findings:
            print('    %-13s %s' % (kind, detail))
    else:
        print('  NOTHING NEEDS ATTENTION on the three questions this asks.')
    print('')
    print('  AND THAT IS THREE QUESTIONS, NOT A CLEAN BILL. It cannot see')
    print('  whether the work was any good, whether a claim matched what was')
    print('  actually built, or whether a worklog entry is true -- only that')
    print('  each claim left SOME trace, that no obligation of this session is')
    print('  past the register\'s own deadline, and that no status row is')
    print('  advertising a block it is not in.')
    return EXIT_ATTENTION if findings else EXIT_CLEAN


# ── self-check ──────────────────────────────────────────────────────────────

def self_check():
    ok = True

    def ck(name, cond, detail=''):
        nonlocal ok
        print('  %-4s %s%s' % ('ok' if cond else 'FAIL', name,
                               '' if cond else '   <- %s' % (detail,)))
        if not cond:
            ok = False

    print('SELF STATE -- self-check')
    print('\n1. the clone name is DERIVED from the directory, not from a list')
    ck('this clone resolves to a session name', bool(clone_session()),
       clone_session())

    print('\n2. the reconciliation predicates, locked against synthetic input')
    # A generic claim cannot be matched by any method and must be UNCHECKABLE
    # rather than reported as unrecorded -- otherwise the tool accuses somebody
    # of not logging work on the strength of its own inability to match.
    ck('a claim of only stop-words has no distinctive words',
       _words('continue work on the next item') - STOP == set(),
       _words('continue work on the next item') - STOP)
    ck('...and a real claim does',
       bool(_words('bridge_data raw licence key rekey migration') - STOP),
       sorted(_words('bridge_data raw licence key rekey migration') - STOP))
    ck('a claim whose words appear in the log is NOT reported',
       bool(_words('csv formula injection sweep') & _words(
           'the csv formula injection sweep closed 53 sites')))

    print('\n3. a source that cannot be read is a THIRD state (PR 1.11)')
    real = globals()['STATUS_DIR']
    try:
        globals()['STATUS_DIR'] = os.path.join(real, '__no_such_dir__')
        raised = False
        try:
            status_rows()
        except CouldNotTell:
            raised = True
        ck('an absent status registry RAISES rather than reporting zero rows',
           raised)
    finally:
        globals()['STATUS_DIR'] = real

    realrepo = globals()['REPO']
    try:
        globals()['REPO'] = os.path.join(realrepo, '__no_such_repo__')
        raised = False
        try:
            obligations('fourth')
        except CouldNotTell:
            raised = True
        ck('an unreadable review register RAISES rather than reporting no '
           'obligations -- "none" and "could not tell" are different answers',
           raised)
    finally:
        globals()['REPO'] = realrepo

    print('\n4. the stale-blocker predicate, both directions')
    ck('state=blocked WITH a blocker is not a finding',
       not _stale({'state': 'blocked', 'blocked_on': 'michael'}))
    ck('state=working WITH a blocker IS a finding -- the cc case',
       _stale({'state': 'working', 'blocked_on': "fourth's released claim"}))
    ck('state=working with NO blocker is not a finding',
       not _stale({'state': 'working', 'blocked_on': None}))

    print('\n' + ('  all arms pass' if ok else '  ARMS FAILED'))
    return EXIT_CLEAN if ok else EXIT_COULD_NOT_RUN


def _stale(row):
    return (row.get('state') != 'blocked'
            and bool(str(row.get('blocked_on') or '').strip()))


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--days', type=int, default=7)
    ap.add_argument('--session', default=None)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--self-check', dest='selfcheck', action='store_true')
    args = ap.parse_args(argv)
    if args.selfcheck:
        return self_check()
    return report(args.session or clone_session(), args.days, args.json)


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                                  errors='replace')
    sys.exit(main())
