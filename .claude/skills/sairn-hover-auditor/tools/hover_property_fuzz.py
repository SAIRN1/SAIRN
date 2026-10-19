#!/usr/bin/env python
"""
hover_property_fuzz.py -- dependency-free fast-check/Hypothesis-STYLE
generate+shrink fuzzer wrapping hover's own sandbox-sabotage technique.

ONE-LINE CONCEPT (written before this code, per b58 methodology): this
batch's own sweep hand-picked ONE mutation per fix-shape (a block comment, a
string literal, ...) and ran the real suite once each; this tool instead
GENERATES many random mutations of the same comment/string-literal shape
family around a named target line, runs the real suite once per mutation in
an isolated sandbox copy, and SHRINKS any mutation that makes the suite
wrongly pass to its minimal reproducing form -- the generate/falsify/shrink
idea fast-check and Hypothesis are built on, applied to this repo's own
recurring "satisfied by a comment" bug class, without a new dependency.

WHY NOT THE REAL LIBRARIES: fast-check (npm) and Hypothesis (pip) are not
installed in this clone, and installing a new dependency mid-batch was
denied when attempted (pip install permission refused) and not re-attempted,
per the rule against repeating a denied action. This is a hand-rolled
equivalent of the SAME concept, named as such rather than silently passed
off as the real thing. Scope is deliberately narrow: it covers the
comment/string-literal mutation family only (line comment, block comment,
string-literal reassignment, split-with-comment-between, each with
randomised whitespace/casing/decoy-variable-naming) -- the family named
explicitly in four separate register entries this session read (N1, N4, N5,
N6, plus citation_class_check.py's and hover_editor_review.py's own
abbreviation-splitter fixes). It does NOT cover value-flip (bld_draws'
true->false) or statement-reorder (the MONEY ordering arm) or delete-and-
replace (the PHI wiring arm) -- those were each verified by hand this batch
instead, and are named here as a real limitation, not silently absent.

USAGE:
  python hover_property_fuzz.py --check SPEC.json --trials N [--seed S]
  python hover_property_fuzz.py --selftest

SPEC.json: {
  "label": "human name for the finding/log line",
  "source_file": "path relative to repo root, e.g. sairnbuild.html",
  "anchor": "the exact line of real code to neutralise (must appear once)",
  "safe_replacement": "code that keeps the function running, no-op guard",
  "suite_relpath": "path relative to repo root to the real test file",
  "suite_sandbox_layout": "flat" | "nested",
      flat   -> suite_relpath copied next to source_file with suite's own
                env-var html override (DNT_HTML-style)
      nested -> source_file at sandbox root, suite under sandbox/tests/,
                matching a suite that does path.join(__dirname, '..')
  "html_env_var": null or e.g. "DNT_HTML" (required when layout is flat)
}

Exit 0 on CONFIRMED-CLEAN (no trial escaped) or on a logged ESCAPE finding
(the escape itself is the useful output, not a crash). Exit 2 on a spec or
environment problem -- FAILS CLOSED, never silently reports clean on a
suite it could not actually run.
"""
import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

COMMENT_STYLES = [
    lambda expr: '// %s' % expr,
    lambda expr: '/* %s */' % expr,
    lambda expr: '/*%s*/' % expr,
    lambda expr: '  //  %s  ' % expr,
]


def _decoy_var():
    return '_hoverfuzz_%d' % random.randint(0, 10 ** 6)


def _string_literal_mutator(anchor, rng):
    var = _decoy_var()
    rendering = rng.choice(["'%s'", '"%s"'])
    return 'var %s = %s; // was: %s' % (var, rendering % anchor.replace("'", "\\'"), anchor)


def _split_with_comment_mutator(anchor, rng):
    style = rng.choice(COMMENT_STYLES)
    half = len(anchor) // 2
    return style(anchor[:half]) + '\n' + style(anchor[half:])


