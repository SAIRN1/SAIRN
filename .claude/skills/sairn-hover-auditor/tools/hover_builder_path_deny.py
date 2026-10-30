#!/usr/bin/env python
"""hover_builder_path_deny.py -- PreToolUse deny-list: the hover auditor's
"audit and flag, never build" rule, refused BEFORE execution instead of
remembered. Own tool, own scope. Built H1 b98 on Michael's instruction.

    python hover_builder_path_deny.py --clone <this clone>      # hook entry, JSON on stdin
    python hover_builder_path_deny.py --selftest                # arms + planted defects

WHAT IT REFUSES (exit 2, one line to stderr, one line to the shared block log):
  1. Edit / Write / MultiEdit / NotebookEdit whose REAL path (symlinks, junctions,
     `..`, case and git-bash `/c/...` spellings resolved first) is builder-owned.
  2. Bash text that WRITES to a builder-owned path: redirects, rm/mv/cp/touch/tee/
     sed -i/..., `cd <builder>` followed by a relative write, interpreter code
     (python -c, node -e, heredoc bodies) that opens/writes/spawns/imports with a
     builder path in it, and `git` subcommands whose pathspec reaches a builder path
     (checkout, restore, mv, rm, add, reset --hard, clean, apply/am, stash push,
     commit -a) or that mutate a foreign clone through `git -C`.
  3. Bash text that EXECUTES builder code (the b91 no-builder-execution rule, confirmed
     in force from b97 on): python/node/bash/... <builder script>, ./builder-script,
     npm/make runners with a builder cwd. The one exemption is
     `sairn_claim.py check|claim|release|own|list`, chat's b92 ruling.
READING is allowed on purpose (standing rule: "you may read anything"): grep, cat, sed -n,
git show/log/diff, cp FROM a builder file into a scratch dir.

BUILDER-OWNED = every sibling clone under Documents (SAIRN-hank/cc/cody/fourth/hover2/SAIRN),
the shared SAIRN-SESSION-LOCKS dir, and everything in THIS clone that the hover scope
manifest (~/SAIRN-SESSION-LOCKS/hover-scope-manifest.json) does not allow. SELF-PROTECTED
(the guard cannot be removed by the agent it guards): this script, both settings files,
the manifest, the block log, .git internals.

WHAT IT CANNOT DO, STATED HERE SO NOBODY READS IT AS MORE. It reads the TEXT of a tool call;
it is not a sandbox. A script that is already on disk and writes a builder path from inside
(python some_scratch.py) is refused only if the script's own path or the call's text names a
builder path; a path assembled at run time inside it is invisible. An unresolvable path
($(...), an unset $VAR) in a WRITE or EXEC position is refused (fail closed) rather than
guessed. Hooks that exit 1, or a missing python, are non-blocking in the harness: this script
catches its own exceptions and exits 2, and `python <missing file>` exits 2 too, but a missing
interpreter does not. Only the clone that wires the hook is covered: cc, chat and the other
clones appear in the shared log only for the agents that wire it.

BLOCK LOG: ~/SAIRN-SESSION-LOCKS/deny-blocks.log, append-only, one tab-separated line per
refusal: UTC timestamp, agent, path, call type, reason. Outside every clone and outside any
settings.json. A failure to write it is reported on stderr and does NOT lift the refusal.
"""
import sys
_HOOK_DIR = __file__.replace('\\', '/').rsplit('/', 1)[0].lower()
# b117 (H2 cold read b98, class shadow-import): the directory of this script is sys.path[0], so a json.py or os.py dropped beside the
# hook would be IMPORTED by the hook. Nothing here imports from its own directory, so it is removed before any other import.
sys.path[:] = [_p for _p in sys.path if _p and _p.replace('\\', '/').rstrip('/').lower() != _HOOK_DIR]
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

DEFECTS = set()          # selftest only: named mechanisms switched off to prove each arm bites

HOME = os.path.expanduser('~')
LOCKS = os.path.join(HOME, 'SAIRN-SESSION-LOCKS')
BLOCK_LOG = os.path.join(LOCKS, 'deny-blocks.log')
MANIFEST = os.path.join(LOCKS, 'hover-scope-manifest.json')
DELIVERABLE = re.compile(r'^sairn-(handoff|digest|report|latest)-h1[^/]*$')   # repo-root files, lower-cased
CARVEOUT = ('.claude/settings.json', 'docs/scrutiny-flags.json')              # foreign files the claim recipe stashes
CLAIM_OK = {'check', 'claim', 'release', 'own', 'list'}
# Read-only checkers this clone's hover may RUN (Michael, b112 and b115): each reads a file or a git blob and writes nothing.
# Matched on the REAL path of the script inside THIS clone's tools/, so a same-named script in a sibling clone stays refused.
EXEC_OK_TOOLS = ('digest_lint.py', 'sql_placeholder_check.py')

FILE_TOOLS = ('Edit', 'Write', 'MultiEdit', 'NotebookEdit')
SHELL_TOOLS = ('Bash', 'PowerShell')

ALL_ARGS_WRITE = {'rm', 'rmdir', 'del', 'erase', 'touch', 'mkdir', 'md', 'truncate', 'chmod', 'chown',
                  'shred', 'unlink', 'tee', 'ln', 'mklink', 'new-item', 'set-content', 'add-content',
                  'out-file', 'remove-item', 'clear-content', 'rename-item', 'move', 'mv', 'ren', 'rename',
                  'move-item', 'attrib', 'icacls', 'takeown', 'dos2unix', 'unix2dos'}
DEST_LAST = {'cp', 'copy', 'xcopy', 'rsync', 'install', 'copy-item', 'scp'}
INTERPRETERS = {'python', 'python3', 'py', 'pythonw', 'node', 'nodejs', 'perl', 'ruby', 'php', 'lua', 'deno',
                'bun', 'powershell', 'pwsh', 'cmd', 'wscript', 'cscript', 'awk', 'gawk'}
SHELLS = {'bash', 'sh', 'zsh', 'dash', 'ksh'}
RUNNERS = {'npm', 'npx', 'pnpm', 'yarn', 'make', 'cargo', 'go', 'dotnet', 'mvn', 'gradle'}
WRAPPERS = {'time', 'nohup', 'command', 'builtin', 'exec', 'sudo', 'env', 'nice', 'timeout', 'stdbuf'}
GIT_READ = {'log', 'show', 'diff', 'status', 'ls-files', 'ls-tree', 'cat-file', 'rev-parse', 'rev-list', 'grep',
            'blame', 'shortlog', 'describe', 'name-rev', 'merge-base', 'for-each-ref', 'show-ref', 'ls-remote',
            'reflog', 'count-objects', 'diff-tree', 'diff-index', 'cherry', 'whatchanged', 'version', 'help'}
GIT_VALUE_OPTS = {'-m', '-F', '-C', '-c', '--message', '--file', '--author', '--date', '--template', '-t',
                  '--cleanup', '--reuse-message', '--reedit-message', '--fixup', '--squash', '-b', '-B',
                  '--orphan', '--pathspec-from-file', '--source', '-s', '-S'}

WRITE_RE = re.compile(
    r"""open\s*\([^)]*?,\s*(?:mode\s*=\s*)?['"][^'"]*[wax+][^'"]*['"]|write_text|write_bytes|\.write\s*\(|"""
    r"""\bfs\.\w*(?:write|append|unlink|rm|rename|copy|mkdir|truncate|symlink|chmod)\w*|writeFile|appendFile|"""
    r"""shutil\.\w+|os\.(?:remove|rename|replace|unlink|makedirs|mkdir|rmdir|system|popen|chmod|symlink|link|"""
    r"""truncate|exec\w*|spawn\w*)|\bsubprocess\b|Popen|check_output|check_call|child_process|execSync|spawnSync|"""
    r"""\bspawn\b|Set-Content|Add-Content|Out-File|Remove-Item|Move-Item|Copy-Item|New-Item|Rename-Item|"""
    r"""Clear-Content|\[IO\.File\]::|sys\.path|spec_from_file_location|runpy|importlib|execfile|"""
    r"""require\s*\(\s*['"]\.{0,2}[\\/]|inplace|-delete|-exec\b|\bxargs\b""", re.I)
