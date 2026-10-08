#!/usr/bin/env python
"""hover_review_triage.py -- before spending a `git show --stat` plus a full
read on every candidate in hover_coverage_ledger.py's UNCOVERED list, decide
which ones are even worth opening.

WIRED, SECOND PASS (same session, after the classify() fixtures locked).
docs/tier-a-reviews.json carries NO field naming a review's own DISCHARGE
commit -- only `commit`, the ORIGINAL change under review, which the
project's own review-ledger-reseat tooling already documents as routinely
going dead under a rebase. Cross-referencing a discharge sha to a record by
sha is therefore not a lookup this role can do reliably, and is not
attempted. What a discharge commit DOES carry, by definition, is its own
diff to docs/tier-a-reviews.json -- the same diff this role has been reading
by eye all session (`git show <sha> -- docs/tier-a-reviews.json`, then
scanning for a `"verdict":` line among the added lines) to decide "open or
discharged" before deciding whether to open the commit at all. That manual
step is what parse_verdict_from_diff() replaces, and git_diff_for() /
files_touched_by() are the two thin subprocess wrappers around the exact
two `git show` invocations this role already runs for every candidate.

WHY THIS EXISTS. The self-audit at hover-audit-log seq 846 named this as a
real, recurring cost: every coverage-ledger batch this session (8+ of them)
required manually running `git show --stat` and reading verdict text for
4-8 candidate commits before finding 2-3 that were both (a) actually
DISCHARGED -- carrying a real verdict to re-derive, not a bare
"chore(review): open/record the obligation" commit with verdict=null and
nothing to check -- and (b) clear of whichever files the session's current
build-agent claims put off limits for that round. Neither fact is visible
from hover_coverage_ledger.py's own UNCOVERED listing, which only shows the
sha and the commit subject line.

THIS IS A PURE CLASSIFIER, NOT A FIXER. It answers one question per
candidate -- "would re-deriving this one be worth a `git show`" -- from two
facts this role already has to gather anyway: the record's own verdict
field (None means nothing was ever discharged) and the set of files the
commit touches. It does not run git, does not read tier-a-reviews.json, and
does not know about claims; the caller supplies those as plain arguments so
the classifier itself stays testable on hand-built fixtures with no
network, no git repo, and no clock.

PRECEDENCE, LOCKED BY FIXTURE #3/#4 BELOW: an excluded file wins over having
a verdict. A discharged review whose commit touches a file this role is
currently told to avoid is still skip-excluded -- the verdict exists to be
re-derived, and re-deriving it would mean reading the excluded file, which
is the thing being avoided. Having a verdict does not buy back the file.

MATCHING IS PLAIN SUBSTRING CONTAINMENT, DELIBERATELY NOT A GLOB OR REGEX.
`pattern in f` for each file `f`. Fixture #7 below locks the one subtlety
this already caused in real use this session: "api/sd-data.js" as a pattern
must NOT match "api/sd-data-customer-soft-delete.test.js" -- a different
string that happens to share a prefix -- because plain containment checks
the whole pattern appears verbatim, and ".js" immediately after "sd-data"
is not present in the longer name. If a future caller wants prefix-aware or
glob matching, that is a different tool; this one is the containment check
this role has already been doing by eye and getting right only because the
testing was careful, not because the method was reliable.
"""
import sys


def classify(verdict, files, exclude_patterns):
    """Decide whether a review-shaped commit is worth opening.

    verdict: the discharged review's own `verdict` field, or None if the
        obligation was only opened/recorded and never discharged.
    files: the list of file paths the commit touches.
    exclude_patterns: substrings naming files this role is currently told
        to avoid. Order does not matter; all matches are reported.

    Returns a dict: {'has_verdict': bool, 'excluded_by': [pattern, ...],
    'recommend': 'pick' | 'skip-excluded' | 'skip-no-verdict'}.
    """
    excluded_by = [p for p in exclude_patterns if any(p in f for f in files)]
    has_verdict = verdict is not None
    if excluded_by:
        recommend = 'skip-excluded'
    elif not has_verdict:
        recommend = 'skip-no-verdict'
    else:
        recommend = 'pick'
    return {'has_verdict': has_verdict, 'excluded_by': excluded_by,
            'recommend': recommend}