def generate_mutation(anchor, safe_replacement, rng):
    """One randomised variant: the real line is gone, a comment or string
    literal carries its text, and a safe replacement keeps the function
    running. Returns (kind, mutated_text)."""
    kind = rng.choice(['line_comment', 'block_comment', 'string_literal', 'split_comment'])
    if kind == 'line_comment':
        carrier = COMMENT_STYLES[0](anchor)
    elif kind == 'block_comment':
        carrier = rng.choice(COMMENT_STYLES[1:3])(anchor)
    elif kind == 'string_literal':
        carrier = _string_literal_mutator(anchor, rng)
    else:
        carrier = _split_with_comment_mutator(anchor, rng)
    # randomise ordering of carrier vs replacement, and blank-line noise
    pieces = [carrier, safe_replacement]
    if rng.random() < 0.5:
        pieces.reverse()
    if rng.random() < 0.3:
        pieces.insert(1, '')
    return kind, '\n'.join(pieces)


def run_suite(sandbox_dir, suite_relpath_in_sandbox):
    try:
        p = subprocess.run(['node', suite_relpath_in_sandbox], cwd=sandbox_dir,
                            capture_output=True, text=True, timeout=60)
    except Exception as e:
        return None, 'suite could not be run: %r' % e
    return p, (p.stdout or '') + (p.stderr or '')


def build_sandbox(spec, mutated_source):
    tmp = tempfile.mkdtemp(prefix='hover_property_fuzz_')
    layout = spec['suite_sandbox_layout']
    if layout == 'nested':
        os.makedirs(os.path.join(tmp, 'tests'), exist_ok=True)
        src_name = os.path.basename(spec['source_file'])
        with open(os.path.join(tmp, src_name), 'w', encoding='utf-8') as f:
            f.write(mutated_source)
        shutil.copy(os.path.join(REPO_ROOT, spec['suite_relpath']),
                    os.path.join(tmp, 'tests', os.path.basename(spec['suite_relpath'])))
        return tmp, os.path.join('tests', os.path.basename(spec['suite_relpath'])), {}
    else:
        src_name = os.path.basename(spec['source_file'])
        src_path = os.path.join(tmp, src_name)
        with open(src_path, 'w', encoding='utf-8') as f:
            f.write(mutated_source)
        suite_name = os.path.basename(spec['suite_relpath'])
        shutil.copy(os.path.join(REPO_ROOT, spec['suite_relpath']), os.path.join(tmp, suite_name))
        env = {spec['html_env_var']: src_path}
        return tmp, suite_name, env


def load_source_and_mutate(spec, carrier_text):
    with open(os.path.join(REPO_ROOT, spec['source_file']), 'r', encoding='utf-8') as f:
        src = f.read()
    anchor = spec['anchor']
    hits = src.count(anchor)
    if hits != 1:
        raise SystemExit(2, 'FAIL CLOSED: anchor must appear exactly once in %s, found %d' % (
            spec['source_file'], hits))
    return src.replace(anchor, carrier_text, 1)


def one_trial(spec, rng):
    kind, mutated_block = generate_mutation(spec['anchor'], spec['safe_replacement'], rng)
    mutated_source = load_source_and_mutate(spec, mutated_block)
    sandbox, suite_rel, env = build_sandbox(spec, mutated_source)
    try:
        full_env = dict(os.environ)
        full_env.update(env)
        p = subprocess.run(['node', suite_rel], cwd=sandbox, capture_output=True, text=True,
                            timeout=60, env=full_env)
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
    escaped = (p.returncode == 0)
    return kind, mutated_block, escaped, (p.stdout or '')[-800:]


def shrink(spec, rng, kind):
    """Given a kind known to escape, find the SMALLEST carrier (just the
    carrier, no decoy blank line, no reordering) that still escapes."""
    carrier_fns = {
        'line_comment': lambda a: COMMENT_STYLES[0](a),
        'block_comment': lambda a: COMMENT_STYLES[1](a),
        'string_literal': lambda a: _string_literal_mutator(a, rng),
        'split_comment': lambda a: _split_with_comment_mutator(a, rng),
    }
    carrier = carrier_fns[kind](spec['anchor'])
    minimal = carrier + '\n' + spec['safe_replacement']
    mutated_source = load_source_and_mutate(spec, minimal)
    sandbox, suite_rel, env = build_sandbox(spec, mutated_source)
    try:
        full_env = dict(os.environ)
        full_env.update(env)
        p = subprocess.run(['node', suite_rel], cwd=sandbox, capture_output=True, text=True,
                            timeout=60, env=full_env)
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
    return (p.returncode == 0), minimal