RUN_SPLIT = re.compile(r"[^\s'\"`;|&<>(),=\[\]{}]+")
BARE_FILE = re.compile(r'^[\w.-]+\.(?:html|js|mjs|py|json|md|sql|css|ts|sh|yml|yaml|toml|txt|cfg|ini|bak)$')


class Unresolvable(Exception):
    pass


def _under(a, b):
    return a == b or a.startswith(b.rstrip('\\/') + os.sep)


class Policy:
    def __init__(self, own, foreign, allowed, locks, protected):
        self.own = self.real(own)
        self.foreign = [r for r in (self.real(f) for f in foreign) if r != self.own]
        self.allowed = [a.lower().replace('\\', '/') for a in allowed]
        self.locks = self.real(locks)
        self.protected = {self.real(p) for p in protected}
        self.claim = self.real(os.path.join(own, 'tools', 'sairn_claim.py'))
        self.exec_ok = {self.real(os.path.join(own, 'tools', n)) for n in EXEC_OK_TOOLS}
        self.topnames = set(n.lower() for n in os.listdir(own)) if os.path.isdir(own) else set()

    @staticmethod
    def real(p):
        p = os.path.abspath(p) if 'no_realpath' in DEFECTS else os.path.realpath(p)
        p = os.path.normcase(p)
        return p if len(p) <= 3 else p.rstrip('\\/')

    @classmethod
    def live(cls, clone):
        docs = os.path.dirname(os.path.abspath(clone))
        foreign = [d for d in glob.glob(os.path.join(docs, 'SAIRN*')) if os.path.isdir(os.path.join(d, '.git'))]
        with open(MANIFEST, encoding='utf-8') as f:
            allowed = json.load(f)['allowed_prefixes']
        hc = os.path.join(HOME, '.claude')
        prot = [os.path.join(clone, '.claude', 'settings.json'), os.path.join(clone, '.claude', 'settings.local.json'),
                os.path.join(hc, 'settings.json'), os.path.join(hc, 'settings.local.json'),
                os.path.abspath(__file__), MANIFEST, BLOCK_LOG]
        return cls(clone, foreign, allowed, LOCKS, prot)

    def classify(self, rp):
        """'builder' | 'self' | None for an already-resolved path (file or directory)."""
        if any(_under(rp, r) for r in self.foreign):
            return 'builder'
        if rp in self.protected:
            return 'self'
        if _under(rp, self.locks):
            return 'builder'
        if _under(rp, self.own):
            rel = rp[len(self.own):].lstrip('\\/').replace('\\', '/')
            if rel == '':
                return 'builder'
            if rel == '.git' or rel.startswith('.git/'):
                return 'self'
            if DELIVERABLE.match(rel):
                return None
            for pre in self.allowed:
                if rel == pre.rstrip('/') or (pre.endswith('/') and rel.startswith(pre)) or rel == pre:
                    return None
            return 'builder'
        if any(_under(r, rp) for r in self.foreign + [self.own, self.locks]):
            return 'builder'                       # a directory that contains a clone
        return None

    # ---------- path resolution ----------
    def res(self, tok, cwd, env):
        t = tok
        if '`' in t or '$(' in t:
            raise Unresolvable(tok)

        def sub(m):
            name = m.group(1) or m.group(2) or m.group(3)
            v = env.get(name)
            if v is None:
                v = os.environ.get(name)
            if v is None:
                raise Unresolvable(tok)
            return v
        t = re.sub(r'\$\{(\w+)\}|\$(\w+)|%(\w+)%', sub, t)
        if t.startswith('~'):
            t = HOME + t[1:]
        m = re.match(r'^/mnt/([a-zA-Z])(/.*)?$', t) or re.match(r'^/([a-zA-Z])(/.*)?$', t)
        if m:
            t = m.group(1).upper() + ':' + (m.group(2) or '\\')
        if not os.path.isabs(t) or (t.startswith(('/', '\\')) and not re.match(r'^[A-Za-z]:', t)):
            if cwd is None:
                raise Unresolvable(tok)
            if not re.match(r'^[A-Za-z]:', t) and not t.startswith(('/', '\\')):
                t = os.path.join(cwd, t)
        return self.real(t)

    def cls_tok(self, tok, cwd, env):
        """classify a path-ish token, honouring globs by testing the directory part."""
        m = re.search(r'[*?\[{]', tok)
        if m:
            head = tok[:m.start()]
            k = max(head.rfind('/'), head.rfind('\\'))
            tok = head[:k] if k > 0 else (head[:1] if k == 0 else '.')
            if tok == '':
                tok = '.'
        return self.classify(self.res(tok, cwd, env)), self.res(tok, cwd, env)


