# OWNER: fourth
"""push_timeout_guard.py -- a git push is never run under a timeout. Checked, not remembered.

    python tools/push_timeout_guard.py --pre-push   # called by .githooks/pre-push, FIRST
    python tools/push_timeout_guard.py --scan       # every tracked tool, statically
    python tools/push_timeout_guard.py --fixtures   # the criteria against synthetic cases

Exit: 0 clean - 1 REFUSED / findings - 2 COULD NOT RUN (a fixture misclassified)

── WHY (fourth b59, 2026-10-27) ─────────────────────────────────────────────
The push gate runs GUARD_TESTS that write MUTANTS into real tracked files and
put them back in a `finally` -- api/b17-trust-lock-hard.test.js rewrites
api/_lib/law-roles.js four times. A kill skips `finally`. `timeout 100 git push`
killed the gate mid-suite and left law_trusttx paralegal '' -> 'r' in the
working tree. It never shipped only because every later commit was read file by
file. The rule "never wrap git push in timeout" then lived in a handoff and a
memory note, and Michael's b61 call was the right one: a rule drifts and a
check does not.

── TWO LAYERS, BECAUSE A PUSH CAN BE WRAPPED IN TWO PLACES ──────────────────
  --pre-push  the LIVE command. git runs this hook for every push from every
              caller, so it reads this process's ANCESTORS and refuses if one
              of them is `timeout`. It runs before any gate touches a file, so a
              refusal here leaves nothing to restore. MEASURED, not assumed, on
              Windows/Git Bash: the hook's chain under `timeout 30 git ...` is
              python <- sh <- git <- git <- timeout <- timeout, and without it
              the chain reaches bash/claude with no timeout in it.
  --scan      the TOOLING. A Python subprocess call with `timeout=` kills its
              child the same way and leaves no `timeout` process to see, so
              that shape can only be caught in the source. Every tracked
              .py/.js/.sh/hook file is read: a git push inside a call that also
              carries a timeout, or a shell string `timeout N git push`.

── WHAT IT CANNOT SEE ───────────────────────────────────────────────────────
  - The Claude Code Bash tool's own timeout. It kills a foreground command at
    its limit, and it is not a process in the chain. Push in the background.
  - A push killed by hand, by memory pressure or by closing the window. Those
    need a journal that notices a leftover mutant on the NEXT run -- designed in
    SAIRN-handoff-fourth-b60.md and routed to cody (Michael's b61 item 1).
  - Markdown. A handoff that QUOTES the incident is not a tool that does it.
  - A push built from a variable the scan cannot resolve (`cmd = [...]` then
    `subprocess.run(cmd, timeout=9)`). Only literal arguments are read.

── FAILS OPEN ON ITS OWN INTERNAL ERROR, AND SAYS SO ────────────────────────
Same standard as every hook in .githooks/: a gate that crashes closed gets
disabled and then protects nothing. An ancestry it cannot read is printed as
COULD NOT TELL -- the third state, never folded into a pass -- and the push
goes on. A fixture it misclassifies is exit 2, so --scan never reports clean
on criteria that cannot classify their own cases.
"""
import ast
import os
import re
import subprocess
import sys

CRITERIA_VERSION = '2026-10-28.1'

# Process names that kill their child on a clock. `timeout` is GNU coreutils
# (the one Git Bash ships and the one that caused b59); gtimeout is its
# Homebrew name.
KILLERS = {'timeout', 'timeout.exe', 'gtimeout'}

# A shell line that wraps git push in timeout: options (with or without their
# own value, `-k 5`) and a duration between them, and `git -C dir push` as well
# as `git push`.
SHELL_RE = re.compile(r'\b(?:g?timeout)(?:\s+-{1,2}[\w=-]+(?:\s+[\d.]+[smhd]?)?)*\s+[\d.]+[smhd]?\s+git\b[^\n|;&]*?\bpush\b')
SUBPROCESS_FUNCS = {'run', 'call', 'check_call', 'check_output', 'Popen'}
JS_CALL_RE = re.compile(r'\b(?:execSync|execFileSync|spawnSync|exec|execFile|spawn)\s*\(')
TOOL_EXT = ('.py', '.js', '.mjs', '.cjs', '.sh')
SELF = 'tools/push_timeout_guard.py'


