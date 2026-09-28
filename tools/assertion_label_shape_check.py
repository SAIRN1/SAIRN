#!/usr/bin/env python
"""Does the assertion's LABEL claim more than its COMPARISON can see?

    python tools/assertion_label_shape_check.py
    python tools/assertion_label_shape_check.py --fixtures   # the criteria lock, alone
    python tools/assertion_label_shape_check.py --quiet
    python tools/assertion_label_shape_check.py --all        # list the CLEAN rows too

Exit 0 clean, 1 findings, 2 COULD NOT RUN. REPORT ONLY.

── WHY THIS EXISTS ──────────────────────────────────────────────────────────
A register record from 2026-09-16 (`1a64e873128e`, rule 1.11) recorded this as
owed and it stayed owed for eleven days:

    "A floor is the RIGHT tool for a ratchet and the wrong one for a coverage
     claim, and nothing distinguishes the two at review time. Of 57
     floor-compared assertions swept, most are honest ratchets or not-empty
     checks; two had labels claiming a relationship the comparison could not
     see."
    ACTION, planned: "No check compares an assertion's LABEL against the SHAPE
     of its comparison. Both instances were found by reading labels for the
     word every."

READING LABELS FOR THE WORD "EVERY" IS NOT A MECHANISM. This is.

The instance that named the class: an arm labelled *"every section of the
matrix yields requirements"* backed by a FLOOR on the section count. A section
the extractor silently skipped would stay green -- the label claims a
universal, the comparison can only see a minimum, and the two read identically
in a passing run. This is the same family as the defect in this repo's own
memory: **`assert len(hits) == 1` held while the transform deleted 1465 lines**,
because uniqueness says nothing about position. The label is a claim; the
comparison is the evidence; nothing was comparing the two.

── THE ONE DISCRIMINATOR, AND WHY IT IS NOT "IS THERE A FLOOR" ─────────────
Most floors here are CORRECT. A ratchet, a not-empty check and a
grew-since-last-run check are all one-sided on purpose, and a tool that flagged
one-sidedness would report 57 rows of which 55 are right -- which is a tool
nobody runs twice.

The discriminator is the DISAGREEMENT:

    the LABEL makes an EXHAUSTIVE claim   (every / each / all / none / exactly
                                           / only)
    AND the label does NOT itself declare one-sidedness  (at least / at most /
                                           no fewer / minimum / not empty ...)
    AND the comparison is ONE-SIDED       (> >= < <=)
    AND there is NO exact comparison anywhere in it (== != is in)

An honest ratchet SAYS it is a floor. That is what makes this decidable rather
than a judgement: the finding is a label and a comparison that contradict each
other, not a comparison shape on its own.

── WHAT IT DELIBERATELY DOES NOT DECIDE, stated rather than engineered away ─
  * A MIXED condition -- one exact comparison and one floor -- is CLEAN here.
    `a == 5 and b >= 1` usually means the exact half carries the claim and the
    floor is a guard. Flagging it would put the 55 honest rows back.
  * WHETHER THE EXHAUSTIVE CLAIM IS TRUE. This reads the shape of the
    comparison, never the data. A `== N` whose N is itself wrong passes here,
    and that is the *other* half of the same defect family -- pinned in memory
    as "a passing assertion can check the wrong thing" and NOT closed by this
    tool.
  * JAVASCRIPT. Every arm is read from a Python `ast` parse tree, for the
    reason `checker_control_check.py` rebuilt itself in 2026-09-13: patterns
    over text counted docstrings, path constants and print calls as evidence.
    The JS suites are NOT covered and the report says so on every run rather
    than leaving a reader to infer platform-wide coverage from a platform-wide
    clean line. Both known instances were in Python probes.

── SIGNATURE-AGNOSTIC ON PURPOSE ────────────────────────────────────────────
There is no single `check()` idiom here to key off. Measured across tests/:
`check(cond, label)`, `check(name, cond, detail)`, `check(label, actual,
expected)`, `check(name, got, want)` and `check(arm, ok, detail)` all exist. A
tool that assumed one of those would read the LABEL out of the CONDITION slot
in the others and report nonsense with total confidence.

So nothing here parses a signature. An arm is any call carrying BOTH a string
literal and a separate argument that CONTAINS a comparison -- which is true of
every variant above, and false for `check(label, got, want)` where the
comparison happens inside the callee and there is no shape at the call site to
read. Those are not judged, and the count of them is printed.

── THE CRITERIA ARE LOCKED BEFORE ANY REAL FILE IS READ (discipline 1) ─────
FIXTURES below are hand-written source strings with an expected verdict each.
They are classified FIRST, in a pass that reads no real file, and the tool
exits 2 "nothing real was judged" if any one of them comes back wrong. The
criteria were written from the register record's description of the two known
instances, BEFORE this tool was ever run over tests/ -- so the thresholds are
not a description of the corpus wearing a checker's clothes.

TWO FIXTURES WERE CORRECTED ON THE FIRST LOCK RUN, AND WHICH KIND OF
CORRECTION IT WAS IS STATED HERE BECAUSE DISCIPLINE 1 REQUIRES IT. It was the
first kind -- the expected verdict was wrong -- and the correction made the
fixture set STRICTLY STRONGER rather than looser, which is the only direction
that is safe to take on your own word:

  `check('at least 12 sections yield requirements', len(reqs) >= 12)` was
  written expecting CLEAN because "the label declares its own one-sidedness".
  Both the tool and the expectation agree it is CLEAN; they disagreed on WHY,
  and the tool was right -- that label has no universal word at all, so it is
  cleared one test earlier and never reaches the exemption. Same for the bare
  not-empty fixture.

  So rather than relabel the expected reason (which would be a fixture bent to
  match output, and is forbidden), BOTH FIXTURES WERE KEPT with the verdict the
  tool correctly gives, and TWO NEW ONES WERE ADDED that actually exercise the
  exemption -- a label carrying an exhaustive word AND a declared floor in the
  same sentence, which is the case ONE_SIDED_DECLARED exists for and which
  nothing was testing. 14 fixtures became 16, and the exemption went from
  unexercised to covered in both directions.

No fixture has been changed since. If a future edit corrects one, say which of
the two kinds it was.

── MEASURED PRECISION, AND THE THREE ROWS IT DOES NOT EARN ─────────────────
Two numbers, never one (discipline 2). On the first real corpus -- 327 Python
test files, 3,876 arms judged, 2026-09-27:

    CONFIRMED  12      of which 9 hold on reading the source   -> 9/12
    ADVISORY   11      not findings; the demotion reason is printed per row

**THE THREE I DO NOT CLAIM ARE LISTED, so the 9/12 is auditable rather than
asserted:**

  * `run_shape_antipattern_probe.py:81` -- *"the lock covers all three shapes"*
    backed by THREE conjoined floors, one per shape. The conjunction does
    enumerate all three; the floors are per-shape ratchets. Counting conjoined
    comparisons against a cardinal in the label would close it and is not worth
    the rule.
  * `run_shape_search_probe.py:64` and `:70` -- *"renaming every identifier does
    not move the score"* over ONE fixture pair. Reasonable people differ on
    whether the label overclaims or the arm is fine; the tool reports and the
    reader decides.

**FOUR FALSE-POSITIVE SHAPES WERE FOUND BY READING THE FIRST REAL RUN AND ARE
NOW CLOSED, each with a fixture in both directions:** the set-subset operator
(`set(a) <= set(b)` IS the universal), `all(...)` (the quantifier is the
`all`, not the comparison inside it), `min()`/`max()` (`min(xs) >= k` IS
`all(x >= k …)`), and -- the worst of them -- READING THE DETAIL ARGUMENT AS
THE CONDITION, which reported the shape of a failure MESSAGE as the shape of
the check. That one is why `arms()` reads only the slot adjacent to the label.

REPORT ONLY, and that is the reason 9/12 is a usable precision: a false
positive costs a reader ten seconds, not a blocked push. It is deliberately not
wired into the push gate.
"""
import argparse
import ast
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import (EXIT_COULD_NOT_RUN, finish,               # noqa: E402
                         tracked)

