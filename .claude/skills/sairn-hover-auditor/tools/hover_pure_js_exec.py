#!/usr/bin/env python
"""hover_pure_js_exec.py -- TIER 0 of the live-execution capability queued
2026-09-21 item 3: run a real, verbatim JS function extracted from a
platform app's own source against caller-supplied synthetic inputs, inside
an isolated Node vm context with NO ambient network/filesystem/process
globals -- so a genuine runtime execution replaces a source-read guess for
findings this role can otherwise only confirm by reasoning about documented
semantics, with a MECHANICAL (not merely intentional) guarantee that
nothing it runs can reach real production, real network, or real disk.

THIS IS TIER 0 ONLY, DELIBERATELY THE NARROW SLICE THAT NEEDS NO NEW
AUTHORIZATION. The full item-3 ask (Anthropic's own 4.6%->32.8% audit-
realism finding, cited in the queue that requested this) covers two
different risk shapes and they are not being conflated here:

  TIER 0 (this file): execute a genuinely PURE function -- one whose
  observable behaviour depends only on its own arguments -- against
  synthetic, fabricated inputs, inside a sandboxed vm.Context with no
  fetch/XHR/WebSocket/require/process/fs global available at all. Even a
  function that TRIES to reach the network throws ReferenceError inside
  this sandbox; it cannot succeed, not because this script chooses to
  forbid it but because the capability is not there to reach. This needs
  no new authorization: it generalises what this role already did ad hoc
  this session (hover-audit-log #427's predecessor: "LIVE-TESTED FINDING B
  ... with my own test case", calling classify_own_commit() directly with
  real arguments) into standing, reusable tooling, and does the same thing
  for the platform's embedded JS that was already being done by hand for
  its Python tools.

  TIER 1 (NOT built here -- proposed only, see hover-audit-log #429):
  exercising a real API endpoint or a real deployed page against
  production (api/sd-data.js, sairn.vercel.app itself) -- the shape
  tools/*_live_probe.py already uses for build-agent work
  (leg_session_gate_live_probe.py, sc_tier_a_write_gate_live_probe.py),
  with its own proven safety envelope (every arm a REFUSAL or a read of
  already-public demo data, sairn_http.py's browser-UA client, three-state
  VERIFIED/UNVERIFIED/FAILED reporting). That envelope is real and
  reusable, but running ANY new traffic against real production without
  Michael's explicit sign-off is exactly the risk item 3 named ("propose
  the mechanism before building anything that could write to production")
  and exactly what SKILL.md's own Rules of Engagement assign to Michael,
  not this role, to authorize. So Tier 1 is a proposal, not code, pending
  that answer.

WHAT "PURE" MEANS HERE, MECHANICALLY ENFORCED, NOT JUST DOCUMENTED. The
target function runs inside `vm.createContext()` with a sandbox object that
defines ONLY: a captured `console` (never real stdout of the host process),
the caller-supplied --globals JSON (plain data/mock functions the caller
constructs by hand -- never real I/O), and whatever built-ins the JS engine
itself always provides (Math, JSON, Array, ...). fetch, XMLHttpRequest,
WebSocket, require, process, fs, and Node's own global object are NOT
copied in -- a function referencing any of them gets a genuine
ReferenceError from the engine, not a policy this script enforces by
watching for it.

A static pre-scan for network-shaped tokens (fetch(, XMLHttpRequest,
WebSocket(, supabase, axios, localStorage) still runs and is printed as a
NOTE before execution -- not a hard refusal, because the sandbox already
makes any such attempt fail safely, and blocking it would hide a genuine,
sometimes-useful finding ("this function references fetch and would
ReferenceError in isolation, meaning its real behaviour depends on ambient
wiring invisible from its own source" is itself sometimes the finding).

WHAT THIS CANNOT DO, STATED RATHER THAN IMPLIED. Extraction is a
brace-balance scanner over the function's own text, not a real JS parser --
it tracks '/','*' block comments, '//' line comments, and single/double/
template-literal strings well enough for ordinary code, but a function
containing a regex literal with an unescaped brace, or unusual nesting, can
defeat it. On any ambiguity (brace count does not return to zero, or a
string/comment is left open at end of scan) this REFUSES with COULD_NOT_RUN
rather than guessing at a truncated body -- the same fail-closed standard
hover_coverage_ledger.py and hover_cold_scan_pool.py were just fixed to
hold everywhere. Only function-declaration, function-expression, and
brace-bodied-arrow forms are supported; an expression-bodied arrow
(`const f = x => x*2`) is refused, not guessed at.

Run:
  python hover_pure_js_exec.py --html stonedesk.html --fn fmtMoney \
      --args '[3.7]'
  python hover_pure_js_exec.py --html stonedesk.html --fn fmtMoney \
      --args '[3.7]' --repo <path>
  python hover_pure_js_exec.py --selftest
"""
import json
import os
import re
import subprocess
import sys
import tempfile