# ---------------------------------------------------------------- tokenizer
def tokenize(cmd):
    """-> list of segments; seg = dict(words=[(val, raw, sq)], redirs=[(op, target)], heredoc=[body], stdin=None)."""
    toks, i, n = [], 0, len(cmd)
    buf, raw, has, sq = [], [], False, True
    pending = []                                 # heredoc tags awaiting a body: [tag, strip_tabs, tokindex]

    def flush():
        nonlocal buf, raw, has, sq
        if has:
            toks.append(('w', ''.join(buf), ''.join(raw), sq))
        buf, raw, has, sq = [], [], False, True

    while i < n:
        c = cmd[i]
        if c == "'":
            j = cmd.find("'", i + 1)
            j = n if j < 0 else j
            buf.append(cmd[i + 1:j]); raw.append(cmd[i:j + 1]); has = True
            i = j + 1
            continue
        if c == '"':
            j = i + 1
            while j < n and cmd[j] != '"':
                j += 2 if cmd[j] == '\\' and j + 1 < n and cmd[j + 1] in '"$`' else 1
            buf.append(cmd[i + 1:j].replace('\\"', '"')); raw.append(cmd[i:j + 1]); has = True; sq = False
            i = j + 1
            continue
        if c == '`':
            j = cmd.find('`', i + 1)
            j = n - 1 if j < 0 else j
            buf.append(cmd[i:j + 1]); raw.append(cmd[i:j + 1]); has = True; sq = False
            i = j + 1
            continue
        if c == '\\' and i + 1 < n and cmd[i + 1] == '\n':
            i += 2
            continue
        if c in ' \t\r':
            flush(); i += 1
            continue
        if c == '#' and not has:
            while i < n and cmd[i] != '\n':
                i += 1
            continue
        if c == '\n':
            flush(); toks.append(('op', '\n')); i += 1
            for p in pending:                    # read heredoc bodies in order
                body = []
                while i < n:
                    e = cmd.find('\n', i)
                    e = n if e < 0 else e
                    line = cmd[i:e]
                    i = e + 1
                    if (line.strip('\t\r') if p[1] else line.rstrip('\r')) == p[0]:
                        break
                    body.append(line)
                toks[p[2]] = ('heredoc', '\n'.join(body), p[0], True)
            pending = []
            continue
        two = cmd[i:i + 2]
        three = cmd[i:i + 3]
        if c in ';()' or two in ('&&', '||') or (c == '|') or (c == '&' and two != '&>'):
            flush()
            op = two if two in ('&&', '||') else c
            toks.append(('op', op)); i += len(op)
            continue
        if c in '<>' or two == '&>':
            if has and ''.join(buf).isdigit() and not raw[0][:1] in '\'"':
                buf, raw, has = [], [], False   # an fd number: 2>file
            flush()
            if three == '<<<':
                op = '<<<'
            elif two == '<<':
                op = '<<-' if three == '<<-' else '<<'
            elif three == '&>>' or three == '>>|':
                op = three
            elif two in ('>>', '>|', '>&', '&>', '<&'):
                op = two
            else:
                op = c
            toks.append(('op', op)); i += len(op)
            if op in ('<<', '<<-'):
                pending.append(['', op == '<<-', len(toks)])
                toks.append(('heredoc', '', '', True))          # placeholder, body filled at newline
                while i < n and cmd[i] in ' \t':
                    i += 1
                j = i
                q = cmd[j:j + 1]
                if q in ('"', "'"):
                    e = cmd.find(q, j + 1); e = n if e < 0 else e
                    pending[-1][0] = cmd[j + 1:e]; i = e + 1
                else:
                    while j < n and cmd[j] not in ' \t\r\n;&|()<>':
                        j += 1
                    pending[-1][0] = cmd[i:j]; i = j
            continue
        buf.append(c); raw.append(c); has = True
        i += 1
    flush()
    for p in pending:                            # unterminated: body is whatever was left (nothing)
        pass

    segs, cur = [], {'words': [], 'redirs': [], 'heredoc': [], 'stdin': None}

    def close():
        nonlocal cur
        if cur['words'] or cur['redirs'] or cur['heredoc']:
            segs.append(cur)
        cur = {'words': [], 'redirs': [], 'heredoc': [], 'stdin': None}
    k = 0
    while k < len(toks):
        t = toks[k]
        if t[0] == 'op' and t[1] in ('>', '>>', '>|', '&>', '&>>', '>>|', '>&'):
            nxt = toks[k + 1] if k + 1 < len(toks) else None
            if nxt and nxt[0] == 'w':
                if not (t[1] == '>&' and re.fullmatch(r'\d+|-', nxt[1])):
                    cur['redirs'].append((t[1], nxt[1]))
                k += 2
                continue
        elif t[0] == 'op' and t[1] == '<':
            nxt = toks[k + 1] if k + 1 < len(toks) else None
            if nxt and nxt[0] == 'w':
                cur['stdin'] = nxt[1]; k += 2
                continue
        elif t[0] == 'op' and t[1] in ('<<', '<<-'):
            hd = toks[k + 1] if k + 1 < len(toks) else None
            if hd and hd[0] == 'heredoc':
                cur['heredoc'].append(hd[1]); k += 2
                continue
        elif t[0] == 'op':
            close(); k += 1
            continue
        elif t[0] == 'w':
            cur['words'].append((t[1], t[2], t[3]))
        k += 1
    close()
    return segs


def substitutions(raw):
    """inner command strings of $(...) and `...` found in a token's raw text."""
    out, i = [], 0
    while i < len(raw):
        if raw.startswith('$(', i):
            depth, j = 1, i + 2
            while j < len(raw) and depth:
                depth += raw[j] == '('
                depth -= raw[j] == ')'
                j += 1
            out.append(raw[i + 2:j - 1]); i = j
        elif raw[i] == '`':
            j = raw.find('`', i + 1)
            if j < 0:
                break
            out.append(raw[i + 1:j]); i = j + 1
        else:
            i += 1
    return out


# ---------------------------------------------------------------- analysis
def patch_targets(text):
    out = []
    for m in re.finditer(r'^(?:\+\+\+|---) (?:[ab]/)?(\S+)|^diff --git a/(\S+) b/(\S+)|^rename (?:to|from) (\S+)', text, re.M):
        out.extend(g for g in m.groups() if g and g != '/dev/null')
    return out


