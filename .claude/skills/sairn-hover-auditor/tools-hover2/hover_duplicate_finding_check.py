#!/usr/bin/env python
"""hover_duplicate_finding_check.py (hover2's own independent build) --
before logging a finding as new, check whether the same underlying defect
is already tracked under different framing/commit/author. A different,
narrower question than the coverage ledger's "was this exact commit already
reviewed": this is "has ANY record, anywhere, already described this same
defect."

Built from the CONTRACT in hover-interface-specs-2026-09-22.md #4, not from
hover1's source. Reads ALL THREE of the platform's real shared registers --
named explicitly in the contract because hover1's own build only reads two
of them (never docs/defect-density-register.json, arguably the single most
important one to check, since it is where an ALREADY-FIXED defect lives --
the exact case where re-logging as new would be most embarrassing and most
wasteful). That gap is not repeated here.

  1. docs/SAIRN-OPEN-WORK-INDEX.md  -- free-text markdown table, one row per item
  2. docs/tier-a-reviews.json       -- structured JSON, Tier A review obligations
  3. docs/defect-density-register.json -- structured JSON, landed defects

CALL CONTRACT: caller supplies >= 2 terms (function names, error codes,
exact quoted fragments, file paths -- NOT a bare resource/app name alone,
which recurs across dozens of unrelated rows and would be pure noise). A
candidate duplicate requires AT LEAST 2 of the supplied terms to co-occur,
case-insensitive substring match, WITHIN THE SAME row/record. A single
shared term is never sufficient by itself.

Exit 0  clean, no candidate found
Exit 1  candidate(s) found -- printed with source + location, for the
        caller to read before deciding; this tool never decides FOR the
        caller, only narrows what needs reading
Exit 2  COULD NOT RUN -- a source file was unreadable; NEVER silently
        reports "clean" when a source could not actually be checked

WHAT THIS DOES NOT DO, stated rather than implied: pure substring matching
over existing text. It cannot paraphrase and cannot recognise that two
differently-worded write-ups describe the same root cause if they share no
distinctive term. A false negative (a real duplicate in different words) is
possible and undetected. This reduces a real, previously-costly mistake to a
two-second check; it does not replace reading a candidate match before
deciding.

Run:
  python hover_duplicate_finding_check.py "term one" "term two" [more terms...]
  python hover_duplicate_finding_check.py --repo <path> "term" "term"
  python hover_duplicate_finding_check.py --selftest
"""
import io
import json
import os
import re
import sys

REPO_CANDIDATES = (
    'C:/Users/marsh/Documents/SAIRN-hover2',
    'C:/Users/marsh/Documents/SAIRN-hover',
)

REGISTER_RELPATHS = (
    ('open-work-index', 'docs/SAIRN-OPEN-WORK-INDEX.md'),
    ('tier-a-reviews', 'docs/tier-a-reviews.json'),
    ('defect-density-register', 'docs/defect-density-register.json'),
)