FIXTURES = [
    (
        "1. discharged, no excluded files -> pick",
        dict(verdict="SOUND, driven not read.", files=["tools/some_check.py"],
             exclude_patterns=["api/sd-data.js"]),
        dict(has_verdict=True, excluded_by=[], recommend="pick"),
    ),
    (
        "2. open obligation (verdict None), no excluded files -> skip-no-verdict",
        dict(verdict=None, files=["tools/some_check.py"],
             exclude_patterns=["api/sd-data.js"]),
        dict(has_verdict=False, excluded_by=[], recommend="skip-no-verdict"),
    ),
    (
        "3. discharged BUT touches an excluded file -> skip-excluded "
        "(exclusion wins over having a verdict)",
        dict(verdict="SOUND.", files=["api/sd-data.js"],
             exclude_patterns=["api/sd-data.js"]),
        dict(has_verdict=True, excluded_by=["api/sd-data.js"],
             recommend="skip-excluded"),
    ),
    (
        "4. open AND touches an excluded file -> still skip-excluded, not "
        "skip-no-verdict (the two reasons do not stack into a third state)",
        dict(verdict=None, files=["api/sd-data.js"],
             exclude_patterns=["api/sd-data.js"]),
        dict(has_verdict=False, excluded_by=["api/sd-data.js"],
             recommend="skip-excluded"),
    ),
    (
        "5. two exclude patterns given, only one actually present in the "
        "file list -> excluded_by names only the one that matched",
        dict(verdict="SOUND.", files=["tests/sairncare/test-alf-mar.js"],
             exclude_patterns=["tests/sairncare/test-alf-mar.js",
                                "tools/rebase_state_guard.py"]),
        dict(has_verdict=True, excluded_by=["tests/sairncare/test-alf-mar.js"],
             recommend="skip-excluded"),
    ),
    (
        "6. no exclude patterns supplied at all -> an empty list can never "
        "exclude anything, so an open obligation still reads skip-no-verdict "
        "rather than silently becoming pick",
        dict(verdict=None, files=["api/sd-data.js"], exclude_patterns=[]),
        dict(has_verdict=False, excluded_by=[], recommend="skip-no-verdict"),
    ),
    (
        "7. THE REAL SUBTLETY THIS SESSION HIT: 'api/sd-data.js' as a "
        "pattern must NOT match a differently-named test file that merely "
        "shares a prefix",
        dict(verdict="SOUND.",
             files=["api/sd-data-customer-soft-delete.test.js"],
             exclude_patterns=["api/sd-data.js"]),
        dict(has_verdict=True, excluded_by=[], recommend="pick"),
    ),
    (
        "8. CONTROL for #7, the other direction: the exact file name DOES "
        "match its own pattern -- #7 is not passing because nothing can "
        "ever match",
        dict(verdict="SOUND.", files=["api/sd-data.js"],
             exclude_patterns=["api/sd-data.js"]),
        dict(has_verdict=True, excluded_by=["api/sd-data.js"],
             recommend="skip-excluded"),
    ),
    (
        "9. a commit touching several files, only one of which is excluded "
        "-> still skip-excluded (one excluded file is enough; the safe "
        "files present alongside it do not dilute the exclusion)",
        dict(verdict="SOUND.",
             files=["tools/safe_tool.py", "api/sd-data.js", "docs/x.md"],
             exclude_patterns=["api/sd-data.js"]),
        dict(has_verdict=True, excluded_by=["api/sd-data.js"],
             recommend="skip-excluded"),
    ),
]


def run_fixtures():
    ok_count = 0
    for name, inputs, expected in FIXTURES:
        got = classify(**inputs)
        if got == expected:
            print("  ok   %s" % name)
            ok_count += 1
        else:
            print("  FAIL %s" % name)
            print("       expected %r" % (expected,))
            print("       got      %r" % (got,))
    print("criteria lock: %d/%d fixtures classify correctly, on hand-built "
          "inputs only" % (ok_count, len(FIXTURES)))
    return ok_count == len(FIXTURES)


import io
import json
import os
import re
import subprocess


def parse_verdict_from_diff(diff_text):
    """Given the text of `git show <sha> -- docs/tier-a-reviews.json`,
    return the non-null verdict string the commit ADDS, or None if it adds
    no non-null verdict (an open/record-only commit, or a commit that
    touches the file for some other reason without discharging anything).

    Only ADDED lines count -- a line starting with '+' and not '+++' (the
    diff's own file-header line, which also starts with '+'). A removed
    `-      "verdict": null` is not evidence either way; it is what every
    open->discharged transition removes on its way to adding the real one.
    """
    for line in diff_text.splitlines():
        if line.startswith('+++'):
            continue
        if not line.startswith('+'):
            continue
        body = line[1:]
        if '"verdict"' not in body:
            continue
        # (?:[^"\\]|\\.)* consumes an escaped char (\\. ) or any ordinary
        # char that is neither a quote nor a backslash, so the match stops
        # at the real closing quote rather than running through an escaped
        # one -- a plain `.*"` would stop at the FIRST quote, which is the
        # escaped one, and return a truncated string. Fixture E below is
        # the control that would have caught the plain-`.*` version.
        m = re.search(r'"verdict"\s*:\s*"((?:[^"\\]|\\.)*)"', body)
        if m:
            # JSON-DECODE THE CAPTURE, NOT THE RAW TEXT. Found live, not
            # guessed: the diff's text still carries literal backslash-n
            # (two characters) for every newline inside the verdict prose,
            # while json.load()-ing the live file turns the same escape
            # into a real newline. Comparing the raw capture against a
            # record read with json.load() (record_files_for_verdict)
            # would never match on any multi-line verdict -- which is all
            # of them. Wrapping the capture back in quotes and handing it
            # to json.loads() applies the exact same decoding json.load()
            # already applied to the live file, so the two strings are
            # directly comparable.
            try:
                return json.loads('"' + m.group(1) + '"')
            except ValueError:
                return m.group(1)
    return None


