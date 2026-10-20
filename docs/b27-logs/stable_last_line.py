# docs/b27-logs/stable_last_line.py
# OWNER: cody   batch b27   2026-10-19
#
# THE CONCEPT: a known-red row is only ATTRIBUTABLE if the tail it records is
#   a line the runner can really produce, so the fix belongs in the SUITE --
#   each one prints ONE deterministic final line on every exit path -- rather
#   than in the register, where a tail copied from one run goes stale the next
#   time an arm is added or an arm list reorders.
#
#   python docs/b27-logs/stable_last_line.py --check
#   python docs/b27-logs/stable_last_line.py
#   python docs/b27-logs/stable_last_line.py --drive     # measure the result
#
# Exit: 0 applied / clean - 1 an assertion failed, NOTHING written -
#       2 COULD NOT RUN
#
# ── WHY A SUITE-SIDE FIX AND NOT A REGISTER-SIDE ONE ──────────────────────
# b26 measured 12 of the 49 comparable known-red rows carrying a tail
# tools/run_all_tests.py cannot produce, so known_red_check.py classifies every
# one of them CHANGED on every run -- which reads as "a second defect is hiding
# inside an entry that says this file is expected to fail" when THE ENTRY is
# the thing that is wrong (b22 item 4).
#
# Copying the observed line into the register would close all 12 today and
# reopen them on the next arm added, because for most of them the observed line
# IS an arm name or an arm list. The register would be correct and fragile.
#
# A `process.on('exit')` / `atexit` hook is LAST ON EVERY EXIT PATH, including
# the `process.exit(1)` these suites take when an arm fails, and it carries NO
# DIGITS -- so known_red_check's digit-normalising comparison sees one constant
# string for ever.
#
# WHAT IT CANNOT DO, STATED: a suite killed by a TIMEOUT or a hard crash never
# reaches the hook. tests/run_report_only_checks_probe.py's stored tail is
# literally "TIMED OUT after 300s", so that row's history includes a state this
# fix cannot stabilise. It completes today (b26 measured it at 300s), and if it
# hangs again the tail will be the timeout line again -- correctly, because a
# hang is not a result.
#
# ── A CONSTANT, NOT A VERDICT, AND THE FIRST DESIGN WAS WORSE ─────────────
# The line was going to read `... PASSED|FAILED`. Two reasons it is a plain
# constant instead, and the second is a correctness bug caught before writing:
#
#   1. NOT NEEDED. known_red_check.py decides RECOVERED from the run's GREEN
#      list -- by exit code -- not from the tail. The tail's only job is to
#      identify "the line this file ends with", so a constant does it best and
#      a count would digit-normalise to the same string as every other count.
#   2. NOT RELIABLY AVAILABLE IN PYTHON. `atexit` handlers receive no exit
#      code, and `sys.last_value` is an INTERACTIVE-mode artefact of an
#      uncaught exception -- it is NOT set by `sys.exit(1)`, which is the path
#      these probes take. The first draft read it and would have printed
#      `FAILED` for every run including the green ones, in a file whose whole
#      purpose is to make a tail trustworthy.
#
# The path is in the line, so each row's tail is still unique to its file.
#
# ══ b28: THE HOOK GOES AT THE TOP, AND b27's PLACEMENT WAS WRONG TWICE ═════
# b27 appended the hook to the END of each file, drove it, measured 0 of 12 and
# REVERTED. Two independent errors, and the second is the one worth keeping:
#
#   1. UNREACHABLE. These probes call `sys.exit(...)` at MODULE LEVEL.
#      `sys.exit` raises SystemExit, which propagates out of the module body,
#      so every line after it -- INCLUDING the `atexit.register()` call -- is
#      never executed. Measured: tests/run_rebase_resolve_probe.py:213 is the
#      exit, :215 was the hook.
#
#   2. THE REASONING WAS ALSO BACKWARDS. b27's own comment said the end of the
#      file is "the earliest registration, so it fires last". It is the
#      LATEST registration. `atexit` runs handlers in REVERSE registration
#      order, so the LAST registered fires FIRST -- the end of the file would
#      have printed the line BEFORE every cleanup handler even if it had run.
#      TOP placement is therefore correct on BOTH counts: it is reached, and
#      being the first registration it fires last.
#
# So a fix that was reverted for being inert was ALSO aimed the wrong way, and
# only driving it could have said so. A committed fix that does nothing is
# worse than an open item.
#
# ── WHERE "THE TOP" IS, PRECISELY ─────────────────────────────────────────
# Not line 1. A Python module's docstring must stay the FIRST statement or it
# stops being a docstring -- and tools/live_probe_declaration_check.py reads
# these docstrings, so demoting one would break a different check. A
# JavaScript `'use strict'` directive must stay first in its prologue or it
# silently stops applying. The insertion point is therefore computed:
#   .py  -- after the module docstring (located with `ast`, not a regex)
#   .js  -- after the `'use strict';` directive if there is one, else after
#           the leading comment block
#
# ── AND THE ARM THAT WOULD HAVE CAUGHT b27 ────────────────────────────────
# `assert_reached()` below refuses to write any file where the hook would land
# AFTER a module-level `sys.exit(`/`process.exit(`. That is the b27 defect
# expressed as a precondition, so it cannot recur silently in either file type.

