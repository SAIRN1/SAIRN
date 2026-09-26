#!/usr/bin/env python
"""probe_selector.py -- which sabotage probes does THIS push actually need?

    python tools/probe_selector.py <changed-file>...      # the selection
    python tools/probe_selector.py --all                  # every probe + subject
    python tools/probe_selector.py --self-check           # the acceptance test
    python tools/probe_selector.py --changed              # derive from git

Exit 0 a selection was made (possibly empty), 1 a probe's subject could not be
determined, 2 could not run. PRINTS A LIST -- it runs nothing itself.

── WHY A SELECTOR AND NOT A GATE OVER THE WHOLE CORPUS ────────────────────
Measured 2026-09-25 (docs/2026-09-25-probe-corpus-cost-and-decision.md): the
corpus is 65 harness-dependent probes, 1,837s = 30.6 min serial, median 10.9s,
and the slowest five carry 40% of that. A 30-minute pre-push wait is
disqualified on this repo's own recorded arithmetic -- `register_feed_gate.py`
chose a requirement date over a wall for exactly this reason, because a gate
routinely talked past produces overrides that cost more than the gate saved.

At an 11-second median, the probes whose SUBJECT a push actually touches cost
~10-30s, which is inside the noise of the existing gate. That is the trade this
tool exists to make possible.

── THE SUBJECT IS DERIVED, NEVER DECLARED SEPARATELY ──────────────────────
A probe already names its subject twice, in code the harness reads:

  * every `MUTATIONS` entry names the file it mutates;
  * `stage=(...)` names every extra file copied into the worktree.

So no new declaration is invented and nothing can go stale against the probe.
It is read with `ast`, not a regex: a probe is a Python module and importing one
RUNS it (the harness's own header records a probe mutating a tracked file at
import time and leaving it modified on disk).

── THE THIRD STATE IS THE POINT OF THE EXIT CODES ─────────────────────────
A probe whose subject cannot be determined -- a computed path, a name built at
runtime, a parse failure -- is REPORTED and exits 1. It is NOT silently skipped
and NOT silently included:

  * skipping it is the silent-pass shape this whole corpus exists to catch;
  * including it makes "undeterminable" cost 30 minutes and pushes the caller
    straight back to the wall this tool is avoiding.

So the caller decides, with the probe named. A run where every subject was
determined exits 0 and its list can be trusted as complete for those probes.
"""
import argparse
import ast
import io
import os
import re
import subprocess
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(REPO, 'tests')

# A probe belongs to the corpus when it imports the shared harness. BOTH
# spellings, because matching only `from sabotage_harness import` is how the
# corpus was miscounted as 27 when it is 65 -- that error is on the record and
# is not repeated here.
IMPORTS_HARNESS = re.compile(r'^\s*(?:from|import)\s+sabotage_harness\b', re.M)


def corpus_probes():
    out = []
    if not os.path.isdir(TESTS):
        return None
    for fn in sorted(os.listdir(TESTS)):
        if not fn.endswith('.py'):
            continue
        try:
            body = io.open(os.path.join(TESTS, fn), encoding='utf-8',
                           errors='replace').read()
        except OSError:
            continue
        # THE HARNESS ITSELF IS NOT A PROBE. sabotage_harness.py contains its
        # own name and matched the import test, so it was reported
        # UNDETERMINED on every run -- a permanent third-state row that is
        # not a finding, and a disclosure that is always on stops being read.
        if fn == 'sabotage_harness.py':
            continue
        if IMPORTS_HARNESS.search(body):
            out.append(fn)
    return out


def _string_consts(node):
    """Every str constant anywhere under `node`, including inside os.path.join."""
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append(n.value)
    return out


