#!/usr/bin/env python
"""claim_collision_scan.py (hover2's own build, item 4 of the 2026-09-23
standing queue) -- did two DIFFERENT sessions ever hold an overlapping
claim on overlapping work, the real recurring bug class tools/sairn_claim.py
itself was built to prevent (its own docstring: the 2026-08-30 SAIRNfreedom
incident, two sessions running all three pre-build gates the same night,
"roughly four hours, duplicated").

WHY THIS EXISTS SEPARATELY FROM sairn_claim.py's OWN "check". sairn_claim.py
answers "is there an active claim on THIS subject RIGHT NOW" -- a live,
forward-looking gate. It has no retrospective view: nothing asks the claim
HISTORY whether the gate it exists to prevent has actually recurred anyway,
under a different subject string, or with the FILES actually colliding
while the subject text did not match. This asks that question, across the
whole recorded history in every session's claims file, not just the
present moment.

WHAT COUNTS AS A COLLISION, AND THE TWO SIGNALS KEPT SEPARATE (discipline
2 -- never collapse two different questions into one number):

  FILE_OVERLAP  -- two claims, different sessions, TIME-OVERLAPPING
                   windows, and at least one file path in common between
                   their declared FILES: annotations. This is the strong
                   signal: the same resource, touched by two sessions at
                   once.
  SUBJECT_MATCH -- two claims, different sessions, TIME-OVERLAPPING
                   windows, IDENTICAL subject string, but no FILES:
                   annotation parsed from either (or none in common). This
                   is the ORIGINAL 2026-08-30 incident's own shape --
                   "sairnfreedom" / "phase 1 build" against
                   "sairnfreedom" / gate research, no file ever touched in
                   common because the duplicated work was RESEARCH, not a
                   commit.

WHERE "FILES:" COMES FROM. There is no structured files field in a claim
record -- checked directly against every claims/*.json in this repo. FILES:
is a free-text convention some sessions write inside their own `task`
string ("... FILES: docs/tier-a-reviews.json"). This scan parses that
convention with a regex; a claim that does not use it contributes no files
and can therefore only ever be caught by SUBJECT_MATCH, never FILE_OVERLAP
-- stated here so a clean FILE_OVERLAP report is never read as "these are
the only two kinds of collision that occurred," only as "these are the
ones a FILES: line let this tool see."

WHAT AN "ACTIVE, NEVER RELEASED" CLAIM'S WINDOW END IS. A claim with no
released_at is either still genuinely in progress or was abandoned by a
crashed/compacted session -- tools/sairn_claim.py's own STALE_HOURS
(re-derived by importing the real constant from that module, not
retyped) is the point past which OTHER sessions are told to stop treating
it as blocking. This scan uses the SAME rule for its own window end:
min(claimed_at + STALE_HOURS, now) when released_at is absent, and reports
the claim as UNRELEASED alongside any collision found against it, since an
unreleased claim's true end time is fundamentally uncertain and any
collision against it is only as trustworthy as that assumption.

WHAT THIS CANNOT SEE, SAID PLAINLY: git records no session identity on any
commit in this repo -- confirmed directly in sabotage_claim_verify.py's own
LEVEL 2 note ("every commit here is Michael Dibert... regardless of
clone"). This scan CANNOT confirm a flagged pair actually produced
conflicting commits; it reports claim-record overlap only, the same
narrower, honest scope tools/sairn_claim.py itself keeps ("NOT A LOCK...
travels by git... cannot tell you a claim is being WORKED").

    python claim_collision_scan.py
    python claim_collision_scan.py --json
    python claim_collision_scan.py --fixtures
"""
import calendar
import glob
import importlib.util
import io
import json
import os
import re
import sys
import time

REPO = r"C:\Users\marsh\Documents\SAIRN-hover2"
CLAIMS_GLOB = os.path.join(REPO, '.claude', 'claims', '*.json')
FILES_RE = re.compile(r'FILES:\s*(.+)')

