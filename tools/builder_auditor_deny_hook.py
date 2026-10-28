#!/usr/bin/env python
# OWNER: cc
"""tools/builder_auditor_deny_hook.py -- a PreToolUse hook that stops a BUILD
agent's tool call from reaching anything the hover auditor owns, before the
call runs.

THE DIRECTION. tools/hover_auditor_scope_gate.py keeps the auditor out of
platform code. This file covers the other direction: builders reaching into the
auditor. CLAUDE.md: "A build agent must not reach into that clone ... that is
the same boundary problem running the other way." It is armed only in the
four builder clones (cc, cody, fourth, hank), through each clone's
.claude/settings.local.json. The installer and the recurring presence check
are in tools/builder_hook_presence.py. Builders may still touch each other's
code: this blocks only calls from a builder into the auditor.

WHAT THE AUDITOR OWNS. These patterns are matched against a normalised
absolute path (lower case, forward slashes):

  docs/sairn-path-manifest.json `auditor_paths`, read at run time and unioned
  with a built-in floor of the same three entries:
    .claude/skills/sairn-hover-auditor/       the role's skill (CLAUDE.md:
                                              "Its scope is ... and nothing else")
    docs/hover-audit-log/, docs/hover-evidence/
  plus the per-instance shapes no manifest entry carries:
  .claude/claims/hover<N>.json                an auditor instance's claim file
  SAIRN-{handoff,report,digest,closure-recheck}-H<N>-b<n>.{md,txt},
  SAIRN-latest-H<N>.md                        an auditor instance's deliverables
  .../SAIRN-hover<N>/                         the auditor clones themselves

Everything else the auditor MAY write is deliberately NOT listed. That covers
the defect register and the enforcement triad (hover_auditor_scope_gate.py,
hover_separation_audit.py, hover_separation_ci.py, hover_routing_gap_*). Those
paths are SHARED: builders write the register every batch, and cc owns the
scope gate. Blocking them would block legitimate builder work. That call is
routed to Michael rather than made here.

WHAT IS INSPECTED, PER CALL:
  Edit / Write / MultiEdit / NotebookEdit
      The target path is checked twice, as written and after os.path.realpath,
      so a symlink, a junction or a `..` cannot disguise it.
  Bash / PowerShell / Monitor  (the command text)
      1. TEXT: the whole command, including heredoc bodies and `-c` strings,
         is scanned for an auditor reference. It is scanned raw, and again
         with quotes, `+`, commas, backslashes and whitespace stripped, so
         'sairn-'+'hover' and sairn-ho""ver do not slip through.
      2. TOKENS: every path-like token is resolved against the current
         directory. That directory follows `cd`, `pushd` and `git -C`. Each
         token is checked as written and after realpath, and globs are
         expanded.
      3. GIT PATHSPEC SUBCOMMANDS (checkout, restore, rm, mv, clean, reset,
         stash): a pathspec that is an ANCESTOR of an auditor path (`.`,
         `.claude`) or a glob that git would match onto one (`*.md`) is
         refused, not only an exact hit.
      4. GIT APPLY / AM: every existing file in the command is read as a
         patch, and its target paths are checked.
      5. UNTRACKED SCRIPTS: an interpreter (python, node, bash, ...) run on a
         file that is not a clean tracked file is read and text-scanned. That
         is the route of writing a script to the scratchpad and running it.
         A committed, unmodified tool has been through review and the push
         gate, and it is not re-read on every call.

SUBAGENTS. A PreToolUse hook in settings fires for a subagent's tool calls as
well as the main session's. The payload's agent_id / agent_type go into the
log.

WHAT IT CANNOT SEE, stated rather than implied:
  * A committed tool whose own source opens an auditor path. The detect layer
    for that is tools/hover_separation_audit.py, run against history.
  * A path assembled at run time from variables, for example `X=hover;
    cd sairn-$X`. The text pass sees no literal and the token pass sees `$X`.
  * Imports reached from an untracked script. Only the script file itself is
    read.

FAILS CLOSED (PR SS1.11). An unreadable payload, a missing field or any
exception REFUSES the call with "COULD NOT RUN". Exit 2 is Claude Code's
blocking code. A missing hook file also fails closed: `python <absent file>`
exits 2, and that blocks the call too. A missing `python` exits 127, which
Claude Code treats as NON-blocking. That gap is why
tools/builder_hook_presence.py runs at every session start.

ALLOW IS SILENT: exit 0 with no output. The 2026-10-11 hook removal was about
hook output driving compaction, so this adds nothing to the context on the
calls it lets through.

THE BLOCK LOG. Every refusal appends one JSON line to
~/SAIRN-SESSION-LOCKS/builder-auditor-blocks.jsonl. That location is outside
every clone and is the same root as the status registry, so all six clones
can read it. The same line is also appended to
G:/My Drive/SAIRN-status/builder-auditor-blocks.jsonl, the Drive folder chat
reads. A failed log write is reported in the refusal and never turns it into
an allow.

    python tools/builder_auditor_deny_hook.py              # hook entry: payload on stdin
    python tools/builder_auditor_deny_hook.py --selftest   # criteria, both directions
"""
import datetime
import fnmatch
import glob
import io
import json
import os
import re
import shlex
import subprocess
import sys

