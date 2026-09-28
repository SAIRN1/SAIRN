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
  * JAVASCRIPT IS COVERED AS OF 2026-09-29 -- this bullet used to say it was not,
    and it was the largest thing this tool could not see (464 of 807 suite
    files). Python arms come from a real `ast` parse; JS arms come from a
    balanced-paren scan over a copy with comments stripped, STRING INTERIORS
    BLANKED by the canonical offset-preserving checker_kit.strip_comments, and
    REGEX BODIES blanked on top of that. Both feed the SAME classify() and
    tier(). What is still NOT read: a JS file whose two stripped copies differ in
    length is REFUSED to COULD NOT RUN rather than counted clean, an assertion
    whose label is built only from variables yields no arm, and an argument list
    carrying two operator-bearing arguments is NOT JUDGED rather than guessed.

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
# `only N of M`, and `only N thing(s) found` -- both REPORT A QUANTITY rather than
# claim exclusivity, and both appeared in the first real JavaScript run on arms
# whose own comments say "this is a floor, not an equality".
#
# The second tell is mechanical rather than a word list: a concatenated label has
# its interpolations joined as WHITESPACE by _joined_strings(), so
# `'only ' + n + ' call sites'` arrives as "only   call sites". TWO OR MORE SPACES
# after `only` therefore means a value was interpolated there, which is a count
# being printed and not a population being claimed.
PARTITIVE_OF = re.compile(r"(\s{2,}|[^.;]{0,40}?\bof\b)", re.I)
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
        # PARTITIVE `only`, found by the first real JavaScript run. `only N of M
        # were postable` REPORTS A FRACTION; it does not claim exclusivity, and
        # the arm it came from (ledger.test.js:330) says in its own comment
        # "this is a floor, not an equality" and is right to. Narrow on purpose:
        # `only` specifically, and only when ` of ` follows close behind.
        if m.group(0).lower() == 'only' and PARTITIVE_OF.match(after):
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


# ════════════════════════════════════════════════════════════════════════════
# THE JAVASCRIPT HALF -- ADDED 2026-09-29, AND IT IS 75% OF THE GAP
# ════════════════════════════════════════════════════════════════════════════
# The Python path covered 343 of 807 suite files and this header called the other
# 464 a CAPABILITY GAP. Ranked by assertion idiom, that gap is not 464 problems:
#
#     node:assert  assert.X(cond, LABEL)        346 files   <- 75% of the gap
#     node:test    test(NAME, fn)               259
#     local        check(LABEL, cond, ...)       87
#     local        ok(LABEL, cond, ...)          30
#     no recognised idiom                        15
#     eq(LABEL, got, want)                        5
#
# ONE extractor -- the argument list of a call carrying both a string literal and
# a comparison -- covers the 346, and picks up check()/ok()/eq()/ck() for free
# because the shape is identical. That is the cheapest extension covering the
# largest block, and it is why this is a day of work rather than a JS parser.
#
# ── WHY NOT A JS PARSER, AND WHY THIS IS NOT THE AD-HOC REGEX IT LOOKS LIKE ──
# There is no JS ast in the standard library and vendoring one for a report-only
# checker is not proportionate. But text matching here carries exactly the danger
# checker_control_check.py rebuilt itself around in September: a docstring, a path
# constant or a print call counted as evidence.
#
# That danger is removed STRUCTURALLY, not by pattern care:
#   * comments stripped and STRING INTERIORS BLANKED by
#     checker_kit.strip_comments(src, strings=True) -- the canonical,
#     OFFSET-PRESERVING implementation. A comparison operator found in the blanked
#     text is real code and cannot be prose. `//` inside a URL and `/*` inside
#     "image/*" are already handled there; this file adds no stripper of its own.
#   * the argument list is read by BALANCED-PAREN SCAN over the blanked text, so a
#     nested call, an object literal or a paren inside a string cannot truncate the
#     split the way a comma regex would.
#   * the LABEL is read from the comment-stripped-but-NOT-blanked copy at the SAME
#     OFFSETS, and js_arms() REFUSES to read anything if the two copies are not the
#     same length -- a misaligned pair would attribute one arm label to another
#     arm comparison, which is a confident wrong answer rather than a miss.
#
# ── ONE CRITERION, TWO EXTRACTORS ───────────────────────────────────────────
# The label tests (EXHAUSTIVE, ONE_SIDED_DECLARED) and tier() are UNCHANGED and
# SHARED. A JS arm and a Python arm are judged by the same rules in the same
# order, so the locked fixtures bound both languages and the criterion cannot
# drift between them.
JS_CALLS = ('assert.ok', 'assert.strictEqual', 'assert.deepStrictEqual',
            'assert.equal', 'assert.notStrictEqual', 'check', 'ok', 'eq', 'ck')