# ── LAYER 1: THE LIVE COMMAND ────────────────────────────────────────────────
def ancestors():
    """[(pid, name), ...] from this process up, or None if it cannot be read."""
    if os.name == 'nt':
        try:
            import ctypes
            from ctypes import wintypes

            class PE(ctypes.Structure):
                _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                            ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_void_p),
                            ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                            ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', ctypes.c_long),
                            ('dwFlags', wintypes.DWORD), ('szExeFile', ctypes.c_char * 260)]
            k = ctypes.windll.kernel32
            k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
            snap = k.CreateToolhelp32Snapshot(2, 0)        # TH32CS_SNAPPROCESS
            if not snap or snap == wintypes.HANDLE(-1).value:
                return None
            e = PE()
            e.dwSize = ctypes.sizeof(PE)
            procs = {}
            ok = k.Process32First(snap, ctypes.byref(e))
            while ok:
                procs[e.th32ProcessID] = (e.th32ParentProcessID, e.szExeFile.decode('mbcs', 'replace'))
                ok = k.Process32Next(snap, ctypes.byref(e))
            k.CloseHandle(snap)
        except Exception:                                  # noqa: BLE001
            return None
        out, pid, seen = [], os.getpid(), set()
        while pid in procs and pid not in seen:
            seen.add(pid)
            ppid, name = procs[pid]
            out.append((pid, name))
            pid = ppid
        return out or None
    out, pid, seen = [], os.getpid(), set()
    while pid > 1 and pid not in seen:
        seen.add(pid)
        try:
            st = open('/proc/%d/stat' % pid).read()
            name = st[st.index('(') + 1:st.rindex(')')]
            ppid = int(st[st.rindex(')') + 2:].split()[1])
        except Exception:                                  # noqa: BLE001
            break
        out.append((pid, name))
        pid = ppid
    return out or None


def killer_in(chain):
    for pid, name in chain or []:
        if os.path.basename(name).lower() in KILLERS:
            return pid, name
    return None


def pre_push():
    chain = ancestors()
    if chain is None:
        print('push_timeout_guard: COULD NOT TELL -- this platform\'s process ancestry could not be '
              'read, so whether this push runs under `timeout` was NOT checked. Not a pass. The push '
              'goes on (hooks fail open on their own errors).', file=sys.stderr)
        return 0
    hit = killer_in(chain)
    if not hit:
        return 0
    print('\n'.join([
        '',
        'REFUSED (push_timeout_guard): this push is running under `%s` (pid %d).' % (hit[1], hit[0]),
        '  chain: ' + ' <- '.join('%s(%d)' % (n, p) for p, n in chain),
        '',
        'The push gate writes MUTANTS into tracked files and restores them in `finally`;',
        'a timeout that fires mid-gate skips the restore and leaves the mutant in your tree.',
        'fourth b59 (2026-10-27): `timeout 100 git push` left api/_lib/law-roles.js mutated.',
        'Nothing has been run or changed -- this check is first. Push WITHOUT the timeout;',
        'if it is slow, run it in the background instead.',
        '']), file=sys.stderr)
    return 1


# ── LAYER 2: THE TOOLING ─────────────────────────────────────────────────────
def _is_push_args(node):
    """A literal ['git', ..., 'push', ...] list/tuple, or a string holding `git ... push`."""
    if isinstance(node, (ast.List, ast.Tuple)):
        vals = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        if vals and os.path.basename(vals[0]).lower() in ('git', 'git.exe') and 'push' in vals[1:]:
            return True
        # ['timeout', '60', 'git', 'push'] as an argv is the shell shape in a list
        if vals and vals[0] in ('timeout', 'gtimeout') and 'git' in vals and 'push' in vals:
            return True
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return bool(re.search(r'\bgit\b[^\n|;&]*?\bpush\b', node.value))
    return False


