#!/usr/bin/env python
"""hover_tier0_exec.py -- Tier 0 pure-function live execution.

Built independently from H1's published interface spec
(.claude/skills/sairn-hover-auditor/SKILL.md, commit 1b66a71e, "Spec 2 --
live execution, two tiers"). Interface only -- no source seen or copied.

WHAT THIS CLOSES. Anthropic's own published finding: audit realism jumps
from roughly 4.6% to roughly 32.8% when checking against real deployment
conditions instead of synthetic ones. Every hover2 finding up to this point
was confirmed by reading source against documented semantics -- never by
actually running anything.

WHAT IT DOES. Given an app's HTML file, a function name, and caller-
supplied synthetic arguments: extracts the function's own verbatim source
via a brace-balanced scan over the real inline <script> block boundaries
(HTML-parser-based, never a regex across the whole page -- the same
Check-0a discipline this platform already requires everywhere else), then
executes that extracted source inside a Node vm context that provides NO
ambient fetch/XMLHttpRequest/WebSocket/require/process/console/setTimeout
-- so a function that tries to reach the network, the filesystem, or any
host capability gets a REAL ReferenceError from the JS engine itself,
because the capability is not there to reach, never because this tool
chose to intercept a call it recognised.

REFUSES rather than guesses when the span cannot be reliably isolated:
an unsupported function-definition form, more than one candidate
definition found, or an unterminated string/template/comment/brace run
at end of scan.

Reads the app source from origin/main, fetched fresh via git, never a
possibly-stale local working tree -- consistent with the --source
staleness guard this same clone already carries on its self-log.

    python hover_tier0_exec.py --app sairnvet.html --function fdate \\
        --args '["2026-09-23"]'
    python hover_tier0_exec.py --selftest
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser

DEFAULT_PLATFORM_REPO = os.environ.get(
    'HOVER_PLATFORM_REPO', r'C:\Users\marsh\Documents\SAIRN-hover2')
NODE = os.environ.get('HOVER_NODE_BIN', 'node')


class RefuseExtraction(Exception):
    """Raised whenever the span cannot be RELIABLY isolated -- never
    guessed past. Every raise site here is a named, specific reason, not
    a bare 'could not extract'."""


def _run(args, timeout=20, input_text=None):
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          input=input_text, encoding='utf-8', errors='replace',
                          timeout=timeout)
        return p.returncode, p.stdout or '', p.stderr or ''
    except subprocess.TimeoutExpired:
        return None, '', 'TIMEOUT after %ss' % timeout
    except OSError as exc:
        return None, '', 'could not run %s: %s' % (args[0], exc)


def fetch_app_source(app_path, repo=None, ref='origin/main', fetch_timeout=25):
    """Reads the app's HTML straight from origin/main -- fetched fresh
    first, never a possibly-stale local working tree, matching the same
    incident-prevention reasoning as the --source staleness guard."""
    repo = repo or DEFAULT_PLATFORM_REPO
    remote = ref.split('/', 1)[0]
    branch = ref.split('/', 1)[1] if '/' in ref else 'main'
    rc, _out, err = _run(['git', '-C', repo, 'fetch', remote, branch],
                        timeout=fetch_timeout)
    if rc != 0:
        raise RuntimeError('could not fetch %s to read %r fresh: %s'
                          % (ref, app_path, err.strip() or 'unknown error'))
    rc, out, err = _run(['git', '-C', repo, 'show', '%s:%s' % (ref, app_path)])
    if rc != 0:
        raise RuntimeError('could not read %s:%s -- %s'
                          % (ref, app_path, err.strip() or 'unknown error'))
    return out


class _InlineScriptFinder(HTMLParser):
    """A real HTML parser (stdlib html.parser), not a regex scan across the
    whole page -- the same discipline CLAUDE.md names for counting <script>
    blocks (sairn-guardian-v2 Check 0a). Collects the raw text of every
    inline <script> (no src=) with its offset in the ORIGINAL document, so
    a later report can cite a real line number."""

    def __init__(self, raw):
        super().__init__(convert_charrefs=False)
        self.raw = raw
        self.blocks = []  # (start_offset, text)
        self._in_inline_script = False
        self._start = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'script':
            has_src = any(k.lower() == 'src' for k, _v in attrs)
            if not has_src:
                self._in_inline_script = True
                # getpos() is (line, col); resolve to an offset via a running
                # scan rather than trusting col across multi-byte content --
                # HTMLParser's own line/col is 1-indexed line, 0-indexed col.
                line, col = self.getpos()
                self._start = self._offset_of(line, col) + len(self.get_starttag_text())

    def handle_endtag(self, tag):
        if tag.lower() == 'script' and self._in_inline_script:
            line, col = self.getpos()
            end = self._offset_of(line, col)
            self.blocks.append((self._start, self.raw[self._start:end]))
            self._in_inline_script = False
            self._start = None

    def _offset_of(self, line, col):
        # Cache line-start offsets once; called often enough during a 2MB
        # file that a linear rescan per call would be needlessly slow.
        if not hasattr(self, '_line_starts'):
            starts = [0]
            for i, ch in enumerate(self.raw):
                if ch == '\n':
                    starts.append(i + 1)
            self._line_starts = starts
        return self._line_starts[line - 1] + col


def extract_script_blocks(html_text):
    p = _InlineScriptFinder(html_text)
    p.feed(html_text)
    return p.blocks


# --- brace-balanced function-source extraction --------------------------

_FUNC_PATTERNS = [
    # function NAME(...) {
    r'(?<![\w$.])(?:async\s+)?function\s+{name}\s*\([^)]*\)\s*\{{',
    # NAME = function(...) {   /  NAME=function(...){
    r'(?<![\w$.]){name}\s*=\s*(?:async\s+)?function\s*\([^)]*\)\s*\{{',
    # NAME: function(...) {    (old-style object method)
    r'(?<![\w$.])[\'"]?{name}[\'"]?\s*:\s*(?:async\s+)?function\s*\([^)]*\)\s*\{{',
    # NAME = (...) => {        (braced-body arrow only -- concise-body
    # arrows have no brace to balance against and are refused, not guessed)
    r'(?<![\w$.]){name}\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{{',
]


def _find_definition_start(script_text, function_name):
    """Returns (match_start, brace_index) for the ONE definition of
    function_name this script block contains, across the supported forms
    above. Refuses if zero or more-than-one candidate is found -- multiple
    candidates mean the definition cannot be reliably isolated without a
    real JS parser, and this tool does not pretend to be one."""
    name_re = re.escape(function_name)
    candidates = []
    for pat in _FUNC_PATTERNS:
        for m in re.finditer(pat.format(name=name_re), script_text):
            candidates.append((m.start(), m.end() - 1))  # end-1 = the '{' index
    if not candidates:
        raise RefuseExtraction(
            'no supported function-definition form found for %r in this '
            'script block (supported: `function NAME(...) {}`, '
            '`NAME = function(...) {}`, `NAME: function(...) {}`, '
            '`NAME = (...) => {}` with a braced body)' % function_name)
    if len(candidates) > 1:
        raise RefuseExtraction(
            '%d candidate definitions found for %r -- cannot reliably '
            'isolate which one is the real definition without a full JS '
            'parser, refusing rather than guessing' % (len(candidates), function_name))
    return candidates[0]


_REGEX_CONTEXT_KEYWORDS = frozenset((
    'return', 'typeof', 'instanceof', 'in', 'of', 'new', 'delete', 'void',
    'throw', 'case', 'do', 'else', 'yield', 'await'))


def _is_regex_context(text, i):
    """True if a '/' at text[i] plausibly STARTS a regex literal rather
    than being division -- found necessary the hard way: `.replace(/"/g,
    ...)` (an ordinary HTML-escape idiom) contains a literal '"' INSIDE a
    regex literal, which a scanner that only tracks strings/templates/
    comments (as the interface spec names) misreads as the START of a
    double-quoted string, then swallows everything up to the next real
    quote character anywhere later in the file -- silently extracting the
    WRONG, over-long span rather than the true function body. Caught by
    running this tool for real against a live platform function (H() in
    sairnlaw.html), not by inspection -- exactly the 'proven against real
    deployment conditions, not synthetic' standard this whole capability
    exists to bring to every OTHER finding. The heuristic: look at the last
    non-whitespace character before the '/'. An operand just having ended
    (identifier, number, ')', ']', '}', a closed string/template) means
    division; anything else -- an operator, punctuation, a keyword like
    `return`/`typeof`, or the very start of a statement -- means a regex
    literal is about to start."""
    j = i - 1
    while j >= 0 and text[j] in ' \t\n\r':
        j -= 1
    if j < 0:
        return True
    c = text[j]
    if c in ')]}':
        return False
    if c.isalnum() or c in '_$':
        k = j
        while k >= 0 and (text[k].isalnum() or text[k] in '_$'):
            k -= 1
        word = text[k + 1:j + 1]
        return word in _REGEX_CONTEXT_KEYWORDS
    if c in '"\'`':
        return False
    return True


def _skip_regex_literal(text, i):
    """text[i] == '/' and _is_regex_context() said this starts a regex.
    Returns the index just past the literal's closing '/' and any trailing
    flags. Tracks character classes ([...]) since a '/' inside one does not
    close the literal, and escapes within it. Raises RefuseExtraction on a
    newline or end-of-text before the literal closes -- a real regex
    literal cannot span a raw newline in JS, so hitting one here means the
    '/' was misclassified or the file is malformed; refuse either way
    rather than guess."""
    n = len(text)
    j = i + 1
    in_class = False
    while True:
        if j >= n:
            raise RefuseExtraction(
                'reached end of file inside what looked like a regex literal '
                '-- the function span could not be reliably closed')
        c = text[j]
        if c == '\\':
            j += 2; continue
        if c == '\n':
            raise RefuseExtraction(
                'a regex literal appeared to run across a raw newline -- '
                'either malformed source or a division sign misread as a '
                'regex start; refusing rather than guessing which')
        if c == '[':
            in_class = True; j += 1; continue
        if c == ']':
            in_class = False; j += 1; continue
        if c == '/' and not in_class:
            j += 1
            break
        j += 1
    while j < n and text[j].isalpha():
        j += 1
    return j


def _scan_balanced(text, brace_index):
    """text[brace_index] must be '{'. Returns the index just PAST its
    matching closing brace, tracking single/double-quoted strings,
    template literals (including nested ${...} expressions, which get
    their own independent brace-depth frame), regex literals, and
    line/block comments -- so a brace (or a quote character INSIDE a
    regex literal) never desyncs the count. Raises
    RefuseExtraction on any unterminated construct at end of text."""
    assert text[brace_index] == '{'
    n = len(text)
    stack = [1]  # depth of the current 'code' frame; starts at 1 for the
                 # opening brace already consumed below
    i = brace_index + 1
    str_state = None  # None | 'single' | 'double' | 'line' | 'block'
    in_template = [False]  # top-of-stack-relative; parallel list, same length as stack

    def push_code():
        stack.append(1)
        in_template.append(False)

    def pop_code():
        stack.pop()
        in_template.pop()

    while True:
        if i >= n:
            raise RefuseExtraction(
                'reached end of file while still balancing braces/strings/'
                'templates/comments -- the function span could not be '
                'reliably closed')
        c = text[i]
        if str_state == 'single' or str_state == 'double':
            quote = "'" if str_state == 'single' else '"'
            if c == '\\':
                i += 2; continue
            if c == quote:
                str_state = None
            i += 1; continue
        if str_state == 'line':
            if c == '\n':
                str_state = None
            i += 1; continue
        if str_state == 'block':
            if c == '*' and text[i + 1:i + 2] == '/':
                str_state = None; i += 2; continue
            i += 1; continue

        if in_template[-1]:
            if c == '\\':
                i += 2; continue
            if c == '`':
                # closes the template -- pop back to the code frame that
                # opened it (a template is always entered from code, never
                # from another template directly)
                in_template.pop()
                i += 1
                continue
            if c == '$' and text[i + 1:i + 2] == '{':
                push_code()
                i += 2
                continue
            i += 1; continue

        # plain code context
        if c == '/' and text[i + 1:i + 2] == '/':
            str_state = 'line'; i += 2; continue
        if c == '/' and text[i + 1:i + 2] == '*':
            str_state = 'block'; i += 2; continue
        if c == '/' and _is_regex_context(text, i):
            i = _skip_regex_literal(text, i); continue
        if c == "'":
            str_state = 'single'; i += 1; continue
        if c == '"':
            str_state = 'double'; i += 1; continue
        if c == '`':
            in_template.append(True); i += 1; continue
        if c == '{':
            stack[-1] += 1; i += 1; continue
        if c == '}':
            stack[-1] -= 1
            i += 1
            if stack[-1] == 0:
                if len(stack) == 1:
                    return i  # this is the function's own closing brace
                # this closed a ${ ... } expression -- pop back to template
                pop_code()
            continue
        i += 1; continue


CONFLICT_MARKER_RE = re.compile(r'^(<{7}|={7}|>{7})', re.M)


def extract_function_source(html_text, function_name):
    """Returns (source_text, script_block_index, start_offset). Raises
    RefuseExtraction with a specific reason on anything that cannot be
    reliably isolated. Conflict-marker sweep, 2026-09-28: unresolved git
    conflict markers refuse extraction outright -- this reads committed
    origin/main content, where markers should be impossible, but this
    platform's own history carries multiple rebase-reseat commits from
    real conflict churn, and a brace-balanced scan over a conflicted file
    would silently extract from whichever side balanced first; a function
    executed from half a merge proves nothing about either half."""
    if CONFLICT_MARKER_RE.search(html_text):
        raise RefuseExtraction(
            'the document carries unresolved git conflict markers -- a '
            'brace-balanced extraction over a conflicted file would '
            'silently serve one side of the merge; resolve first')
    blocks = extract_script_blocks(html_text)
    if not blocks:
        raise RefuseExtraction('no inline <script> blocks found in this document at all')
    all_hits = []
    for bi, (offset, text) in enumerate(blocks):
        try:
            match_start, brace_index = _find_definition_start(text, function_name)
        except RefuseExtraction as exc:
            if 'no supported function-definition form' in str(exc):
                continue  # just means: not in THIS block, keep looking
            raise  # a real ambiguity inside one block is not swallowed
        all_hits.append((bi, offset, text, match_start, brace_index))
    if not all_hits:
        raise RefuseExtraction(
            'no supported function-definition form for %r found in any of '
            'the %d inline <script> block(s)' % (function_name, len(blocks)))
    if len(all_hits) > 1:
        raise RefuseExtraction(
            '%d candidate definitions for %r found across separate <script> '
            'blocks -- cannot reliably isolate which one is real, refusing '
            'rather than guessing' % (len(all_hits), function_name))
    bi, offset, text, match_start, brace_index = all_hits[0]
    end = _scan_balanced(text, brace_index)
    source = text[match_start:end]
    return source, bi, offset + match_start


# --- Node sandbox execution ----------------------------------------------

_HARNESS = r"""
const vm = require('vm');
const fs = require('fs');
const funcSource = fs.readFileSync(process.argv[2], 'utf8');
const args = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const funcName = process.argv[4];

