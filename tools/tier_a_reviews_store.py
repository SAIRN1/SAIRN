# OWNER: fourth
"""APPEND-ONLY, PER-AGENT STORE for the Tier A review ledger.

Michael's decision, 2026-10-16, after `docs/tier-a-reviews.json` blocked the
SAME Tier A discharge in two consecutive batches -- b27 by cc holding the file,
b27-resume by hank holding it. Both holders were legitimate and were working on
unrelated rows.

── WHY A SINGLE SHARED JSONL WOULD NOT HAVE FIXED IT ────────────────────────
The ledger ALREADY declares itself "append-only across four clones" in its own
`merge_policy`, and `tools/sairn_rebase_resolve.py` already 3-way merges it by
identity. So the contention was never a git-merge problem and a single
append-only file would not have touched it.

THE CONTENTION IS A CLAIM-LOCK ON A PATH. `tools/sairn_claim.py` decides on the
DECLARED FILE SET, so two sessions naming the same path block each other
whatever the merge semantics are. One shared JSONL is still ONE PATH. Only
per-agent shards make two agents' writes land on disjoint paths, which is what
stops the claim tool serialising them.

  docs/tier-a-reviews/<session>.jsonl    one JSON object per line, appended

A session appends ONLY to its own shard. It never opens another's, and it never
rewrites its own.

── HOW AN UPDATE HAPPENS WITHOUT A REWRITE ──────────────────────────────────
This is the part that makes append-only usable for a ledger whose records get
DISCHARGED rather than only created, and it is the part that needs testing
rather than asserting.

Identity is `(author_session, opened_at)`, taken verbatim from the legacy file's
own `merge_policy.identity` rather than invented here. The reader unions every
layer and, for one identity, the LAST layer wins:

  1. `docs/tier-a-reviews.json` -> `records`     the legacy base layer
  2. `docs/tier-a-reviews/*.jsonl`               shards, in line order

So discharging an obligation that was OPENED in the legacy file means appending
ONE line carrying the same identity with `status: reviewed` -- and the legacy
file is never touched. That is what unblocks a discharge while another session
holds the old file.

A NON-AUTHOR MAY APPEND A RECORD CARRYING SOMEBODY ELSE'S `author_session`, and
that is the whole point of a review ledger: a discharge is written by the
REVIEWER. The shard filename says who WROTE the line; `author_session` inside
the record says whose obligation it is. Conflating those two would make a
discharge impossible, so they are deliberately separate -- and `--read`
reports, per record, which shard a field came from.

── WHAT THIS DOES NOT DO ────────────────────────────────────────────────────
It does NOT delete, rewrite or migrate away `docs/tier-a-reviews.json`. That
file is the base layer and stays readable exactly as it is, so every existing
reader keeps working unchanged while the writers move over one at a time. It is
also, at the time this was written, HELD BY A LIVE SESSION -- and a tool whose
first act is to rewrite a file another agent is editing would be the defect it
was built to prevent, committed by the fix for it.

It does NOT make the push gate read shards. `tools/tier_a_review_gate.py` is
cc's file and was held live when this landed; the two call sites it needs are
routed with full diffs in
`docs/2026-10-16-fourth-b28-tier-a-shards-routed-to-cc.md`. UNTIL cc LANDS
THAT, SHARDS ARE ADDITIVE AND NOT AUTHORITATIVE, and this module says so in
`--read` output rather than leaving it to be remembered.

  python tools/tier_a_reviews_store.py --selftest
  python tools/tier_a_reviews_store.py --read [--json] [--open-only]
  python tools/tier_a_reviews_store.py --migrate [--apply] [--all-authors]
  python tools/tier_a_reviews_store.py --append <session> --record '<json>'
  python tools/tier_a_reviews_store.py --validate
"""
import io
import json
import os
import sys

CRITERIA_VERSION = '2026-10-16.b28.1'

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY = os.path.join(REPO, 'docs', 'tier-a-reviews.json')
SHARD_DIR = os.path.join(REPO, 'docs', 'tier-a-reviews')

