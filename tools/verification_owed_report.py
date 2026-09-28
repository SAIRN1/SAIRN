#!/usr/bin/env python3
"""tools/verification_owed_report.py -- commits that SAID verification was owed,
and no later commit or log entry that records it being done.

    python tools/verification_owed_report.py
    python tools/verification_owed_report.py --days 30
    python tools/verification_owed_report.py --json

REPORT-ONLY. Exit 0 with findings printed, 2 COULD NOT RUN. It never blocks: an
owed verification is a debt to surface, not a reason to stop a later push, and a
gate that blocked here would be cleared by deleting the sentence rather than by
doing the verification.

── THE DEFECT THIS EXISTS FOR, AND IT IS MINE ─────────────────────────────
On 2026-09-27 I shipped the alf_incidents attribution fix with this sentence in
its own commit message:

    "LIVE RE-VERIFICATION IS STILL OWED: these arms are in-process, and the
     defect they now cover was invisible to in-process arms."

That was accurate. It was also the last anybody would have heard of it. The next
day the live run found that the fix did not work -- a payload `recorded_by`
overwrote the server-set column on every read -- and the nine green arms could
not see it. The debt was named honestly, in the right place, and nothing carried
it forward.

A PROMISE IN A COMMIT MESSAGE IS WRITE-ONLY. Nothing reads commit prose, so the
most careful possible disclosure and saying nothing at all have identical
consequences. This makes the prose readable.

── WHAT COUNTS AS DISCHARGING THE DEBT ────────────────────────────────────
Any ONE of these, all searched:
  * a LATER commit touching one of the same files whose message records a live
    verification (live-verified, verified live, driven against, observed);
  * a later commit that CITES the owing sha;
  * a defect-register record whose method is live-verification citing a commit
    that touches an overlapping file set.

THE FILE OVERLAP IS THE PART THAT MAKES IT MEAN ANYTHING. Without it, any later
commit anywhere saying "live-verified" would clear every open debt in the repo,
and the report would read clean while every debt stood.

── WHAT IT CANNOT DO ──────────────────────────────────────────────────────
It matches PHRASES. A commit that owes verification without saying so is
invisible, and one that discharges a debt in words this does not know reads as
still-owed. So the owed list is an UPPER bound on what it can see and a LOWER
bound on what exists, and neither number is a measurement of the real debt.
It also cannot tell whether the verification that WAS done covered the thing
that was owed.
"""
import argparse
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# "this still needs a live run", in the spellings this platform actually uses.
OWED = re.compile(
    r"""verification is still owed|still owed[:,]? live|live verification"""
    r"""\s+(?:is\s+)?(?:still\s+)?owed|re-?verification is still owed"""
    r"""|NOT verified live|not been verified live|unverified live"""
    r"""|owes? a live (?:run|verification)|live run is owed"""
    r"""|remains? UNVERIFIED live|verification owed""", re.I)

# "somebody did it".
DONE = re.compile(
    r"""live[- ]verified|verified live|LIVE-VERIFIED|driven against the deployed"""
    r"""|against the deployed endpoint|observed values|live run confirms"""
    r"""|re-?verified live|confirmed live""", re.I)


# ── BOOKKEEPING FILES CANNOT CLEAR A DEBT, AND THE FIRST RUN PROVED IT ────
# docs/defect-density-register.json is touched by almost every commit on this
# platform, so overlapping on it made ANY later live-verification commit clear
# EVERY open debt -- six of the first run's eight "cleared" lines rested on it.
# A clearance that is not one is worse than a missed debt: the report reads
# clean and the debt stands.
#
# These files carry no subject of their own. They are excluded from the OVERLAP
# test, and a commit whose file list is ONLY these is not treated as owing
# anything in the first place -- a claim or a register entry is prose ABOUT
# work, not work.
BOOKKEEPING = (
    'docs/defect-density-register.json',
    'docs/tier-a-reviews.json',
    'docs/SAIRN-OPEN-WORK-INDEX.md',
    'docs/TOOLING-INVENTORY.md',
    'docs/MASTER-PLAN.md',
    'docs/traceability-matrix.md',
    'docs/CRON-LIVENESS-STATUS.md',
)


def substantive(files):
    """The files a commit is actually ABOUT."""
    return {f for f in files
            if not f.startswith('.claude/claims/') and f not in BOOKKEEPING}


class CouldNotRun(Exception):
    pass


def git(*args):
    try:
        r = subprocess.run(('git',) + args, cwd=REPO, capture_output=True,
                           timeout=120)
    except FileNotFoundError:
        raise CouldNotRun('`git` is not on PATH, so NOTHING was read')
    except Exception as exc:                                     # noqa: BLE001
        raise CouldNotRun('git %s did not run: %s' % (' '.join(args), exc))
    if r.returncode != 0:
        raise CouldNotRun('git %s exited %d: %s'
                          % (' '.join(args), r.returncode,
                             r.stderr.decode('utf-8', 'replace').strip()[:200]))
    return r.stdout.decode('utf-8', 'replace')


