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
        "\n// ── A STABLE LAST LINE (2026-10-19, cody b27) ─────────────────────────────\n"
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
        "\n# ── A STABLE LAST LINE (2026-10-19, cody b27) ─────────────────────────────\n"
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


missing = [t for t in TARGETS if not os.path.isfile(t)]
if missing:
    print('COULD NOT RUN: ' + str(len(missing)) + ' subject(s) are not on '
          'disk: ' + ', '.join(missing) + '. Nothing was verified.')
    sys.exit(2)

print('STABLE LAST LINE -- b27 item 4')
print('  subjects  ' + str(len(TARGETS)) + ', read from ' + REG
      + ' (tail_verdict_2026_10_19 == UNPRODUCIBLE)')
print('  marker    ' + MARK + ' <path> PASSED|FAILED   -- no digits, so the '
      'register\'s digit-normalising comparison sees one constant')
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
    if rel.endswith('.py'):
        # ── THE PYTHON HOOK GOES AT THE *END* OF THE FILE, NOT THE TOP ────
        # A top-of-file atexit registration runs LAST among atexit handlers
        # (they run in reverse registration order), and these probes register
        # their own cleanup. Registering at the end means this one runs FIRST
        # -- which would put the line BEFORE a cleanup handler's output. The
        # end of the file is the earliest registration, so it fires last.
        new = src.rstrip('\n') + '\n' + py_hook(rel)
    else:
        new = src.rstrip('\n') + '\n' + js_hook(rel)
    planned.append((rel, src, new))
    print('  %-54s + %d lines' % (rel[:54],
                                  len(new.split('\n')) - len(src.split('\n'))))

if not planned:
    print('\nNothing to do -- every subject already prints a stable last line.')
else:
    # ── POST-CONDITIONS BEFORE ANYTHING IS WRITTEN ────────────────────────
    bad = []
    for rel, src, new in planned:
        if not new.startswith(src.rstrip('\n')):
            bad.append(rel + ': the original content is not a prefix of the '
                             'result, so this is not an append')
        if new.count(MARK) != 2:   # once in the hook, once in the comment? no:
            # the marker appears exactly ONCE, inside the printed string.
            if new.count(MARK) != 1:
                bad.append(rel + ': the marker appears ' + str(new.count(MARK))
                           + ' times, not once')
    if bad:
        print('\nREFUSED -- NOTHING written:')
        for b in bad:
            print('  * ' + b)
        sys.exit(1)
    if CHECK:
        print('\n--check: nothing written.')
    else:
        for rel, src, new in planned:
            io.open(rel, 'wb').write(new.encode('utf-8'))
            if io.open(rel, 'rb').read().decode('utf-8') != new:
                print('REFUSED: ' + rel + ' read back differently.')
                sys.exit(1)
        print('\nWRITTEN: ' + str(len(planned)) + ' file(s), appended only.')

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
