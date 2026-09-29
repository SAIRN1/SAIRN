#!/usr/bin/env python
r"""hover_duplicate_finding_check.py -- before logging a new finding, check
whether the SAME underlying defect is already tracked under a different
citation or commit hash.

    python hover_duplicate_finding_check.py --terms "law_check_and_insert_disbursement,CLEARANCE_NOT_STORED,already exists"
    python hover_duplicate_finding_check.py --terms "..." --json
    python hover_duplicate_finding_check.py --self-check

Exit 0 clean (no likely duplicate), 1 likely duplicate(s) found, 2 COULD NOT
RUN (a source file could not be read -- never silently reports "no
duplicates" when it could not actually check).

-- WHY THIS EXISTS --------------------------------------------------------
Two real near-misses in one night. (1) This role logged the law_trusttx
disbursement-message finding (hover_log #380) as though it were newly
discovered, then had to append a correction (#382) once told to check
docs/SAIRN-OPEN-WORK-INDEX.md -- the SAME defect (v_existing_found discarded,
CLEARANCE_NOT_STORED, "already exists") was already tracked there, fully
spec'd, as row 65, under commit 0498732c rather than the hover_log entry's
own framing. (2) 5a878e7181 and 0b1e017f3f are the SAME underlying gap (no
committed sabotage artifact for api/sd-data-cross-tenant-dispatchers.test.js)
cited under two different commit hashes -- the feature commit and the review
commit that found the gap in it.

"Was this exact commit already reviewed" (hover_coverage_ledger.py's job) is
a DIFFERENT, narrower question than "is this same root cause already
tracked" -- a defect can be re-derived from a completely different commit,
a different fixture, a different author, and still be the identical thing
someone already wrote up. This checks the second question.

-- WHAT COUNTS AS A MATCH, AND WHY TWO TERMS NOT ONE ----------------------
A single shared term (a resource name like "law_trusttx", an app name) is
NOT enough to flag a duplicate -- those appear in dozens of unrelated rows
and a one-term match would be pure noise, drowning the real signal exactly
the way a resource-name-only search would. This requires AT LEAST TWO of
the caller's supplied terms to appear (case-insensitive substring) in the
SAME row/record before it counts as a candidate. Two independent, more
distinctive terms together (a function name AND an error code, or a function
name AND a quoted phrase) is a real signal a resource name alone is not --
the caller should supply a mix of distinctive terms (function names, error
codes, exact message fragments, file paths) rather than only resource/app
names, and is told so if fewer than 2 terms are given at all.

-- WHAT IT CANNOT DO, STATED RATHER THAN IMPLIED ---------------------------
This is substring matching over the SAME text this platform's own registers
already carry -- it cannot paraphrase, cannot understand that two
differently-worded descriptions are "the same idea" if they share no
distinctive term, and a false negative (a real duplicate using none of the
terms supplied) is possible and not detected. It is a real check that
reduces the two documented near-misses to a two-second command, not a
substitute for actually reading a candidate match before deciding.
"""

import argparse
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
# This tool lives OUTSIDE the platform repo (hover-audit-log, sibling to
# memory/), same placement discipline as every other hover-audit-log tool --
# it needs an explicit, checked path to the platform clone, not a guess from
# its own location.
_KNOWN_CLONES = [
    r'C:\Users\marsh\Documents\SAIRN-hover',
    r'C:\Users\marsh\Documents\SAIRN-hover2',
]

EXIT_CLEAN, EXIT_FOUND, EXIT_COULD_NOT_RUN = 0, 1, 2

MIN_TERM_MATCHES = 2


class CouldNotTell(Exception):
    pass


def find_repo(explicit):
    if explicit:
        if os.path.isdir(explicit):
            return explicit
        raise CouldNotTell('--repo %r is not a directory' % explicit)
    env = os.environ.get('HOVER_LEDGER_REPO')
    if env and os.path.isdir(env):
        return env
    for c in _KNOWN_CLONES:
        if os.path.isdir(c):
            return c
    raise CouldNotTell('no readable platform clone found (checked --repo, '
                        '$HOVER_LEDGER_REPO, and %s)' % ', '.join(_KNOWN_CLONES))