class Analyzer:
    def __init__(self, pol, cwd):
        self.p, self.cwd, self.env, self.depth = pol, cwd, {}, 0

    def bad(self, path, why):
        return (path, why)

    def check(self, cmd):
        if self.depth > 6:
            return self.bad('?', 'command nesting too deep to inspect')
        for seg in tokenize(cmd):
            v = self.segment(seg)
            if v:
                return v
        return None

    def sub_check(self, cmd):
        a = Analyzer(self.p, self.cwd)
        a.env, a.depth = dict(self.env), self.depth + 1
        return a.check(cmd)

    # one resolved path in a write/exec position
    def wpos(self, tok, why):
        try:
            k, rp = self.p.cls_tok(tok, self.cwd, self.env)
        except Unresolvable:
            return self.bad(tok, why + ': path not resolvable (refused, fail closed)')
        return self.bad(rp, why) if k else None

    def segment(self, seg):
        words = [w[0] for w in seg['words']]
        if 'no_subst' not in DEFECTS:
            for _, raw, sq in seg['words']:
                if not (raw.startswith("'") and raw.endswith("'")):
                    for inner in substitutions(raw):
                        v = self.sub_check(inner)
                        if v:
                            return v
        if 'no_redirect' not in DEFECTS:
            for op, tgt in seg['redirs']:
                if tgt in ('/dev/null', 'nul', 'NUL', '/dev/stderr', '/dev/stdout'):
                    continue
                v = self.wpos(tgt, 'redirect (%s) writes a builder-owned path' % op)
                if v:
                    return v
        while words and re.match(r'^[A-Za-z_]\w*=', words[0]):
            k, _, val = words.pop(0).partition('=')
            if not words:
                self.env[k] = val
        if not words:
            return None
        while words and os.path.basename(words[0]).lower().replace('.exe', '') in WRAPPERS:
            w = os.path.basename(words.pop(0)).lower()
            while words and (words[0].startswith('-') or re.match(r'^[A-Za-z_]\w*=', words[0]) or (w == 'timeout' and re.match(r'^[\d.]+[smhd]?$', words[0]))):
                words.pop(0)
        if not words:
            return None
        prog = os.path.basename(words[0]).lower().replace('.exe', '')
        args = words[1:]
        if prog in ('cd', 'pushd', 'chdir', 'set-location'):
            if 'no_cd_track' in DEFECTS:
                return None
            if not args or args[0] == '-':
                self.cwd = None
                return None
            try:
                self.cwd = self.p.res(args[0], self.cwd, self.env)
            except Unresolvable:
                self.cwd = None
            return None
        if prog == 'git' and 'no_git' not in DEFECTS:
            v = self.git(args, seg)
            if v:
                return v
            return None
        if prog in ALL_ARGS_WRITE:
            for a in args:
                if a.startswith('-') and prog != 'del':
                    continue
                v = self.wpos(a, prog + ' on a builder-owned path')
                if v:
                    return v
            return None
        if prog in DEST_LAST:
            pos = [a for a in args if not a.startswith('-')]
            dests = []
            for j, a in enumerate(args):
                if a in ('-t', '--target-directory') and j + 1 < len(args):
                    dests.append(args[j + 1])
                elif a.startswith('--target-directory='):
                    dests.append(a.split('=', 1)[1])
            if not dests and pos:
                dests.append(pos[1] if prog == 'robocopy' and len(pos) > 1 else pos[-1])
            for d in dests:
                v = self.wpos(d, prog + ' destination is a builder-owned path')
                if v:
                    return v
            return None
        if prog == 'robocopy':
            pos = [a for a in args if not a.startswith(('-', '/'))]
            return self.wpos(pos[1], 'robocopy destination is a builder-owned path') if len(pos) > 1 else None
        if prog == 'sed' or prog == 'perl' and any(re.match(r'^-\w*i', a) for a in args):
            if any(re.match(r'^-[A-Za-z]*i|^--in-place', a) for a in args):
                for a in args:
                    if not a.startswith('-'):
                        v = self.wpos(a, prog + ' -i edits a builder-owned path')
                        if v:
                            return v
            return None
        if prog in ('curl', 'wget'):
            for j, a in enumerate(args):
                if a in ('-o', '-O', '--output', '--output-document') and j + 1 < len(args):
                    v = self.wpos(args[j + 1], prog + ' output file')
                    if v:
                        return v
            return None
        if prog == 'dd':
            for a in args:
                if a.startswith('of='):
                    return self.wpos(a[3:], 'dd of=')
            return None
        if prog == 'patch':
            return self.patch_check(args, seg, 'patch')
        if prog in SHELLS or prog in INTERPRETERS or prog in RUNNERS or prog in ('eval', 'source', '.', 'find', 'xargs'):
            return self.run(prog, args, seg)
        # direct execution of a path-like program
        if ('/' in words[0] or '\\' in words[0]) and 'no_exec' not in DEFECTS:
            return self.exec_check(words[0], args)
        return None

    # ---- interpreters / shells / runners
    def code_scan(self, text, why):
        text = text.replace('\\\\', '\\')
        cands = []
        for run in RUN_SPLIT.findall(text):
            run = run.rstrip('.,:')
            if '/' in run or '\\' in run or re.match(r'^[A-Za-z]:', run):
                cands.append(run)              # a whole path run: never its fragments
            elif BARE_FILE.match(run) or run.lower() in self.p.topnames:
                cands.append(run)
        hit = None
        for c in cands:
            try:
                k, rp = self.p.cls_tok(c, self.cwd, self.env)
            except Unresolvable:
                continue
            if k:
                hit = rp
                break
        if hit and WRITE_RE.search(text):
            return self.bad(hit, why + ' (code text names a builder path and writes, spawns or imports)')
        return None

    def exec_check(self, script, rest):
        try:
            k, rp = self.p.cls_tok(script, self.cwd, self.env)
        except Unresolvable:
            return self.bad(script, 'script path not resolvable (refused, fail closed)')
        if not k:
            return None
        if rp == self.p.claim and rest and rest[0] in CLAIM_OK:
            return None
        if rp in self.p.exec_ok and 'no_exec_ok' not in DEFECTS:
            return None
        return self.bad(rp, 'executes builder code (no-builder-execution rule)')

    def run(self, prog, args, seg):
        for body in seg['heredoc']:
            if 'no_heredoc' in DEFECTS:
                continue
            if prog in SHELLS or prog == 'eval':
                v = self.sub_check(body)
            else:
                v = self.code_scan(body, prog + ' heredoc')
            if v:
                return v
        if prog in ('find',):
            return self.code_scan(' '.join(args), 'find')
        if prog == 'xargs':
            verb = next((x for x in args if not x.startswith('-')), '')
            verb = os.path.basename(verb).lower().replace('.exe', '')
            if verb in ALL_ARGS_WRITE or verb in DEST_LAST or verb in INTERPRETERS or verb in SHELLS or verb in ('sed', 'perl', 'git'):
                return self.bad('?', 'xargs feeds paths it cannot show to %s (refused, fail closed)' % verb)
            return None
        if prog in ('source', '.'):
            return self.exec_check(args[0], args[1:]) if args and 'no_exec' not in DEFECTS else None
        if prog == 'eval':
            return self.sub_check(' '.join(args))
        if prog in RUNNERS:
            try:
                k = self.p.classify(self.p.real(self.cwd)) if self.cwd else 'builder'
            except Exception:
                k = 'builder'
            return self.bad(self.cwd or '?', prog + ' runs builder code from a builder cwd') if k else None
        if prog in ('powershell', 'pwsh') and any(re.match(r'^-e(nc|ncodedcommand)?$', a, re.I) for a in args):
            return self.bad('?', 'encoded PowerShell command cannot be inspected')
        i, code, script, mod, check_only = 0, None, None, None, False
        while i < len(args):
            a = args[i]
            if a in ('-c', '-e', '--eval', '-p', '--print', '-Command', '/c', '/C', '-command') and i + 1 < len(args):
                code = ' '.join(args[i + 1:]); break
            if a == '-m' and i + 1 < len(args):
                mod = args[i + 1]; script = None; i += 2
                break
            if a in ('--check', '-check') and prog in ('node', 'nodejs'):
                check_only = True
            if a in ('-W', '-X', '-r', '--require', '-File', '-file') and i + 1 < len(args):
                if a in ('-File', '-file'):
                    script = args[i + 1]; i += 1; break
                i += 2
                continue
            if not a.startswith('-') and not a.startswith('/') or (a.startswith('/') and prog not in ('cmd',)):
                script = a; i += 1
                break
            i += 1
        rest = args[i:]
        if code is not None:
            if prog in SHELLS:
                return self.sub_check(code)
            return self.code_scan(code, prog + ' -c/-e code')
        if mod:
            if mod in ('pytest', 'unittest', 'py_compile', 'compileall', 'doctest', 'runpy'):
                builder_arg = any(self.p.cls_tok(x, self.cwd, self.env)[0] for x in rest if not x.startswith('-')
                                  if not _unres(self.p, x, self.cwd, self.env))
                try:
                    in_builder = bool(self.cwd and self.p.classify(self.p.real(self.cwd)))
                except Exception:
                    in_builder = True
                if builder_arg or in_builder:
                    return self.bad(self.cwd or '?', 'python -m %s from/against a builder path' % mod)
            return None
        if script and 'no_exec' not in DEFECTS:
            if check_only:
                return None
            if seg['stdin'] is None and prog in SHELLS and script in ('-s',):
                return None
            return self.exec_check(script, rest)
        if seg['stdin'] and prog in SHELLS | INTERPRETERS:
            return self.wpos(seg['stdin'], 'stdin script from a builder path') if self._stdin_builder(seg['stdin']) else None
        return None

    def _stdin_builder(self, tok):
        try:
            return bool(self.p.cls_tok(tok, self.cwd, self.env)[0])
        except Unresolvable:
            return True

    # ---- patch / git apply
    def patch_check(self, args, seg, what):
        texts = list(seg['heredoc'])
        files = [a for a in args if not a.startswith('-')]
        if seg['stdin']:
            files.append(seg['stdin'])
        for f in files:
            try:
                rp = self.p.res(f, self.cwd, self.env)
            except Unresolvable:
                return self.bad(f, what + ': patch file not resolvable (refused, fail closed)')
            if os.path.isfile(rp):
                try:
                    texts.append(open(rp, encoding='utf-8', errors='replace').read())
                except OSError:
                    return self.bad(rp, what + ': patch file unreadable (refused, fail closed)')
        if not texts:
            return self.bad('?', what + ': no patch text to inspect (refused, fail closed)')
        for t in texts:
            for tgt in patch_targets(t):
                try:
                    k, rp = self.p.cls_tok(tgt, self.cwd, self.env)
                except Unresolvable:
                    continue
                if k:
                    return self.bad(rp, what + ' would write a builder-owned path')
        return None

    # ---- git
    def git(self, args, seg):
        repo, i, sub = self.cwd, 0, None
        while i < len(args):
            a = args[i]
            if a in ('-C', '--git-dir', '--work-tree') and i + 1 < len(args):
                try:
                    repo = self.p.res(args[i + 1], self.cwd, self.env)
                except Unresolvable:
                    return self.bad(args[i + 1], 'git -C path not resolvable (refused, fail closed)')
                i += 2
                continue
            if a.startswith(('--git-dir=', '--work-tree=')):
                try:
                    repo = self.p.res(a.split('=', 1)[1], self.cwd, self.env)
                except Unresolvable:
                    return self.bad(a, 'git path not resolvable (refused, fail closed)')
                i += 1
                continue
            if a == '-c' and i + 1 < len(args):
                if re.search(r'hookspath', args[i + 1], re.I):
                    return self.bad(args[i + 1], 'git -c core.hooksPath (hook bypass)')
                i += 2
                continue
            if a.startswith('-'):
                i += 1
                continue
            sub = a
            break
        if sub is None:
            return None
        rest = args[i + 1:]
        foreign = repo is not None and self.p.classify(self.p.real(repo)) == 'builder' and \
            any(_under(self.p.real(repo), r) for r in self.p.foreign)
        if foreign:
            return None if sub in GIT_READ else self.bad(repo, 'git %s inside a foreign clone' % sub)
        if sub in ('checkout-index', 'update-index', 'filter-branch', 'filter-repo', 'read-tree', 'replace', 'update-ref'):
            return self.bad(sub, 'git %s rewrites worktree/index/history wholesale' % sub)
        if sub == 'config' and any(re.search(r'hookspath', a, re.I) for a in rest):
            return self.bad('core.hooksPath', 'git config core.hooksPath (hook bypass)')
        flags = [a for a in rest if a.startswith('-')]
        dd = rest.index('--') if '--' in rest else None
        explicit = rest[dd + 1:] if dd is not None else []
        positional, j = [], 0
        while j < len(rest):
            a = rest[j]
            if a == '--':
                break
            if a.startswith('-'):
                j += 2 if (a in GIT_VALUE_OPTS and '=' not in a) else 1
                continue
            positional.append(a); j += 1

        def pathspecs(include_pos):
            specs = list(explicit)
            for a in positional if include_pos else []:
                if a in ('.', ':/') or '*' in a or '?' in a:
                    specs.append(a); continue
                try:
                    if os.path.exists(self.p.res(a, repo, self.env)):
                        specs.append(a)
                except Unresolvable:
                    specs.append(a)
            return specs

        def judge(specs, why, builder_only=False):
            for s in specs:
                v = self.wpos_in(s, repo, why, builder_only)
                if v:
                    return v
            return None
        if sub in ('checkout', 'switch'):
            if any(f in ('-f', '--force', '--discard-changes', '-B') or re.match(r'^-[a-zA-Z]*f[a-zA-Z]*$', f) for f in flags):
                return self.bad(repo or '?', 'git %s --force discards the whole worktree' % sub)
            return judge(pathspecs(dd is None and sub == 'checkout' and not any(f in ('-b', '-B', '--orphan') for f in flags)), 'git %s pathspec' % sub)
        if sub == 'restore':
            return judge(pathspecs(True), 'git restore pathspec') or (None if pathspecs(True) else self.bad(repo or '?', 'git restore with no pathspec'))
        if sub in ('mv', 'rm'):
            return judge(pathspecs(True), 'git %s pathspec' % sub)
        if sub == 'reset':
            if any(f in ('--hard', '--merge', '--keep') for f in flags):
                return self.bad(repo or '?', 'git reset %s rewrites the whole worktree' % ' '.join(flags))
            return judge(explicit, 'git reset pathspec')
        if sub == 'clean':
            if any(f in ('-n', '--dry-run') or re.match(r'^-[a-zA-Z]*n[a-zA-Z]*$', f) for f in flags):
                return None
            return judge(pathspecs(True), 'git clean pathspec') or self.bad(repo or '?', 'git clean with no pathspec')
        if sub == 'add':
            if any(f in ('-A', '--all', '-u', '--update') for f in flags):
                return self.bad(repo or '?', 'git add --all stages builder-owned files')
            return judge(pathspecs(True), 'git add pathspec', True)
        if sub == 'commit':
            if any(re.match(r'^-[A-Za-z]*a[A-Za-z]*$', f) or f == '--all' for f in flags):
                return self.bad(repo or '?', 'git commit -a stages builder-owned files')
            return judge(explicit, 'git commit pathspec', True)
        if sub == 'stash':
            verb = positional[0] if positional else 'push'
            if verb in ('pop', 'apply', 'list', 'show', 'drop', 'clear', 'branch'):
                return None
            specs = explicit or positional[1:] if verb in ('push', 'save') and positional else explicit
            specs = [s for s in specs if not s.startswith('-')]
            if not specs:
                return self.bad(repo or '?', 'git stash with no pathspec takes the whole worktree')
            carve = {self.p.real(os.path.join(self.p.own, c)) for c in CARVEOUT}
            for s in specs:
                try:
                    rp = self.p.res(s, repo, self.env)
                except Unresolvable:
                    return self.bad(s, 'git stash pathspec not resolvable (refused, fail closed)')
                if rp not in carve and self.p.classify(rp):
                    return self.bad(rp, 'git stash of a builder-owned path (only the two foreign files are carved out)')
            return None
        if sub in ('apply', 'am'):
            if sub == 'apply' and any(f in ('--check', '--stat', '--numstat', '--summary') for f in flags):
                return None
            return self.patch_check(positional, seg, 'git ' + sub)
        return None

    def wpos_in(self, tok, repo, why, builder_only=False):
        saved, self.cwd = self.cwd, repo
        try:
            if builder_only:
                try:
                    k, rp = self.p.cls_tok(tok, self.cwd, self.env)
                except Unresolvable:
                    return self.bad(tok, why + ': path not resolvable (refused, fail closed)')
                return self.bad(rp, why) if k == 'builder' else None
            return self.wpos(tok, why)
        finally:
            self.cwd = saved


