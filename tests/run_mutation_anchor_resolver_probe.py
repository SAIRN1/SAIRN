"""Does mutation_anchor_check.py's resolver tell RESOLVED, STRUCTURAL and
COULD-NOT-READ apart -- and does it still REFUSE a genuine ambiguity?

    python tests/run_mutation_anchor_resolver_probe.py

WHY THIS EXISTS. On 2026-09-28 the checker was wired into
report_only_checks.REGISTRY and exiting 2 -- COULD NOT RUN -- permanently, on
84 arms across 19 probes. A wired check that cannot run is the same failure as
no check, and it was saying so in output nobody read. Not one of the 84 was a
stale anchor: every one was a declaration shape the resolver did not know.

THE DANGEROUS DIRECTION OF THE FIX IS THE OPPOSITE ONE. Teaching a resolver
more shapes is one edit away from teaching it to GUESS, and a wrong guess
counts an anchor in the wrong file and reports ANCHOR-0 against a healthy arm --
a false stale-anchor finding, which is worse than the silence it replaced. So
every arm below that adds a shape is paired with one asserting the refusal
still happens where the answer is genuinely unknown.

Fixtures are written to a temp directory and parsed. NOTHING under tests/ or
tools/ is touched, and no probe is imported -- importing a probe RUNS it, which
is the incident recorded in the checker's own read_probe() docstring.
"""
import io
import os
import re
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import mutation_anchor_check as m                            # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


tmp = tempfile.mkdtemp(prefix='sairn-anchor-resolver-')


def probe(body):
    """Write a fixture probe and return (consts, MUTATIONS) as the tool reads them."""
    p = os.path.join(tmp, 'fixture_probe.py')
    io.open(p, 'w', encoding='utf-8', newline='').write(body)
    return m.read_probe(p)


# Two REAL repo files, so a resolved target is a path that exists. Chosen for
# being stable and unrelated to anything under test.
SUBJ = 'tools/mutation_anchor_check.py'
SUITE = 'tests/run_mutation_anchor_resolver_probe.py'