import io
import os
import re
import subprocess
import sys

CHECK = '--check' in sys.argv
DRIVE = '--drive' in sys.argv

# The 12 rows b26 marked UNPRODUCIBLE, read from the register rather than typed.
import json
REG = 'docs/known-red-suites.json'
if not os.path.isfile(REG):
    print('COULD NOT RUN: ' + REG + ' is not here. Nothing was verified.')
    sys.exit(2)
reg = json.load(io.open(REG, encoding='utf-8'))
TARGETS = [e['file'] for e in reg.get('entries', [])
           if e.get('tail_verdict_2026_10_19') == 'UNPRODUCIBLE']
if not TARGETS:
    print('COULD NOT RUN: no entry in ' + REG + ' carries '
          'tail_verdict_2026_10_19 == UNPRODUCIBLE, so this tool has no '
          'subjects and would report success over an empty set.')
    sys.exit(2)

MARK = 'SUITE-RESULT'


def js_hook(rel):
    return (
        "\n// ── A STABLE LAST LINE (2026-10-20, cody b28) ─────────────────────────────\n"
        "// AT THE TOP, NOT THE END. b27 appended this and measured 0 of 12: these\n"
        "// files exit at module level, so nothing after that line ever runs.\n"
        "// THE CONCEPT: this suite must print ONE deterministic final line on every\n"
        "//   exit path, so docs/known-red-suites.json can record a tail the runner\n"
        "//   really produces -- b26 measured this file's stored tail as one it CANNOT.\n"
        "//\n"
        "// `process.on('exit')` fires after the summary AND after process.exit(1),\n"
        "// which is the path an arm failure takes here. The line carries NO DIGITS on\n"
        "// purpose: known_red_check.py normalises digits away, so a count would make a\n"
        "// red run and a green run compare EQUAL. It is a CONSTANT rather than a\n"
        "// verdict: known_red_check.py decides RECOVERED from the run's GREEN list,\n"
        "// by exit code, so the tail's only job is to identify the last line.\n"
        "process.on('exit', function () {\n"
        "  try { console.log('" + MARK + " " + rel + " END'); }\n"
        "  catch (e) { /* a suite that cannot log its own last line must not\n"
        "                 change its verdict by trying to */ }\n"
        "});\n")


def py_hook(rel):
    return (
        "\n# ── A STABLE LAST LINE (2026-10-20, cody b28) ─────────────────────────────\n"
        "# AT THE TOP, NOT THE END, FOR TWO REASONS. (1) This probe calls sys.exit()\n"
        "# at module level; SystemExit propagates out of the module body, so an\n"
        "# atexit.register() below it is never reached -- b27 appended it and\n"
        "# measured 0 of 12. (2) atexit runs handlers in REVERSE registration order,\n"
        "# so being registered FIRST is what makes this line print LAST.\n"
        "# THE CONCEPT: this probe must print ONE deterministic final line on every\n"
        "#   exit path, so docs/known-red-suites.json can record a tail the runner\n"
        "#   really produces -- b26 measured this file's stored tail as one it CANNOT.\n"
        "#\n"
        "# atexit fires after the summary AND after sys.exit(1), which is the path an\n"
        "# arm failure takes here. The line carries NO DIGITS on purpose:\n"
        "# known_red_check.py normalises digits away, so a count would make a red run\n"
        "# and a green run compare EQUAL. It is a CONSTANT rather than a verdict for\n"
        "# two reasons, the second of which was a real bug in the first draft:\n"
        "#   1. known_red_check.py decides RECOVERED from the run's GREEN list, by\n"
        "#      exit code, so the tail's only job is to identify the last line.\n"
        "#   2. atexit handlers receive NO exit code, and sys.last_value is an\n"
        "#      interactive-mode artefact of an uncaught exception -- it is NOT set\n"
        "#      by sys.exit(1), which is the path this probe takes. Reading it would\n"
        "#      have printed one verdict for every run.\n"
        "import atexit as _b27_atexit\n"
        "\n"
        "\n"
        "def _b27_stable_last_line():\n"
        "    try:\n"
        "        print('" + MARK + " " + rel + " END')\n"
        "    except Exception:\n"
        "        pass\n"
        "\n"
        "\n"
        "_b27_atexit.register(_b27_stable_last_line)\n")


