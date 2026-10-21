#!/usr/bin/env python
"""hover_stryker_signal.py -- Stryker MUTATION TESTING as a FEEDING SIGNAL into this
role's review. Built H1 b74, item 5. Independent of H2's equivalent (not read).

THE QUESTION IT ANSWERS. "The author's tests pass" is weak evidence the changed
lines are PINNED by those tests. Stryker changes the code (`<` to `<=`, a
condition to `true`, a returned value to `undefined`) and re-runs the tests: a
mutant that SURVIVES on a line the commit just ADDED is a place where the tests
would not notice the behaviour changing. This wrapper runs Stryker on a clean
checkout of one commit and reports the survivors on the lines that commit added.

THREE DECISIONS THAT ARE NOT NEGOTIABLE, each fixture-locked:
  1. NODE 22, REFUSED OTHERWISE. The runtime is located and its major version
     read; anything but 22 is COULD NOT RUN, not a best-effort run on whatever
     node is on PATH.
  2. ALWAYS `--force`. Stryker's incremental mode reuses results from a previous
     run and is BLIND TO TEST-FILE CHANGES: a test that was weakened since the
     last run still "kills" the mutants it killed before. The argv builder cannot
     produce a command without `--force`, and the config sets incremental false.
  3. FAIL-CLOSED. A run that did not complete, produced no report, produced zero
     mutants, found no test that exercises the file, or whose mutants mostly
     errored is INCONCLUSIVE. Only a completed run with full coverage and no
     survivor on an added line is CLEAN, and "CLEAN" here means those mutants,
     under those tests -- never that the change is correct.

HONEST STATE AT BUILD TIME, said first: Stryker and Node 22 are NOT installed on
this machine, and the permission rules deny package installs (npm install / pip
install / winget / curl), so this tool was NOT run against the real Stryker. What
is verified: the argv and config builders, the report parser and classifier
(against a hand-built report in Stryker's documented mutation-testing-elements
schema), the fail-closed paths, and the plumbing end to end against a FAKE
stryker.js that writes a canned report. What is NOT verified: compatibility with
the real binary's CLI and report. The first real run is the verification, and
until then every result carries `UNVERIFIED-AGAINST-REAL-STRYKER`.

UPDATE b79: the first real run happened in b78 (fourth's b46 geocode commit,
real binary, report parsed). The tag is therefore DERIVED, not hard-coded: a
report whose `framework` block names StrykerJS is tagged `STRYKER-<version>`; a
report with no such block (the fake in the selftest, anything unrecognised)
keeps `UNVERIFIED-AGAINST-REAL-STRYKER`. Second b79 change: a commit whose own
tests carry in-file mutation arms (anchor strings in the source's TEXT) used to
abort Stryker's dry run, because Stryker instruments a copy of the file and
every anchor then matches 0 times (exit 2 COULD NOT RUN, which would also
shadow a real arm failure). The test command now loads hover_stryker_preload.js,
which returns the pristine text for the test's own reads of the mutated file and
leaves `require` instrumented.

EXIT CODES: 0 CLEAN, 1 FINDINGS (survivors on added lines), 2 INCONCLUSIVE or
COULD NOT RUN.

Run:
  python hover_stryker_signal.py --availability
  python hover_stryker_signal.py --run --sha <sha> [--files api/a.js,api/b.js] [--added-from <sha>]
  python hover_stryker_signal.py --selftest
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_INCONCLUSIVE = 2
REQUIRED_NODE_MAJOR = 22
ERROR_RATIO_LIMIT = 0.25
TOOL_ROOT = os.path.join(os.path.expanduser('~'), '.claude', 'projects',
                         'C--Users-marsh-Documents-SAIRN-hover', 'hover-audit-log', 'ext')
UNVERIFIED = 'UNVERIFIED-AGAINST-REAL-STRYKER'
PRELOAD = os.path.join(HERE, 'hover_stryker_preload.js')
INSTALL_STEPS = (
    'Run these yourself (the permission rules deny them to this session; prefix '
    'each with ! in the prompt):',
    '  mkdir -p "%s"' % TOOL_ROOT,
    '  npm install --prefix "%s" node@22 @stryker-mutator/core' % TOOL_ROOT,
    'then re-run --availability. Pin versions (>= 2 weeks old) in the command '
    'if you want them fixed.')


def node_major(node):
    try:
        r = subprocess.run([node, '--version'], capture_output=True, text=True, timeout=20)
        m = re.match(r'v(\d+)\.', r.stdout.strip())
        return int(m.group(1)) if m else None
    except Exception:
        return None


def locate(env=None, major_fn=node_major):
    """{'node','stryker_js','problems'}. Nothing is installed or fetched here."""
    env = os.environ if env is None else env
    problems = []
    node = None
    exe = 'node.exe' if os.name == 'nt' else 'node'
    for c in (env.get('HOVER_NODE22'),
              os.path.join(TOOL_ROOT, 'node_modules', 'node', 'bin', exe),
              os.path.join(TOOL_ROOT, 'node_modules', 'node', exe),
              shutil.which('node')):
        if c and os.path.isfile(c):
            m = major_fn(c)
            if m == REQUIRED_NODE_MAJOR:
                node = c
                break
            problems.append('node at %s is major %s, not %d' % (c, m, REQUIRED_NODE_MAJOR))
    if not node:
        problems.append('NO NODE %d FOUND (a different major is refused, not tolerated)'
                        % REQUIRED_NODE_MAJOR)
    sj = env.get('HOVER_STRYKER_JS') or os.path.join(
        TOOL_ROOT, 'node_modules', '@stryker-mutator', 'core', 'bin', 'stryker.js')
    if not os.path.isfile(sj):
        problems.append('NO STRYKER at %s' % sj)
        sj = None
    return {'node': node, 'stryker_js': sj, 'problems': problems}


def build_config(mutate, test_cmd, report_path):
    """The Stryker config. incremental is FALSE here and --force is on argv:
    two independent locks on the same decision."""
    return {
        'mutate': list(mutate),
        'testRunner': 'command',
        'commandRunner': {'command': test_cmd},
        'coverageAnalysis': 'off',
        'concurrency': 1,
        'incremental': False,
        'reporters': ['json'],
        'jsonReporter': {'fileName': report_path},
        'timeoutMS': 60000,
        'cleanTempDir': True,
        'ignorePatterns': ['.git', 'node_modules', 'docs', 'sql', '*.html', 'SAIRN-*'],
    }


def report_tag(report):
    """DERIVED from the report itself: only a report that names StrykerJS counts
    as having come from the real binary."""
    fw = (report or {}).get('framework') or {}
    if str(fw.get('name', '')).lower() == 'strykerjs' and fw.get('version'):
        return 'STRYKER-%s' % fw['version']
    return UNVERIFIED


def installed_tag(loc):
    """Tag for the --availability line: the installed package's own version, or
    UNVERIFIED when it cannot be read (never an assumed one)."""
    try:
        pj = os.path.join(os.path.dirname(os.path.dirname(loc['stryker_js'])), 'package.json')
        with open(pj, encoding='utf-8') as f:
            d = json.load(f)
        if d.get('name') == '@stryker-mutator/core' and d.get('version'):
            return 'STRYKER-%s installed' % d['version']
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return UNVERIFIED


def build_test_command(node, tests, preload=PRELOAD):
    """The command Stryker runs per mutant. Each test runs under the preload so
    its own reads of the mutated source's text see the pristine file."""
    return ' && '.join('"%s" -r "%s" %s' % (node, preload, t) for t in tests)


