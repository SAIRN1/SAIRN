"""A subprocess reading text with the LOCALE default, which on this platform is cp1252.

    python tools/subprocess_decode_check.py
    python tools/subprocess_decode_check.py --json
    python tools/subprocess_decode_check.py --fix     # add the argument, in place

Exit 0 clean, 1 a finding. There is no COULD-NOT-TELL: it parses tracked .py
files and either finds the shape or does not.

── THE DEFECT, OBSERVED RATHER THAN THEORISED ─────────────────────────────────
Text mode with no explicit encoding decodes the child's output with
`locale.getpreferredencoding()`. On this platform that is **cp1252**, and this
repo is full of UTF-8: box-drawing rules in every tool header, em-dashes in
every document, arrows in every gate message.

IT FAILS IN TWO WAYS AND THE QUIET ONE IS WORSE.

  MOJIBAKE   cp1252 maps most UTF-8 continuation bytes to *something*, so the
             call SUCCEEDS and returns text that is not what the child wrote.
             A scanner looking for a box-drawing character, an arrow or a
             curly quote simply stops matching. No error, no exit code, no
             sign -- it under-detects and reports clean.

  HARD FAIL  cp1252 has NO mapping for 0x81, 0x8D, 0x8F, 0x90 or 0x9D. Four
             tracked files in this repo contain one, including
             SAIRN-ACTIVE-WORK-cc.md, which appears in diffs constantly. The
             reader THREAD raises UnicodeDecodeError, the threading machinery
             prints a traceback, and the call returns with partial output.

THE SECOND MODE WAS OBSERVED FIRST, on 2026-09-15, in tools/tier_a_review_gate.py
-- and the consequence was worse than a crash. sairn_push_gate_hook.py maps that
tool's exit 1 to "this push changes Tier A code and no review obligation is
recorded". An uncaught Python exception ALSO exits 1. So the gate did not report
a crash: IT MADE A SPECIFIC, CREDIBLE, FALSE ACCUSATION about a push that
touched no Tier A resource at all.

── IT PARSES, IT DOES NOT GREP, AND THE FIRST TWO VERSIONS PROVED WHY ─────────
Version one used a regex with a 400-character window: 64 sites in 34 files.
Version two used balanced parens: 361. Every multi-line call was invisible to
the first, and multi-line is how the long ones are written -- a 5x
undercount.

Version two then ran its own --fix and EDITED ITS OWN DOCSTRING, because the
prose above contains a literal `subprocess.run(..., text=True)` as an example.
A source scanner that cannot tell code from text that describes code is
CLAUDE.md's standing rule 1.2, reproduced inside a tool written to fix a
different fail-open.

So it walks the AST. A `Call` node is a call; a docstring is a `Constant` and is
never one. There is no window, no window size to get wrong, and prose about
subprocess is just prose.

── WHAT IT CANNOT SEE, named rather than implied ──────────────────────────────
  * `os.popen`, `os.system`, and any subprocess wrapper defined elsewhere.
  * Kwargs splatted from a dict -- `subprocess.run(cmd, **opts)`.
  * Whether `errors='replace'` is the RIGHT policy for a given caller. It is
    the right default here -- git and node emit UTF-8, and a gate must never
    raise on a stray byte -- but a caller needing byte-exactness should not be
    in text mode at all.
"""
import ast
import io
import json
import locale
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOTS = ('tools', 'tests')
FUNCS = ('run', 'Popen', 'check_output', 'call', 'check_call')
TEXT_KW = ('text', 'universal_newlines')
ADD = ", encoding='utf-8', errors='replace'"


def is_subprocess_call(node):
    f = node.func
    return (isinstance(f, ast.Attribute) and f.attr in FUNCS
            and isinstance(f.value, ast.Name) and f.value.id == 'subprocess')


