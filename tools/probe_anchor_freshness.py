"""
A FAULT PROBE WHOSE SABOTAGE ANCHOR NO LONGER MATCHES ITS SUBJECT.

Fast: parses the probes with `ast` and counts strings. Runs no worktree, plants
no mutation, and takes under a second -- which is the point, because the probes
themselves take minutes each and are therefore run when somebody remembers.

── WHY (2026-09-27) ────────────────────────────────────────────────────────
`tests/sairncash_entitlement_fault_probe.py` had been dead since `a100c078`.
That commit -- "the offline fallback was unbounded: a blocked request meant yes
forever" -- inserted an `scGraceOk(s)` check into the exact catch block one arm
anchored on, turning three lines into eight. The probe's `once()` helper refused
the anchor, the file exited non-zero on its FIRST arm, and two arms never ran.

THE ANCHOR DID NOT DRIFT TO MATCHING THE WRONG THING. It stopped matching
anything, which is the LOUD failure -- and nobody heard it, because no fault
probe on this platform is in `report_only_checks.REGISTRY`, in the push gate,
or in any hook. A loud failure in a tool nobody invokes is exactly as quiet as
a silent one. That is the finding, and it is why this checker is fast rather
than thorough: something that takes a second can be wired.

TWO STALE ANCHORS WERE FOUND THE DAY THIS WAS WRITTEN, and they failed in
OPPOSITE directions, which is why this counts matches rather than testing
presence:

  * sairncare_fault_probe.py   -- `const ALF_MAR_ROLES = { owner: true, ... }`
    matched ZERO places. `dadfedf4` wrapped all 48 role maps in `roleSet(...)`
    for a null prototype, so the literal the anchor spans no longer exists.
  * sairnmechanical_fault_probe.py -- `if (lb === null || lb < 0) {` matched
    THREE places. Not gone: AMBIGUOUS. `replace(old, new, 1)` would have
    silently mutated whichever came first, and the probe would have reported a
    pass or a failure about a line nobody chose.

NO PROBE-POPULATION TALLY IS CARRIED HERE, AND THE FIRST DRAFT'S WAS WRONG.
It read "10 green, TWO with stale anchors, one with a red baseline" -- 13, each
probe in exactly one bucket. The buckets are not exclusive: re-anchoring
sairncare and then RUNNING it showed its baseline is red too, so it belonged in
two at once and the tally could not have been right whichever way it was read.
The red is not an anchor problem and is not this tool's to fix -- `c8b5e5b1`
("131 of 132 credential gates closed in ONE edit") added a pre-gate that calls
`verifySessionToken(preToken, licHash)` with no expectedApp, and twelve suites
stub that function to THROW on an unnamed app. Bisected 2026-09-27: green at
`c8b5e5b1~1`, 0-passed-20-failed at `c8b5e5b1`. Counting probes is cheap and
this tool does print its own totals per run; asserting a durable census in a
docstring is what went wrong, so the census lives in the run output only.

ZERO and MORE-THAN-ONE are both refusals and this reports them separately,
because the fix differs: a vanished anchor needs re-deriving against what the
code became, an ambiguous one needs widening.

── WHAT IT CANNOT SEE, printed on every run ───────────────────────────────
See BLIND_SPOTS. The largest by far: AN ANCHOR THAT STILL MATCHES ONCE MAY
STILL BE POINTING AT THE WRONG THING. This counts strings; it does not know
what a line is for. PR 1.3 is exactly that failure and this checker cannot
detect it -- only running the probe can.

CLI:
    python tools/probe_anchor_freshness.py
    python tools/probe_anchor_freshness.py --json
    python tools/probe_anchor_freshness.py --selftest
"""
import ast
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The helper names probes use to plant a mutation. Derived by reading the
# probes rather than guessed: every one of them passes (subject, old, new)
# tuples to a local function with one of these names.
ARM_CALLS = ('arm', 'mutate', 'sabotage', 'plant')