# ── WHERE THE HOOK GOES, COMPUTED RATHER THAN ASSUMED ─────────────────────
def py_insert_line(src, rel):
    """0-based line index to insert at: after the module docstring.

    `ast` AND NOT A REGEX. A triple-quoted docstring that itself contains a
    triple-quote sequence -- which several of these do, quoting shell and
    JSON -- defeats every regex short of a parser, and getting it wrong means
    inserting INSIDE a docstring, which is a silent no-op: the file still
    compiles, still runs, and the hook is a few words in a comment.
    """
    import ast
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return None, 'will not parse before any edit (%s)' % e
    body = tree.body
    if not body:
        return None, 'has no statements'
    first = body[0]
    is_doc = (isinstance(first, ast.Expr)
              and isinstance(getattr(first, 'value', None), ast.Constant)
              and isinstance(first.value.value, str))
    if not is_doc:
        # No docstring: line 0 is safe, EXCEPT after a shebang or a coding
        # declaration, both of which must stay on their own first lines.
        lines = src.split('\n')
        i = 0
        while i < len(lines) and (lines[i].startswith('#!')
                                  or 'coding' in lines[i][:40]
                                  and lines[i].lstrip().startswith('#')):
            i += 1
        return i, None
    return first.end_lineno, None       # end_lineno is 1-based == index after


def js_insert_line(src, rel):
    """0-based line index: after `'use strict';`, else after the leading comments.

    A `'use strict'` directive is only a directive while it is first in the
    prologue. Inserting above it turns strict mode OFF for the whole file --
    which would not fail, it would QUIETLY CHANGE THE SEMANTICS of the suite
    under test, and a probe whose behaviour this tool altered is worse than a
    probe with an unstable tail.
    """
    lines = src.split('\n')
    for i, ln in enumerate(lines[:40]):
        if ln.strip() in ("'use strict';", '"use strict";'):
            return i + 1, None
    i = 0
    while i < len(lines) and (lines[i].lstrip().startswith('//')
                              or not lines[i].strip()):
        i += 1
    return i, None


# THE PRECONDITION THAT IS THE b27 DEFECT, WRITTEN AS A REFUSAL.
MODULE_EXIT_RE = re.compile(r'^(?:sys\.exit\(|process\.exit\()')


def assert_reached(src, insert_at, rel):
    """Refuse if the hook would land after a module-level exit call.

    Column 0 only: an indented `sys.exit(...)` is inside a function and does
    not run at import. An unindented one runs as the module executes, and
    everything below it is unreachable -- which is exactly what made b27's
    twelve appended hooks inert while every file still looked edited.
    """
    for n, ln in enumerate(src.split('\n')):
        if MODULE_EXIT_RE.match(ln) and n < insert_at:
            return ('line %d is a MODULE-LEVEL `%s` and the hook would be '
                    'inserted at line %d, below it -- unreachable, which is '
                    'the b27 defect' % (n + 1, ln.strip()[:30], insert_at + 1))
    return None


missing = [t for t in TARGETS if not os.path.isfile(t)]
if missing:
    print('COULD NOT RUN: ' + str(len(missing)) + ' subject(s) are not on '
          'disk: ' + ', '.join(missing) + '. Nothing was verified.')
    sys.exit(2)

print('STABLE LAST LINE -- b27 item 4')
print('  subjects  ' + str(len(TARGETS)) + ', read from ' + REG
      + ' (tail_verdict_2026_10_19 == UNPRODUCIBLE)')
print('  marker    ' + MARK + ' <path> END   -- no digits and no verdict, so '
      'the register\'s digit-normalising comparison sees one constant')
print('  placement AT THE TOP (b28). b27 appended and measured 0 of 12: these '
      'files exit at module level.')
print('')

planned = []
for rel in TARGETS:
    raw = io.open(rel, 'rb').read()
    if b'\r\n' in raw:
        print('  %-54s COULD NOT RUN -- CRLF in the working tree' % rel[:54])
        sys.exit(2)
    src = raw.decode('utf-8')
    if MARK in src:
        print('  %-54s already has a stable last line' % rel[:54])
        continue
    is_py = rel.endswith('.py')
    at, why = (py_insert_line(src, rel) if is_py else js_insert_line(src, rel))
    if at is None:
        print('  %-54s COULD NOT RUN -- %s' % (rel[:54], why))
        sys.exit(2)
    unreachable = assert_reached(src, at, rel)
    if unreachable:
        print('  %-54s REFUSED -- %s' % (rel[:54], unreachable))
        sys.exit(1)
    hook = py_hook(rel) if is_py else js_hook(rel)
    lines = src.split('\n')
    new = '\n'.join(lines[:at]) + '\n' + hook + '\n'.join(lines[at:])
    planned.append((rel, src, new, at))
    print('  %-54s + %d lines at line %d'
          % (rel[:54], len(new.split('\n')) - len(src.split('\n')), at + 1))