def findings_in(src):
    """[(lineno, end_lineno, end_col_offset of the text kwarg)] for every
    subprocess call in text mode with no encoding."""
    out = []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        raise ValueError('does not parse: %s' % e)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not is_subprocess_call(node):
            continue
        kw = {k.arg: k for k in node.keywords if k.arg}
        if 'encoding' in kw:
            continue
        for name in TEXT_KW:
            k = kw.get(name)
            if k is None:
                continue
            # `text=False` is not text mode and needs nothing.
            if isinstance(k.value, ast.Constant) and k.value.value is not True:
                continue
            out.append((node.lineno, k.value.end_lineno, k.value.end_col_offset))
            break
    return out


def py_files():
    for root in ROOTS:
        for dirpath, _, files in os.walk(os.path.join(REPO, root)):
            if '.git' in dirpath or 'node_modules' in dirpath:
                continue
            for f in sorted(files):
                if f.endswith('.py'):
                    yield os.path.join(dirpath, f).replace(os.sep, '/')


def scan():
    rows, unparsed = [], []
    for path in py_files():
        rel = os.path.relpath(path, REPO).replace(os.sep, '/')
        src = io.open(path, encoding='utf-8', errors='replace').read()
        try:
            for lineno, _, _ in findings_in(src):
                rows.append({'file': rel, 'line': lineno})
        except ValueError as e:
            # A file that does not parse is NOT a clean file. Some probes ship
            # deliberately broken fixtures; those are named rather than counted
            # as passing.
            unparsed.append((rel, str(e)[:80]))
    return rows, unparsed


def fix_file(path):
    """Insert the argument after the text kwarg's VALUE, working bottom-up so
    earlier offsets stay valid. Positions come from the AST, so an example in a
    docstring is never touched."""
    src = io.open(path, encoding='utf-8', newline='').read()
    try:
        hits = findings_in(src)
    except ValueError:
        return 0
    if not hits:
        return 0
    lines = src.split('\n')
    for _, end_line, end_col in sorted(hits, key=lambda h: (-h[1], -h[2])):
        i = end_line - 1
        lines[i] = lines[i][:end_col] + ADD + lines[i][end_col:]
    new = '\n'.join(lines)
    # NEVER WRITE A FILE THAT STOPPED PARSING. A mechanical sweep across 138
    # files is exactly where one bad insertion would be invisible.
    try:
        ast.parse(new)
    except SyntaxError as e:
        sys.stderr.write('REFUSED to write %s -- the edit broke the parse: %s\n'
                         % (path, e))
        return 0
    io.open(path, 'w', encoding='utf-8', newline='').write(new)
    return len(hits)


def main():
    if '--fix' in sys.argv:
        total, touched = 0, 0
        for path in py_files():
            n = fix_file(path)
            if n:
                total += n
                touched += 1
        print('added the encoding argument at %d call site(s) in %d file(s)'
              % (total, touched))
        return 0
    rows, unparsed = scan()
    if '--json' in sys.argv:
        print(json.dumps({'findings': rows, 'unparsed': unparsed}, indent=2))
        return 1 if rows else 0
    print('SUBPROCESS TEXT DECODE -- the locale default here is %s'
          % locale.getpreferredencoding(False))
    print('  text-mode subprocess calls with NO explicit encoding= : %d' % len(rows))
    if unparsed:
        print('  files that DID NOT PARSE (not counted as clean)     : %d' % len(unparsed))
        for f, why in unparsed[:5]:
            print('      %s -- %s' % (f, why))
    if not rows:
        print('\n  CLEAN. Every text-mode subprocess names its encoding.')
        print('  This is a GATE and not a score: the correct number IS zero,')
        print('  because the fix is one keyword argument, and "this caller only')
        print('  checks an exit code" is how a latent fail-open survives.')
        return 0
    by_file = {}
    for r in rows:
        by_file.setdefault(r['file'], []).append(r['line'])
    for f in sorted(by_file):
        print('  %-56s %s' % (f, ','.join(str(x) for x in by_file[f])[:36]))
    print('\n  Fix them all:  python tools/subprocess_decode_check.py --fix')
    return 1


if __name__ == '__main__':
    sys.exit(main())
