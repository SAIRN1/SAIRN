"""sabotage_benchmark/run_benchmark.py -- score reference detectors against
the corpus, and report a real, standing N of M discrimination number, the
same shape Anthropic reports for Petri's own quirky-model suite (built here
from SAIRN's own real incidents instead -- see fixtures.py's own header for
why that is a real difference, not a rebrand).

USAGE:
    python run_benchmark.py            # score every fixture's own reference
                                        # detector against its own pair
    python run_benchmark.py --selftest # identical to the above; this corpus
                                        # scoring ITSELF against known-real
                                        # incidents is its own meta-test --
                                        # there is no separate synthetic
                                        # layer above it the way
                                        # git_history_secrets_scan.py has one

A REAL DETECTOR (a build agent's future checker, or a future extension of an
existing platform scanner) that CLAIMS to guard one of these shapes should be
run against the matching fixture pair here BEFORE being trusted -- exactly
the "sabotage-verify before trusting" discipline this platform already holds
every other checker to, now with a real, versioned, growing corpus to run it
against instead of a one-off hand-built control each time.

HONEST LIMIT, STATED PLAINLY: 5 fixtures is a real, small, first version --
not a claim of covering every recurring defect shape this platform has ever
produced. Growing this corpus (a new fixture per newly-confirmed recurring
shape) is the whole point; this file's own docstring is the place that
number should be updated, not restated from memory elsewhere.
"""

import sys
from fixtures import ALL_FIXTURES


def score(fixture):
    detector = fixture["reference_detector"]
    vuln_input = fixture.get("vulnerable_input", fixture.get("vulnerable"))
    fixed_input = fixture.get("fixed_input", fixture.get("fixed"))

    try:
        vuln_result = bool(detector(vuln_input))
    except Exception as e:
        return False, "detector raised on VULNERABLE input: %r" % e
    try:
        fixed_result = bool(detector(fixed_input))
    except Exception as e:
        return False, "detector raised on FIXED input: %r" % e

    if vuln_result is True and fixed_result is False:
        return True, "correctly flagged vulnerable, correctly cleared fixed"
    if vuln_result is False:
        return False, "MISSED the vulnerable input entirely (false negative)"
    if fixed_result is True:
        return False, "FALSE POSITIVE on the fixed input (would still flag a real fix)"
    return False, "unexpected result shape"


def main(argv):
    print("SABOTAGE BENCHMARK -- %d fixture(s), each scored against its own "
          "reference detector\n" % len(ALL_FIXTURES))
    passed = 0
    for f in ALL_FIXTURES:
        ok, detail = score(f)
        passed += 1 if ok else 0
        print("  %s  %-55s %s" % ("ok  " if ok else "FAIL", f["id"], f["name"]))
        print("        real incident: %s" % f["real_incident"])
        print("        %s" % detail)
    print()
    print("SCORE: %d of %d known real defect-shapes correctly discriminated "
          "by their own reference detector." % (passed, len(ALL_FIXTURES)))
    print("WHAT THIS DOES NOT CLAIM: that any PLATFORM checker currently in "
          "use actually covers these shapes -- only that a reference "
          "detector CAN discriminate them, which is the bar a real checker "
          "should be held to before being trusted on the same shape.")
    return 0 if passed == len(ALL_FIXTURES) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
