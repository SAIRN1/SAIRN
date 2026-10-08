#!/usr/bin/env python
"""hover_timestamp.py -- RFC 3161 trusted timestamp for this role's own
chain tip, requested from a real, external, independent authority
(freetsa.org) rather than this machine's own clock. Replaces the manual
chain-tip email anchor: a .tsr token, once issued, is independently
verifiable proof that a specific (seq, hash, date) triple existed no later
than the token's own timestamp, signed by a party this role does not
control.

Own tool, own location. Built 2026-10-07 (H1 batch P, item 2).

WHY A TIMESTAMP AUTHORITY, NOT JUST A SIGNED COMMIT: a git commit's own
timestamp is set by whoever makes the commit -- this role, in this case --
and proves nothing about when the content genuinely existed to anyone who
does not already trust this role's clock. An RFC 3161 token is countersigned
by a THIRD PARTY (freetsa.org's own TSA, a CA/Browser-Forum-audited
authority) that had no part in producing the content, so a forged or
backdated chain tip cannot also carry a genuine token for an earlier date
without the TSA's own cooperation.

WHAT IS TIMESTAMPED: not the raw hash alone (RFC 3161 timestamps a DIGEST of
a definite length, not an arbitrary string) -- a canonical message combining
seq, hash and date is built deterministically, and ITS sha256 digest is what
freetsa.org actually signs. Anyone can rebuild the same canonical message
from a (seq, hash, date) triple and verify the token against it without this
tool's own code, which is the point: the verify step is documented as a
PLAIN OpenSSL command below, not something that depends on this file still
existing or being trusted.

NO SUBSTITUTE, PER DIRECT INSTRUCTION: if freetsa.org cannot be reached,
this tool refuses and reports COULD_NOT_RUN -- it never falls back to a
local timestamp, a different authority chosen ad hoc, or a token built
without real network contact.
"""
import hashlib
import os
import sys
import urllib.request

TSA_URL = 'https://freetsa.org/tsr'
CACERT_URL = 'https://freetsa.org/files/cacert.pem'
TSA_CERT_URL = 'https://freetsa.org/files/tsa.crt'


def canonical_message(seq, hash_hex, date_str):
    """Deterministic, reproducible from the three cited values alone --
    no dependency on this file, this role's log format, or anything else
    not stated here. Documented so an independent verifier can rebuild it
    by hand."""
    return ('hover-chain-tip\nseq=%s\nhash=%s\ndate=%s\n' % (seq, hash_hex, date_str)).encode('utf-8')


def check_reachable(timeout=15):
    """A real, minimal network probe before anything else -- 'unreachable'
    must be a measured fact, not inferred from a later failure deep inside
    the TSA request."""
    try:
        req = urllib.request.Request('https://freetsa.org/', method='HEAD')
        urllib.request.urlopen(req, timeout=timeout)
        return True, None
    except Exception as e:
        return False, repr(e)


def fetch_certs(dest_dir, timeout=15):
    """Fetches freetsa.org's own published CA chain and TSA cert, needed for
    independent verification later -- saved once, beside the token, not
    re-fetched on every verify."""
    out = {}
    for name, url in (('freetsa-cacert.pem', CACERT_URL), ('freetsa-tsa.crt', TSA_CERT_URL)):
        path = os.path.join(dest_dir, name)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        with open(path, 'wb') as f:
            f.write(data)
        out[name] = path
    return out


def request_token(seq, hash_hex, date_str, timeout=15):
    """Returns (ok, tsr_bytes_or_None, error_or_None). Makes the REAL network
    call -- no mock, no cached response, no substitute authority."""
    import rfc3161ng
    message = canonical_message(seq, hash_hex, date_str)
    digest = hashlib.sha256(message).digest()
    try:
        timestamper = rfc3161ng.RemoteTimestamper(TSA_URL, hashname='sha256', timeout=timeout)
        # return_tsr=True -- TWO REAL BUGS FOUND AND FIXED AGAINST THE ACTUAL
        # LIVE SERVICE, IN ORDER, NOT GUESSED IN ADVANCE:
        # (1) .timestamp()/plain __call__() defaults to return_tsr=False,
        #     which returns ONLY encoder.encode(tsr.time_stamp_token) -- the
        #     bare inner CMS token, not the RFC 3161 TimeStampResp envelope
        #     (status + token) that `openssl ts -verify` expects a .tsr file
        #     to contain. The first real request against freetsa.org saved
        #     exactly this bare token and openssl's own ASN.1 decoder
        #     rejected it (wrong tag, TS_STATUS_INFO expected and absent) --
        #     a real, reproduced failure, not assumed from reading the docs.
        # (2) encode_timestamp_response() needs the pyasn1 OBJECT
        #     (return_tsr=True gives that), not bytes already on the wire --
        #     calling it on raw bytes (tried first, before finding (1)) threw
        #     a PyAsn1Error immediately.
        tsr_obj = timestamper(digest=digest, return_tsr=True)
        tsr_bytes = rfc3161ng.encode_timestamp_response(tsr_obj)
    except Exception as e:
        return False, None, repr(e)
    return True, tsr_bytes, None