def discover_repo(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if '--repo' in argv:
        i = argv.index('--repo')
        if i + 1 < len(argv):
            return argv[i + 1]
    for candidate in REPO_CANDIDATES:
        if os.path.isdir(os.path.join(candidate, '.git')):
            return candidate
    return None


def _read_text(path):
    try:
        return io.open(path, encoding='utf-8').read(), ''
    except OSError as exc:
        return None, 'could not read %s: %s' % (path, exc)


def rows_from_open_work_index(text):
    """One 'row' per markdown table line starting with '|'. Each row is
    returned as (location, blob) where blob is the row's own raw text --
    good enough for a substring co-occurrence check without needing to
    parse cells, and robust to the escaped-pipe convention this file uses
    (an escaped pipe stays inside the blob either way, since this never
    splits on '|' at all)."""
    out = []
    for i, line in enumerate(text.split('\n'), 1):
        if line.strip().startswith('|'):
            out.append(('SAIRN-OPEN-WORK-INDEX.md:line %d' % i, line))
    return out


def rows_from_tier_a_reviews(text):
    """One 'row' per record in the top-level 'records' list, blob = the
    whole record serialised back to text (so a term inside 'what', 'verdict'
    or anywhere else in the record is found without hand-picking fields that
    can drift as the schema grows)."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        return None, 'could not parse tier-a-reviews.json: %s' % exc
    recs = data.get('records', []) if isinstance(data, dict) else data
    out = []
    for i, r in enumerate(recs):
        loc = 'tier-a-reviews.json:record %d (%s, opened %s)' % (
            i, r.get('author_session', '?'), r.get('opened_at', '?'))
        out.append((loc, json.dumps(r)))
    return out, ''


def rows_from_defect_register(text):
    try:
        data = json.loads(text)
    except ValueError as exc:
        return None, 'could not parse defect-density-register.json: %s' % exc
    recs = data.get('records', []) if isinstance(data, dict) else data
    out = []
    for i, r in enumerate(recs):
        loc = 'defect-density-register.json:record %d (%s, %s)' % (
            i, r.get('commit', '?'), r.get('date', '?'))
        out.append((loc, json.dumps(r)))
    return out, ''


def load_all_rows(repo):
    """[(source_name, location, blob)], problem. problem non-empty (and
    rows None) means at least one of the three sources could not be read at
    all -- COULD NOT RUN, never silently degrading to 'checked the two that
    worked and called it clean'."""
    if not repo or not os.path.isdir(repo):
        return None, 'no readable repo: %r' % repo
    all_rows = []
    for source, relpath in REGISTER_RELPATHS:
        path = os.path.join(repo, relpath.replace('/', os.sep))
        text, problem = _read_text(path)
        if problem:
            return None, problem
        if source == 'open-work-index':
            rows = rows_from_open_work_index(text)
        elif source == 'tier-a-reviews':
            rows, problem = rows_from_tier_a_reviews(text)
        else:
            rows, problem = rows_from_defect_register(text)
        if rows is None:
            return None, problem
        for loc, blob in rows:
            all_rows.append((source, loc, blob))
    return all_rows, ''


def find_candidates(terms, all_rows):
    """[(source, location, matched_terms)] for every row where >= 2 of the
    supplied terms co-occur (case-insensitive substring). A single matching
    term is never enough -- see module docstring."""
    if len(terms) < 2:
        raise ValueError('at least 2 terms are required -- a single shared '
                         'term (a bare resource name) produces pure noise')
    lowered = [t.lower() for t in terms]
    out = []
    for source, loc, blob in all_rows:
        blob_l = blob.lower()
        matched = [t for t, tl in zip(terms, lowered) if tl in blob_l]
        if len(matched) >= 2:
            out.append((source, loc, matched))
    return out


def main(argv):
    if '--selftest' in argv:
        return 0 if run_fixtures() else 1
    repo = discover_repo(argv)
    terms = [a for a in argv if not a.startswith('--')]
    if '--repo' in argv:
        i = argv.index('--repo')
        if i + 1 < len(terms) + 1 and (i + 1) < len(argv):
            rp = argv[i + 1]
            terms = [t for t in terms if t != rp]
    if len(terms) < 2:
        print('usage: hover_duplicate_finding_check.py "term one" "term two" '
             '[more...]  -- at least 2 terms required')
        return 2
    all_rows, problem = load_all_rows(repo)
    if all_rows is None:
        print('COULD NOT RUN: %s' % problem)
        return 2
    candidates = find_candidates(terms, all_rows)
    if not candidates:
        print('NO CANDIDATE FOUND -- a lead, not a verdict: no existing record has 2+ of '
             'these terms co-occurring, which means this SEARCH found nothing, not that '
             'no duplicate exists. Pure substring matching cannot see a duplicate expressed '
             'in different words. Terms tried:')
        for t in terms:
            print('  - %s' % t)
        return 0
    print('%d CANDIDATE DUPLICATE(S) FOUND -- read before logging as new:' % len(candidates))
    for source, loc, matched in candidates:
        print('  [%s] %s' % (source, loc))
        print('      matched: %s' % ', '.join(matched))
    return 1


def run_fixtures():
    ok = [0]
    bad = []

    def ck(name, cond):
        if cond:
            ok[0] += 1
            print('  ok   ' + name)
        else:
            bad.append(name)
            print('  FAIL ' + name)

    ck('rows_from_open_work_index() finds every pipe-leading line',
       len(rows_from_open_work_index('| a | b |\nnot a row\n| c | d |\n')) == 2)

    # REALISTIC RATHER THAN A GENERIC PLACEHOLDER BUG NAME (2026-09-22 revision):
    # the original fixture used an invented "frobnicator race condition". The
    # scenario below is a real, recurring class on this platform tonight --
    # a justification comment asserting "no session gate needed" whose premise
    # (the app has no per-employee auth) later shipped and stopped being true,
    # found independently in both SV_RESOURCES (6fb6d696) and SF_RESOURCES
    # (c4f258f4). A duplicate-finding check earns its keep on the scenario it
    # would actually be run against, not on whether the matching logic works
    # in the abstract.
    tar_text = json.dumps({'records': [
        {'author_session': 'cc', 'opened_at': 't1',
         'what': 'a fix for the stale session-gate justification comment'},
        {'author_session': 'cody', 'opened_at': 't2', 'what': 'totally unrelated'},
    ]})
    rows, problem = rows_from_tier_a_reviews(tar_text)
    ck('rows_from_tier_a_reviews() produces one row per record',
       not problem and len(rows) == 2)

    ddr_text = json.dumps({'records': [
        {'commit': 'deadbeef', 'date': '2026-01-01',
         'summary': 'the stale session-gate justification comment was fixed by re-verifying the premise'},
    ]})
    rows2, problem2 = rows_from_defect_register(ddr_text)
    ck('rows_from_defect_register() produces one row per record',
       not problem2 and len(rows2) == 1)

    all_rows = ([('open-work-index', 'line 1', '| stale session-gate | justification comment | open |')]
               + [('tier-a-reviews', loc, blob) for loc, blob in rows]
               + [('defect-density-register', loc, blob) for loc, blob in rows2])

    ck('find_candidates() requires 2+ terms, raises on 1',
       _raises(ValueError, find_candidates, ['only one'], all_rows))

    cands = find_candidates(['session-gate', 'justification comment'], all_rows)
    ck('two co-occurring terms produce candidates across ALL THREE sources '
       '(the exact gap hover1\'s own build has -- confirming this build '
       'does not repeat it)',
       {c[0] for c in cands} == {'open-work-index', 'tier-a-reviews', 'defect-density-register'})

    cands_single = find_candidates(['session-gate', 'nonexistent-term-xyz'], all_rows)
    ck('a single matching term (the other term matches nothing) produces '
       'NO candidate -- co-occurrence of 2 is required, not 1',
       len(cands_single) == 0)

    cands_case = find_candidates(['SESSION-GATE', 'JUSTIFICATION COMMENT'], all_rows)
    ck('matching is case-insensitive', len(cands_case) > 0)

    import tempfile
    tmpdir = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmpdir, 'docs'))
    with io.open(os.path.join(tmpdir, 'docs', 'SAIRN-OPEN-WORK-INDEX.md'), 'w', encoding='utf-8') as f:
        f.write('| a | b |\n')
    with io.open(os.path.join(tmpdir, 'docs', 'tier-a-reviews.json'), 'w', encoding='utf-8') as f:
        f.write('{"records": []}')
    # defect-density-register.json deliberately MISSING
    all_rows3, problem3 = load_all_rows(tmpdir)
    ck('load_all_rows() COULD NOT RUN (not silently clean) when even one of '
       'the three sources is missing -- the exact "checked 2 of 3 and called '
       'it clean" failure this build exists to not repeat',
       all_rows3 is None and problem3)

    # KNOWN-BAD CONTROL, conflict-marker sweep, 2026-09-28: a conflicted
    # tier-a-reviews.json must be a COULD-NOT-PARSE, never rows from one
    # side. JSON's strict grammar already gives this behavior for free
    # (unlike the regex/structural parsers fixed twice elsewhere this
    # session); the control LOCKS it against a future 'lenient parse'
    # change quietly reintroducing the class.
    conflicted_json = ('<<<<<<< HEAD\n{"records":[{"a":1}]}\n=======\n'
                     '{"records":[{"a":2}]}\n>>>>>>> branch\n')
    rows_c, err_c = rows_from_tier_a_reviews(conflicted_json)
    ck('KNOWN-BAD CONTROL: a tier-a-reviews.json with unresolved conflict '
       'markers is COULD-NOT-PARSE (None, error), never rows from one side',
       rows_c is None and err_c)

    print('')
    print('%d ok, %d failed' % (ok[0], len(bad)))
    return not bad


def _raises(exc_type, fn, *a, **kw):
    try:
        fn(*a, **kw)
        return False
    except exc_type:
        return True


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
