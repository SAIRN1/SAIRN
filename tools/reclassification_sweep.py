"""Reclassification sweep v2 — now BIDIRECTIONAL.

v1 (2026-08-30) searched only for statutes that DEEM workers employees. It would
have missed Delaware, whose 16 Del. C. 122(3)(o)(2)(A) expressly PERMITS
independent contractors. Delaware was found by reading, not by sweeping.

v2 adds the affirmative-permission forms, and reports which polarity each hit is,
so a state that permits is not silently filed as clean.

v3 (2026-09-22) -- IT HAD NEVER READ THE CORPUS, AND IT SAID ZERO EVERY TIME.
`glob.glob('*.txt')` was unanchored and non-recursive while the captures live
two directories deep. Driven from four places before this was changed, all four
printing `TALLY: {'DEEM': 0, 'ROLE': 0, 'PERMIT': 0}` and refusing nothing:

    repo root                       files: 22   <- app HTML, not statutes
    docs/sources                    files: 0
    docs/sources/sairnsenior        files: 0
    docs/sources/sairnsenior/MD     files: 3    <- one state at a time

A zero in every bucket reads as "no state deems these workers employees" --
the answer a reader most wants, and the one that is expensive to be wrong
about. The v1->v2 note above is corroboration rather than hindsight: Delaware
"was found by reading, not by sweeping", which is what a sweep that reads
nothing looks like from the outside.

SO v3 CHANGES WHAT IT READS AND WHAT IT REFUSES, and those are two fixes:

  * THE CORPUS IS ANCHORED TO THE REPOSITORY and walked recursively, so the
    answer no longer depends on which directory somebody was standing in. A
    path argument still overrides it, because pointing this at a new capture
    is the normal use of a one-off audit tool.
  * EVERY READER FAILS LOUD. Three separate `except: return ''` / `continue`
    branches turned an unreadable document into one containing no match --
    absent pypdf, an encrypted PDF, a malformed .docx, a read error. A
    document that could not be read is a THIRD STATE, is now listed by name,
    and makes the tool exit non-zero. Same decision
    tests/run_cron_liveness_probe.py already made about its own missing
    import: "COULD NOT RUN -- reported, not skipped".
  * AND A SWEEP THAT READ NOTHING PRINTS NO TALLY. Zero files is a refusal.
  * The under-400-byte skip was silent too. A failed download is now named
    rather than dropped, and the swept count is printed beside the tally so
    the denominator is visible rather than implied.

Exit 0  every candidate file was read, and the tally is over all of them
Exit 1  at least one could not be read -- the tally is over the rest, and
        each failure is printed with its reason
Exit 2  COULD NOT RUN: no corpus directory, or nothing in it
"""
import io
import os
import re
import sys
import zipfile

# ── STDOUT CANNOT BE THE THING THAT FAILS (2026-09-22) ──────────────────────
# The first run of v3 -- the first run of this tool that ever READ the corpus --
# died on `UnicodeEncodeError: 'charmap' codec can't encode '�'` two
# findings in, because Windows stdout defaults to cp1252 and the captures carry
# bytes that decoded to U+FFFD. The bug is as old as the file; it simply could
# not fire while the sweep was reading nothing.
#
# IT WOULD HAVE BEEN WORSE THAN A CRASH IF IT HAD BEEN CAUGHT. A sweep that
# swallowed the encode error and moved on would print SOME findings and lose
# others, with an exit code that looked fine -- which is the same fail-open
# this version exists to remove. So the output is reconfigured rather than
# wrapped: replacement characters in a printed excerpt are visible damage, and
# a missing finding is not.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DEEM = [
    r'not\s+independent\s+contractors?',
    r'shall\s+be\s+considered\s+(?:an\s+)?employ',
    r'shall\s+be\s+deemed\s+(?:to\s+be\s+)?(?:an\s+)?employ',
    r'deemed\s+(?:to\s+be\s+)?employees',
    r'considered\s+employees',
    r'shall\s+not\s+be\s+considered\s+(?:an\s+)?independent\s+contractor',
]
ROLE = [
    r'employer\s+of\s+record',
    r'co-?employer',
    r'common\s+law\s+employer',
    r'joint\s+employ',
    r'is\s+the\s+employer\s+of',
    r'managing\s+employer',
]
PERMIT = [
    r'including\s+those\s+contracts\s+with\s+individuals\s+considered\s+to\s+be\s+independent\s+contractors',
    r'(?:may|can)\s+be\s+provided\s+by\s+independent\s+contractors',
    r'(?:employees?\s+(?:of\s+the\s+\w+\s+)?or|or)\s+(?:through\s+)?contract(?:ual)?\s+arrangements?',
    r'employ\s+or\s+contract\s+with',
    r'whether\s+employed\s+or\s+contracted',
    r'employees\s+or\s+independent\s+contractors',
    r'independent\s+contractor\s+(?:status|arrangement)',
]
GROUPS = [('DEEM', DEEM), ('ROLE', ROLE), ('PERMIT', PERMIT)]
RX = [(name, re.compile('|'.join(pats), re.I)) for name, pats in GROUPS]


class Unreadable(Exception):
    """A document that could not be read is a THIRD STATE.

    It is not a document containing no match, and the whole cost of this
    file's first two versions was that those two were the same value. Raised
    rather than returned so that no caller can accidentally go on treating it
    as empty text -- which is what `return ''` made every caller do.
    """