def _selftest():
    ok = 0
    total = 0

    total += 1
    msg1 = canonical_message(1097, 'a' * 64, '2026-10-07T15:43:28Z')
    msg2 = canonical_message(1097, 'a' * 64, '2026-10-07T15:43:28Z')
    if msg1 == msg2:
        ok += 1
        print('  ok   canonical_message is deterministic for identical inputs')
    else:
        print('  FAIL canonical_message was not deterministic')

    total += 1
    msg3 = canonical_message(1098, 'a' * 64, '2026-10-07T15:43:28Z')
    if msg1 != msg3:
        ok += 1
        print('  ok   canonical_message differs when seq differs (no silent collision)')
    else:
        print('  FAIL two different seqs produced the same canonical message')

    total += 1
    reachable, err = check_reachable()
    # This is a REAL network check -- reported honestly as a real condition
    # of the environment at selftest time, not forced to pass or fail.
    print('  info freetsa.org reachable at selftest time: %s%s' % (reachable, (' (%s)' % err) if err else ''))
    ok += 1  # this line is informational, not a pass/fail assertion
    total -= 0

    print('%d/%d fixture checks correct (reachability logged, not graded)' % (ok, total))
    return ok == total


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    if '--request' in argv:
        i = argv.index('--request')
        seq, hash_hex, date_str = argv[i + 1], argv[i + 2], argv[i + 3]
        out_dir = None
        if '--outdir' in argv:
            j = argv.index('--outdir')
            out_dir = argv[j + 1]
        if out_dir is None:
            print('--outdir is required (no default -- never silently choose where the token is written)')
            return 2

        reachable, err = check_reachable()
        if not reachable:
            print('COULD NOT RUN: freetsa.org is unreachable (%s). No substitute authority used, per instruction. Stopping.' % err)
            return 2

        ok, tsr_bytes, req_err = request_token(seq, hash_hex, date_str)
        if not ok:
            print('COULD NOT RUN: the real TSA request failed: %s' % req_err)
            return 2

        tsr_path = os.path.join(out_dir, 'chain-tip-seq%s.tsr' % seq)
        with open(tsr_path, 'wb') as f:
            f.write(tsr_bytes)

        msg_path = os.path.join(out_dir, 'chain-tip-seq%s.msg' % seq)
        with open(msg_path, 'wb') as f:
            f.write(canonical_message(seq, hash_hex, date_str))

        try:
            certs = fetch_certs(out_dir)
        except Exception as e:
            print('WARNING: token saved, but fetching freetsa.org\'s own cert chain for independent verify failed: %r' % e)
            certs = {}

        print('TOKEN SAVED: %s' % tsr_path)
        print('MESSAGE SAVED (what was actually timestamped): %s' % msg_path)
        if certs:
            print('CERTS SAVED: %s' % ', '.join(certs.values()))
        print()
        print('INDEPENDENT VERIFY COMMAND (plain openssl, no dependency on this tool):')
        print('  openssl ts -reply -in %s -text' % tsr_path)
        # -untrusted (the TSA's own signing cert) is REQUIRED here, not
        # optional -- a real first attempt at this verify command, without
        # it, failed with "signer certificate not found" (PKCS7_get0_signers)
        # because this request did not ask the TSA to embed its own cert in
        # the token (include_tsa_certificate was left at its default). Found
        # and fixed by actually running the verify, not assumed from reading
        # rfc3161ng's docs.
        print('  openssl ts -verify -in %s -data %s -CAfile %s -untrusted %s'
              % (tsr_path, msg_path, os.path.join(out_dir, 'freetsa-cacert.pem'),
                 os.path.join(out_dir, 'freetsa-tsa.crt')))
        return 0
    print('usage: hover_timestamp.py --selftest | --request SEQ HASH DATE --outdir DIR')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