CRITERIA_VERSION = '2026-10-28.b66.1'

WRITE_TOOLS = ('Edit', 'Write', 'MultiEdit', 'NotebookEdit')
COMMAND_TOOLS = ('Bash', 'PowerShell', 'Monitor')
MATCHER = '|'.join(WRITE_TOOLS + COMMAND_TOOLS)

# ── THE AUDITOR'S DIRECTORIES: the path manifest's list, UNIONED with a copy ──
# docs/sairn-path-manifest.json `auditor_paths` is the platform's own statement
# ("denied to every build population", enforced at the push). It is read at
# run time, so an entry added there reaches this hook with no edit here.
#
# THE BUILT-IN COPY IS A FLOOR, NOT A FALLBACK THAT PASSES. If the manifest
# cannot be read, this hook still refuses everything below. It does NOT refuse
# every call, and that is a deliberate departure from PR SS1.11. A hook that
# blocks every Edit and every Bash call while the manifest is broken would
# also block the one edit that repairs the manifest: a deadlock that only
# Michael, by hand, could clear. tools/builder_hook_presence.py reports an
# unreadable manifest at every session start, so the degraded state is not
# silent.
BUILTIN_AUDITOR_DIRS = ('.claude/skills/sairn-hover-auditor/', 'docs/hover-audit-log/',
                        'docs/hover-evidence/')


def clone_root(here=None):
    """The clone this copy belongs to: <clone>/tools/ or <clone>/.git/sairn-hooks/."""
    here = (here or os.path.dirname(os.path.abspath(__file__))).replace('\\', '/')
    parts = here.split('/')
    return '/'.join(parts[:parts.index('.git')]) if '.git' in parts else os.path.dirname(here)


MANIFEST = os.path.join(clone_root(), 'docs', 'sairn-path-manifest.json')


def manifest_auditor_paths(path=MANIFEST):
    """-> the manifest's auditor_paths, or None when it cannot be read."""
    try:
        v = json.loads(io.open(path, encoding='utf-8').read())['auditor_paths']
        return [e for e in v if isinstance(e, str) and e.strip('/')]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def build_scope(dirs):
    """-> (PATH_PATTERNS, TEXT_PATTERNS, REL_GLOBS) for these auditor dirs plus
    the fixed per-instance shapes no manifest entry carries."""
    stems = sorted(set(d.strip('/').lower() for d in dirs))
    # Against a normalised ABSOLUTE path: lower case, forward slashes.
    path_res = tuple(re.compile('/' + re.escape(s) + r'(?:/|$)') for s in stems) + (
        re.compile(r'/\.claude/claims/hover[0-9]*\.json$'),
        re.compile(r'/sairn-(?:handoff|report|digest|closure-recheck)-h[0-9]+-b[0-9]+\.(?:md|txt)$'),
        re.compile(r'/sairn-latest-h[0-9]+\.md$'),
        re.compile(r'/sairn-hover[0-9]*(?:/|$)'),          # the auditor clones
    )
    # Against command TEXT (raw-normalised and compacted). `sairn-hover` covers
    # the skill directory and the clones together.
    text_res = tuple(re.compile(re.escape(s)) for s in stems) + (
        re.compile(r'sairn-hover'),
        re.compile(r'claims/hover[0-9]*(?:\.json|\b)'),
        re.compile(r'sairn-(?:handoff|report|digest|closure-recheck)-h[0-9]+-b[0-9]+'),
        re.compile(r'sairn-latest-h[0-9]+'),
    )
    # Repo-relative, for the ancestor and git-glob questions.
    rel = tuple(d.strip('/') for d in sorted(set(dirs))) + (
        '.claude/claims/hover*.json', 'SAIRN-*-H[0-9]*-b[0-9]*.*', 'SAIRN-latest-H[0-9]*.md')
    return path_res, text_res, rel


MANIFEST_DIRS = manifest_auditor_paths()
AUDITOR_DIRS = tuple(sorted(set(BUILTIN_AUDITOR_DIRS) | set(MANIFEST_DIRS or ())))
PATH_PATTERNS, TEXT_PATTERNS, REL_GLOBS = build_scope(AUDITOR_DIRS)
GIT_PATHSPEC_SUBS = ('checkout', 'restore', 'rm', 'mv', 'clean', 'stash')
# A glob that EXPANDS onto an auditor path is refused only for these, or when it
# is a redirect target. `cat .claude/claims/*.json` is a read and expands onto
# hover.json; the baseline replay found exactly that shape (fourth, a `for`
# loop over the claim files). A LITERAL auditor path in the text is refused
# whatever the program, as specified.
MUTATING = ('cp', 'mv', 'rm', 'rmdir', 'touch', 'tee', 'sed', 'chmod', 'chown', 'ln',
            'truncate', 'dd', 'install', 'rsync', 'mkdir', 'unlink', 'shred', 'xargs',
            'set-content', 'add-content', 'out-file', 'remove-item', 'move-item',
            'copy-item', 'new-item')