// The sandbox starts as a genuinely bare object -- NOTHING is added to it.
// No fetch, no XMLHttpRequest, no WebSocket, no require, no process, no
// console, no setTimeout/setInterval, no module/exports. Anything the
// extracted function reaches for that is not a real ECMAScript language
// builtin gets a real ReferenceError from V8 itself.
const sandbox = {};
vm.createContext(sandbox);
sandbox.__hoverArgs = args;

const wrapped = funcSource + '\n;globalThis.__hoverResult = (function(){' +
  'try { var r = (typeof ' + funcName + " === 'function') ? " + funcName +
  '.apply(null, globalThis.__hoverArgs) : undefined;' +
  "if (typeof " + funcName + " !== 'function') { return {ok:false, error:{name:'TypeError', message:'" +
  funcName + " is not a function after executing its own extracted source'}}; }" +
  'return {ok:true, result: r}; ' +
  '} catch(e) { return {ok:false, error:{name: (e && e.constructor && e.constructor.name) || typeof e, message: e && e.message}}; } ' +
  '})();';

try {
  vm.runInContext(wrapped, sandbox, {timeout: 5000});
  process.stdout.write(JSON.stringify(sandbox.__hoverResult));
} catch (e) {
  // A SyntaxError or an uncaught throw escaping the wrapper's own try --
  // should not happen given the wrapper catches everything from the call,
  // but a syntax error in funcSource itself throws here, before the
  // wrapper's try even starts running.
  process.stdout.write(JSON.stringify({ok:false, error:{name:(e && e.constructor && e.constructor.name) || 'Error', message: e && e.message, phase:'compile'}}));
}
"""


def run_tier0(app_path, function_name, args_json, repo=None, ref='origin/main'):
    """The full pipeline: fetch fresh app source from origin/main, extract
    the one function's verbatim source via the brace-balanced scan, run it
    in a bare vm sandbox with the supplied synthetic args. Returns a dict:
    {ok, result_or_error, extracted:{block_index, char_offset, source_len}}.
    Raises RefuseExtraction (never silently falls back to a guess) or
    RuntimeError (git/node infrastructure failure)."""
    html_text = fetch_app_source(app_path, repo=repo, ref=ref)
    source, block_index, offset = extract_function_source(html_text, function_name)
    args = json.loads(args_json)

    tmpdir = tempfile.mkdtemp(prefix='hover-tier0-')
    try:
        src_path = os.path.join(tmpdir, 'func_source.js')
        args_path = os.path.join(tmpdir, 'args.json')
        harness_path = os.path.join(tmpdir, 'harness.js')
        with io.open(src_path, 'w', encoding='utf-8') as f:
            f.write(source)
        with io.open(args_path, 'w', encoding='utf-8') as f:
            json.dump(args, f)
        with io.open(harness_path, 'w', encoding='utf-8') as f:
            f.write(_HARNESS)
        rc, out, err = _run([NODE, harness_path, src_path, args_path, function_name],
                           timeout=10)
        if rc != 0:
            raise RuntimeError('node harness failed (exit %s): %s' % (rc, err.strip()))
        try:
            outcome = json.loads(out)
        except ValueError:
            raise RuntimeError('node harness produced non-JSON output: %r' % out[:2000])
        return {
            'ok': outcome.get('ok'),
            'result': outcome.get('result'),
            'error': outcome.get('error'),
            'extracted': {
                'app': app_path, 'function': function_name,
                'script_block_index': block_index,
                'char_offset': offset, 'source_len': len(source),
                'ref': ref,
            },
        }
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--app')
    ap.add_argument('--function')
    ap.add_argument('--args', default='[]')
    ap.add_argument('--repo', default=None)
    ap.add_argument('--ref', default='origin/main')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.app or not args.function:
        print(__doc__); return 0
    try:
        result = run_tier0(args.app, args.function, args.args, repo=args.repo, ref=args.ref)
    except (RefuseExtraction, RuntimeError) as exc:
        print('REFUSED: %s' % exc); return 2
    print(json.dumps(result, indent=2))
    return 0 if result['ok'] else 1


def selftest():
    bad = []
    total = [0]

    def ck(name, cond):
        total[0] += 1
        ok = bool(cond)
        print(('  ok   ' if ok else '  FAIL ') + name)
        if not ok:
            bad.append(name)

    # -- extraction correctness, offline, no git/node involved --
    html = '''<html><body>
<script>
function addTwo(a, b) { return a + b; }
function withString() { var s = "a } fake brace"; return s.length; }
function withTemplate() { var x = `literal ${ { a: 1, b: [1,2,3] }.a } more ${1+1}`; return x; }
function withComment() {
  // a } fake brace in a line comment
  /* another } fake brace in a block comment */
  return 42;
}
var arrowAssign = (x) => { return x * 2; };
obj = { methodStyle: function(z) { return z - 1; } };
</script>
<script src="external.js"></script>
<script>
function inSecondBlock() { return "second"; }
function ambiguousName() { return 1; }
</script>
</body></html>'''

    src, bi, off = extract_function_source(html, 'addTwo')
    ck('extracts a plain function() declaration verbatim',
       src == 'function addTwo(a, b) { return a + b; }')

    # KNOWN-BAD CONTROL, conflict-marker sweep, 2026-09-28: a document
    # with unresolved conflict markers must REFUSE extraction, never
    # silently serve whichever conflict side brace-balances first.
    conflicted_html = ('<html><script>\n<<<<<<< HEAD\n'
                      'function addTwo(a, b) { return a + b; }\n=======\n'
                      'function addTwo(a, b) { return a - b; }\n'
                      '>>>>>>> branch\n</script></html>')
    try:
        extract_function_source(conflicted_html, 'addTwo')
        ck('KNOWN-BAD CONTROL: conflicted document refuses extraction', False)
    except RefuseExtraction as e:
        ck('KNOWN-BAD CONTROL: conflicted document refuses extraction '
           '(never serves one merge side silently)',
           'conflict' in str(e).lower())

    src2, _, _ = extract_function_source(html, 'withString')
    ck("a brace inside a string literal does not desync the scan",
       src2.strip().startswith('function withString()') and src2.rstrip().endswith('}'))

    src3, _, _ = extract_function_source(html, 'withTemplate')
    ck('nested ${...} template-expression braces are tracked independently '
       'and do not desync the outer scan',
       src3.count('{') == src3.count('}') and src3.strip().endswith('}'))

    # REGRESSION, found only by running this tool live against a real
    # platform function (sairnlaw.html's H()), not by inspection: a regex
    # literal like /"/ contains a bare quote character that a scanner
    # tracking only strings/templates/comments (the interface spec's exact
    # words) misreads as opening a real string, then swallows everything
    # up to the NEXT quote character anywhere later in the file.
    html_regex_bug = (
        "<script>function H(s){return String(s||'').replace(/&/g,'&amp;')"
        ".replace(/\"/g,'&quot;').replace(/'/g,'&#39;');}\n"
        "function jsEscape(s){return String(s||'').replace(/\\\\/g,'\\\\\\\\');}"
        "</script>")
    src_h, _, _ = extract_function_source(html_regex_bug, 'H')
    ck("a regex literal containing a bare quote character (e.g. /\"/ , an "
       "ordinary HTML-escape idiom) does not fool the string tracker into "
       "swallowing the rest of the file",
       src_h == "function H(s){return String(s||'').replace(/&/g,'&amp;')"
                ".replace(/\"/g,'&quot;').replace(/'/g,'&#39;');}")

    src4, _, _ = extract_function_source(html, 'withComment')
    ck('braces inside line and block comments do not desync the scan',
       'return 42;' in src4 and src4.strip().endswith('}'))

    src5, _, _ = extract_function_source(html, 'arrowAssign')
    ck('a braced-body arrow-function assignment is extracted',
       src5.startswith('arrowAssign = (x) => {'))

    src6, _, _ = extract_function_source(html, 'methodStyle')
    ck('an old-style object-method shorthand is extracted',
       src6.startswith('methodStyle: function(z)'))

    src7, bi7, _ = extract_function_source(html, 'inSecondBlock')
    ck('a function defined in the SECOND script block is found there, '
       'not assumed to be in the first', bi7 == 1)

    ck('a src= script block is never scanned (external.js is not fetched '
       'or parsed)', len(extract_script_blocks(html)) == 2)

    ck('an entirely absent function name refuses rather than returning '
       'nothing silently',
       _raises(RefuseExtraction, extract_function_source, html, 'doesNotExist'))

    html_dup = '<script>function dup(){return 1;} function other(){ dup(); dup(); return 2; }</script>'
    # dup() appears three times total but only ONE is a definition -- must
    # not confuse call-sites with the definition.
    src_dup, _, _ = extract_function_source(html_dup, 'dup')
    ck('call-sites of a function are not mistaken for its definition',
       src_dup == 'function dup(){return 1;}')

    html_two_defs = '<script>function twice(){return 1;} var x=1; function twice(){return 2;}</script>'
    ck('two real candidate definitions for the same name REFUSES rather '
       'than picking one silently',
       _raises(RefuseExtraction, extract_function_source, html_two_defs, 'twice'))

    html_unterminated = '<script>function broken(){ var s = "never closes;</script>'
    ck('an unterminated string at end of scan REFUSES rather than '
       'returning a truncated span',
       _raises(RefuseExtraction, extract_function_source, html_unterminated, 'broken'))

    # -- the three REQUIRED sandbox-boundary proofs, run for real through node --
    fixture_html = '''<script>
function callsFetch() { return fetch("https://example.invalid/x"); }
function callsRequire() { return require("fs").readFileSync("/etc/passwd"); }
function readsProcessEnv() { return process.env.SECRET_KEY; }
function pureMath(a, b) { return a * b + 1; }
function returnsArgsBack(x, y) { return [x, y, x + y]; }
</script>'''
    import tempfile as _tf
    tmp = _tf.mkdtemp(prefix='hover-tier0-fixture-')
    fixture_path = os.path.join(tmp, 'fixture.html')
    with io.open(fixture_path, 'w', encoding='utf-8') as f:
        f.write(fixture_html)

    def run_fixture(fn, fn_args):
        src, _, _ = extract_function_source(fixture_html, fn)
        d = _tf.mkdtemp(prefix='hover-tier0-run-')
        try:
            sp = os.path.join(d, 'f.js'); ap = os.path.join(d, 'a.json'); hp = os.path.join(d, 'h.js')
            with io.open(sp, 'w', encoding='utf-8') as f: f.write(src)
            with io.open(ap, 'w', encoding='utf-8') as f: json.dump(fn_args, f)
            with io.open(hp, 'w', encoding='utf-8') as f: f.write(_HARNESS)
            rc, out, err = _run([NODE, hp, sp, ap, fn], timeout=10)
            if rc != 0:
                raise RuntimeError('harness failed: %s / %s' % (out, err))
            return json.loads(out)
        finally:
            import shutil; shutil.rmtree(d, ignore_errors=True)

    r_fetch = run_fixture('callsFetch', [])
    ck('a function calling fetch() throws a REAL ReferenceError from the '
       'engine (fetch is not defined), proving no ambient network capability',
       r_fetch['ok'] is False and r_fetch['error']['name'] == 'ReferenceError'
       and 'fetch' in (r_fetch['error']['message'] or ''))

    r_require = run_fixture('callsRequire', [])
    ck('a function calling require() throws a REAL ReferenceError, proving '
       'no ambient module-loading capability',
       r_require['ok'] is False and r_require['error']['name'] == 'ReferenceError'
       and 'require' in (r_require['error']['message'] or ''))

    r_process = run_fixture('readsProcessEnv', [])
    ck('a function reading process.env throws a REAL ReferenceError, '
       'proving no ambient process/environment capability',
       r_process['ok'] is False and r_process['error']['name'] == 'ReferenceError'
       and 'process' in (r_process['error']['message'] or ''))

    r_pure = run_fixture('pureMath', [3, 4])
    ck('a genuinely pure function executes for real and returns the '
       'correct computed result (not a mock, not a stub)',
       r_pure['ok'] is True and r_pure['result'] == 13)

    r_args = run_fixture('returnsArgsBack', ['a', 'b'])
    ck('caller-supplied synthetic arguments are passed through faithfully',
       r_args['ok'] is True and r_args['result'] == ['a', 'b', 'ab'])

    import shutil as _sh
    _sh.rmtree(tmp, ignore_errors=True)

    print('')
    if bad:
        print('%d of %d selftest arm(s) failed' % (len(bad), total[0]))
        return 2
    print('OK -- %d arms passed, including 3 real ReferenceError proofs run '
          'through node (not asserted from reading vm-module documentation).'
          % total[0])
    return 0


def _raises(exc_type, fn, *a, **kw):
    try:
        fn(*a, **kw)
        return False
    except exc_type:
        return True


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
