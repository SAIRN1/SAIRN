#!/usr/bin/env python
"""sairn_claim.py -- claim a work gate before running it, so two sessions do not.

WHY THIS EXISTS. On 2026-08-30 two sessions independently ran all three
SAIRNfreedom pre-build gates the same night -- the ORC 2915 statutory read, the
competitive/patent scan, and the service-hour research. Neither knew about the
other. It surfaced only when a rebase pulled three unexpected `docs(sairnfreedom)`
commits into an unrelated push, by which point both were finished. Roughly four
hours, duplicated.

CLAUDE.md already said "read all four SAIRN-ACTIVE-WORK files before starting
work." That rule did not prevent it, because it was understood as collision
avoidance on FILES. Two sessions can run identical research without touching a
single common file. The convention was then rewritten to say "claim a gate
before you run it" -- and a convention nobody can forget to follow is better
than one they can, which is what this is.

── WHY ONE FILE PER SESSION AND NOT ONE SHARED JSON ────────────────────────
This was specified as `.claude/active-claims.json`, a single shared file. It is
built instead as `.claude/claims/<session>.json`, one file per clone, because
THIS PROJECT ALREADY LEARNED THAT LESSON THE EXPENSIVE WAY: `SAIRN-ACTIVE-WORK.md`
was a single append target until 2026-08-24, when "four sessions appending to one
file's end produced repeated merge conflicts in a single night" and it was split
into four per-clone files. A single shared claims file rebuilds exactly that
failure, and rebuilds it in the tool whose entire job is to reduce friction
between parallel sessions.

One file per session means every write is to a file exactly one clone touches.
Merge conflicts are impossible by construction. Reading is a four-file glob.

── WHAT THIS IS NOT ────────────────────────────────────────────────────────
NOT A LOCK. Claims travel by git. A claim is invisible to another clone until it
is pushed AND that clone fetches, so two sessions starting within the same minute
can still both claim. This narrows a four-hour window to roughly a one-fetch
window; it does not close it. The real fix is the coordinating chat session
assigning gates explicitly. This is the fallback for when that did not happen.

It also cannot tell you a claim is being WORKED. It tells you one was MADE. A
crashed or compacted session leaves a claim behind, which is why claims expire --
see STALE_HOURS.

Usage:
  python tools/sairn_claim.py check  sairnfreedom "competitive scan"
  python tools/sairn_claim.py claim  sairnfreedom "competitive scan"
  python tools/sairn_claim.py release sairnfreedom
  python tools/sairn_claim.py list [--all]

Exit codes:  0 clear / claimed   1 blocked by another session's claim   2 error
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

# A crashed or context-compacted session cannot release its own claim, so a
# claim that outlives this is treated as expired rather than blocking forever.
# Four hours is longer than any single gate run so far tonight (the SAIRNfreedom
# gates were ~2h each) and short enough that a dead session frees its work
# before the next person needs it.
STALE_HOURS = float(os.environ.get('SAIRN_CLAIM_STALE_HOURS', '4'))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAIM_DIR = os.path.join(REPO, '.claude', 'claims')

# Words that carry no matching signal. Deliberately short: over-flagging costs a
# five-second read, under-flagging costs four hours, so this list stays minimal
# rather than growing to make the tool quieter.
STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'for', 'of', 'to', 'in', 'on', 'at', 'by',
    'with', 'from', 'work', 'task', 'gate', 'pass', 'run', 'new', 'app',
}

# ── GENERIC TOKENS: real words that carry no SUBJECT signal ────────────────
# Added 2026-09-02, after the same false block happened twice.
#
#   2026-09-01: `sairnvet ... audit` BLOCKED against `stonedesk safehtml audit,
#               session lock auth`. Different app, different file, sole overlap
#               the word "audit". Recorded in CLAUDE.md as a known defect and
#               left unfixed.
#   2026-09-02: `sairnroofing ... gap A2` BLOCKED against `sairnsenior ... gap
#               A6` AND `sairndental ... gap B1`. Three apps, three files, sole
#               overlap the word "gap" -- which every task string derived from
#               the worldwide competitive-gap audit contains, so the matcher was
#               on course to block essentially every audit task that night.
#
# These are NOT stopwords. A stopword is dropped entirely and stops being
# evidence; these still count, they just cannot block ALONE. The distinction
# matters because two of them together is a real signal ("stonedesk audit fix"
# vs "sairnvet audit fix" is worth a human read) while one is noise.
#
# DELIBERATELY SHORT, and it must stay short. The file's own rule still holds:
# over-flagging costs a five-second read, under-flagging costs four hours. Every
# word added here makes the tool quieter and blinder, so add one only after a
# real false block names it -- not in anticipation.
GENERIC_TOKENS = {
    'gap', 'audit', 'fix', 'update', 'panel', 'check', 'phase', 'wiring',
    'schema', 'engine', 'layer', 'seed', 'build', 'add', 'review',
}


def blocks_alone(shared):
    """Is this shared-token set strong enough to BLOCK, or only to note?

    A block needs one shared SPECIFIC token (an app name, a feature name, a
    file name), or at least TWO shared generic ones. One generic word on its
    own is a coincidence of English, not evidence of duplicated work.

    Note this can never weaken a same-subject block: an app name is never
    generic, so `sairnroofing` on both sides still blocks -- which is the case
    the tool exists for.
    """
    specific = shared - GENERIC_TOKENS
    return bool(specific) or len(shared) >= 2


def sh(args, check=True):
    r = subprocess.run(args, cwd=REPO, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + '\n')
        sys.exit(2)
    return r.stdout.strip()


def session_name():
    """Derived from the clone directory, which is how the four sessions are
    already distinguished everywhere else (SAIRN-ACTIVE-WORK-<name>.md)."""
    base = os.path.basename(REPO)
    m = re.match(r'^SAIRN-(.+)$', base, re.I)
    return (m.group(1) if m else base).lower()


def now():
    return time.time()


def iso(ts):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts))


def tokens(*parts):
    out = set()
    for p in parts:
        for t in re.split(r'[^a-z0-9]+', (p or '').lower()):
            if len(t) >= 3 and t not in STOPWORDS:
                out.add(t)
    return out


def load_all():
    """Every claim from every session's file. A malformed file is reported and
    skipped rather than crashing the check -- a broken claims file must never be
    the reason somebody starts duplicate work."""
    claims = []
    for path in sorted(glob.glob(os.path.join(CLAIM_DIR, '*.json'))):
        try:
            with open(path, encoding='utf-8') as f:
                doc = json.load(f)
        except (ValueError, OSError) as e:
            sys.stderr.write('WARNING: unreadable claims file %s (%s) -- '
                             'skipped, so this check is INCOMPLETE\n'
                             % (os.path.basename(path), e))
            continue
        for c in doc.get('claims', []):
            c['_file'] = path
            claims.append(c)
    return claims


def is_active(c):
    if c.get('status') != 'active':
        return False
    return (now() - c.get('claimed_at_epoch', 0)) < STALE_HOURS * 3600


def age_str(c):
    h = (now() - c.get('claimed_at_epoch', 0)) / 3600.0
    return '%.1fh ago' % h


def overlaps(c, subj, task):
    """Shared significant token between the two claims. Conservative on
    purpose: it flags for a human read, it does not decide."""
    mine = tokens(subj, task)
    theirs = tokens(c.get('subject'), c.get('task'))
    return mine & theirs


def my_file():
    return os.path.join(CLAIM_DIR, session_name() + '.json')


def load_mine():
    path = my_file()
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except ValueError:
            sys.stderr.write('ERROR: %s is not valid JSON. Fix it by hand '
                             'rather than letting this tool overwrite it.\n' % path)
            sys.exit(2)
    return {'session': session_name(), 'claims': []}


def save_mine(doc, message, push):
    os.makedirs(CLAIM_DIR, exist_ok=True)
    path = my_file()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write('\n')
    rel = os.path.relpath(path, REPO).replace('\\', '/')
    sh(['git', 'add', rel])
    if not sh(['git', 'diff', '--cached', '--name-only']):
        print('  (no change to commit)')
        return
    sh(['git', 'commit', '-q', '-m', message])
    print('  committed: %s' % message.split('\n')[0])
    if push:
        # Rebase first: another session may have pushed its own claim file.
        # Different files, so this cannot conflict -- that is the whole point
        # of one-file-per-session.
        sh(['git', 'fetch', 'origin'], check=False)
        sh(['git', 'rebase', 'origin/main'], check=False)
        r = subprocess.run(['git', 'push', 'origin', 'HEAD:main'],
                           cwd=REPO, capture_output=True, text=True)
        if r.returncode == 0:
            print('  pushed -- other clones can see this after they fetch')
        else:
            print('  PUSH FAILED. The claim is committed locally and therefore '
                  'INVISIBLE to every other clone. Push it yourself:')
            print('  ' + (r.stderr or '').strip().split('\n')[-1])


def cmd_check(args, quiet=False):
    if not args.no_fetch:
        sh(['git', 'fetch', 'origin'], check=False)
        # Read claims as they exist on origin/main, not just locally -- a claim
        # another session pushed is only visible here after a fetch, and this is
        # the whole reason the check can be trusted at all.
        sh(['git', 'checkout', 'origin/main', '--', '.claude/claims'], check=False)
    subj, task = args.subject, ' '.join(args.task)
    me = session_name()
    blocking = []
    weak = []
    for c in load_all():
        if c.get('session') == me:
            continue
        if not is_active(c):
            continue
        shared = overlaps(c, subj, task)
        if not shared:
            continue
        # A single shared GENERIC word is reported, never blocked. It is still
        # printed -- dropping it silently would be the other failure, and the
        # whole point of this tool is that a human reads the other session's
        # actual task rather than trusting a token match either way.
        (blocking if blocks_alone(shared) else weak).append((c, shared))
    if blocking:
        if not quiet:
            print('BLOCKED -- another session already claimed overlapping work:\n')
            for c, shared in blocking:
                print('  session   : %s' % c.get('session'))
                print('  subject   : %s' % c.get('subject'))
                print('  task      : %s' % c.get('task'))
                print('  claimed   : %s (%s)' % (c.get('claimed_at'), age_str(c)))
                print('  overlap on: %s' % ', '.join(sorted(shared)))
                print()
            print('DO NOT start this. Flag it back to the coordinating chat '
                  'session and let it decide who runs it.')
            print('If you believe that claim is dead, confirm with the other '
                  'session first -- do not just wait %g hours for it to expire.'
                  % STALE_HOURS)
        return 1
    if not quiet:
        print('CLEAR -- no active overlapping claim from another session.')
        if weak:
            print('\nNote: %d active claim(s) share ONE generic word with this '
                  'task and are NOT blocking. Shown so you can judge, not '
                  'because the tool thinks they overlap:' % len(weak))
            for c, shared in weak:
                print('  %s: %s -- %s  (shares only: %s)'
                      % (c.get('session'), c.get('subject'), c.get('task'),
                         ', '.join(sorted(shared))))
        stale = [c for c in load_all()
                 if c.get('session') != me and c.get('status') == 'active'
                 and not is_active(c) and overlaps(c, subj, task)]
        if stale:
            print('\nNote: %d EXPIRED claim(s) overlap this work (older than '
                  '%g hours, so not blocking):' % (len(stale), STALE_HOURS))
            for c in stale:
                print('  %s: %s -- %s (%s)' % (c.get('session'), c.get('subject'),
                                               c.get('task'), age_str(c)))
            print('An expired claim can mean the session died, or that the work '
                  'was DONE and never released. Check before repeating it.')
    return 0


def cmd_claim(args):
    rc = cmd_check(args)
    if rc != 0:
        return rc
    subj, task = args.subject, ' '.join(args.task)
    doc = load_mine()
    ts = now()
    doc['session'] = session_name()
    doc['claims'].append({
        'id': '%s-%d' % (session_name(), int(ts)),
        'session': session_name(),
        'subject': subj,
        'task': task,
        'claimed_at': iso(ts),
        'claimed_at_epoch': ts,
        'status': 'active',
        'released_at': None,
    })
    save_mine(doc, 'chore(claims): %s claims %s -- %s' % (session_name(), subj, task),
              push=not args.no_push)
    print('\nCLAIMED. Release it when the work closes:')
    print('  python tools/sairn_claim.py release %s' % subj)
    return 0


def cmd_release(args):
    doc = load_mine()
    subj = args.subject
    hit = [c for c in doc['claims']
           if c['status'] == 'active' and (c['id'] == subj or c['subject'] == subj)]
    if not hit:
        print('No active claim of yours matches %r.' % subj)
        return 0
    for c in hit:
        c['status'] = 'released'
        c['released_at'] = iso(now())
        print('  releasing: %s -- %s' % (c['subject'], c['task']))
    # Released claims are kept, not deleted: "who ran this gate and when" is the
    # question the next session asks, and a deleted row cannot answer it.
    save_mine(doc, 'chore(claims): %s releases %s' % (session_name(), subj),
              push=not args.no_push)
    return 0


def cmd_list(args):
    if not args.no_fetch:
        sh(['git', 'fetch', 'origin'], check=False)
        sh(['git', 'checkout', 'origin/main', '--', '.claude/claims'], check=False)
    rows = load_all()
    if not args.all:
        rows = [c for c in rows if is_active(c)]
    if not rows:
        print('No %sclaims.' % ('' if args.all else 'active '))
        return 0
    rows.sort(key=lambda c: c.get('claimed_at_epoch', 0), reverse=True)
    for c in rows:
        state = ('active' if is_active(c)
                 else ('EXPIRED' if c.get('status') == 'active' else 'released'))
        print('[%-8s] %-6s %-16s %s  (%s)'
              % (state, c.get('session'), c.get('subject'), c.get('task'), age_str(c)))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = p.add_subparsers(dest='cmd', required=True)

    # --no-fetch is declared per-subcommand rather than at the top level so it
    # can be written AFTER the subcommand, which is where anyone will type it.
    # A top-level-only flag silently errors on `list --no-fetch`.
    def nofetch(x):
        x.add_argument('--no-fetch', action='store_true',
                       help='skip git fetch (offline; the check is then only '
                            'as current as your last fetch)')

    c = sub.add_parser('check', help='is anyone already on this?')
    c.add_argument('subject')
    c.add_argument('task', nargs='*')
    nofetch(c)

    c = sub.add_parser('claim', help='check, then claim, commit and push')
    c.add_argument('subject')
    c.add_argument('task', nargs='*')
    c.add_argument('--no-push', action='store_true')
    nofetch(c)

    c = sub.add_parser('release', help='close your claim')
    c.add_argument('subject', help='subject or claim id')
    c.add_argument('--no-push', action='store_true')

    c = sub.add_parser('list', help='show claims')
    c.add_argument('--all', action='store_true', help='include released/expired')
    nofetch(c)

    args = p.parse_args()
    if args.cmd == 'check':
        return cmd_check(args)
    if args.cmd == 'claim':
        return cmd_claim(args)
    if args.cmd == 'release':
        return cmd_release(args)
    return cmd_list(args)


if __name__ == '__main__':
    sys.exit(main())
