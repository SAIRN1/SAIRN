"""The pass/fail criteria for a requirement, LOCKED BEFORE seeing real code.

── WHY THIS IS A SEPARATE FILE, AND WHY IT CARRIES ITS OWN FIXTURES ──────
A gate whose criteria were derived from what the code already does is not a
check -- it is a description wearing a check's clothes, and it passes by
construction. That failure is not hypothetical here: hours before this was
written, an FMEA scorer reported 38% accuracy on a three-shared-word rule, and
all five hits were false positives. The rule had been chosen by looking at what
produced a number.

So this file holds the criteria AND a set of hand-decided examples, and
`tools/testability_gate.py` REFUSES TO JUDGE ANY REAL REQUIREMENT UNLESS EVERY
FIXTURE BELOW CLASSIFIES CORRECTLY FIRST. That is the lock. Criteria quietly
loosened to flatter the real corpus will break a fixture before they can
flatter anything.

The fixtures were written before the traceability matrix was read for content.
Only its row COUNT (178) was known, which is a shape, not a sample.

── THE CRITERIA, stated as claims about the sentence ──────────────────────
A requirement is TESTABLE when a reader could, in principle, run something and
get a yes or a no. Four ways it fails that, each mechanical:

  VAGUE       it leans on a word that cannot be measured -- "properly",
              "appropriately", "robust", "as needed". The word is the tell: it
              is where the real condition was supposed to go.
  NO-CLAIM    it names a thing but asserts nothing about its behaviour. "A
              checker for X exists" is a fact about the repo, not a property
              anybody can falsify by running the system.
  TOO-SHORT   it is too few words to carry a subject AND a condition. A
              threshold, not a judgement, and deliberately low so it catches
              only labels.
  UNFALSIFIABLE  it is hedged into always being true -- "should generally",
              "where possible", "may".

Anything else PASSES. The gate is report-only and the burden is on the CHECKER
to show a requirement is untestable, never on the requirement to prove itself.
"""

VERSION = '2026-09-13.2'
# 2026-09-13.2 -- the criteria FAILED their own fixtures on the first run, which
# is the lock doing its job before a single real requirement was judged. Three
# corrections, all to the CRITERIA:
#   * BEHAVIOUR held only base and third-person forms, so the PASSIVE VOICE --
#     "is denied", "is refused", "cites" -- read as asserting nothing. Most
#     requirements in this repo are written passively;
#   * TOO-SHORT was tested before VAGUE, so "errors are reported appropriately"
#     came back TOO-SHORT. A short vague sentence is VAGUE: the word is the
#     finding, and reporting length instead hides it.
# And ONE correction to a FIXTURE, declared rather than quiet: "the criticality
# tier register" is four words, so TOO-SHORT is the correct and more actionable
# verdict, not the NO-CLAIM I had written. The fixture was lengthened to test
# NO-CLAIM properly instead. That is a change made on the merits of the case,
# NOT to match what the tool happened to output -- the distinction this whole
# file exists to keep.

# A word that stands where a measurable condition should be. Matched on a word
# boundary so "correctly" fires and "correctness" does not -- the latter is a
# noun naming a subject, which is fine.
VAGUE = (
    'properly', 'appropriately', 'correctly', 'robust', 'robustly', 'reasonable',
    'reasonably', 'as needed', 'as appropriate', 'as required', 'gracefully',
    'sensible', 'sensibly', 'adequate', 'adequately', 'sufficiently',
    'well-behaved', 'user-friendly', 'intuitive', 'efficient', 'efficiently',
    'optimal', 'optimally', 'good', 'better', 'best-effort', 'etc',
)

# A hedge that makes the sentence true whatever happens.
HEDGE = (
    'should generally', 'where possible', 'wherever possible', 'if possible',
    'may ', 'might ', 'could ', 'ideally', 'preferably', 'try to', 'attempt to',
    'aims to', 'intended to',
)

# A verb asserting BEHAVIOUR. A requirement with none of these is naming a
# thing rather than claiming something about it.
BEHAVIOUR = (
    'refuse', 'refuses', 'reject', 'rejects', 'deny', 'denies', 'block', 'blocks',
    'allow', 'allows', 'return', 'returns', 'report', 'reports', 'raise', 'raises',
    'fail', 'fails', 'pass', 'passes', 'write', 'writes', 'read', 'reads',
    'forward', 'forwards', 'enforce', 'enforces', 'require', 'requires',
    'assert', 'asserts', 'match', 'matches', 'carry', 'carries', 'stamp', 'stamps',
    'log', 'logs', 'surface', 'surfaces', 'name', 'names', 'count', 'counts',
    'filter', 'filters', 'keep', 'keeps', 'drop', 'drops', 'never', 'always',
    'must', 'cannot', 'does not', 'is not', 'are not', 'has no', 'have no',
    'authenticate', 'authenticates', 'validate', 'validates', 'resolve',
    'resolves', 'answer', 'answers', 'say', 'says', 'still', 'before', 'after',
    # PASSIVE AND PAST FORMS. Most requirements here are written passively --
    # "a push aimed at master is denied" -- and without these the whole voice
    # reads as asserting nothing.
    'denied', 'refused', 'rejected', 'blocked', 'allowed', 'returned',
    'reported', 'raised', 'failed', 'passed', 'written', 'read', 'forwarded',
    'enforced', 'required', 'asserted', 'matched', 'carried', 'stamped',
    'logged', 'surfaced', 'named', 'counted', 'filtered', 'kept', 'dropped',
    'cite', 'cites', 'cited', 'exists', 'appears', 'reaches', 'reach',
)

MIN_WORDS = 5

# ── FIXTURES: decided by hand, BEFORE the real corpus was read for content ─
# (text, expected verdict). A criteria change that flatters real requirements
# will break one of these first, which is the whole point of committing them.
FIXTURES = (
    # -- should PASS: a subject, and a condition that could be false
    ('the endpoint forwards every input the deadline engine reads', 'PASS'),
    ('no storage wrapper on the platform can fail silently', 'PASS'),
    ('a push aimed at master is denied', 'PASS'),
    ('soft-deleted rows are not returned by the read path', 'PASS'),
    ('every Tier A row cites a commit, a schema file or an incident', 'PASS'),
    ('the merge keeps the local record when its stamp is strictly newer', 'PASS'),
    ('a capture with no _generated_at is refused rather than defaulted', 'PASS'),

    # -- should FAIL: VAGUE
    ('the sync handles conflicts properly', 'VAGUE'),
    ('errors are reported appropriately', 'VAGUE'),
    ('the checker behaves correctly on every app', 'VAGUE'),
    ('the endpoint is robust under load', 'VAGUE'),

    # -- should FAIL: NO-CLAIM (names a thing, asserts nothing testable)
    ('a checker for duplicate globals', 'NO-CLAIM'),
    ('the criticality tier register for every registered app resource', 'NO-CLAIM'),

    # -- should FAIL: TOO-SHORT
    ('push gate', 'TOO-SHORT'),
    ('idempotency', 'TOO-SHORT'),

    # -- should FAIL: UNFALSIFIABLE
    ('the write should generally reach the server', 'UNFALSIFIABLE'),
    ('the tool may report a finding where possible', 'UNFALSIFIABLE'),
)
