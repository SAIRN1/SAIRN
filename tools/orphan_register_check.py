#!/usr/bin/env python
"""orphan_register_check.py -- hold StoneDesk's orphaned-module register to its
own claims, and stop the open-work index describing things that are gone.

WHY THIS EXISTS. On 2026-09-04 two rows in `docs/SAIRN-OPEN-WORK-INDEX.md` were
stale by five weeks:

  * "panel-remnant double-render: sdRemnantRender() and remRender() both live"
    -- marked Open with a warning triangle. `remRender()` was deleted on
    2026-07-30, and `stonedesk.html`'s orphaned-module register said so twice.
  * "Two parallel template modules with different storage keys" -- also Open,
    also resolved the same day, also in the register.

Both still paid for themselves: each turned up a real adjacent defect. But
nothing connected the index to the register in either direction.

── THE FORMAT THIS READS, AND WHY IT EXISTS ────────────────────────────────
Each register entry now carries one machine-readable line directly under its
heading, added 2026-09-04:

    // @REGISTER module=remnant-yard removed=2026-07-30
    //           canonical=sdRemnantAdd,sdRemnantAI,sdRemnantPrint
    //           canonical_key=sd_remnant deleted=remAddRemnant,remSave,...
    //           orphan_keys=sd_remnants

(one physical line in the file; wrapped here for readability)

The prose above and below it is untouched -- it is where a human reads WHY a
module was removed, and it is good. The structured line exists because THREE
attempts to parse that prose each failed differently:

  1. narrow extraction captured 2 of the 9 names in entry 4 and missed
     `remRender`, the exact identifier that prompted the tool. It ran CLEAN
     against the historical index and nearly shipped with a self-test claim in
     its own docstring that was FALSE;
  2. wide extraction pulled the prose words `finish`, `load`, `desc`, `ship`,
     `unit`, `result`, `notes`, `customer`, `date` and matched `date` against a
     SAIRNlaw row about a holiday statute -- eleven false findings;
  3. camelCase-only with a canonical-survivor subtraction then swallowed most
     of the real names.

That churn is itself the lesson: a checker built on parsing English commentary
is the same class of thing as an assertion that matches prose about the code
rather than the code -- `sairn-code-scrubber` item 16, Shape A. The fix is not
a better regex, it is to stop asking prose a question it cannot answer.

── WHAT IT CHECKS ──────────────────────────────────────────────────────────
Per register entry, four assertions, all against the file rather than the text:

  * every `deleted=` name has NO definition        (it really went)
  * every `canonical=` name HAS one                (the survivor really survived)
  * every `orphan_keys=` key is untouched          (the dead key stayed dead)
  * every `canonical_key=` is present              (the live key is still live)
  * every `retired_keys=` key has NO writer but IS read
                                                   (read-only legacy, not dead)

`retired_keys` is a separate field from `orphan_keys` because "dead" and
"read-only legacy" are different states. `sd_template_records` is deliberately
still read, by tmMigrateLegacyRecords(), and deliberately never written;
collapsing the two would either raise a false alarm there or hide a real one
somewhere a key genuinely came back.

Then, across EVERY open row of the index -- not only StoneDesk rows, and not
only identifiers written as code -- any mention of a `deleted=` name, an
`orphan_keys=` key or a `retired_keys=` key. Bare-word matching is safe here in
a way it was not before: the names come from a curated list somebody wrote
down, not from a scrape of commentary.

WHAT IT STILL CANNOT DO, so a clean run is not over-read:

  * It only knows entries that carry a `@REGISTER` line. A module removed
    without being written up is invisible, the same limitation the register has.
  * A row can be stale for reasons that have nothing to do with a missing
    identifier -- a fixed bug, a decision taken, a figure that moved.
  * It reads "open" from the status column's text. An unusually phrased row
    slips past.

── IT HAS BEEN WATCHED GOING RED ───────────────────────────────────────────
A checker nobody has seen fail is a checker whose behaviour nobody knows.

    git show 0e40bb8f:docs/SAIRN-OPEN-WORK-INDEX.md > /tmp/i.md
    python tools/orphan_register_check.py --index /tmp/i.md

flags BOTH 2026-09-04 rows:

    row 177 mentions remRender             (a deleted= name)
    row 178 mentions sd_template_records   (a retired_keys= key)

Under the prose-parsing version only the first was reachable, and only after
three rewrites. The second needed the template entry to carry a @REGISTER line
at all -- it is not numbered and says "RETIRED" rather than "orphaned duplicate
removed", so every phrasing-based scan had walked past it, including this
tool's own first three.

Usage:
  python tools/orphan_register_check.py
  python tools/orphan_register_check.py --index <path>
  python tools/orphan_register_check.py --list      # dump the parsed register

Exit codes: 0 clean / 1 findings / 2 error.
"""
import io
import os
import re
import sys

