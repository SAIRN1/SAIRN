#!/usr/bin/env python
# OWNER: fourth
r"""report_sha_check.py -- is a per-batch report's own SHA line true?

    python tools/report_sha_check.py --check SAIRN-report-ted-b5.txt ...
    python tools/report_sha_check.py --reseat SAIRN-report-ted-b5.txt ...
    python tools/report_sha_check.py --fixtures      # the criteria lock alone
    python tools/report_sha_check.py --check --glob  # every SAIRN-{report,digest}-*

Exit 0 every file checked matches its own SHA line; 1 at least one does not;
2 COULD NOT CHECK -- which is never folded into either of the other two.

── WHY THIS EXISTS ────────────────────────────────────────────────────────────
BUILT BECAUSE IT WAS NAMED AS NOT-DONE AND THEN THE THING IT WOULD HAVE CAUGHT
HAPPENED TWICE IN ONE BATCH. `SAIRN-report-ted-b4.txt` carries its own hash
rule -- line 1 the title, line 2 `SHA256 <hex>`, the body every byte from line 3
to end of file -- and on 2026-10-11 the line said `d2ee6a2d...` while the body
hashed to `2eb5a1ad...`: the SHA was written and then the body kept being
edited. The same batch found `SAIRN-digest-ted-b4.txt` claiming in its own
item-6 line that *"both carry a verifiable body hash"* while having NO SHA LINE
AT ALL. A reader who ran the rule by hand would have concluded somebody had
altered the file.

Both were reseated BY HAND, which is the mechanism that failed, so b4 routed a
`--check` to itself. This is it.

── WHAT IT IS NOT ─────────────────────────────────────────────────────────────
NOT tamper-evidence. A hash a file carries about itself proves only that the
line and the body were written at the same moment; anybody who edits the body
can reseat the line. It catches the ACCIDENT -- an appended section, a late
correction -- and it is the accident that happened. Said here because a check
whose strength is overstated is worse than none: somebody will cite it.

NOT `tools/doc_sha_reseat.py`, and the two have been confused already. That tool
re-seats COMMIT-sha citations inside prose documents after a rebase rewrites
them, and when b4's resume-2 commit was rebased it correctly reported *"NONE of
them is cited in the tracking documents. Nothing to do"* -- true of the
documents it covers and false of the per-batch report, which is not in its
tracked set and cited the pre-rebase hash in five places.

── THE THIRD STATE, WHICH IS MOST OF THE WORK ─────────────────────────────────
A file with no `SHA256` second line is COULD NOT CHECK, exit 2, NOT a pass. That
is the b4 digest's exact shape: nothing to compare, and a tool that returned 0
on it would have confirmed the false claim it was built to find. PR 1.11 -- a
check that cannot run says which file and fails.
"""
import glob as globmod
import hashlib
import io
import os
import re
import sys

CRITERIA_VERSION = '2026-10-12.1'
SHA_RE = re.compile(r'^SHA256\s+([0-9a-f]{64})\s*$')
OK, MISMATCH, CANT = 'OK', 'MISMATCH', 'COULD NOT CHECK'


def split(text):
    """(title, sha_line, body) with the body EXACTLY as the rule defines it.

    `split('\n', 2)` and not `splitlines()`: the body must be every byte from
    line 3 to the end of file, and `splitlines()` then `join` would normalise a
    trailing newline and change the hash of a file nobody edited.
    """
    parts = text.split('\n', 2)
    while len(parts) < 3:
        parts.append('')
    return parts[0], parts[1], parts[2]


def verdict(path):
    """(state, detail, computed, declared). Never raises."""
    try:
        text = io.open(path, encoding='utf-8', newline='').read()
    except OSError as e:
        return CANT, 'unreadable: %s' % e, None, None
    if '\r' in text:
        return (CANT, 'the file contains CR bytes; the rule is LF and UTF-8, so '
                      'a hash taken here would not be the hash the rule names',
                None, None)
    title, sha_line, body = split(text)
    m = SHA_RE.match(sha_line.strip())
    if not m:
        return (CANT, 'line 2 is not `SHA256 <64 hex>` -- it is %r. Nothing to '
                      'compare against, which is NOT a pass'
                % (sha_line[:60]), None, None)
    declared = m.group(1)
    computed = hashlib.sha256(body.encode('utf-8')).hexdigest()
    if computed == declared:
        return OK, 'body matches its own SHA line', computed, declared
    return (MISMATCH, 'the SHA line is stale -- the body was edited after it was '
                      'written', computed, declared)


