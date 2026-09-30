#!/usr/bin/env python
"""Does every source file this push ships actually PARSE?

WHY. The push gate syntax-checks stonedesk.html's script blocks and api/, and did
not check tools/ at all -- so a tools/tooling_inventory.py that did not parse
reached origin/main. The file was imported by nothing at push time, so no gate
noticed; the next session to run the generator found out.

    python tools/staged_parse_check.py <path> [<path> ...]

  .py   parsed with the interpreter's own compiler
  .js   parsed with `node --check`
  other SKIPPED, and the skip is COUNTED AND NAMED -- a file nobody checked is
        not a file that passed

── WHY NOT `python -m py_compile` ───────────────────────────────────────────
py_compile WRITES a __pycache__/*.pyc beside the file it checks. A gate that
mutates the tree it is inspecting is the defect tools/bare_run_write_check.py was
built to find, and it would show up in `git status --porcelain` as though the
push had produced it. `compile(src, path, 'exec')` is the same parser with no
artefact. A SyntaxError from either is the same SyntaxError.

── EXIT CODES, AND THE THIRD ONE IS NOT A PASS ──────────────────────────────
  0  every file given parsed
  1  at least one file does NOT parse
  2  COULD NOT RUN -- no files given, a file could not be read, or a .js was
     given and `node` is not on PATH. "I could not check" is never folded into
     "it is fine": that is PR 1.11, and this tool is invoked BY a gate, where
     exit 0 means allow.

It prints `files checked : N`, so the caller can tell an older copy of this tool
(which might ignore its arguments) from one that honoured the list -- the same
staleness guard the control-byte check already carries.
"""
import io
import os
import shutil
import subprocess
import sys

PY_EXT = ('.py',)
JS_EXT = ('.js', '.mjs', '.cjs')


def out(line):
    sys.stdout.write(line + '\n')


def check_py(path):
    """(ok, detail). A read failure is NOT a parse failure -- it is worse."""
    try:
        src = io.open(path, encoding='utf-8', errors='strict').read()
    except UnicodeDecodeError as e:
        return None, 'not valid UTF-8: %s' % e
    except OSError as e:
        return None, 'could not read: %s' % e
    try:
        compile(src, path, 'exec')
    except SyntaxError as e:
        return False, 'SyntaxError line %s: %s' % (e.lineno, e.msg)
    except ValueError as e:
        # a null byte in the source raises ValueError, not SyntaxError
        return False, 'ValueError: %s' % e
    return True, ''


def check_js(path):
    node = shutil.which('node')
    if not node:
        return None, ('node is not on PATH, so this .js was NOT checked. That is '
                      'a could-not-run, not a pass')
    try:
        r = subprocess.run([node, '--check', path], capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, 'node --check could not run: %s' % e
    if r.returncode == 0:
        return True, ''
    detail = ((r.stderr or '') + (r.stdout or '')).strip().split('\n')
    first = next((l for l in detail if 'Error' in l), detail[0] if detail else '')
    return False, first.strip()[:160]


def main(argv):
    paths = [a for a in argv if not a.startswith('-')]
    if not paths:
        sys.stderr.write(
            'No files given. COULD NOT RUN -- an empty run reporting "everything '
            'parses" is a measurement that did not happen, and this tool is '
            'called from a gate where exit 0 means allow.\n')
        return 2

    broke, could_not, skipped, checked = [], [], [], 0
    for p in paths:
        ap = p if os.path.isabs(p) else os.path.abspath(p)
        if not os.path.isfile(ap):
            could_not.append((p, 'no such file'))
            continue
        low = ap.lower()
        if low.endswith(PY_EXT):
            ok, why = check_py(ap)
        elif low.endswith(JS_EXT):
            ok, why = check_js(ap)
        else:
            skipped.append(p)
            continue
        checked += 1
        if ok is None:
            could_not.append((p, why))
        elif not ok:
            broke.append((p, why))

    out('STAGED PARSE CHECK')
    out('  files given   : %d' % len(paths))
    out('  files checked : %d' % checked)
    out('  skipped       : %d (not .py/.js -- named below, never silently '
        'dropped)' % len(skipped))
    for p in skipped:
        out('      SKIPPED %s' % p)
    if broke:
        out('')
        out('  DOES NOT PARSE: %d' % len(broke))
        for p, why in broke:
            out('      %s' % p)
            out('          %s' % why)
    if could_not:
        out('')
        out('  COULD NOT CHECK: %d -- NOT counted as parsing' % len(could_not))
        for p, why in could_not:
            out('      %s' % p)
            out('          %s' % why)
    out('')
    if broke:
        out('A file that does not parse is not a style problem. In tools/ it is a '
            'tool that will')
        out('fail the first time anybody runs it, and nothing at push time '
            'imports it.')
        return 1
    if could_not:
        out('Nothing failed to parse AND %d file(s) were not checked at all. '
            'That is not a' % len(could_not))
        out('clean bill.')
        return 2
    out('All %d checked file(s) parse.' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
