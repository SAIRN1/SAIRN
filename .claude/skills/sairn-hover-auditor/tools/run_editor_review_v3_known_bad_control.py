#!/usr/bin/env python
"""KNOWN-BAD CONTROL for hover_editor_review_criteria.py's CRITERIA_VERSION 3
(IMPLIED_LINE, bare `:NNNN` implied-file citations) -- built 2026-09-29.

hover_editor_review_criteria.py already carries F17-F27, 27/27 passing, and
they are genuine regression tests: build_fixture_repo() makes a REAL git repo
and F26/F27 check drift a REAL commit produced. But 27 fixtures that always
pass is not, by itself, proof the lock has teeth for THIS specific feature --
per docs/2026-09-13-cross-domain-disciplines.md item 12 (ABLATION over chaos):
remove ONE named layer on already-clean code and measure what it alone
catches. This script is that ablation, run in BOTH directions so the negative
result is not just "the mutant differs" -- it must be the SPECIFIC absence
the mutation removes, and the unmutated control must still be clean.

METHOD: copy hover_editor_review.py + hover_editor_review_criteria.py into a
throwaway directory (never touches the real files), mutate ONE regex in the
copy so IMPLIED_LINE can never match anything, run `--fixtures` as a REAL
subprocess against the mutated copy (Python resolves the local import over
any installed one because the script's own directory is first on sys.path),
and assert the run reports failures -- specifically on the implied-file
fixtures (F17-F27) and nowhere else, since the mutation touches only
IMPLIED_LINE. A second run against an UNMUTATED copy is the positive control:
it must still report 27/27, proving the harness itself (not just the mutant)
is exercising the fixtures correctly.

Exit 0: both directions confirmed (mutant fails on the right fixtures, clean
copy still passes). Exit 1: the ablation did not behave as predicted -- the
lock does NOT have teeth for this feature, or the harness is broken. Exit 2:
COULD NOT RUN (a file/subprocess problem, never folded into pass or fail).
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEW_PY = HERE / "hover_editor_review.py"
CRITERIA_PY = HERE / "hover_editor_review_criteria.py"

# The fixtures whose expected verdict DEPENDS on IMPLIED_LINE matching
# something. F21 is DELIBERATELY unaffected: it asserts an implied match must
# NOT also fire on an explicit path:line -- with IMPLIED_LINE dead, that
# implied claim is simply never extracted (max_claims=1 still holds, since
# the explicit-citation claim alone already satisfies it), so F21's own
# assertion is untouched by this mutation. F20 was FIRST PREDICTED unaffected
# ("no default_file, so cannot_check either way") and PROVED WRONG by a real
# run against the mutant: with zero claims extracted, F20's `cannot=1`
# expectation is no longer met either (cannot_check counts a DIFFERENT claim
# path than "no implied claim exists at all") -- corrected here after
# checking the actual mutant output, not asserted from reading the code, and
# left as a comment rather than silently fixed so the correction is visible.
EXPECTED_TO_BREAK = {"F17", "F18", "F19", "F20", "F22", "F23", "F24", "F25", "F26", "F27"}
EXPECTED_UNAFFECTED = {"F21"}


def run_fixtures_in(dirpath):
    r = subprocess.run(
        [sys.executable, "hover_editor_review.py", "--fixtures"],
        cwd=str(dirpath), capture_output=True, text=True, timeout=120,
    )
    return r.returncode, r.stdout, r.stderr


def parse_fixture_lines(stdout):
    """{name_prefix: 'ok'|'FAIL'} keyed on the F<n> token at line start.
    The tool prints a PASS line as 'fixture ok    Fn ...' (lowercase) and a
    FAIL line as 'FIXTURE FAIL  Fn ...' (uppercase) -- case-insensitive
    match required, or every failure line is silently dropped instead of
    counted (the exact bug this control first shipped with, caught only
    because the mutant run was independently hand-verified rather than
    trusted from the parsed summary alone -- see the module docstring)."""
    out = {}
    for line in stdout.splitlines():
        line = line.strip()
        m = re.match(r"^fixture\s+(ok|fail)\s+(F\d+)\b", line, re.IGNORECASE)
        if m:
            status, fid = m.group(1).lower(), m.group(2)
            out[fid] = status
    return out


def stage(mutate):
    d = Path(tempfile.mkdtemp(prefix="hover_editor_kbc_"))
    shutil.copy(REVIEW_PY, d / "hover_editor_review.py")
    shutil.copy(CRITERIA_PY, d / "hover_editor_review_criteria.py")
    if mutate:
        src = (d / "hover_editor_review_criteria.py").read_text(encoding="utf-8")
        needle = (
            'IMPLIED_LINE = re.compile(r"(?<![\\w./])\\:(\\d{1,6})(?:-(\\d{1,6}))?\\b")'
        )
        if needle not in src:
            raise RuntimeError(
                "COULD NOT RUN: the exact IMPLIED_LINE definition line was not "
                "found verbatim in the source being mutated -- refusing to guess "
                "at a different line and silently mutate the wrong thing. The "
                "real file's regex definition has changed; update this control's "
                "`needle` to match."
            )
        # Mutated to a regex that can NEVER match (empty negative lookahead
        # applied to nothing after it -- structurally unsatisfiable), not
        # merely "unlikely" -- a control must remove the capability entirely,
        # not just make it rare.
        mutated = src.replace(
            needle,
            'IMPLIED_LINE = re.compile(r"(?!)")  # MUTATED: never matches, known-bad control',
        )
        (d / "hover_editor_review_criteria.py").write_text(mutated, encoding="utf-8")
    return d


def main():
    try:
        clean_dir = stage(mutate=False)
        mutant_dir = stage(mutate=True)
    except RuntimeError as e:
        print(str(e))
        return 2

    try:
        rc_clean, out_clean, err_clean = run_fixtures_in(clean_dir)
        rc_mut, out_mut, err_mut = run_fixtures_in(mutant_dir)
    except (OSError, subprocess.TimeoutExpired) as e:
        print("COULD NOT RUN: subprocess failure -- %s" % e)
        return 2
    finally:
        shutil.rmtree(clean_dir, ignore_errors=True)
        shutil.rmtree(mutant_dir, ignore_errors=True)

    ok = True

    # POSITIVE CONTROL: the unmutated copy must be exactly as clean as the
    # real file already shows -- checked against the tool's own printed
    # "all N fixtures classify correctly" line via regex, NOT a hardcoded
    # count. A hardcoded "27" here broke silently the moment F28-F31 were
    # added (2026-09-29, the negation-guard fix) -- the file grew to 31
    # fixtures and the string check stopped matching anything, which is
    # exactly the "a check that stops testing anything, unannounced" shape
    # this whole platform's own discipline #8 warns about, caught here
    # rather than left stale a second time.
    clean_results = parse_fixture_lines(out_clean)
    clean_fails = [k for k, v in clean_results.items() if v == "fail"]
    clean_lock_match = re.search(r"all (\d+) fixtures classify correctly", out_clean)
    if rc_clean != 0 or clean_fails or not clean_lock_match:
        print("CONTROL-OF-THE-CONTROL FAILED: the UNMUTATED copy did not pass "
              "clean (rc=%d, failing=%s, lock-line matched=%s). The ablation "
              "harness is not trustworthy until this is fixed -- the mutant "
              "result below is not meaningful on its own."
              % (rc_clean, clean_fails, bool(clean_lock_match)))
        ok = False
    total_fixtures = int(clean_lock_match.group(1)) if clean_lock_match else None

    # NEGATIVE CONTROL: the mutant must fail, and specifically on the
    # implied-file fixtures -- not vacuously (e.g. a crash before any fixture
    # runs), and not over-broadly (a fixture unrelated to IMPLIED_LINE
    # breaking would mean the mutation touched something it should not have).
    mut_results = parse_fixture_lines(out_mut)
    if not mut_results:
        print("MUTANT PRODUCED NO PARSEABLE FIXTURE LINES -- COULD NOT RUN, not "
              "a pass. stdout follows:\n%s\nstderr:\n%s" % (out_mut, err_mut))
        return 2

    broke = {k for k, v in mut_results.items() if v == "fail"}
    missing_expected_break = EXPECTED_TO_BREAK - broke
    unexpected_break = broke - EXPECTED_TO_BREAK
    wrongly_still_ok = EXPECTED_UNAFFECTED & broke

    if missing_expected_break:
        print("KNOWN-BAD CONTROL FAILED (too weak): killing IMPLIED_LINE did "
              "NOT break %s -- the lock has a blind spot on these fixtures; "
              "they are not actually exercising the feature they claim to." %
              sorted(missing_expected_break))
        ok = False
    if unexpected_break:
        print("KNOWN-BAD CONTROL FAILED (over-broad): killing IMPLIED_LINE "
              "unexpectedly broke %s, which this control asserts should be "
              "unaffected -- either the mutation touched more than intended, "
              "or EXPECTED_TO_BREAK/EXPECTED_UNAFFECTED above is wrong and "
              "needs correcting with the reason stated." % sorted(unexpected_break))
        ok = False
    if wrongly_still_ok - unexpected_break:
        pass  # already covered by unexpected_break; kept named for clarity

    if ok:
        print("KNOWN-BAD CONTROL PASSED, both directions:")
        print("  clean copy : %d/%d, unaffected by the harness itself"
              % (total_fixtures, total_fixtures))
        print("  mutant copy: IMPLIED_LINE killed -> %d fixtures broke (%s), "
              "exactly the predicted set; F21 unaffected as predicted"
              % (len(broke), sorted(broke)))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
