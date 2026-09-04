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
# ── THE BLOCKLIST APPROACH WAS RETIRED 2026-09-04, AFTER IT LOST SIX TIMES ──
# GENERIC_TOKENS above is kept only as the record of what was tried. Nothing
# reads it any more, and it must not be added to -- see below for why adding
# to it was never going to work.
#
# The rule was "one shared SPECIFIC token blocks", where specific meant "not
# on this hand-maintained list of English words". That is a blocklist against
# the whole language, and the language kept winning. Confirmed false blocks:
#
#   2026-09-01  "audit"    sairnvet vs stonedesk
#   2026-09-02  "gap"      sairnroofing vs sairnsenior, and vs sairndental
#   2026-09-02  "platform" a NAMESPACE used as a subject, twice
#   2026-09-04  "triage"   sairnbuild/sairnvet vs stonedesk
#   2026-09-04  "false"    storage-write-wrappers vs sairndental
#   2026-09-04  "name"     THIS change, blocked on its own task string while
#                          on its way to fix this
#
# Every one cost a session an override and a disclosure note, and the sixth
# was a task literally describing the fix. A gate that must be talked past
# routinely is a gate people learn to talk past.
#
# THE NEW RULE, per Michael 2026-09-04: a block needs a shared MULTI-WORD
# PHRASE or a shared REAL NAME -- an app, a file, a resource -- never a single
# shared English word. Four ways to block, and each one is a thing that cannot
# be a coincidence of vocabulary:
#
#   1. THE SAME SUBJECT. Equal token sets, or one a subset of the other with
#      at least two tokens. Two sessions that named the same subject are
#      claiming the same namespace, whatever their task wording. The >= 2
#      floor is what keeps a bare namespace like `platform` from blocking
#      `platform-schema-constraints` -- the 2026-09-02 case.
#   2. THE SAME APP. Discovered from the repo's own *.html files, so it cannot
#      drift from reality. This is STRONGER than before, not weaker: an app
#      name inside a compound subject now matches, so `sairnbuild-sairnvet`
#      collides with a claim on `sairnvet`, which the old rule missed.
#   3. THE SAME FILE OR RESOURCE. A token carrying a separator -- `sd_data`,
#      `api/sd-data.js`, `bld_bids`, `dnt_referrals`. English words do not
#      contain underscores or slashes; identifiers do.
#   4. A SHARED TWO-WORD PHRASE, in order. "audit fix" on both sides is worth
#      a read; "audit" on one and "fix" on the other is not.
#
# WHAT THIS GIVES UP, said plainly rather than discovered later: two different
# apps working on a similarly-named feature no longer block on the feature
# word alone -- `sairnroofing warranty registration` vs `sairnbuild warranty
# tracking` is now a NOTE. That was a deliberate MUST-BLOCK case in the probe
# and it is deliberately flipped, because it is the same shape as every false
# block above: different app, different file, one shared noun. It is still
# printed, and the tool's whole premise is that a human reads the other
# session's actual task rather than trusting a token match either way.

IDENT_RE = re.compile(r'[a-z][a-z0-9]*(?:[_./\-][a-z0-9]+)+')

_APP_NAMES = None


def app_names():
    """App names taken from the repo's own *.html files, not a hardcoded list.

    A hardcoded list is one more thing to drift; this one is wrong only if the
    repo is. Cached because check() calls the matcher once per active claim.
    """
    global _APP_NAMES
    if _APP_NAMES is None:
        try:
            _APP_NAMES = {os.path.splitext(f)[0].lower()
                          for f in os.listdir(REPO) if f.lower().endswith('.html')}
        except OSError:
            _APP_NAMES = set()
    return _APP_NAMES


def word_seq(text):
    """Significant words IN ORDER -- phrase matching needs the order that
    tokens() throws away."""
    return [t for t in re.split(r'[^a-z0-9]+', (text or '').lower())
            if len(t) >= 3 and t not in STOPWORDS]


def bigrams(*parts):
    out = set()
    for p in parts:
        w = word_seq(p)
        for i in range(len(w) - 1):
            out.add(w[i] + ' ' + w[i + 1])
    return out


def idents(*parts):
    out = set()
    for p in parts:
        out |= set(IDENT_RE.findall((p or '').lower()))
    return out


def apps_in(*parts):
    words = set()
    for p in parts:
        words |= set(re.split(r'[^a-z0-9]+', (p or '').lower()))
    return words & app_names()