def read_text(path):
    try:
        return io.open(path, encoding='utf-8').read()
    except OSError as e:
        raise CouldNotTell('could not read %s: %s' % (path, e))


# ---------------------------------------------------------------------------
# SAIRN-OPEN-WORK-INDEX.md: a markdown table, one row per real line (rows are
# NOT wrapped -- each `| App | Item | ... |` is a single, often very long,
# line). Split on the FIRST 6 top-level `|` boundaries to get the App/Item/
# Status/Owner/Blocked/Next-action columns; everything after the 6th belongs
# to the free-text body column, which is where the real defect description
# lives and where terms are most likely to match.
_TABLE_ROW = re.compile(r'^\|.*\|\s*$')
_SEPARATOR_ROW = re.compile(r'^\|[\s\-:|]+\|\s*$')


def index_rows(text):
    """[(line_no, full_row_text)] for every real table row in
    SAIRN-OPEN-WORK-INDEX.md, skipping header/separator rows. Both real
    tables in the file are walked -- there is no section boundary reliable
    enough to trust, and a duplicate could sit in either."""
    out = []
    for i, line in enumerate(text.split('\n'), 1):
        s = line.strip()
        if not _TABLE_ROW.match(s):
            continue
        if _SEPARATOR_ROW.match(s):
            continue
        if re.match(r'^\|\s*App\s*\|', s):
            continue
        out.append((i, s))
    return out


# ---------------------------------------------------------------------------
# docs/tier-a-reviews.json: structured records. Search the concatenation of
# every free-text-bearing field a reader would actually recognise the defect
# from -- `what` and `verdict` carry the real prose; `resources`/`files` are
# included too since a function name sometimes only appears in a file path.
def review_records(text):
    try:
        data = json.loads(text)
    except ValueError as e:
        raise CouldNotTell('docs/tier-a-reviews.json is not valid JSON: %s' % e)
    if not isinstance(data, dict) or not isinstance(data.get('records'), list):
        raise CouldNotTell('docs/tier-a-reviews.json has no `records` list')
    out = []
    for idx, r in enumerate(data['records']):
        if not isinstance(r, dict):
            continue
        parts = [
            str(r.get('what') or ''),
            str(r.get('verdict') or ''),
            ' '.join(r.get('resources') or []),
            ' '.join(r.get('files') or []),
        ]
        out.append((idx, r, '\n'.join(parts)))
    return out


def term_hits(terms, haystack):
    hay = haystack.lower()
    return [t for t in terms if t.lower() in hay]


def snippet(text, terms, width=220):
    """A short window around the FIRST matching term, so a human can judge
    the candidate without opening the source file."""
    low = text.lower()
    pos = -1
    for t in terms:
        p = low.find(t.lower())
        if p != -1:
            pos = p
            break
    if pos == -1:
        return text[:width]
    start = max(0, pos - 40)
    return ('...' if start > 0 else '') + text[start:start + width].replace('\n', ' ') + '...'


