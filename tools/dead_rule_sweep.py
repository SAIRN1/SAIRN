#!/usr/bin/env python
"""Which criteria rules can be DELETED with nothing going red?

    python tools/dead_rule_sweep.py
    python tools/dead_rule_sweep.py --fixtures   # the criteria lock, alone
    python tools/dead_rule_sweep.py --tool X.py  # one tool, with detail
    python tools/dead_rule_sweep.py --quiet

Exit 0 clean, 1 findings, 2 COULD NOT RUN. REPORT ONLY.

── THE DEFECT ───────────────────────────────────────────────────────────────
On 2026-09-29 a new rule in tools/assertion_label_shape_check.py shipped with a
literal backspace where every `\\b` should have been:

    'fixture invalid\\x08|could not\\x08|cannot\\x08|...'

It matched nothing, ever. The tool ran, its fixture lock passed, its control
passed, the count it was meant to move went to zero by a different branch, and
the demotion the rule existed for silently did not happen. IT READ AS A WORKING
RULE FROM EVERY ANGLE. It was caught only because an attribution ablation
counted the demotions and got 0 where it expected 2.

**A rule nothing exercises is indistinguishable from a rule that works**, and no
amount of green says otherwise. That is the eighth cross-domain discipline -- a
check that has stopped testing anything reads identically to one that passed --
and the twelfth: ABLATION over assertion. Remove ONE named layer and measure
what it alone catches.

── WHAT THIS DOES ───────────────────────────────────────────────────────────
For every module-level compiled pattern in every tool in the report-only
registry, it NEUTRALISES that one pattern -- replaced with `(?!x)x`, which is
syntactically valid and can never match -- and re-runs the tool's own evidence:

    1. its fixture lock  (`--fixtures` / `--selftest`), if it has one; else
    2. its declared control, from CONTROLLED_BY.

If neither turns red, that rule is DEAD TO ITS OWN EVIDENCE: nothing the tool
ships as proof of itself depends on the rule existing.

── WHAT "DEAD" DOES AND DOES NOT MEAN, because the distinction is the finding ─
It does NOT mean the rule is wrong, or unused on real data. It means NOTHING
THE TOOL CARRIES AS EVIDENCE would notice if it vanished. A rule in that state
can be deleted, mistyped, or shipped with a literal backspace and every green
light stays green -- which is exactly what happened.

The repair is one of two, and they are not the same:
  * add a fixture that exercises the rule -- when the rule is load-bearing; or
  * register it as a NAMED LIMIT -- when it is defensive, covers a shape that no
    longer occurs, or is a belt-and-braces second spelling. A named limit is
    honest; an unexercised rule presented as a criterion is not.

── WHAT IT CANNOT SEE, stated rather than discovered later ──────────────────
  * A rule built at runtime, or compiled inside a function. Only a module-level
    `NAME = re.compile(...)` is reachable.
  * A rule whose tool has NEITHER a fixture lock NOR a declared control. Those
    are COULD NOT TELL and are counted separately -- not folded into clean,
    because "no evidence to ablate" and "the rule is exercised" are opposite
    findings that would otherwise print the same.
  * WHETHER THE FIXTURE THAT SAVES A RULE IS ANY GOOD. One fixture that happens
    to touch the pattern clears it here. That is sabotage_control_check's
    question.
  * A rule that only matters on REAL data. The evidence a tool ships is the
    thing under test, deliberately: a rule defended only by the corpus is
    defended by something that changes without anybody deciding.
"""
import argparse
import ast
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN, finish                 # noqa: E402

CONTROLLED_BY = ['tests/run_dead_rule_sweep_probe.py']
CRITERIA_VERSION = '2026-09-29.1'

# A pattern that is syntactically valid and can never match anything. Used
# instead of deleting the line, so the module still imports and the failure is
# ABOUT THE RULE rather than about a NameError somewhere else.
NEVER = "(?!x)x"

