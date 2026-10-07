#!/usr/bin/env python
"""hover2_timestamp.py -- this role's OWN RFC 3161 timestamp tool,
built from scratch under this role's own prefix, replacing the manual
chain-tip-anchor email with a real, independently-verifiable, third-
party timestamp.

GOAL: a signed RFC 3161 token (.tsr) over this role's own chain-tip
hash, seq and date, from a public Time-Stamp Authority DIFFERENT from
H1's (freetsa.org) -- real method diversity (a different operator, a
different trust chain), not merely a different output filename for the
same underlying service.

NON-GOALS: this does not replace the hash-chain itself (hover_log.py
owns that) or the git mirror (hover2_log_mirror.py owns that). It adds
ONE independently-verifiable fact on top of both: a real third party's
signed attestation that this exact hash existed at or before a specific
time. It does not verify the CHAIN's own internal consistency -- that is
`hover_log.py --verify`'s job, called first and cited, not re-derived
here.

TSA CHOICE: DigiCert's public timestamping service
(http://timestamp.digicert.com), then Sectigo's
(http://timestamp.sectigo.com) as the one fallback, per the standing
instruction ("if that TSA is unreachable, try one other; if both fail,
report and stop -- no substitute"). Neither is freetsa.org, operated by
a different organisation under a different root, which is the real
diversity this tool exists to add -- not a second filename pointed at
the same operator.

ALTERNATIVES CONSIDERED:
  1. Use freetsa.org, same as H1 -- rejected outright, this is exactly
     what the instruction says NOT to do: a second copy of the same
     attestation path is not a second opinion, it just makes H1's
     single point of trust look doubled.
  2. Hand-roll the TSP request/response ASN.1 rather than use
     rfc3161ng -- rejected: RFC 3161's ASN.1 structures are exactly the
     kind of hand-rolled-crypto risk this platform's own precedent
     (CLAUDE.md: security-critical crypto goes through an audited
     library, not custom code, per the @simplewebauthn/server and
     firebase-admin precedents) argues against. rfc3161ng is the
     standard library for this on PyPI.

WHAT GETS TIMESTAMPED: not the raw chain_head hash alone -- a canonical
string binding hash+seq+date together (`chain_head=<hash>;seq=<n>;
date=<iso>`), SHA256-digested, so the token itself proves WHICH seq and
date the hash belongs to, not just that some 64-hex-char string existed.
A reader with only the .tsr and the chain log can re-derive this exact
string and confirm the token covers THIS claim, not a different one.

Usage:
  python hover2_timestamp.py --log PATH [--out-dir PATH] [--repo PATH]
  python hover2_timestamp.py --verify-cmd PATH_TO_TSR   # prints the openssl command, does not run it
  python hover2_timestamp.py --selftest
"""
import argparse
import hashlib
import json
import os
import sys

TSAS = [
    ('digicert', 'http://timestamp.digicert.com'),
    ('sectigo', 'http://timestamp.sectigo.com'),
]


def canonical_message(chain_head, seq, date):
    return 'chain_head=%s;seq=%s;date=%s' % (chain_head, seq, date)


