#!/usr/bin/env python
"""freshness_stamp.py -- one line every report-style hover tool prints so a
reader can SEE the vintage of a list instead of assuming it is current.

Built 2026-09-29 after a real staleness incident that was NOT a tool bug:
the session's hand-compiled routing list (log #722's item-4 grouping) mixed
rows already landed with rows still open by the time it was read, because
it was compiled once and quoted later. Every list-printing tool here
already RE-DERIVES from its live source at print time -- the missing half
was the stamp that lets a reader tell a fresh print from a quoted one.

The stamp carries: the PLATFORM repo's HEAD sha (the thing register/index
claims go stale against), the UTC time of generation, and the sentence
that makes the semantics explicit. stamp() FAILS CLOSED: if HEAD cannot be
read, the stamp says COULD-NOT-STAMP loudly rather than printing nothing
(a report with no stamp would read exactly like a pre-stamp report, which
is the silent-degradation shape discipline 8 warns about).

Selftest covers both directions: the stamp must carry the REAL current
HEAD (positive), and a doctored stamp carrying a wrong sha must FAIL the
verification helper (known-bad) -- so a tool asserting its own stamp via
verify() cannot vacuously pass.
"""
import os
import re
import subprocess
from datetime import datetime, timezone

PLATFORM_REPO = os.path.join(os.path.expanduser('~'), 'Documents', 'SAIRN-hover')

STAMP_RX = re.compile(r'\[freshness\] HEAD ([0-9a-f]{7,40}) @ '
                      r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)')


def head_sha(repo=None):
    try:
        r = subprocess.run(['git', 'rev-parse', '--short=12', 'HEAD'],
                           cwd=repo or PLATFORM_REPO, capture_output=True,
                           text=True, encoding='utf-8')
    except OSError:
        # a nonexistent cwd raises on Windows before git even starts --
        # the same could-not-read outcome as a git failure, not a crash
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def stamp(repo=None):
    """The one line to print directly under a report header."""
    sha = head_sha(repo)
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    if not sha:
        return ('[freshness] COULD-NOT-STAMP: platform HEAD unreadable @ %s '
                '-- treat every row below as of UNKNOWN vintage.' % now)
    return ('[freshness] HEAD %s @ %s -- rows below were derived against '
            'THIS state; anything landed after it is not reflected.'
            % (sha, now))


def verify(stamped_text, repo=None):
    """(True, detail) iff the text carries a stamp whose sha IS the current
    HEAD. Used by fixtures; also usable by a consumer that refuses to act
    on a quoted, stale report."""
    m = STAMP_RX.search(stamped_text)
    if not m:
        return (False, 'no freshness stamp found')
    current = head_sha(repo)
    if current is None:
        return (False, 'current HEAD unreadable -- cannot verify')
    if m.group(1) != current:
        return (False, 'STALE: stamp sha %s != current HEAD %s'
                       % (m.group(1), current))
    return (True, 'stamp matches current HEAD %s' % current)


def _selftest():
    ok = [0]
    bad = [0]

    def ck(name, cond):
        (ok if cond else bad)[0] += 1
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))

    s = stamp()
    ck('stamp() carries the real current HEAD', verify(s)[0] is True)
    doctored = re.sub(r'HEAD [0-9a-f]+', 'HEAD deadbeef4444', s)
    v = verify(doctored)
    ck('KNOWN-BAD: a doctored stamp with a wrong sha FAILS verify(), '
       'naming STALE', v[0] is False and 'STALE' in v[1])
    ck('KNOWN-BAD: text with no stamp at all FAILS verify(), never passes '
       'vacuously', verify('a report with no stamp line')[0] is False)
    ck('an unreadable repo produces a LOUD could-not-stamp line, not '
       'silence', 'COULD-NOT-STAMP' in stamp(repo=os.path.join(
           PLATFORM_REPO, 'no_such_dir_xyz')))
    print('%d ok, %d failed' % (ok[0], bad[0]))
    return bad[0] == 0


if __name__ == '__main__':
    import sys
    sys.exit(0 if _selftest() else 1)
