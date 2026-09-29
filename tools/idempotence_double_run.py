r"""A MUTATING TOOL MUST CHANGE NOTHING ON ITS SECOND RUN.

    python tools/idempotence_double_run.py
    python tools/idempotence_double_run.py --tool tools/master_plan.py
    python tools/idempotence_double_run.py --json
    python tools/idempotence_double_run.py --selftest

REPORT ONLY, and it NEVER runs a tool against the real repository. Every double
run happens inside a throwaway copy. Exit 0 clean, 1 findings, 2 COULD NOT RUN.

── WHY, AND I CAUSED IT ────────────────────────────────────────────────────
On 2026-09-29 I repointed 28 citations in `docs/CRITICALITY-TIERS.md` by shifting
every line number at or after 1711 by +25. **Run one shifted ten citations that a
previous pass had already shifted, moving them 50 lines.** Run two excluded those
rows by prefix and FOUR still got through, because the population was a union with
"names sairngrounds.html" and the cell in question names that file in its own prose.
**An exclusion a later OR can override is not an exclusion.**

The general shape: **a repoint, a backfill, a reseat and a regenerate are all
`f(state) -> state'`, and only a regenerate is naturally idempotent.** The other
three read the state, compute a delta, and apply it -- so running one twice applies
the delta twice unless something makes the second application a no-op. Nothing
required that, and nothing checked it.

── WHAT IT DOES ────────────────────────────────────────────────────────────
For every candidate tool: copy the repo's tracked files into a scratch directory,
run the tool there TWICE, and compare the tree after run 1 against the tree after
run 2. **Equal is a pass. Different is a finding, and the changed files are named.**

── THE SCRATCH COPY IS THE WHOLE SAFETY PROPERTY ───────────────────────────
A tool being tested for idempotence is by definition one that writes. Running these
against the real tree would be running twenty mutating tools over the working copy
to find out whether that is safe. The copy is made from `git ls-files` plus a real
`git init` and one commit, because several of these tools ask git questions and a
directory of files is not a repository.

── WHAT IT CANNOT SEE, so the gap is a decision ────────────────────────────
* A tool needing arguments to mutate. `--reseat-shas` does nothing without
  `--write`, so the DEFAULT invocation is idempotent trivially and the mutating
  one is not exercised. Those are listed with their flag and reported as NOT
  EXERCISED -- which is a third state, not a pass.
* A tool whose output depends on the clock or on the network. A timestamp changing
  between two runs is not the defect this looks for, so tools known to stamp a time
  are named and excluded rather than reported as broken.
* A tool that mutates something outside the repo.
"""
import argparse
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN  # noqa: E402

CRITERIA_VERSION = '2026-09-29.1'

# ── THE CANDIDATES, DERIVED. A tool that writes a tracked file is a candidate;
# the shape is an `io.open(..., 'w')` or an `open(..., 'w')` on a path under the
# repo. Derived rather than listed so a new mutating tool is covered without
# editing this file -- which is the very defect the pattern-enumeration sweep is
# about, applied to itself.
WRITES = re.compile(r"""(?:io\.)?open\s*\([^)]*['"]w['"]""")

# ── EXCLUDED, EACH WITH ITS REASON. Named, never silently skipped.
EXCLUDE = {
    'idempotence_double_run.py':
        'this file. It writes only inside its own scratch directory.',
    'fact_sheet_regenerates.py':
        'STAMPS A TIME on a clean --update, so two runs differ by design and the '
        'difference is not the defect this looks for. Its own control covers the '
        'stamp.',
    'hook_integrity_check.py':
        'its --regenerate hashes THIS FILE among others, so a scratch copy whose '
        'tool set differs from the real one produces a different manifest for a '
        'reason that is not a defect.',
    'sairn_claim.py':
        'claims, commits and PUSHES. Running it twice in a scratch repo would '
        'exercise a push path against no remote and prove nothing.',
    'defect_register.py':
        'its --add takes a dozen required arguments and mutates nothing without '
        'them; the mutating path needs a full record and is covered by its own '
        'probe.',
    'tier_a_review_gate.py':
        'mutates only under --write (--backfill-shas, --reseat-shas), both of '
        'which are argument-gated. Listed as NOT EXERCISED below.',
    'install_git_hooks.py':
        'sets local git config rather than writing a tracked file, and its own '
        'header already claims idempotence with a --check that proves it.',
}