def _unres(pol, tok, cwd, env):
    try:
        pol.res(tok, cwd, env)
        return False
    except Unresolvable:
        return True


# ---------------------------------------------------------------- decision
def decide(pol, payload):
    """-> None (allow) or (path, call_type, reason)."""
    tool = payload.get('tool_name', '')
    inp = payload.get('tool_input') or {}
    cwd = payload.get('cwd') or os.getcwd()
    if tool in FILE_TOOLS:
        p = inp.get('file_path') or inp.get('notebook_path')
        if not p:
            return ('?', tool, 'no path in the tool input (refused, fail closed)')
        try:
            rp = pol.res(p, cwd, {})
        except Unresolvable:
            return (p, tool, 'path not resolvable (refused, fail closed)')
        k = pol.classify(rp)
        if k:
            return (rp, tool, 'direct %s on a %s-owned path' % (tool, 'self-protected' if k == 'self' else 'builder'))
        return None
    if tool in SHELL_TOOLS:
        cmd = inp.get('command')
        if not isinstance(cmd, str):
            return ('?', tool, 'no command text (refused, fail closed)')
        v = Analyzer(pol, cwd).check(cmd)
        return (v[0], tool, v[1]) if v else None
    return None


def block_log(agent, path, call, reason):
    line = '\t'.join(s.replace('\t', ' ').replace('\r', ' ').replace('\n', ' ')[:400] for s in (
        datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), agent, path, call, reason)) + '\n'
    try:
        os.makedirs(os.path.dirname(BLOCK_LOG), exist_ok=True)
        # O_BINARY: without it Windows translates the LF to CRLF on os.write (b102;
        # cc found 12 of 12 auditor rows ending CRLF while builder rows end LF).
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        if 'no_binary' not in DEFECTS:
            flags |= getattr(os, 'O_BINARY', 0)
        fd = os.open(BLOCK_LOG, flags)
        try:
            os.write(fd, line.encode('utf-8', 'backslashreplace'))
        finally:
            os.close(fd)
        return True
    except Exception as e:     # b117: not only OSError -- a UnicodeEncodeError here used to lift the refusal (exit 1 is non-blocking)
        sys.stderr.write('NOTE: block log not written (%s); the refusal stands.\n' % e)
        return False