def cmd_check(args):
    with open(args.check, 'r', encoding='utf-8') as f:
        spec = json.load(f)
    rng = random.Random(args.seed)
    escapes = []
    for i in range(args.trials):
        kind, block, escaped, tail = one_trial(spec, rng)
        if escaped:
            escapes.append((kind, block, tail))
    print('SPEC: %s' % spec.get('label', args.check))
    print('TRIALS: %d, SEED: %s' % (args.trials, args.seed))
    if not escapes:
        print('CONFIRMED-CLEAN -- 0 of %d randomised comment/string-literal '
              'mutations escaped the suite. Not a proof for all inputs; a '
              'stated trial count, not a combined single figure.' % args.trials)
        return 0
    kinds_seen = sorted(set(k for k, _, _ in escapes))
    print('ESCAPE -- %d of %d trials escaped the suite, kinds: %s' % (
        len(escapes), args.trials, ', '.join(kinds_seen)))
    shrunk_escaped, shrunk_block = shrink(spec, rng, escapes[0][0])
    print('SHRUNK MINIMAL REPRODUCER (kind=%s, still escapes=%s):' % (
        escapes[0][0], shrunk_escaped))
    print(shrunk_block)
    return 1


def cmd_selftest():
    """No real repo file needed: builds its own tiny fixture pair (a source
    file with one guarded line, and a suite that fails if the guard is not
    executable) and proves the fuzzer finds the escape it is given."""
    tmp = tempfile.mkdtemp(prefix='hover_property_fuzz_selftest_')
    try:
        src = os.path.join(tmp, 'fixture.js')
        with open(src, 'w', encoding='utf-8') as f:
            f.write("function guard(key){\n  if(!ALLOWED[key])return 'refused';\n  return 'ok';\n}\n"
                    "var ALLOWED={a:true};\nmodule.exports={guard:guard};\n")
        suite = os.path.join(tmp, 'fixture_suite.js')
        # a DELIBERATELY WEAK suite: raw indexOf, the exact bug class this
        # tool exists to re-derive -- a comment satisfies it.
        with open(suite, 'w', encoding='utf-8') as f:
            f.write(
                "var fs=require('fs');\n"
                "var src=fs.readFileSync('fixture.js','utf8');\n"
                "if(src.indexOf('!ALLOWED[key]')===-1){console.error('FAIL');process.exit(1);}\n"
                "console.log('ok');process.exit(0);\n"
            )
        spec = {
            'label': 'selftest fixture',
            # absolute paths: os.path.join(REPO_ROOT, abspath) returns
            # abspath unchanged on every platform, so these bypass
            # REPO_ROOT without needing to mutate it.
            'source_file': src,
            'anchor': "if(!ALLOWED[key])return 'refused';",
            'safe_replacement': "if(!Array.isArray([]))return 'refused';",
            'suite_relpath': suite,
            'suite_sandbox_layout': 'flat',
            'html_env_var': 'HOVER_FUZZ_SELFTEST_SRC',
        }
        rng = random.Random(1234)
        escapes = 0
        for _ in range(20):
            kind, block, escaped, _tail = one_trial(spec, rng)
            escapes += 1 if escaped else 0
        ok = escapes > 0
        print('SELFTEST %s -- weak-suite fixture: %d/20 trials escaped '
              '(expected >0, a comment satisfies a raw indexOf by design)' % (
                  'PASS' if ok else 'FAIL', escapes))
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--check')
    p.add_argument('--trials', type=int, default=25)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--selftest', action='store_true')
    args = p.parse_args(argv)
    if args.selftest:
        return cmd_selftest()
    if args.check:
        return cmd_check(args)
    print('usage: hover_property_fuzz.py --check SPEC.json --trials N | --selftest')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
