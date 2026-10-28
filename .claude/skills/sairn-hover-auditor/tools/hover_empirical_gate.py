#!/usr/bin/env python
"""hover_empirical_gate.py -- REFUTE-OR-PROMOTE, Tier 1 (b91). H1's own independent
implementation; it shares no code with H2's.

THE MANDATE. For a Tier 1 finding this role is the CRITIC and its job is to KILL the
finding, not to evaluate or improve it. A finding that survives is PROMOTED, and the only
thing that promotes it is a test result:

  python hover_empirical_gate.py --run  --finding-id F --tier 1 --category C --commit REF \
         --test-cmd "python <script> [args]"
  python hover_empirical_gate.py --cite --finding-id F --tier 1 --category legal-compliance \
         --commit REF --source <file-or-https-url> --quote "<verbatim text>"
  python hover_empirical_gate.py --kill-report
  python hover_empirical_gate.py --selftest

THE TEST'S MEANING. The test is written to assert the finding's claim. Exit 0 = the claim
held = the kill attempt FAILED = the finding SURVIVES ('pass', promoted). Exit 1 = the claim
did not hold = the finding is KILLED ('fail', not promoted). Anything else, a timeout, a
refused command, an unreachable timestamp authority = COULD NOT RUN, which is a third state:
it is never folded into either, and nothing is promoted on it. Reviewer or critic agreement
is not an input to this tool at all: it has no flag that takes an opinion.

WHAT A PROMOTION WRITES, in this order, and it fails closed at each step:
  1. the record {finding_id, tier, test_command_hash, result, commit_sha, timestamp}, canonical
     JSON, sha256'd;
  2. an RFC 3161 token over that sha256 from freetsa.org via hover_timestamp.py (no substitute
     authority: unreachable = no promotion);
  3. an entry in this role's hash-chained log, detection_method=empirical-gate;
  4. one row in kill_attempts.jsonl.
Every attempt, survived or killed or could-not-run, gets steps 3 and 4 (only a survivor gets
step 2). --kill-report reads step 4 by finding category, for the recurring-bug-classes feed.

SCOPE OF WHAT IT WILL EXECUTE. NO BUILDER EXECUTION: the test script must live inside this
role's own skill directory or its audit-log directory, so a build agent's tool, test or script
cannot be named as the test. The script runs under the interpreter in isolated mode (-I) with
the repo root as the working directory, so it reads the repo as data and imports nothing from
it implicitly. That is a path rule and an isolation rule. It is NOT a proof that the script
never shells out to something in the repo; a test that does is a defect in the test, and the
script's own sha256 is bound into test_command_hash so a changed script is a different test.

CONTEXT ASYMMETRY (the diff and the test evidence only, never the generator's own writeup) is
a PROCEDURE for whoever runs this. The tool takes no prose about the finding, so it cannot be
fed a writeup, but it cannot stop a person from having read one, and it does not claim to.

LEGAL / COMPLIANCE. A claim about a statute, a contract or a regulation has no executable
test; --cite stands in for it: the quoted text must appear VERBATIM (whitespace collapsed,
case kept) in the named primary source, a local file or an https URL. A paraphrase fails.
"""
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
EXIT_OK = 0
EXIT_KILLED = 1
EXIT_COULD_NOT_RUN = 2
RECORD_FIELDS = ('finding_id', 'tier', 'test_command_hash', 'result', 'commit_sha', 'timestamp')
TEST_TIMEOUT = 120
MIN_QUOTE = 20
MAX_SOURCE_BYTES = 5 * 1024 * 1024
CATEGORY_RE = re.compile(r'^[a-z0-9][a-z0-9-]{2,39}$')
FINDING_RE = re.compile(r'^[A-Za-z0-9._:#-]{1,60}$')


def _sys_path():
    if HERE not in sys.path:
        sys.path.insert(0, HERE)


def _hl():
    _sys_path()
    import hover_log as HL
    return HL


def _ts():
    _sys_path()
    import hover_timestamp as TS
    return TS


def _log_dir():
    return os.path.dirname(os.path.abspath(_hl().LOG_PATH))


def kill_path():
    return os.path.join(_log_dir(), 'kill_attempts.jsonl')