def main(argv):
    if '--selftest' in argv:
        return selftest()
    clone = argv[argv.index('--clone') + 1] if '--clone' in argv and argv.index('--clone') + 1 < len(argv) else None
    agent = os.path.basename(clone.rstrip('/\\')).replace('SAIRN-', '') if clone else '?'
    payload, verdict = {}, None
    try:
        if not clone:
            raise RuntimeError('--clone missing')
        payload = json.load(sys.stdin)
        verdict = decide(Policy.live(clone), payload)
    except Exception as e:                                   # fail CLOSED: exit 1 would be non-blocking
        verdict = ('?', payload.get('tool_name', '?') if isinstance(payload, dict) else '?', 'hook could not decide: %r (refused, fail closed)' % (e,))
    if verdict is None:
        return 0
    path, call, reason = verdict
    if isinstance(payload, dict) and payload.get('agent_type'):
        agent += '/' + str(payload['agent_type'])
    try:
        block_log(agent, path, call, reason)
    except BaseException:       # b117: a refusal is never lifted by its own bookkeeping
        pass
    msg = ('REFUSED by the hover builder-path deny-list: %s [%s]. This role audits and flags; it does not build. '
           'Log it as a finding for the owning builder. Block recorded in %s.\n' % (reason, path, BLOCK_LOG))
    try:
        sys.stderr.write(msg)
    except BaseException:       # a lone surrogate in the path cannot be encoded by the console
        sys.stderr.write(msg.encode('ascii', 'backslashreplace').decode('ascii'))
    return 2


# ---------------------------------------------------------------- selftest
def _mk(root):
    docs = os.path.join(root, 'Documents')
    own, cc, main = (os.path.join(docs, d) for d in ('SAIRN-fakehover', 'SAIRN-fakecc', 'SAIRN'))
    for d in (own, cc, main):
        os.makedirs(os.path.join(d, '.git'), exist_ok=True)
        os.makedirs(os.path.join(d, 'tools'), exist_ok=True)
        os.makedirs(os.path.join(d, 'api'), exist_ok=True)
        open(os.path.join(d, 'api', 'x.js'), 'w').write('x')
        open(os.path.join(d, 'tools', 'b.py'), 'w').write('print(1)')
    os.makedirs(os.path.join(own, '.claude', 'skills', 'sairn-hover-auditor', 'tools'), exist_ok=True)
    os.makedirs(os.path.join(own, 'docs'), exist_ok=True)
    open(os.path.join(own, 'tools', 'sairn_claim.py'), 'w').write('#')
    for _n in EXEC_OK_TOOLS:
        open(os.path.join(own, 'tools', _n), 'w').write('#')
        open(os.path.join(cc, 'tools', _n), 'w').write('#')
    open(os.path.join(own, 'docs', 'scrutiny-flags.json'), 'w').write('{}')
    open(os.path.join(own, 'docs', 'p.patch'), 'w').write('--- a/api/x.js\n+++ b/api/x.js\n@@ -1 +1 @@\n-x\n+y\n')
    open(os.path.join(own, 'docs', 'q.patch'), 'w').write('--- a/.claude/skills/sairn-hover-auditor/n.md\n+++ b/.claude/skills/sairn-hover-auditor/n.md\n')
    locks, scratch, hc = os.path.join(root, 'locks'), os.path.join(root, 'scratch'), os.path.join(root, 'home', '.claude')
    os.makedirs(locks); os.makedirs(scratch); os.makedirs(hc)
    manifest = os.path.join(locks, 'hover-scope-manifest.json')
    prot = [os.path.join(own, '.claude', 'settings.json'), os.path.join(own, '.claude', 'settings.local.json'),
            os.path.join(hc, 'settings.json'), manifest, os.path.join(locks, 'deny-blocks.log'),
            os.path.join(own, '.claude', 'skills', 'sairn-hover-auditor', 'tools', 'guard_copy.py')]
    allowed = ['.claude/skills/sairn-hover-auditor/', 'docs/defect-density-register.json', '.claude/claims/hover.json']
    pol = Policy(own, [cc, main], allowed, locks, prot)
    return pol, own, cc, main, scratch, locks