# Findings quote real index rows, which carry em dashes and warning triangles. A
# cp1252 stdout turns that into a crash INSIDE the reporting path -- a checker
# that dies while telling you what it found. Seen on this machine, 2026-09-04.
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, 'stonedesk.html')
INDEX = os.path.join(REPO, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')

# Phrases that mean a row is NOT open. Kept literal and short: a longer list
# makes this quieter, and quiet is the failure mode it exists to prevent.
CLOSED_MARKERS = ('closed', 'done', 'superseded', 'fixed', 'recovered', 'seeded',
                  'built and live', 'not a defect', 'accepted')


def read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def parse_register(src):
    out = []
    for line in src.split('\n'):
        if not line.startswith('// @REGISTER '):
            continue
        fields = {}
        for m in re.finditer(r'(\w+)=([^\s]*)', line[len('// @REGISTER '):]):
            fields[m.group(1)] = [v for v in m.group(2).split(',') if v]
        out.append(fields)
    return out


def is_defined(src, name):
    n = re.escape(name)
    pats = [r'function\s+' + n + r'\s*\(',
            r'\b' + n + r'\s*[:=]\s*(async\s+)?function',
            r'window\.' + n + r'\s*=',
            r'\b' + n + r'\s*=\s*(async\s*)?\(']
    return any(re.search(p, src) for p in pats)


_SQL = None


def sql_names():
    """`sd_*` names declared in sql/. An index row citing `sd_public_rate_limits`
    names a SUPABASE TABLE, not a localStorage key, and it is correct that
    stonedesk.html never mentions it. The two namespaces share the prefix, so
    the only way to tell them apart is to ask the schema files."""
    global _SQL
    if _SQL is None:
        names, d = set(), os.path.join(REPO, 'sql')
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.endswith('.sql'):
                    names |= set(re.findall(r'\b(sd_[a-z_]{3,})\b', read(os.path.join(d, fn))))
        _SQL = names
    return _SQL


def writers(src, key):
    pat = r"(st|stRaw)\(\s*'%s'|setItem\(\s*'%s'" % (re.escape(key), re.escape(key))
    return [l for l in src.split('\n') if re.search(pat, l)]


def key_present(src, key):
    return ("'%s'" % key) in src or ('"%s"' % key) in src


def open_rows(index_path):
    rows = []
    for n, line in enumerate(read(index_path).split('\n'), 1):
        if not line.startswith('| **'):
            continue
        cells = line.split('|')
        if len(cells) < 5:
            continue
        item, status = cells[2], cells[3]
        if any(m in status.lower() for m in CLOSED_MARKERS):
            continue
        if item.strip().startswith('~~'):
            continue
        rows.append((n, item.strip(), line))
    return rows


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    index_path = argv[argv.index('--index') + 1] if '--index' in argv else INDEX
    for p in (APP, index_path):
        if not os.path.exists(p):
            sys.stderr.write('not found: %s\n' % p)
            return 2

    src = read(APP)
    entries = parse_register(src)
    if not entries:
        sys.stderr.write('ERROR: no @REGISTER lines in stonedesk.html. Either the '
                         'register lost them or this tool is pointed at the wrong '
                         'file -- it is checking NOTHING until that is resolved.\n')
        return 2
    print('REGISTER_ENTRIES:%d' % len(entries))

    if '--list' in argv:
        for e in entries:
            print('  ' + ' '.join('%s=%s' % (k, ','.join(v)) for k, v in sorted(e.items())))
        return 0

    findings = []
    dead_names, dead_keys = set(), set()
    for e in entries:
        mod = (e.get('module') or ['?'])[0]
        for n in e.get('deleted', []):
            dead_names.add(n)
            if is_defined(src, n):
                findings.append('REGISTER: %s says %s() was deleted, but it is '
                                'defined again' % (mod, n))
        for n in e.get('canonical', []):
            if not is_defined(src, n):
                findings.append('REGISTER: %s names %s() as the surviving canonical '
                                'function, and it no longer exists' % (mod, n))
        for k in e.get('orphan_keys', []):
            dead_keys.add(k)
            if key_present(src, k):
                findings.append('REGISTER: %s says %s is a dead orphan key, but the '
                                'file references it' % (mod, k))
        for k in e.get('canonical_key', []):
            if not key_present(src, k) and k not in sql_names():
                findings.append('REGISTER: %s names %s as its canonical key, and the '
                                'file never references it' % (mod, k))
        # retired_keys are NOT orphan_keys. A retired key is read-only legacy:
        # still read, by a migration, and never written. "Dead" and "read-only
        # legacy" are different states, and collapsing them would either raise a
        # false alarm on the template manager or hide a real one elsewhere.
        for k in e.get('retired_keys', []):
            dead_keys.add(k)
            if writers(src, k):
                findings.append('REGISTER: %s calls %s a retired read-only key, but '
                                'something writes it' % (mod, k))
            elif not key_present(src, k):
                findings.append('REGISTER: %s names %s as a retired key still read by '
                                'a migration, and nothing references it -- either the '
                                'migration went or the entry is stale' % (mod, k))
    print('DELETED_NAMES:%d  DEAD_KEYS:%d' % (len(dead_names), len(dead_keys)))

    rows = open_rows(index_path)
    print('OPEN_INDEX_ROWS:%d' % len(rows))
    for n, item, line in rows:
        # Bare word boundaries are safe here, unlike in the prose-parsing
        # version: these names come from a curated list somebody wrote down.
        hit_n = sorted(x for x in dead_names if re.search(r'(?<![\w$.])%s\b' % re.escape(x), line))
        hit_k = sorted(x for x in dead_keys if re.search(r'\b%s\b' % re.escape(x), line))
        if hit_n or hit_k:
            findings.append(
                'INDEX: open row %d mentions %s, which the register records as '
                'removed. %s' % (n, ', '.join(hit_n + hit_k), item[:80]))

    if findings:
        print('\n--- FINDINGS ---')
        for f in findings:
            print('  ' + f)
        print('\nRESULT:FINDINGS (%d)' % len(findings))
        print('Read the row before closing it: on 2026-09-04 both stale rows still '
              'pointed at real adjacent defects.')
        return 1
    print('\nRESULT:CLEAN -- the register matches the file, and no open index row '
          'mentions anything it records as removed.')
    print('NOTE: only entries carrying a @REGISTER line are visible here, and a row '
          'can be stale for reasons this cannot see. A clean run is not a claim '
          'that the index is current.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