def subject_files(fn):
    """(set of repo-relative-ish paths, problem-or-None) for one probe.

    Read from the AST: the file names inside MUTATIONS and stage=, plus any
    module-level assignment whose value looks like a path under a known
    source directory. A name this cannot resolve makes the whole probe
    UNDETERMINED rather than partially known -- a partial subject would select
    a probe for the wrong reason and miss it for the right one.
    """
    path = os.path.join(TESTS, fn)
    try:
        src = io.open(path, encoding='utf-8', errors='replace').read()
        tree = ast.parse(src)
    except (OSError, SyntaxError) as exc:
        return set(), 'unparseable (%s)' % exc

    # Module-level constants: NAME = os.path.join('api', 'x.js') / 'a/b.js'
    consts = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            parts = _string_consts(node.value)
            joined = '/'.join(p for p in parts if p and not p.startswith('-'))
            if joined:
                consts[node.targets[0].id] = joined

    files, unresolved = set(), []

    def add_from(value):
        """A MUTATIONS element's file slot, or a stage tuple member."""
        if isinstance(value, ast.Name):
            if value.id in consts:
                files.add(consts[value.id])
            else:
                unresolved.append(value.id)
        elif isinstance(value, ast.Constant) and isinstance(value.value, str):
            files.add(value.value)
        elif isinstance(value, ast.Call):
            parts = _string_consts(value)
            j = '/'.join(p for p in parts if p and not p.startswith('-'))
            if j:
                files.add(j)
            else:
                unresolved.append('call')
        else:
            unresolved.append(type(value).__name__)

    for node in ast.walk(tree):
        # MUTATIONS = [ (name, FILE, old, new), ... ]
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == 'MUTATIONS'
                for t in node.targets):
            if not isinstance(node.value, (ast.List, ast.Tuple)):
                unresolved.append('MUTATIONS is not a literal list')
                continue
            for el in node.value.elts:
                if isinstance(el, (ast.Tuple, ast.List)) and len(el.elts) >= 2:
                    add_from(el.elts[1])
                else:
                    unresolved.append('mutation element shape')
        # run_probe(SUITE, MUTATIONS, ..., stage=(A, B))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == 'run_probe':
            if node.args:
                add_from(node.args[0])          # the SUITE is a subject too
            for kw in node.keywords:
                if kw.arg == 'stage':
                    if isinstance(kw.value, (ast.Tuple, ast.List)):
                        for el in kw.value.elts:
                            add_from(el)
                    else:
                        unresolved.append('stage is not a literal tuple')

    if not files and not unresolved:
        unresolved.append('no MUTATIONS and no run_probe call found')
    return files, ('; '.join(sorted(set(unresolved))) if unresolved else None)


def norm(p):
    return p.replace('\\', '/').lstrip('./').lower()


def select(changed):
    """(selected, undetermined, table). `changed` are repo-relative paths."""
    probes = corpus_probes()
    if probes is None:
        return None, None, None
    want = {norm(c) for c in changed}
    selected, undetermined, table = [], [], {}
    for fn in probes:
        files, problem = subject_files(fn)
        table[fn] = (sorted(files), problem)
        if problem:
            undetermined.append((fn, problem))
            continue
        if any(norm(f) in want for f in files):
            selected.append(fn)
    return selected, undetermined, table


