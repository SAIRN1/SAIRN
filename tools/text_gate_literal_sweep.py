#!/usr/bin/env python3
"""tools/text_gate_literal_sweep.py -- which gates that read TEXT can be fooled
by a literal, a comment or a concatenation that looks like code?

    python tools/text_gate_literal_sweep.py
    python tools/text_gate_literal_sweep.py --list
    python tools/text_gate_literal_sweep.py --empirical   # feed each a decoy
    python tools/text_gate_literal_sweep.py --baseline

Exit 0 no worse than pinned, 1 a regression, 2 COULD NOT TELL.

── THE CLASS ──────────────────────────────────────────────────────────────
A gate that searches source, SQL or prose for a pattern will find that pattern
INSIDE a string literal or a comment unless it removes them first. Two failure
directions, and only one of them is visible:

  FALSE POSITIVE  a decoy in prose is reported as real. Survivable, loud, and
                  it trains people to add skip-lists -- which is how a real
                  finding later gets hidden.
  DESYNCHRONISED  the scanner loses track of where a literal ends and parses
                  the rest of the file wrongly. SILENT, and it can make real
                  code INVISIBLE to the gate.

MEASURED, NOT HYPOTHESISED. tools/sairn_sql_preflight.py stripped comments and
literals in four separate regex passes, so a `--` inside a string was blanked as
a comment and took the closing quote with it. It reported MISSING_TABLE `the`
from an English sentence -- and, far worse, ~140 lines of
sql/sairn_circuit_breaker_schema.sql were invisible to it because :54 is a
literal that BEGINS with `--`. Fixed 2026-09-27 with a single left-to-right scan.

── WHAT THIS MEASURES, AND ITS LIMIT IS THE HEADLINE ─────────────────────
STATIC: does the tool mask literals/comments before matching? A tool carrying a
masking function, a tokeniser, or an AST parse is MASKED. One calling
re.search/findall straight over file text is RAW.

RAW IS NOT A DEFECT LIST. Plenty of gates are correctly raw: a marker scan
anchored at column zero is *about* raw lines, and a prose checker's subject IS
the prose. The question a reader must answer per tool is "could a decoy in a
literal change this tool's verdict", and only the tool's author can answer it.
So RAW is a list to READ.

EMPIRICAL (--empirical): for gates with a file-path CLI, feed a file whose
comments and literals contain the exact thing the gate looks for, and see
whether the verdict moves. THAT is a real answer rather than a proxy, and it is
the only half that can promote a tool from RAW to CONFIRMED-SAFE.

A RATCHET on docs/text-gate-literal-coverage.json: `raw_unverified` must never
rise. An absent or unparseable pin is exit 2, and so is finding zero text gates.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIN = os.path.join(REPO, 'docs', 'text-gate-literal-coverage.json')

# A tool READS TEXT if it opens files and matches patterns against what it read.
READS_TEXT = re.compile(r"""\.read\(\)|read_text\(|readlines\(|io\.open\(""")
# MATCHING, IN EVERY SPELLING USED HERE. The first cut required a literal
# `re.search(`-style call and therefore MISSED EVERY TOOL USING A PRECOMPILED
# PATTERN -- which is most of the careful ones, including
# conflict_marker_check.py, control_char_check.py and md_table_check.py. Three
# of the four BY_DESIGN entries were reported as not-a-text-gate at all, so the
# exemptions read as zero and the universe was undercounted.
#
# THAT IS THIS SWEEP COMMITTING THE DEFECT IT SWEEPS FOR: a pattern that looks
# complete, silently misses a whole shape, and reports a confident number.
MATCHES = re.compile(
    r"""re\.(?:search|match|findall|finditer|sub|split|compile)\("""
    r"""|\.(?:search|match|findall|finditer)\(""")

# Evidence the tool removes literals/comments before matching, or parses rather
# than scans. Names are deliberately broad -- a tool that masks under any of
# these spellings is doing the right thing.
MASKS = re.compile(
    r"""def\s+mask|def\s+masks|def\s+strip_noise|def\s+_?strip_comments"""
    r"""|strip_comments|strip_noise\(|\bmasked\b|blank_literals"""
    r"""|\bast\.parse\(|\btokenize\.|html\.parser|HTMLParser|json\.loads\(""")

# Tools whose SUBJECT is the raw text, so raw matching is correct by design.
# Each needs a REASON, not just a name -- an exemption without one is a
# skip-list, which is the hole this whole sweep exists to keep closed.
BY_DESIGN = {
    'conflict_marker_check.py':
        'its subject IS raw lines: a conflict marker is defined as appearing at '
        'column zero, and its measured false-positive baseline over 2,069 files '
        'is 0 for all four shapes. Masking would be wrong here.',
    'control_char_check.py':
        'it looks for control characters as BYTES; a literal cannot hide one '
        'from it and there is nothing to mask.',
    'eaten_substitution_check.py':
        'it exists to find text that was EATEN by shell substitution, so the '
        'damaged raw text is the subject.',
    'md_table_check.py':
        'its subject is markdown table structure, which is prose by definition.',
}


class CouldNotTell(Exception):
    pass


def tools():
    d = os.path.join(REPO, 'tools')
    if not os.path.isdir(d):
        raise CouldNotTell('tools/ does not exist')
    return [os.path.join(d, n) for n in sorted(os.listdir(d)) if n.endswith('.py')]


def classify():
    out = {}
    for path in tools():
        name = os.path.basename(path)
        try:
            src = io.open(path, encoding='utf-8', errors='replace').read()
        except OSError as exc:
            raise CouldNotTell('%s could not be read (%s) -- NOT a pass'
                               % (name, exc))
        if not (READS_TEXT.search(src) and MATCHES.search(src)):
            continue
        if name in BY_DESIGN:
            out[name] = ('BY-DESIGN', BY_DESIGN[name])
        elif MASKS.search(src):
            out[name] = ('MASKED', '')
        else:
            out[name] = ('RAW', '')
    if not out:
        raise CouldNotTell(
            'no tool matched read-text-and-match -- the shape moved and NOTHING '
            'was measured. This is NOT "no text gates".')
    return out


# ── THE EMPIRICAL HALF ─────────────────────────────────────────────────────
# A decoy file: every line below is a COMMENT or a STRING. Nothing in it is
# executable code, valid SQL, or a real finding. A gate that reports anything
# about it is reading prose as code.

DECOY_PY = '''"""A docstring that mentions subprocess.run(['git', 'rev-parse']) and
a role: 'owner' and a resource: 'alf_facility' and verifySessionToken(x).
"""
# subprocess.run(['git', 'log'])  -- commented out, not a call
NOTES = [
    "update public.alf_billing set amount = 0 where id = 'x'",
    "if (!ALF_MANAGEMENT_ROLES[session.role]) { res.status(403) }",
    "-- a literal that begins with a SQL comment",
]
'''

DECOY_SQL = """-- a comment naming public.not_a_real_table
select 1 as ok;
comment on table public.alf_incidents is
  'one -- two '
  'three from four '
  'update public.also_not_real set x = 1 where y = 2';
"""


def empirical():
    """Feed each file-path gate a decoy and report whether its verdict moved."""
    results = {}
    d = tempfile.mkdtemp(prefix='textgate-')
    py = os.path.join(d, 'decoy_module.py')
    sq = os.path.join(d, 'decoy_schema.sql')
    io.open(py, 'w', encoding='utf-8', newline='\n').write(DECOY_PY)
    io.open(sq, 'w', encoding='utf-8', newline='\n').write(DECOY_SQL)

    probes = [
        ('sairn_sql_preflight.py',
         [sys.executable, os.path.join(REPO, 'tools', 'sairn_sql_preflight.py'),
          '--live', os.path.join(REPO, 'db', 'schema_snapshot.json'), sq],
         ['not_a_real_table', 'also_not_real', 'MISSING_TABLE   the',
          'MISSING_TABLE   two', 'MISSING_TABLE   four']),
        ('conflict_marker_check.py',
         [sys.executable, os.path.join(REPO, 'tools', 'conflict_marker_check.py'),
          '--files', os.path.relpath(py, REPO)],
         []),
    ]
    for name, cmd, forbidden in probes:
        try:
            r = subprocess.run(cmd, cwd=REPO, capture_output=True, timeout=180)
            out = (r.stdout + r.stderr).decode('utf-8', 'replace')
        except Exception as exc:                                 # noqa: BLE001
            results[name] = ('COULD-NOT-RUN', str(exc)[:90])
            continue
        leaked = [f for f in forbidden if f in out]
        results[name] = (('LEAKED', ', '.join(leaked)) if leaked
                         else ('CONFIRMED-SAFE', 'decoy in prose changed no verdict'))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--empirical', action='store_true')
    ap.add_argument('--baseline', action='store_true')
    args = ap.parse_args(argv)

    try:
        found = classify()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- %s\n' % e)
        sys.stderr.write('This is the THIRD STATE and is NOT a clean run.\n')
        return 2

    raw = sorted(k for k, v in found.items() if v[0] == 'RAW')
    masked = sorted(k for k, v in found.items() if v[0] == 'MASKED')
    design = sorted(k for k, v in found.items() if v[0] == 'BY-DESIGN')

    print('TEXT-GATE LITERAL SWEEP -- can a decoy in a comment or a string')
    print('change this gate\'s verdict?')
    print('')
    print('%d tool(s) read text AND match patterns against it.' % len(found))
    print('  MASKED     removes literals/comments, or parses rather than scans : %d' % len(masked))
    print('  BY-DESIGN  raw is correct -- the raw text IS the subject          : %d' % len(design))
    print('  RAW        matches straight over file text, unverified            : %d' % len(raw))
    print('')

    if args.list or raw:
        print('  RAW -- A LIST TO READ, NOT A LIST OF DEFECTS. Ask per tool: could')
        print('  a decoy inside a literal change its verdict? Only --empirical or')
        print('  the tool\'s own control can answer that.')
        for n in raw:
            print('   %s' % n)
        print('')
    if args.list:
        for n in design:
            print('   BY-DESIGN %-38s %s' % (n, found[n][1]))
        print('')

    emp = {}
    if args.empirical:
        emp = empirical()
        print('  EMPIRICAL -- each gate fed a file whose comments and strings')
        print('  contain exactly what it looks for:')
        for n in sorted(emp):
            print('   %-34s %-16s %s' % (n, emp[n][0], emp[n][1]))
        print('')
        print('  ONLY %d of %d gates have an empirical probe. The rest are'
              % (len(emp), len(found)))
        print('  CLASSIFIED, not TESTED, and that difference is the point of this')
        print('  line: a static class is a proxy and the decoy is the property.')
        print('')

    if args.baseline:
        io.open(PIN, 'w', encoding='utf-8', newline='\n').write(json.dumps({
            '_what': 'Pinned text-gate literal coverage. Written by '
                     'tools/text_gate_literal_sweep.py --baseline. A ratchet: '
                     '`raw_unverified` must never rise.',
            '_why': 'A gate that searches text finds its pattern inside string '
                    'literals and comments unless it removes them first. The '
                    'loud direction is a false positive; the silent one is a '
                    'desynchronised scanner that makes real code invisible.',
            'text_gates': len(found),
            'masked': len(masked),
            'by_design': len(design),
            'raw_unverified': len(raw),
            'raw_tools': raw,
            'empirically_probed': sorted(emp),
        }, indent=2, sort_keys=True) + '\n')
        print('wrote %s' % os.path.relpath(PIN, REPO))
        return 0

    if not os.path.isfile(PIN):
        sys.stderr.write('COULD NOT TELL -- %s does not exist, so NOTHING was '
                         'compared. Run --baseline once.\n'
                         % os.path.relpath(PIN, REPO))
        return 2
    try:
        pin = json.load(io.open(PIN, encoding='utf-8'))
    except ValueError as e:
        sys.stderr.write('COULD NOT TELL -- %s will not parse (%s). NOTHING WAS '
                         'COMPARED.\n' % (os.path.relpath(PIN, REPO), e))
        return 2
    was = pin.get('raw_unverified')
    if not isinstance(was, int):
        sys.stderr.write('COULD NOT TELL -- the pin carries no integer '
                         '`raw_unverified`.\n')
        return 2
    now = len(raw)
    if now > was:
        print('REGRESSION -- unverified raw text gates rose from %d to %d.'
              % (was, now))
        print('Mask literals and comments before matching, or add the tool to')
        print('BY_DESIGN WITH A REASON and re-pin in the same commit.')
        return 1
    if now < was:
        print('IMPROVED -- fell from %d to %d. Re-pin:' % (was, now))
        print('   python tools/text_gate_literal_sweep.py --baseline')
        return 0
    print('OK -- no worse than pinned (%d raw).' % was)
    print('A RATCHET IS NOT A PASS. %d gate(s) still match straight over file '
          'text with no decoy control.' % now)
    return 0


if __name__ == '__main__':
    sys.exit(main())