JS_EXACT_OPS = ('===', '!==', '==', '!=')
JS_ONE_SIDED_OPS = ('>=', '<=', '>', '<')
# LONGEST FIRST. If `>` were tried before `>=`, every `>=` would also register as
# a one-sided `>` and -- worse -- `===` would register as `==`, which decides the
# exact-versus-one-sided question on the wrong token.
JS_OP_ORDER = ('===', '!==', '>=', '<=', '==', '!=', '>', '<')
QUOTES = chr(39) + chr(34) + chr(96)   # ' " `


def _balanced(src, open_at):
    """Index just past the ) matching the ( at open_at, or None.

    Runs on the STRING-BLANKED text, so a paren inside a string literal cannot
    unbalance it. That is the whole reason the blanked copy exists.
    """
    depth = 0
    for k in range(open_at, len(src)):
        c = src[k]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
            if depth == 0:
                return k + 1
    return None


def _split_top(seg):
    """Top-level comma split of an argument-list body, as (start, end) pairs."""
    out, depth, start = [], 0, 0
    for k, c in enumerate(seg):
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif c == ',' and depth == 0:
            out.append((start, k))
            start = k + 1
    out.append((start, len(seg)))
    return out


def _js_ops(text):
    """Comparison operators in one argument, longest-match-first."""
    found, i = [], 0
    while i < len(text):
        for op in JS_OP_ORDER:
            if text.startswith(op, i):
                found.append(op)
                i += len(op)
                break
        else:
            i += 1
    return found


# Callbacks whose body bounds ONE ELEMENT, not the population. A `> 40` inside
# `.filter(r => r.quote.length > 40)` is the JS spelling of Python's
# `all(len(x) > 40 for x in xs)`, which the ast path already exempts: the
# universality is carried by the iterator, not by the comparison. Reading the
# comparison instead reports a per-element bound as a population floor.
ELEMENT_CALLBACKS = ('.filter(', '.map(', '.every(', '.some(', '.find(',
                     '.findIndex(', '.forEach(', '.reduce(', '.flatMap(',
                     '.sort(')


def _strip_element_predicates(text):
    """Blank the argument list of every per-element callback in `text`.

    Blanked rather than removed so nothing shifts: a caller reading offsets in
    the result would otherwise be reading a different string.
    """
    out = list(text)
    for name in ELEMENT_CALLBACKS:
        k = 0
        while True:
            i = text.find(name, k)
            if i < 0:
                break
            k = i + 1
            op = i + len(name) - 1
            end = _balanced(text, op)
            if end is None:
                continue
            for j in range(op + 1, end - 1):
                out[j] = ' '
    return ''.join(out)


# ── REGEX LITERALS MUST BE BLANKED TOO, AND checker_kit DOES NOT DO IT ──────
# FOUND BY THE FIRST REAL RUN. `/<th>Unit<\/th>/.test(src)` reported a one-sided
# comparison because the `<` in `<th>` is not an operator -- it is markup inside a
# regex. checker_kit.strip_comments blanks STRING interiors (three quote
# characters) and leaves regex bodies standing, which is correct for its own
# subject and wrong for this one.
#
# Whether a `/` opens a regex is decided from the previous significant character,
# the same heuristic tests/lib/strip_comments.js carries for the same reason. The
# direction of its error is chosen: anything unrecognised stays DIVISION, so this
# can only ever under-blank. Under-blanking leaves a spurious operator and shows
# up as a reviewable finding; over-blanking would hide a real one.
_REGEX_OK_PREV = '(,=:[!&|?{};^'


def _quoted_spans(text):
    """(start, end) of every quoted run in `text`, on the UNBLANKED copy."""
    spans, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in QUOTES:
            q, j = c, i + 1
            while j < n:
                if text[j] == chr(92):
                    j += 2
                    continue
                if text[j] == q:
                    break
                j += 1
            spans.append((i, min(j, n)))
            i = j + 1
            continue
        i += 1
    return spans