def scan_python(src):
    """[(line, why)] for one Python source."""
    out = []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    docs = _docstring_ids(tree)
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and SHELL_RE.search(n.value):
            if id(n) not in docs:
                out.append((n.lineno, 'a string runs `timeout ... git push`'))
        if not isinstance(n, ast.Call):
            continue
        fn = n.func
        name = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else '')
        if name not in SUBPROCESS_FUNCS or not n.args:
            continue
        if not _is_push_args(n.args[0]):
            continue
        if any(k.arg == 'timeout' for k in n.keywords):
            out.append((n.lineno, '%s(git push ..., timeout=...) kills the push on a clock' % name))
        elif isinstance(n.args[0], (ast.List, ast.Tuple)) and n.args[0].elts and \
                isinstance(n.args[0].elts[0], ast.Constant) and n.args[0].elts[0].value in ('timeout', 'gtimeout'):
            out.append((n.lineno, '%s([\'timeout\', ..., \'git\', \'push\']) wraps the push' % name))
    # ── A PUSH THROUGH A HELPER (found on the first real scan, b61) ─────────
    # tools/push_retry.py pushed with git('push', 'origin', 'main'), and its
    # git() runs subprocess.run(['git'] + list(args), timeout=120). Neither
    # line alone is a timed push; together they are. So: a function whose
    # body runs `git` with a timeout is a TIMED GIT HELPER, and a call to it
    # whose first argument is 'push' is flagged -- unless that call passes
    # timeout=None, which is how a helper is told not to start the clock.
    helpers = {}
    for f in ast.walk(tree):
        if not isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for c in ast.walk(f):
            if isinstance(c, ast.Call) and c.args and _call_name(c) in SUBPROCESS_FUNCS and \
                    _starts_with_git(c.args[0]) and any(k.arg == 'timeout' for k in c.keywords):
                helpers[f.name] = c.lineno
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and n.args and _call_name(n) in helpers):
            continue
        a0 = n.args[0]
        if not (isinstance(a0, ast.Constant) and a0.value == 'push'):
            continue
        if any(k.arg == 'timeout' and isinstance(k.value, ast.Constant) and k.value.value is None
               for k in n.keywords):
            continue
        out.append((n.lineno, "%s('push', ...) runs through %s(), which sets a timeout (line %d)"
                    % (_call_name(n), _call_name(n), helpers[_call_name(n)])))
    return sorted(set(out))


def _call_name(c):
    fn = c.func
    return fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else '')