def commits(days):
    """[(sha, date, subject, body, files)] newest first."""
    sep = '\x1e'
    raw = git('log', '--since=%d.days' % days, '--name-only',
              '--format=%s%%H%%x1f%%ad%%x1f%%s%%x1f%%B%%x1f' % sep,
              '--date=short')
    out = []
    for chunk in raw.split(sep):
        if not chunk.strip():
            continue
        parts = chunk.split('\x1f')
        if len(parts) < 5:
            continue
        sha, date, subject, body, tail = parts[0], parts[1], parts[2], parts[3], parts[4]
        files = [l.strip() for l in tail.splitlines() if l.strip()]
        out.append((sha.strip(), date, subject, body, files))
    if not out:
        raise CouldNotRun(
            'git log returned no commits in the last %d days -- NOTHING was '
            'scanned. This is not "no debts".' % days)
    return out


def register_live_files():
    """Files touched by commits cited in live-verification register records."""
    p = os.path.join(REPO, 'docs', 'defect-density-register.json')
    if not os.path.isfile(p):
        return set()
    try:
        d = json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError):
        return set()
    recs = d.get('records') if isinstance(d, dict) else d
    out = set()
    for r in recs or []:
        if not isinstance(r, dict):
            continue
        if (r.get('detection_method') or '') != 'live-verification':
            continue
        out |= substantive({str(f).replace('\\', '/')
                            for f in (r.get('files') or [])})
    return out


def analyse(days):
    rows = commits(days)
    reg_live = register_live_files()
    owed = []
    for i, (sha, date, subject, body, files) in enumerate(rows):
        if not OWED.search(body or ''):
            continue
        fileset = substantive({f.replace('\\', '/') for f in files})
        if not fileset:
            # A claim entry or a register row quoting the phrase is prose ABOUT
            # work, not work that owes a run.
            continue
        # LATER commits are the ones BEFORE this index (log is newest first).
        cleared_by = None
        for sha2, date2, subj2, body2, files2 in rows[:i]:
            f2 = substantive({f.replace('\\', '/') for f in files2})
            if sha[:8] in (body2 or ''):
                cleared_by = (sha2[:8], 'cites the owing sha')
                break
            if DONE.search(body2 or '') and (fileset & f2):
                cleared_by = (sha2[:8], 'later commit records a live run on %d '
                                        'shared file(s)' % len(fileset & f2))
                break
        if not cleared_by and (fileset & reg_live):
            cleared_by = ('register', 'a live-verification record covers %d '
                                      'shared file(s)' % len(fileset & reg_live))
        owed.append({'sha': sha[:8], 'date': date, 'subject': subject[:70],
                     'files': sorted(fileset)[:6], 'cleared_by': cleared_by})
    return owed


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=21)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)

    try:
        rows = analyse(args.days)
    except CouldNotRun as e:
        sys.stderr.write('COULD NOT RUN -- %s\n' % e)
        sys.stderr.write('This is the THIRD STATE. Report-only does not mean '
                         'report-anything.\n')
        return 2

    open_debts = [r for r in rows if not r['cleared_by']]
    if args.json:
        print(json.dumps({'window_days': args.days, 'said_owed': len(rows),
                          'still_owed': len(open_debts), 'rows': rows},
                         indent=2))
        return 0

    print('VERIFICATION OWED -- commits that said a live run was owed')
    print('window: last %d days' % args.days)
    print('')
    print('  commits SAYING verification is owed : %d' % len(rows))
    print('  of those, nothing records it done   : %d' % len(open_debts))
    print('')
    if open_debts:
        print('  STILL OWED:')
        for r in open_debts:
            print('   %s  %s  %s' % (r['sha'], r['date'], r['subject']))
            print('        files: %s' % ', '.join(r['files'][:4]))
        print('')
    for r in rows:
        if r['cleared_by']:
            print('   cleared  %s  by %s -- %s'
                  % (r['sha'], r['cleared_by'][0], r['cleared_by'][1]))
    print('')
    print('REPORT-ONLY, AND DELIBERATELY. A gate here would be cleared by')
    print('deleting the sentence rather than by doing the verification, which')
    print('would make honest disclosure the expensive option.')
    print('')
    print('IT MATCHES PHRASES. A commit that owes a live run without saying so is')
    print('invisible; one that discharges a debt in words this does not know')
    print('reads as still-owed. Neither number measures the real debt, and it')
    print('cannot tell whether the run that happened covered what was owed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
