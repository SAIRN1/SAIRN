"""sairn_self_state.py -- what is THIS session's real current state, derived.

    python tools/sairn_self_state.py                # this clone, last 7 days
    python tools/sairn_self_state.py --days 14
    python tools/sairn_self_state.py --session cc   # cc's shared sources only
    python tools/sairn_self_state.py --session cc --clone ../SAIRN-cc
    python tools/sairn_self_state.py --bundle out.json --stamp "<iso time>"
    python tools/sairn_self_state.py --json
    python tools/sairn_self_state.py --self-check

── THREE WAYS TO GET A ROW, AND THEY ARE NOT EQUIVALENT ────────────────────
  SELF     run inside a session's own clone. The only authoritative form.
  OUTSIDE  `--clone <path>`, whose identity marker must match `--session` or it
           refuses. Real, and blind to everything not on disk.
  NOT DERIVED  `--session X` with no `--clone`, from somebody else's clone: the
           git half is ABSENT and says so. It used to be silently filled in
           from the clone you happened to be standing in -- see git_state().

`--bundle` captures every provisioned clone in ONE run, which is what makes the
rows comparable: these clones push to one branch, so four readings taken ten
minutes apart are four readings of different repositories.

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
import shutil
import subprocess
import sys
import tempfile
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


def clone_session(repo=None):
    """This clone's session name, FROM THE MARKER, never from the folder name.

    ── THIS FUNCTION WAS THE DEFECT ITS OWN AUTHOR FIXED 43 MINUTES LATER ────
    It read `os.path.basename(REPO).split('-', 1)[1]`. That is exactly the
    spoofable derivation hover finding #258 is about, and
    `tools/sairn_session_identity.py` replaced it platform-wide in `527b31bf`
    at 08:46 -- 43 minutes after this file landed in `4213c84f` at 08:03. The
    migration reached `sairn_claim.py` and `tier_a_review_gate.py` and did not
    reach here, so the tool whose entire purpose is deriving TRUE state was
    deriving its own identity from the one source the platform had just ruled
    untrustworthy. Nothing was wrong on disk -- every clone is named after its
    session today -- which is precisely why it survived: a wrong method that
    returns the right answer leaves no evidence.

    FAILS CLOSED, like the module it now calls: an unprovisioned clone raises
    rather than guessing, because a fallback would leave the spoofable path
    live with nothing to say which one answered.
    """
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import sairn_session_identity as _identity                   # noqa: E402
    if repo is None:
        return _identity.session_name()
    return _identity.session_name(repo)


# ── the five sources ────────────────────────────────────────────────────────

def git_state(repo=None):
    """Branch, HEAD, dirt and ahead/behind FOR ONE WORKING COPY.

    ── IT USED TO IGNORE WHICH ONE, AND THAT MADE `--session cc` WRONG ──────
    This read the module-level REPO unconditionally, so `--session cc` printed
    cc's claims, cc's obligations and cc's worklog next to THIS clone's branch,
    dirt and ahead/behind, under one heading, with nothing saying they came
    from different places. Measured 2026-09-18: the four build clones sat at
    four different HEADs (hank 179fde48, cc d01011d1, cody 952a5cc4, fourth
    57b44c05) and fourth had one modified file. Run from here, `--session
    fourth` reported fourth as clean at my HEAD. Every field was real and the
    row was false.

    `--no-optional-locks` on every call: reading ANOTHER live clone must not
    contend for its `index.lock` while an agent in it is mid-commit. That flag
    is what makes an outside read genuinely read-only rather than merely
    read-intent.
    """
    cwd = repo or REPO
    def g(*a):
        return run(['git', '--no-optional-locks'] + list(a), cwd=cwd)
    out = {'repo': cwd}
    out['branch'] = g('rev-parse', '--abbrev-ref', 'HEAD').strip()
    out['head'] = g('rev-parse', '--short', 'HEAD').strip()
    porcelain = g('status', '--porcelain').splitlines()
    out['dirty'] = [l for l in porcelain if l.strip() and not l.startswith('??')]
    out['untracked'] = [l[3:] for l in porcelain if l.startswith('??')]
    try:
        counts = g('rev-list', '--left-right', '--count',
                   'origin/main...HEAD').split()
        out['behind'], out['ahead'] = int(counts[0]), int(counts[1])
    except Exception:                                            # noqa: BLE001
        out['behind'] = out['ahead'] = None
    try:
        out['unpushed'] = [l for l in g('log', '--format=%h %s',
                                        'origin/main..HEAD').splitlines() if l.strip()]
    except Exception:                                            # noqa: BLE001
        out['unpushed'] = None
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

def resolve_git_source(session, clone):
    """(repo_or_None, derivation, why) -- WHOSE working copy the git half is.

    Three honest answers and never a silent fourth:
      SELF     the caller is inside `session`'s own clone. Authoritative.
      OUTSIDE  a path was named and its marker says `session`. Real, and it
               cannot see anything that is not on disk -- an edit held in the
               running agent's head, a decision not yet written down, or what
               that session BELIEVES it is doing.
      None     no path was named and this is not that session's clone, so the
               git half COULD NOT BE DERIVED. It is left out rather than
               filled in from here, which is what the old version did.
    """
    here = None
    try:
        here = clone_session()
    except Exception:                                            # noqa: BLE001
        pass
    if clone:
        clone = os.path.abspath(clone)
        if not os.path.isdir(os.path.join(clone, '.git')):
            raise CouldNotTell('%s is not a git clone' % clone)
        marker = clone_session(clone)
        if marker != session:
            raise CouldNotTell(
                'REFUSED: --clone %s carries the marker %r, not %r. A state '
                'row attributed to the wrong session is worse than a missing '
                'one, so this does not proceed on the assumption that the '
                'path was meant.' % (clone, marker, session))
        return clone, ('SELF' if os.path.abspath(clone) == os.path.abspath(REPO)
                       else 'OUTSIDE'), ''
    if here == session:
        return REPO, 'SELF', ''
    return None, None, (
        'no --clone was given and this is %s\'s clone, so %s\'s branch, dirt, '
        'ahead/behind and unpushed commits were NOT derived. They are absent '
        'rather than filled in from here.' % (here or 'an unidentified clone', session))


def report(session, days, as_json, clone=None):
    try:
        repo, derivation, why = resolve_git_source(session, clone)
        g = git_state(repo) if repo else None
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
            'git_derivation': derivation, 'git_not_derived_because': why,
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
    if not g:
        print('    NOT DERIVED -- this is a third state, not "clean":')
        print('      %s' % why)
    else:
        print('    derived %s from %s' % (derivation, g['repo']))
        if derivation == 'OUTSIDE':
            print('      An outside read sees the DISK. It cannot see an edit the')
            print('      running agent has not written, a decision it has not')
            print('      recorded, or what it believes it is doing. Only that')
            print('      session running this in its own clone can.')
        print('    branch %s   head %s   ahead %s   behind %s'
              % (g['branch'], g['head'], g['ahead'], g['behind']))
        if g['ahead']:
            print('    *** %d commit(s) exist ONLY in that clone' % g['ahead'])
            for u in (g.get('unpushed') or [])[:6]:
                print('        %s' % u)
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
    print('\n1. the clone name comes from the MARKER, not from the directory')
    # THIS ARM USED TO SAY "derived from the directory, not from a list" and
    # passed while doing the spoofable thing. The label was the tell and nothing
    # read it. Both directions now: the marker is what answers, and a directory
    # named after nobody still resolves.
    ck('this clone resolves to a session name', bool(clone_session()),
       clone_session())
    _tmp = tempfile.mkdtemp(prefix='selfstate_id_')
    try:
        # REAL clones, not a bare `.git` folder. The identity module resolves
        # the marker through `git rev-parse --git-dir`, so a directory that is
        # not a repository walks UP to the first one above it -- and on this
        # box `C:\Users\marsh\.git` exists, so EVERYTHING under the user
        # profile, including the system temp directory, resolves there. The arm
        # would have been reading somebody else's repository and reporting on
        # it. Found by this arm naming C:/Users/marsh/.git in its own failure.
        _fake = os.path.join(_tmp, 'NOT-NAMED-AFTER-ANY-SESSION')
        os.makedirs(_fake)
        subprocess.run(['git', 'init', '-q', _fake], capture_output=True)
        with io.open(os.path.join(_fake, '.git', 'sairn-session'), 'w',
                     encoding='utf-8') as _fh:
            _fh.write('cody\n')
        ck('a directory named after NOBODY still resolves, from its marker',
           clone_session(_fake) == 'cody', clone_session(_fake))
        _bare = os.path.join(_tmp, 'SAIRN-cody')
        os.makedirs(_bare)
        subprocess.run(['git', 'init', '-q', _bare], capture_output=True)
        _raised = False
        try:
            clone_session(_bare)
        except Exception:                                         # noqa: BLE001
            _raised = True
        ck('a directory NAMED SAIRN-cody with no marker RAISES rather than '
           'answering "cody" -- the rename attack, refused', _raised)

        print('\n1b. the git half is attributed to the RIGHT working copy')
        # The defect: --session cc printed cc's claims beside THIS clone's
        # branch and dirt, under one heading, with nothing saying so.
        _repo, _deriv, _why = resolve_git_source(clone_session(), None)
        ck('no --clone, own session -> SELF from this clone',
           _deriv == 'SELF' and _repo == REPO, (_deriv, _repo))
        _repo2, _deriv2, _why2 = resolve_git_source('nobody_else', None)
        ck('no --clone, ANOTHER session -> NOT DERIVED, never this clone\'s git',
           _repo2 is None and _deriv2 is None and 'NOT derived' in _why2,
           (_repo2, _deriv2, _why2))
        _refused = False
        try:
            resolve_git_source('hank', _fake)      # marker says cody
        except CouldNotTell:
            _refused = True
        ck('--clone whose marker disagrees with --session REFUSES', _refused)
        _r3, _d3, _ = resolve_git_source('cody', _fake)
        ck('--clone whose marker AGREES is accepted, and labelled OUTSIDE',
           _d3 == 'OUTSIDE' and _r3 == os.path.abspath(_fake), (_d3, _r3))
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)
    ck('the scratch clones are gone', not os.path.isdir(_tmp))

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


def collect(session, days, clone):
    """The same dict --json prints, as data rather than stdout."""
    repo, derivation, why = resolve_git_source(session, clone)
    g = git_state(repo) if repo else None
    findings, claims, log, owed, dischargeable = reconcile(session, days)
    rows = status_rows()
    return {'session': session, 'window_days': days, 'git': g,
            'git_derivation': derivation, 'git_not_derived_because': why,
            'attributable_commits': my_commits(session, days),
            'claims': claims, 'worklog_entries': len(log),
            'obligations_owed': len(owed),
            'obligations_dischargeable': len(dischargeable),
            'findings': [{'kind': k, 'detail': d} for k, d in findings],
            'status_row': rows.get(session, {})}


def bundle(days, out_path, stamp):
    """One artifact holding EVERY clone's derived state, for the auditor.

    ── WHY A BUNDLE AND NOT FOUR SEPARATE RUNS ─────────────────────────────
    The reconciliation is a comparison. Four outputs read at four different
    moments cannot be compared, because the thing being compared moves: these
    clones push to one branch and a row read ten minutes apart is a row about a
    different repository. So every entry here is stamped with the SAME run, and
    each carries its own derivation label so an OUTSIDE reading is never mistaken
    for a session's own account of itself.

    CLONES ARE COUNTED FROM DISK, never from a list. CLAUDE.md said "Four
    clones" for weeks after a fifth was pushing; `sibling_clones()` in
    nhi_register.py already enumerates them and fails closed if it cannot find
    even itself, so it is imported rather than reimplemented.

    A CLONE WITH NO IDENTITY MARKER IS NAMED AND NOT READ FURTHER. That is the
    honest handling of the auditor clone, which is not a build session and whose
    directory a build agent must not reach into -- and it falls out of the
    marker rule rather than out of a hardcoded name, so a sixth clone provisioned
    tomorrow is included and an unprovisioned one never is.
    """
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    from nhi_register import sibling_clones                       # noqa: E402
    parent = os.path.dirname(REPO)
    entries, skipped = [], []
    for name in sibling_clones():
        path = os.path.join(parent, name)
        try:
            sess = clone_session(path)
        except Exception as e:                                    # noqa: BLE001
            skipped.append({'dir': name,
                            'why': 'no identity marker (%s). Not read further: '
                                   'an unprovisioned clone is not a build '
                                   'session and is not guessed at.'
                                   % type(e).__name__})
            continue
        try:
            entries.append(collect(sess, days, path))
        except CouldNotTell as e:
            skipped.append({'dir': name, 'session': sess,
                            'why': 'COULD NOT DERIVE: %s' % e})
    doc = {
        'bundle_of': 'sairn_self_state',
        'generated_at': stamp,
        'generated_by_clone': clone_session(),
        'window_days': days,
        'clones': entries,
        'not_included': skipped,
        'what_this_is_not': [
            'NOT a reconciliation. It is the INPUT to one: four derived states '
            'captured in a single run so they can be compared without the '
            'branch moving underneath the comparison.',
            'An entry whose git_derivation is OUTSIDE was read off another '
            'clone\'s disk by this one. It is real and it is not that session '
            'speaking: it cannot see an unwritten edit, an unrecorded decision, '
            'or what that session believes it is doing. Only that session '
            'running this tool in its own clone produces SELF.',
            'COMMIT AUTHORSHIP IS STILL NOT DERIVABLE. Every clone commits as '
            'one git identity; only commits touching a session\'s own claim '
            'file or worklog are attributable and that is a small fraction of '
            'real work.',
        ],
    }
    with io.open(out_path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    print('BUNDLE -- %d clone(s) derived, %d not included'
          % (len(entries), len(skipped)))
    for e in entries:
        g = e['git'] or {}
        print('  %-8s %-7s head=%-9s ahead=%-3s dirty=%-3s untracked=%-3s '
              'owed=%-2s dischargeable=%-3s findings=%s'
              % (e['session'], e['git_derivation'], g.get('head'),
                 g.get('ahead'), len(g.get('dirty') or []),
                 len(g.get('untracked') or []), e['obligations_owed'],
                 e['obligations_dischargeable'], len(e['findings'])))
    for s in skipped:
        print('  %-8s NOT INCLUDED -- %s' % (s.get('session') or s['dir'], s['why']))
    print('  written: %s' % out_path)
    if not entries:
        print('COULD NOT RUN: no clone yielded a state, which is a broken '
              'enumeration rather than an empty platform.')
        return EXIT_COULD_NOT_RUN
    return EXIT_ATTENTION if any(e['findings'] for e in entries) else EXIT_CLEAN


def _stale(row):
    return (row.get('state') != 'blocked'
            and bool(str(row.get('blocked_on') or '').strip()))


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--days', type=int, default=7)
    ap.add_argument('--session', default=None)
    ap.add_argument('--clone', default=None,
                    help='the working copy to derive the GIT half from. Its '
                         'identity marker must match --session or this refuses.')
    ap.add_argument('--bundle', default=None, metavar='OUT.json',
                    help='derive EVERY provisioned clone in one run and write '
                         'the artifact the reconciliation reads')
    ap.add_argument('--stamp', default=None,
                    help='the timestamp to record in a bundle. Passed in rather '
                         'than read from the clock so a run is reproducible and '
                         'so nothing here has to be trusted about when it ran.')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--self-check', dest='selfcheck', action='store_true')
    args = ap.parse_args(argv)
    if args.selfcheck:
        return self_check()
    if args.bundle:
        if not args.stamp:
            print('COULD NOT RUN: --bundle needs --stamp "<iso time>". A '
                  'bundle with no stamp is four rows nobody can place in '
                  'time, which is the failure the bundle exists to avoid.')
            return EXIT_COULD_NOT_RUN
        try:
            return bundle(args.days, args.bundle, args.stamp)
        except CouldNotTell as e:
            print('COULD NOT RUN: %s' % e)
            return EXIT_COULD_NOT_RUN
    try:
        session = args.session or clone_session()
    except Exception as e:                                        # noqa: BLE001
        print('COULD NOT RUN: %s' % e)
        return EXIT_COULD_NOT_RUN
    return report(session, args.days, args.json, args.clone)


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                                  errors='replace')
    sys.exit(main())
