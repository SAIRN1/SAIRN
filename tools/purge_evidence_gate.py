"""Record the forensics BEFORE anything destroys them, and refuse a prune that did not.

Run:  python tools/purge_evidence_gate.py --audit           # scan for unguarded prunes
      python tools/purge_evidence_gate.py --record          # write today's evidence record
      python tools/purge_evidence_gate.py --require-record  # exit 0 only if today's exists

── THE INCIDENT, ON THIS CLONE ─────────────────────────────────────────────
2026-09-28 a session purged a credential from SAIRN-fourth, re-verified by
content hash, and reported ZERO unreachable objects. 2026-09-29 the same search
found ONE unreachable blob in the same clone. Both readings cannot be explained
without knowing WHEN the blob arrived -- and the two things that would have
said, the object's mtime and the reflog entry keeping it alive, had been
destroyed by the `reflog expire --expire-unreachable=now` and `gc --prune=now`
that fixed the problem.

THE FIX AND THE FORENSICS ARE THE SAME COMMAND, AND THE FIX HAS TO WIN. There
is no version of this where the prune is wrong. So the only defence left is
ordering: record first, prune second, and make "prune second" mechanically
impossible to reach without the first.

`tools/credential_purge_check.py --record` already writes a dated VERDICT
(count searched, zero or not). That is not the same artefact. A verdict says
"zero, over 5,596 objects, on this date"; this says "here are the unreachable
object ids and their mtimes, on this date, before anything was destroyed". The
first answers *was it clean*; only the second can answer *when did this arrive*,
which is the question that actually went unanswerable.

── HOW --audit DECIDES, AND THE TWO TRAPS IT WAS BUILT WRONG INTO FIRST ────
The first version of this file matched `gc`/`prune`/`reflog expire` with regexes
over comment-stripped lines. It reported 40 findings on this repo and 40 of them
were wrong in one of two ways, both worth naming because both are the standing
classes on this platform:

  37 of 40 were `git worktree prune`, WHICH DESTROYS NO OBJECTS. It removes
  stale worktree administrative files. A gate that blocks 37 correct lines is a
  gate somebody switches off, which is the failure the whole repo is organised
  around avoiding.

  3 of 40 were PROSE -- two inside module docstrings describing this very
  incident, one inside a tool-description string in tools/tooling_inventory.py.
  A line-oriented comment stripper cannot see a triple-quoted docstring, and
  a string constant cannot be stripped without blinding the detector to
  `subprocess.run(['git', 'gc', ...])`, where the command IS a string constant.

SO IT DOES NOT MATCH TEXT. For Python it walks the AST, finds the calls that
actually execute a subprocess, and reads the string constants inside THOSE
calls. A docstring is never inside a Call node and a description table is never
inside `subprocess.run`, so both fall out by construction rather than by a
heuristic that has to be maintained. No fixed-size window anywhere.

For `.js` and for hook/shell files there is no AST available here, so those are
line-based, and the requirement is an invocation marker (`spawnSync`, `execSync`,
`exec`, `spawn`, or a shell line whose command word is `git`) on the same line.
That limit is stated rather than hidden: a multi-line JS spawn with the
subcommand on its own line is NOT seen. It is listed in the DISCLOSED section
so it is visible instead of silently absent.

Everything the scan touched and did not block on is printed under DISCLOSED,
with the reason. Nothing is dropped quietly -- a truncation that reads as
"covered everything" is the defect this repo keeps paying for.

── THE EVIDENCE PREDICATE IS COMMENT-STRIPPED, AND THAT IS THE POINT ───────
Whether a file records before it prunes is decided on comment-stripped source.
A file carrying `# purge_evidence_gate.py --record was run by hand, honest`
above a real `gc --prune=now` is UNGUARDED and is reported as such. That is the
sixth instance of the class: a predicate satisfiable by comment text instead of
by behaviour.

── FAIL CLOSED (PR 1.11) ───────────────────────────────────────────────────
`--record` exits 2 COULD NOT RUN, never 0, when git cannot be invoked or when
`fsck` fails, and writes NOTHING in that case. A record that exists but is empty
because the fsck failed is worse than no record: the next session reads it as
evidence of zero.
"""
import argparse
import ast
import datetime
import io
import json
import os
import re
import subprocess
import sys

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_RECORD_DIR = os.path.join(REPO, 'docs', 'purge-evidence')

