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

CRITERIA_VERSION = '2026-10-12.2'
SHA_RE = re.compile(r'^SHA256\s+([0-9a-f]{64})\s*$')
SHA_ANY = re.compile(r'^SHA256\s+(\S*)\s*$')
OK, MISMATCH, CANT = 'OK', 'MISMATCH', 'COULD NOT CHECK'
END_MARK = 'END-OF-REPORT'

# ── TWO LAYOUTS, BECAUSE THE PLATFORM USES TWO AND A TOOL THAT KNEW ONE WOULD
#    HAVE REPORTED THE OTHER AS "NO SHA LINE" -- a COULD NOT CHECK on a file
#    that is correctly sealed, which is the fail-shut twin of the fail-open this
#    tool exists to catch. Added the same day the second layout was specified.
#
#   HEAD   line 1 title, line 2 `SHA256 <hex>`, body = lines 3..EOF
#          (b4's report and digest, and b5's digest)
#   TAIL   line 1 title, LAST line `END-OF-REPORT`, SECOND-TO-LAST
#          `SHA256 <hex>`, body = line 2 .. the line before the SHA
#          (b5's report)
#
# The body definition is forced in both: a hash cannot cover the line that
# carries it, so in TAIL the trailing two lines are outside the body and in HEAD
# the leading two are. Said out loud because "the whole file" is the obvious
# wrong answer and would make the rule uncheckable.
HEAD, TAIL = 'head', 'tail'


def strip_final_nl(text):
    """(text_without_one_trailing_newline, had_one).

    FOUND BY USING IT, on the first real TAIL file the tool was pointed at. The
    file ended with a newline -- as every editor and every `write` of a
    line-joined list does -- so `split('\n')` put an EMPTY STRING last and the
    END marker second-to-last. The detector saw neither layout and reported
    COULD NOT CHECK on a correctly written report: the fail-shut direction, on
    the most ordinary input there is. A trailing newline is not a structural
    difference and must not be read as one.
    """
    if text.endswith('\n'):
        return text[:-1], True
    return text, False


def layout(lines):
    """Which layout a file is in, or None. Reads structure, not a filename."""
    if len(lines) >= 3 and lines[-1].strip() == END_MARK \
            and SHA_ANY.match(lines[-2].strip()):
        return TAIL
    if len(lines) >= 2 and SHA_ANY.match(lines[1].strip()):
        return HEAD
    # An END-OF-REPORT with no SHA above it, or a title with nothing under it:
    # structurally a TAIL file that was never sealed. Reported as TAIL so the
    # verdict says "the SHA line is missing" rather than "unknown layout".
    if lines and lines[-1].strip() == END_MARK:
        return TAIL
    return None


def parts(text):
    """(layout, sha_line, body) or (None, None, None)."""
    core, _ = strip_final_nl(text)
    lines = core.split('\n')
    lay = layout(lines)
    if lay == HEAD:
        p = text.split('\n', 2)
        while len(p) < 3:
            p.append('')
        return HEAD, p[1], p[2]
    if lay == TAIL:
        if len(lines) >= 3 and SHA_ANY.match(lines[-2].strip()):
            return TAIL, lines[-2], '\n'.join(lines[1:-2])
        return TAIL, '', '\n'.join(lines[1:-1])
    return None, None, None


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
    lay, sha_line, body = parts(text)
    if lay is None:
        return (CANT, 'neither layout: line 2 is not `SHA256 <hex>` and the last '
                      'line is not %r. Nothing to compare against, which is NOT '
                      'a pass' % END_MARK, None, None)
    m = SHA_RE.match((sha_line or '').strip())
    if not m:
        where = 'line 2' if lay == HEAD else 'the second-to-last line'
        return (CANT, '%s layout, but %s is not `SHA256 <64 hex>` -- it is %r'
                % (lay.upper(), where, (sha_line or '')[:60]), None, None)
    declared = m.group(1)
    computed = hashlib.sha256(body.encode('utf-8')).hexdigest()
    if computed == declared:
        return OK, '%s layout; body matches its own SHA line' % lay.upper(), computed, declared
    return (MISMATCH, '%s layout; the SHA line is stale -- the body was edited '
                      'after it was written' % lay.upper(), computed, declared)


