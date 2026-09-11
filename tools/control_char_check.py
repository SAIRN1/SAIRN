"""No source file may contain a raw C0 control byte. Type the escape instead.

    python tools/control_char_check.py           # report, exit 1 on a hit
    python tools/control_char_check.py --quiet   # exit code only

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


def tracked():
    out = subprocess.run(['git', 'ls-files'], cwd=REPO,
                         capture_output=True, text=True).stdout
    return [f for f in out.split('\n') if f.strip()]


def scan(path):
    """Every (line, offset, byte) hit in one file."""
    with io.open(os.path.join(REPO, path), 'rb') as fh:
        data = fh.read()
    if not (set(data) & BAD):
        return []
    hits, line = [], 1
    for off, b in enumerate(data):
        if b == 0x0a:
            line += 1
        elif b in BAD:
            hits.append((line, off, b))
    return hits


def main(argv):
    quiet = '--quiet' in argv
    files, skipped, findings = tracked(), [], []
    for f in files:
        if f.lower().endswith(BINARY_EXT):
            skipped.append(f)
            continue
        if not os.path.exists(os.path.join(REPO, f)):
            continue
        for line, off, b in scan(f):
            findings.append((f, line, off, b))

    if not quiet:
        print('control character check')
        print('  tracked files scanned : %d' % (len(files) - len(skipped)))
        if skipped:
            print('  skipped as binary (%d, NOT silently): %s'
                  % (len(skipped), ', '.join(sorted(skipped))[:160]))
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
        else:
            print('  CLEAN -- no raw control bytes in any tracked text file.')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
