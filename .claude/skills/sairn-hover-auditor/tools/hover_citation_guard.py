#!/usr/bin/env python
r"""hover_citation_guard.py -- before any chain-log entry is written, every
tool/script/file path it names as something that was ACTUALLY RUN must
resolve in git, on a branch that is pushed. Refuses the append otherwise.

H1 batch S item 5. Built the same batch that found seq1125 was itself
wrong: hover_cross_resource_gate_check.py was cited as this role's own
committed tool across 11 entries (seq975-seq1111) while never being
committed anywhere git could see -- and item 4's existence audit found
18 MORE of this role's own tools in exactly the same situation. This
guard is the PREVENTION half; item 4 was DETECTION, after the fact.

THE HARD PART, NAMED FIRST: a naive "does this entry mention a .py or .js
path" scan is actively dangerous here, not just imprecise. This role's own
log is full of entries that DELIBERATELY invent fictional tool names as
sabotage-test fixtures -- seq172 constructs "tools/my_invented_checker.py"
specifically to prove a parser distinguishes real code from "a sentence
merely NAMING a checker in prose," and seq706 builds a synthetic
tool_provenance_validations.jsonl naming fake tools unchanged_tool.py/
changed_tool.py/crlf_tool.py/gitignored_tool.py on purpose. A write-time
guard that flagged every path-shaped token in free prose would refuse
those entries outright -- correct test-fixture narration is not a false
citation, and a guard that cannot tell the two apart would train this role
to route around it, which is worse than no guard.

TWO TIERS, DELIBERATELY DIFFERENT PRECISION:

  TIER 1 -- --ref FIELD, STRICT. --ref already exists specifically to
  stamp the real artifact(s) an entry is about (a commit sha, a file, a
  claim id) -- it is structured, not narrative prose, so EVERY path-shaped
  token in it is checked, no exceptions. This is the field this role
  SHOULD have used for the lost tool's citations and the one place a
  false positive is very unlikely, because nobody writes a sabotage
  fixture name into --ref.

  TIER 2 -- --summary FIELD, NARROW, INVOCATION-SHAPED ONLY. Free prose is
  not blanket-scanned. Only a path-shaped token appearing within
  INVOCATION_WINDOW characters of an execution-result marker (`--selftest`,
  `EXIT \d`, `exit \d`, `-> EXIT`) is treated as a real citation -- the
  shape seq975 itself used ("hover_cross_resource_gate_check.py --selftest
  ... exit 0", "api/sd-data.js (291 branches, ... EXIT 1 ...)"). A name
  mentioned without a nearby result marker (seq172's "tools/
  my_invented_checker.py, my_other_checker.js" enumeration, with no EXIT
  code anywhere near it) is NOT flagged -- named narrowing, not silent.

WHAT THIS CANNOT SEE: a citation phrased without any of the known
result-marker words at all (a result reported as plain prose with no
"EXIT"/"--selftest" nearby) slips past tier 2 entirely. Tier 1 (--ref) is
the reliable half; tier 2 is a best-effort net under the real prose this
role already writes, not a guarantee.
"""
import json
import os
import re
import subprocess
import sys

PATH_TOKEN_RE = re.compile(
    r'\b((?:[\w.-]+/)*[a-zA-Z_][a-zA-Z0-9_.-]*\.(?:py|js|md|json|jsonl))\b')
RESULT_MARKER_RE = re.compile(r'--selftest|EXIT\s+\d|exit\s+\d|->\s*EXIT', re.I)
INVOCATION_WINDOW = 60


def _known_clones():
    return (
        os.environ.get('HOVER_GUARD_REPO'),
        r'C:\Users\marsh\Documents\SAIRN-hover',
    )


def discover_repo():
    for cand in _known_clones():
        if cand and os.path.isdir(os.path.join(cand, '.git')):
            return cand
    return None


def extract_ref_citations(ref_text):
    """Tier 1 -- every path-shaped token in --ref, no exceptions."""
    if not ref_text:
        return set()
    out = set()
    for seg in re.split(r'[,;]', ref_text):
        out |= set(PATH_TOKEN_RE.findall(seg))
    return out


def extract_invocation_citations(summary_text):
    """Tier 2 -- a path-shaped token in --summary counts ONLY if an
    execution-result marker appears within INVOCATION_WINDOW chars of it,
    on EITHER side. This is a window search, not a same-sentence parse --
    deliberately a little generous, since missing a real citation is the
    failure this tool exists to prevent and a few extra chars of margin
    costs little precision in exchange."""
    if not summary_text:
        return set()
    out = set()
    markers = [m.span() for m in RESULT_MARKER_RE.finditer(summary_text)]
    if not markers:
        return out
    for m in PATH_TOKEN_RE.finditer(summary_text):
        ps, pe = m.span()
        for ms, me in markers:
            if (ms - INVOCATION_WINDOW) <= ps <= (me + INVOCATION_WINDOW) or \
               (ms - INVOCATION_WINDOW) <= pe <= (me + INVOCATION_WINDOW):
                out.add(m.group(1))
                break
    return out