PARSE_VERDICT_FIXTURES = [
    (
        "A. a clean open->discharged diff: removed null, added a real "
        "verdict -> the added string",
        '-      "verdict": null\n+      "verdict": "SOUND, driven not read."',
        "SOUND, driven not read.",
    ),
    (
        "B. record-only commit, no verdict line touched at all -> None",
        '+      "opened_at": "2026-09-30T00:25:30Z",\n+      "status": "open",',
        None,
    ),
    (
        "C. a removed null with NOTHING added in its place (a field "
        "deleted outright) -> None, not the removed value",
        '-      "verdict": null',
        None,
    ),
    (
        "D. the diff's OWN file-header line starts with '+++' and must "
        "not be read as an added line even though it starts with '+'",
        '+++ b/docs/tier-a-reviews.json\n+      \"status\": \"open\",',
        None,
    ),
    (
        "E. a verdict string containing an escaped double-quote, FOLLOWED "
        "by more JSON on the same line: the match must stop at the real "
        "closing quote (not run into the next field's own quoted value), "
        "AND the result must be JSON-DECODED -- a real quote character, "
        "not the two-character backslash-quote the diff text still shows",
        '+      "verdict": "the file reads \\"ok\\" in both branches", '
        '"reviewer_session": "cc"',
        'the file reads "ok" in both branches',
    ),
    (
        "G. a verdict containing an escaped newline (routine in this "
        "file's real multi-paragraph verdicts) must decode to a real "
        "newline, so it can be compared against a record read with "
        "json.load() -- not left as two literal characters",
        '+      "verdict": "first line\\nsecond line"',
        "first line\nsecond line",
    ),
]


def _naive_parse_verdict_control(diff_text):
    """NOT USED BY parse_verdict_from_diff -- kept only so fixture F below
    can prove escape-awareness is load-bearing rather than coincidental, by
    running the OBVIOUS, unescaped version against the same input and
    showing it gets fixture E's case wrong."""
    for line in diff_text.splitlines():
        if line.startswith('+++') or not line.startswith('+'):
            continue
        m = re.search(r'"verdict"\s*:\s*"(.*)"', line[1:])
        if m:
            return m.group(1)
    return None


def run_parse_verdict_fixtures():
    ok_count = 0
    for name, diff_text, expected in PARSE_VERDICT_FIXTURES:
        got = parse_verdict_from_diff(diff_text)
        if got == expected:
            print("  ok   %s" % name)
            ok_count += 1
        else:
            print("  FAIL %s" % name)
            print("       expected %r" % (expected,))
            print("       got      %r" % (got,))
    # KNOWN-BAD CONTROL, run once rather than per-fixture: the naive,
    # escape-blind version must get fixture E's escaped-quote case WRONG,
    # which is what makes E a real lock on escape-awareness rather than a
    # case the naive pattern would also have passed by luck.
    escaped_case = PARSE_VERDICT_FIXTURES[-1][1]
    naive_result = _naive_parse_verdict_control(escaped_case)
    real_result = parse_verdict_from_diff(escaped_case)
    if naive_result != real_result:
        print("  ok   CONTROL: the naive escape-blind pattern gets the "
              "escaped-quote case WRONG (%r) where the real parser is "
              "right (%r) -- fixture E is testing something real"
              % (naive_result, real_result))
        ok_count += 1
    else:
        print("  FAIL CONTROL: the naive pattern agrees with the real one "
              "on the escaped-quote case -- fixture E proves nothing")
    total = len(PARSE_VERDICT_FIXTURES) + 1
    print("criteria lock: %d/%d parse_verdict_from_diff fixtures correct, "
          "on hand-built diff text only" % (ok_count, total))
    return ok_count == total