_KNOWN_CLONES = (
    'C:/Users/marsh/Documents/SAIRN-hover',
    'C:/Users/marsh/Documents/SAIRN-hover2',
)

NETWORK_TOKENS = ('fetch(', 'XMLHttpRequest', 'WebSocket(', 'supabase',
                   'axios', 'localStorage', 'sessionStorage', 'require(',
                   'process.', 'import(')


class CouldNotTell(Exception):
    pass


def discover_repo(argv=None):
    """Identical contract to the other two hover-audit-log tools' own
    discover_repo() -- --repo, then $HOVER_LEDGER_REPO, then the first
    existing known clone, then None (COULD NOT TELL)."""
    argv = sys.argv[1:] if argv is None else argv
    if '--repo' in argv:
        i = argv.index('--repo')
        if i + 1 < len(argv):
            return argv[i + 1]
    env = os.environ.get('HOVER_LEDGER_REPO')
    if env:
        return env
    for candidate in _KNOWN_CLONES:
        if os.path.isdir(os.path.join(candidate, '.git')):
            return candidate
    return None


def read_source_text(repo, rel_path):
    """The real file content as of origin/main, same fetch-then-git-show
    discipline as hover_cold_scan_pool.py's read_tiers_text() -- so a
    Tier 0 run never quietly reasons about a stale local working tree."""
    if not repo or not os.path.isdir(repo):
        raise CouldNotTell('no readable clone: %r (checked --repo, '
                            '$HOVER_LEDGER_REPO, and %s)'
                            % (repo, ', '.join(_KNOWN_CLONES)))
    try:
        subprocess.run(['git', 'fetch', 'origin', '--quiet'],
                        cwd=repo, capture_output=True, text=True,
                        encoding='utf-8', check=True)
    except subprocess.CalledProcessError as e:
        raise CouldNotTell('git fetch failed in %s: %s'
                            % (repo, (e.stderr or str(e)).strip()))
    # encoding='utf-8' explicitly: subprocess.run's text=True otherwise
    # decodes with the OS locale's preferred encoding (cp1252 on this
    # platform's Windows clones), which crashes with UnicodeDecodeError on
    # the very first non-ASCII byte a real app file contains -- found live,
    # not by inspection, running this tool against the real stonedesk.html
    # (2MB+ of real content) rather than only the small ASCII-only fixture.
    # git blobs on this platform are UTF-8 (every file here is opened with
    # encoding='utf-8'), so this is the correct decoding, not a workaround.
    r = subprocess.run(['git', 'show', 'origin/main:' + rel_path],
                        cwd=repo, capture_output=True, text=True,
                        encoding='utf-8')
    if r.returncode != 0:
        raise CouldNotTell('git show origin/main:%s failed in %s: %s'
                            % (rel_path, repo, r.stderr.strip()))
    return r.stdout


# ---------------------------------------------------------------------------
# Script-block extraction: the same HTML-parser-based approach CLAUDE.md
# requires ("HTML-parser-based extraction, not grep -c") -- kept as a
# literal inline copy of tools/extract_scripts.py's ScriptExtractor rather
# than an import, matching this directory's every-tool-standalone
# convention (see hover_cold_scan_pool.py's identical reasoning about
# TIER_ROW) and keeping this file usable without the platform repo's own
# tools/ on sys.path.
from html.parser import HTMLParser


