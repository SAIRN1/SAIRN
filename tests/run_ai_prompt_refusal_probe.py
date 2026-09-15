"""tests/run_ai_prompt_refusal_probe.py

Run:  python tests/run_ai_prompt_refusal_probe.py

The control pair for tools/ai_prompt_refusal_check.py.

A CONTROL IS ONLY A CONTROL WHEN IT ASSERTS BOTH DIRECTIONS:

    plant the defect -> the checker must REPORT it   (non-zero exit)
    plant clean code -> the checker must STAY SILENT (zero exit)

A check that always reports passes the first alone. A check that never reports
passes the second alone. Only the pair says anything -- and `checkblocks.py`
always exited 0 for months precisely because nobody had written the first half.

EVERY PLANT ASSERTS IT LANDED. When an anchor rots, str.replace silently does
nothing, the checker runs against an UNCHANGED file, and "it exited 0" is then
reported as the clean arm passing. tools/sabotage_control_check.py exists
because 23 of 39 controls on this platform had drifted into exactly that state.

NOTHING IS MUTATED IN THIS CLONE -- every plant is written to a temporary file.

── THE THREE DEFECTS THESE ARMS WERE WRITTEN AFTER, NOT BEFORE ─────────────
Sections D, E and F exist because the checker had all three of these while being
built, and none of them was caught by the blind lock:

  D  `_value_expr` was not string-aware, so the first comma INSIDE a prompt's
     own English prose ended the expression. `sairnfreedom.html:4066` really
     does end `...'+extra+VA_CLAIM_REFUSAL`, and the walk stopped at the comma
     in "on a page you read, and always name the page" -- reporting two
     COMPLIANT sites as missing their own refusal. Nine findings became four.
     The lock said 9/9 throughout: not one fixture had a comma inside a string,
     so it was silent on the commonest shape in the tree.

  E  the population counters were incremented by the FIXTURE run as well as the
     sweep, because `run_fixtures()` calls the same `rule()`. The first report
     read "18 sites, 10 compliant, 4 flagged" -- which does not add up, and the
     arithmetic is the only reason it was noticed. Disciplines item 5 pointing
     the other way: the validation contaminating the measurement.

  F  the generated scaffold ran the lock on RAW fixture text while the sweep
     runs `strip_comments(src)`. The two fixtures whose entire subject is
     comment handling were therefore testing a code path the sweep never takes,
     and one of them passed for a completely unrelated reason.

Each is now an arm here AND a mutation control in section G, because a defect
that was only ever fixed is a defect that can come back.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['ai_prompt_refusal_check.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'ai_prompt_refusal_check.py')
FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else chr(10) + '        ' + str(detail)[:700]))
    if not cond:
        FAIL.append(name)


def run(*args, **kw):
    """Run the checker (or a mutant of it) and return (rc, output).

    ── WHY A MUTANT NEEDS PYTHONPATH, AND WHY THAT MATTERED A LOT ──────────
    The checker derives REPO from its own `__file__` and imports `checker_kit`
    from the tools directory beside it. A mutant copied to a temp directory
    therefore died on `ModuleNotFoundError: No module named 'checker_kit'` --
    BEFORE reaching a single line of the sabotaged logic.

    That crash exits 1. So four of the five mutation controls below were
    "going RED" because the mutant could not import, not because the sabotage
    worked: vacuous controls, passing while measuring nothing. Only G3 caught
    it, and only because its expected-not-RED code happened to collide with the
    crash's exit code.

    This is the defect these controls exist to prevent, arriving inside them --
    the same shape as an anchor that no longer matches. The import path is
    fixed here, and `control()` now additionally requires PROOF THE MUTANT RAN,
    because a future crash of some other kind would otherwise read as a pass
    again.
    """
    tool = kw.get('tool', TOOL)
    env = dict(os.environ)
    env['PYTHONPATH'] = (os.path.join(REPO, 'tools') + os.pathsep +
                         env.get('PYTHONPATH', ''))
    r = subprocess.run([sys.executable, tool] + list(args),
                       capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO, env=env)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def write(tmp, name, body):
    """Write a fixture file and PROVE it landed."""
    p = os.path.join(tmp, name)
    io.open(p, 'w', encoding='utf-8', newline='').write(body)
    back = io.open(p, encoding='utf-8').read()
    if back != body:
        raise AssertionError('the fixture did not land: ' + name)
    return p


CONST = "var X_RULE='CRITICAL RULE: never output a citation.';\n"


def site(system_expr, extra=''):
    return ("fetch(P,{body:JSON.stringify({app_id:'a',system:" + system_expr +
            ",messages:[{role:'user',content:q}]})});" + extra)


print('ai_prompt_refusal_check -- the control pair')
tmp = tempfile.mkdtemp(prefix='ai_prompt_refusal-probe-')
try:
    # ── A. the blind lock stands on its own ────────────────────────────────
    print('')
    print('--- A. the fixtures, in isolation ---')
    rc, out = run('--fixtures')
    ok('A1 the lock runs before any real file is opened',
       'before any real file' in out, out)
    ok('A2 the lock PASSES now that rule() is written',
       rc == 0 and 'fixtures correct' in out, 'rc=%d' % rc + chr(10) + out)
    ok('A3 --fixtures opens no real file at all',
       'files scanned' not in out, out)

    # ── B. the two directions ─────────────────────────────────────────────
    print('')
    print('--- B. plant the defect / plant clean code ---')
    bad = write(tmp, 'bad.html', CONST + site("'You help.'"))
    good = write(tmp, 'good.html', CONST + site("'You help.'+X_RULE"))
    rc_bad, out_bad = run(bad)
    ok('B1 the planted defect is REPORTED', rc_bad == 1,
       'rc=%d' % rc_bad + chr(10) + out_bad)
    ok('B2 ...and the report names the constant that is missing',
       'X_RULE' in out_bad, out_bad)
    rc_good, out_good = run(good)
    ok('B3 THE PAIR: clean code is left alone', rc_good == 0,
       'rc=%d' % rc_good + chr(10) + out_good)

    # ── C. the narrowings that keep it from being a design opinion ────────
    print('')
    print('--- C. what it must NOT flag ---')
    nocon = write(tmp, 'nocon.html', site("'You help.'"))
    rc_n, out_n = run(nocon)
    ok('C1 an app that defines NO constant is not told to write one',
       rc_n == 0, 'rc=%d' % rc_n + chr(10) + out_n)

    cfg = write(tmp, 'cfg.html', CONST + "var cfg={system:'linux',arch:'x64'};")
    rc_c, out_c = run(cfg)
    ok('C2 a system: property with no messages sibling is not an AI call',
       rc_c == 0, 'rc=%d' % rc_c + chr(10) + out_c)

    # The real sairnvet false positive, in the file rather than only in the
    # tool's own fixture list -- driven through the CLI so a wiring mistake
    # cannot hide behind a function-level pass.
    dom = write(tmp, 'dom.html', CONST +
                "function searchDiagnoses(){var system=document."
                "getElementById('dx-system').value;return rows.filter("
                "function(r){return r.system===system;});}")
    rc_d, out_d = run(dom)
    ok('C3 FP1: a body-system <select> named `system` is not an AI call',
       rc_d == 0, 'rc=%d' % rc_d + chr(10) + out_d)

    # ── D. THE STRING-AWARENESS DEFECT (was live, found in the first sweep) ─
    print('')
    print('--- D. a comma inside the prompt prose ---')
    prose = write(tmp, 'prose.html', CONST +
                  site("'You read a page, and you always name it.'+X_RULE"))
    rc_p, out_p = run(prose)
    ok('D1 a comma in the prose does not sever the constant reference',
       rc_p == 0, 'rc=%d' % rc_p + chr(10) + out_p)
    prose2 = write(tmp, 'prose2.html', CONST +
                   site("'You read a page, and you always name it.'"))
    rc_p2, out_p2 = run(prose2)
    ok('D2 ...and prose commas still cannot HIDE a missing constant',
       rc_p2 == 1, 'rc=%d' % rc_p2 + chr(10) + out_p2)
    # The other direction of the same defect: a semicolon stop. Without it the
    # walk ran into the NEXT statement and borrowed its compliance.
    neigh = write(tmp, 'neigh.html', CONST + site("'You help.'") + '\n' +
                  site("'You also help.'+X_RULE"))
    rc_ng, out_ng = run(neigh)
    ok('D3 a site cannot borrow compliance from the statement below it',
       rc_ng == 1 and out_ng.count('! ') >= 1,
       'rc=%d' % rc_ng + chr(10) + out_ng)

    # ── E. THE DENOMINATOR (was contaminated by the lock) ─────────────────
    print('')
    print('--- E. the published population ---')
    rc_e, out_e = run(bad, good, prose, prose2)
    ok('E1 the population is published at all',
       'AI call sites inside those files' in out_e, out_e)
    nums = dict(re.findall(r'(files defining a rule constant|AI call sites '
                           r'inside those files|\.\.\.of which carry a '
                           r'constant|\.\.\.of which do not)\s*:\s*(\d+)',
                           out_e))
    exam = int(nums.get('AI call sites inside those files', -1))
    comp = int(nums.get('...of which carry a constant', -1))
    miss = int(nums.get('...of which do not', -1))
    ok('E2 THE IDENTITY: compliant + flagged == sites examined',
       exam >= 0 and comp + miss == exam,
       'examined=%s compliant=%s flagged=%s' % (exam, comp, miss))
    ok('E3 the fixtures are NOT inside the measurement',
       exam == 4, 'four planted sites, so examined must be 4, got %s' % exam)
    ok('E4 the model-obedience limit is restated in the output',
       'does not and cannot show the model obeys' in out_e, out_e)

    # ── F. A SOURCE THAT YIELDS ZERO IS A REFUSAL ─────────────────────────
    # Not reachable by scoping to files (the refusal is deliberately confined
    # to a whole-tree sweep, because a file list naming only constant-free
    # files is a legitimate request rather than a lost subject). Asserted on
    # the code path instead, which is the honest scope for this arm and is
    # said out loud rather than quietly skipped.
    print('')
    print('--- F. a lost subject is not a clean run ---')
    src = io.open(TOOL, encoding='utf-8').read()
    ok('F1 the zero-constant case appends to could_not_run, not findings',
       re.search(r"if POP\['files_with_consts'\] == 0 and not args:\s*\n"
                 r"(?:\s*#.*\n)*\s*could_not_run\.append", src),
       'the refusal branch is not wired to could_not_run')
    ok('F2 ...and says it is a REFUSAL rather than a pass',
       'That is a REFUSAL, not a clean run' in src, 'wording missing')

    # ── G. MUTATION CONTROLS -- each proves its own sabotage landed ────────
    print('')
    print('--- G. mutation controls: five ways to break it ---')
    mut_tool = os.path.join(tmp, 'mutant.py')

    def control(name, anchor, replacement, args, expect_rc_not):
        shutil.copy(TOOL, mut_tool)
        body = io.open(mut_tool, encoding='utf-8').read()
        if anchor not in body:
            ok(name + ' -- SABOTAGE APPLIED', False,
               'ANCHOR NO LONGER MATCHES, so this control cannot fail and is '
               'worthless: %r' % anchor[:120])
            return
        patched = body.replace(anchor, replacement, 1)
        if patched == body:
            ok(name + ' -- SABOTAGE APPLIED', False,
               'the replacement changed nothing')
            return
        io.open(mut_tool, 'w', encoding='utf-8', newline='').write(patched)
        back = io.open(mut_tool, encoding='utf-8').read()
        ok(name + ' -- sabotage applied (%+d bytes, anchor matched)'
           % (len(patched) - len(body)),
           back == patched, 'the mutant did not land on disk')
        rc_m, out_m = run(*args, tool=mut_tool)
        # PROOF IT RAN, CHECKED BEFORE THE VERDICT IS BELIEVED. A mutant that
        # crashes on import also exits non-zero, which is indistinguishable
        # from the sabotage working unless something demands evidence the
        # sabotaged code was reached. Four controls here passed on an import
        # crash before this arm existed. `Traceback` is checked too, because a
        # crash LATER than the lock would still print the banner.
        reached = 'BLIND LOCK' in out_m and 'Traceback' not in out_m
        ok(name + ' -- the mutant actually RAN (not a crash)', reached,
           'no evidence the sabotaged code was reached:' + chr(10) + out_m)
        ok(name + ' -- and it goes RED', reached and rc_m != expect_rc_not,
           'expected NOT %d, got %d%s' % (expect_rc_not, rc_m, chr(10) + out_m))

    # 1. the string-awareness defect, restored verbatim.
    control('G1 _value_expr stops being string-aware',
            "        if quote:", "        if False:", [prose], 0)

    # 2. the lock runs on raw text again -- the scaffold's own mismatch.
    # ANCHOR UPDATED 2026-09-14 when run_fixtures() was rewritten to check the
    # finding KIND as well as flag/no-flag. The control REFUSED rather than
    # silently patching nothing, which is the behaviour that makes it worth
    # having: `got = bool(rule(...))` no longer exists in the tool.
    control('G2 the lock stops running the sweep\'s path',
            'got_list = rule(name, strip_comments(src))',
            'got_list = rule(name, src)', ['--fixtures'], 0)

    # G7: THE R3 CLASSIFICATION ITSELF. Without this, the post-call-control
    # split is unguarded -- and its whole purpose is to stop a site with a real
    # control being read at the same severity as one with nothing. Disabling
    # the detector must make the lock refuse, because two fixtures differ in
    # kind alone.
    control('G7 the post-call control detector stops seeing controls',
            '        ctrl = POSTCALL_CONTROL_RE.search(after)',
            '        ctrl = None', ['--fixtures'], 0)

    # 3. the population is contaminated by the fixtures again.
    control('G3 the fixture run is left inside the denominator',
            '    for _k in POP:\n        POP[_k] = 0',
            '    pass',
            [bad, good, prose, prose2], 1)

    # 4. an app with no constant gets flagged -- the design-opinion failure.
    control('G4 it starts telling constant-free apps to write one',
            '    if not consts:', '    if False:', [nocon], 0)

    # 5. the envelope narrowing is dropped, so config objects become AI calls.
    control('G5 the messages sibling stops being required',
            '        if not ENVELOPE_RE.search(near):',
            '        if False:', [cfg], 0)

    # The tool itself is untouched by any of that.
    ok('G6 tools/ai_prompt_refusal_check.py is byte-identical afterwards',
       io.open(TOOL, encoding='utf-8').read() == src,
       'the real tool was mutated')

finally:
    shutil.rmtree(tmp, ignore_errors=True)

print('')
if FAIL:
    print('ai_prompt_refusal: %d ARM(S) FAILED -- %s' % (len(FAIL), ', '.join(FAIL)))
    sys.exit(1)
print('ai_prompt_refusal: all arms pass')