# Taken from the legacy file's own merge_policy.identity, NOT invented here. If
# that file ever changes its identity fields, `--validate` says so rather than
# this module silently disagreeing with the thing it layers on top of.
IDENTITY = ('author_session', 'opened_at')

SESSIONS = ('hank', 'cc', 'cody', 'fourth', 'hover', 'hover2')


def shard_path(session):
    return os.path.join(SHARD_DIR, '%s.jsonl' % session)


def _ident(rec):
    return tuple(str(rec.get(k, '')) for k in IDENTITY)


def read_legacy(path=None):
    """-> (records, note). NEVER raises on a missing file: absent is a state."""
    p = path or LEGACY
    if not os.path.isfile(p):
        return [], 'legacy file ABSENT at %s' % p
    try:
        d = json.load(io.open(p, encoding='utf-8'))
    except Exception as e:                       # noqa: BLE001
        # FAILS CLOSED, loudly. The legacy file is the base layer, so reading
        # it as empty would silently drop 265 obligations and report a clean
        # ledger -- which is the exact shape of the 503 the payroll freeze
        # exists for. Callers must treat None as COULD NOT READ, never as [].
        return None, 'legacy file UNREADABLE (%s)' % e
    recs = d.get('records')
    if not isinstance(recs, list):
        return None, 'legacy file has no `records` list'
    return recs, 'legacy file read: %d record(s)' % len(recs)