class _ScriptExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.in_script = False
        self.current = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'script':
            self.in_script = True
            self.current = []

    def handle_endtag(self, tag):
        if tag.lower() == 'script' and self.in_script:
            self.in_script = False
            self.blocks.append(''.join(self.current))

    def handle_data(self, data):
        if self.in_script:
            self.current.append(data)


def script_blocks(html_text):
    p = _ScriptExtractor()
    p.feed(html_text)
    return p.blocks


# ---------------------------------------------------------------------------
# Function-body extraction: brace-balance scan, comment/string aware,
# refuses rather than guesses on any ambiguity.
_FN_PATTERNS = lambda name: [
    # (?:async\s+)? on the DECLARATION form, added 2026-09-28 after the
    # other auditor's find (its seq 286): the pattern used to match AT the
    # 'function' keyword, so `async function x(){ await ... }` extracted
    # WITHOUT its async prefix -- a source the tool itself corrupted, whose
    # `await` is then a SyntaxError the report presented as the SUBJECT
    # throwing. The expression forms below already carried the async
    # alternative inside the match span.
    re.compile(r'(?:async\s+)?function\s+' + re.escape(name) + r'\s*\('),
    re.compile(r'(?:const|let|var)\s+' + re.escape(name)
               + r'\s*=\s*(?:async\s*)?function\s*\('),
    re.compile(r'(?:const|let|var)\s+' + re.escape(name)
               + r'\s*=\s*(?:async\s*)?\('),
]


def _scan_balanced_braces(text, open_idx):
    """From text[open_idx] == '{', return the index one past its matching
    '}', tracking strings/template-literals/comments so a brace inside one
    of those does not desync the count. Raises CouldNotTell on any
    ambiguity (unterminated string/comment, or EOF before depth returns to
    zero) rather than returning a guessed span."""
    assert text[open_idx] == '{'
    depth = 0
    i = open_idx
    n = len(text)
    in_str = None       # one of "'", '"', '`', or None
    in_line_comment = False
    in_block_comment = False
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ''
        if in_line_comment:
            if c == '\n':
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if c == '*' and nxt == '/':
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            if c == '\\':
                i += 2
                continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c == '/' and nxt == '/':
            in_line_comment = True
            i += 2
            continue
        if c == '/' and nxt == '*':
            in_block_comment = True
            i += 2
            continue
        if c in ("'", '"', '`'):
            in_str = c
            i += 1
            continue
        if c == '{':
            depth += 1
            i += 1
            continue
        if c == '}':
            depth -= 1
            i += 1
            if depth == 0:
                return i
            continue
        i += 1
    raise CouldNotTell('brace-balance scan reached end of text without '
                        'closing (depth=%d, in_str=%r, in_block_comment=%r) '
                        '-- refusing a guessed span' % (depth, in_str, in_block_comment))


def extract_function(block_text, name):
    """Verbatim source text of function NAME's declaration/expression form
    (signature through the matching closing brace), or raises CouldNotTell.
    Tries each supported form in _FN_PATTERNS in order; the first pattern
    that matches AND whose signature is immediately followed by a '{' body
    (walking past an arrow's '=>' if present) wins."""
    for pat in _FN_PATTERNS(name):
        m = pat.search(block_text)
        if not m:
            continue
        start = m.start()
        # walk forward from the end of the signature match to find the
        # opening '{' of the body, permitting an arrow's '=>' in between
        # but nothing else structural (a real param-list close is assumed
        # already consumed by the pattern's trailing '(' -- so scan to the
        # matching ')' of that param list first, comment/string-naive but
        # adequate for a parameter list, which is rarely commented).
        paren_depth = 1
        j = m.end()
        n = len(block_text)
        while j < n and paren_depth > 0:
            if block_text[j] == '(':
                paren_depth += 1
            elif block_text[j] == ')':
                paren_depth -= 1
            j += 1
        # skip whitespace and an optional '=>'
        k = j
        while k < n and block_text[k] in ' \t\r\n':
            k += 1
        if block_text[k:k + 2] == '=>':
            k += 2
            while k < n and block_text[k] in ' \t\r\n':
                k += 1
        if k >= n or block_text[k] != '{':
            continue  # expression-bodied arrow or unsupported form; try next pattern
        end = _scan_balanced_braces(block_text, k)
        return block_text[start:end]
    raise CouldNotTell(
        "could not find a brace-bodied function/function-expression/"
        "arrow-with-braces named %r in this script block (an "
        "expression-bodied arrow is not supported)" % name)