# Flags that run a tool's own fixture lock without touching real data.
LOCK_FLAGS = ('--fixtures', '--selftest', '--self-check')
# A bare real run is the third tier's evidence and some tools are slow.
# A timeout is COULD NOT TELL, never dead.
# Lowered from 180 after the first full run: the third tier costs TWO bare
# runs per rule and the sweep has to finish to be worth anything. A timeout
# is COULD NOT TELL, never dead.
CORPUS_TIMEOUT = 45

DEAD = 'DEAD TO ITS OWN EVIDENCE -- neutralise it and nothing goes red'
LIVE = 'exercised'
# ── A THIRD TIER, ADDED 2026-09-29 ──────────────────────────────────────────
# The first run left 91 of 156 rules as COULD NOT TELL because their tool ships
# neither a fixture lock nor a declared control. But a tool with no evidence
# still PRODUCES SOMETHING: if neutralising a rule changes what it prints on the
# real corpus, something notices.
#
# THIS IS WEAKER EVIDENCE AND THE VERDICT SAYS SO. A lock is hand-built and
# changes only when somebody decides; the corpus changes when anybody pushes. A
# rule defended only by the corpus is defended by something nobody agreed to,
# and the day the last matching line is deleted the rule goes dead with no
# signal. It is real evidence and it is not the same evidence, so it is a
# separate verdict rather than folded into `exercised`.
LIVE_CORPUS = 'exercised BY THE REAL RUN ONLY -- no lock, no control'
DEAD_EVEN_ON_OUTPUT = ('DEAD EVEN ON THE REAL RUN -- no lock, no control, and '
                       'neutralising it does not change a byte of the output')
NO_EVIDENCE = ('COULD NOT TELL -- no lock, no control, and the real run could '
               'not be compared either')
WRITES = ('COULD NOT TELL -- no lock, no control, and the tool WRITES '
          'when run, so the real run is not safe to use as evidence')
# A tool whose bare run rewrites a file cannot be the third tier's
# evidence: the first full run of that tier left docs/MASTER-PLAN.md,
# docs/TOOLING-INVENTORY.md and docs/traceability-matrix.md modified in
# the working tree, because the generators regenerate when run with no
# arguments. Detected by SHAPE rather than by a name list -- a write to a
# path built from REPO -- so a new generator is covered on the day it
# lands rather than on the day somebody remembers to add it.
WRITE_SHAPES = (
    "'w'", '"w"', "'wb'", '"wb"', "'a'", "'w+'",
)


def writes_when_run(src):
    """Does a bare run of this tool open something for writing?"""
    for ln in src.split('\n'):
        t = ln.strip()
        if t.startswith('#'):
            continue
        if ('open(' not in t and '.write(' not in t
                and 'makedirs' not in t and 'replace(' not in t):
            continue
        if any(w in t for w in WRITE_SHAPES):
            return True
    return False


def module_patterns(src):
    """[(name, lineno)] for every module-level NAME = re.compile(...)."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    out = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        t = node.targets[0]
        if not isinstance(t, ast.Name):
            continue
        v = node.value
        if not (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
                and v.func.attr == 'compile'):
            continue
        out.append((t.id, node.lineno))
    return out


def neutralise(src, name):
    """Replace one module-level compiled pattern with a never-matching one.

    Rewritten through `ast` rather than by text surgery: a pattern can span
    lines, carry adjacent string literals and end with flags, and a regex that
    edits regexes by regex is how this class of defect is born.
    """
    tree = ast.parse(src)
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == name
                and isinstance(node.value, ast.Call)):
            lines = src.split('\n')
            start = node.lineno - 1
            end = getattr(node, 'end_lineno', node.lineno) - 1
            flags = ''
            for kw in node.value.keywords:
                flags = ''
            if len(node.value.args) > 1:
                flags = ', ' + ast.unparse(node.value.args[1])
            repl = '%s = re.compile(%r%s)' % (name, NEVER, flags)
            return '\n'.join(lines[:start] + [repl] + lines[end + 1:])
    return None


def evidence_cmds(tool, src):
    """[(label, argv)] -- the tool's own proof, cheapest first."""
    cmds = []
    for f in LOCK_FLAGS:
        if "'%s'" % f in src or '"%s"' % f in src:
            cmds.append(('lock %s' % f,
                         [sys.executable, os.path.join(REPO, 'tools', tool), f]))
            break
    for m in re.findall(r"CONTROLLED_BY\s*=\s*\[([^\]]*)\]", src):
        for name in re.findall(r"'([^']+)'", m):
            p = os.path.join(REPO, name.replace('/', os.sep))
            if os.path.isfile(p):
                cmds.append(('control %s' % os.path.basename(name),
                             [sys.executable, p]))
    return cmds


