"""Does every mutation probe's anchor still match its target EXACTLY ONCE?

CANONICAL RULE: docs/SAIRN-PROCESS-RULES.md section 1.3, "An anchor that still
matches is not an anchor that still points at the right thing". That section
carries the durable form -- a string anchor verifies UNIQUENESS, never
CORRECTNESS -- and applies it to standing-document edits as well as to probes.
It was written 2026-09-12 because this lesson lived only in this docstring.

WHY. A mutation probe reintroduces a defect, asserts the suite goes red, and
restores the file. Its anchor is an exact string. When the target is refactored
the anchor stops matching, and the arm stops testing:

  * MATCHES ZERO TIMES -- loud. tests/dnt_vendor_write_confirmation_probe.py arm
    4 expected an `}else if(storeKey){` that a refactor had collapsed into a flat
    `if`. Its own harness reported ANCHOR-0 and failed. Nobody fixed it for a
    day, but it was saying so.
  * MATCHES MORE THAN ONCE -- also loud, and already the reason one arm in that
    same file carries a note: an anchor shared by two writers probed neither.

BOTH OF THOSE ARE CAUGHT BY EACH PROBE'S OWN HARNESS, WHEN IT RUNS. This tool
exists because that is a weaker guarantee than it sounds:

  * a probe only checks its own anchors, and only when something runs it. Four of
    the six could not be swept at all on 2026-09-11 because they declare their
    target differently -- so "they pass in the full suite" was the strongest
    claim available, which is not the same as "their anchors were verified";
  * an anchor that has drifted onto DIFFERENT code while still matching exactly
    once is invisible to the uniqueness check. That is not detectable here
    either -- said plainly below rather than implied away.

WHAT IT DOES. PARSES every tests/*_probe.py that defines MUTATIONS -- with ast,
never importing it -- resolves the target file for each arm, and counts the
anchor. It does not import because IMPORTING A PROBE RUNS IT: most have no
`if __name__ == "__main__"` guard, so an import mutates a live source file,
shells out to node, and restores it at the end. The first version of this tool
did import, hung, was killed mid-probe, and left api/_lib/dental-guardian.js
modified on disk. A read-only checker must not be able to change the thing it
inspects. Two declaration shapes
exist in this repo and both are handled rather than normalised, because
rewriting six probes to suit a checker is the tail wagging the dog:

    (name, old, new)          -> the module-level TARGET
    (name, FILE, old, new)    -> FILE, as given

WHAT IT CANNOT SEE, said here rather than discovered later:
  * an anchor pointing at the WRONG branch while matching exactly once. On
    2026-09-11 that cost a real arm: a six-space anchor sat on the
    missing-fields branch of dntPushOne() instead of the refused branch it was
    named for, matched once, and reported SILENT for weeks. Uniqueness is the
    only half a string match can check;
  * whether the mutation actually makes the suite fail -- that is the probe's
    own job, and it needs to run the suite. This never runs anything and never
    writes anything;
  * a probe that builds its MUTATIONS list at run time rather than declaring it.

Usage:
    python tools/mutation_anchor_check.py
    python tools/mutation_anchor_check.py --json

Exit 0 when every anchor matches exactly once, 1 when one does not, 2 when a
probe could not be read at all -- which is not a pass.
"""
import ast
import glob
import io
import re
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# A sentinel target meaning "resolved, and it is not a file" -- an in-memory
# buffer or a transform. Distinct from None (could not resolve) so main() can
# tell them apart, which is the whole correction made to resolve() on
# 2026-09-28.
#
# NOT A NUL BYTE, and the first version was. `'\x00structural'` reached
# docs/MASTER-PLAN.md through the generator that reads this tool, and the push
# gate's control-byte check refused it -- correctly, and it is the reason that
# check exists: a raw control byte in a tracked file is invisible to a reader
# and to grep. Angle brackets are safe because no path on this platform
# contains one, so the sentinel can never collide with a real target.
STRUCTURAL = '<structural: no file anchor>'


