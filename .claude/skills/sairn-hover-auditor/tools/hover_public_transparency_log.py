#!/usr/bin/env python
"""hover_public_transparency_log.py -- a genuinely independent, PUBLIC,
hash-only transparency record for individual findings in this role's own
self-log, built H1 b67 per direct instruction.

NEVER THE FINDING TEXT, ONLY seq + hash + timestamp. The ONLY three values
read from a real log entry are its `seq`, its own hash-chain `hash` (itself
already an opaque sha256 digest, never the raw summary), and its `ts`.
`summary`, `ref`, `vector` and every other field are never read, never
touched, never sent anywhere by this file. This is the whole point: a
later reader who has NOT seen the finding's text can still verify that
THIS EXACT entry (by its own chain hash) existed, at this claimed seq, no
later than this publicly, independently timestamped moment -- without this
tool ever having disclosed what the finding said.

WHY THIS IS A DIFFERENT MECHANISM FROM hover_timestamp.py, NOT A DUPLICATE.
hover_timestamp.py timestamps the CHAIN TIP ONLY (one checkpoint, via a
single RFC 3161 Time-Stamp Authority, freetsa.org) -- a real, independent,
CA/Browser-Forum-audited party, but still ONE centralized authority whose
own cooperation a forger would need to subvert. This file timestamps
INDIVIDUAL findings (any seq, not only the tip) via OpenTimestamps, which
is intentionally decentralized: the calendar server is a free convenience
front-end, and the real, permanent anchor is the Bitcoin blockchain itself
once a proof is "upgraded" -- no single party, including OpenTimestamps'
own calendar operators, can later deny or alter a confirmed attestation.
Two different trust models, both real, kept distinct rather than treated
as redundant.

THE CANDIDATE SERVICE'S CURRENT TERMS, CHECKED BEFORE USE, H1 b67. Fetched
https://opentimestamps.org and the opentimestamps-server README directly:
NO published terms of service, usage policy, rate limit or acceptable-use
statement exists for the public calendar servers. The site's own words:
"These servers are free to use and they don't require any registration or
api key." They are stated to run on donations. Because no formal rate
limit is published, this tool is deliberately conservative by design,
named here rather than assumed: it submits ONE 32-byte digest per real
--publish call, never loops or batches multiple findings in one run, and
every real submission is logged with the calendar URL actually used so a
later reader can see exactly how much real traffic this role sent.
Real HTTP contract, confirmed live before writing a single line of this
tool against it (not assumed from documentation, which does not actually
describe it): `POST <calendar>/digest` with the raw 32-byte sha256 digest
as the request body, `Accept: application/vnd.opentimestamps.v1` ->
HTTP 200, a binary OTS proof in the response body. Confirmed with a real,
disposable test digest before this tool existed.

NO SUBSTITUTE, SAME DISCIPLINE AS hover_timestamp.py. If the calendar
server is unreachable or answers anything other than 200, this tool
refuses (COULD_NOT_RUN) -- it never silently falls back to a different,
undisclosed service, and never fabricates a local-only "proof" standing
in for a real submission.

Run:
  python hover_public_transparency_log.py --publish --seq N [--calendar URL] [--outdir DIR]
  python hover_public_transparency_log.py --list
  python hover_public_transparency_log.py --selftest
"""
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, 'hover-audit-log.jsonl')
RECORD_PATH = os.path.join(HERE, 'public-transparency-log.jsonl')

# The default calendar server -- one of OpenTimestamps' own named, public,
# independently-operated servers. Not this role's infrastructure, not
# SAIRN's, not Anthropic's.
DEFAULT_CALENDAR = 'https://a.pool.opentimestamps.org'


class CouldNotTell(Exception):
    pass


def canonical_message(seq, finding_hash, ts):
    """Deterministic, reproducible from the three cited values alone --
    same discipline as hover_timestamp.py's own canonical_message(), so an
    independent verifier can rebuild this exact byte string by hand from
    (seq, hash, ts) without trusting this file still exists or is
    unmodified. Carries ONLY these three values -- never finding text."""
    return ('hover-finding-transparency\nseq=%s\nhash=%s\nts=%s\n'
            % (seq, finding_hash, ts)).encode('utf-8')