def build_argv(node, stryker_js, config_path):
    argv = [node, stryker_js, 'run', '--force', config_path]
    assert '--force' in argv   # not a comment: an assertion the fixtures drive
    return argv


def parse_report(report, added_by_file):
    """PURE. Per file: counts by status, and the SURVIVORS (Survived or
    NoCoverage) located on lines the commit ADDED."""
    out = {}
    for path, f in (report.get('files') or {}).items():
        added = added_by_file.get(path) or added_by_file.get(path.replace('\\', '/')) or set()
        counts, surv, on_added = {}, [], 0
        for m in f.get('mutants') or []:
            st = m.get('status')
            counts[st] = counts.get(st, 0) + 1
            line = ((m.get('location') or {}).get('start') or {}).get('line')
            if line in added:
                on_added += 1
                if st in ('Survived', 'NoCoverage'):
                    surv.append({'line': line, 'mutator': m.get('mutatorName'),
                                 'replacement': str(m.get('replacement'))[:60], 'status': st})
        out[path] = {'counts': counts, 'mutants_on_added_lines': on_added, 'survivors': surv}
    return out


def classify(parsed, ran_with_force, tests_found):
    """PURE. (status, reasons)."""
    reasons = []
    if not ran_with_force:
        reasons.append('--force NOT USED: incremental results are blind to test-file changes')
    if not tests_found:
        reasons.append('NO TEST FILE EXERCISES THE MUTATED FILE(S): nothing to kill a mutant with')
    if not parsed:
        reasons.append('NO REPORT / NO FILES in the report')
    total = sum(sum(v['counts'].values()) for v in parsed.values())
    if parsed and total == 0:
        reasons.append('ZERO MUTANTS generated: the run read nothing it could mutate')
    bad = sum(v['counts'].get('RuntimeError', 0) + v['counts'].get('CompileError', 0) for v in parsed.values())
    tmo = sum(v['counts'].get('Timeout', 0) for v in parsed.values())
    if total and (bad / total) > ERROR_RATIO_LIMIT:
        reasons.append('%d of %d mutants ERRORED (> %d%%): the tests did not really run against them'
                       % (bad, total, int(ERROR_RATIO_LIMIT * 100)))
    if total and (tmo / total) > ERROR_RATIO_LIMIT:
        reasons.append('%d of %d mutants TIMED OUT (> %d%%): timeouts count as killed and may be an infinite loop'
                       % (tmo, total, int(ERROR_RATIO_LIMIT * 100)))
    if reasons:
        return 'INCONCLUSIVE', reasons
    if any(v['survivors'] for v in parsed.values()):
        return 'FINDINGS', ['at least one mutant SURVIVED on a line this commit added']
    if not any(v['mutants_on_added_lines'] for v in parsed.values()):
        return 'INCONCLUSIVE', ['no mutant landed on an ADDED line, so the commit\'s own changes were not tested at all']
    return 'CLEAN', ['every mutant on an added line was killed']