def scan(repo, terms):
    if len(terms) < MIN_TERM_MATCHES:
        raise CouldNotTell(
            '%d term(s) supplied -- at least %d are required. A single term '
            '(often a resource or app name) matches too many unrelated rows '
            'to mean anything; supply a mix of distinctive terms (function '
            'names, error codes, exact message fragments, file paths).'
            % (len(terms), MIN_TERM_MATCHES))

    index_path = os.path.join(repo, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')
    reviews_path = os.path.join(repo, 'docs', 'tier-a-reviews.json')

    index_text = read_text(index_path)
    reviews_text = read_text(reviews_path)

    findings = []

    for line_no, row in index_rows(index_text):
        hits = term_hits(terms, row)
        if len(hits) >= MIN_TERM_MATCHES:
            findings.append({
                'source': 'SAIRN-OPEN-WORK-INDEX.md', 'line': line_no,
                'terms_matched': hits, 'match_count': len(hits),
                'snippet': snippet(row, hits),
            })

    for idx, record, haystack in review_records(reviews_text):
        hits = term_hits(terms, haystack)
        if len(hits) >= MIN_TERM_MATCHES:
            findings.append({
                'source': 'tier-a-reviews.json', 'record_index': idx,
                'author_session': record.get('author_session'),
                'reviewer_session': record.get('reviewer_session'),
                'status': record.get('status'),
                'resources': record.get('resources'),
                'terms_matched': hits, 'match_count': len(hits),
                'snippet': snippet(haystack, hits),
            })

    findings.sort(key=lambda f: -f['match_count'])
    return findings


# ---------------------------------------------------------------------------
def print_report(terms, findings):
    print('HOVER DUPLICATE-FINDING CHECK -- %d term(s): %s'
          % (len(terms), ', '.join(terms)))
    print('A match requires >= %d of the supplied terms in the SAME row/record.'
          % MIN_TERM_MATCHES)
    if not findings:
        print('\nNo candidate duplicate found. This does NOT prove the finding is '
              'new -- only that none of the supplied terms co-occur in the two '
              'files checked. A real duplicate using different words would not '
              'be caught; read the candidate context yourself before trusting a '
              'clean result on a high-stakes finding.')
        return
    print('\n%d CANDIDATE DUPLICATE(S) -- READ BEFORE LOGGING AS NEW:\n' % len(findings))
    for f in findings:
        if f['source'] == 'SAIRN-OPEN-WORK-INDEX.md':
            print('  [%d/%d terms] %s:%d' % (
                f['match_count'], len(terms), f['source'], f['line']))
        else:
            print('  [%d/%d terms] %s record #%d (status=%s, author=%s, reviewer=%s, resources=%s)' % (
                f['match_count'], len(terms), f['source'], f['record_index'],
                f['status'], f['author_session'], f['reviewer_session'], f['resources']))
        print('    matched: %s' % ', '.join(f['terms_matched']))
        print('    context: %s' % f['snippet'])
        print()


def self_check():
    """Fixtures, not the real repo -- locks this tool's own classification
    logic against synthetic input before it is ever pointed at real docs,
    same blind-lock discipline every other checker in this directory uses."""
    ok = True

    idx_fixture = (
        '| App | Item | Status | Owner | Blocked by | Next action | Sz |\n'
        '|---|---|---|---|---|---|---|\n'
        '| SAIRNfixture | fixture_func() raises FIXTURE_CODE when the widget is '
        'already exists | OPEN | unassigned | -- | -- | S |\n'
        '| SAIRNfixture | unrelated row about a completely different topic | OPEN | -- | -- | -- | S |\n'
    )
    reviews_fixture = json.dumps({'records': [
        {'author_session': 'a', 'reviewer_session': 'b', 'status': 'reviewed',
         'resources': ['fx_widget'], 'files': [],
         'what': 'fixture_func() has no guard for the fixture_widget case',
         'verdict': 'Confirmed: fixture_func() raises FIXTURE_CODE incorrectly.'},
        {'author_session': 'c', 'reviewer_session': None, 'status': 'open',
         'resources': ['fx_other'], 'files': [],
         'what': 'a totally unrelated finding about fx_other',
         'verdict': None},
    ]})

    import tempfile
    tmpdir = tempfile.mkdtemp(prefix='hover_dup_check_selftest_')
    docs = os.path.join(tmpdir, 'docs')
    os.makedirs(docs)
    io.open(os.path.join(docs, 'SAIRN-OPEN-WORK-INDEX.md'), 'w', encoding='utf-8').write(idx_fixture)
    io.open(os.path.join(docs, 'tier-a-reviews.json'), 'w', encoding='utf-8').write(reviews_fixture)

    def ck(label, cond):
        print(('  ok   ' if cond else '  FAIL ') + label)
        return cond

    # 2-term match hits both the INDEX row and the reviews record.
    r = scan(tmpdir, ['fixture_func', 'FIXTURE_CODE'])
    ok = ck('2 distinctive terms find BOTH the index row and the review record',
            len(r) == 2) and ok
    ok = ck('the index-row match cites the right line',
            any(f['source'] == 'SAIRN-OPEN-WORK-INDEX.md' and f['line'] == 3 for f in r)) and ok
    ok = ck('the reviews-json match cites record #0',
            any(f['source'] == 'tier-a-reviews.json' and f['record_index'] == 0 for f in r)) and ok

    # A single term must NOT be enough on its own (the whole point of the
    # MIN_TERM_MATCHES floor) -- confirmed by driving a genuinely single-term
    # search and requiring it to raise, not merely trusting the constant.
    raised = False
    try:
        scan(tmpdir, ['fixture_func'])
    except CouldNotTell:
        raised = True
    ok = ck('a single term is refused (CouldNotTell), not silently searched', raised) and ok

    # A term appearing in only ONE row, paired with a term appearing
    # elsewhere, must not falsely co-occur.
    r2 = scan(tmpdir, ['fixture_func', 'fx_other'])
    ok = ck('two terms that do NOT co-occur in the same row/record find nothing',
            len(r2) == 0) and ok

    # Unreadable source file fails closed (COULD NOT RUN), never a silent
    # "no duplicates".
    bad_repo = os.path.join(tmpdir, 'nope')
    os.makedirs(os.path.join(bad_repo, 'docs'))
    raised2 = False
    try:
        scan(bad_repo, ['fixture_func', 'FIXTURE_CODE'])
    except CouldNotTell:
        raised2 = True
    ok = ck('an unreadable docs file raises CouldNotTell rather than reporting clean',
            raised2) and ok

    print('\n' + ('ALL FIXTURE CHECKS PASS' if ok else 'FIXTURE CHECKS FAILED'))
    return ok


def _make_stdio_utf8_safe():
    """Found live, not by inspection: printing a real matched snippet
    containing a Unicode arrow (U+2192, from an existing platform doc)
    crashed this tool outright with UnicodeEncodeError on Windows, because
    the console's default codepage (cp1252) cannot encode it -- the same
    class of bug found and fixed in three other hover tools tonight
    (subprocess-side rather than stdout-side there). A crash mid-check is
    the worst possible failure mode for a DUPLICATE-FINDING check
    specifically: the caller is left with no verdict at all, not even a
    could-not-tell, right before logging a finding. Reconfigure stdout/
    stderr to UTF-8 with errors='replace' -- never drops output silently
    (a replaced character is visibly different, not invisible), never
    crashes the process over a printable character existing in real
    platform content."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass  # older Python / already-wrapped stream -- best-effort only


def main(argv):
    _make_stdio_utf8_safe()
    p = argparse.ArgumentParser()
    p.add_argument('--terms', default=None,
                    help='comma-separated distinctive terms (function names, '
                         'error codes, exact phrases) describing the finding')
    p.add_argument('--repo', default=None)
    p.add_argument('--json', action='store_true')
    p.add_argument('--self-check', action='store_true')
    args = p.parse_args(argv)

    if args.self_check:
        return EXIT_CLEAN if self_check() else EXIT_FOUND

    if not args.terms:
        print('missing --terms (comma-separated)', file=sys.stderr)
        return EXIT_COULD_NOT_RUN

    terms = [t.strip() for t in args.terms.split(',') if t.strip()]

    try:
        repo = find_repo(args.repo)
        findings = scan(repo, terms)
    except CouldNotTell as e:
        print('COULD NOT RUN: %s' % e, file=sys.stderr)
        return EXIT_COULD_NOT_RUN

    if args.json:
        print(json.dumps({'terms': terms, 'findings': findings}, indent=2))
    else:
        print_report(terms, findings)

    return EXIT_FOUND if findings else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