def _is_quoted_fragment(text):
    """True when `text` contains at least one quoted run -- a concatenated label."""
    return bool(_quoted_spans(text))


def _joined_strings(text):
    """Every quoted fragment of a concatenation, joined -- the label as written."""
    return ' '.join(text[a + 1:b] for a, b in _quoted_spans(text)).strip()


def _blank_regex_literals(text):
    """Blank regex-literal bodies in `text`, preserving length.

    Runs on the already-string-blanked copy, so a `/` inside a string literal is
    gone before this looks at anything.
    """
    out = list(text)
    i, prev = 0, ''
    n = len(text)
    while i < n:
        c = text[i]
        if c == '/' and (prev in _REGEX_OK_PREV or prev == ''):
            # not a comment -- comments are already gone by this point
            j, in_class = i + 1, False
            while j < n:
                d = text[j]
                if d == chr(92):
                    j += 2
                    continue
                if d == '[':
                    in_class = True
                elif d == ']':
                    in_class = False
                elif d == chr(10):
                    break                      # unterminated: do not run away
                elif d == '/' and not in_class:
                    j += 1
                    break
                j += 1
            for k in range(i + 1, min(j, n)):
                if out[k] != chr(10):
                    out[k] = ' '
            i = j
            prev = '/'
            continue
        if not c.isspace():
            prev = c
        i += 1
    return ''.join(out)


# An argument that IS a function is a test BODY, not a condition. `check(NAME,
# () => { ... })` and `test(NAME, function () { ... })` put every operator in the
# body inside the callee's scope, and reading them reports the shape of a test
# body as the shape of an assertion -- dnt-rollup.test.js:382 on the first real
# run, whose label is a sentence about floating point and whose second argument is
# an arrow function.
def _is_function_arg(text):
    """True when the ARGUMENT ITSELF is a function, not merely contains one.

    The first version tested for `=>` anywhere on the first line and therefore
    swallowed `rows.filter(r => r.n > 40).length >= 3` -- a real population floor
    with a per-element callback inside it, which is exactly the case a fixture
    was written to protect. Per-element callbacks are blanked FIRST, so what
    remains is the argument's own shape.
    """
    t = _strip_element_predicates(text).strip()
    return (t.startswith('function') or t.startswith('async')
            or t.startswith('()')
            or re.match(r'^[A-Za-z_$][\w$]*\s*=>', t) is not None
            or re.match(r'^\([^()]*\)\s*=>', t) is not None)


def _is_quoted(raw):
    raw = raw.strip()
    return len(raw) >= 2 and raw[0] in QUOTES and raw[-1] == raw[0]


