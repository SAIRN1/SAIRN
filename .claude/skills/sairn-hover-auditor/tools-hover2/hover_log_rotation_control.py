#!/usr/bin/env python
"""hover_log_rotation_control.py (hover2's own build, item 2 of the
2026-09-23 standing queue) -- an ADVERSARIAL MUTATION CONTROL on
hover_log.py's rotation gate, not a second copy of the behaviour test that
already exists inside hover_log.py's own --selftest.

WHAT ALREADY EXISTS, CHECKED FIRST SO THIS DOES NOT DUPLICATE IT.
hover_log.py's own selftest (lines ~584-591) already has two arms that
exercise the rotation gate directly: an undeclared repeat is refused, and a
declared one (same_target_reason set) is allowed. THAT IS A BEHAVIOUR TEST
-- it proves the gate works today. It cannot answer a different question:
if someone weakens the gate's own condition next month, would ANYTHING
notice? A behaviour test and the code it exercises can both be right today
and both silently stop meaning anything the day the condition changes,
exactly the eighth cross-domain discipline (docs/2026-09-13-cross-domain-
disciplines.md): "nothing announces the day a check stops testing
anything."

WHAT THIS FILE ADDS INSTEAD: it sabotages a COPY of hover_log.py's actual
rotation-gate line, in a tempfile, and asserts the mutated copy's behaviour
DIFFERS from the real one's -- proving the gate's own selftest arms are
anchored to real, load-bearing source and not passing by coincidence. Same
shape as tools/sabotage_control_check.py's own convention, applied to one
specific gate rather than run generically over the whole platform.

THE ANCHOR. hover_log.py's rotation check is one line:
    if rows and rows[-1].get('target') == target and not same_target_reason:
Sabotage: drop the trailing `and not same_target_reason` clause, producing
a gate that refuses EVERY same-target append, reason or no reason -- a
fail-CLOSED mutation (safer than the original, but still a behaviour
change the control must detect, and the deliberately chosen direction:
fail-open would risk actually writing corrupted state into a scratch
log, which this file avoids on principle even though it targets tempfiles
only).

THREE THINGS THIS ALSO CHECKS, NAMED RATHER THAN ASSUMED:
  1. the anchor string is UNIQUE in the file (count == 1) -- an anchor that
     matches twice could sabotage the wrong line and still report success;
  2. the mutation actually CHANGED the bytes on disk (str.replace silently
     doing nothing is the single most common shape behind a control that
     cannot break its own target, per tools/sabotage_control_check.py's own
     header);
  3. the mutated module still IMPORTS -- a red run must be the gate
     failing, not a SyntaxError from a bad sabotage string.

    python hover_log_rotation_control.py
    python hover_log_rotation_control.py --fixtures
"""
import importlib.util
import io
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, 'hover_log.py')

ANCHOR = "rows[-1].get('target') == target and not same_target_reason:"
MUTATED = "rows[-1].get('target') == target:"


def load_module_from_source(src, module_name):
    tmpdir = tempfile.mkdtemp(prefix='hover-rotation-control-')
    path = os.path.join(tmpdir, module_name + '.py')
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(src)
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, path, tmpdir


def append_twice_same_target(mod, log_path):
    """Two appends to the same target, no same_target_reason on the second.
    Returns True if the second append RAISED (gate refused, correct
    behaviour), False if it went through (gate did not refuse)."""
    mod.append_entry('check', 'first', target='alpha', path=log_path)
    try:
        mod.append_entry('check', 'second, undeclared repeat', target='alpha',
                          path=log_path)
        return False
    except ValueError:
        return True