def literal(node):
    """The constant value of an AST node, or None if it is not a plain literal."""
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def element(node):
    """One MUTATIONS element, rendered so resolve() can tell the kinds apart.

    Three shapes, and the third was being MIS-REPORTED until 2026-09-17:

      a literal            -> the value
      a bare Name          -> '@name' (a module constant, or a transform fn)
      re.compile('...')    -> ('re', '<pattern>')

    A COMPILED PATTERN IS A TEXT ANCHOR AND IT CAN ROT, which is why it is
    counted rather than excused. license_trial_gate_probe.py arm 9 switched to
    one after its literal died on a rename, and this checker -- which could not
    see past the Call node -- reported it as COULD NOT READ. That is the right
    answer for something genuinely unreadable and the WRONG one here: it moved a
    live, checkable anchor into the bucket that means "nobody knows", which is
    the same place a real stale anchor would sit. Counted now, with re.findall,
    so the uniqueness rule applies to it exactly as to a literal.
    """
    if isinstance(node, ast.Name):
        return '@' + node.id
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'compile' and node.args):
        pat = literal(node.args[0])
        if isinstance(pat, str):
            return ('re', pat)
    # ── AN INLINE os.path.join IN THE TARGET SLOT, added 2026-09-28 ────────
    # A FOURTH shape, and the last thing keeping this tool at exit 2.
    # tests/fail_open_triage_probe.py arm 5 names its subject as
    # `os.path.join('api', 'sen-portal.js')` right in the entry rather than via
    # a module constant. literal() cannot evaluate a Call, so the target read
    # as None and the arm was reported as "the probe declares 5 candidate
    # subject files and the arm names none of them" -- while the arm named its
    # file more precisely than any of the five. read_probe() has resolved this
    # exact form for module-level constants since it was written; the entry
    # parser simply never learned it.
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'join' and node.args):
        parts = [literal(a) for a in node.args]
        if parts and all(isinstance(p, str) for p in parts):
            return os.path.join(*parts)
    return literal(node)