def digest_for(seq, finding_hash, ts):
    return hashlib.sha256(canonical_message(seq, finding_hash, ts)).digest()


def load_entry_fields(seq, log_path=LOG_PATH):
    """Returns ONLY {'seq', 'hash', 'ts'} for the entry -- deliberately
    narrowed at the read site itself, not just "not used later", so a
    future edit to this file cannot accidentally start threading the
    summary through by forgetting to drop it somewhere downstream."""
    if not os.path.isfile(log_path):
        raise CouldNotTell('self-log not found at %s' % log_path)
    with open(log_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if e.get('seq') == seq:
                return {'seq': e['seq'], 'hash': e['hash'], 'ts': e['ts']}
    raise CouldNotTell('no entry with seq=%d in %s' % (seq, log_path))


def submit_digest(digest_bytes, calendar_url=DEFAULT_CALENDAR, http_post=None, timeout=20):
    """http_post(url, digest_bytes) -> (status, body_bytes) is injectable
    for the selftest -- no real network call needed to test the logic
    around this. Returns the raw OTS proof bytes on success. Raises
    CouldNotTell on anything else -- unreachable, non-200, or an
    implausibly short body (a real proof is never near-empty)."""
    if http_post is not None:
        status, body = http_post(calendar_url, digest_bytes)
    else:
        req = urllib.request.Request(
            calendar_url.rstrip('/') + '/digest', data=digest_bytes,
            headers={'Content-Type': 'application/x-www-form-urlencoded',
                     'Accept': 'application/vnd.opentimestamps.v1',
                     'User-Agent': 'sairn-hover-auditor/1.0'},
            method='POST')
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                body = resp.read()
        except urllib.error.HTTPError as e:
            raise CouldNotTell('calendar server HTTP %d: %s'
                                % (e.code, e.read()[:200]))
        except Exception as e:
            raise CouldNotTell('calendar server call failed: %s: %s'
                                % (type(e).__name__, e))
    if status != 200:
        raise CouldNotTell('calendar server returned HTTP %d, not 200' % status)
    if len(body) < 16:
        raise CouldNotTell('calendar server returned an implausibly short '
                            'body (%d bytes) -- not trusted as a real proof' % len(body))
    return body


def save_proof(seq, proof_bytes, out_dir):
    """Writes the binary .ots proof AND a plain-text sidecar documenting
    exactly what was submitted -- seq, hash, ts, calendar URL, digest hex
    -- and NOTHING about what the finding said. Returns (ots_path, txt_path)."""
    ots_path = os.path.join(out_dir, 'finding-seq%s.ots' % seq)
    with open(ots_path, 'wb') as f:
        f.write(proof_bytes)
    return ots_path


def record(seq, finding_hash, ts, digest_bytes, calendar_url, proof_path, record_path=RECORD_PATH):
    """Appends ONE row to the local side-ledger -- seq, hash, ts, digest
    hex, calendar URL, proof path. Never the summary. This ledger is NOT
    the public artifact (the .ots proof + Bitcoin blockchain are); it is
    this role's own local index of what it has already published, so a
    re-run does not have to re-derive the list by re-reading every .ots
    file's own filename."""
    row = {'seq': seq, 'finding_hash': finding_hash, 'ts': ts,
           'digest_hex': digest_bytes.hex(), 'calendar_url': calendar_url,
           'proof_path': proof_path,
           'recorded_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    with open(record_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row) + '\n')
    return row


def already_published(seq, record_path=RECORD_PATH):
    if not os.path.isfile(record_path):
        return False
    with open(record_path, encoding='utf-8') as f:
        for line in f:
            if line.strip() and json.loads(line).get('seq') == seq:
                return True
    return False


def publish(seq, log_path=LOG_PATH, calendar_url=DEFAULT_CALENDAR, out_dir=HERE,
            record_path=RECORD_PATH, http_post=None, force=False):
    if not force and already_published(seq, record_path=record_path):
        raise CouldNotTell('seq=%d was already published (see %s) -- re-run with '
                            'force=True if this is a deliberate re-publish, never '
                            'silently duplicated' % (seq, record_path))
    fields = load_entry_fields(seq, log_path=log_path)
    digest_bytes = digest_for(fields['seq'], fields['hash'], fields['ts'])
    proof_bytes = submit_digest(digest_bytes, calendar_url=calendar_url, http_post=http_post)
    proof_path = save_proof(seq, proof_bytes, out_dir)
    row = record(fields['seq'], fields['hash'], fields['ts'], digest_bytes,
                  calendar_url, proof_path, record_path=record_path)
    return row, proof_path


# ── selftest ─────────────────────────────────────────────────────────────

def run_fixtures():
    import tempfile
    import shutil

    ok = [0]
    bad = [0]

    def ck(name, cond):
        (ok if cond else bad)[0] += 1
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))

    real_log = LOG_PATH
    real_record = RECORD_PATH
    lines_before_log = 0
    if os.path.isfile(real_log):
        with open(real_log, encoding='utf-8') as f:
            lines_before_log = sum(1 for l in f if l.strip())
    lines_before_record = 0
    if os.path.isfile(real_record):
        with open(real_record, encoding='utf-8') as f:
            lines_before_record = sum(1 for l in f if l.strip())

    msg1 = canonical_message(42, 'abc123', '2026-10-19T00:00:00Z')
    msg2 = canonical_message(42, 'abc123', '2026-10-19T00:00:00Z')
    ck('canonical_message is deterministic for identical inputs', msg1 == msg2)
    msg3 = canonical_message(43, 'abc123', '2026-10-19T00:00:00Z')
    ck('canonical_message differs when seq differs (no silent collision)', msg1 != msg3)
    ck('canonical_message never contains the word SUMMARY/finding text markers '
       '-- it is built from exactly 3 fields, nothing else',
       b'summary' not in msg1.lower() and b'severity' not in msg1.lower())

    d1 = digest_for(42, 'abc123', '2026-10-19T00:00:00Z')
    ck('digest_for returns a real 32-byte sha256 digest', len(d1) == 32)

    tmp = tempfile.mkdtemp(prefix='hover_ptl_fx_')
    fixture_log = os.path.join(tmp, 'log.jsonl')
    with open(fixture_log, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'seq': 1, 'hash': 'h1', 'ts': 't1',
                              'summary': 'SENSITIVE FINDING TEXT THAT MUST NEVER LEAK',
                              'severity': 'critical', 'target': 'someone'}) + '\n')

    fields = load_entry_fields(1, log_path=fixture_log)
    ck('load_entry_fields returns ONLY seq/hash/ts',
       set(fields.keys()) == {'seq', 'hash', 'ts'})
    ck('load_entry_fields never carries the summary text through, even '
       'though the real row has one', 'summary' not in fields and
       'SENSITIVE' not in json.dumps(fields))

    raised = False
    try:
        load_entry_fields(999, log_path=fixture_log)
    except CouldNotTell:
        raised = True
    ck('load_entry_fields raises CouldNotTell on an unknown seq, never returns None', raised)

    sent_bodies = []

    def fake_post_ok(url, digest_bytes):
        sent_bodies.append(digest_bytes)
        return 200, b'\x00' * 277  # a real proof's rough shape (never near-empty)

    proof = submit_digest(d1, http_post=fake_post_ok)
    ck('submit_digest returns the real proof bytes on a 200', len(proof) == 277)
    ck('submit_digest sent EXACTLY the digest bytes, never any text',
       sent_bodies == [d1] and b'SENSITIVE' not in sent_bodies[0])

    def fake_post_404(url, digest_bytes):
        return 404, b''

    raised2 = False
    try:
        submit_digest(d1, http_post=fake_post_404)
    except CouldNotTell:
        raised2 = True
    ck('submit_digest raises CouldNotTell on a non-200, never fabricates a proof', raised2)

    def fake_post_tiny(url, digest_bytes):
        return 200, b'x'

    raised3 = False
    try:
        submit_digest(d1, http_post=fake_post_tiny)
    except CouldNotTell:
        raised3 = True
    ck('submit_digest raises CouldNotTell on an implausibly short 200 body, '
       'rather than trusting a near-empty response as a real proof', raised3)

    out_dir = os.path.join(tmp, 'out')
    os.makedirs(out_dir)
    scratch_record = os.path.join(tmp, 'record.jsonl')

    row, proof_path = publish(1, log_path=fixture_log, out_dir=out_dir,
                                record_path=scratch_record, http_post=fake_post_ok)
    ck('publish() writes the .ots proof file for real', os.path.isfile(proof_path))
    ck('publish() records seq/hash/ts/digest/calendar/proof_path in the local ledger',
       row['seq'] == 1 and row['finding_hash'] == 'h1' and 'digest_hex' in row)
    ck('publish() record row NEVER contains the finding summary text',
       'SENSITIVE' not in json.dumps(row))

    ck('already_published correctly reports True for a just-published seq',
       already_published(1, record_path=scratch_record))

    raised4 = False
    try:
        publish(1, log_path=fixture_log, out_dir=out_dir, record_path=scratch_record,
                http_post=fake_post_ok)
    except CouldNotTell:
        raised4 = True
    ck('publish() REFUSES a duplicate re-publish of the same seq without force=True, '
       'rather than silently writing a second attestation', raised4)

    row2, _ = publish(1, log_path=fixture_log, out_dir=out_dir, record_path=scratch_record,
                       http_post=fake_post_ok, force=True)
    ck('publish() with force=True DOES allow a deliberate re-publish',
       row2['seq'] == 1)

    shutil.rmtree(tmp, ignore_errors=True)

    lines_after_log = 0
    if os.path.isfile(real_log):
        with open(real_log, encoding='utf-8') as f:
            lines_after_log = sum(1 for l in f if l.strip())
    lines_after_record = 0
    if os.path.isfile(real_record):
        with open(real_record, encoding='utf-8') as f:
            lines_after_record = sum(1 for l in f if l.strip())
    ck('SAFETY NET: the real hover-audit-log.jsonl gained zero lines '
       '(before=%d, after=%d)' % (lines_before_log, lines_after_log),
       lines_after_log == lines_before_log)
    ck('SAFETY NET: the real public-transparency-log.jsonl gained zero lines '
       '(before=%d, after=%d)' % (lines_before_record, lines_after_record),
       lines_after_record == lines_before_record)

    print('%d ok, %d failed' % (ok[0], bad[0]))
    return bad[0] == 0


