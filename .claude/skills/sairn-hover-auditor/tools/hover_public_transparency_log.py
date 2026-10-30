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


# ── REAL PROOF VERIFICATION, built H1 b68 ────────────────────────────────
# WHY THIS HAD TO BE BUILT RATHER THAN SHELLED OUT: b68 required confirming
# each published proof actually verifies. Checked first -- there is no `ots`
# CLI on this machine and no `opentimestamps` Python package installed, so
# "it verifies" could not be delegated. And a proof does NOT contain the
# digest it attests: an OpenTimestamps proof is a SEQUENCE OF OPERATIONS
# whose implicit starting value is the digest you submitted. Confirmed
# directly before writing any of this -- the submitted digest's own bytes
# are literally absent from the returned file. So a check that the file
# merely exists, is non-trivially long, or "contains the hash" is not a
# verification at all; the second of those is what this tool shipped with in
# b67 and the third would have silently always failed.
#
# WHAT THIS DOES VERIFY, PRECISELY: it REPLAYS the proof's operation chain
# starting from this role's own canonical digest for that (seq, hash, ts),
# and confirms (a) the proof parses completely with no unknown opcode and no
# trailing bytes, (b) every operation applies cleanly, and (c) the chain
# terminates in one or more real attestations, naming the calendar for a
# pending one. Because the replay STARTS from the locally recomputed digest,
# a proof that is well-formed but attests to some OTHER digest fails -- which
# is the property that actually matters and the one a file-exists check
# cannot see.
#
# WHAT IT DOES NOT VERIFY, STATED PLAINLY: Bitcoin inclusion. A freshly
# issued proof carries a PENDING attestation -- the calendar's promise to
# include the commitment in a future block. Confirming that requires waiting
# for the block and upgrading the proof against a Bitcoin node or explorer.
# PENDING is reported as PENDING, never as verified-on-chain.

OP_APPEND = 0xf0
OP_PREPEND = 0xf1
OP_REVERSE = 0xf2
OP_HEXLIFY = 0xf3
OP_SHA1 = 0x02
OP_RIPEMD160 = 0x03
OP_SHA256 = 0x08
OP_KECCAK256 = 0x67
OP_ATTESTATION = 0x00
OP_FORK = 0xff

PENDING_TAG = bytes.fromhex('83dfe30d2ef90c8e')
BITCOIN_TAG = bytes.fromhex('0588960d73d71901')


class _Reader:
    def __init__(self, data):
        self.d = data
        self.i = 0

    def byte(self):
        if self.i >= len(self.d):
            raise CouldNotTell('proof truncated: ran out of bytes')
        b = self.d[self.i]
        self.i += 1
        return b

    def varuint(self):
        val = 0
        shift = 0
        while True:
            b = self.byte()
            val |= (b & 0x7f) << shift
            if not (b & 0x80):
                return val
            shift += 7

    def varbytes(self):
        n = self.varuint()
        if self.i + n > len(self.d):
            raise CouldNotTell('proof truncated: varbytes length %d exceeds '
                                'remaining %d' % (n, len(self.d) - self.i))
        out = self.d[self.i:self.i + n]
        self.i += n
        return out

    def done(self):
        return self.i >= len(self.d)


def _apply_op(op, value, operand=None):
    import hashlib as _h
    if op == OP_APPEND:
        return value + operand
    if op == OP_PREPEND:
        return operand + value
    if op == OP_REVERSE:
        return value[::-1]
    if op == OP_HEXLIFY:
        return value.hex().encode('ascii')
    if op == OP_SHA256:
        return _h.sha256(value).digest()
    if op == OP_SHA1:
        return _h.sha1(value).digest()
    if op == OP_RIPEMD160:
        h = _h.new('ripemd160')
        h.update(value)
        return h.digest()
    if op == OP_KECCAK256:
        raise CouldNotTell('proof uses keccak256, which this verifier does '
                            'not implement -- reported rather than skipped')
    raise CouldNotTell('unknown operation byte 0x%02x' % op)


