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

── AND IT CANNOT BE CURRENT WITHOUT A FETCH, WHICH IT NOW SAYS (2026-09-14) ──
`check` printed a bare, unqualified CLEAR when the `git fetch` it depends on had
FAILED. Reproduced live: with the remote unreachable the fetch exited 128 with
"unable to access", and the very next line was

    CLEAR -- no active overlapping claim from another session.

That verdict came off an `origin/main` ref eighteen minutes stale, and nothing in
the output said so -- the failure was swallowed by `check=False` and the origin
read then SUCCEEDED, because a stale remote-tracking ref is perfectly readable.
So the one existing warning ("falling back to this clone's copy, which may be
stale") could not fire: nothing had fallen back.

This is CLAUDE.md PR §1.11 inside the tool whose whole premise is that a fetch
happened -- "could not run" folded into "passed" -- and it is disciplines item 8
exactly (docs/2026-09-13-cross-domain-disciplines.md): the gyro reads perfectly
smoothly the entire time it is wrong. **A check that cannot say how old its
evidence is has not been re-referenced at all.**

Worth naming, because it is why this was a blind spot and not a bug anyone would
trip over: `tools/sairn_claim_hook.py` -- the SessionStart companion -- already
tracked this. Its `try_fetch()` returns a bool and its `read_claims()` threads a
`fresh` flag through so "a fallback answer is never reported as a current one".
The freshness accounting existed in the copy that runs unattended and was
missing from the copy a human invokes before spending hours. That is the same
one-copy-fixed asymmetry this pair recorded on 2026-09-04 over
`git checkout origin/main -- .claude/claims`, with the arrow reversed.

Usage:
  python tools/sairn_claim.py check  sairnfreedom "competitive scan"
  python tools/sairn_claim.py claim  sairnfreedom "competitive scan"
  python tools/sairn_claim.py release sairnfreedom
  python tools/sairn_claim.py list [--all]

Exit codes:  0 clear / claimed   1 blocked by another session's claim   2 error
             3 the claim or release never reached origin/main
             4 CHECKED, BUT NOT AGAINST THE REMOTE -- the fetch failed or was
               skipped, so the answer is as of the last successful fetch rather
               than as of now. A distinct code on purpose: exiting 0 for both a
               fresh CLEAR and a stale one is what left nothing downstream able
               to tell them apart. It does NOT stop `claim` -- see cmd_claim().
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


# ── A RELEASED CLAIM GIVES NO SIGNAL, AND THAT COST REAL TIME (2026-09-10) ──
# `check` reported CLEAR on work another session had FINISHED minutes earlier,
# twice in one day and in both directions: cody claimed
# `sairnbiz-sb-incidents-kpi-with-no-write-path` 57 seconds after that work was
# pushed and released, and hank had a claim written for the local-only wrapper
# false-clean while reading the code that cc had already fixed hours before.
# Neither was caught by this tool. Both were caught by reading `git log`.
#
# The gap is structural, not a bug: an ACTIVE claim blocks, an EXPIRED one is
# reported -- and the SUCCESSFUL case, a claim properly released the moment the
# work landed, is the one that says nothing at all. The better a session
# behaves, the less its finished work warns anybody.
#
# So a recently-released overlapping claim is REPORTED. It does not block:
# follow-on work on the same subject is legitimate and common, and this tool's
# own rule is that it flags for a human read rather than deciding. What it must
# not do is stay silent.
RECENT_RELEASE_HOURS = float(
    os.environ.get('SAIRN_CLAIM_RECENT_RELEASE_HOURS', '24'))


def released_hours_ago(c):
    """Hours since this claim was released, or None if it was not or cannot be read.

    Tolerant on purpose. `released_at` is an ISO-Z string with no companion
    epoch field, and this runs inside a tool every session invokes constantly --
    a parse failure here must degrade to "say nothing" rather than take the
    claim tool down for four clones.
    """
    if c.get('status') != 'released':
        return None
    raw = c.get('released_at')
    if not raw:
        return None
    try:
        txt = str(raw).strip().replace('Z', '+0000')
        if '+' not in txt and '-' not in txt[10:]:
            txt += '+0000'
        stamp = time.mktime(time.strptime(txt[:19], '%Y-%m-%dT%H:%M:%S'))
        # strptime gives local time for a UTC string; correct for the offset so
        # a fresh release does not read as hours old on a non-UTC machine.
        stamp -= time.timezone if not time.daylight else time.altzone
        return (now() - stamp) / 3600.0
    except Exception:                                       # noqa: BLE001
        return None


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


def published_claim_ids():
    """The ids of MY active claims as origin/main holds them right now.

    Returns None when origin/main's copy cannot be read at all -- a distinct
    third state from "an empty set", and the caller must not fold the two
    together (PR 1.11). "Could not tell" is not "not published", and it is not
    "published" either.

    Reads with `git show`, which cannot write the index or the working tree --
    the same reason load_all(from_origin=True) reads that way rather than
    checking anything out. Section 6 of tests/claims/run_push_verify_probe.py
    asserts the whole tool leaves the tree alone while reading.
    """
    rel = os.path.relpath(my_file(), REPO).replace(os.sep, '/')
    r = subprocess.run(['git', 'show', 'origin/main:' + rel],
                       cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        # The file may simply not exist on origin yet -- a session that has
        # never published a claim. That is READABLE and means "none published",
        # so it is only unknown if origin/main itself is unreadable.
        ok = subprocess.run(['git', 'rev-parse', '--verify', 'origin/main'],
                            cwd=REPO, capture_output=True, text=True)
        return set() if ok.returncode == 0 else None
    try:
        doc = json.loads(r.stdout)
    except ValueError:
        return None
    return set(c.get('id') for c in doc.get('claims', [])
               if c.get('status') == 'active')


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


# ── HOW OLD IS THE ANSWER: the fetch, not the commit date (2026-09-14) ─────
STALE_RC = 4

# The instant of the last SUCCESSFUL fetch, written by this tool and nothing
# else. Two things it deliberately is NOT:
#
#   * NOT `.git/FETCH_HEAD`. That was the first implementation and it was
#     WRONG IN THE DANGEROUS DIRECTION -- measured, not reasoned about:
#     `git clone` never writes FETCH_HEAD at all, and a FAILED fetch CREATES
#     and touches it (`git fetch` exit 128 against a dead remote left the file
#     0.00 hours old). So the age would have read "1 minute ago" on a view five
#     hours stale, immediately after the fetch that failed to refresh it. That
#     is the `gate_column_check` 18.7-hour understatement recommitted by the
#     code written to avoid it, and only the mutation control caught it.
#   * NOT in the working tree. An untracked file in REPO shows as `??` and
#     makes every clean-tree-dependent probe skip -- the reason
#     `run_all_tests.py` puts its own lock outside the repo too.
FETCH_STAMP = 'sairn-claim-last-fetch'


def git_dir():
    """Absolute path to this clone's `.git`, or None."""
    d = sh(['git', 'rev-parse', '--git-dir'], check=False)
    if not d:
        return None
    return d if os.path.isabs(d) else os.path.join(REPO, d)


def fetch_origin():
    """(ok, error_line). A failed fetch is a FACT, not a detail to swallow.

    Replaces `sh(['git','fetch','origin'], check=False)` at both call sites. That
    form discarded the result, which is the whole defect in the header: the
    verdict printed afterwards claimed a currency the run had not achieved.

    Stamps the success instant, so the NEXT run that cannot reach the remote can
    say how old its answer is.
    """
    r = subprocess.run(['git', 'fetch', 'origin'], cwd=REPO,
                       capture_output=True, text=True)
    if r.returncode == 0:
        d = git_dir()
        if d:
            try:
                with open(os.path.join(d, FETCH_STAMP), 'w') as f:
                    f.write('%f\n' % now())
            except OSError:
                pass        # an unwritable .git must not take this tool down
        return True, ''
    text = (r.stderr or r.stdout or '').strip().split('\n')
    # The FIRST fatal line, not the last one. Git's dead-remote error ends with
    # "and the repository exists.", which is advice rather than the error.
    fatal = [ln.strip() for ln in text if ln.strip().startswith('fatal:')]
    return False, (fatal[0] if fatal else (text[0].strip() if text else ''))


def last_fetch_hours():
    """Hours since the last SUCCESSFUL fetch, or None if it cannot be measured.

    Reads the epoch this tool WROTE when a fetch returned 0 -- the content, not
    the file's mtime, because the content records the instant of the observation
    and an mtime records whatever last happened to the file.

    NOT the commit date of origin/main's tip, and that choice is the point.
    `gate_column_check.py` measured freshness from a git commit date and
    reported a capture as 25 hours old when it was 43.3 -- an 18.7-hour
    UNDERSTATEMENT, in the direction that makes stale data look current
    (docs/2026-09-13-claim-provenance-chain-design.md, Q1). Freshness is
    measured from when the measurement was TAKEN. Here the measurement is the
    fetch; when somebody else last happened to commit is a different question,
    and answering it instead is how that 18.7 hours went missing.

    Returns None rather than 0 whenever it cannot tell -- no stamp yet on this
    clone, an unreadable one, or a value in the future from a clock that moved.
    "Unknown" and "just now" are the two answers that must never be confused,
    and this is the direction that errs toward saying so out loud.
    """
    d = git_dir()
    if not d:
        return None
    try:
        with open(os.path.join(d, FETCH_STAMP)) as f:
            hrs = (now() - float(f.read().strip())) / 3600.0
    except (OSError, ValueError):
        return None
    return None if hrs < 0 else hrs


def fetch_age_str(hrs):
    """The age in the unit that carries the information at that magnitude.

    `%.1f hours` renders a two-minute-old fetch as "0.0 hours ago", which is
    the display defect disciplines item 4 records against the margin printer:
    a number that cannot distinguish the two cases a reader is deciding
    between is worse than no number. Minutes under an hour, days over two.
    """
    if hrs is None:
        return 'AT A TIME THIS CANNOT MEASURE'
    if hrs < 1:
        mins = max(1, int(round(hrs * 60)))
        return '%d minute%s ago' % (mins, '' if mins == 1 else 's')
    if hrs > 48:
        return '%.1f DAYS ago' % (hrs / 24.0)
    return '%.1f hours ago' % hrs


def freshness_lines(fetched, err, skipped):
    """The age of the evidence a verdict rests on -- printed only when it is
    not NOW.

    Deliberately silent on a successful fetch. A banner that prints every run
    is one a reader learns to skip, which would cost exactly the line that
    matters; and on a good fetch the verdict really is current.

    The wording is taken from the platform's worked example for this,
    `tools/schema_snapshot_freshness.py`: state the age, say which instrument
    loses a disagreement, and say what to do about it.
    """
    if fetched:
        return []
    age = fetch_age_str(last_fetch_hours())
    lines = ['',
             'THE REMOTE WAS NOT READ ON THIS RUN -- %s.'
             % ('--no-fetch was passed' if skipped else 'the git fetch FAILED'),
             'EVERY VERDICT ABOVE IS AS OF THE LAST SUCCESSFUL FETCH, %s, '
             'NOT AS OF NOW.' % age,
             'A claim another session pushed since then is invisible here, and '
             'one shown as active may already have been released.']
    if err:
        lines.append('  fetch error: ' + err)
    lines.append('Get the network up and re-run before spending hours on the '
                 'strength of this. Exit code %d says the same to a script.'
                 % STALE_RC)
    return lines


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
        # ── "NOTHING TO COMMIT" IS NOT "NOTHING TO PUBLISH" (2026-09-14) ──────
        # The comment here used to read "Nothing to publish, so nothing can be
        # invisible", and that is false in the one case that matters: an EARLIER
        # run already wrote this exact file and committed it, and its push
        # failed. The local file then matches, this returns True, and the caller
        # prints CLAIMED over a commit no other clone can see. cmd_release()
        # already guards this exact case in its own no-match branch; the write
        # path did not.
        if push and not on_origin(sh(['git', 'rev-parse', 'HEAD'])):
            print('  ...but HEAD is not on origin/main, so an earlier write may '
                  'be committed here and unpublished. Publishing it.')
            return push_verified()
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
    # ── NAME THE DIRTY TREE, BECAUSE IT IS THE CAUSE AND "push it yourself"
    #    WILL NOT WORK EITHER (2026-09-14) ─────────────────────────────────────
    # Measured cause of every failure in this session: one unstaged file makes
    # `git rebase origin/main` exit 1 with "cannot rebase: You have unstaged
    # changes" on all three attempts, so the push never runs. git's own line was
    # printed as `last error` and read straight past, because the headline said
    # to push and pushing by hand fails identically. The actionable instruction
    # is to clean the tree.
    dirty = sh(['git', 'status', '--porcelain', '--untracked-files=no'],
               check=False)
    if dirty:
        print('')
        print('  THE WORKING TREE IS DIRTY, AND THAT IS ALMOST CERTAINLY WHY.')
        print('  `git rebase` refuses outright with unstaged changes, so no push')
        print('  was ever attempted. Commit or stash these, then re-run the same')
        print('  claim -- re-running is a RETRY and will not add a second entry:')
        for line in dirty.split('\n')[:8]:
            print('    ' + line)
    print('  Then confirm with: python tools/sairn_claim.py list')
    return False


def cmd_check(args, quiet=False):
    fetched, ferr = False, ''
    if not args.no_fetch:
        # Read claims as they exist on origin/main, not just locally -- a claim
        # another session pushed is only visible here after a fetch, and this is
        # the whole reason the check can be trusted at all. Which is exactly why
        # the RESULT of the fetch is kept now instead of discarded: if it
        # failed, that reason did not hold on this run and the verdict has to
        # say so. See the header.
        # NO `git checkout origin/main -- .claude/claims` here. It overwrites AND
        # STAGES the working tree; read_origin_claims() reads the same bytes
        # with `git show` and cannot write anything. See its docstring.
        fetched, ferr = fetch_origin()
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
            # A stale BLOCK is reported too, and it is not the harmless
            # direction people assume: the claim blocking you may have been
            # released since the last fetch, so the note is the difference
            # between confirming with the other session and waiting 4 hours
            # for nothing.
            for ln in freshness_lines(fetched, ferr, args.no_fetch):
                print(ln)
        # A block stays a block -- 1 is the actionable code and must not be
        # displaced by the staleness one. The staleness is in the text.
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
        _report_recent_releases(load_all(from_origin=not args.no_fetch),
                                me, subj, task)
        for ln in freshness_lines(fetched, ferr, args.no_fetch):
            print(ln)
    return 0 if fetched else STALE_RC


def _report_recent_releases(claims, me, subj, task):
    """Name overlapping work another session FINISHED recently. Never blocks.

    See RECENT_RELEASE_HOURS for why this exists: a properly released claim was
    the one state this tool said nothing about, and it is the state that means
    "somebody just did this".
    """
    recent = []
    for c in claims:
        if c.get('session') == me:
            continue
        hrs = released_hours_ago(c)
        if hrs is None or hrs < 0 or hrs > RECENT_RELEASE_HOURS:
            continue
        if not overlaps(c, subj, task):
            continue
        recent.append((hrs, c))
    if not recent:
        return
    recent.sort(key=lambda x: x[0])
    print('\nNote: %d overlapping claim(s) were RELEASED in the last %g hours. '
          'Not blocking -- follow-on work is normal -- but READ THE COMMIT '
          'before repeating any of it:' % (len(recent), RECENT_RELEASE_HOURS))
    for hrs, c in recent:
        print('  %s: %s -- %s  (finished %.1fh ago)'
              % (c.get('session'), c.get('subject'), c.get('task') or '(no task)', hrs))
    print('This tool said CLEAR on finished work twice on 2026-09-10, in both '
          'directions. `git log --oneline -15` is the check that caught it both '
          'times; this note is so it does not depend on remembering.')


def cmd_claim(args):
    rc = cmd_check(args)
    stale_check = rc == STALE_RC
    if stale_check:
        # STALE DOES NOT ABORT, and that is a decision rather than an oversight.
        # Refusing to claim without a fetch would make the tool unusable the
        # moment the network is down, and this file already records what that
        # costs: "a gate that must be talked past routinely is a gate people
        # learn to talk past" -- six false blocks, six overrides. The two halves
        # also fail differently. The COLLISION half genuinely degrades on stale
        # data. The PUBLISH half does not: save_mine() -> push_verified() ->
        # on_origin() proves the claim reached the remote or returns 3, so a
        # claim that lands was never published on stale evidence.
        print('\nPROCEEDING ANYWAY on a check that did not reach the remote. '
              'The publish half below is still verified against origin/main; '
              'it is the COLLISION half above that is only as current as the '
              'last fetch.')
    elif rc != 0:
        return rc
    subj, task = args.subject, ' '.join(args.task)
    doc = load_mine()
    ts = now()
    doc['session'] = session_name()

    # ── RE-CLAIMING THE SAME THING IS A RETRY, NOT A SECOND CLAIM ─────────────
    # Added 2026-09-14 after six unreleased claims appeared in the record, three
    # of them IDENTICAL and 30-45 seconds apart from this session, and three more
    # 13-29 seconds apart from cc the same hour. Neither was a loop and neither
    # was carelessness: save_mine() COMMITS the claim before it pushes, and when
    # the push fails it prints "treat this as NOT CLAIMED" and LEAVES THE COMMIT
    # THERE. The operator does the sensible thing and re-runs; each re-run
    # appends another entry; and whatever pushes next publishes all of them.
    #
    # So the tool reported a refusal it had not performed, and the claim it said
    # did not happen happened anyway, later, three times. That is PR 1.11's shape
    # on the WRITE side -- f5855e31 fixed the same family on the READ side, where
    # `check` printed CLEAR after its fetch had failed.
    #
    # REPRODUCED, NOT INFERRED: the trigger was one unstaged file in the working
    # tree. `git rebase origin/main` then exits 1 with "cannot rebase: You have
    # unstaged changes" on all three attempts, so the push never gets to run.
    same = [c for c in doc['claims']
            if c.get('status') == 'active'
            and c.get('subject') == subj
            and c.get('task') == task]
    if same:
        print('\nALREADY CLAIMED BY THIS SESSION -- not adding a second entry.')
        print('  claimed at: %s' % same[-1].get('claimed_at'))
        print('  This is a RETRY of the same claim, so the only thing left to do')
        print('  is publish the commit that is already sitting here.')
        if args.no_push:
            print('  --no-push: nothing published. Other clones still cannot see it.')
            return 3
        if on_origin(sh(['git', 'rev-parse', 'HEAD'])):
            print('  ...and it is already on origin/main. Nothing to do.')
            return 0
        if not push_verified():
            print('\nSTILL NOT CLAIMED -- the earlier claim is committed here and')
            print('every other clone still sees this work as unclaimed.')
            return 3
        print('\nCLAIMED (the earlier entry, now published). Release it when the '
              'work closes:')
        print('  python tools/sairn_claim.py release %s' % subj)
        return 0

    # ── A RETYPED TASK STRING IS STILL A RETRY, AND THE GUARD ABOVE MISSES IT ─
    # Added 2026-09-14 (CC). The guard above compares `task` BYTE FOR BYTE, and
    # befb65e3's own evidence says the real incident was not byte-identical:
    # "cc has three for item 92 ... with the task string slightly retyped
    # between attempts". Driven against the real tool with the two real strings
    # from that incident, three attempts still produced TWO published claims:
    #
    #   attempt 1  "item 92 functional core imperative shell on sbThreeWayMatch and ledger"
    #   attempt 2  "...sbThreeWayMatch and ledger money rule"   <- NOT recognised
    #   attempt 3  same as 2                                     <- recognised
    #
    # So the fix halved the defect on the case it was measured against and did
    # not close it. A person retyping after a reported failure is the ONLY way
    # this state is reached -- a machine would repeat the string exactly -- so
    # the retyped case is the likelier half, not the edge case.
    #
    # WHY THIS REFUSES RATHER THAN MERGING. Folding a different task string into
    # the existing entry would silently rewrite WHAT WAS CLAIMED, and the record
    # would then name work nobody chose to claim. Folding the other way -- a new
    # entry -- is the defect. Both guesses are wrong in a way nothing downstream
    # can see, so the tool names both strings and lets the operator say which.
    #
    # SCOPED TO AN UNPUBLISHED CLAIM, which is what makes it safe. Once the
    # earlier claim is on origin/main this state cannot arise from a failed
    # push, and a second claim on the same subject is ordinary. `published_claim_ids`
    # returns None when origin cannot be read, and that is treated as UNPUBLISHED
    # -- fail closed: an unreadable origin is also an origin nothing can be
    # published to, so the refusal costs nothing that was going to work anyway.
    stuck = []
    if not args.no_push:
        published = published_claim_ids()
        for c in doc['claims']:
            if c.get('status') != 'active' or c.get('subject') != subj:
                continue
            if published is None or c.get('id') not in published:
                stuck.append(c)
    if stuck:
        earlier = stuck[-1]
        print('\nNOT CLAIMED -- and nothing was added, deliberately.')
        print('')
        print('THIS SESSION ALREADY HAS AN UNPUBLISHED CLAIM ON "%s"' % subj)
        print('with a DIFFERENT task string. That is what a retype after a failed')
        print('push looks like, and appending a second entry is the defect that')
        print('put three claims for one piece of work into the record.')
        print('')
        print('  already here (unpublished): %s' % (earlier.get('task') or '(no task)'))
        print('  claimed at                : %s' % earlier.get('claimed_at'))
        print('  you just typed            : %s' % (task or '(no task)'))
        print('')
        print('IF THIS IS THE SAME WORK -- clear whatever blocked the push (a dirty')
        print('tree is the usual cause; `git status` names it), then re-run the')
        print('EARLIER wording, which publishes the entry already written:')
        print('  python tools/sairn_claim.py claim %s %s' % (subj, earlier.get('task') or ''))
        print('')
        print('IF IT IS GENUINELY DIFFERENT WORK -- publish or release the one above')
        print('first, then claim this. Two claims on one subject is fine; two')
        print('claims for one piece of work is what this refuses.')
        return 3

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
        # The entry IS written and committed here; that is not a leak any more
        # because re-running the same claim is now a retry rather than a second
        # entry. Say so, so the obvious next action is also the safe one --
        # before this, "re-run" is exactly what produced three identical claims.
        print('Clear whatever the reason above names, then RE-RUN THIS SAME '
              'COMMAND.')
        print('It is a retry: the entry already written will be published, and '
              'no second entry is added.')
        return 3
    print('\nCLAIMED. Release it when the work closes:')
    print('  python tools/sairn_claim.py release %s' % subj)
    if stale_check:
        # The push just proved the remote is reachable NOW, which means the
        # collision check can finally be made for real -- and it is the cheap
        # half. Saying it here rather than leaving the session to infer it.
        print('\nThe collision check ran before the remote was readable. It is '
              'readable now (the claim landed), so re-run it:')
        print('  python tools/sairn_claim.py check %s %s' % (subj, task))
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
    fetched, ferr = False, ''
    if not args.no_fetch:
        # NO `git checkout origin/main -- .claude/claims` here. It overwrites AND
        # STAGES the working tree; read_origin_claims() reads the same bytes
        # with `git show` and cannot write anything. See its docstring.
        fetched, ferr = fetch_origin()
    rows = load_all(from_origin=not args.no_fetch)
    if not args.all:
        rows = [c for c in rows if is_active(c)]
    if not rows:
        # "No active claims" off a stale ref is the most misleading output this
        # tool can produce -- an empty list reads as permission -- so the note
        # matters MORE here, not less.
        print('No %sclaims.' % ('' if args.all else 'active '))
    else:
        rows.sort(key=lambda c: c.get('claimed_at_epoch', 0), reverse=True)
        for c in rows:
            state = ('active' if is_active(c)
                     else ('EXPIRED' if c.get('status') == 'active' else 'released'))
            print('[%-8s] %-6s %-16s %s  (%s)'
                  % (state, c.get('session'), c.get('subject'), c.get('task'),
                     age_str(c)))
    for ln in freshness_lines(fetched, ferr, args.no_fetch):
        print(ln)
    return 0 if fetched else STALE_RC


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