def changed_from_git():
    r = subprocess.run(['git', '-C', REPO, 'diff', '--name-only',
                        'origin/main...HEAD'], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        return None
    return [l.strip() for l in (r.stdout or '').split('\n') if l.strip()]


# ── THE ACCEPTANCE TEST, WRITTEN DOWN AND EXECUTABLE ───────────────────────
# From docs/2026-09-25-probe-corpus-cost-and-decision.md §5, verbatim in
# intent. It is here rather than only in a probe because a selector whose
# acceptance criteria live in prose is one nobody can re-check.
def self_check(verbose=True):
    bad = []

    def case(label, cond, detail=''):
        if verbose:
            print('  %-4s %s' % ('ok' if cond else 'FAIL', label))
            if not cond and detail:
                print('       %s' % detail)
        if not cond:
            bad.append(label)

    sel, und, table = select(['api/sd-data.js'])
    if sel is None:
        case('the tests directory is readable', False)
        return bad
    # 1. A push touching api/sd-data.js selects the probes naming it, and only
    #    those. Asserted as a SUBSET relation in both directions rather than a
    #    count, because a count moves every time a probe is added.
    named = [fn for fn, (files, prob) in table.items()
             if not prob and any(norm(f) == 'api/sd-data.js' for f in files)]
    case('a push touching api/sd-data.js selects exactly the probes naming it',
         sorted(sel) == sorted(named),
         'selected %d, naming it %d' % (len(sel), len(named)))
    case('...and that set is not empty (api/sd-data.js is the most-probed file)',
         len(sel) > 0)
    case('...and it is not the whole corpus', len(sel) < len(table))

    # 2. A DOCS-ONLY push selects NOTHING. This is the arm that matters: "run
    #    the corpus to be safe" is how the 30-minute wall gets in the back door.
    sel2, _u2, _t2 = select(['docs/SAIRN-OPEN-WORK-INDEX.md',
                             'docs/tier-a-reviews.json'])
    case('a docs-only push selects NO probes', sel2 == [],
         'selected: %s' % ', '.join(sel2[:5]))

    # 3. An empty changed-file list selects nothing, rather than everything.
    sel3, _u3, _t3 = select([])
    case('an empty change set selects NO probes', sel3 == [])

    # 4. A file no probe names selects nothing -- the selector must not fall
    #    back to "everything" when it recognises nothing.
    sel4, _u4, _t4 = select(['zz_no_such_file_anywhere.txt'])
    case('an unknown file selects NO probes (no everything-fallback)', sel4 == [])

    # 5. Subjects really were derived: most probes must have one, or the
    #    selector is a sophisticated way of selecting nothing.
    determined = [fn for fn, (_f, prob) in table.items() if not prob]
    case('most probes have a derived subject (%d of %d)'
         % (len(determined), len(table)), len(determined) >= 0.8 * len(table),
         'undetermined: ' + ', '.join(fn for fn, _p in und[:6]))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--changed', action='store_true')
    ap.add_argument('--self-check', action='store_true')
    args = ap.parse_args(argv)

    if args.self_check:
        print('PROBE SELECTOR -- acceptance test\n')
        bad = self_check()
        print('\n%d case(s) wrong' % len(bad))
        return 0 if not bad else 1

    probes = corpus_probes()
    if probes is None:
        print('COULD NOT RUN: no tests/ directory. Nothing was selected, which '
              'is not the same as nothing to select.')
        return 2

    if args.all:
        print('CORPUS: %d harness-dependent probe(s), with the subject each '
              'declares\n' % len(probes))
        for fn in probes:
            files, prob = subject_files(fn)
            print('  %-52s %s' % (fn, prob and ('UNDETERMINED: ' + prob)
                                  or ', '.join(sorted(files))))
        return 0

    changed = args.files
    if args.changed:
        g = changed_from_git()
        if g is None:
            print('COULD NOT RUN: git diff failed, so the change set is '
                  'unknown. NOT treated as empty.')
            return 2
        changed = g
    if not changed:
        print('No changed files given. Selecting NOTHING -- an empty change '
              'set is not a reason to run the corpus.')
        return 0

    sel, und, _table = select(changed)
    print('CHANGED: %d file(s)' % len(changed))
    print('SELECTED: %d probe(s) of %d in the corpus' % (len(sel), len(probes)))
    for fn in sel:
        print('   tests/%s' % fn)
    if und:
        print('')
        print('UNDETERMINED SUBJECT: %d probe(s). NOT selected and NOT '
              'dismissed -- you decide:' % len(und))
        for fn, prob in und:
            print('   tests/%-48s %s' % (fn, prob))
        print('   A probe whose subject cannot be read is a third state. '
              'Skipping it silently is')
        print('   the shape this corpus exists to catch; including it makes '
              '"undeterminable" cost')
        print('   the whole 30 minutes and pushes you back to the wall.')
    return 1 if und else 0


if __name__ == '__main__':
    sys.exit(main())