GIT_PATCH_SUBS = ('apply', 'am')
INTERPRETERS = ('python', 'python3', 'py', 'node', 'bash', 'sh', 'pwsh',
                'powershell', 'perl', 'ruby', 'deno', 'bun')
SEGMENT_OPS = (';', '&&', '||', '|', '&', '(', ')', '\n')

LOCKS = os.path.join(os.path.expanduser('~'), 'SAIRN-SESSION-LOCKS')
LOG_NAME = 'builder-auditor-blocks.jsonl'
LOG_PATHS = (os.path.join(LOCKS, LOG_NAME),
             os.path.join('G:', os.sep, 'My Drive', 'SAIRN-status', LOG_NAME))


class CouldNotRun(Exception):
    pass


def norm(p):
    return os.path.abspath(p).replace('\\', '/').lower()


def path_hit(p):
    n = norm(p)
    return any(rx.search(n) for rx in PATH_PATTERNS)


def resolved_hits(p, base):
    """The auditor paths `p` reaches, both as written and after realpath."""
    full = p if os.path.isabs(p) else os.path.join(base, p)
    out = []
    for cand in (full, os.path.realpath(full)):
        if path_hit(cand) and cand not in out:
            out.append(cand)
    return out


def text_hits(text):
    raw = text.replace('\\', '/').lower()
    compact = re.sub(r"[\s'\"`+,\\]", '', text.lower()).replace('//', '/')
    found = []
    for s in (raw, compact):
        for rx in TEXT_PATTERNS:
            m = rx.search(s)
            if m and m.group(0) not in found:
                found.append(m.group(0))
    return found


def repo_root(start):
    d = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(d, '.git')):
            return d
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up


def auditor_rel_paths(root, walk=False):
    """Repo-relative auditor paths under `root`, forward slashes. With `walk`,
    every FILE inside the skill directory too, because a git glob such as
    `*.md` matches SKILL.md and not the directory. The ancestor question does
    not need the walk, and the walk is the slow part."""
    out = []
    for g in REL_GLOBS:
        for m in glob.glob(os.path.join(root, g)):
            out.append(os.path.relpath(m, root).replace('\\', '/'))
            if walk and os.path.isdir(m):
                for dp, _dn, fns in os.walk(m):
                    out.extend(os.path.relpath(os.path.join(dp, f), root).replace('\\', '/')
                               for f in fns)
    return out