def block_reason(mine_subj, mine_task, their_subj, their_task):
    """Why these two claims collide, or None if they only share vocabulary.

    Returns a human-readable reason so the printed block names the EVIDENCE
    rather than a bare token -- "same app: sairnvet" is actionable, "overlap
    on: name" is what six sessions had to argue with.
    """
    ms, ts = set(word_seq(mine_subj)), set(word_seq(their_subj))
    if ms and ts:
        if ms == ts:
            return 'same subject'
        if ms < ts and len(ms) >= 2:
            return 'subject "%s" is inside theirs' % ' '.join(sorted(ms))
        if ts < ms and len(ts) >= 2:
            return 'their subject "%s" is inside yours' % ' '.join(sorted(ts))
    shared_apps = apps_in(mine_subj, mine_task) & apps_in(their_subj, their_task)
    if shared_apps:
        return 'same app: ' + ', '.join(sorted(shared_apps))
    shared_ids = idents(mine_subj, mine_task) & idents(their_subj, their_task)
    if shared_ids:
        return 'same file or resource: ' + ', '.join(sorted(shared_ids))
    shared_phrase = bigrams(mine_subj, mine_task) & bigrams(their_subj, their_task)
    if shared_phrase:
        return 'shared phrase: "%s"' % sorted(shared_phrase)[0]
    return None


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


def read_origin_claims():
    """Every session's claim file AS IT EXISTS ON origin/main, read without
    touching the working tree. Returns {name: text} or None if unavailable.

    ── WHY NOT `git checkout origin/main -- .claude/claims` (2026-09-04) ──────
    That is what check and list used to do, and CLAUDE.md already documents
    half of the damage: it OVERWRITES the working tree, so a hand-written claim
    that had not been committed was silently gone, from a command that sounds
    read-only.

    The other half was not documented and is worse. `git checkout <ref> -- path`
    also STAGES what it wrote. Observed on 2026-09-04: running `list` left
    `M .claude/claims/fourth.json` staged, holding origin's OLDER copy -- a
    staged revert of a claim this clone had already committed. Any later
    `git commit` sweeping the index would have undone it, and the tool that
    exists to stop sessions colliding would have deleted the record of one.

    `git show` reads the same bytes and cannot write anything.
    """
    out = {}
    ls = subprocess.run(['git', 'ls-tree', '--name-only', 'origin/main',
                         '.claude/claims/'], cwd=REPO, capture_output=True, text=True)
    if ls.returncode != 0:
        return None
    for path in ls.stdout.split('\n'):
        path = path.strip()
        if not path.endswith('.json'):
            continue
        r = subprocess.run(['git', 'show', 'origin/main:' + path],
                           cwd=REPO, capture_output=True, text=True)
        if r.returncode == 0:
            out[os.path.basename(path)] = r.stdout
    return out


def load_all(from_origin=False):
    """Every claim from every session's file. A malformed file is reported and
    skipped rather than crashing the check -- a broken claims file must never be
    the reason somebody starts duplicate work.

    from_origin reads origin/main's copies instead of the working tree, which is
    the view that matters: a claim another session pushed is only a fact once it
    is there. Falls back to the working tree if origin cannot be read, and SAYS
    SO, because a check that quietly narrowed its own scope is how a collision
    gets missed.
    """
    sources = []
    if from_origin:
        blobs = read_origin_claims()
        if blobs is None:
            sys.stderr.write('WARNING: could not read .claude/claims from '
                             'origin/main -- falling back to this clone\'s copy, '
                             'which may be stale. This check is WEAKER than usual.\n')
        else:
            sources = [(name, text) for name, text in sorted(blobs.items())]
    if not sources:
        for path in sorted(glob.glob(os.path.join(CLAIM_DIR, '*.json'))):
            try:
                with open(path, encoding='utf-8') as f:
                    sources.append((os.path.basename(path), f.read()))
            except OSError as e:
                sys.stderr.write('WARNING: unreadable claims file %s (%s) -- '
                                 'skipped, so this check is INCOMPLETE\n'
                                 % (os.path.basename(path), e))
    claims = []
    for name, text in sources:
        try:
            doc = json.loads(text)
        except ValueError as e:
            sys.stderr.write('WARNING: unreadable claims file %s (%s) -- '
                             'skipped, so this check is INCOMPLETE\n' % (name, e))
            continue
        for c in doc.get('claims', []):
            c['_file'] = os.path.join(CLAIM_DIR, name)
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


def on_origin(sha):
    """Is this commit actually reachable from origin/main RIGHT NOW.

    'Pushed' is a claim about a command; 'present on the remote' is a fact.
    CLAUDE.md's push protocol says to query the remote rather than trust the
    exit code, and this is that query. Fetches first, because the local
    origin/main ref is only as fresh as the last fetch.
    """
    sh(['git', 'fetch', 'origin'], check=False)
    r = subprocess.run(['git', 'merge-base', '--is-ancestor', sha, 'origin/main'],
                       cwd=REPO, capture_output=True, text=True)
    return r.returncode == 0