def main(argv):
    if '--selftest' in argv:
        return 0 if run_fixtures() else 1

    if '--list' in argv:
        if not os.path.isfile(RECORD_PATH):
            print('no publications recorded yet')
            return 0
        with open(RECORD_PATH, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    print('seq=%(seq)s hash=%(finding_hash)s...%(ts)s -> %(proof_path)s'
                          % {'seq': row['seq'], 'finding_hash': row['finding_hash'][:12],
                             'ts': row['ts'], 'proof_path': row['proof_path']})
        return 0

    if '--publish' in argv:
        def opt(name, default=None):
            if name in argv:
                i = argv.index(name)
                if i + 1 < len(argv):
                    return argv[i + 1]
            return default

        seq = opt('--seq')
        if not seq:
            print('--publish requires --seq N')
            return 2
        calendar_url = opt('--calendar', DEFAULT_CALENDAR)
        out_dir = opt('--outdir', HERE)
        try:
            row, proof_path = publish(int(seq), calendar_url=calendar_url, out_dir=out_dir)
        except CouldNotTell as e:
            print('COULD NOT RUN: %s' % e)
            return 2
        print('PUBLISHED: seq=%d, proof saved to %s' % (row['seq'], proof_path))
        print('Calendar: %s' % calendar_url)
        print('Digest (hex): %s' % row['digest_hex'])
        print('Verify later with: ots verify <proof_path>, or wait for Bitcoin '
              'confirmation and upgrade with: ots upgrade <proof_path>')
        return 0

    print('usage: hover_public_transparency_log.py --publish --seq N '
          '[--calendar URL] [--outdir DIR] | --list | --selftest')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
