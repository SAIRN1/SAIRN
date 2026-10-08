#!/usr/bin/env python
"""hover_hash_citation_guard.py -- the system-level fix from the batch-O item
7 blameless postmortem (seq1082's self-caught fabricated chain-hash).

WHAT HAPPENED, BLAMELESSLY: mid-draft on a full handoff rewrite, this role
needed to re-state the chain tip hash it had already queried a few tool
calls earlier in the same turn. Rather than re-running the query at the
moment of writing it into prose, it typed the hash from short-term memory --
got the real, recently-seen first 8 characters right (because those were
the part actually attended to, the same way a person reads the start of a
long number and infers they "know" it) and invented the remaining 56
characters, which are not something anyone can reliably hold in working
memory. It made sense IN THE MOMENT because writing a handoff narrative
felt like a REPORTING step, not a VERIFICATION step -- the same mental mode
that does not re-check a fact already believed true. It was caught, not by
a gate, but by noticing the string "looked wrong" against what had actually
been queried -- a lucky catch, not a reliable one.

THE SYSTEM-LEVEL FIX, not "will be more careful": a mechanical gate that
scans any text for anything SHAPED like a hash this role's own log would
produce, and refuses to let it stand uncompared against the real value.
Every 64-hex-char run is checked against the real, current
hover-audit-log.jsonl -- if it does not match ANY entry's real hash,
exactly, it is flagged, by name, as UNVERIFIED rather than let through as
plausible-looking text. This is the identical principle hover_log.py's own
--source staleness guard already applies to cited file content; this
applies it to the act of TRANSCRIBING a hash value into prose, which the
staleness guard does not cover at all (prose is not a --source citation).

USAGE:
  python hover_hash_citation_guard.py --check PATH [--logpath LOGPATH]
  python hover_hash_citation_guard.py --selftest
"""
import json
import re
import sys

HASH_RE = re.compile(r'\b[0-9a-f]{64}\b', re.I)


def real_hashes(log_path):
    """Returns the set of every real, logged hash in the chain -- not just
    the tip -- since a handoff may legitimately quote an EARLIER seq's hash
    (a prior tip, a historical reference), not only the current one."""
    out = set()
    with open(log_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            h = d.get('hash')
            if h:
                out.add(h.lower())
    return out


def check_text(text, known_hashes):
    """Returns (verified, unverified) lists of the 64-hex-char candidates
    found in text, each compared against known_hashes."""
    candidates = sorted(set(m.group(0).lower() for m in HASH_RE.finditer(text)))
    verified = [c for c in candidates if c in known_hashes]
    unverified = [c for c in candidates if c not in known_hashes]
    return verified, unverified


def check_file(path, log_path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    known = real_hashes(log_path)
    return check_text(text, known)


def _selftest():
    ok = 0
    total = 0

    # Fixture log: 2 real entries with known hashes.
    import os
    import tempfile
    fd, log_path = tempfile.mkstemp(suffix='.jsonl')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'seq': 1, 'hash': 'a' * 64}) + '\n')
        f.write(json.dumps({'seq': 2, 'hash': 'b' * 64}) + '\n')

    try:
        total += 1
        verified, unverified = check_text('Tip hash: %s' % ('b' * 64), real_hashes(log_path))
        if verified == ['b' * 64] and not unverified:
            ok += 1
            print('  ok   a genuine, logged hash is VERIFIED, not flagged')
        else:
            print('  FAIL expected verified=[b*64], unverified=[], got %r/%r' % (verified, unverified))

        total += 1
        fabricated = 'c' * 64
        verified, unverified = check_text('Tip hash: %s' % fabricated, real_hashes(log_path))
        if unverified == [fabricated] and not verified:
            ok += 1
            print('  ok   a fabricated, never-logged hash is caught as UNVERIFIED')
        else:
            print('  FAIL expected unverified=[fabricated], got %r/%r' % (verified, unverified))

        total += 1
        # The real seq1082 shape: right prefix, wrong remainder.
        half_real = ('a' * 8) + ('9' * 56)
        verified, unverified = check_text('Tip hash: %s' % half_real, real_hashes(log_path))
        if unverified == [half_real] and not verified:
            ok += 1
            print('  ok   a half-real, half-fabricated hash (the real seq1082 shape) is caught, not waved through on a matching prefix')
        else:
            print('  FAIL expected unverified=[half_real], got %r/%r' % (verified, unverified))

        total += 1
        verified, unverified = check_text('No hash-shaped text here at all.', real_hashes(log_path))
        if not verified and not unverified:
            ok += 1
            print('  ok   text with no 64-hex-char run at all reports clean, not a false alarm')
        else:
            print('  FAIL expected no candidates, got %r/%r' % (verified, unverified))
    finally:
        os.remove(log_path)

    print('%d/%d fixture checks correct' % (ok, total))
    return ok == total


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    if '--check' in argv:
        i = argv.index('--check')
        path = argv[i + 1]
        log_path = None
        if '--logpath' in argv:
            j = argv.index('--logpath')
            log_path = argv[j + 1]
        if log_path is None:
            print('--logpath is required (no default -- never guess which log a draft is being checked against)')
            return 2
        verified, unverified = check_file(path, log_path)
        print('%s -- %d hash-shaped string(s) found, %d verified, %d UNVERIFIED'
              % (path, len(verified) + len(unverified), len(verified), len(unverified)))
        for u in unverified:
            print('  ! UNVERIFIED  %s -- does not match any real logged hash' % u)
        return 1 if unverified else 0
    print('usage: hover_hash_citation_guard.py --selftest | --check PATH --logpath LOGPATH')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