def discover_tests(root, source_rel):
    """Test files under root that mention the source's basename."""
    base = os.path.basename(source_rel)
    stem = os.path.splitext(base)[0]
    found = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ('.git', 'node_modules')]
        for f in fn:
            if '.test.' not in f:
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, encoding='utf-8', errors='replace') as fh:
                    txt = fh.read()
            except OSError:
                continue
            if base in txt or ("'%s'" % stem) in txt:
                found.append(os.path.relpath(p, root).replace('\\', '/'))
    return sorted(found)


def execute(loc, workdir, mutate, test_cmd, timeout=1800, env=None):
    """Run Stryker in `workdir` (a throwaway checkout). Returns (ran, report|None, note)."""
    rep = os.path.join(workdir, 'reports', 'mutation', 'mutation.json')
    cfg = os.path.join(workdir, 'stryker.hover.conf.json')
    with open(cfg, 'w', encoding='utf-8') as f:
        json.dump(build_config(mutate, test_cmd, rep), f)
    argv = build_argv(loc['node'], loc['stryker_js'], cfg)
    try:
        r = subprocess.run(argv, cwd=workdir, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return True, None, 'stryker TIMED OUT after %ds' % timeout
    note = 'stryker exit %s' % r.returncode
    if not os.path.isfile(rep):
        return True, None, note + '; no report at ' + rep + '; ' + (r.stderr or '')[-200:]
    try:
        with open(rep, encoding='utf-8') as f:
            return True, json.load(f), note
    except ValueError:
        return True, None, note + '; report was not valid JSON'


def run_commit(sha, files, repo, loc=None, added_from=None):
    """The on-demand signal for one commit. {'status','reasons','per_file','note','tag'}.
    `added_from`: judge the lines ANOTHER commit added under THIS commit's tests (the
    code commit and its tests often land apart; the file must be unchanged between
    the two or the line numbers do not line up, which the caller has to check)."""
    loc = loc or locate()
    if loc['problems'] and (not loc['node'] or not loc['stryker_js']):
        return {'status': 'COULD_NOT_RUN', 'reasons': loc['problems'] + list(INSTALL_STEPS),
                'per_file': {}, 'note': '', 'tag': UNVERIFIED}
    sys.path.insert(0, HERE)
    import hover_cross_vendor_check as X
    diff = X.get_diff('%s~1..%s' % (added_from or sha, added_from or sha), repo)
    added = X.added_lines_with_numbers(diff)
    targets = [f for f in (files or sorted(added)) if f.endswith('.js') and '.test.' not in f]
    if not targets:
        return {'status': 'INCONCLUSIVE', 'reasons': ['no non-test .js file in this commit to mutate'],
                'per_file': {}, 'note': '', 'tag': UNVERIFIED}
    wt = tempfile.mkdtemp(prefix='h1-stryker-')
    wt_repo = os.path.join(wt, 'wt')
    try:
        r = subprocess.run(['git', 'worktree', 'add', '--detach', wt_repo, sha], cwd=repo,
                           capture_output=True, text=True)
        if r.returncode != 0:
            return {'status': 'COULD_NOT_RUN', 'reasons': ['git worktree add failed: ' + r.stderr[:200]],
                    'per_file': {}, 'note': '', 'tag': UNVERIFIED}
        tests = sorted({t for f in targets for t in discover_tests(wt_repo, f)})
        cmd = build_test_command(loc['node'], tests) if tests else '"%s" -e "process.exit(1)"' % loc['node']
        env = dict(os.environ, HOVER_STRYKER_PRISTINE=wt_repo,
                   HOVER_STRYKER_TARGETS='|'.join(t.replace(chr(92), '/') for t in targets))
        ran, report, note = execute(loc, wt_repo, targets, cmd, env=env)
        parsed = parse_report(report or {}, added)
        st, reasons = classify(parsed, True, bool(tests))
        if report is None:
            reasons.append('stryker gave no report: ' + note)
        return {'status': st, 'reasons': reasons, 'per_file': parsed, 'note': note,
                'tests': tests, 'tag': report_tag(report)}
    finally:
        subprocess.run(['git', 'worktree', 'remove', '--force', wt_repo], cwd=repo, capture_output=True)
        shutil.rmtree(wt, ignore_errors=True)


def availability_line():
    """One line for hover_static_input's not_available list."""
    loc = locate()
    if loc['node'] and loc['stryker_js']:
        return None
    return 'NOT RUN: ' + '; '.join(loc['problems'][:3])


def main(argv):
    if '--selftest' in argv:
        return selftest()
    if '--availability' in argv:
        loc = locate()
        if loc['node'] and loc['stryker_js']:
            print('AVAILABLE: node %s, stryker %s  [%s]' % (loc['node'], loc['stryker_js'], installed_tag(loc)))
            return EXIT_CLEAN
        print('COULD NOT RUN:')
        for p in loc['problems']:
            print('  - ' + p)
        for l in INSTALL_STEPS:
            print(l)
        return EXIT_INCONCLUSIVE
    if '--run' in argv:
        def opt(n, d=None):
            return argv[argv.index(n) + 1] if n in argv and argv.index(n) + 1 < len(argv) else d
        sha = opt('--sha')
        if not sha:
            print('COULD NOT RUN: --run needs --sha')
            return EXIT_INCONCLUSIVE
        files = [f for f in (opt('--files') or '').split(',') if f]
        repo = opt('--cwd', os.path.join(os.path.expanduser('~'), 'Documents', 'SAIRN-hover'))
        res = run_commit(sha, files, repo, added_from=opt('--added-from'))
        print('STRYKER SIGNAL: %s  [%s]' % (res['status'], res['tag']))
        for r in res['reasons']:
            print('  REASON: ' + r)
        for p, v in res['per_file'].items():
            print('  %s  counts=%s  mutants-on-added-lines=%d' % (p, v['counts'], v['mutants_on_added_lines']))
            for s in v['survivors']:
                print('      SURVIVED line %s  %s -> %s  (%s)' % (s['line'], s['mutator'], s['replacement'], s['status']))
        print('INCONCLUSIVE IS NOT CLEAN. A survivor is a place the tests would not notice; it is a prompt to look.')
        return {'CLEAN': EXIT_CLEAN, 'FINDINGS': EXIT_FINDINGS}.get(res['status'], EXIT_INCONCLUSIVE)
    print('usage: --availability | --run --sha SHA [--files a,b] [--added-from SHA] | --selftest')
    return EXIT_INCONCLUSIVE


def selftest():
    ok_n, bad_n = [0], [0]

    def ck(name, cond):
        if cond:
            ok_n[0] += 1
            print('  ok   %s' % name)
        else:
            bad_n[0] += 1
            print('  FAIL %s' % name)

    argv = build_argv('/n/node', '/s/stryker.js', '/c/conf.json')
    cfg = build_config(['api/a.js'], 'node api/a.test.js', '/r/mutation.json')
    ck('Y1 the argv builder ALWAYS carries --force, before the config path',
       argv[:3] == ['/n/node', '/s/stryker.js', 'run'] and argv.index('--force') < argv.index('/c/conf.json'))
    ck('Y2 the config sets incremental FALSE (a second lock on the same decision), '
       'the command runner, no coverage analysis, one worker, a json report',
       cfg['incremental'] is False and cfg['testRunner'] == 'command'
       and cfg['coverageAnalysis'] == 'off' and cfg['concurrency'] == 1
       and cfg['reporters'] == ['json'] and cfg['mutate'] == ['api/a.js']
       and cfg['commandRunner']['command'] == 'node api/a.test.js')

    tmp = tempfile.mkdtemp(prefix='h1-stryker-st-')
    try:
        fake_node = os.path.join(tmp, 'node.exe')
        fake_js = os.path.join(tmp, 'stryker.js')
        open(fake_node, 'w').write('x')
        open(fake_js, 'w').write('x')
        loc22 = locate({'HOVER_NODE22': fake_node, 'HOVER_STRYKER_JS': fake_js}, major_fn=lambda n: 22)
        loc24 = locate({'HOVER_NODE22': fake_node, 'HOVER_STRYKER_JS': fake_js}, major_fn=lambda n: 24)
        ck('Y3 locate accepts a node whose major is 22 and REFUSES a 24 (named), '
           'never "close enough"',
           loc22['node'] == fake_node and loc22['stryker_js'] == fake_js
           and loc24['node'] is None
           and any('major 24, not 22' in p for p in loc24['problems']))
        miss = locate({'HOVER_STRYKER_JS': os.path.join(tmp, 'absent-stryker.js')}, major_fn=lambda n: None)
        ck('Y4 nothing found -> no node, no stryker, and the problems NAME what is missing',
           miss['stryker_js'] is None and any('NO STRYKER' in p for p in miss['problems'])
           and any('NO NODE 22' in p for p in miss['problems']))

        report = {'schemaVersion': '1', 'files': {'api/x.js': {'language': 'javascript', 'mutants': [
            {'id': '1', 'mutatorName': 'ConditionalExpression', 'replacement': 'true',
             'location': {'start': {'line': 5, 'column': 1}, 'end': {'line': 5, 'column': 9}}, 'status': 'Killed'},
            {'id': '2', 'mutatorName': 'EqualityOperator', 'replacement': '<=',
             'location': {'start': {'line': 6, 'column': 1}, 'end': {'line': 6, 'column': 9}}, 'status': 'Survived'},
            {'id': '3', 'mutatorName': 'StringLiteral', 'replacement': '""',
             'location': {'start': {'line': 9, 'column': 1}, 'end': {'line': 9, 'column': 9}}, 'status': 'NoCoverage'},
        ]}}}
        parsed = parse_report(report, {'api/x.js': {5, 6}})
        st, why = classify(parsed, True, True)
        ck('Y5 parse_report finds the survivor on an ADDED line (6) and ignores the '
           'NoCoverage mutant on a line the commit did not add (9) -> FINDINGS',
           [s['line'] for s in parsed['api/x.js']['survivors']] == [6]
           and parsed['api/x.js']['mutants_on_added_lines'] == 2 and st == 'FINDINGS')
        killed_all = {'files': {'api/x.js': {'mutants': [
            {'status': 'Killed', 'mutatorName': 'M', 'replacement': 'r', 'location': {'start': {'line': 5}}}]}}}
        ck('Y6 every mutant on an added line killed -> CLEAN',
           classify(parse_report(killed_all, {'api/x.js': {5}}), True, True)[0] == 'CLEAN')
        ck('Y7 INCONCLUSIVE, never CLEAN: not forced / no tests / no report / zero mutants / '
           'no mutant on an added line',
           classify(parse_report(killed_all, {'api/x.js': {5}}), False, True)[0] == 'INCONCLUSIVE'
           and classify(parse_report(killed_all, {'api/x.js': {5}}), True, False)[0] == 'INCONCLUSIVE'
           and classify({}, True, True)[0] == 'INCONCLUSIVE'
           and classify(parse_report({'files': {'api/x.js': {'mutants': []}}}, {}), True, True)[0] == 'INCONCLUSIVE'
           and classify(parse_report(killed_all, {'api/x.js': {99}}), True, True)[0] == 'INCONCLUSIVE')
        errs = {'files': {'api/x.js': {'mutants': [
            {'status': 'RuntimeError', 'location': {'start': {'line': 5}}}] * 3 + [
            {'status': 'Killed', 'location': {'start': {'line': 5}}}]}}}
        tmo = {'files': {'api/x.js': {'mutants': [
            {'status': 'Timeout', 'location': {'start': {'line': 5}}}] * 3 + [
            {'status': 'Killed', 'location': {'start': {'line': 5}}}]}}}
        ck('Y8 mostly-errored or mostly-timed-out mutants are INCONCLUSIVE (the tests '
           'did not really run against them)',
           classify(parse_report(errs, {'api/x.js': {5}}), True, True)[0] == 'INCONCLUSIVE'
           and classify(parse_report(tmo, {'api/x.js': {5}}), True, True)[0] == 'INCONCLUSIVE')

        none_loc = {'node': None, 'stryker_js': None, 'problems': ['NO NODE 22 FOUND', 'NO STRYKER at x']}
        r_missing = run_commit('HEAD', [], tmp, loc=none_loc)
        ck('Y9 with the tools absent, run_commit answers COULD_NOT_RUN with the exact install '
           'steps -- never CLEAN, never a best-effort run',
           r_missing['status'] == 'COULD_NOT_RUN' and any('npm install' in x for x in r_missing['reasons'])
           and r_missing['tag'] == UNVERIFIED)

        node = shutil.which('node')
        git_ok = shutil.which('git') is not None
        if not node or not git_ok:
            ck('Y10 plumbing against a fake stryker needs node and git on PATH', False)
        else:
            repo = os.path.join(tmp, 'repo')
            os.makedirs(os.path.join(repo, 'api'))

            def git(*a):
                return subprocess.run(['git', '-c', 'commit.gpgsign=false', '-c', 'user.email=t@t.invalid',
                                        '-c', 'user.name=t'] + list(a), cwd=repo, capture_output=True, text=True)
            git('init', '-q')
            open(os.path.join(repo, 'api', 'a.js'), 'w').write('module.exports = (x) => x > 1;\n')
            open(os.path.join(repo, 'api', 'a.test.js'), 'w').write("const f = require('./a.js'); process.exit(f(2) ? 0 : 1);\n")
            git('add', '-A'); git('commit', '-q', '-m', 'base')
            open(os.path.join(repo, 'api', 'a.js'), 'w').write('module.exports = (x) => x > 1;\nmodule.exports.limit = 5;\n')
            git('add', '-A'); git('commit', '-q', '-m', 'add limit')
            sha = git('rev-parse', 'HEAD').stdout.strip()
            fake = os.path.join(tmp, 'fake_stryker.js')
            open(fake, 'w').write(
                "const fs=require('fs'),path=require('path');\n"
                "const a=process.argv; if(!a.includes('--force')) process.exit(3);\n"
                "const cfg=JSON.parse(fs.readFileSync(a[a.length-1],'utf8'));\n"
                "if(cfg.incremental!==false) process.exit(4);\n"
                "const mode=process.env.FAKE_MODE||'survivor';\n"
                "if(mode==='crash') process.exit(5);\n"
                "const muts= mode==='empty'?[]:[{id:'1',mutatorName:'NumericLiteral',replacement:'6',status:mode==='clean'?'Killed':'Survived',location:{start:{line:2,column:1},end:{line:2,column:30}}}];\n"
                "fs.mkdirSync(path.dirname(cfg.jsonReporter.fileName),{recursive:true});\n"
                "fs.writeFileSync(cfg.jsonReporter.fileName,JSON.stringify({schemaVersion:'1',files:{'api/a.js':{language:'javascript',mutants:muts}}}));\n")
            loc = locate({'HOVER_NODE22': node, 'HOVER_STRYKER_JS': fake}, major_fn=lambda n: 22)
            results = {}
            for mode in ('survivor', 'clean', 'empty', 'crash'):
                os.environ['FAKE_MODE'] = mode
                results[mode] = run_commit(sha, ['api/a.js'], repo, loc=loc)
            os.environ.pop('FAKE_MODE', None)
            ck('Y10 PLUMBING against a FAKE stryker (it exits non-zero unless --force is on argv '
               'and incremental is false in the config): a survivor on the added line -> FINDINGS, '
               'all killed -> CLEAN, zero mutants -> INCONCLUSIVE, a crash with no report -> '
               'INCONCLUSIVE; every result tagged ' + UNVERIFIED,
               results['survivor']['status'] == 'FINDINGS' and results['clean']['status'] == 'CLEAN'
               and results['empty']['status'] == 'INCONCLUSIVE' and results['crash']['status'] == 'INCONCLUSIVE'
               and results['survivor']['tests'] == ['api/a.test.js']
               and all(r['tag'] == UNVERIFIED for r in results.values()))
            open(os.path.join(repo, 'api', 'b.test.js'), 'w', newline='').write("process.exit(0);" + chr(10))
            git('add', '-A'); git('commit', '-q', '-m', 'tests only')
            sha_t = git('rev-parse', 'HEAD').stdout.strip()
            os.environ['FAKE_MODE'] = 'survivor'
            r_own = run_commit(sha_t, ['api/a.js'], repo, loc=loc)
            r_from = run_commit(sha_t, ['api/a.js'], repo, loc=loc, added_from=sha)
            os.environ.pop('FAKE_MODE', None)
            ck('Y16 --added-from: a tests-only commit has no added line in the source (INCONCLUSIVE, '
               'named), but judged against the code commit that added the lines it is FINDINGS',
               r_own['status'] == 'INCONCLUSIVE' and r_from['status'] == 'FINDINGS')
            ck('Y11 the throwaway worktree was removed afterwards (only the main checkout '
               'is still registered in the repo)',
               len([l for l in git('worktree', 'list').stdout.splitlines() if l.strip()]) == 1)
        ck('Y13 the tag is DERIVED from the report: a StrykerJS framework block -> STRYKER-<version>; '
           'no block (the fake) or a different framework -> UNVERIFIED',
           report_tag({'framework': {'name': 'StrykerJS', 'version': '9.1.1'}}) == 'STRYKER-9.1.1'
           and report_tag({'schemaVersion': '1', 'files': {}}) == UNVERIFIED
           and report_tag({'framework': {'name': 'Other', 'version': '1'}}) == UNVERIFIED
           and report_tag(None) == UNVERIFIED)
        tc = build_test_command('/n/node', ['api/a.test.js', 'api/b.test.js'], preload='/p/pre.js')
        ck('Y14 every test in the command runs under the preload, chained with &&',
           tc == '"/n/node" -r "/p/pre.js" api/a.test.js && "/n/node" -r "/p/pre.js" api/b.test.js')
        if node:
            # THE b79 CLASS, driven: a test that builds its own mutants by string anchor in the
            # source TEXT. Stryker's sandbox holds an instrumented copy (anchor matches 0 times),
            # the pristine file holds it once. The test exits 2 COULD NOT RUN on the instrumented
            # text, and 0 with the preload; a real arm failure must still exit 1, not be shadowed.
            sb = os.path.join(tmp, 'sb')
            pr = os.path.join(tmp, 'pr')
            for d in (sb, pr):
                os.makedirs(os.path.join(d, 'api'))
            open(os.path.join(pr, 'api', 'a.js'), 'w', newline='').write('module.exports = () => 1; // ANCHOR\n')
            open(os.path.join(sb, 'api', 'a.js'), 'w', newline='').write('module.exports = () => stryMutAct(1); // ANCHOR-INSTRUMENTED\n')
            open(os.path.join(sb, 'api', 'a.test.js'), 'w', newline='').write(
                "const fs=require('fs'),path=require('path');\n"
                "const SRC=fs.readFileSync(path.join(__dirname,'a.js'),'utf8');\n"
                "const n=SRC.split('// ANCHOR' + String.fromCharCode(10)).length-1;\n"
                "if(n!==1){console.log('COULD NOT RUN anchor found '+n);process.exit(2);}\n"
                "const v=require('./a.js');\n"
                "process.exit(process.env.FAIL_ARM==='1'?1:0);\n")
            def run_t(use_preload, fail_arm=False):
                env = dict(os.environ, HOVER_STRYKER_PRISTINE=pr, HOVER_STRYKER_TARGETS='api/a.js')
                env.pop('FAIL_ARM', None)
                if fail_arm:
                    env['FAIL_ARM'] = '1'
                cmd = [node] + (['-r', PRELOAD] if use_preload else []) + ['api/a.test.js']
                return subprocess.run(cmd, cwd=sb, env=env, capture_output=True, text=True).returncode
            no_pre, with_pre, with_pre_fail = run_t(False), run_t(True), run_t(True, True)
            ck('Y15 WITHOUT the preload the instrumented text breaks the anchors of a test that builds its own '
               'mutants (exit 2); WITH it the test passes (exit 0) and a real arm failure still exits 1, '
               'not shadowed by 2',
               (no_pre, with_pre, with_pre_fail) == (2, 0, 1))
        else:
            ck('Y15 the preload class needs node on PATH', False)
        al = availability_line()
        loc_real = locate()
        ck('Y12 availability_line names the absence in the review input when the tools are '
           'missing (and is None only when both are found)',
           (al is None) == bool(loc_real['node'] and loc_real['stryker_js']) and (al is None or al.startswith('NOT RUN')))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('%d ok, %d failed' % (ok_n[0], bad_n[0]))
    return EXIT_CLEAN if not bad_n[0] else EXIT_FINDINGS


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