def _arms(pol, own, cc, main, scratch, locks, jn):
    B = lambda c, cwd=None: {'tool_name': 'Bash', 'tool_input': {'command': c}, 'cwd': cwd or own}
    E = lambda t, p, cwd=None: {'tool_name': t, 'tool_input': {'file_path': p}, 'cwd': cwd or own}
    sk = os.path.join(own, '.claude', 'skills', 'sairn-hover-auditor')
    gb = lambda p: '/' + p[0].lower() + p[2:].replace('\\', '/')            # git-bash spelling
    D, A = 'DENY', 'ALLOW'
    ccx = os.path.join(cc, 'api', 'x.js')
    return [
        ('edit foreign clone file', E('Edit', ccx), D),
        ('write new file in foreign clone', E('Write', os.path.join(cc, 'new.txt')), D),
        ('edit own-clone builder file (api/)', E('Edit', os.path.join(own, 'api', 'x.js')), D),
        ('edit relative path from cwd into builder', E('Edit', 'api/x.js'), D),
        ('edit via .. escape out of scope dir', E('Edit', os.path.join(sk, '..', '..', '..', 'api', 'x.js')), D),
        ('edit via git-bash spelling', E('Edit', gb(ccx)), D),
        ('edit via other letter case', E('Edit', ccx.swapcase()), D),
        ('edit through a junction', E('Edit', os.path.join(jn, 'api', 'x.js')), D),
        ('write new file through a junction', E('Write', os.path.join(jn, 'api', 'new.js')), D),
        ('NotebookEdit builder path', {'tool_name': 'NotebookEdit', 'tool_input': {'notebook_path': ccx}, 'cwd': own}, D),
        ('edit settings.local.json (self-protected)', E('Edit', os.path.join(own, '.claude', 'settings.local.json')), D),
        ('edit the manifest (self-protected)', E('Edit', os.path.join(locks, 'hover-scope-manifest.json')), D),
        ('edit .git hook', E('Write', os.path.join(own, '.git', 'hooks', 'pre-push')), D),
        ('write in locks dir', E('Write', os.path.join(locks, 'status')), D),
        ('edit own skill file', E('Edit', os.path.join(sk, 'SKILL.md')), A),
        ('write handoff at repo root', E('Write', os.path.join(own, 'SAIRN-handoff-H1-b98.md')), A),
        ('write digest at repo root', E('Write', os.path.join(own, 'SAIRN-digest-H1-b98.txt')), A),
        ('write scratch', E('Write', os.path.join(scratch, 'a.txt')), A),
        ('edit defect register (manifest-allowed)', E('Edit', os.path.join(own, 'docs', 'defect-density-register.json')), A),
        ('edit claim file (manifest-allowed)', E('Edit', os.path.join(own, '.claude', 'claims', 'hover.json')), A),
        ('no path in Edit input', {'tool_name': 'Edit', 'tool_input': {}, 'cwd': own}, D),
        ('other tool ignored', {'tool_name': 'Read', 'tool_input': {'file_path': ccx}, 'cwd': own}, A),
        ('git checkout -- builder path', B('git checkout -- api/x.js'), D),
        ('git checkout rev -- builder path', B('git checkout origin/main -- tools/b.py'), D),
        ('git restore builder path', B('git restore api/x.js'), D),
        ('git restore .', B('git restore .'), D),
        ('git mv builder path', B('git mv api/x.js api/y.js'), D),
        ('git rm builder path', B('git rm api/x.js'), D),
        ('git apply patch file hitting builder', B('git apply docs/p.patch'), D),
        ('git apply heredoc hitting builder', B("git apply <<'EOF'\n--- a/api/x.js\n+++ b/api/x.js\nEOF"), D),
        ('git apply --check is a read', B('git apply --check docs/p.patch'), A),
        ('git apply patch inside scope', B('git apply docs/q.patch'), A),
        ('git add -A', B('git add -A'), D),
        ('git add builder path', B('git add api/x.js'), D),
        ('git commit -am', B('git commit -am "x"'), D),
        ('git reset --hard', B('git reset --hard origin/main'), D),
        ('git clean -fd', B('git clean -fd'), D),
        ('git clean -n is a read', B('git clean -n'), A),
        ('git checkout -f', B('git checkout -f main'), D),
        ('git -C foreign clone checkout', B('git -C %s checkout -- api/x.js' % cc), D),
        ('git -C foreign clone pull', B('git -C %s pull' % cc), D),
        ('git -C foreign clone log is a read', B('git -C %s log --oneline -3' % cc), A),
        ('git stash bare', B('git stash'), D),
        ('git stash push non-carve-out builder file', B('git stash push -- api/x.js'), D),
        ('git stash push the two carve-out files', B('git stash push -q -- .claude/settings.json docs/scrutiny-flags.json'), A),
        ('git stash pop', B('git stash pop -q'), A),
        ('git checkout -b newbranch', B('git checkout -b hover-b98-x origin/main'), A),
        ('git commit -m with builder paths in the message', B('git commit -m "fix api/x.js and tools/b.py"'), A),
        ('git add own skill file', B('git add .claude/skills/sairn-hover-auditor/tools/t.py'), A),
        ('git add a self-protected file is staging, not editing', B('git add .claude/skills/sairn-hover-auditor/tools/guard_copy.py'), A),
        ('git pull --rebase', B('git pull --rebase -q origin main'), A),
        ('git push', B('git push origin main'), A),
        ('git show builder file is a read', B('git show HEAD:api/x.js'), A),
        ('redirect into builder', B('echo x > api/x.js'), D),
        ('append into foreign clone', B('echo x >> %s' % ccx), D),
        ('redirect to scratch plus builder read', B('cat api/x.js > %s/o.txt' % scratch.replace('\\', '/')), A),
        ('redirect 2>&1 and /dev/null', B('grep x api/x.js 2>&1 >/dev/null'), A),
        ('sed -i builder', B("sed -i 's/x/y/' api/x.js"), D),
        ('sed -n builder is a read', B("sed -n '1,5p' api/x.js"), A),
        ('rm builder', B('rm -f api/x.js'), D),
        ('rm glob in builder dir', B('rm tools/*.py'), D),
        ('touch builder', B('touch tools/new.py'), D),
        ('cp INTO builder', B('cp %s/a.txt api/a.txt' % scratch.replace('\\', '/')), D),
        ('cp FROM builder to scratch is a read', B('cp api/x.js %s/copy.js' % scratch.replace('\\', '/')), A),
        ('mv builder file out', B('mv api/x.js %s/x.js' % scratch.replace('\\', '/')), D),
        ('tee into builder', B('echo x | tee api/x.js'), D),
        ('cd builder then relative write', B('cd %s && echo x > f.txt' % cc), D),
        ('cd via variable then relative write', B('D=%s; cd $D; echo x > f.txt' % cc), D),
        ('cd into foreign clone from a scratch cwd, relative write', B('cd %s && echo x > f.txt' % cc, scratch), D),
        ('cd .. out of the scope dir, relative write', B('cd ../../../.. && echo x > f.txt', os.path.join(sk, 'tools')), D),
        ('cd within scratch, relative write', B('cd %s && echo x > f.txt' % scratch, scratch), A),
        ('double-quoted substitution hides a write', B('echo "$(rm -f api/x.js)"'), D),
        ('backtick substitution hides a write', B('echo `rm -f api/x.js`'), D),
        ('cd then git checkout', B('cd %s && git checkout -- api/x.js' % cc), D),
        ('subshell cd then write', B('(cd %s; echo x > f.txt)' % cc), D),
        ('write path from unset variable', B('echo x > $NOPE_UNSET_VAR/f.txt'), D),
        ('write via command substitution path', B('echo x > $(echo api)/x.js'), D),
        ('command substitution hides a write', B('echo $(rm -f api/x.js)'), D),
        ('assigned variable then write to scratch', B('S=%s; echo x > $S/f.txt' % scratch.replace('\\', '/')), A),
        ('python -c writes builder', B('python -c "open(\'api/x.js\',\'w\').write(\'z\')"'), D),
        ('python -c r+ builder', B('python -c "open(\'api/x.js\',\'r+\').write(\'\')"'), D),
        ('python -c with subprocess and builder path', B('python -c "import subprocess; subprocess.run([\'rm\',\'api/x.js\'])"'), D),
        ('python -c windows path doubled backslashes', B('python -c "open(\'%s\',\'w\')"' % ccx.replace('\\', '\\\\')), D),
        ('python heredoc writes builder', B("python - <<'EOF'\nopen('api/x.js','w').write('z')\nEOF"), D),
        ('node -e writes builder', B('node -e "require(\'fs\').writeFileSync(\'api/x.js\',\'z\')"'), D),
        ('python -c reads builder', B('python -c "print(open(\'api/x.js\').read())"'), A),
        ('python -c scratch only', B('python -c "open(\'%s/o.txt\',\'w\').write(\'z\')"' % scratch.replace('\\', '/')), A),
        ('bash -c writes builder', B("bash -c 'echo x > api/x.js'"), D),
        ('eval writes builder', B('eval "echo x > api/x.js"'), D),
        ('find -delete in builder', B('find api -name "*.js" -delete'), D),
        ('xargs rm builder', B('ls api | xargs rm'), D),
        ('exec: python builder script', B('python tools/b.py'), D),
        ('exec: node builder test', B('node api/x.js'), D),
        ('exec: foreign clone script', B('python %s' % os.path.join(cc, 'tools', 'b.py')), D),
        ('exec: bash builder script', B('bash tools/b.py'), D),
        ('exec: direct ./path', B('./tools/b.py'), D),
        ('exec: npm from builder cwd', B('npm test'), D),
        ('exec: python -m pytest from builder cwd', B('python -m pytest'), D),
        ('exec: python -m py_compile builder', B('python -m py_compile tools/b.py'), D),
        ('exec: node --check is parse-only', B('node --check api/x.js'), A),
        ('exec: sairn_claim claim', B('python tools/sairn_claim.py claim hover b98 task words'), A),
        ('exec: sairn_claim release', B('python tools/sairn_claim.py release hover'), A),
        ('exec: sairn_claim other subcommand', B('python tools/sairn_claim.py gc'), D),
        ('exec: digest_lint on a digest (exempt checker)', B('python tools/digest_lint.py SAIRN-digest-H1-b9.txt'), A),
        ('exec: sql_placeholder_check --fixtures (exempt checker)', B('python tools/sql_placeholder_check.py --fixtures'), A),
        ('exec: sql_placeholder_check --all (exempt checker)', B('python tools/sql_placeholder_check.py --all'), A),
        ('exec: exempt checker chained with a builder script', B('python tools/sql_placeholder_check.py --all && python tools/b.py'), D),
        ('exec: same-named checker in a SIBLING clone stays refused', B('python %s' % os.path.join(cc, 'tools', 'sql_placeholder_check.py')), D),
        ('exec: a different builder tool is still refused', B('python tools/tier_a_review_gate.py --list'), D),
        ('exec: own skill tool', B('python .claude/skills/sairn-hover-auditor/tools/t.py --selftest'), A),
        ('exec: scratch script', B('python %s/s.py' % scratch.replace('\\', '/')), A),
        ('heredoc prose naming builder paths', B("cat > %s/n.md <<'EOF'\nwe ran sed -i on api/x.js and rm tools/b.py\nEOF" % scratch.replace('\\', '/')), A),
        ('grep builder files', B('grep -rn foo api tools | head'), A),
        ('chain of reads', B('git log --oneline -3 && cat api/x.js && ls tools'), A),
        ('background chain with pull and push', B('git pull --rebase -q origin main > %s/p.out 2>&1; git push origin main >> %s/p.out 2>&1' % ((scratch.replace('\\', '/'),) * 2)), A),
        ('patch with builder target', B('patch -p1 < docs/p.patch'), D),
        ('curl -o into builder', B('curl -o api/x.js http://example.invalid'), D),
        ('dd of= builder', B('dd if=/dev/zero of=api/x.js'), D),
        ('encoded powershell', {'tool_name': 'PowerShell', 'tool_input': {'command': 'powershell -enc AAAA'}, 'cwd': own}, D),
    ]


