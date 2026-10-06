#!/usr/bin/env python
# OWNER: fourth
r"""Drive every REGISTERED red suite and fail if the register is lying.

    python tools/red_suite_register_check.py
    python tools/red_suite_register_check.py --from-run <run-all-tests log>
    python tools/red_suite_register_check.py --json
    python tools/red_suite_register_check.py --selftest

Exit 0 every registered suite really is red; 1 the register is wrong;
2 COULD NOT RUN -- which is never folded into either of the other two.

── IT IS NOT tools/known_red_check.py AND THE DIFFERENCE IS THE COST ──────
That tool answers the richer question (NEW / KNOWN / CHANGED / RECOVERED) and
it is the one to reach for after a full run. But it needs a WHOLE-TREE run log
-- 738 files, the better part of an hour -- or `--run`, which produces one.
Its own header says, correctly, "It does not gate."

So on a normal batch nobody runs it, and the register rots between the runs
that do. **This one drives only the REGISTERED suites** -- thirteen files, not
738 -- so it is cheap enough to run every batch, and it EXITS NON-ZERO. The
two are the expensive half and the cheap half of one reconciliation, not two
tools for one job:

    known_red_check.py          whole tree, four answers, report-only, slow
    red_suite_register_check.py the register only, two answers, FAILS, fast

**Do not delete either believing it is the other.** Deleting this one loses
the cheap cadence; deleting that one loses the only thing that can find a NEW
red suite from a whole-tree log.

── THE TWO FAILURES, AND WHY A PASSING ENTRY IS THE WORSE ONE ─────────────
  RECOVERED      a registered suite now exits 0. **This is the finding that
                 matters.** A register entry is an exemption: while it stands,
                 a reader -- and known_red_check.py -- calls the next real
                 failure of that file KNOWN. A stale entry does not clutter
                 the register, it SWALLOWS the next regression in the one file
                 somebody already decided not to look at.
  UNREGISTERED   a suite the run log shows failing that no entry covers.
                 Only available with --from-run: this tool cannot know about
                 a file it was never pointed at, and it says so rather than
                 reporting "no unregistered reds" from a population of zero.

── WHAT IT REFUSES TO CALL EITHER ─────────────────────────────────────────
A registered file that does not EXIST, a suite whose interpreter is missing,
a suite that times out, a run log that cannot be parsed: each is COULD NOT RUN
and each is named. A suite that could not be launched is not a suite that
passed, and the whole reason this repo keeps re-learning PR §1.11 is that the
difference is one `else` branch wide.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN  # noqa: E402

REGISTRY = os.path.join(REPO, 'docs', 'known-red-suites.json')

# A per-suite ceiling. A suite that hangs is COULD NOT RUN, never a pass --
# the same reason PR §1.12 exists: an arm whose failure mode is a hang must be
# preceded by one that fails loudly, and here the ceiling IS that arm.
TIMEOUT_S = 420

# `  FAIL py    tests/x.py   tail` as tools/run_all_tests.py prints it.
FAIL_RE = re.compile(r'^\s{2}FAIL\s+(?:node|py)\s+(\S+)', re.M)
RAN_RE = re.compile(r'^RAN:', re.M)


def load_registry(path=REGISTRY):
    """-> (entries, could_not_run). Never raises on a bad file."""
    if not os.path.isfile(path):
        return None, 'the register is not at %s -- nothing was checked' % path
    try:
        doc = json.load(io.open(path, encoding='utf-8'))
    except ValueError as e:
        return None, 'the register is not valid JSON (%s) -- nothing was checked' % e
    entries = doc.get('entries')
    if not isinstance(entries, list):
        return None, 'the register has no `entries` list -- nothing was checked'
    return entries, None


def drive(rel, kind, repo=REPO, timeout=TIMEOUT_S):
    """Run one suite. -> (exit_code, note). exit_code None means COULD NOT RUN."""
    full = os.path.join(repo, rel.replace('/', os.sep))
    if not os.path.isfile(full):
        return None, 'the file does not exist'
    exe = [sys.executable] if kind == 'py' else ['node']
    try:
        r = subprocess.run(exe + [full], cwd=repo, capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=timeout)
    except FileNotFoundError:
        return None, '%s is not on PATH' % exe[0]
    except subprocess.TimeoutExpired:
        return None, 'timed out after %ds -- a hang is not a pass' % timeout
    return r.returncode, ''


def kind_of(entry, rel):
    k = entry.get('kind')
    if k in ('py', 'node'):
        return k
    return 'py' if rel.endswith('.py') else 'node'


def check(entries, run_log=None, repo=REPO, driver=drive):
    """-> (findings, could_not_run, driven). Pure except for `driver`."""
    findings = []
    could_not_run = []
    driven = []
    registered = set()

    for e in entries:
        rel = e.get('file')
        if not rel:
            could_not_run.append('a register entry has no `file` key')
            continue
        registered.add(rel.replace('\\', '/'))
        code, note = driver(rel, kind_of(e, rel), repo)
        driven.append({'file': rel, 'exit': code, 'note': note})
        if code is None:
            could_not_run.append('%s -- %s' % (rel, note))
        elif code == 0:
            findings.append({
                'kind': 'RECOVERED', 'file': rel, 'exit': 0,
                'detail': 'registered as red and it exits 0. DELETE THE ENTRY: '
                          'while it stands it absorbs the next real failure of '
                          'this file.'})

    if run_log is None:
        could_not_run.append(
            'no --from-run log, so UNREGISTERED red suites were not looked for. '
            'This run says nothing about suites outside the register.')
    else:
        if not RAN_RE.search(run_log):
            could_not_run.append(
                'the run log has no RAN: line -- it is truncated or is not a '
                'run-all-tests log, and reading it would report a clean '
                'platform from a file that never said so.')
        else:
            for rel in sorted(set(FAIL_RE.findall(run_log))):
                norm = rel.replace('\\', '/')
                if norm not in registered:
                    findings.append({
                        'kind': 'UNREGISTERED', 'file': norm, 'exit': 1,
                        'detail': 'red in the run log and no register entry '
                                  'covers it. A new regression is '
                                  'indistinguishable from the existing set '
                                  'until it is recorded.'})
    return findings, could_not_run, driven


def report(findings, could_not_run, driven, as_json=False):
    if as_json:
        print(json.dumps({'findings': findings, 'could_not_run': could_not_run,
                          'driven': driven}, indent=2, sort_keys=True))
    else:
        print('RED SUITE REGISTER CHECK -- is every registered entry still true?')
        print('  registered entries driven  %3d' % len(driven))
        print('')
        # EVERY EXIT CODE ON ITS OWN LINE, because a status read off the end of
        # a summary line is the misreading this repo has recorded four times.
        for d in driven:
            print('  %s' % d['file'])
            print('  %s' % ('COULD NOT RUN -- ' + d['note'] if d['exit'] is None
                            else d['exit']))
        print('')
        for f in findings:
            print('  %-12s %s' % (f['kind'], f['file']))
            print('               %s' % f['detail'])
    # could_not_run wins over findings -- a partial run's findings are a floor.
    if could_not_run:
        if not as_json:
            print('\nCOULD NOT RUN (%d) -- this is NOT a pass:' % len(could_not_run))
            for c in could_not_run:
                print('  %s' % c)
        return EXIT_COULD_NOT_RUN
    if findings:
        return EXIT_FINDING
    if not as_json:
        print('  Every registered suite is still red. No unregistered red suite '
              'in the log.')
    return EXIT_CLEAN


# ── SELFTEST. BOTH DIRECTIONS, and the clean arm is half the evidence ──────
def selftest():
    """Fixtures against a FAKE registry and FAKE suites, so the arms are about
    the rule and not about whatever the real tree happens to be doing today."""
    cases = []
    bad = 0

    def fake_driver(table):
        def d(rel, kind, repo):
            v = table.get(rel, ('missing',))
            if v[0] == 'missing':
                return None, 'the file does not exist'
            return v[1], ''
        return d

    def case(name, entries, table, log, want_exit, want_kinds):
        f, c, dr = check(entries, run_log=log, driver=fake_driver(table))
        code = report(f, c, dr, as_json=True) if False else (
            EXIT_COULD_NOT_RUN if c else (EXIT_FINDING if f else EXIT_CLEAN))
        kinds = sorted(set(x['kind'] for x in f))
        ok = (code == want_exit and kinds == sorted(want_kinds))
        cases.append((name, ok, code, kinds))
        return ok

    LOG_OK = 'RAN: 3 files\n  FAIL py    tests/a.py   boom\n  ok   py    tests/b.py\n'

    case('1. every registered suite still red, log clean -> EXIT 0',
         [{'file': 'tests/a.py', 'kind': 'py'}],
         {'tests/a.py': ('ran', 1)}, LOG_OK, EXIT_CLEAN, [])

    case('2. a registered suite that PASSES -> RECOVERED, EXIT 1',
         [{'file': 'tests/a.py', 'kind': 'py'}],
         {'tests/a.py': ('ran', 0)},
         'RAN: 1 files\n', EXIT_FINDING, ['RECOVERED'])

    case('3. a red suite the register does not cover -> UNREGISTERED, EXIT 1',
         [{'file': 'tests/b.py', 'kind': 'py'}],
         {'tests/b.py': ('ran', 1)}, LOG_OK, EXIT_FINDING, ['UNREGISTERED'])

    case('4. both at once -> both reported, not just the first',
         [{'file': 'tests/b.py', 'kind': 'py'}],
         {'tests/b.py': ('ran', 0)}, LOG_OK,
         EXIT_FINDING, ['RECOVERED', 'UNREGISTERED'])

    # LOG_CLEAN, not LOG_OK: the first version of arms 5 and 8 passed LOG_OK,
    # which names tests/a.py as failing, so each ALSO raised a correct
    # UNREGISTERED finding and the arm failed against right behaviour. The
    # fixture was wrong, not the rule -- recorded because fitting the rule to
    # the fixture instead is the easier mistake.
    LOG_CLEAN = 'RAN: 1 files\n  ok   py    tests/b.py\n'

    case('5. a registered file that does not exist -> COULD NOT RUN, EXIT 2',
         [{'file': 'tests/gone.py', 'kind': 'py'}],
         {}, LOG_CLEAN, EXIT_COULD_NOT_RUN, [])

    case('6. NO log -> COULD NOT RUN, because "no unregistered reds" would be '
         'a claim from a population of zero',
         [{'file': 'tests/a.py', 'kind': 'py'}],
         {'tests/a.py': ('ran', 1)}, None, EXIT_COULD_NOT_RUN, [])

    case('7. a TRUNCATED log -> COULD NOT RUN, never read as clean',
         [{'file': 'tests/a.py', 'kind': 'py'}],
         {'tests/a.py': ('ran', 1)},
         '  FAIL py    tests/a.py   boom\n', EXIT_COULD_NOT_RUN, [])

    case('8. an entry with no `file` key -> COULD NOT RUN, named',
         [{'kind': 'py'}], {}, LOG_CLEAN, EXIT_COULD_NOT_RUN, [])

    case('9. a backslash path in the log matches a forward-slash entry',
         [{'file': 'tests/a.py', 'kind': 'py'}],
         {'tests/a.py': ('ran', 1)},
         'RAN: 1 files\n  FAIL py    tests\\a.py   boom\n', EXIT_CLEAN, [])

    for name, ok, code, kinds in cases:
        print(('  ok   ' if ok else '  FAIL ') + name)
        if not ok:
            bad += 1
            print('        got exit %s, kinds %s' % (code, kinds))

    # CONTROLS. A fixture set that only ever reaches one verdict proves nothing.
    seen = set()
    for _n, _ok, code, _k in cases:
        seen.add(code)
    if seen != {EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN}:
        print('  FAIL CONTROL: the fixtures reach %s, not all three exit codes'
              % sorted(seen))
        bad += 1
    else:
        print('  ok   CONTROL: the fixtures reach all three exit codes')

    # And the registry loader's own refusals, which no case above touches.
    for label, path in (('absent file', os.path.join(REPO, 'docs', 'no-such.json')),
                        ('this .py file, which is not JSON', os.path.abspath(__file__))):
        entries, err = load_registry(path)
        if entries is None and err:
            print('  ok   CONTROL: load_registry refuses %s' % label)
        else:
            print('  FAIL CONTROL: load_registry accepted %s' % label)
            bad += 1

    print('\n%d case(s), %d failed' % (len(cases), bad))
    return EXIT_FINDING if bad else EXIT_CLEAN


def main(argv):
    if '--selftest' in argv:
        return selftest()
    entries, err = load_registry()
    if entries is None:
        sys.stderr.write('COULD NOT RUN -- %s\n' % err)
        return EXIT_COULD_NOT_RUN
    log = None
    if '--from-run' in argv:
        i = argv.index('--from-run')
        if i + 1 >= len(argv):
            sys.stderr.write('COULD NOT RUN -- --from-run needs a path\n')
            return EXIT_COULD_NOT_RUN
        p = argv[i + 1]
        if not os.path.isfile(p):
            sys.stderr.write('COULD NOT RUN -- no run log at %s\n' % p)
            return EXIT_COULD_NOT_RUN
        log = io.open(p, encoding='utf-8', errors='replace').read()
    findings, could_not_run, driven = check(entries, run_log=log)
    return report(findings, could_not_run, driven, as_json='--json' in argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
