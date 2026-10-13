#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""run_unproven_arm_probe.py -- the control pair for tools/unproven_arm_check.py.

WHY THIS EXISTS AND WHY IT IS NOT OPTIONAL. The checker reports ZERO findings
over the real tree, and zero is exactly the number a checker that cannot fire
also reports. This repo's standing rule is that criteria are locked against
SYNTHETIC FIXTURES before being believed on real data, and that the locking
runs in BOTH directions -- a fixture that must trip it and a fixture that must
not. Five of the twelve cross-domain disciplines are about this one hazard.

EVERY FIXTURE IS WRITTEN TO A FRESH tempfile.mkdtemp() AND NOTHING IS WRITTEN
INSIDE THE CLONE. The checker is driven through its real entry point with
--root pointing at the temp tree, so the exit code under test is the one a
caller would actually get, not an internal return value.

THE FIXTURE THAT MATTERS MOST IS F3. It is not invented: it is the verbatim
shape of tests/push_gate/check4_probe.py:526 --

    print('directly rather than reported UNPROVEN. The foreign refusal:')

a sentence ABOUT the b5 defect, inside the probe that FIXED it. The first
version of the checker counted it as an unproven mechanism. That is this
platform's own recurring defect shape -- a checker whose universe includes the
text that DESCRIBES its subject -- and it is the false positive the spec named
in advance. F3 locks it closed in both directions.

exit 0  every arm held
exit 1  an arm failed
exit 3  an arm could not be evaluated -- the rule this probe's own subject
        enforces, applied to this probe. UNPROVEN IS COUNTED, NOT PRINTED.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'unproven_arm_check.py')

CRITERIA_VERSION = '2026-10-13.1'

passed = 0
failed = 0
unproven = 0
FAILED = []
UNPROVEN_ARMS = []


def arm(name, fn):
    """Three outcomes, and the third one is COUNTED."""
    global passed, failed, unproven
    try:
        fn()
    except AssertionError as exc:
        failed += 1
        FAILED.append(name)
        print('  FAIL  %s' % name)
        print('        %s' % exc)
    except Exception as exc:                 # noqa: BLE001 -- see below
        # Any non-assertion error means the arm did not get to compare
        # anything. That is not a pass and it is not a failure of the subject;
        # it is an arm that was not evaluated, and it is counted as such.
        unproven += 1
        UNPROVEN_ARMS.append(name)
        print('  COULD NOT EVALUATE  %s' % name)
        print('        %s: %s' % (type(exc).__name__, exc))
    else:
        passed += 1
        print('  ok    %s' % name)


def run_tool(root=None, extra=None):
    cmd = [sys.executable, TOOL]
    if root:
        cmd += ['--root', root]
    if extra:
        cmd += extra
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True)
    return p.returncode, p.stdout