def js_arms(src):
    """(line, label, ops, kind) per readable assertion, or None if unreadable.

    Mirrors arms() for Python: an arm is a call carrying BOTH a string literal and
    a separate ADJACENT argument containing a comparison. Anything else is NOT
    JUDGED rather than guessed at.
    """
    from checker_kit import strip_comments as _strip
    bare = _strip(src)                      # comments gone, strings intact
    blank = _strip(src, strings=True)       # comments gone, string bodies blanked
    if len(bare) != len(src) or len(blank) != len(src):
        return None
    blank = _blank_regex_literals(blank)    # ...and regex bodies, see above
    if len(blank) != len(src):
        return None
    out, seen = [], set()
    for name in JS_CALLS:
        needle = name + '('
        start = 0
        while True:
            i = blank.find(needle, start)
            if i < 0:
                break
            start = i + 1
            # A CALL, NOT A SUFFIX: `recheck(` must not match `check(`.
            if i > 0 and (blank[i - 1].isalnum() or blank[i - 1] in '_$.'):
                continue
            op = i + len(name)
            end = _balanced(blank, op)
            if end is None or (op, end) in seen:
                continue
            seen.add((op, end))
            body_b = blank[op + 1:end - 1]
            body_r = bare[op + 1:end - 1]
            args = _split_top(body_b)
            label, label_i = None, None
            for n, (a, b) in enumerate(args):
                raw = body_r[a:b]
                # CONCATENATION FIRST. `'only ' + n + ' found'` also starts and
                # ends with a quote, so the simple test swallows the whole
                # expression and hands the interpolation syntax to the label
                # tests -- which is how `only ' + found.length + ' call site(s)`
                # kept reading as an exclusivity claim after the partitive rule
                # was added. More than one quoted run means a concatenation.
                if len(_quoted_spans(raw)) > 1:
                    label, label_i = _joined_strings(raw), n
                    break
                if _is_quoted(raw):
                    label, label_i = raw.strip()[1:-1], n
                    break
                # A CONCATENATED LABEL IS STILL THE LABEL, and reading only its
                # first fragment changes what the label says. ledger.test.js:330's
                # message is `'only ' + postable + ' of ' + checked + ' were
                # postable...'`; the first fragment alone is "only ", which trips
                # the exhaustive test on a word that is partitive in the full
                # sentence. Mirrors Python's _str_of() BinOp handling.
                if '+' in raw and _is_quoted_fragment(raw):
                    label, label_i = _joined_strings(raw), n
                    break

            if label is None:
                continue
            # ── THE VALUE-COMPARISON FORM HAS NO SHAPE AT THE CALL SITE ─────
            # FOUND BY THE FIRST REAL RUN, which reported 171 CONFIRMED -- most of
            # them this. `check(LABEL, got, want)` and
            # `assert.strictEqual(a, b, MSG)` do the comparison INSIDE the callee,
            # so there is no operator at the call site to read and the Python path
            # gives exactly the same answer: NOT JUDGED. Reading the `got`
            # expression instead finds whatever operators happen to be inside it
            # -- typically a per-element predicate -- and reports the shape of a
            # FILTER as the shape of the assertion.
            #
            # Detected by counting NON-STRING arguments: two or more of them means
            # the callee is comparing them, and inventing a shape would be a
            # confident wrong answer rather than a miss.
            # COUNTING ARGUMENTS THAT CARRY AN OPERATOR, not arguments that are
            # not strings. The first version counted non-strings and refused
            # `check(LABEL, fired >= 3, sprintf('%d', n))` -- a real condition with
            # a CALL as its detail, which is indistinguishable from
            # `check(LABEL, got, want)` by argument type alone. The operator is
            # what distinguishes them: a condition carries one, a `got` expression
            # does not.
            #
            # ZERO means the callee compares (no shape here). TWO OR MORE is
            # genuinely ambiguous and is NOT JUDGED rather than guessed -- erring
            # toward silence, because inventing a shape is a confident wrong
            # answer and missing one is a miss.
            carriers = []
            for n, (a, b) in enumerate(args):
                if _is_quoted(body_r[a:b]) or _is_function_arg(body_r[a:b]):
                    continue
                if _js_ops(_strip_element_predicates(body_b[a:b])):
                    carriers.append(n)
            if len(carriers) != 1:
                continue
            cand = body_b[args[carriers[0]][0]:args[carriers[0]][1]]
            ops = _js_ops(_strip_element_predicates(cand))
            if ops:
                out.append((blank.count(chr(10), 0, i) + 1, label, ops, 'js'))
    return out


def js_classify(label, ops):
    """classify() for JS operator STRINGS rather than ast nodes.

    A thin translation onto the SAME decision order, deliberately: exact wins,
    then one-sided, then the label tests. Anything else would let the two
    languages disagree about identical code.
    """
    if not ops:
        return CLEAN_NO_COMPARE
    if any(o in JS_EXACT_OPS for o in ops):
        return CLEAN_EXACT
    if not any(o in JS_ONE_SIDED_OPS for o in ops):
        return CLEAN_NO_COMPARE
    if not EXHAUSTIVE.search(label or ''):
        return CLEAN_NO_EXHAUSTIVE
    if ONE_SIDED_DECLARED.search(label or ''):
        return CLEAN_DECLARED
    return FINDING