def _git_ls_tree_basenames(repo):
    try:
        r = subprocess.run(['git', 'ls-tree', '-r', 'origin/main', '--name-only'],
                            cwd=repo, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, 'could not run git ls-tree: %s' % e
    if r.returncode != 0:
        return None, 'git ls-tree failed (rc=%d): %s' % (r.returncode, r.stderr.strip())
    full = set(l.strip() for l in r.stdout.splitlines() if l.strip())
    basenames = set(os.path.basename(p) for p in full)
    return (full, basenames), None


def check(ref_text, summary_text, repo=None):
    """Returns (ok, missing, detail). missing is a sorted list of cited
    names that do not resolve on origin/main. detail explains how each
    was cited (tier1/tier2) for the refusal message."""
    repo = repo or discover_repo()
    if not repo:
        return False, [], 'COULD_NOT_RUN: no known clone found to check against'
    sets, err = _git_ls_tree_basenames(repo)
    if err:
        return False, [], 'COULD_NOT_RUN: %s' % err
    full, basenames = sets
    cited = {}
    for name in extract_ref_citations(ref_text):
        cited[name] = 'tier1 (--ref)'
    for name in extract_invocation_citations(summary_text):
        cited.setdefault(name, 'tier2 (--summary, invocation-shaped)')
    missing = []
    for name, tier in sorted(cited.items()):
        base = os.path.basename(name)
        if name in full or base in basenames:
            continue
        missing.append((name, tier))
    return (len(missing) == 0), missing, None


def main(argv):
    if '--selftest' in argv:
        return _selftest()
    if '--recheck-log' in argv:
        return _recheck_log(argv)
    print('usage: --selftest | --recheck-log --log <path>')
    return 2


def _recheck_log(argv):
    """Periodic re-check mode: re-verify every citation in an EXISTING
    log against CURRENT origin/main (a citation that was real at write
    time can still rot if the file is later deleted/renamed upstream)."""
    if '--log' not in argv:
        print('COULD NOT RUN: --recheck-log requires --log <path>')
        return 2
    log_path = argv[argv.index('--log') + 1]
    if not os.path.isfile(log_path):
        print('COULD NOT RUN: log not found at %s' % log_path)
        return 2
    repo = discover_repo()
    checked = 0
    flagged = []
    with open(log_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            checked += 1
            ok, missing, err = check(d.get('ref', ''), d.get('summary', ''), repo)
            if err:
                print('COULD NOT RUN at seq %s: %s' % (d.get('seq'), err))
                return 2
            if not ok:
                flagged.append((d.get('seq'), missing))
    print('RECHECK: %d entries checked, %d flagged' % (checked, len(flagged)))
    for seq, missing in flagged:
        for name, tier in missing:
            print('  seq %s: %s (%s) does not resolve on origin/main' % (seq, name, tier))
    return 1 if flagged else 0


def _selftest():
    import tempfile
    failures = []

    def chk(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            failures.append(label)

    with tempfile.TemporaryDirectory() as td:
        subprocess.run(['git', 'init', '-q'], cwd=td)
        subprocess.run(['git', 'config', 'user.email', 'x@x.com'], cwd=td)
        subprocess.run(['git', 'config', 'user.name', 'x'], cwd=td)
        with open(os.path.join(td, 'real_tool.py'), 'w') as f:
            f.write('print(1)\n')
        subprocess.run(['git', 'add', '.'], cwd=td)
        subprocess.run(['git', 'commit', '-q', '-m', 'init'], cwd=td)
        # fake a remote-tracking ref locally so `origin/main` resolves --
        # ONLY refs/remotes/origin/main, never a local branch literally
        # named "origin/main" (that would shadow the real lookup and was
        # the actual cause of this fixture's own first failed run).
        subprocess.run(['git', 'update-ref', 'refs/remotes/origin/main', 'HEAD'], cwd=td)

        # Case 1: tier 1 (--ref) citing a REAL, committed tool -> passes.
        ok, missing, err = check('real_tool.py', 'no markers here', td)
        chk('a real, committed tool cited in --ref passes', ok and not missing)

        # Case 2: tier 1 citing a NEVER-COMMITTED tool -> refused. This is
        # the EXACT seq1125 shape, planted directly.
        ok, missing, err = check('never_committed_tool.py', 'plain prose', td)
        chk('a never-committed tool cited in --ref is refused',
            not ok and any(n == 'never_committed_tool.py' for n, _ in missing))

        # Case 3: tier 2, invocation-shaped prose citing the missing tool
        # with a nearby EXIT marker -> refused (the real seq975 shape).
        ok, missing, err = check(
            '', 'ran python never_committed_tool.py --selftest -> EXIT 0', td)
        chk('invocation-shaped prose citing a missing tool is refused',
            not ok and any('never_committed_tool.py' in n for n, _ in missing))

        # Case 4: tier 2 must NOT flag a sabotage-fixture name with no
        # nearby result marker -- the exact seq172/seq706 false-positive
        # risk this tool's own docstring names.
        ok, missing, err = check(
            '', 'invented five fictional names: tools/my_invented_checker.py, '
                'my_other_checker.js, a nested path, none of them real', td)
        chk('a fixture name with no nearby EXIT/--selftest marker is NOT flagged',
            ok and not missing)

        # Case 5: the REAL TRANSITION -- never_committed_tool.py gets
        # committed AFTER the first refusal, and the SAME citation that
        # was refused now passes, unchanged otherwise. This is not a
        # second fixture; it is the state produced by actually fixing the
        # problem the guard exists to force.
        with open(os.path.join(td, 'never_committed_tool.py'), 'w') as f:
            f.write('print(2)\n')
        subprocess.run(['git', 'add', '.'], cwd=td)
        subprocess.run(['git', 'commit', '-q', '-m', 'commit the tool'], cwd=td)
        subprocess.run(['git', 'update-ref', 'refs/remotes/origin/main', 'HEAD'], cwd=td)
        ok, missing, err = check('never_committed_tool.py', '', td)
        chk('the SAME citation passes once the tool is actually committed (real transition)',
            ok and not missing)

    print()
    print('SELFTEST %s (%d/%d)' % ('PASS' if not failures else 'FAIL', 5 - len(failures), 5))
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