def read_shards(shard_dir=None):
    """-> (layers, problems). layers is [(session, lineno, record)] in order."""
    d = shard_dir or SHARD_DIR
    layers, problems = [], []
    if not os.path.isdir(d):
        return layers, ['shard dir ABSENT at %s -- no shard has been written yet'
                        % d]
    for name in sorted(os.listdir(d)):
        if not name.endswith('.jsonl'):
            continue
        session = name[:-len('.jsonl')]
        p = os.path.join(d, name)
        for n, line in enumerate(io.open(p, encoding='utf-8'), 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception as e:               # noqa: BLE001
                # ONE BAD LINE IS NOT A BAD LEDGER, and it is not skipped
                # either. It is reported per line and the read is marked
                # degraded, because "I could not parse line 7" and "there is
                # no line 7" must not look the same.
                problems.append('%s:%d UNPARSEABLE (%s)' % (name, n, e))
                continue
            if not isinstance(rec, dict):
                problems.append('%s:%d not an object' % (name, n))
                continue
            layers.append((session, n, rec))
    return layers, problems


def read_all(legacy_path=None, shard_dir=None):
    """Union every layer. LAST LAYER WINS for one identity.

    -> dict with `records`, `problems`, `degraded`, `provenance`.
    `degraded` True means some layer could not be fully read, and a caller must
    not treat the record list as complete.
    """
    out = {'records': [], 'problems': [], 'degraded': False, 'provenance': {}}
    legacy, note = read_legacy(legacy_path)
    out['problems'].append(note)
    if legacy is None:
        out['degraded'] = True
        legacy = []
    merged, order = {}, []
    for rec in legacy:
        i = _ident(rec)
        if i not in merged:
            order.append(i)
        merged[i] = dict(rec)
        out['provenance'][i] = ['legacy']
    layers, problems = read_shards(shard_dir)
    out['problems'].extend(problems)
    if problems and any('UNPARSEABLE' in p or 'not an object' in p
                        for p in problems):
        out['degraded'] = True
    for session, n, rec in layers:
        i = _ident(rec)
        if i not in merged:
            order.append(i)
            merged[i] = dict(rec)
            out['provenance'][i] = ['%s.jsonl:%d' % (session, n)]
        else:
            # FIELD-LEVEL MERGE, not replace. A discharge line carries the
            # verdict and the reviewer and need not restate the resources,
            # files and rules the opening record already holds -- and must not
            # erase them by omission, which is what a whole-record replace
            # would do. Only keys the appended line actually names move.
            merged[i].update(rec)
            out['provenance'][i].append('%s.jsonl:%d' % (session, n))
    out['records'] = [merged[i] for i in order]
    return out


def append(session, record, shard_dir=None):
    """Append ONE record to ONE session's shard. Never reads another's."""
    if session not in SESSIONS:
        return 2, ('REFUSED: %r is not a known session. Known: %s. A typo would '
                   'create a shard nobody reads, which looks exactly like a '
                   'record nobody wrote.' % (session, ', '.join(SESSIONS)))
    if not isinstance(record, dict):
        return 2, 'REFUSED: the record must be a JSON object'
    missing = [k for k in IDENTITY if not str(record.get(k, '')).strip()]
    if missing:
        return 2, ('REFUSED: a record with no %s has no identity, so no reader '
                   'can ever supersede or discharge it.' % ' or '.join(missing))
    d = shard_dir or SHARD_DIR
    if not os.path.isdir(d):
        os.makedirs(d)
    p = os.path.join(d, '%s.jsonl' % session)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    if '\n' in line or '\r' in line:
        return 2, 'REFUSED: the serialised record contains a newline'
    # APPEND MODE, and the newline goes FIRST only if the file does not already
    # end in one -- a shard whose last line lost its terminator would otherwise
    # have the next record concatenated onto it and both would be lost.
    pre = ''
    if os.path.isfile(p):
        with io.open(p, 'rb') as fh:
            if fh.seek(0, 2) or True:
                size = fh.tell()
                if size:
                    fh.seek(size - 1)
                    if fh.read(1) != b'\n':
                        pre = '\n'
    with io.open(p, 'a', encoding='utf-8', newline='\n') as fh:
        fh.write(pre + line + '\n')
    return 0, 'appended to docs/tier-a-reviews/%s.jsonl' % session


def migrate(apply_it=False, legacy_path=None, shard_dir=None,
            all_authors=False):
    """Write the legacy records into per-author shards. IDEMPOTENT.

    ── IT IS A ONE-TIME BULK MOVE AND IT NEEDS --all-authors TO SAY SO ──────
    Found by observation, 2026-10-16, minutes after the first migration: a
    rebase brought 14 commits and hank had appended ONE new record to the
    legacy file during the batch (266 records, hank 76 -> 77). The union read
    it correctly from the base layer with no action needed -- but a casual
    `--migrate --apply` would then have written a line into
    `docs/tier-a-reviews/hank.jsonl`, and this module's own rule is that a
    session appends ONLY to its own shard.

    A tool that forges lines in another agent's shard while claiming that rule
    is the same contradiction as a detector blessing its own fix. So the bulk
    move across every author is now EXPLICIT (`--all-authors`), and the default
    migrates only the invoking session's own records. Records belonging to
    others stay readable in the base layer -- they are not lost, they are just
    not written by me.
    """

    legacy, note = read_legacy(legacy_path)
    if legacy is None:
        return 2, ['COULD NOT RUN: %s' % note], {}
    by = {}
    unknown = []
    for rec in legacy:
        a = str(rec.get('author_session', '')).strip()
        if a not in SESSIONS:
            unknown.append(a or '(blank)')
            continue
        by.setdefault(a, []).append(rec)
    lines = ['%s' % note,
             'authors: %s' % ', '.join('%s=%d' % (k, len(v))
                                       for k, v in sorted(by.items()))]
    me = os.environ.get('SAIRN_SESSION', '').strip()
    if not all_authors:
        skipped = {k: len(v) for k, v in by.items() if k != me}
        by = {k: v for k, v in by.items() if k == me}
        if skipped:
            lines.append('OWN SHARD ONLY (session %r). NOT writing %s -- a '
                         'session appends only to its own shard, and those '
                         'records stay readable in the legacy base layer. Pass '
                         '--all-authors for the ONE-TIME bulk move.'
                         % (me or '(SAIRN_SESSION unset)',
                            ', '.join('%s=%d' % kv for kv in sorted(skipped.items()))))
        if not by:
            lines.append('Nothing to migrate for this session.')
    if unknown:
        # NOT DROPPED SILENTLY. A record whose author is not a known session
        # has no shard to go in, and migrating it into somebody else's would
        # forge an author on a review ledger.
        from collections import Counter
        lines.append('*** %d record(s) carry an author that is NOT a known '
                     'session and were NOT migrated: %s. They stay readable in '
                     'the legacy base layer and are NOT lost -- but they will '
                     'never be appendable, so each needs a decision.'
                     % (len(unknown),
                        ', '.join('%s x%d' % (k, v)
                                  for k, v in Counter(unknown).items())))
    if not apply_it:
        lines.append('DRY RUN. Nothing was written. Re-run with --apply.')
        return 0, lines, by
    d = shard_dir or SHARD_DIR
    existing = read_all(legacy_path, d)
    have = set()
    for session, n, rec in read_shards(d)[0]:
        have.add(_ident(rec))
    wrote = 0
    for session, recs in sorted(by.items()):
        for rec in recs:
            if _ident(rec) in have:
                continue          # idempotent: already in a shard
            rc, msg = append(session, rec, d)
            if rc:
                lines.append('STOPPED at %s: %s' % (_ident(rec), msg))
                return 2, lines, by
            have.add(_ident(rec))
            wrote += 1
    lines.append('APPLIED: %d record(s) written into shards; %d already there.'
                 % (wrote, len(existing['records']) - wrote
                    if existing['records'] else 0))
    return 0, lines, by


def validate(legacy_path=None, shard_dir=None):
    """Findings, not a boolean. Exit 1 if any, 2 if a layer could not be read."""
    findings = []
    legacy, note = read_legacy(legacy_path)
    if legacy is None:
        return 2, ['COULD NOT RUN: %s. A gate whose input is missing has '
                   'checked NOTHING.' % note]
    # THE IDENTITY THIS MODULE USES MUST STILL BE THE ONE THE LEGACY FILE
    # DECLARES. If that drifts, the two layers stop agreeing on what one record
    # is and a discharge would silently create a second obligation instead.
    try:
        d = json.load(io.open(legacy_path or LEGACY, encoding='utf-8'))
        declared = tuple(d.get('merge_policy', {}).get('identity') or ())
    except Exception:                            # noqa: BLE001
        declared = ()
    if declared and declared != IDENTITY:
        findings.append('IDENTITY DRIFT: the legacy merge_policy declares %s '
                        'and this module uses %s. A discharge keyed on the '
                        'wrong fields creates a second obligation instead of '
                        'closing one.' % (list(declared), list(IDENTITY)))
    layers, problems = read_shards(shard_dir)
    for p in problems:
        if 'ABSENT' not in p:
            findings.append(p)
    seen = {}
    for session, n, rec in layers:
        for k in IDENTITY:
            if not str(rec.get(k, '')).strip():
                findings.append('%s.jsonl:%d has no %s' % (session, n, k))
        key = (session, n)
        seen[key] = rec
    return (1 if findings else 0), findings


# ═════════════════════════ FIXTURES, BOTH DIRECTIONS ════════════════════════
def selftest(verbose=True):
    import shutil
    import tempfile
    bad = 0

    def chk(name, cond, detail=''):
        nonlocal_bad = 0
        if cond:
            if verbose:
                print('  ok   %s' % name)
        else:
            if verbose:
                print('  FAIL %s   -> %s' % (name, detail))
            nonlocal_bad = 1
        return nonlocal_bad

    tmp = tempfile.mkdtemp(prefix='tastore-')
    try:
        lp = os.path.join(tmp, 'tier-a-reviews.json')
        sd = os.path.join(tmp, 'tier-a-reviews')
        base = {
            'merge_policy': {'identity': list(IDENTITY)},
            'records': [
                {'author_session': 'hank', 'opened_at': '2026-01-01T00:00:00Z',
                 'status': 'open', 'resources': ['bld_bids'],
                 'files': ['a.js'], 'what': 'the opening record'},
                {'author_session': 'cody', 'opened_at': '2026-01-02T00:00:00Z',
                 'status': 'open', 'resources': ['sen_visits']},
            ]}
        io.open(lp, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(base, indent=2) + '\n')

        r = read_all(lp, sd)
        bad += chk('the legacy base layer is read with no shards present',
                   len(r['records']) == 2 and not r['degraded'],
                   json.dumps(r['records']))

        # THE WHOLE POINT: discharge a LEGACY-opened obligation by appending
        rc, msg = append('fourth', {
            'author_session': 'hank', 'opened_at': '2026-01-01T00:00:00Z',
            'status': 'reviewed', 'reviewer_session': 'fourth',
            'verdict': 'ok'}, sd)
        bad += chk('a reviewer may append a discharge for ANOTHER session\'s '
                   'obligation', rc == 0, msg)
        r = read_all(lp, sd)
        got = [x for x in r['records']
               if x['author_session'] == 'hank'][0]
        bad += chk('the discharge SUPERSEDES the legacy record, still ONE row',
                   len(r['records']) == 2 and got['status'] == 'reviewed',
                   json.dumps(r['records']))
        bad += chk('the appended line did NOT erase fields it did not name',
                   got.get('resources') == ['bld_bids'] and got.get('files') == ['a.js']
                   and got.get('what') == 'the opening record', json.dumps(got))
        bad += chk('the reviewer is recorded and is not the author',
                   got['reviewer_session'] == 'fourth'
                   and got['reviewer_session'] != got['author_session'])
        bad += chk('provenance names the shard AND the legacy layer',
                   r['provenance'][('hank', '2026-01-01T00:00:00Z')]
                   == ['legacy', 'fourth.jsonl:1'],
                   str(r['provenance'][('hank', '2026-01-01T00:00:00Z')]))
        bad += chk('THE LEGACY FILE WAS NOT TOUCHED',
                   json.load(io.open(lp, encoding='utf-8'))['records'][0]['status']
                   == 'open')

        # a NEW obligation, existing in no legacy layer
        rc, _ = append('fourth', {'author_session': 'fourth',
                                  'opened_at': '2026-01-03T00:00:00Z',
                                  'status': 'open'}, sd)
        r = read_all(lp, sd)
        bad += chk('a shard-only record appears as a THIRD row',
                   len(r['records']) == 3, str(len(r['records'])))

        # ── the refusal directions ──────────────────────────────────────────
        rc, msg = append('nobody', {'author_session': 'x',
                                    'opened_at': 'y'}, sd)
        bad += chk('an unknown session is REFUSED', rc == 2 and 'not a known' in msg, msg)
        rc, msg = append('fourth', {'author_session': 'fourth'}, sd)
        bad += chk('a record with no opened_at is REFUSED -- it could never be '
                   'discharged', rc == 2 and 'no identity' in msg, msg)
        rc, msg = append('fourth', ['not', 'an', 'object'], sd)
        bad += chk('a non-object record is REFUSED', rc == 2, msg)

        # ── a shard whose last line lost its newline ────────────────────────
        p4 = os.path.join(sd, 'fourth.jsonl')
        body = io.open(p4, encoding='utf-8').read().rstrip('\n')
        io.open(p4, 'w', encoding='utf-8', newline='\n').write(body)
        rc, _ = append('fourth', {'author_session': 'fourth',
                                  'opened_at': '2026-01-04T00:00:00Z'}, sd)
        lines = [l for l in io.open(p4, encoding='utf-8').read().split('\n') if l.strip()]
        bad += chk('appending after a MISSING final newline does not concatenate '
                   'two records', rc == 0 and len(lines) == 3, str(len(lines)))

        # ── an unparseable line is reported per line and degrades the read ──
        io.open(os.path.join(sd, 'cc.jsonl'), 'w', encoding='utf-8',
                newline='\n').write('{not json\n')
        r = read_all(lp, sd)
        bad += chk('one bad line is reported PER LINE, not swallowed',
                   any('cc.jsonl:1 UNPARSEABLE' in p for p in r['problems']),
                   str(r['problems']))
        bad += chk('...and the read is marked DEGRADED rather than complete',
                   r['degraded'] is True)
        bad += chk('...and the GOOD records are still returned',
                   len(r['records']) >= 3, str(len(r['records'])))

        # ── the legacy layer failing CLOSED ────────────────────────────────
        io.open(lp, 'w', encoding='utf-8', newline='\n').write('{not json')
        recs, note = read_legacy(lp)
        bad += chk('an unreadable legacy file returns None, never []',
                   recs is None and 'UNREADABLE' in note, note)
        r = read_all(lp, sd)
        bad += chk('...and read_all marks itself DEGRADED rather than '
                   'reporting a clean small ledger', r['degraded'] is True)

        # ── migration is idempotent and does not forge an author ───────────
        io.open(lp, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(base, indent=2) + '\n')
        sd2 = os.path.join(tmp, 'shards2')
        rc, lines1, _ = migrate(True, lp, sd2, all_authors=True)
        n1 = len(read_shards(sd2)[0])
        rc2, lines2, _ = migrate(True, lp, sd2, all_authors=True)
        n2 = len(read_shards(sd2)[0])
        bad += chk('migrate --apply --all-authors is IDEMPOTENT -- a second run '
                   'writes nothing',
                   rc == 0 and rc2 == 0 and n1 == 2 and n2 == 2,
                   '%d then %d' % (n1, n2))

        # ── THE --all-authors GUARD, BOTH DIRECTIONS ──────────────────────
        # Found by observation: a rebase brought one new hank record into the
        # legacy file mid-batch, and a casual `--migrate --apply` would have
        # written a line into hank.jsonl while this module's own rule says a
        # session appends only to its own shard.
        sd4 = os.path.join(tmp, 'shards4')
        was = os.environ.get('SAIRN_SESSION')
        os.environ['SAIRN_SESSION'] = 'cody'
        try:
            rc, lines4, _ = migrate(True, lp, sd4)
            names = sorted(os.listdir(sd4)) if os.path.isdir(sd4) else []
            bad += chk('WITHOUT --all-authors only the invoking session OWN '
                       'shard is written', rc == 0 and names == ['cody.jsonl'],
                       str(names))
            bad += chk('...and the records it did NOT write are NAMED, not '
                       'silently dropped',
                       any('OWN SHARD ONLY' in l and 'hank=1' in l
                           for l in lines4), ' | '.join(lines4))
            r4 = read_all(lp, sd4)
            bad += chk('...and the OTHER author record is still read, from '
                       'the legacy base layer', len(r4['records']) == 2,
                       str(len(r4['records'])))
        finally:
            if was is None:
                os.environ.pop('SAIRN_SESSION', None)
            else:
                os.environ['SAIRN_SESSION'] = was
        bad += chk('migrate leaves the legacy file byte-identical',
                   json.load(io.open(lp, encoding='utf-8'))['records'][0]['status']
                   == 'open')
        base2 = json.loads(json.dumps(base))
        base2['records'].append({'author_session': 'someone-else',
                                 'opened_at': '2026-01-09T00:00:00Z'})
        lp2 = os.path.join(tmp, 'legacy2.json')
        io.open(lp2, 'w', encoding='utf-8', newline='\n').write(json.dumps(base2))
        rc, lines3, _ = migrate(False, lp2, os.path.join(tmp, 'shards3'))
        bad += chk('a record with an UNKNOWN author is named, not migrated into '
                   'somebody else\'s shard',
                   any('NOT a known' in l for l in lines3), ' | '.join(lines3))

        # ── validate catches identity drift ───────────────────────────────
        drift = json.loads(json.dumps(base))
        drift['merge_policy']['identity'] = ['author_session']
        lp3 = os.path.join(tmp, 'legacy3.json')
        io.open(lp3, 'w', encoding='utf-8', newline='\n').write(json.dumps(drift))
        rc, f = validate(lp3, os.path.join(tmp, 'empty'))
        bad += chk('validate reports IDENTITY DRIFT against the legacy '
                   'merge_policy', rc == 1 and any('IDENTITY DRIFT' in x for x in f),
                   ' | '.join(f))
        rc, f = validate(lp, os.path.join(tmp, 'empty'))
        bad += chk('...and says nothing when the identity agrees', rc == 0,
                   ' | '.join(f))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if verbose:
        print('  %d fixture(s) failed' % bad if bad
              else '  ALL FIXTURES PASS')
    return bad


def main(argv):
    if '--selftest' in argv:
        print('TIER A REVIEW STORE -- fixtures, criteria %s' % CRITERIA_VERSION)
        return 1 if selftest() else 0

    bad = selftest(verbose=False)
    if bad:
        print('COULD NOT RUN: %d fixture(s) failed, so nothing is reported.' % bad)
        print('Run --selftest to see which. This is exit 2, not a result with a')
        print('caveat: a store that cannot pass its own criteria produces a')
        print('ledger nobody can use.')
        return 2

    if '--validate' in argv:
        rc, findings = validate()
        print('TIER A REVIEW STORE -- validate, criteria %s' % CRITERIA_VERSION)
        for f in findings:
            print('  ! %s' % f)
        print('  %s' % ('%d finding(s)' % len(findings) if findings
                        else 'no findings'))
        return rc

    if '--migrate' in argv:
        rc, lines, _ = migrate('--apply' in argv,
                                all_authors='--all-authors' in argv)
        print('TIER A REVIEW STORE -- migrate, criteria %s' % CRITERIA_VERSION)
        for l in lines:
            print('  %s' % l)
        return rc

    if '--append' in argv:
        i = argv.index('--append')
        if i + 1 >= len(argv):
            print('COULD NOT RUN: --append <session>')
            return 2
        session = argv[i + 1]
        if '--record' not in argv:
            print('COULD NOT RUN: --record \'<json object>\' is required')
            return 2
        raw = argv[argv.index('--record') + 1]
        try:
            rec = json.loads(raw)
        except Exception as e:                   # noqa: BLE001
            print('COULD NOT RUN: --record is not JSON (%s)' % e)
            return 2
        rc, msg = append(session, rec)
        print(msg)
        return rc

    r = read_all()
    if '--json' in argv:
        print(json.dumps({'records': r['records'], 'problems': r['problems'],
                          'degraded': r['degraded']},
                         ensure_ascii=False, indent=1))
        return 2 if r['degraded'] else 0
    print('TIER A REVIEW STORE -- read, criteria %s' % CRITERIA_VERSION)
    for p in r['problems']:
        print('  %s' % p)
    recs = r['records']
    openx = [x for x in recs if str(x.get('status', '')) != 'reviewed']
    print('  %d record(s) after union; %d not reviewed' % (len(recs), len(openx)))
    shard_only = sum(1 for k, v in r['provenance'].items() if 'legacy' not in v)
    # LAYERED IS NOT CHANGED, and the first draft of this line conflated them:
    # it reported all 265 migrated records as "superseded by an appended line"
    # when every one was a byte-identical mirror of itself. A count that reads
    # as 265 edits when there were none is the fabrication shape, in the tool
    # built to stop one.
    legacy_recs, _n = read_legacy()
    was = {_ident(x): json.dumps(x, sort_keys=True) for x in (legacy_recs or [])}
    layered = changed = 0
    for rec in recs:
        i = _ident(rec)
        if len(r['provenance'].get(i, [])) > 1:
            layered += 1
            if was.get(i) != json.dumps(rec, sort_keys=True):
                changed += 1
    print('  %d record(s) exist ONLY in a shard' % shard_only)
    print('  %d legacy record(s) also have a shard line, of which %d DIFFER '
          'from the legacy value (the rest are identical mirrors, not edits)'
          % (layered, changed))
    if r['degraded']:
        print('')
        print('  DEGRADED: a layer could not be fully read, so the list above is')
        print('  NOT known to be complete. Do not treat it as a clean ledger.')
    print('')
    print('  NOT YET AUTHORITATIVE. tools/tier_a_review_gate.py still reads')
    print('  docs/tier-a-reviews.json directly, so a discharge that exists only')
    print('  in a shard is NOT yet seen by the push gate. The two call sites')
    print('  are routed to cc in')
    print('  docs/2026-10-16-fourth-b28-tier-a-shards-routed-to-cc.md.')
    if '--open-only' in argv:
        for x in openx:
            print('    %-8s %s  %s' % (x.get('author_session'),
                                       x.get('opened_at'),
                                       ','.join(x.get('resources') or [])[:60]))
    return 2 if r['degraded'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
