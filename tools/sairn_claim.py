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
import calendar
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
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sairn_session_identity as _identity            # noqa: E402
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


# ── A STRUCTURED IDENTIFIER IS ONE THING OR IT IS NOTHING ───────────────────
# TOOL-BUGS ITEM 6, INSTANCE 8, AND A FOURTH DISTINCT MECHANISM (2026-09-22).
#
# Two Tier A discharge claims opened ONE MINUTE apart -- hank's
# `2026-09-22T12:02:38Z` and fourth's `2026-09-22T12:01:35Z` -- and this
# matcher refused with `blocked by: shared phrase "2026 22t12"`. The two pieces
# of work ran in OPPOSITE directions (hank reviewing fourth's change, fourth
# reviewing hank's) over disjoint file sets. The only thing in common was the
# minute.
#
# The cause is one line: `word_seq` splits on `[^a-z0-9]+`, so the lowercased
# timestamp became the words `2026`, `22t12` and `38z`, and a bigram straddling
# two of them read as a shared phrase.
#
# WHY THIS CLASS IS EXPENSIVE, and it is worth saying in the file rather than
# only in the register: an obligation id is the ONE token a discharge claim
# must carry to be identifiable at all, so NAMING THE THING MORE PRECISELY MADE
# THE COLLISION MORE LIKELY. That inverts the incentive on exactly the field
# this tool most needs people to fill in honestly, and the workaround it
# invites -- dropping or fuzzing the id -- is worse than the block.
# sairn-code-scrubber item 25.
#
# THE RULE: an identifier is matched WHOLE, by its own syntax, or not at all.
# Never a prefix, a bigram or a substring of one.
#
#   TIMESTAMP -- an obligation id. Matched whole, and a MATCH IS A REAL
#                COLLISION: two sessions discharging one obligation.
#   SHA       -- the same, and it was not matched at all before: a claim to
#                revert 467baf74 and a claim to extend it answered CLEAR.
#   DATE      -- a bare date is STRIPPED and is NOT an identifier. Two claims
#                on the same day are not related, and promoting a date would
#                make every same-day pair collide -- the original bug with a
#                wider blast radius.
TIMESTAMP_RE = re.compile(r'\d{4}-\d{2}-\d{2}[t ]\d{2}:\d{2}:\d{2}(?:\.\d+)?z?')
BARE_DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}')
# EIGHT, NOT SEVEN, AND A DIGIT IS REQUIRED. `defaced` is seven hex characters
# with no digit, and a rule keyed on hex alone would take it out of the word
# stream and then report two unrelated claims as sharing a commit. Requiring a
# digit costs nothing real: the chance an 8-character sha has none is (6/16)^8,
# about four in ten thousand.
SHA_TOKEN_RE = re.compile(r'\b(?=[0-9a-f]*\d)[0-9a-f]{8,40}\b')


def structured_ids(*parts):
    """Every whole structured identifier in the given strings.

    Returned as ('timestamp'|'commit', value) pairs so the refusal can NAME
    what it matched -- "same obligation" and "same commit" are different facts
    and a reader can act on the difference.
    """
    out = set()
    for p in parts:
        low = (p or '').lower()
        for m in TIMESTAMP_RE.findall(low):
            out.add(('timestamp', m.rstrip('z')))
        for m in SHA_TOKEN_RE.findall(TIMESTAMP_RE.sub(' ', low)):
            out.add(('commit', m))
    return out


def shared_structured(mine, theirs):
    """Shared identifiers, with a SHA matching its own longer form.

    A short sha and the full one are the same commit, and a session that wrote
    the full 40 characters must not slip past a session that wrote 8 -- being
    more precise is exactly what this whole change is about not punishing.
    """
    hit = set()
    for kind_a, val_a in mine:
        for kind_b, val_b in theirs:
            if kind_a != kind_b:
                continue
            if kind_a == 'commit':
                n = min(len(val_a), len(val_b))
                if n >= 8 and val_a[:n] == val_b[:n]:
                    hit.add((kind_a, val_a if len(val_a) <= len(val_b) else val_b))
            elif val_a == val_b:
                hit.add((kind_a, val_a))
    return hit


def _strip_identifiers(text):
    """Blank every structured identifier so its FRAGMENTS never become words."""
    low = (text or '').lower()
    low = TIMESTAMP_RE.sub(' ', low)
    low = BARE_DATE_RE.sub(' ', low)
    return SHA_TOKEN_RE.sub(' ', low)


def word_seq(text):
    """Significant words IN ORDER -- phrase matching needs the order that
    tokens() throws away.

    Structured identifiers are removed FIRST. They are compared whole by
    shared_structured(); leaving their fragments in the word stream is what
    produced `shared phrase: "2026 22t12"` between two unrelated reviews.
    """
    return [t for t in re.split(r'[^a-z0-9]+', _strip_identifiers(text))
            if len(t) >= 3 and t not in STOPWORDS]


