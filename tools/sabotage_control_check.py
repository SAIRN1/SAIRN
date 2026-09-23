"""Does a negative control prove it actually broke its target?

    python tools/sabotage_control_check.py --fixtures    # the blind lock alone
    python tools/sabotage_control_check.py
    python tools/sabotage_control_check.py --json

── WHY, AND IT HAPPENED TWICE IN ONE FILE ────────────────────────────────
A negative control sabotages a real source file, runs the checker, and asserts
it goes red. The sabotage is almost always `src.replace('<anchor>', ...)`. When
the target is refactored the anchor stops matching, **str.replace silently does
nothing**, and the control then runs the checker against an UNMODIFIED file.

The two ways that goes wrong are both bad and only one is loud:

  * the arm FAILS, and somebody spends time debugging a tool that is working
    perfectly. That happened in tests/run_financial_invariant_probe.py when
    invariant_registry.js moved from `debit_total` to `debit_total_cents`;
  * the arm PASSES, because the checker legitimately reports nothing on a file
    nobody touched and the arm was written as "expect no findings". **A control
    that cannot break its target is indistinguishable from a control that
    works**, and it will report green forever.

The second is the reason this exists. The first is merely how it was noticed.

MEASURED on the day this was written: 17 probes sabotage a source file, and
ELEVEN of them never check that the sabotage applied.

── WHAT A GUARDED CONTROL LOOKS LIKE ─────────────────────────────────────
Any of these is enough, and the tool accepts all of them rather than demanding
one house style:

    assert old in src                      # the anchor is present before use
    assert mutated != src                  # the replacement changed something
    check('the anchor still matches', sab != src, ...)
    if src_after == src_before: raise       # explicit refusal

What is NOT enough is asserting only on the checker's verdict afterwards. That
is the shape the whole convention exists to catch.

── WHAT IT CANNOT SEE, said here rather than discovered later ───────────
  * a sabotage that applies but changes the WRONG thing -- an anchor that
    matched somewhere unintended. Uniqueness is a separate question, and
    tools/mutation_anchor_check.py is the tool for it;
  * a control whose assertion is simply wrong about what the checker should do;
  * probes that sabotage by writing a whole fixture file rather than patching a
    real one. Those have no anchor to go stale and are not counted.

Exit 0 when every sabotaging probe verifies its own sabotage, 1 when one does
not, 2 when the fixtures fail -- which means nothing real was scanned.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# BUMPED WITH THE CRITERIA, and that is the point of the string existing. It
# printed 2026-09-13.2 on the run that first accepted the uniqueness shape, so
# the output named criteria that had already moved -- a version stamp that does
# not travel with the thing it stamps is worse than none, because it is read as
# evidence. Any change to GUARDS, REPLACES or FIXTURES bumps this.
CRITERIA_VERSION = '2026-09-23.1'

# Writes a file AND builds the content with a replacement: the patch-a-real-file
# shape. A probe that only writes a fresh fixture has no anchor to rot.
# BROADENED after the blind lock caught a real BIAS in the first version.
# It required `.replace(` to be followed by a QUOTE, so `src.replace(old, new)`
# -- which is the GUARDED idiom, the one that names its anchor in a variable it
# can assert on -- was never judged at all. A pattern that cannot see the
# well-written probes would have reported the careless ones as the whole
# population. And WRITES missed a bare `write(p, m)` helper, which is how the JS
# probes do it.
WRITES = re.compile(r"open\([^)]*['\"]w['\"]|writeFileSync|write\(")
REPLACES = re.compile(r"\.replace\(")

# Any of these proves the probe checked its own sabotage landed.
GUARDS = (
    re.compile(r"assert\s+[\w\.\[\]']+\s+in\s+\w+"),          # assert old in src
    # ── CASE-INSENSITIVE ONLY, AND THE ATTEMPT TO GO FURTHER IS RECORDED
    # ── BECAUSE THE BLIND LOCK CAUGHT IT, 2026-09-16 ───────────────────────
    # These were lower-case-only, so a JS control holding the original in a
    # CONST -- `const ORIGINAL = fs.readFileSync(...)`, the house idiom for a
    # value that must not be reassigned -- was invisible. `re.I` fixes that and
    # is safe: a DIFFERENCE assertion is the guard, and it is always spelled
    # `!=`.
    #
    # THE SAME EDIT ALSO ADDED `==` AND `===`, AND THAT WAS WRONG. It credited
    # two probes immediately and both credits were false:
    #
    #   run_master_plan_probe.py:205   check(after == original, 'the document
    #                                  is restored byte-identical')
    #   run_selftest_independence_probe.py:61   '    if out == src:'
    #
    # The first is a RESTORE check -- it proves the probe put the file back,
    # which is the opposite end of the run from proving the sabotage landed.
    # The second is a STRING LITERAL of the code being sabotaged, not code at
    # all. An equality against the original cannot be told from a restore
    # assertion by any pattern, because they are the same text, so the
    # equality spelling is deliberately NOT accepted. A control that wants
    # credit for `if (m === ORIGINAL) refuse` has the uniqueness shape below
    # available and it is stronger anyway.
    re.compile(r"!=\s*(src|orig|before|_before|original)\b", re.I),
    re.compile(r"!==" + r"\s*(src|orig|before|_before|original|s)" + chr(92) + "b", re.I),
    # `if (m !== s) write(...)` -- the JS shape, where the SHORT name holds
    # the original. Matching only long names missed every JS probe.
    re.compile(r"if\s*\([^)]*!==[^)]*\)\s*write"),
    re.compile(r"assert\s+\w+\s*!=\s*\w+"),
    re.compile(r"anchor[^\n]{0,60}(match|found|applies|still)", re.I),
    re.compile(r"sabotage[^\n]{0,60}(applied|changed|matches)", re.I),
    # ── THE UNIQUENESS SHAPE, ADDED 2026-09-15, AND IT WAS THE STRONGEST ONE ──
    # This tool reported 11 UNGUARDED. Five of those eleven guard by COUNTING
    # the anchor and refusing unless it matches exactly once:
    #
    #   entitlement_freshness_control.py   assert n == 1, 'fixture invalid: ...'
    #   law_custody_attribution_probe.py   if n != 1: ...
    #   license_trial_gate_probe.py        .count(ob) == 1
    #   sairndental_write_failure_probe.py if n != 1: ...
    #   faults/run_fault_suite_probe.py    if n != 1: ...
    #
    # A COUNT IS STRICTLY STRONGER THAN THE PRESENCE SHAPES ABOVE. `assert old
    # in src` catches a rename and is blind to an anchor that matches in four
    # places; a count catches both, and `tools/guard_ablation.py` records four
    # real gates that `replace(..., 1)` would silently have collapsed into the
    # first one.
    #
    # SO THE TOOL WAS UNDER-CREDITING EXACTLY THE BEST-WRITTEN CONTROLS, which
    # inverts the signal it exists to give: a probe that did the harder thing
    # scored worse than one that did the easy thing. Found while consolidating
    # the class into tools/sabotage.py, by reading a flagged file and finding it
    # already guarded.
    re.compile(r"\.count\([^)]*\)\s*(?:!=|==)\s*1"),
    re.compile(r"\bif\s+n\s*!=\s*1\b"),
    re.compile(r"\bassert\s+n\s*==\s*1\b"),
    # ── THE SAME UNIQUENESS SHAPE IN JAVASCRIPT, ADDED 2026-09-16 ──────────
    # JS has no `str.count`, so the idiom is `s.split(anchor).length - 1`. The
    # tool had the Python spelling and not this one, and reported
    # tests/sairnbiz_po_recv_mutation_control.js -- which guards by uniqueness,
    # by difference AND by reading the bytes back -- as UNGUARDED on the day it
    # was written. That is the 2026-09-15 finding recurring in another language.
    #
    # THE ARGUMENT IS A VARIABLE, NOT A LITERAL, AND THAT IS THE WHOLE
    # NARROWING. A probe counting the CHECKER'S FINDINGS writes
    # `out.split('FINDING').length - 1` -- a literal, because the thing being
    # counted is known when the probe is written. An anchor guard splits on the
    # ANCHOR, which is a variable, because the thing being counted is the text
    # it is about to replace. Same distinction the Python negative fixture
    # already rests on, expressed structurally rather than through a variable
    # name.
    re.compile(r"\.split\(\s*[A-Za-z_$][\w$.]*\s*\)\.length\s*-\s*1"),
    # ── THE ABSENCE-AND-REFUSE SHAPE, ADDED 2026-09-16, AND IT IS THE FOURTH
    # ── TIME THIS TOOL HAS UNDER-CREDITED A WELL-WRITTEN CONTROL ───────────
    # Reported UNGUARDED while carrying a guard the vocabulary could not see:
    #
    #   run_invisible_in_pattern_probe.py  if anchor not in s:
    #                                          raise AssertionError('the
    #                                          SABOTAGE did not land: ...')
    #   run_new_checker_probe.py           the same, twice, on two anchors
    #   run_selftest_independence_probe.py if old not in ORIG: check(...
    #                                          'ANCHOR MISSING -- ... That is a
    #                                          could-not-tell and is not a pass')
    #
    # All three REFUSE on a missing anchor and say so in the language this
    # platform uses for a third state. `assert old in src` was already
    # accepted; `if old not in src: raise` is the same assertion written the
    # way a probe that wants a READABLE MESSAGE has to write it -- and the
    # better a probe's error message, the less likely it was to use `assert`.
    #
    # THE SIGNAL WAS INVERTED IN EXACTLY THE WAY THE 2026-09-15 NOTE ABOVE
    # DESCRIBES, for the same reason, in a third spelling. Recording it here
    # rather than only fixing it: a detector that knows one spelling reports
    # every other spelling as ABSENT, and absent reads as unguarded.
    #
    # NARROW ON PURPOSE, AND THE BLIND LOCK FORCED THE NARROWING. The first
    # version was `not\s+in\s+[\w.\[\]']+` followed by a refusal, and its own
    # negative fixture refused it: `if 'x' not in os.environ: raise
    # SystemExit(...)` is a CONFIG CHECK, matched that pattern, and guards no
    # sabotage at all. The criteria failed their own fixtures and nothing was
    # scanned, which is the lock doing exactly what it is for.
    #
    # BOTH OPERANDS MUST BE PLAIN IDENTIFIERS. An anchor guard reads `if anchor
    # not in s` or `if old not in ORIG` -- a name for the needle, a name for the
    # buffer. A config check reads `if 'x' not in os.environ`: a STRING LITERAL
    # on the left, a DOTTED ATTRIBUTE on the right. Neither can be a bare
    # identifier pair, so the distinction is structural rather than a guess
    # about what the names mean.
    #
    # And the refusal must follow within one line: `if x not in y: continue` is
    # control flow, and the second negative fixture holds that line.
    # ── `cannot(` IS A REFUSAL VERB TOO, ADDED 2026-09-23, AND IT IS THE
    # ── FIFTH TIME THIS TOOL HAS UNDER-CREDITED A WELL-WRITTEN CONTROL ────
    # The REVIEW-PROBE family -- five files -- reports a could-not-drive
    # through a local `cannot(n, why)` helper rather than by raising, because
    # these probes answer a numbered press-on and have to say WHICH one could
    # not be driven while still running the others. That is a better refusal
    # than `raise`, not a worse one: it names the arm, keeps the exit code
    # separate from a finding, and lets the remaining arms report.
    #
    # tests/cross_tenant_grader_declaration_review_probe.py carries BOTH
    # halves of the guard in that spelling --
    #
    #     if target not in real:
    #         cannot(2, 'the loop line ... was reworded; this arm has no
    #                    target and is NOT reporting agreement it did not
    #                    check')
    #     if neutered == real:
    #         cannot(2, 'the mutation did not land')
    #
    # -- and was reported UNGUARDED. The vocabulary was the only thing
    # missing, which is the same inverted signal this file's own comments
    # record four times above: a detector that knows one spelling reports
    # every other spelling as ABSENT, and absent reads as unguarded.
    #
    # NOTHING ELSE IS WIDENED. The structural narrowing is untouched -- both
    # operands still have to be bare identifiers, so `if 'x' not in
    # os.environ: cannot(...)` is still a config check and still refused by
    # the negative fixture that already holds that shape.
    re.compile(r"\b[A-Za-z_]\w*\s+not\s+in\s+[A-Za-z_]\w*\s*:\s*\n?"
               r"[^\n]{0,80}(?:raise|check\(|assert|sys\.exit|ok\(|cannot\()", re.I),
)


def strip_comments(src, js):
    lines = src.split('\n')
    marker = '//' if js else '#'
    return '\n'.join(l for l in lines if not l.strip().startswith(marker))


# A `.replace(` that can never touch a file. Stated as a narrow, named list
# rather than inferred: `datetime.replace(tzinfo=...)` is the stdlib's
# immutable-copy API and has nothing to do with source text.
NEVER_A_FILE = re.compile(r'\.replace\(\s*tzinfo\s*=')


def logical_lines(code):
    """Join continuations so an expression split across lines is one unit.

    `open(p,'w').write(` on one line and `src.replace(old,new))` on the next is
    the commonest shape in this repo, and a line-at-a-time reader sees a bare
    replace with no write anywhere near it.
    """
    out, buf, depth = [], '', 0
    for raw in code.split('\n'):
        buf = raw if not buf else buf + ' ' + raw.strip()
        depth += raw.count('(') + raw.count('[') - raw.count(')') - raw.count(']')
        if depth <= 0:
            out.append(buf)
            buf, depth = '', 0
    if buf:
        out.append(buf)
    return out


ASSIGNED = re.compile(r'^\s*(?:const|let|var)?\s*([A-Za-z_$][\w$]*)\s*=[^=]')

WRITE_CALL = re.compile(r'\b(?:write|writeFileSync)\s*\(')

# `x = src.replace(...)` -- the replace is what produces x. Not
# `x = json.load(open(p.replace(...)))`, where it produced a path.
ASSIGN_IS_REPLACE = re.compile(r'=\s*[\w$.\[\]\'"]+\.replace\(')


def write_arguments(line):
    """The argument text of every write call on one logical line.

    `open(dest, 'w').write(body)` yields `body` and NOT `dest`. That distinction
    is the whole point: a path variable sits on the write line without being
    what is written, and reading the line as a whole counts it as content.
    """
    out = []
    for m in WRITE_CALL.finditer(line):
        i, depth = m.end(), 1
        while i < len(line) and depth:
            if line[i] == '(':
                depth += 1
            elif line[i] == ')':
                depth -= 1
                if not depth:
                    break
            i += 1
        out.append(line[m.end():i])
    return out


def replace_feeds_a_write(code):
    """Does any `.replace(` result actually reach a file write?

    NARROWED 2026-09-13 (Cody, Michael's call). The previous test was
    file-level -- any write anywhere AND any replace anywhere -- so a probe
    that patched no file at all was judged and counted. Measured across the
    19 rows then outstanding: about NINE were `datetime.replace(tzinfo=None)`,
    scrubbing a checker's OUTPUT STRING, or path-separator normalisation.
    None of them has an anchor that can rot, so there was nothing to guard and
    no honest way to close them -- which is how a headline count inflates.

    Two shapes count, and they are the two this repo actually uses:
      * the replace sits inside the write call itself;
      * the replace is assigned to a name, and that name is later written.

    BOTH ARE JUDGED ON THE WRITE'S CONTENT ARGUMENT, NOT ON THE LINE. The first
    version of this narrowing asked whether the name appeared anywhere on a line
    containing a write, and a PATH variable does exactly that --
    `open(dest, 'w').write(body)` has `dest` on the write line while the thing
    being written is `body`. So `dest = p.replace('/', os.sep)` still counted,
    and two path-normalising probes stayed flagged. Sabotage is about CONTENT;
    the destination is not the payload.

    WHAT THIS STILL CANNOT SEE, said here rather than discovered later: a
    replace passed to a local helper that writes (`mutate(src.replace(...))`).
    Tracking that needs the helper's body, which is not done. The bias is now
    toward NOT judging, which loses a real row rather than inventing one.
    """
    lines = logical_lines(code)
    written_args = ' '.join(a for ln in lines for a in write_arguments(ln))
    written_names = set(re.findall(r'[A-Za-z_$][\w$]*', written_args))
    for ln in lines:
        if not REPLACES.search(ln) or NEVER_A_FILE.search(ln):
            continue
        # Inside the write's own argument text, not merely on the same line.
        if any('.replace(' in a and not NEVER_A_FILE.search(a)
               for a in write_arguments(ln)):
            return True
        m = ASSIGNED.match(ln)
        # ...and the replace must PRODUCE the assigned value, not merely occur
        # somewhere inside the expression that does. `doc = json.load(io.open(
        # os.path.join(wt, REG.replace('/', os.sep))))` assigns a parsed
        # document and is later written -- but the replace built the PATH. That
        # kept run_defect_register_probe flagged through two rounds of this
        # narrowing, which is how a heuristic stays wrong while getting closer.
        if m and m.group(1) in written_names and ASSIGN_IS_REPLACE.search(ln):
            return True
    return False


def analyse(rel, src):
    js = rel.endswith('.js')
    code = strip_comments(src, js)
    if not (WRITES.search(code) and REPLACES.search(code)):
        return None
    if not replace_feeds_a_write(code):
        return None
    guarded = any(g.search(code) for g in GUARDS)
    return {'file': rel, 'guarded': guarded}


# ── FIXTURES: hand-decided before the tests tree was scanned ──────────────
FIXTURES = [
    ('an unguarded replace-and-write is reported',
     "src = open(p).read()\nopen(p,'w').write(src.replace('a','b'))\n", False),
    ('a guarded one with `assert old in src` is not',
     "src = open(p).read()\nassert old in src\nopen(p,'w').write(src.replace(old,new))\n", True),
    ('a guarded one comparing before and after is not',
     "src = open(p).read()\nm = src.replace('a','b')\nassert m != src\nopen(p,'w').write(m)\n", True),
    ('a JS probe using !== src is not',
     "const s = read(p);\nconst m = s.replace('a','b');\nif (m !== s) write(p, m);\n", True),
    # ── ADDED 2026-09-15 WITH THE UNIQUENESS SHAPE ────────────────────────
    # The criterion is new, so it gets fixtures in BOTH directions before the
    # real number is believed. Without the negative one, "it recognises a
    # count" would also be satisfied by a pattern that matches any `.count(`
    # at all -- including a probe that counts findings and guards nothing.
    ('a guarded one that COUNTS the anchor and demands exactly one is not '
     'reported -- stronger than `old in src`, which is blind to four matches',
     "src = open(p).read()\nn = src.count(old)\nif n != 1: raise SystemExit(2)\n"
     "open(p,'w').write(src.replace(old,new,1))\n", True),
    ('...and the assert spelling of the same thing',
     "src = open(p).read()\nn = src.count(old)\nassert n == 1\n"
     "open(p,'w').write(src.replace(old,new,1))\n", True),
    ('NEGATIVE: counting the CHECKER\'S FINDINGS guards nothing and is still '
     'reported',
     "src = open(p).read()\nopen(p,'w').write(src.replace('a','b'))\n"
     "hits = out.count('FINDING')\nassert hits == 1\n", False),
    ('the review-probe family refuses through cannot() rather than raise, '
     'and that is a guard',
     "src = open(p).read()\nif old not in src:\n    cannot(2, 'no target')\n"
     "    return\nopen(p,'w').write(src.replace(old,new,1))\n", True),
    ('NEGATIVE: cannot() on a CONFIG value guards no sabotage -- the string '
     'literal and the dotted attribute are what separate them, not the verb',
     "if 'KEY' not in os.environ:\n    cannot(9, 'unconfigured')\n    return\n"
     "src = open(p).read()\nopen(p,'w').write(src.replace('a','b'))\n", False),
    ('CONTROL: a probe that writes a FRESH fixture is not judged at all',
     "open(p,'w').write('| A | B |\\n')\n", None),
    ('CONTROL: a probe that only reads is not judged',
     "src = open(p).read()\nassert 'x' in src\n", None),
    # ── ADDED 2026-09-13 WITH THE NARROWING. Not one of the seven fixtures
    # above contains a datetime or an output scrub, which is exactly why the
    # blind lock could not catch the bias this pass found -- a lock is only as
    # good as the shapes it imagines.
    ('CONTROL: datetime.replace(tzinfo=) beside a write is not judged',
     "open(p,'w').write('x')\nt = now.replace(tzinfo=None)\n", None),
    ('CONTROL: scrubbing a checker OUTPUT string is not judged',
     "open(p,'w').write('x')\nassert 'y' not in out.replace('write x','')\n", None),
    ('CONTROL: path-separator normalisation is not judged',
     "open(p,'w').write('x')\nq = REL.replace('/', os.sep)\n", None),
    ('a replace ASSIGNED then written IS judged, and unguarded here',
     "src = open(p).read()\nm = src.replace('a','b')\nopen(p,'w').write(m)\n", False),
    ('a replace INSIDE the write call is judged',
     "open(p,'w').write(src.replace('a','b'))\n", False),
    ('a write and a replace SPLIT ACROSS LINES is still one expression',
     "open(p,'w').write(\n    src.replace('a','b'))\n", False),
    ('CONTROL: a path built with replace, parsed, then written is not judged',
     "doc = json.load(open(REG.replace('/', os.sep)))\n" "open(p,'w').write(json.dumps(doc))\n", None),
    # ── THE ABSENCE-AND-REFUSE SHAPE, BOTH DIRECTIONS (2026-09-16.2) ──────
    # The two positives are the real idioms from the three probes this tool was
    # under-crediting. The two negatives are the whole narrowing: `not in`
    # followed by control flow, or asked about something that is not the
    # anchor, guards nothing and must stay reported.
    ('an anchor checked with `not in` and a RAISE is guarded -- the spelling a '
     'probe uses when it wants a readable message instead of a bare assert',
     's = open(p).read()\n'
     'if anchor not in s:\n'
     "    raise AssertionError('the SABOTAGE did not land')\n"
     "open(p,'w').write(s.replace(anchor,'b'))\n", True),
    ('...and with a failing CHECK instead of a raise, which is how a probe '
     'that reports rather than crashes writes it',
     's = open(p).read()\n'
     'if old not in ORIG:\n'
     "    check('ANCHOR MISSING -- not a pass', False, old)\n"
     "open(p,'w').write(s.replace(old,'b'))\n", True),
    ('NEGATIVE: `not in` followed by CONTINUE is control flow and guards '
     'nothing -- this is the line the narrowing rests on',
     's = open(p).read()\n'
     'if anchor not in s:\n'
     '    continue\n'
     "open(p,'w').write(s.replace(anchor,'b'))\n", False),
    ('NEGATIVE: a `not in` about something OTHER than the anchor, with the '
     'write still unguarded',
     's = open(p).read()\n'
     "if 'x' not in os.environ:\n"
     "    raise SystemExit('config missing')\n"
     "open(p,'w').write(s.replace('a','b'))\n", False),
    ('a GUARD IN A COMMENT does not count -- the check must be in the code',
     "# assert old in src\nsrc = open(p).read()\nopen(p,'w').write(src.replace('a','b'))\n", False),
    # ── ADDED 2026-09-16 WITH THE JS UNIQUENESS SHAPE AND THE CASE FIX ─────
    # Both directions before the real number is believed, exactly as the
    # 2026-09-15 addition did. The negative one is the load-bearing half: it is
    # what stops the new pattern from crediting any `.split(...).length - 1`,
    # including a probe that counts the CHECKER'S output and guards nothing.
    ('a JS control counting the ANCHOR by split is guarded -- the JS spelling '
     'of `src.count(old) != 1`',
     "const s = read(p);\nconst hits = s.split(anchor).length - 1;\n"
     "if (hits !== 1) throw new Error('stale anchor');\n"
     "write(p, s.replace(anchor, 'b'));\n", True),
    ('NEGATIVE: splitting the CHECKER\'S OUTPUT on a LITERAL counts findings, '
     'guards nothing, and is still reported',
     "const s = read(p);\nwrite(p, s.replace('a','b'));\n"
     "const hits = out.split('FINDING').length - 1;\n"
     "if (hits !== 1) throw new Error('x');\n", False),
    ('a JS control holding the original in an UPPERCASE const is guarded -- it '
     'was invisible while the name patterns were lower-case only',
     "const ORIGINAL = read(p);\nconst m = ORIGINAL.replace(a, b);\n"
     "if (m !== ORIGINAL) write(p, m);\n", True),
    # THE TWO NEGATIVES BELOW ARE THE ONES THAT CAUGHT A REAL OVER-CREDIT. The
    # first draft of the case fix also accepted `==`/`===`, and these two shapes
    # -- both lifted from probes in this repo -- were credited within seconds.
    ('NEGATIVE: an EQUALITY against the original is a RESTORE check, at the '
     'opposite end of the run from proving the sabotage landed',
     "src = open(p).read()\nopen(p,'w').write(src.replace('a','b'))\n"
     "after = open(p).read()\ncheck(after == original, 'restored byte-identical')\n",
     False),
    ('NEGATIVE: a guard quoted as a STRING LITERAL is not code, the same way a '
     'guard in a comment is not',
     "src = open(p).read()\nopen(p,'w').write(src.replace('a','b'))\n"
     "MUTATIONS = [('    if out == src:', '    if False:')]\n", False),
]


def run_fixtures():
    bad = []
    for name, src, want in FIXTURES:
        got = analyse('x.py', src)
        gv = None if got is None else got['guarded']
        if gv != want:
            bad.append((name, want, gv))
    return bad


def main(argv):
    bad = run_fixtures()
    print('SABOTAGE CONTROL CHECK -- criteria %s, report only' % CRITERIA_VERSION)
    if bad:
        print('  !! THE CRITERIA FAILED THEIR OWN FIXTURES. NOTHING WAS SCANNED.')
        for n, w, g in bad:
            print('     expected %-6s got %-6s %s' % (w, g, n))
        return 2
    print('  blind lock: %d/%d fixtures correct, run before the tests tree was read.'
          % (len(FIXTURES), len(FIXTURES)))
    if '--fixtures' in argv:
        return 0

    rows = []
    for root, _d, files in os.walk(os.path.join(REPO, 'tests')):
        for f in sorted(files):
            if not (f.endswith('.py') or f.endswith('.js')):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, REPO).replace(os.sep, '/')
            a = analyse(rel, io.open(p, encoding='utf-8', errors='replace').read())
            if a:
                rows.append(a)

    unguarded = [r for r in rows if not r['guarded']]
    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION, 'rows': rows,
                          'unguarded': [r['file'] for r in unguarded]}, indent=1))
        return 1 if unguarded else 0

    print('  probes that sabotage a real source file : %d' % len(rows))
    print('  of those, verifying the sabotage APPLIED : %d' % (len(rows) - len(unguarded)))
    print('  UNGUARDED                                : %d' % len(unguarded))
    print('')
    print('  An unguarded control can silently become a no-op on a rename. The')
    print('  loud outcome is an arm failing against a tool that works. THE QUIET')
    print('  ONE IS WORSE: an arm written as "expect no findings" keeps passing')
    print('  on a file nobody touched, and reports green forever.')
    for r in unguarded:
        print('    %s' % r['file'])
    if not rows:
        print('')
        print('  NOTHING MATCHED. That is not a clean result -- check the patterns')
        print('  still describe how probes in this repo sabotage a file.')
    return 1 if unguarded else 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
