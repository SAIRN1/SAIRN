#!/usr/bin/env python
"""hover_semgrep_signal.py -- a FAIL-CLOSED wrapper around Semgrep (or Opengrep)
as a FEEDING SIGNAL into this role's review. Built H1 b74, item 5. Independent
of H2's equivalent: written from the Semgrep CLI's own documented JSON output,
with no H2 code or rule read.

THE ONE RULE THIS FILE EXISTS FOR. A clean scan is a statement about the files
the tool actually read with rules it actually loaded. Semgrep exits 0 with a
non-empty `errors` array, exits 7 on an invalid rule file, and exits 0 on a
directory it silently skipped -- in every case the default reading ("exit 0,
no findings, clean") is wrong. This wrapper returns CLEAN only when ALL of:
  1. a binary was found AND a POSITIVE CONTROL (a canary rule that must fire on
     a canary file) AND a NEGATIVE CONTROL (the same rule that must NOT fire on
     a safe file) both behave, in this same invocation -- so "no findings" can
     only mean the engine works and the files are clean to these rules;
  2. every target was scanned (paths.scanned covers all of them);
  3. the errors array is empty and nothing was skipped;
  4. no timeout, no unparseable output, an exit code of 0 or 1.
Anything else is INCONCLUSIVE; a missing binary is COULD NOT RUN. Neither is
ever folded into a pass. This was not theoretical: the first draft of
semgrep-rules/hover-risk.yml failed to load (YAML: a plain scalar cannot hold
": "), semgrep exited 7, and the scan printed ZERO findings for 24 files -- a
clean-looking result from a run that read nothing.

WHAT A FINDING IS. A prompt to look, never a verdict. The rule pack's measured
behaviour against the witnessed planted-bug set is locked in --selftest, with
its blind spots listed, because a rule that is silent on a hard spelling of a
defect reports nothing about it.

EXIT CODES (the same trio as hover_static_input): 0 CLEAN, 1 FINDINGS,
2 INCONCLUSIVE / COULD NOT RUN.

Run:
  python hover_semgrep_signal.py --scan <file> [<file>...]
  python hover_semgrep_signal.py --canary
  python hover_semgrep_signal.py --selftest
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RULES_PATH = os.path.join(HERE, 'semgrep-rules', 'hover-risk.yml')
EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_INCONCLUSIVE = 2
# Overridable because the engine is SLOW WHEN THE MACHINE IS BUSY (found live in b74:
# a 0.5s canary became a >90s one while another session ran its own scans, and the
# wrapper correctly failed closed with COULD NOT RUN). A longer limit changes how
# long it waits, never what a timeout means.
PER_RUN_TIMEOUT = int(os.environ.get('HOVER_SEMGREP_TIMEOUT', '240'))
CANARY_TIMEOUT = int(os.environ.get('HOVER_SEMGREP_CANARY_TIMEOUT', '90'))

CANARY_RULE = ('rules:\n  - id: hover.canary\n    languages: [javascript]\n'
               '    severity: WARNING\n    message: canary\n'
               '    pattern: |\n      eval(...)\n')


def find_binary():
    """(path, reason). Order: HOVER_SEMGREP_BIN, PATH (semgrep then opengrep),
    then the user-scripts directory a `pip install --user` puts it in -- which
    is NOT on PATH on Windows, the reason a plain `where semgrep` says absent
    while pip lists it installed."""
    cands = []
    if os.environ.get('HOVER_SEMGREP_BIN'):
        cands.append(os.environ['HOVER_SEMGREP_BIN'])
    for n in ('semgrep', 'opengrep'):
        w = shutil.which(n)
        if w:
            cands.append(w)
    try:
        import sysconfig
        for scheme in ('nt_user', 'posix_user'):
            try:
                d = sysconfig.get_path('scripts', scheme)
            except Exception:
                continue
            for n in ('semgrep.exe', 'semgrep', 'opengrep.exe', 'opengrep'):
                cands.append(os.path.join(d, n))
    except Exception:
        pass
    for c in cands:
        if c and os.path.isfile(c):
            return c, 'found at %s' % c
    return None, ('no semgrep or opengrep found (HOVER_SEMGREP_BIN unset, not '
                  'on PATH, not in the user scripts directory)')


def _env_for(binary):
    env = dict(os.environ)
    # semgrep.exe on Windows execs `pysemgrep`, which lives beside it.
    env['PATH'] = os.path.dirname(binary) + os.pathsep + env.get('PATH', '')
    env['SEMGREP_SEND_METRICS'] = 'off'
    env['PYTHONUTF8'] = '1'
    return env


def scan_cwd(paths):
    """The directory the engine MUST run in: the closest common ancestor of its
    targets. FOUND LIVE, b74, by elimination across four invocations of the same
    scan on the same two-file canary: with the working directory ABOVE or AT the
    targets semgrep finished in ~6 s; with the working directory anywhere else
    (an empty directory, a populated one, this tool's own directory) and the same
    absolute target paths, it did not finish in 45 s and was killed. Cause not
    established -- the rule is empirical, said as such. Before this, the wrapper
    inherited its caller's cwd, its canary timed out, and it correctly reported
    COULD NOT RUN for a healthy engine for the better part of an hour."""
    if not paths:
        return None
    ds = [os.path.dirname(os.path.abspath(p)) for p in paths]
    try:
        return os.path.commonpath(ds)
    except ValueError:      # targets on different drives
        return ds[0]


def _kill_tree(pid):
    """Kill a process AND ITS DESCENDANTS. semgrep.exe execs pysemgrep which
    spawns semgrep-core; killing only the direct child leaves the grandchild
    running and still holding the output handles."""
    if os.name == 'nt':
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)],
                       capture_output=True, text=True)
    else:
        try:
            os.killpg(os.getpgid(pid), 9)
        except OSError:
            pass


def run_scan(binary, rules, paths, timeout=PER_RUN_TIMEOUT, argv=None, cwd=None):
    """{'exit', 'json', 'timed_out', 'stderr'} -- raw, uninterpreted. THE TIMEOUT
    IS REAL: output goes to temp FILES, not pipes, and a timeout kills the whole
    process tree. The first version used subprocess.run(timeout=...) over pipes,
    and on Windows that blocked for MINUTES past its timeout because the
    grandchild kept the pipes open (found live, b74, on a machine another
    session was loading) -- a timeout that does not time out turns a wedged
    engine into a wedged review."""
    cmd = argv or ([binary, 'scan', '--config', rules, '--metrics=off',
                    '--disable-version-check', '--json', '--quiet',
                    '--no-git-ignore'] + list(paths))
    with tempfile.TemporaryFile() as fo, tempfile.TemporaryFile() as fe:
        try:
            p = subprocess.Popen(cmd, stdout=fo, stderr=fe, stdin=subprocess.DEVNULL,
                                 cwd=cwd or scan_cwd(paths), env=_env_for(binary),
                                 **({} if os.name == 'nt' else {'start_new_session': True}))
        except OSError as e:
            return {'exit': None, 'json': None, 'timed_out': False,
                    'stderr': 'could not execute %s: %s' % (binary, e)}
        timed_out = False
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_tree(p.pid)
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                pass
        fo.seek(0)
        fe.seek(0)
        out = fo.read().decode('utf-8', 'replace')
        err = fe.read().decode('utf-8', 'replace')
    if timed_out:
        return {'exit': None, 'json': None, 'timed_out': True, 'stderr': ''}
    try:
        j = json.loads(out)
    except ValueError:
        j = None
    return {'exit': p.returncode, 'json': j, 'timed_out': False, 'stderr': err[:400]}


def short_rule(check_id):
    """Semgrep prefixes a rule id with the dotted path of the config file. Our
    ids are 'hover.<name>' with no dot in <name>, so the LAST 'hover.' starts the
    id even when the path itself contains 'hover' (it does: SAIRN-hover)."""
    s = str(check_id or '')
    i = s.rfind('hover.')
    return s[i:] if i >= 0 else s


def interpret(res, targets):
    """PURE. (status, reasons, findings, scanned_count). The whole tool."""
    reasons = []
    if res.get('timed_out'):
        return 'INCONCLUSIVE', ['TIMEOUT: killed before it finished, so its '
                                 'silence covers nothing'], [], 0
    j = res.get('json')
    code = res.get('exit')
    if code not in (0, 1):
        why = 'UNEXPECTED EXIT %s' % code
        if j and j.get('errors'):
            why += ' (%s)' % '; '.join(str(e.get('message'))[:90] for e in j['errors'][:2])
        elif res.get('stderr'):
            why += ' (%s)' % res['stderr'][:120].replace('\n', ' ')
        return 'INCONCLUSIVE', [why], [], 0
    if not isinstance(j, dict) or 'results' not in j:
        return 'INCONCLUSIVE', ['UNPARSEABLE OUTPUT: no results key'], [], 0
    errors = j.get('errors') or []
    scanned = (j.get('paths') or {}).get('scanned') or []
    skipped = (j.get('paths') or {}).get('skipped') or []
    findings = [{'path': f.get('path'), 'line': (f.get('start') or {}).get('line'),
                 'rule': short_rule(f.get('check_id')),
                 'message': str((f.get('extra') or {}).get('message') or '')[:160]}
                for f in j['results']]
    if errors:
        reasons.append('ERRORS ARRAY NON-EMPTY (%d): %s' % (
            len(errors), '; '.join('%s: %s' % (e.get('type'), str(e.get('message'))[:70])
                                    for e in errors[:3])))
    if skipped:
        reasons.append('SKIPPED %d target(s): %s' % (
            len(skipped), ', '.join(str(s.get('path', s))[:50] for s in skipped[:3])))
    norm = lambda p: os.path.normcase(os.path.normpath(str(p)))
    got = {norm(p) for p in scanned}
    missing = [t for t in targets if norm(t) not in got]
    if missing:
        reasons.append('PARTIAL COVERAGE: %d of %d target(s) not reported '
                       'scanned (%s) -- UNKNOWN, not clean'
                       % (len(missing), len(targets), ', '.join(missing[:3])))
    if reasons:
        return 'INCONCLUSIVE', reasons, findings, len(scanned)
    return ('FINDINGS' if findings else 'CLEAN'), [], findings, len(scanned)


def canary(binary):
    """(ok, why). Positive AND negative control, run for real, every time."""
    d = tempfile.mkdtemp(prefix='h1-semgrep-canary-')
    try:
        rule = os.path.join(d, 'rule.yml')
        pos = os.path.join(d, 'pos.js')
        neg = os.path.join(d, 'neg.js')
        with open(rule, 'w', encoding='utf-8') as f:
            f.write(CANARY_RULE)
        with open(pos, 'w', encoding='utf-8') as f:
            f.write('function f(x) { return eval(x); }\n')
        with open(neg, 'w', encoding='utf-8') as f:
            f.write('function g(x) { return safe(x); }\n')
        res = run_scan(binary, rule, [pos, neg], timeout=CANARY_TIMEOUT)
        st, reasons, findings, _n = interpret(res, [pos, neg])
        hit_paths = {os.path.normcase(os.path.normpath(str(f['path']))) for f in findings}
        if st != 'FINDINGS':
            return False, 'canary run was %s %s' % (st, reasons)
        if hit_paths != {os.path.normcase(os.path.normpath(pos))}:
            return False, ('canary fired on the wrong set of files: %s '
                           '(positive control must fire, negative must not)' % sorted(hit_paths))
        return True, 'positive control fired, negative control silent'
    finally:
        shutil.rmtree(d, ignore_errors=True)


_CANARY_OK = set()


def scan(paths, rules=RULES_PATH, runner=None, binary_finder=None):
    """{'status', 'reasons', 'findings', 'scanned', 'binary'}; status is one of
    CLEAN | FINDINGS | INCONCLUSIVE | COULD_NOT_RUN. `runner` / `binary_finder`
    are injectable so every arm of the contract is driven by a fixture."""
    binary, why = (binary_finder or find_binary)()
    if not binary:
        return {'status': 'COULD_NOT_RUN', 'reasons': [why], 'findings': [],
                'scanned': 0, 'binary': None}
    if runner is not None:
        ok, cwhy = True, 'injected runner'
    elif binary in _CANARY_OK:
        ok, cwhy = True, 'canary passed earlier in this process'
    else:
        ok, cwhy = canary(binary)
        if ok:
            _CANARY_OK.add(binary)   # only a PASS is cached; a failure is re-tried
    if not ok:
        return {'status': 'COULD_NOT_RUN', 'reasons': ['CANARY FAILED: ' + cwhy],
                'findings': [], 'scanned': 0, 'binary': binary}
    if not os.path.isfile(rules):
        return {'status': 'COULD_NOT_RUN', 'reasons': ['rule pack missing: %s' % rules],
                'findings': [], 'scanned': 0, 'binary': binary}
    res = (runner or run_scan)(binary, rules, list(paths))
    st, reasons, findings, n = interpret(res, list(paths))
    return {'status': st, 'reasons': reasons, 'findings': findings, 'scanned': n,
            'binary': binary}


def run_semgrep(paths):
    """Adapter with hover_static_input.ANALYSERS' contract:
    (exit, stdout, stderr, timed_out, seen). The error channel is rendered so
    that hover_static_input.classify -- not this file -- turns a non-empty
    errors array into INCONCLUSIVE, and an unusable engine into exit 2."""
    r = scan(paths)
    if r['status'] == 'COULD_NOT_RUN':
        return 2, '', 'semgrep could not run: %s' % '; '.join(r['reasons']), False, 0
    out = '\n'.join('%s:%s %s %s' % (f['path'], f['line'], f['rule'], f['message'])
                    for f in r['findings'])
    err = ''
    if r['status'] == 'INCONCLUSIVE':
        err = 'semgrep INCONCLUSIVE "errors": [{ %s' % '; '.join(r['reasons'])
    return (1 if r['findings'] else 0), out, err, False, r['scanned']


def main(argv):
    if '--selftest' in argv:
        return selftest(full='--full' in argv)
    if '--canary' in argv:
        b, why = find_binary()
        if not b:
            print('COULD NOT RUN: %s' % why)
            return EXIT_INCONCLUSIVE
        ok, cwhy = canary(b)
        print('CANARY %s: %s (%s)' % ('OK' if ok else 'FAILED', cwhy, b))
        return EXIT_CLEAN if ok else EXIT_INCONCLUSIVE
    if '--scan' in argv:
        paths = [a for a in argv[argv.index('--scan') + 1:] if not a.startswith('--')]
        if not paths:
            print('COULD NOT RUN: --scan needs at least one file')
            return EXIT_INCONCLUSIVE
        r = scan(paths)
        print('SEMGREP SIGNAL: %s  (scanned %d of %d target(s); binary %s)'
              % (r['status'], r['scanned'], len(paths), r['binary']))
        for why in r['reasons']:
            print('  REASON: %s' % why)
        for f in r['findings']:
            print('  %s:%s  %s  -- %s' % (f['path'], f['line'], f['rule'], f['message']))
        print('INCONCLUSIVE IS NOT CLEAN; a finding is a prompt to look, not a verdict.')
        return {'CLEAN': EXIT_CLEAN, 'FINDINGS': EXIT_FINDINGS}.get(r['status'], EXIT_INCONCLUSIVE)
    print('usage: --scan FILE... | --canary | --selftest')
    return EXIT_INCONCLUSIVE


def selftest(full=False):
    ok_n, bad_n = [0], [0]

    def ck(name, cond):
        if cond:
            ok_n[0] += 1
            print('  ok   %s' % name)
        else:
            bad_n[0] += 1
            print('  FAIL %s' % name)

    def res(results=(), errors=(), scanned=('a.js',), skipped=(), exit_code=0, timed_out=False):
        return {'exit': exit_code, 'timed_out': timed_out, 'stderr': '',
                'json': {'results': list(results), 'errors': list(errors),
                         'paths': {'scanned': list(scanned), 'skipped': list(skipped)}}}
    hit = {'path': 'a.js', 'check_id': 'C.x.SAIRN-hover.y.hover.rule-a', 'start': {'line': 3},
           'extra': {'message': 'm'}}
    st = lambda r, t=('a.js',): interpret(r, list(t))[0]

    ck('S1 a complete run with no findings is CLEAN', st(res()) == 'CLEAN')
    ck('S2 a complete run with a finding is FINDINGS, and the rule id is normalised '
       'past the config path (which itself contains "hover")',
       st(res([hit])) == 'FINDINGS'
       and interpret(res([hit]), ['a.js'])[2][0]['rule'] == 'hover.rule-a')
    ck('S3 THE HEADLINE CASE: exit 0 with a NON-EMPTY errors array is INCONCLUSIVE, not CLEAN',
       st(res(errors=[{'type': 'PartialParsing', 'message': 'x'}])) == 'INCONCLUSIVE')
    ck('S4 findings AND errors is INCONCLUSIVE, not FINDINGS: a run that found things and '
       'could not finish has an unknown remainder',
       st(res([hit], errors=[{'type': 'T', 'message': 'm'}])) == 'INCONCLUSIVE')
    ck('S5 exit 7 (an invalid rule file) is INCONCLUSIVE -- the defect this tool met on its '
       'own first rule pack, which printed ZERO findings for 24 files',
       st(res(exit_code=7, errors=[{'message': 'Invalid YAML'}])) == 'INCONCLUSIVE')
    ck('S6 a target missing from paths.scanned is INCONCLUSIVE and NAMED',
       interpret(res(scanned=('a.js',)), ['a.js', 'b.js'])[0] == 'INCONCLUSIVE'
       and 'b.js' in interpret(res(scanned=('a.js',)), ['a.js', 'b.js'])[1][0])
    ck('S7 a skipped path, a timeout and unparseable output are each INCONCLUSIVE',
       st(res(skipped=[{'path': 'a.js'}])) == 'INCONCLUSIVE'
       and st(res(timed_out=True, exit_code=None)) == 'INCONCLUSIVE'
       and st({'exit': 0, 'json': None, 'timed_out': False, 'stderr': ''}) == 'INCONCLUSIVE')

    missing = scan(['x.js'], binary_finder=lambda: (None, 'absent'))
    sys.path.insert(0, HERE)
    import hover_static_input as SI
    saved = scan
    try:
        globals()['scan'] = lambda paths, **k: saved(paths, binary_finder=lambda: (None, 'absent'))
        code, out, err, timed, seen = run_semgrep(['x.js'])
    finally:
        globals()['scan'] = saved
    verdict = SI.classify(code, out, err, timed, ['x.js'], seen)[0]
    ck('S8 FAIL-CLOSED when no binary exists: COULD_NOT_RUN, and through hover_static_input.classify '
       'the adapter reads INCONCLUSIVE -- never CLEAN',
       missing['status'] == 'COULD_NOT_RUN' and verdict == 'INCONCLUSIVE')
    ck('S9a scan_cwd is the closest common ancestor of the targets (the working directory the '
       'engine is only fast in), and None for no targets',
       scan_cwd([os.path.join(os.sep, 'a', 'b', 'x.js'), os.path.join(os.sep, 'a', 'b', 'c', 'y.js')])
       == os.path.dirname(os.path.abspath(os.path.join(os.sep, 'a', 'b', 'x.js')))
       and scan_cwd([]) is None)
    ck('S9 short_rule leaves a bare id alone and finds the id inside a long path',
       short_rule('hover.a-b') == 'hover.a-b' and short_rule('C.U.SAIRN-hover.w.hover.a-b') == 'hover.a-b')

    # S9b: a fake engine that spawns a long-lived GRANDCHILD and hangs. The scan must come
    # back flagged timed_out within a few seconds, not after the grandchild ends.
    import time
    fake = [sys.executable, '-c', 'import subprocess,sys,time;'
            'subprocess.Popen([sys.executable,"-c","import time;time.sleep(90)"]);time.sleep(90)']
    t0 = time.time()
    r_to = run_scan(sys.executable, 'x', [], timeout=3, argv=fake)
    took = time.time() - t0
    ck('S9b THE TIMEOUT IS REAL: a hung engine with a long-lived grandchild returns timed_out '
       'in %.0fs (limit 3s), not after the grandchild ends, and reads INCONCLUSIVE' % took,
       r_to['timed_out'] is True and took < 25 and interpret(r_to, ['a.js'])[0] == 'INCONCLUSIVE')

    binary, why = find_binary()
    if not binary:
        ck('S10 a real binary is available to drive the real arms (%s)' % why, False)
    else:
        ok, cwhy = canary(binary)
        if ok:
            _CANARY_OK.add(binary)
        ck('S10 REAL CANARY: the positive control fires and the negative control stays silent (%s)' % cwhy, ok)
        d = tempfile.mkdtemp(prefix='h1-sg-st-')
        try:
            bad_rules = os.path.join(d, 'bad.yml')
            with open(bad_rules, 'w', encoding='utf-8') as f:
                f.write('rules:\n  - id: bad\n    languages: [javascript]\n    message: x\n'
                        '    severity: WARNING\n    pattern: fetch($U, {a: 1})\n    broken: [unclosed\n')
            tgt = os.path.join(d, 'ok.js')
            with open(tgt, 'w', encoding='utf-8') as f:
                f.write('function f() { return 1; }\n')
            r_bad = scan([tgt], rules=bad_rules)
            ck('S11 SABOTAGE CONTROL, REAL ENGINE: an invalid rule file makes the scan INCONCLUSIVE '
               '(it exits non-zero with errors), not a clean scan of one file',
               r_bad['status'] == 'INCONCLUSIVE')
            r_pack = scan([tgt])
            ck('S12 the shipped rule pack LOADS and a file with nothing risky is CLEAN '
               '(%s)' % r_pack['status'], r_pack['status'] == 'CLEAN' and r_pack['scanned'] == 1)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        if full:
            sys.path.insert(0, HERE)
            import hover_planted_bug_recall as P
            d2 = tempfile.mkdtemp(prefix='h1-sg-seeds-')
            try:
                paths = []
                for sid, _c, _t, _k, code in P.SEEDS:
                    p = os.path.join(d2, sid + '.js')
                    with open(p, 'w', encoding='utf-8') as f:
                        f.write('async function __seed() {\n' + code + '\n}\n')
                    paths.append(p)
                r = scan(paths)
                got = {}
                for f in r['findings']:
                    got.setdefault(os.path.basename(f['path'])[:-3], set()).add(f['rule'])
                kinds = {s[0]: s[3] for s in P.SEEDS}
                blind = sorted(i for i, k in kinds.items() if k != 'clean' and not got.get(i))
                fps = sorted(i for i, k in kinds.items() if k == 'clean' and got.get(i))
                ck('S13 (--full) the rule pack scanned all 24 witnessed seeds completely (%s)' % r['status'],
                   r['status'] in ('FINDINGS', 'CLEAN') and r['scanned'] == len(P.SEEDS))
                if blind != KNOWN_BLIND_SEEDS or fps:
                    print('MEASURED blind=%s clean-twins-flagged=%s hits=%s'
                          % (blind, fps, json.dumps({k: sorted(v) for k, v in got.items()}, sort_keys=True)))
                ck('S14 (--full) REGRESSION LOCK, measured on the witnessed set: the rule pack is silent on '
                   'EXACTLY %s of the 18 planted bugs (its blind spots, named) and flags NONE of the 6 clean '
                   'twins. Written AFTER the rules saw the seeds, so this locks behaviour and measures nothing '
                   'about recall in the wild.' % KNOWN_BLIND_SEEDS, blind == KNOWN_BLIND_SEEDS and not fps)
            finally:
                shutil.rmtree(d2, ignore_errors=True)
    print('%d ok, %d failed' % (ok_n[0], bad_n[0]))
    return EXIT_CLEAN if not bad_n[0] else EXIT_FINDINGS


# The seeds the rule pack is SILENT on, as measured (b74): revocation-clobber hard2, whose id-only
# write goes through a helper the pattern cannot see. A blind spot named is a blind spot a reader can
# discount; an unnamed one reads as coverage.
KNOWN_BLIND_SEEDS = ['rc-3']


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