try:
    print('\n1. THE FOUR DECLARATION SHAPES -- each was an exit-2 driver')

    # SHAPE A: a four-element entry naming a module constant. Worked before.
    c, muts = probe("import os\nAPP = os.path.join('tools', 'mutation_anchor_check.py')\n"
                    "MUTATIONS = [('a', APP, 'def resolve(', 'def zz(')]\n")
    t, old = m.resolve(c, muts[0])
    check('A. a @constant target resolves', t and t.endswith('mutation_anchor_check.py')
          and old == 'def resolve(', 'got %r %r' % (t, old))

    # SHAPE B: NO target element. The old fallback looked for a constant named
    # TARGET, which is a name ZERO of the 19 failing probes used.
    c, muts = probe("import os\nSERVING = os.path.join('tools', 'mutation_anchor_check.py')\n"
                    "SUITE = os.path.join('tests', 'run_mutation_anchor_resolver_probe.py')\n"
                    "MUTATIONS = [('b', 'def resolve(', ['x'])]\n")
    t, old = m.resolve(c, muts[0])
    check('B. no target element resolves to the SOLE NON-SUITE subject',
          t and t.endswith('mutation_anchor_check.py'),
          'got %r. The suite must be dropped first: a mutation probe mutates '
          'the subject and WATCHES the suite.' % t)

    # SHAPE C: an inline os.path.join in the target slot.
    c, muts = probe("import os\nA = os.path.join('tools', 'mutation_anchor_check.py')\n"
                    "B = os.path.join('tools', 'report_only_checks.py')\n"
                    "MUTATIONS = [('c', os.path.join('tools', 'report_only_checks.py'),"
                    " 'REGISTRY = [', 'ZZ = [')]\n")
    t, _old = m.resolve(c, muts[0])
    check('C. an INLINE os.path.join target resolves',
          t and t.endswith('report_only_checks.py'),
          'got %r -- and note the arm named its file MORE precisely than either '
          'constant, while the old message said it "names none of them"' % t)

    # SHAPE D: a two-element (label, build_function) entry.
    c, muts = probe("import os\nE = os.path.join('tools', 'mutation_anchor_check.py')\n"
                    "F = os.path.join('tools', 'report_only_checks.py')\n"
                    "def m1():\n    return {}\n"
                    "MUTATIONS = [('d', m1)]\n")
    t, old = m.resolve(c, muts[0])
    check('D. a transform-function entry is STRUCTURAL, not unreadable',
          t == m.STRUCTURAL and old is None,
          'got %r %r. Two candidate subjects AND no text anchor: there is '
          'nothing here that can rot, so "nobody knows" is the wrong answer.'
          % (t, old))

    print('\n2. THE REFUSALS -- what must still be COULD NOT READ')

    # A real text anchor, several candidate subjects, and the arm names none.
    # This is the one case where guessing would produce a FALSE ANCHOR-0.
    c, muts = probe("import os\nA = os.path.join('tools', 'mutation_anchor_check.py')\n"
                    "B = os.path.join('tools', 'report_only_checks.py')\n"
                    "MUTATIONS = [('e', 'def resolve(', ['x'])]\n")
    t, old = m.resolve(c, muts[0])
    check('a REAL anchor with two candidate subjects is REFUSED',
          t is None and old == 'def resolve(',
          'got %r. Picking one of two files here would count the anchor in the '
          'wrong file and report ANCHOR-0 against a healthy arm.' % t)

    # A named constant that exists NOWHERE is a typo and a real finding.
    c, muts = probe("import os\nA = os.path.join('tools', 'mutation_anchor_check.py')\n"
                    "MUTATIONS = [('f', NOPE, 'def resolve(', 'def zz(')]\n")
    t, _old = m.resolve(c, muts[0])
    check('a target naming something that exists NOWHERE stays unreadable',
          t is None,
          'got %r -- a name no module-level assignment or def produces is a '
          'typo, and swallowing it would hide a real broken arm' % t)

    # A name that EXISTS but is not a path is a buffer, not a typo.
    c, muts = probe("import os\nA = os.path.join('tools', 'mutation_anchor_check.py')\n"
                    "RAW, OTHER = open(A).read(), 1\n"
                    "MUTATIONS = [('g', RAW, 'def resolve(', 'def zz(')]\n")
    t, _old = m.resolve(c, muts[0])
    check('...but a name that EXISTS and is not a path is STRUCTURAL',
          t == m.STRUCTURAL,
          'got %r. RAW is assigned by TUPLE UNPACKING at module level -- the '
          'shape read_probe could not see, which made six arms read as '
          '"names a thing that does not exist" when it is one line up.' % t)

    print('\n3. THE CONTROL -- the resolver still DISCRIMINATES')
    # Without this, every arm above is satisfied by a resolver that returns the
    # same thing for everything.
    c1, m1_ = probe("import os\nA = os.path.join('tools', 'mutation_anchor_check.py')\n"
                    "MUTATIONS = [('x', A, 'def resolve(', 'def zz(')]\n")
    c2, m2_ = probe("import os\nA = os.path.join('tools', 'mutation_anchor_check.py')\n"
                    "B = os.path.join('tools', 'report_only_checks.py')\n"
                    "MUTATIONS = [('y', 'def resolve(', ['x'])]\n")
    c3, m3_ = probe("import os\nA = os.path.join('tools', 'mutation_anchor_check.py')\n"
                    "def t1():\n    return {}\n"
                    "MUTATIONS = [('z', t1)]\n")
    # CLASSIFIED THE WAY main() DOES, not by the target alone -- and the first
    # version of this control got that wrong and FIRED, correctly. A transform
    # arm on a probe with ONE subject resolves that subject and signals
    # structural through `old is None`, so comparing only resolve()[0] made two
    # different classifications look identical. A control that compares the
    # wrong field reports a discriminating tool as non-discriminating, which is
    # the same false-alarm direction the checker itself was fixed for.
    def classify(consts, entry):
        t, old = m.resolve(consts, entry)
        if t == m.STRUCTURAL or (t and old is None):
            return 'structural'
        if not t:
            return 'could-not-read'
        return 'resolved'
    outs = [classify(c1, m1_[0]), classify(c2, m2_[0]), classify(c3, m3_[0])]
    check('resolved / refused / structural are three DIFFERENT answers',
          sorted(outs) == ['could-not-read', 'resolved', 'structural'],
          'the resolver classified the three shapes as %r, so every arm above '
          'is checking one verdict repeatedly' % (outs,))

    print('\n4. THE REAL RUN -- it must now reach a verdict')
    import subprocess                                          # noqa: E402
    r = subprocess.run([sys.executable,
                        os.path.join(REPO, 'tools', 'mutation_anchor_check.py')],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=300)
    check('the checker exits 0 or 1, never 2', r.returncode in (0, 1),
          'rc=%s. Exit 2 means COULD NOT RUN, and this tool is WIRED -- a '
          'wired check that cannot run is the same failure as no check.\n%s'
          % (r.returncode, (r.stdout or '')[-600:]))
    out = r.stdout or ''
    check('...and reports ZERO could-not-read arms',
          'could not read               : 0' in out,
          [l for l in out.splitlines() if 'could not read' in l])
    # ── THE 16 WERE FIXED, AND THIS ARM ASKED TO BE UPDATED WHEN THEY WERE ──
    # 2026-10-06. The arm required a NON-ZERO bad-anchor count, so that "the
    # resolver started swallowing findings" and "the findings were fixed" could
    # not be confused. Its own failure message names the two readings and says
    # which action each needs. The second reading is the true one, and the
    # evidence is a count that went UP, not down:
    #
    #   at origin/main : 527 anchors checked, 2 NOT matching once, 5 could not read
    #   at this tip    : 533 anchors checked, 0 NOT matching once, 0 could not read
    #
    # The 2 bad anchors were in tests/claims/run_fileset_matcher_sabotage_probe.py
    # and both pointed at `return ('refuse' if shared else 'clear'), shared`,
    # which file_verdict() has not contained since the 2026-09-30 narrowing. They
    # were RE-POINTED to the lines carrying the same decisions, not deleted, and a
    # seventh arm was added for the narrowing itself -- hence +1. The 5
    # could-not-reads were tests/run_alf_scope_mutation_probe.py arms whose target
    # slot holds a SUITE GROUP label, now resolved through sole_subject(); their
    # anchors MATCH, which is the +5 and is the proof they were not swallowed. A
    # swallowed finding would have LOWERED the checked count, not raised it.
    #
    # SO THE ARM IS RE-POINTED AT THE PROPERTY IT WAS PROTECTING rather than at
    # the number: the resolver must still be ABLE to report a bad anchor, which
    # is checked by planting one, and the real run's checked-anchor count must not
    # fall below the floor the fix established.
    bad_line = [l for l in out.splitlines()
                if 'NOT matching exactly once' in l]
    checked = [l for l in out.splitlines() if 'anchors checked' in l]
    n_checked = 0
    for l in checked:
        # NOT `m` -- that is the module alias in this file, and shadowing it
        # turned the planted arm below into AttributeError on a re.Match.
        _mm = re.search(r'(\d+)', l)
        if _mm:
            n_checked = int(_mm.group(1))
    ANCHOR_FLOOR = 533
    check('the real run still INSPECTS at least as many anchors as the resolver '
          'fix established -- a swallowed finding lowers this count, it cannot '
          'raise it', n_checked >= ANCHOR_FLOOR,
          'anchors checked is %d, below the floor of %d: the resolver has started '
          'dropping arms rather than reading them. %s'
          % (n_checked, ANCHOR_FLOOR, checked))
    check('...and the bad-anchor count is REPORTED either way, so a zero is a '
          'measured zero rather than a missing line', bool(bad_line), out[-400:])
    # AND THE CAPABILITY ITSELF, planted rather than inferred from the real run:
    # a probe whose anchor cannot be found must still be reported.
    _dead = os.path.join(tmp, 'dead_probe.py')
    io.open(_dead, 'w', encoding='utf-8', newline='\n').write(
        "SUBJECT = 'tools/mutation_anchor_check.py'\n"
        "MUTATIONS = [('x. an anchor that does not exist anywhere', SUBJECT,\n"
        "              'this text is not in that file at all zzz', 'y')]\n")
    # read_probe() takes a PATH and resolve() takes (consts, entry) -- both of
    # which I had the wrong way round first, and the crash said so immediately.
    _c, _muts = m.read_probe(_dead)
    _p, _old = m.resolve(_c, _muts[0])
    _n = (io.open(_p, encoding='utf-8', errors='replace').read().count(_old)
          if _p and isinstance(_old, str) else None)
    check('PLANTED: an anchor that matches ZERO times is still counted as zero, '
          'so the resolver has not lost the ability to report one',
          _p and _n == 0, 'resolved=%r count=%r' % (_p, _n))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('\n%s  mutation_anchor_resolver probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