def replay_proof(proof_bytes, start_digest):
    """(attestations, reason). attestations is a list of dicts:
    {'kind': 'pending'|'bitcoin'|'unknown', 'detail': str,
     'commitment': hex}. Raises CouldNotTell on anything malformed.

    Walks the operation tree from `start_digest`, handling FORK (0xff) by
    recursing down each branch, exactly as the format requires -- a verifier
    that ignored forks would silently verify only one branch of a
    multi-calendar proof and report the rest as absent."""
    r = _Reader(proof_bytes)
    attestations = []

    def walk(value):
        while True:
            op = r.byte()
            if op == OP_FORK:
                # A fork duplicates the current value down two branches; the
                # first branch is parsed to completion, then the second
                # continues from the SAME value.
                walk(value)
                continue
            if op == OP_ATTESTATION:
                tag = bytes(r.d[r.i:r.i + 8])
                r.i += 8
                payload = r.varbytes()
                if tag == PENDING_TAG:
                    pr = _Reader(payload)
                    url = pr.varbytes().decode('utf-8', 'replace')
                    attestations.append({'kind': 'pending', 'detail': url,
                                          'commitment': value.hex()})
                elif tag == BITCOIN_TAG:
                    pr = _Reader(payload)
                    height = pr.varuint()
                    attestations.append({'kind': 'bitcoin',
                                          'detail': 'block height %d' % height,
                                          'commitment': value.hex()})
                else:
                    attestations.append({'kind': 'unknown',
                                          'detail': 'tag %s' % tag.hex(),
                                          'commitment': value.hex()})
                return
            if op in (OP_APPEND, OP_PREPEND):
                value = _apply_op(op, value, r.varbytes())
                continue
            value = _apply_op(op, value)

    walk(start_digest)
    if not r.done():
        raise CouldNotTell('proof has %d trailing byte(s) after the operation '
                            'chain -- not accepted as well-formed'
                            % (len(proof_bytes) - r.i))
    if not attestations:
        raise CouldNotTell('proof contains no attestation at all')
    return attestations, None


def pin_values(proof_bytes, digest_bytes):
    """What a proof must keep producing from THIS digest: its own sha256 and the
    sorted commitment hexes of its attestations. An OTS operation chain does not
    contain the digest it was issued for, so replay parses from ANY 32 bytes;
    only a commitment recorded when the digest was known to be right can tell a
    swapped row from the original (H2-b98-1, b117)."""
    atts, _ = replay_proof(proof_bytes, digest_bytes)
    return {'proof_sha256': hashlib.sha256(proof_bytes).hexdigest(),
            'commitments': sorted(a['commitment'] for a in atts)}


def pin_for(row, record_path=None):
    """The pinned values for a ledger row: carried on the row itself (written at
    publish time, b117 on) or, for older rows, the LATEST pin row appended by
    --pin for the same seq. None when nothing pins it."""
    if row.get('commitments') and row.get('proof_sha256'):
        return {'proof_sha256': row['proof_sha256'], 'commitments': row['commitments'],
                'basis': 'at issuance'}
    path = record_path or RECORD_PATH
    found = None
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    if r.get('type') == 'pin' and str(r.get('seq')) == str(row.get('seq')):
                        found = r
    return found


def verify_published(row, out_dir=HERE, record_path=None):
    """(ok, detail) for one ledger row; ok is True, False, or None.
    Recomputes the digest from the row's own (seq, hash, ts) and replays the
    saved proof from it. A row edited INCONSISTENTLY (digest_hex no longer
    matches its triple) is caught here. A row edited CONSISTENTLY -- another
    finding hash with its matching digest_hex -- replays fine from any digest,
    so replay alone cannot catch it; that is what the PIN is for: the proof's
    sha256 and its commitments, recorded when the digest was known to be right.
    ok is None (UNPINNED, cannot tell) when no pin exists -- never True."""
    expected = digest_for(row['seq'], row['finding_hash'], row['ts'])
    if expected.hex() != row.get('digest_hex'):
        return False, ('ledger row for seq=%s records digest %s but its own '
                        '(seq, hash, ts) recompute to %s -- the LEDGER ROW is '
                        'inconsistent with itself'
                        % (row['seq'], (row.get('digest_hex') or '')[:16],
                           expected.hex()[:16]))
    path = row.get('proof_path') or os.path.join(
        out_dir, 'finding-seq%s.ots' % row['seq'])
    if not os.path.isfile(path):
        return False, 'proof file missing at %s' % path
    try:
        with open(path, 'rb') as f:
            proof = f.read()
    except OSError as e:
        return False, 'proof unreadable: %s' % e
    try:
        atts, _ = replay_proof(proof, expected)
    except CouldNotTell as e:
        return False, 'proof did not replay from this digest: %s' % e
    kinds = ', '.join('%s (%s)' % (a['kind'], a['detail']) for a in atts)
    confirmed = [a for a in atts if a['kind'] == 'bitcoin']
    pin = pin_for(row, record_path)
    if pin is None:
        return None, ('UNPINNED -- the proof replays from the recomputed digest, but nothing '
                       'records which digest it was issued for, and replay succeeds from ANY '
                       'digest, so this row could have been swapped: cannot tell. Run --pin '
                       'to pin it from the current row (a trust-on-first-use pin, labelled '
                       'as such) -- %s' % kinds)
    if hashlib.sha256(proof).hexdigest() != pin['proof_sha256']:
        return False, 'the proof file is not the one pinned for this seq (sha256 differs)'
    if sorted(a['commitment'] for a in atts) != sorted(pin['commitments']):
        return False, ('the proof replayed from this row\'s digest gives different commitments than '
                        'the pinned ones -- the row names a different digest than the proof was '
                        'issued for')
    basis = pin.get('basis') or 'at issuance'
    if confirmed:
        return True, ('REPLAYED from the recomputed digest; PINNED (%s); BITCOIN-CONFIRMED '
                       '-- %s' % (basis, kinds))
    return True, ('REPLAYED from the recomputed digest; PINNED (%s); attestation(s) '
                   'PENDING, not yet on-chain -- %s' % (basis, kinds))