def dirty(root, rels):
    """The subset of `rels` that git reports modified, staged or untracked."""
    if not rels:
        return []
    try:
        r = subprocess.run(['git', '-C', root, 'status', '--porcelain', '--untracked-files=all', '--']
                           + rels, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as e:
        raise CouldNotRun('git status in %s failed (%s)' % (root, e))
    if r.returncode != 0:
        raise CouldNotRun('git status in %s exited %d' % (root, r.returncode))
    changed = [ln[3:].strip().strip('"') for ln in r.stdout.splitlines() if len(ln) > 3]
    return [x for x in rels if any(c == x or c.startswith(x.rstrip('/') + '/') for c in changed)]


def pathspec_hits(tok, base, sub, words):
    """A git pathspec that is an ANCESTOR of an auditor path, or a glob git
    would match onto one. Exact and descendant hits are resolved_hits' job,
    and those are refused whatever the subcommand.

    WHEN AN ANCESTOR COUNTS -- measured, not assumed. The baseline replay of
    5,194 real builder calls (cc b66) found `git restore --staged .` and
    `git checkout -q -- .` in a scratch worktree among the would-be refusals.
    Neither can change an auditor file in a builder clone: the first touches
    only the index, and the second rewrites only files that differ from HEAD.
    No auditor file differs in a builder clone, because this hook stops it
    from differing. So:
      * index-only forms (`restore --staged` without `--worktree`,
        `rm --cached`) are not checked;
      * mv and rm move or delete whatever the pathspec covers, so an ancestor
        is refused unconditionally;
      * checkout, restore, stash and clean change only DIRTY files, so an
        ancestor is refused when git reports an auditor path under it as
        modified or untracked. That is exactly when the call would change
        one.
    """
    root = repo_root(base)
    if not root or tok.startswith(':'):
        return []
    if sub == 'restore' and ({'--staged', '-S'} & set(words)) and not ({'--worktree', '-W'} & set(words)):
        return []
    if sub == 'rm' and '--cached' in words:
        return []
    is_glob = any(c in tok for c in '*?[')
    rels = auditor_rel_paths(root, walk=is_glob)
    if is_glob:
        prefix = os.path.relpath(base, root).replace('\\', '/')
        pat = tok.replace('\\', '/') if prefix == '.' else prefix + '/' + tok.replace('\\', '/')
        under = [r for r in rels if fnmatch.fnmatch(r, pat) or fnmatch.fnmatch(os.path.basename(r), tok)]
    else:
        nf = norm(os.path.realpath(os.path.join(base, tok))).rstrip('/')
        under = [r for r in rels if norm(os.path.join(root, r)).startswith(nf + '/')]
    if sub in ('mv', 'rm'):
        return under
    return dirty(root, under)


def patch_targets(path, root):
    try:
        text = io.open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return []
    out = []
    for ln in text.splitlines():
        m = re.match(r'^(?:\+\+\+ b/|--- a/|rename (?:from|to) |copy (?:from|to) )(.+)$', ln)
        if m:
            out.append(m.group(1).strip())
        m = re.match(r'^diff --git a/(\S+) b/(\S+)', ln)
        if m:
            out.extend(m.groups())
    return [t for t in out if t != '/dev/null' and path_hit(os.path.join(root, t))]


def is_clean_tracked(path):
    d = os.path.dirname(os.path.abspath(path))
    try:
        out = subprocess.run(['git', '-C', d, 'status', '--porcelain', '--ignored', '--',
                              os.path.abspath(path)], capture_output=True, text=True, timeout=10)
        tracked = subprocess.run(['git', '-C', d, 'ls-files', '--error-unmatch', '--',
                                  os.path.abspath(path)], capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return out.returncode == 0 and out.stdout.strip() == '' and tracked.returncode == 0


def tokenize(cmd):
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=';&|()<>')
        lex.whitespace_split = True
        lex.commenters = ''
        return list(lex)
    except ValueError:
        return cmd.split()


def segments(tokens):
    seg = []
    for t in tokens:
        if t in SEGMENT_OPS or (t and set(t) <= set(';&|()')):
            if seg:
                yield seg
            seg = []
        else:
            seg.append(t)
    if seg:
        yield seg


def looks_like_path(tok):
    return ('/' in tok or '\\' in tok or tok.startswith('.')
            or any(c in tok for c in '*?['))


def inspect_command(cmd, cwd):
    """-> list of (call_type, path_or_reference). Empty means allow.

    The token pass runs twice, once on the command as written and once with
    backslashes turned into slashes. A POSIX tokenizer reads an unquoted
    `.claude\\skills` as escapes and loses the separators.
    """
    hits = [('command-text', h) for h in text_hits(cmd)]
    for variant in (cmd, cmd.replace('\\', '/')):
        hits.extend(h for h in _inspect_tokens(variant, cwd) if h not in hits)
    return hits


def _inspect_tokens(cmd, cwd):
    hits = []
    base = cwd
    for seg in segments(tokenize(cmd)):
        redirect_in = [seg[i + 1] for i, w in enumerate(seg[:-1]) if w == '<']
        redirect_out = set(seg[i + 1] for i, w in enumerate(seg[:-1]) if w in ('>', '>>', '&>'))
        words = [w for w in seg if w not in ('<', '>', '>>', '<<', '2>', '&>')]
        while words and re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', words[0]):
            words = words[1:]                       # leading env assignment
        if not words:
            continue
        prog = os.path.basename(words[0]).lower()
        if prog.endswith('.exe'):
            prog = prog[:-4]
        if prog in ('cd', 'pushd') and len(words) > 1:
            nxt = words[1]
            for p in resolved_hits(nxt, base):
                hits.append(('cd', p))
            base = nxt if os.path.isabs(nxt) else os.path.join(base, nxt)
            continue
        if prog in INTERPRETERS:
            # The SCRIPT only: the first positional argument, or the file fed
            # on stdin to `python -`. Data files passed to a script are not
            # read, because they are not code that runs.
            pos = [w for w in words[1:] if not w.startswith('-')]
            scripts = pos[:1] if pos and words[1:].count('-c') == 0 else []
            if prog == 'node' and ({'--check', '-c'} & set(words)):
                scripts = []                        # a syntax check runs nothing
            if (not scripts or scripts == ['-']) and redirect_in:
                scripts = redirect_in[:1]
            for s in scripts:
                full = s if os.path.isabs(s) else os.path.join(base, s)
                if not os.path.isfile(full):
                    continue
                try:
                    body = io.open(full, encoding='utf-8', errors='replace').read()
                except OSError as e:
                    raise CouldNotRun('script %s could not be read (%s)' % (full, e))
                # Scan first, ask git second: the git call is the slow part and
                # only a script that names an auditor path needs it.
                found = text_hits(body)
                if found and not is_clean_tracked(full):
                    for h in found:
                        hits.append(('%s untracked-script %s' % (prog, s), h))
        git_base, sub = base, None
        if prog == 'git':
            i = 1
            while i < len(words) and words[i].startswith('-'):
                if words[i] == '-C' and i + 1 < len(words):
                    git_base = os.path.join(git_base, words[i + 1])
                    i += 1
                i += 1
            sub = words[i] if i < len(words) else None
        call = 'git %s' % sub if sub else prog
        for w in words[1:]:
            val = w.split('=', 1)[1] if w.startswith('-') and '=' in w else w
            if not val or val.startswith('-'):
                continue
            b = git_base if prog == 'git' else base
            if looks_like_path(val) or os.path.lexists(os.path.join(b, val)):
                for p in resolved_hits(val, b):
                    hits.append((call, p))
                if any(c in val for c in '*?[') and prog != 'git' and (
                        prog in MUTATING or w in redirect_out):
                    # realpath per match is the slow part, so resolve each
                    # match's DIRECTORY once, plus the match itself only when
                    # it is a link.
                    dirs = {}
                    for m in glob.glob(os.path.join(b, val))[:2000]:
                        dn = os.path.dirname(m)
                        if dn not in dirs:
                            dirs[dn] = os.path.realpath(dn)
                        cands = [m, os.path.join(dirs[dn], os.path.basename(m))]
                        if os.path.islink(m):
                            cands.append(os.path.realpath(m))
                        for p in cands:
                            if path_hit(p):
                                hits.append((call + ' (glob)', p))
                                break
            if sub in GIT_PATHSPEC_SUBS:
                for r in pathspec_hits(val, git_base, sub, words):
                    hits.append((call + ' (pathspec)', r))
            full = os.path.join(b, val)
            if sub in GIT_PATCH_SUBS and os.path.isfile(full):
                for t in patch_targets(full, repo_root(git_base) or git_base):
                    hits.append((call + ' (patch)', t))
    # `cat x.patch | git apply` -- the patch is not an argument of git itself.
    if re.search(r'\bgit\b[^;&|]*\b(?:apply|am)\b', cmd):
        root = repo_root(cwd) or cwd
        for t in tokenize(cmd):
            f = os.path.join(cwd, t)
            if os.path.isfile(f):
                for p in patch_targets(f, root):
                    hits.append(('git apply (piped patch)', p))
    return hits


def decide(payload):
    """-> list of (call_type, path). Empty means allow. Raises CouldNotRun."""
    if not isinstance(payload, dict):
        raise CouldNotRun('the hook payload is not a JSON object')
    tool = payload.get('tool_name')
    ti = payload.get('tool_input')
    cwd = payload.get('cwd') or os.getcwd()
    if not tool or not isinstance(ti, dict):
        raise CouldNotRun('the payload has no tool_name / tool_input')
    if tool in WRITE_TOOLS:
        p = ti.get('file_path') or ti.get('notebook_path')
        if not p:
            raise CouldNotRun('%s call with no file_path' % tool)
        return [(tool, h) for h in resolved_hits(p, cwd)]
    if tool in COMMAND_TOOLS:
        cmd = ti.get('command')
        if cmd is None and tool == 'Monitor':
            # A WebSocket monitor, or one re-attached by task_id (the shape
            # the baseline replay found in cody's transcripts), runs no shell.
            return []
        if cmd is None:
            raise CouldNotRun('%s call with no command' % tool)
        return inspect_command(cmd, cwd)
    return []


def agent_name():
    """Logging only, never a decision input: the clone's identity marker."""
    git_dir = os.path.join(clone_root(), '.git')
    try:
        return io.open(os.path.join(git_dir, 'sairn-session'), encoding='utf-8').read().strip()
    except OSError:
        return 'UNKNOWN (no sairn-session marker under %s)' % git_dir


def log_block(payload, hits, reason):
    line = json.dumps({
        'ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'agent': agent_name(),
        'path': hits[0][1] if hits else None,
        'call_type': hits[0][0] if hits else (payload or {}).get('tool_name'),
        'more_hits': len(hits) - 1 if hits else 0,
        'tool': (payload or {}).get('tool_name'),
        'cwd': (payload or {}).get('cwd'),
        'session_id': (payload or {}).get('session_id'),
        'agent_id': (payload or {}).get('agent_id'),
        'agent_type': (payload or {}).get('agent_type'),
        'reason': reason,
        'criteria': CRITERIA_VERSION,
    }, ensure_ascii=False)
    failed = []
    for p in LOG_PATHS:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with io.open(p, 'a', encoding='utf-8', newline='\n') as fh:
                fh.write(line + '\n')
        except OSError as e:
            failed.append('%s (%s)' % (p, e))
    return failed


def main():
    payload = None
    try:
        payload = json.loads(sys.stdin.read())
        hits = decide(payload)
        if not hits:
            return 0
        reason = 'auditor-owned path'
        msg = ['REFUSED by builder_auditor_deny_hook: this %s call reaches a path the '
               'hover auditor owns. Build agents never edit, create, delete or reach '
               'into the auditor layer -- surface it in your handoff instead.'
               % payload.get('tool_name')]
        for call, p in hits[:5]:
            msg.append('  %s -> %s' % (call, p))
    except CouldNotRun as e:
        hits, reason = [], 'COULD NOT RUN: %s' % e
        msg = ['REFUSED (fail closed): builder_auditor_deny_hook %s. "Could not run" '
               'is never a pass.' % reason]
    except Exception as e:                                          # noqa: BLE001
        hits, reason = [], 'COULD NOT RUN: %s: %s' % (type(e).__name__, e)
        msg = ['REFUSED (fail closed): builder_auditor_deny_hook %s.' % reason]
    failed = log_block(payload, hits, reason)
    if failed:
        msg.append('  block-log write FAILED for: %s (the refusal stands)' % '; '.join(failed))
    sys.stderr.write('\n'.join(msg) + '\n')
    return 2


# ── SELFTEST ────────────────────────────────────────────────────────────────
def selftest():
    import shutil
    import tempfile
    global LOG_PATHS
    real_logs = LOG_PATHS
    t = tempfile.mkdtemp(prefix='bad-hook-')
    LOG_PATHS = (os.path.join(t, 'log', LOG_NAME),)
    bad = []
    n = [0]

    def arm(name, ok, got=None):
        n[0] += 1
        print('  %s %s%s' % ('ok  ' if ok else 'FAIL', name, '' if ok else '   got %r' % (got,)))
        if not ok:
            bad.append(name)

    try:
        clone = os.path.join(t, 'SAIRN-cc')
        skill = os.path.join(clone, '.claude', 'skills', 'sairn-hover-auditor')
        os.makedirs(skill)
        os.makedirs(os.path.join(clone, '.claude', 'claims'))
        os.makedirs(os.path.join(clone, 'tools'))
        tracked = os.path.join(clone, 'tools', 'audit_reader.py')
        io.open(tracked, 'w', newline='\n').write("SKILL = '.claude/skills/sairn-hover-auditor/'\n")
        g = ['git', '-C', clone, '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'core.autocrlf=false']
        git_ok = (subprocess.run(g + ['init', '-q'], capture_output=True).returncode == 0
                  and subprocess.run(g + ['add', 'tools/audit_reader.py'], capture_output=True).returncode == 0
                  and subprocess.run(g + ['commit', '-q', '-m', 't'], capture_output=True).returncode == 0)
        for f in (os.path.join(skill, 'SKILL.md'), os.path.join(clone, 'SAIRN-handoff-H1-b9.md'),
                  os.path.join(clone, 'tools', 'x.py'), os.path.join(clone, 'SAIRN-handoff-cc-b9.md')):
            io.open(f, 'w').write('x\n')
        patch = os.path.join(t, 'p.diff')
        io.open(patch, 'w').write('diff --git a/.claude/skills/sairn-hover-auditor/SKILL.md '
                                  'b/.claude/skills/sairn-hover-auditor/SKILL.md\n')
        okpatch = os.path.join(t, 'ok.diff')
        io.open(okpatch, 'w').write('diff --git a/tools/x.py b/tools/x.py\n+++ b/tools/x.py\n')
        script = os.path.join(t, 'sneak.py')
        io.open(script, 'w').write("p = '.claude/skills/' + 'sairn-' + 'hover-auditor/SKILL.md'\n")
        clean_script = os.path.join(t, 'fine.py')
        io.open(clean_script, 'w').write("print('hello')\n")
        link = os.path.join(t, 'innocent')
        try:
            os.symlink(skill, link, target_is_directory=True)
            have_link = True
        except (OSError, NotImplementedError):
            r = subprocess.run(['cmd', '/c', 'mklink', '/J', link, skill], capture_output=True)
            have_link = r.returncode == 0

        def d(tool, **ti):
            return decide({'tool_name': tool, 'tool_input': ti, 'cwd': clone})

        # DENY arms
        arm('Edit on the skill file (relative) is refused', bool(d('Edit', file_path='.claude/skills/sairn-hover-auditor/SKILL.md')))
        arm('Write with ../ traversal into the skill is refused',
            bool(d('Write', file_path=os.path.join(clone, 'tools', '..', '.claude', 'skills', 'sairn-hover-auditor', 'n.md'))))
        arm('Edit in an auditor CLONE is refused', bool(d('Edit', file_path=r'C:\Users\x\Documents\SAIRN-hover2\tools\a.py')))
        arm('Write to an auditor claim file is refused', bool(d('Write', file_path='.claude/claims/hover2.json')))
        arm("Write to an auditor's handoff is refused", bool(d('Write', file_path='SAIRN-handoff-H1-b9.md')))
        if have_link:
            arm('SYMLINK: Write through a link that resolves into the skill is refused',
                bool(decide({'tool_name': 'Write', 'tool_input': {'file_path': os.path.join(link, 'SKILL.md')}, 'cwd': t})))
            arm('SYMLINK: Bash redirect through the link is refused',
                bool(decide({'tool_name': 'Bash', 'tool_input': {'command': 'echo x > innocent/SKILL.md'}, 'cwd': t})))
        else:
            arm('SYMLINK arms COULD NOT RUN: neither os.symlink nor mklink /J worked here', False)
        arm('git checkout -- <skill file> is refused', bool(d('Bash', command='git checkout -- .claude/skills/sairn-hover-auditor/SKILL.md')))
        arm('git checkout -- .claude (an ANCESTOR) is refused', bool(d('Bash', command='git checkout -- .claude')))
        arm("git checkout -- '*.md' (a glob git matches onto SKILL.md) is refused", bool(d('Bash', command="git checkout -- '*.md'")))
        arm('git -C <clone> restore .claude/skills is refused', bool(decide({'tool_name': 'Bash', 'tool_input': {'command': 'git -C SAIRN-cc restore .claude/skills'}, 'cwd': t})))
        arm('git mv out of the skill dir is refused', bool(d('Bash', command='git mv .claude/skills/sairn-hover-auditor/SKILL.md x.md')))
        arm('git apply of a patch touching the skill is refused', bool(d('Bash', command='git apply %s' % patch)))
        arm('cat patch | git apply is refused', bool(d('Bash', command='cat %s | git apply' % patch)))
        arm('cd into the skill dir then write is refused', bool(d('Bash', command='cd .claude/skills && echo x > sairn-hover-auditor/a')))
        arm('a heredoc naming the skill path is refused',
            bool(d('Bash', command="python - <<'EOF'\nopen('.claude/skills/sairn-hover-auditor/SKILL.md','a').write('x')\nEOF")))
        arm("'sairn-'+'hover' concatenation is refused (compact pass)",
            bool(d('Bash', command="python -c \"open('.claude/skills/'+'sairn-'+'hover-auditor/SKILL.md','a')\"")))
        arm('quote-split sairn-ho""ver is refused', bool(d('Bash', command='touch .claude/skills/sairn-ho""ver-auditor/z')))
        arm('a subprocess in bash -c is refused', bool(d('Bash', command='bash -c "cp x .claude/skills/sairn-hover-auditor/"')))
        arm('an UNTRACKED script that names the path is read and refused', bool(d('Bash', command='python %s' % script)))
        arm('PowerShell Set-Content into an auditor clone is refused',
            bool(d('PowerShell', command=r'Set-Content C:\Users\x\Documents\SAIRN-hover\a.txt x')))
        arm('a glob that expands onto the skill is refused', bool(d('Bash', command='touch .claude/skills/*/SKILL.md')))
        arm('backslash Windows path to the skill is refused', bool(d('Bash', command=r'echo x >> .claude\skills\sairn-hover-auditor\SKILL.md')))
        # ALLOW arms -- each pairs with a deny arm above (item 20: both directions)
        arm('Edit on tools/x.py is allowed', d('Edit', file_path='tools/x.py') == [], d('Edit', file_path='tools/x.py'))
        arm("Write to a BUILDER's handoff is allowed", d('Write', file_path='SAIRN-handoff-cc-b9.md') == [])
        arm('Write to a builder claim file is allowed', d('Write', file_path='.claude/claims/hank.json') == [])
        arm('git checkout -- tools/x.py is allowed', d('Bash', command='git checkout -- tools/x.py') == [],
            d('Bash', command='git checkout -- tools/x.py'))
        arm("git checkout -- 'tools/*.py' is allowed", d('Bash', command="git checkout -- 'tools/*.py'") == [],
            d('Bash', command="git checkout -- 'tools/*.py'"))
        arm('git checkout main (a branch, not a path) is allowed', d('Bash', command='git checkout main') == [])
        arm('git pull is allowed (sync is not reaching in)', d('Bash', command='git pull --ff-only origin main') == [])
        arm('git apply of a patch on tools/ is allowed', d('Bash', command='git apply %s' % okpatch) == [])
        arm('python on an untracked script that does not name the path is allowed',
            d('Bash', command='python %s' % clean_script) == [], d('Bash', command='python %s' % clean_script))
        arm('python tools/hover_separation_audit.py (a hover-named builder-run tool) is allowed',
            d('Bash', command='python tools/hover_separation_audit.py --check') == [])
        if git_ok:
            arm('a CLEAN TRACKED tool that names the path may run (reviewed code)',
                d('Bash', command='python tools/audit_reader.py') == [], d('Bash', command='python tools/audit_reader.py'))
            io.open(tracked, 'a', newline='\n').write('# modified\n')
            arm('...the SAME tool once MODIFIED is read and refused',
                bool(d('Bash', command='python tools/audit_reader.py')))
            arm('node --check on that modified file is allowed (a syntax check runs nothing)',
                d('Bash', command='node --check tools/audit_reader.py') == [])
            # Baseline-replay shapes (cc b66): each was a would-be refusal of a
            # harmless call in a real builder transcript.
            io.open(os.path.join(clone, '.claude', 'claims', 'hover.json'), 'w').write('{}')
            subprocess.run(g + ['add', '-A'], capture_output=True)
            subprocess.run(g + ['commit', '-q', '-m', 'all'], capture_output=True)
            arm('git checkout -- . with every auditor file CLEAN is allowed (it changes none)',
                d('Bash', command='git checkout -q -- .') == [], d('Bash', command='git checkout -q -- .'))
            arm('git restore --staged . (index only) is allowed', d('Bash', command='git restore --staged .') == [])
            arm('git mv .claude elsewhere is refused even when clean (mv moves them)',
                bool(d('Bash', command='git mv .claude claude-old')))
            arm('cat .claude/claims/*.json (a READ glob) is allowed', d('Bash', command='cat .claude/claims/*.json') == [],
                d('Bash', command='cat .claude/claims/*.json'))
            arm('...but echo > .claude/claims/hov*.json (a WRITE glob) is refused',
                bool(d('Bash', command='echo x > .claude/claims/hov*.json')))
            io.open(os.path.join(skill, 'SKILL.md'), 'a').write('dirty\n')
            arm('git checkout -- . with an auditor file DIRTY is refused (it would rewrite it)',
                bool(d('Bash', command='git checkout -q -- .')))
        else:
            arm('tracked-script arms COULD NOT RUN: git init/commit failed in the temp dir', False)
        arm('Monitor re-attached by task_id (no command) is allowed',
            decide({'tool_name': 'Monitor', 'tool_input': {'task_id': 'x'}, 'cwd': clone}) == [])
        arm('Write into docs/hover-audit-log/ is refused', bool(d('Write', file_path='docs/hover-audit-log/x.jsonl')))
        arm('Bash append to docs/hover-evidence/ is refused', bool(d('Bash', command='echo x >> docs/hover-evidence/e.txt')))
        arm('docs/hover-something-else/ is NOT auditor scope', d('Write', file_path='docs/hover-routing-notes.md') == [])
        man = os.path.join(t, 'manifest.json')
        io.open(man, 'w').write(json.dumps({'auditor_paths': ['.claude/skills/sairn-hover-auditor/', 'docs/zz-new-auditor-dir/']}))
        got = manifest_auditor_paths(man)
        p2, _t2, _r2 = build_scope(set(BUILTIN_AUDITOR_DIRS) | set(got or ()))
        arm('a dir ADDED to the manifest is in scope with no edit to this file',
            any(rx.search('/c/x/docs/zz-new-auditor-dir/a') for rx in p2), got)
        arm('an unreadable manifest reads as None (the built-in floor still applies)',
            manifest_auditor_paths(os.path.join(t, 'absent.json')) is None)
        p3, _t3, _r3 = build_scope(BUILTIN_AUDITOR_DIRS)
        arm('...and the floor alone still refuses the skill dir and both docs dirs',
            all(any(rx.search(x) for rx in p3) for x in ('/c/.claude/skills/sairn-hover-auditor/s.md',
                                                         '/c/docs/hover-audit-log/a', '/c/docs/hover-evidence/b')))
        arm('THE LIVE MANIFEST was read and its entries are in scope (not only the floor)',
            MANIFEST_DIRS is not None and set(MANIFEST_DIRS) <= set(AUDITOR_DIRS), (MANIFEST, MANIFEST_DIRS))
        arm('Read-type tools are not inspected', decide({'tool_name': 'Read', 'tool_input': {'file_path': os.path.join(skill, 'SKILL.md')}, 'cwd': clone}) == [])
        arm('a builder-to-builder edit (another clone) is allowed', d('Edit', file_path=r'C:\Users\x\Documents\SAIRN-hank\tools\a.py') == [])
        # FAIL CLOSED
        for name, pl in (('a non-object payload', []), ('no tool_input', {'tool_name': 'Bash'}),
                         ('Bash with no command', {'tool_name': 'Bash', 'tool_input': {}}),
                         ('Edit with no file_path', {'tool_name': 'Edit', 'tool_input': {}})):
            try:
                decide(pl)
                arm('%s is COULD NOT RUN' % name, False, 'allowed')
            except CouldNotRun:
                arm('%s is COULD NOT RUN' % name, True)
        # END TO END through main(): exit code, stderr, and the log line
        for cmdline, want in (('git checkout -- .claude/skills/sairn-hover-auditor/SKILL.md', 2),
                              ('git status', 0), ('{not json', 2)):
            body = cmdline if cmdline.startswith('{') else json.dumps(
                {'tool_name': 'Bash', 'tool_input': {'command': cmdline}, 'cwd': clone,
                 'session_id': 's', 'agent_id': 'sub-1'})
            r = subprocess.run([sys.executable, os.path.abspath(__file__), '--_log-to', LOG_PATHS[0]],
                               input=body, capture_output=True, text=True)
            arm('main() exit %d for %r' % (want, cmdline[:40]), r.returncode == want, (r.returncode, r.stderr[:200]))
            if want == 0:
                arm('...and the allow path is SILENT', r.stdout == '' and r.stderr == '', (r.stdout, r.stderr))
        try:
            rows = [json.loads(x) for x in io.open(LOG_PATHS[0], encoding='utf-8')]
        except OSError:
            rows = []
        arm('two refusals logged, the allow not logged', len(rows) == 2, len(rows))
        arm('a log row carries ts, agent, path, call_type',
            bool(rows) and all(rows[0].get(k) for k in ('ts', 'agent', 'path', 'call_type')), rows[:1])
        arm('a subagent call logs its agent_id', bool(rows) and rows[0].get('agent_id') == 'sub-1', rows[:1])
        arm('the could-not-run refusal is logged with its reason',
            len(rows) == 2 and rows[1]['reason'].startswith('COULD NOT RUN'), rows[1:])
    finally:
        LOG_PATHS = real_logs
        shutil.rmtree(t, ignore_errors=True)
    print('BUILDER AUDITOR DENY HOOK SELFTEST -- criteria %s -- %d arm(s), %d failed'
          % (CRITERIA_VERSION, n[0], len(bad)))
    return 1 if bad else 0


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        sys.exit(selftest())
    if '--_log-to' in sys.argv:                 # selftest only: keep test rows out of the real log
        LOG_PATHS = (sys.argv[sys.argv.index('--_log-to') + 1],)
    sys.exit(main())