CONTROLLED_BY = ['tests/run_assertion_label_shape_probe.py']
CRITERIA_VERSION = '2026-09-27.1'

# ── THE CRITERIA ─────────────────────────────────────────────────────────────
# An EXHAUSTIVE claim: the label says the arm covers a whole population.
#
# THE NEGATIVE LOOKBEHIND IS NOT TIDYING. `(?<!-)` keeps `\bonly\b` out of
# hyphenated compounds: `soft-delete-only` has a word boundary before "only"
# because "-" is not a word character, so without it every label describing a
# soft-delete-only resource reads as an exhaustiveness claim. That was a real
# false positive on the first run (run_tier_a_replaceability_probe.py:80).
EXHAUSTIVE = re.compile(
    r'(?<!-)\b(every|each|all|none|exactly|only|no other|nothing else)\b', re.I)
# ── TIER: is the exhaustive word making the CLAIM, or explaining it? ─────────
# The first real run reported 32 arms, and reading them showed the word doing
# three different jobs. Only the first is this defect:
#
#   THE CLAIM       "every promoted checker is scored"           <- CONFIRMED
#   THE NEGATION    "it does NOT report every one as unguarded"  <- not a
#                   universal claim; the arm is asserting the opposite
#   THE EXPLANATION "...the majority ARE named, SO the rung is not reporting
#                   every action it can see"                     <- the word is
#                   in the rationale after a clause marker, not in the claim
#
# So the verdict is TIERED rather than thresholded, and the two counts are
# printed separately and never summed -- discipline 2 applied to a finding
# count: a single number would hide which half moved.
NEGATED_BEFORE = re.compile(
    r"(\bnot\b|n't\b|\bnever\b|\bno\b|\bnothing\b|\bwithout\b|\bfewer than\b)"
    r"[^.;]{0,14}$", re.I)