def try_upgrade(row, out_dir=HERE, http_get=None, timeout=20):
    """(state, detail) where state is 'confirmed' | 'still-pending' |
    'could-not-tell'. Asks the REAL calendar whether a Bitcoin attestation
    now exists for this proof's pending commitment, via the OTS
    GET <calendar>/timestamp/<commitment-hex> endpoint.

    A 404 is the calendar's way of saying "nothing newer yet" and is
    reported as STILL-PENDING, never as confirmed and never as an error. A
    network failure is COULD-NOT-TELL. Neither is ever folded into
    'confirmed' -- the whole value of this record is that a pending receipt
    is never described as on-chain proof."""
    expected = digest_for(row['seq'], row['finding_hash'], row['ts'])
    path = row.get('proof_path') or os.path.join(
        out_dir, 'finding-seq%s.ots' % row['seq'])
    if not os.path.isfile(path):
        return 'could-not-tell', 'proof file missing at %s' % path
    with open(path, 'rb') as f:
        proof = f.read()
    try:
        atts, _ = replay_proof(proof, expected)
    except CouldNotTell as e:
        return 'could-not-tell', 'existing proof does not replay: %s' % e
    if any(a['kind'] == 'bitcoin' for a in atts):
        return 'confirmed', 'already carries a Bitcoin attestation'
    pending = [a for a in atts if a['kind'] == 'pending']
    if not pending:
        return 'could-not-tell', 'no pending attestation to upgrade'
    commitment = pending[0]['commitment']
    calendar = (row.get('calendar_url') or DEFAULT_CALENDAR).rstrip('/')
    url = '%s/timestamp/%s' % (calendar, commitment)
    if http_get is not None:
        status, body = http_get(url)
    else:
        req = urllib.request.Request(
            url, headers={'Accept': 'application/vnd.opentimestamps.v1',
                           'User-Agent': 'sairn-hover-auditor/1.0'})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status, body = resp.status, resp.read()
        except urllib.error.HTTPError as e:
            status, body = e.code, b''
        except Exception as e:
            return 'could-not-tell', 'calendar unreachable: %s: %s' % (
                type(e).__name__, e)
    if status == 404:
        return 'still-pending', ('the calendar has nothing newer for this '
                                  'commitment yet (HTTP 404 is its "not aggregated '
                                  'into a block yet" answer, not an error)')
    if status != 200:
        return 'could-not-tell', 'calendar returned HTTP %d' % status
    if len(body) < 8:
        return 'could-not-tell', 'calendar returned an implausibly short body'
    # The upgrade response continues the timestamp FROM the commitment, so
    # it replays from the commitment bytes rather than from the digest.
    try:
        up_atts, _ = replay_proof(body, bytes.fromhex(commitment))
    except CouldNotTell as e:
        return 'could-not-tell', 'upgrade response did not replay: %s' % e
    if any(a['kind'] == 'bitcoin' for a in up_atts):
        detail = ', '.join('%s (%s)' % (a['kind'], a['detail']) for a in up_atts)
        return 'confirmed', 'calendar returned a Bitcoin attestation: %s' % detail
    return 'still-pending', ('the calendar answered but its response carries '
                             'no Bitcoin attestation yet -- %s'
                             % ', '.join(a['kind'] for a in up_atts))