def read_probe(path):
    """(module-level string assignments, MUTATIONS entries) by PARSING, never importing.

    THIS TOOL IMPORTED THE PROBES ON ITS FIRST RUN AND THAT WAS A REAL HAZARD,
    not a style point. Most probes in tests/ have no `if __name__ == "__main__"`
    guard, so importing one RUNS it: it mutates a live source file, shells out to
    node, and restores the file at the end. The first run of this checker hung on
    that and was killed mid-probe, which left `api/_lib/dental-guardian.js`
    modified on disk with an injected `if (r.zz_probe_field) return "probe";`.
    Restored by hand, verified clean, and the tool rewritten to parse instead.

    A read-only checker must not be able to change the thing it inspects.
    """
    tree = ast.parse(io.open(path, encoding='utf-8', errors='replace').read(), path)
    consts, muts = {}, []
    # ── EVERY MODULE-LEVEL NAME, INCLUDING TUPLE UNPACKING AND def ─────────
    # Needed to tell a NAME THAT EXISTS BUT IS NOT A PATH -- an in-memory
    # buffer, a transform function -- from a name that exists NOWHERE, which is
    # a real typo and a real finding. `RAW_APP, RAW_H, RAW_REG = raw_of(APP),
    # ...` in tests/sen_evv_payroll_wiring_probe.py is a tuple target, so the
    # single-Name loop below could not see it and six of its arms read as
    # "names a thing that does not exist" when the thing is one line up.
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                for sub in (t.elts if isinstance(t, (ast.Tuple, ast.List)) else [t]):
                    if isinstance(sub, ast.Name):
                        names.add(sub.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        tgt = node.targets[0]
        if not isinstance(tgt, ast.Name):
            continue
        if tgt.id == 'MUTATIONS' and isinstance(node.value, (ast.List, ast.Tuple)):  # noqa: E501
            for el in node.value.elts:
                if isinstance(el, (ast.Tuple, ast.List)):
                    muts.append([element(x) for x in el.elts])
            continue
        v = literal(node.value)
        if isinstance(v, str):
            consts[tgt.id] = v
        elif (isinstance(node.value, ast.Call) and
              isinstance(node.value.func, ast.Attribute) and
              node.value.func.attr == 'join'):
            # os.path.join('a', 'b') -- resolved as a relative path. A ROOT
            # argument is dropped: every path here is resolved against REPO
            # anyway, and ROOT is not a literal this parser can see.
            parts = [literal(x) for x in node.value.args]
            parts = [x for x in parts if isinstance(x, str)]
            if parts:
                consts[tgt.id] = os.path.join(*parts)
    consts['__names__'] = names
    return consts, muts


def is_observer(rel):
    """A SUITE rather than a SUBJECT: a mutation probe mutates the subject and
    watches the suite, so a suite path is never the thing an arm mutates."""
    q = str(rel).replace('\\', '/')
    return q.startswith('tests/') or '/tests/' in q or q.endswith('.test.js')


def sole_subject(consts):
    """The one file an entry with NO target element can only mean, or None.

    ── WHY THIS EXISTS: `TARGET` IS A NAME NOBODY USES ────────────────────
    resolve() fell back to `consts.get('TARGET')` for any entry shorter than
    four elements. MEASURED 2026-09-28 across the 19 probes this tool could not
    read: **`TARGET` appears in exactly ZERO of them.** They call the subject
    SUITE (11), APP (3), HANDLER (3), API, ENDPOINT, REGISTRY, SERVING, ENGINE,
    LOCK, AUTH, SRC, TOOL, SUBJECT and eight more. The fallback was looking for
    a spelling this repo does not use, which is the one-spelling-of-a-correct-
    answer defect three tools on this platform have now shipped.

    OBSERVERS ARE DROPPED FIRST, and that is what makes this decidable rather
    than a guess: a probe names its suite and its subject, and only the subject
    is ever mutated. What remains after dropping suites is one file in 30 arms.

    MORE THAN ONE REMAINING IS AMBIGUOUS AND STAYS UNREADABLE, with the
    candidates NAMED. Guessing which of three files an arm meant is exactly the
    ambiguity this checker exists to refuse, and a wrong guess would count an
    anchor in the wrong file and report ANCHOR-0 against a healthy arm.
    """
    paths = {}
    for k, v in consts.items():
        if k == '__names__' or not isinstance(v, str):
            continue
        p = v if os.path.isabs(v) else os.path.join(REPO, v)
        if os.path.exists(p) and not os.path.isdir(p):
            paths[k] = p
    nonobs = {k: v for k, v in paths.items() if not is_observer(consts[k])}
    if len(nonobs) == 1:
        return list(nonobs.values())[0], sorted(nonobs)
    return None, sorted(nonobs)


def resolve(consts, entry):
    """(target_path, old) for one MUTATIONS entry, or (None, old) if unresolved.

    ── THE ROOT CAUSE OF THIS TOOL'S EXIT 2, FOUND 2026-09-28 ─────────────
    It reported 84 arms across 19 probes as "target unresolved" and exited 2 --
    COULD NOT RUN -- permanently, while wired into report_only_checks.REGISTRY.
    A wired check that cannot run is the same failure as no check, and it was
    saying so in output nobody read.

    NOT ONE OF THE 84 WAS A STALE ANCHOR. Two separate defects in THIS
    FUNCTION, and the message was wrong about both:

      1. THE TARGET RESOLVED FINE AND WAS THROWN AWAY. The type guard below
         used to read

             if not isinstance(target, str) or not (isinstance(old, str) or ...):
                 return None, old

         so an arm whose target is a real file but whose mutation is a LAMBDA
         or transform function returned (None, ...) -- "target unresolved" --
         about a target that had just been resolved. main() already has a
         STRUCTURAL bucket for "an arm with no text anchor, nothing to rot"; it
         was unreachable for these because reaching it needs `target` to
         survive. Now the two questions are asked separately: is the TARGET
         resolvable, and separately, is there a TEXT ANCHOR to count.

      2. THE NO-TARGET FALLBACK LOOKED FOR A NAME NOBODY USES. See
         sole_subject(): `TARGET` appears in ZERO of the 19 probes.

    A NAME THAT EXISTS BUT IS NOT A PATH IS STRUCTURAL, NOT UNREADABLE -- an
    in-memory buffer like RAW_APP, which is the file's CONTENT rather than its
    path. A name that exists NOWHERE in the module stays unreadable, because
    that is a typo and a real finding.
    """
    if len(entry) >= 4:
        target, old = entry[1], entry[2]
    else:
        target, old = None, (entry[1] if len(entry) > 1 else None)
    if target is None:
        # NO TARGET, WHATEVER THE ARITY. The first version only tried this for
        # entries shorter than four elements, and tests/roofing_claim_gate_
        # probe.py writes four-element entries whose target slot is a literal
        # None -- so the fallback was skipped and the arm was reported
        # unreadable while naming the single candidate it should have used.
        # "The probe declares 1 candidate and the arm names none of them" is a
        # message that answers itself, which is how that was spotted.
        sub, _cands = sole_subject(consts)
        target = sub
    if isinstance(target, str) and target.startswith('@'):
        nm = target[1:]
        if nm in consts and isinstance(consts.get(nm), str):
            target = consts[nm]
        elif nm in consts.get('__names__', ()):
            # A real module-level name that is not a path: a buffer or a
            # transform. There is no FILE anchor here by construction.
            return STRUCTURAL, None
        else:
            return None, old
    # ── AN ARM THAT NAMES A FUNCTION HAS NO TEXT ANCHOR TO ROT ──────────
    # read_probe() renders a bare Name as '@name'. For a TARGET that means a
    # module constant; for OLD it can also mean a TRANSFORM FUNCTION, which
    # is what license_trial_gate_probe.py switched its two snapshot arms to
    # on 2026-09-14 after their text anchors died for the third time in a
    # re-capture. Counting '@_snap_add_trial_column' as a literal found it
    # zero times and reported ANCHOR-0 -- a stale-anchor finding against an
    # arm that has no anchor by construction. Structural arms are reported
    # in their own line rather than dropped: an exclusion nobody sees is how
    # a real stale anchor would hide in the same category.
    # ── AN ANCHOR NAMED BY A CONSTANT IS SUBSTITUTED, NOT COUNTED AS TEXT ──
    # FALSE VANISHED, found 2026-09-28. The target half of this function has
    # resolved `@NAME` from consts since it was written; the ANCHOR half never
    # did, so an arm written as `(label, SUBJECT, ROW_LOOP, replacement)` --
    # where ROW_LOOP is a module-level multi-line string, the readable way to
    # write a long unique span -- had the nine characters '@ROW_LOOP' counted
    # as literal text. Zero matches, reported ANCHOR-0 against an anchor that
    # matches its subject EXACTLY ONCE.
    #
    # A FALSE VANISHED IS WORSE THAN A MISS: it sends somebody to re-derive a
    # healthy anchor, and the re-derivation is the risky edit. Two of the 16
    # findings this tool reported after its exit-2 fix were this, and both
    # probes were correct.
    if isinstance(old, str) and old.startswith('@') and old[1:] in consts \
            and isinstance(consts[old[1:]], str):
        old = consts[old[1:]]
    if isinstance(old, str) and old.startswith('@') and old[1:] not in consts:
        # A TRANSFORM FUNCTION, so there is no text anchor in the entry --
        # the anchor, if any, lives inside the function body and this tool
        # cannot see it. STRUCTURAL whether or not a target was named: the old
        # `return target, None` only reached main()'s structural bucket when a
        # target happened to resolve, so the 2-element
        # `(label, build_function)` shape -- eight arms in
        # tests/run_provisioner_health_sole_role_sabotage_probe.py alone -- fell
        # through to COULD NOT READ instead.
        return (target if isinstance(target, str) else STRUCTURAL), None
    # NO ANCHOR AT ALL IS STRUCTURAL WHATEVER THE TARGET IS. An arm carrying
    # neither a countable anchor nor a resolvable file has nothing that can
    # rot, so reporting it as COULD NOT READ says "nobody knows" about
    # something there is nothing to know about -- and it is the bucket a real
    # stale anchor would hide in. tests/law_trust_reconcile_wiring_probe.py's
    # four arms are this shape: their mutations are functions and their
    # constants are fixture STRINGS, not paths.
    countable = (isinstance(old, str)
                 or (isinstance(old, tuple) and old and old[0] == 're'))
    if not countable:
        return STRUCTURAL, None
    if not isinstance(target, str):
        return None, old
    p = target if os.path.isabs(target) else os.path.join(REPO, target)
    if not os.path.exists(p):
        # ── A GROUP LABEL IN THE TARGET SLOT IS NOT A TYPO (2026-10-06) ─────
        # tests/run_alf_scope_mutation_probe.py writes
        # `(label, 'alf-mar', old, new, must_arms)` -- the second element is the
        # SUITE GROUP, not a file, which is a fifth convention this tool had not
        # met. Five arms came back COULD NOT READ with the message "the probe
        # declares 1 candidate subject file (TARGET) and the arm names none of
        # them", which is the same self-answering message the 2026-09-28 note
        # above records: if there is exactly ONE candidate, the arm cannot mean
        # anything else.
        #
        # THE DISTINCTION THAT KEEPS THIS HONEST IS PATH-SHAPE, NOT EXISTENCE.
        # A string carrying a separator or a code extension that does not exist
        # on disk IS a typo and stays COULD NOT READ -- a real finding, and the
        # one this fallback must not swallow. `alf-mar` has neither, so it can
        # only be a label.
        #
        # AMBIGUITY STILL REFUSES. sole_subject() returns None when more than
        # one non-observer path remains, and guessing between them is exactly
        # what this checker exists not to do.
        looks_like_path = ('/' in target or '\\' in target
                           or re.search(r'\.(py|js|html|sql|json|md)$', target))
        if not looks_like_path:
            sub, _c = sole_subject(consts)
            if sub:
                p = sub
            else:
                return None, old
        else:
            return None, old
    # THE TARGET IS RESOLVED and `countable` was decided above. A lambda, a
    # transform or a None mutation is STRUCTURAL rather than unreadable;
    # conflating the two is defect 1 in the docstring.
    return p, old



def mutates_repo_path(body):
    """True if this probe opens a REPO/ROOT-derived path for binary writing.

    Parsed, never grepped: see the note at the call site for why that matters.
    """
    try:
        tree = ast.parse(body)
    except SyntaxError:
        return False
    repo_names = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == 'join'
                and node.value.args
                and isinstance(node.value.args[0], ast.Name)
                and node.value.args[0].id in ('REPO', 'ROOT')):
            repo_names.add(node.targets[0].id)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, 'id', None)
        if name != 'open' or len(node.args) < 2:
            continue
        mode = node.args[1]
        if not (isinstance(mode, ast.Constant) and mode.value == 'wb'):
            continue
        tgt = node.args[0]
        if isinstance(tgt, ast.Name) and tgt.id in repo_names:
            return True
    return False


