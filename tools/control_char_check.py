"""No source file may contain a raw C0 control byte. Type the escape instead.

    python tools/control_char_check.py                   # whole tree, exit 1 on a hit
    python tools/control_char_check.py --quiet            # exit code only
    python tools/control_char_check.py <paths...>         # as the WORKING TREE holds them
    python tools/control_char_check.py --rev <REV> <paths...>
                                       # as REVISION REV holds them -- what a
                                       # push actually ships. See scan_at_rev().

Exit 0 clean, 1 a finding, 2 COULD NOT RUN -- a file that could not be read is
the third state and is never folded into either of the other two.

WHY THIS EXISTS. On 2026-09-10 a sweep for control bytes across all 1,624
tracked files found FOUR, in three source files, and two of them were dead code
paths nobody could see:

  api/sd-data.js:509                   a raw NUL as a composite-key separator
  api/_lib/roofing-crew-capacity.js    the same, twice -- one of them in a COMMENT
  tests/stonedesk_server_backup.js:310 /grant[^;]*<BS>delete<BS>/i
  tools/sairn_ai_fact_scan.py:136      "...|<p<BS>|<b>|..."

Every one is the same mistake: **an escape sequence typed as its literal
control character.** `\\b` became a backspace byte, `\\x00` became a NUL byte.

THE TWO REGEXES WERE DEAD AND PROVEN DEAD WITH REAL INPUT.
`/grant[^;]*<BS>delete<BS>/i` is the assertion *"the schema still grants no
delete privilege"* -- a real privilege guard. Given
`grant select, insert, update, delete on public.sd_stuff to service_role;` it
returns **false**, because nothing matches a backspace, so the assertion passed
on the exact grant it exists to refuse. (The guarded schema is in fact clean --
so it hid no live defect, only the ability to notice one.) The fact-scan case
was the alternative `<p`, which never matched a `<p>` markup line.

AND THE NUL MAKES THE FILE UNSEARCHABLE, which is why it survived. `grep` and
`ripgrep` answer `Binary file api/sd-data.js matches` and print NO LINES -- on
the central API handler serving every app. Measured before and after: the same
`grep -c DNT_RESOURCES` went from that message to `8`. **A content search that
returns nothing looks like "no matches", not like "your tool gave up"**, which
is this platform's signature failure shape applied to its own tooling.

ONE THING THIS CHECK IS *NOT* ABOUT, stated because the first draft of the
finding got it wrong: `git diff` was FINE. `.gitattributes` marks the repo
`text`, which overrides git's binary auto-detection, so diffs were readable the
whole time. Verified by making a one-byte edit and reading the diff. Only the
grep tools were affected.

WHAT IT ALLOWS. Tab, newline, carriage return. Nothing else below 0x20, and not
0x7f. A file that genuinely needs a control byte in its DATA should carry the
escape in its SOURCE -- the runtime string is identical, which is the whole
point: all four fixes above are byte-for-byte no-ops at run time.

BINARY FILES ARE SKIPPED BY EXTENSION AND THE SKIP IS PRINTED, never silent --
a category quietly dropped is how a real file hides, the same argument
`report_only_checks.py` makes for its own exclusions.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Bytes that are legitimate in a text source. Everything else below 0x20, plus
# DEL, is a hit.
ALLOWED = {9, 10, 13}
BAD = (set(range(0x00, 0x20)) - ALLOWED) | {0x7f}

BINARY_EXT = (
    '.zip', '.gz', '.tgz', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp',
    '.pdf', '.woff', '.woff2', '.ttf', '.otf', '.eot', '.mp4', '.mp3', '.wav',
    '.xlsx', '.docx', '.pptx', '.exe', '.dll', '.so', '.dylib', '.pyc',
)

NAMES = {
    0x00: 'NUL (write \\x00)',
    0x07: 'BEL (write \\a)',
    0x08: 'BACKSPACE -- almost always a \\b word boundary typed literally',
    0x0b: 'VTAB (write \\v)',
    0x0c: 'FORMFEED (write \\f)',
    0x1b: 'ESC (write \\x1b)',
    0x7f: 'DEL (write \\x7f)',
}


# ── `git ls-files` QUOTES A PATH IT CANNOT PRINT PLAINLY, AND THAT HID ONE ──
# Found 2026-10-05 by the could-not-read disclosure below, on its first run.
# This repo tracks
#   archive/branch-lucid-ptolemy-b73vu0/SAIRNlaw \342\200\224 A Partnership Proposal ... .pdf
# and plain `git ls-files` prints it WRAPPED IN DOUBLE QUOTES with the non-ASCII
# bytes as C escapes. The old reader took that line literally, so every scan
# since 2026-09-10 looked for a file whose name begins with a quote character,
# failed to find it, and skipped it IN SILENCE while still counting it in
# `files scanned`. It is a PDF and would have been skipped as binary anyway --
# the defect is that the skip was invisible and the count was wrong, so the next
# such path (a .js with an em-dash in the name) would have been unscanned and
# reported as scanned.
#
# `-z` is the fix rather than an unquoting parser: git emits the raw bytes with
# NUL separators and does no quoting at all, so there is nothing to parse and
# nothing to get wrong. Writing the unquoter is how this class recurs.
def tracked():
    out = subprocess.run(['git', 'ls-files', '-z'], cwd=REPO,
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace').stdout
    return [f for f in out.split('\0') if f.strip()]


def scan_bytes(data):
    """Every (line, offset, byte) hit in one blob of bytes."""
    if not (set(data) & BAD):
        return []
    hits, line = [], 1
    for off, b in enumerate(data):
        if b == 0x0a:
            line += 1
        elif b in BAD:
            hits.append((line, off, b))
    return hits


def scan(path):
    """Every (line, offset, byte) hit in one file, AS THE WORKING TREE HOLDS IT."""
    with io.open(os.path.join(REPO, path), 'rb') as fh:
        return scan_bytes(fh.read())


# ── THE WORKING TREE IS NOT WHAT THE PUSH SHIPS (2026-10-05) ───────────────
# Push-gate check 11 derives its file list from the OUTGOING COMMIT RANGE and
# then hands the checker WORKING-TREE PATHS, so it answers about bytes that are
# not the bytes being pushed. REPRODUCED in a throwaway repo before this was
# written, and the gate's own words came out of it:
#
#   1. commit a file containing  PAT = r'grant[^;]*<BS>delete<BS>'
#   2. fix the WORKING TREE only, do not commit
#   3. `control_char_check.py <path>`  ->  "CLEAN -- no raw control bytes",
#                                          exit 0
#   4. `git show HEAD:guard.py`        ->  two raw 0x08 bytes, still outgoing
#
# So the one gate whose entire subject is a byte in a committed blob was
# reading a file somebody had already repaired, and would have passed the push
# that shipped the defect. It is the same proxy-for-the-real-subject shape this
# register records over and over; here the proxy and the subject are one `git
# show` apart.
#
# A READ FAILURE IS EXIT 2, NEVER A SKIP. `git show REV:path` failing means the
# path does not exist at that revision or the revision is unreadable, and
# neither is "no control bytes". The old file-argument branch did
# `if not os.path.exists(...): continue` -- silently -- while still counting
# that file in `files scanned`, so the printed number was a claim about files
# nobody opened (PR 1.11).
def scan_at_rev(rev, path):
    """Hits in `path` AS REVISION `rev` HOLDS IT. Raises on an unreadable blob."""
    r = subprocess.run(['git', 'show', '%s:%s' % (rev, path)],
                       cwd=REPO, capture_output=True)
    if r.returncode != 0:
        raise IOError((r.stderr or b'').decode('utf-8', 'replace').strip()
                      or 'git show %s:%s failed' % (rev, path))
    return scan_bytes(r.stdout)


def main(argv):
    quiet = '--quiet' in argv
    # FILE ARGUMENTS, ADDED 2026-09-13 FOR THE PUSH GATE. Scoping matters here:
    # the whole-tree scan is the right question for a sweep and the wrong one
    # for a gate. A standing finding anywhere would otherwise refuse EVERY push
    # -- which is the state check 5 has been stuck in since 2026-09-01 -- so the
    # gate passes the files that push actually ships and a finding blocks the
    # push that carries it, not somebody else's.
    #
    # Paths may be absolute or repo-relative; they are reported repo-relative
    # either way so the message reads the same from a hook and from a terminal.
    # --rev REV / --rev=REV: read every named path AS THAT REVISION HOLDS IT
    # rather than as the working tree holds it. See scan_at_rev() for the
    # reproduction. Only meaningful with file arguments: a whole-tree sweep at
    # a revision is a different tool and is not pretended to here.
    rev = None
    for i, a in enumerate(argv):
        if a == '--rev' and i + 1 < len(argv):
            rev = argv[i + 1]
        elif a.startswith('--rev='):
            rev = a.split('=', 1)[1]
    given = [a for a in argv
             if not a.startswith('--') and a != rev]
    if rev and not given:
        print('COULD NOT RUN: --rev names a revision and no file was given. '
              'A whole-tree\nscan at a revision is not what this flag does, '
              'and scanning the working tree\ninstead would answer a '
              'different question under the flag that asked not to.\n'
              'Exit 2, not a pass.')
        return 2
    if given:
        files = []
        for a in given:
            p = os.path.abspath(a)
            try:
                rel = os.path.relpath(p, REPO).replace('\\', '/')
            except ValueError:
                rel = a.replace('\\', '/')
            files.append(rel)
        skipped, findings = [], []
    else:
        files = tracked()
        skipped, findings = [], []
        # ── A ZERO-ITEM CORPUS IS NOT A CLEAN SWEEP (PR 1.11) ──────────────
        # Guarded in the else only: the branch above scans the files a caller
        # NAMED, and naming none is the caller's business. This branch is the
        # whole-repo sweep, and an empty one means `git ls-files` returned
        # nothing -- which would print "tracked files scanned : 0" and then
        # clean. Added 2026-09-29 after parse_zero_third_state_check named it.
        if not files:
            print('COULD NOT RUN: `git ls-files` returned no tracked file. '
                  'Zero files scanned\nis not zero control characters found. '
                  'Exit 2, not a pass.')
            return 2
    unreadable = []
    for f in files:
        if f.lower().endswith(BINARY_EXT):
            skipped.append(f)
            continue
        try:
            hits = scan_at_rev(rev, f) if rev else scan(f)
        except (IOError, OSError) as e:
            # ── A FILE NOBODY OPENED IS NOT A FILE WITH NO CONTROL BYTES ───
            # This was `continue`, silently, while `files scanned` still
            # counted the file -- so the printed number was a claim about
            # bytes nobody read, and the gate's own count guard compared
            # against it and agreed. Exit 2, named, every time (PR 1.11).
            unreadable.append((f, str(e)))
            continue
        for line, off, b in hits:
            findings.append((f, line, off, b))

    if not quiet:
        print('control character check')
        if rev:
            print('  source                : revision %s, NOT the working tree'
                  % rev)
        # NAMED BY WHERE THE LIST CAME FROM. `files given` is the count the
        # push gate compares against its own argument list, and printing it
        # for the whole-tree sweep -- where nobody gave anything -- would make
        # the gate's guard compare two unrelated numbers.
        if given:
            print('  files given           : %d' % len(files))
        print('  tracked files scanned : %d'
              % (len(files) - len(skipped) - len(unreadable)))
        if skipped:
            print('  skipped as binary (%d, NOT silently): %s'
                  % (len(skipped), ', '.join(sorted(skipped))[:160]))
        if unreadable:
            print('\nCOULD NOT READ %d FILE(S) -- this is NOT a pass:'
                  % len(unreadable))
            for f, why in unreadable:
                print('  ? %s -- %s' % (f, why[:140]))
        if findings:
            print('\n%d FINDING(S):' % len(findings))
            for f, line, off, b in findings:
                print('  - %s:%d (byte offset %d) contains 0x%02x -- %s'
                      % (f, line, off, b, NAMES.get(b, 'a raw control byte')))
            print('\nReplace the raw byte with its ESCAPE SEQUENCE. The runtime '
                  'string is identical; what changes is that the file becomes '
                  'searchable and the intent becomes visible to a reader. Check '
                  'first whether the byte is in a REGEX -- a literal backspace '
                  'where \\b was meant is a pattern that can never match, and '
                  'two of those were found on 2026-09-10, one of them guarding '
                  'a database privilege.')
        elif not unreadable:
            print('  CLEAN -- no raw control bytes in any tracked text file.')
    # ORDER MATTERS AND IS DELIBERATE: a FINDING outranks a could-not-read,
    # because a known bad byte is actionable now and the unread file is still
    # named in the output above. With no finding, an unread file is exit 2 --
    # the third state -- and never 0.
    if findings:
        return 1
    return 2 if unreadable else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