def text_of(path):
    low = path.lower()
    if low.endswith('.txt'):
        try:
            return io.open(path, encoding='utf-8', errors='replace').read()
        except OSError as e:
            raise Unreadable('%s could not be opened: %s' % (path, e))
    if low.endswith('.pdf'):
        # THE MISSING IMPORT IS ITS OWN FAILURE AND IS NAMED SEPARATELY.
        # "pypdf is not installed" is a fixable instruction; "this PDF is
        # encrypted" is a fact about the capture. One message for both sends
        # the next reader to the wrong place.
        try:
            from pypdf import PdfReader
        except ImportError:
            raise Unreadable('%s needs pypdf, which is not installed in this '
                             'clone -- `python -m pip install pypdf`. The '
                             'document was NOT swept.' % path)
        try:
            return '\n'.join((p.extract_text() or '') for p in PdfReader(path).pages)
        except Exception as e:
            raise Unreadable('%s could not be parsed as a PDF (%s: %s)'
                             % (path, type(e).__name__, e))
    if low.endswith('.docx'):
        try:
            x = zipfile.ZipFile(path).read('word/document.xml').decode('utf-8', 'replace')
        except Exception as e:
            raise Unreadable('%s could not be read as a .docx (%s: %s)'
                             % (path, type(e).__name__, e))
        return re.sub(r'<[^>]+>', ' ', x)
    try:
        s = io.open(path, encoding='utf-8', errors='replace').read()
    except OSError as e:
        raise Unreadable('%s could not be opened: %s' % (path, e))
    s = re.sub(r'(?is)<(script|style).*?</\1>', ' ', s)
    return re.sub(r'<[^>]+>', ' ', s)


# ── THE CORPUS IS ANCHORED TO THE REPOSITORY, NOT TO THE CURRENT DIRECTORY ──
# This was `glob.glob('*.txt') + ...` -- unanchored and non-recursive -- while
# the captures sit two directories deep under docs/sources/<app>/<STATE>/. The
# result was a tool that read the wrong files from the repo root and no files
# from anywhere sensible, and printed a zero tally from all of them.
#
# A PATH ARGUMENT STILL OVERRIDES IT, because this is a one-off audit tool and
# pointing it at a newly captured directory is the normal use. What is gone is
# the DEFAULT depending on where somebody happened to be standing.
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(REPO, 'docs', 'sources')
EXTS = ('.txt', '.html', '.pdf', '.docx', '.out')

root = sys.argv[1] if len(sys.argv) > 1 else CORPUS
if not os.path.isdir(root):
    print('COULD NOT RUN: %s is not a directory. Nothing was swept, and a '
          'tally over nothing would read as a clean corpus.' % root)
    sys.exit(2)

files = sorted(
    os.path.join(dp, fn)
    for dp, _dn, fns in os.walk(root)
    for fn in fns
    if fn.lower().endswith(EXTS)
)
print('corpus:', root)
print('files:', len(files))
# ── ZERO FILES IS A REFUSAL, NOT A RESULT ───────────────────────────────────
# The old code printed `TALLY: {'DEEM': 0, 'ROLE': 0, 'PERMIT': 0}` after
# reading nothing, and that line is indistinguishable from a real sweep over a
# real corpus that found nothing. It is the difference between "no state deems
# these workers employees" and "I did not look".
if not files:
    print('COULD NOT RUN: no candidate document under %s. A sweep that read '
          'nothing must not print a tally -- an empty result here reads as "no '
          'state deems these workers employees".' % root)
    sys.exit(2)

tally = {'DEEM': 0, 'ROLE': 0, 'PERMIT': 0}
# EVERY FILE NOT SWEPT IS NAMED. A skipped document is not a document with no
# match, and the count of them is printed beside the tally so the denominator
# is visible rather than implied.
unreadable, too_small = [], []
for f in files:
    rel = os.path.relpath(f, root)
    # A capture this short is a failed download, not a statute -- but it was
    # being dropped in silence, so it is recorded rather than skipped.
    if os.path.getsize(f) < 400:
        too_small.append(rel)
        continue
    try:
        t = re.sub(r'\s+', ' ', text_of(f))
    except Unreadable as e:
        unreadable.append(str(e))
        continue
    if not t.strip():
        unreadable.append('%s read as EMPTY -- a capture with no text in it is '
                          'not a statute with no match' % rel)
        continue
    for name, rx in RX:
        seen = set()
        for m in rx.finditer(t):
            seg = t[max(0, m.start() - 200):m.start() + 260]
            if seg[:45] in seen:
                continue
            seen.add(seg[:45])
            tally[name] += 1
            print('\n[%s] %s :: %s' % (name, rel, m.group(0)[:44]))
            print('   ' + seg)
            if len(seen) >= 2:
                break
swept = len(files) - len(unreadable) - len(too_small)
print('\nTALLY:', tally)
print('swept %d of %d candidate file(s) under %s' % (swept, len(files), root))
if too_small:
    print('\n%d file(s) were UNDER 400 BYTES and were not swept -- a capture '
          'that short is a failed download, not a statute:' % len(too_small))
    for r in too_small:
        print('  ' + r)
if unreadable:
    print('\n%d file(s) COULD NOT BE READ. The tally above is over the OTHER '
          '%d, and is not a statement about these:' % (len(unreadable), swept))
    for m in unreadable:
        print('  ' + m)
    sys.exit(1)
sys.exit(0)