if not planned:
    print('\nNothing to do -- every subject already prints a stable last line.')
else:
    # ── POST-CONDITIONS BEFORE ANYTHING IS WRITTEN ────────────────────────
    bad = []
    for rel, src, new, at in planned:
        is_py = rel.endswith('.py')
        hook = py_hook(rel) if is_py else js_hook(rel)
        # ── NOTHING WAS CHANGED EXCEPT THE INSERTION ────────────────────
        # b27 could assert "the original is a PREFIX of the result" because it
        # appended. An insert cannot use that, and the weaker check it invites
        # -- "the file got longer" -- is what let an earlier sweep on this
        # platform delete 1,465 lines while an assertion stayed green. So the
        # hook is REMOVED from the result and the remainder must be the
        # original, byte for byte.
        if new.replace(hook, '', 1) != src:
            bad.append(rel + ': removing the hook from the result does not '
                             'give back the original file, so this edit '
                             'changed something else')
        if new.count(MARK) != 1:
            bad.append(rel + ': the marker appears ' + str(new.count(MARK))
                       + ' times, not once')
        # ── AND IT STILL PARSES. A docstring-boundary mistake does not raise;
        # it produces a file that compiles and does nothing, which is b27's
        # failure mode wearing different clothes.
        if is_py:
            try:
                compile(new, rel, 'exec')
            except SyntaxError as e:
                bad.append(rel + ': the result does not compile -- %s' % e)
        # ── AND THE HOOK IS ABOVE EVERY MODULE-LEVEL EXIT IN THE RESULT,
        # re-checked on the NEW text rather than inferred from the old.
        hook_line = new.split('\n').index(
            [l for l in new.split('\n') if MARK in l][0])
        for n, ln in enumerate(new.split('\n')):
            if MODULE_EXIT_RE.match(ln) and n < hook_line:
                bad.append(rel + ': in the RESULT, line %d is a module-level '
                           'exit above the hook at line %d'
                           % (n + 1, hook_line + 1))
                break
    if bad:
        print('\nREFUSED -- NOTHING written:')
        for b in bad:
            print('  * ' + b)
        sys.exit(1)
    if CHECK:
        print('\n--check: nothing written.')
    else:
        for rel, src, new, at in planned:
            io.open(rel, 'wb').write(new.encode('utf-8'))
            if io.open(rel, 'rb').read().decode('utf-8') != new:
                print('REFUSED: ' + rel + ' read back differently.')
                sys.exit(1)
        print('\nWRITTEN: ' + str(len(planned)) + ' file(s), inserted at the '
              'top of each.')

if DRIVE:
    print('')
    print('DRIVEN -- the real last line of each subject, captured the way '
          'tools/run_all_tests.py:942 captures it')
    print('  (stdout or stderr).strip().splitlines()[-1]')
    print('')
    out_rows = []
    for rel in TARGETS:
        cmd = [sys.executable if rel.endswith('.py') else 'node', rel]
        try:
            r = subprocess.run(cmd, cwd=os.getcwd(), capture_output=True,
                               text=True, encoding='utf-8', errors='replace',
                               timeout=300)
            lines = (r.stdout or r.stderr or '').strip().splitlines()
            tail = lines[-1] if lines else '(no output)'
            code = r.returncode
        except subprocess.TimeoutExpired:
            tail, code = 'TIMED OUT after 300s', None
        stable = tail.startswith(MARK)
        out_rows.append({'file': rel, 'exit': code, 'tail': tail,
                         'stable': stable})
        print('  %-5s %-52s exit %-4s %s'
              % ('ok' if stable else 'NO', rel[:52], code, tail[:60]))
    io.open('docs/b27-logs/stable_last_line.json', 'w', encoding='utf-8',
            newline='').write(json.dumps(
                {'measured': '2026-10-19', 'by': 'cody b27', 'marker': MARK,
                 'rows': out_rows}, indent=1))
    print('')
    nots = [r for r in out_rows if not r['stable']]
    print('  %d of %d subjects now end with %s'
          % (len(out_rows) - len(nots), len(out_rows), MARK))
    for r in nots:
        print('  NOT STABLE: ' + r['file'] + ' -> ' + r['tail'][:90])
    print('  wrote docs/b27-logs/stable_last_line.json')
    if nots:
        sys.exit(1)
sys.exit(0)
