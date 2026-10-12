"""Duplicate DOM ids across every SAIRN app file. REPORT-ONLY.

`document.getElementById` returns the FIRST element with a duplicated id, so a
duplicate is never cosmetic: one of the two features silently operates on the
other one's element. All three duplicates found by hand on 2026-10-12 were live
defects, not style nits --

  sairnfreedom.html `ac-tbody`   the officer roster and the accounts table
                                 shared a tbody, so whichever renderer ran last
                                 won: the accounts table never rendered, or the
                                 roster was replaced by account rows.
  sairnfreedom.html `ac-name`    sfOpenAccount() read the OFFICER name box, so a
                                 post could not open its ORC 2915.10(C)
                                 exclusive bingo-session account under the name
                                 typed into the account form.
  sairncare.html `fc-name`       saveFacility() stored the family-contact box's
                                 value as the facility's name -- normally empty.

── WHY THIS TOOL EXISTS AT ALL (2026-10-12) ───────────────────────────────────
Guardian Check 8 has said "each HTML id= appears exactly once" since the skill
was written. NOTHING IN tools/ CHECKED IT. All three defects above were found by
an id scan typed inline during one batch and thrown away afterwards, which is
the same "a tool that exists is not a mechanism; a tool that RUNS is" problem
this repo records against its own app-map checker.

── REPORT-ONLY, AND THAT IS A DECISION WITH A REASON ─────────────────────────
This is NOT wired as a push gate and must not be until the platform is clean.
Promoting a checker to blocking while real findings exist refuses every push to
the affected file, which is how a gate gets switched off and then protects
nothing -- the identical reasoning sairn_reachability_check.py carries for
staying report-only with 9 live findings on stonedesk.html. Exit codes still
mean something: 1 on a finding, 2 on COULD NOT RUN, 0 on clean. "Could not run"
is a third state and is never folded into "passed".

── AN HTML PARSER, NOT A REGEX, AND THIS IS NOT A PREFERENCE ─────────────────
`grep -o 'id="[^"]*"'` is wrong on these files in BOTH directions:

  FALSE POSITIVES  every SAIRN app builds its tables by assigning innerHTML
                   from JS template strings, so the source is full of
                   `'<tr><td id="x">'` inside <script>. Those are not markup
                   ids; the browser never has two of them at once unless the JS
                   renders twice, which is a different question. A regex counts
                   them. `html.parser` puts <script> into CDATA mode and never
                   sees them, which is the behaviour wanted.
  FALSE NEGATIVES  an id written with single quotes, with no quotes, or with
                   unusual spacing is still a real id to the browser. A parser
                   gets all of those for free.

The same argument Guardian Check 0a makes for `node --check` per extracted
block rather than `grep -c '<script'`.

── WHAT IT DELIBERATELY DOES NOT DO ──────────────────────────────────────────
It does not look at ids generated at RUNTIME. A template string that renders
`id="row-' + i + '"` inside a loop can produce duplicates in the live DOM that
no static read can see, and this tool says nothing about them -- the same
limitation sairn_reachability_check.py needs `--live` for. It reports what the
MARKUP declares twice, which is the subset that is always wrong.

It also does not judge WHICH of a pair to rename. That needs the call sites, and
it is a judgment call: both sairnfreedom panels legitimately used the `ac-`
prefix, and the fix followed the file's own existing `acct-` convention rather
than a rule.

Usage:
  python tools/dup_dom_ids_check.py                 # every tracked app file
  python tools/dup_dom_ids_check.py a.html b.html    # named files
  python tools/dup_dom_ids_check.py --json
  python tools/dup_dom_ids_check.py --all-tracked    # include archive/ too
"""
import io
import json
import os
import subprocess
import sys
from collections import defaultdict
from html.parser import HTMLParser

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Bumped when the classification changes, so a saved result can be told apart
# from one produced by different criteria. Same convention as the other checkers
# in this directory.
CRITERIA_VERSION = '2026-10-12.1'


class IdScan(HTMLParser):
    """Every id= the MARKUP declares, with its line. Script/style are CDATA."""

    def __init__(self):
        # convert_charrefs=True so `id="a&amp;b"` is recorded as the browser
        # sees it rather than as the source spells it.
        super().__init__(convert_charrefs=True)
        self.hits = defaultdict(list)
        self.errors = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            # Attribute names are lower-cased by the parser, so ID= and Id= are
            # already handled. An EMPTY id is not an id and is skipped rather
            # than counted -- `id=""` on three elements is not three
            # duplicates of anything.
            if k == 'id' and v and v.strip():
                self.hits[v.strip()].append(self.getpos()[0])

    def handle_startendtag(self, tag, attrs):
        # `<input id="x" />` reaches handle_startendtag, NOT handle_starttag, in
        # some documents. Missing this would under-count, which is the silent
        # direction.
        self.handle_starttag(tag, attrs)

    def error(self, message):            # pragma: no cover - py<3.9 ABC
        self.errors.append(message)