# INVESTIGATED, NOT LEFT AS A CAVEAT. Keyed by frozenset({claim_id_a,
# claim_id_b}) so a resolution is pinned to the two EXACT claim records, not
# to the subject string (a future claim on the same subject is a fresh
# question). Each entry was resolved by reading the real commit diffs inside
# the overlap window, not by assuming the subject-queue explanation --
# see hover-audit-log.jsonl for the full evidence trail cited in each.
RESOLVED_COLLISIONS = {
    frozenset({'cc-1789747246', 'cody-1789729790'}): {
        'verdict': 'LEGITIMATE SHARED QUEUE, not a collision',
        'evidence': "commit 1383d90f (2026-09-18T17:30:03-04:00) says so in "
                     "its own message -- 'cody and I reviewed cc's two "
                     "oldest within minutes of each other -- both verdicts "
                     "kept, and the duplication is the finding'. The "
                     "sessions themselves detected and reconciled the "
                     "overlap in real time and kept both reviews as "
                     "corroborating evidence, not wasted work.",
    },
    frozenset({'cody-1790032600', 'fourth-1789619644'}): {
        'verdict': 'LEGITIMATE SHARED QUEUE, not a collision',
        'evidence': "cody's ENTIRE claim window (2026-09-21T23:16:40Z-"
                     "2026-09-22T07:59:06Z) contains exactly ONE substantive "
                     "sairnlaw-related commit -- 61f3cefe, cody's own "
                     "tests/law_timeentry_scope_review_probe.js review, "
                     "matching the claim's task text exactly. No commit "
                     "from fourth's broad 5-day 'jurisdiction seeding' claim "
                     "landed inside that window at all -- fourth's next "
                     "sairnlaw-touching commit (47a5534c, provisioning) "
                     "lands 14 minutes AFTER cody released. Disjoint in "
                     "both file and time in practice, despite the subject "
                     "string and claim windows nominally overlapping.",
    },
    # THE FOLLOWING 8 SURFACED 2026-09-23 by the DST epoch-bug fix above --
    # investigated in the same dedicated pass, same standard (real commit
    # diffs, not assumed).
    frozenset({'cc-1788400388', 'hank-1788400390'}): {
        'verdict': 'REAL COLLISION -- confirmed, not benign, but not wasted '
                    'work either',
        'evidence': "cc claimed stonedesk 'multi location yards GAP7' at "
                     "2026-09-03T01:53:08Z; hank claimed stonedesk 'multi "
                     "location yard scoping GAP7' 2 SECONDS LATER. Confirmed "
                     "via git log in that exact window: hank built the "
                     "feature (5ddde111, 'feat(stonedesk): [GAP 7] yards') "
                     "touching api/sd-data.js, stonedesk.html, "
                     "tests/stonedesk_locations.js, sql/"
                     "stonedesk_locations_schema.sql, api/_resources/"
                     "stonedesk.js; cc then landed a fix ON TOP of it "
                     "(17cdad85, 'the yard registry had no session gate at "
                     "all') touching the SAME three JS/HTML files. Genuinely "
                     "the same feature, claimed within 2 seconds by two "
                     "sessions, both wrote to the identical file set -- but "
                     "SEQUENTIAL (hank built, cc gated afterward), not "
                     "duplicated. The claim system did not prevent the "
                     "double-claim; the two sessions' actual edits happened "
                     "not to conflict.",
    },
    frozenset({'cc-1788354015', 'cody-1788355428'}): {
        'verdict': 'LEGITIMATE, not a collision',
        'evidence': "subject 'stonedesk' is the whole app, not a task -- cc "
                     "(executive panel role gate / token budget) and cody "
                     "(sd-sub-data.js compliance clock) are unrelated "
                     "features. No commit found touching stonedesk.html or "
                     "api/sd-data.js in the overlap window at all.",
    },
    frozenset({'cc-1788398614', 'hank-1788396861'}): {
        'verdict': 'LEGITIMATE, not a collision',
        'evidence': "same 'stonedesk' coarse-subject shape -- cc (0039 "
                     "composite inference context) and hank (nesting "
                     "machine output dxf GAP2) are unrelated features, no "
                     "declared FILES, no evidence of a shared touched file.",
    },
    frozenset({'cc-1790003400', 'cody-1790019422'}): {
        'verdict': 'LEGITIMATE, disclosed dead-claim override',
        'evidence': "cody's OWN claim note explains it in full: cc's claim "
                     "was 4.4h old (past the 4h expiry) AND cc's CLAUDE_PID "
                     "was confirmed gone via a live Get-Process check, not "
                     "read off the registry. Cody grepped and confirmed no "
                     "legGate existed on main -- cc died before landing "
                     "anything, so nothing was duplicated. Cody's version is "
                     "an independent implementation of the same gate, taken "
                     "over a confirmed-dead claim, exactly the override "
                     "tools/sairn_claim.py's own docs describe as the "
                     "intended fallback.",
    },
    frozenset({'cc-1790186292', 'hank-1790168912'}): {
        'verdict': 'LEGITIMATE, sequential review',
        'evidence': "cc's task literally says 'review hank 13:44:34Z "
                     "NONE-bucket isolation arms, then fix postgrestMock "
                     "select= honouring' -- cc is explicitly reviewing and "
                     "extending hank's just-finished work, not duplicating "
                     "it. Commit 7cfc2c24 ('the mock honours select= now') "
                     "lands inside cc's window and matches its stated task "
                     "exactly; no commit in the window shows any conflicting "
                     "edit to the shared test file.",
    },
    frozenset({'cody-1789998850', 'fourth-1789997768'}): {
        'verdict': 'LEGITIMATE, self-diagnosed structural false-positive',
        'evidence': "cody's own claim note names this exactly: the ONLY "
                     "overlap is docs/tier-a-reviews.json, 'the file every "
                     "review on this platform writes' -- an append-only "
                     "register, not a resource being edited twice. Cody "
                     "read fourth's declared files (api/sd-data-cross-"
                     "tenant-dispatchers.test.js, tools/"
                     "cross_tenant_isolation_scope.py) against its own "
                     "(sairnlaw.html, api/_lib/law-timeentry.js) and found "
                     "them disjoint. Cody flagged this as the THIRD such "
                     "false collision that day and called for a convention "
                     "fix.",
    },
    frozenset({'cody-1789998850', 'fourth-1789999202'}): {
        'verdict': 'LEGITIMATE, same structural cause as the pair above, '
                    'AND the direct fix',
        'evidence': "fourth-1789999202's own task text is the fix: 'stamp a "
                     "reviewing OWNER at --open time so two sessions cannot "
                     "both discharge one obligation. Michael's direction "
                     "after FOUR duplicates today.' This claim built "
                     "tools/tier_a_review_gate.py's owner-stamping in "
                     "direct response to this exact false-collision shape, "
                     "the same session (cody) still holding an unrelated "
                     "review claim on the same append-only file.",
    },
    frozenset({'cody-1790115147', 'hank-1790115153'}): {
        'verdict': 'LEGITIMATE, disjoint concurrent retier batches',
        'evidence': "cody ('six executed-instrument and clinical rows') and "
                     "hank ('items 2-13... eleven apps') claimed within 6 "
                     "seconds of each other on docs/CRITICALITY-TIERS.md. "
                     "Both landed as separate, later commits (91d6c9f2, "
                     "fc5f3e66) retiering DIFFERENT named resource batches "
                     "-- different rows of the same shared register, merged "
                     "cleanly, no lost work.",
    },
    frozenset({'cc-1789974340', 'fourth-1789619644'}): {
        'verdict': 'LEGITIMATE SHARED QUEUE, not a collision',
        'evidence': "same structural shape as the cody/fourth sairnlaw pair "
                     "already resolved above: fourth's claim ('jurisdiction "
                     "seeding next gate') ran 2026-09-17 to 2026-09-22, five "
                     "days. cc's claim (invoiced-flag sync bug) is a "
                     "narrow, 15-minute, specific billing-logic fix "
                     "entirely disjoint from jurisdiction/schema work.",
    },
    frozenset({'cc-1789975400', 'fourth-1789619644'}): {
        'verdict': 'LEGITIMATE SHARED QUEUE, not a collision',
        'evidence': "same fourth 5-day umbrella claim as above; cc's claim "
                     "here (rate validation / LEDES header) is a second, "
                     "separate, narrow billing-logic fix, also disjoint "
                     "from jurisdiction seeding.",
    },
    frozenset({'cc-1789991991', 'fourth-1789619644'}): {
        'verdict': 'LEGITIMATE SHARED QUEUE, not a collision',
        'evidence': "same fourth 5-day umbrella claim a third time; this cc "
                     "claim explicitly DECLARES its files (sairnlaw.html, "
                     "api/_lib/law-timeentry.js, tests/"
                     "server_wins_hydration.js, tests/"
                     "sairnlaw_billable_rate.js) -- none overlap "
                     "jurisdiction/schema files. THREE separate cc claims "
                     "plus cody's all fell inside fourth's single "
                     "five-day claim without a real conflict; the pattern "
                     "itself says the umbrella claim was too broad/too "
                     "long-lived to be a useful collision signal, a process "
                     "observation worth naming even though no instance was "
                     "a real collision.",
    },
}