def selftest():
    import shutil
    root = tempfile.mkdtemp(prefix='hover-deny-selftest-')
    rc = 0
    try:
        pol, own, cc, main, scratch, locks = _mk(root)
        jn = os.path.join(root, 'junction')
        r = subprocess.run(['cmd', '/c', 'mklink', '/J', jn, cc], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.isdir(jn):
            print('COULD NOT RUN: junction not creatable (%s)' % (r.stdout + r.stderr).strip())
            return 2

        def run(defects):
            DEFECTS.clear(); DEFECTS.update(defects)
            fails = []
            for name, payload, want in _arms(pol, own, cc, main, scratch, locks, jn):
                try:
                    got = 'DENY' if decide(pol, payload) else 'ALLOW'
                except Exception as e:
                    got = 'CRASH %r' % (e,)
                if got != want:
                    fails.append('%s (want %s, got %s)' % (name, want, got))
            return fails
        arms = _arms(pol, own, cc, main, scratch, locks, jn)
        base = run(set())
        print('ARMS: %d, clean run: %d failed' % (len(arms), len(base)))
        for f in base:
            print('  FAIL', f)
        rc = 1 if base else 0
        for flag in ('no_realpath', 'no_cd_track', 'no_git', 'no_heredoc', 'no_exec', 'no_exec_ok', 'no_redirect', 'no_subst'):
            fl = run({flag})
            print('PLANTED %-12s -> %d arm(s) red%s' % (flag, len(fl), '' if fl else '   <-- UNGUARDED: nothing turned red'))
            if not fl:
                rc = 1
        DEFECTS.clear()

        # b102: a fresh block-log row is LF-only, five tab-separated columns, capped at 400.
        def _row_bytes(defects):
            global BLOCK_LOG
            saved, BLOCK_LOG = BLOCK_LOG, os.path.join(root, 'bl-%d.log' % len(defects))
            DEFECTS.clear(); DEFECTS.update(defects)
            try:
                block_log('hover/x', 'c:/p\tq\r\nr' + 'z' * 500, 'Edit', 'direct Edit')
                with open(BLOCK_LOG, 'rb') as fh:
                    return fh.read()
            finally:
                BLOCK_LOG = saved
                DEFECTS.clear()
        def _row_ok(b):
            return (b.endswith(b'\n') and b'\r' not in b and b.count(b'\n') == 1
                    and len(b.rstrip(b'\n').split(b'\t')) == 5
                    and all(len(f) <= 400 for f in b.rstrip(b'\n').split(b'\t')))
        good = _row_bytes(set())
        bl_ok = _row_ok(good)
        print('BLOCKLOG fresh row LF-only, 5 columns, fields capped -> %s' % ('ok' if bl_ok else '<-- WRONG: %r' % good[:80]))
        rc = rc or (0 if bl_ok else 1)
        bad = _row_bytes({'no_binary'})
        planted = not _row_ok(bad)
        print('PLANTED no_binary    -> %s' % ('arm red (CRLF row)' if planted
                                              else '<-- UNGUARDED: no O_BINARY still wrote an LF-only row'))
        rc = rc or (0 if planted else 1)
        # fail-closed arms on the hook entry point itself
        env = dict(os.environ)
        for label, stdin in (('garbage stdin', 'not json'), ('empty stdin', '')):
            code = ('import sys; sys.path.insert(0, %r); import hover_builder_path_deny as m; m.BLOCK_LOG = %r; sys.exit(m.main(["--clone", %r]))'
                    % (os.path.dirname(os.path.abspath(__file__)), os.path.join(root, 'entry.log'), own))
            p = subprocess.run([sys.executable, '-c', code], input=stdin, capture_output=True, text=True, env=env)
            ok = p.returncode == 2
            print('ENTRY %-14s -> exit %d %s' % (label, p.returncode, 'ok' if ok else '<-- must be 2 (fail closed)'))
            rc = rc or (0 if ok else 1)
        p = subprocess.run([sys.executable, os.path.join(root, 'no_such_hook.py')], capture_output=True, text=True)
        print('ENTRY missing script   -> exit %d %s' % (p.returncode, 'ok' if p.returncode == 2 else '<-- must be 2'))
        rc = rc or (0 if p.returncode == 2 else 1)
        # b117 arms on the SCRIPT FILE ITSELF (a copy with its block log redirected, so the real log gains no row)
        ent = os.path.join(root, 'entry_copy')
        os.makedirs(ent)
        src_text = open(os.path.abspath(__file__), encoding='utf-8').read()
        marker_line = "BLOCK_LOG = os.path.join(LOCKS, 'deny-blocks.log')"
        if marker_line not in src_text:
            print('ENTRY b117 arms SKIPPED -- the BLOCK_LOG line moved <-- fix the selftest')
            rc = rc or 1
        else:
            open(os.path.join(ent, 'hook.py'), 'w', encoding='utf-8').write(
                src_text.replace(marker_line, 'BLOCK_LOG = %r' % os.path.join(root, 'entry_copy.log')))
            lone = {'tool_name': 'Write', 'tool_input': {'file_path': cc + '/api/\ud800.js'}, 'cwd': own}
            p = subprocess.run([sys.executable, os.path.join(ent, 'hook.py'), '--clone', own],
                               input=json.dumps(lone, ensure_ascii=True).encode('ascii'), capture_output=True)
            print('ENTRY lone-surrogate path -> exit %d %s' % (p.returncode, 'ok' if p.returncode == 2 else '<-- must be 2 (refusal lifted)'))
            rc = rc or (0 if p.returncode == 2 else 1)
            mark = os.path.join(root, 'shadow_marker.txt')
            open(os.path.join(ent, 'json.py'), 'w').write('open(%r, "w").write("imported")\nraise ImportError("shadow")\n' % mark)
            p = subprocess.run([sys.executable, os.path.join(ent, 'hook.py'), '--clone', own], input=b'not json', capture_output=True)
            shadow = os.path.exists(mark)
            print('ENTRY shadow json.py     -> exit %d, shadow module %s %s' % (p.returncode, 'IMPORTED' if shadow else 'not imported',
                  'ok' if (p.returncode == 2 and not shadow) else '<-- must be exit 2 and not imported'))
            rc = rc or (0 if (p.returncode == 2 and not shadow) else 1)
    finally:
        DEFECTS.clear()
        subprocess.run(['cmd', '/c', 'rmdir', os.path.join(root, 'junction')], capture_output=True)
        shutil.rmtree(root, ignore_errors=True)
    print('SELFTEST', 'PASS' if rc == 0 else 'FAIL')
    return rc


if __name__ == '__main__':
    try:
        _rc = main(sys.argv[1:])
    except BaseException:       # b117: any escape from main is a refusal, never exit 1 (non-blocking)
        _rc = 2
    sys.exit(_rc)