# ── THE JS FIXTURE LOCK, held to the same standard as the Python one ────────
JS_FIXTURES = (
    ("assert.ok(rows.length >= 12, 'every section yields requirements');",
     FINDING, 'the named shape, in JS: a universal label behind a floor'),
    ("assert.ok(rows.length === 12, 'every section yields requirements');",
     CLEAN_EXACT, 'an exact count under the same label is the correct shape'),
    ("assert.ok(rows.length >= 12, 'at least 12 sections yield requirements');",
     CLEAN_NO_EXHAUSTIVE, 'an honest ratchet has no universal word'),
    ("assert.ok(n > prev, 'the count grew since the last run');",
     CLEAN_NO_EXHAUSTIVE, 'no exhaustive claim, so one-sidedness is not a '
     'contradiction'),
    ("check('every arm fired', fired >= 3, 'detail');",
     FINDING, 'the local check() idiom is the same shape and must be read too'),
    ("check('every arm fired', fired >= 3, sprintf('%d of %d', a, b));",
     FINDING, 'a DETAIL argument containing a call must not break the balanced '
     'scan -- a comma regex would have split inside sprintf()'),
    ("assert.ok(u === 'https://x/*y' , 'every url is absolute');",
     CLEAN_EXACT, 'a URL and an image/* glob inside a STRING must not be read as '
     'a comment or an operator -- the blanked copy is what makes this safe'),
    ("// assert.ok(rows.length >= 3, 'every row is present');",
     None, 'a COMMENTED-OUT assertion is NOT an arm -- this is the docstring '
     'failure checker_control_check rebuilt itself around, in JS'),
    ("assert.ok(rows.length >= 3, 'every row is present'); "
     "// assert.ok(x >= 1, 'every other row too');",
     FINDING, '...and a real arm beside a commented-out one is still read'),
    ("recheck('every arm fired', fired >= 3);",
     None, '`recheck(` must not match `check(` -- a suffix is not a call'),
    # ── THE TWO SHAPES THE FIRST REAL RUN PROVED WERE FALSE POSITIVES ────────
    ("check('every rule cites its own PDF and a verbatim quote', "
     "seed.rules.filter(r => r.quote && r.quote.length > 40).length, 11);",
     None, 'THE VALUE-COMPARISON FORM: two non-string arguments means the callee '
     'compares them, so there is no shape at the call site -- reading the `got` '
     'expression found the filter predicate and reported 171 CONFIRMED on the '
     'first real run, most of them this'),
    ("assert.ok(rows.every(r => r.n > 40), 'every row is over the bar');",
     None, 'A PER-ELEMENT PREDICATE is the JS spelling of Python `all(...)`: the '
     'universality is carried by .every(), not by the comparison inside it, and '
     'the ast path already exempts the Python form'),
    ("assert.ok(rows.filter(r => r.n > 40).length >= 3, 'every row is over the bar');",
     FINDING, '...but a per-element predicate does NOT exempt a floor on the '
     'OUTER count -- the >= 3 is still a population claim behind a universal '
     'label, and blanking the callback must not blank that too'),
    ("assert.strictEqual(rows.length, 12, 'every section yields requirements');",
     None, 'the value-comparison form has no operator at the call site, so there '
     'is no shape to read, no arm is produced, and none is invented -- the same '
     'answer the Python path gives check(label, got, want)'),
)