SCAN_DIRS = ('tools', 'tests', '.githooks')
PY_EXT = ('.py',)
JS_EXT = ('.js',)
SH_EXT = ('.sh', '')

# Python callables that hand a command line to the operating system.
#
# `git`, `run_git` and `sh` are in here because MOST PROBES IN THIS REPO DO NOT
# CALL subprocess DIRECTLY -- they define a local `def git(repo, *args)` helper
# and call that. The first AST version missed fifteen files for exactly that
# reason, and a detector that is blind to the way the repo actually writes the
# call is a detector that reports zero forever.
SUBPROCESS_NAMES = ('run', 'call', 'check_call', 'check_output', 'Popen',
                    'system', 'getoutput', 'getstatusoutput', 'spawn',
                    'git', 'run_git', 'sh')
JS_INVOKERS = ('spawnSync', 'execSync', 'execFileSync', 'spawn', 'exec',
               'execFile')

# `git worktree prune` and `git remote prune` remove administrative files and
# remote-tracking refs. Neither deletes an object, so neither can destroy the
# mtime evidence. Named rather than pattern-guessed.
NOT_HISTORY_DESTROYING = ('worktree', 'remote', 'submodule')

EVIDENCE = (
    re.compile(r'purge_evidence_gate(\.py)?[^\n]{0,40}--record'),
    re.compile(r'\brecord_evidence\s*\('),
    re.compile(r'\brequire_record\s*\('),
)


def clone_label(path):
    """A filename-safe label that is UNIQUE across the checkouts on this machine.

    `os.path.basename` IS NOT ENOUGH AND THE FIRST RUN PROVED IT. There are two
    stray bare git directories here -- C:/Users/marsh/.git and
    C:/Users/marsh/Documents/.git -- and both have the basename `.git`, so the
    second record silently OVERWROTE the first and the run reported nine
    successes for eight distinct records. A collision that reports success is
    the shape this whole file exists to refuse, arriving through the filename.
    """
    p = os.path.abspath(path).rstrip(os.sep)
    base = os.path.basename(p)
    if base in ('.git', '') or base.startswith('.'):
        parent = os.path.basename(os.path.dirname(p)) or 'root'
        return (parent + base).replace(os.sep, '-')
    return base


def git_bin():
    return os.environ.get('SAIRN_PURGE_EVIDENCE_GIT') or 'git'


def destructive_tokens(tokens):
    """Do these argv tokens destroy git objects? Returns a reason or None."""
    t = [x.lower() for x in tokens]
    if 'git' not in t and not any(x.startswith('--prune') or
                                  x.startswith('--expire-unreachable') for x in t):
        return None
    for skip in NOT_HISTORY_DESTROYING:
        if skip in t:
            return None
    if 'gc' in t:
        return 'git gc (prunes by default via gc.pruneExpire)'
    if 'prune' in t:
        return 'git prune'
    if 'reflog' in t and ('expire' in t or 'delete' in t):
        return 'git reflog expire/delete (removes what keeps an object reachable)'
    for x in t:
        if x.startswith('--prune'):
            return 'a --prune flag'
        if x.startswith('--expire-unreachable'):
            return '--expire-unreachable'
    return None


def tokenize(strings):
    out = []
    for s in strings:
        out.extend(s.split())
    return out


# ── comment stripping, for the EVIDENCE predicate only ──────────────────────
def strip_comments(src, ext):
    """Remove what cannot execute. Used ONLY to decide whether an evidence call
    is present -- never to decide whether a command is present, because a
    command's own text lives in a string literal."""
    if ext in JS_EXT:
        src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    out = []
    for line in src.split('\n'):
        i = line.find('//') if ext in JS_EXT else line.find('#')
        out.append(line if i < 0 else line[:i])
    return '\n'.join(out)