# ── ARGUMENT-GATED MUTATORS. The default invocation cannot mutate, so a clean
# double run says nothing about the dangerous path. REPORTED AS NOT EXERCISED.
ARG_GATED = {
    'tier_a_review_gate.py': '--backfill-shas --write / --reseat-shas --write',
    'defect_register.py': '--add / --reseat',
    'hook_integrity_check.py': '--regenerate',
}

# ── 30s, AND THE CEILING IS A FINDING RATHER THAN A CONVENIENCE ─────────────
# 72 candidates x 2 runs at 180s is over seven hours in the worst case, and a sweep
# nobody can run is not a sweep -- the same lesson --reseat-shas learned when its
# first draft spawned 7,000 subprocesses. 30s is generous for a tool that writes a
# document: the slowest generator in this repo finishes in about seven.
#
# AND A TOOL THAT EXCEEDS IT IS REPORTED AS COULD-NOT-TELL, never as clean. A
# mutating tool that needs half a minute twice is either doing something this sweep
# should not be doing to it, or is itself worth a look. Either way the answer is
# "not examined", which is the third state.
TIMEOUT = 30

# ── PUSHES, NETWORK AND INTERACTIVE TOOLS, EXCLUDED BY WHAT THEY DO ─────────
# Derived from the source rather than listed by name: a tool that pushes, fetches
# over the network, or blocks on input cannot be double-run in a scratch repo, and
# running one would time out 72 times over rather than telling anybody anything.
SIDE_EFFECT = re.compile(
    r"['\"]push['\"]|urllib|requests\.|input\s*\(|getpass|webbrowser|"
    r"sairn_http|smtplib")