def fixture_tree(files):
    """{relative-path-under-tests: source} -> a temp repo root."""
    root = tempfile.mkdtemp(prefix='unproven_fix_')
    for rel, src in files.items():
        full = os.path.join(root, 'tests', rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as fh:
            fh.write(src)
    return root


# ── THE FIXTURES ──────────────────────────────────────────────────
# EVERY FIXTURE LIVES INSIDE ONE TRIPLE-QUOTED DATA BLOCK, which is the subject
# tool's OWN documented escape hatch rather than a trick: normalise() blanks
# triple-quoted regions precisely so a probe can carry its subject's shape
# without becoming an instance of it.
#
# MEASURED, NOT ANTICIPATED. The first version of this file built the fixtures
# by concatenating ordinary string literals and said so in a comment: "built by
# concatenation so this probe's own source carries no line that the checker
# would read as a verdict emission in THIS file." THAT REASONING WAS WRONG AND
# ARM 6 CAUGHT IT. The checker fired A2 on THIS FILE, line 127 --
# `sys.exit(1 if failed else 0)` sitting in a plain literal, in a file that also
# carries an UNPROVEN verdict label in another one. The probe reported
# 11 passed, 1 failed, and the one that failed was the arm asserting this probe
# is clean against its own subject. A concatenated literal is still a literal.
# Only the triple-quoted form is invisible to the tool, and the tool says so.
#
# <<<TQ>>> stands in for a literal triple quote, so the one fixture that must
# CONTAIN a triple-quoted string lives in this block too rather than being the
# single exception that re-opens the hole.

_TQ = '"' * 3

_FIXTURE_DATA = """
=== a1_pos
passed = 1
failed = 0
print('UNPROVEN  arm 1 -- the gate refused for a foreign reason')
print('%d passed, %d failed' % (passed, failed))
import sys
sys.exit(0 if failed == 0 else 1)
=== a1_neg
passed = 1
failed = 0
unproven = 0
unproven += 1
print('UNPROVEN  arm 1 -- the gate refused for a foreign reason')
print('%d passed, %d failed, %d unproven'
      % (passed, failed, unproven))
import sys
sys.exit(0 if (failed or unproven) == 0 else 1)
=== prose
passed = 1
failed = 0
print('directly rather than reported UNPROVEN. The foreign refusal:')
print('%d passed, %d failed' % (passed, failed))
import sys
sys.exit(0 if failed == 0 else 1)
=== comment
passed = 1
failed = 0
# an arm that cannot run is reported UNPROVEN, see the spec
print('%d passed, %d failed' % (passed, failed))
import sys
sys.exit(1 if failed else 0)
=== triplequote
passed = 1
failed = 0
FIXTURE = <<<TQ>>>
print('UNPROVEN  arm 1 -- the gate refused for a foreign reason')
<<<TQ>>>
print('%d passed, %d failed' % (passed, failed))
import sys
sys.exit(1 if failed else 0)
=== a2_pos
passed = 1
failed = 0
unproven = 0
unproven += 1
print('UNPROVEN  arm 1 -- the gate refused for a foreign reason')
print('%d passed, %d failed, %d unproven'
      % (passed, failed, unproven))
import sys
sys.exit(1 if failed else 0)
=== a2_neg
passed = 1
failed = 0
unproven = 0
unproven += 1
print('UNPROVEN  arm 1 -- the gate refused for a foreign reason')
print('%d passed, %d failed, %d unproven'
      % (passed, failed, unproven))
import sys
sys.exit(3 if unproven else (1 if failed else 0))
=== a3_pos
passed = 1
failed = 0
print('%d passed, %d failed, %d unproven'
      % (passed, failed, 0))
import sys
sys.exit(1 if failed else 0)
=== a2_pos_okflag
passed = 1
failed = 0
ok = True
unproven = 0
unproven += 1
print('UNPROVEN  arm 1 -- the gate refused for a foreign reason')
print('%d passed, %d failed, %d unproven'
      % (passed, failed, unproven))
import sys
sys.exit(0 if ok else 1)
=== a2_neg_delegate
import sys


def main():
    passed = 1
    failed = 0
    unproven = 0
    unproven += 1
    print('UNPROVEN  arm 1 -- the gate refused for a foreign reason')
    print('%d passed, %d failed, %d unproven'
          % (passed, failed, unproven))
    if unproven:
        return 3
    return 1 if failed else 0


sys.exit(main())
=== js_a1_pos
let pass = 1, fail = 0;
console.log('UNPROVEN  arm 1 -- foreign refusal');
console.log(pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
=== js_a1_neg
let pass = 1, fail = 0, unproven = 0;
unproven += 1;
console.log('UNPROVEN  arm 1 -- foreign refusal');
console.log(pass + ' passed, ' + fail + ' failed, '
            + unproven + ' unproven');
process.exit((fail || unproven) ? 1 : 0);
"""


def _parse_fixtures(blob):
    """Split the data block on `=== name` headers. REFUSES on an empty parse."""
    out, name, buf = {}, None, []
    NL = chr(10)
    seen = []
    for line in blob.split(NL):
        if line.startswith('=== '):
            if name is not None:
                out[name] = NL.join(buf).strip(NL) + NL
            name, buf = line[4:].strip(), []
            # A DUPLICATE HEADER IS REFUSED, not resolved. A dict keeps the
            # LAST definition and says nothing, so two fixtures under one name
            # means every arm using that name silently tests only one of them
            # -- and which one depends on file order. This block was edited
            # twice in one session and did briefly carry two `a2_pos_okflag`
            # headers, which is why the refusal is here rather than trusted to
            # care.
            assert name not in seen, (
                'duplicate fixture header "=== %s". A dict keeps the last '
                'definition silently, so two fixtures under one name make the '
                'earlier one dead weight that still looks tested.' % name)
            seen.append(name)
        elif name is not None:
            buf.append(line)
    if name is not None:
        out[name] = NL.join(buf).strip(NL) + NL
    assert len(out) >= 12, ('the fixture data block parsed to %d fixture(s). '
                            'An empty or short parse would make every arm below '
                            'assert against an empty string and pass, which is '
                            'the silent-pass shape this file exists to refuse.'
                            % len(out))
    return dict((k, v.replace('<<<TQ>>>', _TQ)) for k, v in out.items())


F = _parse_fixtures(_FIXTURE_DATA)


def signals_for(name, src, filename):
    """Drive the tool over a one-file temp tree and return the signal set."""
    root = fixture_tree({filename: src})
    try:
        code, out = run_tool(root)
        sigs = set()
        for line in out.split('\n'):
            for s in ('A1', 'A2', 'A3'):
                if line.startswith(s + '  '):
                    sigs.add(s)
        return sigs, code, out
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    print('UNPROVEN ARM PROBE -- criteria %s' % CRITERIA_VERSION)
    print('  subject: tools/unproven_arm_check.py')
    print('  every fixture is written to tempfile.mkdtemp(); nothing is')
    print('  written inside the clone.')
    print('')

    if not os.path.isfile(TOOL):
        print('COULD NOT RUN: %s is absent. This probe has no subject, so it' % TOOL)
        print('reports exit 3 rather than a pass -- a missing subject is not a')
        print('clean result, and folding it into one is the defect this whole')
        print('file is about.')
        return 3

    print('1. THE CONTROL PAIR -- A1 must FIRE, and must STAY SILENT')

    def a1_fires():
        sigs, code, out = signals_for('a1_pos', F['a1_pos'], 'run_a_probe.py')
        assert 'A1' in sigs, ('A1 did NOT fire on a file that prints an UNPROVEN '
                              'verdict with a plain "passed, failed" summary -- '
                              'the exact b5 defect. The checker cannot fire and '
                              'every zero it reports is decoration.\n%s' % out)
        assert code == 1, 'A1 fired but the exit code was %d, not 1' % code
    arm('1a. A1 FIRES on verdict-printed-never-counted (the b5 defect)', a1_fires)

    def a1_silent():
        sigs, code, out = signals_for('a1_neg', F['a1_neg'], 'run_b_probe.py')
        assert 'A1' not in sigs, ('A1 fired on a file whose summary DOES carry '
                                  'the unproven count -- a false positive on the '
                                  'correct shape, which is how a checker gets '
                                  'switched off.\n%s' % out)
    arm('1b. A1 STAYS SILENT when the summary carries the count', a1_silent)

    print('')
    print('2. THE NAMED FALSE POSITIVE -- prose, comments, and fixture bodies')

    def prose_silent():
        sigs, code, out = signals_for('prose', F['prose'], 'run_c_probe.py')
        assert not sigs, ('a SENTENCE containing the word tripped the checker. '
                          'This is the verbatim check4_probe.py:526 shape and '
                          'the false positive the spec named in advance.\n%s'
                          % out)
        assert code == 0, 'prose fixture exited %d, expected 0' % code
    arm('2a. a PROSE sentence (check4_probe.py:526 verbatim) trips NOTHING',
        prose_silent)

    def comment_silent():
        sigs, _, out = signals_for('comment', F['comment'], 'run_d_probe.py')
        assert not sigs, 'a COMMENT mention tripped the checker:\n%s' % out
    arm('2b. a COMMENT mention trips NOTHING', comment_silent)

    def triple_silent():
        sigs, _, out = signals_for('triplequote', F['triplequote'],
                                   'run_e_probe.py')
        assert not sigs, ('a verdict print held INSIDE A TRIPLE-QUOTED STRING '
                          'tripped the checker. That is this probe\'s own shape, '
                          'so if this fires no probe for this tool can be '
                          'written at all.\n%s' % out)
    arm('2c. a verdict print inside a TRIPLE-QUOTED fixture body trips NOTHING',
        triple_silent)

    print('')
    print('3. A2 AND A3, each with its own negative')

    def a2_fires():
        sigs, code, out = signals_for('a2_pos', F['a2_pos'], 'run_f_probe.py')
        assert 'A2' in sigs, ('A2 did NOT fire on an exit expression that names '
                              'only the failure counter while an unproven '
                              'counter is set.\n%s' % out)
    arm('3a. A2 FIRES when the exit expression cannot see the unproven counter',
        a2_fires)

    def a2_silent():
        sigs, _, out = signals_for('a2_neg', F['a2_neg'], 'run_g_probe.py')
        assert 'A2' not in sigs, ('A2 fired although the exit expression names '
                                  'the unproven counter.\n%s' % out)
    arm('3b. A2 STAYS SILENT when the exit expression names it', a2_silent)

    def a2_okflag():
        sigs, _, out = signals_for('a2_pos_okflag', F['a2_pos_okflag'],
                                   'run_i_probe.py')
        assert 'A2' in sigs, ('A2 did NOT fire on the BOOLEAN OUTCOME FLAG form '
                              '`sys.exit(0 if ok else 1)`. That is the real shape '
                              'of tests/push_gate/check4_probe.py at c465743b~1 '
                              'and it is the half of the ablation the '
                              'fail-counter form missed: 1 of 2, not 2 of 2.\n%s'
                              % out)
    arm('3d. A2 FIRES on the boolean-outcome-flag form (check4_probe.py shape)',
        a2_okflag)

    def a2_delegate_silent():
        sigs, _, out = signals_for('a2_neg_delegate', F['a2_neg_delegate'],
                                   'run_j_probe.py')
        assert 'A2' not in sigs, ('A2 fired on `sys.exit(main())`, where main() '
                                  'returns 3 when unproven. That is a CORRECT '
                                  'shape, and a false positive on the correct '
                                  'shape is how a checker gets switched off. It '
                                  'is also why _OUTCOME_ID is a closed set of '
                                  'names rather than "any identifier".\n%s' % out)
    arm('3e. A2 STAYS SILENT on the delegating `sys.exit(main())` shape',
        a2_delegate_silent)

    def ablation_two_real_instances():
        """THE ABLATION, over the only two real instances, at c465743b~1.

        Not a fixture: both files are recoverable from git, so this measures
        the checker against the code that actually had the defect.
        """
        import subprocess as sp
        root = tempfile.mkdtemp(prefix='unproven_abl_')
        try:
            dest = os.path.join(root, 'tests', 'push_gate')
            os.makedirs(dest, exist_ok=True)
            got = []
            for fn in ('check4_probe.py', 'check7_probe.py'):
                p = sp.run(['git', 'show', 'c465743b~1:tests/push_gate/' + fn],
                           cwd=REPO, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
                if p.returncode != 0:
                    raise RuntimeError(
                        'git show c465743b~1:tests/push_gate/%s failed -- the '
                        'ablation subject is not reachable in this clone, so '
                        'this arm was NOT EVALUATED rather than passed: %s'
                        % (fn, p.stderr.decode('utf-8', 'replace')[:200]))
                with open(os.path.join(dest, fn), 'wb') as fh:
                    fh.write(p.stdout)
                got.append(fn)
            assert len(got) == 2, 'expected 2 ablation subjects, got %d' % len(got)
            code, out = run_tool(root)
            hit = set()
            for line in out.split('\n'):
                if line.startswith('A2  '):
                    hit.add(line.split()[1].split(':')[0].split('/')[-1])
            assert hit == {'check4_probe.py', 'check7_probe.py'}, (
                'A2 fired on %s of the 2 real instances (%s). The fail-counter '
                'form alone caught 1 of 2; this arm is what stops that being '
                'quoted as 2 of 2.\n%s' % (len(hit), sorted(hit) or 'none', out))
            print('       A2 fired on BOTH real instances at c465743b~1')
        finally:
            shutil.rmtree(root, ignore_errors=True)
    arm('3f. ABLATION -- A2 fires on BOTH real instances at c465743b~1',
        ablation_two_real_instances)

    def a3_fires():
        sigs, _, out = signals_for('a3_pos', F['a3_pos'], 'run_h_probe.py')
        assert 'A3' in sigs, ('A3 did NOT fire on a summary printing an unproven '
                              'count the file never sets -- the inverse defect, '
                              'and the one that keeps A1 honest.\n%s' % out)
    arm('3c. A3 FIRES on a printed count nothing ever sets', a3_fires)

    print('')
    print('4. THE OTHER LANGUAGE -- .test.js, same two directions')

    def js_fires():
        sigs, _, out = signals_for('js_a1_pos', F['js_a1_pos'], 'x.test.js')
        assert 'A1' in sigs, 'A1 did not fire on the JS form:\n%s' % out
    arm('4a. A1 FIRES on the .test.js form', js_fires)

    def js_silent():
        sigs, _, out = signals_for('js_a1_neg', F['js_a1_neg'], 'y.test.js')
        assert 'A1' not in sigs, 'A1 fired on the correct JS form:\n%s' % out
    arm('4b. A1 STAYS SILENT on the correct .test.js form', js_silent)

    print('')
    print('5. FAILS CLOSED -- an empty scan is exit 2, never a clean 0')

    def empty_is_2():
        root = tempfile.mkdtemp(prefix='unproven_empty_')
        try:
            os.makedirs(os.path.join(root, 'tests'), exist_ok=True)
            code, out = run_tool(root)
            assert code == 2, ('an empty tests/ tree exited %d. "0 findings over '
                               '0 files" is indistinguishable from a clean tree '
                               'and must be exit 2.\n%s' % (code, out))
            assert 'COULD NOT RUN' in out, 'exit 2 but no COULD NOT RUN line'
        finally:
            shutil.rmtree(root, ignore_errors=True)
    arm('5. an empty tests/ tree -> exit 2 COULD NOT RUN', empty_is_2)

    print('')
    print('6. THE SUBJECT APPLIED TO THIS PROBE AND TO ITSELF')

    def self_clean():
        code, out = run_tool(extra=['--file', os.path.abspath(__file__)])
        assert code == 0, ('this probe trips its own subject. It sets an '
                           'unproven counter, carries it in the summary and '
                           'names it in the exit expression, so it should be '
                           'the exemplar, not a finding.\n%s' % out)
    arm('6. this probe is CLEAN against its own subject', self_clean)

    print('')
    print('7. THE REAL TREE -- MEASURED AND REPORTED, NOT ASSERTED')
    code, out = run_tool()
    for line in out.split('\n'):
        if line.strip():
            print('     | %s' % line)
    print('     the real-tree result is the CURRENT COUNT this repo requires')
    print('     before a new checker is believed. It is reported here and NOT')
    print('     asserted: an assertion that the tree is clean would turn every')
    print('     future real finding into a failure of this probe.')

    print('')
    if UNPROVEN_ARMS:
        print('%d ARM(S) COULD NOT BE EVALUATED:' % len(UNPROVEN_ARMS))
        for n in UNPROVEN_ARMS:
            print('  - %s' % n)
    if FAILED:
        print('%d ARM(S) FAILED:' % len(FAILED))
        for n in FAILED:
            print('  - %s' % n)

    print('%d passed, %d failed, %d unproven' % (passed, failed, unproven))
    if unproven:
        print('EXIT 3: an arm was not evaluated. This is the rule the subject')
        print('enforces, applied to the probe that checks it.')
        return 3
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