# Where the claim stops and the rationale starts. Everything after the FIRST of
# these is explanation, and an exhaustive word that appears only there is not
# the arm's claim.
CLAUSE_MARKER = re.compile(
    r'(\s--\s|\bso that\b|\bso\b|\bwhich\b|\bbecause\b|\brather than\b'
    r'|\botherwise\b|\bwould be\b|\bwould mean\b)', re.I)
# `all at the end`, `all of them`, `all the way` -- adverbial, not a quantifier
# over the population under test.
ADVERBIAL_AFTER = re.compile(
    r'\s+(at|of them|of it|the way|along|through)\b', re.I)
CONFIRMED, ADVISORY = 'CONFIRMED', 'ADVISORY'
# The label DECLARES its own one-sidedness. A ratchet that says it is a ratchet
# is not this defect -- it is the correct use of a floor.
ONE_SIDED_DECLARED = re.compile(
    r'(\bat least\b|\bat most\b|\bno fewer\b|\bno more\b|\bminimum\b'
    r'|\bmaximum\b|\bfloor\b|\bceiling\b|\bratchet\b|\bor more\b|\bor fewer\b'
    r'|\bnot empty\b|\bnon-?empty\b|\bat all\b|\bsome\b|\bgrew\b|\bgrows\b'
    r'|\bincreased\b|\bnever fewer\b|>=|<=|\bmore than\b|\bfewer than\b'
    r'|\bless than\b|\blonger than\b|\bshorter than\b)', re.I)
ONE_SIDED_OPS = (ast.Gt, ast.GtE, ast.Lt, ast.LtE)
EXACT_OPS = (ast.Eq, ast.NotEq, ast.Is, ast.IsNot, ast.In, ast.NotIn)

CLEAN_NO_EXHAUSTIVE = 'label makes no exhaustive claim'
CLEAN_DECLARED = 'label declares its own one-sidedness'
CLEAN_EXACT = 'the condition carries an exact comparison'
CLEAN_NO_COMPARE = 'no comparison at the call site to read'
FINDING = 'FINDING'


def classify(label, ops):
    """The whole criterion. `ops` is the list of ast comparison-operator types.

    Returns FINDING or one of the CLEAN_* reasons. Pure -- no file, no state --
    which is what lets the fixture lock below be a real lock rather than a
    second run of the same pipeline over different bytes.
    """
    if not ops:
        return CLEAN_NO_COMPARE
    if any(isinstance(o, EXACT_OPS) for o in ops):
        return CLEAN_EXACT
    if not any(isinstance(o, ONE_SIDED_OPS) for o in ops):
        return CLEAN_NO_COMPARE
    if not EXHAUSTIVE.search(label or ''):
        return CLEAN_NO_EXHAUSTIVE
    if ONE_SIDED_DECLARED.search(label or ''):
        return CLEAN_DECLARED
    return FINDING