def run_js_fixtures(verbose=False):
    bad = []
    for src, want, why in JS_FIXTURES:
        got_arms = js_arms(src)
        if got_arms is None:
            bad.append('JS: extractor refused to read the fixture -- %s' % why)
            continue
        if want is None:
            if got_arms:
                bad.append('JS: EXPECTED NOT JUDGED, got %r -- %s'
                           % (js_classify(got_arms[0][1], got_arms[0][2]), why))
            elif verbose:
                print('  ok   %-38s %s' % ('NOT JUDGED', why))
            continue
        if not got_arms:
            bad.append('JS: EXPECTED %s, got NOT JUDGED -- %s' % (want, why))
            continue
        got = js_classify(got_arms[0][1], got_arms[0][2])
        if got != want:
            bad.append('JS: EXPECTED %s, got %s -- %s' % (want, got, why))
        elif verbose:
            print('  ok   %-38s %s' % (want, why))
    return bad


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
def scan(paths, js_paths=()):
    """(confirmed, advisory, not_judged, clean_rows, unparsed) over real files.

    Python and JavaScript go through the SAME classify()/tier() pair and differ
    only in the extractor, so a finding means the same thing in both languages.
    """
    confirmed, advisory, not_judged, clean_rows, unparsed = [], [], 0, [], []
    for rel in js_paths:
        full = os.path.join(REPO, rel)
        try:
            with io.open(full, encoding='utf-8', errors='replace') as fh:
                src = fh.read()
        except OSError as e:
            unparsed.append('%s -- could not read: %s' % (rel, e))
            continue
        got = js_arms(src)
        if got is None:
            # THE OFFSET REFUSAL. Not folded into clean: a file whose two
            # stripped copies disagree in length was NOT read, and reading it
            # anyway would attribute one arm's label to another's comparison.
            unparsed.append('%s -- the stripped copies differ in length, so no '
                            'arm could be read safely' % rel)
            continue
        for line, label, ops, kind in got:
            verdict = js_classify(label, ops)
            if verdict == FINDING:
                t, why = tier(label)
                (confirmed if t == CONFIRMED else advisory).append(
                    (rel, line, kind, label, why))
            elif verdict == CLEAN_NO_COMPARE:
                not_judged += 1
            else:
                clean_rows.append((rel, line, kind, label, verdict))
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
    bad = (run_fixtures(verbose=verbose) + run_tier_fixtures(verbose=verbose)
           + run_js_fixtures(verbose=verbose))
    total_fx = len(FIXTURES) + len(TIER_FIXTURES) + len(JS_FIXTURES)
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
              'tier, %d javascript), on hand-built sources only'
              % (total_fx, total_fx, len(FIXTURES), len(TIER_FIXTURES),
                 len(JS_FIXTURES)))
    if a.fixtures:
        return 0

    if a.paths:
        paths = [p for p in a.paths if p.endswith('.py')]
        js_paths = [p for p in a.paths if p.endswith('.js')]
        notes = []
    else:
        py, notes = tracked('tests/*.py', 'tests/**/*.py', 'tools/*_probe.py')
        paths = sorted(set(py))
        js, _jsnotes = tracked('tests/*.js', 'tests/**/*.js',
                               'api/*.test.js', 'api/**/*.test.js')
        js_paths = sorted(set(js))
    if not paths and not js_paths:
        if not a.quiet:
            print('\nNO FILES MATCHED. That is not a clean sweep -- the file '
                  'list is empty,\nwhich means the pattern or the git call '
                  'failed, not that the repo is clean.')
        return EXIT_COULD_NOT_RUN

    confirmed, advisory, not_judged, clean_rows, unparsed = scan(
        paths, js_paths=js_paths)

    if not a.quiet:
        print('read %d Python and %d JavaScript suite file(s); %d arm(s) '
              'judged, %d NOT JUDGED (no comparison at the call site)'
              % (len(paths), len(js_paths),
                 len(confirmed) + len(advisory) + len(clean_rows), not_judged))
        # ── CHECKED / UNIVERSE, PRINTED AS TWO NUMBERS WITH A NAMED GAP ──────
        # A rate over the subset you looked at is not a rate. This tool reads
        # PYTHON ONLY, so the honest denominator is not "the test suite" -- it is
        # the test suite split into what this tool can parse and what it cannot,
        # with both counted from git rather than estimated.
        _checked = len(paths) + len(js_paths)
        print('\nCHECKED / UNIVERSE: %d of %d suite files (%.0f%%).'
              % (_checked, _checked, 100.0 if _checked else 0))
        print('  THE JAVASCRIPT GAP IS CLOSED AS OF 2026-09-29. It was 343 of 807 '
              '(43%), and the\n  464 uncovered files were named in this header as a '
              'CAPABILITY gap rather than a\n  sampling choice. Ranked by assertion '
              'idiom, 346 of those 464 used one shape --\n  assert.X(cond, LABEL) '
              '-- so ONE extractor closed three quarters of it, and the\n  same '
              'extractor picked up check()/ok()/eq() for free.')
        print('  PYTHON GOES THROUGH `ast`; JAVASCRIPT GOES THROUGH A BALANCED '
              'SCAN over a copy\n  with comments stripped and STRING INTERIORS '
              'BLANKED by the canonical,\n  offset-preserving '
              'checker_kit.strip_comments. Both feed the SAME classify() and\n'
              '  tier(), so a finding means the same thing in either language and '
              'the locked\n  fixtures bound both.')
        print('  WHAT IS STILL NOT READ, and it is not zero: a JS file whose two '
              'stripped copies\n  differ in length is REFUSED and listed under '
              'COULD NOT RUN rather than counted\n  clean, and an assertion whose '
              'label is built from variables yields no arm at all.\n  Both figures '
              'come from `git ls-files`, so the denominator moves with the repo.')
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
        # NAMES BOTH LANGUAGES. It said "no Python arm" while the JavaScript
        # half of the run was already feeding the same classify(), so a clean
        # verdict understated its own scope -- the mirror of the failure this
        # tool exists to catch, in the tool's own summary line.
        clean_line='\nCLEAN -- no Python or JavaScript arm labels an exhaustive '
                   'claim while comparing one-sidedly.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