# ── THE KNOWN-POSITIVE FIXTURE SET, ADDED 2026-09-29 ────────────────────────
# This tool had NO fixture set of any kind, so a run printing "0 stale anchors,
# 0 unguarded probes" was indistinguishable from a run whose detector had
# stopped working -- the exact failure it was written to catch, one level up.
# Found by tools/checker_selftest_check.py.
#
# The two criteria carried here are `mutates_repo_path`, whose THIRD version is
# the first correct one, and the anchor counting in main(). The fixtures below
# lock the first in BOTH directions, including the two false positives the
# earlier versions actually shipped: a probe writing only into a temp worktree,
# and a probe containing the unsafe pattern as a QUOTED FIXTURE STRING -- which
# is why this is parsed rather than grepped, and it is worth a permanent arm
# because it is the third instance of that class in two days.
FIXTURE_CASES = (
    ("""
import io, os
def go():
    p = os.path.join(REPO, 'stonedesk.html')
    open(p, 'wb').write(b'x')
""", True, 'THE UNSAFE SHAPE: a REPO-derived path opened for binary writing'),
    ("""
import io, os
def go():
    p = os.path.join(tmp, 'stonedesk.html')
    open(p, 'wb').write(b'x')
""", False,
     'THE SILENT HALF: a TEMP-derived path is the safe pattern and must not '
     'report. v1 flagged any open(x, "wb") and caught six probes doing this'),
    ("""
BAD_EXAMPLE = "p = os.path.join(REPO, 'x'); open(p, 'wb')"
def go():
    print(BAD_EXAMPLE)
""", False,
     'THE QUOTED EXAMPLE: v2 flagged THIS TOOL\'S OWN PROBE because that probe '
     'carries the unsafe pattern as a fixture STRING. ast cannot see inside a '
     'literal, which is why this is parsed -- third instance of that class in '
     'two days and the reason the arm is permanent'),
    ("""
import os
def go():
    p = os.path.join(REPO, 'x.html')
    open(p, 'r').read()
""", False, 'reading a REPO path is not mutating one'),
    ("""
def go():
    open(os.path.join(REPO, 'x'), 'wb')
""", False,
     'AND A LIMIT, LOCKED RATHER THAN DISCOVERED: the path must be bound to a '
     'NAME first. An inline os.path.join inside the open() call is NOT seen, '
     'and that is a false negative this fixture makes visible instead of '
     'leaving for somebody to find'),
    ("""
def go():
    x = 1
""", False, 'a probe that writes nothing at all'),
)