def save_mine(doc, message, push):
    """Returns True only when the claim is PRESENT ON THE REMOTE.

    ── WHY THIS RETURNS A VALUE (2026-09-04) ─────────────────────────────────
    It used to return None and print on failure, and both callers printed
    'CLAIMED.' / released-cleanly regardless. So a push that failed with a
    non-fast-forward -- the ordinary case when two of the four clones claim
    within the same few seconds -- left the claim COMMITTED LOCALLY AND
    INVISIBLE to every other clone, while the tool said it was claimed.

    That is the exact failure this whole tool exists to prevent, happening
    inside the tool, and it is the same false-success shape as a deploy
    watcher that swallows a 403: the expensive part is not the error, it is
    the confident line printed after it. Reproduced live on 2026-09-04 --
    'error: failed to push some refs' immediately followed by 'CLAIMED.'

    Three changes, and the third is the one that matters:
      1. RETRY. A non-fast-forward here is normal, not exceptional: another
         session pushed its own claim file between the fetch and the push.
         The files cannot conflict (one per clone), so rebasing and pushing
         again is the correct response, not an error to hand to a human.
      2. ABORT A FAILED REBASE. `git rebase` was run with check=False and its
         result ignored, so a rebase that stopped left the repo mid-rebase and
         the next push failed for a second, unrelated reason.
      3. VERIFY AGAINST THE REMOTE. Even a zero exit is only evidence. The
         commit must be an ancestor of origin/main afterwards, checked by
         asking git, before this returns True.
    """
    os.makedirs(CLAIM_DIR, exist_ok=True)
    path = my_file()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write('\n')
    rel = os.path.relpath(path, REPO).replace('\\', '/')
    sh(['git', 'add', rel])
    if not sh(['git', 'diff', '--cached', '--name-only']):
        print('  (no change to commit)')
        # Nothing to publish, so nothing can be invisible.
        return True
    sh(['git', 'commit', '-q', '-m', message])
    print('  committed: %s' % message.split('\n')[0])
    if not push:
        print('  --no-push: committed locally only. Other clones cannot see this '
              'until you push it.')
        return False

    return push_verified()


def push_verified():
    """Rebase-and-push until HEAD is genuinely on origin/main. Returns bool.

    Extracted from save_mine() on 2026-09-04 so cmd_release() can also use it.
    Its own probe found the reason: after a release whose push failed, the LOCAL
    file already said 'released', so re-running release matched no active claim,
    printed nothing wrong, exited 0 -- and never pushed the commit that was
    still sitting there. A second false success, one layer behind the first.
    """
    sha = sh(['git', 'rev-parse', 'HEAD'])
    last_err = ''
    for attempt in range(1, 4):
        sh(['git', 'fetch', 'origin'], check=False)
        # Rebase first: another session may have pushed its own claim file.
        # Different files, so this cannot conflict -- that is the whole point
        # of one-file-per-session. If it stops anyway, abort rather than
        # leaving the tree mid-rebase for whatever runs next.
        rb = subprocess.run(['git', 'rebase', 'origin/main'],
                            cwd=REPO, capture_output=True, text=True)
        if rb.returncode != 0:
            subprocess.run(['git', 'rebase', '--abort'], cwd=REPO,
                           capture_output=True, text=True)
            last_err = (rb.stderr or rb.stdout or '').strip().split('\n')[-1]
            continue
        sha = sh(['git', 'rev-parse', 'HEAD'])   # rebase rewrites it
        r = subprocess.run(['git', 'push', 'origin', 'HEAD:main'],
                           cwd=REPO, capture_output=True, text=True)
        if r.returncode != 0:
            last_err = (r.stderr or '').strip().split('\n')[-1]
            continue
        if on_origin(sha):
            print('  pushed and verified on origin/main -- other clones can see '
                  'this after they fetch')
            return True
        last_err = ('push reported success but %s is not an ancestor of '
                    'origin/main' % sha[:8])

    print('  PUSH FAILED after 3 attempts. The claim is committed locally and is '
          'therefore INVISIBLE to every other clone -- treat this as NOT CLAIMED.')
    if last_err:
        print('  last error: ' + last_err)
    print('  Push it yourself, then confirm with: python tools/sairn_claim.py list')
    return False