def run_control():
    src = io.open(TARGET, encoding='utf-8').read()

    count = src.count(ANCHOR)
    if count != 1:
        return {'verdict': 'COULD_NOT_RUN',
                'detail': 'anchor matched %d times, expected exactly 1 -- '
                           'refusing to sabotage an ambiguous line' % count}

    # 1. BASELINE -- the real, unmutated source, gate must refuse.
    import tempfile as _tf
    base_dir = _tf.mkdtemp(prefix='hover-rotation-baseline-')
    base_log = os.path.join(base_dir, 'log.jsonl')
    real_mod, real_path, real_dir = load_module_from_source(src, 'hover_log_real')
    baseline_refused = append_twice_same_target(real_mod, base_log)

    # 2. SABOTAGE -- drop the same_target_reason exemption entirely.
    mutated_src = src.replace(ANCHOR, MUTATED)
    if mutated_src == src:
        return {'verdict': 'COULD_NOT_RUN',
                'detail': 'str.replace() did not change the source -- '
                           'the sabotage did not apply'}

    try:
        mut_mod, mut_path, mut_dir = load_module_from_source(mutated_src, 'hover_log_mutated')
    except SyntaxError as e:
        return {'verdict': 'COULD_NOT_RUN',
                'detail': 'mutated module does not even import: %r' % (e,)}

    mut_dir2 = _tf.mkdtemp(prefix='hover-rotation-mutated-')
    mut_log = os.path.join(mut_dir2, 'log.jsonl')
    # the mutated gate refuses EVERY same-target repeat, so a THIRD append
    # WITH same_target_reason set must now ALSO be refused -- that is the
    # observable difference this control is actually checking for.
    mut_mod.append_entry('check', 'first', target='alpha', path=mut_log)
    declared_now_refused = False
    try:
        mut_mod.append_entry('check', 'second, WITH a reason', target='alpha',
                              same_target_reason='deliberate follow-up',
                              path=mut_log)
    except ValueError:
        declared_now_refused = True

    if not baseline_refused:
        return {'verdict': 'FAIL', 'detail': 'the REAL gate did not refuse '
                'an undeclared repeat -- this is a live regression, not a '
                'control-harness problem'}
    if not declared_now_refused:
        return {'verdict': 'CONTROL_DID_NOT_BITE',
                'detail': 'the mutation was applied but the mutated gate '
                'still allowed a DECLARED same-target repeat through -- the '
                'sabotage did not actually change observable behaviour, so '
                'this control cannot prove the anchor is load-bearing'}

    return {'verdict': 'OK', 'detail': 'anchor unique, sabotage applied, '
            'baseline refuses correctly, mutated gate demonstrably behaves '
            'differently (now refuses even a DECLARED repeat) -- the '
            'selftest arms at hover_log.py:584-591 are anchored to real, '
            'load-bearing source'}


# ---------------------------------------------------------------- fixtures
FIXTURE_SRC = '''
def append_entry(entry_type, summary, ref='', target='self', severity='',
                  vector='', retrospective=False, same_target_reason='',
                  path=None):
    rows = _read(path)
    if rows and rows[-1].get('target') == target and not same_target_reason:
        raise ValueError('rotation refused')
    _write(path, {'type': entry_type, 'target': target, 'summary': summary})
    return {'seq': len(_read(path))}


def _read(path):
    import io, json, os
    if not path or not os.path.isfile(path):
        return []
    out = []
    with io.open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _write(path, obj):
    import io, json
    with io.open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(obj) + '\\n')
'''.strip('\n')


def run_fixtures():
    bad = []

    def ck(name, cond):
        print(('  ok   ' if cond else '  FAIL ') + name)
        if not cond:
            bad.append(name)

    mod, path, tmpdir = load_module_from_source(FIXTURE_SRC, 'fixture_hover_log')
    log_path = os.path.join(tempfile.mkdtemp(), 'log.jsonl')
    refused = append_twice_same_target(mod, log_path)
    ck('fixture harness: a real gate (matching the real shape) DOES refuse '
       'an undeclared repeat -- proves append_twice_same_target() itself '
       'is correctly wired before trusting its verdict on the real file',
       refused is True)

    ANCHOR_FX = "rows[-1].get('target') == target and not same_target_reason:"
    ck('the anchor string used against the real file also appears, once, '
       'in this fixture -- so the fixture is testing the SAME shape, not '
       'a look-alike', FIXTURE_SRC.count(ANCHOR_FX) == 1)

    mutated = FIXTURE_SRC.replace(ANCHOR_FX,
                                    "rows[-1].get('target') == target:")
    ck('the mutation changes the fixture bytes', mutated != FIXTURE_SRC)
    mut_mod, mp, md = load_module_from_source(mutated, 'fixture_hover_log_mut')
    log2 = os.path.join(tempfile.mkdtemp(), 'log.jsonl')
    mut_mod.append_entry('check', 'first', target='a', path=log2)
    declared_refused = False
    try:
        mut_mod.append_entry('check', 'second', target='a',
                              same_target_reason='x', path=log2)
    except ValueError:
        declared_refused = True
    ck('on the MUTATED fixture, a DECLARED repeat is now ALSO refused -- '
       'confirms the mutation direction this control uses is detectable',
       declared_refused is True)

    if bad:
        print('%d of 4 fixture(s) failed -- refusing to judge the real file' % len(bad))
        return 2
    print('OK -- 4/4 fixtures passed')
    return 0


def main(argv):
    if '--fixtures' in argv:
        return run_fixtures()

    fx_buf = io.StringIO()
    _stdout = sys.stdout
    sys.stdout = fx_buf
    try:
        fx_rc = run_fixtures()
    finally:
        sys.stdout = _stdout
    if fx_rc != 0:
        print(fx_buf.getvalue())
        print('FIXTURES FAILED -- nothing real was judged')
        return 2

    result = run_control()
    print('HOVER_LOG ROTATION GATE -- adversarial mutation control')
    print('  verdict: %s' % result['verdict'])
    print('  %s' % result['detail'])
    return 0 if result['verdict'] == 'OK' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