def rmtree(path):
    def onerror(fn, p, exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            fn(p)
        except Exception:
            pass
    shutil.rmtree(path, onerror=onerror)


def git(cwd, *args):
    return subprocess.run(['git', '-c', 'user.name=idem',
                           '-c', 'user.email=idem@local',
                           '-c', 'commit.gpgsign=false'] + list(args),
                          cwd=cwd, capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def tracked():
    p = subprocess.run(['git', '-C', REPO, 'ls-files'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    if p.returncode != 0:
        return None
    return [x.strip() for x in (p.stdout or '').splitlines() if x.strip()]


def make_scratch(files):
    """A real repository holding the tracked tree. (path, None) or (None, why)."""
    d = tempfile.mkdtemp(prefix='sairn_idem_')
    for rel in files:
        src = os.path.join(REPO, rel)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(d, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.copyfile(src, dst)
        except OSError:
            pass
    r = git(d, 'init', '-q', '-b', 'main')
    if r.returncode != 0:
        rmtree(d)
        return None, 'git init failed in the scratch copy: %s' % (r.stderr or '')[:120]
    git(d, 'add', '-A')            # inside a THROWAWAY repo, never the real one
    git(d, 'commit', '-q', '-m', 'scratch baseline')
    return d, None


def snapshot(d):
    """{relpath: sha1} for every file, from git itself rather than by walking."""
    git(d, 'add', '-A')
    p = git(d, 'ls-files', '-s')
    out = {}
    for line in (p.stdout or '').splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4:
            out[parts[3].strip()] = parts[1]
    return out


def double_run(d, tool_rel, argv=()):
    """(changed_files, why) -- files whose content differs between run 1 and 2."""
    def run():
        return subprocess.run([sys.executable, os.path.join(d, tool_rel)]
                              + list(argv), cwd=d, capture_output=True,
                              text=True, encoding='utf-8', errors='replace',
                              timeout=TIMEOUT,
                              env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    try:
        run()
        first = snapshot(d)
        run()
        second = snapshot(d)
    except subprocess.TimeoutExpired:
        return None, 'timed out after %ds' % TIMEOUT
    except Exception as exc:
        return None, 'raised %s' % type(exc).__name__
    changed = sorted(k for k in set(first) | set(second)
                     if first.get(k) != second.get(k))
    return changed, None


SKIPPED_SIDE_EFFECT = []


def candidates():
    out = []
    for f in sorted(os.listdir(TOOLS)):
        if not f.endswith('.py') or f in EXCLUDE:
            continue
        try:
            body = io.open(os.path.join(TOOLS, f), encoding='utf-8',
                           errors='replace').read()
        except OSError:
            continue
        if not WRITES.search(body):
            continue
        if SIDE_EFFECT.search(body):
            SKIPPED_SIDE_EFFECT.append(f)
            continue
        out.append(f)
    return out


def selftest():
    """A KNOWN-BAD AND A KNOWN-GOOD FIXTURE BEFORE THE CORPUS.

    The standing rule after two of my criteria came out wrong this week. A sweep
    whose only evidence is a clean corpus run cannot distinguish "nothing is
    broken" from "the comparison never fires".
    """
    bad = 0

    def arm(name, cond, detail=''):
        nonlocal bad
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))
        if not cond:
            bad += 1
            if detail:
                print('       %s' % str(detail)[:300])

    d = tempfile.mkdtemp(prefix='sairn_idem_self_')
    try:
        os.makedirs(os.path.join(d, 'tools'))
        io.open(os.path.join(d, 'data.txt'), 'w', encoding='utf-8',
                newline='\n').write('100\n')
        # KNOWN-BAD: adds 25 every run. This is the citation repoint, in miniature.
        io.open(os.path.join(d, 'tools', 'bad.py'), 'w', encoding='utf-8',
                newline='\n').write(
            'import io\n'
            'p = "data.txt"\n'
            'n = int(io.open(p).read().strip())\n'
            'io.open(p, "w", newline="\\n").write(str(n + 25) + "\\n")\n')
        # KNOWN-GOOD: writes a computed constant. A regenerate.
        io.open(os.path.join(d, 'tools', 'good.py'), 'w', encoding='utf-8',
                newline='\n').write(
            'import io\n'
            'io.open("data.txt", "w", newline="\\n").write("100\\n")\n')
        git(d, 'init', '-q', '-b', 'main')
        git(d, 'add', '-A')
        git(d, 'commit', '-q', '-m', 'fixture')

        changed, why = double_run(d, os.path.join('tools', 'bad.py'))
        arm('KNOWN-BAD: a tool that adds 25 every run is CAUGHT -- the citation '
            'repoint in miniature', changed == ['data.txt'], (changed, why))

        git(d, 'checkout', '-q', '--', 'data.txt')
        changed, why = double_run(d, os.path.join('tools', 'good.py'))
        arm('KNOWN-GOOD: a tool that writes a computed constant is CLEAN -- so the '
            'comparison is not simply reporting everything', changed == [],
            (changed, why))

        changed, why = double_run(d, os.path.join('tools', 'no_such.py'))
        arm('a tool that cannot run is a COULD-NOT-TELL, not a clean pass',
            changed == [] or why is not None, (changed, why))
    finally:
        rmtree(d)
    print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
    return EXIT_CLEAN if not bad else EXIT_FINDING


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tool', default=None)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)

    if args.selftest:
        print('IDEMPOTENCE DOUBLE RUN -- selftest, fixtures before the corpus')
        return selftest()

    print('IDEMPOTENCE DOUBLE RUN -- a mutating tool must change nothing twice')
    print('  criteria : %s' % CRITERIA_VERSION)

    # THE FIXTURES RUN FIRST, ALWAYS. A corpus result from a comparison that
    # cannot fire is the vacuous pass this repo names most often.
    print()
    print('  FIXTURE GATE -- run before the corpus so a vacuous pass is impossible:')
    if selftest() != EXIT_CLEAN:
        print()
        print('COULD NOT RUN: the fixture arms did not pass, so nothing below '
              'would mean anything.')
        return EXIT_COULD_NOT_RUN

    files = tracked()
    if files is None:
        print('COULD NOT RUN: git ls-files did not answer, so no scratch copy '
              'could be made.')
        return EXIT_COULD_NOT_RUN

    todo = [args.tool.replace('\\', '/').split('/')[-1]] if args.tool \
        else candidates()
    if not todo:
        print('COULD NOT RUN: no candidate tool was found. A sweep over nothing '
              'reports clean.')
        return EXIT_COULD_NOT_RUN

    print()
    print('  candidates (a tool that writes a file, DERIVED): %d' % len(todo))
    print('  skipped for a NETWORK, PUSH or INTERACTIVE side effect, DERIVED from')
    print('  the source rather than listed: %d' % len(SKIPPED_SIDE_EFFECT))
    for n in SKIPPED_SIDE_EFFECT[:12]:
        print('    %s' % n)
    if len(SKIPPED_SIDE_EFFECT) > 12:
        print('    ... and %d more' % (len(SKIPPED_SIDE_EFFECT) - 12))
    print('  excluded with a reason: %d' % len(EXCLUDE))
    for name, why in sorted(EXCLUDE.items()):
        print('    %-34s %s' % (name, why[:96]))
    print()
    print('  ARGUMENT-GATED MUTATORS -- the default run cannot mutate, so a clean')
    print('  double run says NOTHING about the dangerous path. NOT EXERCISED:')
    for name, flag in sorted(ARG_GATED.items()):
        print('    %-34s %s' % (name, flag))

    d, why = make_scratch(files)
    if d is None:
        print()
        print('COULD NOT RUN: %s' % why)
        return EXIT_COULD_NOT_RUN

    findings, could_not, clean = [], [], []
    try:
        for name in todo:
            rel = os.path.join('tools', name)
            if not os.path.isfile(os.path.join(d, rel)):
                could_not.append((name, 'not in the scratch copy'))
                continue
            git(d, 'checkout', '-q', '--', '.')
            changed, err = double_run(d, rel)
            if err:
                could_not.append((name, err))
            elif changed:
                findings.append((name, changed))
            else:
                clean.append(name)
    finally:
        rmtree(d)

    print()
    print('  double-run CLEAN        : %d' % len(clean))
    print('  double-run DIFFERENT    : %d' % len(findings))
    print('  COULD NOT TELL          : %d -- NOT a pass' % len(could_not))
    print()
    for name, changed in findings:
        print('  ! %-34s changed %d file(s) on the second run' % (name, len(changed)))
        for c in changed[:6]:
            print('        %s' % c)
    for name, err in could_not:
        print('  ? %-34s %s' % (name, err[:100]))
    if not findings:
        print('  No candidate tool changed the tree on its second run.')

    print()
    print('  WHAT A CLEAN RESULT DOES NOT SAY: that the argument-gated mutators')
    print('  above are idempotent. Their dangerous path was NOT exercised, which')
    print('  is a third state and is listed rather than counted as a pass.')

    if args.json:
        print(json.dumps({'criteria': CRITERIA_VERSION,
                          'clean': clean,
                          'different': [{'tool': n, 'files': c}
                                        for n, c in findings],
                          'could_not_tell': [{'tool': n, 'why': w}
                                             for n, w in could_not],
                          'not_exercised': ARG_GATED,
                          'excluded': EXCLUDE}, indent=2))

    if could_not and not findings:
        return EXIT_COULD_NOT_RUN
    return EXIT_FINDING if findings else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