def tier(label):
    """CONFIRMED when the exhaustive word makes the CLAIM, ADVISORY when it does
    not. Returns (tier, why). Only called on labels classify() already said
    FINDING for, so the floor-vs-exact question is settled before this runs.

    ADVISORY is printed and counted and NEVER folded into CONFIRMED, for the
    same reason EXIT_COULD_NOT_RUN is not folded into EXIT_CLEAN: the whole
    value of the split is that a reader can see which half moved.
    """
    text = label or ''
    claim = CLAUSE_MARKER.split(text, 1)[0]
    in_claim = [m for m in EXHAUSTIVE.finditer(claim)]
    if not in_claim:
        return ADVISORY, ('the exhaustive word is in the rationale, after a '
                          'clause marker -- the claim half makes no universal '
                          'claim')
    for m in in_claim:
        before = claim[:m.start()]
        after = claim[m.end():]
        if NEGATED_BEFORE.search(before):
            continue
        if ADVERBIAL_AFTER.match(after):
            continue
        return CONFIRMED, 'the exhaustive word IS the claim'
    return ADVISORY, ('every occurrence is negated or adverbial -- the arm is '
                      'asserting the opposite of a universal, or using the '
                      'word to describe position rather than population')


# ── EXTRACTION ───────────────────────────────────────────────────────────────
def _str_of(node):
    """The string a label argument contributes, or None if it contributes none.

    Handles the three shapes a real label takes: a plain literal, a `%`/`+`
    concatenation of literals, and an f-string. A label built entirely from
    variables yields None and the arm is NOT JUDGED rather than judged against
    an empty string -- an empty label would classify as "no exhaustive claim",
    which is a silent pass on an arm nobody read.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp):
        parts = [_str_of(node.left), _str_of(node.right)]
        parts = [p for p in parts if p]
        return ' '.join(parts) if parts else None
    if isinstance(node, ast.JoinedStr):
        parts = [v.value for v in node.values
                 if isinstance(v, ast.Constant) and isinstance(v.value, str)]
        return ' '.join(parts) if parts else None
    return None


def _is_setish(node):
    """True when this operand is SYNTACTICALLY a set.

    `set(a) <= set(b)` is NOT a numeric floor. It is the subset relation, which
    is the EXACT encoding of "every member of a is also in b" -- the strongest
    possible form of the universal claim the label is making, not a weaker one.
    Both false positives of this shape in the first real run
    (run_schema_verdict_probe.py:210 and :213) were correct assertions.

    Syntactic only, and deliberately: a bare NAME could hold a set or an int and
    nothing here can tell, so a name is not treated as a set. That errs toward
    reporting, which is the right direction for a report-only tool.
    """
    if isinstance(node, (ast.Set, ast.SetComp)):
        return True
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in ('set', 'frozenset'))


def _is_quantifier(node):
    """True when this operand makes the comparison a UNIVERSAL one.

    `min(xs) >= k` is not a floor on a count -- it is exactly `all(x >= k for x
    in xs)`, and `max(xs) <= k` is the mirror. A real arm proved this on the
    first run: *"the body count tracks the keyword count in every page (min
    ratio ...)"* backed by `min(_ratio.values()) >= 0.40` is a correct universal
    over every page, and reporting it would be telling an author their strongest
    available assertion is their weakest.
    """
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in ('min', 'max'))


def _ops_in(node):
    """Every comparison operator inside one expression, in source order.

    TWO SHAPES ARE SKIPPED, both because the universal is already expressed and
    the comparison is not the thing carrying it:

      * `all(<cond> for x in xs)` -- `all` IS the universal quantifier. A floor
        inside it bounds each ELEMENT, not the population, so the label's
        "every" and the code agree. `any()` is NOT skipped: it is an
        existential, and a universal label over an existential check is exactly
        this defect.
      * a comparison between two SETS -- see _is_setish.
    """
    out = []
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id == 'all':
        return out
    if isinstance(node, ast.Compare):
        operands = [node.left] + list(node.comparators)
        if not any(_is_setish(o) or _is_quantifier(o) for o in operands):
            out.extend(node.ops)
        for o in operands:
            out.extend(_ops_in(o))
        return out
    for sub in ast.iter_child_nodes(node):
        out.extend(_ops_in(sub))
    return out


def arms(src):
    """(line, label, ops, kind) for every readable assertion in `src`.

    Two shapes only, both from the parse tree:
      * `assert <cond>, '<label>'`
      * any Call carrying a string literal AND a separate argument containing a
        comparison -- which covers every check() signature variant in tests/
        without reading any of their signatures.
    """
    out = []
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            label = _str_of(node.msg) if node.msg is not None else None
            if label is not None:
                out.append((node.lineno, label, _ops_in(node.test), 'assert'))
            continue
        if not isinstance(node, ast.Call) or len(node.args) < 2:
            continue
        label, label_i = None, None
        for i, a in enumerate(node.args):
            s = _str_of(a)
            if s is not None:
                label, label_i = s, i
                break
        if label is None:
            continue
        # ONLY THE CONDITION SLOT IS READ, NOT EVERY NON-LABEL ARGUMENT.
        # The third argument of `check(name, cond, detail)` is the DETAIL a
        # failure prints, and it routinely contains a comparison of its own --
        # `str([k for k, v in X.items() if len(v) <= 30])`. Reading it produced a
        # confident finding about an arm whose condition was a correct `all(...)`
        # (run_financial_invariant_probe.py:215 on the first real run): the tool
        # was reporting the SHAPE OF THE ERROR MESSAGE as the shape of the check.
        #
        # The condition is the argument ADJACENT to the label: the one after it
        # (`check(name, cond, ...)`) or, when the label is last, the one before
        # (`check(cond, label)`). Both idioms are in tests/ and this reads each
        # correctly without knowing which is which.
        cand = None
        if label_i + 1 < len(node.args) \
                and _str_of(node.args[label_i + 1]) is None:
            cand = node.args[label_i + 1]
        elif label_i > 0:
            cand = node.args[label_i - 1]
        ops = _ops_in(cand) if cand is not None else []
        if ops:
            out.append((node.lineno, label, ops, 'call'))
    return out


# ── THE FIXTURE LOCK (discipline 1 and discipline 5) ─────────────────────────
# Hand-built sources, an expected verdict each, classified with NO real file in
# the run. Written from the register record's description of the two known
# instances before this tool was pointed at tests/.
FIXTURES = (
    # the real instance the register recorded, reduced
    ("check('every section of the matrix yields requirements', "
     "len(reqs) >= 12)", FINDING,
     'the named instance: a universal claim backed by a floor'),
    # the same floor, honestly labelled -- this is the 55-of-57 case
    ("check('at least 12 sections yield requirements', len(reqs) >= 12)",
     CLEAN_NO_EXHAUSTIVE, 'an honest ratchet with no universal word never '
     'reaches the exemption -- it is cleared one test earlier'),
    # ...and the exemption itself, which needs BOTH words in one label
    ("check('every section yields at least 12 requirements', len(reqs) >= 12)",
     CLEAN_DECLARED,
     'the exemption proper: an exhaustive word AND a declared floor in one '
     'label is a ratchet, not a contradiction'),
    ("check('every row is present', len(rows) == 12)", CLEAN_EXACT,
     'a universal claim backed by an exact count is the correct shape'),
    ("check('the section list is not empty', len(rows) > 0)",
     CLEAN_NO_EXHAUSTIVE, 'a bare not-empty check has no universal word either'),
    ("check('every section list is not empty', len(rows) > 0)", CLEAN_DECLARED,
     'a not-empty check IS one-sided on purpose, and saying so exempts it even '
     'under a universal word'),
    ("check('all three arms fired', fired >= 3)", FINDING,
     '"all" is the same claim as "every" and must not need its own rule'),
    ("check('the count grew since the last run', n > prev)",
     CLEAN_NO_EXHAUSTIVE, 'no exhaustive claim, so one-sidedness is not a '
     'contradiction'),
    ("assert len(hits) >= 1, 'every hit is unique'", FINDING,
     'the assert form carries its label second and must be read too'),
    ("check('exactly one row survives', len(rows) >= 1)", FINDING,
     '"exactly" is an exhaustive claim about a count and a floor cannot see it'),
    ("check('none of the rows are stale', stale == 0)", CLEAN_EXACT,
     'a negative universal backed by an equality is correct'),
    ("check('every code appears exactly once and the denominator is "
     "published', a == 5 and b >= 1)", CLEAN_EXACT,
     'MIXED is deliberately clean -- the exact half carries the claim'),
    ("check(label_from_a_variable, len(rows) >= 3)", None,
     'a label that is not a literal is NOT JUDGED rather than judged against '
     'an empty string'),
    ("check('every row matches', got, want)", None,
     'no comparison at the call site -- the check() variant that compares '
     'inside the callee has no shape to read and must not be invented'),
    ("check('only admin may write', role in ALLOWED)", CLEAN_EXACT,
     '`in` is an exact membership test, not a floor'),
    ("check('every arm ran', ran >= total)", FINDING,
     'a floor against another variable is still a floor'),
    ("check('the seven records are soft-delete-only now', len(r) >= 7)",
     CLEAN_NO_EXHAUSTIVE,
     'a HYPHENATED compound is not an exhaustiveness claim -- \\bonly\\b '
     'matches inside soft-delete-only without the lookbehind'),
    # ── the two shapes the FIRST REAL RUN proved were false positives ───────
    ("check('every table it calls never-run is also in the queried set', "
     "set(a) <= set(b))", None,
     'SET SUBSET is the exact encoding of "every member of a is in b", not a '
     'numeric floor -- a real arm this tool wrongly reported on its first run'),
    ("check('every SKIP_REASONS entry carries a non-trivial reason', "
     "all(len(w) > 30 for w in ws))", None,
     '`all()` IS the universal quantifier; the floor inside it bounds each '
     'ELEMENT -- the other false positive from the first run'),
    ("check('every entry carries a non-trivial reason', "
     "any(len(w) > 30 for w in ws))", FINDING,
     '`any()` is an EXISTENTIAL and must NOT be exempted -- a universal label '
     'over an existential check is this defect, and the all() exemption must '
     'not widen to it'),
    ("check('every promoted checker is scored', len(rows) > 20)", FINDING,
     'the first REAL confirmed finding, kept as a fixture: a floor of 20 stays '
     'green while checkers silently disappear'),
    ("check('exactly one object is emitted, never two', objects <= 1)",
     FINDING,
     'the second REAL confirmed finding: <= 1 passes on ZERO, which is the one '
     'case the label rules out'),
    # ── the two further false-positive shapes the first real run proved ──────
    ("ok('the count tracks the keyword count in every page', "
     "min(ratio.values()) >= 0.40, ratio)", None,
     '`min(xs) >= k` IS `all(x >= k for x in xs)` -- a universal, and the '
     "author's strongest available assertion"),
    ("check('each judgment says WHY', all(len(v) > 30 for v in J.values()), "
     "str([k for k, v in J.items() if len(v) <= 30]))", None,
     'the DETAIL argument carries its own comparison and must NOT be read as '
     'the condition -- reading it reported the shape of the error message'),
    ("check('every row is scored', len(rows) > 20, 'rows=%d' % len(rows))",
     FINDING,
     '...and the detail rule must not go so far as to stop reading the real '
     'condition when a detail argument follows it'),
)

# ── THE TIER FIXTURES, locked the same way ──────────────────────────────────
# Each is a label classify() already calls FINDING. What is under test here is
# only whether the exhaustive word is the CLAIM or the RATIONALE.
TIER_FIXTURES = (
    ('every promoted checker is scored', CONFIRMED,
     'the plain shape: the universal word is the subject of the claim'),
    ('it does NOT report every one as unguarded', ADVISORY,
     'negated -- the arm asserts the opposite of a universal'),
    ('the overwhelming majority ARE named, so the rung is not reporting every '
     'action it can see', ADVISORY,
     'the word is in the rationale after "so", not in the claim'),
    ('the split is REAL -- not every commit is deployable', ADVISORY,
     'after a dash marker AND negated, either of which is enough'),
    ('a series whose mass is all at the end is caught as a ramp', ADVISORY,
     '"all at" is adverbial -- it describes position, not a population'),
    ('the set is a SUBSET of the tests on disk, not all of them', ADVISORY,
     '"not all of them" is both negated and adverbial'),
    ('all three arms fired', CONFIRMED,
     '"all three" IS a quantifier over the population and must survive the '
     'adverbial rule -- if this goes ADVISORY the rule has over-reached'),
    ('...and exactly one hookSpecificOutput object is emitted, never two',
     CONFIRMED,
     'a trailing "never two" must not demote a claim that was made before it'),
    ('every committed seed json is present in the export', CONFIRMED,
     'the second real instance shape: a universal over a file set'),
)


def run_tier_fixtures(verbose=False):
    bad = []
    for label, want, why in TIER_FIXTURES:
        got, _why = tier(label)
        if got != want:
            bad.append('TIER: expected %s, got %s -- %s\n      %s'
                       % (want, got, why, label))
        elif verbose:
            print('  ok   %-9s %s' % (want, why))
    return bad


def run_fixtures(verbose=False):
    """Classify every fixture. Returns a list of failure strings -- empty is the
    only state in which this tool may read a real file."""
    bad = []
    for src, want, why in FIXTURES:
        try:
            got_arms = arms(src)
        except SyntaxError as e:
            bad.append('fixture does not parse (%s): %s' % (e, src))
            continue
        if want is None:
            if got_arms:
                bad.append('EXPECTED NOT JUDGED, got %r -- %s\n      %s'
                           % (classify(got_arms[0][1], got_arms[0][2]), why, src))
            elif verbose:
                print('  ok   NOT JUDGED -- %s' % why)
            continue
        if not got_arms:
            bad.append('EXPECTED %s, got NOT JUDGED -- %s\n      %s'
                       % (want, why, src))
            continue
        got = classify(got_arms[0][1], got_arms[0][2])
        if got != want:
            bad.append('EXPECTED %s, got %s -- %s\n      %s'
                       % (want, got, why, src))
        elif verbose:
            print('  ok   %-38s %s' % (want, why))
    return bad


# ── THE REAL RUN ─────────────────────────────────────────────────────────────
def scan(paths):
    """(confirmed, advisory, not_judged, clean_rows, unparsed) over real files."""
    confirmed, advisory, not_judged, clean_rows, unparsed = [], [], 0, [], []
    for rel in paths:
        full = os.path.join(REPO, rel)
        try:
            with io.open(full, encoding='utf-8', errors='replace') as fh:
                src = fh.read()
        except OSError as e:
            unparsed.append('%s -- could not read: %s' % (rel, e))
            continue
        try:
            got = arms(src)
        except SyntaxError as e:
            unparsed.append('%s -- does not parse: %s' % (rel, e))
            continue
        for line, label, ops, kind in got:
            verdict = classify(label, ops)
            if verdict == FINDING:
                t, why = tier(label)
                (confirmed if t == CONFIRMED else advisory).append(
                    (rel, line, kind, label, why))
            elif verdict == CLEAN_NO_COMPARE:
                not_judged += 1
            else:
                clean_rows.append((rel, line, kind, label, verdict))
    return confirmed, advisory, not_judged, clean_rows, unparsed


def main(argv):
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.split('\n')[0])
    ap.add_argument('--fixtures', action='store_true',
                    help='run the criteria lock alone and stop -- reads no real file')
    ap.add_argument('--all', action='store_true',
                    help='also list the CLEAN rows with the reason each was cleared')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--paths', nargs='*',
                    help='override the file list (used by the control)')
    a = ap.parse_args(argv)

    if not a.quiet:
        print('ASSERTION LABEL vs COMPARISON SHAPE -- criteria %s'
              % CRITERIA_VERSION)

    # ── the lock runs FIRST and ALONE. Nothing real is read until it holds. ──
    verbose = a.fixtures and not a.quiet
    bad = run_fixtures(verbose=verbose) + run_tier_fixtures(verbose=verbose)
    total_fx = len(FIXTURES) + len(TIER_FIXTURES)
    if bad:
        if not a.quiet:
            print('\nCRITERIA LOCK FAILED -- %d of %d fixtures misclassified.'
                  % (len(bad), total_fx))
            for b in bad:
                print('  ! %s' % b)
            print('\nNOTHING REAL WAS JUDGED. A criterion that cannot classify '
                  'a hand-built\ncase correctly cannot be trusted on a real '
                  'file, and reporting a clean\nsweep here would be the exact '
                  'defect this tool exists to find.')
        return EXIT_COULD_NOT_RUN
    if not a.quiet:
        print('criteria lock: %d/%d fixtures classify correctly (%d shape, %d '
              'tier), on hand-built sources only'
              % (total_fx, total_fx, len(FIXTURES), len(TIER_FIXTURES)))
    if a.fixtures:
        return 0

    if a.paths:
        paths, notes = list(a.paths), []
    else:
        py, notes = tracked('tests/*.py', 'tests/**/*.py', 'tools/*_probe.py')
        paths = sorted(set(py))
    if not paths:
        if not a.quiet:
            print('\nNO FILES MATCHED. That is not a clean sweep -- the file '
                  'list is empty,\nwhich means the pattern or the git call '
                  'failed, not that the repo is clean.')
        return EXIT_COULD_NOT_RUN

    confirmed, advisory, not_judged, clean_rows, unparsed = scan(paths)

    if not a.quiet:
        print('read %d Python test file(s); %d arm(s) judged, %d NOT JUDGED '
              '(no comparison at the call site)'
              % (len(paths), len(confirmed) + len(advisory) + len(clean_rows),
                 not_judged))
        # ── CHECKED / UNIVERSE, PRINTED AS TWO NUMBERS WITH A NAMED GAP ──────
        # A rate over the subset you looked at is not a rate. This tool reads
        # PYTHON ONLY, so the honest denominator is not "the test suite" -- it is
        # the test suite split into what this tool can parse and what it cannot,
        # with both counted from git rather than estimated.
        _js, _ = tracked('tests/*.js', 'tests/**/*.js',
                         'api/*.test.js', 'api/**/*.test.js')
        _uni = len(paths) + len(_js)
        print('\nCHECKED / UNIVERSE: %d of %d suite files (%.0f%%).'
              % (len(paths), _uni, (100.0 * len(paths) / _uni) if _uni else 0))
        print('  The %d NOT CHECKED are JavaScript, and that is a capability gap '
              'rather than a\n  sampling choice: every arm above came from a '
              'Python `ast` parse tree, for the\n  reason checker_control_check.py '
              'rebuilt itself in 2026-09-13 -- patterns over\n  text counted '
              'docstrings, path constants and print calls as evidence. A clean\n'
              '  verdict here says NOTHING about tests/*.js or api/**/*.test.js.'
              % len(_js))
        print('  BOTH FIGURES ARE COUNTED FROM `git ls-files`, so the gap moves '
              'when the repo\n  does and cannot be quoted stale from a document.')
        for n in notes:
            print('  excluded: %s' % n)
        # TWO NUMBERS, NEVER SUMMED. Printed BEFORE the findings so a reader
        # cannot take the CONFIRMED count for the total.
        print('\nTIERS: %d CONFIRMED, %d ADVISORY. These are not added '
              'together anywhere.\n  ADVISORY means the exhaustive word is '
              'negated, adverbial, or sitting in\n  the rationale rather than '
              'the claim -- readable in seconds, and NOT a finding.'
              % (len(confirmed), len(advisory)))
        if advisory:
            print('\nADVISORY (%d) -- listed so the demotion is auditable '
                  'rather than silent:' % len(advisory))
            for rel, line, _k, label, why in advisory:
                print('  ~ %s:%d  %s\n      %s' % (rel, line, why, label[:140]))
        if a.all:
            print('\nCLEARED (%d) -- with the reason each was cleared, so a '
                  'wrong exemption is visible:' % len(clean_rows))
            for rel, line, kind, label, verdict in clean_rows:
                print('  - %s:%d  %s\n      %s' % (rel, line, verdict, label[:120]))

    return finish(
        ['%s:%d  %s label claims a universal, comparison is one-sided only\n'
         '      %s' % (rel, line, kind, label[:160])
         for rel, line, kind, label, _w in confirmed],
        could_not_run=unparsed, quiet=a.quiet,
        clean_line='\nCLEAN -- no Python arm labels an exhaustive claim while '
                   'comparing one-sidedly.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