def app_files(argv):
    """The files to scan. DERIVED from git, never a hardcoded list.

    The App File Map in sairn-guardian-v2 has been wrong about which apps exist
    SEVEN times, every time because it was a claim about the repo rather than
    something read out of it. This reads `git ls-files` and takes the
    root-level *.html, which is where every app and companion page lives.
    `archive/` is excluded by default -- it is an abandoned branch snapshot, and
    reporting duplicates in dead code would bury the live findings.
    """
    named = [a for a in argv if not a.startswith('-')]
    if named:
        return named, 'named on the command line'
    r = subprocess.run(['git', '-C', REPO, 'ls-files', '*.html'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        return None, 'git ls-files failed: %s' % (r.stderr or '').strip()[:200]
    allh = [p for p in r.stdout.split('\n') if p.strip()]
    if '--all-tracked' in argv:
        return allh, 'every tracked *.html including archive/'
    root = [p for p in allh if '/' not in p]
    return root, 'root-level tracked *.html (archive/ and subdirectories excluded)'


def scan(path):
    """-> (dupes, total_ids, error_or_None). A read failure is NOT zero dupes."""
    full = path if os.path.isabs(path) else os.path.join(REPO, path)
    try:
        src = io.open(full, encoding='utf-8', errors='replace').read()
    except OSError as e:
        return None, None, 'could not read: %s' % e
    p = IdScan()
    try:
        p.feed(src)
        p.close()
    except Exception as e:                                   # noqa: BLE001
        # A parse that blows up is COULD NOT RUN for that file, not a clean
        # one. Returning 0 duplicates here is the silent-pass shape.
        return None, None, '%s: %s' % (type(e).__name__, e)
    dupes = {k: v for k, v in p.hits.items() if len(v) > 1}
    return dupes, len(p.hits), None


def main(argv):
    as_json = '--json' in argv
    files, how = app_files(argv)
    if files is None:
        sys.stderr.write('COULD NOT RUN: %s\n' % how)
        return 2

    rows, unreadable = [], []
    for f in sorted(files):
        dupes, total, err = scan(f)
        if err:
            unreadable.append((f, err))
            continue
        rows.append({'file': f, 'ids': total,
                     'duplicates': {k: v for k, v in sorted(dupes.items())}})

    total_dupes = sum(len(r['duplicates']) for r in rows)
    total_sites = sum(len(v) for r in rows for v in r['duplicates'].values())

    if as_json:
        print(json.dumps({'criteria_version': CRITERIA_VERSION,
                          'how': how, 'files': rows,
                          'unreadable': [{'file': f, 'why': w} for f, w in unreadable],
                          'duplicate_ids': total_dupes,
                          'duplicate_sites': total_sites}, indent=1))
    else:
        print('DUPLICATE DOM IDS -- criteria %s' % CRITERIA_VERSION)
        print('  scope: %s' % how)
        print('  files scanned: %d' % len(rows))
        print()
        print('  %-28s %6s %6s' % ('file', 'ids', 'dupes'))
        for r in rows:
            print('  %-28s %6d %6d' % (r['file'], r['ids'], len(r['duplicates'])))
        print()
        if total_dupes:
            print('%d DUPLICATE ID(S) ACROSS %d SITE(S). Each one means '
                  'getElementById' % (total_dupes, total_sites))
            print('returns the FIRST element and one of the two features is '
                  'operating on the')
            print('other one\'s element. Read the call sites before renaming -- '
                  'which of a')
            print('pair is wrong is a judgment call, and the file\'s own '
                  'existing prefix')
            print('convention is usually the answer.')
            print()
            for r in rows:
                for k, lines in r['duplicates'].items():
                    print('  %s  %-22s lines %s' % (r['file'], k, lines))
        else:
            print('CLEAN -- no id is declared twice in the markup of any file '
                  'scanned.')
            print('This says nothing about ids generated at RUNTIME by a '
                  'template string;')
            print('see this file\'s header for why that is a different question.')
        if unreadable:
            print()
            print('COULD NOT READ %d FILE(S) -- these are NOT counted clean:'
                  % len(unreadable))
            for f, w in unreadable:
                print('  ! %s -- %s' % (f, w))

    if unreadable:
        return 2
    return 1 if total_dupes else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