def _repo():
    r = subprocess.run(['git', '-C', HERE, 'rev-parse', '--show-toplevel'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def now_utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def canonical_record(rec):
    return json.dumps({k: rec[k] for k in RECORD_FIELDS}, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True)


def record_hash(rec):
    return sha256_bytes(canonical_record(rec).encode('utf-8'))


def allowed_roots():
    return [os.path.normcase(os.path.realpath(SKILL_DIR)),
            os.path.normcase(os.path.realpath(_log_dir()))]


def _inside(path, roots):
    p = os.path.normcase(os.path.realpath(path))
    return any(p == r or p.startswith(r + os.sep) for r in roots)


def resolve_test(test_cmd, repo):
    """(argv, script_path, script_sha, error). Refuses anything but 'python SCRIPT [args]' whose
    SCRIPT is a file inside this role's own directories. Pure apart from reading the script."""
    try:
        # Windows paths: a backslash is a path separator here, not an escape, and posix shlex eats it.
        argv = shlex.split(test_cmd.replace(chr(92), '/'), posix=True)
    except ValueError as e:
        return None, None, None, 'the test command does not parse (%s)' % e
    if len(argv) < 2 or os.path.basename(argv[0]).lower() not in ('python', 'python.exe', 'python3'):
        return None, None, None, 'the test command must be: python SCRIPT [args]'
    if argv[1].startswith('-'):
        return None, None, None, 'an interpreter flag (%s) where the script path belongs: -c and -m can run anything' % argv[1]
    script = argv[1] if os.path.isabs(argv[1]) else os.path.join(repo or os.getcwd(), argv[1])
    if not os.path.isfile(script):
        return None, None, None, 'the test script does not exist: %s' % argv[1]
    if not _inside(script, allowed_roots()):
        return None, None, None, ('NO BUILDER EXECUTION: %s is outside this role\'s own directories '
                                  '(%s)' % (argv[1], ', '.join(allowed_roots())))
    with open(script, 'rb') as f:
        sha = sha256_bytes(f.read())
    return argv, script, sha, None


def test_command_hash(argv, script_sha):
    return sha256_bytes(json.dumps([argv, script_sha], sort_keys=True).encode('utf-8'))


def run_test(argv, repo):
    """(exit_code or None, stdout_sha256, note). None = could not run (timeout, spawn failure)."""
    try:
        r = subprocess.run([sys.executable, '-I'] + argv[1:], cwd=repo or os.getcwd(), capture_output=True,
                           timeout=TEST_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, '', 'timed out after %ds' % TEST_TIMEOUT
    except Exception as e:  # noqa: BLE001
        return None, '', '%s: %s' % (type(e).__name__, e)
    return r.returncode, sha256_bytes(r.stdout or b''), ''


def resolve_commit(ref, repo):
    if not ref or not repo:
        return None
    r = subprocess.run(['git', '-C', repo, 'rev-parse', '--verify', '--quiet', ref + '^{commit}'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = r.stdout.strip()
    return out if r.returncode == 0 and re.fullmatch(r'[0-9a-f]{40}', out) else None


def collapse(s):
    return ' '.join(s.split())


def cite_check(source, quote):
    """(result 'pass'|'fail'|None, source_sha256, note). Verbatim, whitespace collapsed, case kept."""
    try:
        if source.lower().startswith('https://'):
            import urllib.request
            with urllib.request.urlopen(urllib.request.Request(source), timeout=20) as r:
                data = r.read(MAX_SOURCE_BYTES + 1)
        elif source.lower().startswith('http://'):
            return None, '', 'http:// is refused: a primary source is read over https or from a local file'
        else:
            with open(source, 'rb') as f:
                data = f.read(MAX_SOURCE_BYTES + 1)
    except Exception as e:  # noqa: BLE001
        return None, '', 'could not read the source (%s: %s)' % (type(e).__name__, e)
    if len(data) > MAX_SOURCE_BYTES:
        return None, '', 'the source is over %d bytes; a truncated read is not a read' % MAX_SOURCE_BYTES
    text = data.decode('utf-8', errors='replace')
    return ('pass' if collapse(quote) in collapse(text) else 'fail'), sha256_bytes(data), ''


def _append_jsonl_chain(path, row):
    prev = '0' * 64
    if os.path.isfile(path):
        last = None
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    last = line
        if last:
            prev = json.loads(last).get('row_hash', prev)
    row = dict(row, prev_row_hash=prev)
    row['row_hash'] = sha256_bytes((prev + json.dumps(row, sort_keys=True)).encode('utf-8'))
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, sort_keys=True) + '\n')
    return row


def write_log(summary, target, ref):
    """Append one chain entry, detection_method=empirical-gate. Returns (rc, output)."""
    import contextlib
    import io
    HL = _hl()
    spath = os.path.join(_log_dir(), '.empirical-gate-summary.tmp')
    with open(spath, 'w', encoding='utf-8', newline='') as f:
        f.write(summary)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = HL.cmd_add(['--add', '--type', 'note', '--target', target, '--ref', ref,
                             '--summary-file', spath, '--detection-method', 'empirical-gate'])
    finally:
        try:
            os.remove(spath)
        except OSError:
            pass
    return rc, buf.getvalue()


def gate(mode, finding_id, tier, category, commit_ref, target='self', test_cmd=None, source=None,
         quote=None, ts_fn=None, out=print):
    """One kill attempt end to end. Returns the process exit code. ts_fn is injectable so the
    selftest can drive the real control flow without the network."""
    ts_mod = None
    if not FINDING_RE.match(finding_id or ''):
        out('REFUSED: --finding-id must match %s' % FINDING_RE.pattern)
        return EXIT_COULD_NOT_RUN
    if not CATEGORY_RE.match(category or ''):
        out('REFUSED: --category must be a lowercase slug (%s)' % CATEGORY_RE.pattern)
        return EXIT_COULD_NOT_RUN
    if tier != 1:
        out('REFUSED: this gate is Tier 1 only (got tier %r); a lower tier is out of its scope, '
            'not passed by it' % (tier,))
        return EXIT_COULD_NOT_RUN
    repo = _repo()
    sha = resolve_commit(commit_ref, repo)
    if not sha:
        out('REFUSED: --commit %r is not a commit in this repo; the record must name what was tested' % commit_ref)
        return EXIT_COULD_NOT_RUN

    evidence = {'mode': mode}
    if mode == 'run':
        argv, script, script_sha, err = resolve_test(test_cmd or '', repo)
        if err:
            out('REFUSED: %s. Nothing was run and nothing was logged.' % err)
            return EXIT_COULD_NOT_RUN
        tch = test_command_hash(argv, script_sha)
        code, stdout_sha, note = run_test(argv, repo)
        evidence.update(script_sha256=script_sha, exit_code=code, stdout_sha256=stdout_sha)
        result = 'pass' if code == 0 else ('fail' if code == 1 else None)
        if result is None:
            evidence['note'] = note or 'exit code %s is neither pass (0) nor fail (1)' % code
    elif mode == 'cite':
        if not source or not quote or len(collapse(quote)) < MIN_QUOTE:
            out('REFUSED: --cite needs --source and a --quote of at least %d characters' % MIN_QUOTE)
            return EXIT_COULD_NOT_RUN
        tch = sha256_bytes(json.dumps(['cite', source, collapse(quote)], sort_keys=True).encode('utf-8'))
        result, src_sha, note = cite_check(source, quote)
        evidence.update(source=source, source_sha256=src_sha)
        if result is None:
            evidence['note'] = note
    else:
        out('REFUSED: unknown mode')
        return EXIT_COULD_NOT_RUN

    rec = {'finding_id': finding_id, 'tier': tier, 'test_command_hash': tch,
           'result': result if result else 'could-not-run', 'commit_sha': sha, 'timestamp': now_utc()}
    rhash = record_hash(rec)
    outcome = {'pass': 'survived', 'fail': 'killed', None: 'could-not-run'}[result]
    token = ''

    if outcome == 'survived':
        try:
            ts_mod = _ts()
            ts_call = ts_fn or ts_mod.request_token
            if ts_fn is None:
                reachable, rerr = ts_mod.check_reachable()
                if not reachable:
                    raise RuntimeError('freetsa.org is unreachable (%s)' % rerr)
            seq_label = 'empirical-gate:%s' % finding_id
            ok, tsr, terr = ts_call(seq_label, rhash, rec['timestamp'])
            if not ok:
                raise RuntimeError(terr)
            stem = 'empirical-gate-%s-%s' % (re.sub(r'[^A-Za-z0-9._-]', '_', finding_id), rhash[:12])
            tsr_path = os.path.join(_log_dir(), stem + '.tsr')
            msg_path = os.path.join(_log_dir(), stem + '.msg')
            with open(tsr_path, 'wb') as f:
                f.write(tsr)
            with open(msg_path, 'wb') as f:
                f.write(ts_mod.canonical_message(seq_label, rhash, rec['timestamp']))
            token = os.path.basename(tsr_path)
        except Exception as e:  # noqa: BLE001
            evidence['note'] = 'NOT PROMOTED, the timestamp authority could not be used: %s' % e
            outcome = 'could-not-run'
            rec['result'] = 'could-not-run'
            rhash = record_hash(rec)

    summary = ('EMPIRICAL GATE %s. finding %s, tier %s, category %s, outcome %s. record_sha256 %s. '
               'record %s. evidence %s. rfc3161 token file %s.'
               % (outcome.upper(), finding_id, tier, category, outcome, rhash, canonical_record(rec),
                  json.dumps(evidence, sort_keys=True), token or 'none (only a survivor is timestamped)'))
    rc, logout = write_log(summary, target, 'empirical-gate %s' % finding_id)
    logged = (rc == 0)
    _append_jsonl_chain(kill_path(), {'ts': rec['timestamp'], 'finding_id': finding_id, 'category': category,
                                      'tier': tier, 'outcome': outcome, 'record_sha256': rhash,
                                      'commit_sha': sha, 'logged_to_chain': logged})
    out('%s: %s (record_sha256 %s)%s' % (outcome.upper(), finding_id, rhash[:16],
                                         '' if logged else ' -- THE CHAIN APPEND FAILED: ' + logout.strip()[:200]))
    if outcome == 'survived' and logged:
        return EXIT_OK
    if outcome == 'killed':
        return EXIT_KILLED
    return EXIT_COULD_NOT_RUN


def kill_report(out=print):
    p = kill_path()
    if not os.path.isfile(p):
        out('KILL REPORT: no attempts recorded yet (%s). That is a measured zero, not a failure to look.' % p)
        return EXIT_OK
    by = {}
    for line in open(p, encoding='utf-8'):
        if line.strip():
            r = json.loads(line)
            by.setdefault(r['category'], {'survived': 0, 'killed': 0, 'could-not-run': 0})[r['outcome']] += 1
    out('KILL-MANDATE ATTEMPTS BY FINDING CATEGORY (survived = the disproof failed and the finding was promoted)')
    for cat in sorted(by):
        c = by[cat]
        out('  %-28s attempts %-3d survived %-3d killed %-3d could-not-run %d'
            % (cat, sum(c.values()), c['survived'], c['killed'], c['could-not-run']))
    return EXIT_OK


# ── SELFTEST ───────────────────────────────────────────────────────────────
def selftest():
    import contextlib
    import io
    import tempfile
    ok = [0]
    bad = [0]

    def ck(name, cond):
        if cond:
            ok[0] += 1
            print('  ok   ' + name)
        else:
            bad[0] += 1
            print('  FAIL ' + name)

    HL = _hl()
    real_log = HL.LOG_PATH
    work = tempfile.mkdtemp(prefix='hover-gate-')
    # The isolated log dir is also an allowed root, so fixtures can live in it.
    HL.LOG_PATH = os.path.join(work, 'gate-test-log.jsonl')
    repo = _repo()
    head = subprocess.run(['git', '-C', repo, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    calls = []

    def stub_ts(seq, h, d):
        calls.append((seq, h, d))
        return True, b'TSR-STUB', None

    def stub_ts_down(seq, h, d):
        calls.append(('down', h, d))
        return False, b'TSR-STUB', 'stubbed: authority down'   # a token IS returned: only the ok flag says it is invalid

    def script(name, body):
        p = os.path.join(work, name)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(body)
        return p

    def attempt(**kw):
        buf = io.StringIO()
        kw.setdefault('out', lambda s: buf.write(s + '\n'))
        rc = gate(**kw)
        return rc, buf.getvalue()

    def rows():
        return [json.loads(x) for x in open(HL.LOG_PATH, encoding='utf-8') if x.strip()] if os.path.isfile(HL.LOG_PATH) else []

    try:
        passer = script('t_pass.py', 'import sys\nsys.exit(0)\n')
        failer = script('t_fail.py', 'import sys\nsys.exit(1)\n')
        weird = script('t_weird.py', 'import sys\nsys.exit(3)\n')
        sentinel = os.path.join(work, 'SENTINEL')
        # lives OUTSIDE every allowed root, in a directory of its own
        outside_dir = tempfile.mkdtemp(prefix='hover-gate-outside-')
        outsider = os.path.join(outside_dir, 'builder_test.py')
        with open(outsider, 'w', encoding='utf-8') as f:
            f.write('open(%r, "w").write("ran")\n' % sentinel)

        # G1 survivor
        calls.clear()
        rc, o = attempt(mode='run', finding_id='F-PASS', tier=1, category='data-integrity', commit_ref='HEAD',
                        test_cmd='python ' + passer, ts_fn=stub_ts)
        rs = rows()
        ck('G1 a passing test PROMOTES: exit 0, one timestamp request, one chain entry with detection_method=empirical-gate',
           rc == EXIT_OK and len(calls) == 1 and len(rs) == 1 and rs[0].get('detection_method') == 'empirical-gate')
        rec_json = re.search(r'record (\{.*?\})\. evidence', rs[0]['summary'])
        rec = json.loads(rec_json.group(1)) if rec_json else {}
        ck('G1b the record has EXACTLY the six fields, commit_sha is the full 40-hex HEAD, tier is 1',
           sorted(rec) == sorted(RECORD_FIELDS) and rec.get('commit_sha') == head and rec.get('tier') == 1
           and rec.get('result') == 'pass')
        ck('G1c the sha256 that went to the timestamp authority is the sha256 of that canonical record',
           calls and calls[0][1] == record_hash(rec) and ('record_sha256 ' + record_hash(rec)) in rs[0]['summary'])
        ck('G1d the token and its message file were written beside the log',
           any(n.endswith('.tsr') for n in os.listdir(work)) and any(n.endswith('.msg') for n in os.listdir(work)))
        # G2 killed
        calls.clear()
        rc, o = attempt(mode='run', finding_id='F-FAIL', tier=1, category='access-control', commit_ref='HEAD',
                        test_cmd='python ' + failer, ts_fn=stub_ts)
        ck('G2 a failing test KILLS: exit 1, NO timestamp request, logged as killed',
           rc == EXIT_KILLED and calls == [] and 'KILLED' in rows()[-1]['summary'])
        # G3 weird exit
        calls.clear()
        rc, o = attempt(mode='run', finding_id='F-WEIRD', tier=1, category='access-control', commit_ref='HEAD',
                        test_cmd='python ' + weird, ts_fn=stub_ts)
        ck('G3 an exit code that is neither 0 nor 1 is COULD NOT RUN (exit 2), not a pass and not a kill, nothing timestamped',
           rc == EXIT_COULD_NOT_RUN and calls == [] and 'COULD-NOT-RUN' in rows()[-1]['summary'])
        # G4 builder execution
        n_before = len(rows())
        rc, o = attempt(mode='run', finding_id='F-OUT', tier=1, category='code-integrity', commit_ref='HEAD',
                        test_cmd='python ' + outsider, ts_fn=stub_ts)
        ck('G4 NO BUILDER EXECUTION: a script outside this role\'s directories is refused, never run (sentinel absent), nothing logged',
           rc == EXIT_COULD_NOT_RUN and not os.path.exists(sentinel) and len(rows()) == n_before)
        rc, o = attempt(mode='run', finding_id='F-DASHC', tier=1, category='code-integrity', commit_ref='HEAD',
                        test_cmd='python -c "open(%r,\'w\')"' % sentinel, ts_fn=stub_ts)
        ck('G4b python -c is refused (an interpreter flag where the script belongs)',
           rc == EXIT_COULD_NOT_RUN and not os.path.exists(sentinel))
        rc, o = attempt(mode='run', finding_id='F-PS', tier=1, category='code-integrity', commit_ref='HEAD',
                        test_cmd='bash ' + passer, ts_fn=stub_ts)
        ck('G4c a command that is not python SCRIPT is refused', rc == EXIT_COULD_NOT_RUN)
        # G5 tier
        rc, o = attempt(mode='run', finding_id='F-T2', tier=2, category='data-integrity', commit_ref='HEAD',
                        test_cmd='python ' + passer, ts_fn=stub_ts)
        ck('G5 a Tier 2 finding is refused as out of scope (not passed)', rc == EXIT_COULD_NOT_RUN and 'Tier 1 only' in o)
        # G6 unknown commit
        rc, o = attempt(mode='run', finding_id='F-C', tier=1, category='data-integrity', commit_ref='deadbeefdeadbeef',
                        test_cmd='python ' + passer, ts_fn=stub_ts)
        ck('G6 a commit that does not exist is refused', rc == EXIT_COULD_NOT_RUN)
        # G7 TSA down
        calls.clear()
        n_before = len(rows())
        rc, o = attempt(mode='run', finding_id='F-TSA', tier=1, category='data-integrity', commit_ref='HEAD',
                        test_cmd='python ' + passer, ts_fn=stub_ts_down)
        ck('G7 FAIL CLOSED: a passing test whose timestamp cannot be obtained is NOT promoted (exit 2) and says so in the chain',
           rc == EXIT_COULD_NOT_RUN and len(rows()) == n_before + 1 and 'NOT PROMOTED' in rows()[-1]['summary']
           and 'COULD-NOT-RUN' in rows()[-1]['summary'])
        # G8 citation
        src = script('primary.txt', 'The   licensee shall  maintain\nrecords for seven years after termination of the engagement.\n')
        calls.clear()
        rc, o = attempt(mode='cite', finding_id='F-LAW1', tier=1, category='legal-compliance', commit_ref='HEAD',
                        source=src, quote='licensee shall maintain records for seven years', ts_fn=stub_ts)
        ck('G8 a verbatim quote (whitespace-collapsed) in the primary source PROMOTES', rc == EXIT_OK and len(calls) == 1)
        calls.clear()
        rc, o = attempt(mode='cite', finding_id='F-LAW2', tier=1, category='legal-compliance', commit_ref='HEAD',
                        source=src, quote='licensee must retain records for seven years total', ts_fn=stub_ts)
        ck('G8b a PARAPHRASE is killed, not promoted', rc == EXIT_KILLED and calls == [])
        rc, o = attempt(mode='cite', finding_id='F-LAW3', tier=1, category='legal-compliance', commit_ref='HEAD',
                        source=src, quote='seven years', ts_fn=stub_ts)
        ck('G8c a quote under %d characters is refused (a short string matches anything)' % MIN_QUOTE, rc == EXIT_COULD_NOT_RUN)
        rc, o = attempt(mode='cite', finding_id='F-LAW4', tier=1, category='legal-compliance', commit_ref='HEAD',
                        source='http://example.com/x', quote='licensee shall maintain records for seven years', ts_fn=stub_ts)
        ck('G8d an http:// source is not a readable primary source (could not run)', rc == EXIT_COULD_NOT_RUN)
        # G9 chain + kill report
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            vrc = HL.cmd_verify([])
        ck('G9 the hash chain written by the gate VERIFIES', vrc == 0)
        kp = kill_path()
        krows = [json.loads(x) for x in open(kp, encoding='utf-8') if x.strip()]
        ck('G9b every attempt that got past argument validation has a kill_attempts row, outcomes survived / killed / could-not-run all present',
           {r['outcome'] for r in krows} == {'survived', 'killed', 'could-not-run'})
        # G10 kill report
        lines = []
        kill_report(out=lines.append)
        txt = '\n'.join(lines)
        ck('G10 --kill-report groups by category with all three counts (legal-compliance: 3 attempts = 1 survived, 1 killed, 1 could-not-run from the http source)',
           re.search(r'legal-compliance\s+attempts 3\s+survived 1\s+killed 1\s+could-not-run 1', txt) is not None)
        # G11 row chain
        ok_chain = True
        prev = '0' * 64
        for r in krows:
            body = {k: v for k, v in r.items() if k != 'row_hash'}
            if r['prev_row_hash'] != prev or r['row_hash'] != sha256_bytes((prev + json.dumps(body, sort_keys=True)).encode('utf-8')):
                ok_chain = False
            prev = r['row_hash']
        ck('G11 kill_attempts.jsonl is itself hash-chained and the chain checks out', ok_chain)
        # G12 binds the script content
        h1 = test_command_hash(['python', passer], sha256_bytes(b'a'))
        h2 = test_command_hash(['python', passer], sha256_bytes(b'b'))
        ck('G12 test_command_hash changes when the script\'s content changes', h1 != h2)
    finally:
        HL.LOG_PATH = real_log
    print('%d ok, %d failed' % (ok[0], bad[0]))
    return EXIT_OK if not bad[0] else EXIT_KILLED


def main(argv):
    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default

    if '--selftest' in argv:
        return selftest()
    if '--kill-report' in argv:
        return kill_report()
    mode = 'run' if '--run' in argv else ('cite' if '--cite' in argv else None)
    if not mode:
        print('usage: --run | --cite | --kill-report | --selftest   (see the header)')
        return EXIT_COULD_NOT_RUN
    try:
        tier = int(opt('--tier', '0'))
    except ValueError:
        tier = 0
    return gate(mode, opt('--finding-id', ''), tier, opt('--category', ''), opt('--commit', ''),
                target=opt('--target', 'self'), test_cmd=opt('--test-cmd'), source=opt('--source'),
                quote=opt('--quote'))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