def run_fixtures():
    """[] when every hand-built case classifies correctly."""
    bad = []
    for src, want, why in FIXTURE_CASES:
        got = mutates_repo_path(src)
        if got != want:
            bad.append('EXPECTED %s, got %s -- %s' % (want, got, why))
    return bad


def main(argv):
    # ── THE LOCK RUNS ON THE REAL RUN AND PRINTS, not behind a flag ─────────
    # A self-test that only runs when somebody passes --selftest is a control
    # with a shorter name, and the person reading a clean line is not passing it.
    _bad = run_fixtures()
    if _bad:
        print('CRITERIA LOCK FAILED -- %d of %d fixtures misclassified. NOTHING '
              'REAL WAS JUDGED:' % (len(_bad), len(FIXTURE_CASES)))
        for b in _bad:
            print('  ! %s' % b)
        return 2
    print('criteria lock: %d/%d fixtures classify correctly, on hand-built '
          'sources only' % (len(FIXTURE_CASES), len(FIXTURE_CASES)))
    return _main(argv)


def _main(argv):
    rows, unreadable, structural = [], [], []
    cache = {}
    for path in sorted(glob.glob(os.path.join(REPO, 'tests', '**', '*_probe.py'), recursive=True)):
        rel = os.path.relpath(path, REPO).replace(os.sep, '/')
        try:
            consts, muts = read_probe(path)
        except Exception as e:
            unreadable.append((rel, '%s: %s' % (type(e).__name__, str(e)[:60])))
            continue
        if not muts:
            continue               # not a mutation probe; nothing to check
        for entry in muts:
            target, old = resolve(consts, entry)
            if target == STRUCTURAL or (target and old is None):
                structural.append((rel, str(entry[0])[:70]))
                continue
            if not target:
                # NAMES THE CANDIDATES rather than saying only "unresolved".
                # The old message was wrong as well as unhelpful: it said the
                # target was unresolved for arms whose target had resolved.
                _sub, cands = sole_subject(consts)
                why = ('the probe declares %d candidate subject file(s) (%s) and '
                       'the arm names none of them, so which file it mutates '
                       'cannot be decided' % (len(cands), ', '.join(cands))
                       if cands else
                       'the probe declares no resolvable subject file at all')
                unreadable.append((rel, 'arm %r: %s' % (str(entry[0])[:40], why)))
                continue
            if target not in cache:
                cache[target] = io.open(target, encoding='utf-8', errors='replace').read()
            if isinstance(old, tuple):          # ('re', pattern) -- see element()
                try:
                    n = len(re.findall(old[1], cache[target]))
                except re.error as e:
                    unreadable.append((rel, 'arm %r: the pattern will not compile: %s'
                                       % (str(entry[0])[:40], e)))
                    continue
            else:
                n = cache[target].count(old)
            rows.append({'probe': rel,
                         'target': os.path.relpath(target, REPO).replace('\\', '/'),
                         'arm': str(entry[0])[:70], 'matches': n})

    # -- SECOND SECTION: a probe that mutates a tracked file IN PLACE must
    # refuse an import. Same family as a stale anchor -- both are a probe
    # being unsafe to touch in a way nothing announces. See the docstring
    # for the live incident that produced this.
    unguarded = []
    for path in sorted(glob.glob(os.path.join(REPO, 'tests', '**', '*_probe.py'),
                                 recursive=True)):
        rel = os.path.relpath(path, REPO).replace('\\\\', '/')
        body = io.open(path, encoding='utf-8', errors='replace').read()
        # DETECTED BY PARSING, NOT BY GREP, AND THE THIRD VERSION IS THE FIRST
        # CORRECT ONE. v1 flagged any `open(x, "wb")` and caught six probes that
        # write only into a temp worktree -- the safe pattern. v2 narrowed to a
        # target built from REPO/ROOT and then flagged THIS TOOL'S OWN PROBE,
        # because that probe contains the unsafe pattern as a FIXTURE STRING.
        # A checker matching a quoted example instead of live code is the exact
        # class tools/comment_quote_check.py exists for -- third instance in two
        # days, and this time in the tool written the same week. ast cannot see
        # inside a string literal, so parsing removes the class rather than
        # patching the symptom.
        in_place = mutates_repo_path(body)
        if not in_place:
            continue
        guarded = any(m in body for m in (
            "__name__ == '__main__'",
            '__name__ == "__main__"',
            "__name__ != '__main__'"))
        if not guarded:
            unguarded.append(rel)

    bad = [r for r in rows if r['matches'] != 1]
    by_probe = {}
    for r in rows:
        by_probe.setdefault(r['probe'], []).append(r)

    if '--json' in argv:
        print(json.dumps({'arms': rows, 'unreadable': unreadable}, indent=1))
    else:
        print('MUTATION ANCHOR CHECK -- report only, nothing was run and nothing written')
        print('  probes with a MUTATIONS list : %d' % len(by_probe))
        print('  anchors checked              : %d' % len(rows))
        print('  anchors NOT matching exactly once: %d' % len(bad))
        print('  could not read               : %d  (NOT a pass)' % len(unreadable))
        for p in sorted(by_probe):
            arms = by_probe[p]
            b = sum(1 for a in arms if a['matches'] != 1)
            print('    %-46s arms=%-3d bad=%d' % (p, len(arms), b))
        for r in bad:
            print('\n  %s' % r['probe'])
            print('      ANCHOR-%d in %s' % (r['matches'], r['target']))
            print('      %s' % r['arm'])
            print('      zero means the target was refactored; more than one means the'
                  ' arm probes whichever came first, i.e. neither on purpose.')
        for p, why in unreadable:
            print('\n  COULD NOT READ  %s' % p)
            print('      %s' % why)
        print('')
        if structural:
            print('  arms with NO TEXT ANCHOR (a transform function, nothing to '
                  'rot): %d' % len(structural))
            for rel, arm in structural:
                print('      %s  %s' % (rel, arm))
            print('      Not checked here, which is correct -- but printed,')
            print('      because an exclusion nobody sees is how a real stale')
            print('      anchor would hide inside the category that excuses it.')
        print('  probes that mutate in place and do NOT refuse an import: %d'
              % len(unguarded))
        for u in unguarded:
            print('      %s' % u)
        if unguarded:
            print('      An import RUNS these, and an interrupted import leaves the')
            print('      mutation on disk. Add at the top:')
            print('          if __name__ != "__main__": raise RuntimeError(...)')
        print('\n  NOTE: this checks that an anchor matches ONCE. It cannot tell whether')
        print('  it matches the RIGHT code -- an anchor that drifts onto a different')
        print('  branch stays unique and stays invisible here. See the module docstring.')

    if unreadable:
        return 2
    return 1 if (bad or unguarded) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