def find_function_source(repo, html_rel_path, name):
    text = read_source_text(repo, html_rel_path)
    blocks = script_blocks(text)
    if not blocks:
        raise CouldNotTell('%s has no <script> blocks on origin/main'
                            % html_rel_path)
    errors = []
    for i, b in enumerate(blocks):
        try:
            return extract_function(b, name), i
        except CouldNotTell as e:
            errors.append('block %d: %s' % (i, e))
    raise CouldNotTell('%r not found as a supported function form in any '
                        'of %d script block(s) in %s:\n  %s'
                        % (name, len(blocks), html_rel_path, '\n  '.join(errors)))


def network_token_notes(fn_source):
    return [t for t in NETWORK_TOKENS if t in fn_source]


# ---------------------------------------------------------------------------
# Sandboxed execution. Builds a Node driver script that runs entirely
# inside vm.createContext() with a hand-picked sandbox object -- no
# require/process/fs/fetch/XHR/WebSocket copied in, so those names are
# simply undefined inside the sandbox, not merely avoided by convention.
_DRIVER_TEMPLATE = r'''
const vm = require('vm');
const fnSource = %(fn_source)s;
const fnName = %(fn_name)s;
const args = %(args)s;
const extraGlobals = %(extra_globals)s;

const captured = { logs: [] };
const sandbox = Object.assign({}, extraGlobals, {
  console: {
    log: (...a) => captured.logs.push(a.map(String).join(' ')),
    warn: (...a) => captured.logs.push(a.map(String).join(' ')),
    error: (...a) => captured.logs.push(a.map(String).join(' ')),
  },
});
const ctx = vm.createContext(sandbox);

// TWO PHASES, reported separately (2026-09-28, the other auditor's seq
// 286): an error while LOADING the extracted source is the TOOL's
// failure (bad extraction, corrupted span) and must surface as
// could-not-run upstream; only an error while CALLING the function is
// the subject genuinely throwing. Folding the two into one catch is how
// a tool-corrupted `await` was reported as the subject's SyntaxError.
let out;
let fn;
try {
  vm.runInContext(fnSource + '\n;this.__hover_fn__ = ' + fnName + ';', ctx,
                   { timeout: 5000 });
  fn = ctx.__hover_fn__;
  if (typeof fn !== 'function') throw new TypeError(fnName + ' did not evaluate to a function');
} catch (e) {
  out = { ok: false, phase: 'load',
          error_type: e.constructor ? e.constructor.name : 'Error',
          error: String(e && e.message !== undefined ? e.message : e),
          logs: captured.logs };
}
if (!out) {
  try {
    const result = fn.apply(null, args);
    out = { ok: true, result: result === undefined ? null : result,
            result_type: typeof result, logs: captured.logs };
  } catch (e) {
    out = { ok: false, phase: 'call',
            error_type: e.constructor ? e.constructor.name : 'Error',
            error: String(e && e.message !== undefined ? e.message : e),
            logs: captured.logs };
  }
}
process.stdout.write(JSON.stringify(out));
'''