def load_tip(log_path):
    last = None
    with open(log_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            last = json.loads(line)
    if not last:
        return None
    return last.get('hash'), last.get('seq'), last.get('ts')


def request_timestamp(message_bytes, timeout=15):
    """Tries each TSA in TSAS order. Returns (tsa_name, tsr_bytes) on the
    first success, or raises the last error after both fail -- the
    standing instruction's own 'try one other; if both fail, report and
    stop' as control flow, not prose."""
    import rfc3161ng
    digest = hashlib.sha256(message_bytes).digest()
    errors = []
    for name, url in TSAS:
        try:
            timestamper = rfc3161ng.RemoteTimestamper(
                url, hashname='sha256', timeout=timeout)
            tsr = timestamper.timestamp(digest=digest)
            return name, tsr
        except Exception as e:
            errors.append('%s (%s): %s' % (name, url, e))
    raise RuntimeError('ALL TSAs FAILED, no substitute attempted:\n  '
                       + '\n  '.join(errors))


def _print_verify_help(tsr_path, req_path=None):
    """Single source for the verify instructions -- printed from both
    --verify-cmd and a real successful run, and exercised by selftest's
    own regression guard, so there is only one place to get this right."""
    if req_path is None:
        req_path = os.path.splitext(tsr_path)[0] + '.message.txt'
    print('Independent verify (no dependency on this tool or any TSA library):')
    print('  openssl ts -reply -in "%s" -token_in -text' % tsr_path)
    print('  -token_in IS REQUIRED: rfc3161ng\'s timestamp() returns the bare')
    print('  TimeStampToken (a PKCS#7 SignedData ContentInfo), not the full')
    print('  TimeStampResp wrapper openssl expects by default -- without the')
    print('  flag this fails with an ASN.1 "wrong tag" error. Caught on this')
    print('  tool\'s own first real run (batch M) by distrusting its own')
    print('  success message and verifying independently before trusting it.')
    print('  (confirms the token\'s own content: TSA, serial, genTime, digest)')
    print('')
    print('To confirm the digest inside the token matches THIS claim, re-derive it:')
    print('  python -c "import hashlib; print(hashlib.sha256(open(%r, encoding=%r).read().encode()).hexdigest())"'
          % (req_path, 'utf-8'))
    print('  then compare against the token\'s own MessageImprint (shown by the')
    print('  openssl command above) -- a match proves the token covers exactly')
    print('  this chain_head/seq/date triple, not a different one.')


def selftest():
    # No network, no real TSA call -- proves the canonical-message
    # construction and digest binding are deterministic and that a
    # changed seq/date/hash produces a DIFFERENT digest (the property
    # that makes the token specific to one claim, not reusable for a
    # different one).
    m1 = canonical_message('abc123', 5, '2026-10-07T00:00:00Z')
    m2 = canonical_message('abc123', 6, '2026-10-07T00:00:00Z')
    m3 = canonical_message('abc123', 5, '2026-10-07T00:00:00Z')
    d1 = hashlib.sha256(m1.encode()).digest()
    d2 = hashlib.sha256(m2.encode()).digest()
    d3 = hashlib.sha256(m3.encode()).digest()
    ok = (d1 != d2) and (d1 == d3)

    # REGRESSION GUARD for this tool's own first real-run bug (batch M):
    # rfc3161ng's timestamp() returns a bare TimeStampToken, not the full
    # TimeStampResp wrapper -- the printed verify command MUST carry
    # -token_in or a reader following it gets the same ASN.1 "wrong tag"
    # error this tool's own author hit before checking independently.
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _print_verify_help('fx.tsr')
    has_token_in = '-token_in' in buf.getvalue()
    ok = ok and has_token_in

    print('SELFTEST %s: same-inputs digest stable=%s, seq-changed digest differs=%s, '
          'verify command carries -token_in=%s' %
          ('PASS' if ok else 'FAIL', d1 == d3, d1 != d2, has_token_in))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', default='hover-audit-log.jsonl')
    ap.add_argument('--out-dir', default='.')
    ap.add_argument('--verify-cmd')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if args.verify_cmd:
        _print_verify_help(args.verify_cmd)
        sys.exit(0)

    log_path = args.log
    if not os.path.isfile(log_path):
        print('COULD NOT RUN: %s not found' % log_path)
        sys.exit(2)
    tip = load_tip(log_path)
    if not tip:
        print('COULD NOT RUN: log is empty or unparseable')
        sys.exit(2)
    chain_head, seq, date = tip
    message = canonical_message(chain_head, seq, date)
    message_bytes = message.encode('utf-8')

    try:
        tsa_name, tsr = request_timestamp(message_bytes)
    except Exception as e:
        print('COULD NOT RUN: %s' % e)
        print('NO SUBSTITUTE ATTEMPTED, per standing instruction.')
        sys.exit(2)

    tsr_path = os.path.join(args.out_dir, 'chain-tip-seq%s.tsr' % seq)
    msg_path = os.path.join(args.out_dir, 'chain-tip-seq%s.message.txt' % seq)
    with open(tsr_path, 'wb') as f:
        f.write(tsr)
    with open(msg_path, 'w', encoding='utf-8') as f:
        f.write(message)

    print('TSA used: %s' % tsa_name)
    print('Timestamped message: %s' % message)
    print('Saved: %s' % tsr_path)
    print('Saved: %s' % msg_path)
    print('')
    _print_verify_help(tsr_path, msg_path)
    sys.exit(0)


if __name__ == '__main__':
    main()