# ── STAMPED, BECAUSE THE CRITERIA CHANGED ONCE AND WILL AGAIN ──────────────
# `tools/sabotage_control_check.py` carries a CRITERIA_VERSION for exactly this
# reason: it once scored five well-written controls as unguarded because it knew
# only ONE spelling of a correct answer, and the fix was a criteria change rather
# than a bug fix. A result quoted from this tool is only comparable to another
# result under the SAME criteria, so the version is printed on every run and in
# the --json payload. Do not compare a count across versions.
#
#   1  2026-09-27  first version. An anchor is correct iff it matches exactly
#                  once. Reported 5 AMBIGUOUS, of which FOUR were false.
#   2  2026-09-27  the 4-element edit form `(SUBJECT, old, new, N)` declares its
#                  own expected count and replaces ALL occurrences, which is
#                  STRICTLY STRONGER than uniqueness. Those are now held to N
#                  rather than to 1, and a disagreement with N is its own
#                  verdict (COUNT DISAGREES) rather than being folded into
#                  AMBIGUOUS. Remaining real finding after the change: 1.
CRITERIA_VERSION = '2026-09-27.2'

BLIND_SPOTS = [
    'AN ANCHOR THAT STILL MATCHES ONCE MAY STILL BE POINTING AT THE WRONG '
    'THING. This counts strings and does not know what a line is FOR. That is '
    'PR 1.3 and only running the probe can catch it.',
    'Only anchors passed as a LITERAL string in a call to %s are seen. An '
    'anchor built by concatenation, an f-string, or read from a variable is '
    'invisible here and is not reported as unchecked -- it is simply absent '
    'from the count.' % '/'.join(ARM_CALLS),
    'The subject path must be a module-level string assignment this can '
    'resolve. A probe that computes its subject path is skipped, and the skip '
    'is PRINTED rather than folded into the pass count.',
    'A probe whose BASELINE is red is not a stale-anchor problem and is '
    'invisible here -- its subject suite fails, so it stops before any '
    'mutation and every anchor in it could be perfect. Two were red the day '
    'this was written: tests/sairnlegacy_fault_probe.py, and '
    'tests/sairncare_fault_probe.py once its anchors were fixed and it could '
    'run far enough to show it. A GREEN REPORT HERE IS NOT A WORKING PROBE.',
    'It says nothing about whether the probe is WIRED. On the day this was '
    'written, NONE of the 13 fault probes was in report_only_checks.REGISTRY, '
    'the push gate, or any hook.',
]


def tracked_probes():
    """Probe files under tests/, from git rather than a walk."""
    try:
        p = subprocess.run(['git', 'ls-files', 'tests/'], cwd=REPO,
                           capture_output=True, timeout=60)
        if p.returncode != 0:
            return None
        names = (p.stdout or b'').decode('utf-8', 'replace').split('\n')
    except Exception:
        return None
    return [n.strip() for n in names
            if n.strip().endswith('.py') and ('probe' in n or 'control' in n)]


def read(path):
    try:
        return io.open(os.path.join(REPO, path), encoding='utf-8',
                       newline='').read()
    except Exception:
        return None


def lf(text):
    r"""Carriage returns removed before any comparison.

    A CRLF-VS-LF DIFFERENCE IS NOT DRIFT, and this tool produced two false
    VANISHED rows before it did this. The probes read their subject out of a
    fresh `git worktree add`, where `.gitattributes` gives them LF; this clone's
    working tree holds CRLF for the same files. So an anchor written with `\n`
    matched perfectly inside the probe and matched zero times here -- on files
    whose probes were passing at the time.

    CLAUDE.md names this exact trap and the three false alarms it caused in one
    session on 2026-09-03. Comparing without normalising would have had this
    checker reporting healthy probes as broken, which is the failure mode that
    gets a checker switched off.
    """
    return (text or '').replace('\r', '')