def evidence_line(src, ext):
    for lineno, line in enumerate(strip_comments(src, ext).split('\n'), 1):
        if any(rx.search(line) for rx in EVIDENCE):
            return lineno
    return None


# ── Python: the AST walk ────────────────────────────────────────────────────
def _call_name(node):
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ''


def _literal_strings(node):
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            out.append(sub.value)
    return out


def scan_python(src):
    """Returns (executable, disclosed). Each entry is (lineno, text, reason)."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [], [(getattr(e, 'lineno', 0) or 0, 'unparseable',
                     'COULD NOT PARSE (%s) -- NOT scanned, and not a pass' % e.msg)]
    executable, disclosed = [], []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name not in SUBPROCESS_NAMES:
            continue
        toks = tokenize(_literal_strings(node))
        # A `git(REPO, 'gc', '--prune=now')` helper carries the word `git` in
        # the CALLEE, not in the arguments, so it is supplied here. Without
        # this the helper form reads as ['gc', '--prune=now'] with no `git`
        # and falls through as not-a-git-command.
        if name in ('git', 'run_git'):
            toks = ['git'] + toks
        if not toks:
            continue
        why = destructive_tokens(toks)
        text = ' '.join(toks)[:110]
        if why:
            executable.append((node.lineno, text, why))
        elif any(k in [t.lower() for t in toks]
                 for k in ('gc', 'prune', 'reflog')):
            executable_reason = 'subprocess call mentions %s but is not history-destroying' % \
                ', '.join(sorted({t.lower() for t in toks}
                                 & {'gc', 'prune', 'reflog', 'worktree', 'remote'}))
            disclosed.append((node.lineno, text, executable_reason))
    return executable, disclosed


# ── JS and shell: line-based, with the limit stated ─────────────────────────
def scan_lines(src, ext):
    executable, disclosed = [], []
    stripped = strip_comments(src, ext)
    for lineno, line in enumerate(stripped.split('\n'), 1):
        toks = tokenize([line])
        if not toks:
            continue
        invoked = (any(m in line for m in JS_INVOKERS) if ext in JS_EXT
                   else (toks[0] == 'git' or ' git ' in line))
        why = destructive_tokens(toks)
        text = line.strip()[:110]
        if why and invoked:
            executable.append((lineno, text, why))
        elif why:
            disclosed.append((lineno, text,
                              'matches %s but no invocation marker on this line '
                              '-- line-based scan, no AST for this file type' % why))
        elif any(k in [t.lower() for t in toks] for k in ('gc', 'prune', 'reflog')) \
                and invoked:
            disclosed.append((lineno, text, 'invocation mentions gc/prune/reflog '
                                            'but is not history-destroying'))
    # Non-executing text, disclosed so it is visible rather than absent.
    for lineno, line in enumerate(src.split('\n'), 1):
        if lineno <= len(stripped.split('\n')) and \
                stripped.split('\n')[lineno - 1].strip() == line.strip():
            continue
        if destructive_tokens(tokenize([line])):
            disclosed.append((lineno, line.strip()[:110],
                              'comment text only -- a note about gc is not a gc'))
    return executable, disclosed


def scan_file(path):
    try:
        src = io.open(path, encoding='utf-8', errors='replace').read()
    except OSError as e:
        return [], [(0, os.path.basename(path), 'UNREADABLE (%s)' % e)], None
    ext = os.path.splitext(path)[1].lower()
    if ext in PY_EXT:
        ex, dis = scan_python(src)
    else:
        ex, dis = scan_lines(src, ext)
    return ex, dis, evidence_line(src, ext)


# ── the audit ───────────────────────────────────────────────────────────────
SELF = ('tools/purge_evidence_gate.py', 'tests/run_purge_evidence_probe.py')


def audit(root):
    findings, disclosed = [], []
    scanned = 0
    for d in SCAN_DIRS:
        base = os.path.join(root, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x != '__pycache__']
            for fn in sorted(filenames):
                ext = os.path.splitext(fn)[1].lower()
                if ext not in PY_EXT + JS_EXT + SH_EXT:
                    continue
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, root).replace('\\', '/')
                # This file and its probe ARE the gate: every pattern above
                # appears here as a pattern, not as a call. Named explicitly so
                # the exemption is auditable rather than heuristic.
                if rel in SELF:
                    continue
                scanned += 1
                ex, dis, guard = scan_file(path)
                for lineno, text, why in ex:
                    if guard is None or guard > lineno:
                        findings.append((rel, lineno, text, why,
                                         'no evidence call in this file' if guard is None
                                         else 'evidence call is AFTER it (line %d)' % guard))
                    else:
                        disclosed.append((rel, lineno, text,
                                          'guarded -- evidence call at line %d' % guard))
                for lineno, text, why in dis:
                    disclosed.append((rel, lineno, text, why))

    print('PURGE-EVIDENCE AUDIT -- root %s' % root)
    print('files scanned: %d  (%s)' % (scanned, ', '.join(SCAN_DIRS)))
    print('')
    print('EXECUTABLE history-destroying commands with no prior evidence call: %d'
          % len(findings))
    for rel, lineno, text, why, order in findings:
        print('  %s:%d  %s' % (rel, lineno, order))
        print('      %s' % why)
        print('      %s' % text)
    print('')
    print('DISCLOSED -- seen, not blocked, with the reason: %d' % len(disclosed))
    for rel, lineno, text, why in disclosed:
        print('  %s:%d  %s' % (rel, lineno, why))
    print('')
    if findings:
        print('BLOCKING. Record the forensics first:')
        print('    python tools/purge_evidence_gate.py --record')
        print('then run the prune. The fix and the forensics are the same command,')
        print('so the ordering is the only thing that can preserve both.')
        return EXIT_FINDING
    print('OK -- every executable prune/gc/reflog-expire is preceded by an')
    print('evidence call in its own file.')
    return EXIT_CLEAN


# ── the record ──────────────────────────────────────────────────────────────
def record_evidence(record_dir, repo=None):
    """Write today's evidence record. Returns (exit_code, path_or_reason).

    NOTHING IS WRITTEN UNLESS THE FSCK COULD BE READ. An empty `unreachable`
    list because fsck failed reads identically to a genuinely clean repo, and
    that is the exact confusion this tool exists to end.

    `repo` RECORDS ANOTHER CLONE WITHOUT WRITING INTO IT. There are seven
    checkouts on this machine plus two stray git directories, and four of the
    checkouts have a live session in them. Reading another clone's `git fsck`
    is read-only; writing a file into its working tree while it is mid-rebase
    is not, and `git add -A` staging somebody else's file is the exact failure
    push_retry.py exists to prevent. So the SUBJECT is the named repo and the
    DESTINATION is always the clone this tool was run from -- the record's
    filename and its `clone` field both carry the subject, so nothing is
    ambiguous about which repo was measured.
    """
    target = os.path.abspath(repo) if repo else REPO
    if not os.path.isdir(os.path.join(target, '.git')) and \
            not os.path.isfile(os.path.join(target, 'HEAD')):
        return EXIT_COULD_NOT_RUN, '%s is not a git repository or bare git dir' % target
    try:
        p = subprocess.run([git_bin(), 'fsck', '--unreachable', '--no-progress'],
                           cwd=target, capture_output=True, text=True)
    except (OSError, ValueError) as e:
        return EXIT_COULD_NOT_RUN, 'git could not be invoked (%s)' % e
    if p.returncode != 0 and not p.stdout.strip():
        return EXIT_COULD_NOT_RUN, ('git fsck exited %d with no output: %s'
                                    % (p.returncode, (p.stderr or '').strip()[:200]))

    unreachable = []
    for line in p.stdout.split('\n'):
        parts = line.split()
        if len(parts) >= 3 and parts[0] == 'unreachable':
            unreachable.append({'kind': parts[1], 'oid': parts[2]})

    # OBJECT MTIMES. Loose objects only -- a packed object has no mtime of its
    # own, so the packfile's mtime is recorded separately and the record says
    # which it is rather than silently conflating them.
    mtimes = {}
    objdir = os.path.join(target, '.git', 'objects')
    if not os.path.isdir(objdir):
        # A bare git dir (Documents/.git, ~/.git) has objects/ at its root.
        objdir = os.path.join(target, 'objects')
    for entry in unreachable:
        oid = entry['oid']
        loose = os.path.join(objdir, oid[:2], oid[2:])
        if os.path.isfile(loose):
            mtimes[oid] = {'where': 'loose',
                           'mtime': datetime.datetime.utcfromtimestamp(
                               os.path.getmtime(loose)).isoformat() + 'Z'}
        else:
            mtimes[oid] = {'where': 'packed-or-absent', 'mtime': None}
    packs = {}
    packdir = os.path.join(objdir, 'pack')
    if os.path.isdir(packdir):
        for fn in sorted(os.listdir(packdir)):
            if fn.endswith('.pack'):
                packs[fn] = datetime.datetime.utcfromtimestamp(
                    os.path.getmtime(os.path.join(packdir, fn))).isoformat() + 'Z'

    now = datetime.datetime.utcnow()
    rec = {
        'recorded_at': now.isoformat() + 'Z',
        'clone': clone_label(target),
        'subject_path': target,
        'recorded_from': os.path.basename(REPO),
        'fsck_exit': p.returncode,
        'unreachable': unreachable,
        'unreachable_count': len(unreachable),
        'object_mtimes': mtimes,
        'packfile_mtimes': packs,
        'note': ('Written BEFORE any prune/gc/reflog expire. No object contents, '
                 'no values, no fragments -- object ids, kinds and mtimes only.'),
    }
    try:
        os.makedirs(record_dir, exist_ok=True)
        path = os.path.join(record_dir, '%s-%s.json'
                            % (now.strftime('%Y-%m-%d'), clone_label(target)))
        io.open(path, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(rec, indent=1, sort_keys=True) + '\n')
    except OSError as e:
        return EXIT_COULD_NOT_RUN, 'could not write the record (%s)' % e
    return EXIT_CLEAN, path


def require_record(record_dir):
    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    want = '%s-%s.json' % (today, clone_label(REPO))
    path = os.path.join(record_dir, want)
    if not os.path.isfile(path):
        print('REFUSED -- no purge-evidence record for %s in %s'
              % (clone_label(REPO), record_dir))
        print('  expected: %s' % want)
        have = sorted(os.listdir(record_dir)) if os.path.isdir(record_dir) else []
        print('  present : %s' % (', '.join(have) if have else 'nothing'))
        print('')
        print('A record from an earlier day is NOT evidence for a prune today --')
        print('the objects it lists may have arrived since. Run:')
        print('    python tools/purge_evidence_gate.py --record')
        return EXIT_FINDING
    print('OK -- %s' % path)
    return EXIT_CLEAN


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--audit', action='store_true')
    g.add_argument('--record', action='store_true')
    g.add_argument('--require-record', action='store_true')
    ap.add_argument('--root', default=REPO, help='--audit: tree to scan')
    ap.add_argument('--dir', default=DEFAULT_RECORD_DIR, help='where records live')
    ap.add_argument('--repo', default=None,
                    help='--record: measure ANOTHER clone or bare git dir. '
                         'Read-only on the subject; the record is written '
                         'here, named for the subject.')
    a = ap.parse_args(argv)

    if a.audit:
        return audit(a.root)
    if a.record:
        rc, detail = record_evidence(a.dir, a.repo)
        if rc == EXIT_CLEAN:
            print('recorded: %s' % detail)
        else:
            print('COULD NOT RUN -- %s' % detail)
            print('NOTHING WAS WRITTEN. This is not a clean record and it is not')
            print('a pass: do not prune until fsck can be read.')
        return rc
    return require_record(a.dir)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