def reseat(path):
    """Write the true hash into whichever line the file's layout puts it on."""
    try:
        text = io.open(path, encoding='utf-8', newline='').read()
    except OSError as e:
        return CANT, 'unreadable: %s' % e
    if '\r' in text:
        return CANT, 'the file contains CR bytes; refusing to seal a hash the rule cannot reproduce'
    core, had_nl = strip_final_nl(text)
    lines = core.split('\n')
    lay = layout(lines)
    if lay is None:
        return CANT, 'neither layout -- nothing to reseat'
    if lay == HEAD:
        p = text.split('\n', 2)
        while len(p) < 3:
            p.append('')
        new = hashlib.sha256(p[2].encode('utf-8')).hexdigest()
        out = '\n'.join([p[0], 'SHA256 ' + new, p[2]])
    else:
        if len(lines) >= 3 and SHA_ANY.match(lines[-2].strip()):
            body = '\n'.join(lines[1:-2])
            new = hashlib.sha256(body.encode('utf-8')).hexdigest()
            out = '\n'.join([lines[0]] + lines[1:-2] + ['SHA256 ' + new, END_MARK])
        else:
            body = '\n'.join(lines[1:-1])
            new = hashlib.sha256(body.encode('utf-8')).hexdigest()
            out = '\n'.join([lines[0]] + lines[1:-1] + ['SHA256 ' + new, END_MARK])
        # The trailing newline is PUT BACK rather than normalised away: a tool
        # that silently changes the last byte of a file it was asked to hash is
        # editing the thing it measures.
        if had_nl:
            out += '\n'
    io.open(path, 'w', encoding='utf-8', newline='').write(out)
    st2, d2, _, _ = verdict(path)
    if st2 != OK:
        return CANT, 'reseated and it STILL does not verify: %s' % d2
    return OK, '%s layout; reseated to %s' % (lay.upper(), new)


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
    # DELIBERATE CHANGE WHEN THE TAIL LAYOUT WAS ADDED, and the arm is kept
    # rather than deleted so the change is visible. Before, `--reseat` would
    # write a SHA into line 2 of ANY file. Once a second layout exists, a file
    # whose line 2 is blank and whose last line is not the END marker is in
    # NEITHER layout -- and writing a hash into line 2 of an unknown document
    # would be a tool editing something it cannot identify. It refuses, and a
    # TAIL file with no SHA line is still sealed (arm below), because there the
    # END marker identifies it.
    st, _ = reseat(none)
    arm('--reseat REFUSES a file in neither layout rather than guessing',
        verdict(none)[0], CANT)

    # NEGATIVE HALF: reseating must not be able to "fix" an unreadable file.
    arm('--reseat on a missing path is COULD NOT CHECK, not OK',
        reseat(os.path.join(d, 'nope.txt'))[0], CANT)

    # ── THE TAIL LAYOUT, both directions ──────────────────────────────────
    tbody = 'first body line\nsecond body line'
    thash = hashlib.sha256(tbody.encode()).hexdigest()
    tgood = write('tail_good.txt',
                  'REPORT ted b5\n%s\nSHA256 %s\n%s' % (tbody, thash, END_MARK))
    arm('a correctly sealed TAIL file is OK', verdict(tgood)[0], OK)
    arm('...and it is recognised AS tail, not as head',
        'TAIL' in verdict(tgood)[1], True)

    tbad = write('tail_bad.txt',
                 'REPORT ted b5\n%s\nSHA256 %s\n%s' % (tbody, '0' * 64, END_MARK))
    arm('a stale TAIL SHA is MISMATCH', verdict(tbad)[0], MISMATCH)
    arm('--reseat fixes a TAIL MISMATCH', reseat(tbad)[0], OK)
    arm('...and the END marker is still the last line',
        io.open(tbad, encoding='utf-8', newline='').read().split('\n')[-1], END_MARK)

    tnone = write('tail_none.txt', 'REPORT ted b5\n%s\n%s' % (tbody, END_MARK))
    arm('a TAIL file with no SHA line is COULD NOT CHECK', verdict(tnone)[0], CANT)
    arm('--reseat seals an unsealed TAIL file', reseat(tnone)[0], OK)
    arm('...and it then verifies', verdict(tnone)[0], OK)

    # THE ONE THAT MATTERS: the body must NOT include the lines carrying the
    # hash, or the rule is uncheckable. Measured rather than asserted in prose.
    sealed = io.open(tnone, encoding='utf-8', newline='').read().split('\n')
    arm('the TAIL body excludes the SHA line and the END marker',
        hashlib.sha256('\n'.join(sealed[1:-2]).encode()).hexdigest(),
        SHA_RE.match(sealed[-2]).group(1))

    # ── A TRAILING NEWLINE IS NOT A LAYOUT. Found by using the tool on the
    # first real TAIL report, which ended with one -- as everything written by
    # a text editor or a line-joined `write` does -- and was reported COULD NOT
    # CHECK. Both directions, and the newline must SURVIVE a reseat.
    tnl = write('tail_nl.txt',
                'REPORT ted b5\n%s\nSHA256 %s\n%s\n' % (tbody, thash, END_MARK))
    arm('a sealed TAIL file WITH a trailing newline is OK', verdict(tnl)[0], OK)
    tnl2 = write('tail_nl2.txt',
                 'REPORT ted b5\n%s\nSHA256 %s\n%s\n' % (tbody, '0' * 64, END_MARK))
    arm('--reseat fixes it', reseat(tnl2)[0], OK)
    arm('...and the trailing newline survives the reseat',
        io.open(tnl2, encoding='utf-8', newline='').read().endswith('\n'), True)
    hnl = write('head_nl.txt', 'TITLE\nSHA256 %s\n%s'
                % (hashlib.sha256(body.encode()).hexdigest(), body))
    arm('the HEAD layout was already newline-safe and still is',
        verdict(hnl)[0], OK)

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
