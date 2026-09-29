#!/usr/bin/env python
"""claim_collision_scan.py -- retrospective detection of the 2026-09-15 session-
lock collision SHAPE, run against .claims history. Built 2026-09-16.

WHY THIS SCANS CLAIMS, NOT THE SESSION LOCK ITSELF, STATED FIRST, NOT BURIED.
session_lock_check.py's own lock files (~/SAIRN-SESSION-LOCKS/*.lock) are
mutated IN PLACE, live outside the git repo entirely, and are NEVER versioned
-- there is no git history to walk for them, and no other record of what any
lock file said at any past moment. A literal reading of "scan git history for
a period a clone's lock showed a different session" is not buildable: that
history does not exist and never did. Naming this plainly rather than
building a tool that quietly checks something smaller and calling it the
same thing.

What IS real, tracked, and has full history: .claude/claims/<session>.json.
Each file is append-only in practice -- confirmed 2026-09-16, spans
2026-08-30 through the current session for all five files -- so the CURRENT
content of each file already carries its own complete history; no `git log
-p` walk is needed to see it. The closest real, honestly-scoped analog to
"a clone occupied by two sessions" that this data can actually answer is:
did two DIFFERENT sessions hold ACTIVE, OVERLAPPING claims on the SAME real
subject at the same time -- the claim-system's own version of the identical
collision shape (two sessions duplicating effort with no way for either to
see the other), using the SAME conservative token-overlap heuristic
tools/sairn_claim.py's own overlaps() already uses for the identical
purpose, re-implemented here rather than imported so this stays a read-only
external tool with no platform-module coupling.

WHAT THIS CANNOT SEE, DISCLOSED PLAINLY: two sessions in the SAME clone
working on the SAME subject without either ever filing a claim at all would
be invisible to this -- it can only see collisions where at least the claim
system's own bookkeeping was followed. And it detects claim-level overlap,
not literal simultaneous tool use in one clone; a genuine two-Claude-
Code-processes-in-one-directory collision (the actual 2026-09-15 incident)
would only show up here if it also produced two overlapping claims on
related subjects, which is not guaranteed.

Run: python claim_collision_scan.py [--claims-dir PATH]
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

STOPWORDS = {
    'the', 'and', 'for', 'with', 'from', 'that', 'this', 'into', 'onto',
    'a', 'an', 'of', 'to', 'in', 'on', 'at', 'is', 'be', 'it', 'as', 'by',
}


def tokens(*parts):
    """Same conservative shape as sairn_claim.py's own tokens()/overlaps():
    lowercase word tokens, stopwords dropped, short tokens (<3 chars) dropped
    to avoid noise like 'a', 'gm', 'r1' matching by accident."""
    out = set()
    for p in parts:
        if not p:
            continue
        for w in re.findall(r'[a-z0-9]+', str(p).lower()):
            if len(w) >= 3 and w not in STOPWORDS:
                out.add(w)
    return out


def parse_ts(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
    except ValueError:
        return None


def load_intervals(claims_dir):
    """[(session, subject, task, start, end)] across every session file.
    end=None means still active (never released) -- treated as open-ended,
    extending to "now" for overlap purposes, which is the conservative
    (more-likely-to-flag) direction."""
    out = []
    for fname in sorted(os.listdir(claims_dir)):
        if not fname.endswith('.json') or fname == 'README.md':
            continue
        path = os.path.join(claims_dir, fname)
        try:
            with open(path, encoding='utf-8') as f:
                doc = json.load(f)
        except (OSError, ValueError) as e:
            print('SKIPPED %s -- could not read/parse: %s' % (fname, e), file=sys.stderr)
            continue
        session = doc.get('session') or fname[:-5]
        for c in doc.get('claims', []):
            start = parse_ts(c.get('claimed_at'))
            if start is None:
                continue
            end = parse_ts(c.get('released_at'))  # None if still active
            out.append((session, c.get('subject') or '', c.get('task') or '', start, end))
    return out


def overlaps_in_time(a_start, a_end, b_start, b_end, now):
    a_end = a_end or now
    b_end = b_end or now
    return a_start < b_end and b_start < a_end


MIN_SHARED_TOKENS_WHEN_SUBJECT_DIFFERS = 3
# A single shared word (measured: 'gate', 'audit') fires on unrelated pairs
# across dozens of subjects -- this platform's vocabulary is small and
# common words like 'gate'/'audit'/'fix' are not a real signal alone.
# Confirmed by spot-check on the first real run (2026-09-16): 1-token hits
# on 'gate' and 'audit' matched entirely unrelated subjects (stonedesk vs
# sairnlaw, roofing vs sairncash) -- the exact "manual spot-check before
# trusting a regex/keyword count" lesson this platform already learned
# three times (item 117), applied to this tool before its own first
# real number was trusted rather than after a false one shipped.


def find_collisions(intervals, now):
    """Two tiers, reported separately -- collapsing them into one number
    would hide which claim is doing the work, the same discipline this
    platform's own severity-scoring rules already require.

    STRONG: same real subject string, different sessions, overlapping time.
    This is the direct claim-system analog of two sessions in one clone --
    high confidence, worth a human read every time.

    WEAK: different subjects, but >= MIN_SHARED_TOKENS_WHEN_SUBJECT_DIFFERS
    real tokens shared in the combined subject+task text, overlapping time.
    Lower confidence -- flagged for a human to look at, not asserted as a
    real collision.
    """
    strong, weak = [], []
    n = len(intervals)
    for i in range(n):
        s1, subj1, task1, start1, end1 = intervals[i]
        subj1_norm = (subj1 or '').strip().lower()
        tok1 = tokens(subj1, task1)
        for j in range(i + 1, n):
            s2, subj2, task2, start2, end2 = intervals[j]
            if s2 == s1:
                continue
            if not overlaps_in_time(start1, end1, start2, end2, now):
                continue
            subj2_norm = (subj2 or '').strip().lower()
            entry = {
                'session_a': s1, 'subject_a': subj1, 'task_a': task1,
                'window_a': [start1.isoformat(), (end1.isoformat() if end1 else 'STILL ACTIVE')],
                'session_b': s2, 'subject_b': subj2, 'task_b': task2,
                'window_b': [start2.isoformat(), (end2.isoformat() if end2 else 'STILL ACTIVE')],
            }
            if subj1_norm and subj1_norm == subj2_norm:
                # Same subject alone is TOO COARSE -- confirmed on this
                # tool's own first real run: 'stonedesk' is an app-level
                # bucket multiple sessions legitimately work concurrently on
                # different features of. 2 of 3 same-subject hits on the
                # first run were unrelated features (no shared task token
                # at all); the third ('multi location yards GAP7' /
                # 'multi location yard scoping GAP7', shared tokens
                # {gap7, location, multi}) was the real one. GENUINE
                # requires the task text to ALSO overlap, not just the
                # subject bucket.
                task_overlap = tokens(task1) & tokens(task2)
                entry['task_shared_tokens'] = sorted(task_overlap)
                entry['GENUINE'] = bool(task_overlap)
                strong.append(entry)
                continue
            shared = tok1 & tokens(subj2, task2)
            if len(shared) >= MIN_SHARED_TOKENS_WHEN_SUBJECT_DIFFERS:
                entry['shared_tokens'] = sorted(shared)
                weak.append(entry)
    return strong, weak


def _fixture_control():
    """Blind control, same discipline as hover_self_health.py's own fixture
    controls: expected classifications are written as literals BEFORE the
    call, not recorded from what the function happened to return."""
    now = datetime(2026, 9, 3, 2, 0, tzinfo=timezone.utc)
    T = lambda h, m: datetime(2026, 9, 3, h, m, tzinfo=timezone.utc)
    cases = [
        ('overlapping time, same subject, same real task -> GENUINE strong',
         [('a', 'app', 'multi location yards gap7', T(1, 50), T(2, 10)),
          ('b', 'app', 'multi location yard scoping gap7', T(1, 53), T(2, 5))],
         1, 0, [True]),
        ('overlapping time, same subject, UNRELATED task -> strong but NOT genuine',
         [('a', 'app', 'executive panel role gate', T(1, 0), T(1, 30)),
          ('b', 'app', 'compliance clock utc default', T(1, 10), T(1, 40))],
         1, 0, [False]),
        ('same subject, NO time overlap -> not flagged at all',
         [('a', 'app', 'thing one', T(1, 0), T(1, 30)),
          ('b', 'app', 'thing one', T(2, 0), T(2, 30))],
         0, 0, []),
        ('different subject, 3+ shared task tokens, time overlap -> weak only',
         [('a', 'app-one', 'multi location yard gap seven scoping', T(1, 0), T(1, 30)),
          ('b', 'app-two', 'multi location yard gap seven audit', T(1, 10), T(1, 40))],
         0, 1, []),
        ('same session, same subject, overlapping -> never flagged (not cross-session)',
         [('a', 'app', 'x thing', T(1, 0), T(1, 30)), ('a', 'app', 'x thing', T(1, 10), T(1, 40))],
         0, 0, []),
        ('still-active claim (no released_at) overlapping a later one -> flagged',
         [('a', 'app', 'multi location yard gap7', T(1, 0), None),
          ('b', 'app', 'multi location yard gap7 scoping', T(1, 30), T(1, 45))],
         1, 0, [True]),
    ]
    failures = []
    for label, ivals, exp_strong, exp_weak, exp_genuine_flags in cases:
        strong, weak = find_collisions(ivals, now)
        if len(strong) != exp_strong or len(weak) != exp_weak:
            failures.append('%s: expected strong=%d weak=%d, got strong=%d weak=%d'
                            % (label, exp_strong, exp_weak, len(strong), len(weak)))
            continue
        got_flags = [h['GENUINE'] for h in strong]
        if got_flags != exp_genuine_flags:
            failures.append('%s: expected GENUINE flags %r, got %r'
                            % (label, exp_genuine_flags, got_flags))
    return {'fixtures_run': len(cases), 'fixtures_failed': failures, 'FAIL_control': len(failures) > 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--claims-dir',
                    default=r'C:\Users\marsh\Documents\SAIRN-hover\.claude\claims')
    args = ap.parse_args()

    control = _fixture_control()
    if control['FAIL_control']:
        print(json.dumps({'FAIL_control': True, 'fixtures_failed': control['fixtures_failed'],
                          'note': 'COULD NOT RUN -- classifier failed its own fixtures, '
                                  'every number below would be untrusted'}, indent=2))
        return 2

    intervals = load_intervals(args.claims_dir)
    now = datetime.now(timezone.utc)
    strong, weak = find_collisions(intervals, now)

    report = {
        'claims_dir': args.claims_dir,
        'classifier_control': control,
        'total_intervals_scanned': len(intervals),
        'sessions_seen': sorted({s for s, *_ in intervals}),
        'STRONG_same_subject_overlaps_found': len(strong),
        'strong_hits': strong,
        'weak_shared_token_overlaps_found': len(weak),
        'weak_hits_NOT_asserted_as_real_UNTIL_spot_checked': weak,
        'DISCLOSED_SCOPE_LIMIT': (
            'This detects claim-level token+time overlap across different session '
            'claim files, which is the closest real, historical analog to a session-'
            'lock collision that .claude/claims/*.json data can actually answer. It '
            'is not a scan of session_lock_check.py\'s own lock files, which have no '
            'git or filesystem history at all -- see this file\'s own module '
            'docstring for why that scan is not buildable as literally stated.'
        ),
    }
    print(json.dumps(report, indent=2))
    return 1 if strong else 0


if __name__ == '__main__':
    sys.exit(main())