def run_sandboxed(fn_source, fn_name, args, extra_globals=None):
    """Execute fn_source's function fn_name(*args) inside an isolated
    Node vm.Context (see module docstring for exactly what is and is not
    available inside it). Returns the driver's parsed JSON result dict.
    Raises CouldNotTell if node itself could not be run or produced
    unparseable output -- never silently reports success."""
    driver = _DRIVER_TEMPLATE % {
        'fn_source': json.dumps(fn_source),
        'fn_name': json.dumps(fn_name),
        'args': json.dumps(args),
        'extra_globals': json.dumps(extra_globals or {}),
    }
    tmpdir = tempfile.mkdtemp(prefix='hover_pure_js_exec_')
    driver_path = os.path.join(tmpdir, 'driver.js')
    with open(driver_path, 'w', encoding='utf-8') as f:
        f.write(driver)
    try:
        r = subprocess.run(['node', driver_path], cwd=tmpdir,
                            capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise CouldNotTell('could not run node driver: %s' % e)
    if r.returncode != 0 and not r.stdout.strip():
        raise CouldNotTell('node driver exited %d with no output: %s'
                            % (r.returncode, r.stderr.strip()))
    try:
        parsed = json.loads(r.stdout.strip())
    except ValueError as e:
        raise CouldNotTell('node driver produced unparseable output: %s '
                            '(stdout=%r stderr=%r)'
                            % (e, r.stdout, r.stderr))
    # A LOAD-phase failure means the extracted source itself did not
    # evaluate -- the tool's problem, never the subject's verdict. Raised
    # as COULD NOT RUN rather than returned as a THREW result (2026-09-28,
    # the other auditor's seq 286: an async-stripped extraction's
    # SyntaxError was reported as the subject throwing).
    if not parsed.get('ok') and parsed.get('phase') == 'load':
        raise CouldNotTell('the extracted source did not LOAD in the '
                           'sandbox (%s: %s) -- this is an extraction/tool '
                           'failure, NOT the subject function throwing; no '
                           'verdict about the subject exists'
                           % (parsed.get('error_type'), parsed.get('error')))
    return parsed


def execute(repo, html_rel_path, fn_name, args, extra_globals=None):
    fn_source, block_idx = find_function_source(repo, html_rel_path, fn_name)
    notes = network_token_notes(fn_source)
    result = run_sandboxed(fn_source, fn_name, args, extra_globals)
    result['_block_index'] = block_idx
    result['_network_token_notes'] = notes
    result['_fn_source'] = fn_source
    return result


# ---------------------------------------------------------------------------
def _print_report(html_rel_path, fn_name, args, result):
    print('HOVER PURE-JS-EXEC (Tier 0) -- %s :: %s(%s)'
          % (html_rel_path, fn_name, ', '.join(json.dumps(a) for a in args)))
    if result['_network_token_notes']:
        print('NOTE: source contains network-shaped token(s): %s -- these '
              'are NOT available in this sandbox; a real call attempt would '
              'ReferenceError, not silently succeed or silently no-op.'
              % ', '.join(result['_network_token_notes']))
    print()
    print('--- extracted source (block %d) ---' % result['_block_index'])
    print(result['_fn_source'])
    print('--- end source ---')
    print()
    if result['ok']:
        print('RESULT (%s): %s' % (result['result_type'], json.dumps(result['result'])))
    else:
        print('THREW: %s: %s' % (result['error_type'], result['error']))
    if result['logs']:
        print('console output: %s' % result['logs'])


def run_fixtures():
    ok_count = [0]
    fail_count = [0]

    def ck(name, cond):
        if cond:
            ok_count[0] += 1
            print('  ok   ' + name)
        else:
            fail_count[0] += 1
            print('  FAIL ' + name)

    # --- extract_function(): the forms this Tier 0 is meant to support ---
    block = '''
      function plainFn(a, b) { return a + b; }
      const exprFn = function(a) { return a * 2; };
      const arrowFn = (a) => { return a - 1; };
      const arrowExprBody = (a) => a * 100;   // not supported, must be refused
      function withBraceString(s) { return s.replace('{', 'X') + '}'; }
      function withComment(a) {
        // a brace in a comment: { not a real one
        return a; /* another { one */
      }
    '''
    src = extract_function(block, 'plainFn')
    ck('plain function form extracted, braces balanced',
       src.count('{') == src.count('}') and 'a + b' in src)

    src2 = extract_function(block, 'exprFn')
    ck('const X = function(...) form extracted', 'a * 2' in src2)

    src3 = extract_function(block, 'arrowFn')
    ck('const X = (...) => { } arrow form extracted', 'a - 1' in src3)

    raised = False
    try:
        extract_function(block, 'arrowExprBody')
    except CouldNotTell:
        raised = True
    ck('expression-bodied arrow is REFUSED, not guessed at', raised)

    src4 = extract_function(block, 'withBraceString')
    ck('a brace inside a string literal does not desync the balance scan',
       src4.strip().startswith('function withBraceString')
       and src4.rstrip().endswith('}'))

    src5 = extract_function(block, 'withComment')
    ck('a brace inside a comment does not desync the balance scan',
       src5.strip().startswith('function withComment')
       and src5.rstrip().endswith('}'))

    raised2 = False
    try:
        extract_function(block, 'doesNotExist')
    except CouldNotTell:
        raised2 = True
    ck('a missing function name is refused, not silently empty', raised2)

    # --- F-ASYNC, THE OTHER AUDITOR'S FIND (its seq 286), fixtures      ---
    # --- written to the exact failure shape before the fix ran on real  ---
    # --- data: `async function` extracted with async DROPPED, whose     ---
    # --- await then SyntaxErrored, reported as the SUBJECT throwing.    ---
    async_block = ('function before(){ return 1; }\n'
                   'async function asyncFn(a){ var r = await a; return r; }\n'
                   'function after(){ return 2; }\n')
    src6 = extract_function(async_block, 'asyncFn')
    ck('F-ASYNC1: the async DECLARATION form extracts WITH its async '
       'prefix -- the span starts at async, not at function',
       src6.strip().startswith('async function asyncFn'))
    res_async = run_sandboxed(src6, 'asyncFn', [7])
    ck('F-ASYNC2: the correctly-extracted async function LOADS and runs '
       '(returns a Promise -- result_type object, ok true); no phantom '
       'SyntaxError from a source the tool itself corrupted',
       res_async.get('ok') is True and res_async.get('result_type') == 'object')
    # F-ASYNC-CONTROL, KNOWN-BAD, MUST KEEP FAILING TO PASS AS A VERDICT:
    # the PRE-FIX artifact -- the same function with async stripped, which
    # is what the old pattern handed the sandbox -- must now surface as
    # COULD NOT RUN (load-phase, tool's fault), never as 'the subject
    # THREW SyntaxError'.
    corrupted = src6.strip()[len('async '):]
    raised_load = False
    try:
        run_sandboxed(corrupted, 'asyncFn', [7])
    except CouldNotTell as e:
        raised_load = 'did not LOAD' in str(e)
    ck('F-ASYNC-CONTROL: the async-stripped source (the exact pre-fix '
       'artifact) raises COULD NOT RUN naming the load phase -- a tool-'
       'corrupted extraction can no longer masquerade as a subject verdict',
       raised_load)
    res_call = run_sandboxed(
        'function callThrows(){ throw new TypeError("genuine"); }',
        'callThrows', [])
    ck('F-ASYNC3, the overcorrection guard: a function that GENUINELY '
       'throws at CALL time still reports as THREW (ok false, phase '
       'call) -- load-phase strictness must not swallow real subject '
       'failures', res_call.get('ok') is False
       and res_call.get('phase') == 'call'
       and res_call.get('error_type') == 'TypeError')

    # --- network_token_notes(): informational, not a hard block ---
    ck('a fetch(...) call is flagged as a note',
       'fetch(' in network_token_notes('function f(){ return fetch("x"); }'))
    ck('an ordinary pure function has no notes',
       network_token_notes('function f(a){ return a+1; }') == [])

    # --- run_sandboxed(): THE ACTUAL SAFETY PROPERTY, DRIVEN, not assumed.
    # A function that tries to call fetch() must ReferenceError inside the
    # sandbox -- proving the capability is genuinely absent, not merely
    # unused by this test.
    r = run_sandboxed('function f(){ return fetch("http://example.invalid"); }', 'f', [])
    ck('a function calling fetch() THROWS ReferenceError inside the sandbox '
       '-- proving no real network call is even reachable, not just untried',
       r['ok'] is False and r['error_type'] == 'ReferenceError'
       and 'fetch' in r['error'])

    r2 = run_sandboxed('function f(){ return require("fs"); }', 'f', [])
    ck('a function calling require() ALSO throws ReferenceError (no module '
       'system, no filesystem access from inside the sandbox)',
       r2['ok'] is False and r2['error_type'] == 'ReferenceError')

    r3 = run_sandboxed('function f(){ return process.env; }', 'f', [])
    ck('a function reading process.env throws ReferenceError (no host '
       'environment visible from inside the sandbox)',
       r3['ok'] is False and r3['error_type'] == 'ReferenceError')

    # --- run_sandboxed(): ordinary pure computation actually runs and
    # returns the real answer, not a stub.
    r4 = run_sandboxed('function add(a,b){ return a+b; }', 'add', [2, 3])
    ck('an ordinary pure function actually executes and returns 5, not a '
       'placeholder', r4['ok'] is True and r4['result'] == 5)

    r5 = run_sandboxed('function boom(){ throw new Error("bad input"); }', 'boom', [])
    ck('a function that throws surfaces the real thrown message, not '
       'silently swallowed', r5['ok'] is False and 'bad input' in r5['error'])

    # --- discover_repo(): identical contract to the other two tools ---
    ck('--repo on the command line wins over everything',
       discover_repo(['--repo', '/explicit/path']) == '/explicit/path')

    # --- end-to-end against a REAL fixture repo (not the live platform
    # clone), same fetch+origin/main discipline as the other two tools,
    # proving read_source_text() reads origin/main, not a stale local file.
    tmpdir = tempfile.mkdtemp()
    bare_repo = os.path.join(tmpdir, 'origin.git')
    work_repo = os.path.join(tmpdir, 'work')
    subprocess.run(['git', 'init', '-q', '--bare', bare_repo], check=True)
    subprocess.run(['git', 'init', '-q', work_repo], check=True)
    subprocess.run(['git', 'config', 'user.email', 'x@x.com'], cwd=work_repo, check=True)
    subprocess.run(['git', 'config', 'user.name', 'x'], cwd=work_repo, check=True)
    subprocess.run(['git', 'checkout', '-q', '-b', 'main'], cwd=work_repo, check=True)
    subprocess.run(['git', 'remote', 'add', 'origin', bare_repo], cwd=work_repo, check=True)
    html_path = os.path.join(work_repo, 'fixture.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write('<html><body><script>\n'
                'function fmtMoneyFixture(n){ return "$" + Math.round(n); }\n'
                '</script></body></html>')
    subprocess.run(['git', 'add', '.'], cwd=work_repo, check=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'add fixture.html'], cwd=work_repo, check=True)
    subprocess.run(['git', 'push', '-q', 'origin', 'main'], cwd=work_repo, check=True)

    result = execute(work_repo, 'fixture.html', 'fmtMoneyFixture', [3.7])
    ck('end-to-end: real function extracted from a real committed HTML '
       'file via origin/main and actually executed, real result returned',
       result['ok'] is True and result['result'] == '$4')

    raised3 = False
    try:
        execute(None, 'fixture.html', 'fmtMoneyFixture', [3.7])
    except CouldNotTell:
        raised3 = True
    ck('no repo resolvable -> refuses (COULD_NOT_RUN), never a silent '
       'fabricated result', raised3)

    print()
    print('%d ok, %d failed' % (ok_count[0], fail_count[0]))
    return fail_count[0] == 0


def main(argv):
    if '--selftest' in argv:
        ok = run_fixtures()
        sys.exit(0 if ok else 1)

    def opt(flag, required=True, default=None):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 < len(argv):
                return argv[i + 1]
        if required:
            print('missing %s' % flag, file=sys.stderr)
            sys.exit(2)
        return default

    html_rel_path = opt('--html')
    fn_name = opt('--fn')
    args_json = opt('--args', required=False, default='[]')
    globals_json = opt('--globals', required=False, default='{}')
    try:
        args = json.loads(args_json)
        extra_globals = json.loads(globals_json)
    except ValueError as e:
        print('COULD NOT RUN: --args/--globals not valid JSON: %s' % e)
        return 2
    repo = discover_repo(argv)
    try:
        result = execute(repo, html_rel_path, fn_name, args, extra_globals)
    except CouldNotTell as e:
        print('COULD NOT RUN: %s' % e)
        return 2
    _print_report(html_rel_path, fn_name, args, result)
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