def reseat(path):
    """Write the true hash into line 2. Returns (state, detail)."""
    st, detail, computed, declared = verdict(path)
    if st == CANT and computed is None and 'line 2 is not' not in detail:
        return CANT, detail
    try:
        text = io.open(path, encoding='utf-8', newline='').read()
    except OSError as e:
        return CANT, 'unreadable: %s' % e
    title, sha_line, body = split(text)
    new = hashlib.sha256(body.encode('utf-8')).hexdigest()
    io.open(path, 'w', encoding='utf-8', newline='').write(
        '\n'.join([title, 'SHA256 ' + new, body]))
    st2, d2, c2, _ = verdict(path)
    if st2 != OK:
        return CANT, 'reseated and it STILL does not verify: %s' % d2
    return OK, 'reseated to %s' % new


def fixtures():
    """The criteria lock. Synthetic files only -- it reads no real report.

    Both directions, because a checker that only ever sees the broken case
    cannot show it is not simply always failing (convention 6).
    """
    import tempfile
    arms = []

    def arm(name, got, want):
        arms.append((name, got == want, got, want))

    d = tempfile.mkdtemp(prefix='reportsha-')

    def write(name, text):
        p = os.path.join(d, name)
        io.open(p, 'w', encoding='utf-8', newline='').write(text)
        return p

    body = 'line three\nline four\n'
    good = write('good.txt', 'TITLE\nSHA256 %s\n%s'
                 % (hashlib.sha256(body.encode()).hexdigest(), body))
    # The body is lines 3..EOF, which includes the newline that ends line 2.
    st, _, c, dec = verdict(good)
    arm('a correctly seated file is OK', st, OK)

    bad = write('bad.txt', 'TITLE\nSHA256 %s\n%s' % ('0' * 64, body))
    st, _, c, dec = verdict(bad)
    arm('a stale SHA line is MISMATCH, not OK', st, MISMATCH)
    arm('...and the computed hash is reported', bool(c and c != dec), True)

    none = write('none.txt', 'TITLE\n\n%s' % body)
    st, _, _, _ = verdict(none)
    arm('NO SHA line is COULD NOT CHECK, never a pass -- the b4 digest shape',
        st, CANT)

    short = write('short.txt', 'TITLE\n')
    arm('a file with no body is COULD NOT CHECK', verdict(short)[0], CANT)

    crlf = os.path.join(d, 'crlf.txt')
    io.open(crlf, 'wb').write(b'TITLE\r\nSHA256 ' + b'0' * 64 + b'\r\nbody\r\n')
    arm('CRLF is COULD NOT CHECK rather than a silent wrong hash',
        verdict(crlf)[0], CANT)

    arm('a missing path is COULD NOT CHECK',
        verdict(os.path.join(d, 'nope.txt'))[0], CANT)

    st, _ = reseat(bad)
    arm('--reseat fixes a MISMATCH', st, OK)
    arm('...and the file then verifies', verdict(bad)[0], OK)
    st, _ = reseat(none)
    arm('--reseat also seats a file that had no SHA line', verdict(none)[0], OK)

    # NEGATIVE HALF: reseating must not be able to "fix" an unreadable file.
    arm('--reseat on a missing path is COULD NOT CHECK, not OK',
        reseat(os.path.join(d, 'nope.txt'))[0], CANT)

    print('report_sha_check --fixtures  criteria %s' % CRITERIA_VERSION)
    bad_arms = [a for a in arms if not a[1]]
    for name, good_, got, want in arms:
        print('  %-4s %s%s' % ('ok' if good_ else 'FAIL', name,
                               '' if good_ else '   got %r want %r' % (got, want)))
    print('\n%d arm(s), %d failed' % (len(arms), len(bad_arms)))
    return 0 if not bad_arms else 1


def main(argv):
    mode = 'check'
    paths = []
    use_glob = False
    for a in argv:
        if a == '--fixtures':
            return fixtures()
        if a == '--check':
            mode = 'check'
        elif a == '--reseat':
            mode = 'reseat'
        elif a == '--glob':
            use_glob = True
        elif a.startswith('-'):
            print('unknown option %r' % a)
            return 2
        else:
            paths.append(a)
    if use_glob:
        for pat in ('SAIRN-report-*.txt', 'SAIRN-digest-*.txt'):
            paths.extend(sorted(globmod.glob(pat)))
    paths = sorted(set(paths))
    if not paths:
        print('COULD NOT CHECK: no files named. Pass paths or --glob.')
        return 2
    print('report_sha_check --%s   criteria %s   %d file(s)'
          % (mode, CRITERIA_VERSION, len(paths)))
    worst = 0
    for p in paths:
        if mode == 'reseat':
            st, detail = reseat(p)
            computed = declared = None
        else:
            st, detail, computed, declared = verdict(p)
        print('  %-15s %-34s %s' % (st, os.path.basename(p), detail))
        if st == MISMATCH:
            print('                    declared %s' % declared)
            print('                    computed %s' % computed)
            worst = max(worst, 1)
        elif st == CANT:
            worst = max(worst, 2)
    print('\nEXIT %d   (0 all match, 1 at least one stale, 2 at least one could '
          'not be checked)' % worst)
    return worst


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