def run(argv, timeout=240, want_output=False):
    """Exit code, or (exit code, stdout) when the output itself is the signal.

    None means the run could not be compared at all -- a timeout or a crash of
    the harness rather than of the tool. Kept distinct from a non-zero exit,
    because "it failed" and "I could not find out" are different answers and
    this file's whole subject is not confusing the two.
    """
    try:
        r = subprocess.run(argv, cwd=REPO, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                    PYTHONUTF8='1'))
        return (r.returncode, r.stdout or '') if want_output else r.returncode
    except subprocess.TimeoutExpired:
        return (None, None) if want_output else None
    except Exception:                                          # noqa: BLE001
        return (None, None) if want_output else None


# ── THE FIXTURE LOCK (discipline 1), and this tool must pass its own test ────
# Hand-built sources, classified with no real file read. The FIRST one is the
# whole point: a pattern replaced with NEVER must still PARSE and still IMPORT,
# because a neutralisation that breaks the module would turn every rule red for
# the wrong reason and report a clean sweep of exercised rules.
FIXTURES = (
    ("PAT = re.compile(r'abc')\n", 'PAT', True,
     'the simple form: one pattern, one line'),
    ("PAT = re.compile(\n    r'abc'\n    r'|def', re.I)\n", 'PAT', True,
     'A MULTI-LINE PATTERN WITH ADJACENT LITERALS AND A FLAG. Text surgery gets '
     'this wrong, which is why the rewrite goes through ast -- a regex that '
     'edits regexes by regex is how this defect class is born'),
    ("import re\nPAT = re.compile(r'a', re.I | re.M)\nX = 1\n", 'PAT', True,
     'the flags expression is carried over, not dropped: dropping re.I would '
     'change behaviour beyond the neutralisation and the ablation would be '
     'measuring two things'),
    ("PAT = re.compile(r'abc')\n", 'NOSUCH', False,
     'a name that is not there yields no rewrite rather than a silent no-op '
     'that would be counted as an ablation that changed nothing'),
    ("def f():\n    P = re.compile(r'x')\n", 'P', False,
     'A PATTERN COMPILED INSIDE A FUNCTION IS OUT OF REACH, and saying so is '
     'the difference between a limit and a gap'),
)


def run_fixtures(verbose=False):
    bad = []
    # ── THE FIRST THING THE LOCK CHECKS IS THAT `NEVER` NEVER MATCHES ───────
    # Its own control caught this missing. Every fixture below asks "does the
    # rewrite contain NEVER", and `'' in anything` is True -- so an EMPTY NEVER
    # passed all five while neutralising nothing, and every rule in the repo
    # would have been reported as exercised. A sentinel that is not checked is
    # not a sentinel.
    try:
        _n = re.compile(NEVER)
        _ok = all(_n.search(s) is None
                  for s in ('', 'x', 'abc', 'fixture invalid', '\n'))
    except re.error as _e:
        _ok, _n = False, None
    if not _ok:
        bad.append('NEVER=%r MATCHES SOMETHING (or will not compile) -- the '
                   'neutralisation would be a no-op reported as an exercise, '
                   'and every rule would read as exercised' % NEVER)
    elif verbose:
        print('  ok   %-28s %s' % ('NEVER matches nothing',
                                   'the sentinel the whole ablation rests on'))
    for src, name, should, why in FIXTURES:
        out = neutralise(src, name)
        ok = (out is not None) if should else (out is None)
        if ok and out is not None:
            try:
                ast.parse(out)
                ok = NEVER in out
            except SyntaxError:
                ok = False
        if not ok:
            bad.append('%s -- %s' % (name, why))
        elif verbose:
            print('  ok   %-28s %s' % (name, why))
    return bad