def bigrams(*parts):
    """Adjacent significant-word PAIRS, UNORDERED, across the joined parts.

    ── TWO DEFECTS FIXED HERE, BOTH MEASURED LIVE (2026-09-15) ──────────────
    This used to build ORDERED bigrams WITHIN each part separately, and both
    halves of that produced false CLEARs on the same afternoon:

      * ORDER. `"CRLF recombination"` and `"recombination crlf"` are the same
        phrase and produced no match. Word order in a hand-typed task string
        carries no meaning, so a pair is now a frozenset and matches either way.
      * THE SUBJECT/TASK BOUNDARY. The CLI takes argv[0] as the SUBJECT and the
        rest as the TASK, so `check recombination crlf lf false alarm` split one
        sentence the user typed into `subject="recombination"` +
        `task="crlf lf ..."` -- and a pair straddling that split could never be
        seen. The subject had ONE word, so it produced no pairs at all.

    THE LIVE CASE: Hank probed `recombination crlf lf false alarm` against
    Cody's active `... CRLF recombination ...`. Both `crlf` and `recombination`
    were shared TOKENS, and the tool still answered CLEAR, because the only
    phrase evidence it could form was order-sensitive and boundary-bound.

    Joining rather than iterating also means a pair can span a comma, which is
    right: a claim is a list of subjects separated by commas and the words
    either side of one are as adjacent as any other pair.
    """
    w = []
    for p in parts:
        w.extend(word_seq(p))
    return {frozenset((w[i], w[i + 1]))
            for i in range(len(w) - 1) if w[i] != w[i + 1]}


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


# ── THE PRIMARY CHECK IS THE FILE SET, AND THE LEXICAL ONE IS A WARNING ────
# (2026-09-22. The measurement is below and it is the whole argument.)
#
# Every rule in block_reason() answers "do these two strings talk about the
# same thing". That is a proxy, and the thing it is a proxy FOR is "would these
# two sessions edit the same file". The convention that makes the real question
# answerable arrived on 2026-09-21: claims now carry `FILES: <paths>` in the
# task text. 31 of the most recent claims declare one.
#
# MEASURED over every cross-session pair among the claims that declare files
# -- 318 pairs, using the tool's own block_reason():
#
#     153 pairs BLOCK today
#      43 of those have INTERSECTING file sets   <- real, still blocked
#     110 of those have DISJOINT file sets       <- 72%, false, now cleared
#
# The 110 are not marginal. They include `shared phrase: "html tests"` between
# a SAIRNlegacy hydration claim and a SAIRNlaw trust-clearance claim, and
# `same app: sairnlegacy` between a hydration claim and one whose declared
# files are three api/ test files in other apps entirely. That second one
# blocked two different sessions three times each in a single night.
#
# ── WHY THIS IS NOT "LOOSENING THE MATCHER" ────────────────────────────────
# This file already records, twice, that the honest fix is always a NARROWER
# NEW SIGNAL and never a looser existing one, and that every gap resolves to
# CLEAR rather than to a doubt. Both still hold. The file set is a narrower and
# STRONGER signal than any word overlap: it is what the two sessions actually
# said they would touch. What is being removed is not a check -- it is a proxy,
# in the cases where the real evidence is present and says the proxy was wrong.
#
# ── AND IT IS THREE STATES, NOT TWO, WHICH IS THE PART THAT KEEPS IT SAFE ──
#   BOTH claims declare files, and they INTERSECT   -> refuse. The strongest
#                                                      signal this tool has
#                                                      ever had.
#   BOTH declare files, and they are DISJOINT       -> no block. The lexical
#                                                      hit is printed as a
#                                                      WARNING so nothing is
#                                                      hidden.
#   EITHER declares nothing                          -> COULD NOT TELL. The
#                                                      lexical matcher decides,
#                                                      byte-for-byte as before.
#
# The third state is why this cannot weaken anything by accident. 774 of the
# 805 claims in the record declare no files; every one of them keeps exactly
# the behaviour it has today, and the tool SAYS SO in its output rather than
# leaving a reader to assume the file check ran.
#
# ── THE INCENTIVE THIS CREATES, STATED BECAUSE IT IS REAL ──────────────────
# Making the file set authoritative rewards under-declaring it. That is the
# same failure as rewording a task string past the matcher, in a new costume,
# and PR 4.3 forbids one so it forbids the other. Two things are done about it
# and neither is sufficient alone: the parsed set is STORED on the claim record
# (`files`), so a later audit can compare declared paths against what the
# session actually changed; and a claim that declares nothing is named in the
# output every time, so "no files declared" is visible rather than silent.
FILES_DECL = re.compile(r'FILES:\s*(.*?)(?:\s+--\s|$)', re.I | re.S)
# A path is a token carrying a dot-extension. Deliberately NOT "any word with a
# slash": `docs/` alone is a directory claim this tool cannot reason about, and
# guessing at it would put the file check back into the proxy business.
FILE_TOKEN = re.compile(r'[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]{1,5}')


def declared_files(task):
    """The file set a claim's task DECLARES, or None when it declares none.

    None and empty are different and the difference decides everything below:
    None means "this claim gave no file evidence", empty would mean "it gave
    evidence that it touches nothing". Only the first is reachable, and it is
    the one that must fall back to the lexical matcher rather than to CLEAR.
    """
    m = FILES_DECL.search(task or '')
    if not m:
        return None
    found = {f.replace('\\', '/') for f in FILE_TOKEN.findall(m.group(1))}
    return found or None


def file_verdict(mine_task, their_task):
    """('refuse'|'clear'|'unknown', shared_paths).

    'unknown' is the honest answer when either side declared nothing, and the
    caller must then fall through to the lexical matcher unchanged.
    """
    a, b = declared_files(mine_task), declared_files(their_task)
    if a is None or b is None:
        return 'unknown', set()
    shared = a & b
    return ('refuse' if shared else 'clear'), shared