def _load_stale_hours():
    """Import the real constant from tools/sairn_claim.py rather than
    retyping '4' here -- a duplicated literal is exactly what drifts
    silently when the source changes and nothing re-reads it."""
    path = os.path.join(REPO, 'tools', 'sairn_claim.py')
    try:
        spec = importlib.util.spec_from_file_location('sairn_claim', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return float(mod.STALE_HOURS)
    except Exception:
        return None  # caller must treat this as COULD_NOT_DERIVE, not silently default to 4


def parse_files(text):
    """Extract path-like tokens after a 'FILES:' marker. Stops at the next
    ' -- ' free-text separator this codebase's own claim tasks use, e.g.
    '...FILES: a.js b.js -- LEG_RESOURCES session gate...'."""
    if not text:
        return []
    m = FILES_RE.search(text)
    if not m:
        return []
    rest = m.group(1)
    rest = re.split(r'\s+--\s+', rest, maxsplit=1)[0]
    toks = [t.strip() for t in rest.split() if t.strip()]
    return [t for t in toks if '/' in t or '.' in t]


def _epoch(iso_or_epoch, fallback_epoch=None):
    """REAL BUG FOUND AND FIXED 2026-09-23, by independent cross-validation
    against H1's own claim_collision_scan.py on the SAME real claims data
    (hover2's own delegated task 1: validate a real H1 tool against a real
    holdout, not a synthetic fixture). H1's tool found 8 genuine
    cc/hank/cody/fourth collisions on stonedesk and sairnlaw; this tool
    found only 2. Traced to a REAL claim pair (cc-1788400388 /
    hank-1788400390, both subject='stonedesk', both real Tier A stonedesk
    GAP7 work, confirmed genuinely overlapping by reading the actual commits
    in that window) that this tool silently missed.

    THE MECHANISM: time.mktime(t) - time.timezone interprets a UTC struct
    as LOCAL time and subtracts the STANDARD (non-DST) offset. On a machine
    observing DST (time.daylight=1) for a date that falls inside DST, that
    is wrong by exactly one hour -- time.mktime() applies the DST-aware
    local rule while time.timezone is the fixed standard-time offset.
    claimed_at is never affected in practice, because every real claim
    record already carries a precise claimed_at_epoch that this function's
    fallback-epoch path uses directly, bypassing the parse entirely.
    released_at is ALWAYS affected: no real claim record carries a
    released_at_epoch, so every released_at silently went through the buggy
    ISO-string path. On the GAP7 pair this shifted released_at down by
    ~3600s, producing an END EPOCH SMALLER THAN THE START EPOCH -- a
    negative-width interval that made every overlap check `hi <= lo` on
    that claim, silently, with no error and no disclosure. A DST-shaped bug
    that only ever touches one of two timestamp fields is exactly the kind
    of asymmetric defect that survives testing on data captured outside
    DST season and bites only in it.

    THE FIX: calendar.timegm(), the documented correct inverse of
    time.gmtime() -- treats the struct as UTC and does the conversion with
    no local timezone or DST involved at all, so claimed_at's
    epoch-fallback path and released_at's parsed path now agree by
    construction rather than by coincidence."""
    if fallback_epoch is not None:
        try:
            return float(fallback_epoch)
        except (TypeError, ValueError):
            pass
    if not iso_or_epoch:
        return None
    try:
        t = time.strptime(iso_or_epoch, '%Y-%m-%dT%H:%M:%SZ')
        return float(calendar.timegm(t))
    except Exception:
        return None


def load_claims(claims_glob=CLAIMS_GLOB, stale_hours=4.0, now=None):
    now = now if now is not None else time.time()
    out = []
    for path in sorted(glob.glob(claims_glob)):
        if not path.endswith('.json'):
            continue
        try:
            data = json.load(io.open(path, encoding='utf-8'))
        except Exception as e:
            out.append({'session': os.path.basename(path), 'load_error': repr(e)})
            continue
        session = data.get('session') or os.path.basename(path).replace('.json', '')
        for c in data.get('claims', []):
            start = _epoch(c.get('claimed_at'), c.get('claimed_at_epoch'))
            released_at = c.get('released_at')
            end = _epoch(released_at, c.get('released_at_epoch'))
            unreleased = end is None and c.get('status') == 'active'
            if end is None:
                end = (start + stale_hours * 3600) if start is not None else None
                end = min(end, now) if end is not None else None
            subject = c.get('subject', '')
            task = c.get('task', '')
            files = set(parse_files(task)) | set(parse_files(subject))
            out.append({
                'session': session, 'id': c.get('id'), 'subject': subject,
                'task': task, 'start': start, 'end': end,
                'unreleased': unreleased, 'files': files,
            })
    return out


def find_collisions(claims):
    results = []
    n = len(claims)
    for i in range(n):
        a = claims[i]
        if a.get('start') is None or a.get('end') is None or 'load_error' in a:
            continue
        for j in range(i + 1, n):
            b = claims[j]
            if b.get('start') is None or b.get('end') is None or 'load_error' in b:
                continue
            if a['session'] == b['session']:
                continue
            lo = max(a['start'], b['start'])
            hi = min(a['end'], b['end'])
            if hi <= lo:
                continue
            common_files = a['files'] & b['files']
            if common_files:
                kind = 'FILE_OVERLAP'
            elif a['subject'] and a['subject'] == b['subject']:
                kind = 'SUBJECT_MATCH'
            else:
                continue
            resolution = RESOLVED_COLLISIONS.get(frozenset({a['id'], b['id']}))
            results.append({
                'kind': kind,
                'overlap_seconds': hi - lo,
                'a': {'session': a['session'], 'id': a['id'], 'subject': a['subject'],
                      'unreleased': a['unreleased']},
                'b': {'session': b['session'], 'id': b['id'], 'subject': b['subject'],
                      'unreleased': b['unreleased']},
                'common_files': sorted(common_files),
                'resolution': resolution,
            })
    return results


# ---------------------------------------------------------------- fixtures
def run_fixtures():
    bad = []

    def ck(name, cond):
        print(('  ok   ' if cond else '  FAIL ') + name)
        if not cond:
            bad.append(name)

    base = 1_000_000_000.0
    fx = [
        {'session': 'x', 'id': 'x1', 'subject': 'sairnfreedom', 'task': 'FILES: a.js b.js -- gate',
         'start': base, 'end': base + 3600, 'unreleased': False, 'files': {'a.js', 'b.js'}},
        {'session': 'y', 'id': 'y1', 'subject': 'sairnfreedom', 'task': 'FILES: b.js c.js -- gate2',
         'start': base + 1800, 'end': base + 5400, 'unreleased': False, 'files': {'b.js', 'c.js'}},
    ]
    hits = find_collisions(fx)
    ck('overlapping time + a common file (b.js) reports FILE_OVERLAP',
       len(hits) == 1 and hits[0]['kind'] == 'FILE_OVERLAP' and hits[0]['common_files'] == ['b.js'])

    fx2 = [
        {'session': 'x', 'id': 'x1', 'subject': 'sairnfreedom', 'task': '',
         'start': base, 'end': base + 3600, 'unreleased': False, 'files': set()},
        {'session': 'y', 'id': 'y1', 'subject': 'sairnfreedom', 'task': '',
         'start': base + 1800, 'end': base + 5400, 'unreleased': False, 'files': set()},
    ]
    hits2 = find_collisions(fx2)
    ck('same subject, overlapping time, NO files parsed on either side -- '
       'the original 2026-08-30 incident shape -- reports SUBJECT_MATCH',
       len(hits2) == 1 and hits2[0]['kind'] == 'SUBJECT_MATCH')

    fx3 = [
        {'session': 'x', 'id': 'x1', 'subject': 'a', 'task': 'FILES: a.js',
         'start': base, 'end': base + 100, 'unreleased': False, 'files': {'a.js'}},
        {'session': 'y', 'id': 'y1', 'subject': 'a', 'task': 'FILES: b.js',
         'start': base + 500, 'end': base + 700, 'unreleased': False, 'files': {'b.js'}},
    ]
    ck('same subject and files, but NON-overlapping time windows -- no collision',
       len(find_collisions(fx3)) == 0)

    fx4 = [
        {'session': 'x', 'id': 'x1', 'subject': 'a', 'task': 'FILES: a.js',
         'start': base, 'end': base + 3600, 'unreleased': False, 'files': {'a.js'}},
        {'session': 'x', 'id': 'x2', 'subject': 'a', 'task': 'FILES: a.js',
         'start': base + 100, 'end': base + 200, 'unreleased': False, 'files': {'a.js'}},
    ]
    ck('the SAME session cannot collide with itself, even with identical '
       'files and overlapping time',
       len(find_collisions(fx4)) == 0)

    ck('parse_files() stops at the " -- " free-text separator this '
       'codebase\'s own claim tasks use, not swallowing prose as a path',
       parse_files('FILES: a.js b.js -- some free prose about c.js') == ['a.js', 'b.js'])

    ck('parse_files() on a claim with no FILES: marker returns empty, not '
       'a false split on unrelated text',
       parse_files('two-axis criticality tier format implementation') == [])

    fx5 = [
        {'session': 'cc', 'id': 'cc-1789747246', 'subject': 'tier-a-reviews', 'task': '',
         'start': base, 'end': base + 3600, 'unreleased': False, 'files': set()},
        {'session': 'cody', 'id': 'cody-1789729790', 'subject': 'tier-a-reviews', 'task': '',
         'start': base + 1800, 'end': base + 5400, 'unreleased': False, 'files': set()},
    ]
    hits5 = find_collisions(fx5)
    ck('a real, investigated pair (the tier-a-reviews cc/cody overlap) '
       'carries its resolution inline in the output, not left as a bare '
       'unresolved caveat', len(hits5) == 1 and hits5[0]['resolution'] is not None
       and 'LEGITIMATE SHARED QUEUE' in hits5[0]['resolution']['verdict'])

    # REGRESSION LOCK for the DST bug found 2026-09-23 by cross-validation
    # against H1's independently-built claim_collision_scan.py on the same
    # real data. The real shape: claimed_at_epoch is always present
    # (bypasses the parser), released_at_epoch is NEVER present in real
    # records (always goes through the parser) -- so only released_at was
    # ever exposed to the old time.mktime()-minus-time.timezone bug.
    ck('_epoch() on two bare ISO strings 1814 real seconds apart, during '
       'DST season, computes exactly 1814 seconds apart -- the old '
       'time.mktime()-minus-time.timezone formula was off by exactly one '
       'DST hour here (3600s), which is what hid the real GAP7 collision',
       _epoch('2026-09-03T02:23:24Z') - _epoch('2026-09-03T01:53:10Z') == 1814)

    raw_start = _epoch('2026-09-03T01:53:10Z', 1788400390.1685426)
    raw_end = _epoch('2026-09-03T02:23:24Z', None)
    ck('THE REAL GAP7 PAIR: with the fix, released_at (02:23:24) parses to '
       'AFTER claimed_at (01:53:10, from its stored epoch) -- the old bug '
       'made end < start here and silently hid a genuine collision',
       raw_end > raw_start)

    # KNOWN-BAD CONTROL, conflict-marker sweep, 2026-09-28: a claims file
    # left with unresolved git conflict markers must be VISIBLY reported
    # via load_error, never silently skipped or treated as an empty/clean
    # claims file. Driven against a real temp file, not asserted -- JSON's
    # own strict grammar already makes this the correct behavior (a
    # literal '<<<<<<<' is not valid JSON syntax and json.load() raises
    # immediately), unlike the regex-based structural parsers elsewhere in
    # this session's tooling that silently accepted one side of a
    # conflict; this control exists to LOCK that this tool stays on the
    # safe side of that distinction, not to fix a defect that was found.
    import tempfile as _tf
    _d = _tf.mkdtemp()
    with io.open(os.path.join(_d, 'conflicted.json'), 'w', encoding='utf-8') as _f:
        _f.write('<<<<<<< HEAD\n{"session":"x","claims":[]}\n=======\n'
                '{"session":"y"}\n>>>>>>> branch\n')
    conflicted_result = load_claims(claims_glob=os.path.join(_d, '*.json'))
    ck('KNOWN-BAD CONTROL: a conflicted claims file is reported via '
       'load_error, never silently treated as empty/clean',
       len(conflicted_result) == 1 and 'load_error' in conflicted_result[0])

    if bad:
        print('%d of 10 fixture(s) failed -- refusing to judge real claims' % len(bad))
        return 2
    print('OK -- 10/10 fixtures passed')
    return 0


def main(argv):
    if '--fixtures' in argv:
        return run_fixtures()

    fx_buf = io.StringIO()
    _stdout = sys.stdout
    sys.stdout = fx_buf
    try:
        fx_rc = run_fixtures()
    finally:
        sys.stdout = _stdout
    if fx_rc != 0:
        print(fx_buf.getvalue())
        print('FIXTURES FAILED -- nothing real was judged')
        return 2

    stale_hours = _load_stale_hours()
    if stale_hours is None:
        print('COULD NOT DERIVE STALE_HOURS from tools/sairn_claim.py -- '
              'refusing to guess a window end for unreleased claims')
        return 2

    claims = load_claims(stale_hours=stale_hours)
    load_errors = [c for c in claims if 'load_error' in c]
    claims = [c for c in claims if 'load_error' not in c]
    collisions = find_collisions(claims)

    as_json = '--json' in argv
    if as_json:
        print(json.dumps({'collisions': collisions, 'load_errors': load_errors,
                           'stale_hours': stale_hours, 'n_claims': len(claims)}, indent=2))
        unresolved = [h for h in collisions if not h['resolution']]
        return 1 if unresolved else 0

    sessions = sorted(set(c['session'] for c in claims))
    print('CLAIM COLLISION SCAN -- %d claim(s) across %d session file(s) (%s), '
          'STALE_HOURS=%s (imported from tools/sairn_claim.py)' %
          (len(claims), len(sessions), ', '.join(sessions), stale_hours))
    for e in load_errors:
        print('  LOAD_ERROR %s: %s' % (e['session'], e['load_error']))
    if not collisions:
        print('  none found -- no two different sessions held time-overlapping '
              'claims with a common declared file or an identical subject')
    unresolved = 0
    for h in collisions:
        print('  %s  overlap=%ds' % (h['kind'], int(h['overlap_seconds'])))
        print('      %s/%s  "%s"%s' % (h['a']['session'], h['a']['id'], h['a']['subject'],
                                        ' [UNRELEASED]' if h['a']['unreleased'] else ''))
        print('      %s/%s  "%s"%s' % (h['b']['session'], h['b']['id'], h['b']['subject'],
                                        ' [UNRELEASED]' if h['b']['unreleased'] else ''))
        if h['common_files']:
            print('      common files: %s' % ', '.join(h['common_files']))
        if h['resolution']:
            print('      RESOLVED: %s' % h['resolution']['verdict'])
            print('        %s' % h['resolution']['evidence'])
        else:
            print('      UNRESOLVED -- not yet investigated against real commit diffs')
            unresolved += 1
    print()
    print('LIMITATION, STATED NOT HIDDEN: this scan reads claim RECORDS only. '
          'No commit in this repo carries session identity (confirmed in '
          'sabotage_claim_verify.py\'s own LEVEL 2 note), so a flagged pair '
          'is claim-window overlap, not a confirmed conflicting commit -- '
          'RESOLVED entries above were settled by hand-reading the real '
          'commit diffs inside the overlap window, not by this scan alone.')
    return 1 if (unresolved or load_errors) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