def cmd_check(args, quiet=False):
    if not args.no_fetch:
        sh(['git', 'fetch', 'origin'], check=False)
        # Read claims as they exist on origin/main, not just locally -- a claim
        # another session pushed is only visible here after a fetch, and this is
        # the whole reason the check can be trusted at all.
        # NO `git checkout origin/main -- .claude/claims` here. It overwrites AND
        # STAGES the working tree; read_origin_claims() reads the same bytes
        # with `git show` and cannot write anything. See its docstring.
    subj, task = args.subject, ' '.join(args.task)
    me = session_name()
    blocking = []
    weak = []
    for c in load_all(from_origin=not args.no_fetch):
        if c.get('session') == me:
            continue
        if not is_active(c):
            continue
        shared = overlaps(c, subj, task)
        if not shared:
            continue
        # Shared vocabulary is REPORTED, never blocked on its own -- dropping
        # it silently would be the other failure, and the whole point of this
        # tool is that a human reads the other session's actual task rather
        # than trusting a token match either way.
        reason = block_reason(subj, task, c.get('subject'), c.get('task'))
        (blocking if reason else weak).append((c, shared, reason))
    if blocking:
        if not quiet:
            print('BLOCKED -- another session already claimed overlapping work:\n')
            for c, shared, reason in blocking:
                print('  session   : %s' % c.get('session'))
                print('  subject   : %s' % c.get('subject'))
                print('  task      : %s' % c.get('task'))
                print('  claimed   : %s (%s)' % (c.get('claimed_at'), age_str(c)))
                # The EVIDENCE, not a bare token. "same app: sairnvet" tells
                # you what to check; "overlap on: name" is what six sessions
                # had to argue with.
                print('  blocked by: %s' % reason)
                print('  also share: %s' % ', '.join(sorted(shared)))
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
            print('\nNote: %d active claim(s) share WORDS with this task but no '
                  'app, file, subject or phrase, so they are NOT blocking. '
                  'Shown so you can judge, not because the tool thinks they '
                  'overlap:' % len(weak))
            for c, shared, _reason in weak:
                print('  %s: %s -- %s  (shares only: %s)'
                      % (c.get('session'), c.get('subject'), c.get('task'),
                         ', '.join(sorted(shared))))
        stale = [c for c in load_all(from_origin=not args.no_fetch)
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
    ok = save_mine(doc, 'chore(claims): %s claims %s -- %s' % (session_name(), subj, task),
                   push=not args.no_push)
    if not ok:
        # A claim nobody else can see is not a claim. Saying so, and exiting
        # non-zero so a script cannot read this as success either.
        print('\nNOT CLAIMED -- the claim did not reach origin/main, so every other')
        print('clone still sees this work as unclaimed and can start it.')
        print('Fix the push and re-run, or write the claim by hand and push it.')
        return 3
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
        # ...but a PREVIOUS release may have been written and committed here and
        # failed to push, which is exactly why nothing matches now: the local
        # file already says released while origin still says active. Publish it
        # rather than exiting 0 over a commit nobody else can see.
        if not args.no_push and not on_origin(sh(['git', 'rev-parse', 'HEAD'])):
            print('  There are local commits not on origin/main -- publishing them,')
            print('  in case an earlier release was committed here and never landed.')
            if not push_verified():
                print('\nSTILL NOT ON origin/main. Other clones may still see one of your')
                print('claims as active. Push by hand, then confirm with: list')
                return 3
        return 0
    for c in hit:
        c['status'] = 'released'
        c['released_at'] = iso(now())
        print('  releasing: %s -- %s' % (c['subject'], c['task']))
    # Released claims are kept, not deleted: "who ran this gate and when" is the
    # question the next session asks, and a deleted row cannot answer it.
    ok = save_mine(doc, 'chore(claims): %s releases %s' % (session_name(), subj),
                   push=not args.no_push)
    if not ok:
        # A release that does not land is the opposite failure to an unlanded
        # claim and is milder -- the work stays blocked rather than duplicated,
        # and the claim expires after 4 hours anyway. Still reported, and still
        # non-zero, because "released" should not be printed for something that
        # is still active everywhere else.
        print('\nNOT RELEASED on origin/main -- other clones still see this claim as')
        print('active until the push lands (or until it expires 4h after it was made).')
        return 3
    return 0


def cmd_list(args):
    if not args.no_fetch:
        sh(['git', 'fetch', 'origin'], check=False)
        # NO `git checkout origin/main -- .claude/claims` here. It overwrites AND
        # STAGES the working tree; read_origin_claims() reads the same bytes
        # with `git show` and cannot write anything. See its docstring.
    rows = load_all(from_origin=not args.no_fetch)
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