def block_reason(mine_subj, mine_task, their_subj, their_task):
    """Why these two claims collide, or None if they only share vocabulary.

    ── EVERY RULE HERE IS A POSITIVE SIGNAL, AND THAT IS THE SHARED CAUSE ────
    Worth stating once, at the top, because this file has now had two defects
    of apparently different shapes and they are the same defect underneath.
    2026-09-17's false CLEAR (a brief restatement of an active claim, below)
    and the duplicate-claim family the GUARDS table records both end the same
    way: NO BLOCK. Nothing in this function fires on absence. It is an OR of
    things that must be spotted, so every gap in the rule set -- a scope the
    matcher was never pointed at, a phrasing it cannot survive -- resolves to
    CLEAR rather than to an error or a doubt.
    That is why each one costs real work before anybody notices, and why the
    honest fix is always a NARROWER new signal measured against the corpus,
    never a looser existing one.

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
    # ── IDENTIFIERS FIRST, BECAUSE THEY ARE THE STRONGEST EVIDENCE HERE ────
    # An obligation id or a commit sha names ONE thing. Two claims carrying the
    # same one are working on the same item, which is a better reason to block
    # than any word overlap -- and until 2026-09-22 a sha was not compared at
    # all, so "revert 467baf74" and "extend 467baf74" answered CLEAR.
    sid = shared_structured(structured_ids(mine_subj, mine_task),
                            structured_ids(their_subj, their_task))
    if sid:
        kind, val = sorted(sid)[0]
        return ('same obligation: %s' % val) if kind == 'timestamp' \
            else ('same commit: %s' % val)
    shared_apps = apps_in(mine_subj, mine_task) & apps_in(their_subj, their_task)
    if shared_apps:
        return 'same app: ' + ', '.join(sorted(shared_apps))
    shared_ids = idents(mine_subj, mine_task) & idents(their_subj, their_task)
    if shared_ids:
        return 'same file or resource: ' + ', '.join(sorted(shared_ids))
    shared_phrase = bigrams(mine_subj, mine_task) & bigrams(their_subj, their_task)
    if shared_phrase:
        pair = sorted(sorted(shared_phrase, key=lambda p: sorted(p))[0])
        return 'shared phrase: "%s"' % ' '.join(pair)
    # ── ONE TASK'S WORDS ARE ALL INSIDE THE OTHER'S (2026-09-17) ───────────
    # THE FALSE CLEAR THIS CLOSES, reproduced exactly. Fourth checked
    #
    #     "tier A rotation"
    #
    # while cody held, active and readable,
    #
    #     "invisible_in_pattern probe stale anchor, sairnlaw citation format
    #      rule convergence, tier A negative control rotation"
    #
    # and the answer was CLEAR. Nothing was stale and nothing failed to fetch:
    # the matcher simply could not see it. `tier` and `rotation` are ADJACENT in
    # the short phrasing and FOUR APART in the long one, and every rule above
    # this line rests on adjacency -- `bigrams()` forms adjacent pairs only. Two
    # words inserted between them makes the match vanish.
    #
    # THAT IS THE RESIDUAL THE BLOCK BELOW ALREADY NAMED, arriving for real:
    # "one intervening word breaks adjacency". A person restating their own task
    # more briefly is the commonest way it happens, and a brief restatement is
    # exactly what somebody types into `check`.
    #
    # ── THE OBVIOUS FIX WAS MEASURED AND REJECTED, AGAIN ──────────────────
    # Widening adjacency to a WINDOW (two significant tokens within k places)
    # was implemented and run over all 171,477 cross-session claim pairs in the
    # record:
    #
    #     current 5074 blocks | k=2 +154 | k=3 +294 | k=4 +440 | k=5 +575
    #
    # k=3 is the smallest that catches the incident, and READING its 294 extra
    # blocks kills it: the commonest new pairs are `validation + write` (x10),
    # `controls + suite` (x9), `path + write` (x8), `only + read` (x7). That is
    # ordinary engineering vocabulary, and a gate that fires on `only + read` is
    # one sessions learn to override -- the same verdict, for the same reason,
    # that the rare-token rule got.
    #
    # ── CONTAINMENT IS THE NARROWER RULE, AND IT COSTS ALMOST NOTHING ─────
    # If EVERY significant word of one task appears in the other, the shorter is
    # a restatement or a subset of the longer. Measured over the same 171,477
    # pairs: **+1 block.** One. (cody's "multi-tenant scope lookup ... claim
    # verification" against fourth's "v1 scope verification" -- a fair thing to
    # make somebody read, and arguably not even wrong.)
    #
    # THE TASK ONLY, NOT THE SUBJECT. The subject is a bucket name -- three of
    # the four sessions use their own session name for a whole day's work -- so
    # including it would make every pair of one session's claims contain each
    # other. Measured with it in: unusable.
    #
    # WHAT THIS STILL DOES NOT FIX, and it is the case the block below names:
    # `triage plan staleness checker` against `triage staleness tool`. Neither
    # token set contains the other (`plan`/`checker` against `tool`), and
    # `checker`/`tool` are synonyms no matcher here can know. That residual is
    # unchanged and is still open.
    mine_words = set(word_seq(mine_task))
    their_words = set(word_seq(their_task))
    if (len(mine_words) >= 2 and len(their_words) >= 2
            and (mine_words <= their_words or their_words <= mine_words)):
        smaller = mine_words if mine_words <= their_words else their_words
        return ('one task is entirely inside the other: "%s"'
                % ' '.join(sorted(smaller)))
    # ── A RARE-TOKEN RULE WAS WRITTEN HERE, MEASURED, AND REMOVED ──────────
    # Recorded rather than deleted, so the next person to notice the residual
    # gap below does not spend the afternoon rediscovering why it is still open.
    #
    # THE GAP IS REAL: `triage plan staleness checker` against an active
    # `triage staleness tool` is the same work and still answers CLEAR. No
    # adjacent pair exists in either direction -- one intervening word breaks
    # adjacency, and `checker`/`tool` are synonyms no matcher can know.
    #
    # THE OBVIOUS FIX IS WORSE THAN THE DISEASE, AND THAT IS A MEASUREMENT
    # RATHER THAN AN OPINION. Blocking on a shared token the corpus says is rare
    # (<= 4 of 593 recorded claims) was implemented and run over 20,000 sampled
    # cross-session claim pairs:
    #
    #     OLD 494 blocked  |  pair fix alone 496  |  pair fix + rare token 570
    #
    # The pair fix costs TWO extra blocks and closes a real false CLEAR. The
    # rare-token rule costs SEVENTY-FOUR more, and reading them shows why:
    # `instead` (4 claims), `into` (2), `load` (2), `number` (4), `commits` (3),
    # `cleanup` (4). RARITY IN A 593-CLAIM CORPUS IS NOT DISTINCTIVENESS -- it
    # is mostly ordinary English that happens not to recur, and STOPWORDS cannot
    # list every such word. Requiring TWO rare tokens does not rescue it either:
    # the triage case shares `staleness` (4) and `triage` (17), so only one is
    # rare, and the case that motivated the rule is the case it still misses.
    #
    # A blocking gate that fires on `into` is a gate sessions learn to override,
    # which is a worse end state than the one open gap. Left open, named here,
    # and the residual is reported rather than papered over.
    return None


def sh(args, check=True):
    r = subprocess.run(args, cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if check and r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout).strip() + '\n')
        sys.exit(2)
    return r.stdout.strip()


# ── IDENTITY COMES FROM A MARKER, NOT FROM THE FOLDER NAME (2026-09-18) ────
# Hover finding #258, HIGH. This function existed here AND in tools/tier_a_review_gate.py,
# byte for byte, and both derived identity from `os.path.basename(REPO)`. So
# "who am I" was a property of a directory name: a clone renamed `SAIRN-cody`
# would discharge its own Tier A obligation and the gate would report an
# INDEPENDENT REVIEW, and the same string decides who holds a claim, so a
# rename silently reassigns work in the other direction too.
#
# tools/sairn_session_identity.py is now the ONE implementation -- two answers
# to "who am I" is what made the self-review refusal meaningless. It reads a
# per-clone marker in .git/, the convention hover_auditor_scope_gate.py already
# uses, and it RAISES when the marker is absent rather than falling back: a
# fallback would leave the spoofable path live with nothing to say which one
# answered (PR 1.11).
#
# IT IS NOT A CRYPTOGRAPHIC CONTROL. Anything that can rename the directory can
# also write the marker. What it closes is DRIFT AND ACCIDENT -- identity stops
# being a side effect of a folder name and becomes a deliberate act with a file
# to point at.
def session_name():
    return _identity.session_name()


def now():
    return time.time()


def iso(ts):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts))


def tokens(*parts):
    out = set()
    for p in parts:
        # Same identifier strip as word_seq(), and it has to be the same or the
        # two would disagree about what a word is -- tokens() gates whether
        # block_reason() is consulted at all.
        for t in re.split(r'[^a-z0-9]+', _strip_identifiers(p)):
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
                         '.claude/claims/'], cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if ls.returncode != 0:
        return None
    for path in ls.stdout.split('\n'):
        path = path.strip()
        if not path.endswith('.json'):
            continue
        r = subprocess.run(['git', 'show', 'origin/main:' + path],
                           cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')
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


# ── THE DUPLICATE THIS TOOL COULD NOT SEE: YOUR OWN CLAIMS (2026-09-17) ─────
# Every collision check in this file begins `if c.get('session') == me:
# continue`. That is correct for the problem the tool was built for -- two
# SESSIONS doing one piece of work -- and it means the matcher has never once
# been pointed at the claims of the session running it.
#
# So the two guards in cmd_claim() are the only thing standing between one
# session and two claims for one piece of work, and both are narrow:
#
#   `same`   exact (subject, task) byte-match, so any retyping walks past it
#   `stuck`  same subject AND the earlier claim still UNPUBLISHED
#
# Once the earlier claim is on origin/main, `stuck` cannot fire at all, and a
# session can accumulate unlimited concurrent claims on overlapping work with
# nothing saying anything. BOTH live cases are that shape:
#
#   fourth  "... G7 factors, rebase resolve tool"        14:00, published
#           "rebase resolve semantic merge for the two json registers"  14:53
#   cc      "discharge mechanism, export_coverage label plus pin, alf and
#            mech export registries"                     published
#           "tier a review gate single write point, export_coverage_check
#            ... and the same two export registries"
#
# (The second cc string is abridged HERE ON PURPOSE: quoted in full it names
#  two Tier A resources, and tools/tier_a_review_gate.py then demands an
#  independent-review obligation for a COORDINATION TOOL that serves neither.
#  That is the fourth instance of the false positive its own header predicts --
#  a file whose job is to TALK ABOUT Tier A work -- and the honest response to
#  one example is to stop pasting the names, not to record an obligation that
#  would be false. The verbatim strings live in
#  tests/claims/run_own_claim_overlap_probe.py, where the arms need them.)
#
# Neither is byte-identical and neither was unpublished, so neither guard could
# fire. `audit` then reported ZERO duplicates after the guards and was right on
# its own definition -- it counts EXACT (session, subject, task) groups, and
# says in its own closing paragraph that deciding two different strings are the
# same work "would move the failure rather than remove it".
#
# THAT ARGUMENT DOES NOT SURVIVE THE MEASUREMENT, and the measurement is why
# this is a matcher change rather than a fourth special case. Over all 662
# recorded claims there are 411 pairs from ONE session that were ACTIVE AT THE
# SAME TIME. Running the tool's own block_reason() over them, with the SUBJECT
# DROPPED:
#
#     24 refuse  (shared identifier or shared phrase)
#      2 report  (same app and nothing else)
#
# Reading all 24: the item 92 triple, fourth's sv_controlled quadruple, cc's
# export-registries pair, cody's subcontractor-compliance pair. Every one is a
# real duplicate of the session's own in-flight work. The 2 reports are genuine
# separate work in one app. It is not a second guesser -- it is the SAME
# guesser, finally aimed at the claims it was never allowed to see.
#
# ── WHY THE SUBJECT IS DROPPED, WHICH IS NOT AN OVERSIGHT ─────────────────
# block_reason()'s first rule is `same subject`. Across sessions that is the
# strongest signal there is. Within one session it is NOISE: cc, cody and
# fourth all use their own session name as the subject for a whole day's work,
# so `same subject` fires on every self-pair. Measured with it left in, the
# refuse count was 33 and the extra nine were plainly unrelated work --
# "check5 exemptions, field quote wiring" against "0072 supplier lead time and
# job risk engine". A subject that says WHO rather than WHAT cannot tell you
# two tasks are the same, so it is not asked.
#
# ── WHY `same app` REPORTS AND DOES NOT REFUSE ───────────────────────────
# Two claims on one app at once is ordinary and legitimate -- this session held
# sv-audit-log-retrievability and sv-controlled-export within an hour, both
# real, both distinct. A shared IDENTIFIER or a shared PHRASE means the two
# strings describe the same THING; a shared app means only that they are in the
# same building. The tier is drawn where the measurement drew it.
def self_overlap(mine_task, their_task):
    """(reason, kind) for two claims by the SAME session. kind is
    'refuse', 'report' or None.

    Subject-free by design -- see above. Returns the tool's own block_reason()
    verdict so there is exactly one matcher on this platform, not two.
    """
    reason = block_reason('', mine_task, '', their_task)
    if not reason:
        return None, None
    return reason, ('report' if reason.startswith('same app') else 'refuse')


def my_active_overlaps(doc, task):
    """[(claim, reason, kind)] for MY still-active claims that overlap `task`.

    Uses is_active(), not the raw status field: an EXPIRED claim is one this
    tool already treats as not held, and refusing new work on the strength of
    one would block a session for ever over a row nobody ever released. Those
    are reported by cmd_check instead, where an unreleased claim is a finding
    about the record rather than about the work being claimed now.
    """
    out = []
    for c in doc.get('claims', []):
        if c.get('status') != 'active':
            continue
        reason, kind = self_overlap(task, c.get('task'))
        if not kind:
            continue
        # ── EXPIRED-BUT-UNRELEASED IS A THIRD ANSWER (2026-09-17) ─────────
        # It used to be skipped outright and that hid a real case. `audit`
        # found a post-guard same-work pair by fourth: a claim held from
        # 02:54 to 14:50 -- 11.9 hours, never released -- with a second
        # overlapping claim taken at 13:56. The guard did not fire, correctly,
        # because STALE_HOURS had already expired the first one.
        #
        # The two readings disagree and BOTH are right. The guard must use
        # expiry or a forgotten row locks a session out for ever. `audit` uses
        # the real held-span, because `released_at` is the ground truth of when
        # it stopped being held -- and by that measure the session genuinely
        # held two claims on one piece of work.
        #
        # So it is REPORTED and never blocks. "You have an expired claim on
        # this; did you finish it?" is the question, and silence was the wrong
        # answer to it.
        out.append((c, reason, 'expired' if not is_active(c) else kind))
    return out


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
                       cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        # The file may simply not exist on origin yet -- a session that has
        # never published a claim. That is READABLE and means "none published",
        # so it is only unknown if origin/main itself is unreadable.
        ok = subprocess.run(['git', 'rev-parse', '--verify', 'origin/main'],
                            cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')
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
                       cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')
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
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
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
                            cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if rb.returncode != 0:
            subprocess.run(['git', 'rebase', '--abort'], cwd=REPO,
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
            last_err = (rb.stderr or rb.stdout or '').strip().split('\n')[-1]
            continue
        sha = sh(['git', 'rev-parse', 'HEAD'])   # rebase rewrites it
        r = subprocess.run(['git', 'push', 'origin', 'HEAD:main'],
                           cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')
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
    # MY OWN overlapping claims, which every check in this file has skipped
    # since it was written. Reported here and REFUSED in cmd_claim: `check` is
    # the advisory read and must not start returning 1 for a claim the caller
    # already holds -- that would make `check` before `claim` fail on the
    # legitimate retry path. The gate belongs where the duplicate is created.
    self_hits = []
    for c in load_all(from_origin=not args.no_fetch):
        if c.get('session') == me:
            if is_active(c):
                reason, kind = self_overlap(task, c.get('task'))
                if kind:
                    self_hits.append((c, reason, kind))
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
        # ── THE FILE SET DECIDES WHEN BOTH SIDES GAVE ONE (2026-09-22) ────
        # See the header above declared_files(). A lexical hit over DISJOINT
        # declared files is demoted to the warning list rather than blocking;
        # a file intersection blocks even when no word matched, which is the
        # direction this change makes STRICTER and the reason it is not a
        # loosening.
        fv, fshared = file_verdict(task, c.get('task'))
        if fv == 'refuse':
            reason = ('same declared FILES: ' + ', '.join(sorted(fshared))
                      + ((' (and ' + reason + ')') if reason else ''))
        elif fv == 'clear' and reason:
            weak.append((c, shared, 'LEXICAL ONLY -- ' + reason
                         + '; the declared file sets are DISJOINT'))
            continue
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
        # PRINTED FIRST, BEFORE THE CLEAR SINKS IN. "CLEAR" answers a question
        # about the OTHER sessions and always has; a reader who already holds a
        # claim on this work needs to know that before anything else on the
        # screen, because the duplicate they are about to create is their own.
        if self_hits:
            hard = [x for x in self_hits if x[2] == 'refuse']
            print('')
            print('BUT YOU ALREADY HOLD %d ACTIVE CLAIM(S) THAT OVERLAP THIS WORK.'
                  % len(self_hits))
            for c, reason, kind in self_hits:
                print('  %-9s %s -- %s' % ('[SAME WORK]' if kind == 'refuse'
                                           else '[same app]',
                                           c.get('subject'), c.get('task') or '(no task)'))
                print('            claimed %s, overlaps on: %s' % (age_str(c), reason))
            if hard:
                print('  `claim` will REFUSE this. Either carry on under the claim you')
                print('  already hold, or release it first so the record says one thing.')
        if weak:
            # ── TWO KINDS OF WEAK NOW, AND ONE SENTENCE CANNOT COVER BOTH ──
            # (2026-09-22.) This printed "share WORDS ... but no app, file,
            # subject or phrase" for everything in the list. That is still true
            # of a plain vocabulary overlap, and it became FALSE the moment a
            # lexical BLOCK could be demoted here on disjoint file sets: for
            # those the phrase matched, and saying it did not would be this
            # tool telling a reader the opposite of why the entry is in front
            # of them. Caught by the probe asserting the demoted reason reaches
            # the output -- the arm went red on a sentence, not on a verdict,
            # which is the only reason it was noticed at all.
            demoted = [w for w in weak if w[2]]
            plain = [w for w in weak if not w[2]]
            if demoted:
                print('\nNote: %d active claim(s) MATCHED the word matcher and are '
                      'NOT blocking, because the FILES each claim declares do not '
                      'overlap. The match is shown so you can overrule it -- a '
                      'declared file list is only as good as the session that '
                      'wrote it:' % len(demoted))
                for c, shared, reason in demoted:
                    print('  %s: %s -- %s' % (c.get('session'), c.get('subject'),
                                              c.get('task')))
                    print('      %s' % reason)
                    print('      your files : %s'
                          % ', '.join(sorted(declared_files(task) or [])))
                    print('      their files: %s'
                          % ', '.join(sorted(declared_files(c.get('task')) or [])))
            if plain:
                print('\nNote: %d active claim(s) share WORDS with this task but no '
                      'app, file, subject or phrase, so they are NOT blocking. '
                      'Shown so you can judge, not because the tool thinks they '
                      'overlap:' % len(plain))
                for c, shared, _reason in plain:
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

    # ── AND THE SAME WORK UNDER ANY OTHER WORDING OR SUBJECT ────────────────
    # The two guards above are byte-match and same-subject-unpublished. This is
    # the general case they are both special cases of, and it is the one both
    # live incidents took. See self_overlap() for the measurement that set the
    # refuse/report line.
    mine = my_active_overlaps(doc, task)
    refuse = [x for x in mine if x[2] == 'refuse']
    report = [x for x in mine if x[2] == 'report']
    expired = [x for x in mine if x[2] == 'expired']
    if refuse:
        print('\nNOT CLAIMED -- and nothing was added, deliberately.')
        print('')
        print('THIS SESSION ALREADY HOLDS AN ACTIVE CLAIM ON WORK THIS OVERLAPS.')
        print('Not the same subject and not the same wording -- the same THING,')
        print('by the matcher this tool already uses on every other session:')
        print('')
        for c, reason, _k in refuse:
            print('  already held : %s -- %s' % (c.get('subject'), c.get('task') or '(no task)'))
            print('  claimed at   : %s (%s)' % (c.get('claimed_at'), age_str(c)))
            print('  overlaps on  : %s' % reason)
            print('')
        print('  you just typed: %s' % (task or '(no task)'))
        print('')
        print('TWO CLAIMS FOR ONE PIECE OF WORK IS THE DEFECT, and it is invisible')
        print('once it is written: `list` shows two rows, another session reads two')
        print('blocks, and nothing downstream can tell them from real ones.')
        print('')
        print('IF THIS IS THE SAME WORK, continue under the claim you already hold')
        print('-- it does not need re-claiming. If the wording has moved on, release')
        print('and re-claim so the record says one thing:')
        print('  python tools/sairn_claim.py release %s' % refuse[0][0].get('subject'))
        print('')
        print('IF IT IS GENUINELY DIFFERENT WORK, release the one above first. A')
        print('session holding one claim at a time is what makes `list` readable.')
        return 3
    if expired:
        # Never blocks -- see my_active_overlaps(). An expired claim is one this
        # tool has already decided is not held; saying nothing about it is how a
        # session takes a second claim on work it never closed the first one on.
        print('')
        print('Note: you have %d EXPIRED but UNRELEASED claim(s) on work this '
              'overlaps. NOT blocking -- this tool treats a claim older than '
              '%gh as dead -- but the record still shows it open, and another '
              'session reading it sees a phantom:' % (len(expired), STALE_HOURS))
        for c, reason, _k in expired:
            print('  %s -- %s  (%s, %s)'
                  % (c.get('subject'), c.get('task') or '(no task)', reason, age_str(c)))
        print('  If that work is done: python tools/sairn_claim.py release %s'
              % expired[0][0].get('subject'))
    if report:
        # Same app and nothing more. Real and common; said out loud and never
        # blocked, the same policy cmd_check applies to another session's weak
        # overlap.
        print('\nNote: you already hold %d active claim(s) in the same app. NOT '
              'blocking -- two claims on one app is ordinary -- but check you '
              'are not re-claiming work you are already on:' % len(report))
        for c, reason, _k in report:
            print('  %s -- %s  (%s, %s)'
                  % (c.get('subject'), c.get('task') or '(no task)', reason, age_str(c)))

    doc['claims'].append({
        'id': '%s-%d' % (session_name(), int(ts)),
        'session': session_name(),
        'subject': subj,
        'task': task,
        'claimed_at': iso(ts),
        'claimed_at_epoch': ts,
        'status': 'active',
        'released_at': None,
        # ── THE DECLARED FILE SET, STORED RATHER THAN RE-PARSED (2026-09-22) ──
        # The matcher reads it out of the task string at compare time, so this
        # field is not what it acts on -- it is what makes the declaration
        # AUDITABLE. Making the file set authoritative rewards under-declaring
        # it, which is rewording-past-the-matcher in a new costume; the answer
        # is that a later pass can compare these paths against what the session
        # actually changed in the commits it made while holding the claim.
        # `null` means the task declared none, which is the state that keeps a
        # claim on the lexical path and is worth being able to count.
        'files': sorted(declared_files(task) or []) or None,
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


# ── HAS THE DUPLICATE-CLAIM DEFECT RECURRED, OR IS THE EVIDENCE HISTORICAL? ──
# Released claims are KEPT, deliberately -- "who ran this and when" is the
# question the next session asks. The cost of that decision is that every
# duplicate ever recorded is still sitting in the file, so a reader opening
# .claude/claims/ finds the 2026-09-13 quadruple and the 2026-09-14 triple and
# reasonably concludes the bug is live.
#
# IT IS NOT, AND THE DATES DECIDE IT RATHER THAN ANYBODY'S MEMORY. The two
# guards landed at the timestamps below, and EVERY exact duplicate in the record
# predates the guard that covers it -- the fourth triple by 43 minutes, the cc
# pair by 22. Measured 2026-09-16: 631 claims, 6 duplicate groups, ZERO after
# the guards.
#
# So this command exists to stop a FIXED defect being re-reported as a live one,
# which has now happened twice. It bins by date rather than asserting a verdict,
# and a duplicate AFTER a guard is a real finding it will say loudly.
#
# THE TIMESTAMPS ARE THE COMMITS, not a recollection:
#   befb65e3  identical-task retry guard      2026-09-14T19:24:31Z
#   a50aaf60  retyped-task unpublished guard  2026-09-14T21:46:51Z
#
# ── AND THE THIRD, WHICH IS WHY THE FIRST TWO READ AS SUFFICIENT ──────────
# This command reported ZERO duplicates after the guards on 2026-09-16, and on
# its own definition that was TRUE. It bins EXACT (session, subject, task)
# groups, and its closing paragraph says so. The defect then recurred twice
# within a day, in two clones, in the form the definition does not count: the
# SAME WORK under a different subject or a retyped string, with the earlier
# claim already published so neither guard could fire.
#
# A metric that says FIXED while the thing it measures keeps happening is worse
# than no metric, because it is quoted. So the same-work count below uses the
# tool's own matcher (self_overlap) over claims that were CONCURRENTLY ACTIVE,
# and it is reported beside the exact count rather than folded into it -- they
# have different fixes and a summed number would hide which one moved.
GUARDS = (
    ('befb65e3', 'identical-task retry', 1789500271),
    ('a50aaf60', 'retyped-task unpublished', 1789508811),
    ('1f25f8bf', 'own-claim overlap (any wording, any subject)', 1789617600),
)
GUARDED_FROM = max(g[2] for g in GUARDS[:2])
# The own-claim guard lands later than the first two and covers a strictly
# wider shape, so the exact-duplicate bins keep using the older timestamp --
# re-dating them against this guard would silently reclassify six historical
# groups as "after the guard" and turn a clean audit into a false finding.
SELF_GUARDED_FROM = GUARDS[2][2]


def _claim_span(c):
    """(start, end) epoch for when this claim was HELD. An unreleased claim is
    held until it expires, which is what every other read of this file assumes."""
    a = c.get('claimed_at_epoch') or 0
    b = None
    r = c.get('released_at')
    if r:
        try:
            b = calendar.timegm(time.strptime(r, '%Y-%m-%dT%H:%M:%SZ'))
        except (ValueError, TypeError):
            b = None
    if b is None:
        b = a + STALE_HOURS * 3600
    return a, max(b, a + 1)


def same_work_pairs(claims):
    """[(session, a, b, reason)] -- one session's claims, held at the same time,
    that the matcher says are the same work. Concurrency is required: the same
    session claiming the same subject again next week is follow-on work, not a
    duplicate, and counting it would make this number grow for ever."""
    by = {}
    for c in claims:
        by.setdefault(c.get('session'), []).append(c)
    out = []
    for sess, cl in by.items():
        cl = sorted(cl, key=lambda x: x.get('claimed_at_epoch') or 0)
        for i in range(len(cl)):
            for j in range(i + 1, len(cl)):
                s1, e1 = _claim_span(cl[i])
                s2, e2 = _claim_span(cl[j])
                if not (s1 < e2 and s2 < e1):
                    continue
                reason, kind = self_overlap(cl[i].get('task'), cl[j].get('task'))
                if kind == 'refuse':
                    out.append((sess, cl[i], cl[j], reason))
    return out

# A session holding this many ACTIVE claims at once is not a duplicate defect --
# it is claims that were never released. Both make `list` noisy and both make
# another session read a phantom block, but they need OPPOSITE fixes, so they
# are counted apart rather than summed into one number.
MANY_ACTIVE = 4


def cmd_audit(args):
    claims = load_all(from_origin=False)
    if not claims:
        print('COULD NOT READ ANY CLAIM FILE -- nothing was audited. NOT a pass.')
        return 2

    groups = {}
    for c in claims:
        k = (c.get('session'), c.get('subject'), c.get('task') or '')
        groups.setdefault(k, []).append(c)
    dup = {k: v for k, v in groups.items() if len(v) > 1}

    before, after = [], []
    for k, v in dup.items():
        v = sorted(v, key=lambda c: c.get('claimed_at_epoch') or 0)
        (after if (v[-1].get('claimed_at_epoch') or 0) > GUARDED_FROM
         else before).append((k, v))

    active_by = {}
    for c in claims:
        if c.get('status') == 'active':
            active_by.setdefault(c.get('session'), []).append(c)
    hoarders = {s: v for s, v in active_by.items() if len(v) >= MANY_ACTIVE}

    print('CLAIM RECORD AUDIT -- %d claim(s) across %d session file(s)'
          % (len(claims), len({c.get('session') for c in claims})))
    print('  guards landed: ' + ', '.join('%s %s' % (g[0], g[1]) for g in GUARDS))
    print('')
    print('  EXACT DUPLICATES (same session, subject and task): %d group(s)'
          % len(dup))
    print('    BEFORE the guard that covers them  %d   <- historical, not a bug now'
          % len(before))
    print('    AFTER                              %d%s'
          % (len(after), '   <- A REAL FINDING' if after else ''))
    print('')
    for k, v in sorted(before, key=lambda x: x[1][0].get('claimed_at_epoch') or 0):
        print('    x%d  %-7s %s  %s'
              % (len(v), k[0], v[0].get('claimed_at'), (k[2] or '(empty task)')[:46]))
    for k, v in sorted(after, key=lambda x: x[1][0].get('claimed_at_epoch') or 0):
        print('    AFTER THE GUARD  x%d  %-7s %s  %s'
              % (len(v), k[0], v[0].get('claimed_at'), (k[2] or '(empty)')[:40]))
    print('')
    print('  THE OTHER SHAPE, COUNTED APART BECAUSE IT NEEDS THE OPPOSITE FIX:')
    print('  claims never RELEASED. Not a duplicate -- each is different work --')
    print('  but it makes `list` noisy and another session reads a phantom block.')
    if hoarders:
        for s, v in sorted(hoarders.items(), key=lambda x: -len(x[1])):
            oldest = sorted(v, key=lambda c: c.get('claimed_at_epoch') or 0)[0]
            print('    %-8s %2d active, oldest %s' % (s, len(v), oldest.get('claimed_at')))
    else:
        print('    no session is holding %d or more.' % MANY_ACTIVE)
    print('')
    # ── THE SHAPE THE EXACT COUNT ABOVE CANNOT SEE ────────────────────────
    # This paragraph used to say the opposite: that deciding two different task
    # strings are the same work "would move the failure rather than remove it.
    # Exact means exact." That was a defensible position and it was wrong in a
    # way the number could not show -- the defect recurred twice in two clones
    # while this command reported zero, because both recurrences were the same
    # work under different wording. The matcher is the tool's own, the same one
    # every cross-session block already rests on, and it is measured: 24 of 411
    # concurrent same-session pairs, every one a real duplicate on reading.
    same = same_work_pairs(claims)
    sbefore = [p for p in same
               if (p[2].get('claimed_at_epoch') or 0) <= SELF_GUARDED_FROM]
    safter = [p for p in same
              if (p[2].get('claimed_at_epoch') or 0) > SELF_GUARDED_FROM]
    print('  SAME WORK, DIFFERENT WORDING (one session, both held at once): '
          '%d pair(s)' % len(same))
    print('    BEFORE the own-claim guard          %d   <- historical' % len(sbefore))
    print('    AFTER                               %d%s'
          % (len(safter), '   <- A REAL FINDING' if safter else ''))
    for sess, a, b, reason in sorted(sbefore,
                                     key=lambda p: p[2].get('claimed_at_epoch') or 0)[-6:]:
        print('    %-7s %s  %s' % (sess, b.get('claimed_at'), reason))
        print('            A: %s' % (a.get('task') or '(empty)')[:64])
        print('            B: %s' % (b.get('task') or '(empty)')[:64])
    for sess, a, b, reason in safter:
        print('    AFTER THE GUARD  %-7s %s  %s' % (sess, b.get('claimed_at'), reason))
        print('            A: %s' % (a.get('task') or '(empty)')[:64])
        print('            B: %s' % (b.get('task') or '(empty)')[:64])
    print('')
    print('  WHAT THIS STILL DOES NOT DO: catch two claims for one piece of work')
    print('  that share no identifier, no phrase and no app -- `triage plan')
    print('  staleness checker` against `triage staleness tool`. block_reason()')
    print('  names that residual in its own body and records why the obvious fix')
    print('  (a rare-token rule) was measured at 74 extra blocks and rejected.')
    return 1 if (after or safter or hoarders) else 0


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

    c = sub.add_parser('audit', help='duplicates and unreleased claims, binned '
                                     'by whether they predate the guard')

    args = p.parse_args()
    if args.cmd == 'check':
        return cmd_check(args)
    if args.cmd == 'claim':
        return cmd_claim(args)
    if args.cmd == 'release':
        return cmd_release(args)
    if args.cmd == 'audit':
        return cmd_audit(args)
    return cmd_list(args)


if __name__ == '__main__':
    sys.exit(main())