def git_diff_for(repo, sha, path):
    """Text of `git show <sha> -- <path>` in repo, or raise RuntimeError
    naming what failed. Read-only; never writes."""
    r = subprocess.run(['git', 'show', sha, '--', path], cwd=repo,
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace')
    if r.returncode != 0:
        raise RuntimeError('git show %s -- %s failed in %s: %s'
                            % (sha, path, repo, (r.stderr or '').strip()))
    return r.stdout


def files_touched_by(repo, sha):
    """[path, ...] touched by sha in repo, via `git show --stat`. Read-only."""
    r = subprocess.run(['git', 'show', '--stat', '--format=', sha], cwd=repo,
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace')
    if r.returncode != 0:
        raise RuntimeError('git show --stat %s failed in %s: %s'
                            % (sha, repo, (r.stderr or '').strip()))
    out = []
    for line in r.stdout.splitlines():
        if '|' not in line:
            continue
        name = line.split('|', 1)[0].strip()
        if name:
            out.append(name)
    return out


def record_files_for_verdict(reviews_json_path, verdict):
    """Find the record in a live docs/tier-a-reviews.json whose own
    'verdict' field equals the given string, and return ITS 'files' list --
    the ORIGINAL code under review -- or None if no record matches.

    WHY THIS EXISTS, FOUND BY PROVING triage() AGAINST A REAL COMMIT RATHER
    THAN GUESSED: files_touched_by(repo, sha) answers "what did the
    DISCHARGE commit itself change", which is very often just
    docs/tier-a-reviews.json plus whatever repair the reviewer happened to
    make in the same push -- NOT the original reviewed code. Proved live
    against 929473f2 (a real discharge in this session's own log, #819):
    the discharge commit's own files are .claude/claims/cody.json,
    docs/tier-a-reviews.json, tests/run_tier_a_review_gate_probe.py and
    tools/tier_a_review_gate.py -- none of them api/sd-data.js, even though
    the review this role actually re-verified at #819 was squarely about
    api/sd-data.js's storedBlob calls. A caller excluding api/sd-data.js
    would have missed this one entirely using files_touched_by() alone.
    The record's own 'files' field is the right source for "what to avoid
    re-opening" -- it is the ORIGINAL reviewed change's file list, recorded
    once when the obligation was opened and never the discharge commit's
    own diff footprint."""
    try:
        data = json.load(io.open(reviews_json_path, encoding='utf-8'))
    except (OSError, ValueError):
        return None
    for rec in data.get('records', []):
        if rec.get('verdict') == verdict:
            return rec.get('files')
    return None


def triage(repo, sha, exclude_patterns, reviews_path='docs/tier-a-reviews.json'):
    """The real, git-touching end-to-end call. Verdict from the discharge
    commit's own diff to reviews_path. Files to classify against are the
    ORIGINAL review record's 'files' field when the verdict matches one
    (record_files_for_verdict) -- falling back to the discharge commit's own
    changed files (files_touched_by) only when no record matches, which
    happens for an open/record-only commit that never added a findable
    verdict in the first place. Returns classify()'s dict plus 'files',
    'files_source' ('record' | 'commit-stat') and 'verdict'."""
    diff_text = git_diff_for(repo, sha, reviews_path)
    verdict = parse_verdict_from_diff(diff_text)
    files = None
    files_source = None
    if verdict is not None:
        files = record_files_for_verdict(os.path.join(repo, reviews_path), verdict)
        if files is not None:
            files_source = 'record'
    if files is None:
        files = files_touched_by(repo, sha)
        files_source = 'commit-stat'
    result = classify(verdict, files, exclude_patterns)
    result['files'] = files
    result['files_source'] = files_source
    result['verdict'] = verdict
    return result


if __name__ == '__main__':
    argv = sys.argv[1:]
    if '--fixtures' in argv:
        ok1 = run_fixtures()
        ok2 = run_parse_verdict_fixtures()
        sys.exit(0 if (ok1 and ok2) else 1)
    if '--triage' in argv:
        i = argv.index('--triage')
        sha = argv[i + 1]
        repo = None
        exclude = []
        j = i + 2
        while j < len(argv):
            if argv[j] == '--repo':
                repo = argv[j + 1]
                j += 2
            elif argv[j] == '--exclude':
                exclude.append(argv[j + 1])
                j += 2
            else:
                j += 1
        if not repo:
            print("--triage needs --repo <path>")
            sys.exit(2)
        result = triage(repo, sha, exclude)
        print("sha        : %s" % sha)
        print("has_verdict: %s" % result['has_verdict'])
        print("excluded_by: %s" % result['excluded_by'])
        print("recommend  : %s" % result['recommend'])
        print("files      : %d (source: %s)" % (len(result['files']),
                                                  result['files_source']))
        sys.exit(0)
    print(__doc__)
    print("\nRun with --fixtures to lock the pure classifier and the diff "
          "parser against hand-built cases. Run with --triage <sha> --repo "
          "<path> [--exclude <pattern> ...] for the real, git-touching "
          "end-to-end call against one real commit.")
    sys.exit(0)