def registry_tools():
    try:
        import report_only_checks
        return [e['tool'] for e in report_only_checks.REGISTRY if e.get('tool')]
    except Exception:                                          # noqa: BLE001
        return None


def sweep_tool(tool, verbose=False):
    """[(rule, verdict)] for one tool."""
    path = os.path.join(REPO, 'tools', tool)
    if not os.path.isfile(path):
        return None
    orig = io.open(path, encoding='utf-8', newline='').read()
    pats = module_patterns(orig)
    if pats is None:
        return None
    if not pats:
        return []
    cmds = evidence_cmds(tool, orig)
    bare = None
    if not cmds and writes_when_run(orig):
        return [(n, WRITES) for n, _ln in pats]
    if not cmds:
        # THE THIRD TIER. Run the tool bare and compare its OUTPUT, not only its
        # exit code: a rule can change what a report says without changing
        # whether it exits 1.
        bare = [sys.executable, os.path.join(REPO, 'tools', tool)]

    base = {}
    for label, argv in cmds:
        base[label] = run(argv)
    base_bare = run(bare, timeout=CORPUS_TIMEOUT, want_output=True) if bare else None
    if bare and base_bare[1] is None:
        # The baseline itself could not be taken, so nothing below is a
        # comparison. NOT folded into dead.
        return [(n, NO_EVIDENCE) for n, _ln in pats]

    rows = []
    try:
        for name, _ln in pats:
            patched = neutralise(orig, name)
            if patched is None:
                rows.append((name, NO_EVIDENCE))
                continue
            io.open(path, 'w', encoding='utf-8', newline='').write(patched)
            # THE NEUTRALISATION MUST HAVE APPLIED. A patch that silently did
            # nothing would report every rule as dead.
            if NEVER not in io.open(path, encoding='utf-8').read():
                rows.append((name, NO_EVIDENCE))
                continue
            if bare:
                got = run(bare, timeout=CORPUS_TIMEOUT, want_output=True)
                if got[1] is None:
                    rows.append((name, NO_EVIDENCE))
                elif got != base_bare:
                    rows.append((name, LIVE_CORPUS))
                else:
                    rows.append((name, DEAD_EVEN_ON_OUTPUT))
                continue
            moved = False
            for label, argv in cmds:
                rc = run(argv)
                if rc != base.get(label):
                    moved = True
                    if verbose:
                        print('     %-26s %s: %s -> %s'
                              % (name, label, base.get(label), rc))
                    break
            rows.append((name, LIVE if moved else DEAD))
    finally:
        io.open(path, 'w', encoding='utf-8', newline='').write(orig)
        after = io.open(path, encoding='utf-8', newline='').read()
        if after != orig:
            raise RuntimeError('RESTORE FAILED for %s -- the file on disk is '
                               'not what it was' % tool)
    return rows