def _starts_with_git(node):
    """['git', ...], ['git'] + args, or ['git', *args]."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        node = node.left
    if isinstance(node, (ast.List, ast.Tuple)) and node.elts:
        e = node.elts[0]
        return isinstance(e, ast.Constant) and isinstance(e.value, str) and \
            os.path.basename(e.value).lower() in ('git', 'git.exe')
    return False


def _docstring_ids(tree):
    """ids of every docstring node -- computed once per file (a per-string
    re-walk of the whole tree made the full scan 82 s)."""
    ids = set()
    for holder in [tree] + [n for n in ast.walk(tree)
                            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]:
        body = getattr(holder, 'body', [])
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            ids.add(id(body[0].value))
    return ids

def scan_text(src, js=False):
    """[(line, why)] for shell/hook files and JS: comment lines are not code."""
    out = []
    lines = src.splitlines()
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith('#') or s.startswith('//') or s.startswith('*'):
            continue
        if SHELL_RE.search(line):
            out.append((i, 'runs `timeout ... git push`'))
    if js:
        for m in JS_CALL_RE.finditer(src):
            # the call's own text, up to its closing paren at depth 0
            depth, j = 0, m.end() - 1
            while j < len(src):
                c = src[j]
                depth += c == '('
                depth -= c == ')'
                if depth == 0:
                    break
                j += 1
            call = src[m.start():j + 1]
            if re.search(r'\bgit\b[^\n]*?\bpush\b', call) and re.search(r'\btimeout\s*:', call):
                out.append((src.count('\n', 0, m.start()) + 1, 'a child-process call runs git push with a timeout option'))
    return sorted(set(out))


def scan_file(rel, src):
    # Every shape this reports needs BOTH words in the file, so a file without
    # them cannot match and is not parsed. Measured on this tree: the parse
    # alone was 29 s and the whole --scan is now about 8 s end to end, which is
    # what lets it run on every push.
    if 'push' not in src or 'timeout' not in src:
        return []
    if rel.endswith('.py'):
        return scan_python(src)
    if rel.endswith(('.js', '.mjs', '.cjs')):
        return scan_text(src, js=True)
    return scan_text(src)


def tracked_tools(repo):
    r = subprocess.run(['git', 'ls-files'], cwd=repo, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        return None
    files = []
    for rel in r.stdout.splitlines():
        if rel == SELF or rel.startswith('node_modules/') or rel.startswith('archive/'):
            continue
        if rel.endswith(TOOL_EXT) or rel.startswith('.githooks/'):
            files.append(rel)
    return files


def scan_hits(repo):
    """[(rel, line, why)] over every tracked tool, or None if git could not list them."""
    files = tracked_tools(repo)
    if files is None:
        return None
    hits = []
    for rel in files:
        try:
            src = open(os.path.join(repo, rel), encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        hits += [(rel, ln, why) for ln, why in scan_file(rel, src)]
    scan_hits.files = len(files)
    return hits


def scan(repo):
    hits = scan_hits(repo)
    if hits is None:
        print('COULD NOT RUN: `git ls-files` failed in %s' % repo)
        return 2
    print('PUSH TIMEOUT GUARD -- criteria %s -- %d tracked tool file(s) read' % (CRITERIA_VERSION, scan_hits.files))
    if not hits:
        print('  clean: no tool runs git push under a timeout')
        return 0
    for rel, ln, why in hits:
        print('  ! %s:%d  %s' % (rel, ln, why))
    print('\n%d finding(s). A push killed on a clock can leave a gate mutant in the tree. '
          'Drop the timeout; run the push in the background if it is slow.' % len(hits))
    return 1


# ── FIXTURES: THE CRITERIA LOCKED BEFORE THEY JUDGE REAL FILES ──────────────
FIXTURES = [
    # (name, file, source, should_flag)
    ('shell, the b59 command', 'x.sh', 'timeout 100 git push origin main\n', True),
    ('shell, options and -C', 'x.sh', 'timeout -k 5 --signal=TERM 60s git -C ../r push -q\n', True),
    ('shell, a comment quoting it', 'x.sh', '# never: timeout 100 git push\n', False),
    ('shell, timeout on something else', 'x.sh', 'timeout 30 node tests/a.js && git push\n', False),
    ('hook file, no extension', '.githooks/pre-push', 'timeout 9 git push\n', True),
    ('python, run with timeout=', 'x.py', "import subprocess\nsubprocess.run(['git', 'push', 'origin', 'main'], timeout=100)\n", True),
    ('python, multi-line call', 'x.py', "import subprocess\nsubprocess.run(\n    ['git', '-C', r, 'push'],\n    capture_output=True,\n    timeout=60)\n", True),
    ('python, argv starts with timeout', 'x.py', "import subprocess\nsubprocess.call(['timeout', '60', 'git', 'push'])\n", True),
    ('python, shell string', 'x.py', "import os\nos.system('timeout 60 git push origin main')\n", True),
    ('python, push with NO timeout', 'x.py', "import subprocess\nsubprocess.run(['git', 'push', 'origin', 'main'])\n", False),
    ('python, timeout on a NON-push git call', 'x.py', "import subprocess\nsubprocess.run(['git', 'fetch'], timeout=30)\n", False),
    ('python, the word push in a test name', 'x.py', "import subprocess\nsubprocess.run(['node', 'push_test.js'], timeout=30)\n", False),
    ('python, push through a timed helper (push_retry.py shape)', 'x.py',
     "import subprocess\ndef git(*a):\n    return subprocess.run(['git'] + list(a), timeout=120)\ngit('push', 'origin', 'main')\n", True),
    ('python, timed helper told timeout=None for the push', 'x.py',
     "import subprocess\ndef git(*a, timeout=120):\n    return subprocess.run(['git'] + list(a), timeout=timeout)\ngit('push', 'origin', 'main', timeout=None)\n", False),
    ('python, timed helper used for fetch only', 'x.py',
     "import subprocess\ndef git(*a):\n    return subprocess.run(['git'] + list(a), timeout=120)\ngit('fetch', 'origin')\n", False),
    ('python, untimed helper pushing', 'x.py',
     "import subprocess\ndef git(*a):\n    return subprocess.run(['git'] + list(a))\ngit('push', 'origin', 'main')\n", False),
    ('python, the rule in a docstring', 'x.py', '"""never `timeout 100 git push` -- see b59"""\n', False),
    ('js, execSync with timeout', 'x.js', "execSync('git push origin main', { timeout: 60000 });\n", True),
    ('js, execSync push no timeout', 'x.js', "execSync('git push origin main', { stdio: 'inherit' });\n", False),
    ('js, timeout on a non-push call', 'x.js', "execSync('node a.js', { timeout: 60000 }); // then git push\n", False),
]


def fixtures_quiet():
    """Number of misclassified fixtures, printing nothing -- for the pre-push path."""
    bad = sum(bool(scan_file(rel, src)) != want for _, rel, src, want in FIXTURES)
    return bad


def fixtures():
    bad = 0
    for name, rel, src, want in FIXTURES:
        got = bool(scan_file(rel, src))
        if got != want:
            bad += 1
            print('  FAIL %s -- wanted %s, got %s' % (name, 'flag' if want else 'clean', 'flag' if got else 'clean'))
    # the ancestry matcher, on synthetic chains
    for chain, want in (([(9, 'python.exe'), (8, 'sh.exe'), (7, 'git.exe'), (6, 'timeout.exe')], True),
                        ([(9, 'python3'), (8, 'git'), (7, 'timeout')], True),
                        ([(9, 'python.exe'), (8, 'git.exe'), (7, 'bash.exe'), (6, 'claude.exe')], False),
                        ([(9, 'python.exe'), (8, 'node_timeout_helper.exe')], False)):
        if bool(killer_in(chain)) != want:
            bad += 1
            print('  FAIL ancestry %r -- wanted %s' % ([n for _, n in chain], want))
    total = len(FIXTURES) + 4
    print('push_timeout_guard criteria %s: %d/%d fixtures classify correctly' % (CRITERIA_VERSION, total - bad, total))
    return 2 if bad else 0


def main(argv):
    repo = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip() or '.'
    if '--fixtures' in argv:
        return fixtures()
    if '--scan' in argv:
        rc = fixtures()
        if rc:
            print('COULD NOT RUN: the criteria misclassify their own fixtures, so no real file is judged.')
            return 2
        return scan(repo)
    if '--pre-push' in argv:
        # BOTH LAYERS ON EVERY PUSH. The live command first (cheap, and nothing
        # has run yet); then the tooling, so a tool that starts pushing on a
        # clock is refused on the first push after it lands, not on the day it
        # finally fires. The scan is silent when clean.
        try:
            rc = pre_push()
            if rc:
                return rc
            if fixtures_quiet():
                print('push_timeout_guard: COULD NOT RUN the tooling scan -- its criteria misclassify '
                      'their own fixtures. Not a pass; the push goes on.', file=sys.stderr)
                return 0
            hits = scan_hits(repo)
            if hits is None:
                print('push_timeout_guard: COULD NOT RUN the tooling scan (`git ls-files` failed). '
                      'Not a pass; the push goes on.', file=sys.stderr)
                return 0
            if hits:
                print('\nREFUSED (push_timeout_guard): a tracked tool runs git push under a timeout.',
                      file=sys.stderr)
                for rel, ln, why in hits:
                    print('  ! %s:%d  %s' % (rel, ln, why), file=sys.stderr)
                print("A push killed on a clock skips the gate's restore and can leave a mutant in a "
                      'tracked file. Drop the timeout (a git() helper takes timeout=None).\n', file=sys.stderr)
                return 1
            return 0
        except Exception as e:                             # noqa: BLE001
            print('push_timeout_guard: COULD NOT TELL (%s: %s) -- not checked, not a pass; the push goes on.'
                  % (type(e).__name__, e), file=sys.stderr)
            return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