def save_proof(seq, proof_bytes, out_dir):
    """Writes the binary .ots proof AND a plain-text sidecar documenting
    exactly what was submitted -- seq, hash, ts, calendar URL, digest hex
    -- and NOTHING about what the finding said. Returns (ots_path, txt_path)."""
    ots_path = os.path.join(out_dir, 'finding-seq%s.ots' % seq)
    with open(ots_path, 'wb') as f:
        f.write(proof_bytes)
    return ots_path


def record(seq, finding_hash, ts, digest_bytes, calendar_url, proof_path, record_path=RECORD_PATH,
           proof_bytes=None):
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
    if proof_bytes is not None:
        try:
            row.update(pin_values(proof_bytes, digest_bytes))   # pinned AT ISSUANCE (b117)
        except CouldNotTell as e:
            row['pin_error'] = str(e)[:120]                      # stays UNPINNED, and says why
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
                  calendar_url, proof_path, record_path=record_path, proof_bytes=proof_bytes)
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

    # ── THE VERIFIER'S OWN CONTROLS, b68. A verifier never shown to fail
    # is not a verifier -- this role's own standing rule, applied here.
    # Built against a REAL proof produced by the real calendar server, not a
    # synthetic one: a hand-built proof would only prove the parser agrees
    # with my own idea of the format.
    real_proofs = [p for p in os.listdir(HERE)
                   if p.startswith('finding-seq') and p.endswith('.ots')]
    if real_proofs and os.path.isfile(RECORD_PATH):
        rows_all = []
        with open(RECORD_PATH, encoding='utf-8') as fh:
            for line in fh:
                if line.strip():
                    rows_all.append(json.loads(line))
        row0 = rows_all[0] if rows_all else None
        if row0 and os.path.isfile(row0.get('proof_path') or ''):
            with open(row0['proof_path'], 'rb') as fh:
                real_proof = fh.read()
            good_digest = digest_for(row0['seq'], row0['finding_hash'], row0['ts'])

            atts, _ = replay_proof(real_proof, good_digest)
            ck('V1 a REAL calendar proof replays from the correct digest and '
               'yields at least one attestation', bool(atts))

            # THE CONTROL THAT MATTERS: same well-formed proof, wrong digest.
            # The ops still apply (append/prepend/sha256 work on any bytes),
            # so this does NOT raise -- it produces a DIFFERENT commitment.
            # That is exactly why verify_published recomputes the digest
            # locally rather than trusting the stored one.
            wrong = bytes((good_digest[0] ^ 0xff,)) + good_digest[1:]
            atts_wrong, _ = replay_proof(real_proof, wrong)
            ck('V2 KNOWN-BAD CONTROL: replaying the SAME proof from a wrong '
               'digest yields a DIFFERENT commitment -- so the commitment is '
               'genuinely a function of the digest, which is the whole basis '
               'of this verification',
               atts_wrong[0]['commitment'] != atts[0]['commitment'])

            truncated = real_proof[:len(real_proof) // 2]
            raised_t = False
            try:
                replay_proof(truncated, good_digest)
            except CouldNotTell:
                raised_t = True
            ck('V3 KNOWN-BAD CONTROL: a TRUNCATED proof is refused, never '
               'partially accepted', raised_t)

            raised_tr = False
            try:
                replay_proof(real_proof + b'\x99\x99', good_digest)
            except CouldNotTell as e:
                raised_tr = 'trailing' in str(e)
            ck('V4 KNOWN-BAD CONTROL: trailing bytes after the operation '
               'chain are refused as not well-formed', raised_tr)

            # A ledger row whose digest_hex disagrees with its own
            # (seq, hash, ts) must fail BEFORE the proof is even read.
            tampered = dict(row0)
            tampered['digest_hex'] = '0' * 64
            ok_t, detail_t = verify_published(tampered)
            ck('V5 KNOWN-BAD CONTROL: a ledger row whose recorded digest '
               'disagrees with its own (seq, hash, ts) FAILS, and fails on '
               'the row rather than on the proof',
               ok_t is False and 'inconsistent with itself' in detail_t)

            tampered2 = dict(row0)
            tampered2['ts'] = '1999-01-01T00:00:00Z'
            ok_t2, _ = verify_published(tampered2)
            ck('V6 KNOWN-BAD CONTROL: altering the ts in a ledger row breaks '
               'verification -- the proof is bound to the exact (seq, hash, '
               'ts) triple, not merely to the seq', ok_t2 is False)

            # H2-b98-1 (b117): the PIN. Built on the REAL proof, in a scratch copy, so the real ledger and proof
            # stay untouched. A proof replays from ANY digest, so a CONSISTENTLY swapped row needs a pin.
            ptmp = tempfile.mkdtemp(prefix='hover_ptl_pin_')
            pproof = os.path.join(ptmp, 'finding-seq%s.ots' % row0['seq'])
            with open(pproof, 'wb') as pf:
                pf.write(real_proof)
            prec = os.path.join(ptmp, 'ledger.jsonl')
            rowp = dict(row0)
            rowp['proof_path'] = pproof
            rowp.update(pin_values(real_proof, good_digest))
            ok_p, det_p = verify_published(rowp, record_path=prec)
            ck('P1 a row carrying its pin verifies ok and says PINNED', ok_p is True and 'PINNED' in det_p)
            swapped = dict(rowp)
            swapped['finding_hash'] = 'a-different-finding-hash'
            swapped['digest_hex'] = digest_for(swapped['seq'], swapped['finding_hash'], swapped['ts']).hex()
            ok_s, det_s = verify_published(swapped, record_path=prec)
            ck('P2 KNOWN-BAD CONTROL: a row swapped CONSISTENTLY (new hash, matching digest_hex, same proof) '
               'FAILS on the pin, although replay alone accepts it',
               ok_s is False and 'different commitments' in det_s)
            bare = {k: v for k, v in rowp.items() if k not in ('commitments', 'proof_sha256')}
            ok_u, det_u = verify_published(bare, record_path=prec)
            ck('P3 an UNPINNED row is None (cannot tell), never True', ok_u is None and 'UNPINNED' in det_u)
            with open(pproof, 'wb') as pf:
                pf.write(real_proof[:-1] + bytes((real_proof[-1] ^ 1,)))
            ok_f, _ = verify_published(rowp, record_path=prec)
            ck('P4 KNOWN-BAD CONTROL: a proof file altered after pinning FAILS', ok_f is False)
            with open(pproof, 'wb') as pf:
                pf.write(real_proof)
            pin_row = {'type': 'pin', 'seq': bare['seq'], 'basis': 'backfill (selftest)'}
            pin_row.update(pin_values(real_proof, good_digest))
            with open(prec, 'w', encoding='utf-8') as prf:
                prf.write(json.dumps(pin_row) + '\n')
            ok_b, det_b = verify_published(bare, record_path=prec)
            ck('P5 a backfilled pin row makes an old unpinned row verifiable and its basis is shown',
               ok_b is True and 'backfill' in det_b)
            shutil.rmtree(ptmp, ignore_errors=True)
        else:
            ck('V0 verifier controls SKIPPED -- no real proof+ledger pair '
               'available (reported, never silently passed)', False)
    else:
        ck('V0 verifier controls SKIPPED -- no real proof on disk yet '
           '(reported as not-run rather than counted as a pass)', False)

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
                    if row.get('type') == 'pin':
                        continue
                    print('seq=%(seq)s hash=%(finding_hash)s...%(ts)s -> %(proof_path)s'
                          % {'seq': row['seq'], 'finding_hash': row['finding_hash'][:12],
                             'ts': row['ts'], 'proof_path': row['proof_path']})
        return 0

    if '--upgrade' in argv:
        if not os.path.isfile(RECORD_PATH):
            print('COULD NOT RUN: no publications recorded at %s' % RECORD_PATH)
            return 2
        rows, seen = [], set()
        with open(RECORD_PATH, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    if r['seq'] not in seen:
                        seen.add(r['seq'])
                        rows.append(r)
        counts = {'confirmed': 0, 'still-pending': 0, 'could-not-tell': 0}
        for row in sorted(rows, key=lambda r: r['seq']):
            state, detail = try_upgrade(row)
            counts[state] = counts.get(state, 0) + 1
            print('%-15s seq=%-5s %s' % (state.upper(), row['seq'], detail))
        print()
        print('%d confirmed, %d still pending, %d could-not-tell.'
              % (counts['confirmed'], counts['still-pending'],
                 counts['could-not-tell']))
        print('STILL-PENDING IS RECORDED AS PENDING. A 404 from the calendar '
              'means the commitment has not been aggregated into a Bitcoin '
              'block yet; it is not an error and it is never reported as '
              'confirmation. Nothing here claims on-chain proof it does not '
              'have.')
        return 0 if counts['could-not-tell'] == 0 else 1

    if '--verify' in argv:
        if not os.path.isfile(RECORD_PATH):
            print('COULD NOT RUN: no publications recorded at %s' % RECORD_PATH)
            return 2
        only = None
        if '--seq' in argv:
            i = argv.index('--seq')
            if i + 1 < len(argv):
                only = int(argv[i + 1])
        rows = []
        with open(RECORD_PATH, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    r0 = json.loads(line)
                    if r0.get('type') != 'pin':
                        rows.append(r0)
        if only is not None:
            rows = [r for r in rows if r.get('seq') == only]
            if not rows:
                print('COULD NOT RUN: seq=%d is not in the ledger' % only)
                return 2
        bad = 0
        unpinned = 0
        seen = set()
        for row in rows:
            if row['seq'] in seen:
                continue
            seen.add(row['seq'])
            ok, detail = verify_published(row)
            print('%s seq=%-5s %s' % ('ok  ' if ok else ('????' if ok is None else 'FAIL'), row['seq'], detail))
            if ok is None:
                unpinned += 1
            elif not ok:
                bad += 1
        print()
        print('%d proof(s) checked, %d failed, %d UNPINNED (cannot tell, counted as neither ok nor failed).'
              % (len(seen), bad, unpinned))
        print('WHAT "ok" MEANS HERE, and the limit is sharper than it first '
              'looks. It means: (1) the ledger row is self-consistent -- its '
              'recorded digest matches a digest recomputed locally from its '
              'own (seq, hash, ts); (2) the saved proof parses completely, '
              'with no unknown opcode and no trailing bytes; (3) every '
              'operation applies cleanly from that digest; (4) the chain '
              'ends in a real attestation naming a real calendar.')
        print('WHAT IT DOES NOT YET MEAN -- found by this verifier\'s own '
              'control V2: replaying the same proof from a DIFFERENT digest '
              'also succeeds, it just yields a different commitment. So the '
              'replay proves the proof is well-formed and that THIS digest '
              'produces THIS commitment -- it does NOT by itself prove the '
              'calendar committed to this digest rather than another. That '
              'binding becomes checkable only once the attestation is '
              'BITCOIN-CONFIRMED and the commitment can be matched against '
              'the real block. Until then these are well-formed pending '
              'receipts, and saying more than that would be the overclaim '
              'this role exists to catch in other people\'s work.')
        print('UPDATE b117 (H2-b98-1): a row is now ok only if it is PINNED -- its proof sha256 and '
              'commitments were recorded when the digest was known to be right, so a row swapped '
              'CONSISTENTLY (another hash with its own digest_hex) no longer passes on replay alone. '
              'UNPINNED rows exit 2 (cannot tell), never 0.')
        return 1 if bad else (2 if unpinned else 0)

    if '--pin' in argv:
        # Trust-on-first-use pin for a row published before b117. It records what the CURRENT row and
        # proof produce; it cannot prove the row was never swapped before today, and says so on the row.
        if not os.path.isfile(RECORD_PATH):
            print('COULD NOT RUN: no publications recorded at %s' % RECORD_PATH)
            return 2
        rows = []
        with open(RECORD_PATH, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    r0 = json.loads(line)
                    if r0.get('type') != 'pin':
                        rows.append(r0)
        only = None
        if '--seq' in argv and argv.index('--seq') + 1 < len(argv):
            only = str(argv[argv.index('--seq') + 1])
        done = 0
        for row in rows:
            if only is not None and str(row['seq']) != only:
                continue
            if pin_for(row) is not None:
                print('already pinned: seq=%s' % row['seq'])
                continue
            digest = digest_for(row['seq'], row['finding_hash'], row['ts'])
            path = row.get('proof_path') or os.path.join(HERE, 'finding-seq%s.ots' % row['seq'])
            try:
                with open(path, 'rb') as pf:
                    proof = pf.read()
                vals = pin_values(proof, digest)
            except (OSError, CouldNotTell) as e:
                print('COULD NOT PIN seq=%s: %s' % (row['seq'], e))
                continue
            if digest.hex() != row.get('digest_hex'):
                print('REFUSED to pin seq=%s: the row is inconsistent with itself' % row['seq'])
                continue
            pin = {'type': 'pin', 'seq': row['seq'], 'digest_hex': digest.hex(), 'basis':
                   'backfill b117: pinned from the row and proof as they are TODAY; not proof that they '
                   'were never swapped before',
                   'pinned_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
            pin.update(vals)
            with open(RECORD_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps(pin) + '\n')
            print('pinned seq=%s (%d commitment(s))' % (row['seq'], len(vals['commitments'])))
            done += 1
        print('%d row(s) pinned.' % done)
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