def main(argv):
    ap = argparse.ArgumentParser(add_help=True,
                                 description=__doc__.split('\n')[0])
    ap.add_argument('--fixtures', action='store_true')
    ap.add_argument('--tool', default=None)
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args(argv)

    if not a.quiet:
        print('DEAD RULE SWEEP -- criteria %s' % CRITERIA_VERSION)
    bad = run_fixtures(verbose=(a.fixtures and not a.quiet))
    if bad:
        if not a.quiet:
            print('\nCRITERIA LOCK FAILED -- %d of %d fixtures wrong:'
                  % (len(bad), len(FIXTURES)))
            for b in bad:
                print('  ! %s' % b)
            print('\nNOTHING REAL WAS ABLATED. A sweep whose own rewrite is '
                  'broken reports every\nrule as dead, which is the loudest '
                  'possible wrong answer.')
        return EXIT_COULD_NOT_RUN
    if not a.quiet:
        print('criteria lock: %d/%d fixtures classify correctly, on hand-built '
              'sources only' % (len(FIXTURES) + 1, len(FIXTURES) + 1))
    if a.fixtures:
        return 0

    tools = [a.tool] if a.tool else registry_tools()
    if not tools:
        if not a.quiet:
            print('\nCOULD NOT READ the report-only registry. The population is '
                  'that registry\nand nothing else, so there is nothing to '
                  'report rather than nothing wrong.')
        return EXIT_COULD_NOT_RUN

    dead, live, unknown, unreadable = [], 0, [], []
    live_corpus, dead_output, writes = 0, [], []
    for t in tools:
        try:
            rows = sweep_tool(t, verbose=bool(a.tool) and not a.quiet)
        except RuntimeError as e:
            print('RESTORE FAILURE: %s' % e, file=sys.stderr)
            return EXIT_COULD_NOT_RUN
        if rows is None:
            unreadable.append(t)
            continue
        for name, verdict in rows:
            if verdict == DEAD:
                dead.append((t, name))
            elif verdict == LIVE:
                live += 1
            elif verdict == LIVE_CORPUS:
                live_corpus += 1
            elif verdict == DEAD_EVEN_ON_OUTPUT:
                dead_output.append((t, name))
            elif verdict == WRITES:
                writes.append((t, name))
            else:
                unknown.append((t, name))

    total = (len(dead) + live + len(unknown) + live_corpus
             + len(dead_output) + len(writes))
    if not a.quiet:
        print('read %d tool(s) from the report-only registry; %d module-level '
              'compiled rule(s)' % (len(tools), total))
        print('\nCHECKED / UNIVERSE: %d of %d rules could be ABLATED against '
              'SOME evidence.\n  %d of those against evidence the tool SHIPS -- '
              'a lock or a control -- of which\n  %d exercised and %d dead. '
              'THE OTHER %d WERE ABLATED AGAINST THE REAL RUN ONLY,\n  which is '
              'weaker: a lock changes when somebody decides, a corpus changes '
              'when\n  anybody pushes. %d of those move the output and %d do '
              'not move a byte of it.\n  AND %d ARE STILL NOT CLEARED -- no '
              'lock, no control, and the real run could\n  not be compared '
              'either. "No evidence to ablate" and "the rule is exercised"\n  '
              'are opposite findings and must not print the same.'
              % (live + len(dead) + live_corpus + len(dead_output), total,
                 live + len(dead), live, len(dead),
                 live_corpus + len(dead_output), live_corpus, len(dead_output),
                 len(unknown) + len(writes)))
        if writes:
            print('  OF THOSE, %d belong to a tool that WRITES when run, so the '
                  'real run is not\n  safe to use as evidence -- the first '
                  'attempt at this tier left three generated\n  documents '
                  'modified in the working tree.' % len(writes))
        if unreadable:
            print('  UNREADABLE: %s' % ', '.join(unreadable))

    return finish(
        ['%s  %s  %s' % (t, n, DEAD) for t, n in dead]
        + ['%s  %s  %s' % (t, n, DEAD_EVEN_ON_OUTPUT) for t, n in dead_output],
        could_not_run=['%s %s -- no fixture lock and no control to ablate '
                       'against' % (t, n) for t, n in unknown]
        + ['%s %s -- the tool WRITES when run; the real run is not safe '
           'evidence' % (t, n) for t, n in writes],
        quiet=a.quiet,
        clean_line='\nCLEAN -- every module-level rule whose tool ships '
                   'evidence is exercised by it.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