def _path_literal(node):
    """A file path from a Constant, or from os.path.join('a','b') -- nothing else.

    THE JOIN FORM IS THE COMMON ONE AND THE FIRST VERSION OF THIS MISSED IT.
    Every fault probe declares its subject as `os.path.join('api', 'sd-data.js')`
    for Windows, and reading only Constants meant those probes resolved to
    nothing -- so their anchors landed in "not a resolvable literal" and were
    never counted. That is precisely where the two REAL stale anchors were: this
    tool's first run reported zero vanished anchors while two were known to
    exist, found by running the probes. A sweep that misses the instances that
    motivated it is worse than no sweep, because it reads as a clean bill.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Call):
        fn = node.func
        is_join = (getattr(fn, 'attr', None) == 'join'
                   and getattr(getattr(fn, 'value', None), 'attr', None) == 'path')
        if is_join and node.args and all(
                isinstance(a, ast.Constant) and isinstance(a.value, str)
                for a in node.args):
            return '/'.join(a.value for a in node.args)
    return None


def subject_names(tree):
    """{VARNAME: 'path/to/file'} from module-level assignments."""
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        val = _path_literal(node.value)
        if not val or not val.endswith(('.js', '.html', '.py', '.sql', '.json')):
            continue
        for t in node.targets:
            if isinstance(t, ast.Name):
                out[t.id] = val
    return out


def sole_subject(names):
    """The one subject a 2-tuple `(old, new)` edit must mean.

    Some probes carry a single subject and pass `(old, new)` with no path --
    tests/sairnsenior_fault_probe.py does. The first version of this read those
    as `(subject, old)` and reported nine COULD-NOT-CHECK rows that were not
    findings at all, just a misparse. If a probe has more than one plausible
    subject this returns None and the row is reported as unresolved, because
    guessing which file a 2-tuple meant is exactly the ambiguity this whole
    checker exists to refuse.
    """
    app = [v for v in names.values() if v.endswith('.html')]
    return app[0] if len(app) == 1 else None


def declared_count(elt):
    """The DECLARED occurrence count from a 4-element edit tuple, or None.

    ── THE INVERSION THIS CLOSES, AND IT IS THE SECOND TIME ────────────────
    `tests/sairndesign_sairngrounds_fault_probe.py` writes some edits as a FOUR
    element tuple -- `(SUBJECT, old, new, 6)` -- and its helper is

        def all_n(rel, needle, expect):
            n = ORIG[rel].count(needle)
            assert n == expect, 'fixture invalid: ... expected %d'
            return needle

    ...then replaces EVERY occurrence. That is STRICTLY STRONGER than the
    uniqueness guard this checker was built around: it asserts the exact number
    and refuses on any drift in either direction, up or down. A rename that must
    stay consistent across a file legitimately touches many places; the rule the
    platform actually adopted is "know how many you are hitting", not "it must be
    exactly one".

    THE FIRST VERSION OF THIS CHECKER REPORTED ALL FOUR OF THOSE AS AMBIGUOUS.
    Four well-written anchors read as broken, and a probe that did the harder
    thing scored worse -- which is EXACTLY the failure
    `tools/sabotage_control_check.py` shipped when it did not recognise the
    `count(anchor) != 1` guard and reported five guarded controls as unguarded.
    The signal was inverted there and it was inverted here, on the next tool,
    for the same reason: the criteria encoded ONE spelling of a correct answer.

    So a declared count changes the VERDICT, not just the message: with one, the
    right outcome is `count == expect` and a match total above 1 is correct
    rather than a finding. A mismatch is its own row -- see COUNT DISAGREES.

    A NON-LITERAL COUNT IS NOT GUESSED. `(SUBJECT, old, new, n)` where `n` is a
    variable returns None and the edit falls back to the uniqueness rule, which
    is the wrong rule for it -- so it is reported as unresolved instead, because
    a checker that quietly applied the stricter rule to an edit whose declared
    count it could not read would be inventing the criteria.
    """
    if len(elt.elts) < 4:
        return None
    n = elt.elts[3]
    if isinstance(n, ast.Constant) and isinstance(n.value, bool):
        return None
    if isinstance(n, ast.Constant) and isinstance(n.value, int):
        return n.value
    return False  # a 4th element that is not an int literal: unreadable


def flat_arm_positions(tree):
    """{helper_name: (old_index, new_index)} for the FLAT positional arm form.

    ── A THIRD CONVENTION, AND NOTHING WAS POINTED AT IT (2026-09-27) ───────
    Measured across 99 probe files, there are THREE ways an anchor is declared
    on this platform and each is a different call shape:

      1. a module-level MUTATIONS list        85 probes  mutation_anchor_check.py
      2. arm(..., [(SUBJECT, old, new)])      10 probes  this file
      3. arm(label, suite, old, new)           2 probes  NOTHING

    Overlap between 1 and 2 is ZERO -- two checkers, two disjoint populations,
    neither aware of the other. The three probes that died silently this week
    were all in population 2, which is why a WIRED checker for population 1
    could not have caught any of them. Population 3 is tests/sairnbiz_fault_
    probe.py and tests/sairnvet_fault_probe.py, the second of which arms a
    controlled-substance register.

    ── THE SHAPE IS READ OFF THE HELPER'S OWN DECLARATION, NEVER GUESSED ────
    A positional heuristic ("the last two string literals are old and new")
    would misread ordinary assertion helpers -- tests/run_adversarial_prompt_
    corpus_probe.py has `def arm(name, ok, detail='')` and
    tests/push_gate/missing_checker_probe.py has a seven-parameter arm that
    takes fixtures, not anchors. Both carry three string literals per call and
    neither declares an anchor.

    AND THE OBVIOUS DISCRIMINATOR IS CIRCULAR AND MUST NOT BE USED: "treat it as
    an anchor if the subject contains it" can never report an anchor as VANISHED,
    because vanishing is exactly the case where the subject does not contain it.
    A rule that requires a match in order to look is a rule that reports every
    healthy anchor and no broken one.

    So the discriminator is the PARAMETER NAMES: a helper whose signature
    literally has `old` and `new` is a mutation helper, and their positions say
    which arguments to read. That is exact, non-circular, and it rejects both
    false candidates above.
    """
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in ARM_CALLS:
            continue
        params = [a.arg for a in node.args.args]
        if 'old' in params and 'new' in params:
            out[node.name] = (params.index('old'), params.index('new'))
    return out


def anchors_in(tree, names):
    """[(subject_path, anchor_string, lineno, expect)] for every literal anchor.

    `expect` is the DECLARED occurrence count from a 4-element edit tuple, or
    None when the edit is the ordinary replace-once form. See declared_count().

    Also returns the count of tuples this could NOT resolve, so an unreadable
    anchor is a stated gap rather than a silently smaller denominator.
    """
    found, unresolved = [], 0
    flat = flat_arm_positions(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fname = getattr(node.func, 'id', None) or getattr(node.func, 'attr', None)
        if fname not in ARM_CALLS:
            continue
        if fname in flat:
            # CONVENTION 3. The helper's own signature said where `old` is.
            oi = flat[fname][0]
            if oi >= len(node.args):
                unresolved += 1
                continue
            old_node = node.args[oi]
            path = sole_subject(names)
            if not path or not isinstance(old_node, ast.Constant) \
                    or not isinstance(old_node.value, str):
                unresolved += 1
                continue
            found.append((path, old_node.value, getattr(node, 'lineno', 0), None))
            continue
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            for elt in (arg.elts if isinstance(arg, (ast.List, ast.Tuple)) else [arg]):
                if not isinstance(elt, ast.Tuple) or len(elt.elts) < 2:
                    continue
                subj, old = elt.elts[0], elt.elts[1]
                expect = declared_count(elt)
                if expect is False:
                    # A 4th element that is not an int literal. Neither rule is
                    # safe to apply, so this is a stated gap, never a verdict.
                    unresolved += 1
                    continue
                path = None
                if isinstance(subj, ast.Name):
                    path = names.get(subj.id)
                elif isinstance(subj, ast.Constant) and isinstance(subj.value, str) \
                        and subj.value.endswith(('.js', '.html', '.py', '.sql', '.json')):
                    path = subj.value
                if path is None and len(elt.elts) == 2:
                    # `(old, new)` against a probe's single subject. See
                    # sole_subject() for why this is narrow rather than a guess.
                    path = sole_subject(names)
                    old = elt.elts[0]
                if not path or not isinstance(old, ast.Constant) \
                        or not isinstance(old.value, str):
                    unresolved += 1
                    continue
                found.append((path, old.value, getattr(elt, 'lineno', 0), expect))
    return found, unresolved


def scan():
    probes = tracked_probes()
    if probes is None:
        return None
    subjects = {}
    rows = []
    skipped = []
    for rel in probes:
        src = read(rel)
        if src is None:
            skipped.append((rel, 'could not be read'))
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            # A PROBE THAT DOES NOT PARSE IS A FINDING, not a skip: it cannot
            # run either.
            rows.append({'probe': rel, 'subject': '-', 'count': -1,
                         'anchor': 'FILE DOES NOT PARSE: %s' % exc, 'line': 0})
            continue
        names = subject_names(tree)
        anchors, unresolved = anchors_in(tree, names)
        if unresolved:
            skipped.append((rel, '%d anchor(s) not a resolvable literal' % unresolved))
        for path, anchor, line, expect in anchors:
            if path not in subjects:
                subjects[path] = read(path)
            body = subjects[path]
            if body is None:
                rows.append({'probe': rel, 'subject': path, 'count': -2,
                             'anchor': anchor[:110], 'line': line,
                             'expect': expect})
                continue
            rows.append({'probe': rel, 'subject': path,
                         'count': lf(body).count(lf(anchor)),
                         'anchor': anchor[:110], 'line': line,
                         'expect': expect})
    return {'probes': len(probes), 'rows': rows, 'skipped': skipped}


def verdict(row):
    """One of ok / vanished / ambiguous / miscounted / unreadable.

    THE DECLARED COUNT DECIDES WHICH RULE APPLIES, and that is the whole point of
    this function existing rather than the report filtering on `count` inline.
    With no declared count the probe will `replace(old, new, 1)`, so exactly one
    is the only safe number. With one, the probe asserts the total and replaces
    every occurrence, so `expect` is the only safe number -- 6 matches is CORRECT
    for an edit that declared 6 and a FINDING for an edit that declared 8.
    """
    c = row['count']
    if c in (-1, -2):
        return 'unreadable'
    exp = row.get('expect')
    if exp is None:
        return 'ok' if c == 1 else ('vanished' if c == 0 else 'ambiguous')
    if c == exp:
        return 'ok'
    return 'vanished' if c == 0 else 'miscounted'


def selftest():
    out, bad = [], 0

    def arm_(name, ok, detail=''):
        nonlocal bad
        out.append('  %s %s%s' % ('ok  ' if ok else 'FAIL', name,
                                  '' if ok else '\n       ' + detail))
        if not ok:
            bad += 1

    FIXTURE = (
        "HTML = 'fixture_subject.html'\n"
        "DATA = 'api/fixture.js'\n"
        "def arm(label, edits):\n"
        "    pass\n"
        "arm('a', [(HTML, 'ONE_MATCH', 'x')])\n"
        "arm('b', [(HTML, 'TWICE', 'y')])\n"
        "arm('c', [(HTML, 'GONE', 'z')])\n"
        "arm('d', [(HTML, 'a' + 'b', 'w')])\n"
        "arm('e', [(UNKNOWN, 'ANY', 'v')])\n"
        # THE COUNTED FORM, IN BOTH DIRECTIONS. `f` declares the number the
        # fixture body really has and must read as CORRECT even though it
        # matches twice; `g` declares a number it does not have and must read as
        # COUNT DISAGREES. Without both, a checker that ignored the 4th element
        # entirely would satisfy the first and a checker that trusted it blindly
        # would satisfy the second.
        "arm('f', [(HTML, 'TWICE', 'y2', 2)])\n"
        "arm('g', [(HTML, 'TWICE', 'y3', 5)])\n"
        # A NON-LITERAL COUNT IS UNRESOLVED, NEVER GUESSED.
        "arm('h', [(HTML, 'ONE_MATCH', 'x2', HOW_MANY)])\n"
    )
    # ── CONVENTION 3, IN BOTH DIRECTIONS ───────────────────────────────────
    # A helper whose signature literally names `old` and `new` IS a mutation
    # helper and its parameter positions say which arguments to read. One whose
    # signature does not is an assertion helper and must be left alone, however
    # many string literals its calls carry -- tests/run_adversarial_prompt_
    # corpus_probe.py has `def arm(name, ok, detail='')` and would be misread by
    # any positional heuristic.
    FLAT_YES = ("HTML = 'fixture_subject.html'\n"
                "def arm(label, suite, old, new):\n    pass\n"
                "arm('a', SUITE, 'ONE_MATCH', 'x')\n"
                "arm('b', SUITE, 'GONE', 'y')\n")
    FLAT_NO = ("HTML = 'fixture_subject.html'\n"
               "def arm(name, ok, detail=''):\n    pass\n"
               "arm('1. a thing holds', 'yes', 'detail text')\n")
    ty = ast.parse(FLAT_YES)
    tn = ast.parse(FLAT_NO)
    arm_('a FLAT arm helper is recognised from its own signature',
         flat_arm_positions(ty) == {'arm': (2, 3)},
         'read %r' % (flat_arm_positions(ty),))
    arm_('...and an ASSERTION helper of the same name is NOT',
         flat_arm_positions(tn) == {},
         'read %r -- `def arm(name, ok, detail)` declares no anchor, and a '
         'positional heuristic would have taken its three string literals as '
         'one' % (flat_arm_positions(tn),))
    fa, _fu = anchors_in(ty, subject_names(ty))
    arm_('...and its anchors are read against the probe SOLE subject',
         sorted(a for _p, a, _l, _e in fa) == ['GONE', 'ONE_MATCH']
         and all(p == 'fixture_subject.html' for p, _a, _l, _e in fa),
         'read %r' % (fa,))
    na, _nu = anchors_in(tn, subject_names(tn))
    arm_('CONTROL -- the assertion helper contributes NO anchors at all',
         na == [],
         'read %r. If this ever returns rows, every assertion in every probe '
         'named arm() becomes a phantom anchor and the VANISHED list fills '
         'with strings that were never anchors.' % (na,))
    tree = ast.parse(FIXTURE)
    names = subject_names(tree)
    arm_('module-level subject paths are resolved',
         names.get('HTML') == 'fixture_subject.html'
         and names.get('DATA') == 'api/fixture.js',
         'resolved %r' % names)
    anchors, unresolved = anchors_in(tree, names)
    got = sorted(a for _p, a, _l, _e in anchors)
    # 'TWICE' three times: arm b (no declared count), f (declares 2) and g
    # (declares 5). The SAME anchor string under three different rules is
    # deliberate -- it is what proves the rule comes from the edit rather than
    # from the anchor.
    arm_('every LITERAL anchor is found',
         got == ['GONE', 'ONE_MATCH', 'TWICE', 'TWICE', 'TWICE'],
         'found %r' % got)
    arm_('a CONCATENATED anchor, an UNRESOLVABLE subject and a NON-LITERAL '
         'count are counted as unresolved, not silently dropped',
         unresolved == 3,
         'unresolved was %d, expected 3 (the a+b concatenation, the UNKNOWN '
         'subject name, and the HOW_MANY variable count)' % unresolved)
    declared = sorted(e for _p, _a, _l, e in anchors if e is not None)
    arm_('the DECLARED count is read off the 4th element',
         declared == [2, 5],
         'declared counts read as %r, expected [2, 5]' % declared)

    # CRLF IN THE FIXTURE ON PURPOSE. The body carries carriage returns and the
    # anchors do not, which is exactly the mismatch between this clone's working
    # tree and the LF worktree the probes read. Without lf() all three counts
    # below would be 0 and this checker would call every healthy probe broken --
    # which it did, on two of them, before this fixture existed.
    body = 'ONE_MATCH\r\nTWICE\r\nTWICE\r\n'
    counts = dict((a, lf(body).count(lf(a))) for _p, a, _l, _e in anchors)
    arm_('a unique anchor counts 1', counts.get('ONE_MATCH') == 1)
    arm_('an AMBIGUOUS anchor counts >1 -- the sairnmechanical shape',
         counts.get('TWICE') == 2,
         'three matches is what replace(old, new, 1) silently picks from')
    arm_('a VANISHED anchor counts 0 -- the sairncash/sairncare shape',
         counts.get('GONE') == 0)
    arm_('CONTROL -- the three outcomes are distinguishable',
         len(set([counts.get('ONE_MATCH'), counts.get('TWICE'),
                  counts.get('GONE')])) == 3,
         'the counter returns the same answer for unique, ambiguous and '
         'vanished, so every arm above is checking one value three times')

    # ── THE VERDICT LAYER, WHICH IS WHERE THE INVERSION LIVED ──────────────
    # The counter above was never wrong. What was wrong was the RULE applied to
    # its answer: 2 matches is a finding for an edit that declares nothing and
    # correct for an edit that declares 2. These arms drive verdict() rather
    # than the counter, because a criteria change is not a counting change.
    def row(count, expect):
        return {'count': count, 'expect': expect}
    arm_('no declared count: exactly one is ok, zero VANISHED, more AMBIGUOUS',
         verdict(row(1, None)) == 'ok'
         and verdict(row(0, None)) == 'vanished'
         and verdict(row(3, None)) == 'ambiguous',
         'got %r' % [verdict(row(n, None)) for n in (1, 0, 3)])
    arm_('a DECLARED count of 6 makes 6 matches CORRECT -- the four false '
         'AMBIGUOUS rows this closes',
         verdict(row(6, 6)) == 'ok',
         'six matches against a declared six read as %r. This is the '
         'sairndesign/sairngrounds shape and the reason criteria moved to '
         '.2: all_n() asserts the number and replaces every occurrence, which '
         'is stronger than uniqueness, and the first version scored it worse.'
         % verdict(row(6, 6)))
    arm_('...and a DECLARED count of 6 makes ONE match a finding, not a pass',
         verdict(row(1, 6)) == 'miscounted',
         'one match against a declared six read as %r -- five sites were '
         'removed or renamed and the arm would now mutate a subset'
         % verdict(row(1, 6)))
    arm_('...and 8 against a declared 6 is a finding too -- it drifts UP as '
         'well as down',
         verdict(row(8, 6)) == 'miscounted',
         'got %r' % verdict(row(8, 6)))
    arm_('a declared count with ZERO matches is still VANISHED, not miscounted',
         verdict(row(0, 6)) == 'vanished',
         'zero is the anchor being gone, which has a different fix from a '
         'number that moved; got %r' % verdict(row(0, 6)))
    arm_('CONTROL -- the declared count actually CHANGES the verdict',
         verdict(row(6, None)) != verdict(row(6, 6)),
         'verdict() returns the same answer for 6 matches whether or not a '
         'count was declared, so every arm above is checking one rule twice '
         'and the inversion this version exists to fix is still live')
    arm_('COULD NOT CHECK survives a declared count rather than being '
         'overridden by it',
         verdict(row(-2, 6)) == 'unreadable' and verdict(row(-1, None)) == 'unreadable',
         'an unreadable subject must stay a third state whatever the edit '
         'declared; got %r' % [verdict(row(-2, 6)), verdict(row(-1, None))])

    live = scan()
    arm_('the real scan runs and finds anchors to count',
         live is not None and len(live['rows']) > 20,
         'the live scan produced %s rows -- too few to be the real probe set, '
         'so a clean result would mean nothing'
         % (len(live['rows']) if live else 'no'))
    return out, bad


def main(argv):
    if '--selftest' in argv:
        print('PROBE ANCHOR FRESHNESS -- selftest')
        o, bad = selftest()
        for l in o:
            print(l)
        print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
        return 1 if bad else 0

    res = scan()
    if res is None:
        print('COULD NOT RUN: git ls-files failed, so the probe list is '
              'unknown. NOT reporting a clean sweep.', file=sys.stderr)
        return 2

    by = {}
    for r in res['rows']:
        by.setdefault(verdict(r), []).append(r)
    vanished = by.get('vanished', [])
    ambiguous = by.get('ambiguous', [])
    miscounted = by.get('miscounted', [])
    unreadable = by.get('unreadable', [])
    ok = by.get('ok', [])
    counted = [r for r in res['rows'] if r.get('expect') is not None]

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION,
                          'vanished': vanished, 'ambiguous': ambiguous,
                          'miscounted': miscounted,
                          'unreadable': unreadable, 'ok': len(ok),
                          'counted_form': len(counted),
                          'skipped': res['skipped'],
                          'blind_spots': BLIND_SPOTS}, indent=1))
        return 1 if (vanished or ambiguous or miscounted or unreadable) else 0

    print('PROBE ANCHOR FRESHNESS -- a sabotage anchor that no longer matches')
    print('  criteria %s' % CRITERIA_VERSION)
    print('  %d probe file(s) parsed, %d anchor(s) counted'
          % (res['probes'], len(res['rows'])))
    print('  %d agree with the rule that applies to them' % len(ok))
    print('  %d of those declare an expected count and are held to THAT number, '
          'not to 1' % len(counted))
    print('')
    print('VANISHED -- matches ZERO places (%d). The code moved; re-derive the '
          'anchor against' % len(vanished))
    print('  what it became, and do not restore the old text.')
    for r in vanished:
        print('    %s:%d -> %s' % (r['probe'], r['line'], r['subject']))
        print('        %r' % r['anchor'])
    print('')
    print('AMBIGUOUS -- matches MORE THAN ONE place and declares NO expected '
          'count (%d).' % len(ambiguous))
    print('  replace(old, new, 1) silently picks the first, so the probe reports '
          'a verdict about')
    print('  a line nobody chose. Either WIDEN the anchor, or declare the count '
          'and replace all.')
    for r in ambiguous:
        print('    %s:%d -> %s  (%d matches)'
              % (r['probe'], r['line'], r['subject'], r['count']))
        print('        %r' % r['anchor'])
    print('')
    print('COUNT DISAGREES -- the edit DECLARES a count and the subject no longer '
          'has it (%d).' % len(miscounted))
    print('  This is the STRONGER guard drifting, and it drifts in both '
          'directions: fewer means')
    print('  a site was removed or renamed, more means one was added and the '
          'sabotage would now')
    print('  reach a line the arm was never about. Re-derive the number against '
          'the subject.')
    for r in miscounted:
        print('    %s:%d -> %s  (declares %d, found %d)'
              % (r['probe'], r['line'], r['subject'], r['expect'], r['count']))
        print('        %r' % r['anchor'])
    if unreadable:
        print('')
        print('COULD NOT CHECK (%d) -- a third state, not a pass:' % len(unreadable))
        for r in unreadable:
            print('    %s:%d -> %s  %s'
                  % (r['probe'], r['line'], r['subject'], r['anchor'][:80]))
    if res['skipped']:
        print('')
        print('NOT FULLY SCANNED (%d) -- printed rather than counted as clean:'
              % len(res['skipped']))
        for rel, why in res['skipped']:
            print('    %s -- %s' % (rel, why))
    print('')
    print('WHAT THIS CANNOT SEE:')
    for b in BLIND_SPOTS:
        print('  - %s' % b)
    return 1 if (vanished or ambiguous or miscounted or unreadable) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
